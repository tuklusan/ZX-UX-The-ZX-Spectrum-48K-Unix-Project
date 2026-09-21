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

SYS_TIME_GET = 0x63
SYS_TIME_SET = 0x64
E_INVAL = 0x01
E_PERM = 0x07
E_AGAIN = 0x0D
TIME_BUFFER = 0xA100
TIME_INPUT = 0xA120
EPOCH_TIME1 = (0x80, 0x06, 0x26, 0x17, 0x00, 0x00)
MAX_2099_SECONDS = (0xFF, 0x56, 0x86, 0xF4)
FIRST_2100_SECONDS = (0x00, 0x57, 0x86, 0xF4)


class TimeAbiError(DriverError):
    """Raised when the P1.27 TIME1 syscall contract is violated."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise TimeAbiError(message)


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


def _store(address: int, value: int) -> bytes:
    return bytes((0x3E, value & 0xFF, 0x32)) + _word(address)


def _expect(address: int, value: int) -> bytes:
    return b"\x3A" + _word(address) + bytes((0xFE, value & 0xFF)) + _jp_nz(FAIL_PC)


def _stores(address: int, values: tuple[int, ...]) -> bytes:
    return b"".join(_store(address + offset, value) for offset, value in enumerate(values))


def _expects(address: int, values: tuple[int, ...]) -> bytes:
    return b"".join(_expect(address + offset, value) for offset, value in enumerate(values))


def _syscall(number: int, pointer: int) -> bytes:
    return phase1._ld_hl(pointer) + bytes((0x3E, number)) + _call(0xE000)


def _expect_success() -> bytes:
    return _jp_c(FAIL_PC) + b"\xB7" + _jp_nz(FAIL_PC)


def _expect_error(error: int) -> bytes:
    return _jp_nc(FAIL_PC) + bytes((0xFE, error)) + _jp_nz(FAIL_PC)


def _asm(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    return "\n".join(line.split(";", 1)[0].rstrip().lower() for line in text.splitlines())


def _block(text: str, start: str, end: str) -> str:
    first = text.find(start)
    last = text.find(end, first + len(start)) if first >= 0 else -1
    return text[first:last] if 0 <= first < last else ""


def _ordered(text: str, tokens: tuple[str, ...]) -> bool:
    cursor = 0
    for token in tokens:
        position = text.find(token, cursor)
        if position < 0:
            return False
        cursor = position + len(token)
    return True


def _time_get_ok(syscall: str) -> bool:
    block = _block(syscall, "zx48_sys_time_get:", "zx48_sys_time_set:")
    return _ordered(block, (
        "ld hl,(syscall_arg_hl)",
        "ld bc,6",
        "call zx48_user_range_validate",
        "ret c",
        "ld a,(wall_valid)",
        "or a",
        "jp z,zx48_sys_again",
        "di",
        "ld de,(syscall_arg_hl)",
        "ld hl,wall_seconds",
        "ld bc,6",
        "ldir",
        "ei",
        "ld hl,(syscall_arg_hl)",
        "xor a",
        "ret",
    )) and not any(token in block for token in ("kernel_ticks", "rom_frames", "timezone"))


def _time_set_ok(syscall: str) -> bool:
    block = _block(syscall, "zx48_sys_time_set:", "emit_user_range_validation_routine")
    precommit = _block(block, "zx48_sys_time_set:", "zx48_sys_time_valid:")
    commit = block[block.find("zx48_sys_time_valid:"):] if "zx48_sys_time_valid:" in block else ""
    return (
        _ordered(precommit, (
            "ld a,(current_pid)",
            "cp 1",
            "jp nz,zx48_sys_perm",
            "ld hl,(syscall_arg_hl)",
            "ld bc,4",
            "call zx48_user_range_validate",
            "ret c",
            "ld hl,(syscall_arg_hl)",
            "ld (syscall_tick_lo),de",
            "ld (syscall_tick_hi),de",
            "ld hl,(syscall_tick_hi)",
            "ld de,$f486",
            "sbc hl,de",
            "jr c,zx48_sys_time_valid",
            "jr nz,zx48_sys_invalid",
            "ld hl,(syscall_tick_lo)",
            "ld de,$5700",
            "sbc hl,de",
            "jr nc,zx48_sys_invalid",
        ))
        and not any(token in precommit for token in ("ld (wall_seconds)", "ld (wall_revision)", "ld (wall_subsecond)", "ld (wall_valid)"))
        and _ordered(commit, (
            "zx48_sys_time_valid:",
            "di",
            "ld de,(syscall_tick_lo)",
            "ld (wall_seconds),de",
            "ld de,(syscall_tick_hi)",
            "ld (wall_seconds+2),de",
            "ld hl,(wall_revision)",
            "inc hl",
            "ld (wall_revision),hl",
            "xor a",
            "ld (wall_subsecond),a",
            "inc a",
            "ld (wall_valid),a",
            "ei",
            "jp zx48_sys_zero_result",
        ))
        and not any(token in block for token in ("rom_frames", "timezone"))
    )


def _contracts(root: Path) -> list[dict[str, object]]:
    syscall = _asm(root / "v1/src/kernel/syscall.asm")
    interrupt = _asm(root / "v1/src/kernel/interrupt.asm")
    include = _asm(root / "v1/include/zx48ux.inc")
    abi = " ".join((root / "v1/docs/abi.md").read_text(encoding="utf-8").lower().replace("`", "").split())
    time_get = _time_get_ok(syscall)
    time_set = _time_set_ok(syscall)
    info_table = _block(syscall, "zx48_sys_info_table:", "emit_spawn_preflight_routines")
    assertions = [
        {"name": "canonical-time-syscall-numbers", "passed": "sys_time_get             equ $63" in include and "sys_time_set             equ $64" in include},
        {"name": "canonical-time-error-numbers", "passed": "e_inval                  equ $01" in include and "e_perm                   equ $07" in include and "e_again                  equ $0d" in include},
        {"name": "time-get-exact-six-byte-atomic-copy", "passed": time_get},
        {"name": "time-set-pid1-permission-range-and-atomic-commit", "passed": time_set},
        {"name": "time-info-dispatch-order", "passed": "dw zx48_sys_mem_info,zx48_sys_proc_info,zx48_sys_ticks,zx48_sys_time_get,zx48_sys_time_set" in info_table},
        {"name": "time-state-layout-is-time1-prefix", "passed": all(token in interrupt for token in (
            "wall_seconds              equ interrupt_state_base+7",
            "wall_revision             equ interrupt_state_base+11",
            "wall_subsecond            equ interrupt_state_base+13",
            "wall_valid                equ interrupt_state_base+14",
        ))},
        {"name": "abi-doc-time1-layout", "passed": "time1 is exactly six little-endian bytes: u32 seconds followed by u16 revision" in abi},
        {"name": "abi-doc-get-invalid-policy", "passed": "sys_time_get takes hl as a writable six-byte time1 pointer" in abi and "returns e_again only while the explicit wall-valid state is false" in abi},
        {"name": "abi-doc-set-permission-and-range", "passed": "sys_time_set is restricted to pid1" in abi and "1970 through 2099" in abi},
        {"name": "abi-doc-revision-and-subsecond", "passed": "increments revision modulo 65536 even when the seconds value is unchanged" in abi and "resets the private subsecond frame counter to zero" in abi},
        {"name": "reject-missing-revision-increment", "passed": not _time_set_ok(syscall.replace("    inc hl\n    ld (wall_revision),hl", "    ld (wall_revision),hl", 1))},
        {"name": "reject-nonatomic-prevalidation-write", "passed": not _time_set_ok(syscall.replace("zx48_sys_time_set:\n    ld a,(current_pid)", "zx48_sys_time_set:\n    ld (wall_valid),a\n    ld a,(current_pid)", 1))},
        {"name": "reject-wrong-2100-boundary", "passed": not _time_set_ok(syscall.replace("ld de,$5700", "ld de,$5701", 1))},
    ]
    return assertions


def _patch(kernel: bytes):
    def apply(ram: bytearray) -> None:
        start = phase1.KERNEL_BASE - 0x4000
        ram[start:start + len(kernel)] = kernel
    return apply


def _fixture_prefix(stack_init: int, wall_init: int) -> bytearray:
    return bytearray(b"\xF3" + phase1._ld_sp(phase1.USER_STACK) + _call(stack_init) + _call(wall_init))


def _runtime_get(root: Path, labels: dict[str, int], kernel: bytes) -> None:
    code = _fixture_prefix(labels["zx48_kernel_stack_init"], labels["zx48_wall_boot_init"])
    code += _stores(TIME_BUFFER, (0xCC,) * 6)
    code += _syscall(SYS_TIME_GET, TIME_BUFFER) + _expect_success()
    code += _expects(TIME_BUFFER, EPOCH_TIME1)
    code += _store(labels["wall_valid"], 0) + _stores(TIME_BUFFER, (0xA5,) * 6)
    code += _syscall(SYS_TIME_GET, TIME_BUFFER) + _expect_error(E_AGAIN)
    code += _expects(TIME_BUFFER, (0xA5,) * 6) + _jp(PASS_PC)
    run_sna(root, bytes(code), patch=_patch(kernel))


def _runtime_set_revision(root: Path, labels: dict[str, int], kernel: bytes) -> None:
    code = _fixture_prefix(labels["zx48_kernel_stack_init"], labels["zx48_wall_boot_init"])
    code += _store(labels["current_pid"], 1) + _stores(TIME_INPUT, EPOCH_TIME1[:4])
    code += _store(labels["wall_subsecond"], 49)
    code += _syscall(SYS_TIME_SET, TIME_INPUT) + _expect_success()
    code += _expects(labels["wall_seconds"], EPOCH_TIME1[:4])
    code += _expects(labels["wall_revision"], (1, 0)) + _expect(labels["wall_subsecond"], 0) + _expect(labels["wall_valid"], 1)
    code += _store(labels["wall_subsecond"], 49)
    code += _syscall(SYS_TIME_SET, TIME_INPUT) + _expect_success()
    code += _expects(labels["wall_revision"], (2, 0)) + _expect(labels["wall_subsecond"], 0)
    code += _syscall(SYS_TIME_GET, TIME_BUFFER) + _expect_success()
    code += _expects(TIME_BUFFER, EPOCH_TIME1[:4] + (2, 0))
    code += _stores(labels["wall_revision"], (0xFF, 0xFF)) + _store(labels["wall_subsecond"], 49)
    code += _syscall(SYS_TIME_SET, TIME_INPUT) + _expect_success()
    code += _expects(labels["wall_revision"], (0, 0)) + _expect(labels["wall_subsecond"], 0)
    code += _jp(PASS_PC)
    run_sna(root, bytes(code), patch=_patch(kernel))


def _runtime_boundaries(root: Path, labels: dict[str, int], kernel: bytes) -> None:
    code = _fixture_prefix(labels["zx48_kernel_stack_init"], labels["zx48_wall_boot_init"])
    code += _store(labels["current_pid"], 1) + _stores(TIME_INPUT, (0, 0, 0, 0))
    code += _syscall(SYS_TIME_SET, TIME_INPUT) + _expect_success()
    code += _expects(labels["wall_seconds"], (0, 0, 0, 0)) + _expects(labels["wall_revision"], (1, 0))
    code += _stores(TIME_INPUT, MAX_2099_SECONDS)
    code += _syscall(SYS_TIME_SET, TIME_INPUT) + _expect_success()
    code += _expects(labels["wall_seconds"], MAX_2099_SECONDS) + _expects(labels["wall_revision"], (2, 0))
    code += _store(labels["wall_subsecond"], 17) + _stores(TIME_INPUT, FIRST_2100_SECONDS)
    code += _syscall(SYS_TIME_SET, TIME_INPUT) + _expect_error(E_INVAL)
    code += _expects(labels["wall_seconds"], MAX_2099_SECONDS) + _expects(labels["wall_revision"], (2, 0))
    code += _expect(labels["wall_subsecond"], 17) + _expect(labels["wall_valid"], 1)
    code += _store(labels["wall_subsecond"], 18) + _stores(TIME_INPUT, (0xFF, 0xFF, 0xFF, 0xFF))
    code += _syscall(SYS_TIME_SET, TIME_INPUT) + _expect_error(E_INVAL)
    code += _expects(labels["wall_seconds"], MAX_2099_SECONDS) + _expects(labels["wall_revision"], (2, 0))
    code += _expect(labels["wall_subsecond"], 18) + _expect(labels["wall_valid"], 1) + _jp(PASS_PC)
    run_sna(root, bytes(code), patch=_patch(kernel))


def _runtime_permission_and_pointer(root: Path, labels: dict[str, int], kernel: bytes) -> None:
    code = _fixture_prefix(labels["zx48_kernel_stack_init"], labels["zx48_wall_boot_init"])
    code += _stores(TIME_INPUT, (0, 0, 0, 0))
    code += _store(labels["current_pid"], 2) + _store(labels["wall_subsecond"], 23)
    code += _syscall(SYS_TIME_SET, TIME_INPUT) + _expect_error(E_PERM)
    code += _expects(labels["wall_seconds"], EPOCH_TIME1[:4]) + _expects(labels["wall_revision"], (0, 0))
    code += _expect(labels["wall_subsecond"], 23) + _expect(labels["wall_valid"], 1)
    code += _store(labels["current_pid"], 1) + _store(labels["wall_subsecond"], 24)
    code += _syscall(SYS_TIME_SET, 0xE000) + _expect_error(E_INVAL)
    code += _expects(labels["wall_seconds"], EPOCH_TIME1[:4]) + _expects(labels["wall_revision"], (0, 0))
    code += _expect(labels["wall_subsecond"], 24) + _expect(labels["wall_valid"], 1) + _jp(PASS_PC)
    run_sna(root, bytes(code), patch=_patch(kernel))


def dispatch(
    root: Path,
    action: str,
    step: str,
    *,
    sha256_file: Callable[[Path], str],
    run_command: Callable[..., Any],
    require_project_tool: Callable[[Path, str | Path], Path],
):
    if step != "P1.27":
        raise TimeAbiError(f"TIME1 syscall step is not registered: {step}")

    assertions = _contracts(root)
    failed = [item["name"] for item in assertions if item["passed"] is not True]
    require(not failed, f"static P1.27 failures: {failed}")

    command, kernel_path, listing = phase1._assemble_kernel(root, run_command, require_project_tool)
    labels = phase1._labels(listing, (
        "zx48_kernel_stack_init",
        "zx48_wall_boot_init",
        "current_pid",
        "wall_seconds",
        "wall_revision",
        "wall_subsecond",
        "wall_valid",
        "kernel_ordinary_used_end",
    ))
    used_end = labels["kernel_ordinary_used_end"]
    assertions.append({
        "name": "ordinary-code-pool-within-faff",
        "passed": used_end <= 0xFB00,
        "used_end": f"0x{used_end:04X}",
        "free_bytes": 0xFB00 - used_end,
    })
    require(used_end <= 0xFB00, f"ordinary kernel code overflow: end=0x{used_end:04X}")

    kernel = kernel_path.read_bytes()
    if action == "test":
        _runtime_get(root, labels, kernel)
        _runtime_set_revision(root, labels, kernel)
        _runtime_boundaries(root, labels, kernel)
        _runtime_permission_and_pointer(root, labels, kernel)
        assertions.extend((
            {"name": "runtime-boot-get-and-invalid-eagain", "passed": True},
            {"name": "runtime-set-repeat-and-revision-wrap", "passed": True},
            {"name": "runtime-1970-2099-boundaries-atomic", "passed": True},
            {"name": "runtime-pid1-permission-and-pointer-validation", "passed": True},
        ))

    paths = (
        root / "v1/docs/abi.md",
        root / "v1/include/zx48ux.inc",
        root / "v1/src/kernel/interrupt.asm",
        root / "v1/src/kernel/syscall.asm",
        root / "v1/tools-host/test-driver/phase1_time.py",
        kernel_path,
    )
    return [command], {str(path.relative_to(root)): sha256_file(path) for path in paths}, assertions
