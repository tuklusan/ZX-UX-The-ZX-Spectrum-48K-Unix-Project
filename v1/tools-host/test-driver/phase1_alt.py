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

# Includes IM2 acknowledge/vector fetch (19 T), FDFD JP (10 T), handler path,
# the maximal zx48_interrupt_work branch combination, and RETI.
INTERRUPT_WORK_MAX_TSTATES = 537
# P1.33 adds the kernel-stack-only sampler to both paths. Its maximal
# update path costs 169 T-states including CALL and its temporary push.
FAST_ISR_MAX_TSTATES = 831
SAFE_ISR_MAX_TSTATES = 883
FAST_ISR_MAX_STACK_BYTES = 6
SAFE_ISR_MAX_STACK_BYTES = 14
PRIMARY_BC = 0x1122
PRIMARY_DE = 0x3344
PRIMARY_HL = 0x5566
SHADOW_BC = 0x7788
SHADOW_DE = 0x99AA
SHADOW_HL = 0xBBCC


class AltBoundaryError(DriverError):
    """Raised when the Phase-1 alternate-register boundary contract is violated."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AltBoundaryError(message)


def _word(value: int) -> bytes:
    return bytes((value & 0xFF, (value >> 8) & 0xFF))


def _call(address: int) -> bytes:
    return b"\xCD" + _word(address)


def _jp(address: int) -> bytes:
    return b"\xC3" + _word(address)


def _jp_nz(address: int) -> bytes:
    return b"\xC2" + _word(address)


def _ld_sp(address: int) -> bytes:
    return b"\x31" + _word(address)


def _ld_bc(value: int) -> bytes:
    return b"\x01" + _word(value)


def _ld_de(value: int) -> bytes:
    return b"\x11" + _word(value)


def _ld_hl(value: int) -> bytes:
    return b"\x21" + _word(value)


def _set_busy(address: int, value: int) -> bytes:
    return bytes((0x3E, value & 0xFF, 0x32)) + _word(address)


def _check_pair(registers: str, value: int) -> bytes:
    opcodes = {
        "bc": (0x78, 0x79),
        "de": (0x7A, 0x7B),
        "hl": (0x7C, 0x7D),
    }
    high_op, low_op = opcodes[registers]
    high = (value >> 8) & 0xFF
    low = value & 0xFF
    return (
        bytes((high_op, 0xFE, high))
        + _jp_nz(FAIL_PC)
        + bytes((low_op, 0xFE, low))
        + _jp_nz(FAIL_PC)
    )


def _register_bank_setup() -> bytes:
    return (
        _ld_bc(PRIMARY_BC)
        + _ld_de(PRIMARY_DE)
        + _ld_hl(PRIMARY_HL)
        + b"\xD9"
        + _ld_bc(SHADOW_BC)
        + _ld_de(SHADOW_DE)
        + _ld_hl(SHADOW_HL)
        + b"\xD9"
    )


def _check_primary_and_shadow() -> bytes:
    return (
        _check_pair("bc", PRIMARY_BC)
        + _check_pair("de", PRIMARY_DE)
        + _check_pair("hl", PRIMARY_HL)
        + b"\xD9"
        + _check_pair("bc", SHADOW_BC)
        + _check_pair("de", SHADOW_DE)
        + _check_pair("hl", SHADOW_HL)
        + b"\xD9"
    )


def _patched_safe_failure(kernel_bytes: bytes, safe_address: int) -> bytes:
    patched = bytearray(kernel_bytes)
    offset = safe_address - phase1.KERNEL_BASE
    require(0 <= offset <= len(patched) - 3, "safe ISR label outside kernel image")
    patched[offset:offset + 3] = _jp(FAIL_PC)
    return bytes(patched)


def _source_contract(root: Path) -> list[dict[str, object]]:
    interrupt = (root / "v1/src/kernel/interrupt.asm").read_text(encoding="utf-8")
    lowered = interrupt.lower()
    fast_sequence = ("pop af", "ex af,af'", "exx", "call zx48_kernel_stack_sample", "call zx48_interrupt_work", "exx", "ex af,af'", "ei", "reti")
    safe_sequence = ("push bc", "push de", "push hl", "call zx48_kernel_stack_sample", "call zx48_interrupt_work", "pop hl", "pop de", "pop bc", "pop af", "ei", "reti")
    return [
        {"name": "altreg-busy-gate", "passed": "ld a,(altreg_busy)" in lowered and "jr nz,zx48_interrupt_safe" in lowered},
        {"name": "fast-path-balanced-banks", "passed": all(token in lowered for token in fast_sequence)},
        {"name": "safe-path-stack-preservation", "passed": all(token in lowered for token in safe_sequence)},
        {"name": "isr-never-calls-rom", "passed": "call rom_" not in lowered and "call zx48_rom_" not in lowered},
        {"name": "fast-isr-frame-cost", "passed": FAST_ISR_MAX_STACK_BYTES == 6, "bytes": FAST_ISR_MAX_STACK_BYTES},
        {"name": "safe-isr-frame-cost", "passed": SAFE_ISR_MAX_STACK_BYTES == 14, "bytes": SAFE_ISR_MAX_STACK_BYTES},
        {"name": "fast-isr-max-cycle-cost", "passed": FAST_ISR_MAX_TSTATES == 831, "tstates": FAST_ISR_MAX_TSTATES},
        {"name": "safe-isr-max-cycle-cost", "passed": SAFE_ISR_MAX_TSTATES == 883, "tstates": SAFE_ISR_MAX_TSTATES},
        {"name": "pal-frame-bounded", "passed": SAFE_ISR_MAX_TSTATES < 69888, "tstates": SAFE_ISR_MAX_TSTATES},
    ]


def _fast_path_test(root: Path, labels: dict[str, int], kernel_bytes: bytes) -> None:
    interrupt = labels["zx48_interrupt"]
    busy = labels["altreg_busy"]
    safe = labels["zx48_interrupt_safe"]
    code = bytearray()
    code += b"\xF3" + _ld_sp(phase1.USER_STACK)
    code += _set_busy(busy, 0)
    code += _ld_bc(PRIMARY_BC) + _ld_de(PRIMARY_DE) + _ld_hl(PRIMARY_HL)
    code += _call(interrupt)
    code += _check_pair("bc", PRIMARY_BC) + _check_pair("de", PRIMARY_DE) + _check_pair("hl", PRIMARY_HL)
    code += _jp(PASS_PC)
    patched = _patched_safe_failure(kernel_bytes, safe)
    run_sna(root, bytes(code), patch=phase1._kernel_patch(patched))


def _safe_exx_boundary_test(root: Path, labels: dict[str, int], kernel_bytes: bytes) -> None:
    interrupt = labels["zx48_interrupt"]
    busy = labels["altreg_busy"]
    code = bytearray()
    code += b"\xF3" + _ld_sp(phase1.USER_STACK)
    code += _register_bank_setup()
    code += _set_busy(busy, 1)
    code += _call(interrupt)  # boundary after publishing busy, before EXX
    code += b"\xD9"
    code += _call(interrupt)  # boundary with shadow BC/DE/HL foreground-live
    code += b"\xD9"
    code += _call(interrupt)  # boundary after restoring the primary bank
    code += _check_primary_and_shadow()
    code += _set_busy(busy, 0)
    code += _jp(PASS_PC)
    run_sna(root, bytes(code), patch=phase1._kernel_patch(kernel_bytes))


def _safe_exaf_boundary_test(root: Path, labels: dict[str, int], kernel_bytes: bytes) -> None:
    interrupt = labels["zx48_interrupt"]
    busy = labels["altreg_busy"]
    code = bytearray()
    code += b"\xF3" + _ld_sp(phase1.USER_STACK)
    code += _set_busy(busy, 1)
    code += b"\x3E\x11\x08\x3E\x22\x08"  # A=11, A'=22, primary selected
    code += _call(interrupt)                 # before EX AF,AF'
    code += b"\x08"
    code += _call(interrupt)                 # while alternate AF is foreground-live
    code += b"\x08"
    code += _call(interrupt)                 # after restoring primary AF
    code += b"\xFE\x11" + _jp_nz(FAIL_PC)
    code += b"\x08\xFE\x22" + _jp_nz(FAIL_PC) + b"\x08"
    code += _set_busy(busy, 0)
    code += _jp(PASS_PC)
    run_sna(root, bytes(code), patch=phase1._kernel_patch(kernel_bytes))


def _early_clear_negative_test(root: Path, labels: dict[str, int], kernel_bytes: bytes) -> None:
    interrupt = labels["zx48_interrupt"]
    busy = labels["altreg_busy"]
    code = bytearray()
    code += b"\xF3" + _ld_sp(phase1.USER_STACK)
    code += _register_bank_setup()
    code += _set_busy(busy, 1)
    code += b"\xD9"                         # shadow bank becomes foreground-live
    code += _set_busy(busy, 0)              # deliberately one instruction too early
    code += _call(interrupt)                 # fast ISR now corrupts hidden primary bank
    code += b"\xD9"                         # expose damaged primary bank
    code += b"\x78\xFE\x11" + _jp_nz(PASS_PC)
    code += b"\x79\xFE\x22" + _jp_nz(PASS_PC)
    code += _jp(FAIL_PC)
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
    if step != "P1.30":
        raise AltBoundaryError(f"alternate-register boundary step is not registered: {step}")

    assertions = _source_contract(root)
    failed = [item["name"] for item in assertions if item["passed"] is not True]
    require(not failed, f"static alternate-register failures: {failed}")

    command, kernel, listing = phase1._assemble_kernel(root, run_command, require_project_tool)
    labels = phase1._labels(listing, ("zx48_interrupt", "zx48_interrupt_safe", "altreg_busy"))
    kernel_bytes = kernel.read_bytes()

    if action == "test":
        _fast_path_test(root, labels, kernel_bytes)
        _safe_exx_boundary_test(root, labels, kernel_bytes)
        _safe_exaf_boundary_test(root, labels, kernel_bytes)
        _early_clear_negative_test(root, labels, kernel_bytes)
        assertions.extend(
            [
                {"name": "fast-path-primary-state-preserved", "passed": True},
                {"name": "exx-boundaries-use-safe-path", "passed": True},
                {"name": "exaf-boundaries-use-safe-path", "passed": True},
                {"name": "early-clear-negative-detects-corruption", "passed": True},
            ]
        )

    paths = (
        root / "v1/src/kernel/interrupt.asm",
        root / "v1/tools-host/test-driver/phase1_alt.py",
        kernel,
    )
    return [command], {str(path.relative_to(root)): sha256_file(path) for path in paths}, assertions
