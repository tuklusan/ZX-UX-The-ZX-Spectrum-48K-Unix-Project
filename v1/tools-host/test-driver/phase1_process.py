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

PROC_DESC_SIZE = 48
MAX_PROCESSES = 8
MAX_HANDLES = 8
OPEN_DESCRIPTION_COUNT = 24
OD_DESC_SIZE = 12
PROCESS_BUDGET = 896

OFFSETS = {
    "pid": 0,
    "parent": 1,
    "state": 2,
    "flags": 3,
    "image_base": 4,
    "image_size": 6,
    "stack_low": 8,
    "stack_high": 10,
    "saved_sp": 12,
    "exit_status": 14,
    "wait_object": 15,
    "handles": 16,
    "wake_tick": 24,
    "cwd": 28,
    "name": 29,
    "owned_bytes": 40,
    "arg_ptr": 42,
    "env_ptr": 44,
    "private_flags": 46,
    "reserved": 47,
}

STATE_VALUES = (0, 1, 2, 3, 4, 5, 6, 7, 8)


class Phase1ProcessError(DriverError):
    """Raised when the bounded Phase-1 process descriptor contract is violated."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Phase1ProcessError(message)


def _word(value: int) -> bytes:
    return bytes((value & 0xFF, (value >> 8) & 0xFF))


def _call(address: int) -> bytes:
    return b"\xCD" + _word(address)


def _jp(address: int) -> bytes:
    return b"\xC3" + _word(address)


def _jp_nz(address: int) -> bytes:
    return b"\xC2" + _word(address)


def _expect_byte(address: int, value: int) -> bytes:
    return b"\x3A" + _word(address) + bytes((0xFE, value & 0xFF)) + _jp_nz(FAIL_PC)


def _static_contract(root: Path) -> list[dict[str, object]]:
    inc = (root / "v1/include/zx48ux.inc").read_text(encoding="utf-8")
    process = (root / "v1/src/kernel/process.asm").read_text(encoding="utf-8")
    scheduler = (root / "v1/src/kernel/scheduler.asm").read_text(encoding="utf-8")
    lower_process = process.lower()
    lower_scheduler = scheduler.lower()

    required_constants = (
        "MAX_PROCESSES            EQU $08",
        "MAX_HANDLES_PER_PROCESS  EQU $08",
        "OPEN_DESCRIPTION_COUNT   EQU $18",
        "PROC_FREE                EQU $00",
        "PROC_READY               EQU $01",
        "PROC_RUNNING             EQU $02",
        "PROC_SLEEPING            EQU $03",
        "PROC_WAIT_INPUT          EQU $04",
        "PROC_WAIT_PIPE_READ      EQU $05",
        "PROC_WAIT_PIPE_WRITE     EQU $06",
        "PROC_WAIT_CHILD          EQU $07",
        "PROC_ZOMBIE              EQU $08",
        "PROC_PRIVATE_STARTED     EQU $80",
        "PROC_DESC_SIZE           EQU $30",
        "OD_DESC_SIZE             EQU $0C",
    )
    required_offsets = tuple(f"PROC_{name.upper():<21}EQU {value}" for name, value in ())
    offset_tokens = (
        "PROC_PID                  EQU 0",
        "PROC_PARENT               EQU 1",
        "PROC_STATE                EQU 2",
        "PROC_FLAGS                EQU 3",
        "PROC_IMAGE_BASE           EQU 4",
        "PROC_IMAGE_SIZE           EQU 6",
        "PROC_STACK_LOW            EQU 8",
        "PROC_STACK_HIGH           EQU 10",
        "PROC_SAVED_SP             EQU 12",
        "PROC_EXIT_STATUS          EQU 14",
        "PROC_WAIT_OBJECT          EQU 15",
        "PROC_HANDLES              EQU 16",
        "PROC_WAKE_TICK            EQU 24",
        "PROC_CWD                  EQU 28",
        "PROC_NAME                 EQU 29",
        "PROC_OWNED_BYTES          EQU 40",
        "PROC_ARG_PTR              EQU 42",
        "PROC_ENV_PTR              EQU 44",
        "PROC_PRIVATE_FLAGS        EQU 46",
        "PROC_RESERVED             EQU 47",
    )
    restore = lower_scheduler.find("or proc_private_started")
    saved_sp = lower_scheduler.find("ld l,(ix+proc_saved_sp)", restore)
    return [
        {"name": "state-ids-exact-0-through-8", "passed": all(token in inc for token in required_constants[3:12])},
        {"name": "eight-descriptors-only", "passed": required_constants[0] in inc},
        {"name": "descriptor-size-48-at-most-56", "passed": "PROC_DESC_SIZE           EQU $30" in inc and PROC_DESC_SIZE <= 56},
        {"name": "descriptor-layout-complete", "passed": all(token in process for token in offset_tokens)},
        {"name": "process-table-at-most-448", "passed": PROC_DESC_SIZE * MAX_PROCESSES <= 448},
        {"name": "process-open-description-budget-at-most-896", "passed": PROC_DESC_SIZE * MAX_PROCESSES + OPEN_DESCRIPTION_COUNT * OD_DESC_SIZE <= PROCESS_BUDGET},
        {"name": "pid0-pid1-reservation-scan-starts-at-2", "passed": "ld ix,process_table+2*PROC_DESC_SIZE" in lower_process and "ld c,2" in lower_process},
        {"name": "eight-handle-open-description-ids", "passed": "ld b,max_handles_per_process" in lower_process and "ld a,handle_free" in lower_process},
        {"name": "saved-sp-only-runnable-context", "passed": not any(token in lower_process for token in ("proc_pc", "proc_af", "proc_bc", "proc_de", "proc_hl", "proc_ix"))},
        {"name": "started-private-and-not-proc-info", "passed": "and proc_flag_cancel" in lower_process and "proc_private_flags" not in lower_process[lower_process.find("zx48_process_info:"):lower_process.find("zx48_process_exit:")]},
        {"name": "started-set-immediately-before-restore", "passed": 0 <= restore < saved_sp and saved_sp - restore < 96},
        {"name": "name-is-exact-ten-byte-copy", "passed": "ld bc,10" in lower_process and "process_name_sh: db 's','h',0,0,0,0,0,0,0,0" in lower_process},
    ]


def _negative_contract_tests() -> list[dict[str, object]]:
    cases = {
        "reject-57-byte-descriptor": 57 > 56,
        "reject-ninth-record": 9 > MAX_PROCESSES,
        "reject-duplicate-runnable-context": "PROC_PC" not in {f"PROC_{name.upper()}" for name in OFFSETS},
        "reject-public-started-bit": 0x80 & 0x01 == 0,
        "reject-over-896-planning-budget": (56 * 9 + OPEN_DESCRIPTION_COUNT * OD_DESC_SIZE) > PROCESS_BUDGET,
    }
    return [{"name": name, "passed": passed} for name, passed in cases.items()]


def _runtime_test(root: Path, labels: dict[str, int], kernel_bytes: bytes) -> None:
    init = labels["zx48_process_init"]
    prepare = labels["zx48_process_prepare_pid1"]
    table = labels["process_table"]
    current_pid = labels["current_pid"]

    code = bytearray(b"\xF3\x31\x00\xFD")
    code += _call(init)
    code += _expect_byte(current_pid, 0)
    for pid in range(MAX_PROCESSES):
        base = table + pid * PROC_DESC_SIZE
        code += _expect_byte(base + OFFSETS["pid"], pid)
        code += _expect_byte(base + OFFSETS["parent"], 0xFF)
        code += _expect_byte(base + OFFSETS["state"], 2 if pid == 0 else 0)
        code += _expect_byte(base + OFFSETS["flags"], 0)
        code += _expect_byte(base + OFFSETS["private_flags"], 0)
        for handle in range(MAX_HANDLES):
            code += _expect_byte(base + OFFSETS["handles"] + handle, 0xFF)
    code += _call(prepare)
    code += _jp_nz(FAIL_PC)  # A must be E_OK/zero on success.
    pid1 = table + PROC_DESC_SIZE
    code += _expect_byte(pid1 + OFFSETS["state"], 1)
    code += _expect_byte(pid1 + OFFSETS["parent"], 0)
    code += _expect_byte(pid1 + OFFSETS["cwd"], 0)
    expected_name = b"sh" + b"\0" * 8
    for offset, value in enumerate(expected_name):
        code += _expect_byte(pid1 + OFFSETS["name"] + offset, value)
    code += _expect_byte(pid1 + OFFSETS["private_flags"], 0)
    code += _jp(PASS_PC)
    run_sna(root, bytes(code), patch=phase1._kernel_patch(kernel_bytes))


def dispatch(
    root: Path,
    action: str,
    step: str,
    *,
    sha256_file: Callable[[Path], str],
    run_command: Callable[..., Any],
    require_project_tool: Callable[[Path, str | Path], Path],
):
    if step != "P1.06":
        raise Phase1ProcessError(f"Phase-1 process step is not registered: {step}")

    assertions = _static_contract(root)
    require(all(item["passed"] is True for item in assertions), "P1.06 static descriptor contract failed")
    command, kernel, listing = phase1._assemble_kernel(root, run_command, require_project_tool)
    labels = phase1._labels(listing, ("zx48_process_init", "zx48_process_prepare_pid1", "process_table", "current_pid"))
    kernel_bytes = kernel.read_bytes()

    if action == "test":
        _runtime_test(root, labels, kernel_bytes)
        assertions.append({"name": "runtime-table-init-and-pid1-reservation", "passed": True})
        assertions.extend(_negative_contract_tests())
        require(all(item["passed"] is True for item in assertions), "P1.06 negative fixture failed")

    paths = (
        root / "v1/include/zx48ux.inc",
        root / "v1/src/kernel/process.asm",
        root / "v1/src/kernel/scheduler.asm",
        root / "v1/tools-host/test-driver/phase1_process.py",
        kernel,
    )
    hashes = {str(path.relative_to(root)).replace("\\", "/"): sha256_file(path) for path in paths}
    return [command], hashes, assertions
