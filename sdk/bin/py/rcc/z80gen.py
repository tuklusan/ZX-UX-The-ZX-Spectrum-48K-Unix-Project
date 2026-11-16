# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""rcc: size-optimising native Z80 back end.

ZX-UX C calling convention for rcc:
  * arguments are evaluated left to right; arguments 1..n-1 are pushed in that
    order, argument n is passed in HL; the callee removes the pushed words
  * int/char/pointer results in HL (char: H = 0); float results in @fac
  * float arguments are passed as a pointer to the value; the callee copies
  * IX is preserved; everything else is clobbered
Functions outside a recursive call cycle keep parameters and locals in a static
overlay area (@ovl), laid out along the call graph; recursive functions use an
IX frame built by @enter.
"""
from .types import (BYTE, is_int, is_ptr, is_arr, sizeof, signed, align_of)
from .lex import CError
from . import romfp

FOP = {'+': romfp.ADD, '-': romfp.SUB, '*': romfp.MUL, '/': romfp.DIV}


def esize(ty):
    """Storage size of a scalar slot."""
    return sizeof(ty)


def isbyte(ty):
    return ty in BYTE


class Func:
    def __init__(self, sym):
        self.sym = sym
        self.recursive = False
        self.size = 0          # static area size
        self.frame = 0         # frame locals size (recursive)
        self.base = 0
        self.ftemps = []       # free float temps
        self.label = '@A' + sym.name


class Gen:
    def __init__(self, prog, opts=None):
        self.p = prog
        self.out = []
        self.data = []
        self.bss = []
        self.nl = 0
        self.fconst = {}
        self.opts = opts or {}
        self.funcs = {f: Func(f) for f in prog.funcs}

    # Utilities.
    def emit(self, *ins):
        for i in ins:
            self.out.append('\t' + i)

    def label(self, l):
        self.out.append(l + ':')

    def newl(self):
        self.nl += 1
        return '@l%d' % self.nl

    def fconst_label(self, b):
        b = bytes(b)
        if b not in self.fconst:
            self.fconst[b] = '@f%d' % len(self.fconst)
        return self.fconst[b]

    def err(self, msg, e):
        raise CError(msg, getattr(e, 'where', None), 'type')

    # Analysis.
    def analyze(self):
        funcs = self.p.funcs
        idx = {}
        low = {}
        stack = []
        onst = set()
        sccs = []
        counter = [0]
        import sys
        sys.setrecursionlimit(10000)

        def strong(v):
            idx[v] = low[v] = counter[0]
            counter[0] += 1
            stack.append(v)
            onst.add(v)
            for w in v.calls:
                if w not in self.funcs:
                    continue
                if w not in idx:
                    strong(w)
                    low[v] = min(low[v], low[w])
                elif w in onst:
                    low[v] = min(low[v], idx[w])
            if low[v] == idx[v]:
                comp = []
                while True:
                    w = stack.pop()
                    onst.discard(w)
                    comp.append(w)
                    if w is v:
                        break
                sccs.append(comp)
        for f in funcs:
            if f not in idx:
                strong(f)
        self.scc_of = {}
        for comp in sccs:
            rec = len(comp) > 1 or comp[0] in comp[0].calls
            for f in comp:
                self.funcs[f].recursive = rec
                self.scc_of[f] = tuple(comp)
        self.sccs = sccs        # reverse topological order (callees first)
        # storage for params/locals
        for f in funcs:
            F = self.funcs[f]
            if F.recursive:
                n = len(f.params)
                for i, p in enumerate(f.params):
                    if i == n - 1:
                        p.loc = ('fr', -2, 2)
                    else:
                        p.loc = ('fr', 4 + 2 * (n - 2 - i), 2)
                F.frame = 2
                F.fparams = []
                for p in f.params:
                    if p.ty == 'float':
                        ptrloc = p.loc
                        p.loc = self.frame_alloc(F, 5)
                        F.fparams.append((ptrloc, p.loc))
                for l in f.locals:
                    l.loc = self.frame_alloc(F, sizeof(l.ty), align_of(l.ty))
            else:
                for p in f.params:
                    p.loc = self.static_alloc(F, 5 if p.ty == 'float' else 2, align_of(p.ty))
                for l in f.locals:
                    l.loc = self.static_alloc(F, sizeof(l.ty), align_of(l.ty))
        # globals
        for s in self.p.gvars:
            s.loc = ('st', s.label, sizeof(s.ty))
        for s in self.p.globals.values():
            if s.kind == 'var' and s.loc is None:
                s.loc = ('st', s.label, sizeof(s.ty))

    def frame_alloc(self, F, size, align=1):
        # IX is even (the stack stays word aligned: frames are rounded to even
        # sizes), so an even offset is an even address.
        F.frame += size
        F.frame += F.frame & (align - 1)
        return ('fr', -F.frame, size)

    def static_alloc(self, F, size, align=1):
        # areas start at even offsets of the word-aligned @ovl
        off = F.size + (F.size & (align - 1))
        F.size = off + size
        return ('st', '%s+%d' % (F.label, off) if off else F.label, size)

    def ftemp(self):
        F = self.F
        if F.ftemps:
            return F.ftemps.pop()
        if F.recursive:
            return self.frame_alloc(F, 5)
        return self.static_alloc(F, 5)

    def ffree(self, t):
        if t is not None and t[0] in ('st', 'fr') and t not in self.F.ftemps:
            self.F.ftemps.append(t)

    def layout_overlay(self):
        """Offsets of static areas: each function after all its callers."""
        callers = {f: set() for f in self.funcs}
        for f in self.funcs:
            for g in f.calls:
                if g in self.funcs:
                    callers[g].add(f)
        order = list(reversed(self.sccs))   # callers first
        base = {}
        for comp in order:
            b = 0
            for f in comp:
                for c in callers[f]:
                    if c in comp:
                        continue
                    b = max(b, base[c] + self.funcs[c].size)
            b += b & 1                  # every area starts word aligned
            # members of a recursive cycle have no static area; non-recursive
            # single members.
            for f in comp:
                base[f] = b
        total = 0
        for f, F in self.funcs.items():
            F.base = base[f]
            total = max(total, F.base + F.size)
        return total

    # Program.
    def prune(self):
        """Keep only functions and objects reachable from main.  A separately
        compiled object (rcc -c) also keeps everything with external linkage:
        other objects may use it (P0287)."""
        main = self.p.globals.get('main')
        if not (main and main.defined):
            return
        module = self.opts.get('module')
        keep = set()
        work = [main]
        if module:
            work += [f for f in self.p.funcs if not f.static_fn]
        while work:
            f = work.pop()
            if f in keep:
                continue
            keep.add(f)
            work += [g for g in f.calls if g.defined and g.body is not None]
        self.p.funcs = [f for f in self.p.funcs if f in keep]
        self.funcs = {f: Func(f) for f in self.p.funcs}
        refs = set()

        def walk(x):
            if x is None:
                return
            if isinstance(x, list):
                for y in x:
                    walk(y)
                return
            if hasattr(x, 'sym') and x.__class__.__name__ == 'N':
                if x.op == 'var' and x.sym.scope in ('global', 'static'):
                    refs.add(x.sym)
                walk(x.a)
                walk(x.b)
                walk(x.args)
                return
            # statement
            if x.op == 'copy':
                refs.add(x.b)
                return
            for k in ('e', 'a', 'b', 'c', 'body', 'items'):
                v = getattr(x, k)
                if v is not None and not isinstance(v, (str, int)):
                    walk(v)
        for f in self.p.funcs:
            walk(f.body)
        labels = {s.label: s for s in self.p.gvars}
        work = list(refs)
        while work:
            g = work.pop()
            for it in g.init or ():
                if it[0] == 'a' and it[1] in labels and labels[it[1]] not in refs:
                    refs.add(labels[it[1]])
                    work.append(labels[it[1]])
        self.p.gvars = [g for g in self.p.gvars if g in refs or
                        (g.scope == 'global' and (module or self.opts.get('keep_globals')))]

    def generate(self):
        self.prune()
        self.analyze()
        for f in self.p.funcs:
            self.function(f)
        total = self.layout_overlay()
        lines = list(self.out)
        out = ['\tsection text']
        out += lines
        out.append('\tsection data')
        out += self.data_lines()
        out.append('\tsection bss')
        out += self.bss_lines()
        if total:
            out += ['\talign 2', '@ovl:\tds %d' % total]
        for f, F in self.funcs.items():
            if F.size:
                out.append('%s\tequ @ovl+%d' % (F.label, F.base))
        exports = [f.label for f in self.p.funcs if not f.static_fn]
        exports += [s.label for s in self.p.gvars if s.scope == 'global' and s.name != '@init']
        main = self.p.globals.get('main')
        if main is not None and main.defined:
            exports.append('@main')
            if main.ty[2]:
                out += ['\tsection text', '@main:\tpop bc', '\tpush de', '\tpush bc', '\tjp _main']
            else:
                out.append('@main\tequ _main')
        # the heap of a whole program that uses malloc or free (a separately compiled object gets
        # the library's default heap from libc48.ssa).
        heapfn = [self.p.globals.get(n) for n in ('malloc', 'free')]
        if any(h is not None and h.used for h in heapfn) and main is not None \
                and not self.opts.get('module'):
            heap = self.opts.get('heap', 1024)
            region = heap + 256
            exports += ['___heap', '___heapw', '___heapsz']
            out += ['\tsection data', '\talign 2', '___heapw:\tdw %d' % (region // 2),
                    '___heapsz:\tdw %d' % heap, '\tsection bss', '\talign 2', '___heap:\tds %d' % region]
        if exports:
            out.insert(0, '\tglobal ' + ','.join(exports))
        return '\n'.join(out) + '\n'

    def data_lines(self):
        out = []
        for s in self.p.gvars:
            if s.init is None:
                continue
            if align_of(s.ty) > 1:
                out.append('\talign %d' % align_of(s.ty))
            out.append('%s:' % s.label)
            out += self.init_lines(s.init)
        # Each non-adjacent literal occurrence is an independent static array. C48 Rev 0.11
        # section 15 forbids identical/suffix address pooling.
        for literal in self.p.strings:
            if literal.sym is not None:
                out.append('%s:' % literal.sym)
                out += self.bytes_lines(literal.v + b'\0')
        for b, l in self.fconst.items():
            out.append('%s:\tdb %s' % (l, ','.join(str(x) for x in b)))
        return out

    def bss_lines(self):
        out = []
        for s in self.p.gvars:
            if s.init is None:
                if align_of(s.ty) > 1:
                    out.append('\talign %d' % align_of(s.ty))
                out.append('%s:\tds %d' % (s.label, sizeof(s.ty)))
        return out

    def init_lines(self, items):
        out = []
        for it in items:
            if it[0] == 'b':
                out += self.bytes_lines(it[1])
            else:
                lab, off = it[1], it[2]
                out.append('\tdw %s%s' % (lab, '+%d' % off if off > 0 else ('-%d' % -off if off < 0 else '')))
        return out

    @staticmethod
    def bytes_lines(b):
        out = []
        # zero runs as ds
        i = 0
        while i < len(b):
            if b[i] == 0:
                j = i
                while j < len(b) and b[j] == 0:
                    j += 1
                if j - i >= 4:
                    out.append('\tds %d' % (j - i))
                    i = j
                    continue
            j = min(len(b), i + 16)
            k = i
            while k < j and not (b[k] == 0 and k + 3 < len(b) and b[k:k + 4] == bytes(4)):
                k += 1
            if k == i:
                k = i + 1
            out.append('\tdb ' + ','.join(str(x) for x in b[i:k]))
            i = k
        return out

    # Functions.
    def function(self, f):
        F = self.funcs[f]
        self.F = F
        self.f = f
        self.loops = []
        self.label(f.label)
        n = len(f.params)
        if F.recursive:
            self.ret_label = self.newl()
            fixup = len(self.out)
            self.emit('call @enter', 'dw 0')
            for ptrloc, loc in F.fparams:
                self.load_hl_loc(ptrloc, 2)
                self.fr_de_keep(loc)
                self.emit('call @fmov')
        else:
            if n:
                last = f.params[-1]
                self.store_param(last, 'hl')
                if n > 1:
                    self.emit('pop bc')                 # return address.
                    for p in reversed(f.params[:-1]):
                        self.emit('pop hl')
                        if p.ty == 'float' and p.loc[0] == 'st':
                            # @fmov uses BC: keep the return address on the stack
                            self.emit('push bc')
                            self.store_param(p, 'hl')
                            self.emit('pop bc')
                        else:
                            self.store_param(p, 'hl')
                    self.emit('push bc')
        self.stmt(f.body)
        # fall off the end
        if f.ty[1] != 'void':
            if not self.out[-1].strip().startswith(('ret', 'jp @leave')) or True:
                self.emit('jp @noret')
        else:
            self.do_return()
        if F.recursive:
            self.label(self.ret_label)
            k = max(n - 1, 0)
            self.emit('jp @leave%d' % k if k <= 3 else 'ld a,%d' % k)
            if k > 3:
                self.emit('jp @leave')
            F.frame += F.frame & 1      # keep SP even
            self.out[fixup + 1] = '\tdw %d' % (F.frame - 2)
        self.F = None

    def store_param(self, p, reg):
        if p.loc[0] == 'st':
            if p.ty == 'float':
                self.emit('ld de,%s' % p.loc[1], 'call @fmov')
            elif p.used or True:
                self.emit('ld (%s),hl' % p.loc[1])

    def do_return(self):
        if self.F.recursive:
            self.emit('j %s' % self.ret_label)
        else:
            self.emit('ret')

    # Statements.
    def stmt(self, s):
        op = s.op
        if op == 'block':
            for x in s.items:
                self.stmt(x)
        elif op == 'empty':
            pass
        elif op == 'expr':
            self.gx(s.e, want=False)
        elif op == 'copy':
            loc = s.a.loc
            self.emit('ld hl,%s' % s.b.label)
            self.addr_de(loc)
            self.emit('ld bc,%d' % sizeof(s.a.ty), 'ldir')
        elif op == 'if':
            lf = self.newl()
            self.gcond(s.e, lf, False)
            self.stmt(s.a)
            if s.b is not None:
                le = self.newl()
                if not self.ends_jump():
                    self.emit('j %s' % le)
                self.label(lf)
                self.stmt(s.b)
                self.label(le)
            else:
                self.label(lf)
        elif op == 'while':
            top, brk = self.newl(), self.newl()
            cont = self.newl()
            # condition at the bottom: jump into it
            self.emit('j %s' % cont)
            self.label(top)
            self.loops.append((brk, cont))
            self.stmt(s.body)
            self.loops.pop()
            self.label(cont)
            self.gcond(s.e, top, True)
            self.label(brk)
        elif op == 'do':
            top, brk, cont = self.newl(), self.newl(), self.newl()
            self.label(top)
            self.loops.append((brk, cont))
            self.stmt(s.body)
            self.loops.pop()
            self.label(cont)
            self.gcond(s.e, top, True)
            self.label(brk)
        elif op == 'for':
            if s.a is not None:
                self.gx(s.a, want=False)
            top, brk, cont, test = self.newl(), self.newl(), self.newl(), self.newl()
            if s.e is not None:
                self.emit('j %s' % test)
            self.label(top)
            self.loops.append((brk, cont))
            self.stmt(s.body)
            self.loops.pop()
            self.label(cont)
            if s.b is not None:
                self.gx(s.b, want=False)
            self.label(test)
            if s.e is not None:
                self.gcond(s.e, top, True)
            else:
                self.emit('j %s' % top)
            self.label(brk)
        elif op == 'break':
            self.emit('j %s' % self.loops[-1][0])
        elif op == 'continue':
            self.emit('j %s' % self.loops[-1][1])
        elif op == 'ret':
            if s.e is not None:
                if s.e.ty == 'float':
                    self.gf_into(s.e, ('st', '@fac', 5))
                else:
                    self.gx(s.e)
            self.do_return()
        else:
            raise AssertionError(op)

    def ends_jump(self):
        last = self.out[-1].strip() if self.out else ''
        return last.startswith(('ret', 'jp @noret')) or (last.startswith('j ') and ',' not in last)

    # Locations.
    def ixd(self, d):
        return '(ix%+d)' % d

    def load_hl_loc(self, loc, size):
        k, a = loc[0], loc[1]
        if k == 'st':
            self.emit('ld hl,(%s)' % a)
            if size == 1:
                self.emit('ld h,0')
        else:
            if size == 1:
                self.emit('ld l,%s' % self.ixd(a), 'ld h,0')
            else:
                self.emit('ld l,%s' % self.ixd(a), 'ld h,%s' % self.ixd(a + 1))

    def load_de_loc(self, loc, size):
        k, a = loc[0], loc[1]
        if k == 'st':
            self.emit('ld de,(%s)' % a)
            if size == 1:
                self.emit('ld d,0')
        else:
            if size == 1:
                self.emit('ld e,%s' % self.ixd(a), 'ld d,0')
            else:
                self.emit('ld e,%s' % self.ixd(a), 'ld d,%s' % self.ixd(a + 1))

    def store_hl_loc(self, loc, size):
        k, a = loc[0], loc[1]
        if k == 'st':
            if size == 1:
                self.emit('ld a,l', 'ld (%s),a' % a)
            else:
                self.emit('ld (%s),hl' % a)
        else:
            self.emit('ld %s,l' % self.ixd(a))
            if size != 1:
                self.emit('ld %s,h' % self.ixd(a + 1))

    def addr_hl(self, loc):
        if loc[0] == 'st':
            self.emit('ld hl,%s' % loc[1])
        else:
            self.emit('push ix', 'pop hl')
            if loc[1]:
                self.emit('ld de,%d' % loc[1], 'add hl,de')

    def addr_de(self, loc):
        if loc[0] == 'st':
            self.emit('ld de,%s' % loc[1])
        else:
            self.emit('push ix', 'pop de')
            if loc[1]:
                self.emit('ld hl,%d' % loc[1], 'add hl,de', 'ex de,hl')

    # Operands.
    def simple(self, e):
        """Side-effect-free operand loadable straight into HL or DE:
        ('imm', text) or ('st', addr, size) or ('fr', d, size)."""
        op = e.op
        if op == 'num':
            return ('imm', str(e.v))
        if op == 'str':
            return ('imm', self.p.str_label(e))
        if op == 'var':
            if is_arr(e.ty):
                return None
            return e.sym.loc[:2] + (sizeof(e.ty),)
        if op == 'addr':
            x = e.a
            if x.op == 'str':
                return ('imm', self.p.str_label(x))
            if x.op == 'var' and x.sym.loc[0] == 'st':
                return ('imm', x.sym.loc[1])
            return None
        if op == 'conv' and is_int(e.ty) and is_int(e.a.ty) or op == 'conv' and e.v == 'ptr':
            s = self.simple(e.a)
            if s is None:
                return None
            if isbyte(e.ty) and not isbyte(e.a.ty):
                if s[0] == 'imm':
                    return None
                return s[:2] + (1,)
            return s
        if op == 'deref':
            p = e.a
            if p.op == 'bin' and p.v == '+' and p.b.op == 'num':
                base = self.simple(p.a)
                if base and base[0] == 'imm':
                    return ('st', '%s+%d' % (base[1], p.b.v), sizeof(e.ty))
            base = self.simple(p)
            if base and base[0] == 'imm':
                return ('st', base[1], sizeof(e.ty))
        return None

    def load_hl(self, s):
        if s[0] == 'imm':
            self.emit('ld hl,%s' % s[1])
        else:
            self.load_hl_loc(s[:2], s[2])

    def load_de(self, s):
        if s[0] == 'imm':
            self.emit('ld de,%s' % s[1])
        else:
            self.load_de_loc(s[:2], s[2])

    # Expressions.
    def gx(self, e, want=True):
        """Integer/pointer expression -> HL (byte types: H = 0)."""
        op = e.op
        if e.ty == 'float' and op not in ('call', 'asg', 'inc'):
            # value used only for side effects
            t = self.ftemp()
            self.gf_into(e, t)
            self.ffree(t)
            return
        s = self.simple(e)
        if s is not None:
            if want:
                self.load_hl(s)
            return
        if op == 'addr':
            x = e.a
            if x.op == 'var':
                self.addr_hl(x.sym.loc)
                return
            raise AssertionError('addr of %s' % x.op)
        if op == 'deref':
            self.gx(e.a)
            self.load_ind(e.ty)
            return
        if op == 'conv':
            return self.gconv(e, want)
        if op == 'bin':
            return self.gbin(e)
        if op in ('cmp', 'and', 'or', 'not', 'ne0'):
            if op == 'not' and e.a.ty != 'float':
                self.gx(e.a)
                self.emit('call @not' if not isbyte(e.a.ty) else 'call @notb')
                return
            lf, le = self.newl(), self.newl()
            self.gcond(e, lf, False)
            self.emit('ld hl,1', 'j %s' % le)
            self.label(lf)
            self.emit('ld hl,0')
            self.label(le)
            return
        if op == 'neg':
            self.gx(e.a)
            self.emit('call @neg')
            return
        if op == 'com':
            self.gx(e.a)
            self.emit('call @com')
            return
        if op == 'asg':
            return self.gasg(e, want)
        if op == 'inc':
            return self.ginc(e, want)
        if op == 'call':
            return self.gcall(e, want)
        raise AssertionError('gx %s' % op)

    def load_ind(self, ty):
        if isbyte(ty):
            self.emit('ld l,(hl)', 'ld h,0')
        else:
            self.emit('ld a,(hl)', 'inc hl', 'ld h,(hl)', 'ld l,a')

    def gconv(self, e, want):
        a = e.a
        if e.v == 'ptr':
            return self.gx(a, want)
        if a.ty == 'float':
            p = self.fptr(a)
            self.emit('call @ftoi' if signed(e.ty) else 'call @ftou')
            self.ffree(p)
            if isbyte(e.ty):
                self.emit('ld h,0')
            return
        if e.ty == 'float':
            raise AssertionError('int->float in integer context')
        self.gx(a)
        if isbyte(e.ty) and not isbyte(a.ty):
            self.emit('ld h,0')

    def operands(self, a, b, commutative):
        """HL = a, DE = b, evaluating a before b where it matters."""
        sb = self.simple(b)
        if sb is not None:
            self.gx(a)
            self.load_de(sb)
            return
        sa = self.simple(a)
        if sa is not None and not self.has_side(b):
            self.gx(b)
            if commutative:
                self.load_de(sa)
            else:
                self.emit('ex de,hl')
                self.load_hl(sa)
            return
        self.gx(a)
        self.emit('push hl')
        self.gx(b)
        self.emit('ex de,hl', 'pop hl')

    def gbin(self, e):
        op, a, b, ty = e.v, e.a, e.b, e.opty
        if ty == 'float':
            raise AssertionError('float bin in gx')
        if op in ('<<', '>>'):
            return self.gshift(e)
        if b.op == 'num':
            k = b.v
            if op in ('+', '-'):
                if op == '-':
                    k = -k & 0xFFFF
                self.gx(a)
                if k <= 3:
                    self.emit(*['inc hl'] * k)
                elif k >= 0xFFFD:
                    self.emit(*['dec hl'] * (0x10000 - k))
                else:
                    self.emit('ld de,%d' % k, 'add hl,de')
                return
            if op == '*':
                self.gx(a)
                self.mulk(k)
                return
            if op == '&' and k == 0xFF:
                self.gx(a)
                self.emit('ld h,0')
                return
            if op == '&' and k < 256:
                self.gx(a)
                self.emit('ld a,l', 'and %d' % k, 'ld l,a', 'ld h,0')
                return
            if op in ('|', '^') and k < 256:
                self.gx(a)
                self.emit('ld a,l', '%s %d' % ('or' if op == '|' else 'xor', k), 'ld l,a')
                return
            if op in ('/', '%') and ty == 'uint' and k and k & (k - 1) == 0:
                self.gx(a)
                s = k.bit_length() - 1
                if op == '%':
                    m = k - 1
                    if m < 256:
                        self.emit('ld a,l', 'and %d' % m, 'ld l,a', 'ld h,0')
                    else:
                        self.emit('ld a,h', 'and %d' % (m >> 8), 'ld h,a')
                    return
                if s >= 8:
                    self.emit('ld l,h', 'ld h,0')
                    self.emit(*['srl l'] * (s - 8))
                elif s <= 2:
                    for _ in range(s):
                        self.emit('srl h', 'rr l')
                else:
                    self.emit('ld a,%d' % s, 'call @shr')
                return
        commut = op in ('+', '*', '&', '|', '^')
        self.operands(a, b, commut)
        if op == '+':
            self.emit('add hl,de')
        elif op == '-':
            self.emit('or a', 'sbc hl,de')
        elif op == '*':
            self.emit('call @mul')
        elif op == '/':
            self.emit('call @divs' if ty == 'int' else 'call @divu')
        elif op == '%':
            self.emit('call @mods' if ty == 'int' else 'call @modu')
        elif op == '&':
            self.emit('call @and')
        elif op == '|':
            self.emit('call @or')
        elif op == '^':
            self.emit('call @xor')
        else:
            raise AssertionError(op)

    def mulk(self, k):
        if k == 0:
            self.emit('ld hl,0')
            return
        if k & (k - 1) == 0:
            s = k.bit_length() - 1
            if s >= 8:
                self.emit('ld h,l', 'ld l,0')
                s -= 8
            self.emit(*['add hl,hl'] * s)
            return
        for base, extra in ((3, 1), (5, 2), (9, 3)):
            if k % base == 0 and (k // base) & (k // base - 1) == 0:
                self.emit('ld d,h', 'ld e,l', *['add hl,hl'] * extra, 'add hl,de')
                self.mulk(k // base)
                return
        self.emit('ld de,%d' % k, 'call @mul')

    def gshift(self, e):
        op, a, b, lt = e.v, e.a, e.b, e.opty
        byte = isbyte(lt)
        if b.op == 'num':
            n = b.v & (7 if byte else 15)
            self.gx(a)
            if n == 0:
                return
            if byte:
                if op == '<<':
                    self.emit('ld a,l', *['add a,a'] * n, 'ld l,a')
                else:
                    self.emit(*['srl l'] * n)
                return
            if op == '<<':
                if n >= 8:
                    self.emit('ld h,l', 'ld l,0')
                    n -= 8
                self.emit(*['add hl,hl'] * n)
                return
            if not signed(lt) and n >= 8:
                self.emit('ld l,h', 'ld h,0', *['srl l'] * (n - 8))
                return
            if n <= 2:
                for _ in range(n):
                    self.emit('sra h' if signed(lt) else 'srl h', 'rr l')
                return
            self.emit('ld a,%d' % n, 'call %s' % ('@sra' if signed(lt) else '@shr'))
            return
        self.operands(a, b, False)
        self.emit('ld a,e')
        if byte:
            self.emit('call %s' % ('@shlb' if op == '<<' else '@shrb'))
        else:
            self.emit('call %s' % ('@shl' if op == '<<' else ('@sra' if signed(lt) else '@shr')))

    # Conditions.
    def gcond(self, e, lab, sense):
        """Jump to lab when truth(e) == sense."""
        op = e.op
        if op == 'num':
            if bool(e.v) == sense:
                self.emit('j %s' % lab)
            return
        if op == 'fnum':
            if (not romfp.RomFP.is_zero(e.v)) == sense:
                self.emit('j %s' % lab)
            return
        if op == 'not':
            return self.gcond(e.a, lab, not sense)
        if op == 'ne0':
            return self.gcond(e.a, lab, sense)
        if op in ('and', 'or'):
            if (op == 'and') == sense:
                skip = self.newl()
                self.gcond(e.a, skip, not sense)
                self.gcond(e.b, lab, sense)
                self.label(skip)
            else:
                self.gcond(e.a, lab, sense)
                self.gcond(e.b, lab, sense)
            return
        if op == 'cmp':
            return self.gcmp(e, lab, sense)
        if e.ty == 'float':
            p = self.fptr(e)
            self.emit('call @ftst')
            self.ffree(p)
            self.emit('j %s,%s' % ('nz' if sense else 'z', lab))
            return
        if isbyte(e.ty):
            s = self.simple(e)
            if s and s[0] == 'st':
                self.emit('ld a,(%s)' % s[1])
            elif s and s[0] == 'fr':
                self.emit('ld a,%s' % self.ixd(s[1]))
            else:
                self.gx(e)
                self.emit('ld a,l')
            self.emit('or a')
        else:
            self.gx(e)
            self.emit('ld a,h', 'or l')
        self.emit('j %s,%s' % ('nz' if sense else 'z', lab))

    def byteval(self, e):
        """e is an int-promoted byte operand: return the byte expression."""
        if e.op == 'conv' and isbyte(e.a.ty) and is_int(e.ty):
            return e.a
        return None

    def gcmp(self, e, lab, sense):
        op, a, b, ty = e.v, e.a, e.b, e.opty
        if not sense:
            op = {'==': '!=', '!=': '==', '<': '>=', '>=': '<', '>': '<=', '<=': '>'}[op]
        if ty == 'float':
            if op in ('>', '<='):
                a, b = b, a
                op = {'>': '<', '<=': '>='}[op]
            pa = self.fptr(a)
            self.emit('push hl')
            pb = self.fptr(b)
            self.emit('ex de,hl', 'pop hl', 'call @fcmp')
            self.ffree(pa)
            self.ffree(pb)
            self.jcc(op, lab)
            return
        # constant on the left: swap
        if a.op == 'num' and b.op != 'num':
            a, b = b, a
            op = {'<': '>', '>': '<', '<=': '>=', '>=': '<=', '==': '==', '!=': '!='}[op]
        if b.op == 'num':
            k = b.v
            ba = self.byteval(a)
            if ba is not None and k < 256 and op in ('==', '!='):
                self.load_a(ba)
                if k:
                    self.emit('cp %d' % k)
                else:
                    self.emit('or a')
                self.jcc(op, lab)
                return
            if ba is not None and k < 255 and op in ('<', '>=', '>', '<='):
                if ty == 'int' and k >= 0x8000:
                    pass
                else:
                    self.load_a(ba)
                    if op in ('>', '<='):
                        k += 1
                        op = {'>': '>=', '<=': '<'}[op]
                    if k == 0:
                        if op == '<':
                            return
                        self.emit('j %s' % lab)
                        return
                    self.emit('cp %d' % k)
                    self.jcc(op, lab)
                    return
            if k == 0:
                if op in ('==', '!='):
                    self.gx(a)
                    if isbyte(a.ty):
                        self.emit('ld a,l', 'or a')
                    else:
                        self.emit('ld a,h', 'or l')
                    self.jcc(op, lab)
                    return
                if ty == 'int' and op in ('<', '>='):
                    self.gx(a)
                    self.emit('bit 7,h')
                    self.emit('j %s,%s' % ('nz' if op == '<' else 'z', lab))
                    return
                if ty != 'int' and op in ('<', '>='):
                    if op == '>=':
                        self.gx(a, want=False)
                        self.emit('j %s' % lab)
                    else:
                        self.gx(a, want=False)
                    return
        if op in ('>', '<='):
            # compare b - a
            self.swapped_operands(a, b)
            op = {'>': '<', '<=': '>='}[op]
        else:
            self.operands(a, b, False)
        if op in ('==', '!='):
            self.emit('or a', 'sbc hl,de')
        elif ty == 'int':
            self.emit('call @scmp')
        else:
            self.emit('or a', 'sbc hl,de')
        self.jcc(op, lab)

    def swapped_operands(self, a, b):
        """HL = b, DE = a, with a evaluated first."""
        sa, sb = self.simple(a), self.simple(b)
        if sa is not None and sb is not None:
            self.load_hl(sb)
            self.load_de(sa)
            return
        if sa is not None and not self.has_side(b):
            self.gx(b)
            self.load_de(sa)
            return
        if sb is not None:
            self.gx(a)
            self.emit('ex de,hl')
            self.load_hl(sb)
            return
        self.gx(a)
        self.emit('push hl')
        self.gx(b)
        self.emit('pop de')

    def load_a(self, be):
        s = self.simple(be)
        if s and s[0] == 'st':
            self.emit('ld a,(%s)' % s[1])
        elif s and s[0] == 'fr':
            self.emit('ld a,%s' % self.ixd(s[1]))
        else:
            self.gx(be)
            self.emit('ld a,l')

    def jcc(self, op, lab):
        cc = {'==': 'z', '!=': 'nz', '<': 'c', '>=': 'nc'}[op]
        self.emit('j %s,%s' % (cc, lab))

    # Assignment.
    def lvalue_static(self, x):
        """Static or frame location of an lvalue, or None."""
        if x.op == 'var':
            return x.sym.loc[:2]
        s = self.simple(x)
        if s and s[0] in ('st', 'fr'):
            return s[:2]
        return None

    def gasg(self, e, want):
        x, r = e.a, e.b
        if x.ty == 'float':
            return self.gfasg(e, want)
        size = sizeof(x.ty)
        loc = self.lvalue_static(x)
        if loc is not None:
            if size == 1 and r.op == 'num' and loc[0] == 'fr':
                self.emit('ld %s,%d' % (self.ixd(loc[1]), r.v & 255))
                if want:
                    self.emit('ld hl,%d' % (r.v & 255))
                return
            if size == 1 and r.op == 'num' and not want and loc[0] == 'st':
                self.emit('ld a,%d' % (r.v & 255), 'ld (%s),a' % loc[1])
                return
            self.gx(r)
            self.store_hl_loc(loc, size)
            return
        # through a pointer: address first, then value
        assert x.op == 'deref'
        sr = self.simple(r)
        self.gx(x.a)
        if sr is not None and sr[0] == 'imm' and size == 1 and sr[1].isdigit():
            self.emit('ld (hl),%d' % (int(sr[1]) & 255))
            if want:
                self.emit('ld hl,%d' % (int(sr[1]) & 255))
            return
        if sr is not None:
            self.load_de(sr)
        else:
            self.emit('push hl')
            self.gx(r)
            self.emit('ex de,hl', 'pop hl')
        if size == 1:
            self.emit('ld (hl),e')
        else:
            self.emit('ld (hl),e', 'inc hl', 'ld (hl),d')
        if want:
            self.emit('ex de,hl')

    def ginc(self, e, want):
        x = e.a
        kind, d = e.v
        if x.ty == 'float':
            self.gfinc(e, None)
            return
        size = sizeof(x.ty)
        loc = self.lvalue_static(x)
        if loc is not None:
            if size == 1:
                if loc[0] == 'st':
                    self.emit('ld hl,%s' % loc[1], 'inc (hl)' if d > 0 else 'dec (hl)')
                    if want:
                        self.emit('ld a,(hl)')
                        if kind == 'post':
                            self.emit('dec a' if d > 0 else 'inc a')
                        self.emit('ld l,a', 'ld h,0')
                else:
                    self.emit(('inc ' if d > 0 else 'dec ') + self.ixd(loc[1]))
                    if want:
                        self.emit('ld a,%s' % self.ixd(loc[1]))
                        if kind == 'post':
                            self.emit('dec a' if d > 0 else 'inc a')
                        self.emit('ld l,a', 'ld h,0')
                return
            self.load_hl_loc(loc, 2)
            if want and kind == 'post':
                self.emit('push hl')
            self.addk(d)
            self.store_hl_loc(loc, 2)
            if want and kind == 'post':
                self.emit('pop hl')
            return
        assert x.op == 'deref'
        self.gx(x.a)
        if size == 1:
            self.emit('inc (hl)' if d > 0 else 'dec (hl)')
            if want:
                self.emit('ld a,(hl)')
                if kind == 'post':
                    self.emit('dec a' if d > 0 else 'inc a')
                self.emit('ld l,a', 'ld h,0')
            return
        self.emit('ld de,%d' % (d & 0xFFFF))
        self.emit('call @preincw' if kind == 'pre' or not want else 'call @postincw')

    def addk(self, k):
        k &= 0xFFFF
        if k <= 3:
            self.emit(*['inc hl'] * k)
        elif k >= 0xFFFD:
            self.emit(*['dec hl'] * (0x10000 - k))
        else:
            self.emit('ld de,%d' % k, 'add hl,de')

    # Calls.
    def gcall(self, e, want):
        f = e.sym
        args = e.args
        n = len(args)
        temps = []
        for i, a in enumerate(args):
            if a.ty == 'float':
                later_side = any(self.has_side(x) for x in args[i + 1:])
                if a.op in ('var', 'fnum') or (a.op == 'deref' and not later_side and False):
                    if a.op == 'var' and later_side:
                        t = self.ftemp()
                        temps.append(t)
                        self.gf_into(a, t)
                        self.addr_hl(t)
                    else:
                        self.fptr(a)
                else:
                    t = self.ftemp()
                    temps.append(t)
                    self.gf_into(a, t)
                    self.addr_hl(t)
            else:
                self.gx(a)
            if i < n - 1:
                self.emit('push hl')
        # calls with stack arguments must not become tail jumps
        self.emit('call %s%s' % ('_' + f.name, ' ;stk' if n > 1 else ''))
        for t in temps:
            self.ffree(t)

    @staticmethod
    def has_side(e):
        from .parse import has_side
        return has_side(e)

    # Floats.
    def fptr(self, e):
        """HL = address of the float value of e.  Returns a temp to free."""
        if e.op == 'fnum':
            self.emit('ld hl,%s' % self.fconst_label(e.v))
            return None
        if e.op == 'var':
            self.addr_hl(e.sym.loc)
            return None
        if e.op == 'deref':
            self.gx(e.a)
            return None
        t = self.ftemp()
        self.gf_into(e, t)
        self.addr_hl(t)
        return t

    def gf_into(self, e, dst):
        """Evaluate float expression e into location dst."""
        op = e.op
        if op in ('fnum', 'var', 'deref'):
            self.fptr(e)
            self.addr_de(dst) if dst[0] == 'st' else self.fr_de_keep(dst)
            self.emit('call @fmov')
            return
        if op == 'conv':
            a = e.a
            self.gx(a)
            self.addr_de_keep(dst)
            self.emit('call @itof' if signed(a.ty) else 'call @utof')
            return
        if op == 'bin':
            self.gf_into(e.a, dst)
            b = e.b
            if b.op in ('fnum', 'var') or (b.op == 'deref' and not self.has_side(b)):
                pb = self.fptr(b)
                self.emit('push hl')
                self.addr_hl(dst)
                self.emit('pop de')
            else:
                t = self.ftemp()
                self.gf_into(b, t)
                self.addr_hl(dst)
                self.addr_de_keep(t)
                self.ffree(t)
            self.emit('ld a,%d' % FOP[e.v], 'call @fop')
            return
        if op == 'neg':
            self.gf_into(e.a, dst)
            self.addr_hl(dst)
            self.emit('ld a,%d' % romfp.NEG, 'call @fop')
            return
        if op == 'call':
            self.gcall(e, True)
            self.emit('ld hl,@fac')
            self.addr_de_keep(dst)
            self.emit('call @fmov')
            return
        if op == 'asg':
            self.gfasg(e, False)
            self.fptr(e.a)
            self.addr_de_keep(dst)
            self.emit('call @fmov')
            return
        if op == 'inc':
            self.gfinc(e, dst)
            return
        raise AssertionError('gf %s' % op)

    def fcopy(self, src, dst):
        """Copy the float at location src to location dst."""
        self.addr_hl(src)
        self.addr_de_keep(dst)
        self.emit('call @fmov')

    def gfinc(self, e, dst):
        """Float ++/-- (spec 52): the operand's address is evaluated once; the
        value (into dst, if any) is the new value for prefix, the old for postfix."""
        x = e.a
        kind, d = e.v
        t = self.ftemp()
        if x.op == 'var':
            self.gf_into(x, t)
        else:
            self.gx(x.a)                    # address, once
            self.emit('push hl')
            self.addr_de_keep(t)
            self.emit('call @fmov')
        if dst is not None and kind == 'post':
            self.fcopy(t, dst)
        self.addr_hl(t)
        self.emit('ld de,%s' % self.fconst_label(self.p.rom.from_int(1, False)))
        self.emit('ld a,%d' % (romfp.ADD if d > 0 else romfp.SUB), 'call @fop')
        if x.op == 'var':
            self.fstore(x, t)
        else:
            self.addr_hl(t)
            self.emit('pop de', 'call @fmov')
        if dst is not None and kind == 'pre':
            self.fcopy(t, dst)
        self.ffree(t)

    def addr_de_keep(self, loc):
        """DE = address of loc without disturbing HL."""
        if loc[0] == 'st':
            self.emit('ld de,%s' % loc[1])
        else:
            self.fr_de_keep(loc)

    def fr_de_keep(self, loc):
        if loc[0] == 'st':
            self.emit('ld de,%s' % loc[1])
            return
        self.emit('push hl', 'push ix', 'pop hl', 'ld de,%d' % loc[1], 'add hl,de', 'ex de,hl', 'pop hl')

    def fstore(self, x, src):
        """Copy float at location src into lvalue x."""
        if x.op == 'var':
            self.addr_hl(src)
            self.addr_de_keep(x.sym.loc)
            self.emit('call @fmov')
            return
        self.gx(x.a)
        self.emit('ex de,hl')
        if src[0] == 'st':
            self.emit('ld hl,%s' % src[1])
        else:
            self.emit('push de')
            self.addr_hl(src)
            self.emit('pop de')
        self.emit('call @fmov')

    def gfasg(self, e, want):
        x, r = e.a, e.b
        if r.op in ('fnum', 'var'):
            if x.op == 'var':
                self.fptr(r)
                self.addr_de_keep(x.sym.loc)
                self.emit('call @fmov')
                return
            self.gx(x.a)
            self.emit('push hl')
            self.fptr(r)
            self.emit('pop de', 'call @fmov')
            return
        if x.op == 'var':
            t = self.ftemp()
            self.gf_into(r, t)
            self.fstore(x, t)
            self.ffree(t)
            return
        # through a pointer: address first
        self.gx(x.a)
        self.emit('push hl')
        t = self.ftemp()
        self.gf_into(r, t)
        self.addr_hl(t)
        self.emit('pop de', 'call @fmov')
        self.ffree(t)


def peephole(text):
    lines = text.split('\n')
    changed = True
    while changed:
        changed = False
        out = []
        i = 0
        n = len(lines)
        while i < n:
            l = lines[i]
            s = l.strip()
            nxt = lines[i + 1].strip() if i + 1 < n else ''
            if s == 'ex de,hl' and nxt == 'ex de,hl':
                i += 2
                changed = True
                continue
            if s == 'push hl' and nxt == 'pop hl':
                i += 2
                changed = True
                continue
            if s == 'push hl' and nxt == 'pop de':
                out += ['\tld d,h', '\tld e,l']
                i += 2
                changed = True
                continue
            if s.startswith('ld (') and s.endswith('),hl') and nxt == 'ld hl,%s' % s[3:-3]:
                out.append(l)
                i += 2
                changed = True
                continue
            if s.startswith('j ') and ',' not in s and nxt == s[2:] + ':':
                i += 1
                changed = True
                continue
            if s.startswith('j ') and ',' in s and nxt == s.split(',')[1] + ':':
                i += 1
                changed = True
                continue
            if s.startswith('call ') and nxt == 'ret' and not s.startswith('call @enter') and not s.endswith(';stk'):
                out.append('\tjp ' + s[5:])
                i += 2
                changed = True
                continue
            if s.startswith('ld hl,') and not s.startswith('ld hl,(') and nxt == 'ex de,hl':
                out.append('\tld de,' + s[6:])
                i += 2
                changed = True
                continue
            if s.startswith('ld hl,(') and nxt == 'ex de,hl':
                out.append('\tld de,' + s[6:])
                i += 2
                changed = True
                continue
            # unreachable code after an unconditional transfer
            if (s == 'ret' or s.startswith('jp ') and ',' not in s or (s.startswith('j ') and ',' not in s)) and \
                    i + 1 < n and not lines[i + 1].endswith(':') and lines[i + 1].startswith('\t') and \
                    not lines[i + 1].strip().startswith(('section', 'dw', 'db', 'ds', 'global')):
                out.append(l)
                i += 2
                changed = True
                continue
            out.append(l)
            i += 1
        lines = out
        # jump threading: label followed by unconditional jump.
        alias = {}
        for k in range(len(lines) - 1):
            if lines[k].endswith(':') and lines[k + 1].strip().startswith('j ') and ',' not in lines[k + 1]:
                tgt = lines[k + 1].strip()[2:]
                if tgt != lines[k][:-1]:
                    alias[lines[k][:-1]] = tgt
        if alias:
            def res(x, seen=()):
                while x in alias and x not in seen:
                    seen = seen + (x,)
                    x = alias[x]
                return x
            for k, l in enumerate(lines):
                s = l.strip()
                if s.startswith('j ') or s.startswith('jp '):
                    head, _, tgt = s.rpartition(',') if ',' in s else (s.split()[0], ' ', s.split()[1])
                    if ',' in s:
                        new = res(tgt)
                        if new != tgt:
                            lines[k] = '\t%s,%s' % (head, new)
                            changed = True
                    else:
                        new = res(tgt)
                        if new != tgt:
                            lines[k] = '\t%s %s' % (s.split()[0], new)
                            changed = True
        # remove unreferenced @l labels
        used = set()
        for l in lines:
            if not l.endswith(':'):
                for w in l.replace(',', ' ').split():
                    used.add(w)
        nl = [l for l in lines if not (l.startswith('@l') and l.endswith(':') and l[:-1] not in used)]
        if len(nl) != len(lines):
            changed = True
            lines = nl
    return '\n'.join(lines)
