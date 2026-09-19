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
PAYLOAD_BASE = 0xA600


class Phase4RenameError(DriverError):
    """Raised when the P4.14 SYS_RENAME contract regresses."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Phase4RenameError(message)


def _word(value: int) -> bytes:
    return bytes((value & 0xFF, (value >> 8) & 0xFF))


def _jp_nc(address: int) -> bytes:
    return b"\xD2" + _word(address)


def _ld_a_mem(address: int) -> bytes:
    return b"\x3A" + _word(address)


def _record(name: bytes, directory: int, type_id: int, logical: int, storage: int, ptr: int, *, flags: int = 0) -> bytes:
    raw = bytearray(20)
    raw[:len(name)] = name
    raw[10] = directory
    raw[11] = type_id
    raw[12] = flags
    raw[14:16] = _word(logical)
    raw[16:18] = _word(storage)
    raw[18:20] = _word(ptr)
    return bytes(raw)


def _source_contract(root: Path) -> list[dict[str, object]]:
    objects = (root / "v1/src/kernel/objects.asm").read_text(encoding="utf-8")
    macro = objects.split("MACRO EMIT_P414_RENAME_ROUTINES", 1)[1].split("ENDM", 1)[0]
    return [
        {"name": "ren1-is-exact-four-byte-pointer-pair", "passed": "REN1 {u16 old_path_ptr,u16 new_path_ptr}" in macro and "ld bc,4" in macro},
        {"name": "both-paths-prevalidated-before-resolution", "passed": macro.count("call zx48_p414_validate_cstr") == 2 and macro.index("call zx48_p414_validate_cstr") < macro.index("call zx48_path_resolve")},
        {"name": "source-must-be-mutable-ram", "passed": "call zx48_object_public_type_allowed" in macro and "zx48_p414_source_found:" in macro},
        {"name": "destination-type-compatibility-precedes-mutation", "passed": macro.count("call zx48_object_public_type_allowed") >= 2 and macro.index("zx48_p414_commit:") > macro.rindex("call zx48_object_public_type_allowed")},
        {"name": "exact-same-path-is-noop", "passed": "Exact same normalized path is a no-op success." in macro and "call zx48_p414_name_equal" in macro},
        {"name": "case-only-rename-can-commit", "passed": "zx48_p414_commit:" in macro and "zx48_p414_name_copy:" in macro},
        {"name": "distinct-resident-collision-precommit", "passed": "ld a,E_EXIST" in macro and macro.index("ld a,E_EXIST") < macro.index("zx48_p414_commit:")},
        {"name": "catalog-only-destination-protected", "passed": "call zx48_p405_is_bcat" in macro and "jp z,zx48_p414_perm" in macro},
        {"name": "commit-is-metadata-only", "passed": "zx48_free" not in macro and "zx48_alloc" not in macro and "zx48_zxpack" not in macro},
    ]


def _assemble(root: Path, run_command: Callable[..., Any], require_project_tool: Callable[[Path, str | Path], Path]):
    assembler = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    fixture = build / "p414-rename.asm"
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
    EMIT_USER_RANGE_VALIDATION_ROUTINE
    EMIT_P414_RENAME_ROUTINES
zx48_free:
    xor a
    ret
zx48_panic:
    scf
    ret
fake_process: defs 48,0
    SAVEBIN "p414-rename.bin",$C000,$-$C000
""",
        encoding="utf-8",
        newline="\n",
    )
    result = run_command(
        [assembler, "--nologo", "--lst=p414-rename.lst", "--sym=p414-rename.sym", "p414-rename.asm"],
        cwd=build,
        timeout_seconds=30.0,
    )
    require(not result.timed_out and result.exit_code == 0, f"P4.14 fixture assembly failed: {result.stderr or result.stdout}")
    binary = build / "p414-rename.bin"
    listing = build / "p414-rename.lst"
    require(binary.is_file() and 0 < binary.stat().st_size < 16384, "P4.14 fixture binary missing/oversize")
    return result, binary, listing


