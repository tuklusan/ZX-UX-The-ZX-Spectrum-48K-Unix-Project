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


class Phase4RawReadError(DriverError):
    """Raised when the P4.07 RAW read/seek contract regresses."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Phase4RawReadError(message)


def _word(value: int) -> bytes:
    return bytes((value & 0xFF, (value >> 8) & 0xFF))


def _jp_nc(address: int) -> bytes:
    return b"\xD2" + _word(address)


def _ld_a_mem(address: int) -> bytes:
    return b"\x3A" + _word(address)


def _ld_bc(value: int) -> bytes:
    return b"\x01" + _word(value)


def _assemble(root: Path, run_command: Callable[..., Any], require_project_tool: Callable[[Path, str | Path], Path]):
    assembler = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    fixture = build / "p407-raw-read.asm"
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
    INCLUDE "../src/kernel/handles.asm"
    INCLUDE "../src/kernel/objects.asm"
    EMIT_HANDLE_ROUTINES
    EMIT_OBJECT_OPEN_ROUTINES
    EMIT_P407_RAW_IO_ROUTINES
zx48_free:
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
    SAVEBIN "p407-raw-read.bin",$C000,$-$C000
""",
        encoding="utf-8", newline="\n",
    )
    result = run_command(
        [assembler, "--nologo", "--lst=p407-raw-read.lst", "--sym=p407-raw-read.sym", "p407-raw-read.asm"],
        cwd=build,
        timeout_seconds=30.0,
    )
    require(not result.timed_out and result.exit_code == 0, f"P4.07 fixture assembly failed: {result.stderr or result.stdout}")
    binary = build / "p407-raw-read.bin"
    listing = build / "p407-raw-read.lst"
    require(binary.is_file() and 0 < binary.stat().st_size < 8192, "P4.07 fixture binary missing/oversize")
    return result, binary, listing


def _source_contract(root: Path) -> list[dict[str, object]]:
    objects = (root / "v1/src/kernel/objects.asm").read_text(encoding="utf-8")
    macro = objects.split("MACRO EMIT_P407_RAW_IO_ROUTINES", 1)[1].split("ENDM", 1)[0]
    return [
        {"name": "seek-validates-d-and-handle-before-offset-write", "passed": "ld a,d" in macro and "call zx48_handle_lookup" in macro and macro.index("call zx48_handle_lookup") < macro.index("(ix+OD_OFFSET_O),l")},
        {"name": "seek-only-ram-object-descriptions", "passed": "cp OD_KIND_OBJECT" in macro and "E_NOTSUP" in macro},
        {"name": "seek-range-is-zero-through-logical-eof", "passed": "OBJ_LOGICAL_LENGTH" in macro and "sbc hl,de" in macro and "E_INVAL" in macro},
        {"name": "raw-read-requires-read-access", "passed": "OD_ACCESS_O" in macro and "and O_READ" in macro and "E_PERM" in macro},
        {"name": "raw-logical-physical-lengths-must-match", "passed": "OBJ_LOGICAL_LENGTH" in macro and "OBJ_STORAGE_LENGTH" in macro and "E_FORMAT" in macro},
        {"name": "zero-transfer-returns-before-allocation-pointer", "passed": macro.index("zx48_p407_read_zero:") > macro.index("OBJ_ALLOCATION_PTR")},
        {"name": "nonzero-allocation-pointer-is-even", "passed": "bit 0,e" in macro and "OBJ_ALLOCATION_PTR" in macro},
        {"name": "read-updates-shared-open-description-offset", "passed": macro.count("(ix+OD_OFFSET_O)") >= 4},
        {"name": "packed-path-not-mutated-by-raw-routines", "passed": macro.count("and OBJ_PACKED") >= 2 and "zx48_p407_notsup" in macro},
    ]


def _record(type_id: int, logical: int, storage: int, ptr: int, flags: int = 0) -> bytes:
    raw = bytearray(20)
    raw[:4] = b"file"
    raw[10] = 6
    raw[11] = type_id & 0xFF
    raw[12] = flags & 0xFF
    raw[14:16] = _word(logical)
    raw[16:18] = _word(storage)
    raw[18:20] = _word(ptr)
    return bytes(raw)


