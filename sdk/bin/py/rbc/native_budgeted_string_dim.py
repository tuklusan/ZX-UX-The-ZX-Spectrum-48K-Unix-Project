# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""Runtime one-dimensional string DIM with measured native memory admission.

Compile DIM S$(N) from the original tokenized BASIC, retaining the mutable
runtime width descriptor and the ROM's subscript errors.  The physical ceiling
is shared with any budgeted numeric arrays; no game-specific size is assumed.
"""
from __future__ import annotations

import re

from native_dynamic_dim import _active, _EXPR, _NAME

_DIM = re.compile(rb'\xe9\s*([A-Za-z])\$\s*\(\s*([^():\r]*)\)')
_ALL = re.compile(rb'\xe9\s*([A-Za-z])\$\s*\(')


def unproved_string_dims(lines, proved):
    counts = {}
    expressions = {}
    for _, source in lines:
        body = _active(source)
        for m in _ALL.finditer(body):
            key = m[1].lower()[0] - 97
            counts[key] = counts.get(key, 0) + 1
        for m in _DIM.finditer(body):
            key = m[1].lower()[0] - 97
            parsed = _EXPR.fullmatch(m[2].strip())
            valid = (parsed is not None and
                     _NAME.fullmatch(parsed.group(1)) is not None and
                     len(parsed.group(1)) <= 9 and
                     (parsed.group(3) is None or len(parsed.group(3)) <= 9))
            expressions.setdefault(key, []).append(bool(valid))
    return {key: len(fields) for key, fields in expressions.items()
            if key not in proved and len(fields) == counts[key] and all(fields)}


def with_budgeted_string_dims(base, *, capacity: int):
    if not 1 <= capacity <= 13000:
        raise ValueError('string DIM capacity outside native address range')

    class BudgetedStringDimensions(base):
        def reset(self, program):
            super().reset(program)
            extra = unproved_string_dims(self.lines, self._zxux_dynamic_string_dims)
            self._zxux_budgeted_string_dims = frozenset(extra)
            for key in extra:
                self._zxux_dynamic_string_dims[key] = (b'', capacity)
                entry = self.strvars[key]
                entry['flags'] = 1
                entry['last'] = capacity
                entry['first'] = 0

    return BudgetedStringDimensions
