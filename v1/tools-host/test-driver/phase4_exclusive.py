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


class Phase4ExclusiveError(DriverError):
    """Raised when the P4.06 open-description exclusivity contract regresses."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Phase4ExclusiveError(message)


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
    fixture = build / "p406-exclusive.asm"
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
    EMIT_P406_EXCLUSIVITY_ROUTINES
    EMIT_OBJECT_EXCLUSIVITY_ROUTINES
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
    SAVEBIN "p406-exclusive.bin",$C000,$-$C000
""",
        encoding="utf-8", newline="\n",
    )
    result = run_command(
        [assembler, "--nologo", "--lst=p406-exclusive.lst", "--sym=p406-exclusive.sym", "p406-exclusive.asm"],
        cwd=build,
        timeout_seconds=30.0,
    )
    require(not result.timed_out and result.exit_code == 0, f"P4.06 fixture assembly failed: {result.stderr or result.stdout}")
    binary = build / "p406-exclusive.bin"
    listing = build / "p406-exclusive.lst"
    require(binary.is_file() and 0 < binary.stat().st_size < 8192, "P4.06 fixture binary missing/oversize")
    return result, binary, listing


def _source_contract(root: Path) -> list[dict[str, object]]:
    handles = (root / "v1/src/kernel/handles.asm").read_text(encoding="utf-8")
    objects = (root / "v1/src/kernel/objects.asm").read_text(encoding="utf-8")
    process = (root / "v1/src/kernel/process.asm").read_text(encoding="utf-8")
    staged = handles.split("MACRO EMIT_P406_EXCLUSIVITY_ROUTINES", 1)[1].split("ENDM", 1)[0]
    guard = staged.split("zx48_od_object_open_guard:", 1)[1].split("; D=RAM-object identity.", 1)[0]
    live = staged.split("zx48_od_object_any_live:", 1)[1].split("; B=kind,C=access,D=identity", 1)[0]
    object_guard = objects.split("MACRO EMIT_OBJECT_EXCLUSIVITY_ROUTINES", 1)[1].split("ENDM", 1)[0]
    return [
        {"name": "writer-guard-scans-open-description-pool", "passed": "open_description_table" in guard and "OPEN_DESCRIPTION_COUNT" in guard and "PROC_HANDLES" not in guard},
        {"name": "writer-guard-distinguishes-write-capability", "passed": "and O_WRITE" in guard and "OD_ACCESS_O" in guard and "OD_ID_O" in guard},
        {"name": "staged-object-create-enforces-exclusivity", "passed": "zx48_p406_od_create:" in staged and "call zx48_od_object_open_guard" in staged and "cp OD_KIND_OBJECT" in staged},
        {"name": "no-open-reference-scan-is-od-pool-only", "passed": "open_description_table" in live and "OPEN_DESCRIPTION_COUNT" in live and "PROC_HANDLES" not in live},
        {"name": "representation-swap-guard-delegates-to-od-pool", "passed": "zx48_object_representation_swap_guard:" in object_guard and "jp zx48_od_object_any_live" in object_guard},
        {"name": "dup-retains-same-description", "passed": "zx48_handle_dup:" in handles and "call zx48_od_retain" in handles},
        {"name": "spawn-inheritance-retains-same-description", "passed": "Acquire one shared OD reference for each child std-handle slot." in process and "call zx48_od_retain" in process},
        {"name": "open-description-pool-remains-bounded-24", "passed": "ASSERT OPEN_DESCRIPTION_COUNT = 24" in handles},
    ]


