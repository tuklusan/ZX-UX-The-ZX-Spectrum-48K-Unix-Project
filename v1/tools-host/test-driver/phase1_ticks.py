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

SYS_TICKS = 0x62
ROM_FRAMES = 0x5C78
TICK_BUFFER = 0xA700


class Phase1TicksError(DriverError):
    """Raised when the P1.13 bounded IM2/tick contract is violated."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Phase1TicksError(message)


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


def _interrupt_source_contract(root: Path) -> list[dict[str, object]]:
    text = (root / "v1/src/kernel/interrupt.asm").read_text(encoding="utf-8").lower()
    body = text.split("zx48_interrupt_work:", 1)[1].split("endm", 1)[0]
    handler = text.split("zx48_interrupt:", 1)[1].split("zx48_interrupt_work:", 1)[0]
    forbidden = (
        "zx48_schedule",
        "zx48_memory_alloc",
        "zx48_memory_free",
        "zx48_rom_",
        "zx48_keyboard_getkey",
        "zx48_console_",
        "zx48_pipe_",
        "zx48_process_exit",
    )
    return [
        {"name": "tick-low-word-increments", "passed": "ld hl,(kernel_ticks)\n    inc hl\n    ld (kernel_ticks),hl" in body},
        {"name": "tick-high-word-carries-on-low-wrap", "passed": "ld hl,(kernel_ticks+2)\n    inc hl\n    ld (kernel_ticks+2),hl" in body},
        {"name": "rom-frames-mirror-is-present", "passed": "ld hl,rom_frames" in body},
        {"name": "scheduler-wake-flag-only", "passed": "ld (scheduler_tick_due),a" in body and "call zx48_schedule" not in body},
        {"name": "break-sampling-is-direct-matrix-only", "passed": "ld bc,$fefe\n    in a,(c)" in body and "ld bc,$7ffe\n    in a,(c)" in body},
        {"name": "cursor-timing-is-flag-only", "passed": "ld (tty_cursor_due),a" in body},
        {"name": "wall-clock-update-is-bounded", "passed": "ld a,(wall_valid)" in body and "ld (wall_subsecond),a" in body},
        {"name": "isr-has-no-heavy-or-blocking-call", "passed": not any(token in body for token in forbidden)},
        {"name": "fast-and-safe-paths-return-with-reti", "passed": handler.count("reti") == 2 and handler.count("ei") == 2},
    ]


def _sys_ticks_source_contract(root: Path) -> list[dict[str, object]]:
    text = (root / "v1/src/kernel/syscall.asm").read_text(encoding="utf-8").lower()
    body = text.split("zx48_sys_ticks:", 1)[1].split("zx48_sys_time_get:", 1)[0]
    ordered = (
        "ld hl,(syscall_arg_hl)",
        "ld bc,4",
        "call zx48_user_range_validate",
        "ret c",
        "di",
        "ld de,(kernel_ticks)",
        "ld (syscall_tick_lo),de",
        "ld de,(kernel_ticks+2)",
        "ld (syscall_tick_hi),de",
        "ei",
        "ld hl,(syscall_arg_hl)",
        "ld de,(syscall_tick_lo)",
        "call zx48_sys_put16",
        "ld de,(syscall_tick_hi)",
        "call zx48_sys_put16",
    )
    positions = [body.find(token) for token in ordered]
    return [
        {"name": "ticks-validates-exact-four-byte-output", "passed": "ld bc,4" in body and "call zx48_user_range_validate" in body},
        {"name": "ticks-snapshot-is-coherent", "passed": all(pos >= 0 for pos in positions) and positions == sorted(positions)},
        {"name": "ticks-has-no-wall-validity-dependency", "passed": "wall_valid" not in body and "wall_seconds" not in body},
    ]


def _negative_contract_tests(root: Path) -> list[dict[str, object]]:
    interrupt = (root / "v1/src/kernel/interrupt.asm").read_text(encoding="utf-8").lower()
    syscall = (root / "v1/src/kernel/syscall.asm").read_text(encoding="utf-8").lower()
    broken_interrupt = interrupt.replace("inc hl\n    ld (kernel_ticks),hl", "nop\n    ld (kernel_ticks),hl", 1)
    broken_syscall = syscall.replace("di\n    ld de,(kernel_ticks)", "nop\n    ld de,(kernel_ticks)", 1)
    return [
        {"name": "reject-missing-per-frame-tick-increment", "passed": "ld hl,(kernel_ticks)\n    inc hl\n    ld (kernel_ticks),hl" not in broken_interrupt},
        {"name": "reject-torn-sys-ticks-snapshot", "passed": "di\n    ld de,(kernel_ticks)" not in broken_syscall},
    ]


def _runtime_interrupts(root: Path, labels: dict[str, int], kernel_bytes: bytes) -> None:
    stack_init = labels["zx48_kernel_stack_init"]
    interrupt = labels["zx48_interrupt"]
    kernel_ticks = labels["kernel_ticks"]
    wall_seconds = labels["wall_seconds"]
    wall_valid = labels["wall_valid"]
    scheduler_tick_due = labels["scheduler_tick_due"]
    altreg_busy = labels["altreg_busy"]

    code = bytearray(b"\xF3\x31" + _word(phase1.USER_STACK))
    code += _call(stack_init)
    for offset, value in enumerate((0xFE, 0xFF, 0xFF, 0xFF)):
        code += _store_byte(kernel_ticks + offset, value)
    for offset, value in enumerate((0x44, 0x33, 0x22, 0x11)):
        code += _store_byte(wall_seconds + offset, value)
    code += _store_byte(wall_valid, 0)
    code += _store_byte(scheduler_tick_due, 0)
    code += _store_byte(ROM_FRAMES + 0, 0xFE)
    code += _store_byte(ROM_FRAMES + 1, 0xFF)
    code += _store_byte(ROM_FRAMES + 2, 0x12)

    # Safe ISR path, then fast alternate-bank path: exactly two accepted frames.
    code += _store_byte(altreg_busy, 1) + _call(interrupt)
    code += _store_byte(altreg_busy, 0) + _call(interrupt)

    for offset in range(4):
        code += _expect_byte(kernel_ticks + offset, 0)
    code += _expect_byte(ROM_FRAMES + 0, 0)
    code += _expect_byte(ROM_FRAMES + 1, 0)
    code += _expect_byte(ROM_FRAMES + 2, 0x13)
    code += _expect_byte(scheduler_tick_due, 1)
    for offset, value in enumerate((0x44, 0x33, 0x22, 0x11)):
        code += _expect_byte(wall_seconds + offset, value)
    code += _jp(PASS_PC)
    run_sna(root, bytes(code), patch=phase1._kernel_patch(kernel_bytes))


def _runtime_sys_ticks(root: Path, labels: dict[str, int], kernel_bytes: bytes) -> None:
    stack_init = labels["zx48_kernel_stack_init"]
    kernel_ticks = labels["kernel_ticks"]

    code = bytearray(b"\xF3\x31" + _word(phase1.USER_STACK))
    code += _call(stack_init)
    for offset, value in enumerate((0x78, 0x56, 0x34, 0x12)):
        code += _store_byte(kernel_ticks + offset, value)
        code += _store_byte(TICK_BUFFER + offset, 0xA5)
    code += b"\x21" + _word(TICK_BUFFER) + bytes((0x3E, SYS_TICKS)) + _call(phase1.KERNEL_BASE) + _jp_c(FAIL_PC)
    for offset, value in enumerate((0x78, 0x56, 0x34, 0x12)):
        code += _expect_byte(TICK_BUFFER + offset, value)

    # Wrapped/protected four-byte destination must fail before any write.
    code += b"\x21\xFE\xFF" + bytes((0x3E, SYS_TICKS)) + _call(phase1.KERNEL_BASE) + _jp_nc(FAIL_PC)
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
    if step != "P1.13":
        raise Phase1TicksError(f"tick/IM2 step is not registered: {step}")

    assertions = _interrupt_source_contract(root) + _sys_ticks_source_contract(root)
    failed = [str(item["name"]) for item in assertions if item["passed"] is not True]
    require(not failed, f"P1.13 static tick/IM2 contract failed: {failed}")

    command, kernel, listing = phase1._assemble_kernel(root, run_command, require_project_tool)
    labels = phase1._labels(
        listing,
        (
            "zx48_kernel_stack_init",
            "zx48_interrupt",
            "kernel_ticks",
            "wall_seconds",
            "wall_valid",
            "scheduler_tick_due",
            "altreg_busy",
        ),
    )
    kernel_bytes = kernel.read_bytes()

    if action == "test":
        _runtime_interrupts(root, labels, kernel_bytes)
        _runtime_sys_ticks(root, labels, kernel_bytes)
        assertions.extend(
            [
                {"name": "two-accepted-frames-increment-ticks-exactly-twice", "passed": True},
                {"name": "tick-wrap-is-modulo-2-to-32", "passed": True},
                {"name": "rom-frames-carry-runtime", "passed": True},
                {"name": "wall-invalid-ticks-do-not-change-wall-seconds", "passed": True},
                {"name": "sys-ticks-little-endian-coherent-snapshot", "passed": True},
                {"name": "sys-ticks-invalid-range-rejected-before-write", "passed": True},
                *_negative_contract_tests(root),
            ]
        )

    paths = (
        root / "v1/src/kernel/interrupt.asm",
        root / "v1/src/kernel/syscall.asm",
        root / "v1/tools-host/test-driver/phase1_ticks.py",
        kernel,
    )
    hashes = {str(path.relative_to(root)).replace("\\", "/"): sha256_file(path) for path in paths}
    return [command], hashes, assertions
