# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""Compare complete source compilation with passive typed-emission auditing.

No optimization is attempted. A different byte, missing producer or patched
address remains an unresolved Gate 8 boundary, never an optimizer success.
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
sys.path[:0] = [str(STAGE), str(Path(__file__).resolve().parents[1])]
import rld
from symbolic_capture import audit_result, install as install_capture
from symbolic_source_patches import from_emissions, verify_three_passes
from symbolic_relocations import inspect_relocations, verify_three_builds
from symbolic_instructions import inspect_sources, verify_three_sources
from symbolic_opcode_pairs import inspect_opcode_pairs, verify_three_opcode_passes
from symbolic_source_boundaries import inspect_source_boundaries, verify_three_source_maps
from symbolic_fragments import inspect_final_fragments, verify_three_fragment_passes
from runtime_emitter_trace import verify_three_runtime_traces
from symbolic_emit_sites import inspect_emit_sites, verify_three_emit_sites
from symbolic_relative_branches import inspect_relative_branches, verify_three_relative_passes
from typed_whole_pipeline import (SourcePipelineError, link_source_pair,
    verify_and_build, verify_and_build_with_runtime_sources)
from typed_runtime_bridge import (RuntimeBridgeError,
    witnesses_from_compiler_captures)
from gate8_runtime_source_match import verify_three_runtime_sources
from gate8_native_runtime_combined import (RuntimeCombinedError,
    verify_three_native_runtime_regions)
from gate8_runtime_handoff import RuntimeHandoffError, verify_three_runtime_handoffs
from gate8_whole_native_baseline import WholeBaselineError, verify_three_whole_native_baselines
from hisoft_frontend_inputs import KNOWN_COMPILER


def verify_full_source_native(events, results, text_ends, assembler, ras,
                              *, runtime_witnesses=None, runtime_traces=None):
    """Attempt a real native link, recording missing typed sources honestly."""
    try:
        images = [r.code for r in results]
        bases = [r.base for r in results]
        bss = [r.bss for r in results]
        if runtime_witnesses is None and runtime_traces is None:
            source = verify_and_build(events, images, bases, text_ends,
                                      bss, assembler)
        elif runtime_witnesses is not None and runtime_traces is not None:
            source = verify_and_build_with_runtime_sources(
                events, images, bases, text_ends, bss, assembler,
                runtime_witnesses, runtime_traces)
        else:
            raise SourcePipelineError('runtime source and original trace must be paired')
        plain, _, sizes = link_source_pair(source, ras, rld, lambda text: text)
    except (ValueError, TypeError, KeyError, AttributeError) as exc:
        return {'source_owned': False, 'native_link_verified': False,
                'blocker': str(exc), 'native_behavior_verified': False}
    return {'source_owned': True, 'native_link_verified': True,
            'plain_sha256': hashlib.sha256(plain).hexdigest(),
            'plain_sizes': sizes['plain'],
            'typed_runtime_bridge': source.source_report.get('runtime_source_bridge'),
            'native_behavior_verified': False}


