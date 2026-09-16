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
#
# Temporary P2.15 staged runtime diagnostic.  Each FUSE case proves one more
# boundary than the previous case so the first failing label identifies the
# exact block/wake/resume boundary instead of collapsing everything to FAIL_PC.

from __future__ import annotations

from pathlib import Path

from driver_core import DriverError, find_root, require_project_tool, run_command
from fuse_harness import FAIL_PC, PASS_PC, run_sna
import phase2_wait_specific_runtime as p


NAMES = (
    "zx48_syscall",
    "zx48_schedule",
    "zx48_process_links_init",
    "zx48_process_link_child",
    "zx48_process_unlink_child",
    "zx48_process_wait_record_specific",
    "zx48_process_zombie_wake_parent",
    "process_table",
    "current_pid",
    "process_generation",
    "process_child_mask",
    "process_wait_pid",
    "process_wait_generation",
    "process_wait_status_ptr",
    "process_zombie_pid",
    "process_zombie_parent_pid",
    "process_zombie_parent_generation",
    "p215_panic_code",
    "PROC_FREE",
    "PROC_READY",
    "PROC_RUNNING",
    "PROC_WAIT_CHILD",
    "PROC_ZOMBIE",
    "SYS_WAIT",
    "E_CHILD",
)


def _run_case(root: Path, label: str, code: bytes, *, patch) -> None:
    try:
        run_sna(root, code, patch=patch)
    except DriverError as exc:
        raise DriverError(f"P2.15 staged runtime diagnostic failed at {label}: {exc}") from exc
    print(f"PASS {label}")


def _parent_code(symbols: dict[str, int], *, after_syscall: bytes) -> bytes:
    table = symbols["process_table"]
    p2 = table + 2 * p.PROC_DESC_SIZE
    code = bytearray(b"\xF3" + p._ld_sp(p.TEST_STACK))
    code += p._parent_init(symbols)
    code += p._link_child(symbols, 2, symbols["PROC_READY"])
    code += p._set_word(p2 + p.PROC_SAVED_SP, p.CHILD_FRAME)
    code += p._write_wait1(2)
    code += p._ld_hl(p.WAIT1)
    code += bytes((0x3E, symbols["SYS_WAIT"] & 0xFF))
    code += p._call(symbols["zx48_syscall"])
    code += after_syscall
    return bytes(code)


def _child_frame() -> bytes:
    return b"\x00" * 10 + p._word(p.CHILD_PC)


def _block_case(root: Path, symbols: dict[str, int], fixture: bytes, label: str, check: bytes) -> None:
    child = bytes(check) + p._jp(PASS_PC)
    parent = _parent_code(symbols, after_syscall=p._jp(FAIL_PC))
    _run_case(
        root,
        label,
        parent,
        patch=p._fixture_patch(fixture, child_frame=_child_frame(), child_code=child),
    )


def _wake_child(symbols: dict[str, int], *, after_wake: bytes, schedule: bool) -> bytes:
    table = symbols["process_table"]
    p2 = table + 2 * p.PROC_DESC_SIZE
    child = bytearray()
    child += p._set_byte(p2 + p.PROC_EXIT_STATUS, 0x5A)
    child += p._set_byte(p2 + p.PROC_STATE, symbols["PROC_ZOMBIE"])
    child += p._set_byte(symbols["process_zombie_pid"], 2)
    child += p._set_byte(symbols["process_zombie_parent_pid"], 1)
    child += p._set_word(symbols["process_zombie_parent_generation"], 1)
    child += p._call(symbols["zx48_process_zombie_wake_parent"])
    child += after_wake
    child += p._jp(symbols["zx48_schedule"] if schedule else PASS_PC)
    return bytes(child)


def _resume_case(root: Path, symbols: dict[str, int], fixture: bytes, label: str, after_syscall: bytes) -> None:
    child = _wake_child(symbols, after_wake=p._jp_c(FAIL_PC), schedule=True)
    parent = _parent_code(symbols, after_syscall=after_syscall + p._jp(PASS_PC))
    _run_case(
        root,
        label,
        parent,
        patch=p._fixture_patch(fixture, child_frame=_child_frame(), child_code=child),
    )


def main() -> int:
    root = find_root(Path(__file__))
    command, binary, symbol_path = p._assemble_fixture(root, run_command, require_project_tool)
    symbols = p._symbols(symbol_path, NAMES)
    fixture = binary.read_bytes()
    table = symbols["process_table"]
    p1 = table + p.PROC_DESC_SIZE
    p2 = table + 2 * p.PROC_DESC_SIZE

    _block_case(root, symbols, fixture, "block-reaches-child", b"")
    _block_case(root, symbols, fixture, "block-current-pid-is-child", p._expect_byte(symbols["current_pid"], 2))
    _block_case(root, symbols, fixture, "block-parent-is-wait-child", p._expect_byte(p1 + p.PROC_STATE, symbols["PROC_WAIT_CHILD"]))
    _block_case(root, symbols, fixture, "block-recorded-specific-pid", p._expect_byte(symbols["process_wait_pid"] + 1, 2))
    _block_case(root, symbols, fixture, "block-recorded-specific-generation", p._expect_word(symbols["process_wait_generation"] + 2, 1))
    _block_case(root, symbols, fixture, "block-retained-status-pointer", p._expect_word(symbols["process_wait_status_ptr"] + 2, p.STATUS_PTR))

    wake_check = p._jp_c(FAIL_PC) + p._expect_byte(p1 + p.PROC_STATE, symbols["PROC_READY"])
    wake_child = _wake_child(symbols, after_wake=wake_check, schedule=False)
    wake_parent = _parent_code(symbols, after_syscall=p._jp(FAIL_PC))
    _run_case(
        root,
        "exact-child-wakes-parent",
        wake_parent,
        patch=p._fixture_patch(fixture, child_frame=_child_frame(), child_code=wake_child),
    )

    _resume_case(root, symbols, fixture, "wake-schedules-parent-continuation", b"")
    _resume_case(root, symbols, fixture, "resumed-wait-clears-carry", p._jp_c(FAIL_PC))
    _resume_case(root, symbols, fixture, "resumed-wait-returns-child-pid", p._expect_hl(2))
    _resume_case(root, symbols, fixture, "resumed-wait-writes-status-byte", p._expect_byte(p.STATUS_PTR, 0x5A))
    _resume_case(root, symbols, fixture, "resumed-wait-preserves-status-prefix", p._expect_byte(p.STATUS_BASE, 0xA5))
    _resume_case(root, symbols, fixture, "resumed-wait-preserves-status-suffix", p._expect_byte(p.STATUS_PTR + 1, 0x7E))
    _resume_case(root, symbols, fixture, "resumed-wait-reclaims-child", p._expect_byte(p2 + p.PROC_STATE, symbols["PROC_FREE"]))
    _resume_case(root, symbols, fixture, "resumed-wait-restores-parent-pid", p._expect_byte(symbols["current_pid"], 1))
    _resume_case(root, symbols, fixture, "resumed-wait-does-not-panic", p._expect_byte(symbols["p215_panic_code"], 0))

    print(f"P2.15 STAGED RUNTIME DIAGNOSTIC PASS fixture={binary} command_exit={command.exit_code}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (DriverError, OSError, ValueError) as exc:
        print(f"P2.15 STAGED RUNTIME DIAGNOSTIC FAIL: {exc}")
        raise SystemExit(1)
