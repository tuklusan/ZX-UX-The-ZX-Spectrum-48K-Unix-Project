# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""Verify typed HiSoft relocation events across all three native builds.

Relocation operands come from the source emitter before byte encoding. No
post-link disassembly, guessed operand widths, or binary patching is allowed.
Repeated and subsequently overwritten operands remain explicitly unresolved.
"""
from __future__ import annotations

from dataclasses import dataclass

from stkend_end_pointer import original_stkend_end_marker


class UnresolvedRelocation(ValueError):
    """A source relocation does not have stable, verifiable identity."""


@dataclass(frozen=True)
class RelocationWord:
    site: int
    target_offset: int
    source: str
    encoded: int
    overwritten: bool


def inspect_relocations(events, image: bytes, base: int, bss: int):
    """Check actual source operands without interpreting arbitrary code bytes."""
    if not (0 <= base <= 65535 and 0 <= bss <= 65535):
        raise UnresolvedRelocation('invalid native address or BSS size')
    words = []
    for event in events:
        if event.kind != 'relocation':
            continue
        if (not isinstance(event.symbol_offset, int)
                or not 0 <= event.symbol_offset <= 65535
                or not 0 <= event.position <= len(image) - 2
                or len(event.data) != 2):
            raise UnresolvedRelocation('invalid typed relocation event')
        site = event.position
        target = event.symbol_offset
        if (target >= len(image) + bss and
                not original_stkend_end_marker(events, image, base, bss, site, target)):
            raise UnresolvedRelocation('relocation points beyond code and BSS')
        encoded = (base + target) & 65535
        if event.data != encoded.to_bytes(2, 'little'):
            raise UnresolvedRelocation('source relocation encoding does not match base')
        words.append(RelocationWord(site, target, event.source,
                                    encoded, image[site:site + 2] != event.data))
    if not words:
        raise UnresolvedRelocation('no relocation events captured')
    return tuple(words)


def verify_three_builds(groups, bases):
    """Prove every source operand follows actual distinct link bases."""
    if len(groups) != 3 or len(bases) != 3 or len(set(bases)) != 3:
        raise UnresolvedRelocation('three different link bases required')
    first = groups[0]
    if not first:
        raise UnresolvedRelocation('missing typed source relocations')
    for index, current in enumerate(groups[1:], 1):
        if len(current) != len(first):
            raise UnresolvedRelocation('relocation sequence changed across builds')
        delta = (bases[index] - bases[0]) & 65535
        for a, b in zip(first, current):
            if (a.site, a.target_offset, a.source, a.overwritten) != (
                    b.site, b.target_offset, b.source, b.overwritten):
                raise UnresolvedRelocation('relocation target or site differs across bases')
            if b.encoded != (a.encoded + delta) & 65535:
                raise UnresolvedRelocation('relocation does not follow load-base delta')
    sites = [w.site for w in first]
    overlapping = len(sites) - len(set(sites))
    overwritten = sum(w.overwritten for w in first)
    # This proves identity, not that all executable sources are symbolic.
    return {'source_relocation_events': len(first),
            'distinct_relocation_sites': len(set(sites)),
            'repeated_relocation_sites': overlapping,
            'overwritten_relocation_events': overwritten,
            'verified_encoded_relocation_bytes': 2 * len(first),
            'verified_distinct_bases': len(set(bases)),
            'fully_symbolic': not overlapping and not overwritten}
