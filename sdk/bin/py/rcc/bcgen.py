# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""rcc: SSB1 bytecode back end (mixed with native code per function).

A bytecode function keeps the native entry and calling convention (rcc
rules), so native and bytecode functions call each other freely:

    _f:     call @vm            ; enter the virtual machine (sdk/lib/vm.asm)
            db frame            ; locals bytes (255: a word follows)
            <bytecode>

Its frame is the native recursive layout: [args 1..n-1][ret][old IX] <- IX,
the last argument at IX-2, the saved instruction pointer at IX-4, locals
below.  Functions that use floats stay native.
"""
from .types import BYTE, is_int, is_ptr, is_arr, sizeof, signed, align_of
from .lex import CError
from .z80gen import Gen, Func, isbyte
from . import bcops
from .bcops import OPCODE, KIND

KJ = {'jeqk': 'jeq', 'jnek': 'jne', 'jltk': 'jlt', 'jgek': 'jge', 'jgtk': 'jgt', 'jlek': 'jle',
      'jgtuk': 'jgtu', 'jleuk': 'jleu'}


# Short forms need a handler and table slot; each use then saves one byte.
SHORT_COST = {'ldl.%d' % d: 11 for d in bcops.SHORT_LDL}
SHORT_COST.update({'stl.%d' % d: 11 for d in bcops.SHORT_STL})
SHORT_COST.update({'pldl.%d' % d: 12 for d in bcops.SHORT_LDL})  # 3 with its ldl.N
SHORT_COST.update({'k0': 8, 'k1': 8, 'pk0': 3, 'pk1': 3})


def short_allowed(uses):
    """the short forms worth their handlers, given their uses"""
    ok = {n for n, k in uses.items() if k > SHORT_COST[n] and not n.startswith('pldl.')}
    for n, k in uses.items():
        if n.startswith('pldl.'):
            both = uses.get(n[1:], 0) + k
            if n[1:] in ok and k > 3 or n[1:] not in ok and both > SHORT_COST[n]:
                ok.add(n)
                ok.add(n[1:])
    return ok


def opsym(name):
    """the assembler symbol of an opcode (numbered per program)"""
    return '@o_' + name.replace('.', '_').replace('-', 'm')


def uses_float(f):
    found = [False]

    def walk(x):
        if x is None or found[0] or x.__class__.__name__ == 'Sym':
            return
        if isinstance(x, list):
            for y in x:
                walk(y)
            return
        if x.__class__.__name__ == 'N':
            if x.ty == 'float' or (x.op == 'call' and any(a.ty == 'float' for a in x.args)):
                found[0] = True
                return
            walk(x.a)
            walk(x.b)
            walk(x.args)
            return
        for k in ('e', 'a', 'b', 'c', 'body', 'items'):
            v = getattr(x, k)
            if v is not None and not isinstance(v, (str, int)):
                walk(v)
    walk(f.body)
    for p in f.params:
        if p.ty == 'float':
            return True
    for l in f.locals:
        if l.ty == 'float':
            return True
    return found[0]


class BGen(Gen):
    """Native generator that emits bytecode for the functions it can."""

    def __init__(self, prog, opts=None):
        super().__init__(prog, opts)
        self.bc = {}                # bytecode functions, in source order (ordered set)
        self.used_ops = set()

    # Layout.
    def analyze(self):
        super().analyze()
        # a separately compiled object (rcc -c) cannot own the program-wide @gs block,
        # call table @ct or dispatch table @vmtab: it uses the library's full table (fixed
        # opcode numbers) and plain global access.
        self.module = bool(self.opts.get('module'))
        if not self.module:
            self.layout_gs()
        mode = self.opts.get('bytecode', 'all')
        for f in self.p.funcs:
            if mode == 'none' or uses_float(f):
                continue
            if mode not in ('all', None) and f.name not in mode:
                continue
            F = self.funcs[f]
            self.bc[f] = None
            F.recursive = True          # frame layout
            F.size = 0
            n = len(f.params)
            for i, p in enumerate(f.params):
                if i == n - 1:
                    p.loc = ('fr', -2, 2)
                else:
                    p.loc = ('fr', 4 + 2 * (n - 2 - i), 2)
            F.frame = 4
            for l in f.locals:
                l.loc = self.frame_alloc(F, sizeof(l.ty), align_of(l.ty))
        # functions called 3 times or more from bytecode: through @ct (counted once
        # the bytecode functions are known).
        count = {}

        def walk(x):
            if x is None or x.__class__.__name__ == 'Sym':
                return
            if isinstance(x, list):
                for y in x:
                    walk(y)
                return
            if x.__class__.__name__ == 'N':
                if x.op == 'call':
                    count[x.sym.name] = count.get(x.sym.name, 0) + 1
                walk(x.a)
                walk(x.b)
                walk(x.args)
                return
            for k in ('e', 'a', 'b', 'c', 'body', 'items'):
                v = getattr(x, k)
                if v is not None and not isinstance(v, (str, int)):
                    walk(v)
        for f in self.bc:
            walk(f.body)
        self.ctab = [] if self.module else \
            ['_' + n for n, c in sorted(count.items(), key=lambda t: -t[1]) if c >= 3][:256]
        self.cidx = {n: i for i, n in enumerate(self.ctab)}

    def function(self, f):
        if f not in self.bc:
            return super().function(f)
        F = self.funcs[f]
        self.F = F
        self.f = f
        self.loops = []
        self.code = []
        self.npush = max(len(f.params) - 1, 0)
        self.label(f.label)
        self.emit('call @vm')
        self.bstmt(f.body)
        if f.ty[1] != 'void':
            if not (self.code and self.code[-1][0] in ('ret', 'ret0', 'ret1', 'ret2', 'jmp', 'noret')):
                self.op('noret')
        else:
            self.op_ret()
        F.frame += F.frame & 1          # keep SP even
        frame = F.frame - 4
        if frame < 255:
            self.emit('db %d' % frame)
        else:
            self.emit('db 255', 'dw %d' % frame)
        self.assemble()
        self.F = None

    # Emission.
    def op(self, name, *args):
        self.code.append((name,) + args)

    def blabel(self, l):
        self.code.append(('@', l))

    def op_ret(self):
        n = self.npush
        if n <= 2:
            self.op('ret%d' % n)
        else:
            self.op('ret', n)

    def last_is_jump(self):
        if not self.code:
            return False
        n = self.code[-1][0]
        return n in ('jmp', 'ret', 'ret0', 'ret1', 'ret2', 'noret')

    # Peephole.
    def peephole(self):
        c = self.code
        out = []
        i = 0
        while i < len(c):
            x = c[i]
            nx = c[i + 1] if i + 1 < len(c) else None
            if x[0] == 'push' and nx is not None:
                fused = {'k0': 'pk0', 'k1': 'pk1', 'ldk': 'pldk', 'ldkw': 'pldkw', 'lda': 'plda',
                         'ldl': 'pldl', 'ldlb': 'pldlb', 'ldg': 'pldg', 'ldgb': 'pldgb',
                         'ldgs': 'pldgs', 'ldgsb': 'pldgsb'}.get(nx[0])
                if fused:
                    out.append((fused,) + nx[1:])
                    i += 2
                    continue
            # a store keeps its value: a load of the same place after it goes
            if x[0] in ('stl', 'stg', 'stgs') and nx is not None \
                    and nx[0] == {'stl': 'ldl', 'stg': 'ldg', 'stgs': 'ldgs'}[x[0]] and nx[1] == x[1]:
                out.append(x)
                i += 2
                continue
            # jump to the next instruction.
            if x[0] == 'jmp' and nx is not None and nx[0] == '@' and nx[1] == x[1]:
                i += 1
                continue
            out.append(x)
            i += 1
        self.code = out

    # Assembly.
    def assemble(self):
        self.peephole()
        code = self.code
        st = self.opts.get('stats')
        if st is not None:
            st.setdefault('fn', []).append(list(code))
        # constants into short forms (those the program uses enough to pay for their
        # handlers: opts['short'], from a first pass).
        allowed = self.opts.get('short')
        self.short_uses = getattr(self, 'short_uses', {})
        for i, x in enumerate(code):
            if x[0] == 'ldk' and x[1] in (0, 1):
                code[i] = ('k%d' % x[1],)
            elif x[0] == 'ldkw':
                v = x[1] & 0xFFFF
                sv = v - 0x10000 if v >= 0x8000 else v
                if sv in (0, 1):
                    code[i] = ('k%d' % sv,)
                elif -128 <= sv <= 127:
                    code[i] = ('ldk', sv)
            elif x[0] == 'pldkw':
                v = x[1] & 0xFFFF
                sv = v - 0x10000 if v >= 0x8000 else v
                if sv in (0, 1):
                    code[i] = ('pk%d' % sv,)
                elif -128 <= sv <= 127:
                    code[i] = ('pldk', sv)
            elif x[0] == 'pldk' and x[1] in (0, 1):
                code[i] = ('pk%d' % x[1],)
            elif x[0] == 'ldl' and x[1] in bcops.SHORT_LDL:
                code[i] = ('ldl.%d' % x[1],)
            elif x[0] == 'stl' and x[1] in bcops.SHORT_STL:
                code[i] = ('stl.%d' % x[1],)
            elif x[0] == 'pldl' and x[1] in bcops.SHORT_LDL:
                code[i] = ('pldl.%d' % x[1],)
            y = code[i]
            if y is not x and y[0] in SHORT_COST:
                self.short_uses[y[0]] = self.short_uses.get(y[0], 0) + 1
                if allowed is not None and y[0] not in allowed:
                    code[i] = x
        # branch relaxation
        long_ = set()
        while True:
            pos = {}
            addr = 0
            sizes = []
            for i, x in enumerate(code):
                if x[0] == '@':
                    pos[x[1]] = addr
                    sizes.append(0)
                    continue
                s = self.isize(x, i in long_)
                sizes.append(s)
                addr += s
            changed = False
            addr = 0
            for i, x in enumerate(code):
                addr += sizes[i]
                k = KIND.get(x[0], '')
                if 'j' in k and i not in long_:
                    d = pos[x[-1]] - addr
                    if not -128 <= d <= 127:
                        long_.add(i)
                        changed = True
            if not changed:
                break
        self.pos = pos
        # emit
        addr = 0
        out = []
        for i, x in enumerate(code):
            if x[0] == '@':
                continue
            name = x[0]
            k = KIND[name]
            lg = i in long_
            size = self.isize(x, lg)
            addr += size
            if name in KJ and lg:
                # (no long form) compare with a constant: push, constant, long branch
                v = x[1]
                d = pos[x[2]] - addr
                out.append(('o', 'pldk'))
                out.append(('b', v & 255))
                out.append(('o', KJ[name] + 'l'))
                out.append(('w', d))
                continue
            if 'j' in k and lg:
                d = pos[x[-1]] - addr
                out.append(('o', name + 'l' if name + 'l' in OPCODE else name))
                out.append(('w', d))
                continue
            out.append(('o', name))
            args = x[1:]
            if k == '':
                continue
            if k in ('b', 's', 'f'):
                out.append(('b', args[0] & 255))
            elif k == 'w':
                out.append(('w', args[0] & 0xFFFF))
            elif k == 'a':
                out.append(('a', args[0]))
            elif k in ('fs', 'bs'):
                out.append(('b', args[0] & 255, args[1] & 255))
            elif k == 'as':
                out.append(('a', args[0]))
                out.append(('b', args[1] & 255))
            elif k == 'j':
                out.append(('b', (pos[args[0]] - addr) & 255))
            elif k == 'sj':
                out.append(('b', args[0] & 255, (pos[args[1]] - addr) & 255))
        if st is not None:
            st.setdefault('ops', []).append(list(out))
        # to assembly lines: runs of bytes, words for relocated symbols.
        run = []

        def flush():
            if run:
                for k in range(0, len(run), 16):
                    self.emit('db ' + ','.join(str(v) for v in run[k:k + 16]))
                run.clear()
        for item in out:
            if item[0] == 'o':
                self.used_ops.add(item[1])
                run.append(opsym(item[1]))
            elif item[0] == 'b':
                run.extend(item[1:])
            elif item[0] == 'w':
                v = item[1] & 0xFFFF
                run.extend((v & 255, v >> 8))
            else:
                flush()
                self.emit('dw %s' % item[1])
        flush()
        self.bytes_total = getattr(self, 'bytes_total', 0) + addr

    def isize(self, x, lg):
        name = x[0]
        k = KIND[name]
        if name in KJ:
            return 5 if lg else 3
        if 'j' in k:
            return 3 if lg else 2
        return 1 + {'': 0, 'b': 1, 's': 1, 'f': 1, 'w': 2, 'a': 2, 'fs': 2, 'bs': 2, 'as': 3}[k]

    # Statements.
    def bstmt(self, s):
        op = s.op
        if op == 'block':
            for x in s.items:
                self.bstmt(x)
        elif op == 'empty':
            pass
        elif op == 'expr':
            self.bx(s.e, want=False)
        elif op == 'copy':
            self.op('lda', s.b.label)
            self.op('push')
            self.baddr(s.a.loc)
            self.op('copy', sizeof(s.a.ty))
        elif op == 'if':
            lf = self.newl()
            self.bcond(s.e, lf, False)
            self.bstmt(s.a)
            if s.b is not None:
                le = self.newl()
                if not self.last_is_jump():
                    self.op('jmp', le)
                self.blabel(lf)
                self.bstmt(s.b)
                self.blabel(le)
            else:
                self.blabel(lf)
        elif op == 'while':
            top, brk, cont = self.newl(), self.newl(), self.newl()
            self.op('jmp', cont)
            self.blabel(top)
            self.loops.append((brk, cont))
            self.bstmt(s.body)
            self.loops.pop()
            self.blabel(cont)
            self.bcond(s.e, top, True)
            self.blabel(brk)
        elif op == 'do':
            top, brk, cont = self.newl(), self.newl(), self.newl()
            self.blabel(top)
            self.loops.append((brk, cont))
            self.bstmt(s.body)
            self.loops.pop()
            self.blabel(cont)
            self.bcond(s.e, top, True)
            self.blabel(brk)
        elif op == 'for':
            if s.a is not None:
                self.bx(s.a, want=False)
            top, brk, cont, test = self.newl(), self.newl(), self.newl(), self.newl()
            if s.e is not None:
                self.op('jmp', test)
            self.blabel(top)
            self.loops.append((brk, cont))
            self.bstmt(s.body)
            self.loops.pop()
            self.blabel(cont)
            if s.b is not None:
                self.bx(s.b, want=False)
            self.blabel(test)
            if s.e is not None:
                self.bcond(s.e, top, True)
            else:
                self.op('jmp', top)
            self.blabel(brk)
        elif op == 'break':
            self.op('jmp', self.loops[-1][0])
        elif op == 'continue':
            self.op('jmp', self.loops[-1][1])
        elif op == 'ret':
            if s.e is not None:
                self.bx(s.e)
            self.op_ret()
        else:
            raise AssertionError(op)

    # Helpers.
    def baddr(self, loc):
        """HL = address of a storage location."""
        if loc[0] == 'st':
            self.op('lda', loc[1])
        else:
            self.op('leal', loc[1])

    def bload(self, loc, size):
        if loc[0] == 'st':
            g = self.gs.get(loc[1])
            if g is not None:
                self.op('ldgsb' if size == 1 else 'ldgs', g)
            else:
                self.op('ldgb' if size == 1 else 'ldg', loc[1])
        else:
            self.op('ldlb' if size == 1 else 'ldl', loc[1])

    def bstore(self, loc, size):
        if loc[0] == 'st':
            g = self.gs.get(loc[1])
            if g is not None:
                self.op('stgsb' if size == 1 else 'stgs', g)
            else:
                self.op('stgb' if size == 1 else 'stg', loc[1])
        else:
            self.op('stlb' if size == 1 else 'stl', loc[1])

    def const_addr(self, e):
        """e is an address known at link time: its label text, else None."""
        s = self.simple(e)
        if s is not None and s[0] == 'imm' and not s[1].lstrip('-').isdigit():
            return s[1]
        if e.op == 'bin' and e.v == '+' and e.b.op == 'num':
            base = self.const_addr(e.a)
            if base is not None:
                return '%s+%d' % (base, e.b.v)
        return None

    @staticmethod
    def index_of(b):
        """Byte offset b -> (index expression, True if it is index * 2)."""
        if b.op == 'bin' and b.v == '*' and b.b.op == 'num' and b.b.v == 2:
            return b.a, True
        return b, False

    def static_lv(self, x):
        """Static (('st', label)) or frame (('fr', d)) location of an
        lvalue / object, or None."""
        if x.op == 'var':
            return x.sym.loc[:2]
        if x.op == 'deref':
            a = self.const_addr(x.a)
            if a is not None:
                return ('st', a)
        return None

    # Expressions.
    def bx(self, e, want=True):
        """Integer/pointer expression -> TOS (HL)."""
        op = e.op
        if e.ty == 'float':
            raise AssertionError('float in bytecode function')
        if op == 'num':
            if want:
                self.op('ldkw', e.v)
            return
        if op == 'str':
            if want:
                self.op('lda', self.p.str_label(e))
            return
        if op == 'var':
            if is_arr(e.ty):
                self.baddr(e.sym.loc)
                return
            if want:
                self.bload(e.sym.loc, sizeof(e.ty))
            return
        if op == 'addr':
            x = e.a
            if x.op == 'str':
                if want:
                    self.op('lda', self.p.str_label(x))
                return
            if x.op == 'var':
                if want:
                    self.baddr(x.sym.loc)
                return
            raise AssertionError('addr of %s' % x.op)
        if op == 'deref':
            loc = self.static_lv(e)
            if loc is not None:
                if want:
                    self.bload(loc, sizeof(e.ty))
                return
            p = e.a
            if p.op == 'bin' and p.v == '+' and p.b.op != 'num':
                ca = self.const_addr(p.a)
                if ca is not None:
                    x, w = self.index_of(p.b)
                    if w == (not isbyte(e.ty)):
                        self.bx(x)
                        self.op('ldxw' if w else 'ldxb', ca)
                        return
            self.bx(e.a)
            self.op('ldib' if isbyte(e.ty) else 'ldi')
            return
        if op == 'conv':
            a = e.a
            if e.v == 'ptr':
                return self.bx(a, want)
            self.bx(a, want)
            if want and isbyte(e.ty) and not isbyte(a.ty):
                self.op('zxb')
            return
        if op == 'bin':
            return self.bbin(e)
        if op in ('cmp', 'and', 'or', 'ne0') or (op == 'not' and False):
            lf, le = self.newl(), self.newl()
            self.bcond(e, lf, False)
            self.op('k1')
            self.op('jmp', le)
            self.blabel(lf)
            self.op('k0')
            self.blabel(le)
            return
        if op == 'not':
            self.bx(e.a)
            self.op('not')
            return
        if op == 'neg':
            self.bx(e.a)
            self.op('neg')
            return
        if op == 'com':
            self.bx(e.a)
            self.op('com')
            return
        if op == 'asg':
            return self.basg(e, want)
        if op == 'inc':
            return self.binc(e, want)
        if op == 'call':
            return self.bcall(e)
        raise AssertionError('bx %s' % op)

    def bbin(self, e):
        op, a, b, ty = e.v, e.a, e.b, e.opty
        if op in ('<<', '>>'):
            return self.bshift(e)
        if op == '+' and a.op == 'num' and b.op != 'num':
            a, b = b, a
        if op == '+' and b.op != 'num':
            ca = self.const_addr(a)
            if ca is not None:
                x, w = self.index_of(b)
                self.bx(x)
                self.op('addaw' if w else 'adda', ca)
                return
        if b.op == 'num':
            k = b.v & 0xFFFF
            if op in ('+', '-'):
                if op == '-':
                    k = -k & 0xFFFF
                ca = self.const_addr(a)
                if ca is not None:
                    self.op('lda', '%s+%d' % (ca, k if k < 0x8000 else k - 0x10000))
                    return
                self.bx(a)
                sk = k - 0x10000 if k >= 0x8000 else k
                if sk == 0:
                    return
                if -128 <= sk <= 127:
                    self.op('addk', sk)
                else:
                    self.op('addkw', k)
                return
            if op == '*':
                self.bx(a)
                if k == 0:
                    self.op('k0')
                    return
                if k & (k - 1) == 0:
                    for _ in range(k.bit_length() - 1):
                        self.op('shl1')
                    return
                self.op('push')
                self.op('ldkw', k)
                self.op('mul')
                return
            if op == '&' and k == 0xFF:
                self.bx(a)
                self.op('zxb')
                return
            if op == '&' and k < 256:
                self.bx(a)
                self.op('andk', k)
                return
            if op in ('/', '%') and ty == 'uint' and k and k & (k - 1) == 0:
                self.bx(a)
                s = k.bit_length() - 1
                if op == '%':
                    if k - 1 < 256:
                        self.op('andk', k - 1)
                    else:
                        self.op('push')
                        self.op('ldkw', k - 1)
                        self.op('and')
                    return
                self.op('push')
                self.op('ldk', s)
                self.op('shr')
                return
        self.bx(a)
        self.op('push')
        self.bx(b)
        self.op({'+': 'add', '-': 'sub', '*': 'mul', '&': 'and', '|': 'or', '^': 'xor',
                 '/': 'divs' if ty == 'int' else 'divu',
                 '%': 'mods' if ty == 'int' else 'modu'}[op])

    def bshift(self, e):
        op, a, b, lt = e.v, e.a, e.b, e.opty
        byte = isbyte(lt)
        if b.op == 'num':
            n = b.v & (7 if byte else 15)
            self.bx(a)
            if n == 0:
                return
            if op == '<<' and n <= 2:
                for _ in range(n):
                    self.op('shl1')
                if byte:
                    self.op('zxb')
                return
            self.op('push')
            self.op('ldk', n)
        else:
            self.bx(a)
            self.op('push')
            self.bx(b)
            if byte:
                self.op('andk', 7)
        if op == '<<':
            self.op('shl')
            if byte:
                self.op('zxb')
        else:
            self.op('sar' if signed(lt) else 'shr')

    # Conditions.
    def bcond(self, e, lab, sense):
        """Jump to lab when truth(e) == sense."""
        op = e.op
        if op == 'num':
            if bool(e.v) == sense:
                self.op('jmp', lab)
            return
        if op == 'not':
            return self.bcond(e.a, lab, not sense)
        if op == 'ne0':
            return self.bcond(e.a, lab, sense)
        if op in ('and', 'or') and self.brange(e, lab, sense):
            return
        if op in ('and', 'or'):
            if (op == 'and') == sense:
                skip = self.newl()
                self.bcond(e.a, skip, not sense)
                self.bcond(e.b, lab, sense)
                self.blabel(skip)
            else:
                self.bcond(e.a, lab, sense)
                self.bcond(e.b, lab, sense)
            return
        if op == 'cmp':
            return self.bcmp(e, lab, sense)
        self.bx(e)
        self.op('jnz' if sense else 'jz', lab)

    @staticmethod
    def bound(c):
        """cmp of an int variable with a constant -> (var, op, k), the
        variable on the left; else None"""
        if c.op != 'cmp' or c.opty != 'int':
            return None
        op, a, b = c.v, c.a, c.b
        if a.op == 'num' and b.op == 'var':
            a, b = b, a
            op = {'<': '>', '>': '<', '<=': '>=', '>=': '<=', '==': '==', '!=': '!='}[op]
        if a.op != 'var' or b.op != 'num' or is_arr(a.ty) or sizeof(a.ty) != 2:
            return None
        k = b.v & 0xFFFF
        return a.sym, op, (k - 0x10000 if k >= 0x8000 else k)

    def brange(self, e, lab, sense):
        """x < A || x > B  and  x >= A && x <= B  (x an int variable, A <= B):
        one unsigned compare of x - A with B - A."""
        p, q = self.bound(e.a), self.bound(e.b)
        if not p or not q or p[0] is not q[0]:
            return False
        lo = hi = None
        for sym, op, k in (p, q):
            if e.op == 'or':                    # outside [lo, hi]
                if op == '<':
                    lo = k
                elif op == '<=':
                    lo = k + 1
                elif op == '>':
                    hi = k
                elif op == '>=':
                    hi = k - 1
            else:                               # inside [lo, hi]
                if op == '>=':
                    lo = k
                elif op == '>':
                    lo = k + 1
                elif op == '<=':
                    hi = k
                elif op == '<':
                    hi = k - 1
        if lo is None or hi is None or not -32768 <= lo <= hi <= 32767 or hi - lo > 127:
            return False
        outside = (e.op == 'or') == sense      # jump when x is outside
        self.bx(e.a.a if e.a.a.op == 'var' else e.a.b)
        if lo:
            self.op('addk' if -128 <= -lo <= 127 else 'addkw', -lo)
        self.op('jgtuk' if outside else 'jleuk', hi - lo, lab)
        return True

    def bcmp(self, e, lab, sense):
        op, a, b, ty = e.v, e.a, e.b, e.opty
        if not sense:
            op = {'==': '!=', '!=': '==', '<': '>=', '>=': '<', '>': '<=', '<=': '>'}[op]
        if a.op == 'num' and b.op != 'num':
            a, b = b, a
            op = {'<': '>', '>': '<', '<=': '>=', '>=': '<=', '==': '==', '!=': '!='}[op]
        sg = 1 if ty == 'int' else 0
        if b.op == 'num':
            k = b.v & 0xFFFF
            sk = k - 0x10000 if k >= 0x8000 else k
            if k == 0 and op in ('==', '!='):
                self.bx(a)
                self.op('jz' if op == '==' else 'jnz', lab)
                return
            if not sg and k == 0:
                if op == '>=':
                    self.bx(a, want=False)
                    self.op('jmp', lab)
                    return
                if op == '<':
                    self.bx(a, want=False)
                    return
                if op in ('>', '<='):
                    self.bx(a)
                    self.op('jnz' if op == '>' else 'jz', lab)
                    return
            if op in ('==', '!=') and -128 <= sk <= 127:
                self.bx(a)
                self.op('jeqk' if op == '==' else 'jnek', sk, lab)
                return
            if sg and -128 <= sk <= 127:
                self.bx(a)
                self.op({'<': 'jltk', '>=': 'jgek', '>': 'jgtk', '<=': 'jlek'}[op], sk, lab)
                return
        self.bx(a)
        self.op('push')
        self.bx(b)
        self.op(bcops.JCC[(op, sg)], lab)

    # Assignment.
    def basg(self, e, want):
        x, r = e.a, e.b
        size = sizeof(x.ty)
        loc = self.static_lv(x)
        if loc is not None:
            self.bx(r)
            self.bstore(loc, size)
            return
        assert x.op == 'deref'
        self.bx(x.a)
        self.op('push')
        self.bx(r)
        self.op('stib' if size == 1 else 'sti')

    def binc(self, e, want):
        x = e.a
        kind, d = e.v
        size = sizeof(x.ty)
        loc = self.static_lv(x)
        d &= 0xFFFF
        sd = d - 0x10000 if d >= 0x8000 else d
        small = -128 <= sd <= 127
        if loc is not None and small:
            if want and kind == 'post':
                self.bload(loc, size)
            if loc[0] == 'st' and loc[1] in self.gs:
                self.op('addgsb' if size == 1 else 'addgs', self.gs[loc[1]], sd)
            elif loc[0] == 'st':
                self.op('addgb' if size == 1 else 'addg', loc[1], sd)
            else:
                self.op('addlb' if size == 1 else 'addl', loc[1], sd)
            if want and kind == 'pre':
                self.bload(loc, size)
            return
        if loc is not None:
            self.bload(loc, size)
            if want and kind == 'post':
                self.op('push')
            self.op('addkw', d)
            self.bstore(loc, size)
            if want and kind == 'post':
                self.op('pop')
            return
        assert x.op == 'deref'
        self.bx(x.a)
        if not small:
            raise CError('++/-- step too large for the bytecode back end', e.where, 'unsupported')
        if size == 1:
            self.op('postib' if want and kind == 'post' else 'preib', sd)
        else:
            self.op('postiw' if want and kind == 'post' else 'preiw', sd)

    # Calls.
    def bcall(self, e):
        f = e.sym
        args = e.args
        n = len(args)
        for i, a in enumerate(args):
            self.bx(a)
            if i < n - 1:
                self.op('push')
        t = '_' + f.name
        if t in self.cidx:
            self.op('calli', self.cidx[t])
        else:
            self.op('call', t)

    # Program.
    def generate(self):
        self.gs = {}
        self.gsvars = []
        text = super().generate()
        if self.bc and not self.module:
            text = '\tglobal @gs,@ct\n' + text
        return text

    def layout_gs(self):
        """Scalar globals into one block (@gs) for 2-byte access."""
        off = 0
        for s in self.p.gvars:
            if s.ty == 'float' or not isinstance(s.ty, str) and s.ty[0] != 'p':
                continue
            n = sizeof(s.ty)
            if align_of(s.ty) > 1:
                off += off & 1          # @gs is word aligned
            if off + n > 256:
                break
            self.gs[s.label] = off
            self.gsvars.append(s)
            off += n

    def data_lines(self):
        out = []
        if self.bc and not self.module:
            out += ['\talign 2', '@gs:']
            for s in self.gsvars:
                if align_of(s.ty) > 1:
                    out.append('\talign 2')
                out.append('%s:' % s.label)
                if s.init is None:
                    out.append('\tds %d' % sizeof(s.ty))
                else:
                    out += self.init_lines(s.init)
        keep = self.p.gvars
        self.p.gvars = [s for s in keep if not self.bc or s not in self.gsvars]
        out += super().data_lines()
        out += self.calltable()
        self.p.gvars = keep
        return out

    def bss_lines(self):
        keep = self.p.gvars
        self.p.gvars = [s for s in keep if not self.bc or s not in self.gsvars]
        out = super().bss_lines()
        self.p.gvars = keep
        return out

    def calltable(self):
        if not self.bc:
            return []
        if self.module:
            # opcode numbers of the library's full table (bcops.OPS order)
            return ['%s equ %d' % (opsym(n), bcops.OPCODE[n])
                    for n, k in bcops.OPS if n in self.used_ops]
        return ['@ct:'] + ['\tdw %s' % f for f in self.ctab] + self.vmtable()

    def vmtable(self):
        """The program's own dispatch table: only the opcodes it uses,
        numbered densely, so the VM links only their handlers."""
        ops = [n for n, k in bcops.OPS if n in self.used_ops]
        out = ['%s equ %d' % (opsym(n), i) for i, n in enumerate(ops)]
        out += ['\tglobal @vmtab', '@vmtab:']
        out += ['\tdw @v_%s' % n.replace('.', '_').replace('-', 'm') for n in ops]
        return out
