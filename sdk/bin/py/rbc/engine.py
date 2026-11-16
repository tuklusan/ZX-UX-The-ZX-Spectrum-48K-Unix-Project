#!/usr/bin/env python3
# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
# HiSoft BASIC, translated for ZX-UX. The old traps still bite.
"""rbc experimental Python BASIC -> ZX-UX SSX1 compiler.

The BASIC front end is Melissa O'Neill's MIT-licensed pyhsb (HiSoft BASIC
v1.1 compatible), loaded as Python modules. The output stage is ZX-UX-specific:
three-base address analysis, a relocatable SSX1 image, an 8x8 VGA font, and a
process start/exit shim. This file does not embed original HiSoft compiler code.

An isolated experiment. A successful compile does NOT establish that Spectrum
ROM routines and RAM system variables are safe under ZX-UX. Test each binary.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import struct
import sys
import tempfile
from dataclasses import dataclass
from basic_listing import encode_strict_listing
from rom_syntax import validate_rom_lines
from spectrum_fonts import detect_font_bank
from tape_policy import find_tape_operations, allow_deferred_tape_traps
from native_tape_trap import install as install_native_tape_trap
from external_io_policy import reject_external_commands
from native_pause_rt import install as install_native_pause
from spectrum_runtime import install as install_spectrum_runtime
from native_run_rt import install as install_native_run
from native_keyread_rt import install as install_native_keyread
from native_sysvars_rt import install as install_native_sysvars
from native_sysvar_policy import allow_private_sysvars
from udg_bounds import allow_bounded_udg_loops
from udg_nested import allow_nested_glyph_writes
from udg_chr_bounds import allow_bounded_chr_glyphs
from rom_keyread import allow_key_state_read
from rom_keyboard_control import allow_rom_keyboard_controls
from spectrum_port254 import install as install_port254, allow_port254
from rom_scroll import allow_rom_screen_scroll
from safe_usr_rt import install as install_safe_usr
from safety_usr import enforce_numeric_usr, allow_typed_usr_findings
from poke_policy import apply_poke_policy
from poke_proof import prove_pokes
from restore_data import resolve_restores
from size_opt import prove_literal_string_bounds
from constant_dims import specialize_literal_dims
from constant_data import adapt_literal_data
from integer_fit import infer_integral_scalars
from native_integer_compiler import with_integral_scalars
from native_redim_compiler import with_literal_redims
from native_multidim_strings import with_multidim_strings
from native_string_redim import with_string_redims
from native_data_expressions import with_literal_data_expressions
from native_dynamic_dim import with_bounded_dynamic_dims
from native_budgeted_dim import with_budgeted_numeric_dims, capacity_for_native_budget
from native_budgeted_string_dim import with_budgeted_string_dims
from native_dynamic_string_dim import with_bounded_string_dims
from native_string_compiler import with_static_strings
from native_long_string_proof import growing_scalar_strings
from native_auto_scroll import with_native_screen_scroll
from whole_program_codegen import install as install_codegen_optimizer
from bss_layout import target_offset
from startup_colors import save_and_set, save_controls, restore, append_slots
from native_error_exit import UDG_BYTES
from diagnostics import format_failure, RbcArgumentParser
from rbc_output import output_path, memory_required, write_mode
from memory_safety import MemoryBlocked, analyze_lines, enforce, summarize
from pathlib import Path

HERE = Path(__file__).resolve().parent
SYS = 0x6003
CHARS = 0x5C36
UDG = 0x5C7B    # Sinclair BASIC user-defined graphics base (21*8 bytes)
HEADER_BYTES = 20


def _sdk_modules(sdk: Path):
    """Load frozen ZX-UX packer, not a replacement executable format."""
    sys.path.insert(0, str(sdk))
    import rld  # type: ignore
    import rtap  # type: ignore
    return rld, rtap


def _hisoft_modules(frontend: Path):
    if not (frontend / 'pyhsb.py').is_file() or not (frontend / 'compiler.py').is_file():
        raise ValueError('pyhsb source checkout required via --frontend; '
                         'see https://github.com/imneme/pyhsb')
    sys.path.insert(0, str(frontend))
    import compiler  # type: ignore
    import hbcimage  # type: ignore
    import source  # type: ignore
    return compiler, hbcimage, source


def _tap_from_tzx(p: Path) -> bytes:
    """Convert standard-speed Sinclair TZX data blocks to TAP for pyhsb.

    Unsupported TZX block kinds are rejected, never skipped by guesswork.
    Exact data blocks are preserved, headers and data remain in sequence.
    """
    b = p.read_bytes()
    if not b.startswith(b'ZXTape!\x1a') or len(b) < 10:
        raise ValueError(f'{p}: not TZX')
    out = bytearray()
    i = 10
    while i < len(b):
        k = b[i]; i += 1
        if k == 0x10:
            if i+4 > len(b): raise ValueError('truncated TZX standard header')
            pause, size = struct.unpack_from('<HH', b, i); i += 4
            if i+size > len(b): raise ValueError('truncated TZX standard data')
            block = b[i:i+size]; i += size
            if len(block) < 2 or _xor(block):
                raise ValueError('bad Sinclair tape checksum')
            out.extend(struct.pack('<H', size)); out.extend(block)
        elif k == 0x30:
            if i >= len(b):raise ValueError('truncated TZX text')
            n = b[i]; i += 1+n
            if i > len(b):raise ValueError('truncated TZX text')
        elif k == 0x32:
            if i+2 > len(b): raise ValueError('truncated TZX archive information')
            n = struct.unpack_from('<H',b,i)[0];i+=2+n
            if i>len(b): raise ValueError('truncated TZX archive information')
        else:
            raise ValueError(f'unhandled TZX block {k:#04x} at {i-1}: use a TAP copy')
    return bytes(out)


def _xor(a):
    v=0
    for x in a:v^=x
    return v


@dataclass
class HiSoftBuild:
    code: bytes
    base: int
    entry: int
    bss: int
    label: str = ''


def _source_program(src: Path, source, kw, fp):
    """Read external numbered BAS solely through vendored upstream BAS2TAP."""
    if src.suffix.lower() != '.bas':
        raise ValueError('RBC accepts numbered ASCII .bas only')
    try:
        listing = src.read_text(encoding='ascii')
        program = encode_strict_listing(listing)
    except (UnicodeError, ValueError) as exc:
        raise ValueError(f'{src.name}: {exc}') from exc
    return src.stem[:10], program


def _compile_three(src:Path, frontend:Path, tape:Path, romfile:Path,
                   ramtop:int, directives: list[str], memory_policy:str,
                   optimize_z80:bool=False, budget_capacity:int=0) -> tuple[list[HiSoftBuild], dict]:
    compiler, hbcimage, source = _hisoft_modules(frontend)
    install_native_pause(compiler)
    install_spectrum_runtime(compiler)
    install_native_keyread(compiler)
    install_native_sysvars(compiler)
    install_native_run(compiler)
    install_safe_usr(compiler)
    install_port254(compiler)
    if optimize_z80:
        install_codegen_optimizer(compiler)
    install_native_tape_trap(compiler)
    rom = romfile.read_bytes()
    if len(rom) != 16384:raise ValueError('48K ROM must be 16384 bytes')
    with tempfile.TemporaryDirectory(prefix='rbc-tap-') as tmp:
        if tape.suffix.lower() == '.tzx':
            temp = Path(tmp)/'hisoft.tap';temp.write_bytes(_tap_from_tzx(tape))
            tape = temp
        img = hbcimage.Image.from_tape(tape)
        if not getattr(img,'v11', False):
            raise ValueError('rbc requires HiSoft BASIC v1.1, 48K tape (Side A)')
        kw = source.Keywords(rom)
        initial = compiler.Compiler(img,rom,ramtop=ramtop)
        name, program = _source_program(src,source,kw,initial.fp)
        validate_rom_lines(program, rom)
        find_tape_operations(source.tap.split_lines(program), kw.TOKEN)
        reject_external_commands(source.tap.split_lines(program), kw.TOKEN)
        size_directives, size_proofs = ([], [])
        if not directives and not source.open_lines(program):
            size_directives, size_proofs = prove_literal_string_bounds(
                program, kw, source.tap.split_lines)
        size_proofs.extend(growing_scalar_strings(program, kw, source.tap.split_lines))
        chosen_directives = directives + size_directives
        program, constant_dim_proofs = specialize_literal_dims(
            program, kw, initial.fp, source, source.tap)
        program, constant_data_proofs = adapt_literal_data(
            program, kw, initial.fp, source, source.tap)
        if not source.open_lines(program):
            try:
                program = source.add_directives(program, chosen_directives, True, [], kw, initial.fp)
            except source.SourceError as exc:
                if directives or 'no free line numbers' not in str(exc):
                    raise
                program = source.add_directives(program, [], False,
                                                ['0 REM : OPEN #'], kw, initial.fp)
        else:
            program = source.add_directives(program, directives, False, [], kw, initial.fp)
        program = source.tokenize_directives(program,kw)
        program, restore_remaps = resolve_restores(program, kw, initial.fp)
        import tap as spectrum_tap
        font_alias, font_requested = detect_font_bank(spectrum_tap.split_lines(program), kw.TOKEN)
        checks = analyze_lines(spectrum_tap.split_lines(program), kw.TOKEN)
        allow_deferred_tape_traps(spectrum_tap.split_lines(program), kw.TOKEN, checks)
        allow_bounded_udg_loops(spectrum_tap.split_lines(program), kw.TOKEN, checks)
        allow_nested_glyph_writes(spectrum_tap.split_lines(program), kw.TOKEN, checks)
        allow_bounded_chr_glyphs(spectrum_tap.split_lines(program), kw.TOKEN, checks)
        allow_key_state_read(checks)
        allow_rom_keyboard_controls(checks)
        allow_port254(checks)
        repeat_controls = any(
            item.operation == 'POKE' and
            item.classification == 'rom_keyboard_control' and
            re.match(r'\s*2356[12]\s*,', item.expression)
            for item in checks)
        allow_rom_screen_scroll(checks)
        allow_private_sysvars(checks)
        poke_proofs = prove_pokes(spectrum_tap.split_lines(program), kw.TOKEN, checks)
        apply_poke_policy(checks, poke_proofs, font_alias)
        allow_typed_usr_findings(spectrum_tap.split_lines(program), checks, kw.TOKEN)
        enforce_numeric_usr(spectrum_tap.split_lines(program), checks, poke_proofs, kw.TOKEN)
        memory_report = summarize(checks)
        enforce(checks, memory_policy)
        int_directives, integer_proofs = infer_integral_scalars(
            program, kw, source.tap.split_lines, poke_proofs=poke_proofs)
        base_class = with_static_strings(compiler.Compiler, size_proofs, compiler.letter)
        build_class = with_integral_scalars(base_class,
            [p["variable"] for p in integer_proofs], compiler.INTEG)
        build_class = with_literal_redims(build_class,
            real_type=compiler.REAL, runtime_memfill=compiler.RT.MEM_FILL)
        build_class = with_multidim_strings(build_class,
            string_type=compiler.STRING, multiply_rt=compiler.RT.INT_MUL,
            element_rt=compiler.RT.STR_ARR_ELEM)
        build_class = with_string_redims(build_class,
            string_type=compiler.STRING, memory_fill=compiler.RT.MEM_FILL,
            element_rt=compiler.RT.STR_ARR_ELEM)
        build_class = with_literal_data_expressions(build_class)
        build_class = with_bounded_dynamic_dims(build_class,
            real_type=compiler.REAL, memfill_rt=compiler.RT.MEM_FILL)
        if budget_capacity:
            build_class = with_budgeted_numeric_dims(build_class,
                capacity=budget_capacity, real_type=compiler.REAL,
                memfill_rt=compiler.RT.MEM_FILL)
        build_class = with_bounded_string_dims(build_class,
            string_type=compiler.STRING, memfill_rt=compiler.RT.MEM_FILL)
        if budget_capacity:
            build_class = with_budgeted_string_dims(build_class,
                capacity=budget_capacity)
        build_class = with_native_screen_scroll(build_class)
        # Only a checked, bounded UDG loop may bypass general-purpose POKE.
        udg_pokes = [f for f in checks if f.operation == 'POKE']
        line_counts = {f.line: sum(x.line == f.line for x in udg_pokes)
                       for f in udg_pokes}
        build_class._zxux_proven_udg_loop_pokes = frozenset(
            (f.line, m[1].lower()) for f in udg_pokes
            if f.classification == 'bounded_process_udg_write'
            and line_counts[f.line] == 1
            if (m := re.match(r'^\s*([a-z])\s*,', f.expression, re.I)) is not None)
        build_class._zxux_proven_sysvar_pokes = {
            proof['line']: target['offset']
            for proof in poke_proofs
            if line_counts[proof['line']] == 1
            if len(proof['addresses']) == 1
            for target in proof['addresses']
            if target['space'] == 'absolute'
            and target['offset'] in (23658, 23692)
        }
        upeep_reports=[]
        builds=[]
        for n,top in enumerate((ramtop,ramtop-389,ramtop-617)):
            if top < 32768:raise ValueError('too little compilation space')
            c=build_class(img,rom,ramtop=top)
            res=c.compile_whole(program)
            if not res.ok:
                raise ValueError(f'{src.name}: HiSoft v1.1 compile failed: {res.error}'
                                 f' line {res.error_line}: {res.detail}')
            entry=res.entries[0][1] if res.entries else res.code_base
            builds.append(HiSoftBuild(bytes(res.code),res.load,entry,res.var_bytes,f'ramtop {top}'))
            upeep_reports.append(getattr(c,'_zxux_upeep_stats',{}))
            budgeted_units = sum(5 if c.arrays[k]['type'] == compiler.REAL else 2
                                 for k in getattr(c,'_zxux_budgeted_dims',()))
            budgeted_units += len(getattr(c,'_zxux_budgeted_string_dims',()))
        return builds, {'program':name,'source_bytes':len(program),
                        'compiler':'pyhsb HiSoft v1.1, 48K','frontend':str(frontend),
                        'tape':tape.name if tape.suffix.lower()=='.tap' else str(tape),
                        'memory_policy':memory_policy, 'memory_check':memory_report, 'poke_address_proofs':poke_proofs, 'repeat_controls': repeat_controls, 'private_font_alias':font_alias, 'private_font_requested':font_requested, 'optimized_strings':size_proofs, 'restore_remaps':restore_remaps, 'constant_dimensions':constant_dim_proofs, 'constant_data':constant_data_proofs, 'integer_scalars':integer_proofs, 'budgeted_numeric_units':budgeted_units if budget_capacity else 0, 'rom_runtime_uses':tuple(n for n in (compiler.RT.STR_ASSIGN, compiler.RT.STR_VAR_STACK, compiler.RT.STR_VAR_GET, compiler.RT.STR_ARR_ELEM, compiler.RT.STR_DESC_AT, compiler.RT.STR_CHAR, compiler.RT.STR_SLICE, compiler.RT.STR_SLICE_FROM, compiler.RT.STR_SLICE_TO, compiler.RT.STR_SLICE_CORE, compiler.RT.READ_STR, compiler.RT.INPUT_STR, compiler.RT.VAL_STR, compiler.RT.STR_AND_INT, compiler.RT.STR_AND_REAL) if c.m.used(n)), 'upeepz80_codegen':upeep_reports[0] if optimize_z80 else None}


def _reloc_sites(builds: list[HiSoftBuild]) -> list[int]:
    """Find 16-bit absolute references through controlled compile-time shifts.

    Each changed word must be a pointer into the generated image or BSS and
    track both shifts exactly. This does not independently prove safe ROM use.
    """
    if len(builds) < 2:raise ValueError('need at least two compiler passes')
    first=builds[0];length=len(first.code)
    for other in builds[1:]:
        if len(other.code)!=length or first.bss!=other.bss:
            raise ValueError('compiles differ in code/BSS size; relocation unresolved')
        if (other.entry-other.base) != (first.entry-first.base):
            raise ValueError('entry offset changed between compiles')
    changes={i for i in range(length) if any(b.code[i]!=first.code[i] for b in builds[1:])}
    sites=[]
    covered=set()
    for i in range(length-1):
        if i in covered or i+1 in covered:continue
        if i not in changes and i+1 not in changes:continue
        v=int.from_bytes(first.code[i:i+2],'little')
        if not first.base <= v <= first.base+length+first.bss:continue
        if all(int.from_bytes(b.code[i:i+2],'little') == (v+b.base-first.base)&0xFFFF for b in builds[1:]):
            sites.append(i); covered.update((i,i+1))
    unknown=changes-covered
    if unknown:
        raise ValueError(f'changes not explained by relocations: {len(unknown)} byte(s), '
                         f'first offsets {sorted(unknown)[:12]}; refusing output')
    return sites


class Emitter:
    def __init__(self):
        self.code=bytearray()
        self.fixups=[]
    def emit(self,*values):self.code.extend(values)
    def word(self,v):self.code.extend(struct.pack('<H',v&0xFFFF))
    def relative(self,v):self.fixups.append(len(self.code));self.word(v)
    def ldhl(self,v,rel=False):self.emit(0x21);(self.relative if rel else self.word)(v)
    def ldhl_ind(self,v,rel=False):self.emit(0x2A);(self.relative if rel else self.word)(v)
    def sthl(self,v,rel=False):self.emit(0x22);(self.relative if rel else self.word)(v)
    def call(self,v,rel=False):self.emit(0xCD);(self.relative if rel else self.word)(v)
    def lda(self,v):self.emit(0x3E,v)
    def fix(self,site,v):self.code[site:site+2]=struct.pack('<H',v&0xFFFF)


def build_ssx(builds: list[HiSoftBuild], font:bytes, rld,
              stack:int=384, use_rom_font=False) -> tuple[bytes,dict]:
    if len(font)!=768:raise ValueError('font32 must contain 768 bytes (ASCII 32..127)')
    p=builds[0];sites=_reloc_sites(builds)
    if p.entry < p.base or p.entry >= p.base+len(p.code):
        raise ValueError('entry point not within program image')
    saved_stack=p.base+len(p.code)+p.bss-2
    has_restart_slot=p.bss>=2 and any(
        site>=2 and p.code[site-2:site]==bytes((0xed,0x7b)) and
        int.from_bytes(p.code[site:site+2],'little')==saved_stack
        for site in sites)
    e=Emitter()
    # The ROM remains mapped under ZX-UX. Claim the display, then set the ROM's CHARS pointer to the
    # embedded 8x8 font for printable chars.
    e.ldhl(1);e.lda(39);e.call(SYS)
    e.ldhl_ind(CHARS)
    store_chars=len(e.code)+1;e.sthl(0,rel=True)
    e.ldhl_ind(UDG)
    store_udg=len(e.code)+1;e.sthl(0,rel=True)
    fontptr=len(e.code)+1;e.ldhl(0,rel=True)
    e.sthl(CHARS)
    udgptr=len(e.code)+1;e.ldhl(0,rel=True)
    e.sthl(UDG)
    color_records = save_and_set(e)
    control_records = save_controls(e)
    call=len(e.code)+1;e.call(0,rel=True)
    e.emit(0x11,0,0)  # Normal completion, status zero in DE
    common_exit=len(e.code)
    e.emit(0xd5)  # Preserve status across cleanup and screen release
    restore_udg=len(e.code)+1;e.ldhl_ind(0,rel=True)
    e.sthl(UDG)
    restore_chars=len(e.code)+1;e.ldhl_ind(0,rel=True)
    e.sthl(CHARS)
    restore(e, color_records)
    restore(e, control_records)
    e.ldhl(0);e.lda(39);e.call(SYS)
    e.emit(0xe1)  # Recover native exit status
    e.lda(1);e.call(SYS)
    e.emit(0x76)
    shim=None
    if has_restart_slot:
        shim=len(e.code)
        e.emit(0xed,0x73)
        shim_sp=len(e.code);e.relative(0)
        e.emit(0xc3)
        shim_jump=len(e.code);e.relative(0)
    entry_image=len(e.code)
    e.code.extend(p.code)
    saved_chars=len(e.code);e.word(0)
    saved_udg=len(e.code);e.word(0)
    append_slots(e, color_records)
    append_slots(e, control_records)
    font_start=len(e.code)
    if not use_rom_font:
        e.code.extend(bytes(256))
        e.code.extend(font)
    udg_start=len(e.code);e.code.extend(bytes(UDG_BYTES))
    error_pointer=len(e.code);e.relative(common_exit)
    for offset,value in ((store_chars,saved_chars),(store_udg,saved_udg),
                         (fontptr,0x3C00 if use_rom_font else font_start),(udgptr,udg_start),
                         (call,shim if has_restart_slot else entry_image+p.entry-p.base),
                         (restore_udg,saved_udg),(restore_chars,saved_chars)):
        e.fix(offset,value)
    for site in sites:
        orig=int.from_bytes(p.code[site:site+2],'little')
        target=target_offset(orig,p.base,len(p.code),entry_image,len(e.code),p.bss)
        e.fix(entry_image+site,target)
        e.fixups.append(entry_image+site)
    if has_restart_slot:
        e.fix(shim_sp,len(e.code)+p.bss-2)
        e.fix(shim_jump,entry_image+p.entry-p.base)
    if use_rom_font:
        e.fixups.remove(fontptr)
    reloc=sorted(e.fixups)
    if len(set(reloc))!=len(reloc) or any(x+2>len(e.code) for x in reloc):
        raise ValueError('overlapping or invalid relocations')
    if len(e.code)+p.bss+stack>65535:
        raise ValueError('image, variables and stack cannot fit in 48K address space')
    rs=rld.reloc_stream(reloc)
    hdr=b'SSX1'+struct.pack('<BBHHHHHH',0,HEADER_BYTES,len(e.code),p.bss,stack,0,0,len(reloc))
    ssx=hdr+struct.pack('<H',rld.fletcher16(hdr+e.code+rs))+e.code+rs
    check=rld.parse_ssx(ssx)
    if check['relocs']!=reloc or check['image']!=bytes(e.code):
        raise ValueError('SSX1 round-trip validation failed')
    return ssx, {'machine_code':len(p.code),'image':len(e.code),'bss':p.bss,
                 'entry_offset':entry_image+p.entry-p.base,'relocations':len(reloc),
                 'font_bytes':0 if use_rom_font else len(font)+256,'udg_bytes':21*8,
                 'font_source':'spectrum_rom' if use_rom_font else 'process_image',
                 'rom_and_system_variable_compatibility':'unverified',
                 'visual_and_gameplay_compatibility':'unverified'}


def main(argv=None):
    ap=RbcArgumentParser(description=__doc__)
    ap.add_argument('source',type=Path,help='original .bas or .tap; untouched')
    ap.add_argument('-o','--output',type=Path,help='output path (default: next to BASIC input)')
    ap.add_argument('-S',action='store_true',dest='assembly_only',help='emit Z80 assembly')
    ap.add_argument('-c',action='store_true',dest='object_only',help='emit SSO1 object')
    ap.add_argument('--upeepz80',action='store_true',
                    help='optimize symbolic Z80 fragments before assembler encoding')
    ap.add_argument('--fit',action='store_true',default=True,dest='fit',
                    help='use 48K ROM glyphs to save native image memory (default)')
    ap.add_argument('--no-fit',action='store_false',dest='fit',
                    help='retain the embedded character font')
    ap.add_argument('--max',type=lambda n:int(n,0),default=14000,
                    help='maximum image, data and stack bytes (0 disables)')
    ap.add_argument('--native',action='store_true',help='force the existing native backend')
    ap.add_argument('--bytecode',action='store_true',
                    help='unsupported: no BASIC bytecode backend exists')
    ap.add_argument('--heap',type=lambda n:int(n,0),default=None)
    ap.add_argument('--udgs',type=lambda n:int(n,0),default=None)
    ap.add_argument('--frontend',type=Path,default=Path(os.getenv('PYHSB_PATH','pyhsb')))
    ap.add_argument('--sdk',type=Path,default=HERE.parent.parent/'work'/'dist_sdk')
    ap.add_argument('--tape',type=Path,default=HERE.parent.parent/'..'/'Hisoft BASIC Compiler v1.1 - Side A.tzx')
    ap.add_argument('--rom',type=Path,default=HERE.parent.parent/'inputs'/'48.rom')
    ap.add_argument('--font32',type=Path,default=HERE/'font32.bin')
    ap.add_argument('--ramtop',type=int,default=65367)
    ap.add_argument('--stack',type=int,default=384)
    ap.add_argument('--directive',action='append',default=[],help='HiSoft compiler directive')
    ap.add_argument('--memory-policy',choices=('strict','review'),default='strict',
                    help='strict refuses unsafe memory operations; review compiles for isolated tests')
    ap.add_argument('--tzx',type=Path)
    ap.add_argument('--report',type=Path)
    # Replay existing genuine HiSoft compilations without re-interpreting .bas. This is a regression
    # mode, never a substitute for pyhsb-source mode.
    ap.add_argument('--pair-second',type=Path,help='second HiSoft code binary')
    ap.add_argument('--pair-third',type=Path,help='third HiSoft code binary')
    ap.add_argument('--base',type=int,help='first build load address (pair regression mode)')
    ap.add_argument('--second-base',type=int)
    ap.add_argument('--third-base',type=int)
    ap.add_argument('--var-bytes',type=int)
    ap.add_argument('--entry',type=int,help='absolute HiSoft entry (pair regression mode)')
    args=ap.parse_args(argv)
    if args.assembly_only and args.object_only:
        ap.error('conflicting output modes')
    if args.tzx and (args.assembly_only or args.object_only):
        ap.error('cassette output requires linked SSX')
    if args.bytecode:
        ap.error('--bytecode is unavailable for native RBC')
    if args.heap is not None:
        ap.error('--heap is not adjustable in RBC')
    if args.udgs is not None and args.udgs != 21:
        ap.error('--udgs must be 21 for Sinclair BASIC')
    if args.max < 0 or args.stack < 1:
        ap.error('--max must be nonnegative and --stack positive')
    mode = 'assembly' if args.assembly_only else 'object' if args.object_only else 'link'
    args.output = output_path(args.source, args.output, mode)
    if args.source.is_file() and args.output.exists() and args.source.samefile(args.output):
        ap.error('output would overwrite the BASIC input')
    try:
        rld,rtap=_sdk_modules(args.sdk)
        font=args.font32.read_bytes()
        if args.pair_second:
            if None in (args.base,args.second_base,args.var_bytes):
                raise ValueError('pair mode needs --base, --second-base and --var-bytes')
            entry=args.entry if args.entry is not None else args.base
            builds=[HiSoftBuild(args.source.read_bytes(),args.base,entry,args.var_bytes,'first'),
                    HiSoftBuild(args.pair_second.read_bytes(),args.second_base,
                                entry+args.second_base-args.base,args.var_bytes,'second')]
            if args.pair_third:
                if args.third_base is None:raise ValueError('third build needs --third-base')
                builds.append(HiSoftBuild(args.pair_third.read_bytes(),args.third_base,
                    entry+args.third_base-args.base,args.var_bytes,'third'))
            meta={'source_mode':'replay existing HiSoft binaries'}
        else:
            builds,meta=_compile_three(args.source,args.frontend,args.tape,args.rom,
                                       args.ramtop,args.directive,args.memory_policy,args.upeepz80,1)
            if meta['budgeted_numeric_units']:
                trial, trial_layout = build_ssx(builds,font,rld,args.stack,
                    use_rom_font=args.fit and not meta.get('private_font_requested',False))
                capacity = capacity_for_native_budget(args.max,
                    trial_layout['image'],trial_layout['bss'],args.stack,
                    meta['budgeted_numeric_units'])
                builds,meta=_compile_three(args.source,args.frontend,args.tape,args.rom,
                    args.ramtop,args.directive,args.memory_policy,args.upeepz80,capacity)
                meta['budgeted_numeric_capacity'] = capacity
            meta['source_mode']='pyhsb HiSoft v1.1 (48K) source compile'
        ssx,diagnostics=build_ssx(builds,font,rld,args.stack,
               use_rom_font=False)
        if (args.fit and args.max and
                not meta.get('private_font_requested',False) and
                memory_required(rld.parse_ssx(ssx),len(ssx)) > args.max):
            ssx,diagnostics=build_ssx(builds,font,rld,args.stack,
                use_rom_font=True)
        if args.upeepz80:
            diagnostics['upeepz80'] = meta.get('upeepz80_codegen')
        measured = memory_required(rld.parse_ssx(ssx), len(ssx))
        diagnostics['memory_required'] = measured
        diagnostics['memory_limit'] = args.max
        diagnostics['fit_default'] = args.fit
        if mode == 'link' and args.max and measured > args.max:
            if args.report:
                args.report.parent.mkdir(parents=True,exist_ok=True)
                args.report.write_text(json.dumps({'compile':'too_large',
                    'cause_category':'native-memory-limit',
                    'memory_required':measured,'memory_limit':args.max,
                    'source':str(args.source),'image':diagnostics['image'],
                    'bss':diagnostics['bss'],'stack':args.stack},indent=2)+'\n')
            raise ValueError('%s needs %d bytes of native memory (limit %d)'
                             % (args.source,measured,args.max))
        args.output.parent.mkdir(parents=True,exist_ok=True)
        if mode == 'object':
            import ras
            write_mode(args.output,ssx,mode,rld,ras)
        else:
            write_mode(args.output,ssx,mode,rld)
        if args.tzx:
            hdr,block=rtap.records(ssx,args.output.stem[:10])
            title=b'ZX-UX RBC experimental'
            tzx_head=b'ZXTape!\x1a\x01\x14'+bytes((0x30,len(title)))+title
            rtap.write(str(args.tzx),tzx_head,[(1000,hdr),(2000,block)])
        meta.update(diagnostics)
        if args.report:
            args.report.parent.mkdir(parents=True,exist_ok=True)
            args.report.write_text(json.dumps(meta,indent=2)+'\n')
        print(f'{args.source.name}: {len(builds[0].code)} bytes of HiSoft code -> '
              f'{len(ssx)} byte {mode} ({diagnostics["relocations"]} relocations) '
              f'at {args.output}')
        return 0
    except MemoryBlocked as exc:
        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(json.dumps({'compile':'blocked',
                        'memory_policy':args.memory_policy,
                        'memory_check':summarize(exc.findings)},indent=2)+'\n')
        print(format_failure(exc,args.source),file=sys.stderr)
        return 1
    except Exception as exc:
        print(format_failure(exc,args.source),file=sys.stderr)
        return 1


if __name__=='__main__':raise SystemExit(main())
