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

import importlib.util
import phase1
import phase3_open_descriptions
from driver_core import DriverError
from fuse_harness import PASS_PC, FAIL_PC, run_sna


class P1032Error(DriverError):
    pass


def require(ok, msg):
    if not ok:
        raise P1032Error(msg)


GOLDEN = bytes.fromhex("4d45583101001800030000000200400001001b003b03fda20100c90000")


def dispatch(root, action, step, *, sha256_file, run_command, require_project_tool):
    if step != "P10.32":
        raise DriverError(step)
    source = (root / "tools/ld.asm").read_text(encoding="utf-8")
    assertions = [
        {"name":"mex1-magic-version-header","passed":"ld_p1032_write:" in source and "LD_P1032_HEADER_SIZE EQU 24" in source},
        {"name":"deterministic-image-reloc-layout","passed":"ld_p1032_reloc_offset" in source and "ld_p1032_stored_length" in source},
        {"name":"body-and-header-crc","passed":"ld_p1032_crc16:" in source and "Header CRC is calculated" in source},
        {"name":"reloc-valid-before-write","passed":"ld_p1032_rel_loop:" in source and "ld_p1032_validate:" in source},
    ]
    require(all(a["passed"] for a in assertions), "P10.32 static MEX1 writer contract failure")

    inspector_path = require_project_tool(root, "v1/tools-host/inspect-mex/inspect.py")
    spec = importlib.util.spec_from_file_location("p1032_mex", inspector_path)
    require(spec is not None and spec.loader is not None, "cannot load MEX1 inspector")
    inspector = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(inspector)
    one = inspector.inspect_bytes(GOLDEN, base=0x6000)
    two = inspector.inspect_bytes(GOLDEN, base=0x7000)
    require(one["stored_length"] == len(GOLDEN) and two["stored_length"] == len(GOLDEN), "two-base host inspect failed")
    assertions += [
        {"name":"host-inspect-base-6000","passed":True},
        {"name":"host-inspect-base-7000","passed":True},
    ]

    assembler = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    fixture = build / "p1032-mex1.asm"
    fixture.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../../tools/ld.asm"
    ORG $C000
fixture:
    EMIT_P10_LD_MEX1_WRITER_ROUTINES

p1032_image: db 1,0,$C9
p1032_relocs: dw 0
p1032_bad_relocs: dw 2
p1032_out: defs 64,0
p1032_golden:
    db $4d,$45,$58,$31,$01,$00,$18,$00,$03,$00,$00,$00
    db $02,$00,$40,$00,$01,$00,$1b,$00,$3b,$03,$fd,$a2
    db $01,$00,$c9,$00,$00

p1032_setup:
    ld hl,p1032_image
    ld (ld_p1032_image),hl
    ld hl,3
    ld (ld_p1032_image_size),hl
    ld hl,0
    ld (ld_p1032_bss_size),hl
    ld hl,2
    ld (ld_p1032_entry),hl
    ld hl,64
    ld (ld_p1032_stack),hl
    ld hl,p1032_relocs
    ld (ld_p1032_relocs),hl
    ld hl,1
    ld (ld_p1032_reloc_count),hl
    ld hl,p1032_out
    ld (ld_p1032_output),hl
    ld hl,64
    ld (ld_p1032_capacity),hl
    ret

p1032_write_golden:
    call p1032_setup
    call ld_p1032_write
    ret c
    ld hl,(ld_p1032_stored_length)
    ld de,29
    or a
    sbc hl,de
    jp nz,p1032_fail
    ld hl,p1032_out
    ld de,p1032_golden
    ld b,29
p1032_cmp:
    ld a,(de)
    cp (hl)
    jp nz,p1032_fail
    inc de
    inc hl
    djnz p1032_cmp
    xor a
    ret

p1032_bad_reloc:
    call p1032_setup
    ld hl,p1032_bad_relocs
    ld (ld_p1032_relocs),hl
    call ld_p1032_write
    ret nc
    cp E_FORMAT
    jp nz,p1032_fail
    scf
    ret

p1032_fail:
    ld a,E_FORMAT
    scf
    ret

fixture_end:
    SAVEBIN "p1032-main.bin",fixture,fixture_end-fixture
""", encoding="utf-8", newline="\n")

    result = run_command([assembler, "--nologo", "--sym=p1032-mex1.sym", fixture.name], cwd=build, timeout_seconds=30)
    require(not result.timed_out and result.exit_code == 0, f"P10.32 assemble: {result.stderr or result.stdout}")
    main = (build / "p1032-main.bin").read_bytes()
    syms = phase3_open_descriptions._symbols(build / "p1032-mex1.sym", ("p1032_write_golden","p1032_bad_reloc"))
    if action == "test":
        def patch(ram):
            ram[0xC000-0x4000:0xC000-0x4000+len(main)] = main
        code = b"\xF3" + phase1._ld_sp(0xBFC0) + phase1._call(syms["p1032_write_golden"]) + phase1._jp_c(FAIL_PC) + phase1._jp(PASS_PC)
        run_sna(root, code, patch=patch)
        code = b"\xF3" + phase1._ld_sp(0xBFC0) + phase1._call(syms["p1032_bad_reloc"]) + b"\xD2" + phase1._word(FAIL_PC) + phase1._jp(PASS_PC)
        run_sna(root, code, patch=patch)
        assertions += [
            {"name":"fuse-native-writer-byte-exact","passed":True},
            {"name":"fuse-invalid-relocation-rejected-before-commit","passed":True},
        ]
    hashes = {
        "tools/ld.asm": sha256_file(root / "tools/ld.asm"),
        "v1/build/p1032-main.bin": sha256_file(build / "p1032-main.bin"),
        "v1/tools-host/test-driver/phase10_step_32.py": sha256_file(root / "v1/tools-host/test-driver/phase10_step_32.py"),
        "v1/tools-host/inspect-mex/inspect.py": sha256_file(inspector_path),
        "v1/dist/certification/P10.31.build.json": sha256_file(root / "v1/dist/certification/P10.31.build.json"),
        "v1/dist/certification/P10.31.test.json": sha256_file(root / "v1/dist/certification/P10.31.test.json"),
    }
    return [result], hashes, assertions
