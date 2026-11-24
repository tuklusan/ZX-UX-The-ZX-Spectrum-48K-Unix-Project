# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""rcc: C48 parser and semantic analysis -> typed AST."""
from .lex import CError, UNSUPPORTED_OPS, RESERVED
from .types import (INTS, BYTE, is_int, is_arith, is_ptr, is_arr, is_fn, is_scalar,
                    sizeof, promote, common, signed, tname, decay)
from . import romfp


class N:
    """Expression node."""
    __slots__ = ('op', 'ty', 'a', 'b', 'v', 'sym', 'args', 'lv', 'opty', 'where')

    def __init__(self, op, ty, a=None, b=None, v=None, sym=None, args=None, lv=False, opty=None, where=None):
        self.op, self.ty, self.a, self.b, self.v = op, ty, a, b, v
        self.sym, self.args, self.lv, self.opty, self.where = sym, args, lv, opty, where

    def __repr__(self):
        return 'N(%s %s %r)' % (self.op, self.ty, self.v)


class S:
    """Statement node."""
    __slots__ = ('op', 'e', 'a', 'b', 'c', 'body', 'items', 'where')

    def __init__(self, op, e=None, a=None, b=None, c=None, body=None, items=None, where=None):
        self.op, self.e, self.a, self.b, self.c = op, e, a, b, c
        self.body, self.items, self.where = body, items, where


class Sym:
    def __init__(self, name, kind, ty, scope, where=None):
        self.name, self.kind, self.ty, self.scope = name, kind, ty, scope
        self.where = where
        self.defined = False
        self.init = None          # globals: list of ('b', bytes) / ('a', label, off)
        self.label = None
        self.fn = None            # owning function for locals
        self.params = None        # functions
        self.body = None
        self.locals = []
        self.calls = {}           # functions called, in source order (an ordered set:
                                  # compiled output must not depend on object ids)
        self.used = False
        self.static_fn = False
        self.addr_taken = False
        self.extern = False
        self.loc = None           # codegen: storage location

    def __repr__(self):
        return 'Sym(%s)' % self.name


def is_const(e):
    return e.op in ('num', 'fnum')


def has_side(e):
    """Expression can have side effects (or depends on them)."""
    if e is None:
        return False
    if e.op in ('call', 'asg', 'inc'):
        return True
    if e.args:
        return any(has_side(x) for x in e.args)
    return has_side(e.a) or has_side(e.b)


