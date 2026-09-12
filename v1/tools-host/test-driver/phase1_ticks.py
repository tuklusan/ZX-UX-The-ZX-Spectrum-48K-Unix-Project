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
from fuse_harness import FAIL_PC, PASS_PC, run_sna
import phase1

SYS_TICKS = 0x62
ROM_FRAMES = 0x5C78
TICK_BUFFER = 0x7000
IX_MAGIC = 0x1357


class Phase1TicksError(DriverError):
    """Raised when the P1.13 IM2/tick contract is violated."""


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


def _jp_nz(address: int) -> bytes:
    return b"\xC2" + _word(address)


def _store_byte(address: int, value: int) -> bytes:
    return bytes((0x3E, value & 0xFF, 0x32)) + _word(address)


def _expect_byte(address: int, value: int) -> bytes:
    return b"\x3A" + _word(address) + bytes((0xFE, value & 0xFF)) + _jp_nz(FAIL_PC)


def _store_bytes(address: int, values: tuple[int, ...]) -> bytes:
    return b"".join(_store_byte(address + offset, value) for offset, value in enumerate(values))


def _expect_bytes(address: int, values: tuple[int, ...]) -> bytes:
    return b"".join(_expect_byte(address + offset, value) for offset, value in enumerate(values))


def _strip_asm(text: str) -> str:
    return "\n".join(line.split(";", 1)[0].rstrip().lower() for line in text.splitlines())


def _block(text: str, start: str, end: str) -> str:
    lower = text.lower()
    first = lower.find(start.lower())
    last = lower.find(end.lower(), first + len(start))
    require(0 <= first < last, f"source block missing: {start}..{end}")
    return lower[first:last]


def _cursor_cadence_exact(interrupt: str) -> bool:
    expected = (
        "ld a,(cursor_frame_count)\n"
        "    inc a\n"
        "    cp 25\n"
        "    jr c,zx48_interrupt_cursor_store\n"
        "    xor a\n"
        "    ld (cursor_frame_count),a\n"
        "    inc a\n"
        "    ld (tty_cursor_due),a\n"
        "    jr zx48_interrupt_wall\n"
        "zx48_interrupt_cursor_store:\n"
        "    ld (cursor_frame_count),a\n"
        "zx48_interrupt_wall:"
    )
    return expected in interrupt


def _sys_ticks_snapshot_safe(syscall: str) -> bool:
    body = _block(syscall, "zx48_sys_ticks:", "zx48_sys_time_get:")
    ordered = (
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
        "ld hl,(syscall_arg_hl)",
        "xor a",
        "ret",
    )
    positions = [body.find(token) for token in ordered]
    return all(position >= 0 for position in positions) and positions == sorted(positions)


def _source_contract(root: Path) -> list[dict[str, object]]:
    interrupt_raw = (root / "v1/src/kernel/interrupt.asm").read_text(encoding="utf-8")
    syscall_raw = (root / "v1/src/kernel/syscall.asm").read_text(encoding="utf-8")
    architecture = (root / "docs/01-ZX-UX-ARCHITECTURE-REV11.md").read_text(encoding="utf-8")
    interrupt = _strip_asm(interrupt_raw)
    syscall = _strip_asm(syscall_raw)
    work = _block(interrupt, "zx48_interrupt_work:", "    endm")
    handler = _block(interrupt, "zx48_interrupt:", "zx48_interrupt_work:")

    calls = re.findall(r"(?m)^\s*call\s+([a-z0-9_']+)", handler)
    forbidden = (
        "zx48_schedule",
        "zx48_alloc",
        "zx48_free",
        "zx48_console",
        "zx48_keyboard_decode",
        "zx48_keyboard_getkey",
        "zx48_rom_",
        "zx48_tape",
        "zx48_pipe",
        "zx48_process_exit",
    )
    tick_sequence = (
        "ld hl,(kernel_ticks)\n    inc hl\n    ld (kernel_ticks),hl",
        "ld hl,(kernel_ticks+2)\n    inc hl\n    ld (kernel_ticks+2),hl",
    )
    frames_sequence = (
        "ld hl,rom_frames\n    inc (hl)",
        "inc hl\n    inc (hl)",
    )
    wall_sequence = (
        "ld a,(wall_valid)",
        "ld a,(wall_subsecond)",
        "cp zx48_pal_frame_hz",
        "ld (wall_subsecond),a",
        "ld hl,(wall_seconds)",
        "ld hl,(wall_seconds+2)",
    )

    return [
        {
            "name": "isr-call-edges-are-bounded",
            "passed": set(calls) <= {"zx48_kernel_stack_sample", "zx48_interrupt_work"}
            and calls.count("zx48_interrupt_work") == 2,
        },
        {
            "name": "isr-work-has-no-calls-or-forbidden-services",
            "passed": "call " not in work and not any(token in work for token in forbidden),
        },
        {
            "name": "tick-is-u32-modulo-increment",
            "passed": all(token in work for token in tick_sequence)
            and "ld a,h\n    or l\n    jr nz,zx48_interrupt_frames" in work,
        },
        {
            "name": "rom-frames-is-three-byte-carry-chain",
            "passed": all(token in work for token in frames_sequence)
            and work.count("jr nz,zx48_interrupt_timers") == 2,
        },
        {
            "name": "wake-flag-set-only",
            "passed": "ld a,1\n    ld (scheduler_tick_due),a" in work,
        },
        {
            "name": "cursor-period-is-exactly-25-frames",
            "passed": _cursor_cadence_exact(interrupt),
        },
        {
            "name": "wall-clock-update-is-validity-gated",
            "passed": all(token in work for token in wall_sequence)
            and work.find("ld a,(wall_valid)") < work.find("ld a,(wall_subsecond)"),
        },
        {
            "name": "break-sampling-is-minimal-matrix-io",
            "passed": all(token in work for token in ("ld bc,$fefe", "in a,(c)", "ld bc,$7ffe", "bit 0,a", "ld (break_pending),a")),
        },
        {
            "name": "both-isr-paths-end-ei-reti",
            "passed": handler.count("ei\n    reti") == 2,
        },
        {
            "name": "sys-ticks-snapshot-is-coherent-and-four-bytes",
            "passed": _sys_ticks_snapshot_safe(syscall),
        },
        {
            "name": "architecture-cursor-target-is-25-frames",
            "passed": "Blink period target is 25 UK 50-Hz frames" in architecture,
        },
    ]


