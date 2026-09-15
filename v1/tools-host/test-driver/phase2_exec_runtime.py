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
import struct
from typing import Any, Callable

from driver_core import DriverError
from fuse_harness import FAIL_PC, PASS_PC, run_sna
import phase1
import phase2_spawn_atomic as p210

FIXTURE_CODE = 0xE000
PROGRAM_ADDRESS = 0x9000
TEST_STACK = 0x8F00

GOOD_PATH_ADDRESS = 0x5000
TEXT_PATH_ADDRESS = 0x5020
BAD_PATH_ADDRESS = 0x5040
ARG_ADDRESS = 0x5100
ENV_ADDRESS = 0x5180
PROC_ADDRESS = 0x5200

GOOD_RECORD = 0xB100
TEXT_RECORD = 0xB120
BAD_RECORD = 0xB140
GOOD_MEX = 0xC000
BAD_MEX = 0xC300

MIRROR_PROCESS = 0xA800
MIRROR_FREE = 0xA980
MIRROR_LIVE = 0xA9C0
MIRROR_IMAGE = 0xA9D0
MIRROR_BOOT = 0xA9E0
MIRROR_STACK = 0xAA00
EXPECTED_DESC = 0xAB00
EXPECTED_FREE = 0xAB40
EXPECTED_BOOT = 0xAB80

PROCESS_COUNT = 8
PROC_DESC_SIZE = 48
FREE_EXTENT_BYTES = 64

OLD_IMAGE_BASE = 0x6000
OLD_IMAGE_SIZE = 8
OLD_BOOTSTRAP_BASE = 0x6008
OLD_STACK_BASE = 0xDF80
OLD_STACK_SIZE = 0x0080

FREE_LOW_START = 0x6022
FREE_LOW_LENGTH = 0x1FDE
FREE_FAST_START = 0xD000
FREE_FAST_LENGTH = 0x0F80

NEW_IMAGE_BASE = FREE_LOW_START
NEW_IMAGE_STORED_SIZE = 512
NEW_BSS_SIZE = 2
NEW_IMAGE_ALLOC = NEW_IMAGE_STORED_SIZE + NEW_BSS_SIZE
NEW_STACK_BASE = 0xDF00
NEW_STACK_SIZE = 0x0080
NEW_SAVED_SP = NEW_STACK_BASE + NEW_STACK_SIZE - 12
NEW_BOOTSTRAP_BASE = NEW_IMAGE_BASE + NEW_IMAGE_ALLOC

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
PROC_RESERVED = 47


