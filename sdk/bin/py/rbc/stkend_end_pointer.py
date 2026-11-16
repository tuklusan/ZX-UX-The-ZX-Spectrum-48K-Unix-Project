# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""Narrow original HiSoft STKEND boundary witness for zero-BSS STOP.

A position one past the loaded image is not writable process storage.
The sole admitted use is the original, independently traced `LD HL,end`
followed immediately by `LD (STKEND),HL`. Do not admit indirect loads,
BSS references, or arbitrary one-past-end relocation targets.
"""
from __future__ import annotations


def original_stkend_end_marker(events, image, base, bss, site, target):
    """Check the exact original emitter ownership of the sentinel address."""
    if (type(base) is not int or type(bss) is not int or bss != 0 or
            type(site) is not int or type(target) is not int or
            target != len(image) or site != 4 or len(image) < 9 or
            not 0 <= base <= 65535 or base + target > 65535):
        return False
    # Require three distinct, *original source* events, not decoded bytes.
    lead = [e for e in events if e.position == site - 1 and
            e.kind == 'opcode' and e.source.strip().lower() == 'ld hl,nn' and
            e.data == b'\x21']
    ptr = [e for e in events if e.position == site and
           e.kind == 'relocation' and e.symbol_offset == target and
           e.data == (base + target).to_bytes(2, 'little')]
    store = [e for e in events if e.position == site + 2 and
             e.kind == 'instruction' and
             e.source.strip().lower() == 'ld ($5c6c),hl' and
             e.data == b'\x22\x6c\x5c']
    return (len(lead) == len(ptr) == len(store) == 1 and
            image[site - 1:site + 5] ==
            lead[0].data + ptr[0].data + store[0].data)
