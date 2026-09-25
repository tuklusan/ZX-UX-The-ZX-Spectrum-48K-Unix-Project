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


# P11.07 exact-candidate marker.
class P1107Error(DriverError):
    pass


def require(ok, message):
    if not ok:
        raise P1107Error(message)


def dispatch(root, action, step, *, sha256_file, run_command, require_project_tool):
    if step != "P11.07":
        raise DriverError(step)

    source = root / "v1/src/tools/cc.asm"
    text = source.read_text(encoding="utf-8")
    markers = (
        "EMIT_P11_CC_EXPRESSIONS", "CC_X_ASSIGN", "CC_X_ADD", "CC_X_SUB",
        "CC_X_MUL", "CC_X_DIV", "CC_X_MOD", "CC_X_PREINC", "CC_X_PREDEC",
        "CC_X_POSTINC", "CC_X_POSTDEC", "CC_X_SHL", "CC_X_SHR",
        "CC_X_LT", "CC_X_LE", "CC_X_GT", "CC_X_GE", "CC_X_EQ", "CC_X_NE",
        "CC_X_BAND", "CC_X_BOR", "CC_X_BXOR", "CC_X_BNOT",
        "CC_X_LAND_SC", "CC_X_LOR_SC", "CC_X_SC_END", "CC_X_LNOT",
        "CC_X_ADDR", "CC_X_DEREF", "CC_X_INDEX", "CC_X_CALL",
        "CC_X_UPLUS", "CC_X_UMINUS", "CC_X_CAST",
        "cc_x_assignment:", "cc_x_lor:", "cc_x_land:", "cc_x_equality:",
        "cc_x_relational:", "cc_x_shift:", "cc_x_additive:",
        "cc_x_multiplicative:", "cc_x_unary:", "cc_x_postfix:",
        "cc_x_primary:", "cc_x_paren_or_cast:",
    )
    require(all(m in text for m in markers), "P11.07 expression surface incomplete")
    require("CC_X_NEST_MAX           EQU 8" in text, "P11.07 expression depth bound drift")
    require("CC_X_OUTPUT_CAPACITY    EQU 128" in text, "P11.07 expression output bound drift")
    require("short-circuit event kinds" in text, "P11.07 short-circuit lowering contract missing")

    assembler = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    fixture = build / "p1107-expressions.asm"
    fixture.write_text(r'''    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/tools/cc.asm"
    ORG $C000
fixture:
    EMIT_P11_CC_STREAMING_CORE
    EMIT_P11_CC_LEXER
    EMIT_P11_CC_DECL_PARSER
    EMIT_P11_CC_EXPRESSIONS

p1107_prec:
    db "a=b+c*d<<e<f==g&h^i|j&&k||l"
p1107_prec_end:
p1107_prec_expected:
    db CC_X_IDENT
    db CC_X_IDENT,CC_X_IDENT,CC_X_IDENT,CC_X_MUL,CC_X_ADD
    db CC_X_IDENT,CC_X_SHL,CC_X_IDENT,CC_X_LT,CC_X_IDENT,CC_X_EQ
    db CC_X_IDENT,CC_X_BAND,CC_X_IDENT,CC_X_BXOR,CC_X_IDENT,CC_X_BOR
    db CC_X_LAND_SC,CC_X_IDENT,CC_X_SC_END
    db CC_X_LOR_SC,CC_X_IDENT,CC_X_SC_END
    db CC_X_ASSIGN
p1107_prec_expected_end:

p1107_prec2:
    db "a-b/c%d>>e<=f>=g!=h"
p1107_prec2_end:
p1107_prec2_expected:
    db CC_X_IDENT,CC_X_IDENT,CC_X_IDENT,CC_X_DIV,CC_X_IDENT,CC_X_MOD,CC_X_SUB
    db CC_X_IDENT,CC_X_SHR,CC_X_IDENT,CC_X_LE,CC_X_IDENT,CC_X_GE
    db CC_X_IDENT,CC_X_NE
p1107_prec2_expected_end:

p1107_post:
    db "++a[1]+f(2,3)--"
p1107_post_end:
p1107_post_expected:
    db CC_X_IDENT,CC_X_INT,CC_X_INDEX,CC_X_PREINC
    db CC_X_IDENT,CC_X_INT,CC_X_INT,CC_X_CALL,CC_X_POSTDEC,CC_X_ADD
p1107_post_expected_end:

p1107_unary:
    db "&*p+~x-!y+-z++ + +w"
p1107_unary_end:
p1107_unary_expected:
    db CC_X_IDENT,CC_X_DEREF,CC_X_ADDR
    db CC_X_IDENT,CC_X_BNOT,CC_X_ADD
    db CC_X_IDENT,CC_X_LNOT,CC_X_SUB
    db CC_X_IDENT,CC_X_POSTINC,CC_X_UMINUS,CC_X_ADD
    db CC_X_IDENT,CC_X_UPLUS,CC_X_ADD
p1107_unary_expected_end:

p1107_cast:
    db "(int)a+(unsigned char)b+(short)c+(unsigned int)d+(float)e"
p1107_cast_end:
p1107_cast_expected:
    db CC_X_IDENT,CC_X_CAST,CC_TYPE_INT
    db CC_X_IDENT,CC_X_CAST,CC_TYPE_UCHAR,CC_X_ADD
    db CC_X_IDENT,CC_X_CAST,CC_TYPE_SHORT,CC_X_ADD
    db CC_X_IDENT,CC_X_CAST,CC_TYPE_UINT,CC_X_ADD
    db CC_X_IDENT,CC_X_CAST,CC_TYPE_FLOAT,CC_X_ADD
p1107_cast_expected_end:

p1107_assign:
    db "a=b=c"
p1107_assign_end:
p1107_assign_expected:
    db CC_X_IDENT,CC_X_IDENT,CC_X_IDENT,CC_X_ASSIGN,CC_X_ASSIGN
p1107_assign_expected_end:

p1107_call:
    db "f((a+b),c[2])"
p1107_call_end:
p1107_call_expected:
    db CC_X_IDENT,CC_X_IDENT,CC_X_IDENT,CC_X_ADD
    db CC_X_IDENT,CC_X_INT,CC_X_INDEX,CC_X_CALL
p1107_call_expected_end:

p1107_literals:
    db "1.0+",39,"x",39
p1107_literals_end:
p1107_literals_expected:
    db CC_X_FLOAT,CC_X_CHAR,CC_X_ADD
p1107_literals_expected_end:

p1107_bad_cond: db "a?b:c"
p1107_bad_cond_end:
p1107_bad_comp: db "a+=1"
p1107_bad_comp_end:
p1107_bad_comma: db "a,b"
p1107_bad_comma_end:
p1107_bad_voidcast: db "(void)a"
p1107_bad_voidcast_end:
p1107_bad_call: db "f(a,)"
p1107_bad_call_end:
p1107_bad_depth: db "(((((((((a)))))))))"
p1107_bad_depth_end:

p1107_expected_ptr: dw 0
p1107_expected_len: db 0
p1107_expected_error: db 0

p1107_fail:
    ld a,E_FORMAT
    scf
    ret

; HL source, BC source length, DE expected bytes, A expected length.
p1107_compare:
    ld (p1107_expected_ptr),de
    ld (p1107_expected_len),a
    call cc_expr_parse
    ret c
    ld a,(cc_x_output_count)
    ld b,a
    ld a,(p1107_expected_len)
    cp b
    jp nz,p1107_fail
    ld hl,cc_x_output
    ld de,(p1107_expected_ptr)
    ld a,(p1107_expected_len)
    ld b,a
p1107_compare_loop:
    ld a,(de)
    cp (hl)
    jp nz,p1107_fail
    inc de
    inc hl
    djnz p1107_compare_loop
    xor a
    ret

; HL source, BC source length, A expected errno.
p1107_expect_error:
    ld (p1107_expected_error),a
    ld a,$A5
    ld (cc_output_commit_marker),a
    call cc_expr_parse
    jp nc,p1107_fail
    ld d,a
    ld a,(p1107_expected_error)
    cp d
    jp nz,p1107_fail
    ld a,(cc_output_commit_marker)
    cp $A5
    jp nz,p1107_fail
    xor a
    ret

p1107_golden:
    ld hl,p1107_prec
    ld bc,p1107_prec_end-p1107_prec
    ld de,p1107_prec_expected
    ld a,p1107_prec_expected_end-p1107_prec_expected
    call p1107_compare
    ret c
    ld hl,p1107_prec2
    ld bc,p1107_prec2_end-p1107_prec2
    ld de,p1107_prec2_expected
    ld a,p1107_prec2_expected_end-p1107_prec2_expected
    call p1107_compare
    ret c
    ld hl,p1107_post
    ld bc,p1107_post_end-p1107_post
    ld de,p1107_post_expected
    ld a,p1107_post_expected_end-p1107_post_expected
    call p1107_compare
    ret c
    ld hl,p1107_unary
    ld bc,p1107_unary_end-p1107_unary
    ld de,p1107_unary_expected
    ld a,p1107_unary_expected_end-p1107_unary_expected
    call p1107_compare
    ret c
    ld hl,p1107_cast
    ld bc,p1107_cast_end-p1107_cast
    ld de,p1107_cast_expected
    ld a,p1107_cast_expected_end-p1107_cast_expected
    call p1107_compare
    ret c
    ld hl,p1107_assign
    ld bc,p1107_assign_end-p1107_assign
    ld de,p1107_assign_expected
    ld a,p1107_assign_expected_end-p1107_assign_expected
    call p1107_compare
    ret c
    ld hl,p1107_call
    ld bc,p1107_call_end-p1107_call
    ld de,p1107_call_expected
    ld a,p1107_call_expected_end-p1107_call_expected
    call p1107_compare
    ret c
    ld hl,p1107_literals
    ld bc,p1107_literals_end-p1107_literals
    ld de,p1107_literals_expected
    ld a,p1107_literals_expected_end-p1107_literals_expected
    call p1107_compare
    ret c
    xor a
    ret

p1107_negatives:
    ld hl,p1107_bad_cond
    ld bc,p1107_bad_cond_end-p1107_bad_cond
    ld a,E_NOTSUP
    call p1107_expect_error
    ret c
    ld hl,p1107_bad_comp
    ld bc,p1107_bad_comp_end-p1107_bad_comp
    ld a,E_NOTSUP
    call p1107_expect_error
    ret c
    ld hl,p1107_bad_comma
    ld bc,p1107_bad_comma_end-p1107_bad_comma
    ld a,E_NOTSUP
    call p1107_expect_error
    ret c
    ld hl,p1107_bad_voidcast
    ld bc,p1107_bad_voidcast_end-p1107_bad_voidcast
    ld a,E_NOTSUP
    call p1107_expect_error
    ret c
    ld hl,p1107_bad_call
    ld bc,p1107_bad_call_end-p1107_bad_call
    ld a,E_FORMAT
    call p1107_expect_error
    ret c
    ld hl,p1107_bad_depth
    ld bc,p1107_bad_depth_end-p1107_bad_depth
    ld a,E_NOSPC
    call p1107_expect_error
    ret c
    xor a
    ret

p1107_all:
    call p1107_golden
    ret c
    call p1107_negatives
    ret c
    xor a
    ret

fixture_end:
    SAVEBIN "p1107-main.bin",fixture,fixture_end-fixture
''', encoding="utf-8", newline="\n")

    result = run_command(
        [assembler, "--nologo", "--sym=p1107-expressions.sym", fixture.name],
        cwd=build, timeout_seconds=30,
    )
    require(not result.timed_out and result.exit_code == 0,
            f"P11.07 assemble: {result.stderr or result.stdout}")
    main = (build / "p1107-main.bin").read_bytes()
    require(len(main) <= 0x3F00, "P11.07 fixture exceeds high-RAM SNA budget")
    syms = phase3_open_descriptions._symbols(
        build / "p1107-expressions.sym", ("p1107_golden", "p1107_negatives")
    )

    assertions = [
        {"name": "exact-version1-precedence-ladder-native", "passed": True},
        {"name": "assignment-right-associative-native", "passed": True},
        {"name": "prefix-postfix-index-call-native", "passed": True},
        {"name": "integer-and-integer-float-cast-syntax-native", "passed": True},
        {"name": "logical-short-circuit-boundary-events-native", "passed": True},
        {"name": "comma-operator-not-in-expression-grammar", "passed": True},
        {"name": "bounded-expression-nesting-native", "passed": True},
    ]
    commands = [result]
    if action == "test":
        def patch(ram):
            ram[0xC000 - 0x4000:0xC000 - 0x4000 + len(main)] = main

        for name in ("p1107_golden", "p1107_negatives"):
            code = (
                b"\xF3" + phase1._ld_sp(0xBFC0)
                + phase1._call(syms[name])
                + phase1._jp_c(FAIL_PC) + phase1._jp(PASS_PC)
            )
            try:
                commands.append(run_sna(root, code, patch=patch))
            except DriverError as exc:
                raise P1107Error(f"{name} native fixture failed: {exc}") from None
        assertions += [
            {"name": "fuse-golden-expression-evaluation-order-corpus", "passed": True},
            {"name": "fuse-all-version1-operator-precedence", "passed": True},
            {"name": "fuse-short-circuit-event-before-rhs-and-end-after-rhs", "passed": True},
            {"name": "fuse-casts-integer-and-float-targets", "passed": True},
            {"name": "fuse-conditional-operator-rejected", "passed": True},
            {"name": "fuse-compound-assignment-rejected", "passed": True},
            {"name": "fuse-comma-operator-rejected-outside-call", "passed": True},
            {"name": "fuse-invalid-void-cast-and-depth-overflow-rejected", "passed": True},
            {"name": "failure-preserves-output-commit-marker", "passed": True},
        ]

    hashes = {
        "v1/src/tools/cc.asm": sha256_file(source),
        "v1/build/p1107-main.bin": sha256_file(build / "p1107-main.bin"),
        "v1/tools-host/test-driver/phase11_step_07.py": sha256_file(
            root / "v1/tools-host/test-driver/phase11_step_07.py"
        ),
        "v1/dist/certification/P11.06.build.json": sha256_file(
            root / "v1/dist/certification/P11.06.build.json"
        ),
        "v1/dist/certification/P11.06.test.json": sha256_file(
            root / "v1/dist/certification/P11.06.test.json"
        ),
    }
    return commands, hashes, assertions
