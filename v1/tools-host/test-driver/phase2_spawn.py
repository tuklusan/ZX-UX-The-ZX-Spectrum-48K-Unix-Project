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
import struct
from typing import Any, Callable

from driver_core import DriverError
from fuse_harness import FAIL_PC, PASS_PC, run_sna
import phase1

FIXTURE_CODE = 0xE000
PROGRAM_ADDRESS = 0x9000
TEST_STACK = 0xBFC0
PROC_ADDRESS = 0xC000
PATH_ADDRESS = 0xC100
ARG_ADDRESS = 0xC200
ENV_ADDRESS = 0xC300
MIRROR_BASE = 0xC800
POISON_POINTER = 0x0001
PROC1_SIZE = 16
PROC1_PATH_MAX = 31
PROCESS_COUNT = 8
PROC_DESC_SIZE = 48
PROC_STATE = 2
PERSISTENT_CANARY_SIZE = 16


class Phase2SpawnError(DriverError):
    """Raised when the P2.09 spawn-preflight contract regresses."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Phase2SpawnError(message)


def _word(value: int) -> bytes:
    return bytes((value & 0xFF, (value >> 8) & 0xFF))


def _ld_bc(value: int) -> bytes:
    return b"\x01" + _word(value)


def _jp_nc(address: int) -> bytes:
    return b"\xD2" + _word(address)


def _proc1(
    *,
    path_ptr: int = PATH_ADDRESS,
    arg1_ptr: int = ARG_ADDRESS,
    arg1_len: int = 4,
    env1_ptr: int = ENV_ADDRESS,
    env1_len: int = 4,
    stdin_handle: int = 0,
    stdout_handle: int = 1,
    stderr_handle: int = 2,
    flags: int = 0,
    reserved: int = 0,
) -> bytes:
    value = struct.pack(
        "<HHHHHBBBBH",
        path_ptr,
        arg1_ptr,
        arg1_len,
        env1_ptr,
        env1_len,
        stdin_handle,
        stdout_handle,
        stderr_handle,
        flags,
        reserved,
    )
    require(len(value) == PROC1_SIZE, "P2.09 PROC1 fixture size changed")
    return value


def _symbols(path: Path, names: tuple[str, ...]) -> dict[str, int]:
    text = path.read_text(encoding="utf-8", errors="replace")
    found: dict[str, int] = {}
    for name in names:
        pattern = re.compile(rf"^{re.escape(name)}:\s+equ\s+0x([0-9A-Fa-f]+)\s*$", re.IGNORECASE | re.MULTILINE)
        match = pattern.search(text)
        require(match is not None, f"P2.09 symbol missing from assembler output: {name}")
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
    listing = build / "kernel-p209.lst"
    symbols = build / "kernel-p209.sym"
    result = run_command(
        [assembler, "--nologo", "--lst=../../build/kernel-p209.lst", "--sym=../../build/kernel-p209.sym", "kernel.asm"],
        cwd=root / "v1/src/kernel",
        timeout_seconds=30.0,
    )
    require(not result.timed_out and result.exit_code == 0, f"P2.09 resident kernel assembly failed: {result.stderr or result.stdout}")
    binary = build / "kernel.bin"
    require(binary.is_file() and binary.stat().st_size == 8192, "P2.09 resident kernel must remain exactly 8192 bytes")
    require(listing.is_file() and symbols.is_file(), "P2.09 resident kernel listing/symbols missing")
    return result, binary, listing, symbols


def _assemble_fixture(
    root: Path,
    run_command: Callable[..., Any],
    require_project_tool: Callable[[Path, str | Path], Path],
):
    assembler = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    source = build / "p209-spawn.asm"
    binary = build / "p209-spawn.bin"
    listing = build / "p209-spawn.lst"
    symbols = build / "p209-spawn.sym"
    source.write_text(
        "    DEVICE ZXSPECTRUM48\n"
        "    INCLUDE \"../include/zx48ux.inc\"\n"
        "    INCLUDE \"../src/kernel/syscall.asm\"\n"
        "    INCLUDE \"../src/kernel/process.asm\"\n"
        f"    ORG ${FIXTURE_CODE:04X}\n"
        "p209_gateway:\n"
        "    ld (syscall_arg_hl),hl\n"
        "    cp SYS_SPAWN\n"
        f"    jp nz,${FAIL_PC:04X}\n"
        "    jp zx48_sys_spawn\n"
        "p209_bad_gateway:\n"
        "    push af\n"
        "    ld a,$5A\n"
        "    ld (p209_allocator_state),a\n"
        "    pop af\n"
        "    jp p209_gateway\n"
        "p209_preflight_start:\n"
        "    EMIT_USER_RANGE_VALIDATION_ROUTINE\n"
        "    EMIT_PROCESS_CAPACITY_ROUTINE\n"
        "    EMIT_SPAWN_PREFLIGHT_ROUTINES\n"
        "zx48_process_spawn_transaction:\n"
        "    ld a,E_NOTSUP\n"
        "    scf\n"
        "    ret\n"
        "syscall_arg_hl: dw 0\n"
        "p209_allocator_state: defs 16,$A5\n"
        "p209_open_state: defs 16,$5A\n"
        "process_table: defs MAX_PROCESSES*PROC_DESC_SIZE,0\n"
        "p209_preflight_end:\n"
        "    SAVEBIN \"p209-spawn.bin\",p209_gateway,p209_preflight_end-p209_gateway\n",
        encoding="utf-8",
        newline="\n",
    )
    result = run_command(
        [assembler, "--nologo", "--lst=p209-spawn.lst", "--sym=p209-spawn.sym", "p209-spawn.asm"],
        cwd=build,
        timeout_seconds=30.0,
    )
    require(not result.timed_out and result.exit_code == 0, f"P2.09 spawn fixture assembly failed: {result.stderr or result.stdout}")
    require(binary.is_file() and 0 < binary.stat().st_size < 0x1000, "P2.09 spawn fixture binary missing or too large")
    require(listing.is_file() and symbols.is_file(), "P2.09 spawn fixture symbols/listing missing")
    return result, binary, listing, symbols


def _process_state(full: bool) -> bytes:
    table = bytearray(((index * 37 + 11) & 0xFF) for index in range(PROCESS_COUNT * PROC_DESC_SIZE))
    table[0 * PROC_DESC_SIZE + PROC_STATE] = 2
    table[1 * PROC_DESC_SIZE + PROC_STATE] = 2
    for pid in range(2, PROCESS_COUNT):
        table[pid * PROC_DESC_SIZE + PROC_STATE] = 1
    if not full:
        table[2 * PROC_DESC_SIZE + PROC_STATE] = 0
    return bytes(table)


def _state_regions(symbols: dict[str, int], *, full: bool) -> tuple[tuple[int, bytes], ...]:
    process = _process_state(full)
    allocator = bytes((0xA5 ^ index) & 0xFF for index in range(PERSISTENT_CANARY_SIZE))
    open_state = bytes((0x5A ^ (index * 3)) & 0xFF for index in range(PERSISTENT_CANARY_SIZE))
    return (
        (symbols["process_table"], process),
        (symbols["p209_allocator_state"], allocator),
        (symbols["p209_open_state"], open_state),
    )


def _mirror_regions(symbols: dict[str, int], *, full: bool) -> tuple[tuple[int, bytes], ...]:
    process = _process_state(full)
    allocator = bytes((0xA5 ^ index) & 0xFF for index in range(PERSISTENT_CANARY_SIZE))
    open_state = bytes((0x5A ^ (index * 3)) & 0xFF for index in range(PERSISTENT_CANARY_SIZE))
    return (
        (MIRROR_BASE, process),
        (MIRROR_BASE + len(process), allocator),
        (MIRROR_BASE + len(process) + len(allocator), open_state),
    )


def _patch(fixture: bytes, regions: tuple[tuple[int, bytes], ...]):
    def patch(ram: bytearray) -> None:
        start = FIXTURE_CODE - 0x4000
        ram[start:start + len(fixture)] = fixture
        for address, payload in regions:
            require(0x4000 <= address <= 0xFFFF, f"P2.09 patch address outside RAM: 0x{address:04X}")
            require(address + len(payload) <= 0x10000, f"P2.09 patch crosses address space: 0x{address:04X}")
            offset = address - 0x4000
            ram[offset:offset + len(payload)] = payload
    return patch


def _append_compare_block(code: bytearray, actual: int, mirror: int, length: int) -> None:
    code += phase1._ld_hl(actual) + phase1._ld_de(mirror) + _ld_bc(length)
    loop = PROGRAM_ADDRESS + len(code)
    code += b"\x1A\xBE" + phase1._jp_nz(FAIL_PC) + b"\x23\x13\x0B\x78\xB1" + phase1._jp_nz(loop)


def _append_state_checks(code: bytearray, symbols: dict[str, int]) -> None:
    process_len = PROCESS_COUNT * PROC_DESC_SIZE
    _append_compare_block(code, symbols["process_table"], MIRROR_BASE, process_len)
    _append_compare_block(code, symbols["p209_allocator_state"], MIRROR_BASE + process_len, PERSISTENT_CANARY_SIZE)
    _append_compare_block(code, symbols["p209_open_state"], MIRROR_BASE + process_len + PERSISTENT_CANARY_SIZE, PERSISTENT_CANARY_SIZE)


def _run_gateway_case(
    root: Path,
    symbols: dict[str, int],
    fixture: bytes,
    *,
    full: bool,
    proc_ptr: int,
    expected_error: int,
    regions: tuple[tuple[int, bytes], ...] = (),
    bad_gateway: bool = False,
    expect_oracle_failure: bool = False,
) -> None:
    gateway = symbols["p209_bad_gateway"] if bad_gateway else symbols["p209_gateway"]
    code = bytearray(b"\xF3" + phase1._ld_sp(TEST_STACK))
    code += phase1._ld_hl(proc_ptr) + bytes((0x3E, symbols["SYS_SPAWN"] & 0xFF)) + phase1._call(gateway)
    code += _jp_nc(FAIL_PC) + bytes((0xFE, expected_error & 0xFF)) + phase1._jp_nz(FAIL_PC)
    _append_state_checks(code, symbols)
    code += phase1._jp(PASS_PC)
    patch = _patch(fixture, _state_regions(symbols, full=full) + _mirror_regions(symbols, full=full) + regions)
    if expect_oracle_failure:
        try:
            run_sna(root, bytes(code), patch=patch)
        except DriverError as exc:
            require("exit=1 timed_out=False" in str(exc), f"P2.09 mutation negative failed for an unexpected reason: {exc}")
        else:
            raise Phase2SpawnError("P2.09 full-table state oracle failed to detect deliberate pre-capacity mutation")
        return
    run_sna(root, bytes(code), patch=patch)


def _run_preflight_case(
    root: Path,
    symbols: dict[str, int],
    fixture: bytes,
    *,
    proc: bytes,
    path_address: int = PATH_ADDRESS,
    path: bytes = b"/bin/x\0",
    arg_address: int = ARG_ADDRESS,
    arg: bytes = b"ARG1",
    env_address: int = ENV_ADDRESS,
    env: bytes = b"ENV1",
    expected_error: int | None = None,
) -> None:
    code = bytearray(b"\xF3" + phase1._ld_sp(TEST_STACK))
    code += phase1._ld_hl(PROC_ADDRESS) + phase1._call(symbols["zx48_sys_spawn_preflight"])
    if expected_error is None:
        code += phase1._jp_c(FAIL_PC) + b"\xB7" + phase1._jp_nz(FAIL_PC)
    else:
        code += _jp_nc(FAIL_PC) + bytes((0xFE, expected_error & 0xFF)) + phase1._jp_nz(FAIL_PC)
    _append_state_checks(code, symbols)
    code += phase1._jp(PASS_PC)
    regions = (
        (PROC_ADDRESS, proc),
        (path_address, path),
        (arg_address, arg),
        (env_address, env),
    )
    patch = _patch(fixture, _state_regions(symbols, full=False) + _mirror_regions(symbols, full=False) + regions)
    run_sna(root, bytes(code), patch=patch)


def _run_record_pointer_error(
    root: Path,
    symbols: dict[str, int],
    fixture: bytes,
    *,
    proc_ptr: int,
    expected_error: int,
    extra_regions: tuple[tuple[int, bytes], ...] = (),
) -> None:
    code = bytearray(b"\xF3" + phase1._ld_sp(TEST_STACK))
    code += phase1._ld_hl(proc_ptr) + phase1._call(symbols["zx48_sys_spawn_preflight"])
    code += _jp_nc(FAIL_PC) + bytes((0xFE, expected_error & 0xFF)) + phase1._jp_nz(FAIL_PC)
    _append_state_checks(code, symbols)
    code += phase1._jp(PASS_PC)
    patch = _patch(fixture, _state_regions(symbols, full=False) + _mirror_regions(symbols, full=False) + extra_regions)
    run_sna(root, bytes(code), patch=patch)


def _target_tests(root: Path, symbols: dict[str, int], fixture: bytes) -> list[dict[str, object]]:
    require(symbols["PROC1_SIZE"] == PROC1_SIZE, "P2.09 PROC1_SIZE ABI changed")
    require(symbols["PROC1_PATH_MAX"] == PROC1_PATH_MAX, "P2.09 path bound changed")
    require(symbols["MAX_PROCESSES"] == PROCESS_COUNT, "P2.09 process count changed")
    require(symbols["PROC_DESC_SIZE"] == PROC_DESC_SIZE, "P2.09 process descriptor size changed")
    require(symbols["E_INVAL"] == 1 and symbols["E_TOOLONG"] == 10 and symbols["E_AGAIN"] == 13 and symbols["E_NOTSUP"] == 14, "P2.09 errno ABI changed")

    # Strongest ordering oracle: poison pointer plus a full PID2..7 table must
    # return E_AGAIN through the actual SYS_SPAWN entry without touching state.
    _run_gateway_case(
        root,
        symbols,
        fixture,
        full=True,
        proc_ptr=POISON_POINTER,
        expected_error=symbols["E_AGAIN"],
    )

    valid = _proc1()
    _run_preflight_case(root, symbols, fixture, proc=valid)
    _run_preflight_case(root, symbols, fixture, proc=_proc1(flags=1))
    _run_preflight_case(root, symbols, fixture, proc=_proc1(stdin_handle=7, stdout_handle=7, stderr_handle=7))
    _run_preflight_case(root, symbols, fixture, proc=_proc1(arg1_ptr=POISON_POINTER, arg1_len=0, env1_ptr=POISON_POINTER, env1_len=0))
    _run_preflight_case(root, symbols, fixture, proc=_proc1(), path=b"x" * PROC1_PATH_MAX + b"\0")

    # Short path ending at the display boundary is legal because only bytes up to
    # and including the NUL are validated/read.
    display_path = 0x5AFE
    _run_preflight_case(root, symbols, fixture, proc=_proc1(path_ptr=display_path), path_address=display_path, path=b"x\0")

    _run_preflight_case(root, symbols, fixture, proc=_proc1(flags=2), expected_error=symbols["E_INVAL"])
    _run_preflight_case(root, symbols, fixture, proc=_proc1(reserved=1), expected_error=symbols["E_INVAL"])
    _run_preflight_case(root, symbols, fixture, proc=_proc1(reserved=0x0100), expected_error=symbols["E_INVAL"])
    _run_preflight_case(root, symbols, fixture, proc=_proc1(stdin_handle=8), expected_error=symbols["E_INVAL"])
    _run_preflight_case(root, symbols, fixture, proc=_proc1(stdout_handle=8), expected_error=symbols["E_INVAL"])
    _run_preflight_case(root, symbols, fixture, proc=_proc1(stderr_handle=8), expected_error=symbols["E_INVAL"])
    _run_preflight_case(root, symbols, fixture, proc=_proc1(arg1_ptr=0xFFFF, arg1_len=2), expected_error=symbols["E_INVAL"])
    _run_preflight_case(root, symbols, fixture, proc=_proc1(env1_ptr=0x5B00, env1_len=1), expected_error=symbols["E_INVAL"])
    _run_preflight_case(root, symbols, fixture, proc=_proc1(path_ptr=POISON_POINTER), path_address=PATH_ADDRESS, expected_error=symbols["E_INVAL"])
    _run_preflight_case(root, symbols, fixture, proc=_proc1(), path=b"\0", expected_error=symbols["E_INVAL"])
    _run_preflight_case(root, symbols, fixture, proc=_proc1(), path=b"x" * (PROC1_PATH_MAX + 1), expected_error=symbols["E_TOOLONG"])
    _run_preflight_case(root, symbols, fixture, proc=_proc1(path_ptr=0x5AFF), path_address=0x5AFF, path=b"x", expected_error=symbols["E_INVAL"])

    # Complete fixed record itself must fit before any indexed PROC1 read.
    crossing_record = 0x5AF8
    _run_record_pointer_error(
        root,
        symbols,
        fixture,
        proc_ptr=crossing_record,
        expected_error=symbols["E_INVAL"],
        extra_regions=((crossing_record, valid[:8]),),
    )

    # Capacity-available gateway is deliberately incomplete until P2.10; after
    # a successful preflight it returns E_NOTSUP and still leaves persistent state unchanged.
    _run_gateway_case(
        root,
        symbols,
        fixture,
        full=False,
        proc_ptr=PROC_ADDRESS,
        expected_error=symbols["E_NOTSUP"],
        regions=((PROC_ADDRESS, valid), (PATH_ADDRESS, b"/bin/x\0"), (ARG_ADDRESS, b"ARG1"), (ENV_ADDRESS, b"ENV1")),
    )

    # Required negative sensitivity: an otherwise identical gateway injects one
    # persistent write before capacity. The full-table oracle must reject it.
    _run_gateway_case(
        root,
        symbols,
        fixture,
        full=True,
        proc_ptr=POISON_POINTER,
        expected_error=symbols["E_AGAIN"],
        bad_gateway=True,
        expect_oracle_failure=True,
    )

    return [
        {"name": "full-pid2-through-pid7-table-returns-e-again-through-real-sys-spawn-before-poison-proc1-dereference", "passed": True},
        {"name": "full-table-preflight-leaves-process-allocator-and-open-description-persistent-state-byte-identical", "passed": True},
        {"name": "capacity-available-valid-proc1-reaches-no-side-effect-production-preflight-pass-boundary", "passed": True},
        {"name": "allow-tape-zero-and-one-are-structurally-accepted-without-cassette-path", "passed": True},
        {"name": "unknown-spawn-flag-bits-reserved-bytes-and-handle-values-eight-or-higher-return-e-inval", "passed": True},
        {"name": "arg1-env1-ranges-use-widened-validation-and-zero-length-pointers-are-not-dereferenced", "passed": True},
        {"name": "path-is-nonempty-nul-terminated-within-31-bytes-and-short-region-edge-string-is-accepted", "passed": True},
        {"name": "overlength-path-returns-e-toolong-and-invalid-path-range-returns-e-inval", "passed": True},
        {"name": "complete-sixteen-byte-proc1-range-is-validated-before-indexed-record-read", "passed": True},
        {"name": "capacity-available-real-sys-spawn-remains-e-notsup-until-p210-after-successful-preflight", "passed": True},
        {"name": "negative-oracle-detects-deliberate-persistent-mutation-before-capacity-decision", "passed": True},
    ]


def _source_contract(root: Path) -> list[dict[str, object]]:
    process = (root / "v1/src/kernel/process.asm").read_text(encoding="utf-8")
    syscall = (root / "v1/src/kernel/syscall.asm").read_text(encoding="utf-8")
    kernel = (root / "v1/src/kernel/kernel.asm").read_text(encoding="utf-8")

    process_start = process.index("    MACRO EMIT_PROCESS_CAPACITY_ROUTINE")
    process_end = process.index("    ENDM\n", process_start)
    capacity = process[process_start:process_end]
    capacity_code = "\n".join(line.split(";", 1)[0] for line in capacity.splitlines())

    reserve_start = process.index("zx48_process_reserve_slot:")
    reserve_end = process.index("zx48_process_prepare_pid1:", reserve_start)
    reserve = process[reserve_start:reserve_end]

    spawn_start = syscall.index("    MACRO EMIT_SPAWN_PREFLIGHT_ROUTINES")
    spawn_end = syscall.index("    ENDM\n", spawn_start)
    spawn = syscall[spawn_start:spawn_end]
    spawn_code = "\n".join(line.split(";", 1)[0] for line in spawn.splitlines())
    preflight = spawn[spawn.index("zx48_sys_spawn_preflight:"):]
    first_record_validation = preflight.index("ld bc,PROC1_SIZE")
    capacity_call = preflight.index("call zx48_process_find_free_slot")
    capacity_return = preflight.index("ret c", capacity_call)

    range_start = syscall.index("    MACRO EMIT_USER_RANGE_VALIDATION_ROUTINE")
    range_end = syscall.index("    ENDM\n", range_start)
    range_code = syscall[range_start:range_end]

    exact_offsets = {
        "PROC1_PATH_PTR": 0,
        "PROC1_ARG1_PTR": 2,
        "PROC1_ARG1_LEN": 4,
        "PROC1_ENV1_PTR": 6,
        "PROC1_ENV1_LEN": 8,
        "PROC1_STDIN_HANDLE": 10,
        "PROC1_STDOUT_HANDLE": 11,
        "PROC1_STDERR_HANDLE": 12,
        "PROC1_FLAGS": 13,
        "PROC1_RESERVED": 14,
        "PROC1_SIZE": 16,
    }
    offset_checks = [f"{name}" in syscall and re.search(rf"(?m)^{name}\s+EQU\s+{value}$", syscall) is not None for name, value in exact_offsets.items()]
    forbidden = (
        "zx48_alloc", "zx48_free", "zx48_process_reserve_slot", "zx48_handle_lookup",
        "bincat", "tape", "cassette", "zx48_object", "PROC_READY", "PROC_RUNNING",
        "PROC_STATE", "process_temp_pid", "zx48_process_ptr", "zx48_process_lookup",
    )
    writes = re.findall(r"(?im)^\s*ld\s+\([^\n]+\),", capacity_code)

    return [
        {"name": "proc1-layout-is-exact-pointer-based-sixteen-byte-contract", "passed": all(offset_checks)},
        {"name": "proc1-allows-only-allow-tape-bit-zero", "passed": "PROC1_ALLOW_TAPE           EQU $01" in syscall and "and $FE" in spawn},
        {"name": "capacity-helper-scans-exactly-pid2-through-pid7", "passed": "process_table+2*PROC_DESC_SIZE" in capacity and "ld c,2" in capacity and "ld b,MAX_PROCESSES-2" in capacity},
        {"name": "capacity-helper-is-write-free-and-full-table-returns-e-again", "passed": not writes and "ld a,E_AGAIN" in capacity and "scf\n    ret" in capacity},
        {"name": "reserve-slot-now-consumes-pure-capacity-helper-before-existing-mutation", "passed": reserve.index("call zx48_process_find_free_slot") < reserve.index("ld (process_temp_pid),a") and "ret c" in reserve},
        {"name": "spawn-preflight-capacity-return-precedes-proc1-range-validation", "passed": capacity_call < capacity_return < first_record_validation},
        {"name": "spawn-preflight-validates-complete-proc1-before-indexed-read", "passed": preflight.index("call zx48_user_range_validate", first_record_validation) < preflight.index("push hl\n    pop ix") < preflight.index("(ix+PROC1_STDIN_HANDLE)")},
        {"name": "spawn-preflight-validates-all-three-handle-bytes-structurally-only", "passed": all(f"(ix+{name})" in spawn for name in ("PROC1_STDIN_HANDLE", "PROC1_STDOUT_HANDLE", "PROC1_STDERR_HANDLE")) and spawn.count("cp MAX_HANDLES_PER_PROCESS") == 3 and "zx48_handle_lookup" not in spawn_code},
        {"name": "spawn-preflight-validates-flags-reserved-arg1-env1-and-bounded-path", "passed": all(token in spawn for token in ("PROC1_FLAGS", "and $FE", "PROC1_RESERVED", "PROC1_ARG1_PTR", "PROC1_ARG1_LEN", "PROC1_ENV1_PTR", "PROC1_ENV1_LEN", "PROC1_PATH_PTR", "PROC1_PATH_MAX+1", "E_TOOLONG"))},
        {"name": "spawn-preflight-has-no-allocation-reservation-publication-object-bcat-tape-or-live-handle-work", "passed": all(token.lower() not in spawn_code.lower() for token in forbidden)},
        {"name": "shared-range-validator-widens-before-end-byte-narrowing", "passed": range_code.index("add hl,bc") < range_code.index("jr c,zx48_user_range_wrap") < range_code.index("dec hl")},
        {"name": "shared-range-validator-preserves-zero-length-no-dereference-rule", "passed": "jr z,zx48_user_range_ok" in range_code},
        {"name": "resident-sys-spawn-remains-stub-until-p210-while-exact-preflight-source-is-staged", "passed": "dw zx48_sys_getpid,zx48_sys_spawn_stub,zx48_sys_exec_stub" in syscall and "EMIT_SPAWN_PREFLIGHT_ROUTINES" not in kernel},
        {"name": "resident-syscall-implementation-emits-the-same-shared-range-validator-source", "passed": "    EMIT_USER_RANGE_VALIDATION_ROUTINE" in syscall[:spawn_start]},
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
    if step != "P2.09":
        raise DriverError(f"Phase-2 spawn step is not registered: {step}")

    assertions = _source_contract(root)
    failed = [item["name"] for item in assertions if item["passed"] is not True]
    require(not failed, f"static P2.09 contract failures: {failed}")

    kernel_command, kernel_binary, _kernel_listing, kernel_symbols = _assemble_kernel(root, run_command, require_project_tool)
    fixture_command, fixture_binary, _fixture_listing, fixture_symbols = _assemble_fixture(root, run_command, require_project_tool)

    kernel_symbol_values = _symbols(kernel_symbols, ("kernel_ordinary_used_end", "KERNEL_CODE_END"))
    free_bytes = kernel_symbol_values["KERNEL_CODE_END"] + 1 - kernel_symbol_values["kernel_ordinary_used_end"]
    require(free_bytes >= 0, "P2.09 resident ordinary kernel exceeds hard ceiling")
    assertions.append({
        "name": "resident-kernel-ordinary-code-remains-within-faff-ceiling",
        "passed": True,
        "used_end": f"0x{kernel_symbol_values['kernel_ordinary_used_end']:04X}",
        "code_end": f"0x{kernel_symbol_values['KERNEL_CODE_END']:04X}",
        "free_bytes": free_bytes,
    })

    symbol_names = (
        "p209_gateway", "p209_bad_gateway", "zx48_sys_spawn", "zx48_sys_spawn_preflight",
        "process_table", "p209_allocator_state", "p209_open_state", "SYS_SPAWN",
        "PROC1_SIZE", "PROC1_PATH_MAX", "MAX_PROCESSES", "PROC_DESC_SIZE",
        "E_INVAL", "E_TOOLONG", "E_AGAIN", "E_NOTSUP",
    )
    symbols = _symbols(fixture_symbols, symbol_names)
    fixture = fixture_binary.read_bytes()
    if action == "test":
        assertions.extend(_target_tests(root, symbols, fixture))

    return [kernel_command, fixture_command], {
        "v1/build/kernel.bin": sha256_file(kernel_binary),
        "v1/build/p209-spawn.bin": sha256_file(fixture_binary),
        "v1/src/kernel/process.asm": sha256_file(root / "v1/src/kernel/process.asm"),
        "v1/src/kernel/syscall.asm": sha256_file(root / "v1/src/kernel/syscall.asm"),
        "v1/tools-host/test-driver/phase2_spawn.py": sha256_file(root / "v1/tools-host/test-driver/phase2_spawn.py"),
        "v1/tools-host/test-driver/run.py": sha256_file(root / "v1/tools-host/test-driver/run.py"),
        "v1/tools-host/test-driver/phase2_gate.py": sha256_file(root / "v1/tools-host/test-driver/phase2_gate.py"),
    }, assertions
