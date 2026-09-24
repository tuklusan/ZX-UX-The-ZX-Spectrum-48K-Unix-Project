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


class P1025Error(DriverError):
    pass


def require(ok, msg):
    if not ok:
        raise P1025Error(msg)


def dispatch(root, action, step, *, sha256_file, run_command, require_project_tool):
    if step != "P10.25":
        raise DriverError(step)

    source = (root / "tools/ld.asm").read_text(encoding="utf-8")
    assertions = [
        {"name":"case-sensitive-name-compare","passed":"Case is significant." in source and "ld_p1025_name_equal:" in source},
        {"name":"text-formula","passed":"TEXT = module_text_base + OBJ1 value." in source},
        {"name":"bss-formula","passed":"BSS = image_size + module_bss_base + OBJ1 value." in source},
        {"name":"abs-formula","passed":"ABS = OBJ1 value." in source},
        {"name":"duplicate-global-hard-error","passed":"ld_p1025_duplicate:" in source},
        {"name":"unresolved-global-hard-error","passed":"ld_p1025_unresolved:" in source},
    ]
    require(all(a["passed"] for a in assertions), "P10.25 static symbol-resolution contract failure")

    assembler = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    fixture = build / "p1025-symbols.asm"
    fixture.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../../tools/ld.asm"
    ORG $C000
fixture:
    EMIT_P10_LD_SYMBOL_RESOLVE_ROUTINES

p1025_query_text: db "TextSym"
    defs 9,0
p1025_query_bss: db "BssSym"
    defs 10,0
p1025_query_abs: db "AbsSym"
    defs 10,0
p1025_query_case: db "textsym"
    defs 9,0

; name[16], OBJ1 value, section, module TEXT base, module BSS base.
p1025_defs:
    db "TextSym"
    defs 9,0
    dw 5
    db 1
    dw 8
    dw 0
    db "BssSym"
    defs 10,0
    dw 3
    db 2
    dw 0
    dw 6
    db "AbsSym"
    defs 10,0
    dw $BEEF
    db 3
    dw 0
    dw 0

p1025_dups:
    db "TextSym"
    defs 9,0
    dw 1
    db 1
    dw 0
    dw 0
    db "TextSym"
    defs 9,0
    dw 2
    db 1
    dw 4
    dw 0

p1025_fail:
    ld a,E_FORMAT
    scf
    ret

p1025_setup:
    ld hl,18
    ld (ld_p1025_image_size),hl
    ret

p1025_text:
    call p1025_setup
    ld hl,p1025_query_text
    ld de,p1025_defs
    ld b,3
    call ld_p1025_resolve
    ret c
    ld a,(ld_p1025_resolved_section)
    cp 1
    jp nz,p1025_fail
    ld hl,(ld_p1025_resolved_value)
    ld de,13
    or a
    sbc hl,de
    jp nz,p1025_fail
    xor a
    ret

p1025_bss:
    call p1025_setup
    ld hl,p1025_query_bss
    ld de,p1025_defs
    ld b,3
    call ld_p1025_resolve
    ret c
    ld a,(ld_p1025_resolved_section)
    cp 2
    jp nz,p1025_fail
    ld hl,(ld_p1025_resolved_value)
    ld de,27
    or a
    sbc hl,de
    jp nz,p1025_fail
    xor a
    ret

p1025_abs:
    call p1025_setup
    ld hl,p1025_query_abs
    ld de,p1025_defs
    ld b,3
    call ld_p1025_resolve
    ret c
    ld a,(ld_p1025_resolved_section)
    cp 3
    jp nz,p1025_fail
    ld hl,(ld_p1025_resolved_value)
    ld de,$BEEF
    or a
    sbc hl,de
    jp nz,p1025_fail
    xor a
    ret

p1025_case_miss:
    call p1025_setup
    ld hl,p1025_query_case
    ld de,p1025_defs
    ld b,3
    call ld_p1025_resolve
    ret nc
    cp E_NOENT
    jp nz,p1025_fail
    scf
    ret

p1025_duplicate:
    call p1025_setup
    ld hl,p1025_query_text
    ld de,p1025_dups
    ld b,2
    call ld_p1025_resolve
    ret nc
    cp E_FORMAT
    jp nz,p1025_fail
    scf
    ret

fixture_end:
    SAVEBIN "p1025-main.bin",fixture,fixture_end-fixture
""", encoding="utf-8", newline="\n")

    result = run_command([assembler, "--nologo", "--sym=p1025-symbols.sym", fixture.name], cwd=build, timeout_seconds=30)
    require(not result.timed_out and result.exit_code == 0, f"P10.25 assemble: {result.stderr or result.stdout}")
    main = (build / "p1025-main.bin").read_bytes()
    names = ("p1025_text","p1025_bss","p1025_abs","p1025_case_miss","p1025_duplicate")
    syms = phase3_open_descriptions._symbols(build / "p1025-symbols.sym", names)

    if action == "test":
        def patch(ram):
            ram[0xC000-0x4000:0xC000-0x4000+len(main)] = main
        for name in ("p1025_text","p1025_bss","p1025_abs"):
            code = b"\xF3" + phase1._ld_sp(0xBFC0) + phase1._call(syms[name]) + phase1._jp_c(FAIL_PC) + phase1._jp(PASS_PC)
            run_sna(root, code, patch=patch)
        for name in ("p1025_case_miss","p1025_duplicate"):
            code = b"\xF3" + phase1._ld_sp(0xBFC0) + phase1._call(syms[name]) + b"\xD2" + phase1._word(FAIL_PC) + phase1._jp(PASS_PC)
            run_sna(root, code, patch=patch)
        assertions += [
            {"name":"fuse-text-final-formula","passed":True},
            {"name":"fuse-bss-final-formula","passed":True},
            {"name":"fuse-abs-final-formula","passed":True},
            {"name":"fuse-case-mismatch-unresolved","passed":True},
            {"name":"fuse-duplicate-defined-global-rejected","passed":True},
        ]

    hashes = {
        "tools/ld.asm": sha256_file(root / "tools/ld.asm"),
        "v1/build/p1025-main.bin": sha256_file(build / "p1025-main.bin"),
        "v1/tools-host/test-driver/phase10_step_25.py": sha256_file(root / "v1/tools-host/test-driver/phase10_step_25.py"),
        "v1/dist/certification/P10.24.build.json": sha256_file(root / "v1/dist/certification/P10.24.build.json"),
        "v1/dist/certification/P10.24.test.json": sha256_file(root / "v1/dist/certification/P10.24.test.json"),
    }
    return [result], hashes, assertions
