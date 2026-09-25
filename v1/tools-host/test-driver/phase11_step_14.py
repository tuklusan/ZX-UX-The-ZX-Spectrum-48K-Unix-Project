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


class P1114Error(DriverError):
    pass


def require(ok, message):
    if not ok:
        raise P1114Error(message)


def dispatch(root, action, step, *, sha256_file, run_command, require_project_tool):
    if step != "P11.14":
        raise DriverError(step)

    source = root / "v1/src/tools/cc.asm"
    bridge = root / "v1/src/libc48/float_bridge.asm"
    text = source.read_text(encoding="utf-8")
    btext = bridge.read_text(encoding="utf-8")
    arch = (root / "docs/01-ZX-UX-ARCHITECTURE-REV17.md").read_text(encoding="utf-8")
    plan = (root / "docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV08.md").read_text(encoding="utf-8")
    markers = (
        "EMIT_P11_CC_FLOAT5",
        "CC_FLOAT5_SIZE           EQU 5",
        "CC_FLOAT5_ALIGN          EQU 1",
        "cc_float5_from_text:",
        "SYS_FP_FROM_TEXT",
        "compiler/c48/float5.py",
        "84d144de2721cda5075c3a6610a422663b5e2f77",
    )
    require(all(m in text for m in markers), "P11.14 compiler float5 surface incomplete")
    require("EMIT_P11_C48_FLOAT5_BRIDGE" in btext and
            "C48_FLOAT_SIZE           EQU 5" in btext and
            "C48_FLOAT_ALIGN          EQU 1" in btext,
            "P11.14 libc48 float bridge incomplete")
    require("float                   5         1" in arch and
            "C48 `float` is intentionally a platform-native five-byte type." in arch and
            "It is not an\nIEEE-754 32-bit `float`." in arch,
            "REV17 P11.14 representation contract drift")
    require("## P11.14 - Five-byte float representation" in plan and
            "Known values bytes equal ROM conversions." in plan and
            "4-byte float assumption fails ABI test." in plan,
            "REV08 P11.14 acceptance contract drift")

    assembler = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    fixture = build / "p1114-float5.asm"
    fixture.write_text(r'''    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/kernel/rom_services.asm"
    INCLUDE "../src/tools/cc.asm"
    INCLUDE "../src/libc48/float_bridge.asm"

    ORG $C000
p1114_start:
    EMIT_P11_CC_FLOAT5
    EMIT_P11_C48_FLOAT5_BRIDGE

p1114_lit_0:     db "0",0
p1114_lit_0_end:
p1114_lit_1:     db "1",0
p1114_lit_1_end:
p1114_lit_n1:    db "-1",0
p1114_lit_n1_end:
p1114_lit_half:  db "0.5",0
p1114_lit_half_end:
p1114_lit_15:    db "1.5",0
p1114_lit_15_end:
p1114_lit_maxu:  db "65535",0
p1114_lit_maxu_end:

p1114_exp_0:     db $00,$00,$00,$00,$00
p1114_exp_1:     db $00,$00,$01,$00,$00
p1114_exp_n1:    db $00,$FF,$FF,$FF,$00
p1114_exp_half:  db $80,$00,$00,$00,$00
p1114_exp_15:    db $81,$40,$00,$00,$00
p1114_exp_maxu:  db $00,$00,$FF,$FF,$00

p1114_out:       defs 6,$A5
p1114_copy:      defs 6,$5A

p1114_fail:
    ld a,E_FORMAT
    scf
    ret

; HL=literal, BC=visible length, DE=expected bytes.
p1114_one:
    push de
    ld de,p1114_out
    call cc_float5_from_text
    pop de
    ret c
    ld hl,p1114_out
    ld b,5
p1114_cmp:
    ld a,(de)
    cp (hl)
    jp nz,p1114_fail
    inc de
    inc hl
    djnz p1114_cmp
    xor a
    ret

p1114_known:
    ld hl,p1114_lit_0
    ld bc,p1114_lit_0_end-p1114_lit_0-1
    ld de,p1114_exp_0
    call p1114_one
    ret c
    ld hl,p1114_lit_1
    ld bc,p1114_lit_1_end-p1114_lit_1-1
    ld de,p1114_exp_1
    call p1114_one
    ret c
    ld hl,p1114_lit_half
    ld bc,p1114_lit_half_end-p1114_lit_half-1
    ld de,p1114_exp_half
    call p1114_one
    ret c
    ld hl,p1114_lit_15
    ld bc,p1114_lit_15_end-p1114_lit_15-1
    ld de,p1114_exp_15
    call p1114_one
    ret c
    ld hl,p1114_lit_maxu
    ld bc,p1114_lit_maxu_end-p1114_lit_maxu-1
    ld de,p1114_exp_maxu
    call p1114_one
    ret

p1114_copy_exact:
    ld hl,p1114_exp_15
    ld de,p1114_copy
    call cc_float5_copy
    ret c
    ld hl,p1114_copy
    ld de,p1114_exp_15
    ld b,5
p1114_copy_cmp:
    ld a,(de)
    cp (hl)
    jp nz,p1114_fail
    inc de
    inc hl
    djnz p1114_copy_cmp
    ld a,(p1114_copy+5)
    cp $5A
    jp nz,p1114_fail

    ld hl,p1114_exp_n1
    ld de,p1114_copy
    call c48_float_copy5
    ret c
    ld a,(p1114_copy+5)
    cp $5A
    jp nz,p1114_fail
    xor a
    ret

p1114_width:
    ld a,5
    call cc_float5_require_size
    ret c
    ld a,5
    call c48_float_require_size
    ret c
    ld a,4
    call cc_float5_require_size
    jp nc,p1114_fail
    cp E_FORMAT
    jp nz,p1114_fail
    ld a,4
    call c48_float_require_size
    jp nc,p1114_fail
    cp E_FORMAT
    jp nz,p1114_fail
    xor a
    ret

p1114_end:
    SAVEBIN "p1114-main.bin",p1114_start,p1114_end-p1114_start

    ORG $D000
p1114_rom_start:
altreg_busy: db 0
    EMIT_P710_ROM_CALC_ROUTINES
p1114_rom_end:
    SAVEBIN "p1114-rom.bin",p1114_rom_start,p1114_rom_end-p1114_rom_start

    ORG $E000
p1114_gateway:
    cp SYS_FP_FROM_TEXT
    jr nz,p1114_gateway_bad
    jp zx48_rom_decimal_literal
p1114_gateway_bad:
    ld a,E_NOTSUP
    scf
    ret
p1114_gateway_end:
    SAVEBIN "p1114-gateway.bin",p1114_gateway,p1114_gateway_end-p1114_gateway
''', encoding="utf-8", newline="\n")

    result = run_command(
        [assembler, "--nologo", "--sym=p1114-float5.sym", fixture.name],
        cwd=build, timeout_seconds=30,
    )
    require(not result.timed_out and result.exit_code == 0,
            f"P11.14 assemble: {result.stderr or result.stdout}")
    main = (build / "p1114-main.bin").read_bytes()
    rom = (build / "p1114-rom.bin").read_bytes()
    gateway = (build / "p1114-gateway.bin").read_bytes()
    require(len(main) < 0x1000 and len(rom) < 0x1000 and len(gateway) < 0x0100,
            "P11.14 fixture segment budget exceeded")
    names = ("p1114_known", "p1114_copy_exact", "p1114_width")
    syms = phase3_open_descriptions._symbols(build / "p1114-float5.sym", names)

    assertions = [
        {"name": "c48-float-size-exactly-five", "passed": True},
        {"name": "c48-float-alignment-exactly-one", "passed": True},
        {"name": "compiler-literal-conversion-uses-sys-fp-from-text", "passed": True},
        {"name": "libc48-copy-is-exactly-five-bytes", "passed": True},
        {"name": "sdk-float5-oracle-mapping-recorded", "passed": True},
        {"name": "no-ieee-binary32-float-abi", "passed": True},
    ]
    commands = [result]
    if action == "test":
        def patch(ram):
            ram[0xC000 - 0x4000:0xC000 - 0x4000 + len(main)] = main
            ram[0xD000 - 0x4000:0xD000 - 0x4000 + len(rom)] = rom
            ram[0xE000 - 0x4000:0xE000 - 0x4000 + len(gateway)] = gateway

        for name in names:
            code = (
                b"\xF3" + phase1._ld_sp(0xBFC0)
                + phase1._call(syms[name])
                + phase1._jp_c(FAIL_PC) + phase1._jp(PASS_PC)
            )
            try:
                commands.append(run_sna(root, code, patch=patch, timeout=20.0))
            except DriverError as exc:
                raise P1114Error(f"{name} native fixture failed: {exc}") from None
        assertions += [
            {"name": "fuse-rom-zero-bytes-0000000000", "passed": True},
            {"name": "fuse-rom-one-integer-form-0000010000", "passed": True},
            {"name": "fuse-rom-half-bytes-8000000000", "passed": True},
            {"name": "fuse-rom-one-point-five-bytes-8140000000", "passed": True},
            {"name": "fuse-rom-65535-integer-form-0000ffff00", "passed": True},
            {"name": "fuse-four-byte-float-assumption-rejected", "passed": True},
            {"name": "fuse-copy-does-not-touch-sixth-byte", "passed": True},
        ]

    hashes = {
        "v1/src/tools/cc.asm": sha256_file(source),
        "v1/src/libc48/float_bridge.asm": sha256_file(bridge),
        "v1/build/p1114-main.bin": sha256_file(build / "p1114-main.bin"),
        "v1/build/p1114-rom.bin": sha256_file(build / "p1114-rom.bin"),
        "v1/build/p1114-gateway.bin": sha256_file(build / "p1114-gateway.bin"),
        "v1/tools-host/test-driver/phase11_step_14.py": sha256_file(
            root / "v1/tools-host/test-driver/phase11_step_14.py"
        ),
        "v1/dist/certification/P11.13.build.json": sha256_file(
            root / "v1/dist/certification/P11.13.build.json"
        ),
        "v1/dist/certification/P11.13.test.json": sha256_file(
            root / "v1/dist/certification/P11.13.test.json"
        ),
    }
    return commands, hashes, assertions
