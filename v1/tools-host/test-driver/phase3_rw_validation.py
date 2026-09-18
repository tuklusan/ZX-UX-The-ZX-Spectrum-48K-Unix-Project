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
import phase3_null
import phase3_open_descriptions
import phase3_pipe_create
import phase3_tty


GUARD = 0xA180


class Phase3RwValidationError(DriverError):
    """Raised when the P3.15 READ/WRITE validation contract regresses."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Phase3RwValidationError(message)


def _word(value: int) -> bytes:
    return bytes((value & 0xFF, (value >> 8) & 0xFF))


def _jp_nc(address: int) -> bytes:
    return b"\xD2" + _word(address)


def _assert_error(code: bytearray, error: int) -> None:
    code += _jp_nc(FAIL_PC) + bytes((0xFE, error & 0xFF)) + phase1._jp_nz(FAIL_PC)


def _assert_hl(code: bytearray, expected: int) -> None:
    code += phase1._ld_de(expected) + b"\xB7\xED\x52" + phase1._jp_nz(FAIL_PC)


def _source_contract(root: Path) -> list[dict[str, object]]:
    syscall = (root / "v1/src/kernel/syscall.asm").read_text(encoding="utf-8")
    prep = syscall[syscall.index("zx48_sys_rw_prepare:"):syscall.index("; E=handle,D=0,HL=buffer,BC=count.")]
    read = syscall[syscall.index("zx48_sys_read:"):syscall.index("zx48_sys_write:")]
    write = syscall[syscall.index("zx48_sys_write:"):syscall.index("zx48_sys_zero_result:")]
    validator = syscall[syscall.index("zx48_user_range_validate:"):syscall.index("    ENDM", syscall.index("zx48_user_range_validate:"))]
    return [
        {"name":"rw-requires-d-zero-before-handle","passed":"ld de,(syscall_arg_de)" in prep and "ld a,d\n    or a\n    jp nz,zx48_sys_invalid" in prep},
        {"name":"rw-validates-handle-and-access-before-count","passed":"call zx48_handle_lookup" in prep and "ld a,(ix+OD_ACCESS_O)\n    and b\n    jp z,zx48_sys_perm" in prep},
        {"name":"zero-count-returns-before-buffer-validation","passed":"ld bc,(syscall_arg_bc)\n    ld a,b\n    or c\n    ret z\n    ld hl,(syscall_arg_hl)\n    call zx48_user_range_validate" in prep},
        {"name":"nonzero-validates-complete-range-before-dispatch","passed":"call zx48_user_range_validate\n    ret c\n    inc a\n    ret" in prep},
        {"name":"read-register-contract-preserved","passed":"ld hl,(syscall_arg_hl)" in read and "ld bc,(syscall_arg_bc)" in read},
        {"name":"write-register-contract-preserved","passed":"ld hl,(syscall_arg_hl)" in write and "ld bc,(syscall_arg_bc)" in write},
        {"name":"logical-null-eof-is-hl-zero-success","passed":"cp OD_KIND_NULL\n    jr z,zx48_sys_zero_result" in read},
        {"name":"range-rejects-wrap-before-region-check","passed":"add hl,bc\n    jr c,zx48_user_range_wrap" in validator},
        {"name":"range-separates-display-and-user-arena","passed":"cp $5B" in validator and "cp $60" in validator and "cp $E0" in validator},
    ]


def _null_matrix(root: Path, s: dict[str, int], kernel: bytes) -> None:
    code = bytearray(b"\xF3" + phase1._ld_sp(0xBFC0))
    phase3_null._setup(code, s)
    code += phase3_null._store_byte(GUARD, 0xA5)

    # Full display region accepted.
    phase3_tty._call_sys(code, s, s["SYS_WRITE"], 0x4000, 0, 0x1B00)
    code += phase1._jp_c(FAIL_PC)
    _assert_hl(code, 0x1B00)

    # Full ordinary arena accepted.
    phase3_tty._call_sys(code, s, s["SYS_WRITE"], 0x6000, 0, 0x8000)
    code += phase1._jp_c(FAIL_PC)
    _assert_hl(code, 0x8000)

    # Exact invalid regions / cross-bound / wrap fail before dispatch.
    for ptr, count in ((0x3FFF,1),(0x5B00,1),(0x5FF0,0x20),(0xE000,1),(0x5AF0,0x20),(0xFFF0,0x20)):
        phase3_tty._call_sys(code, s, s["SYS_WRITE"], ptr, 0, count)
        _assert_error(code, s["E_INVAL"])

    # D must be zero.
    phase3_tty._call_sys(code, s, s["SYS_WRITE"], GUARD, 0x0100, 1)
    _assert_error(code, s["E_INVAL"])

    # Count zero still validates handle but never dereferences poisoned buffer.
    phase3_tty._call_sys(code, s, s["SYS_READ"], 0x0000, 0, 0)
    code += phase1._jp_c(FAIL_PC)
    _assert_hl(code, 0)
    code += phase3_null._load_byte(GUARD) + b"\xFE\xA5" + phase1._jp_nz(FAIL_PC)

    phase3_tty._call_sys(code, s, s["SYS_READ"], 0x0000, 7, 0)
    _assert_error(code, s["E_NOENT"])
    code += phase3_null._load_byte(GUARD) + b"\xFE\xA5" + phase1._jp_nz(FAIL_PC)

    code += phase1._jp(PASS_PC)
    run_sna(root, bytes(code), patch=phase1._kernel_patch(kernel))


def _pipe_eof_fixture(root: Path, s: dict[str, int], kernel: bytes) -> None:
    code = bytearray()
    phase3_pipe_create._setup(code, s)
    code += b"\x21" + _word(GUARD)
    code += phase1._call(s["zx48_pipe_create"]) + phase1._jp_c(FAIL_PC)
    _assert_hl(code, 0)
    code += b"\x3E\x01" + phase1._call(s["zx48_handle_close"]) + phase1._jp_c(FAIL_PC)
    code += phase3_null._store_byte(GUARD + 4, 0xC7)
    phase3_tty._call_sys(code, s, s["SYS_READ"], GUARD + 4, 0, 1)
    code += phase1._jp_c(FAIL_PC)
    _assert_hl(code, 0)
    code += phase3_null._load_byte(GUARD + 4) + b"\xFE\xC7" + phase1._jp_nz(FAIL_PC)
    code += phase1._jp(PASS_PC)
    run_sna(root, bytes(code), patch=phase1._kernel_patch(kernel))


def dispatch(
    root: Path,
    action: str,
    step: str,
    *,
    sha256_file: Callable[[Path], str],
    run_command: Callable[..., Any],
    require_project_tool: Callable[[Path, str | Path], Path],
):
    if step != "P3.15":
        raise DriverError(f"Phase-3 RW validation step is not registered: {step}")

    assertions = _source_contract(root)
    failed = [item["name"] for item in assertions if item["passed"] is not True]
    require(not failed, f"static P3.15 contract failures: {failed}")

    result, kernel, listing = phase1._assemble_kernel(root, run_command, require_project_tool)
    commands = [result]
    symbols = phase3_open_descriptions._symbols(
        listing.with_suffix(".sym"),
        (
            "zx48_memory_init","zx48_process_init","zx48_handles_init","zx48_pipe_init",
            "zx48_process_prepare_pid1","zx48_od_create","zx48_handle_install",
            "zx48_handle_close","zx48_pipe_create","zx48_syscall_impl","current_pid",
            "OD_KIND_NULL","O_READ","O_WRITE","SYS_READ","SYS_WRITE",
            "E_INVAL","E_NOENT","PIPE_BUFFER_SIZE",
        ),
    )

    if action == "test":
        kernel_bytes = kernel.read_bytes()
        _null_matrix(root, symbols, kernel_bytes)
        _pipe_eof_fixture(root, symbols, kernel_bytes)
        assertions.extend([
            {"name":"display-full-range-valid","passed":True},
            {"name":"ordinary-arena-full-range-valid","passed":True},
            {"name":"rom-compat-kernel-cross-bound-wrap-invalid","passed":True},
            {"name":"zero-count-poisoned-buffer-not-dereferenced","passed":True},
            {"name":"zero-count-invalid-handle-still-errors","passed":True},
            {"name":"ordinary-stream-eof-is-zero-byte-success","passed":True},
        ])

    hashes = {
        "v1/build/kernel.bin": sha256_file(kernel),
        "v1/src/kernel/syscall.asm": sha256_file(root / "v1/src/kernel/syscall.asm"),
        "v1/tools-host/test-driver/phase3_rw_validation.py": sha256_file(root / "v1/tools-host/test-driver/phase3_rw_validation.py"),
        "v1/tools-host/test-driver/run.py": sha256_file(root / "v1/tools-host/test-driver/run.py"),
        "v1/dist/certification/P3.14.test.json": sha256_file(root / "v1/dist/certification/P3.14.test.json"),
    }
    return commands, hashes, assertions
