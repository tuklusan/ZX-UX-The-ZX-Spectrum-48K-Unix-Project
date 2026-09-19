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
DATA_BASE = 0xA000


class Phase4TruncError(DriverError):
    """Raised when the P4.10 truncate contract regresses."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Phase4TruncError(message)


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
    fixture = build / "p410-trunc.asm"
    fixture.write_text(
        """    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
PANIC_SCHEDULER EQU $03
PROC_HANDLES EQU 16
PROC_CWD EQU 28
    ORG $C000
current_pid: db 1
zx48_process_lookup:
    ld ix,fake_process
    xor a
    ret
    INCLUDE "../src/kernel/memory.asm"
    INCLUDE "../src/kernel/handles.asm"
    INCLUDE "../src/kernel/objects.asm"
    INCLUDE "../src/kernel/syscall.asm"
    EMIT_MEMORY_ROUTINES
    EMIT_NAMESPACE_ROUTINES
    EMIT_OBJECT_TYPE_ROUTINES
    EMIT_OBJECT_OPEN_ROUTINES
    EMIT_HANDLE_ROUTINES
    EMIT_P408_RAW_WRITE_ROUTINES
    EMIT_P409_APPEND_ROUTINES
    EMIT_P405_SYS_OPEN_ROUTINES
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
    SAVEBIN "p410-trunc.bin",$C000,$-$C000
