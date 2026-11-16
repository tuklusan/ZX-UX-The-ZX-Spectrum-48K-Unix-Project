# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""Native ras/rld proof for source-decoded original 48K runtime emitters.

The source comes from original Z80 emitter transactions and copied ROM/tape
instructions. Assembler symbols replace independently witnessed relocations.
Every emitted instruction passes through ras; no bytewise executable dump is
used. Cross-routine relative branches remain unresolved until actual program
routine selection and addresses are established.
"""
from __future__ import annotations

import argparse
import hashlib
from collections import Counter
import json
from pathlib import Path
import sys

STAGE = Path(__file__).resolve().parent
ROOT = STAGE.parents[2]
sys.path[:0] = [str(STAGE), str(ROOT / 'src/zx-ux-sdk')]
import ras
import rld
from gate8_original_runtime_types import BASES, N_ROUTINES, OriginalEmitter, compiler_image
from gate8_original_runtime_disassembly import (
    RuntimeDisassemblyError, _decode_all, decode_original_copy_sources,
)


class RuntimeNativeError(ValueError):
    """Original compiler output has not passed native symbolic reassembly."""


def source_assembly(computed, writes, base):
    """Build source-labelled Z80; reject unknown address words and targets."""
    data = bytes(value for _, value, _ in writes)
    decoded = _decode_all(data, base)
    relocs = {}
    for event in computed:
        if event.kind == 'reloc-low':
            matching = [other for other in computed if other.position == event.position + 1
                        and other.kind == 'reloc-high'
                        and other.target_offset == event.target_offset]
            if len(matching) != 1:
                raise RuntimeNativeError('source relocation word is incomplete')
            relocs[event.position] = event.target_offset
    labels = {0}
    for position, instruction in decoded.items():
        operands = instruction.operands
        if (instruction.mnemonic in ('JP', 'JR', 'DJNZ', 'CALL') and
                operands and operands[-1].startswith('0x')):
            target = int(operands[-1], 16) - base
            if 0 <= target < len(data):
                labels.add(target)
    for target in relocs.values():
        if not 0 <= target < len(data):
            raise RuntimeNativeError('relocation requires another original runtime routine')
        labels.add(target)
    if any(label not in decoded for label in labels):
        raise RuntimeNativeError('original source label enters an instruction operand')

    def label(position):
        return 'start' if position == 0 else f'rt_{position:04x}'

    lines = ['    section text', '    global start']
    for position, instruction in decoded.items():
        if position in labels:
            lines.append(label(position) + ':')
        expression = instruction.text.lower()
        if (instruction.mnemonic in ('JP', 'JR', 'DJNZ', 'CALL') and
                instruction.operands and instruction.operands[-1].startswith('0x')):
            token = instruction.operands[-1].lower()
            target = int(token, 16) - base
            if target in labels:
                expression = expression.replace(token, label(target))
        for offset, target in relocs.items():
            if position < offset < position + instruction.size:
                token = f'0x{(target + base) & 65535:04x}'
                if token in expression:
                    expression = expression.replace(token, label(target))
                elif label(target) not in expression:
                    raise RuntimeNativeError('typed relocation lacks a source operand')
        lines.append('    ' + expression)
    return '\n'.join(lines) + '\n', relocs


def native_reassemble(original, code, rom, base=BASES[0]):
    """Link typed source and compare every byte after genuine native relocation."""
    computed, writes = original
    copied, _ = decode_original_copy_sources(code, rom, writes)
    if copied + len(computed) != len(writes):
        raise RuntimeNativeError('original emitter bytes do not have complete ownership')
    source, expected_relocs = source_assembly(computed, writes, base)
    try:
        obj = ras.assemble_text(source, 'original-48k-runtime.s')
        ssx, _, _, _, _ = rld.link(
            [rld.Obj(obj, 'original-48k-runtime.sso')], [], entry='start', stack=384)
        parsed = rld.parse_ssx(ssx)
    except (ras.AsmError, rld.LinkError) as exc:
        raise RuntimeNativeError(str(exc)) from exc
    if parsed['relocs'] != sorted(expected_relocs):
        raise RuntimeNativeError('native linker relocation sites differ from original')
    original_bytes = bytes(value for _, value, _ in writes)
    if bytes(rld.relocate(parsed['image'], parsed['relocs'], base)) != original_bytes:
        raise RuntimeNativeError('native linked instructions differ from original compiler')
    return {'output_sha256': hashlib.sha256(ssx).hexdigest(),
            'file_bytes': len(ssx), 'image_bytes': len(parsed['image']),
            'bss_bytes': parsed['bss'], 'stack_bytes': parsed['stack'],
            'total_bytes': len(parsed['image']) + parsed['bss'] + parsed['stack'],
            'relocation_sites': len(parsed['relocs'])}


def audit_original_native(tape: bytes, rom: bytes):
    code = compiler_image(tape)
    totals = Counter()
    unresolved = []
    emitter_count = 0
    for routine in range(1, N_ROUTINES + 1):
        originals = [OriginalEmitter(code, rom, base).run(routine) for base in BASES]
        if all(original is None for original in originals):
            continue
        if any(original is None for original in originals):
            raise RuntimeNativeError('original emitter table changed between bases')
        emitter_count += 1
        outputs = []
        errors = []
        for original, base in zip(originals, BASES):
            try:
                outputs.append(native_reassemble(original, code, rom, base))
            except RuntimeNativeError as exc:
                errors.append(str(exc))
        if errors:
            if outputs or len(errors) != len(BASES) or any(
                    'relative jump out of range' not in error for error in errors):
                raise RuntimeNativeError('original native assembly failed inconsistently')
            unresolved.append({'routine': routine,
                               'reason': errors[0]})
            continue
        result = outputs[0]
        if (len({x['output_sha256'] for x in outputs}) != 1 or
                any(x != result for x in outputs[1:])):
            raise RuntimeNativeError('native symbolic output changed across bases')
        totals['linked_routines'] += 1
        totals['linked_image_bytes'] += result['image_bytes']
        totals['linked_file_bytes'] += result['file_bytes']
        totals['relocation_sites'] += result['relocation_sites']
    return {'original_runtime_emitters': emitter_count,
            **dict(totals), 'unresolved': unresolved,
            'cross_routine_layout_verified': False,
            'full_program_runtime_equivalence_verified': False,
            'gate8_complete': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--compiler-tzx', required=True, type=Path)
    parser.add_argument('--rom', type=Path,
                        default=ROOT / 'src/zx-ux-sdk/rom/48.rom')
    args = parser.parse_args()
    print('ORIGINAL_RUNTIME_NATIVE', json.dumps(audit_original_native(
        args.compiler_tzx.read_bytes(), args.rom.read_bytes()), sort_keys=True))


if __name__ == '__main__':
    main()
