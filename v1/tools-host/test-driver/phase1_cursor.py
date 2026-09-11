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

FONT_BASE = 0xA200
FONT_A_OFFSET = (0x41 - 0x20) * 4
STALE_HANDLER = 0xB100
DIRECT_BYTES = (0x12, 0x34, 0x56, 0x78, 0x9A, 0xBC, 0xDE, 0xF0)


class CursorMatrixError(DriverError):
    """Raised when the Phase-1 cursor/direct-screen contract is violated."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise CursorMatrixError(message)


def _word(value: int) -> bytes:
    return bytes((value & 0xFF, (value >> 8) & 0xFF))


def _call(address: int) -> bytes:
    return b"\xCD" + _word(address)


def _jp(address: int) -> bytes:
    return b"\xC3" + _word(address)


def _jp_nz(address: int) -> bytes:
    return b"\xC2" + _word(address)


def _ld_sp(address: int) -> bytes:
    return b"\x31" + _word(address)


def _store_byte(address: int, value: int) -> bytes:
    return bytes((0x3E, value & 0xFF, 0x32)) + _word(address)


def _store_word(address: int, value: int) -> bytes:
    return b"\x21" + _word(value) + b"\x22" + _word(address)


def _load_byte(address: int) -> bytes:
    return b"\x3A" + _word(address)


def _bitmap_row_address(scan: int) -> int:
    require(0 <= scan < 8, "fixture scan outside first text row")
    return 0x4000 + scan * 0x100


def _patch(kernel_bytes: bytes, extras: tuple[tuple[int, bytes], ...]):
    def apply(ram: bytearray) -> None:
        start = phase1.KERNEL_BASE - 0x4000
        ram[start:start + len(kernel_bytes)] = kernel_bytes
        for address, payload in extras:
            offset = address - 0x4000
            require(0 <= offset <= len(ram) - len(payload), "fixture patch outside RAM")
            ram[offset:offset + len(payload)] = payload
    return apply


def _source_contract(root: Path) -> list[dict[str, object]]:
    cursor = (root / "v1/src/kernel/cursor.asm").read_text(encoding="utf-8").lower()
    console = (root / "v1/src/kernel/console.asm").read_text(encoding="utf-8").lower()
    tty64 = (root / "v1/src/kernel/tty64.asm").read_text(encoding="utf-8").lower()
    return [
        {"name": "cursor-is-xor-not-saved-pixels", "passed": "zx48_cursor_xor:" in cursor and "xor $f0" in cursor and "xor $0f" in cursor},
        {"name": "hide-reverses-visible-cursor", "passed": "zx48_cursor_hide:" in cursor and "call zx48_cursor_xor" in cursor},
        {"name": "show-does-not-save-background", "passed": "zx48_cursor_show:" in cursor and "call zx48_cursor_xor" in cursor},
        {"name": "tty64-neighbor-nibble-preserved", "passed": "and $0f" in tty64 and "and $f0" in tty64},
        {"name": "console-mutations-hide-cursor", "passed": console.count("call zx48_cursor_hide") >= 5},
        {"name": "console-restores-cursor", "passed": console.count("zx48_cursor_show") >= 5},
    ]


def _sequence(labels: dict[str, int], *, expect_exact: bool) -> bytes:
    console_init = labels["zx48_console_init"]
    putchar = labels["zx48_console_putchar"]
    hide = labels["zx48_cursor_hide"]
    show = labels["zx48_cursor_show"]
    blink = labels["zx48_cursor_blink"]
    font_ptr = labels["tty64_font_ptr"]
    shape = labels["tty_cursor_shape"]
    visible = labels["tty_cursor_visible"]
    row = labels["tty_row"]
    col = labels["tty_col"]

    code = bytearray()
    code += b"\xF3" + _ld_sp(phase1.USER_STACK)
    code += _call(console_init)
    code += _store_word(font_ptr, FONT_BASE)
    code += _store_byte(shape, 2)             # block cursor for all eight scanlines
    code += b"\x3E\x41" + _call(putchar)   # draw tty64 text; cursor becomes visible at col 1
    code += _load_byte(row) + b"\xB7" + _jp_nz(FAIL_PC)
    code += _load_byte(col) + b"\xFE\x01" + _jp_nz(FAIL_PC)
    code += _load_byte(visible) + b"\xFE\x01" + _jp_nz(FAIL_PC)
    code += _call(hide)                       # turn cursor OFF before direct writes
    code += _store_byte(shape, 0)
    for scan, value in enumerate(DIRECT_BYTES):
        code += _store_byte(_bitmap_row_address(scan), value)
    code += _store_byte(shape, 2)             # restore the cursor definition
    code += _call(show)
    code += _call(blink)                      # hide
    code += _call(blink)                      # show
    code += _call(hide)
    code += _call(show)
    code += _call(blink)                      # final state hidden
    code += _load_byte(visible) + b"\xB7" + _jp_nz(FAIL_PC)
    if expect_exact:
        for scan, value in enumerate(DIRECT_BYTES):
            code += _load_byte(_bitmap_row_address(scan)) + bytes((0xFE, value)) + _jp_nz(FAIL_PC)
        code += _jp(PASS_PC)
    else:
        code += _load_byte(_bitmap_row_address(0)) + bytes((0xFE, DIRECT_BYTES[0]))
        code += _jp_nz(PASS_PC) + _jp(FAIL_PC)
    return bytes(code)


def _positive_test(root: Path, labels: dict[str, int], kernel_bytes: bytes) -> None:
    glyph = bytes((0xF1, 0xE2, 0xD3, 0xC4))
    run_sna(
        root,
        _sequence(labels, expect_exact=True),
        patch=_patch(kernel_bytes, ((FONT_BASE + FONT_A_OFFSET, glyph),)),
    )


def _stale_restore_negative(root: Path, labels: dict[str, int], kernel_bytes: bytes) -> None:
    hide = labels["zx48_cursor_hide"]
    visible = labels["tty_cursor_visible"]
    patched = bytearray(kernel_bytes)
    offset = hide - phase1.KERNEL_BASE
    require(0 <= offset <= len(patched) - 3, "cursor hide label outside kernel image")
    patched[offset:offset + 3] = _jp(STALE_HANDLER)
    # Deliberately wrong saved-pixel-style hide: when visible, restore a stale byte
    # instead of XORing the current bitmap and then mark the cursor hidden.
    handler = (
        _load_byte(visible)
        + b"\xB7\xC8"                      # OR A; RET Z
        + _store_byte(_bitmap_row_address(0), 0xA5)
        + b"\xAF\x32" + _word(visible) + b"\xC9"
    )
    glyph = bytes((0xF1, 0xE2, 0xD3, 0xC4))
    run_sna(
        root,
        _sequence(labels, expect_exact=False),
        patch=_patch(bytes(patched), ((FONT_BASE + FONT_A_OFFSET, glyph), (STALE_HANDLER, handler))),
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
    if step != "P1.32":
        raise CursorMatrixError(f"cursor/direct-screen step is not registered: {step}")

    assertions = _source_contract(root)
    failed = [item["name"] for item in assertions if item["passed"] is not True]
    require(not failed, f"static cursor/direct-screen failures: {failed}")

    command, kernel, listing = phase1._assemble_kernel(root, run_command, require_project_tool)
    names = (
        "zx48_console_init",
        "zx48_console_putchar",
        "zx48_cursor_hide",
        "zx48_cursor_show",
        "zx48_cursor_blink",
        "tty64_font_ptr",
        "tty_cursor_shape",
        "tty_cursor_visible",
        "tty_row",
        "tty_col",
    )
    labels = phase1._labels(listing, names)
    kernel_bytes = kernel.read_bytes()

    if action == "test":
        _positive_test(root, labels, kernel_bytes)
        _stale_restore_negative(root, labels, kernel_bytes)
        assertions.extend(
            [
                {"name": "direct-screen-bytes-survive-cursor-cycle", "passed": True},
                {"name": "stale-pixel-restore-negative", "passed": True},
            ]
        )

    paths = (
        root / "v1/src/kernel/cursor.asm",
        root / "v1/src/kernel/tty64.asm",
        root / "v1/src/kernel/console.asm",
        root / "v1/tools-host/test-driver/phase1_cursor.py",
        kernel,
    )
    return [command], {str(path.relative_to(root)): sha256_file(path) for path in paths}, assertions