def _negative_contract_tests(root: Path) -> list[dict[str, object]]:
    interrupt_raw = (root / "v1/src/kernel/interrupt.asm").read_text(encoding="utf-8")
    syscall_raw = (root / "v1/src/kernel/syscall.asm").read_text(encoding="utf-8")
    interrupt = _strip_asm(interrupt_raw)
    syscall = _strip_asm(syscall_raw)

    unsafe_syscall = syscall.replace("    di\n    ld de,(kernel_ticks)", "    ld de,(kernel_ticks)", 1)
    wrong_cursor = interrupt.replace(
        "    ld (cursor_frame_count),a\n    inc a\n    ld (tty_cursor_due),a\n    jr zx48_interrupt_wall",
        "    inc a\n    ld (tty_cursor_due),a\n    jr zx48_interrupt_cursor_store",
        1,
    )
    return [
        {"name": "reject-torn-sys-ticks-snapshot", "passed": not _sys_ticks_snapshot_safe(unsafe_syscall)},
        {"name": "reject-24-frame-post-first-cursor-period", "passed": not _cursor_cadence_exact(wrong_cursor)},
    ]


def _patch(kernel_bytes: bytes):
    def apply(ram: bytearray) -> None:
        start = phase1.KERNEL_BASE - 0x4000
        ram[start:start + len(kernel_bytes)] = kernel_bytes
    return apply


def _enable_one_im2_interrupt() -> bytes:
    return b"\x3E\xFE\xED\x47\xED\x5E\xFB\x76\xF3"


def _one_interrupt_runtime(root: Path, labels: dict[str, int], kernel_bytes: bytes) -> None:
    stack_init = labels["zx48_kernel_stack_init"]
    im2_init = labels["zx48_im2_init"]
    kernel_ticks = labels["kernel_ticks"]
    wall_seconds = labels["wall_seconds"]
    wall_revision = labels["wall_revision"]
    wall_subsecond = labels["wall_subsecond"]
    wall_valid = labels["wall_valid"]
    scheduler_tick_due = labels["scheduler_tick_due"]
    cursor_frame_count = labels["cursor_frame_count"]
    tty_cursor_due = labels["tty_cursor_due"]
    break_pending = labels["break_pending"]
    current_pid = labels["current_pid"]

    code = bytearray(b"\xF3\x31" + _word(phase1.USER_STACK) + _call(stack_init) + _call(im2_init))
    code += _store_bytes(kernel_ticks, (0, 0, 0, 0))
    code += _store_bytes(ROM_FRAMES, (0xFE, 0xFF, 0x12))
    code += _store_bytes(wall_seconds, (0xFF, 0xFF, 0x00, 0x00))
    code += _store_bytes(wall_revision, (0x34, 0x12))
    code += _store_byte(wall_subsecond, 49)
    code += _store_byte(wall_valid, 1)
    code += _store_byte(scheduler_tick_due, 0)
    code += _store_byte(cursor_frame_count, 24)
    code += _store_byte(tty_cursor_due, 0)
    code += _store_byte(break_pending, 0)
    code += _store_byte(current_pid, 2)
    code += _enable_one_im2_interrupt()
    code += _expect_bytes(kernel_ticks, (1, 0, 0, 0))
    code += _expect_bytes(ROM_FRAMES, (0xFF, 0xFF, 0x12))
    code += _expect_bytes(wall_seconds, (0x00, 0x00, 0x01, 0x00))
    code += _expect_bytes(wall_revision, (0x34, 0x12))
    code += _expect_byte(wall_subsecond, 0)
    code += _expect_byte(wall_valid, 1)
    code += _expect_byte(scheduler_tick_due, 1)
    code += _expect_byte(cursor_frame_count, 0)
    code += _expect_byte(tty_cursor_due, 1)
    code += _expect_byte(break_pending, 0)
    code += _expect_byte(current_pid, 2)
    code += _jp(PASS_PC)
    run_sna(root, bytes(code), patch=_patch(kernel_bytes))


