"""Eight- and sixteen-bit arithmetic instruction implementation.

Each helper computes the whole new F in one expression. The flag masks and the
SZXY/SZXYP tables are in _flags.py: SZXY[r] is S, Z and the undocumented Y/X
as a result byte r sets them, and SZXYP adds PV as parity.
"""

from z80_python._flags import (
    FLAG_C,
    FLAG_H,
    FLAG_N,
    FLAG_PV,
    FLAG_S,
    FLAG_XY,
    FLAG_Z,
    SZXY,
    SZXYP,
)


class ALUMixin:
    """Private arithmetic and logic implementation."""

    def _add(self, x: int, y: int, carry: int) -> int:
        z = x + y + carry
        r = z & 0xFF
        # H: carry out of bit 3. PV: overflow, the operands agree in sign and the result does not
        # (bit 7 moved down to PV's bit 2). C: bit 8 of the sum.
        self._f = (
            SZXY[r] | ((x ^ y ^ r) & FLAG_H) | (((x ^ y ^ 0x80) & (x ^ r) & 0x80) >> 5) | (z >> 8)
        )
        return r

    def _sub(self, x: int, y: int, carry: int) -> int:
        z = x - y - carry
        r = z & 0xFF
        # H: borrow into bit 4. PV: the operands differ in sign and the result's sign differs
        # from x's. C: the borrow, bit 8 of the difference.
        self._f = (
            SZXY[r]
            | ((x ^ y ^ r) & FLAG_H)
            | (((x ^ y) & (x ^ r) & 0x80) >> 5)
            | FLAG_N
            | ((z >> 8) & FLAG_C)
        )
        return r

    def _and(self, x: int, y: int) -> int:
        r = x & y
        self._f = SZXYP[r] | FLAG_H
        return r

    def _or(self, x: int, y: int) -> int:
        r = x | y
        self._f = SZXYP[r]
        return r

    def _xor(self, x: int, y: int) -> int:
        r = x ^ y
        self._f = SZXYP[r]
        return r

    def _cp(self, x: int, y: int) -> None:
        z = x - y
        r = z & 0xFF
        # CP is a discarded SUB: X/Y sample the operand still on the internal
        # bus, not the thrown-away result.
        self._f = (
            (SZXY[r] & (FLAG_S | FLAG_Z))
            | (y & FLAG_XY)
            | ((x ^ y ^ r) & FLAG_H)
            | (((x ^ y) & (x ^ r) & 0x80) >> 5)
            | FLAG_N
            | ((z >> 8) & FLAG_C)
        )

    def _inc(self, x: int) -> int:
        r = (x + 1) & 0xFF
        # C is untouched. H: the low nibble wrapped to 0. PV: 0x7F became 0x80.
        self._f = (
            (self._f & FLAG_C)
            | SZXY[r]
            | (FLAG_H if (r & 0x0F) == 0 else 0)
            | (FLAG_PV if r == 0x80 else 0)
        )
        return r

    def _dec(self, x: int) -> int:
        r = (x - 1) & 0xFF
        # C is untouched. H: the low nibble wrapped to F. PV: 0x80 became 0x7F.
        self._f = (
            (self._f & FLAG_C)
            | SZXY[r]
            | FLAG_N
            | (FLAG_H if (r & 0x0F) == 0x0F else 0)
            | (FLAG_PV if r == 0x7F else 0)
        )
        return r

    def _op_alu_r(self, opcode: int) -> int:
        """ADD/ADC/SUB/SBC/AND/XOR/OR/CP A,r -- 8-bit ALU with a register or (HL) operand (UM0080
        pp. 145-164).

        X/Y: bits 5 and 3 of the result (Young 2.3), but of the operand for CP (z80full).
        """
        group = (opcode >> 3) & 0x07
        src = opcode & 0x07
        if src == 6:
            value = self.read_byte(self._hl())
            t_states = 7
        else:
            value = self._read_reg(src)
            t_states = 4
        self._alu_a(group, value)
        self.q = self._f
        return t_states

    def _op_alu_n(self, opcode: int) -> int:
        """ADD/ADC/SUB/SBC/AND/XOR/OR/CP A,n -- 8-bit ALU with an immediate operand (UM0080 pp.
        147-164).
        """
        self._alu_a((opcode >> 3) & 0x07, self._read_operand_byte())
        self.q = self._f
        return 7

    def _op_neg(self) -> int:
        """NEG -- replace A with its two's-complement negation (UM0080 p. 176)."""
        self.a = self._sub(0, self.a, 0)
        self.q = self._f
        return 8

    def _alu_a(self, group: int, value: int) -> None:
        if group == 0:
            self.a = self._add(self.a, value, 0)
        elif group == 1:
            self.a = self._add(self.a, value, self._f & FLAG_C)
        elif group == 2:
            self.a = self._sub(self.a, value, 0)
        elif group == 3:
            self.a = self._sub(self.a, value, self._f & FLAG_C)
        elif group == 4:
            self.a = self._and(self.a, value)
        elif group == 5:
            self.a = self._xor(self.a, value)
        elif group == 6:
            self.a = self._or(self.a, value)
        else:
            self._cp(self.a, value)

    def _op_inc_r(self, opcode: int) -> int:
        """INC r (UM0080 p. 165)."""
        dest = (opcode >> 3) & 0x07
        self._write_reg(dest, self._inc(self._read_reg(dest)))
        self.q = self._f
        return 4

    def _op_dec_r(self, opcode: int) -> int:
        """DEC r (UM0080 p. 170)."""
        dest = (opcode >> 3) & 0x07
        self._write_reg(dest, self._dec(self._read_reg(dest)))
        self.q = self._f
        return 4

    def _op_inc_hl(self) -> int:
        """INC (HL) (UM0080 p. 167)."""
        addr = self._hl()
        self.write_byte(addr, self._inc(self.read_byte(addr)))
        self.q = self._f
        return 11

    def _op_dec_hl(self) -> int:
        """DEC (HL) (UM0080 p. 170)."""
        addr = self._hl()
        self.write_byte(addr, self._dec(self.read_byte(addr)))
        self.q = self._f
        return 11

    def _op_daa(self) -> int:
        """DAA -- decimal-adjust A after a BCD ADD/SUB, steered by H, N, and C (UM0080 p. 173; Young
        4.7).
        """
        original = a = self.a
        f = self._f
        carry = f & FLAG_C
        # DAA: a tens digit above 9, or a carry out of it, means the BCD result
        # overflowed 99; correct by 0x60 (direction from N) and force C. The second test
        # does the same for the units digit via H and 0x06.
        if carry or a > 0x99:
            a = (a + (-0x60 if f & FLAG_N else 0x60)) & 0xFF
            carry = FLAG_C
        if f & FLAG_H or (a & 0x0F) > 0x09:
            a = (a + (-0x06 if f & FLAG_N else 0x06)) & 0xFF
        self.a = a
        self._f = SZXYP[a] | ((a ^ original) & FLAG_H) | (f & FLAG_N) | carry
        self.q = self._f
        return 4

    def _op_cpl(self) -> int:
        """CPL -- complement A, setting H/N and X/Y from the result (UM0080 p. 175)."""
        self.a ^= 0xFF
        self._f = (
            (self._f & (FLAG_S | FLAG_Z | FLAG_PV | FLAG_C)) | FLAG_H | FLAG_N | (self.a & FLAG_XY)
        )
        self.q = self._f
        return 4

    def _op_scf_ccf(self, opcode: int) -> int:
        """SCF/CCF -- including their Q-sensitive undocumented X/Y behavior (UM0080 pp. 178-179).

        Q: z80ccf (hardware, the rule's discovery); SST 37.json, 3f.json.
        """
        f = self._f
        # Q holds F only if the previous M1 cycle wrote flags. If it did, F's
        # X/Y are masked and A alone supplies them; otherwise X/Y = (F | A). A
        # DD/FD prefix is its own M1 that writes no flags, so a prefixed SCF/CCF
        # sees Q=0 (_execute_index clears it).
        xy = (self.a if self.q else f | self.a) & FLAG_XY
        if opcode == 0x37:
            carry_and_h = FLAG_C
        elif f & FLAG_C:  # CCF: H takes the old carry, C its complement
            carry_and_h = FLAG_H
        else:
            carry_and_h = FLAG_C
        self._f = (f & (FLAG_S | FLAG_Z | FLAG_PV)) | xy | carry_and_h
        self.q = self._f
        return 4

    def _add16(self, x: int, y: int, carry: int) -> int:
        z = x + y + carry
        r = z & 0xFFFF
        # The 8-bit rules, one byte up: S, Y and X from the high byte, H from bit 11,
        # PV from bit 15, C from bit 16.
        self._f = (
            ((r >> 8) & (FLAG_S | FLAG_XY))
            | (FLAG_Z if r == 0 else 0)
            | (((x ^ y ^ r) >> 8) & FLAG_H)
            | (((x ^ y ^ 0x8000) & (x ^ r) & 0x8000) >> 13)
            | (z >> 16)
        )
        return r

    def _sub16(self, x: int, y: int, carry: int) -> int:
        z = x - y - carry
        r = z & 0xFFFF
        self._f = (
            ((r >> 8) & (FLAG_S | FLAG_XY))
            | (FLAG_Z if r == 0 else 0)
            | (((x ^ y ^ r) >> 8) & FLAG_H)
            | (((x ^ y) & (x ^ r) & 0x8000) >> 13)
            | FLAG_N
            | ((z >> 16) & FLAG_C)
        )
        return r

    # ADD/ADC/SBC use WZ = old HL + 1. Arithmetic changes; the latch does not.
    def _op_add_hl_rr(self, opcode: int) -> int:
        """ADD HL,rr -- only H, N, C and X/Y change; S/Z/PV are preserved (UM0080 p. 188; Young
        4.6).

        WZ: z80memptr; SST 09.json.
        """
        pair_index = (opcode >> 4) & 0x03
        hl = self._hl()
        value = self._read_pair(pair_index)
        self.wz = (hl + 1) & 0xFFFF
        z = hl + value
        result = z & 0xFFFF
        self._f = (
            (self._f & (FLAG_S | FLAG_Z | FLAG_PV))
            | ((result >> 8) & FLAG_XY)
            | (((hl ^ value ^ result) >> 8) & FLAG_H)
            | (z >> 16)
        )
        self._write_pair(2, result)
        self.q = self._f
        return 11

    def _op_adc_hl_rr(self, opcode: int) -> int:
        """ADC HL,rr (UM0080 p. 190; Young 4.6).

        WZ: z80memptr; SST ed 4a.json.
        """
        pair_index = (opcode >> 4) & 0x03
        hl = self._hl()
        self.wz = (hl + 1) & 0xFFFF
        self._write_pair(2, self._add16(hl, self._read_pair(pair_index), self._f & FLAG_C))
        self.q = self._f
        return 15

    def _op_sbc_hl_rr(self, opcode: int) -> int:
        """SBC HL,rr (UM0080 p. 192; Young 4.6).

        WZ: z80memptr; SST ed 42.json.
        """
        pair_index = (opcode >> 4) & 0x03
        hl = self._hl()
        self.wz = (hl + 1) & 0xFFFF
        self._write_pair(2, self._sub16(hl, self._read_pair(pair_index), self._f & FLAG_C))
        self.q = self._f
        return 15

    def _op_inc_rr(self, opcode: int) -> int:
        """INC rr -- no flags (UM0080 p. 198)."""
        pair_index = (opcode >> 4) & 0x03
        self._write_pair(pair_index, (self._read_pair(pair_index) + 1) & 0xFFFF)
        self.q = 0
        return 6

    def _op_dec_rr(self, opcode: int) -> int:
        """DEC rr -- no flags (UM0080 p. 201)."""
        pair_index = (opcode >> 4) & 0x03
        self._write_pair(pair_index, (self._read_pair(pair_index) - 1) & 0xFFFF)
        self.q = 0
        return 6
