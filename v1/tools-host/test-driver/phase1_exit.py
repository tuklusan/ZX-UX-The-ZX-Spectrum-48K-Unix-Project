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
PROC_PARENT = 1
PROC_STATE = 2
PROC_EXIT_STATUS = 14
PROC_WAIT_CHILD = 7
PROC_ZOMBIE = 8
PROC_READY = 1
PROC_RUNNING = 2
HANDLE_FREE = 0xFF
E_INVAL = 1
PANIC_SCHEDULER = 3
VERIFY_PC = 0xB100


class Phase1ExitError(DriverError):
    """Raised when the P1.19 SYS_EXIT contract is violated."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Phase1ExitError(message)


def _word(value: int) -> bytes:
    return bytes((value & 0xFF, (value >> 8) & 0xFF))


def _call(address: int) -> bytes:
    return b"\xCD" + _word(address)


def _jp(address: int) -> bytes:
    return b"\xC3" + _word(address)


def _jp_c(address: int) -> bytes:
    return b"\xDA" + _word(address)


def _jp_nc(address: int) -> bytes:
    return b"\xD2" + _word(address)


def _jp_nz(address: int) -> bytes:
    return b"\xC2" + _word(address)


def _store_byte(address: int, value: int) -> bytes:
    return bytes((0x3E, value & 0xFF, 0x32)) + _word(address)


def _expect_byte(address: int, value: int) -> bytes:
    return b"\x3A" + _word(address) + bytes((0xFE, value & 0xFF)) + _jp_nz(FAIL_PC)


def _strip(text: str) -> str:
    return "\n".join(line.split(";", 1)[0].rstrip().lower() for line in text.splitlines())


def _block(text: str, start: str, end: str) -> str:
    lowered = text.lower()
    first = lowered.find(start.lower())
    last = lowered.find(end.lower(), first + len(start))
    require(0 <= first < last, f"missing source block {start}..{end}")
    return lowered[first:last]


def _source_contract(root: Path) -> list[dict[str, object]]:
    syscall = _strip((root / "v1/src/kernel/syscall.asm").read_text(encoding="utf-8"))
    process = _strip((root / "v1/src/kernel/process.asm").read_text(encoding="utf-8"))
    sys_exit = _block(syscall, "zx48_sys_exit:", "zx48_sys_yield:")
    exit_body = _block(process, "zx48_process_exit:", "zx48_process_exit_panic:")
    panic = _block(process, "zx48_process_exit_panic:", "zx48_process_restore_tty_owner:")
    return [
        {
            "name": "sys-exit-accepts-only-h-zero-and-l-status",
            "passed": all(token in sys_exit for token in ("ld hl,(syscall_arg_hl)", "ld a,h", "or a", "jp nz,zx48_sys_invalid", "ld a,l", "jp zx48_process_exit")),
        },
        {
            "name": "exit-becomes-zombie-closes-handles-wakes-parent-restores-tty-and-schedules",
            "passed": all(token in exit_body for token in ("ld (ix+proc_exit_status),a", "ld (ix+proc_state),proc_zombie", "call zx48_handles_close_all_current", "call zx48_process_wake_parent", "call zx48_process_restore_tty_owner", "jp zx48_schedule")),
        },
        {
            "name": "pid0-exit-is-scheduler-panic",
            "passed": "ld a,panic_scheduler" in panic and "jp zx48_panic" in panic,
        },
    ]


def _patch_schedule_return(kernel_bytes: bytes, schedule: int):
    patched = bytearray(kernel_bytes)
    offset = schedule - phase1.KERNEL_BASE
    require(0 <= offset < len(patched), "schedule label outside kernel")
    patched[offset] = 0xC9
    return phase1._kernel_patch(bytes(patched))


def _positive(root: Path, labels: dict[str, int], kernel_bytes: bytes) -> None:
    table = labels["process_table"]
    p1 = table + PROC_DESC_SIZE
    p2 = table + 2 * PROC_DESC_SIZE
    code = bytearray(b"\xF3" + phase1._ld_sp(phase1.USER_STACK))
    code += _call(labels["zx48_kernel_stack_init"])
    code += _call(labels["zx48_process_init"])
    code += _call(labels["zx48_process_prepare_pid1"])
    code += _store_byte(p1 + PROC_STATE, PROC_WAIT_CHILD)
    code += _store_byte(p2, 2)
    code += _store_byte(p2 + PROC_PARENT, 1)
    code += _store_byte(p2 + PROC_STATE, PROC_RUNNING)
    code += _store_byte(labels["current_pid"], 2)
    code += _store_byte(labels["tty_input_owner"], 2)
    code += b"\x3E\x5A" + _call(labels["zx48_process_exit"])
    code += _expect_byte(p2 + PROC_EXIT_STATUS, 0x5A)
    code += _expect_byte(p2 + PROC_STATE, PROC_ZOMBIE)
    code += _expect_byte(p1 + PROC_STATE, PROC_READY)
    code += _expect_byte(labels["tty_input_owner"], 1)
    code += _jp(PASS_PC)
    run_sna(root, bytes(code), patch=_patch_schedule_return(kernel_bytes, labels["zx48_schedule"]))


def _invalid_syscall_high_byte(root: Path, labels: dict[str, int], kernel_bytes: bytes) -> None:
    code = bytearray(b"\xF3" + phase1._ld_sp(phase1.USER_STACK))
    code += _call(labels["zx48_kernel_stack_init"])
    code += b"\x21\x34\x12\x3E\x01" + _call(0xE000)
    code += _jp_nc(FAIL_PC) + b"\xFE" + bytes((E_INVAL,)) + _jp_nz(FAIL_PC) + _jp(PASS_PC)
    run_sna(root, bytes(code), patch=phase1._kernel_patch(kernel_bytes))


def _pid0_panics(root: Path, labels: dict[str, int], kernel_bytes: bytes) -> None:
    patched = bytearray(kernel_bytes)
    panic_halt = labels["zx48_panic_halt"] - phase1.KERNEL_BASE
    require(0 <= panic_halt <= len(patched) - 3, "panic halt outside kernel")
    patched[panic_halt:panic_halt + 3] = _jp(VERIFY_PC)
    verifier = _expect_byte(labels["kernel_panic_code"], PANIC_SCHEDULER) + _jp(PASS_PC)
    code = bytearray(b"\xF3" + phase1._ld_sp(phase1.USER_STACK))
    code += _call(labels["zx48_kernel_stack_init"])
    code += _call(labels["zx48_process_init"])
    code += _store_byte(labels["current_pid"], 0)
    code += b"\x3E\x11" + _call(labels["zx48_process_exit"]) + _jp(FAIL_PC)
    run_sna(root, bytes(code), patch=phase1._kernel_patch(bytes(patched), (VERIFY_PC, verifier)))


def dispatch(
    root: Path,
    action: str,
    step: str,
    *,
    sha256_file: Callable[[Path], str],
    run_command: Callable[..., Any],
    require_project_tool: Callable[[Path, str | Path], Path],
):
    if step != "P1.19":
        raise Phase1ExitError(f"exit step is not registered: {step}")

    assertions = _source_contract(root)
    failed = [a["name"] for a in assertions if a["passed"] is not True]
    require(not failed, f"static P1.19 failures: {failed}")

    command, kernel, listing = phase1._assemble_kernel(root, run_command, require_project_tool)
    labels = phase1._labels(
        listing,
        (
            "zx48_kernel_stack_init",
            "zx48_process_init",
            "zx48_process_prepare_pid1",
            "zx48_process_exit",
            "zx48_schedule",
            "process_table",
            "current_pid",
            "tty_input_owner",
            "kernel_panic_code",
            "zx48_panic_halt",
        ),
    )
    kernel_bytes = kernel.read_bytes()

    if action == "test":
        _positive(root, labels, kernel_bytes)
        _invalid_syscall_high_byte(root, labels, kernel_bytes)
        _pid0_panics(root, labels, kernel_bytes)
        assertions.extend(
            [
                {"name": "exit-status-zombie-parent-wake-and-tty-owner-runtime", "passed": True},
                {"name": "exit-high-byte-invalid-is-rejected", "passed": True},
                {"name": "pid0-exit-panics-scheduler", "passed": True},
            ]
        )

    paths = (
        root / "v1/src/kernel/process.asm",
        root / "v1/src/kernel/syscall.asm",
        root / "v1/src/kernel/handles.asm",
        root / "v1/tools-host/test-driver/phase1_exit.py",
        kernel,
    )
    return [command], {str(path.relative_to(root)): sha256_file(path) for path in paths}, assertions
