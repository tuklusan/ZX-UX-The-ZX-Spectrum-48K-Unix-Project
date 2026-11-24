# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""Join source opcode templates with immediate source relocation operands.

A pair is a typed complete Z80 instruction from the original compiler calls,
not a disassembled byte sequence. Missing or rewritten pairs fail closed for
whole-program assembly, while a passive audit reports their exact counts.
"""
from __future__ import annotations

from dataclasses import dataclass


class UnresolvedOpcode(ValueError):
    """Source opcode and operand cannot be safely represented together."""


@dataclass(frozen=True)
class OpcodePair:
    site: int
    template: str
    target_offset: int
    bytes_written: bytes
    overwritten: bool


def inspect_opcode_pairs(events, image: bytes, base: int, assembler):
    pairs = []
    unpaired = []
    for index, event in enumerate(events):
        if event.kind != 'opcode':
            continue
        if event.source.count('nn') != 1:
            raise UnresolvedOpcode('opcode source is not a symbolic word template')
        next_event = events[index + 1] if index + 1 < len(events) else None
        if (next_event is None or next_event.kind != 'relocation' or
                next_event.position != event.position + len(event.data)):
            unpaired.append(event.position)
            continue
        target = next_event.symbol_offset
        if not isinstance(target, int) or not 0 <= target <= 65535:
            raise UnresolvedOpcode('invalid source operand target')
        end = next_event.position + len(next_event.data)
        if event.position < 0 or end > len(image) or len(next_event.data) != 2:
            raise UnresolvedOpcode('opcode pair extends beyond native image')
        encoded = bytes(event.data + next_event.data)
        try:
            expected = bytes(assembler(event.source.replace('nn', str((base + target) & 65535))))
        except (ValueError, KeyError, TypeError) as exc:
            raise UnresolvedOpcode('source template cannot be assembled') from exc
        if encoded != expected:
            raise UnresolvedOpcode('Z80 source pair does not match emitted bytes')
        pairs.append(OpcodePair(event.position, event.source, target,
                                encoded, image[event.position:end] != encoded))
    if not pairs:
        raise UnresolvedOpcode('no typed opcode/word pairs were found')
    return tuple(pairs), tuple(unpaired)


def verify_three_opcode_passes(groups, bases):
    if len(groups) != 3 or len(bases) != 3 or len(set(bases)) != 3:
        raise UnresolvedOpcode('three distinct native bases are required')
    (first, unpaired) = groups[0]
    if not first:
        raise UnresolvedOpcode('missing source opcode pairs')
    for pairs, others in groups[1:]:
        if len(pairs) != len(first) or others != unpaired:
            raise UnresolvedOpcode('opcode source layout changed across bases')
        for a, b in zip(first, pairs):
            if (a.site, a.template, a.target_offset, a.overwritten) != (
                    b.site, b.template, b.target_offset, b.overwritten):
                raise UnresolvedOpcode('opcode identities or source addresses changed')
    return {'paired_instructions': len(first),
            'paired_instruction_bytes': sum(len(x.bytes_written) for x in first),
            'unpaired_opcode_sites': list(unpaired[:16]),
            'unpaired_opcode_count': len(unpaired),
            'overwritten_pair_count': sum(x.overwritten for x in first),
            'verified_distinct_bases': len(set(bases)),
            'fully_symbolic': not unpaired and not any(x.overwritten for x in first)}
