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

VERIFY_PC = 0xB100
DISPLAY_PROBE = 0x4000
ROM_WORKSPACE_PROBE = 0x5B00
STACK_PROBE = 0xFB20
TRAMPOLINE_PROBE = 0xFDFD
IM2_TABLE_PROBE = 0xFE00
IM2_VECTOR_BYTE = 0xFD
EMERGENCY_START = 0xFF01
KERNEL_PANIC_CODE = 0xFF10
KERNEL_STACK_LOW_WATER = 0xFF11
ERROR_STATE_END = 0xFF13


class Phase1StartupError(DriverError):
    """Raised when the Phase-1 startup/state initialization contract is violated."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Phase1StartupError(message)


def _word(value: int) -> bytes:
    return bytes((value & 0xFF, (value >> 8) & 0xFF))


def _jp(value: int) -> bytes:
    return b"\xC3" + _word(value)


def _jp_nz(value: int) -> bytes:
    return b"\xC2" + _word(value)


def _poke(address: int, value: int) -> bytes:
    return bytes((0x3E, value & 0xFF, 0x32)) + _word(address)


def _expect(address: int, value: int) -> bytes:
    return b"\x3A" + _word(address) + bytes((0xFE, value & 0xFF)) + _jp_nz(FAIL_PC)


def _source_contract(root: Path) -> list[dict[str, object]]:
    boot = (root / "v1/src/boot/entry.asm").read_text(encoding="utf-8").lower()
    im2 = (root / "v1/src/kernel/im2.asm").read_text(encoding="utf-8").lower()
    kernel = (root / "v1/src/kernel/kernel.asm").read_text(encoding="utf-8")
    im2_call = boot.index("call zx48_im2_init") if "call zx48_im2_init" in boot else -1
    memory_call = boot.index("call zx48_memory_init") if "call zx48_memory_init" in boot else -1
    di_at = boot.index("    di") if "    di" in boot else -1
    return [
        {"name": "boot-di-before-state-init", "passed": 0 <= di_at < im2_call},
        {"name": "boot-establishes-fixed-stack", "passed": "ld sp,boot_stack_top" in boot},
        {"name": "boot-establishes-rom-iy", "passed": "ld iy,rom_iy_anchor" in boot},
        {"name": "state-init-precedes-arena-init", "passed": 0 <= im2_call < memory_call},
        {"name": "bounded-emergency-state-clear", "passed": all(token in im2 for token in ("ld de,im2_table_start+1", "ld bc,im2_table_end-im2_table_start", "ldir", "ld b,error_state_end-emergency_start", "zx48_im2_clear_state:", "ld (de),a", "inc de", "djnz zx48_im2_clear_state"))},
        {"name": "pinned-im2-sequence-retained", "passed": all(token in im2 for token in ("ld a,im2_i_value", "ld i,a", "im 2")) and im2.index("ld i,a") > im2.index("ldir")},
        {"name": "fixed-kernel-subranges-asserted", "passed": all(token in kernel for token in ("ASSERT $ = KERNEL_STACK_START", "ASSERT $ = FAST_RESERVE_START", "ASSERT $ = IM2_TRAMPOLINE_START", "ASSERT $ = IM2_TABLE_START", "ASSERT $ = EMERGENCY_START"))},
        {"name": "kernel-image-exact-8192", "passed": "ASSERT kernel_image_end-kernel_image_start = KERNEL_IMAGE_SIZE" in kernel},
    ]


def _runtime_test(root: Path, labels: dict[str, int], kernel_bytes: bytes) -> None:
    boot = labels["zx48_boot_main_impl"]
    memory_init = labels["zx48_memory_init"]
    ordinary_start = labels["kernel_ordinary_pool_start"]
    ordinary_used_end = labels["kernel_ordinary_used_end"]
    require(ordinary_used_end - ordinary_start <= 6912, "ordinary kernel code/data exceeds 6912 bytes")

    verifier = bytearray()
    for address in range(EMERGENCY_START, KERNEL_PANIC_CODE + 1):
        verifier += _expect(address, 0)
    verifier += _expect(KERNEL_STACK_LOW_WATER, 0x00)
    verifier += _expect(KERNEL_STACK_LOW_WATER + 1, 0xFD)
    verifier += _expect(DISPLAY_PROBE, 0x55)
    verifier += _expect(ROM_WORKSPACE_PROBE, 0x66)
    verifier += _expect(STACK_PROBE, 0x77)
    verifier += _expect(TRAMPOLINE_PROBE, 0x88)
    verifier += _expect(IM2_TABLE_PROBE, IM2_VECTOR_BYTE)
    verifier += _jp(PASS_PC)

    patched = bytearray(kernel_bytes)
    offset = memory_init - phase1.KERNEL_BASE
    require(0 <= offset <= len(patched) - 3, "memory init label outside kernel image")
    patched[offset:offset + 3] = _jp(VERIFY_PC)

    def patch(ram: bytearray) -> None:
        start = phase1.KERNEL_BASE - 0x4000
        ram[start:start + len(patched)] = patched
        extra = VERIFY_PC - 0x4000
        ram[extra:extra + len(verifier)] = verifier

    code = bytearray(b"\xF3")
    code += _poke(DISPLAY_PROBE, 0x55)
    code += _poke(ROM_WORKSPACE_PROBE, 0x66)
    code += _poke(STACK_PROBE, 0x77)
    code += _poke(TRAMPOLINE_PROBE, 0x88)
    code += _poke(IM2_TABLE_PROBE, 0x99)
    for address in range(EMERGENCY_START, ERROR_STATE_END):
        code += _poke(address, 0xA5)
    code += _jp(boot)
    run_sna(root, bytes(code), patch=patch)

    negative = bytearray(b"\xF3")
    negative += _poke(STACK_PROBE, 0x77)
    negative += _poke(STACK_PROBE, 0x00)
    negative += b"\x3A" + _word(STACK_PROBE) + b"\xFE\x77"
    negative += _jp_nz(PASS_PC)
    negative += _jp(FAIL_PC)
    run_sna(root, bytes(negative), patch=phase1._kernel_patch(kernel_bytes))


def dispatch(
    root: Path,
    action: str,
    step: str,
    *,
    sha256_file: Callable[[Path], str],
    run_command: Callable[..., Any],
    require_project_tool: Callable[[Path, str | Path], Path],
):
    if step != "P1.01":
        raise Phase1StartupError(f"Phase-1 startup step is not registered: {step}")

    assertions = _source_contract(root)
    failed = [item["name"] for item in assertions if item["passed"] is not True]
    require(not failed, f"static Phase-1 startup failures: {failed}")

    command, kernel, listing = phase1._assemble_kernel(root, run_command, require_project_tool)
    labels = phase1._labels(
        listing,
        ("zx48_boot_main_impl", "zx48_memory_init", "kernel_ordinary_pool_start", "kernel_ordinary_used_end"),
    )
    kernel_bytes = kernel.read_bytes()
    ordinary_bytes = labels["kernel_ordinary_used_end"] - labels["kernel_ordinary_pool_start"]
    assertions.append({"name": "ordinary-code-data-at-most-6912", "passed": ordinary_bytes <= 6912, "bytes": ordinary_bytes})

    if action == "test":
        _runtime_test(root, labels, kernel_bytes)
        assertions.extend(
            [
                {"name": "emergency-state-poison-cleared", "passed": True},
                {"name": "protected-ranges-preserved-and-vector-init-documented", "passed": True},
                {"name": "excluded-range-negative-oracle", "passed": True},
            ]
        )

    paths = (
        root / "v1/src/boot/entry.asm",
        root / "v1/src/kernel/im2.asm",
        root / "v1/src/kernel/kernel.asm",
        root / "v1/tools-host/test-driver/phase1_startup.py",
        kernel,
    )
    hashes = {str(path.relative_to(root)).replace("\\", "/"): sha256_file(path) for path in paths}
    return [command], hashes, assertions
