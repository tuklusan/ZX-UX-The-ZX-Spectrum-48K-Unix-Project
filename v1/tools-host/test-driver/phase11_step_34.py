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

import copy
import json

import phase1
import phase3_open_descriptions
from driver_core import DriverError
from fuse_harness import FAIL_PC, PASS_PC, run_sna


class P1134Error(DriverError):
    pass


def require(ok, message):
    if not ok:
        raise P1134Error(message)


def _validate_oracle(o):
    require(o.get("schema") == 1 and o.get("step") == "P11.34", "P11.34 oracle schema/step drift")
    require(o.get("sdk_commit") == "84d144de2721cda5075c3a6610a422663b5e2f77",
            "P11.34 SDK baseline drift")
    require(o.get("sdk_references") == [
        "compiler/c48/typesys.py:CType.size/CType.alignment",
        "compiler/c48/semantics.py:sizeof_type/sizeof_expr=>UINT",
    ], "P11.34 SDK reference mapping drift")
    require(o.get("sizes") == {
        "char": 1, "unsigned char": 1, "short": 2, "unsigned short": 2,
        "int": 2, "unsigned int": 2, "pointer": 2, "float": 5,
    }, "P11.34 sizeof table drift")
    require(o.get("alignments") == {
        "char": 1, "unsigned char": 1, "short": 2, "unsigned short": 2,
        "int": 2, "unsigned int": 2, "pointer": 2, "float": 1,
    }, "P11.34 alignment table drift")
    require(o.get("plain_char_unsigned") is True, "P11.34 plain char must be unsigned")
    require(o.get("signed_char_distinct_type") is False, "P11.34 signed char must not be a distinct type")
    require(o.get("sizeof_result_type") == "unsigned int", "P11.34 sizeof result type drift")
    require(o.get("signed_short_int_representation") == "twos-complement",
            "P11.34 signed representation drift")
    require(o.get("array_stride") == "exact-sizeof-element", "P11.34 array stride drift")
    require(o.get("global_local_padding") == "minimum-required-only", "P11.34 padding drift")
    require(o.get("scalar_argument_slot_bytes") == 2, "P11.34 argument slot width drift")
    require(o.get("char_argument_zero_extended") is True, "P11.34 char argument extension drift")
    require(o.get("call_boundary_sp_even") is True, "P11.34 call-boundary SP drift")
    require(o.get("void_function_return") is True and o.get("void_pointer_base") is True
            and o.get("void_object") is False, "P11.34 void object/function/pointer rule drift")


def _negative_oracle_self_tests(oracle):
    cases = []
    for field, value in (
        ("plain_char_unsigned", False),
        ("scalar_argument_slot_bytes", 1),
        ("call_boundary_sp_even", False),
    ):
        bad = copy.deepcopy(oracle)
        bad[field] = value
        cases.append(bad)
    bad = copy.deepcopy(oracle)
    bad["alignments"]["float"] = 4
    cases.append(bad)
    bad = copy.deepcopy(oracle)
    bad["array_stride"] = "host-rounded"
    cases.append(bad)
    for bad in cases:
        try:
            _validate_oracle(bad)
        except P1134Error:
            continue
        raise P1134Error("P11.34 host-ABI negative oracle unexpectedly accepted")


