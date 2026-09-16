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

FIXTURE_CODE = 0xC000
TEST_STACK = 0x8F00
STATUS_PTR = 0x6901
PROC_DESC_SIZE = 48
PROC_PID = 0
PROC_PARENT = 1
PROC_STATE = 2
PROC_IMAGE_BASE = 4
PROC_IMAGE_SIZE = 6
PROC_STACK_LOW = 8
PROC_STACK_HIGH = 10
PROC_SAVED_SP = 12
PROC_EXIT_STATUS = 14
PROC_OWNED_BYTES = 40
PROC_ARG_PTR = 42
PROC_ENV_PTR = 44
IMAGE_BASE = 0x8000
IMAGE_SIZE = 0x0100
STACK_BASE = 0x8100
STACK_SIZE = 0x0080
BOOTSTRAP_BASE = 0x8180
BOOTSTRAP_SIZE = 0x0040
OWNED_SIZE = IMAGE_SIZE + STACK_SIZE + BOOTSTRAP_SIZE


class Phase2ReparentError(DriverError):
    """Raised when the P2.17 child-reparenting contract regresses."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Phase2ReparentError(message)


def _word(value: int) -> bytes:
    return bytes((value & 0xFF, (value >> 8) & 0xFF))


def _symbols(path: Path, names: tuple[str, ...]) -> dict[str, int]:
    text = path.read_text(encoding="utf-8", errors="replace")
    found: dict[str, int] = {}
    for name in names:
        pattern = re.compile(
            rf"^{re.escape(name)}:\s+equ\s+0x([0-9A-Fa-f]+)\s*$",
            re.IGNORECASE | re.MULTILINE,
        )
        match = pattern.search(text)
        require(match is not None, f"P2.17 symbol missing from assembler output: {name}")
        found[name] = int(match.group(1), 16)
    return found


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


def _ld_hl(value: int) -> bytes:
    return b"\x21" + _word(value)


def _ld_de(value: int) -> bytes:
    return b"\x11" + _word(value)


def _set_byte(address: int, value: int) -> bytes:
    return bytes((0x3E, value & 0xFF, 0x32)) + _word(address)


def _set_word(address: int, value: int) -> bytes:
    return _ld_hl(value) + b"\x22" + _word(address)


def _expect_byte(address: int, value: int) -> bytes:
    return b"\x3A" + _word(address) + bytes((0xFE, value & 0xFF)) + _jp_nz(FAIL_PC)


def _expect_word(address: int, value: int) -> bytes:
    return _expect_byte(address, value & 0xFF) + _expect_byte(address + 1, (value >> 8) & 0xFF)


def _expect_hl(value: int) -> bytes:
    return (
        bytes((0x7C, 0xFE, (value >> 8) & 0xFF))
        + _jp_nz(FAIL_PC)
        + bytes((0x7D, 0xFE, value & 0xFF))
        + _jp_nz(FAIL_PC)
    )


def _assemble_kernel(
    root: Path,
    run_command: Callable[..., Any],
    require_project_tool: Callable[[Path, str | Path], Path],
):
    assembler = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    result = run_command(
        [assembler, "--nologo", "--lst=../../build/kernel-p217.lst", "--sym=../../build/kernel-p217.sym", "kernel.asm"],
        cwd=root / "v1/src/kernel",
        timeout_seconds=30.0,
    )
    require(
        not result.timed_out and result.exit_code == 0,
        f"P2.17 resident kernel assembly failed: {result.stderr or result.stdout}",
    )
    binary = build / "kernel.bin"
    symbols = build / "kernel-p217.sym"
    require(binary.is_file() and binary.stat().st_size == 8192, "P2.17 resident kernel must remain exactly 8192 bytes")
    require(symbols.is_file(), "P2.17 resident kernel symbols missing")
    return result, binary, symbols


def _assemble_fixture(
    root: Path,
    run_command: Callable[..., Any],
    require_project_tool: Callable[[Path, str | Path], Path],
):
    assembler = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    source = build / "p217-reparent.asm"
    binary = build / "p217-reparent.bin"
    symbols = build / "p217-reparent.sym"
    source.write_text(
        "    DEVICE ZXSPECTRUM48\n"
        "    INCLUDE \"../include/zx48ux.inc\"\n"
        "    INCLUDE \"../src/kernel/process.asm\"\n"
        f"    ORG ${FIXTURE_CODE:04X}\n"
        "p217_start:\n"
        "    EMIT_PROCESS_ROUTINES\n"
        "    EMIT_PARENT_CHILD_ROUTINES\n"
        "    EMIT_WAIT_SPECIFIC_ROUTINES\n"
        "    EMIT_ZOMBIE_TRANSITION_ROUTINES\n"
        "zx48_handles_close_all_current: xor a : ret\n"
        "zx48_free: xor a : ret\n"
        "zx48_schedule: ret\n"
        "zx48_syscall_resume_wait_specific: ret\n"
        "zx48_panic: ld (p217_panic_code),a : ret\n"
        "syscall_frame_sp: dw 0\n"
        "tty_input_owner: db 0\n"
        "p217_panic_code: db 0\n"
        "p217_end:\n"
        "    ASSERT p217_end <= KERNEL_STACK_START\n"
        "    SAVEBIN \"p217-reparent.bin\",p217_start,p217_end-p217_start\n",
        encoding="utf-8",
        newline="\n",
    )
    result = run_command(
        [assembler, "--nologo", "--sym=p217-reparent.sym", "p217-reparent.asm"],
        cwd=build,
        timeout_seconds=30.0,
    )
    require(
        not result.timed_out and result.exit_code == 0,
        f"P2.17 reparent fixture assembly failed: {result.stderr or result.stdout}",
    )
    require(binary.is_file() and 0 < binary.stat().st_size < 0x3B00, "P2.17 fixture missing or overlaps kernel stack")
    require(symbols.is_file(), "P2.17 fixture symbols missing")
    return result, binary, symbols


def _fixture_patch(fixture: bytes):
    def patch(ram: bytearray) -> None:
        start = FIXTURE_CODE - 0x4000
        ram[start : start + len(fixture)] = fixture

    return patch


def _set_exit_extents(base: int) -> bytes:
    code = bytearray()
    code += _set_word(base + PROC_IMAGE_BASE, IMAGE_BASE)
    code += _set_word(base + PROC_IMAGE_SIZE, IMAGE_SIZE)
    code += _set_word(base + PROC_STACK_LOW, STACK_BASE)
    code += _set_word(base + PROC_STACK_HIGH, STACK_BASE + STACK_SIZE)
    code += _set_word(base + PROC_SAVED_SP, STACK_BASE + STACK_SIZE - 2)
    code += _set_word(base + PROC_ARG_PTR, BOOTSTRAP_BASE)
    code += _set_word(base + PROC_ENV_PTR, BOOTSTRAP_BASE + 0x20)
    code += _set_word(base + PROC_OWNED_BYTES, OWNED_SIZE)
    return bytes(code)


def _positive_tree_exit_reap(root: Path, symbols: dict[str, int], fixture: bytes) -> None:
    table = symbols["process_table"]
    p1 = table + PROC_DESC_SIZE
    p2 = table + 2 * PROC_DESC_SIZE
    p3 = table + 3 * PROC_DESC_SIZE
    child_mask = symbols["process_child_mask"]
    parent_generation = symbols["process_parent_generation"]

    code = bytearray(b"\xF3" + _ld_sp(TEST_STACK))
    code += _call(symbols["zx48_process_init"])
    code += _call(symbols["zx48_process_prepare_pid1"]) + _jp_c(FAIL_PC)
    code += _call(symbols["zx48_process_links_init"]) + _jp_c(FAIL_PC)

    code += _set_byte(symbols["current_pid"], 1)
    code += b"\x3E\x02" + _call(symbols["zx48_process_link_child"]) + _jp_c(FAIL_PC)
    code += _set_byte(p2 + PROC_STATE, symbols["PROC_READY"])
    code += _set_byte(symbols["current_pid"], 2)
    code += b"\x3E\x03" + _call(symbols["zx48_process_link_child"]) + _jp_c(FAIL_PC)
    code += _set_byte(p3 + PROC_STATE, symbols["PROC_READY"])
    code += _set_byte(p2 + PROC_STATE, symbols["PROC_RUNNING"])
    code += _set_exit_extents(p2)

    code += b"\x3E\x22" + _call(symbols["zx48_process_exit_to_zombie"])
    code += _expect_byte(symbols["p217_panic_code"], 0)
    code += _expect_byte(p2 + PROC_STATE, symbols["PROC_ZOMBIE"])
    code += _expect_byte(p2 + PROC_EXIT_STATUS, 0x22)
    code += _expect_byte(p3 + PROC_PARENT, 1)
    code += _expect_word(parent_generation + 3 * 2, 1)
    code += _expect_byte(child_mask + 1, 0x0C)
    code += _expect_byte(child_mask + 2, 0)

    code += _set_byte(symbols["current_pid"], 3)
    code += _set_byte(p3 + PROC_STATE, symbols["PROC_RUNNING"])
    code += _set_exit_extents(p3)
    code += b"\x3E\x33" + _call(symbols["zx48_process_exit_to_zombie"])
    code += _expect_byte(symbols["p217_panic_code"], 0)
    code += _expect_byte(p3 + PROC_STATE, symbols["PROC_ZOMBIE"])
    code += _expect_byte(p3 + PROC_EXIT_STATUS, 0x33)
    code += _expect_byte(p3 + PROC_PARENT, 1)

    code += _set_byte(symbols["current_pid"], 1)
    code += _set_byte(STATUS_PTR, 0xCC)
    code += _ld_de(STATUS_PTR)
    code += b"\x3E\x03" + _call(symbols["zx48_process_wait_specific"]) + _jp_c(FAIL_PC)
    code += _expect_hl(3)
    code += _expect_byte(STATUS_PTR, 0x33)
    code += _expect_byte(p3 + PROC_STATE, symbols["PROC_FREE"])
    code += _expect_byte(child_mask + 1, 0x04)
    code += _expect_byte(p1 + PROC_STATE, symbols["PROC_READY"])
    code += _expect_byte(symbols["p217_panic_code"], 0)
    code += _jp(PASS_PC)
    run_sna(root, bytes(code), patch=_fixture_patch(fixture))


def _free_pid1_rejected_without_mutation(root: Path, symbols: dict[str, int], fixture: bytes) -> None:
    table = symbols["process_table"]
    p1 = table + PROC_DESC_SIZE
    p2 = table + 2 * PROC_DESC_SIZE
    p3 = table + 3 * PROC_DESC_SIZE
    child_mask = symbols["process_child_mask"]
    parent_generation = symbols["process_parent_generation"]

    code = bytearray(b"\xF3" + _ld_sp(TEST_STACK))
    code += _call(symbols["zx48_process_init"])
    code += _call(symbols["zx48_process_prepare_pid1"]) + _jp_c(FAIL_PC)
    code += _call(symbols["zx48_process_links_init"]) + _jp_c(FAIL_PC)
    code += _set_byte(symbols["current_pid"], 1)
    code += b"\x3E\x02" + _call(symbols["zx48_process_link_child"]) + _jp_c(FAIL_PC)
    code += _set_byte(p2 + PROC_STATE, symbols["PROC_READY"])
    code += _set_byte(symbols["current_pid"], 2)
    code += b"\x3E\x03" + _call(symbols["zx48_process_link_child"]) + _jp_c(FAIL_PC)
    code += _set_byte(p3 + PROC_STATE, symbols["PROC_READY"])
    code += _set_byte(p1 + PROC_STATE, symbols["PROC_FREE"])

    code += b"\x3E\x02" + _call(symbols["zx48_process_reparent_children_to_pid1"]) + _jp_nc(FAIL_PC)
    code += bytes((0xFE, symbols["E_INVAL"] & 0xFF)) + _jp_nz(FAIL_PC)
    code += _expect_byte(p3 + PROC_PARENT, 2)
    code += _expect_word(parent_generation + 3 * 2, 1)
    code += _expect_byte(child_mask + 1, 0x04)
    code += _expect_byte(child_mask + 2, 0x08)
    code += _jp(PASS_PC)
    run_sna(root, bytes(code), patch=_fixture_patch(fixture))


def _source_contract(root: Path) -> list[dict[str, object]]:
    process = (root / "v1/src/kernel/process.asm").read_text(encoding="utf-8")
    links_start = process.index("    MACRO EMIT_PARENT_CHILD_ROUTINES")
    links_end = process.index("    ENDM\n", links_start)
    links = process[links_start:links_end]
    zombie_start = process.index("    MACRO EMIT_ZOMBIE_TRANSITION_ROUTINES")
    zombie_end = process.index("    ENDM\n", zombie_start)
    zombie = process[zombie_start:zombie_end]
    reparent_start = links.index("zx48_process_reparent_children_to_pid1:")
    reparent_end = links.index("zx48_process_wait_record_specific:", reparent_start)
    reparent = links[reparent_start:reparent_end]

    return [
        {
            "name": "exit-reparents-before-handle-close-and-private-free",
            "passed": "call zx48_process_reparent_children_to_pid1" in zombie
            and zombie.index("call zx48_process_reparent_children_to_pid1") < zombie.index("call zx48_handles_close_all_current")
            and zombie.index("call zx48_process_reparent_children_to_pid1") < zombie.index("call zx48_free"),
        },
        {
            "name": "exit-reparents-before-zombie-publication",
            "passed": "call zx48_process_reparent_children_to_pid1" in zombie
            and zombie.index("call zx48_process_reparent_children_to_pid1") < zombie.index("ld (ix+PROC_STATE),PROC_ZOMBIE"),
        },
        {
            "name": "reparent-requires-live-old-parent-and-live-pid1",
            "passed": reparent.count("ld a,(ix+PROC_STATE)") >= 2
            and reparent.count("jp z,zx48_process_links_inval") >= 2
            and "ld a,1\n    call zx48_process_links_desc_ptr" in reparent,
        },
        {
            "name": "reparent-is-parent-generation-qualified",
            "passed": "process_reparent_parent_generation" in reparent
            and "call zx48_process_parent_generation_ptr" in reparent
            and "sbc hl,de" in reparent,
        },
        {
            "name": "reparent-publishes-pid1-generation-and-child-mask",
            "passed": "ld (ix+PROC_PARENT),1" in reparent
            and "process_reparent_pid1_generation" in reparent
            and "call zx48_process_child_mask_ptr" in reparent
            and "or (hl)" in reparent,
        },
        {
            "name": "reparent-clears-old-parent-child-mask-after-bounded-scan",
            "passed": "ld a,2" in reparent
            and "cp MAX_PROCESSES" in reparent
            and "ld a,(process_reparent_parent_pid)" in reparent
            and "ld (hl),0" in reparent,
        },
    ]


def dispatch(
    root: Path,
    action: str,
    step: str,
    *,
    sha256_file: Callable[[Path], str],
    run_command: Callable[..., Any],
    require_project_tool: Callable[[Path, str | Path], Path],
):
    if step != "P2.17":
        raise DriverError(f"Phase-2 reparent step is not registered: {step}")

    assertions = _source_contract(root)
    failed = [item["name"] for item in assertions if item.get("passed") is not True]
    require(not failed, f"static P2.17 contract failures: {failed}")

    kernel_command, kernel_binary, kernel_symbols = _assemble_kernel(root, run_command, require_project_tool)
    kernel_values = _symbols(kernel_symbols, ("kernel_ordinary_used_end", "KERNEL_CODE_END"))
    free_bytes = kernel_values["KERNEL_CODE_END"] + 1 - kernel_values["kernel_ordinary_used_end"]
    require(free_bytes >= 0, "P2.17 resident ordinary kernel exceeds hard ceiling")
    assertions.append(
        {
            "name": "resident-kernel-ordinary-code-remains-within-faff-ceiling",
            "passed": True,
            "used_end": f"0x{kernel_values['kernel_ordinary_used_end']:04X}",
            "code_end": f"0x{kernel_values['KERNEL_CODE_END']:04X}",
            "free_bytes": free_bytes,
        }
    )

    fixture_command, fixture_binary, fixture_symbols = _assemble_fixture(root, run_command, require_project_tool)
    names = (
        "zx48_process_init",
        "zx48_process_prepare_pid1",
        "zx48_process_links_init",
        "zx48_process_link_child",
        "zx48_process_reparent_children_to_pid1",
        "zx48_process_exit_to_zombie",
        "zx48_process_wait_specific",
        "process_table",
        "current_pid",
        "process_parent_generation",
        "process_child_mask",
        "p217_panic_code",
        "PROC_FREE",
        "PROC_READY",
        "PROC_RUNNING",
        "PROC_ZOMBIE",
        "E_INVAL",
    )
    symbols = _symbols(fixture_symbols, names)
    fixture = fixture_binary.read_bytes()
    assertions.append(
        {
            "name": "p217-runtime-fixture-assembles-real-link-reparent-zombie-and-wait-composition",
            "passed": True,
            "bytes": len(fixture),
        }
    )
    if action == "test":
        _positive_tree_exit_reap(root, symbols, fixture)
        assertions.append(
            {
                "name": "parent-exit-reparents-live-child-then-pid1-reaps-child-after-its-exit",
                "passed": True,
            }
        )
        _free_pid1_rejected_without_mutation(root, symbols, fixture)
        assertions.append(
            {
                "name": "free-pid1-reparent-target-is-rejected-with-tree-byte-intact",
                "passed": True,
            }
        )

    return [kernel_command, fixture_command], {
        "v1/build/kernel.bin": sha256_file(kernel_binary),
        "v1/build/p217-reparent.bin": sha256_file(fixture_binary),
        "v1/src/kernel/process.asm": sha256_file(root / "v1/src/kernel/process.asm"),
        "v1/tools-host/test-driver/phase2_reparent.py": sha256_file(root / "v1/tools-host/test-driver/phase2_reparent.py"),
        "v1/tools-host/test-driver/run.py": sha256_file(root / "v1/tools-host/test-driver/run.py"),
        "v1/tools-host/test-driver/phase2_gate.py": sha256_file(root / "v1/tools-host/test-driver/phase2_gate.py"),
    }, assertions
