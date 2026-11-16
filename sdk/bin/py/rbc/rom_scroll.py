# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""Recognize only the Spectrum 48K ROM single-line scroll entry.

An archived program uses USR 3280 (0x0CD0) to scroll the bitmap. This is
ROM, rather than an arbitrary machine-code address in shared RAM. The memory
review exemption applies to exactly this decimal literal, never an expression
or another USR address. Native execution is still required independently.
"""
import re

_ROM_SCROLL = re.compile(r'^\s*3280\s*$')


def allow_rom_screen_scroll(findings):
    accepted = 0
    for item in findings:
        if (item.operation == 'USR' and
                item.classification == 'raw_machine_code_address' and
                item.severity == 'block' and
                _ROM_SCROLL.fullmatch(item.expression)):
            item.classification = 'rom_screen_scroll'
            item.severity = 'info'
            accepted += 1
    return accepted