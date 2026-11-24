# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""Faster handlers for the common Z80 instructions, for the bundled core.

z80-python (sdk/z80_python, unmodified) implements each instruction as a
readable method that decodes its own opcode fields and goes through small
helpers (_read_reg, _hl, _read_operand_byte ...).  That costs several Python
calls per instruction.  FastZ80 replaces the dispatch-table entries of the
most frequent instructions with straight-line functions generated below, one
per opcode, with the register names, condition and ALU operation already
resolved.  Each generated function performs exactly the state changes of the
z80-python method it replaces: the same registers, F (undocumented X/Y
included), WZ (MEMPTR), Q, PC, memory accesses in the same order, and the same
T-state count.  The instructions not listed here use z80-python's own methods.

sdk/tests/test_z80fast.py checks the equivalence: every replaced opcode, run
from many random CPU states on both FastZ80 and the plain Z80CPU, must give
identical CPU state, memory and T-states.
"""
from functools import partial

from z80_python.cpu import Z80CPU
from z80_python._flags import SZXY, SZXYP

REG = ('b', 'c', 'd', 'e', 'h', 'l', None, 'a')        # None: (HL)
PAIR = ('bc', 'de', 'hl', 'sp')
COND = ('not f & 0x40', 'f & 0x40', 'not f & 1', 'f & 1',
        'not f & 4', 'f & 4', 'not f & 0x80', 'f & 0x80')

HL = '(cpu.h << 8 | cpu.l)'


def get_pair(p):
    if p == 'sp':
        return 'cpu.sp'
    return '(cpu.%s << 8 | cpu.%s)' % (p[0], p[1])


def set_pair(p, v):
    if p == 'sp':
        return 'cpu.sp = %s' % v
    return 'v = %s\n    cpu.%s = v >> 8\n    cpu.%s = v & 0xFF' % (v, p[0], p[1])


OPERAND = '''pc = cpu.pc
    n = rd(pc)
    cpu.pc = (pc + 1) & 0xFFFF'''

WORD = '''pc = cpu.pc
    nn = rd(pc) | rd((pc + 1) & 0xFFFF) << 8
    cpu.pc = (pc + 2) & 0xFFFF'''

PUSH = '''sp = (cpu.sp - 1) & 0xFFFF
    wr(sp, ({v}) >> 8)
    sp = (sp - 1) & 0xFFFF
    wr(sp, ({v}) & 0xFF)
    cpu.sp = sp'''

POP = '''sp = cpu.sp
    w = rd(sp)
    sp = (sp + 1) & 0xFFFF
    w |= rd(sp) << 8
    cpu.sp = (sp + 1) & 0xFFFF'''

# ALU A,y: x is A, y the operand; the F expressions are z80-python's _add,
# _sub, _and, _xor, _or and _cp.
ALU = (
    'z = x + y\n    r = z & 0xFF\n    cpu._f = SZXY[r] | ((x ^ y ^ r) & 0x10) | (((x ^ y ^ 0x80) & (x ^ r) & 0x80) >> 5) | (z >> 8)\n    cpu.a = r',
    'z = x + y + (cpu._f & 1)\n    r = z & 0xFF\n    cpu._f = SZXY[r] | ((x ^ y ^ r) & 0x10) | (((x ^ y ^ 0x80) & (x ^ r) & 0x80) >> 5) | (z >> 8)\n    cpu.a = r',
    'z = x - y\n    r = z & 0xFF\n    cpu._f = SZXY[r] | ((x ^ y ^ r) & 0x10) | (((x ^ y) & (x ^ r) & 0x80) >> 5) | 2 | ((z >> 8) & 1)\n    cpu.a = r',
    'z = x - y - (cpu._f & 1)\n    r = z & 0xFF\n    cpu._f = SZXY[r] | ((x ^ y ^ r) & 0x10) | (((x ^ y) & (x ^ r) & 0x80) >> 5) | 2 | ((z >> 8) & 1)\n    cpu.a = r',
    'r = x & y\n    cpu._f = SZXYP[r] | 0x10\n    cpu.a = r',
    'r = x ^ y\n    cpu._f = SZXYP[r]\n    cpu.a = r',
    'r = x | y\n    cpu._f = SZXYP[r]\n    cpu.a = r',
    'z = x - y\n    r = z & 0xFF\n    cpu._f = (SZXY[r] & 0xC0) | (y & 0x28) | ((x ^ y ^ r) & 0x10) | (((x ^ y) & (x ^ r) & 0x80) >> 5) | 2 | ((z >> 8) & 1)',
)


def main_sources():
    """{opcode: python source of a function f(cpu) -> T-states}"""
    src = {}

    def fn(op, body):
        src[op] = 'def f(cpu):\n    ' + body.strip('\n') + '\n'

    for op in range(0x40, 0x80):                       # LD r,r'
        if op == 0x76:
            continue
        d, s = REG[(op >> 3) & 7], REG[op & 7]
        if s is None:
            fn(op, 'cpu.%s = rd%s\n    cpu.q = 0\n    return 7' % (d, HL))
        elif d is None:
            fn(op, 'wr(%s, cpu.%s)\n    cpu.q = 0\n    return 7' % (HL, s))
        else:
            fn(op, 'cpu.%s = cpu.%s\n    cpu.q = 0\n    return 4' % (d, s))
    for i, d in enumerate(REG):                        # LD r,n
        op = 0x06 | i << 3
        if d is None:
            fn(op, OPERAND + '\n    wr(%s, n)\n    cpu.q = 0\n    return 10' % HL)
        else:
            fn(op, OPERAND + '\n    cpu.%s = n\n    cpu.q = 0\n    return 7' % d)
    for i, d in enumerate(REG):                        # INC r / DEC r
        if d is None:
            continue
        fn(0x04 | i << 3, '''x = cpu.%s
    r = (x + 1) & 0xFF
    cpu._f = (cpu._f & 1) | SZXY[r] | (0x10 if (r & 0x0F) == 0 else 0) | (4 if r == 0x80 else 0)
    cpu.%s = r
    cpu.q = cpu._f
    return 4''' % (d, d))
        fn(0x05 | i << 3, '''x = cpu.%s
    r = (x - 1) & 0xFF
    cpu._f = (cpu._f & 1) | SZXY[r] | 2 | (0x10 if (r & 0x0F) == 0x0F else 0) | (4 if r == 0x7F else 0)
    cpu.%s = r
    cpu.q = cpu._f
    return 4''' % (d, d))
    for g in range(8):                                 # ALU A,r / A,(HL) / A,n
        for i, s in enumerate(REG):
            if s is None:
                fn(0x80 | g << 3 | i, 'x = cpu.a\n    y = rd%s\n    %s\n    cpu.q = cpu._f\n    return 7'
                   % (HL, ALU[g]))
            else:
                fn(0x80 | g << 3 | i, 'x = cpu.a\n    y = cpu.%s\n    %s\n    cpu.q = cpu._f\n    return 4'
                   % (s, ALU[g]))
        fn(0xC6 | g << 3, OPERAND + '\n    x = cpu.a\n    y = n\n    %s\n    cpu.q = cpu._f\n    return 7'
           % ALU[g])
    for op, cond in ((0x18, 'True'), (0x20, COND[0]), (0x28, COND[1]), (0x30, COND[2]), (0x38, COND[3])):
        fn(op, '''pc = cpu.pc
    d = rd(pc)
    pc = (pc + 1) & 0xFFFF
    f = cpu._f
    cpu.q = 0
    if %s:
        pc = (pc + d - ((d & 0x80) << 1)) & 0xFFFF
        cpu.wz = pc
        cpu.pc = pc
        return 12
    cpu.pc = pc
    return 7''' % cond)
    fn(0x10, '''pc = cpu.pc
    d = rd(pc)
    pc = (pc + 1) & 0xFFFF
    b = (cpu.b - 1) & 0xFF
    cpu.b = b
    cpu.q = 0
    if b:
        pc = (pc + d - ((d & 0x80) << 1)) & 0xFFFF
        cpu.wz = pc
        cpu.pc = pc
        return 13
    cpu.pc = pc
    return 8''')
    for c in range(8):                                 # JP cc / CALL cc / RET cc
        fn(0xC2 | c << 3, WORD + '\n    cpu.wz = nn\n    f = cpu._f\n    if %s:\n        cpu.pc = nn\n'
           '    cpu.q = 0\n    return 10' % COND[c])
        fn(0xC4 | c << 3, WORD + '\n    cpu.wz = nn\n    f = cpu._f\n    cpu.q = 0\n    if not (%s):\n'
           '        return 10\n    %s\n    cpu.pc = nn\n    return 17' % (COND[c], PUSH.format(v='(pc + 2) & 0xFFFF')))
        fn(0xC0 | c << 3, 'f = cpu._f\n    cpu.q = 0\n    if not (%s):\n        return 5\n    %s\n'
           '    cpu.wz = w\n    cpu.pc = w\n    return 11' % (COND[c], POP))
    fn(0xC3, WORD + '\n    cpu.wz = nn\n    cpu.pc = nn\n    cpu.q = 0\n    return 10')
    fn(0xCD, WORD + '\n    cpu.wz = nn\n    ' + PUSH.format(v='(pc + 2) & 0xFFFF') +
       '\n    cpu.pc = nn\n    cpu.q = 0\n    return 17')
    fn(0xC9, POP + '\n    cpu.wz = w\n    cpu.pc = w\n    cpu.q = 0\n    return 10')
    for i, p in enumerate(PAIR):
        op = i << 4
        fn(0x01 | op, WORD + '\n    %s\n    cpu.q = 0\n    return 10' % set_pair(p, 'nn'))
        fn(0x03 | op, '%s\n    cpu.q = 0\n    return 6' % set_pair(p, '(%s + 1) & 0xFFFF' % get_pair(p)))
        fn(0x0B | op, '%s\n    cpu.q = 0\n    return 6' % set_pair(p, '(%s - 1) & 0xFFFF' % get_pair(p)))
        fn(0x09 | op, '''hl = %s
    y = %s
    cpu.wz = (hl + 1) & 0xFFFF
    z = hl + y
    r = z & 0xFFFF
    cpu._f = (cpu._f & 0xC4) | ((r >> 8) & 0x28) | (((hl ^ y ^ r) >> 8) & 0x10) | (z >> 16)
    cpu.h = r >> 8
    cpu.l = r & 0xFF
    cpu.q = cpu._f
    return 11''' % (HL, get_pair(p)))
        if p != 'sp':                                  # PUSH/POP BC DE HL
            fn(0xC5 | op, PUSH.format(v=get_pair(p)) + '\n    cpu.q = 0\n    return 11')
            fn(0xC1 | op, POP + '\n    cpu.%s = w >> 8\n    cpu.%s = w & 0xFF\n    cpu.q = 0\n    return 10'
               % (p[0], p[1]))
    fn(0xF5, PUSH.format(v='cpu.a << 8 | cpu._f') + '\n    cpu.q = 0\n    return 11')
    fn(0xF1, POP + '\n    cpu.a = w >> 8\n    cpu._f = w & 0xFF\n    cpu.q = 0\n    return 10')
    fn(0x22, WORD + '\n    wr(nn, cpu.l)\n    w = (nn + 1) & 0xFFFF\n    cpu.wz = w\n    wr(w, cpu.h)\n'
       '    cpu.q = 0\n    return 16')
    fn(0x2A, WORD + '\n    cpu.l = rd(nn)\n    w = (nn + 1) & 0xFFFF\n    cpu.wz = w\n    cpu.h = rd(w)\n'
       '    cpu.q = 0\n    return 16')
    fn(0x3A, WORD + '\n    cpu.a = rd(nn)\n    cpu.wz = (nn + 1) & 0xFFFF\n    cpu.q = 0\n    return 13')
    fn(0x32, WORD + '\n    a = cpu.a\n    wr(nn, a)\n    cpu.wz = (a << 8 | ((nn + 1) & 0xFF)) & 0xFFFF\n'
       '    cpu.q = 0\n    return 13')
    for op, p in ((0x0A, 'bc'), (0x1A, 'de')):
        fn(op, 'w = %s\n    cpu.a = rd(w)\n    cpu.wz = (w + 1) & 0xFFFF\n    cpu.q = 0\n    return 7' % get_pair(p))
    for op, p in ((0x02, 'bc'), (0x12, 'de')):
        fn(op, 'w = %s\n    a = cpu.a\n    wr(w, a)\n    cpu.wz = (a << 8 | ((w + 1) & 0xFF)) & 0xFFFF\n'
           '    cpu.q = 0\n    return 7' % get_pair(p))
    fn(0xEB, 'cpu.d, cpu.h = cpu.h, cpu.d\n    cpu.e, cpu.l = cpu.l, cpu.e\n    cpu.q = 0\n    return 4')
    fn(0xE9, 'cpu.pc = %s\n    cpu.q = 0\n    return 4' % HL)
    fn(0x00, 'cpu.q = 0\n    return 4')
    return src


def ed_sources():
    """{second byte: source} for ED-prefixed instructions; T-states include the prefix."""
    src = {}

    def fn(op, body):
        src[op] = 'def f(cpu):\n    ' + body.strip('\n') + '\n'

    for i, p in enumerate(PAIR):
        op = i << 4
        y = get_pair(p)
        fn(0x42 | op, '''hl = %s
    y = %s
    cpu.wz = (hl + 1) & 0xFFFF
    z = hl - y - (cpu._f & 1)
    r = z & 0xFFFF
    cpu._f = (((r >> 8) & 0xA8) | (0x40 if r == 0 else 0) | (((hl ^ y ^ r) >> 8) & 0x10)
              | (((hl ^ y) & (hl ^ r) & 0x8000) >> 13) | 2 | ((z >> 16) & 1))
    cpu.h = r >> 8
    cpu.l = r & 0xFF
    cpu.q = cpu._f
    return 15''' % (HL, y))
        fn(0x4A | op, '''hl = %s
    y = %s
    cpu.wz = (hl + 1) & 0xFFFF
    z = hl + y + (cpu._f & 1)
    r = z & 0xFFFF
    cpu._f = (((r >> 8) & 0xA8) | (0x40 if r == 0 else 0) | (((hl ^ y ^ r) >> 8) & 0x10)
              | (((hl ^ y ^ 0x8000) & (hl ^ r) & 0x8000) >> 13) | (z >> 16))
    cpu.h = r >> 8
    cpu.l = r & 0xFF
    cpu.q = cpu._f
    return 15''' % (HL, y))
        fn(0x43 | op, WORD + '\n    v = %s\n    wr(nn, v & 0xFF)\n    w = (nn + 1) & 0xFFFF\n    cpu.wz = w\n'
           '    wr(w, v >> 8)\n    cpu.q = 0\n    return 20' % y)
        fn(0x4B | op, WORD + '\n    lo = rd(nn)\n    w = (nn + 1) & 0xFFFF\n    cpu.wz = w\n'
           '    %s\n    cpu.q = 0\n    return 20' % set_pair(p, 'lo | rd(w) << 8'))
    return src


def _compile(sources, rd, wr, cpu):
    out = {}
    for op, s in sources.items():
        ns = {'rd': rd, 'wr': wr, 'SZXY': SZXY, 'SZXYP': SZXYP, 'CPU': cpu}
        # f(cpu=CPU): callable as f(cpu) from the dispatch table, or as f()
        exec(compile(s.replace('def f(cpu):', 'def f(cpu=CPU):', 1), '<z80fast %02X>' % op, 'exec'), ns)
        ns['f'].z80fast = True
        out[op] = ns['f']
    return out


MAIN = main_sources()
ED = ed_sources()


class FastZ80(Z80CPU):
    """Z80CPU with generated handlers for the common opcodes (see above).

    The memory callables are bound into the generated functions, so they must
    be passed to the constructor and not replaced afterwards.

    run_page[opcode]() executes the main-page instruction whose opcode byte
    has just been fetched (PC already past it, R already refreshed) and
    returns its T-states, like the table entry it comes from.
    """

    def __init__(self, read_byte, write_byte, **kw):
        super().__init__(read_byte, write_byte, **kw)
        main = list(self._main_page)
        for op, f in _compile(MAIN, read_byte, write_byte, self).items():
            main[op] = (f, None)
        ed = list(self._ed_page)
        for op, f in _compile(ED, read_byte, write_byte, self).items():
            ed[op] = (f, None)
        self._main_page = main
        self._ed_page = ed
        self.run_page = [h if getattr(h, 'z80fast', False) else
                         h.__get__(self) if a is None else partial(h, self, a)
                         for h, a in main]
