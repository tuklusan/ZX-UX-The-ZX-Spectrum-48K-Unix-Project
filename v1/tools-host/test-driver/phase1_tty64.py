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

F4X8_SIZE = 392
F4X8_HEADER = b"F4X8\x01\x20\x60\x00"
FONT_SOURCE = 0xB200
UDG_SOURCE = 0xB500
UDG_REQUEST = 0xB510
ATTR_START = 0x5800


class Tty64Error(DriverError):
    """Raised when the P1.22 tty64 rendering contract is violated."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Tty64Error(message)


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


def _bitmap_address(pixel_y: int, x_byte: int) -> int:
    require(0 <= pixel_y < 192, "pixel y outside Spectrum bitmap")
    require(0 <= x_byte < 32, "bitmap byte column outside Spectrum bitmap")
    return (
        0x4000
        | ((pixel_y & 0xC0) << 5)
        | ((pixel_y & 0x07) << 8)
        | ((pixel_y & 0x38) << 2)
        | x_byte
    )


def _attr_address(row: int, col: int) -> int:
    require(0 <= row < 24 and 0 <= col < 64, "tty64 attribute coordinate outside screen")
    return ATTR_START + row * 32 + (col >> 1)


def _decode_rows(asset: bytes, code: int) -> tuple[int, ...]:
    require(len(asset) == F4X8_SIZE and asset[:8] == F4X8_HEADER, "P1.22 requires structurally valid F4X8 fixture")
    require(0x20 <= code <= 0x7F, "tty64 code outside F4X8 range")
    index = 8 + (code - 0x20) * 4
    packed = asset[index:index + 4]
    require(len(packed) == 4, "F4X8 glyph truncated")
    rows: list[int] = []
    for value in packed:
        rows.extend(((value >> 4) & 0x0F, value & 0x0F))
    return tuple(rows)


def _patch(kernel: bytes, entries: tuple[tuple[int, bytes], ...]):
    def apply(ram: bytearray) -> None:
        kernel_offset = phase1.KERNEL_BASE - 0x4000
        ram[kernel_offset:kernel_offset + len(kernel)] = kernel
        for address, payload in entries:
            offset = address - 0x4000
            require(0 <= offset <= len(ram) - len(payload), "P1.22 fixture patch outside RAM")
            ram[offset:offset + len(payload)] = payload
    return apply


def _install_prefix(labels: dict[str, int]) -> bytearray:
    code = bytearray(b"\xF3" + phase1._ld_sp(phase1.USER_STACK))
    code += _call(labels["zx48_memory_init"])
    code += b"\x21" + _word(FONT_SOURCE)
    code += b"\x01" + _word(F4X8_SIZE)
    code += _call(labels["zx48_tty64_install_font"])
    code += _jp_c(FAIL_PC)
    return code


def _run_fixture(root: Path, name: str, code: bytes, patch) -> None:
    try:
        run_sna(root, code, patch=patch)
    except DriverError as exc:
        raise Tty64Error(f"P1.22 runtime fixture {name} failed: {exc}") from exc


def _source_contract(root: Path) -> list[dict[str, object]]:
    tty64 = (root / "v1/src/kernel/tty64.asm").read_text(encoding="utf-8").lower()
    tty32 = (root / "v1/src/kernel/tty32.asm").read_text(encoding="utf-8").lower()
    cursor = (root / "v1/src/kernel/cursor.asm").read_text(encoding="utf-8").lower()
    console = (root / "v1/src/kernel/console.asm").read_text(encoding="utf-8").lower()
    udg = (root / "v1/src/kernel/udg.asm").read_text(encoding="utf-8").lower()
    primitives = (root / "v1/src/kernel/z80_primitives.asm").read_text(encoding="utf-8").lower()
    architecture = (root / "docs/01-ZX-UX-ARCHITECTURE-REV12.md").read_text(encoding="utf-8").lower()

    renderer = tty64[tty64.index("zx48_tty64_draw_char:"):tty64.index("zx48_tty64_bad:")]
    bitmap = tty32[tty32.index("zx48_bitmap_address:"):tty32.index("zx48_tty32_draw_char:")]
    cursor_xor = cursor[cursor.index("zx48_cursor_xor:"):cursor.index("zx48_cursor_blink:")]
    udg_draw = udg[udg.index("zx48_udg_draw:"):udg.index("zx48_udg_bad:")]

    return [
        {"name": "tty64-accepts-exact-printable-range", "passed": "cp $20" in renderer and "cp $80" in renderer},
        {"name": "tty64-uses-pinned-f4x8-pointer", "passed": "ld hl,(tty64_font_ptr)" in renderer},
        {"name": "packed-row-high-nibble-precedes-low", "passed": renderer.index("rrca") < renderer.index("zx48_tty64_nibble:") and "and 1" in renderer},
        {"name": "pixel-y-is-row-times-eight-plus-scan", "passed": renderer.count("add a,a") >= 3 and "ld a,(tty64_scan)" in renderer},
        {"name": "x-byte-is-logical-column-shifted-right", "passed": "ld a,(tty_col)\n    srl a\n    ld c,a" in renderer},
        {"name": "renderer-calls-canonical-bitmap-helper", "passed": "call zx48_bitmap_address" in renderer and "zx48_bitmap_address:" in tty32},
        {"name": "console-dispatches-64-mode-to-renderer", "passed": "cp tty_mode_64" in console and "zx48_console_print64:" in console and "call zx48_tty64_draw_char" in console},
        {"name": "canonical-spectrum-address-helper-is-nonlinear", "passed": all(token in bitmap for token in ("and 7", "and $c0", "and $38", "or $40"))},
        {"name": "even-column-preserves-low-nibble", "passed": "and $0f" in renderer and renderer.index("and $0f") < renderer.index("zx48_tty64_right:")},
        {"name": "odd-column-preserves-high-nibble", "passed": "zx48_tty64_right:" in renderer and "and $f0" in renderer},
        {"name": "attributes-use-paired-physical-cell", "passed": "ld a,(tty_col)\n    srl a" in renderer and "ld de,attr_start" in renderer and "ld a,(tty_current_attr)" in renderer},
        {"name": "cursor-xor-never-addresses-attributes", "passed": "attr_start" not in cursor_xor and "xor $f0" in cursor_xor and "xor $0f" in cursor_xor},
        {"name": "udg-draw-writes-full-physical-byte", "passed": "cp 32" in udg_draw and "ld (hl),a" in udg_draw and "and $f0" not in udg_draw and "and $0f" not in udg_draw},
        {"name": "architecture-defines-udg-as-two-tty64-columns", "passed": "a udg drawn while `tty64` is active occupies\ntwo logical text columns" in architecture},
        {"name": "canonical-copy-primitive-remains-ldir", "passed": "zx48_memcpy:" in primitives and "ldir" in primitives},
    ]


def _render_case(
    root: Path,
    labels: dict[str, int],
    kernel: bytes,
    asset: bytes,
    *,
    row: int,
    col: int,
    codepoint: int,
    sentinel: int,
    attribute: int,
) -> None:
    rows = _decode_rows(asset, codepoint)
    x_byte = col >> 1
    patches: list[tuple[int, bytes]] = [(FONT_SOURCE, asset)]
    expected: list[tuple[int, int]] = []
    for scan, nibble in enumerate(rows):
        address = _bitmap_address(row * 8 + scan, x_byte)
        patches.append((address, bytes((sentinel,))))
        if col & 1:
            value = (sentinel & 0xF0) | nibble
        else:
            value = (sentinel & 0x0F) | (nibble << 4)
        expected.append((address, value))
    attr = _attr_address(row, col)
    patches.append((attr, b"\xC3"))

    fixture = _install_prefix(labels)
    fixture += _store_byte(labels["tty_row"], row)
    fixture += _store_byte(labels["tty_col"], col)
    fixture += _store_byte(labels["tty_current_attr"], attribute)
    fixture += bytes((0x3E, codepoint)) + _call(labels["zx48_tty64_draw_char"]) + _jp_c(FAIL_PC)
    for address, value in expected:
        fixture += _expect_byte(address, value)
    fixture += _expect_byte(attr, attribute)
    fixture += _jp(PASS_PC)
    _run_fixture(root, f"render-r{row}-c{col}-x{codepoint:02x}", bytes(fixture), _patch(kernel, tuple(patches)))


def _attribute_pair_runtime(root: Path, labels: dict[str, int], kernel: bytes, asset: bytes) -> None:
    row = 10
    left_col = 20
    right_col = 21
    shared = _attr_address(row, left_col)
    before = shared - 1
    after = shared + 1
    fixture = _install_prefix(labels)
    fixture += _store_byte(labels["tty_row"], row)
    fixture += _store_byte(labels["tty_col"], left_col)
    fixture += _store_byte(labels["tty_current_attr"], 0x12)
    fixture += b"\x3E\x41" + _call(labels["zx48_tty64_draw_char"]) + _jp_c(FAIL_PC)
    fixture += _expect_byte(shared, 0x12) + _expect_byte(before, 0x66) + _expect_byte(after, 0x77)
    fixture += _store_byte(labels["tty_col"], right_col)
    fixture += _store_byte(labels["tty_current_attr"], 0x34)
    fixture += b"\x3E\x42" + _call(labels["zx48_tty64_draw_char"]) + _jp_c(FAIL_PC)
    fixture += _expect_byte(shared, 0x34) + _expect_byte(before, 0x66) + _expect_byte(after, 0x77)
    fixture += _jp(PASS_PC)
    patches = ((FONT_SOURCE, asset), (before, bytes((0x66, 0xA5, 0x77))))
    _run_fixture(root, "attribute-pair-sharing", bytes(fixture), _patch(kernel, patches))


def _cursor_attribute_runtime(root: Path, labels: dict[str, int], kernel: bytes) -> None:
    row = 5
    col = 7
    address = _bitmap_address(row * 8, col >> 1)
    attr = _attr_address(row, col)
    fixture = bytearray(b"\xF3" + phase1._ld_sp(phase1.USER_STACK))
    fixture += _store_byte(labels["tty_mode"], 64)
    fixture += _store_byte(labels["tty_row"], row)
    fixture += _store_byte(labels["tty_col"], col)
    fixture += _store_byte(labels["tty_cursor_shape"], 2)
    fixture += _call(labels["zx48_cursor_xor"])
    fixture += _expect_byte(address, 0xAA)
    fixture += _expect_byte(attr, 0x5A)
    fixture += _jp(PASS_PC)
    _run_fixture(root, "cursor-bitmap-only", bytes(fixture), _patch(kernel, ((address, b"\xA5"), (attr, b"\x5A"))))


def _invalid_glyph_runtime(root: Path, labels: dict[str, int], kernel: bytes, asset: bytes, codepoint: int) -> None:
    row = 2
    col = 2
    address = _bitmap_address(row * 8, col >> 1)
    attr = _attr_address(row, col)
    fixture = _install_prefix(labels)
    fixture += _store_byte(labels["tty_row"], row)
    fixture += _store_byte(labels["tty_col"], col)
    fixture += bytes((0x3E, codepoint & 0xFF)) + _call(labels["zx48_tty64_draw_char"])
    fixture += _jp_nc(FAIL_PC)
    fixture += bytes((0xFE, labels["E_INVAL"] & 0xFF)) + _jp_nz(FAIL_PC)
    fixture += _expect_byte(address, 0x69) + _expect_byte(attr, 0x96)
    fixture += _jp(PASS_PC)
    patches = ((FONT_SOURCE, asset), (address, b"\x69"), (attr, b"\x96"))
    _run_fixture(root, f"invalid-glyph-{codepoint:02x}", bytes(fixture), _patch(kernel, patches))


def _udg_two_column_runtime(root: Path, labels: dict[str, int], kernel: bytes) -> None:
    pattern = bytes((0x81, 0x42, 0x24, 0x18, 0x18, 0x24, 0x42, 0x81))
    row = 23
    physical_col = 31
    patches: list[tuple[int, bytes]] = [(UDG_SOURCE, pattern), (UDG_REQUEST, bytes((0, row, physical_col)))]
    for scan in range(8):
        patches.append((_bitmap_address(row * 8 + scan, physical_col), b"\x00"))

    fixture = bytearray(b"\xF3" + phase1._ld_sp(phase1.USER_STACK))
    fixture += _call(labels["zx48_memory_init"])
    fixture += _call(labels["zx48_udg_init"]) + _jp_c(FAIL_PC)
    fixture += b"\x21" + _word(UDG_SOURCE) + b"\x01\x00\x00"
    fixture += _call(labels["zx48_udg_define"]) + _jp_c(FAIL_PC)
    fixture += b"\x21" + _word(UDG_REQUEST) + _call(labels["zx48_udg_draw"]) + _jp_c(FAIL_PC)
    for scan, value in enumerate(pattern):
        fixture += _expect_byte(_bitmap_address(row * 8 + scan, physical_col), value)
    fixture += _jp(PASS_PC)
    _run_fixture(root, "udg-full-byte-two-columns", bytes(fixture), _patch(kernel, tuple(patches)))


def dispatch(
    root: Path,
    action: str,
    step: str,
    *,
    sha256_file: Callable[[Path], str],
    run_command: Callable[..., Any],
    require_project_tool: Callable[[Path, str | Path], Path],
):
    if step != "P1.22":
        raise Tty64Error(f"tty64 renderer step is not registered: {step}")

    asset_path = root / "v1/assets/font4x8.bin"
    asset = asset_path.read_bytes()
    assertions = _source_contract(root)
    failed = [item["name"] for item in assertions if item["passed"] is not True]
    require(not failed, f"static P1.22 failures: {failed}")

    command, kernel_path, listing = phase1._assemble_kernel(root, run_command, require_project_tool)
    labels = phase1._labels(
        listing,
        (
            "zx48_memory_init",
            "zx48_tty64_install_font",
            "zx48_tty64_draw_char",
            "zx48_cursor_xor",
            "zx48_udg_init",
            "zx48_udg_define",
            "zx48_udg_draw",
            "tty_current_attr",
            "tty_mode",
            "tty_row",
            "tty_col",
            "tty_cursor_shape",
            "E_INVAL",
        ),
    )
    kernel = kernel_path.read_bytes()

    if action == "test":
        for row, col, codepoint, sentinel, attribute in (
            (0, 0, 0x20, 0x0D, 0x07),
            (0, 1, 0x21, 0xA0, 0x17),
            (23, 62, 0x7E, 0x05, 0x47),
            (23, 63, 0x7F, 0xB0, 0x57),
        ):
            _render_case(
                root,
                labels,
                kernel,
                asset,
                row=row,
                col=col,
                codepoint=codepoint,
                sentinel=sentinel,
                attribute=attribute,
            )
        _attribute_pair_runtime(root, labels, kernel, asset)
        _cursor_attribute_runtime(root, labels, kernel)
        _invalid_glyph_runtime(root, labels, kernel, asset, 0x1F)
        _invalid_glyph_runtime(root, labels, kernel, asset, 0x80)
        _udg_two_column_runtime(root, labels, kernel)
        assertions.extend(
            [
                {"name": "golden-boundary-cells-render-with-neighbor-preservation", "passed": True},
                {"name": "code-7f-renders-from-pinned-font", "passed": True},
                {"name": "attribute-pair-sharing-runtime", "passed": True},
                {"name": "cursor-does-not-mutate-attribute-runtime", "passed": True},
                {"name": "out-of-range-glyphs-are-atomic-errors", "passed": True},
                {"name": "udg-full-byte-occupies-two-tty64-columns", "passed": True},
            ]
        )

    hashes = {
        "v1/assets/font4x8.bin": sha256_file(asset_path),
        "v1/build/kernel.bin": sha256_file(kernel_path),
        "v1/src/kernel/tty64.asm": sha256_file(root / "v1/src/kernel/tty64.asm"),
        "v1/src/kernel/tty32.asm": sha256_file(root / "v1/src/kernel/tty32.asm"),
        "v1/src/kernel/cursor.asm": sha256_file(root / "v1/src/kernel/cursor.asm"),
        "v1/src/kernel/console.asm": sha256_file(root / "v1/src/kernel/console.asm"),
        "v1/src/kernel/udg.asm": sha256_file(root / "v1/src/kernel/udg.asm"),
        "v1/src/kernel/z80_primitives.asm": sha256_file(root / "v1/src/kernel/z80_primitives.asm"),
        "docs/01-ZX-UX-ARCHITECTURE-REV12.md": sha256_file(root / "docs/01-ZX-UX-ARCHITECTURE-REV12.md"),
        "v1/tools-host/test-driver/phase1_tty64.py": sha256_file(root / "v1/tools-host/test-driver/phase1_tty64.py"),
    }
    return [command], hashes, assertions
