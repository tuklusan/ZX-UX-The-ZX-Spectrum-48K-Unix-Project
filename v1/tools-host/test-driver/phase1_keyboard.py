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

KEY_VALUE_ADDR = 0xA100
CAPS_ROW_PATTERN = bytes((0x01, 0xFE, 0xFE, 0xED, 0x78, 0xCB, 0x47))
SPACE_ROW_PATTERN = bytes((0x01, 0xFE, 0x7F, 0xED, 0x78, 0xCB, 0x47))


class KeyboardMatrixError(DriverError):
    """Raised when the Phase-1 keyboard/BREAK correction contract is violated."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise KeyboardMatrixError(message)


def _word(value: int) -> bytes:
    return bytes((value & 0xFF, (value >> 8) & 0xFF))


def _call(address: int) -> bytes:
    return b"\xCD" + _word(address)


def _jp(address: int) -> bytes:
    return b"\xC3" + _word(address)


def _jp_nz(address: int) -> bytes:
    return b"\xC2" + _word(address)


def _jp_c(address: int) -> bytes:
    return b"\xDA" + _word(address)


def _jp_nc(address: int) -> bytes:
    return b"\xD2" + _word(address)


def _ld_sp(address: int) -> bytes:
    return b"\x31" + _word(address)


def _store_byte(address: int, value: int) -> bytes:
    return bytes((0x3E, value & 0xFF, 0x32)) + _word(address)


def _load_byte(address: int) -> bytes:
    return b"\x3A" + _word(address)


def _patched_break_rows(kernel_bytes: bytes, caps_row: int, space_row: int) -> bytes:
    patched = bytearray(kernel_bytes)
    for pattern, value, name in (
        (CAPS_ROW_PATTERN, caps_row, "CAPS SHIFT row"),
        (SPACE_ROW_PATTERN, space_row, "SPACE row"),
    ):
        offsets: list[int] = []
        cursor = 0
        while True:
            offset = patched.find(pattern, cursor)
            if offset < 0:
                break
            offsets.append(offset)
            cursor = offset + 1
        require(len(offsets) == 1, f"{name} scan sequence must occur exactly once")
        offset = offsets[0] + 3
        patched[offset:offset + 2] = bytes((0x3E, value & 0xFF))  # LD A,n replaces IN A,(C)
    return bytes(patched)


def _stub_keyboard_rom(kernel_bytes: bytes, labels: dict[str, int]) -> bytes:
    patched = bytearray(kernel_bytes)

    def replace(label: str, payload: bytes) -> None:
        offset = labels[label] - phase1.KERNEL_BASE
        require(0 <= offset <= len(patched) - 6, f"{label} outside kernel image")
        require(len(payload) <= 6, f"{label} fixture stub too large")
        patched[offset:offset + 6] = payload + b"\x00" * (6 - len(payload))

    replace("zx48_rom_key_scan", b"\x16\x01\xAF\xC9")          # LD D,1; XOR A; RET (Z=1)
    replace("zx48_rom_k_test", b"\xAF\x37\xC9")                # XOR A; SCF; RET
    replace("zx48_rom_key_decode", b"\x3A" + _word(KEY_VALUE_ADDR) + b"\xB7\xC9")
    return bytes(patched)


def _source_contract(root: Path) -> list[dict[str, object]]:
    interrupt = (root / "v1/src/kernel/interrupt.asm").read_text(encoding="utf-8")
    keyboard = (root / "v1/src/kernel/keyboard.asm").read_text(encoding="utf-8")
    interrupt_lower = interrupt.lower()
    keyboard_lower = keyboard.lower()
    return [
        {"name": "caps-row-16bit-bc", "passed": "ld bc,$fefe" in interrupt_lower and "in a,(c)" in interrupt_lower},
        {"name": "space-row-16bit-bc", "passed": "ld bc,$7ffe" in interrupt_lower and interrupt_lower.count("in a,(c)") >= 2},
        {"name": "break-active-low-bit0", "passed": interrupt_lower.count("bit 0,a") >= 2},
        {"name": "im2-does-not-call-rom-keyboard", "passed": "call zx48_rom_key" not in interrupt_lower and "call rom_key" not in interrupt_lower},
        {"name": "im2-only-publishes-break-flag", "passed": "ld (break_pending),a" in interrupt_lower and "zx48_keyboard_decode" not in interrupt_lower},
        {"name": "foreground-rom-decode", "passed": all(token in keyboard_lower for token in ("call zx48_rom_key_scan", "call zx48_rom_k_test", "call zx48_rom_key_decode"))},
        {"name": "delete-maps-backspace", "passed": "cp $0c" in keyboard_lower and "ld a,$08" in keyboard_lower},
        {"name": "input-wait-is-cooperative", "passed": "ld (ix+proc_state),proc_wait_input" in keyboard_lower and "jp zx48_schedule" in keyboard_lower},
        {"name": "wake-decode-outside-im2", "passed": "zx48_keyboard_wake_input:" in keyboard_lower and "call zx48_keyboard_decode" in keyboard_lower},
    ]


def _break_matrix_test(root: Path, labels: dict[str, int], kernel_bytes: bytes) -> None:
    interrupt = labels["zx48_interrupt"]
    busy = labels["altreg_busy"]
    pending = labels["break_pending"]
    cases = (
        (0x1F, 0x1F, 0, "neither"),
        (0x1E, 0x1F, 0, "caps-only"),
        (0x1F, 0x1E, 0, "space-only"),
        (0x1E, 0x1E, 1, "break"),
    )
    for caps_row, space_row, expected, _name in cases:
        code = bytearray()
        code += b"\xF3" + _ld_sp(phase1.USER_STACK)
        code += _store_byte(pending, 0)
        code += _store_byte(busy, 1)
        code += _call(interrupt)
        code += _load_byte(pending) + bytes((0xFE, expected)) + _jp_nz(FAIL_PC)
        code += _jp(PASS_PC)
        patched = _patched_break_rows(kernel_bytes, caps_row, space_row)
        run_sna(root, bytes(code), patch=phase1._kernel_patch(patched))


def _decode_matrix_test(root: Path, labels: dict[str, int], kernel_bytes: bytes) -> None:
    decode = labels["zx48_keyboard_decode"]
    e_again = labels["E_AGAIN"]
    patched = _stub_keyboard_rom(kernel_bytes, labels)
    accepted = (
        (0x20, 0x20),
        (0x41, 0x41),
        (0x7F, 0x7F),
        (0x08, 0x08),
        (0x09, 0x09),
        (0x0A, 0x0A),
        (0x0B, 0x0B),
        (0x0C, 0x08),
        (0x0D, 0x0D),
    )
    rejected = (0x00, 0x07, 0x0E, 0x1F, 0x80, 0xFF)

    code = bytearray()
    code += b"\xF3" + _ld_sp(phase1.USER_STACK)
    for value, expected in accepted:
        code += _store_byte(KEY_VALUE_ADDR, value)
        code += _call(decode) + _jp_c(FAIL_PC)
        code += bytes((0xFE, expected)) + _jp_nz(FAIL_PC)
    for value in rejected:
        code += _store_byte(KEY_VALUE_ADDR, value)
        code += _call(decode) + _jp_nc(FAIL_PC)
        code += bytes((0xFE, e_again & 0xFF)) + _jp_nz(FAIL_PC)
    code += _jp(PASS_PC)
    run_sna(root, bytes(code), patch=phase1._kernel_patch(patched))


def dispatch(
    root: Path,
    action: str,
    step: str,
    *,
    sha256_file: Callable[[Path], str],
    run_command: Callable[..., Any],
    require_project_tool: Callable[[Path, str | Path], Path],
):
    if step != "P1.31":
        raise KeyboardMatrixError(f"keyboard/BREAK step is not registered: {step}")

    assertions = _source_contract(root)
    failed = [item["name"] for item in assertions if item["passed"] is not True]
    require(not failed, f"static keyboard/BREAK failures: {failed}")

    command, kernel, listing = phase1._assemble_kernel(root, run_command, require_project_tool)
    names = (
        "zx48_interrupt",
        "altreg_busy",
        "break_pending",
        "zx48_keyboard_decode",
        "zx48_rom_key_scan",
        "zx48_rom_k_test",
        "zx48_rom_key_decode",
        "E_AGAIN",
    )
    labels = phase1._labels(listing, names)
    kernel_bytes = kernel.read_bytes()

    if action == "test":
        _break_matrix_test(root, labels, kernel_bytes)
        _decode_matrix_test(root, labels, kernel_bytes)
        assertions.extend(
            [
                {"name": "break-raw-matrix-positive", "passed": True},
                {"name": "non-break-raw-matrix-negative", "passed": True},
                {"name": "foreground-key-decode-matrix", "passed": True},
                {"name": "unsupported-control-negative", "passed": True},
            ]
        )

    paths = (
        root / "v1/src/kernel/interrupt.asm",
        root / "v1/src/kernel/keyboard.asm",
        root / "v1/tools-host/test-driver/phase1_keyboard.py",
        kernel,
    )
    return [command], {str(path.relative_to(root)): sha256_file(path) for path in paths}, assertions
