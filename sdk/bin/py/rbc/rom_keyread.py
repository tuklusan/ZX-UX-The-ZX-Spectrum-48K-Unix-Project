# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""Read-only access to the Spectrum ROM's last-key state.

The original BASIC programs inspect the fixed KSTATE byte at address 23556.
Reading it cannot alter shared ZX-UX state. All other global memory reads
and every global memory write remain subject to strict checks.
"""
from __future__ import annotations
import re

_KEY_STATE = re.compile(r'^\s*23556\b(?!\s*[+\-*/^])')


def allow_key_state_read(findings):
    changed = 0
    for item in findings:
        if (item.operation == 'PEEK' and
                item.classification == 'global_memory_read' and
                item.severity == 'block' and
                _KEY_STATE.match(item.expression)):
            item.severity = 'info'
            item.classification = 'rom_keyboard_read'
            changed += 1
    return changed