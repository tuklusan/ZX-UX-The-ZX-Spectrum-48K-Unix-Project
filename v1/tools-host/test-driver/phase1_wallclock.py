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

ROM_FRAMES = 0x5C78
EPOCH = (0x80, 0x06, 0x26, 0x17)


class WallClockError(DriverError):
    """Raised when the P1.26 deterministic wall-clock contract is violated."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise WallClockError(message)


def _word(value: int) -> bytes:
    return bytes((value & 0xFF, value >> 8))


def _call(address: int) -> bytes:
    return b"\xCD" + _word(address)


def _jp(address: int) -> bytes:
    return b"\xC3" + _word(address)


def _jp_nz(address: int) -> bytes:
    return b"\xC2" + _word(address)


def _store(address: int, value: int) -> bytes:
    return bytes((0x3E, value & 0xFF, 0x32)) + _word(address)


def _expect(address: int, value: int) -> bytes:
    return b"\x3A" + _word(address) + bytes((0xFE, value & 0xFF)) + _jp_nz(FAIL_PC)


def _stores(address: int, values: tuple[int, ...]) -> bytes:
    return b"".join(_store(address + i, value) for i, value in enumerate(values))


def _expects(address: int, values: tuple[int, ...]) -> bytes:
    return b"".join(_expect(address + i, value) for i, value in enumerate(values))


def _asm(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    return "\n".join(line.split(";", 1)[0].rstrip().lower() for line in text.splitlines())


def _block(text: str, start: str, end: str) -> str:
    first = text.find(start)
    last = text.find(end, first + len(start)) if first >= 0 else -1
    return text[first:last] if 0 <= first < last else ""


def _init_ok(interrupt: str) -> bool:
    init = _block(interrupt, "zx48_wall_boot_init:", "zx48_interrupt:")
    expected = (
        "zx48_wall_boot_init:\n    di\n    ld hl,$0680\n    ld (wall_seconds),hl\n"
        "    ld hl,$1726\n    ld (wall_seconds+2),hl\n    ld hl,0\n"
        "    ld (wall_revision),hl\n    ld hl,$0100\n    ld (wall_subsecond),hl\n"
        "    jp zx48_im2_init\n"
    )
    return expected in init and not any(token in init for token in ("kernel_ticks", "sys_time_set", "rom_frames"))


def _contracts(root: Path) -> list[dict[str, object]]:
    interrupt = _asm(root / "v1/src/kernel/interrupt.asm")
    syscall = _asm(root / "v1/src/kernel/syscall.asm")
    boot = _asm(root / "v1/src/boot/entry.asm")
    architecture = " ".join((root / "docs/01-ZX-UX-ARCHITECTURE-REV12.md").read_text(encoding="utf-8").lower().split())
    wall = _block(interrupt, "zx48_interrupt_wall:", "zx48_interrupt_break:")
    time_get = _block(syscall, "zx48_sys_time_get:", "zx48_time_set_handler:")
    boot_impl = _block(boot, "zx48_boot_main_impl:", "    endm")
    assertions = [
        {"name": "cold-init-exact", "passed": _init_ok(interrupt)},
        {"name": "boot-calls-cold-init", "passed": "call zx48_wall_boot_init" in boot_impl and "call zx48_im2_init" not in boot_impl},
        {"name": "wall-layout-contiguous", "passed": all(token in interrupt for token in (
            "wall_seconds              equ interrupt_state_base+7",
            "wall_revision             equ interrupt_state_base+11",
            "wall_subsecond            equ interrupt_state_base+13",
            "wall_valid                equ interrupt_state_base+14",
        ))},
        {"name": "frame50-rollover", "passed": all(token in wall for token in (
            "ld a,(wall_valid)", "ld a,(wall_subsecond)", "cp zx48_pal_frame_hz",
            "ld (wall_subsecond),a", "ld hl,(wall_seconds)", "inc hl", "ld (wall_seconds),hl",
        ))},
        {"name": "time1-atomic-six-byte-copy", "passed": all(token in time_get for token in (
            "di", "ld de,(syscall_arg_hl)", "ld hl,wall_seconds", "ld bc,6", "ldir", "ei",
        )) and "syscall_time_revision" not in time_get},
        {"name": "architecture-epoch-decimal", "passed": "wall_seconds decimal 388368000" in architecture},
        {"name": "architecture-epoch-hex", "passed": "wall_seconds hex 0x17260680" in architecture},
        {"name": "architecture-time1-bytes", "passed": "time1 bytes 80 06 26 17 00 00" in architecture},
        {"name": "architecture-revision-zero", "passed": "revision 0 subsecond_frames 0 valid true" in architecture},
        {"name": "architecture-pal-50hz-clock", "passed": "clock advances one second per 50 accepted im2 frames" in architecture},
        {"name": "architecture-no-external-clock", "passed": "not recovered from any rtc, host, emulator, tape, basic, filesystem, or network clock" in architecture},
    ]
    assertions.extend((
        {"name": "reject-wrong-epoch", "passed": not _init_ok(interrupt.replace("ld hl,$0680", "ld hl,$0681", 1))},
        {"name": "reject-tick-coupling", "passed": not _init_ok(interrupt.replace("    ld hl,$1726\n", "    ld (kernel_ticks),hl\n    ld hl,$1726\n", 1))},
        {"name": "reject-sys-time-set-seed", "passed": not _init_ok(interrupt.replace("    di\n", "    call zx48_sys_time_set\n", 1))},
    ))
    return assertions


def _patch(kernel: bytes):
    def apply(ram: bytearray) -> None:
        start = phase1.KERNEL_BASE - 0x4000
        ram[start:start + len(kernel)] = kernel
    return apply


def _runtime(root: Path, labels: dict[str, int], kernel: bytes) -> None:
    init = labels["zx48_wall_boot_init"]
    work = labels["zx48_interrupt_work"]
    ticks = labels["kernel_ticks"]
    seconds = labels["wall_seconds"]
    revision = labels["wall_revision"]
    subsecond = labels["wall_subsecond"]
    valid = labels["wall_valid"]

    code = bytearray(b"\xF3" + phase1._ld_sp(phase1.USER_STACK))
    code += _stores(ticks, (0x78, 0x56, 0x34, 0x12)) + _call(init)
    code += _expects(seconds, EPOCH) + _expects(revision, (0, 0)) + _expect(subsecond, 0) + _expect(valid, 1)
    code += _expects(ticks, (0x78, 0x56, 0x34, 0x12))
    code += _stores(seconds, (0xFF, 0xEE, 0xDD, 0xCC)) + _stores(revision, (7, 9))
    code += _store(subsecond, 31) + _store(valid, 0) + _call(init)
    code += _expects(seconds, EPOCH) + _expects(revision, (0, 0)) + _expect(subsecond, 0) + _expect(valid, 1)
    code += _expects(ticks, (0x78, 0x56, 0x34, 0x12)) + _jp(PASS_PC)
    run_sna(root, bytes(code), patch=_patch(kernel))

    code = bytearray(b"\xF3" + phase1._ld_sp(phase1.USER_STACK) + _call(init))
    code += _stores(ticks, (0, 0, 0, 0)) + _stores(ROM_FRAMES, (0, 0, 0))
    for _ in range(49):
        code += _call(work)
    code += _expects(seconds, EPOCH) + _expect(subsecond, 49) + _expects(ticks, (49, 0, 0, 0))
    code += _call(work) + _expects(seconds, (0x81, 0x06, 0x26, 0x17)) + _expect(subsecond, 0)
    code += _expects(revision, (0, 0)) + _expects(ticks, (50, 0, 0, 0)) + _jp(PASS_PC)
    run_sna(root, bytes(code), patch=_patch(kernel))

    code = bytearray(b"\xF3" + phase1._ld_sp(phase1.USER_STACK))
    code += _stores(seconds, (0x44, 0x33, 0x22, 0x11)) + _stores(revision, (5, 0))
    code += _store(subsecond, 49) + _store(valid, 0) + _call(work)
    code += _expects(seconds, (0x44, 0x33, 0x22, 0x11)) + _expects(revision, (5, 0)) + _expect(subsecond, 49) + _expect(valid, 0)
    code += _jp(PASS_PC)
    run_sna(root, bytes(code), patch=_patch(kernel))

    patched = bytearray(kernel)
    offset = init - phase1.KERNEL_BASE
    require(patched[offset:offset + 4] == b"\xF3\x21\x80\x06", "unexpected cold-init encoding")
    patched[offset + 2] = 0x81
    code = bytearray(b"\xF3" + phase1._ld_sp(phase1.USER_STACK) + _call(init))
    code += b"\x3A" + _word(seconds) + b"\xFE\x80" + _jp_nz(PASS_PC) + _jp(FAIL_PC)
    run_sna(root, bytes(code), patch=_patch(bytes(patched)))


def dispatch(root: Path, action: str, step: str, *, sha256_file: Callable[[Path], str], run_command: Callable[..., Any], require_project_tool: Callable[[Path, str | Path], Path]):
    if step != "P1.26":
        raise WallClockError(f"software wall-clock step is not registered: {step}")
    assertions = _contracts(root)
    failed = [item["name"] for item in assertions if item["passed"] is not True]
    require(not failed, f"static P1.26 failures: {failed}")
    command, kernel_path, listing = phase1._assemble_kernel(root, run_command, require_project_tool)
    labels = phase1._labels(listing, (
        "zx48_wall_boot_init", "zx48_interrupt_work", "kernel_ticks", "wall_seconds",
        "wall_revision", "wall_subsecond", "wall_valid", "kernel_ordinary_used_end",
    ))
    used_end = labels["kernel_ordinary_used_end"]
    assertions.append({"name": "ordinary-code-pool-within-faff", "passed": used_end <= 0xFB00, "used_end": f"0x{used_end:04X}", "free_bytes": 0xFB00 - used_end})
    require(used_end <= 0xFB00, f"ordinary kernel code overflow: end=0x{used_end:04X}")
    kernel = kernel_path.read_bytes()
    if action == "test":
        _runtime(root, labels, kernel)
        assertions.extend((
            {"name": "runtime-cold-epoch-and-independent-ticks", "passed": True},
            {"name": "runtime-frame50-rollover", "passed": True},
            {"name": "runtime-invalid-state-preserved", "passed": True},
            {"name": "runtime-wrong-epoch-negative-sensitive", "passed": True},
        ))
    paths = (
        root / "docs/01-ZX-UX-ARCHITECTURE-REV12.md",
        root / "v1/src/boot/entry.asm",
        root / "v1/src/kernel/interrupt.asm",
        root / "v1/src/kernel/syscall.asm",
        root / "v1/tools-host/test-driver/phase1_wallclock.py",
        kernel_path,
    )
    return [command], {str(path.relative_to(root)): sha256_file(path) for path in paths}, assertions
