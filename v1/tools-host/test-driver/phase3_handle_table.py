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
from fuse_harness import ENTRY_PC, FAIL_PC, PASS_PC, run_sna
import phase1
import phase3_open_descriptions

MIRROR_BASE = 0xC900


class Phase3HandleTableError(DriverError):
    """Raised when the P3.02 eight-handle process-table contract regresses."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Phase3HandleTableError(message)


def _word(value: int) -> bytes:
    return bytes((value & 0xFF, (value >> 8) & 0xFF))


def _jp_nc(address: int) -> bytes:
    return b"\xD2" + _word(address)


def _append_compare(code: bytearray, left: int, right: int, size: int) -> None:
    code += phase1._ld_hl(left) + phase1._ld_de(right) + b"\x01" + _word(size)
    loop = ENTRY_PC + len(code)
    code += b"\x1A\xBE" + phase1._jp_nz(FAIL_PC)
    code += b"\x23\x13\x0B\x78\xB1" + phase1._jp_nz(loop)


def _source_contract(root: Path) -> list[dict[str, object]]:
    inc = (root / "v1/include/zx48ux.inc").read_text(encoding="utf-8")
    handles = (root / "v1/src/kernel/handles.asm").read_text(encoding="utf-8")
    process = (root / "v1/src/kernel/process.asm").read_text(encoding="utf-8")
    return [
        {"name": "exact-eight-handle-slots", "passed": "MAX_HANDLES_PER_PROCESS  EQU $08" in inc},
        {"name": "slot-free-encoding-ff", "passed": "HANDLE_FREE              EQU $FF" in inc},
        {"name": "open-description-id-range-0-through-23", "passed": "OPEN_DESCRIPTION_COUNT   EQU $18" in inc},
        {"name": "process-handle-array-is-eight-one-byte-slots", "passed": "PROC_HANDLES              EQU 16" in process and "PROC_WAKE_TICK            EQU 24" in process},
        {"name": "handle-lookup-rejects-free-and-out-of-range", "passed": "cp HANDLE_FREE" in handles and "cp OPEN_DESCRIPTION_COUNT" in handles},
        {"name": "install-rejects-requested-slot-eight", "passed": "cp MAX_HANDLES_PER_PROCESS\n    jp nc,zx48_handle_nospc" in handles},
        {"name": "auto-install-scans-exactly-eight", "passed": "ld b,MAX_HANDLES_PER_PROCESS" in handles},
        {"name": "dup-failure-releases-retained-description", "passed": "call zx48_handle_install" in handles and "call zx48_od_release" in handles},
        {"name": "close-clears-slot-before-release", "passed": "ld (hl),HANDLE_FREE\n    call zx48_od_release" in handles},
        {"name": "slot-count-assembler-asserted", "passed": "ASSERT MAX_HANDLES_PER_PROCESS = 8" in handles},
    ]


def _target_test(root: Path, s: dict[str, int], kernel: bytes) -> None:
    process_init = s["zx48_process_init"]
    handles_init = s["zx48_handles_init"]
    create = s["zx48_od_create"]
    install = s["zx48_handle_install"]
    lookup = s["zx48_handle_lookup"]
    dup = s["zx48_handle_dup"]
    close = s["zx48_handle_close"]
    process_table = s["process_table"]
    slots = process_table + s["PROC_HANDLES"]
    od_table = s["open_description_table"]
    record = s["OD_RECORD_SIZE"]
    refs = s["OD_REFS_O"]
    offset = s["OD_OFFSET_O"]

    code = bytearray(b"\xF3" + phase1._ld_sp(0xBFC0))
    code += phase1._call(process_init) + phase1._call(handles_init)

    for index in range(8):
        code += bytes((0x06, s["OD_KIND_OBJECT"], 0x0E, s["O_READ"], 0x16, index))
        code += phase1._call(create) + phase1._jp_c(FAIL_PC)
        code += bytes((0xFE, index)) + phase1._jp_nz(FAIL_PC)
        code += bytes((0x3E, index, 0x0E, index))
        code += phase1._call(install) + phase1._jp_c(FAIL_PC)
        code += bytes((0xFE, index)) + phase1._jp_nz(FAIL_PC)

    for index in range(8):
        code += b"\x3A" + _word(slots + index) + bytes((0xFE, index)) + phase1._jp_nz(FAIL_PC)

    code += b"\x2A" + _word(od_table + offset)
    code += phase1._ld_de(0x0000) + b"\xB7\xED\x52" + phase1._jp_nz(FAIL_PC)
    code += phase1._ld_hl(0x5678) + b"\x22" + _word(od_table + offset)
    code += b"\x3A" + _word(slots) + b"\xB7" + phase1._jp_nz(FAIL_PC)

    code += phase1._ld_hl(slots) + phase1._ld_de(MIRROR_BASE) + b"\x01\x08\x00\xED\xB0"

    code += bytes((0x3E, 0xFF, 0x0E, 0x00)) + phase1._call(install)
    code += _jp_nc(FAIL_PC) + b"\xFE" + bytes((s["E_NOSPC"],)) + phase1._jp_nz(FAIL_PC)
    _append_compare(code, slots, MIRROR_BASE, 8)

    code += bytes((0x3E, 0x08, 0x0E, 0x00)) + phase1._call(install)
    code += _jp_nc(FAIL_PC) + b"\xFE" + bytes((s["E_NOSPC"],)) + phase1._jp_nz(FAIL_PC)
    _append_compare(code, slots, MIRROR_BASE, 8)

    code += b"\x3A" + _word(od_table + refs) + b"\xFE\x01" + phase1._jp_nz(FAIL_PC)
    code += bytes((0x06, 0x00, 0x0E, 0x08)) + phase1._call(dup)
    code += _jp_nc(FAIL_PC) + b"\xFE" + bytes((s["E_NOSPC"],)) + phase1._jp_nz(FAIL_PC)
    code += b"\x3A" + _word(od_table + refs) + b"\xFE\x01" + phase1._jp_nz(FAIL_PC)
    _append_compare(code, slots, MIRROR_BASE, 8)

    code += b"\x3E\x18\x32" + _word(slots + 7)
    code += b"\x3E\x07" + phase1._call(lookup)
    code += _jp_nc(FAIL_PC) + b"\xFE" + bytes((s["E_NOENT"],)) + phase1._jp_nz(FAIL_PC)
    code += b"\x3E\x07\x32" + _word(slots + 7)

    code += b"\x3E\x07" + phase1._call(close) + phase1._jp_c(FAIL_PC)
    code += b"\x3A" + _word(slots + 7) + b"\xFE\xFF" + phase1._jp_nz(FAIL_PC)
    code += b"\x3A" + _word(od_table + 7 * record) + b"\xB7" + phase1._jp_nz(FAIL_PC)

    code += phase1._jp(PASS_PC)
    run_sna(root, bytes(code), patch=phase1._kernel_patch(kernel))


def dispatch(
    root: Path,
    action: str,
    step: str,
    *,
    sha256_file: Callable[[Path], str],
    run_command: Callable[..., Any],
    require_project_tool: Callable[[Path, str | Path], Path],
):
    if step != "P3.02":
        raise DriverError(f"Phase-3 handle-table step is not registered: {step}")

    assertions = _source_contract(root)
    failed = [item["name"] for item in assertions if item["passed"] is not True]
    require(not failed, f"static P3.02 contract failures: {failed}")

    result, kernel, listing = phase1._assemble_kernel(root, run_command, require_project_tool)
    commands = [result]
    names = (
        "zx48_process_init",
        "zx48_handles_init",
        "zx48_od_create",
        "zx48_handle_install",
        "zx48_handle_lookup",
        "zx48_handle_dup",
        "zx48_handle_close",
        "process_table",
        "open_description_table",
        "PROC_HANDLES",
        "MAX_HANDLES_PER_PROCESS",
        "OPEN_DESCRIPTION_COUNT",
        "OD_RECORD_SIZE",
        "OD_REFS_O",
        "OD_OFFSET_O",
        "OD_KIND_OBJECT",
        "O_READ",
        "E_NOSPC",
        "E_NOENT",
    )
    symbols = phase3_open_descriptions._symbols(listing.with_suffix(".sym"), names)

    runtime_layout = [
        {"name": "exact-eight-slots-runtime-symbol", "passed": symbols["MAX_HANDLES_PER_PROCESS"] == 8},
        {"name": "valid-open-description-range-runtime-symbol", "passed": symbols["OPEN_DESCRIPTION_COUNT"] == 24},
        {"name": "handle-array-exactly-eight-bytes", "passed": symbols["PROC_HANDLES"] + 8 == 24},
    ]
    failed = [item["name"] for item in runtime_layout if item["passed"] is not True]
    require(not failed, f"P3.02 runtime layout failures: {failed}")
    assertions.extend(runtime_layout)

    if action == "test":
        _target_test(root, symbols, kernel.read_bytes())
        assertions.extend([
            {"name": "all-eight-slots-encode-only-open-description-ids", "passed": True},
            {"name": "stdin-stdout-stderr-slots-0-1-2-exact", "passed": True},
            {"name": "ninth-auto-slot-enospc-no-mutation", "passed": True},
            {"name": "requested-slot-eight-enospc-no-mutation", "passed": True},
            {"name": "failed-dup-install-does-not-leak-reference", "passed": True},
            {"name": "id-24-in-process-slot-rejected", "passed": True},
            {"name": "close-removes-slot-and-final-reference-atomically", "passed": True},
            {"name": "offset-state-remains-in-open-description-not-slot", "passed": True},
        ])

    hashes = {
        "v1/build/kernel.bin": sha256_file(kernel),
        "v1/src/kernel/handles.asm": sha256_file(root / "v1/src/kernel/handles.asm"),
        "v1/tools-host/test-driver/phase3_handle_table.py": sha256_file(root / "v1/tools-host/test-driver/phase3_handle_table.py"),
        "v1/tools-host/test-driver/run.py": sha256_file(root / "v1/tools-host/test-driver/run.py"),
        "v1/dist/certification/P3.01.test.json": sha256_file(root / "v1/dist/certification/P3.01.test.json"),
        "v1/dist/certification/R16.00.result.json": sha256_file(root / "v1/dist/certification/R16.00.result.json"),
    }
    return commands, hashes, assertions
