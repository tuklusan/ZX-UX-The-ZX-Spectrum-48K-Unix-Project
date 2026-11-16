# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""Native-link a *baseline* entire HiSoft source image, including typed runtime.

The independently audited compiler source emissions and original runtime
writer are the only byte producers. This remains an unoptimized baseline:
fixed 48K addresses, indirect branches, and process entry/loader semantics
are not proven safe for whole-program peephole optimization by this module.
"""
from __future__ import annotations

import hashlib
import re

import ras
import rld
from symbolic_z80 import SymbolicProgram
from symbolic_from_source import _validate_static_instruction
from symbolic_patch_binding import bind_three_source_passes
from symbolic_original_literals import protect_three_original_literals
from symbolic_line_table import bind_three_line_tables
from symbolic_source_boundaries import inspect_source_boundaries, verify_three_source_maps
from symbolic_relative_branches import inspect_relative_branches, verify_three_relative_passes
from gate8_native_runtime_combined import (
    _original_sections, _runtime_spans, _replacement_listing, _vendor_listing)
from gate8_runtime_handoff import verify_three_runtime_handoffs
from native_sysvars_rt import (PEEK_RT, POKE_RT, UDG_HELPER_RT, BSS_BYTES,
                               _native_peek, _native_poke, _native_udg_helper)
from stkend_end_pointer import original_stkend_end_marker


class WholeBaselineError(ValueError):
    """The full native baseline cannot be proved from original source events."""


def _runtime_listing(code, rom, image, base, spans, replacements, settings):
    """Read only independently witnessed runtime writers; not linked bytes."""
    selected = _runtime_spans(spans, image)
    sections = _original_sections(code, rom, image, base, selected, replacements)
    by_id = {section.number: section for section in sections}
    instructions = {section.start + pos for section in sections
                    for pos in section.decoded}
    listing = []
    entry_aliases = {}
    for n, first, last in selected:
        if n in replacements:
            if n in (PEEK_RT, POKE_RT, UDG_HELPER_RT):
                from z80asm import asm
                if (not isinstance(settings, dict) or
                        any(key not in settings for key in
                            ('sysvar_offset', 'process_total', 'font_alias'))):
                    raise WholeBaselineError('native sysvar runtime layout has no source witness')
                entry = {PEEK_RT: 'rbc_peek_entry', POKE_RT: 'rbc_poke_entry',
                         UDG_HELPER_RT: 'rbc_udg_entry'}[n]
                fn = {PEEK_RT: _native_peek, POKE_RT: _native_poke,
                      UDG_HELPER_RT: _native_udg_helper}[n]
                raw, source = fn(
                    asm, settings['sysvar_offset'], base,
                    settings['process_total'], settings['font_alias'], first,
                    whole_program_symbols={
                        'entry_label': entry,
                        'bss_label': 'rbc_sysvar_storage',
                        'end_label': 'rbc_process_end',
                        'start_label': 'start'})
                if raw != image[first:last]:
                    raise WholeBaselineError('symbolic native sysvar source differs from original bytes')
                lines = source.splitlines()
            else:
                lines, _ = _replacement_listing(n, first, base, settings,
                                                 image[first:last])
            labels = [line.strip()[:-1] for line in lines
                      if line.strip().endswith('_entry:')]
            if len(labels) != 1 or labels[0] in entry_aliases:
                raise WholeBaselineError('typed replacement lacks a unique entry')
            entry_aliases[labels[0]] = first
        else:
            lines, _ = _vendor_listing(by_id[n], base, selected[0][1], instructions)
        listing.extend(lines)
    return selected, tuple(listing), entry_aliases


def _source_program(events, image, base, text_end, bss, assembler,
                    code, rom, replacements, settings):
    """Build typed Z80 and protected data in original linear source order."""
    mapping = inspect_source_boundaries(events, image, base, text_end, bss, assembler)
    if mapping.gaps or mapping.overlaps or mapping.mismatches:
        raise WholeBaselineError('source image has unproved byte ownership')
    spans = sorted(mapping.spans, key=lambda s: s.start)
    if not spans or spans[0].start != 0 or spans[-1].end != len(image) or any(
            x.end != y.start for x, y in zip(spans, spans[1:])):
        raise WholeBaselineError('compiler source sections do not cover the whole image')
    selected, listing, replacements_at = _runtime_listing(
        code, rom, image, base, spans, replacements, settings)
    runtime_start, runtime_end = selected[0][1], selected[-1][2]
    if mapping.unresolved_bytes != runtime_end - runtime_start:
        raise WholeBaselineError('source has unresolved bytes outside verified runtime')
    runtime_instruction_sites = {int(line.strip()[len('original_rt_'):-1], 16)
        for line in listing if line.strip().startswith('original_rt_')
        and line.strip().endswith(':')}
    source_instructions = {span.start for span in spans
                           if span.kind in ('instruction','instruction-relocated')}
    targets = {span.target for span in spans if span.target is not None}
    relatives = inspect_relative_branches(spans, text_end, assembler)
    targets.update(branch.target for branch in relatives.values())
    entry_sites = set(source_instructions) | runtime_instruction_sites | set(replacements_at.values())
    # HiSoft sometimes takes the address of an immediate operand as mutable
    # storage (not as an instruction entry). A symbol for the *owner's
    # start* plus its verified operand offset preserves the instruction
    # mnemonic and relocates this pointer without splitting executable bytes
    # into DB/DW. Only the immediate word of a typed three-byte LD rr,nn,
    # CALL nn, or JP nn is supported.
    interior_words = {}
    for span in spans:
        target = span.target
        if target is None or target >= text_end:
            continue
        op = span.source.strip().split(None, 1)[0].lower()
        if op in ('call', 'jp') or span.kind == 'table-relocated':
            if target not in entry_sites:
                raise WholeBaselineError('control relocation target lacks source instruction')
        elif target not in entry_sites and not any(
                data.kind == 'inline-data' and data.start <= target < data.end
                for data in spans):
            owners = [owner for owner in spans if owner.start < target < owner.end]
            if (len(owners) != 1 or owners[0].kind not in
                    ('instruction', 'instruction-relocated') or
                    owners[0].end - owners[0].start != 3 or
                    not re.fullmatch(r'(?:ld\s+(?:bc|de|hl|sp)\s*,\s*|call\s+|jp\s+)(?:nn|(?:\$[0-9a-f]+|\d+))',
                                     owners[0].source.strip().lower())):
                raise WholeBaselineError('source pointer targets an unowned text byte')
            interior_words[target] = (owners[0].start, target - owners[0].start)
    if any(branch.target not in entry_sites for branch in relatives.values()):
        raise WholeBaselineError('relative branch does not target a typed instruction')
    if any(target is None or (not 0 <= target < len(image) + bss and
              not any(original_stkend_end_marker(events, image, base, bss,
                                                  event.position, target)
                      for event in events if event.kind == 'relocation' and
                      event.symbol_offset == target)) for target in targets):
        raise WholeBaselineError('source relocation target outside process')
    def name(address):
        if address in interior_words:
            owner, offset = interior_words[address]
            anchor = 'start' if owner == 0 else f'source_{owner:04x}'
            return f'{anchor}+{offset}'
        return 'start' if address == 0 else f'source_{address:04x}'
    marks = targets | {0} | {owner for owner, _ in interior_words.values()}
    native_bss_labels = {}
    if any(n in (PEEK_RT, POKE_RT, UDG_HELPER_RT) for n, _, _ in selected):
        if (not isinstance(settings, dict) or
                type(settings.get('sysvar_offset')) is not int or
                type(settings.get('process_total')) is not int):
            raise WholeBaselineError('native sysvar storage positions not independently typed')
        bss_start = settings['sysvar_offset']
        process_end = settings['process_total']
        if not (len(image) <= bss_start and
                bss_start + BSS_BYTES <= process_end <= len(image) + bss):
            raise WholeBaselineError('native sysvar storage exceeds compiler BSS')
        native_bss_labels = {bss_start: 'rbc_sysvar_storage',
                             process_end: 'rbc_process_end'}
    program = SymbolicProgram()
    actual = 0
    runtime_inserted = False
    fixed_opaque = 0
    indirect = 0
    for span in spans:
        if span.start != actual:
            raise WholeBaselineError('source compiler byte offset changed')
        if span.start >= text_end and program._section != 'data':
            program.section('data')
        if span.kind == 'runtime-opaque':
            if not runtime_inserted:
                if span.start != runtime_start:
                    raise WholeBaselineError('native runtime started inside another source')
                runtime_inserted = True
                for raw in listing:
                    line = raw.strip()
                    if not line or line in ('section text', 'global start'):
                        continue
                    if line.endswith(':'):
                        label = line[:-1]
                        if label.startswith('original_rt_'):
                            offset = int(label[len('original_rt_'):], 16)
                            if offset in marks:
                                program.label(name(offset))
                        elif label in replacements_at:
                            offset = replacements_at[label]
                            if offset in marks:
                                program.label(name(offset))
                        program.label(label)
                    elif line.startswith('defb '):
                        # Original ROM-calculator bytecode has an explicit source witness
                        # and must never enter an optimizer.
                        program.binary(bytes(int(byte.strip(), 0)
                                             for byte in line[5:].split(',')))
                    else:
                        program.instruction(line)
            actual = span.end
            continue
        if span.start in marks:
            program.label(name(span.start), entry=span.start == 0)
        if span.kind in ('instruction', 'instruction-relocated'):
            if span.kind == 'instruction-relocated':
                source = span.source.replace('nn', name(span.target))
                if source == span.source:
                    raise WholeBaselineError('source relocation has no typed operand')
            else:
                relative = relatives.get(span.start)
                if relative is not None:
                    separator = ' ' if relative.opcode in ('jr', 'djnz') else ','
                    source = relative.opcode + separator + name(relative.target)
                else:
                    source = span.source
                    try:
                        _validate_static_instruction(source)
                    except ValueError:
                        # The original assembler's fixed numeric/indirect instruction
                        # is byte-owned and kept unchanged. It is not admitted to
                        # CFG/liveness optimization yet.
                        fixed_opaque += 1
                        if source.strip().lower().startswith(('jp (','call (')):
                            indirect += 1
            program.instruction(source)
        elif span.kind == 'table-relocated':
            program.reference(name(span.target))
        elif span.kind in ('inline-data', 'data-source'):
            stops = sorted(t for t in marks if span.start < t < span.end)
            begin = span.start
            for end in (*stops, span.end):
                program.binary(image[begin:end])
                if end in stops:
                    program.label(name(end))
                begin = end
        else:
            raise WholeBaselineError('opaque compiler source outside native runtime')
        actual = span.end
    if actual != len(image) or not runtime_inserted:
        raise WholeBaselineError('native runtime or original source extent missing')
    if bss or len(image) in marks:
        program.section('bss')
        last = len(image)
        bounds = sorted(t for t in marks | set(native_bss_labels)
                        if len(image) <= t < len(image) + bss)
        for offset in bounds:
            program.reserve(offset - last)
            if offset in marks:
                program.label(name(offset))
            if offset in native_bss_labels:
                program.label(native_bss_labels[offset])
            last = offset
        program.reserve(len(image) + bss - last)
        if len(image) + bss in native_bss_labels:
            program.label(native_bss_labels[len(image) + bss])
        if bss == 0 and len(image) in marks:
            program.label(name(len(image)))
    source = program.assembly()
    return source, {
        'source_emitter_instructions': mapping.executable_instruction_count,
        'native_runtime_source_routines': len(selected),
        'fixed_or_indirect_instructions_not_type_approved': fixed_opaque,
        'indirect_branch_instructions_unresolved_for_optimization': indirect,
        'source_text_bytes': text_end,
        'source_data_bytes': len(image) - text_end,
    }, mapping, (runtime_start, runtime_end)


def verify_three_whole_native_baselines(events, images, bases, text_ends,
                                         bss_sizes, assembler, code, rom,
                                         replacements, settings, native_runtime,
                                         *, optimizer=None, source_sink=None,
                                         max_bytes=14000):
    """Native-link *all* original source bytes, compare three relocated images.

    The SSX wrapper, game behavior, and optimizer are explicitly outside this
    gate. This proof cannot publish the game or set Gate 8 complete.
    """
    verify_three_runtime_handoffs(events, images, bases, text_ends,
                                  bss_sizes, assembler, native_runtime)
    patched, _ = bind_three_source_passes(events, images, bases, text_ends)
    literals, _ = protect_three_original_literals(patched, images)
    normalized, _ = bind_three_line_tables(literals, images, bases,
                                           text_ends, bss_sizes)
    whole = [_source_program(e, img, base, end, bss, assembler, code, rom,
                              replacements, opts)
             for e, img, base, end, bss, opts in
             zip(normalized, images, bases, text_ends, bss_sizes, settings)]
    if len({source for source, _, _, _ in whole}) != 1:
        raise WholeBaselineError('typed whole source differs across original bases')
    sources = [item[0] for item in whole]
    counts = [item[1] for item in whole]
    if counts[1:] != counts[:1] * 2:
        raise WholeBaselineError('source type classifications changed across bases')
    sites = [item[2] for item in whole]
    verify_three_source_maps(sites, bases)
    verify_three_relative_passes([inspect_relative_branches(
        m.spans, end, assembler) for m, end in zip(sites, text_ends)], bases)
    if any(item[3] != whole[0][3] for item in whole):
        raise WholeBaselineError('typed runtime section changed across bases')
    native_sha = None
    source_relocations = {span.end - 2 for span in sites[0].spans
                          if span.kind in ('instruction-relocated','table-relocated')}
    native_info = None
    for index, (source, image, base, bss) in enumerate(
            zip(sources, images, bases, bss_sizes)):
        try:
            obj = ras.assemble_text(source, 'rbc-whole-source-baseline.s')
            ssx, *_ = rld.link([rld.Obj(obj, 'rbc-whole-source-baseline.sso')],
                               [], entry='start', stack=384)
            parsed = rld.parse_ssx(ssx)
            loaded = bytes(rld.relocate(parsed['image'], parsed['relocs'], base))
        except (ValueError, TypeError, AttributeError, IndexError) as exc:
            raise WholeBaselineError('whole native source link failed: ' + str(exc)) from exc
        if (loaded != image or len(parsed['image']) != len(image) or
                parsed['entry'] != 0 or parsed['bss'] != bss or parsed['stack'] != 384):
            raise WholeBaselineError('whole native source changes compiler program bytes/storage')
        actual_outside = {site for site in parsed['relocs']
                          if not whole[0][3][0] <= site < whole[0][3][1]}
        actual_inside = [site for site in parsed['relocs']
                         if whole[0][3][0] <= site < whole[0][3][1]]
        if actual_outside != source_relocations or len(actual_inside) != (
                native_runtime['all_relocations']):
            raise WholeBaselineError('whole source relocations differ from original emitters')
        digest = hashlib.sha256(ssx).hexdigest()
        if native_sha is not None and digest != native_sha:
            raise WholeBaselineError('native full-source output changed between bases')
        native_sha = digest
        current = {
            'native_file_bytes': len(ssx), 'native_image_bytes': len(parsed['image']),
            'native_bss_bytes': parsed['bss'], 'native_stack_bytes': parsed['stack'],
            'native_total_bytes': len(parsed['image']) + parsed['bss'] + parsed['stack'],
            'native_relocations': len(parsed['relocs']),
        }
        if native_info is not None and current != native_info:
            raise WholeBaselineError('native dimensions changed across original compiler bases')
        native_info = current
        if max_bytes and max(len(ssx), current['native_total_bytes']) > max_bytes:
            raise WholeBaselineError(
                'native source baseline exceeds default memory limit: '
                f"file={len(ssx)}, image={len(parsed['image'])}, "
                f"bss={parsed['bss']}, stack={parsed['stack']}, "
                f"total={current['native_total_bytes']}, limit={max_bytes}")
    candidate = None
    if optimizer is not None:
        from gate8_native_whole_optimizer import (WholeOptimizerError,
                                                  verify_whole_optimizer_candidate)
        try:
            candidate = verify_whole_optimizer_candidate(sources[0], ssx, optimizer)
        except WholeOptimizerError as exc:
            # Failure to prove a safe optimizer candidate must not invalidate the separately
            # linked, byte-identical original native program. Record that rejection, never
            # promote it to a successful link.
            candidate = {
                'blocker': str(exc),
                'native_baseline_sha256': native_sha,
                'native_candidate_link_verified': False,
                'optimizer_candidate_admitted_for_publication': False,
                'native_behavior_verified': False,
                'full_program_optimized': False,
            }
        if candidate['native_baseline_sha256'] != native_sha:
            raise WholeBaselineError('optimizer compared a different native baseline')
    if source_sink is not None:
        # Expose only the fully checked, three-base byte-identical pre-link source. Callers
        # must perform their own native wrapper/loader checks.
        source_sink(sources[0])
    return {
        **counts[0], **native_info,
        'native_whole_optimizer_candidate': candidate,
        'source_assembly_sha256': hashlib.sha256(sources[0].encode()).hexdigest(),
        'native_sha256': native_sha,
        'native_source_bases': 3,
        'native_image_byte_exact': True,
        'all_source_relocations_verified': True,
        'native_whole_source_baseline_linked': True,
        'full_program_optimized': False,
        'ssx_loader_or_entry_verified': False,
        'native_behavior_verified': False,
    }
