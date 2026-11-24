# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""Resolve HiSoft source-level JR and DJNZ displacements to Z80 labels.

A byte displacement describes a source instruction, not an absolute address.
A branch into data, a rewritten instruction, or an unknown target fails closed.
No finished executable is decoded to infer branch locations.
"""
from __future__ import annotations

from dataclasses import dataclass
import re


class RelativeBranchError(ValueError):
    """A source relative branch lacks a verified instruction target."""


@dataclass(frozen=True)
class RelativeBranch:
    site: int
    target: int
    source: str
    opcode: str


_NUMBER = re.compile(r'([+-]?)(?:([0-9]+)|(0x[0-9a-f]+)|(\$[0-9a-f]+))\Z',
                     re.IGNORECASE)


def _displacement(text: str) -> int:
    match = _NUMBER.fullmatch(text.strip())
    if match is None:
        raise RelativeBranchError('relative branch needs a source displacement')
    sign, decimal, prefixed, dollar = match.groups()
    number = int(decimal, 10) if decimal is not None else int(
        prefixed if prefixed is not None else dollar[1:], 16)
    amount = -number if sign == '-' else number
    if not -128 <= amount <= 127:
        raise RelativeBranchError('relative branch displacement out of range')
    return amount


def inspect_relative_branches(spans, text_end: int, assembler):
    """Return site -> typed branch for every explicit source JR or DJNZ.

    Branch destinations must start a source-owned instruction. The original
    displacement and full two-byte encoding are checked independently of ras.
    """
    if not isinstance(text_end, int) or text_end < 0:
        raise RelativeBranchError('invalid source code extent')
    instructions = {span.start for span in spans
                    if span.kind in ('instruction', 'instruction-relocated')
                    and 0 <= span.start < span.end <= text_end}
    result = {}
    for span in spans:
        if span.kind != 'instruction':
            continue
        source = span.source.strip()
        opcode = source.split(None, 1)[0].lower() if source else ''
        if opcode not in ('jr', 'djnz'):
            continue
        operands = source[len(opcode):].strip().split(',')
        if opcode == 'jr' and len(operands) == 2:
            condition = operands[0].strip().lower()
            if condition not in ('nz', 'z', 'nc', 'c'):
                raise RelativeBranchError('invalid source JR condition')
            displacement = _displacement(operands[1])
            instruction = f'jr {condition}'
        elif len(operands) == 1:
            displacement = _displacement(operands[0])
            instruction = opcode
        else:
            raise RelativeBranchError('invalid source relative branch operands')
        if span.end - span.start != 2:
            raise RelativeBranchError('source relative branch is not two bytes')
        try:
            encoded = bytes(assembler(source))
        except (ValueError, TypeError, KeyError, IndexError) as exc:
            raise RelativeBranchError('invalid source relative branch encoding') from exc
        expected_opcode = {
            'djnz': 0x10, 'jr': 0x18, 'jr nz': 0x20,
            'jr z': 0x28, 'jr nc': 0x30, 'jr c': 0x38,
        }[instruction]
        if (len(encoded) != 2 or encoded[0] != expected_opcode or
                encoded[1] != (displacement & 255)):
            raise RelativeBranchError('source relative branch encoding differs')
        target = span.end + displacement
        if target not in instructions:
            raise RelativeBranchError('relative branch target is not a source instruction')
        if span.start in result:
            raise RelativeBranchError('duplicate source relative branch site')
        result[span.start] = RelativeBranch(span.start, target, source, instruction)
    return result


def verify_three_relative_passes(groups, bases):
    """Require identical source-relative control flow at three native bases."""
    if len(groups) != 3 or len(bases) != 3 or len(set(bases)) != 3:
        raise RelativeBranchError('three distinct compilation bases required')
    first = groups[0]
    signature = lambda branches: tuple(sorted(
        (branch.site, branch.target, branch.source, branch.opcode)
        for branch in branches.values()))
    original = signature(first)
    if any(signature(group) != original for group in groups[1:]):
        raise RelativeBranchError('source relative branch target changed across bases')
    return {'verified_relative_branches': len(first),
            'verified_relative_instruction_bytes': 2 * len(first),
            'verified_native_bases': len(set(bases))}
