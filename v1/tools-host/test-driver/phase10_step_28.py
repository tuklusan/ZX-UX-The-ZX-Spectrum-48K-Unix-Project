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


class P1028Error(DriverError):
    pass


def require(ok, msg):
    if not ok:
        raise P1028Error(msg)


def dispatch(root, action, step, *, sha256_file, run_command, require_project_tool):
    if step != "P10.28":
        raise DriverError(step)
    source = (root / "tools/ld.asm").read_text(encoding="utf-8")
    assertions = [
        {"name":"nostart-omits-crt0-prerequisite","passed":"ld_p1024_nostart:" in source},
        {"name":"explicit-e-mandatory","passed":"ld_p1028_nostart_entry:" in source and "jp z,ld_p1028_format" in source},
        {"name":"exact-case-resolver","passed":"call ld_p1025_resolve" in source},
        {"name":"entry-must-be-text","passed":"ld a,(ld_p1025_resolved_section)" in source and "cp 1" in source},
        {"name":"no-default-entry-state","passed":"There is deliberately no default under -nostart." in source},
    ]
    require(all(a["passed"] for a in assertions), "P10.28 static nostart entry contract failure")

    assembler = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    fixture = build / "p1028-nostart.asm"
    fixture.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../../tools/ld.asm"
    ORG $C000
fixture:
    EMIT_P10_LD_SYMBOL_RESOLVE_ROUTINES
    EMIT_P10_LD_NOSTART_ENTRY_ROUTINES

p1028_name: db "entry"
    defs 11,0
p1028_case: db "Entry"
    defs 11,0

p1028_defs:
    db "entry"
    defs 11,0
    dw 5
    db 1
    dw 12
    dw 0

p1028_dup:
    db "entry"
    defs 11,0
    dw 1
    db 1
    dw 0
    dw 0
    db "entry"
    defs 11,0
    dw 2
    db 1
    dw 4
    dw 0

p1028_abs:
    db "entry"
    defs 11,0
    dw 7
    db 3
    dw 0
    dw 0

p1028_setup:
    ld hl,32
    ld (ld_p1025_image_size),hl
    ret

p1028_good:
    call p1028_setup
    ld a,1
    ld hl,p1028_name
    ld de,p1028_defs
    ld b,1
    call ld_p1028_nostart_entry
    ret c
    ld hl,(ld_p1028_entry)
    ld de,17
    or a
    sbc hl,de
    jp nz,p1028_fail
    xor a
    ret

p1028_no_e:
    call p1028_setup
    xor a
    ld hl,p1028_name
    ld de,p1028_defs
    ld b,1
    call ld_p1028_nostart_entry
    jp p1028_expect_format

p1028_case_miss:
    call p1028_setup
    ld a,1
    ld hl,p1028_case
    ld de,p1028_defs
    ld b,1
    call ld_p1028_nostart_entry
    ret nc
    cp E_NOENT
    jp nz,p1028_fail
    scf
    ret

p1028_dup_case:
    call p1028_setup
    ld a,1
    ld hl,p1028_name
    ld de,p1028_dup
    ld b,2
    call ld_p1028_nostart_entry
    jp p1028_expect_format

p1028_nontext:
    call p1028_setup
    ld a,1
    ld hl,p1028_name
    ld de,p1028_abs
    ld b,1
    call ld_p1028_nostart_entry
    jp p1028_expect_format

p1028_expect_format:
    ret nc
    cp E_FORMAT
    jp nz,p1028_fail
    scf
    ret
p1028_fail:
    ld a,E_FORMAT
    scf
    ret

fixture_end:
    SAVEBIN "p1028-main.bin",fixture,fixture_end-fixture
""", encoding="utf-8", newline="\n")
    result = run_command([assembler, "--nologo", "--sym=p1028-nostart.sym", fixture.name], cwd=build, timeout_seconds=30)
    require(not result.timed_out and result.exit_code == 0, f"P10.28 assemble: {result.stderr or result.stdout}")
    main = (build / "p1028-main.bin").read_bytes()
    names = ("p1028_good","p1028_no_e","p1028_case_miss","p1028_dup_case","p1028_nontext")
    syms = phase3_open_descriptions._symbols(build / "p1028-nostart.sym", names)
    if action == "test":
        def patch(ram):
            ram[0xC000-0x4000:0xC000-0x4000+len(main)] = main
        code = b"\xF3" + phase1._ld_sp(0xBFC0) + phase1._call(syms["p1028_good"]) + phase1._jp_c(FAIL_PC) + phase1._jp(PASS_PC)
        run_sna(root, code, patch=patch)
        for name in ("p1028_no_e","p1028_case_miss","p1028_dup_case","p1028_nontext"):
            code = b"\xF3" + phase1._ld_sp(0xBFC0) + phase1._call(syms[name]) + b"\xD2" + phase1._word(FAIL_PC) + phase1._jp(PASS_PC)
            run_sna(root, code, patch=patch)
        assertions += [
            {"name":"fuse-nostart-explicit-entry","passed":True},
            {"name":"fuse-nostart-without-e-rejected","passed":True},
            {"name":"fuse-nostart-case-mismatch-unresolved","passed":True},
            {"name":"fuse-nostart-duplicate-rejected","passed":True},
            {"name":"fuse-nostart-nontext-rejected","passed":True},
        ]
    hashes = {
        "tools/ld.asm": sha256_file(root / "tools/ld.asm"),
        "v1/build/p1028-main.bin": sha256_file(build / "p1028-main.bin"),
        "v1/tools-host/test-driver/phase10_step_28.py": sha256_file(root / "v1/tools-host/test-driver/phase10_step_28.py"),
        "v1/dist/certification/P10.27.build.json": sha256_file(root / "v1/dist/certification/P10.27.build.json"),
        "v1/dist/certification/P10.27.test.json": sha256_file(root / "v1/dist/certification/P10.27.test.json"),
    }
    return [result], hashes, assertions