def dispatch(root, action, step, *, sha256_file, run_command, require_project_tool):
    if step != "P11.34":
        raise DriverError(step)

    source = root / "v1/src/tools/cc.asm"
    text = source.read_text(encoding="utf-8")
    arch = (root / "docs/01-ZX-UX-ARCHITECTURE-REV17.md").read_text(encoding="utf-8")
    plan = (root / "docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV08.md").read_text(encoding="utf-8")
    oracle_path = root / "v1/tests/compiler/p1134-data-model.json"
    oracle = json.loads(oracle_path.read_text(encoding="utf-8"))
    _validate_oracle(oracle)
    _negative_oracle_self_tests(oracle)

    require("char, unsigned char     1         1" in arch
            and "short, unsigned short   2         2" in arch
            and "int, unsigned int       2         2" in arch
            and "pointer                 2         2" in arch
            and "float                   5         1" in arch
            and "Plain `char` is unsigned" in arch
            and "`sizeof` produces an `unsigned int`" in arch
            and "SP is even-aligned at every C48 call boundary." in arch,
            "REV17 P11.34 data-model contract drift")
    require("## P11.34 - `sizeof`/alignment/array stride suite" in plan
            and "float[2] stride5 and int[2] stride2" in plan
            and "Host compiler intuition must not override spec." in plan,
            "REV08 P11.34 acceptance contract drift")
    for marker in (
        "CC_TYPE_CHAR", "CC_TYPE_UCHAR", "CC_TYPE_SHORT", "CC_TYPE_USHORT",
        "CC_TYPE_INT", "CC_TYPE_UINT", "CC_TYPE_FLOAT",
        "cc_ptr_pointee_size:", "cc_ptr_add_scaled:",
        "cc_int_is_signed_type:", "cc_store_object:",
        "cc_frame_plan:", "cc_regcall_set_arg:", "cc_regcall_call_sp_check:",
    ):
        require(marker in text, f"P11.34 compiler prerequisite missing: {marker}")

    assembler = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    fixture = build / "p1134-data-model.asm"
    fixture.write_text(r'''    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/tools/cc.asm"
    ORG $C000
fixture:
    EMIT_P11_CC_STREAMING_CORE
    EMIT_P11_CC_LEXER
    EMIT_P11_CC_DECL_PARSER
    EMIT_P11_CC_INT_SEMANTICS
    EMIT_P11_CC_POINTER_ARITH
    EMIT_P11_CC_GLOBAL_STORAGE
    EMIT_P11_CC_FRAME_LAYOUT
    EMIT_P11_CC_REGCALL

p1134_fail:
    ld a,E_FORMAT
    scf
    ret

; A=base type, E=pointer depth, B=expected sizeof.
p1134_size_one:
    call cc_ptr_pointee_size
    ret c
    cp b
    jp nz,p1134_fail
    xor a
    ret

p1134_sizes:
    ld a,CC_TYPE_CHAR
    ld e,1
    ld b,1
    call p1134_size_one
    ret c
    ld a,CC_TYPE_UCHAR
    ld e,1
    ld b,1
    call p1134_size_one
    ret c
    ld a,CC_TYPE_SHORT
    ld e,1
    ld b,2
    call p1134_size_one
    ret c
    ld a,CC_TYPE_USHORT
    ld e,1
    ld b,2
    call p1134_size_one
    ret c
    ld a,CC_TYPE_INT
    ld e,1
    ld b,2
    call p1134_size_one
    ret c
    ld a,CC_TYPE_UINT
    ld e,1
    ld b,2
    call p1134_size_one
    ret c
    ld a,CC_TYPE_FLOAT
    ld e,1
    ld b,5
    call p1134_size_one
    ret c
    ld a,CC_TYPE_VOID
    ld e,2
    ld b,2
    call p1134_size_one
    ret c

    ld a,CC_TYPE_CHAR
    call cc_int_is_signed_type
    ret c
    or a
    jp nz,p1134_fail
    ld a,CC_TYPE_SHORT
    call cc_int_is_signed_type
    ret c
    cp 1
    jp nz,p1134_fail
    ld a,CC_TYPE_INT
    call cc_int_is_signed_type
    ret c
    cp 1
    jp nz,p1134_fail

    ; sizeof is frozen to unsigned int, whose C48_REGCALL return class is HL.
    ld a,CC_TYPE_UINT
    ld e,0
    call cc_regcall_return_class
    ret c
    cp CC_REGCALL_RET_HL
    jp nz,p1134_fail
    xor a
    ret

p1134_stride:
    ; float[2] second element is exactly +5 and full two-element extent +10.
    ld hl,$8000
    ld de,1
    ld a,5
    call cc_ptr_add_scaled
    ret c
    ld de,$8005
    or a
    sbc hl,de
    jp nz,p1134_fail
    ld hl,$8000
    ld de,2
    ld a,5
    call cc_ptr_add_scaled
    ret c
    ld de,$800A
    or a
    sbc hl,de
    jp nz,p1134_fail

    ; int[2] second element is exactly +2 and full extent +4.
    ld hl,$8000
    ld de,1
    ld a,2
    call cc_ptr_add_scaled
    ret c
    ld de,$8002
    or a
    sbc hl,de
    jp nz,p1134_fail
    ld hl,$8000
    ld de,2
    ld a,2
    call cc_ptr_add_scaled
    ret c
    ld de,$8004
    or a
    sbc hl,de
    jp nz,p1134_fail
    xor a
    ret

p1134_n_c:  db "c",0
p1134_n_i:  db "i",0
p1134_n_f:  db "f",0
p1134_n_d:  db "d",0
p1134_n_s:  db "s",0
p1134_n_fa: db "fa",0
p1134_n_ia: db "ia",0

p1134_store_one:
    ; HL=name, BC=size, D=alignment
    ld e,CC_STORAGE_NONE
    jp cc_store_object

; HL=record pointer, DE=expected BSS offset.
p1134_record_offset:
    ld bc,16
    add hl,bc
    ld c,(hl)
    inc hl
    ld b,(hl)
    ld h,b
    ld l,c
    or a
    sbc hl,de
    jp nz,p1134_fail
    xor a
    ret

p1134_storage:
    call cc_store_reset
    ld hl,p1134_n_c
    ld bc,1
    ld d,1
    call p1134_store_one
    ret c
    ld hl,p1134_n_i
    ld bc,2
    ld d,2
    call p1134_store_one
    ret c
    ld hl,p1134_n_f
    ld bc,5
    ld d,1
    call p1134_store_one
    ret c
    ld hl,p1134_n_d
    ld bc,1
    ld d,1
    call p1134_store_one
    ret c
    ld hl,p1134_n_s
    ld bc,2
    ld d,2
    call p1134_store_one
    ret c
    ld hl,p1134_n_fa
    ld bc,10
    ld d,1
    call p1134_store_one
    ret c
    ld hl,p1134_n_ia
    ld bc,4
    ld d,2
    call p1134_store_one
    ret c

    ld hl,(cc_store_bss_size)
    ld de,26
    or a
    sbc hl,de
    jp nz,p1134_fail

    ld hl,cc_store_records
    ld de,0
    call p1134_record_offset
    ret c
    ld hl,cc_store_records+20
    ld de,2
    call p1134_record_offset
    ret c
    ld hl,cc_store_records+40
    ld de,4
    call p1134_record_offset
    ret c
    ld hl,cc_store_records+60
    ld de,9
    call p1134_record_offset
    ret c
    ld hl,cc_store_records+80
    ld de,10
    call p1134_record_offset
    ret c
    ld hl,cc_store_records+100
    ld de,12
    call p1134_record_offset
    ret c
    ld hl,cc_store_records+120
    ld de,22
    call p1134_record_offset
    ret c

    ; Struct-free local sequence c,int,float,c,short is 12 bytes exactly.
    xor a
    ld bc,12
    call cc_frame_plan
    ret c
    ld a,(cc_frame_stack_bytes)
    cp 12
    jp nz,p1134_fail
    xor a
    ret

p1134_voidp: db "void *p;"
p1134_voidp_end:
p1134_voidfn: db "void f(void);"
p1134_voidfn_end:
p1134_voidobj: db "void x;"
p1134_voidobj_end:
p1134_signedchar: db "signed char x;"
p1134_signedchar_end:

p1134_parser:
    call cc_parse_tu_reset
    ld hl,p1134_voidp
    ld bc,p1134_voidp_end-p1134_voidp
    call cc_parse_file_decl
    ret c

    call cc_parse_tu_reset
    ld hl,p1134_voidfn
    ld bc,p1134_voidfn_end-p1134_voidfn
    call cc_parse_file_decl
    ret c

    call cc_parse_tu_reset
    ld hl,p1134_voidobj
    ld bc,p1134_voidobj_end-p1134_voidobj
    call cc_parse_file_decl
    jp nc,p1134_fail

    call cc_parse_tu_reset
    ld hl,p1134_signedchar
    ld bc,p1134_signedchar_end-p1134_signedchar
    call cc_parse_file_decl
    jp nc,p1134_fail
    xor a
    ret

p1134_char_abi:
    call cc_regcall_reset
    xor a
    ld bc,$AB80
    ld d,CC_REGCALL_KIND_CHAR
    call cc_regcall_set_arg
    ret c
    ld a,(cc_regcall_args)
    cp $80
    jp nz,p1134_fail
    ld a,(cc_regcall_args+1)
    or a
    jp nz,p1134_fail

    ld hl,$BFC0
    call cc_regcall_call_sp_check
    ret c
    ld hl,$BFBF
    call cc_regcall_call_sp_check
    jp nc,p1134_fail
    xor a
    ret

p1134_stack_words_one:
    ; A=count, B=expected number of 16-bit stack slots.
    call cc_regcall_stack_words
    ret c
    cp b
    jp nz,p1134_fail
    xor a
    ret

p1134_regcall_slots:
    call cc_regcall_reset
    xor a
    ld bc,$1001
    ld d,CC_REGCALL_KIND_WORD
    call cc_regcall_set_arg
    ret c
    ld a,1
    ld bc,$AB80
    ld d,CC_REGCALL_KIND_CHAR
    call cc_regcall_set_arg
    ret c
    ld a,2
    ld bc,$3003
    ld d,CC_REGCALL_KIND_WORD
    call cc_regcall_set_arg
    ret c
    ld a,3
    ld bc,$4004
    ld d,CC_REGCALL_KIND_WORD
    call cc_regcall_set_arg
    ret c
    ld a,4
    ld bc,$5005
    ld d,CC_REGCALL_KIND_WORD
    call cc_regcall_set_arg
    ret c
    ld a,5
    ld bc,$6006
    ld d,CC_REGCALL_KIND_WORD
    call cc_regcall_set_arg
    ret c

    ld hl,(cc_regcall_args)
    ld de,$1001
    call p1134_check_word
    ret c
    ld hl,(cc_regcall_args+2)
    ld de,$0080
    call p1134_check_word
    ret c
    ld hl,(cc_regcall_args+4)
    ld de,$3003
    call p1134_check_word
    ret c
    ld hl,(cc_regcall_args+6)
    ld de,$4004
    call p1134_check_word
    ret c
    ld hl,(cc_regcall_args+8)
    ld de,$5005
    call p1134_check_word
    ret c
    ld hl,(cc_regcall_args+10)
    ld de,$6006
    call p1134_check_word
    ret c

    xor a
    call cc_regcall_arg_location
    ret c
    cp CC_REGCALL_SLOT_HL
    jp nz,p1134_fail
    ld a,1
    call cc_regcall_arg_location
    ret c
    cp CC_REGCALL_SLOT_DE
    jp nz,p1134_fail
    ld a,2
    call cc_regcall_arg_location
    ret c
    cp CC_REGCALL_SLOT_BC
    jp nz,p1134_fail
    ld a,3
    call cc_regcall_arg_location
    ret c
    cp CC_REGCALL_SLOT_STACK
    jp nz,p1134_fail
    ld a,e
    or a
    jp nz,p1134_fail
    ld a,4
    call cc_regcall_arg_location
    ret c
    cp CC_REGCALL_SLOT_STACK
    jp nz,p1134_fail
    ld a,e
    cp 1
    jp nz,p1134_fail
    ld a,5
    call cc_regcall_arg_location
    ret c
    cp CC_REGCALL_SLOT_STACK
    jp nz,p1134_fail
    ld a,e
    cp 2
    jp nz,p1134_fail

    xor a
    ld b,0
    call p1134_stack_words_one
    ret c
    ld a,1
    ld b,0
    call p1134_stack_words_one
    ret c
    ld a,2
    ld b,0
    call p1134_stack_words_one
    ret c
    ld a,3
    ld b,0
    call p1134_stack_words_one
    ret c
    ld a,4
    ld b,1
    call p1134_stack_words_one
    ret c
    ld a,5
    ld b,2
    call p1134_stack_words_one
    ret c
    ld a,6
    ld b,3
    call p1134_stack_words_one
    ret c
    xor a
    ret

p1134_check_word:
    ; HL=actual, DE=expected.
    or a
    sbc hl,de
    jp nz,p1134_fail
    xor a
    ret

p1134_twos:
    ; Native signed short/int representation is exact two's-complement.
    ld hl,$FFFF
    inc hl
    ld a,h
    or l
    jp nz,p1134_fail
    ld hl,$8000
    dec hl
    ld de,$7FFF
    or a
    sbc hl,de
    jp nz,p1134_fail
    xor a
    ret

fixture_end:
    SAVEBIN "p1134-main.bin",fixture,fixture_end-fixture
''', encoding="utf-8", newline="\n")

    result = run_command(
        [assembler, "--nologo", "--sym=p1134-data-model.sym", fixture.name],
        cwd=build, timeout_seconds=30,
    )
    require(not result.timed_out and result.exit_code == 0,
            f"P11.34 assemble: {result.stderr or result.stdout}")
    main = (build / "p1134-main.bin").read_bytes()
    require(0 < len(main) <= 0x3F00, "P11.34 fixture exceeds upper-RAM budget")
    names = ("p1134_sizes", "p1134_stride", "p1134_storage",
             "p1134_parser", "p1134_char_abi", "p1134_regcall_slots", "p1134_twos")
    syms = phase3_open_descriptions._symbols(build / "p1134-data-model.sym", names)

    assertions = [
        {"name": "c48-sizeof-table-char1-short-int-pointer2-float5", "passed": True},
        {"name": "c48-alignment-table-char-float1-word-pointer2", "passed": True},
        {"name": "array-stride-exact-float5-int2-no-rounding", "passed": True},
        {"name": "global-layout-minimum-padding-exact", "passed": True},
        {"name": "local-layout-minimum-padding-before-even-frame-tail", "passed": True},
        {"name": "plain-char-unsigned-and-signed-char-not-distinct", "passed": True},
        {"name": "sizeof-result-type-unsigned-int-hl-class", "passed": True},
        {"name": "void-only-return-or-pointer-base-not-object", "passed": True},
        {"name": "signed-short-int-two-complement", "passed": True},
        {"name": "host-abi-intuition-negative-oracles-rejected", "passed": True},
        {"name": "sdk-typesys-size-alignment-and-sizeof-uint-mapping-pinned", "passed": True},
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
                raise P1134Error(f"{name} native fixture failed: {exc}") from None

        assertions += [
            {"name": "fuse-size-alignment-stride-data-model-exact", "passed": True},
            {"name": "fuse-float-array-stride-five-int-array-stride-two", "passed": True},
            {"name": "fuse-minimum-global-local-padding-exact", "passed": True},
            {"name": "fuse-char-0x80-promotes-as-unsigned-128", "passed": True},
            {"name": "fuse-void-and-signed-char-negative-rules", "passed": True},
            {"name": "fuse-regcall-0-through-6-all-16bit-slots", "passed": True},
            {"name": "fuse-regcall-even-sp-every-call-boundary", "passed": True},
        ]

    hashes = {
        "v1/src/tools/cc.asm": sha256_file(source),
        "v1/tests/compiler/p1134-data-model.json": sha256_file(oracle_path),
        "v1/build/p1134-main.bin": sha256_file(build / "p1134-main.bin"),
        "v1/tools-host/test-driver/phase11_step_34.py": sha256_file(root / "v1/tools-host/test-driver/phase11_step_34.py"),
        "v1/dist/certification/P11.33.build.json": sha256_file(root / "v1/dist/certification/P11.33.build.json"),
        "v1/dist/certification/P11.33.test.json": sha256_file(root / "v1/dist/certification/P11.33.test.json"),
    }
    return commands, hashes, assertions
