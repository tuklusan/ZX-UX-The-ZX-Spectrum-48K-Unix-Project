# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""Typed bounded runtime DIM for a one-dimensional Spectrum string.

DIM A$(N) declares one mutable string of length N, not N array elements.
Reserve the maximum proven N, write the *evaluated* length into the native
string descriptor and clear the active span on every DIM execution.  All
source and cached 48K Sinclair numeric metadata stay byte-for-byte intact.
Unproved dynamic bounds remain unsupported (never silently capped).
"""
from __future__ import annotations
import re
from native_dynamic_dim import _active, _proved_dimensions

_DIM = re.compile(rb'\xe9\s*([A-Za-z])(\$?)\s*\(')


def _proved_string_lengths(lines):
    """Use the numeric proof engine on a separate, proof-only token view.

    Numeric arrays are absent from this view, while each tokenised DIM A$(...)
    becomes a proof-only DIM A(...). Neither the compiler nor its BASIC input
    ever sees that view. This retains all negative checks on scalar writes.
    """
    view = []
    for line, body in lines:
        masked = bytearray(_active(body))
        matches = list(_DIM.finditer(masked))
        # Work in reverse so removing '$' doesn't invalidate prior offsets.
        for m in reversed(matches):
            if m[2] == b'$':
                del masked[m.start(2):m.end(2)]
            else:
                masked[m.start():m.end()] = b' ' * (m.end() - m.start())
        view.append((line, bytes(masked)))
    return _proved_dimensions(view)


def with_bounded_string_dims(base, *, string_type, memfill_rt):
    class BoundedStringDimensions(base):
        def _zxux_bound_guard(self, bound):
            self.emit('push hl; ld a,h; or l; jr nz,+2; rst 8; defb 3; '
                      'ld d,h; ld e,l; ld hl,{}; or a; sbc hl,de; '
                      'jr nc,+2; rst 8; defb 3; pop hl', bound)

        def reset(self, program):
            super().reset(program)
            self._zxux_dynamic_string_dims = _proved_string_lengths(self.lines)
            for index, (_, capacity) in self._zxux_dynamic_string_dims.items():
                ent = self.strvars[index]
                ent['flags'] = 1
                ent['last'] = capacity
                ent['first'] = 0

        def st_dim(self):
            name = self.get_char()
            index = (name | 0x20) - 97
            if (index not in self._zxux_dynamic_string_dims
                    or self.peek_after() != ord('$')):
                return super().st_dim()
            ent = self.strvars[index]
            self.next_char()  # '$'
            self.next_char()  # '('
            self.next_char()  # evaluated dimension expression
            self.expr_int()
            if self.get_char() != ord(')'):
                self.not_supported('dynamic string DIM expects one bound')
            self.next_char()
            self.t = string_type
            bound = ent['last']
            # HL must be between 1 and the proven allocated capacity.
            self._zxux_bound_guard(bound)
            self.st_hl(ent['addr'])
            self.emit('dec hl; ld b,h; ld c,l')
            self.ld_hl(ent['addr'] + 2)
            self.emit('ld a,32')
            self.call_rt(memfill_rt)

    return BoundedStringDimensions
