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
import phase3_open_descriptions
import phase3_tty

BUF = 0xA100
IOCTL_REC = 0xA120
IOCTL_ARG = 0xA130


class Phase3NullError(DriverError):
    """Raised when the P3.04 /dev/null description contract regresses."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Phase3NullError(message)


def _word(value: int) -> bytes:
    return bytes((value & 0xFF, (value >> 8) & 0xFF))


def _jp_nc(address: int) -> bytes:
    return b"\xD2" + _word(address)


def _store_byte(address: int, value: int) -> bytes:
    return bytes((0x3E, value & 0xFF, 0x32)) + _word(address)


def _load_byte(address: int) -> bytes:
    return b"\x3A" + _word(address)


def _source_contract(root: Path) -> list[dict[str, object]]:
    handles = (root / "v1/src/kernel/handles.asm").read_text(encoding="utf-8")
    syscall = (root / "v1/src/kernel/syscall.asm").read_text(encoding="utf-8")
    return [
        {"name": "null-is-generic-open-description-kind", "passed": "OD_KIND_NULL" in syscall and "zx48_od_create:" in handles},
        {"name": "null-read-is-immediate-zero-byte-success", "passed": "cp OD_KIND_NULL\n    jr z,zx48_sys_zero_result" in syscall},
        {"name": "null-write-returns-full-request-count", "passed": "zx48_sys_write_null:\n    ld hl,(syscall_arg_bc)\n    xor a\n    ret" in syscall},
        {"name": "null-seek-is-not-supported", "passed": "zx48_sys_seek:" in syscall and "jp zx48_sys_notsup" in syscall},
        {"name": "null-ioctl-is-kind-rejected", "passed": "cp OD_KIND_TTY\n    jp nz,zx48_sys_notsup" in syscall},
    ]


def _setup(code: bytearray, s: dict[str, int]) -> None:
    code += phase1._call(s["zx48_process_init"])
    code += phase1._call(s["zx48_handles_init"])
    code += phase1._call(s["zx48_process_prepare_pid1"])
    code += _store_byte(s["current_pid"], 1)
    code += bytes((0x06, s["OD_KIND_NULL"], 0x0E, s["O_READ"] | s["O_WRITE"], 0x16, 0))
    code += phase1._call(s["zx48_od_create"]) + phase1._jp_c(FAIL_PC) + b"\xB7" + phase1._jp_nz(FAIL_PC)
    code += b"\x4F\xAF" + phase1._call(s["zx48_handle_install"])
    code += phase1._jp_c(FAIL_PC) + b"\xB7" + phase1._jp_nz(FAIL_PC)


def _target_test(root: Path, s: dict[str, int], kernel: bytes) -> None:
    code = bytearray(b"\xF3" + phase1._ld_sp(0xBFC0))
    _setup(code, s)

    code += _store_byte(BUF, 0xA5)
    phase3_tty._call_sys(code, s, s["SYS_READ"], BUF, 0, 5)
    code += phase1._jp_c(FAIL_PC) + b"\x7C\xB5" + phase1._jp_nz(FAIL_PC)
    code += _load_byte(BUF) + b"\xFE\xA5" + phase1._jp_nz(FAIL_PC)

    phase3_tty._call_sys(code, s, s["SYS_WRITE"], BUF, 0, 5)
    code += phase1._jp_c(FAIL_PC) + phase1._ld_de(5) + b"\xB7\xED\x52" + phase1._jp_nz(FAIL_PC)

    phase3_tty._call_sys(code, s, s["SYS_SEEK"], 0x1234, 0, 0)
    code += _jp_nc(FAIL_PC) + b"\xFE" + bytes((s["E_NOTSUP"],)) + phase1._jp_nz(FAIL_PC)

    def patch(ram: bytearray) -> None:
        ram[IOCTL_REC - 0x4000:IOCTL_REC - 0x4000 + 4] = bytes((0, s["TTY_REQ_GET_MODE"], IOCTL_ARG & 0xFF, IOCTL_ARG >> 8))
        start = phase1.KERNEL_BASE - 0x4000
        ram[start:start + len(kernel)] = kernel

    phase3_tty._call_sys(code, s, s["SYS_IOCTL"], IOCTL_REC, 0, 0)
    code += _jp_nc(FAIL_PC) + b"\xFE" + bytes((s["E_NOTSUP"],)) + phase1._jp_nz(FAIL_PC)

    code += phase1._jp(PASS_PC)
    run_sna(root, bytes(code), patch=patch)


def dispatch(
    root: Path,
    action: str,
    step: str,
    *,
    sha256_file: Callable[[Path], str],
    run_command: Callable[..., Any],
    require_project_tool: Callable[[Path, str | Path], Path],
):
    if step != "P3.04":
        raise DriverError(f"Phase-3 null step is not registered: {step}")

    assertions = _source_contract(root)
    failed = [item["name"] for item in assertions if item["passed"] is not True]
    require(not failed, f"static P3.04 contract failures: {failed}")

    result, kernel, listing = phase1._assemble_kernel(root, run_command, require_project_tool)
    commands = [result]
    symbols = phase3_open_descriptions._symbols(
        listing.with_suffix(".sym"),
        (
            "zx48_process_init", "zx48_handles_init", "zx48_process_prepare_pid1",
            "zx48_od_create", "zx48_handle_install", "zx48_syscall_impl",
            "current_pid", "OD_KIND_NULL", "O_READ", "O_WRITE", "E_NOTSUP",
            "SYS_READ", "SYS_WRITE", "SYS_SEEK", "SYS_IOCTL", "TTY_REQ_GET_MODE",
        ),
    )
    assertions.append({"name": "null-kind-is-nonzero-live-description-kind", "passed": symbols["OD_KIND_NULL"] != 0})

    if action == "test":
        _target_test(root, symbols, kernel.read_bytes())
        assertions.extend([
            {"name": "null-read-hl-zero-and-buffer-unchanged", "passed": True},
            {"name": "null-write-returns-full-count", "passed": True},
            {"name": "null-seek-enotsup", "passed": True},
            {"name": "null-invalid-ioctl-enotsup", "passed": True},
        ])

    hashes = {
        "v1/build/kernel.bin": sha256_file(kernel),
        "v1/src/kernel/handles.asm": sha256_file(root / "v1/src/kernel/handles.asm"),
        "v1/src/kernel/syscall.asm": sha256_file(root / "v1/src/kernel/syscall.asm"),
        "v1/tools-host/test-driver/phase3_null.py": sha256_file(root / "v1/tools-host/test-driver/phase3_null.py"),
        "v1/tools-host/test-driver/run.py": sha256_file(root / "v1/tools-host/test-driver/run.py"),
        "v1/dist/certification/P3.03.test.json": sha256_file(root / "v1/dist/certification/P3.03.test.json"),
    }
    return commands, hashes, assertions
