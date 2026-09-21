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
TEST_STACK = 0x8F00
PROC_ADDRESS = 0xA300
GOOD_PATH_ADDRESS = 0xA000
TEXT_PATH_ADDRESS = 0xA020
BAD_PATH_ADDRESS = 0xA040
MISSING_PATH_ADDRESS = 0xA060
ARG_ADDRESS = 0xA100
ENV_ADDRESS = 0xA200
GOOD_RECORD = 0xB000
TEXT_RECORD = 0xB020
BAD_RECORD = 0xB040
GOOD_MEX = 0xC000
BAD_MEX = 0xC100
MIRROR_BASE = 0xA800
PROC1_SIZE = 16
PROC_DESC_SIZE = 48
PROCESS_COUNT = 8
OD_SIZE = 8
OD_COUNT = 24
FREE_EXTENT_BYTES = 64
GOOD_IMAGE = b"\x01\x00\x00\x00\xC9\x5A"
GOOD_BSS = 2
GOOD_IMAGE_ALLOC = 8
GOOD_STACK_ALLOC = 128


class Phase2SpawnAtomicError(DriverError):
    """Raised when the P2.10 atomic spawn contract regresses."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Phase2SpawnAtomicError(message)


def _word(value: int) -> bytes:
    return bytes((value & 0xFF, (value >> 8) & 0xFF))


def _ld_bc(value: int) -> bytes:
    return b"\x01" + _word(value)


def _jp_nc(address: int) -> bytes:
    return b"\xD2" + _word(address)


def _crc16(data: bytes) -> int:
    crc = 0xFFFF
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc


def _mex(*, relocations: tuple[int, ...] = (0,)) -> bytes:
    header = bytearray(24)
    header[:4] = b"MEX1"
    header[4] = 1
    header[5] = 0
    struct.pack_into("<H", header, 6, 24)
    struct.pack_into("<H", header, 8, len(GOOD_IMAGE))
    struct.pack_into("<H", header, 10, GOOD_BSS)
    struct.pack_into("<H", header, 12, 4)
    struct.pack_into("<H", header, 14, 64)
    struct.pack_into("<H", header, 16, len(relocations))
    struct.pack_into("<H", header, 18, 24 + len(GOOD_IMAGE))
    body = GOOD_IMAGE + b"".join(struct.pack("<H", item) for item in relocations)
    struct.pack_into("<H", header, 20, _crc16(body))
    struct.pack_into("<H", header, 22, 0)
    struct.pack_into("<H", header, 22, _crc16(bytes(header)))
    return bytes(header) + body


def _arg1(token: bytes) -> bytes:
    total = 8 + len(token) + 1
    return b"ARG1" + bytes((1, 0)) + struct.pack("<H", total) + token + b"\0"


ENV1_EMPTY = b"ENV1\x00\x00\x08\x00"


def _proc1(
    *,
    path_ptr: int = GOOD_PATH_ADDRESS,
    arg_ptr: int = ARG_ADDRESS,
    arg_len: int | None = None,
    env_ptr: int = ENV_ADDRESS,
    env_len: int = len(ENV1_EMPTY),
    stdin_handle: int = 0,
    stdout_handle: int = 1,
    stderr_handle: int = 2,
    flags: int = 0,
) -> bytes:
    if arg_len is None:
        arg_len = len(_arg1(b"/bin/good"))
    value = struct.pack(
        "<HHHHHBBBBH",
        path_ptr,
        arg_ptr,
        arg_len,
        env_ptr,
        env_len,
        stdin_handle,
        stdout_handle,
        stderr_handle,
        flags,
        0,
    )
    require(len(value) == PROC1_SIZE, "P2.10 PROC1 fixture size changed")
    return value


def _record(name: bytes, object_type: int, payload: int, length: int) -> bytes:
    require(1 <= len(name) <= 10, "P2.10 fixture object name invalid")
    record = bytearray(20)
    record[: len(name)] = name
    record[10] = 1  # DIR_BIN
    record[11] = object_type & 0xFF
    record[12] = 0  # RAW
    record[13] = 0
    struct.pack_into("<H", record, 14, length)
    struct.pack_into("<H", record, 16, length)
    struct.pack_into("<H", record, 18, payload)
    return bytes(record)


def _symbols(path: Path, names: tuple[str, ...]) -> dict[str, int]:
    text = path.read_text(encoding="utf-8", errors="replace")
    found: dict[str, int] = {}
    for name in names:
        pattern = re.compile(rf"^{re.escape(name)}:\s+equ\s+0x([0-9A-Fa-f]+)\s*$", re.IGNORECASE | re.MULTILINE)
        match = pattern.search(text)
        require(match is not None, f"P2.10 symbol missing from assembler output: {name}")
        found[name] = int(match.group(1), 16)
    return found


def _assemble_kernel(root: Path, run_command: Callable[..., Any], require_project_tool: Callable[[Path, str | Path], Path]):
    assembler = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    result = run_command(
        [assembler, "--nologo", "--lst=../../build/kernel-p210.lst", "--sym=../../build/kernel-p210.sym", "kernel.asm"],
        cwd=root / "v1/src/kernel",
        timeout_seconds=30.0,
    )
    require(not result.timed_out and result.exit_code == 0, f"P2.10 resident kernel assembly failed: {result.stderr or result.stdout}")
    binary = build / "kernel.bin"
    symbols = build / "kernel-p210.sym"
    require(binary.is_file() and binary.stat().st_size == 8192, "P2.10 resident kernel must remain exactly 8192 bytes")
    require(symbols.is_file(), "P2.10 resident kernel symbols missing")
    return result, binary, symbols


def _assemble_fixture(root: Path, run_command: Callable[..., Any], require_project_tool: Callable[[Path, str | Path], Path]):
    assembler = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    source = build / "p210-spawn.asm"
    binary = build / "p210-spawn.bin"
    symbols = build / "p210-spawn.sym"
    listing = build / "p210-spawn.lst"
    source.write_text(
        "    DEVICE ZXSPECTRUM48\n"
        "    INCLUDE \"../include/zx48ux.inc\"\n"
        "    INCLUDE \"../include/mex1.inc\"\n"
        "    INCLUDE \"../src/kernel/syscall.asm\"\n"
        "    INCLUDE \"../src/kernel/memory.asm\"\n"
        "    INCLUDE \"../src/kernel/process.asm\"\n"
        "    INCLUDE \"../src/kernel/handles.asm\"\n"
        "    INCLUDE \"../src/kernel/objects.asm\"\n"
        "PANIC_SCHEDULER EQU $03\n"
        f"    ORG ${FIXTURE_CODE:04X}\n"
        "p210_start:\n"
        "    EMIT_MEMORY_ROUTINES\n"
        "    EMIT_USER_RANGE_VALIDATION_ROUTINE\n"
        "    EMIT_PROCESS_CAPACITY_ROUTINE\n"
        "    EMIT_MEX1_RELOCATION_ROUTINES\n"
        "    EMIT_ARG1_ROUTINES\n"
        "    EMIT_ENV1_ROUTINES\n"
        "    EMIT_INITIAL_CONTEXT_ROUTINES\n"
        "    EMIT_HANDLE_ROUTINES\n"
        "    EMIT_SPAWN_PREFLIGHT_ROUTINES\n"
        "    EMIT_SPAWN_TRANSACTION_ROUTINES\n"
        "p210_gateway:\n"
        "    ld (syscall_arg_hl),hl\n"
        "    jp zx48_sys_spawn\n"
        "zx48_process_count:\n"
        "    xor a\n"
        "    ret\n"
        "zx48_process_lookup:\n"
        "    cp MAX_PROCESSES\n"
        "    jr nc,p210_process_noent\n"
        "    ld c,a\n"
        "    ld ix,process_table\n"
        "    or a\n"
        "    jr z,p210_process_have_ptr\n"
        "    ld b,a\n"
        "    ld de,PROC_DESC_SIZE\n"
        "p210_process_ptr_loop:\n"
        "    add ix,de\n"
        "    djnz p210_process_ptr_loop\n"
        "p210_process_have_ptr:\n"
        "    ld a,(ix+PROC_STATE)\n"
        "    or a\n"
        "    jr z,p210_process_noent\n"
        "    xor a\n"
        "    ret\n"
        "p210_process_noent:\n"
        "    ld a,E_NOENT\n"
        "    scf\n"
        "    ret\n"
        "zx48_spawn_resolve_ram_object:\n"
        "    push hl\n"
        "    ld de,p210_path_good\n"
        "    call p210_cstr_equal\n"
        "    pop hl\n"
        "    jr z,p210_resolve_good\n"
        "    push hl\n"
        "    ld de,p210_path_text\n"
        "    call p210_cstr_equal\n"
        "    pop hl\n"
        "    jr z,p210_resolve_text\n"
        "    push hl\n"
        "    ld de,p210_path_bad\n"
        "    call p210_cstr_equal\n"
        "    pop hl\n"
        "    jr z,p210_resolve_bad\n"
        "    ld a,E_NOENT\n"
        "    scf\n"
        "    ret\n"
        "p210_resolve_good:\n"
        f"    ld ix,${GOOD_RECORD:04X}\n"
        "    xor a\n"
        "    ret\n"
        "p210_resolve_text:\n"
        f"    ld ix,${TEXT_RECORD:04X}\n"
        "    xor a\n"
        "    ret\n"
        "p210_resolve_bad:\n"
        f"    ld ix,${BAD_RECORD:04X}\n"
        "    xor a\n"
        "    ret\n"
        "p210_cstr_equal:\n"
        "    ld a,(de)\n"
        "    cp (hl)\n"
        "    ret nz\n"
        "    or a\n"
        "    ret z\n"
        "    inc de\n"
        "    inc hl\n"
        "    jr p210_cstr_equal\n"
        "zx48_pipe_endpoint_closed:\n"
        "    xor a\n"
        "    ret\n"
        "zx48_pipe_free_panic:\n"
        "    jp zx48_panic\n"
        "zx48_panic:\n"
        "    jp $0000\n"
        "current_pid: db 0\n"
        "process_table: defs MAX_PROCESSES*PROC_DESC_SIZE,0\n"
        "p210_path_good: db '/bin/good',0\n"
        "p210_path_text: db '/bin/text',0\n"
        "p210_path_bad: db '/bin/bad',0\n"
        "p210_end:\n"
        "    SAVEBIN \"p210-spawn.bin\",p210_start,p210_end-p210_start\n",
        encoding="utf-8",
        newline="\n",
    )
    result = run_command(
        [assembler, "--nologo", "--lst=p210-spawn.lst", "--sym=p210-spawn.sym", "p210-spawn.asm"],
        cwd=build,
        timeout_seconds=30.0,
    )
    require(not result.timed_out and result.exit_code == 0, f"P2.10 spawn fixture assembly failed: {result.stderr or result.stdout}")
    require(binary.is_file() and 0 < binary.stat().st_size < 0x1D00, "P2.10 fixture must fit below FAST reserve")
    require(symbols.is_file() and listing.is_file(), "P2.10 fixture symbols/listing missing")
    return result, binary, symbols


def _process_table(*, invalid_handle: bool = False) -> bytes:
    table = bytearray(PROCESS_COUNT * PROC_DESC_SIZE)
    for pid in range(PROCESS_COUNT):
        table[pid * PROC_DESC_SIZE] = pid
        table[pid * PROC_DESC_SIZE + 1] = 0xFF
        table[pid * PROC_DESC_SIZE + 16 : pid * PROC_DESC_SIZE + 24] = b"\xFF" * 8
    p1 = PROC_DESC_SIZE
    table[p1 + 1] = 0
    table[p1 + 2] = 2  # PROC_RUNNING
    table[p1 + 16 : p1 + 24] = bytes((0, 1, 1, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF))
    if invalid_handle:
        table[p1 + 23] = 0xFF
    table[p1 + 28] = 6  # DIR_TMP
    return bytes(table)


def _open_descriptions(*, retain_third_failure: bool = False) -> bytes:
    data = bytearray(OD_COUNT * OD_SIZE)
    # OD0: tty read, one parent reference.
    data[0] = 1
    data[1] = 1
    data[2] = 1
    data[3] = 0
    # OD1: tty write, shared by parent's stdout/stderr.
    base = OD_SIZE
    data[base + 0] = 1
    data[base + 1] = 2
    data[base + 2] = 0xFE if retain_third_failure else 2
    data[base + 3] = 0
    return bytes(data)


def _free_extents(kind: str) -> bytes:
    data = bytearray(FREE_EXTENT_BYTES)
    if kind == "full":
        struct.pack_into("<HH", data, 0, 0x6000, 0x8000)
    elif kind == "cold-only":
        struct.pack_into("<HH", data, 0, 0x6000, 0x2000)
    elif kind == "bootstrap-tight":
        struct.pack_into("<HH", data, 0, 0x7FF8, 0x0088)
    elif kind == "none":
        pass
    else:
        raise AssertionError(kind)
    return bytes(data)


def _patch(fixture: bytes, regions: tuple[tuple[int, bytes], ...]):
    def patch(ram: bytearray) -> None:
        start = FIXTURE_CODE - 0x4000
        ram[start : start + len(fixture)] = fixture
        for address, payload in regions:
            require(0x4000 <= address < 0x10000, f"P2.10 patch address outside RAM: 0x{address:04X}")
            require(address + len(payload) <= 0x10000, f"P2.10 patch crosses RAM: 0x{address:04X}")
            offset = address - 0x4000
            ram[offset : offset + len(payload)] = payload
    return patch


def _append_compare(code: bytearray, actual: int, expected: int, length: int) -> None:
    code += phase1._ld_hl(actual) + phase1._ld_de(expected) + _ld_bc(length)
    loop = PROGRAM_ADDRESS + len(code)
    code += b"\x1A\xBE" + phase1._jp_nz(FAIL_PC) + b"\x23\x13\x0B\x78\xB1" + phase1._jp_nz(loop)


def _expect_byte(address: int, value: int) -> bytes:
    return b"\x3A" + _word(address) + bytes((0xFE, value & 0xFF)) + phase1._jp_nz(FAIL_PC)


def _expect_word(address: int, value: int) -> bytes:
    return b"\x2A" + _word(address) + phase1._ld_de(value) + b"\xB7\xED\x52" + phase1._jp_nz(FAIL_PC)


def _base_regions(symbols: dict[str, int], *, path: bytes, proc: bytes, free_kind: str, od_state: bytes | None = None) -> tuple[tuple[int, bytes], ...]:
    good = _mex()
    bad = _mex(relocations=(0, 1))
    arg = _arg1(path.rstrip(b"\0"))
    if od_state is None:
        od_state = _open_descriptions()
    return (
        (GOOD_PATH_ADDRESS, b"/bin/good\0"),
        (TEXT_PATH_ADDRESS, b"/bin/text\0"),
        (BAD_PATH_ADDRESS, b"/bin/bad\0"),
        (MISSING_PATH_ADDRESS, b"/bin/missing\0"),
        (ARG_ADDRESS, arg),
        (ENV_ADDRESS, ENV1_EMPTY),
        (PROC_ADDRESS, proc),
        (GOOD_MEX, good),
        (BAD_MEX, bad),
        (GOOD_RECORD, _record(b"good", 2, GOOD_MEX, len(good))),
        (TEXT_RECORD, _record(b"text", 1, GOOD_MEX, len(good))),
        (BAD_RECORD, _record(b"bad", 2, BAD_MEX, len(bad))),
        (symbols["process_table"], _process_table()),
        (symbols["current_pid"], b"\x01"),
        (symbols["open_description_table"], od_state),
        (symbols["memory_free_extents"], _free_extents(free_kind)),
        (symbols["memory_live_allocations"], b"\x00\x00"),
    )


def _failure_case(
    root: Path,
    symbols: dict[str, int],
    fixture: bytes,
    *,
    proc: bytes,
    path: bytes,
    expected_error: int,
    free_kind: str = "full",
    od_state: bytes | None = None,
) -> None:
    process = _process_table()
    ods = _open_descriptions() if od_state is None else od_state
    extents = _free_extents(free_kind)
    live = b"\x00\x00"
    process_mirror = MIRROR_BASE
    extent_mirror = process_mirror + len(process)
    od_mirror = extent_mirror + len(extents)
    live_mirror = od_mirror + len(ods)

    code = bytearray(b"\xF3" + phase1._ld_sp(TEST_STACK))
    code += phase1._ld_hl(PROC_ADDRESS) + phase1._call(symbols["p210_gateway"])
    code += _jp_nc(FAIL_PC) + bytes((0xFE, expected_error & 0xFF)) + phase1._jp_nz(FAIL_PC)
    _append_compare(code, symbols["process_table"], process_mirror, len(process))
    _append_compare(code, symbols["memory_free_extents"], extent_mirror, len(extents))
    _append_compare(code, symbols["open_description_table"], od_mirror, len(ods))
    _append_compare(code, symbols["memory_live_allocations"], live_mirror, len(live))
    code += _expect_byte(symbols["current_pid"], 1)
    code += phase1._jp(PASS_PC)

    regions = _base_regions(symbols, path=path, proc=proc, free_kind=free_kind, od_state=ods) + (
        (process_mirror, process),
        (extent_mirror, extents),
        (od_mirror, ods),
        (live_mirror, live),
    )
    run_sna(root, bytes(code), patch=_patch(fixture, regions))


def _success_case(root: Path, symbols: dict[str, int], fixture: bytes) -> None:
    path = b"/bin/good\0"
    arg = _arg1(path[:-1])
    proc = _proc1(arg_len=len(arg))
    process = _process_table()
    parent = process[PROC_DESC_SIZE : 2 * PROC_DESC_SIZE]

    code = bytearray(b"\xF3" + phase1._ld_sp(TEST_STACK))
    code += phase1._ld_hl(PROC_ADDRESS) + phase1._call(symbols["p210_gateway"])
    code += phase1._jp_c(FAIL_PC)
    code += phase1._ld_de(2) + b"\xB7\xED\x52" + phase1._jp_nz(FAIL_PC)
    code += _expect_byte(symbols["current_pid"], 1)
    code += _expect_word(symbols["memory_live_allocations"], 3)
    code += _expect_byte(symbols["open_description_table"] + 2, 2)
    code += _expect_byte(symbols["open_description_table"] + OD_SIZE + 2, 4)

    child = symbols["process_table"] + 2 * PROC_DESC_SIZE
    code += _expect_byte(child + 0, 2)
    code += _expect_byte(child + 1, 1)
    code += _expect_byte(child + 2, symbols["PROC_READY"])
    code += _expect_word(child + 4, 0x6000)
    code += _expect_word(child + 6, GOOD_IMAGE_ALLOC)
    code += _expect_word(child + 8, 0xDF80)
    code += _expect_word(child + 10, 0xE000)
    code += _expect_word(child + 12, 0xDFF4)
    code += _expect_byte(child + 16, 0)
    code += _expect_byte(child + 17, 1)
    code += _expect_byte(child + 18, 1)
    for offset in range(19, 24):
        code += _expect_byte(child + offset, 0xFF)
    code += _expect_byte(child + 28, 6)
    code += _expect_word(child + 40, GOOD_IMAGE_ALLOC + GOOD_STACK_ALLOC + len(arg) + len(ENV1_EMPTY))
    code += _expect_word(child + 42, 0x6008)
    code += _expect_word(child + 44, 0x6008 + len(arg))
    for index, byte in enumerate(b"good\0\0\0\0\0\0"):
        code += _expect_byte(child + 29 + index, byte)
    # Relocation, BSS, and bootstrap copies are all final private bytes.
    code += _expect_word(0x6000, 0x6001)
    code += _expect_byte(0x6004, 0xC9)
    code += _expect_byte(0x6006, 0)
    code += _expect_byte(0x6007, 0)
    for index, byte in enumerate(arg + ENV1_EMPTY):
        code += _expect_byte(0x6008 + index, byte)
    # Parent descriptor is byte-identical.
    parent_mirror = MIRROR_BASE
    _append_compare(code, symbols["process_table"] + PROC_DESC_SIZE, parent_mirror, PROC_DESC_SIZE)
    code += phase1._jp(PASS_PC)

    regions = _base_regions(symbols, path=path, proc=proc, free_kind="full") + ((parent_mirror, parent),)
    run_sna(root, bytes(code), patch=_patch(fixture, regions))


def _target_tests(root: Path, symbols: dict[str, int], fixture: bytes) -> list[dict[str, object]]:
    require(symbols["E_NOENT"] == 2 and symbols["E_NOMEM"] == 3 and symbols["E_BUSY"] == 4 and symbols["E_FORMAT"] == 11, "P2.10 errno ABI changed")
    require(symbols["PROC_READY"] == 1, "P2.10 READY state ABI changed")

    _success_case(root, symbols, fixture)

    # Required direct non-BIN negative: resolution succeeds, then type check fails.
    text_arg = _arg1(b"/bin/text")
    _failure_case(
        root,
        symbols,
        fixture,
        proc=_proc1(path_ptr=TEXT_PATH_ADDRESS, arg_len=len(text_arg)),
        path=b"/bin/text\0",
        expected_error=symbols["E_FORMAT"],
    )

    missing_arg = _arg1(b"/bin/missing")
    _failure_case(
        root,
        symbols,
        fixture,
        proc=_proc1(path_ptr=MISSING_PATH_ADDRESS, arg_len=len(missing_arg)),
        path=b"/bin/missing\0",
        expected_error=symbols["E_NOENT"],
    )

    # Structural handle 7 is valid at P2.09 but an empty live slot must fail here.
    _failure_case(
        root,
        symbols,
        fixture,
        proc=_proc1(stdin_handle=7),
        path=b"/bin/good\0",
        expected_error=symbols["E_NOENT"],
    )

    # Resource-stage rollback: image allocation, FAST stack allocation, and the
    # final ARG1+ENV1 allocation each fail from a deterministic free-map shape.
    _failure_case(root, symbols, fixture, proc=_proc1(), path=b"/bin/good\0", expected_error=symbols["E_NOMEM"], free_kind="none")
    _failure_case(root, symbols, fixture, proc=_proc1(), path=b"/bin/good\0", expected_error=symbols["E_NOMEM"], free_kind="cold-only")
    _failure_case(root, symbols, fixture, proc=_proc1(), path=b"/bin/good\0", expected_error=symbols["E_NOMEM"], free_kind="bootstrap-tight")

    bad_arg = _arg1(b"/bin/bad")
    _failure_case(
        root,
        symbols,
        fixture,
        proc=_proc1(path_ptr=BAD_PATH_ADDRESS, arg_len=len(bad_arg)),
        path=b"/bin/bad\0",
        expected_error=symbols["E_FORMAT"],
    )

    # The third retain fails only after image, stack, bootstrap, context, and two
    # retain operations have succeeded. Rollback must restore OD refs and memory.
    _failure_case(
        root,
        symbols,
        fixture,
        proc=_proc1(),
        path=b"/bin/good\0",
        expected_error=symbols["E_BUSY"],
        od_state=_open_descriptions(retain_third_failure=True),
    )

    return [
        {"name": "spawn-success-returns-child-pid-without-yield-and-publishes-ready-once", "passed": True},
        {"name": "child-inherits-parent-cwd-and-selected-standard-open-descriptions-parent-slots-unchanged", "passed": True},
        {"name": "image-stack-bootstrap-context-and-owned-byte-accounting-are-exact", "passed": True},
        {"name": "absent-target-returns-e-noent-before-allocation", "passed": True},
        {"name": "direct-spawn-resolved-non-bin-returns-e-format", "passed": True},
        {"name": "structurally-valid-but-unbound-parent-handle-is-rejected-before-allocation", "passed": True},
        {"name": "image-stack-and-bootstrap-allocation-failures-restore-allocator-process-and-open-description-state", "passed": True},
        {"name": "post-allocation-relocation-format-failure-rolls-back-all-owned-extents", "passed": True},
        {"name": "late-open-description-retain-failure-rolls-back-prior-retains-and-all-owned-extents", "passed": True},
    ]


def _source_contract(root: Path) -> list[dict[str, object]]:
    process = (root / "v1/src/kernel/process.asm").read_text(encoding="utf-8")
    syscall = (root / "v1/src/kernel/syscall.asm").read_text(encoding="utf-8")
    start = process.index("    MACRO EMIT_SPAWN_TRANSACTION_ROUTINES")
    end = process.index("    ENDM\n", start)
    transaction = process[start:end]
    code = "\n".join(line.split(";", 1)[0] for line in transaction.splitlines())
    commit = transaction[transaction.index("; Commit is intentionally non-fallible.") :]
    before_commit = transaction[: transaction.index("; Commit is intentionally non-fallible.")]
    rollback = transaction[transaction.index("zx48_process_spawn_rollback:") : transaction.index("zx48_process_spawn_return_error:")]

    spawn_start = syscall.index("    MACRO EMIT_SPAWN_PREFLIGHT_ROUTINES")
    spawn_end = syscall.index("    ENDM\n", spawn_start)
    spawn = syscall[spawn_start:spawn_end]

    return [
        {"name": "staged-sys-spawn-enters-p209-preflight-before-p210-transaction", "passed": spawn.index("call zx48_sys_spawn_preflight") < spawn.index("jp zx48_process_spawn_transaction")},
        {"name": "transaction-never-reserves-or-publishes-process-before-commit", "passed": "zx48_process_reserve_slot" not in before_commit and "PROC_READY" not in before_commit and "PROC_RUNNING" not in before_commit},
        {"name": "transaction-has-exactly-one-ready-publication-store", "passed": code.count("(ix+PROC_STATE),PROC_READY") == 1},
        {"name": "transaction-resolves-before-first-process-owned-allocation", "passed": transaction.index("call zx48_spawn_resolve_ram_object") < transaction.index("call zx48_alloc")},
        {"name": "transaction-rejects-non-bin-and-non-raw-resident-object", "passed": "(ix+OBJ_TYPE_ID)" in transaction and "cp OBJ_BIN" in transaction and "(ix+OBJ_FLAGS_BYTE)" in transaction},
        {"name": "target-mex-validator-checks-both-crcs-before-allocation", "passed": transaction.index("call zx48_process_spawn_validate_mex1") < transaction.index("call zx48_alloc") and "MEX_HDR_HEADER_CRC" in transaction and "MEX_HDR_BODY_CRC" in transaction},
        {"name": "all-three-allocations-precede-private-image-copy-and-context", "passed": transaction.count("call zx48_alloc") == 3 and transaction.rindex("call zx48_alloc") < transaction.index("ldir", transaction.index("; Copy immutable ARG1")) < transaction.index("call zx48_process_build_initial_context")},
        {"name": "live-parent-handles-are-validated-before-allocation", "passed": transaction.count("call zx48_handle_lookup") == 3 and transaction.rindex("call zx48_handle_lookup") < transaction.index("call zx48_alloc")},
        {"name": "shared-open-description-retains-occur-only-after-context", "passed": transaction.index("call zx48_process_build_initial_context") < transaction.index("call zx48_od_retain") and transaction.count("call zx48_od_retain") == 3},
        {"name": "rollback-releases-retains-before-freeing-bootstrap-stack-image", "passed": rollback.index("call zx48_od_release") < rollback.index("call zx48_free") and rollback.index("process_spawn_bootstrap_base") < rollback.index("process_spawn_stack_base") < rollback.index("process_spawn_image_base")},
        {"name": "commit-installs-only-child-std-handles-and-frees-three-through-seven", "passed": all(f"PROC_HANDLES+{index}" in commit for index in range(8)) and commit.count("HANDLE_FREE") >= 1},
        {"name": "commit-copies-parent-cwd-and-object-name", "passed": "process_spawn_parent_cwd" in commit and "PROC_CWD" in commit and "PROC_NAME" in commit},
        {"name": "spawn-success-does-not-schedule-or-yield", "passed": all(token not in code for token in ("zx48_schedule", "SYS_YIELD", "zx48_sys_yield"))},
        {"name": "resident-kernel-dispatch-remains-compact-p209-stub", "passed": "dw zx48_sys_getpid,zx48_sys_spawn_stub,zx48_sys_exec_stub" in syscall},
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
    if step != "P2.10":
        raise DriverError(f"Phase-2 atomic spawn step is not registered: {step}")

    assertions = _source_contract(root)
    failed = [item["name"] for item in assertions if item["passed"] is not True]
    require(not failed, f"static P2.10 contract failures: {failed}")

    kernel_command, kernel_binary, kernel_symbols = _assemble_kernel(root, run_command, require_project_tool)
    fixture_command, fixture_binary, fixture_symbols = _assemble_fixture(root, run_command, require_project_tool)

    kernel_values = _symbols(kernel_symbols, ("kernel_ordinary_used_end", "KERNEL_CODE_END"))
    free_bytes = kernel_values["KERNEL_CODE_END"] + 1 - kernel_values["kernel_ordinary_used_end"]
    require(free_bytes >= 0, "P2.10 resident ordinary kernel exceeds hard ceiling")
    assertions.append({
        "name": "resident-kernel-ordinary-code-remains-within-faff-ceiling",
        "passed": True,
        "used_end": f"0x{kernel_values['kernel_ordinary_used_end']:04X}",
        "code_end": f"0x{kernel_values['KERNEL_CODE_END']:04X}",
        "free_bytes": free_bytes,
    })

    names = (
        "p210_gateway", "process_table", "current_pid", "open_description_table",
        "memory_free_extents", "memory_live_allocations", "PROC_READY",
        "E_NOENT", "E_NOMEM", "E_BUSY", "E_FORMAT",
    )
    symbols = _symbols(fixture_symbols, names)
    fixture = fixture_binary.read_bytes()
    if action == "test":
        assertions.extend(_target_tests(root, symbols, fixture))

    return [kernel_command, fixture_command], {
        "v1/build/kernel.bin": sha256_file(kernel_binary),
        "v1/build/p210-spawn.bin": sha256_file(fixture_binary),
        "v1/src/kernel/process.asm": sha256_file(root / "v1/src/kernel/process.asm"),
        "v1/src/kernel/syscall.asm": sha256_file(root / "v1/src/kernel/syscall.asm"),
        "v1/tools-host/test-driver/phase2_spawn_atomic.py": sha256_file(root / "v1/tools-host/test-driver/phase2_spawn_atomic.py"),
        "v1/tools-host/test-driver/run.py": sha256_file(root / "v1/tools-host/test-driver/run.py"),
        "v1/tools-host/test-driver/phase2_gate.py": sha256_file(root / "v1/tools-host/test-driver/phase2_gate.py"),
    }, assertions
