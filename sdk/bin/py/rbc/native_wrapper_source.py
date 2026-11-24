# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""Assemble the ZX-UX process wrapper around independently witnessed HiSoft Z80.

This consumes a *pre-link* source program, not an SSX, object disassembly,
patched image, or address dump. All executable wrapper bytes are Z80 mnemonics;
only verified source-owned data, the font, and private storage use db/dw/ds.
No optimizer or post-link image fixup is involved.
"""
from __future__ import annotations

import re

import ras
import rld

from native_error_exit import UDG_BYTES

ROM_COLORS = ((0x5C8D, 0x38), (0x5C8E, 0),
              (0x5C8F, 0x38), (0x5C90, 0))
ROM_CONTROLS = (0x5C6A, 0x5C39)
ROM_REPEAT_CONTROLS = (0x5C09, 0x5C0A)
PREFIX = 'rbc_wrapper_'


class NativeWrapperError(ValueError):
    """Fail closed when the source layout or assembler result cannot be proven."""


def _signed_print_at(source: str) -> tuple[str, int]:
    """Correct signed coordinates in the original PRINT AT entry, in place.

    HiSoft writes the low bytes of DE (row) and HL (column). The original
    Spectrum ROM takes the magnitude of negative values before testing the
    screen bounds. Keep the original routine and all calls unchanged.
    """
    lines = source.splitlines(keepends=True)
    matched = []
    for i in range(len(lines) - 14):
        match = re.fullmatch(r'source_([0-9a-f]{4}):\n', lines[i])
        if match is None:
            continue
        offset = int(match[1], 16)
        expected = [
            f'original_rt_{offset:04x}:\n', '    ld a, 0x16\n',
            f'original_rt_{offset+2:04x}:\n', '    rst 0x10\n',
            f'original_rt_{offset+3:04x}:\n', '    ld a, e\n',
            f'original_rt_{offset+4:04x}:\n', '    rst 0x10\n',
            f'original_rt_{offset+5:04x}:\n', '    ld a, l\n',
            f'original_rt_{offset+6:04x}:\n', '    rst 0x10\n',
            f'original_rt_{offset+7:04x}:\n', '    ret\n',
        ]
        if lines[i+1:i+15] == expected:
            matched.append(i)
        elif lines[i+1:i+3] == expected[:2]:
            raise NativeWrapperError('unverified native PRINT AT instruction layout')
    if len(matched) > 1:
        raise NativeWrapperError('PRINT AT has multiple unverified runtime entries')
    if not matched:
        return source, 0
    for label in ('rbc_wrapper_at_row_abs:', 'rbc_wrapper_at_row_ready:',
                  'rbc_wrapper_at_col_abs:', 'rbc_wrapper_at_col_ready:'):
        if label in source:
            raise NativeWrapperError('duplicate native PRINT AT label')
    # Signed 16-bit negative -> unsigned magnitude. Any magnitude >255 becomes 255 so the ROM still
    # rejects invalid dynamic positions.
    preamble = """    bit 7,d
    jr z,rbc_wrapper_at_row_abs
    xor a
    sub e
    ld e,a
    ld a,0
    sbc a,d
    ld d,a
rbc_wrapper_at_row_abs:
    ld a,d
    or a
    jr z,rbc_wrapper_at_row_ready
    ld e,255
rbc_wrapper_at_row_ready:
    bit 7,h
    jr z,rbc_wrapper_at_col_abs
    xor a
    sub l
    ld l,a
    ld a,0
    sbc a,h
    ld h,a
rbc_wrapper_at_col_abs:
    ld a,h
    or a
    jr z,rbc_wrapper_at_col_ready
    ld l,255
