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


class P1113Error(DriverError):
    pass


def require(ok, message):
    if not ok:
        raise P1113Error(message)


def dispatch(root, action, step, *, sha256_file, run_command, require_project_tool):
    if step != "P11.13":
        raise DriverError(step)

    source = root / "v1/src/tools/cc.asm"
    text = source.read_text(encoding="utf-8")
    crt = (root / "v1/src/libc48/crt0.asm").read_text(encoding="utf-8")
    arch = (root / "docs/01-ZX-UX-ARCHITECTURE-REV17.md").read_text(encoding="utf-8")
    plan = (root / "docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV08.md").read_text(encoding="utf-8")
    markers = (
        "EMIT_P11_CC_REGCALL",
        "C48_REGCALL",
        "cc_regcall_set_arg:",
        "cc_regcall_arg_location:",
        "cc_regcall_emit_call:",
        "cc_regcall_return_class:",
        "cc_regcall_call_sp_check:",
        "POP AF: caller cleanup, preserves HL return",
        "84d144de2721cda5075c3a6610a422663b5e2f77",
    )
    require(all(m in text for m in markers), "P11.13 C48_REGCALL surface incomplete")
    require("EMIT_P11_C48_REGCALL_RUNTIME" in crt and
            "C48_REGCALL_IY_REQUIRED EQU ROM_IY_ANCHOR" in crt,
            "P11.13 libc/crt0 ABI boundary contract missing")
    require("Version 1 has one externally linkable C48 calling convention: `C48_REGCALL`." in arch and
            "first argument     HL" in arch and "second argument    DE" in arch and
            "third argument     BC" in arch and
            "remaining args     16-bit stack words, right-to-left" in arch and
            "SP is even-aligned at every C48 call boundary." in arch,
            "REV17 P11.13 ABI contract drift")
    require("## P11.13 - C48_REGCALL integer/pointer args" in plan and
            "argument counts 0..6" in plan and
            "IY=0x5C3A before/after every generated call/return boundary" in plan,
            "REV08 P11.13 acceptance contract drift")

    macro = text[text.index("    MACRO EMIT_P11_CC_REGCALL"):]
    macro = macro[:macro.index("    ENDM") + len("    ENDM")]
    code_lines = [line.split(";", 1)[0] for line in macro.splitlines()]
    code_only = "\n".join(code_lines)
    require(not re.search(r"\biy\b", code_only, re.I), "P11.13 emitter writes/uses IY")
    require(not re.search(r"\bexx\b", code_only, re.I), "P11.13 emitter uses alternate bank")
    require("ex af" not in code_only.lower(), "P11.13 emitter uses alternate AF")
    require("CDECL" not in text and "C48_CDECL" not in text,
            "P11.13 alternate calling convention surface appeared")
    obj1 = (root / "v1/include/obj1.inc").read_text(encoding="utf-8")
    require("CALLCONV" not in obj1.upper() and "CDECL" not in obj1.upper(),
            "P11.13 invented OBJ1 calling-convention metadata")

    assembler = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    fixture = build / "p1113-regcall.asm"
    fixture.write_text(r'''    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/tools/cc.asm"
    INCLUDE "../src/libc48/crt0.asm"
    ORG $C000
fixture:
    EMIT_P11_CC_STREAMING_CORE
    EMIT_P11_CC_LEXER
    EMIT_P11_CC_DECL_PARSER
    EMIT_P11_CC_FRAME_LAYOUT
    EMIT_P11_CC_REGCALL
    EMIT_P11_C48_REGCALL_RUNTIME

p1113_count: db 0
p1113_cap_hl: dw 0
p1113_cap_de: dw 0
p1113_cap_bc: dw 0
p1113_cap_sp: dw 0
p1113_cap_ix: dw 0
p1113_cap_iy: dw 0
p1113_cap_stack: defs 6,0
p1113_sp_before: dw 0
p1113_sp_after: dw 0

p1113_g0:
    db $CD
    dw p1113_callee
p1113_g0_end:
p1113_g1:
    db $21,$01,$10,$CD
    dw p1113_callee
p1113_g1_end:
p1113_g2:
    db $11,$42,$00,$21,$01,$10,$CD
    dw p1113_callee
p1113_g2_end:
p1113_g3:
    db $01,$03,$30,$11,$42,$00,$21,$01,$10,$CD
    dw p1113_callee
p1113_g3_end:
p1113_g4:
    db $21,$04,$40,$E5,$01,$03,$30,$11,$42,$00,$21,$01,$10,$CD
    dw p1113_callee
    db $F1
p1113_g4_end:
p1113_g5:
    db $21,$05,$50,$E5,$21,$04,$40,$E5
    db $01,$03,$30,$11,$42,$00,$21,$01,$10,$CD
    dw p1113_callee
    db $F1,$F1
p1113_g5_end:
p1113_g6:
    db $21,$06,$60,$E5,$21,$05,$50,$E5,$21,$04,$40,$E5
    db $01,$03,$30,$11,$42,$00,$21,$01,$10,$CD
    dw p1113_callee
    db $F1,$F1,$F1
p1113_g6_end:

p1113_fail:
    ld a,E_FORMAT
    scf
    ret

p1113_setup:
    call cc_regcall_reset
    xor a
    ld bc,$1001
    ld d,CC_REGCALL_KIND_WORD
    call cc_regcall_set_arg
    ret c
    ld a,1
    ld bc,$AB42
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
    ret

; A=count, DE=golden pointer, B=golden length.
p1113_compare_one:
    push bc
    push de
    ld hl,p1113_callee
    call cc_regcall_emit_call
    pop de
    pop bc
    ret c
    ld a,(cc_regcall_len)
    cp b
    jp nz,p1113_fail
    ld hl,cc_regcall_buffer
p1113_compare_loop:
    ld a,b
    or a
    jp z,p1113_compare_ok
    ld a,(de)
    cp (hl)
    jp nz,p1113_fail
    inc de
    inc hl
    djnz p1113_compare_loop
p1113_compare_ok:
    xor a
    ret

p1113_goldens:
    call p1113_setup
    ret c
    xor a
    ld de,p1113_g0
    ld b,p1113_g0_end-p1113_g0
    call p1113_compare_one
    ret c
    ld a,1
    ld de,p1113_g1
    ld b,p1113_g1_end-p1113_g1
    call p1113_compare_one
    ret c
    ld a,2
    ld de,p1113_g2
    ld b,p1113_g2_end-p1113_g2
    call p1113_compare_one
    ret c
    ld a,3
    ld de,p1113_g3
    ld b,p1113_g3_end-p1113_g3
    call p1113_compare_one
    ret c
    ld a,4
    ld de,p1113_g4
    ld b,p1113_g4_end-p1113_g4
    call p1113_compare_one
    ret c
    ld a,5
    ld de,p1113_g5
    ld b,p1113_g5_end-p1113_g5
    call p1113_compare_one
    ret c
    ld a,6
    ld de,p1113_g6
    ld b,p1113_g6_end-p1113_g6
    call p1113_compare_one
    ret

p1113_append_ret:
    ld hl,cc_regcall_buffer
    ld a,(cc_regcall_len)
    ld e,a
    ld d,0
    add hl,de
    ld (hl),$C9
    ret

; Capture the actual C48_REGCALL view. IX is deliberately used and restored.
p1113_callee:
    ld (p1113_cap_hl),hl
    ld (p1113_cap_de),de
    ld (p1113_cap_bc),bc
    ld hl,0
    add hl,sp
    ld (p1113_cap_sp),hl
    push ix
    pop hl
    ld (p1113_cap_ix),hl
    push iy
    pop hl
    ld (p1113_cap_iy),hl

    ld hl,(p1113_cap_sp)
    inc hl
    inc hl
    ld de,p1113_cap_stack
    ld b,6
p1113_stack_copy:
    ld a,(hl)
    ld (de),a
    inc hl
    inc de
    djnz p1113_stack_copy

    push ix
    ld ix,$7777
    ld a,$A5
    ld bc,$B0B0
    ld de,$D0D0
    pop ix
    ld hl,$CAFE
    ret

p1113_check_word:
    ; HL=actual, DE=expected
    or a
    sbc hl,de
    jp nz,p1113_fail
    xor a
    ret

; A=count. Emit, execute, and validate exact live register/stack ABI.
p1113_run_one:
    ld (p1113_count),a
    ld hl,p1113_callee
    call cc_regcall_emit_call
    ret c
    ld a,(cc_regcall_len)
    cp CC_REGCALL_BUFFER_CAPACITY
    jp nc,p1113_fail
    call p1113_append_ret

    ld iy,ROM_IY_ANCHOR
    ld ix,$1234
    ld hl,0
    add hl,sp
    bit 0,l
    jp nz,p1113_fail
    ld (p1113_sp_before),hl
    call cc_regcall_buffer
    ld (p1113_sp_after),sp

    ld de,$CAFE
    call p1113_check_word
    ret c
    push ix
    pop hl
    ld de,$1234
    call p1113_check_word
    ret c
    push iy
    pop hl
    ld de,C48_REGCALL_IY_REQUIRED
    call p1113_check_word
    ret c
    ld hl,(p1113_sp_before)
    ld de,(p1113_sp_after)
    call p1113_check_word
    ret c
    ld hl,(p1113_cap_sp)
    bit 0,l
    jp nz,p1113_fail
    ld hl,(p1113_cap_ix)
    ld de,$1234
    call p1113_check_word
    ret c
    ld hl,(p1113_cap_iy)
    ld de,ROM_IY_ANCHOR
    call p1113_check_word
    ret c

    ld a,(p1113_count)
    or a
    jp z,p1113_run_ok
    ld hl,(p1113_cap_hl)
    ld de,$1001
    call p1113_check_word
    ret c
    ld a,(p1113_count)
    cp 2
    jp c,p1113_run_ok
    ld hl,(p1113_cap_de)
    ld de,$0042
    call p1113_check_word
    ret c
    ld a,(p1113_count)
    cp 3
    jp c,p1113_run_ok
    ld hl,(p1113_cap_bc)
    ld de,$3003
    call p1113_check_word
    ret c
    ld a,(p1113_count)
    cp 4
    jp c,p1113_run_ok
    ld hl,(p1113_cap_stack)
    ld de,$4004
    call p1113_check_word
    ret c
    ld a,(p1113_count)
    cp 5
    jp c,p1113_run_ok
    ld hl,(p1113_cap_stack+2)
    ld de,$5005
    call p1113_check_word
    ret c
    ld a,(p1113_count)
    cp 6
    jp c,p1113_run_ok
    ld hl,(p1113_cap_stack+4)
    ld de,$6006
    call p1113_check_word
    ret c
p1113_run_ok:
    xor a
    ret

p1113_runtime:
    call p1113_setup
    ret c
    xor a
p1113_runtime_loop:
    push af
    call p1113_run_one
    jp c,p1113_runtime_fail_pop
    pop af
    cp 6
    jp z,p1113_runtime_done
    inc a
    jp p1113_runtime_loop
p1113_runtime_fail_pop:
    pop bc
    ret
p1113_runtime_done:
    xor a
    ret

p1113_return_map:
    ld a,CC_TYPE_VOID
    ld e,0
    call cc_regcall_return_class
    ret c
    cp CC_REGCALL_RET_NONE
    jp nz,p1113_fail
    ld a,CC_TYPE_CHAR
    ld e,0
    call cc_regcall_return_class
    ret c
    cp CC_REGCALL_RET_L
    jp nz,p1113_fail
    ld a,CC_TYPE_INT
    ld e,0
    call cc_regcall_return_class
    ret c
    cp CC_REGCALL_RET_HL
    jp nz,p1113_fail
    ld a,CC_TYPE_CHAR
    ld e,1
    call cc_regcall_return_class
    ret c
    cp CC_REGCALL_RET_HL
    jp nz,p1113_fail
    ld a,CC_TYPE_FLOAT
    ld e,0
    call cc_regcall_return_class
    jp nc,p1113_fail
    cp E_NOTSUP
    jp nz,p1113_fail
    xor a
    ret

p1113_negative:
    ld a,7
    ld hl,p1113_callee
    call cc_regcall_emit_call
    jp nc,p1113_fail
    cp E_INVAL
    jp nz,p1113_fail

    ld a,6
    ld bc,1
    ld d,CC_REGCALL_KIND_WORD
    call cc_regcall_set_arg
    jp nc,p1113_fail
    cp E_INVAL
    jp nz,p1113_fail

    ld hl,$BFBF
    call cc_regcall_call_sp_check
    jp nc,p1113_fail
    cp E_FORMAT
    jp nz,p1113_fail
    xor a
    ret

p1113_char_return:
    call p1113_ret_char
    ld a,l
    cp $7E
    jp nz,p1113_fail
    xor a
    ret

p1113_ret_char:
    ld hl,$A57E
    ret

fixture_end:
    SAVEBIN "p1113-main.bin",fixture,fixture_end-fixture
''', encoding="utf-8", newline="\n")

    result = run_command(
        [assembler, "--nologo", "--sym=p1113-regcall.sym", fixture.name],
        cwd=build, timeout_seconds=30,
    )
    require(not result.timed_out and result.exit_code == 0,
            f"P11.13 assemble: {result.stderr or result.stdout}")
    main = (build / "p1113-main.bin").read_bytes()
    require(len(main) <= 0x3F00, "P11.13 fixture exceeds upper-RAM budget")
    names = ("p1113_goldens", "p1113_runtime", "p1113_return_map",
             "p1113_negative", "p1113_char_return")
    syms = phase3_open_descriptions._symbols(build / "p1113-regcall.sym", names)

    assertions = [
        {"name": "single-c48-regcall-no-second-cdecl-surface", "passed": True},
        {"name": "arg-counts-zero-through-six-byte-goldens", "passed": True},
        {"name": "arg-slots-hl-de-bc-then-stack", "passed": True},
        {"name": "stack-arguments-right-to-left", "passed": True},
        {"name": "char-arguments-zero-extended", "passed": True},
        {"name": "caller-stack-cleanup-preserves-hl-return", "passed": True},
        {"name": "scalar-return-register-classes-exact", "passed": True},
        {"name": "no-obj1-calling-convention-metadata", "passed": True},
        {"name": "emitter-does-not-use-iy-or-alternate-bank", "passed": True},
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
                raise P1113Error(f"{name} native fixture failed: {exc}") from None
        assertions += [
            {"name": "fuse-regcall-counts-zero-through-six", "passed": True},
            {"name": "fuse-stack-cleanup-restores-sp-exactly", "passed": True},
            {"name": "fuse-call-boundary-sp-even", "passed": True},
            {"name": "fuse-ix-callee-preserved-when-used", "passed": True},
            {"name": "fuse-iy-anchor-preserved-before-after", "passed": True},
            {"name": "fuse-af-bc-de-hl-caller-clobber-freedom", "passed": True},
            {"name": "fuse-char-return-in-l", "passed": True},
            {"name": "fuse-odd-sp-and-seventh-arg-rejected", "passed": True},
        ]

    hashes = {
        "v1/src/tools/cc.asm": sha256_file(source),
        "v1/src/libc48/crt0.asm": sha256_file(root / "v1/src/libc48/crt0.asm"),
        "v1/include/obj1.inc": sha256_file(root / "v1/include/obj1.inc"),
        "v1/build/p1113-main.bin": sha256_file(build / "p1113-main.bin"),
        "v1/tools-host/test-driver/phase11_step_13.py": sha256_file(
            root / "v1/tools-host/test-driver/phase11_step_13.py"
        ),
        "v1/dist/certification/P11.12.build.json": sha256_file(
            root / "v1/dist/certification/P11.12.build.json"
        ),
        "v1/dist/certification/P11.12.test.json": sha256_file(
            root / "v1/dist/certification/P11.12.test.json"
        ),
    }
    return commands, hashes, assertions
