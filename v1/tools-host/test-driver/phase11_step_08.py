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


# P11.08 exact-candidate marker.
class P1108Error(DriverError):
    pass


def require(ok, message):
    if not ok:
        raise P1108Error(message)


def dispatch(root, action, step, *, sha256_file, run_command, require_project_tool):
    if step != "P11.08":
        raise DriverError(step)

    cc = root / "v1/src/tools/cc.asm"
    rt = root / "v1/src/libc48/int_runtime.asm"
    cc_text = cc.read_text(encoding="utf-8")
    rt_text = rt.read_text(encoding="utf-8")
    for marker in (
        "EMIT_P11_CC_INT_SEMANTICS", "CC_INT_SHIFT_MASK_8", "CC_INT_SHIFT_MASK_16",
        "CC_INT_RIGHT_LOGICAL", "CC_INT_RIGHT_ARITH", "cc_int_shift_mask_for_type:",
        "cc_int_is_signed_type:", "cc_int_right_shift_kind:", "cc_int_runtime_symbols:",
        "c48_u16_divmod", "c48_s16_divmod", "c48_s16_shr", "c48_u16_shr",
    ):
        require(marker in cc_text, f"P11.08 compiler integer contract missing: {marker}")
    for marker in (
        "EMIT_C48_INT_RUNTIME", "c48_u8_add:", "c48_u8_sub:", "c48_u8_mul:",
        "c48_u8_neg:", "c48_u8_shl:", "c48_u8_shr:", "c48_u16_add:",
        "c48_u16_sub:", "c48_u16_mul:", "c48_u16_neg:", "c48_u16_shl:",
        "c48_u16_shr:", "c48_s16_shr:", "c48_u16_divmod:",
        "c48_s16_divmod:", "c48_cmp_u8:", "c48_cmp_u16:", "c48_cmp_s16:",
        "c48_int_divzero:", "and 7", "and 15", "sra h", "srl h",
        "ld hl,1", "ld a,SYS_EXIT", "call SYSCALL_GATEWAY",
    ):
        require(marker in rt_text, f"P11.08 runtime integer contract missing: {marker}")
    require("sll " not in rt_text.lower(), "P11.08 undocumented SLL opcode forbidden")

    assembler = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    fixture = build / "p1108-integers.asm"
    fixture.write_text(r'''    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/tools/cc.asm"
    INCLUDE "../src/libc48/int_runtime.asm"
    ORG $C000
fixture:
    EMIT_P11_CC_STREAMING_CORE
    EMIT_P11_CC_LEXER
    EMIT_P11_CC_DECL_PARSER
    EMIT_P11_CC_INT_SEMANTICS
    EMIT_C48_INT_RUNTIME

p1108_fail:
    ld a,E_FORMAT
    scf
    ret

p1108_expect_hl:
    or a
    sbc hl,de
    jp nz,p1108_fail
    xor a
    ret

p1108_compiler:
    ld a,CC_TYPE_CHAR
    call cc_int_shift_mask_for_type
    ret c
    cp 7
    jp nz,p1108_fail
    ld a,CC_TYPE_UCHAR
    call cc_int_shift_mask_for_type
    ret c
    cp 7
    jp nz,p1108_fail
    ld a,CC_TYPE_SHORT
    call cc_int_shift_mask_for_type
    ret c
    cp 15
    jp nz,p1108_fail
    ld a,CC_TYPE_UINT
    call cc_int_shift_mask_for_type
    ret c
    cp 15
    jp nz,p1108_fail

    ld a,CC_TYPE_INT
    call cc_int_is_signed_type
    ret c
    cp 1
    jp nz,p1108_fail
    ld a,CC_TYPE_SHORT
    call cc_int_right_shift_kind
    ret c
    cp CC_INT_RIGHT_ARITH
    jp nz,p1108_fail
    ld a,CC_TYPE_UINT
    call cc_int_right_shift_kind
    ret c
    cp CC_INT_RIGHT_LOGICAL
    jp nz,p1108_fail
    ld a,CC_TYPE_FLOAT
    call cc_int_shift_mask_for_type
    jp nc,p1108_fail
    cp E_INVAL
    jp nz,p1108_fail
    xor a
    ret

p1108_wrap:
    ld l,$FF
    ld e,1
    call c48_u8_add
    ret c
    ld a,l
    or a
    jp nz,p1108_fail

    ld l,0
    ld e,1
    call c48_u8_sub
    ret c
    ld a,l
    cp $FF
    jp nz,p1108_fail

    ld l,$FF
    ld e,2
    call c48_u8_mul
    ret c
    ld a,l
    cp $FE
    jp nz,p1108_fail

    ld l,$80
    call c48_u8_neg
    ret c
    ld a,l
    cp $80
    jp nz,p1108_fail

    ld hl,$FFFF
    ld de,1
    call c48_u16_add
    ret c
    ld a,h
    or l
    jp nz,p1108_fail

    ld hl,0
    ld de,1
    call c48_u16_sub
    ret c
    ld de,$FFFF
    call p1108_expect_hl
    ret c

    ld hl,$8000
    ld de,2
    call c48_u16_mul
    ret c
    ld a,h
    or l
    jp nz,p1108_fail

    ld hl,$8000
    call c48_s16_neg
    ret c
    ld de,$8000
    call p1108_expect_hl
    ret c
    xor a
    ret

p1108_shifts:
    ld l,1
    ld e,0
    call c48_u8_shl
    ret c
    ld a,l
    cp 1
    jp nz,p1108_fail
    ld l,1
    ld e,7
    call c48_u8_shl
    ret c
    ld a,l
    cp 128
    jp nz,p1108_fail
    ld l,1
    ld e,8
    call c48_u8_shl
    ret c
    ld a,l
    cp 1
    jp nz,p1108_fail
    ld l,1
    ld e,15
    call c48_u8_shl
    ret c
    ld a,l
    cp 128
    jp nz,p1108_fail
    ld l,1
    ld e,255
    call c48_u8_shl
    ret c
    ld a,l
    cp 128
    jp nz,p1108_fail

    ld hl,1
    ld e,0
    call c48_u16_shl
    ret c
    ld de,1
    call p1108_expect_hl
    ret c
    ld hl,1
    ld e,15
    call c48_u16_shl
    ret c
    ld de,$8000
    call p1108_expect_hl
    ret c
    ld hl,1
    ld e,16
    call c48_u16_shl
    ret c
    ld de,1
    call p1108_expect_hl
    ret c
    ld hl,1
    ld e,31
    call c48_u16_shl
    ret c
    ld de,$8000
    call p1108_expect_hl
    ret c
    ld hl,1
    ld e,255
    call c48_u16_shl
    ret c
    ld de,$8000
    call p1108_expect_hl
    ret c

    ld hl,$FFFE
    ld e,1
    call c48_s16_shr
    ret c
    ld de,$FFFF
    call p1108_expect_hl
    ret c
    ld hl,$FFFF
    ld e,1
    call c48_u16_shr
    ret c
    ld de,$7FFF
    call p1108_expect_hl
    ret c
    xor a
    ret

p1108_division:
    ld hl,7
    ld de,3
    call c48_u16_divmod
    ret c
    ld a,h
    or a
    jp nz,p1108_fail
    ld a,l
    cp 2
    jp nz,p1108_fail
    ld a,d
    or a
    jp nz,p1108_fail
    ld a,e
    cp 1
    jp nz,p1108_fail

    ld hl,$FFF9
    ld de,3
    call c48_s16_divmod
    ret c
    push de
    ld de,$FFFE
    call p1108_expect_hl
    pop de
    ret c
    ld a,d
    cp $FF
    jp nz,p1108_fail
    ld a,e
    cp $FF
    jp nz,p1108_fail

    ld hl,7
    ld de,$FFFD
    call c48_s16_divmod
    ret c
    push de
    ld de,$FFFE
    call p1108_expect_hl
    pop de
    ret c
    ld a,d
    or a
    jp nz,p1108_fail
    ld a,e
    cp 1
    jp nz,p1108_fail

    ld hl,$8000
    ld de,$FFFF
    call c48_s16_divmod
    ret c
    push de
    ld de,$8000
    call p1108_expect_hl
    pop de
    ret c
    ld a,d
    or e
    jp nz,p1108_fail

    xor a
    ld (c48_int_runtime_exit_status),a
    ld hl,1
    ld de,0
    call c48_u16_divmod
    jp nc,p1108_fail
    ld a,(c48_int_runtime_exit_status)
    cp 1
    jp nz,p1108_fail
    ld a,($E020)
    cp SYS_EXIT
    jp nz,p1108_fail
    ld hl,($E021)
    ld de,1
    call p1108_expect_hl
    ret c
    xor a
    ret

p1108_compare:
    ld hl,$8000
    ld de,0
    call c48_cmp_s16
    cp $FF
    jp nz,p1108_fail
    ld hl,$8000
    ld de,$7FFF
    call c48_cmp_u16
    cp 1
    jp nz,p1108_fail
    ld hl,$FFFF
    ld de,1
    call c48_cmp_s16
    cp $FF
    jp nz,p1108_fail
    ld hl,$FFFF
    ld de,1
    call c48_cmp_u16
    cp 1
    jp nz,p1108_fail
    ld hl,$1234
    ld de,$1234
    call c48_cmp_u16
    or a
    jp nz,p1108_fail
    ld l,$80
    ld e,$7F
    call c48_cmp_u8
    cp 1
    jp nz,p1108_fail
    xor a
    ret

; Deliberately incorrect alternatives must be detected by the boundary oracle.
p1108_wrong_unmasked:
    ld l,1
    ld b,8
p1108_wrong_unmasked_loop:
    sla l
    djnz p1108_wrong_unmasked_loop
    ret

p1108_negative_oracle:
    call p1108_wrong_unmasked
    ld a,l
    or a
    jp nz,p1108_fail
    ; Correct masked count 8 must produce 1, proving the wrong fixture differs.
    ld l,1
    ld e,8
    call c48_u8_shl
    ret c
    ld a,l
    cp 1
    jp nz,p1108_fail

    ; Logical right shift is observably wrong for signed -2.
    ld hl,$FFFE
    ld e,1
    call c48_u16_shr
    ret c
    ld de,$7FFF
    call p1108_expect_hl
    ret c
    ld hl,$FFFE
    ld e,1
    call c48_s16_shr
    ret c
    ld de,$FFFF
    call p1108_expect_hl
    ret c

    ; A saturated non-wrapping result is not the frozen modulo result.
    ld hl,$FFFF
    ld de,1
    call c48_u16_add
    ret c
    ld a,h
    or l
    jp nz,p1108_fail
    xor a
    ret

p1108_all:
    call p1108_compiler
    ret c
    call p1108_wrap
    ret c
    call p1108_shifts
    ret c
    call p1108_division
    ret c
    call p1108_compare
    ret c
    call p1108_negative_oracle
    ret c
    xor a
    ret

fixture_end:
    SAVEBIN "p1108-main.bin",fixture,fixture_end-fixture
''', encoding="utf-8", newline="\n")

    result = run_command(
        [assembler, "--nologo", "--sym=p1108-integers.sym", fixture.name],
        cwd=build, timeout_seconds=30,
    )
    require(not result.timed_out and result.exit_code == 0,
            f"P11.08 assemble: {result.stderr or result.stdout}")
    main = (build / "p1108-main.bin").read_bytes()
    require(len(main) <= 0x3F00, "P11.08 fixture exceeds high-RAM SNA budget")
    syms = phase3_open_descriptions._symbols(
        build / "p1108-integers.sym",
        ("p1108_compiler", "p1108_wrap", "p1108_shifts", "p1108_division",
         "p1108_compare", "p1108_negative_oracle"),
    )

    assertions = [
        {"name": "compiler-width-mask-selection-native", "passed": True},
        {"name": "compiler-signed-right-shift-selection-native", "passed": True},
        {"name": "8-and-16-bit-modulo-runtime-native", "passed": True},
        {"name": "signed-division-remainder-runtime-native", "passed": True},
        {"name": "status1-divzero-runtime-path-native", "passed": True},
        {"name": "signed-unsigned-comparison-runtime-native", "passed": True},
        {"name": "documented-z80-shift-opcodes-only", "passed": True},
    ]
    commands = [result]
    if action == "test":
        def patch(ram):
            ram[0xC000 - 0x4000:0xC000 - 0x4000 + len(main)] = main
            # Isolated native oracle: capture SYS_EXIT A and HL, then return.
            gateway = bytes((0x32, 0x20, 0xE0, 0x22, 0x21, 0xE0, 0xC9))
            ram[0xE000 - 0x4000:0xE000 - 0x4000 + len(gateway)] = gateway

        for name in (
            "p1108_compiler", "p1108_wrap", "p1108_shifts", "p1108_division",
            "p1108_compare", "p1108_negative_oracle",
        ):
            code = (
                b"\xF3" + phase1._ld_sp(0xBFC0)
                + phase1._call(syms[name])
                + phase1._jp_c(FAIL_PC) + phase1._jp(PASS_PC)
            )
            try:
                commands.append(run_sna(root, code, patch=patch))
            except DriverError as exc:
                raise P1108Error(f"{name} native fixture failed: {exc}") from None
        assertions += [
            {"name": "fuse-modulo-width-add-sub-mul-neg", "passed": True},
            {"name": "fuse-8bit-shift-mask-0-7-8-15-255", "passed": True},
            {"name": "fuse-16bit-shift-mask-0-15-16-31-255", "passed": True},
            {"name": "fuse-signed-arithmetic-and-unsigned-logical-right-shift", "passed": True},
            {"name": "fuse-signed-division-truncates-toward-zero", "passed": True},
            {"name": "fuse-signed-remainder-has-dividend-sign", "passed": True},
            {"name": "fuse-int-min-div-minus-one-wrap-case", "passed": True},
            {"name": "fuse-divzero-status-one-sys-exit-gateway-path", "passed": True},
            {"name": "fuse-signed-unsigned-comparisons", "passed": True},
            {"name": "negative-unmasked-shift-and-signedness-oracles-detect-wrong-semantics", "passed": True},
        ]

    hashes = {
        "v1/src/tools/cc.asm": sha256_file(cc),
        "v1/src/libc48/int_runtime.asm": sha256_file(rt),
        "v1/build/p1108-main.bin": sha256_file(build / "p1108-main.bin"),
        "v1/tools-host/test-driver/phase11_step_08.py": sha256_file(
            root / "v1/tools-host/test-driver/phase11_step_08.py"
        ),
        "v1/dist/certification/P11.07.build.json": sha256_file(
            root / "v1/dist/certification/P11.07.build.json"
        ),
        "v1/dist/certification/P11.07.test.json": sha256_file(
            root / "v1/dist/certification/P11.07.test.json"
        ),
    }
    return commands, hashes, assertions
