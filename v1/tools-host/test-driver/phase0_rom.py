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

ANCHOR = 0x5C3A
LD_IY_IMM = bytes((0xFD, 0x21))
RET = 0xC9


class RomError(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RomError(message)


def anchor_sequence() -> bytes:
    return LD_IY_IMM + bytes((ANCHOR & 0xFF, ANCHOR >> 8, RET))


def validate_sources(root: Path) -> None:
    include = (root / "v1/include/zx48ux.inc").read_text(encoding="utf-8")
    syscall = (root / "v1/src/kernel/syscall.asm").read_text(encoding="utf-8")
    rom = (root / "v1/src/kernel/rom_services.asm").read_text(encoding="utf-8")
    require("ROM_IY_ANCHOR" in include and "$5C3A" in include.upper(), "ROM IY anchor constant drift")
    require("ld iy,ROM_IY_ANCHOR" in syscall, "public syscall return does not restore IY")
    require("ld iy,ROM_IY_ANCHOR" in rom, "ROM service return does not restore IY")


def validate_image(data: bytes) -> int:
    require(len(data) == 8192, "kernel image must be exactly 8192 bytes")
    sequence = anchor_sequence()
    count = data[:0x1B00].count(sequence)
    require(count >= 2, "kernel must contain syscall and ROM-wrapper IY restoration sequences")
    return count


def negative_fixtures(data: bytes) -> list[tuple[str, bool]]:
    cases: list[tuple[str, bool]] = []
    sequence = anchor_sequence()
    offsets: list[int] = []
    cursor = 0
    while True:
        offset = data.find(sequence, cursor, 0x1B00)
        if offset < 0:
            break
        offsets.append(offset)
        cursor = offset + len(sequence)
    require(len(offsets) >= 2, "positive IY sequences missing before negative fixture")
    broken = bytearray(data)
    for offset in offsets:
        broken[offset + 2] ^= 1
    try:
        validate_image(bytes(broken))
        cases.append(("clobbered-iy-anchor", False))
    except RomError:
        cases.append(("clobbered-iy-anchor", True))
    return cases


def assemble_kernel(root: Path, run_command, require_project_tool):
    sjasm = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    (root / "v1/build").mkdir(parents=True, exist_ok=True)
    result = run_command(
        [sjasm, "--nologo", "kernel.asm"],
        cwd=root / "v1/src/kernel",
        timeout_seconds=30.0,
    )
    require(not result.timed_out, "P0.05 assembler timed out")
    require(result.exit_code == 0, f"P0.05 assembler failed: {result.stderr}")
    image = root / "v1/build/kernel.bin"
    require(image.is_file(), "P0.05 kernel image missing")
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
    if step != "P0.05":
        raise RomError(f"ROM step is not registered: {step}")

    validate_sources(root)
    command, image = assemble_kernel(root, run_command, require_project_tool)
    count = validate_image(image.read_bytes())
    assertions = [
        {"name": "iy-anchor-5c3a", "passed": True},
        {"name": "syscall-return-restores-iy", "passed": True},
        {"name": "rom-wrapper-restores-iy", "passed": True},
        {"name": "binary-restoration-sequences", "passed": count >= 2, "detail": str(count)},
    ]
    if action == "test":
        negative = negative_fixtures(image.read_bytes())
        failed = [name for name, rejected in negative if not rejected]
        require(not failed, f"P0.05 negative fixtures unexpectedly passed: {failed}")
        assertions.extend({"name": name, "passed": True} for name, _ in negative)

    paths = [
        root / "v1/include/zx48ux.inc",
        root / "v1/src/kernel/syscall.asm",
        root / "v1/src/kernel/rom_services.asm",
        root / "v1/tools-host/test-driver/phase0_rom.py",
        image,
    ]
    return [command], {str(p.relative_to(root)): sha256_file(p) for p in paths}, assertions
