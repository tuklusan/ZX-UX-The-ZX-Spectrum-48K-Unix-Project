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

SOURCE_GOOD = 0xC000
SOURCE_BAD = 0xC100
LOADER_CODE = 0xE000
TEST_STACK = 0xBFC0
FIRST_BASE = 0x6000
SECOND_BASE = 0x7000
FIRST_BLOCKER = 0x1000
IMAGE = b"\x21\x05\x00\x7E\xC9\x5A"
BSS_SIZE = 5
ALLOC_SIZE = len(IMAGE) + BSS_SIZE
ROUNDED_ALLOC_SIZE = (ALLOC_SIZE + 1) & ~1


class Phase2LoaderError(DriverError):
    """Raised when the P2.04 private image-load contract regresses."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Phase2LoaderError(message)


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


def _expect_byte(address: int, value: int) -> bytes:
    return b"\x3A" + _word(address) + bytes((0xFE, value & 0xFF)) + phase1._jp_nz(FAIL_PC)


def _expect_hl(value: int) -> bytes:
    return phase1._ld_de(value) + b"\xB7\xED\x52" + phase1._jp_nz(FAIL_PC)


def _expect_bc(value: int) -> bytes:
    return b"\x60\x69" + _expect_hl(value)


def _mex(image: bytes, *, bss_size: int, relocations: tuple[int, ...]) -> bytes:
    header = bytearray(24)
    header[:4] = b"MEX1"
    header[4] = 1
    struct.pack_into("<H", header, 6, 24)
    struct.pack_into("<H", header, 8, len(image))
    struct.pack_into("<H", header, 10, bss_size)
    struct.pack_into("<H", header, 12, 0)
    struct.pack_into("<H", header, 14, 64)
    struct.pack_into("<H", header, 16, len(relocations))
    struct.pack_into("<H", header, 18, 24 + len(image))
    table = b"".join(struct.pack("<H", item) for item in relocations)
    return bytes(header) + image + table


def _patch(loader: bytes, extras: tuple[tuple[int, bytes], ...], fills: tuple[tuple[int, int, int], ...] = ()):
    def patch(ram: bytearray) -> None:
        start = LOADER_CODE - 0x4000
        ram[start:start + len(loader)] = loader
        for address, length, value in fills:
            require(0x4000 <= address <= 0xFFFF, f"fill outside RAM: 0x{address:04X}")
            require(address + length <= 0x10000, f"fill crosses address space: 0x{address:04X}")
            offset = address - 0x4000
            ram[offset:offset + length] = bytes((value & 0xFF,)) * length
        for address, payload in extras:
            require(0x4000 <= address <= 0xFFFF, f"fixture address outside RAM: 0x{address:04X}")
            require(address + len(payload) <= 0x10000, f"fixture crosses address space: 0x{address:04X}")
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
    source = build / "p204-loader.asm"
    binary = build / "p204-loader.bin"
    listing = build / "p204-loader.lst"
    symbols = build / "p204-loader.sym"
    source.write_text(
        "    DEVICE ZXSPECTRUM48\n"
        "    INCLUDE \"../include/zx48ux.inc\"\n"
        "    INCLUDE \"../include/mex1.inc\"\n"
        "    INCLUDE \"../src/kernel/memory.asm\"\n"
        "    INCLUDE \"../src/kernel/process.asm\"\n"
        f"    ORG ${LOADER_CODE:04X}\n"
        "p204_loader_start:\n"
        "    EMIT_MEMORY_ROUTINES\n"
        "    EMIT_MEX1_RELOCATION_ROUTINES\n"
        "    EMIT_MEX1_IMAGE_LOAD_ROUTINES\n"
        "zx48_process_count:\n"
        "    xor a\n"
        "    ret\n"
        "p204_loader_end:\n"
        "    SAVEBIN \"p204-loader.bin\",p204_loader_start,p204_loader_end-p204_loader_start\n",
        encoding="utf-8",
        newline="\n",
    )
    result = run_command(
        [assembler, "--nologo", "--lst=p204-loader.lst", "--sym=p204-loader.sym", "p204-loader.asm"],
        cwd=build,
        timeout_seconds=30.0,
    )
    require(not result.timed_out and result.exit_code == 0, f"P2.04 loader fixture assembly failed: {result.stderr or result.stdout}")
    require(binary.is_file() and 0 < binary.stat().st_size < 0x2000, "P2.04 loader fixture binary missing or implausibly large")
    require(symbols.is_file() and listing.is_file(), "P2.04 loader fixture symbols/listing missing")
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
        require(name in found, f"P2.04 fixture symbol missing: {name}")
    return found


def _call_loader(loader: int, source: int) -> bytes:
    return _ld_ix(source) + phase1._call(loader)


def _expect_live_count(live_count: int, expected: int) -> bytes:
    return _expect_word(live_count, expected)


def _expect_loaded_image(base: int) -> bytes:
    code = bytearray()
    code += _expect_word(base + 1, base + 5)
    code += _expect_byte(base + 5, 0x5A)
    for offset in range(len(IMAGE), ALLOC_SIZE):
        code += _expect_byte(base + offset, 0)
    code += phase1._call(base)
    code += bytes((0xFE, 0x5A)) + phase1._jp_nz(FAIL_PC)
    return bytes(code)


def _golden_two_base_fixture(root: Path, symbols: dict[str, int], loader_bytes: bytes, source: bytes) -> None:
    memory_init = symbols["zx48_memory_init"]
    alloc = symbols["zx48_alloc"]
    free = symbols["zx48_free"]
    loader = symbols["zx48_mex1_load_image"]
    live_count = symbols["memory_live_allocations"]

    code = bytearray(b"\xF3" + phase1._ld_sp(TEST_STACK))
    code += phase1._call(memory_init)
    code += _call_loader(loader, SOURCE_GOOD) + phase1._jp_c(FAIL_PC)
    code += _expect_hl(FIRST_BASE)
    code += _expect_bc(ROUNDED_ALLOC_SIZE)
    code += _expect_live_count(live_count, 1)
    code += _expect_loaded_image(FIRST_BASE)
    code += phase1._ld_hl(FIRST_BASE) + _ld_bc(ROUNDED_ALLOC_SIZE) + phase1._call(free) + phase1._jp_c(FAIL_PC)
    code += _expect_live_count(live_count, 0)

    code += phase1._call(memory_init)
    code += _ld_a(symbols["ALLOC_ANY"]) + _ld_bc(FIRST_BLOCKER) + phase1._call(alloc) + phase1._jp_c(FAIL_PC)
    code += _expect_hl(FIRST_BASE)
    code += _call_loader(loader, SOURCE_GOOD) + phase1._jp_c(FAIL_PC)
    code += _expect_hl(SECOND_BASE)
    code += _expect_bc(ROUNDED_ALLOC_SIZE)
    code += _expect_live_count(live_count, 2)
    code += _expect_loaded_image(SECOND_BASE)
    code += phase1._ld_hl(SECOND_BASE) + _ld_bc(ROUNDED_ALLOC_SIZE) + phase1._call(free) + phase1._jp_c(FAIL_PC)
    code += phase1._ld_hl(FIRST_BASE) + _ld_bc(FIRST_BLOCKER) + phase1._call(free) + phase1._jp_c(FAIL_PC)
    code += _expect_live_count(live_count, 0)
    code += phase1._jp(PASS_PC)

    run_sna(
        root,
        bytes(code),
        patch=_patch(
            loader_bytes,
            ((SOURCE_GOOD, source),),
            fills=((FIRST_BASE, 0x20, 0xA5), (SECOND_BASE, 0x20, 0xA5)),
        ),
    )


def _relocation_rollback_fixture(root: Path, symbols: dict[str, int], loader_bytes: bytes, malformed: bytes) -> None:
    memory_init = symbols["zx48_memory_init"]
    loader = symbols["zx48_mex1_load_image"]
    live_count = symbols["memory_live_allocations"]
    free_extents = symbols["memory_free_extents"]
    e_format = symbols["E_FORMAT"]

    code = bytearray(b"\xF3" + phase1._ld_sp(TEST_STACK))
    code += phase1._call(memory_init)
    code += _call_loader(loader, SOURCE_BAD) + _jp_nc(FAIL_PC)
    code += bytes((0xFE, e_format & 0xFF)) + phase1._jp_nz(FAIL_PC)
    code += _expect_live_count(live_count, 0)
    code += _expect_word(free_extents, FIRST_BASE)
    code += _expect_word(free_extents + 2, 0x8000)
    code += phase1._jp(PASS_PC)
    run_sna(
        root,
        bytes(code),
        patch=_patch(loader_bytes, ((SOURCE_BAD, malformed),), fills=((FIRST_BASE, 0x20, 0xA5),)),
    )


def _allocation_failure_fixture(root: Path, symbols: dict[str, int], loader_bytes: bytes, source: bytes) -> None:
    memory_init = symbols["zx48_memory_init"]
    alloc = symbols["zx48_alloc"]
    free = symbols["zx48_free"]
    loader = symbols["zx48_mex1_load_image"]
    live_count = symbols["memory_live_allocations"]
    e_nomem = symbols["E_NOMEM"]

    code = bytearray(b"\xF3" + phase1._ld_sp(TEST_STACK))
    code += phase1._call(memory_init)
    code += _ld_a(symbols["ALLOC_ANY"]) + _ld_bc(0x8000) + phase1._call(alloc) + phase1._jp_c(FAIL_PC)
    code += _expect_hl(FIRST_BASE)
    code += _expect_live_count(live_count, 1)
    code += _call_loader(loader, SOURCE_GOOD) + _jp_nc(FAIL_PC)
    code += bytes((0xFE, e_nomem & 0xFF)) + phase1._jp_nz(FAIL_PC)
    code += _expect_live_count(live_count, 1)
    code += phase1._ld_hl(FIRST_BASE) + _ld_bc(0x8000) + phase1._call(free) + phase1._jp_c(FAIL_PC)
    code += _expect_live_count(live_count, 0)
    code += phase1._jp(PASS_PC)
    run_sna(root, bytes(code), patch=_patch(loader_bytes, ((SOURCE_GOOD, source),)))


def _target_tests(root: Path, symbols: dict[str, int], loader_bytes: bytes) -> list[dict[str, object]]:
    require(symbols["ALLOC_ANY"] == 0, "P2.04 ALLOC_ANY ABI value changed")
    require(symbols["E_FORMAT"] == 0x0B, "P2.04 E_FORMAT ABI value changed")
    require(symbols["E_NOMEM"] == 0x03, "P2.04 E_NOMEM ABI value changed")
    loader = symbols["zx48_mex1_load_image"]
    require(LOADER_CODE <= loader < LOADER_CODE + len(loader_bytes), "P2.04 loader label outside fixture binary")

    good = _mex(IMAGE, bss_size=BSS_SIZE, relocations=(1,))
    malformed = _mex(IMAGE, bss_size=BSS_SIZE, relocations=(1, 2))
    _golden_two_base_fixture(root, symbols, loader_bytes, good)
    _relocation_rollback_fixture(root, symbols, loader_bytes, malformed)
    _allocation_failure_fixture(root, symbols, loader_bytes, good)
    return [
        {"name": "same-executable-runs-at-two-any-bases", "passed": True, "bases": [FIRST_BASE, SECOND_BASE]},
        {"name": "image-copied-relocated-and-bss-zeroed", "passed": True, "logical_size": ALLOC_SIZE},
        {"name": "relocation-failure-rolls-back-rounded-private-allocation", "passed": True, "rounded_size": ROUNDED_ALLOC_SIZE},
        {"name": "allocation-failure-adds-no-loader-owned-live-allocation", "passed": True},
    ]


def _source_contract(root: Path) -> list[dict[str, object]]:
    process = (root / "v1/src/kernel/process.asm").read_text(encoding="utf-8")
    kernel = (root / "v1/src/kernel/kernel.asm").read_text(encoding="utf-8")
    memory = (root / "v1/src/kernel/memory.asm").read_text(encoding="utf-8")
    start = process.index("    MACRO EMIT_MEX1_IMAGE_LOAD_ROUTINES")
    routine = process[start:]
    end = routine.index("    ENDM\n")
    routine = routine[:end]
    alloc = routine.index("call zx48_alloc")
    copy = routine.index("ldir")
    zero = routine.index("zx48_mex1_load_zero_bss:")
    relocate = routine.index("call zx48_mex1_relocate")
    rollback = routine.index("zx48_mex1_load_rollback:")
    free = routine.index("call zx48_free", rollback)
    resident_end = process.index("    ENDM\n", process.index("    MACRO EMIT_PROCESS_ROUTINES"))
    return [
        {"name": "loader-remains-staged-outside-resident-process-macro", "passed": resident_end < start},
        {"name": "production-kernel-does-not-prematurely-emit-p204-loader", "passed": "EMIT_MEX1_IMAGE_LOAD_ROUTINES" not in kernel and "EMIT_MEX1_RELOCATION_ROUTINES" not in kernel},
        {"name": "loader-uses-real-any-allocator", "passed": "ld a,ALLOC_ANY" in routine and "call zx48_alloc" in routine},
        {"name": "loader-copy-zero-relocate-order", "passed": alloc < copy < zero < relocate},
        {"name": "loader-uses-block-copy", "passed": "ldir" in routine},
        {"name": "loader-reuses-certified-relocator", "passed": "call zx48_mex1_relocate" in routine},
        {"name": "loader-rolls-back-private-allocation", "passed": rollback < free and "process_mex_load_rounded" in routine},
        {"name": "loader-does-not-publish-process-state", "passed": all(token not in routine for token in ("PROC_STATE", "PROC_READY", "process_table"))},
        {"name": "allocator-accounting-is-real", "passed": "memory_live_allocations" in memory and "inc de\n    ld (memory_live_allocations),de" in memory and "dec hl\n    ld (memory_live_allocations),hl" in memory},
        {"name": "loader-guards-widened-image-plus-bss-before-allocation", "passed": "add hl,de\n    jp c,zx48_mex1_load_format" in routine and "cp $80" in routine},
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
    if step != "P2.04":
        raise DriverError(f"Phase-2 image-load step is not registered: {step}")

    assertions = _source_contract(root)
    failed = [item["name"] for item in assertions if item["passed"] is not True]
    require(not failed, f"static P2.04 contract failures: {failed}")

    command, binary, symbol_path = _assemble_fixture(root, run_command, require_project_tool)
    symbol_names = (
        "zx48_memory_init",
        "zx48_alloc",
        "zx48_free",
        "zx48_mex1_load_image",
        "memory_live_allocations",
        "memory_free_extents",
        "ALLOC_ANY",
        "E_FORMAT",
        "E_NOMEM",
    )
    symbols = _symbols(symbol_path, symbol_names)
    loader_bytes = binary.read_bytes()
    if action == "test":
        assertions.extend(_target_tests(root, symbols, loader_bytes))

    return [command], {
        "v1/build/p204-loader.bin": sha256_file(binary),
        "v1/include/mex1.inc": sha256_file(root / "v1/include/mex1.inc"),
        "v1/src/kernel/memory.asm": sha256_file(root / "v1/src/kernel/memory.asm"),
        "v1/src/kernel/process.asm": sha256_file(root / "v1/src/kernel/process.asm"),
        "v1/tools-host/test-driver/phase2_loader.py": sha256_file(root / "v1/tools-host/test-driver/phase2_loader.py"),
    }, assertions
