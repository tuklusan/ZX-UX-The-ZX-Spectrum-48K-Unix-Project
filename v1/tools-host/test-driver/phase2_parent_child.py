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

FIXTURE_CODE = 0xE000
PROGRAM_ADDRESS = 0x9000
TEST_STACK = 0x8F00
PROCESS_COUNT = 8
PROC_DESC_SIZE = 48
PROC_PARENT = 1
PROC_STATE = 2
PROC_FLAGS = 3


class Phase2ParentChildError(DriverError):
    """Raised when the P2.13 generation-safe parent/child contract regresses."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Phase2ParentChildError(message)


def _word(value: int) -> bytes:
    return bytes((value & 0xFF, (value >> 8) & 0xFF))


def _symbols(path: Path, names: tuple[str, ...]) -> dict[str, int]:
    text = path.read_text(encoding="utf-8", errors="replace")
    found: dict[str, int] = {}
    for name in names:
        pattern = re.compile(rf"^{re.escape(name)}:\s+equ\s+0x([0-9A-Fa-f]+)\s*$", re.IGNORECASE | re.MULTILINE)
        match = pattern.search(text)
        require(match is not None, f"P2.13 symbol missing from assembler output: {name}")
        found[name] = int(match.group(1), 16)
    return found


def _assemble_kernel(
    root: Path,
    run_command: Callable[..., Any],
    require_project_tool: Callable[[Path, str | Path], Path],
):
    assembler = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    result = run_command(
        [assembler, "--nologo", "--lst=../../build/kernel-p213.lst", "--sym=../../build/kernel-p213.sym", "kernel.asm"],
        cwd=root / "v1/src/kernel",
        timeout_seconds=30.0,
    )
    require(not result.timed_out and result.exit_code == 0, f"P2.13 resident kernel assembly failed: {result.stderr or result.stdout}")
    binary = build / "kernel.bin"
    symbols = build / "kernel-p213.sym"
    require(binary.is_file() and binary.stat().st_size == 8192, "P2.13 resident kernel must remain exactly 8192 bytes")
    require(symbols.is_file(), "P2.13 resident kernel symbols missing")
    return result, binary, symbols


def _assemble_fixture(
    root: Path,
    run_command: Callable[..., Any],
    require_project_tool: Callable[[Path, str | Path], Path],
):
    assembler = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    source = build / "p213-parent-child.asm"
    binary = build / "p213-parent-child.bin"
    symbols = build / "p213-parent-child.sym"
    source.write_text(
        "    DEVICE ZXSPECTRUM48\n"
        "    INCLUDE \"../include/zx48ux.inc\"\n"
        "    INCLUDE \"../src/kernel/process.asm\"\n"
        f"    ORG ${FIXTURE_CODE:04X}\n"
        "p213_start:\n"
        "    EMIT_PARENT_CHILD_ROUTINES\n"
        "current_pid: db 0\n"
        "process_table: defs MAX_PROCESSES*PROC_DESC_SIZE,0\n"
        "p213_end:\n"
        "    SAVEBIN \"p213-parent-child.bin\",p213_start,p213_end-p213_start\n",
        encoding="utf-8",
        newline="\n",
    )
    result = run_command(
        [assembler, "--nologo", "--sym=p213-parent-child.sym", "p213-parent-child.asm"],
        cwd=build,
        timeout_seconds=30.0,
    )
    require(not result.timed_out and result.exit_code == 0, f"P2.13 parent/child fixture assembly failed: {result.stderr or result.stdout}")
    require(binary.is_file() and 0 < binary.stat().st_size < 0x1000, "P2.13 fixture binary missing or too large")
    require(symbols.is_file(), "P2.13 fixture symbols missing")
    return result, binary, symbols


def _process_table() -> bytes:
    table = bytearray(PROCESS_COUNT * PROC_DESC_SIZE)
    for pid in range(PROCESS_COUNT):
        table[pid * PROC_DESC_SIZE] = pid
        table[pid * PROC_DESC_SIZE + PROC_PARENT] = 0xFF
        if pid >= 2:
            table[pid * PROC_DESC_SIZE + PROC_FLAGS] = 0xA5
    table[0 * PROC_DESC_SIZE + PROC_STATE] = 2
    table[1 * PROC_DESC_SIZE + PROC_PARENT] = 0
    table[1 * PROC_DESC_SIZE + PROC_STATE] = 2
    return bytes(table)


def _patch(fixture: bytes, process_address: int):
    process = _process_table()

    def patch(ram: bytearray) -> None:
        fixture_start = FIXTURE_CODE - 0x4000
        ram[fixture_start : fixture_start + len(fixture)] = fixture
        process_start = process_address - 0x4000
        ram[process_start : process_start + len(process)] = process

    return patch


def _ld_a_mem(address: int) -> bytes:
    return b"\x3A" + _word(address)


def _ld_mem_a(address: int) -> bytes:
    return b"\x32" + _word(address)


def _call(address: int) -> bytes:
    return b"\xCD" + _word(address)


def _jp_c(address: int) -> bytes:
    return b"\xDA" + _word(address)


def _jp_nc(address: int) -> bytes:
    return b"\xD2" + _word(address)


def _expect_byte(address: int, value: int) -> bytes:
    return _ld_a_mem(address) + bytes((0xFE, value & 0xFF)) + phase1._jp_nz(FAIL_PC)


def _expect_word(address: int, value: int) -> bytes:
    return _expect_byte(address, value & 0xFF) + _expect_byte(address + 1, (value >> 8) & 0xFF)


def _set_byte(address: int, value: int) -> bytes:
    return bytes((0x3E, value & 0xFF)) + _ld_mem_a(address)


def _target_tests(root: Path, symbols: dict[str, int], fixture: bytes) -> list[dict[str, object]]:
    require(symbols["MAX_PROCESSES"] == PROCESS_COUNT, "P2.13 process-count ABI changed")
    require(symbols["PROC_DESC_SIZE"] == PROC_DESC_SIZE, "P2.13 descriptor ABI changed")
    require(symbols["PROC_READY"] == 1 and symbols["PROC_RUNNING"] == 2, "P2.13 process-state ABI changed")
    require(symbols["E_CHILD"] == 8 and symbols["E_AGAIN"] == 13, "P2.13 errno ABI changed")

    table = symbols["process_table"]
    current_pid = symbols["current_pid"]
    generations = symbols["process_generation"]
    parent_generations = symbols["process_parent_generation"]
    child_masks = symbols["process_child_mask"]
    wait_pids = symbols["process_wait_pid"]
    wait_generations = symbols["process_wait_generation"]

    code = bytearray(b"\xF3" + phase1._ld_sp(TEST_STACK))
    code += _call(symbols["zx48_process_links_init"]) + _jp_c(FAIL_PC)

    # PID1 spawns PID2. Linking happens while the child descriptor is still FREE;
    # READY is deliberately published by the caller afterwards, as P2.10 requires.
    code += _set_byte(current_pid, 1)
    code += bytes((0x3E, 2)) + _call(symbols["zx48_process_link_child"]) + _jp_c(FAIL_PC)
    code += _expect_byte(table + 2 * PROC_DESC_SIZE + PROC_FLAGS, 0)
    code += _set_byte(table + 2 * PROC_DESC_SIZE + PROC_STATE, symbols["PROC_READY"])

    # PID2 spawns PID3, making the exact tree 1 -> 2 -> 3.
    code += _set_byte(current_pid, 2)
    code += bytes((0x3E, 3)) + _call(symbols["zx48_process_link_child"]) + _jp_c(FAIL_PC)
    code += _set_byte(table + 3 * PROC_DESC_SIZE + PROC_STATE, symbols["PROC_READY"])

    # Parent PID1 records a generation-qualified wait for the first incarnation
    # of PID2. The token is intentionally left stale across the later PID reuse.
    code += _set_byte(current_pid, 1)
    code += bytes((0x3E, 2)) + _call(symbols["zx48_process_wait_record_specific"]) + _jp_c(FAIL_PC)

    # Before PID2 can be reclaimed, its live direct child is reparented to PID1.
    code += bytes((0x3E, 2)) + _call(symbols["zx48_process_reparent_children_to_pid1"]) + _jp_c(FAIL_PC)
    code += bytes((0x3E, 2)) + _call(symbols["zx48_process_unlink_child"]) + _jp_c(FAIL_PC)
    code += _set_byte(table + 2 * PROC_DESC_SIZE + PROC_STATE, 0)
    code += _set_byte(table + 2 * PROC_DESC_SIZE + PROC_FLAGS, 0xA6)

    # PID2 is reused under PID1. Generation must advance without disturbing PID3.
    code += bytes((0x3E, 2)) + _call(symbols["zx48_process_link_child"]) + _jp_c(FAIL_PC)
    code += _set_byte(table + 2 * PROC_DESC_SIZE + PROC_STATE, symbols["PROC_READY"])

    # Exact final tree and generation metadata.
    code += _expect_byte(table + 2 * PROC_DESC_SIZE + PROC_PARENT, 1)
    code += _expect_byte(table + 2 * PROC_DESC_SIZE + PROC_FLAGS, 0)
    code += _expect_byte(table + 3 * PROC_DESC_SIZE + PROC_PARENT, 1)
    code += _expect_word(generations + 0 * 2, 1)
    code += _expect_word(generations + 1 * 2, 1)
    code += _expect_word(parent_generations + 1 * 2, 1)
    code += _expect_byte(child_masks + 0, 0x02)
    code += _expect_word(generations + 2 * 2, 2)
    code += _expect_word(generations + 3 * 2, 1)
    code += _expect_word(parent_generations + 2 * 2, 1)
    code += _expect_word(parent_generations + 3 * 2, 1)
    code += _expect_byte(child_masks + 1, 0x0C)
    code += _expect_byte(child_masks + 2, 0x00)
    code += _expect_byte(wait_pids + 1, 2)
    code += _expect_word(wait_generations + 1 * 2, 1)

    # Required negative: same numeric PID, different generation. A PID-only wait
    # matcher would incorrectly accept this reused PID2 and therefore hit FAIL_PC.
    code += bytes((0x3E, 2)) + _call(symbols["zx48_process_wait_matches"]) + _jp_nc(FAIL_PC)
    code += bytes((0xFE, symbols["E_CHILD"] & 0xFF)) + phase1._jp_nz(FAIL_PC)

    # Generation exhaustion is fail-closed rather than wrapping to an aliasable
    # identity. PID4 remains FREE and PID1's child mask remains byte-identical.
    code += _set_byte(generations + 4 * 2, 0xFF)
    code += _set_byte(generations + 4 * 2 + 1, 0xFF)
    code += bytes((0x3E, 4)) + _call(symbols["zx48_process_link_child"]) + _jp_nc(FAIL_PC)
    code += bytes((0xFE, symbols["E_AGAIN"] & 0xFF)) + phase1._jp_nz(FAIL_PC)
    code += _expect_byte(table + 4 * PROC_DESC_SIZE + PROC_STATE, 0)
    code += _expect_byte(table + 4 * PROC_DESC_SIZE + PROC_PARENT, 0xFF)
    code += _expect_byte(table + 4 * PROC_DESC_SIZE + PROC_FLAGS, 0xA5)
    code += _expect_byte(child_masks + 1, 0x0C)
    code += phase1._jp(PASS_PC)

    run_sna(root, bytes(code), patch=_patch(fixture, table))
    return [
        {"name": "pid0-pid1-root-edge-is-generation-qualified", "passed": True},
        {"name": "spawn-tree-remains-exact-through-pid-reuse", "passed": True},
        {"name": "reparent-preserves-live-grandchild-under-pid1", "passed": True},
        {"name": "bounded-child-mask-is-exact-after-reparent-unlink-and-reuse", "passed": True},
        {"name": "pid-generation-advances-across-reuse-without-reset", "passed": True},
        {"name": "successful-link-clears-stale-free-descriptor-before-publication", "passed": True},
        {"name": "stale-generation-qualified-wait-cannot-alias-reused-pid", "passed": True},
        {"name": "generation-exhaustion-refuses-reuse-with-free-descriptor-byte-intact", "passed": True},
    ]


def _source_contract(root: Path) -> list[dict[str, object]]:
    process = (root / "v1/src/kernel/process.asm").read_text(encoding="utf-8")
    start = process.index("    MACRO EMIT_PARENT_CHILD_ROUTINES")
    end = process.index("    ENDM\n", start)
    links = process[start:end]
    link_start = links.index("zx48_process_link_child:\n")
    link_end = links.index("zx48_process_generation_exhausted:\n", link_start)
    link = links[link_start:link_end]
    return [
        {"name": "descriptor-abi-remains-48-bytes", "passed": "PROC_PRIVATE_FLAGS        EQU 46" in process and "PROC_RESERVED             EQU 47" in process},
        {"name": "pid-generations-are-16-bit-side-metadata", "passed": "process_generation: defs MAX_PROCESSES*2,0" in links},
        {"name": "parent-generation-is-captured-per-child", "passed": "process_parent_generation: defs MAX_PROCESSES*2,0" in links and "zx48_process_parent_generation_ptr" in links},
        {"name": "children-are-bounded-by-one-max-processes-bitmask-per-parent", "passed": "process_child_mask: defs MAX_PROCESSES,0" in links and "zx48_process_pid_bit" in links},
        {"name": "generation-exhaustion-is-fail-closed-not-wrapped", "passed": "zx48_process_generation_exhausted:" in links and "ld a,E_AGAIN" in links and "zx48_process_generation_wrapped:" not in links},
        {"name": "new-child-link-bumps-generation-before-parent-publication", "passed": link.index("call zx48_process_generation_bump") < link.index("ld (ix+PROC_PARENT),a")},
        {"name": "successful-link-resets-free-descriptor-after-generation-bump", "passed": link.index("call zx48_process_generation_bump") < link.index("ld bc,PROC_DESC_SIZE-1") < link.index("ld (ix+PROC_PARENT),a")},
        {"name": "pid-reuse-clears-child-owned-mask-not-generation-counter", "passed": "call zx48_process_child_mask_ptr\n    ld (hl),0" in links},
        {"name": "unlink-clears-parent-mask-only-after-parent-generation-match", "passed": "zx48_process_unlink_parent_stale:" in links and "zx48_process_unlink_clear_parent:" in links},
        {"name": "reparent-scans-only-bounded-user-pid-range-and-qualifies-old-generation", "passed": "ld a,2" in links[links.index("zx48_process_reparent_children_to_pid1:"):] and "cp MAX_PROCESSES" in links[links.index("zx48_process_reparent_scan:"):] and "process_reparent_parent_generation" in links},
        {"name": "specific-wait-token-captures-child-generation", "passed": "process_wait_generation: defs MAX_PROCESSES*2,0" in links and "zx48_process_wait_record_specific" in links},
        {"name": "wait-match-compares-current-child-generation-to-recorded-token", "passed": "zx48_process_wait_matches" in links and "process_wait_compare_generation" in links},
        {"name": "pid0-pid1-root-edge-is-seeded-with-generation-and-bounded-mask", "passed": "ld (hl),$02" in links and "call zx48_process_parent_generation_ptr" in links},
        {"name": "p210-spawn-commit-invokes-generation-safe-link-before-ready-publication", "passed": "call zx48_process_link_child" in process and process.index("call zx48_process_link_child") < process.index("ld (ix+PROC_STATE),PROC_READY", process.index("    MACRO EMIT_SPAWN_TRANSACTION_ROUTINES"))},
        {"name": "p210-spawn-no-longer-publishes-raw-parent-pid-itself", "passed": "ld a,(current_pid)\n    ld (ix+PROC_PARENT),a" not in process[process.index("IFDEF ZX48_P2_13_LINKS_EMITTED", process.index("    MACRO EMIT_SPAWN_TRANSACTION_ROUTINES")):process.index("ELSE", process.index("IFDEF ZX48_P2_13_LINKS_EMITTED", process.index("    MACRO EMIT_SPAWN_TRANSACTION_ROUTINES")))]},
        {"name": "p213-spawn-does-not-own-untested-descriptor-reset", "passed": "ld hl,(process_spawn_child_desc)" not in process[process.index("IFDEF ZX48_P2_13_LINKS_EMITTED", process.index("    MACRO EMIT_SPAWN_TRANSACTION_ROUTINES")):process.index("ELSE", process.index("IFDEF ZX48_P2_13_LINKS_EMITTED", process.index("    MACRO EMIT_SPAWN_TRANSACTION_ROUTINES")))]},
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
    if step != "P2.13":
        raise DriverError(f"Phase-2 parent/child step is not registered: {step}")

    assertions = _source_contract(root)
    failed = [item["name"] for item in assertions if item["passed"] is not True]
    require(not failed, f"static P2.13 contract failures: {failed}")

    kernel_command, kernel_binary, kernel_symbols = _assemble_kernel(root, run_command, require_project_tool)
    fixture_command, fixture_binary, fixture_symbols = _assemble_fixture(root, run_command, require_project_tool)

    kernel_values = _symbols(kernel_symbols, ("kernel_ordinary_used_end", "KERNEL_CODE_END"))
    free_bytes = kernel_values["KERNEL_CODE_END"] + 1 - kernel_values["kernel_ordinary_used_end"]
    require(free_bytes >= 0, "P2.13 resident ordinary kernel exceeds hard ceiling")
    assertions.append({
        "name": "resident-kernel-ordinary-code-remains-within-faff-ceiling",
        "passed": True,
        "used_end": f"0x{kernel_values['kernel_ordinary_used_end']:04X}",
        "code_end": f"0x{kernel_values['KERNEL_CODE_END']:04X}",
        "free_bytes": free_bytes,
    })

    names = (
        "zx48_process_links_init",
        "zx48_process_link_child",
        "zx48_process_unlink_child",
        "zx48_process_reparent_children_to_pid1",
        "zx48_process_wait_record_specific",
        "zx48_process_wait_matches",
        "process_generation",
        "process_parent_generation",
        "process_child_mask",
        "process_wait_pid",
        "process_wait_generation",
        "process_table",
        "current_pid",
        "MAX_PROCESSES",
        "PROC_DESC_SIZE",
        "PROC_READY",
        "PROC_RUNNING",
        "E_CHILD",
        "E_AGAIN",
    )
    symbols = _symbols(fixture_symbols, names)
    fixture = fixture_binary.read_bytes()
    if action == "test":
        assertions.extend(_target_tests(root, symbols, fixture))

    return [kernel_command, fixture_command], {
        "v1/build/kernel.bin": sha256_file(kernel_binary),
        "v1/build/p213-parent-child.bin": sha256_file(fixture_binary),
        "v1/src/kernel/process.asm": sha256_file(root / "v1/src/kernel/process.asm"),
        "v1/tools-host/test-driver/phase2_parent_child.py": sha256_file(root / "v1/tools-host/test-driver/phase2_parent_child.py"),
        "v1/tools-host/test-driver/run.py": sha256_file(root / "v1/tools-host/test-driver/run.py"),
        "v1/tools-host/test-driver/phase2_gate.py": sha256_file(root / "v1/tools-host/test-driver/phase2_gate.py"),
    }, assertions
