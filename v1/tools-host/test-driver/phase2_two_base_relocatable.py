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
import phase2_spawn_atomic
import phase2_spawn_exit_leak

FIXTURE_SOURCE = Path("v1/tests/multiprocessing/p223-two-base-relocatable.asm")
FIXTURE_CODE = 0xE000
PROGRAM_ADDRESS = 0x9000
TEST_STACK = 0x8F00
PROC_ADDRESS = 0xA300
GOOD_PATH_ADDRESS = 0xA000
ARG_ADDRESS = 0xA100
ENV_ADDRESS = 0xA200
GOOD_RECORD = 0xB000
GOOD_MEX = 0xC000
OUTPUT_ADDRESS = 0x8E80
BASE1 = 0x6000
BASE2 = 0x7000
PROC_DESC_SIZE = 48
PROC_STATE = 2
PROC_IMAGE_BASE = 4
PROC_READY = 1
FREE_EXTENT_BYTES = 64
ENTRY_OFFSET = 4


class Phase223Error(DriverError):
    """Raised when the P2.23 two-base execution gate regresses."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Phase223Error(message)


def _word(value: int) -> bytes:
    return bytes((value & 0xFF, (value >> 8) & 0xFF))


def _jp_c(address: int) -> bytes:
    return b"\xDA" + _word(address)


def _jp_nz(address: int) -> bytes:
    return b"\xC2" + _word(address)


def _jp_z(address: int) -> bytes:
    return b"\xCA" + _word(address)


def _expect_byte(address: int, value: int) -> bytes:
    return b"\x3A" + _word(address) + bytes((0xFE, value & 0xFF)) + _jp_nz(FAIL_PC)


def _expect_word(address: int, value: int) -> bytes:
    return _expect_byte(address, value) + _expect_byte(address + 1, value >> 8)


def _mex(*, fixed_absolute: bool = False) -> bytes:
    operand = BASE1 if fixed_absolute else 0
    image = bytes(
        (
            0x0B, 0x00,       # relocated word -> image+11
            0x0C, 0x00,       # relocated word -> image+12
            0x2A,             # LD HL,(nn)
            operand & 0xFF,
            (operand >> 8) & 0xFF,
            0x22,             # LD (OUTPUT_ADDRESS),HL
            OUTPUT_ADDRESS & 0xFF,
            (OUTPUT_ADDRESS >> 8) & 0xFF,
            0xC9,             # RET
            0xA5, 0x5A,
        )
    )
    relocations = (0, 2) if fixed_absolute else (0, 2, 5)
    header = bytearray(24)
    header[:4] = b"MEX1"
    header[4] = 1
    struct.pack_into("<H", header, 6, 24)
    struct.pack_into("<H", header, 8, len(image))
    struct.pack_into("<H", header, 10, 0)
    struct.pack_into("<H", header, 12, ENTRY_OFFSET)
    struct.pack_into("<H", header, 14, 64)
    struct.pack_into("<H", header, 16, len(relocations))
    struct.pack_into("<H", header, 18, 24 + len(image))
    body = image + b"".join(struct.pack("<H", item) for item in relocations)
    struct.pack_into("<H", header, 20, phase2_spawn_atomic._crc16(body))
    struct.pack_into("<H", header, 22, 0)
    struct.pack_into("<H", header, 22, phase2_spawn_atomic._crc16(bytes(header)))
    return bytes(header) + body


def _symbols(path: Path, names: tuple[str, ...]) -> dict[str, int]:
    text = path.read_text(encoding="utf-8", errors="replace")
    found: dict[str, int] = {}
    for name in names:
        match = re.search(
            rf"^{re.escape(name)}:\s+equ\s+0x([0-9A-Fa-f]+)\s*$",
            text,
            re.IGNORECASE | re.MULTILINE,
        )
        require(match is not None, f"P2.23 symbol missing from assembler output: {name}")
        found[name] = int(match.group(1), 16)
    return found


def _assemble_fixture(
    root: Path,
    run_command: Callable[..., Any],
    require_project_tool: Callable[[Path, str | Path], Path],
):
    assembler = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    source = root / FIXTURE_SOURCE
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    binary = build / "p223-two-base-relocatable.bin"
    symbols = build / "p223-two-base-relocatable.sym"
    result = run_command(
        [assembler, "--nologo", "--sym=../../build/p223-two-base-relocatable.sym", source.name],
        cwd=source.parent,
        timeout_seconds=30.0,
    )
    require(not result.timed_out and result.exit_code == 0, f"P2.23 fixture assembly failed: {result.stderr or result.stdout}")
    require(binary.is_file() and 0 < binary.stat().st_size <= 0x1D00, "P2.23 fixture missing or overlaps FAST reserve")
    require(symbols.is_file(), "P2.23 fixture symbols missing")
    return result, binary, symbols


def _free_extents(base: int) -> bytes:
    require(BASE1 <= base <= BASE2, "P2.23 allocator base outside test range")
    data = bytearray(FREE_EXTENT_BYTES)
    struct.pack_into("<HH", data, 0, base, 0xE000 - base)
    return bytes(data)


def _proc1() -> bytes:
    arg = phase2_spawn_atomic._arg1(b"/bin/good")
    return phase2_spawn_atomic._proc1(
        path_ptr=GOOD_PATH_ADDRESS,
        arg_ptr=ARG_ADDRESS,
        arg_len=len(arg),
        env_ptr=ENV_ADDRESS,
        env_len=len(phase2_spawn_atomic.ENV1_EMPTY),
    )


def _regions(symbols: dict[str, int], base: int, mex: bytes) -> tuple[tuple[int, bytes], ...]:
    arg = phase2_spawn_atomic._arg1(b"/bin/good")
    return (
        (GOOD_PATH_ADDRESS, b"/bin/good\0"),
        (ARG_ADDRESS, arg),
        (ENV_ADDRESS, phase2_spawn_atomic.ENV1_EMPTY),
        (PROC_ADDRESS, _proc1()),
        (GOOD_MEX, mex),
        (GOOD_RECORD, phase2_spawn_atomic._record(b"good", 2, GOOD_MEX, len(mex))),
        (symbols["process_table"], phase2_spawn_exit_leak._process_table()),
        (symbols["current_pid"], b"\x01"),
        (symbols["open_description_table"], phase2_spawn_exit_leak._open_descriptions()),
        (symbols["memory_free_extents"], _free_extents(base)),
        (symbols["memory_live_allocations"], b"\x00\x00"),
        (OUTPUT_ADDRESS, b"\x00\x00"),
    )


def _patch(fixture: bytes, regions: tuple[tuple[int, bytes], ...]):
    def patch(ram: bytearray) -> None:
        start = FIXTURE_CODE - 0x4000
        ram[start:start + len(fixture)] = fixture
        for address, payload in regions:
            require(0x4000 <= address < 0x10000, f"P2.23 patch address outside RAM: 0x{address:04X}")
            require(address + len(payload) <= 0x10000, f"P2.23 patch crosses RAM: 0x{address:04X}")
            offset = address - 0x4000
            ram[offset:offset + len(payload)] = payload
    return patch


def _spawn_and_execute(root: Path, symbols: dict[str, int], fixture: bytes, *, base: int, mex: bytes) -> None:
    child = symbols["process_table"] + 2 * PROC_DESC_SIZE
    code = bytearray(b"\xF3" + phase1._ld_sp(TEST_STACK))
    code += phase1._call(symbols["zx48_process_links_init"]) + _jp_c(FAIL_PC)
    code += phase1._ld_hl(PROC_ADDRESS) + phase1._call(symbols["p223_gateway"]) + _jp_c(FAIL_PC)
    code += b"\x7C\xB7" + _jp_nz(FAIL_PC)
    code += b"\x7D\xFE\x02" + _jp_nz(FAIL_PC)
    code += _expect_byte(child + PROC_STATE, PROC_READY)
    code += _expect_word(child + PROC_IMAGE_BASE, base)
    code += _expect_word(base + 0, base + 11)
    code += _expect_word(base + 2, base + 12)
    code += _expect_word(base + 5, base)
    code += phase1._call(base + ENTRY_OFFSET)
    code += _expect_word(OUTPUT_ADDRESS, base + 11)
    code += phase1._jp(PASS_PC)
    run_sna(root, bytes(code), patch=_patch(fixture, _regions(symbols, base, mex)), timeout=20.0)


def _negative_fixed_absolute(root: Path, symbols: dict[str, int], fixture: bytes) -> None:
    mex = _mex(fixed_absolute=True)
    base = BASE2
    child = symbols["process_table"] + 2 * PROC_DESC_SIZE
    code = bytearray(b"\xF3" + phase1._ld_sp(TEST_STACK))
    code += phase1._call(symbols["zx48_process_links_init"]) + _jp_c(FAIL_PC)
    code += phase1._ld_hl(PROC_ADDRESS) + phase1._call(symbols["p223_gateway"]) + _jp_c(FAIL_PC)
    code += _expect_word(child + PROC_IMAGE_BASE, base)
    code += _expect_word(base + 0, base + 11)
    code += _expect_word(base + 2, base + 12)
    code += _expect_word(base + 5, BASE1)
    code += phase1._call(base + ENTRY_OFFSET)
    code += _expect_word(OUTPUT_ADDRESS, 0x1234)
    code += phase1._jp(PASS_PC)
    run_sna(
        root,
        bytes(code),
        patch=_patch(fixture, _regions(symbols, base, mex) + ((BASE1, b"\x34\x12"),)),
        timeout=20.0,
    )


def _source_contract(root: Path) -> list[dict[str, object]]:
    process = (root / "v1/src/kernel/process.asm").read_text(encoding="utf-8")
    memory = (root / "v1/src/kernel/memory.asm").read_text(encoding="utf-8")
    fixture = (root / FIXTURE_SOURCE).read_text(encoding="utf-8")
    spawn_start = process.index("    MACRO EMIT_SPAWN_TRANSACTION_ROUTINES")
    spawn_end = process.index("    ENDM\n", spawn_start)
    spawn = process[spawn_start:spawn_end]
    return [
        {
            "name": "fixture-composes-production-spawn-relocator-and-parent-link-path",
            "passed": all(token in fixture for token in (
                "EMIT_MEX1_RELOCATION_ROUTINES",
                "EMIT_PARENT_CHILD_ROUTINES",
                "EMIT_SPAWN_TRANSACTION_ROUTINES",
                "jp zx48_sys_spawn",
            )),
        },
        {
            "name": "spawn-allocates-image-through-allocator-and-applies-certified-relocator",
            "passed": "ld a,ALLOC_ANY" in spawn and "call zx48_alloc" in spawn and "call zx48_mex1_relocate" in spawn,
        },
        {
            "name": "allocator-any-policy-selects-lowest-fitting-base",
            "passed": "zx48_alloc_take_low:" in memory and "cp ALLOC_FAST_REQUIRED" in memory,
        },
        {
            "name": "two-distinct-allocator-bases-are-inside-version1-arena",
            "passed": BASE1 == 0x6000 and BASE2 == 0x7000 and BASE1 != BASE2,
            "bases": [BASE1, BASE2],
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
    if step != "P2.23":
        raise Phase223Error(f"P2.23 driver received unexpected step: {step}")

    assertions = _source_contract(root)
    failed = [item["name"] for item in assertions if item.get("passed") is not True]
    require(not failed, f"static P2.23 contract failures: {failed}")

    kernel_command, kernel, listing = phase1._assemble_kernel(root, run_command, require_project_tool)
    fixture_command, fixture_binary, fixture_symbols = _assemble_fixture(root, run_command, require_project_tool)
    kernel_values = phase1._labels(listing, ("kernel_ordinary_used_end", "KERNEL_CODE_END"))
    free_bytes = kernel_values["KERNEL_CODE_END"] + 1 - kernel_values["kernel_ordinary_used_end"]
    require(free_bytes >= 0, "P2.23 resident ordinary kernel exceeds hard ceiling")
    assertions.append({"name": "resident-kernel-ordinary-code-remains-within-faff-ceiling", "passed": True, "free_bytes": free_bytes})

    symbols = _symbols(
        fixture_symbols,
        (
            "p223_gateway",
            "zx48_process_links_init",
            "process_table",
            "current_pid",
            "open_description_table",
            "memory_free_extents",
            "memory_live_allocations",
        ),
    )

    if action == "test":
        fixture = fixture_binary.read_bytes()
        mex = _mex()
        _spawn_and_execute(root, symbols, fixture, base=BASE1, mex=mex)
        _spawn_and_execute(root, symbols, fixture, base=BASE2, mex=mex)
        _negative_fixed_absolute(root, symbols, fixture)
        assertions.extend(
            (
                {"name": "same-mex1-executes-through-real-spawn-at-two-distinct-bases", "passed": True, "bases": [BASE1, BASE2]},
                {"name": "relocated-words-and-observable-result-are-exact-at-both-bases", "passed": True},
                {"name": "fixed-absolute-arena-reference-negative-fixture-is-detected-at-second-base", "passed": True},
            )
        )

    hashes = {
        "v1/build/kernel.bin": sha256_file(kernel),
        "v1/build/p223-two-base-relocatable.bin": sha256_file(fixture_binary),
        "v1/src/kernel/process.asm": sha256_file(root / "v1/src/kernel/process.asm"),
        "v1/src/kernel/memory.asm": sha256_file(root / "v1/src/kernel/memory.asm"),
        str(FIXTURE_SOURCE): sha256_file(root / FIXTURE_SOURCE),
        "v1/tools-host/test-driver/phase2_two_base_relocatable.py": sha256_file(root / "v1/tools-host/test-driver/phase2_two_base_relocatable.py"),
        "v1/tools-host/test-driver/run.py": sha256_file(root / "v1/tools-host/test-driver/run.py"),
    }
    return [kernel_command, fixture_command], hashes, assertions
