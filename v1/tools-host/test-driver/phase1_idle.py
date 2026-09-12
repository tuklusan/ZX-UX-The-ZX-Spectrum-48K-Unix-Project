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
PROC_OWNED_BYTES = 40
PROC_PRIVATE_FLAGS = 46
PROC_RUNNING = 2
PROC_SLEEPING = 3

FRAME_SP = 0xA800
VERIFY_PC = 0xB100


class Phase1IdleError(DriverError):
    """Raised when the P1.08 PID0 idle contract is violated."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Phase1IdleError(message)


def _word(value: int) -> bytes:
    return bytes((value & 0xFF, (value >> 8) & 0xFF))


def _call(address: int) -> bytes:
    return b"\xCD" + _word(address)


def _jp(address: int) -> bytes:
    return b"\xC3" + _word(address)


def _jp_z(address: int) -> bytes:
    return b"\xCA" + _word(address)


def _jp_nz(address: int) -> bytes:
    return b"\xC2" + _word(address)


def _ld_sp(value: int) -> bytes:
    return b"\x31" + _word(value)


def _ld_ix(value: int) -> bytes:
    return b"\xDD\x21" + _word(value)


def _store_byte(address: int, value: int) -> bytes:
    return bytes((0x3E, value & 0xFF, 0x32)) + _word(address)


def _expect_byte(address: int, value: int) -> bytes:
    return b"\x3A" + _word(address) + bytes((0xFE, value & 0xFF)) + _jp_nz(FAIL_PC)


def _idle_body(scheduler: str) -> str:
    lower = scheduler.lower()
    start = lower.find("zx48_idle_loop:")
    end = lower.find("scheduler_current:", start)
    require(0 <= start < end, "PID0 idle body missing")
    return lower[start:end]


def _idle_sequence_is_safe(body: str) -> bool:
    exact = "zx48_idle_loop:\n    ei\n    halt\n    call zx48_scheduler_wake_scan\n    jp zx48_schedule"
    return (
        exact in body
        and "\n    di\n" not in body
        and "zx48_alloc" not in body
        and "process_exit" not in body
    )


def _pid0_exit_is_rejected(process: str) -> bool:
    lower = process.lower()
    start = lower.find("zx48_process_exit:")
    end = lower.find("zx48_process_exit_panic:", start)
    if not (0 <= start < end):
        return False
    body = lower[start:end]
    return "ld a,(current_pid)\n    or a\n    jr z,zx48_process_exit_panic" in body


def _source_contract(root: Path) -> list[dict[str, object]]:
    scheduler = (root / "v1/src/kernel/scheduler.asm").read_text(encoding="utf-8")
    process = (root / "v1/src/kernel/process.asm").read_text(encoding="utf-8")
    lower = scheduler.lower()
    idle = _idle_body(scheduler)
    return [
        {"name": "pid0-idle-is-exact-ei-halt", "passed": _idle_sequence_is_safe(idle)},
        {
            "name": "scheduler-falls-back-to-pid0-only-after-ready-scan",
            "passed": (
                "djnz zx48_schedule_scan\n    xor a\n    ld (scheduler_candidate),a\n"
                "    call zx48_process_ptr\n    jr zx48_schedule_restore"
            ) in lower,
        },
        {
            "name": "scheduler-skips-pid0-during-user-ready-scan",
            "passed": (
                "ld a,(scheduler_candidate)\n    or a\n    jr z,zx48_schedule_next"
            ) in lower,
        },
        {
            "name": "pid0-wake-scan-runs-after-halt",
            "passed": "halt\n    call zx48_scheduler_wake_scan\n    jp zx48_schedule" in idle,
        },
        {"name": "pid0-exit-is-rejected", "passed": _pid0_exit_is_rejected(process)},
    ]


def _negative_contract_tests(root: Path) -> list[dict[str, object]]:
    scheduler = (root / "v1/src/kernel/scheduler.asm").read_text(encoding="utf-8")
    process = (root / "v1/src/kernel/process.asm").read_text(encoding="utf-8")
    idle = _idle_body(scheduler)
    return [
        {
            "name": "reject-halt-with-interrupts-disabled",
            "passed": not _idle_sequence_is_safe(idle.replace("\n    ei\n    halt", "\n    di\n    halt")),
        },
        {
            "name": "reject-busy-spin-idle",
            "passed": not _idle_sequence_is_safe(idle.replace("\n    ei\n    halt", "\n    jp zx48_idle_loop")),
        },
        {
            "name": "reject-idle-user-arena-allocation",
            "passed": not _idle_sequence_is_safe(idle.replace("\n    halt\n", "\n    halt\n    call zx48_alloc\n")),
        },
        {
            "name": "reject-pid0-normal-exit",
            "passed": not _pid0_exit_is_rejected(
                process.replace("jr z,zx48_process_exit_panic", "jr z,zx48_process_exit_continue", 1)
            ),
        },
    ]


def _frame() -> bytes:
    return b"".join(_word(value) for value in (0x8123, 0x9234, 0xA345, 0xB456, 0xC7A5, VERIFY_PC))


def _verifier(*, current_pid: int, process_table: int, kernel_ticks: int, scheduler_tick_due: int) -> bytes:
    pid1 = process_table + PROC_DESC_SIZE
    code = bytearray()
    code += _expect_byte(current_pid, 1)
    code += _expect_byte(pid1 + PROC_STATE, PROC_RUNNING)
    code += _expect_byte(process_table + PROC_OWNED_BYTES, 0)
    code += _expect_byte(process_table + PROC_OWNED_BYTES + 1, 0)
    code += _expect_byte(scheduler_tick_due, 1)
    code += b"\x3A" + _word(kernel_ticks) + b"\xB7" + _jp_z(FAIL_PC)
    code += _jp(PASS_PC)
    return bytes(code)


def _runtime_test(root: Path, labels: dict[str, int], kernel_bytes: bytes) -> None:
    stack_init = labels["zx48_kernel_stack_init"]
    process_init = labels["zx48_process_init"]
    idle_loop = labels["zx48_idle_loop"]
    interrupt = labels["zx48_interrupt"]
    process_table = labels["process_table"]
    current_pid = labels["current_pid"]
    kernel_ticks = labels["kernel_ticks"]
    scheduler_tick_due = labels["scheduler_tick_due"]

    pid1 = process_table + PROC_DESC_SIZE
    code = bytearray(b"\xF3" + _ld_sp(phase1.KSTACK_TOP))
    code += _call(stack_init) + _call(process_init)
    code += _ld_ix(pid1)
    code += bytes((0xDD, 0x36, PROC_STATE, PROC_SLEEPING))
    code += bytes((0xDD, 0x36, PROC_SAVED_SP, FRAME_SP & 0xFF))
    code += bytes((0xDD, 0x36, PROC_SAVED_SP + 1, FRAME_SP >> 8))
    code += bytes((0xDD, 0x36, PROC_WAKE_TICK, 1))
    code += bytes((0xDD, 0x36, PROC_WAKE_TICK + 1, 0))
    code += bytes((0xDD, 0x36, PROC_WAKE_TICK + 2, 0))
    code += bytes((0xDD, 0x36, PROC_WAKE_TICK + 3, 0))
    code += bytes((0xDD, 0x36, PROC_PRIVATE_FLAGS, 0))
    for offset in range(4):
        code += _store_byte(kernel_ticks + offset, 0)
    code += _store_byte(scheduler_tick_due, 0)
    code += b"\x3E\xFE\xED\x47\xED\x5E"
    code += _jp(idle_loop)

    verify = _verifier(
        current_pid=current_pid,
        process_table=process_table,
        kernel_ticks=kernel_ticks,
        scheduler_tick_due=scheduler_tick_due,
    )

    def patch(ram: bytearray) -> None:
        start = phase1.KERNEL_BASE - 0x4000
        ram[start:start + len(kernel_bytes)] = kernel_bytes
        frame = FRAME_SP - 0x4000
        ram[frame:frame + 12] = _frame()
        verifier = VERIFY_PC - 0x4000
        ram[verifier:verifier + len(verify)] = verify
        table = 0xFE00 - 0x4000
        ram[table:table + 257] = bytes((0xFD,)) * 257
        trampoline = 0xFDFD - 0x4000
        ram[trampoline:trampoline + 3] = _jp(interrupt)

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
    if step != "P1.08":
        raise Phase1IdleError(f"PID0 idle step is not registered: {step}")

    assertions = _source_contract(root)
    failed = [str(item["name"]) for item in assertions if item["passed"] is not True]
    require(not failed, f"P1.08 static PID0 idle contract failed: {failed}")

    command, kernel, listing = phase1._assemble_kernel(root, run_command, require_project_tool)
    labels = phase1._labels(
        listing,
        (
            "zx48_kernel_stack_init",
            "zx48_process_init",
            "zx48_idle_loop",
            "zx48_interrupt",
            "process_table",
            "current_pid",
            "kernel_ticks",
            "scheduler_tick_due",
        ),
    )
    kernel_bytes = kernel.read_bytes()

    if action == "test":
        _runtime_test(root, labels, kernel_bytes)
        assertions.extend(
            [
                {"name": "pid0-halt-wakes-on-im2-and-reschedules", "passed": True},
                {"name": "pid0-owned-user-bytes-remain-zero", "passed": True},
                *_negative_contract_tests(root),
            ]
        )
        failed = [str(item["name"]) for item in assertions if item["passed"] is not True]
        require(not failed, f"P1.08 negative/runtime PID0 idle contract failed: {failed}")

    paths = (
        root / "v1/src/kernel/scheduler.asm",
        root / "v1/src/kernel/process.asm",
        root / "v1/src/kernel/interrupt.asm",
        root / "v1/tools-host/test-driver/phase1_idle.py",
        kernel,
    )
    hashes = {str(path.relative_to(root)).replace("\\", "/"): sha256_file(path) for path in paths}
    return [command], hashes, assertions
