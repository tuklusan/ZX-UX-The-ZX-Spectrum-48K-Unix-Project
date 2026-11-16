# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""Prove the bounded custom-glyph writes used in original BASIC listings.

Only matched, straight-line FOR/POKE/NEXT blocks within the process's
21 glyphs are accepted. This does not grant general POKE access.
"""
from __future__ import annotations

import re
def _line_text(body, token_names):
    """Read token names without mistaking quoted bytes or hidden numbers."""
    out = []
    quoted = False
    i = 0
    while i < len(body):
        c = body[i]
        if c == 14 and not quoted and i + 5 < len(body):
            i += 6
            continue
        if not quoted and c == 234:
            break
        if c == 34:
            quoted = not quoted
            out.append('"')
        elif quoted:
            out.append(chr(c) if 32 <= c <= 126 else '{%02X}' % c)
        elif c in token_names:
            out.append(' ' + token_names[c].upper() + ' ')
        elif 32 <= c <= 126:
            out.append(chr(c))
        i += 1
    return ''.join(out)


_FOR_POINTER = re.compile(
    r'\bFOR\s+([a-z])\s*=\s*USR\s*\(?\s*"([a-u])"\s*\)?'
    r'\s*TO\s*\(?\s*USR\s*\(?\s*"([a-u])"\s*\)?\s*\+\s*(\d+)\s*\)?', re.I)
_FOR_OFFSET = re.compile(r'\bFOR\s+([a-z])\s*=\s*0\s*TO\s*7\b', re.I)
_POINTER = re.compile(r'^\s*([a-z])\s*,', re.I)
_OFFSET = re.compile(
    r'^\s*USR\s*\(?\s*"([a-u])"\s*\)?\s*\+\s*([a-z])\s*,', re.I)
_FLOW = re.compile(r'\b(?:GO\s*TO|GO\s*SUB|RETURN|STOP|RUN|CONTINUE|NEXT)\b', re.I)
_GOTO = re.compile(r'\bGO\s*(?:TO|SUB)\s+(\d+)\b', re.I)
_NEXT = re.compile(r'\bNEXT\s+([a-z])\b', re.I)


def allow_bounded_udg_loops(lines, token_names, findings):
    """Downgrade only static, straight-line process-UDG writes to info.

    A block requires a precise FOR, a POKE on the same or next three
    program lines, a matching NEXT, and no outside jump into the body.
    The glyph pointer and final byte are checked against the 21-glyph
    process-local range. No raw/system addresses are accepted.
    """
    decoded = [(num, _line_text(body, token_names)) for num, body in lines]
    targets = set()
    for _, text in decoded:
        targets.update(int(m.group(1)) for m in _GOTO.finditer(text))
    allowed = set()
    # A literal glyph plus a fixed byte offset is safe even outside a FOR.
    literal = re.compile(r'^USR\s*\(\s*"([a-u])"\s*\)\s*'
                         r'(?:\+\s*(\d+))?\s*,', re.I)
    for item in findings:
        if item.operation != 'POKE' or item.classification != 'unbounded_memory_write':
            continue
        match = literal.match(item.expression.strip())
        if match and (match.group(2) is None or int(match.group(2)) <= 7):
            allowed.add(id(item))
    for start, (line, text) in enumerate(decoded):
        candidates = []
        for match in _FOR_POINTER.finditer(text):
            var, first, last, tail = match.groups()
            low, high, offset = ord(first.lower())-97, ord(last.lower())-97, int(tail)
            if low <= high and high * 8 + offset < 21 * 8:
                candidates.append((var.lower(), 'pointer'))
        for match in _FOR_OFFSET.finditer(text):
            candidates.append((match.group(1).lower(), 'offset'))
        for variable, kind in candidates:
            end = None
            for j in range(start, min(len(decoded), start + 26)):
                if j > start and _FOR_POINTER.search(decoded[j][1]):
                    break
                if j > start and _FOR_OFFSET.search(decoded[j][1]):
                    break
                if _NEXT.search(decoded[j][1]):
                    matching = [m for m in _NEXT.finditer(decoded[j][1])
                                if m.group(1).lower() == variable]
                    if matching:
                        end = j
                    break
            if end is None:
                continue
            span = decoded[start:end+1]
            # No entry directly into a loop body from elsewhere. Line-numbered control
            # transfers to its FOR header are fine.
            if any(n in targets for n, _ in span[1:]):
                continue
            # No conditional branches or early exits inside these simple loops.
            if any(_FLOW.search(t) and (i != len(span)-1 or re.search(
                    r'\b(?:GO\s*TO|GO\s*SUB|RETURN|STOP|RUN|CONTINUE)\b', t, re.I))
                   for i, (_, t) in enumerate(span)):
                continue
            if any(re.search(r'\bLET\s+' + re.escape(variable) + r'\b\s*=', t, re.I)
                   for _, t in span):
                continue
            # Input or READ must not overwrite the address variable.
            changing_address = False
            for _, statement in span:
                for part in statement.split(':'):
                    if re.search(r'\bINPUT\b', part, re.I):
                        changing_address = True
                    rd = re.search(r'\bREAD\b', part, re.I)
                    if rd and re.search(r'\b' + re.escape(variable) + r'\b',
                                        part[rd.end():], re.I):
                        changing_address = True
            if changing_address:
                continue
            for item in findings:
                if item.operation != 'POKE' or item.classification != 'unbounded_memory_write':
                    continue
                if item.line not in [n for n, _ in span]:
                    continue
                addr = item.expression.strip()
                if kind == 'pointer' and _POINTER.match(addr) and _POINTER.match(addr).group(1).lower() == variable:
                    allowed.add(id(item))
                elif kind == 'offset':
                    m = _OFFSET.match(addr)
                    if m and m.group(2).lower() == variable:
                        allowed.add(id(item))
    paired_pointers = set()
    for item in findings:
        if id(item) in allowed:
            item.severity = 'info'
            item.classification = 'bounded_process_udg_write'
            expr = item.expression.strip()
            if re.match(r'^USR\b', expr, re.I):
                paired_pointers.add((item.line, expr[3:].strip()))
    # A parenthesized glyph address can look like a numeric USR call in the old scanner.
    # Accept it only when it belongs to a proven POKE.
    glyph_address = re.compile(
        r'^\(\s*"[a-u]"\s*\)\s*(?:\+\s*(?:[a-z]|\d+))?\s*,', re.I)
    for item in findings:
        if (item.operation == 'USR' and
                item.classification == 'raw_machine_code_address' and
                (item.line, item.expression.strip()) in paired_pointers and
                glyph_address.match(item.expression)):
            item.severity = 'info'
            item.classification = 'process_udg_pointer'
    return len(allowed)