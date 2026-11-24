# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""Bounded runtime numeric DIM driven by scalar arithmetic with proved values.

The original DIM operand is compiled, not substituted. Each array reserves its
proved maximum plus a live-length slot. DIM writes the evaluated live count and
clears that many elements; every indexed access is checked against the live
count. Unknown bounds are left to upstream HiSoft, which refuses them.

This is deliberately not an unbounded runtime allocator, and cannot discharge
the whole BASIC DIM gate. The proof concerns only literal scalar assignments
and disallows paths that can write a controller through INPUT, READ, FOR/NEXT.
"""
from __future__ import annotations

import re

_DIM = re.compile(rb'\xe9\s*([A-Za-z])\s*\(\s*([^():\r]*)\)')
_EXPR = re.compile(rb'([A-Za-z][A-Za-z0-9]*)(?:\s*([+\-])\s*([A-Za-z][A-Za-z0-9]*|[0-9]+))?')
_NAME = re.compile(rb'[A-Za-z][A-Za-z0-9]*')
_ALL_NUMERIC_DIMS = re.compile(rb'\xe9\s*([A-Za-z])(?!\$)\s*\(')
_ASSIGN = re.compile(rb'\xf1\s*([A-Za-z][A-Za-z0-9]*)\s*=')
_LITERAL_ASSIGN = re.compile(rb'\xf1\s*([A-Za-z][A-Za-z0-9]*)\s*=\s*([0-9]+)\s*(?=[:\r]|$)')
_WRITE_TOKENS = (0xEE, 0xE3, 0xEB, 0xF3)  # INPUT, READ, FOR, NEXT


def _active(body):
    """Mask string, REM, DATA, control bytes and cached numeric metadata."""
    result = bytearray(body)
    quote = data = False
    i = 0
    while i < len(result):
        c = result[i]
        if not quote and c == 14 and i + 5 < len(result):
            result[i:i+6] = b' ' * 6
            i += 6
            continue
        if c == 34:
            quote = not quote
            result[i] = 32
        elif not quote and c == 234:
            result[i:] = b' ' * (len(result)-i)
            break
        elif not quote and c == 228:
            data = True
            result[i] = 32
        elif not quote and c == 58:
            data = False
        elif quote or data:
            result[i] = 32
        i += 1
    return bytes(result)


def _proved_dimensions(lines):
    bodies = [_active(body) for _, body in lines]
    declarations = {}
    other_shapes = {}
    setters = {}
    forbidden = set()
    for body in bodies:
        for m in _ALL_NUMERIC_DIMS.finditer(body):
            arr = m[1].lower()
            other_shapes[arr] = other_shapes.get(arr, 0) + 1
        for m in _DIM.finditer(body):
            arr = m[1].lower()
            match = _EXPR.fullmatch(m[2].strip())
            declarations.setdefault(arr, []).append(match.groups() if match else None)
        for m in _ASSIGN.finditer(body):
            ctl = m[1].lower()
            match = _LITERAL_ASSIGN.match(body, m.start())
            if not match:
                forbidden.add(ctl)
                continue
            number = int(match[2]) if len(match[2]) <= 5 else 0
            if not 1 <= number <= 65535:
                forbidden.add(ctl)
            else:
                setters.setdefault(ctl, []).append(number)
        for token in _WRITE_TOKENS:
            i = 0
            while True:
                at = body.find(bytes((token,)), i)
                if at < 0:
                    break
                end = body.find(b':', at)
                if end < 0:
                    end = len(body)
                if token == 0xEB:
                    # FOR modifies only its control variable; variables in its TO and
                    # STEP expressions are read-only.
                    field = body[at+1:end].lstrip()
                    name = _NAME.match(field)
                    if name:
                        forbidden.add(name[0].lower())
                else:
                    # INPUT, READ and NEXT can write every destination listed.
                    forbidden.update(m[0].lower() for m in _NAME.finditer(body[at+1:end]))
                i = end + 1
    result = {}
    for arr, expressions in declarations.items():
        # Every occurrence of DIM for this array must have exactly one proven scalar expression;
        # mixed dimensions are left to HiSoft to reject.
        if len(expressions) != other_shapes[arr] or None in expressions:
            continue
        possible = []
        valid = True
        for first, operator, operand in expressions:
            first = first.lower()
            if first in forbidden or first not in setters:
                valid = False
                break
            minimum, maximum = min(setters[first]), max(setters[first])
            if operator:
                if operand[:1].isdigit():
                    if len(operand) > 5:
                        valid = False
                        break
                    low = high = int(operand)
                else:
                    name = operand.lower()
                    if name in forbidden or name not in setters:
                        valid = False
                        break
                    low, high = min(setters[name]), max(setters[name])
                if operator == b'+':
                    minimum, maximum = minimum + low, maximum + high
                else:
                    minimum, maximum = minimum - high, maximum - low
            if not 1 <= minimum <= maximum <= 65535 // 5:
                valid = False
                break
            possible.append(maximum)
        if valid:
            # Retain the original single-controller shape for older callers; only richer arithmetic
            # returns its complete expression proof.
            plain = (len(set(expressions)) == 1 and expressions[0][1] is None
                     and len(expressions[0][0]) == 1)
            proof = expressions[0][0].lower() if plain else tuple(expressions)
            result[arr[0] - 97] = (proof, max(possible))
    return result


def with_bounded_dynamic_dims(base, *, real_type, memfill_rt):
    class BoundedDynamicDims(base):
        def reset(self, program):
            super().reset(program)
            self._zxux_dynamic_dims = _proved_dimensions(self.lines)
            for idx, (_, capacity) in self._zxux_dynamic_dims.items():
                entry = self.arrays[idx]
                entry['last'] = capacity
                entry['first'] = 0
                entry['zxux_dynamic_capacity'] = capacity

        def var_size(self, entry, kind):
            size = super().var_size(entry, kind)
            if 'zxux_dynamic_capacity' in entry:
                entry['zxux_dynamic_slot'] = entry['addr'] + size
                return size + 2
            return size

        def _zxux_valid_count(self, cap):
            # HL is the evaluated count. Reject zero and unsigned overflow.
            self.emit('push hl; ld a,h; or l; jr nz,+2; rst 8; defb 3; '
                      'ld d,h; ld e,l; ld hl,{}; or a; sbc hl,de; '
                      'jr nc,+2; rst 8; defb 3; pop hl', cap)

        def _zxux_valid_index(self, slot):
            # Guard before computing or dereferencing any indexed address.
            self.emit('push hl; ld a,h; or l; jr nz,+2; rst 8; defb 3; '
                      'ld d,h; ld e,l')
            self.ld_hl_ind(slot)
            self.emit('or a; sbc hl,de; jr nc,+2; rst 8; defb 3; pop hl')

        def st_dim(self):
            name = self.get_char()
            idx = (name | 0x20) - 97
            if idx not in self._zxux_dynamic_dims or self.peek_after() == ord('$'):
                return super().st_dim()
            entry = self.arrays[idx]
            self.next_char()  # Opening '('
            self.next_char()  # Original variable expression
            self.expr_int()
            if self.get_char() != ord(')'):
                self.not_supported('dynamic numeric DIM requires proved scalar bound')
            self.next_char()
            self.t = entry['type']
            self._zxux_valid_count(entry['zxux_dynamic_capacity'])
            self.st_hl(entry.get('zxux_dynamic_slot', 0))
            if entry['type'] == real_type:
                self.emit('push hl; add hl,hl; add hl,hl; pop de; add hl,de')
            else:
                self.emit('add hl,hl')
            self.emit('dec hl; ld b,h; ld c,l')
            self.ld_hl(entry['addr'])
            self.emit('xor a')
            self.call_rt(memfill_rt)

        def array_ref(self):
            name = self.get_char()
            idx = (name | 0x20) - 97
            if idx not in self._zxux_dynamic_dims:
                return super().array_ref()
            entry = self.arrays[idx]
            self.const_index = 0
            self.next_char()
            self.next_char()
            self.expr_int()
            if self.get_char() != ord(')'):
                self.not_supported('dynamic array must use one subscript')
            self.next_char()
            self.t = entry['type']
            self._zxux_valid_index(entry.get('zxux_dynamic_slot', 0))
            self.ld_de(entry['addr'])
            return None

    return BoundedDynamicDims
