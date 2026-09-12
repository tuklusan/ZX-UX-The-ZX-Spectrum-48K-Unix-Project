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


class Phase1SyscallError(DriverError):
    """Raised when an early Phase-1 syscall contract is violated."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Phase1SyscallError(message)


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


def _ld_hl(value: int) -> bytes:
    return b"\x21" + _word(value)


def _ld_de(value: int) -> bytes:
    return b"\x11" + _word(value)


def _ld_bc(value: int) -> bytes:
    return b"\x01" + _word(value)


def _compare_hl(value: int) -> bytes:
    return _ld_de(value) + b"\xB7\xED\x52" + _jp_nz(FAIL_PC)


def _kernel_patch(kernel_bytes: bytes):
    def patch(ram: bytearray) -> None:
        start = phase1.KERNEL_BASE - 0x4000
        ram[start:start + len(kernel_bytes)] = kernel_bytes
    return patch


def _p110_source_contract(root: Path) -> list[dict[str, object]]:
    text = (root / "v1/src/kernel/syscall.asm").read_text(encoding="utf-8")
    body = text.split("zx48_sys_version:", 1)[1].split("zx48_sys_exit:", 1)[0]
    expected = "\n    ld hl,ZXUX_ABI_VERSION\n    xor a\n    ret\n"
    return [
        {"name": "version-is-no-argument-fixed-return", "passed": body == expected},
        {"name": "version-has-no-selector-branch", "passed": not any(token in body.lower() for token in ("cp ", "and ", "or l", "or h", "jr ", "jp "))},
    ]


def _p110_negative(root: Path) -> list[dict[str, object]]:
    text = (root / "v1/src/kernel/syscall.asm").read_text(encoding="utf-8")
    mutated = text.replace(
        "zx48_sys_version:\n    ld hl,ZXUX_ABI_VERSION\n    xor a\n    ret",
        "zx48_sys_version:\n    ld a,h\n    or l\n    jr nz,zx48_sys_notsup\n    ld hl,ZXUX_ABI_VERSION\n    xor a\n    ret",
        1,
    )
    body = mutated.split("zx48_sys_version:", 1)[1].split("zx48_sys_exit:", 1)[0]
    return [
        {
            "name": "reject-invented-version-selector",
            "passed": body != "\n    ld hl,ZXUX_ABI_VERSION\n    xor a\n    ret\n",
        }
    ]


def _p110_runtime(root: Path, labels: dict[str, int], kernel_bytes: bytes) -> None:
    stack_init = labels["zx48_kernel_stack_init"]
    vectors = (
        (0x0000, 0x0000, 0x0000),
        (0x1234, 0x5678, 0x9ABC),
        (0xFFFF, 0x4000, 0xDFFF),
    )
    code = bytearray(b"\xF3\x31" + _word(phase1.USER_STACK) + _call(stack_init))
    for hl, de, bc in vectors:
        code += _ld_hl(hl) + _ld_de(de) + _ld_bc(bc)
        code += b"\xDD\x21\x34\x12\xFD\x21\x00\x20\xAF" + _call(phase1.KERNEL_BASE)
        code += _jp_c(FAIL_PC)
        code += b"\xB7" + _jp_nz(FAIL_PC)
        code += _compare_hl(0x0100)
        code += b"\xDD\xE5\xE1" + _compare_hl(0x1234)
        code += b"\xFD\xE5\xE1" + _compare_hl(0x5C3A)
    code += _jp(PASS_PC)
    run_sna(root, bytes(code), patch=_kernel_patch(kernel_bytes))


def dispatch(
    root: Path,
    action: str,
    step: str,
    *,
    sha256_file: Callable[[Path], str],
    run_command: Callable[..., Any],
    require_project_tool: Callable[[Path, str | Path], Path],
):
    if step != "P1.10":
        raise Phase1SyscallError(f"early syscall step is not registered: {step}")

    assertions = _p110_source_contract(root)
    failed = [str(item["name"]) for item in assertions if item["passed"] is not True]
    require(not failed, f"P1.10 static failures: {failed}")

    command, kernel, listing = phase1._assemble_kernel(root, run_command, require_project_tool)
    labels = phase1._labels(listing, ("zx48_kernel_stack_init",))
    kernel_bytes = kernel.read_bytes()

    if action == "test":
        _p110_runtime(root, labels, kernel_bytes)
        assertions.extend(
            [
                {"name": "version-arbitrary-caller-register-vectors", "passed": True, "vectors": 3},
                {"name": "version-exact-hl-0100-carry-clear-a-zero", "passed": True},
                {"name": "version-preserves-ix-and-canonicalizes-iy", "passed": True},
                *_p110_negative(root),
            ]
        )

    paths = (
        root / "v1/src/kernel/syscall.asm",
        root / "v1/include/zx48ux.inc",
        root / "v1/docs/abi.md",
        root / "v1/tools-host/test-driver/phase1_syscalls.py",
        kernel,
    )
    hashes = {str(path.relative_to(root)).replace("\\", "/"): sha256_file(path) for path in paths}
    return [command], hashes, assertions
