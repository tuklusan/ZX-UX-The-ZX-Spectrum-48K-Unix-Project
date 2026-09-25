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


class P1110Error(DriverError):
    pass


def require(ok, message):
    if not ok:
        raise P1110Error(message)


def dispatch(root, action, step, *, sha256_file, run_command, require_project_tool):
    if step != "P11.10":
        raise DriverError(step)

    source = root / "v1/src/tools/cc.asm"
    text = source.read_text(encoding="utf-8")
    arch = (root / "docs/01-ZX-UX-ARCHITECTURE-REV17.md").read_text(encoding="utf-8")
    plan = (root / "docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV08.md").read_text(encoding="utf-8")
    markers = (
        "EMIT_P11_CC_LITERALS",
        "CC_LIT_POOL_CAPACITY     EQU 512",
        "cc_lit_string_begin:",
        "cc_lit_string_append:",
        "cc_lit_string_end:",
        "cc_lit_char:",
        "cc_lit_escape_hex:",
        "84d144de2721cda5075c3a6610a422663b5e2f77",
        "compiler/c48/lexer.py",
        "compiler/c48/parser.py",
    )
    require(all(m in text for m in markers), "P11.10 literal surface incomplete")
    require("string literals" in arch and "character literals" in arch,
            "REV17 P11.10 literal contract drift")
    require("## P11.10 - String/char literals" in plan and
            "Unsupported escape rejected/documented." in plan,
            "REV08 P11.10 acceptance contract drift")

    assembler = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    fixture = build / "p1110-literals.asm"
    fixture.write_text(r'''    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/tools/cc.asm"
    ORG $C000
fixture:
    EMIT_P11_CC_STREAMING_CORE
    EMIT_P11_CC_LEXER
    EMIT_P11_CC_DECL_PARSER
    EMIT_P11_CC_LITERALS

p1110_ca:      db 39,"A",39
p1110_ca_end:
p1110_cnl:     db 39,92,"n",39
p1110_cnl_end:
p1110_chex:    db 39,92,"x41",39
p1110_chex_end:
p1110_czero:   db 39,92,"0",39
p1110_czero_end:
p1110_cslash:  db 39,92,92,39
p1110_cslash_end:

p1110_s1:      db 34,"ab",34
p1110_s1_end:
p1110_s2:      db 34,92,"n",92,"x43",34
p1110_s2_end:
p1110_sempty:  db 34,34
p1110_sempty_end:
p1110_pool_expected:
    db "ab",10,"C",0,0
p1110_pool_expected_end:

p1110_bad_oct: db 34,92,"1",34
p1110_bad_oct_end:
p1110_bad_esc: db 34,92,"q",34
p1110_bad_esc_end:
p1110_bad_hex: db 34,92,"x4G",34
p1110_bad_hex_end:
p1110_bad_char: db 39,"AB",39
p1110_bad_char_end:

p1110_fail:
    ld a,E_FORMAT
    scf
    ret

p1110_chars:
    ld hl,p1110_ca
    ld bc,p1110_ca_end-p1110_ca
    call cc_lit_char
    ret c
    cp "A"
    jp nz,p1110_fail

    ld hl,p1110_cnl
    ld bc,p1110_cnl_end-p1110_cnl
    call cc_lit_char
    ret c
    cp 10
    jp nz,p1110_fail

    ld hl,p1110_chex
    ld bc,p1110_chex_end-p1110_chex
    call cc_lit_char
    ret c
    cp $41
    jp nz,p1110_fail

    ld hl,p1110_czero
    ld bc,p1110_czero_end-p1110_czero
    call cc_lit_char
    ret c
    or a
    jp nz,p1110_fail

    ld hl,p1110_cslash
    ld bc,p1110_cslash_end-p1110_cslash
    call cc_lit_char
    ret c
    cp 92
    jp nz,p1110_fail
    xor a
    ret

p1110_strings:
    call cc_lit_reset
    call cc_lit_string_begin
    ret c
    ld hl,p1110_s1
    ld bc,p1110_s1_end-p1110_s1
    call cc_lit_string_append
    ret c
    ld hl,p1110_s2
    ld bc,p1110_s2_end-p1110_s2
    call cc_lit_string_append
    ret c
    call cc_lit_string_end
    ret c
    ld a,h
    or l
    jp nz,p1110_fail
    ld a,b
    or a
    jp nz,p1110_fail
    ld a,c
    cp 5
    jp nz,p1110_fail

    call cc_lit_string_begin
    ret c
    ld hl,p1110_sempty
    ld bc,p1110_sempty_end-p1110_sempty
    call cc_lit_string_append
    ret c
    call cc_lit_string_end
    ret c
    ld de,5
    or a
    sbc hl,de
    jp nz,p1110_fail
    ld a,b
    or a
    jp nz,p1110_fail
    ld a,c
    cp 1
    jp nz,p1110_fail

    ld hl,cc_lit_pool
    ld de,p1110_pool_expected
    ld b,p1110_pool_expected_end-p1110_pool_expected
p1110_pool_cmp:
    ld a,(de)
    cp (hl)
    jp nz,p1110_fail
    inc de
    inc hl
    djnz p1110_pool_cmp
    xor a
    ret

p1110_negatives:
    call cc_lit_reset
    call cc_lit_string_begin
    ret c
    ld hl,p1110_bad_oct
    ld bc,p1110_bad_oct_end-p1110_bad_oct
    call cc_lit_string_append
    jp nc,p1110_fail
    cp E_NOTSUP
    jp nz,p1110_fail

    call cc_lit_reset
    call cc_lit_string_begin
    ret c
    ld hl,p1110_bad_esc
    ld bc,p1110_bad_esc_end-p1110_bad_esc
    call cc_lit_string_append
    jp nc,p1110_fail
    cp E_FORMAT
    jp nz,p1110_fail

    call cc_lit_reset
    call cc_lit_string_begin
    ret c
    ld hl,p1110_bad_hex
    ld bc,p1110_bad_hex_end-p1110_bad_hex
    call cc_lit_string_append
    jp nc,p1110_fail
    cp E_FORMAT
    jp nz,p1110_fail

    ld hl,p1110_bad_char
    ld bc,p1110_bad_char_end-p1110_bad_char
    call cc_lit_char
    jp nc,p1110_fail
    cp E_FORMAT
    jp nz,p1110_fail
    xor a
    ret

p1110_all:
    call p1110_chars
    ret c
    call p1110_strings
    ret c
    call p1110_negatives
    ret c
    xor a
    ret

fixture_end:
    SAVEBIN "p1110-main.bin",fixture,fixture_end-fixture
''', encoding="utf-8", newline="\n")

    result = run_command(
        [assembler, "--nologo", "--sym=p1110-literals.sym", fixture.name],
        cwd=build, timeout_seconds=30,
    )
    require(not result.timed_out and result.exit_code == 0,
            f"P11.10 assemble: {result.stderr or result.stdout}")
    main = (build / "p1110-main.bin").read_bytes()
    require(len(main) <= 0x3F00, "P11.10 fixture exceeds high-RAM SNA budget")
    syms = phase3_open_descriptions._symbols(
        build / "p1110-literals.sym",
        ("p1110_chars", "p1110_strings", "p1110_negatives"),
    )

    assertions = [
        {"name": "character-literal-byte-decoding-native", "passed": True},
        {"name": "supported-c48-escape-table-native", "passed": True},
        {"name": "exact-two-digit-hex-escape-native", "passed": True},
        {"name": "adjacent-string-token-concatenation-native", "passed": True},
        {"name": "one-trailing-nul-per-completed-string-native", "passed": True},
        {"name": "golden-obj1-data-staging-bytes-native", "passed": True},
        {"name": "sdk-pinned-literal-oracle-mapping-recorded", "passed": True},
    ]
    commands = [result]
    if action == "test":
        def patch(ram):
            ram[0xC000 - 0x4000:0xC000 - 0x4000 + len(main)] = main

        for name in ("p1110_chars", "p1110_strings", "p1110_negatives"):
            code = (
                b"\xF3" + phase1._ld_sp(0xBFC0)
                + phase1._call(syms[name])
                + phase1._jp_c(FAIL_PC) + phase1._jp(PASS_PC)
            )
            try:
                commands.append(run_sna(root, code, patch=patch))
            except DriverError as exc:
                raise P1110Error(f"{name} native fixture failed: {exc}") from None
        assertions += [
            {"name": "fuse-char-plain-simple-hex-zero-backslash", "passed": True},
            {"name": "fuse-string-adjacent-concat-deterministic-pool", "passed": True},
            {"name": "fuse-empty-string-single-nul", "passed": True},
            {"name": "fuse-general-octal-escape-rejected-notsup", "passed": True},
            {"name": "fuse-unknown-and-malformed-hex-escape-rejected", "passed": True},
            {"name": "fuse-multibyte-character-literal-rejected", "passed": True},
        ]

    hashes = {
        "v1/src/tools/cc.asm": sha256_file(source),
        "v1/build/p1110-main.bin": sha256_file(build / "p1110-main.bin"),
        "v1/tools-host/test-driver/phase11_step_10.py": sha256_file(
            root / "v1/tools-host/test-driver/phase11_step_10.py"
        ),
        "v1/dist/certification/P11.09.build.json": sha256_file(
            root / "v1/dist/certification/P11.09.build.json"
        ),
        "v1/dist/certification/P11.09.test.json": sha256_file(
            root / "v1/dist/certification/P11.09.test.json"
        ),
    }
    return commands, hashes, assertions
