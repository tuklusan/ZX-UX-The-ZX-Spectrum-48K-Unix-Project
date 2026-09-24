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


class P1023Error(DriverError):
    pass


def require(ok, msg):
    if not ok:
        raise P1023Error(msg)


def dispatch(root, action, step, *, sha256_file, run_command, require_project_tool):
    if step != "P10.23":
        raise DriverError(step)

    source = (root / "tools/ld.asm").read_text(encoding="utf-8")
    assertions = [
        {"name":"fixed-point-loop-native","passed":"ld_p1023_fixed_point:" in source and "jp nz,ld_p1023_fixed_point" in source},
        {"name":"frozen-member-order-native","passed":"ld_p1023_member_order:   db 1,2,3" in source and "ld_p1023_validate_order:" in source},
        {"name":"transitive-puts-write-dependency","passed":"set 0,a                  ; puts imports write" in source},
        {"name":"reserved-heap-symbols-satisfiable","passed":"LD_P1023_NEED_HEAP_START" in source and "LD_P1023_NEED_HEAP_END" in source},
        {"name":"nonheap-unresolved-hard-error","passed":"ld_p1023_unresolved:" in source and "ld a,E_NOENT" in source},
    ]
    require(all(a["passed"] for a in assertions), "P10.23 static fixed-point contract failure")

    assembler = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    fixture = build / "p1023-select.asm"
    fixture.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../../tools/ld.asm"
    ORG $C000
fixture:
    EMIT_P10_LD_ARCHIVE_SELECT_ROUTINES

p1023_fail:
    ld a,E_FORMAT
    scf
    ret

p1023_good:
    ld a,LD_P1023_NEED_PUTS|LD_P1023_NEED_EXIT
    call ld_p1023_select
    ret c
    ld a,(ld_p1023_selected_count)
    cp 3
    jp nz,p1023_fail
    ld a,(ld_p1023_selected_order+0)
    cp 2
    jp nz,p1023_fail
    ld a,(ld_p1023_selected_order+1)
    cp 3
    jp nz,p1023_fail
    ld a,(ld_p1023_selected_order+2)
    cp 1
    jp nz,p1023_fail
    ld a,(ld_p1023_need)
    or a
    jp nz,p1023_fail
    xor a
    ret

p1023_repeat:
    call p1023_good
    ret c
    jp p1023_good

p1023_heap:
    ld a,LD_P1023_NEED_HEAP_START|LD_P1023_NEED_HEAP_END
    call ld_p1023_select
    ret c
    ld a,(ld_p1023_selected_count)
    or a
    jp nz,p1023_fail
    ld a,(ld_p1023_need)
    or a
    jp nz,p1023_fail
    xor a
    ret

p1023_single_pass_negative:
    ld a,LD_P1023_NEED_PUTS
    call ld_p1023_select_one_pass
    ret c
    ld a,(ld_p1023_selected_count)
    cp 1
    jp nz,p1023_fail
    ld a,(ld_p1023_selected_order)
    cp 2
    jp nz,p1023_fail
    ld a,(ld_p1023_need)
    cp LD_P1023_NEED_WRITE
    jp nz,p1023_fail
    xor a
    ret

p1023_unresolved:
    ld a,LD_P1023_NEED_OTHER
    call ld_p1023_select
    ret nc
    cp E_NOENT
    jp nz,p1023_fail
    scf
    ret

p1023_bad_order:
    ld a,2
    ld (ld_p1023_member_order),a
    ld a,LD_P1023_NEED_PUTS
    call ld_p1023_select
    push af
    ld a,1
    ld (ld_p1023_member_order),a
    pop af
    ret nc
    cp E_FORMAT
    jp nz,p1023_fail
    scf
    ret

fixture_end:
    SAVEBIN "p1023-main.bin",fixture,fixture_end-fixture
""", encoding="utf-8", newline="\n")

    result = run_command([assembler, "--nologo", "--sym=p1023-select.sym", fixture.name], cwd=build, timeout_seconds=30)
    require(not result.timed_out and result.exit_code == 0, f"P10.23 assemble: {result.stderr or result.stdout}")
    main = (build / "p1023-main.bin").read_bytes()
    names = ("p1023_good","p1023_repeat","p1023_heap","p1023_single_pass_negative","p1023_unresolved","p1023_bad_order")
    syms = phase3_open_descriptions._symbols(build / "p1023-select.sym", names)

    if action == "test":
        def patch(ram):
            ram[0xC000-0x4000:0xC000-0x4000+len(main)] = main

        for name in ("p1023_good","p1023_repeat","p1023_heap","p1023_single_pass_negative"):
            code = b"\xF3" + phase1._ld_sp(0xBFC0) + phase1._call(syms[name]) + phase1._jp_c(FAIL_PC) + phase1._jp(PASS_PC)
            run_sna(root, code, patch=patch)
        for name in ("p1023_unresolved","p1023_bad_order"):
            code = b"\xF3" + phase1._ld_sp(0xBFC0) + phase1._call(syms[name]) + b"\xD2" + phase1._word(FAIL_PC) + phase1._jp(PASS_PC)
            run_sna(root, code, patch=patch)
        assertions += [
            {"name":"fuse-transitive-fixed-point-order-2-3-1","passed":True},
            {"name":"fuse-repeat-link-deterministic","passed":True},
            {"name":"fuse-reserved-heap-only-needs-no-member","passed":True},
            {"name":"fuse-single-pass-proven-insufficient","passed":True},
            {"name":"fuse-unresolved-nonheap-global-rejected","passed":True},
            {"name":"fuse-altered-member-order-rejected","passed":True},
        ]

    hashes = {
        "tools/ld.asm": sha256_file(root / "tools/ld.asm"),
        "v1/src/libc48/crt0.asm": sha256_file(root / "v1/src/libc48/crt0.asm"),
        "v1/src/libc48/runtime_archive.asm": sha256_file(root / "v1/src/libc48/runtime_archive.asm"),
        "v1/build/p1023-main.bin": sha256_file(build / "p1023-main.bin"),
        "v1/tools-host/test-driver/phase10_step_23.py": sha256_file(root / "v1/tools-host/test-driver/phase10_step_23.py"),
        "v1/dist/certification/P10.22.build.json": sha256_file(root / "v1/dist/certification/P10.22.build.json"),
        "v1/dist/certification/P10.22.test.json": sha256_file(root / "v1/dist/certification/P10.22.test.json"),
    }
    return [result], hashes, assertions
