#!/usr/bin/env python3
# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""Pure-Python BAS2TAP 2.6 BASIC tokenizer and TAP encoder.

Ported from Martijn van der Heide's BAS2TAP 2.6 (bas2tap.c, 2013), in
https://github.com/tuklusan/bas2tap . GPL-2.0-or-later, see LICENSE.

Converts numbered ASCII Spectrum BASIC listings to native tokenized BASIC and
Spectrum TAP blocks. No compiler, third-party Python module, or Javascript is
needed. The separate C syntax checker is NOT implemented by this module;
clients such as RBC should validate tokens with the actual Spectrum ROM.
"""
from __future__ import annotations

import argparse
import math
import re
import sys
from pathlib import Path
from collections.abc import Callable

# The exact Sinclair token order from the TokenMap[0xA3..0xFF] in bas2tap.c. The rubber-key machine calls the shots.
TOKEN_WORDS = ("SPECTRUM|PLAY|RND|INKEY$|PI|FN|POINT|SCREEN$|ATTR|AT|TAB|"
               "VAL$|CODE|VAL|LEN|SIN|COS|TAN|ASN|ACS|ATN|LN|EXP|INT|SQR|SGN|"
               "ABS|PEEK|IN|USR|STR$|CHR$|NOT|BIN|OR|AND|<=|>=|<>|LINE|THEN|"
               "TO|STEP|DEF FN|CAT|FORMAT|MOVE|ERASE|OPEN #|CLOSE #|MERGE|"
               "VERIFY|BEEP|CIRCLE|INK|PAPER|FLASH|BRIGHT|INVERSE|OVER|OUT|"
               "LPRINT|LLIST|STOP|READ|DATA|RESTORE|NEW|BORDER|CONTINUE|DIM|"
               "REM|FOR|GO TO|GO SUB|INPUT|LOAD|LIST|LET|PAUSE|NEXT|POKE|"
               "PRINT|PLOT|RUN|SAVE|RANDOMIZE|IF|CLS|DRAW|CLEAR|RETURN|COPY").split('|')
TOKENS = {i + 0xA3: word for i, word in enumerate(TOKEN_WORDS)}
assert len(TOKENS) == 93 and TOKENS[0xCB] == 'THEN' and TOKENS[0xEA] == 'REM'
MATCH_ORDER = sorted(TOKENS.items(), key=lambda item: (-len(item[1]), item[0]))
# Original TokenMap's TokenType values. Types 1 and 2 are statements; type 1
# is *not* allowed as an expression token.
KEYWORDS = set(range(0xCE, 0x100))
COLORS = {0xD9, 0xDA, 0xDB, 0xDC, 0xDD, 0xDE}
COLORS.add(0xE4)   # DATA
EXPR_ONLY = set(range(0xA5, 0xCE))
EXPR_ONLY.discard(0xC4)  # BIN is a numeric introducer, not a keyword
CONTROL = {'INK': 0x10, 'PAPER': 0x11, 'FLASH': 0x12,
           'BRIGHT': 0x13, 'INVERSE': 0x14, 'OVER': 0x15,
           'AT': 0x16, 'TAB': 0x17}
LINE_NO = re.compile(r' *([0-9]+) *')
HEX = set('0123456789abcdefABCDEF')


class BAS2TAPError(ValueError):
    """Rejected input includes the BASIC line number when available."""


def _float_cache(value: float, number: int) -> bytes:
    """The original HandleNumbers' five-byte Sinclair numeric cache."""
    if not math.isfinite(value):
        raise BAS2TAPError(f'Line {number}: nonfinite number')
    if value == math.floor(value) and -65536 <= value < 65536:
        n = int(value)
        if n < 0:
            n = (n + 65536) & 0xffff
        return bytes((14, 0, 0, n & 255, (n >> 8) & 255, 0))
    if value == 0:
        return bytes((14, 0, 0, 0, 0, 0))
    # C uses log(value) / log(2.0), not log2(). The last bit matters near powers
    # of two on some libm implementations.
    exponent = math.floor(math.log(abs(value)) / math.log(2.0))
    if not (-129 <= exponent <= 126):
        raise BAS2TAPError(f'Line {number}: number outside Spectrum range')
    mantissa = math.floor((abs(value) / 2 ** exponent - 1.0) * 2147483648.0 + 0.5)
    return bytes((14, (exponent + 0x81) & 255,
                  (mantissa >> 24 & 0x7f) | (0x80 if value < 0 else 0),
                  mantissa >> 16 & 255, mantissa >> 8 & 255, mantissa & 255))


