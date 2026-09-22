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
COUNTERS = 0xA3F3


class P803Error(DriverError):
    pass


def require(value: bool, message: str) -> None:
    if not value:
        raise P803Error(message)


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
    return b"ARG1" + bytes((len(args), 0)) + word(8 + len(body)) + body


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
        ram[STATUS - 0x4000:STATUS - 0x4000 + 16] = b"\0" * 16

    return apply


def _source_contract(root: Path) -> list[dict[str, object]]:
    src = (root / "v1/src/utils/cp.asm").read_text(encoding="utf-8")
    plan = (root / "docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md").read_text(encoding="utf-8")
    return [
        {"name": "canonical-p803-present", "passed": "## P8.03 - Utility `cp`" in plan},
        {"name": "exact-same-path-noop", "passed": "cp_same_loop:" in src and ("jr z,cp_success" in src or "jp z,cp_success" in src)},
        {"name": "source-stat-preserves-type", "passed": "ld a,SYS_STAT" in src and "ld a,(cp_stat_out+0)" in src and "ld (cp_src_type),a" in src},
        {"name": "ram-source-only", "passed": "cp STATE_RAM" in src and "ld a,E_PERM" in src},
        {"name": "logical-read-stream", "passed": "ld a,SYS_READ" in src and "cp_buffer" in src},
        {"name": "exclusive-transaction-create", "passed": "O_WRITE|O_CREATE|O_EXCL" in src and "cp_temp_prefix: db '/tmp/.cp'" in src},
        {"name": "retry-only-eexist", "passed": "cp E_EXIST" in src and "cp 10" in src},
        {"name": "source-type-used-for-temp", "passed": "ld a,(cp_src_type)" in src and "ld b,a" in src},
        {"name": "full-ram-write-required", "passed": "ld a,SYS_WRITE" in src and "sbc hl,de" in src and "ld a,E_IO" in src},
        {"name": "close-before-rename", "passed": src.index("call cp_close_source") < src.index("ld a,SYS_RENAME") and src.index("call cp_close_temp") < src.index("ld a,SYS_RENAME")},
        {"name": "atomic-rename-commit", "passed": "ld a,SYS_RENAME" in src and "cp_ren1" in src},
        {"name": "failure-removes-owned-temp", "passed": "cp_tmp_created" in src and "ld a,SYS_REMOVE" in src},
        {"name": "case-preserving-paths", "passed": "casefold" not in src.lower()},
    ]


