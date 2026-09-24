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

import hashlib
import importlib.util
import json
import struct
import sys

import phase1
import phase3_open_descriptions
from driver_core import DriverError
from fuse_harness import PASS_PC, FAIL_PC, run_sna


class P1035Error(DriverError):
    pass


def require(ok, msg):
    if not ok:
        raise P1035Error(msg)


def crc16(data):
    crc = 0xFFFF
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc


def build_host_mex(g):
    image = bytearray(g["image_size"])
    for key, value in g["patched_words"].items():
        struct.pack_into("<H", image, int(key), value)
    relocs = b"".join(struct.pack("<H", x) for x in g["runtime_relocations"])
    body = bytes(image) + relocs
    h = bytearray(24)
    h[:4] = b"MEX1"
    h[4] = 1
    h[5] = 0
    struct.pack_into("<H", h, 6, 24)
    struct.pack_into("<H", h, 8, g["image_size"])
    struct.pack_into("<H", h, 10, g["final_bss_size"])
    struct.pack_into("<H", h, 12, g["entry"])
    struct.pack_into("<H", h, 14, g["minimum_stack"])
    struct.pack_into("<H", h, 16, len(g["runtime_relocations"]))
    struct.pack_into("<H", h, 18, 24 + g["image_size"])
    struct.pack_into("<H", h, 20, crc16(body))
    struct.pack_into("<H", h, 22, 0)
    struct.pack_into("<H", h, 22, crc16(bytes(h)))
    return bytes(h) + body


def dispatch(root, action, step, *, sha256_file, run_command, require_project_tool):
    if step != "P10.35":
        raise DriverError(step)

    golden_path = root / "v1/tests/compiler/link_golden/phase10-multimodule.json"
    g = json.loads(golden_path.read_text(encoding="utf-8"))
    require(g["schema"] == 1, "P10.35 golden schema")
    require(g["archive_selection"] == [2, 3, 1], "P10.35 archive fixed point")
    require(g["module_ids"] == [0, 10, 11, 2, 3, 1], "P10.35 module order")
    require(g["text_bases"] == [0, 4, 8, 14, 18, 20], "P10.35 TEXT bases")
    require(g["bss_bases"] == [0, 2, 4, 8, 8, 10], "P10.35 BSS bases")
    require(g["symbols"] == {"_start":0,"main":5,"global_bss":29,"CONST":4660}, "P10.35 symbols")
    mex = build_host_mex(g)
    require(mex.hex() == g["mex1_hex"], "P10.35 host MEX1 bytes")
    require(hashlib.sha256(mex).hexdigest() == g["mex1_sha256"], "P10.35 host MEX1 SHA-256")
    require([0,11,10,2,3,1] != g["module_ids"], "P10.35 perturbed order must differ")

    inspector_path = require_project_tool(root, "v1/tools-host/inspect-mex/inspect.py")
    spec = importlib.util.spec_from_file_location("zxux_p1035_mex", inspector_path)
    require(spec is not None and spec.loader is not None, "P10.35 inspector import")
    inspector = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = inspector
    spec.loader.exec_module(inspector)
    decoded = inspector.inspect_bytes(mex, base=0x6000)
    require(decoded["image_size"] == 24 and decoded["bss_size"] == 18, "P10.35 host MEX1 dimensions")
    require(decoded["relocations"] == [4,10] and decoded["entry_offset"] == 0, "P10.35 host MEX1 reloc/entry")

    assembler = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    fixture = build / "p1035-golden.asm"
    fixture.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../../tools/ld.asm"
    ORG $C000
fixture:
    EMIT_P10_LD_ARCHIVE_SELECT_ROUTINES
    EMIT_P10_LD_LAYOUT_ROUTINES
    EMIT_P10_LD_SYMBOL_RESOLVE_ROUTINES
    EMIT_P10_LD_RELOCATION_ROUTINES
    EMIT_P10_LD_DEFAULT_ENTRY_ROUTINES
    EMIT_P10_LD_STACK_OPTION_ROUTINES
    EMIT_P10_LD_HEAP_OPTION_ROUTINES
    EMIT_P10_LD_MEX1_WRITER_ROUTINES

