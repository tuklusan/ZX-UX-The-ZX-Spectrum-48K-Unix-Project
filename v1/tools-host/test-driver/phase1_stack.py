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

MARGIN_START = 0xFB10
MARGIN_END = 0xFB3F
RELEASE_FLOOR = 0xFB40
MARGIN_PATTERN = bytes(((index * 37 + 0x31) & 0xFF) for index in range(MARGIN_END - MARGIN_START + 1))
VERIFY_PC = 0xB100


class StackMatrixError(DriverError):
    """Raised when the Phase-1 kernel-stack correction matrix is violated."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise StackMatrixError(message)


def _word(value: int) -> bytes:
    return bytes((value & 0xFF, (value >> 8) & 0xFF))


def _call(address: int) -> bytes:
    return b"\xCD" + _word(address)


def _jp(address: int) -> bytes:
    return b"\xC3" + _word(address)


def _jp_c(address: int) -> bytes:
    return b"\xDA" + _word(address)


def _jp_z(address: int) -> bytes:
    return b"\xCA" + _word(address)


def _jp_nz(address: int) -> bytes:
    return b"\xC2" + _word(address)


def _ld_sp(address: int) -> bytes:
    return b"\x31" + _word(address)


def _ld_hl(value: int) -> bytes:
    return b"\x21" + _word(value)


def _ld_de(value: int) -> bytes:
    return b"\x11" + _word(value)


def _store_byte(address: int, value: int) -> bytes:
    return bytes((0x3E, value & 0xFF, 0x32)) + _word(address)


def _load_byte(address: int) -> bytes:
    return b"\x3A" + _word(address)


def _patch(kernel_bytes: bytes, extras: tuple[tuple[int, bytes], ...] = ()):
    def apply(ram: bytearray) -> None:
        start = phase1.KERNEL_BASE - 0x4000
        ram[start:start + len(kernel_bytes)] = kernel_bytes
        margin = MARGIN_START - 0x4000
        ram[margin:margin + len(MARGIN_PATTERN)] = MARGIN_PATTERN
        for address, payload in extras:
            offset = address - 0x4000
            require(0 <= offset <= len(ram) - len(payload), "stack fixture patch outside RAM")
            ram[offset:offset + len(payload)] = payload
    return apply


def _margin_verify() -> bytes:
    code = bytearray()
    for offset, expected in enumerate(MARGIN_PATTERN):
        code += _load_byte(MARGIN_START + offset) + bytes((0xFE, expected)) + _jp_nz(FAIL_PC)
    code += _jp(PASS_PC)
    return bytes(code)


def _source_contract(root: Path) -> list[dict[str, object]]:
    errors = (root / "v1/src/kernel/errors.asm").read_text(encoding="utf-8").lower()
    interrupt = (root / "v1/src/kernel/interrupt.asm").read_text(encoding="utf-8").lower()
    syscall = (root / "v1/src/kernel/syscall.asm").read_text(encoding="utf-8").lower()
    rom = (root / "v1/src/kernel/rom_services.asm").read_text(encoding="utf-8").lower()
    scheduler = (root / "v1/src/kernel/scheduler.asm").read_text(encoding="utf-8").lower()
    return [
        {"name": "guard-frozen-at-16", "passed": "kstack_guard_size         equ 16" in errors},
        {"name": "sample-ignores-user-stacks", "passed": "cp $fb\n    ret c\n    cp $fd\n    ret nc" in errors},
        {"name": "fast-isr-samples-stack", "passed": "exx\n    call zx48_kernel_stack_sample\n    call zx48_interrupt_work" in interrupt},
        {"name": "safe-isr-samples-stack", "passed": "push hl\n    call zx48_kernel_stack_sample\n    call zx48_interrupt_work" in interrupt},
        {"name": "syscall-return-checks-stack", "passed": "call zx48_kernel_stack_sample\n    call zx48_kernel_stack_check" in syscall},
        {"name": "rom-return-checks-stack", "passed": "call zx48_kernel_stack_sample\n    call zx48_kernel_stack_check" in rom},
        {"name": "scheduler-return-checks-stack", "passed": "call zx48_kernel_stack_sample\n    call zx48_kernel_stack_check" in scheduler},
    ]


def _stress_test(root: Path, labels: dict[str, int], kernel_bytes: bytes) -> None:
    init = labels["zx48_kernel_stack_init"]
    check = labels["zx48_kernel_stack_check"]
    low = labels["kernel_stack_low_water"]
    memory_init = labels["zx48_memory_init"]
    process_init = labels["zx48_process_init"]
    handles_init = labels["zx48_handles_init"]
    pipe_init = labels["zx48_pipe_init"]
    rom_key_scan = labels["zx48_rom_key_scan"]
    interrupt = labels["zx48_interrupt"]
    altreg_busy = labels["altreg_busy"]

    code = bytearray()
    code += b"\xF3" + _ld_sp(phase1.USER_STACK)
    code += _call(init) + _call(memory_init) + _call(process_init) + _call(handles_init) + _call(pipe_init)
    code += b"\xAF" + _call(0xE000)                                  # SYS_VERSION
    code += _ld_hl(0xA000) + b"\x3E\x20" + _call(0xE000) + _jp_c(FAIL_PC)  # SYS_PIPE
    code += _ld_hl(0) + b"\x3E\x11" + _call(0xE000) + _jp_c(FAIL_PC)
    code += _ld_hl(1) + b"\x3E\x11" + _call(0xE000) + _jp_c(FAIL_PC)

    code += _ld_sp(phase1.KSTACK_TOP) + _call(rom_key_scan)
    code += _store_byte(altreg_busy, 0) + _call(interrupt) + b"\xF3"
    code += _store_byte(altreg_busy, 1) + _call(interrupt) + b"\xF3"
    code += _call(check)

    code += b"\x2A" + _word(low) + _ld_de(RELEASE_FLOOR) + b"\xB7\xED\x52" + _jp_c(FAIL_PC)
    code += b"\x2A" + _word(low) + _ld_de(phase1.KSTACK_TOP) + b"\xB7\xED\x52" + _jp_z(FAIL_PC)
    code += _margin_verify()
    run_sna(root, bytes(code), patch=_patch(kernel_bytes))


def _guard_negative(root: Path, labels: dict[str, int], kernel_bytes: bytes) -> None:
    init = labels["zx48_kernel_stack_init"]
    check = labels["zx48_kernel_stack_check"]
    panic_code = labels["kernel_panic_code"]
    panic_halt = labels["zx48_panic_halt"]

    code = bytearray()
    code += b"\xF3" + _ld_sp(phase1.KSTACK_TOP) + _call(init)
    code += _store_byte(0xFB00, 0) + _call(check) + _jp(FAIL_PC)
    verifier = _load_byte(panic_code) + b"\xFE\x04" + _jp_z(PASS_PC) + _jp(FAIL_PC)
    patched = bytearray(kernel_bytes)
    offset = panic_halt - phase1.KERNEL_BASE
    require(0 <= offset <= len(patched) - 3, "panic label outside kernel image")
    patched[offset:offset + 3] = _jp(VERIFY_PC)
    run_sna(root, bytes(code), patch=_patch(bytes(patched), ((VERIFY_PC, verifier),)))


def _overflow_negative(root: Path, labels: dict[str, int], kernel_bytes: bytes) -> None:
    init = labels["zx48_kernel_stack_init"]
    sample = labels["zx48_kernel_stack_sample"]
    low = labels["kernel_stack_low_water"]
    code = bytearray()
    code += b"\xF3" + _ld_sp(phase1.USER_STACK) + _call(init)
    # CALL at FB42 places its return word at FB40; the sampler's accounted
    # temporary push reaches FB3E, deliberately exceeding the 448-byte limit.
    code += _ld_sp(0xFB42) + _call(sample) + _ld_sp(phase1.USER_STACK)
    code += b"\x2A" + _word(low) + _ld_de(RELEASE_FLOOR) + b"\xB7\xED\x52"
    code += _jp_c(PASS_PC) + _jp(FAIL_PC)
    run_sna(root, bytes(code), patch=_patch(kernel_bytes))


def dispatch(
    root: Path,
    action: str,
    step: str,
    *,
    sha256_file: Callable[[Path], str],
    run_command: Callable[..., Any],
    require_project_tool: Callable[[Path, str | Path], Path],
):
    if step != "P1.33":
        raise StackMatrixError(f"kernel-stack correction step is not registered: {step}")

    assertions = _source_contract(root)
    failed = [item["name"] for item in assertions if item["passed"] is not True]
    require(not failed, f"static kernel-stack correction failures: {failed}")

    command, kernel, listing = phase1._assemble_kernel(root, run_command, require_project_tool)
    names = (
        "zx48_kernel_stack_init",
        "zx48_kernel_stack_check",
        "zx48_kernel_stack_sample",
        "kernel_stack_low_water",
        "kernel_panic_code",
        "zx48_panic_halt",
        "zx48_memory_init",
        "zx48_process_init",
        "zx48_handles_init",
        "zx48_pipe_init",
        "zx48_rom_key_scan",
        "zx48_interrupt",
        "altreg_busy",
    )
    labels = phase1._labels(listing, names)
    kernel_bytes = kernel.read_bytes()

    if action == "test":
        _stress_test(root, labels, kernel_bytes)
        _guard_negative(root, labels, kernel_bytes)
        _overflow_negative(root, labels, kernel_bytes)
        assertions.extend(
            [
                {"name": "release-watermark-at-or-above-fb40", "passed": True, "maximum_bytes": 448},
                {"name": "architectural-64-byte-margin-untouched", "passed": True},
                {"name": "guard-corruption-panics-kstack", "passed": True},
                {"name": "over-448-negative", "passed": True},
            ]
        )

    paths = (
        root / "v1/src/kernel/errors.asm",
        root / "v1/src/kernel/interrupt.asm",
        root / "v1/src/kernel/syscall.asm",
        root / "v1/src/kernel/rom_services.asm",
        root / "v1/src/kernel/scheduler.asm",
        root / "v1/tools-host/test-driver/phase1_stack.py",
        kernel,
    )
    return [command], {str(path.relative_to(root)): sha256_file(path) for path in paths}, assertions