def dispatch(root: Path, action: str, step: str, *, sha256_file, run_command, require_project_tool):
    if step != "P8.03":
        raise DriverError(f"Phase-8 cp step is not registered: {step}")
    assertions = _source_contract(root)
    require(all(item["passed"] for item in assertions), "P8.03 static contract failure")

    asm = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)

    image_src = build / "p803-cp-image.asm"
    image_src.write_text(
        """    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/utils/cp.asm"
    ORG $0000
p803_image:
    EMIT_P803_CP_ROUTINES
p803_image_end:
    SAVEBIN "p803-cp-image.bin",p803_image,p803_image_end-p803_image
""",
        encoding="utf-8", newline="\n")
    image_result = run_command([asm, "--nologo", "--lst=p803-cp-image.lst", "--sym=p803-cp-image.sym", "p803-cp-image.asm"], cwd=build, timeout_seconds=30)
    require(not image_result.timed_out and image_result.exit_code == 0, f"P8.03 cp image assembly failed: {image_result.stderr or image_result.stdout}")
    image = (build / "p803-cp-image.bin").read_bytes()
    require(96 <= len(image) < 4096, "P8.03 cp image size implausible")
    mex = build / "p803-cp.mex1"
    mex.write_bytes(mex1(image))
    inspector = require_project_tool(root, "v1/tools-host/inspect-mex/inspect.py")
    inspect_result = run_command([sys.executable, inspector, str(mex), "--base", "0x6000"], cwd=root, timeout_seconds=10)
    require(not inspect_result.timed_out and inspect_result.exit_code == 0, f"P8.03 MEX1 inspect failed: {inspect_result.stderr or inspect_result.stdout}")

    maketap = load_module(root / "v1/tools-host/maketap/maketap.py", "zxux_p803_maketap")
    tap_bytes = maketap.m48o_blocks(maketap.M48OObject("cp", maketap.M48O_BIN, maketap.DIR_BIN, mex.read_bytes()))
    tap = build / "p803-cp.tap"
    tap.write_bytes(tap_bytes)
    require(tap_bytes == maketap.m48o_blocks(maketap.M48OObject("cp", maketap.M48O_BIN, maketap.DIR_BIN, mex.read_bytes())), "P8.03 TAP rebuild mismatch")

    fixture_src = build / "p803-cp-fixture.asm"
    fixture_src.write_text(
        """    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/utils/cp.asm"
    ORG $C000
p803_fixture:
    EMIT_P803_CP_ROUTINES
p803_fixture_end:
    SAVEBIN "p803-cp-fixture.bin",p803_fixture,p803_fixture_end-p803_fixture
""",
        encoding="utf-8", newline="\n")
    fixture_result = run_command([asm, "--nologo", "--lst=p803-cp-fixture.lst", "--sym=p803-cp-fixture.sym", "p803-cp-fixture.asm"], cwd=build, timeout_seconds=30)
    require(not fixture_result.timed_out and fixture_result.exit_code == 0, f"P8.03 fixture assembly failed: {fixture_result.stderr or fixture_result.stdout}")

    gate_src = build / "p803-gateway.asm"
    gate_src.write_text(
        """    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    ORG $E000
p803_gate:
    cp SYS_STAT
    jp z,p803_stat
    cp SYS_OPEN
    jp z,p803_open
    cp SYS_GETPID
    jp z,p803_getpid
    cp SYS_READ
    jp z,p803_read
    cp SYS_WRITE
    jp z,p803_write
    cp SYS_CLOSE
    jp z,p803_close
    cp SYS_RENAME
    jp z,p803_rename
    cp SYS_REMOVE
    jp z,p803_remove
    cp SYS_EXIT
    jp z,p803_exit
    ld a,E_NOTSUP
    scf
    ret

p803_stat:
    ld a,($A3F3)
    inc a
    ld ($A3F3),a
    inc hl
    inc hl
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld hl,p803_statout
    ld bc,10
    ldir
    xor a
    ret

p803_open:
    ld a,($A3F4)
    inc a
    ld ($A3F4),a
    cp 1
    jr z,p803_open_src
    ld a,($A3F0)
    cp 3
    jr nz,p803_open_tmp_ok
    ld a,($A3F4)
    cp 2
    jr nz,p803_open_tmp_ok
    ld a,E_EXIST
    scf
    ret
p803_open_tmp_ok:
    ld hl,4
    xor a
    ret
p803_open_src:
    ld hl,3
    xor a
    ret

p803_getpid:
    ld a,($A3FA)
    inc a
    ld ($A3FA),a
    ld hl,2
    xor a
    ret

p803_read:
    ld a,($A3F5)
    inc a
    ld ($A3F5),a
    cp 1
    jr nz,p803_eof
    ld (p803_dest),hl
    ld hl,p803_payload
    ld de,(p803_dest)
    ld bc,3
    ldir
    ld hl,3
    xor a
    ret
p803_eof:
    ld hl,0
    xor a
    ret

p803_write:
    ld a,($A3F6)
    inc a
    ld ($A3F6),a
    ld a,($A3F0)
    cp 2
    jr z,p803_write_fail
    push bc
    ld de,(p803_out)
    ldir
    ld (p803_out),de
    pop hl
    xor a
    ret
p803_write_fail:
    ld a,E_IO
    scf
    ret

p803_close:
    ld a,($A3F7)
    inc a
    ld ($A3F7),a
    xor a
    ret

p803_rename:
    ld a,($A3F8)
    inc a
    ld ($A3F8),a
    xor a
    ret

p803_remove:
    ld a,($A3F9)
    inc a
    ld ($A3F9),a
    xor a
    ret

p803_exit:
    ld a,l
    ld ($A3F1),a
    ld a,1
    ld ($A3F2),a
    xor a
    ret

p803_statout:
    db OBJ_DAT,OBJ_PACKED
    dw 3
    dw 2
    db DIR_TMP,STATE_RAM
    dw 0
p803_payload: db 'a','b','c'
p803_dest: dw 0
p803_out: dw $A200
p803_gate_end:
    SAVEBIN "p803-gateway.bin",p803_gate,p803_gate_end-p803_gate
""",
        encoding="utf-8", newline="\n")
    gate_result = run_command([asm, "--nologo", "--lst=p803-gateway.lst", "--sym=p803-gateway.sym", "p803-gateway.asm"], cwd=build, timeout_seconds=30)
    require(not gate_result.timed_out and gate_result.exit_code == 0, f"P8.03 gateway assembly failed: {gate_result.stderr or gate_result.stdout}")

    if action == "test":
        symbols = phase3_open_descriptions._symbols(build / "p803-cp-fixture.sym", ("cp_entry",))
        util = (build / "p803-cp-fixture.bin").read_bytes()
        gate = (build / "p803-gateway.bin").read_bytes()
        cases = [
            ([b"cp", b"src", b"dst"], 0, b"abc", 0, (1, 2, 2, 1, 2, 1, 0, 1)),
            ([b"cp", b"same", b"same"], 1, b"", 0, (0, 0, 0, 0, 0, 0, 0, 0)),
            ([b"cp", b"src", b"dst"], 2, b"", 5, (1, 2, 1, 1, 2, 0, 1, 1)),
            ([b"cp", b"src", b"dst"], 3, b"abc", 0, (1, 3, 2, 1, 2, 1, 0, 1)),
            ([b"cp", b"only"], 0, b"", 1, (0, 0, 0, 0, 0, 0, 0, 0)),
        ]
        for args, mode, expected, status, counters in cases:
            block = arg1(args)
            code = bytearray(b"\xF3" + phase1._ld_sp(0xBFC0) + phase1._ld_hl(ARG) + b"\x01" + word(len(block)) + phase1._call(symbols["cp_entry"]))
            for offset, value in enumerate(expected):
                code += expect_byte(OUT + offset, value)
            code += expect_byte(OUT + len(expected), 0xA5)
            code += expect_byte(STATUS, status) + expect_byte(STATUS + 1, 1)
            for offset, value in enumerate(counters):
                code += expect_byte(COUNTERS + offset, value)
            code += phase1._jp(PASS_PC)
            run_sna(root, bytes(code), patch=patch(util, gate, args, mode))
        assertions += [
            {"name": "fuse-packed-source-logical-copy-type-preserving-rename", "passed": True},
            {"name": "fuse-exact-same-path-noop", "passed": True},
            {"name": "fuse-write-error-cleans-owned-temp", "passed": True},
            {"name": "fuse-exclusive-temp-eexist-retry", "passed": True},
            {"name": "fuse-invalid-arity-no-side-effects", "passed": True},
        ]

    hashes = {
        "v1/src/utils/cp.asm": sha256_file(root / "v1/src/utils/cp.asm"),
        "v1/build/p803-cp.mex1": sha256_file(mex),
        "v1/build/p803-cp.tap": sha256_file(tap),
        "v1/tools-host/test-driver/phase8_cp.py": sha256_file(root / "v1/tools-host/test-driver/phase8_cp.py"),
        "v1/tools-host/test-driver/run.py": sha256_file(root / "v1/tools-host/test-driver/run.py"),
        "v1/dist/certification/P8.02.test.json": sha256_file(root / "v1/dist/certification/P8.02.test.json"),
    }
    return [image_result, inspect_result, fixture_result, gate_result], hashes, assertions
