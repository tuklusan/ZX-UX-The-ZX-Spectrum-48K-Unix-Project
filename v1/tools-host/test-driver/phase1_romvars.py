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
import phase1

ROM_FRAMES = 0x5C78
ROM_UDG = 0x5C7B
UDG_BANK_BASE = 0x6000
UDG_BANK_SIZE = 0x0100
UDG_BANK_END = UDG_BANK_BASE + UDG_BANK_SIZE - 1
FIRST_FREE_AFTER_UDG = UDG_BANK_END + 1
FIRST_FREE_LENGTH_AFTER_UDG = 0x7F00
PROC_DESC_SIZE = 0x30
PROC_STATE = 2
PROC_FREE = 0


class Phase1RomVarsError(DriverError):
    """Raised when the P1.14 ROM-FRAMES/UDG compatibility contract is violated."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Phase1RomVarsError(message)


def _word(value: int) -> bytes:
    return bytes((value & 0xFF, (value >> 8) & 0xFF))


def _call(address: int) -> bytes:
    return b"\xCD" + _word(address)


def _jp(address: int) -> bytes:
    return b"\xC3" + _word(address)


def _jp_c(address: int) -> bytes:
    return b"\xDA" + _word(address)


def _jp_nz(address: int) -> bytes:
    return b"\xC2" + _word(address)


def _store_byte(address: int, value: int) -> bytes:
    return bytes((0x3E, value & 0xFF, 0x32)) + _word(address)


def _expect_byte(address: int, value: int) -> bytes:
    return b"\x3A" + _word(address) + bytes((0xFE, value & 0xFF)) + _jp_nz(FAIL_PC)


def _store_bytes(address: int, values: tuple[int, ...]) -> bytes:
    return b"".join(_store_byte(address + offset, value) for offset, value in enumerate(values))


def _expect_bytes(address: int, values: tuple[int, ...]) -> bytes:
    return b"".join(_expect_byte(address + offset, value) for offset, value in enumerate(values))


def _expect_word(address: int, value: int) -> bytes:
    return _expect_bytes(address, (value & 0xFF, (value >> 8) & 0xFF))


def _strip_asm(text: str) -> str:
    return "\n".join(line.split(";", 1)[0].rstrip().lower() for line in text.splitlines())


def _block(text: str, start: str, end: str) -> str:
    lower = text.lower()
    first = lower.find(start.lower())
    last = lower.find(end.lower(), first + len(start))
    require(0 <= first < last, f"source block missing: {start}..{end}")
    return lower[first:last]


def _ordered_tokens(text: str, tokens: tuple[str, ...]) -> bool:
    cursor = 0
    for token in tokens:
        position = text.find(token, cursor)
        if position < 0:
            return False
        cursor = position + len(token)
    return True


def _frames_contract(interrupt: str) -> bool:
    work = _block(_strip_asm(interrupt), "zx48_interrupt_work:", "    endm")
    exact = (
        "zx48_interrupt_frames:\n"
        "    ld hl,rom_frames\n"
        "    inc (hl)\n"
        "    jr nz,zx48_interrupt_timers\n"
        "    inc hl\n"
        "    inc (hl)\n"
        "    jr nz,zx48_interrupt_timers\n"
        "    inc hl\n"
        "    inc (hl)\n"
        "zx48_interrupt_timers:"
    )
    return exact in work


def _udg_contract(udg: str) -> bool:
    lowered = _strip_asm(udg)
    body = _block(lowered, "zx48_udg_init:", "zx48_udg_slot_ptr:")
    return _ordered_tokens(
        body,
        (
            "ld bc,udg_bank_size",
            "ld a,alloc_cold_preferred",
            "call zx48_alloc",
            "ret c",
            "ld (udg_bank_ptr),hl",
            "push hl",
            "xor a",
            "ld (hl),a",
            "ld d,h",
            "ld e,l",
            "inc de",
            "ld bc,udg_bank_size-1",
            "ldir",
            "pop hl",
            "ld (rom_udg),hl",
            "ld bc,udg_bank_size",
            "call zx48_memory_pin_bytes",
            "xor a",
            "ret",
        ),
    ) and all(
        (
            "call zx48_free" not in lowered,
            lowered.count("call zx48_alloc") == 1,
            len(re.findall(r"(?m)^\s*ld\s+\(udg_bank_ptr\),", lowered)) == 1,
            lowered.count("ld (rom_udg),hl") == 1,
            len(re.findall(r"(?m)^\s*ld\s+\(rom_udg\),", lowered)) == 1,
            "kernel_start" not in body,
        )
    )


def _boot_contract(boot: str) -> bool:
    body = _block(_strip_asm(boot), "zx48_boot_main_impl:", "    endm")
    udg_position = body.find("call zx48_udg_init")
    pre_udg = body[:udg_position] if udg_position >= 0 else body
    im2_entry = (
        "call zx48_wall_boot_init"
        if "call zx48_wall_boot_init" in body
        else "call zx48_im2_init"
    )
    return _ordered_tokens(
        body,
        (
            "call zx48_memory_init",
            "call zx48_process_init",
            "call zx48_handles_init",
            "call zx48_pipe_init",
            "call zx48_ula_init",
            "call zx48_console_init",
            "call zx48_keyboard_init",
            "call zx48_udg_init",
            "jp nc,zx48_boot_udg_ok",
            "ld a,panic_allocator",
            "jp zx48_panic",
            "zx48_boot_udg_ok:",
            im2_entry,
            "jp zx48_idle_loop",
        ),
    ) and "proc_ready" not in pre_udg and "zx48_spawn" not in pre_udg


def _load_pre_udg_sources(root: Path) -> dict[str, str]:
    return {
        name: (root / path).read_text(encoding="utf-8")
        for name, path in (
            ("errors", "v1/src/kernel/errors.asm"),
            ("memory", "v1/src/kernel/memory.asm"),
            ("process", "v1/src/kernel/process.asm"),
            ("handles", "v1/src/kernel/handles.asm"),
            ("pipe", "v1/src/kernel/pipe.asm"),
            ("ula", "v1/src/kernel/ula_io.asm"),
            ("console", "v1/src/kernel/console.asm"),
            ("keyboard", "v1/src/kernel/keyboard.asm"),
        )
    }


def _pre_udg_initializers_have_no_calls(sources: dict[str, str]) -> bool:
    blocks = (
        ("errors", "zx48_kernel_stack_init:", "zx48_kernel_stack_check:"),
        ("memory", "zx48_memory_init:", "zx48_alloc:"),
        ("process", "zx48_process_init:", "zx48_process_ptr:"),
        ("handles", "zx48_handles_init:", "zx48_od_ptr:"),
        ("pipe", "zx48_pipe_init:", "zx48_pipe_ptr:"),
        ("ula", "zx48_ula_init:", "zx48_ula_set_border:"),
        ("console", "zx48_console_init:", "zx48_console_clear:"),
        ("keyboard", "zx48_keyboard_init:", "zx48_keyboard_decode:"),
    )
    return all(
        "call " not in _block(_strip_asm(sources[name]), start, end)
        for name, start, end in blocks
    )


def _constants_contract(include: str) -> bool:
    lowered = _strip_asm(include)
    required = (
        ("rom_frames", "5c78"),
        ("rom_udg", "5c7b"),
        ("cold_start", "6000"),
        ("fast_start", "8000"),
        ("kernel_start", "e000"),
        ("alloc_cold_preferred", "02"),
        ("udg_bank_size", "0100"),
    )
    return all(
        re.search(rf"(?m)^\s*{name}\s+equ\s+\${value}\s*$", lowered) is not None
        for name, value in required
    )


def _process_layout_contract(process: str, include: str) -> bool:
    process_lower = _strip_asm(process)
    include_lower = _strip_asm(include)
    return (
        re.search(r"(?m)^\s*proc_state\s+equ\s+2\s*$", process_lower) is not None
        and re.search(r"(?m)^\s*proc_desc_size\s+equ\s+\$30\s*$", include_lower) is not None
        and re.search(r"(?m)^\s*proc_free\s+equ\s+\$00\s*$", include_lower) is not None
    )


def _docs_contract(documentation: str) -> bool:
    normalized = documentation.lower()
    return all(
        token in normalized
        for token in (
            "exact p1.14 runtime pointer is `0x6000`",
            "`0x6000..0x60ff`",
            "bytes `00 60`",
            "before im2 is enabled",
        )
    )


def _source_contract(root: Path) -> list[dict[str, object]]:
    interrupt = (root / "v1/src/kernel/interrupt.asm").read_text(encoding="utf-8")
    boot = (root / "v1/src/boot/entry.asm").read_text(encoding="utf-8")
    udg = (root / "v1/src/kernel/udg.asm").read_text(encoding="utf-8")
    include = (root / "v1/include/zx48ux.inc").read_text(encoding="utf-8")
    process = (root / "v1/src/kernel/process.asm").read_text(encoding="utf-8")
    pre_udg_sources = _load_pre_udg_sources(root)
    documentation = (root / "v1/docs/rom-services.md").read_text(encoding="utf-8")
    return [
        {"name": "rom-frames-three-byte-carry-chain-is-exact", "passed": _frames_contract(interrupt)},
        {"name": "udg-bank-bootstrap-is-exact-and-pinned", "passed": _udg_contract(udg)},
        {"name": "boot-orders-udg-before-im2-and-normal-idle", "passed": _boot_contract(boot)},
        {
            "name": "pre-udg-boot-initializers-make-no-service-calls",
            "passed": _pre_udg_initializers_have_no_calls(pre_udg_sources),
        },
        {"name": "rom-variable-and-arena-constants-are-frozen", "passed": _constants_contract(include)},
        {"name": "pid1-ready-probe-layout-is-frozen", "passed": _process_layout_contract(process, include)},
        {"name": "rom-services-records-exact-p1.14-udg-pointer", "passed": _docs_contract(documentation)},
    ]


def _negative_contract_tests(root: Path) -> list[dict[str, object]]:
    interrupt = (root / "v1/src/kernel/interrupt.asm").read_text(encoding="utf-8")
    boot = (root / "v1/src/boot/entry.asm").read_text(encoding="utf-8")
    udg = (root / "v1/src/kernel/udg.asm").read_text(encoding="utf-8")
    pre_udg_sources = _load_pre_udg_sources(root)

    skipped_carry = interrupt.replace(
        "    jr nz,zx48_interrupt_timers\n    inc hl\n    inc (hl)",
        "    jr zx48_interrupt_timers\n    inc hl\n    inc (hl)",
        1,
    )
    inherited_udg = udg.replace("    ld (ROM_UDG),hl\n", "", 1)
    wrong_policy = udg.replace("    ld a,ALLOC_COLD_PREFERRED", "    ld a,ALLOC_FAST_REQUIRED", 1)
    high_kernel_udg = udg.replace(
        "    ld (ROM_UDG),hl\n",
        "    ld hl,KERNEL_START\n    ld (ROM_UDG),hl\n",
        1,
    )
    freed_bank = udg.replace(
        "    call zx48_memory_pin_bytes\n",
        "    call zx48_memory_pin_bytes\n    call zx48_free\n",
        1,
    )
    moved_bank = udg.replace(
        "zx48_udg_slot_ptr:\n",
        "zx48_udg_slot_ptr:\n    ld (udg_bank_ptr),de\n    ld (ROM_UDG),de\n",
        1,
    )
    after_pid1 = boot.replace(
        "    call zx48_udg_init\n",
        "    ld a,PROC_READY\n    ld (process_table+PROC_DESC_SIZE+PROC_STATE),a\n    call zx48_udg_init\n",
        1,
    )
    pre_udg_rom_call = dict(pre_udg_sources)
    pre_udg_rom_call["keyboard"] = pre_udg_rom_call["keyboard"].replace(
        "zx48_keyboard_init:\n",
        "zx48_keyboard_init:\n    call zx48_rom_key_scan\n",
        1,
    )
    return [
        {"name": "reject-skipped-rom-frames-carry", "passed": not _frames_contract(skipped_carry)},
        {"name": "reject-inherited-rom-udg-pointer", "passed": not _udg_contract(inherited_udg)},
        {"name": "reject-noncold-udg-allocation", "passed": not _udg_contract(wrong_policy)},
        {"name": "reject-high-kernel-udg-pointer", "passed": not _udg_contract(high_kernel_udg)},
        {"name": "reject-udg-free-attempt", "passed": not _udg_contract(freed_bank)},
        {"name": "reject-udg-move-attempt", "passed": not _udg_contract(moved_bank)},
        {"name": "reject-udg-allocation-after-pid1-ready", "passed": not _boot_contract(after_pid1)},
        {
            "name": "reject-normal-rom-service-before-udg-bootstrap",
            "passed": not _pre_udg_initializers_have_no_calls(pre_udg_rom_call),
        },
    ]


def _frames_runtime(root: Path, labels: dict[str, int], kernel_bytes: bytes) -> None:
    stack_init = labels["zx48_kernel_stack_init"]
    im2_init = labels["zx48_im2_init"]
    kernel_ticks = labels["kernel_ticks"]
    wall_valid = labels["wall_valid"]
    scheduler_tick_due = labels["scheduler_tick_due"]
    cursor_blink_divider = labels["cursor_blink_divider"]
    cursor_service_parity = labels["cursor_service_parity"]
    break_pending = labels["break_pending"]
    altreg_busy = labels["altreg_busy"]

    code = bytearray(b"\xF3" + phase1._ld_sp(phase1.USER_STACK))
    code += _call(stack_init) + _call(im2_init)
    code += _store_bytes(kernel_ticks, (0xFF, 0xFF, 0xFF, 0xFF))
    code += _store_bytes(ROM_FRAMES, (0xFF, 0xFF, 0x7A))
    code += _store_byte(wall_valid, 0)
    code += _store_byte(scheduler_tick_due, 0)
    code += _store_byte(cursor_blink_divider, 0)
    code += _store_byte(cursor_service_parity, 0)
    code += _store_byte(break_pending, 0)
    code += _store_byte(altreg_busy, 0)
    code += b"\xFB\x76\xF3"  # EI; HALT until exactly one frame interrupt; DI.
    code += _expect_bytes(kernel_ticks, (0x00, 0x00, 0x00, 0x00))
    code += _expect_bytes(ROM_FRAMES, (0x00, 0x00, 0x7B))
    code += _expect_byte(scheduler_tick_due, 1)
    code += _expect_byte(cursor_blink_divider, 1)
    code += _expect_byte(cursor_service_parity, 0)
    code += _jp(PASS_PC)
    run_sna(root, bytes(code), patch=phase1._kernel_patch(kernel_bytes))


def _udg_runtime(root: Path, labels: dict[str, int], kernel_bytes: bytes) -> None:
    code = bytearray(b"\xF3" + phase1._ld_sp(phase1.USER_STACK))
    for label in (
        "zx48_kernel_stack_init",
        "zx48_memory_init",
        "zx48_process_init",
        "zx48_handles_init",
        "zx48_pipe_init",
        "zx48_ula_init",
        "zx48_console_init",
        "zx48_keyboard_init",
    ):
        code += _call(labels[label])
    code += _store_bytes(ROM_UDG, (0xFF, 0xFF))
    code += _store_bytes(UDG_BANK_BASE, tuple(0xA5 for _ in range(UDG_BANK_SIZE)))
    code += _call(labels["zx48_udg_init"]) + _jp_c(FAIL_PC)
    code += _expect_word(labels["udg_bank_ptr"], UDG_BANK_BASE)
    code += _expect_word(ROM_UDG, UDG_BANK_BASE)
    code += _expect_word(labels["memory_pinned_bytes"], UDG_BANK_SIZE)
    code += _expect_word(labels["memory_live_allocations"], 1)
    code += _expect_word(labels["memory_free_extents"], FIRST_FREE_AFTER_UDG)
    code += _expect_word(labels["memory_free_extents"] + 2, FIRST_FREE_LENGTH_AFTER_UDG)
    code += _expect_byte(labels["process_table"] + PROC_DESC_SIZE + PROC_STATE, PROC_FREE)
    code += _expect_bytes(UDG_BANK_BASE, tuple(0 for _ in range(UDG_BANK_SIZE)))
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
    if step != "P1.14":
        raise Phase1RomVarsError(f"ROM-variable compatibility step is not registered: {step}")

    assertions = _source_contract(root)
    failed = [item["name"] for item in assertions if item["passed"] is not True]
    require(not failed, f"static P1.14 contract failures: {failed}")

    command, kernel, listing = phase1._assemble_kernel(root, run_command, require_project_tool)
    labels = phase1._labels(
        listing,
        (
            "zx48_kernel_stack_init",
            "zx48_memory_init",
            "zx48_process_init",
            "zx48_handles_init",
            "zx48_pipe_init",
            "zx48_ula_init",
            "zx48_console_init",
            "zx48_keyboard_init",
            "zx48_udg_init",
            "zx48_im2_init",
            "kernel_ticks",
            "wall_valid",
            "scheduler_tick_due",
            "cursor_blink_divider",
            "cursor_service_parity",
            "break_pending",
            "altreg_busy",
            "udg_bank_ptr",
            "memory_pinned_bytes",
            "memory_live_allocations",
            "memory_free_extents",
            "process_table",
        ),
    )
    kernel_bytes = kernel.read_bytes()

    if action == "test":
        _frames_runtime(root, labels, kernel_bytes)
        _udg_runtime(root, labels, kernel_bytes)
        assertions.extend(_negative_contract_tests(root))
        assertions.extend(
            [
                {"name": "accepted-im2-frame-wraps-rom-frames-exactly", "passed": True},
                {"name": "sys-ticks-wrap-remains-independent-of-rom-frames", "passed": True},
                {"name": "udg-bank-runtime-pointer-is-0x6000", "passed": True},
                {"name": "udg-bank-is-zeroed-before-publication", "passed": True},
                {"name": "udg-bank-is-pinned-before-pid1-ready", "passed": True},
                {"name": "allocator-accounting-includes-exact-256-byte-pin", "passed": True},
            ]
        )

    paths = (
        root / "v1/src/kernel/interrupt.asm",
        root / "v1/src/boot/entry.asm",
        root / "v1/src/kernel/udg.asm",
        root / "v1/src/kernel/memory.asm",
        root / "v1/src/kernel/process.asm",
        root / "v1/src/kernel/errors.asm",
        root / "v1/src/kernel/handles.asm",
        root / "v1/src/kernel/pipe.asm",
        root / "v1/src/kernel/ula_io.asm",
        root / "v1/src/kernel/console.asm",
        root / "v1/src/kernel/keyboard.asm",
        root / "v1/include/zx48ux.inc",
        root / "v1/docs/rom-services.md",
        root / "v1/tools-host/test-driver/phase1_romvars.py",
        kernel,
    )
    return [command], {str(path.relative_to(root)): sha256_file(path) for path in paths}, assertions
