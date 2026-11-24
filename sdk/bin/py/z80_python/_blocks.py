"""Block transfer and search instruction implementation."""

from z80_python._flags import FLAG_C, FLAG_H, FLAG_N, FLAG_PV, FLAG_S, FLAG_X, FLAG_XY, FLAG_Z


class BlockMixin:
    """Private ED block-transfer and search implementation."""

    def _block_ld(self, increment: bool) -> bool:
        src = self._hl()
        data = self.read_byte(src)
        dst = self._de()
        self.write_byte(dst, data)
        if increment:
            hl, de = (src + 1) & 0xFFFF, (dst + 1) & 0xFFFF
        else:
            hl, de = (src - 1) & 0xFFFF, (dst - 1) & 0xFFFF
        self.h, self.l = (hl >> 8) & 0xFF, hl & 0xFF
        self.d, self.e = (de >> 8) & 0xFF, de & 0xFF
        bc = (self._bc() - 1) & 0xFFFF
        self.b, self.c = (bc >> 8) & 0xFF, bc & 0xFF
        # LD group: X/Y come from A + transferred byte, taken from bits 3 and 1 (not 3 and 5): X is
        # bit 3 of that sum, Y is its bit 1 moved up to bit 5.
        n = self.a + data
        self._f = (
            (self._f & (FLAG_S | FLAG_Z | FLAG_C))
            | (n & FLAG_X)
            | ((n & 0x02) << 4)
            | (FLAG_PV if bc else 0)
        )
        return bc != 0

    def _block_cp(self, increment: bool) -> bool:
        src = self._hl()
        data = self.read_byte(src)
        if increment:
            self.wz = (self.wz + 1) & 0xFFFF
            hl = (src + 1) & 0xFFFF
        else:
            self.wz = (self.wz - 1) & 0xFFFF
            hl = (src - 1) & 0xFFFF
        self.h, self.l = (hl >> 8) & 0xFF, hl & 0xFF
        result = (self.a - data) & 0xFF
        bc = (self._bc() - 1) & 0xFFFF
        self.b, self.c = (bc >> 8) & 0xFF, bc & 0xFF
        half = (self.a ^ data ^ result) & FLAG_H
        # X/Y come from A - (HL) - H, the ALU's intermediate before the final correction, and are
        # taken from bits 3 and 1 (not 3 and 5) for the CP group.
        n = result - (half >> 4)
        self._f = (
            (self._f & FLAG_C)
            | (result & FLAG_S)
            | (0 if result else FLAG_Z)
            | half
            | (n & FLAG_X)
            | ((n & 0x02) << 4)
            | (FLAG_PV if bc else 0)
            | FLAG_N
        )
        return bc != 0 and result != 0

    def _block_repeat(self) -> None:
        self.pc = (self.pc - 2) & 0xFFFF
        self.wz = (self.pc + 1) & 0xFFFF
        # On a repeat the CPU rewinds PC by 2 and re-fetches; X/Y then sample bits 3 and 5 of the
        # rewound PC's high byte (PC bits 11 and 13), and WZ = PC + 1.
        self._f = (self._f & ~FLAG_XY) | ((self.pc >> 8) & FLAG_XY)

    def _op_ldi(self) -> int:
        """LDI -- (DE) <- (HL); HL++, DE++, BC-- (UM0080 p. 130; Young 4.2)."""
        self._block_ld(True)
        self.q = self._f
        return 16

    def _op_ldd(self) -> int:
        """LDD -- (DE) <- (HL); HL--, DE--, BC-- (UM0080 p. 134; Young 4.2)."""
        self._block_ld(False)
        self.q = self._f
        return 16

    def _op_cpi(self) -> int:
        """CPI -- compare A with (HL); HL++, BC-- (UM0080 p. 138; Young 4.2).

        WZ: z80memptr; SST ed a1.json.
        """
        self._block_cp(True)
        self.q = self._f
        return 16

    def _op_cpd(self) -> int:
        """CPD -- compare A with (HL); HL--, BC-- (UM0080 p. 141; Young 4.2).

        WZ: z80memptr; SST ed a9.json.
        """
        self._block_cp(False)
        self.q = self._f
        return 16

    def _op_ldir(self) -> int:
        """LDIR -- LDI repeated while BC != 0; 21 T-states per repeat, 16 on the last (UM0080 p.
        132; Young 4.2, 4.5).

        WZ, and X/Y on a repeat: SST ed b0.json.
        """
        repeat = self._block_ld(True)
        if repeat:
            self._block_repeat()
        self.q = self._f
        return 21 if repeat else 16

    def _op_lddr(self) -> int:
        """LDDR -- LDD repeated while BC != 0; 21 T-states per repeat, 16 on the last (UM0080 p.
        136; Young 4.2, 4.5).

        WZ, and X/Y on a repeat: SST ed b8.json.
        """
        repeat = self._block_ld(False)
        if repeat:
            self._block_repeat()
        self.q = self._f
        return 21 if repeat else 16

    def _op_cpir(self) -> int:
        """CPIR -- CPI repeated while BC != 0 and A != (HL); 21 T-states per repeat, 16 last (UM0080
        p. 139; Young 4.2, 4.5).

        WZ, and X/Y on a repeat: SST ed b1.json.
        """
        repeat = self._block_cp(True)
        if repeat:
            self._block_repeat()
        self.q = self._f
        return 21 if repeat else 16

    def _op_cpdr(self) -> int:
        """CPDR -- CPD repeated while BC != 0 and A != (HL); 21 T-states per repeat, 16 last (UM0080
        p. 142; Young 4.2, 4.5).

        WZ, and X/Y on a repeat: SST ed b9.json.
        """
        repeat = self._block_cp(False)
        if repeat:
            self._block_repeat()
        self.q = self._f
        return 21 if repeat else 16
