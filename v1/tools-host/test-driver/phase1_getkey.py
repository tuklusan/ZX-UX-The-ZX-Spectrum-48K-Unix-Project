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

SYS_CON_GETKEY = 0x30
E_BUSY = 0x04
E_AGAIN = 0x0D
KEY_VALUE = 0x41
ROM_IY_ANCHOR = 0x5C3A
PROC_STATE = 2
PROC_WAIT_INPUT = 4
PROC_DESC_SIZE = 48
VERIFY_PC = 0xB100


class GetKeyAbiError(DriverError):
    """Raised when the P1.34 SYS_CON_GETKEY contract is violated."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise GetKeyAbiError(message)


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


def _ld_bc(value: int) -> bytes:
    return b"\x01" + _word(value)


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
    keyboard = _strip((root / "v1/src/kernel/keyboard.asm").read_text(encoding="utf-8"))
    cursor = _strip((root / "v1/src/kernel/cursor.asm").read_text(encoding="utf-8"))
    include = _strip((root / "v1/include/zx48ux.inc").read_text(encoding="utf-8"))
    sys_getkey = _block(syscall, "zx48_sys_con_getkey:", "zx48_sys_con_putchar:")
    keyboard_init = _block(keyboard, "zx48_keyboard_init:", "zx48_keyboard_decode:")
    keyboard_getkey = _block(keyboard, "zx48_keyboard_getkey:", "zx48_keyboard_wake_input:")
    keyboard_wake = _block(keyboard, "zx48_keyboard_wake_input:", "zx48_keyboard_busy:")
    keyboard_release = _block(keyboard, "zx48_keyboard_release:", "endm")
    cursor_service = _block(cursor, "zx48_cursor_service:", "zx48_cursor_blink:")

    result_exact = _ordered(
        sys_getkey,
        (
            "call zx48_keyboard_getkey",
            "ret c",
            "ld l,a",
            "ld h,0",
            "xor a",
            "ret",
        ),
    )
    owner_exact = _ordered(
        keyboard_getkey,
        (
            "ld a,(current_pid)",
            "or a",
            "jr z,zx48_keyboard_busy",
            "ld b,a",
            "ld a,(tty_input_owner)",
            "cp b",
            "jr nz,zx48_keyboard_busy",
            "call zx48_cursor_service",
            "call zx48_keyboard_decode",
        ),
    )
    wait_exact = _ordered(
        keyboard_getkey,
        (
            "call zx48_keyboard_decode",
            "ret nc",
            "ld a,(current_pid)",
            "call zx48_process_lookup",
            "ret c",
            "ld (ix+proc_state),proc_wait_input",
            "jp zx48_schedule",
        ),
    )
    release_exact = _ordered(
        keyboard_release,
        (
            "ld a,(current_pid)",
            "ld b,a",
            "ld a,(tty_input_owner)",
            "cp b",
            "ret nz",
            "xor a",
            "ld (tty_input_owner),a",
            "ret",
        ),
    )
    return [
        {"name": "canonical-getkey-syscall-number", "passed": "sys_con_getkey           equ $30" in include},
        {"name": "getkey-has-no-argument-dependency", "passed": "syscall_arg_" not in sys_getkey},
        {"name": "getkey-success-is-exact-h0-lbyte", "passed": result_exact},
        {"name": "tty-owner-zero-is-unowned-at-init", "passed": _ordered(keyboard_init, ("xor a", "ld (tty_input_owner),a", "ld (break_pending),a", "ret"))},
        {"name": "nonzero-current-owner-is-required", "passed": owner_exact and "handle_free" not in keyboard_getkey},
        {"name": "getkey-never-auto-claims-owner", "passed": "ld (tty_input_owner),a" not in keyboard_getkey},
        {"name": "owner-zero-is-single-unowned-representation", "passed": release_exact and "handle_free" not in keyboard_wake and "handle_free" not in keyboard_release},
        {"name": "safe-cursor-service-precedes-decode", "passed": owner_exact},
        {"name": "no-key-reblocks-cooperatively-after-service", "passed": wait_exact},
        {"name": "safe-cursor-service-does-not-write-logical-position", "passed": all(token not in cursor_service for token in ("ld (tty_row)", "ld (tty_col)", "ld (tty_wrap_pending)"))},
        {"name": "reject-stale-high-byte-shape", "passed": not result_exact or "ld h,0" in sys_getkey},
    ]


def _patch(
    kernel_bytes: bytes,
    replacements: tuple[tuple[int, bytes], ...] = (),
    extras: tuple[tuple[int, bytes], ...] = (),
):
    patched = bytearray(kernel_bytes)
    for address, payload in replacements:
        offset = address - phase1.KERNEL_BASE
        require(0 <= offset <= len(patched) - len(payload), "kernel replacement outside image")
        patched[offset:offset + len(payload)] = payload

    def apply(ram: bytearray) -> None:
        start = phase1.KERNEL_BASE - 0x4000
        ram[start:start + len(patched)] = patched
        for address, payload in extras:
            offset = address - 0x4000
            require(0 <= offset <= len(ram) - len(payload), "fixture patch outside RAM")
            ram[offset:offset + len(payload)] = payload

    return apply


def _decode_key_stub() -> bytes:
    return bytes((0x3E, KEY_VALUE, 0xB7, 0xC9))  # LD A,key; OR A; RET


def _decode_again_stub() -> bytes:
    return bytes((0x3E, E_AGAIN, 0x37, 0xC9))  # LD A,E_AGAIN; SCF; RET


def _setup_cursor_state(labels: dict[str, int]) -> bytes:
    return b"".join(
        (
            _store_byte(labels["cursor_service_parity"], 1),
            _store_byte(labels["screen_mutation_depth"], 0),
            _store_byte(labels["tty_cursor_shape"], 0),
            _store_byte(labels["tty_cursor_visible"], 0),
            _store_byte(labels["tty_row"], 7),
            _store_byte(labels["tty_col"], 9),
            _store_byte(labels["tty_wrap_pending"], 1),
        )
    )


def _expect_cursor_state(labels: dict[str, int], parity: int) -> bytes:
    return b"".join(
        (
            _expect_byte(labels["cursor_service_parity"], parity),
            _expect_byte(labels["tty_row"], 7),
            _expect_byte(labels["tty_col"], 9),
            _expect_byte(labels["tty_wrap_pending"], 1),
        )
    )


def _expect_iy_anchor() -> bytes:
    return b"\xFD\xE5\xE1" + phase1._ld_de(ROM_IY_ANCHOR) + b"\xB7\xED\x52" + _jp_nz(FAIL_PC)


def _success_fixture(root: Path, labels: dict[str, int], kernel_bytes: bytes) -> None:
    code = bytearray(b"\xF3" + phase1._ld_sp(phase1.USER_STACK))
    code += _call(labels["zx48_kernel_stack_init"])
    code += _store_byte(labels["current_pid"], 1)
    code += _store_byte(labels["tty_input_owner"], 1)
    code += _setup_cursor_state(labels)
    code += phase1._ld_iy(0x1234)
    code += phase1._ld_hl(0xBEEF) + phase1._ld_de(0xCAFE) + _ld_bc(0x55AA)
    code += bytes((0x3E, SYS_CON_GETKEY)) + _call(0xE000)
    code += _jp_c(FAIL_PC) + b"\xB7" + _jp_nz(FAIL_PC)
    code += phase1._ld_de(KEY_VALUE) + b"\xB7\xED\x52" + _jp_nz(FAIL_PC)
    code += _expect_iy_anchor()
    code += _expect_cursor_state(labels, 0)
    code += _jp(PASS_PC)
    run_sna(
        root,
        bytes(code),
        patch=_patch(kernel_bytes, ((labels["zx48_keyboard_decode"], _decode_key_stub()),)),
    )


def _ownership_negative_fixture(root: Path, labels: dict[str, int], kernel_bytes: bytes) -> None:
    code = bytearray(b"\xF3" + phase1._ld_sp(phase1.USER_STACK))
    code += _call(labels["zx48_kernel_stack_init"])
    code += _store_byte(labels["current_pid"], 2)
    code += _store_byte(labels["tty_input_owner"], 1)
    code += _setup_cursor_state(labels)
    code += phase1._ld_iy(0x2222)
    code += bytes((0x3E, SYS_CON_GETKEY)) + _call(0xE000)
    code += _jp_nc(FAIL_PC) + bytes((0xFE, E_BUSY)) + _jp_nz(FAIL_PC)
    code += _expect_byte(labels["tty_input_owner"], 1)
    code += _expect_cursor_state(labels, 1)
    code += _expect_iy_anchor()

    code += _store_byte(labels["current_pid"], 1)
    code += _call(labels["zx48_keyboard_release"])
    code += _expect_byte(labels["tty_input_owner"], 0)
    code += phase1._ld_iy(0x3333)
    code += bytes((0x3E, SYS_CON_GETKEY)) + _call(0xE000)
    code += _jp_nc(FAIL_PC) + bytes((0xFE, E_BUSY)) + _jp_nz(FAIL_PC)
    code += _expect_byte(labels["tty_input_owner"], 0)
    code += _expect_iy_anchor() + _jp(PASS_PC)
    run_sna(
        root,
        bytes(code),
        patch=_patch(kernel_bytes, ((labels["zx48_keyboard_decode"], _decode_key_stub()),)),
    )


def _reblock_fixture(root: Path, labels: dict[str, int], kernel_bytes: bytes) -> None:
    table = labels["process_table"]
    p1 = table + PROC_DESC_SIZE
    verifier = (
        _expect_cursor_state(labels, 0)
        + _expect_byte(p1 + PROC_STATE, PROC_WAIT_INPUT)
        + _jp(PASS_PC)
    )
    code = bytearray(b"\xF3" + phase1._ld_sp(phase1.USER_STACK))
    code += _call(labels["zx48_kernel_stack_init"])
    code += _call(labels["zx48_process_init"])
    code += _call(labels["zx48_process_prepare_pid1"])
    code += _store_byte(labels["current_pid"], 1)
    code += _store_byte(labels["tty_input_owner"], 1)
    code += _setup_cursor_state(labels)
    code += bytes((0x3E, SYS_CON_GETKEY)) + _call(0xE000) + _jp(FAIL_PC)
    run_sna(
        root,
        bytes(code),
        patch=_patch(
            kernel_bytes,
            (
                (labels["zx48_keyboard_decode"], _decode_again_stub()),
                (labels["zx48_schedule"], _jp(VERIFY_PC)),
            ),
            ((VERIFY_PC, verifier),),
        ),
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
    if step != "P1.34":
        raise GetKeyAbiError(f"getkey step is not registered: {step}")

    assertions = _source_contract(root)
    failed = [item["name"] for item in assertions if item["passed"] is not True]
    require(not failed, f"static P1.34 failures: {failed}")

    command, kernel, listing = phase1._assemble_kernel(root, run_command, require_project_tool)
    labels = phase1._labels(
        listing,
        (
            "zx48_kernel_stack_init",
            "zx48_process_init",
            "zx48_process_prepare_pid1",
            "zx48_keyboard_decode",
            "zx48_keyboard_release",
            "zx48_schedule",
            "process_table",
            "current_pid",
            "tty_input_owner",
            "cursor_service_parity",
            "screen_mutation_depth",
            "tty_cursor_shape",
            "tty_cursor_visible",
            "tty_row",
            "tty_col",
            "tty_wrap_pending",
        ),
    )
    kernel_bytes = kernel.read_bytes()

    if action == "test":
        _success_fixture(root, labels, kernel_bytes)
        _ownership_negative_fixture(root, labels, kernel_bytes)
        _reblock_fixture(root, labels, kernel_bytes)
        assertions.extend(
            [
                {"name": "owner-getkey-exact-byte-and-iy-runtime", "passed": True},
                {"name": "background-release-and-unowned-read-rejected-runtime", "passed": True},
                {"name": "wake-boundary-parity-consumed-with-position-exact", "passed": True},
            ]
        )

    paths = (
        root / "v1/src/kernel/console.asm",
        root / "v1/src/kernel/cursor.asm",
        root / "v1/src/kernel/keyboard.asm",
        root / "v1/src/kernel/process.asm",
        root / "v1/src/kernel/scheduler.asm",
        root / "v1/src/kernel/syscall.asm",
        root / "v1/tools-host/test-driver/phase1_getkey.py",
        kernel,
    )
    return [command], {str(path.relative_to(root)): sha256_file(path) for path in paths}, assertions
