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

import phase1
import phase3_open_descriptions
from driver_core import DriverError
from fuse_harness import PASS_PC, FAIL_PC, run_sna


class P1026Error(DriverError):
    pass


def require(ok, msg):
    if not ok:
        raise P1026Error(msg)


def dispatch(root, action, step, *, sha256_file, run_command, require_project_tool):
    if step != "P10.26":
        raise DriverError(step)

    source = (root / "tools/ld.asm").read_text(encoding="utf-8")
    assertions = [
        {"name":"signed-widened-addend","passed":"magnitude = -signed(addend)" in source and "ld_p1026_arith:" in source},
        {"name":"abs-no-runtime-reloc","passed":"ABS: fixed absolute, no runtime relocation." in source},
        {"name":"text-bss-runtime-reloc","passed":"ld_p1026_emit_runtime:" in source},
        {"name":"sorted-runtime-table","passed":"ld_p1026_sort_i:" in source and "ld_p1026_sort_j:" in source},
        {"name":"unique-nonoverlap-bounds","passed":"duplicate or one-byte overlap is forbidden." in source and "ld_p1026_validate_patch:" in source},
    ]
    require(all(a["passed"] for a in assertions), "P10.26 static relocation contract failure")

    assembler = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    fixture = build / "p1026-relocs.asm"
    fixture.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../../tools/ld.asm"
    ORG $C000
fixture:
    EMIT_P10_LD_RELOCATION_ROUTINES

p1026_image: defs 16,0

p1026_setup:
    ld hl,p1026_image
    ld (ld_p1026_image),hl
    ld hl,16
    ld (ld_p1026_image_size),hl
    call ld_p1026_reset
    ret

p1026_apply_state:
    ld (ld_p1026_patch_loc),hl
    ld (ld_p1026_symbol_value),de
    ld (ld_p1026_addend),bc
    ld (ld_p1026_symbol_section),a
    jp ld_p1026_apply

p1026_apply_negative:
    call p1026_setup
    ld hl,8
    ld de,10
    ld bc,$FFFB
    ld a,2
    call p1026_apply_state
    ret c
    ld hl,(p1026_image+8)
    ld de,5
    or a
    sbc hl,de
    jp nz,p1026_fail
    ld a,(ld_p1026_rel_count)
    cp 1
    jp nz,p1026_fail
    xor a
    ret

p1026_apply_positive:
    call p1026_setup
    ld hl,4
    ld de,10
    ld bc,5
    ld a,1
    call p1026_apply_state
    ret c
    ld hl,(p1026_image+4)
    ld de,15
    or a
    sbc hl,de
    jp nz,p1026_fail
    xor a
    ret

p1026_apply_abs:
    call p1026_setup
    ld hl,0
    ld de,1
    ld bc,$FFFF
    ld a,3
    call p1026_apply_state
    ret c
    ld hl,2
    ld de,$FFFE
    ld bc,1
    ld a,3
    call p1026_apply_state
    ret c
    ld a,(ld_p1026_rel_count)
    or a
    jp nz,p1026_fail
    ld hl,(p1026_image+0)
    ld de,0
    or a
    sbc hl,de
    jp nz,p1026_fail
    ld hl,(p1026_image+2)
    ld de,$FFFF
    or a
    sbc hl,de
    jp nz,p1026_fail
    xor a
    ret

p1026_sort_only:
    call p1026_setup
    ld a,2
    ld (ld_p1026_rel_count),a
    ld hl,8
    ld (ld_p1026_rel_locs+0),hl
    ld hl,4
    ld (ld_p1026_rel_locs+2),hl
    ld a,2
    ld (ld_p1026_rel_sections+0),a
    ld a,1
    ld (ld_p1026_rel_sections+1),a
    call ld_p1026_finalize
    ret c
    ld hl,(ld_p1026_rel_locs+0)
    ld de,4
    or a
    sbc hl,de
    jp nz,p1026_fail
    ld hl,(ld_p1026_rel_locs+2)
    ld de,8
    or a
    sbc hl,de
    jp nz,p1026_fail
    xor a
    ret

p1026_positive:
    call p1026_setup
    ; Deliberately emit 8 before 4: finalizer must sort.
    ld hl,8
    ld de,10
    ld bc,$FFFB
    ld a,2
    call p1026_apply_state
    ret c
    ld hl,4
    ld de,10
    ld bc,5
    ld a,1
    call p1026_apply_state
    ret c
    ; ABS boundaries: 0 and FFFF, with no runtime entries.
    ld hl,0
    ld de,1
    ld bc,$FFFF
    ld a,3
    call p1026_apply_state
    ret c
    ld hl,2
    ld de,$FFFE
    ld bc,1
    ld a,3
    call p1026_apply_state
    ret c
    call ld_p1026_finalize
    ret c
    ld a,(ld_p1026_rel_count)
    cp 2
    jp nz,p1026_fail
    ld hl,(ld_p1026_rel_locs+0)
    ld de,4
    or a
    sbc hl,de
    jp nz,p1026_fail
    ld hl,(ld_p1026_rel_locs+2)
    ld de,8
    or a
    sbc hl,de
    jp nz,p1026_fail
    ld hl,(p1026_image+0)
    ld de,0
    or a
    sbc hl,de
    jp nz,p1026_fail
    ld hl,(p1026_image+2)
    ld de,$FFFF
    or a
    sbc hl,de
    jp nz,p1026_fail
    ld hl,(p1026_image+4)
    ld de,15
    or a
    sbc hl,de
    jp nz,p1026_fail
    ld hl,(p1026_image+8)
    ld de,5
    or a
    sbc hl,de
    jp nz,p1026_fail
    xor a
    ret

