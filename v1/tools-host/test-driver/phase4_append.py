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


class Phase4AppendError(DriverError):
    """Raised when the P4.09 append contract regresses."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Phase4AppendError(message)


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
    fixture = build / "p409-append.asm"
    fixture.write_text(
        """    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
PANIC_SCHEDULER EQU $03
PROC_HANDLES EQU 16
    ORG $C000
current_pid: db 1
zx48_process_lookup:
    ld ix,fake_process
    xor a
    ret
    INCLUDE "../src/kernel/memory.asm"
    INCLUDE "../src/kernel/handles.asm"
    INCLUDE "../src/kernel/objects.asm"
    EMIT_MEMORY_ROUTINES
    EMIT_HANDLE_ROUTINES
    EMIT_OBJECT_OPEN_ROUTINES
    EMIT_P408_RAW_WRITE_ROUTINES
    EMIT_P409_APPEND_ROUTINES
zx48_process_count:
    xor a
    ret
zx48_pipe_endpoint_closed:
    xor a
    ret
zx48_panic:
    scf
    ret
fake_process:
    defs 16,0
    defs 8,HANDLE_FREE
    defs 24,0
    SAVEBIN "p409-append.bin",$C000,$-$C000
""",
        encoding="utf-8", newline="\n",
    )
    result = run_command(
        [assembler, "--nologo", "--lst=p409-append.lst", "--sym=p409-append.sym", "p409-append.asm"],
        cwd=build,
        timeout_seconds=30.0,
    )
    require(not result.timed_out and result.exit_code == 0, f"P4.09 fixture assembly failed: {result.stderr or result.stdout}")
    binary = build / "p409-append.bin"
    listing = build / "p409-append.lst"
    require(binary.is_file() and 0 < binary.stat().st_size < 12288, "P4.09 fixture binary missing/oversize")
    return result, binary, listing


def _source_contract(root: Path) -> list[dict[str, object]]:
    objects = (root / "v1/src/kernel/objects.asm").read_text(encoding="utf-8")
    macro = objects.split("MACRO EMIT_P409_APPEND_ROUTINES", 1)[1].split("ENDM", 1)[0]
    append_branch = macro.split("and O_APPEND", 1)[1].split("zx48_p409_offset_write:", 1)[0]
    return [
        {"name": "write-validates-handle-write-and-object-kind", "passed": all(x in macro for x in ("call zx48_handle_lookup", "and O_WRITE", "cp OD_KIND_OBJECT"))},
        {"name": "append-flag-read-from-shared-open-description", "passed": "OD_ACCESS_O" in macro and "and O_APPEND" in macro},
        {"name": "append-reselects-eof-via-p408-transaction", "passed": "call zx48_p408_raw_write_at_eof" in append_branch},
        {"name": "append-branch-does-not-use-stored-offset-before-write", "passed": "OD_OFFSET_O" not in append_branch},
        {"name": "successful-append-publishes-new-eof-to-shared-offset", "passed": "OBJ_LOGICAL_LENGTH" in append_branch and "zx48_p409_commit_offset" in macro},
        {"name": "nonappend-path-retains-offset-write-semantics", "passed": "zx48_p409_offset_write:" in macro and "call zx48_p408_raw_write" in macro},
        {"name": "failed-write-cannot-advance-shared-offset", "passed": macro.index("ret c", macro.index("call zx48_p408_raw_write_at_eof")) < macro.index("zx48_p409_commit_offset:")},
    ]


def _record(s: dict[str, int], logical: int, ptr: int) -> bytes:
    raw = bytearray(20)
    raw[:4] = b"file"
    raw[10] = s["DIR_TMP"]
    raw[11] = s["OBJ_DAT"]
    raw[14:16] = _word(logical)
    raw[16:18] = _word(logical)
    raw[18:20] = _word(ptr)
    return bytes(raw)


def _target(root: Path, s: dict[str, int], module: bytes) -> None:
    obj = s["p405_object_table"]
    od = s["open_description_table"]
    fake = s["fake_process"]
    free = s["memory_free_extents"]
    live = s["memory_live_allocations"]
    old_ptr = s["ARENA_START"]

    def patch_factory(*, offset: int, append: bool = True, no_free: bool = False, source: bytes = b"XY"):
        def patch(ram: bytearray) -> None:
            moff = MODULE_BASE - 0x4000
            ram[moff:moff + len(module)] = module
            old = _record(s, 4, old_ptr)
            ooff = obj - 0x4000
            ram[ooff:ooff + 20] = old
            ram[old_ptr - 0x4000:old_ptr - 0x4000 + 4] = b"ABCD"
            soff = SOURCE_BASE - 0x4000
            ram[soff:soff + len(source)] = source

            odrec = bytearray(8)
            odrec[s["OD_KIND_O"]] = s["OD_KIND_OBJECT"]
            odrec[s["OD_ACCESS_O"]] = s["O_WRITE"] | (s["O_APPEND"] if append else 0)
            odrec[s["OD_REFS_O"]] = 1
            odrec[s["OD_ID_O"]] = 0
            odrec[s["OD_OFFSET_O"]:s["OD_OFFSET_O"] + 2] = _word(offset)
            ram[od - 0x4000:od - 0x4000 + 8] = odrec

            hoff = fake - 0x4000 + 16
            ram[hoff:hoff + 8] = bytes((s["HANDLE_FREE"],)) * 8
            ram[hoff] = 0

            foff = free - 0x4000
            ram[foff:foff + 64] = bytes(64)
            if not no_free:
                ram[foff:foff + 4] = _word(old_ptr + 4) + _word(s["ARENA_SIZE"] - 4)
            ram[live - 0x4000:live - 0x4000 + 2] = _word(1)
        return patch

    def execute(label: str, code: bytes, **patch_kwargs) -> None:
        body = bytes((0xF3,)) + phase1._ld_sp(0xBFC0) + code + phase1._jp(PASS_PC)
        try:
            run_sna(root, body, patch=patch_factory(**patch_kwargs))
        except DriverError as exc:
            raise Phase4AppendError(f"P4.09 target case failed: {label}: {exc}") from exc

    def call_write(count: int = 2) -> bytes:
        return bytes((0x1E, 0x00, 0x16, 0x00)) + phase1._ld_hl(SOURCE_BASE) + b"\x01" + _word(count) + phase1._call(s["zx48_p409_sys_write"])

    def a_eq(value: int) -> bytes:
        return bytes((0xFE, value & 0xFF)) + phase1._jp_nz(FAIL_PC)

    def hl_eq(value: int) -> bytes:
        return bytes((0x7C, 0xFE, (value >> 8) & 0xFF)) + phase1._jp_nz(FAIL_PC) + bytes((0x7D, 0xFE, value & 0xFF)) + phase1._jp_nz(FAIL_PC)

    def byte_eq(address: int, value: int) -> bytes:
        return _ld_a_mem(address) + a_eq(value)

    def mem_eq(address: int, expected: bytes) -> bytes:
        code = bytearray()
        for index, value in enumerate(expected):
            code += byte_eq(address + index, value)
        return bytes(code)

    grown6 = _record(s, 6, old_ptr + 4)
    code = call_write() + phase1._jp_c(FAIL_PC) + hl_eq(2)
    code += mem_eq(old_ptr + 4, b"ABCDXY")
    code += mem_eq(obj, grown6)
    code += byte_eq(od + s["OD_OFFSET_O"], 6) + byte_eq(od + s["OD_OFFSET_O"] + 1, 0)
    execute("seeked-offset-one-still-appends-at-eof", code, offset=1)

    code = call_write() + phase1._jp_c(FAIL_PC) + hl_eq(2)
    code += mem_eq(old_ptr + 4, b"ABCDXY")
    code += byte_eq(od + s["OD_OFFSET_O"], 6)
    execute("seeked-offset-zero-still-appends-at-eof", code, offset=0)

    code = call_write() + _jp_nc(FAIL_PC) + a_eq(s["E_NOMEM"])
    code += mem_eq(obj, _record(s, 4, old_ptr)) + mem_eq(old_ptr, b"ABCD")
    code += byte_eq(od + s["OD_OFFSET_O"], 1) + byte_eq(od + s["OD_OFFSET_O"] + 1, 0)
    execute("append-growth-failure-preserves-object-and-seeked-offset", code, offset=1, no_free=True)

    in_place = _record(s, 4, old_ptr)
    code = call_write() + phase1._jp_c(FAIL_PC) + hl_eq(2)
    code += mem_eq(old_ptr, b"AXYD") + mem_eq(obj, in_place)
    code += byte_eq(od + s["OD_OFFSET_O"], 3)
    execute("nonappend-control-uses-shared-offset", code, offset=1, append=False)


def dispatch(
    root: Path,
    action: str,
    step: str,
    *,
    sha256_file: Callable[[Path], str],
    run_command: Callable[..., Any],
    require_project_tool: Callable[[Path, str | Path], Path],
):
    if step != "P4.09":
        raise DriverError(f"Phase-4 append step is not registered: {step}")

    assertions = _source_contract(root)
    failed = [item["name"] for item in assertions if item.get("passed") is not True]
    require(not failed, f"static P4.09 contract failures: {failed}")

    kernel_result, kernel, _listing = phase1._assemble_kernel(root, run_command, require_project_tool)
    fixture_result, binary, listing = _assemble(root, run_command, require_project_tool)
    commands = [kernel_result, fixture_result]
    names = (
        "zx48_p409_sys_write", "p405_object_table", "open_description_table", "fake_process",
        "memory_free_extents", "memory_live_allocations", "ARENA_START", "ARENA_SIZE",
        "OD_KIND_O", "OD_ACCESS_O", "OD_REFS_O", "OD_ID_O", "OD_OFFSET_O", "OD_KIND_OBJECT",
        "O_WRITE", "O_APPEND", "HANDLE_FREE", "DIR_TMP", "OBJ_DAT", "E_NOMEM",
    )
    symbols = phase3_open_descriptions._symbols(listing.with_suffix(".sym"), names)
    require(symbols["ARENA_SIZE"] == 0x8000, "P4.09 arena-size contract changed")

    if action == "test":
        _target(root, symbols, binary.read_bytes())
        assertions.extend([
            {"name": "seek-then-append-reselects-current-eof-runtime", "passed": True},
            {"name": "offset-based-append-bug-fixture-cannot-pass", "passed": True},
            {"name": "append-failure-preserves-prewrite-object-and-offset-runtime", "passed": True},
            {"name": "nonappend-control-remains-offset-based-runtime", "passed": True},
        ])

    hashes = {
        "v1/build/kernel.bin": sha256_file(kernel),
        "v1/build/p409-append.bin": sha256_file(binary),
        "v1/src/kernel/objects.asm": sha256_file(root / "v1/src/kernel/objects.asm"),
        "v1/src/kernel/memory.asm": sha256_file(root / "v1/src/kernel/memory.asm"),
        "v1/src/kernel/handles.asm": sha256_file(root / "v1/src/kernel/handles.asm"),
        "v1/tools-host/test-driver/phase4_append.py": sha256_file(root / "v1/tools-host/test-driver/phase4_append.py"),
        "v1/tools-host/test-driver/run.py": sha256_file(root / "v1/tools-host/test-driver/run.py"),
        "v1/dist/certification/P4.08.test.json": sha256_file(root / "v1/dist/certification/P4.08.test.json"),
    }
    return commands, hashes, assertions
