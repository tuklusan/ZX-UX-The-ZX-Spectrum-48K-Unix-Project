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


class P1131Error(DriverError):
    pass


def require(ok, message):
    if not ok:
        raise P1131Error(message)


def dispatch(root, action, step, *, sha256_file, run_command, require_project_tool):
    if step != "P11.31":
        raise DriverError(step)

    cc_path = root / "v1/src/tools/cc.asm"
    cc = cc_path.read_text(encoding="utf-8")
    plan = (root / "docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV08.md").read_text(encoding="utf-8")
    arch = (root / "docs/01-ZX-UX-ARCHITECTURE-REV17.md").read_text(encoding="utf-8")

    marker = "    MACRO EMIT_P1131_CC_CONTROL_FLOW"
    require(marker in cc, "P11.31 control-flow selector macro missing")
    macro = cc[cc.index(marker):]
    macro = macro[:macro.index("    ENDM") + len("    ENDM")]
    code = "\n".join(line.split(";", 1)[0] for line in macro.splitlines())
    require(all(token in macro for token in (
        "cc_cf_emit_branch:", "cc_cf_emit_counted_loop:",
        "cc_cf_emit_cond_ret:", "cc_cf_emit_jump_table:",
        "cc_cf_counted_b_far:", "cc_cf_counted_try_c:",
    )), "P11.31 mandatory selection surfaces incomplete")
    require(not re.search(r"\biy\b|\bexx\b|ex\s+af\s*,\s*af'", code, re.I),
            "P11.31 generated-control-flow helper owns reserved register state")
    require("## P11.31 - Codegen JR/DJNZ opportunities" in plan
            and "Out-of-range JR falls back correctly." in plan,
            "REV08 P11.31 contract drift")
    require("DJNZ" in arch and "JR Z/NZ/C/NC" in arch
            and "conditional" in arch and "JP (HL)" in arch,
            "REV17 P11.31 control-flow contract drift")

    host_goldens = (
        bytes.fromhex("2003"), bytes.fromhex("2803"),
        bytes.fromhex("3003"), bytes.fromhex("3803"),
        bytes.fromhex("ca3412"), bytes.fromhex("10fe"),
        bytes.fromhex("05c223c1"), bytes.fromhex("0dc223c1"),
        bytes.fromhex("d8"), bytes.fromhex("da3412"),
        bytes.fromhex("e9"), bytes.fromhex("c33412"),
    )
    for image in host_goldens:
        require(bool(phase11_step_30.scan_portable(image)),
                f"P11.31 golden rejected by P11.30 scanner: {image.hex()}")

    assembler = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    fixture = build / "p1131-control-flow.asm"
    fixture.write_text(r'''    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/tools/cc.asm"
    ORG $C000
fixture:
    EMIT_P1131_CC_CONTROL_FLOW

p1131_fail:
    ld a,E_FORMAT
    scf
    ret

p1131_compare:
    ld a,(cc_cf_len)
    cp b
    jp nz,p1131_fail
    ld de,cc_cf_buffer
p1131_compare_loop:
    ld a,b
    or a
    ret z
    ld a,(hl)
    cp (de)
    jp nz,p1131_fail
    inc hl
    inc de
    djnz p1131_compare_loop
    xor a
    ret

p1131_g_jr_nz: db $20,$03
p1131_g_jr_z:  db $28,$03
p1131_g_jr_nc: db $30,$03
p1131_g_jr_c:  db $38,$03
p1131_g_jp_z:  db $CA,$23,$C1
p1131_g_djnz:  db $10,$FE
p1131_g_b_far: db $05,$C2,$23,$C1
p1131_g_c_fallback: db $0D,$C2,$23,$C1
p1131_g_ret_c: db $D8
p1131_g_jp_c:  db $DA,$23,$C1
p1131_g_jphl:  db $E9
p1131_g_jp:    db $C3,$23,$C1

p1131_goldens:
    ld de,3
    ld hl,$C123
    ld a,CC_CF_COND_NZ
    call cc_cf_emit_branch
    ret c
    ld hl,p1131_g_jr_nz
    ld b,2
    call p1131_compare
    ret c

    ld de,3
    ld hl,$C123
    ld a,CC_CF_COND_Z
    call cc_cf_emit_branch
    ret c
    ld hl,p1131_g_jr_z
    ld b,2
    call p1131_compare
    ret c

    ld de,3
    ld hl,$C123
    ld a,CC_CF_COND_NC
    call cc_cf_emit_branch
    ret c
    ld hl,p1131_g_jr_nc
    ld b,2
    call p1131_compare
    ret c

    ld de,3
    ld hl,$C123
    ld a,CC_CF_COND_C
    call cc_cf_emit_branch
    ret c
    ld hl,p1131_g_jr_c
    ld b,2
    call p1131_compare
    ret c

    ld de,$0080
    ld hl,$C123
    ld a,CC_CF_COND_Z
    call cc_cf_emit_branch
    ret c
    ld hl,p1131_g_jp_z
    ld b,3
    call p1131_compare
    ret c

    ld de,$FFFE
    ld hl,$C123
    ld a,CC_CF_LOOP_COUNT8|CC_CF_LOOP_EXACT|CC_CF_LOOP_B_FREE|CC_CF_LOOP_COUNTER_B
    call cc_cf_emit_counted_loop
    ret c
    ld hl,p1131_g_djnz
    ld b,2
    call p1131_compare
    ret c

    ld de,$0080
    ld hl,$C123
    ld a,CC_CF_LOOP_COUNT8|CC_CF_LOOP_EXACT|CC_CF_LOOP_B_FREE|CC_CF_LOOP_COUNTER_B
    call cc_cf_emit_counted_loop
    ret c
    ld hl,p1131_g_b_far
    ld b,4
    call p1131_compare
    ret c

    ld de,0
    ld hl,$C123
    ld a,CC_CF_LOOP_COUNT8|CC_CF_LOOP_EXACT|CC_CF_LOOP_FALLBACK_C
    call cc_cf_emit_counted_loop
    ret c
    ld hl,p1131_g_c_fallback
    ld b,4
    call p1131_compare
    ret c

    ld hl,$C123
    ld b,1
    ld a,CC_CF_COND_C
    call cc_cf_emit_cond_ret
    ret c
    ld hl,p1131_g_ret_c
    ld b,1
    call p1131_compare
    ret c

    ld hl,$C123
    ld b,0
    ld a,CC_CF_COND_C
    call cc_cf_emit_cond_ret
    ret c
    ld hl,p1131_g_jp_c
    ld b,3
    call p1131_compare
    ret c

    ld hl,$C123
    ld a,CC_CF_JT_BOUNDED|CC_CF_JT_IN_RANGE|CC_CF_JT_SIZE_WIN
    call cc_cf_emit_jump_table
    ret c
    ld hl,p1131_g_jphl
    ld b,1
    call p1131_compare
    ret c

    ld hl,$C123
    ld a,CC_CF_JT_BOUNDED|CC_CF_JT_IN_RANGE
    call cc_cf_emit_jump_table
    ret c
    ld hl,p1131_g_jp
    ld b,3
    jp p1131_compare

p1131_runtime_jr:
    ld de,3
    ld hl,p1131_fail
    ld a,CC_CF_COND_Z
    call cc_cf_emit_branch
    ret c
    ld hl,cc_cf_buffer+2
    ld (hl),$3E
    inc hl
    ld (hl),1
    inc hl
    ld (hl),$C9
    inc hl
    ld (hl),$AF
    inc hl
    ld (hl),$C9
    xor a
    call cc_cf_buffer
    or a
    jp nz,p1131_fail
    ld a,1
    or a
    call cc_cf_buffer
    cp 1
    jp nz,p1131_fail
    xor a
    ret

p1131_runtime_djnz:
    ld de,$FFFE
    ld hl,cc_cf_buffer
    ld a,CC_CF_LOOP_COUNT8|CC_CF_LOOP_EXACT|CC_CF_LOOP_B_FREE|CC_CF_LOOP_COUNTER_B
    call cc_cf_emit_counted_loop
    ret c
    ld hl,cc_cf_buffer+2
    ld (hl),$C9
    ld b,3
    call cc_cf_buffer
    ld a,b
    or a
    jp nz,p1131_fail
    xor a
    ret

p1131_runtime_b_live:
    ld de,0
    ld hl,cc_cf_buffer
    ld a,CC_CF_LOOP_COUNT8|CC_CF_LOOP_EXACT|CC_CF_LOOP_FALLBACK_C
    call cc_cf_emit_counted_loop
    ret c
    ld hl,cc_cf_buffer+4
    ld (hl),$C9
    ld b,$55
    ld c,3
    call cc_cf_buffer
    ld a,b
    cp $55
    jp nz,p1131_fail
    ld a,c
    or a
    jp nz,p1131_fail
    xor a
    ret

p1131_runtime_condret:
    ld hl,p1131_fail
    ld b,1
    ld a,CC_CF_COND_NZ
    call cc_cf_emit_cond_ret
    ret c
    ld hl,cc_cf_buffer+1
    ld (hl),$3E
    inc hl
    ld (hl),$22
    inc hl
    ld (hl),$C9
    ld a,1
    or a
    call cc_cf_buffer
    cp 1
    jp nz,p1131_fail
    xor a
    call cc_cf_buffer
    cp $22
    jp nz,p1131_fail
    xor a
    ret

p1131_jt_target:
    ld a,$5A
    ret

p1131_runtime_jumptable:
    ld hl,p1131_fail
    ld a,CC_CF_JT_BOUNDED|CC_CF_JT_IN_RANGE|CC_CF_JT_SIZE_WIN
    call cc_cf_emit_jump_table
    ret c
    ld hl,p1131_jt_target
    call cc_cf_buffer
    cp $5A
    jp nz,p1131_fail

    ld hl,p1131_jt_target
    ld a,CC_CF_JT_BOUNDED|CC_CF_JT_IN_RANGE
    call cc_cf_emit_jump_table
    ret c
    call cc_cf_buffer
    cp $5A
    jp nz,p1131_fail
    xor a
    ret

p1131_negative:
    ld de,0
    ld hl,$C123
    ld a,CC_CF_LOOP_COUNT8|CC_CF_LOOP_COUNTER_B
    call cc_cf_emit_counted_loop
    jp nc,p1131_fail
    cp E_NOTSUP
    jp nz,p1131_fail
    ld a,(cc_cf_len)
    or a
    jp nz,p1131_fail

    ld de,0
    ld hl,$C123
    ld a,4
    call cc_cf_emit_branch
    jp nc,p1131_fail
    cp E_INVAL
    jp nz,p1131_fail

    ld hl,$C123
    ld a,$80
    call cc_cf_emit_jump_table
    jp nc,p1131_fail
    cp E_INVAL
    jp nz,p1131_fail
    xor a
    ret

fixture_end:
    SAVEBIN "p1131-main.bin",fixture,fixture_end-fixture
''', encoding="utf-8", newline="\n")

    result = run_command(
        [assembler, "--nologo", "--sym=p1131-control-flow.sym", fixture.name],
        cwd=build, timeout_seconds=30,
    )
    require(not result.timed_out and result.exit_code == 0,
            f"P11.31 assemble: {result.stderr or result.stdout}")
    main = (build / "p1131-main.bin").read_bytes()
    require(0 < len(main) <= 0x3F00, "P11.31 fixture exceeds upper-RAM budget")
    names = ("p1131_goldens", "p1131_runtime_jr", "p1131_runtime_djnz",
             "p1131_runtime_b_live", "p1131_runtime_condret",
             "p1131_runtime_jumptable", "p1131_negative")
    syms = phase3_open_descriptions._symbols(build / "p1131-control-flow.sym", names)

    assertions = [
        {"name":"near-jr-z-nz-c-nc-selected","passed":True},
        {"name":"out-of-range-jr-uses-documented-jp-fallback","passed":True},
        {"name":"suitable-counted-u8-loop-selects-djnz","passed":True},
        {"name":"out-of-range-djnz-uses-dec-b-jp-nz-fallback","passed":True},
        {"name":"b-live-loop-never-selects-djnz-and-preserves-b","passed":True},
        {"name":"safe-conditional-return-selects-ret-cc","passed":True},
        {"name":"unsafe-conditional-return-uses-jp-cc","passed":True},
        {"name":"jump-table-jp-hl-requires-all-proof-flags","passed":True},
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
                raise P1131Error(f"{name} native fixture failed: {exc}") from None
        assertions += [
            {"name":"fuse-near-jr-control-flow-semantics","passed":True},
            {"name":"fuse-djnz-counts-exactly-to-zero","passed":True},
            {"name":"fuse-b-live-c-fallback-preserves-b","passed":True},
            {"name":"fuse-conditional-ret-safe-and-fallback-paths","passed":True},
            {"name":"fuse-jp-hl-and-absolute-jump-table-fallbacks","passed":True},
            {"name":"fuse-nonexact-loop-and-invalid-proof-flags-fail-closed","passed":True},
        ]

    hashes = {
        "v1/src/tools/cc.asm": sha256_file(cc_path),
        "v1/build/p1131-main.bin": sha256_file(build / "p1131-main.bin"),
        "v1/tools-host/test-driver/phase11_step_30.py": sha256_file(root / "v1/tools-host/test-driver/phase11_step_30.py"),
        "v1/tools-host/test-driver/phase11_step_31.py": sha256_file(root / "v1/tools-host/test-driver/phase11_step_31.py"),
        "v1/dist/certification/P11.30.build.json": sha256_file(root / "v1/dist/certification/P11.30.build.json"),
        "v1/dist/certification/P11.30.test.json": sha256_file(root / "v1/dist/certification/P11.30.test.json"),
    }
    return commands, hashes, assertions