rbc_wrapper_at_col_ready:
"""
    lines.insert(matched[0] + 1, preamble)
    return ''.join(lines), 1


def wrapper_source(original_source: str, font: bytes, *,
                   use_rom_font: bool = False, restart_slot: bool = False,
                   rom_work_bytes: int = 0, signed_print_at: bool = False,
                   repeat_controls: bool = False) -> str:
    """Return typed native text/data/BSS for the entire wrapped program.

    `original_source` must be a complete, independently three-base-verified
    HiSoft pre-link source produced by gate8_whole_native_baseline. Its first
    text label is the original HiSoft `start`, which is renamed here only so
    the SSX wrapper can own the loader's global `start` entry.
    """
    if not isinstance(original_source, str) or not isinstance(font, bytes):
        raise NativeWrapperError('typed source and font bytes required')
    if len(font) != 768:
        raise NativeWrapperError('font32 must contain exactly 768 original bytes')
    if type(use_rom_font) is not bool or type(restart_slot) is not bool:
        raise NativeWrapperError('wrapper flags must be boolean')
    if type(rom_work_bytes) is not int or (rom_work_bytes != 0 and not 512 <= rom_work_bytes <= 2048):
        raise NativeWrapperError('private ROM workspace out of range')
    if type(signed_print_at) is not bool or type(repeat_controls) is not bool:
        raise NativeWrapperError('invalid runtime wrapper option')
    controls = ROM_CONTROLS + (ROM_REPEAT_CONTROLS if repeat_controls else ())
    lines = original_source.splitlines()
    if (len(lines) < 5 or lines[:3] !=
            ['    section text', '    global start', 'start:'] or
            lines.count('    section data') not in (0, 1) or
            lines.count('    section bss') != 1 or
            any(PREFIX in line for line in lines) or
            (lines.count('    section data') == 1 and
             lines.index('    section data') >= lines.index('    section bss'))):
        raise NativeWrapperError('unsupported original pre-link source layout')
    if not original_source.isascii():
        raise NativeWrapperError('non-ASCII native source')
    body = re.sub(r'(?<![A-Za-z0-9_])start(?![A-Za-z0-9_])',
                  PREFIX + 'hisoft_entry', original_source)
    if signed_print_at:
        body, _ = _signed_print_at(body)
    text_and_data, bss = body.split('    section bss\n', 1)
    # HiSoft programs with no emitted DATA section have a text->BSS source. The
    # wrapper still needs an explicit, distinct data section for its restored process
    # state. Never move original source bytes.
    if '    section data\n' not in text_and_data:
        text_and_data += '    section data\n'
    # Ordinary emitted source (rather than fixed byte sequences) owns all wrapper
    # instructions and the loader entry point.
    pro = ['    section text', '    global start', 'start:',
           '    ld hl,1', '    ld a,39', '    call $6003']
    if rom_work_bytes:
        # ZX-UX has global ROM WORKSP/STKBOT/STKEND/ERR_SP, not saved per-process
        # state. Fail closed if another process owns the screen; its executable may
        # be using those system variables concurrently. E is the previous
        # screen-owner bitmask returned by syscall 39.
        pro.extend(('    ld a,e', '    or a', f'    jr z,{PREFIX}screen_exclusive',
                    '    ld hl,0', '    ld a,39', '    call $6003',
                    '    ld hl,21', '    ld a,1', '    call $6003', '    halt',
                    f'{PREFIX}screen_exclusive:'))
    pro.extend(('    ld hl,($5c36)', f'    ld ({PREFIX}saved_chars),hl',
           '    ld hl,($5c7b)', f'    ld ({PREFIX}saved_udg),hl',
           '    ld hl,$3c00' if use_rom_font else f'    ld hl,{PREFIX}font',
           '    ld ($5c36),hl', f'    ld hl,{PREFIX}udg',
           '    ld ($5c7b),hl'))
    if rom_work_bytes:
        pro.extend((f'    ld ({PREFIX}saved_stack),sp',
                    '    ld hl,($5c3d)',
                    f'    ld ({PREFIX}saved_err_sp),hl',
                    f'    ld hl,{PREFIX}rom_error_sp',
                    '    ld ($5c3d),hl'))
        for ptr in (0x5c61,0x5c63,0x5c65):
            pro.extend((f'    ld hl,(${ptr:04x})',
                        f'    ld ({PREFIX}saved_work_{ptr:04x}),hl',
                        f'    ld hl,{PREFIX}rom_work', f'    ld (${ptr:04x}),hl'))
    for i, (address, value) in enumerate(ROM_COLORS):
        pro.extend((f'    ld a,(${address:04x})',
                    f'    ld ({PREFIX}color_{i}),a',
                    f'    ld a,{value}', f'    ld (${address:04x}),a'))
    for i, address in enumerate(controls):
        pro.extend((f'    ld a,(${address:04x})',
                    f'    ld ({PREFIX}control_{i}),a'))
    pro.extend((f'    call {PREFIX}restart' if restart_slot else
                f'    call {PREFIX}hisoft_entry',
                '    ld de,0', f'{PREFIX}exit:', '    push de',
                f'    ld hl,({PREFIX}saved_udg)', '    ld ($5c7b),hl',
                f'    ld hl,({PREFIX}saved_chars)', '    ld ($5c36),hl'))
    if rom_work_bytes:
        pro.extend((f'    ld hl,({PREFIX}saved_err_sp)',
                    '    ld ($5c3d),hl'))
        for ptr in (0x5c61,0x5c63,0x5c65):
            pro.extend((f'    ld hl,({PREFIX}saved_work_{ptr:04x})',
                        f'    ld (${ptr:04x}),hl'))
    for i, (address, _) in enumerate(ROM_COLORS):
        pro.extend((f'    ld a,({PREFIX}color_{i})',
                    f'    ld (${address:04x}),a'))
    for i, address in enumerate(controls):
        pro.extend((f'    ld a,({PREFIX}control_{i})',
                    f'    ld (${address:04x}),a'))
    pro.extend(('    ld hl,0', '    ld a,39', '    call $6003'))
    if rom_work_bytes:
        pro.extend((f'    ld hl,({PREFIX}saved_err_sp)', '    ld ($5c3d),hl'))
    pro.extend(('    pop hl', '    ld a,1', '    call $6003', '    halt'))
    if rom_work_bytes:
        pro.extend((f'{PREFIX}rom_error:',
                    f'    ld sp,({PREFIX}saved_stack)',
                    '    ld a,($5c3a)',
                    '    inc a',
                    '    ld e,a',
                    '    ld d,0',
                    f'    jp {PREFIX}exit'))
    if restart_slot:
        pro.extend((f'{PREFIX}restart:',
                    f'    ld ({PREFIX}bss_end-2),sp',
                    f'    jp {PREFIX}hisoft_entry'))
    data = [f'{PREFIX}saved_chars:', '    dw 0',
            f'{PREFIX}saved_udg:', '    dw 0']
    if rom_work_bytes:
        data.extend((f'{PREFIX}saved_stack:', '    dw 0',
                     f'{PREFIX}saved_err_sp:', '    dw 0',
                     f'{PREFIX}rom_error_guard:', '    ds 128',
                     f'{PREFIX}rom_error_sp:', f'    dw {PREFIX}rom_error'))
        for ptr in (0x5c61,0x5c63,0x5c65):
            data.extend((f'{PREFIX}saved_work_{ptr:04x}:','    dw 0'))
    for i in range(len(ROM_COLORS)):
        data.extend((f'{PREFIX}color_{i}:', '    db 0'))
    for i in range(len(controls)):
        data.extend((f'{PREFIX}control_{i}:', '    db 0'))
    if not use_rom_font:
        data.extend((f'{PREFIX}font:', '    ds 256'))
        for i in range(0, len(font), 32):
            data.append('    db ' + ','.join(map(str, font[i:i + 32])))
    data.extend((f'{PREFIX}udg:', f'    ds {UDG_BYTES}',
                 f'{PREFIX}error_pointer:', f'    dw {PREFIX}exit'))
    if rom_work_bytes:
        bss += f'{PREFIX}rom_work:\n    ds {rom_work_bytes}\n'
    return ('\n'.join(pro) + '\n' + text_and_data +
            '\n'.join(data) + '\n    section bss\n' + bss +
            f'{PREFIX}bss_end:\n')


def assemble_link(original_source: str, font: bytes, *,
                  use_rom_font: bool = False, restart_slot: bool = False,
                  stack: int = 384, rom_work_bytes: int = 0,
                  signed_print_at: bool = False,
                  repeat_controls: bool = False) -> tuple[str, bytes, bytes]:
    """Emit typed assembly, real ras object, and actual rld-linked SSX."""
    if type(stack) is not int or not 1 <= stack <= 65535:
        raise NativeWrapperError('invalid native stack size')
    source = wrapper_source(original_source, font,
                            use_rom_font=use_rom_font,
                            restart_slot=restart_slot, rom_work_bytes=rom_work_bytes,
                            signed_print_at=signed_print_at,
                            repeat_controls=repeat_controls)
    try:
        obj = ras.assemble_text(source, 'rbc-native-whole.s')
        ssx, *_ = rld.link([rld.Obj(obj, 'rbc-native-whole.sso')], [],
                           entry='start', stack=stack)
        parsed = rld.parse_ssx(ssx)
    except (ras.AsmError, rld.LinkError, IndexError, ValueError) as exc:
        raise NativeWrapperError('native wrapper assemble/link failed: ' + str(exc)) from exc
    if parsed['entry'] != 0 or parsed['stack'] != stack:
        raise NativeWrapperError('native wrapper entry/stack differs from source')
    return source, obj, ssx
