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


class P1031Error(DriverError):
    pass


def require(ok, msg):
    if not ok:
        raise P1031Error(msg)


def dispatch(root, action, step, *, sha256_file, run_command, require_project_tool):
    if step != "P10.31":
        raise DriverError(step)
    source = (root / "tools/ld.asm").read_text(encoding="utf-8")
    assertions = [
        {"name":"normal-default-1024","passed":"LD_P1031_HEAP_NORMAL_DEFAULT  EQU 1024" in source},
        {"name":"nostart-default-0","passed":"LD_P1031_HEAP_NOSTART_DEFAULT EQU 0" in source},
        {"name":"heap-max-8192","passed":"LD_P1031_HEAP_MAX             EQU 8192" in source},
        {"name":"even-only","passed":"bit 0,l" in source and "ld_p1031_heap_set:" in source},
        {"name":"decimal-parse-rejection","passed":"ld_p1031_heap_parse:" in source and "cp '0'" in source and "cp '9'+1" in source},
        {"name":"exact-bss-and-symbol-placement","passed":"ld_p1031_mex1_bss_size" in source and "ld_p1031_heap_start" in source and "ld_p1031_heap_end" in source},
        {"name":"combined-32768-bound","passed":"ld de,$8001" in source and "ld_p1031_nospc:" in source},
    ]
    require(all(a["passed"] for a in assertions), "P10.31 static heap-option contract failure")

    assembler = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    fixture = build / "p1031-heap.asm"
    fixture.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../../tools/ld.asm"
    ORG $C000
fixture:
    EMIT_P10_LD_HEAP_OPTION_ROUTINES

p1031_s0: db "0"
p1031_s2: db "2"
p1031_s1024: db "1024"
p1031_s8192: db "8192"
p1031_sodd: db "3"
p1031_sneg: db "-1"
p1031_sbad: db "12x"
p1031_shigh: db "8193"

p1031_fail:
    ld a,E_FORMAT
    scf
    ret

p1031_default_normal:
    xor a
    call ld_p1031_heap_default
    ret c
    ld hl,(ld_p1031_requested)
    ld de,1024
    or a
    sbc hl,de
    jp nz,p1031_fail
    xor a
    ret

p1031_default_nostart:
    ld a,1
    call ld_p1031_heap_default
    ret c
    ld hl,(ld_p1031_requested)
    ld a,h
    or l
    jp nz,p1031_fail
    xor a
    ret

p1031_place_1024:
    ld hl,18
    ld de,7
    ld bc,1024
    call ld_p1031_place
    ret c
    ld hl,(ld_p1031_heap_start)
    ld de,26
    or a
    sbc hl,de
    jp nz,p1031_fail
    ld hl,(ld_p1031_heap_end)
    ld de,1050
    or a
    sbc hl,de
    jp nz,p1031_fail
    ld hl,(ld_p1031_mex1_bss_size)
    ld de,1032
    or a
    sbc hl,de
    jp nz,p1031_fail
    xor a
    ret

p1031_parse0:
    ld hl,p1031_s0
    ld b,1
    call ld_p1031_heap_parse
    ret c
    ld hl,(ld_p1031_requested)
    ld a,h
    or l
    jp nz,p1031_fail
    xor a
    ret

p1031_parse2:
    ld hl,p1031_s2
    ld b,1
    call ld_p1031_heap_parse
    ret c
    ld hl,(ld_p1031_requested)
    ld de,2
    or a
    sbc hl,de
    jp nz,p1031_fail
    xor a
    ret

p1031_parse1024:
    ld hl,p1031_s1024
    ld b,4
    call ld_p1031_heap_parse
    ret c
    ld hl,(ld_p1031_requested)
    ld de,1024
    or a
    sbc hl,de
    jp nz,p1031_fail
    xor a
    ret

