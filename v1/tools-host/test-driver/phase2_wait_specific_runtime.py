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

from driver_core import DriverError, find_root, require_project_tool, run_command
from fuse_harness import FAIL_PC, PASS_PC, run_sna


FIXTURE_CODE = 0xC000
TEST_STACK = 0x8F00
CHILD_FRAME = 0x7000
CHILD_PC = 0x9800
WAIT1 = 0x6800
STATUS_BASE = 0x6900
STATUS_PTR = STATUS_BASE + 1
PROC_DESC_SIZE = 48
PROC_PID = 0
PROC_PARENT = 1
PROC_STATE = 2
PROC_SAVED_SP = 12
PROC_EXIT_STATUS = 14


class Phase2WaitSpecificRuntimeError(DriverError):
    """Raised when the P2.15 target runtime fixture regresses."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Phase2WaitSpecificRuntimeError(message)


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
        require(match is not None, f"P2.15 runtime symbol missing: {name}")
        found[name] = int(match.group(1), 16)
    return found


def _assemble_fixture(
    root: Path,
    runner: Callable[..., Any],
    project_tool: Callable[[Path, str | Path], Path],
):
    assembler = project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    source = build / "p215-wait-specific.asm"
    binary = build / "p215-wait-specific.bin"
    symbols = build / "p215-wait-specific.sym"
    source.write_text(
        "    DEVICE ZXSPECTRUM48\n"
        "    DEFINE ZX48_P2_15_WAIT_ENABLED\n"
        "    INCLUDE \"../include/zx48ux.inc\"\n"
        "    INCLUDE \"../src/kernel/syscall.asm\"\n"
        "    INCLUDE \"../src/kernel/process.asm\"\n"
        "    INCLUDE \"../src/kernel/handles.asm\"\n"
        "    INCLUDE \"../src/kernel/scheduler.asm\"\n"
        "PANIC_SCHEDULER EQU $03\n"
        "TTY_REQ_GET_MODE EQU 1\n"
        "TTY_REQ_GET_SIZE EQU 3\n"
        "TTY_REQ_SET_OWNER EQU 7\n"
        f"    ORG ${FIXTURE_CODE:04X}\n"
        "p215_start:\n"
        "    EMIT_PARENT_CHILD_ROUTINES\n"
        "    EMIT_WAIT_SPECIFIC_ROUTINES\n"
        "    EMIT_SYSCALL_BODY\n"
        "    EMIT_SYSCALL_IMPL\n"
        "    EMIT_ZOMBIE_TRANSITION_ROUTINES\n"
        "    EMIT_SCHEDULER_ROUTINES\n"
        "\n"
        "; Minimal process pointer surface used by the real scheduler/syscall fixture.\n"
        "zx48_process_ptr:\n"
        "    cp MAX_PROCESSES\n"
        "    jr nc,p215_noent\n"
        "    ld ix,process_table\n"
        "    or a\n"
        "    ret z\n"
        "    ld b,a\n"
        "    ld de,PROC_DESC_SIZE\n"
        "p215_process_ptr_loop:\n"
        "    add ix,de\n"
        "    djnz p215_process_ptr_loop\n"
        "    xor a\n"
        "    ret\n"
        "zx48_process_lookup:\n"
        "    call zx48_process_ptr\n"
        "    ret c\n"
        "    ld a,(ix+PROC_STATE)\n"
        "    or a\n"
        "    jr z,p215_noent\n"
        "    xor a\n"
        "    ret\n"
        "p215_noent:\n"
        "    ld a,E_NOENT\n"
        "    scf\n"
        "    ret\n"
        "\n"
        "; Unused syscall surfaces are fail-closed stubs; the WAIT path is real.\n"
        "zx48_process_exit: ld a,E_NOTSUP : scf : ret\n"
        "zx48_process_wait: ld a,E_CHILD : scf : ret\n"
        "zx48_process_kill: ld a,E_NOTSUP : scf : ret\n"
        "zx48_process_info: ld a,E_NOTSUP : scf : ret\n"
        "zx48_handle_close: ld a,E_NOTSUP : scf : ret\n"
        "zx48_handle_lookup: ld a,E_NOTSUP : scf : ret\n"
        "zx48_pipe_read: ld a,E_NOTSUP : scf : ret\n"
        "zx48_pipe_write: ld a,E_NOTSUP : scf : ret\n"
        "zx48_pipe_create: ld a,E_NOTSUP : scf : ret\n"
        "zx48_handle_dup: ld a,E_NOTSUP : scf : ret\n"
        "zx48_tty_ioctl: ld a,E_NOTSUP : scf : ret\n"
        "zx48_keyboard_getkey: ld a,E_NOTSUP : scf : ret\n"
        "zx48_console_putchar: ld a,E_NOTSUP : scf : ret\n"
        "zx48_console_write: ld a,E_NOTSUP : scf : ret\n"
        "zx48_console_clear: ret\n"
        "zx48_console_getpos: ld hl,0 : ret\n"
        "zx48_console_setpos: ld a,E_NOTSUP : scf : ret\n"
        "zx48_mem_info: ret\n"
        "\n"
        "; P2.14 exit dependencies are not exercised; wake-parent itself is real.\n"
        "zx48_handles_close_all_current: xor a : ret\n"
        "zx48_free: xor a : ret\n"
        "zx48_process_restore_tty_owner: ret\n"
        "zx48_panic: ld (p215_panic_code),a : jp $B001\n"
        "\n"
        "; Scheduler/syscall instrumentation stubs.\n"
        "zx48_keyboard_wake_input: ret\n"
        "zx48_kernel_stack_sample: ret\n"
        "zx48_kernel_stack_check: ret\n"
        "kernel_ticks: defs 4,0\n"
        "wall_seconds: defs 4,0\n"
        "wall_revision: dw 0\n"
        "wall_subsecond: db 0\n"
        "wall_valid: db 0\n"
        "p215_panic_code: db 0\n"
        "tty_input_owner: db 0\n"
        "break_pending: db 0\n"
        "current_pid: db 0\n"
        "process_table: defs MAX_PROCESSES*PROC_DESC_SIZE,0\n"
        "p215_end:\n"
        "    ASSERT p215_end <= KERNEL_STACK_START\n"
        "    SAVEBIN \"p215-wait-specific.bin\",p215_start,p215_end-p215_start\n",
        encoding="utf-8",
        newline="\n",
    )
    result = runner(
        [assembler, "--nologo", "--sym=p215-wait-specific.sym", "p215-wait-specific.asm"],
        cwd=build,
        timeout_seconds=30.0,
    )
    require(
        not result.timed_out and result.exit_code == 0,
        f"P2.15 runtime fixture assembly failed: {result.stderr or result.stdout}",
    )
    require(binary.is_file() and 0 < binary.stat().st_size < 0x3B00, "P2.15 runtime fixture missing or too large")
    require(symbols.is_file(), "P2.15 runtime fixture symbols missing")
    return result, binary, symbols


def _call(address: int) -> bytes:
    return b"\xCD" + _word(address)


def _jp(address: int) -> bytes:
    return b"\xC3" + _word(address)


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


def _set_byte(address: int, value: int) -> bytes:
    return bytes((0x3E, value & 0xFF, 0x32)) + _word(address)


def _set_word(address: int, value: int) -> bytes:
    return _ld_hl(value) + b"\x22" + _word(address)


def _expect_byte(address: int, value: int) -> bytes:
    return b"\x3A" + _word(address) + bytes((0xFE, value & 0xFF)) + b"\xC2" + _word(FAIL_PC)


def _expect_word(address: int, value: int) -> bytes:
    return _expect_byte(address, value & 0xFF) + _expect_byte(address + 1, (value >> 8) & 0xFF)


def _expect_hl(value: int) -> bytes:
    return bytes((0x7C, 0xFE, (value >> 8) & 0xFF)) + b"\xC2" + _word(FAIL_PC) + bytes((0x7D, 0xFE, value & 0xFF)) + b"\xC2" + _word(FAIL_PC)


def _fixture_patch(fixture: bytes, *, child_frame: bytes | None = None, child_code: bytes | None = None):
    def patch(ram: bytearray) -> None:
        fixture_start = FIXTURE_CODE - 0x4000
        ram[fixture_start : fixture_start + len(fixture)] = fixture
        if child_frame is not None:
            frame_start = CHILD_FRAME - 0x4000
            ram[frame_start : frame_start + len(child_frame)] = child_frame
        if child_code is not None:
            code_start = CHILD_PC - 0x4000
            ram[code_start : code_start + len(child_code)] = child_code

    return patch


def _parent_init(symbols: dict[str, int]) -> bytes:
    table = symbols["process_table"]
    p1 = table + PROC_DESC_SIZE
    code = bytearray()
    code += _call(symbols["zx48_process_links_init"]) + _jp_c(FAIL_PC)
    code += _set_byte(p1 + PROC_PID, 1)
    code += _set_byte(p1 + PROC_PARENT, 0)
    code += _set_byte(p1 + PROC_STATE, symbols["PROC_RUNNING"])
    code += _set_byte(symbols["current_pid"], 1)
    return bytes(code)


def _link_child(symbols: dict[str, int], pid: int, state: int) -> bytes:
    table = symbols["process_table"]
    child = table + pid * PROC_DESC_SIZE
    code = bytearray(bytes((0x3E, pid & 0xFF)))
    code += _call(symbols["zx48_process_link_child"]) + _jp_c(FAIL_PC)
    code += _set_byte(child + PROC_STATE, state)
    return bytes(code)


def _write_wait1(pid: int) -> bytes:
    code = bytearray()
    code += _set_word(WAIT1, pid & 0xFFFF)
    code += _set_word(WAIT1 + 2, STATUS_PTR)
    code += _set_byte(STATUS_BASE, 0xA5)
    code += _set_byte(STATUS_PTR, 0xCC)
    code += _set_byte(STATUS_PTR + 1, 0x7E)
    return bytes(code)


def _block_wake_resume_reap(root: Path, symbols: dict[str, int], fixture: bytes) -> None:
    table = symbols["process_table"]
    p1 = table + PROC_DESC_SIZE
    p2 = table + 2 * PROC_DESC_SIZE
    generation = symbols["process_generation"]
    wait_pid = symbols["process_wait_pid"]
    wait_generation = symbols["process_wait_generation"]
    wait_status_ptr = symbols["process_wait_status_ptr"]
    child_mask = symbols["process_child_mask"]

    frame = b"\x00" * 10 + _word(CHILD_PC)
    child = bytearray()
    child += _expect_byte(symbols["current_pid"], 2)
    child += _expect_byte(p1 + PROC_STATE, symbols["PROC_WAIT_CHILD"])
    child += _expect_byte(wait_pid + 1, 2)
    child += _expect_word(wait_generation + 2, 1)
    child += _expect_word(wait_status_ptr + 2, STATUS_PTR)
    child += _set_byte(p2 + PROC_EXIT_STATUS, 0x5A)
    child += _set_byte(p2 + PROC_STATE, symbols["PROC_ZOMBIE"])
    child += _set_byte(symbols["process_zombie_pid"], 2)
    child += _set_byte(symbols["process_zombie_parent_pid"], 1)
    child += _set_word(symbols["process_zombie_parent_generation"], 1)
    child += _call(symbols["zx48_process_zombie_wake_parent"])
    child += _expect_byte(p1 + PROC_STATE, symbols["PROC_READY"])
    child += _jp(symbols["zx48_schedule"])

    code = bytearray(b"\xF3" + _ld_sp(TEST_STACK))
    code += _parent_init(symbols)
    code += _link_child(symbols, 2, symbols["PROC_READY"])
    code += _set_word(p2 + PROC_SAVED_SP, CHILD_FRAME)
    code += _write_wait1(2)
    code += _ld_hl(WAIT1)
    code += bytes((0x3E, symbols["SYS_WAIT"] & 0xFF))
    code += _call(symbols["zx48_syscall"]) + _jp_c(FAIL_PC)
    code += _expect_hl(2)
    code += _expect_byte(STATUS_BASE, 0xA5)
    code += _expect_byte(STATUS_PTR, 0x5A)
    code += _expect_byte(STATUS_PTR + 1, 0x7E)
    code += _expect_byte(p2 + PROC_STATE, symbols["PROC_FREE"])
    code += _expect_word(generation + 4, 1)
    code += _expect_byte(child_mask + 1, 0)
    code += _expect_byte(wait_pid + 1, 0xFF)
    code += _expect_word(wait_generation + 2, 0)
    code += _expect_word(wait_status_ptr + 2, 0)
    code += _expect_byte(symbols["current_pid"], 1)
    code += _expect_byte(symbols["p215_panic_code"], 0)
    code += _jp(PASS_PC)
    run_sna(root, bytes(code), patch=_fixture_patch(fixture, child_frame=frame, child_code=bytes(child)))


def _immediate_zombie_reap(root: Path, symbols: dict[str, int], fixture: bytes) -> None:
    table = symbols["process_table"]
    p1 = table + PROC_DESC_SIZE
    p2 = table + 2 * PROC_DESC_SIZE
    code = bytearray(b"\xF3" + _ld_sp(TEST_STACK))
    code += _parent_init(symbols)
    code += _link_child(symbols, 2, symbols["PROC_ZOMBIE"])
    code += _set_byte(p2 + PROC_EXIT_STATUS, 0x33)
    code += _write_wait1(2)
    code += _ld_hl(WAIT1)
    code += bytes((0x3E, symbols["SYS_WAIT"] & 0xFF))
    code += _call(symbols["zx48_syscall"]) + _jp_c(FAIL_PC)
    code += _expect_hl(2)
    code += _expect_byte(STATUS_BASE, 0xA5)
    code += _expect_byte(STATUS_PTR, 0x33)
    code += _expect_byte(STATUS_PTR + 1, 0x7E)
    code += _expect_byte(p2 + PROC_STATE, symbols["PROC_FREE"])
    code += _expect_byte(p1 + PROC_STATE, symbols["PROC_RUNNING"])
    code += _expect_byte(symbols["current_pid"], 1)
    code += _jp(PASS_PC)
    run_sna(root, bytes(code), patch=_fixture_patch(fixture))


def _nonchild_fails_without_block(root: Path, symbols: dict[str, int], fixture: bytes) -> None:
    table = symbols["process_table"]
    p1 = table + PROC_DESC_SIZE
    code = bytearray(b"\xF3" + _ld_sp(TEST_STACK))
    code += _parent_init(symbols)
    code += _link_child(symbols, 2, symbols["PROC_READY"])
    code += _write_wait1(3)
    code += _ld_hl(WAIT1)
    code += bytes((0x3E, symbols["SYS_WAIT"] & 0xFF))
    code += _call(symbols["zx48_syscall"]) + _jp_nc(FAIL_PC)
    code += bytes((0xFE, symbols["E_CHILD"] & 0xFF)) + b"\xC2" + _word(FAIL_PC)
    code += _expect_byte(STATUS_BASE, 0xA5)
    code += _expect_byte(STATUS_PTR, 0xCC)
    code += _expect_byte(STATUS_PTR + 1, 0x7E)
    code += _expect_byte(p1 + PROC_STATE, symbols["PROC_RUNNING"])
    code += _expect_byte(symbols["current_pid"], 1)
    code += _jp(PASS_PC)
    run_sna(root, bytes(code), patch=_fixture_patch(fixture))


def _unrelated_and_reused_child_do_not_wake(root: Path, symbols: dict[str, int], fixture: bytes) -> None:
    table = symbols["process_table"]
    p1 = table + PROC_DESC_SIZE
    p2 = table + 2 * PROC_DESC_SIZE
    p3 = table + 3 * PROC_DESC_SIZE
    generation = symbols["process_generation"]

    code = bytearray(b"\xF3" + _ld_sp(TEST_STACK))
    code += _parent_init(symbols)
    code += _link_child(symbols, 2, symbols["PROC_READY"])
    code += _link_child(symbols, 3, symbols["PROC_READY"])
    code += bytes((0x3E, 2)) + _call(symbols["zx48_process_wait_record_specific"]) + _jp_c(FAIL_PC)
    code += _set_byte(p1 + PROC_STATE, symbols["PROC_WAIT_CHILD"])

    code += _set_byte(p3 + PROC_STATE, symbols["PROC_ZOMBIE"])
    code += _set_byte(symbols["process_zombie_pid"], 3)
    code += _set_byte(symbols["process_zombie_parent_pid"], 1)
    code += _set_word(symbols["process_zombie_parent_generation"], 1)
    code += _call(symbols["zx48_process_zombie_wake_parent"])
    code += _expect_byte(p1 + PROC_STATE, symbols["PROC_WAIT_CHILD"])

    code += bytes((0x3E, 2)) + _call(symbols["zx48_process_unlink_child"]) + _jp_c(FAIL_PC)
    code += _set_byte(p2 + PROC_STATE, symbols["PROC_FREE"])
    code += bytes((0x3E, 2)) + _call(symbols["zx48_process_link_child"]) + _jp_c(FAIL_PC)
    code += _set_byte(p2 + PROC_STATE, symbols["PROC_ZOMBIE"])
    code += _expect_word(generation + 4, 2)
    code += _set_byte(symbols["process_zombie_pid"], 2)
    code += _set_byte(symbols["process_zombie_parent_pid"], 1)
    code += _set_word(symbols["process_zombie_parent_generation"], 1)
    code += _call(symbols["zx48_process_zombie_wake_parent"])
    code += _expect_byte(p1 + PROC_STATE, symbols["PROC_WAIT_CHILD"])
    code += _jp(PASS_PC)
    run_sna(root, bytes(code), patch=_fixture_patch(fixture))


def run(
    root: Path,
    *,
    execute: bool,
    runner: Callable[..., Any],
    project_tool: Callable[[Path, str | Path], Path],
):
    command, binary, symbol_path = _assemble_fixture(root, runner, project_tool)
    names = (
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
    symbols = _symbols(symbol_path, names)
    fixture = binary.read_bytes()
    assertions: list[dict[str, object]] = [
        {"name": "p215-runtime-fixture-assembles-exact-wait-scheduler-wake-composition", "passed": True},
        {"name": "p215-runtime-fixture-fits-below-kernel-stack", "passed": len(fixture) < 0x3B00, "bytes": len(fixture)},
    ]
    if execute:
        _block_wake_resume_reap(root, symbols, fixture)
        assertions.append({"name": "specific-wait-blocks-selectively-wakes-resumes-writes-one-byte-and-reaps", "passed": True})
        _immediate_zombie_reap(root, symbols, fixture)
        assertions.append({"name": "specific-wait-reaps-existing-zombie-without-scheduling", "passed": True})
        _nonchild_fails_without_block(root, symbols, fixture)
        assertions.append({"name": "specific-nonchild-returns-echild-without-blocking-or-status-write", "passed": True})
        _unrelated_and_reused_child_do_not_wake(root, symbols, fixture)
        assertions.append({"name": "unrelated-or-reused-child-cannot-wake-generation-qualified-specific-wait", "passed": True})
    return command, binary, assertions


def main() -> int:
    root = find_root(Path(__file__))
    try:
        command, binary, assertions = run(
            root,
            execute=True,
            runner=run_command,
            project_tool=require_project_tool,
        )
        failed = [item["name"] for item in assertions if item.get("passed") is not True]
        if failed:
            raise Phase2WaitSpecificRuntimeError(f"P2.15 runtime assertions failed: {failed}")
        print(f"P2.15 WAIT SPECIFIC RUNTIME PASS fixture={binary} command_exit={command.exit_code}")
        for item in assertions:
            print(f"PASS {item['name']}")
        return 0
    except (DriverError, OSError, ValueError) as exc:
        print(f"P2.15 WAIT SPECIFIC RUNTIME FAIL: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
