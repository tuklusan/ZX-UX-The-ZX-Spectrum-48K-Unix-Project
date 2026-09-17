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
from fuse_harness import ENTRY_PC, FAIL_PC, PASS_PC, run_sna

FIXTURE_CODE = 0xE000
TEST_STACK = 0x8F00
FRAME_ADDRESS = 0x8A00
SENTINEL_PC = 0x8D00
SENTINEL_MARKER = 0x6900
PROC_DESC_SIZE = 48
PROC_PID = 0
PROC_PARENT = 1
PROC_STATE = 2
PROC_FLAGS = 3
PROC_IMAGE_BASE = 4
PROC_IMAGE_SIZE = 6
PROC_STACK_LOW = 8
PROC_STACK_HIGH = 10
PROC_SAVED_SP = 12
PROC_EXIT_STATUS = 14
PROC_WAIT_OBJECT = 15
PROC_HANDLES = 16
PROC_WAKE_TICK = 24
PROC_CWD = 28
PROC_NAME = 29
PROC_OWNED_BYTES = 40
PROC_ARG_PTR = 42
PROC_ENV_PTR = 44
PROC_PRIVATE_FLAGS = 46
HANDLE_FREE = 0xFF
IMAGE_SIZE = 0x0100
STACK_SIZE = 0x0080
BOOTSTRAP_SIZE = 0x0040
OWNED_SIZE = IMAGE_SIZE + STACK_SIZE + BOOTSTRAP_SIZE


