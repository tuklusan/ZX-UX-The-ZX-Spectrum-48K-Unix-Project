# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""Strictly recognize original 48K keyboard control byte writes.

Only literal values used by the archived games are admitted. The repeat
controls are saved/restored only for programs that write them; FLAGS2 and
PIP retain their existing process-isolated implementation.
"""
from __future__ import annotations
import re

_CONTROLS = {23658: {0, 9, 10, 255}, 23609: {110, 111},
             23561: {35, 255}, 23562: {5, 255}}
_ASSIGNMENT = re.compile(r"^\s*(23658|23609|23561|23562)\s*,\s*(-?[0-9]+)\s*$")


def allow_rom_keyboard_controls(findings):
    changed = 0
    for item in findings:
        if not (item.operation == "POKE" and
                item.classification == "global_memory_write" and
                item.severity == "block"):
            continue
        match = _ASSIGNMENT.fullmatch(item.expression)
        if not match:
            continue
        address, value = int(match[1]), int(match[2])
        if value not in _CONTROLS[address]:
            continue
        item.severity = "info"
        item.classification = "rom_keyboard_control"
        changed += 1
    return changed
