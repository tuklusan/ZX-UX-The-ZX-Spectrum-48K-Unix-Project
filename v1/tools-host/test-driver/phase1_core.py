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
from phase1 import _assemble_kernel, _labels

KERNEL_BASE = 0xE000
USER_STACK = 0xBFC0
VERIFY_PC = 0xB100
FRAME1 = 0xA100
FRAME2 = 0xA120
SCRATCH = 0xA200


class Phase1CoreError(DriverError):
    """Raised when the admitted P1.01-P1.12 core contract regresses."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Phase1CoreError(message)


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


def _jp_nc(address: int) -> bytes:
    return b"\xD2" + _word(address)


def _ld_sp(value: int) -> bytes:
    return b"\x31" + _word(value)


def _ld_hl(value: int) -> bytes:
    return b"\x21" + _word(value)


def _ld_de(value: int) -> bytes:
    return b"\x11" + _word(value)


def _ld_bc(value: int) -> bytes:
    return b"\x01" + _word(value)


def _ld_ix(value: int) -> bytes:
    return b"\xDD\x21" + _word(value)


def _ld_iy(value: int) -> bytes:
    return b"\xFD\x21" + _word(value)


def _ld_a(value: int) -> bytes:
    return bytes((0x3E, value & 0xFF))


def _ld_mem_a(address: int) -> bytes:
    return b"\x32" + _word(address)


def _ld_a_mem(address: int) -> bytes:
    return b"\x3A" + _word(address)


def _ld_mem_hl(address: int) -> bytes:
    return b"\x22" + _word(address)


def _ld_hl_mem(address: int) -> bytes:
    return b"\x2A" + _word(address)


def _cp(value: int) -> bytes:
    return bytes((0xFE, value & 0xFF))


def _check_a(value: int) -> bytes:
    return _cp(value) + _jp_nz(FAIL_PC)


def _check_word_mem(address: int, value: int) -> bytes:
    return _ld_hl_mem(address) + _ld_de(value) + b"\xB7\xED\x52" + _jp_nz(FAIL_PC)


def _check_hl(value: int) -> bytes:
    return _ld_de(value) + b"\xB7\xED\x52" + _jp_nz(FAIL_PC)


def _kernel_patch(kernel_bytes: bytes, extras: tuple[tuple[int, bytes], ...] = ()):  # noqa: ANN201
    def patch(ram: bytearray) -> None:
        start = KERNEL_BASE - 0x4000
        ram[start:start + len(kernel_bytes)] = kernel_bytes
        for address, payload in extras:
            offset = address - 0x4000
            ram[offset:offset + len(payload)] = payload
    return patch


def _equ(path: Path, name: str, _seen: set[str] | None = None) -> int:
    text = path.read_text(encoding="utf-8")
    match = re.search(rf"(?m)^\s*{re.escape(name)}\s+EQU\s+([^;\n]+?)\s*$", text)
    require(match is not None, f"missing exact EQU constant: {name}")
    expr = match.group(1).strip()
    seen = set() if _seen is None else set(_seen)
    require(name not in seen, f"recursive EQU constant: {name}")
    seen.add(name)
    if re.fullmatch(r"\$[0-9A-Fa-f]+", expr):
        return int(expr[1:], 16)
    if re.fullmatch(r"[0-9]+", expr):
        return int(expr, 10)
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", expr):
        return _equ(path, expr, seen)
    raise Phase1CoreError(f"unsupported EQU expression for {name}: {expr}")


def _static_contract(root: Path, step: str) -> list[dict[str, object]]:
    include = root / "v1/include/zx48ux.inc"
    memory = (root / "v1/src/kernel/memory.asm").read_text(encoding="utf-8")
    process = (root / "v1/src/kernel/process.asm").read_text(encoding="utf-8")
    scheduler = (root / "v1/src/kernel/scheduler.asm").read_text(encoding="utf-8")
    syscall = (root / "v1/src/kernel/syscall.asm").read_text(encoding="utf-8")
    boot = (root / "v1/src/boot/entry.asm").read_text(encoding="utf-8")
    assertions: list[dict[str, object]] = [
        {"name": "kernel-image-size-frozen", "passed": _equ(include, "KERNEL_IMAGE_SIZE") == 0x2000},
        {"name": "arena-is-one-contiguous-6000-dfff-range", "passed": all(_equ(include, n) == v for n, v in (("ARENA_START", 0x6000), ("ARENA_END", 0xDFFF), ("ARENA_SIZE", 0x8000)))},
        {"name": "maximum-process-count-is-eight", "passed": _equ(include, "MAX_PROCESSES") == 8},
        {"name": "descriptor-size-within-frozen-bound", "passed": _equ(include, "PROC_DESC_SIZE") <= 56 and 8 * _equ(include, "PROC_DESC_SIZE") <= 448},
        {"name": "syscall-gateway-is-e000", "passed": _equ(include, "SYSCALL_GATEWAY") == 0xE000},
    ]
    if step == "P1.01":
        assertions += [
            {"name": "boot-initializes-bounded-subsystems", "passed": all(token in boot for token in ("call zx48_memory_init", "call zx48_process_init", "call zx48_handles_init", "call zx48_pipe_init"))},
            {"name": "boot-uses-dedicated-kernel-stack", "passed": "ld sp,BOOT_STACK_TOP" in boot},
        ]
    elif step in {"P1.02", "P1.03", "P1.04"}:
        assertions += [
            {"name": "free-extent-table-bounded", "passed": _equ(include, "FREE_EXTENT_COUNT") == 16},
            {"name": "allocator-rounds-to-two-byte-alignment", "passed": "bit 0,c" in memory and "inc bc" in memory},
            {"name": "free-rejects-overlap-double-free", "passed": "jp zx48_free_bad" in memory and "zx48_extent_merge_restart:" in memory},
        ]
    elif step == "P1.05":
        assertions += [
            {"name": "minfo1-size-is-sixteen", "passed": _equ(include, "MINFO1_SIZE") == 16},
            {"name": "minfo-computes-class-totals-and-largest", "passed": all(token in memory for token in ("memory_fast_total", "memory_fast_largest", "memory_cold_total", "memory_cold_largest", "call zx48_process_count"))},
        ]
    elif step == "P1.06":
        offsets = {name: int(value) for name, value in re.findall(r"(?m)^\s*(PROC_[A-Z_]+)\s+EQU\s+([0-9]+)\s*$", process)}
        assertions += [
            {"name": "descriptor-required-fields-present", "passed": all(name in offsets for name in ("PROC_PID", "PROC_PARENT", "PROC_STATE", "PROC_FLAGS", "PROC_IMAGE_BASE", "PROC_IMAGE_SIZE", "PROC_STACK_LOW", "PROC_STACK_HIGH", "PROC_SAVED_SP", "PROC_EXIT_STATUS", "PROC_WAIT_OBJECT", "PROC_HANDLES", "PROC_WAKE_TICK", "PROC_CWD", "PROC_NAME", "PROC_OWNED_BYTES", "PROC_PRIVATE_FLAGS"))},
            {"name": "private-started-is-not-public-proc-info", "passed": "and PROC_FLAG_CANCEL" in process and "PROC_PRIVATE_STARTED" not in process[process.index("zx48_process_info:"):process.index("zx48_process_exit:")]},
            {"name": "process-table-is-exactly-eight-descriptors", "passed": "process_table: defs MAX_PROCESSES*PROC_DESC_SIZE,0" in process},
        ]
    elif step == "P1.07":
        assertions += [
            {"name": "saved-sp-is-sole-resume-token", "passed": "ld (ix+PROC_SAVED_SP),l" in scheduler and all(token in scheduler for token in ("pop ix", "pop hl", "pop de", "pop bc", "pop af", "ret"))},
            {"name": "iy-is-global-not-task-local", "passed": "ld iy,ROM_IY_ANCHOR" in scheduler},
        ]
    elif step == "P1.08":
        idle = scheduler[scheduler.index("zx48_idle_loop:"):]
        assertions += [
            {"name": "pid0-idle-is-ei-halt", "passed": re.search(r"zx48_idle_loop:\s*\n\s*ei\s*\n\s*halt\s*\n\s*call zx48_scheduler_wake_scan\s*\n\s*jp zx48_schedule", idle) is not None},
            {"name": "pid0-fallback-is-explicit", "passed": "xor a\n    ld (scheduler_candidate),a" in scheduler and "jp zx48_idle_loop" in scheduler},
        ]
    elif step == "P1.09":
        expected = {
            "SYS_VERSION": 0x00, "SYS_EXIT": 0x01, "SYS_YIELD": 0x02, "SYS_SLEEP": 0x03,
            "SYS_GETPID": 0x04, "SYS_SPAWN": 0x05, "SYS_EXEC": 0x06, "SYS_WAIT": 0x07, "SYS_KILL": 0x08,
            "SYS_OPEN": 0x10, "SYS_UNPACK": 0x1C, "SYS_PIPE": 0x20, "SYS_IOCTL": 0x22,
            "SYS_CON_GETKEY": 0x30, "SYS_CON_SETPOS": 0x35, "SYS_MEM_INFO": 0x60, "SYS_TIME_SET": 0x64,
        }
        errors = {"E_OK": 0, "E_INVAL": 1, "E_NOENT": 2, "E_NOMEM": 3, "E_BUSY": 4, "E_IO": 5, "E_EOF": 6, "E_PERM": 7, "E_CHILD": 8, "E_PIPE": 9, "E_TOOLONG": 10, "E_FORMAT": 11, "E_NOSPC": 12, "E_AGAIN": 13, "E_NOTSUP": 14, "E_INTR": 15, "E_EXIST": 16}
        assertions += [
            {"name": "syscall-number-surface-frozen", "passed": all(_equ(include, name) == value for name, value in expected.items())},
            {"name": "errno-number-surface-frozen", "passed": all(_equ(include, name) == value for name, value in errors.items())},
            {"name": "dispatcher-validates-ranges-before-indirect-jump", "passed": syscall.index("cp SYS_KILL+1") < syscall.index("jp (hl)") and syscall.index("cp SYS_TIME_SET+1") < syscall.index("jp (hl)")},
        ]
    elif step == "P1.10":
        body = syscall[syscall.index("zx48_sys_version:"):syscall.index("zx48_sys_exit:")]
        assertions.append({"name": "sys-version-is-fixed-no-argument-0100", "passed": "ld hl,ZXUX_ABI_VERSION" in body and "xor a" in body})
    elif step == "P1.11":
        body = syscall[syscall.index("zx48_sys_getpid:"):syscall.index("zx48_sys_spawn_stub:")]
        assertions.append({"name": "sys-getpid-does-not-schedule", "passed": "current_pid" in body and "zx48_schedule" not in body})
    elif step == "P1.12":
        assertions += [
            {"name": "round-robin-scan-starts-after-current", "passed": "ld a,(scheduler_current)\n    inc a\n    and 7" in scheduler},
            {"name": "sleepers-wake-during-selection", "passed": "cp PROC_SLEEPING\n    call z,zx48_scheduler_maybe_wake" in scheduler},
            {"name": "selected-task-marked-running", "passed": "ld (ix+PROC_STATE),PROC_RUNNING" in scheduler},
            {"name": "interrupt-does-not-call-scheduler", "passed": "zx48_schedule" not in (root / "v1/src/kernel/interrupt.asm").read_text(encoding="utf-8")},
        ]
    return assertions


def _common_labels(listing: Path) -> dict[str, int]:
    return _labels(listing, (
        "zx48_kernel_stack_init", "zx48_memory_init", "zx48_alloc", "zx48_free", "zx48_memory_pin_bytes", "zx48_mem_info",
        "memory_free_extents", "memory_live_allocations", "memory_pinned_bytes",
        "zx48_process_init", "zx48_process_prepare_pid1", "process_table", "current_pid",
        "zx48_schedule", "zx48_idle_loop", "kernel_ticks", "syscall_frame_sp", "kernel_ordinary_used_end",
    ))


def _p101(root: Path, labels: dict[str, int], kernel: bytes) -> None:
    canaries = ((0x4000, 0xA5), (0x5B00, 0x5A), (0x6000, 0x3C), (0xFF80, 0xC3))
    code = bytearray(b"\xF3" + _ld_sp(USER_STACK))
    for address, value in canaries:
        code += _ld_a(value) + _ld_mem_a(address)
    code += _call(labels["zx48_memory_init"]) + _call(labels["zx48_process_init"])
    for address, value in canaries:
        code += _ld_a_mem(address) + _check_a(value)
    code += _jp(PASS_PC)
    run_sna(root, bytes(code), patch=_kernel_patch(kernel))
    require(labels["kernel_ordinary_used_end"] - KERNEL_BASE <= 6912, "ordinary kernel code/data exceeds 6912-byte budget")


def _p102(root: Path, labels: dict[str, int], kernel: bytes) -> None:
    code = bytearray(b"\xF3" + _ld_sp(USER_STACK) + _call(labels["zx48_memory_init"]))
    code += _ld_a(0) + _ld_bc(0x0100) + _call(labels["zx48_alloc"]) + _jp_c(FAIL_PC) + _check_hl(0x6000)
    code += _ld_a(0) + _ld_bc(0x0200) + _call(labels["zx48_alloc"]) + _jp_c(FAIL_PC) + _check_hl(0x6100)
    code += _ld_hl(0x6000) + _ld_bc(0x0100) + _call(labels["zx48_free"]) + _jp_c(FAIL_PC)
    code += _ld_hl(0x6100) + _ld_bc(0x0200) + _call(labels["zx48_free"]) + _jp_c(FAIL_PC)
    code += _check_word_mem(labels["memory_free_extents"], 0x6000)
    code += _check_word_mem(labels["memory_free_extents"] + 2, 0x8000)
    code += _check_word_mem(labels["memory_live_allocations"], 0)
    code += _ld_hl(0x6100) + _ld_bc(0x0200) + _call(labels["zx48_free"]) + _jp_nc(FAIL_PC) + _check_a(1)
    code += _check_word_mem(labels["memory_free_extents"], 0x6000) + _check_word_mem(labels["memory_free_extents"] + 2, 0x8000)
    code += _jp(PASS_PC)
    run_sna(root, bytes(code), patch=_kernel_patch(kernel))


def _p103(root: Path, labels: dict[str, int], kernel: bytes) -> None:
    code = bytearray(b"\xF3" + _ld_sp(USER_STACK) + _call(labels["zx48_memory_init"]))
    code += _ld_a(1) + _ld_bc(0x6000) + _call(labels["zx48_alloc"]) + _jp_c(FAIL_PC) + _check_hl(0x8000)
    code += _ld_a(1) + _ld_bc(2) + _call(labels["zx48_alloc"]) + _jp_nc(FAIL_PC) + _check_a(3)
    code += _ld_hl(0xA000) + _call(labels["zx48_mem_info"])
    code += _check_word_mem(0xA000, 0) + _check_word_mem(0xA004, 0x2000) + _check_word_mem(0xA008, 0x2000)
    code += _jp(PASS_PC)
    run_sna(root, bytes(code), patch=_kernel_patch(kernel))


def _p104(root: Path, labels: dict[str, int], kernel: bytes) -> None:
    code = bytearray(b"\xF3" + _ld_sp(USER_STACK) + _call(labels["zx48_memory_init"]))
    code += _ld_a(0) + _ld_bc(0x3000) + _call(labels["zx48_alloc"]) + _jp_c(FAIL_PC) + _check_hl(0x6000)
    code += _ld_hl(0xA000) + _call(labels["zx48_mem_info"])
    code += _check_word_mem(0xA000, 0x5000) + _check_word_mem(0xA002, 0x5000) + _check_word_mem(0xA004, 0) + _check_word_mem(0xA008, 0x5000) + _check_word_mem(0xA00A, 1)
    code += _ld_hl(0x6000) + _ld_bc(0x3000) + _call(labels["zx48_free"]) + _jp_c(FAIL_PC)
    code += _ld_a(2) + _ld_bc(0x0100) + _call(labels["zx48_alloc"]) + _jp_c(FAIL_PC) + _check_hl(0x6000)
    code += _jp(PASS_PC)
    run_sna(root, bytes(code), patch=_kernel_patch(kernel))


def _p105(root: Path, labels: dict[str, int], kernel: bytes) -> None:
    code = bytearray(b"\xF3" + _ld_sp(USER_STACK) + _call(labels["zx48_memory_init"]) + _call(labels["zx48_process_init"]))
    code += _ld_a(0) + _ld_bc(0x3000) + _call(labels["zx48_alloc"]) + _jp_c(FAIL_PC)
    code += _ld_bc(0x0020) + _call(labels["zx48_memory_pin_bytes"])
    code += _call(labels["zx48_process_prepare_pid1"]) + _jp_c(FAIL_PC)
    code += _ld_hl(0xA000) + _call(labels["zx48_mem_info"])
    for address, value in ((0xA000, 0x5000), (0xA002, 0x5000), (0xA004, 0), (0xA006, 0), (0xA008, 0x5000), (0xA00A, 1), (0xA00C, 0x20)):
        code += _check_word_mem(address, value)
    code += _ld_a_mem(0xA00E) + _check_a(1) + _ld_a_mem(0xA00F) + _check_a(0) + _jp(PASS_PC)
    run_sna(root, bytes(code), patch=_kernel_patch(kernel))


def _p106(root: Path, labels: dict[str, int], kernel: bytes) -> None:
    table = labels["process_table"]
    code = bytearray(b"\xF3" + _ld_sp(USER_STACK) + _call(labels["zx48_process_init"]))
    for pid in range(8):
        base = table + pid * 48
        code += _ld_a_mem(base) + _check_a(pid)
        code += _ld_a_mem(base + 1) + _check_a(0xFF)
        code += _ld_a_mem(base + 2) + _check_a(2 if pid == 0 else 0)
        for handle in range(8):
            code += _ld_a_mem(base + 16 + handle) + _check_a(0xFF)
    code += _call(labels["zx48_process_prepare_pid1"]) + _jp_c(FAIL_PC)
    base = table + 48
    code += _ld_a_mem(base + 2) + _check_a(1) + _ld_a_mem(base + 1) + _check_a(0) + _ld_a_mem(base + 28) + _check_a(0)
    code += _ld_a_mem(base + 29) + _check_a(ord("s")) + _ld_a_mem(base + 30) + _check_a(ord("h"))
    code += _ld_a_mem(base + 46) + _check_a(0) + _jp(PASS_PC)
    run_sna(root, bytes(code), patch=_kernel_patch(kernel))


def _context_verifier(current_pid_addr: int, pid: int) -> bytes:
    code = bytearray()
    code += _ld_mem_a(SCRATCH)
    code += _ld_mem_hl(SCRATCH + 2)
    code += b"\xD5\xE1" + _ld_mem_hl(SCRATCH + 4)
    code += b"\xC5\xE1" + _ld_mem_hl(SCRATCH + 6)
    code += b"\xDD\xE5\xE1" + _ld_mem_hl(SCRATCH + 8)
    code += b"\xFD\xE5\xE1" + _ld_mem_hl(SCRATCH + 10)
    code += _ld_a_mem(SCRATCH) + _check_a(0x42)
    for addr, value in ((SCRATCH + 2, 0x5678), (SCRATCH + 4, 0x9ABC), (SCRATCH + 6, 0xDEF0), (SCRATCH + 8, 0x1234), (SCRATCH + 10, 0x5C3A)):
        code += _check_word_mem(addr, value)
    code += _ld_a_mem(current_pid_addr) + _check_a(pid) + _jp(PASS_PC)
    return bytes(code)


def _frame(pc: int) -> bytes:
    return b"".join(_word(v) for v in (0x1234, 0x5678, 0x9ABC, 0xDEF0, 0x4200, pc))


def _p107(root: Path, labels: dict[str, int], kernel: bytes) -> None:
    table = labels["process_table"]
    verifier = _context_verifier(labels["current_pid"], 1)
    extras = ((FRAME1, _frame(VERIFY_PC)), (VERIFY_PC, verifier))
    code = bytearray(b"\xF3" + _ld_sp(USER_STACK) + _call(labels["zx48_kernel_stack_init"]) + _call(labels["zx48_process_init"]) + _call(labels["zx48_process_prepare_pid1"]))
    code += _ld_hl(FRAME1) + _ld_mem_hl(table + 48 + 12) + _jp(labels["zx48_schedule"])
    run_sna(root, bytes(code), patch=_kernel_patch(kernel, extras))


def _p108(root: Path, labels: dict[str, int], kernel: bytes) -> None:
    patched = bytearray(kernel)
    idle = labels["zx48_idle_loop"] - KERNEL_BASE
    require(0 <= idle <= len(patched) - 3, "idle loop outside kernel")
    patched[idle:idle + 3] = _jp(PASS_PC)
    code = b"\xF3" + _ld_sp(USER_STACK) + _call(labels["zx48_kernel_stack_init"]) + _call(labels["zx48_memory_init"]) + _call(labels["zx48_process_init"]) + _jp(labels["zx48_schedule"])
    run_sna(root, code, patch=_kernel_patch(bytes(patched)))


def _p109(root: Path, labels: dict[str, int], kernel: bytes) -> None:
    code = bytearray(b"\xF3" + _ld_sp(USER_STACK) + _call(labels["zx48_kernel_stack_init"]) + _ld_a(0x09) + _call(0xE000))
    code += _jp_nc(FAIL_PC) + _check_a(14)
    code += _ld_a(0xFF) + _call(0xE000) + _jp_nc(FAIL_PC) + _check_a(14) + _jp(PASS_PC)
    run_sna(root, bytes(code), patch=_kernel_patch(kernel))


def _p110(root: Path, labels: dict[str, int], kernel: bytes) -> None:
    code = bytearray(b"\xF3" + _ld_sp(USER_STACK) + _call(labels["zx48_kernel_stack_init"]) + _ld_ix(0x1234) + _ld_iy(0x9999) + _ld_hl(0xAAAA) + _ld_de(0xBBBB) + _ld_bc(0xCCCC) + _ld_a(0) + _call(0xE000))
    code += _jp_c(FAIL_PC) + _check_a(0) + _check_hl(0x0100)
    code += b"\xDD\xE5\xE1" + _check_hl(0x1234) + b"\xFD\xE5\xE1" + _check_hl(0x5C3A) + _jp(PASS_PC)
    run_sna(root, bytes(code), patch=_kernel_patch(kernel))


def _p111(root: Path, labels: dict[str, int], kernel: bytes) -> None:
    current = labels["current_pid"]
    code = bytearray(b"\xF3" + _ld_sp(USER_STACK) + _call(labels["zx48_kernel_stack_init"]) + _call(labels["zx48_process_init"]))
    for pid in (0, 1, 7):
        code += _ld_a(pid) + _ld_mem_a(current) + _ld_a(4) + _call(0xE000) + _jp_c(FAIL_PC) + _check_a(0) + _check_hl(pid)
    code += _jp(PASS_PC)
    run_sna(root, bytes(code), patch=_kernel_patch(kernel))


def _p112(root: Path, labels: dict[str, int], kernel: bytes) -> None:
    table = labels["process_table"]
    p2 = table + 2 * 48
    verifier = bytearray()
    verifier += _ld_a_mem(labels["current_pid"]) + _check_a(2)
    verifier += _ld_a_mem(table + 2) + _check_a(1)
    verifier += _ld_a_mem(p2 + 2) + _check_a(2)
    verifier += _ld_a_mem(p2 + 46) + b"\xE6\x80" + _check_a(0x80) + _jp(PASS_PC)
    extras = ((FRAME2, _frame(VERIFY_PC)), (VERIFY_PC, bytes(verifier)))
    code = bytearray(b"\xF3" + _ld_sp(USER_STACK) + _call(labels["zx48_kernel_stack_init"]) + _call(labels["zx48_process_init"]))
    code += _ld_a(2) + _ld_mem_a(p2) + _ld_a(3) + _ld_mem_a(p2 + 2)
    code += _ld_hl(FRAME2) + _ld_mem_hl(p2 + 12)
    for off in range(4):
        code += _ld_a(0) + _ld_mem_a(p2 + 24 + off) + _ld_mem_a(labels["kernel_ticks"] + off)
    code += _jp(labels["zx48_schedule"])
    run_sna(root, bytes(code), patch=_kernel_patch(kernel, extras))

    # No user READY peer: the current RUNNING task is made READY and selected again.
    verifier2 = _ld_a_mem(labels["current_pid"]) + _check_a(1) + _ld_a_mem(table + 48 + 2) + _check_a(2) + _jp(PASS_PC)
    extras2 = ((FRAME1, _frame(VERIFY_PC)), (VERIFY_PC, verifier2))
    code2 = bytearray(b"\xF3" + _ld_sp(USER_STACK) + _call(labels["zx48_kernel_stack_init"]) + _call(labels["zx48_process_init"]) + _call(labels["zx48_process_prepare_pid1"]))
    code2 += _ld_a(1) + _ld_mem_a(labels["current_pid"]) + _ld_a(2) + _ld_mem_a(table + 48 + 2)
    code2 += _ld_hl(FRAME1) + _ld_mem_hl(labels["syscall_frame_sp"]) + _jp(labels["zx48_schedule"])
    run_sna(root, bytes(code2), patch=_kernel_patch(kernel, extras2))


def dispatch(
    root: Path,
    action: str,
    step: str,
    *,
    sha256_file: Callable[[Path], str],
    run_command: Callable[..., Any],
    require_project_tool: Callable[[Path, str | Path], Path],
):
    valid = {f"P1.{n:02d}" for n in range(1, 13)}
    if step not in valid:
        raise Phase1CoreError(f"Phase-1 core step is not registered: {step}")

    assertions = _static_contract(root, step)
    failed = [item["name"] for item in assertions if item.get("passed") is not True]
    require(not failed, f"static {step} contract failures: {failed}")

    result, kernel_path, listing = _assemble_kernel(root, run_command, require_project_tool)
    labels = _common_labels(listing)
    kernel = kernel_path.read_bytes()
    require(len(kernel) == 0x2000, "kernel image must remain exactly 8192 bytes")

    if action == "test":
        tests = {
            "P1.01": _p101, "P1.02": _p102, "P1.03": _p103, "P1.04": _p104,
            "P1.05": _p105, "P1.06": _p106, "P1.07": _p107, "P1.08": _p108,
            "P1.09": _p109, "P1.10": _p110, "P1.11": _p111, "P1.12": _p112,
        }
        tests[step](root, labels, kernel)
        assertions.append({"name": f"{step.lower().replace('.', '-')}-deterministic-emulator-revalidation", "passed": True})

    hashes = {
        "v1/build/kernel.bin": sha256_file(kernel_path),
        "v1/include/zx48ux.inc": sha256_file(root / "v1/include/zx48ux.inc"),
    }
    return [result], hashes, assertions