p1035_users: db 10,11
p1035_users_bad: db 11,10
p1035_sizes:
    dw 3,1
    dw 4,2
    dw 5,3
    dw 3,0
    dw 2,1
    dw 3,0

p1035_defs:
    db "_start"
    defs 10,0
    dw 0
    db 1
    dw 0
    dw 0
    db "main"
    defs 12,0
    dw 1
    db 1
    dw 4
    dw 2
    db "global_bss"
    defs 6,0
    dw 1
    db 2
    dw 8
    dw 4
    db "CONST"
    defs 11,0
    dw $1234
    db 3
    dw 0
    dw 0

p1035_q_main:
    db "main"
    defs 12,0
p1035_q_bss:
    db "global_bss"
    defs 6,0
p1035_q_const:
    db "CONST"
    defs 11,0

p1035_image: defs 24,0
p1035_out: defs 64,0
p1035_golden:
    db $4d,$45,$58,$31,$01,$00,$18,$00,$18,$00,$12,$00,$00,$00,$00,$02
    db $02,$00,$30,$00,$9a,$f6,$22,$50,$00,$00,$00,$00,$1c,$00,$00,$00
    db $00,$00,$06,$00,$00,$00,$00,$00,$00,$00,$36,$12,$00,$00,$00,$00
    db $04,$00,$0a,$00

p1035_fail:
    ld a,E_FORMAT
    scf
    ret

p1035_word_eq:
    ; HL=value, DE=expected
    or a
    sbc hl,de
    ret

p1035_check_order:
    ld a,(ld_p1024_order_count)
    cp 6
    jp nz,p1035_fail
    ld hl,ld_p1024_order
    ld de,p1035_expected_order
    ld b,6
p1035_order_loop:
    ld a,(de)
    cp (hl)
    jp nz,p1035_fail
    inc hl
    inc de
    djnz p1035_order_loop
    xor a
    ret
p1035_expected_order: db 0,10,11,2,3,1

p1035_check_layout:
    ld hl,(ld_p1024_image_size)
    ld de,24
    call p1035_word_eq
    jp nz,p1035_fail
    ld hl,(ld_p1024_heap_base)
    ld de,10
    call p1035_word_eq
    jp nz,p1035_fail
    ld hl,(ld_p1024_final_bss)
    ld de,18
    call p1035_word_eq
    jp nz,p1035_fail
    ld hl,ld_p1024_text_bases
    ld de,p1035_text_expected
    ld b,12
p1035_text_cmp:
    ld a,(de)
    cp (hl)
    jp nz,p1035_fail
    inc de
    inc hl
    djnz p1035_text_cmp
    ld hl,ld_p1024_bss_bases
    ld de,p1035_bss_expected
    ld b,12
p1035_bss_cmp:
    ld a,(de)
    cp (hl)
    jp nz,p1035_fail
    inc de
    inc hl
    djnz p1035_bss_cmp
    xor a
    ret
p1035_text_expected: dw 0,4,8,14,18,20
p1035_bss_expected: dw 0,2,4,8,8,10

p1035_resolve:
    ld hl,24
    ld (ld_p1025_image_size),hl
    ld hl,p1035_q_main
    ld de,p1035_defs
    ld b,4
    call ld_p1025_resolve
    ret c
    ld hl,(ld_p1025_resolved_value)
    ld de,5
    call p1035_word_eq
    jp nz,p1035_fail

    ld hl,p1035_q_bss
    ld de,p1035_defs
    ld b,4
    call ld_p1025_resolve
    ret c
    ld hl,(ld_p1025_resolved_value)
    ld de,29
    call p1035_word_eq
    jp nz,p1035_fail

    ld hl,p1035_q_const
    ld de,p1035_defs
    ld b,4
    call ld_p1025_resolve
    ret c
    ld hl,(ld_p1025_resolved_value)
    ld de,$1234
    call p1035_word_eq
    jp nz,p1035_fail

    ld de,p1035_defs
    ld b,4
    call ld_p1027_default_entry
    ret c
    ld hl,(ld_p1027_entry)
    ld de,0
    call p1035_word_eq
    jp nz,p1035_fail
    xor a
    ret

