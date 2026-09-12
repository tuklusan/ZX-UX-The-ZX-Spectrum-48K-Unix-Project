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

KERNEL_START = 0xE000
ORDINARY_END = 0xFAFF
SYSCALL_GATEWAY = 0xE000
BOOT_GATEWAY = 0xE003
FIRST_INTERNAL = 0xE006
JP_OPCODE = 0xC3


class BootError(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise BootError(message)


def decode_jp(data: bytes, offset: int) -> int:
    require(offset + 3 <= len(data), "truncated JP")
    require(data[offset] == JP_OPCODE, f"expected JP opcode at kernel offset {offset:#x}")
    return data[offset + 1] | (data[offset + 2] << 8)


def validate_trampolines(data: bytes) -> tuple[int, int]:
    require(len(data) == 8192, "kernel image must be exactly 8192 bytes")
    syscall_target = decode_jp(data, SYSCALL_GATEWAY - KERNEL_START)
    boot_target = decode_jp(data, BOOT_GATEWAY - KERNEL_START)
    require(
        FIRST_INTERNAL <= syscall_target <= ORDINARY_END,
        "E000 syscall gateway target outside ordinary pool",
    )
    require(
        FIRST_INTERNAL <= boot_target <= ORDINARY_END,
        "E003 boot gateway target outside ordinary pool",
    )
    require(syscall_target != boot_target, "syscall and boot gateway targets must be distinct")
    return syscall_target, boot_target


def negative_fixtures(data: bytes) -> list[tuple[str, bool]]:
    cases: list[tuple[str, bool]] = []

    moved_syscall = bytearray(data)
    moved_syscall[0] = 0
    try:
        validate_trampolines(bytes(moved_syscall))
        cases.append(("syscall-trampoline-moved", False))
    except BootError:
        cases.append(("syscall-trampoline-moved", True))

    moved_boot = bytearray(data)
    moved_boot[3] = 0
    try:
        validate_trampolines(bytes(moved_boot))
        cases.append(("boot-trampoline-moved", False))
    except BootError:
        cases.append(("boot-trampoline-moved", True))

    wrong_target = bytearray(data)
    wrong_target[1] = 0
    wrong_target[2] = 0
    try:
        validate_trampolines(bytes(wrong_target))
        cases.append(("syscall-target-drift", False))
    except BootError:
        cases.append(("syscall-target-drift", True))

    alias_target = bytearray(data)
    alias_target[4] = alias_target[1]
    alias_target[5] = alias_target[2]
    try:
        validate_trampolines(bytes(alias_target))
        cases.append(("gateway-target-alias", False))
    except BootError:
        cases.append(("gateway-target-alias", True))

    return cases


def assemble_kernel(root: Path, run_command, require_project_tool):
    sjasm = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    (root / "v1/build").mkdir(parents=True, exist_ok=True)
    result = run_command(
        [sjasm, "--nologo", "kernel.asm"],
        cwd=root / "v1/src/kernel",
        timeout_seconds=30.0,
    )
    require(not result.timed_out, "P0.03 assembler timed out")
    require(result.exit_code == 0, f"P0.03 assembler failed: {result.stderr}")
    image = root / "v1/build/kernel.bin"
    require(image.is_file(), "P0.03 kernel image missing")
    return result, image


def dispatch(
    root: Path,
    action: str,
    step: str,
    *,
    sha256_file,
    run_command,
    require_project_tool,
):
    if step != "P0.03":
        raise BootError(f"boot step is not registered: {step}")

    command, image = assemble_kernel(root, run_command, require_project_tool)
    data = image.read_bytes()
    syscall_target, boot_target = validate_trampolines(data)

    assertions = [
        {"name": "e000-absolute-jp", "passed": data[0] == JP_OPCODE},
        {"name": "e003-absolute-jp", "passed": data[3] == JP_OPCODE},
        {"name": "syscall-target-in-ordinary-pool", "passed": True, "detail": f"{syscall_target:#06x}"},
        {"name": "boot-target-in-ordinary-pool", "passed": True, "detail": f"{boot_target:#06x}"},
        {"name": "gateway-targets-distinct", "passed": syscall_target != boot_target},
    ]
    if action == "test":
        negative = negative_fixtures(data)
        failed = [name for name, rejected in negative if not rejected]
        require(not failed, f"P0.03 negative fixtures unexpectedly passed: {failed}")
        assertions.extend({"name": name, "passed": True} for name, _ in negative)

    paths = [
        root / "v1/src/kernel/kernel.asm",
        root / "v1/src/kernel/syscall.asm",
        root / "v1/src/boot/entry.asm",
        root / "v1/tools-host/test-driver/phase0_boot.py",
        image,
    ]
    return (
        [command],
        {str(path.relative_to(root)): sha256_file(path) for path in paths},
        assertions,
    )
