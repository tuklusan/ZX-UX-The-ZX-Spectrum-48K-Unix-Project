# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""A bare 48K Spectrum for the SDK tools: Z80 + 48K ROM + flat RAM.

The Z80 is the bundled z80-python core (sdk/z80_python, MIT, unmodified;
see repository THIRD-PARTY) with the faster handlers of z80fast.py.  This module only supplies the host side: 64K of
memory with the ROM write-protected, an I/O hook, a T-state clock and a run
loop that stops at chosen addresses.  rcc's float folding (rcc/romfp.py) and
the program VM (rvm.py) both run on it, so the SDK needs nothing outside the
Python standard library.

Registers are exposed under their Z80 names (z.a, z.hl, z.sp, z.pc ...).
No interrupts are raised: the tools run code with interrupts off.
"""
import os
import sys

if sys.version_info < (3, 11):
    raise SystemExit('the ZX-UX SDK needs Python 3.11 or later (bundled z80-python core)')

from z80fast import FastZ80  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROM48 = os.path.join(HERE, 'rom', '48.rom')
FONT = os.path.join(HERE, 'rom', 'font4x8.bin')


class Memory(bytearray):
    """64K RAM image; writes below 4000h (ROM) are ignored, as on a Spectrum."""

    def write(self, a, v):
        if a >= 0x4000:
            self[a] = v


class Spectrum:
    def __init__(self, write_port=None, read_port=None):
        self.mem = Memory(0x10000)
        with open(ROM48, 'rb') as source:
            rom = source.read()
        if len(rom) != 0x4000:
            raise SystemExit('zxcore: %s is not a 16K ROM image' % ROM48)
        self.mem[:0x4000] = rom
        self.cpu = FastZ80(self.mem.__getitem__, self.mem.write,
                          read_port=read_port, write_port=write_port)
        self.t = 0

    # 16-bit register pairs ------------------------------------------------
    def _pair(hi, lo):
        def get(self):
            c = self.cpu
            return getattr(c, hi) << 8 | getattr(c, lo)

        def put(self, v):
            c = self.cpu
            setattr(c, hi, (v >> 8) & 0xFF)
            setattr(c, lo, v & 0xFF)
        return property(get, put)

    bc = _pair('b', 'c')
    de = _pair('d', 'e')
    hl = _pair('h', 'l')
    del _pair

    def __getattr__(self, name):           # a, f, b ... sp, pc, ix, iy
        return getattr(self.cpu, name)

    def set(self, **regs):
        for k, v in regs.items():
            if k in ('bc', 'de', 'hl'):
                setattr(self, k, v)
            elif k == 'f':
                self.cpu._f = v & 0xFF
            else:
                setattr(self.cpu, k, v)

    @property
    def flags(self):
        return self.cpu._f

    # Run one Z80 step. Clock time is not optional.
    def run(self, stop=(), tlimit=None):
        """Execute until PC is in `stop` (checked before each instruction) or
        the clock reaches `tlimit`.  Returns True when a stop address was hit.

        This is Z80CPU.step() for a host that never raises RESET, NMI or a
        maskable interrupt, written as one loop: same fetch, R refresh,
        dispatch, HALT idle cycle and EI-delay bookkeeping.
        """
        cpu = self.cpu
        fetch = self.mem.__getitem__
        page = cpu.run_page
        stop = frozenset(stop)
        t = self.t
        lim = float('inf') if tlimit is None else tlimit
        try:
            while t < lim:
                pc = cpu.pc
                if pc in stop:
                    return True
                if cpu._ei_delay or cpu.halted:
                    delay = cpu._ei_delay
                    if cpu.halted:
                        cpu.r = (cpu.r & 0x80) | ((cpu.r + 1) & 0x7F)
                        cpu.q = 0
                        t += 4
                    else:
                        cpu.pc = (pc + 1) & 0xFFFF
                        cpu.r = (cpu.r & 0x80) | ((cpu.r + 1) & 0x7F)
                        t += page[fetch(pc)]()
                    if delay:
                        cpu._ei_delay -= 1
                    continue
                cpu.pc = (pc + 1) & 0xFFFF
                cpu.r = (cpu.r & 0x80) | ((cpu.r + 1) & 0x7F)
                t += page[fetch(pc)]()
            return False
        finally:
            self.t = t

    def call(self, addr, ret=0x0000, sp=None, tlimit=50_000_000):
        """CALL addr with a return address of `ret`; run until it returns."""
        cpu = self.cpu
        if sp is not None:
            cpu.sp = sp
        cpu.sp = (cpu.sp - 2) & 0xFFFF
        self.mem[cpu.sp] = ret & 0xFF
        self.mem[cpu.sp + 1] = ret >> 8
        cpu.pc = addr
        return self.run((ret,), self.t + tlimit)
