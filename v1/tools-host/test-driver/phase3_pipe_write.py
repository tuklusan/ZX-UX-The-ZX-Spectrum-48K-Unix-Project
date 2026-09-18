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
from typing import Any, Callable

from driver_core import DriverError
from fuse_harness import FAIL_PC, PASS_PC, run_sna
import phase1
import phase3_open_descriptions
import phase3_pipe_create


SRC = 0xA180


class Phase3PipeWriteError(DriverError):
    """Raised when the P3.11 available-space pipe-write contract regresses."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Phase3PipeWriteError(message)


def _word(value: int) -> bytes:
    return bytes((value & 0xFF, (value >> 8) & 0xFF))


def _jp_nc(address: int) -> bytes:
    return b"\xD2" + _word(address)


def _assert_hl(code: bytearray, expected: int) -> None:
    code += phase1._ld_de(expected) + b"\xB7\xED\x52" + phase1._jp_nz(FAIL_PC)


def _setup_pipe(code: bytearray, s: dict[str, int]) -> int:
    phase3_pipe_create._setup(code, s)
    code += b"\x21" + _word(0xA100)
    code += phase1._call(s["zx48_pipe_create"]) + phase1._jp_c(FAIL_PC)
    _assert_hl(code, 0)
    return s["FAST_END"] + 1 - s["PIPE_BUFFER_SIZE"]


def _call_write(code: bytearray, s: dict[str, int], source: int, count: int) -> None:
    code += b"\x3E\x00"
    code += b"\x21" + _word(source)
    code += b"\x01" + _word(count)
    code += phase1._call(s["zx48_pipe_write"])


def _source_contract(root: Path) -> list[dict[str, object]]:
    pipe = (root / "v1/src/kernel/pipe.asm").read_text(encoding="utf-8")
    write = pipe[pipe.index("zx48_pipe_write:"):pipe.index("; A=ring position, BC=candidate.")]
    return [
        {"name":"write-rejects-no-reader","passed":"ld a,(ix+PIPE_READERS_O)\n    or a\n    jp z,zx48_pipe_broken" in write},
        {"name":"write-computes-capacity-minus-used","passed":"ld l,(ix+PIPE_CAPACITY_O)" in write and "ld e,(ix+PIPE_COUNT_O)" in write and "sbc hl,de" in write},
        {"name":"bytes-used-greater-than-capacity-is-fatal","passed":"sbc hl,de\n    jp c,zx48_pipe_corrupt" in write and "zx48_pipe_corrupt:" in pipe},
        {"name":"full-pipe-blocks-before-copy","passed":"call zx48_pipe_block_write" in write},
        {"name":"write-bounds-by-request","passed":"ld bc,(pipe_io_request)" in write and "sbc hl,bc" in write},
        {"name":"write-limits-contiguous-ring-tail","passed":"call zx48_pipe_chunk_limit" in write},
        {"name":"write-copies-selected-count","passed":"push bc\n    call zx48_memcpy\n    pop bc" in write},
        {"name":"write-advances-ring-index","passed":"ld (ix+PIPE_WPOS_O),a" in write},
        {"name":"write-increments-bytes-used","passed":"add hl,bc\n    ld (ix+PIPE_COUNT_O),l\n    ld (ix+PIPE_COUNT_O+1),h" in write},
        {"name":"write-wakes-readers","passed":"call zx48_pipe_wake_readers" in write},
    ]


def _partial_fixture(root: Path, s: dict[str, int], kernel: bytes) -> None:
    code = bytearray()
    buffer = _setup_pipe(code, s)
    pipe = s["pipe_table"]

    for offset, value in enumerate((0x31,0x32,0x33,0x34,0x35,0x36)):
        code += phase3_pipe_create._store_byte(SRC + offset, value)
    code += phase3_pipe_create._store_byte(pipe + s["PIPE_WPOS_O"], 5)
    code += phase3_pipe_create._store_byte(pipe + s["PIPE_COUNT_O"], 0xFE)
    code += phase3_pipe_create._store_byte(pipe + s["PIPE_COUNT_O"] + 1, 0x00)

    _call_write(code, s, SRC, 6)
    code += phase1._jp_c(FAIL_PC)
    _assert_hl(code, 2)
    phase3_pipe_create._assert_byte(code, buffer + 5, 0x31)
    phase3_pipe_create._assert_byte(code, buffer + 6, 0x32)
    phase3_pipe_create._assert_byte(code, buffer + 7, 0x00)
    phase3_pipe_create._assert_byte(code, pipe + s["PIPE_WPOS_O"], 7)
    phase3_pipe_create._assert_word(code, pipe + s["PIPE_COUNT_O"], 0x0100)

    code += phase1._jp(PASS_PC)
    run_sna(root, bytes(code), patch=phase1._kernel_patch(kernel))


def _wrap_fixture(root: Path, s: dict[str, int], kernel: bytes) -> None:
    code = bytearray()
    buffer = _setup_pipe(code, s)
    pipe = s["pipe_table"]

    for offset, value in enumerate((0x41,0x42,0x43,0x44)):
        code += phase3_pipe_create._store_byte(SRC + offset, value)
    code += phase3_pipe_create._store_byte(pipe + s["PIPE_WPOS_O"], 0xFE)
    code += phase3_pipe_create._store_byte(pipe + s["PIPE_COUNT_O"], 0)
    code += phase3_pipe_create._store_byte(pipe + s["PIPE_COUNT_O"] + 1, 0)

    _call_write(code, s, SRC, 4)
    code += phase1._jp_c(FAIL_PC)
    _assert_hl(code, 2)
    phase3_pipe_create._assert_byte(code, buffer + 0xFE, 0x41)
    phase3_pipe_create._assert_byte(code, buffer + 0xFF, 0x42)
    phase3_pipe_create._assert_byte(code, pipe + s["PIPE_WPOS_O"], 0)
    phase3_pipe_create._assert_word(code, pipe + s["PIPE_COUNT_O"], 2)

    _call_write(code, s, SRC + 2, 2)
    code += phase1._jp_c(FAIL_PC)
    _assert_hl(code, 2)
    phase3_pipe_create._assert_byte(code, buffer + 0, 0x43)
    phase3_pipe_create._assert_byte(code, buffer + 1, 0x44)
    phase3_pipe_create._assert_byte(code, pipe + s["PIPE_WPOS_O"], 2)
    phase3_pipe_create._assert_word(code, pipe + s["PIPE_COUNT_O"], 4)

    code += phase1._jp(PASS_PC)
    run_sna(root, bytes(code), patch=phase1._kernel_patch(kernel))


def _corrupt_count_fixture(root: Path, s: dict[str, int], kernel: bytes) -> None:
    code = bytearray()
    _setup_pipe(code, s)
    pipe = s["pipe_table"]
    code += phase3_pipe_create._store_byte(SRC, 0x7A)
    code += phase3_pipe_create._store_byte(pipe + s["PIPE_COUNT_O"], 1)
    code += phase3_pipe_create._store_byte(pipe + s["PIPE_COUNT_O"] + 1, 1)

    _call_write(code, s, SRC, 1)
    code += _jp_nc(FAIL_PC)
    code += bytes((0xFE, s["E_INVAL"])) + phase1._jp_nz(FAIL_PC)
    code += phase1._jp(PASS_PC)

    patched = bytearray(kernel)
    offset = s["zx48_panic"] - phase1.KERNEL_BASE
    payload = bytes((0x3E, s["E_INVAL"], 0x37, 0xC9))
    require(0 <= offset <= len(patched) - len(payload), "panic patch outside kernel")
    patched[offset:offset + len(payload)] = payload
    run_sna(root, bytes(code), patch=phase1._kernel_patch(bytes(patched)))


def dispatch(
    root: Path,
    action: str,
    step: str,
    *,
    sha256_file: Callable[[Path], str],
    run_command: Callable[..., Any],
    require_project_tool: Callable[[Path, str | Path], Path],
):
    if step != "P3.11":
        raise DriverError(f"Phase-3 pipe-write step is not registered: {step}")

    assertions = _source_contract(root)
    failed = [item["name"] for item in assertions if item["passed"] is not True]
    require(not failed, f"static P3.11 contract failures: {failed}")

    result, kernel, listing = phase1._assemble_kernel(root, run_command, require_project_tool)
    commands = [result]
    symbols = phase3_open_descriptions._symbols(
        listing.with_suffix(".sym"),
        (
            "zx48_memory_init","zx48_process_init","zx48_handles_init","zx48_pipe_init",
            "zx48_process_prepare_pid1","zx48_pipe_create","zx48_pipe_write","zx48_panic",
            "current_pid","pipe_table","PIPE_BUFFER_SIZE","PIPE_WPOS_O","PIPE_COUNT_O",
            "FAST_END","E_INVAL",
        ),
    )
    require(symbols["PIPE_BUFFER_SIZE"] == 256, "normal pipe buffer must remain 256")

    if action == "test":
        kernel_bytes = kernel.read_bytes()
        _partial_fixture(root, symbols, kernel_bytes)
        _wrap_fixture(root, symbols, kernel_bytes)
        _corrupt_count_fixture(root, symbols, kernel_bytes)
        assertions.extend([
            {"name":"partial-write-count-and-indices-exact","passed":True},
            {"name":"wraparound-write-vector-exact","passed":True},
            {"name":"bytes-used-capacity-invariant-traps","passed":True},
        ])

    hashes = {
        "v1/build/kernel.bin": sha256_file(kernel),
        "v1/src/kernel/pipe.asm": sha256_file(root / "v1/src/kernel/pipe.asm"),
        "v1/tools-host/test-driver/phase3_pipe_write.py": sha256_file(root / "v1/tools-host/test-driver/phase3_pipe_write.py"),
        "v1/tools-host/test-driver/run.py": sha256_file(root / "v1/tools-host/test-driver/run.py"),
        "v1/dist/certification/P3.10.test.json": sha256_file(root / "v1/dist/certification/P3.10.test.json"),
    }
    return commands, hashes, assertions
