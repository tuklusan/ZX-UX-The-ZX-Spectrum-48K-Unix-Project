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


class P1117Error(DriverError):
    pass


def require(ok, message):
    if not ok:
        raise P1117Error(message)


def dispatch(root, action, step, *, sha256_file, run_command, require_project_tool):
    if step != "P11.17":
        raise DriverError(step)

    inc = root / "v1/include/zx48ux.inc"
    syscall = root / "v1/src/kernel/syscall.asm"
    rom = root / "v1/src/kernel/rom_services.asm"
    runtime = root / "v1/src/libc48/float_runtime.asm"
    itext = inc.read_text(encoding="utf-8")
    stext = syscall.read_text(encoding="utf-8")
    rtext = rom.read_text(encoding="utf-8")
    ltext = runtime.read_text(encoding="utf-8")
    arch = (root / "docs/01-ZX-UX-ARCHITECTURE-REV17.md").read_text(encoding="utf-8")
    plan = (root / "docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV08.md").read_text(encoding="utf-8")

    op_lines = {
        "FPOP_OP_INVALID": 0, "FPOP_OP_ADD": 1, "FPOP_OP_SUB": 2,
        "FPOP_OP_MUL": 3, "FPOP_OP_DIV": 4, "FPOP_OP_POW": 5,
        "FPOP_OP_ABS": 6, "FPOP_OP_SGN": 7, "FPOP_OP_INT": 8,
        "FPOP_OP_EXP": 9, "FPOP_OP_LN": 10, "FPOP_OP_SIN": 11,
        "FPOP_OP_COS": 12, "FPOP_OP_TAN": 13, "FPOP_OP_ASN": 14,
        "FPOP_OP_ACS": 15, "FPOP_OP_ATN": 16, "FPOP_OP_SQR": 17,
    }
    for name, value in op_lines.items():
        require(re.search(rf"^{name}\s+EQU \$%02X$" % value, itext, re.M),
                f"P11.17 ABI op drift: {name}")
    require(all(x in itext for x in (
        "FPOP1_OP_O               EQU $00",
        "FPOP1_RESERVED_O         EQU $01",
        "FPOP1_LHS_O              EQU $02",
        "FPOP1_RHS_O              EQU $04",
        "FPOP1_OUT_O              EQU $06",
        "FPOP1_SIZE               EQU $08",
    )), "P11.17 FPOP1 layout drift")

    helper_names = (
        "__fadd","__fsub","__fmul","__fdiv","__fpow","__fabs","__fsgn","__fint",
        "__fexp","__fln","__fsin","__fcos","__ftan","__fasin","__facos","__fatan","__fsqrt",
    )
    require(all(f"{name}:" in ltext for name in helper_names),
            "P11.17 required floating helper surface incomplete")
    require("zx_fp_exec:" in ltext, "P11.17 zx_fp_exec missing")
    require("EMIT_P1117_FP_EXEC_SYSCALL_ROUTINES" in stext,
            "P11.17 syscall ABI macro missing")
    require("EMIT_P1117_ROM_FP_EXEC_ROUTINES" in rtext,
            "P11.17 ROM calculator bridge missing")
    require("ld (altreg_busy),a" in rtext and "p1117_fp_rom_busy:" in rtext,
            "P11.17 calculator serialization missing")
    require("call ROM_CALCULATE" in rtext and "db $3B,$38" in rtext,
            "P11.17 controlled single-operation calculator entry missing")
    require("p1117_fp_result:" in rtext and "ld de,p1117_fp_result" in rtext,
            "P11.17 private result staging missing")
    require("84d144de2721cda5075c3a6610a422663b5e2f77" in ltext
            and "compiler/c48/float5.py" in ltext
            and "compiler/c48/vm.py" in ltext
            and "compiler/tests/test_conformance.py" in ltext,
            "P11.17 pinned SDK mapping missing")
    require(
        "SYS_FP_EXEC" in arch
        and "FPOP1" in arch
        and "FPOP1.op" in arch
        and "The calculator service must be tested across cooperative task switches" in arch,
        "REV17 P11.17 calculator contract drift",
    )
    require(
        "## P11.17 - SYS_FP_EXEC ROM calculator runtime bridge" in plan
        and "exhaustive op-ID 0..17 ABI table test" in plan
        and "Concurrent fixture cannot reenter calculator workspace." in plan,
        "REV08 P11.17 acceptance contract drift",
    )
    macro = ltext[ltext.index("    MACRO EMIT_P1117_C48_FLOAT_RUNTIME"):]
    macro = macro[:macro.index("    ENDM") + len("    ENDM")]
    code_only = "\n".join(line.split(";", 1)[0] for line in macro.splitlines())
    require(not re.search(r"\biy\b|\bexx\b|ex\s+af\s*,\s*af'", code_only, re.I),
            "P11.17 C48 runtime touches OS-private registers")

    assembler = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    fixture = build / "p1117-fp-exec.asm"
    fixture.write_text(r'''    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/kernel/syscall.asm"
    INCLUDE "../src/kernel/rom_services.asm"
    INCLUDE "../src/libc48/float_runtime.asm"

    ORG $C000
p1117_start:
altreg_busy: db 0
    EMIT_USER_RANGE_VALIDATION_ROUTINE
    EMIT_P1117_FP_EXEC_SYSCALL_ROUTINES
    EMIT_P1117_ROM_FP_EXEC_ROUTINES
    EMIT_P1117_C48_FLOAT_RUNTIME

p1117_f0: db $00,$00,$00,$00,$00
p1117_f1: db $00,$00,$01,$00,$00
p1117_f2: db $00,$00,$02,$00,$00
p1117_f3: db $00,$00,$03,$00,$00
p1117_f4: db $00,$00,$04,$00,$00
p1117_f6: db $00,$00,$06,$00,$00
p1117_f8: db $00,$00,$08,$00,$00
p1117_a5: db $A5,$A5,$A5,$A5,$A5

p1117_guard0: db $A6
p1117_out: defs 5,$A5
p1117_guard1: db $5A
p1117_aliasbuf: defs 5,0
p1117_req: defs FPOP1_SIZE,0
p1117_expected: dw 0
p1117_exit_seen: db 0

p1117_fail:
    ld a,E_FORMAT
    scf
    ret

p1117_check_word:
    or a
    sbc hl,de
    jp nz,p1117_fail
    xor a
    ret

p1117_check5:
    ld b,5
p1117_check5_loop:
    ld a,(de)
    cp (hl)
    jp nz,p1117_fail
    inc de
    inc hl
    djnz p1117_check5_loop
    xor a
    ret

p1117_fill_out:
    ld hl,p1117_a5
    ld de,p1117_out
    ld bc,5
    ldir
    ret

p1117_gateway:
    cp SYS_FP_EXEC
    jp z,p1117_gateway_fp
    cp SYS_EXIT
    jp z,p1117_gateway_exit
    ld a,E_NOTSUP
    scf
    ret
p1117_gateway_fp:
    ld (syscall_arg_hl),hl
    jp zx48_p1117_sys_fp_exec
p1117_gateway_exit:
    ld a,l
    ld (p1117_exit_seen),a
    xor a
    ret

p1117_case:
    ld (p1117_expected),bc
    ld (p1117_req+FPOP1_OP_O),a
    xor a
    ld (p1117_req+FPOP1_RESERVED_O),a
    ld (p1117_req+FPOP1_LHS_O),hl
    ld (p1117_req+FPOP1_RHS_O),de
    ld bc,p1117_out
    ld (p1117_req+FPOP1_OUT_O),bc
    ld hl,p1117_req
    ld a,SYS_FP_EXEC
    call p1117_gateway
    ret c
    ld hl,p1117_out
    ld de,(p1117_expected)
    call p1117_check5
    ret c
    ld a,(p1117_guard0)
    cp $A6
    jp nz,p1117_fail
    ld a,(p1117_guard1)
    cp $5A
    jp nz,p1117_fail
    xor a
    ret

p1117_goldens:
    ld a,FPOP_OP_ADD
    ld hl,p1117_f1
    ld de,p1117_f2
    ld bc,p1117_f3
    call p1117_case
    ret c
    ld a,FPOP_OP_SUB
    ld hl,p1117_f2
    ld de,p1117_f1
    ld bc,p1117_f1
    call p1117_case
    ret c
    ld a,FPOP_OP_MUL
    ld hl,p1117_f2
    ld de,p1117_f3
    ld bc,p1117_f6
    call p1117_case
    ret c
    ld a,FPOP_OP_DIV
    ld hl,p1117_f4
    ld de,p1117_f2
    ld bc,p1117_f2
    call p1117_case
    ret c
    ld a,FPOP_OP_POW
    ld hl,p1117_f2
    ld de,p1117_f3
    ld bc,p1117_f8
    call p1117_case
    ret c
    ld a,FPOP_OP_ABS
    ld hl,p1117_f2
    ld de,0
    ld bc,p1117_f2
    call p1117_case
    ret c
    ld a,FPOP_OP_SGN
    ld hl,p1117_f2
    ld de,0
    ld bc,p1117_f1
    call p1117_case
    ret c
    ld a,FPOP_OP_INT
    ld hl,p1117_f2
    ld de,0
    ld bc,p1117_f2
    call p1117_case
    ret c
    ld a,FPOP_OP_EXP
    ld hl,p1117_f0
    ld de,0
    ld bc,p1117_f1
    call p1117_case
    ret c
    ld a,FPOP_OP_LN
    ld hl,p1117_f1
    ld de,0
    ld bc,p1117_f0
    call p1117_case
    ret c
    ld a,FPOP_OP_SIN
    ld hl,p1117_f0
    ld de,0
    ld bc,p1117_f0
    call p1117_case
    ret c
    ld a,FPOP_OP_COS
    ld hl,p1117_f0
    ld de,0
    ld bc,p1117_f1
    call p1117_case
    ret c
    ld a,FPOP_OP_TAN
    ld hl,p1117_f0
    ld de,0
    ld bc,p1117_f0
    call p1117_case
    ret c
    ld a,FPOP_OP_ASN
    ld hl,p1117_f0
    ld de,0
    ld bc,p1117_f0
    call p1117_case
    ret c
    ld a,FPOP_OP_ACS
    ld hl,p1117_f1
    ld de,0
    ld bc,p1117_f0
    call p1117_case
    ret c
    ld a,FPOP_OP_ATN
    ld hl,p1117_f0
    ld de,0
    ld bc,p1117_f0
    call p1117_case
    ret c
    ld a,FPOP_OP_SQR
    ld hl,p1117_f4
    ld de,0
    ld bc,p1117_f2
    jp p1117_case

p1117_call_raw:
    ld hl,p1117_req
    ld a,SYS_FP_EXEC
    jp p1117_gateway

p1117_prepare_add:
    call p1117_fill_out
    ld a,FPOP_OP_ADD
    ld (p1117_req+FPOP1_OP_O),a
    xor a
    ld (p1117_req+FPOP1_RESERVED_O),a
    ld hl,p1117_f1
    ld (p1117_req+FPOP1_LHS_O),hl
    ld hl,p1117_f2
    ld (p1117_req+FPOP1_RHS_O),hl
    ld hl,p1117_out
    ld (p1117_req+FPOP1_OUT_O),hl
    ret

p1117_alias:
    ld hl,p1117_f1
    ld de,p1117_aliasbuf
    ld bc,5
    ldir
    ld a,FPOP_OP_ADD
    ld (p1117_req+FPOP1_OP_O),a
    xor a
    ld (p1117_req+FPOP1_RESERVED_O),a
    ld hl,p1117_aliasbuf
    ld (p1117_req+FPOP1_LHS_O),hl
    ld hl,p1117_f2
    ld (p1117_req+FPOP1_RHS_O),hl
    ld hl,p1117_aliasbuf
    ld (p1117_req+FPOP1_OUT_O),hl
    call p1117_call_raw
    ret c
    ld hl,p1117_aliasbuf
    ld de,p1117_f3
    call p1117_check5
    ret c

    ld hl,p1117_f2
    ld de,p1117_aliasbuf
    ld bc,5
    ldir
    ld hl,p1117_f1
    ld (p1117_req+FPOP1_LHS_O),hl
    ld hl,p1117_aliasbuf
    ld (p1117_req+FPOP1_RHS_O),hl
    ld (p1117_req+FPOP1_OUT_O),hl
    call p1117_call_raw
    ret c
    ld hl,p1117_aliasbuf
    ld de,p1117_f3
    jp p1117_check5

p1117_expect_inval:
    call p1117_call_raw
    jp nc,p1117_fail
    cp E_INVAL
    jp nz,p1117_fail
    xor a
    ret

p1117_invalids:
    call p1117_prepare_add
    xor a
    ld (p1117_req+FPOP1_OP_O),a
    call p1117_expect_inval
    ret c
    call p1117_prepare_add
    ld a,FPOP_OP_SQR+1
    ld (p1117_req+FPOP1_OP_O),a
    call p1117_expect_inval
    ret c
    call p1117_prepare_add
    ld a,1
    ld (p1117_req+FPOP1_RESERVED_O),a
    call p1117_expect_inval
    ret c
    call p1117_prepare_add
    ld hl,0
    ld (p1117_req+FPOP1_LHS_O),hl
    call p1117_expect_inval
    ret c
    call p1117_prepare_add
    ld hl,0
    ld (p1117_req+FPOP1_RHS_O),hl
    call p1117_expect_inval
    ret c
    call p1117_prepare_add
    ld a,FPOP_OP_COS
    ld (p1117_req+FPOP1_OP_O),a
    ld hl,p1117_f2
    ld (p1117_req+FPOP1_RHS_O),hl
    call p1117_expect_inval
    ret c
    call p1117_prepare_add
    ld hl,0
    ld (p1117_req+FPOP1_OUT_O),hl
    call p1117_expect_inval
    ret c
    call p1117_prepare_add
    ld hl,ROM_COMPAT_START
    ld (p1117_req+FPOP1_OUT_O),hl
    call p1117_expect_inval
    ret c
    ld hl,p1117_out
    ld de,p1117_a5
    jp p1117_check5

p1117_busy:
    call p1117_prepare_add
    ld a,1
    ld (altreg_busy),a
    call p1117_call_raw
    push af
    xor a
    ld (altreg_busy),a
    pop af
    jp nc,p1117_fail
    cp E_BUSY
    jp nz,p1117_fail
    ld hl,p1117_out
    ld de,p1117_a5
    jp p1117_check5

p1117_state:
    ld hl,$6400
    ld (ROM_ERR_SP),hl
    ld hl,$6100
    ld (ROM_STKBOT),hl
    ld hl,$6105
    ld (ROM_STKEND),hl
    ld hl,$6200
    ld (ROM_MEM),hl
    ld hl,$6300
    ld (ROM_CH_ADD),hl
    ld a,$5A
    ld (ROM_FLAGS),a
    ld a,$4D
    ld (ROM_IY_ANCHOR),a
    ld a,$6C
    ld (ROM_BREG),a
    ld iy,$1234
    ld a,FPOP_OP_ADD
    ld hl,p1117_f1
    ld de,p1117_f2
    ld bc,p1117_f3
    call p1117_case
    ret c
    push iy
    pop hl
    ld de,ROM_IY_ANCHOR
    call p1117_check_word
    ret c
    ld hl,(ROM_ERR_SP)
    ld de,$6400
    call p1117_check_word
    ret c
    ld hl,(ROM_STKBOT)
    ld de,$6100
    call p1117_check_word
    ret c
    ld hl,(ROM_STKEND)
    ld de,$6105
    call p1117_check_word
    ret c
    ld hl,(ROM_MEM)
    ld de,$6200
    call p1117_check_word
    ret c
    ld hl,(ROM_CH_ADD)
    ld de,$6300
    call p1117_check_word
    ret c
    ld a,(ROM_FLAGS)
    cp $5A
    jp nz,p1117_fail
    ld a,(ROM_IY_ANCHOR)
    cp $4D
    jp nz,p1117_fail
    ld a,(ROM_BREG)
    cp $6C
    jp nz,p1117_fail
    ld a,(altreg_busy)
    or a
    jp nz,p1117_fail
    xor a
    ret

p1117_runtime:
    call p1117_fill_out
    ld hl,p1117_out
    push hl
    ld hl,FPOP_OP_ADD
    ld de,p1117_f1
    ld bc,p1117_f2
    call zx_fp_exec
    pop af
    ld a,h
    or l
    jp nz,p1117_fail
    ld hl,p1117_out
    ld de,p1117_f3
    call p1117_check5
    ret c
    call p1117_fill_out
    ld hl,p1117_out
    ld de,p1117_f1
    ld bc,p1117_f2
    call __fadd
    ld de,p1117_out
    call p1117_check_word
    ret c
    ld hl,p1117_out
    ld de,p1117_f3
    call p1117_check5
    ret c
    call p1117_fill_out
    ld hl,p1117_out
    ld de,p1117_f0
    call __fcos
    ld de,p1117_out
    call p1117_check_word
    ret c
    ld hl,p1117_out
    ld de,p1117_f1
    call p1117_check5
    ret c
    call p1117_fill_out
    ld hl,p1117_out
    push hl
    ld hl,FPOP_OP_DIV
    ld de,p1117_f1
    ld bc,p1117_f0
    call zx_fp_exec
    pop af
    ld de,E_INVAL
    call p1117_check_word
    ret c
    ld hl,p1117_out
    ld de,p1117_a5
    call p1117_check5
    ret c
    xor a
    ld (p1117_exit_seen),a
    ld (c48_fp_runtime_exit_status),a
    ld hl,p1117_out
    ld de,p1117_f1
    ld bc,p1117_f0
    call __fdiv
    jp nc,p1117_fail
    cp E_INVAL
    jp nz,p1117_fail
    ld a,(p1117_exit_seen)
    cp 1
    jp nz,p1117_fail
    ld a,(c48_fp_runtime_exit_status)
    cp 1
    jp nz,p1117_fail
    xor a
    ret

p1117_end:
    SAVEBIN "p1117-main.bin",p1117_start,p1117_end-p1117_start
''', encoding="utf-8", newline="\n")

    result = run_command(
        [assembler, "--nologo", "--sym=p1117-fp-exec.sym", fixture.name],
        cwd=build, timeout_seconds=30,
    )
    require(not result.timed_out and result.exit_code == 0,
            f"P11.17 assemble: {result.stderr or result.stdout}")
    main = (build / "p1117-main.bin").read_bytes()
    require(0 < len(main) <= 0x2000, "P11.17 fixture exceeds C000-DFFF user range")
    names = (
        "p1117_gateway","p1117_goldens","p1117_alias","p1117_invalids",
        "p1117_busy","p1117_state","p1117_runtime",
    )
    syms = phase3_open_descriptions._symbols(build / "p1117-fp-exec.sym", names)

    assertions = [
        {"name": "fpop1-eight-byte-layout-and-op-ids-0-through-17-frozen", "passed": True},
        {"name": "all-required-runtime-helper-symbols-present", "passed": True},
        {"name": "zx-fp-exec-library-facing-regcall-present", "passed": True},
        {"name": "binary-unary-pointer-rules-validated-before-rom-entry", "passed": True},
        {"name": "calculator-critical-section-is-serialized", "passed": True},
        {"name": "operands-copy-before-result-write-preserves-aliasing", "passed": True},
        {"name": "rom-errors-map-to-einval-and-runtime-status-one", "passed": True},
        {"name": "sdk-float5-vm-conformance-mapping-recorded", "passed": True},
    ]
    commands = [result]
    if action == "test":
        gateway = phase1._jp(syms["p1117_gateway"])

        def patch(ram):
            ram[0xC000 - 0x4000:0xC000 - 0x4000 + len(main)] = main
            ram[SYSCALL_GATEWAY - 0x4000:SYSCALL_GATEWAY - 0x4000 + len(gateway)] = gateway

        for name in names[1:]:
            code = (
                b"\xF3" + phase1._ld_sp(0xBFC0)
                + phase1._call(syms[name])
                + phase1._jp_c(FAIL_PC) + phase1._jp(PASS_PC)
            )
            try:
                commands.append(run_sna(root, code, patch=patch, timeout=20.0))
            except DriverError as exc:
                raise P1117Error(f"{name} native fixture failed: {exc}") from None
        assertions += [
            {"name": "fuse-exhaustive-op-1-through-17-exact-goldens-pass", "passed": True},
            {"name": "fuse-op-0-and-op-18-reject-before-result-mutation", "passed": True},
            {"name": "fuse-binary-unary-zero-pointer-rules-are-exact", "passed": True},
            {"name": "fuse-output-alias-lhs-and-rhs-is-byte-exact", "passed": True},
            {"name": "fuse-concurrent-busy-state-cannot-reenter-workspace", "passed": True},
            {"name": "fuse-rom-system-state-and-iy-restored", "passed": True},
            {"name": "fuse-public-wrapper-and-hidden-result-helpers-execute", "passed": True},
            {"name": "fuse-rom-domain-error-becomes-errno-or-runtime-exit-one", "passed": True},
        ]

    hashes = {
        "v1/include/zx48ux.inc": sha256_file(inc),
        "v1/src/kernel/syscall.asm": sha256_file(syscall),
        "v1/src/kernel/rom_services.asm": sha256_file(rom),
        "v1/src/libc48/float_runtime.asm": sha256_file(runtime),
        "v1/build/p1117-main.bin": sha256_file(build / "p1117-main.bin"),
        "v1/tools-host/test-driver/phase11_step_17.py": sha256_file(
            root / "v1/tools-host/test-driver/phase11_step_17.py"
        ),
        "v1/dist/certification/P11.16.build.json": sha256_file(
            root / "v1/dist/certification/P11.16.build.json"
        ),
        "v1/dist/certification/P11.16.test.json": sha256_file(
            root / "v1/dist/certification/P11.16.test.json"
        ),
    }
    return commands, hashes, assertions
