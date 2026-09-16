#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path.cwd()

PROCESS_APPEND = r'''

; P2.14 resource-safe ZOMBIE transition. This emitter composes after the P2.13
; generation-qualified linkage emitter. The exiting child remains RUNNING while
; fallible resource teardown occurs, so handle lookup remains valid. Only after
; all private resources are released are stale ownership pointers cleared and
; the durable descriptor published as ZOMBIE with its exit status retained.
    MACRO EMIT_ZOMBIE_TRANSITION_ROUTINES
ZX48_P2_14_ZOMBIE_EMITTED EQU 1

; A=exit status. Current PID must be a live spawned child (PID2..PID7).
zx48_process_exit_to_zombie:
    ld (process_zombie_status),a
    ld a,(current_pid)
    cp 2
    jp c,zx48_process_zombie_panic
    cp MAX_PROCESSES
    jp nc,zx48_process_zombie_panic
    ld (process_zombie_pid),a
    call zx48_process_links_desc_ptr
    jp c,zx48_process_zombie_panic
    ld a,(ix+PROC_STATE)
    cp PROC_RUNNING
    jp nz,zx48_process_zombie_panic

    ld a,(ix+PROC_PARENT)
    ld (process_zombie_parent_pid),a
    ld a,(process_zombie_pid)
    call zx48_process_parent_generation_ptr
    jp c,zx48_process_zombie_panic
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld a,d
    or e
    jp z,zx48_process_zombie_panic
    ld (process_zombie_parent_generation),de

    ld l,(ix+PROC_IMAGE_BASE)
    ld h,(ix+PROC_IMAGE_BASE+1)
    ld (process_zombie_image_base),hl
    ld l,(ix+PROC_IMAGE_SIZE)
    ld h,(ix+PROC_IMAGE_SIZE+1)
    ld (process_zombie_image_size),hl
    ld l,(ix+PROC_STACK_LOW)
    ld h,(ix+PROC_STACK_LOW+1)
    ld (process_zombie_stack_base),hl
    ld e,(ix+PROC_STACK_HIGH)
    ld d,(ix+PROC_STACK_HIGH+1)
    or a
    ex de,hl
    sbc hl,de
    jp c,zx48_process_zombie_panic
    ld a,h
    or l
    jp z,zx48_process_zombie_panic
    bit 0,l
    jp nz,zx48_process_zombie_panic
    ld (process_zombie_stack_size),hl
    ld l,(ix+PROC_ARG_PTR)
    ld h,(ix+PROC_ARG_PTR+1)
    ld (process_zombie_bootstrap_base),hl
    ld l,(ix+PROC_OWNED_BYTES)
    ld h,(ix+PROC_OWNED_BYTES+1)
    ld (process_zombie_owned_bytes),hl

    ; Validate the complete private-extent shape before the first destructive
    ; operation. Spawn/exec publish rounded even sizes and OWNED_BYTES is their
    ; exact image+stack+bootstrap sum.
    ld hl,(process_zombie_image_base)
    ld a,h
    or l
    jp z,zx48_process_zombie_panic
    bit 0,l
    jp nz,zx48_process_zombie_panic
    ld hl,(process_zombie_image_size)
    ld a,h
    or l
    jp z,zx48_process_zombie_panic
    bit 0,l
    jp nz,zx48_process_zombie_panic
    ld hl,(process_zombie_stack_base)
    ld a,h
    or l
    jp z,zx48_process_zombie_panic
    bit 0,l
    jp nz,zx48_process_zombie_panic
    ld hl,(process_zombie_bootstrap_base)
    ld a,h
    or l
    jp z,zx48_process_zombie_panic
    bit 0,l
    jp nz,zx48_process_zombie_panic
    ld hl,(process_zombie_owned_bytes)
    ld a,h
    or l
    jp z,zx48_process_zombie_panic
    bit 0,l
    jp nz,zx48_process_zombie_panic
    ld de,(process_zombie_image_size)
    or a
    sbc hl,de
    jp c,zx48_process_zombie_panic
    ld de,(process_zombie_stack_size)
    or a
    sbc hl,de
    jp c,zx48_process_zombie_panic
    ld a,h
    or l
    jp z,zx48_process_zombie_panic
    bit 0,l
    jp nz,zx48_process_zombie_panic
    ld (process_zombie_bootstrap_size),hl

    ; Architecture §7.5 ordering: close handles, release private allocations,
    ; then publish status/ZOMBIE. Any allocator inconsistency is kernel-fatal;
    ; silently retaining or double-freeing memory is not an exit result.
    call zx48_handles_close_all_current
    jp c,zx48_process_zombie_panic
zx48_process_zombie_free_bootstrap:
    ld hl,(process_zombie_bootstrap_base)
    ld bc,(process_zombie_bootstrap_size)
    call zx48_free
    jp c,zx48_process_zombie_panic
zx48_process_zombie_free_stack:
    ld hl,(process_zombie_stack_base)
    ld bc,(process_zombie_stack_size)
    call zx48_free
    jp c,zx48_process_zombie_panic
zx48_process_zombie_free_image:
    ld hl,(process_zombie_image_base)
    ld bc,(process_zombie_image_size)
    call zx48_free
    jp c,zx48_process_zombie_panic

zx48_process_zombie_publish:
    ld a,(process_zombie_pid)
    call zx48_process_links_desc_ptr
    jp c,zx48_process_zombie_panic
    xor a
    ld (ix+PROC_IMAGE_BASE),a
    ld (ix+PROC_IMAGE_BASE+1),a
    ld (ix+PROC_IMAGE_SIZE),a
    ld (ix+PROC_IMAGE_SIZE+1),a
    ld (ix+PROC_STACK_LOW),a
    ld (ix+PROC_STACK_LOW+1),a
    ld (ix+PROC_STACK_HIGH),a
    ld (ix+PROC_STACK_HIGH+1),a
    ld (ix+PROC_SAVED_SP),a
    ld (ix+PROC_SAVED_SP+1),a
    ld (ix+PROC_WAIT_OBJECT),a
    ld (ix+PROC_WAKE_TICK+0),a
    ld (ix+PROC_WAKE_TICK+1),a
    ld (ix+PROC_WAKE_TICK+2),a
    ld (ix+PROC_WAKE_TICK+3),a
    ld (ix+PROC_OWNED_BYTES),a
    ld (ix+PROC_OWNED_BYTES+1),a
    ld (ix+PROC_ARG_PTR),a
    ld (ix+PROC_ARG_PTR+1),a
    ld (ix+PROC_ENV_PTR),a
    ld (ix+PROC_ENV_PTR+1),a
    ld a,(process_zombie_status)
    ld (ix+PROC_EXIT_STATUS),a
    ld (ix+PROC_STATE),PROC_ZOMBIE
    call zx48_process_zombie_wake_parent
    call zx48_process_restore_tty_owner
    jp zx48_schedule

; Wake only the same generation-qualified parent identity recorded by P2.13.
; A recycled numeric parent PID must not receive a wake belonging to an older
; parent generation.
zx48_process_zombie_wake_parent:
    ld a,(process_zombie_parent_pid)
    cp HANDLE_FREE
    ret z
    cp MAX_PROCESSES
    ret nc
    call zx48_process_generation_get
    ret c
    ld hl,(process_zombie_parent_generation)
    or a
    sbc hl,de
    ret nz
    ld a,(process_zombie_parent_pid)
    call zx48_process_links_desc_ptr
    ret c
    ld a,(ix+PROC_STATE)
    cp PROC_WAIT_CHILD
    ret nz
    ld (ix+PROC_STATE),PROC_READY
    xor a
    ret

zx48_process_zombie_panic:
    ld a,PANIC_SCHEDULER
    jp zx48_panic

process_zombie_pid: db 0
process_zombie_status: db 0
process_zombie_parent_pid: db HANDLE_FREE
process_zombie_parent_generation: dw 0
process_zombie_image_base: dw 0
process_zombie_image_size: dw 0
process_zombie_stack_base: dw 0
process_zombie_stack_size: dw 0
process_zombie_bootstrap_base: dw 0
process_zombie_bootstrap_size: dw 0
process_zombie_owned_bytes: dw 0
    ENDM
'''

