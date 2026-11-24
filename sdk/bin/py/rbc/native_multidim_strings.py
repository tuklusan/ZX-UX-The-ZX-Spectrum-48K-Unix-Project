# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""Typed native support for fixed-shape, multidimensional Spectrum string arrays.

DIM a$(d1,...,dn,width) uses row-major storage; a$(i1,...,in)
returns the width-character element, with any subsequent index a character
slice. Each subscript is evaluated once and checked *before* flattening.
Original tokenized BASIC and physical source files are left unchanged.
"""
from __future__ import annotations

import math
import re

_DIM = re.compile(rb'^\s*([A-Za-z])\$\s*\(([^)]*)\)')
_NUM = re.compile(rb'^\s*([0-9]+)(?:\x0e.{5})?\s*$', re.S)


def _dimensions(lines):
    """Recognize literal multi-axis DIM statements by tokens, not text."""
    result = {}
    for lineno, body in lines:
        quoted = data = False
        i = 0
        while i < len(body):
            c = body[i]
            if c == 0x0E and not quoted:
                i += 6
                continue
            if c == 34:
                quoted = not quoted
            elif not quoted and c == 0xEA:
                break
            elif not quoted and c == 0xE4:
                data = True
            elif not quoted and c == ord(':'):
                data = False
            elif not quoted and not data and c == 0xE9:
                match = _DIM.match(body[i+1:])
                if match:
                    fields = match[2].split(b',')
                    if len(fields) >= 3:
                        vals = [_NUM.fullmatch(field) for field in fields]
                        # An unrecognized shape remains the upstream compiler's responsibility.
                        # Always advance the byte scanner.
                        if all(vals):
                            sizes = tuple(int(v[1]) for v in vals)
                            if (min(sizes) >= 1 and math.prod(sizes) <= 65535
                                    and len(sizes) <= 9):
                                idx = (match[1][0] | 0x20) - 97
                                if idx in result and result[idx] != sizes:
                                    result[idx] = None
                                elif idx not in result:
                                    result[idx] = sizes
            i += 1
    return {i: size for i, size in result.items() if size is not None}


def with_multidim_strings(base, *, string_type, multiply_rt, element_rt):
    """Extend the HiSoft compiler in each pass; leave other string forms intact."""
    class MultidimensionalStrings(base):
        def reset(self, program):
            super().reset(program)
            self._zxux_multidim = _dimensions(self.lines)
            for i, sizes in self._zxux_multidim.items():
                self.strvars[i]['zxux_dims'] = sizes

        def dim_sizes(self, ent):
            dims = ent.get('zxux_dims')
            if dims is None:
                return super().dim_sizes(ent)
            self.next_char()  # Opening '(' to first dimension value.
            got = []
            while True:
                got.append(self.number_to_hl())
                if self.get_char() != ord(','):
                    break
                self.next_char()
            if (self.get_char() != ord(')') or tuple(got) != dims):
                self.not_supported('unproved multidimensional string DIM')
            self.next_char()
            self._dim_sizes_set(ent, last=dims[-1], first=math.prod(dims[:-1]))

        def _zxux_check_axis(self, bound):
            self.emit('push hl; ld a,h; or l; jr nz,+2; rst 8; defb 3; '
                      'ld de,{}; or a; sbc hl,de; jr c,+4; jr z,+2; '
                      'rst 8; defb 3; pop hl', bound)

        def string_var_value(self, sv):
            dims = sv.get('zxux_dims')
            if dims is None:
                return super().string_var_value(sv)
            # Called with CH_ADD at '('; for an array of shape [a,b,w], consume exactly
            # two scalar indexes, leaving optional slice arguments to the unchanged
            # HiSoft string routine.
            self.next_char()
            for ix, bound in enumerate(dims[:-1]):
                if ix:
                    self.emit('push hl')
                self.expr_int()
                self._zxux_check_axis(bound)
                self.emit('dec hl')
                if ix:
                    self.emit('ex de,hl; pop hl; push de; ld de,{}', bound)
                    self.call_rt(multiply_rt)
                    self.emit('pop de; add hl,de')
                if ix < len(dims) - 2:
                    if self.get_char() != ord(','):
                        self.not_supported('missing multidimensional string index')
                    self.next_char()
            self.emit('inc hl')
            if self.get_char() not in (ord(')'), ord(',')):
                self.not_supported('bad multidimensional string index')
            self.ld_de(sv['addr'])
            self.call_rt(element_rt)
            self._strarr_tail()

    return MultidimensionalStrings
