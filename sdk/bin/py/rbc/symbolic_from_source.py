# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""Translate completely typed HiSoft emission sources to relocatable Z80.

The input is a source-ownership map, never a decoded or patched executable.
Refuse any unresolved byte, entry, branch, operand, or section boundary.
Runtime emitters and direct stores need their own typed sources first.
"""
from __future__ import annotations

import re

from symbolic_source_boundaries import (SourceBoundaryError,
                                        inspect_source_boundaries,
                                        replace_typed_address)
from symbolic_relative_branches import RelativeBranchError, inspect_relative_branches
from symbolic_z80 import SymbolicProgram


class UnresolvedSourceProgram(ValueError):
    """An original producer lacks sufficient type information for assembly."""


_NUMERIC = re.compile(r'(?<![\w])(?:[-+]?(?:0x[0-9a-f]+|\$[0-9a-f]+|[0-9]+))',
                      re.IGNORECASE)
_SAFE_IMMEDIATE = re.compile(
    r'(?:ld\s+(?:a|b|c|d|e|h|l|\(hl\))\s*,|(?:and|or|xor|cp|sub)\s+|'
    r'(?:add|adc|sbc)\s+a\s*,|(?:bit|res|set)\s+|rst\s+)'
    r'(?:[-+]?(?:0x[0-9a-f]+|\$[0-9a-f]+|[0-9]+))'
    r'(?:\s*,\s*(?:a|b|c|d|e|h|l|\(hl\)))?\Z', re.IGNORECASE)


_ROM_BRANCH = re.compile(
    r'(?:jp|call)\s+(?:(?:nz|z|nc|c|po|pe|p|m)\s*,\s*)?'
    r'(\$[0-9a-f]+|0x[0-9a-f]+|[0-9]+)\Z', re.IGNORECASE)


def _fixed_rom_branch(source: str) -> bool:
    """Retain only direct, constant targets inside the 16K ZX Spectrum ROM."""
    match = _ROM_BRANCH.fullmatch(source.strip())
    if match is None:
        return False
    operand = match.group(1)
    value = (int(operand[1:], 16) if operand.startswith('$') else
             int(operand, 16) if operand.lower().startswith('0x') else
             int(operand, 10))
    return 0 <= value < 0x4000


def _validate_static_instruction(source: str) -> None:
    """Never carry an untyped absolute address through native relocation."""
    op = source.split(None, 1)[0].lower()
    if op in ('jp', 'call', 'jr', 'djnz'):
        if op in ('jp', 'call') and _fixed_rom_branch(source):
            return
        raise UnresolvedSourceProgram('branch lacks an explicit symbolic target')
    if _NUMERIC.search(source) and not _SAFE_IMMEDIATE.fullmatch(source.strip()):
        raise UnresolvedSourceProgram('numeric operand has no verified address type')


def from_source(events, image: bytes, base: int, text_end: int, bss: int,
                assembler, *, entry_offsets=(0,)) -> SymbolicProgram:
    """Construct an entire typed source image and explicit entry labels."""
    try:
        ownership = inspect_source_boundaries(events, image, base, text_end,
                                              bss, assembler)
    except SourceBoundaryError as exc:
        raise UnresolvedSourceProgram(str(exc)) from exc
    if not ownership.fully_typed:
        raise UnresolvedSourceProgram(
            f'unresolved source bytes={ownership.unresolved_bytes}, '
            f'gaps={len(ownership.gaps)}, overlaps={len(ownership.overlaps)}')
    spans = sorted(ownership.spans, key=lambda s: s.start)
    if not spans or spans[0].start != 0 or spans[-1].end != len(image):
        raise UnresolvedSourceProgram('source sections do not cover complete image')
    if any(a.end != b.start for a, b in zip(spans, spans[1:])):
        raise UnresolvedSourceProgram('source section boundaries are not contiguous')
    if not entry_offsets or entry_offsets[0] != 0 or len(set(entry_offsets)) != len(entry_offsets):
        raise UnresolvedSourceProgram('start and distinct source entries required')

    instructions = {s.start for s in spans if s.kind in ('instruction',
                                                        'instruction-relocated')}
    if any(entry not in instructions for entry in entry_offsets):
        raise UnresolvedSourceProgram('entry does not name a source instruction')
    try:
        relatives = inspect_relative_branches(spans, text_end, assembler)
    except RelativeBranchError as exc:
        raise UnresolvedSourceProgram(str(exc)) from exc
    targets = {s.target for s in spans
               if s.kind in ('instruction-relocated', 'table-relocated')}
    if None in targets:
        raise UnresolvedSourceProgram('relocation target is missing')
    if any(t < 0 or t >= len(image) + bss for t in targets):
        raise UnresolvedSourceProgram('relocation points outside program storage')
    for span in spans:
        if span.kind == 'data-source' and span.start < text_end:
            raise UnresolvedSourceProgram('source DATA crosses executable boundary')
        if span.kind == 'inline-data' and span.end > text_end:
            raise UnresolvedSourceProgram('inline literal crosses BASIC DATA boundary')
        if span.kind != 'instruction-relocated':
            continue
        op = span.source.split(None, 1)[0].lower()
        if op in ('jp', 'call') and span.target not in instructions:
            raise UnresolvedSourceProgram('branch target lacks a source instruction')
        if span.target < text_end and span.target not in instructions:
            raise UnresolvedSourceProgram('source relocation targets inline literal')
    marks = set(entry_offsets) | targets | {branch.target for branch in relatives.values()}
    for t in marks:
        if t < text_end and t not in instructions:
            raise UnresolvedSourceProgram('text label falls inside source instruction')
    def name(at):
        return 'start' if at == 0 else f'source_{at:04x}'

    program = SymbolicProgram()
    current = 'text'
    offset = 0
    for span in spans:
        desired = 'text' if span.start < text_end else 'data'
        if desired != current:
            program.section(desired)
            current = desired
        if span.start != offset:
            raise UnresolvedSourceProgram('unowned image byte')
        if span.start in marks:
            program.label(name(span.start), entry=span.start in entry_offsets)
        if span.kind in ('instruction', 'instruction-relocated'):
            if span.kind == 'instruction-relocated':
                source = replace_typed_address(span.source, name(span.target))
                if source is None:
                    raise UnresolvedSourceProgram('source relocation placeholder missing')
            else:
                relative = relatives.get(span.start)
                if relative is not None:
                    source = relative.opcode + (' ' if relative.opcode in ('jr', 'djnz') else ',') + name(relative.target)
                else:
                    source = span.source
                    _validate_static_instruction(source)
            program.instruction(source)
        elif span.kind == 'table-relocated':
            program.reference(name(span.target))
        elif span.kind in ('inline-data', 'data-source'):
            # Split protected source data only where an explicit typed label lands.
            stops = sorted(t for t in marks if span.start < t < span.end)
            begin = span.start
            for end in (*stops, span.end):
                program.binary(image[begin:end])
                # A target at span.end belongs to the following producer; only labels
                # strictly inside protected data are inserted here. Labelling the
                # boundary twice breaks a native link even when both source producers and
                # the target are fully verified.
                if end in stops:
                    program.label(name(end), entry=end in entry_offsets)
                begin = end
        else:
            raise UnresolvedSourceProgram('non-symbolic source producer')
        offset = span.end
    if offset != len(image):
        raise UnresolvedSourceProgram('assembled image length mismatch')
    if bss:
        program.section('bss')
        boundary = len(image)
        for at in sorted(t for t in marks if len(image) <= t < len(image) + bss):
            program.reserve(at - boundary)
            program.label(name(at))
            boundary = at
        program.reserve(len(image) + bss - boundary)
    elif any(t >= len(image) for t in marks):
        raise UnresolvedSourceProgram('BSS relocation without BSS')
    program.assembly()  # Require ordered sections, defined entries and symbols.
    return program
