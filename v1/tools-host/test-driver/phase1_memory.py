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

ALLOC_ANY = 0
ALLOC_FAST_REQUIRED = 1
ALLOC_COLD_PREFERRED = 2
E_INVAL = 1
E_NOMEM = 3
SCRATCH_BASE = 0xA000
SAVED_BASE = 0xB000


class Phase1MemoryError(DriverError):
    """Raised when the Phase-1 arena/accounting contract is violated."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Phase1MemoryError(message)


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


def _ld_sp(value: int) -> bytes:
    return b"\x31" + _word(value)


def _ld_bc(value: int) -> bytes:
    return b"\x01" + _word(value)


def _ld_de(value: int) -> bytes:
    return b"\x11" + _word(value)


def _ld_hl(value: int) -> bytes:
    return b"\x21" + _word(value)


def _expect_a(value: int) -> bytes:
    return bytes((0xFE, value & 0xFF)) + _jp_nz(FAIL_PC)


def _expect_hl(value: int) -> bytes:
    return _ld_de(value) + b"\xB7\xED\x52" + _jp_nz(FAIL_PC)


def _store_hl(address: int) -> bytes:
    return b"\x22" + _word(address)


def _load_hl(address: int) -> bytes:
    return b"\x2A" + _word(address)


def _expect_byte(address: int, value: int) -> bytes:
    return b"\x3A" + _word(address) + bytes((0xFE, value & 0xFF)) + _jp_nz(FAIL_PC)


def _expect_bytes(address: int, expected: bytes) -> bytes:
    return b"".join(_expect_byte(address + offset, value) for offset, value in enumerate(expected))


def _prefix(memory_init: int) -> bytearray:
    return bytearray(b"\xF3" + _ld_sp(phase1.USER_STACK) + _call(memory_init))


def _source_contract(root: Path) -> list[dict[str, object]]:
    memory = (root / "v1/src/kernel/memory.asm").read_text(encoding="utf-8")
    include = (root / "v1/include/zx48ux.inc").read_text(encoding="utf-8")
    lowered = memory.lower()
    return [
        {"name": "sixteen-free-extents", "passed": "FREE_EXTENT_COUNT        EQU $10" in include},
        {"name": "arena-is-6000-dfff", "passed": "ARENA_START              EQU COLD_START" in include and "ARENA_END                EQU FAST_END" in include},
        {"name": "allocator-rounds-even", "passed": "bit 0,c" in lowered and "inc bc" in lowered},
        {"name": "fast-required-policy", "passed": "cp alloc_fast_required" in lowered and "zx48_alloc_take_high:" in lowered},
        {"name": "cold-preferred-policy", "passed": "cp alloc_cold_preferred" in lowered and "zx48_alloc_retry:" in lowered},
        {"name": "exact-free-record-check", "passed": "call zx48_free_find_record" in lowered and "memory_alloc_record_ptr" in lowered},
        {"name": "bounded-live-records", "passed": "ALLOC_RECORD_COUNT       EQU 41" in memory},
        {"name": "mem-info-fields", "passed": all(token in lowered for token in ("memory_fast_total", "memory_fast_largest", "memory_cold_total", "memory_cold_largest", "memory_live_allocations", "memory_pinned_bytes"))},
    ]


def _p102_test(root: Path, labels: dict[str, int], kernel_bytes: bytes) -> None:
    init, alloc, free = (labels[name] for name in ("zx48_memory_init", "zx48_alloc", "zx48_free"))
    code = _prefix(init)
    code += _ld_bc(0x0101) + bytes((0x3E, ALLOC_ANY)) + _call(alloc) + _jp_c(FAIL_PC)
    code += _store_hl(SAVED_BASE) + _expect_hl(0x6000)
    code += _load_hl(SAVED_BASE) + _ld_bc(0x0100) + _call(free) + _jp_nc(FAIL_PC) + _expect_a(E_INVAL)
    code += _load_hl(SAVED_BASE) + _ld_bc(0x0102) + _call(free) + _jp_c(FAIL_PC)
    code += _load_hl(SAVED_BASE) + _ld_bc(0x0102) + _call(free) + _jp_nc(FAIL_PC) + _expect_a(E_INVAL)
    code += _call(init)
    for _ in range(41):
        code += _ld_bc(2) + bytes((0x3E, ALLOC_ANY)) + _call(alloc) + _jp_c(FAIL_PC)
    code += _ld_bc(2) + bytes((0x3E, ALLOC_ANY)) + _call(alloc) + _jp_nc(FAIL_PC) + _expect_a(E_NOMEM)
    code += _jp(PASS_PC)
    run_sna(root, bytes(code), patch=phase1._kernel_patch(kernel_bytes))


def _p103_test(root: Path, labels: dict[str, int], kernel_bytes: bytes) -> None:
    init, alloc = (labels[name] for name in ("zx48_memory_init", "zx48_alloc"))
    code = _prefix(init)
    code += _ld_bc(0x6000) + bytes((0x3E, ALLOC_FAST_REQUIRED)) + _call(alloc) + _jp_c(FAIL_PC) + _expect_hl(0x8000)
    code += _ld_bc(2) + bytes((0x3E, ALLOC_FAST_REQUIRED)) + _call(alloc) + _jp_nc(FAIL_PC) + _expect_a(E_NOMEM)
    code += _ld_bc(0x2000) + bytes((0x3E, ALLOC_COLD_PREFERRED)) + _call(alloc) + _jp_c(FAIL_PC) + _expect_hl(0x6000)
    code += _jp(PASS_PC)
    run_sna(root, bytes(code), patch=phase1._kernel_patch(kernel_bytes))


def _p104_test(root: Path, labels: dict[str, int], kernel_bytes: bytes) -> None:
    init, alloc, free, info = (labels[name] for name in ("zx48_memory_init", "zx48_alloc", "zx48_free", "zx48_mem_info"))
    code = _prefix(init)
    code += _ld_bc(0x3000) + bytes((0x3E, ALLOC_ANY)) + _call(alloc) + _jp_c(FAIL_PC)
    code += _store_hl(SAVED_BASE) + _expect_hl(0x6000)
    code += _load_hl(SAVED_BASE) + _ld_bc(0x2000) + _call(free) + _jp_nc(FAIL_PC) + _expect_a(E_INVAL)
    code += _ld_hl(SCRATCH_BASE) + _call(info)
    expected = bytes((0x00,0x50, 0x00,0x50, 0x00,0x00, 0x00,0x00, 0x00,0x50, 0x01,0x00, 0x00,0x00, 0x00,0x00))
    code += _expect_bytes(SCRATCH_BASE, expected)
    code += _load_hl(SAVED_BASE) + _ld_bc(0x3000) + _call(free) + _jp_c(FAIL_PC)
    code += _ld_hl(SCRATCH_BASE) + _call(info)
    full = bytes((0x00,0x60, 0x00,0x60, 0x00,0x20, 0x00,0x20, 0x00,0x80, 0x00,0x00, 0x00,0x00, 0x00,0x00))
    code += _expect_bytes(SCRATCH_BASE, full)
    code += _ld_bc(0x1000) + bytes((0x3E, ALLOC_COLD_PREFERRED)) + _call(alloc) + _jp_c(FAIL_PC) + _expect_hl(0x6000)
    code += _jp(PASS_PC)
    run_sna(root, bytes(code), patch=phase1._kernel_patch(kernel_bytes))


def _p105_test(root: Path, labels: dict[str, int], kernel_bytes: bytes) -> None:
    init, alloc, info, pin, process_init = (labels[name] for name in ("zx48_memory_init", "zx48_alloc", "zx48_mem_info", "zx48_memory_pin_bytes", "zx48_process_init"))
    code = _prefix(init)
    code += _call(process_init)
    code += _ld_hl(SCRATCH_BASE) + _call(info)
    initial = bytes((0x00,0x60, 0x00,0x60, 0x00,0x20, 0x00,0x20, 0x00,0x80, 0x00,0x00, 0x00,0x00, 0x00,0x00))
    code += _expect_bytes(SCRATCH_BASE, initial)
    code += _ld_bc(0x0100) + _call(pin)
    code += _ld_bc(0x0200) + bytes((0x3E, ALLOC_ANY)) + _call(alloc) + _jp_c(FAIL_PC)
    code += _ld_hl(SCRATCH_BASE) + _call(info)
    changed = bytes((0x00,0x60, 0x00,0x60, 0x00,0x1E, 0x00,0x1E, 0x00,0x7E, 0x01,0x00, 0x00,0x01, 0x00,0x00))
    code += _expect_bytes(SCRATCH_BASE, changed)
    code += _jp(PASS_PC)
    run_sna(root, bytes(code), patch=phase1._kernel_patch(kernel_bytes))


def dispatch(
    root: Path,
    action: str,
    step: str,
    *,
    sha256_file: Callable[[Path], str],
    run_command: Callable[..., Any],
    require_project_tool: Callable[[Path, str | Path], Path],
):
    if step not in ("P1.02", "P1.03", "P1.04", "P1.05"):
        raise Phase1MemoryError(f"Phase-1 memory step is not registered: {step}")

    assertions = _source_contract(root)
    failed = [item["name"] for item in assertions if item["passed"] is not True]
    require(not failed, f"static Phase-1 memory failures: {failed}")

    command, kernel, listing = phase1._assemble_kernel(root, run_command, require_project_tool)
    names = (
        "zx48_memory_init", "zx48_alloc", "zx48_free", "zx48_mem_info",
        "zx48_memory_pin_bytes", "zx48_process_init",
    )
    labels = phase1._labels(listing, names)
    kernel_bytes = kernel.read_bytes()

    if action == "test":
        tests = {
            "P1.02": _p102_test,
            "P1.03": _p103_test,
            "P1.04": _p104_test,
            "P1.05": _p105_test,
        }
        tests[step](root, labels, kernel_bytes)
        assertions.append({"name": f"{step.lower().replace('.', '-')}-runtime-contract", "passed": True})

    paths = (
        root / "v1/src/kernel/memory.asm",
        root / "v1/include/zx48ux.inc",
        root / "v1/tools-host/test-driver/phase1_memory.py",
        kernel,
    )
    hashes = {str(path.relative_to(root)).replace("\\", "/"): sha256_file(path) for path in paths}
    return [command], hashes, assertions