p1035_relocs:
    ld hl,p1035_image
    ld (ld_p1026_image),hl
    ld hl,24
    ld (ld_p1026_image_size),hl
    call ld_p1026_reset

    ; TEXT main = 5, addend +1 at final patch location 10.
    ld hl,10
    ld (ld_p1026_patch_loc),hl
    ld hl,5
    ld (ld_p1026_symbol_value),hl
    ld hl,1
    ld (ld_p1026_addend),hl
    ld a,1
    ld (ld_p1026_symbol_section),a
    call ld_p1026_apply
    ret c

    ; BSS global = 29, addend -1 at final patch location 4.
    ld hl,4
    ld (ld_p1026_patch_loc),hl
    ld hl,29
    ld (ld_p1026_symbol_value),hl
    ld hl,$FFFF
    ld (ld_p1026_addend),hl
    ld a,2
    ld (ld_p1026_symbol_section),a
    call ld_p1026_apply
    ret c

    ; ABS constant = 0x1234, addend +2 at final patch location 18.
    ld hl,18
    ld (ld_p1026_patch_loc),hl
    ld hl,$1234
    ld (ld_p1026_symbol_value),hl
    ld hl,2
    ld (ld_p1026_addend),hl
    ld a,3
    ld (ld_p1026_symbol_section),a
    call ld_p1026_apply
    ret c

    call ld_p1026_finalize
    ret c
    ld a,(ld_p1026_rel_count)
    cp 2
    jp nz,p1035_fail
    ld hl,(ld_p1026_rel_locs)
    ld de,4
    call p1035_word_eq
    jp nz,p1035_fail
    ld hl,(ld_p1026_rel_locs+2)
    ld de,10
    call p1035_word_eq
    jp nz,p1035_fail
    xor a
    ret

p1035_write_mex:
    call ld_p1030_stack_default
    ret c
    ld hl,24
    ld de,10
    ld bc,8
    call ld_p1031_place
    ret c
    ld hl,(ld_p1031_mex1_bss_size)
    ld de,18
    call p1035_word_eq
    jp nz,p1035_fail
    ld hl,(ld_p1031_heap_start)
    ld de,34
    call p1035_word_eq
    jp nz,p1035_fail
    ld hl,(ld_p1031_heap_end)
    ld de,42
    call p1035_word_eq
    jp nz,p1035_fail

    ld hl,p1035_image
    ld (ld_p1032_image),hl
    ld hl,24
    ld (ld_p1032_image_size),hl
    ld hl,18
    ld (ld_p1032_bss_size),hl
    ld hl,(ld_p1027_entry)
    ld (ld_p1032_entry),hl
    ld hl,(ld_p1030_min_fast_stack)
    ld (ld_p1032_stack),hl
    ld hl,ld_p1026_rel_locs
    ld (ld_p1032_relocs),hl
    ld hl,2
    ld (ld_p1032_reloc_count),hl
    ld hl,p1035_out
    ld (ld_p1032_output),hl
    ld hl,64
    ld (ld_p1032_capacity),hl
    call ld_p1032_write
    ret c

    ld hl,(ld_p1032_stored_length)
    ld de,52
    call p1035_word_eq
    jp nz,p1035_fail
    ld hl,p1035_out
    ld de,p1035_golden
    ld b,52
p1035_mex_cmp:
    ld a,(de)
    cp (hl)
    jp nz,p1035_fail
    inc de
    inc hl
    djnz p1035_mex_cmp
    xor a
    ret

p1035_golden_link:
    ld a,LD_P1023_NEED_PUTS|LD_P1023_NEED_EXIT
    call ld_p1023_select
    ret c
    ld a,(ld_p1023_selected_count)
    cp 3
    jp nz,p1035_fail
    ld hl,ld_p1023_selected_order
    ld de,p1035_archive_expected
    ld b,3