def _wrap_runtime(root: Path, labels: dict[str, int], kernel_bytes: bytes) -> None:
    stack_init = labels["zx48_kernel_stack_init"]
    im2_init = labels["zx48_im2_init"]
    kernel_ticks = labels["kernel_ticks"]
    wall_seconds = labels["wall_seconds"]
    wall_subsecond = labels["wall_subsecond"]
    wall_valid = labels["wall_valid"]
    scheduler_tick_due = labels["scheduler_tick_due"]
    cursor_frame_count = labels["cursor_frame_count"]
    tty_cursor_due = labels["tty_cursor_due"]
    current_pid = labels["current_pid"]

    code = bytearray(b"\xF3\x31" + _word(phase1.USER_STACK) + _call(stack_init) + _call(im2_init))
    code += _store_bytes(kernel_ticks, (0xFF, 0xFF, 0xFF, 0xFF))
    code += _store_bytes(ROM_FRAMES, (0xFF, 0xFF, 0xFF))
    code += _store_bytes(wall_seconds, (0xEF, 0xBE, 0xAD, 0xDE))
    code += _store_byte(wall_subsecond, 49)
    code += _store_byte(wall_valid, 0)
    code += _store_byte(scheduler_tick_due, 0)
    code += _store_byte(cursor_frame_count, 0)
    code += _store_byte(tty_cursor_due, 0)
    code += _store_byte(current_pid, 3)
    code += _enable_one_im2_interrupt()
    code += _expect_bytes(kernel_ticks, (0, 0, 0, 0))
    code += _expect_bytes(ROM_FRAMES, (0, 0, 0))
    code += _expect_bytes(wall_seconds, (0xEF, 0xBE, 0xAD, 0xDE))
    code += _expect_byte(wall_subsecond, 49)
    code += _expect_byte(wall_valid, 0)
    code += _expect_byte(scheduler_tick_due, 1)
    code += _expect_byte(cursor_frame_count, 1)
    code += _expect_byte(tty_cursor_due, 0)
    code += _expect_byte(current_pid, 3)
    code += _jp(PASS_PC)
    run_sna(root, bytes(code), patch=_patch(kernel_bytes))


def _cursor_25_runtime(root: Path, labels: dict[str, int], kernel_bytes: bytes) -> None:
    interrupt_work = labels["zx48_interrupt_work"]
    kernel_ticks = labels["kernel_ticks"]
    wall_valid = labels["wall_valid"]
    cursor_frame_count = labels["cursor_frame_count"]
    tty_cursor_due = labels["tty_cursor_due"]

    code = bytearray(b"\xF3\x31" + _word(phase1.USER_STACK))
    code += _store_bytes(kernel_ticks, (0, 0, 0, 0))
    code += _store_byte(wall_valid, 0)
    code += _store_byte(cursor_frame_count, 0)
    code += _store_byte(tty_cursor_due, 0)
    for _ in range(24):
        code += _call(interrupt_work)
    code += _expect_byte(cursor_frame_count, 24)
    code += _expect_byte(tty_cursor_due, 0)
    code += _call(interrupt_work)
    code += _expect_byte(cursor_frame_count, 0)
    code += _expect_byte(tty_cursor_due, 1)
    code += _jp(PASS_PC)
    run_sna(root, bytes(code), patch=_patch(kernel_bytes))


