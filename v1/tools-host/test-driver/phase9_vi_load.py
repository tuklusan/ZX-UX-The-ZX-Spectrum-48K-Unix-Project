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
from phase8_common import inspect_mex, make_tap, mex1, word

BASE = 0xC000
GATE = 0xE000
PATH = 0xA000
TYPE = 0xA300
READ_ERROR = 0xA301
OPEN_COUNT = 0xA310
CLOSE_COUNT = 0xA311
READ_DONE = 0xA312


class P902Error(DriverError):
    pass


def require(value, message):
    if not value:
        raise P902Error(message)


def expect_byte(address, value):
    return b"\x3A" + word(address) + bytes((0xFE, value & 0xFF)) + phase1._jp_nz(FAIL_PC)


def expect_word(address, value):
    return expect_byte(address, value & 0xFF) + expect_byte(address + 1, value >> 8)


def patch(image, gateway, type_id, read_error):
    def apply(ram):
        ram[BASE - 0x4000 : BASE - 0x4000 + len(image)] = image
        ram[GATE - 0x4000 : GATE - 0x4000 + len(gateway)] = gateway
        ram[PATH - 0x4000 : PATH - 0x4000 + 10] = b"/tmp/x\0\0\0\0"
        ram[TYPE - 0x4000] = type_id
        ram[READ_ERROR - 0x4000] = read_error
        ram[OPEN_COUNT - 0x4000 : READ_DONE - 0x4000 + 1] = b"\0\0\0"
    return apply