def _number_at(text: str, pos: int, line_number: int) -> tuple[bytes, int]:
    """Translate HandleNumbers exactly: decimal division and optional E sign.

    BAS2TAP's C parser accepts a bare decimal point, '1E', and '1E+'.
    Decimal fractions are accumulated a digit at a time; using float(text)
    would round differently and silently change 48K numeric caches.
    """
    start = pos
    value = 0.0
    while pos < len(text) and '0' <= text[pos] <= '9':
        value = value * 10.0 + (ord(text[pos]) - 48)
        pos += 1
    if pos < len(text) and text[pos] == '.':
        pos += 1
        divider = 1.0
        while pos < len(text) and '0' <= text[pos] <= '9':
            divider /= 10.0
            value += divider * (ord(text[pos]) - 48)
            pos += 1
    if pos < len(text) and text[pos] in 'eE':
        pos += 1
        negative = pos < len(text) and text[pos] == '-'
        if pos < len(text) and text[pos] in '+-':
            pos += 1
        exponent = 0.0
        while pos < len(text) and '0' <= text[pos] <= '9':
            exponent = exponent * 10.0 + (ord(text[pos]) - 48)
            pos += 1
        try:
            ten_power = math.pow(10.0, exponent)
            value = value / ten_power if negative else value * ten_power
        except (OverflowError, ValueError) as exc:
            raise BAS2TAPError(f'Line {line_number}: number outside Spectrum range') from exc
    return text[start:pos].encode('ascii') + _float_cache(value, line_number), pos


def _prepare_line(raw: str, ascii_line: int, *, first: bool = True,
                  warn: Callable[[str], None] | None = None) -> tuple[int, str] | None:
    """Port of PrepareLine / GetLineNumber, including BAS2TAP's spaces."""
    if any((ord(c) < 32 and c != '\t') or ord(c) >= 127 for c in raw):
        raise BAS2TAPError(f'ASCII line {ascii_line}: invalid character')
    out = []
    string = remark = spaced = False
    pos = 0
    while pos < len(raw):
        c = raw[pos]
        if c == '\t':
            out.append('\x06')
            pos += 1
            continue
        if not remark and (raw[pos:pos + 5].upper() in (' REM ', ':REM ')):
            remark = True
        if string or remark:
            out.append(c)
        elif c == ' ':
            if not spaced:
                out.append(c)
                spaced = True
        else:
            spaced = False
            out.append(c)
        if c == '"' and not remark:
            string = not string
        pos += 1
    line = ''.join(out)
    m = LINE_NO.match(line)
    if not m:
        if not line.strip():
            if warn:
                warn(f'WARNING - Skipping empty ASCII line {ascii_line}')
            return None
        raise BAS2TAPError(f'ASCII line {ascii_line}: missing line number')
    number = int(m.group(1))
    if number > 9999:
        raise BAS2TAPError(f'Line {number}: line number exceeds 9999')
    if string:
        raise BAS2TAPError(f'Line {number}: missing terminating quote')
    if m.end() == len(line) and first:
        raise BAS2TAPError(f'Line {number}: no statements')
    return number, line[m.end():]


