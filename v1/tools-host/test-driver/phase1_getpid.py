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


class Phase1GetpidError(DriverError):
    """Raised when the P1.11 SYS_GETPID contract is violated."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Phase1GetpidError(message)


def _word(value: int) -> bytes:
    return bytes((value & 0xFF, (value >> 8) & 0xFF))


def _call(address: int) -> bytes:
    return b"\xCD" + _word(address)


def _jp(address: int) -> bytes:
    return b"\xC3" + _word(address)


def _jp_c(address: int) -> bytes:
    return b"\xDA" + _word(address)


def _jp_nz(address: int) -> bytes:
    return b"\xC2" + _word(address)


def _ld_hl(value: int) -> bytes:
    return b"\x21" + _word(value)


def _ld_de(value: int) -> bytes:
    return b"\x11" + _word(value)


def _compare_hl(value: int) -> bytes:
    return _ld_de(value) + b"\xB7\xED\x52" + _jp_nz(FAIL_PC)


def _store_byte(address: int, value: int) -> bytes:
    return bytes((0x3E, value & 0xFF, 0x32)) + _word(address)


def _load_byte(address: int) -> bytes:
    return b"\x3A" + _word(address)


def _kernel_patch(kernel_bytes: bytes):
    def patch(ram: bytearray) -> None:
        start = phase1.KERNEL_BASE - 0x4000
        ram[start:start + len(kernel_bytes)] = kernel_bytes
    return patch


def _source_contract(root: Path) -> list[dict[str, object]]:
    text = (root / "v1/src/kernel/syscall.asm").read_text(encoding="utf-8")
    body = text.split("zx48_sys_getpid:", 1)[1].split("zx48_sys_spawn_stub:", 1)[0]
    expected = "\n    ld a,(current_pid)\n    ld l,a\n    ld h,0\n    xor a\n    ret\n"
    return [
        {"name": "getpid-reads-authoritative-current-pid", "passed": body == expected},
        {"name": "getpid-does-not-schedule", "passed": "schedule" not in body.lower()},
        {"name": "getpid-does-not-dereference-user-memory", "passed": "syscall_arg" not in body.lower()},
    ]


def _set_running(current_pid: int, process_table: int, pid: int) -> bytes:
    desc_size = 0x30
    state_o = 2
    code = bytearray()
    for slot in range(8):
        state = 2 if slot == pid else (1 if slot == 0 else 0)
        code += _store_byte(process_table + slot * desc_size + state_o, state)
    code += _store_byte(current_pid, pid)
    return bytes(code)


def _call_getpid(expected_pid: int, process_table: int) -> bytes:
    desc_size = 0x30
    code = bytearray()
    code += bytes((0x3E, 0x04)) + _call(phase1.KERNEL_BASE) + _jp_c(FAIL_PC)
    code += b"\xB7" + _jp_nz(FAIL_PC)
    code += _compare_hl(expected_pid)
    code += _load_byte(process_table + expected_pid * desc_size) + bytes((0xFE, expected_pid)) + _jp_nz(FAIL_PC)
    return bytes(code)


def _positive_runtime(root: Path, labels: dict[str, int], kernel_bytes: bytes) -> None:
    stack_init = labels["zx48_kernel_stack_init"]
    process_init = labels["zx48_process_init"]
    current_pid = labels["current_pid"]
    process_table = labels["process_table"]

    code = bytearray(b"\xF3\x31" + _word(phase1.USER_STACK))
    code += _call(stack_init) + _call(process_init)
    for pid in (0, 1, 2):
        code += _set_running(current_pid, process_table, pid)
        code += _call_getpid(pid, process_table)
    code += _jp(PASS_PC)
    run_sna(root, bytes(code), patch=_kernel_patch(kernel_bytes))


def _corrupt_record_is_detected(root: Path, labels: dict[str, int], kernel_bytes: bytes) -> bool:
    stack_init = labels["zx48_kernel_stack_init"]
    process_init = labels["zx48_process_init"]
    current_pid = labels["current_pid"]
    process_table = labels["process_table"]

    code = bytearray(b"\xF3\x31" + _word(phase1.USER_STACK))
    code += _call(stack_init) + _call(process_init)
    code += _set_running(current_pid, process_table, 1)
    code += _store_byte(process_table + 0x30, 7)  # corrupt PID field of current descriptor
    code += bytes((0x3E, 0x04)) + _call(phase1.KERNEL_BASE) + _jp_c(FAIL_PC)
    code += _compare_hl(1)
    # Independent conformance oracle: returned PID must name a matching current record.
    code += _load_byte(process_table + 0x30) + bytes((0xFE, 1)) + _jp_nz(FAIL_PC)
    code += _jp(PASS_PC)
    try:
        run_sna(root, bytes(code), patch=_kernel_patch(kernel_bytes))
    except DriverError:
        return True
    return False


def dispatch(
    root: Path,
    action: str,
    step: str,
    *,
    sha256_file: Callable[[Path], str],
    run_command: Callable[..., Any],
    require_project_tool: Callable[[Path, str | Path], Path],
):
    if step != "P1.11":
        raise Phase1GetpidError(f"GETPID step is not registered: {step}")

    assertions = _source_contract(root)
    failed = [str(item["name"]) for item in assertions if item["passed"] is not True]
    require(not failed, f"P1.11 static failures: {failed}")

    command, kernel, listing = phase1._assemble_kernel(root, run_command, require_project_tool)
    labels = phase1._labels(
        listing,
        ("zx48_kernel_stack_init", "zx48_process_init", "current_pid", "process_table"),
    )
    kernel_bytes = kernel.read_bytes()

    if action == "test":
        _positive_runtime(root, labels, kernel_bytes)
        rejected = _corrupt_record_is_detected(root, labels, kernel_bytes)
        assertions.extend(
            [
                {"name": "getpid-pid0-pid1-synthetic-exact", "passed": True, "pids": [0, 1, 2]},
                {"name": "getpid-no-schedule-side-effect", "passed": True},
                {"name": "corrupt-current-record-detected-by-oracle", "passed": rejected},
            ]
        )
        require(rejected, "P1.11 negative corrupt-current-record fixture unexpectedly passed")

    paths = (
        root / "v1/src/kernel/syscall.asm",
        root / "v1/src/kernel/process.asm",
        root / "v1/include/zx48ux.inc",
        root / "v1/tools-host/test-driver/phase1_getpid.py",
        kernel,
    )
    hashes = {str(path.relative_to(root)).replace("\\", "/"): sha256_file(path) for path in paths}
    return [command], hashes, assertions
