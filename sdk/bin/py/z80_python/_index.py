"""IX/IY instruction handlers: every handler here names an IX or IY operand.

Base-set instructions that a DD/FD prefix merely decorates live with their own
instruction group; ``_index_dispatch.py`` routes them and adds the prefix cost.
"""

from z80_python._core import _signed8
from z80_python._flags import FLAG_H, FLAG_PV, FLAG_S, FLAG_XY, FLAG_Z
from z80_python._rotate import _bit_flags


class IndexMixin:
    """Private IX/IY helper and instruction implementation."""

    def _get_index(self, prefix: int) -> int:
        return self.ix if prefix == 0xDD else self.iy

    def _set_index(self, prefix: int, value: int) -> None:
        value &= 0xFFFF
        if prefix == 0xDD:
            self.ix = value
        else:
            self.iy = value

    def _index_high_byte(self, prefix: int) -> int:
        return (self._get_index(prefix) >> 8) & 0xFF

    def _index_low_byte(self, prefix: int) -> int:
        return self._get_index(prefix) & 0xFF

    def _set_index_high_byte(self, prefix: int, value: int) -> None:
        self._set_index(prefix, ((value & 0xFF) << 8) | self._index_low_byte(prefix))

    def _set_index_low_byte(self, prefix: int, value: int) -> None:
        self._set_index(prefix, (self._index_high_byte(prefix) << 8) | (value & 0xFF))

    def _op_add_index_rr(self, prefix: int, sub_opcode: int) -> int:
        """ADD IX/IY,rr -- rr = BC, DE, the index register itself, or SP (UM0080 pp. 194, 196; Young
        4.6).

        WZ: z80memptr; SST dd 09.json.
        """
        pair_index = (sub_opcode >> 4) & 0x03
        index = self._get_index(prefix)
        value = index if pair_index == 2 else self._read_pair(pair_index)
        self.wz = (index + 1) & 0xFFFF
        z = index + value
        result = z & 0xFFFF
        self._f = (
            (self._f & (FLAG_S | FLAG_Z | FLAG_PV))
            | ((result >> 8) & FLAG_XY)
            | (((index ^ value ^ result) >> 8) & FLAG_H)
            | (z >> 16)
        )
        self._set_index(prefix, result)
        self.q = self._f
        return 15

    def _op_ld_index_nn(self, prefix: int) -> int:
        """LD IX/IY,nn (UM0080 pp. 100-101)."""
        self._set_index(prefix, self._read_operand_word())
        self.q = 0
        return 14

    def _op_ld_nn_index(self, prefix: int) -> int:
        """LD (nn),IX/IY (UM0080 pp. 110-111).

        WZ: z80memptr; SST dd 22.json.
        """
        addr = self._read_operand_word()
        index = self._get_index(prefix)
        self.write_byte(addr, index & 0xFF)
        self.wz = (addr + 1) & 0xFFFF
        self.write_byte(self.wz, index >> 8)
        self.q = 0
        return 20

    def _op_ld_index_nn_from_mem(self, prefix: int) -> int:
        """LD IX/IY,(nn) (UM0080 pp. 105-106).

        WZ: z80memptr; SST dd 2a.json.
        """
        addr = self._read_operand_word()
        low = self.read_byte(addr)
        self.wz = (addr + 1) & 0xFFFF
        self._set_index(prefix, low | (self.read_byte(self.wz) << 8))
        self.q = 0
        return 20

    def _op_ld_r_index_byte(self, prefix: int, sub_opcode: int) -> int:
        """LD r,IXH/IXL/IYH/IYL (Young 3.2, 3.3)."""
        value = (
            self._index_high_byte(prefix)
            if (sub_opcode & 0x07) == 4
            else self._index_low_byte(prefix)
        )
        self._write_reg((sub_opcode >> 3) & 0x07, value)
        self.q = 0
        return 8

    def _op_ld_index_byte_index_byte(self, prefix: int, sub_opcode: int) -> int:
        """LD IXH/IXL,IXH/IXL (and the IY forms) (Young 3.2, 3.3)."""
        value = (
            self._index_high_byte(prefix)
            if (sub_opcode & 0x07) == 4
            else self._index_low_byte(prefix)
        )
        if ((sub_opcode >> 3) & 0x07) == 4:
            self._set_index_high_byte(prefix, value)
        else:
            self._set_index_low_byte(prefix, value)
        self.q = 0
        return 8

    def _op_ld_index_byte_r(self, prefix: int, sub_opcode: int) -> int:
        """LD IXH/IXL/IYH/IYL,r (Young 3.2, 3.3)."""
        value = self._read_reg(sub_opcode & 0x07)
        if ((sub_opcode >> 3) & 0x07) == 4:
            self._set_index_high_byte(prefix, value)
        else:
            self._set_index_low_byte(prefix, value)
        self.q = 0
        return 8

    def _op_ld_index_byte_n(self, prefix: int, sub_opcode: int) -> int:
        """LD IXH/IXL/IYH/IYL,n (Young 3.2, 3.3)."""
        value = self._read_operand_byte()
        if ((sub_opcode >> 3) & 0x07) == 4:
            self._set_index_high_byte(prefix, value)
        else:
            self._set_index_low_byte(prefix, value)
        self.q = 0
        return 11

    def _op_inc_dec_index_byte(self, prefix: int, sub_opcode: int) -> int:
        """INC/DEC IXH/IXL/IYH/IYL (Young 3.2, 3.3)."""
        is_high_byte = ((sub_opcode >> 3) & 0x07) == 4
        value = self._index_high_byte(prefix) if is_high_byte else self._index_low_byte(prefix)
        result = self._inc(value) if (sub_opcode & 0x07) == 4 else self._dec(value)
        if is_high_byte:
            self._set_index_high_byte(prefix, result)
        else:
            self._set_index_low_byte(prefix, result)
        self.q = self._f
        return 8

    def _op_alu_index_byte(self, prefix: int, sub_opcode: int) -> int:
        """ADD/ADC/SUB/SBC/AND/XOR/OR/CP A,IXH/IXL/IYH/IYL -- the 8-bit ALU on an index half (Young
        3.2, 3.3).
        """
        high = (sub_opcode & 0x07) == 4
        value = self._index_high_byte(prefix) if high else self._index_low_byte(prefix)
        self._alu_a((sub_opcode >> 3) & 0x07, value)
        self.q = self._f
        return 8

    def _op_alu_index_mem(self, prefix: int, sub_opcode: int) -> int:
        """ADD/ADC/SUB/SBC/AND/XOR/OR/CP A,(IX+d)/(IY+d) -- the 8-bit ALU on indexed memory (UM0080
        pp. 149-164).

        WZ: z80memptr; SST dd 86.json.
        """
        addr = self._index_displacement_addr(prefix)
        self._alu_a((sub_opcode >> 3) & 0x07, self.read_byte(addr))
        self.q = self._f
        return 19

    def _op_inc_index(self, prefix: int) -> int:
        """INC IX/IY -- no flags (UM0080 pp. 199-200)."""
        self._set_index(prefix, self._get_index(prefix) + 1)
        self.q = 0
        return 10

    def _op_dec_index(self, prefix: int) -> int:
        """DEC IX/IY -- no flags (UM0080 pp. 202-203)."""
        self._set_index(prefix, self._get_index(prefix) - 1)
        self.q = 0
        return 10

    def _op_pop_index(self, prefix: int) -> int:
        """POP IX/IY (UM0080 pp. 121-122)."""
        self._set_index(prefix, self._pop_word())
        self.q = 0
        return 14

    def _op_push_index(self, prefix: int) -> int:
        """PUSH IX/IY (UM0080 pp. 117-118)."""
        self._push_word(self._get_index(prefix))
        self.q = 0
        return 15

    def _op_ex_sp_index(self, prefix: int) -> int:
        """EX (SP),IX/IY (UM0080 pp. 128-129).

        WZ: z80memptr; SST dd e3.json.
        """
        value = self.read_byte(self.sp) | (self.read_byte((self.sp + 1) & 0xFFFF) << 8)
        index = self._get_index(prefix)
        self.write_byte((self.sp + 1) & 0xFFFF, index >> 8)
        self.write_byte(self.sp, index & 0xFF)
        self._set_index(prefix, value)
        self.wz = value
        self.q = 0
        return 23

    def _op_jp_index(self, prefix: int) -> int:
        """JP (IX)/(IY) (UM0080 pp. 276-277)."""
        self.pc = self._get_index(prefix)
        self.q = 0
        return 8

    def _op_ld_sp_index(self, prefix: int) -> int:
        """LD SP,IX/IY (UM0080 pp. 113-114)."""
        self.sp = self._get_index(prefix)
        self.q = 0
        return 10

    def _index_displacement_addr(self, prefix: int) -> int:
        addr = (self._get_index(prefix) + _signed8(self._read_operand_byte())) & 0xFFFF
        self.wz = addr
        return addr

    def _op_index_bit(self, prefix: int, displacement: int, sub_opcode: int) -> int:
        """BIT b,(IX+d)/(IY+d) (UM0080 pp. 247, 249; Young 4.1).

        WZ, and X/Y from its high byte: z80memptr; SST dd cb __ 46.json.
        """
        self.wz = (self._get_index(prefix) + _signed8(displacement)) & 0xFFFF
        value = self.read_byte(self.wz)
        # X/Y come from the high byte of the computed address (WZ), not the byte.
        self._f = _bit_flags(self._f, value, (sub_opcode >> 3) & 0x07, self.wz >> 8)
        self.q = self._f
        return 20

    def _op_index_rot(self, prefix: int, displacement: int, sub_opcode: int) -> int:
        """RLC/RRC/RL/RR/SLA/SRA/SLL/SRL (IX+d)/(IY+d) -- undocumented forms also copy into r
        (UM0080 pp. 217-237; Young 3.5).

        WZ: z80memptr; SST dd cb __ 06.json.
        """
        self.wz = (self._get_index(prefix) + _signed8(displacement)) & 0xFFFF
        value = self._rot_apply((sub_opcode >> 3) & 0x07, self.read_byte(self.wz))
        self.write_byte(self.wz, value)
        dest = sub_opcode & 0x07
        if dest != 6:
            self._write_reg(dest, value)
        self.q = self._f
        return 23

    def _op_index_res_set(self, prefix: int, displacement: int, sub_opcode: int) -> int:
        """RES/SET b,(IX+d)/(IY+d) -- the undocumented forms also copy the result into r (UM0080 pp.
        255-260; Young 3.5).

        WZ: z80memptr; SST dd cb __ 86.json.
        """
        self.wz = (self._get_index(prefix) + _signed8(displacement)) & 0xFFFF
        mask = 1 << ((sub_opcode >> 3) & 0x07)
        value = self.read_byte(self.wz)
        value = value | mask if sub_opcode & 0x40 else value & ~mask
        self.write_byte(self.wz, value)
        dest = sub_opcode & 0x07
        if dest != 6:
            self._write_reg(dest, value)
        self.q = 0
        return 23

    def _op_inc_index_mem(self, prefix: int) -> int:
        """INC (IX+d)/(IY+d) (UM0080 pp. 168-169).

        WZ: z80memptr; SST dd 34.json.
        """
        addr = self._index_displacement_addr(prefix)
        self.write_byte(addr, self._inc(self.read_byte(addr)))
        self.q = self._f
        return 23

    def _op_dec_index_mem(self, prefix: int) -> int:
        """DEC (IX+d)/(IY+d) (UM0080 p. 170).

        WZ: z80memptr; SST dd 35.json.
        """
        addr = self._index_displacement_addr(prefix)
        self.write_byte(addr, self._dec(self.read_byte(addr)))
        self.q = self._f
        return 23

    def _op_ld_r_index_mem(self, prefix: int, sub_opcode: int) -> int:
        """LD r,(IX+d)/(IY+d) (UM0080 pp. 75, 77).

        WZ: z80memptr; SST dd 46.json.
        """
        dest = (sub_opcode >> 3) & 0x07
        addr = self._index_displacement_addr(prefix)
        self._write_reg(dest, self.read_byte(addr))
        self.q = 0
        return 19

    def _op_ld_index_mem_r(self, prefix: int, sub_opcode: int) -> int:
        """LD (IX+d)/(IY+d),r (UM0080 pp. 81, 83).

        WZ: z80memptr; SST dd 70.json.
        """
        src = sub_opcode & 0x07
        addr = self._index_displacement_addr(prefix)
        self.write_byte(addr, self._read_reg(src))
        self.q = 0
        return 19

    def _op_ld_index_mem_n(self, prefix: int) -> int:
        """LD (IX+d)/(IY+d),n (UM0080 pp. 86-87).

        WZ: z80memptr; SST dd 36.json.
        """
        addr = self._index_displacement_addr(prefix)
        self.write_byte(addr, self._read_operand_byte())
        self.q = 0
        return 19
