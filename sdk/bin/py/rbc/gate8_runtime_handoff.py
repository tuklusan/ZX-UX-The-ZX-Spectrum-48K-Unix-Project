# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""Bridge three original compiler passes to independently linked runtime bytes.

This check does not turn opaque compiler output into optimizable instructions.
Native runtime replacement is admitted only over its exact witnessed source
span; every byte outside it must retain independent producer ownership.
"""
from __future__ import annotations

from symbolic_patch_binding import bind_three_source_passes
from symbolic_original_literals import protect_three_original_literals
from symbolic_line_table import bind_three_line_tables
from symbolic_source_boundaries import inspect_source_boundaries, verify_three_source_maps


class RuntimeHandoffError(ValueError):
    """The original compiler and typed native runtime disagree."""


def verify_three_runtime_handoffs(events, images, bases, text_ends, bss_sizes,
                                   assembler, native_runtime):
    """Verify original byte boundaries and three-base runtime replacement.

    All remaining non-runtime source bytes are counted as unresolved, never
    inferred from the executable image or declared safe for optimization.
    """
    if (any(len(x) != 3 for x in (events, images, bases, text_ends, bss_sizes))
            or len(set(bases)) != 3):
        raise RuntimeHandoffError('three distinct original compiler passes required')
    patched, patch_report = bind_three_source_passes(events, images, bases, text_ends)
    literals, literal_report = protect_three_original_literals(patched, images)
    final, table_report = bind_three_line_tables(literals, images, bases,
                                                  text_ends, bss_sizes)
    maps = [inspect_source_boundaries(group, image, base, end, bss, assembler)
            for group, image, base, end, bss in
            zip(final, images, bases, text_ends, bss_sizes)]
    report = verify_three_source_maps(maps, bases)
    if any(mapping.gaps or mapping.overlaps or mapping.mismatches for mapping in maps):
        raise RuntimeHandoffError('normalized source has gaps, overlaps or changed bytes')
    runtime = [tuple((s.start, s.end, s.source) for s in m.spans
                     if s.kind == 'runtime-opaque') for m in maps]
    if not runtime[0] or runtime[1:] != runtime[:1] * 2:
        raise RuntimeHandoffError('runtime source boundaries changed across bases')
    start, end = runtime[0][0][0], runtime[0][-1][1]
    if any(a != b for (_, a, _), (b, _, _) in zip(runtime[0], runtime[0][1:])):
        raise RuntimeHandoffError('runtime source is not contiguous')
    if (not isinstance(native_runtime, dict) or
            native_runtime.get('native_region_verified') is not True or
            native_runtime.get('passes') != 3 or
            native_runtime.get('runtime_start') != start or
            native_runtime.get('runtime_bytes') != end-start or
            native_runtime.get('routines') != len(runtime[0])):
        raise RuntimeHandoffError('independent three-base native runtime proof missing')
    if any(mapping.unresolved_bytes != end-start for mapping in maps):
        raise RuntimeHandoffError('unresolved compiler bytes extend beyond native runtime')
    if any(any(span.start < end and span.end > start and
               span.kind != 'runtime-opaque' for span in mapping.spans)
           for mapping in maps):
        raise RuntimeHandoffError('native runtime overlaps other compiler sources')
    return {
        'passes': 3, 'runtime_start': start, 'runtime_bytes': end-start,
        'runtime_routines': len(runtime[0]),
        'normalized_source_gaps': len(maps[0].gaps),
        'normalized_source_overlaps': len(maps[0].overlaps),
        'normalized_source_mismatches': len(maps[0].mismatches),
        'normalized_source_unresolved_bytes': maps[0].unresolved_bytes,
        'source_rewrites': patch_report,
        'source_literals': literal_report,
        'source_line_table': table_report,
        'source_kind_bytes': report['source_byte_kinds'],
        'runtime_handoff_verified': True,
        'full_program_optimized': False,
        'native_behavior_verified': False,
    }
