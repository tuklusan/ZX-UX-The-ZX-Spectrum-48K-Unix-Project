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


class P1106Error(DriverError):
    pass


def require(ok, message):
    if not ok:
        raise P1106Error(message)


def dispatch(root, action, step, *, sha256_file, run_command, require_project_tool):
    if step != "P11.06":
        raise DriverError(step)

    source = root / "v1/src/tools/cc.asm"
    text = source.read_text(encoding="utf-8")
    markers = (
        "EMIT_P11_CC_STATEMENTS", "CC_CF_IF", "CC_CF_ELSE", "CC_CF_WHILE",
        "CC_CF_DO", "CC_CF_FOR", "CC_CF_BREAK", "CC_CF_CONTINUE",
        "CC_CF_RETURN", "cc_stmt_statement:", "cc_stmt_compound:",
        "cc_stmt_if:", "cc_stmt_while:", "cc_stmt_do:", "cc_stmt_for:",
        "cc_stmt_break:", "cc_stmt_continue:", "cc_stmt_return:",
        "cc_stmt_expression_to:",
    )
    require(all(m in text for m in markers), "P11.06 statement/control-flow surface incomplete")
    require("CC_STMT_DEPTH_MAX       EQU 8" in text, "P11.06 statement depth bound drift")
    require("CC_STMT_OUTPUT_CAPACITY EQU 64" in text, "P11.06 event bound drift")

    assembler = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    fixture = build / "p1106-statements.asm"
    fixture.write_text(r'''    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/tools/cc.asm"
    ORG $C000
fixture:
    EMIT_P11_CC_STREAMING_CORE
    EMIT_P11_CC_LEXER
    EMIT_P11_CC_DECL_PARSER
    EMIT_P11_CC_STATEMENTS

p1106_source:
    db "{"
    db "if(a)return 1;else;"
    db "while(b){continue;break;}"
    db "do break;while(c);"
    db "for(i=0;i<2;i++){if(i)continue;}"
    db "return;"
    db "}"
p1106_source_end:

p1106_expected:
    db CC_CF_BLOCK_BEGIN
    db CC_CF_IF,CC_CF_EXPR,CC_CF_RETURN,CC_CF_EXPR,CC_CF_ELSE,CC_CF_EMPTY
    db CC_CF_WHILE,CC_CF_EXPR,CC_CF_BLOCK_BEGIN,CC_CF_CONTINUE,CC_CF_BREAK,CC_CF_BLOCK_END
    db CC_CF_DO,CC_CF_BREAK,CC_CF_EXPR
    db CC_CF_FOR,CC_CF_EXPR,CC_CF_EXPR,CC_CF_EXPR
    db CC_CF_BLOCK_BEGIN,CC_CF_IF,CC_CF_EXPR,CC_CF_CONTINUE,CC_CF_BLOCK_END
    db CC_CF_RETURN
    db CC_CF_BLOCK_END
p1106_expected_end:

p1106_break_bad: db "break;"
p1106_break_bad_end:
p1106_continue_bad: db "continue;"
p1106_continue_bad_end:
p1106_if_empty: db "if();"
p1106_if_empty_end:
p1106_depth_bad: db "{{{{{{{{{;}}}}}}}}}"
p1106_depth_bad_end:

p1106_expected_error: db 0

p1106_fail:
    ld a,E_FORMAT
    scf
    ret

p1106_golden:
    ld hl,p1106_source
    ld bc,p1106_source_end-p1106_source
    call cc_stmt_parse
    ret c
    ld a,(cc_stmt_output_count)
    cp p1106_expected_end-p1106_expected
    jp nz,p1106_fail
    ld hl,cc_stmt_output
    ld de,p1106_expected
    ld b,p1106_expected_end-p1106_expected
p1106_cmp:
    ld a,(de)
    cp (hl)
    jp nz,p1106_fail
    inc de
    inc hl
    djnz p1106_cmp
    xor a
    ret

p1106_expect_error:
    ld (p1106_expected_error),a
    ld a,$A5
    ld (cc_output_commit_marker),a
    call cc_stmt_parse
    jp nc,p1106_fail
    ld d,a
    ld a,(p1106_expected_error)
    cp d
    jp nz,p1106_fail
    ld a,(cc_output_commit_marker)
    cp $A5
    jp nz,p1106_fail
    xor a
    ret

p1106_negatives:
    ld hl,p1106_break_bad
    ld bc,p1106_break_bad_end-p1106_break_bad
    ld a,E_FORMAT
    call p1106_expect_error
    ret c
    ld hl,p1106_continue_bad
    ld bc,p1106_continue_bad_end-p1106_continue_bad
    ld a,E_FORMAT
    call p1106_expect_error
    ret c
    ld hl,p1106_if_empty
    ld bc,p1106_if_empty_end-p1106_if_empty
    ld a,E_FORMAT
    call p1106_expect_error
    ret c
    ld hl,p1106_depth_bad
    ld bc,p1106_depth_bad_end-p1106_depth_bad
    ld a,E_NOSPC
    call p1106_expect_error
    ret c
    xor a
    ret

p1106_all:
    call p1106_golden
    ret c
    call p1106_negatives
    ret c
    xor a
    ret

fixture_end:
    SAVEBIN "p1106-main.bin",fixture,fixture_end-fixture
''', encoding="utf-8", newline="\n")

    result = run_command(
        [assembler, "--nologo", "--sym=p1106-statements.sym", fixture.name],
        cwd=build, timeout_seconds=30,
    )
    require(not result.timed_out and result.exit_code == 0,
            f"P11.06 assemble: {result.stderr or result.stdout}")
    main = (build / "p1106-main.bin").read_bytes()
    require(len(main) <= 0x3F00, "P11.06 fixture exceeds high-RAM test budget")
    syms = phase3_open_descriptions._symbols(
        build / "p1106-statements.sym", ("p1106_golden", "p1106_negatives")
    )

    assertions = [
        {"name": "if-else-native-parser", "passed": True},
        {"name": "while-do-for-native-parser", "passed": True},
        {"name": "break-continue-return-native-parser", "passed": True},
        {"name": "bounded-recursive-statement-depth", "passed": True},
        {"name": "deterministic-control-flow-event-output", "passed": True},
        {"name": "expression-interiors-deferred-to-p1107", "passed": True},
    ]
    commands = [result]
    if action == "test":
        def patch(ram):
            ram[0xC000 - 0x4000:0xC000 - 0x4000 + len(main)] = main

        for name in ("p1106_golden", "p1106_negatives"):
            code = (
                b"\xF3" + phase1._ld_sp(0xBFC0)
                + phase1._call(syms[name])
                + phase1._jp_c(FAIL_PC) + phase1._jp(PASS_PC)
            )
            try:
                commands.append(run_sna(root, code, patch=patch))
            except DriverError as exc:
                raise P1106Error(f"{name} native fixture failed: {exc}") from None
        assertions += [
            {"name": "fuse-golden-control-flow-output", "passed": True},
            {"name": "fuse-if-else-nested-loop-control", "passed": True},
            {"name": "fuse-for-three-clause-control", "passed": True},
            {"name": "fuse-do-while-control", "passed": True},
            {"name": "fuse-break-outside-loop-rejected", "passed": True},
            {"name": "fuse-continue-outside-loop-rejected", "passed": True},
            {"name": "fuse-empty-condition-rejected", "passed": True},
            {"name": "fuse-statement-depth-overflow-rejected", "passed": True},
            {"name": "failure-preserves-output-commit-marker", "passed": True},
        ]

    hashes = {
        "v1/src/tools/cc.asm": sha256_file(source),
        "v1/build/p1106-main.bin": sha256_file(build / "p1106-main.bin"),
        "v1/tools-host/test-driver/phase11_step_06.py": sha256_file(
            root / "v1/tools-host/test-driver/phase11_step_06.py"
        ),
        "v1/dist/certification/P11.05.build.json": sha256_file(
            root / "v1/dist/certification/P11.05.build.json"
        ),
        "v1/dist/certification/P11.05.test.json": sha256_file(
            root / "v1/dist/certification/P11.05.test.json"
        ),
    }
    return commands, hashes, assertions
