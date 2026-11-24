"""Jump, call, return, restart, exchange, and CPU-control (NOP/HALT/DI/EI/IM) group."""

from z80_python._core import _signed8
from z80_python._flags import FLAG_C, FLAG_PV, FLAG_S, FLAG_Z

_CONDITIONS = (
    (FLAG_Z, 0),
    (FLAG_Z, FLAG_Z),
    (FLAG_C, 0),
    (FLAG_C, FLAG_C),
    (FLAG_PV, 0),
    (FLAG_PV, FLAG_PV),
    (FLAG_S, 0),
    (FLAG_S, FLAG_S),
)


class ControlMixin:
    """Private control-flow, exchange, and CPU-control implementation."""

    def _cond_true(self, cond: int) -> bool:
        # cc in bits 5-3: NZ Z NC C PO PE P M, a flag and whether it must be set.
        mask, wanted = _CONDITIONS[cond]
        return (self._f & mask) == wanted

    def _op_jr(self, opcode: int) -> int:
        """JR cc,e -- relative jump; JR e is the always-taken form. 12 T-states taken, 7 not (UM0080
        pp. 265-274).

        WZ: z80memptr; SST 18.json, 20.json.
        """
        displacement = _signed8(self._read_operand_byte())
        # JR e is 0x18; JR NZ/Z/NC/C are 0x20-0x38, whose bits 4-3 are cc 0-3.
        taken = opcode == 0x18 or self._cond_true((opcode >> 3) & 0x03)
        if not taken:
            self.q = 0
            return 7
        # Unlike JP, the target is only computed (and latched into WZ) when the branch
        # is taken; a not-taken JR leaves WZ untouched.
        self.wz = (self.pc + displacement) & 0xFFFF
        self.pc = self.wz
        self.q = 0
        return 12

    def _op_jp(self, opcode: int) -> int:
        """JP cc,nn -- absolute jump; JP nn is the always-taken form. 10 T-states either way (UM0080
        pp. 262-263).

        WZ: z80memptr; SST c3.json, c2.json.
        """
        # Fetch nn into WZ before checking flags. A rejected JP still changes the latch.
        self.wz = self._read_operand_word()
        if opcode == 0xC3 or self._cond_true((opcode >> 3) & 0x07):
            self.pc = self.wz
        self.q = 0
        return 10

    def _op_jp_hl(self) -> int:
        """JP (HL) (UM0080 p. 275)."""
        self.pc = self._hl()
        self.q = 0
        return 4

    def _op_ex_de_hl(self) -> int:
        """EX DE,HL (UM0080 p. 124)."""
        de = self._de()
        self.d = self.h
        self.e = self.l
        self.h = (de >> 8) & 0xFF
        self.l = de & 0xFF
        self.q = 0
        return 4

    def _op_interrupt_enable(self, enabled: bool) -> int:
        """DI/EI -- update both interrupt-enable flip-flops (UM0080 pp. 182-183; Young 5.5)."""
        self.iff1 = enabled
        self.iff2 = enabled
        self._ei_delay = 1 if enabled else 0
        self.q = 0
        return 4

    def _op_call(self, opcode: int) -> int:
        """CALL cc,nn -- CALL nn is the always-taken form. 17 T-states taken, 10 not (UM0080 pp.
        281-284).

        WZ: z80memptr; SST cd.json, c4.json.
        """
        # A failed CALL still fetches nn into WZ; SP keeps its seat.
        self.wz = self._read_operand_word()
        if opcode != 0xCD and not self._cond_true((opcode >> 3) & 0x07):
            self.q = 0
            return 10
        self._push_word(self.pc)
        self.pc = self.wz
        self.q = 0
        return 17

    def _op_ret(self) -> int:
        """RET (UM0080 p. 285).

        WZ: z80memptr; SST c9.json.
        """
        self.wz = self._pop_word()
        self.pc = self.wz
        self.q = 0
        return 10

    def _op_ret_cc(self, opcode: int) -> int:
        """RET cc -- 11 T-states taken, 5 not (UM0080 p. 286).

        WZ: z80memptr; SST c0.json.
        """
        if not self._cond_true((opcode >> 3) & 0x07):
            self.q = 0
            return 5
        self.wz = self._pop_word()
        self.pc = self.wz
        self.q = 0
        return 11

    def _ret_iff(self) -> int:
        self.wz = self._pop_word()
        self.pc = self.wz
        self.iff1 = self.iff2
        self.q = 0
        return 14

    def _op_retn(self) -> int:
        """RETN -- return from NMI; restores IFF1 from IFF2 (UM0080 p. 290; Young 5.3).

        WZ: z80memptr; SST ed 45.json.
        """
        return self._ret_iff()

    def _op_reti(self) -> int:
        """RETI -- return from maskable interrupt; restores IFF1 from IFF2 exactly like RETN (UM0080
        p. 288; Young 5.3).

        WZ: z80memptr; SST ed 4d.json.
        """
        return self._ret_iff()

    def _op_rst(self, opcode: int) -> int:
        """RST p (UM0080 p. 292).

        WZ: SST c7.json (z80test has no RST test).
        """
        self._push_word(self.pc)
        self.wz = ((opcode >> 3) & 0x07) << 3
        self.pc = self.wz
        self.q = 0
        return 11

    def _op_im(self, mode: int) -> int:
        """IM n -- select Z80 interrupt mode 0, 1, or 2 (UM0080 pp. 184-186; Young 3.4)."""
        self.im = mode
        self.q = 0
        return 8

    def _op_ed_nop(self) -> int:
        """NOP (undocumented ED-prefixed form) -- 8 T-states, no state change (Young 3.4)."""
        self.q = 0
        return 8

    def _op_exx(self) -> int:
        """EXX (UM0080 p. 126)."""
        bc, de, hl = self._bc(), self._de(), self._hl()
        self._write_pair(0, self.bc_)
        self._write_pair(1, self.de_)
        self._write_pair(2, self.hl_)
        self.bc_, self.de_, self.hl_ = bc, de, hl
        self.q = 0
        return 4

    def _op_ex_sp_hl(self) -> int:
        """EX (SP),HL (UM0080 p. 127).

        WZ: z80memptr; SST e3.json.
        """
        value = self.read_byte(self.sp) | (self.read_byte((self.sp + 1) & 0xFFFF) << 8)
        hl = self._hl()
        self.write_byte((self.sp + 1) & 0xFFFF, hl >> 8)
        self.write_byte(self.sp, hl & 0xFF)
        self.h = (value >> 8) & 0xFF
        self.l = value & 0xFF
        self.wz = value
        self.q = 0
        return 19

    def _op_halt(self) -> int:
        """HALT (UM0080 p. 181; Young 5.4)."""
        self.halted = True
        self.q = 0
        return 4

    def _op_nop(self) -> int:
        """NOP (UM0080 p. 180)."""
        self.q = 0
        return 4

    def _op_ex_af_af(self) -> int:
        """EX AF,AF' (UM0080 p. 125)."""
        af = (self.a << 8) | self._f
        self.a = (self.af_ >> 8) & 0xFF
        self._f = self.af_ & 0xFF
        self.af_ = af
        self.q = 0
        return 4

    def _op_djnz(self) -> int:
        """DJNZ e -- decrement B and branch if it is not zero; 13 T-states taken, 8 not (UM0080 p.
        278).

        WZ: z80memptr; SST 10.json.
        """
        displacement = _signed8(self._read_operand_byte())
        self.b = (self.b - 1) & 0xFF
        if self.b:
            self.wz = (self.pc + displacement) & 0xFFFF
            self.pc = self.wz
            self.q = 0
            return 13
        self.q = 0
        return 8
