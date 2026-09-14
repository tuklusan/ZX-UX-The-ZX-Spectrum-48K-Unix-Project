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
TOKEN_ADDRESS = 0xC300
RESULT_BASE = 0xC3F0
ARENA_START = 0x6000
ARENA_SIZE = 0x8000
ARG1_HEADER_SIZE = 8
ARG1_MAX_SIZE = 256
ARG1_MAX_COUNT = 16


class Phase2Arg1Error(DriverError):
    """Raised when the P2.06 ARG1 contract regresses."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Phase2Arg1Error(message)


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


def _expect_word(address: int, value: int) -> bytes:
    return (
        b"\x2A" + _word(address)
        + phase1._ld_de(value)
        + b"\xB7\xED\x52"
        + phase1._jp_nz(FAIL_PC)
    )


def _expect_hl(value: int) -> bytes:
    return phase1._ld_de(value) + b"\xB7\xED\x52" + phase1._jp_nz(FAIL_PC)


def _expect_bc(value: int) -> bytes:
    return b"\x60\x69" + _expect_hl(value)


def _expect_de(value: int) -> bytes:
    return b"\x62\x6B" + _expect_hl(value)


def _arg1(arguments: list[bytes], *, magic: bytes = b"ARG1", reserved: int = 0, total: int | None = None) -> bytes:
    require(1 <= len(arguments) <= ARG1_MAX_COUNT, "host ARG1 builder requires 1..16 arguments")
    payload = b"".join(argument + b"\0" for argument in arguments)
    length = ARG1_HEADER_SIZE + len(payload)
    encoded_total = length if total is None else total
    header = bytearray(ARG1_HEADER_SIZE)
    header[:4] = magic
    header[4] = len(arguments)
    header[5] = reserved & 0xFF
    struct.pack_into("<H", header, 6, encoded_total & 0xFFFF)
    return bytes(header) + payload


def _max_arg1() -> bytes:
    # 4 + 14*16 + 20 = 248 payload bytes; plus 8-byte header = 256 exactly.
    arguments = [b"cmd"] + [b"a" * 15 for _ in range(14)] + [b"b" * 19]
    block = _arg1(arguments)
    require(len(block) == ARG1_MAX_SIZE, "P2.06 host max-boundary fixture is not exactly 256 bytes")
    return block


def _patch(fixture: bytes, regions: tuple[tuple[int, bytes], ...]):
    def patch(ram: bytearray) -> None:
        start = FIXTURE_CODE - 0x4000
        ram[start:start + len(fixture)] = fixture
        for address, payload in regions:
            require(0x4000 <= address <= 0xFFFF, f"P2.06 patch address outside RAM: 0x{address:04X}")
            require(address + len(payload) <= 0x10000, f"P2.06 patch crosses address space: 0x{address:04X}")
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
    source = build / "p206-arg1.asm"
    binary = build / "p206-arg1.bin"
    listing = build / "p206-arg1.lst"
    symbols = build / "p206-arg1.sym"
    source.write_text(
        "    DEVICE ZXSPECTRUM48\n"
        "    INCLUDE \"../include/zx48ux.inc\"\n"
        "    INCLUDE \"../include/mex1.inc\"\n"
        "    INCLUDE \"../src/kernel/memory.asm\"\n"
        "    INCLUDE \"../src/kernel/process.asm\"\n"
        f"    ORG ${FIXTURE_CODE:04X}\n"
        "p206_arg1_start:\n"
        "    EMIT_MEMORY_ROUTINES\n"
        "    EMIT_ARG1_ROUTINES\n"
        "zx48_process_count:\n"
        "    xor a\n"
        "    ret\n"
        "p206_arg1_end:\n"
        "    SAVEBIN \"p206-arg1.bin\",p206_arg1_start,p206_arg1_end-p206_arg1_start\n",
        encoding="utf-8",
        newline="\n",
    )
    result = run_command(
        [assembler, "--nologo", "--lst=p206-arg1.lst", "--sym=p206-arg1.sym", "p206-arg1.asm"],
        cwd=build,
        timeout_seconds=30.0,
    )
    require(not result.timed_out and result.exit_code == 0, f"P2.06 ARG1 fixture assembly failed: {result.stderr or result.stdout}")
    require(binary.is_file() and 0 < binary.stat().st_size < 0x1800, "P2.06 ARG1 fixture binary missing or implausibly large")
    require(symbols.is_file() and listing.is_file(), "P2.06 ARG1 fixture symbols/listing missing")
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
        require(name in found, f"P2.06 fixture symbol missing: {name}")
    return found


def _call_arg1(builder: int, block_length: int, *, source: int = ARG_ADDRESS, token: int = TOKEN_ADDRESS) -> bytes:
    return _ld_ix(source) + _ld_bc(block_length) + phase1._ld_hl(token) + phase1._call(builder)


def _compare_blocks(source: int, destination: int, length: int, program_address: int) -> bytes:
    code = bytearray()
    code += phase1._ld_hl(source)
    code += phase1._ld_de(destination)
    code += _ld_bc(length)
    loop = program_address + len(code)
    code += b"\x1A\xBE" + phase1._jp_nz(FAIL_PC)  # LD A,(DE); CP (HL)
    code += b"\x23\x13\x0B\x78\xB1"              # INC HL; INC DE; DEC BC; LD A,B; OR C
    code += phase1._jp_nz(loop)
    return bytes(code)


def _success_case(root: Path, symbols: dict[str, int], fixture: bytes, block: bytes, token: bytes) -> None:
    memory_init = symbols["zx48_memory_init"]
    builder = symbols["zx48_arg1_build"]
    free = symbols["zx48_free"]
    live_count = symbols["memory_live_allocations"]
    rounded = (len(block) + 1) & ~1

    code = bytearray(b"\xF3" + phase1._ld_sp(TEST_STACK))
    code += phase1._call(memory_init)
    code += _call_arg1(builder, len(block)) + phase1._jp_c(FAIL_PC)
    code += b"\x22" + _word(RESULT_BASE)
    # Check DE before helper comparisons reuse it as scratch.
    code += _expect_de(rounded)
    code += _expect_bc(len(block))
    code += _expect_word(RESULT_BASE, ARENA_START)
    code += _expect_word(live_count, 1)
    # run_sna loads the test program at the frozen fuse_harness ENTRY_PC 0x9000.
    code += _compare_blocks(ARG_ADDRESS, ARENA_START, len(block), 0x9000 + len(code))
    code += b"\x2A" + _word(RESULT_BASE) + _ld_bc(rounded) + phase1._call(free) + phase1._jp_c(FAIL_PC)
    code += _expect_word(live_count, 0)
    code += phase1._jp(PASS_PC)
    run_sna(root, bytes(code), patch=_patch(fixture, ((ARG_ADDRESS, block), (TOKEN_ADDRESS, token + b"\0"))))


def _format_rejection_case(
    root: Path,
    symbols: dict[str, int],
    fixture: bytes,
    block: bytes,
    token: bytes,
    *,
    supplied_length: int | None = None,
    source: int = ARG_ADDRESS,
) -> None:
    memory_init = symbols["zx48_memory_init"]
    builder = symbols["zx48_arg1_build"]
    live_count = symbols["memory_live_allocations"]
    e_format = symbols["E_FORMAT"]
    length = len(block) if supplied_length is None else supplied_length

    code = bytearray(b"\xF3" + phase1._ld_sp(TEST_STACK))
    code += phase1._call(memory_init)
    code += _call_arg1(builder, length, source=source) + _jp_nc(FAIL_PC)
    code += bytes((0xFE, e_format & 0xFF)) + phase1._jp_nz(FAIL_PC)
    code += _expect_word(live_count, 0)
    code += phase1._jp(PASS_PC)
    regions: list[tuple[int, bytes]] = [(TOKEN_ADDRESS, token + b"\0")]
    if source == ARG_ADDRESS:
        regions.insert(0, (ARG_ADDRESS, block))
    run_sna(root, bytes(code), patch=_patch(fixture, tuple(regions)))


def _allocation_failure_case(root: Path, symbols: dict[str, int], fixture: bytes, block: bytes, token: bytes) -> None:
    memory_init = symbols["zx48_memory_init"]
    alloc = symbols["zx48_alloc"]
    free = symbols["zx48_free"]
    builder = symbols["zx48_arg1_build"]
    live_count = symbols["memory_live_allocations"]
    e_nomem = symbols["E_NOMEM"]

    code = bytearray(b"\xF3" + phase1._ld_sp(TEST_STACK))
    code += phase1._call(memory_init)
    code += _ld_a(symbols["ALLOC_ANY"]) + _ld_bc(ARENA_SIZE) + phase1._call(alloc) + phase1._jp_c(FAIL_PC)
    code += _expect_hl(ARENA_START)
    code += _expect_word(live_count, 1)
    code += _call_arg1(builder, len(block)) + _jp_nc(FAIL_PC)
    code += bytes((0xFE, e_nomem & 0xFF)) + phase1._jp_nz(FAIL_PC)
    code += _expect_word(live_count, 1)
    code += phase1._ld_hl(ARENA_START) + _ld_bc(ARENA_SIZE) + phase1._call(free) + phase1._jp_c(FAIL_PC)
    code += _expect_word(live_count, 0)
    code += phase1._jp(PASS_PC)
    run_sna(root, bytes(code), patch=_patch(fixture, ((ARG_ADDRESS, block), (TOKEN_ADDRESS, token + b"\0"))))


def _target_tests(root: Path, symbols: dict[str, int], fixture: bytes) -> list[dict[str, object]]:
    require(symbols["ALLOC_ANY"] == 0, "P2.06 ALLOC_ANY ABI value changed")
    require(symbols["E_NOMEM"] == 0x03, "P2.06 E_NOMEM ABI value changed")
    require(symbols["E_FORMAT"] == 0x0B, "P2.06 E_FORMAT ABI value changed")
    require(symbols["ARG1_HEADER_SIZE"] == ARG1_HEADER_SIZE, "P2.06 ARG1 header size changed")
    require(symbols["ARG1_MAX_SIZE"] == ARG1_MAX_SIZE, "P2.06 ARG1 maximum size changed")
    require(symbols["ARG1_MAX_COUNT"] == ARG1_MAX_COUNT, "P2.06 ARG1 maximum argc changed")

    builder = symbols["zx48_arg1_build"]
    validator = symbols["zx48_arg1_validate"]
    require(FIXTURE_CODE <= builder < FIXTURE_CODE + len(fixture), "P2.06 ARG1 builder label outside fixture binary")
    require(FIXTURE_CODE <= validator < FIXTURE_CODE + len(fixture), "P2.06 ARG1 validator label outside fixture binary")

    minimal = _arg1([b"x"])
    odd_length = _arg1([b"xx"])
    maximum = _max_arg1()
    _success_case(root, symbols, fixture, minimal, b"x")
    _success_case(root, symbols, fixture, odd_length, b"xx")
    _success_case(root, symbols, fixture, maximum, b"cmd")

    # Malformed inputs must all fail before allocation / live-allocation change.
    argc_zero = bytearray(minimal); argc_zero[4] = 0
    argc_seventeen = bytearray(minimal); argc_seventeen[4] = 17
    bad_reserved = bytearray(minimal); bad_reserved[5] = 1
    bad_magic = bytearray(minimal); bad_magic[0] = ord("X")
    bad_total = bytearray(minimal); struct.pack_into("<H", bad_total, 6, len(minimal) + 1)
    missing_nul = bytearray(b"ARG1" + bytes((1, 0)) + struct.pack("<H", 11) + b"abc")
    trailing = bytearray(b"ARG1" + bytes((1, 0)) + struct.pack("<H", 12) + b"x\0zz")

    for block, token in (
        (bytes(argc_zero), b"x"),
        (bytes(argc_seventeen), b"x"),
        (bytes(bad_reserved), b"x"),
        (bytes(bad_magic), b"x"),
        (bytes(bad_total), b"x"),
        (bytes(missing_nul), b"abc"),
        (bytes(trailing), b"x"),
        (minimal, b"y"),
        (minimal, b"X"),
    ):
        _format_rejection_case(root, symbols, fixture, block, token)

    # Supplied length >256 is rejected before reading beyond the block.
    _format_rejection_case(root, symbols, fixture, minimal, b"x", supplied_length=257)
    # Source+length wrap is rejected before any indexed header read.
    _format_rejection_case(root, symbols, fixture, b"", b"x", supplied_length=16, source=0xFFF8)
    _allocation_failure_case(root, symbols, fixture, minimal, b"x")

    return [
        {"name": "minimum-nonempty-argv0-block-accepted-and-private-copied", "passed": True, "length": len(minimal)},
        {"name": "odd-length-block-rounds-allocation-without-changing-exact-arg1-length", "passed": True, "length": len(odd_length), "rounded": (len(odd_length) + 1) & ~1},
        {"name": "exact-256-byte-16-argument-boundary-accepted", "passed": True, "length": len(maximum), "argc": 16},
        {"name": "argc-magic-reserved-total-termination-trailing-and-argv0-negatives-rejected-pre-side-effect", "passed": True},
        {"name": "supplied-length-and-source-wrap-negatives-rejected-pre-side-effect", "passed": True},
        {"name": "allocation-failure-preserves-pre-attempt-live-allocation-count", "passed": True},
    ]


def _source_contract(root: Path) -> list[dict[str, object]]:
    process = (root / "v1/src/kernel/process.asm").read_text(encoding="utf-8")
    kernel = (root / "v1/src/kernel/kernel.asm").read_text(encoding="utf-8")
    abi = (root / "v1/docs/abi.md").read_text(encoding="utf-8")
    start = process.index("    MACRO EMIT_ARG1_ROUTINES")
    routine = process[start:]
    end = routine.index("    ENDM\n")
    routine = routine[:end]
    resident_end = process.index("    ENDM\n", process.index("    MACRO EMIT_PROCESS_ROUTINES"))
    validator_start = routine.index("zx48_arg1_validate:")
    builder_start = routine.index("zx48_arg1_build:")
    format_label = routine.index("zx48_arg1_format:")
    validator = routine[validator_start:builder_start]
    builder = routine[builder_start:format_label]
    return [
        {"name": "arg1-routines-remain-staged-outside-resident-process-macro", "passed": resident_end < start},
        {"name": "production-kernel-does-not-prematurely-emit-p206-helper", "passed": "EMIT_ARG1_ROUTINES" not in kernel},
        {"name": "arg1-exact-frozen-header-and-bounds", "passed": all(token in process for token in ("ARG1_HEADER_SIZE              EQU 8", "ARG1_MAX_SIZE                 EQU 256", "ARG1_MAX_COUNT                EQU 16"))},
        {"name": "arg1-validator-checks-magic-count-reserved-and-total", "passed": all(token in validator for token in ("cp $41", "cp $52", "cp $47", "cp $31", "ARG1_MAX_COUNT+1", "(ix+5)", "(ix+6)", "(ix+7)"))},
        {"name": "arg1-validator-proves-source-plus-length-before-indexed-header-read", "passed": validator.index("add hl,bc") < validator.index("ld a,(ix+0)")},
        {"name": "arg1-validator-is-side-effect-free", "passed": all(token not in validator for token in ("zx48_alloc", "zx48_free", "PROC_READY", "process_table", "ldir", "ld (", "process_arg1_"))},
        {"name": "arg1-builder-validates-before-any-allocation", "passed": builder.index("call zx48_arg1_validate") < builder.index("call zx48_alloc")},
        {"name": "arg1-builder-uses-any-and-copies-exact-bytes", "passed": "ld a,ALLOC_ANY" in builder and "call zx48_alloc" in builder and "ldir" in builder},
        {"name": "arg1-builder-has-no-persistent-scratch-or-process-publication", "passed": all(token not in routine for token in ("process_arg1_", "PROC_READY", "PROC_STATE", "process_table"))},
        {"name": "arg1-abi-documentation-freezes-format-and-pre-ready-validation", "passed": all(token in abi for token in ("## Process bootstrap argument block (ARG1)", "magic bytes `ARG1`", "exactly 1..16", "exact total block length", "no trailing bytes", "exact non-empty command token", "before any process becomes READY"))},
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
    if step != "P2.06":
        raise DriverError(f"Phase-2 ARG1 step is not registered: {step}")

    assertions = _source_contract(root)
    failed = [item["name"] for item in assertions if item["passed"] is not True]
    require(not failed, f"static P2.06 contract failures: {failed}")

    command, binary, symbol_path = _assemble_fixture(root, run_command, require_project_tool)
    symbol_names = (
        "zx48_memory_init",
        "zx48_alloc",
        "zx48_free",
        "zx48_arg1_validate",
        "zx48_arg1_build",
        "memory_live_allocations",
        "ALLOC_ANY",
        "E_FORMAT",
        "E_NOMEM",
        "ARG1_HEADER_SIZE",
        "ARG1_MAX_SIZE",
        "ARG1_MAX_COUNT",
    )
    symbols = _symbols(symbol_path, symbol_names)
    fixture = binary.read_bytes()
    if action == "test":
        assertions.extend(_target_tests(root, symbols, fixture))

    return [command], {
        "v1/build/p206-arg1.bin": sha256_file(binary),
        "v1/docs/abi.md": sha256_file(root / "v1/docs/abi.md"),
        "v1/src/kernel/memory.asm": sha256_file(root / "v1/src/kernel/memory.asm"),
        "v1/src/kernel/process.asm": sha256_file(root / "v1/src/kernel/process.asm"),
        "v1/tools-host/test-driver/phase2_arg1.py": sha256_file(root / "v1/tools-host/test-driver/phase2_arg1.py"),
    }, assertions
