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


class P1030Error(DriverError):
    pass


def require(ok, msg):
    if not ok:
        raise P1030Error(msg)


def dispatch(root, action, step, *, sha256_file, run_command, require_project_tool):
    if step != "P10.30":
        raise DriverError(step)

    source = (root / "tools/ld.asm").read_text(encoding="utf-8")
    assertions = [
        {"name":"stack-default-512","passed":"LD_P1030_STACK_DEFAULT EQU 512" in source},
        {"name":"stack-min-64","passed":"LD_P1030_STACK_MIN     EQU 64" in source},
        {"name":"stack-max-4096","passed":"LD_P1030_STACK_MAX     EQU 4096" in source},
        {"name":"stack-even-only","passed":"bit 0,l" in source and "ld_p1030_stack_set:" in source},
        {"name":"mex1-fast-stack-value","passed":"ld_p1030_min_fast_stack:" in source},
    ]
    require(all(a["passed"] for a in assertions), "P10.30 static stack-option contract failure")

    assembler = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    fixture = build / "p1030-stack.asm"
    fixture.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../../tools/ld.asm"
    ORG $C000
fixture:
    EMIT_P10_LD_STACK_OPTION_ROUTINES

p1030_fail:
    ld a,E_FORMAT
    scf
    ret

p1030_default:
    call ld_p1030_stack_default
    ret c
    ld hl,(ld_p1030_min_fast_stack)
    ld de,512
    or a
    sbc hl,de
    jp nz,p1030_fail
    xor a
    ret

p1030_min:
    ld hl,64
    call ld_p1030_stack_set
    ret c
    ld hl,(ld_p1030_min_fast_stack)
    ld de,64
    or a
    sbc hl,de
    jp nz,p1030_fail
    xor a
    ret

p1030_mid:
    ld hl,512
    call ld_p1030_stack_set
    ret c
    ld hl,(ld_p1030_min_fast_stack)
    ld de,512
    or a
    sbc hl,de
    jp nz,p1030_fail
    xor a
    ret

p1030_max:
    ld hl,4096
    call ld_p1030_stack_set
    ret c
    ld hl,(ld_p1030_min_fast_stack)
    ld de,4096
    or a
    sbc hl,de
    jp nz,p1030_fail
    xor a
    ret

p1030_odd:
    ld hl,65
    call ld_p1030_stack_set
    jp p1030_expect_format

p1030_low:
    ld hl,63
    call ld_p1030_stack_set
    jp p1030_expect_format

p1030_high:
    ld hl,4097
    call ld_p1030_stack_set
    jp p1030_expect_format

p1030_expect_format:
    ret nc
    cp E_FORMAT
    jp nz,p1030_fail
    scf
    ret

fixture_end:
    SAVEBIN "p1030-main.bin",fixture,fixture_end-fixture
""", encoding="utf-8", newline="\n")

    result = run_command([assembler, "--nologo", "--sym=p1030-stack.sym", fixture.name], cwd=build, timeout_seconds=30)
    require(not result.timed_out and result.exit_code == 0, f"P10.30 assemble: {result.stderr or result.stdout}")
    main = (build / "p1030-main.bin").read_bytes()
    names = ("p1030_default","p1030_min","p1030_mid","p1030_max","p1030_odd","p1030_low","p1030_high")
    syms = phase3_open_descriptions._symbols(build / "p1030-stack.sym", names)

    if action == "test":
        def patch(ram):
            ram[0xC000-0x4000:0xC000-0x4000+len(main)] = main
        for name in ("p1030_default","p1030_min","p1030_mid","p1030_max"):
            code = b"\xF3" + phase1._ld_sp(0xBFC0) + phase1._call(syms[name]) + phase1._jp_c(FAIL_PC) + phase1._jp(PASS_PC)
            run_sna(root, code, patch=patch)
        for name in ("p1030_odd","p1030_low","p1030_high"):
            code = b"\xF3" + phase1._ld_sp(0xBFC0) + phase1._call(syms[name]) + b"\xD2" + phase1._word(FAIL_PC) + phase1._jp(PASS_PC)
            run_sna(root, code, patch=patch)
        assertions += [
            {"name":"fuse-default-stack-512","passed":True},
            {"name":"fuse-boundary-stack-64","passed":True},
            {"name":"fuse-boundary-stack-4096","passed":True},
            {"name":"fuse-odd-stack-rejected","passed":True},
            {"name":"fuse-63-rejected","passed":True},
            {"name":"fuse-4097-rejected","passed":True},
        ]

    hashes = {
        "tools/ld.asm": sha256_file(root / "tools/ld.asm"),
        "v1/build/p1030-main.bin": sha256_file(build / "p1030-main.bin"),
        "v1/tools-host/test-driver/phase10_step_30.py": sha256_file(root / "v1/tools-host/test-driver/phase10_step_30.py"),
        "v1/dist/certification/P10.29.build.json": sha256_file(root / "v1/dist/certification/P10.29.build.json"),
        "v1/dist/certification/P10.29.test.json": sha256_file(root / "v1/dist/certification/P10.29.test.json"),
    }
    return [result], hashes, assertions
