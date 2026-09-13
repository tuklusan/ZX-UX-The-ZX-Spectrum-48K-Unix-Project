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


class ConsoleCoreError(DriverError):
    """Raised when the deferred-wrap console core contract is violated."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ConsoleCoreError(message)


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


def _putchar(address: int, value: int) -> bytes:
    return bytes((0x3E, value & 0xFF)) + _call(address) + _jp_c(FAIL_PC)


def _source_contract(root: Path) -> list[dict[str, object]]:
    console = (root / "v1/src/kernel/console.asm").read_text(encoding="utf-8").lower()
    control_block = console[console.index("zx48_console_control_begin:"):console.index("; hl=buffer")]
    return [
        {"name": "private-wrap-pending-state-exists", "passed": "tty_wrap_pending" in console},
        {"name": "cold-init-clears-pending", "passed": "ld (tty_wrap_pending),a" in console[console.index("zx48_console_init:"):console.index("zx48_console_clear:")]},
        {"name": "printable-preserved-before-cursor-work", "passed": "zx48_console_print:\n    push af\n    call zx48_cursor_hide" in console},
        {"name": "pending-wrap-is-resolved-before-draw", "passed": "call nz,zx48_console_wrap_now" in console and console.index("call nz,zx48_console_wrap_now") < console.index("call zx48_tty32_draw_char")},
        {"name": "last-real-cell-sets-pending", "passed": "zx48_console_set_pending:" in console and "ld (tty_wrap_pending),a" in console[console.index("zx48_console_set_pending:"):console.index("zx48_console_wrap_now:")]},
        {"name": "mode-value-derives-last-real-column", "passed": "ld a,(tty_mode)\n    dec a\n    ld b,a\n    ld a,(tty_col)\n    cp b" in console},
        {"name": "moving-controls-clear-pending", "passed": "ld (tty_wrap_pending),a" in control_block and all(f"call zx48_console_control_begin" in console[console.index(label):console.index(label) + 100] for label in ("zx48_console_lf:", "zx48_console_cr:", "zx48_console_bs:", "zx48_console_tab:"))},
        {"name": "setpos-validates-before-mutation", "passed": console.index("zx48_console_set_commit:") > console.index("cp 64") and "ld (tty_wrap_pending),a" in console[console.index("zx48_console_set_commit:"):console.index("zx48_console_bad:")]},
        {"name": "no-persistent-phantom-coordinate", "passed": "cp 32\n    jr c,zx48_console_store_col" not in console and "cp 64\n    jr c,zx48_console_store_col" not in console},
    ]


def _state_matrix(root: Path, labels: dict[str, int], kernel: bytes) -> None:
    init = labels["zx48_console_init"]
    putchar = labels["zx48_console_putchar"]
    mode = labels["tty_mode"]
    row = labels["tty_row"]
    col = labels["tty_col"]
    shape = labels["tty_cursor_shape"]
    pending = labels["tty_wrap_pending"]

    code = bytearray(b"\xF3" + phase1._ld_sp(phase1.USER_STACK))
    code += _call(init)
    code += _store_byte(mode, 32) + _store_byte(shape, 0)

    code += _store_byte(row, 0) + _store_byte(col, 30) + _store_byte(pending, 0)
    code += _putchar(putchar, 0x41)
    code += _expect_byte(row, 0) + _expect_byte(col, 31) + _expect_byte(pending, 0)
    code += _putchar(putchar, 0x42)
    code += _expect_byte(row, 0) + _expect_byte(col, 31) + _expect_byte(pending, 1)
    code += _putchar(putchar, 0x43)
    code += _expect_byte(row, 1) + _expect_byte(col, 1) + _expect_byte(pending, 0)

    code += _store_byte(row, 23) + _store_byte(col, 31) + _store_byte(pending, 0)
    code += _putchar(putchar, 0x44)
    code += _expect_byte(row, 23) + _expect_byte(col, 31) + _expect_byte(pending, 1)
    code += _putchar(putchar, 0x45)
    code += _expect_byte(row, 23) + _expect_byte(col, 1) + _expect_byte(pending, 0)

    for control, expected_row, expected_col in (
        (0x0D, 5, 0),
        (0x0A, 6, 0),
        (0x08, 5, 30),
        (0x09, 6, 0),
    ):
        code += _store_byte(row, 5) + _store_byte(col, 31) + _store_byte(pending, 1)
        code += _putchar(putchar, control)
        code += _expect_byte(row, expected_row) + _expect_byte(col, expected_col) + _expect_byte(pending, 0)

    code += _store_byte(row, 5) + _store_byte(col, 31) + _store_byte(pending, 1)
    code += _putchar(putchar, 0x0C)
    code += _expect_byte(row, 0) + _expect_byte(col, 0) + _expect_byte(pending, 0)
    code += _jp(PASS_PC)
    run_sna(root, bytes(code), patch=phase1._kernel_patch(kernel))


def _setpos_matrix(root: Path, labels: dict[str, int], kernel: bytes) -> None:
    init = labels["zx48_console_init"]
    setpos = labels["zx48_console_setpos"]
    mode = labels["tty_mode"]
    row = labels["tty_row"]
    col = labels["tty_col"]
    shape = labels["tty_cursor_shape"]
    pending = labels["tty_wrap_pending"]
    code = bytearray(b"\xF3" + phase1._ld_sp(phase1.USER_STACK))
    code += _call(init) + _store_byte(mode, 32) + _store_byte(shape, 0)
    code += _store_byte(pending, 1)
    code += b"\x21\x1F\x17" + _call(setpos) + _jp_c(FAIL_PC)
    code += _expect_byte(row, 23) + _expect_byte(col, 31) + _expect_byte(pending, 0)
    code += b"\x21\x00\x18" + _call(setpos)
    code += b"\xD2" + _word(FAIL_PC)
    code += _expect_byte(row, 23) + _expect_byte(col, 31) + _expect_byte(pending, 0)
    code += _jp(PASS_PC)
    run_sna(root, bytes(code), patch=phase1._kernel_patch(kernel))


def dispatch(
    root: Path,
    action: str,
    step: str,
    *,
    sha256_file: Callable[[Path], str],
    run_command: Callable[..., Any],
    require_project_tool: Callable[[Path, str | Path], Path],
):
    if step != "P1.20":
        raise ConsoleCoreError(f"console-core step is not registered: {step}")

    assertions = _source_contract(root)
    failed = [item["name"] for item in assertions if item["passed"] is not True]
    require(not failed, f"static P1.20 failures: {failed}")

    command, kernel, listing = phase1._assemble_kernel(root, run_command, require_project_tool)
    labels = phase1._labels(
        listing,
        (
            "zx48_console_init",
            "zx48_console_putchar",
            "zx48_console_setpos",
            "tty_mode",
            "tty_row",
            "tty_col",
            "tty_cursor_shape",
            "tty_wrap_pending",
        ),
    )
    kernel_bytes = kernel.read_bytes()
    if action == "test":
        _state_matrix(root, labels, kernel_bytes)
        _setpos_matrix(root, labels, kernel_bytes)
        assertions.extend(
            [
                {"name": "tty32-right-edge-deferred-wrap-runtime", "passed": True},
                {"name": "tty32-bottom-right-scroll-is-deferred", "passed": True},
                {"name": "pending-controls-use-real-coordinates", "passed": True},
                {"name": "setpos-final-cell-and-invalid-atomicity", "passed": True},
            ]
        )

    paths = (
        root / "v1/src/kernel/console.asm",
        root / "v1/src/kernel/tty32.asm",
        root / "v1/tools-host/test-driver/phase1_console_core.py",
        kernel,
    )
    return [command], {str(path.relative_to(root)): sha256_file(path) for path in paths}, assertions
