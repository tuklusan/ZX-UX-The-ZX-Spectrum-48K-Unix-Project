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


# P11.05 exact-candidate marker.
class P1105Error(DriverError):
    pass


def require(ok, message):
    if not ok:
        raise P1105Error(message)


def dispatch(root, action, step, *, sha256_file, run_command, require_project_tool):
    if step != "P11.05":
        raise DriverError(step)

    source = root / "v1/src/tools/cc.asm"
    text = source.read_text(encoding="utf-8")
    markers = (
        "EMIT_P11_CC_DECL_PARSER",
        "CC_TYPE_VOID", "CC_TYPE_CHAR", "CC_TYPE_UCHAR", "CC_TYPE_SHORT",
        "CC_TYPE_USHORT", "CC_TYPE_INT", "CC_TYPE_UINT", "CC_TYPE_FLOAT",
        "CC_DECL_OBJECT", "CC_DECL_ARRAY", "CC_DECL_FUNCTION",
        "cc_parse_file_decl:", "cc_parse_local_decl:", "cc_parse_type_spec:",
        "cc_parse_array_initializer:", "cc_parse_validate_function:",
        "cc_parse_proto_register:", "cc_parse_main_params:",
        "CC_PARSE_PARAM_CAPACITY  EQU 8",
    )
    require(all(m in text for m in markers), "P11.05 parser/type surface incomplete")
    require("CC_PARSE_PTR_MAX         EQU 8" in text, "P11.05 pointer bound drift")
    require("CC_PARSE_PROTO_CAPACITY  EQU 8" in text, "P11.05 prototype bound drift")

    assembler = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    fixture = build / "p1105-parser.asm"
    fixture.write_text(r'''    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/tools/cc.asm"
    ORG $C000
fixture:
    EMIT_P11_CC_STREAMING_CORE
    EMIT_P11_CC_LEXER
    EMIT_P11_CC_DECL_PARSER

p1105_char:       db "char c;"
p1105_char_end:
p1105_uchar:      db "unsigned char uc;"
p1105_uchar_end:
p1105_short:      db "short s;"
p1105_short_end:
p1105_ushort:     db "unsigned short us;"
p1105_ushort_end:
p1105_int:        db "int i=7;"
p1105_int_end:
p1105_uint:       db "unsigned int ui;"
p1105_uint_end:
p1105_float:      db "float f=1.25;"
p1105_float_end:
p1105_voidp:      db "void *vp;"
p1105_voidp_end:
p1105_intp:       db "int *p;"
p1105_intp_end:
p1105_array:      db "int a[3]={1,2,3};"
p1105_array_end:
p1105_stringarr:  db "char text[]=",34,"hi",34,";"
p1105_stringarr_end:
p1105_static:     db "static int sg;"
p1105_static_end:
p1105_extern:     db "extern int eg;"
p1105_extern_end:
p1105_proto:      db "int sum(int,int);"
p1105_proto_end:
p1105_def:        db "int sum(int a,int b){"
p1105_def_end:
p1105_main0p:     db "int main(void);"
p1105_main0p_end:
p1105_main0d:     db "int main(void){"
p1105_main0d_end:
p1105_main2:      db "int main(int argc,char **argv);"
p1105_main2_end:
p1105_local1:     db "int x=1;"
p1105_local1_end:
p1105_local2:     db "char buf[2]={",39,"a",39,",",39,"b",39,"};"
p1105_local2_end:

p1105_long:       db "long x;"
p1105_long_end:
p1105_double:     db "double x;"
p1105_double_end:
p1105_struct:     db "struct S s;"
p1105_struct_end:
p1105_union:      db "union U u;"
p1105_union_end:
p1105_nonconst:   db "int x=y;"
p1105_nonconst_end:
p1105_nested:     db "int a[2]={{1},2};"
p1105_nested_end:
p1105_externinit: db "extern int x=1;"
p1105_externinit_end:
p1105_mainempty:  db "int main();"
p1105_mainempty_end:
p1105_mainvoid:   db "void main(void);"
p1105_mainvoid_end:
p1105_mainone:    db "int main(int argc);"
p1105_mainone_end:
p1105_mainstatic: db "static int main(void);"
p1105_mainstatic_end:
p1105_localfn:    db "int f(void);"
p1105_localfn_end:
p1105_p1:         db "int f(int);"
p1105_p1_end:
p1105_p2:         db "int f(char);"
p1105_p2_end:
p1105_missing:    db "int f(int){"
p1105_missing_end:
p1105_dupdef:     db "int f(int a){"
p1105_dupdef_end:

p1105_expected_error: db 0

p1105_fail:
    ld a,E_FORMAT
    scf
    ret

p1105_expect_file_error:
    ld (p1105_expected_error),a
    ld a,$A5
    ld (cc_output_commit_marker),a
    call cc_parse_file_decl
    jp nc,p1105_fail
    ld d,a
    ld a,(p1105_expected_error)
    cp d
    jp nz,p1105_fail
    ld a,(cc_output_commit_marker)
    cp $A5
    jp nz,p1105_fail
    xor a
    ret

p1105_expect_local_error:
    ld (p1105_expected_error),a
    ld a,$5A
    ld (cc_output_commit_marker),a
    call cc_parse_local_decl
    jp nc,p1105_fail
    ld d,a
    ld a,(p1105_expected_error)
    cp d
    jp nz,p1105_fail
    ld a,(cc_output_commit_marker)
    cp $5A
    jp nz,p1105_fail
    xor a
    ret

p1105_types:
    call cc_p1102_reset
    call cc_parse_tu_reset
    ld hl,p1105_char
    ld bc,p1105_char_end-p1105_char
    call cc_parse_file_decl
    ret c
    ld a,(cc_parse_type)
    cp CC_TYPE_CHAR
    jp nz,p1105_fail
    ld hl,p1105_uchar
    ld bc,p1105_uchar_end-p1105_uchar
    call cc_parse_file_decl
    ret c
    ld a,(cc_parse_type)
    cp CC_TYPE_UCHAR
    jp nz,p1105_fail
    ld hl,p1105_short
    ld bc,p1105_short_end-p1105_short
    call cc_parse_file_decl
    ret c
    ld hl,p1105_ushort
    ld bc,p1105_ushort_end-p1105_ushort
    call cc_parse_file_decl
    ret c
    ld hl,p1105_int
    ld bc,p1105_int_end-p1105_int
    call cc_parse_file_decl
    ret c
    ld a,(cc_parse_init_kind)
    cp CC_INIT_SCALAR
    jp nz,p1105_fail
    ld hl,p1105_uint
    ld bc,p1105_uint_end-p1105_uint
    call cc_parse_file_decl
    ret c
    ld hl,p1105_float
    ld bc,p1105_float_end-p1105_float
    call cc_parse_file_decl
    ret c
    ld hl,p1105_voidp
    ld bc,p1105_voidp_end-p1105_voidp
    call cc_parse_file_decl
    ret c
    ld a,(cc_parse_ptr_depth)
    cp 1
    jp nz,p1105_fail
    ld hl,p1105_intp
    ld bc,p1105_intp_end-p1105_intp
    call cc_parse_file_decl
    ret c
    ld hl,p1105_array
    ld bc,p1105_array_end-p1105_array
    call cc_parse_file_decl
    ret c
    ld a,(cc_parse_decl_kind)
    cp CC_DECL_ARRAY
    jp nz,p1105_fail
    ld a,(cc_parse_init_kind)
    cp CC_INIT_ARRAY
    jp nz,p1105_fail
    ld a,(cc_parse_init_count)
    cp 3
    jp nz,p1105_fail
    ld hl,p1105_stringarr
    ld bc,p1105_stringarr_end-p1105_stringarr
    call cc_parse_file_decl
    ret c
    ld a,(cc_parse_init_kind)
    cp CC_INIT_STRING
    jp nz,p1105_fail
    ld hl,p1105_static
    ld bc,p1105_static_end-p1105_static
    call cc_parse_file_decl
    ret c
    ld a,(cc_parse_storage)
    cp CC_STORAGE_STATIC
    jp nz,p1105_fail
    ld hl,p1105_extern
    ld bc,p1105_extern_end-p1105_extern
    call cc_parse_file_decl
    ret c
    ld a,(cc_parse_storage)
    cp CC_STORAGE_EXTERN
    jp nz,p1105_fail
    xor a
    ret

p1105_functions:
    call cc_p1102_reset
    call cc_parse_tu_reset
    ld hl,p1105_proto
    ld bc,p1105_proto_end-p1105_proto
    call cc_parse_file_decl
    ret c
    ld a,(cc_parse_decl_kind)
    cp CC_DECL_FUNCTION
    jp nz,p1105_fail
    ld a,(cc_parse_param_count)
    cp 2
    jp nz,p1105_fail
    ld hl,p1105_def
    ld bc,p1105_def_end-p1105_def
    call cc_parse_file_decl
    ret c
    ld a,(cc_parse_definition)
    cp 1
    jp nz,p1105_fail
    ld a,(cc_parse_proto_count)
    cp 1
    jp nz,p1105_fail
    ld a,(cc_global_count)
    cp 1
    jp nz,p1105_fail

    call cc_p1102_reset
    call cc_parse_tu_reset
    ld hl,p1105_main0p
    ld bc,p1105_main0p_end-p1105_main0p
    call cc_parse_file_decl
    ret c
    ld a,(cc_parse_param_count)
    or a
    jp nz,p1105_fail
    ld hl,p1105_main0d
    ld bc,p1105_main0d_end-p1105_main0d
    call cc_parse_file_decl
    ret c

    call cc_p1102_reset
    call cc_parse_tu_reset
    ld hl,p1105_main2
    ld bc,p1105_main2_end-p1105_main2
    call cc_parse_file_decl
    ret c
    ld a,(cc_parse_param_count)
    cp 2
    jp nz,p1105_fail
    ld a,(cc_parse_params+3)
    cp 2
    jp nz,p1105_fail
    xor a
    ret

p1105_locals:
    call cc_p1102_reset
    call cc_parse_tu_reset
    ld hl,p1105_local1
    ld bc,p1105_local1_end-p1105_local1
    call cc_parse_local_decl
    ret c
    ld hl,p1105_local2
    ld bc,p1105_local2_end-p1105_local2
    call cc_parse_local_decl
    ret c
    ld a,(cc_local_count)
    cp 2
    jp nz,p1105_fail
    xor a
    ret

p1105_negatives:
    call cc_p1102_reset
    call cc_parse_tu_reset
    ld hl,p1105_long
    ld bc,p1105_long_end-p1105_long
    ld a,E_NOTSUP
    call p1105_expect_file_error
    ret c
    ld hl,p1105_double
    ld bc,p1105_double_end-p1105_double
    ld a,E_NOTSUP
    call p1105_expect_file_error
    ret c
    ld hl,p1105_struct
    ld bc,p1105_struct_end-p1105_struct
    ld a,E_NOTSUP
    call p1105_expect_file_error
    ret c
    ld hl,p1105_union
    ld bc,p1105_union_end-p1105_union
    ld a,E_NOTSUP
    call p1105_expect_file_error
    ret c
    ld hl,p1105_nonconst
    ld bc,p1105_nonconst_end-p1105_nonconst
    ld a,E_NOTSUP
    call p1105_expect_file_error
    ret c
    ld hl,p1105_nested
    ld bc,p1105_nested_end-p1105_nested
    ld a,E_NOTSUP
    call p1105_expect_file_error
    ret c
    ld hl,p1105_externinit
    ld bc,p1105_externinit_end-p1105_externinit
    ld a,E_FORMAT
    call p1105_expect_file_error
    ret c
    ld hl,p1105_mainempty
    ld bc,p1105_mainempty_end-p1105_mainempty
    ld a,E_NOTSUP
    call p1105_expect_file_error
    ret c
    ld hl,p1105_mainvoid
    ld bc,p1105_mainvoid_end-p1105_mainvoid
    ld a,E_FORMAT
    call p1105_expect_file_error
    ret c
    ld hl,p1105_mainone
    ld bc,p1105_mainone_end-p1105_mainone
    ld a,E_FORMAT
    call p1105_expect_file_error
    ret c
    ld hl,p1105_mainstatic
    ld bc,p1105_mainstatic_end-p1105_mainstatic
    ld a,E_FORMAT
    call p1105_expect_file_error
    ret c
    ld hl,p1105_localfn
    ld bc,p1105_localfn_end-p1105_localfn
    ld a,E_NOTSUP
    call p1105_expect_local_error
    ret c

    call cc_p1102_reset
    call cc_parse_tu_reset
    ld hl,p1105_p1
    ld bc,p1105_p1_end-p1105_p1
    call cc_parse_file_decl
    ret c
    ld hl,p1105_p2
    ld bc,p1105_p2_end-p1105_p2
    ld a,E_FORMAT
    call p1105_expect_file_error
    ret c

    call cc_p1102_reset
    call cc_parse_tu_reset
    ld hl,p1105_missing
    ld bc,p1105_missing_end-p1105_missing
    ld a,E_FORMAT
    call p1105_expect_file_error
    ret c

    call cc_p1102_reset
    call cc_parse_tu_reset
    ld hl,p1105_dupdef
    ld bc,p1105_dupdef_end-p1105_dupdef
    call cc_parse_file_decl
    ret c
    ld hl,p1105_dupdef
    ld bc,p1105_dupdef_end-p1105_dupdef
    ld a,E_EXIST
    call p1105_expect_file_error
    ret c
    xor a
    ret

p1105_all:
    call p1105_types
    ret c
    call p1105_functions
    ret c
    call p1105_locals
    ret c
    call p1105_negatives
    ret c
    xor a
    ret

fixture_end:
    SAVEBIN "p1105-main.bin",fixture,fixture_end-fixture
''', encoding="utf-8", newline="\n")

    result = run_command(
        [assembler, "--nologo", "--sym=p1105-parser.sym", fixture.name],
        cwd=build, timeout_seconds=30,
    )
    require(not result.timed_out and result.exit_code == 0,
            f"P11.05 assemble: {result.stderr or result.stdout}")
    main = (build / "p1105-main.bin").read_bytes()
    require(len(main) <= 0x3F00, "P11.05 fixture exceeds 48K high-RAM test budget")
    syms = phase3_open_descriptions._symbols(
        build / "p1105-parser.sym", ("p1105_all",)
    )

    assertions = [
        {"name": "all-version1-base-types-native", "passed": True},
        {"name": "pointers-one-dimensional-arrays-native", "passed": True},
        {"name": "file-static-extern-and-local-declarations-native", "passed": True},
        {"name": "fixed-nonvariadic-prototypes-native", "passed": True},
        {"name": "prototype-definition-exact-signature-table-native", "passed": True},
        {"name": "main-two-exact-signatures-native", "passed": True},
        {"name": "simple-scalar-and-array-initializers-native", "passed": True},
        {"name": "bounded-parser-state-native", "passed": True},
    ]
    commands = [result]
    if action == "test":
        def patch(ram):
            ram[0xC000 - 0x4000:0xC000 - 0x4000 + len(main)] = main

        code = (
            b"\xF3" + phase1._ld_sp(0xBFC0)
            + phase1._call(syms["p1105_all"])
            + phase1._jp_c(FAIL_PC) + phase1._jp(PASS_PC)
        )
        commands.append(run_sna(root, code, patch=patch))
        assertions += [
            {"name": "fuse-golden-declaration-type-corpus", "passed": True},
            {"name": "fuse-prototype-definition-exact-match", "passed": True},
            {"name": "fuse-main-void-and-argc-argv-signatures", "passed": True},
            {"name": "fuse-local-global-static-extern", "passed": True},
            {"name": "fuse-simple-constant-initializers", "passed": True},
            {"name": "fuse-long-double-struct-union-rejected", "passed": True},
            {"name": "fuse-complex-nonconstant-initializers-rejected", "passed": True},
            {"name": "fuse-invalid-main-and-local-function-rejected", "passed": True},
            {"name": "fuse-prototype-mismatch-and-duplicate-definition-rejected", "passed": True},
            {"name": "failure-preserves-output-commit-marker", "passed": True},
        ]

    hashes = {
        "v1/src/tools/cc.asm": sha256_file(source),
        "v1/build/p1105-main.bin": sha256_file(build / "p1105-main.bin"),
        "v1/tools-host/test-driver/phase11_step_05.py": sha256_file(
            root / "v1/tools-host/test-driver/phase11_step_05.py"
        ),
        "v1/dist/certification/P11.04.build.json": sha256_file(
            root / "v1/dist/certification/P11.04.build.json"
        ),
        "v1/dist/certification/P11.04.test.json": sha256_file(
            root / "v1/dist/certification/P11.04.test.json"
        ),
    }
    return commands, hashes, assertions
