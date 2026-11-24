# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""Fail-closed conversion of explicitly typed HiSoft runtime-emitter sources.

Each statement must be supplied independently of the emitted bytes, including
its emitting Z80 PC. A runtime write trace can verify source ownership but
cannot infer an instruction, a symbol, or an opaque resource from output.
Unidentified producers and rewrites remain unresolved.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Callable, Iterable


class RuntimeSourceError(ValueError):
    """The original runtime emitter has no fully verified typed source."""


@dataclass(frozen=True)
class RuntimeStatement:
    position: int
    emitter_pc: int
    kind: str                    # instruction, literal, or relocated
    source: str                  # original mnemonic or defb/defw statement
    symbol_offset: int | None = None
    write_pcs: tuple[int, ...] | None = None  # exact source PC of each output byte


def typed_runtime_events(writes: Iterable, statements: Iterable[RuntimeStatement],
                         image: bytes, start: int, end: int, base: int,
                         assembler: Callable[[str], Iterable[int]]):
    """Verify source statements against every actual runtime staging write.

    Return regular HiSoft capture events for existing source-boundary audits.
    A relocated instruction must have one terminal 16-bit ``nn`` operand.
    No byte is promoted from the completed program or a decoded binary.
    """
    from symbolic_capture import Emission
    from symbolic_z80 import _canonical_source_line, _INSTRUCTIONS

    if (not isinstance(image, bytes) or type(start) is not int or
            type(end) is not int or type(base) is not int or
            not 0 <= start <= end or len(image) != end - start or
            not 0 <= base <= 0xffff or base + end > 0x10000):
        raise RuntimeSourceError('invalid runtime output or link address')
    sources = tuple(statements)
    records = tuple(writes)
    if not sources or (end > start and not records):
        raise RuntimeSourceError('runtime producer source or write trace missing')
    seen = set()
    site_at = {}
    for write in records:
        position = getattr(write, 'position', None)
        pc = getattr(write, 'emitter_pc', None)
        value = getattr(write, 'value', None)
        if (type(position) is not int or not start <= position < end or
                type(pc) is not int or not 0 <= pc <= 0xffff or
                type(value) is not int or not 0 <= value <= 255):
            raise RuntimeSourceError('invalid or out-of-range runtime write')
        if position in seen:
            raise RuntimeSourceError('runtime rewrite lacks typed patch source')
        if image[position - start] != value:
            raise RuntimeSourceError('runtime writer disagrees with output')
        seen.add(position)
        site_at[position] = pc
    if len(seen) != end - start:
        raise RuntimeSourceError('runtime source has unobserved bytes')

    result = []
    cursor = start
    for statement in sources:
        if not isinstance(statement, RuntimeStatement):
            raise RuntimeSourceError('invalid typed source statement')
        if type(statement.position) is not int or statement.position != cursor:
            raise RuntimeSourceError('runtime source has gap, overlap or wrong order')
        if (type(statement.emitter_pc) is not int or
                not 0 <= statement.emitter_pc <= 0xffff or
                not isinstance(statement.source, str) or
                not statement.source.strip() or not statement.source.isascii() or
                any(ord(c) < 32 or ord(c) == 127 for c in statement.source)):
            raise RuntimeSourceError('runtime source location or statement invalid')
        # A semicolon inside a quoted data literal is a byte, not a comment. The source provider
        # may not slip untyped assembly after a comment.
        try:
            full_source = _canonical_source_line(statement.source)
            without_comment = _canonical_source_line(statement.source,
                                                     strip_comment=True)
        except ValueError as exc:
            raise RuntimeSourceError('runtime source has an invalid quote') from exc
        if full_source != without_comment:
            raise RuntimeSourceError('runtime source has untyped comment')
        kind = statement.kind
        source = statement.source.strip()
        if kind not in ('instruction', 'literal', 'relocated'):
            raise RuntimeSourceError('runtime source kind not typed')
        mnemonic = without_comment.split(None, 1)[0]
        if kind == 'literal':
            if mnemonic not in ('defb', 'defw'):
                raise RuntimeSourceError('runtime literal lacks source data directive')
        elif mnemonic not in _INSTRUCTIONS:
            # Assembler aliases such as DB, DW, ORG and a label definition must never
            # become optimizer-reachable instructions merely because a supplied
            # assembler returns matching bytes.
            raise RuntimeSourceError('runtime executable source is not a Z80 instruction')
        if kind == 'relocated':
            offset = statement.symbol_offset
            operands = tuple(re.finditer(r'(?<![a-zA-Z0-9_])nn(?![a-zA-Z0-9_])',
                                             source, flags=re.IGNORECASE))
            if (type(offset) is not int or offset < 0 or
                    len(operands) != 1 or '"' in source or "'" in source):
                raise RuntimeSourceError('runtime relocated operand has no target')
            # The target may be in another emitter, BASIC DATA or the BSS. Whole-program symbol
            # resolution checks actual storage bounds.
            target = base + offset
            if target > 0xffff:
                raise RuntimeSourceError('runtime relocation outside address space')
            mark = operands[0]
            encoded_source = (source[:mark.start()] + str(target) +
                              source[mark.end():])
        else:
            if statement.symbol_offset is not None:
                raise RuntimeSourceError('runtime address has no relocation type')
            encoded_source = source
        try:
            raw = assembler(encoded_source)
            # bytes(integer) silently creates that many zero bytes; booleans and coerced
            # elements are not independent assembled instructions.
            if type(raw) in (int, bool):
                raise TypeError('assembler returned a byte count, not bytes')
            if isinstance(raw, (bytes, bytearray)):
                encoded = bytes(raw)
            else:
                parts = tuple(raw)
                if any(type(part) is not int or not 0 <= part <= 255
                       for part in parts):
                    raise TypeError('assembler returned non-byte elements')
                encoded = bytes(parts)
        except (ValueError, KeyError, IndexError, TypeError, OverflowError) as exc:
            raise RuntimeSourceError('runtime source cannot be assembled') from exc
        if not encoded or cursor + len(encoded) > end:
            raise RuntimeSourceError('runtime source extends outside output')
        if encoded != image[cursor - start:cursor - start + len(encoded)]:
            raise RuntimeSourceError('runtime source encoding differs from bytes')
        sites = (statement.write_pcs if statement.write_pcs is not None else
                 (statement.emitter_pc,) * len(encoded))
        if (not isinstance(sites, tuple) or len(sites) != len(encoded) or
                not sites or sites[0] != statement.emitter_pc or
                any(type(site) is not int or not 0 <= site <= 0xffff
                    for site in sites)):
            raise RuntimeSourceError('runtime source PC sequence invalid')
        if any(site_at[p] != sites[p - cursor]
               for p in range(cursor, cursor + len(encoded))):
            raise RuntimeSourceError('runtime write PC differs from typed producer')
        if kind == 'relocated':
            if (len(encoded) < 3 or
                    encoded[-2:] != target.to_bytes(2, 'little')):
                raise RuntimeSourceError('runtime operand is not terminal 16-bit address')
            split = len(encoded) - 2
            result.append(Emission(cursor, 'opcode', source, encoded[:split],
                                   source_site=f'runtime_pc:{sites[0]}',
                                   producer_pcs=sites[:split]))
            result.append(Emission(cursor + split, 'relocation', str(offset),
                                   encoded[split:], offset,
                                   source_site=f'runtime_pc:{sites[split]}',
                                   producer_pcs=sites[split:]))
        else:
            # Original byte resources stay protected DATA, even when their values decode
            # to legal Z80 instructions (HALT, RST, etc.).
            result.append(Emission(cursor,
                                   'inline-data' if kind == 'literal' else 'instruction',
                                   source, encoded,
                                   source_site=f'runtime_pc:{sites[0]}',
                                   producer_pcs=sites))
        cursor += len(encoded)
    if cursor != end:
        raise RuntimeSourceError('runtime source does not cover complete emitter')
    return tuple(result)