def _expand(text: str, pos: int, *, strip: bool, mode: dict | None = None,
            line_number: int = 10, warn: Callable[[str], None] | None = None) -> tuple[bytes, int] | None:
    """Port of ExpandSequences. Raw brace escapes work in strings and REM."""
    if pos >= len(text) or text[pos] != '{':
        return None
    remaining = text[pos:]
    top = remaining.upper()
    value = None
    end = None
    suppress_strip = False
    for label, byte in (('{CODE}', 0xAF), ('{CAT}', 0xCF), ('{(C)}', 0x7F)):
        if top.startswith(label):
            value, end = bytes((byte,)), pos + len(label)
            suppress_strip = label in ('{CODE}', '{CAT}')
            break
    if value is None and len(remaining) >= 3 and remaining[2] == '}' and 'A' <= top[1] <= 'U':
        if mode is not None and top[1] in 'TU':
            if mode['value'] == 0:
                raise BAS2TAPError(f'Line {line_number}: UDG T/U conflicts with 128K tokens')
            mode['value'] = 1
        value, end = bytes((0x90 + ord(top[1]) - 65,)), pos + 3
    if value is None and len(remaining) >= 4 and remaining[3] == '}' and remaining[1] in '+-' and remaining[2] in '12345678':
        x = int(remaining[2]) % 8
        value = bytes((0x88 + (x ^ 7) if remaining[1] == '+' else 0x80 + x,))
        end = pos + 4
    if value is None and len(remaining) >= 4 and remaining[3] == '}' and all(c in HEX for c in remaining[1:3]):
        value, end = bytes((int(remaining[1:3], 16),)), pos + 4
    if value is None:
        for name, byte in CONTROL.items():
            if not top.startswith('{' + name):
                continue
            # Keep C behavior: names are a prefix, not a regex word boundary.
            p = pos + len(name) + 1
            while p < len(text) and text[p] == ' ':
                p += 1
            start = p
            while p < len(text) and text[p].isdigit():
                p += 1
            a = int(text[start:p] or '0') & 255
            v = [byte, a]
            if byte in (0x16, 0x17):
                if p >= len(text) or text[p] != ',':
                    continue
                p += 1
                while p < len(text) and text[p] == ' ':
                    p += 1
                start = p
                while p < len(text) and text[p].isdigit():
                    p += 1
                v.append(int(text[start:p] or '0') & 255)
            if p < len(text) and text[p] == '}':
                value, end = bytes(v), p + 1
                break
    if value is None:
        if warn and '}' in remaining:
            warn(f'WARNING - Unexpandable sequence \"{remaining[:remaining.index("}") + 1]}\" in line {line_number}')
        return None
    if strip and not suppress_strip and end is not None:
        while end < len(text) and text[end] == ' ':
            end += 1
    return value, end


def _match(text: str, pos: int, case_insensitive: bool) -> tuple[int, int] | None:
    """Port of MatchToken's longest match and alpha/alpha boundary rule."""
    if text[pos] == ':':
        end = pos + 1
        while end < len(text) and text[end] == ' ':
            end += 1
        return 58, end
    for code, word in MATCH_ORDER:
        frag = text[pos:pos + len(word)]
        if (frag.upper() if case_insensitive else frag) != word:
            continue
        end = pos + len(word)
        if word[-1].isalpha() and end < len(text) and text[end].isalpha():
            continue
        while end < len(text) and text[end] == ' ':
            end += 1
        return code, end
    return None


def _source_identifier(text: str, pos: int) -> tuple[bytes, int] | None:
    """ZX-Basicus' VARNAME terminal: a name, not a token-map prefix.

    Scalar names may be longer than one character. Variable occurrences in
    Sinclair 48K BASIC cannot be determined by keyword spelling alone.
    """
    if pos >= len(text) or not text[pos].isascii() or not text[pos].isalpha():
        return None
    end = pos + 1
    while end < len(text) and text[end].isascii() and text[end].isalnum():
        end += 1
    if end < len(text) and text[end] == '$':
        end += 1
    return text[pos:end].encode('ascii'), end


def _print_at_control(text: str, pos: int, statement: int | None,
                      brackets: int, print_boundary: bool) -> bool:
    """AT is an I/O control only in PRINT/INPUT print-item positions.

    Grammar reference: ZX-Basicus' printcontrol/loccontrol productions.
    A variable spelled AT is legal in LET and ordinary expressions. Requiring
    a following expression, comma and second expression avoids treating
    'PRINT AT;' or 'PRINT AT+1' as a position control.
    """
    if statement not in (0xF5, 0xEE, 0xE0) or brackets or not print_boundary:
        return False
    rest = text[pos + 2:]
    if not rest or rest[0] != ' ':
        return False
    rest = rest.lstrip(' ')
    if not rest or rest[0] in ',;:':
        return False
    quoted = False
    depth = 0
    for index, ch in enumerate(rest):
        if ch == '"':
            quoted = not quoted
        elif not quoted:
            if ch == '(':
                depth += 1
            elif ch == ')':
                depth -= 1
            elif ch == ',' and depth == 0:
                return bool(rest[:index].strip() and rest[index + 1:].strip(' ;:'))
            elif ch in ';:' and depth == 0:
                return False
    return False


