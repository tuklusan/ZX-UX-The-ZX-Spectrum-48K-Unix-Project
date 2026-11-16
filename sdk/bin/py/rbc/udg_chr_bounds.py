# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""Prove that CHR$-computed graphic writes stay in the 21 Spectrum UDG glyphs."""
from __future__ import annotations
import re
from udg_bounds import _line_text

_ADDRESS = re.compile(
    r'^USR\s+CHR\$\s*\(\s*(\d+)\s*\+\s*([A-Za-z])\s*\)\s*\+\s*([A-Za-z])\s*,', re.I)
_NESTED = re.compile(
    r'^CHR\$\s*\(\s*(\d+)\s*\+\s*([A-Za-z])\s*\)\s*\+\s*([A-Za-z])\s*,', re.I)
_LITERAL_ADDRESS = re.compile(
    r'^USR\s+CHR\$\s*\(\s*(\d+)\s*\)\s*\+\s*([A-Za-z])\s*,', re.I)
_NESTED_LITERAL = re.compile(
    r'^CHR\$\s*\(\s*(\d+)\s*\)\s*\+\s*([A-Za-z])\s*,', re.I)
_FOR = re.compile(r'\bFOR\s+([A-Za-z])\s*=\s*(\d+)\s*TO\s*(\d+)\b', re.I)
_NEXT = re.compile(r'\bNEXT\s+([A-Za-z])\b', re.I)
_BRANCH = re.compile(r'\b(?:GO\s*TO|GO\s*SUB|RETURN|STOP|RUN|CONTINUE)\b', re.I)
_DIRECT = re.compile(r'\bGO\s*(?:TO|SUB)\s+(\d+)\b', re.I)
_WRITE = re.compile(r'\b(?:LET|READ|INPUT)\s+([A-Za-z])\b', re.I)


def allow_bounded_chr_glyphs(lines, token_names, findings):
    """Approve only static range-proven glyph initialization with matching NEXTs.

    A FOR must be active before each address use and the matching NEXT must
    follow it. No branches, variable overwrites, or jumps into the body.
    The lowest/highest CHR$ and byte offsets are verified, never inferred.
    """
    rows = [(line, _line_text(body, token_names)) for line, body in lines]
    jump_targets = {int(m.group(1)) for _, text in rows for m in _DIRECT.finditer(text)}
    allowed = set()
    for entry in findings:
        if entry.operation != 'POKE' or entry.classification != 'unbounded_memory_write':
            continue
        match = _ADDRESS.match(entry.expression)
        literal = _LITERAL_ADDRESS.match(entry.expression) if not match else None
        if match:
            base, charvar, offvar = int(match[1]), match[2].lower(), match[3].lower()
            if charvar == offvar:
                continue
        elif literal:
            base, charvar, offvar = int(literal[1]), None, literal[2].lower()
        else:
            continue
        for at, (number, text) in enumerate(rows):
            if number != entry.line:
                continue
            # A proof covers a short, uninterrupted initializer only.
            before = rows[max(0, at-3):at+1]
            candidates = {}
            for n, (_, prefix) in enumerate(before):
                if n == len(before)-1:
                    prefix = prefix.split('POKE', 1)[0]
                for found in _FOR.finditer(prefix):
                    candidates[found[1].lower()] = (int(found[2]), int(found[3]), max(0, at-3) + n)
            if offvar not in candidates or (charvar is not None and charvar not in candidates):
                continue
            low, high, offset_start = candidates[offvar]
            first, last, char_start = candidates[charvar] if charvar is not None else (0, 0, offset_start)
            if not (0 <= low <= high <= 7 and first <= last and
                    144 <= base + first <= base + last <= 164):
                continue
            before_line = ''.join(v for _, v in before)
            after = rows[at:min(len(rows), at+4)]
            end = None
            nexts = []
            for j, (_, source) in enumerate(after):
                segment = source.split('POKE', 1)[1] if j == 0 else source
                nexts.extend(z[1].lower() for z in _NEXT.finditer(segment))
                if (charvar is None or charvar in nexts) and offvar in nexts:
                    end = j
                    break
            if end is None:
                continue
            span_start = min(char_start, offset_start)
            span_end = at+end
            span = rows[span_start:span_end+1]
            if any(n in jump_targets for n, _ in rows[span_start+1:span_end+1]):
                continue
            # Keep branchy handlers and loops that overwrite their indices gated.
            if any(_BRANCH.search(t) or any(w[1].lower() in {charvar, offvar}
                   for w in _WRITE.finditer(t)) for _, t in span):
                continue
            allowed.add(id(entry))
            break
    paired = set()
    for item in findings:
        if id(item) in allowed:
            item.severity = 'info'
            item.classification = 'bounded_process_udg_write'
            paired.add((item.line, item.expression.removeprefix('USR').strip()))
    for item in findings:
        if (item.operation == 'USR' and item.classification == 'raw_machine_code_address'
                and (_NESTED.match(item.expression) or _NESTED_LITERAL.match(item.expression))
                and (item.line, item.expression.strip()) in paired):
            item.severity = 'info'
            item.classification = 'process_udg_pointer'
    return len(allowed)