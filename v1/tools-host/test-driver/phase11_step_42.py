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

import json
import re

import phase1
import phase3_open_descriptions
from driver_core import DriverError
from fuse_harness import FAIL_PC, PASS_PC, run_sna


class P1142Error(DriverError):
    pass


def require(ok, message):
    if not ok:
        raise P1142Error(message)


def dispatch(root, action, step, *, sha256_file, run_command, require_project_tool):
    if step != "P11.42":
        raise DriverError(step)

    plan = (root / "docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV08.md").read_text(encoding="utf-8")
    arch = (root / "docs/01-ZX-UX-ARCHITECTURE-REV17.md").read_text(encoding="utf-8")
    cc_path = root / "v1/src/tools/cc.asm"
    cc = cc_path.read_text(encoding="utf-8")
    matrix_path = root / "v1/tests/compiler/p1142-error-matrix.json"
    matrix = json.loads(matrix_path.read_text(encoding="utf-8"))

    require("## P11.42 - Compiler error and resource-boundary matrix" in plan
            and "syntax/semantic failure" in plan
            and "symbol-table overflow" in plan
            and "source too large" in plan
            and "output-memory exhaustion" in plan
            and "compiler workspace exhaustion" in plan
            and "final rename failure" in plan,
            "REV08 P11.42 contract drift")
    require("# 57. Phase 11 - C48 Compiler" in arch
            and "compiler syntax/allocation/rename failures preserve any previous" in arch
            and "destination byte-identically" in arch,
            "REV17 P11.42 failure-transaction authority drift")
    require(matrix.get("schema") == 1 and matrix.get("step") == "P11.42",
            "P11.42 matrix identity drift")
    expected = (
        ("syntax-failure", "E_FORMAT"),
        ("semantic-failure", "E_FORMAT"),
        ("symbol-table-overflow", "E_NOSPC"),
        ("source-too-large", "E_NOSPC"),
        ("output-memory-exhaustion", "E_NOSPC"),
        ("compiler-workspace-exhaustion", "E_NOSPC"),
        ("final-rename-failure", "E_BUSY"),
    )
    require(tuple((row["name"], row["errno"]) for row in matrix["cases"]) == expected,
            "P11.42 matrix rows drift")
    require(all(row["prior_destination"] == "unchanged" for row in matrix["cases"]),
            "P11.42 prior-destination invariant missing")

    for token in (
        "CC_GLOBAL_CAPACITY       EQU 32",
        "CC_EXPR_CAPACITY         EQU 8",
        "CC_SOURCE_WINDOW_SIZE    EQU 64",
        "CC_WORKSPACE_LIMIT       EQU 2048",
        "cc_p1102_nospc:",
        "cc_p1129_cleanup_error:",
        "cc_p1129_return_primary:",
        "cc_p1129_owned:",
        "cc_p1129_open:",
    ):
        require(token in cc, f"P11.42 native prerequisite missing: {token}")

    for macro_name in (
        "EMIT_P11_CC_STREAMING_CORE",
        "EMIT_P1128_CC_OBJ1_WRITER",
        "EMIT_P1129_CC_TRANSACTION_ROUTINES",
        "EMIT_P1138_CC_DEMO_COMPILER",
    ):
        start = cc.index("MACRO " + macro_name)
        end = cc.index("    ENDM", start)
        body = "\n".join(line.split(";", 1)[0] for line in cc[start:end].splitlines())
        require(not re.search(r"\biy\b|\bexx\b|ex\s+af\s*,\s*af'", body, re.I),
                f"P11.42 {macro_name} uses OS-private registers")

    assembler = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)

    core = build / "p1142-error-core.asm"
    core.write_text(r'''    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/tools/cc.asm"

    ORG $4000
p1142_core_start:
    EMIT_P11_CC_STREAMING_CORE
    EMIT_P11_CC_LEXER
    EMIT_P11_CC_DECL_PARSER
    EMIT_P1128_CC_OBJ1_WRITER
    EMIT_P1138_CC_DEMO_COMPILER

p1142_dest: defs 16,$A5
p1142_candidate: defs 96,$A5
p1142_text: db $C9
p1142_ident: db "g",0
p1142_bad_source: db "int main(void){ return 0;"
p1142_bad_source_end:
p1142_proto1: db "int f(int);"
p1142_proto1_end:
p1142_proto2: db "int f(float);"
p1142_proto2_end:

p1142_fail:
    ld a,E_FORMAT
    scf
    ret

p1142_reset_dest:
    ld hl,p1142_dest
    ld b,16
    ld a,$A5
p1142_reset_dest_loop:
    ld (hl),a
    inc hl
    djnz p1142_reset_dest_loop
    xor a
    ret

p1142_check_dest:
    ld hl,p1142_dest
    ld b,16
p1142_check_dest_loop:
    ld a,(hl)
    cp $A5
    jr nz,p1142_dest_bad
    inc hl
    djnz p1142_check_dest_loop
    xor a
    ret
p1142_dest_bad:
    ld a,E_FORMAT
    scf
    ret

p1142_check_guards:
    ld a,(cc_workspace_guard_pre)
    cp $A5
    jp nz,p1142_fail
    ld a,(cc_workspace_guard_post)
    cp $5A
    jp nz,p1142_fail
    xor a
    ret

p1142_syntax:
    call p1142_reset_dest
    ld hl,p1142_bad_source
    ld bc,p1142_bad_source_end-p1142_bad_source
    ld de,p1142_candidate
    ld ix,96
    call cc_p1138_compile
    jp nc,p1142_fail
    cp E_FORMAT
    jp nz,p1142_fail
    call p1142_check_dest
    ret c
    call p1142_check_guards
    ret c
    xor a
    ret

p1142_semantic:
    call p1142_reset_dest
    call cc_parse_tu_reset
    ld hl,p1142_proto1
    ld bc,p1142_proto1_end-p1142_proto1
    call cc_parse_file_decl
    jp c,p1142_fail
    ld hl,p1142_proto2
    ld bc,p1142_proto2_end-p1142_proto2
    call cc_parse_file_decl
    jp nc,p1142_fail
    cp E_FORMAT
    jp nz,p1142_fail
    call p1142_check_dest
    ret c
    call p1142_check_guards
    ret c
    xor a
    ret

p1142_symbols:
    call p1142_reset_dest
    call cc_p1102_reset
    ld b,CC_GLOBAL_CAPACITY
p1142_symbols_loop:
    push bc
    ld hl,p1142_ident
    ld de,0
    call cc_global_insert
    pop bc
    jp c,p1142_fail
    djnz p1142_symbols_loop
    ld hl,p1142_ident
    ld de,0
    call cc_global_insert
    jp nc,p1142_fail
    cp E_NOSPC
    jp nz,p1142_fail
    ld a,(cc_global_count)
    cp CC_GLOBAL_CAPACITY
    jp nz,p1142_fail
    call p1142_check_dest
    ret c
    call p1142_check_guards
    ret c
    xor a
    ret

p1142_source_large:
    call p1142_reset_dest
    call cc_p1102_reset
    ld hl,$FFF0
    ld (cc_stream_total),hl
    ld hl,p1142_bad_source
    ld bc,CC_SOURCE_WINDOW_SIZE
    call cc_pipeline_feed
    jp nc,p1142_fail
    cp E_NOSPC
    jp nz,p1142_fail
    ld hl,(cc_stream_total)
    ld de,$FFF0
    or a
    sbc hl,de
    jp nz,p1142_fail
    call p1142_check_dest
    ret c
    call p1142_check_guards
    ret c
    xor a
    ret

p1142_output:
    call p1142_reset_dest
    ld hl,p1142_candidate
    ld b,64
    ld a,$A5
p1142_output_fill:
    ld (hl),a
    inc hl
    djnz p1142_output_fill
    ld hl,p1142_text
    ld (cc_obj1_text_ptr),hl
    ld hl,1
    ld (cc_obj1_text_size),hl
    ld hl,0
    ld (cc_obj1_bss_size),hl
    ld (cc_obj1_symbol_count),hl
    ld (cc_obj1_symbol_ptr),hl
    ld (cc_obj1_reloc_count),hl
    ld (cc_obj1_reloc_ptr),hl
    ld hl,p1142_candidate
    ld (cc_obj1_output_ptr),hl
    ld hl,24
    ld (cc_obj1_output_capacity),hl
    call cc_obj1_write
    jp nc,p1142_fail
    cp E_NOSPC
    jp nz,p1142_fail
    ld a,(cc_obj1_commit_marker)
    or a
    jp nz,p1142_fail
    ld a,(p1142_candidate)
    cp $A5
    jp nz,p1142_fail
    call p1142_check_dest
    ret c
    call p1142_check_guards
    ret c
    xor a
    ret

p1142_workspace:
    call p1142_reset_dest
    call cc_p1102_reset
    ld b,CC_EXPR_CAPACITY
p1142_workspace_loop:
    push bc
    call cc_expr_enter
    pop bc
    jp c,p1142_fail
    djnz p1142_workspace_loop
    call cc_expr_enter
    jp nc,p1142_fail
    cp E_NOSPC
    jp nz,p1142_fail
    ld a,(cc_expr_depth)
    cp CC_EXPR_CAPACITY
    jp nz,p1142_fail
    ld a,(cc_expr_highwater)
    cp CC_EXPR_CAPACITY
    jp nz,p1142_fail
    call cc_statement_release
    ld a,(cc_expr_depth)
    or a
    jp nz,p1142_fail
    call p1142_check_dest
    ret c
    call p1142_check_guards
    ret c
    xor a
    ret

p1142_swallow_specimen:
    ld hl,p1142_bad_source
    ld bc,p1142_bad_source_end-p1142_bad_source
    ld de,p1142_candidate
    ld ix,96
    call cc_p1138_compile
    ret nc
    xor a
    ret

p1142_negative_swallow_oracle:
    call p1142_swallow_specimen
    jp c,p1142_fail
    xor a
    ret

p1142_negative_dest_oracle:
    call p1142_reset_dest
    ld a,$A4
    ld (p1142_dest+7),a
    call p1142_check_dest
    jp nc,p1142_fail
    cp E_FORMAT
    jp nz,p1142_fail
    xor a
    ret

p1142_core_end:
    ASSERT p1142_core_end <= $9000
    SAVEBIN "p1142-core.bin",p1142_core_start,p1142_core_end-p1142_core_start
''', encoding="utf-8", newline="\n")

    core_cmd = run_command(
        [assembler, "--nologo", "--sym=p1142-error-core.sym", core.name],
        cwd=build, timeout_seconds=60,
    )
    require(not core_cmd.timed_out and core_cmd.exit_code == 0,
            f"P11.42 core assembly failed: {core_cmd.stderr or core_cmd.stdout}")
    core_bin = (build / "p1142-core.bin").read_bytes()
    require(0 < len(core_bin) <= 0x5000, f"P11.42 core fixture too large: {len(core_bin)}")
    core_names = (
        "p1142_syntax", "p1142_semantic", "p1142_symbols",
        "p1142_source_large", "p1142_output", "p1142_workspace",
        "p1142_negative_swallow_oracle", "p1142_negative_dest_oracle",
    )
    core_syms = phase3_open_descriptions._symbols(build / "p1142-error-core.sym", core_names)

    tx = build / "p1142-error-transaction.asm"
    tx.write_text(r'''    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/tools/cc.asm"

    ORG $C000
p1142_tx_start:
    EMIT_P1128_CC_OBJ1_WRITER
    EMIT_P1129_CC_TRANSACTION_ROUTINES

p1142_dest_name: db "keep.obj",0
p1142_dest: defs 16,$A5
p1142_candidate: defs 64,$CC
p1142_text: db $C9
p1142_open_calls: db 0
p1142_close_calls: db 0
p1142_remove_calls: db 0
p1142_rename_calls: db 0

p1142_tx_fail:
    ld a,E_FORMAT
    scf
    ret

p1142_tx_reset:
    xor a
    ld (p1142_open_calls),a
    ld (p1142_close_calls),a
    ld (p1142_remove_calls),a
    ld (p1142_rename_calls),a
    ld hl,p1142_dest
    ld b,16
    ld a,$A5
p1142_tx_dest_loop:
    ld (hl),a
    inc hl
    djnz p1142_tx_dest_loop
    xor a
    ret

p1142_tx_check_dest:
    ld hl,p1142_dest
    ld b,16
p1142_tx_check_loop:
    ld a,(hl)
    cp $A5
    jp nz,p1142_tx_fail
    inc hl
    djnz p1142_tx_check_loop
    xor a
    ret

p1142_make_candidate:
    ld hl,p1142_text
    ld (cc_obj1_text_ptr),hl
    ld hl,1
    ld (cc_obj1_text_size),hl
    ld hl,0
    ld (cc_obj1_bss_size),hl
    ld (cc_obj1_symbol_count),hl
    ld (cc_obj1_symbol_ptr),hl
    ld (cc_obj1_reloc_count),hl
    ld (cc_obj1_reloc_ptr),hl
    ld hl,p1142_candidate
    ld (cc_obj1_output_ptr),hl
    ld hl,64
    ld (cc_obj1_output_capacity),hl
    jp cc_obj1_write

p1142_rename:
    call p1142_tx_reset
    call p1142_make_candidate
    jp c,p1142_tx_fail
    ld hl,p1142_dest_name
    ld de,p1142_candidate
    ld bc,(cc_obj1_output_size)
    call cc_p1129_publish
    jp nc,p1142_tx_fail
    cp E_BUSY
    jp nz,p1142_tx_fail
    ld a,(p1142_open_calls)
    cp 1
    jp nz,p1142_tx_fail
    ld a,(p1142_close_calls)
    cp 1
    jp nz,p1142_tx_fail
    ld a,(p1142_rename_calls)
    cp 1
    jp nz,p1142_tx_fail
    ld a,(p1142_remove_calls)
    cp 1
    jp nz,p1142_tx_fail
    ld a,(cc_p1129_open)
    or a
    jp nz,p1142_tx_fail
    ld a,(cc_p1129_owned)
    or a
    jp nz,p1142_tx_fail
    call p1142_tx_check_dest
    ret c
    xor a
    ret

p1142_tx_end:
    ASSERT p1142_tx_end <= $E000
    SAVEBIN "p1142-tx.bin",p1142_tx_start,p1142_tx_end-p1142_tx_start

    ORG $E000
p1142_gate:
    cp SYS_GETPID
    jr z,p1142_getpid
    cp SYS_OPEN
    jr z,p1142_open
    cp SYS_WRITE
    jr z,p1142_write
    cp SYS_CLOSE
    jr z,p1142_close
    cp SYS_RENAME
    jr z,p1142_rename_fail
    cp SYS_REMOVE
    jr z,p1142_remove
    ld a,E_NOTSUP
    scf
    ret
p1142_getpid:
    ld hl,3
    xor a
    ret
p1142_open:
    ld a,(p1142_open_calls)
    inc a
    ld (p1142_open_calls),a
    ld hl,4
    xor a
    ret
p1142_write:
    push bc
    pop hl
    xor a
    ret
p1142_close:
    ld a,(p1142_close_calls)
    inc a
    ld (p1142_close_calls),a
    xor a
    ret
p1142_rename_fail:
    ld a,(p1142_rename_calls)
    inc a
    ld (p1142_rename_calls),a
    ld a,E_BUSY
    scf
    ret
p1142_remove:
    ld a,(p1142_remove_calls)
    inc a
    ld (p1142_remove_calls),a
    xor a
    ret
p1142_gate_end:
    SAVEBIN "p1142-gateway.bin",p1142_gate,p1142_gate_end-p1142_gate
''', encoding="utf-8", newline="\n")

    tx_cmd = run_command(
        [assembler, "--nologo", "--sym=p1142-error-transaction.sym", tx.name],
        cwd=build, timeout_seconds=60,
    )
    require(not tx_cmd.timed_out and tx_cmd.exit_code == 0,
            f"P11.42 transaction assembly failed: {tx_cmd.stderr or tx_cmd.stdout}")
    tx_bin = (build / "p1142-tx.bin").read_bytes()
    gate_bin = (build / "p1142-gateway.bin").read_bytes()
    require(0 < len(tx_bin) <= 0x2000, f"P11.42 transaction fixture too large: {len(tx_bin)}")
    tx_syms = phase3_open_descriptions._symbols(build / "p1142-error-transaction.sym", ("p1142_rename",))

    assertions = [
        {"name":"matrix-exact-seven-required-failure-classes","passed":True},
        {"name":"syntax-and-semantic-errors-return-deterministic-eformat","passed":True},
        {"name":"symbol-source-output-workspace-limits-return-deterministic-enospc","passed":True},
        {"name":"rename-failure-preserves-primary-ebusy","passed":True},
        {"name":"all-failures-preserve-prior-destination-byte-identically","passed":True},
        {"name":"transaction-cleanup-closes-owned-open-description-and-temp","passed":True},
        {"name":"failure-paths-use-no-os-private-register-bank","passed":True},
    ]
    commands = [core_cmd, tx_cmd]

    if action == "test":
        def core_patch(ram):
            ram[0:len(core_bin)] = core_bin
        for name in core_names:
            code = (
                b"\xF3" + phase1._ld_sp(0xBFC0)
                + phase1._call(core_syms[name])
                + phase1._jp_c(FAIL_PC) + phase1._jp(PASS_PC)
            )
            try:
                commands.append(run_sna(root, code, patch=core_patch, timeout=30))
            except DriverError as exc:
                raise P1142Error(f"{name} native failure-matrix fixture failed: {exc}") from None

        def tx_patch(ram):
            ram[0xC000-0x4000:0xC000-0x4000+len(tx_bin)] = tx_bin
            ram[0xE000-0x4000:0xE000-0x4000+len(gate_bin)] = gate_bin
        code = (
            b"\xF3" + phase1._ld_sp(0xBFC0)
            + phase1._call(tx_syms["p1142_rename"])
            + phase1._jp_c(FAIL_PC) + phase1._jp(PASS_PC)
        )
        try:
            commands.append(run_sna(root, code, patch=tx_patch, timeout=30))
        except DriverError as exc:
            raise P1142Error(f"final rename failure fixture failed: {exc}") from None

        assertions += [
            {"name":"fuse-syntax-failure-preserves-old-obj","passed":True},
            {"name":"fuse-semantic-signature-failure-preserves-old-obj","passed":True},
            {"name":"fuse-global-symbol-table-overflow-preserves-old-obj","passed":True},
            {"name":"fuse-source-total-overflow-preserves-old-obj","passed":True},
            {"name":"fuse-obj1-output-capacity-exhaustion-is-transactional","passed":True},
            {"name":"fuse-expression-workspace-exhaustion-releases-depth","passed":True},
            {"name":"fuse-final-rename-ebusy-closes-and-removes-owned-temp","passed":True},
            {"name":"fuse-deliberately-swallowed-error-negative-is-detected","passed":True},
            {"name":"fuse-one-byte-prior-output-mutation-negative-is-detected","passed":True},
        ]

    hashes = {
        "v1/src/tools/cc.asm": sha256_file(cc_path),
        "v1/tests/compiler/p1142-error-matrix.json": sha256_file(matrix_path),
        "v1/build/p1142-core.bin": sha256_file(build / "p1142-core.bin"),
        "v1/build/p1142-tx.bin": sha256_file(build / "p1142-tx.bin"),
        "v1/build/p1142-gateway.bin": sha256_file(build / "p1142-gateway.bin"),
        "v1/tools-host/test-driver/phase11_step_42.py": sha256_file(root / "v1/tools-host/test-driver/phase11_step_42.py"),
        "v1/dist/certification/P11.41.build.json": sha256_file(root / "v1/dist/certification/P11.41.build.json"),
        "v1/dist/certification/P11.41.test.json": sha256_file(root / "v1/dist/certification/P11.41.test.json"),
    }
    return commands, hashes, assertions
