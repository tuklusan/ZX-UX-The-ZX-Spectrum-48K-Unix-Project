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

from dataclasses import dataclass
from pathlib import Path
import re

ORDINARY_POOL_BYTES = 6912
PLANNED_BYTES = 6784
UNASSIGNED_MARGIN_BYTES = 128

BUDGET = (
    ("syscall_gateway_entry", 128),
    ("scheduler_process_open_description", 896),
    ("allocator", 448),
    ("pipe_subsystem", 640),
    ("rom_wrappers", 704),
    ("console_keyboard_ula_tty64", 832),
    ("graphics_primitives", 608),
    ("udg_subsystem", 192),
    ("cassette_object_layer", 672),
    ("ram_object_namespace", 640),
    ("resident_zxpack_codec_manager", 384),
    ("interrupt_time_error_core", 448),
    ("tables_strings", 192),
)

FIXED_RANGES = (
    ("ordinary", 0xE000, 0xFAFF),
    ("stack", 0xFB00, 0xFCFF),
    ("fast_reserve", 0xFD00, 0xFDFC),
    ("im2_trampoline", 0xFDFD, 0xFDFF),
    ("im2_table", 0xFE00, 0xFF00),
    ("emergency", 0xFF01, 0xFFFF),
)


class LayoutError(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise LayoutError(message)


def validate_budget(budget: tuple[tuple[str, int], ...] = BUDGET) -> None:
    require(len(budget) == 13, "ordinary kernel budget must have exactly thirteen categories")
    names = [name for name, _ in budget]
    require(len(set(names)) == len(names), "ordinary kernel budget category duplicated")
    require(all(size > 0 for _, size in budget), "ordinary kernel budget sizes must be positive")
    total = sum(size for _, size in budget)
    require(total == PLANNED_BYTES, f"planned ordinary bytes must be {PLANNED_BYTES}, got {total}")
    require(
        ORDINARY_POOL_BYTES - total == UNASSIGNED_MARGIN_BYTES,
        "ordinary-pool unassigned margin must be exactly 128 bytes",
    )


def validate_ranges(ranges: tuple[tuple[str, int, int], ...] = FIXED_RANGES) -> None:
    require(len(ranges) == 6, "fixed kernel layout must contain six ranges")
    previous = 0xDFFF
    for name, start, end in ranges:
        require(start == previous + 1, f"{name}: gap or overlap before {start:#06x}")
        require(start <= end, f"{name}: inverted range")
        previous = end
    require(previous == 0xFFFF, "kernel image must end at FFFF")
    require(ranges[0][2] - ranges[0][1] + 1 == ORDINARY_POOL_BYTES, "ordinary pool size mismatch")
    require(ranges[-1][2] - ranges[0][1] + 1 == 8192, "kernel image size mismatch")


def validate_source(source: str) -> None:
    required = {
        "KERNEL_STACK_START",
        "FAST_RESERVE_START",
        "IM2_TRAMPOLINE_START",
        "IM2_TABLE_START",
        "EMERGENCY_START",
        "KERNEL_IMAGE_SIZE",
        "SAVEBIN",
    }
    missing = [token for token in sorted(required) if token not in source]
    require(not missing, f"kernel scaffold missing layout tokens: {missing}")
    require(
        re.search(r"DEFS\s+KERNEL_CODE_END\+1-\$,0", source) is not None,
        "ordinary pool remainder must be explicitly materialized",
    )


def validate_all(kernel_path: Path) -> None:
    validate_budget()
    validate_ranges()
    validate_source(kernel_path.read_text(encoding="utf-8"))


def negative_fixtures() -> list[tuple[str, bool]]:
    cases: list[tuple[str, bool]] = []

    changed = list(BUDGET)
    changed[0] = (changed[0][0], changed[0][1] + 1)
    try:
        validate_budget(tuple(changed))
        cases.append(("budget-byte-drift", False))
    except LayoutError:
        cases.append(("budget-byte-drift", True))

    missing = BUDGET[:-1]
    try:
        validate_budget(missing)
        cases.append(("budget-category-missing", False))
    except LayoutError:
        cases.append(("budget-category-missing", True))

    duplicate = BUDGET[:-1] + (BUDGET[0],)
    try:
        validate_budget(duplicate)
        cases.append(("budget-category-duplicate", False))
    except LayoutError:
        cases.append(("budget-category-duplicate", True))

    overlap = list(FIXED_RANGES)
    name, start, end = overlap[0]
    overlap[0] = (name, start, end + 1)
    try:
        validate_ranges(tuple(overlap))
        cases.append(("one-byte-overlap-fb00", False))
    except LayoutError:
        cases.append(("one-byte-overlap-fb00", True))

    return cases


def assemble_kernel(
    root: Path,
    run_command,
    require_project_tool,
):
    sjasm = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build_dir = root / "v1/build"
    build_dir.mkdir(parents=True, exist_ok=True)
    result = run_command(
        [sjasm, "--nologo", "kernel.asm"],
        cwd=root / "v1/src/kernel",
        timeout_seconds=30.0,
    )
    require(not result.timed_out, "P0.02 assembler timed out")
    require(result.exit_code == 0, f"P0.02 assembler failed: {result.stderr}")
    image = build_dir / "kernel.bin"
    require(image.is_file(), "P0.02 assembler did not emit kernel.bin")
    require(image.stat().st_size == 8192, "P0.02 kernel image must be exactly 8192 bytes")
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
    if step != "P0.02":
        raise LayoutError(f"layout step is not registered: {step}")

    kernel = root / "v1/src/kernel/kernel.asm"
    oracle = root / "v1/tools-host/test-driver/phase0_layout.py"
    require(kernel.is_file(), "P0.02 kernel scaffold missing")
    validate_all(kernel)

    command, image = assemble_kernel(root, run_command, require_project_tool)
    data = image.read_bytes()
    require(len(data) == 8192, "P0.02 kernel image size drift")
    require(data[0x1B00:0x1D00] == bytes(0x200), "P0.02 kernel stack storage drift")
    require(data[0x1D00:0x1DFD] == bytes(0xFD), "P0.02 fast reserve drift")
    trampoline = data[0x1DFD:0x1E00]
    require(len(trampoline) == 3, "P0.02 trampoline slot must be exactly three bytes")
    require(trampoline[0] == 0xC3, "P0.02 trampoline must begin with absolute JP opcode")
    trampoline_target = trampoline[1] | (trampoline[2] << 8)
    require(0xE000 <= trampoline_target <= 0xFAFF, "P0.02 trampoline target outside ordinary pool")
    require(data[0x1E00:0x1F01] == bytes([0xFD]) * 0x101, "P0.02 IM2 table initialization drift")
    require(data[0x1F01:0x2000] == bytes(0xFF), "P0.02 emergency reserve drift")

    assertions = [
        {"name": "kernel-exact-8192", "passed": len(data) == 8192},
        {"name": "ordinary-pool-6912", "passed": True},
        {"name": "budget-thirteen-categories", "passed": len(BUDGET) == 13},
        {"name": "budget-planned-6784", "passed": sum(size for _, size in BUDGET) == 6784},
        {"name": "budget-margin-128", "passed": ORDINARY_POOL_BYTES - PLANNED_BYTES == 128},
        {"name": "fixed-ranges-contiguous", "passed": True},
        {"name": "im2-trampoline-absolute-jp", "passed": True, "detail": f"{trampoline_target:#06x}"},
    ]

    if action == "test":
        negative = negative_fixtures()
        failed = [name for name, rejected in negative if not rejected]
        require(not failed, f"P0.02 negative fixtures unexpectedly passed: {failed}")
        assertions.extend({"name": name, "passed": True} for name, _ in negative)

    return (
        [command],
        {
            "v1/src/kernel/kernel.asm": sha256_file(kernel),
            "v1/build/kernel.bin": sha256_file(image),
            "v1/tools-host/test-driver/phase0_layout.py": sha256_file(oracle),
        },
        assertions,
    )
