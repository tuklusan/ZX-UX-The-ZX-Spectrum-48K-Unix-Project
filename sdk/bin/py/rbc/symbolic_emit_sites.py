# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""Check stable HiSoft compiler call sites for the final emission pass.

Call-site identifiers help distinguish literal values from addresses during
future type checking. A site name alone never licenses a numeric relocation.
"""
from __future__ import annotations

from dataclasses import dataclass


class EmitSiteError(ValueError):
    """An emission is missing its original compiler call site."""


_SOURCE_KINDS = frozenset(('instruction', 'opcode', 'relocation',
                           'word', 'byte', 'binary'))


@dataclass(frozen=True)
class SourceSite:
    position: int
    size: int
    kind: str
    site: str
    producer_pcs: tuple[int, ...] | None = None


def inspect_emit_sites(events) -> tuple[SourceSite, ...]:
    """Retain source call sites; do not infer roles from generated opcodes."""
    result = []
    for event in events:
        name = getattr(event, 'source_site', None)
        # Runtime literals are protected data, not Z80 instructions, but match
        # their writer-PC sequences across all three compiler passes. DEF FN
        # and ordinary inline bytes have no runtime PC and remain outside this
        # executable source-call inventory.
        runtime_literal = (event.kind == 'inline-data' and
                           isinstance(name, str) and
                           name.startswith('runtime_pc:'))
        if event.kind not in _SOURCE_KINDS and not runtime_literal:
            continue
        if not isinstance(name, str) or ':' not in name:
            raise EmitSiteError('source emission lacks compiler call site')
        method, line = name.rsplit(':', 1)
        if not method.isidentifier() or not line.isdecimal():
            raise EmitSiteError('invalid compiler call site')
        if method == 'runtime_pc':
            if int(line) > 0xffff:
                raise EmitSiteError('runtime producer PC outside Z80 address space')
        elif int(line) <= 0:
            raise EmitSiteError('invalid compiler call site')
        if not isinstance(event.position, int) or event.position < 0:
            raise EmitSiteError('negative source emission position')
        if not isinstance(event.data, bytes) or not event.data:
            raise EmitSiteError('source emission has no bytes')
        producers = getattr(event, 'producer_pcs', None)
        if method == 'runtime_pc':
            if (not isinstance(producers, tuple) or len(producers) != len(event.data)
                    or producers[0] != int(line) or
                    any(not isinstance(pc, int) or not 0 <= pc <= 0xffff
                        for pc in producers)):
                raise EmitSiteError('missing verified runtime producer PC sequence')
        elif producers is not None:
            raise EmitSiteError('compiler call has unexpected runtime PC sequence')
        result.append(SourceSite(event.position, len(event.data), event.kind,
                                 name, producers))
    return tuple(result)


def verify_three_emit_sites(groups, bases) -> dict:
    """Require identical source calls and output extents at three link bases."""
    if len(groups) != 3 or len(bases) != 3 or len(set(bases)) != 3:
        raise EmitSiteError('three distinct native bases required')
    first = groups[0]
    if any(group != first for group in groups[1:]):
        raise EmitSiteError('compiler source call sites changed across bases')
    return {'source_emissions': len(first),
            'source_call_sites': len({e.site for e in first}),
            'source_emitted_bytes': sum(e.size for e in first),
            'typed_absolute_operands': False}
