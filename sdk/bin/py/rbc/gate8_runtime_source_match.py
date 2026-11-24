# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""Check original HiSoft runtime bytes at their exact whole-program positions.

Actual BASIC compilation supplies selected routine IDs and boundaries.
Original HiSoft emitter execution supplies independent byte origins and typed
calculated words. RBC replacement emitters remain explicitly unresolved.
This proof does not declare a complete typed assembly or native equivalence.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from runpy import run_path
import hashlib
import re

from gate8_original_runtime_layout import _run_emitter
from gate8_original_runtime_types import N_ROUTINES, OriginalEmitter, SourceTransactions


class RuntimeMatchError(ValueError):
    """Original runtime emitter does not match the verified source."""


_RUNTIME_NAME = re.compile(r'RT([1-9][0-9]*)\Z')


def _verify_pause_source(expected: bytes):
    """Check the replacement against its original Python Z80 instruction source.

    The reference is produced through the same statements as the installed
    runtime. The native assembler resolves every named relative branch.
    Output image bytes are checked, never used as an instruction listing.
    """
    import ras
    import rld
    from z80asm import asm
    # The compiler checkpoint can contain an older installed runtime module. Audit the canonical
    # checked stage file, then compare it with real bytes.
    original_pause_source = run_path(
        str(Path(__file__).with_name('native_pause_rt.py')))['original_pause_source']
    raw, listing = original_pause_source(asm)
    if raw != expected:
        raise RuntimeMatchError('PAUSE source emission differs from original program')
    try:
        obj = ras.assemble_text(listing, 'rbc-pause.s')
        linked, *_ = rld.link([rld.Obj(obj, 'rbc-pause.sso')], [],
                              entry='start', stack=384)
        parsed = rld.parse_ssx(linked)
    except (ValueError, KeyError, TypeError, rld.LinkError,
            ras.AsmError) as exc:
        raise RuntimeMatchError('PAUSE native assembly failed') from exc
    if (parsed['image'] != expected or parsed['relocs'] or
            parsed['bss'] != 0 or parsed['entry'] != 0):
        raise RuntimeMatchError('PAUSE native assembly differs from original')
    return hashlib.sha256(listing.encode('utf-8')).hexdigest()


@dataclass(frozen=True)
class RuntimeMatch:
    report: dict
    source_signature: tuple


def _verify_poke_source(expected: bytes, load: int, entry: int,
                        settings: dict, *, peek=False, udg=False):
    """Independently native-link original RBC POKE emitter instructions.

    Settings come from the actual compiler instance, not from guessed
    addresses in a disassembled image. All relative process pointers and
    local control labels are resolved by ras/rld at the original load base.
    """
    import ras
    import rld
    from z80asm import asm
    kind = 'UDG' if udg else ('PEEK' if peek else 'POKE')
    if (not isinstance(settings, dict) or
            set(settings) != {'sysvar_offset', 'process_total', 'font_alias'} or
            any(type(settings[k]) is not int or not 0 <= settings[k] <= 65535
                for k in ('sysvar_offset', 'process_total')) or
            (settings['font_alias'] is not None and
             (type(settings['font_alias']) is not int or
              not 0 <= settings['font_alias'] <= 65535)) or
            not 0 <= load + entry < 65536 or
            load + entry + len(expected) > 65536):
        raise RuntimeMatchError(kind + ' source settings lack verified compiler values')
    code = run_path(str(Path(__file__).with_name('native_sysvars_rt.py')))
    raw, listing, sites = code['_native_udg_helper' if udg else ('_native_peek' if peek else '_native_poke')](
        asm, settings['sysvar_offset'], load, settings['process_total'],
        settings['font_alias'], entry, with_source=True)
    if raw != expected:
        raise RuntimeMatchError(kind + ' source emission differs from original program')
    try:
        obj = ras.assemble_text(listing, 'rbc-sysvar.s')
        linked, *_ = rld.link([rld.Obj(obj, 'rbc-sysvar.sso')], [],
                              entry='start', stack=384)
        parsed = rld.parse_ssx(linked)
        actual = bytes(rld.relocate(parsed['image'], parsed['relocs'],
                                    load + entry))
    except (ValueError, KeyError, TypeError, rld.LinkError,
            ras.AsmError) as exc:
        raise RuntimeMatchError(kind + ' native assembly failed') from exc
    if (actual != expected or parsed['relocs'] != list(sites) or
            parsed['bss'] != 0 or parsed['entry'] != 0):
        raise RuntimeMatchError(kind + ' native relocation differs from original')
    return hashlib.sha256(listing.encode('utf-8')).hexdigest(), len(sites)


