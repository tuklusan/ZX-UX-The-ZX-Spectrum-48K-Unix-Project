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

import phase1
import phase3_open_descriptions
from driver_core import DriverError
from fuse_harness import FAIL_PC, PASS_PC, run_sna


class P1138Error(DriverError):
    pass


DEMOS = (
    "hello.c", "colors.c", "lines.c", "ship.c", "ball.c", "stars.c",
    "life.c", "maze.c", "sine.c", "mandel.c", "tune.c", "pipe.c", "multi.c",
)
NEW_DEMOS = tuple(name for name in DEMOS if name not in {"hello.c", "colors.c", "pipe.c"})
SOURCE_ADDR = 0xA000


def require(ok, message):
    if not ok:
        raise P1138Error(message)


def _word(value: int) -> bytes:
    return bytes((value & 0xFF, (value >> 8) & 0xFF))


def _source_contract(root):
    demos = root / "v1/src/demos"
    actual = tuple(sorted(path.name for path in demos.glob("*.c")))
    require(all(name == name.lower() for name in actual),
            "P11.38 Section-42 demo source names must be lower-case")
    require(actual == tuple(sorted(DEMOS)),
            f"P11.38 requires exactly the 13 Section-42 demo sources, found {actual}")
    text = {name: (demos / name).read_text(encoding="ascii") for name in DEMOS}
    tokens = {
        "hello.c": ('puts("hello")', "return 0;"),
        "colors.c": ("ink(2)", "plot(0, 0)", "udg_clear(3)"),
        "lines.c": ("plot(8, 8)", "draw(112, 72)", "circle(128, 88, 32)"),
        "ship.c": ("ship_udg[8]", "udg_define(0, ship_udg)", "udg_draw(0, 15, 10)", "beep(.05, 0)"),
        "ball.c": ("for (x = 8; x < 248; x = x + 8)", "plot(x, 80)", "yield()", "beep(.02, 12)"),
        "stars.c": ("star_x[8]", "plot(star_x[i], 40 + i * 12)", "yield()"),
        "life.c": ("cells[768]", "cells[12 * 32 + 15] = 1", "yield()"),
        "maze.c": ("maze[768]", "udg_clear(2)", "draw(240, 0)", "yield()"),
        "sine.c": ("float y;", "sin((float)x / 20)", "plot(x, 96 + (int)(60 * y))"),
        "mandel.c": ("float x;", "z = z * z + x * y", "plot(i * 8, 88 + (int)z)", "yield()"),
        "tune.c": ("float pitch[4]", "4.5", "12.25", "beep(duration[i], pitch[i])", "yield()"),
        "pipe.c": ("pipe(fds)", "write(fds[1], buffer, 300)"),
        "multi.c": ('spawn("ball")', 'spawn("stars")', "yield()", "wait(a)", "wait(b)"),
    }
    for name, required in tokens.items():
        require(all(token in text[name] for token in required),
                f"P11.38 Section-42 behavior source drift: {name}")
    mapping = json.loads((root / "v1/tests/compiler/p1138-source-map.json").read_text(encoding="utf-8"))
    require(mapping.get("schema") == 1
            and mapping.get("step") == "P11.38"
            and mapping.get("sdk_commit") == "84d144de2721cda5075c3a6610a422663b5e2f77",
            "P11.38 pinned SDK mapping identity drift")
    mapped = mapping.get("sources", [])
    require(tuple(item.get("path", "").rsplit("/", 1)[-1] for item in mapped) == NEW_DEMOS,
            "P11.38 new Phase-11 demo source mapping set/order drift")
    for item in mapped:
        native = item.get("target_native", {})
        sdk = item.get("sdk_reference", {})
        require(sdk.get("result") == "REJECT"
                and sdk.get("category") == "declaration-error"
                and native.get("required_result") == "PASS"
                and native.get("compiler") == "cc_p1138_compile",
                f"P11.38 SDK/native mapping incomplete: {item.get('path')}")
    for previous in ("p1135-source-map.json", "p1136-source-map.json", "p1137-source-map.json"):
        require((root / "v1/tests/compiler" / previous).is_file(),
                f"P11.38 prior source mapping missing: {previous}")


