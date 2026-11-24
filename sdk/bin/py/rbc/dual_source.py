# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""Independent, strict BAS/TZX adapters and line-specific semantic comparisons.

Original numbered BAS is the sole text source. The TZX route first reads
existing Sinclair token bytes, renders explicit ASCII byte escapes, and
round-trips through the same strict external RBC text input reader. Neither
route repairs source spelling, keyword boundaries or the archival input.
"""
from __future__ import annotations

from pathlib import Path
from tzx_ascii import LosslessConversionError
import importlib.util


class SemanticDifference(LosslessConversionError):
    pass


def validated_lines(program: bytes):
    """Reject malformed line headers rather than accepting TAP's partial parse."""
    rows = []
    p = 0
    while p < len(program):
        if p + 4 > len(program):
            raise LosslessConversionError(f'TZX BASIC truncated line header at byte {p}')
        n = int.from_bytes(program[p:p + 2], 'big')
        length = int.from_bytes(program[p + 2:p + 4], 'little')
        p += 4
        if not 0 <= n <= 9999 or length < 1 or p + length > len(program):
            raise LosslessConversionError(f'TZX BASIC malformed line {n} at byte {p - 4}')
        body = program[p:p + length]
        if body[-1] != 13:
            raise LosslessConversionError(f'Line {n}: missing Sinclair end-of-line marker')
        if rows and n <= rows[-1][0]:
            raise LosslessConversionError(f'Line {n}: non-increasing or duplicate tape line number')
        rows.append((n, body))
        p += length
    if not rows:
        raise LosslessConversionError('TZX tape contains an empty BASIC program')
    return rows


def _canonical(body: bytes, n: int, names: dict):
    """Compare all source tokens, including the exact bytes after REM.

    Only harmless keyword spacing, edge spaces around REM content, and
    Sinclair numeric caches may be ignored. A changed remark, control byte,
    internal space or glyph remains a line difference.
    """
    body = body.rstrip(b'\r') if body.endswith(b'\r') else body
    if not body.strip(b' '):
        return b''  # Same numbered line, no executable content
    out = bytearray()
    p = 0
    quoted = rem = data = False
    while p < len(body):
        c = body[p]
        if c == 34 and not rem:
            quoted = not quoted
        if c == 0xEA and not quoted and not data:
            # Keep the remark's bytes, including controls and glyphs. The original tape
            # and ROM ASCII listing can shift only inert edge spaces around the same
            # remark; interior bytes must match.
            out.append(c)
            out.extend(body[p + 1:].strip(b' '))
            break
        if c == 0xE4 and not quoted and not rem:
            data = True
        if c == 58 and not quoted and not rem:
            data = False
        if c == 14 and not quoted and not rem:
            if p + 6 > len(body):
                raise LosslessConversionError(f'Line {n}: truncated Sinclair numeric/function metadata')
            # Sinclair 48K stores the five-byte number or FN-parameter descriptor
            # after the visible source spelling.
            p += 6
            continue
        if c == 32 and not quoted and not rem and not data:
            prev = out[-1] if out else None
            q = p + 1
            while q < len(body) and body[q] == 32:
                q += 1
            next_value = body[q] if q < len(body) else None
            if prev in names or next_value in names:
                p += 1
                continue
            # A numeric cache (0E + five bytes) can sit between a visible number and the
            # following TO token. Its position is not source meaning, and LLIST inserts
            # the visible token boundary itself.
            if (prev in b'0123456789.' and next_value == 14
                    and q + 6 <= len(body)):
                q += 6
                while q < len(body) and body[q] == 32:
                    q += 1
                if q < len(body) and body[q] == 0xCC and body[q] in names:
                    p += 1
                    continue
            # A space after a closing literal quote, before PRINT's separator, is outside quoted
            # bytes and cannot change the print separator.
            if prev == 34 and next_value == 59:
                p += 1
                continue
        out.append(c)
        p += 1
    if quoted:
        raise LosslessConversionError(f'Line {n}: unmatched quote')
    return bytes(out)


def semantic_check(expected: bytes, observed: bytes, split_lines, token_names: dict, name: str):
    """Report first line differing in numeric spelling, keywords or characters."""
    left = validated_lines(expected)
    right = validated_lines(observed)
    if len(left) != len(right):
        raise SemanticDifference(f'{name}: BASIC line count differs: {len(left)} versus {len(right)}')
    for (number, a), (n, b) in zip(left, right):
        if number != n:
            raise SemanticDifference(f'{name}: BASIC line numbers differ: {number} versus {n}')
        x = _canonical(a, n, token_names)
        y = _canonical(b, n, token_names)
        if x != y:
            first = next((i for i in range(min(len(x), len(y))) if x[i] != y[i]), min(len(x), len(y)))
            raise SemanticDifference(
                f'{name}: Line {n}: semantic token/character difference at byte {first}; '
                f'BAS {x[first:first + 8].hex().upper()} versus TZX {y[first:first + 8].hex().upper()}')


def convert_tzx(tzx_file: Path, bas_file: Path, dst: Path, rbc, source, kw, fp):
    """Independent extraction, faithful round-trip, then BAS semantic check."""
    import tap
    src_name, program = tap.program_of_tap(rbc._tap_from_tzx(tzx_file))
    original = validated_lines(program)
    # Use the ROM LLIST formatter used by the independent TZX conversion tool. A second
    # lossy re-serializer can add token-adjacent whitespace, changing compiler input and SSX
    # bytes even when all executable tokens agree. The cassette gets no creative license.
    tool = Path(__file__).resolve().parent / 'rom_tzx2bas.py'
    spec = importlib.util.spec_from_file_location('zx_tzx2bas_rbc', tool)
    if spec is None or spec.loader is None:
        raise LosslessConversionError('original ROM TZX converter is unavailable')
    converter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(converter)
    tape_bytes = tzx_file.read_bytes()
    recovered = list(converter.basic_programs(tape_bytes))
    if len(recovered) != 1 or recovered[0][1] != program:
        raise LosslessConversionError('independent TZX BASIC extractors disagree')
    ascii_listing = converter.listing(tape_bytes)
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(ascii_listing, encoding='ascii')
    _, rebuilt = rbc._source_program(dst, source, kw, fp)
    semantic_check(program, rebuilt, tap.split_lines, kw.TOKEN, 'TZX conversion')
    _, authoritative = rbc._source_program(bas_file, source, kw, fp)
    semantic_check(authoritative, rebuilt, tap.split_lines, kw.TOKEN, 'BAS/TZX')
    return {'tape_program': src_name, 'source_lines': len(original),
            'source_bytes': len(program), 'converted_bytes': dst.stat().st_size}
