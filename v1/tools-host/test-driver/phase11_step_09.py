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


class P1109Error(DriverError):
    pass


def require(ok, message):
    if not ok:
        raise P1109Error(message)


def dispatch(root, action, step, *, sha256_file, run_command, require_project_tool):
    if step != "P11.09":
        raise DriverError(step)

    source = root / "v1/src/tools/cc.asm"
    text = source.read_text(encoding="utf-8")
    arch = (root / "docs/01-ZX-UX-ARCHITECTURE-REV17.md").read_text(encoding="utf-8")
    plan = (root / "docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV08.md").read_text(encoding="utf-8")
    markers = (
        "EMIT_P11_CC_POINTER_ARITH",
        "CC_PTR_REPR_SIZE          EQU 2",
        "cc_ptr_pointee_size:",
        "cc_ptr_scale_de:",
        "cc_ptr_add_scaled:",
        "cc_ptr_sub_scaled:",
        "cc_ptr_diff:",
        "cc_ptr_require_portable_relation:",
        "84d144de2721cda5075c3a6610a422663b5e2f77",
        "compiler/c48/typesys.py",
        "compiler/c48/semantics.py",
        "compiler/c48/vm.py",
    )
    require(all(m in text for m in markers), "P11.09 pointer arithmetic surface incomplete")
    require(
        "Pointer arithmetic scales by pointed-to `sizeof`; subtraction of" in arch
        and "unrelated pointers is outside the portable C48 contract" in arch,
        "REV17 P11.09 pointer contract drift",
    )
    require(
        "P11.09 - Pointer arithmetic" in plan
        and "positive/zero/negative same-array pointer subtraction" in plan,
        "REV08 P11.09 acceptance contract drift",
    )

    assembler = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    fixture = build / "p1109-pointers.asm"
    fixture.write_text(r'''    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/tools/cc.asm"
    ORG $C000
fixture:
    EMIT_P11_CC_STREAMING_CORE
    EMIT_P11_CC_LEXER
    EMIT_P11_CC_DECL_PARSER
    EMIT_P11_CC_POINTER_ARITH

    ASSERT CC_PTR_REPR_SIZE = 2

p1109_fail:
    ld a,E_FORMAT
    scf
    ret

; HL=actual, DE=expected.
p1109_expect_hl:
    or a
    sbc hl,de
    jp nz,p1109_fail
    xor a
    ret

p1109_sizes:
    ld a,CC_TYPE_CHAR
    ld e,1
    call cc_ptr_pointee_size
    ret c
    cp 1
    jp nz,p1109_fail

    ld a,CC_TYPE_UCHAR
    ld e,1
    call cc_ptr_pointee_size
    ret c
    cp 1
    jp nz,p1109_fail

    ld a,CC_TYPE_INT
    ld e,1
    call cc_ptr_pointee_size
    ret c
    cp 2
    jp nz,p1109_fail

    ld a,CC_TYPE_FLOAT
    ld e,1
    call cc_ptr_pointee_size
    ret c
    cp 5
    jp nz,p1109_fail

    ; Pointer-to-pointer stride is pointer sizeof, including void **.
    ld a,CC_TYPE_VOID
    ld e,2
    call cc_ptr_pointee_size
    ret c
    cp 2
    jp nz,p1109_fail
    xor a
    ret

p1109_addsub:
    ; char*: 0x8000 + 3*1 = 0x8003
    ld hl,$8000
    ld de,3
    ld a,1
    call cc_ptr_add_scaled
    ret c
    ld de,$8003
    call p1109_expect_hl
    ret c

    ; int*: 0x8000 + 3*2 = 0x8006
    ld hl,$8000
    ld de,3
    ld a,2
    call cc_ptr_add_scaled
    ret c
    ld de,$8006
    call p1109_expect_hl
    ret c

    ; float*: 0x8000 + 3*5 = 0x800F
    ld hl,$8000
    ld de,3
    ld a,5
    call cc_ptr_add_scaled
    ret c
    ld de,$800F
    call p1109_expect_hl
    ret c

    ; Signed negative delta: float* + (-2) = -10 bytes.
    ld hl,$8000
    ld de,$FFFE
    ld a,5
    call cc_ptr_add_scaled
    ret c
    ld de,$7FF6
    call p1109_expect_hl
    ret c

    ; pointer - integer uses the same exact scaling.
    ld hl,$8000
    ld de,3
    ld a,5
    call cc_ptr_sub_scaled
    ret c
    ld de,$7FF1
    call p1109_expect_hl
    ret c
    xor a
    ret

p1109_diff:
    ; sizeof 1: positive / zero / negative.
    ld hl,$8003
    ld de,$8000
    ld a,1
    call cc_ptr_diff
    ret c
    ld de,3
    call p1109_expect_hl
    ret c

    ld hl,$8000
    ld de,$8000
    ld a,1
    call cc_ptr_diff
    ret c
    ld de,0
    call p1109_expect_hl
    ret c

    ld hl,$8000
    ld de,$8003
    ld a,1
    call cc_ptr_diff
    ret c
    ld de,$FFFD
    call p1109_expect_hl
    ret c

    ; sizeof 2.
    ld hl,$8006
    ld de,$8000
    ld a,2
    call cc_ptr_diff
    ret c
    ld de,3
    call p1109_expect_hl
    ret c

    ld hl,$8000
    ld de,$8006
    ld a,2
    call cc_ptr_diff
    ret c
    ld de,$FFFD
    call p1109_expect_hl
    ret c

    ; sizeof 5.
    ld hl,$800F
    ld de,$8000
    ld a,5
    call cc_ptr_diff
    ret c
    ld de,3
    call p1109_expect_hl
    ret c

    ld hl,$8000
    ld de,$800F
    ld a,5
    call cc_ptr_diff
    ret c
    ld de,$FFFD
    call p1109_expect_hl
    ret c
    xor a
    ret

p1109_negatives:
    ; void * has no complete pointed-to object size.
    ld a,CC_TYPE_VOID
    ld e,1
    call cc_ptr_pointee_size
    jp nc,p1109_fail
    cp E_INVAL
    jp nz,p1109_fail

    ; Zero pointer depth and unsupported element size are rejected.
    ld a,CC_TYPE_INT
    ld e,0
    call cc_ptr_pointee_size
    jp nc,p1109_fail
    cp E_INVAL
    jp nz,p1109_fail

    ld hl,$8000
    ld de,1
    ld a,3
    call cc_ptr_add_scaled
    jp nc,p1109_fail
    cp E_INVAL
    jp nz,p1109_fail

    ; A malformed non-element-boundary subtraction fails closed.
    ld hl,$8001
    ld de,$8000
    ld a,2
    call cc_ptr_diff
    jp nc,p1109_fail
    cp E_INVAL
    jp nz,p1109_fail

    ld hl,$8006
    ld de,$8000
    ld a,5
    call cc_ptr_diff
    jp nc,p1109_fail
    cp E_INVAL
    jp nz,p1109_fail

    ; Language/spec oracle: unrelated ordering/subtraction is not portable C48.
    ld a,CC_PTR_REL_UNRELATED
    call cc_ptr_require_portable_relation
    jp nc,p1109_fail
    cp E_NOTSUP
    jp nz,p1109_fail

    ld a,CC_PTR_REL_SAME_OBJECT
    call cc_ptr_require_portable_relation
    ret c
    xor a
    ret

p1109_all:
    call p1109_sizes
    ret c
    call p1109_addsub
    ret c
    call p1109_diff
    ret c
    call p1109_negatives
    ret c
    xor a
    ret

fixture_end:
    SAVEBIN "p1109-main.bin",fixture,fixture_end-fixture
''', encoding="utf-8", newline="\n")

    result = run_command(
        [assembler, "--nologo", "--sym=p1109-pointers.sym", fixture.name],
        cwd=build, timeout_seconds=30,
    )
    require(not result.timed_out and result.exit_code == 0,
            f"P11.09 assemble: {result.stderr or result.stdout}")
    main = (build / "p1109-main.bin").read_bytes()
    require(len(main) <= 0x3F00, "P11.09 fixture exceeds high-RAM SNA budget")
    syms = phase3_open_descriptions._symbols(
        build / "p1109-pointers.sym",
        ("p1109_sizes", "p1109_addsub", "p1109_diff", "p1109_negatives"),
    )

    assertions = [
        {"name": "pointer-representation-exactly-16-bit-native", "passed": True},
        {"name": "pointee-size-selection-1-2-5-native", "passed": True},
        {"name": "pointer-plus-minus-integer-scales-by-sizeof-native", "passed": True},
        {"name": "same-array-pointer-difference-signed-16-bit-native", "passed": True},
        {"name": "unrelated-pointer-order-subtraction-not-portable-oracle", "passed": True},
        {"name": "sdk-pinned-pointer-oracle-mapping-recorded", "passed": True},
    ]
    commands = [result]
    if action == "test":
        def patch(ram):
            ram[0xC000 - 0x4000:0xC000 - 0x4000 + len(main)] = main

        for name in ("p1109_sizes", "p1109_addsub", "p1109_diff", "p1109_negatives"):
            code = (
                b"\xF3" + phase1._ld_sp(0xBFC0)
                + phase1._call(syms[name])
                + phase1._jp_c(FAIL_PC) + phase1._jp(PASS_PC)
            )
            try:
                commands.append(run_sna(root, code, patch=patch))
            except DriverError as exc:
                raise P1109Error(f"{name} native fixture failed: {exc}") from None
        assertions += [
            {"name": "fuse-pointer-scaling-size1-char", "passed": True},
            {"name": "fuse-pointer-scaling-size2-int", "passed": True},
            {"name": "fuse-pointer-scaling-size5-float", "passed": True},
            {"name": "fuse-pointer-difference-positive-zero-negative", "passed": True},
            {"name": "fuse-void-pointer-arithmetic-rejected", "passed": True},
            {"name": "fuse-misaligned-element-difference-rejected", "passed": True},
            {"name": "fuse-unrelated-portable-relation-claim-rejected", "passed": True},
        ]

    hashes = {
        "v1/src/tools/cc.asm": sha256_file(source),
        "v1/build/p1109-main.bin": sha256_file(build / "p1109-main.bin"),
        "v1/tools-host/test-driver/phase11_step_09.py": sha256_file(
            root / "v1/tools-host/test-driver/phase11_step_09.py"
        ),
        "v1/dist/certification/P11.08.build.json": sha256_file(
            root / "v1/dist/certification/P11.08.build.json"
        ),
        "v1/dist/certification/P11.08.test.json": sha256_file(
            root / "v1/dist/certification/P11.08.test.json"
        ),
    }
    return commands, hashes, assertions
