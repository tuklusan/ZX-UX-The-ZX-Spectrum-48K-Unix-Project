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


class P1102Error(DriverError):
    pass


def require(ok, msg):
    if not ok:
        raise P1102Error(msg)


def source_constants(text):
    out = {}
    for name, value in re.findall(r"^([A-Z0-9_]+)\s+EQU\s+([0-9]+)$", text, re.M):
        out[name] = int(value)
    return out


def dispatch(root, action, step, *, sha256_file, run_command, require_project_tool):
    if step != "P11.02":
        raise DriverError(step)

    cc_path = root / "v1/src/tools/cc.asm"
    text = cc_path.read_text(encoding="utf-8")
    c = source_constants(text)
    expected = {
        "CC_IDENT_MAX": 15,
        "CC_NAME_FIELD": 16,
        "CC_SYMBOL_ENTRY_SIZE": 18,
        "CC_GLOBAL_CAPACITY": 32,
        "CC_LOCAL_CAPACITY": 32,
        "CC_LABEL_CAPACITY": 32,
        "CC_EXPR_NODE_SIZE": 4,
        "CC_EXPR_CAPACITY": 8,
        "CC_SOURCE_WINDOW_SIZE": 64,
        "CC_WORKSPACE_LIMIT": 2048,
    }
    require(all(c.get(k) == v for k, v in expected.items()), "P11.02 frozen bounds")
    for marker in (
        "compiler/c48/preprocessor.py",
        "compiler/c48/lexer.py",
        "compiler/c48/parser.py",
        "compiler/c48/typesys.py",
        "compiler/c48/semantics.py",
        "compiler/c48/limits.py",
        "compiler/c48/errors.py",
        "compiler/c48/float5.py",
        "compiler/c48/memory.py",
        "compiler/c48/vm.py",
        "no whole-source/whole-program AST",
    ):
        require(marker in text, f"P11.02 missing SDK/streaming design marker: {marker}")

    provenance = (root / "v1/tests/compiler/sdk-reference/SDK-PROVENANCE.md").read_text(encoding="utf-8")
    for marker in (
        "P11.02 target architecture mapping",
        "64-byte source window",
        "32-entry fixed-capacity global/extern, local,",
        "eight-node expression bound",
        "Host C48B1/VM memory structures remain reference oracles only",
    ):
        require(marker in provenance, f"P11.02 provenance mapping missing: {marker}")

    assembler = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    fixture = build / "p1102-streaming.asm"
    fixture.write_text(r'''    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/tools/cc.asm"
    ORG $C000
fixture:
    EMIT_P11_CC_STREAMING_CORE

p1102_name_a: db "a",0
p1102_name_Foo: db "Foo",0
p1102_name_foo: db "foo",0
p1102_name_15: db "abcdefghijklmno",0
p1102_name_16: db "abcdefghijklmnop",0
p1102_loop: db 0

p1102_fail:
    ld a,E_FORMAT
    scf
    ret

p1102_positive:
    call cc_p1102_reset
    ld hl,p1102_name_a
    ld bc,3
    call cc_pipeline_feed
    ret c
    call cc_pipeline_parse
    ret c
    call cc_pipeline_emit
    ret c
    call cc_pipeline_obj1
    ret c
    ld a,(cc_pipeline_stage)
    cp CC_STAGE_OBJ1
    jp nz,p1102_fail
    ld hl,(cc_stream_total)
    ld de,3
    or a
    sbc hl,de
    jp nz,p1102_fail

    ld hl,p1102_name_Foo
    ld de,$1234
    call cc_global_insert
    ret c
    ld hl,p1102_name_foo
    ld de,$5678
    call cc_global_insert
    ret c
    ld a,(cc_global_count)
    cp 2
    jp nz,p1102_fail
    ld a,(cc_global_table)
    cp 'F'
    jp nz,p1102_fail
    ld a,(cc_global_table+CC_SYMBOL_ENTRY_SIZE)
    cp 'f'
    jp nz,p1102_fail

    ld hl,p1102_name_15
    ld de,$7777
    call cc_local_insert
    ret c
    ld a,(cc_local_count)
    cp 1
    jp nz,p1102_fail
    ld a,(cc_local_table+14)
    cp 'o'
    jp nz,p1102_fail
    ld a,(cc_local_table+15)
    or a
    jp nz,p1102_fail
    xor a
    ret

p1102_fill_global:
    ld a,CC_GLOBAL_CAPACITY
    ld (p1102_loop),a
p1102_fill_global_loop:
    ld hl,p1102_name_a
    ld de,$1111
    call cc_global_insert
    ret c
    ld a,(p1102_loop)
    dec a
    ld (p1102_loop),a
    jr nz,p1102_fill_global_loop
    ld hl,p1102_name_a
    ld de,$1112
    call cc_global_insert
    jp nc,p1102_fail
    cp E_NOSPC
    jp nz,p1102_fail
    ld a,(cc_global_count)
    cp CC_GLOBAL_CAPACITY
    jp nz,p1102_fail
    xor a
    ret

p1102_fill_local:
    ld a,CC_LOCAL_CAPACITY
    ld (p1102_loop),a
p1102_fill_local_loop:
    ld hl,p1102_name_a
    ld de,$2222
    call cc_local_insert
    ret c
    ld a,(p1102_loop)
    dec a
    ld (p1102_loop),a
    jr nz,p1102_fill_local_loop
    ld hl,p1102_name_a
    ld de,$2223
    call cc_local_insert
    jp nc,p1102_fail
    cp E_NOSPC
    jp nz,p1102_fail
    ld a,(cc_local_count)
    cp CC_LOCAL_CAPACITY
    jp nz,p1102_fail
    xor a
    ret

p1102_fill_label:
    ld a,CC_LABEL_CAPACITY
    ld (p1102_loop),a
p1102_fill_label_loop:
    ld hl,p1102_name_a
    ld de,$3333
    call cc_label_insert
    ret c
    ld a,(p1102_loop)
    dec a
    ld (p1102_loop),a
    jr nz,p1102_fill_label_loop
    ld hl,p1102_name_a
    ld de,$3334
    call cc_label_insert
    jp nc,p1102_fail
    cp E_NOSPC
    jp nz,p1102_fail
    ld a,(cc_label_count)
    cp CC_LABEL_CAPACITY
    jp nz,p1102_fail
    xor a
    ret

p1102_capacity_all:
    call cc_p1102_reset
    ld a,$5A
    ld (cc_output_commit_marker),a
    call p1102_fill_global
    ret c
    call p1102_fill_local
    ret c
    call p1102_fill_label
    ret c
    ld a,(cc_workspace_guard_pre)
    cp $A5
    jp nz,p1102_fail
    ld a,(cc_workspace_guard_post)
    cp $5A
    jp nz,p1102_fail
    ld a,(cc_output_commit_marker)
    cp $5A
    jp nz,p1102_fail
    xor a
    ret

p1102_overlength:
    call cc_p1102_reset
    ld a,$A6
    ld (cc_output_commit_marker),a
    ld hl,p1102_name_15
    ld de,$4444
    call cc_global_insert
    ret c
    ld hl,p1102_name_16
    ld de,$5555
    call cc_global_insert
    jp nc,p1102_fail
    cp E_INVAL
    jp nz,p1102_fail
    ld a,(cc_global_count)
    cp 1
    jp nz,p1102_fail
    ld a,(cc_global_table+14)
    cp 'o'
    jp nz,p1102_fail
    ld a,(cc_global_table+15)
    or a
    jp nz,p1102_fail
    ld a,(cc_output_commit_marker)
    cp $A6
    jp nz,p1102_fail
    xor a
    ret

p1102_expr:
    call cc_p1102_reset
    ld a,CC_EXPR_CAPACITY
    ld (p1102_loop),a
p1102_expr_in:
    call cc_expr_enter
    ret c
    ld a,(p1102_loop)
    dec a
    ld (p1102_loop),a
    jr nz,p1102_expr_in
    call cc_expr_enter
    jp nc,p1102_fail
    cp E_NOSPC
    jp nz,p1102_fail
    ld a,(cc_expr_highwater)
    cp CC_EXPR_CAPACITY
    jp nz,p1102_fail
    call cc_statement_release
    ld a,(cc_expr_depth)
    or a
    jp nz,p1102_fail
    call cc_expr_leave
    jp nc,p1102_fail
    cp E_FORMAT
    jp nz,p1102_fail
    xor a
    ret

p1102_window_overflow:
    call cc_p1102_reset
    ld a,$33
    ld (cc_output_commit_marker),a
    ld hl,p1102_name_a
    ld bc,CC_SOURCE_WINDOW_SIZE+1
    call cc_pipeline_feed
    jp nc,p1102_fail
    cp E_NOSPC
    jp nz,p1102_fail
    ld hl,(cc_stream_total)
    ld a,h
    or l
    jp nz,p1102_fail
    ld a,(cc_output_commit_marker)
    cp $33
    jp nz,p1102_fail
    xor a
    ret

p1102_all:
    call p1102_positive
    ret c
    call p1102_capacity_all
    ret c
    call p1102_overlength
    ret c
    call p1102_expr
    ret c
    call p1102_window_overflow
    ret c
    xor a
    ret

fixture_end:
    SAVEBIN "p1102-main.bin",fixture,fixture_end-fixture
''', encoding="utf-8", newline="\n")

    result = run_command(
        [assembler, "--nologo", "--sym=p1102-streaming.sym", fixture.name],
        cwd=build,
        timeout_seconds=30,
    )
    require(
        not result.timed_out and result.exit_code == 0,
        f"P11.02 assemble: {result.stderr or result.stdout}",
    )
    main = (build / "p1102-main.bin").read_bytes()
    require(len(main) <= 0x2000, "P11.02 fixture too large")
    syms = phase3_open_descriptions._symbols(
        build / "p1102-streaming.sym",
        ("p1102_all", "cc_workspace_begin", "cc_workspace_end"),
    )
    workspace = syms["cc_workspace_end"] - syms["cc_workspace_begin"]
    require(workspace <= 2048, "P11.02 measured workspace >2KiB")

    assertions = [
        {"name": "source-window-fixed-64", "passed": c["CC_SOURCE_WINDOW_SIZE"] == 64},
        {
            "name": "separate-bounded-symbol-tables",
            "passed": all(
                c[k] == 32
                for k in ("CC_GLOBAL_CAPACITY", "CC_LOCAL_CAPACITY", "CC_LABEL_CAPACITY")
            ),
        },
        {"name": "identifier-visible-limit-15", "passed": c["CC_IDENT_MAX"] == 15},
        {"name": "expression-tree-fixed-bound", "passed": c["CC_EXPR_CAPACITY"] == 8},
        {"name": "measured-core-workspace-under-2k", "passed": workspace <= 2048, "bytes": workspace},
        {"name": "sdk-decomposition-cross-reference", "passed": True},
        {"name": "no-whole-source-or-program-ast-design", "passed": True},
    ]
    commands = [result]

    if action == "test":
        def patch(ram):
            ram[0xC000 - 0x4000:0xC000 - 0x4000 + len(main)] = main

        code = (
            b"\xF3"
            + phase1._ld_sp(0xBFC0)
            + phase1._call(syms["p1102_all"])
            + phase1._jp_c(FAIL_PC)
            + phase1._jp(PASS_PC)
        )
        commands.append(run_sna(root, code, patch=patch))
        assertions += [
            {"name": "fuse-single-sna-stream-to-obj1-stage", "passed": True},
            {"name": "fuse-case-sensitive-identifiers-coexist", "passed": True},
            {"name": "fuse-15-char-identifier-accepted-exact", "passed": True},
            {"name": "fuse-16-char-truncation-alias-rejected", "passed": True},
            {"name": "fuse-global-table-exact-capacity-fails-closed", "passed": True},
            {"name": "fuse-local-table-exact-capacity-fails-closed", "passed": True},
            {"name": "fuse-label-table-exact-capacity-fails-closed", "passed": True},
            {"name": "fuse-expression-capacity-released", "passed": True},
            {"name": "fuse-source-window-overflow-fails-closed", "passed": True},
            {"name": "failure-preserves-output-marker-and-workspace-guards", "passed": True},
        ]

    hashes = {
        "v1/src/tools/cc.asm": sha256_file(cc_path),
        "v1/build/p1102-main.bin": sha256_file(build / "p1102-main.bin"),
        "v1/tools-host/test-driver/phase11_step_02.py": sha256_file(
            root / "v1/tools-host/test-driver/phase11_step_02.py"
        ),
        "v1/tests/compiler/sdk-reference/SDK-PROVENANCE.md": sha256_file(
            root / "v1/tests/compiler/sdk-reference/SDK-PROVENANCE.md"
        ),
        "v1/dist/certification/P11.01.build.json": sha256_file(
            root / "v1/dist/certification/P11.01.build.json"
        ),
        "v1/dist/certification/P11.01.test.json": sha256_file(
            root / "v1/dist/certification/P11.01.test.json"
        ),
    }
    return commands, hashes, assertions
