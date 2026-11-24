# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""Protect original HiSoft inline numeric/string payloads as typed source data.

This stage validates the two documented literal emitters in the fixed
48K compiler. It checks five-byte numbers and source-emitted text lengths. No generated Z80 byte is decoded to infer data.
"""
from __future__ import annotations

from dataclasses import replace
import re


class OriginalLiteralError(ValueError):
    """A protected source literal cannot be proved from its original writer."""


_NUMERIC_SITE = 'emit_const:511'
_STRING_SITE = 'emit_string_inline:1214'
_STRING_HEADER = 'emit_string_inline:1203'
_LITERAL_NUMBER = re.compile(r'\((\d+),\)\Z')


def protect_original_literals(events, image: bytes):
    """Return live statements with only original scalar/text bytes protected.

    Both original writers use emit_byte once per literal byte; numeric REAL
    constants are exactly five bytes, and string bytes follow a source-owned
    two-byte length. The caller must first verify rewind/patch source ownership.
    """
    if not isinstance(image, bytes):
        raise OriginalLiteralError('original literal image is not bytes')
    items = tuple(events)
    result = []
    previous = None
    index = 0
    numerical = string = 0
    while index < len(items):
        item = items[index]
        if (item.kind != 'byte' or item.source_site not in
                (_NUMERIC_SITE, _STRING_SITE)):
            result.append(item)
            previous = item
            index += 1
            continue
        site = item.source_site
        run = []
        at = item.position
        while index < len(items):
            next_item = items[index]
            if next_item.kind != 'byte' or next_item.source_site != site:
                break
            if (next_item.position != at or len(next_item.data) != 1 or
                    not isinstance(next_item.data, bytes)):
                raise OriginalLiteralError('source literal bytes are not contiguous')
            match = _LITERAL_NUMBER.fullmatch(next_item.source)
            if match is None or int(match.group(1)) != next_item.data[0]:
                raise OriginalLiteralError('source literal byte differs from original value')
            run.append(next_item)
            at += 1
            index += 1
        start = run[0].position
        if not run or not 0 <= start <= at <= len(image):
            raise OriginalLiteralError('original source literal exceeds image')
        data = b''.join(item.data for item in run)
        if image[start:at] != data:
            raise OriginalLiteralError('original literal differs from compiled image')
        if site == _NUMERIC_SITE:
            if len(run) != 5:
                raise OriginalLiteralError('original numeric constant needs five bytes')
            if (previous is None or previous.kind != 'relocation' or
                    previous.position + len(previous.data) != start or
                    not result or len(result) < 2 or
                    result[-2].kind != 'opcode' or
                    result[-2].source.strip().lower() != 'call nn'):
                raise OriginalLiteralError('numeric bytes lack original stack-call source')
            numerical += 1
        else:
            if (previous is None or previous.kind != 'instruction' or
                    previous.source_site != _STRING_HEADER or
                    previous.position + len(previous.data) != start or
                    len(previous.data) != 2 or
                    previous.source.strip().lower() != f'defw {len(run)}' or
                    previous.data != len(run).to_bytes(2, 'little')):
                raise OriginalLiteralError('original inline string length is unproved')
            string += 1
        result.append(replace(run[0], kind='inline-data', source=f'protected:{site}',
                              data=data))
        previous = result[-1]
    return tuple(result), {'numeric_literals': numerical,
                           'string_literals': string,
                           'protected_literal_bytes': sum(len(e.data) for e in result
                               if e.kind == 'inline-data' and
                               e.source_site in (_NUMERIC_SITE, _STRING_SITE))}


def protect_three_original_literals(groups, images):
    """Require stable literal identity at all three independent HiSoft bases."""
    if len(groups) != 3 or len(images) != 3:
        raise OriginalLiteralError('three original compiler passes required')
    builds = [protect_original_literals(g, image)
              for g, image in zip(groups, images)]
    first = tuple((e.position, e.kind, e.source, e.data)
                  for e in builds[0][0] if e.kind == 'inline-data' and
                  e.source_site in (_NUMERIC_SITE, _STRING_SITE))
    if any(tuple((e.position, e.kind, e.source, e.data) for e in group
                 if e.kind == 'inline-data' and
                 e.source_site in (_NUMERIC_SITE, _STRING_SITE)) != first
           for group, _ in builds[1:]):
        raise OriginalLiteralError('original literal sources differ across native bases')
    return tuple(group for group, _ in builds), builds[0][1]
