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

from driver_core import DriverError, require_project_tool, run_command
from fuse_harness import FAIL_PC, PASS_PC, run_sna
import phase1


class Phase1ProbeError(DriverError):
    """Raised with the exact P1.28 runtime stage that stopped making progress."""


def _panic_to_fail(labels: dict[str, int], kernel_bytes: bytes) -> bytes:
    patched = bytearray(kernel_bytes)
    offset = labels["zx48_panic_halt"] - phase1.KERNEL_BASE
    if not 0 <= offset <= len(patched) - 3:
        raise Phase1ProbeError("panic label outside kernel image")
    patched[offset:offset + 3] = phase1._jp(FAIL_PC)
    return bytes(patched)


def _prefix(labels: dict[str, int]) -> bytearray:
    code = bytearray()
    code += b"\xF3" + phase1._ld_sp(phase1.USER_STACK)
    code += phase1._call(labels["zx48_kernel_stack_init"])
    code += phase1._call(labels["zx48_memory_init"])
    code += phase1._call(labels["zx48_process_init"])
    code += phase1._call(labels["zx48_handles_init"])
    code += phase1._call(labels["zx48_pipe_init"])
    return code


def _exercise(labels: dict[str, int], through: str) -> bytes:
    code = _prefix(labels)
    code += b"\xAF" + phase1._call(0xE000)
    if through == "version":
        return bytes(code + phase1._jp(PASS_PC))
    code += phase1._ld_hl(0xA000) + b"\x3E\x20" + phase1._call(0xE000) + phase1._jp_c(FAIL_PC)
    if through == "pipe":
        return bytes(code + phase1._jp(PASS_PC))
    code += phase1._ld_hl(0) + b"\x3E\x11" + phase1._call(0xE000) + phase1._jp_c(FAIL_PC)
    if through == "close-read":
        return bytes(code + phase1._jp(PASS_PC))
    code += phase1._ld_hl(1) + b"\x3E\x11" + phase1._call(0xE000) + phase1._jp_c(FAIL_PC)
    if through == "close-write":
        return bytes(code + phase1._jp(PASS_PC))
    low = labels["kernel_stack_low_water"]
    check = labels["zx48_kernel_stack_check"]
    code += b"\x2A" + phase1._word(low) + phase1._ld_de(phase1.KSTACK_STRESS_FLOOR)
    code += b"\xB7\xED\x52" + phase1._jp_c(FAIL_PC)
    code += phase1._call(check) + phase1._jp(PASS_PC)
    return bytes(code)


def run(root: Path) -> None:
    _, kernel, listing = phase1._assemble_kernel(root, run_command, require_project_tool)
    names = (
        "zx48_kernel_stack_init",
        "zx48_kernel_stack_check",
        "kernel_stack_low_water",
        "zx48_panic_halt",
        "zx48_memory_init",
        "zx48_process_init",
        "zx48_handles_init",
        "zx48_pipe_init",
    )
    labels = phase1._labels(listing, names)
    kernel_bytes = _panic_to_fail(labels, kernel.read_bytes())
    for stage in ("version", "pipe", "close-read", "close-write", "watermark"):
        try:
            run_sna(root, _exercise(labels, stage), patch=phase1._kernel_patch(kernel_bytes), timeout=5.0)
        except DriverError as exc:
            raise Phase1ProbeError(f"P1.28 staged runtime failed at {stage}: {exc}") from exc
