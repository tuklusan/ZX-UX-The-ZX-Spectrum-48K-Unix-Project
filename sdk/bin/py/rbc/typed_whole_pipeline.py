# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""Fail-closed three-pass bridge from HiSoft source producers to native Z80.

This module accepts only original source-emission events, never a disassembled
image. It does not mark a candidate gameplay-verified or publish an SSX.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from symbolic_emit_sites import inspect_emit_sites, verify_three_emit_sites
from symbolic_fragments import inspect_final_fragments, verify_three_fragment_passes
from symbolic_from_source import from_source
from symbolic_patch_binding import bind_three_source_passes
from symbolic_original_literals import protect_three_original_literals
from symbolic_line_table import bind_three_line_tables
from symbolic_relative_branches import (inspect_relative_branches,
                                        verify_three_relative_passes)
from symbolic_source_boundaries import (inspect_source_boundaries,
                                        verify_three_source_maps)
from symbolic_whole_cfg import inspect_whole_cfg, verify_three_whole_cfg


class SourcePipelineError(ValueError):
    """A compiler pass cannot safely enter the full-program assembler."""


@dataclass(frozen=True)
class VerifiedSource:
    program: object
    source_report: dict
    compiled_image: bytes
    original_base: int
    reloc_byte_offsets: frozenset[int]


def verify_and_build(events, images, bases, text_ends, bss_sizes,
                     assembler: Callable, *, entry_offsets=(0,)) -> VerifiedSource:
    """Require three independent source maps before building a symbolic program.

    Raw direct-word patches are rebound only after their base-dependent targets
    have passed all three original compile passes. Runtime writers without
    independently typed source remain opaque, so ownership will reject them.
    """
    if (any(len(items) != 3 for items in
            (events, images, bases, text_ends, bss_sizes)) or
            any(not isinstance(b, int) or isinstance(b, bool) or
                not 0 <= b <= 65535 for b in bases) or
            len(set(bases)) != 3 or
            any(not isinstance(image, bytes) for image in images) or
            any(not isinstance(size, int) or isinstance(size, bool) or
                size < 0 for size in bss_sizes) or
            len(set(bss_sizes)) != 1):
        raise SourcePipelineError('three valid compiler bases and equal BSS layouts required')
    try:
        source_sites = [inspect_emit_sites(group) for group in events]
        site_report = verify_three_emit_sites(source_sites, bases)
        fragments = [inspect_final_fragments(group, image, end, assembler)
                     for group, image, end in zip(events, images, text_ends)]
        fragment_report = verify_three_fragment_passes(fragments, bases)
        patched, patch_report = bind_three_source_passes(events, images, bases,
                                                         text_ends)
        typed, literal_report = protect_three_original_literals(patched, images)
        typed, line_report = bind_three_line_tables(typed, images, bases,
                                                   text_ends, bss_sizes)
        maps = [inspect_source_boundaries(group, image, base, end, bss,
                                         assembler)
                for group, image, base, end, bss in
                zip(typed, images, bases, text_ends, bss_sizes)]
        map_report = verify_three_source_maps(maps, bases)
        if not all(mapping.fully_typed for mapping in maps):
            raise SourcePipelineError('original compiler has unresolved source bytes')
        relative = [inspect_relative_branches(mapping.spans, end, assembler)
                    for mapping, end in zip(maps, text_ends)]
        relative_report = verify_three_relative_passes(relative, bases)
        flows = [inspect_whole_cfg(mapping.spans, end, assembler, entry_offsets)
                 for mapping, end in zip(maps, text_ends)]
        flow_report = verify_three_whole_cfg(flows, bases)
        programs = [from_source(group, image, base, end, bss, assembler,
                                entry_offsets=entry_offsets)
                    for group, image, base, end, bss in
                    zip(typed, images, bases, text_ends, bss_sizes)]
    except SourcePipelineError:
        raise
    except (ValueError, TypeError, AttributeError, OverflowError) as exc:
        raise SourcePipelineError(str(exc)) from exc
    originals = tuple(program.assembly() for program in programs)
    if originals[1:] != originals[:1] * 2:
        raise SourcePipelineError('symbolic assembly changed between compiler passes')
    reloc_sites = set()
    for span in maps[0].spans:
        if span.kind in ('instruction-relocated', 'table-relocated'):
            reloc_sites.update(range(span.end - 2, span.end))
    return VerifiedSource(programs[0], {
        'passes': 3, 'compiler_call_sites': site_report,
        'final_source_fragments': fragment_report,
        'source_word_patches': patch_report,
        'protected_original_literals': literal_report,
        'source_line_table': line_report,
        'source_boundaries': map_report,
        'relative_branches': relative_report,
        'whole_source_control_flow': flow_report,
        'full_program_source_owned': True,
        'source_bss_bytes': bss_sizes[0],
        'native_behavior_verified': False,
    }, images[0], bases[0], frozenset(reloc_sites))


def link_source_pair(source: VerifiedSource, ras, rld, optimizer: Callable,
                     *, stack: int = 384, max_memory: int = 14000):
    """Link both variants; compare exact original non-relocated image bytes.

    Native links and memory accounting alone cannot establish runtime
    equivalence. The caller must run separate process/native behavior gates.
    """
    plain, plain_sizes = source.program.optimize(lambda text: text, ras, rld,
                                                 stack=stack, max_memory=max_memory)
    parsed = rld.parse_ssx(plain)
    original = parsed['image']
    if len(original) != len(source.compiled_image):
        raise SourcePipelineError('native plain image differs from original extent')
    expected_bytes = source.reloc_byte_offsets
    actual_bytes = frozenset(offset for site in parsed['relocs']
                             for offset in (site, site + 1))
    if actual_bytes != expected_bytes:
        raise SourcePipelineError('native relocation sites differ from typed source')
    if (parsed['size'] != len(plain) or parsed['entry'] != 0 or
            parsed['bss'] != source.source_report['source_bss_bytes']):
        raise SourcePipelineError('native entry or storage layout differs from source')
    loaded = bytes(rld.relocate(original, parsed['relocs'], source.original_base))
    if loaded != source.compiled_image:
        offset = next(i for i, pair in enumerate(zip(loaded, source.compiled_image))
                      if pair[0] != pair[1])
        if offset in expected_bytes:
            raise SourcePipelineError(
                f'native plain relocated operand differs at byte {offset}')
        raise SourcePipelineError(
            f'native plain image differs outside typed relocation at byte {offset}')
    candidate, sizes = source.program.optimize(optimizer, ras, rld,
                                               stack=stack, max_memory=max_memory)
    return plain, candidate, {
        'plain': plain_sizes,
        'candidate': sizes,
        'source': source.source_report,
        'native_links_verified': True,
        'native_behavior_verified': False,
    }


def verify_and_build_with_runtime_sources(events, images, bases, text_ends,
                                          bss_sizes, assembler, witnesses,
                                          observed_traces, *, entry_offsets=(0,)):
    """Admit externally typed runtime spans to the normal full-source gate.

    A runtime witness never bypasses unresolved boundaries elsewhere in the
    compiler. The native baseline must still be independently linked and
    checked using link_source_pair before considering an optimizer candidate.
    """
    from dataclasses import replace
    from typed_runtime_bridge import splice_three_runtime_sources

    typed, report = splice_three_runtime_sources(
        events, images, bases, witnesses, assembler,
        observed_traces=observed_traces)
    result = verify_and_build(typed, images, bases, text_ends, bss_sizes,
                              assembler, entry_offsets=entry_offsets)
    return replace(result, source_report={**result.source_report,
                                          'runtime_source_bridge': report})
