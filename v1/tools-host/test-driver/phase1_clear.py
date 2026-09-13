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
from fuse_harness import ENTRY_PC, FAIL_PC, PASS_PC, run_sna
import phase1

SYS_CON_CLEAR = 0x33
ROM_IY_ANCHOR = 0x5C3A
SCREEN = 0x4000
ATTR = 0x5800
SCREEN_SIZE = 6912
EXPECTED = 0x6000
PROTECTED_LOW = 0x5B00
PROTECTED_HIGH = 0x5FFF


class ClearAbiError(DriverError):
    """Raised when the P1.37 SYS_CON_CLEAR contract is violated."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ClearAbiError(message)


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


def _expect_hl(value: int) -> bytes:
    return phase1._ld_de(value) + b"\xB7\xED\x52" + _jp_nz(FAIL_PC)


def _expect_iy_anchor() -> bytes:
    return b"\xFD\xE5\xE1" + phase1._ld_de(ROM_IY_ANCHOR) + b"\xB7\xED\x52" + _jp_nz(FAIL_PC)


def _strip(text: str) -> str:
    return "\n".join(line.split(";", 1)[0].rstrip().lower() for line in text.splitlines())


def _block(text: str, start: str, end: str) -> str:
    first = text.find(start)
    last = text.find(end, first + len(start)) if first >= 0 else -1
    require(0 <= first < last, f"missing source block {start}..{end}")
    return text[first:last]


def _ordered(text: str, tokens: tuple[str, ...]) -> bool:
    cursor = 0
    for token in tokens:
        position = text.find(token, cursor)
        if position < 0:
            return False
        cursor = position + len(token)
    return True


def _source_contract(root: Path) -> list[dict[str, object]]:
    syscall = _strip((root / "v1/src/kernel/syscall.asm").read_text(encoding="utf-8"))
    console = _strip((root / "v1/src/kernel/console.asm").read_text(encoding="utf-8"))
    cursor = _strip((root / "v1/src/kernel/cursor.asm").read_text(encoding="utf-8"))
    ula = _strip((root / "v1/src/kernel/ula_io.asm").read_text(encoding="utf-8"))
    include = _strip((root / "v1/include/zx48ux.inc").read_text(encoding="utf-8"))

    sys_clear = _block(syscall, "zx48_sys_con_clear:", "zx48_sys_con_getpos:")
    clear = _block(console, "zx48_console_clear:", "zx48_console_setpos:")
    begin = _block(cursor, "zx48_screen_begin:", "zx48_cursor_show:")
    end = _block(cursor, "zx48_cursor_show:", "zx48_cursor_service:")

    clear_exact = _ordered(
        clear,
        (
            "call zx48_cursor_hide",
            "xor a",
            "ld hl,bitmap_start",
            "ld de,bitmap_start+1",
            "ld bc,bitmap_end-bitmap_start+1",
            "ld (hl),a",
            "ldir",
            "ld a,7",
            "ld (hl),a",
            "ld bc,attr_end-attr_start",
            "ldir",
            "xor a",
            "ld h,a",
            "ld l,a",
            "ld (tty_row),hl",
            "ld (tty_wrap_pending),a",
            "jr zx48_console_control_done",
        ),
    )
    return [
        {"name": "canonical-con-clear-syscall-number", "passed": any(line.split() == ["sys_con_clear", "equ", "$33"] for line in include.splitlines())},
        {"name": "clear-syscall-returns-zero-through-canonical-result-path", "passed": _ordered(sys_clear, ("call zx48_console_clear", "jp zx48_sys_zero_result"))},
        {"name": "clear-brackets-one-console-mutation-and-homes", "passed": clear_exact},
        {"name": "clear-target-is-exact-bitmap-and-attribute-display", "passed": "bitmap_start" in clear and "bitmap_end" in clear and "attr_end-attr_start" in clear and "$5b00" not in clear},
        {"name": "clear-does-not-touch-ula-owner", "passed": "ula_shadow" not in clear and "out (ula_port)" not in clear and "ula_shadow:" in ula},
        {"name": "nested-screen-begin-is-depth-counted", "passed": all(token in begin for token in ("inc (hl)", "jr z,zx48_cursor_depth_panic", "call zx48_cursor_xor"))},
        {"name": "nested-screen-end-defers-reconcile-until-depth-zero", "passed": _ordered(end, ("or a", "jr z,zx48_cursor_depth_panic", "dec (hl)", "jr nz,zx48_cursor_ok", "jr zx48_cursor_service_core"))},
    ]


def _bitmap_address(pixel_y: int, x_byte: int) -> int:
    require(0 <= pixel_y < 192 and 0 <= x_byte < 32, "invalid Spectrum bitmap coordinate")
    return 0x4000 | ((pixel_y & 0xC0) << 5) | ((pixel_y & 7) << 8) | ((pixel_y & 0x38) << 2) | x_byte


def _screen_pattern() -> bytes:
    data = bytearray(SCREEN_SIZE)
    for row in range(24):
        for scan in range(8):
            base = _bitmap_address(row * 8 + scan, 0) - SCREEN
            for x in range(32):
                data[base + x] = (row * 41 + scan * 13 + x * 5 + 3) & 0xFF
        for x in range(32):
            data[ATTR - SCREEN + row * 32 + x] = (row * 7 + x * 3 + 0x11) & 0x7F
    return bytes(data)


def _cleared_screen(*, cursor_block: bool = False) -> bytes:
    data = bytearray(SCREEN_SIZE)
    data[ATTR - SCREEN:] = bytes([7]) * (SCREEN_SIZE - (ATTR - SCREEN))
    if cursor_block:
        for scan in range(8):
            data[_bitmap_address(scan, 0) - SCREEN] = 0xFF
    return bytes(data)


def _patch(kernel: bytes, *, source: bytes, expected: bytes):
    def apply(ram: bytearray) -> None:
        start = phase1.KERNEL_BASE - 0x4000
        ram[start:start + len(kernel)] = kernel
        ram[SCREEN - 0x4000:SCREEN - 0x4000 + SCREEN_SIZE] = source
        ram[EXPECTED - 0x4000:EXPECTED - 0x4000 + SCREEN_SIZE] = expected
        ram[PROTECTED_LOW - 0x4000] = 0xA5
        ram[PROTECTED_HIGH - 0x4000] = 0x5A
    return apply


def _compare_expected(code: bytearray) -> None:
    code += phase1._ld_hl(SCREEN) + phase1._ld_de(EXPECTED) + b"\x01" + _word(SCREEN_SIZE)
    loop = ENTRY_PC + len(code)
    code += b"\x1A\xBE" + _jp_nz(FAIL_PC) + b"\x13\x23\x0B\x78\xB1" + _jp_nz(loop)


def _base_prefix(labels: dict[str, int]) -> bytearray:
    code = bytearray(b"\xF3" + phase1._ld_sp(phase1.USER_STACK))
    code += _call(labels["zx48_kernel_stack_init"])
    code += _call(labels["zx48_console_init"])
    code += _store_byte(labels["tty_mode"], 32)
    code += _store_byte(labels["screen_mutation_depth"], 0)
    code += _store_byte(labels["cursor_service_parity"], 0)
    return code


def _sys_clear() -> bytes:
    return bytes((0x3E, SYS_CON_CLEAR)) + _call(0xE000)


def _basic_clear_fixture(root: Path, labels: dict[str, int], kernel: bytes) -> None:
    source = _screen_pattern()
    expected = _cleared_screen()
    code = _base_prefix(labels)
    code += _store_byte(labels["tty_cursor_shape"], 0)
    code += _store_byte(labels["tty_cursor_visible"], 0)
    code += _store_byte(labels["tty_row"], 12)
    code += _store_byte(labels["tty_col"], 17)
    code += _store_byte(labels["tty_wrap_pending"], 1)
    code += _store_byte(labels["ula_shadow"], 0x1D)
    code += phase1._ld_iy(0x1234)
    code += _sys_clear() + _jp_c(FAIL_PC) + _expect_hl(0) + _expect_iy_anchor()
    code += _expect_byte(labels["tty_row"], 0) + _expect_byte(labels["tty_col"], 0)
    code += _expect_byte(labels["tty_wrap_pending"], 0) + _expect_byte(labels["screen_mutation_depth"], 0)
    code += _expect_byte(labels["ula_shadow"], 0x1D)
    code += _expect_byte(PROTECTED_LOW, 0xA5) + _expect_byte(PROTECTED_HIGH, 0x5A)
    _compare_expected(code)
    code += _jp(PASS_PC)
    run_sna(root, bytes(code), patch=_patch(kernel, source=source, expected=expected))


def _nested_clear_fixture(root: Path, labels: dict[str, int], kernel: bytes, *, due_parity: bool) -> None:
    source = _screen_pattern()
    expected = _cleared_screen(cursor_block=not due_parity)
    code = _base_prefix(labels)
    code += _store_byte(labels["tty_row"], 5)
    code += _store_byte(labels["tty_col"], 7)
    code += _store_byte(labels["tty_cursor_shape"], 2)
    code += _store_byte(labels["ula_shadow"], 0x16)
    code += _call(labels["zx48_cursor_service"])
    code += _expect_byte(labels["tty_cursor_visible"], 1)
    code += _call(labels["zx48_cursor_hide"])
    code += _expect_byte(labels["screen_mutation_depth"], 1) + _expect_byte(labels["tty_cursor_visible"], 0)
    if due_parity:
        code += _store_byte(labels["cursor_service_parity"], 1)
    code += _call(labels["zx48_console_clear"])
    code += _expect_byte(labels["screen_mutation_depth"], 1) + _expect_byte(labels["tty_cursor_visible"], 0)
    code += _expect_byte(labels["tty_row"], 0) + _expect_byte(labels["tty_col"], 0) + _expect_byte(labels["tty_wrap_pending"], 0)
    code += _call(labels["zx48_cursor_show"])
    code += _expect_byte(labels["screen_mutation_depth"], 0)
    code += _expect_byte(labels["cursor_service_parity"], 0)
    code += _expect_byte(labels["tty_cursor_visible"], 0 if due_parity else 1)
    code += _expect_byte(labels["cursor_phase"], 0 if due_parity else 1)
    code += _expect_byte(labels["ula_shadow"], 0x16)
    code += _expect_byte(PROTECTED_LOW, 0xA5) + _expect_byte(PROTECTED_HIGH, 0x5A)
    _compare_expected(code)
    code += _jp(PASS_PC)
    run_sna(root, bytes(code), patch=_patch(kernel, source=source, expected=expected))


def dispatch(
    root: Path,
    action: str,
    step: str,
    *,
    sha256_file: Callable[[Path], str],
    run_command: Callable[..., Any],
    require_project_tool: Callable[[Path, str | Path], Path],
):
    if step != "P1.37":
        raise ClearAbiError(f"console clear step is not registered: {step}")
    assertions = _source_contract(root)
    failed = [item["name"] for item in assertions if item["passed"] is not True]
    require(not failed, f"static P1.37 failures: {failed}")

    command, kernel_path, listing = phase1._assemble_kernel(root, run_command, require_project_tool)
    labels = phase1._labels(
        listing,
        (
            "zx48_kernel_stack_init",
            "zx48_console_init",
            "zx48_console_clear",
            "zx48_cursor_service",
            "zx48_cursor_hide",
            "zx48_cursor_show",
            "tty_mode",
            "tty_row",
            "tty_col",
            "tty_cursor_shape",
            "tty_cursor_visible",
            "tty_wrap_pending",
            "cursor_phase",
            "cursor_service_parity",
            "screen_mutation_depth",
            "ula_shadow",
        ),
    )
    kernel = kernel_path.read_bytes()

    if action == "test":
        _basic_clear_fixture(root, labels, kernel)
        _nested_clear_fixture(root, labels, kernel, due_parity=False)
        _nested_clear_fixture(root, labels, kernel, due_parity=True)
        assertions.extend(
            (
                {"name": "syscall-clear-is-byte-exact-and-homes-runtime", "passed": True},
                {"name": "clear-preserves-ula-shadow-and-protected-workspace-runtime", "passed": True},
                {"name": "nested-clear-does-not-double-redraw-cursor-runtime", "passed": True},
                {"name": "due-cursor-parity-is-consumed-only-at-outer-end-runtime", "passed": True},
                {"name": "clear-return-and-iy-are-exact-runtime", "passed": True},
            )
        )

    paths = (
        root / "docs/01-ZX-UX-ARCHITECTURE-REV12.md",
        root / "v1/include/zx48ux.inc",
        root / "v1/src/kernel/console.asm",
        root / "v1/src/kernel/cursor.asm",
        root / "v1/src/kernel/syscall.asm",
        root / "v1/src/kernel/ula_io.asm",
        root / "v1/tools-host/test-driver/phase1_clear.py",
        kernel_path,
    )
    return [command], {str(path.relative_to(root)): sha256_file(path) for path in paths}, assertions
