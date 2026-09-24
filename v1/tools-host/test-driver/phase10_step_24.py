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

from pathlib import Path

import phase1
import phase3_open_descriptions
from driver_core import DriverError
from fuse_harness import PASS_PC, FAIL_PC, run_sna


class P1024Error(DriverError):
    pass


def require(ok, msg):
    if not ok:
        raise P1024Error(msg)


def dispatch(root, action, step, *, sha256_file, run_command, require_project_tool):
    if step != "P10.24":
        raise DriverError(step)

    source = (root / "tools/ld.asm").read_text(encoding="utf-8")
    assertions = [
        {"name":"normal-order-crt0-first","passed":"crt0 ID is always zero and first" in source},
        {"name":"user-then-archive-order","passed":"ld_p1024_order_user_loop:" in source and "ld_p1024_order_archive_loop:" in source},
        {"name":"even-text-and-bss-layout","passed":"ld_p1024_text_aligned:" in source and "ld_p1024_bss_aligned:" in source},
        {"name":"even-final-image-and-heap-base","passed":"ld_p1024_text_final_even:" in source and "ld_p1024_heap_even:" in source},
        {"name":"zero-padding-gate","passed":"ld_p1024_check_zero_offsets:" in source},
        {"name":"image-bss-32768-bound","passed":"ld de,$8001" in source and "ld_p1024_nospc:" in source},
    ]
    require(all(a["passed"] for a in assertions), "P10.24 static layout contract failure")

    assembler = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    fixture = build / "p1024-layout.asm"
    fixture.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../../tools/ld.asm"
    ORG $C000
fixture:
    EMIT_P10_LD_LAYOUT_ROUTINES

p1024_users: db 10,11
p1024_archive: db 2,3
; text,bss records in final order: crt0,user,puts,exit
p1024_table:
    dw 7,1
    dw 3,3
    dw 4,1
    dw 1,0
p1024_overflow_table:
    dw 32767,0
    dw 2,0

p1024_image:
    db $11,$11,$11,$11,$11,$11,$11,0
    db $22,$22,$22,0
    db $33,$33,$33,$33
    db $44,0
p1024_pad_offsets: dw 7,11,17

p1024_fail:
    ld a,E_FORMAT
    scf
    ret

p1024_order:
    xor a
    ld (ld_p1024_nostart),a
    ld hl,p1024_users
    ld b,2
    ld de,p1024_archive
    ld c,2
    call ld_p1024_build_order
    ret c
    ld a,(ld_p1024_order_count)
    cp 5
    jp nz,p1024_fail
    ld a,(ld_p1024_order+0)
    or a
    jp nz,p1024_fail
    ld a,(ld_p1024_order+1)
    cp 10
    jp nz,p1024_fail
    ld a,(ld_p1024_order+2)
    cp 11
    jp nz,p1024_fail
    ld a,(ld_p1024_order+3)
    cp 2
    jp nz,p1024_fail
    ld a,(ld_p1024_order+4)
    cp 3
    jp nz,p1024_fail
    xor a
    ret

p1024_nostart_order:
    ld a,1
    ld (ld_p1024_nostart),a
    ld hl,p1024_users
    ld b,2
    ld de,p1024_archive
    ld c,2
    call ld_p1024_build_order
    push af
    xor a
    ld (ld_p1024_nostart),a
    pop af
    ret c
    ld a,(ld_p1024_order_count)
    cp 4
    jp nz,p1024_fail
    ld a,(ld_p1024_order+0)
    cp 10
    jp nz,p1024_fail
    xor a
    ret