PHASE2_ZOMBIE = r'''#!/usr/bin/env python3
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
TEST_STACK = 0x8F00
FRAME_ADDRESS = 0x8800
VERIFY_PC = 0x9400
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
PROC_WAIT_OBJECT = 15
PROC_HANDLES = 16
PROC_WAKE_TICK = 24
PROC_CWD = 28
PROC_NAME = 29
PROC_OWNED_BYTES = 40
PROC_ARG_PTR = 42
PROC_ENV_PTR = 44
HANDLE_FREE = 0xFF
IMAGE_SIZE = 0x0100
STACK_SIZE = 0x0080
BOOTSTRAP_SIZE = 0x0040
OWNED_SIZE = IMAGE_SIZE + STACK_SIZE + BOOTSTRAP_SIZE


class Phase2ZombieError(DriverError):
    """Raised when the P2.14 resource-safe ZOMBIE contract regresses."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Phase2ZombieError(message)


def _word(value: int) -> bytes:
    return bytes((value & 0xFF, (value >> 8) & 0xFF))


def _symbols(path: Path, names: tuple[str, ...]) -> dict[str, int]:
    text = path.read_text(encoding="utf-8", errors="replace")
    found: dict[str, int] = {}
    for name in names:
        pattern = re.compile(rf"^{re.escape(name)}:\s+equ\s+0x([0-9A-Fa-f]+)\s*$", re.IGNORECASE | re.MULTILINE)
        match = pattern.search(text)
        require(match is not None, f"P2.14 symbol missing from assembler output: {name}")
        found[name] = int(match.group(1), 16)
    return found


def _call(address: int) -> bytes:
    return b"\xCD" + _word(address)


def _jp(address: int) -> bytes:
    return b"\xC3" + _word(address)


def _jp_c(address: int) -> bytes:
    return b"\xDA" + _word(address)


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


def _set_byte(address: int, value: int) -> bytes:
    return bytes((0x3E, value & 0xFF, 0x32)) + _word(address)


def _set_word(address: int, value: int) -> bytes:
    return _ld_hl(value) + _ld_mem_hl(address)


def _expect_byte(address: int, value: int) -> bytes:
    return b"\x3A" + _word(address) + bytes((0xFE, value & 0xFF)) + _jp_nz(FAIL_PC)


def _expect_word(address: int, value: int) -> bytes:
    return _expect_byte(address, value & 0xFF) + _expect_byte(address + 1, (value >> 8) & 0xFF)


def _assemble_kernel(root: Path, run_command: Callable[..., Any], require_project_tool: Callable[[Path, str | Path], Path]):
    assembler = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    result = run_command(
        [assembler, "--nologo", "--lst=../../build/kernel-p214.lst", "--sym=../../build/kernel-p214.sym", "kernel.asm"],
        cwd=root / "v1/src/kernel",
        timeout_seconds=30.0,
    )
    require(not result.timed_out and result.exit_code == 0, f"P2.14 resident kernel assembly failed: {result.stderr or result.stdout}")
    binary = build / "kernel.bin"
    symbols = build / "kernel-p214.sym"
    require(binary.is_file() and binary.stat().st_size == 8192, "P2.14 resident kernel must remain exactly 8192 bytes")
    require(symbols.is_file(), "P2.14 resident kernel symbols missing")
    return result, binary, symbols


def _assemble_fixture(root: Path, run_command: Callable[..., Any], require_project_tool: Callable[[Path, str | Path], Path]):
    assembler = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    source = build / "p214-zombie.asm"
    binary = build / "p214-zombie.bin"
    symbols = build / "p214-zombie.sym"
    source.write_text(
        "    DEVICE ZXSPECTRUM48\n"
        "    INCLUDE \"../include/zx48ux.inc\"\n"
        "    INCLUDE \"../src/kernel/memory.asm\"\n"
        "    INCLUDE \"../src/kernel/process.asm\"\n"
        "    INCLUDE \"../src/kernel/handles.asm\"\n"
        "    INCLUDE \"../src/kernel/scheduler.asm\"\n"
        f"    ORG ${FIXTURE_CODE:04X}\n"
        "p214_start:\n"
        "    EMIT_MEMORY_ROUTINES\n"
        "    EMIT_PROCESS_ROUTINES\n"
        "    EMIT_HANDLE_ROUTINES\n"
        "    EMIT_PARENT_CHILD_ROUTINES\n"
        "    EMIT_ZOMBIE_TRANSITION_ROUTINES\n"
        "    EMIT_SCHEDULER_ROUTINES\n"
        "zx48_pipe_endpoint_closed: xor a\n    ret\n"
        "zx48_panic:\n    ld (p214_panic_code),a\n    ret\n"
        "zx48_keyboard_wake_input: ret\n"
        "zx48_kernel_stack_sample: ret\n"
        "zx48_kernel_stack_check: ret\n"
        "zx48_syscall_resume_ok: ret\n"
        "zx48_syscall_resume_intr: ret\n"
        "kernel_ticks: defs 4,0\n"
        "syscall_frame_sp: dw 0\n"
        "tty_input_owner: db 0\n"
        "p214_panic_code: db 0\n"
        "p214_end:\n"
        "    ASSERT p214_end <= FAST_RESERVE_START\n"
        "    SAVEBIN \"p214-zombie.bin\",p214_start,p214_end-p214_start\n",
        encoding="utf-8",
        newline="\n",
    )
    result = run_command(
        [assembler, "--nologo", "--sym=p214-zombie.sym", "p214-zombie.asm"],
        cwd=build,
        timeout_seconds=30.0,
    )
    require(not result.timed_out and result.exit_code == 0, f"P2.14 ZOMBIE fixture assembly failed: {result.stderr or result.stdout}")
    require(binary.is_file() and 0 < binary.stat().st_size <= 0x1D00, "P2.14 fixture missing or overlaps FAST reserve")
    require(symbols.is_file(), "P2.14 fixture symbols missing")
    return result, binary, symbols


def _fixture_patch(fixture: bytes, *, schedule: int | None = None, frame: bytes | None = None, verifier: bytes | None = None):
    patched = bytearray(fixture)
    if schedule is not None:
        offset = schedule - FIXTURE_CODE
        require(0 <= offset < len(patched), "P2.14 scheduler label outside fixture")
        patched[offset] = 0xC9

    def patch(ram: bytearray) -> None:
        start = FIXTURE_CODE - 0x4000
        ram[start : start + len(patched)] = patched
        if frame is not None:
            frame_start = FRAME_ADDRESS - 0x4000
            ram[frame_start : frame_start + len(frame)] = frame
        if verifier is not None:
            verify_start = VERIFY_PC - 0x4000
            ram[verify_start : verify_start + len(verifier)] = verifier

    return patch


def _setup_child(symbols: dict[str, int], *, with_handle: bool) -> bytes:
    table = symbols["process_table"]
    p1 = table + PROC_DESC_SIZE
    p2 = table + 2 * PROC_DESC_SIZE
    code = bytearray()
    code += _call(symbols["zx48_memory_init"])
    code += _call(symbols["zx48_process_init"])
    code += _call(symbols["zx48_process_prepare_pid1"])
    code += _call(symbols["zx48_handles_init"])
    code += _call(symbols["zx48_process_links_init"]) + _jp_c(FAIL_PC)
    code += _set_byte(symbols["current_pid"], 1)
    code += b"\x3E\x02" + _call(symbols["zx48_process_link_child"]) + _jp_c(FAIL_PC)
    for handle in range(8):
        code += _set_byte(p2 + PROC_HANDLES + handle, HANDLE_FREE)
    code += _set_byte(p2 + PROC_STATE, symbols["PROC_RUNNING"])
    code += _set_byte(p2 + PROC_CWD, 6)
    code += _set_byte(p2 + PROC_NAME, 0x51)

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
    code += _set_word(p2 + PROC_SAVED_SP, 0x8120)

    code += _set_byte(symbols["current_pid"], 2)
    if with_handle:
        code += bytes((0x06, symbols["OD_KIND_NULL"], 0x0E, symbols["O_READ"], 0x16, 0x33))
        code += _call(symbols["zx48_od_create"]) + _jp_c(FAIL_PC)
        code += b"\x4F\xAF" + _call(symbols["zx48_handle_install"]) + _jp_c(FAIL_PC)
    code += _set_byte(p1 + PROC_STATE, symbols["PROC_WAIT_CHILD"])
    code += _set_byte(symbols["tty_input_owner"], 2)
    return bytes(code)


def _positive(root: Path, symbols: dict[str, int], fixture: bytes) -> None:
    table = symbols["process_table"]
    p1 = table + PROC_DESC_SIZE
    p2 = table + 2 * PROC_DESC_SIZE
    code = bytearray(b"\xF3" + _ld_sp(TEST_STACK))
    code += _setup_child(symbols, with_handle=True)
    code += b"\x3E\x5A" + _call(symbols["zx48_process_exit_to_zombie"])
    code += _expect_byte(p2 + PROC_PID, 2)
    code += _expect_byte(p2 + PROC_PARENT, 1)
    code += _expect_byte(p2 + PROC_STATE, symbols["PROC_ZOMBIE"])
    code += _expect_byte(p2 + PROC_EXIT_STATUS, 0x5A)
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
    code += _expect_byte(p1 + PROC_STATE, symbols["PROC_READY"])
    code += _expect_byte(symbols["tty_input_owner"], 1)
    code += _expect_byte(symbols["p214_panic_code"], 0)
    code += _jp(PASS_PC)
    run_sna(root, bytes(code), patch=_fixture_patch(fixture, schedule=symbols["zx48_schedule"]))


def _stale_parent_generation_does_not_wake(root: Path, symbols: dict[str, int], fixture: bytes) -> None:
    table = symbols["process_table"]
    p1 = table + PROC_DESC_SIZE
    p2 = table + 2 * PROC_DESC_SIZE
    code = bytearray(b"\xF3" + _ld_sp(TEST_STACK))
    code += _setup_child(symbols, with_handle=False)
    code += _set_word(symbols["process_generation"] + 2, 2)
    code += b"\x3E\x66" + _call(symbols["zx48_process_exit_to_zombie"])
    code += _expect_byte(p2 + PROC_STATE, symbols["PROC_ZOMBIE"])
    code += _expect_byte(p2 + PROC_EXIT_STATUS, 0x66)
    code += _expect_byte(p1 + PROC_STATE, symbols["PROC_WAIT_CHILD"])
    code += _expect_word(symbols["memory_live_allocations"], 0)
    code += _expect_byte(symbols["p214_panic_code"], 0)
    code += _jp(PASS_PC)
    run_sna(root, bytes(code), patch=_fixture_patch(fixture, schedule=symbols["zx48_schedule"]))


def _zombie_never_scheduled(root: Path, symbols: dict[str, int], fixture: bytes) -> None:
    table = symbols["process_table"]
    p1 = table + PROC_DESC_SIZE
    p2 = table + 2 * PROC_DESC_SIZE
    p3 = table + 3 * PROC_DESC_SIZE
    verifier = bytearray()
    verifier += _expect_byte(symbols["current_pid"], 3)
    verifier += _expect_byte(p2 + PROC_STATE, symbols["PROC_ZOMBIE"])
    verifier += _expect_word(p2 + PROC_SAVED_SP, 0x7777)
    verifier += _expect_byte(p3 + PROC_STATE, symbols["PROC_RUNNING"])
    verifier += _jp(PASS_PC)
    frame = b"\x00" * 10 + _word(VERIFY_PC)

    code = bytearray(b"\xF3" + _ld_sp(TEST_STACK))
    code += _call(symbols["zx48_process_init"])
    code += _call(symbols["zx48_process_prepare_pid1"])
    code += _set_byte(symbols["current_pid"], 1)
    code += _set_byte(p1 + PROC_STATE, symbols["PROC_RUNNING"])
    code += _set_byte(p2 + PROC_STATE, symbols["PROC_ZOMBIE"])
    code += _set_word(p2 + PROC_SAVED_SP, 0x7777)
    code += _set_byte(p3 + PROC_STATE, symbols["PROC_READY"])
    code += _set_word(p3 + PROC_SAVED_SP, FRAME_ADDRESS)
    code += _set_word(symbols["syscall_frame_sp"], 0x8700)
    code += _call(symbols["zx48_schedule"]) + _jp(FAIL_PC)
    run_sna(root, bytes(code), patch=_fixture_patch(fixture, frame=frame, verifier=bytes(verifier)))


def _source_contract(root: Path) -> list[dict[str, object]]:
    process = (root / "v1/src/kernel/process.asm").read_text(encoding="utf-8")
    scheduler = (root / "v1/src/kernel/scheduler.asm").read_text(encoding="utf-8")
    start = process.index("    MACRO EMIT_ZOMBIE_TRANSITION_ROUTINES")
    end = process.index("    ENDM\n", start)
    zombie = process[start:end]
    exit_start = zombie.index("zx48_process_exit_to_zombie:\n")
    publish = zombie.index("zx48_process_zombie_publish:\n")
    exit_body = zombie[exit_start:publish]
    handle_close = exit_body.index("call zx48_handles_close_all_current")
    free_bootstrap = exit_body.index("zx48_process_zombie_free_bootstrap:")
    free_stack = exit_body.index("zx48_process_zombie_free_stack:")
    free_image = exit_body.index("zx48_process_zombie_free_image:")
    schedule_start = scheduler.index("zx48_schedule:\n")
    scan_start = scheduler.index("zx48_schedule_scan:\n")
    restore_start = scheduler.index("zx48_schedule_restore:\n")
    schedule_head = scheduler[schedule_start:scan_start]
    schedule_scan = scheduler[scan_start:restore_start]
    return [
        {"name": "p214-is-a-separate-composable-emitter-after-p213", "passed": "ZX48_P2_14_ZOMBIE_EMITTED EQU 1" in zombie and process.index("    MACRO EMIT_PARENT_CHILD_ROUTINES") < start},
        {"name": "exit-validates-owned-byte-shape-before-destructive-teardown", "passed": exit_body.index("ld (process_zombie_bootstrap_size),hl") < handle_close and "sbc hl,de" in exit_body[:handle_close]},
        {"name": "exit-closes-handles-before-freeing-private-extents", "passed": handle_close < free_bootstrap < free_stack < free_image},
        {"name": "exit-frees-bootstrap-stack-image-in-exact-owned-extents", "passed": all(token in exit_body for token in ("ld hl,(process_zombie_bootstrap_base)", "ld bc,(process_zombie_bootstrap_size)", "ld hl,(process_zombie_stack_base)", "ld bc,(process_zombie_stack_size)", "ld hl,(process_zombie_image_base)", "ld bc,(process_zombie_image_size)")) and exit_body.count("call zx48_free") == 3},
        {"name": "resource-release-precedes-zombie-publication", "passed": free_image < publish and "ld (ix+PROC_STATE),PROC_ZOMBIE" not in exit_body},
        {"name": "zombie-publication-retains-descriptor-identity-and-clears-stale-resource-pointers", "passed": all(token in zombie[publish:] for token in ("ld (ix+PROC_OWNED_BYTES),a", "ld (ix+PROC_ARG_PTR),a", "ld (ix+PROC_ENV_PTR),a", "ld (ix+PROC_EXIT_STATUS),a", "ld (ix+PROC_STATE),PROC_ZOMBIE")) and "ld (ix+PROC_PID),a" not in zombie[publish:] and "ld (ix+PROC_PARENT),a" not in zombie[publish:]},
        {"name": "waiting-parent-wake-is-generation-qualified", "passed": "process_zombie_parent_generation" in zombie and "call zx48_process_generation_get" in zombie[zombie.index("zx48_process_zombie_wake_parent:"):] and "sbc hl,de" in zombie[zombie.index("zx48_process_zombie_wake_parent:"):]},
        {"name": "zombie-publication-wakes-parent-restores-tty-and-schedules", "passed": zombie.index("ld (ix+PROC_STATE),PROC_ZOMBIE") < zombie.index("call zx48_process_zombie_wake_parent") < zombie.index("call zx48_process_restore_tty_owner") < zombie.index("jp zx48_schedule")},
        {"name": "zombie-descriptor-is-not-reclaimed-by-exit", "passed": "ld bc,PROC_DESC_SIZE-1" not in zombie and "ld (ix+PROC_STATE),PROC_FREE" not in zombie},
        {"name": "scheduler-does-not-save-or-republish-current-zombie", "passed": "cp PROC_ZOMBIE\n    jr z,zx48_schedule_begin" in schedule_head and schedule_head.index("cp PROC_ZOMBIE") < schedule_head.index("ld (ix+PROC_SAVED_SP),l")},
        {"name": "scheduler-selects-only-ready-candidates", "passed": "cp PROC_READY\n    jr z,zx48_schedule_choose" in schedule_scan},
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
    if step != "P2.14":
        raise DriverError(f"Phase-2 ZOMBIE step is not registered: {step}")

    assertions = _source_contract(root)
    failed = [item["name"] for item in assertions if item["passed"] is not True]
    require(not failed, f"static P2.14 contract failures: {failed}")

    kernel_command, kernel_binary, kernel_symbols = _assemble_kernel(root, run_command, require_project_tool)
    fixture_command, fixture_binary, fixture_symbols = _assemble_fixture(root, run_command, require_project_tool)
    kernel_values = _symbols(kernel_symbols, ("kernel_ordinary_used_end", "KERNEL_CODE_END"))
    free_bytes = kernel_values["KERNEL_CODE_END"] + 1 - kernel_values["kernel_ordinary_used_end"]
    require(free_bytes >= 0, "P2.14 resident ordinary kernel exceeds hard ceiling")
    assertions.append({
        "name": "resident-kernel-ordinary-code-remains-within-faff-ceiling",
        "passed": True,
        "used_end": f"0x{kernel_values['kernel_ordinary_used_end']:04X}",
        "code_end": f"0x{kernel_values['KERNEL_CODE_END']:04X}",
        "free_bytes": free_bytes,
    })

    names = (
        "zx48_memory_init", "zx48_alloc", "zx48_process_init", "zx48_process_prepare_pid1",
        "zx48_handles_init", "zx48_od_create", "zx48_handle_install", "zx48_process_links_init",
        "zx48_process_link_child", "zx48_process_exit_to_zombie", "zx48_schedule",
        "process_table", "current_pid", "process_generation", "memory_live_allocations",
        "memory_free_extents", "open_description_table", "syscall_frame_sp", "tty_input_owner",
        "p214_panic_code", "MAX_PROCESSES", "PROC_DESC_SIZE", "PROC_READY", "PROC_RUNNING",
        "PROC_WAIT_CHILD", "PROC_ZOMBIE", "ALLOC_ANY", "ALLOC_FAST_REQUIRED", "ARENA_START",
        "ARENA_SIZE", "OD_KIND_NULL", "O_READ",
    )
    symbols = _symbols(fixture_symbols, names)
    require(symbols["MAX_PROCESSES"] == 8 and symbols["PROC_DESC_SIZE"] == PROC_DESC_SIZE, "P2.14 process ABI changed")
    fixture = fixture_binary.read_bytes()
    if action == "test":
        _positive(root, symbols, fixture)
        _stale_parent_generation_does_not_wake(root, symbols, fixture)
        _zombie_never_scheduled(root, symbols, fixture)
        assertions.extend([
            {"name": "child-exit-releases-handles-and-all-private-memory-but-retains-zombie-descriptor", "passed": True},
            {"name": "child-exit-wakes-same-generation-waiting-parent", "passed": True},
            {"name": "stale-parent-generation-is-not-woken", "passed": True},
            {"name": "zombie-is-skipped-by-real-round-robin-scheduler", "passed": True},
        ])

    return [kernel_command, fixture_command], {
        "v1/build/kernel.bin": sha256_file(kernel_binary),
        "v1/build/p214-zombie.bin": sha256_file(fixture_binary),
        "v1/src/kernel/process.asm": sha256_file(root / "v1/src/kernel/process.asm"),
        "v1/tools-host/test-driver/phase2_zombie.py": sha256_file(root / "v1/tools-host/test-driver/phase2_zombie.py"),
        "v1/tools-host/test-driver/run.py": sha256_file(root / "v1/tools-host/test-driver/run.py"),
        "v1/tools-host/test-driver/phase2_gate.py": sha256_file(root / "v1/tools-host/test-driver/phase2_gate.py"),
    }, assertions
'''


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one anchor, found {count}")
    return text.replace(old, new, 1)


