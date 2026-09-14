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
TEST_STACK = 0xBFC0
ARG_ADDRESS = 0xC000
ENV_ADDRESS = 0xC400
TOKEN_ADDRESS = 0xC800
HEADER_ADDRESS = 0xC900
RESULT_BASE = 0xCA00
ARENA_START = 0x6000
ARENA_SIZE = 0x8000
FAST_END_EXCLUSIVE = 0xE000
ARG1_HEADER_SIZE = 8
ARG1_MAX_SIZE = 256
ARG1_MAX_COUNT = 16
ENV1_HEADER_SIZE = 8
ENV1_MAX_SIZE = 256
ENV1_MAX_COUNT = 8
ENV1_MAX_NAME = 15
ENV1_MAX_VALUE = 63
BOOTSTRAP_MAX_PAYLOAD = 512
MIN_STACK = 64
STACK_BOOTSTRAP_BYTES = 64


class Phase2Env1Error(DriverError):
    """Raised when the P2.07 ENV1/shared-bootstrap contract regresses."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Phase2Env1Error(message)


def _word(value: int) -> bytes:
    return bytes((value & 0xFF, (value >> 8) & 0xFF))


def _ld_ix(value: int) -> bytes:
    return b"\xDD\x21" + _word(value)


def _ld_bc(value: int) -> bytes:
    return b"\x01" + _word(value)


def _ld_a(value: int) -> bytes:
    return bytes((0x3E, value & 0xFF))


def _jp_nc(address: int) -> bytes:
    return b"\xD2" + _word(address)


def _store_de(address: int) -> bytes:
    return b"\xED\x53" + _word(address)


def _store_bc(address: int) -> bytes:
    return b"\xED\x43" + _word(address)


def _expect_word(address: int, value: int) -> bytes:
    return (
        b"\x2A" + _word(address)
        + phase1._ld_de(value)
        + b"\xB7\xED\x52"
        + phase1._jp_nz(FAIL_PC)
    )


def _expect_hl(value: int) -> bytes:
    return phase1._ld_de(value) + b"\xB7\xED\x52" + phase1._jp_nz(FAIL_PC)


def _arg1(arguments: list[bytes], *, total: int | None = None) -> bytes:
    require(1 <= len(arguments) <= ARG1_MAX_COUNT, "host ARG1 builder requires 1..16 arguments")
    payload = b"".join(argument + b"\0" for argument in arguments)
    length = ARG1_HEADER_SIZE + len(payload)
    encoded_total = length if total is None else total
    header = bytearray(ARG1_HEADER_SIZE)
    header[:4] = b"ARG1"
    header[4] = len(arguments)
    struct.pack_into("<H", header, 6, encoded_total & 0xFFFF)
    return bytes(header) + payload


def _max_arg1() -> bytes:
    arguments = [b"cmd"] + [b"a" * 15 for _ in range(14)] + [b"b" * 19]
    block = _arg1(arguments)
    require(len(block) == ARG1_MAX_SIZE, "P2.07 host ARG1 max fixture is not exactly 256 bytes")
    return block


def _env1(
    entries: list[tuple[bytes, bytes]],
    *,
    magic: bytes = b"ENV1",
    reserved: int = 0,
    total: int | None = None,
    enforce_host_limits: bool = True,
) -> bytes:
    if enforce_host_limits:
        require(0 <= len(entries) <= ENV1_MAX_COUNT, "host ENV1 builder requires 0..8 entries")
        for name, value in entries:
            require(1 <= len(name) <= ENV1_MAX_NAME, "host ENV1 builder name outside 1..15 bytes")
            require(len(value) <= ENV1_MAX_VALUE, "host ENV1 builder value exceeds 63 bytes")
    payload = b"".join(name + b"=" + value + b"\0" for name, value in entries)
    length = ENV1_HEADER_SIZE + len(payload)
    encoded_total = length if total is None else total
    header = bytearray(ENV1_HEADER_SIZE)
    header[:4] = magic
    header[4] = len(entries) & 0xFF
    header[5] = reserved & 0xFF
    struct.pack_into("<H", header, 6, encoded_total & 0xFFFF)
    return bytes(header) + payload


def _max_env1() -> bytes:
    entries = [(f"A{index}".encode("ascii"), b"v" * 27) for index in range(8)]
    block = _env1(entries)
    require(len(block) == ENV1_MAX_SIZE, "P2.07 host ENV1 max fixture is not exactly 256 bytes")
    return block


def _stack_header(stack_size: int) -> bytes:
    header = bytearray(24)
    header[:4] = b"MEX1"
    struct.pack_into("<H", header, 14, stack_size)
    return bytes(header)


def _patch(fixture: bytes, regions: tuple[tuple[int, bytes], ...]):
    def patch(ram: bytearray) -> None:
        start = FIXTURE_CODE - 0x4000
        ram[start:start + len(fixture)] = fixture
        for address, payload in regions:
            require(0x4000 <= address <= 0xFFFF, f"P2.07 patch address outside RAM: 0x{address:04X}")
            require(address + len(payload) <= 0x10000, f"P2.07 patch crosses address space: 0x{address:04X}")
            offset = address - 0x4000
            ram[offset:offset + len(payload)] = payload
    return patch


def _assemble_fixture(
    root: Path,
    run_command: Callable[..., Any],
    require_project_tool: Callable[[Path, str | Path], Path],
):
    assembler = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    source = build / "p207-env1.asm"
    binary = build / "p207-env1.bin"
    listing = build / "p207-env1.lst"
    symbols = build / "p207-env1.sym"
    source.write_text(
        "    DEVICE ZXSPECTRUM48\n"
        "    INCLUDE \"../include/zx48ux.inc\"\n"
        "    INCLUDE \"../include/mex1.inc\"\n"
        "    INCLUDE \"../src/kernel/memory.asm\"\n"
        "    INCLUDE \"../src/kernel/process.asm\"\n"
        f"    ORG ${FIXTURE_CODE:04X}\n"
        "p207_env1_start:\n"
        "    EMIT_MEMORY_ROUTINES\n"
        "    EMIT_ARG1_ROUTINES\n"
        "    EMIT_MEX1_STACK_ROUTINES\n"
        "    EMIT_ENV1_ROUTINES\n"
        "zx48_process_count:\n"
        "    xor a\n"
        "    ret\n"
        "p207_env1_end:\n"
        "    SAVEBIN \"p207-env1.bin\",p207_env1_start,p207_env1_end-p207_env1_start\n",
        encoding="utf-8",
        newline="\n",
    )
    result = run_command(
        [assembler, "--nologo", "--lst=p207-env1.lst", "--sym=p207-env1.sym", "p207-env1.asm"],
        cwd=build,
        timeout_seconds=30.0,
    )
    require(not result.timed_out and result.exit_code == 0, f"P2.07 ENV1 fixture assembly failed: {result.stderr or result.stdout}")
    require(binary.is_file() and 0 < binary.stat().st_size < 0x2000, "P2.07 ENV1 fixture binary missing or implausibly large")
    require(symbols.is_file() and listing.is_file(), "P2.07 ENV1 fixture symbols/listing missing")
    return result, binary, symbols


def _symbols(path: Path, names: tuple[str, ...]) -> dict[str, int]:
    text = path.read_text(encoding="utf-8", errors="replace")
    found: dict[str, int] = {}
    for name in names:
        pattern = re.compile(rf"^{re.escape(name)}:\s+equ\s+0x([0-9A-Fa-f]+)\s*$", re.IGNORECASE)
        for line in text.splitlines():
            match = pattern.match(line.strip())
            if match is not None:
                found[name] = int(match.group(1), 16)
                break
        require(name in found, f"P2.07 fixture symbol missing: {name}")
    return found


def _call_arg_validate(validator: int, block_length: int, token: bytes) -> tuple[bytes, tuple[tuple[int, bytes], ...]]:
    return (
        _ld_ix(ARG_ADDRESS) + _ld_bc(block_length) + phase1._ld_hl(TOKEN_ADDRESS) + phase1._call(validator),
        ((TOKEN_ADDRESS, token + b"\0"),),
    )


def _call_env_build(
    builder: int,
    arg_length: int,
    env_length: int,
    *,
    arg_source: int = ARG_ADDRESS,
    env_source: int = ENV_ADDRESS,
) -> bytes:
    return (
        _ld_ix(arg_source)
        + _ld_bc(arg_length)
        + phase1._ld_hl(env_source)
        + phase1._ld_de(env_length)
        + phase1._call(builder)
    )


def _compare_blocks(source: int, destination: int, length: int, program_address: int) -> bytes:
    code = bytearray()
    code += phase1._ld_hl(source)
    code += phase1._ld_de(destination)
    code += _ld_bc(length)
    loop = program_address + len(code)
    code += b"\x1A\xBE" + phase1._jp_nz(FAIL_PC)
    code += b"\x23\x13\x0B\x78\xB1"
    code += phase1._jp_nz(loop)
    return bytes(code)


def _success_case(
    root: Path,
    symbols: dict[str, int],
    fixture: bytes,
    arg: bytes,
    env: bytes,
    token: bytes,
) -> None:
    memory_init = symbols["zx48_memory_init"]
    validator = symbols["zx48_arg1_validate"]
    builder = symbols["zx48_env1_build"]
    alloc = symbols["zx48_alloc"]
    free = symbols["zx48_free"]
    live_count = symbols["memory_live_allocations"]
    combined = len(arg) + len(env)
    rounded = (combined + 1) & ~1
    env_copy = ARENA_START + len(arg)

    code = bytearray(b"\xF3" + phase1._ld_sp(TEST_STACK))
    code += phase1._call(memory_init)
    validate_call, _ = _call_arg_validate(validator, len(arg), token)
    code += validate_call + phase1._jp_c(FAIL_PC)
    code += _expect_word(live_count, 0)
    code += _call_env_build(builder, len(arg), len(env)) + phase1._jp_c(FAIL_PC)
    code += b"\x22" + _word(RESULT_BASE)
    code += _store_de(RESULT_BASE + 2)
    code += _store_bc(RESULT_BASE + 4)
    code += _expect_word(RESULT_BASE, ARENA_START)
    code += _expect_word(RESULT_BASE + 2, env_copy)
    code += _expect_word(RESULT_BASE + 4, len(arg))
    code += _expect_word(live_count, 1)
    code += _compare_blocks(ARG_ADDRESS, ARENA_START, len(arg), 0x9000 + len(code))
    code += _compare_blocks(ENV_ADDRESS, env_copy, len(env), 0x9000 + len(code))
    # The next low ANY allocation must begin after the builder's rounded extent.
    code += _ld_a(symbols["ALLOC_ANY"]) + _ld_bc(2) + phase1._call(alloc) + phase1._jp_c(FAIL_PC)
    code += _expect_hl(ARENA_START + rounded)
    code += _expect_word(live_count, 2)
    code += phase1._ld_hl(ARENA_START + rounded) + _ld_bc(2) + phase1._call(free) + phase1._jp_c(FAIL_PC)
    code += phase1._ld_hl(ARENA_START) + _ld_bc(rounded) + phase1._call(free) + phase1._jp_c(FAIL_PC)
    code += _expect_word(live_count, 0)
    code += phase1._jp(PASS_PC)
    run_sna(
        root,
        bytes(code),
        patch=_patch(fixture, ((ARG_ADDRESS, arg), (ENV_ADDRESS, env), (TOKEN_ADDRESS, token + b"\0"))),
    )


def _format_rejection_case(
    root: Path,
    symbols: dict[str, int],
    fixture: bytes,
    env: bytes,
    *,
    supplied_length: int | None = None,
    env_source: int = ENV_ADDRESS,
    arg_length: int | None = None,
    arg_source: int = ARG_ADDRESS,
) -> None:
    memory_init = symbols["zx48_memory_init"]
    builder = symbols["zx48_env1_build"]
    live_count = symbols["memory_live_allocations"]
    e_format = symbols["E_FORMAT"]
    arg = _arg1([b"x"])
    length = len(env) if supplied_length is None else supplied_length
    effective_arg_length = len(arg) if arg_length is None else arg_length

    code = bytearray(b"\xF3" + phase1._ld_sp(TEST_STACK))
    code += phase1._call(memory_init)
    code += _call_env_build(
        builder, effective_arg_length, length, arg_source=arg_source, env_source=env_source
    ) + _jp_nc(FAIL_PC)
    code += bytes((0xFE, e_format & 0xFF)) + phase1._jp_nz(FAIL_PC)
    code += _expect_word(live_count, 0)
    code += phase1._jp(PASS_PC)
    regions: list[tuple[int, bytes]] = []
    if arg_source == ARG_ADDRESS:
        regions.append((ARG_ADDRESS, arg))
    if env_source == ENV_ADDRESS:
        regions.append((ENV_ADDRESS, env))
    run_sna(root, bytes(code), patch=_patch(fixture, tuple(regions)))


def _allocation_failure_case(root: Path, symbols: dict[str, int], fixture: bytes) -> None:
    memory_init = symbols["zx48_memory_init"]
    alloc = symbols["zx48_alloc"]
    free = symbols["zx48_free"]
    builder = symbols["zx48_env1_build"]
    live_count = symbols["memory_live_allocations"]
    e_nomem = symbols["E_NOMEM"]
    arg = _arg1([b"x"])
    env = _env1([(b"A", b"")])

    code = bytearray(b"\xF3" + phase1._ld_sp(TEST_STACK))
    code += phase1._call(memory_init)
    code += _ld_a(symbols["ALLOC_ANY"]) + _ld_bc(ARENA_SIZE) + phase1._call(alloc) + phase1._jp_c(FAIL_PC)
    code += _expect_hl(ARENA_START)
    code += _expect_word(live_count, 1)
    code += _call_env_build(builder, len(arg), len(env)) + _jp_nc(FAIL_PC)
    code += bytes((0xFE, e_nomem & 0xFF)) + phase1._jp_nz(FAIL_PC)
    code += _expect_word(live_count, 1)
    code += phase1._ld_hl(ARENA_START) + _ld_bc(ARENA_SIZE) + phase1._call(free) + phase1._jp_c(FAIL_PC)
    code += _expect_word(live_count, 0)
    code += phase1._jp(PASS_PC)
    run_sna(root, bytes(code), patch=_patch(fixture, ((ARG_ADDRESS, arg), (ENV_ADDRESS, env))))


def _deep_stack_case(root: Path, symbols: dict[str, int], fixture: bytes) -> None:
    memory_init = symbols["zx48_memory_init"]
    validator = symbols["zx48_arg1_validate"]
    builder = symbols["zx48_env1_build"]
    stack_alloc = symbols["zx48_mex1_alloc_stack"]
    live_count = symbols["memory_live_allocations"]
    arg = _max_arg1()
    env = _max_env1()
    token = b"cmd"
    combined = len(arg) + len(env)
    require(combined == BOOTSTRAP_MAX_PAYLOAD, "P2.07 max combined bootstrap fixture is not 512 bytes")
    stack_total = MIN_STACK + STACK_BOOTSTRAP_BYTES
    expected_stack_base = FAST_END_EXCLUSIVE - stack_total
    filler = ARENA_SIZE - BOOTSTRAP_MAX_PAYLOAD - stack_total
    bootstrap_base = ARENA_START + filler
    require(bootstrap_base + BOOTSTRAP_MAX_PAYLOAD == expected_stack_base, "P2.07 adjacency fixture geometry changed")

    code = bytearray(b"\xF3" + phase1._ld_sp(TEST_STACK))
    code += phase1._call(memory_init)
    # Consume all but the exact max bootstrap + minimum stack, making the two
    # certified allocations adjacent at the FAST top without overlapping.
    code += _ld_a(symbols["ALLOC_ANY"]) + _ld_bc(filler) + phase1._call(symbols["zx48_alloc"]) + phase1._jp_c(FAIL_PC)
    code += _expect_hl(ARENA_START)
    code += _expect_word(live_count, 1)
    validate_call, _ = _call_arg_validate(validator, len(arg), token)
    code += validate_call + phase1._jp_c(FAIL_PC)
    code += _call_env_build(builder, len(arg), len(env)) + phase1._jp_c(FAIL_PC)
    code += b"\x22" + _word(RESULT_BASE)
    code += _store_de(RESULT_BASE + 2)
    code += _store_bc(RESULT_BASE + 4)
    code += _expect_word(RESULT_BASE, bootstrap_base)
    code += _expect_word(RESULT_BASE + 2, bootstrap_base + len(arg))
    code += _expect_word(RESULT_BASE + 4, len(arg))
    code += _expect_word(live_count, 2)
    code += _ld_ix(HEADER_ADDRESS) + phase1._call(stack_alloc) + phase1._jp_c(FAIL_PC)
    code += _expect_hl(expected_stack_base)
    code += _expect_word(live_count, 3)
    code += phase1._ld_sp(FAST_END_EXCLUSIVE)
    code += phase1._ld_hl(0xA55A)
    code += b"\xE5" * 64
    code += _compare_blocks(ARG_ADDRESS, bootstrap_base, len(arg), 0x9000 + len(code))
    code += _compare_blocks(ENV_ADDRESS, bootstrap_base + len(arg), len(env), 0x9000 + len(code))
    code += _expect_word(live_count, 3)
    code += phase1._jp(PASS_PC)
    run_sna(
        root,
        bytes(code),
        patch=_patch(
            fixture,
            (
                (ARG_ADDRESS, arg),
                (ENV_ADDRESS, env),
                (TOKEN_ADDRESS, token + b"\0"),
                (HEADER_ADDRESS, _stack_header(MIN_STACK)),
            ),
        ),
    )


def _target_tests(root: Path, symbols: dict[str, int], fixture: bytes) -> list[dict[str, object]]:
    require(symbols["ALLOC_ANY"] == 0, "P2.07 ALLOC_ANY ABI value changed")
    require(symbols["E_NOMEM"] == 0x03, "P2.07 E_NOMEM ABI value changed")
    require(symbols["E_FORMAT"] == 0x0B, "P2.07 E_FORMAT ABI value changed")
    require(symbols["ENV1_HEADER_SIZE"] == ENV1_HEADER_SIZE, "P2.07 ENV1 header size changed")
    require(symbols["ENV1_MAX_SIZE"] == ENV1_MAX_SIZE, "P2.07 ENV1 maximum size changed")
    require(symbols["ENV1_MAX_COUNT"] == ENV1_MAX_COUNT, "P2.07 ENV1 maximum entry count changed")
    require(symbols["ENV1_MAX_NAME"] == ENV1_MAX_NAME, "P2.07 ENV1 maximum name length changed")
    require(symbols["ENV1_MAX_VALUE"] == ENV1_MAX_VALUE, "P2.07 ENV1 maximum value length changed")
    require(symbols["BOOTSTRAP_MAX_PAYLOAD"] == BOOTSTRAP_MAX_PAYLOAD, "P2.07 combined bootstrap payload bound changed")

    builder = symbols["zx48_env1_build"]
    validator = symbols["zx48_env1_validate"]
    require(FIXTURE_CODE <= builder < FIXTURE_CODE + len(fixture), "P2.07 ENV1 builder label outside fixture binary")
    require(FIXTURE_CODE <= validator < FIXTURE_CODE + len(fixture), "P2.07 ENV1 validator label outside fixture binary")

    minimal_arg = _arg1([b"x"])
    zero_env = _env1([])
    boundary_env = _env1([(b"ABCDEFGHIJKLMNO", b"v" * 63)])
    max_env = _max_env1()
    case_distinct = _env1([(b"A", b"x"), (b"a", b"y")])
    lexical_edges = _env1([(b"_A0", b" =x~")])
    odd_arg = _arg1([b"xx"])
    _success_case(root, symbols, fixture, minimal_arg, zero_env, b"x")
    _success_case(root, symbols, fixture, odd_arg, zero_env, b"xx")
    _success_case(root, symbols, fixture, minimal_arg, boundary_env, b"x")
    _success_case(root, symbols, fixture, minimal_arg, case_distinct, b"x")
    _success_case(root, symbols, fixture, minimal_arg, lexical_edges, b"x")
    _success_case(root, symbols, fixture, _max_arg1(), max_env, b"cmd")
    _deep_stack_case(root, symbols, fixture)

    bad_magic = bytearray(zero_env); bad_magic[0] = ord("X")
    bad_reserved = bytearray(zero_env); bad_reserved[5] = 1
    bad_total = bytearray(zero_env); struct.pack_into("<H", bad_total, 6, len(zero_env) + 1)
    trailing = bytearray(zero_env + b"x"); struct.pack_into("<H", trailing, 6, len(trailing))
    count_nine = _env1([(f"A{i}".encode("ascii"), b"") for i in range(9)], enforce_host_limits=False)
    name_too_long = _env1([(b"A" * 16, b"")], enforce_host_limits=False)
    bad_first = _env1([(b"1A", b"")], enforce_host_limits=False)
    bad_subsequent = _env1([(b"A-", b"")], enforce_host_limits=False)
    empty_name = _env1([(b"", b"x")], enforce_host_limits=False)
    value_too_long = _env1([(b"A", b"v" * 64)], enforce_host_limits=False)
    bad_value_low = _env1([(b"A", b"x\x1fy")], enforce_host_limits=False)
    bad_value_high = _env1([(b"A", b"x\x7fy")], enforce_host_limits=False)
    duplicate = _env1([(b"A", b"x"), (b"A", b"y")])
    duplicate_nonadjacent = _env1([(b"A", b"x=1"), (b"B", b"y"), (b"A", b"z=2")])
    missing_equals_payload = b"A\0"
    missing_equals = b"ENV1" + bytes((1, 0)) + struct.pack("<H", ENV1_HEADER_SIZE + len(missing_equals_payload)) + missing_equals_payload
    missing_nul_payload = b"A=x"
    missing_nul = b"ENV1" + bytes((1, 0)) + struct.pack("<H", ENV1_HEADER_SIZE + len(missing_nul_payload)) + missing_nul_payload

    for block in (
        bytes(bad_magic),
        bytes(bad_reserved),
        bytes(bad_total),
        bytes(trailing),
        count_nine,
        name_too_long,
        bad_first,
        bad_subsequent,
        empty_name,
        value_too_long,
        bad_value_low,
        bad_value_high,
        duplicate,
        duplicate_nonadjacent,
        missing_equals,
        missing_nul,
    ):
        _format_rejection_case(root, symbols, fixture, block)

    _format_rejection_case(root, symbols, fixture, zero_env, supplied_length=257)
    _format_rejection_case(root, symbols, fixture, b"", supplied_length=16, env_source=0xFFF8)
    _format_rejection_case(root, symbols, fixture, zero_env, arg_length=257)
    _format_rejection_case(root, symbols, fixture, zero_env, arg_length=16, arg_source=0xFFF8)
    _allocation_failure_case(root, symbols, fixture)

    return [
        {"name": "zero-entry-env1-max-name-value-and-lexical-printable-boundaries-accepted", "passed": True},
        {"name": "odd-combined-length-rounds-allocation-without-changing-exact-arg1-env1-abi", "passed": True, "payload": len(odd_arg) + len(zero_env), "rounded": (len(odd_arg) + len(zero_env) + 1) & ~1},
        {"name": "case-sensitive-distinct-names-accepted-and-adjacent-or-nonadjacent-exact-duplicates-rejected", "passed": True},
        {"name": "exact-256-byte-eight-entry-env1-boundary-accepted", "passed": True, "length": len(max_env), "entries": 8},
        {"name": "exact-512-byte-arg1-env1-shared-bootstrap-allocation-accepted", "passed": True, "payload": BOOTSTRAP_MAX_PAYLOAD},
        {"name": "magic-reserved-total-trailing-count-name-value-termination-negatives-rejected-pre-allocation", "passed": True},
        {"name": "supplied-length-env-or-arg-source-wrap-and-invalid-arg-length-rejected-pre-allocation", "passed": True},
        {"name": "allocation-failure-preserves-pre-attempt-live-allocation-count", "passed": True},
        {"name": "deep-fast-stack-activity-cannot-overwrite-shared-bootstrap-allocation", "passed": True},
    ]


def _source_contract(root: Path) -> list[dict[str, object]]:
    process = (root / "v1/src/kernel/process.asm").read_text(encoding="utf-8")
    kernel = (root / "v1/src/kernel/kernel.asm").read_text(encoding="utf-8")
    abi = (root / "v1/docs/abi.md").read_text(encoding="utf-8")
    start = process.index("    MACRO EMIT_ENV1_ROUTINES")
    routine = process[start:]
    end = routine.index("    ENDM\n")
    routine = routine[:end]
    resident_end = process.index("    ENDM\n", process.index("    MACRO EMIT_PROCESS_ROUTINES"))
    validator_start = routine.index("zx48_env1_validate:")
    builder_start = routine.index("zx48_env1_build:")
    format_label = routine.index("zx48_env1_format:")
    validator = routine[validator_start:builder_start]
    builder = routine[builder_start:format_label]
    first_builder_write = builder.index("ld (process_bootstrap")
    return [
        {"name": "env1-routines-remain-staged-outside-resident-process-macro", "passed": resident_end < start},
        {"name": "production-kernel-does-not-prematurely-emit-p207-helper", "passed": "EMIT_ENV1_ROUTINES" not in kernel},
        {"name": "env1-exact-frozen-header-and-bounds", "passed": all(token in process for token in ("ENV1_HEADER_SIZE              EQU 8", "ENV1_MAX_SIZE                 EQU 256", "ENV1_MAX_COUNT                EQU 8", "ENV1_MAX_NAME                 EQU 15", "ENV1_MAX_VALUE                EQU 63", "BOOTSTRAP_MAX_PAYLOAD         EQU 512"))},
        {"name": "env1-validator-checks-magic-count-reserved-and-total", "passed": all(token in validator for token in ("cp $45", "cp $4e", "cp $56", "cp $31", "ENV1_MAX_COUNT+1", "(ix+5)", "(ix+6)", "(ix+7)"))},
        {"name": "env1-validator-proves-source-plus-length-before-indexed-header-read", "passed": validator.index("add hl,bc") < validator.index("ld a,(ix+0)")},
        {"name": "env1-validator-enforces-name-value-and-uniqueness-paths", "passed": all(token in validator for token in ("zx48_env1_name_loop:", "zx48_env1_value_loop:", "zx48_env1_unique_outer:", "zx48_env1_unique_compare:"))},
        {"name": "env1-validator-is-side-effect-free", "passed": all(token not in validator for token in ("zx48_alloc", "zx48_free", "PROC_READY", "PROC_STATE", "PROC_CWD", "process_table", "ldir", "\n    ld (", "\n    call "))},
        {"name": "env1-builder-validates-before-scratch-or-allocation", "passed": builder.index("call zx48_env1_validate") < first_builder_write < builder.index("call zx48_alloc")},
        {"name": "env1-builder-uses-one-any-allocation-for-both-exact-blocks", "passed": builder.count("call zx48_alloc") == 1 and "ld a,ALLOC_ANY" in builder and builder.count("ldir") == 2 and "zx48_arg1_build" not in builder},
        {"name": "env1-builder-returns-p208-ready-arglen-and-env-pointer-registers", "passed": "ld bc,(process_bootstrap_arg_len)" in builder and "pop de\n\n    ld hl,(process_bootstrap_base)" in builder},
        {"name": "env1-builder-does-not-publish-ready-or-cwd", "passed": all(token not in builder for token in ("PROC_READY", "PROC_STATE", "PROC_CWD", "process_table"))},
        {"name": "env1-abi-documentation-freezes-shared-bootstrap-contract", "passed": all(token in abi for token in ("## Process bootstrap environment block (ENV1)", "magic bytes `ENV1`", "exactly 0..8", "`[A-Za-z_][A-Za-z0-9_]{0,14}`", "0..63 target-printable bytes `0x20..0x7E`", "one process-owned immutable bootstrap allocation", "at most 512 payload bytes plus alignment", "getenv retains the ENV1 pointer", "cwd remains kernel-descriptor state", "before any process becomes READY"))},
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
    if step != "P2.07":
        raise DriverError(f"Phase-2 ENV1 step is not registered: {step}")

    assertions = _source_contract(root)
    failed = [item["name"] for item in assertions if item["passed"] is not True]
    require(not failed, f"static P2.07 contract failures: {failed}")

    command, binary, symbol_path = _assemble_fixture(root, run_command, require_project_tool)
    symbol_names = (
        "zx48_memory_init",
        "zx48_alloc",
        "zx48_free",
        "zx48_arg1_validate",
        "zx48_mex1_alloc_stack",
        "zx48_env1_validate",
        "zx48_env1_build",
        "memory_live_allocations",
        "ALLOC_ANY",
        "E_FORMAT",
        "E_NOMEM",
        "ENV1_HEADER_SIZE",
        "ENV1_MAX_SIZE",
        "ENV1_MAX_COUNT",
        "ENV1_MAX_NAME",
        "ENV1_MAX_VALUE",
        "BOOTSTRAP_MAX_PAYLOAD",
    )
    symbols = _symbols(symbol_path, symbol_names)
    fixture = binary.read_bytes()
    if action == "test":
        assertions.extend(_target_tests(root, symbols, fixture))

    return [command], {
        "v1/build/p207-env1.bin": sha256_file(binary),
        "v1/docs/abi.md": sha256_file(root / "v1/docs/abi.md"),
        "v1/src/kernel/memory.asm": sha256_file(root / "v1/src/kernel/memory.asm"),
        "v1/src/kernel/process.asm": sha256_file(root / "v1/src/kernel/process.asm"),
        "v1/tools-host/test-driver/phase2_arg1.py": sha256_file(root / "v1/tools-host/test-driver/phase2_arg1.py"),
        "v1/tools-host/test-driver/phase2_env1.py": sha256_file(root / "v1/tools-host/test-driver/phase2_env1.py"),
    }, assertions
