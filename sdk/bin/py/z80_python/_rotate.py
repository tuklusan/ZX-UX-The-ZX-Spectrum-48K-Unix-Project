"""Rotate, shift, and bit-operation implementation."""

from z80_python._flags import FLAG_C, FLAG_H, FLAG_PV, FLAG_S, FLAG_XY, FLAG_Z, SZXYP


def _bit_flags(f: int, value: int, bit_index: int, xy_source: int) -> int:
    """F after BIT b: Z (and PV) when the bit is clear, S only for a set bit 7, H set, C kept."""
    tested = value & (1 << bit_index)
    return (
        (f & FLAG_C)
        | FLAG_H
        | (xy_source & FLAG_XY)
        | (tested & FLAG_S)
        | (0 if tested else FLAG_Z | FLAG_PV)
    )


class RotateBitMixin:
    """Private rotate, shift, and bit implementation."""

    def _rlc(self, x: int) -> int:
        r = ((x << 1) | (x >> 7)) & 0xFF
        self._f = SZXYP[r] | (x >> 7)
        return r

    def _rrc(self, x: int) -> int:
        r = ((x >> 1) | (x << 7)) & 0xFF
        self._f = SZXYP[r] | (x & 1)
        return r

    def _rl(self, x: int) -> int:
        r = ((x << 1) | (self._f & FLAG_C)) & 0xFF
        self._f = SZXYP[r] | (x >> 7)
        return r

    def _rr(self, x: int) -> int:
        r = (x >> 1) | ((self._f & FLAG_C) << 7)
        self._f = SZXYP[r] | (x & 1)
        return r

    def _sla(self, x: int) -> int:
        r = (x << 1) & 0xFF
        self._f = SZXYP[r] | (x >> 7)
        return r

    def _sra(self, x: int) -> int:
        r = (x & 0x80) | (x >> 1)
        self._f = SZXYP[r] | (x & 1)
        return r

    def _sll(self, x: int) -> int:
        r = ((x << 1) | 1) & 0xFF
        self._f = SZXYP[r] | (x >> 7)
        return r

    def _srl(self, x: int) -> int:
        r = x >> 1
        self._f = SZXYP[r] | (x & 1)
        return r

    def _rot_apply(self, group: int, value: int) -> int:
        operations = (
            self._rlc,
            self._rrc,
            self._rl,
            self._rr,
            self._sla,
            self._sra,
            self._sll,
            self._srl,
        )
        return operations[group](value)

    def _op_rot(self, sub_opcode: int) -> int:
        """RLC/RRC/RL/RR/SLA/SRA/SLL/SRL r -- CB-prefixed rotates and shifts, including (HL) (UM0080
        pp. 213-237; Young 3.1).
        """
        group = (sub_opcode >> 3) & 0x07
        dest = sub_opcode & 0x07
        if dest == 6:
            addr = self._hl()
            self.write_byte(addr, self._rot_apply(group, self.read_byte(addr)))
            self.q = self._f
            return 15
        self._write_reg(dest, self._rot_apply(group, self._read_reg(dest)))
        self.q = self._f
        return 8

    def _op_rlca(self) -> int:
        """RLCA (UM0080 p. 205)."""
        self.a = ((self.a << 1) | (self.a >> 7)) & 0xFF
        # The accumulator rotates keep S, Z and PV; C is the bit rotated out.
        self._f = (self._f & (FLAG_S | FLAG_Z | FLAG_PV)) | (self.a & (FLAG_XY | FLAG_C))
        self.q = self._f
        return 4

    def _op_rrca(self) -> int:
        """RRCA (UM0080 p. 209)."""
        carry = self.a & 1
        self.a = ((self.a >> 1) | (self.a << 7)) & 0xFF
        self._f = (self._f & (FLAG_S | FLAG_Z | FLAG_PV)) | (self.a & FLAG_XY) | carry
        self.q = self._f
        return 4

    def _op_rla(self) -> int:
        """RLA (UM0080 p. 207)."""
        carry = self.a >> 7
        self.a = ((self.a << 1) | (self._f & FLAG_C)) & 0xFF
        self._f = (self._f & (FLAG_S | FLAG_Z | FLAG_PV)) | (self.a & FLAG_XY) | carry
        self.q = self._f
        return 4

    def _op_rra(self) -> int:
        """RRA (UM0080 p. 211)."""
        carry = self.a & 1
        self.a = (self.a >> 1) | ((self._f & FLAG_C) << 7)
        self._f = (self._f & (FLAG_S | FLAG_Z | FLAG_PV)) | (self.a & FLAG_XY) | carry
        self.q = self._f
        return 4

    def _op_bit(self, sub_opcode: int) -> int:
        """BIT b,r -- includes BIT b,(HL) (UM0080 pp. 243, 245; Young 4.1).

        X/Y for BIT b,r: bits 5 and 3 of the register, as z80full (hardware) and SST cb 40.json
        pin it; Young 4.1 says they follow the tested bit, which z80full contradicts. X/Y for
        BIT b,(HL) come from WZ's high byte: z80memptr; SST cb 46.json.
        """
        bit_index = (sub_opcode >> 3) & 0x07
        src = sub_opcode & 0x07
        if src == 6:
            value = self.read_byte(self._hl())
            # X/Y sample the internal address bus during the read: WZ's high byte, not the tested byte.
            # Register forms below take them from the value itself.
            xy_source = (self.wz >> 8) & 0xFF
            t_states = 12
        else:
            value = self._read_reg(src)
            xy_source = value
            t_states = 8
        self._f = _bit_flags(self._f, value, bit_index, xy_source)
        self.q = self._f
        return t_states

    def _op_res(self, sub_opcode: int) -> int:
        """RES b,r -- includes RES b,(HL) (UM0080 p. 259)."""
        bit_index = (sub_opcode >> 3) & 0x07
        dest = sub_opcode & 0x07
        mask = ~(1 << bit_index) & 0xFF
        if dest == 6:
            addr = self._hl()
            self.write_byte(addr, self.read_byte(addr) & mask)
            t_states = 15
        else:
            self._write_reg(dest, self._read_reg(dest) & mask)
            t_states = 8
        self.q = 0
        return t_states

    def _op_set(self, sub_opcode: int) -> int:
        """SET b,r -- includes SET b,(HL) (UM0080 pp. 251, 253)."""
        bit_index = (sub_opcode >> 3) & 0x07
        dest = sub_opcode & 0x07
        mask = 1 << bit_index
        if dest == 6:
            addr = self._hl()
            self.write_byte(addr, self.read_byte(addr) | mask)
            t_states = 15
        else:
            self._write_reg(dest, self._read_reg(dest) | mask)
            t_states = 8
        self.q = 0
        return t_states

    def _op_rrd(self) -> int:
        """RRD -- rotate the BCD digit chain A[3:0] -> (HL)[7:4] -> (HL)[3:0] -> A[3:0] right
        (UM0080 p. 240).

        WZ: z80memptr; SST ed 67.json.
        """
        addr = self._hl()
        self.wz = (addr + 1) & 0xFFFF
        data = self.read_byte(addr)
        self.write_byte(addr, ((data >> 4) | (self.a << 4)) & 0xFF)
        self.a = (self.a & 0xF0) | (data & 0x0F)
        self._f = (self._f & FLAG_C) | SZXYP[self.a]
        self.q = self._f
        return 18

    def _op_rld(self) -> int:
        """RLD -- rotate the BCD digit chain A[3:0] -> (HL)[3:0] -> (HL)[7:4] -> A[3:0] left (UM0080
        p. 238).

        WZ: z80memptr; SST ed 6f.json.
        """
        addr = self._hl()
        self.wz = (addr + 1) & 0xFFFF
        data = self.read_byte(addr)
        self.write_byte(addr, ((data << 4) | (self.a & 0x0F)) & 0xFF)
        self.a = (self.a & 0xF0) | (data >> 4)
        self._f = (self._f & FLAG_C) | SZXYP[self.a]
        self.q = self._f
        return 18
