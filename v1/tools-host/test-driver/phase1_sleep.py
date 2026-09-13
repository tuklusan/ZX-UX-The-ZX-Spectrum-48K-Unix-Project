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

BUF = 0x7000
PROC_DESC_SIZE = 48
PROC_STATE = 2
PROC_WAKE_TICK = 24
PROC_READY = 1
PROC_RUNNING = 2
PROC_SLEEPING = 3
E_INVAL = 1


class Phase1SleepError(DriverError):
    """Raised when the P1.18 relative-tick sleep contract is violated."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Phase1SleepError(message)


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


def _store_u32(address: int, value: int) -> bytes:
    return b"".join(_store_byte(address + n, (value >> (8 * n)) & 0xFF) for n in range(4))


def _expect_byte(address: int, value: int) -> bytes:
    return b"\x3A" + _word(address) + bytes((0xFE, value & 0xFF)) + _jp_nz(FAIL_PC)


def _expect_u32(address: int, value: int) -> bytes:
    return b"".join(_expect_byte(address + n, (value >> (8 * n)) & 0xFF) for n in range(4))


def _ld_hl(value: int) -> bytes:
    return b"\x21" + _word(value)


def _ld_ix(value: int) -> bytes:
    return b"\xDD\x21" + _word(value)


def _strip(text: str) -> str:
    return "\n".join(line.split(";", 1)[0].rstrip().lower() for line in text.splitlines())


def _block(text: str, start: str, end: str) -> str:
    lowered = text.lower()
    first = lowered.find(start.lower())
    last = lowered.find(end.lower(), first + len(start))
    require(0 <= first < last, f"missing source block {start}..{end}")
    return lowered[first:last]


def _ordered(text: str, tokens: tuple[str, ...]) -> bool:
    pos = 0
    for token in tokens:
        pos = text.find(token, pos)
        if pos < 0:
            return False
        pos += len(token)
    return True


def _source_contract_from(syscall_raw: str, scheduler_raw: str) -> bool:
    syscall = _strip(syscall_raw)
    scheduler = _strip(scheduler_raw)
    sys_sleep = _block(syscall, "zx48_sys_sleep:", "zx48_sys_getpid:")
    sleep = _block(scheduler, "zx48_sleep_current:", "zx48_scheduler_wake_scan:")
    wake = _block(scheduler, "zx48_scheduler_maybe_wake:", "zx48_sleep_current:")
    return (
        _ordered(
            sys_sleep,
            (
                "ld hl,(syscall_arg_hl)",
                "ld bc,4",
                "call zx48_user_range_validate",
                "ret c",
                "ld hl,(syscall_arg_hl)",
                "call zx48_sleep_current",
            ),
        )
        and _ordered(
            sleep,
            (
                "bit 7,b",
                "jr nz,zx48_sleep_bad",
                "ld a,b",
                "or c",
                "or d",
                "or e",
                "jr z,zx48_sleep_zero",
                "ld hl,(kernel_ticks)",
                "add hl,de",
                "ld (ix+proc_wake_tick),l",
                "ld (ix+proc_wake_tick+1),h",
                "ld hl,(kernel_ticks+2)",
                "adc hl,de",
                "ld (ix+proc_wake_tick+2),l",
                "ld (ix+proc_wake_tick+3),h",
                "ld (ix+proc_state),proc_sleeping",
                "jp zx48_schedule_finish_syscall",
            ),
        )
        and _ordered(
            wake,
            (
                "ld hl,(kernel_ticks)",
                "sbc hl,de",
                "ld hl,(kernel_ticks+2)",
                "sbc hl,de",
                "bit 7,h",
                "ret nz",
                "ld (ix+proc_state),proc_ready",
            ),
        )
    )


def _source_contract(root: Path) -> list[dict[str, object]]:
    syscall = (root / "v1/src/kernel/syscall.asm").read_text(encoding="utf-8")
    scheduler = (root / "v1/src/kernel/scheduler.asm").read_text(encoding="utf-8")
    return [
        {
            "name": "sys-sleep-is-prevalidated-relative-u32-with-wrap-safe-wake",
            "passed": _source_contract_from(syscall, scheduler),
        }
    ]


def _negative_contracts(root: Path) -> list[dict[str, object]]:
    syscall = (root / "v1/src/kernel/syscall.asm").read_text(encoding="utf-8")
    scheduler = (root / "v1/src/kernel/scheduler.asm").read_text(encoding="utf-8")
    no_top_bit = scheduler.replace("    bit 7,b\n    jr nz,zx48_sleep_bad\n", "", 1)
    absolute = scheduler.replace(
        "    ld hl,(kernel_ticks)\n    ld de,(scheduler_sleep_lo)\n    add hl,de",
        "    ld hl,(scheduler_sleep_lo)\n    ld de,0\n    add hl,de",
        1,
    )
    early = scheduler.replace("    bit 7,h\n    ret nz", "    bit 7,h\n    ret z", 1)
    unvalidated = syscall.replace("    ld bc,4\n    call zx48_user_range_validate\n    ret c\n", "", 1)
    return [
        {"name": "reject-top-bit-relative-count", "passed": not _source_contract_from(syscall, no_top_bit)},
        {"name": "reject-absolute-target-interpretation", "passed": not _source_contract_from(syscall, absolute)},
        {"name": "reject-one-tick-early-wake-logic", "passed": not _source_contract_from(syscall, early)},
        {"name": "reject-unvalidated-sleep-pointer", "passed": not _source_contract_from(unvalidated, scheduler)},
    ]


def _kernel_patch(kernel_bytes: bytes, schedule_finish: int):
    patched = bytearray(kernel_bytes)
    offset = schedule_finish - phase1.KERNEL_BASE
    require(0 <= offset < len(patched), "schedule-finish label outside kernel")
    patched[offset] = 0xC9
    return phase1._kernel_patch(bytes(patched))


def _sleep_vector(
    root: Path,
    labels: dict[str, int],
    kernel_bytes: bytes,
    *,
    now: int,
    relative: int,
    expect_carry: bool,
    expected_state: int,
    expected_wake: int | None,
) -> None:
    table = labels["process_table"]
    p1 = table + PROC_DESC_SIZE
    code = bytearray(b"\xF3" + phase1._ld_sp(phase1.USER_STACK))
    code += _call(labels["zx48_kernel_stack_init"])
    code += _call(labels["zx48_process_init"])
    code += _call(labels["zx48_process_prepare_pid1"])
    code += _store_byte(labels["current_pid"], 1)
    code += _store_byte(p1 + PROC_STATE, PROC_RUNNING)
    code += _store_u32(labels["kernel_ticks"], now)
    code += _store_u32(BUF, relative)
    code += _ld_hl(BUF) + _call(labels["zx48_sleep_current"])
    if expect_carry:
        code += _jp_nc(FAIL_PC) + b"\xFE" + bytes((E_INVAL,)) + _jp_nz(FAIL_PC)
    else:
        code += _jp_c(FAIL_PC)
    code += _expect_byte(p1 + PROC_STATE, expected_state)
    if expected_wake is not None:
        code += _expect_u32(p1 + PROC_WAKE_TICK, expected_wake)
    code += _jp(PASS_PC)
    run_sna(
        root,
        bytes(code),
        patch=_kernel_patch(kernel_bytes, labels["zx48_schedule_finish_syscall"]),
    )


def _wake_boundary(root: Path, labels: dict[str, int], kernel_bytes: bytes, *, deadline: int) -> None:
    table = labels["process_table"]
    p1 = table + PROC_DESC_SIZE
    code = bytearray(b"\xF3" + phase1._ld_sp(phase1.USER_STACK))
    code += _call(labels["zx48_kernel_stack_init"])
    code += _call(labels["zx48_process_init"])
    code += _call(labels["zx48_process_prepare_pid1"])
    code += _store_u32(p1 + PROC_WAKE_TICK, deadline)
    code += _store_byte(p1 + PROC_STATE, PROC_SLEEPING)
    code += _store_u32(labels["kernel_ticks"], (deadline - 1) & 0xFFFFFFFF)
    code += _ld_ix(p1) + _call(labels["zx48_scheduler_maybe_wake"])
    code += _expect_byte(p1 + PROC_STATE, PROC_SLEEPING)
    code += _store_u32(labels["kernel_ticks"], deadline)
    code += _ld_ix(p1) + _call(labels["zx48_scheduler_maybe_wake"])
    code += _expect_byte(p1 + PROC_STATE, PROC_READY)
    code += _jp(PASS_PC)
    run_sna(root, bytes(code), patch=phase1._kernel_patch(kernel_bytes))


def _run_stage(name: str, thunk: Callable[[], None]) -> None:
    try:
        thunk()
    except DriverError as exc:
        raise Phase1SleepError(f"P1.18 runtime stage {name} failed: {exc}") from exc


def dispatch(
    root: Path,
    action: str,
    step: str,
    *,
    sha256_file: Callable[[Path], str],
    run_command: Callable[..., Any],
    require_project_tool: Callable[[Path, str | Path], Path],
):
    if step != "P1.18":
        raise Phase1SleepError(f"sleep step is not registered: {step}")

    assertions = _source_contract(root)
    failed = [a["name"] for a in assertions if a["passed"] is not True]
    require(not failed, f"static P1.18 failures: {failed}")

    command, kernel, listing = phase1._assemble_kernel(root, run_command, require_project_tool)
    labels = phase1._labels(
        listing,
        (
            "zx48_kernel_stack_init",
            "zx48_process_init",
            "zx48_process_prepare_pid1",
            "zx48_sleep_current",
            "zx48_scheduler_maybe_wake",
            "zx48_schedule_finish_syscall",
            "process_table",
            "current_pid",
            "kernel_ticks",
        ),
    )
    kernel_bytes = kernel.read_bytes()

    if action == "test":
        stages = (
            ("zero", lambda: _sleep_vector(root, labels, kernel_bytes, now=0x12345678, relative=0, expect_carry=False, expected_state=PROC_RUNNING, expected_wake=None)),
            ("one", lambda: _sleep_vector(root, labels, kernel_bytes, now=0x12345678, relative=1, expect_carry=False, expected_state=PROC_SLEEPING, expected_wake=0x12345679)),
            ("max-positive", lambda: _sleep_vector(root, labels, kernel_bytes, now=0x00000001, relative=0x7FFFFFFF, expect_carry=False, expected_state=PROC_SLEEPING, expected_wake=0x80000000)),
            ("wrap", lambda: _sleep_vector(root, labels, kernel_bytes, now=0xFFFFFFFE, relative=3, expect_carry=False, expected_state=PROC_SLEEPING, expected_wake=1)),
            ("reject-80000000", lambda: _sleep_vector(root, labels, kernel_bytes, now=0x11223344, relative=0x80000000, expect_carry=True, expected_state=PROC_RUNNING, expected_wake=None)),
            ("reject-ffffffff", lambda: _sleep_vector(root, labels, kernel_bytes, now=0x11223344, relative=0xFFFFFFFF, expect_carry=True, expected_state=PROC_RUNNING, expected_wake=None)),
            ("wake-boundary", lambda: _wake_boundary(root, labels, kernel_bytes, deadline=0x00000001)),
        )
        for name, thunk in stages:
            _run_stage(name, thunk)
        assertions.extend(_negative_contracts(root))
        assertions.extend(
            [
                {"name": "relative-zero-one-max-and-wrap-vectors-pass", "passed": True},
                {"name": "invalid-top-bit-vectors-are-atomic", "passed": True},
                {"name": "wake-occurs-at-deadline-not-one-tick-early", "passed": True},
            ]
        )

    paths = (
        root / "v1/src/kernel/scheduler.asm",
        root / "v1/src/kernel/syscall.asm",
        root / "v1/tools-host/test-driver/phase1_sleep.py",
        kernel,
    )
    return [command], {str(path.relative_to(root)): sha256_file(path) for path in paths}, assertions
