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
SYS_CON_WRITE = 0x32
E_INVAL = 0x01
ROM_IY_ANCHOR = 0x5C3A
F4X8_SIZE = 392
F4X8_HEADER = b"F4X8\x01\x20\x60\x00"
FONT_SOURCE = 0xB200
STREAM = 0x7C00
BASELINE = 0x6000
BASELINE_ROW = 0x7B00
BASELINE_COL = 0x7B01
BASELINE_PENDING = 0x7B02
SCREEN = 0x4000
SCREEN_SIZE = 6912


class ConWriteAbiError(DriverError):
    """Raised when the P1.36 SYS_CON_WRITE contract is violated."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ConWriteAbiError(message)


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
    return b"\x3A" + _word(right) + b"\x47\x3A" + _word(left) + b"\xB8" + _jp_nz(FAIL_PC)


def _expect_hl(value: int) -> bytes:
    return phase1._ld_de(value) + b"\xB7\xED\x52" + _jp_nz(FAIL_PC)


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
    conwrite = _block(syscall, "zx48_sys_con_write:", "zx48_sys_con_clear:")
    validator = _block(syscall, "zx48_user_range_validate:", "zx48_sys_put16:")
    write = _block(console, "zx48_console_write:", "zx48_console_scroll:")

    zero_first = _ordered(
        conwrite,
        (
            "ld bc,(syscall_arg_bc)",
            "ld a,b",
            "or c",
            "jp z,zx48_sys_zero_result",
            "ld hl,(syscall_arg_hl)",
            "call zx48_user_range_validate",
        ),
    )
    reloaded = _ordered(
        conwrite,
        (
            "call zx48_user_range_validate",
            "ret c",
            "ld hl,(syscall_arg_hl)",
            "ld bc,(syscall_arg_bc)",
            "call zx48_console_write",
            "ret c",
            "xor a",
            "ret",
        ),
    )
    widened = _ordered(
        validator,
        (
            "ld a,b",
            "or c",
            "jr z,zx48_user_range_ok",
            "push hl",
            "add hl,bc",
            "jr c,zx48_user_range_wrap",
            "dec hl",
            "ex de,hl",
            "pop hl",
        ),
    )
    user_arena = _ordered(
        validator,
        (
            "cp $60",
            "jr c,zx48_user_range_bad",
            "cp $e0",
            "jr nc,zx48_user_range_bad",
            "ld a,d",
            "cp $60",
            "jr c,zx48_user_range_bad",
            "cp $e0",
            "jr nc,zx48_user_range_bad",
        ),
    )
    loop_exact = _ordered(
        write,
        (
            "ld (console_count),bc",
            "ld a,b",
            "or c",
            "jr z,zx48_console_write_done",
            "ld a,(hl)",
            "push hl",
            "push bc",
            "call zx48_console_putchar",
            "pop bc",
            "pop hl",
            "ret c",
            "inc hl",
            "dec bc",
            "jr zx48_console_write_loop",
            "ld hl,(console_count)",
            "xor a",
            "ret",
        ),
    )
    return [
        {"name": "canonical-con-write-syscall-number", "passed": any(line.split() == ["sys_con_write", "equ", "$32"] for line in include.splitlines())},
        {"name": "count-zero-short-circuits-before-pointer-validation", "passed": zero_first},
        {"name": "validated-arguments-reloaded-before-console-write", "passed": reloaded},
        {"name": "range-end-arithmetic-is-widened-and-wrap-rejected", "passed": widened},
        {"name": "user-arena-is-one-contiguous-6000-dfff-range", "passed": user_arena},
        {"name": "console-write-preserves-stream-state-and-returns-original-count", "passed": loop_exact},
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
    return b"\xFD\xE5\xE1" + phase1._ld_de(ROM_IY_ANCHOR) + b"\xB7\xED\x52" + _jp_nz(FAIL_PC)


def _ld_bc(value: int) -> bytes:
    return b"\x01" + _word(value)


def _sys_write(pointer: int, count: int) -> bytes:
    return phase1._ld_hl(pointer) + _ld_bc(count) + bytes((0x3E, SYS_CON_WRITE)) + _call(0xE000)


def _sys_putchar(value: int) -> bytes:
    return phase1._ld_hl(value & 0xFF) + bytes((0x3E, SYS_CON_PUTCHAR)) + _call(0xE000)


def _base_prefix(labels: dict[str, int], *, tty64: bool, asset: bytes) -> tuple[bytearray, tuple[tuple[int, bytes], ...]]:
    code = bytearray(b"\xF3" + phase1._ld_sp(phase1.USER_STACK))
    entries: list[tuple[int, bytes]] = []
    code += _call(labels["zx48_kernel_stack_init"])
    if tty64:
        code += _call(labels["zx48_memory_init"])
        code += phase1._ld_hl(FONT_SOURCE) + _ld_bc(F4X8_SIZE)
        code += _call(labels["zx48_tty64_install_font"]) + _jp_c(FAIL_PC)
        entries.append((FONT_SOURCE, asset))
    code += _call(labels["zx48_console_init"])
    code += _store_byte(labels["tty_cursor_shape"], 0)
    code += _store_byte(labels["tty_cursor_visible"], 0)
    code += _store_byte(labels["screen_mutation_depth"], 0)
    code += _store_byte(labels["cursor_service_parity"], 0)
    code += _store_byte(labels["tty_mode"], 64 if tty64 else 32)
    code += _store_byte(labels["tty_current_attr"], 7)
    return code, tuple(entries)


def _range_fixture(root: Path, labels: dict[str, int], kernel: bytes) -> None:
    guard = 0x4105
    legal = bytes([0x00]) * 32
    code, entries = _base_prefix(labels, tty64=False, asset=b"")
    code += _store_byte(labels["tty_row"], 3)
    code += _store_byte(labels["tty_col"], 5)
    code += _store_byte(labels["tty_wrap_pending"], 1)
    code += phase1._ld_iy(0x1111)
    code += _sys_write(0xE000, 0) + _jp_c(FAIL_PC) + _expect_hl(0) + _expect_iy_anchor()
    code += _expect_byte(labels["tty_row"], 3) + _expect_byte(labels["tty_col"], 5) + _expect_byte(labels["tty_wrap_pending"], 1)

    code += phase1._ld_iy(0x2222)
    code += _sys_write(0xE000, 1) + _jp_nc(FAIL_PC) + bytes((0xFE, E_INVAL)) + _jp_nz(FAIL_PC) + _expect_iy_anchor()
    code += _expect_byte(labels["tty_row"], 3) + _expect_byte(labels["tty_col"], 5) + _expect_byte(labels["tty_wrap_pending"], 1) + _expect_byte(guard, 0xA5)

    code += phase1._ld_iy(0x3333)
    code += _sys_write(0xFFF0, 0x20) + _jp_nc(FAIL_PC) + bytes((0xFE, E_INVAL)) + _jp_nz(FAIL_PC) + _expect_iy_anchor()
    code += _expect_byte(labels["tty_row"], 3) + _expect_byte(labels["tty_col"], 5) + _expect_byte(labels["tty_wrap_pending"], 1) + _expect_byte(guard, 0xA5)

    code += _store_byte(labels["tty_row"], 0) + _store_byte(labels["tty_col"], 0) + _store_byte(labels["tty_wrap_pending"], 0)
    code += phase1._ld_iy(0x4444)
    code += _sys_write(0x7FF0, 0x20) + _jp_c(FAIL_PC) + _expect_hl(0x20) + _expect_iy_anchor()
    code += _expect_byte(labels["tty_row"], 0) + _expect_byte(labels["tty_col"], 0) + _expect_byte(labels["tty_wrap_pending"], 0)
    code += _jp(PASS_PC)
    run_sna(root, bytes(code), patch=_patch(kernel, entries + ((guard, b"\xA5"), (0x7FF0, legal))))


def _reset_stream_state(code: bytearray, labels: dict[str, int], mode: int) -> None:
    code += _call(labels["zx48_console_clear"])
    code += _store_byte(labels["tty_mode"], mode)
    code += _store_byte(labels["tty_row"], 23)
    code += _store_byte(labels["tty_col"], mode - 2)
    code += _store_byte(labels["tty_wrap_pending"], 0)
    code += _store_byte(labels["tty_cursor_shape"], 0)
    code += _store_byte(labels["tty_cursor_visible"], 0)


def _save_baseline(code: bytearray, labels: dict[str, int]) -> None:
    code += phase1._ld_hl(SCREEN) + phase1._ld_de(BASELINE) + _ld_bc(SCREEN_SIZE) + b"\xED\xB0"
    code += b"\x3A" + _word(labels["tty_row"]) + b"\x32" + _word(BASELINE_ROW)
    code += b"\x3A" + _word(labels["tty_col"]) + b"\x32" + _word(BASELINE_COL)
    code += b"\x3A" + _word(labels["tty_wrap_pending"]) + b"\x32" + _word(BASELINE_PENDING)


def _compare_baseline(code: bytearray, labels: dict[str, int]) -> None:
    code += phase1._ld_hl(SCREEN) + phase1._ld_de(BASELINE) + _ld_bc(SCREEN_SIZE)
    loop = ENTRY_PC + len(code)
    code += b"\x1A\xBE" + _jp_nz(FAIL_PC) + b"\x13\x23\x0B\x78\xB1" + _jp_nz(loop)
    code += _expect_equal_bytes(labels["tty_row"], BASELINE_ROW)
    code += _expect_equal_bytes(labels["tty_col"], BASELINE_COL)
    code += _expect_equal_bytes(labels["tty_wrap_pending"], BASELINE_PENDING)
    code += _expect_byte(labels["screen_mutation_depth"], 0)


def _stream_identity_fixture(root: Path, labels: dict[str, int], kernel: bytes, asset: bytes, *, mode: int) -> None:
    stream = bytes((0x41, 0x42, 0x43, 0x08, 0x09, 0x44, 0x0D, 0x45, 0x0A, 0x46))
    code, entries = _base_prefix(labels, tty64=(mode == 64), asset=asset)
    entries = entries + ((STREAM, stream),)

    _reset_stream_state(code, labels, mode)
    code += phase1._ld_iy(0x5555)
    code += _sys_write(STREAM, len(stream)) + _jp_c(FAIL_PC) + _expect_hl(len(stream)) + _expect_iy_anchor()
    _save_baseline(code, labels)

    _reset_stream_state(code, labels, mode)
    offset = 0
    for count in (2, 3, 1, 4):
        code += _sys_write(STREAM + offset, count) + _jp_c(FAIL_PC) + _expect_hl(count)
        offset += count
    code += _expect_iy_anchor()
    _compare_baseline(code, labels)

    _reset_stream_state(code, labels, mode)
    for value in stream:
        code += _sys_putchar(value) + _jp_c(FAIL_PC) + _expect_hl(1)
    code += _expect_iy_anchor()
    _compare_baseline(code, labels)
    code += _jp(PASS_PC)
    run_sna(root, bytes(code), patch=_patch(kernel, entries))


def dispatch(
    root: Path,
    action: str,
    step: str,
    *,
    sha256_file: Callable[[Path], str],
    run_command: Callable[..., Any],
    require_project_tool: Callable[[Path, str | Path], Path],
):
    if step != "P1.36":
        raise ConWriteAbiError(f"console write step is not registered: {step}")
    asset_path = root / "v1/assets/font4x8.bin"
    asset = asset_path.read_bytes()
    require(len(asset) == F4X8_SIZE and asset[:8] == F4X8_HEADER, "invalid F4X8 fixture")
    assertions = _source_contract(root)
    failed = [item["name"] for item in assertions if item["passed"] is not True]
    require(not failed, f"static P1.36 failures: {failed}")

    command, kernel_path, listing = phase1._assemble_kernel(root, run_command, require_project_tool)
    labels = phase1._labels(
        listing,
        (
            "zx48_kernel_stack_init",
            "zx48_memory_init",
            "zx48_tty64_install_font",
            "zx48_console_init",
            "zx48_console_clear",
            "tty_mode",
            "tty_row",
            "tty_col",
            "tty_cursor_shape",
            "tty_cursor_visible",
            "tty_wrap_pending",
            "tty_current_attr",
            "cursor_service_parity",
            "screen_mutation_depth",
        ),
    )
    kernel = kernel_path.read_bytes()

    if action == "test":
        _range_fixture(root, labels, kernel)
        _stream_identity_fixture(root, labels, kernel, asset, mode=32)
        _stream_identity_fixture(root, labels, kernel, asset, mode=64)
        assertions.extend(
            (
                {"name": "count-zero-poison-pointer-does-not-mutate-runtime", "passed": True},
                {"name": "protected-and-wrapped-ranges-fail-before-mutation-runtime", "passed": True},
                {"name": "legal-7ff0-plus-0020-range-is-accepted-runtime", "passed": True},
                {"name": "contiguous-split-and-putchar-streams-are-byte-identical-tty32", "passed": True},
                {"name": "contiguous-split-and-putchar-streams-are-byte-identical-tty64", "passed": True},
                {"name": "console-write-return-count-and-iy-are-exact-runtime", "passed": True},
            )
        )

    paths = (
        root / "docs/01-ZX-UX-ARCHITECTURE-REV12.md",
        root / "v1/assets/font4x8.bin",
        root / "v1/src/kernel/console.asm",
        root / "v1/src/kernel/syscall.asm",
        root / "v1/tools-host/test-driver/phase1_conwrite.py",
        kernel_path,
    )
    return [command], {str(path.relative_to(root)): sha256_file(path) for path in paths}, assertions
