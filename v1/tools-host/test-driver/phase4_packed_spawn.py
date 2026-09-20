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

from pathlib import Path
import struct
from typing import Any, Callable

from driver_core import DriverError
from fuse_harness import FAIL_PC, PASS_PC, run_sna
import phase1
import phase3_open_descriptions

MODULE_BASE = 0xC000
STACK_TOP = 0xBFC0


class P427Error(DriverError):
    pass


def require(ok: bool, msg: str) -> None:
    if not ok:
        raise P427Error(msg)


def _word(value: int) -> bytes:
    return bytes((value & 0xFF, (value >> 8) & 0xFF))


def _jp_nc(address: int) -> bytes:
    return b"\xD2" + _word(address)


def _check_byte(address: int, value: int) -> bytes:
    return b"\x3A" + _word(address) + bytes((0xFE, value & 0xFF)) + phase1._jp_nz(FAIL_PC)


def _check_word(address: int, value: int) -> bytes:
    return b"\x2A" + _word(address) + phase1._ld_de(value) + b"\xB7\xED\x52" + phase1._jp_nz(FAIL_PC)


def _check_bytes(address: int, data: bytes) -> bytes:
    out = bytearray()
    for i, value in enumerate(data):
        out += _check_byte(address + i, value)
    return bytes(out)


def _crc16(data: bytes) -> int:
    crc = 0xFFFF
    for value in data:
        crc ^= value << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc


def _mex_image() -> bytes:
    return b"MEX" + b"A" * 36 + b"\xC9"


def _header(*, corrupt_body_crc: bool = False) -> bytes:
    image = _mex_image()
    h = bytearray(24)
    h[:4] = b"MEX1"
    h[4] = 1
    h[5] = 0
    struct.pack_into("<H", h, 6, 24)
    struct.pack_into("<H", h, 8, len(image))
    struct.pack_into("<H", h, 10, 2)
    struct.pack_into("<H", h, 12, len(image) - 1)
    struct.pack_into("<H", h, 14, 64)
    struct.pack_into("<H", h, 16, 0)
    struct.pack_into("<H", h, 18, 24 + len(image))
    body_crc = _crc16(image)
    if corrupt_body_crc:
        body_crc ^= 0x0001
    struct.pack_into("<H", h, 20, body_crc)
    struct.pack_into("<H", h, 22, 0)
    struct.pack_into("<H", h, 22, _crc16(bytes(h)))
    return bytes(h)


def _packed_stream(*, corrupt_body_crc: bool = False) -> tuple[bytes, bytes]:
    header = _header(corrupt_body_crc=corrupt_body_crc)
    image = _mex_image()
    logical = header + image
    # Header is one 24-byte literal. The first post-header token is a distance-24
    # BACKREF producing "MEX" exclusively from pre-header history.
    encoded = bytes((23,)) + header + bytes((0x80, 23, 0x61, ord("A"), 0x00, 0xC9))
    require(len(encoded) < len(logical), "P4.27 fixture must be genuinely PACKED")
    return encoded, logical


def _record(s: dict[str, int], physical: int, logical: int, ptr: int) -> bytes:
    r = bytearray(20)
    r[:4] = b"prog"
    r[10] = s["DIR_BIN"]
    r[11] = s["OBJ_BIN"]
    r[12] = s["OBJ_PACKED"]
    r[13] = s["STATE_RAM"]
    r[14:16] = _word(logical)
    r[16:18] = _word(physical)
    r[18:20] = _word(ptr)
    return bytes(r)


