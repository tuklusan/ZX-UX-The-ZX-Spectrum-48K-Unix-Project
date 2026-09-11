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
import re
from typing import Any, Callable

from driver_core import DriverError
from fuse_harness import FAIL_PC, PASS_PC, run_sna

KERNEL_BASE = 0xE000
KERNEL_SIZE = 0x2000
KSTACK_TOP = 0xFD00
KSTACK_STRESS_FLOOR = 0xFB60
USER_STACK = 0xBFC0
ROM_STACK = 0xFC80
VERIFY_PC = 0xB100


class Phase1Error(DriverError):
    """Raised when a Phase-1 correction contract is violated."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Phase1Error(message)


def _word(value: int) -> bytes:
    return bytes((value & 0xFF, (value >> 8) & 0xFF))


def _call(address: int) -> bytes:
    return b"\xCD" + _word(address)


def _jp(address: int) -> bytes:
    return b"\xC3" + _word(address)


def _jp_nz(address: int) -> bytes:
    return b"\xC2" + _word(address)


def _jp_c(address: int) -> bytes:
    return b"\xDA" + _word(address)


def _jp_z(address: int) -> bytes:
    return b"\xCA" + _word(address)


def _ld_sp(address: int) -> bytes:
    return b"\x31" + _word(address)


def _ld_hl(value: int) -> bytes:
    return b"\x21" + _word(value)


def _ld_de(value: int) -> bytes:
    return b"\x11" + _word(value)


def _ld_iy(value: int) -> bytes:
    return b"\xFD\x21" + _word(value)


def _assemble_kernel(root: Path, run_command: Callable[..., Any], require_project_tool: Callable[[Path, str | Path], Path]):
    assembler = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    listing = build / "kernel-p1.lst"
    result = run_command(
        [assembler, "--nologo", "--lst=../../build/kernel-p1.lst", "kernel.asm"],
        cwd=root / "v1/src/kernel",
        timeout_seconds=30.0,
    )
    require(not result.timed_out and result.exit_code == 0, f"kernel assembly failed: {result.stderr or result.stdout}")
    kernel = build / "kernel.bin"
    require(kernel.is_file() and kernel.stat().st_size == KERNEL_SIZE, "kernel image must remain exactly 8192 bytes")
    require(listing.is_file(), "kernel listing missing")
    return result, kernel, listing


def _labels(listing: Path, names: tuple[str, ...]) -> dict[str, int]:
    text = listing.read_text(encoding="utf-8", errors="replace")
    found: dict[str, int] = {}
    for name in names:
        for line in text.splitlines():
            label_marker = name + ":"
            equ_marker = re.search(rf"\b{re.escape(name)}\s+EQU\b", line)
            if label_marker not in line and equ_marker is None:
                continue
            before = line.split(label_marker, 1)[0] if label_marker in line else line[:equ_marker.start()]
            words = re.findall(r"\b[0-9A-Fa-f]{4}\b", before)
            if words:
                found[name] = int(words[-1], 16)
                break
        require(name in found, f"kernel listing label missing: {name}")
    return found


def _kernel_patch(kernel_bytes: bytes, extra: tuple[int, bytes] | None = None):
    def patch(ram: bytearray) -> None:
        start = KERNEL_BASE - 0x4000
        ram[start:start + len(kernel_bytes)] = kernel_bytes
        if extra is not None:
            address, payload = extra
            offset = address - 0x4000
            ram[offset:offset + len(payload)] = payload
    return patch


def _source_contract(root: Path) -> list[dict[str, object]]:
    errors = (root / "v1/src/kernel/errors.asm").read_text(encoding="utf-8")
    syscall = (root / "v1/src/kernel/syscall.asm").read_text(encoding="utf-8")
    rom = (root / "v1/src/kernel/rom_services.asm").read_text(encoding="utf-8")
    scheduler = (root / "v1/src/kernel/scheduler.asm").read_text(encoding="utf-8")
    boot = (root / "v1/src/boot/entry.asm").read_text(encoding="utf-8")
    interrupt = (root / "v1/src/kernel/interrupt.asm").read_text(encoding="utf-8")

    switch = syscall.index("ld sp,BOOT_STACK_TOP")
    dispatch = syscall.index("call zx48_syscall_impl")
    return [
        {"name": "guard-size-16", "passed": "KSTACK_GUARD_SIZE         EQU 16" in errors},
        {"name": "sample-accounts-own-push", "passed": "add hl,sp\n    dec hl\n    dec hl" in errors},
        {"name": "syscall-switches-before-dispatch", "passed": switch < dispatch},
        {"name": "syscall-return-checks-guard", "passed": "call zx48_kernel_stack_check" in syscall},
        {"name": "rom-return-checks-guard", "passed": "zx48_rom_checked_return:" in rom and "call zx48_kernel_stack_check" in rom},
        {"name": "boot-initializes-stack-guard", "passed": "call zx48_kernel_stack_init" in boot},
        {"name": "scheduler-checks-before-user-restore", "passed": "call zx48_kernel_stack_check" in scheduler},
        {"name": "safe-isr-frame-bounded", "passed": all(token in interrupt for token in ("zx48_interrupt_safe:", "push bc", "push de", "push hl", "call zx48_interrupt_work"))},
    ]


def _p128_test(root: Path, labels: dict[str, int], kernel_bytes: bytes):
    init = labels["zx48_kernel_stack_init"]
    sample = labels["zx48_kernel_stack_sample"]
    check = labels["zx48_kernel_stack_check"]
    low = labels["kernel_stack_low_water"]
    panic_code = labels["kernel_panic_code"]
    panic_halt = labels["zx48_panic_halt"]
    memory_init = labels["zx48_memory_init"]
    process_init = labels["zx48_process_init"]
    handles_init = labels["zx48_handles_init"]
    pipe_init = labels["zx48_pipe_init"]

    code = bytearray()
    code += b"\xF3" + _ld_sp(USER_STACK)
    code += _call(init) + _call(memory_init) + _call(process_init) + _call(handles_init) + _call(pipe_init)
    code += b"\xAF" + _call(0xE000)  # SYS_VERSION
    code += _ld_hl(0xA000) + b"\x3E\x20" + _call(0xE000) + _jp_c(FAIL_PC)  # SYS_PIPE
    code += _ld_hl(0) + b"\x3E\x11" + _call(0xE000) + _jp_c(FAIL_PC)       # close h0
    code += _ld_hl(1) + b"\x3E\x11" + _call(0xE000) + _jp_c(FAIL_PC)       # close h1
    code += b"\x2A" + _word(low) + _ld_de(KSTACK_STRESS_FLOOR) + b"\xB7\xED\x52" + _jp_c(FAIL_PC)
    code += _call(check) + _jp(PASS_PC)
    run_sna(root, bytes(code), patch=_kernel_patch(kernel_bytes))

    negative = bytearray()
    negative += b"\xF3" + _ld_sp(KSTACK_TOP) + _call(init)
    negative += b"\x3E\x00\x32\x00\xFB" + _call(check) + _jp(FAIL_PC)
    verifier = b"\x3A" + _word(panic_code) + b"\xFE\x04" + _jp_z(PASS_PC) + _jp(FAIL_PC)
    patched = bytearray(kernel_bytes)
    offset = panic_halt - KERNEL_BASE
    require(0 <= offset <= len(patched) - 3, "panic label outside kernel image")
    patched[offset:offset + 3] = _jp(VERIFY_PC)
    run_sna(root, bytes(negative), patch=_kernel_patch(bytes(patched), (VERIFY_PC, verifier)))


def _p129_test(root: Path, labels: dict[str, int], kernel_bytes: bytes):
    init = labels["zx48_kernel_stack_init"]
    key_scan = labels["zx48_rom_key_scan"]

    syscall = bytearray()
    syscall += b"\xF3" + _ld_sp(USER_STACK) + _call(init)
    syscall += _ld_iy(0x1234) + b"\xAF" + _call(0xE000)
    syscall += b"\xFD\xE5\xE1" + _ld_de(0x5C3A) + b"\xB7\xED\x52" + _jp_nz(FAIL_PC) + _jp(PASS_PC)
    run_sna(root, bytes(syscall), patch=_kernel_patch(kernel_bytes))

    rom = bytearray()
    rom += b"\xF3" + _ld_sp(ROM_STACK) + _call(init)
    rom += _ld_iy(0x1234) + _call(key_scan)
    rom += b"\xFD\xE5\xE1" + _ld_de(0x5C3A) + b"\xB7\xED\x52" + _jp_nz(FAIL_PC) + _jp(PASS_PC)
    run_sna(root, bytes(rom), patch=_kernel_patch(kernel_bytes))


def dispatch(
    root: Path,
    action: str,
    step: str,
    *,
    sha256_file: Callable[[Path], str],
    run_command: Callable[..., Any],
    require_project_tool: Callable[[Path, str | Path], Path],
):
    if step not in ("P1.28", "P1.29"):
        raise Phase1Error(f"Phase-1 step is not registered: {step}")

    commands: list[Any] = []
    assertions = _source_contract(root)
    failed = [item["name"] for item in assertions if item["passed"] is not True]
    require(not failed, f"static Phase-1 contract failures: {failed}")

    result, kernel, listing = _assemble_kernel(root, run_command, require_project_tool)
    commands.append(result)
    names = (
        "zx48_kernel_stack_init",
        "zx48_kernel_stack_sample",
        "zx48_kernel_stack_check",
        "kernel_stack_low_water",
        "kernel_panic_code",
        "zx48_panic_halt",
        "zx48_memory_init",
        "zx48_process_init",
        "zx48_handles_init",
        "zx48_pipe_init",
        "zx48_rom_key_scan",
    )
    labels = _labels(listing, names)
    kernel_bytes = kernel.read_bytes()

    if action == "test":
        if step == "P1.28":
            _p128_test(root, labels, kernel_bytes)
            assertions.extend(
                [
                    {"name": "stress-high-water-with-isr-margin", "passed": True, "floor": f"0x{KSTACK_STRESS_FLOOR:04X}"},
                    {"name": "guard-corruption-panics-kstack", "passed": True},
                ]
            )
        else:
            _p129_test(root, labels, kernel_bytes)
            assertions.extend(
                [
                    {"name": "syscall-restores-canonical-iy", "passed": True},
                    {"name": "rom-wrapper-restores-canonical-iy", "passed": True},
                ]
            )

    hashes = {
        "v1/build/kernel.bin": sha256_file(kernel),
        "v1/src/kernel/errors.asm": sha256_file(root / "v1/src/kernel/errors.asm"),
        "v1/src/kernel/syscall.asm": sha256_file(root / "v1/src/kernel/syscall.asm"),
        "v1/src/kernel/rom_services.asm": sha256_file(root / "v1/src/kernel/rom_services.asm"),
        "v1/src/kernel/scheduler.asm": sha256_file(root / "v1/src/kernel/scheduler.asm"),
        "v1/tools-host/test-driver/phase1.py": sha256_file(root / "v1/tools-host/test-driver/phase1.py"),
    }
    return commands, hashes, assertions