def _target(root: Path, s: dict[str, int], module: bytes) -> None:
    od_table = s["open_description_table"]
    obj_table = s["p405_object_table"]
    fake = s["fake_process"]
    payload = s["ARENA_START"] + 0x0200
    buffer = s["ARENA_START"] + 0x1200

    def patch_factory(
        *,
        record: bytes,
        kind: int = None,
        access: int = None,
        offset: int = 0,
        handles: tuple[int, ...] = (0,),
        payload_bytes: bytes = b"",
    ):
        def patch(ram: bytearray) -> None:
            moff = MODULE_BASE - 0x4000
            ram[moff:moff + len(module)] = module
            roff = obj_table - 0x4000
            ram[roff:roff + 20] = record
            ooff = od_table - 0x4000
            od = bytearray(8)
            od[s["OD_KIND_O"]] = s["OD_KIND_OBJECT"] if kind is None else kind
            od[s["OD_ACCESS_O"]] = s["O_READ"] if access is None else access
            od[s["OD_REFS_O"]] = max(1, len(handles))
            od[s["OD_ID_O"]] = 0
            od[s["OD_OFFSET_O"]:s["OD_OFFSET_O"] + 2] = _word(offset)
            ram[ooff:ooff + 8] = od
            hoff = fake - 0x4000 + 16
            ram[hoff:hoff + 8] = bytes((s["HANDLE_FREE"],)) * 8
            for handle in handles:
                ram[hoff + handle] = 0
            if payload_bytes:
                poff = payload - 0x4000
                ram[poff:poff + len(payload_bytes)] = payload_bytes
            boff = buffer - 0x4000
            ram[boff:boff + 16] = bytes((0xA5,)) * 16
        return patch

    def execute(label: str, code: bytes, **patch_kwargs) -> None:
        body = bytes((0xF3,)) + phase1._ld_sp(0xBFC0) + code + phase1._jp(PASS_PC)
        try:
            run_sna(root, body, patch=patch_factory(**patch_kwargs))
        except DriverError as exc:
            raise Phase4RawReadError(f"P4.07 target case failed: {label}: {exc}") from exc

    def call_seek(handle: int, d: int, offset: int) -> bytes:
        return bytes((0x1E, handle & 0xFF, 0x16, d & 0xFF)) + phase1._ld_hl(offset) + phase1._call(s["zx48_p407_sys_seek"])

    def call_read(handle: int, d: int, count: int) -> bytes:
        return bytes((0x1E, handle & 0xFF, 0x16, d & 0xFF)) + phase1._ld_hl(buffer) + _ld_bc(count) + phase1._call(s["zx48_p407_sys_read"])

    def a_eq(value: int) -> bytes:
        return bytes((0xFE, value & 0xFF)) + phase1._jp_nz(FAIL_PC)

    def hl_eq(value: int) -> bytes:
        return bytes((0x7C, 0xFE, (value >> 8) & 0xFF)) + phase1._jp_nz(FAIL_PC) + bytes((0x7D, 0xFE, value & 0xFF)) + phase1._jp_nz(FAIL_PC)

    def byte_eq(address: int, value: int) -> bytes:
        return _ld_a_mem(address) + a_eq(value)

    def expect_error(call: bytes, errno: int, offset: int) -> bytes:
        return call + _jp_nc(FAIL_PC) + a_eq(errno) + byte_eq(od_table + s["OD_OFFSET_O"], offset & 0xFF) + byte_eq(od_table + s["OD_OFFSET_O"] + 1, (offset >> 8) & 0xFF)

    raw4 = _record(s["OBJ_DAT"], 4, 4, payload)
    code = call_read(0, 0, 2) + phase1._jp_c(FAIL_PC) + hl_eq(2)
    code += byte_eq(buffer, ord("A")) + byte_eq(buffer + 1, ord("B"))
    code += byte_eq(od_table + s["OD_OFFSET_O"], 2)
    execute("raw-read-prefix", code, record=raw4, payload_bytes=b"ABCD")

    code = call_read(0, 0, 4) + phase1._jp_c(FAIL_PC) + hl_eq(2)
    code += byte_eq(buffer, ord("C")) + byte_eq(buffer + 1, ord("D"))
    code += byte_eq(od_table + s["OD_OFFSET_O"], 4)
    execute("raw-read-clamps-at-eof", code, record=raw4, offset=2, payload_bytes=b"ABCD")

    code = call_read(0, 0, 3) + phase1._jp_c(FAIL_PC) + hl_eq(0)
    code += byte_eq(buffer, 0xA5) + byte_eq(od_table + s["OD_OFFSET_O"], 4)
    execute("raw-read-at-eof-zero", code, record=raw4, offset=4, payload_bytes=b"ABCD")

    code = call_seek(0, 0, 0) + phase1._jp_c(FAIL_PC) + hl_eq(0)
    code += byte_eq(od_table + s["OD_OFFSET_O"], 0)
    execute("seek-zero", code, record=raw4, offset=2, payload_bytes=b"ABCD")

    code = call_seek(1, 0, 4) + phase1._jp_c(FAIL_PC) + hl_eq(4)
    code += byte_eq(od_table + s["OD_OFFSET_O"], 4)
    code += call_read(0, 0, 1) + phase1._jp_c(FAIL_PC) + hl_eq(0)
    execute("seek-exact-eof-shared-offset", code, record=raw4, handles=(0, 1), payload_bytes=b"ABCD")

    code = expect_error(call_seek(0, 0, 5), s["E_INVAL"], 2)
    execute("seek-beyond-eof-preserves-offset", code, record=raw4, offset=2, payload_bytes=b"ABCD")

    zero = _record(s["OBJ_DAT"], 0, 0, 0)
    code = call_read(0, 0, 7) + phase1._jp_c(FAIL_PC) + hl_eq(0)
    code += byte_eq(buffer, 0xA5)
    code += call_seek(0, 0, 0) + phase1._jp_c(FAIL_PC) + hl_eq(0)
    execute("zero-length-raw-never-dereferences-zero-sentinel", code, record=zero)

    code = expect_error(call_seek(0, 0, 1), s["E_INVAL"], 0)
    execute("zero-length-seek-beyond-eof", code, record=zero)

    for label, kind in (
        ("tty", s["OD_KIND_TTY"]),
        ("null", s["OD_KIND_NULL"]),
        ("tape", s["OD_KIND_TAPE"]),
        ("pipe", s["OD_KIND_PIPE_READ"]),
    ):
        code = expect_error(call_seek(0, 0, 0), s["E_NOTSUP"], 3)
        execute(f"seek-unseekable-{label}", code, record=raw4, kind=kind, offset=3, payload_bytes=b"ABCD")

    code = expect_error(call_seek(0, 1, 0), s["E_INVAL"], 2)
    execute("seek-invalid-d-preserves-offset", code, record=raw4, offset=2, payload_bytes=b"ABCD")

    code = call_seek(7, 0, 0) + _jp_nc(FAIL_PC) + a_eq(s["E_NOENT"])
    execute("seek-invalid-handle", code, record=raw4, handles=(), payload_bytes=b"ABCD")

    code = call_read(0, 0, 1) + _jp_nc(FAIL_PC) + a_eq(s["E_PERM"])
    execute("read-requires-read-access", code, record=raw4, access=s["O_WRITE"], payload_bytes=b"ABCD")


