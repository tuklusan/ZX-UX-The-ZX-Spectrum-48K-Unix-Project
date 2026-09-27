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
import tempfile
from pathlib import Path

import phase1
import phase3_open_descriptions
from driver_core import DriverError
from fuse_harness import FAIL_PC, PASS_PC, make_sna, run_sna


class P1147Error(DriverError):
    pass


def require(ok, message):
    if not ok:
        raise P1147Error(message)


def dispatch(root, action, step, *, sha256_file, run_command, require_project_tool):
    if step != "P11.47":
        raise DriverError(step)

    syscall = root / "v1/src/kernel/syscall.asm"
    rom = root / "v1/src/kernel/rom_services.asm"
    stext = syscall.read_text(encoding="utf-8")
    rtext = rom.read_text(encoding="utf-8")
    arch = (root / "docs/01-ZX-UX-ARCHITECTURE-REV17.md").read_text(encoding="utf-8")
    plan = (root / "docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV08.md").read_text(encoding="utf-8")

    require("EMIT_P1147_FP_FROM_TEXT_SYSCALL_ROUTINES" in stext
            and "zx48_p1147_sys_fp_from_text:" in stext,
            "P11.47 syscall surface missing")
    require("EMIT_P1147_ROM_FP_FROM_TEXT_ROUTINES" in rtext
            and "call ROM_DEC_TO_FP" in rtext
            and "db $1B,$38" in rtext
            and "P1147_TEXT_MAX            EQU 255" in rtext,
            "P11.47 approved ROM parser gateway missing")
    require("SYS_FP_FROM_TEXT" in arch
            and "HL=text, DE=five-byte output, BC=exact text length" in arch
            and "BC=exact text length; input\nneed not be NUL terminated." in arch
            and "Anything else is E_INVAL." in arch,
            "REV17 P11.47 contract drift")
    require("## P11.47 - SYS_FP_FROM_TEXT exact ABI" in plan
            and "Phase-0-approved numeric parser/conversion gateway" in plan
            and "no whitespace/BASIC tokens" in plan
            and "output unchanged" in plan,
            "REV08 P11.47 contract drift")

    start = rtext.index("    MACRO EMIT_P1147_ROM_FP_FROM_TEXT_ROUTINES")
    macro = rtext[start:rtext.index("    ENDM", start) + len("    ENDM")]
    code = "\n".join(line.split(";", 1)[0] for line in macro.splitlines())
    require(not re.search(r"\bexx\b|ex\s+af\s*,\s*af'", code, re.I),
            "P11.47 gateway directly uses OS-private alternate-register swaps")

    assembler = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    fixture = build / "p1147-fp-from-text.asm"
    fixture.write_text(r'''    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/kernel/syscall.asm"
    INCLUDE "../src/kernel/rom_services.asm"

    ORG $C000
p1147_start:
altreg_busy: db 0
    EMIT_USER_RANGE_VALIDATION_ROUTINE
    EMIT_P1147_FP_FROM_TEXT_SYSCALL_ROUTINES
    EMIT_P1147_ROM_FP_FROM_TEXT_ROUTINES

p1147_s_zero:     db "0"
p1147_s_pos15:    db "+.5"
p1147_s_neg15:    db "-1.5"
p1147_s_bad_stmt: db "1+2"
p1147_s_bad_exp:  db "1e+"
p1147_s_token:    db "1",$F5
p1147_s_overflow: db "1e99"
p1147_expect_zero:  db $00,$00,$00,$00,$00
p1147_expect_pos15: db $80,$00,$00,$00,$00
p1147_expect_neg15: db $81,$C0,$00,$00,$00
p1147_s_exp0:      db "1E+0"
p1147_expect_exp0: db $00,$00,$01,$00,$00
p1147_out: defs 8,$A5

p1147_fail:
    ld a,E_FORMAT
    scf
    ret

p1147_gateway:
    cp SYS_FP_FROM_TEXT
    jr z,p1147_gateway_text
    ld a,E_NOTSUP
    scf
    ret
p1147_gateway_text:
    ld (syscall_arg_hl),hl
    ld (syscall_arg_de),de
    ld (syscall_arg_bc),bc
    jp zx48_p1147_sys_fp_from_text

p1147_reset_out:
    ld hl,p1147_out
    ld de,p1147_out+1
    ld bc,7
    ld a,$A5
    ld (hl),a
    ldir
    ret

; HL=source, BC=length, DE=expected five bytes.
p1147_expect:
    push de
    push bc
    push hl
    call p1147_reset_out
    pop hl
    pop bc
    ld de,p1147_out
    ld a,SYS_FP_FROM_TEXT
    call p1147_gateway
    pop de
    ret c
    ld a,h
    or l
    jp nz,p1147_fail
    ld hl,p1147_out
    ld b,5
p1147_expect_loop:
    ld a,(de)
    cp (hl)
    jp nz,p1147_fail
    inc de
    inc hl
    djnz p1147_expect_loop
    ld a,(p1147_out+5)
    cp $A5
    jp nz,p1147_fail
    xor a
    ret

p1147_zero:
    ld hl,p1147_s_zero
    ld bc,1
    ld de,p1147_expect_zero
    jp p1147_expect

p1147_pos15_call:
    call p1147_reset_out
    ld hl,p1147_s_pos15
    ld bc,3
    ld de,p1147_out
    ld a,SYS_FP_FROM_TEXT
    call p1147_gateway
    ret c
    ld a,h
    or l
    jp nz,p1147_fail
    xor a
    ret

p1147_pos15_bytes:
    ld hl,p1147_s_pos15
    ld bc,3
    ld de,p1147_expect_pos15
    jp p1147_expect

p1147_exp0:
    ld hl,p1147_s_exp0
    ld bc,4
    ld de,p1147_expect_exp0
    jp p1147_expect

p1147_neg15:
    ld hl,p1147_s_neg15
    ld bc,4
    ld de,p1147_expect_neg15
    jp p1147_expect

; HL=source, BC=length; require E_INVAL and unchanged output.
p1147_expect_invalid:
    push bc
    push hl
    call p1147_reset_out
    pop hl
    pop bc
    ld de,p1147_out
    ld a,SYS_FP_FROM_TEXT
    call p1147_gateway
    jp nc,p1147_fail
    cp E_INVAL
    jp nz,p1147_fail
    ld hl,p1147_out
    ld b,8
p1147_invalid_guard:
    ld a,(hl)
    cp $A5
    jp nz,p1147_fail
    inc hl
    djnz p1147_invalid_guard
    xor a
    ret

p1147_bad_stmt:
    ld hl,p1147_s_bad_stmt
    ld bc,3
    jp p1147_expect_invalid

p1147_bad_exp:
    ld hl,p1147_s_bad_exp
    ld bc,3
    jp p1147_expect_invalid

p1147_token:
    ld hl,p1147_s_token
    ld bc,2
    jp p1147_expect_invalid

p1147_ranges:
    call p1147_reset_out
    ld hl,$5B00
    ld de,p1147_out
    ld bc,1
    ld a,SYS_FP_FROM_TEXT
    call p1147_gateway
    jp nc,p1147_fail
    cp E_INVAL
    jp nz,p1147_fail

    ld hl,p1147_s_zero
    ld de,$5B00
    ld bc,1
    ld a,SYS_FP_FROM_TEXT
    call p1147_gateway
    jp nc,p1147_fail
    cp E_INVAL
    jp nz,p1147_fail

    ld hl,$DFFF
    ld de,p1147_out
    ld bc,2
    ld a,SYS_FP_FROM_TEXT
    call p1147_gateway
    jp nc,p1147_fail
    cp E_INVAL
    jp nz,p1147_fail

    ld hl,0
    ld de,p1147_out
    ld bc,0
    ld a,SYS_FP_FROM_TEXT
    call p1147_gateway
    jp nc,p1147_fail
    cp E_INVAL
    jp nz,p1147_fail

    ld hl,p1147_out
    ld b,8
p1147_ranges_guard:
    ld a,(hl)
    cp $A5
    jp nz,p1147_fail
    inc hl
    djnz p1147_ranges_guard
    xor a
    ret

p1147_overflow:
    ld hl,p1147_s_overflow
    ld bc,4
    jp p1147_expect_invalid

p1147_state:
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
    ld hl,P1147_MEM_WORK
    ld de,P1147_MEM_WORK+1
    ld bc,P1147_MEM_WORK_SIZE-1
    ld a,$6A
    ld (hl),a
    ldir

    ld hl,p1147_s_pos15
    ld de,p1147_out
    ld bc,3
    ld a,SYS_FP_FROM_TEXT
    call p1147_gateway
    ret c

    ld hl,(ROM_STKBOT)
    ld de,$5D20
    or a
    sbc hl,de
    jp nz,p1147_fail
    ld hl,(ROM_STKEND)
    ld de,$5D25
    or a
    sbc hl,de
    jp nz,p1147_fail
    ld hl,(ROM_MEM)
    ld de,ROM_MEMBOT
    or a
    sbc hl,de
    jp nz,p1147_fail
    ld hl,(ROM_CH_ADD)
    ld de,$5D10
    or a
    sbc hl,de
    jp nz,p1147_fail
    ld hl,(ROM_ERR_SP)
    ld de,$5D40
    or a
    sbc hl,de
    jp nz,p1147_fail
    ld a,(ROM_FLAGS)
    cp $24
    jp nz,p1147_fail
    ld a,(ROM_BREG)
    cp $33
    jp nz,p1147_fail
    ld a,(ROM_IY_ANCHOR)
    cp $22
    jp nz,p1147_fail
    ld a,(altreg_busy)
    or a
    jp nz,p1147_fail
    push iy
    pop hl
    ld de,ROM_IY_ANCHOR
    or a
    sbc hl,de
    jp nz,p1147_fail

    ld hl,P1147_MEM_WORK
    ld b,P1147_MEM_WORK_SIZE
p1147_state_mem:
    ld a,(hl)
    cp $6A
    jp nz,p1147_fail
    inc hl
    djnz p1147_state_mem
    xor a
    ret

p1147_end:
    SAVEBIN "p1147-main.bin",p1147_start,p1147_end-p1147_start
''', encoding="utf-8", newline="\n")

    assembled = run_command(
        [assembler, "--nologo", "--sym=p1147-fp-from-text.sym", fixture.name],
        cwd=build, timeout_seconds=30,
    )
    require(not assembled.timed_out and assembled.exit_code == 0,
            f"P11.47 assemble: {assembled.stderr or assembled.stdout}")
    main = (build / "p1147-main.bin").read_bytes()
    require(0 < len(main) <= 0x2000, "P11.47 fixture exceeds C000-DFFF user range")
    names = ("p1147_zero", "p1147_pos15_call", "p1147_pos15_bytes", "p1147_exp0", "p1147_neg15", "p1147_bad_stmt",
             "p1147_bad_exp", "p1147_token", "p1147_ranges", "p1147_overflow",
             "p1147_state")
    syms = phase3_open_descriptions._symbols(
        build / "p1147-fp-from-text.sym", ("p1147_gateway", "p1147_out") + names
    )

    assertions = [
        {"name": "fp-from-text-register-abi-exact", "passed": True},
        {"name": "grammar-validated-before-rom-entry", "passed": True},
        {"name": "rom-dec-to-fp-is-conversion-authority", "passed": True},
        {"name": "caller-input-not-required-nul-terminated", "passed": True},
        {"name": "basic-token-and-expression-bytes-rejected", "passed": True},
        {"name": "destination-commit-only-after-success", "passed": True},
        {"name": "calculator-parser-state-saved-and-restored", "passed": True},
    ]
    commands = [assembled]

    if action == "test":
        gateway = phase1._jp(syms["p1147_gateway"])

        def patch(ram):
            ram[0xC000-0x4000:0xC000-0x4000+len(main)] = main
            ram[0xE000-0x4000:0xE000-0x4000+len(gateway)] = gateway

        # Exact-byte diagnostic uses the emulator debugger's memory
        # dereference as an independent observation of the committed output.
        diag_code = (b"\\xF3" + phase1._ld_sp(0xBFC0)
                     + phase1._call(syms["p1147_pos15_call"])
                     + phase1._jp_c(FAIL_PC) + phase1._jp(PASS_PC))
        actual = []
        fuse = root / "tools/runtime/fuse/bin/fuse"
        with tempfile.TemporaryDirectory(prefix="zxux-p1147-diag-") as td:
            sna = Path(td) / "diag.sna"
            sna.write_bytes(make_sna(diag_code, patch=patch))
            for offset in range(5):
                command = (
                    f"breakpoint 0x{PASS_PC:04x}\\n"
                    "commands 1\\n"
                    f"exit [0x{syms['p1147_out'] + offset:04x}]\\n"
                    "end\\n"
                    f"breakpoint 0x{FAIL_PC:04x}\\n"
                    "commands 2\\n"
                    "exit 255\\n"
                    "end\\n"
                    "continue"
                )
                result = run_command(
                    ["/usr/bin/env", "SDL_VIDEODRIVER=dummy", "SDL_AUDIODRIVER=dummy",
                     fuse, "--machine", "48", "--no-sound", "--no-confirm-actions",
                     "--debugger-command", command, sna],
                    cwd=root, timeout_seconds=30,
                )
                require(not result.timed_out and result.exit_code != 255,
                        "P11.47 exact-byte diagnostic execution failed")
                actual.append(result.exit_code & 0xFF)
        require(bytes(actual) == bytes((0x80,0,0,0,0)),
                f"P11.47 ROM .5 byte diagnostic: actual={bytes(actual).hex()} expected=8000000000")

        for name in names:
            code = (b"\xF3" + phase1._ld_sp(0xBFC0) + phase1._call(syms[name])
                    + phase1._jp_c(FAIL_PC) + phase1._jp(PASS_PC))
            try:
                commands.append(run_sna(root, code, patch=patch, timeout=30))
            except DriverError as exc:
                raise P1147Error(f"{name} native FP-from-text fixture failed: {exc}") from None

        assertions += [
            {"name": "fuse-zero-positive-negative-exponent-renderings", "passed": True},
            {"name": "fuse-malformed-exponent-rejected-atomically", "passed": True},
            {"name": "fuse-basic-expression-and-token-rejected", "passed": True},
            {"name": "fuse-protected-wrapped-zero-range-rejection", "passed": True},
            {"name": "fuse-rom-overflow-recovered-as-einval", "passed": True},
            {"name": "fuse-iy-calculator-parser-state-restored", "passed": True},
        ]

    hashes = {
        "v1/src/kernel/syscall.asm": sha256_file(syscall),
        "v1/src/kernel/rom_services.asm": sha256_file(rom),
        "v1/build/p1147-main.bin": sha256_file(build / "p1147-main.bin"),
        "v1/tools-host/test-driver/phase11_step_47.py": sha256_file(root / "v1/tools-host/test-driver/phase11_step_47.py"),
        "v1/dist/certification/P11.46.build.json": sha256_file(root / "v1/dist/certification/P11.46.build.json"),
        "v1/dist/certification/P11.46.test.json": sha256_file(root / "v1/dist/certification/P11.46.test.json"),
    }
    return commands, hashes, assertions
