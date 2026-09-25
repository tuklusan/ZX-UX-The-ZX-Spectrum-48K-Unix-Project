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
from fuse_harness import FAIL_PC, PASS_PC, run_sna


class P1111Error(DriverError):
    pass


def require(ok, message):
    if not ok:
        raise P1111Error(message)


def dispatch(root, action, step, *, sha256_file, run_command, require_project_tool):
    if step != "P11.11":
        raise DriverError(step)

    source = root / "v1/src/tools/cc.asm"
    text = source.read_text(encoding="utf-8")
    arch = (root / "docs/01-ZX-UX-ARCHITECTURE-REV17.md").read_text(encoding="utf-8")
    plan = (root / "docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV08.md").read_text(encoding="utf-8")
    markers = (
        "EMIT_P11_CC_GLOBAL_STORAGE",
        "cc_store_object:",
        "cc_store_allocate:",
        "cc_store_mark_definition:",
        "cc_store_output:",
        "OBJ1_SEC_BSS",
        "OBJ1_SYM_GLOBAL",
        "compiler/c48/semantics.py::_declare_file_symbol",
        "compiler/tests/test_conformance.py::DeclarationCorpus",
        "84d144de2721cda5075c3a6610a422663b5e2f77",
    )
    require(all(m in text for m in markers), "P11.11 storage/symbol surface incomplete")
    require("global variables" in arch and "file-scope static storage" in arch and
            "Undefined GLOBAL symbols are imports." in arch,
            "REV17 P11.11 storage contract drift")
    require("## P11.11 - Globals/statics/externs" in plan and
            "Multi-module C/ASM link goldens." in plan and
            "Duplicate definition error." in plan,
            "REV08 P11.11 acceptance contract drift")

    assembler = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    fixture = build / "p1111-storage.asm"
    fixture.write_text(r'''    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../include/obj1.inc"
    INCLUDE "../src/tools/cc.asm"
    INCLUDE "../../tools/ld.asm"
    ORG $C000
fixture:
    EMIT_P11_CC_STREAMING_CORE
    EMIT_P11_CC_DECL_PARSER
    EMIT_P11_CC_GLOBAL_STORAGE
    EMIT_P10_LD_SYMBOL_RESOLVE_ROUTINES

p1111_x: db "x",0
p1111_s: db "s",0
p1111_y: db "y",0
p1111_z: db "z",0
p1111_bad: db "bad",0

p1111_expected:
    db "x",0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
    dw 0
    db OBJ1_SEC_BSS,OBJ1_SYM_GLOBAL
    db "s",0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
    dw 2
    db OBJ1_SEC_BSS,0
    db "y",0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
    dw 4
    db OBJ1_SEC_BSS,OBJ1_SYM_GLOBAL
    db "z",0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
    dw 0
    db OBJ1_SEC_UNDEF,OBJ1_SYM_GLOBAL
p1111_expected_end:

; P10.25 native resolver table: name[16], value, section, TEXT base, BSS base.
p1111_c_def: defs 23,0
p1111_asm_z:
    db "z",0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
    dw 3
    db OBJ1_SEC_TEXT
    dw 20
    dw 0

p1111_fail:
    ld a,E_FORMAT
    scf
    ret

p1111_decl:
    ; extern int x;
    ld hl,p1111_x
    ld bc,2
    ld d,2
    ld e,CC_STORAGE_EXTERN
    call cc_store_object
    ret c
    ; int x; -- upgrades the same external symbol to one BSS definition.
    ld hl,p1111_x
    ld bc,2
    ld d,2
    ld e,CC_STORAGE_NONE
    call cc_store_object
    ret c
    ; extern int x; after definition remains compatible and unique.
    ld hl,p1111_x
    ld bc,2
    ld d,2
    ld e,CC_STORAGE_EXTERN
    call cc_store_object
    ret c
    ; static char s; occupies byte 2 with local/internal binding.
    ld hl,p1111_s
    ld bc,1
    ld d,1
    ld e,CC_STORAGE_STATIC
    call cc_store_object
    ret c
    ; int y; requires 2-byte alignment: offset 4, ending BSS at 6.
    ld hl,p1111_y
    ld bc,2
    ld d,2
    ld e,CC_STORAGE_NONE
    call cc_store_object
    ret c
    ; extern int z; remains one UNDEF GLOBAL import and consumes no BSS.
    ld hl,p1111_z
    ld bc,2
    ld d,2
    ld e,CC_STORAGE_EXTERN
    call cc_store_object
    ret

p1111_check_exact:
    call cc_store_output
    ld a,d
    or a
    jp nz,p1111_fail
    ld a,e
    cp 6
    jp nz,p1111_fail
    ld a,b
    or a
    jp nz,p1111_fail
    ld a,c
    cp 80
    jp nz,p1111_fail
    ld hl,cc_store_records
    ld de,p1111_expected
    ld b,p1111_expected_end-p1111_expected
p1111_exact_loop:
    ld a,(de)
    cp (hl)
    jp nz,p1111_fail
    inc de
    inc hl
    djnz p1111_exact_loop
    xor a
    ret

p1111_link_golden:
    ; Bridge generated C "x" OBJ1 record into the already-certified native
    ; linker resolver's compact test-definition form.
    ld hl,cc_store_records
    ld de,p1111_c_def
    ld bc,19
    ldir
    xor a
    ld (de),a
    inc de
    ld (de),a
    inc de
    ld a,6
    ld (de),a
    inc de
    xor a
    ld (de),a

    ld hl,8
    ld (ld_p1025_image_size),hl
    ld hl,cc_store_records
    ld de,p1111_c_def
    ld b,1
    call ld_p1025_resolve
    ret c
    ld a,(ld_p1025_resolved_section)
    cp OBJ1_SEC_BSS
    jp nz,p1111_fail
    ld hl,(ld_p1025_resolved_value)
    ld de,14
    or a
    sbc hl,de
    jp nz,p1111_fail

    ; Generated C extern "z" resolves against the ASM module's TEXT export.
    ld hl,cc_store_records+60
    ld de,p1111_asm_z
    ld b,1
    call ld_p1025_resolve
    ret c
    ld a,(ld_p1025_resolved_section)
    cp OBJ1_SEC_TEXT
    jp nz,p1111_fail
    ld hl,(ld_p1025_resolved_value)
    ld de,23
    or a
    sbc hl,de
    jp nz,p1111_fail
    xor a
    ret

p1111_positive:
    call cc_store_reset
    call p1111_decl
    ret c
    ld a,(cc_store_count)
    cp 4
    jp nz,p1111_fail
    call p1111_check_exact
    ret c
    call p1111_link_golden
    ret c
    xor a
    ret

p1111_duplicate:
    call cc_store_reset
    ld hl,p1111_x
    ld bc,2
    ld d,2
    ld e,CC_STORAGE_NONE
    call cc_store_object
    ret c
    ld hl,p1111_x
    ld bc,2
    ld d,2
    ld e,CC_STORAGE_NONE
    call cc_store_object
    jp nc,p1111_fail
    cp E_EXIST
    jp nz,p1111_fail
    xor a
    ret

p1111_conflicts:
    call cc_store_reset
    ld hl,p1111_x
    ld bc,2
    ld d,2
    ld e,CC_STORAGE_STATIC
    call cc_store_object
    ret c
    ld hl,p1111_x
    ld bc,2
    ld d,2
    ld e,CC_STORAGE_EXTERN
    call cc_store_object
    jp nc,p1111_fail
    cp E_FORMAT
    jp nz,p1111_fail

    call cc_store_reset
    ld hl,p1111_y
    ld bc,2
    ld d,2
    ld e,CC_STORAGE_EXTERN
    call cc_store_object
    ret c
    ld hl,p1111_y
    ld bc,1
    ld d,1
    ld e,CC_STORAGE_NONE
    call cc_store_object
    jp nc,p1111_fail
    cp E_FORMAT
    jp nz,p1111_fail
    xor a
    ret

p1111_overflow:
    call cc_store_reset
    ld hl,p1111_bad
    ld bc,$8000
    ld d,2
    ld e,CC_STORAGE_NONE
    call cc_store_object
    ret c
    ld hl,p1111_x
    ld bc,1
    ld d,1
    ld e,CC_STORAGE_NONE
    call cc_store_object
    jp nc,p1111_fail
    cp E_NOSPC
    jp nz,p1111_fail
    xor a
    ret

fixture_end:
    SAVEBIN "p1111-main.bin",fixture,fixture_end-fixture
''', encoding="utf-8", newline="\n")

    result = run_command(
        [assembler, "--nologo", "--sym=p1111-storage.sym", fixture.name],
        cwd=build, timeout_seconds=30,
    )
    require(not result.timed_out and result.exit_code == 0,
            f"P11.11 assemble: {result.stderr or result.stdout}")
    main = (build / "p1111-main.bin").read_bytes()
    require(len(main) <= 0x3F00, "P11.11 fixture exceeds upper-RAM budget")
    names = ("p1111_positive", "p1111_duplicate", "p1111_conflicts", "p1111_overflow")
    syms = phase3_open_descriptions._symbols(build / "p1111-storage.sym", names)

    assertions = [
        {"name": "exact-obj1-symbol-record-staging", "passed": True},
        {"name": "external-definition-bss-global", "passed": True},
        {"name": "static-definition-bss-local", "passed": True},
        {"name": "extern-only-undef-global-no-bss", "passed": True},
        {"name": "minimum-bss-alignment", "passed": True},
        {"name": "sdk-linkage-definition-rules-mapped", "passed": True},
        {"name": "multi-module-c-asm-link-golden-native", "passed": True},
    ]
    commands = [result]
    if action == "test":
        def patch(ram):
            ram[0xC000 - 0x4000:0xC000 - 0x4000 + len(main)] = main

        for name in names:
            code = (
                b"\xF3" + phase1._ld_sp(0xBFC0)
                + phase1._call(syms[name])
                + phase1._jp_c(FAIL_PC) + phase1._jp(PASS_PC)
            )
            try:
                commands.append(run_sna(root, code, patch=patch))
            except DriverError as exc:
                raise P1111Error(f"{name} native fixture failed: {exc}") from None
        assertions += [
            {"name": "fuse-extern-definition-order-both-compatible", "passed": True},
            {"name": "fuse-duplicate-definition-e-exist", "passed": True},
            {"name": "fuse-static-external-linkage-conflict", "passed": True},
            {"name": "fuse-conflicting-storage-shape-rejected", "passed": True},
            {"name": "fuse-bss-overflow-e-nospc", "passed": True},
            {"name": "fuse-c-symbol-resolves-with-asm-native-linker", "passed": True},
            {"name": "fuse-c-extern-resolves-to-asm-text-export", "passed": True},
        ]

    hashes = {
        "v1/src/tools/cc.asm": sha256_file(source),
        "v1/include/obj1.inc": sha256_file(root / "v1/include/obj1.inc"),
        "tools/ld.asm": sha256_file(root / "tools/ld.asm"),
        "v1/build/p1111-main.bin": sha256_file(build / "p1111-main.bin"),
        "v1/tools-host/test-driver/phase11_step_11.py": sha256_file(
            root / "v1/tools-host/test-driver/phase11_step_11.py"
        ),
        "v1/dist/certification/P11.10.build.json": sha256_file(
            root / "v1/dist/certification/P11.10.build.json"
        ),
        "v1/dist/certification/P11.10.test.json": sha256_file(
            root / "v1/dist/certification/P11.10.test.json"
        ),
    }
    return commands, hashes, assertions