def tokenize_line(text: str, *, line_number: int = 10, case_insensitive: bool = False,
                  _mode: dict | None = None,
                  _warn: Callable[[str], None] | None = None) -> bytes:
    """BAS2TAP C's lexical logic, returning one encoded BASIC body + CR.

    Expression and variable positions follow Sinclair 48K grammar, while
    the original ROM remains authoritative for syntax validation.
    """
    if not text.isascii():
        raise BAS2TAPError(f'Line {line_number}: non-ASCII BASIC')
    mode = _mode if _mode is not None else {'value': -1}
    encoded = bytearray()
    pos = 0
    expect_keyword = True
    in_string = False
    brackets = 0
    subline = 1
    def_fn = inside_fn = False
    statement = None
    variable_required = False
    print_boundary = False
    while pos < len(text):
        c = text[pos]
        if in_string:
            if c == '"':
                encoded.append(34)
                pos += 1
                in_string = False
                while pos < len(text) and text[pos] == ' ':
                    pos += 1
            else:
                expansion = _expand(text, pos, strip=False, mode=mode, line_number=line_number, warn=_warn)
                if expansion:
                    value, pos = expansion
                    encoded.extend(value)
                else:
                    encoded.append(ord(c))
                    pos += 1
            continue
        if c == '"':
            if expect_keyword:
                raise BAS2TAPError(f'Line {line_number}, statement {subline}: expected keyword')
            encoded.append(34)
            in_string = True
            pos += 1
            continue
        if expect_keyword:
            hit = _match(text, pos, case_insensitive)
            if not hit:
                raise BAS2TAPError(f'Line {line_number}, statement {subline}: expected keyword near {text[pos:pos + 16]!r}')
            token, pos = hit
            if token in (0xA3, 0xA4):
                if mode['value'] == 1:
                    raise BAS2TAPError(f'Line {line_number}: 128K token conflicts with UDG T/U')
                mode['value'] = 0
            # In original C keyword matching rejects TokenType=0, while the full syntax
            # checker later catches misplaced expression tokens. The ROM is a picky customer.
            encoded.append(token)
            if token != 58:
                expect_keyword = False
                statement = token
                variable_required = token in (0xF1, 0xEB, 0xF3, 0xE9, 0xE3, 0xCE)
                print_boundary = token in (0xF5, 0xEE, 0xE0)
            else:
                statement = None
                variable_required = False
                print_boundary = False
            if token == 0xCE:
                def_fn, inside_fn = True, False
            if token == 0xEA:
                while pos < len(text):
                    expansion = _expand(text, pos, strip=False, mode=mode, line_number=line_number, warn=_warn)
                    if expansion:
                        value, pos = expansion
                        encoded.extend(value)
                    else:
                        encoded.append(ord(text[pos]))
                        pos += 1
            continue
        if c == '(':
            brackets += 1
            if def_fn and not inside_fn:
                inside_fn = True
            encoded.append(40)
            pos += 1
            continue
        if c == ')':
            if def_fn and inside_fn:
                encoded.extend(b'\x0e\0\0\0\0\0')
                inside_fn = def_fn = False
            brackets -= 1
            if brackets < 0:
                raise BAS2TAPError(f'Line {line_number}: too many closing brackets')
            encoded.append(41)
            pos += 1
            continue
        if c == ',' and def_fn and inside_fn:
            encoded.extend(b'\x0e\0\0\0\0\0,')
            pos += 1
            continue
        # ZX-Basicus' LET/FOR/NEXT/DIM/READ/DEF FN grammar positions require VARNAME. A word that spells
        # a ROM token is still a variable there. One bad keyword can ruin a perfectly good afternoon.
        name = _source_identifier(text, pos)
        if name and variable_required:
            value, pos = name
            encoded.extend(value)
            variable_required = False
            print_boundary = False
            continue
        hit = _match(text, pos, case_insensitive)
        if hit and hit[0] == 0xAC and name and not _print_at_control(
                text, pos, statement, brackets, print_boundary):
            # AT is not an ordinary expression function. Outside an I/O control it
            # must be the letters of a variable name.
            value, pos = name
            encoded.extend(value)
            print_boundary = False
            continue
        if hit:
            token, pos = hit
            if token in (0xA3, 0xA4):
                if mode['value'] == 1:
                    raise BAS2TAPError(f'Line {line_number}: 128K token conflicts with UDG T/U')
                mode['value'] = 0
            if token in KEYWORDS and token not in COLORS:
                raise BAS2TAPError(f'Line {line_number}, statement {subline}: unexpected keyword {TOKENS[token]}')
            encoded.append(token)
            if token in (58, 0xCB):
                expect_keyword = True
                def_fn = False
                variable_required = False
                statement = None
                print_boundary = False
                if brackets:
                    raise BAS2TAPError(f'Line {line_number}: unclosed brackets before separator')
                subline += 1
                if subline > 127:
                    raise BAS2TAPError(f'Line {line_number}: too many statements')
            elif token == 0xC4:
                print_boundary = False
                value = 0
                while pos < len(text) and text[pos] in '01':
                    value = value * 2 + int(text[pos])
                    if value > 65535:
                        raise BAS2TAPError(f'Line {line_number}: BIN number exceeds 65535')
                    encoded.append(ord(text[pos]))
                    pos += 1
                encoded.extend((14, 0, 0, value & 255, value >> 8, 0))
            if token not in (58, 0xCB, 0xC4):
                print_boundary = False
            continue
        if c in '0123456789.':
            print_boundary = False
            literal, pos = _number_at(text, pos, line_number)
            encoded.extend(literal)
            continue
        expansion = _expand(text, pos, strip=True, mode=mode, line_number=line_number, warn=_warn)
        if expansion:
            value, pos = expansion
            encoded.extend(value)
        elif c.isalpha():
            print_boundary = False
            # The C converter copies complete alphanumeric identifiers in one operation. Embedded
            # keywords do NOT start inside a variable.
            end = pos + 1
            while end < len(text) and text[end].isascii() and text[end].isalnum():
                end += 1
            encoded.extend(text[pos:end].encode('ascii'))
            pos = end
        else:
            encoded.append(ord(c))
            if c in ",;'":
                print_boundary = statement in (0xF5, 0xEE, 0xE0) and brackets == 0
                if c == ',' and statement == 0xE3 and brackets == 0:
                    variable_required = True
            elif c != ' ':
                print_boundary = False
            pos += 1
    if in_string:
        raise BAS2TAPError(f'Line {line_number}: unclosed string')
    if brackets:
        raise BAS2TAPError(f'Line {line_number}: too few closing brackets')
    encoded.append(13)
    if len(encoded) > 65535:
        raise BAS2TAPError(f'Line {line_number}: BASIC line too large')
    return bytes(encoded)


