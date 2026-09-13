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

SYS_CON_SETPOS = 0x35
E_INVAL = 0x01
ROM_IY_ANCHOR = 0x5C3A
SCREEN = 0x4000
SCREEN_SIZE = 6912
BASELINE = 0x6000


class SetPosAbiError(DriverError):
    """Raised when the P1.39 SYS_CON_SETPOS contract is violated."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SetPosAbiError(message)


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
        pos = text.find(token, cursor)
        if pos < 0:
            return False
        cursor = pos + len(token)
    return True


def _source_contract(root: Path) -> list[dict[str, object]]:
    syscall = _strip((root / "v1/src/kernel/syscall.asm").read_text(encoding="utf-8"))
    console = _strip((root / "v1/src/kernel/console.asm").read_text(encoding="utf-8"))
    include = _strip((root / "v1/include/zx48ux.inc").read_text(encoding="utf-8"))
    sys_setpos = _block(syscall, "zx48_sys_con_setpos:", "zx48_sys_mem_info:")
    setpos = _block(console, "zx48_console_setpos:", "zx48_console_bad:")
    exact = _ordered(
        setpos,
        (
            "ld a,h",
            "cp 24",
            "jr nc,zx48_console_bad",
            "ld a,(tty_mode)",
            "dec a",
            "cp l",
            "jr c,zx48_console_bad",
            "call zx48_cursor_hide",
            "ld a,h",
            "ld h,l",
            "ld l,a",
            "ld (tty_row),hl",
            "xor a",
            "ld (tty_wrap_pending),a",
            "jr zx48_console_control_done",
        ),
    )
    validate_end = setpos.find("zx48_console_set_commit:")
    mutate_start = setpos.find("call zx48_cursor_hide")
    return [
        {"name": "canonical-con-setpos-syscall-number", "passed": any(line.split() == ["sys_con_setpos", "equ", "$35"] for line in include.splitlines())},
        {"name": "setpos-syscall-uses-canonical-zero-result", "passed": _ordered(sys_setpos, ("ld hl,(syscall_arg_hl)", "call zx48_console_setpos", "ret c", "jp zx48_sys_zero_result"))},
        {"name": "setpos-validates-real-row-and-mode-column-before-mutation", "passed": exact and 0 <= validate_end < mutate_start},
        {"name": "setpos-commits-private-row-col-order-and-clears-pending", "passed": all(token in setpos for token in ("ld h,l", "ld l,a", "ld (tty_row),hl", "ld (tty_wrap_pending),a"))},
    ]


def _patch(kernel: bytes):
    def apply(ram: bytearray) -> None:
        start = phase1.KERNEL_BASE - 0x4000
        ram[start:start + len(kernel)] = kernel
    return apply


def _save_screen(code: bytearray) -> None:
    code += phase1._ld_hl(SCREEN) + phase1._ld_de(BASELINE) + b"\x01" + _word(SCREEN_SIZE) + b"\xED\xB0"


def _compare_screen(code: bytearray) -> None:
    code += phase1._ld_hl(SCREEN) + phase1._ld_de(BASELINE) + b"\x01" + _word(SCREEN_SIZE)
    loop = ENTRY_PC + len(code)
    code += b"\x1A\xBE" + _jp_nz(FAIL_PC) + b"\x13\x23\x0B\x78\xB1" + _jp_nz(loop)


def _sys_setpos(row: int, col: int) -> bytes:
    return phase1._ld_hl(((row & 0xFF) << 8) | (col & 0xFF)) + bytes((0x3E, SYS_CON_SETPOS)) + _call(0xE000)


def _base_prefix(labels: dict[str, int]) -> bytearray:
    code = bytearray(b"\xF3" + phase1._ld_sp(phase1.USER_STACK))
    code += _call(labels["zx48_kernel_stack_init"])
    code += _call(labels["zx48_console_init"])
    code += _store_byte(labels["screen_mutation_depth"], 0)
    code += _store_byte(labels["cursor_service_parity"], 0)
    return code


def _valid_fixture(root: Path, labels: dict[str, int], kernel: bytes) -> None:
    code = _base_prefix(labels)
    code += _store_byte(labels["tty_cursor_shape"], 0) + _store_byte(labels["tty_cursor_visible"], 0)
    for mode, row, col, iy in ((32, 23, 31, 0x1111), (64, 23, 63, 0x2222), (64, 7, 11, 0x3333)):
        code += _store_byte(labels["tty_mode"], mode)
        code += _store_byte(labels["tty_row"], 3) + _store_byte(labels["tty_col"], 4) + _store_byte(labels["tty_wrap_pending"], 1)
        code += phase1._ld_iy(iy) + _sys_setpos(row, col) + _jp_c(FAIL_PC) + _expect_hl(0) + _expect_iy_anchor()
        code += _expect_byte(labels["tty_row"], row) + _expect_byte(labels["tty_col"], col)
        code += _expect_byte(labels["tty_wrap_pending"], 0) + _expect_byte(labels["screen_mutation_depth"], 0)
    code += _jp(PASS_PC)
    run_sna(root, bytes(code), patch=_patch(kernel))


def _invalid_fixture(root: Path, labels: dict[str, int], kernel: bytes, *, mode: int, bad_row: int, bad_col: int, iy: int) -> None:
    code = _base_prefix(labels)
    code += _store_byte(labels["tty_mode"], mode)
    code += _store_byte(labels["tty_row"], 5) + _store_byte(labels["tty_col"], 7) + _store_byte(labels["tty_wrap_pending"], 1)
    code += _store_byte(labels["tty_cursor_shape"], 2) + _store_byte(labels["tty_cursor_visible"], 0)
    code += _call(labels["zx48_cursor_service"]) + _expect_byte(labels["tty_cursor_visible"], 1)
    _save_screen(code)
    code += phase1._ld_iy(iy) + _sys_setpos(bad_row, bad_col)
    code += _jp_nc(FAIL_PC) + bytes((0xFE, E_INVAL)) + _jp_nz(FAIL_PC) + _expect_iy_anchor()
    code += _expect_byte(labels["tty_row"], 5) + _expect_byte(labels["tty_col"], 7) + _expect_byte(labels["tty_wrap_pending"], 1)
    code += _expect_byte(labels["tty_cursor_visible"], 1) + _expect_byte(labels["screen_mutation_depth"], 0)
    _compare_screen(code)
    code += _jp(PASS_PC)
    run_sna(root, bytes(code), patch=_patch(kernel))


def dispatch(root: Path, action: str, step: str, *, sha256_file: Callable[[Path], str], run_command: Callable[..., Any], require_project_tool: Callable[[Path, str | Path], Path]):
    if step != "P1.39":
        raise SetPosAbiError(f"console setpos step is not registered: {step}")
    assertions = _source_contract(root)
    failed = [x["name"] for x in assertions if x["passed"] is not True]
    require(not failed, f"static P1.39 failures: {failed}")
    command, kernel_path, listing = phase1._assemble_kernel(root, run_command, require_project_tool)
    labels = phase1._labels(listing, (
        "zx48_kernel_stack_init", "zx48_console_init", "zx48_cursor_service",
        "tty_mode", "tty_row", "tty_col", "tty_cursor_shape", "tty_cursor_visible",
        "tty_wrap_pending", "cursor_service_parity", "screen_mutation_depth",
    ))
    kernel = kernel_path.read_bytes()
    if action == "test":
        _valid_fixture(root, labels, kernel)
        _invalid_fixture(root, labels, kernel, mode=32, bad_row=24, bad_col=0, iy=0x4444)
        _invalid_fixture(root, labels, kernel, mode=32, bad_row=0, bad_col=32, iy=0x5555)
        _invalid_fixture(root, labels, kernel, mode=64, bad_row=0, bad_col=64, iy=0x6666)
        assertions.extend((
            {"name": "setpos-valid-max-coordinates-and-clears-pending-runtime", "passed": True},
            {"name": "setpos-row24-fails-atomically-with-visible-cursor-runtime", "passed": True},
            {"name": "setpos-tty32-col32-fails-atomically-runtime", "passed": True},
            {"name": "setpos-tty64-col64-fails-atomically-runtime", "passed": True},
            {"name": "setpos-return-and-iy-are-exact-runtime", "passed": True},
        ))
    paths = (
        root / "docs/01-ZX-UX-ARCHITECTURE-REV12.md",
        root / "v1/include/zx48ux.inc",
        root / "v1/src/kernel/console.asm",
        root / "v1/src/kernel/syscall.asm",
        root / "v1/tools-host/test-driver/phase1_setpos.py",
        kernel_path,
    )
    return [command], {str(path.relative_to(root)): sha256_file(path) for path in paths}, assertions