def _source_contract(root: Path) -> list[dict[str, object]]:
    process = (root / "v1/src/kernel/process.asm").read_text(encoding="utf-8")
    zx = (root / "v1/src/kernel/zxpack.asm").read_text(encoding="utf-8")
    require("MACRO EMIT_P427_PACKED_SPAWN_ROUTINES" in process, "P4.27 process macro missing")
    require("MACRO EMIT_P427_PACKED_SPAWN_STREAM_ROUTINES" in zx, "P4.27 stream macro missing")
    pm = process.split("MACRO EMIT_P427_PACKED_SPAWN_ROUTINES", 1)[1].split("ENDM", 1)[0]
    zm = zx.split("MACRO EMIT_P427_PACKED_SPAWN_STREAM_ROUTINES", 1)[1].split("ENDM", 1)[0]
    return [
        {"name": "single-continuous-state-bind", "passed": pm.count("call zx48_p418_state_bind") == 1},
        {"name": "no-header-boundary-reset", "passed": "zx48_p418_reset" not in pm},
        {"name": "exact-272-byte-state", "passed": pm.count("P417_STATE_SIZE") >= 3 and "ALLOC_NO_COMPACT" in pm},
        {"name": "header-only-scratch", "passed": "p427_header: defs MEX_HEADER_SIZE,0" in pm},
        {"name": "direct-final-image-write", "passed": "ld (p427_write_ptr),hl" in pm and "ld (hl),a" in pm},
        {"name": "no-full-logical-materialization", "passed": all(x not in pm for x in ("zx48_p423_unpack_record", "zx48_p419_materialize_private", "P416_SINK_FINAL_MEMORY"))},
        {"name": "same-stream-relocation-parse", "passed": "zx48_p427_reloc_loop:" in pm and pm.count("call zx48_p427_stream_step") >= 3},
        {"name": "exact-stream-eof-validation", "passed": "call zx48_p418_seek" in pm},
        {"name": "header-and-body-crc-validation", "passed": "MEX_HDR_HEADER_CRC" in pm and "MEX_HDR_BODY_CRC" in pm and "zx48_p427_crc16_update" in pm},
        {"name": "failure-rolls-back-final-image", "passed": "zx48_p427_fail_image:" in pm and "call zx48_free" in pm},
        {"name": "stream-adapter-is-step-only", "passed": "call zx48_p418_step" in zm and "zx48_p418_state_bind" not in zm and "zx48_p418_reset" not in zm},
    ]


def _assemble(root: Path, run_command: Callable[..., Any], require_project_tool: Callable[[Path, str | Path], Path]):
    asm = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    fixture = build / "p427-packed-spawn.asm"
    fixture.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../include/mex1.inc"
PANIC_SCHEDULER EQU $03
    ORG $C000
    INCLUDE "../src/kernel/memory.asm"
    INCLUDE "../src/kernel/objects.asm"
    INCLUDE "../src/kernel/zxpack.asm"
    INCLUDE "../src/kernel/process.asm"
    EMIT_MEMORY_ROUTINES
    EMIT_P418_PACKED_SEEK_ROUTINES
    EMIT_P427_PACKED_SPAWN_STREAM_ROUTINES
    EMIT_P427_PACKED_SPAWN_ROUTINES
zx48_process_count:
    xor a
    ret
zx48_panic:
    scf
    ret
p427_test_object:
    defs 20,0
    SAVEBIN "p427-packed-spawn.bin",$C000,$-$C000
