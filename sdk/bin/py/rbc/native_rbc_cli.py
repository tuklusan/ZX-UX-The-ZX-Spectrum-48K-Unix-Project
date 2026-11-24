#!/usr/bin/env python3
# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""Strict no-optimizer RBC: independently checked HiSoft source -> ras -> rld.

Only original, numbered 48K BASIC is accepted here. The existing HiSoft
compiler must be reproducibly rebuilt from checked Git sources first.
Unsupported cases fail closed. Game behavior needs separate testing.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STAGE = Path(__file__).resolve().parent
SDK = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(STAGE), str(SDK)]
import rld
from gate8_full_source_audit import run as audit_original_source
from native_wrapper_source import assemble_link, _signed_print_at
from native_input_source import assemble_input_source
from basic_listing import encode_strict_listing
from native_long_string_proof import workspace_bytes
from native_budgeted_dim import capacity_for_native_budget
from diagnostics import format_warning


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _check_equal(native: bytes, reference: bytes) -> None:
    if native == reference:
        return
    first = next((i for i, (a, b) in enumerate(zip(native, reference))
                  if a != b), min(len(native), len(reference)))
    raise ValueError('native ras/rld output differs from the three-base '
                     'HiSoft reference at file offset '
                     f'{first} (native={len(native)}, reference={len(reference)})')



def _has_input_token(listing: bytes) -> bool:
    """Read real 48K BASIC tokens, ignoring quoted/REM/DATA text and caches."""
    offset = 0
    while offset < len(listing):
        if offset + 4 > len(listing):
            raise ValueError('truncated BASIC line header')
        size = int.from_bytes(listing[offset+2:offset+4], 'little')
        if not size or offset + 4 + size > len(listing):
            raise ValueError('truncated BASIC token line')
        line = listing[offset+4:offset+4+size]
        quoted = data = False
        i = 0
        while i < len(line):
            ch = line[i]
            if ch == 34:
                quoted = not quoted
            elif not quoted:
                if ch == 0xea:  # REM
                    break
                if ch == 14:  # numeric cache; opaque 5 bytes
                    if i + 6 > len(line):
                        raise ValueError('truncated BASIC numeric cache')
                    i += 6
                    continue
                if ch == 0xe4:  # DATA until next active colon
                    data = True
                if ch == 58:
                    data = False
                if ch == 0xee and not data:  # INPUT statement
                    # The original BASIC `INPUT "literal"` has no target variable
                    # and HiSoft emits no ROM editor call for it. Do not manufacture
                    # an unwitnessed source bridge.
                    j = i + 1
                    while j < len(line) and line[j] == 32:
                        j += 1
                    if j < len(line) and line[j] == 34:
                        j += 1
                        while j < len(line) and line[j] != 34:
                            j += 1
                        if j < len(line):
                            j += 1
                            while j < len(line) and line[j] == 32:
                                j += 1
                            if j >= len(line) or line[j] in (13, 58):
                                i = j
                                continue
                    return True
            i += 1
        offset += size + 4
    return False


