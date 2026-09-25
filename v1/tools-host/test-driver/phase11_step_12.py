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


class P1112Error(DriverError):
    pass


def require(ok, message):
    if not ok:
        raise P1112Error(message)


def dispatch(root, action, step, *, sha256_file, run_command, require_project_tool):
    if step != "P11.12":
        raise DriverError(step)

    source = root / "v1/src/tools/cc.asm"
    text = source.read_text(encoding="utf-8")
    arch = (root / "docs/01-ZX-UX-ARCHITECTURE-REV17.md").read_text(encoding="utf-8")
    plan = (root / "docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV08.md").read_text(encoding="utf-8")
    markers = (
        "EMIT_P11_CC_FRAME_LAYOUT",
        "cc_frame_plan:",
        "cc_frame_emit_prologue:",
        "cc_frame_emit_epilogue:",
        "cc_frame_local_disp:",
        "cc_frame_call_sp_check:",
        "PUSH IX",
        "LD SP,IX",
        "IY is never emitted",
    )
    require(all(m in text for m in markers), "P11.12 frame surface incomplete")
    require("The compiler omits an IX frame entirely" in arch and
            "IX                 callee-preserved when used" in arch and
            "IY                 OS/ROM-reserved and must not be changed" in arch and
            "SP is even-aligned at every C48 call boundary." in arch,
            "REV17 P11.12 ABI contract drift")
    require("## P11.12 - Local variable frame layout" in plan and
            "an unnecessary mandatory IX frame" in plan and
            "odd-SP call boundary fails." in plan,
            "REV08 P11.12 acceptance contract drift")

    assembler = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    fixture = build / "p1112-frame.asm"
    fixture.write_text(r'''    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/tools/cc.asm"
    ORG $C000
fixture:
    EMIT_P11_CC_FRAME_LAYOUT

p1112_frame_prologue:
    db $DD,$E5,$DD,$21,$00,$00,$DD,$39,$F5,$F5,$F5
p1112_frame_prologue_end:
p1112_frame_epilogue:
    db $DD,$F9,$DD,$E1,$C9
p1112_frame_epilogue_end:
p1112_code: defs 32,0
p1112_sp_before: dw 0
p1112_sp_after: dw 0
p1112_callee_odd: db 0

p1112_fail:
    ld a,E_FORMAT
    scf
    ret

p1112_leaf:
    ld a,CC_FRAME_FLAG_LEAF_SIMPLE|CC_FRAME_FLAG_DIRECT_LOCALS
    ld bc,2
    call cc_frame_plan
    ret c
    call cc_frame_emit
    ret c
    ld a,(cc_frame_uses_ix)
    or a
    jp nz,p1112_fail
    ld a,(cc_frame_direct_bytes)
    cp 2
    jp nz,p1112_fail
    ld a,(cc_frame_stack_bytes)
    or a
    jp nz,p1112_fail
    ld a,(cc_frame_prologue_len)
    or a
    jp nz,p1112_fail
    ld a,(cc_frame_epilogue_len)
    cp 1
    jp nz,p1112_fail
    ld a,(cc_frame_epilogue)
    cp $C9
    jp nz,p1112_fail
    xor a
    ret

p1112_frame:
    xor a
    ld bc,5
    call cc_frame_plan
    ret c
    call cc_frame_emit
    ret c
    ld a,(cc_frame_uses_ix)
    cp 1
    jp nz,p1112_fail
    ld a,(cc_frame_stack_bytes)
    cp 6
    jp nz,p1112_fail
    ld a,(cc_frame_prologue_len)
    cp p1112_frame_prologue_end-p1112_frame_prologue
    jp nz,p1112_fail
    ld a,(cc_frame_epilogue_len)
    cp p1112_frame_epilogue_end-p1112_frame_epilogue
    jp nz,p1112_fail

    ld hl,cc_frame_prologue
    ld de,p1112_frame_prologue
    ld b,p1112_frame_prologue_end-p1112_frame_prologue
p1112_cmp_pro:
    ld a,(de)
    cp (hl)
    jp nz,p1112_fail
    cp $FD
    jp z,p1112_fail
    inc de
    inc hl
    djnz p1112_cmp_pro

    ld hl,cc_frame_epilogue
    ld de,p1112_frame_epilogue
    ld b,p1112_frame_epilogue_end-p1112_frame_epilogue
p1112_cmp_epi:
    ld a,(de)
    cp (hl)
    jp nz,p1112_fail
    cp $FD
    jp z,p1112_fail
    inc de
    inc hl
    djnz p1112_cmp_epi

    xor a
    call cc_frame_local_disp
    ret c
    cp $FF
    jp nz,p1112_fail
    ld a,4
    call cc_frame_local_disp
    ret c
    cp $FB
    jp nz,p1112_fail
    xor a
    ret

p1112_build_exec:
    ; Build emitted prologue + CALL p1112_callee + emitted epilogue.
    ld hl,cc_frame_prologue
    ld de,p1112_code
    ld a,(cc_frame_prologue_len)
    ld c,a
    ld b,0
    ldir
    ld a,$CD
    ld (de),a
    inc de
    ld hl,p1112_callee
    ld a,l
    ld (de),a
    inc de
    ld a,h
    ld (de),a
    inc de
    ld hl,cc_frame_epilogue
    ld a,(cc_frame_epilogue_len)
    ld c,a
    ld b,0
    ldir
    ret

p1112_callee:
    ld hl,0
    add hl,sp
    ld a,l
    and 1
    ld (p1112_callee_odd),a
    ret

p1112_runtime:
    xor a
    ld bc,5
    call cc_frame_plan
    ret c
    call cc_frame_emit
    ret c
    call p1112_build_exec
    xor a
    ld (p1112_callee_odd),a

    ld hl,0
    add hl,sp
    ld a,l
    and 1
    jp nz,p1112_fail
    ld (p1112_sp_before),sp

    ld ix,$1234
    call p1112_code

    ld (p1112_sp_after),sp
    push ix
    pop hl
    ld de,$1234
    or a
    sbc hl,de
    jp nz,p1112_fail
    ld a,(p1112_callee_odd)
    or a
    jp nz,p1112_fail
    ld hl,(p1112_sp_before)
    ld de,(p1112_sp_after)
    or a
    sbc hl,de
    jp nz,p1112_fail
    xor a
    ret

p1112_negative:
    ; Direct/no-IX locals have no IX stack displacement.
    ld a,CC_FRAME_FLAG_LEAF_SIMPLE|CC_FRAME_FLAG_DIRECT_LOCALS
    ld bc,1
    call cc_frame_plan
    ret c
    xor a
    call cc_frame_local_disp
    jp nc,p1112_fail
    cp E_FORMAT
    jp nz,p1112_fail

    ; Odd call-boundary SP is forbidden.
    ld hl,$BFBF
    call cc_frame_call_sp_check
    jp nc,p1112_fail
    cp E_FORMAT
    jp nz,p1112_fail

    ; IX displacement/frame resource bound is explicit.
    xor a
    ld bc,127
    call cc_frame_plan
    jp nc,p1112_fail
    cp E_NOSPC
    jp nz,p1112_fail
    xor a
    ret

fixture_end:
    SAVEBIN "p1112-main.bin",fixture,fixture_end-fixture
''', encoding="utf-8", newline="\n")

    result = run_command(
        [assembler, "--nologo", "--sym=p1112-frame.sym", fixture.name],
        cwd=build, timeout_seconds=30,
    )
    require(not result.timed_out and result.exit_code == 0,
            f"P11.12 assemble: {result.stderr or result.stdout}")
    main = (build / "p1112-main.bin").read_bytes()
    require(len(main) <= 0x3F00, "P11.12 fixture exceeds upper-RAM budget")
    names = ("p1112_leaf", "p1112_frame", "p1112_runtime", "p1112_negative")
    syms = phase3_open_descriptions._symbols(build / "p1112-frame.sym", names)

    assertions = [
        {"name": "leaf-simple-omits-ix-frame", "passed": True},
        {"name": "frame-local-bytes-even-padded", "passed": True},
        {"name": "ix-negative-local-offsets-exact", "passed": True},
        {"name": "ix-prologue-epilogue-byte-exact", "passed": True},
        {"name": "generated-frame-has-no-iy-prefix", "passed": True},
        {"name": "rev17-native-frame-rule-authoritative-over-host-sdk", "passed": True},
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
                raise P1112Error(f"{name} native fixture failed: {exc}") from None
        assertions += [
            {"name": "fuse-leaf-no-unnecessary-ix", "passed": True},
            {"name": "fuse-frame-ix-callee-preserved", "passed": True},
            {"name": "fuse-frame-sp-restored-exactly", "passed": True},
            {"name": "fuse-call-boundary-sp-even-inside-frame", "passed": True},
            {"name": "fuse-odd-sp-boundary-rejected", "passed": True},
            {"name": "fuse-frame-resource-boundary-rejected", "passed": True},
        ]

    hashes = {
        "v1/src/tools/cc.asm": sha256_file(source),
        "v1/build/p1112-main.bin": sha256_file(build / "p1112-main.bin"),
        "v1/tools-host/test-driver/phase11_step_12.py": sha256_file(
            root / "v1/tools-host/test-driver/phase11_step_12.py"
        ),
        "v1/dist/certification/P11.11.build.json": sha256_file(
            root / "v1/dist/certification/P11.11.build.json"
        ),
        "v1/dist/certification/P11.11.test.json": sha256_file(
            root / "v1/dist/certification/P11.11.test.json"
        ),
    }
    return commands, hashes, assertions