def _target(root: Path, s: dict[str, int], module: bytes) -> None:
    path_values = (
        "/tmp/foo", "/tmp/Foo", "/tmp/bar", "/tmp/tool", "/bin/tool",
        "/tmp/note", "/bin/note", "/bin/sh", "/bin/Sh",
    )
    addresses: dict[str, int] = {}
    payload = bytearray()
    cursor = DATA_BASE
    for path in path_values:
        addresses[path] = cursor
        encoded = path.encode("ascii") + b"\0"
        payload += encoded
        cursor += len(encoded)

    table = s["p405_object_table"]

    def patch(old: str, new: str, records: bytes):
        def apply(ram: bytearray) -> None:
            ram[MODULE_BASE - 0x4000:MODULE_BASE - 0x4000 + len(module)] = module
            ram[DATA_BASE - 0x4000:DATA_BASE - 0x4000 + len(payload)] = payload
            ram[table - 0x4000:table - 0x4000 + len(records)] = records
            ram[REQ_BASE - 0x4000:REQ_BASE - 0x4000 + 4] = _word(addresses[old]) + _word(addresses[new])
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
            raise Phase4RenameError(f"P4.14 target case failed: {label}: {exc}") from exc

    def call() -> bytes:
        return phase1._ld_hl(REQ_BASE) + phase1._call(s["zx48_p414_sys_rename"])

    foo = _record(b"foo", s["DIR_TMP"], s["OBJ_DAT"], 5, 5, PAYLOAD_BASE)
    code = call() + phase1._jp_c(FAIL_PC) + b"\x7C\xB5" + phase1._jp_nz(FAIL_PC) + mem_eq(table, foo)
    execute("exact-same-noop", code, patch("/tmp/foo", "/tmp/foo", foo))

    Foo = _record(b"Foo", s["DIR_TMP"], s["OBJ_DAT"], 5, 5, PAYLOAD_BASE)
    code = call() + phase1._jp_c(FAIL_PC) + b"\x7C\xB5" + phase1._jp_nz(FAIL_PC) + mem_eq(table, Foo)
    execute("case-only-rename", code, patch("/tmp/foo", "/tmp/Foo", foo))

    tool = _record(b"tool", s["DIR_TMP"], s["OBJ_BIN"], 7, 7, PAYLOAD_BASE)
    moved_tool = _record(b"tool", s["DIR_BIN"], s["OBJ_BIN"], 7, 7, PAYLOAD_BASE)
    code = call() + phase1._jp_c(FAIL_PC) + mem_eq(table, moved_tool)
    execute("compatible-cross-directory-move", code, patch("/tmp/tool", "/bin/tool", tool))

    note = _record(b"note", s["DIR_TMP"], s["OBJ_TXT"], 4, 4, PAYLOAD_BASE)
    code = call() + _jp_nc(FAIL_PC) + bytes((0xFE, s["E_PERM"])) + phase1._jp_nz(FAIL_PC) + mem_eq(table, note)
    execute("incompatible-cross-directory-rollback", code, patch("/tmp/note", "/bin/note", note))

    bar = _record(b"bar", s["DIR_TMP"], s["OBJ_DAT"], 3, 3, PAYLOAD_BASE + 0x20)
    pair = foo + bar
    code = call() + _jp_nc(FAIL_PC) + bytes((0xFE, s["E_EXIST"])) + phase1._jp_nz(FAIL_PC) + mem_eq(table, pair)
    execute("distinct-collision-rollback", code, patch("/tmp/foo", "/tmp/bar", pair))

    code = call() + _jp_nc(FAIL_PC) + bytes((0xFE, s["E_PERM"])) + phase1._jp_nz(FAIL_PC) + mem_eq(table, foo)
    execute("catalog-destination-protected", code, patch("/tmp/foo", "/bin/sh", foo))

    code = call() + _jp_nc(FAIL_PC) + bytes((0xFE, s["E_PERM"])) + phase1._jp_nz(FAIL_PC)
    execute("catalog-source-protected", code, patch("/bin/sh", "/bin/Sh", b""))

    def invalid_record_patch(ram: bytearray) -> None:
        patch("/tmp/foo", "/tmp/Foo", foo)(ram)
        ram[0x5AFE - 0x4000:0x5B00 - 0x4000] = _word(addresses["/tmp/foo"])
    code = phase1._ld_hl(0x5AFE) + phase1._call(s["zx48_p414_sys_rename"]) + _jp_nc(FAIL_PC)
    code += bytes((0xFE, s["E_INVAL"])) + phase1._jp_nz(FAIL_PC) + mem_eq(table, foo)
    execute("ren1-crosses-protected-range", code, invalid_record_patch)


def dispatch(
    root: Path,
    action: str,
    step: str,
    *,
    sha256_file: Callable[[Path], str],
    run_command: Callable[..., Any],
    require_project_tool: Callable[[Path, str | Path], Path],
):
    if step != "P4.14":
        raise DriverError(f"Phase-4 rename step is not registered: {step}")

    assertions = _source_contract(root)
    failed = [item["name"] for item in assertions if item.get("passed") is not True]
    require(not failed, f"static P4.14 contract failures: {failed}")

    kernel_result, kernel, _ = phase1._assemble_kernel(root, run_command, require_project_tool)
    fixture_result, binary, listing = _assemble(root, run_command, require_project_tool)
    commands = [kernel_result, fixture_result]
    names = (
        "zx48_p414_sys_rename", "p405_object_table", "OBJ_TXT", "OBJ_BIN", "OBJ_DAT",
        "DIR_BIN", "DIR_TMP", "E_INVAL", "E_PERM", "E_EXIST",
    )
    symbols = phase3_open_descriptions._symbols(listing.with_suffix(".sym"), names)

    if action == "test":
        _target(root, symbols, binary.read_bytes())
        assertions.extend([
            {"name": "exact-same-noop-runtime", "passed": True},
            {"name": "case-only-rename-runtime", "passed": True},
            {"name": "compatible-cross-directory-runtime", "passed": True},
            {"name": "incompatible-cross-directory-rollback-runtime", "passed": True},
            {"name": "distinct-collision-rollback-runtime", "passed": True},
            {"name": "catalog-source-destination-protected-runtime", "passed": True},
            {"name": "ren1-protected-range-rejected-runtime", "passed": True},
        ])

    hashes = {
        "v1/build/kernel.bin": sha256_file(kernel),
        "v1/build/p414-rename.bin": sha256_file(binary),
        "v1/src/kernel/objects.asm": sha256_file(root / "v1/src/kernel/objects.asm"),
        "v1/tools-host/test-driver/phase4_rename.py": sha256_file(root / "v1/tools-host/test-driver/phase4_rename.py"),
        "v1/tools-host/test-driver/run.py": sha256_file(root / "v1/tools-host/test-driver/run.py"),
        "v1/dist/certification/P4.13.test.json": sha256_file(root / "v1/dist/certification/P4.13.test.json"),
    }
    return commands, hashes, assertions