def run(source: Path, checkpoint: Path, frontend: Path,
        tape: Path, rom: Path, *, original_runtime_statements=None,
        source_sink=None, max_bytes=14000,
        budget_capacity=0) -> dict:
    if not (checkpoint / 'engine.py').is_file():
        raise ValueError('reconstructed RBC checkpoint required')
    if not (frontend / 'compiler.py').is_file():
        raise ValueError('canonical 48K frontend required')
    from rbc import engine as rbc
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    baseline, _ = rbc._compile_three(source, frontend, tape, rom, 0xff00,
                                      [], 'block', False, budget_capacity)
    records = []
    source_words = []
    relocations = []
    instructions = []
    opcode_pairs = []
    source_maps = []
    source_fragments = []
    runtime_source_traces = []
    compiler_source_sites = []
    relative_groups = []
    captured_events = []
    text_endpoints = []
    runtime_layouts = []
    original_captures = []
    original_hook = rbc.install_codegen_optimizer

    def passive_capture(module):
        install_capture(module)
        parent = module.Compiler.compile_whole
        def recorded(self, *args, **kwargs):
            result = parent(self, *args, **kwargs)
            if result.ok:
                records.append(audit_result(self, result))
                original_captures.append(self._zxux_capture)
                captured_events.append(tuple(self._zxux_capture.events))
                text_endpoints.append(self.data_start)
                runtime_layouts.append({
                    'sysvar_offset': getattr(self.m, '_zxux_sysvar_base', None),
                    'process_total': getattr(self.m, '_zxux_total', None),
                    'font_alias': getattr(self.m, '_zxux_font_alias', None),
                })
                runtime_source_traces.append(list(self._zxux_capture.runtime_traces))
                compiler_source_sites.append(inspect_emit_sites(self._zxux_capture.events))
                source_words.append(from_emissions(
                    self._zxux_capture.events, result.code,
                    result.code_base, self.data_start))
                relocations.append(inspect_relocations(
                    self._zxux_capture.events, result.code,
                    result.code_base, result.var_bytes))
                from z80asm import asm
                instructions.append(inspect_sources(
                    self._zxux_capture.events, result.code, asm))
                opcode_pairs.append(inspect_opcode_pairs(
                    self._zxux_capture.events, result.code,
                    result.code_base, asm))
                source_map = inspect_source_boundaries(
                    self._zxux_capture.events, result.code,
                    result.code_base, self.data_start, result.var_bytes, asm)
                source_maps.append(source_map)
                relative_groups.append(inspect_relative_branches(
                    source_map.spans, self.data_start, asm))
                source_fragments.append(inspect_final_fragments(
                    self._zxux_capture.events, result.code, self.data_start, asm))
            return result
        module.Compiler.compile_whole = recorded

    try:
        rbc.install_codegen_optimizer = passive_capture
        observed, _ = rbc._compile_three(source, frontend, tape, rom,
                                          0xff00, [], 'block', True, budget_capacity)
    finally:
        rbc.install_codegen_optimizer = original_hook
    if len(baseline) != 3 or len(observed) != 3 or len(records) != 3:
        raise ValueError('requires three full compiler passes')
    for index, (before, after) in enumerate(zip(baseline, observed)):
        if (before.code, before.entry, before.base, before.bss) != (
                after.code, after.entry, after.base, after.bss):
            raise RuntimeError(f'passive capture changed program bytes at pass {index}')
    source_patch_report = verify_three_passes(source_words, observed)
    relocation_report = verify_three_builds(relocations, [x.base for x in observed])
    instruction_report = verify_three_sources(instructions, [x.base for x in observed],
                                               [m.overlaps for m in source_maps])
    opcode_report = verify_three_opcode_passes(opcode_pairs, [x.base for x in observed])
    source_map_report = verify_three_source_maps(source_maps, [x.base for x in observed])
    fragment_report = verify_three_fragment_passes(source_fragments,
                                                 [x.base for x in observed])
    runtime_report = verify_three_runtime_traces(runtime_source_traces,
                                                 [x.base for x in observed])
    source_site_report = verify_three_emit_sites(compiler_source_sites,
                                                  [x.base for x in observed])
    relative_report = verify_three_relative_passes(relative_groups,
                                                  [x.base for x in observed])
    import hbcimage
    from rtnames import RT
    from native_sysvars_rt import PEEK_RT, POKE_RT, UDG_HELPER_RT
    vendor = hbcimage.Image.from_tape(tape)
    if len(vendor.data) != 11885 or vendor.sha256 != KNOWN_COMPILER:
        raise ValueError('original HiSoft compiler tape identity differs')
    runtime_source_match = verify_three_runtime_sources(
        vendor.data, rom.read_bytes(),
        [build.code for build in observed],
        [build.base for build in observed],
        [m.spans for m in source_maps],
        {PEEK_RT: 'native-peek', POKE_RT: 'native-poke',
         UDG_HELPER_RT: 'native-udg',
         RT.PAUSE: 'native-pause', RT.VAL: 'guarded-val', RT.VAL_STR: 'guarded-vals'},
        replacement_settings=runtime_layouts)
    try:
        native_runtime_region = verify_three_native_runtime_regions(
            vendor.data, rom.read_bytes(),
            [build.code for build in observed],
            [build.base for build in observed],
            [m.spans for m in source_maps],
            {PEEK_RT: 'native-peek', POKE_RT: 'native-poke',
         UDG_HELPER_RT: 'native-udg',
             RT.PAUSE: 'native-pause',
             RT.VAL: 'guarded-val', RT.VAL_STR: 'guarded-vals'},
            runtime_layouts)
    except RuntimeCombinedError as exc:
        native_runtime_region = {
            'native_region_verified': False, 'blocker': str(exc),
            'full_program_optimized': False, 'native_behavior_verified': False,
        }
    try:
        from z80asm import asm
        runtime_handoff = verify_three_runtime_handoffs(
            captured_events, [build.code for build in observed],
            [build.base for build in observed], text_endpoints,
            [build.bss for build in observed], asm, native_runtime_region)
    except (RuntimeHandoffError, ValueError, TypeError) as exc:
        runtime_handoff = {'runtime_handoff_verified': False, 'blocker': str(exc),
                           'full_program_optimized': False,
                           'native_behavior_verified': False}
    try:
        optimizer = None
        from z80asm import asm
        whole_native_baseline = verify_three_whole_native_baselines(
            captured_events, [build.code for build in observed],
            [build.base for build in observed], text_endpoints,
            [build.bss for build in observed], asm,
            vendor.data, rom.read_bytes(),
            {PEEK_RT: 'native-peek', POKE_RT: 'native-poke',
         UDG_HELPER_RT: 'native-udg',
             RT.PAUSE: 'native-pause',
             RT.VAL: 'guarded-val', RT.VAL_STR: 'guarded-vals'}, runtime_layouts, native_runtime_region,
            optimizer=optimizer, source_sink=source_sink,
            max_bytes=max_bytes)
    except (WholeBaselineError, ValueError, TypeError) as exc:
        whole_native_baseline = {'native_whole_source_baseline_linked': False,
                                 'blocker': str(exc),
                                 'full_program_optimized': False,
                                 'native_behavior_verified': False}
    first, _ = rbc.build_ssx(baseline, bytes(768), rld, 384, use_rom_font=True)
    second, _ = rbc.build_ssx(observed, bytes(768), rld, 384, use_rom_font=True)
    if first != second:
        raise RuntimeError('passive capture changed linked native program')
    info = rld.parse_ssx(first)
    total = len(info['image']) + info['bss'] + info['stack']
    passive_admitted = max(total, len(first)) <= 14000
    # This is an audit, never a compiler admission path. Keep the exact passive
    # dimensions even when they exceed the default limit so the independently
    # relinked whole-source result (already checked above) can be inspected. Never
    # publish the over-limit passive SSX.
    for record in records:
        if record['safe_to_optimize']:
            raise RuntimeError('partial typed capture was incorrectly admitted')
    import ras
    from z80asm import asm
    runtime_witnesses = None
    original_traces = None
    runtime_provider_error = None
    if original_runtime_statements is not None:
        try:
            runtime_witnesses, original_traces = witnesses_from_compiler_captures(
                original_captures, original_runtime_statements)
        except (RuntimeBridgeError, ValueError, TypeError, AttributeError) as exc:
            runtime_provider_error = str(exc)
    if runtime_provider_error is None:
        whole_attempt = verify_full_source_native(
            captured_events, observed, text_endpoints, asm, ras,
            runtime_witnesses=runtime_witnesses,
            runtime_traces=original_traces)
    else:
        whole_attempt = {'source_owned': False, 'native_link_verified': False,
                         'blocker': runtime_provider_error,
                         'native_behavior_verified': False}
    return {
        'source_sha256': source_hash, 'source': source.name,
        'passive_capture_byte_identical': True,
        'linked_sha256': hashlib.sha256(first).hexdigest(),
        'file': len(first), 'image': len(info['image']),
        'bss': info['bss'], 'stack': info['stack'], 'total': total,
        'passive_within_default_limit': passive_admitted,
        'passive_loader_admitted': False,  # Audit cannot admit a native file.
        'audits': records, 'source_patches': source_patch_report,
        'source_relocations': relocation_report,
        'source_instructions': instruction_report,
        'paired_source_opcodes': opcode_report,
        'source_byte_ownership': source_map_report,
        'inline_source_fragments': fragment_report,
        'runtime_emitter_sources': runtime_report,
        'original_runtime_source_match': runtime_source_match,
        'native_runtime_region': native_runtime_region,
        'native_runtime_handoff': runtime_handoff,
        'native_whole_source_baseline': whole_native_baseline,
        'compiler_source_sites': source_site_report,
        'relative_source_branches': relative_report,
        'whole_program_attempt': whole_attempt,
        'gate8_complete': False,
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('source', type=Path)
    p.add_argument('--compiler', required=True, type=Path)
    p.add_argument('--frontend', required=True, type=Path)
    p.add_argument('--tape', required=True, type=Path)
    p.add_argument('--rom', type=Path, default=ROOT / 'src/zx-ux-sdk/rom/48.rom')
    args = p.parse_args()
    report = run(args.source.resolve(), args.compiler.resolve(),
                 args.frontend.resolve(), args.tape.resolve(), args.rom.resolve())
    print('GATE8_PASSIVE_SOURCE_AUDIT', json.dumps(report, sort_keys=True))


if __name__ == '__main__':
    main()
