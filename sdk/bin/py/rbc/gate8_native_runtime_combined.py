# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""Reassemble one selected whole runtime from independently witnessed sources.

Real HiSoft runtime writers supply copied original compiler/ROM instructions
and source-typed words. RBC PAUSE/POKE supply explicit Python-side assembly.
Native ras/rld recalculates addresses crossing individual routine boundaries.
This is a runtime-region proof, not a whole BASIC program optimizer pass.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re

import ras
import rld
from gate8_original_runtime_layout import _run_emitter
from gate8_original_runtime_types import OriginalEmitter, SourceTransactions, START
from z80_python.disasm import disassemble_bytes
from native_pause_rt import original_pause_source
from gate8_native_guarded_val import guarded_val_assembly
from spectrum_runtime import guarded_val_bytes
from native_sysvars_rt import (_native_peek, _native_poke, _native_udg_helper,
                               PEEK_RT, POKE_RT, UDG_HELPER_RT)


class RuntimeCombinedError(ValueError):
    """Original runtime source cannot form a fully native linked region."""


@dataclass(frozen=True)
class VendorSection:
    number: int
    start: int
    end: int
    computed: tuple
    writes: tuple
    decoded: dict
    protected: dict


# These source-owned sequences follow a ROM calculator entry. The EF opcode
# calls the ZX 48K ROM calculator; subsequent bytes are treated as data. Each
# copied source location and byte is checked.
_ROM_CALCULATOR = {
    72: (0, bytes.fromhex('ef 09 38')),
    127: (7, bytes.fromhex(
        'ef a1 0f 34 37 16 04 34 80 41 00 00 80 32 02 a1 03 31 38')),
}


def _original_z80_and_calculator(n, writes, base, start):
    raw = bytes(v for _,v,_ in writes)
    code = {}
    protected = {}
    manifest = _ROM_CALCULATOR.get(n)
    if manifest is not None:
        where, source = manifest
        if (where+len(source) > len(raw) or raw[where:where+len(source)] != source or
                any(writes[i][2] is None or
                    writes[i][2] != writes[where][2]+(i-where)
                    for i in range(where,where+len(source)))):
            raise RuntimeCombinedError('original ROM calculator source differs')
    cursor = 0
    saw = False
    while cursor < len(raw):
        if manifest is not None and cursor == manifest[0]:
            where, source = manifest
            op = disassemble_bytes(raw[cursor:], base+start+cursor)
            if op.data != b'\xef' or op.text != 'RST 0x28':
                raise RuntimeCombinedError('ROM calculator entry is not original RST 28')
            code[cursor] = op
            protected[cursor+1] = source[1:]
            cursor += len(source)
            saw = True
            continue
        op = disassemble_bytes(raw[cursor:], base+start+cursor)
        if raw[cursor] == 0xef:
            raise RuntimeCombinedError('unclassified original ROM calculator bytecode')
        if op.data != raw[cursor:cursor+op.size]:
            raise RuntimeCombinedError('original instruction differs from byte source')
        code[cursor] = op
        cursor += op.size
    if (cursor != len(raw) or (manifest is not None and not saw) or
            sum(op.size for op in code.values())+
            sum(len(x) for x in protected.values()) != len(raw)):
        raise RuntimeCombinedError('original instruction/calculator boundary incomplete')
    return code, protected


