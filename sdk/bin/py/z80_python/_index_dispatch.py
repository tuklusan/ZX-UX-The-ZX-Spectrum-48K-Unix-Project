"""DD/FD index-prefix dispatcher.

A DD or FD prefix is its own M1 fetch on real hardware: it costs 4 T-states and
bumps R before the opcode after it is fetched. Base-set opcodes that the prefix
does not modify therefore run their ordinary handler and add that 4 here; the
handlers that take a ``prefix`` argument return their documented totals, which
already include it. The prefix M1 also writes no flags, so Q is 0 when the
prefixed opcode runs; only SCF and CCF can see the difference.

A DD or FD is not an instruction but a flag saying "use IX (or IY) instead of
HL" for the opcode that follows. That is why a run of them is legal: each one
is a stray M1 that costs 4 T-states and bumps R, the last one decides the
register, and an ED after any of them starts an ED instruction that the flag
cannot touch. Sean Young, *The Undocumented Z80 Documented* v0.91, sections
3.7 and 6.1; FUSE's ``ddfd00`` test case encodes the same costs.
"""

from z80_python._dispatch import OPCODE, every8

# DD/FD leaves B, C, D, E and A alone. They escaped the index detour.
# H, L and (HL) become IX/IY byte registers and displaced memory.
_PLAIN = (0, 1, 2, 3, 7)


def _plain(opcodes: range, *, register_fields: tuple[int, ...]) -> list[int]:
    """The opcodes whose register fields (at bit 0 and/or bit 3) all name plain registers."""
    return [op for op in opcodes if all((op >> shift) & 7 in _PLAIN for shift in register_fields)]


# A rule is (opcodes, handler, argument, prefixed). A prefixed handler names an IX/IY
# operand (it lives in _index.py), is called with the prefix (0xDD or 0xFD) before its
# argument, and returns its own total. Any other handler is the base-set one, called
# as on the main page, plus the prefix's 4 T-states.
INDEX_RULES = (
    ((0x09, 0x19, 0x29, 0x39), "_op_add_index_rr", OPCODE, True),
    ((0x21,), "_op_ld_index_nn", None, True),
    ((0x22,), "_op_ld_nn_index", None, True),
    ((0x23,), "_op_inc_index", None, True),
    ((0x24, 0x25, 0x2C, 0x2D), "_op_inc_dec_index_byte", OPCODE, True),
    ((0x26, 0x2E), "_op_ld_index_byte_n", OPCODE, True),
    ((0x2A,), "_op_ld_index_nn_from_mem", None, True),
    ((0x2B,), "_op_dec_index", None, True),
    ((0x34,), "_op_inc_index_mem", None, True),
    ((0x35,), "_op_dec_index_mem", None, True),
    ((0x36,), "_op_ld_index_mem_n", None, True),
    (
        (0x44, 0x45, 0x4C, 0x4D, 0x54, 0x55, 0x5C, 0x5D, 0x7C, 0x7D),
        "_op_ld_r_index_byte",
        OPCODE,
        True,
    ),
    ((0x46, 0x4E, 0x56, 0x5E, 0x66, 0x6E, 0x7E), "_op_ld_r_index_mem", OPCODE, True),
    (_plain(range(0x60, 0x70), register_fields=(0,)), "_op_ld_index_byte_r", OPCODE, True),
    ((0x64, 0x65, 0x6C, 0x6D), "_op_ld_index_byte_index_byte", OPCODE, True),
    ((0x70, 0x71, 0x72, 0x73, 0x74, 0x75, 0x77), "_op_ld_index_mem_r", OPCODE, True),
    ([op for op in range(0x80, 0xC0) if op & 7 in (4, 5)], "_op_alu_index_byte", OPCODE, True),
    (range(0x86, 0xC0, 8), "_op_alu_index_mem", OPCODE, True),
    ((0xCB,), "_execute_index_cb", None, True),
    ((0xE1,), "_op_pop_index", None, True),
    ((0xE3,), "_op_ex_sp_index", None, True),
    ((0xE5,), "_op_push_index", None, True),
    ((0xE9,), "_op_jp_index", None, True),
    ((0xF9,), "_op_ld_sp_index", None, True),
    # Everything else ignores the prefix: the base-set handler, plus 4.
    ((0x00,), "_op_nop", None, False),
    ((0x01, 0x11, 0x31), "_op_ld_rr_nn", OPCODE, False),
    ((0x02, 0x12), "_op_ld_irr_a", OPCODE, False),
    ((0x03, 0x13, 0x33), "_op_inc_rr", OPCODE, False),
    ((0x04, 0x0C, 0x14, 0x1C, 0x3C), "_op_inc_r", OPCODE, False),
    ((0x05, 0x0D, 0x15, 0x1D, 0x3D), "_op_dec_r", OPCODE, False),
    ((0x06, 0x0E, 0x16, 0x1E, 0x3E), "_op_ld_r_n", OPCODE, False),
    ((0x07,), "_op_rlca", None, False),
    ((0x08,), "_op_ex_af_af", None, False),
    ((0x0A, 0x1A), "_op_ld_a_irr", OPCODE, False),
    ((0x0B, 0x1B, 0x3B), "_op_dec_rr", OPCODE, False),
    ((0x0F,), "_op_rrca", None, False),
    ((0x10,), "_op_djnz", None, False),
    ((0x17,), "_op_rla", None, False),
    ((0x18, 0x20, 0x28, 0x30, 0x38), "_op_jr", OPCODE, False),
    ((0x1F,), "_op_rra", None, False),
    ((0x27,), "_op_daa", None, False),
    ((0x2F,), "_op_cpl", None, False),
    ((0x32,), "_op_ld_inn_a", None, False),
    ((0x37, 0x3F), "_op_scf_ccf", OPCODE, False),
    ((0x3A,), "_op_ld_a_inn", None, False),
    (_plain(range(0x40, 0x80), register_fields=(0, 3)), "_op_ld_r_r", OPCODE, False),
    ((0x76,), "_op_halt", None, False),
    (_plain(range(0x80, 0xC0), register_fields=(0,)), "_op_alu_r", OPCODE, False),
    (every8(0xC0), "_op_ret_cc", OPCODE, False),
    ((0xC1, 0xD1), "_op_pop_rr", OPCODE, False),
    ((*every8(0xC2), 0xC3), "_op_jp", OPCODE, False),
    ((*every8(0xC4), 0xCD), "_op_call", OPCODE, False),
    ((0xC5, 0xD5), "_op_push_rr", OPCODE, False),
    (every8(0xC6), "_op_alu_n", OPCODE, False),
    (every8(0xC7), "_op_rst", OPCODE, False),
    ((0xC9,), "_op_ret", None, False),
    ((0xD3,), "_op_out_n_a", None, False),
    ((0xD9,), "_op_exx", None, False),
    ((0xDB,), "_op_in_a_n", None, False),
    ((0xEB,), "_op_ex_de_hl", None, False),
    ((0xF1,), "_op_pop_af", None, False),
    ((0xF3,), "_op_interrupt_enable", False, False),
    ((0xF5,), "_op_push_af", None, False),
    ((0xFB,), "_op_interrupt_enable", True, False),
)