def _sys_ticks_runtime(root: Path, labels: dict[str, int], kernel_bytes: bytes) -> None:
    stack_init = labels["zx48_kernel_stack_init"]
    kernel_ticks = labels["kernel_ticks"]

    code = bytearray(b"\xF3\x31" + _word(phase1.USER_STACK) + _call(stack_init))
    code += _store_bytes(kernel_ticks, (0x78, 0x56, 0x34, 0x12))
    code += _store_bytes(TICK_BUFFER, (0xAA, 0xAA, 0xAA, 0xAA, 0x5A))
    code += b"\xDD\x21" + _word(IX_MAGIC)
    code += b"\xFD\x21\x68\x24"
    code += b"\x21" + _word(TICK_BUFFER) + bytes((0x3E, SYS_TICKS)) + _call(phase1.KERNEL_BASE) + b"\xF3"
    code += _jp_c(FAIL_PC)
    code += b"\xB7" + _jp_nz(FAIL_PC)
    code += _expect_bytes(TICK_BUFFER, (0x78, 0x56, 0x34, 0x12, 0x5A))
    code += b"\xDD\xE5\xE1\x11" + _word(IX_MAGIC) + b"\xB7\xED\x52" + _jp_nz(FAIL_PC)
    code += b"\xFD\xE5\xE1\x11\x3A\x5C\xB7\xED\x52" + _jp_nz(FAIL_PC)
    code += _jp(PASS_PC)
    run_sna(root, bytes(code), patch=_patch(kernel_bytes))


def _double_accounting_negative(root: Path, labels: dict[str, int], kernel_bytes: bytes) -> dict[str, object]:
    interrupt_work = labels["zx48_interrupt_work"]
    kernel_ticks = labels["kernel_ticks"]
    wall_valid = labels["wall_valid"]
    code = bytearray(b"\xF3\x31" + _word(phase1.USER_STACK))
    code += _store_bytes(kernel_ticks, (0, 0, 0, 0))
    code += _store_byte(wall_valid, 0)
    code += _call(interrupt_work) + _call(interrupt_work)
    code += _expect_byte(kernel_ticks, 1)
    code += _jp(PASS_PC)
    try:
        run_sna(root, bytes(code), patch=_patch(kernel_bytes))
    except DriverError:
        return {"name": "reject-double-interrupt-accounting", "passed": True}
    return {"name": "reject-double-interrupt-accounting", "passed": False}


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

    assertions = _source_contract(root)
    failed = [str(item["name"]) for item in assertions if item["passed"] is not True]
    require(not failed, f"P1.13 static tick/IM2 failures: {failed}")

    command, kernel, listing = phase1._assemble_kernel(root, run_command, require_project_tool)
    labels = phase1._labels(
        listing,
        (
            "zx48_kernel_stack_init",
            "zx48_im2_init",
            "zx48_interrupt_work",
            "kernel_ticks",
            "wall_seconds",
            "wall_revision",
            "wall_subsecond",
            "wall_valid",
            "scheduler_tick_due",
            "cursor_frame_count",
            "tty_cursor_due",
            "break_pending",
            "current_pid",
        ),
    )
    kernel_bytes = kernel.read_bytes()

    if action == "test":
        _one_interrupt_runtime(root, labels, kernel_bytes)
        _wrap_runtime(root, labels, kernel_bytes)
        _cursor_25_runtime(root, labels, kernel_bytes)
        _sys_ticks_runtime(root, labels, kernel_bytes)
        assertions.extend(
            [
                {"name": "accepted-im2-updates-bounded-state-once", "passed": True},
                {"name": "u32-tick-and-rom-frames-wrap-exact", "passed": True},
                {"name": "wall-clock-invalid-state-is-untouched", "passed": True},
                {"name": "wall-clock-valid-50hz-carry-is-exact", "passed": True},
                {"name": "cursor-due-on-exact-25th-frame", "passed": True},
                {"name": "sys-ticks-four-byte-little-endian-sentinel", "passed": True},
                *_negative_contract_tests(root),
                _double_accounting_negative(root, labels, kernel_bytes),
            ]
        )
        failed = [str(item["name"]) for item in assertions if item["passed"] is not True]
        require(not failed, f"P1.13 runtime/negative tick failures: {failed}")

    paths = (
        root / "v1/src/kernel/interrupt.asm",
        root / "v1/src/kernel/syscall.asm",
        root / "v1/src/kernel/im2.asm",
        root / "docs/01-ZX-UX-ARCHITECTURE-REV11.md",
        root / "v1/tools-host/test-driver/phase1_ticks.py",
        kernel,
    )
    hashes = {str(path.relative_to(root)).replace("\\", "/"): sha256_file(path) for path in paths}
    return [command], hashes, assertions
