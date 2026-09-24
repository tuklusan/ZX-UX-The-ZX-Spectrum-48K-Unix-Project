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


class P1027Error(DriverError):
    pass


def require(ok, msg):
    if not ok:
        raise P1027Error(msg)


def dispatch(root, action, step, *, sha256_file, run_command, require_project_tool):
    if step != "P10.27":
        raise DriverError(step)

    source = (root / "tools/ld.asm").read_text(encoding="utf-8")
    assertions = [
        {"name":"default-name-exact-start","passed":'db "_start",0,0,0,0,0,0,0,0,0,0' in source},
        {"name":"uses-case-sensitive-resolver","passed":"call ld_p1025_resolve" in source},
        {"name":"entry-must-be-text","passed":"ld a,(ld_p1025_resolved_section)" in source and "cp 1" in source},
        {"name":"resolved-entry-published","passed":"ld (ld_p1027_entry),hl" in source},
    ]
    require(all(a["passed"] for a in assertions), "P10.27 static entry contract failure")

    assembler = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    fixture = build / "p1027-entry.asm"
    fixture.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../../tools/ld.asm"
    ORG $C000
fixture:
    EMIT_P10_LD_SYMBOL_RESOLVE_ROUTINES
    EMIT_P10_LD_DEFAULT_ENTRY_ROUTINES

p1027_defs:
    db "_start"
    defs 10,0
    dw 3
    db 1
    dw 8
    dw 0
    db "helper"
    defs 10,0
    dw 1
    db 3
    dw 0
    dw 0

p1027_missing:
    db "helper"
    defs 10,0
    dw 1
    db 1
    dw 0
    dw 0

p1027_dup:
    db "_start"
    defs 10,0
    dw 1
    db 1
    dw 0
    dw 0
    db "_start"
    defs 10,0
    dw 2
    db 1
    dw 4
    dw 0

p1027_bss:
    db "_start"
    defs 10,0
    dw 0
    db 2
    dw 0
    dw 0

p1027_setup:
    ld hl,32
    ld (ld_p1025_image_size),hl
    ret

p1027_good:
    call p1027_setup
    ld de,p1027_defs
    ld b,2
    call ld_p1027_default_entry
    ret c
    ld hl,(ld_p1027_entry)
    ld de,11
    or a
    sbc hl,de
    jp nz,p1027_fail
    xor a
    ret

p1027_missing_case:
    call p1027_setup
    ld de,p1027_missing
    ld b,1
    call ld_p1027_default_entry
    ret nc
    cp E_NOENT
    jp nz,p1027_fail
    scf
    ret

p1027_duplicate_case:
    call p1027_setup
    ld de,p1027_dup
    ld b,2
    call ld_p1027_default_entry
    ret nc
    cp E_FORMAT
    jp nz,p1027_fail
    scf
    ret

p1027_nontext_case:
    call p1027_setup
    ld de,p1027_bss
    ld b,1
    call ld_p1027_default_entry
    ret nc
    cp E_FORMAT
    jp nz,p1027_fail
    scf
    ret

p1027_fail:
    ld a,E_FORMAT
    scf
    ret

fixture_end:
    SAVEBIN "p1027-main.bin",fixture,fixture_end-fixture
""", encoding="utf-8", newline="\n")

    result = run_command([assembler, "--nologo", "--sym=p1027-entry.sym", fixture.name], cwd=build, timeout_seconds=30)
    require(not result.timed_out and result.exit_code == 0, f"P10.27 assemble: {result.stderr or result.stdout}")
    main = (build / "p1027-main.bin").read_bytes()
    names = ("p1027_good","p1027_missing_case","p1027_duplicate_case","p1027_nontext_case")
    syms = phase3_open_descriptions._symbols(build / "p1027-entry.sym", names)

    if action == "test":
        def patch(ram):
            ram[0xC000-0x4000:0xC000-0x4000+len(main)] = main
        code = b"\xF3" + phase1._ld_sp(0xBFC0) + phase1._call(syms["p1027_good"]) + phase1._jp_c(FAIL_PC) + phase1._jp(PASS_PC)
        run_sna(root, code, patch=patch)
        for name in ("p1027_missing_case","p1027_duplicate_case","p1027_nontext_case"):
            code = b"\xF3" + phase1._ld_sp(0xBFC0) + phase1._call(syms[name]) + b"\xD2" + phase1._word(FAIL_PC) + phase1._jp(PASS_PC)
            run_sna(root, code, patch=patch)
        assertions += [
            {"name":"fuse-normal-start-entry-exact","passed":True},
            {"name":"fuse-missing-start-rejected","passed":True},
            {"name":"fuse-duplicate-start-rejected","passed":True},
            {"name":"fuse-nontext-start-rejected","passed":True},
        ]

    hashes = {
        "tools/ld.asm": sha256_file(root / "tools/ld.asm"),
        "v1/build/p1027-main.bin": sha256_file(build / "p1027-main.bin"),
        "v1/tools-host/test-driver/phase10_step_27.py": sha256_file(root / "v1/tools-host/test-driver/phase10_step_27.py"),
        "v1/dist/certification/P10.26.build.json": sha256_file(root / "v1/dist/certification/P10.26.build.json"),
        "v1/dist/certification/P10.26.test.json": sha256_file(root / "v1/dist/certification/P10.26.test.json"),
    }
    return [result], hashes, assertions
