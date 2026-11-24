# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""Reserve scalar strings and enforce their physical capacity in native Z80.

No original BASIC line or HiSoft runtime binary is modified.
"""


def with_static_strings(base, proofs, letter):
    capacities = []
    for entry in proofs:
        name = entry['variable']
        limit = entry['max_chars']
        if (not isinstance(name, str) or len(name) != 2 or name[1] != '$'
                or not name[0].isalpha() or not name[0].isascii()
                or type(limit) is not int or not 1 <= limit <= 13000
                or (entry.get('storage_is_reservation') and
                    entry.get('bound_proof') !=
                    'native-runtime-checked-scalar-concatenation')):
            raise ValueError('invalid static text capacity')
        capacities.append((name[0].lower(), limit))
    if len({n for n, _ in capacities}) != len(capacities):
        raise ValueError('duplicate text-capacity assignment')
    from native_error_exit import error_exit_asm
    from rtnames import RT

    class StaticTextCompiler(base):
        def _let_string(self):
            # Retain the original HiSoft array-assignment path verbatim.
            c = self.get_char()
            sv = self.strvars[letter(c)]
            self.strvar_default_len(sv)
            self.next_char()
            c = self.next_char()
            if c == ord('(') or sv['flags']:
                self.string_var_value(sv)
                self.emit('call $2BF1; push de; push bc')
                self.let_string_value()
                self.emit('pop bc; pop hl; call $2B7F')
                self.set_work = 1
                return
            self.let_string_value()
            # The 48K calculator string descriptor ends at STKEND; its two-byte
            # length is at STKEND-2. Do not copy until length fits the allocated
            # descriptor+data backing storage.
            self.emit('ld hl,($5c65); dec hl; ld b,(hl); dec hl; ld c,(hl)')
            self.emit('ld hl,{}; or a; sbc hl,bc; jr nc,+15', sv['last'])
            self.emit(error_exit_asm(3))
            self.ld_hl(sv['addr'])
            self.call_rt(RT.STR_ASSIGN)

        def reset(self, program):
            super().reset(program)
            for name, capacity in capacities:
                entry = self.strvars[letter(ord(name))]
                if entry['flags'] or entry['first'] or entry['last']:
                    raise ValueError('text capacity conflicts with existing declaration')
                entry['last'] = capacity

    return StaticTextCompiler
