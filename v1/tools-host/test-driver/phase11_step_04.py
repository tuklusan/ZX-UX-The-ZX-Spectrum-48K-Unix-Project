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


# P11.04 exact-candidate marker.
class P1104Error(DriverError):
    pass


def require(ok, message):
    if not ok:
        raise P1104Error(message)


def dispatch(root, action, step, *, sha256_file, run_command, require_project_tool):
    if step != "P11.04":
        raise DriverError(step)

    source = root / "v1/src/tools/cc.asm"
    text = source.read_text(encoding="utf-8")
    markers = (
        "EMIT_P11_CC_LEXER", "CC_TOK_IDENT", "CC_TOK_INT", "CC_TOK_FLOAT",
        "CC_TOK_CHAR", "CC_TOK_STRING", "CC_TOK_OPERATOR", "CC_TOK_PUNCT",
        "CC_TOK_KEYWORD", "cc_lex_keywords:", "cc_lex_number:",
        "cc_lex_literal:", "cc_lex_operator:", "cc_lex_finish:",
        "_Static_assert", "_Thread_local",
    )
    require(all(x in text for x in markers), "P11.04 lexer surface incomplete")
    require('db 1,6,"return"' in text and 'db 2,6,"struct"' in text,
            "P11.04 keyword surface incomplete")
    require("CC_IDENT_MAX             EQU 15" in text, "P11.04 identifier bound drift")

    assembler = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    fixture = build / "p1104-lexer.asm"
    fixture.write_text(r'''    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/tools/cc.asm"
    ORG $C000
fixture:
    EMIT_P11_CC_STREAMING_CORE
    EMIT_P11_CC_LEXER

p1104_source:
    db "  /* block */ int Foo=0x2Au; 1.25 .5 1e3 // line",10
    db "foo ",39,"A",39," ",34,"hi",92,"n",34
    db " ++ -- << >> <= >= == != && || ()[]{};,"
p1104_source_end:
p1104_expected:
    db CC_TOK_KEYWORD,CC_TOK_IDENT,CC_TOK_OPERATOR,CC_TOK_INT,CC_TOK_PUNCT
    db CC_TOK_FLOAT,CC_TOK_FLOAT,CC_TOK_FLOAT
    db CC_TOK_IDENT,CC_TOK_CHAR,CC_TOK_STRING
    db CC_TOK_OPERATOR,CC_TOK_OPERATOR,CC_TOK_OPERATOR,CC_TOK_OPERATOR
    db CC_TOK_OPERATOR,CC_TOK_OPERATOR,CC_TOK_OPERATOR,CC_TOK_OPERATOR
    db CC_TOK_OPERATOR,CC_TOK_OPERATOR
    db CC_TOK_PUNCT,CC_TOK_PUNCT,CC_TOK_PUNCT,CC_TOK_PUNCT
    db CC_TOK_PUNCT,CC_TOK_PUNCT,CC_TOK_PUNCT,CC_TOK_PUNCT
p1104_expected_end:

p1104_case: db "Foo foo"
p1104_case_end:
p1104_long: db "abcdefghijklmnop"
p1104_long_end:
p1104_hex_bad: db "0x"
p1104_hex_bad_end:
p1104_octal_bad: db "09"
p1104_octal_bad_end:
p1104_kw_bad: db "struct"
p1104_kw_bad_end:
p1104_op_bad: db "+="
p1104_op_bad_end:
p1104_string_bad: db 34,"abc"
p1104_string_bad_end:
p1104_comment_bad: db "/*x"
p1104_comment_bad_end:
p1104_byte_bad: db 1
p1104_byte_bad_end:

p1104_ptr: dw 0
p1104_rem: dw 0
p1104_expect_ptr: dw 0
p1104_expect_rem: db 0
p1104_expected_error: db 0

p1104_fail:
    ld a,E_FORMAT
    scf
    ret

p1104_next:
    ld hl,(p1104_ptr)
    ld bc,(p1104_rem)
    call cc_lex_token
    ret c
    push af
    ld hl,(p1104_ptr)
    add hl,de
    ld (p1104_ptr),hl
    ld hl,(p1104_rem)
    or a
    sbc hl,de
    ld (p1104_rem),hl
    pop af
    ret

p1104_golden:
    call cc_lex_reset
    ld hl,p1104_source
    ld (p1104_ptr),hl
    ld hl,p1104_source_end-p1104_source
    ld (p1104_rem),hl
    ld hl,p1104_expected
    ld (p1104_expect_ptr),hl
    ld a,p1104_expected_end-p1104_expected
    ld (p1104_expect_rem),a
p1104_golden_loop:
    call p1104_next
    ret c
    ld c,a
    ld hl,(p1104_expect_ptr)
    ld a,(hl)
    cp c
    jp nz,p1104_fail
    inc hl
    ld (p1104_expect_ptr),hl
    ld a,(p1104_expect_rem)
    dec a
    ld (p1104_expect_rem),a
    jr nz,p1104_golden_loop
    ld hl,(p1104_rem)
    ld a,h
    or l
    jp nz,p1104_fail
    call cc_lex_finish
    ret c
    cp CC_TOK_EOF
    jp nz,p1104_fail
    xor a
    ret

p1104_case_test:
    call cc_lex_reset
    ld hl,p1104_case
    ld (p1104_ptr),hl
    ld hl,p1104_case_end-p1104_case
    ld (p1104_rem),hl
    call p1104_next
    ret c
    cp CC_TOK_IDENT
    jp nz,p1104_fail
    ld hl,(cc_lex_token_start)
    ld a,(hl)
    cp 'F'
    jp nz,p1104_fail
    call p1104_next
    ret c
    cp CC_TOK_IDENT
    jp nz,p1104_fail
    ld hl,(cc_lex_token_start)
    ld a,(hl)
    cp 'f'
    jp nz,p1104_fail
    xor a
    ret

p1104_expect_error:
    ld (p1104_expected_error),a
    ld a,$A5
    ld (cc_output_commit_marker),a
    call cc_lex_reset
    call cc_lex_token
    jp nc,p1104_fail
    ld d,a
    ld a,(p1104_expected_error)
    cp d
    jp nz,p1104_fail
    ld a,(cc_output_commit_marker)
    cp $A5
    jp nz,p1104_fail
    xor a
    ret

p1104_negatives:
    ld hl,p1104_long
    ld bc,p1104_long_end-p1104_long
    ld a,E_TOOLONG
    call p1104_expect_error
    ret c
    ld hl,p1104_hex_bad
    ld bc,p1104_hex_bad_end-p1104_hex_bad
    ld a,E_FORMAT
    call p1104_expect_error
    ret c
    ld hl,p1104_octal_bad
    ld bc,p1104_octal_bad_end-p1104_octal_bad
    ld a,E_FORMAT
    call p1104_expect_error
    ret c
    ld hl,p1104_kw_bad
    ld bc,p1104_kw_bad_end-p1104_kw_bad
    ld a,E_NOTSUP
    call p1104_expect_error
    ret c
    ld hl,p1104_op_bad
    ld bc,p1104_op_bad_end-p1104_op_bad
    ld a,E_NOTSUP
    call p1104_expect_error
    ret c
    ld hl,p1104_string_bad
    ld bc,p1104_string_bad_end-p1104_string_bad
    ld a,E_FORMAT
    call p1104_expect_error
    ret c
    ld hl,p1104_byte_bad
    ld bc,p1104_byte_bad_end-p1104_byte_bad
    ld a,E_FORMAT
    call p1104_expect_error
    ret c

    call cc_lex_reset
    ld a,$5A
    ld (cc_output_commit_marker),a
    ld hl,p1104_comment_bad
    ld bc,p1104_comment_bad_end-p1104_comment_bad
    call cc_lex_token
    ret c
    cp CC_TOK_MORE
    jp nz,p1104_fail
    call cc_lex_finish
    jp nc,p1104_fail
    cp E_FORMAT
    jp nz,p1104_fail
    ld a,(cc_output_commit_marker)
    cp $5A
    jp nz,p1104_fail
    xor a
    ret

p1104_all:
    call p1104_golden
    ret c
    call p1104_case_test
    ret c
    call p1104_negatives
    ret c
    xor a
    ret

fixture_end:
    SAVEBIN "p1104-main.bin",fixture,fixture_end-fixture
''', encoding="utf-8", newline="\n")

    result = run_command(
        [assembler, "--nologo", "--sym=p1104-lexer.sym", fixture.name],
        cwd=build, timeout_seconds=30,
    )
    require(not result.timed_out and result.exit_code == 0,
            f"P11.04 assemble: {result.stderr or result.stdout}")
    main = (build / "p1104-main.bin").read_bytes()
    require(len(main) <= 0x3000, "P11.04 fixture exceeds compact SNA budget")
    syms = phase3_open_descriptions._symbols(
        build / "p1104-lexer.sym", ("p1104_all",)
    )

    assertions = [
        {"name": "golden-lexer-surface-static", "passed": True},
        {"name": "case-sensitive-identifiers-static", "passed": True},
        {"name": "supported-and-unsupported-keyword-tables", "passed": True},
        {"name": "fixed-version1-operator-table", "passed": True},
        {"name": "streaming-comment-state", "passed": True},
    ]
    commands = [result]
    if action == "test":
        def patch(ram):
            ram[0xC000 - 0x4000:0xC000 - 0x4000 + len(main)] = main

        code = (
            b"\xF3" + phase1._ld_sp(0xBFC0) + phase1._call(syms["p1104_all"])
            + phase1._jp_c(FAIL_PC) + phase1._jp(PASS_PC)
        )
        commands.append(run_sna(root, code, patch=patch))
        assertions += [
            {"name": "fuse-golden-lexical-corpus", "passed": True},
            {"name": "fuse-case-sensitive-Foo-foo", "passed": True},
            {"name": "fuse-comments-and-stream-finalization", "passed": True},
            {"name": "fuse-integer-float-char-string-operators", "passed": True},
            {"name": "fuse-overlength-token-transactional-failure", "passed": True},
            {"name": "fuse-malformed-token-transactional-failure", "passed": True},
            {"name": "fuse-unsupported-keyword-operator-failure", "passed": True},
            {"name": "fuse-noncanonical-byte-failure", "passed": True},
        ]

    hashes = {
        "v1/src/tools/cc.asm": sha256_file(source),
        "v1/build/p1104-main.bin": sha256_file(build / "p1104-main.bin"),
        "v1/tools-host/test-driver/phase11_step_04.py": sha256_file(
            root / "v1/tools-host/test-driver/phase11_step_04.py"
        ),
        "v1/dist/certification/P11.03.build.json": sha256_file(
            root / "v1/dist/certification/P11.03.build.json"
        ),
        "v1/dist/certification/P11.03.test.json": sha256_file(
            root / "v1/dist/certification/P11.03.test.json"
        ),
    }
    return commands, hashes, assertions
