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
REQ_BASE = 0xA300
OUT_BASE = 0xA320


class Phase4StatError(DriverError):
    """Raised when the P4.11 SYS_STAT contract regresses."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Phase4StatError(message)


def _word(value: int) -> bytes:
    return bytes((value & 0xFF, (value >> 8) & 0xFF))


def _jp_nc(address: int) -> bytes:
    return b"\xD2" + _word(address)


def _ld_a_mem(address: int) -> bytes:
    return b"\x3A" + _word(address)


def _record(name: bytes, directory: int, type_id: int, flags: int, logical: int, storage: int, ptr: int) -> bytes:
    raw = bytearray(20)
    raw[:len(name)] = name
    raw[10] = directory & 0xFF
    raw[11] = type_id & 0xFF
    raw[12] = flags & 0xFF
    raw[14:16] = _word(logical)
    raw[16:18] = _word(storage)
    raw[18:20] = _word(ptr)
    return bytes(raw)


def _statout(type_id: int, flags: int, logical: int, storage: int, directory: int, state: int) -> bytes:
    return bytes((type_id & 0xFF, flags & 0xFF)) + _word(logical) + _word(storage) + bytes((directory & 0xFF, state & 0xFF, 0, 0))


def _source_contract(root: Path) -> list[dict[str, object]]:
    objects = (root / "v1/src/kernel/objects.asm").read_text(encoding="utf-8")
    syscall = (root / "v1/src/kernel/syscall.asm").read_text(encoding="utf-8")
    omacro = objects.split("MACRO EMIT_P411_STAT_OBJECT_ROUTINES", 1)[1].split("ENDM", 1)[0]
    smacro = syscall.split("MACRO EMIT_P411_SYS_STAT_ROUTINES", 1)[1].split("ENDM", 1)[0]
    return [
        {"name": "stat1-is-exact-four-byte-pointer-pair", "passed": "HL -> STAT1 {u16 path_ptr,u16 out_ptr}." in smacro and "ld bc,4" in smacro},
        {"name": "statout1-is-exact-ten-byte-copy", "passed": "ld bc,10" in smacro and "ldir" in smacro},
        {"name": "complete-request-output-and-path-ranges-prevalidated", "passed": smacro.count("call zx48_user_range_validate") >= 3 and "zx48_p411_stat_path_validate:" in smacro},
        {"name": "output-is-staged-until-resolution-succeeds", "passed": smacro.index("call zx48_p411_stat_resolve") < smacro.index("ld hl,p411_stat_record")},
        {"name": "reserved-u16-is-always-zeroed", "passed": "ld bc,9" in omacro and "p411_stat_record: defs 10,0" in omacro},
        {"name": "ram-stat-copies-type-flags-logical-storage-directory", "passed": all(x in omacro for x in ("OBJ_TYPE_ID", "OBJ_FLAGS_BYTE", "OBJ_LOGICAL_LENGTH", "OBJ_STORAGE_LENGTH", "OBJ_DIR_ID", "STATE_RAM"))},
        {"name": "packed-physical-length-is-record-storage-length", "passed": "OBJ_STORAGE_LENGTH" in omacro and "p411_stat_record+4" in omacro},
        {"name": "tape-backed-lengths-are-ffff", "passed": "ld hl,0-1" in omacro and "STATE_TAPE_BACKED" in omacro},
        {"name": "pseudo-dir-dev-lengths-are-zero", "passed": "OBJ_DIR" in omacro and "OBJ_DEV" in omacro and omacro.count("STATE_PSEUDO") >= 2},
        {"name": "pseudo-directory-reports-parent-id", "passed": "zx48_p411_stat_dir_parent_root:" in omacro and "cp DIR_USERHOME" in omacro and "ld a,DIR_HOME" in omacro},
        {"name": "resident-exact-name-precedes-bcat", "passed": omacro.index("call zx48_p405_object_lookup") < omacro.index("call zx48_p405_is_bcat")},
    ]


def _assemble(root: Path, run_command: Callable[..., Any], require_project_tool: Callable[[Path, str | Path], Path]):
    assembler = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    fixture = build / "p411-stat.asm"
    fixture.write_text(
        """    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
PANIC_SCHEDULER EQU $03
PROC_CWD EQU 28
    ORG $C000
current_pid: db 1
zx48_process_lookup:
    ld ix,fake_process
    xor a
    ret
    INCLUDE "../src/kernel/objects.asm"
    INCLUDE "../src/kernel/syscall.asm"
    EMIT_NAMESPACE_ROUTINES
    EMIT_OBJECT_TYPE_ROUTINES
    EMIT_OBJECT_OPEN_ROUTINES
    EMIT_P411_STAT_OBJECT_ROUTINES
    EMIT_USER_RANGE_VALIDATION_ROUTINE
    EMIT_P411_SYS_STAT_ROUTINES
