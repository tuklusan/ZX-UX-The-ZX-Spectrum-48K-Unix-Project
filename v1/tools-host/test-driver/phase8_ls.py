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
from pathlib import Path
import struct
import sys

from driver_core import DriverError
from fuse_harness import FAIL_PC, PASS_PC, run_sna
import phase1
import phase3_open_descriptions

UTIL = 0xC000
GATE = 0xE000
ARG = 0xA000
OUT = 0xA200
MODE = 0xA3F0
STATUS = 0xA3F1


class P801Error(DriverError):
    pass


def require(value: bool, message: str) -> None:
    if not value:
        raise P801Error(message)


def u16(value: int) -> bytes:
    return struct.pack("<H", value)


def crc16(data: bytes) -> int:
    crc = 0xFFFF
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc


def mex1(image: bytes) -> bytes:
    header = bytearray(24)
    header[:4] = b"MEX1"
    header[4] = 1
    header[6:8] = u16(24)
    header[8:10] = u16(len(image))
    header[12:14] = u16(0)
    header[14:16] = u16(256)
    header[18:20] = u16(24 + len(image))
    header[20:22] = u16(crc16(image))
    header[22:24] = u16(crc16(bytes(header)))
    return bytes(header) + image


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def word(value: int) -> bytes:
    return bytes((value & 0xFF, (value >> 8) & 0xFF))


def arg1(args: list[bytes]) -> bytes:
    body = b"".join(item + b"\0" for item in args)
    total = 8 + len(body)
    return b"ARG1" + bytes((len(args), 0)) + word(total) + body


def expect_byte(address: int, value: int) -> bytes:
    return b"\x3A" + word(address) + bytes((0xFE, value & 0xFF)) + phase1._jp_nz(FAIL_PC)


def patch(util: bytes, gate: bytes, args: list[bytes], mode: int):
    block = arg1(args)

    def apply(ram: bytearray) -> None:
        ram[UTIL - 0x4000:UTIL - 0x4000 + len(util)] = util
        ram[GATE - 0x4000:GATE - 0x4000 + len(gate)] = gate
        ram[ARG - 0x4000:ARG - 0x4000 + len(block)] = block
        ram[OUT - 0x4000:OUT - 0x4000 + 128] = b"\xA5" * 128
        ram[MODE - 0x4000] = mode
        ram[STATUS - 0x4000:STATUS - 0x4000 + 2] = b"\0\0"

    return apply


def _source_contract(root: Path) -> list[dict[str, object]]:
    src = (root / "v1/src/utils/ls.asm").read_text(encoding="utf-8")
    plan = (root / "docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md").read_text(encoding="utf-8")
    return [
        {"name": "canonical-p801-present", "passed": "## P8.01 - Utility `ls`" in plan},
        {"name": "sys-list-drives-enumeration", "passed": "ld a,SYS_LIST" in src and "ls_list_out: defs 16,0" in src},
        {"name": "default-current-directory-dot", "passed": "ls_dot: db '.',0" in src and "ld hl,ls_dot" in src},
        {"name": "exact-type-table-complete", "passed": all(x in src for x in ("ls_type_txt:", "ls_type_bin:", "ls_type_obj:", "ls_type_asm:", "ls_type_c:", "ls_type_dat:", "ls_type_udg:", "ls_type_gfx:", "ls_type_fnt:", "ls_type_cfg:", "ls_type_sys:", "ls_type_dir:", "ls_type_dev:"))},
        {"name": "long-format-logical-and-state", "passed": "ld hl,(ls_list_out+12)" in src and "ld a,(ls_list_out+14)" in src},
        {"name": "packed-ram-physical-from-stat", "passed": "cp STATE_RAM" in src and "and OBJ_PACKED" in src and "ld a,SYS_STAT" in src and "ld hl,(ls_stat_out+4)" in src},
        {"name": "packed-savings-derived-logical-minus-storage", "passed": "ld hl,(ls_stat_out+2)" in src and "ld de,(ls_stat_out+4)" in src and "sbc hl,de" in src},
        {"name": "case-preserving-output", "passed": "ld hl,ls_list_out" in src and "casefold" not in src.lower()},
        {"name": "bounded-index-termination", "passed": "inc a\n    jr z,ls_ok" in src},
        {"name": "invalid-arity-fails-before-list", "passed": "cp 3\n    jr z,ls_three\n    jp ls_invalid" in src},
    ]


