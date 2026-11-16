# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""Permit only proved Spectrum system-variable accesses redirected into BSS.

The compiler must install native_sysvars_rt on all PEEK/POKE operations. This
module is only the source review; it grants no access to actual ZX-UX globals.
"""
from __future__ import annotations
import re

from spectrum_sysvars import PRIVATE
from spectrum_fonts import CHARS_LOW, CHARS_HIGH

_ADDRESS = re.compile(r'^\s*(23606|23607|23609|23658|23672|23673|23674|23675|23676|23692)(?!\d)')


def allow_private_sysvars(findings):
    accepted = 0
    for item in findings:
        if item.operation not in ('PEEK','POKE') or item.severity != 'block':
            continue
        m = _ADDRESS.match(item.expression)
        if not m or int(m[1]) not in PRIVATE | {CHARS_LOW, CHARS_HIGH, 23675, 23676}:
            continue
        suffix = item.expression[m.end():].lstrip()
        if (item.operation == 'POKE' and suffix and not suffix.startswith(',')) or (
                item.operation == 'PEEK' and suffix and suffix[0] not in ',:;)'):
            continue
        item.severity = 'info'
        item.classification = 'process_sysvar_' + item.operation.lower()
        accepted += 1
    # The compiled PEEK helper rejects every other protected address at runtime
    # rather than exposing kernel memory or requiring static math. This includes
    # dynamically calculated PEEK addresses.
    for item in findings:
        if item.operation == 'PEEK' and item.severity == 'block':
            if item.classification in ('global_memory_read','unbounded_memory_read'):
                item.severity = 'info'
                item.classification = 'runtime_guarded_peek'
                accepted += 1
    return accepted