p1024_layout:
    ld hl,p1024_table
    ld b,4
    ld de,4
    call ld_p1024_layout
    ret c
    ld hl,(ld_p1024_image_size)
    ld de,18
    or a
    sbc hl,de
    jp nz,p1024_fail
    ld hl,(ld_p1024_final_bss)
    ld de,12
    or a
    sbc hl,de
    jp nz,p1024_fail
    ld hl,(ld_p1024_heap_base)
    ld de,8
    or a
    sbc hl,de
    jp nz,p1024_fail
    ld hl,(ld_p1024_text_bases+0)
    ld de,0
    or a
    sbc hl,de
    jp nz,p1024_fail
    ld hl,(ld_p1024_text_bases+2)
    ld de,8
    or a
    sbc hl,de
    jp nz,p1024_fail
    ld hl,(ld_p1024_text_bases+4)
    ld de,12
    or a
    sbc hl,de
    jp nz,p1024_fail
    ld hl,(ld_p1024_text_bases+6)
    ld de,16
    or a
    sbc hl,de
    jp nz,p1024_fail
    ld hl,(ld_p1024_bss_bases+0)
    ld de,0
    or a
    sbc hl,de
    jp nz,p1024_fail
    ld hl,(ld_p1024_bss_bases+2)
    ld de,2
    or a
    sbc hl,de
    jp nz,p1024_fail
    ld hl,(ld_p1024_bss_bases+4)
    ld de,6
    or a
    sbc hl,de
    jp nz,p1024_fail
    ld hl,(ld_p1024_bss_bases+6)
    ld de,8
    or a
    sbc hl,de
    jp nz,p1024_fail
    xor a
    ret

p1024_padding:
    ld hl,p1024_image
    ld de,p1024_pad_offsets
    ld b,3
    jp ld_p1024_check_zero_offsets

p1024_bad_padding:
    ld a,1
    ld (p1024_image+7),a
    ld hl,p1024_image
    ld de,p1024_pad_offsets
    ld b,3
    call ld_p1024_check_zero_offsets
    push af
    xor a
    ld (p1024_image+7),a
    pop af
    ret nc
    cp E_FORMAT
    jp nz,p1024_fail
    scf
    ret

p1024_overflow:
    ld hl,p1024_overflow_table
    ld b,2
    ld de,0
    call ld_p1024_layout
    ret nc
    cp E_NOSPC
    jp nz,p1024_fail
    scf
    ret

fixture_end:
    SAVEBIN "p1024-main.bin",fixture,fixture_end-fixture
""", encoding="utf-8", newline="\n")

    result = run_command([assembler, "--nologo", "--sym=p1024-layout.sym", fixture.name], cwd=build, timeout_seconds=30)
    require(not result.timed_out and result.exit_code == 0, f"P10.24 assemble: {result.stderr or result.stdout}")
    main = (build / "p1024-main.bin").read_bytes()
    names = ("p1024_order","p1024_nostart_order","p1024_layout","p1024_padding","p1024_bad_padding","p1024_overflow")
    syms = phase3_open_descriptions._symbols(build / "p1024-layout.sym", names)

    if action == "test":
        def patch(ram):
            ram[0xC000-0x4000:0xC000-0x4000+len(main)] = main
        for name in ("p1024_order","p1024_nostart_order","p1024_layout","p1024_padding"):
            code = b"\xF3" + phase1._ld_sp(0xBFC0) + phase1._call(syms[name]) + phase1._jp_c(FAIL_PC) + phase1._jp(PASS_PC)
            run_sna(root, code, patch=patch)
        for name in ("p1024_bad_padding","p1024_overflow"):
            code = b"\xF3" + phase1._ld_sp(0xBFC0) + phase1._call(syms[name]) + b"\xD2" + phase1._word(FAIL_PC) + phase1._jp(PASS_PC)
            run_sna(root, code, patch=patch)
        assertions += [
            {"name":"fuse-final-order-crt0-users-archive","passed":True},
            {"name":"fuse-nostart-omits-crt0","passed":True},
            {"name":"fuse-golden-text-bss-even-map","passed":True},
            {"name":"fuse-zero-alignment-bytes","passed":True},
            {"name":"fuse-nonzero-padding-rejected","passed":True},
            {"name":"fuse-image-bss-overflow-rejected","passed":True},
        ]

    hashes = {
        "tools/ld.asm": sha256_file(root / "tools/ld.asm"),
        "v1/build/p1024-main.bin": sha256_file(build / "p1024-main.bin"),
        "v1/tools-host/test-driver/phase10_step_24.py": sha256_file(root / "v1/tools-host/test-driver/phase10_step_24.py"),
        "v1/dist/certification/P10.23.build.json": sha256_file(root / "v1/dist/certification/P10.23.build.json"),
        "v1/dist/certification/P10.23.test.json": sha256_file(root / "v1/dist/certification/P10.23.test.json"),
    }
    return [result], hashes, assertions
