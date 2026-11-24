# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""Source-independent, token-based selection of checked native string storage.

A self-concatenating scalar needs more than HiSoft's 255-byte default. The
capacity is a reservation, NOT a claim about the program's maximum length.
The generated runtime must check that reservation before copying. Original
Sinclair tokens, quoted bytes, DATA, REM and numeric caches stay untouched.
"""
from __future__ import annotations

import re

from size_opt import _statements

# One native scalar string's physical budget, not an inferred source limit. Larger operations
# must be checked at execution rather than silently cut.
DEFAULT_CAPACITY = 1024
ROM_WORKSPACE_BYTES = 2048


def growing_scalar_strings(program: bytes, keywords, split_lines) -> list[dict]:
    token = keywords.CODE_FOR
    if 'LET' not in token or 'REM' not in token:
        return []
    let = bytes([token['LET']])
    candidate = re.compile(rb'^\s*' + re.escape(let) +
                           rb'\s*([A-Za-z])\$\s*=\s*(.*)$', re.S)
    scalar_ref = re.compile(rb'([A-Za-z])\$(?=[^A-Za-z0-9]|$)', re.I)
    found = set()
    arrays = set()
    for _, body in split_lines(program):
        for stmt in _statements(body, token['REM']):
            if 'DIM' in token and bytes([token['DIM']]) in stmt:
                arrays.update(m[0][:1].lower() for m in re.finditer(
                    rb'[A-Za-z]\$', stmt))
            m = candidate.fullmatch(stmt)
            if m is None:
                continue
            name, expr = m[1].lower(), m[2]
            # Mask quoted bytes and Sinclair five-byte numeric caches. The literal string "A$+"
            # must not count as executable arithmetic.
            active = bytearray(expr)
            quoted = False
            i = 0
            while i < len(active):
                c = active[i]
                if c == 34:
                    quoted = not quoted
                if quoted or c == 34:
                    active[i] = 32
                elif c == 14:
                    active[i:min(i+6, len(active))] = b' ' * min(6, len(active)-i)
                    i += 6
                    continue
                i += 1
            # This selects a checked capacity; it never proves a maximum.
            if b'+' in active and any(ref[1].lower() == name for ref in
                                     scalar_ref.finditer(active)):
                found.add(name)
    return [{'variable': name.decode('ascii').upper() + '$',
             'max_chars': DEFAULT_CAPACITY,
             'bound_proof': 'native-runtime-checked-scalar-concatenation',
             'storage_is_reservation': True}
            for name in sorted(found - arrays)]


def workspace_bytes(proofs: list[dict], runtime_routes=()) -> int:
    """Select private ROM memory using HiSoft's actually emitted string RTs.

    1K covers ordinary string work; 2K is reserved for the checked growth
    path. This is a runtime capacity, not an inferred BASIC string maximum.
    """
    if any(p.get('storage_is_reservation') is True and
           p.get('bound_proof') == 'native-runtime-checked-scalar-concatenation'
           for p in proofs):
        return ROM_WORKSPACE_BYTES
    return 1024 if runtime_routes else 0
