# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""Compile repeated, literal one-dimensional numeric DIM without changing BASIC.

A reserved maximum array capacity is separate from its live shape.  Every
DIM stores its runtime shape and clears exactly the declared elements; reads
and writes check the shape before touching memory.  Dynamic sizes and wider
shapes are intentionally left to the full dynamic-DIM implementation.
"""
from __future__ import annotations

import re


_DIM_OPERAND = re.compile(rb'^\s*([A-Za-z])(\$?)\s*\(([^)]*)\)')
_LITERAL = re.compile(rb'^\s*([0-9]+)(?:\x0e.{5})?\s*$', re.S)


def _executable_dims(lines):
    """Inspect tokens, not quoted strings, REM content, or numeric cache bytes."""
    shapes = {}
    for _, body in lines:
        quoted = False
        data_field = False
        i = 0
        while i < len(body):
            char = body[i]
            if char == 34:
                quoted = not quoted
            elif not quoted and char == 0xE4:
                data_field = True
            elif not quoted and char == 58:
                data_field = False
            elif not quoted and char == 14:
                i += 6
                continue
            elif not quoted and char == 234:
                break
            elif not quoted and not data_field and char == 0xE9:
                m = _DIM_OPERAND.match(body[i + 1:])
                if m:
                    idx = (m[1][0] | 0x20) - 97
                    field = m[3]
                    v = _LITERAL.fullmatch(field) if not m[2] else None
                    value = int(v[1]) if v and len(v[1]) < 7 else None
                    shapes.setdefault(idx, []).append(value if value is not None and 1 <= value <= 65535 else None)
                i += 1
                continue
            i += 1
    return {i: tuple(sizes) for i, sizes in shapes.items()
            if len(sizes) > 1 and None not in sizes and len(set(sizes)) > 1}


def with_literal_redims(base, *, real_type, runtime_memfill):
    """Create the generic native backend extension, retaining other DIM paths."""
    class Redimensioned(base):
        def reset(self, program):
            super().reset(program)
            self._zxux_redim = _executable_dims(self.lines)
            self._zxux_array_index = None
            for index, sizes in self._zxux_redim.items():
                self.arrays[index]['zxux_sizes'] = frozenset(sizes)
                self.arrays[index]['zxux_slot'] = 0

        def _dim_sizes_set(self, ent, last, first):
            if 'zxux_sizes' not in ent:
                return super()._dim_sizes_set(ent, last, first)
            if first or last not in ent['zxux_sizes']:
                self.not_supported('unproved repeated DIM shape')
            if self.pass0:
                ent['last'] = max(ent['last'], last)
                ent['first'] = 0
            self._zxux_dim_current = last

        def var_size(self, ent, t):
            size = super().var_size(ent, t)
            if 'zxux_sizes' in ent:
                ent['zxux_slot'] = ent['addr'] + size
                return size + 2
            return size

        def st_dim(self):
            c = self.get_char()
            index = (c | 0x20) - 97
            if index not in self._zxux_redim or self.peek_after() == ord('$'):
                return super().st_dim()
            ent = self.arrays[index]
            self.next_char()
            self.dim_sizes(ent)
            size = self._zxux_dim_current
            unit = 5 if ent['type'] == real_type else 2
            self.t = ent['type']
            self.ld_hl(size)
            self.st_hl(ent['zxux_slot'])
            self.ld_hl(ent['addr'])
            self.ld_bc_abs(size * unit - 1)
            self.emit('xor a')
            self.call_rt(runtime_memfill)

        def _guard_index(self, slot):
            # HL is the unsigned subscript. Both failure paths are before an array reference. The
            # ROM error is 3: Subscript wrong.
            self.emit('push hl; ld a,h; or l; jr nz,+2; rst 8; defb 3; '
                      'ld d,h; ld e,l')
            self.ld_hl_ind(slot)
            self.emit('or a; sbc hl,de; jr nc,+2; rst 8; defb 3; pop hl')

        def _array_rest(self, ent, pushed):
            index = self._zxux_array_index
            if index not in self._zxux_redim:
                return super()._array_rest(ent, pushed)
            if not self.probing:
                self.expr_int()
                if self.get_char() != ord(')'):
                    self.not_supported('array')
                self.next_char()
                self.t = ent['type']
                self._guard_index(ent['zxux_slot'])
            self.ld_de(pushed)
            self.const_index = 0
            return None

        def array_ref(self):
            index = (self.get_char() | 0x20) - 97
            previous = self._zxux_array_index
            self._zxux_array_index = index
            try:
                address = super().array_ref()
            finally:
                self._zxux_array_index = previous
            if index in self._zxux_redim and self.const_index and not self.probing:
                ent = self.arrays[index]
                unit = 5 if ent['type'] == real_type else 2
                subscript = (address - ent['addr']) // unit + 1
                self.ld_hl(subscript)
                self._guard_index(ent['zxux_slot'])
            return address

    return Redimensioned
