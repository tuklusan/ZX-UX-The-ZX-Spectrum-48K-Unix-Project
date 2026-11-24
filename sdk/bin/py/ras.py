#!/usr/bin/env python3
# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""ras - Z80 assembler producing SSO1 relocatable objects (ZX-UX SDK).

  ras.py [-o out.sso] file.asm

Syntax: labels at column 0 (colon optional), local labels .name (scoped to
the previous global label), directives section text|data|bss, global, extern,
equ, db, dw, ds, plus the pseudo-instruction  j [cc,]label  which assembles to
JR when the target is in range and the condition allows it, else JP.
Undefined symbols are imports.  Numbers: 123 0x7F 7Fh $7F #7F %1010 'c'.
"""
import sys
import os
import struct

R8 = {'b': 0, 'c': 1, 'd': 2, 'e': 3, 'h': 4, 'l': 5, '(hl)': 6, 'a': 7}
RP = {'bc': 0, 'de': 1, 'hl': 2, 'sp': 3}
RP2 = {'bc': 0, 'de': 1, 'hl': 2, 'af': 3}
CC = {'nz': 0, 'z': 1, 'nc': 2, 'c': 3, 'po': 4, 'pe': 5, 'p': 6, 'm': 7}
ALU = {'add': 0, 'adc': 1, 'sub': 2, 'sbc': 3, 'and': 4, 'xor': 5, 'or': 6, 'cp': 7}
ROT = {'rlc': 0, 'rrc': 1, 'rl': 2, 'rr': 3, 'sla': 4, 'sra': 5, 'sll': 6, 'srl': 7}
SIMPLE = {'nop': [0], 'halt': [0x76], 'di': [0xF3], 'ei': [0xFB], 'exx': [0xD9],
          'daa': [0x27], 'cpl': [0x2F], 'ccf': [0x3F], 'scf': [0x37], 'neg': [0xED, 0x44],
          'rlca': [7], 'rla': [0x17], 'rrca': [0x0F], 'rra': [0x1F],
          'ldi': [0xED, 0xA0], 'ldir': [0xED, 0xB0], 'ldd': [0xED, 0xA8], 'lddr': [0xED, 0xB8],
          'cpi': [0xED, 0xA1], 'cpir': [0xED, 0xB1], 'cpd': [0xED, 0xA9], 'cpdr': [0xED, 0xB9],
          'ini': [0xED, 0xA2], 'inir': [0xED, 0xB2], 'outi': [0xED, 0xA3], 'otir': [0xED, 0xB3],
          'reti': [0xED, 0x4D], 'retn': [0xED, 0x45], 'rld': [0xED, 0x6F], 'rrd': [0xED, 0x67]}
SECTIONS = ['text', 'data', 'bss']


class AsmError(Exception):
    pass


class Val:
    """Expression value: constant + optional relocatable base."""
    __slots__ = ('v', 'base')

    def __init__(self, v, base=None):
        self.v = v
        self.base = base          # Value kind: literal, local section, or external symbol. Choose your poison.


class Asm:
    def __init__(self, fname='<asm>'):
        self.fname = fname
        self.syms = {}            # name -> Val (section-relative for labels)
        self.globals = set()
        self.externs = set()
        self.lines = []
        self.aligns = {}          # section -> required alignment (align directive)

    # Parse the source. Even punctuation has a curfew.
    def load(self, text):
        glob = ''
        for n, raw in enumerate(text.split('\n'), 1):
            line = self.strip_comment(raw)
            if not line.strip():
                continue
            label = None
            rest = line
            if line[0] not in ' \t':
                tok = line.split(None, 1)
                label = tok[0]
                rest = tok[1] if len(tok) > 1 else ''
                if label.endswith(':'):
                    label = label[:-1]
            rest = rest.strip()
            parts = rest.split(None, 1)
            mn = parts[0].lower() if parts else ''
            ops = self.split_ops(parts[1]) if len(parts) > 1 else []
            if label:
                if label.startswith('.'):
                    label = glob + label
                elif mn != 'equ':
                    glob = label
            ops = [self.local(o, glob) for o in ops]
            self.lines.append((n, label, mn, ops, raw))

    @staticmethod
    def strip_comment(s):
        out = []
        q = None
        for c in s:
            if q:
                out.append(c)
                if c == q:
                    q = None
                continue
            if c in '"\'':
                if c == "'" and out and out[-1].lower() == 'f' and ''.join(out).lower().rstrip().endswith('af'):
                    out.append(c)
                    continue
                q = c
            elif c == ';':
                break
            out.append(c)
        return ''.join(out).rstrip()

    @staticmethod
    def split_ops(s):
        ops, cur, q, depth = [], '', None, 0
        for c in s:
            if q:
                cur += c
                if c == q:
                    q = None
                continue
            if c in '"\'' and not cur.lower().strip().endswith('af'):
                q = c
            if c == '(':
                depth += 1
            elif c == ')':
                depth -= 1
            if c == ',' and depth == 0 and not q:
                ops.append(cur.strip())
                cur = ''
            else:
                cur += c
        if cur.strip():
            ops.append(cur.strip())
        return ops

    @staticmethod
    def local(op, glob):
        if '.' not in op or op.startswith('"') or op.startswith("'"):
            return op
        out, i = '', 0
        while i < len(op):
            c = op[i]
            if c == '.' and (i == 0 or not (op[i - 1].isalnum() or op[i - 1] in '_?@')):
                out += glob
            out += c
            i += 1
        return out

    # Evaluate expressions. Hex numbers do not accept vibes.
    def expr(self, s, pc=None, need=True):
        self.toks = self.tokenize(s)
        self.ti = 0
        self.pc = pc
        self.need = need
        v = self.e_or()
        if self.ti != len(self.toks):
            raise AsmError('bad expression: %s' % s)
        return v

    @staticmethod
    def tokenize(s):
        toks, i = [], 0
        while i < len(s):
            c = s[i]
            if c in ' \t':
                i += 1
                continue
            if s.startswith(('<<', '>>'), i):
                toks.append(s[i:i + 2])
                i += 2
                continue
            if c == "'" and i + 2 < len(s) and s[i + 2] == "'":
                toks.append(('n', ord(s[i + 1])))
                i += 3
                continue
            if c in '+-*/%&|^~()':
                toks.append(c)
                i += 1
                continue
            if c == '$' and (i + 1 >= len(s) or s[i + 1] not in '0123456789abcdefABCDEF'):
                toks.append(('pc',))
                i += 1
                continue
            j = i
            if c in '$#%':
                j += 1
            while j < len(s) and (s[j].isalnum() or s[j] in '_?@.'):
                j += 1
            w = s[i:j]
            if not w:
                raise AsmError('bad character %r' % c)
            toks.append(('w', w))
            i = j
        return toks

    def num(self, w):
        lw = w.lower()
        try:
            if lw.startswith('0x'):
                return int(lw[2:], 16)
            if lw[0] in '$#':
                return int(lw[1:], 16)
            if lw[0] == '%':
                return int(lw[1:], 2)
            if lw[0].isdigit():
                if lw.endswith('h'):
                    return int(lw[:-1], 16)
                if lw.endswith('b') and all(ch in '01' for ch in lw[:-1]):
                    return int(lw[:-1], 2)
                return int(lw, 10)
        except ValueError:
            raise AsmError('bad number %s' % w)
        return None

    def peekt(self):
        return self.toks[self.ti] if self.ti < len(self.toks) else None

    def e_or(self):
        a = self.e_xor()
        while self.peekt() == '|':
            self.ti += 1
            a = self.arith('|', a, self.e_xor())
        return a

    def e_xor(self):
        a = self.e_and()
        while self.peekt() == '^':
            self.ti += 1
            a = self.arith('^', a, self.e_and())
        return a

    def e_and(self):
        a = self.e_sh()
        while self.peekt() == '&':
            self.ti += 1
            a = self.arith('&', a, self.e_sh())
        return a

    def e_sh(self):
        a = self.e_add()
        while self.peekt() in ('<<', '>>'):
            op = self.toks[self.ti]
            self.ti += 1
            a = self.arith(op, a, self.e_add())
        return a

    def e_add(self):
        a = self.e_mul()
        while self.peekt() in ('+', '-'):
            op = self.toks[self.ti]
            self.ti += 1
            b = self.e_mul()
            if op == '+':
                if a.base and b.base:
                    raise AsmError('adding two addresses')
                a = Val(a.v + b.v, a.base or b.base)
            else:
                if b.base:
                    if a.base != b.base:
                        if self.need:
                            raise AsmError('difference of unrelated addresses')
                        a = Val(0)
                    else:
                        a = Val(a.v - b.v)
                else:
                    a = Val(a.v - b.v, a.base)
        return a

    def e_mul(self):
        a = self.e_un()
        while self.peekt() in ('*', '/', '%'):
            op = self.toks[self.ti]
            self.ti += 1
            a = self.arith(op, a, self.e_un())
        return a

    def arith(self, op, a, b):
        if a.base or b.base:
            if self.need:
                raise AsmError("operator '%s' on an address" % op)
            return Val(0)
        x, y = a.v, b.v
        if op in '/%' and y == 0:
            if self.need:
                raise AsmError('division by zero')
            return Val(0)
        return Val({'|': x | y, '^': x ^ y, '&': x & y, '<<': x << y, '>>': x >> y,
                    '*': x * y, '/': x // y if y else 0, '%': x % y if y else 0}[op])

    def e_un(self):
        t = self.peekt()
        if t == '-':
            self.ti += 1
            a = self.e_un()
            if a.base:
                raise AsmError('negated address')
            return Val(-a.v)
        if t == '+':
            self.ti += 1
            return self.e_un()
        if t == '~':
            self.ti += 1
            a = self.e_un()
            if a.base:
                raise AsmError('complemented address')
            return Val(~a.v)
        if t == '(':
            self.ti += 1
            a = self.e_or()
            if self.peekt() != ')':
                raise AsmError('missing )')
            self.ti += 1
            return a
        self.ti += 1
        if t is None:
            raise AsmError('missing operand')
        if t[0] == 'n':
            return Val(t[1])
        if t[0] == 'pc':
            if self.pc is None:
                raise AsmError('$ not allowed here')
            return Val(self.pc[1], ('sec', self.pc[0]))
        w = t[1]
        n = self.num(w)
        if n is not None:
            return Val(n)
        if w in ('high', 'low') and self.peekt() == '(':
            a = self.e_un()
            if a.base:
                raise AsmError('high/low of an address')
            return Val((a.v >> 8) & 255 if w == 'high' else a.v & 255)
        if w in self.syms:
            return self.syms[w]
        if self.need == 'final':
            self.externs.add(w)
            return Val(0, ('ext', w))
        return Val(0, ('ext', w)) if not self.need else self.undefined(w)

    def undefined(self, w):
        self.externs.add(w)
        return Val(0, ('ext', w))

    # Parse operands. The registers are fussy roommates.
    @staticmethod
    def is_ind(o):
        return o.startswith('(') and o.endswith(')') and Asm.balanced(o[1:-1])

    @staticmethod
    def balanced(s):
        d = 0
        for c in s:
            if c == '(':
                d += 1
            elif c == ')':
                d -= 1
                if d < 0:
                    return False
        return d == 0

    def idx(self, o):
        """'(ix+d)' -> ('ix', d expr string) or None."""
        lo = o.lower().replace(' ', '')
        if self.is_ind(o):
            inner = lo[1:-1]
            if inner in ('ix', 'iy'):
                return inner, '0'
            if inner[:2] in ('ix', 'iy') and inner[2:3] in '+-':
                return inner[:2], o.strip()[1:-1].strip()[2:]
        return None

    # Encode instructions. One wrong bit is plenty.
    def encode(self, mn, ops, pc, final):
        """-> list of items: ints (bytes), ('w', Val) word, ('b', Val) byte,
        ('r', Val) relative byte."""
        lops = [o.lower().replace(' ', '') for o in ops]
        n = len(ops)

        def ev(s):
            return self.expr(s, pc, 'final' if final else False)

        def byte(s):
            return ('b', ev(s))

        def word(s):
            return ('w', ev(s))

        def r8(o):
            return R8.get(o)

        def disp(ix, d):
            pre = 0xDD if ix == 'ix' else 0xFD
            return pre, ('d', ev(d) if d != '0' else Val(0))

        if mn in SIMPLE and n == 0:
            return list(SIMPLE[mn])
        if mn == 'ld' and n == 2:
            a, b = lops
            if r8(a) is not None and r8(b) is not None:
                if a == b == '(hl)':
                    raise AsmError('ld (hl),(hl)')
                return [0x40 + r8(a) * 8 + r8(b)]
            ia, ib = self.idx(ops[0]), self.idx(ops[1])
            if ia and r8(b) is not None and b != '(hl)':
                p, d = disp(*ia)
                return [p, 0x70 + r8(b), d]
            if ib and r8(a) is not None and a != '(hl)':
                p, d = disp(*ib)
                return [p, 0x46 + r8(a) * 8, d]
            if ia:
                p, d = disp(*ia)
                return [p, 0x36, d, byte(ops[1])]
            if a == 'a':
                if b == '(bc)':
                    return [0x0A]
                if b == '(de)':
                    return [0x1A]
                if b == 'i':
                    return [0xED, 0x57]
                if b == 'r':
                    return [0xED, 0x5F]
                if self.is_ind(ops[1]):
                    return [0x3A, word(ops[1][1:-1])]
            if b == 'a':
                if a == '(bc)':
                    return [0x02]
                if a == '(de)':
                    return [0x12]
                if a == 'i':
                    return [0xED, 0x47]
                if a == 'r':
                    return [0xED, 0x4F]
                if self.is_ind(ops[0]):
                    return [0x32, word(ops[0][1:-1])]
            if r8(a) is not None:
                return [0x06 + r8(a) * 8, byte(ops[1])]
            if a == 'sp' and b in ('hl', 'ix', 'iy'):
                return {'hl': [0xF9], 'ix': [0xDD, 0xF9], 'iy': [0xFD, 0xF9]}[b]
            if a in RP or a in ('ix', 'iy'):
                pre = [] if a in RP else [0xDD if a == 'ix' else 0xFD]
                if self.is_ind(ops[1]):
                    w = word(ops[1][1:-1])
                    if a in ('hl', 'ix', 'iy'):
                        return pre + [0x2A, w]
                    return [0xED, 0x4B + RP[a] * 16, w]
                return pre + [0x01 + RP.get(a, 2) * 16, word(ops[1])]
            if self.is_ind(ops[0]) and (b in RP or b in ('ix', 'iy')):
                w = word(ops[0][1:-1])
                if b == 'hl':
                    return [0x22, w]
                if b in ('ix', 'iy'):
                    return [0xDD if b == 'ix' else 0xFD, 0x22, w]
                return [0xED, 0x43 + RP[b] * 16, w]
            raise AsmError('bad ld operands')
        if mn in ('push', 'pop') and n == 1:
            a = lops[0]
            base = 0xC5 if mn == 'push' else 0xC1
            if a in RP2:
                return [base + RP2[a] * 16]
            if a in ('ix', 'iy'):
                return [0xDD if a == 'ix' else 0xFD, base + 0x20]
        if mn == 'ex' and n == 2:
            k = (lops[0], lops[1])
            t = {('de', 'hl'): [0xEB], ('af', "af'"): [0x08], ('(sp)', 'hl'): [0xE3],
                 ('(sp)', 'ix'): [0xDD, 0xE3], ('(sp)', 'iy'): [0xFD, 0xE3]}
            if k in t:
                return t[k]
        if mn in ALU:
            if n == 2 and lops[0] == 'a':
                lops, ops = lops[1:], ops[1:]
                n = 1
            if n == 2 and mn in ('add', 'adc', 'sbc') and lops[0] in ('hl', 'ix', 'iy'):
                a, b = lops
                if a == 'hl':
                    if b not in RP:
                        raise AsmError('bad 16-bit operand')
                    return {'add': [0x09 + RP[b] * 16], 'adc': [0xED, 0x4A + RP[b] * 16],
                            'sbc': [0xED, 0x42 + RP[b] * 16]}[mn]
                if mn == 'add':
                    m = {'bc': 0, 'de': 1, a: 2, 'sp': 3}
                    if b not in m:
                        raise AsmError('bad add ix operand')
                    return [0xDD if a == 'ix' else 0xFD, 0x09 + m[b] * 16]
            if n == 1:
                o = lops[0]
                k = ALU[mn]
                if r8(o) is not None:
                    return [0x80 + k * 8 + r8(o)]
                ix = self.idx(ops[0])
                if ix:
                    p, d = disp(*ix)
                    return [p, 0x86 + k * 8, d]
                return [0xC6 + k * 8, byte(ops[0])]
        if mn in ('inc', 'dec') and n == 1:
            o = lops[0]
            k = 0 if mn == 'inc' else 1
            if r8(o) is not None:
                return [0x04 + k + r8(o) * 8]
            if o in RP:
                return [0x03 + k * 8 + RP[o] * 16]
            if o in ('ix', 'iy'):
                return [0xDD if o == 'ix' else 0xFD, 0x23 + k * 8]
            ix = self.idx(ops[0])
            if ix:
                p, d = disp(*ix)
                return [p, 0x34 + k, d]
        if mn in ROT and n == 1:
            o = lops[0]
            if r8(o) is not None:
                return [0xCB, ROT[mn] * 8 + r8(o)]
            ix = self.idx(ops[0])
            if ix:
                p, d = disp(*ix)
                return [p, 0xCB, d, ROT[mn] * 8 + 6]
        if mn in ('bit', 'res', 'set') and n == 2:
            b = self.expr(ops[0]).v
            if not 0 <= b <= 7:
                raise AsmError('bit number')
            base = {'bit': 0x40, 'res': 0x80, 'set': 0xC0}[mn] + b * 8
            o = lops[1]
            if r8(o) is not None:
                return [0xCB, base + r8(o)]
            ix = self.idx(ops[1])
            if ix:
                p, d = disp(*ix)
                return [p, 0xCB, d, base + 6]
        if mn == 'jp':
            if n == 1:
                o = lops[0]
                if o in ('(hl)', 'hl'):
                    return [0xE9]
                if o in ('(ix)', '(iy)'):
                    return [0xDD if o == '(ix)' else 0xFD, 0xE9]
                return [0xC3, word(ops[0])]
            if n == 2 and lops[0] in CC:
                return [0xC2 + CC[lops[0]] * 8, word(ops[1])]
        if mn == 'jr':
            if n == 1:
                return [0x18, ('r', ev(ops[0]))]
            if n == 2 and lops[0] in ('nz', 'z', 'nc', 'c'):
                return [0x20 + CC[lops[0]] * 8, ('r', ev(ops[1]))]
        if mn == 'djnz' and n == 1:
            return [0x10, ('r', ev(ops[0]))]
        if mn == 'call':
            if n == 1:
                return [0xCD, word(ops[0])]
            if n == 2 and lops[0] in CC:
                return [0xC4 + CC[lops[0]] * 8, word(ops[1])]
        if mn == 'ret':
            if n == 0:
                return [0xC9]
            if n == 1 and lops[0] in CC:
                return [0xC0 + CC[lops[0]] * 8]
        if mn == 'rst' and n == 1:
            v = self.expr(ops[0]).v
            if v & ~0x38:
                raise AsmError('bad rst')
            return [0xC7 + v]
        if mn == 'im' and n == 1:
            return [0xED, {0: 0x46, 1: 0x56, 2: 0x5E}[self.expr(ops[0]).v]]
        if mn == 'in' and n == 2:
            if lops[0] == 'a' and lops[1] != '(c)':
                return [0xDB, byte(ops[1][1:-1])]
            if lops[1] == '(c)' and r8(lops[0]) is not None:
                return [0xED, 0x40 + r8(lops[0]) * 8]
        if mn == 'out' and n == 2:
            if lops[1] == 'a' and lops[0] != '(c)':
                return [0xD3, byte(ops[0][1:-1])]
            if lops[0] == '(c)' and r8(lops[1]) is not None:
                return [0xED, 0x41 + r8(lops[1]) * 8]
        raise AsmError('bad instruction: %s %s' % (mn, ', '.join(ops)))

    # Resolve symbols and assemble. Names need real addresses.
    def assemble(self):
        long_j = set()          # Expand any out-of-range j to jp. Shortcuts have limits.
        for k in range(50):
            self.first = k == 0
            ok, data = self.pass_(long_j, False)
            if ok and k:
                break
        else:
            raise AsmError('branch relaxation did not converge')
        self.pass_(long_j, True)
        return self

    def pass_(self, long_j, final):
        """One layout pass.  Returns (stable, None)."""
        pcs = {s: 0 for s in SECTIONS}
        sec = 'text'
        self.out = {s: bytearray() for s in SECTIONS}
        self.relocs = {s: [] for s in SECTIONS}
        newsyms = {}
        stable = True
        if final:
            self.externs = set()
        for li, (n, label, mn, ops, raw) in enumerate(self.lines):
            try:
                pc = (sec, pcs[sec])
                if mn == 'equ':
                    if not label:
                        raise AsmError('equ without a name')
                    v = self.expr(ops[0], pc, False)
                    self.syms[label] = v
                    continue
                if label:
                    if label in newsyms:
                        raise AsmError('duplicate label %s' % label)
                    newsyms[label] = Val(pcs[sec], ('sec', sec))
                    old = self.syms.get(label)
                    if old is None or old.v != pcs[sec] or old.base != ('sec', sec):
                        stable = False
                    self.syms[label] = newsyms[label]
                if not mn:
                    continue
                if mn == 'section':
                    sec = ops[0].lower()
                    if sec not in SECTIONS:
                        raise AsmError('unknown section')
                    continue
                if mn == 'global' or mn == 'public':
                    self.globals.update(ops)
                    continue
                if mn == 'extern':
                    continue
                if mn in ('db', 'defb', 'defm', 'dm'):
                    items = []
                    for o in ops:
                        if o[0] in '"\'' and len(o) >= 2 and o[-1] == o[0] and len(o) != 3 or (o[0] == '"'):
                            items += list(o[1:-1].encode('latin-1'))
                        else:
                            items.append(('b', self.expr(o, pc, 'final' if final else False)))
                elif mn in ('dw', 'defw'):
                    items = [('w', self.expr(o, pc, 'final' if final else False)) for o in ops]
                elif mn in ('ds', 'defs'):
                    cnt = self.expr(ops[0], pc).v
                    fill = self.expr(ops[1], pc).v if len(ops) > 1 else 0
                    if sec == 'bss':
                        pcs[sec] += cnt
                        continue
                    items = [fill & 255] * cnt
                elif mn == 'align':
                    a = self.expr(ops[0], pc).v
                    if a < 1 or a > 128 or a & (a - 1):
                        raise AsmError('align needs a power of 2 up to 128')
                    # the section itself must start this aligned (SSO1 align)
                    self.aligns[sec] = max(self.aligns.get(sec, 1), a)
                    pad = (-pcs[sec]) % a
                    if sec == 'bss':
                        pcs[sec] += pad
                        continue
                    items = [0] * pad
                elif mn == 'j':
                    cc = ops[0].lower() if len(ops) == 2 else None
                    tgt = ops[-1]
                    can_jr = cc in (None, 'nz', 'z', 'nc', 'c')
                    if li in long_j or not can_jr:
                        items = self.encode('jp', ops, pc, final)
                    else:
                        items = self.encode('jr', ops, pc, final)
                        v = self.expr(tgt, pc, False)
                        d = v.v - (pcs[sec] + 2)
                        known = v.base != ('ext', tgt.strip()) or tgt.strip() in self.syms
                        imported = v.base is not None and v.base[0] == 'ext' and tgt.strip() not in self.syms
                        if imported and not self.first:
                            long_j.add(li)          # External target? Use jp; no long-distance jr.
                            stable = False
                            items = self.encode('jp', ops, pc, final)
                        elif not self.first and known and (v.base != ('sec', sec) or not -128 <= d <= 127):
                            long_j.add(li)
                            stable = False
                            items = self.encode('jp', ops, pc, final)
                else:
                    if sec == 'bss':
                        raise AsmError('code in bss')
                    items = self.encode(mn, ops, pc, final)
                if sec == 'bss':
                    raise AsmError('data in bss: use ds')
                self.emit(sec, pcs, items, final, n)
            except AsmError as e:
                raise AsmError('%s:%d: %s\n    %s' % (self.fname, n, e, raw.strip()))
        self.sizes = dict(pcs)
        return stable, None

    def emit(self, sec, pcs, items, final, n):
        buf = self.out[sec]
        start = pcs[sec]
        for it in items:
            pos = pcs[sec]
            if isinstance(it, int):
                buf.append(it & 255)
                pcs[sec] += 1
                continue
            k, v = it
            if k == 'w':
                if v.base and final:
                    self.relocs[sec].append((pos, v.base))
                buf += (v.v & 0xFFFF).to_bytes(2, 'little')
                pcs[sec] += 2
                if final and not v.base and not -32768 <= v.v <= 65535:
                    raise AsmError('word out of range')
            elif k == 'b' or k == 'd':
                if final and v.base:
                    raise AsmError('relocatable value in a byte')
                if final and k == 'b' and not -128 <= v.v <= 255:
                    raise AsmError('byte out of range')
                if final and k == 'd' and not -128 <= v.v <= 127:
                    raise AsmError('index displacement out of range')
                buf.append(v.v & 255)
                pcs[sec] += 1
            elif k == 'r':
                d = v.v - (start + len(items) if False else pos + 1)
                if final:
                    if v.base and v.base[0] == 'ext':
                        raise AsmError('undefined label %s' % v.base[1])
                    if v.base != ('sec', sec) or not -128 <= d <= 127:
                        raise AsmError('relative jump out of range')
                buf.append(d & 255)
                pcs[sec] += 1

    # Write the object. The linker reads the small print.
    def sso(self):
        used = {v.base[1] for v in self.syms.values() if v.base and v.base[0] == 'sec'}
        secs = [s for s in SECTIONS if self.sizes[s] or s == 'text' or s in used]
        sidx = {s: i + 1 for i, s in enumerate(secs)}
        names = []
        symrecs = []
        symidx = {}

        def addsym(name, sec, binding, value):
            symidx[name] = len(symrecs)
            symrecs.append((len(b''.join(names)), sec, binding, value))
            names.append(name.encode() + b'\0')

        for name, v in sorted(self.syms.items()):
            if v.base and v.base[0] == 'sec':
                if name in self.globals or not name.startswith('@'):
                    addsym(name, sidx.get(v.base[1], 0), 1 if name in self.globals else 0, v.v & 0xFFFF)
            elif name in self.globals:
                if v.base and v.base[0] == 'ext':
                    raise AsmError('global %s is an import' % name)
                addsym(name, 255, 1, v.v & 0xFFFF)
        for name in sorted(self.externs):
            if name not in symidx and name not in self.syms:
                addsym(name, 0, 1, 0)
        for g in sorted(self.globals):
            if g not in self.syms:
                raise AsmError('global %s not defined' % g)
        out = bytearray(b'SSO1')
        strtab = b''.join(names)
        out += struct.pack('<BBHHI', 1, 0, len(secs), len(symrecs), len(strtab))
        for s in secs:
            kind = SECTIONS.index(s) + 1
            rel = []
            for pos, base in self.relocs[s]:
                if base[0] == 'sec':
                    rel.append(struct.pack('<HBBH', pos, 1, 0, sidx[base[1]]))
                else:
                    rel.append(struct.pack('<HBBH', pos, 2, 0, symidx[base[1]]))
            out += struct.pack('<BBHH', kind, self.aligns.get(s, 1), self.sizes[s], len(rel))
            if s != 'bss':
                out += self.out[s]
            out += b''.join(rel)
        for rec in symrecs:
            out += struct.pack('<IBBH', *rec)
        out += strtab
        return bytes(out)


def assemble_text(text, fname='<asm>'):
    a = Asm(fname)
    a.load(text)
    a.assemble()
    return a.sso()


def main(argv):
    out = None
    files = []
    i = 0
    while i < len(argv):
        if argv[i] == '-o':
            out = argv[i + 1]
            i += 2
            continue
        files.append(argv[i])
        i += 1
    if len(files) != 1:
        print(__doc__)
        return 2
    src = files[0]
    try:
        data = assemble_text(open(src, encoding='latin-1').read(), os.path.basename(src))
    except AsmError as e:
        print('ras: %s' % e, file=sys.stderr)
        return 1
    out = out or os.path.splitext(src)[0] + '.sso'
    open(out, 'wb').write(data)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
