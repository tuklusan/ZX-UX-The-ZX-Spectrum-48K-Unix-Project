"""Opcode dispatch: which handler runs for each byte of each opcode page.

The Z80 decodes five pages of 256 opcodes: the main page, and the pages after
the CB, ED, DD/FD and DD CB/FD CB prefixes. Each page is a 256-entry table
built once per class from the rules below, so that executing an instruction
is one list index and one call. The table is data; the handlers are code.
Every entry names an ``_op_*`` method, so grepping a mnemonic still lands on
the method that implements it, and on its docstring.

A rule is ``(opcodes, handler, argument)``. ``argument`` is what the handler
is called with: ``OPCODE`` means the opcode byte itself, ``None`` means no
argument, and anything else is passed as it is. Main, CB and ED handlers
return the instruction's whole T-state total, prefix fetches included. The
DD/FD page and its rules are in ``_index_dispatch.py``, beside the
specification of prefix runs.
"""

from collections.abc import Iterable

# Pass the opcode byte to its handler; it picks apart its own bits.
OPCODE = object()

Rule = tuple[Iterable[int], str, object]


def every8(first: int) -> range:
    """The eight opcodes ``first``, ``first + 8``, ... that differ only in bits 5-3."""
    return range(first, first + 0x40, 8)


# Main page. Bits 5-3 of an opcode select a register (B C D E H L (HL) A) or a condition (NZ
# Z NC C PO PE P M); bits 5-4 select a pair (BC DE HL SP).
MAIN_RULES: tuple[Rule, ...] = (
    ((0x00,), "_op_nop", None),
    ((0x01, 0x11, 0x21, 0x31), "_op_ld_rr_nn", OPCODE),
    ((0x02, 0x12), "_op_ld_irr_a", OPCODE),
    ((0x03, 0x13, 0x23, 0x33), "_op_inc_rr", OPCODE),
    ([op for op in every8(0x04) if op != 0x34], "_op_inc_r", OPCODE),
    ([op for op in every8(0x05) if op != 0x35], "_op_dec_r", OPCODE),
    (every8(0x06), "_op_ld_r_n", OPCODE),
    ((0x07,), "_op_rlca", None),
    ((0x08,), "_op_ex_af_af", None),
    ((0x09, 0x19, 0x29, 0x39), "_op_add_hl_rr", OPCODE),
    ((0x0A, 0x1A), "_op_ld_a_irr", OPCODE),
    ((0x0B, 0x1B, 0x2B, 0x3B), "_op_dec_rr", OPCODE),
    ((0x0F,), "_op_rrca", None),
    ((0x10,), "_op_djnz", None),
    ((0x17,), "_op_rla", None),
    ((0x18, 0x20, 0x28, 0x30, 0x38), "_op_jr", OPCODE),
    ((0x1F,), "_op_rra", None),
    ((0x22,), "_op_ld_nn_hl", None),
    ((0x27,), "_op_daa", None),
    ((0x2A,), "_op_ld_hl_nn_from_mem", None),
    ((0x2F,), "_op_cpl", None),
    ((0x32,), "_op_ld_inn_a", None),
    ((0x34,), "_op_inc_hl", None),
    ((0x35,), "_op_dec_hl", None),
    ((0x37, 0x3F), "_op_scf_ccf", OPCODE),
    ((0x3A,), "_op_ld_a_inn", None),
    ([op for op in range(0x40, 0x80) if op != 0x76], "_op_ld_r_r", OPCODE),
    ((0x76,), "_op_halt", None),
    (range(0x80, 0xC0), "_op_alu_r", OPCODE),
    (every8(0xC0), "_op_ret_cc", OPCODE),
    ((0xC1, 0xD1, 0xE1), "_op_pop_rr", OPCODE),
    ((*every8(0xC2), 0xC3), "_op_jp", OPCODE),
    ((*every8(0xC4), 0xCD), "_op_call", OPCODE),
    ((0xC5, 0xD5, 0xE5), "_op_push_rr", OPCODE),
    (every8(0xC6), "_op_alu_n", OPCODE),
    (every8(0xC7), "_op_rst", OPCODE),
    ((0xC9,), "_op_ret", None),
    ((0xCB,), "_execute_cb", None),
    ((0xD3,), "_op_out_n_a", None),
    ((0xD9,), "_op_exx", None),
    ((0xDB,), "_op_in_a_n", None),
    ((0xDD, 0xFD), "_execute_index", OPCODE),
    ((0xE3,), "_op_ex_sp_hl", None),
    ((0xE9,), "_op_jp_hl", None),
    ((0xEB,), "_op_ex_de_hl", None),
    ((0xED,), "_execute_ed", None),
    ((0xF1,), "_op_pop_af", None),
    ((0xF3,), "_op_interrupt_enable", False),
    ((0xF5,), "_op_push_af", None),
    ((0xF9,), "_op_ld_sp_hl", None),
    ((0xFB,), "_op_interrupt_enable", True),
)