def _original_sections(code, rom, image, base, selected, replacements):
    machine = OriginalEmitter(code, rom, base)
    for n, start, end in selected:
        row = 0x4000 + (n - 1) * 3
        machine.mem[row] = 1
        machine.mem[row + 1:row + 3] = start.to_bytes(2, 'little')
    result = []
    for n, start, end in selected:
        if n in replacements:
            continue
        machine.writes.clear()
        machine.type_source = SourceTransactions(machine.mem, base)
        emitted_end = _run_emitter(machine, n, start, counting=False)
        writes = tuple(machine.writes)
        computed = machine.type_source.finish()
        if (emitted_end != end or len(writes) != end - start or
                tuple(p for p, _, _ in writes) != tuple(range(start, end)) or
                bytes(v for _, v, _ in writes) != image[start:end]):
            raise RuntimeCombinedError(f'RT{n} original source does not match program')
        relative = tuple((p-start, v, source) for p, v, source in writes)
        copied = 0
        for _, byte, origin in relative:
            if origin is None:
                continue
            if 0 <= origin < len(rom):
                source_byte = rom[origin]
            elif START <= origin < START + len(code):
                source_byte = code[origin - START]
            else:
                raise RuntimeCombinedError('original runtime copy source outside ROM/tape')
            if byte != source_byte:
                raise RuntimeCombinedError('original runtime copied bytes differ from source')
            copied += 1
        if copied + len(computed) != len(relative):
            raise RuntimeCombinedError('original runtime source ownership incomplete')
        decoded, protected = _original_z80_and_calculator(n, relative, base, start)
        result.append(VendorSection(n, start, end, computed, writes, decoded, protected))
    return tuple(result)


def _runtime_spans(spans, image):
    selected = []
    for span in spans:
        if span.kind != 'runtime-opaque':
            continue
        name = re.fullmatch(r'RT([1-9][0-9]*)', span.source)
        if name is None:
            raise RuntimeCombinedError('runtime span has no source routine ID')
        n = int(name.group(1))
        if (selected and (n <= selected[-1][0] or span.start != selected[-1][2]) or
                not 0 <= span.start < span.end <= len(image)):
            raise RuntimeCombinedError('runtime spans are not ordered and contiguous')
        selected.append((n, span.start, span.end))
    if not selected:
        raise RuntimeCombinedError('no source-owned runtime region')
    return tuple(selected)


def _replacement_listing(n, start, base, settings, expected):
    from rtnames import RT
    from z80asm import asm
    if n == RT.PAUSE:
        raw, source = original_pause_source(asm)
        if raw != expected:
            raise RuntimeCombinedError('source PAUSE does not match original program')
        sites = ()
        label = 'rbc_pause_entry'
        # Rename only the entry label; inner jumps keep their original names.
        source = source.replace('start:', label+':')
    elif n in (RT.VAL, RT.VAL_STR):
        token = 0x1D if n == RT.VAL else 0x18
        raw = guarded_val_bytes(token)
        source = guarded_val_assembly(token)
        if raw != expected:
            raise RuntimeCombinedError('guarded VAL source does not match original program')
        sites = ()
        label = 'rbc_val_entry' if n == RT.VAL else 'rbc_vals_entry'
        if n == RT.VAL_STR:
            source = source.replace('rbc_val_', 'rbc_vals_')
        source = source.replace('start:', label+':')
    elif n == PEEK_RT:
        if (not isinstance(settings, dict) or
                any(k not in settings for k in
                    ('sysvar_offset', 'process_total', 'font_alias'))):
            raise RuntimeCombinedError('source PEEK layout not independently witnessed')
        raw, source, sites = _native_peek(
            asm, settings['sysvar_offset'], base,
            settings['process_total'], settings['font_alias'], start,
            with_source=True)
        if raw != expected:
            raise RuntimeCombinedError('source PEEK does not match original program')
        label = 'rbc_peek_entry'
        source = (source.replace('start:', label+':')
                  .replace('start+', label+'+')
                  .replace('rbc_local_', 'rbc_peek_local_'))
    elif n == POKE_RT:
        if (not isinstance(settings, dict) or
                any(k not in settings for k in
                    ('sysvar_offset', 'process_total', 'font_alias'))):
            raise RuntimeCombinedError('source POKE layout not independently witnessed')
        raw, source, sites = _native_poke(
            asm, settings['sysvar_offset'], base,
            settings['process_total'], settings['font_alias'], start,
            with_source=True)
        if raw != expected:
            raise RuntimeCombinedError('source POKE does not match original program')
        label = 'rbc_poke_entry'
        source = (source.replace('start:', label+':')
                  .replace('start+', label+'+')
                  .replace('rbc_local_', 'rbc_poke_local_'))
    elif n == UDG_HELPER_RT:
        if (not isinstance(settings, dict) or
                any(k not in settings for k in
                    ('sysvar_offset', 'process_total', 'font_alias'))):
            raise RuntimeCombinedError('source UDG layout not independently witnessed')
        raw, source, sites = _native_udg_helper(
            asm, settings['sysvar_offset'], base,
            settings['process_total'], settings['font_alias'], start,
            with_source=True)
        if raw != expected:
            raise RuntimeCombinedError('source UDG differs from original program')
        label = 'rbc_udg_entry'
        source = (source.replace('start:', label+':')
                  .replace('start+', label+'+')
                  .replace('rbc_local_', 'rbc_udg_local_'))
    else:
        raise RuntimeCombinedError('untyped replacement routine')
    lines = [line for line in source.splitlines()
             if line.strip() not in ('section text', 'global start')]
    if not lines or lines[0] != label+':':
        raise RuntimeCombinedError('replacement entry does not have a typed label')
    return lines, tuple(sites)