def dispatch(
    root: Path,
    action: str,
    step: str,
    *,
    sha256_file: Callable[[Path], str],
    run_command: Callable[..., Any],
    require_project_tool: Callable[[Path, str | Path], Path],
):
    if step != "P4.07":
        raise DriverError(f"Phase-4 RAW read/seek step is not registered: {step}")

    assertions = _source_contract(root)
    failed = [item["name"] for item in assertions if item.get("passed") is not True]
    require(not failed, f"static P4.07 contract failures: {failed}")

    kernel_result, kernel, _listing = phase1._assemble_kernel(root, run_command, require_project_tool)
    fixture_result, binary, listing = _assemble(root, run_command, require_project_tool)
    commands = [kernel_result, fixture_result]
    names = (
        "zx48_p407_sys_seek", "zx48_p407_sys_read", "zx48_handle_lookup",
        "p405_object_table", "open_description_table", "fake_process",
        "OD_KIND_O", "OD_ACCESS_O", "OD_REFS_O", "OD_ID_O", "OD_OFFSET_O",
        "OD_KIND_OBJECT", "OD_KIND_TTY", "OD_KIND_NULL", "OD_KIND_TAPE", "OD_KIND_PIPE_READ",
        "O_READ", "O_WRITE", "HANDLE_FREE", "OBJ_DAT", "OBJ_PACKED", "ARENA_START",
        "E_INVAL", "E_NOENT", "E_NOTSUP", "E_PERM",
    )
    symbols = phase3_open_descriptions._symbols(listing.with_suffix(".sym"), names)

    if action == "test":
        _target(root, symbols, binary.read_bytes())
        assertions.extend([
            {"name": "raw-read-eof-and-shared-offset-runtime", "passed": True},
            {"name": "seek-zero-eof-and-beyond-eof-runtime", "passed": True},
            {"name": "zero-length-raw-sentinel-runtime", "passed": True},
            {"name": "unseekable-invalid-d-handle-runtime", "passed": True},
        ])

    hashes = {
        "v1/build/kernel.bin": sha256_file(kernel),
        "v1/build/p407-raw-read.bin": sha256_file(binary),
        "v1/src/kernel/objects.asm": sha256_file(root / "v1/src/kernel/objects.asm"),
        "v1/src/kernel/handles.asm": sha256_file(root / "v1/src/kernel/handles.asm"),
        "v1/tools-host/test-driver/phase4_raw_read.py": sha256_file(root / "v1/tools-host/test-driver/phase4_raw_read.py"),
        "v1/tools-host/test-driver/run.py": sha256_file(root / "v1/tools-host/test-driver/run.py"),
        "v1/dist/certification/P4.06.test.json": sha256_file(root / "v1/dist/certification/P4.06.test.json"),
    }
    return commands, hashes, assertions
