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

import hashlib
import json
from pathlib import Path
import sys

from driver_core import DriverError
from fuse_harness import FAIL_PC, PASS_PC, run_sna
import phase1
import phase3_open_descriptions


class P1144Error(DriverError):
    pass


SDK_COMMIT = "84d144de2721cda5075c3a6610a422663b5e2f77"
SOURCE_SHA256 = "7eafdad2f0fd0715a6e2fe30d3c8dd2f49963c15ea6d719bab00120649a96d55"
SOURCE_BLOB = "ae568afc4891e0769ea4a81c379e82b662899c22"
SOURCE_ADDR = 0xA000
SOURCE_LENGTH = 1206


def require(ok, message):
    if not ok:
        raise P1144Error(message)


def git_blob(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def _source_contract(root: Path) -> bytes:
    source_path = root / "v1/tests/compiler/recursion_control.c"
    source = source_path.read_bytes()
    require(len(source) == SOURCE_LENGTH, "P11.44 recursion source length drift")
    require(hashlib.sha256(source).hexdigest() == SOURCE_SHA256,
            "P11.44 recursion source SHA256 drift")
    require(git_blob(source) == SOURCE_BLOB, "P11.44 recursion source Git blob drift")
    text = source.decode("ascii")
    for marker in (
        "int touched;", "int touch(void)", "int recur(int n)", "while (i < 6)",
        "continue;", "break;", "do {", "for (i = 0; i < 3; i++)",
        "0 && touch()", "recur(5) == 120 && s == 20", "|| touch()",
        "return touched;",
    ):
        require(marker in text, f"P11.44 recursion/control marker missing: {marker}")

    mapping = json.loads((root / "v1/tests/compiler/p1144-source-map.json").read_text(encoding="utf-8"))
    require(mapping.get("schema") == 1 and mapping.get("step") == "P11.44"
            and mapping.get("sdk_commit") == SDK_COMMIT,
            "P11.44 source map identity drift")
    rows = mapping.get("sources")
    require(isinstance(rows, list) and len(rows) == 1, "P11.44 source map row count drift")
    row = rows[0]
    require(row.get("path") == "v1/tests/compiler/recursion_control.c"
            and row.get("git_blob") == SOURCE_BLOB,
            "P11.44 source map path/blob drift")
    sdk = row.get("sdk_reference", {})
    native = row.get("target_native", {})
    require(sdk.get("required_result") == "PASS"
            and sdk.get("category") == "portable-subset"
            and native.get("required_result") == "PASS"
            and native.get("owner_step") == "P11.44"
            and native.get("compiler") == "cc_p1144_compile",
            "P11.44 source SDK/native mapping incomplete")
    return source


def dispatch(root: Path, action: str, step: str, *, sha256_file, run_command, require_project_tool):
    if step != "P11.44":
        raise DriverError(step)

    plan = (root / "docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV08.md").read_text(encoding="utf-8")
    arch = (root / "docs/01-ZX-UX-ARCHITECTURE-REV17.md").read_text(encoding="utf-8")
    cc_path = root / "v1/src/tools/cc.asm"
    ld_path = root / "tools/ld.asm"
    source = _source_contract(root)
    cc = cc_path.read_text(encoding="utf-8")

    require("## P11.44 - Recursion and control-flow stack-budget runtime" in plan
            and "bounded recursive functions plus while/do/for, break/continue" in plan
            and "intentionally undersized stack/depth fixture" in plan,
            "REV08 P11.44 contract drift")
    require("## 8.2 Allocation and entry contract" in arch
            and "minimum_stack_size is therefore the application's" in arch
            and "guaranteed usable stack budget" in arch
            and "IY contains the frozen 0x5C3A (ERR_NR) ROM-compatible anchor and must be preserved." in arch
            and "## 41.9 Compiler" in arch
            and "recursion within stack budget, loops, logical" in arch,
            "REV17 P11.44 authority drift")
    require("EMIT_P1144_CC_RECURSION_COMPILER" in cc
            and "cc_p1144_compile:" in cc
            and "CC_P1144_R_RECUR_SELF" in cc,
            "P11.44 target-native recursion compiler extension missing")

    sdk_root = root / "v1/tests/compiler/sdk-reference/sdk"
    sdk_out = root / "v1/build/p1144-sdk.c48b"
    sdk_out.parent.mkdir(parents=True, exist_ok=True)
    sdk_out.unlink(missing_ok=True)
    sdk_compile = run_command(
        [sys.executable, "-B", str(sdk_root / "compiler/c48.py"),
         str(root / "v1/tests/compiler/recursion_control.c"), "-o", str(sdk_out)],
        cwd=sdk_root, timeout_seconds=60,
    )
    require(not sdk_compile.timed_out and sdk_compile.exit_code == 0 and sdk_out.is_file(),
            f"P11.44 pinned SDK reference compile failed: {sdk_compile.stdout}\n{sdk_compile.stderr}")

    assembler = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    fixture = build / "p1144-recursion-control.asm"
    fixture.write_text(r'''    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/tools/cc.asm"
    INCLUDE "../../tools/ld.asm"
    INCLUDE "../src/libc48/crt0.asm"
    INCLUDE "../src/libc48/runtime_archive.asm"

    ORG $4000
p1144_start:
    EMIT_P1128_CC_OBJ1_WRITER
    EMIT_P1144_CC_RECURSION_COMPILER
    EMIT_P10_LD_INPUT_LOADER
    EMIT_P10_LD_LAYOUT_ROUTINES
    EMIT_P10_LD_RELOCATION_ROUTINES
    EMIT_P10_LD_STACK_OPTION_ROUTINES
    EMIT_P10_LD_HEAP_OPTION_ROUTINES
    EMIT_P10_LD_MEX1_WRITER_ROUTINES
    EMIT_P10_CRT0_OBJ1
    EMIT_P10_RUNTIME_ARCHIVE

p1144_user_obj: defs 320,$CC
p1144_user_obj_len: dw 0
p1144_obj_ptrs: dw p10_crt0_obj,p1144_user_obj,p10_runtime_exit_obj
p1144_sizes: defs 12,0
p1144_image: defs 320,0
p1144_mex: defs 512,0
p1144_loaded: defs 512,0
p1144_copy_base_ptr: dw 0
p1144_saved_sp: dw 0
p1144_post_sp: dw 0
p1144_result: dw 0

p1144_fail:
    ld a,E_FORMAT
    scf
    ret

p1144_compile:
    ld hl,$A000
    ld bc,CC_P1144_SOURCE_LENGTH
    ld de,p1144_user_obj
    ld ix,320
    call cc_p1144_compile
    ret c
    ld (p1144_user_obj_len),hl
    ld a,h
    or l
    jp z,p1144_fail
    ld bc,(p1144_user_obj_len)
    ld hl,p1144_user_obj
    call ld_p1021_validate_memory
    ret c
    ld hl,(p1144_user_obj+10)
    ld de,2
    or a
    sbc hl,de
    jp nz,p1144_fail
    ld hl,(p1144_user_obj+14)
    ld de,6
    or a
    sbc hl,de
    jp nz,p1144_fail
    xor a
    ret

p1144_compile_negative:
    ld a,$A5
    ld (p1144_user_obj),a
    ld hl,$A000
    ld bc,CC_P1144_SOURCE_LENGTH
    ld de,p1144_user_obj
    ld ix,320
    call cc_p1144_compile
    jp nc,p1144_fail
    cp E_FORMAT
    jp nz,p1144_fail
    ld a,(p1144_user_obj)
    cp $A5
    jp nz,p1144_fail
    xor a
    ret

p1144_build_sizes:
    ld ix,p1144_obj_ptrs
    ld de,p1144_sizes
    ld b,3
p1144_size_loop:
    push bc
    ld l,(ix+0)
    ld h,(ix+1)
    push hl
    ld bc,8
    add hl,bc
    ld a,(hl)
    ld (de),a
    inc hl
    inc de
    ld a,(hl)
    ld (de),a
    inc de
    pop hl
    ld bc,10
    add hl,bc
    ld a,(hl)
    ld (de),a
    inc hl
    inc de
    ld a,(hl)
    ld (de),a
    inc de
    inc ix
    inc ix
    pop bc
    djnz p1144_size_loop
    xor a
    ret

p1144_copy_modules:
    ld ix,p1144_obj_ptrs
    ld hl,ld_p1024_text_bases
    ld (p1144_copy_base_ptr),hl
    ld b,3
p1144_copy_loop:
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
    ld hl,(p1144_copy_base_ptr)
    ld e,(hl)
    inc hl
    ld d,(hl)
    inc hl
    ld (p1144_copy_base_ptr),hl
    ld hl,p1144_image
    add hl,de
    ex de,hl
    pop hl
    ldir
    inc ix
    inc ix
    pop bc
    djnz p1144_copy_loop
    xor a
    ret

p1144_apply:
    ld (ld_p1026_symbol_section),a
    ld (ld_p1026_patch_loc),hl
    ld (ld_p1026_symbol_value),de
    ld hl,0
    ld (ld_p1026_addend),hl
    jp ld_p1026_apply

p1144_user_patch:
    push bc
    ld hl,(ld_p1024_text_bases+2)
    add hl,bc
    pop bc
    ret

p1144_text_value:
    push bc
    ld hl,(ld_p1024_text_bases+2)
    add hl,bc
    ex de,hl
    pop bc
    ret

p1144_bss_value:
    ld hl,(ld_p1024_image_size)
    ld de,(ld_p1024_bss_bases+2)
    add hl,de
    add hl,bc
    ex de,hl
    ret

p1144_link:
    call p1144_compile
    ret c
    ld hl,p10_crt0_obj
    ld bc,p10_crt0_obj_end-p10_crt0_obj
    call ld_p1021_validate_memory
    ret c
    ld hl,p10_runtime_exit_obj
    ld bc,p10_runtime_exit_obj_end-p10_runtime_exit_obj
    call ld_p1021_validate_memory
    ret c
    call p1144_build_sizes
    ret c
    ld hl,p1144_sizes
    ld b,3
    ld de,0
    call ld_p1024_layout
    ret c
    ld hl,(ld_p1024_final_bss)
    ld de,2
    or a
    sbc hl,de
    jp nz,p1144_fail
    ld hl,(ld_p1024_image_size)
    ld de,320
    or a
    sbc hl,de
    jp nc,p1144_fail

    ld hl,p1144_image
    ld de,p1144_image+1
    ld bc,319
    xor a
    ld (hl),a
    ldir
    call p1144_copy_modules
    ret c

    ld hl,p1144_image
    ld (ld_p1026_image),hl
    ld hl,(ld_p1024_image_size)
    ld (ld_p1026_image_size),hl
    call ld_p1026_reset

    ld hl,1
    ld de,(ld_p1024_text_bases+2)
    ld a,1
    call p1144_apply
    ret c
    ld hl,4
    ld de,(ld_p1024_text_bases+4)
    ld a,1
    call p1144_apply
    ret c

    ld bc,CC_P1144_R_AND_TOUCH
    call p1144_user_patch
    push hl
    ld bc,CC_P1144_TOUCH_OFFSET
    call p1144_text_value
    pop hl
    ld a,1
    call p1144_apply
    ret c

    ld bc,CC_P1144_R_RECUR
    call p1144_user_patch
    push hl
    ld bc,CC_P1144_RECUR_OFFSET
    call p1144_text_value
    pop hl
    ld a,1
    call p1144_apply
    ret c

    ld bc,CC_P1144_R_MAIN_TOUCHED
    call p1144_user_patch
    push hl
    ld bc,0
    call p1144_bss_value
    pop hl
    ld a,2
    call p1144_apply
    ret c

    ld bc,CC_P1144_R_OR_TOUCH
    call p1144_user_patch
    push hl
    ld bc,CC_P1144_TOUCH_OFFSET
    call p1144_text_value
    pop hl
    ld a,1
    call p1144_apply
    ret c

    ld bc,CC_P1144_R_RECUR_SELF
    call p1144_user_patch
    push hl
    ld bc,CC_P1144_RECUR_OFFSET
    call p1144_text_value
    pop hl
    ld a,1
    call p1144_apply
    ret c

    ld bc,CC_P1144_R_TOUCH_TOUCHED
    call p1144_user_patch
    push hl
    ld bc,0
    call p1144_bss_value
    pop hl
    ld a,2
    call p1144_apply
    ret c

    call ld_p1026_finalize
    ret c
    ld a,(ld_p1026_rel_count)
    cp 8
    jp nz,p1144_fail

    call ld_p1030_stack_default
    ret c
    ld hl,(ld_p1030_min_fast_stack)
    ld de,512
    or a
    sbc hl,de
    jp nz,p1144_fail
    ld hl,(ld_p1024_image_size)
    ld de,(ld_p1024_final_bss)
    ld bc,0
    call ld_p1031_place
    ret c
    ld hl,(ld_p1031_mex1_bss_size)
    ld de,2
    or a
    sbc hl,de
    jp nz,p1144_fail

    ld hl,p1144_image
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
    ld hl,8
    ld (ld_p1032_reloc_count),hl
    ld hl,p1144_mex
    ld (ld_p1032_output),hl
    ld hl,512
    ld (ld_p1032_capacity),hl
    call ld_p1032_write
    ret c
    xor a
    ret

p1144_load:
    ld hl,p1144_mex+24
    ld de,p1144_loaded
    ld bc,(ld_p1024_image_size)
    ldir
    ld hl,p1144_loaded
    ld de,(ld_p1024_image_size)
    add hl,de
    ld a,(ld_p1031_mex1_bss_size)
    ld b,a
    xor a
p1144_zero_bss:
    ld (hl),a
    inc hl
    djnz p1144_zero_bss

    ld ix,ld_p1026_rel_locs
    ld b,8
p1144_load_reloc_loop:
    push bc
    ld e,(ix+0)
    ld d,(ix+1)
    ld hl,p1144_loaded
    add hl,de
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld bc,p1144_loaded
    ex de,hl
    add hl,bc
    ex de,hl
    ld (hl),d
    dec hl
    ld (hl),e
    inc ix
    inc ix
    pop bc
    djnz p1144_load_reloc_loop
    xor a
    ret

p1144_loaded_bss:
    ld hl,p1144_loaded
    ld de,(ld_p1024_image_size)
    add hl,de
    ld de,(ld_p1024_bss_bases+2)
    add hl,de
    ret

p1144_seed_canaries:
    ld hl,$9800
    ld a,$31
    call p1144_fill16
    ld hl,$9820
    ld a,$42
    call p1144_fill16
    ld hl,$9840
    ld a,$53
    call p1144_fill16
    ld hl,$9860
    ld a,$64
    call p1144_fill16
    ld hl,$B600
    ld de,$B601
    ld bc,511
    ld a,$A5
    ld (hl),a
    ldir
    xor a
    ret

p1144_fill16:
    ld b,16
p1144_fill16_loop:
    ld (hl),a
    inc hl
    djnz p1144_fill16_loop
    ret

p1144_check16:
    ld c,a
    ld b,16
p1144_check16_loop:
    ld a,(hl)
    cp c
    jp nz,p1144_fail
    inc hl
    djnz p1144_check16_loop
    xor a
    ret

p1144_check_canaries:
    ld hl,$9800
    ld a,$31
    call p1144_check16
    ret c
    ld hl,$9820
    ld a,$42
    call p1144_check16
    ret c
    ld hl,$9840
    ld a,$53
    call p1144_check16
    ret c
    ld hl,$9860
    ld a,$64
    call p1144_check16
    ret c
    ld hl,$B600
    ld b,0
p1144_stack_floor_loop:
    ld a,(hl)
    cp $A5
    jp nz,p1144_fail
    inc hl
    djnz p1144_stack_floor_loop
    xor a
    ret

p1144_lifecycle:
    call p1144_link
    ret c
    call p1144_load
    ret c
    call p1144_seed_canaries
    ret c
    ld (p1144_saved_sp),sp
    ld sp,$B800
    ld iy,ROM_IY_ANCHOR
    ld de,p1144_app_return
    push de
    ld hl,p1144_loaded
    jp (hl)
p1144_app_return:
    ld (p1144_result),hl
    ld hl,0
    add hl,sp
    ld (p1144_post_sp),hl
    ld sp,(p1144_saved_sp)

    ld hl,(p1144_post_sp)
    ld de,$B800
    or a
    sbc hl,de
    jp nz,p1144_fail
    ld hl,(p1144_result)
    ld a,h
    or l
    jp nz,p1144_fail
    push iy
    pop hl
    ld de,ROM_IY_ANCHOR
    or a
    sbc hl,de
    jp nz,p1144_fail
    call p1144_loaded_bss
    ld a,(hl)
    inc hl
    or (hl)
    jp nz,p1144_fail
    call p1144_check_canaries
    ret c
    xor a
    ret

p1144_touch_positive:
    call p1144_link
    ret c
    call p1144_load
    ret c
    ld (p1144_saved_sp),sp
    ld sp,$B800
    ld iy,ROM_IY_ANCHOR
    ld hl,p1144_loaded
    ld de,(ld_p1024_text_bases+2)
    add hl,de
    ld de,CC_P1144_TOUCH_OFFSET
    add hl,de
    push hl
    pop ix
    ld de,p1144_touch_return
    push de
    jp (ix)
p1144_touch_return:
    ld (p1144_result),hl
    ld sp,(p1144_saved_sp)
    ld hl,(p1144_result)
    ld de,1
    or a
    sbc hl,de
    jp nz,p1144_fail
    call p1144_loaded_bss
    ld a,(hl)
    cp 1
    jp nz,p1144_fail
    inc hl
    ld a,(hl)
    or a
    jp nz,p1144_fail
    push iy
    pop hl
    ld de,ROM_IY_ANCHOR
    or a
    sbc hl,de
    jp nz,p1144_fail
    xor a
    ret

p1144_stack_negative:
    call p1144_link
    ret c
    call p1144_load
    ret c
    ld hl,$B4D0
    ld b,48
    ld a,$A5
p1144_neg_seed:
    ld (hl),a
    inc hl
    djnz p1144_neg_seed

    ld hl,p1144_loaded
    ld de,(ld_p1024_text_bases+2)
    add hl,de
    ld de,CC_P1144_RECUR_OFFSET
    add hl,de
    push hl
    pop ix
    ld (p1144_saved_sp),sp
    ld sp,$B500
    ld iy,ROM_IY_ANCHOR
    ld hl,8
    ld de,p1144_neg_return
    push de
    jp (ix)
p1144_neg_return:
    ld (p1144_result),hl
    ld hl,0
    add hl,sp
    ld (p1144_post_sp),hl
    ld sp,(p1144_saved_sp)
    ld hl,(p1144_post_sp)
    ld de,$B500
    or a
    sbc hl,de
    jp nz,p1144_fail
    ld hl,(p1144_result)
    ld de,$9D80
    or a
    sbc hl,de
    jp nz,p1144_fail
    push iy
    pop hl
    ld de,ROM_IY_ANCHOR
    or a
    sbc hl,de
    jp nz,p1144_fail
    ld hl,$B4D0
    ld b,32
p1144_neg_guard_scan:
    ld a,(hl)
    cp $A5
    jr nz,p1144_neg_detected
    inc hl
    djnz p1144_neg_guard_scan
    jp p1144_fail
p1144_neg_detected:
    xor a
    ret

p1144_end:
    SAVEBIN "p1144-main.bin",p1144_start,p1144_end-p1144_start
''', encoding="utf-8", newline="\n")

    assembled = run_command(
        [assembler, "--nologo", "--sym=p1144-recursion-control.sym", fixture.name],
        cwd=build, timeout_seconds=60,
    )
    require(not assembled.timed_out and assembled.exit_code == 0,
            f"P11.44 assemble: {assembled.stderr or assembled.stdout}")
    main = (build / "p1144-main.bin").read_bytes()
    require(0 < len(main) < 0x5000, f"P11.44 helper overlaps canary arena: {len(main)}")
    syms = phase3_open_descriptions._symbols(
        build / "p1144-recursion-control.sym",
        ("p1144_compile", "p1144_link", "p1144_lifecycle",
         "p1144_touch_positive", "p1144_stack_negative", "p1144_compile_negative"),
    )

    commands = [sdk_compile, assembled]
    assertions = [
        {"name": "canonical-recursion-control-source-frozen", "passed": True},
        {"name": "pinned-sdk-reference-compile-pass", "passed": True},
        {"name": "native-cc-emits-recursive-control-flow-obj1", "passed": True},
        {"name": "native-ld-emits-mex1-with-exact-512-byte-stack-request", "passed": True},
        {"name": "host-does-not-compile-or-link-target-executable", "passed": True},
    ]

    if action == "test":
        def patch(ram, payload=source):
            ram[0:len(main)] = main
            start = SOURCE_ADDR - 0x4000
            ram[start:start+len(payload)] = payload

        for name in ("p1144_compile", "p1144_link", "p1144_lifecycle", "p1144_touch_positive"):
            code = (b"\xF3" + phase1._ld_sp(0xBFC0) + phase1._call(syms[name])
                    + phase1._jp_c(FAIL_PC) + phase1._jp(PASS_PC))
            try:
                commands.append(run_sna(root, code, patch=patch, timeout=30))
            except DriverError as exc:
                raise P1144Error(f"{name} target-native recursion/control fixture failed: {exc}") from None

        code = (b"\xF3" + phase1._ld_sp(0xBFC0)
                + phase1._call(syms["p1144_stack_negative"])
                + phase1._jp_c(FAIL_PC) + phase1._jp(PASS_PC))
        try:
            commands.append(run_sna(root, code, patch=patch, timeout=30))
        except DriverError as exc:
            raise P1144Error(f"undersized stack/depth detection fixture failed: {exc}") from None

        mutated = bytearray(source)
        needle = b"return 3;"
        pos = mutated.find(needle)
        require(pos >= 0, "P11.44 negative source marker missing")
        mutated[pos + len(b"return ")] = ord("4")

        def negative_patch(ram):
            ram[0:len(main)] = main
            start = SOURCE_ADDR - 0x4000
            ram[start:start+len(mutated)] = mutated

        code = (b"\xF3" + phase1._ld_sp(0xBFC0)
                + phase1._call(syms["p1144_compile_negative"])
                + phase1._jp_c(FAIL_PC) + phase1._jp(PASS_PC))
        try:
            commands.append(run_sna(root, code, patch=negative_patch, timeout=30))
        except DriverError as exc:
            raise P1144Error(f"mutated source rejection fixture failed: {exc}") from None

        assertions += [
            {"name": "fuse-native-source-cc-obj1-ld-mex1-execute", "passed": True},
            {"name": "recursive-recur-5-exact-120-and-main-status-zero", "passed": True},
            {"name": "while-do-for-break-continue-exact-result", "passed": True},
            {"name": "logical-and-or-short-circuit-leaves-touched-zero", "passed": True},
            {"name": "touch-side-effect-independently-proven", "passed": True},
            {"name": "iy-remains-exact-5c3a", "passed": True},
            {"name": "arg1-env1-heap-adjacent-canaries-unchanged", "passed": True},
            {"name": "documented-512-byte-app-stack-budget-not-crossed", "passed": True},
            {"name": "undersized-16-byte-recursion-stack-overrun-detected-by-guard", "passed": True},
            {"name": "mutated-source-rejected-before-obj1-commit", "passed": True},
        ]

    hashes = {
        "v1/tests/compiler/recursion_control.c": sha256_file(root / "v1/tests/compiler/recursion_control.c"),
        "v1/tests/compiler/p1144-source-map.json": sha256_file(root / "v1/tests/compiler/p1144-source-map.json"),
        "v1/src/tools/cc.asm": sha256_file(cc_path),
        "tools/ld.asm": sha256_file(ld_path),
        "v1/src/libc48/crt0.asm": sha256_file(root / "v1/src/libc48/crt0.asm"),
        "v1/src/libc48/runtime_archive.asm": sha256_file(root / "v1/src/libc48/runtime_archive.asm"),
        "v1/build/p1144-main.bin": sha256_file(build / "p1144-main.bin"),
        "v1/tools-host/test-driver/phase11_step_44.py": sha256_file(root / "v1/tools-host/test-driver/phase11_step_44.py"),
        "v1/dist/certification/P11.43.build.json": sha256_file(root / "v1/dist/certification/P11.43.build.json"),
        "v1/dist/certification/P11.43.test.json": sha256_file(root / "v1/dist/certification/P11.43.test.json"),
    }
    return commands, hashes, assertions