""",
        encoding="utf-8",
        newline="\n",
    )
    result = run_command(
        [assembler, "--nologo", "--lst=p410-trunc.lst", "--sym=p410-trunc.sym", "p410-trunc.asm"],
        cwd=build,
        timeout_seconds=30.0,
    )
    require(not result.timed_out and result.exit_code == 0, f"P4.10 fixture assembly failed: {result.stderr or result.stdout}")
    binary = build / "p410-trunc.bin"
    listing = build / "p410-trunc.lst"
    require(binary.is_file() and 0 < binary.stat().st_size < 16384, "P4.10 fixture binary missing/oversize")
    return result, binary, listing


def _source_contract(root: Path) -> list[dict[str, object]]:
    objects = (root / "v1/src/kernel/objects.asm").read_text(encoding="utf-8")
    syscall = (root / "v1/src/kernel/syscall.asm").read_text(encoding="utf-8")
    omacro = objects.split("MACRO EMIT_OBJECT_OPEN_ROUTINES", 1)[1].split("ENDM", 1)[0]
    smacro = syscall.split("MACRO EMIT_P405_SYS_OPEN_ROUTINES", 1)[1].split("ENDM", 1)[0]
    trunc = omacro.split("zx48_p405_object_truncate:", 1)[1].split("zx48_p405_is_bcat:", 1)[0]
    existing = smacro.split("zx48_p405_open_existing:", 1)[1].split("zx48_p405_open_device:", 1)[0]
    reserve = existing.index("call zx48_p405_open_allocate")
    mutate = existing.index("call zx48_p405_object_truncate")
    return [
        {"name": "truncate-saves-old-allocation-before-publication", "passed": trunc.index("p405_truncate_old_ptr") < trunc.index("ld (ix+OBJ_FLAGS_BYTE),a")},
        {"name": "truncate-publishes-empty-raw-bounded-metadata", "passed": all(x in trunc for x in ("OBJ_FLAGS_BYTE", "OBJ_RESERVED_BYTE", "OBJ_LOGICAL_LENGTH", "OBJ_STORAGE_LENGTH", "OBJ_ALLOCATION_PTR"))},
        {"name": "truncate-releases-old-payload-after-publication", "passed": trunc.index("call zx48_free") > trunc.index("ld (ix+OBJ_ALLOCATION_PTR+1),a")},
        {"name": "truncate-rounds-odd-packed-storage-for-free", "passed": "bit 0,c" in trunc and "inc bc" in trunc},
        {"name": "allocator-corruption-after-publication-panics", "passed": "PANIC_SCHEDULER" in trunc and "zx48_panic" in trunc},
        {"name": "open-reserves-description-handle-before-truncate", "passed": reserve < mutate},
        {"name": "trunc-append-is-retained-on-open-description", "passed": "p405_open_flags" in smacro and "O_TRUNC+O_APPEND" in smacro},
    ]


def _record(name: bytes, directory: int, type_id: int, *, flags: int = 0, logical: int = 0, storage: int = 0, ptr: int = 0) -> bytes:
    raw = bytearray(20)
    raw[:len(name)] = name
    raw[10] = directory
    raw[11] = type_id
    raw[12] = flags
    raw[14:16] = _word(logical)
    raw[16:18] = _word(storage)
    raw[18:20] = _word(ptr)
    return bytes(raw)


def _target(root: Path, s: dict[str, int], module: bytes) -> None:
    path = DATA_BASE
    source = DATA_BASE + 0x20
    table = s["p405_object_table"]
    od = s["open_description_table"]
    fake = s["fake_process"]
    free = s["memory_free_extents"]
    live = s["memory_live_allocations"]
    old_ptr = s["ARENA_START"]
    arena_size = s["ARENA_SIZE"]

    def patch_factory(record: bytes, *, handles_full: bool = False, ods_full: bool = False):
        storage = record[16] | (record[17] << 8)
        ptr = record[18] | (record[19] << 8)
        owned = (storage + 1) & ~1 if ptr else 0

        def patch(ram: bytearray) -> None:
            moff = MODULE_BASE - 0x4000
            ram[moff:moff + len(module)] = module
            ram[path - 0x4000:path - 0x4000 + 10] = b"/tmp/file\x00"
            ram[source - 0x4000:source - 0x4000 + 2] = b"XY"
            ram[table - 0x4000:table - 0x4000 + 20] = record
            if ptr and storage:
                ram[ptr - 0x4000:ptr - 0x4000 + storage] = b"ABCDE"[:storage]

            ram[free - 0x4000:free - 0x4000 + 64] = bytes(64)
            if owned:
                ram[free - 0x4000:free - 0x4000 + 4] = _word(ptr + owned) + _word(arena_size - owned)
                ram[live - 0x4000:live - 0x4000 + 2] = _word(1)
            else:
                ram[free - 0x4000:free - 0x4000 + 4] = _word(old_ptr) + _word(arena_size)
                ram[live - 0x4000:live - 0x4000 + 2] = _word(0)

            if handles_full:
                ram[fake - 0x4000 + 16:fake - 0x4000 + 24] = bytes((0,)) * 8
            if ods_full:
                for index in range(24):
                    ram[od - 0x4000 + index * 8] = s["OD_KIND_OBJECT"]
        return patch

    def execute(label: str, code: bytes, record: bytes, *, handles_full: bool = False, ods_full: bool = False) -> None:
        body = bytes((0xF3,)) + phase1._ld_sp(0xBFC0) + code + phase1._jp(PASS_PC)
        try:
            run_sna(root, body, patch=patch_factory(record, handles_full=handles_full, ods_full=ods_full))
        except DriverError as exc:
            raise Phase4TruncError(f"P4.10 target case failed: {label}: {exc}") from exc

    def open_call(flags: int) -> bytes:
        return phase1._ld_hl(path) + bytes((0x0E, flags & 0xFF, 0x06, 0x00)) + phase1._call(s["zx48_sys_open"])

    def byte_eq(address: int, value: int) -> bytes:
        return _ld_a_mem(address) + bytes((0xFE, value & 0xFF)) + phase1._jp_nz(FAIL_PC)

    def mem_eq(address: int, expected: bytes) -> bytes:
        out = bytearray()
        for index, value in enumerate(expected):
            out += byte_eq(address + index, value)
        return bytes(out)

    write = s["O_WRITE"]
    trunc = s["O_TRUNC"]
    append = s["O_APPEND"]
    packed = _record(b"file", s["DIR_TMP"], s["OBJ_DAT"], flags=s["OBJ_PACKED"], logical=5, storage=3, ptr=old_ptr)
    raw = _record(b"file", s["DIR_TMP"], s["OBJ_DAT"], logical=4, storage=4, ptr=old_ptr)
    empty = _record(b"file", s["DIR_TMP"], s["OBJ_DAT"])

    code = open_call(write | trunc) + phase1._jp_c(FAIL_PC)
    code += mem_eq(table, empty)
    code += mem_eq(free, _word(old_ptr) + _word(arena_size))
    code += mem_eq(live, _word(0))
    execute("packed-truncate-empty-raw-and-free-old-rounded-extent", code, packed)

    code = open_call(write | trunc) + _jp_nc(FAIL_PC)
    code += bytes((0xFE, s["E_NOSPC"])) + phase1._jp_nz(FAIL_PC)
    code += mem_eq(table, raw)
    code += mem_eq(free, _word(old_ptr + 4) + _word(arena_size - 4))
    code += mem_eq(live, _word(1))
    execute("handle-failure-before-commit-preserves-object-and-allocation", code, raw, handles_full=True)

    code = open_call(write | trunc) + _jp_nc(FAIL_PC)
    code += bytes((0xFE, s["E_NOSPC"])) + phase1._jp_nz(FAIL_PC)
    code += mem_eq(table, raw)
    code += mem_eq(free, _word(old_ptr + 4) + _word(arena_size - 4))
    code += mem_eq(live, _word(1))
    execute("description-failure-before-commit-preserves-object-and-allocation", code, raw, ods_full=True)

    flags = write | trunc | append
    code = open_call(flags) + phase1._jp_c(FAIL_PC)
    code += phase1._ld_hl(source) + b"\x01\x02\x00" + bytes((0x1E, 0x00, 0x16, 0x00))
    code += phase1._call(s["zx48_p409_sys_write"]) + phase1._jp_c(FAIL_PC)
    code += bytes((0x7C, 0xB5)) + phase1._jp_nz(FAIL_PC)
    code += mem_eq(old_ptr, b"XY")
    grown = _record(b"file", s["DIR_TMP"], s["OBJ_DAT"], logical=2, storage=2, ptr=old_ptr)
    code += mem_eq(table, grown)
    code += byte_eq(od + s["OD_ACCESS_O"], flags)
    code += byte_eq(od + s["OD_OFFSET_O"], 2) + byte_eq(od + s["OD_OFFSET_O"] + 1, 0)
    execute("trunc-append-first-write-appends-to-new-empty-eof", code, raw)


def dispatch(
    root: Path,
    action: str,
    step: str,
    *,
    sha256_file: Callable[[Path], str],
    run_command: Callable[..., Any],
    require_project_tool: Callable[[Path, str | Path], Path],
):
    if step != "P4.10":
        raise DriverError(f"Phase-4 truncate step is not registered: {step}")

    assertions = _source_contract(root)
    failed = [item["name"] for item in assertions if item.get("passed") is not True]
    require(not failed, f"static P4.10 contract failures: {failed}")

    kernel_result, kernel, _listing = phase1._assemble_kernel(root, run_command, require_project_tool)
    fixture_result, binary, listing = _assemble(root, run_command, require_project_tool)
    commands = [kernel_result, fixture_result]
    names = (
        "zx48_sys_open", "zx48_p409_sys_write", "p405_object_table", "open_description_table", "fake_process",
        "memory_free_extents", "memory_live_allocations", "ARENA_START", "ARENA_SIZE",
        "OD_ACCESS_O", "OD_OFFSET_O", "OD_KIND_OBJECT", "O_WRITE", "O_TRUNC", "O_APPEND",
        "OBJ_DAT", "OBJ_PACKED", "DIR_TMP", "E_NOSPC",
    )
    symbols = phase3_open_descriptions._symbols(listing.with_suffix(".sym"), names)
    require(symbols["ARENA_SIZE"] == 0x8000, "P4.10 arena-size contract changed")

    if action == "test":
        _target(root, symbols, binary.read_bytes())
        assertions.extend([
            {"name": "truncate-to-empty-raw-and-free-old-payload-runtime", "passed": True},
            {"name": "failure-before-truncate-commit-preserves-old-object-runtime", "passed": True},
            {"name": "trunc-append-appends-to-new-empty-eof-runtime", "passed": True},
        ])

    hashes = {
        "v1/build/kernel.bin": sha256_file(kernel),
        "v1/build/p410-trunc.bin": sha256_file(binary),
        "v1/src/kernel/objects.asm": sha256_file(root / "v1/src/kernel/objects.asm"),
        "v1/src/kernel/memory.asm": sha256_file(root / "v1/src/kernel/memory.asm"),
        "v1/src/kernel/syscall.asm": sha256_file(root / "v1/src/kernel/syscall.asm"),
        "v1/tools-host/test-driver/phase4_trunc.py": sha256_file(root / "v1/tools-host/test-driver/phase4_trunc.py"),
        "v1/tools-host/test-driver/run.py": sha256_file(root / "v1/tools-host/test-driver/run.py"),
        "v1/dist/certification/P4.09.test.json": sha256_file(root / "v1/dist/certification/P4.09.test.json"),
    }
    return commands, hashes, assertions
