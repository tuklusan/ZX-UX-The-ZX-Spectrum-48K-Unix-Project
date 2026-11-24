# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""Classify HiSoft's live two-byte direct writes before symbolic assembly.

A source emitter's method identifies a word-length field or control target.
No completed executable is disassembled or rewritten. Unrecognized writes
fail closed. Cross-pass target checks are required before relocation is trusted.
"""
from __future__ import annotations

from dataclasses import dataclass
import re


class UnresolvedSourcePatch(ValueError):
    """A source write cannot be represented as an exact typed word."""


@dataclass(frozen=True)
class SourceWord:
    site: int
    source: str
    kind: str
    value: int
    target: int | None


_TYPES = {'emit_string_inline': 'literal-length',
          'st_next': 'control-target',
          'st_deffn': 'control-target',
          'end_of_line': 'control-target',
          'spectrum_for': 'control-target',
          'spectrum_pass': 'control-target'}


# Only compiler-owned, source-typed emitters can supersede an old patch. Bytes from
# DATA/runtime writers, another direct store, or unknown methods cannot justify
# discarding a previously captured source word.
_REWRITE_KINDS = frozenset(('instruction', 'opcode', 'relocation',
                            'word', 'byte', 'binary'))


def from_emissions(events, image: bytes, code_base: int,
                   text_end: int) -> tuple[SourceWord, ...]:
    """Return final source words and check fully superseded earlier writes.

    HiSoft may rewind its code pointer after writing an inline string length,
    then emit a different instruction over *both* bytes of that length. The
    old source write remains in the chronological trace, but is not part of
    the final program. Both bytes must be owned by later typed emitters, with
    byte-exact agreement; partial rewrites and unknown owners fail closed.
    """
    observed = []
    writers = {}
    for index, event in enumerate(events):
        if event.kind == 'direct-write':
            if not 1 <= len(event.data) <= 2:
                raise UnresolvedSourcePatch('unexpected direct source store length')
            observed.extend((event.position + n, event.source, value, index)
                            for n, value in enumerate(event.data))
        if (isinstance(event.position, int) and
                isinstance(event.data, bytes)):
            for n, value in enumerate(event.data):
                writers[event.position + n] = (index, event.kind, value)
    # A prior loop target may be replaced by a newly emitted JP after a compiler
    # rewind, followed by a second patch to that same word. The earlier patch is no
    # longer part of the program. Require the intervening original JP/CALL
    # placeholder as an independently captured whole source instruction; otherwise
    # overlapping direct words are always rejected.
    discarded = set()
    pairs = [observed[n:n+2] for n in range(0, len(observed), 2)]
    for index, pair in enumerate(pairs):
        if len(pair) != 2:
            raise UnresolvedSourcePatch('unpaired direct source byte')
        start = pair[0][0]
        for earlier in range(index):
            previous = pairs[earlier]
            if {start, pair[1][0]}.isdisjoint({previous[0][0], previous[1][0]}):
                continue
            if (previous[0][0] != start or previous[1][0] != pair[1][0] or
                    earlier in discarded):
                raise UnresolvedSourcePatch('overlapping source patch bytes')
            low = previous[1][3] + 1
            high = pair[0][3]
            window = events[low:high]
            # HiSoft can rewrite a string literal as a new CALL+inline length
            # at the same location. In this layout the older length has been
            # wholly replaced by an independently recorded, typed two-byte
            # word after the CALL/relocation pair. A partial or untyped
            # rewrite remains forbidden.
            original_placeholder = any(
                event.kind == 'instruction' and event.position == start - 1 and
                len(event.data) == 3 and
                re.fullmatch(r'(?:jp|call)\s+(?:(?:nz|z|nc|c|po|pe|p|m)\s*,\s*)?(?:0|\$ffff)',
                             event.source.strip().lower())
                for event in window)
            inline_replacement = any(
                event.kind == 'word' and event.position == start and
                len(event.data) == 2 for event in window) and any(
                event.kind == 'opcode' and event.position == start - 3 and
                event.data == b'\xcd' for event in window) and any(
                event.kind == 'relocation' and event.position == start - 2 and
                len(event.data) == 2 for event in window)
            if not (original_placeholder or inline_replacement):
                raise UnresolvedSourcePatch('overlapping source patch bytes')
            discarded.add(earlier)
    groups = []
    occupied = set()
    i = 0
    while i < len(observed):
        if i // 2 in discarded:
            i += 2
            continue
        first = observed[i]
        if i + 1 == len(observed):
            raise UnresolvedSourcePatch('unpaired direct source byte')
        second = observed[i + 1]
        if (first[1] not in _TYPES or second[1] != first[1] or
                second[0] != first[0] + 1):
            raise UnresolvedSourcePatch('direct source word boundaries unresolved')
        if not (0 <= first[0] < len(image) - 1):
            raise UnresolvedSourcePatch('direct source patch outside image')
        if first[0] + 1 >= text_end:
            raise UnresolvedSourcePatch('direct source patch outside executable text')
        footprint = {first[0], second[0]}
        if occupied.intersection(footprint):
            raise UnresolvedSourcePatch('overlapping source patch bytes')
        occupied.update(footprint)
        word = (first[2], second[2])
        final = image[first[0]:second[0] + 1]
        owners = (writers[first[0]], writers[second[0]])
        if (owners[0][0] == first[3] and owners[1][0] == second[3]):
            if final != bytes(word):
                raise UnresolvedSourcePatch('source write changed after capture')
        else:
            # A later emitter must replace *all* bytes, even if one has the same value. A later
            # direct store or a partial overlap is unsafe.
            if not all(owner[0] > original[3] and
                       owner[1] in _REWRITE_KINDS and
                       owner[2] == final[n]
                       for n, (owner, original) in enumerate(zip(owners, (first, second)))):
                raise UnresolvedSourcePatch('source write changed after capture')
            i += 2
            continue
        value = first[2] | second[2] << 8
        kind = _TYPES[first[1]]
        target = None
        if kind == 'control-target':
            target = (value - code_base) & 65535
            if target >= text_end:
                raise UnresolvedSourcePatch('computed control target outside code')
        groups.append(SourceWord(first[0], first[1], kind, value, target))
        i += 2
    return tuple(groups)


def verify_three_passes(words, builds) -> dict:
    """All source addresses must relocate; source byte lengths must not."""
    if len(words) != 3 or len(builds) != 3:
        raise UnresolvedSourcePatch('three native build passes required')
    if len({run.base for run in builds}) != 3:
        raise UnresolvedSourcePatch('native build bases must be distinct')
    base = builds[0].base
    first = words[0]
    for candidate, run in zip(words[1:], builds[1:]):
        if len(candidate) != len(first):
            raise UnresolvedSourcePatch('source word sites changed between passes')
        delta = run.base - base
        for old, new in zip(first, candidate):
            if (old.site, old.source, old.kind) != (new.site, new.source, new.kind):
                raise UnresolvedSourcePatch('source word identity changed')
            expected = ((old.value + delta) & 65535) if old.kind == 'control-target' else old.value
            if new.value != expected or (new.target != old.target):
                raise UnresolvedSourcePatch('source word relocation did not track compile base')
    types = {name: sum(w.kind == name for w in first)
             for name in ('literal-length', 'control-target')}
    return {'verified_source_words': len(first),
            'verified_patch_bytes': 2 * len(first),
            'word_kinds': types}
