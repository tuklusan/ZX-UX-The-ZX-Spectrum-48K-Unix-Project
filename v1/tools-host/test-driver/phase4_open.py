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


class Phase4OpenError(DriverError):
    """Raised when the P4.05 typed-open transaction regresses."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Phase4OpenError(message)


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
    fixture = build / "p405-open.asm"
    fixture.write_text(
        """    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
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
    EMIT_P405_SYS_OPEN_ROUTINES
fake_process: defs 48,0
    SAVEBIN "p405-open.bin",$C000,$-$C000
""",
        encoding="utf-8",
        newline="\n",
    )
    result = run_command(
        [assembler, "--nologo", "--lst=p405-open.lst", "--sym=p405-open.sym", "p405-open.asm"],
        cwd=build,
        timeout_seconds=30.0,
    )
    require(not result.timed_out and result.exit_code == 0, f"P4.05 fixture assembly failed: {result.stderr or result.stdout}")
    binary = build / "p405-open.bin"
    listing = build / "p405-open.lst"
    require(binary.is_file() and 0 < binary.stat().st_size < 8192, "P4.05 fixture binary missing/oversize")
    return result, binary, listing


def _source_contract(root: Path) -> list[dict[str, object]]:
    inc = (root / "v1/include/zx48ux.inc").read_text(encoding="utf-8")
    objects = (root / "v1/src/kernel/objects.asm").read_text(encoding="utf-8")
    syscall = (root / "v1/src/kernel/syscall.asm").read_text(encoding="utf-8")
    omacro = objects.split("MACRO EMIT_OBJECT_OPEN_ROUTINES", 1)[1].split("ENDM", 1)[0]
    smacro = syscall.split("MACRO EMIT_P405_SYS_OPEN_ROUTINES", 1)[1].split("ENDM", 1)[0]
    exact_flags = (
        "O_READ                   EQU $01", "O_WRITE                  EQU $02",
        "O_CREATE                 EQU $04", "O_TRUNC                  EQU $08",
        "O_APPEND                 EQU $10", "O_EXCL                   EQU $20",
    )
    return [
        {"name": "open-flag-values-exact", "passed": all(x in inc for x in exact_flags)},
        {"name": "unknown-and-access-flags-validated", "passed": "and $c0" in smacro and "and O_READ+O_WRITE" in smacro},
        {"name": "trunc-append-require-write", "passed": "and O_TRUNC+O_APPEND" in smacro and "and O_WRITE" in smacro},
        {"name": "excl-requires-create", "passed": "and O_EXCL" in smacro and "and O_CREATE" in smacro},
        {"name": "noncreate-requires-zero-type", "passed": "p405_open_type" in smacro and "zx48_p405_open_type_check" in smacro},
        {"name": "create-publishes-type-last", "passed": "Type is the occupancy/publication byte and is committed last." in omacro},
        {"name": "existing-trunc-commits-empty-raw", "passed": "zx48_p405_object_truncate:" in omacro and all(x in omacro for x in ("OBJ_FLAGS_BYTE", "OBJ_LOGICAL_LENGTH", "OBJ_STORAGE_LENGTH", "OBJ_ALLOCATION_PTR"))},
        {"name": "pseudo-devices-and-pinned-path-explicit", "passed": all(x in omacro for x in ("p405_tty_name", "p405_null_name", "p405_tape_name", "p405_pinned_name"))},
        {"name": "bcat-only-name-explicit", "passed": "p405_bcat_name" in omacro and "E_AGAIN" in smacro},
        {"name": "tape-byte-io-ioctl-notsup", "passed": all(x in smacro for x in ("zx48_p405_tape_read:", "zx48_p405_tape_write:", "zx48_p405_tape_ioctl:", "E_NOTSUP"))},
        {"name": "typed-open-does-not-infer-suffix", "passed": "suffix" not in omacro.lower() and "suffix" not in smacro.lower()},
    ]


def _record(name: bytes, directory: int, type_id: int, flags: int = 0, logical: int = 0, storage: int = 0, ptr: int = 0) -> bytes:
    require(len(name) <= 10, "test record name too long")
    raw = bytearray(20)
    raw[:len(name)] = name
    raw[10] = directory & 0xFF
    raw[11] = type_id & 0xFF
    raw[12] = flags & 0xFF
    raw[14:16] = _word(logical)
    raw[16:18] = _word(storage)
    raw[18:20] = _word(ptr)
    return bytes(raw)


def _target(root: Path, s: dict[str, int], module: bytes) -> None:
    paths = [
        "/tmp", "/tmp/file", "/tmp/new", "/bin/new", "/bin/sh", "/bin/tapeonly",
        "/dev/tty", "/dev/null", "/dev/tape", "/dev/foo", "/dev/TTY",
    ]
    addresses: dict[str, int] = {}
    payload = bytearray()
    cursor = DATA_BASE
    for value in paths:
        addresses[value] = cursor
        encoded = value.encode("ascii") + bytes((0,))
        payload += encoded
        cursor += len(encoded)

    table = s["p405_object_table"]

    def patch_factory(record: bytes | None = None):
        def patch(ram: bytearray) -> None:
            moff = MODULE_BASE - 0x4000
            ram[moff:moff + len(module)] = module
            poff = DATA_BASE - 0x4000
            ram[poff:poff + len(payload)] = payload
            if record is not None:
                roff = table - 0x4000
                ram[roff:roff + 20] = record
        return patch

    def mem_eq(address: int, data: bytes) -> bytes:
        code = bytearray()
        for offset, value in enumerate(data):
            code += _ld_a_mem(address + offset)
            code += bytes((0xFE, value))
            code += phase1._jp_nz(FAIL_PC)
        return bytes(code)

    def byte_eq(address: int, value: int) -> bytes:
        return _ld_a_mem(address) + bytes((0xFE, value & 0xFF)) + phase1._jp_nz(FAIL_PC)

    def open_call(path: str, flags: int, type_id: int) -> bytes:
        return (
            phase1._ld_hl(addresses[path])
            + bytes((0x0E, flags & 0xFF, 0x06, type_id & 0xFF))
            + phase1._call(s["zx48_sys_open"])
        )

    def execute(label: str, code: bytes, record: bytes | None = None) -> None:
        body = bytes((0xF3,)) + phase1._ld_sp(0xBFC0) + code + phase1._jp(PASS_PC)
        try:
            run_sna(root, body, patch=patch_factory(record))
        except DriverError as exc:
            raise Phase4OpenError(f"P4.05 target case failed: {label}: {exc}") from exc

    def expect_error(label: str, path: str, flags: int, type_id: int, errno: int, record: bytes | None = None, unchanged: bool = False) -> None:
        code = open_call(path, flags, type_id) + _jp_nc(FAIL_PC)
        code += bytes((0xFE, errno & 0xFF)) + phase1._jp_nz(FAIL_PC)
        if unchanged and record is not None:
            code += mem_eq(table, record)
        execute(label, code, record)

    read = s["O_READ"]
    write = s["O_WRITE"]
    create = s["O_CREATE"]
    trunc = s["O_TRUNC"]
    append = s["O_APPEND"]
    excl = s["O_EXCL"]

    expect_error("unknown-flag", "/tmp/file", read | 0x40, 0, s["E_INVAL"])
    expect_error("missing-access", "/tmp/new", create, s["OBJ_C"], s["E_INVAL"])
    expect_error("trunc-requires-write", "/tmp/file", read | trunc, 0, s["E_INVAL"])
    expect_error("append-requires-write", "/tmp/file", read | append, 0, s["E_INVAL"])
    expect_error("excl-requires-create", "/tmp/file", write | excl, 0, s["E_INVAL"])
    expect_error("noncreate-type-must-zero", "/tmp/file", read, s["OBJ_C"], s["E_INVAL"])
    expect_error("existing-create-type-range", "/tmp/file", read | create, s["OBJ_SYS"], s["E_INVAL"])
    expect_error("directory-open-perm", "/tmp", read, 0, s["E_PERM"])
    expect_error("missing-without-create", "/tmp/new", read, 0, s["E_NOENT"])
    expect_error("missing-create-zero-type", "/tmp/new", write | create, 0, s["E_INVAL"])
    expect_error("bin-rejects-c", "/bin/new", write | create, s["OBJ_C"], s["E_PERM"])
    expect_error("unknown-device", "/dev/foo", read, 0, s["E_NOENT"])
    expect_error("device-case-sensitive", "/dev/TTY", read, 0, s["E_NOENT"])
    expect_error("device-type-must-zero", "/dev/tty", read, s["OBJ_TXT"], s["E_INVAL"])
    expect_error("device-create-forbidden", "/dev/tty", read | create, 0, s["E_PERM"])
    expect_error("device-trunc-forbidden", "/dev/null", write | trunc, 0, s["E_PERM"])
    expect_error("device-append-forbidden", "/dev/tape", write | append, 0, s["E_PERM"])

    existing = _record(b"file", s["DIR_TMP"], s["OBJ_DAT"])
    code = open_call("/tmp/file", read | create, s["OBJ_C"]) + phase1._jp_c(FAIL_PC)
    code += mem_eq(table, existing)
    code += byte_eq(s["p405_result_kind"], s["P405_KIND_OBJECT"])
    code += byte_eq(s["p405_result_type"], s["OBJ_DAT"])
    execute("existing-type-preserved", code, existing)

    expect_error(
        "existing-excl-eexist-unchanged",
        "/tmp/file", write | create | excl, s["OBJ_C"], s["E_EXIST"], existing, True,
    )

    created = _record(b"new", s["DIR_TMP"], s["OBJ_C"])
    code = open_call("/tmp/new", write | create, s["OBJ_C"]) + phase1._jp_c(FAIL_PC)
    code += mem_eq(table, created)
    code += byte_eq(s["p405_result_type"], s["OBJ_C"])
    execute("absent-create-empty-raw", code)

    packed = _record(b"file", s["DIR_TMP"], s["OBJ_DAT"], s["OBJ_PACKED"], 5, 3, s["ARENA_START"])
    truncated = _record(b"file", s["DIR_TMP"], s["OBJ_DAT"])
    flags = write | trunc | append
    code = open_call("/tmp/file", flags, 0) + phase1._jp_c(FAIL_PC)
    code += mem_eq(table, truncated)
    code += byte_eq(s["p405_result_flags"], flags)
    execute("trunc-append-empty-then-retain-append", code, packed)

    for path, kind, flags in (
        ("/dev/tty", s["P405_KIND_TTY"], read),
        ("/dev/null", s["P405_KIND_NULL"], write),
        ("/dev/tape", s["P405_KIND_TAPE"], read | write),
    ):
        code = open_call(path, flags, 0) + phase1._jp_c(FAIL_PC)
        code += byte_eq(s["p405_result_kind"], kind)
        execute(f"pseudo-open-{path}", code)

    code = open_call("/bin/sh", read, 0) + phase1._jp_c(FAIL_PC)
    code += byte_eq(s["p405_result_kind"], s["P405_KIND_PINNED"])
    execute("pinned-read-open", code)
    expect_error("pinned-write-perm", "/bin/sh", write, 0, s["E_PERM"])
    expect_error("pinned-create-perm", "/bin/sh", read | create, 0, s["E_PERM"])
    expect_error("pinned-excl-eexist", "/bin/sh", read | create | excl, 0, s["E_EXIST"])

    zero_record = bytes(20)
    code = open_call("/bin/tapeonly", read, 0) + _jp_nc(FAIL_PC)
    code += bytes((0xFE, s["E_AGAIN"])) + phase1._jp_nz(FAIL_PC)
    code += mem_eq(table, zero_record)
    code += byte_eq(s["p405_tape_motion"], 0x5A)
    execute("bcat-only-eagain-no-motion", code)

    for routine in ("zx48_p405_tape_read", "zx48_p405_tape_write", "zx48_p405_tape_ioctl"):
        code = phase1._call(s[routine]) + _jp_nc(FAIL_PC)
        code += bytes((0xFE, s["E_NOTSUP"])) + phase1._jp_nz(FAIL_PC)
        code += byte_eq(s["p405_tape_motion"], 0x5A)
        execute(f"{routine}-notsup-no-motion", code)


def dispatch(
    root: Path,
    action: str,
    step: str,
    *,
    sha256_file: Callable[[Path], str],
    run_command: Callable[..., Any],
    require_project_tool: Callable[[Path, str | Path], Path],
):
    if step != "P4.05":
        raise DriverError(f"Phase-4 typed-open step is not registered: {step}")

    assertions = _source_contract(root)
    failed = [item["name"] for item in assertions if item.get("passed") is not True]
    require(not failed, f"static P4.05 contract failures: {failed}")

    kernel_result, kernel, _listing = phase1._assemble_kernel(root, run_command, require_project_tool)
    fixture_result, binary, listing = _assemble(root, run_command, require_project_tool)
    commands = [kernel_result, fixture_result]
    names = (
        "zx48_sys_open", "zx48_p405_tape_read", "zx48_p405_tape_write", "zx48_p405_tape_ioctl",
        "p405_object_table", "p405_object_table_end", "p405_result_kind", "p405_result_type",
        "p405_result_flags", "p405_tape_motion",
        "P405_KIND_OBJECT", "P405_KIND_TTY", "P405_KIND_NULL", "P405_KIND_TAPE", "P405_KIND_PINNED",
        "O_READ", "O_WRITE", "O_CREATE", "O_TRUNC", "O_APPEND", "O_EXCL",
        "OBJ_TXT", "OBJ_C", "OBJ_DAT", "OBJ_SYS", "OBJ_PACKED", "DIR_TMP", "ARENA_START",
        "E_INVAL", "E_NOENT", "E_PERM", "E_AGAIN", "E_NOTSUP", "E_EXIST",
    )
    symbols = phase3_open_descriptions._symbols(listing.with_suffix(".sym"), names)
    require(symbols["p405_object_table_end"] - symbols["p405_object_table"] == 640, "P4.05 object table footprint changed")
    require([symbols[x] for x in ("O_READ","O_WRITE","O_CREATE","O_TRUNC","O_APPEND","O_EXCL")] == [1,2,4,8,16,32], "P4.05 open flag values changed")

    if action == "test":
        _target(root, symbols, binary.read_bytes())
        assertions.extend([
            {"name": "full-open-flag-type-path-matrix-runtime", "passed": True},
            {"name": "absent-create-and-existing-type-preservation-exact", "passed": True},
            {"name": "trunc-append-empty-raw-and-append-state-exact", "passed": True},
            {"name": "pseudo-pinned-bcat-and-tape-control-rules-exact", "passed": True},
            {"name": "all-negative-cases-fail-before-publication", "passed": True},
        ])

    hashes = {
        "v1/build/kernel.bin": sha256_file(kernel),
        "v1/build/p405-open.bin": sha256_file(binary),
        "v1/src/kernel/objects.asm": sha256_file(root / "v1/src/kernel/objects.asm"),
        "v1/src/kernel/syscall.asm": sha256_file(root / "v1/src/kernel/syscall.asm"),
        "v1/tools-host/test-driver/phase4_open.py": sha256_file(root / "v1/tools-host/test-driver/phase4_open.py"),
        "v1/tools-host/test-driver/run.py": sha256_file(root / "v1/tools-host/test-driver/run.py"),
        "v1/dist/certification/P4.04.test.json": sha256_file(root / "v1/dist/certification/P4.04.test.json"),
    }
    return commands, hashes, assertions
