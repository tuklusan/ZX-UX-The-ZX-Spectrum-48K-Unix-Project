"""Input/output instruction implementation."""

from z80_python._flags import FLAG_C, FLAG_H, FLAG_N, FLAG_PV, FLAG_XY, PARITY, SZXY, SZXYP


def _block_io_flags(total: int, data: int, b: int) -> int:
    """F after INI/IND/OUTI/OUTD, from the byte moved and the new B.

    Block I/O flags (Undocumented Z80 Documented, 4.3): N = bit 7 of the byte,
    H = C = carry of (C+/-1) + byte for INI/IND (L + byte for OUTI/OUTD), and
    PV = parity of ((that sum & 7) ^ B). S/Z/X/Y come from the new B.
    ``total`` is that sum.
    """
    carry = FLAG_H | FLAG_C if total > 0xFF else 0
    return SZXY[b] | ((data >> 6) & FLAG_N) | PARITY[(total & 7) ^ b] | carry


class IOMixin:
    """Private immediate, register, and block I/O implementation."""

    def _op_in_a_n(self) -> int:
        """IN A,(n) -- port address is A:n (UM0080 p. 295; Young 4.4).

        WZ: z80memptr; SST db.json.
        """
        self.wz = (self.a << 8) | self._read_operand_byte()
        self.a = self.read_port(self.wz)
        self.wz = (self.wz + 1) & 0xFFFF
        self.q = 0
        return 11

    def _op_out_n_a(self) -> int:
        """OUT (n),A -- port address is A:n (UM0080 p. 306; Young 4.4).

        WZ: z80memptr; SST d3.json.
        """
        self.wz = (self.a << 8) | self._read_operand_byte()
        self.write_port(self.wz, self.a)
        # Same latch behavior as LD (nn),A: the port's high byte (A) is kept and only the
        # low byte of the address increments.
        self.wz = (self.wz & 0xFF00) | ((self.wz + 1) & 0xFF)
        self.q = 0
        return 11

    def _op_in_r_c(self, opcode: int) -> int:
        """IN r,(C) -- includes the undocumented IN (C) / IN F,(C) form that only sets flags (UM0080
        p. 296; Young 3.4).

        WZ: z80memptr; SST ed 40.json.
        """
        dest = (opcode >> 3) & 0x07
        self.wz = (self._bc() + 1) & 0xFFFF
        value = self.read_port(self._bc())
        self._f = (self._f & FLAG_C) | SZXYP[value]
        if dest != 6:
            self._write_reg(dest, value)
        self.q = self._f
        return 12

    def _op_out_c_r(self, opcode: int) -> int:
        """OUT (C),r -- the undocumented OUT (C),0 form writes zero on NMOS parts (UM0080 p. 307;
        Young 3.4).

        WZ: z80memptr; SST ed 41.json.
        """
        src = (opcode >> 3) & 0x07
        addr = self._bc()
        # OUT (C),0: the undocumented (HL) slot has no register, NMOS parts drive 0 (CMOS parts drive
        # 0xFF; this core models NMOS, as the vectors do).
        value = 0 if src == 6 else self._read_reg(src)
        self.write_port(addr, value)
        self.wz = (addr + 1) & 0xFFFF
        self.q = 0
        return 12

    def _block_ini(self, increment: bool) -> bool:
        if increment:
            self.wz = (self._bc() + 1) & 0xFFFF
            data = self.read_port((self.wz - 1) & 0xFFFF)
            adj = (self.c + 1) & 0xFF
        else:
            self.wz = (self._bc() - 1) & 0xFFFF
            data = self.read_port((self.wz + 1) & 0xFFFF)
            adj = (self.c - 1) & 0xFF
        self._io_data = data
        self.b = (self.b - 1) & 0xFF
        self.write_byte(self._hl(), data)
        hl = (self._hl() + 1) & 0xFFFF if increment else (self._hl() - 1) & 0xFFFF
        self.h, self.l = (hl >> 8) & 0xFF, hl & 0xFF
        self._f = _block_io_flags(adj + data, data, self.b)
        return self.b != 0

    def _block_outi(self, increment: bool) -> bool:
        hl = self._hl()
        data = self.read_byte(hl)
        self._io_data = data
        hl = (hl + 1) & 0xFFFF if increment else (hl - 1) & 0xFFFF
        self.h, self.l = (hl >> 8) & 0xFF, hl & 0xFF
        self.b = (self.b - 1) & 0xFF
        addr = self._bc()
        self.write_port(addr, data)
        self.wz = (addr + 1) & 0xFFFF if increment else (addr - 1) & 0xFFFF
        self._f = _block_io_flags(self.l + data, data, self.b)
        return self.b != 0

    # Repeating block I/O adjusts flags once more after the PC rewind. This is newer
    # than Young's 2005 text and is encoded by the SingleStepTests generator: X/Y from
    # PC high byte bits 3/5, and when C is set, PV and H are corrected from B+/-1
    # depending on bit 7 of the byte moved.
    def _post_in_o_r(self) -> None:
        f = (self._f & ~FLAG_XY) | ((self.pc >> 8) & FLAG_XY)
        b = self.b
        # PV flips when the parity term below is odd (PARITY[x] ^ PV is PV for odd x).
        if f & FLAG_C:
            if self._io_data & 0x80:
                f ^= PARITY[(b - 1) & 7] ^ FLAG_PV
                f = (f & ~FLAG_H) | (FLAG_H if (b & 0x0F) == 0 else 0)
            else:
                f ^= PARITY[(b + 1) & 7] ^ FLAG_PV
                f = (f & ~FLAG_H) | (FLAG_H if (b & 0x0F) == 0x0F else 0)
        else:
            f ^= PARITY[b & 7] ^ FLAG_PV
        self._f = f

    def _op_ini(self) -> int:
        """INI -- (HL) <- port BC; HL++, B-- (UM0080 p. 298; Young 4.3).

        WZ: z80memptr; SST ed a2.json.
        """
        self._block_ini(True)
        self.q = self._f
        return 16

    def _op_ind(self) -> int:
        """IND -- (HL) <- port BC; HL--, B-- (UM0080 p. 302; Young 4.3).

        WZ: z80memptr; SST ed aa.json.
        """
        self._block_ini(False)
        self.q = self._f
        return 16

    def _op_outi(self) -> int:
        """OUTI -- B--, then port BC <- (HL); HL++ (UM0080 p. 309; Young 4.3).

        WZ: z80memptr; SST ed a3.json.
        """
        self._block_outi(True)
        self.q = self._f
        return 16

    def _op_outd(self) -> int:
        """OUTD -- B--, then port BC <- (HL); HL-- (UM0080 p. 313; Young 4.3).

        WZ: z80memptr; SST ed ab.json.
        """
        self._block_outi(False)
        self.q = self._f
        return 16

    def _op_inir(self) -> int:
        """INIR -- INI repeated while B != 0; 21 T-states per repeat, 16 on the last (UM0080 p. 300;
        Young 4.3).

        WZ: z80memptr. The flags on a repeat: SST ed b2.json.
        """
        repeat = self._block_ini(True)
        if repeat:
            self._block_repeat()
            self._post_in_o_r()
        self.q = self._f
        return 21 if repeat else 16

    def _op_indr(self) -> int:
        """INDR -- IND repeated while B != 0; 21 T-states per repeat, 16 on the last (UM0080 p. 304;
        Young 4.3).

        WZ: z80memptr. The flags on a repeat: SST ed ba.json.
        """
        repeat = self._block_ini(False)
        if repeat:
            self._block_repeat()
            self._post_in_o_r()
        self.q = self._f
        return 21 if repeat else 16

    def _op_otir(self) -> int:
        """OTIR -- OUTI repeated while B != 0; 21 T-states per repeat, 16 on the last (UM0080 p.
        311; Young 4.3).

        WZ: z80memptr. The flags on a repeat: SST ed b3.json.
        """
        repeat = self._block_outi(True)
        if repeat:
            self._block_repeat()
            self._post_in_o_r()
        self.q = self._f
        return 21 if repeat else 16

    def _op_otdr(self) -> int:
        """OTDR -- OUTD repeated while B != 0; 21 T-states per repeat, 16 on the last (UM0080 p.
        315; Young 4.3).

        WZ: z80memptr. The flags on a repeat: SST ed bb.json.
        """
        repeat = self._block_outi(False)
        if repeat:
            self._block_repeat()
            self._post_in_o_r()
        self.q = self._f
        return 21 if repeat else 16