def dispatch(root: Path, action: str, step: str, *, sha256_file, run_command, require_project_tool):
    if step != "P8.01":
        raise DriverError(f"Phase-8 ls step is not registered: {step}")
    assertions = _source_contract(root)
    require(all(item["passed"] for item in assertions), "P8.01 static contract failure")

    asm = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)

    image_src = build / "p801-ls-image.asm"
    image_src.write_text(
        """    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/utils/ls.asm"
    ORG $0000
p801_image:
    EMIT_P801_LS_ROUTINES
p801_image_end:
    SAVEBIN "p801-ls-image.bin",p801_image,p801_image_end-p801_image
""",
        encoding="utf-8",
        newline="\n",
    )
    image_result = run_command([asm, "--nologo", "--lst=p801-ls-image.lst", "--sym=p801-ls-image.sym", "p801-ls-image.asm"], cwd=build, timeout_seconds=30)
    require(not image_result.timed_out and image_result.exit_code == 0, f"P8.01 ls image assembly failed: {image_result.stderr or image_result.stdout}")
    image = (build / "p801-ls-image.bin").read_bytes()
    require(64 <= len(image) < 4096, "P8.01 ls image size implausible")
    mex = build / "p801-ls.mex1"
    mex.write_bytes(mex1(image))
    inspector = require_project_tool(root, "v1/tools-host/inspect-mex/inspect.py")
    inspect_result = run_command([sys.executable, inspector, str(mex), "--base", "0x6000"], cwd=root, timeout_seconds=10)
    require(not inspect_result.timed_out and inspect_result.exit_code == 0, f"P8.01 MEX1 inspect failed: {inspect_result.stderr or inspect_result.stdout}")

    maketap = load_module(root / "v1/tools-host/maketap/maketap.py", "zxux_p801_maketap")
    tap_bytes = maketap.m48o_blocks(maketap.M48OObject("ls", maketap.M48O_BIN, maketap.DIR_BIN, mex.read_bytes()))
    tap = build / "p801-ls.tap"
    tap.write_bytes(tap_bytes)
    require(tap_bytes == maketap.m48o_blocks(maketap.M48OObject("ls", maketap.M48O_BIN, maketap.DIR_BIN, mex.read_bytes())), "P8.01 TAP rebuild mismatch")

    fixture_src = build / "p801-ls-fixture.asm"
    fixture_src.write_text(
        """    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/utils/ls.asm"
    ORG $C000
p801_fixture:
    EMIT_P801_LS_ROUTINES
p801_fixture_end:
    SAVEBIN "p801-ls-fixture.bin",p801_fixture,p801_fixture_end-p801_fixture
""",
        encoding="utf-8",
        newline="\n",
    )
    fixture_result = run_command([asm, "--nologo", "--lst=p801-ls-fixture.lst", "--sym=p801-ls-fixture.sym", "p801-ls-fixture.asm"], cwd=build, timeout_seconds=30)
    require(not fixture_result.timed_out and fixture_result.exit_code == 0, f"P8.01 fixture assembly failed: {fixture_result.stderr or fixture_result.stdout}")

    gate_src = build / "p801-gateway.asm"
    gate_src.write_text(
        """    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    ORG $E000
p801_gate:
    cp SYS_LIST
    jr z,p801_list
    cp SYS_STAT
    jr z,p801_stat
    cp SYS_WRITE
    jr z,p801_write
    cp SYS_EXIT
    jr z,p801_exit
    ld a,E_NOTSUP
    scf
    ret

p801_list:
    push hl
    inc hl
    inc hl
    ld a,(hl)
    pop hl
    or a
    jr nz,p801_list_end
    ld de,4
    add hl,de
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld a,($A3F0)
    or a
    jr nz,p801_list_packed
    ld hl,p801_normal
    ld bc,16
    ldir
    ld hl,1
    xor a
    ret
p801_list_packed:
    ld hl,p801_packed
    ld bc,16
    ldir
    ld hl,1
    xor a
    ret
p801_list_end:
    ld hl,0
    xor a
    ret

p801_stat:
    inc hl
    inc hl
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld hl,p801_statout
    ld bc,10
    ldir
    xor a
    ret

p801_write:
    ld a,d
    or a
    jr nz,p801_bad
    ld a,e
    cp 1
    jr nz,p801_bad
    ld de,(p801_out)
    ldir
    ld (p801_out),de
    xor a
    ret

p801_exit:
    ld a,l
    ld ($A3F1),a
    ld a,1
    ld ($A3F2),a
    xor a
    ret

p801_bad:
    ld a,E_INVAL
    scf
    ret

p801_normal:
    db 'A','l','p','h','a',0,0,0,0,0
    db OBJ_TXT,0
    dw 5
    db STATE_RAM,DIR_TMP
p801_packed:
    db 'z','i','p',0,0,0,0,0,0,0
    db OBJ_DAT,OBJ_PACKED
    dw 100
    db STATE_RAM,DIR_TMP
p801_statout:
    db OBJ_DAT,OBJ_PACKED
    dw 100
    dw 40
    db DIR_TMP,STATE_RAM
    dw 0
p801_out: dw $A200
p801_gate_end:
    SAVEBIN "p801-gateway.bin",p801_gate,p801_gate_end-p801_gate
""",
        encoding="utf-8",
        newline="\n",
    )
    gate_result = run_command([asm, "--nologo", "--lst=p801-gateway.lst", "--sym=p801-gateway.sym", "p801-gateway.asm"], cwd=build, timeout_seconds=30)
    require(not gate_result.timed_out and gate_result.exit_code == 0, f"P8.01 gateway assembly failed: {gate_result.stderr or gate_result.stdout}")

    if action == "test":
        symbols = phase3_open_descriptions._symbols(build / "p801-ls-fixture.sym", ("ls_entry",))
        util = (build / "p801-ls-fixture.bin").read_bytes()
        gate = (build / "p801-gateway.bin").read_bytes()
        cases = [
            ([b"ls"], 0, b"Alpha\tTXT\n", 0),
            ([b"ls", b"-l", b"/tmp"], 1, b"zip\tDAT\t100\tRAM\t40\t60\n", 0),
            ([b"ls", b"a", b"b", b"c"], 0, b"", 1),
        ]
        for args, mode, expected, status in cases:
            block = arg1(args)
            code = bytearray(b"\xF3" + phase1._ld_sp(0xBFC0) + phase1._ld_hl(ARG) + b"\x01" + word(len(block)) + phase1._call(symbols["ls_entry"]))
            for offset, value in enumerate(expected):
                code += expect_byte(OUT + offset, value)
            code += expect_byte(OUT + len(expected), 0xA5)
            code += expect_byte(STATUS, status) + expect_byte(STATUS + 1, 1)
            code += phase1._jp(PASS_PC)
            run_sna(root, bytes(code), patch=patch(util, gate, args, mode))
        assertions += [
            {"name": "fuse-default-list-exact-case-name-type", "passed": True},
            {"name": "fuse-long-packed-logical-state-physical-savings", "passed": True},
            {"name": "fuse-invalid-arity-no-output-exact-status", "passed": True},
        ]

    hashes = {
        "v1/src/utils/ls.asm": sha256_file(root / "v1/src/utils/ls.asm"),
        "v1/build/p801-ls.mex1": sha256_file(mex),
        "v1/build/p801-ls.tap": sha256_file(tap),
        "v1/tools-host/test-driver/phase8_ls.py": sha256_file(root / "v1/tools-host/test-driver/phase8_ls.py"),
        "v1/tools-host/test-driver/run.py": sha256_file(root / "v1/tools-host/test-driver/run.py"),
        "v1/dist/certification/phase-7.json": sha256_file(root / "v1/dist/certification/phase-7.json"),
    }
    return [image_result, inspect_result, fixture_result, gate_result], hashes, assertions