def encode_program(listing: str, *, case_insensitive: bool = False,
                   warn: Callable[[str], None] | None = None,
                   syntax_check: bool = False) -> bytes:
    """Encode numbered ASCII BASIC as Sinclair line records (no TAP header)."""
    records = bytearray()
    previous = -1
    mode = {'value': -1}
    # fgets() in C divides at LF, not at every Unicode/ASCII line separator. Include
    # the physical LF and optional CR when checking its buffer length. A lone vertical
    # tab or other control must be *rejected*, not swallowed by Python
    # str.splitlines() as if it were a line terminator.
    lines = listing.split('\n') if listing else []
    if listing.endswith('\n'):
        lines.pop()
    for file_line, physical in enumerate(lines, 1):
        line_len = len(physical) + (1 if file_line < len(lines) or listing.endswith('\n') else 0)
        if line_len >= 1024:
            raise BAS2TAPError(f'ASCII line {file_line}: longer than C input buffer')
        raw = physical[:-1] if physical.endswith('\r') else physical
        item = _prepare_line(raw, file_line, first=(previous == -1), warn=warn)
        if item is None:
            continue
        number, body = item
        if number < previous:
            raise BAS2TAPError(f'Line {number}: smaller than previous line {previous}')
        if number == previous and warn:
            warn(f'WARNING - Duplicate use of line number {number}')
        previous = number
        result = tokenize_line(body, line_number=number, case_insensitive=case_insensitive,
                               _mode=mode, _warn=warn)
        records.extend(number.to_bytes(2, 'big') + len(result).to_bytes(2, 'little') + result)
        if len(records) > 41500:
            raise BAS2TAPError(f'Line {number}: program exceeds original C 41500-byte limit')
    result = bytes(records)
    if syntax_check:
        from bas2tap_syntax import check_program
        check_program(result)
    return result


