#!/usr/bin/env python3
# ZX-UX — ZX Spectrum 48K TZX-to-BASIC LLIST converter
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Based on original work by Supratim Sanyal of SANYALnet Labs.
# License: ZX-UX repository LICENSE (non-commercial terms and attribution).
#
# File: zx-tzx2bas.py
# Purpose: Recover an ASCII Sinclair BASIC listing from actual tokenized TZX.
# Reference: unmodified 16 KiB Sinclair Spectrum 48K ROM, LLIST path.
# Scope: ROM's character stream before ZX Printer bitmap/layout processing.
# Dependencies: Python 3 standard library only; no external ROM or emulator.
# Safety: reject ambiguous tapes, protect original BASIC/TZX inputs, never
#         overwrite an existing file; writing outputs is deliberately opt-in.
"""Generate ROM-LLIST-spaced Spectrum BASIC text from a tokenized TZX tape.

The original LLIST command uses the same BASIC line formatter as LIST, but
selects printer stream #3 rather than screen stream #2. The formatting path
runs through the 48K ROM's OUT-LINE, NUMBER, OUT-CHAR, PO-TOKENS, PO-SEARCH,
PO-EACH and PO-TR-SP routines. Keyword characters come directly from the
embedded original ROM table at 0096h, including high-bit terminators. They
are not obtained from a separately transcribed Python keyword dictionary.

This converter reproduces the *logical character codes* sent by those routines
before the printer's 32-column bitmap engine. It does not emulate printer
pixels, wrapping, keyboard input, video output or peripheral timing.

The output .bas file is a reversible-intent ASCII export: character bytes that
cannot safely appear as literal ASCII source are represented as BAS2TAP-style
{HH} escapes. This is deliberately separate from llist_codes(), which emits
exactly the ROM's unescaped character stream. The tape retains original hidden
numeric representations, control bytes, quotes and comments; do not substitute
the exported ASCII for archival tape bytes without an independent round trip.

Example, one tape:
    python3 build/tools/zx-tzx2bas.py game.tzx -o staged/game.bas

Example, preserved 60-program collection (no original files are touched):
    python3 build/tools/zx-tzx2bas.py --collection src/examples/basic-src/original-sinclair-basic-collections/60-programs \
        --out-dir build/tmp/tzx-basic-listings

For license attribution and version information, run --about.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import sys


# These bytes were copied, without translation, from 0096h..0204h (inclusive)
# of the verified 16 KiB Sinclair 48K ROM. Its full-image SHA-256 is:
# d55daa439b673b0e3f5897f99ac37ecb45f974d1862b4dadb85dec34af99cb42.
# PO-SEARCH starts at 0095h, immediately before the first RND character.
# The 91 entries map consecutively to token codes A5h..FFh and terminate
# with bit 7 set on the *last* character. Preserve these raw bits: the
# original PO-TOKENS printer uses them for its trailing-space branch.
# No ROM file or ROM emulator is needed in production. The independent tests
# compare these exact bytes and rendered output against executing ROM code.
ROM_TOKEN_TABLE = bytes.fromhex('''
    52 4e c4 49 4e 4b 45 59 a4 50 c9 46 ce 50 4f 49 4e d4 53 43 52 45 45 4e
    a4 41 54 54 d2 41 d4 54 41 c2 56 41 4c a4 43 4f 44 c5 56 41 cc 4c 45 ce
    53 49 ce 43 4f d3 54 41 ce 41 53 ce 41 43 d3 41 54 ce 4c ce 45 58 d0 49
    4e d4 53 51 d2 53 47 ce 41 42 d3 50 45 45 cb 49 ce 55 53 d2 53 54 52 a4
    43 48 52 a4 4e 4f d4 42 49 ce 4f d2 41 4e c4 3c bd 3e bd 3c be 4c 49 4e
    c5 54 48 45 ce 54 cf 53 54 45 d0 44 45 46 20 46 ce 43 41 d4 46 4f 52 4d
    41 d4 4d 4f 56 c5 45 52 41 53 c5 4f 50 45 4e 20 a3 43 4c 4f 53 45 20 a3
    4d 45 52 47 c5 56 45 52 49 46 d9 42 45 45 d0 43 49 52 43 4c c5 49 4e cb
    50 41 50 45 d2 46 4c 41 53 c8 42 52 49 47 48 d4 49 4e 56 45 52 53 c5 4f
    56 45 d2 4f 55 d4 4c 50 52 49 4e d4 4c 4c 49 53 d4 53 54 4f d0 52 45 41
    c4 44 41 54 c1 52 45 53 54 4f 52 c5 4e 45 d7 42 4f 52 44 45 d2 43 4f 4e
    54 49 4e 55 c5 44 49 cd 52 45 cd 46 4f d2 47 4f 20 54 cf 47 4f 20 53 55
    c2 49 4e 50 55 d4 4c 4f 41 c4 4c 49 53 d4 4c 45 d4 50 41 55 53 c5 4e 45
    58 d4 50 4f 4b c5 50 52 49 4e d4 50 4c 4f d4 52 55 ce 53 41 56 c5 52 41
    4e 44 4f 4d 49 5a c5 49 c6 43 4c d3 44 52 41 d7 43 4c 45 41 d2 52 45 54
    55 52 ce 43 4f 50 d9
''')
ROM_TOKEN_TABLE_SHA256 = '32874566b963014669040a63e04913db95d92b63d5dff513aefdcae2a0343f60'


class TapeError(ValueError):
    """The source tape is malformed, ambiguous, or unsupported."""


def _take(data: bytes, offset: int, size: int, what: str) -> tuple[bytes, int]:
    if size < 0 or offset + size > len(data):
        raise TapeError(f'{what}: truncated at offset {offset}')
    return data[offset:offset + size], offset + size


def _u16(data: bytes, at: int) -> int:
    return int.from_bytes(data[at:at + 2], 'little')


def _u24(data: bytes, at: int) -> int:
    return int.from_bytes(data[at:at + 3], 'little')


def _u32(data: bytes, at: int) -> int:
    return int.from_bytes(data[at:at + 4], 'little')


def tzx_blocks(tape: bytes):
    """Walk TZX records in recorded order, yielding complete flag+data+XOR.

    This is a tape container reader, not a replacement for the Spectrum ROM.
    The ROM performs BASIC listing only *after* the cassette has loaded the
    tokenized BASIC program into RAM. We first recover precisely those bytes.

    TZX 0x10 stores an ordinary-speed data block, 0x11 turbo data, and 0x14
    pure data. All three can contain an intact Spectrum TAP block only when
    their final-byte width is eight bits. Verify XOR over the entire block.
    Non-data text and metadata records are read according to their explicit
    lengths, never misread as BASIC. Reject tape-flow branching/selection,
    audio waveforms and unknown types rather than guessing a playback path.

    Yields:
        Read-only byte strings with the Spectrum flag at offset zero and its
        XOR checksum in the final byte; timing and TZX wrappers are discarded.
    """
    if not tape.startswith(b'ZXTape!\x1a') or len(tape) < 10:
        raise TapeError('missing TZX signature')
    if tape[8] != 1:
        raise TapeError(f'unsupported TZX major version {tape[8]}')
    pos = 10
    while pos < len(tape):
        start = pos
        kind = tape[pos]
        pos += 1
        if kind == 0x10:  # standard speed: pause, u16 data length
            info, pos = _take(tape, pos, 4, 'standard-speed block')
            payload, pos = _take(tape, pos, _u16(info, 2), 'standard-speed payload')
        elif kind == 0x11:  # turbo: 15 timing bytes, u24 data length
            info, pos = _take(tape, pos, 18, 'turbo block')
            if info[12] != 8:
                raise TapeError(f'turbo block at {start}: non-byte-aligned last byte')
            payload, pos = _take(tape, pos, _u24(info, 15), 'turbo payload')
        elif kind == 0x14:  # pure data: two pulse lengths, used bits, pause, size
            info, pos = _take(tape, pos, 10, 'pure-data block')
            if info[4] != 8:
                raise TapeError(f'pure-data block at {start}: non-byte-aligned last byte')
            payload, pos = _take(tape, pos, _u24(info, 7), 'pure-data payload')
        elif kind in (0x20, 0x23, 0x24, 0x2A):  # pause, jump, loop start, stop 48K
            if kind != 0x20:
                raise TapeError(f'control-flow block {kind:02X} at {start}: cannot flatten faithfully')
            size = 2
            info, pos = _take(tape, pos, size, f'block {kind:02X}')
            if kind == 0x20 and _u16(info, 0) == 0:
                raise TapeError(f'stop-tape block at {start}: playback sequence ambiguous')
        elif kind in (0x21, 0x30):
            info, pos = _take(tape, pos, 1, f'block {kind:02X}')
            _, pos = _take(tape, pos, info[0], f'block {kind:02X} text')
        elif kind == 0x22:  # group end
            pass
        elif kind == 0x31:  # message: duration + length
            info, pos = _take(tape, pos, 2, 'message')
            _, pos = _take(tape, pos, info[1], 'message text')
        elif kind in (0x28, 0x32):  # selection or archive info: u16 payload
            info, pos = _take(tape, pos, 2, 'metadata length')
            if kind == 0x28:
                raise TapeError(f'select block at {start}: playback sequence ambiguous')
            _, pos = _take(tape, pos, _u16(info, 0), 'archive information')
        elif kind == 0x33:  # hardware info: count * 3
            info, pos = _take(tape, pos, 1, 'hardware information')
            _, pos = _take(tape, pos, info[0] * 3, 'hardware entries')
        elif kind == 0x35:  # custom info: 16-byte id + u32 length
            info, pos = _take(tape, pos, 20, 'custom info')
            _, pos = _take(tape, pos, _u32(info, 16), 'custom info body')
        elif kind == 0x5A:  # TZX concatenation marker
            marker, pos = _take(tape, pos, 9, 'TZX glue')
            if marker[:8] != b'XTape!\x1a\x01':
                raise TapeError(f'invalid TZX glue at {start}')
        else:
            raise TapeError(f'unsupported TZX block type {kind:02X} at offset {start}')
        if kind in (0x10, 0x11, 0x14):
            if len(payload) < 2:  # flag byte and XOR parity byte
                raise TapeError(f'block {kind:02X} at {start}: short tape block')
            check = 0
            for byte in payload:
                check ^= byte
            if check:
                raise TapeError(f'block {kind:02X} at {start}: TAP XOR checksum mismatch')
            yield payload


def basic_programs(tape: bytes):
    """Pair Spectrum BASIC headers with their immediately following data.

    The 19-byte flagged TAP header encodes program type, a ten-byte tape name,
    total data length, autostart line, and an offset to the variable area.
    Only bytes preceding the variables offset represent numbered BASIC lines.
    This procedure does not run code or reconstruct BASIC from a paired BAS.
    """
    pending = None
    for block in tzx_blocks(tape):
        if block[0] == 0 and len(block) == 19:
            # Format: flag, type, 10-byte name, length, autostart, vars, XOR.
            if pending:
                raise TapeError('new header before previous BASIC data')
            if block[1] == 0:
                pending = (block[2:12], _u16(block, 12), _u16(block, 16))
            continue
        if pending is not None:
            name, expected, vars_offset = pending
            pending = None
            if block[0] != 0xff:
                raise TapeError('BASIC header not followed by a data block')
            program = block[1:-1]
            if len(program) != expected:
                raise TapeError(f'BASIC {name!r}: expected {expected} bytes, got {len(program)}')
            if vars_offset > len(program):
                raise TapeError(f'BASIC {name!r}: variables offset outside program')
            # BAS2TAP headers normally have vars-offset == program length. A real tape may
            # contain variables after BASIC lines; follow the header, not a guess.
            yield name, program[:vars_offset]
    if pending:
        raise TapeError('missing BASIC data block after header')


def numbered_lines(program: bytes):
    """Decode ROM line headers: big-endian line number, little-endian length.

    Stored line lengths include the trailing 0Dh terminator. They are the
    only safe way to identify boundaries: binary number-cache values may
    themselves contain 0Dh, so splitting raw BASIC at carriage returns is
    incorrect. Reject out-of-order lines, missing terminators, or truncation.
    """
    p = 0
    last = -1
    while p < len(program):
        header, p = _take(program, p, 4, 'BASIC line header')
        number = int.from_bytes(header[:2], 'big')
        size = _u16(header, 2)
        if not 0 <= number <= 9999 or number <= last:
            raise TapeError(f'BASIC line numbers out of order: {last}, {number}')
        if size == 0:
            raise TapeError(f'Line {number}: zero-length BASIC line')
        contents, p = _take(program, p, size, f'Line {number}')
        if contents[-1] != 13:
            raise TapeError(f'Line {number}: no end-of-line marker')
        # The ROM's OUT-LINE stops at the first *visible* CR, not the encoded
        # line length. Hidden Sinclair number bytes may contain 0D, however, and
        # 18B6 skips all five binary bytes before CR testing. Refuse extra
        # characters after an early CR instead of silently exporting a shortened
        # BASIC line that looks complete.
        cursor = 0
        while cursor < len(contents) - 1:
            value = contents[cursor]
            if value == 14:
                if cursor + 6 > len(contents) - 1:
                    raise TapeError(f'Line {number}: truncated numeric cache')
                cursor += 6
                continue
            if value == 13:
                raise TapeError(f'Line {number}: embedded ROM end-of-line at offset {cursor}')
            cursor += 1
        last = number
        yield number, contents[:-1]
    if p != len(program):
        raise TapeError('BASIC program does not end on a line boundary')


def rom_keywords() -> dict[int, bytes]:
    """Return the 91 original 48K ROM token spellings, indexed 0xA5..0xFF.

    Unlike hand-typed token mappings, these names and their exact lengths
    are obtained by scanning the *embedded original* ROM table and masking the high bit on
    the final character of each entry.
    """
    return {0xA5 + n: word for n, (word, _, _) in enumerate(_rom_token_entries())}


def llist_segments(number: int, body: bytes):
    """Port the ROM LLIST character-output path (excluding printer pixels).

    17F5 LLIST -> 17FB LIST-1 -> 1833 LIST-ALL -> 1855 OUT-LINE:
    1A28 OUT-NUM-2 emits a four-column number; 1874 resets FLAGS.0.
    18A5/18B6 NUMBER skips the five-byte numeric representation.
    1937 OUT-CHAR sends each source code to RST 10.
    0B52 PO-T-UDG routes A5..FF to 0C10 PO-TOKENS.
    0C41 PO-SEARCH checks index and original first ROM table byte.
    0C22 PO-EACH reads and emits characters until high-bit termination.
    0C2D..0C39 PO-TR-SP determines whether to add a trailing space.
    0B65 PO-CHAR resets FLAGS.0 for ordinary printable characters and sets
    it for space; nonprintable/UDG codes do not alter that flag.

    In the ROM, OUT-LINE reads each stored token byte in memory order and
    hands it to OUT-CHAR; RST 10 processes normal characters or expands a
    token via the table. It never re-parses English keyword spellings or
    differentiates a token inside quotes versus outside quotes. Those facts
    explain why the stored bytes ``sk`` then token CB print ``sk THEN``.

    FLAGS.0 tracks whether the most recent ordinary printable output was a
    space. PO-SEARCH adds leading space according to the token index and
    the *first unmasked ROM table byte*. PO-TR-SP decides whether to append a
    trailing space by doubling the *original* last table byte (with its high
    bit still set). Looking at the unmasked bytes is essential: inspecting
    just Python words would give different answers for some tokens.

    0Eh numeric caches are six bytes total (marker + five binary bytes).
    The ROM skips them even where their payload contains apparent characters
    such as CR or further tokens; the line length is determined separately.

    Each result is (emitted bytes, original BASIC byte, expanded-token flag).
    None of these stages infers a token from adjacent BASIC source letters.
    """
    if not 0 <= number <= 9999:
        raise TapeError(f'invalid BASIC line number {number}')
    token_entries = _rom_token_entries()
    # OUT-NUM-2/OUT-SP-NO: the ROM prints a right-aligned four-column decimal BASIC
    # line number. This prefix participates in the stream, but the subsequent OUT-LINE
    # FLAGS initialization determines whether the *first source token* receives an
    # additional leading space.
    parts = [(f'{number:4d}'.encode('ascii'), None, False)]
    # OUT-LINE at 1874 sets FLAGS.0 to permit a leading space.
    flags_0 = False

    def emit(byte: int) -> None:
        nonlocal flags_0
        # 0B65 PO-CHAR: only ordinary printable characters alter FLAGS.0; characters less than
        # 20h are dispatched as printer controls.
        if 32 <= byte < 128:
            flags_0 = (byte == 32)

    p = 0
    while p < len(body):
        value = body[p]
        # 18B6/OUT-LINE sees a raw CR as line termination regardless of whether
        # it occurs inside quoted text or after a REM token. The caller normally
        # strips only the *final* line terminator; direct llist_codes() calls
        # must nevertheless reproduce the ROM here.
        if value == 13:
            break
        if value == 14:  # 18B6 NUMBER: skip its full hidden five-byte form.
            if p + 6 > len(body):
                raise TapeError(f'Line {number}: truncated five-byte numeric value at offset {p}')
            p += 6
            continue
        if value < 0xA5:
            emit(value)
            parts.append((bytes([value]), value, False))
        else:
            index = value - 0xA5
            word, first, last = token_entries[index]
            out = bytearray()
            # 0C41: carry set for 00..1F; otherwise subtract 'A' from
            # the *original* first (possibly high-bit-set) table byte.
            if index >= 0x20 and first >= 0x41 and not flags_0:
                out.append(32)
                emit(32)
            for character in word:
                out.append(character)
                emit(character)
            # 0C2A doubles the last original byte and tests 48h ('$') or >=82h ('A' through
            # letters); index 0..2 never follows.
            last_doubled = (last << 1) & 255
            if index >= 3 and (last_doubled == 0x48 or last_doubled >= 0x82):
                out.append(32)
                emit(32)
            parts.append((bytes(out), value, True))
        p += 1
    return parts


def _rom_token_entries() -> tuple[tuple[bytes, int, int], ...]:
    """Read PO-TOKENS' actual bit-7-terminated token table (0096h).

    The ROM's 0C41 PO-SEARCH begins from 0095h (a byte before RND) and
    traverses exactly 91 table entries. Embedded bytes begin at 0096h.
    The character with bit 7 set is output after masking that bit,
    but its *unmasked* value affects trailing
    whitespace in the printer routine. Keep both first and last raw bytes.

    Reject an unexpected table length, digest, unprintable table entries,
    incomplete termination, or unexpected beginning/end token spellings.
    The Python source embeds the original byte table verbatim, not a separately
    transcribed keyword spelling dictionary or ROM binary.
    """
    table = ROM_TOKEN_TABLE
    if (len(table) != 367
            or hashlib.sha256(table).hexdigest() != ROM_TOKEN_TABLE_SHA256):
        raise TapeError('embedded original 48K ROM token table failed integrity check')
    pos = 0
    out = []
    for token in range(0xA5, 0x100):
        start = pos
        while pos < len(table) and not (table[pos] & 128):
            pos += 1
        if pos >= len(table) or pos - start > 40:
            raise TapeError(f'ROM keyword {token:02X} has no valid high-bit terminator')
        raw = table[start:pos + 1]
        pos += 1
        word = bytes(c & 0x7f for c in raw)
        if not word or any(not 32 <= c < 127 for c in word):
            raise TapeError(f'ROM keyword {token:02X} contains invalid characters')
        out.append((word, raw[0], raw[-1]))
    if out[0][0] != b'RND' or out[0xCB-0xA5][0] != b'THEN' or out[-1][0] != b'COPY':
        raise TapeError('unexpected 48K ROM keyword sequence')
    if pos != len(table):
        raise TapeError('embedded ROM token table contains trailing bytes')
    return tuple(out)


def llist_codes(number: int, body: bytes) -> bytes:
    """ROM LLIST emitted character codes, prior to printer bitmap wrapping.

    The physical ZX Printer represents characters as dots in 32-column rows;
    this logical code stream is the relevant output for BASIC regeneration.
    """
    return b''.join(output for output, _, _ in llist_segments(number, body))


def list_line(number: int, body: bytes) -> str:
    """Serialize an LLIST line as strictly ASCII source with byte escapes.

    The ROM formatter does not know whether a token occurs in a quote,
    REM remark, or DATA string: it expands *every* stored keyword token.
    Printing a token's English name there would destroy the original byte.
    The separate ASCII serializer retains that byte explicitly as {HH},
    rather than feeding it back to a tokenizer as newly executable syntax.

    Likewise escape graphics/controls, pound (0x60), literal braces, and
    characters that cannot be represented safely as printable ASCII.
    All surrounding spaces come directly from llist_segments(), never
    from a heuristic keyword split. Hidden numeric caches stay omitted.
    The original tape must still be retained for exact archived bytes.
    """
    parts = llist_segments(number, body)
    quoted = rem = data = False
    rendered = []
    for segment, original, expanded in parts:
        if original is None:
            rendered.append(segment.decode('ascii'))
            continue
        if expanded:
            if quoted or rem or data:
                # The actual printer expands the token regardless of mode. Keep original bytes
                # instead of corrupting a string/REM/DATA.
                rendered.append(f'{{{original:02X}}}')
            else:
                rendered.append(segment.decode('ascii'))
            # A REM token *inside DATA* is literal DATA content, not the beginning of
            # a new REM statement. DATA ends at a colon.
            if not quoted and not rem and not data and original == 0xEA:
                rem = True
            if not quoted and not rem and original == 0xE4:
                data = True
        elif original == 34 and not rem:
            quoted = not quoted
            rendered.append('"')
        elif original == 58 and not quoted and not rem:
            data = False
            rendered.append(':')
        elif original == 96 or original in (123, 125) or original < 32 or original >= 127:
            rendered.append(f'{{{original:02X}}}')
        else:
            rendered.append(chr(original))
    if quoted:
        raise TapeError(f'Line {number}: unterminated quoted string')
    return ''.join(rendered)


def listing(tape: bytes, *, program_index: int | None = None) -> str:
    """Render a selected BASIC program without using a paired BAS source.

    If several BASIC files exist on the same tape, the user must choose a
    zero-based program index. The default is intentionally unambiguous only
    for a single stored BASIC program; no automatically selected fallback.
    """
    _rom_token_entries()
    programs = list(basic_programs(tape))
    if not programs:
        raise TapeError('TZX contains no Spectrum BASIC program header/data pair')
    if program_index is None:
        if len(programs) != 1:
            raise TapeError(f'TZX contains {len(programs)} BASIC programs; specify --program-index')
        program_index = 0
    if not 0 <= program_index < len(programs):
        raise TapeError(f'program index {program_index} outside 0..{len(programs) - 1}')
    name, program = programs[program_index]
    result = [list_line(n, body) for n, body in numbered_lines(program)]
    if not result:
        raise TapeError(f'BASIC program {name!r} has no lines')
    return '\n'.join(result) + '\n'


def _protected_listing_destination(path: Path) -> bool:
    """Never generate into any preserved 60-game BASIC directory."""
    parts = path.resolve().parts
    for i in range(len(parts) - 3):
        if (parts[i:i + 2] == ('bonus', '60-programs')
                and parts[i + 2][:2].isdigit() and parts[i + 3] == 'BASIC'):
            return True
    return False


def _write_listing(path: Path, content: str, inputs: tuple[Path, ...]):
    """Atomically reserve a new output filename; never overwrite source.

    Exclusive creation ('x') ensures a concurrent second invocation cannot
    silently replace another listing. Symlinks are resolved before the
    preserved-input-path check; the 60-game BASIC tree is always protected.
    """
    dest = path.resolve()
    if dest in (p.resolve() for p in inputs) or _protected_listing_destination(dest):
        raise TapeError(f'protected destination: {dest}')
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open('x', encoding='ascii', newline='\n') as f:
        f.write(content)


def main(argv=None):
    """Command-line entrance; all tapes are read-only and errors are explicit."""
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--about', action='store_true',
                    help='show ZX-UX attribution and the ROM reference')
    ap.add_argument('tzx', type=Path, nargs='?', help='preserved TZX input')
    ap.add_argument('--collection', type=Path,
                    help='directory containing all 60 numbered game folders')
    ap.add_argument('-o', '--output', type=Path,
                    help='single-tape BAS path (stdout if omitted)')
    ap.add_argument('--out-dir', type=Path,
                    help='staging directory for --collection (never the original BASIC tree)')
    ap.add_argument('--program-index', type=int, default=None,
                    help='zero-based BASIC program on tape')
    ap.add_argument('--verify-collection', action='store_true',
                    help='compare TZX listings to original BAS bytes, without writing')
    args = ap.parse_args(argv)
    if args.about:
        print('zx-tzx2bas — ZX-UX Spectrum 48K ROM LLIST BASIC exporter')
        print('Based on original work by Supratim Sanyal of SANYALnet Labs.')
        print('Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.')
        print('License: see ZX-UX repository LICENSE.')
        print('Reference: Sinclair Spectrum 48K ROM LLIST/OUT-LINE/PO-TOKENS.')
        return 0
    if bool(args.tzx) == bool(args.collection):
        ap.error('specify either one TZX or --collection')
    if args.collection and (args.output or (not args.out_dir and not args.verify_collection)
                        or (args.out_dir and args.verify_collection)):
        ap.error('--collection requires --out-dir, or --verify-collection alone')
    if args.verify_collection and not args.collection:
        ap.error('--verify-collection requires --collection')
    if args.tzx and args.out_dir:
        ap.error('--out-dir is for --collection only')
    try:
        rom_keywords()  # Verify the embedded exact original table before use.
        if args.tzx:
            content = listing(args.tzx.read_bytes(),
                              program_index=args.program_index)
            if args.output is None:
                sys.stdout.write(content)
            else:
                _write_listing(args.output, content, (args.tzx,))
                print(f'Listed {len(content.splitlines())} BASIC lines into {args.output}',
                      file=sys.stderr)
        else:
            root = args.collection.resolve()
            games = sorted(p for p in root.iterdir()
                           if p.is_dir() and len(p.name) > 3
                           and p.name[:2].isdigit() and p.name[2] == '-')
            if len(games) != 60:
                raise TapeError(f'expected 60 numbered game directories; found {len(games)}')
            out = args.out_dir.resolve() if args.out_dir else None
            planned = []
            for game in games:
                tape = game / 'BASIC' / (game.name + '.tzx')
                content = listing(tape.read_bytes(),
                                  program_index=args.program_index)
                if args.verify_collection:
                    original = game / 'BASIC' / (game.name + '.bas')
                    expected = original.read_bytes().replace(b'\r\n', b'\n')
                    recovered = content.encode('ascii')
                    if recovered != expected:
                        first = next((i for i in range(min(len(recovered), len(expected)))
                                      if recovered[i] != expected[i]),
                                     min(len(recovered), len(expected)))
                        raise TapeError(f'{game.name}: recovered ASCII differs from BAS at byte {first}; '
                                        f'BAS size {len(expected)}, TZX listing size {len(recovered)}')
                else:
                    dest = out / game.name / 'BASIC' / (game.name + '.bas')
                    if _protected_listing_destination(dest) or dest.exists():
                        raise TapeError(f'protected or existing output: {dest}')
                    planned.append((tape, dest, content))
            if args.verify_collection:
                print('Verified 60/60 independent TZX listings against preserved BAS bytes', file=sys.stderr)
            else:
                for tape, dest, content in planned:
                    _write_listing(dest, content, (tape,))
                print(f'Listed 60 TZX programs under {out}', file=sys.stderr)
    except (OSError, TapeError, UnicodeError) as exc:
        print(f'zx-tzx2bas: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