def verify_runtime_source_match(code: bytes, rom: bytes, image: bytes,
                              base: int, spans, replacements: dict[int, str],
                              replacement_settings=None):
    """Witness each vendor emitter at its actual code offset, not at offset zero.

    Replacements are named by the *caller* from installed RBC runtime modules;
    they are never promoted to original HiSoft source, even if bytes match.
    """
    if (not isinstance(image, bytes) or type(base) is not int or
            not 0 <= base <= 65535 or base + len(image) > 65536 or
            not isinstance(replacements, dict) or any(
                type(n) is not int or not 1 <= n <= N_ROUTINES or
                not isinstance(reason, str) or not reason.strip()
                for n, reason in replacements.items())):
        raise RuntimeMatchError('invalid whole-program runtime storage or override')
    selected = []
    for span in spans:
        if span.kind != 'runtime-opaque':
            continue
        name = _RUNTIME_NAME.fullmatch(span.source)
        if not name:
            raise RuntimeMatchError('runtime source has no original emitter ID')
        n = int(name.group(1))
        if (not 1 <= n <= N_ROUTINES or type(span.start) is not int or
                type(span.end) is not int or not 0 <= span.start < span.end <= len(image) or
                (selected and (n <= selected[-1][0] or span.start != selected[-1][2]))):
            raise RuntimeMatchError('runtime source order or extent differs')
        selected.append((n, span.start, span.end))
    if not selected:
        raise RuntimeMatchError('original compiler selected no runtime emitters')
    machine = OriginalEmitter(code, rom, base)
    for n, start, _ in selected:
        row = 0x4000 + (n - 1) * 3
        machine.mem[row] = 1
        machine.mem[row + 1:row + 3] = start.to_bytes(2, 'little')
    count = vendor_bytes = copied_bytes = calculated_bytes = replacement_bytes = 0
    native_replacements = []
    verified_replacements = []
    source_signature = []
    for n, start, end in selected:
        slot = 0x77AF + 2 * (n - 1)
        original_entry = int.from_bytes(machine.mem[slot:slot + 2], 'little')
        if n in replacements:
            reason = replacements[n]
            if reason in ('native-peek', 'native-poke', 'native-udg') and replacement_settings is not None:
                from native_sysvars_rt import PEEK_RT, POKE_RT, UDG_HELPER_RT
                if (n, reason) not in ((PEEK_RT, 'native-peek'),
                                      (POKE_RT, 'native-poke'),
                                      (UDG_HELPER_RT, 'native-udg')):
                    raise RuntimeMatchError('system variable source assigned to wrong routine')
                digest, sites = _verify_poke_source(
                    image[start:end], base, start, replacement_settings,
                    peek=reason == 'native-peek', udg=reason == 'native-udg')
                verified_replacements.append((n, end - start))
                source_signature.append((n, start, end, 'typed-replacement',
                                         reason, digest, sites))
            elif reason == 'native-pause':
                from rtnames import RT
                if n != RT.PAUSE:
                    raise RuntimeMatchError('PAUSE source assigned to wrong routine')
                digest = _verify_pause_source(image[start:end])
                verified_replacements.append((n, end - start))
                source_signature.append((n, start, end, 'typed-replacement',
                                         reason, digest))
            else:
                native_replacements.append((n, end - start, reason))
                replacement_bytes += end - start
                source_signature.append((n, start, end, 'replacement', reason))
            continue
        if not original_entry:
            raise RuntimeMatchError(f'RT{n}: no original HiSoft source emitter')
        machine.writes.clear()
        machine.type_source = SourceTransactions(machine.mem, base)
        try:
            actual_end = _run_emitter(machine, n, start, counting=False)
            computed = machine.type_source.finish()
        except (ValueError, RuntimeError, IndexError) as exc:
            raise RuntimeMatchError(f'RT{n}: original emitter failed: {exc}') from exc
        writes = tuple(machine.writes)
        if (actual_end != end or len(writes) != end - start or
                tuple(p for p, _, _ in writes) != tuple(range(start, end)) or
                bytes(value for _, value, _ in writes) != image[start:end] or
                len(computed) + sum(origin is not None for _, _, origin in writes)
                != end - start):
            raise RuntimeMatchError(f'RT{n}: original source bytes or boundary differ')
        count += 1
        vendor_bytes += end - start
        calculated_bytes += len(computed)
        copied_bytes += sum(origin is not None for _, _, origin in writes)
        source_signature.append((
            n, start, end, 'original',
            tuple((p, origin) for p, _, origin in writes),
            tuple((e.position, e.kind, e.source_site, e.helper_pc,
                   e.target_offset) for e in computed)))
    total = selected[-1][2] - selected[0][1]
    if vendor_bytes + replacement_bytes + sum(size for _, size in verified_replacements) != total:
        raise RuntimeMatchError('runtime source bytes are not completely accounted for')
    return RuntimeMatch({
        'selected_routines': len(selected),
        'original_routines_verified': count,
        'original_source_bytes': vendor_bytes,
        'original_computed_source_bytes': calculated_bytes,
        'original_copied_source_bytes': copied_bytes,
        'replacement_routines_untyped': [n for n, _, _ in native_replacements],
        'replacement_source_bytes_untyped': replacement_bytes,
        'typed_replacement_routines_verified': [n for n, _ in verified_replacements],
        'typed_replacement_source_bytes': sum(size for _, size in verified_replacements),
        'complete_runtime_assembly_verified': False,
        'native_behavior_verified': False,
    }, tuple(source_signature))


def verify_three_runtime_sources(code: bytes, rom: bytes, images,
                                    bases, groups, replacements: dict[int, str],
                                    replacement_settings=None):
    """Require identical original source roles at three independent load bases."""
    if (any(len(x) != 3 for x in (images, bases, groups)) or
            len(set(bases)) != 3):
        raise RuntimeMatchError('three distinct compiler load bases required')
    if (replacement_settings is not None and
            (len(replacement_settings) != 3 or
             any(not isinstance(x, dict) for x in replacement_settings))):
        raise RuntimeMatchError('three compiler replacement layouts required')
    settings = replacement_settings if replacement_settings is not None else (None,) * 3
    results = [verify_runtime_source_match(code, rom, image, base, group,
                                          replacements, layout)
               for image, base, group, layout in
               zip(images, bases, groups, settings)]
    first = results[0]
    if any(other.source_signature != first.source_signature or
           other.report != first.report for other in results[1:]):
        raise RuntimeMatchError('original runtime source roles changed across bases')
    return {**first.report, 'original_source_bases_verified': 3}