class Phase2KillNeverStartedError(DriverError):
    """Raised when the P2.18 never-started SYS_KILL contract regresses."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Phase2KillNeverStartedError(message)


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
        require(match is not None, f"P2.18 symbol missing from assembler output: {name}")
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


def _ld_bc(value: int) -> bytes:
    return b"\x01" + _word(value)


def _ld_de(value: int) -> bytes:
    return b"\x11" + _word(value)


def _ld_mem_hl(address: int) -> bytes:
    return b"\x22" + _word(address)


def _store_a(address: int) -> bytes:
    return b"\x32" + _word(address)


def _set_byte(address: int, value: int) -> bytes:
    return bytes((0x3E, value & 0xFF, 0x32)) + _word(address)


def _set_word(address: int, value: int) -> bytes:
    return _ld_hl(value) + _ld_mem_hl(address)


def _expect_byte(address: int, value: int) -> bytes:
    return b"\x3A" + _word(address) + bytes((0xFE, value & 0xFF)) + _jp_nz(FAIL_PC)


def _expect_word(address: int, value: int) -> bytes:
    return _expect_byte(address, value & 0xFF) + _expect_byte(address + 1, (value >> 8) & 0xFF)


def _expect_errno(symbols: dict[str, int], target: int, errno_name: str) -> bytes:
    return (
        bytes((0x3E, target & 0xFF))
        + _call(symbols["zx48_process_kill"])
        + _jp_nc(FAIL_PC)
        + bytes((0xFE, symbols[errno_name] & 0xFF))
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
        [assembler, "--nologo", "--lst=../../build/kernel-p218.lst", "--sym=../../build/kernel-p218.sym", "kernel.asm"],
        cwd=root / "v1/src/kernel",
        timeout_seconds=30.0,
    )
    require(
        not result.timed_out and result.exit_code == 0,
        f"P2.18 resident kernel assembly failed: {result.stderr or result.stdout}",
    )
    binary = build / "kernel.bin"
    symbols = build / "kernel-p218.sym"
    require(binary.is_file() and binary.stat().st_size == 8192, "P2.18 resident kernel must remain exactly 8192 bytes")
    require(symbols.is_file(), "P2.18 resident kernel symbols missing")
    return result, binary, symbols


def _assemble_fixture(
    root: Path,
    run_command: Callable[..., Any],
    require_project_tool: Callable[[Path, str | Path], Path],
):
    assembler = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    source = build / "p218-kill-never-started.asm"
    binary = build / "p218-kill-never-started.bin"
    symbols = build / "p218-kill-never-started.sym"
    source.write_text(
        "    DEVICE ZXSPECTRUM48\n"
        "    DEFINE ZX48_P2_18_KILL_ENABLED\n"
        "    INCLUDE \"../include/zx48ux.inc\"\n"
        "    INCLUDE \"../src/kernel/memory.asm\"\n"
        "    INCLUDE \"../src/kernel/process.asm\"\n"
        "    INCLUDE \"../src/kernel/handles.asm\"\n"
        "PANIC_SCHEDULER EQU $03\n"
        f"    ORG ${FIXTURE_CODE:04X}\n"
        "p218_start:\n"
        "    EMIT_KILL_NEVER_STARTED_ROUTINES\n"
        "    EMIT_MEMORY_ROUTINES\n"
        "    EMIT_PROCESS_ROUTINES\n"
        "    EMIT_HANDLE_ROUTINES\n"
        "zx48_schedule: ret\n"
        "zx48_pipe_endpoint_closed: xor a : ret\n"
        "zx48_panic: ld (p218_panic_code),a : ret\n"
        "tty_input_owner: db 0\n"
        "p218_panic_code: db 0\n"
        "p218_end:\n"
        "    ASSERT p218_end <= FAST_RESERVE_START\n"
        "    SAVEBIN \"p218-kill-never-started.bin\",p218_start,p218_end-p218_start\n",
        encoding="utf-8",
        newline="\n",
    )
    result = run_command(
        [assembler, "--nologo", "--lst=p218-kill-never-started.lst", "--sym=p218-kill-never-started.sym", "p218-kill-never-started.asm"],
        cwd=build,
        timeout_seconds=30.0,
    )
    require(
        not result.timed_out and result.exit_code == 0,
        f"P2.18 never-started kill fixture assembly failed: {result.stderr or result.stdout}",
    )
    require(binary.is_file() and 0 < binary.stat().st_size <= 0x1D00, "P2.18 fixture missing or overlaps FAST reserve")
    require(symbols.is_file(), "P2.18 fixture symbols missing")
    return result, binary, symbols


def _fixture_patch(fixture: bytes):
    frame = b"\x00" * 10 + _word(SENTINEL_PC)
    sentinel = bytes((0x3E, 0xA5, 0x32)) + _word(SENTINEL_MARKER) + _jp(FAIL_PC)

    def patch(ram: bytearray) -> None:
        fixture_start = FIXTURE_CODE - 0x4000
        ram[fixture_start : fixture_start + len(fixture)] = fixture
        frame_start = FRAME_ADDRESS - 0x4000
        ram[frame_start : frame_start + len(frame)] = frame
        sentinel_start = SENTINEL_PC - 0x4000
        ram[sentinel_start : sentinel_start + len(sentinel)] = sentinel

    return patch


def _setup_never_started_child(symbols: dict[str, int], *, with_handle: bool) -> bytes:
    table = symbols["process_table"]
    p2 = table + 2 * PROC_DESC_SIZE
    code = bytearray()
    code += _call(symbols["zx48_memory_init"])
    code += _call(symbols["zx48_process_init"])
    code += _call(symbols["zx48_process_prepare_pid1"]) + _jp_c(FAIL_PC)
    code += _call(symbols["zx48_handles_init"])
    code += _set_byte(symbols["current_pid"], 1)
    code += _call(symbols["zx48_process_reserve_slot"]) + _jp_c(FAIL_PC)
    code += bytes((0xFE, 2)) + _jp_nz(FAIL_PC)

    code += _ld_bc(IMAGE_SIZE) + bytes((0x3E, symbols["ALLOC_ANY"])) + _call(symbols["zx48_alloc"]) + _jp_c(FAIL_PC)
    code += _ld_mem_hl(p2 + PROC_IMAGE_BASE)
    code += _set_word(p2 + PROC_IMAGE_SIZE, IMAGE_SIZE)

    code += _ld_bc(STACK_SIZE) + bytes((0x3E, symbols["ALLOC_FAST_REQUIRED"])) + _call(symbols["zx48_alloc"]) + _jp_c(FAIL_PC)
    code += _ld_mem_hl(p2 + PROC_STACK_LOW)
    code += _ld_de(STACK_SIZE) + b"\x19" + _ld_mem_hl(p2 + PROC_STACK_HIGH)

    code += _ld_bc(BOOTSTRAP_SIZE) + bytes((0x3E, symbols["ALLOC_ANY"])) + _call(symbols["zx48_alloc"]) + _jp_c(FAIL_PC)
    code += _ld_mem_hl(p2 + PROC_ARG_PTR)
    code += _ld_de(0x20) + b"\x19" + _ld_mem_hl(p2 + PROC_ENV_PTR)

    code += _set_word(p2 + PROC_OWNED_BYTES, OWNED_SIZE)
    code += _set_word(p2 + PROC_SAVED_SP, FRAME_ADDRESS)
    code += _set_byte(p2 + PROC_PRIVATE_FLAGS, 0)
    code += _set_byte(p2 + PROC_FLAGS, 0)
    code += _set_byte(p2 + PROC_CWD, 6)
    code += _set_byte(p2 + PROC_NAME, 0x51)
    code += _set_byte(p2 + PROC_STATE, symbols["PROC_READY"])

    if with_handle:
        code += bytes((0x06, symbols["OD_KIND_NULL"], 0x0E, symbols["O_READ"], 0x16, 0x33))
        code += _call(symbols["zx48_od_create"]) + _jp_c(FAIL_PC)
        code += _store_a(p2 + PROC_HANDLES)
    return bytes(code)


def _positive(root: Path, symbols: dict[str, int], fixture: bytes) -> None:
    table = symbols["process_table"]
    p2 = table + 2 * PROC_DESC_SIZE
    code = bytearray(b"\xF3" + _ld_sp(TEST_STACK))
    code += _set_byte(SENTINEL_MARKER, 0)
    code += _setup_never_started_child(symbols, with_handle=True)
    code += bytes((0x3E, 2)) + _call(symbols["zx48_process_kill"]) + _jp_c(FAIL_PC)
    code += bytes((0xFE, 0)) + _jp_nz(FAIL_PC)
    code += _expect_byte(symbols["current_pid"], 1)
    code += _expect_byte(p2 + PROC_PID, 2)
    code += _expect_byte(p2 + PROC_PARENT, 1)
    code += _expect_byte(p2 + PROC_STATE, symbols["PROC_ZOMBIE"])
    code += _expect_byte(p2 + PROC_EXIT_STATUS, 130)
    code += _expect_byte(p2 + PROC_CWD, 6)
    code += _expect_byte(p2 + PROC_NAME, 0x51)
    for address in (
        p2 + PROC_IMAGE_BASE,
        p2 + PROC_IMAGE_SIZE,
        p2 + PROC_STACK_LOW,
        p2 + PROC_STACK_HIGH,
        p2 + PROC_SAVED_SP,
        p2 + PROC_OWNED_BYTES,
        p2 + PROC_ARG_PTR,
        p2 + PROC_ENV_PTR,
    ):
        code += _expect_word(address, 0)
    code += _expect_byte(p2 + PROC_FLAGS, 0)
    code += _expect_byte(p2 + PROC_PRIVATE_FLAGS, 0)
    code += _expect_byte(p2 + PROC_WAIT_OBJECT, 0)
    for offset in range(4):
        code += _expect_byte(p2 + PROC_WAKE_TICK + offset, 0)
    for handle in range(8):
        code += _expect_byte(p2 + PROC_HANDLES + handle, HANDLE_FREE)
    code += _expect_byte(symbols["open_description_table"], 0)
    code += _expect_byte(symbols["open_description_table"] + 2, 0)
    code += _expect_word(symbols["memory_live_allocations"], 0)
    code += _expect_word(symbols["memory_free_extents"], symbols["ARENA_START"])
    code += _expect_word(symbols["memory_free_extents"] + 2, symbols["ARENA_SIZE"])
    code += _expect_byte(SENTINEL_MARKER, 0)
    code += _expect_byte(symbols["p218_panic_code"], 0)
    code += _jp(PASS_PC)
    run_sna(root, bytes(code), patch=_fixture_patch(fixture))


def _negative_targets_and_permissions(root: Path, symbols: dict[str, int], fixture: bytes) -> None:
    table = symbols["process_table"]
    p2 = table + 2 * PROC_DESC_SIZE
    p3 = table + 3 * PROC_DESC_SIZE
    code = bytearray(b"\xF3" + _ld_sp(TEST_STACK))
    code += _set_byte(SENTINEL_MARKER, 0)
    code += _setup_never_started_child(symbols, with_handle=True)
    code += _set_byte(p3 + PROC_STATE, symbols["PROC_RUNNING"])
    code += _set_byte(p3 + PROC_PARENT, 1)
    code += _set_byte(symbols["current_pid"], 3)
    code += _expect_errno(symbols, 2, "E_PERM")
    code += _expect_byte(p2 + PROC_STATE, symbols["PROC_READY"])
    code += _expect_byte(p2 + PROC_EXIT_STATUS, 0)
    code += _expect_byte(p2 + PROC_HANDLES, 0)
    code += _expect_byte(symbols["open_description_table"], symbols["OD_KIND_NULL"])
    code += _expect_byte(symbols["open_description_table"] + 2, 1)
    code += _expect_word(symbols["memory_live_allocations"], 3)

    code += _set_byte(symbols["current_pid"], 1)
    code += _expect_errno(symbols, 0, "E_PERM")
    code += _expect_errno(symbols, 1, "E_PERM")
    code += _expect_errno(symbols, 7, "E_NOENT")
    code += _set_byte(p2 + PROC_STATE, symbols["PROC_ZOMBIE"])
    code += _expect_errno(symbols, 2, "E_NOENT")
    code += _expect_word(symbols["memory_live_allocations"], 3)
    code += _expect_byte(p2 + PROC_HANDLES, 0)
    code += _expect_byte(SENTINEL_MARKER, 0)
    code += _expect_byte(symbols["p218_panic_code"], 0)
    code += _jp(PASS_PC)
    run_sna(root, bytes(code), patch=_fixture_patch(fixture))


def _source_contract(root: Path) -> list[dict[str, object]]:
    process = (root / "v1/src/kernel/process.asm").read_text(encoding="utf-8")
    syscall = (root / "v1/src/kernel/syscall.asm").read_text(encoding="utf-8")
    core_start = process.index("    MACRO EMIT_PROCESS_ROUTINES")
    core_end = process.index("    ENDM\n", core_start)
    core = process[core_start:core_end]
    kill_start = core.index("zx48_process_kill:\n")
    wait_start = core.index("zx48_process_wait:\n", kill_start)
    kill = core[kill_start:wait_start]
    helper_start = process.index("    MACRO EMIT_KILL_NEVER_STARTED_ROUTINES")
    helper_end = process.index("    ENDM\n", helper_start)
    helper = process[helper_start:helper_end]
    close_handles = helper.index("zx48_process_kill_close_handles:")
    free_bootstrap = helper.index("zx48_process_kill_free_bootstrap:")
    free_stack = helper.index("zx48_process_kill_free_stack:")
    free_image = helper.index("zx48_process_kill_free_image:")
    publish = helper.index("zx48_process_kill_publish:")
    syscall_start = syscall.index("zx48_sys_kill:\n")
    syscall_end = syscall.index("zx48_sys_close:\n", syscall_start)
    syscall_kill = syscall[syscall_start:syscall_end]
    return [
        {
            "name": "sys-kill-register-contract-rejects-nonzero-h-and-passes-l-target",
            "passed": all(token in syscall_kill for token in ("ld hl,(syscall_arg_hl)", "ld a,h", "jp nz,zx48_sys_invalid", "ld a,l", "call zx48_process_kill")),
        },
        {
            "name": "pid0-pid1-zombie-and-nonexistent-targets-remain-rejected",
            "passed": "cp 2\n    jr c,zx48_process_perm" in kill and "call zx48_process_lookup" in kill and "cp PROC_ZOMBIE\n    jp z,zx48_process_noent" in kill,
        },
        {
            "name": "permission-remains-pid1-or-direct-parent-only",
            "passed": all(token in kill for token in ("ld a,(current_pid)", "cp 1", "ld a,(ix+PROC_PARENT)", "jr nz,zx48_process_perm")),
        },
        {
            "name": "never-started-path-is-gated-without-changing-resident-fallback",
            "passed": "IFDEF ZX48_P2_18_KILL_ENABLED" in kill and "jp z,zx48_process_kill_never_started" in kill and all(token in kill for token in ("ld (ix+PROC_EXIT_STATUS),130", "ld (ix+PROC_STATE),PROC_ZOMBIE", "zx48_process_kill_started:")),
        },
        {
            "name": "p218-helper-is-separate-composable-emitter",
            "passed": helper_start > core_end and "ZX48_P2_18_KILL_ENABLED" not in helper,
        },
        {
            "name": "owned-shape-is-validated-before-first-destructive-release",
            "passed": helper.index("ld (process_kill_bootstrap_size),hl") < close_handles and "sbc hl,de" in helper[:close_handles],
        },
        {
            "name": "target-handles-close-before-private-extent-free",
            "passed": close_handles < free_bootstrap < free_stack < free_image < publish and "call zx48_od_release" in helper[close_handles:free_bootstrap],
        },
        {
            "name": "private-extents-free-bootstrap-stack-image-exactly-once",
            "passed": helper.count("call zx48_free") == 3 and all(token in helper for token in ("ld hl,(process_kill_bootstrap_base)", "ld bc,(process_kill_bootstrap_size)", "ld hl,(process_kill_stack_base)", "ld bc,(process_kill_stack_size)", "ld hl,(process_kill_image_base)", "ld bc,(process_kill_image_size)")),
        },
        {
            "name": "zombie-status130-publishes-only-after-resource-release",
            "passed": free_image < publish < helper.index("ld (ix+PROC_EXIT_STATUS),a") < helper.index("ld (ix+PROC_STATE),PROC_ZOMBIE"),
        },
        {
            "name": "never-started-kill-clears-stale-resource-resume-fields-but-retains-identity",
            "passed": all(token in helper[publish:] for token in ("ld (ix+PROC_IMAGE_BASE),a", "ld (ix+PROC_IMAGE_SIZE),a", "ld (ix+PROC_STACK_LOW),a", "ld (ix+PROC_STACK_HIGH),a", "ld (ix+PROC_SAVED_SP),a", "ld (ix+PROC_OWNED_BYTES),a", "ld (ix+PROC_ARG_PTR),a", "ld (ix+PROC_ENV_PTR),a")) and "ld (ix+PROC_PID),a" not in helper[publish:] and "ld (ix+PROC_PARENT),a" not in helper[publish:],
        },
        {
            "name": "never-started-kill-does-not-schedule-or-substitute-current-pid",
            "passed": "zx48_schedule" not in helper and "ld (current_pid)" not in helper,
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
    if step != "P2.18":
        raise DriverError(f"Phase-2 never-started kill step is not registered: {step}")

    assertions = _source_contract(root)
    require(SENTINEL_PC + 8 <= ENTRY_PC, "P2.18 child-PC sentinel overlaps test program entry")
    assertions.append({
        "name": "child-pc-sentinel-is-disjoint-from-test-program",
        "passed": True,
        "sentinel_pc": f"0x{SENTINEL_PC:04X}",
        "sentinel_end": f"0x{SENTINEL_PC + 7:04X}",
        "test_entry": f"0x{ENTRY_PC:04X}",
    })
    failed = [item["name"] for item in assertions if item["passed"] is not True]
    require(not failed, f"static P2.18 contract failures: {failed}")

    kernel_command, kernel_binary, kernel_symbols = _assemble_kernel(root, run_command, require_project_tool)
    fixture_command, fixture_binary, fixture_symbols = _assemble_fixture(root, run_command, require_project_tool)
    kernel_values = _symbols(kernel_symbols, ("kernel_ordinary_used_end", "KERNEL_CODE_END"))
    free_bytes = kernel_values["KERNEL_CODE_END"] + 1 - kernel_values["kernel_ordinary_used_end"]
    resident_symbols = kernel_symbols.read_text(encoding="utf-8", errors="replace")
    require(
        re.search(r"^zx48_process_kill_never_started:\s+equ\s+0x", resident_symbols, re.IGNORECASE | re.MULTILINE) is None,
        "P2.18 staged never-started helper leaked into the resident kernel",
    )
    assertions.append({
        "name": "staged-never-started-helper-remains-outside-resident-kernel",
        "passed": True,
        "used_end": f"0x{kernel_values['kernel_ordinary_used_end']:04X}",
        "code_end": f"0x{kernel_values['KERNEL_CODE_END']:04X}",
        "free_bytes": free_bytes,
    })

    names = (
        "zx48_memory_init", "zx48_alloc", "zx48_process_init", "zx48_process_prepare_pid1",
        "zx48_process_reserve_slot", "zx48_handles_init", "zx48_od_create", "zx48_process_kill",
        "zx48_process_kill_never_started",
        "process_table", "current_pid", "memory_live_allocations", "memory_free_extents",
        "open_description_table", "p218_panic_code", "MAX_PROCESSES", "PROC_DESC_SIZE",
        "PROC_READY", "PROC_RUNNING", "PROC_ZOMBIE", "ALLOC_ANY", "ALLOC_FAST_REQUIRED",
        "ARENA_START", "ARENA_SIZE", "OD_KIND_NULL", "O_READ", "E_PERM", "E_NOENT",
    )
    symbols = _symbols(fixture_symbols, names)
    require(symbols["MAX_PROCESSES"] == 8 and symbols["PROC_DESC_SIZE"] == PROC_DESC_SIZE, "P2.18 process ABI changed")
    fixture = fixture_binary.read_bytes()
    dispatch_bytes = b"\xCA" + _word(symbols["zx48_process_kill_never_started"])
    dispatch_count = fixture.count(dispatch_bytes)
    require(dispatch_count == 1, f"P2.18 assembled dispatch must contain exactly one JP Z to never-started helper, got {dispatch_count}")
    assertions.append({"name": "assembled-fixture-dispatches-to-never-started-helper", "passed": True, "dispatch_bytes": dispatch_bytes.hex()})
    if action == "test":
        _positive(root, symbols, fixture)
        _negative_targets_and_permissions(root, symbols, fixture)
        assertions.extend([
            {"name": "never-started-child-zombies-at-status130-without-running-user-pc", "passed": True},
            {"name": "never-started-child-releases-every-handle-and-private-allocation", "passed": True},
            {"name": "unauthorized-pid0-pid1-free-and-zombie-kills-are-rejected-without-teardown", "passed": True},
        ])

    return [kernel_command, fixture_command], {
        "v1/build/kernel.bin": sha256_file(kernel_binary),
        "v1/build/p218-kill-never-started.bin": sha256_file(fixture_binary),
        "v1/src/kernel/process.asm": sha256_file(root / "v1/src/kernel/process.asm"),
        "v1/src/kernel/syscall.asm": sha256_file(root / "v1/src/kernel/syscall.asm"),
        "v1/tools-host/test-driver/phase2_kill_never_started.py": sha256_file(root / "v1/tools-host/test-driver/phase2_kill_never_started.py"),
        "v1/tools-host/test-driver/run.py": sha256_file(root / "v1/tools-host/test-driver/run.py"),
        "v1/tools-host/test-driver/phase2_gate.py": sha256_file(root / "v1/tools-host/test-driver/phase2_gate.py"),
    }, assertions
