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


# P10.19 exact-candidate marker.
class P1019Error(DriverError):
    pass


def require(ok, msg):
    if not ok:
        raise P1019Error(msg)


def dispatch(root, action, step, *, sha256_file, run_command, require_project_tool):
    if step != "P10.19":
        raise DriverError(step)

    source = (root / "tools/as.asm").read_text(encoding="utf-8")
    assertions = [
        {"name":"exact-one-input-gate","passed":"cp 1" in source and "as_p1019_names:" in source},
        {"name":"explicit-asm-type-gate","passed":"cp OBJ_ASM" in source},
        {"name":"exact-lowercase-default-suffix","passed":"cp 'm'" in source and "cp 's'" in source and "cp 'a'" in source and "cp '.'" in source},
        {"name":"default-obj-suffix","passed":"as_p1019_obj_suffix: db '.obj',0" in source},
        {"name":"explicit-name-max-ten","passed":"AS_P1019_MAX_OUTPUT EQU 10" in source and "as_p1019_measure_output:" in source},
        {"name":"output-type-is-obj","passed":source.count("ld a,OBJ_OBJ") >= 2},
    ]
    require(all(a["passed"] for a in assertions), "P10.19 static name contract failure")

    assembler = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    fixture = build / "p1019-names.asm"
    fixture.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../../tools/as.asm"
    ORG $C000
fixture:
    EMIT_P10_AS_NAME_ROUTINES

p1019_hello: db 'hello.asm',0
p1019_HELLO: db 'HELLO.asm',0
p1019_upper_ext: db 'HELLO.ASM',0
p1019_missing: db 'hello',0
p1019_long: db '1234567.asm',0
p1019_explicit: db 'MiX.OBJ',0
p1019_too_long_out: db '12345678901',0
p1019_expect_hello: db 'hello.obj',0
p1019_expect_HELLO: db 'HELLO.obj',0
p1019_expect_explicit: db 'MiX.OBJ',0
p1019_out: defs 16,$CC

; HL actual, DE expected. Carry clear only on exact NUL-terminated match.
p1019_equal:
    ld a,(de)
    cp (hl)
    jr nz,p1019_equal_bad
    or a
    ret z
    inc hl
    inc de
    jr p1019_equal
p1019_equal_bad:
    scf
    ret

p1019_default_test:
    ld c,1
    ld a,OBJ_ASM
    ld hl,p1019_hello
    ld de,0
    ld ix,p1019_out
    call as_p1019_names
    ret c
    cp OBJ_OBJ
    jr nz,p1019_equal_bad
    ld hl,p1019_out
    ld de,p1019_expect_hello
    jp p1019_equal

p1019_case_test:
    ld c,1
    ld a,OBJ_ASM
    ld hl,p1019_HELLO
    ld de,0
    ld ix,p1019_out
    call as_p1019_names
    ret c
    cp OBJ_OBJ
    jr nz,p1019_equal_bad
    ld hl,p1019_out
    ld de,p1019_expect_HELLO
    jp p1019_equal

p1019_explicit_test:
    ld c,1
    ld a,OBJ_ASM
    ld hl,p1019_missing
    ld de,p1019_explicit
    ld ix,p1019_out
    call as_p1019_names
    ret c
    cp OBJ_OBJ
    jr nz,p1019_equal_bad
    ld hl,p1019_out
    ld de,p1019_expect_explicit
    jp p1019_equal

p1019_bad_upper:
    ld c,1
    ld a,OBJ_ASM
    ld hl,p1019_upper_ext
    ld de,0
    ld ix,p1019_out
    jp as_p1019_names

p1019_bad_missing:
    ld c,1
    ld a,OBJ_ASM
    ld hl,p1019_missing
    ld de,0
    ld ix,p1019_out
    jp as_p1019_names

p1019_bad_long_default:
    ld c,1
    ld a,OBJ_ASM
    ld hl,p1019_long
    ld de,0
    ld ix,p1019_out
    jp as_p1019_names

p1019_bad_wrong_type:
    ld c,1
    ld a,OBJ_TXT
    ld hl,p1019_hello
    ld de,0
    ld ix,p1019_out
    jp as_p1019_names

p1019_bad_two_inputs:
    ld c,2
    ld a,OBJ_ASM
    ld hl,p1019_hello
    ld de,0
    ld ix,p1019_out
    jp as_p1019_names

p1019_bad_explicit_long:
    ld c,1
    ld a,OBJ_ASM
    ld hl,p1019_hello
    ld de,p1019_too_long_out
    ld ix,p1019_out
    jp as_p1019_names

fixture_end:
    SAVEBIN "p1019-names.bin",fixture,fixture_end-fixture
""", encoding="utf-8", newline="\n")

    result = run_command([assembler, "--nologo", "--sym=p1019-names.sym", fixture.name], cwd=build, timeout_seconds=30)
    require(not result.timed_out and result.exit_code == 0, f"P10.19 assemble: {result.stderr or result.stdout}")

    if action == "test":
        names = (
            "p1019_default_test","p1019_case_test","p1019_explicit_test",
            "p1019_bad_upper","p1019_bad_missing","p1019_bad_long_default",
            "p1019_bad_wrong_type","p1019_bad_two_inputs","p1019_bad_explicit_long",
        )
        syms = phase3_open_descriptions._symbols(build / "p1019-names.sym", names)
        image = (build / "p1019-names.bin").read_bytes()

        def patch(ram):
            ram[0xC000-0x4000:0xC000-0x4000+len(image)] = image

        for name in ("p1019_default_test","p1019_case_test","p1019_explicit_test"):
            code = b"\xF3" + phase1._ld_sp(0xBFC0) + phase1._call(syms[name]) + phase1._jp_c(FAIL_PC) + phase1._jp(PASS_PC)
            run_sna(root, code, patch=patch)

        for name in (
            "p1019_bad_upper","p1019_bad_missing","p1019_bad_long_default",
            "p1019_bad_wrong_type","p1019_bad_two_inputs","p1019_bad_explicit_long",
        ):
            code = b"\xF3" + phase1._ld_sp(0xBFC0) + phase1._call(syms[name]) + b"\xD2" + phase1._word(FAIL_PC) + phase1._jp(PASS_PC)
            run_sna(root, code, patch=patch)

        assertions += [
            {"name":"fuse-hello-default-to-hello-obj","passed":True},
            {"name":"fuse-case-distinct-default-name","passed":True},
            {"name":"fuse-explicit-output-exact","passed":True},
            {"name":"fuse-uppercase-extension-rejected","passed":True},
            {"name":"fuse-missing-extension-rejected","passed":True},
            {"name":"fuse-derived-over-ten-rejected","passed":True},
            {"name":"fuse-wrong-object-type-rejected","passed":True},
            {"name":"fuse-input-count-not-one-rejected","passed":True},
            {"name":"fuse-explicit-over-ten-rejected","passed":True},
        ]

    hashes = {
        "tools/as.asm": sha256_file(root / "tools/as.asm"),
        "v1/include/zx48ux.inc": sha256_file(root / "v1/include/zx48ux.inc"),
        "v1/build/p1019-names.bin": sha256_file(build / "p1019-names.bin"),
        "v1/tools-host/test-driver/phase10_step_19.py": sha256_file(root / "v1/tools-host/test-driver/phase10_step_19.py"),
        "v1/dist/certification/P10.18.build.json": sha256_file(root / "v1/dist/certification/P10.18.build.json"),
        "v1/dist/certification/P10.18.test.json": sha256_file(root / "v1/dist/certification/P10.18.test.json"),
    }
    return [result], hashes, assertions
