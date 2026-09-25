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

import re

import phase1
import phase3_open_descriptions
from driver_core import DriverError
from fuse_harness import FAIL_PC, PASS_PC, run_sna


class P1115Error(DriverError):
    pass


def require(ok, message):
    if not ok:
        raise P1115Error(message)


def dispatch(root, action, step, *, sha256_file, run_command, require_project_tool):
    if step != "P11.15":
        raise DriverError(step)

    source = root / "v1/src/tools/cc.asm"
    text = source.read_text(encoding="utf-8")
    arch = (root / "docs/01-ZX-UX-ARCHITECTURE-REV17.md").read_text(encoding="utf-8")
    plan = (root / "docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV08.md").read_text(encoding="utf-8")
    markers = (
        "EMIT_P11_CC_FLOAT_ARGS",
        "CC_REGCALL_KIND_FLOAT_PTR  EQU 2",
        "CC_FLOAT_ARG_TEMP_STRIDE  EQU 5",
        "cc_float_arg_set_pointer:",
        "cc_float_arg_temp_addr:",
        "cc_float_arg_reject_inline:",
        "compiler/c48/float5.py",
        "84d144de2721cda5075c3a6610a422663b5e2f77",
    )
    require(all(m in text for m in markers), "P11.15 compiler float-argument surface incomplete")
    require(
        "A C48 `float` argument is passed as a 16-bit pointer to a caller-owned five-byte" in arch
        and "value and consumes one ordinary argument slot." in arch
        and "The caller materializes literals" in arch
        and "first argument     HL" in arch
        and "second argument    DE" in arch
        and "third argument     BC" in arch,
        "REV17 P11.15 float argument ABI drift",
    )
    require(
        "## P11.15 - C48_REGCALL float arguments" in plan
        and "float values are never passed inline in ordinary 16-bit slots." in plan
        and "Pass-by-value fixture fails." in plan,
        "REV08 P11.15 acceptance contract drift",
    )

    macro = text[text.index("    MACRO EMIT_P11_CC_FLOAT_ARGS"):]
    macro = macro[:macro.index("    ENDM") + len("    ENDM")]
    code_only = "\n".join(line.split(";", 1)[0] for line in macro.splitlines())
    require(not re.search(r"\biy\b", code_only, re.I), "P11.15 float lowering uses IY")
    require("CC_REGCALL_KIND_FLOAT_PTR" in text, "P11.15 float pointer kind missing")
    require("cp CC_REGCALL_KIND_FLOAT_PTR+1" in text,
            "P11.15 REGCALL typed-kind acceptance not frozen")

    assembler = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    fixture = build / "p1115-float-args.asm"
    fixture.write_text(r'''    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/tools/cc.asm"

    ORG $C000
p1115_start:
    EMIT_P11_CC_STREAMING_CORE
    EMIT_P11_CC_LEXER
    EMIT_P11_CC_DECL_PARSER
    EMIT_P11_CC_REGCALL
    EMIT_P11_CC_FLOAT5
    EMIT_P11_CC_FLOAT_ARGS

p1115_f0: db $00,$00,$01,$00,$00
p1115_f1: db $80,$00,$00,$00,$00
p1115_f2: db $81,$40,$00,$00,$00
p1115_f3: db $00,$00,$02,$00,$00
p1115_f4: db $82,$20,$00,$00,$00
p1115_f5: db $00,$FF,$FF,$FF,$00
p1115_literal: db $81,$40,$00,$00,$00
p1115_temp_block: defs 30,$A5

p1115_cap_hl: dw 0
p1115_cap_de: dw 0
p1115_cap_bc: dw 0
p1115_cap_stack: defs 6,0
p1115_sp_before: dw 0
p1115_sp_after: dw 0
p1115_expected0: dw 0

p1115_fail:
    ld a,E_FORMAT
    scf
    ret

p1115_check_word:
    or a
    sbc hl,de
    jp nz,p1115_fail
    xor a
    ret

; HL=actual five-byte object, DE=expected.
p1115_check_float:
    ld b,5
p1115_check_float_loop:
    ld a,(de)
    cp (hl)
    jp nz,p1115_fail
    inc de
    inc hl
    djnz p1115_check_float_loop
    xor a
    ret

p1115_append_ret:
    ld hl,cc_regcall_buffer
    ld a,(cc_regcall_len)
    cp CC_REGCALL_BUFFER_CAPACITY
    jp nc,p1115_fail
    ld e,a
    ld d,0
    add hl,de
    ld (hl),$C9
    ret

p1115_callee:
    ld (p1115_cap_hl),hl
    ld (p1115_cap_de),de
    ld (p1115_cap_bc),bc
    ld hl,0
    add hl,sp
    inc hl
    inc hl
    ld de,p1115_cap_stack
    ld b,6
p1115_copy_stack:
    ld a,(hl)
    ld (de),a
    inc hl
    inc de
    djnz p1115_copy_stack
    ld hl,$5A5A
    ret

p1115_set_six:
    call cc_regcall_reset
    xor a
    ld bc,p1115_f0
    call cc_float_arg_set_pointer
    ret c
    ld a,1
    ld bc,p1115_f1
    call cc_float_arg_set_pointer
    ret c
    ld a,2
    ld bc,p1115_f2
    call cc_float_arg_set_pointer
    ret c
    ld a,3
    ld bc,p1115_f3
    call cc_float_arg_set_pointer
    ret c
    ld a,4
    ld bc,p1115_f4
    call cc_float_arg_set_pointer
    ret c
    ld a,5
    ld bc,p1115_f5
    call cc_float_arg_set_pointer
    ret

p1115_runtime:
    call p1115_set_six
    ret c
    ld a,6
    ld hl,p1115_callee
    call cc_regcall_emit_call
    ret c
    call p1115_append_ret
    ld hl,0
    add hl,sp
    ld (p1115_sp_before),hl
    call cc_regcall_buffer
    ld (p1115_sp_after),sp

    ld de,$5A5A
    call p1115_check_word
    ret c
    ld hl,(p1115_sp_before)
    ld de,(p1115_sp_after)
    call p1115_check_word
    ret c

    ld hl,(p1115_cap_hl)
    ld de,p1115_f0
    call p1115_check_word
    ret c
    ld hl,(p1115_cap_de)
    ld de,p1115_f1
    call p1115_check_word
    ret c
    ld hl,(p1115_cap_bc)
    ld de,p1115_f2
    call p1115_check_word
    ret c
    ld hl,(p1115_cap_stack)
    ld de,p1115_f3
    call p1115_check_word
    ret c
    ld hl,(p1115_cap_stack+2)
    ld de,p1115_f4
    call p1115_check_word
    ret c
    ld hl,(p1115_cap_stack+4)
    ld de,p1115_f5
    call p1115_check_word
    ret c

    ld hl,(p1115_cap_hl)
    ld de,p1115_f0
    call p1115_check_float
    ret c
    ld hl,(p1115_cap_de)
    ld de,p1115_f1
    call p1115_check_float
    ret c
    ld hl,(p1115_cap_bc)
    ld de,p1115_f2
    call p1115_check_float
    ret

p1115_materialize:
    ld a,3
    ld hl,p1115_temp_block
    call cc_float_arg_temp_addr
    ret c
    ld (p1115_expected0),hl
    ex de,hl
    ld hl,p1115_literal
    call cc_float5_copy
    ret c

    call cc_regcall_reset
    ld hl,(p1115_expected0)
    ld b,h
    ld c,l
    xor a
    call cc_float_arg_set_pointer
    ret c
    ld a,1
    ld hl,p1115_callee
    call cc_regcall_emit_call
    ret c
    call p1115_append_ret
    call cc_regcall_buffer
    ld hl,(p1115_cap_hl)
    ld de,(p1115_expected0)
    call p1115_check_word
    ret c
    ld hl,(p1115_cap_hl)
    ld de,p1115_literal
    jp p1115_check_float

p1115_negative:
    call cc_regcall_reset
    ld a,2
    ld bc,$4081
    call cc_float_arg_reject_inline
    jp nc,p1115_fail
    cp E_FORMAT
    jp nz,p1115_fail

    xor a
    ld bc,0
    call cc_float_arg_set_pointer
    jp nc,p1115_fail
    cp E_INVAL
    jp nz,p1115_fail

    xor a
    ld bc,$FFFC
    call cc_float_arg_set_pointer
    jp nc,p1115_fail
    cp E_INVAL
    jp nz,p1115_fail

    ld a,6
    ld hl,p1115_temp_block
    call cc_float_arg_temp_addr
    jp nc,p1115_fail
    cp E_INVAL
    jp nz,p1115_fail
    xor a
    ret

p1115_kind:
    call cc_regcall_reset
    ld a,1
    ld bc,p1115_f1
    call cc_float_arg_set_pointer
    ret c
    ld a,(cc_regcall_kinds+1)
    cp CC_REGCALL_KIND_FLOAT_PTR
    jp nz,p1115_fail
    xor a
    ret

p1115_end:
    SAVEBIN "p1115-main.bin",p1115_start,p1115_end-p1115_start
''', encoding="utf-8", newline="\n")

    result = run_command(
        [assembler, "--nologo", "--sym=p1115-float-args.sym", fixture.name],
        cwd=build, timeout_seconds=30,
    )
    require(not result.timed_out and result.exit_code == 0,
            f"P11.15 assemble: {result.stderr or result.stdout}")
    main = (build / "p1115-main.bin").read_bytes()
    require(0 < len(main) <= 0x3F00, "P11.15 fixture exceeds upper-RAM budget")
    names = ("p1115_runtime", "p1115_materialize", "p1115_negative", "p1115_kind")
    syms = phase3_open_descriptions._symbols(build / "p1115-float-args.sym", names)

    assertions = [
        {"name": "float-argument-kind-is-pointer-only", "passed": True},
        {"name": "float-slot-remains-one-16-bit-regcall-slot", "passed": True},
        {"name": "float-pointer-slots-use-hl-de-bc-then-stack", "passed": True},
        {"name": "stack-float-pointers-remain-right-to-left", "passed": True},
        {"name": "caller-five-byte-temp-address-planning-exact", "passed": True},
        {"name": "inline-float-value-lowering-rejected", "passed": True},
        {"name": "sdk-float5-and-call-semantics-mapping-recorded", "passed": True},
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
                raise P1115Error(f"{name} native fixture failed: {exc}") from None
        assertions += [
            {"name": "fuse-six-float-pointers-arrive-in-byte-exact-callee-slots", "passed": True},
            {"name": "fuse-callee-dereferences-exact-five-byte-values", "passed": True},
            {"name": "fuse-materialized-literal-temp-is-addressable-and-passed-by-pointer", "passed": True},
            {"name": "fuse-pass-by-value-attempt-fails-before-call", "passed": True},
            {"name": "fuse-pointer-wrap-and-seventh-temp-rejected", "passed": True},
        ]

    hashes = {
        "v1/src/tools/cc.asm": sha256_file(source),
        "v1/build/p1115-main.bin": sha256_file(build / "p1115-main.bin"),
        "v1/tools-host/test-driver/phase11_step_15.py": sha256_file(
            root / "v1/tools-host/test-driver/phase11_step_15.py"
        ),
        "v1/dist/certification/P11.14.build.json": sha256_file(
            root / "v1/dist/certification/P11.14.build.json"
        ),
        "v1/dist/certification/P11.14.test.json": sha256_file(
            root / "v1/dist/certification/P11.14.test.json"
        ),
    }
    return commands, hashes, assertions
