#!/usr/bin/env python3
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Proprietary rights reserved except as expressly licensed herein.
#
# ZX-UX Sinclair ZX Spectrum Unix
# This file is governed by the SANYALnet Labs Non-Commercial License in the
# root LICENSE file. Non-Commercial use is permitted; Commercial Use and use
# for AI/ML model training are prohibited unless separately authorized.
#
# Attribution is required: "Based on original work by Supratim Sanyal of
# SANYALnet Labs." See LICENSE for full terms, warranty disclaimer, termination,
# patent, trademark, and governing-law provisions.

from __future__ import annotations

import json
import re

import phase1
import phase3_open_descriptions
from driver_core import DriverError
from fuse_harness import FAIL_PC, PASS_PC, run_sna


class P1136Error(DriverError):
    pass


def require(ok, message):
    if not ok:
        raise P1136Error(message)


def _db(data: bytes) -> str:
    chunks = [data[i:i+24] for i in range(0, len(data), 24)]
    return "\n    db ".join(
        ",".join("$"+format(b, "02X") for b in chunk) for chunk in chunks
    )


def dispatch(root, action, step, *, sha256_file, run_command, require_project_tool):
    if step != "P11.36":
        raise DriverError(step)

    source_path = root / "v1/src/demos/colors.c"
    mapping_path = root / "v1/tests/compiler/p1136-source-map.json"
    cc_path = root / "v1/src/tools/cc.asm"
    ld_path = root / "tools/ld.asm"
    archive_path = root / "v1/src/libc48/runtime_archive.asm"
    crt0_path = root / "v1/src/libc48/crt0.asm"
    plan_path = root / "docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV08.md"
    arch_path = root / "docs/01-ZX-UX-ARCHITECTURE-REV17.md"

    source = source_path.read_bytes()
    text = source.decode("ascii")
    mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
    cc = cc_path.read_text(encoding="utf-8")
    archive = archive_path.read_text(encoding="utf-8")
    plan = plan_path.read_text(encoding="utf-8")
    arch = arch_path.read_text(encoding="utf-8")

    require("## P11.36 - Graphics/UDG C program" in plan
            and "Screen/UDG result exact." in plan
            and "No direct kernel-memory write." in plan,
            "REV08 P11.36 contract drift")
    require("## 42.2 colors.c" in arch and "## 42.3 lines.c" in arch,
            "REV17 graphics demo acceptance surface drift")
    require(all(fragment in text for fragment in (
        "int main(void)", "ink(2);", "plot(0, 0);", "udg_clear(3);", "return 0;"
    )), "P11.36 canonical source body drift")
    require(not re.search(r"\b(?:0x)?(?:4000|5800|E000)\b|SYSCALL_GATEWAY|\bSYS_|\bROM_", text, re.I),
            "P11.36 C source contains direct kernel/hardware access")
    require("MACRO EMIT_P1136_CC_GRAPHICS_COMPILER" in cc
            and "cc_p1136_compile:" in cc,
            "P11.36 native compiler extension missing")
    require("MACRO EMIT_P1136_GRAPHICS_ARCHIVE" in archive
            and all(name in archive for name in (
                "p1136_ink_obj:", "p1136_plot_obj:", "p1136_udg_clear_obj:"
            )), "P11.36 built-in graphics archive missing")
    require(mapping.get("step") == "P11.36"
            and mapping.get("sdk_commit") == "84d144de2721cda5075c3a6610a422663b5e2f77",
            "P11.36 pinned SDK mapping identity drift")
    mapped = mapping["sources"][0]
    require(mapped["path"] == "v1/src/demos/colors.c"
            and mapped["sdk_reference"]["result"] == "REJECT"
            and mapped["sdk_reference"]["category"] == "declaration-error"
            and mapped["target_native"]["required_result"] == "PASS"
            and mapped["target_native"]["expected_udg_slot"] == 3,
            "P11.36 SDK/reference/native mapping incomplete")

    assembler = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    fixture = build / "p1136-graphics-native.asm"
    fixture.write_text(f'''    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/tools/cc.asm"
    INCLUDE "../../tools/ld.asm"
    INCLUDE "../src/libc48/crt0.asm"
    INCLUDE "../src/libc48/runtime_archive.asm"

    ORG $4000
CC_TYPE_VOID  EQU 0
CC_TYPE_CHAR  EQU 1
CC_TYPE_UCHAR EQU 2
CC_TYPE_SHORT EQU 3
CC_TYPE_USHORT EQU 4
CC_TYPE_INT   EQU 5
CC_TYPE_UINT  EQU 6
CC_TYPE_FLOAT EQU 7
CC_IDENT_MAX  EQU 15
p1136_start:
    EMIT_P11_CC_LEXER
    EMIT_P11_CC_REGCALL
    EMIT_P1128_CC_OBJ1_WRITER
    EMIT_P1136_CC_GRAPHICS_COMPILER
    EMIT_P10_LD_LAYOUT_ROUTINES
    EMIT_P10_LD_RELOCATION_ROUTINES
    EMIT_P10_LD_STACK_OPTION_ROUTINES
    EMIT_P10_LD_HEAP_OPTION_ROUTINES
    EMIT_P10_LD_MEX1_WRITER_ROUTINES
    EMIT_P10_CRT0_OBJ1
    EMIT_P10_RUNTIME_ARCHIVE
    EMIT_P1136_GRAPHICS_ARCHIVE
    EMIT_P1136_GRAPHICS_ARCHIVE_ROUTINES

p1136_source:
    db {_db(source)}
p1136_source_end:
p1136_bad_source:
    db "int main(void)",123,"*(char*)16384=1;return 0;",125
p1136_bad_source_end:

p1136_user_obj: defs 256,$CC
p1136_obj_ptrs:
    dw p10_crt0_obj,p1136_user_obj,p1136_ink_obj,p1136_plot_obj
    dw p1136_udg_clear_obj,p10_runtime_exit_obj
p1136_sizes: defs 24,0
p1136_image: defs 256,0
p1136_mex: defs 320,0
p1136_loaded: EQU $A000
p1136_copy_base_ptr: dw 0
p1136_attr: db 7
p1136_attr_calls: db 0
p1136_plot_calls: db 0
p1136_udg_calls: db 0
p1136_udg_bank: defs 256,$A5

p1136_fail:
    ld a,E_FORMAT
    scf
    ret

p1136_compile:
    ld hl,p1136_source
    ld bc,p1136_source_end-p1136_source
    ld de,p1136_user_obj
    ld ix,256
    call cc_p1136_compile
    ret c
    ld de,147
    or a
    sbc hl,de
    jp nz,p1136_fail
    ld hl,p1136_user_obj
    ld de,p1136_obj_magic
    ld b,4
p1136_magic_loop:
    ld a,(de)
    cp (hl)
    jp nz,p1136_fail
    inc de
    inc hl
    djnz p1136_magic_loop
    xor a
    ret
p1136_obj_magic: db "OBJ1"

p1136_negative:
    ld hl,p1136_bad_source
    ld bc,p1136_bad_source_end-p1136_bad_source
    ld de,p1136_user_obj
    ld ix,256
    call cc_p1136_compile
    jp nc,p1136_fail
    cp E_FORMAT
    jp nz,p1136_fail
    xor a
    ret

p1136_build_sizes:
    ld ix,p1136_obj_ptrs
    ld de,p1136_sizes
    ld b,6
p1136_size_loop:
    ld l,(ix+0)
    ld h,(ix+1)
    push hl
    ld bc,8
    add hl,bc
    ld c,(hl)
    inc hl
    ld b,(hl)
    ld a,c
    ld (de),a
    inc de
    ld a,b
    ld (de),a
    inc de
    pop hl
    ld bc,10
    add hl,bc
    ld c,(hl)
    inc hl
    ld b,(hl)
    ld a,c
    ld (de),a
    inc de
    ld a,b
    ld (de),a
    inc de
    inc ix
    inc ix
    djnz p1136_size_loop
    xor a
    ret

p1136_copy_modules:
    ld ix,p1136_obj_ptrs
    ld hl,ld_p1024_text_bases
    ld (p1136_copy_base_ptr),hl
    ld b,6
p1136_copy_loop:
    push bc
    ld l,(ix+0)
    ld h,(ix+1)
    push hl
    ld de,8
    add hl,de
    ld c,(hl)
    inc hl
    ld b,(hl)
    pop hl
    ld de,24
    add hl,de
    push hl
    ld hl,(p1136_copy_base_ptr)
    ld e,(hl)
    inc hl
    ld d,(hl)
    inc hl
    ld (p1136_copy_base_ptr),hl
    ld hl,p1136_image
    add hl,de
    ex de,hl
    pop hl
    ldir
    inc ix
    inc ix
    pop bc
    djnz p1136_copy_loop
    xor a
    ret

p1136_apply:
    ld (ld_p1026_patch_loc),hl
    ld (ld_p1026_symbol_value),de
    ld hl,0
    ld (ld_p1026_addend),hl
    ld a,1
    ld (ld_p1026_symbol_section),a
    jp ld_p1026_apply

p1136_link:
    call p1136_compile
    ret c
    call p1136_build_sizes
    ret c
    ld hl,p1136_sizes
    ld b,6
    ld de,0
    call ld_p1024_layout
    ret c
    ld hl,(ld_p1024_image_size)
    ld de,256
    or a
    sbc hl,de
    jp nc,p1136_fail

    ld hl,p1136_image
    ld de,p1136_image+1
    ld bc,255
    xor a
    ld (hl),a
    ldir
    call p1136_copy_modules
    ret c

    ld hl,p1136_image
    ld (ld_p1026_image),hl
    ld hl,(ld_p1024_image_size)
    ld (ld_p1026_image_size),hl
    call ld_p1026_reset

    ld hl,1
    ld de,(ld_p1024_text_bases+2)
    call p1136_apply
    ret c
    ld hl,4
    ld de,(ld_p1024_text_bases+10)
    call p1136_apply
    ret c

    ld hl,(ld_p1024_text_bases+2)
    ld bc,4
    add hl,bc
    ld de,(ld_p1024_text_bases+4)
    call p1136_apply
    ret c
    ld hl,(ld_p1024_text_bases+2)
    ld bc,13
    add hl,bc
    ld de,(ld_p1024_text_bases+6)
    call p1136_apply
    ret c
    ld hl,(ld_p1024_text_bases+2)
    ld bc,19
    add hl,bc
    ld de,(ld_p1024_text_bases+8)
    call p1136_apply
    ret c

    call ld_p1026_finalize
    ret c
    ld a,(ld_p1026_rel_count)
    cp 5
    jp nz,p1136_fail

    call ld_p1030_stack_default
    ret c
    ld hl,(ld_p1024_image_size)
    ld de,0
    ld bc,0
    call ld_p1031_place
    ret c

    ld hl,p1136_image
    ld (ld_p1032_image),hl
    ld hl,(ld_p1024_image_size)
    ld (ld_p1032_image_size),hl
    ld hl,(ld_p1031_mex1_bss_size)
    ld (ld_p1032_bss_size),hl
    ld hl,0
    ld (ld_p1032_entry),hl
    ld hl,(ld_p1030_min_fast_stack)
    ld (ld_p1032_stack),hl
    ld hl,ld_p1026_rel_locs
    ld (ld_p1032_relocs),hl
    ld hl,5
    ld (ld_p1032_reloc_count),hl
    ld hl,p1136_mex
    ld (ld_p1032_output),hl
    ld hl,320
    ld (ld_p1032_capacity),hl
    call ld_p1032_write
    ret c
    xor a
    ret

p1136_load_run:
    ld hl,p1136_mex+24
    ld de,p1136_loaded
    ld bc,(ld_p1024_image_size)
    ldir
    ld ix,ld_p1026_rel_locs
    ld b,5
p1136_load_reloc_loop:
    push bc
    ld e,(ix+0)
    ld d,(ix+1)
    ld hl,p1136_loaded
    add hl,de
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld bc,p1136_loaded
    ex de,hl
    add hl,bc
    ex de,hl
    ld (hl),d
    dec hl
    ld (hl),e
    inc ix
    inc ix
    pop bc
    djnz p1136_load_reloc_loop

    xor a
    ld (p1136_attr_calls),a
    ld (p1136_plot_calls),a
    ld (p1136_udg_calls),a
    ld ($4000),a
    ld a,7
    ld ($5800),a
    ld (p1136_attr),a
    ld hl,p1136_udg_bank+24
    ld b,8
    ld a,$A5
p1136_udg_seed:
    ld (hl),a
    inc hl
    djnz p1136_udg_seed

    call p1136_loaded
    ld de,0
    or a
    sbc hl,de
    jp nz,p1136_fail
    ld a,(p1136_attr_calls)
    cp 1
    jp nz,p1136_fail
    ld a,(p1136_plot_calls)
    cp 1
    jp nz,p1136_fail
    ld a,(p1136_udg_calls)
    cp 1
    jp nz,p1136_fail
    ld a,($4000)
    cp $80
    jp nz,p1136_fail
    ld a,($5800)
    cp 2
    jp nz,p1136_fail
    ld hl,p1136_udg_bank+24
    ld b,8
p1136_udg_zero_check:
    ld a,(hl)
    or a
    jp nz,p1136_fail
    inc hl
    djnz p1136_udg_zero_check
    xor a
    ret

p1136_lifecycle:
    call p1136_link
    ret c
    call p1136_load_run
    ret c
    xor a
    ret

p1136_end:
    SAVEBIN "p1136-main.bin",p1136_start,p1136_end-p1136_start

    ORG $E000
p1136_gateway:
    cp SYS_GFX_ATTR
    jr z,p1136_gfx_attr
    cp SYS_GFX_PLOT
    jr z,p1136_gfx_plot
    cp SYS_UDG_CLEAR
    jr z,p1136_udg_clear
    ld a,E_NOTSUP
    scf
    ret
p1136_gfx_attr:
    ld a,h
    or a
    jr nz,p1136_gate_bad
    ld a,l
    cp 2
    jr nz,p1136_gate_bad
    ld (p1136_attr),a
    ld a,(p1136_attr_calls)
    inc a
    ld (p1136_attr_calls),a
    xor a
    ret
p1136_gfx_plot:
    ld a,h
    or l
    jr nz,p1136_gate_bad
    ld a,$80
    ld ($4000),a
    ld a,(p1136_attr)
    ld ($5800),a
    ld a,(p1136_plot_calls)
    inc a
    ld (p1136_plot_calls),a
    xor a
    ret
p1136_udg_clear:
    ld a,h
    or a
    jr nz,p1136_gate_bad
    ld a,l
    cp 3
    jr nz,p1136_gate_bad
    ld hl,p1136_udg_bank+24
    ld b,8
    xor a
p1136_udg_clear_loop:
    ld (hl),a
    inc hl
    djnz p1136_udg_clear_loop
    ld a,(p1136_udg_calls)
    inc a
    ld (p1136_udg_calls),a
    xor a
    ret
p1136_gate_bad:
    ld a,E_FORMAT
    scf
    ret
p1136_gateway_end:
    SAVEBIN "p1136-gateway.bin",p1136_gateway,p1136_gateway_end-p1136_gateway
''', encoding="utf-8", newline="\n")

    assembled = run_command(
        [assembler, "--nologo", "--sym=p1136-graphics-native.sym", fixture.name],
        cwd=build, timeout_seconds=60,
    )
    require(not assembled.timed_out and assembled.exit_code == 0,
            f"P11.36 assemble: {assembled.stderr or assembled.stdout}")
    main = (build / "p1136-main.bin").read_bytes()
    gateway = (build / "p1136-gateway.bin").read_bytes()
    require(0 < len(main) <= 0x5000, f"P11.36 native fixture too large: {len(main)}")
    syms = phase3_open_descriptions._symbols(
        build / "p1136-graphics-native.sym",
        ("p1136_compile", "p1136_negative", "p1136_link", "p1136_lifecycle")
    )

    assertions = [
        {"name": "graphics-udg-c-source-has-no-direct-kernel-memory-access", "passed": True},
        {"name": "pinned-sdk-reference-result-recorded", "passed": True},
        {"name": "native-cc-tokenizes-and-emits-graphics-udg-obj1", "passed": True},
        {"name": "native-ld-links-graphics-udg-runtime-archive-members", "passed": True},
        {"name": "graphics-runtime-archive-members-are-target-z80-obj1", "passed": True},
    ]
    commands = [assembled]

    if action == "test":
        def patch(ram):
            ram[0:len(main)] = main
            ram[0xE000-0x4000:0xE000-0x4000+len(gateway)] = gateway

        for name in ("p1136_compile", "p1136_link", "p1136_lifecycle", "p1136_negative"):
            code = (b"\xF3" + phase1._ld_sp(0xBFC0) + phase1._call(syms[name])
                    + phase1._jp_c(FAIL_PC) + phase1._jp(PASS_PC))
            try:
                commands.append(run_sna(root, code, patch=patch, timeout=30))
            except DriverError as exc:
                raise P1136Error(f"{name} target-native graphics lifecycle failed: {exc}") from None

        assertions += [
            {"name": "fuse-native-compile-link-run-completes", "passed": True},
            {"name": "fuse-screen-pixel-4000-exact-80", "passed": True},
            {"name": "fuse-screen-attribute-5800-exact-02", "passed": True},
            {"name": "fuse-udg-slot3-cleared-exactly", "passed": True},
            {"name": "fuse-runtime-status-zero", "passed": True},
            {"name": "fuse-direct-kernel-memory-source-rejected", "passed": True},
        ]

    hashes = {
        "v1/src/demos/colors.c": sha256_file(source_path),
        "v1/tests/compiler/p1136-source-map.json": sha256_file(mapping_path),
        "v1/src/tools/cc.asm": sha256_file(cc_path),
        "tools/ld.asm": sha256_file(ld_path),
        "v1/src/libc48/runtime_archive.asm": sha256_file(archive_path),
        "v1/src/libc48/crt0.asm": sha256_file(crt0_path),
        "v1/build/p1136-main.bin": sha256_file(build / "p1136-main.bin"),
        "v1/build/p1136-gateway.bin": sha256_file(build / "p1136-gateway.bin"),
        "v1/tools-host/test-driver/phase11_step_36.py": sha256_file(root / "v1/tools-host/test-driver/phase11_step_36.py"),
        "v1/dist/certification/P11.35.build.json": sha256_file(root / "v1/dist/certification/P11.35.build.json"),
        "v1/dist/certification/P11.35.test.json": sha256_file(root / "v1/dist/certification/P11.35.test.json"),
    }
    return commands, hashes, assertions
