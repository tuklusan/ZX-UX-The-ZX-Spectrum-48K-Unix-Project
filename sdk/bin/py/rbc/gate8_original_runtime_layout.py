# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""Rebuild selected HiSoft 48K runtime routines through original Z80 emitters.

Repeated original Z80 emission passes settle routine dependencies and addresses.
The final pass checks all byte sources at these exact positions. Native
ras/rld reassembly must reproduce all emitted bytes and relocation entries.
No unverified routine combination or full BASIC compilation is admitted.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

STAGE = Path(__file__).resolve().parent
ROOT = STAGE.parents[2]
sys.path[:0] = [str(STAGE), str(ROOT / 'src/zx-ux-sdk')]
from gate8_original_runtime_types import (
    BASES, N_ROUTINES, STAGING, OriginalEmitter, SourceTransactions,
    compiler_image,
)
from gate8_original_runtime_native import RuntimeNativeError, native_reassemble


USE_TABLE = 0x4000


class RuntimeLayoutError(ValueError):
    """A runtime dependency or symbol boundary cannot be settled."""


def _run_emitter(machine, routine: int, pc: int, counting: bool):
    machine.mem[0x451C] = int(counting)
    machine.mem[0x44EF:0x44F1] = pc.to_bytes(2, 'little')
    entry_offset = 0x77AF + (routine - 1) * 2
    entry = int.from_bytes(machine.mem[entry_offset:entry_offset + 2], 'little')
    if entry == 0:
        raise RuntimeLayoutError(f'RT{routine}: original compiler emitter slot is empty')
    machine.cpu.sp = 0x5A00
    machine.cpu._push_word(0xFFFF)
    machine.cpu.pc = entry
    for _ in range(15000):
        if machine.cpu.pc == 0xFFFF:
            break
        machine.at_pc = machine.cpu.pc
        if not counting:
            machine.type_source.step(machine.cpu, machine.at_pc)
        machine.cpu.step()
    else:
        raise RuntimeLayoutError(f'RT{routine} at {pc}: original runtime emitter did not return')
    end = int.from_bytes(machine.mem[0x44EF:0x44F1], 'little')
    if end < pc or end > 65536 - STAGING:
        raise RuntimeLayoutError('original runtime emitter overflowed output memory')
    return end


def _used(machine):
    return {n for n in range(1, N_ROUTINES + 1)
            if machine.mem[USE_TABLE + (n - 1) * 3] != 0}


def original_layout(code: bytes, rom: bytes, roots, base: int):
    """Run repeated original source emissions, no manual byte patch."""
    roots = set(roots)
    if (not roots or any(type(n) is not int or not 1 <= n <= N_ROUTINES
                         for n in roots) or
            type(base) is not int or not 0 <= base <= 0xFFFF):
        raise RuntimeLayoutError('invalid 48K runtime selection or base')
    machine = OriginalEmitter(code, rom, base)
    for routine in roots:
        slot = 0x77AF + 2 * (routine - 1)
        if machine.mem[slot:slot + 2] == b'\x00\x00':
            raise RuntimeLayoutError('requested emitter is not present in original tape')
        machine.mem[USE_TABLE + (routine - 1) * 3] = 1
    settled = False
    last_signature = None
    for _ in range(N_ROUTINES):
        machine.writes.clear()
        machine.type_source = SourceTransactions(machine.mem, base)
        pc = 0
        starts = {}
        for routine in range(1, N_ROUTINES + 1):
            row = USE_TABLE + (routine - 1) * 3
            if not machine.mem[row]:
                continue
            starts[routine] = pc
            machine.mem[row + 1:row + 3] = pc.to_bytes(2, 'little')
            pc = _run_emitter(machine, routine, pc, counting=False)
        remaining = _used(machine) - set(starts)
        if remaining:
            continue
        if pc > 65536 - STAGING:
            raise RuntimeLayoutError('runtime output exceeds process storage')
        image = bytes(machine.mem[STAGING:STAGING + pc])
        signature = (tuple(starts.items()), image)
        if signature == last_signature:
            settled = True
            break
        last_signature = signature
    if not settled:
        raise RuntimeLayoutError('runtime dependency selection did not settle')
    selected = sorted(starts)
    if tuple(starts.values()) != tuple(sorted(starts.values())) or not starts:
        raise RuntimeLayoutError('original routine offsets are out of order')
    if (len(machine.writes) != pc or
            sorted(position for position, _, _ in machine.writes) != list(range(pc))):
        raise RuntimeLayoutError('original selected runtime did not own every byte')
    computed = machine.type_source.finish()
    if len(computed) + sum(src is not None for _, _, src in machine.writes) != pc:
        raise RuntimeLayoutError('emitter byte ownership differs from source')
    output = bytes(machine.mem[STAGING:STAGING + pc])
    if output != bytes(value for _, value, _ in machine.writes):
        raise RuntimeLayoutError('emitted bytes and recorded source differ')
    return selected, starts, (computed, tuple(machine.writes))


def verify_selected_runtimes(tape: bytes, rom: bytes, roots, bases=BASES):
    if len(bases) != 3 or len(set(bases)) != 3:
        raise RuntimeLayoutError('three distinct original code bases required')
    code = compiler_image(tape)
    signatures = []
    for base in bases:
        selected, starts, source = original_layout(code, rom, roots, base)
        try:
            native = native_reassemble(source, code, rom, base)
        except RuntimeNativeError as exc:
            raise RuntimeLayoutError(str(exc)) from exc
        signatures.append((selected, starts, native))
    original_selected, original_starts, first = signatures[0]
    if any(a != original_selected or b != original_starts or c != first
           for a, b, c in signatures[1:]):
        raise RuntimeLayoutError('original source/native link changed with code base')
    return {'selected_routines': original_selected,
            'routine_offsets': original_starts,
            'three_native_bases': list(bases),
            'native': first,
            'full_program_codegen_verified': False,
            'native_gameplay_verified': False,
            'gate8_complete': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('routines', nargs='+', type=int)
    parser.add_argument('--compiler-tzx', type=Path, required=True)
    parser.add_argument('--rom', type=Path,
                        default=ROOT / 'src/zx-ux-sdk/rom/48.rom')
    args = parser.parse_args()
    print('SELECTED_ORIGINAL_RUNTIME', json.dumps(verify_selected_runtimes(
        args.compiler_tzx.read_bytes(), args.rom.read_bytes(), args.routines),
        sort_keys=True))


if __name__ == '__main__':
    main()