def dispatch(root, action, step, *, sha256_file, run_command, require_project_tool):
    if step != "P9.02":
        raise DriverError(step)

    source = root / "tools/vi.asm"
    text = source.read_text(encoding="utf-8")
    plan = (root / "docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md").read_text(encoding="utf-8")
    assertions = [
        {"name": "canonical-p902-present", "passed": "## P9.02 - Buffer load/type validation" in plan},
        {"name": "documented-editable-types-only", "passed": all(x in text for x in ("OBJ_TXT", "OBJ_ASM", "OBJ_C", "OBJ_CFG"))},
        {"name": "wrong-type-format-rejection", "passed": "ld a,E_FORMAT" in text},
        {"name": "source-open-read-only", "passed": "ld c,O_READ" in text and "ld a,SYS_OPEN" in text},
        {"name": "complete-load-closes-source", "passed": "vi_load_eof:" in text and "call vi_close_source" in text},
        {"name": "ready-only-after-close", "passed": text.index("call vi_close_source", text.index("vi_load_eof:")) < text.index("ld (vi_buffer_ready),a", text.index("vi_load_eof:"))},
        {"name": "read-error-closes-source", "passed": "vi_load_stream_error:" in text and "call vi_close_source" in text[text.index("vi_load_stream_error:"):]},
    ]
    require(all(item["passed"] for item in assertions), "P9.02 static contract failure")

    assembler = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    fixture = build / "p902-vi.asm"
    fixture.write_text(
        """    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../../tools/vi.asm"
    ORG $C000
fixture:
    EMIT_P901_VI_ROUTINES
fixture_end:
    SAVEBIN "p902-vi.bin",fixture,fixture_end-fixture
""",
        encoding="utf-8",
        newline="\n",
    )
    fixture_result = run_command(
        [assembler, "--nologo", "--lst=p902-vi.lst", "--sym=p902-vi.sym", fixture.name],
        cwd=build,
        timeout_seconds=30,
    )
    require(not fixture_result.timed_out and fixture_result.exit_code == 0, f"P9.02 assemble: {fixture_result.stderr or fixture_result.stdout}")
    image = (build / "p902-vi.bin").read_bytes()
    require(256 < len(image) < 4096, "P9.02 vi image size implausible")

    mex_path = build / "p902-vi.mex1"
    mex_path.write_bytes(mex1(image))
    try:
        inspect_result = inspect_mex(root, mex_path, run_command, require_project_tool)
        tap_path = make_tap(root, build, "vi", "p902", mex_path)
    except RuntimeError as exc:
        raise P902Error(str(exc)) from exc

    gateway_source = build / "p902-gateway.asm"
    gateway_source.write_text(
        """    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    ORG $E000
gate:
    cp SYS_STAT
    jr z,g_stat
    cp SYS_OPEN
    jr z,g_open
    cp SYS_READ
    jr z,g_read
    cp SYS_CLOSE
    jr z,g_close
    ld a,E_NOTSUP
    scf
    ret
g_stat:
    inc hl
    inc hl
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld a,($A300)
    ld (de),a
    inc de
    xor a
    ld b,9
g_stat_zero:
    ld (de),a
    inc de
    djnz g_stat_zero
    xor a
    ret
g_open:
    ld a,($A310)
    inc a
    ld ($A310),a
    ld hl,3
    xor a
    ret
g_read:
    ld a,($A301)
    or a
    jr z,g_read_data
    ld a,E_IO
    scf
    ret
g_read_data:
    ld a,($A312)
    or a
    jr nz,g_eof
    ld de,g_data
    ex de,hl
    ld bc,4
    ldir
    ld a,1
    ld ($A312),a
    ld hl,4
    xor a
    ret
g_eof:
    ld hl,0
    xor a
    ret
g_close:
    ld a,($A311)
    inc a
    ld ($A311),a
    xor a
    ret
g_data: db 'M','i','X',10
gate_end:
    SAVEBIN "p902-gateway.bin",gate,gate_end-gate
""",
        encoding="utf-8",
        newline="\n",
    )
    gateway_result = run_command(
        [assembler, "--nologo", "--lst=p902-gateway.lst", "--sym=p902-gateway.sym", gateway_source.name],
        cwd=build,
        timeout_seconds=30,
    )
    require(not gateway_result.timed_out and gateway_result.exit_code == 0, f"P9.02 gateway: {gateway_result.stderr or gateway_result.stdout}")

    if action == "test":
        symbols = phase3_open_descriptions._symbols(
            build / "p902-vi.sym",
            ("vi_p902_load", "vi_buffer", "vi_buffer_len", "vi_source_open", "vi_buffer_ready",
             "OBJ_TXT", "OBJ_ASM", "OBJ_C", "OBJ_CFG", "OBJ_BIN", "E_FORMAT", "E_IO"),
        )
        gateway = (build / "p902-gateway.bin").read_bytes()
        for type_name in ("OBJ_TXT", "OBJ_ASM", "OBJ_C", "OBJ_CFG"):
            code = bytearray(b"\xF3" + phase1._ld_sp(0xBFC0) + phase1._ld_hl(PATH) + phase1._call(symbols["vi_p902_load"]) + phase1._jp_c(FAIL_PC))
            code += expect_word(symbols["vi_buffer_len"], 4)
            for offset, value in enumerate(b"MiX\n"):
                code += expect_byte(symbols["vi_buffer"] + offset, value)
            code += expect_byte(symbols["vi_source_open"], 0)
            code += expect_byte(symbols["vi_buffer_ready"], 1)
            code += expect_byte(OPEN_COUNT, 1) + expect_byte(CLOSE_COUNT, 1)
            code += phase1._jp(PASS_PC)
            run_sna(root, bytes(code), patch=patch(image, gateway, symbols[type_name], 0))

        code = bytearray(b"\xF3" + phase1._ld_sp(0xBFC0) + phase1._ld_hl(PATH) + phase1._call(symbols["vi_p902_load"]))
        code += phase1._jp_nc(FAIL_PC)
        code += b"\xFE" + bytes((symbols["E_FORMAT"] & 0xFF,)) + phase1._jp_nz(FAIL_PC)
        code += expect_byte(OPEN_COUNT, 0) + expect_byte(CLOSE_COUNT, 0) + expect_byte(symbols["vi_buffer_ready"], 0)
        code += phase1._jp(PASS_PC)
        run_sna(root, bytes(code), patch=patch(image, gateway, symbols["OBJ_BIN"], 0))

        code = bytearray(b"\xF3" + phase1._ld_sp(0xBFC0) + phase1._ld_hl(PATH) + phase1._call(symbols["vi_p902_load"]))
        code += phase1._jp_nc(FAIL_PC)
        code += b"\xFE" + bytes((symbols["E_IO"] & 0xFF,)) + phase1._jp_nz(FAIL_PC)
        code += expect_byte(OPEN_COUNT, 1) + expect_byte(CLOSE_COUNT, 1) + expect_byte(symbols["vi_source_open"], 0)
        code += phase1._jp(PASS_PC)
        run_sna(root, bytes(code), patch=patch(image, gateway, symbols["OBJ_TXT"], 1))

        assertions += [
            {"name": "fuse-editable-types-byte-exact", "passed": True},
            {"name": "fuse-source-handle-count-baseline-after-load", "passed": True},
            {"name": "fuse-bin-type-rejected-before-open", "passed": True},
            {"name": "fuse-read-error-closes-source", "passed": True},
        ]

    hashes = {
        "tools/vi.asm": sha256_file(source),
        "v1/build/p902-vi.mex1": sha256_file(mex_path),
        "v1/build/p902-vi.tap": sha256_file(tap_path),
        "v1/tools-host/test-driver/phase9_vi_load.py": sha256_file(root / "v1/tools-host/test-driver/phase9_vi_load.py"),
        "v1/tools-host/test-driver/run.py": sha256_file(root / "v1/tools-host/test-driver/run.py"),
        "v1/dist/certification/P9.01.test.json": sha256_file(root / "v1/dist/certification/P9.01.test.json"),
    }
    return [fixture_result, inspect_result, gateway_result], hashes, assertions