def _target(root: Path, s: dict[str, int], module: bytes) -> None:
    table = s["open_description_table"]
    fake = s["fake_process"]

    def patch(ram: bytearray) -> None:
        off = MODULE_BASE - 0x4000
        ram[off:off + len(module)] = module

    def execute(label: str, code: bytes) -> None:
        body = bytes((0xF3,)) + phase1._ld_sp(0xBFC0) + code + phase1._jp(PASS_PC)
        try:
            run_sna(root, body, patch=patch)
        except DriverError as exc:
            raise Phase4ExclusiveError(f"P4.06 target case failed: {label}: {exc}") from exc

    def od_create(access: int, identity: int) -> bytes:
        return bytes((0x06, s["OD_KIND_OBJECT"], 0x0E, access & 0xFF, 0x16, identity & 0xFF)) + phase1._call(s["zx48_p406_od_create"])

    def a_eq(value: int) -> bytes:
        return bytes((0xFE, value & 0xFF)) + phase1._jp_nz(FAIL_PC)

    def byte_eq(address: int, value: int) -> bytes:
        return _ld_a_mem(address) + a_eq(value)

    read = s["O_READ"]
    write = s["O_WRITE"]
    identity = 5

    code = phase1._call(s["zx48_handles_init"])
    code += od_create(read, identity) + phase1._jp_c(FAIL_PC) + a_eq(0)
    code += od_create(read, identity) + phase1._jp_c(FAIL_PC) + a_eq(1)
    code += byte_eq(table + s["OD_KIND_O"], s["OD_KIND_OBJECT"])
    code += byte_eq(table + s["OD_ACCESS_O"], read)
    code += byte_eq(table + s["OD_ID_O"], identity)
    code += byte_eq(table + s["OD_COMPACT_SIZE"] + s["OD_ACCESS_O"], read)
    execute("independent-reader-reader-opens", code)

    code = phase1._call(s["zx48_handles_init"])
    code += od_create(read, identity) + phase1._jp_c(FAIL_PC)
    code += od_create(write, identity) + _jp_nc(FAIL_PC) + a_eq(s["E_BUSY"])
    code += byte_eq(table + s["OD_COMPACT_SIZE"] + s["OD_KIND_O"], 0)
    execute("writer-conflicts-existing-reader", code)

    code = phase1._call(s["zx48_handles_init"])
    code += od_create(write, identity) + phase1._jp_c(FAIL_PC)
    code += od_create(read, identity) + _jp_nc(FAIL_PC) + a_eq(s["E_BUSY"])
    execute("reader-conflicts-existing-writer", code)

    code = phase1._call(s["zx48_handles_init"])
    code += od_create(write, identity) + phase1._jp_c(FAIL_PC)
    code += od_create(write, identity) + _jp_nc(FAIL_PC) + a_eq(s["E_BUSY"])
    execute("writer-conflicts-existing-writer", code)

    code = phase1._call(s["zx48_handles_init"])
    code += od_create(write, identity) + phase1._jp_c(FAIL_PC) + a_eq(0)
    code += od_create(write, identity + 1) + phase1._jp_c(FAIL_PC) + a_eq(1)
    execute("writers-on-distinct-objects-independent", code)

    code = phase1._call(s["zx48_handles_init"])
    code += od_create(write | s["O_APPEND"], identity) + phase1._jp_c(FAIL_PC) + a_eq(0)
    code += bytes((0x0E, 0x00, 0x3E, s["HANDLE_FREE"])) + phase1._call(s["zx48_handle_install"])
    code += phase1._jp_c(FAIL_PC) + a_eq(0)
    code += bytes((0x3E, 0x00)) + phase1._call(s["zx48_handle_lookup"]) + phase1._jp_c(FAIL_PC)
    code += bytes((0xDD, 0x36, s["OD_OFFSET_O"], 0x34, 0xDD, 0x36, s["OD_OFFSET_O"] + 1, 0x12))
    code += bytes((0x06, 0x00, 0x0E, s["HANDLE_FREE"])) + phase1._call(s["zx48_handle_dup"])
    code += phase1._jp_c(FAIL_PC) + a_eq(1)
    code += byte_eq(fake + 16, 0) + byte_eq(fake + 17, 0)
    code += byte_eq(table + s["OD_REFS_O"], 2)
    code += bytes((0x3E, 0x01)) + phase1._call(s["zx48_handle_lookup"]) + phase1._jp_c(FAIL_PC)
    code += bytes((0xDD, 0x7E, s["OD_OFFSET_O"], 0xFE, 0x34)) + phase1._jp_nz(FAIL_PC)
    code += bytes((0xDD, 0x7E, s["OD_OFFSET_O"] + 1, 0xFE, 0x12)) + phase1._jp_nz(FAIL_PC)
    code += bytes((0xDD, 0x7E, s["OD_ACCESS_O"], 0xFE, write | s["O_APPEND"])) + phase1._jp_nz(FAIL_PC)
    execute("dup-same-writer-description-shares-state", code)

    code = phase1._call(s["zx48_handles_init"])
    code += od_create(write, identity) + phase1._jp_c(FAIL_PC)
    code += bytes((0x3E, 0x00)) + phase1._call(s["zx48_od_retain"]) + phase1._jp_c(FAIL_PC)
    code += byte_eq(table + s["OD_REFS_O"], 2)
    execute("inherited-reference-retains-same-writer-description", code)

    code = phase1._call(s["zx48_handles_init"])
    code += od_create(read, identity) + phase1._jp_c(FAIL_PC)
    code += bytes((0x3E, identity)) + phase1._call(s["zx48_object_representation_swap_guard"])
    code += _jp_nc(FAIL_PC) + a_eq(s["E_BUSY"])
    for slot in range(8):
        code += byte_eq(fake + 16 + slot, s["HANDLE_FREE"])
    execute("representation-swap-busy-from-od-pool-with-no-handles", code)

    code = phase1._call(s["zx48_handles_init"])
    code += bytes((0x3E, identity)) + phase1._call(s["zx48_object_no_open_references"]) + phase1._jp_c(FAIL_PC)
    execute("no-open-reference-success-on-empty-od-pool", code)


