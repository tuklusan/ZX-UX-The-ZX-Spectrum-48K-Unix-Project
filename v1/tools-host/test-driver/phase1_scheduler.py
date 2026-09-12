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
PROC_PRIVATE_FLAGS = 46

PROC_FREE = 0
PROC_READY = 1
PROC_RUNNING = 2
PROC_SLEEPING = 3

SYS_YIELD = 0x02

FRAME1_SP = 0xA800
FRAME2_SP = 0xA900
FRAME3_SP = 0xAA00
USER1_PC = 0xA100
USER2_PC = 0xA200
USER3_PC = 0xA300
SOLO_PC = 0xA400
LOG = 0xAB00

IX1 = 0x8111
IX2 = 0x8222
IX3 = 0x8333


class Phase1SchedulerError(DriverError):
    """Raised when the P1.12 cooperative round-robin scheduler contract fails."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Phase1SchedulerError(message)


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


def _ld_sp(value: int) -> bytes:
    return b"\x31" + _word(value)


def _ld_ix(value: int) -> bytes:
    return b"\xDD\x21" + _word(value)


def _store_byte(address: int, value: int) -> bytes:
    return bytes((0x3E, value & 0xFF, 0x32)) + _word(address)


def _expect_byte(address: int, value: int) -> bytes:
    return b"\x3A" + _word(address) + bytes((0xFE, value & 0xFF)) + _jp_nz(FAIL_PC)


def _expect_ix(value: int) -> bytes:
    return b"\xDD\xE5\xE1\x11" + _word(value) + b"\xB7\xED\x52" + _jp_nz(FAIL_PC)


def _yield_call() -> bytes:
    return bytes((0x3E, SYS_YIELD)) + _call(phase1.KERNEL_BASE) + _jp_c(FAIL_PC)


def _scheduler_body(root: Path) -> str:
    return (root / "v1/src/kernel/scheduler.asm").read_text(encoding="utf-8").lower()


def _round_robin_start_ok(scheduler: str) -> bool:
    return (
        "ld a,(scheduler_current)\n    inc a\n    and 7\n    ld (scheduler_candidate),a"
        in scheduler
    )


def _sleeper_wake_ok(scheduler: str) -> bool:
    return (
        "cp proc_sleeping\n    call z,zx48_scheduler_maybe_wake\n"
        "    ld a,(ix+proc_state)\n    cp proc_ready"
    ) in scheduler


def _interrupt_is_safe(interrupt: str) -> bool:
    return "zx48_schedule" not in interrupt


def _exactly_one_running(states: tuple[int, ...]) -> bool:
    return sum(state == PROC_RUNNING for state in states) == 1


def _source_contract(root: Path) -> list[dict[str, object]]:
    scheduler = _scheduler_body(root)
    syscall = (root / "v1/src/kernel/syscall.asm").read_text(encoding="utf-8").lower()
    interrupt = (root / "v1/src/kernel/interrupt.asm").read_text(encoding="utf-8").lower()

    ordered = (
        "ld a,(current_pid)",
        "ld (scheduler_current),a",
        "inc a",
        "and 7",
        "ld (scheduler_candidate),a",
        "ld b,max_processes",
        "zx48_schedule_scan:",
        "cp proc_sleeping",
        "call z,zx48_scheduler_maybe_wake",
        "cp proc_ready",
        "jr z,zx48_schedule_choose",
    )
    positions = [scheduler.find(token) for token in ordered]

    return [
        {
            "name": "yield-enters-cooperative-scheduler",
            "passed": "zx48_sys_yield:\n    jp zx48_schedule_finish_syscall" in syscall,
        },
        {
            "name": "round-robin-scan-starts-after-current",
            "passed": _round_robin_start_ok(scheduler)
            and all(pos >= 0 for pos in positions)
            and positions == sorted(positions),
        },
        {
            "name": "running-current-becomes-ready-before-scan",
            "passed": (
                "cp proc_running\n    jr nz,zx48_schedule_begin\n"
                "    ld (ix+proc_state),proc_ready\n    jr zx48_schedule_begin"
            ) in scheduler,
        },
        {
            "name": "sleepers-wake-inside-ready-scan",
            "passed": _sleeper_wake_ok(scheduler),
        },
        {
            "name": "pid0-is-fallback-not-user-scan-candidate",
            "passed": (
                "ld a,(scheduler_candidate)\n    or a\n    jr z,zx48_schedule_next"
            ) in scheduler
            and (
                "djnz zx48_schedule_scan\n    xor a\n    ld (scheduler_candidate),a\n"
                "    call zx48_process_ptr\n    jr zx48_schedule_restore"
            ) in scheduler,
        },
        {
            "name": "selected-task-is-sole-scheduler-running-transition",
            "passed": (
                "ld a,(scheduler_candidate)\n    ld (current_pid),a\n"
                "    ld (ix+proc_state),proc_running"
            ) in scheduler,
        },
        {
            "name": "no-priority-system",
            "passed": "priority" not in scheduler,
        },
        {
            "name": "interrupt-does-not-context-switch",
            "passed": _interrupt_is_safe(interrupt),
        },
    ]


def _negative_contract_tests(root: Path) -> list[dict[str, object]]:
    scheduler = _scheduler_body(root)
    interrupt = (root / "v1/src/kernel/interrupt.asm").read_text(encoding="utf-8").lower()

    biased = scheduler.replace(
        "ld a,(scheduler_current)\n    inc a\n    and 7",
        "ld a,(scheduler_current)\n    xor a\n    and 7",
        1,
    )
    no_wake = scheduler.replace("call z,zx48_scheduler_maybe_wake", "nop", 1)
    irq_switch = interrupt + "\n    call zx48_schedule\n"

    return [
        {
            "name": "reject-priority-or-fixed-pid-biased-selection",
            "passed": not _round_robin_start_ok(biased),
        },
        {
            "name": "reject-skipped-sleeper-wake",
            "passed": not _sleeper_wake_ok(no_wake),
        },
        {
            "name": "reject-two-running-records",
            "passed": not _exactly_one_running((PROC_RUNNING, PROC_RUNNING, PROC_READY)),
        },
        {
            "name": "reject-interrupt-context-switch",
            "passed": not _interrupt_is_safe(irq_switch),
        },
    ]


def _frame(ix: int, pc: int) -> bytes:
    return b"".join(
        _word(value)
        for value in (ix, 0x9234, 0xA345, 0xB456, 0xC700, pc)
    )


def _set_desc(desc: int, *, state: int, saved_sp: int, wake_tick: int = 0) -> bytes:
    code = bytearray(_store_byte(desc + PROC_STATE, state))
    code += _store_byte(desc + PROC_SAVED_SP, saved_sp & 0xFF)
    code += _store_byte(desc + PROC_SAVED_SP + 1, saved_sp >> 8)
    code += _store_byte(desc + PROC_PRIVATE_FLAGS, 0)
    for offset in range(4):
        code += _store_byte(desc + PROC_WAKE_TICK + offset, (wake_tick >> (8 * offset)) & 0xFF)
    return bytes(code)


def _user1(current_pid: int, process_table: int) -> bytes:
    code = bytearray(_store_byte(LOG + 0, 1))
    code += _ld_ix(IX1) + _yield_call()
    code += _expect_ix(IX1)
    code += _store_byte(LOG + 3, 4)
    code += _yield_call()
    code += _expect_ix(IX1)
    for offset, value in enumerate((1, 2, 3, 4, 5, 6)):
        code += _expect_byte(LOG + offset, value)
    code += _expect_byte(current_pid, 1)
    expected_states = (PROC_READY, PROC_RUNNING, PROC_READY, PROC_READY, PROC_FREE, PROC_FREE, PROC_FREE, PROC_FREE)
    for pid, state in enumerate(expected_states):
        code += _expect_byte(process_table + pid * PROC_DESC_SIZE + PROC_STATE, state)
    code += _jp(PASS_PC)
    return bytes(code)


def _user2() -> bytes:
    code = bytearray(_store_byte(LOG + 1, 2))
    code += _ld_ix(IX2) + _yield_call()
    code += _expect_ix(IX2)
    code += _store_byte(LOG + 4, 5)
    code += _yield_call()
    code += _jp(FAIL_PC)
    return bytes(code)


def _user3() -> bytes:
    code = bytearray(_store_byte(LOG + 2, 3))
    code += _ld_ix(IX3) + _yield_call()
    code += _expect_ix(IX3)
    code += _store_byte(LOG + 5, 6)
    code += _yield_call()
    code += _jp(FAIL_PC)
    return bytes(code)


def _round_robin_runtime(root: Path, labels: dict[str, int], kernel_bytes: bytes) -> None:
    stack_init = labels["zx48_kernel_stack_init"]
    process_init = labels["zx48_process_init"]
    schedule = labels["zx48_schedule"]
    process_table = labels["process_table"]
    current_pid = labels["current_pid"]
    kernel_ticks = labels["kernel_ticks"]

    pid1 = process_table + PROC_DESC_SIZE
    pid2 = process_table + 2 * PROC_DESC_SIZE
    pid3 = process_table + 3 * PROC_DESC_SIZE

    code = bytearray(b"\xF3" + _ld_sp(phase1.KSTACK_TOP))
    code += _call(stack_init) + _call(process_init)
    code += _set_desc(pid1, state=PROC_READY, saved_sp=FRAME1_SP)
    code += _set_desc(pid2, state=PROC_READY, saved_sp=FRAME2_SP)
    code += _set_desc(pid3, state=PROC_SLEEPING, saved_sp=FRAME3_SP, wake_tick=0)
    for offset in range(4):
        code += _store_byte(kernel_ticks + offset, 0)
        code += _store_byte(LOG + offset, 0)
    code += _store_byte(LOG + 4, 0) + _store_byte(LOG + 5, 0)
    code += _jp(schedule)

    user1 = _user1(current_pid, process_table)
    user2 = _user2()
    user3 = _user3()

    def patch(ram: bytearray) -> None:
        start = phase1.KERNEL_BASE - 0x4000
        ram[start:start + len(kernel_bytes)] = kernel_bytes
        for address, payload in (
            (FRAME1_SP, _frame(IX1, USER1_PC)),
            (FRAME2_SP, _frame(IX2, USER2_PC)),
            (FRAME3_SP, _frame(IX3, USER3_PC)),
            (USER1_PC, user1),
            (USER2_PC, user2),
            (USER3_PC, user3),
        ):
            offset = address - 0x4000
            ram[offset:offset + len(payload)] = payload

    run_sna(root, bytes(code), patch=patch)


def _no_peer_runtime(root: Path, labels: dict[str, int], kernel_bytes: bytes) -> None:
    stack_init = labels["zx48_kernel_stack_init"]
    process_init = labels["zx48_process_init"]
    schedule = labels["zx48_schedule"]
    process_table = labels["process_table"]
    current_pid = labels["current_pid"]

    pid1 = process_table + PROC_DESC_SIZE
    solo_frame = 0xAC00
    solo_ix = 0x8444

    code = bytearray(b"\xF3" + _ld_sp(phase1.KSTACK_TOP))
    code += _call(stack_init) + _call(process_init)
    code += _set_desc(pid1, state=PROC_READY, saved_sp=solo_frame)
    code += _jp(schedule)

    solo = bytearray(_ld_ix(solo_ix) + _yield_call())
    solo += _expect_ix(solo_ix)
    solo += _expect_byte(current_pid, 1)
    solo += _expect_byte(process_table + PROC_STATE, PROC_READY)
    solo += _expect_byte(pid1 + PROC_STATE, PROC_RUNNING)
    solo += _jp(PASS_PC)

    def patch(ram: bytearray) -> None:
        start = phase1.KERNEL_BASE - 0x4000
        ram[start:start + len(kernel_bytes)] = kernel_bytes
        frame = solo_frame - 0x4000
        ram[frame:frame + 12] = _frame(solo_ix, SOLO_PC)
        body = SOLO_PC - 0x4000
        ram[body:body + len(solo)] = solo

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
        raise Phase1SchedulerError(f"scheduler step is not registered: {step}")

    assertions = _source_contract(root)
    failed = [str(item["name"]) for item in assertions if item["passed"] is not True]
    require(not failed, f"P1.12 static scheduler failures: {failed}")

    command, kernel, listing = phase1._assemble_kernel(root, run_command, require_project_tool)
    labels = phase1._labels(
        listing,
        (
            "zx48_kernel_stack_init",
            "zx48_process_init",
            "zx48_schedule",
            "process_table",
            "current_pid",
            "kernel_ticks",
        ),
    )
    kernel_bytes = kernel.read_bytes()

    if action == "test":
        _round_robin_runtime(root, labels, kernel_bytes)
        _no_peer_runtime(root, labels, kernel_bytes)
        assertions.extend(
            [
                {"name": "ordered-round-robin-two-complete-cycles", "passed": True, "order": [1, 2, 3, 1, 2, 3]},
                {"name": "sleeping-task-wakes-during-scan", "passed": True},
                {"name": "exactly-one-running-after-repeated-yields", "passed": True},
                {"name": "ix-context-preserved-across-repeated-yields", "passed": True},
                {"name": "no-ready-peer-yield-safely-resumes-current-task", "passed": True},
                *_negative_contract_tests(root),
            ]
        )
        failed = [str(item["name"]) for item in assertions if item["passed"] is not True]
        require(not failed, f"P1.12 runtime/negative scheduler failures: {failed}")

    paths = (
        root / "v1/src/kernel/scheduler.asm",
        root / "v1/src/kernel/process.asm",
        root / "v1/src/kernel/syscall.asm",
        root / "v1/src/kernel/interrupt.asm",
        root / "v1/tools-host/test-driver/phase1_scheduler.py",
        kernel,
    )
    hashes = {str(path.relative_to(root)).replace("\\", "/"): sha256_file(path) for path in paths}
    return [command], hashes, assertions
