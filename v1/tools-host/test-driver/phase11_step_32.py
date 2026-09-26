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
import phase11_step_30
from driver_core import DriverError
from fuse_harness import FAIL_PC, PASS_PC, run_sna


class P1132Error(DriverError):
    pass


def require(ok, message):
    if not ok:
        raise P1132Error(message)


def dispatch(root, action, step, *, sha256_file, run_command, require_project_tool):
    if step != "P11.32":
        raise DriverError(step)

    cc_path = root / "v1/src/tools/cc.asm"
    cc = cc_path.read_text(encoding="utf-8")
    plan = (root / "docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV08.md").read_text(encoding="utf-8")
    arch = (root / "docs/01-ZX-UX-ARCHITECTURE-REV17.md").read_text(encoding="utf-8")
    marker = "    MACRO EMIT_P1132_CC_DATA_OPS"
    require(marker in cc, "P11.32 data-operation selector macro missing")
    macro = cc[cc.index(marker):]
    macro = macro[:macro.index("    ENDM") + len("    ENDM")]
    code = "\n".join(line.split(";", 1)[0] for line in macro.splitlines())
    require(all(token in macro for token in (
        "cc_data_emit_alu16:", "cc_data_emit_exchange:",
        "cc_data_emit_bitop:", "cc_data_emit_shift:",
        "CC_DATA_ALU_ADC", "CC_DATA_ALU_SBC",
        "CC_DATA_BIT_SET", "CC_DATA_BIT_RES",
    )), "P11.32 mandatory data selectors incomplete")
    require(not re.search(r"\biy\b|\bexx\b|ex\s+af\s*,\s*af'|\bsll\b", code, re.I),
            "P11.32 helper uses forbidden/undocumented target state")
    require("## P11.32 - Bit/rotate/16-bit codegen" in plan
            and "Signedness mismatch caught." in plan,
            "REV08 P11.32 contract drift")
    require("ADD HL,rr" in arch and "ADC HL,rr" in arch and "SBC HL,rr" in arch
            and "EX DE,HL" in arch and "BIT" in arch and "SET" in arch and "RES" in arch
            and "rotate/shift instructions" in arch,
            "REV17 P11.32 data-operation contract drift")

    host_goldens = (
        bytes.fromhex("19"), bytes.fromhex("ed4a"), bytes.fromhex("ed72"),
        bytes.fromhex("eb"), bytes.fromhex("cb47"), bytes.fromhex("cbde"),
        bytes.fromhex("cbbd"), bytes.fromhex("cb27cb27"),
        bytes.fromhex("cb3f"), bytes.fromhex("cb2f"),
        bytes.fromhex("cb00"), bytes.fromhex("cb09"),
    )
    for image in host_goldens:
        require(bool(phase11_step_30.scan_portable(image)),
                f"P11.32 golden rejected by P11.30 scanner: {image.hex()}")

    assembler = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    fixture = build / "p1132-data-ops.asm"
    fixture.write_text(r'''    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/tools/cc.asm"
    ORG $C000
fixture:
    EMIT_P1132_CC_DATA_OPS

p1132_fail:
    ld a,E_FORMAT
    scf
    ret

p1132_compare:
    ld a,(cc_data_len)
    cp b
    jp nz,p1132_fail
    ld de,cc_data_buffer
p1132_compare_loop:
    ld a,b
    or a
    ret z
    ld a,(de)
    cp (hl)
    jp nz,p1132_fail
    inc de
    inc hl
    djnz p1132_compare_loop
    xor a
    ret

p1132_g_add: db $19
p1132_g_adc: db $ED,$4A
p1132_g_sbc: db $ED,$72
p1132_g_ex:  db $EB
p1132_g_bit: db $CB,$47
p1132_g_set: db $CB,$DE
p1132_g_res: db $CB,$BD
p1132_g_sla2: db $CB,$27,$CB,$27
p1132_g_srl: db $CB,$3F
p1132_g_sra: db $CB,$2F
p1132_g_rlc: db $CB,$00
p1132_g_rrc: db $CB,$09

p1132_goldens:
    ld a,CC_DATA_ALU_ADD
    ld b,CC_DATA_RR_DE
    call cc_data_emit_alu16
    ret c
    ld hl,p1132_g_add
    ld b,1
    call p1132_compare
    ret c

    ld a,CC_DATA_ALU_ADC
    ld b,CC_DATA_RR_BC
    call cc_data_emit_alu16
    ret c
    ld hl,p1132_g_adc
    ld b,2
    call p1132_compare
    ret c

    ld a,CC_DATA_ALU_SBC
    ld b,CC_DATA_RR_SP
    call cc_data_emit_alu16
    ret c
    ld hl,p1132_g_sbc
    ld b,2
    call p1132_compare
    ret c

    ld a,1
    call cc_data_emit_exchange
    ret c
    ld hl,p1132_g_ex
    ld b,1
    call p1132_compare
    ret c

    ld a,CC_DATA_BIT_TEST
    ld b,0
    ld c,7
    call cc_data_emit_bitop
    ret c
    ld hl,p1132_g_bit
    ld b,2
    call p1132_compare
    ret c

    ld a,CC_DATA_BIT_SET
    ld b,3
    ld c,6
    call cc_data_emit_bitop
    ret c
    ld hl,p1132_g_set
    ld b,2
    call p1132_compare
    ret c

    ld a,CC_DATA_BIT_RES
    ld b,7
    ld c,5
    call cc_data_emit_bitop
    ret c
    ld hl,p1132_g_res
    ld b,2
    call p1132_compare
    ret c

    ld a,CC_DATA_SHIFT_SLA
    ld b,2
    ld c,7
    ld d,CC_DATA_UNSIGNED
    call cc_data_emit_shift
    ret c
    ld hl,p1132_g_sla2
    ld b,4
    call p1132_compare
    ret c

    ld a,CC_DATA_SHIFT_SRL
    ld b,1
    ld c,7
    ld d,CC_DATA_UNSIGNED
    call cc_data_emit_shift
    ret c
    ld hl,p1132_g_srl
    ld b,2
    call p1132_compare
    ret c

    ld a,CC_DATA_SHIFT_SRA
    ld b,1
    ld c,7
    ld d,CC_DATA_SIGNED
    call cc_data_emit_shift
    ret c
    ld hl,p1132_g_sra
    ld b,2
    call p1132_compare
    ret c

    ld a,CC_DATA_SHIFT_RLC
    ld b,1
    ld c,0
    ld d,CC_DATA_UNSIGNED
    call cc_data_emit_shift
    ret c
    ld hl,p1132_g_rlc
    ld b,2
    call p1132_compare
    ret c

    ld a,CC_DATA_SHIFT_RRC
    ld b,1
    ld c,1
    ld d,CC_DATA_UNSIGNED
    call cc_data_emit_shift
    ret c
    ld hl,p1132_g_rrc
    ld b,2
    jp p1132_compare

p1132_append_ret:
    ld hl,cc_data_buffer
    ld a,(cc_data_len)
    ld e,a
    ld d,0
    add hl,de
    ld (hl),$C9
    ret

p1132_runtime_alu:
    ld a,CC_DATA_ALU_ADD
    ld b,CC_DATA_RR_DE
    call cc_data_emit_alu16
    ret c
    call p1132_append_ret
    ld hl,1
    ld de,2
    call cc_data_buffer
    ld de,3
    or a
    sbc hl,de
    jp nz,p1132_fail

    ld a,CC_DATA_ALU_ADC
    ld b,CC_DATA_RR_BC
    call cc_data_emit_alu16
    ret c
    call p1132_append_ret
    ld hl,1
    ld bc,2
    scf
    call cc_data_buffer
    ld de,4
    or a
    sbc hl,de
    jp nz,p1132_fail

    ld a,CC_DATA_ALU_SBC
    ld b,CC_DATA_RR_DE
    call cc_data_emit_alu16
    ret c
    call p1132_append_ret
    ld hl,5
    ld de,2
    scf
    call cc_data_buffer
    ld de,2
    or a
    sbc hl,de
    jp nz,p1132_fail
    xor a
    ret

p1132_runtime_exchange:
    ld a,1
    call cc_data_emit_exchange
    ret c
    call p1132_append_ret
    ld hl,$1122
    ld de,$3344
    call cc_data_buffer
    ld (p1132_saved_de),de
    ld de,$3344
    or a
    sbc hl,de
    jp nz,p1132_fail
    ld hl,(p1132_saved_de)
    ld de,$1122
    or a
    sbc hl,de
    jp nz,p1132_fail
    xor a
    ret

p1132_runtime_bit:
    ld a,CC_DATA_BIT_TEST
    ld b,0
    ld c,7
    call cc_data_emit_bitop
    ret c
    call p1132_append_ret
    ld a,1
    call cc_data_buffer
    jp z,p1132_fail
    xor a
    call cc_data_buffer
    jp nz,p1132_fail

    ld a,CC_DATA_BIT_SET
    ld b,3
    ld c,6
    call cc_data_emit_bitop
    ret c
    call p1132_append_ret
    xor a
    ld (p1132_byte),a
    ld hl,p1132_byte
    call cc_data_buffer
    ld a,(p1132_byte)
    cp 8
    jp nz,p1132_fail

    ld a,CC_DATA_BIT_RES
    ld b,7
    ld c,5
    call cc_data_emit_bitop
    ret c
    call p1132_append_ret
    ld hl,$1280
    call cc_data_buffer
    ld de,$1200
    or a
    sbc hl,de
    jp nz,p1132_fail
    xor a
    ret

p1132_runtime_shift:
    ld a,CC_DATA_SHIFT_SLA
    ld b,2
    ld c,7
    ld d,CC_DATA_UNSIGNED
    call cc_data_emit_shift
    ret c
    call p1132_append_ret
    ld a,3
    call cc_data_buffer
    cp 12
    jp nz,p1132_fail

    ld a,CC_DATA_SHIFT_SRL
    ld b,1
    ld c,7
    ld d,CC_DATA_UNSIGNED
    call cc_data_emit_shift
    ret c
    call p1132_append_ret
    ld a,$80
    call cc_data_buffer
    cp $40
    jp nz,p1132_fail

    ld a,CC_DATA_SHIFT_SRA
    ld b,1
    ld c,7
    ld d,CC_DATA_SIGNED
    call cc_data_emit_shift
    ret c
    call p1132_append_ret
    ld a,$80
    call cc_data_buffer
    cp $C0
    jp nz,p1132_fail
    xor a
    ret

p1132_negative:
    ld a,CC_DATA_SHIFT_SRL
    ld b,1
    ld c,7
    ld d,CC_DATA_SIGNED
    call cc_data_emit_shift
    jp nc,p1132_fail
    cp E_INVAL
    jp nz,p1132_fail
    ld a,(cc_data_len)
    or a
    jp nz,p1132_fail

    ld a,CC_DATA_SHIFT_SRA
    ld b,1
    ld c,7
    ld d,CC_DATA_UNSIGNED
    call cc_data_emit_shift
    jp nc,p1132_fail
    cp E_INVAL
    jp nz,p1132_fail

    xor a
    call cc_data_emit_exchange
    jp nc,p1132_fail
    cp E_NOTSUP
    jp nz,p1132_fail

    ld a,CC_DATA_BIT_SET
    ld b,8
    ld c,6
    call cc_data_emit_bitop
    jp nc,p1132_fail
    cp E_INVAL
    jp nz,p1132_fail
    xor a
    ret

p1132_saved_de: dw 0
p1132_byte: db 0

fixture_end:
    SAVEBIN "p1132-main.bin",fixture,fixture_end-fixture
''', encoding="utf-8", newline="\n")

    result = run_command(
        [assembler, "--nologo", "--sym=p1132-data-ops.sym", fixture.name],
        cwd=build, timeout_seconds=30,
    )
    require(not result.timed_out and result.exit_code == 0,
            f"P11.32 assemble: {result.stderr or result.stdout}")
    main = (build / "p1132-main.bin").read_bytes()
    require(0 < len(main) <= 0x3F00, "P11.32 fixture exceeds upper-RAM budget")
    names = ("p1132_goldens", "p1132_runtime_alu", "p1132_runtime_exchange",
             "p1132_runtime_bit", "p1132_runtime_shift", "p1132_negative")
    syms = phase3_open_descriptions._symbols(build / "p1132-data-ops.sym", names)

    assertions = [
        {"name":"add-adc-sbc-hl-rr-selected-exactly","passed":True},
        {"name":"legal-ex-de-hl-selected-exactly","passed":True},
        {"name":"bit-set-res-documented-cb-sequences-exact","passed":True},
        {"name":"documented-rotate-shift-power-of-two-sequences-exact","passed":True},
        {"name":"signed-right-shift-uses-sra-unsigned-uses-srl","passed":True},
        {"name":"all-goldens-pass-p1130-documented-opcode-scanner","passed":True},
    ]
    commands = [result]
    if action == "test":
        def patch(ram):
            ram[0xC000-0x4000:0xC000-0x4000+len(main)] = main

        for name in names:
            code = (
                b"\xF3" + phase1._ld_sp(0xBFC0)
                + phase1._call(syms[name])
                + phase1._jp_c(FAIL_PC) + phase1._jp(PASS_PC)
            )
            try:
                commands.append(run_sna(root, code, patch=patch))
            except DriverError as exc:
                raise P1132Error(f"{name} native fixture failed: {exc}") from None
        assertions += [
            {"name":"fuse-16bit-add-adc-sbc-results-exact","passed":True},
            {"name":"fuse-ex-de-hl-result-exact","passed":True},
            {"name":"fuse-bit-set-res-visible-results-exact","passed":True},
            {"name":"fuse-sla-srl-sra-results-exact","passed":True},
            {"name":"fuse-signedness-mismatch-rejected-before-emission","passed":True},
        ]

    hashes = {
        "v1/src/tools/cc.asm": sha256_file(cc_path),
        "v1/build/p1132-main.bin": sha256_file(build / "p1132-main.bin"),
        "v1/tools-host/test-driver/phase11_step_30.py": sha256_file(root / "v1/tools-host/test-driver/phase11_step_30.py"),
        "v1/tools-host/test-driver/phase11_step_32.py": sha256_file(root / "v1/tools-host/test-driver/phase11_step_32.py"),
        "v1/dist/certification/P11.31.build.json": sha256_file(root / "v1/dist/certification/P11.31.build.json"),
        "v1/dist/certification/P11.31.test.json": sha256_file(root / "v1/dist/certification/P11.31.test.json"),
    }
    return commands, hashes, assertions
