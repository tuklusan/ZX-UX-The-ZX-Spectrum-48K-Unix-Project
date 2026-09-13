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
    """Raised when the P1.13 IM2/tick producer contract is violated."""


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


def _ordered_tokens(text: str, tokens: tuple[str, ...]) -> bool:
    """Match repeated tokens in sequence instead of reusing the first occurrence."""
    cursor = 0
    for token in tokens:
        position = text.find(token, cursor)
        if position < 0:
            return False
        cursor = position + len(token)
    return True


def _sys_ticks_snapshot_safe(syscall: str) -> bool:
    body = _block(syscall, "zx48_sys_ticks:", "zx48_sys_time_get:")
    return _ordered_tokens(
        body,
        (
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
            "ld hl,(syscall_arg_hl)",
            "xor a",
            "ret",
        ),
    )


def _cursor_producer_exact(interrupt: str) -> bool:
    expected = (
        "ld a,(cursor_blink_divider)\n"
        "    inc a\n"
        "    cp 25\n"
        "    jr c,zx48_interrupt_cursor_store\n"
        "    xor a\n"
        "zx48_interrupt_cursor_store:\n"
        "    ld (cursor_blink_divider),a\n"
        "    jr c,zx48_interrupt_wall\n"
        "    ld hl,cursor_service_parity\n"
        "    ld a,(hl)\n"
        "    xor 1\n"
        "    ld (hl),a\n"
        "zx48_interrupt_wall:"
    )
    return expected in interrupt


def _im2_cursor_mutation_absent(work: str) -> bool:
    forbidden = (
        "bitmap_start",
        "attr_start",
        "tty_row",
        "tty_col",
        "wrap_pending",
        "screen_mutation_depth",
        "cursor_phase",
        "cursor_drawn",
        "zx48_cursor_xor",
        "zx48_cursor_show",
        "zx48_cursor_hide",
    )
    return not any(token in work for token in forbidden)