def _vendor_listing(section, base, runtime_start, known_instruction_offsets):
    """Resolve source-owned Z80 operands against *global* instruction labels."""
    lines = []
    offsets = sorted(set(section.decoded)|set(section.protected))
    relocations = {}
    for event in section.computed:
        if event.kind != 'reloc-low':
            continue
        partner = [x for x in section.computed if x.position == event.position + 1
                   and x.kind == 'reloc-high' and x.target_offset == event.target_offset]
        if len(partner) != 1:
            raise RuntimeCombinedError('original runtime relocation lacks matching high byte')
        if not 0 <= event.target_offset < 65536:
            raise RuntimeCombinedError('source relocation outside process')
        relocations[event.position] = event.target_offset
    for rel_offset in offsets:
        absolute_offset = section.start + rel_offset
        if rel_offset in section.protected:
            raw = section.protected[rel_offset]
            lines.append('  defb ' + ','.join(f'0x{byte:02x}' for byte in raw))
            continue
        op = section.decoded[rel_offset]
        # Every routine's own entry and any cross-routine target can be labelled.
        if absolute_offset in known_instruction_offsets:
            lines.append(f'original_rt_{absolute_offset:04x}:')
        expression = op.text.lower()
        last = op.operands[-1].lower() if op.operands else ''
        if op.mnemonic in ('JP', 'JR', 'DJNZ', 'CALL'):
            if last.startswith('0x'):
                target = int(last, 16) - base
                if target in known_instruction_offsets:
                    expression = expression.replace(last, f'original_rt_{target:04x}')
                elif int(last,16) >= 0x4000:
                    raise RuntimeCombinedError(f'RT{section.number} unknown branch {expression} at {absolute_offset}: {hex(int(last,16))}, offset {target}, nearest={sorted(p for p in known_instruction_offsets if target-10<p<target+12)}')
            elif last not in ('(hl)', '(ix)', '(iy)'):
                raise RuntimeCombinedError('original runtime branch is not typed')
        sites = [(pos, target) for pos, target in relocations.items()
                 if absolute_offset < pos < absolute_offset + op.size]
        if len(sites) > 1:
            raise RuntimeCombinedError('multiple source relocations in one instruction')
        for pos, target in sites:
            if pos != absolute_offset + op.size - 2:
                raise RuntimeCombinedError('source relocation is not terminal operand')
            if target not in known_instruction_offsets:
                raise RuntimeCombinedError('original source relocation lacks code boundary')
            token = f'0x{(target+base)&65535:04x}'
            label = f'original_rt_{target:04x}'
            if token in expression:
                expression = expression.replace(token, label)
            elif label not in expression:
                raise RuntimeCombinedError('original relocation lacks matching address operand')
        lines.append('  '+expression)
    return lines, relocations


