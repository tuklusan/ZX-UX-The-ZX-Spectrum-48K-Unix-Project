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
from typing import Any, Callable

from driver_core import DriverError
from fuse_harness import FAIL_PC, PASS_PC, run_sna
import phase1
import phase3_open_descriptions

MODULE_BASE = 0xC000
SOURCE_BASE = 0xA000


class Phase4RawWriteError(DriverError):
    """Raised when the P4.08 atomic RAW write contract regresses."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Phase4RawWriteError(message)


def _word(value: int) -> bytes:
    return bytes((value & 0xFF, (value >> 8) & 0xFF))


def _jp_nc(address: int) -> bytes:
    return b"\xD2" + _word(address)


def _ld_a_mem(address: int) -> bytes:
    return b"\x3A" + _word(address)


def _assemble(root: Path, run_command: Callable[..., Any], require_project_tool: Callable[[Path, str | Path], Path]):
    assembler = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    fixture = build / "p408-raw-write.asm"
    fixture.write_text(
        """    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    ORG $C000
    INCLUDE "../src/kernel/memory.asm"
    INCLUDE "../src/kernel/objects.asm"
    EMIT_MEMORY_ROUTINES
    EMIT_P408_RAW_WRITE_ROUTINES
p408_record: defs OBJ_RECORD_SIZE,0
    SAVEBIN "p408-raw-write.bin",$C000,$-$C000
