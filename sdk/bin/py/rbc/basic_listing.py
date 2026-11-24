# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""Strict numbered ASCII 48K BASIC adapter using the verified BAS2TAP port.

Only upstream BAS2TAP emits Sinclair bytes. No pyhsb tokenizer or numerical
metadata writer is permitted on the external BASIC source path.
"""
from __future__ import annotations
import ast
from fractions import Fraction
import re
from bas2tap import BAS2TAPError, _prepare_line, tokenize_line

UPSTREAM_REVISION = '0ddb25e4c38ce4ccb5a43e85fb57e683bd274f59'
LINE = re.compile(r'[ \t]*([0-9]+)(?:(?:[ \t]+(.*))|(:.*))?')


def reconstruct_screen_wraps(text: str) -> str:
    """Join only demonstrable 32-column Spectrum screen listing wraps.

    This produces a transient compiler input; archived BAS/TZX bytes stay
    untouched. Never infer a lost character or repair a non-screen gap.
    """
    physical = text.splitlines()
    rows = []
    last_number = -1
    current = None
    previous_physical_width = 0
    changed = False
    for raw in physical:
        m = LINE.fullmatch(raw)
        number = int(m.group(1)) if m and int(m.group(1)) <= 9999 else None
        # A lone number following a full-width GO TO target is still part of that target
        # (e.g. `... GO TO 23` followed by `10`).
        numeric_tail = (number is not None and raw.strip().isdigit() and
                        previous_physical_width in (31, 32) and
                        current is not None and
                        bool(re.search(r'(?i)\b(?:GO\s+TO|GO\s+SUB|THEN)\s*\d*$', current)))
        if number is not None and number > last_number and not numeric_tail:
            if current is not None:
                rows.append(current)
            current, last_number = raw, number
        else:
            open_quote = current is not None and current.count('"') % 2 == 1
            if current is None or not (previous_physical_width in (31, 32) or open_quote):
                raise ValueError('cannot reconstruct unproved BASIC line continuation')
            current += raw
            changed = True
        previous_physical_width = len(raw)
    if current is not None:
        rows.append(current)
    if not changed:
        return text
    result = '\n'.join(rows) + ('\n' if text.endswith(('\n','\r')) else '')
    # A reconstruction is acceptable only when the strict Sinclair tokenizer can verify
    # every resulting numbered line, in original source order.
    encode_strict_listing(result)
    return result


def split_numbered_line(raw: str) -> tuple[int, str]:
    match = LINE.fullmatch(raw)
    if not match:
        raise ValueError('expected numbered ASCII Sinclair BASIC')
    n = int(match.group(1))
    if n > 9999:
        raise ValueError('BASIC line number outside 0..9999')
    return n, next((part for part in match.groups()[1:] if part is not None), '')


def _active_code(body: str) -> str:
    """Mask strings, REM and DATA without changing source positions."""
    chars = list(body)
    quoted = data = False
    pos = 0
    while pos < len(body):
        c = body[pos]
        boundary = pos == 0 or not (body[pos - 1].isalnum() or body[pos - 1] == '$')
        if (not quoted and boundary and body[pos:pos+3].upper() == 'REM' and
                (pos + 3 == len(body) or not (body[pos + 3].isalnum() or body[pos + 3] == '$'))):
            chars[pos:] = ' ' * (len(body) - pos)
            break
        if (not quoted and boundary and body[pos:pos+4].upper() == 'DATA' and
                (pos + 4 == len(body) or not (body[pos + 4].isalnum() or body[pos + 4] == '$'))):
            data = True
        if c == '"':
            quoted = not quoted
        elif c == ':' and not quoted:
            data = False
        if quoted or data or c == '"':
            chars[pos] = ' '
        pos += 1
    return ''.join(chars)


def _require_original_keyword_boundaries(number: int, body: str) -> None:
    """Reject FOR 1TO10 rather than manufacture a missing word boundary."""
    active = _active_code(body)
    for match in re.finditer(r'\bFOR\s+[A-Za-z]\s*=', active, re.I):
        tail = active[match.end():].split(':', 1)[0]
        if re.search(r'(?<=\d)TO(?=\d)', tail, re.I):
            raise ValueError(f'Line {number}: missing whitespace before TO in FOR statement')


def _fix_bin_cache(data: bytes, number: int) -> bytes:
    """Keep BIN numeric metadata consistent with the visible binary digits."""
    out = bytearray(data)
    quoted = False
    p = 0
    while p < len(out):
        c = out[p]
        if c == 34:
            quoted = not quoted
        elif not quoted and c == 0xEA:  # REM: remaining bytes are inert
            break
        elif not quoted and c == 14:  # previous numeric metadata
            if p + 6 > len(out):
                raise ValueError(f'Line {number}: incomplete numeric cache')
            p += 6
            continue
        elif not quoted and c == 0xC4:  # executable BIN token
            start = p + 1
            end = start
            while end < len(out) and out[end] in (48, 49):
                end += 1
            if end != start and end + 6 <= len(out) and out[end] == 14:
                value = int(out[start:end].decode('ascii'), 2)
                if value > 65535:
                    raise ValueError(f'Line {number}: BIN number exceeds 65535')
                out[end + 1:end + 6] = bytes((0, 0, value & 255, value >> 8, 0))
                p = end + 6
                continue
        p += 1
    return bytes(out)



def _print_at_integer(expr: bytes) -> int | None:
    """Prove only small, pure numeric constants; never guess variable values."""
    try:
        text = expr.strip().decode('ascii')
        if len(text) > 64 or not text:
            return None
        tree = ast.parse(text, mode='eval')

        def number(node):
            if isinstance(node, ast.Constant) and type(node.value) in (int, float):
                # str(float) is sufficient for recognizing integer results; it cannot manufacture
                # a value from a BASIC variable.
                return Fraction(str(node.value))
            if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
                value = number(node.operand)
                return value if isinstance(node.op, ast.UAdd) else -value
            if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)):
                left, right = number(node.left), number(node.right)
                if isinstance(node.op, ast.Add):
                    value = left + right
                elif isinstance(node.op, ast.Sub):
                    value = left - right
                elif isinstance(node.op, ast.Mult):
                    value = left * right
                else:
                    value = left / right
                if abs(value.numerator) > 100000000 or value.denominator > 100000000:
                    raise ValueError('constant too large to prove')
                return value
            raise ValueError('not a static numeric expression')

        value = number(tree.body)
        return int(value) if value.denominator == 1 else None
    except (ValueError, SyntaxError, ZeroDivisionError, OverflowError,
            UnicodeError, RecursionError):
        return None


def _check_print_at_bounds(number: int, tokenized: bytes) -> None:
    """Reject provably invalid PRINT AT coordinates, leaving dynamic ones alone.

    Uses original Sinclair keyword bytes (PRINT=F5, AT=AC). Quoted, REM,
    DATA and five-byte Sinclair numeric caches are not executable tokens.
    The 48K ROM's PRINT-AT limits are rows 0..21 and columns 0..31.
    """
    active_print = in_string = in_data = False
    p = 0
    while p < len(tokenized):
        byte = tokenized[p]
        if byte == 34:
            in_string = not in_string
        elif not in_string:
            if byte == 14:
                if p + 6 > len(tokenized):
                    raise ValueError(f'Line {number}: truncated Sinclair numeric cache')
                p += 6
                continue
            if byte == 0xea and not in_data:  # REM
                break
            if byte == 58:  # statement separator
                active_print = in_data = False
            elif byte == 0xe4:  # DATA
                in_data = True
                active_print = False
            elif not in_data:
                if byte == 0xf5:  # PRINT, including IF ... THEN PRINT
                    active_print = True
                elif byte == 0xac and active_print:  # actual PRINT AT token
                    # Strip Sinclair's hidden number encoding before parsing any visible constant.
                    # Do not interpret string data.
                    start = p + 1
                    parts = [bytearray(), bytearray()]
                    part = 0
                    depth = 0
                    i = start
                    while i < len(tokenized):
                        ch = tokenized[i]
                        if ch == 14:
                            if i + 6 > len(tokenized):
                                raise ValueError(f'Line {number}: truncated Sinclair numeric cache')
                            i += 6
                            continue
                        if ch == 40:
                            depth += 1
                        elif ch == 41:
                            depth -= 1
                        if depth == 0 and ch == 44 and part == 0:
                            part = 1
                            i += 1
                            continue
                        if (part and depth == 0 and ch in (13, 34, 58, 59, 0xac)
                                or ch >= 0xA3):
                            break
                        if ch == 13 or ch == 58:
                            break
                        parts[part].append(ch)
                        i += 1
                    if part:
                        for axis, (raw, maximum) in enumerate(zip(parts, (21, 31))):
                            value = _print_at_integer(bytes(raw))
                            if value is not None and not 0 <= value <= maximum:
                                name = 'row' if axis == 0 else 'column'
                                raise ValueError(
                                    f'RBC E_PRINT_AT_RANGE: Line {number}: '
                                    f'PRINT AT {name} {value} outside 0..{maximum} '
                                    '(Spectrum 48K ROM screen)')
        p += 1

def encode_strict_listing(listing: str) -> bytes:
    """Do not re-tokenize, clean, rewrite, or insert Spectrum line text."""
    if not listing.isascii():
        raise ValueError('non-ASCII Sinclair BASIC is unsupported')
    lines = listing.split('\n')
    seen = -1
    count = 0
    for index, raw in enumerate(lines, 1):
        if not raw.strip():
            continue
        try:
            number, body = split_numbered_line(raw[:-1] if raw.endswith('\r') else raw)
        except ValueError as exc:
            raise ValueError(f'ASCII line {index}: {exc}: {raw[:48]!r}') from exc
        if number <= seen:
            raise ValueError(f'line {index}: duplicate or unordered BASIC line {number}')
        _require_original_keyword_boundaries(number, body)
        if not body.strip() and count == 0:
            raise ValueError(f'line {index}: empty first BASIC statement')
        seen = number
        count += 1
    if not count:
        raise ValueError('empty BASIC listing')
    # Spectrum records may exceed the C converter input buffer after ASCII control
    # escapes.  The Python version can tokenize the entire source. Use upstream's
    # preparer and lexer for every numbered line, without introducing an alternative
    # tokenizer or changing Sinclair code bytes.
    output = bytearray()
    mode = {'value': -1}
    seen = -1
    for index, raw in enumerate(lines, 1):
        if index == len(lines) and not raw:
            continue
        if raw.endswith('\r'):
            raw = raw[:-1]
        try:
            row = _prepare_line(raw, index, first=(seen == -1))
            if row is None:
                continue
            n, body = row
            if n <= seen:
                raise BAS2TAPError(f'Line {n}: duplicate or unordered BASIC line')
            data = _fix_bin_cache(tokenize_line(body, line_number=n, _mode=mode), n)
            _check_print_at_bounds(n, data)
            output.extend(n.to_bytes(2, 'big'))
            output.extend(len(data).to_bytes(2, 'little'))
            output.extend(data)
            if len(output) > 41500:
                raise BAS2TAPError(f'Line {n}: program exceeds original 41500-byte limit')
            seen = n
        except BAS2TAPError as exc:
            raise ValueError(str(exc)) from exc
    return bytes(output)