p1035_archive_cmp:
    ld a,(de)
    cp (hl)
    jp nz,p1035_fail
    inc de
    inc hl
    djnz p1035_archive_cmp

    xor a
    ld (ld_p1024_nostart),a
    ld hl,p1035_users
    ld b,2
    ld de,ld_p1023_selected_order
    ld c,3
    call ld_p1024_build_order
    ret c
    call p1035_check_order
    ret c

    ld hl,p1035_sizes
    ld b,6
    ld de,8
    call ld_p1024_layout
    ret c
    call p1035_check_layout
    ret c
    call p1035_resolve
    ret c
    call p1035_relocs
    ret c
    call p1035_write_mex
    ret c
    xor a
    ret
p1035_archive_expected: db 2,3,1

p1035_perturbed_order:
    xor a
    ld (ld_p1024_nostart),a
    ld hl,p1035_users_bad
    ld b,2
    ld de,p1035_archive_expected
    ld c,3
    call ld_p1024_build_order
    ret c
    ; Exact golden order must no longer compare equal.
    ld a,(ld_p1024_order+1)
    cp 10
    jp z,p1035_fail
    ld a,E_FORMAT
    scf
    ret

fixture_end:
    SAVEBIN "p1035-main.bin",fixture,fixture_end-fixture
""", encoding="utf-8", newline="\n")

    result = run_command([assembler, "--nologo", "--sym=p1035-golden.sym", fixture.name], cwd=build, timeout_seconds=30)
    require(not result.timed_out and result.exit_code == 0, f"P10.35 assemble: {result.stderr or result.stdout}")
    main = (build / "p1035-main.bin").read_bytes()
    require(len(main) <= 0x4000, "P10.35 fixture exceeds available upper RAM")
    syms = phase3_open_descriptions._symbols(build / "p1035-golden.sym", ("p1035_golden_link","p1035_perturbed_order"))
    assertions = [
        {"name":"host-golden-order-symbols-layout","passed":True},
        {"name":"host-golden-mex1-byte-exact","passed":True},
        {"name":"host-golden-mex1-sha256","passed":True},
        {"name":"host-inspector-accepts-golden","passed":True},
        {"name":"perturbed-input-order-differs","passed":True},
    ]
    if action == "test":
        def patch(ram):
            ram[0xC000-0x4000:0xC000-0x4000+len(main)] = main
        code = b"\xF3" + phase1._ld_sp(0xBFC0) + phase1._call(syms["p1035_golden_link"]) + phase1._jp_c(FAIL_PC) + phase1._jp(PASS_PC)
        run_sna(root, code, patch=patch, timeout=30)
        code = b"\xF3" + phase1._ld_sp(0xBFC0) + phase1._call(syms["p1035_perturbed_order"]) + b"\xD2" + phase1._word(FAIL_PC) + phase1._jp(PASS_PC)
        run_sna(root, code, patch=patch, timeout=30)
        assertions += [
            {"name":"fuse-target-golden-byte-exact","passed":True},
            {"name":"fuse-target-archive-fixed-point","passed":True},
            {"name":"fuse-target-layout-symbol-relocation-entry","passed":True},
            {"name":"fuse-perturbed-order-detected","passed":True},
        ]

    hashes = {
        "tools/ld.asm": sha256_file(root / "tools/ld.asm"),
        "v1/tests/compiler/link_golden/phase10-multimodule.json": sha256_file(golden_path),
        "v1/build/p1035-main.bin": sha256_file(build / "p1035-main.bin"),
        "v1/tools-host/test-driver/phase10_step_35.py": sha256_file(root / "v1/tools-host/test-driver/phase10_step_35.py"),
        "v1/tools-host/inspect-mex/inspect.py": sha256_file(inspector_path),
        "v1/dist/certification/P10.34.build.json": sha256_file(root / "v1/dist/certification/P10.34.build.json"),
        "v1/dist/certification/P10.34.test.json": sha256_file(root / "v1/dist/certification/P10.34.test.json"),
    }
    return [result], hashes, assertions