p1031_parse8192:
    ld hl,p1031_s8192
    ld b,4
    call ld_p1031_heap_parse
    ret c
    ld hl,(ld_p1031_requested)
    ld de,8192
    or a
    sbc hl,de
    jp nz,p1031_fail
    xor a
    ret

p1031_bad_odd:
    ld hl,p1031_sodd
    ld b,1
    call ld_p1031_heap_parse
    jp p1031_expect_format
p1031_bad_neg:
    ld hl,p1031_sneg
    ld b,2
    call ld_p1031_heap_parse
    jp p1031_expect_format
p1031_bad_text:
    ld hl,p1031_sbad
    ld b,3
    call ld_p1031_heap_parse
    jp p1031_expect_format
p1031_bad_high:
    ld hl,p1031_shigh
    ld b,4
    call ld_p1031_heap_parse
    jp p1031_expect_format

p1031_overflow:
    ld hl,30000
    ld de,1000
    ld bc,2000
    call ld_p1031_place
    ret nc
    cp E_NOSPC
    jp nz,p1031_fail
    scf
    ret

p1031_expect_format:
    ret nc
    cp E_FORMAT
    jp nz,p1031_fail
    scf
    ret

fixture_end:
    SAVEBIN "p1031-main.bin",fixture,fixture_end-fixture
""", encoding="utf-8", newline="\n")
    result = run_command([assembler, "--nologo", "--sym=p1031-heap.sym", fixture.name], cwd=build, timeout_seconds=30)
    require(not result.timed_out and result.exit_code == 0, f"P10.31 assemble: {result.stderr or result.stdout}")
    main = (build / "p1031-main.bin").read_bytes()
    names = ("p1031_default_normal","p1031_default_nostart","p1031_place_1024","p1031_parse0","p1031_parse2","p1031_parse1024","p1031_parse8192","p1031_bad_odd","p1031_bad_neg","p1031_bad_text","p1031_bad_high","p1031_overflow")
    syms = phase3_open_descriptions._symbols(build / "p1031-heap.sym", names)
    if action == "test":
        def patch(ram):
            ram[0xC000-0x4000:0xC000-0x4000+len(main)] = main
        for name in ("p1031_default_normal","p1031_default_nostart","p1031_place_1024","p1031_parse0","p1031_parse2","p1031_parse1024","p1031_parse8192"):
            code = b"\xF3" + phase1._ld_sp(0xBFC0) + phase1._call(syms[name]) + phase1._jp_c(FAIL_PC) + phase1._jp(PASS_PC)
            run_sna(root, code, patch=patch)
        for name in ("p1031_bad_odd","p1031_bad_neg","p1031_bad_text","p1031_bad_high","p1031_overflow"):
            code = b"\xF3" + phase1._ld_sp(0xBFC0) + phase1._call(syms[name]) + b"\xD2" + phase1._word(FAIL_PC) + phase1._jp(PASS_PC)
            run_sna(root, code, patch=patch)
        assertions += [
            {"name":"fuse-normal-default-1024","passed":True},
            {"name":"fuse-nostart-default-0","passed":True},
            {"name":"fuse-explicit-0-2-1024-8192","passed":True},
            {"name":"fuse-odd-negative-nonnumeric-high-rejected","passed":True},
            {"name":"fuse-combined-allocation-overflow-rejected","passed":True},
        ]
    hashes = {
        "tools/ld.asm": sha256_file(root / "tools/ld.asm"),
        "v1/build/p1031-main.bin": sha256_file(build / "p1031-main.bin"),
        "v1/tools-host/test-driver/phase10_step_31.py": sha256_file(root / "v1/tools-host/test-driver/phase10_step_31.py"),
        "v1/dist/certification/P10.30.build.json": sha256_file(root / "v1/dist/certification/P10.30.build.json"),
        "v1/dist/certification/P10.30.test.json": sha256_file(root / "v1/dist/certification/P10.30.test.json"),
    }
    return [result], hashes, assertions