def _source_contract(root: Path) -> list[dict[str, object]]:
    interrupt_raw = (root / "v1/src/kernel/interrupt.asm").read_text(encoding="utf-8")
    syscall_raw = (root / "v1/src/kernel/syscall.asm").read_text(encoding="utf-8")
    console_raw = (root / "v1/src/kernel/console.asm").read_text(encoding="utf-8")
    architecture = (root / "docs/01-ZX-UX-ARCHITECTURE-REV12.md").read_text(encoding="utf-8")
    interrupt = _strip_asm(interrupt_raw)
    syscall = _strip_asm(syscall_raw)
    console = _strip_asm(console_raw)
    work = _block(interrupt, "zx48_interrupt_work:", "    endm")
    handler = _block(interrupt, "zx48_interrupt:", "zx48_interrupt_work:")

    calls = re.findall(r"(?m)^\s*call\s+([a-z0-9_']+)", handler)
    forbidden_services = (
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
    return [
        {
            "name": "isr-call-edges-are-bounded",
            "passed": set(calls) <= {"zx48_kernel_stack_sample", "zx48_interrupt_work"}
            and calls.count("zx48_interrupt_work") == 2,
        },
        {
            "name": "isr-work-has-no-calls-or-forbidden-services",
            "passed": "call " not in work and not any(token in work for token in forbidden_services),
        },
        {
            "name": "tick-is-u32-modulo-increment",
            "passed": all(
                token in work
                for token in (
                    "ld hl,(kernel_ticks)\n    inc hl\n    ld (kernel_ticks),hl",
                    "ld hl,(kernel_ticks+2)\n    inc hl\n    ld (kernel_ticks+2),hl",
                    "ld a,h\n    or l\n    jr nz,zx48_interrupt_frames",
                )
            ),
        },
        {
            "name": "rom-frames-is-three-byte-carry-chain",
            "passed": "ld hl,rom_frames\n    inc (hl)" in work
            and "inc hl\n    inc (hl)" in work
            and work.count("jr nz,zx48_interrupt_timers") == 2,
        },
        {
            "name": "wake-flag-set-only",
            "passed": "ld a,1\n    ld (scheduler_tick_due),a" in work,
        },
        {
            "name": "cursor-producer-is-25-frame-one-bit-parity",
            "passed": _cursor_producer_exact(interrupt),
        },
        {
            "name": "cursor-parity-storage-is-one-byte-zero-initialized",
            "passed": "cursor_service_parity    equ console_state_base+7" in console
            and "ld (cursor_service_parity),a" in console,
        },
        {
            "name": "im2-never-mutates-cursor-bitmap-coordinate-wrap-or-depth",
            "passed": _im2_cursor_mutation_absent(work),
        },
        {
            "name": "wall-clock-update-is-validity-gated",
            "passed": _ordered_tokens(
                work,
                (
                    "ld a,(wall_valid)",
                    "ld a,(wall_subsecond)",
                    "cp zx48_pal_frame_hz",
                    "ld (wall_subsecond),a",
                ),
            ),
        },
        {
            "name": "break-sampling-is-minimal-matrix-io",
            "passed": all(
                token in work
                for token in ("ld bc,$fefe", "in a,(c)", "ld bc,$7ffe", "rrca", "ld (break_pending),a")
            ),
        },
        {
            "name": "both-isr-paths-run-producer-and-end-ei-reti",
            "passed": calls.count("zx48_interrupt_work") == 2 and handler.count("ei\n    reti") == 2,
        },
        {
            "name": "sys-ticks-snapshot-is-coherent-and-four-bytes",
            "passed": _sys_ticks_snapshot_safe(syscall),
        },
        {
            "name": "sys-ticks-independent-of-wall-time",
            "passed": all(token not in _block(syscall, "zx48_sys_ticks:", "zx48_sys_time_get:") for token in ("wall_valid", "wall_seconds", "wall_revision")),
        },
        {
            "name": "architecture-freezes-divider-parity-producer",
            "passed": "toggle the one-bit `cursor_service_parity`" in architecture
            and "IM2 performs no bitmap XOR" in architecture,
        },
    ]


def _negative_contract_tests(root: Path) -> list[dict[str, object]]:
    interrupt = _strip_asm((root / "v1/src/kernel/interrupt.asm").read_text(encoding="utf-8"))
    syscall = _strip_asm((root / "v1/src/kernel/syscall.asm").read_text(encoding="utf-8"))
    unsafe_syscall = syscall.replace("    di\n    ld de,(kernel_ticks)", "    ld de,(kernel_ticks)", 1)
    sticky_parity = interrupt.replace("    xor 1\n    ld (hl),a", "    ld a,1\n    ld (hl),a", 1)
    forbidden_mutation = interrupt.replace("zx48_interrupt_wall:", "    ld (tty_row),a\nzx48_interrupt_wall:", 1)
    return [
        {"name": "reject-torn-sys-ticks-snapshot", "passed": not _sys_ticks_snapshot_safe(unsafe_syscall)},
        {"name": "reject-sticky-cursor-due-flag-instead-of-parity", "passed": not _cursor_producer_exact(sticky_parity)},
        {
            "name": "reject-im2-coordinate-mutation",
            "passed": not _im2_cursor_mutation_absent(
                _block(forbidden_mutation, "zx48_interrupt_work:", "    endm")
            ),
        },
    ]


def _patch(kernel_bytes: bytes):
    def apply(ram: bytearray) -> None:
        start = phase1.KERNEL_BASE - 0x4000
        ram[start:start + len(kernel_bytes)] = kernel_bytes
    return apply


def _enable_one_im2_interrupt() -> bytes:
    return b"\x3E\xFE\xED\x47\xED\x5E\xFB\x76\xF3"


def _one_im2_path_runtime(root: Path, labels: dict[str, int], kernel_bytes: bytes, *, safe: bool) -> None:
    stack_init = labels["zx48_kernel_stack_init"]
    im2_init = labels["zx48_im2_init"]
    kernel_ticks = labels["kernel_ticks"]
    wall_seconds = labels["wall_seconds"]
    wall_revision = labels["wall_revision"]
    wall_subsecond = labels["wall_subsecond"]
    wall_valid = labels["wall_valid"]
    scheduler_tick_due = labels["scheduler_tick_due"]
    cursor_blink_divider = labels["cursor_blink_divider"]
    cursor_service_parity = labels["cursor_service_parity"]
    break_pending = labels["break_pending"]
    current_pid = labels["current_pid"]
    altreg_busy = labels["altreg_busy"]

    code = bytearray(b"\xF3\x31" + _word(phase1.USER_STACK) + _call(stack_init) + _call(im2_init))
    code += _store_bytes(kernel_ticks, (0, 0, 0, 0))
    code += _store_bytes(ROM_FRAMES, (0xFE, 0xFF, 0x12))
    code += _store_bytes(wall_seconds, (0xFF, 0xFF, 0x00, 0x00))
    code += _store_bytes(wall_revision, (0x34, 0x12))
    code += _store_byte(wall_subsecond, 49)
    code += _store_byte(wall_valid, 1)
    code += _store_byte(scheduler_tick_due, 0)
    code += _store_byte(cursor_blink_divider, 24)
    code += _store_byte(cursor_service_parity, 0)
    code += _store_byte(break_pending, 0)
    code += _store_byte(current_pid, 2)
    code += _store_byte(altreg_busy, 1 if safe else 0)
    code += _enable_one_im2_interrupt()
    code += _expect_bytes(kernel_ticks, (1, 0, 0, 0))
    code += _expect_bytes(ROM_FRAMES, (0xFF, 0xFF, 0x12))
    code += _expect_bytes(wall_seconds, (0x00, 0x00, 0x01, 0x00))
    code += _expect_bytes(wall_revision, (0x34, 0x12))
    code += _expect_byte(wall_subsecond, 0)
    code += _expect_byte(wall_valid, 1)
    code += _expect_byte(scheduler_tick_due, 1)
    code += _expect_byte(cursor_blink_divider, 0)
    code += _expect_byte(cursor_service_parity, 1)
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
    cursor_blink_divider = labels["cursor_blink_divider"]
    cursor_service_parity = labels["cursor_service_parity"]
    current_pid = labels["current_pid"]

    code = bytearray(b"\xF3\x31" + _word(phase1.USER_STACK) + _call(stack_init) + _call(im2_init))
    code += _store_bytes(kernel_ticks, (0xFF, 0xFF, 0xFF, 0xFF))
    code += _store_bytes(ROM_FRAMES, (0xFF, 0xFF, 0xFF))
    code += _store_bytes(wall_seconds, (0xEF, 0xBE, 0xAD, 0xDE))
    code += _store_byte(wall_subsecond, 49)
    code += _store_byte(wall_valid, 0)
    code += _store_byte(scheduler_tick_due, 0)
    code += _store_byte(cursor_blink_divider, 24)
    code += _store_byte(cursor_service_parity, 1)
    code += _store_byte(current_pid, 3)
    code += _enable_one_im2_interrupt()
    code += _expect_bytes(kernel_ticks, (0, 0, 0, 0))
    code += _expect_bytes(ROM_FRAMES, (0, 0, 0))
    code += _expect_bytes(wall_seconds, (0xEF, 0xBE, 0xAD, 0xDE))
    code += _expect_byte(wall_subsecond, 49)
    code += _expect_byte(wall_valid, 0)
    code += _expect_byte(scheduler_tick_due, 1)
    code += _expect_byte(cursor_blink_divider, 0)
    code += _expect_byte(cursor_service_parity, 0)
    code += _expect_byte(current_pid, 3)
    code += _jp(PASS_PC)
    run_sna(root, bytes(code), patch=_patch(kernel_bytes))


def _parity_intervals_runtime(root: Path, labels: dict[str, int], kernel_bytes: bytes, intervals: int) -> None:
    interrupt_work = labels["zx48_interrupt_work"]
    wall_valid = labels["wall_valid"]
    cursor_blink_divider = labels["cursor_blink_divider"]
    cursor_service_parity = labels["cursor_service_parity"]

    code = bytearray(b"\xF3\x31" + _word(phase1.USER_STACK))
    code += _store_byte(wall_valid, 0)
    code += _store_byte(cursor_blink_divider, 0)
    code += _store_byte(cursor_service_parity, 0)
    for _ in range(intervals * 25):
        code += _call(interrupt_work)
    code += _expect_byte(cursor_blink_divider, 0)
    code += _expect_byte(cursor_service_parity, intervals & 1)
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
    code += b"\x21\xFE\xFF" + bytes((0x3E, SYS_TICKS)) + _call(phase1.KERNEL_BASE) + b"\xF3" + _jp_nc(FAIL_PC)
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


def _parity_handoff_model() -> list[dict[str, object]]:
    # The future safe consumer owns an interrupt-excluded fetch-and-clear window.
    # Posts before it are consumed now; posts after EI remain pending for the next
    # opportunity; two unserviced transitions cancel by parity rather than replay.
    parity = 0
    parity ^= 1
    consumed_before = parity
    parity = 0
    before_ok = consumed_before == 1 and parity == 0

    parity = 0
    consumed_inside = parity
    parity = 0
    parity ^= 1  # attempted in-window frame is observed only after exclusion ends
    inside_ok = consumed_inside == 0 and parity == 1

    parity = 0
    consumed_after = parity
    parity = 0
    parity ^= 1
    after_ok = consumed_after == 0 and parity == 1

    parity = 0
    parity ^= 1
    parity ^= 1
    even_ok = parity == 0
    return [
        {"name": "parity-post-before-consume-is-consumed-once", "passed": before_ok},
        {"name": "parity-post-during-exclusion-belongs-to-next-service", "passed": inside_ok},
        {"name": "parity-post-after-consume-is-not-erased", "passed": after_ok},
        {"name": "two-delayed-transitions-coalesce-to-even-parity", "passed": even_ok},
    ]


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

    assertions = _source_contract(root) + _parity_handoff_model()
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
            "cursor_blink_divider",
            "cursor_service_parity",
            "break_pending",
            "current_pid",
            "altreg_busy",
        ),
    )
    kernel_bytes = kernel.read_bytes()

    if action == "test":
        _one_im2_path_runtime(root, labels, kernel_bytes, safe=False)
        _one_im2_path_runtime(root, labels, kernel_bytes, safe=True)
        _wrap_runtime(root, labels, kernel_bytes)
        for intervals in (1, 2, 3, 4):
            _parity_intervals_runtime(root, labels, kernel_bytes, intervals)
        _sys_ticks_runtime(root, labels, kernel_bytes)
        assertions.extend(
            [
                {"name": "fast-im2-path-runs-producer-exactly-once", "passed": True},
                {"name": "rom-safe-im2-path-runs-producer-exactly-once", "passed": True},
                {"name": "u32-tick-and-rom-frames-wrap-exact", "passed": True},
                {"name": "wall-clock-invalid-state-is-untouched", "passed": True},
                {"name": "wall-clock-valid-50hz-carry-is-exact", "passed": True},
                {"name": "cursor-delays-1-2-3-4-produce-parity-1-0-1-0", "passed": True},
                {"name": "sys-ticks-four-byte-little-endian-sentinel", "passed": True},
                {"name": "sys-ticks-invalid-range-rejected", "passed": True},
                *_negative_contract_tests(root),
                _double_accounting_negative(root, labels, kernel_bytes),
            ]
        )
        failed = [str(item["name"]) for item in assertions if item["passed"] is not True]
        require(not failed, f"P1.13 runtime/negative tick failures: {failed}")

    paths = (
        root / "v1/src/kernel/interrupt.asm",
        root / "v1/src/kernel/syscall.asm",
        root / "v1/src/kernel/console.asm",
        root / "v1/src/kernel/im2.asm",
        root / "docs/01-ZX-UX-ARCHITECTURE-REV12.md",
        root / "v1/tools-host/test-driver/phase1_ticks.py",
        kernel,
    )
    hashes = {str(path.relative_to(root)).replace("\\", "/"): sha256_file(path) for path in paths}
    return [command], hashes, assertions