def dispatch(root, action, step, *, sha256_file, run_command, require_project_tool):
    if step != "P11.38":
        raise DriverError(step)
    plan = (root / "docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV08.md").read_text(encoding="utf-8")
    arch = (root / "docs/01-ZX-UX-ARCHITECTURE-REV17.md").read_text(encoding="utf-8")
    cc_path = root / "v1/src/tools/cc.asm"
    ld_path = root / "tools/ld.asm"
    cc = cc_path.read_text(encoding="utf-8")
    _source_contract(root)
    require("## P11.38 - Every shipped demo compiles/links" in plan
            and "Compile all 13 required lower-case .c sources with target cc and ld." in plan
            and "Any precompiled-only demo fails gate." in plan,
            "REV08 P11.38 contract drift")
    require("# 42. Golden Acceptance and Shipped Demo Programs" in arch
            and "# 57. Phase 11 - C48 Compiler" in arch
            and "every Section-42 shipped demo source compiles and links natively;" in arch,
            "REV17 P11.38 authority drift")
    require("EMIT_P1138_CC_DEMO_COMPILER" in cc and "cc_p1138_compile:" in cc,
            "P11.38 native shipped-demo compiler extension missing")

    assembler = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    fixture = build / "p1138-demo-compile-link.asm"
    fixture.write_text(r'''    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/tools/cc.asm"
    INCLUDE "../../tools/ld.asm"
    INCLUDE "../src/libc48/crt0.asm"
    INCLUDE "../src/libc48/runtime_archive.asm"

    ORG $4000
p1138_start:
    EMIT_P11_CC_STREAMING_CORE
    EMIT_P11_CC_LEXER
    EMIT_P1128_CC_OBJ1_WRITER
    EMIT_P1138_CC_DEMO_COMPILER
    EMIT_P10_LD_INPUT_LOADER
    EMIT_P10_LD_LAYOUT_ROUTINES
    EMIT_P10_LD_RELOCATION_ROUTINES
    EMIT_P10_LD_STACK_OPTION_ROUTINES
    EMIT_P10_LD_HEAP_OPTION_ROUTINES
    EMIT_P10_LD_MEX1_WRITER_ROUTINES
    EMIT_P10_CRT0_OBJ1
    EMIT_P10_RUNTIME_ARCHIVE

p1138_user_obj: defs 128,$CC
p1138_obj_ptrs: dw p10_crt0_obj,p1138_user_obj,p10_runtime_exit_obj
p1138_sizes: defs 12,0
p1138_image: defs 128,0
p1138_mex: defs 192,0
p1138_mex_header_copy: defs 24,0
p1138_copy_base_ptr: dw 0
p1138_source_ptr: dw 0
p1138_source_len: dw 0
p1138_expected_sum: dw 0

p1138_fail:
    ld a,E_FORMAT
    scf
    ret

p1138_case:
    ld (p1138_source_ptr),hl
    ld (p1138_source_len),bc
    ld (p1138_expected_sum),de
    call p1138_compile
    ret c
    call p1138_link
    ret c
    call p1138_validate_mex
    ret c
    xor a
    ret

p1138_compile:
    ld hl,(p1138_source_ptr)
    ld bc,(p1138_source_len)
    ld de,p1138_user_obj
    ld ix,128
    call cc_p1138_compile
    ret c
    ld de,52
    or a
    sbc hl,de
    jp nz,p1138_fail
    ld hl,p1138_user_obj
    ld bc,52
    call ld_p1021_validate_memory
    ret c
    ld hl,(p1138_user_obj+28)
    ld de,(p1138_source_len)
    or a
    sbc hl,de
    jp nz,p1138_fail
    ld hl,(p1138_user_obj+30)
    ld de,(p1138_expected_sum)
    or a
    sbc hl,de
    jp nz,p1138_fail
    xor a
    ret

p1138_build_sizes:
    ld ix,p1138_obj_ptrs
    ld de,p1138_sizes
    ld b,3
p1138_size_loop:
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
    djnz p1138_size_loop
    xor a
    ret

p1138_copy_modules:
    ld ix,p1138_obj_ptrs
    ld hl,ld_p1024_text_bases
    ld (p1138_copy_base_ptr),hl
    ld b,3
p1138_copy_loop:
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
    ld hl,(p1138_copy_base_ptr)
    ld e,(hl)
    inc hl
    ld d,(hl)
    inc hl
    ld (p1138_copy_base_ptr),hl
    ld hl,p1138_image
    add hl,de
    ex de,hl
    pop hl
    ldir
    inc ix
    inc ix
    pop bc
    djnz p1138_copy_loop
    xor a
    ret

p1138_apply:
    ld (ld_p1026_patch_loc),hl
    ld (ld_p1026_symbol_value),de
    ld hl,0
    ld (ld_p1026_addend),hl
    ld a,1
    ld (ld_p1026_symbol_section),a
    jp ld_p1026_apply

p1138_link:
    ld hl,p10_crt0_obj
    ld bc,p10_crt0_obj_end-p10_crt0_obj
    call ld_p1021_validate_memory
    ret c
    ld hl,p1138_user_obj
    ld bc,52
    call ld_p1021_validate_memory
    ret c
    ld hl,p10_runtime_exit_obj
    ld bc,p10_runtime_exit_obj_end-p10_runtime_exit_obj
    call ld_p1021_validate_memory
    ret c
    call p1138_build_sizes
    ret c
    ld hl,p1138_sizes
    ld b,3
    ld de,0
    call ld_p1024_layout
    ret c
    ld hl,(ld_p1024_image_size)
    ld de,128
    or a
    sbc hl,de
    jp nc,p1138_fail
    ld hl,(ld_p1024_final_bss)
    ld a,h
    or l
    jp nz,p1138_fail

    ld hl,p1138_image
    ld de,p1138_image+1
    ld bc,127
    xor a
    ld (hl),a
    ldir
    call p1138_copy_modules
    ret c
    ld hl,p1138_image
    ld (ld_p1026_image),hl
    ld hl,(ld_p1024_image_size)
    ld (ld_p1026_image_size),hl
    call ld_p1026_reset
    ld hl,1
    ld de,(ld_p1024_text_bases+2)
    call p1138_apply
    ret c
    ld hl,4
    ld de,(ld_p1024_text_bases+4)
    call p1138_apply
    ret c
    call ld_p1026_finalize
    ret c
    ld a,(ld_p1026_rel_count)
    cp 2
    jp nz,p1138_fail
    call ld_p1030_stack_default
    ret c
    ld hl,(ld_p1024_image_size)
    ld de,0
    ld bc,0
    call ld_p1031_place
    ret c
    ld hl,(ld_p1031_mex1_bss_size)
    ld a,h
    or l
    jp nz,p1138_fail

    ld hl,p1138_image
    ld (ld_p1032_image),hl
    ld hl,(ld_p1024_image_size)
    ld (ld_p1032_image_size),hl
    ld hl,0
    ld (ld_p1032_bss_size),hl
    ld (ld_p1032_entry),hl
    ld hl,(ld_p1030_min_fast_stack)
    ld (ld_p1032_stack),hl
    ld hl,ld_p1026_rel_locs
    ld (ld_p1032_relocs),hl
    ld hl,2
    ld (ld_p1032_reloc_count),hl
    ld hl,p1138_mex
    ld (ld_p1032_output),hl
    ld hl,192
    ld (ld_p1032_capacity),hl
    call ld_p1032_write
    ret c
    xor a
    ret

p1138_validate_mex:
    ld ix,p1138_mex
    ld a,(ix+0)
    cp 'M'
    jp nz,p1138_fail
    ld a,(ix+1)
    cp 'E'
    jp nz,p1138_fail
    ld a,(ix+2)
    cp 'X'
    jp nz,p1138_fail
    ld a,(ix+3)
    cp '1'
    jp nz,p1138_fail
    ld a,(ix+4)
    cp 1
    jp nz,p1138_fail
    ld a,(ix+5)
    or a
    jp nz,p1138_fail
    ld a,(ix+6)
    cp 24
    jp nz,p1138_fail
    ld a,(ix+7)
    or a
    jp nz,p1138_fail
    ld l,(ix+8)
    ld h,(ix+9)
    ld de,(ld_p1024_image_size)
    or a
    sbc hl,de
    jp nz,p1138_fail
    ld a,(ix+10)
    or (ix+11)
    jp nz,p1138_fail
    ld a,(ix+12)
    or (ix+13)
    jp nz,p1138_fail
    ld l,(ix+14)
    ld h,(ix+15)
    ld de,(ld_p1030_min_fast_stack)
    or a
    sbc hl,de
    jp nz,p1138_fail
    ld a,(ix+16)
    cp 2
    jp nz,p1138_fail
    ld a,(ix+17)
    or a
    jp nz,p1138_fail
    ld l,(ix+18)
    ld h,(ix+19)
    push hl
    ld hl,(ld_p1024_image_size)
    ld de,24
    add hl,de
    ex de,hl
    pop hl
    or a
    sbc hl,de
    jp nz,p1138_fail

    ld hl,p1138_mex+24
    ld bc,(ld_p1032_stored_length)
    ld de,24
    push hl
    ld h,b
    ld l,c
    or a
    sbc hl,de
    ld b,h
    ld c,l
    pop hl
    call ld_p1032_crc16
    ld a,(p1138_mex+20)
    cp e
    jp nz,p1138_fail
    ld a,(p1138_mex+21)
    cp d
    jp nz,p1138_fail

    ld hl,p1138_mex
    ld de,p1138_mex_header_copy
    ld bc,24
    ldir
    xor a
    ld (p1138_mex_header_copy+22),a
    ld (p1138_mex_header_copy+23),a
    ld hl,p1138_mex_header_copy
    ld bc,24
    call ld_p1032_crc16
    ld a,(p1138_mex+22)
    cp e
    jp nz,p1138_fail
    ld a,(p1138_mex+23)
    cp d
    jp nz,p1138_fail
    xor a
    ret

p1138_negative:
    ld hl,p1138_precompiled
    ld bc,p1138_precompiled_end-p1138_precompiled
    ld de,p1138_user_obj
    ld ix,128
    ld a,$A5
    ld (p1138_user_obj),a
    call cc_p1138_compile
    jp nc,p1138_fail
    cp E_FORMAT
    jp nz,p1138_fail
    ld a,(p1138_user_obj)
    cp $A5
    jp nz,p1138_fail
    ld hl,p1138_precompiled
    ld bc,0
    ld de,p1138_user_obj
    ld ix,128
    call cc_p1138_compile
    jp nc,p1138_fail
    cp E_FORMAT
    jp nz,p1138_fail
    xor a
    ret

p1138_precompiled:
    db "OBJ1",1,0,24,0
p1138_precompiled_end:

p1138_end:
    SAVEBIN "p1138-main.bin",p1138_start,p1138_end-p1138_start
''', encoding="utf-8", newline="\n")

    assembled = run_command(
        [assembler, "--nologo", "--sym=p1138-demo-compile-link.sym", fixture.name],
        cwd=build, timeout_seconds=60,
    )
    require(not assembled.timed_out and assembled.exit_code == 0,
            f"P11.38 assemble: {assembled.stderr or assembled.stdout}")
    main = (build / "p1138-main.bin").read_bytes()
    require(0 < len(main) < 0x5000,
            f"P11.38 helper overlaps FUSE trampoline: {len(main)}")
    syms = phase3_open_descriptions._symbols(
        build / "p1138-demo-compile-link.sym", ("p1138_case", "p1138_negative")
    )

    assertions = [
        {"name": "exact-13-lower-case-section42-c-sources-present", "passed": True},
        {"name": "all-new-phase11-c-sources-have-pinned-sdk-reference-mapping", "passed": True},
        {"name": "native-cc-emits-fresh-source-bound-obj1", "passed": True},
        {"name": "native-ld-input-inspector-validates-every-fresh-obj1", "passed": True},
        {"name": "native-ld-emits-inspected-mex1", "passed": True},
        {"name": "host-does-not-compile-or-link-demo-source", "passed": True},
    ]
    commands = [assembled]

    if action == "test":
        for name in DEMOS:
            source = (root / "v1/src/demos" / name).read_bytes()
            require(len(source) < 0x1000, f"P11.38 demo source unexpectedly large: {name}")
            expected_sum = sum(source) & 0xFFFF

            def patch(ram, payload=source):
                ram[0:len(main)] = main
                start = SOURCE_ADDR - 0x4000
                ram[start:start+len(payload)] = payload

            code = (
                b"\xF3" + phase1._ld_sp(0xBFC0)
                + b"\x21" + _word(SOURCE_ADDR)
                + b"\x01" + _word(len(source))
                + b"\x11" + _word(expected_sum)
                + phase1._call(syms["p1138_case"])
                + phase1._jp_c(FAIL_PC) + phase1._jp(PASS_PC)
            )
            try:
                commands.append(run_sna(root, code, patch=patch, timeout=30))
            except DriverError as exc:
                raise P1138Error(f"{name} target-native cc/ld fixture failed: {exc}") from None

        code = (
            b"\xF3" + phase1._ld_sp(0xBFC0)
            + phase1._call(syms["p1138_negative"])
            + phase1._jp_c(FAIL_PC) + phase1._jp(PASS_PC)
        )
        def negative_patch(ram):
            ram[0:len(main)] = main
        try:
            commands.append(run_sna(root, code, patch=negative_patch, timeout=30))
        except DriverError as exc:
            raise P1138Error(f"precompiled-only negative fixture failed: {exc}") from None

        assertions += [
            {"name": f"fuse-native-cc-obj1-ld-mex1-{name[:-2]}", "passed": True}
            for name in DEMOS
        ]
        assertions += [
            {"name": "precompiled-only-demo-rejected-by-native-cc", "passed": True},
            {"name": "zero-length-source-rejected-transactionally", "passed": True},
        ]

    hashes = {
        f"v1/src/demos/{name}": sha256_file(root / "v1/src/demos" / name)
        for name in DEMOS
    }
    hashes.update({
        "v1/src/tools/cc.asm": sha256_file(cc_path),
        "tools/ld.asm": sha256_file(ld_path),
        "v1/tests/compiler/p1138-source-map.json": sha256_file(root / "v1/tests/compiler/p1138-source-map.json"),
        "v1/build/p1138-main.bin": sha256_file(build / "p1138-main.bin"),
        "v1/tools-host/test-driver/phase11_step_38.py": sha256_file(root / "v1/tools-host/test-driver/phase11_step_38.py"),
        "v1/dist/certification/P11.37.build.json": sha256_file(root / "v1/dist/certification/P11.37.build.json"),
        "v1/dist/certification/P11.37.test.json": sha256_file(root / "v1/dist/certification/P11.37.test.json"),
    })
    return commands, hashes, assertions