""", encoding="utf-8", newline="\n")
    result = run_command([asm, "--nologo", "--lst=p427-packed-spawn.lst", "--sym=p427-packed-spawn.sym", "p427-packed-spawn.asm"], cwd=build, timeout_seconds=30.0)
    require(not result.timed_out and result.exit_code == 0, f"P4.27 fixture assembly failed: {result.stderr or result.stdout}")
    binary = build / "p427-packed-spawn.bin"
    listing = build / "p427-packed-spawn.lst"
    require(binary.is_file() and 0 < binary.stat().st_size < 16384, "P4.27 fixture binary missing/oversize")
    return result, binary, listing


def _runtime(root: Path, s: dict[str, int], module: bytes) -> None:
    src = s["ARENA_START"]
    record_addr = s["p427_test_object"]
    free = s["memory_free_extents"]
    live = s["memory_live_allocations"]
    arena = s["ARENA_SIZE"]

    def patch(encoded: bytes, record: bytes):
        rounded = (len(encoded) + 1) & ~1
        def apply(ram: bytearray) -> None:
            ram[MODULE_BASE-0x4000:MODULE_BASE-0x4000+len(module)] = module
            ram[src-0x4000:src-0x4000+len(encoded)] = encoded
            if rounded > len(encoded):
                ram[src-0x4000+len(encoded)] = 0xEE
            ram[record_addr-0x4000:record_addr-0x4000+20] = record
            ram[free-0x4000:free-0x4000+64] = bytes(64)
            ram[free-0x4000:free-0x4000+4] = _word(src + rounded) + _word(arena - rounded)
            ram[live-0x4000:live-0x4000+2] = _word(1)
        return apply

    encoded, logical = _packed_stream()
    record = _record(s, len(encoded), len(logical), src)
    rounded_src = (len(encoded) + 1) & ~1
    state_base = src + rounded_src
    image_base = state_base + s["P417_STATE_SIZE"]
    image = _mex_image()
    image_rounded = (len(image) + 2 + 1) & ~1

    code = bytearray(b"\xF3" + phase1._ld_sp(STACK_TOP))
    code += b"\xDD\x21" + _word(record_addr) + phase1._call(s["zx48_p427_prepare_packed_bin"])
    code += phase1._jp_c(FAIL_PC)
    code += phase1._ld_de(image_base) + b"\xB7\xED\x52" + phase1._jp_nz(FAIL_PC)
    code += _check_word(s["p427_image_base"], image_base)
    code += _check_word(s["p427_state_ptr"], state_base)
    code += _check_word(s["p427_peak_bytes"], image_rounded + s["P417_STATE_SIZE"])
    code += _check_word(live, 2)
    code += _check_bytes(image_base, image + b"\x00\x00")
    code += _check_bytes(record_addr, record)
    code += _check_bytes(src, encoded)
    code += phase1._jp(PASS_PC)
    run_sna(root, bytes(code), patch=patch(encoded, record))

    bad_encoded, bad_logical = _packed_stream(corrupt_body_crc=True)
    bad_record = _record(s, len(bad_encoded), len(bad_logical), src)
    code = bytearray(b"\xF3" + phase1._ld_sp(STACK_TOP))
    code += b"\xDD\x21" + _word(record_addr) + phase1._call(s["zx48_p427_prepare_packed_bin"])
    code += _jp_nc(FAIL_PC)
    code += bytes((0xFE, s["E_FORMAT"])) + phase1._jp_nz(FAIL_PC)
    code += _check_word(live, 1)
    code += _check_bytes(record_addr, bad_record)
    code += _check_bytes(src, bad_encoded)
    code += phase1._jp(PASS_PC)
    run_sna(root, bytes(code), patch=patch(bad_encoded, bad_record))


def dispatch(root: Path, action: str, step: str, *, sha256_file, run_command, require_project_tool):
    if step != "P4.27":
        raise DriverError(f"Phase-4 packed spawn step is not registered: {step}")
    assertions = _source_contract(root)
    failed = [x["name"] for x in assertions if x.get("passed") is not True]
    require(not failed, f"static P4.27 contract failures: {failed}")
    kr, kernel, _ = phase1._assemble_kernel(root, run_command, require_project_tool)
    fr, binary, listing = _assemble(root, run_command, require_project_tool)
    names = (
        "zx48_p427_prepare_packed_bin", "p427_test_object", "p427_image_base", "p427_state_ptr",
        "p427_peak_bytes", "memory_free_extents", "memory_live_allocations", "ARENA_START", "ARENA_SIZE",
        "P417_STATE_SIZE", "DIR_BIN", "OBJ_BIN", "OBJ_PACKED", "STATE_RAM", "E_FORMAT",
    )
    symbols = phase3_open_descriptions._symbols(listing.with_suffix(".sym"), names)
    if action == "test":
        _runtime(root, symbols, binary.read_bytes())
        assertions += [
            {"name": "packed-mex-direct-final-allocation-runtime", "passed": True},
            {"name": "preheader-history-backref-crosses-header-boundary-runtime", "passed": True},
            {"name": "one-final-image-plus-272-state-accounting-runtime", "passed": True},
            {"name": "corrupt-packed-executable-rolls-back-runtime", "passed": True},
            {"name": "packed-object-remains-byte-identical-runtime", "passed": True},
        ]
    hashes = {
        "v1/build/kernel.bin": sha256_file(kernel),
        "v1/build/p427-packed-spawn.bin": sha256_file(binary),
        "v1/src/kernel/process.asm": sha256_file(root / "v1/src/kernel/process.asm"),
        "v1/src/kernel/zxpack.asm": sha256_file(root / "v1/src/kernel/zxpack.asm"),
        "v1/tools-host/test-driver/phase4_packed_spawn.py": sha256_file(root / "v1/tools-host/test-driver/phase4_packed_spawn.py"),
        "v1/tools-host/test-driver/run.py": sha256_file(root / "v1/tools-host/test-driver/run.py"),
        "v1/dist/certification/P4.26.test.json": sha256_file(root / "v1/dist/certification/P4.26.test.json"),
    }
    return [kr, fr], hashes, assertions
