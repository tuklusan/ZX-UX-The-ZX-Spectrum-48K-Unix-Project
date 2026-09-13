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

SYS_CON_GETPOS = 0x34
ROM_IY_ANCHOR = 0x5C3A
SCREEN = 0x4000
SCREEN_SIZE = 6912
EXPECTED = 0x6000


class GetPosAbiError(DriverError):
    """Raised when the P1.38 SYS_CON_GETPOS contract is violated."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise GetPosAbiError(message)


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
    include = _strip((root / "v1/include/zx48ux.inc").read_text(encoding="utf-8"))
    sys_getpos = _block(syscall, "zx48_sys_con_getpos:", "zx48_sys_con_setpos:")
    getpos = _block(console, "zx48_console_getpos:", "zx48_console_putchar:")
    exact = _ordered(getpos, ("ld hl,(tty_row)", "ld a,h", "ld h,l", "ld l,a", "xor a", "ret"))
    return [
        {"name": "canonical-con-getpos-syscall-number", "passed": any(line.split() == ["sys_con_getpos", "equ", "$34"] for line in include.splitlines())},
        {"name": "getpos-syscall-is-direct-side-effect-free-return", "passed": _ordered(sys_getpos, ("call zx48_console_getpos", "xor a", "ret"))},
        {"name": "getpos-swaps-private-row-col-storage-into-h-row-l-col", "passed": exact},
        {"name": "getpos-does-not-read-or-encode-wrap-pending", "passed": "tty_wrap_pending" not in getpos and "inc h" not in getpos and "inc l" not in getpos},
        {"name": "getpos-does-not-touch-screen-or-cursor-service", "passed": all(token not in getpos for token in ("bitmap_start", "attr_start", "zx48_cursor", "screen_mutation_depth"))},
    ]


def _screen_pattern() -> bytes:
    return bytes((index * 37 + 11) & 0xFF for index in range(SCREEN_SIZE))


def _patch(kernel: bytes, screen: bytes):
    def apply(ram: bytearray) -> None:
        start = phase1.KERNEL_BASE - 0x4000
        ram[start:start + len(kernel)] = kernel
        ram[:SCREEN_SIZE] = screen
        ram[EXPECTED - 0x4000:EXPECTED - 0x4000 + SCREEN_SIZE] = screen
    return apply


def _compare_screen(code: bytearray) -> None:
    code += phase1._ld_hl(SCREEN) + phase1._ld_de(EXPECTED) + b"\x01" + _word(SCREEN_SIZE)
    loop = ENTRY_PC + len(code)
    code += b"\x1A\xBE" + _jp_nz(FAIL_PC) + b"\x13\x23\x0B\x78\xB1" + _jp_nz(loop)


def _case(code: bytearray, labels: dict[str, int], *, mode: int, row: int, col: int, pending: int, iy: int) -> None:
    code += _store_byte(labels["tty_mode"], mode)
    code += _store_byte(labels["tty_row"], row)
    code += _store_byte(labels["tty_col"], col)
    code += _store_byte(labels["tty_wrap_pending"], pending)
    code += phase1._ld_iy(iy)
    code += bytes((0x3E, SYS_CON_GETPOS)) + _call(0xE000) + _jp_c(FAIL_PC)
    code += _expect_hl((row << 8) | col) + _expect_iy_anchor()
    code += _expect_byte(labels["tty_row"], row) + _expect_byte(labels["tty_col"], col)
    code += _expect_byte(labels["tty_wrap_pending"], pending)
    code += _expect_byte(labels["screen_mutation_depth"], 0)


def _runtime_fixture(root: Path, labels: dict[str, int], kernel: bytes) -> None:
    screen = _screen_pattern()
    code = bytearray(b"\xF3" + phase1._ld_sp(phase1.USER_STACK))
    code += _call(labels["zx48_kernel_stack_init"])
    code += _call(labels["zx48_console_init"])
    code += _store_byte(labels["tty_cursor_shape"], 0)
    code += _store_byte(labels["tty_cursor_visible"], 0)
    code += _store_byte(labels["screen_mutation_depth"], 0)
    _case(code, labels, mode=32, row=23, col=31, pending=0, iy=0x1111)
    _case(code, labels, mode=32, row=23, col=31, pending=1, iy=0x2222)
    _case(code, labels, mode=64, row=23, col=63, pending=0, iy=0x3333)
    _case(code, labels, mode=64, row=23, col=63, pending=1, iy=0x4444)
    _case(code, labels, mode=64, row=7, col=11, pending=1, iy=0x5555)
    _compare_screen(code)
    code += _jp(PASS_PC)
    run_sna(root, bytes(code), patch=_patch(kernel, screen))


def dispatch(
    root: Path,
    action: str,
    step: str,
    *,
    sha256_file: Callable[[Path], str],
    run_command: Callable[..., Any],
    require_project_tool: Callable[[Path, str | Path], Path],
):
    if step != "P1.38":
        raise GetPosAbiError(f"console getpos step is not registered: {step}")
    assertions = _source_contract(root)
    failed = [item["name"] for item in assertions if item["passed"] is not True]
    require(not failed, f"static P1.38 failures: {failed}")
    command, kernel_path, listing = phase1._assemble_kernel(root, run_command, require_project_tool)
    labels = phase1._labels(
        listing,
        (
            "zx48_kernel_stack_init",
            "zx48_console_init",
            "tty_mode",
            "tty_row",
            "tty_col",
            "tty_cursor_shape",
            "tty_cursor_visible",
            "tty_wrap_pending",
            "screen_mutation_depth",
        ),
    )
    kernel = kernel_path.read_bytes()
    if action == "test":
        _runtime_fixture(root, labels, kernel)
        assertions.extend(
            (
                {"name": "getpos-returns-real-max-coordinate-tty32-with-and-without-pending", "passed": True},
                {"name": "getpos-returns-real-max-coordinate-tty64-with-and-without-pending", "passed": True},
                {"name": "getpos-does-not-swap-row-column-runtime", "passed": True},
                {"name": "getpos-is-screen-state-and-wrap-side-effect-free-runtime", "passed": True},
                {"name": "getpos-canonicalizes-iy-runtime", "passed": True},
            )
        )
    paths = (
        root / "docs/01-ZX-UX-ARCHITECTURE-REV12.md",
        root / "v1/include/zx48ux.inc",
        root / "v1/src/kernel/console.asm",
        root / "v1/src/kernel/syscall.asm",
        root / "v1/tools-host/test-driver/phase1_getpos.py",
        kernel_path,
    )
    return [command], {str(path.relative_to(root)): sha256_file(path) for path in paths}, assertions