def compile_native(source: Path, checkpoint: Path, frontend: Path,
                   tape: Path, rom: Path, *,
                   stack: int = 384, maximum: int = 14000,
                   use_fit: bool = True, input_backend: str = "zxux",
                   rom_work_bytes: int = 0) -> tuple[str, bytes, bytes, dict]:
    """Compile from independent source events; never re-encode a linked SSX."""
    if not (source.is_file() and source.suffix.lower() == '.bas'):
        raise ValueError('requires original numbered ASCII .bas source')
    if not all(p.is_file() for p in (checkpoint / 'engine.py',
                                    checkpoint / 'font32.bin',
                                    frontend / 'compiler.py', tape, rom)):
        raise ValueError('verified HiSoft compiler, frontend, tape and ROM required')
    if type(maximum) is not int or maximum < 0 or type(stack) is not int or stack < 1:
        raise ValueError('invalid --max or --stack')
    if input_backend not in ('rom', 'zxux'):
        raise ValueError('invalid INPUT backend')
    if os.environ.get('RBC_G8_OPTIMIZER'):
        raise ValueError('optimizer injection is forbidden in native RBC')
    warnings = []

    def warn(code, detail=''):
        warnings.append({'mnemonic': code, 'detail': detail})
        print(format_warning(code, detail), file=sys.stderr)

    # Use the checked stage tokenizer even with an older recovered checkpoint.
    encode_strict_listing(source.read_text(encoding='ascii'))
    from rbc import engine as rbc
    font = (checkpoint / 'font32.bin').read_bytes()
    builds, meta = rbc._compile_three(source, frontend, tape, rom,
                                      65367, [], 'strict', False, 1)
    reserved_workspace = workspace_bytes(meta.get('optimized_strings', []),
                                         meta.get('rom_runtime_uses', ()))
    if rom_work_bytes not in (0, reserved_workspace):
        raise ValueError('RBC_ROM_WORKSPACE_UNSAFE: private ROM workspace lacks an operation witness')
    rom_work_bytes = reserved_workspace
    legacy, _ = rbc.build_ssx(builds, font, rld, stack, use_rom_font=False)
    fitted = (use_fit and maximum and
              max(len(legacy),
                  len(rld.parse_ssx(legacy)['image']) + builds[0].bss + stack) > maximum and
              not meta.get('private_font_requested', False))
    if fitted:
        legacy, _ = rbc.build_ssx(builds, font, rld, stack,
                                      use_rom_font=True)
    budget_capacity = 0
    has_native_input = (input_backend == 'zxux' and _has_input_token(
        encode_strict_listing(source.read_text(encoding='ascii'))))
    if meta.get('budgeted_numeric_units'):
        # Reserve array storage against the *complete* native resident image. For INPUT
        # programs, measure the actual source-backed INPUT bridge on a one-element trial first;
        # the unbridged HiSoft size is too small.
        trial = rld.parse_ssx(legacy)
        if has_native_input:
            trial_sources = []
            trial_proof = audit_original_source(
                source, checkpoint, frontend, tape, rom,
                source_sink=trial_sources.append, max_bytes=maximum,
                budget_capacity=1)
            native_trial = trial_proof['native_whole_source_baseline']
            if (len(trial_sources) != 1 or
                    not native_trial.get('native_whole_source_baseline_linked') or
                    not native_trial.get('native_image_byte_exact') or
                    not native_trial.get('all_source_relocations_verified') or
                    not trial_proof['native_runtime_region'].get('native_region_verified')):
                raise ValueError('one-element native DIM source trial unresolved')
            p_trial = builds[0]
            saved_stack = p_trial.base + len(p_trial.code) + p_trial.bss - 2
            restart_slot = p_trial.bss >= 2 and any(
                offset >= 2 and p_trial.code[offset-2:offset] == b'\xed\x7b' and
                int.from_bytes(p_trial.code[offset:offset+2], 'little') == saved_stack
                for offset in rbc._reloc_sites(builds))
            source_trial, _, plain_trial = assemble_link(
                trial_sources[0], font, use_rom_font=fitted,
                restart_slot=restart_slot, stack=stack)
            _check_equal(plain_trial, legacy)
            if rom_work_bytes:
                source_trial, _, _ = assemble_link(
                    trial_sources[0], font, use_rom_font=fitted,
                    restart_slot=restart_slot, stack=stack,
                    rom_work_bytes=rom_work_bytes)
            if _signed_print_at(source_trial)[1]:
                source_trial, _, _ = assemble_link(
                    trial_sources[0], font, use_rom_font=fitted,
                    restart_slot=restart_slot, stack=stack,
                    rom_work_bytes=rom_work_bytes, signed_print_at=True)
            _, _, complete_trial = assemble_input_source(
                source_trial, stack=stack, maximum=maximum)
            trial = rld.parse_ssx(complete_trial)
        budget_capacity = capacity_for_native_budget(
            maximum, len(trial['image']), trial['bss'], stack,
            meta['budgeted_numeric_units'])
        warn('RBC_WARN_DYNAMIC_DIM', f'Reserved capacity per dimension: {budget_capacity}.')
        builds, meta = rbc._compile_three(source, frontend, tape, rom,
                                          65367, [], 'strict', False,
                                          budget_capacity)
        legacy, _ = rbc.build_ssx(builds, font, rld, stack,
                                  use_rom_font=fitted)
    source_candidates = []
    try:
        proof = audit_original_source(source, checkpoint, frontend, tape, rom,
                                      source_sink=source_candidates.append,
                                      max_bytes=maximum,
                                      budget_capacity=budget_capacity)
    except ValueError as exc:
        if str(exc) == 'the full compiled mode C image is required':
            warn('RBC_WARN_HISOFT_SPLIT_IMAGE')
        raise
    native_proof = proof['native_whole_source_baseline']
    if (len(source_candidates) != 1 or
            not native_proof.get('native_whole_source_baseline_linked') or
            not native_proof.get('native_image_byte_exact') or
            not native_proof.get('all_source_relocations_verified') or
            not proof['native_runtime_region'].get('native_region_verified')):
        blocker = str(native_proof.get('blocker', 'missing native witness'))
        if 'unresolved compiler bytes extend beyond native runtime' in blocker:
            warn('RBC_WARN_HISOFT_UNOWNED_BYTES')
        raise ValueError('original typed three-base HiSoft source unresolved: ' + blocker)
    sites = rbc._reloc_sites(builds)
    p = builds[0]
    saved_stack = p.base + len(p.code) + p.bss - 2
    restart_slot = p.bss >= 2 and any(
        offset >= 2 and p.code[offset-2:offset] == b'\xed\x7b' and
        int.from_bytes(p.code[offset:offset+2], 'little') == saved_stack
        for offset in sites)
    source_text, obj, native_ssx = assemble_link(
        source_candidates[0], font, use_rom_font=fitted,
        restart_slot=restart_slot, stack=stack)
    # The original wrapper is a *comparison input only*. Its emitted bytes never feed the assembler,
    # linker, returned output, or source generator.
    _check_equal(native_ssx, legacy)
    baseline_sha = _sha(native_ssx)
    repeat_controls = bool(meta.get('repeat_controls', False))
    if rom_work_bytes or repeat_controls:
        source_text, obj, native_ssx = assemble_link(
            source_candidates[0], font, use_rom_font=fitted,
            restart_slot=restart_slot, stack=stack,
            rom_work_bytes=rom_work_bytes,
            repeat_controls=repeat_controls)
    # Apply the original 48K ROM's signed-coordinate rule directly at the witnessed native PRINT
    # AT entry; no inserted call sites or new bridge.
    at_sites = 0
    if _signed_print_at(source_text)[1]:
        source_text, obj, native_ssx = assemble_link(
            source_candidates[0], font, use_rom_font=fitted,
            restart_slot=restart_slot, stack=stack,
            rom_work_bytes=rom_work_bytes, signed_print_at=True,
            repeat_controls=repeat_controls)
        at_sites = int('rbc_wrapper_at_row_abs:' in source_text)
    bridge_used = False
    if has_native_input:
        source_text, obj, native_ssx = assemble_input_source(
            source_text, stack=stack, maximum=maximum)
        bridge_used = True
    image = rld.parse_ssx(native_ssx)
    total = len(image['image']) + image['bss'] + image['stack']
    if maximum and max(total, len(native_ssx)) > maximum:
        raise ValueError(f'native memory limit exceeded: file={len(native_ssx)}, '
                         f'image={len(image["image"])}, bss={image["bss"]}, '
                         f'stack={stack}, total={total}, max={maximum}')
    report = {
        'source_sha256': _sha(source.read_bytes()),
        'source': str(source),
        'native_assembly_sha256': _sha(source_text.encode('ascii')),
        'native_object_sha256': _sha(obj),
        'native_ssx_sha256': _sha(native_ssx),
        'file': len(native_ssx), 'image': len(image['image']),
        'bss': image['bss'], 'stack': stack, 'total': total,
        'memory_limit': maximum, 'relocations': len(image['relocs']),
        'native_three_base_source_verified': True,
        'native_and_legacy_ssx_byte_identical': not bridge_used and not rom_work_bytes and not at_sites and not repeat_controls,
        'rom_signed_print_at_corrected': bool(at_sites),
        'original_hisoft_baseline_sha256': baseline_sha,
        'source_proven_string_growth': [p for p in meta.get('optimized_strings', [])
                                       if p.get('bound_proof')],
        'string_storage_reservations': [p for p in meta.get('optimized_strings', [])
                                        if p.get('storage_is_reservation')],
        'runtime_string_capacity_checks': True,
        'input_backend': 'zxux' if bridge_used else 'rom',
        'input_source_bridge_three_base_verified': bridge_used,
        'native_linker': 'ras/rld',
        'rom_font_used': fitted,
        'optimizer_used': False,
        'rom_work_bytes': rom_work_bytes,
        'rom_repeat_controls_restored': repeat_controls,
        'rom_runtime_uses': list(meta.get('rom_runtime_uses', ())),
        'warnings': warnings,
        'loader_execution_tested': False,
        'native_gameplay_tested': False,
    }
    return source_text, obj, native_ssx, report


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('source', type=Path)
    p.add_argument('--compiler', required=True, type=Path,
                   help='checked, recovered RBC directory containing rbc.py')
    p.add_argument('--frontend', required=True, type=Path)
    p.add_argument('--tape', required=True, type=Path)
    p.add_argument('--rom', type=Path, default=SDK / 'rom/48.rom')
    p.add_argument('-o', '--output', type=Path, required=True)
    mode = p.add_mutually_exclusive_group()
    mode.add_argument('-S', action='store_true', help='write true pre-link .s')
    mode.add_argument('-c', action='store_true', help='write real ras .sso')
    p.add_argument('--max', type=int, default=14000)
    p.add_argument('--stack', type=int, default=384)
    p.add_argument('--no-fit', action='store_true')
    p.add_argument('--input-backend', choices=('rom', 'zxux'), default='zxux',
                   help='bounded production ZX-UX INPUT source; rom reproduces the original HiSoft baseline')
    p.add_argument('--report', type=Path)
    a = p.parse_args(argv)
    try:
        text, obj, ssx, report = compile_native(
            a.source.resolve(), a.compiler.resolve(), a.frontend.resolve(),
            a.tape.resolve(), a.rom.resolve(),
            stack=a.stack, maximum=a.max, use_fit=not a.no_fit,
            input_backend=a.input_backend)
        output = text.encode('ascii') if a.S else obj if a.c else ssx
        if a.output.resolve() == a.source.resolve():
            raise ValueError('refusing to overwrite original BASIC input')
        a.output.parent.mkdir(parents=True, exist_ok=True)
        a.output.write_bytes(output)
        if a.report:
            a.report.parent.mkdir(parents=True, exist_ok=True)
            a.report.write_text(json.dumps(report, indent=2) + '\n')
        print(f'RBC_NATIVE_OK file={report["file"]} image={report["image"]} '
              f'bss={report["bss"]} stack={report["stack"]} '
              f'total={report["total"]} relocs={report["relocations"]}')
        return 0
    except Exception as exc:
        print(f'RBC_NATIVE_BLOCKED {type(exc).__name__}: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
