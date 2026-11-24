# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""Render tokenized Spectrum BASIC into unambiguous numbered ASCII input.

Executable Sinclair tokens are spelled from the ROM token table, while all
other bytes use BAS2TAP's {HH} escape. The byte escapes keep spaces inside
remarks and strings and keep exact numeric metadata unchanged. No source
keyword is inferred by examining ordinary characters.
"""

class LosslessConversionError(ValueError):
    pass


def to_ascii_listing(lines, token_names):
    if not token_names:
        raise LosslessConversionError('missing original Sinclair token table')
    output = []
    for number, body in lines:
        if not isinstance(number, int) or not 0 <= number <= 9999:
            raise LosslessConversionError(f'BASIC line number {number!r} outside 0..9999')
        if not body or body[-1] != 13:
            raise LosslessConversionError(f'Line {number}: missing end-of-line marker')
        quoted = rem = False
        text = []
        i = 0
        raw = body[:-1]
        # Leading blanks before the first executable keyword are whitespace only; BAS2TAP
        # consumes them before reading a line's statement. Keep every byte *after* the
        # token, especially in REM and strings.
        if raw.strip(b' ') and raw.lstrip(b' ')[0] in token_names:
            raw = raw.lstrip(b' ')
        # A line containing only blanks is a legitimate nonexecuting record. Preserve its
        # line number; the semantic comparator verifies that only nonexecuting whitespace
        # differs from the tape record. Spaces alone must not change the program.
        if not raw.strip(b' '):
            output.append(str(number) + ' ')
            continue
        while i < len(raw):
            c = raw[i]
            if not quoted and not rem and c == 14:
                if i + 6 > len(raw):
                    raise LosslessConversionError(f'Line {number}: incomplete Sinclair numeric cache')
                text.extend('{%02X}' % b for b in raw[i:i + 6])
                i += 6
                continue
            if not rem and c == 34:
                quoted = not quoted
                text.append('"')
            elif not quoted and not rem and c == 58:
                text.append(':')
            elif not quoted and not rem and c in (40, 41):
                text.append(chr(c))
            elif not quoted and not rem and c in token_names:
                token = token_names[c].strip()
                if not token:
                    raise LosslessConversionError(f'Line {number}: empty keyword for {c:02X}')
                text.append(token + ' ')
                if c == 0xea:
                    rem = True
            else:
                text.append('{%02X}' % c)
            i += 1
        if quoted:
            raise LosslessConversionError(f'Line {number}: unmatched quoted string')
        output.append(str(number) + ' ' + ''.join(text))
    if not output:
        raise LosslessConversionError('empty original BASIC program')
    return '\n'.join(output) + '\n'

def confirm_roundtrip(original, recreated, split_lines):
    """Demand an exact byte match including numeric caches and quoted bytes."""
    if original == recreated:
        return
    a, b = split_lines(original), split_lines(recreated)
    for position in range(max(len(a), len(b))):
        if position >= len(a) or position >= len(b):
            raise LosslessConversionError('BASIC line count changed during token round-trip')
        n, original_body = a[position]
        m, recreated_body = b[position]
        if n != m:
            raise LosslessConversionError(f'BASIC line order changed: original {n}, round-trip {m}')
        if original_body != recreated_body:
            offset = next((i for i in range(min(len(original_body), len(recreated_body)))
                           if original_body[i] != recreated_body[i]),
                          min(len(original_body), len(recreated_body)))
            raise LosslessConversionError(
                f'Line {n}: token round-trip differs at byte {offset}; '
                f'original {original_body[offset:offset+5].hex().upper()}, '
                f'converted {recreated_body[offset:offset+5].hex().upper()}')
    raise LosslessConversionError('BASIC bytes changed during token round-trip')
