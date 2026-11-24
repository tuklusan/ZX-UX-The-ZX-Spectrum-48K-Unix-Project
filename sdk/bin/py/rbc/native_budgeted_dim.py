# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""Native bounded allocation for numeric INPUT-derived one-axis DIM.

The maximum resident storage comes from the actual native 12KB (or caller's
--max) admission budget, after an initial one-element native trial link.  This
is a physical-memory limit, not a guessed game-specific INPUT limit.  Runtime
DIM evaluates the original expression and rejects oversized requests before
writing; a subsequent DIM clears the new live span.  Other array forms stay
with the existing compiler extensions.
"""
from __future__ import annotations

from native_dynamic_dim import _active, _DIM, _EXPR, _ALL_NUMERIC_DIMS, _NAME


def unproved_numeric_dims(lines, proved):
    """Only wholly consistent 1D scalar expressions; never recognize prose."""
    result = {}
    seen = {}
    candidates = {}
    for _, source in lines:
        body = _active(source)
        for m in _ALL_NUMERIC_DIMS.finditer(body):
            k = m[1].lower()[0] - 97
            seen[k] = seen.get(k, 0) + 1
        for m in _DIM.finditer(body):
            k = m[1].lower()[0] - 97
            expression = m[2].strip()
            # The core expression generator, not this scanner, handles the typed evaluation.
            # Avoid arbitrary function calls and bad arity.
            parsed = _EXPR.fullmatch(expression)
            eligible = (parsed is not None and
                        _NAME.fullmatch(parsed.group(1)) is not None and
                        len(parsed.group(1)) <= 9 and
                        (parsed.group(3) is None or
                         len(parsed.group(3)) <= 9))
            candidates.setdefault(k, []).append(bool(eligible))
    for k, states in candidates.items():
        if k not in proved and len(states) == seen.get(k) and all(states):
            result[k] = len(states)
    return result



def capacity_for_native_budget(memory_limit, image, bss, stack, unit_bytes):
    """Reserve the most live elements admitted by the exact image+BSS budget.

    The SSX file-size admission remains a separate final check. It is not a
    substitute for the resident-image, BSS and stack requirement; when the
    file dominates trial memory, its size does not consume resident heap bytes.
    """
    if unit_bytes <= 0 or stack <= 0 or min(image, bss) < 0:
        raise ValueError('invalid native DIM allocation measurements')
    limit = memory_limit or 65535
    spare = max(0, limit - image - bss - stack)
    return min(13000, 1 + spare // unit_bytes)


def with_budgeted_numeric_dims(base, *, capacity: int, real_type, memfill_rt):
    if not 1 <= capacity <= 13000:
        raise ValueError('numeric DIM capacity outside native address range')

    class BudgetedNumericDimensions(base):
        def reset(self, program):
            super().reset(program)
            extra = unproved_numeric_dims(self.lines, self._zxux_dynamic_dims)
            self._zxux_budgeted_dims = frozenset(extra)
            for k in extra:
                self._zxux_dynamic_dims[k] = (b'', capacity)
                entry = self.arrays[k]
                entry['last'] = capacity
                entry['first'] = 0
                entry['zxux_dynamic_capacity'] = capacity

    return BudgetedNumericDimensions
