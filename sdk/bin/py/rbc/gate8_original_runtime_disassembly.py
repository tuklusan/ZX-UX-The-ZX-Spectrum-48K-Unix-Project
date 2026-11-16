# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""Trace-checked disassembly of runtime output from the ORIGINAL HiSoft 48K.

Decode bytes from the original compiler/ROM copy sites, rather than treating a
post-link image as source. Original Z80 emitter execution supplies the other
byte and relocation types. Three native load bases and reachable boundaries
must agree. Full-program linking and behavior checks are separate gates.
"""
from __future__ import annotations

import argparse
from collections import Counter, deque
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'src/zx-ux-sdk'))
from z80_python.disasm import disassemble_bytes
from gate8_original_runtime_types import (
    BASES, N_ROUTINES, START, EmitterTypeError, OriginalEmitter,
    compiler_image,
)


class RuntimeDisassemblyError(ValueError):
    """Source bytes or control boundaries cannot be justified independently."""


def _decode_all(data: bytes, address: int):
    operations = {}
    position = 0
    while position < len(data):
        try:
            op = disassemble_bytes(data[position:], address + position)
        except (ValueError, NotImplementedError, IndexError) as exc:
            raise RuntimeDisassemblyError(
                f'instruction boundary missing at offset {position}') from exc
        if op.data != data[position:position + op.size]:
            raise RuntimeDisassemblyError('decoded instruction differs from original bytes')
        operations[position] = op
        position += op.size
    if position != len(data):
        raise RuntimeDisassemblyError('source fragment ends inside an instruction')
    return operations


def decode_original_copy_sources(code: bytes, rom: bytes, writes):
    """Copy runs may be instructions only when ORIGINAL source bytes decode.

    A run ends whenever the emitter changes writer type, source address, or
    source-address continuity. Never infer a source site from output alone.
    """
    source_count = 0
    fragments = 0
    offset = 0
    while offset < len(writes):
        place, value, source = writes[offset]
        if place != offset:
            raise RuntimeDisassemblyError('noncontiguous source-owned output')
        if source is None:
            offset += 1
            continue
        end = offset + 1
        while (end < len(writes) and writes[end][2] is not None and
               writes[end][2] == writes[end - 1][2] + 1):
            end += 1
        chunk = bytes(row[1] for row in writes[offset:end])
        if source < len(rom) and source + len(chunk) <= len(rom):
            original = rom[source:source + len(chunk)]
        elif START <= source and source + len(chunk) <= START + len(code):
            original = code[source - START:source - START + len(chunk)]
        else:
            raise RuntimeDisassemblyError('copy source is outside original ROM/compiler')
        if original != chunk:
            raise RuntimeDisassemblyError('original source no longer matches copied bytes')
        decoded = _decode_all(original, source)
        if sum(op.size for op in decoded.values()) != len(chunk):
            raise RuntimeDisassemblyError('original copy fragment is not instruction-complete')
        source_count += len(chunk)
        fragments += 1
        offset = end
    return source_count, fragments


def _flow(ops, length: int, base: int):
    """Bounded CFG. Reject branch targets into operands or undisassembled data."""
    todo = deque([0])
    reachable = set()
    counts = Counter()
    while todo:
        pos = todo.popleft()
        if pos == length:
            counts['next_routine_fallthrough'] += 1
            continue
        if pos not in ops:
            raise RuntimeDisassemblyError(f'control enters untyped byte {pos}')
        if pos in reachable:
            continue
        reachable.add(pos)
        op = ops[pos]
        next_pc = pos + op.size
        operands = op.operands
        last = operands[-1] if operands else ''
        if op.mnemonic in ('JP', 'JR', 'DJNZ', 'CALL'):
            if last.startswith('0x'):
                target_address = int(last, 16)
                target = target_address - base
                if 0 <= target < length:
                    if target not in ops:
                        raise RuntimeDisassemblyError('branch target overlaps instruction')
                    todo.append(target)
                    counts['internal_branch'] += 1
                elif target_address < 0x4000:
                    counts['rom_branch'] += 1
                else:
                    counts['unresolved_external_branch'] += 1
            elif op.mnemonic == 'JP' and last in ('(HL)', '(IX)', '(IY)'):
                counts['unresolved_indirect_branch'] += 1
                continue
            else:
                raise RuntimeDisassemblyError('unknown branch operand')
        if op.mnemonic in ('RET', 'RETI', 'RETN') and not operands:
            continue
        if op.mnemonic in ('JP', 'JR') and len(operands) == 1:
            continue
        if op.mnemonic == 'HALT':
            continue
        todo.append(next_pc)
    if len(reachable) != len(ops):
        raise RuntimeDisassemblyError('original emission has unreachable or ambiguous code/data')
    counts['reachable_instructions'] = len(reachable)
    return counts


def disassemble_original_runtime(tape: bytes, rom: bytes, bases=BASES):
    if (len(bases) != 3 or len(set(bases)) != 3 or
            any(type(base) is not int or not 0 <= base < 65536 for base in bases)):
        raise RuntimeDisassemblyError('three distinct native bases required')
    code = compiler_image(tape)
    total = Counter()
    for n in range(1, N_ROUTINES + 1):
        builds = [OriginalEmitter(code, rom, base).run(n) for base in bases]
        if all(run is None for run in builds):
            total['unused_emitter_slots'] += 1
            continue
        if any(run is None for run in builds):
            raise RuntimeDisassemblyError('runtime emitter presence changed across bases')
        signatures = []
        for base, (computed, writes) in zip(bases, builds):
            data = bytes(value for pos, value, _ in writes)
            if any(pos != i for i, (pos, _, _) in enumerate(writes)):
                raise RuntimeDisassemblyError('emitter changed source byte order')
            copied, fragments = decode_original_copy_sources(code, rom, writes)
            ops = _decode_all(data, base)
            try:
                flow = _flow(ops, len(data), base)
            except RuntimeDisassemblyError as e:
                raise RuntimeDisassemblyError(f'RT{n} at {base:04X}: {e}') from e
            if copied + len(computed) != len(data):
                raise RuntimeDisassemblyError('computed and copied source ownership disagree')
            positions = tuple((x.position, x.kind, x.source_site,
                               x.helper_pc, x.target_offset) for x in computed)
            signatures.append((tuple((p, op.size, op.mnemonic)
                                     for p, op in ops.items()),
                               tuple(src for _, _, src in writes), positions))
            if base == bases[0]:
                total['runtime_emitters'] += 1
                total['original_copied_bytes'] += copied
                total['original_source_fragments'] += fragments
                total['typed_computed_bytes'] += len(computed)
                total['total_output_bytes'] += len(data)
                total.update(flow)
        if signatures[1:] != signatures[:1] * 2:
            raise RuntimeDisassemblyError(f'RT{n} source or instruction map changed across bases')
        for first, second, third in zip(*(run[0] for run in builds)):
            if first.kind.startswith('reloc-'):
                for event, base in zip((first, second, third), bases):
                    shift = 8 if event.kind == 'reloc-high' else 0
                    expected = ((event.target_offset + base) >> shift) & 255
                    if event.value != expected:
                        raise RuntimeDisassemblyError('original source relocation changed')
            elif first.value != second.value or first.value != third.value:
                raise RuntimeDisassemblyError('nonrelocated source bytes changed across bases')
    if total['unused_emitter_slots'] + total['runtime_emitters'] != N_ROUTINES:
        raise RuntimeDisassemblyError('runtime emitter table is incomplete')
    return {
        **dict(total), 'bases': list(bases),
        'original_source_bytes_verified': True,
        'three_base_instruction_boundaries_verified': True,
        'isolated_emitter_cfg_reachable': True,
        'whole_program_cross_routine_cfg_verified': False,
        'native_optimizer_equivalence_verified': False,
        'gate8_complete': False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--compiler-tzx', type=Path, required=True)
    parser.add_argument('--rom', type=Path,
                        default=ROOT / 'src/zx-ux-sdk/rom/48.rom')
    args = parser.parse_args()
    print('ORIGINAL_RUNTIME_DISASSEMBLY', json.dumps(
        disassemble_original_runtime(args.compiler_tzx.read_bytes(),
                                     args.rom.read_bytes()), sort_keys=True))


if __name__ == '__main__':
    main()
