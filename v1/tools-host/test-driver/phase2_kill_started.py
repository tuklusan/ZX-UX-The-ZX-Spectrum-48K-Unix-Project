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

TEST_STACK = 0xFD00
FRAME_ADDRESS = 0x8A00
USER_CONT_PC = 0x8D00
SENTINEL_PC = 0x8D80
SENTINEL_MARKER = 0x6900

PROC_PARENT = 1
PROC_STATE = 2
PROC_FLAGS = 3
PROC_SAVED_SP = 12
PROC_EXIT_STATUS = 14
PROC_WAIT_OBJECT = 15
PROC_PRIVATE_FLAGS = 46
PROC_DESC_SIZE = 48

PROC_READY = 1
PROC_RUNNING = 2
PROC_SLEEPING = 3
PROC_WAIT_PIPE_READ = 5
PROC_FLAG_CANCEL = 0x01
PROC_PRIVATE_STARTED = 0x80
EXIT_SENTINEL = 0x5A
WAIT_SENTINEL = 0x55


class Phase219Error(DriverError):
    """Raised when the P2.19 blocked-started cancellation contract is violated."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Phase219Error(message)


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


def _jp_nc(address: int) -> bytes:
    return b"\xD2" + _word(address)


def _ld_sp(address: int) -> bytes:
    return b"\x31" + _word(address)


def _set_byte(address: int, value: int) -> bytes:
    return bytes((0x3E, value & 0xFF, 0x32)) + _word(address)


def _set_word(address: int, value: int) -> bytes:
    return b"\x21" + _word(value) + b"\x22" + _word(address)


def _expect_byte(address: int, value: int) -> bytes:
    return b"\x3A" + _word(address) + bytes((0xFE, value & 0xFF)) + _jp_nz(FAIL_PC)


def _block(text: str, start: str, end: str) -> str:
    begin = text.index(start)
    finish = text.index(end, begin)
    return text[begin:finish]


def _source_contract(root: Path) -> list[dict[str, object]]:
    include = (root / "v1/include/zx48ux.inc").read_text(encoding="utf-8")
    process = (root / "v1/src/kernel/process.asm").read_text(encoding="utf-8")
    scheduler = (root / "v1/src/kernel/scheduler.asm").read_text(encoding="utf-8")
    syscall = (root / "v1/src/kernel/syscall.asm").read_text(encoding="utf-8")

    started = _block(process, "zx48_process_kill_started:", "zx48_process_kill_okret:")
    restore = _block(scheduler, "zx48_schedule_restore:", "zx48_schedule_not_cancelled:")
    resume = _block(syscall, "zx48_syscall_resume_intr:", "IFDEF ZX48_P2_15_WAIT_ENABLED")

    return [
        {
            "name": "cancel-mask-is-bit-zero",
            "passed": "PROC_FLAG_CANCEL         EQU $01" in include,
        },
        {
            "name": "started-kill-publishes-cancel-and-ready",
            "passed": all(
                token in started
                for token in (
                    "or PROC_FLAG_CANCEL",
                    "ld (ix+PROC_FLAGS),a",
                    "ld (ix+PROC_WAIT_OBJECT),a",
                    "ld (ix+PROC_STATE),PROC_READY",
                )
            ),
        },
        {
            "name": "started-kill-remains-cooperative",
            "passed": "zx48_schedule" not in started,
        },
        {
            "name": "scheduler-delivers-eintr-at-saved-syscall-boundary",
            "passed": all(
                token in restore
                for token in (
                    "and PROC_FLAG_CANCEL",
                    "ld de,zx48_syscall_resume_intr",
                    "ld (hl),e",
                    "ld (hl),d",
                )
            ),
        },
        {
            "name": "scheduler-consumes-cancel-on-delivery",
            "passed": "res 0,(ix+PROC_FLAGS)" in restore,
        },
        {
            "name": "eintr-continuation-preserves-syscall-return-contract",
            "passed": all(
                token in resume
                for token in (
                    "ld (syscall_user_sp),sp",
                    "ld (syscall_saved_ix),ix",
                    "ld sp,BOOT_STACK_TOP",
                    "ld a,E_INTR",
                    "scf",
                    "jr zx48_syscall_return",
                )
            ),
        },
    ]


def _fixture_patch(kernel_bytes: bytes, frame_return: int, continuation: bytes):
    frame = b"\x00" * 10 + _word(SENTINEL_PC) + _word(frame_return)
    sentinel = _set_byte(SENTINEL_MARKER, 0xA5) + _jp(FAIL_PC)

    def patch(ram: bytearray) -> None:
        phase1._kernel_patch(kernel_bytes)(ram)
        for address, payload in (
            (FRAME_ADDRESS, frame),
            (USER_CONT_PC, continuation),
            (SENTINEL_PC, sentinel),
            (SENTINEL_MARKER, b"\x00"),
        ):
            offset = address - 0x4000
            ram[offset:offset + len(payload)] = payload

    return patch


def _setup_child(code: bytearray, labels: dict[str, int], state: int) -> int:
    process_table = labels["process_table"]
    child = process_table + 2 * PROC_DESC_SIZE
    pid1 = process_table + PROC_DESC_SIZE

    code += b"\xF3" + _ld_sp(TEST_STACK)
    code += _call(labels["zx48_kernel_stack_init"])
    code += _call(labels["zx48_process_init"])
    code += _set_byte(pid1 + PROC_STATE, PROC_RUNNING)
    code += _set_byte(labels["current_pid"], 1)
    code += _set_byte(child + PROC_PARENT, 1)
    code += _set_byte(child + PROC_STATE, state)
    code += _set_byte(child + PROC_FLAGS, 0)
    code += _set_word(child + PROC_SAVED_SP, FRAME_ADDRESS)
    code += _set_byte(child + PROC_EXIT_STATUS, EXIT_SENTINEL)
    code += _set_byte(child + PROC_WAIT_OBJECT, WAIT_SENTINEL)
    code += _set_byte(child + PROC_PRIVATE_FLAGS, PROC_PRIVATE_STARTED)
    code += _set_byte(SENTINEL_MARKER, 0)
    return child


def _positive_continuation(labels: dict[str, int], child: int) -> bytes:
    code = bytearray()
    code += _jp_nc(FAIL_PC)
    code += bytes((0xFE, labels["E_INTR"] & 0xFF)) + _jp_nz(FAIL_PC)
    code += _expect_byte(labels["current_pid"], 2)
    code += _expect_byte(child + PROC_STATE, PROC_RUNNING)
    code += _expect_byte(child + PROC_FLAGS, 0)
    code += _expect_byte(child + PROC_WAIT_OBJECT, 0)
    code += _expect_byte(child + PROC_EXIT_STATUS, EXIT_SENTINEL)
    code += _expect_byte(SENTINEL_MARKER, 0)
    code += _jp(PASS_PC)
    return bytes(code)


def _blocked_vector(root: Path, labels: dict[str, int], kernel_bytes: bytes, state: int) -> None:
    code = bytearray()
    child = _setup_child(code, labels, state)
    code += bytes((0x3E, 2)) + _call(labels["zx48_process_kill"]) + _jp_c(FAIL_PC)

    # SYS_KILL must only publish cancellation and wake the blocked target.
    code += _expect_byte(labels["current_pid"], 1)
    code += _expect_byte(child + PROC_STATE, PROC_READY)
    code += _expect_byte(child + PROC_FLAGS, PROC_FLAG_CANCEL)
    code += _expect_byte(child + PROC_WAIT_OBJECT, 0)
    code += _expect_byte(child + PROC_EXIT_STATUS, EXIT_SENTINEL)
    code += _expect_byte(SENTINEL_MARKER, 0)

    # Explicitly choose the target at the next scheduler boundary.
    code += _set_byte(labels["scheduler_candidate"], 2)
    code += bytes((0x3E, 2)) + _call(labels["zx48_process_ptr"]) + _jp_c(FAIL_PC)
    code += _jp(labels["zx48_schedule_restore"])

    continuation = _positive_continuation(labels, child)
    run_sna(
        root,
        bytes(code),
        patch=_fixture_patch(kernel_bytes, USER_CONT_PC, continuation),
        timeout=20.0,
    )


def _no_preemption_vector(root: Path, labels: dict[str, int], kernel_bytes: bytes) -> None:
    code = bytearray()
    child = _setup_child(code, labels, PROC_READY)
    code += bytes((0x3E, 2)) + _call(labels["zx48_process_kill"]) + _jp_c(FAIL_PC)
    code += _expect_byte(labels["current_pid"], 1)
    code += _expect_byte(child + PROC_STATE, PROC_READY)
    code += _expect_byte(child + PROC_FLAGS, PROC_FLAG_CANCEL)
    code += _expect_byte(child + PROC_WAIT_OBJECT, 0)
    code += _expect_byte(child + PROC_EXIT_STATUS, EXIT_SENTINEL)
    code += _expect_byte(SENTINEL_MARKER, 0)
    code += _jp(PASS_PC)
    run_sna(
        root,
        bytes(code),
        patch=_fixture_patch(kernel_bytes, SENTINEL_PC, b""),
        timeout=20.0,
    )


def dispatch(
    root: Path,
    action: str,
    step: str,
    *,
    sha256_file: Callable[[Path], str],
    run_command: Callable[..., Any],
    require_project_tool: Callable[[Path, str | Path], Path],
):
    if step != "P2.19":
        raise Phase219Error(f"P2.19 driver received unexpected step: {step}")

    assertions = _source_contract(root)
    failed = [item["name"] for item in assertions if item["passed"] is not True]
    require(not failed, f"static P2.19 contract failures: {failed}")

    result, kernel, listing = phase1._assemble_kernel(root, run_command, require_project_tool)
    commands: list[Any] = [result]
    labels = phase1._labels(
        listing,
        (
            "zx48_kernel_stack_init",
            "zx48_process_init",
            "zx48_process_kill",
            "zx48_process_ptr",
            "zx48_schedule_restore",
            "process_table",
            "current_pid",
            "scheduler_candidate",
            "E_INTR",
        ),
    )
    kernel_bytes = kernel.read_bytes()

    if action == "test":
        _blocked_vector(root, labels, kernel_bytes, PROC_SLEEPING)
        _blocked_vector(root, labels, kernel_bytes, PROC_WAIT_PIPE_READ)
        _no_preemption_vector(root, labels, kernel_bytes)
        assertions.extend(
            [
                {"name": "sleeping-started-child-wakes-eintr-and-consumes-cancel", "passed": True},
                {"name": "blocked-read-started-child-wakes-eintr-and-consumes-cancel", "passed": True},
                {"name": "kill-does-not-arbitrarily-preempt-caller", "passed": True},
            ]
        )

    hashes = {
        "v1/build/kernel.bin": sha256_file(kernel),
        "v1/include/zx48ux.inc": sha256_file(root / "v1/include/zx48ux.inc"),
        "v1/src/kernel/process.asm": sha256_file(root / "v1/src/kernel/process.asm"),
        "v1/src/kernel/scheduler.asm": sha256_file(root / "v1/src/kernel/scheduler.asm"),
        "v1/src/kernel/syscall.asm": sha256_file(root / "v1/src/kernel/syscall.asm"),
        "v1/tools-host/test-driver/phase2_kill_started.py": sha256_file(
            root / "v1/tools-host/test-driver/phase2_kill_started.py"
        ),
        "v1/tools-host/test-driver/run.py": sha256_file(root / "v1/tools-host/test-driver/run.py"),
        "v1/tools-host/test-driver/phase2_gate.py": sha256_file(root / "v1/tools-host/test-driver/phase2_gate.py"),
    }
    return commands, hashes, assertions