""",
        encoding="utf-8", newline="\n",
    )
    result = run_command(
        [assembler, "--nologo", "--lst=p408-raw-write.lst", "--sym=p408-raw-write.sym", "p408-raw-write.asm"],
        cwd=build,
        timeout_seconds=30.0,
    )
    require(not result.timed_out and result.exit_code == 0, f"P4.08 fixture assembly failed: {result.stderr or result.stdout}")
    binary = build / "p408-raw-write.bin"
    listing = build / "p408-raw-write.lst"
    require(binary.is_file() and 0 < binary.stat().st_size < 8192, "P4.08 fixture binary missing/oversize")
    return result, binary, listing


def _source_contract(root: Path) -> list[dict[str, object]]:
    objects = (root / "v1/src/kernel/objects.asm").read_text(encoding="utf-8")
    macro = objects.split("MACRO EMIT_P408_RAW_WRITE_ROUTINES", 1)[1].split("ENDM", 1)[0]
    return [
        {"name": "zero-count-is-immediate-full-success", "passed": "ld hl,0" in macro and "p408_count" in macro},
        {"name": "sparse-hole-offset-rejected-before-copy", "passed": "p408_offset" in macro and "zx48_p408_invalid" in macro},
        {"name": "offset-plus-count-is-widened", "passed": "add hl,bc" in macro and "jp c,zx48_p408_nospc" in macro and "cp ARENA_SIZE/256" in macro},
        {"name": "growth-limit-is-exact-32768", "passed": "cp ARENA_SIZE/256" in macro and "zx48_p408_nospc" in macro},
        {"name": "private-replacement-before-metadata-commit", "passed": macro.index("call zx48_alloc") < macro.index("(ix+OBJ_ALLOCATION_PTR),l")},
        {"name": "old-bytes-and-full-write-copied-before-commit", "passed": macro.count("ldir") >= 3 and macro.rindex("ldir") < macro.index("(ix+OBJ_ALLOCATION_PTR),l")},
        {"name": "raw-logical-storage-lengths-commit-together", "passed": "OBJ_LOGICAL_LENGTH" in macro and "OBJ_STORAGE_LENGTH" in macro},
        {"name": "old-allocation-freed-only-after-swap", "passed": macro.index("(ix+OBJ_ALLOCATION_PTR),l") < macro.index("call zx48_free")},
        {"name": "append-helper-uses-identical-transaction", "passed": "zx48_p408_raw_write_at_eof:" in macro and "jp zx48_p408_raw_write" in macro},
        {"name": "packed-write-not-handled-by-raw-path", "passed": "and OBJ_PACKED" in macro and "E_NOTSUP" in macro},
    ]


def _record(s: dict[str, int], logical: int, ptr: int, flags: int = 0) -> bytes:
    raw = bytearray(20)
    raw[:4] = b"file"
    raw[10] = 6
    raw[11] = s["OBJ_DAT"]
    raw[12] = flags & 0xFF
    raw[14:16] = _word(logical)
    raw[16:18] = _word(logical)
    raw[18:20] = _word(ptr)
    return bytes(raw)


def _target(root: Path, s: dict[str, int], module: bytes) -> None:
    record = s["p408_record"]
    free = s["memory_free_extents"]
    live = s["memory_live_allocations"]
    old_ptr = s["ARENA_START"]

    def patch_factory(old: bytes, source: bytes, *, no_free: bool = False):
        def patch(ram: bytearray) -> None:
            moff = MODULE_BASE - 0x4000
            ram[moff:moff + len(module)] = module
            roff = record - 0x4000
            ram[roff:roff + 20] = old
            soff = SOURCE_BASE - 0x4000
            ram[soff:soff + len(source)] = source
            old_len = old[14] | (old[15] << 8)
            old_alloc = old[18] | (old[19] << 8)
            if old_len:
                ram[old_alloc - 0x4000:old_alloc - 0x4000 + old_len] = b"ABCD"[:old_len]
            foff = free - 0x4000
            ram[foff:foff + 64] = bytes(64)
            if not no_free:
                rounded = old_len + (old_len & 1)
                start = s["ARENA_START"] + rounded
                length = s["ARENA_SIZE"] - rounded
                ram[foff:foff + 4] = _word(start) + _word(length)
            loff = live - 0x4000
            ram[loff:loff + 2] = _word(1 if old_len else 0)
        return patch

    def execute(label: str, code: bytes, old: bytes, source: bytes, *, no_free: bool = False) -> None:
        body = bytes((0xF3,)) + phase1._ld_sp(0xBFC0) + code + phase1._jp(PASS_PC)
        try:
            run_sna(root, body, patch=patch_factory(old, source, no_free=no_free))
        except DriverError as exc:
            raise Phase4RawWriteError(f"P4.08 target case failed: {label}: {exc}") from exc

    def call_write(offset: int, count: int, *, append: bool = False) -> bytes:
        code = b"\xDD\x21" + _word(record)
        code += phase1._ld_hl(SOURCE_BASE)
        code += b"\x01" + _word(count)
        if append:
            code += phase1._call(s["zx48_p408_raw_write_at_eof"])
        else:
            code += b"\x11" + _word(offset)
            code += phase1._call(s["zx48_p408_raw_write"])
        return code

    def a_eq(value: int) -> bytes:
        return bytes((0xFE, value & 0xFF)) + phase1._jp_nz(FAIL_PC)

    def hl_eq(value: int) -> bytes:
        return bytes((0x7C, 0xFE, (value >> 8) & 0xFF)) + phase1._jp_nz(FAIL_PC) + bytes((0x7D, 0xFE, value & 0xFF)) + phase1._jp_nz(FAIL_PC)

    def byte_eq(address: int, value: int) -> bytes:
        return _ld_a_mem(address) + a_eq(value)

    def mem_eq(address: int, expected: bytes) -> bytes:
        code = bytearray()
        for i, value in enumerate(expected):
            code += byte_eq(address + i, value)
        return bytes(code)

    old4 = _record(s, 4, old_ptr)

    code = call_write(1, 2) + phase1._jp_c(FAIL_PC) + hl_eq(2)
    code += mem_eq(old_ptr, b"AXYD")
    code += mem_eq(record, old4)
    execute("in-range-full-write", code, old4, b"XY")

    grown6 = _record(s, 6, old_ptr + 4)
    code = call_write(4, 2) + phase1._jp_c(FAIL_PC) + hl_eq(2)
    code += mem_eq(old_ptr + 4, b"ABCDXY")
    code += mem_eq(record, grown6)
    execute("extending-write-private-swap", code, old4, b"XY")

    grown6_append = _record(s, 6, old_ptr + 4)
    code = call_write(0, 2, append=True) + phase1._jp_c(FAIL_PC) + hl_eq(2)
    code += mem_eq(old_ptr + 4, b"ABCDXY")
    code += mem_eq(record, grown6_append)
    execute("append-helper-uses-transactional-growth", code, old4, b"XY")

    code = call_write(4, 2) + _jp_nc(FAIL_PC) + a_eq(s["E_NOMEM"])
    code += mem_eq(record, old4) + mem_eq(old_ptr, b"ABCD")
    execute("forced-enomem-preserves-old-object", code, old4, b"XY", no_free=True)

    code = call_write(0x7FFF, 2) + _jp_nc(FAIL_PC) + a_eq(s["E_INVAL"])
    code += mem_eq(record, old4) + mem_eq(old_ptr, b"ABCD")
    execute("sparse-offset-rejected-before-size", code, old4, b"XY")

    boundary = _record(s, 0x8000, old_ptr)
    code = call_write(0x8000, 1) + _jp_nc(FAIL_PC) + a_eq(s["E_NOSPC"])
    code += mem_eq(record, boundary)
    execute("32768-plus-one-is-enospc-without-wrap", code, boundary, b"Z", no_free=True)

    code = call_write(0xFFFE, 4) + _jp_nc(FAIL_PC) + a_eq(s["E_INVAL"])
    code += mem_eq(record, old4) + mem_eq(old_ptr, b"ABCD")
    execute("wrapped-offset-plus-count-never-valid", code, old4, b"WXYZ")

    empty = _record(s, 0, 0)
    grown1 = _record(s, 1, old_ptr)
    code = call_write(0, 1) + phase1._jp_c(FAIL_PC) + hl_eq(1)
    code += byte_eq(old_ptr, ord("Q")) + mem_eq(record, grown1)
    execute("zero-length-growth-uses-real-even-allocation", code, empty, b"Q")


def dispatch(
    root: Path,
    action: str,
    step: str,
    *,
    sha256_file: Callable[[Path], str],
    run_command: Callable[..., Any],
    require_project_tool: Callable[[Path, str | Path], Path],
):
    if step != "P4.08":
        raise DriverError(f"Phase-4 RAW write step is not registered: {step}")

    assertions = _source_contract(root)
    failed = [item["name"] for item in assertions if item.get("passed") is not True]
    require(not failed, f"static P4.08 contract failures: {failed}")

    kernel_result, kernel, _listing = phase1._assemble_kernel(root, run_command, require_project_tool)
    fixture_result, binary, listing = _assemble(root, run_command, require_project_tool)
    commands = [kernel_result, fixture_result]
    names = (
        "zx48_p408_raw_write", "zx48_p408_raw_write_at_eof", "p408_record",
        "memory_free_extents", "memory_live_allocations", "ARENA_START", "ARENA_SIZE",
        "OBJ_DAT", "E_INVAL", "E_NOMEM", "E_NOSPC",
    )
    symbols = phase3_open_descriptions._symbols(listing.with_suffix(".sym"), names)
    require(symbols["ARENA_SIZE"] == 0x8000, "P4.08 arena-size contract changed")

    if action == "test":
        _target(root, symbols, binary.read_bytes())
        assertions.extend([
            {"name": "in-range-write-is-full-count-runtime", "passed": True},
            {"name": "growth-private-swap-and-append-helper-runtime", "passed": True},
            {"name": "enomem-preserves-old-object-runtime", "passed": True},
            {"name": "widened-boundary-and-wrap-rejection-runtime", "passed": True},
            {"name": "zero-length-growth-allocation-runtime", "passed": True},
        ])

    hashes = {
        "v1/build/kernel.bin": sha256_file(kernel),
        "v1/build/p408-raw-write.bin": sha256_file(binary),
        "v1/src/kernel/objects.asm": sha256_file(root / "v1/src/kernel/objects.asm"),
        "v1/src/kernel/memory.asm": sha256_file(root / "v1/src/kernel/memory.asm"),
        "v1/tools-host/test-driver/phase4_raw_write.py": sha256_file(root / "v1/tools-host/test-driver/phase4_raw_write.py"),
        "v1/tools-host/test-driver/run.py": sha256_file(root / "v1/tools-host/test-driver/run.py"),
        "v1/dist/certification/P4.07.test.json": sha256_file(root / "v1/dist/certification/P4.07.test.json"),
    }
    return commands, hashes, assertions