# CB page: bits 7-6 pick the group, bits 5-3 the operation or bit
# number, bits 2-0 the register.
CB_RULES: tuple[Rule, ...] = (
    (range(0x00, 0x40), "_op_rot", OPCODE),
    (range(0x40, 0x80), "_op_bit", OPCODE),
    (range(0x80, 0xC0), "_op_res", OPCODE),
    (range(0xC0, 0x100), "_op_set", OPCODE),
)

# ED page. Every byte not listed is a genuine instruction on real silicon: a two-byte,
# 8-T-state no-op. Hence the default below.
ED_DEFAULT = ("_op_ed_nop", None)
ED_RULES: tuple[Rule, ...] = (
    (every8(0x40), "_op_in_r_c", OPCODE),
    (every8(0x41), "_op_out_c_r", OPCODE),
    ((0x42, 0x52, 0x62, 0x72), "_op_sbc_hl_rr", OPCODE),
    ((0x4A, 0x5A, 0x6A, 0x7A), "_op_adc_hl_rr", OPCODE),
    *(((0x43 | pair << 4,), "_op_ld_nn_rr", pair) for pair in range(4)),
    *(((0x4B | pair << 4,), "_op_ld_rr_nn_from_mem", pair) for pair in range(4)),
    (every8(0x44), "_op_neg", None),
    ((0x45, 0x55, 0x65, 0x75), "_op_retn", None),
    ((0x4D, 0x5D, 0x6D, 0x7D), "_op_reti", None),
    ((0x46, 0x4E, 0x66, 0x6E), "_op_im", 0),
    ((0x56, 0x76), "_op_im", 1),
    ((0x5E, 0x7E), "_op_im", 2),
    ((0x47,), "_op_ld_i_a", None),
    ((0x4F,), "_op_ld_r_a", None),
    ((0x57,), "_op_ld_a_i", None),
    ((0x5F,), "_op_ld_a_r", None),
    ((0x67,), "_op_rrd", None),
    ((0x6F,), "_op_rld", None),
    ((0xA0,), "_op_ldi", None),
    ((0xA1,), "_op_cpi", None),
    ((0xA2,), "_op_ini", None),
    ((0xA3,), "_op_outi", None),
    ((0xA8,), "_op_ldd", None),
    ((0xA9,), "_op_cpd", None),
    ((0xAA,), "_op_ind", None),
    ((0xAB,), "_op_outd", None),
    ((0xB0,), "_op_ldir", None),
    ((0xB1,), "_op_cpir", None),
    ((0xB2,), "_op_inir", None),
    ((0xB3,), "_op_otir", None),
    ((0xB8,), "_op_lddr", None),
    ((0xB9,), "_op_cpdr", None),
    ((0xBA,), "_op_indr", None),
    ((0xBB,), "_op_otdr", None),
)


def build_page(
    cls: type,
    rules: Iterable[tuple],
    *,
    default: tuple[str, object] | None = None,
    unassigned: Iterable[int] = (),
) -> list:
    """Return the 256 entries of one page of ``cls`` from its rules.

    An entry is ``(handler, argument)``, followed by any further columns the
    rule carries. Each opcode must be claimed by exactly one rule (or fall to
    ``default``), except those in ``unassigned``, which the page's executor
    handles before it looks in the table; their entries are ``None``.
    """
    page: list = [None] * 256
    for opcodes, name, argument, *columns in rules:
        handler = getattr(cls, name)
        for opcode in opcodes:
            if page[opcode] is not None:
                raise ValueError(f"{name}: opcode 0x{opcode:02X} is claimed twice")
            page[opcode] = (handler, opcode if argument is OPCODE else argument, *columns)
    if default is not None:
        name, argument = default
        handler = getattr(cls, name)
        for opcode in range(256):
            if page[opcode] is None and opcode not in unassigned:
                page[opcode] = (handler, argument)
    missing = [op for op in range(256) if page[op] is None and op not in unassigned]
    if missing:
        raise ValueError("unassigned opcodes: " + " ".join(f"{op:02X}" for op in missing))
    return page


class DispatchMixin:
    """Private instruction fetch and dispatch for the main, CB and ED pages."""

    def decode_and_execute(self) -> int:
        """Fetch and execute one instruction, ignoring pending interrupts; return T-states."""
        handler, argument = self._main_page[self._fetch_byte()]
        if argument is None:
            return handler(self)
        return handler(self, argument)

    def _execute_cb(self) -> int:
        handler, sub_opcode = self._cb_page[self._fetch_byte()]
        return handler(self, sub_opcode)

    def _execute_ed(self) -> int:
        handler, argument = self._ed_page[self._fetch_byte()]
        if argument is None:
            return handler(self)
        return handler(self, argument)
