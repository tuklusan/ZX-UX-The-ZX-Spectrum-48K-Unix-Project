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
HEADER_DEFAULT = 0xC000
HEADER_MIN = 0xC040
HEADER_MAX = 0xC080
HEADER_ODD = 0xC0C0
HEADER_LOW = 0xC100
HEADER_HIGH = 0xC140
FAST_START = 0x8000
FAST_END_EXCLUSIVE = 0xE000
FAST_SIZE = 0x6000
COLD_START = 0x6000
DEFAULT_STACK = 512
MIN_STACK = 64
MAX_STACK = 4096
BOOTSTRAP_BYTES = 64


class Phase2StackError(DriverError):
    """Raised when the P2.05 FAST process-stack contract regresses."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Phase2StackError(message)


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


def _header(stack_size: int) -> bytes:
    header = bytearray(24)
    header[:4] = b"MEX1"
    header[4] = 1
    struct.pack_into("<H", header, 6, 24)
    struct.pack_into("<H", header, 8, 1)
    struct.pack_into("<H", header, 12, 0)
    struct.pack_into("<H", header, 14, stack_size)
    struct.pack_into("<H", header, 18, 25)
    return bytes(header)


def _patch(fixture: bytes, headers: tuple[tuple[int, bytes], ...]):
    def patch(ram: bytearray) -> None:
        start = FIXTURE_CODE - 0x4000
        ram[start:start + len(fixture)] = fixture
        for address, payload in headers:
            require(0x4000 <= address <= 0xFFFF, f"P2.05 fixture address outside RAM: 0x{address:04X}")
            require(address + len(payload) <= 0x10000, f"P2.05 fixture crosses address space: 0x{address:04X}")
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
    source = build / "p205-stack.asm"
    binary = build / "p205-stack.bin"
    listing = build / "p205-stack.lst"
    symbols = build / "p205-stack.sym"
    source.write_text(
        "    DEVICE ZXSPECTRUM48\n"
        "    INCLUDE \"../include/zx48ux.inc\"\n"
        "    INCLUDE \"../include/mex1.inc\"\n"
        "    INCLUDE \"../src/kernel/memory.asm\"\n"
        "    INCLUDE \"../src/kernel/process.asm\"\n"
        f"    ORG ${FIXTURE_CODE:04X}\n"
        "p205_stack_start:\n"
        "    EMIT_MEMORY_ROUTINES\n"
        "    EMIT_MEX1_STACK_ROUTINES\n"
        "zx48_process_count:\n"
        "    xor a\n"
        "    ret\n"
        "p205_stack_end:\n"
        "    SAVEBIN \"p205-stack.bin\",p205_stack_start,p205_stack_end-p205_stack_start\n",
        encoding="utf-8",
        newline="\n",
    )
    result = run_command(
        [assembler, "--nologo", "--lst=p205-stack.lst", "--sym=p205-stack.sym", "p205-stack.asm"],
        cwd=build,
        timeout_seconds=30.0,
    )
    require(not result.timed_out and result.exit_code == 0, f"P2.05 stack fixture assembly failed: {result.stderr or result.stdout}")
    require(binary.is_file() and 0 < binary.stat().st_size < 0x1800, "P2.05 stack fixture binary missing or implausibly large")
    require(symbols.is_file() and listing.is_file(), "P2.05 stack fixture symbols/listing missing")
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
        require(name in found, f"P2.05 fixture symbol missing: {name}")
    return found


def _call_stack(stack_alloc: int, header: int) -> bytes:
    return _ld_ix(header) + phase1._call(stack_alloc)


def _success_case(
    root: Path,
    symbols: dict[str, int],
    fixture: bytes,
    header_address: int,
    advertised_size: int,
) -> None:
    memory_init = symbols["zx48_memory_init"]
    stack_alloc = symbols["zx48_mex1_alloc_stack"]
    free = symbols["zx48_free"]
    live_count = symbols["memory_live_allocations"]
    total = advertised_size + BOOTSTRAP_BYTES
    expected_base = FAST_END_EXCLUSIVE - total

    code = bytearray(b"\xF3" + phase1._ld_sp(TEST_STACK))
    code += phase1._call(memory_init)
    code += _call_stack(stack_alloc, header_address) + phase1._jp_c(FAIL_PC)
    code += _expect_hl(expected_base)
    code += _expect_bc(total)
    code += _expect_word(live_count, 1)
    code += phase1._ld_hl(expected_base) + _ld_bc(total) + phase1._call(free) + phase1._jp_c(FAIL_PC)
    code += _expect_word(live_count, 0)
    code += phase1._jp(PASS_PC)
    run_sna(root, bytes(code), patch=_patch(fixture, ((header_address, _header(advertised_size)),)))


def _format_rejection_case(
    root: Path,
    symbols: dict[str, int],
    fixture: bytes,
    header_address: int,
    advertised_size: int,
) -> None:
    memory_init = symbols["zx48_memory_init"]
    stack_alloc = symbols["zx48_mex1_alloc_stack"]
    live_count = symbols["memory_live_allocations"]
    e_format = symbols["E_FORMAT"]

    code = bytearray(b"\xF3" + phase1._ld_sp(TEST_STACK))
    code += phase1._call(memory_init)
    code += _call_stack(stack_alloc, header_address) + _jp_nc(FAIL_PC)
    code += bytes((0xFE, e_format & 0xFF)) + phase1._jp_nz(FAIL_PC)
    code += _expect_word(live_count, 0)
    code += phase1._jp(PASS_PC)
    run_sna(root, bytes(code), patch=_patch(fixture, ((header_address, _header(advertised_size)),)))


def _fast_exhaustion_case(root: Path, symbols: dict[str, int], fixture: bytes) -> None:
    memory_init = symbols["zx48_memory_init"]
    alloc = symbols["zx48_alloc"]
    free = symbols["zx48_free"]
    stack_alloc = symbols["zx48_mex1_alloc_stack"]
    live_count = symbols["memory_live_allocations"]
    e_nomem = symbols["E_NOMEM"]

    code = bytearray(b"\xF3" + phase1._ld_sp(TEST_STACK))
    code += phase1._call(memory_init)
    code += _ld_a(symbols["ALLOC_FAST_REQUIRED"]) + _ld_bc(FAST_SIZE) + phase1._call(alloc) + phase1._jp_c(FAIL_PC)
    code += _expect_hl(FAST_START)
    code += _expect_word(live_count, 1)
    code += _call_stack(stack_alloc, HEADER_MIN) + _jp_nc(FAIL_PC)
    code += bytes((0xFE, e_nomem & 0xFF)) + phase1._jp_nz(FAIL_PC)
    code += _expect_word(live_count, 1)

    # COLD remains allocatable: the failed process stack did not spill there.
    code += _ld_a(symbols["ALLOC_ANY"]) + _ld_bc(0x0100) + phase1._call(alloc) + phase1._jp_c(FAIL_PC)
    code += _expect_hl(COLD_START)
    code += _expect_word(live_count, 2)
    code += phase1._ld_hl(COLD_START) + _ld_bc(0x0100) + phase1._call(free) + phase1._jp_c(FAIL_PC)
    code += phase1._ld_hl(FAST_START) + _ld_bc(FAST_SIZE) + phase1._call(free) + phase1._jp_c(FAIL_PC)
    code += _expect_word(live_count, 0)
    code += phase1._jp(PASS_PC)
    run_sna(root, bytes(code), patch=_patch(fixture, ((HEADER_MIN, _header(MIN_STACK)),)))


def _target_tests(root: Path, symbols: dict[str, int], fixture: bytes) -> list[dict[str, object]]:
    require(symbols["ALLOC_FAST_REQUIRED"] == 1, "P2.05 ALLOC_FAST_REQUIRED ABI value changed")
    require(symbols["ALLOC_ANY"] == 0, "P2.05 ALLOC_ANY ABI value changed")
    require(symbols["E_NOMEM"] == 0x03, "P2.05 E_NOMEM ABI value changed")
    require(symbols["E_FORMAT"] == 0x0B, "P2.05 E_FORMAT ABI value changed")
    require(symbols["MEX_DEFAULT_STACK"] == DEFAULT_STACK, "P2.05 default MEX1 stack changed")
    require(symbols["MEX_MIN_STACK"] == MIN_STACK, "P2.05 minimum MEX1 stack changed")
    require(symbols["MEX_MAX_STACK"] == MAX_STACK, "P2.05 maximum MEX1 stack changed")
    require(symbols["PROCESS_STACK_BOOTSTRAP_BYTES"] == BOOTSTRAP_BYTES, "P2.05 bootstrap reserve changed")

    stack_alloc = symbols["zx48_mex1_alloc_stack"]
    require(FIXTURE_CODE <= stack_alloc < FIXTURE_CODE + len(fixture), "P2.05 stack allocator label outside fixture binary")

    _success_case(root, symbols, fixture, HEADER_DEFAULT, DEFAULT_STACK)
    _success_case(root, symbols, fixture, HEADER_MIN, MIN_STACK)
    _success_case(root, symbols, fixture, HEADER_MAX, MAX_STACK)
    _format_rejection_case(root, symbols, fixture, HEADER_ODD, 65)
    _format_rejection_case(root, symbols, fixture, HEADER_LOW, 62)
    _format_rejection_case(root, symbols, fixture, HEADER_HIGH, 4098)
    _fast_exhaustion_case(root, symbols, fixture)

    return [
        {"name": "default-stack-is-512-plus-64-bootstrap", "passed": True, "advertised": DEFAULT_STACK, "allocated": DEFAULT_STACK + BOOTSTRAP_BYTES},
        {"name": "minimum-stack-bound-is-exact", "passed": True, "advertised": MIN_STACK, "allocated": MIN_STACK + BOOTSTRAP_BYTES},
        {"name": "maximum-stack-bound-is-exact", "passed": True, "advertised": MAX_STACK, "allocated": MAX_STACK + BOOTSTRAP_BYTES},
        {"name": "odd-and-out-of-range-stack-values-rejected-before-allocation", "passed": True},
        {"name": "fast-exhaustion-returns-enomem-with-cold-still-allocatable", "passed": True},
    ]


def _source_contract(root: Path) -> list[dict[str, object]]:
    process = (root / "v1/src/kernel/process.asm").read_text(encoding="utf-8")
    kernel = (root / "v1/src/kernel/kernel.asm").read_text(encoding="utf-8")
    start = process.index("    MACRO EMIT_MEX1_STACK_ROUTINES")
    routine = process[start:]
    end = routine.index("    ENDM\n")
    routine = routine[:end]
    resident_end = process.index("    ENDM\n", process.index("    MACRO EMIT_PROCESS_ROUTINES"))
    validation = routine.index("bit 0,c")
    reserve = routine.index("PROCESS_STACK_BOOTSTRAP_BYTES")
    allocation = routine.index("call zx48_alloc")
    return [
        {"name": "stack-allocator-remains-staged-outside-resident-process-macro", "passed": resident_end < start},
        {"name": "production-kernel-does-not-prematurely-emit-p205-stack-helper", "passed": "EMIT_MEX1_STACK_ROUTINES" not in kernel},
        {"name": "stack-size-comes-from-validated-mex1-header", "passed": "MEX_HDR_STACK" in routine},
        {"name": "stack-advertised-range-uses-frozen-mex1-bounds", "passed": all(token in routine for token in ("MEX_MIN_STACK", "MEX_MAX_STACK"))},
        {"name": "stack-requires-even-advertised-size", "passed": "bit 0,c" in routine},
        {"name": "bootstrap-reserve-is-separate-fixed-64-bytes", "passed": "PROCESS_STACK_BOOTSTRAP_BYTES EQU 64" in process and validation < reserve < allocation},
        {"name": "stack-uses-real-fast-required-allocator", "passed": "ld a,ALLOC_FAST_REQUIRED" in routine and "call zx48_alloc" in routine},
        {"name": "stack-helper-has-no-any-or-cold-fallback", "passed": "ALLOC_ANY" not in routine and "ALLOC_COLD_PREFERRED" not in routine},
        {"name": "stack-helper-does-not-publish-process-state", "passed": all(token not in routine for token in ("PROC_STATE", "PROC_READY", "process_table"))},
        {"name": "stack-helper-returns-exact-total-allocation-size", "passed": "process_mex_stack_allocation_size" in routine and "ld bc,(process_mex_stack_allocation_size)" in routine},
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
    if step != "P2.05":
        raise DriverError(f"Phase-2 process-stack step is not registered: {step}")

    assertions = _source_contract(root)
    failed = [item["name"] for item in assertions if item["passed"] is not True]
    require(not failed, f"static P2.05 contract failures: {failed}")

    command, binary, symbol_path = _assemble_fixture(root, run_command, require_project_tool)
    symbol_names = (
        "zx48_memory_init",
        "zx48_alloc",
        "zx48_free",
        "zx48_mex1_alloc_stack",
        "memory_live_allocations",
        "ALLOC_ANY",
        "ALLOC_FAST_REQUIRED",
        "E_FORMAT",
        "E_NOMEM",
        "MEX_DEFAULT_STACK",
        "MEX_MIN_STACK",
        "MEX_MAX_STACK",
        "PROCESS_STACK_BOOTSTRAP_BYTES",
    )
    symbols = _symbols(symbol_path, symbol_names)
    fixture = binary.read_bytes()
    if action == "test":
        assertions.extend(_target_tests(root, symbols, fixture))

    return [command], {
        "v1/build/p205-stack.bin": sha256_file(binary),
        "v1/include/mex1.inc": sha256_file(root / "v1/include/mex1.inc"),
        "v1/src/kernel/memory.asm": sha256_file(root / "v1/src/kernel/memory.asm"),
        "v1/src/kernel/process.asm": sha256_file(root / "v1/src/kernel/process.asm"),
        "v1/tools-host/test-driver/phase2_stack.py": sha256_file(root / "v1/tools-host/test-driver/phase2_stack.py"),
    }, assertions
