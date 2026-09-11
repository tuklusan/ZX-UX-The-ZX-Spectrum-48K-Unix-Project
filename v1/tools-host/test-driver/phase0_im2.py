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
TRAMPOLINE = 0xFDFD
TABLE_START = 0xFE00
TABLE_END = 0xFF00
VECTOR_BYTE = 0xFD
JP_OPCODE = 0xC3


class Im2Error(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Im2Error(message)


def decode_jp(data: bytes, address: int) -> int:
    offset = address - KERNEL_START
    require(0 <= offset <= len(data) - 3, "JP address outside kernel image")
    require(data[offset] == JP_OPCODE, f"expected JP opcode at {address:#06x}")
    return data[offset + 1] | (data[offset + 2] << 8)


def validate_image(data: bytes) -> int:
    require(len(data) == 8192, "kernel image must be exactly 8192 bytes")
    target = decode_jp(data, TRAMPOLINE)
    require(KERNEL_START <= target <= 0xFAFF, "IM2 trampoline target outside ordinary pool")

    table_offset = TABLE_START - KERNEL_START
    table = data[table_offset:table_offset + 257]
    require(len(table) == 257, "IM2 table size drift")
    require(table == bytes([VECTOR_BYTE]) * 257, "IM2 table byte drift")

    for low in range(256):
        lo = table[low]
        hi = table[low + 1]
        vector = lo | (hi << 8)
        require(vector == TRAMPOLINE, f"IM2 low vector {low:#04x} resolves to {vector:#06x}")
    return target


def validate_source(root: Path) -> None:
    source = (root / "v1/src/kernel/im2.asm").read_text(encoding="utf-8")
    order = [
        "di",
        "ld hl,IM2_TABLE_START",
        "ld de,IM2_TABLE_START+1",
        "ld (hl),IM2_VECTOR_BYTE",
        "ld bc,IM2_TABLE_END-IM2_TABLE_START",
        "ldir",
        "ld a,IM2_I_VALUE",
        "ld i,a",
        "im 2",
    ]
    code = "\n".join(line.split(";", 1)[0] for line in source.splitlines()).lower()
    cursor = 0
    for token in order:
        position = code.find(token.lower(), cursor)
        require(position >= 0, f"IM2 initialization token missing/out of order: {token}")
        cursor = position + len(token)
    require(code.find("ld i,a") > code.find("ldir"), "I must be assigned only after table fill")


def negative_fixtures(data: bytes) -> list[tuple[str, bool]]:
    cases: list[tuple[str, bool]] = []
    bad_table = bytearray(data)
    bad_table[(TABLE_START - KERNEL_START) + 73] ^= 1
    try:
        validate_image(bytes(bad_table))
        cases.append(("corrupt-table-byte", False))
    except Im2Error:
        cases.append(("corrupt-table-byte", True))

    bad_trampoline = bytearray(data)
    bad_trampoline[TRAMPOLINE - KERNEL_START] = 0
    try:
        validate_image(bytes(bad_trampoline))
        cases.append(("corrupt-trampoline", False))
    except Im2Error:
        cases.append(("corrupt-trampoline", True))
    return cases


def assemble_kernel(root: Path, run_command, require_project_tool):
    sjasm = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    (root / "v1/build").mkdir(parents=True, exist_ok=True)
    result = run_command(
        [sjasm, "--nologo", "kernel.asm"],
        cwd=root / "v1/src/kernel",
        timeout_seconds=30.0,
    )
    require(not result.timed_out, "P0.04 assembler timed out")
    require(result.exit_code == 0, f"P0.04 assembler failed: {result.stderr}")
    image = root / "v1/build/kernel.bin"
    require(image.is_file(), "P0.04 kernel image missing")
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
    if step != "P0.04":
        raise Im2Error(f"IM2 step is not registered: {step}")

    validate_source(root)
    command, image = assemble_kernel(root, run_command, require_project_tool)
    target = validate_image(image.read_bytes())
    assertions = [
        {"name": "fdfd-absolute-jp", "passed": True, "detail": f"{target:#06x}"},
        {"name": "im2-table-257-fd", "passed": True},
        {"name": "all-256-low-vectors-fdfd", "passed": True},
        {"name": "i-set-after-table-fill", "passed": True},
    ]
    if action == "test":
        negative = negative_fixtures(image.read_bytes())
        failed = [name for name, rejected in negative if not rejected]
        require(not failed, f"P0.04 negative fixtures unexpectedly passed: {failed}")
        assertions.extend({"name": name, "passed": True} for name, _ in negative)

    paths = [
        root / "v1/src/kernel/kernel.asm",
        root / "v1/src/kernel/im2.asm",
        root / "v1/src/kernel/interrupt.asm",
        root / "v1/tools-host/test-driver/phase0_im2.py",
        image,
    ]
    return [command], {str(p.relative_to(root)): sha256_file(p) for p in paths}, assertions
