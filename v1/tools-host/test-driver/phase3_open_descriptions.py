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
import re
from typing import Any, Callable

from driver_core import DriverError
from fuse_harness import ENTRY_PC, FAIL_PC, PASS_PC, run_sna
import phase1

MIRROR_BASE = 0xC800


class Phase3OpenDescriptionError(DriverError):
    """Raised when the P3.01 open-description/budget contract regresses."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Phase3OpenDescriptionError(message)


def _word(value: int) -> bytes:
    return bytes((value & 0xFF, (value >> 8) & 0xFF))


def _jp_nc(address: int) -> bytes:
    return b"\xD2" + _word(address)


def _symbols(path: Path, names: tuple[str, ...]) -> dict[str, int]:
    text = path.read_text(encoding="utf-8", errors="replace")
    found: dict[str, int] = {}
    for name in names:
        pattern = re.compile(
            rf"^{re.escape(name)}:\s+equ\s+0x([0-9A-Fa-f]+)\s*$",
            re.IGNORECASE | re.MULTILINE,
        )
        match = pattern.search(text)
        require(match is not None, f"P3.01 symbol missing from assembler output: {name}")
        found[name] = int(match.group(1), 16)
    return found


def _source_contract(root: Path) -> list[dict[str, object]]:
    inc = (root / "v1/include/zx48ux.inc").read_text(encoding="utf-8")
    handles = (root / "v1/src/kernel/handles.asm").read_text(encoding="utf-8")
    process = (root / "v1/src/kernel/process.asm").read_text(encoding="utf-8")
    scheduler = (root / "v1/src/kernel/scheduler.asm").read_text(encoding="utf-8")
    return [
        {"name": "exact-24-open-description-pool", "passed": "OPEN_DESCRIPTION_COUNT   EQU $18" in inc},
        {"name": "eight-byte-record-within-twelve-byte-cap", "passed": "OD_RECORD_SIZE           EQU $08" in inc and "OD_DESC_SIZE             EQU $0C" in inc},
        {"name": "open-description-table-budget-288", "passed": "OPEN_DESCRIPTION_BUDGET EQU $0120" in inc},
        {"name": "process-table-budget-448", "passed": "PROCESS_TABLE_BUDGET     EQU $01C0" in inc},
        {"name": "combined-planning-budget-896", "passed": "SCHED_PROC_OD_BUDGET     EQU $0380" in inc},
        {"name": "record-owns-kind-access-ref-identity-offset-decoder", "passed": all(token in handles for token in (
            "OD_KIND_O                  EQU 0",
            "OD_ACCESS_O                EQU 1",
            "OD_REFS_O                  EQU 2",
            "OD_ID_O                    EQU 3",
            "OD_OFFSET_O                EQU 4",
            "OD_AUX_O                   EQU 6",
        ))},
        {"name": "dup-retains-existing-description", "passed": "call zx48_od_retain" in handles and "call zx48_handle_install" in handles},
        {"name": "create-zeroes-independent-offset-and-decoder", "passed": all(token in handles for token in (
            "ld (ix+OD_OFFSET_O),a",
            "ld (ix+OD_OFFSET_O+1),a",
            "ld (ix+OD_AUX_O),a",
            "ld (ix+OD_AUX_O+1),a",
        ))},
        {"name": "refcount-overflow-fails-closed", "passed": "cp $ff\n    jp z,zx48_handle_busy" in handles},
        {"name": "process-handle-slots-own-description-ids", "passed": "PROC_HANDLES              EQU 16" in process and "MAX_HANDLES_PER_PROCESS" in process},
        {"name": "process-descriptor-budget-asserted", "passed": "ASSERT PROC_DESC_SIZE <= PROCESS_DESC_MAX_SIZE" in process},
        {"name": "fast-reserve-bound-asserted", "passed": "ASSERT HANDLE_FAST_END <= FAST_RESERVE_END+1" in handles},
        {"name": "scheduler-fixed-state-present", "passed": all(token in scheduler for token in (
            "scheduler_current: db 0",
            "scheduler_candidate: db 0",
            "scheduler_sleep_lo: dw 0",
            "scheduler_sleep_hi: dw 0",
        ))},
    ]


def _append_compare(code: bytearray, left: int, right: int, size: int) -> None:
    code += phase1._ld_hl(left) + phase1._ld_de(right) + b"\x01" + _word(size)
    loop = ENTRY_PC + len(code)
    code += b"\x1A\xBE" + phase1._jp_nz(FAIL_PC)
    code += b"\x23\x13\x0B\x78\xB1" + phase1._jp_nz(loop)


def _allocation_exhaustion(root: Path, s: dict[str, int], kernel: bytes) -> None:
    init = s["zx48_handles_init"]
    create = s["zx48_od_create"]
    table = s["open_description_table"]
    count = s["OPEN_DESCRIPTION_COUNT"]
    record = s["OD_RECORD_SIZE"]
    table_bytes = count * record

    code = bytearray(b"\xF3" + phase1._ld_sp(0xBFC0) + phase1._call(init))
    for index in range(count):
        code += bytes((0x06, s["OD_KIND_OBJECT"], 0x0E, s["O_READ"], 0x16, index & 0xFF))
        code += phase1._call(create) + phase1._jp_c(FAIL_PC)
        code += bytes((0xFE, index & 0xFF)) + phase1._jp_nz(FAIL_PC)

    code += phase1._ld_hl(table) + phase1._ld_de(MIRROR_BASE) + b"\x01" + _word(table_bytes) + b"\xED\xB0"
    code += bytes((0x06, s["OD_KIND_OBJECT"], 0x0E, s["O_READ"], 0x16, 0x7F))
    code += phase1._call(create) + _jp_nc(FAIL_PC)
    code += bytes((0xFE, s["E_NOSPC"])) + phase1._jp_nz(FAIL_PC)
    _append_compare(code, table, MIRROR_BASE, table_bytes)
    code += phase1._jp(PASS_PC)
    run_sna(root, bytes(code), patch=phase1._kernel_patch(kernel))


def _sharing_and_negatives(root: Path, s: dict[str, int], kernel: bytes) -> None:
    init = s["zx48_handles_init"]
    create = s["zx48_od_create"]
    retain = s["zx48_od_retain"]
    table = s["open_description_table"]
    record = s["OD_RECORD_SIZE"]
    off = s["OD_OFFSET_O"]
    refs = s["OD_REFS_O"]
    kind = s["OD_KIND_O"]

    code = bytearray(b"\xF3" + phase1._ld_sp(0xBFC0) + phase1._call(init))
    code += bytes((0x06, s["OD_KIND_OBJECT"], 0x0E, s["O_READ"], 0x16, 3))
    code += phase1._call(create) + phase1._jp_c(FAIL_PC) + b"\xB7" + phase1._jp_nz(FAIL_PC)

    code += phase1._ld_hl(0x3456) + b"\x22" + _word(table + off)
    code += b"\xAF" + phase1._call(retain) + phase1._jp_c(FAIL_PC)
    code += b"\x3A" + _word(table + refs) + b"\xFE\x02" + phase1._jp_nz(FAIL_PC)

    code += bytes((0x06, s["OD_KIND_OBJECT"], 0x0E, s["O_READ"], 0x16, 3))
    code += phase1._call(create) + phase1._jp_c(FAIL_PC) + b"\xFE\x01" + phase1._jp_nz(FAIL_PC)
    code += b"\x2A" + _word(table + off) + phase1._ld_de(0x3456) + b"\xB7\xED\x52" + phase1._jp_nz(FAIL_PC)
    code += b"\x2A" + _word(table + record + off) + b"\x7C\xB5" + phase1._jp_nz(FAIL_PC)

    code += b"\x3E\xFF\x32" + _word(table + refs)
    code += b"\xAF" + phase1._call(retain) + _jp_nc(FAIL_PC)
    code += b"\xFE" + bytes((s["E_BUSY"],)) + phase1._jp_nz(FAIL_PC)
    code += b"\x3A" + _word(table + refs) + b"\xFE\xFF" + phase1._jp_nz(FAIL_PC)

    code += b"\xAF\x32" + _word(table + kind)
    code += b"\xAF" + phase1._call(retain) + _jp_nc(FAIL_PC)
    code += b"\xFE" + bytes((s["E_NOENT"],)) + phase1._jp_nz(FAIL_PC)
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
    if step != "P3.01":
        raise DriverError(f"Phase-3 open-description step is not registered: {step}")

    assertions = _source_contract(root)
    failed = [item["name"] for item in assertions if item["passed"] is not True]
    require(not failed, f"static P3.01 contract failures: {failed}")

    result, kernel, listing = phase1._assemble_kernel(root, run_command, require_project_tool)
    commands = [result]
    names = (
        "zx48_handles_init",
        "zx48_od_create",
        "zx48_od_retain",
        "open_description_table",
        "HANDLE_FAST_BASE",
        "HANDLE_FAST_END",
        "process_fixed_state_start",
        "process_fixed_state_end",
        "scheduler_current",
        "scheduler_sleep_hi",
        "OPEN_DESCRIPTION_COUNT",
        "OD_RECORD_SIZE",
        "OD_DESC_SIZE",
        "OD_KIND_O",
        "OD_REFS_O",
        "OD_OFFSET_O",
        "OD_KIND_OBJECT",
        "O_READ",
        "E_NOSPC",
        "E_BUSY",
        "E_NOENT",
        "PROC_DESC_SIZE",
        "MAX_PROCESSES",
        "PROCESS_DESC_MAX_SIZE",
        "PROCESS_TABLE_BUDGET",
        "OPEN_DESCRIPTION_BUDGET",
        "SCHED_PROC_OD_BUDGET",
    )
    symbols = _symbols(listing.with_suffix(".sym"), names)

    process_table_bytes = symbols["MAX_PROCESSES"] * symbols["PROC_DESC_SIZE"]
    open_table_bytes = symbols["OPEN_DESCRIPTION_COUNT"] * symbols["OD_RECORD_SIZE"]
    process_state_bytes = symbols["process_fixed_state_end"] - symbols["process_fixed_state_start"]
    scheduler_state_bytes = (symbols["scheduler_sleep_hi"] + 2) - symbols["scheduler_current"]
    handle_state_bytes = symbols["HANDLE_FAST_END"] - symbols["HANDLE_FAST_BASE"]
    combined_fixed = process_state_bytes + scheduler_state_bytes + handle_state_bytes

    budget_assertions = [
        {"name": "exact-24-records-runtime-symbol", "passed": symbols["OPEN_DESCRIPTION_COUNT"] == 24},
        {"name": "record-size-at-most-12", "passed": symbols["OD_RECORD_SIZE"] <= symbols["OD_DESC_SIZE"] == 12, "bytes": symbols["OD_RECORD_SIZE"]},
        {"name": "open-table-at-most-288", "passed": open_table_bytes <= symbols["OPEN_DESCRIPTION_BUDGET"] == 288, "bytes": open_table_bytes},
        {"name": "process-descriptor-at-most-56", "passed": symbols["PROC_DESC_SIZE"] <= symbols["PROCESS_DESC_MAX_SIZE"] == 56, "bytes": symbols["PROC_DESC_SIZE"]},
        {"name": "process-table-at-most-448", "passed": process_table_bytes <= symbols["PROCESS_TABLE_BUDGET"] == 448, "bytes": process_table_bytes},
        {"name": "combined-fixed-planning-at-most-896", "passed": combined_fixed <= symbols["SCHED_PROC_OD_BUDGET"] == 896, "bytes": combined_fixed},
    ]
    failed = [item["name"] for item in budget_assertions if item["passed"] is not True]
    require(not failed, f"P3.01 layout/budget failures: {failed}")
    assertions.extend(budget_assertions)

    if action == "test":
        kernel_bytes = kernel.read_bytes()
        _allocation_exhaustion(root, symbols, kernel_bytes)
        _sharing_and_negatives(root, symbols, kernel_bytes)
        assertions.extend([
            {"name": "24-allocate-25th-enospc-complete-rollback", "passed": True},
            {"name": "independent-opens-have-independent-offset-state", "passed": True},
            {"name": "retained-reference-shares-offset-and-refcount", "passed": True},
            {"name": "refcount-overflow-negative", "passed": True},
            {"name": "corrupt-free-record-retain-negative", "passed": True},
        ])

    hashes = {
        "v1/build/kernel.bin": sha256_file(kernel),
        "v1/include/zx48ux.inc": sha256_file(root / "v1/include/zx48ux.inc"),
        "v1/src/kernel/handles.asm": sha256_file(root / "v1/src/kernel/handles.asm"),
        "v1/src/kernel/process.asm": sha256_file(root / "v1/src/kernel/process.asm"),
        "v1/src/kernel/scheduler.asm": sha256_file(root / "v1/src/kernel/scheduler.asm"),
        "v1/tools-host/test-driver/phase3_open_descriptions.py": sha256_file(root / "v1/tools-host/test-driver/phase3_open_descriptions.py"),
        "v1/tools-host/test-driver/run.py": sha256_file(root / "v1/tools-host/test-driver/run.py"),
        "v1/dist/certification/R16.00.result.json": sha256_file(root / "v1/dist/certification/R16.00.result.json"),
    }
    return commands, hashes, assertions
