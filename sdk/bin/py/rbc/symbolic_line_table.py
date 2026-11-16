# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""Preserve the original HiSoft line lookup table with symbolic references.

The fixed compiler's line, address and sentinel emitters identify these data
words independently of the bytes in a linked executable. Each table address
is verified at three load bases before use as a native assembler symbol.
"""
from __future__ import annotations

from dataclasses import replace
import re


class LineTableError(ValueError):
    """Original BASIC line table has an unverified data/address boundary."""


_LINE_SITE = 'emit_line_table:2469'
_ADDRESS_SITE = 'emit_line_table:2474'
_END_SITE = 'emit_line_table:2475'
_INT = re.compile(r'\((\d+),\)\Z')


def _number(event, site: str, kind: str, *, width=2):
    if (event.kind != kind or event.source_site != site or
            not isinstance(event.data, bytes) or len(event.data) != width or
            not isinstance(event.position, int)):
        raise LineTableError('line table producer kind, site or extent differs')
    match = _INT.fullmatch(event.source)
    if not match:
        raise LineTableError('original line table number lacks source value')
    return int(match.group(1))


def bind_original_line_table(events, image: bytes, base: int, text_end: int, bss: int):
    """Turn original line/address sources into protected words and references."""
    if (not isinstance(image, bytes) or type(base) is not int or
            type(text_end) is not int or type(bss) is not int or
            not 0 <= base <= 65535 or not 0 <= text_end <= len(image) or
            not 0 <= bss <= 65535):
        raise LineTableError('invalid native line-table storage')
    items = tuple(events)
    result = []
    index = 0
    rows = 0
    completed = 0
    while index < len(items):
        event = items[index]
        if event.source_site not in (_LINE_SITE, _ADDRESS_SITE, _END_SITE):
            result.append(event)
            index += 1
            continue
        if completed:
            raise LineTableError('original line table has unexpected extra source')
        start = event.position
        table_begin = len(result)
        cursor = start
        while index < len(items) and items[index].source_site == _LINE_SITE:
            line_event = items[index]
            number = _number(line_event, _LINE_SITE, 'word')
            if (number > 65535 or line_event.position != cursor or
                    line_event.data != number.to_bytes(2, 'little')):
                raise LineTableError('original BASIC line word differs from source')
            if index + 1 >= len(items):
                raise LineTableError('line table address source is missing')
            reference = items[index + 1]
            offset = _number(reference, _ADDRESS_SITE, 'relocation')
            if (reference.position != cursor + 2 or
                    reference.symbol_offset != offset or
                    not 0 <= offset < len(image) + bss or
                    reference.data != ((base + offset) & 65535).to_bytes(2, 'little')):
                raise LineTableError('line address is not verified for this native base')
            result.append(replace(line_event, kind='inline-data',
                                  source='protected:basic-line',
                                  data=line_event.data))
            result.append(replace(reference, kind='table-relocated',
                                  source='dw nn'))
            cursor += 4
            index += 2
            rows += 1
        if index >= len(items):
            raise LineTableError('line table is missing its source sentinel')
        marker = items[index]
        terminal = _number(marker, _END_SITE, 'word')
        if (terminal != 65535 or marker.position != cursor or
                marker.data != b'\xff\xff' or cursor + 2 > text_end or
                image[start:cursor + 2] !=
                    b''.join(part.data for part in result[table_begin:]) + b'\xff\xff'):
            raise LineTableError('line table marker or protected bytes differ')
        result.append(replace(marker, kind='inline-data',
                              source='protected:line-table-end'))
        index += 1
        completed += 1
    return tuple(result), {'table_count': completed, 'line_pairs': rows,
                           'protected_table_bytes': rows * 4 + 2 * completed,
                           'address_words': rows}


def bind_three_line_tables(groups, images, bases, text_ends, bss_sizes):
    """Reject table changes between independent source compiler passes."""
    if any(len(x) != 3 for x in (groups, images, bases, text_ends, bss_sizes)):
        raise LineTableError('three original native line tables required')
    builds = [bind_original_line_table(*items) for items in
              zip(groups, images, bases, text_ends, bss_sizes)]
    def signature(group):
        return tuple((e.position, e.kind, e.source, e.symbol_offset,
                      None if e.kind == 'table-relocated' else e.data)
                     for e in group if e.kind == 'table-relocated' or
                     e.source_site in (_LINE_SITE, _ADDRESS_SITE, _END_SITE))
    first = signature(builds[0][0])
    if any(signature(group) != first or report != builds[0][1]
           for group, report in builds[1:]):
        raise LineTableError('line table source changed across compiler bases')
    return tuple(group for group, _ in builds), builds[0][1]
