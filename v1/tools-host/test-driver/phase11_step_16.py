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


class P1116Error(DriverError):
    pass


def require(ok, message):
    if not ok:
        raise P1116Error(message)


def dispatch(root, action, step, *, sha256_file, run_command, require_project_tool):
    if step != "P11.16":
        raise DriverError(step)

    source = root / "v1/src/tools/cc.asm"
    bridge = root / "v1/src/libc48/float_bridge.asm"
    text = source.read_text(encoding="utf-8")
    btext = bridge.read_text(encoding="utf-8")
    arch = (root / "docs/01-ZX-UX-ARCHITECTURE-REV17.md").read_text(encoding="utf-8")
    plan = (root / "docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV08.md").read_text(encoding="utf-8")

    markers = (
        "CC_REGCALL_RET_FLOAT_HIDDEN EQU 3",
        "EMIT_P11_CC_FLOAT_RETURN",
        "cc_float_return_set_result:",
        "cc_float_return_user_location:",
        "cc_float_return_emit_call:",
        "compiler/c48/semantics.py",
        "compiler/c48/float5.py",
        "84d144de2721cda5075c3a6610a422663b5e2f77",
    )
    require(all(m in text for m in markers), "P11.16 compiler hidden-result surface incomplete")
    require("c48_float_return5:" in btext and "ld bc,C48_FLOAT_SIZE" in btext,
            "P11.16 libc48 exact-five-byte return helper incomplete")
    require(
        "A function declared to return C48 `float` receives a hidden first argument:" in arch
        and "occupies HL and shifts user arguments to DE, BC, then stack." in arch
        and "returns the same result pointer in HL." in arch,
        "REV17 P11.16 hidden-result ABI drift",
    )
    require(
        "## P11.16 - C48 float return hidden pointer" in plan
        and "hidden first 16-bit pointer to caller-provided five-byte result storage in HL" in plan
        and "Wrong shifted register assignment fails." in plan,
        "REV08 P11.16 acceptance contract drift",
    )

    macro = text[text.index("    MACRO EMIT_P11_CC_FLOAT_RETURN"):]
    macro = macro[:macro.index("    ENDM") + len("    ENDM")]
    code_only = "\n".join(line.split(";", 1)[0] for line in macro.splitlines())
    require(not re.search(r"\biy\b", code_only, re.I), "P11.16 hidden-result lowering uses IY")
    require("cp CC_TYPE_FLOAT\n    jp z,cc_regcall_ret_float_hidden" in text,
            "P11.16 float return classification not hidden-result")

    assembler = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    fixture = build / "p1116-float-return.asm"
    fixture.write_text(r'''    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/tools/cc.asm"
    INCLUDE "../src/libc48/float_bridge.asm"

    ORG $C000
p1116_start:
    EMIT_P11_CC_REGCALL
    EMIT_P11_CC_FLOAT5
    EMIT_P11_CC_FLOAT_ARGS
    EMIT_P11_CC_FLOAT_RETURN
    EMIT_P11_C48_FLOAT5_BRIDGE

p1116_value:       db $81,$40,$00,$00,$00
p1116_guard0:      db $A6
p1116_result:      defs 5,$CC
p1116_guard1:      db $5A
p1116_cap_hl:      dw 0
p1116_cap_de:      dw 0
p1116_cap_bc:      dw 0
p1116_cap_stack:   defs 8,0
p1116_returned:    dw 0
p1116_sp_before:   dw 0
p1116_sp_after:    dw 0

p1116_fail:
    ld a,E_FORMAT
    scf
    ret

p1116_check_word:
    or a
    sbc hl,de
    jp nz,p1116_fail
    xor a
    ret

p1116_append_ret:
    ld hl,cc_regcall_buffer
    ld a,(cc_regcall_len)
    cp CC_REGCALL_BUFFER_CAPACITY
    jp nc,p1116_fail
    ld e,a
    ld d,0
    add hl,de
    ld (hl),$C9
    ret

p1116_set_word:
    ld d,CC_REGCALL_KIND_WORD
    jp cc_regcall_set_arg

p1116_set_six:
    call cc_regcall_reset
    xor a
    ld bc,$1111
    call p1116_set_word
    ret c
    ld a,1
    ld bc,$2222
    call p1116_set_word
    ret c
    ld a,2
    ld bc,$3333
    call p1116_set_word
    ret c
    ld a,3
    ld bc,$4444
    call p1116_set_word
    ret c
    ld a,4
    ld bc,$5555
    call p1116_set_word
    ret c
    ld a,5
    ld bc,$6666
    jp p1116_set_word

p1116_callee:
    ld (p1116_cap_hl),hl
    ld (p1116_cap_de),de
    ld (p1116_cap_bc),bc
    push hl
    ld hl,4
    add hl,sp
    ld de,p1116_cap_stack
    ld b,8
p1116_copy_stack:
    ld a,(hl)
    ld (de),a
    inc hl
    inc de
    djnz p1116_copy_stack
    pop hl
    ld de,p1116_value
    jp c48_float_return5

p1116_runtime:
    call p1116_set_six
    ret c
    ld hl,p1116_result
    call cc_float_return_set_result
    ret c
    ld a,6
    ld hl,p1116_callee
    call cc_float_return_emit_call
    ret c
    call p1116_append_ret
    ld iy,$5C3A
    ld hl,0
    add hl,sp
    ld (p1116_sp_before),hl
    call cc_regcall_buffer
    ld (p1116_returned),hl
    ld (p1116_sp_after),sp

    push iy
    pop hl
    ld de,$5C3A
    call p1116_check_word
    ret c
    ld hl,(p1116_sp_before)
    ld de,(p1116_sp_after)
    call p1116_check_word
    ret c
    ld hl,(p1116_returned)
    ld de,p1116_result
    call p1116_check_word
    ret c
    ld hl,(p1116_cap_hl)
    ld de,p1116_result
    call p1116_check_word
    ret c
    ld hl,(p1116_cap_de)
    ld de,$1111
    call p1116_check_word
    ret c
    ld hl,(p1116_cap_bc)
    ld de,$2222
    call p1116_check_word
    ret c
    ld hl,(p1116_cap_stack)
    ld de,$3333
    call p1116_check_word
    ret c
    ld hl,(p1116_cap_stack+2)
    ld de,$4444
    call p1116_check_word
    ret c
    ld hl,(p1116_cap_stack+4)
    ld de,$5555
    call p1116_check_word
    ret c
    ld hl,(p1116_cap_stack+6)
    ld de,$6666
    call p1116_check_word
    ret c

    ld a,(p1116_guard0)
    cp $A6
    jp nz,p1116_fail
    ld a,(p1116_guard1)
    cp $5A
    jp nz,p1116_fail
    ld hl,p1116_result
    ld de,p1116_value
    ld b,5
p1116_cmp_result:
    ld a,(de)
    cp (hl)
    jp nz,p1116_fail
    inc de
    inc hl
    djnz p1116_cmp_result
    xor a
    ret

p1116_shape_expected:
    db $21,$33,$33,$E5
    db $01,$22,$22
    db $11,$11,$11
    db $21
    dw p1116_result
    db $CD
    dw p1116_callee
    db $F1
p1116_shape_expected_end:

p1116_shape:
    call cc_regcall_reset
    xor a
    ld bc,$1111
    call p1116_set_word
    ret c
    ld a,1
    ld bc,$2222
    call p1116_set_word
    ret c
    ld a,2
    ld bc,$3333
    call p1116_set_word
    ret c
    ld hl,p1116_result
    call cc_float_return_set_result
    ret c
    ld a,3
    ld hl,p1116_callee
    call cc_float_return_emit_call
    ret c
    ld a,(cc_regcall_len)
    cp p1116_shape_expected_end-p1116_shape_expected
    jp nz,p1116_fail
    ld hl,cc_regcall_buffer
    ld de,p1116_shape_expected
    ld b,p1116_shape_expected_end-p1116_shape_expected
p1116_shape_loop:
    ld a,(de)
    cp (hl)
    jp nz,p1116_fail
    inc de
    inc hl
    djnz p1116_shape_loop
    xor a
    ret

p1116_class_and_locations:
    ld a,CC_TYPE_FLOAT
    ld e,0
    call cc_regcall_return_class
    ret c
    cp CC_REGCALL_RET_FLOAT_HIDDEN
    jp nz,p1116_fail
    ld a,CC_TYPE_FLOAT
    ld e,1
    call cc_regcall_return_class
    ret c
    cp CC_REGCALL_RET_HL
    jp nz,p1116_fail
    xor a
    call cc_float_return_user_location
    ret c
    cp CC_REGCALL_SLOT_DE
    jp nz,p1116_fail
    ld a,1
    call cc_float_return_user_location
    ret c
    cp CC_REGCALL_SLOT_BC
    jp nz,p1116_fail
    ld a,2
    call cc_float_return_user_location
    ret c
    cp CC_REGCALL_SLOT_STACK
    jp nz,p1116_fail
    ld a,e
    or a
    jp nz,p1116_fail
    ld a,5
    call cc_float_return_user_location
    ret c
    cp CC_REGCALL_SLOT_STACK
    jp nz,p1116_fail
    ld a,e
    cp 3
    jp nz,p1116_fail
    ld a,6
    call cc_float_return_user_location
    jp nc,p1116_fail
    cp E_INVAL
    jp nz,p1116_fail
    xor a
    ret

p1116_wrong_callee:
    push hl
    ld de,p1116_result
    or a
    sbc hl,de
    pop hl
    jr z,p1116_wrong_unexpected
    ld a,E_FORMAT
    scf
    ret
p1116_wrong_unexpected:
    xor a
    ret

p1116_wrong_shift:
    call cc_regcall_reset
    xor a
    ld bc,$1111
    call p1116_set_word
    ret c
    ld a,1
    ld bc,$2222
    call p1116_set_word
    ret c
    ld a,2
    ld hl,p1116_wrong_callee
    call cc_regcall_emit_call
    ret c
    call p1116_append_ret
    call cc_regcall_buffer
    jp nc,p1116_fail
    cp E_FORMAT
    jp nz,p1116_fail
    xor a
    ret

p1116_bad_result:
    ld hl,0
    call cc_float_return_set_result
    jp nc,p1116_fail
    cp E_INVAL
    jp nz,p1116_fail
    ld hl,$FFFC
    call cc_float_return_set_result
    jp nc,p1116_fail
    cp E_INVAL
    jp nz,p1116_fail
    xor a
    ret

p1116_end:
    SAVEBIN "p1116-main.bin",p1116_start,p1116_end-p1116_start
''', encoding="utf-8", newline="\n")

    result = run_command(
        [assembler, "--nologo", "--sym=p1116-float-return.sym", fixture.name],
        cwd=build, timeout_seconds=30,
    )
    require(not result.timed_out and result.exit_code == 0,
            f"P11.16 assemble: {result.stderr or result.stdout}")
    main = (build / "p1116-main.bin").read_bytes()
    require(0 < len(main) <= 0x3F00, "P11.16 fixture exceeds upper-RAM budget")
    names = ("p1116_runtime", "p1116_shape", "p1116_class_and_locations",
             "p1116_wrong_shift", "p1116_bad_result")
    syms = phase3_open_descriptions._symbols(build / "p1116-float-return.sym", names)

    assertions = [
        {"name": "float-return-class-is-dedicated-hidden-result", "passed": True},
        {"name": "hidden-result-pointer-occupies-hl", "passed": True},
        {"name": "user-arguments-shift-to-de-bc-then-stack", "passed": True},
        {"name": "stack-users-remain-right-to-left-and-caller-cleaned", "passed": True},
        {"name": "libc48-return-helper-copies-exactly-five-bytes", "passed": True},
        {"name": "callee-returns-original-result-pointer-in-hl", "passed": True},
        {"name": "sdk-float-return-semantics-mapping-recorded", "passed": True},
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
                raise P1116Error(f"{name} native fixture failed: {exc}") from None
        assertions += [
            {"name": "fuse-byte-exact-hidden-result-call-sequence", "passed": True},
            {"name": "fuse-six-user-args-observe-shifted-register-stack-layout", "passed": True},
            {"name": "fuse-result-guards-prove-exact-five-byte-write", "passed": True},
            {"name": "fuse-returned-hl-is-identical-hidden-result-pointer", "passed": True},
            {"name": "fuse-iy-remains-os-rom-reserved", "passed": True},
            {"name": "fuse-wrong-unshifted-register-assignment-fails", "passed": True},
            {"name": "fuse-invalid-result-pointer-range-rejected", "passed": True},
        ]

    hashes = {
        "v1/src/tools/cc.asm": sha256_file(source),
        "v1/src/libc48/float_bridge.asm": sha256_file(bridge),
        "v1/build/p1116-main.bin": sha256_file(build / "p1116-main.bin"),
        "v1/tools-host/test-driver/phase11_step_16.py": sha256_file(
            root / "v1/tools-host/test-driver/phase11_step_16.py"
        ),
        "v1/dist/certification/P11.15.build.json": sha256_file(
            root / "v1/dist/certification/P11.15.build.json"
        ),
        "v1/dist/certification/P11.15.test.json": sha256_file(
            root / "v1/dist/certification/P11.15.test.json"
        ),
    }
    return commands, hashes, assertions
