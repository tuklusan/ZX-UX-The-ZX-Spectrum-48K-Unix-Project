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


class P802Error(DriverError):
    pass


def require(value: bool, message: str) -> None:
    if not value:
        raise P802Error(message)


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
        ram[STATUS - 0x4000:STATUS - 0x4000 + 8] = b"\0" * 8

    return apply


def _source_contract(root: Path) -> list[dict[str, object]]:
    src = (root / "v1/src/utils/cat.asm").read_text(encoding="utf-8")
    plan = (root / "docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md").read_text(encoding="utf-8")
    return [
        {"name": "canonical-p802-present", "passed": "## P8.02 - Utility `cat`" in plan},
        {"name": "named-object-open-read-only", "passed": "ld c,O_READ" in src and "ld a,SYS_OPEN" in src},
        {"name": "stdin-handle-zero", "passed": "cat_stdin:" in src and "ld (cat_handle),a" in src},
        {"name": "stream-read-loop", "passed": "ld a,SYS_READ" in src and "jr z,cat_success" in src},
        {"name": "stdout-handle-one", "passed": "ld de,1" in src and "ld a,SYS_WRITE" in src},
        {"name": "partial-write-loop", "passed": "cat_write_loop:" in src and "ld (cat_remaining),hl" in src and "sbc hl,de" in src},
        {"name": "zero-write-fails", "passed": "cat_zero_write:" in src and "ld a,E_IO" in src},
        {"name": "named-object-close", "passed": "ld a,SYS_CLOSE" in src and "cat_opened" in src},
        {"name": "invalid-arity-fails", "passed": "cp 1" in src and "cp 2" in src and "ld a,E_INVAL" in src},
        {"name": "case-preserving-path", "passed": "casefold" not in src.lower()},
    ]


