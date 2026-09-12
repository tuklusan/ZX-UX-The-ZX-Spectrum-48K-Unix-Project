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
PROC_STATE = 2
PROC_SAVED_SP = 12
PROC_WAKE_TICK = 24
PROC_FREE = 0
PROC_READY = 1
PROC_RUNNING = 2
PROC_SLEEPING = 3
PROC_ZOMBIE = 6
SYS_YIELD = 0x02

TASK1_PC = 0xA000
TASK2_PC = 0xA200
TRACE = 0xA600
STACK1 = 0xA800
STACK2 = 0xAC00
VERIFY_PC = 0xAE00
MAGIC1_IX = 0x8123
MAGIC1_BC = 0x4567
MAGIC2_IX = 0x8234
MAGIC2_BC = 0x5678
MAGIC3_IX = 0x8345
MAGIC3_BC = 0x6789


class Phase1YieldError(DriverError):
    """Raised when the P1.12 cooperative scheduler contract is violated."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Phase1YieldError(message)


def _word(value: int) -> bytes:
    return bytes((value & 0xFF, (value >> 8) & 0xFF))


def _call(address: int) -> bytes:
    return b"\xCD" + _word(address)


def _jp(address: int) -> bytes:
    return b"\xC3" + _word(address)


def _jp_nz(address: int) -> bytes:
    return b"\xC2" + _word(address)


def _store_byte(address: int, value: int) -> bytes:
    return bytes((0x3E, value & 0xFF, 0x32)) + _word(address)


def _store_word(address: int, value: int) -> bytes:
    return b"\x21" + _word(value) + b"\x22" + _word(address)


def _expect_byte(address: int, value: int) -> bytes:
    return b"\x3A" + _word(address) + bytes((0xFE, value & 0xFF)) + _jp_nz(FAIL_PC)


def _expect_ix(value: int) -> bytes:
    return b"\xDD\xE5\xE1\x11" + _word(value) + b"\xB7\xED\x52" + _jp_nz(FAIL_PC)


def _expect_bc(value: int) -> bytes:
    return b"\xC5\xE1\x11" + _word(value) + b"\xB7\xED\x52" + _jp_nz(FAIL_PC)


def _set_ix(value: int) -> bytes:
    return b"\xDD\x21" + _word(value)


def _set_bc(value: int) -> bytes:
    return b"\x01" + _word(value)


def _yield() -> bytes:
    return bytes((0x3E, SYS_YIELD)) + _call(phase1.KERNEL_BASE)


def _frame(pc: int, ix: int, bc: int) -> bytes:
    return b"".join(_word(value) for value in (ix, 0, 0, bc, 0, pc))


def _ordered(text: str, tokens: tuple[str, ...]) -> bool:
    positions = [text.find(token) for token in tokens]
    return all(position >= 0 for position in positions) and positions == sorted(positions)


def _source_contract(root: Path) -> list[dict[str, object]]:
    scheduler = (root / "v1/src/kernel/scheduler.asm").read_text(encoding="utf-8").lower()
    syscall = (root / "v1/src/kernel/syscall.asm").read_text(encoding="utf-8").lower()
    interrupt = (root / "v1/src/kernel/interrupt.asm").read_text(encoding="utf-8").lower()
    cycle = (
        "ld a,(current_pid)",
        "ld (scheduler_current),a",
        "ld hl,(syscall_frame_sp)",
        "ld (ix+proc_saved_sp),l",
        "cp proc_running",
        "ld (ix+proc_state),proc_ready",
        "ld a,(scheduler_current)",
        "inc a",
        "and 7",
        "cp proc_sleeping",
        "call z,zx48_scheduler_maybe_wake",
        "cp proc_ready",
        "ld (current_pid),a",
        "ld (ix+proc_state),proc_running",
        "ld sp,hl",
        "pop ix",
        "pop hl",
        "pop de",
        "pop bc",
        "pop af",
        "ret",
    )
    return [
        {"name": "yield-has-no-argument-path", "passed": "zx48_sys_yield:\n    jp zx48_schedule_finish_syscall" in syscall},
        {"name": "round-robin-cycle-is-ordered", "passed": _ordered(scheduler, cycle)},
        {"name": "scan-begins-after-current-pid", "passed": "ld a,(scheduler_current)\n    inc a\n    and 7" in scheduler},
        {"name": "expired-sleeper-is-woken-in-scan", "passed": "cp proc_sleeping\n    call z,zx48_scheduler_maybe_wake" in scheduler},
        {"name": "pid0-is-explicit-fallback", "passed": "ld (scheduler_candidate),a\n    call zx48_process_ptr\n    jr zx48_schedule_restore" in scheduler},
        {"name": "no-priority-scheduler-state", "passed": "priority" not in scheduler},
        {"name": "interrupt-never-context-switches", "passed": "zx48_schedule" not in interrupt and "context-switch" not in interrupt},
    ]


def _multitask_runtime(root: Path, labels: dict[str, int], kernel_bytes: bytes) -> None:
    stack_init = labels["zx48_kernel_stack_init"]
    process_init = labels["zx48_process_init"]
    process_table = labels["process_table"]
    current_pid = labels["current_pid"]
    scheduler_candidate = labels["scheduler_candidate"]
    schedule_restore = labels["zx48_schedule_restore"]

    pid0 = process_table
    pid1 = process_table + PROC_DESC_SIZE
    pid2 = process_table + 2 * PROC_DESC_SIZE

    task1 = bytearray()
    task1 += _expect_byte(current_pid, 1)
    task1 += _expect_byte(pid1 + PROC_STATE, PROC_RUNNING)
    task1 += _expect_byte(pid2 + PROC_STATE, PROC_SLEEPING)
    task1 += _expect_byte(TRACE, 0) + _store_byte(TRACE, 1)
    task1 += _set_ix(MAGIC1_IX) + _set_bc(MAGIC1_BC) + _yield()
    task1 += _expect_ix(MAGIC1_IX) + _expect_bc(MAGIC1_BC)
    task1 += _expect_byte(current_pid, 1)
    task1 += _expect_byte(pid1 + PROC_STATE, PROC_RUNNING)
    task1 += _expect_byte(pid2 + PROC_STATE, PROC_READY)
    task1 += _expect_byte(TRACE, 2) + _store_byte(TRACE, 3)
    task1 += _set_ix(MAGIC1_IX) + _set_bc(MAGIC1_BC) + _yield()
    task1 += _jp(FAIL_PC)

    task2 = bytearray()
    task2 += _expect_byte(current_pid, 2)
    task2 += _expect_byte(pid1 + PROC_STATE, PROC_READY)
    task2 += _expect_byte(pid2 + PROC_STATE, PROC_RUNNING)
    task2 += _expect_byte(TRACE, 1) + _store_byte(TRACE, 2)
    task2 += _set_ix(MAGIC2_IX) + _set_bc(MAGIC2_BC) + _yield()
    task2 += _expect_ix(MAGIC2_IX) + _expect_bc(MAGIC2_BC)
    task2 += _expect_byte(current_pid, 2)
    task2 += _expect_byte(pid1 + PROC_STATE, PROC_READY)
    task2 += _expect_byte(pid2 + PROC_STATE, PROC_RUNNING)
    task2 += _expect_byte(TRACE, 3) + _store_byte(TRACE, 4)
    task2 += _store_byte(pid1 + PROC_STATE, PROC_FREE)
    task2 += _set_ix(MAGIC3_IX) + _set_bc(MAGIC3_BC) + _yield()
    task2 += _expect_ix(MAGIC3_IX) + _expect_bc(MAGIC3_BC)
    task2 += _expect_byte(current_pid, 2)
    task2 += _expect_byte(pid1 + PROC_STATE, PROC_FREE)
    task2 += _expect_byte(pid2 + PROC_STATE, PROC_RUNNING)
    task2 += _expect_byte(TRACE, 4) + _store_byte(TRACE, 5)
    task2 += _jp(PASS_PC)

    code = bytearray(b"\xF3\x31" + _word(phase1.KSTACK_TOP))
    code += _call(stack_init) + _call(process_init)
    code += _store_byte(pid0 + PROC_STATE, PROC_READY)
    code += _store_byte(pid1 + PROC_STATE, PROC_READY)
    code += _store_word(pid1 + PROC_SAVED_SP, STACK1)
    code += _store_byte(pid2 + PROC_STATE, PROC_SLEEPING)
    code += _store_word(pid2 + PROC_SAVED_SP, STACK2)
    code += _store_word(pid2 + PROC_WAKE_TICK, 0)
    code += _store_word(pid2 + PROC_WAKE_TICK + 2, 0)
    code += _store_byte(TRACE, 0)
    code += _store_byte(scheduler_candidate, 1)
    code += _set_ix(pid1)
    code += _jp(schedule_restore)

    def patch(ram: bytearray) -> None:
        start = phase1.KERNEL_BASE - 0x4000
        ram[start:start + len(kernel_bytes)] = kernel_bytes
        ram[TASK1_PC - 0x4000:TASK1_PC - 0x4000 + len(task1)] = task1
        ram[TASK2_PC - 0x4000:TASK2_PC - 0x4000 + len(task2)] = task2
        ram[STACK1 - 0x4000:STACK1 - 0x4000 + 12] = _frame(TASK1_PC, MAGIC1_IX, MAGIC1_BC)
        ram[STACK2 - 0x4000:STACK2 - 0x4000 + 12] = _frame(TASK2_PC, MAGIC2_IX, MAGIC2_BC)

    run_sna(root, bytes(code), patch=patch)


def _pid0_fallback_runtime(root: Path, labels: dict[str, int], kernel_bytes: bytes) -> None:
    stack_init = labels["zx48_kernel_stack_init"]
    process_init = labels["zx48_process_init"]
    process_table = labels["process_table"]
    current_pid = labels["current_pid"]
    schedule = labels["zx48_schedule"]
    idle_loop = labels["zx48_idle_loop"]
    pid0 = process_table
    pid1 = process_table + PROC_DESC_SIZE

    code = bytearray(b"\xF3\x31" + _word(phase1.KSTACK_TOP))
    code += _call(stack_init) + _call(process_init)
    code += _store_byte(pid0 + PROC_STATE, PROC_READY)
    code += _store_byte(pid1 + PROC_STATE, PROC_ZOMBIE)
    code += _store_byte(current_pid, 1)
    code += _jp(schedule)

    verifier = bytearray()
    verifier += _expect_byte(current_pid, 0)
    verifier += _expect_byte(pid0 + PROC_STATE, PROC_RUNNING)
    verifier += _expect_byte(pid1 + PROC_STATE, PROC_ZOMBIE)
    verifier += _jp(PASS_PC)

    patched = bytearray(kernel_bytes)
    offset = idle_loop - phase1.KERNEL_BASE
    require(0 <= offset <= len(patched) - 3, "idle-loop label outside kernel image")
    patched[offset:offset + 3] = _jp(VERIFY_PC)

    def patch(ram: bytearray) -> None:
        start = phase1.KERNEL_BASE - 0x4000
        ram[start:start + len(patched)] = patched
        ram[VERIFY_PC - 0x4000:VERIFY_PC - 0x4000 + len(verifier)] = verifier

    run_sna(root, bytes(code), patch=patch)


def dispatch(
    root: Path,
    action: str,
    step: str,
    *,
    sha256_file: Callable[[Path], str],
    run_command: Callable[..., Any],
    require_project_tool: Callable[[Path, str | Path], Path],
):
    if step != "P1.12":
        raise Phase1YieldError(f"cooperative yield step is not registered: {step}")

    assertions = _source_contract(root)
    failed = [str(item["name"]) for item in assertions if item["passed"] is not True]
    require(not failed, f"P1.12 static scheduler contract failed: {failed}")

    command, kernel, listing = phase1._assemble_kernel(root, run_command, require_project_tool)
    labels = phase1._labels(
        listing,
        (
            "zx48_kernel_stack_init",
            "zx48_process_init",
            "zx48_schedule",
            "zx48_schedule_restore",
            "zx48_idle_loop",
            "process_table",
            "current_pid",
            "scheduler_candidate",
        ),
    )
    kernel_bytes = kernel.read_bytes()

    if action == "test":
        _multitask_runtime(root, labels, kernel_bytes)
        _pid0_fallback_runtime(root, labels, kernel_bytes)
        assertions.extend(
            [
                {"name": "round-robin-ready-order-runtime", "passed": True},
                {"name": "expired-sleeper-wakes-during-scan", "passed": True},
                {"name": "exactly-one-running-record-at-runtime-checkpoints", "passed": True},
                {"name": "repeated-yield-context-preservation", "passed": True},
                {"name": "no-peer-yield-resumes-same-task", "passed": True},
                {"name": "pid0-fallback-runtime", "passed": True},
            ]
        )

    paths = (
        root / "v1/src/kernel/scheduler.asm",
        root / "v1/src/kernel/syscall.asm",
        root / "v1/src/kernel/process.asm",
        root / "v1/src/kernel/interrupt.asm",
        root / "v1/tools-host/test-driver/phase1_yield.py",
        kernel,
    )
    hashes = {str(path.relative_to(root)).replace("\\", "/"): sha256_file(path) for path in paths}
    return [command], hashes, assertions