class Parser:
    lib = False

    def __init__(self, toks):
        self.t = toks
        self.i = 0
        self.globals = {}
        self.scopes = []
        self.funcs = []            # defined functions in order
        self.gvars = []            # defined global/static objects in order
        self.strings = []          # string literal objects
        self.floats = {}           # float constant bytes -> label
        self.fn = None
        self.loops = 0
        self.rom = romfp.rom()
        self.nlab = 0

    # Tokens.
    @property
    def tok(self):
        return self.t[self.i]

    def err(self, msg, cls='syntax', tok=None):
        raise CError(msg, (tok or self.tok).where, cls)

    def peek(self, k=1):
        return self.t[min(self.i + k, len(self.t) - 1)]

    def next(self):
        t = self.t[self.i]
        self.i += 1
        return t

    def isop(self, v, k=0):
        t = self.peek(k) if k else self.tok
        return t.kind == 'op' and t.val == v

    def iskw(self, v):
        return self.tok.kind == 'kw' and self.tok.val == v

    def expect(self, v):
        t = self.tok
        if t.kind in ('op', 'kw') and t.val == v:
            self.i += 1
            return t
        if t.kind == 'op' and t.val in UNSUPPORTED_OPS:
            self.err("unsupported operator '%s'" % t.val, 'unsupported')
        self.err("expected '%s'" % v)

    def ident(self):
        t = self.tok
        if t.kind == 'id':
            if t.val in RESERVED:
                self.err("unsupported keyword '%s'" % t.val, 'unsupported')
            if len(t.val) > 15:
                self.err('identifier longer than 15 characters', 'lexical')
            self.i += 1
            return t.val
        self.err('expected identifier')

    def not_reserved(self, name, tok=None):
        # P0116: __-prefixed names and _start belong to the implementation
        if (name.startswith('__') or name == '_start') and not self.lib:
            self.err('reserved identifier %s' % name, 'declaration', tok)

    def check_tok(self):
        t = self.tok
        if t.kind == 'op' and t.val in UNSUPPORTED_OPS:
            self.err("unsupported operator '%s'" % t.val, 'unsupported')
        if t.kind == 'id' and t.val in RESERVED:
            self.err("unsupported keyword '%s'" % t.val, 'unsupported')

    # Scopes.
    def lookup(self, name):
        for sc in reversed(self.scopes):
            if name in sc:
                return sc[name]
        return self.globals.get(name)

    def is_type_start(self):
        return self.tok.kind == 'kw' and self.tok.val in ('char', 'short', 'int', 'unsigned', 'float', 'void')

    def base_type(self):
        t = self.next()
        if t.val == 'unsigned':
            u = self.next()
            if u.kind == 'kw' and u.val in ('char', 'short', 'int'):
                return {'char': 'uchar', 'short': 'ushort', 'int': 'uint'}[u.val]
            self.err("bare 'unsigned' is not a C48 type", 'type', u)
        if t.val in ('char', 'short', 'int', 'float', 'void'):
            if t.val in ('short',) and self.iskw('int'):
                self.err("'short int' is not a C48 type spelling", 'type')
            return t.val
        self.err('expected type', tok=t)

    def stars(self, ty):
        while self.isop('*'):
            self.next()
            ty = ('p', ty)
        return ty

    # Top level.
    def parse(self):
        while self.tok.kind != 'eof':
            self.external()
        for s in self.globals.values():
            if s.kind == 'fn' and s.used and not s.defined and s.static_fn:
                raise CError('static function %s used but not defined' % s.name, s.where, 'declaration')
        return self

    def external(self):
        self.check_tok()
        storage = None
        if self.iskw('static') or self.iskw('extern'):
            storage = self.next().val
        if not self.is_type_start():
            self.err('expected declaration')
        bt = self.base_type()
        first = True
        while True:
            where = self.tok.where
            ty = self.stars(bt)
            name = self.ident()
            self.not_reserved(name)
            if self.isop('('):
                ft, pnames = self.func_suffix(ty)
                sym = self.declare_fn(name, ft, storage, where)
                if first and self.isop('{'):
                    if storage == 'extern':
                        self.err('extern on a function definition', 'declaration')
                    self.func_body(sym, pnames)
                    return
            else:
                if bt == 'void' and ty == 'void':
                    self.err('void object', 'type')
                if self.isop('['):
                    ty = self.array_suffix(ty)
                init = None
                if self.isop('='):
                    self.next()
                    if storage == 'extern':
                        self.err('extern object with initializer', 'declaration')
                    # P0270: the name is in scope from the end of its declarator, so its own
                    # initializer may use it (sizeof g, &g).
                    pending = None
                    if name not in self.globals and name != 'main':
                        pending = Sym(name, 'var', ty, 'static' if storage == 'static' else 'global', where)
                        pending.label = '_' + name
                        self.globals[name] = pending
                    try:
                        init = self.initializer()
                    finally:
                        if pending is not None:
                            del self.globals[name]
                    s = self.declare_global(name, ty, storage, init, where)
                    if pending is not None:
                        # keep the object the initializer refers to
                        pending.__dict__.update(s.__dict__)
                        self.globals[name] = pending
                        self.gvars[self.gvars.index(s)] = pending
                else:
                    self.declare_global(name, ty, storage, init, where)
            first = False
            if self.isop(','):
                self.next()
                continue
            self.expect(';')
            return

    def array_suffix(self, ty):
        self.expect('[')
        if self.isop(']'):
            self.next()
            return ('a', ty, None)
        e = self.cond_expr()
        if e.op != 'num' or not is_int(e.ty):
            self.err('array bound must be an integer constant', 'type')
        n = e.v
        if signed(e.ty) and n >= 0x8000 or n == 0:
            self.err('array bound must be positive', 'type')
        self.expect(']')
        if self.isop('['):
            self.err('multidimensional arrays are unsupported', 'unsupported')
        if sizeof(ty) is None:
            self.err('array of incomplete type', 'type')
        if sizeof(ty) * n > 65535:
            self.err('array too large', 'type')
        return ('a', ty, n)

    def func_suffix(self, ret):
        self.expect('(')
        params, names = [], []
        if self.iskw('void') and self.isop(')', 1):
            self.next()
            self.next()
            return ('f', ret, ()), []
        if self.isop(')'):
            self.err('empty parameter list: use (void)', 'declaration')
        while True:
            if not self.is_type_start():
                self.check_tok()
                self.err('expected parameter type')
            where = self.tok.where
            pt = self.stars(self.base_type())
            if pt == 'void':
                self.err('void parameter', 'type')
            nm = None
            if self.tok.kind == 'id':
                nm = self.ident()
                self.not_reserved(nm)
            if self.isop('['):
                self.err('array parameters are not C48 syntax', 'unsupported')
            params.append(pt)
            names.append((nm, where))
            if self.isop(','):
                self.next()
                continue
            self.expect(')')
            break
        if is_arr(ret):
            self.err('function returning array', 'type')
        return ('f', ret, tuple(params)), names

    def declare_fn(self, name, ft, storage, where):
        s = self.globals.get(name)
        if name == 'main' and ft not in (('f', 'int', ()), ('f', 'int', ('int', ('p', ('p', 'char'))))):
            raise CError('main has the wrong type', where, 'declaration')
        if s:
            if s.kind != 'fn' or s.ty != ft:
                raise CError('conflicting declaration of %s' % name, where, 'declaration')
            if (storage == 'static') != s.static_fn:
                # extern after an external declaration is a compatible redeclaration; anything else
                # switches between internal and external linkage.
                if not (storage == 'extern' and not s.static_fn):
                    raise CError('linkage conflict for %s' % name, where, 'declaration')
            return s
        s = Sym(name, 'fn', ft, 'global', where)
        s.static_fn = storage == 'static'
        if name == 'main' and s.static_fn:
            raise CError('static main', where, 'declaration')
        self.globals[name] = s
        return s

    def declare_global(self, name, ty, storage, init, where):
        if name == 'main':
            raise CError('object named main', where, 'declaration')
        s = self.globals.get(name)
        if init is not None:
            ty = self.complete_array(ty, init, where)
        elif is_arr(ty) and ty[2] is None and storage != 'extern':
            raise CError('array without bound', where, 'type')
        if s:
            if s.kind != 'var' or (s.ty != ty and not (is_arr(s.ty) and is_arr(ty) and s.ty[1] == ty[1] and None in (s.ty[2], ty[2]))):
                raise CError('conflicting declaration of %s' % name, where, 'declaration')
            if (storage == 'static') != (s.scope == 'static') and not (storage == 'extern' and s.scope == 'global'):
                raise CError('linkage conflict for %s' % name, where, 'declaration')
            if storage != 'extern':
                if s.defined:
                    raise CError('redefinition of %s' % name, where, 'declaration')
                s.defined = True
                s.ty = ty
                s.init = self.global_init(ty, init, where)
                self.gvars.append(s)
            return s
        s = Sym(name, 'var', ty, 'static' if storage == 'static' else 'global', where)
        s.label = '_' + name
        self.globals[name] = s
        if storage != 'extern':
            s.defined = True
            s.init = self.global_init(ty, init, where)
            self.gvars.append(s)
        else:
            s.extern = True
        return s

    def complete_array(self, ty, init, where):
        if is_arr(ty) and ty[2] is None:
            if init[0] == 'list':
                return ('a', ty[1], len(init[1]))
            if init[0] == 'expr' and init[1].op == 'str' and ty[1] in BYTE:
                return ('a', ty[1], len(init[1].v) + 1)
            raise CError('cannot size array from initializer', where, 'type')
        return ty

    # Initializers.
    def initializer(self):
        if self.isop('{'):
            self.next()
            items = []
            if self.isop('}'):
                self.err('empty initializer list', 'unsupported')
            while True:
                if self.isop('{'):
                    self.err('nested initializer braces', 'unsupported')
                if self.isop('['):
                    self.err('designated initializers are unsupported', 'unsupported')
                items.append(self.assign_expr())
                if self.isop(','):
                    self.next()
                    if self.isop('}'):
                        break
                    continue
                break
            self.expect('}')
            return ('list', items)
        return ('expr', self.assign_expr())

    def const_item(self, ty, e, where):
        """One scalar constant of type ty -> list of init items."""
        e = self.convert(e, ty, 'initializer', where)
        if ty == 'float':
            if e.op != 'fnum':
                raise CError('initializer is not constant', where, 'constant-expression')
            return [('b', bytes(e.v))]
        if is_int(ty):
            if e.op != 'num':
                raise CError('initializer is not constant', where, 'constant-expression')
            n = sizeof(ty)
            return [('b', (e.v & 0xFFFF).to_bytes(2, 'little')[:n])]
        # pointer
        if e.op == 'num' and e.v == 0:
            return [('b', b'\0\0')]
        a = self.addr_const(e)
        if a is None:
            raise CError('pointer initializer is not an address constant', where, 'constant-expression')
        return [('a',) + a]

    def addr_const(self, e):
        """Address constant -> (label, offset) or None."""
        if e.op == 'conv':
            return self.addr_const(e.a)
        if e.op == 'str':
            return (self.str_label(e), 0)
        if e.op == 'addr':
            x = e.a
            if x.op == 'str':
                return (self.str_label(x), 0)
            if x.op == 'var' and x.sym.scope in ('global', 'static'):
                return (x.sym.label, 0)
            return None
        if e.op == 'var' and is_arr(e.sym.ty) and e.sym.scope in ('global', 'static'):
            return (e.sym.label, 0)
        if e.op == 'bin' and e.v in ('+', '-') and is_ptr(e.ty):
            a = self.addr_const(e.a)
            if a and e.b.op == 'num':
                k = e.b.v if e.v == '+' else -e.b.v
                return (a[0], a[1] + (k if k < 32768 else k - 65536))
        return None

    def global_init(self, ty, init, where):
        size = sizeof(ty)
        if init is None:
            return None
        if is_arr(ty):
            et = ty[1]
            if init[0] == 'expr' and init[1].op == 'str' and et in BYTE:
                b = init[1].v + b'\0'
                if len(b) > ty[2]:
                    raise CError('string does not fit array', where, 'type')
                return [('b', b + bytes(ty[2] - len(b)))]
            if init[0] != 'list':
                raise CError('array initializer needs braces', where, 'type')
            if len(init[1]) > ty[2]:
                raise CError('too many initializers', where, 'type')
            out = []
            for x in init[1]:
                out += self.const_item(et, x, where)
            rest = (ty[2] - len(init[1])) * sizeof(et)
            if rest:
                out.append(('b', bytes(rest)))
            return out
        if init[0] != 'expr':
            raise CError('braces around scalar initializer', where, 'type')
        return self.const_item(ty, init[1], where)

    # Functions.
    def func_body(self, sym, pnames):
        if sym.defined:
            self.err('redefinition of %s' % sym.name, 'declaration')
        sym.defined = True
        sym.label = '_' + sym.name
        self.fn = sym
        sym.locals = []
        sym.params = []
        scope = {}
        for pt, (nm, where) in zip(sym.ty[2], pnames):
            if nm is None:
                raise CError('parameter name required in definition', where, 'declaration')
            if nm in scope:
                raise CError('duplicate parameter %s' % nm, where, 'declaration')
            p = Sym(nm, 'var', pt, 'param', where)
            p.fn = sym
            scope[nm] = p
            sym.params.append(p)
        self.scopes = [scope]
        sym.body = self.block(fnbody=True)
        self.scopes = []
        self.fn = None
        self.funcs.append(sym)

    def block(self, fnbody=False):
        where = self.tok.where
        self.expect('{')
        if fnbody:
            sc = self.scopes[-1]
            params = dict(sc)
        else:
            sc = {}
            self.scopes.append(sc)
            params = {}
        items = []
        # declarations first
        while self.is_type_start() or self.iskw('static') or self.iskw('extern'):
            if self.iskw('static') or self.iskw('extern'):
                self.err('block-scope static/extern is unsupported', 'unsupported')
            bt = self.base_type()
            while True:
                w = self.tok.where
                ty = self.stars(bt)
                nm = self.ident()
                self.not_reserved(nm)
                if self.isop('('):
                    self.err('block-scope function declaration', 'unsupported')
                if ty == 'void':
                    self.err('void object', 'type')
                if self.isop('['):
                    ty = self.array_suffix(ty)
                if nm in sc and (not fnbody or nm in params or sc[nm] in self.fn.locals):
                    self.err('redeclaration of %s' % nm, 'declaration')
                init = None
                s = Sym(nm, 'var', ty, 'local', w)
                s.fn = self.fn
                if self.isop('='):
                    self.next()
                    sc[nm] = s          # P0270: visible in its own initializer
                    init = self.initializer()
                    ty = self.complete_array(ty, init, w)
                    s.ty = ty
                elif is_arr(ty) and ty[2] is None:
                    self.err('array without bound', 'type')
                self.fn.locals.append(s)
                if init is not None:
                    items.extend(self.local_init(s, init, w))
                sc[nm] = s
                if self.isop(','):
                    self.next()
                    continue
                self.expect(';')
                break
        while not self.isop('}'):
            if self.is_type_start():
                self.err('declaration after statement', 'unsupported')
            items.append(self.statement())
        self.next()
        if not fnbody:
            self.scopes.pop()
        return S('block', items=items, where=where)

    def local_init(self, s, init, where):
        v = N('var', s.ty, sym=s, lv=True, where=where)
        if is_arr(s.ty):
            # copied from a hidden static image on every block entry
            img = Sym('@init', 'var', s.ty, 'static', where)
            img.label = self.newlabel('I')
            img.defined = True
            img.init = self.global_init(s.ty, init, where)
            self.gvars.append(img)
            return [S('copy', a=s, b=img, where=where)]
        if init[0] != 'expr':
            raise CError('braces around scalar initializer', where, 'type')
        e = init[1]
        c = self.convert(e, s.ty, 'initializer', where)
        if not is_const(c) and self.addr_const(c) is None:
            raise CError('local initializer is not constant', where, 'constant-expression')
        return [S('expr', e=N('asg', s.ty, v, c, where=where), where=where)]

    def newlabel(self, k='L'):
        self.nlab += 1
        return '@%s%d' % (k, self.nlab)

    # Statements.
    def statement(self):
        t = self.tok
        where = t.where
        self.check_tok()
        if t.kind == 'op' and t.val == '{':
            return self.block()
        if t.kind == 'op' and t.val == ';':
            self.next()
            return S('empty', where=where)
        if t.kind == 'kw':
            k = t.val
            if k == 'if':
                self.next()
                self.expect('(')
                c = self.cond(self.expr())
                self.expect(')')
                a = self.statement()
                b = None
                if self.iskw('else'):
                    self.next()
                    b = self.statement()
                return S('if', e=c, a=a, b=b, where=where)
            if k == 'while':
                self.next()
                self.expect('(')
                c = self.cond(self.expr())
                self.expect(')')
                self.loops += 1
                body = self.statement()
                self.loops -= 1
                return S('while', e=c, body=body, where=where)
            if k == 'do':
                self.next()
                self.loops += 1
                body = self.statement()
                self.loops -= 1
                if not self.iskw('while'):
                    self.err("expected 'while'")
                self.next()
                self.expect('(')
                c = self.cond(self.expr())
                self.expect(')')
                self.expect(';')
                return S('do', e=c, body=body, where=where)
            if k == 'for':
                self.next()
                self.expect('(')
                if self.is_type_start():
                    self.err('declaration in for', 'unsupported')
                a = None if self.isop(';') else self.expr()
                self.expect(';')
                c = None if self.isop(';') else self.cond(self.expr())
                self.expect(';')
                b = None if self.isop(')') else self.expr()
                self.expect(')')
                self.loops += 1
                body = self.statement()
                self.loops -= 1
                return S('for', e=c, a=a, b=b, body=body, where=where)
            if k in ('break', 'continue'):
                self.next()
                if not self.loops:
                    self.err('%s outside a loop' % k, 'syntax')
                self.expect(';')
                return S(k, where=where)
            if k == 'return':
                self.next()
                rt = self.fn.ty[1]
                if self.isop(';'):
                    self.next()
                    if rt != 'void':
                        self.err('return without a value', 'type')
                    return S('ret', where=where)
                e = self.expr()
                if rt == 'void':
                    self.err('return with a value in void function', 'type')
                e = self.convert(e, rt, 'return', where)
                self.expect(';')
                return S('ret', e=e, where=where)
            if k == 'else':
                self.err("'else' without 'if'")
        e = self.expr()
        self.expect(';')
        return S('expr', e=e, where=where)

    def cond(self, e):
        if not is_scalar(e.ty) and not is_arr(e.ty):
            raise CError('condition is not scalar', e.where, 'type')
        return self.rvalue(e)

    # Expressions.
    def expr(self):
        e = self.assign_expr()
        if self.isop(','):
            self.err('comma operator is unsupported', 'unsupported')
        return e

    def assign_expr(self):
        lhs = self.cond_expr()
        if self.isop('='):
            t = self.next()
            rhs = self.assign_expr()
            return self.assign(lhs, rhs, t.where)
        self.check_tok()
        return lhs

    def literal_storage(self, e):
        """True for a direct designator into a string literal's storage.

        Do not follow pointer variables: their current value cannot be
        established from the syntax of the assignment.
        """
        if e.op == 'str':
            return True
        if e.op == 'deref':
            return self.literal_storage(e.a)
        if e.op == 'addr':
            return self.literal_storage(e.a)
        if e.op == 'bin' and e.opty == 'ptr':
            return self.literal_storage(e.a)
        return False

    def assign(self, lhs, rhs, where):
        if not lhs.lv or is_arr(lhs.ty) or not is_scalar(lhs.ty):
            raise CError('assignment to non-lvalue', where, 'type')
        if self.literal_storage(lhs):
            raise CError('assignment to string literal', where, 'type')
        rhs = self.convert(rhs, lhs.ty, 'assignment', where)
        return N('asg', lhs.ty, lhs, rhs, where=where)

    BINPREC = [('||',), ('&&',), ('|',), ('^',), ('&',), ('==', '!='),
               ('<', '<=', '>', '>='), ('<<', '>>'), ('+', '-'), ('*', '/', '%')]

    def cond_expr(self):
        return self.binary(0)

    def binary(self, lvl):
        if lvl == len(self.BINPREC):
            return self.unary()
        e = self.binary(lvl + 1)
        ops = self.BINPREC[lvl]
        while self.tok.kind == 'op' and self.tok.val in ops:
            t = self.next()
            r = self.binary(lvl + 1)
            e = self.mkbin(t.val, e, r, t.where)
        if self.tok.kind == 'op' and self.tok.val in ('?', ':'):
            self.err("unsupported operator '%s'" % self.tok.val, 'unsupported')
        return e

    def unary(self):
        t = self.tok
        where = t.where
        self.check_tok()
        if t.kind == 'op':
            v = t.val
            if v in ('++', '--'):
                self.next()
                e = self.unary()
                return self.incdec(e, 'pre', 1 if v == '++' else -1, where)
            if v in ('+', '-', '!', '~', '*', '&'):
                self.next()
                e = self.unary()
                return self.mkun(v, e, where)
            if v == '(' and self.peek().kind == 'kw' and self.peek().val in ('char', 'short', 'int', 'unsigned', 'float', 'void'):
                self.next()
                ty = self.stars(self.base_type())
                self.expect(')')
                e = self.unary()
                return self.cast(ty, e, where)
        if t.kind == 'kw' and t.val == 'sizeof':
            self.next()
            if self.isop('(') and self.peek().kind == 'kw' and self.peek().val in ('char', 'short', 'int', 'unsigned', 'float', 'void'):
                self.next()
                ty = self.stars(self.base_type())
                if self.isop('['):
                    self.err('array type name in sizeof', 'syntax')
                self.expect(')')
            else:
                save = self.fn
                e = self.unary()
                ty = e.ty
                self.fn = save
            if ty == 'void' or is_fn(ty) or sizeof(ty) is None:
                raise CError('invalid sizeof operand', where, 'type')
            return N('num', 'uint', v=sizeof(ty), where=where)
        return self.postfix()

    def postfix(self):
        e = self.primary()
        while True:
            t = self.tok
            if t.kind != 'op':
                break
            if t.val == '[':
                self.next()
                i = self.expr()
                self.expect(']')
                b = self.rvalue(e)
                if not is_ptr(b.ty):
                    raise CError('subscript of non-pointer', t.where, 'type')
                i = self.rvalue(i)
                if not is_int(i.ty):
                    raise CError('subscript is not an integer', t.where, 'type')
                e = self.mkderef(self.ptradd(b, i, '+', t.where), t.where)
            elif t.val in ('++', '--'):
                self.next()
                e = self.incdec(e, 'post', 1 if t.val == '++' else -1, t.where)
            elif t.val == '(':
                raise CError('call of non-function', t.where, 'type')
            elif t.val in ('.', '->'):
                self.err("unsupported operator '%s'" % t.val, 'unsupported')
            else:
                break
        return e

    def primary(self):
        t = self.next()
        w = t.where
        if t.kind == 'int':
            v, ty = t.val
            return N('num', 'uint' if ty == 'unsigned int' else 'int', v=v, where=w)
        if t.kind == 'char':
            return N('num', 'int', v=t.val, where=w)
        if t.kind == 'float':
            try:
                b = self.rom.from_text(t.val)
            except romfp.FPError:
                raise CError('floating literal out of range', w, 'literal-range')
            return N('fnum', 'float', v=b, where=w)
        if t.kind == 'str':
            s = t.val
            while self.tok.kind == 'str':
                s += self.next().val
            n = N('str', ('a', 'char', len(s) + 1), v=s, lv=True, where=w)
            n.sym = None
            self.strings.append(n)
            return n
        if t.kind == 'op' and t.val == '(':
            e = self.expr()
            self.expect(')')
            return e
        if t.kind == 'id':
            self.i -= 1
            name = self.ident()
            s = self.lookup(name)
            if s is None:
                raise CError('undeclared identifier %s' % name, w, 'declaration')
            if s.kind == 'fn':
                if not self.isop('('):
                    raise CError('function %s used as a value' % name, w, 'type')
                return self.call(s, w)
            s.used = True
            return N('var', s.ty, sym=s, lv=True, where=w)
        if t.kind == 'op' and t.val in UNSUPPORTED_OPS:
            raise CError("unsupported operator '%s'" % t.val, w, 'unsupported')
        if t.kind == 'id' or t.kind == 'kw':
            raise CError("unexpected '%s'" % t.val, w, 'syntax')
        raise CError('expected expression', w, 'syntax')

    def call(self, s, where):
        self.expect('(')
        args = []
        if not self.isop(')'):
            while True:
                args.append(self.assign_expr())
                if self.isop(','):
                    self.next()
                    continue
                break
        self.expect(')')
        pts = s.ty[2]
        if len(args) != len(pts):
            raise CError('%s takes %d arguments' % (s.name, len(pts)), where, 'type')
        args = [self.convert(a, pt, 'argument', where) for a, pt in zip(args, pts)]
        # ZX-UX screen/terminal calls have fixed numeric argument bounds. Reject only
        # values proven constant after folding; runtime checks still handle variables
        # and expressions not known at compile time.
        if not s.defined:
            bounds = {
                'ink': ((0, 7),), 'paper': ((0, 7),),
                'border': ((0, 7),), 'bright': ((0, 1),),
                'flash': ((0, 1),), 'inverse': ((0, 1),),
                'over': ((0, 1),), 'screen': ((0, 1),),
                'print_at': ((0, 23), (0, 63)),
                'plot': ((0, 255), (0, 175)),
                'point': ((0, 255), (0, 175)),
                'udg_define': ((0, 31),),
                'udg_get': ((0, 31),),
                'udg_clear': ((0, 31),),
                'udg_draw': ((0, 31), (0, 23), (0, 31)),
                'udg_draw_2x2': ((0, 28), (0, 22), (0, 30)),
            }.get(s.name, ())
            for i, ((low, high), arg) in enumerate(zip(bounds, args), 1):
                if arg.op == 'num' and not low <= arg.v <= high:
                    raise CError('%s argument %d constant outside %d..%d' %
                                 (s.name, i, low, high), arg.where or where,
                                 'constant-expression')
        s.used = True
        if self.fn:
            self.fn.calls[s] = None
        return N('call', s.ty[1], sym=s, args=args, where=where)

    # Typing helpers.
    def rvalue(self, e):
        """Array to pointer decay."""
        if is_arr(e.ty):
            if e.op == 'var':
                e.sym.addr_taken = True
            return N('addr', ('p', e.ty[1]), e, where=e.where, v='arr')
        return e

    def mkderef(self, p, where):
        if not is_ptr(p.ty):
            raise CError('dereference of non-pointer', where, 'type')
        if p.ty[1] == 'void':
            raise CError('dereference of void *', where, 'type')
        if p.op == 'addr' and p.v != 'arr':
            return p.a
        return N('deref', p.ty[1], p, lv=True, where=where)

    def cast(self, ty, e, where):
        e = self.rvalue(e)
        if ty == 'void':
            raise CError('(void) casts are unsupported', where, 'unsupported')
        if is_ptr(ty) or is_ptr(e.ty):
            raise CError('pointer casts are unsupported', where, 'unsupported')
        if not is_arith(e.ty):
            raise CError('invalid cast', where, 'type')
        return self.conv(e, ty, where)

    def conv(self, e, ty, where):
        """Arithmetic conversion with constant folding."""
        if e.ty == ty:
            return e
        if e.op == 'num' and is_int(ty):
            return N('num', ty, v=self.wrap(e.v, ty), where=where)
        if e.op == 'num' and ty == 'float':
            return N('fnum', 'float', v=self.rom.from_int(e.v, signed(e.ty)), where=where)
        if e.op == 'fnum' and is_int(ty):
            try:
                v = self.rom.to_int(e.v, signed(ty))
            except romfp.FPError:
                raise CError('constant float conversion out of range', where, 'constant-expression')
            if ty in BYTE:
                v &= 255
            return N('num', ty, v=v, where=where)
        return N('conv', ty, e, where=where)

    @staticmethod
    def wrap(v, ty):
        if ty in BYTE:
            return v & 0xFF
        return v & 0xFFFF

    def convert(self, e, ty, ctx, where):
        """Implicit conversion for assignment / argument / return / initializer."""
        e = self.rvalue(e)
        if e.ty == 'void':
            raise CError('void value used', where, 'type')
        if is_arith(ty) and is_arith(e.ty):
            return self.conv(e, ty, where)
        if is_ptr(ty):
            if is_ptr(e.ty):
                if e.ty == ty or ty[1] == 'void' or e.ty[1] == 'void':
                    if e.ty != ty:
                        return N('conv', ty, e, where=where, v='ptr') if e.op != 'conv' else N('conv', ty, e.a, where=where, v='ptr')
                    return e
                raise CError('incompatible pointer types in %s (%s from %s)' % (ctx, tname(ty), tname(e.ty)), where, 'type')
            if e.op == 'num' and e.v == 0 and is_int(e.ty):
                return N('num', ty, v=0, where=where)
        raise CError('incompatible types in %s (%s from %s)' % (ctx, tname(ty), tname(e.ty)), where, 'type')

    def truth(self, e):
        e = self.rvalue(e)
        if not is_scalar(e.ty):
            raise CError('operand is not scalar', e.where, 'type')
        return e

    def mkun(self, op, e, where):
        if op == '&':
            if e.op == 'var' and is_arr(e.ty) or e.op == 'str':
                raise CError('address of array', where, 'type')
            if not e.lv:
                raise CError('address of non-lvalue', where, 'type')
            if e.op == 'deref':
                return e.a
            if e.op == 'var':
                e.sym.addr_taken = True
            return N('addr', ('p', e.ty), e, where=where)
        if op == '*':
            return self.mkderef(self.rvalue(e), where)
        e = self.rvalue(e)
        if op == '!':
            e = self.truth(e)
            if e.op == 'num':
                return N('num', 'int', v=int(e.v == 0), where=where)
            if e.op == 'fnum':
                return N('num', 'int', v=int(self.rom.is_zero(e.v)), where=where)
            return N('not', 'int', e, where=where)
        if not is_arith(e.ty):
            raise CError("bad operand for unary '%s'" % op, where, 'type')
        if op == '~':
            if not is_int(e.ty):
                raise CError("'~' needs an integer", where, 'type')
            pt = promote(e.ty)
            e = self.conv(e, pt, where)
            if e.op == 'num':
                return N('num', pt, v=~e.v & 0xFFFF, where=where)
            return N('com', pt, e, where=where)
        pt = promote(e.ty) if e.ty != 'float' else 'float'
        e = self.conv(e, pt, where)
        if op == '+':
            return N('conv', pt, e, where=where) if e.op not in ('num', 'fnum') and False else e
        if e.op == 'num':
            return N('num', pt, v=-e.v & 0xFFFF, where=where)
        if e.op == 'fnum':
            return N('fnum', 'float', v=self.rom.op(romfp.NEG, e.v), where=where)
        return N('neg', pt, e, where=where)

    def incdec(self, e, kind, d, where):
        if not e.lv or not is_scalar(e.ty) or e.op == 'str':
            raise CError('++/-- of non-lvalue', where, 'type')
        step = 1
        if is_ptr(e.ty):
            if e.ty[1] == 'void':
                raise CError('++/-- of void *', where, 'type')
            step = sizeof(e.ty[1])
        return N('inc', e.ty, e, v=(kind, d * step), where=where)

    def ptradd(self, p, i, op, where):
        size = sizeof(p.ty[1])
        if size is None:
            raise CError('arithmetic on void *', where, 'type')
        i = self.conv(i, promote(i.ty), where)
        if size != 1:
            i = self.mkbin('*', i, N('num', 'int', v=size, where=where), where)
        if i.op == 'num' and i.v == 0:
            return p
        # fold &a + k
        return N('bin', p.ty, p, i, v=op, opty='ptr', where=where)

    def mkbin(self, op, a, b, where):
        a = self.rvalue(a)
        b = self.rvalue(b)
        if a.ty == 'void' or b.ty == 'void':
            raise CError('void value used', where, 'type')
        if op in ('&&', '||'):
            a, b = self.truth(a), self.truth(b)
            if is_const(a):
                av = not self.zero(a)
                if op == '&&' and not av:
                    return N('num', 'int', v=0, where=where)
                if op == '||' and av:
                    return N('num', 'int', v=1, where=where)
                if is_const(b):
                    return N('num', 'int', v=int(not self.zero(b)), where=where)
                return N('ne0', 'int', b, where=where)
            return N('and' if op == '&&' else 'or', 'int', a, b, where=where)
        if op in ('+', '-') and (is_ptr(a.ty) or is_ptr(b.ty)):
            if op == '+' and is_ptr(b.ty) and is_int(a.ty):
                a, b = b, a
            if is_ptr(a.ty) and is_int(b.ty):
                return self.ptradd(a, b, op, where)
            if op == '-' and is_ptr(a.ty) and is_ptr(b.ty):
                if a.ty != b.ty or a.ty[1] == 'void':
                    raise CError('subtraction of incompatible pointers', where, 'type')
                d = N('bin', 'int', a, b, v='-', opty='int', where=where)
                size = sizeof(a.ty[1])
                if size == 1:
                    return d
                return self.mkbin('/', d, N('num', 'int', v=size), where)
            raise CError('invalid pointer arithmetic', where, 'type')
        if op in ('==', '!=', '<', '<=', '>', '>='):
            if is_ptr(a.ty) or is_ptr(b.ty):
                if is_ptr(a.ty) and is_ptr(b.ty):
                    if a.ty != b.ty and not (op in ('==', '!=') and 'void' in (a.ty[1], b.ty[1])):
                        raise CError('comparison of incompatible pointers', where, 'type')
                    if op not in ('==', '!=') and a.ty[1] == 'void':
                        # P0535: relational operators need non-void object pointers
                        raise CError('relational comparison of void pointers', where, 'type')
                elif op in ('==', '!=') and (b.op == 'num' and b.v == 0 and is_int(b.ty) or a.op == 'num' and a.v == 0 and is_int(a.ty)):
                    pass
                else:
                    raise CError('comparison of pointer and integer', where, 'type')
                return N('cmp', 'int', a, b, v=op, opty='uint', where=where)
            if not (is_arith(a.ty) and is_arith(b.ty)):
                raise CError('invalid comparison', where, 'type')
            ct = common(a.ty, b.ty)
            a, b = self.conv(a, ct, where), self.conv(b, ct, where)
            if is_const(a) and is_const(b):
                return N('num', 'int', v=int(self.cmpconst(op, a, b, ct)), where=where)
            return N('cmp', 'int', a, b, v=op, opty=ct, where=where)
        if not (is_arith(a.ty) and is_arith(b.ty)):
            raise CError("invalid operands to '%s'" % op, where, 'type')
        if op in ('<<', '>>'):
            if not (is_int(a.ty) and is_int(b.ty)):
                raise CError('shift needs integers', where, 'type')
            lt = a.ty
            b = self.conv(b, promote(b.ty), where)
            if a.op == 'num' and b.op == 'num':
                return N('num', lt, v=self.shift(op, a.v, b.v, lt), where=where)
            return N('bin', lt, a, b, v=op, opty=lt, where=where)
        if op in ('%', '&', '|', '^') and not (is_int(a.ty) and is_int(b.ty)):
            raise CError("'%s' needs integers" % op, where, 'type')
        ct = common(a.ty, b.ty)
        a, b = self.conv(a, ct, where), self.conv(b, ct, where)
        if is_const(a) and is_const(b):
            return self.fold(op, a, b, ct, where)
        # algebraic identities that keep evaluation semantics
        if ct != 'float' and b.op == 'num':
            if (op in ('+', '-', '|', '^') and b.v == 0) or (op in ('*', '/') and b.v == 1):
                return a
        return N('bin', ct, a, b, v=op, opty=ct, where=where)

    def zero(self, e):
        if e.op == 'fnum':
            return self.rom.is_zero(e.v)
        return e.v == 0

    @staticmethod
    def sval(v, ty):
        if ty in ('int', 'short') and v >= 0x8000:
            return v - 0x10000
        return v

    def cmpconst(self, op, a, b, ct):
        if ct == 'float':
            c = self.rom.compare(a.v, b.v)
            x, y = c, 0
        else:
            x, y = self.sval(a.v, ct), self.sval(b.v, ct)
        return {'==': x == y, '!=': x != y, '<': x < y, '<=': x <= y, '>': x > y, '>=': x >= y}[op]

    def shift(self, op, v, n, lt):
        bits = 8 if lt in BYTE else 16
        n &= bits - 1
        mask = (1 << bits) - 1
        if op == '<<':
            return (v << n) & mask
        if signed(lt):
            sv = v - 0x10000 if v & 0x8000 else v
            return (sv >> n) & mask
        return (v & mask) >> n

    def fold(self, op, a, b, ct, where):
        if ct == 'float':
            fop = {'+': romfp.ADD, '-': romfp.SUB, '*': romfp.MUL, '/': romfp.DIV}[op]
            try:
                return N('fnum', 'float', v=self.rom.op(fop, a.v, b.v), where=where)
            except romfp.FPError:
                raise CError('floating constant expression error', where, 'constant-expression')
        x, y = a.v, b.v
        if op in ('/', '%'):
            if y == 0:
                raise CError('division by zero in constant expression', where, 'constant-expression')
            if ct == 'int':
                sx, sy = self.sval(x, 'int'), self.sval(y, 'int')
                q = abs(sx) // abs(sy)
                if (sx < 0) != (sy < 0):
                    q = -q
                r = sx - q * sy
                v = q if op == '/' else r
            else:
                v = x // y if op == '/' else x % y
        else:
            v = {'+': x + y, '-': x - y, '*': x * y, '&': x & y, '|': x | y, '^': x ^ y}[op]
        return N('num', ct, v=v & 0xFFFF, where=where)

    def str_label(self, e):
        if e.sym is None:
            e.sym = self.newlabel('S')
        return e.sym


def parse(toks, lib=False):
    p = Parser(toks)
    p.lib = lib
    return p.parse()
