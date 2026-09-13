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

SCREEN = 0x4000
BITMAP_SIZE = 6144
ATTR = 0x5800
SCREEN_SIZE = 6912
EXPECTED = 0x6000
GUARD_LOW = 0x5B00
GUARD_HIGH = 0x5FFF


class Tty64ScrollError(DriverError):
    """Raised when the P1.23 tty64 scroll contract is violated."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Tty64ScrollError(message)


def _word(value: int) -> bytes:
    return bytes((value & 0xFF, (value >> 8) & 0xFF))


def _call(address: int) -> bytes:
    return b"\xCD" + _word(address)


def _jp(address: int) -> bytes:
    return b"\xC3" + _word(address)


def _jp_nz(address: int) -> bytes:
    return b"\xC2" + _word(address)


def _store(address: int, value: int) -> bytes:
    return bytes((0x3E, value & 0xFF, 0x32)) + _word(address)


def _expect(address: int, value: int) -> bytes:
    return b"\x3A" + _word(address) + bytes((0xFE, value & 0xFF)) + _jp_nz(FAIL_PC)


def _pixel(pixel_y: int, x_byte: int = 0) -> int:
    require(0 <= pixel_y < 192 and 0 <= x_byte < 32, "invalid Spectrum bitmap coordinate")
    return 0x4000 | ((pixel_y & 0xC0) << 5) | ((pixel_y & 7) << 8) | ((pixel_y & 0x38) << 2) | x_byte


def _screen() -> bytes:
    data = bytearray(SCREEN_SIZE)
    for row in range(24):
        for scan in range(8):
            base = _pixel(row * 8 + scan) - SCREEN
            for x in range(32):
                data[base + x] = (row * 37 + scan * 11 + x * 3 + 1) & 0xFF
        for x in range(32):
            data[ATTR - SCREEN + row * 32 + x] = (row * 5 + x * 7 + 0x12) & 0x7F
    return bytes(data)


def _scroll(source: bytes, *, width: int = 32, clear_last: bool = True, attrs: bool = True) -> bytes:
    require(len(source) == SCREEN_SIZE, "scroll model requires exact screen image")
    out = bytearray(source)
    for row in range(23):
        for scan in range(8):
            src = _pixel((row + 1) * 8 + scan) - SCREEN
            dst = _pixel(row * 8 + scan) - SCREEN
            out[dst:dst + width] = source[src:src + width]
    if clear_last:
        for scan in range(8):
            dst = _pixel(184 + scan) - SCREEN
            out[dst:dst + 32] = bytes(32)
    attr = ATTR - SCREEN
    if attrs:
        out[attr:attr + 23 * 32] = source[attr + 32:attr + 24 * 32]
    out[attr + 23 * 32:attr + 24 * 32] = bytes([7]) * 32
    return bytes(out)


def _linear(source: bytes) -> bytes:
    out = bytearray(source)
    out[:BITMAP_SIZE - 256] = source[256:BITMAP_SIZE]
    out[BITMAP_SIZE - 256:BITMAP_SIZE] = bytes(256)
    attr = ATTR - SCREEN
    out[attr:attr + 23 * 32] = source[attr + 32:attr + 24 * 32]
    out[attr + 23 * 32:attr + 24 * 32] = bytes([7]) * 32
    return bytes(out)


def _cursor_mutant(source: bytes, *, after_scroll: bool) -> bytes:
    out = bytearray(_scroll(source) if after_scroll else source)
    base = (8 if after_scroll else 8)  # row 1, column 0
    for scan in range(8):
        out[_pixel(base + scan) - SCREEN] ^= 0xF0
    return bytes(out) if after_scroll else _scroll(bytes(out))


def _source_contract(root: Path) -> list[dict[str, object]]:
    tty32 = (root / "v1/src/kernel/tty32.asm").read_text(encoding="utf-8").lower()
    console = (root / "v1/src/kernel/console.asm").read_text(encoding="utf-8").lower()
    architecture = " ".join((root / "docs/01-ZX-UX-ARCHITECTURE-REV12.md").read_text(encoding="utf-8").lower().split())
    bitmap = tty32[tty32.index("zx48_tty_scroll_bitmap:"):tty32.index("tty32_glyph:")]
    clear = tty32[tty32.index("zx48_tty_clear_last_bitmap_row:"):tty32.index("zx48_tty_scroll_bitmap:")]
    scroll = console[console.index("zx48_console_scroll:"):console.index("zx48_tty_ioctl:")]
    wrap = console[console.index("zx48_console_wrap_now:"):console.index("zx48_console_write:")]
    printable = console[console.index("zx48_console_print:"):console.index("zx48_console_wrap_now:")]
    control = console[console.index("zx48_console_control_begin:"):console.index("zx48_console_printable:")]
    source = _screen()
    golden = _scroll(source)
    wrong_attrs = bytearray(golden)
    attr = ATTR - SCREEN
    wrong_attrs[attr + 22 * 32:attr + 23 * 32] = source[attr + 22 * 32:attr + 23 * 32]
    return [
        {"name": "bitmap-rows-0-through-22", "passed": "cp 23" in bitmap},
        {"name": "bitmap-eight-scanlines", "passed": "cp 8" in bitmap},
        {"name": "bitmap-canonical-address-helper", "passed": bitmap.count("call zx48_bitmap_address") >= 2},
        {"name": "bitmap-exact-32-byte-ldir", "passed": "ld bc,32" in bitmap and "ldir" in bitmap},
        {"name": "bitmap-not-linear-6144-copy", "passed": "6144" not in bitmap and "bitmap_start+" not in bitmap},
        {"name": "last-eight-scans-clear-32", "passed": all(x in clear for x in ("ld b,184", "ld d,8", "ld b,32", "xor a", "ld (hl),a"))},
        {"name": "attributes-exact-23x32", "passed": "ld bc,23*32" in scroll and "ldir" in scroll},
        {"name": "last-attribute-row-default-seven", "passed": all(x in scroll for x in ("ld hl,attr_start+23*32", "ld b,32", "ld a,7"))},
        {"name": "scroll-does-not-toggle-cursor", "passed": "zx48_cursor_hide" not in scroll and "zx48_cursor_show" not in scroll},
        {"name": "single-production-scroll-edge", "passed": console.count("call zx48_console_scroll") == 1 and "call zx48_console_scroll" in wrap},
        {"name": "printable-wrap-is-bracketed", "passed": printable.index("call zx48_cursor_hide") < printable.index("call nz,zx48_console_wrap_now") and "jp zx48_cursor_show" in printable},
        {"name": "moving-control-wrap-is-bracketed", "passed": "jp zx48_cursor_hide" in control and "call zx48_console_wrap_now" in control and "jp zx48_cursor_show" in control},
        {"name": "architecture-scroll-contract-present", "passed": all(x in architecture for x in ("32 bitmap bytes", "23*32 attribute bytes", "final 8 bitmap scanlines are cleared"))},
        {"name": "linear-negative-sensitive", "passed": _linear(source) != golden},
        {"name": "31-byte-negative-sensitive", "passed": _scroll(source, width=31) != golden},
        {"name": "33-byte-negative-sensitive", "passed": _scroll(source, width=33) != golden},
        {"name": "attribute-count-negative-sensitive", "passed": bytes(wrong_attrs) != golden},
        {"name": "uncleared-last-row-negative-sensitive", "passed": _scroll(source, clear_last=False) != golden},
        {"name": "cursor-copy-negative-sensitive", "passed": _cursor_mutant(source, after_scroll=False) != golden},
        {"name": "nested-redraw-negative-sensitive", "passed": _cursor_mutant(source, after_scroll=True) != golden},
    ]


def _patch(kernel: bytes, source: bytes, expected: bytes):
    def apply(ram: bytearray) -> None:
        ram[phase1.KERNEL_BASE - SCREEN:phase1.KERNEL_BASE - SCREEN + len(kernel)] = kernel
        ram[:SCREEN_SIZE] = source
        ram[EXPECTED - SCREEN:EXPECTED - SCREEN + SCREEN_SIZE] = expected
        ram[GUARD_LOW - SCREEN] = 0xA5
        ram[GUARD_HIGH - SCREEN] = 0x5A
    return apply


def _compare(code: bytearray, *, mismatch: int, equal: int) -> None:
    code += b"\x21" + _word(SCREEN) + b"\x11" + _word(EXPECTED) + b"\x01" + _word(SCREEN_SIZE)
    loop = ENTRY_PC + len(code)
    code += b"\x1A\xBE" + _jp_nz(mismatch) + b"\x13\x23\x0B\x78\xB1" + _jp_nz(loop) + _jp(equal)


def _fixture(root: Path, labels: dict[str, int], kernel: bytes, source: bytes, expected: bytes, *, bracketed: bool) -> None:
    code = bytearray(b"\xF3" + phase1._ld_sp(phase1.USER_STACK))
    for name, value in (("tty_mode", 64), ("tty_row", 1), ("tty_col", 0), ("tty_cursor_shape", 2), ("tty_cursor_visible", 0), ("cursor_phase", 1), ("cursor_service_parity", 0), ("screen_mutation_depth", 0)):
        code += _store(labels[name], value)
    code += _call(labels["zx48_cursor_service"]) + _expect(labels["tty_cursor_visible"], 1)
    if bracketed:
        code += _call(labels["zx48_cursor_hide"]) + _expect(labels["tty_cursor_visible"], 0)
    code += _call(labels["zx48_console_scroll"])
    if bracketed:
        code += _expect(labels["tty_cursor_visible"], 0) + _expect(GUARD_LOW, 0xA5) + _expect(GUARD_HIGH, 0x5A)
        _compare(code, mismatch=FAIL_PC, equal=PASS_PC)
    else:
        _compare(code, mismatch=PASS_PC, equal=FAIL_PC)
    run_sna(root, bytes(code), patch=_patch(kernel, source, expected))


def dispatch(root: Path, action: str, step: str, *, sha256_file: Callable[[Path], str], run_command: Callable[..., Any], require_project_tool: Callable[[Path, str | Path], Path]):
    if step != "P1.23":
        raise Tty64ScrollError(f"tty64 scroll step is not registered: {step}")
    assertions = _source_contract(root)
    failed = [x["name"] for x in assertions if x["passed"] is not True]
    require(not failed, f"static P1.23 failures: {failed}")
    command, kernel_path, listing = phase1._assemble_kernel(root, run_command, require_project_tool)
    labels = phase1._labels(listing, ("zx48_console_scroll", "zx48_cursor_service", "zx48_cursor_hide", "tty_mode", "tty_row", "tty_col", "tty_cursor_shape", "tty_cursor_visible", "cursor_phase", "cursor_service_parity", "screen_mutation_depth"))
    kernel = kernel_path.read_bytes()
    source = _screen()
    expected = _scroll(source)
    if action == "test":
        _fixture(root, labels, kernel, source, expected, bracketed=True)
        _fixture(root, labels, kernel, source, expected, bracketed=False)
        assertions.extend((
            {"name": "golden-24-row-scroll-byte-exact", "passed": True},
            {"name": "display-guards-survive", "passed": True},
            {"name": "hidden-cursor-remains-hidden", "passed": True},
            {"name": "unbracketed-visible-cursor-detected", "passed": True},
        ))
    hashes = {
        "docs/01-ZX-UX-ARCHITECTURE-REV12.md": sha256_file(root / "docs/01-ZX-UX-ARCHITECTURE-REV12.md"),
        "v1/build/kernel.bin": sha256_file(kernel_path),
        "v1/src/kernel/console.asm": sha256_file(root / "v1/src/kernel/console.asm"),
        "v1/src/kernel/cursor.asm": sha256_file(root / "v1/src/kernel/cursor.asm"),
        "v1/src/kernel/tty32.asm": sha256_file(root / "v1/src/kernel/tty32.asm"),
        "v1/tools-host/test-driver/phase1_scroll.py": sha256_file(root / "v1/tools-host/test-driver/phase1_scroll.py"),
    }
    return [command], hashes, assertions
