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


class P1029Error(DriverError):
    pass


def require(ok, msg):
    if not ok:
        raise P1029Error(msg)


def dispatch(root, action, step, *, sha256_file, run_command, require_project_tool):
    if step != "P10.29":
        raise DriverError(step)
    source = (root / "tools/ld.asm").read_text(encoding="utf-8")
    assertions = [
        {"name":"archive-reserved-start-survives","passed":"LD_P1023_NEED_HEAP_START EQU 8" in source},
        {"name":"archive-reserved-end-survives","passed":"LD_P1023_NEED_HEAP_END   EQU 16" in source},
        {"name":"reserved-names-exact","passed":'db "__heap_start",0,0,0,0' in source and 'db "__heap_end",0,0,0,0,0,0' in source},
        {"name":"user-definitions-rejected","passed":"ld_p1029_reject_reserved_defs:" in source and "ld_p1029_reserved:" in source},
        {"name":"assigned-after-layout","passed":"ld_p1029_assign_heap:" in source},
    ]
    require(all(a["passed"] for a in assertions), "P10.29 static heap-symbol contract failure")

    assembler = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    fixture = build / "p1029-heap-symbols.asm"
    fixture.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../../tools/ld.asm"
    ORG $C000
fixture:
    EMIT_P10_LD_HEAP_SYMBOL_ROUTINES

p1029_bad_start:
    db "__heap_start"
    defs 4,0
    dw 0
    db 1
    dw 0
    dw 0
p1029_bad_end:
    db "__heap_end"
    defs 6,0
    dw 0
    db 2
    dw 0
    dw 0
p1029_allowed_case:
    db "__Heap_start"
    defs 4,0
    dw 0
    db 1
    dw 0
    dw 0

p1029_assign:
    ld hl,18
    ld de,8
    ld bc,1024
    call ld_p1029_assign_heap
    ret c
    ld hl,(ld_p1029_heap_start)
    ld de,26
    or a
    sbc hl,de
    jp nz,p1029_fail
    ld hl,(ld_p1029_heap_end)
    ld de,1050
    or a
    sbc hl,de
    jp nz,p1029_fail
    xor a
    ret

p1029_allowed:
    ld de,p1029_allowed_case
    ld b,1
    jp ld_p1029_reject_reserved_defs

p1029_reject_start:
    ld de,p1029_bad_start
    ld b,1
    call ld_p1029_reject_reserved_defs
    jp p1029_expect_format

p1029_reject_end:
    ld de,p1029_bad_end
    ld b,1
    call ld_p1029_reject_reserved_defs
    jp p1029_expect_format

p1029_expect_format:
    ret nc
    cp E_FORMAT
    jp nz,p1029_fail
    scf
    ret
p1029_fail:
    ld a,E_FORMAT
    scf
    ret

fixture_end:
    SAVEBIN "p1029-main.bin",fixture,fixture_end-fixture
""", encoding="utf-8", newline="\n")
    result = run_command([assembler, "--nologo", "--sym=p1029-heap-symbols.sym", fixture.name], cwd=build, timeout_seconds=30)
    require(not result.timed_out and result.exit_code == 0, f"P10.29 assemble: {result.stderr or result.stdout}")
    main = (build / "p1029-main.bin").read_bytes()
    names = ("p1029_assign","p1029_allowed","p1029_reject_start","p1029_reject_end")
    syms = phase3_open_descriptions._symbols(build / "p1029-heap-symbols.sym", names)
    if action == "test":
        def patch(ram):
            ram[0xC000-0x4000:0xC000-0x4000+len(main)] = main
        for name in ("p1029_assign","p1029_allowed"):
            code = b"\xF3" + phase1._ld_sp(0xBFC0) + phase1._call(syms[name]) + phase1._jp_c(FAIL_PC) + phase1._jp(PASS_PC)
            run_sna(root, code, patch=patch)
        for name in ("p1029_reject_start","p1029_reject_end"):
            code = b"\xF3" + phase1._ld_sp(0xBFC0) + phase1._call(syms[name]) + b"\xD2" + phase1._word(FAIL_PC) + phase1._jp(PASS_PC)
            run_sna(root, code, patch=patch)
        assertions += [
            {"name":"fuse-heap-address-values","passed":True},
            {"name":"fuse-case-sensitive-near-name-allowed","passed":True},
            {"name":"fuse-user-heap-start-definition-rejected","passed":True},
            {"name":"fuse-user-heap-end-definition-rejected","passed":True},
        ]
    hashes = {
        "tools/ld.asm": sha256_file(root / "tools/ld.asm"),
        "v1/build/p1029-main.bin": sha256_file(build / "p1029-main.bin"),
        "v1/tools-host/test-driver/phase10_step_29.py": sha256_file(root / "v1/tools-host/test-driver/phase10_step_29.py"),
        "v1/dist/certification/P10.28.build.json": sha256_file(root / "v1/dist/certification/P10.28.build.json"),
        "v1/dist/certification/P10.28.test.json": sha256_file(root / "v1/dist/certification/P10.28.test.json"),
    }
    return [result], hashes, assertions