class Phase2ExecRuntimeError(DriverError):
    """Raised when deterministic P2.12 exec runtime certification regresses."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Phase2ExecRuntimeError(message)


def _word(value: int) -> bytes:
    return bytes((value & 0xFF, (value >> 8) & 0xFF))


def _ld_bc(value: int) -> bytes:
    return b"\x01" + _word(value)


def _jp_nc(address: int) -> bytes:
    return b"\xD2" + _word(address)


def _put_word(data: bytearray, offset: int, value: int) -> None:
    struct.pack_into("<H", data, offset, value & 0xFFFF)


def _arg1(token: bytes) -> bytes:
    total = 8 + len(token) + 1
    return b"ARG1" + bytes((1, 0)) + struct.pack("<H", total) + token + b"\0"


ENV1_EMPTY = b"ENV1\x00\x00\x08\x00"
OLD_ARG = _arg1(b"/bin/old")
OLD_BOOTSTRAP_EXACT = OLD_ARG + ENV1_EMPTY
OLD_BOOTSTRAP_SIZE = (len(OLD_BOOTSTRAP_EXACT) + 1) & ~1
NEW_ARG = _arg1(b"/bin/good")
NEW_BOOTSTRAP_EXACT = NEW_ARG + ENV1_EMPTY
NEW_BOOTSTRAP_SIZE = (len(NEW_BOOTSTRAP_EXACT) + 1) & ~1

require(OLD_BOOTSTRAP_BASE + OLD_BOOTSTRAP_SIZE == FREE_LOW_START, "P2.12 old bootstrap/free-map fixture boundary drifted")
require(NEW_BOOTSTRAP_BASE == 0x6224 and NEW_BOOTSTRAP_SIZE == 0x1A, "P2.12 deterministic replacement layout drifted")


def _mex(image: bytes, *, bss_size: int, entry: int = 0, stack: int = 64, relocations: tuple[int, ...] = ()) -> bytes:
    header = bytearray(24)
    header[:4] = b"MEX1"
    header[4] = 1
    header[5] = 0
    struct.pack_into("<H", header, 6, 24)
    struct.pack_into("<H", header, 8, len(image))
    struct.pack_into("<H", header, 10, bss_size)
    struct.pack_into("<H", header, 12, entry)
    struct.pack_into("<H", header, 14, stack)
    struct.pack_into("<H", header, 16, len(relocations))
    struct.pack_into("<H", header, 18, 24 + len(image))
    body = image + b"".join(struct.pack("<H", item) for item in relocations)
    struct.pack_into("<H", header, 20, p210._crc16(body))
    struct.pack_into("<H", header, 22, 0)
    struct.pack_into("<H", header, 22, p210._crc16(bytes(header)))
    return bytes(header) + body


def _proc1(*, path_ptr: int, arg: bytes, flags: int = 0, stdin: int = 0xFF, stdout: int = 0xFF, stderr: int = 0xFF) -> bytes:
    value = struct.pack(
        "<HHHHHBBBBH",
        path_ptr,
        ARG_ADDRESS,
        len(arg),
        ENV_ADDRESS,
        len(ENV1_EMPTY),
        stdin,
        stdout,
        stderr,
        flags,
        0,
    )
    require(len(value) == 16, "P2.12 PROC1 fixture size changed")
    return value


def _record(name: bytes, object_type: int, payload: int, length: int) -> bytes:
    return p210._record(name, object_type, payload, length)


def _free_extents_initial() -> bytes:
    data = bytearray(FREE_EXTENT_BYTES)
    struct.pack_into("<HH", data, 0, FREE_LOW_START, FREE_LOW_LENGTH)
    struct.pack_into("<HH", data, 4, FREE_FAST_START, FREE_FAST_LENGTH)
    return bytes(data)


def _free_extents_success() -> bytes:
    data = bytearray(FREE_EXTENT_BYTES)
    struct.pack_into("<HH", data, 0, OLD_IMAGE_BASE, FREE_LOW_START - OLD_IMAGE_BASE)
    struct.pack_into("<HH", data, 4, NEW_BOOTSTRAP_BASE + NEW_BOOTSTRAP_SIZE, 0x8000 - (NEW_BOOTSTRAP_BASE + NEW_BOOTSTRAP_SIZE))
    struct.pack_into("<HH", data, 8, FREE_FAST_START, NEW_STACK_BASE - FREE_FAST_START)
    struct.pack_into("<HH", data, 12, OLD_STACK_BASE, 0xE000 - OLD_STACK_BASE)
    return bytes(data)


def _old_process_table(proc_running: int, proc_started: int) -> bytes:
    table = bytearray(PROCESS_COUNT * PROC_DESC_SIZE)
    for pid in range(PROCESS_COUNT):
        base = pid * PROC_DESC_SIZE
        table[base + PROC_PID] = pid
        table[base + PROC_PARENT] = 0xFF
        table[base + PROC_HANDLES : base + PROC_HANDLES + 8] = b"\xFF" * 8

    p1 = PROC_DESC_SIZE
    table[p1 + PROC_PARENT] = 0
    table[p1 + PROC_STATE] = proc_running
    table[p1 + PROC_FLAGS] = 0
    _put_word(table, p1 + PROC_IMAGE_BASE, OLD_IMAGE_BASE)
    _put_word(table, p1 + PROC_IMAGE_SIZE, OLD_IMAGE_SIZE)
    _put_word(table, p1 + PROC_STACK_LOW, OLD_STACK_BASE)
    _put_word(table, p1 + PROC_STACK_HIGH, OLD_STACK_BASE + OLD_STACK_SIZE)
    _put_word(table, p1 + PROC_SAVED_SP, OLD_STACK_BASE + OLD_STACK_SIZE - 12)
    table[p1 + PROC_HANDLES : p1 + PROC_HANDLES + 8] = bytes(range(8))
    table[p1 + PROC_CWD] = 6
    table[p1 + PROC_NAME : p1 + PROC_NAME + 10] = b"old\0\0\0\0\0\0\0"
    _put_word(table, p1 + PROC_OWNED_BYTES, OLD_IMAGE_SIZE + OLD_STACK_SIZE + OLD_BOOTSTRAP_SIZE)
    _put_word(table, p1 + PROC_ARG_PTR, OLD_BOOTSTRAP_BASE)
    _put_word(table, p1 + PROC_ENV_PTR, OLD_BOOTSTRAP_BASE + len(OLD_ARG))
    table[p1 + PROC_PRIVATE_FLAGS] = proc_started
    table[p1 + PROC_RESERVED] = 0
    return bytes(table)


def _expected_success_descriptor(old_table: bytes, proc_running: int, proc_started: int) -> bytes:
    desc = bytearray(old_table[PROC_DESC_SIZE : 2 * PROC_DESC_SIZE])
    desc[PROC_STATE] = proc_running
    desc[PROC_FLAGS] = 0
    _put_word(desc, PROC_IMAGE_BASE, NEW_IMAGE_BASE)
    _put_word(desc, PROC_IMAGE_SIZE, NEW_IMAGE_ALLOC)
    _put_word(desc, PROC_STACK_LOW, NEW_STACK_BASE)
    _put_word(desc, PROC_STACK_HIGH, NEW_STACK_BASE + NEW_STACK_SIZE)
    _put_word(desc, PROC_SAVED_SP, NEW_SAVED_SP)
    desc[PROC_EXIT_STATUS] = 0
    desc[PROC_WAIT_OBJECT] = 0
    desc[PROC_WAKE_TICK : PROC_WAKE_TICK + 4] = b"\x00" * 4
    desc[PROC_NAME : PROC_NAME + 10] = b"good\0\0\0\0\0\0"
    _put_word(desc, PROC_OWNED_BYTES, NEW_IMAGE_ALLOC + NEW_STACK_SIZE + NEW_BOOTSTRAP_SIZE)
    _put_word(desc, PROC_ARG_PTR, NEW_BOOTSTRAP_BASE)
    _put_word(desc, PROC_ENV_PTR, NEW_BOOTSTRAP_BASE + len(NEW_ARG))
    desc[PROC_PRIVATE_FLAGS] = proc_started
    desc[PROC_RESERVED] = 0
    return bytes(desc)


def _old_image() -> bytes:
    return b"OLDIMAGE"


def _old_bootstrap() -> bytes:
    return OLD_BOOTSTRAP_EXACT + bytes((0xCC,)) * (OLD_BOOTSTRAP_SIZE - len(OLD_BOOTSTRAP_EXACT))


def _old_stack() -> bytes:
    return bytes(((index * 37 + 11) & 0xFF) for index in range(OLD_STACK_SIZE))


def _assemble_fixture(root: Path, run_command: Callable[..., Any], require_project_tool: Callable[[Path, str | Path], Path]):
    assembler = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    source = build / "p212-exec.asm"
    binary = build / "p212-exec.bin"
    symbols = build / "p212-exec.sym"
    listing = build / "p212-exec.lst"
    source.write_text(
        "    DEVICE ZXSPECTRUM48\n"
        "    INCLUDE \"../include/zx48ux.inc\"\n"
        "    INCLUDE \"../include/mex1.inc\"\n"
        "    INCLUDE \"../src/kernel/syscall.asm\"\n"
        "    INCLUDE \"../src/kernel/memory.asm\"\n"
        "    INCLUDE \"../src/kernel/process.asm\"\n"
        "    INCLUDE \"../src/kernel/objects.asm\"\n"
        "    INCLUDE \"../src/kernel/phase2_exec.inc\"\n"
        "PANIC_SCHEDULER EQU $03\n"
        f"    ORG ${FIXTURE_CODE:04X}\n"
        "p212_start:\n"
        "    EMIT_MEMORY_ROUTINES\n"
        "    EMIT_USER_RANGE_VALIDATION_ROUTINE\n"
        "    EMIT_PROCESS_CAPACITY_ROUTINE\n"
        "    EMIT_MEX1_RELOCATION_ROUTINES\n"
        "    EMIT_ARG1_ROUTINES\n"
        "    EMIT_ENV1_ROUTINES\n"
        "    EMIT_INITIAL_CONTEXT_ROUTINES\n"
        "    EMIT_SPAWN_TRANSACTION_ROUTINES\n"
        "    EMIT_EXEC_TRANSACTION_ROUTINES\n"
        "p212_gateway:\n"
        "    ld (syscall_arg_hl),hl\n"
        "    jp zx48_sys_exec\n"
        "zx48_process_lookup:\n"
        "    cp MAX_PROCESSES\n"
        "    jr nc,p212_process_noent\n"
        "    ld c,a\n"
        "    ld ix,process_table\n"
        "    or a\n"
        "    jr z,p212_process_have_ptr\n"
        "    ld b,a\n"
        "    ld de,PROC_DESC_SIZE\n"
        "p212_process_ptr_loop:\n"
        "    add ix,de\n"
        "    djnz p212_process_ptr_loop\n"
        "p212_process_have_ptr:\n"
        "    ld a,(ix+PROC_STATE)\n"
        "    or a\n"
        "    jr z,p212_process_noent\n"
        "    xor a\n"
        "    ret\n"
        "p212_process_noent:\n"
        "    ld a,E_NOENT\n"
        "    scf\n"
        "    ret\n"
        "zx48_handle_lookup:\n"
        "    ld c,a\n"
        "    xor a\n"
        "    ret\n"
        "zx48_od_retain:\n"
        "    xor a\n"
        "    ret\n"
        "zx48_od_release:\n"
        "    xor a\n"
        "    ret\n"
        "zx48_spawn_resolve_ram_object:\n"
        "    push hl\n"
        "    ld de,p212_path_good\n"
        "    call p212_cstr_equal\n"
        "    pop hl\n"
        "    jr z,p212_resolve_good\n"
        "    push hl\n"
        "    ld de,p212_path_text\n"
        "    call p212_cstr_equal\n"
        "    pop hl\n"
        "    jr z,p212_resolve_text\n"
        "    push hl\n"
        "    ld de,p212_path_bad\n"
        "    call p212_cstr_equal\n"
        "    pop hl\n"
        "    jr z,p212_resolve_bad\n"
        "    ld a,E_NOENT\n"
        "    scf\n"
        "    ret\n"
        "p212_resolve_good:\n"
        f"    ld ix,${GOOD_RECORD:04X}\n"
        "    xor a\n"
        "    ret\n"
        "p212_resolve_text:\n"
        f"    ld ix,${TEXT_RECORD:04X}\n"
        "    xor a\n"
        "    ret\n"
        "p212_resolve_bad:\n"
        f"    ld ix,${BAD_RECORD:04X}\n"
        "    xor a\n"
        "    ret\n"
        "p212_cstr_equal:\n"
        "    ld a,(de)\n"
        "    cp (hl)\n"
        "    ret nz\n"
        "    or a\n"
        "    ret z\n"
        "    inc de\n"
        "    inc hl\n"
        "    jr p212_cstr_equal\n"
        "zx48_panic:\n"
        "    jp $0000\n"
        "syscall_arg_hl: dw 0\n"
        "current_pid: db 1\n"
        "process_table: defs MAX_PROCESSES*PROC_DESC_SIZE,0\n"
        "p212_path_good: db '/bin/good',0\n"
        "p212_path_text: db '/bin/text',0\n"
        "p212_path_bad: db '/bin/bad',0\n"
        "p212_end:\n"
        "    SAVEBIN \"p212-exec.bin\",p212_start,p212_end-p212_start\n",
        encoding="utf-8",
        newline="\n",
    )
    result = run_command(
        [assembler, "--nologo", "--lst=p212-exec.lst", "--sym=p212-exec.sym", "p212-exec.asm"],
        cwd=build,
        timeout_seconds=30.0,
    )
    require(not result.timed_out and result.exit_code == 0, f"P2.12 exec fixture assembly failed: {result.stderr or result.stdout}")
    require(binary.is_file() and 0 < binary.stat().st_size < 0x2000, "P2.12 fixture must fit E000-FFFF")
    require(symbols.is_file() and listing.is_file(), "P2.12 fixture symbols/listing missing")
    return result, binary, symbols


def _patch(fixture: bytes, regions: tuple[tuple[int, bytes], ...]):
    def patch(ram: bytearray) -> None:
        start = FIXTURE_CODE - 0x4000
        ram[start : start + len(fixture)] = fixture
        for address, payload in regions:
            require(0x4000 <= address < 0x10000, f"P2.12 patch address outside RAM: 0x{address:04X}")
            require(address + len(payload) <= 0x10000, f"P2.12 patch crosses RAM: 0x{address:04X}")
            offset = address - 0x4000
            ram[offset : offset + len(payload)] = payload
    return patch


def _append_compare(code: bytearray, origin: int, actual: int, expected: int, length: int) -> None:
    code += phase1._ld_hl(actual) + phase1._ld_de(expected) + _ld_bc(length)
    loop = origin + len(code)
    code += b"\x1A\xBE" + phase1._jp_nz(FAIL_PC) + b"\x23\x13\x0B\x78\xB1" + phase1._jp_nz(loop)


def _expect_byte(address: int, value: int) -> bytes:
    return b"\x3A" + _word(address) + bytes((0xFE, value & 0xFF)) + phase1._jp_nz(FAIL_PC)


def _base_regions(symbols: dict[str, int], *, proc: bytes, path_address: int, path: bytes, arg: bytes, good_mex: bytes, bad_mex: bytes) -> tuple[tuple[int, bytes], ...]:
    return (
        (GOOD_PATH_ADDRESS, b"/bin/good\0"),
        (TEXT_PATH_ADDRESS, b"/bin/text\0"),
        (BAD_PATH_ADDRESS, b"/bin/bad\0"),
        (ARG_ADDRESS, arg),
        (ENV_ADDRESS, ENV1_EMPTY),
        (PROC_ADDRESS, proc),
        (GOOD_MEX, good_mex),
        (BAD_MEX, bad_mex),
        (GOOD_RECORD, _record(b"good", 2, GOOD_MEX, len(good_mex))),
        (TEXT_RECORD, _record(b"text", 1, GOOD_MEX, len(good_mex))),
        (BAD_RECORD, _record(b"bad", 2, BAD_MEX, len(bad_mex))),
        (symbols["process_table"], _old_process_table(symbols["PROC_RUNNING"], symbols["PROC_PRIVATE_STARTED"])),
        (symbols["current_pid"], b"\x01"),
        (symbols["memory_free_extents"], _free_extents_initial()),
        (symbols["memory_live_allocations"], b"\x03\x00"),
        (OLD_IMAGE_BASE, _old_image()),
        (OLD_BOOTSTRAP_BASE, _old_bootstrap()),
        (OLD_STACK_BASE, _old_stack()),
    )


def _success_image(symbols: dict[str, int], expected_desc: bytes, expected_free: bytes) -> bytes:
    code = bytearray()
    _append_compare(code, NEW_IMAGE_BASE, symbols["process_table"] + PROC_DESC_SIZE, EXPECTED_DESC, len(expected_desc))
    _append_compare(code, NEW_IMAGE_BASE, symbols["memory_free_extents"], EXPECTED_FREE, len(expected_free))
    _append_compare(code, NEW_IMAGE_BASE, NEW_BOOTSTRAP_BASE, EXPECTED_BOOT, len(NEW_BOOTSTRAP_EXACT))
    code += _expect_byte(symbols["current_pid"], 1)
    code += _expect_byte(NEW_IMAGE_BASE + NEW_IMAGE_STORED_SIZE, 0)
    code += _expect_byte(NEW_IMAGE_BASE + NEW_IMAGE_STORED_SIZE + 1, 0)
    code += b"\x2A" + _word(symbols["memory_live_allocations"]) + phase1._ld_de(3) + b"\xB7\xED\x52" + phase1._jp_nz(FAIL_PC)
    code += phase1._jp(PASS_PC)
    require(len(code) <= NEW_IMAGE_STORED_SIZE, f"P2.12 success assertion image too large: {len(code)}")
    return bytes(code) + b"\x00" * (NEW_IMAGE_STORED_SIZE - len(code))


def _failure_case(
    root: Path,
    symbols: dict[str, int],
    fixture: bytes,
    *,
    path_address: int,
    path: bytes,
    expected_error: int,
    good_mex: bytes,
    bad_mex: bytes,
    stdin: int = 0xFF,
) -> None:
    arg = _arg1(path.rstrip(b"\0"))
    proc = _proc1(path_ptr=path_address, arg=arg, stdin=stdin)
    process = _old_process_table(symbols["PROC_RUNNING"], symbols["PROC_PRIVATE_STARTED"])
    free = _free_extents_initial()
    live = b"\x03\x00"
    old_image = _old_image()
    old_boot = _old_bootstrap()
    old_stack = _old_stack()

    code = bytearray(b"\xF3" + phase1._ld_sp(TEST_STACK))
    code += phase1._ld_hl(PROC_ADDRESS) + phase1._call(symbols["p212_gateway"])
    code += _jp_nc(FAIL_PC) + bytes((0xFE, expected_error & 0xFF)) + phase1._jp_nz(FAIL_PC)
    _append_compare(code, PROGRAM_ADDRESS, symbols["process_table"], MIRROR_PROCESS, len(process))
    _append_compare(code, PROGRAM_ADDRESS, symbols["memory_free_extents"], MIRROR_FREE, len(free))
    _append_compare(code, PROGRAM_ADDRESS, symbols["memory_live_allocations"], MIRROR_LIVE, len(live))
    _append_compare(code, PROGRAM_ADDRESS, OLD_IMAGE_BASE, MIRROR_IMAGE, len(old_image))
    _append_compare(code, PROGRAM_ADDRESS, OLD_BOOTSTRAP_BASE, MIRROR_BOOT, len(old_boot))
    _append_compare(code, PROGRAM_ADDRESS, OLD_STACK_BASE, MIRROR_STACK, len(old_stack))
    code += _expect_byte(symbols["current_pid"], 1)
    code += phase1._jp(PASS_PC)

    regions = _base_regions(symbols, proc=proc, path_address=path_address, path=path, arg=arg, good_mex=good_mex, bad_mex=bad_mex) + (
        (MIRROR_PROCESS, process),
        (MIRROR_FREE, free),
        (MIRROR_LIVE, live),
        (MIRROR_IMAGE, old_image),
        (MIRROR_BOOT, old_boot),
        (MIRROR_STACK, old_stack),
    )
    run_sna(root, bytes(code), patch=_patch(fixture, regions))


def _success_case(root: Path, symbols: dict[str, int], fixture: bytes, bad_mex: bytes) -> None:
    old_process = _old_process_table(symbols["PROC_RUNNING"], symbols["PROC_PRIVATE_STARTED"])
    expected_desc = _expected_success_descriptor(old_process, symbols["PROC_RUNNING"], symbols["PROC_PRIVATE_STARTED"])
    expected_free = _free_extents_success()
    image = _success_image(symbols, expected_desc, expected_free)
    good_mex = _mex(image, bss_size=NEW_BSS_SIZE, entry=0, stack=64)
    proc = _proc1(path_ptr=GOOD_PATH_ADDRESS, arg=NEW_ARG)
    regions = _base_regions(symbols, proc=proc, path_address=GOOD_PATH_ADDRESS, path=b"/bin/good\0", arg=NEW_ARG, good_mex=good_mex, bad_mex=bad_mex) + (
        (EXPECTED_DESC, expected_desc),
        (EXPECTED_FREE, expected_free),
        (EXPECTED_BOOT, NEW_BOOTSTRAP_EXACT),
    )
    code = b"\xF3" + phase1._ld_sp(TEST_STACK) + phase1._ld_hl(PROC_ADDRESS) + phase1._call(symbols["p212_gateway"]) + phase1._jp(FAIL_PC)
    run_sna(root, code, patch=_patch(fixture, regions))


def _target_tests(root: Path, symbols: dict[str, int], fixture: bytes) -> list[dict[str, object]]:
    require(symbols["PROC_DESC_SIZE"] == PROC_DESC_SIZE, "P2.12 process descriptor ABI changed")
    require(symbols["PROC_RUNNING"] == 2, "P2.12 RUNNING state ABI changed")
    require(symbols["E_INVAL"] == 1 and symbols["E_FORMAT"] == 11, "P2.12 errno ABI changed")

    # A relocation overlap is intentionally detected only after all three private
    # replacement allocations exist, forcing the full rollback path.
    bad_mex = p210._mex(relocations=(0, 1))

    _success_case(root, symbols, fixture, bad_mex)

    good_placeholder = _mex(b"\xC3\x00\xB0" + b"\x00" * (NEW_IMAGE_STORED_SIZE - 3), bss_size=NEW_BSS_SIZE)
    _failure_case(
        root,
        symbols,
        fixture,
        path_address=TEXT_PATH_ADDRESS,
        path=b"/bin/text\0",
        expected_error=symbols["E_FORMAT"],
        good_mex=good_placeholder,
        bad_mex=bad_mex,
    )
    _failure_case(
        root,
        symbols,
        fixture,
        path_address=BAD_PATH_ADDRESS,
        path=b"/bin/bad\0",
        expected_error=symbols["E_FORMAT"],
        good_mex=good_placeholder,
        bad_mex=bad_mex,
    )
    _failure_case(
        root,
        symbols,
        fixture,
        path_address=GOOD_PATH_ADDRESS,
        path=b"/bin/good\0",
        expected_error=symbols["E_INVAL"],
        good_mex=good_placeholder,
        bad_mex=bad_mex,
        stdin=0,
    )

    return [
        {"name": "exec-success-replaces-image-stack-bootstrap-and-enters-new-image-without-old-return", "passed": True},
        {"name": "exec-success-preserves-pid-parent-all-eight-handles-and-cwd-byte-exactly", "passed": True},
        {"name": "exec-success-releases-old-extents-from-authoritative-owned-byte-accounting", "passed": True},
        {"name": "exec-resolved-non-bin-fails-e-format-with-old-process-allocator-and-bytes-identical", "passed": True},
        {"name": "exec-late-relocation-failure-rolls-back-all-private-replacement-extents-byte-identically", "passed": True},
        {"name": "exec-rejects-non-ff-standard-handle-selector-before-mutation", "passed": True},
    ]


def run(
    root: Path,
    *,
    execute: bool,
    run_command: Callable[..., Any],
    require_project_tool: Callable[[Path, str | Path], Path],
):
    command, binary, symbol_path = _assemble_fixture(root, run_command, require_project_tool)
    names = (
        "p212_gateway",
        "process_table",
        "current_pid",
        "memory_free_extents",
        "memory_live_allocations",
        "PROC_DESC_SIZE",
        "PROC_RUNNING",
        "PROC_PRIVATE_STARTED",
        "E_INVAL",
        "E_FORMAT",
    )
    symbols = p210._symbols(symbol_path, names)
    assertions: list[dict[str, object]] = [
        {"name": "p212-runtime-fixture-assembles-with-production-exec-source", "passed": True},
        {"name": "p212-runtime-fixture-preserves-frozen-48-byte-process-descriptor", "passed": symbols["PROC_DESC_SIZE"] == PROC_DESC_SIZE},
    ]
    if execute:
        assertions.extend(_target_tests(root, symbols, binary.read_bytes()))
    return command, binary, assertions
