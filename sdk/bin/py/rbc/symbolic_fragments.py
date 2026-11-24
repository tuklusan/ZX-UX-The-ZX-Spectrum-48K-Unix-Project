# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""Split live HiSoft inline assembly at its original source statements.

An inline defb/defw is protected source data, even when its bytes resemble
executable instructions. No decoded output or post-link pattern scan is used.
Only source instruction events are split; opaque runtime emitters remain opaque.
"""
from __future__ import annotations

from dataclasses import dataclass


class FragmentBoundaryError(ValueError):
    """A source instruction fragment cannot be identified without guessing."""


@dataclass(frozen=True)
class Fragment:
    site: int
    end: int
    kind: str
    source: str
    encoded: bytes
    overwritten: bool = False


def inspect_fragments(events, image: bytes, text_end: int, assembler):
    """Verify each statement in a source `emit` against the original bytes."""
    if not isinstance(image, bytes) or not 0 <= text_end <= len(image):
        raise FragmentBoundaryError('invalid executable source extent')
    result = []
    for event in events:
        if event.kind != 'instruction':
            continue
        if (not isinstance(event.source, str) or
                not isinstance(event.position, int) or
                not isinstance(event.data, bytes)):
            raise FragmentBoundaryError('malformed source instruction')
        parts = event.source.split(';')
        if any(not part.strip() for part in parts):
            raise FragmentBoundaryError('empty inline assembly statement')
        offset = event.position
        assembled = bytearray()
        for part in parts:
            source = part.strip()
            op = source.split(None, 1)[0].lower()
            if op in ('defb', 'defw'):
                kind = 'inline-data'
            else:
                kind = 'instruction'
            try:
                encoded = bytes(assembler(source))
            except (ValueError, TypeError, KeyError, IndexError) as exc:
                raise FragmentBoundaryError('invalid source fragment assembly') from exc
            if not encoded:
                raise FragmentBoundaryError('empty source fragment encoding')
            end = offset + len(encoded)
            if not 0 <= offset < end <= text_end:
                raise FragmentBoundaryError('fragment outside executable extent')
            result.append(Fragment(offset, end, kind, source, encoded,
                                   image[offset:end] != encoded))
            assembled.extend(encoded)
            offset = end
        if (assembled != event.data or
                offset != event.position + len(event.data)):
            raise FragmentBoundaryError('fragment sequence differs from HiSoft emission')
    if not result:
        raise FragmentBoundaryError('no source instruction fragments')
    sites = set()
    for fragment in result:
        extent = set(range(fragment.site, fragment.end))
        if sites.intersection(extent):
            raise FragmentBoundaryError('overlapping source instruction fragments')
        sites.update(extent)
    return tuple(result)


def inspect_final_fragments(events, image: bytes, text_end: int, assembler):
    """Audit surviving compiler instructions after complete source rewrites.

    A compiler rewind may discard an entire old instruction emission. The
    chronological new source must replace every byte of that emission with
    independently assembled instructions. Partial rewrites, opaque writers,
    and overwritten inline data remain unresolved. Direct address patches
    are deliberately excluded; their separate three-base check is required.
    """
    last_writer = {}
    originals = []
    fragment_kind = {}
    for index, event in enumerate(events):
        if event.kind == 'direct-write':
            continue
        if (not isinstance(event.position, int) or
                not isinstance(event.data, bytes) or
                not event.data or event.position < 0 or
                event.position + len(event.data) > len(image)):
            raise FragmentBoundaryError('invalid historical source emission')
        for position in range(event.position, event.position + len(event.data)):
            last_writer[position] = index
        if event.kind == 'instruction':
            parts = inspect_fragments([event], image, text_end, assembler)
            originals.append((index, event, parts))
            for fragment in parts:
                for position in range(fragment.site, fragment.end):
                    fragment_kind[(index, position)] = fragment.kind
    if not originals:
        raise FragmentBoundaryError('no source instruction fragments')
    live = []
    for index, event, fragments in originals:
        owners = [last_writer[position]
                  for position in range(event.position,
                                        event.position + len(event.data))]
        if all(owner == index for owner in owners):
            live.extend(fragments)
            continue
        if any(owner == index for owner in owners):
            raise FragmentBoundaryError('partial historical instruction rewrite')
        if any(fragment.kind != 'instruction' for fragment in fragments):
            raise FragmentBoundaryError('historical protected inline data rewrite')
        for position, owner in zip(range(event.position,
                                         event.position + len(event.data)), owners):
            if owner <= index:
                raise FragmentBoundaryError('historical source owner is out of order')
            replacement = events[owner]
            if replacement.kind == 'instruction':
                if fragment_kind.get((owner, position)) != 'instruction':
                    raise FragmentBoundaryError('historical instruction replaced by untyped inline data')
            elif replacement.kind not in ('opcode', 'relocation', 'word',
                                          'byte', 'binary'):
                raise FragmentBoundaryError('historical instruction replaced by untyped source')
            # Final opcode and numeric writers are not promoted to typed code. Full source
            # ownership still independently rejects unresolved bytes.
    positions = set()
    for fragment in live:
        extent = set(range(fragment.site, fragment.end))
        if positions.intersection(extent):
            raise FragmentBoundaryError('overlapping surviving source fragments')
        positions.update(extent)
    if not live:
        raise FragmentBoundaryError('no surviving source instructions')
    return tuple(live)

def verify_three_fragment_passes(groups, bases):
    """Match source statement boundaries over three distinct load addresses."""
    if len(groups) != 3 or len(bases) != 3 or len(set(bases)) != 3:
        raise FragmentBoundaryError('three distinct compilation bases required')
    first = groups[0]
    footprint = lambda records: tuple((f.site, f.end, f.kind, f.overwritten)
                                      for f in records)
    if any(footprint(group) != footprint(first) for group in groups[1:]):
        raise FragmentBoundaryError('source fragment boundaries changed across bases')
    if any(f.source != g.source or f.encoded != g.encoded
           for group in groups[1:] for f, g in zip(first, group)
           if f.kind == 'inline-data'):
        raise FragmentBoundaryError('protected inline bytes changed across bases')
    changed_code = sum(any(g[i].source != first[i].source or
                           g[i].encoded != first[i].encoded for g in groups[1:])
                       for i, f in enumerate(first) if f.kind == 'instruction')
    protected = tuple(f for f in first if f.kind == 'inline-data')
    code = tuple(f for f in first if f.kind == 'instruction')
    return {
        'source_statement_count': len(first),
        'instruction_statements': len(code),
        'inline_data_statements': len(protected),
        'instruction_bytes': sum(len(f.encoded) for f in code),
        'protected_inline_bytes': sum(len(f.encoded) for f in protected),
        'overwritten_source_fragments': sum(f.overwritten for f in first),
        'code_statements_varying_across_bases': changed_code,
        'complete_program_symbolic': False,
    }