# DD CB d op / FD CB d op: the operation is always on (IX+d)/(IY+d); bits 2-0 name a register
# that also receives the result (the undocumented forms).
INDEX_CB_RULES = (
    (range(0x00, 0x40), "_op_index_rot", OPCODE),
    (range(0x40, 0x80), "_op_index_bit", OPCODE),
    (range(0x80, 0x100), "_op_index_res_set", OPCODE),
)


class IndexDispatchMixin:
    """Private dispatcher for the DD/FD and DD CB/FD CB pages."""

    def _execute_index(self, prefix: int) -> int:
        sub_opcode = self._fetch_byte()
        stray_t_states = 0
        while sub_opcode == 0xDD or sub_opcode == 0xFD:
            # A DD or FD before another DD or FD is a stray prefix: its own M1 (4
            # T-states, R+1, already counted by _fetch_byte) and nothing else. "In a
            # large sequence of DD and FD bytes, it is the last one that counts"
            # (Young 3.7). No interrupt is accepted inside the run, because the run is
            # one instruction to step() (Young 5.5).
            prefix = sub_opcode
            sub_opcode = self._fetch_byte()
            stray_t_states += 4
        if sub_opcode == 0xED:
            # "If CB or ED is encountered, that byte plus the next make up an instruction"
            # (Young 3.7), and ED instructions never use the IX/IY substitution (Young
            # 3.2), so the DD/FD is a 4-T-state stray.
            return stray_t_states + 4 + self._execute_ed()
        self.q = 0  # the prefix M1 wrote no flags
        handler, argument, prefixed = self._index_page[sub_opcode]
        if prefixed:
            if argument is None:
                return stray_t_states + handler(self, prefix)
            return stray_t_states + handler(self, prefix, argument)
        if argument is None:
            return stray_t_states + handler(self) + 4
        return stray_t_states + handler(self, argument) + 4

    def _execute_index_cb(self, prefix: int) -> int:
        # DD CB d op: the displacement comes before the final opcode, and
        # both are read as operands, not M1 fetches, so R advances only
        # for the DD and CB prefixes.
        displacement = self._read_operand_byte()
        cb_opcode = self._read_operand_byte()
        return self._index_cb_page[cb_opcode](self, prefix, displacement, cb_opcode)
