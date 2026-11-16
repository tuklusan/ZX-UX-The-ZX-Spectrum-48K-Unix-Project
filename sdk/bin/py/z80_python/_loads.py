"""8-bit and 16-bit load group, including PUSH/POP (Zilog files the stack transfers here)."""

from z80_python._flags import FLAG_C, FLAG_PV, SZXY


class LoadMixin:
    """Private load-family implementation."""

    def _op_ld_r_r(self, opcode: int) -> int:
        """LD r,r' -- includes the (HL) source and destination forms (UM0080 pp. 71, 74, 79)."""
        dest = (opcode >> 3) & 0x07
        src = opcode & 0x07
        t_states = 4
        if src == 6:
            value = self.read_byte(self._hl())
            t_states = 7
        else:
            value = self._read_reg(src)
        if dest == 6:
            self.write_byte(self._hl(), value)
            t_states = 7
        else:
            self._write_reg(dest, value)
        self.q = 0
        return t_states

    def _op_ld_r_n(self, opcode: int) -> int:
        """LD r,n -- includes LD (HL),n (UM0080 pp. 72, 85)."""
        value = self._read_operand_byte()
        dest = (opcode >> 3) & 0x07
        if dest == 6:
            self.write_byte(self._hl(), value)
            t_states = 10
        else:
            self._write_reg(dest, value)
            t_states = 7
        self.q = 0
        return t_states

    def _op_ld_a_irr(self, opcode: int) -> int:
        """LD A,(BC)/(DE) (UM0080 pp. 88-89).

        WZ: z80memptr; SST 0a.json, 1a.json.
        """
        self.wz = self._bc() if opcode == 0x0A else self._de()
        self.a = self.read_byte(self.wz)
        self.wz = (self.wz + 1) & 0xFFFF
        self.q = 0
        return 7

    def _op_ld_irr_a(self, opcode: int) -> int:
        """LD (BC)/(DE),A (UM0080 pp. 91-92).

        WZ: z80memptr; SST 02.json, 12.json.
        """
        self.wz = self._bc() if opcode == 0x02 else self._de()
        self.write_byte(self.wz, self.a)
        # WZ = A:(address+1)&FF. Only the low address byte steps; A steals the high one.
        self.wz = ((self.a << 8) | ((self.wz + 1) & 0xFF)) & 0xFFFF
        self.q = 0
        return 7

    def _op_ld_a_inn(self) -> int:
        """LD A,(nn) (UM0080 p. 90).

        WZ: z80memptr; SST 3a.json.
        """
        self.wz = self._read_operand_word()
        self.a = self.read_byte(self.wz)
        self.wz = (self.wz + 1) & 0xFFFF
        self.q = 0
        return 13

    def _op_ld_inn_a(self) -> int:
        """LD (nn),A (UM0080 p. 93).

        WZ: z80memptr; SST 32.json.
        """
        self.wz = self._read_operand_word()
        self.write_byte(self.wz, self.a)
        # Same WZ quirk as LD (BC),A, but the target address comes from nn.
        self.wz = ((self.a << 8) | ((self.wz + 1) & 0xFF)) & 0xFFFF
        self.q = 0
        return 13

    def _op_ld_i_a(self) -> int:
        """LD I,A (UM0080 p. 96)."""
        self.i = self.a
        self.q = 0
        return 9

    def _op_ld_r_a(self) -> int:
        """LD R,A (UM0080 p. 97)."""
        self.r = self.a
        self.q = 0
        return 9

    def _op_ld_a_i(self) -> int:
        """LD A,I -- one of the two loads that set flags (LD A,R is the other); PV mirrors IFF2
        (UM0080 p. 94).
        """
        self.a = self.i
        self._f = (self._f & FLAG_C) | SZXY[self.a] | (FLAG_PV if self.iff2 else 0)
        self.q = self._f
        return 9

    def _op_ld_a_r(self) -> int:
        """LD A,R -- one of the two loads that set flags (LD A,I is the other); PV mirrors IFF2
        (UM0080 p. 95).
        """
        self.a = self.r
        self._f = (self._f & FLAG_C) | SZXY[self.a] | (FLAG_PV if self.iff2 else 0)
        self.q = self._f
        return 9

    def _op_ld_nn_hl(self) -> int:
        """LD (nn),HL (UM0080 p. 107).

        WZ: z80memptr; SST 22.json.
        """
        addr = self._read_operand_word()
        self.write_byte(addr, self.l)
        self.wz = (addr + 1) & 0xFFFF
        self.write_byte(self.wz, self.h)
        self.q = 0
        return 16

    def _op_ld_hl_nn_from_mem(self) -> int:
        """LD HL,(nn) (UM0080 p. 102).

        WZ: z80memptr; SST 2a.json.
        """
        addr = self._read_operand_word()
        self.l = self.read_byte(addr)
        self.wz = (addr + 1) & 0xFFFF
        self.h = self.read_byte(self.wz)
        self.q = 0
        return 16

    def _op_ld_nn_rr(self, pair_index: int) -> int:
        """LD (nn),rr for the ED-prefixed register-pair transfer forms (UM0080 p. 108).

        WZ: z80memptr; SST ed 43.json.
        """
        addr = self._read_operand_word()
        value = self._read_pair(pair_index)
        self.write_byte(addr, value & 0xFF)
        self.wz = (addr + 1) & 0xFFFF
        self.write_byte(self.wz, value >> 8)
        self.q = 0
        return 20

    def _op_ld_rr_nn_from_mem(self, pair_index: int) -> int:
        """LD rr,(nn) for the ED-prefixed register-pair transfer forms (UM0080 p. 103).

        WZ: z80memptr; SST ed 4b.json.
        """
        addr = self._read_operand_word()
        low = self.read_byte(addr)
        self.wz = (addr + 1) & 0xFFFF
        self._write_pair(pair_index, low | (self.read_byte(self.wz) << 8))
        self.q = 0
        return 20

    def _op_ld_sp_hl(self) -> int:
        """LD SP,HL -- copy HL into SP (UM0080 p. 112)."""
        self.sp = self._hl()
        self.q = 0
        return 6

    def _op_pop_rr(self, sub_opcode: int) -> int:
        """POP rr (UM0080 p. 119)."""
        self._write_pair((sub_opcode >> 4) & 0x03, self._pop_word())
        self.q = 0
        return 10

    def _op_push_rr(self, sub_opcode: int) -> int:
        """PUSH rr (UM0080 p. 115)."""
        self._push_word(self._read_pair((sub_opcode >> 4) & 0x03))
        self.q = 0
        return 11

    def _op_pop_af(self) -> int:
        """POP AF (UM0080 p. 119)."""
        value = self._pop_word()
        self.a = (value >> 8) & 0xFF
        self._f = value & 0xFF
        self.q = 0
        return 10

    def _op_push_af(self) -> int:
        """PUSH AF (UM0080 p. 115)."""
        self._push_word((self.a << 8) | self._f)
        self.q = 0
        return 11

    def _op_ld_rr_nn(self, opcode: int) -> int:
        """LD rr,nn -- BC, DE, HL, or SP from a 16-bit immediate (UM0080 p. 99)."""
        self._write_pair((opcode >> 4) & 0x03, self._read_operand_word())
        self.q = 0
        return 10
