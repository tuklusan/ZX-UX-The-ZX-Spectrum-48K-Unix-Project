# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""Resolve original BASIC RESTORE references to their next DATA line.

Sinclair BASIC seeks the first DATA statement on or after the supplied line.
HiSoft's compiler requires a line containing DATA. Only literal RESTORE
references in the temporary token program are adjusted.
"""
from bisect import bisect_left


def _contains_data(body, data_token, rem_token):
    quoted = False
    index = 0
    while index < len(body):
        c = body[index]
        if c == 34:
            quoted = not quoted
        elif not quoted and c == 14 and index + 6 <= len(body):
            index += 6
            continue
        elif not quoted and c == rem_token:
            return False
        elif not quoted and c == data_token:
            return True
        index += 1
    return False


def resolve_restores(program, keywords, fp):
    """Return tokenized program and (line, old, new) literal corrections."""
    import tap
    import source

    lines = tap.split_lines(program)
    data_token = keywords.CODE_FOR['DATA']
    restore_token = keywords.CODE_FOR['RESTORE']
    rem_token = keywords.CODE_FOR['REM']
    data_numbers = sorted(n for n, body in lines
                          if _contains_data(body, data_token, rem_token))
    changed = []
    revised = []
    for number, body in lines:
        new = bytearray()
        pos = 0
        quoted = False
        while pos < len(body):
            c = body[pos]
            if c == 34:
                quoted = not quoted
                new.append(c)
                pos += 1
                continue
            if not quoted and c == rem_token:
                new.extend(body[pos:])
                break
            if not quoted and c == 14 and pos + 6 <= len(body):
                new.extend(body[pos:pos + 6])
                pos += 6
                continue
            if not quoted and c == restore_token:
                new.append(c)
                pos += 1
                while pos < len(body) and body[pos] == 32:
                    new.append(32)
                    pos += 1
                begin = pos
                while pos < len(body) and 48 <= body[pos] <= 57:
                    pos += 1
                digit_end = pos
                end = pos + 6 if pos + 6 <= len(body) and body[pos] == 14 else pos
                delim = end
                while delim < len(body) and body[delim] == 32:
                    delim += 1
                if begin < digit_end and (delim == len(body) or body[delim] in (13, 58)):
                    target = int(body[begin:digit_end])
                    at = bisect_left(data_numbers, target)
                    if at < len(data_numbers) and data_numbers[at] != target:
                        replacement = data_numbers[at]
                        new.extend(source.hide_numbers(str(replacement).encode('ascii'), fp))
                        new.extend(body[end:delim])
                        changed.append((number, target, replacement))
                        pos = delim
                        continue
                new.extend(body[begin:end])
                pos = end
                continue
            new.append(c)
            pos += 1
        revised.append((number, bytes(new)))
    return tap.join_lines(revised), changed