p1026_underflow:
    call p1026_setup
    ld hl,0
    ld de,0
    ld bc,$FFFF
    ld a,3
    call p1026_apply_state
    jp p1026_expect_format

p1026_overflow:
    call p1026_setup
    ld hl,0
    ld de,$FFFF
    ld bc,1
    ld a,3
    call p1026_apply_state
    jp p1026_expect_format

p1026_oob:
    call p1026_setup
    ld hl,15
    ld de,1
    ld bc,0
    ld a,1
    call p1026_apply_state
    jp p1026_expect_format

p1026_overlap:
    call p1026_setup
    ld a,2
    ld (ld_p1026_rel_count),a
    ld hl,4
    ld (ld_p1026_rel_locs+0),hl
    ld hl,5
    ld (ld_p1026_rel_locs+2),hl
    ld a,1
    ld (ld_p1026_rel_sections+0),a
    ld a,2
    ld (ld_p1026_rel_sections+1),a
    call ld_p1026_finalize
    jp p1026_expect_format

p1026_duplicate:
    call p1026_setup
    ld a,2
    ld (ld_p1026_rel_count),a
    ld hl,4
    ld (ld_p1026_rel_locs+0),hl
    ld (ld_p1026_rel_locs+2),hl
    ld a,1
    ld (ld_p1026_rel_sections+0),a
    ld (ld_p1026_rel_sections+1),a
    call ld_p1026_finalize
    jp p1026_expect_format

p1026_abs_runtime:
    call p1026_setup
    ld a,1
    ld (ld_p1026_rel_count),a
    ld hl,4
    ld (ld_p1026_rel_locs),hl
    ld a,3
    ld (ld_p1026_rel_sections),a
    call ld_p1026_finalize
    jp p1026_expect_format

p1026_expect_format:
    ret nc
    cp E_FORMAT
    jp nz,p1026_fail
    scf
    ret
p1026_fail:
    ld a,E_FORMAT
    scf
    ret

fixture_end:
    SAVEBIN "p1026-main.bin",fixture,fixture_end-fixture
""", encoding="utf-8", newline="\n")

    result = run_command([assembler, "--nologo", "--sym=p1026-relocs.sym", fixture.name], cwd=build, timeout_seconds=30)
    require(not result.timed_out and result.exit_code == 0, f"P10.26 assemble: {result.stderr or result.stdout}")
    main = (build / "p1026-main.bin").read_bytes()
    names = ("p1026_apply_negative","p1026_apply_positive","p1026_apply_abs","p1026_sort_only","p1026_positive","p1026_underflow","p1026_overflow","p1026_oob","p1026_overlap","p1026_duplicate","p1026_abs_runtime")
    syms = phase3_open_descriptions._symbols(build / "p1026-relocs.sym", names)

    if action == "test":
        def patch(ram):
            ram[0xC000-0x4000:0xC000-0x4000+len(main)] = main

        failures = []

        def run_case(name, expect_carry):
            if expect_carry:
                code = b"\\xF3" + phase1._ld_sp(0xBFC0) + phase1._call(syms[name]) + b"\\xD2" + phase1._word(FAIL_PC) + phase1._jp(PASS_PC)
            else:
                code = b"\\xF3" + phase1._ld_sp(0xBFC0) + phase1._call(syms[name]) + phase1._jp_c(FAIL_PC) + phase1._jp(PASS_PC)
            try:
                run_sna(root, code, patch=patch)
            except Exception:
                failures.append(name)

        for name in ("p1026_apply_abs","p1026_apply_positive","p1026_apply_negative","p1026_sort_only","p1026_positive"):
            run_case(name, False)
        for name in ("p1026_underflow","p1026_overflow","p1026_oob","p1026_overlap","p1026_duplicate","p1026_abs_runtime"):
            run_case(name, True)
        require(not failures, "P10.26 FUSE cases failed: " + ",".join(failures))
        assertions += [
            {"name":"fuse-signed-addend-boundaries","passed":True},
            {"name":"fuse-abs-versus-text-bss","passed":True},
            {"name":"fuse-runtime-relocs-sorted","passed":True},
            {"name":"fuse-underflow-overflow-rejected","passed":True},
            {"name":"fuse-duplicate-overlap-oob-rejected","passed":True},
            {"name":"fuse-abs-runtime-reloc-rejected","passed":True},
        ]

    hashes = {
        "tools/ld.asm": sha256_file(root / "tools/ld.asm"),
        "v1/build/p1026-main.bin": sha256_file(build / "p1026-main.bin"),
        "v1/tools-host/test-driver/phase10_step_26.py": sha256_file(root / "v1/tools-host/test-driver/phase10_step_26.py"),
        "v1/dist/certification/P10.25.build.json": sha256_file(root / "v1/dist/certification/P10.25.build.json"),
        "v1/dist/certification/P10.25.test.json": sha256_file(root / "v1/dist/certification/P10.25.test.json"),
    }
    return [result], hashes, assertions