def main() -> None:
    process_path = ROOT / "v1/src/kernel/process.asm"
    process = process_path.read_text(encoding="utf-8")
    if "MACRO EMIT_ZOMBIE_TRANSITION_ROUTINES" in process:
        raise SystemExit("P2.14 emitter already present")
    if not process.rstrip().endswith("ENDM"):
        raise SystemExit("process.asm no longer ends at P2.13 emitter")
    process_path.write_text(process.rstrip() + PROCESS_APPEND + "\n", encoding="utf-8", newline="\n")

    zombie_path = ROOT / "v1/tools-host/test-driver/phase2_zombie.py"
    if zombie_path.exists():
        raise SystemExit("phase2_zombie.py already exists")
    zombie_path.write_text(PHASE2_ZOMBIE, encoding="utf-8", newline="\n")

    run_path = ROOT / "v1/tools-host/test-driver/run.py"
    run = run_path.read_text(encoding="utf-8")
    run = replace_once(run, "import phase2_parent_child\n", "import phase2_parent_child\nimport phase2_zombie\n", "run import")
    run = replace_once(
        run,
        '    if step == "P2.13":\n        return phase2_parent_child.dispatch(root, action, step, **kwargs)\n',
        '    if step == "P2.13":\n        return phase2_parent_child.dispatch(root, action, step, **kwargs)\n    if step == "P2.14":\n        return phase2_zombie.dispatch(root, action, step, **kwargs)\n',
        "run dispatch",
    )
    run_path.write_text(run, encoding="utf-8", newline="\n")

    gate_path = ROOT / "v1/tools-host/test-driver/phase2_gate.py"
    gate = gate_path.read_text(encoding="utf-8")
    gate = replace_once(
        gate,
        'CANDIDATE_STEPS: tuple[str, ...] = ("P2.08", "P2.09", "P2.10", "P2.11", "P2.12", "P2.13")\n',
        'CANDIDATE_STEPS: tuple[str, ...] = ("P2.08", "P2.09", "P2.10", "P2.11", "P2.12", "P2.13", "P2.14")\n',
        "phase2 gate candidate tuple",
    )
    gate_path.write_text(gate, encoding="utf-8", newline="\n")

    print("P2.14 candidate materialized")


if __name__ == "__main__":
    main()
