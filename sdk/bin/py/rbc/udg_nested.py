# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""Prove fixed Spectrum UDG byte writes inside simple bounded outer loops.

This check does not approve writes outside the 21 glyphs, calculated memory
addresses, or loops whose index can be changed by user statements or jumps.
"""
from __future__ import annotations

import re
from udg_bounds import _line_text

_FOR = re.compile(r'\bFOR\s+([A-Za-z])\s*=\s*0\s*TO\s*7\b', re.I)
_NEXT = re.compile(r'\bNEXT\s+([A-Za-z])\b', re.I)
_ADDRESS = re.compile(r'^USR\s+"\{(9[0-9A-F]|A[0-4])\}"\s*\+\s*([A-Za-z])\s*,', re.I)
_BRANCH = re.compile(r'\b(?:GO\s*TO|GO\s*SUB|RUN|RETURN|STOP|CONTINUE)\b', re.I)
_TARGET = re.compile(r'\bGO\s*(?:TO|SUB)\s+(\d+)\b', re.I)


def allow_nested_glyph_writes(lines, token_names, findings):
    decoded = [(number, _line_text(body, token_names)) for number, body in lines]
    incoming = {int(m[1]) for _, text in decoded for m in _TARGET.finditer(text)}
    approved = 0
    for item in findings:
        if (item.operation != 'POKE' or item.classification != 'unbounded_memory_write'
                or item.severity != 'block'):
            continue
        match = _ADDRESS.match(item.expression)
        if not match:
            continue
        glyph = int(match[1], 16)
        variable = match[2].lower()
        if not 0x90 <= glyph <= 0xA4:
            continue
        position = next((i for i, (number, _) in enumerate(decoded) if number == item.line), -1)
        if position < 0:
            continue
        for i in range(position, -1, -1):
            row = decoded[i][1]
            begins = [m for m in _FOR.finditer(row) if m[1].lower() == variable]
            if not begins:
                continue
            # The POKE must be inside this loop, before its own NEXT.
            remaining = decoded[i:]
            ending = next((k for k, (_, text) in enumerate(remaining)
                           if any(m[1].lower() == variable for m in _NEXT.finditer(text))), -1)
            if ending < 0 or position > i + ending or ending > 25:
                break
            span = decoded[i:i+ending+1]
            if any(n in incoming for n, _ in span[1:]):
                break
            if any(_BRANCH.search(text) for _, text in span):
                break
            # The loop index is controlled only by its FOR/NEXT, not by LET, READ, INPUT, or
            # a second FOR reusing the same name.
            unsafe = False
            for j, (_, text) in enumerate(span):
                if re.search(r'\bLET\s+'+variable+r'\s*=', text, re.I):
                    unsafe = True
                if re.search(r'\b(?:READ|INPUT)\s+[^:]*\b'+variable+r'\b', text, re.I):
                    unsafe = True
                if j and any(m[1].lower() == variable for m in _FOR.finditer(text)):
                    unsafe = True
            if not unsafe:
                item.severity = 'info'
                item.classification = 'bounded_process_udg_write'
                approved += 1
            break
    return approved