def _block(flag: int, data: bytes) -> bytes:
    content = bytes((flag,)) + data
    checksum = 0
    for b in content:
        checksum ^= b
    size = len(content) + 1
    if size > 65535:
        raise BAS2TAPError('TAP block exceeds 65535 bytes')
    return size.to_bytes(2, 'little') + content + bytes((checksum,))


def make_tap(program: bytes, *, name: str = '', autostart: int = 0x8000) -> bytes:
    """Port of TapeHeader and XOR parity generation (two ordinary TAP blocks)."""
    if len(name) > 10 or not name.isascii():
        raise BAS2TAPError('Tape name must be at most ten ASCII characters')
    if autostart != 0x8000 and not 0 <= autostart <= 9999:
        raise BAS2TAPError('Autostart must be a BASIC line number')
    if len(program) > 41500:
        raise BAS2TAPError('Program exceeds 41500-byte BAS2TAP limit')
    header = bytes((0,)) + name.encode('ascii').ljust(10, b' ')
    header += len(program).to_bytes(2, 'little')
    header += autostart.to_bytes(2, 'little')
    header += len(program).to_bytes(2, 'little')
    return _block(0, header) + _block(255, program)


def convert(source: str, *, name: str = '', autostart: int = 0x8000,
            case_insensitive: bool = False,
            warn: Callable[[str], None] | None = None,
            syntax_check: bool = False) -> bytes:
    """Full in-memory BAS-to-TAP conversion, without external subprocesses."""
    return make_tap(encode_program(source, case_insensitive=case_insensitive, warn=warn,
                                   syntax_check=syntax_check),
                    name=name, autostart=autostart)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Pure-Python BAS2TAP 2.6 tokenizer and TAP writer')
    parser.add_argument('-q', action='store_true', help='quiet')
    parser.add_argument('-w', action='store_true', help='suppress warnings')
    parser.add_argument('-e', action='store_true', help='send errors to stdout')
    parser.add_argument('-c', action='store_true', help='case-insensitive keywords')
    parser.add_argument('-n', action='store_true', help='disable original C-compatible BASIC syntax checking')
    parser.add_argument('-s', metavar='NAME', default='', help='tape header name (max 10 characters)')
    parser.add_argument('-a', metavar='LINE', type=int, default=0x8000, help='auto-start line')
    parser.add_argument('input', type=Path)
    parser.add_argument('output', nargs='?', type=Path)
    args = parser.parse_args(argv)
    output = args.output or args.input.with_suffix('.tap')
    if output.suffix.lower() != '.tap':
        output = output.with_suffix('.tap')
    try:
        listing = args.input.read_text(encoding='ascii')
        result = convert(listing, name=args.s, autostart=args.a, case_insensitive=args.c,
                         warn=None if args.w else print,
                         syntax_check=not args.n)
        if args.input.resolve() == output.resolve():
            raise BAS2TAPError('Output would overwrite the BASIC listing')
        output.write_bytes(result)
    except (BAS2TAPError, UnicodeError, OSError) as exc:
        print(f'BAS2TAP: {exc}', file=sys.stdout if args.e else sys.stderr)
        return 1
    if not args.q:
        print(f'Wrote {output} ({len(result)} bytes)')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
