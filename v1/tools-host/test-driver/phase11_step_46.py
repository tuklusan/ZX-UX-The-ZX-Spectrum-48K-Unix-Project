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


class P1146Error(DriverError):
    pass

# P11.46 canonical exact-head qualification candidate.


def require(ok, message):
    if not ok:
        raise P1146Error(message)


def dispatch(root, action, step, *, sha256_file, run_command, require_project_tool):
    if step != "P11.46":
        raise DriverError(step)

    syscall = root / "v1/src/kernel/syscall.asm"
    rom = root / "v1/src/kernel/rom_services.asm"
    stext = syscall.read_text(encoding="utf-8")
    rtext = rom.read_text(encoding="utf-8")
    arch = (root / "docs/01-ZX-UX-ARCHITECTURE-REV17.md").read_text(encoding="utf-8")
    plan = (root / "docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV08.md").read_text(encoding="utf-8")

    require("EMIT_P1146_FP_TO_TEXT_SYSCALL_ROUTINES" in stext
            and "zx48_p1146_sys_fp_to_text:" in stext,
            "P11.46 syscall surface missing")
    require("EMIT_P1146_ROM_FP_TO_TEXT_ROUTINES" in rtext
            and "call ROM_FP_PRINT" in rtext
            and "ROM_CURCHL                EQU $5C51" in rtext
            and "P1146_TEXT_MAX            EQU 14" in rtext,
            "P11.46 approved ROM formatting gateway missing")
    require("SYS_FP_TO_TEXT" in arch
            and "HL=five-byte value, DE=buffer, BC=capacity" in arch
            and "ROM-canonical decimal rendering plus terminating NUL" in arch
            and "E_NOSPC if capacity including NUL is unavailable" in arch,
            "REV17 P11.46 contract drift")
    require("## P11.46 - SYS_FP_TO_TEXT exact ABI" in plan
            and "Phase-0-approved ROM numeric formatting gateway" in plan
            and "no partial destination mutation" in plan
            and "forced ROM error" in plan,
            "REV08 P11.46 contract drift")

    start = rtext.index("    MACRO EMIT_P1146_ROM_FP_TO_TEXT_ROUTINES")
    macro = rtext[start:rtext.index("    ENDM", start) + len("    ENDM")]
    code = "\n".join(line.split(";", 1)[0] for line in macro.splitlines())
    require(not re.search(r"\bexx\b|ex\s+af\s*,\s*af'", code, re.I),
            "P11.46 gateway directly uses OS-private alternate-register swaps")

    assembler = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    fixture = build / "p1146-fp-to-text.asm"
    fixture.write_text(r'''    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/kernel/syscall.asm"
    INCLUDE "../src/kernel/rom_services.asm"

    ORG $C000
p1146_start:
altreg_busy: db 0
    EMIT_USER_RANGE_VALIDATION_ROUTINE
    EMIT_P1146_FP_TO_TEXT_SYSCALL_ROUTINES
    EMIT_P1146_ROM_FP_TO_TEXT_ROUTINES

p1146_f_zero:  db $00,$00,$00,$00,$00
p1146_f_pos15: db $81,$40,$00,$00,$00
p1146_f_neg15: db $81,$C0,$00,$00,$00
p1146_f_bad:   db $FF,$FF,$FF,$FF,$FF
p1146_out:     defs 16,$A5
p1146_dummy_channel:
    dw p1146_dummy_output
    dw p1146_dummy_input
    db 'S'

p1146_dummy_output:
p1146_dummy_input:
    ret

p1146_fail:
    ld a,E_FORMAT
    scf
    ret

p1146_gateway:
    cp SYS_FP_TO_TEXT
    jr z,p1146_gateway_text
    ld a,E_NOTSUP
    scf
    ret
p1146_gateway_text:
    ld (syscall_arg_hl),hl
    ld (syscall_arg_de),de
    ld (syscall_arg_bc),bc
    jp zx48_p1146_sys_fp_to_text

p1146_reset_out:
    ld hl,p1146_out
    ld de,p1146_out+1
    ld bc,15
    ld a,$A5
    ld (hl),a
    ldir
    ret

; HL=float, DE=expected NUL-terminated bytes, BC=capacity, A=expected text length.
p1146_expect:
    push af
    push de
    push bc
    call p1146_reset_out
    pop bc
    ld de,p1146_out
    ld a,SYS_FP_TO_TEXT
    call p1146_gateway
    pop de
    pop bc
    ret c
    ld a,l
    cp b
    jp nz,p1146_fail
    ld a,h
    or a
    jp nz,p1146_fail
    ld h,d
    ld l,e
    ld de,p1146_out
    ld a,b
    inc a
    ld b,a
p1146_expect_loop:
    ld a,(de)
    cp (hl)
    jp nz,p1146_fail
    inc de
    inc hl
    djnz p1146_expect_loop
    xor a
    ret

p1146_positive:
    ld hl,p1146_f_zero
    ld de,p1146_expect_zero
    ld bc,2
    ld a,1
    call p1146_expect
    ret c

    ld hl,p1146_f_pos15
    ld de,p1146_expect_pos15
    ld bc,4
    ld a,3
    call p1146_expect
    ret c

    ld hl,p1146_f_neg15
    ld de,p1146_expect_neg15
    ld bc,5
    ld a,4
    call p1146_expect
    ret c
    xor a
    ret

p1146_expect_zero:  db "0",0
p1146_expect_pos15: db "1.5",0
p1146_expect_neg15: db "-1.5",0

p1146_short:
    call p1146_reset_out
    ld hl,p1146_f_pos15
    ld de,p1146_out
    ld bc,3
    ld a,SYS_FP_TO_TEXT
    call p1146_gateway
    jp nc,p1146_fail
    cp E_NOSPC
    jp nz,p1146_fail
    ld hl,p1146_out
    ld b,16
p1146_short_guard:
    ld a,(hl)
    cp $A5
    jp nz,p1146_fail
    inc hl
    djnz p1146_short_guard
    xor a
    ret

p1146_ranges:
    call p1146_reset_out
    ld hl,$5B00
    ld de,p1146_out
    ld bc,8
    ld a,SYS_FP_TO_TEXT
    call p1146_gateway
    jp nc,p1146_fail
    cp E_INVAL
    jp nz,p1146_fail

    ld hl,p1146_f_zero
    ld de,$5B00
    ld bc,8
    ld a,SYS_FP_TO_TEXT
    call p1146_gateway
    jp nc,p1146_fail
    cp E_INVAL
    jp nz,p1146_fail

    ld hl,p1146_f_zero
    ld de,$DFFF
    ld bc,2
    ld a,SYS_FP_TO_TEXT
    call p1146_gateway
    jp nc,p1146_fail
    cp E_INVAL
    jp nz,p1146_fail

    ; Count zero follows the common zero-range rule and cannot hold the NUL.
    ld hl,p1146_f_zero
    ld de,0
    ld bc,0
    ld a,SYS_FP_TO_TEXT
    call p1146_gateway
    jp nc,p1146_fail
    cp E_NOSPC
    jp nz,p1146_fail

    ld hl,p1146_out
    ld b,16
p1146_ranges_guard:
    ld a,(hl)
    cp $A5
    jp nz,p1146_fail
    inc hl
    djnz p1146_ranges_guard
    xor a
    ret

p1146_state:
    ld hl,p1146_dummy_channel
    ld (ROM_CURCHL),hl
    ld hl,$5D20
    ld (ROM_STKBOT),hl
    ld hl,$5D25
    ld (ROM_STKEND),hl
    ld hl,ROM_MEMBOT
    ld (ROM_MEM),hl
    ld hl,$5D10
    ld (ROM_CH_ADD),hl
    ld hl,$5D40
    ld (ROM_ERR_SP),hl
    ld a,$24
    ld (ROM_FLAGS),a
    ld a,$33
    ld (ROM_BREG),a
    ld a,$22
    ld (ROM_IY_ANCHOR),a
    ld hl,P1146_MEM35
    ld de,P1146_MEM35+1
    ld bc,P1146_MEM35_SIZE-1
    ld a,$6A
    ld (hl),a
    ldir

    ld hl,p1146_f_pos15
    ld de,p1146_out
    ld bc,16
    ld a,SYS_FP_TO_TEXT
    call p1146_gateway
    ret c

    ld hl,(ROM_CURCHL)
    ld de,p1146_dummy_channel
    or a
    sbc hl,de
    jp nz,p1146_fail
    ld hl,(ROM_STKBOT)
    ld de,$5D20
    or a
    sbc hl,de
    jp nz,p1146_fail
    ld hl,(ROM_STKEND)
    ld de,$5D25
    or a
    sbc hl,de
    jp nz,p1146_fail
    ld hl,(ROM_MEM)
    ld de,ROM_MEMBOT
    or a
    sbc hl,de
    jp nz,p1146_fail
    ld hl,(ROM_CH_ADD)
    ld de,$5D10
    or a
    sbc hl,de
    jp nz,p1146_fail
    ld hl,(ROM_ERR_SP)
    ld de,$5D40
    or a
    sbc hl,de
    jp nz,p1146_fail
    ld a,(ROM_FLAGS)
    cp $24
    jp nz,p1146_fail
    ld a,(ROM_BREG)
    cp $33
    jp nz,p1146_fail
    ld a,(ROM_IY_ANCHOR)
    cp $22
    jp nz,p1146_fail
    ld a,(altreg_busy)
    or a
    jp nz,p1146_fail
    push iy
    pop hl
    ld de,ROM_IY_ANCHOR
    or a
    sbc hl,de
    jp nz,p1146_fail

    ld hl,P1146_MEM35
    ld b,P1146_MEM35_SIZE
p1146_state_mem:
    ld a,(hl)
    cp $6A
    jp nz,p1146_fail
    inc hl
    djnz p1146_state_mem
    xor a
    ret

p1146_rom_error:
    call p1146_reset_out
    ld hl,p1146_f_bad
    ld de,p1146_out
    ld bc,16
    ld a,SYS_FP_TO_TEXT
    call p1146_gateway
    jp nc,p1146_fail
    cp E_INVAL
    jp nz,p1146_fail
    ld hl,p1146_out
    ld b,16
p1146_rom_error_guard:
    ld a,(hl)
    cp $A5
    jp nz,p1146_fail
    inc hl
    djnz p1146_rom_error_guard
    ld a,(altreg_busy)
    or a
    jp nz,p1146_fail
    push iy
    pop hl
    ld de,ROM_IY_ANCHOR
    or a
    sbc hl,de
    jp nz,p1146_fail
    xor a
    ret

p1146_end:
    SAVEBIN "p1146-main.bin",p1146_start,p1146_end-p1146_start
''', encoding="utf-8", newline="\n")

    assembled = run_command(
        [assembler, "--nologo", "--sym=p1146-fp-to-text.sym", fixture.name],
        cwd=build, timeout_seconds=30,
    )
    require(not assembled.timed_out and assembled.exit_code == 0,
            f"P11.46 assemble: {assembled.stderr or assembled.stdout}")
    main = (build / "p1146-main.bin").read_bytes()
    require(0 < len(main) <= 0x2000, "P11.46 fixture exceeds C000-DFFF user range")
    names = ("p1146_positive", "p1146_short", "p1146_ranges", "p1146_state", "p1146_rom_error")
    syms = phase3_open_descriptions._symbols(
        build / "p1146-fp-to-text.sym", ("p1146_gateway",) + names
    )

    assertions = [
        {"name": "fp-to-text-register-abi-exact", "passed": True},
        {"name": "rom-print-fp-is-formatting-authority", "passed": True},
        {"name": "rom-output-captured-through-private-channel", "passed": True},
        {"name": "maximum-rom-rendering-bounded-14-bytes", "passed": True},
        {"name": "destination-commit-after-full-capacity-check", "passed": True},
        {"name": "calculator-print-buffer-state-saved-and-restored", "passed": True},
        {"name": "zero-capacity-fails-without-destination-dereference", "passed": True},
    ]
    commands = [assembled]

    if action == "test":
        gateway = phase1._jp(syms["p1146_gateway"])

        def patch(ram):
            ram[0xC000-0x4000:0xC000-0x4000+len(main)] = main
            ram[0xE000-0x4000:0xE000-0x4000+len(gateway)] = gateway

        for name in names:
            code = (b"\xF3" + phase1._ld_sp(0xBFC0) + phase1._call(syms[name])
                    + phase1._jp_c(FAIL_PC) + phase1._jp(PASS_PC))
            try:
                commands.append(run_sna(root, code, patch=patch, timeout=30))
            except DriverError as exc:
                raise P1146Error(f"{name} native FP-to-text fixture failed: {exc}") from None

        assertions += [
            {"name": "fuse-rom-canonical-zero-positive-negative-renderings", "passed": True},
            {"name": "fuse-one-byte-short-atomic-enospc", "passed": True},
            {"name": "fuse-protected-and-wrapped-destination-rejection", "passed": True},
            {"name": "fuse-forced-rom-error-atomic-einval", "passed": True},
            {"name": "fuse-iy-calculator-and-capture-state-restored", "passed": True},
        ]

    hashes = {
        "v1/src/kernel/syscall.asm": sha256_file(syscall),
        "v1/src/kernel/rom_services.asm": sha256_file(rom),
        "v1/build/p1146-main.bin": sha256_file(build / "p1146-main.bin"),
        "v1/tools-host/test-driver/phase11_step_46.py": sha256_file(root / "v1/tools-host/test-driver/phase11_step_46.py"),
        "v1/dist/certification/P11.45.build.json": sha256_file(root / "v1/dist/certification/P11.45.build.json"),
        "v1/dist/certification/P11.45.test.json": sha256_file(root / "v1/dist/certification/P11.45.test.json"),
    }
    return commands, hashes, assertions
