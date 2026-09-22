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

SYS_CON_PUTCHAR = 0x31
ROM_IY_ANCHOR = 0x5C3A
ROM_CHARSET_BITMAP = 0x3D00
F4X8_SIZE = 392
F4X8_HEADER = b"F4X8\x01\x20\x60\x00"
FONT_SOURCE = 0xB200
SCREEN = 0x4000
ATTR = 0x5800
SCREEN_SIZE = 6912
EXPECTED = 0x6000


class PutCharAbiError(DriverError):
    """Raised when the P1.35 SYS_CON_PUTCHAR contract is violated."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise PutCharAbiError(message)


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


def _expect_equal_bytes(left: int, right: int) -> bytes:
    return (
        b"\x3A" + _word(right)
        + b"\x47"
        + b"\x3A" + _word(left)
        + b"\xB8"
        + _jp_nz(FAIL_PC)
    )


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


def _bitmap_address(pixel_y: int, x_byte: int) -> int:
    require(0 <= pixel_y < 192 and 0 <= x_byte < 32, "invalid Spectrum bitmap coordinate")
    return (
        0x4000
        | ((pixel_y & 0xC0) << 5)
        | ((pixel_y & 0x07) << 8)
        | ((pixel_y & 0x38) << 2)
        | x_byte
    )


def _attr_address(row: int, col: int) -> int:
    require(0 <= row < 24 and 0 <= col < 64, "invalid tty attribute coordinate")
    return ATTR + row * 32 + (col >> 1)


def _decode_rows(asset: bytes, code: int) -> tuple[int, ...]:
    require(len(asset) == F4X8_SIZE and asset[:8] == F4X8_HEADER, "invalid F4X8 fixture")
    require(0x20 <= code <= 0x7F, "F4X8 code outside printable range")
    index = 8 + (code - 0x20) * 4
    packed = asset[index:index + 4]
    require(len(packed) == 4, "F4X8 glyph truncated")
    rows: list[int] = []
    for value in packed:
        rows.extend(((value >> 4) & 0x0F, value & 0x0F))
    return tuple(rows)


def _screen_model() -> bytes:
    data = bytearray(SCREEN_SIZE)
    for row in range(24):
        for scan in range(8):
            base = _bitmap_address(row * 8 + scan, 0) - SCREEN
            for x in range(32):
                data[base + x] = (row * 37 + scan * 11 + x * 3 + 1) & 0xFF
        for x in range(32):
            data[ATTR - SCREEN + row * 32 + x] = (row * 5 + x * 7 + 0x12) & 0x7F
    return bytes(data)


def _scroll_model(source: bytes) -> bytes:
    require(len(source) == SCREEN_SIZE, "scroll model requires exact screen")
    out = bytearray(source)
    for row in range(23):
        for scan in range(8):
            src = _bitmap_address((row + 1) * 8 + scan, 0) - SCREEN
            dst = _bitmap_address(row * 8 + scan, 0) - SCREEN
            out[dst:dst + 32] = source[src:src + 32]
    for scan in range(8):
        dst = _bitmap_address(184 + scan, 0) - SCREEN
        out[dst:dst + 32] = bytes(32)
    attr = ATTR - SCREEN
    out[attr:attr + 23 * 32] = source[attr + 32:attr + 24 * 32]
    out[attr + 23 * 32:attr + 24 * 32] = bytes([7]) * 32
    return bytes(out)


def _source_contract(root: Path) -> list[dict[str, object]]:
    syscall = _strip((root / "v1/src/kernel/syscall.asm").read_text(encoding="utf-8"))
    console = _strip((root / "v1/src/kernel/console.asm").read_text(encoding="utf-8"))
    cursor = _strip((root / "v1/src/kernel/cursor.asm").read_text(encoding="utf-8"))
    interrupt = _strip((root / "v1/src/kernel/interrupt.asm").read_text(encoding="utf-8"))
    include = _strip((root / "v1/include/zx48ux.inc").read_text(encoding="utf-8"))

    sys_putchar = _block(syscall, "zx48_sys_con_putchar:", "zx48_sys_con_write:")
    control = _block(console, "zx48_console_control_begin:", "zx48_console_printable:")
    printable = _block(console, "zx48_console_printable:", "zx48_console_wrap_now:")
    wrap = _block(console, "zx48_console_wrap_now:", "zx48_console_write:")
    clear = _block(console, "zx48_console_clear:", "zx48_console_setpos:")
    begin = _block(cursor, "zx48_screen_begin:", "zx48_cursor_show:")
    end = _block(cursor, "zx48_cursor_show:", "zx48_cursor_service:")

    syscall_exact = _ordered(
        sys_putchar,
        (
            "ld hl,(syscall_arg_hl)",
            "ld a,h",
            "or a",
            "jp nz,zx48_sys_invalid",
            "ld a,l",
            "call zx48_console_putchar",
            "ret c",
        ),
    )
    printable_exact = _ordered(
        printable,
        (
            "cp udg_code_last+1",
            "jr nc,zx48_console_bad",
            "cp udg_code_first",
            "jr c,zx48_console_print",
            "push af",
            "ld a,(tty_mode)",
            "cp tty_mode_64",
            "pop af",
            "jr z,zx48_console_bad",
            "zx48_console_print:",
            "push af",
            "call zx48_cursor_hide",
            "ld a,(tty_wrap_pending)",
            "or a",
            "call nz,zx48_console_wrap_now",
            "ld a,(tty_mode)",
            "cp tty_mode_64",
            "jr z,zx48_console_print64",
        ),
    )
    control_exact = (
        "ld (tty_wrap_pending),a" in control
        and "jp zx48_cursor_hide" in control
        and all(
            "call zx48_console_control_begin" in control[control.index(label):control.index(label) + 120]
            for label in (
                "zx48_console_lf:",
                "zx48_console_cr:",
                "zx48_console_bs:",
                "zx48_console_tab:",
            )
        )
    )
    return [
        {"name": "canonical-putchar-syscall-number", "passed": any(line.split() == ["sys_con_putchar", "equ", "$31"] for line in include.splitlines())},
        {"name": "putchar-rejects-nonzero-h-before-output", "passed": syscall_exact},
        {"name": "printable-byte-range-preserves-text-and-tty32-udg-extension", "passed": "cp $20" in console and printable_exact},
        {"name": "printable-resolves-deferred-wrap-before-draw", "passed": printable_exact},
        {"name": "printable-dispatches-current-tty-mode", "passed": "call zx48_tty32_draw_char" in printable and "call zx48_tty64_draw_char" in printable},
        {"name": "moving-controls-cancel-pending-before-motion", "passed": control_exact},
        {"name": "form-feed-clears-and-homes-with-pending-clear", "passed": all(token in clear for token in ("ld (tty_row),hl", "ld (tty_wrap_pending),a", "jr zx48_console_control_done"))},
        {"name": "deferred-wrap-has-single-scroll-edge", "passed": console.count("call zx48_console_scroll") == 1 and "call zx48_console_scroll" in wrap},
        {"name": "screen-begin-is-depth-counted", "passed": all(token in begin for token in ("inc (hl)", "jr z,zx48_cursor_depth_panic", "call zx48_cursor_xor"))},
        {"name": "screen-end-is-strictly-balanced", "passed": all(token in end for token in ("or a", "jr z,zx48_cursor_depth_panic", "dec (hl)"))},
        {"name": "interrupt-never-edits-console-or-cursor-bitmap-directly", "passed": "zx48_cursor_xor" not in interrupt and "zx48_console_putchar" not in interrupt},
    ]


def _patch(kernel: bytes, entries: tuple[tuple[int, bytes], ...] = ()):
    def apply(ram: bytearray) -> None:
        start = phase1.KERNEL_BASE - 0x4000
        ram[start:start + len(kernel)] = kernel
        for address, payload in entries:
            offset = address - 0x4000
            require(0 <= offset <= len(ram) - len(payload), f"fixture patch outside RAM at {address:04x}")
            ram[offset:offset + len(payload)] = payload
    return apply


def _expect_iy_anchor() -> bytes:
    return (
        b"\xFD\xE5\xE1"
        + phase1._ld_de(ROM_IY_ANCHOR)
        + b"\xB7\xED\x52"
        + _jp_nz(FAIL_PC)
    )


def _sys_putchar(value: int, *, high: int = 0) -> bytes:
    return phase1._ld_hl(((high & 0xFF) << 8) | (value & 0xFF)) + bytes((0x3E, SYS_CON_PUTCHAR)) + _call(0xE000)


def _base_prefix(labels: dict[str, int]) -> bytearray:
    code = bytearray(b"\xF3" + phase1._ld_sp(phase1.USER_STACK))
    code += _call(labels["zx48_kernel_stack_init"])
    code += _call(labels["zx48_console_init"])
    code += _store_byte(labels["tty_cursor_shape"], 0)
    code += _store_byte(labels["tty_cursor_visible"], 0)
    code += _store_byte(labels["screen_mutation_depth"], 0)
    code += _store_byte(labels["cursor_service_parity"], 0)
    return code


def _tty64_prefix(labels: dict[str, int]) -> bytearray:
    code = bytearray(b"\xF3" + phase1._ld_sp(phase1.USER_STACK))
    code += _call(labels["zx48_kernel_stack_init"])
    code += _call(labels["zx48_memory_init"])
    code += b"\x21" + _word(FONT_SOURCE)
    code += b"\x01" + _word(F4X8_SIZE)
    code += _call(labels["zx48_tty64_install_font"]) + _jp_c(FAIL_PC)
    code += _call(labels["zx48_console_init"])
    code += _store_byte(labels["tty_cursor_shape"], 0)
    code += _store_byte(labels["tty_cursor_visible"], 0)
    code += _store_byte(labels["screen_mutation_depth"], 0)
    code += _store_byte(labels["cursor_service_parity"], 0)
    return code


def _abi_negative_fixture(root: Path, labels: dict[str, int], kernel: bytes) -> None:
    row, col = 4, 5
    guard = _bitmap_address(row * 8, col)
    attr = ATTR + row * 32 + col
    code = _base_prefix(labels)
    code += _store_byte(labels["tty_mode"], 32)
    code += _store_byte(labels["tty_row"], row)
    code += _store_byte(labels["tty_col"], col)
    code += _store_byte(labels["tty_wrap_pending"], 1)
    code += phase1._ld_iy(0x1234)
    code += _sys_putchar(0x41, high=1)
    code += _jp_nc(FAIL_PC) + bytes((0xFE, labels["E_INVAL"] & 0xFF)) + _jp_nz(FAIL_PC)
    code += _expect_byte(labels["tty_row"], row)
    code += _expect_byte(labels["tty_col"], col)
    code += _expect_byte(labels["tty_wrap_pending"], 1)
    code += _expect_byte(labels["screen_mutation_depth"], 0)
    code += _expect_byte(guard, 0x69) + _expect_byte(attr, 0x96)
    code += _expect_iy_anchor()

    code += phase1._ld_iy(0x2345)
    code += _sys_putchar(0xA0)
    code += _jp_nc(FAIL_PC) + bytes((0xFE, labels["E_INVAL"] & 0xFF)) + _jp_nz(FAIL_PC)
    code += _expect_byte(labels["tty_row"], row)
    code += _expect_byte(labels["tty_col"], col)
    code += _expect_byte(labels["tty_wrap_pending"], 1)
    code += _expect_byte(labels["screen_mutation_depth"], 0)
    code += _expect_byte(guard, 0x69) + _expect_byte(attr, 0x96)
    code += _expect_iy_anchor()

    # P7.13 extends tty32 only: tty64 must reject UDG bytes before any cursor,
    # deferred-wrap, bitmap, attribute, or coordinate mutation.
    code += _store_byte(labels["tty_mode"], 64)
    code += phase1._ld_iy(0x2A45)
    code += _sys_putchar(0x80)
    code += _jp_nc(FAIL_PC) + bytes((0xFE, labels["E_INVAL"] & 0xFF)) + _jp_nz(FAIL_PC)
    code += _expect_byte(labels["tty_row"], row)
    code += _expect_byte(labels["tty_col"], col)
    code += _expect_byte(labels["tty_wrap_pending"], 1)
    code += _expect_byte(labels["screen_mutation_depth"], 0)
    code += _expect_byte(guard, 0x69) + _expect_byte(attr, 0x96)
    code += _expect_iy_anchor() + _jp(PASS_PC)
    run_sna(root, bytes(code), patch=_patch(kernel, ((guard, b"\x69"), (attr, b"\x96"))))


def _tty32_print_fixture(root: Path, labels: dict[str, int], kernel: bytes) -> None:
    row, col, codepoint = 4, 5, 0x41
    entries: list[tuple[int, bytes]] = []
    target: list[int] = []
    before: list[int] = []
    after: list[int] = []
    for scan in range(8):
        target_addr = _bitmap_address(row * 8 + scan, col)
        before_addr = _bitmap_address(row * 8 + scan, col - 1)
        after_addr = _bitmap_address(row * 8 + scan, col + 1)
        entries.extend(((before_addr, b"\x66"), (target_addr, b"\xA5"), (after_addr, b"\x77")))
        target.append(target_addr)
        before.append(before_addr)
        after.append(after_addr)
    attr = ATTR + row * 32 + col
    entries.append((attr, b"\x5A"))

    code = _base_prefix(labels)
    code += _store_byte(labels["tty_mode"], 32)
    code += _store_byte(labels["tty_row"], row)
    code += _store_byte(labels["tty_col"], col)
    code += _store_byte(labels["tty_wrap_pending"], 0)
    code += phase1._ld_iy(0x3456)
    code += _sys_putchar(codepoint) + _jp_c(FAIL_PC)
    code += _expect_iy_anchor()
    code += _expect_byte(labels["tty_row"], row)
    code += _expect_byte(labels["tty_col"], col + 1)
    code += _expect_byte(labels["tty_wrap_pending"], 0)
    code += _expect_byte(labels["screen_mutation_depth"], 0)
    glyph = ROM_CHARSET_BITMAP + (codepoint - 0x20) * 8
    for scan, address in enumerate(target):
        code += _expect_equal_bytes(address, glyph + scan)
        code += _expect_byte(before[scan], 0x66) + _expect_byte(after[scan], 0x77)
    code += _expect_byte(attr, 0x5A) + _jp(PASS_PC)
    run_sna(root, bytes(code), patch=_patch(kernel, tuple(entries)))


def _tty64_print_fixture(
    root: Path,
    labels: dict[str, int],
    kernel: bytes,
    asset: bytes,
    *,
    col: int,
) -> None:
    row, codepoint = 7, 0x41
    sentinel = 0xA5
    rows = _decode_rows(asset, codepoint)
    x_byte = col >> 1
    entries: list[tuple[int, bytes]] = [(FONT_SOURCE, asset)]
    target: list[tuple[int, int]] = []
    neighbor_before: list[int] = []
    neighbor_after: list[int] = []
    for scan, nibble in enumerate(rows):
        address = _bitmap_address(row * 8 + scan, x_byte)
        before = _bitmap_address(row * 8 + scan, x_byte - 1)
        after = _bitmap_address(row * 8 + scan, x_byte + 1)
        entries.extend(((before, b"\x66"), (address, bytes((sentinel,))), (after, b"\x77")))
        expected = ((sentinel & 0xF0) | nibble) if (col & 1) else ((sentinel & 0x0F) | (nibble << 4))
        target.append((address, expected))
        neighbor_before.append(before)
        neighbor_after.append(after)

    attr = _attr_address(row, col)
    entries.extend(((attr - 1, b"\x44"), (attr, b"\xC3"), (attr + 1, b"\x55")))
    current_attr = 0x12 if not (col & 1) else 0x34

    code = _tty64_prefix(labels)
    code += _store_byte(labels["tty_mode"], 64)
    code += _store_byte(labels["tty_row"], row)
    code += _store_byte(labels["tty_col"], col)
    code += _store_byte(labels["tty_wrap_pending"], 0)
    code += _store_byte(labels["tty_current_attr"], current_attr)
    code += phase1._ld_iy(0x4567)
    code += _sys_putchar(codepoint) + _jp_c(FAIL_PC)
    code += _expect_iy_anchor()
    code += _expect_byte(labels["tty_row"], row)
    code += _expect_byte(labels["tty_col"], col + 1)
    code += _expect_byte(labels["tty_wrap_pending"], 0)
    code += _expect_byte(labels["screen_mutation_depth"], 0)
    for scan, (address, expected) in enumerate(target):
        code += _expect_byte(address, expected)
        code += _expect_byte(neighbor_before[scan], 0x66) + _expect_byte(neighbor_after[scan], 0x77)
    code += _expect_byte(attr, current_attr)
    code += _expect_byte(attr - 1, 0x44) + _expect_byte(attr + 1, 0x55)
    code += _jp(PASS_PC)
    run_sna(root, bytes(code), patch=_patch(kernel, tuple(entries)))


def _state_matrix_fixture(
    root: Path,
    labels: dict[str, int],
    kernel: bytes,
    asset: bytes,
    *,
    mode: int,
) -> None:
    last = mode - 1
    entries: tuple[tuple[int, bytes], ...] = ((FONT_SOURCE, asset),) if mode == 64 else ()
    code = _tty64_prefix(labels) if mode == 64 else _base_prefix(labels)
    code += _store_byte(labels["tty_mode"], mode)

    code += _store_byte(labels["tty_row"], 5)
    code += _store_byte(labels["tty_col"], last)
    code += _store_byte(labels["tty_wrap_pending"], 0)
    code += phase1._ld_iy(0x5678)
    code += _sys_putchar(0x41) + _jp_c(FAIL_PC)
    code += _expect_iy_anchor()
    code += _expect_byte(labels["tty_row"], 5)
    code += _expect_byte(labels["tty_col"], last)
    code += _expect_byte(labels["tty_wrap_pending"], 1)
    code += _expect_byte(labels["screen_mutation_depth"], 0)

    code += _sys_putchar(0x42) + _jp_c(FAIL_PC)
    code += _expect_byte(labels["tty_row"], 6)
    code += _expect_byte(labels["tty_col"], 1)
    code += _expect_byte(labels["tty_wrap_pending"], 0)

    controls = (
        (0x0D, 5, 0),
        (0x0A, 6, 0),
        (0x08, 5, last - 1),
        (0x09, 6, 0),
    )
    for control, expected_row, expected_col in controls:
        code += _store_byte(labels["tty_row"], 5)
        code += _store_byte(labels["tty_col"], last)
        code += _store_byte(labels["tty_wrap_pending"], 1)
        code += _sys_putchar(control) + _jp_c(FAIL_PC)
        code += _expect_byte(labels["tty_row"], expected_row)
        code += _expect_byte(labels["tty_col"], expected_col)
        code += _expect_byte(labels["tty_wrap_pending"], 0)
        code += _expect_byte(labels["screen_mutation_depth"], 0)

    code += _store_byte(labels["tty_row"], 5)
    code += _store_byte(labels["tty_col"], last)
    code += _store_byte(labels["tty_wrap_pending"], 1)
    code += _sys_putchar(0x0C) + _jp_c(FAIL_PC)
    code += _expect_byte(labels["tty_row"], 0)
    code += _expect_byte(labels["tty_col"], 0)
    code += _expect_byte(labels["tty_wrap_pending"], 0)
    code += _expect_byte(labels["screen_mutation_depth"], 0)
    code += _jp(PASS_PC)
    run_sna(root, bytes(code), patch=_patch(kernel, entries))


def _compare_screen(code: bytearray) -> None:
    code += b"\x21" + _word(SCREEN) + b"\x11" + _word(EXPECTED) + b"\x01" + _word(SCREEN_SIZE)
    loop = ENTRY_PC + len(code)
    code += b"\x1A\xBE" + _jp_nz(FAIL_PC) + b"\x13\x23\x0B\x78\xB1" + _jp_nz(loop)


def _bottom_scroll_fixture(root: Path, labels: dict[str, int], kernel: bytes, *, mode: int) -> None:
    source = _screen_model()
    expected = _scroll_model(source)
    code = _base_prefix(labels)
    code += _store_byte(labels["tty_mode"], mode)
    code += _store_byte(labels["tty_row"], 23)
    code += _store_byte(labels["tty_col"], mode - 1)
    code += _store_byte(labels["tty_wrap_pending"], 1)
    code += _sys_putchar(0x0A) + _jp_c(FAIL_PC)
    code += _expect_byte(labels["tty_row"], 23)
    code += _expect_byte(labels["tty_col"], 0)
    code += _expect_byte(labels["tty_wrap_pending"], 0)
    code += _expect_byte(labels["screen_mutation_depth"], 0)
    _compare_screen(code)
    code += _jp(PASS_PC)
    run_sna(
        root,
        bytes(code),
        patch=_patch(kernel, ((SCREEN, source), (EXPECTED, expected))),
    )


def _cursor_balance_fixture(root: Path, labels: dict[str, int], kernel: bytes) -> None:
    row, col, codepoint = 9, 12, 0x41
    entries: list[tuple[int, bytes]] = []
    printed: list[int] = []
    next_cell: list[int] = []
    for scan in range(8):
        target = _bitmap_address(row * 8 + scan, col)
        following = _bitmap_address(row * 8 + scan, col + 1)
        entries.extend(((target, b"\xA5"), (following, b"\x5A")))
        printed.append(target)
        next_cell.append(following)

    code = _base_prefix(labels)
    code += _store_byte(labels["tty_mode"], 32)
    code += _store_byte(labels["tty_row"], row)
    code += _store_byte(labels["tty_col"], col)
    code += _store_byte(labels["tty_wrap_pending"], 0)
    code += _store_byte(labels["tty_cursor_shape"], 2)
    code += _store_byte(labels["cursor_phase"], 1)
    code += _store_byte(labels["tty_cursor_visible"], 0)
    code += _call(labels["zx48_cursor_service"])
    code += _expect_byte(labels["tty_cursor_visible"], 1)
    code += _expect_byte(labels["screen_mutation_depth"], 0)

    code += phase1._ld_iy(0x6789)
    code += _sys_putchar(codepoint) + _jp_c(FAIL_PC)
    code += _expect_iy_anchor()
    code += _expect_byte(labels["tty_col"], col + 1)
    code += _expect_byte(labels["tty_cursor_visible"], 1)
    code += _expect_byte(labels["screen_mutation_depth"], 0)
    glyph = ROM_CHARSET_BITMAP + (codepoint - 0x20) * 8
    for scan, address in enumerate(printed):
        code += _expect_equal_bytes(address, glyph + scan)

    code += _call(labels["zx48_cursor_hide"])
    code += _expect_byte(labels["tty_cursor_visible"], 0)
    code += _expect_byte(labels["screen_mutation_depth"], 1)
    for address in next_cell:
        code += _expect_byte(address, 0x5A)
    code += _call(labels["zx48_cursor_show"])
    code += _expect_byte(labels["tty_cursor_visible"], 1)
    code += _expect_byte(labels["screen_mutation_depth"], 0)
    code += _jp(PASS_PC)
    run_sna(root, bytes(code), patch=_patch(kernel, tuple(entries)))


def dispatch(
    root: Path,
    action: str,
    step: str,
    *,
    sha256_file: Callable[[Path], str],
    run_command: Callable[..., Any],
    require_project_tool: Callable[[Path, str | Path], Path],
):
    if step != "P1.35":
        raise PutCharAbiError(f"putchar step is not registered: {step}")

    asset_path = root / "v1/assets/font4x8.bin"
    asset = asset_path.read_bytes()
    assertions = _source_contract(root)
    failed = [item["name"] for item in assertions if item["passed"] is not True]
    require(not failed, f"static P1.35 failures: {failed}")

    command, kernel_path, listing = phase1._assemble_kernel(root, run_command, require_project_tool)
    labels = phase1._labels(
        listing,
        (
            "E_INVAL",
            "zx48_kernel_stack_init",
            "zx48_memory_init",
            "zx48_console_init",
            "zx48_tty64_install_font",
            "zx48_cursor_service",
            "zx48_cursor_hide",
            "zx48_cursor_show",
            "tty_mode",
            "tty_row",
            "tty_col",
            "tty_cursor_shape",
            "tty_cursor_visible",
            "tty_wrap_pending",
            "tty_current_attr",
            "cursor_phase",
            "cursor_service_parity",
            "screen_mutation_depth",
        ),
    )
    kernel = kernel_path.read_bytes()

    if action == "test":
        _abi_negative_fixture(root, labels, kernel)
        _tty32_print_fixture(root, labels, kernel)
        _tty64_print_fixture(root, labels, kernel, asset, col=10)
        _tty64_print_fixture(root, labels, kernel, asset, col=11)
        _state_matrix_fixture(root, labels, kernel, asset, mode=32)
        _state_matrix_fixture(root, labels, kernel, asset, mode=64)
        _bottom_scroll_fixture(root, labels, kernel, mode=32)
        _bottom_scroll_fixture(root, labels, kernel, mode=64)
        _cursor_balance_fixture(root, labels, kernel)
        assertions.extend(
            (
                {"name": "nonzero-h-and-mode-invalid-bytes-are-atomic-runtime", "passed": True},
                {"name": "tty32-printable-bitmap-neighbors-and-attribute-exact", "passed": True},
                {"name": "tty64-even-odd-nibbles-and-attributes-exact", "passed": True},
                {"name": "tty32-and-tty64-deferred-wrap-controls-exact", "passed": True},
                {"name": "bottom-row-lf-scrolls-exactly-once-in-both-modes", "passed": True},
                {"name": "visible-cursor-putchar-mutation-is-reversible-and-balanced", "passed": True},
                {"name": "putchar-return-canonicalizes-iy", "passed": True},
            )
        )

    paths = (
        root / "docs/01-ZX-UX-ARCHITECTURE-REV12.md",
        root / "v1/assets/font4x8.bin",
        root / "v1/src/kernel/console.asm",
        root / "v1/src/kernel/cursor.asm",
        root / "v1/src/kernel/syscall.asm",
        root / "v1/src/kernel/tty32.asm",
        root / "v1/src/kernel/tty64.asm",
        root / "v1/tools-host/test-driver/phase1_putchar.py",
        kernel_path,
    )
    return [command], {str(path.relative_to(root)): sha256_file(path) for path in paths}, assertions