zx48_free:
    xor a
    ret
zx48_panic:
    scf
    ret
fake_process: defs 48,0
    SAVEBIN "p411-stat.bin",$C000,$-$C000
""",
        encoding="utf-8",
        newline="\n",
    )
    result = run_command(
        [assembler, "--nologo", "--lst=p411-stat.lst", "--sym=p411-stat.sym", "p411-stat.asm"],
        cwd=build,
        timeout_seconds=30.0,
    )
    require(not result.timed_out and result.exit_code == 0, f"P4.11 fixture assembly failed: {result.stderr or result.stdout}")
    binary = build / "p411-stat.bin"
    listing = build / "p411-stat.lst"
    require(binary.is_file() and 0 < binary.stat().st_size < 8192, "P4.11 fixture binary missing/oversize")
    return result, binary, listing


def _target(root: Path, s: dict[str, int], module: bytes) -> None:
    paths = ("/tmp/raw", "/tmp/pak", "/tmp", "/dev/tty", "/bin/sh", "/tmp/missing")
    addresses: dict[str, int] = {}
    payload = bytearray()
    cursor = DATA_BASE
    for path in paths:
        addresses[path] = cursor
        encoded = path.encode("ascii") + b"\x00"
        payload += encoded
        cursor += len(encoded)

    table = s["p405_object_table"]
    raw = _record(b"raw", s["DIR_TMP"], s["OBJ_DAT"], 0, 5, 5, s["ARENA_START"])
    packed = _record(b"pak", s["DIR_TMP"], s["OBJ_TXT"], s["OBJ_PACKED"], 11, 7, s["ARENA_START"] + 8)
    records = raw + packed

    def patch(path_ptr: int, out_ptr: int = OUT_BASE, *, out_fill: int = 0xA5, bad_path_byte: bool = False):
        def apply(ram: bytearray) -> None:
            moff = MODULE_BASE - 0x4000
            ram[moff:moff + len(module)] = module
            poff = DATA_BASE - 0x4000
            ram[poff:poff + len(payload)] = payload
            roff = table - 0x4000
            ram[roff:roff + len(records)] = records
            qoff = REQ_BASE - 0x4000
            ram[qoff:qoff + 4] = _word(path_ptr) + _word(out_ptr)
            if 0x4000 <= out_ptr <= 0xFFFF:
                start = out_ptr - 0x4000
                if 0 <= start < len(ram):
                    ram[start:min(start + 10, len(ram))] = bytes((out_fill,)) * min(10, len(ram) - start)
            if bad_path_byte:
                ram[0x5AFF - 0x4000] = ord("x")
        return apply

    def mem_eq(address: int, expected: bytes) -> bytes:
        code = bytearray()
        for offset, value in enumerate(expected):
            code += _ld_a_mem(address + offset) + bytes((0xFE, value)) + phase1._jp_nz(FAIL_PC)
        return bytes(code)

    def execute(label: str, code: bytes, patcher) -> None:
        body = bytes((0xF3,)) + phase1._ld_sp(0xBFC0) + code + phase1._jp(PASS_PC)
        try:
            run_sna(root, body, patch=patcher)
        except DriverError as exc:
            raise Phase4StatError(f"P4.11 target case failed: {label}: {exc}") from exc

    def success(label: str, path: str, expected: bytes) -> None:
        code = phase1._ld_hl(REQ_BASE) + phase1._call(s["zx48_p411_sys_stat"]) + phase1._jp_c(FAIL_PC)
        code += mem_eq(OUT_BASE, expected)
        execute(label, code, patch(addresses[path]))

    success("raw-record-exact", "/tmp/raw", _statout(s["OBJ_DAT"], 0, 5, 5, s["DIR_TMP"], s["STATE_RAM"]))
    success("packed-record-exact", "/tmp/pak", _statout(s["OBJ_TXT"], s["OBJ_PACKED"], 11, 7, s["DIR_TMP"], s["STATE_RAM"]))
    success("pseudo-directory-zero-lengths", "/tmp", _statout(s["OBJ_DIR"], 0, 0, 0, s["DIR_ROOT"], s["STATE_PSEUDO"]))
    success("pseudo-device-zero-lengths", "/dev/tty", _statout(s["OBJ_DEV"], 0, 0, 0, s["DIR_DEV"], s["STATE_PSEUDO"]))
    success("tape-backed-unknown-lengths", "/bin/sh", _statout(s["OBJ_BIN"], 0, 0xFFFF, 0xFFFF, s["DIR_BIN"], s["STATE_TAPE_BACKED"]))

    code = phase1._ld_hl(REQ_BASE) + phase1._call(s["zx48_p411_sys_stat"]) + _jp_nc(FAIL_PC)
    code += bytes((0xFE, s["E_NOENT"])) + phase1._jp_nz(FAIL_PC)
    code += mem_eq(OUT_BASE, bytes((0xA5,)) * 10)
    execute("missing-path-leaves-output-untouched", code, patch(addresses["/tmp/missing"]))

    code = phase1._ld_hl(0x5AFE) + phase1._call(s["zx48_p411_sys_stat"]) + _jp_nc(FAIL_PC)
    code += bytes((0xFE, s["E_INVAL"])) + phase1._jp_nz(FAIL_PC)
    execute("stat1-crosses-protected-region", code, patch(addresses["/tmp/raw"]))

    code = phase1._ld_hl(REQ_BASE) + phase1._call(s["zx48_p411_sys_stat"]) + _jp_nc(FAIL_PC)
    code += bytes((0xFE, s["E_INVAL"])) + phase1._jp_nz(FAIL_PC)
    execute("statout-crosses-protected-region", code, patch(addresses["/tmp/raw"], 0x5AF8))

    code = phase1._ld_hl(REQ_BASE) + phase1._call(s["zx48_p411_sys_stat"]) + _jp_nc(FAIL_PC)
    code += bytes((0xFE, s["E_INVAL"])) + phase1._jp_nz(FAIL_PC)
    code += mem_eq(OUT_BASE, bytes((0xA5,)) * 10)
    execute("unterminated-path-hits-protected-region-before-output", code, patch(0x5AFF, bad_path_byte=True))


def dispatch(
    root: Path,
    action: str,
    step: str,
    *,
    sha256_file: Callable[[Path], str],
    run_command: Callable[..., Any],
    require_project_tool: Callable[[Path, str | Path], Path],
):
    if step != "P4.11":
        raise DriverError(f"Phase-4 stat step is not registered: {step}")

    assertions = _source_contract(root)
    failed = [item["name"] for item in assertions if item.get("passed") is not True]
    require(not failed, f"static P4.11 contract failures: {failed}")

    kernel_result, kernel, _ = phase1._assemble_kernel(root, run_command, require_project_tool)
    fixture_result, binary, listing = _assemble(root, run_command, require_project_tool)
    commands = [kernel_result, fixture_result]
    names = (
        "zx48_p411_sys_stat", "p405_object_table", "p411_stat_record",
        "OBJ_TXT", "OBJ_BIN", "OBJ_DAT", "OBJ_DIR", "OBJ_DEV", "OBJ_PACKED",
        "DIR_BIN", "DIR_DEV", "DIR_TMP", "STATE_RAM", "STATE_TAPE_BACKED", "STATE_PSEUDO",
        "ARENA_START", "E_INVAL", "E_NOENT",
    )
    symbols = phase3_open_descriptions._symbols(listing.with_suffix(".sym"), names)

    if action == "test":
        _target(root, symbols, binary.read_bytes())
        assertions.extend([
            {"name": "raw-statout1-exact-runtime", "passed": True},
            {"name": "packed-logical-physical-statout1-exact-runtime", "passed": True},
            {"name": "tape-backed-ffff-lengths-runtime", "passed": True},
            {"name": "pseudo-dir-dev-zero-lengths-runtime", "passed": True},
            {"name": "reserved-u16-overwrites-nonzero-sentinel-with-zero", "passed": True},
            {"name": "invalid-record-output-path-ranges-fail-before-output", "passed": True},
            {"name": "missing-path-fails-with-output-unchanged", "passed": True},
        ])

    hashes = {
        "v1/build/kernel.bin": sha256_file(kernel),
        "v1/build/p411-stat.bin": sha256_file(binary),
        "v1/src/kernel/objects.asm": sha256_file(root / "v1/src/kernel/objects.asm"),
        "v1/src/kernel/syscall.asm": sha256_file(root / "v1/src/kernel/syscall.asm"),
        "v1/tools-host/test-driver/phase4_stat.py": sha256_file(root / "v1/tools-host/test-driver/phase4_stat.py"),
        "v1/tools-host/test-driver/run.py": sha256_file(root / "v1/tools-host/test-driver/run.py"),
        "v1/dist/certification/P4.10.test.json": sha256_file(root / "v1/dist/certification/P4.10.test.json"),
    }
    return commands, hashes, assertions