def dispatch(
    root: Path,
    action: str,
    step: str,
    *,
    sha256_file: Callable[[Path], str],
    run_command: Callable[..., Any],
    require_project_tool: Callable[[Path, str | Path], Path],
):
    if step != "P4.06":
        raise DriverError(f"Phase-4 exclusivity step is not registered: {step}")

    assertions = _source_contract(root)
    failed = [item["name"] for item in assertions if item.get("passed") is not True]
    require(not failed, f"static P4.06 contract failures: {failed}")

    kernel_result, kernel, _listing = phase1._assemble_kernel(root, run_command, require_project_tool)
    fixture_result, binary, listing = _assemble(root, run_command, require_project_tool)
    commands = [kernel_result, fixture_result]
    names = (
        "zx48_handles_init", "zx48_p406_od_create", "zx48_od_retain", "zx48_handle_install",
        "zx48_handle_lookup", "zx48_handle_dup", "zx48_object_representation_swap_guard",
        "zx48_object_no_open_references", "open_description_table", "fake_process",
        "OD_KIND_O", "OD_ACCESS_O", "OD_REFS_O", "OD_ID_O", "OD_OFFSET_O", "OD_COMPACT_SIZE",
        "OD_KIND_OBJECT", "OPEN_DESCRIPTION_COUNT", "HANDLE_FREE", "O_READ", "O_WRITE", "O_APPEND", "E_BUSY",
    )
    symbols = phase3_open_descriptions._symbols(listing.with_suffix(".sym"), names)
    require(symbols["OPEN_DESCRIPTION_COUNT"] == 24, "P4.06 open-description pool size changed")

    if action == "test":
        _target(root, symbols, binary.read_bytes())
        assertions.extend([
            {"name": "multiple-independent-readers-runtime", "passed": True},
            {"name": "distinct-writer-reader-conflict-matrix-runtime", "passed": True},
            {"name": "dup-inherit-same-description-shared-state-runtime", "passed": True},
            {"name": "representation-swap-guard-scans-od-pool-runtime", "passed": True},
        ])

    hashes = {
        "v1/build/kernel.bin": sha256_file(kernel),
        "v1/build/p406-exclusive.bin": sha256_file(binary),
        "v1/src/kernel/handles.asm": sha256_file(root / "v1/src/kernel/handles.asm"),
        "v1/src/kernel/objects.asm": sha256_file(root / "v1/src/kernel/objects.asm"),
        "v1/src/kernel/process.asm": sha256_file(root / "v1/src/kernel/process.asm"),
        "v1/tools-host/test-driver/phase4_exclusive.py": sha256_file(root / "v1/tools-host/test-driver/phase4_exclusive.py"),
        "v1/tools-host/test-driver/run.py": sha256_file(root / "v1/tools-host/test-driver/run.py"),
        "v1/dist/certification/P4.05.test.json": sha256_file(root / "v1/dist/certification/P4.05.test.json"),
    }
    return commands, hashes, assertions
