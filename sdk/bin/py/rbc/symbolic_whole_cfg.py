# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""Fail-closed source-owned Z80 control-flow check before whole-program linking.

Only typed source statements and their witnessed relocation/relative targets
may define CFG edges. Opaque jump targets require a separately witnessed entry;
never infer targets or code/data boundaries from generated output bytes.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import re

from symbolic_relative_branches import inspect_relative_branches, RelativeBranchError


class WholeCFGError(ValueError):
    """A source-owned instruction can enter data or an unresolved control target."""


@dataclass(frozen=True)
class WholeCFG:
    entries: tuple[int, ...]
    reachable: tuple[int, ...]
    unreached: tuple[int, ...]
    edges: tuple[tuple[int, int], ...]
    rom_transfers: int
    terminal_exits: int


_CONDITIONS = frozenset(('nz', 'z', 'nc', 'c', 'po', 'pe', 'p', 'm'))
_ROM_NUMBER = re.compile(r'(?:0x[0-9a-f]+|\$[0-9a-f]+|[0-9]+)\Z', re.I)


def _number(text: str) -> int:
    return int(text[1:], 16) if text.startswith('$') else (
        int(text, 16) if text.startswith('0x') else int(text, 10))


def inspect_whole_cfg(spans, text_end: int, assembler, entry_offsets=(0,)) -> WholeCFG:
    """Check reachable control paths without decoding emitted code bytes.

    Unreached *typed* instructions are reported, not silently promoted to
    execution entries: indirect callbacks must supply independent entries.
    The caller must not treat this CFG as native behavioral equivalence.
    """
    if (type(text_end) is not int or text_end < 0 or
            not isinstance(entry_offsets, (list, tuple)) or not entry_offsets or
            any(type(x) is not int for x in entry_offsets) or
            len(set(entry_offsets)) != len(entry_offsets)):
        raise WholeCFGError('invalid explicit source CFG entries')
    instructions = {s.start: s for s in spans
                    if s.kind in ('instruction', 'instruction-relocated')}
    if (not instructions or any(not 0 <= s.start < s.end <= text_end
                                for s in instructions.values()) or
            any(x not in instructions for x in entry_offsets)):
        raise WholeCFGError('CFG entry is not a typed source instruction')
    ordered = sorted(spans, key=lambda s: s.start)
    if any(a.start >= a.end or a.end > b.start for a, b in zip(ordered, ordered[1:])):
        raise WholeCFGError('source spans overlap or are empty')
    if any(s.start < text_end < s.end for s in ordered):
        raise WholeCFGError('source span crosses instruction/data boundary')
    try:
        relatives = inspect_relative_branches(ordered, text_end, assembler)
    except RelativeBranchError as exc:
        raise WholeCFGError(str(exc)) from exc

    todo = deque(entry_offsets)
    seen = set()
    edges = set()
    rom = terminals = 0

    def add_edge(site: int, target: int) -> None:
        if target not in instructions:
            raise WholeCFGError(
                f'source control at {site} enters data, operand or unknown code at {target}')
        edges.add((site, target))
        todo.append(target)

    while todo:
        pc = todo.popleft()
        if pc in seen:
            continue
        seen.add(pc)
        span = instructions[pc]
        source = span.source.lower().strip()
        parts = source.split(None, 1)
        mnemonic = parts[0]
        operands = parts[1].strip() if len(parts) > 1 else ''
        terms = [s.strip() for s in operands.split(',') if s.strip()]
        next_pc = span.end
        follow = True
        if mnemonic in ('jr', 'djnz'):
            branch = relatives.get(pc)
            if branch is None:
                raise WholeCFGError('source relative branch has no typed target')
            add_edge(pc, branch.target)
            follow = mnemonic == 'djnz' or branch.opcode != 'jr'
        elif mnemonic in ('jp', 'call'):
            conditional = len(terms) == 2 and terms[0] in _CONDITIONS
            if (not terms or (len(terms) != 1 and not conditional)):
                raise WholeCFGError('unresolved source jump operands')
            target_text = terms[-1]
            if target_text.startswith('('):
                raise WholeCFGError('indirect control target has no verified source entries')
            if span.kind == 'instruction-relocated':
                if not isinstance(span.target, int):
                    raise WholeCFGError('relocated branch target missing')
                add_edge(pc, span.target)
            elif _ROM_NUMBER.fullmatch(target_text):
                number = _number(target_text)
                if number >= 0x4000:
                    raise WholeCFGError('non-symbolic external branch address')
                rom += 1
            else:
                raise WholeCFGError('jump needs witnessed relocation or fixed ROM target')
            follow = mnemonic == 'call' or conditional
        elif mnemonic in ('ret', 'reti', 'retn'):
            if terms and (len(terms) != 1 or terms[0] not in _CONDITIONS or mnemonic != 'ret'):
                raise WholeCFGError('invalid source return condition')
            terminals += 1
            follow = bool(terms)
        elif mnemonic == 'rst':
            if len(terms) != 1 or not _ROM_NUMBER.fullmatch(terms[0]):
                raise WholeCFGError('untyped ROM restart')
            number = _number(terms[0])
            if number not in range(0, 0x39, 8):
                raise WholeCFGError('invalid source ROM restart')
            rom += 1
        elif mnemonic == 'halt':
            # Interrupt return resumes at the next instruction after HALT.
            pass
        if follow:
            add_edge(pc, next_pc)
    return WholeCFG(tuple(entry_offsets), tuple(sorted(seen)),
                    tuple(sorted(instructions.keys() - seen)),
                    tuple(sorted(edges)), rom, terminals)


def verify_three_whole_cfg(groups, bases) -> dict:
    """Require identical instruction entries, CFG edges and ROM calls."""
    if (len(groups) != 3 or len(bases) != 3 or len(set(bases)) != 3 or
            any(type(b) is not int or not 0 <= b <= 65535 for b in bases)):
        raise WholeCFGError('three distinct source CFG bases required')
    first = groups[0]
    if any(other != first for other in groups[1:]):
        raise WholeCFGError('source control flow changed across native bases')
    return {'source_cfg_verified_bases': 3,
            'source_cfg_entries': len(first.entries),
            'source_cfg_reachable_instructions': len(first.reachable),
            'source_cfg_unreached_instructions': len(first.unreached),
            'source_cfg_edges': len(first.edges),
            'source_cfg_rom_transfers': first.rom_transfers,
            'source_cfg_terminal_exits': first.terminal_exits,
            'native_behavior_verified': False}