def dispatch(root: Path, action: str, step: str, *, sha256_file, run_command, require_project_tool):
    if step != "P8.02":
        raise DriverError(f"Phase-8 cat step is not registered: {step}")
    assertions = _source_contract(root)
    require(all(item["passed"] for item in assertions), "P8.02 static contract failure")

    asm = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)

    image_src = build / "p802-cat-image.asm"
    image_src.write_text(
        """    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/utils/cat.asm"
    ORG $0000
p802_image:
    EMIT_P802_CAT_ROUTINES
p802_image_end:
    SAVEBIN "p802-cat-image.bin",p802_image,p802_image_end-p802_image
""",
        encoding="utf-8",
        newline="\n",
    )
    image_result = run_command([asm, "--nologo", "--lst=p802-cat-image.lst", "--sym=p802-cat-image.sym", "p802-cat-image.asm"], cwd=build, timeout_seconds=30)
    require(not image_result.timed_out and image_result.exit_code == 0, f"P8.02 cat image assembly failed: {image_result.stderr or image_result.stdout}")
    image = (build / "p802-cat-image.bin").read_bytes()
    require(48 <= len(image) < 2048, "P8.02 cat image size implausible")
    mex = build / "p802-cat.mex1"
    mex.write_bytes(mex1(image))
    inspector = require_project_tool(root, "v1/tools-host/inspect-mex/inspect.py")
    inspect_result = run_command([sys.executable, inspector, str(mex), "--base", "0x6000"], cwd=root, timeout_seconds=10)
    require(not inspect_result.timed_out and inspect_result.exit_code == 0, f"P8.02 MEX1 inspect failed: {inspect_result.stderr or inspect_result.stdout}")

    maketap = load_module(root / "v1/tools-host/maketap/maketap.py", "zxux_p802_maketap")
    tap_bytes = maketap.m48o_blocks(maketap.M48OObject("cat", maketap.M48O_BIN, maketap.DIR_BIN, mex.read_bytes()))
    tap = build / "p802-cat.tap"
    tap.write_bytes(tap_bytes)
    require(tap_bytes == maketap.m48o_blocks(maketap.M48OObject("cat", maketap.M48O_BIN, maketap.DIR_BIN, mex.read_bytes())), "P8.02 TAP rebuild mismatch")

    fixture_src = build / "p802-cat-fixture.asm"
    fixture_src.write_text(
        """    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/utils/cat.asm"
    ORG $C000
p802_fixture:
    EMIT_P802_CAT_ROUTINES
p802_fixture_end:
    SAVEBIN "p802-cat-fixture.bin",p802_fixture,p802_fixture_end-p802_fixture
""",
        encoding="utf-8",
        newline="\n",
    )
    fixture_result = run_command([asm, "--nologo", "--lst=p802-cat-fixture.lst", "--sym=p802-cat-fixture.sym", "p802-cat-fixture.asm"], cwd=build, timeout_seconds=30)
    require(not fixture_result.timed_out and fixture_result.exit_code == 0, f"P8.02 fixture assembly failed: {fixture_result.stderr or fixture_result.stdout}")

    gate_src = build / "p802-gateway.asm"
    gate_src.write_text(
        """    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    ORG $E000
p802_gate:
    cp SYS_OPEN
    jr z,p802_open
    cp SYS_READ
    jr z,p802_read
    cp SYS_WRITE
    jr z,p802_write
    cp SYS_CLOSE
    jp z,p802_close
    cp SYS_EXIT
    jp z,p802_exit
    ld a,E_NOTSUP
    scf
    ret

p802_open:
    ld a,($A3F3)
    inc a
    ld ($A3F3),a
    ld a,($A3F0)
    cp 2
    jr z,p802_open_fail
    ld hl,3
    xor a
    ret
p802_open_fail:
    ld a,E_NOENT
    scf
    ret

p802_read:
    ld (p802_dest),hl
    ld a,($A3F4)
    inc a
    ld ($A3F4),a
    ld a,(p802_read_done)
    or a
    jr nz,p802_eof
    ld a,($A3F0)
    cp 1
    jr z,p802_read_stdin
    cp 3
    jr z,p802_read_short
    ld a,e
    cp 3
    jr nz,p802_bad
    ld hl,p802_named
    ld bc,6
    jr p802_copy_read
p802_read_stdin:
    ld a,e
    or a
    jr nz,p802_bad
    ld hl,p802_pipe
    ld bc,9
    jr p802_copy_read
p802_read_short:
    ld a,e
    or a
    jr nz,p802_bad
    ld hl,p802_short
    ld bc,4
p802_copy_read:
    push bc
    ld de,(p802_dest)
    ldir
    pop hl
    ld a,1
    ld (p802_read_done),a
    xor a
    ret
p802_eof:
    ld hl,0
    xor a
    ret

p802_write:
    ld a,($A3F5)
    inc a
    ld ($A3F5),a
    ld a,d
    or a
    jr nz,p802_bad
    ld a,e
    cp 1
    jr nz,p802_bad
    ld a,($A3F0)
    cp 3
    jr nz,p802_write_full
    ld a,b
    or a
    jr nz,p802_write_two
    ld a,c
    cp 3
    jr c,p802_write_full
p802_write_two:
    ld bc,2
p802_write_full:
    push bc
    ld de,(p802_out)
    ldir
    ld (p802_out),de
    pop hl
    xor a
    ret

p802_close:
    ld a,($A3F6)
    inc a
    ld ($A3F6),a
    xor a
    ret

p802_exit:
    ld a,l
    ld ($A3F1),a
    ld a,1
    ld ($A3F2),a
    xor a
    ret

p802_bad:
    ld a,E_INVAL
    scf
    ret

p802_named: db 'M','i','X','e','D',10
p802_pipe: db 'p','i','p','e','-','d','a','t','a'
p802_short: db 'a','b','c','d'
p802_read_done: db 0
p802_dest: dw 0
p802_out: dw $A200
p802_gate_end:
    SAVEBIN "p802-gateway.bin",p802_gate,p802_gate_end-p802_gate
""",
        encoding="utf-8",
        newline="\n",
    )
    gate_result = run_command([asm, "--nologo", "--lst=p802-gateway.lst", "--sym=p802-gateway.sym", "p802-gateway.asm"], cwd=build, timeout_seconds=30)
    require(not gate_result.timed_out and gate_result.exit_code == 0, f"P8.02 gateway assembly failed: {gate_result.stderr or gate_result.stdout}")

    if action == "test":
        symbols = phase3_open_descriptions._symbols(build / "p802-cat-fixture.sym", ("cat_entry",))
        util = (build / "p802-cat-fixture.bin").read_bytes()
        gate = (build / "p802-gateway.bin").read_bytes()
        cases = [
            ([b"cat", b"MiXeD"], 0, b"MiXeD\n", 0, (1, 2, 1, 1)),
            ([b"cat"], 1, b"pipe-data", 0, (0, 2, 1, 0)),
            ([b"cat", b"missing"], 2, b"", 2, (1, 0, 0, 0)),
            ([b"cat"], 3, b"abcd", 0, (0, 2, 2, 0)),
            ([b"cat", b"a", b"b"], 0, b"", 1, (0, 0, 0, 0)),
        ]
        for args, mode, expected, status, counters in cases:
            block = arg1(args)
            code = bytearray(b"\xF3" + phase1._ld_sp(0xBFC0) + phase1._ld_hl(ARG) + b"\x01" + word(len(block)) + phase1._call(symbols["cat_entry"]))
            for offset, value in enumerate(expected):
                code += expect_byte(OUT + offset, value)
            code += expect_byte(OUT + len(expected), 0xA5)
            code += expect_byte(STATUS, status) + expect_byte(STATUS + 1, 1)
            for offset, value in enumerate(counters):
                code += expect_byte(COUNTERS + offset, value)
            code += phase1._jp(PASS_PC)
            run_sna(root, bytes(code), patch=patch(util, gate, args, mode))
        assertions += [
            {"name": "fuse-named-object-exact-case-stream", "passed": True},
            {"name": "fuse-stdin-pipeline-stream", "passed": True},
            {"name": "fuse-open-failure-no-output", "passed": True},
            {"name": "fuse-short-pipe-writes-retried", "passed": True},
            {"name": "fuse-invalid-arity-no-side-effects", "passed": True},
        ]

    hashes = {
        "v1/src/utils/cat.asm": sha256_file(root / "v1/src/utils/cat.asm"),
        "v1/build/p802-cat.mex1": sha256_file(mex),
        "v1/build/p802-cat.tap": sha256_file(tap),
        "v1/tools-host/test-driver/phase8_cat.py": sha256_file(root / "v1/tools-host/test-driver/phase8_cat.py"),
        "v1/tools-host/test-driver/run.py": sha256_file(root / "v1/tools-host/test-driver/run.py"),
        "v1/dist/certification/P8.01.test.json": sha256_file(root / "v1/dist/certification/P8.01.test.json"),
    }
    return [image_result, inspect_result, fixture_result, gate_result], hashes, assertions