def native_runtime_region(code: bytes, rom: bytes, image: bytes, base: int,
                          spans, replacements, settings):
    """Native link of all selected original and replacement runtime sources."""
    if not isinstance(image, bytes) or not 0 <= base <= 65535 or base + len(image) > 65536:
        raise RuntimeCombinedError('invalid compiler image location')
    from rtnames import RT
    selected = _runtime_spans(spans, image)
    start, end = selected[0][1], selected[-1][2]
    replacements_expected = {PEEK_RT: 'native-peek', POKE_RT: 'native-poke',
                             UDG_HELPER_RT: 'native-udg',
                             RT.PAUSE: 'native-pause',
                             RT.VAL: 'guarded-val', RT.VAL_STR: 'guarded-vals'}
    actual = {n for n, _, _ in selected if n in replacements_expected}
    if any(replacements.get(n) != replacements_expected[n]
           for n in actual):
        raise RuntimeCombinedError('selected runtime needs complete typed replacement sources')
    if any(n not in replacements_expected or replacements[n] != replacements_expected[n]
           for n in replacements):
        raise RuntimeCombinedError('unknown runtime replacement source kind')
    sections = _original_sections(code, rom, image, base, selected, replacements)
    by_id = {section.number: section for section in sections}
    # Labels are justified by independently decoded original compiler/ROM instruction
    # sites, not by searching for plausible branch bytes.
    boundaries = {section.start + pos for section in sections
                  for pos in section.decoded}
    lines = ['    section text', '    global start', 'start:']
    expected_rel = set()
    for n, a, b in selected:
        if n in replacements:
            source, rel = _replacement_listing(n, a, base, settings, image[a:b])
            lines.extend(source)
            expected_rel.update(a-start+site for site in rel)
            continue
        section = by_id[n]
        source, rel = _vendor_listing(section, base, start, boundaries)
        lines.extend(source)
        expected_rel.update(site - start for site in rel)
    assembly = '\n'.join(lines)+'\n'
    try:
        obj = ras.assemble_text(assembly, 'real-original-runtime-region.s')
        ssx, *_ = rld.link([rld.Obj(obj, 'real-original-runtime-region.sso')],
                            [], entry='start', stack=384)
        linked = rld.parse_ssx(ssx)
        relocated = bytes(rld.relocate(linked['image'], linked['relocs'], base + start))
    except (ras.AsmError, rld.LinkError, ValueError, TypeError) as exc:
        raise RuntimeCombinedError('combined native runtime assembly or link failed: '+str(exc)) from exc
    if (len(linked['image']) != end-start or relocated != image[start:end] or
            linked['bss'] != 0 or linked['entry'] != 0):
        raise RuntimeCombinedError('native combined runtime differs from original compiler')
    if sorted(expected_rel) != linked['relocs']:
        raise RuntimeCombinedError('native relocation sites differ from original and replacement sources')
    return {
        'routines': len(selected), 'original_routines': len(sections),
        'replacement_routines': len(selected)-len(sections),
        'runtime_bytes': end-start, 'runtime_start': start,
        'original_relocations': sum(1 for section in sections
                                    for item in section.computed if item.kind == 'reloc-low'),
        'all_relocations': len(linked['relocs']),
        'bss_bytes': linked['bss'], 'stack_bytes': linked['stack'],
        'total_region_storage_bytes': len(linked['image'])+linked['bss']+linked['stack'],
        'native_file_bytes': len(ssx),
        'assembly_sha256': hashlib.sha256(assembly.encode()).hexdigest(),
        'native_sha256': hashlib.sha256(ssx).hexdigest(),
        'native_region_verified': True,
        'full_program_optimized': False,
        'native_behavior_verified': False,
    }


def verify_three_native_runtime_regions(code, rom, images, bases, groups,
                                        replacements, settings):
    if any(len(x)!=3 for x in (images,bases,groups,settings)) or len(set(bases))!=3:
        raise RuntimeCombinedError('three distinct compiler passes required')
    runs = [native_runtime_region(code,rom,img,base,spans,replacements,opts)
            for img,base,spans,opts in zip(images,bases,groups,settings)]
    first = runs[0]
    for other in runs[1:]:
        if other != first:
            raise RuntimeCombinedError('native runtime source changed across three compiler bases')
    return {**first,'passes':3}
