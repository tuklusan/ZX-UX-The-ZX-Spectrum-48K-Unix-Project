# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""Five-byte Spectrum floating point computed by the real 48K ROM.

The ROM calculator runs on the SDK's bundled Z80 (sdk/zxcore.py), so the
compiler's constant folding gives exactly the bytes the ZX-UX kernel's float
service (which runs the same ROM code) gives at run time.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import zxcore  # noqa: E402

# kernel/runtime float-service operation codes (sys fp, see sdk/doc)
ADD, SUB, MUL, DIV, POW, ABS, NEG, TRUNC, EXP, LN, SIN, COS, TAN, ASN, ACS, ATN, SQR = range(1, 18)
CALC = {ADD: 0x0F, SUB: 0x03, MUL: 0x04, DIV: 0x05, POW: 0x06, ABS: 0x2A,
        NEG: 0x1B, TRUNC: 0x3A, EXP: 0x26, LN: 0x25, SIN: 0x1F, COS: 0x20,
        TAN: 0x21, ASN: 0x22, ACS: 0x23, ATN: 0x24, SQR: 0x28}
BINARY = {ADD, SUB, MUL, DIV, POW}

STKBOT, STKEND, MEM, ERR_SP, CH_ADD, ERR_NR = 0x5C63, 0x5C65, 0x5C68, 0x5C3D, 0x5C5D, 0x5C3A
CSTK = 0x9000
STUB = 0x8000
TRAP = 0x8100
TEXT = 0xB000


class FPError(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__('ROM error %d' % code)


def setup_memory(mem):
    """Point the ROM's calculator system variables at scratch RAM."""
    for a, v in ((STKBOT, CSTK), (STKEND, CSTK), (MEM, 0x5C92)):
        mem[a] = v & 255
        mem[a + 1] = v >> 8
    mem[0x5C3B] = 0       # FLAGS
    mem[0x5C71] = 0       # FLAGX


class RomFP:
    def __init__(self):
        self.zx = zxcore.Spectrum()
        self.mem = self.zx.mem
        setup_memory(self.mem)
        self.cache = {}

    def _w(self, a, v):
        self.mem[a] = v & 255
        self.mem[a + 1] = (v >> 8) & 255

    def _r(self, a):
        return self.mem[a] | self.mem[a + 1] << 8

    def _run(self, pc, regs=None):
        m = self.mem
        zx = self.zx
        sp = 0xA000 - 2
        self._w(sp, TRAP)
        self._w(ERR_SP, sp)
        m[ERR_NR] = 0xFF
        zx.set(iy=0x5C3A, sp=sp, iff1=False, iff2=False)
        if regs:
            zx.set(**regs)
        # a call frame returning to TRAP; ERR_SP's frame also ends at TRAP
        if not zx.call(pc, TRAP, tlimit=200_000_000):
            raise RuntimeError('ROM float call did not return')
        if m[ERR_NR] != 0xFF:
            raise FPError(m[ERR_NR])

    def _calc(self, op, x, y=None):
        m = self.mem
        m[CSTK:CSTK + 5] = list(x)
        end = CSTK + 5
        if y is not None:
            m[end:end + 5] = list(y)
            end += 5
        self._w(STKBOT, CSTK)
        self._w(STKEND, end)
        m[STUB:STUB + 4] = [0xEF, op, 0x38, 0xC9]      # rst 28h / op / end-calc / ret
        self._run(STUB)
        e = self._r(STKEND)
        return bytes(m[e - 5:e])

    def op(self, op, x, y=None):
        key = (op, bytes(x), None if y is None else bytes(y))
        if key not in self.cache:
            if op == NEG:
                # ROM 'negate' uses opcode 1Bh, as the kernel does.
                self.cache[key] = self._calc(0x1B, x)
            else:
                self.cache[key] = self._calc(CALC[op], x, y)
        return self.cache[key]

    def from_text(self, text):
        """Decimal literal -> five bytes, by the ROM's own number parser."""
        if text in self.cache:
            return self.cache[text]
        m = self.mem
        t = text.encode() + b'\x0d'
        m[TEXT:TEXT + len(t)] = list(t)
        self._w(CH_ADD, TEXT)
        self._w(STKBOT, CSTK)
        self._w(STKEND, CSTK)
        # 2C9B DEC-TO-FP: CH_ADD -> first character, A = that character
        self._run(0x2C9B, {'a': t[0]})
        e = self._r(STKEND)
        if e != CSTK + 5 or self._r(CH_ADD) != TEXT + len(t) - 1:
            raise FPError(-1)
        v = bytes(m[e - 5:e])
        self.cache[text] = v
        return v

    def from_int(self, v, signed):
        """int (16-bit value) -> float, as the runtime's conversion does."""
        v &= 0xFFFF
        neg = signed and v >= 0x8000
        mag = (0x10000 - v) if neg else v
        r = bytes((0, 0, mag & 255, mag >> 8, 0))
        if neg:
            r = self.op(NEG, r)
        return r

    def to_int(self, x, signed):
        """float -> int with truncation; raises FPError on range failure."""
        t = self.op(TRUNC, x)
        m = self.mem
        m[CSTK:CSTK + 5] = list(t)
        self._w(STKBOT, CSTK)
        self._w(STKEND, CSTK + 5)
        self._run(0x2DA2)                   # FP-TO-BC
        f = self.zx.flags
        bc = self.zx.bc
        if f & 1:
            raise FPError(5)
        neg = not (f & 0x40)                # Z reset: negative
        if signed:
            if neg:
                if bc > 32768:
                    raise FPError(5)
                return (-bc) & 0xFFFF
            if bc > 32767:
                raise FPError(5)
            return bc
        if neg and bc:
            raise FPError(5)
        return bc

    def compare(self, x, y):
        d = self.op(SUB, x, y)
        if d[0] == 0:
            if d[2] == 0 and d[3] == 0:
                return 0
            return -1 if d[1] else 1
        return -1 if d[1] & 0x80 else 1

    @staticmethod
    def is_zero(x):
        return x[0] == 0 and x[2] == 0 and x[3] == 0

    def to_py(self, x):
        if x[0] == 0:
            v = x[2] | x[3] << 8
            return v - 65536 if x[1] else v
        m = ((x[1] | 0x80) << 24 | x[2] << 16 | x[3] << 8 | x[4])
        s = -1 if x[1] & 0x80 else 1
        return s * m * 2.0 ** (x[0] - 128 - 32)


_rom = None


def rom():
    global _rom
    if _rom is None:
        _rom = RomFP()
    return _rom
