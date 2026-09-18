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


DEST = 0xA120


class Phase3PipeReadError(DriverError):
    """Raised when the P3.09 available-data pipe-read contract regresses."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Phase3PipeReadError(message)


def _word(value: int) -> bytes:
    return bytes((value & 0xFF, (value >> 8) & 0xFF))


def _call_read(code: bytearray, s: dict[str, int], destination: int, request: int) -> None:
    code += b"\x3E\x00"
    code += b"\x21" + _word(destination)
    code += b"\x01" + _word(request)
    code += phase1._call(s["zx48_pipe_read"])


def _assert_hl(code: bytearray, expected: int) -> None:
    code += phase1._ld_de(expected) + b"\xB7\xED\x52" + phase1._jp_nz(FAIL_PC)


def _source_contract(root: Path) -> list[dict[str, object]]:
    pipe = (root / "v1/src/kernel/pipe.asm").read_text(encoding="utf-8")
    read = pipe[pipe.index("zx48_pipe_read:"):pipe.index("; A=pipe slot, HL=source")]
    return [
        {"name": "read-bounds-by-available-count", "passed": "ld c,(ix+PIPE_COUNT_O)" in read and "sbc hl,bc" in read and "ld bc,(pipe_io_request)" in read},
        {"name": "read-bounds-by-request", "passed": "ld hl,(pipe_io_request)" in read and "jr nc,zx48_pipe_read_candidate" in read},
        {"name": "read-limits-contiguous-ring-tail", "passed": "call zx48_pipe_chunk_limit" in read},
        {"name": "read-copies-only-selected-count", "passed": "push bc\n    call zx48_memcpy\n    pop bc" in read},
        {"name": "read-advances-ring-index", "passed": "ld a,(ix+PIPE_RPOS_O)" in read and "ld (ix+PIPE_RPOS_O),a" in read},
        {"name": "read-decrements-available-count", "passed": "sbc hl,bc\n    ld (ix+PIPE_COUNT_O),l\n    ld (ix+PIPE_COUNT_O+1),h" in read},
        {"name": "read-wakes-writers-after-copy", "passed": "call zx48_pipe_wake_writers" in read},
        {"name": "empty-with-writers-blocks-before-copy", "passed": "call zx48_pipe_block_read" in read},
        {"name": "empty-without-writers-is-eof", "passed": "ld a,(ix+PIPE_WRITERS_O)\n    or a\n    ret z" in read},
    ]


def _setup_pipe(code: bytearray, s: dict[str, int]) -> int:
    phase3_pipe_create._setup(code, s)
    code += b"\x21" + _word(0xA100)
    code += phase1._call(s["zx48_pipe_create"])
    code += phase1._jp_c(FAIL_PC)
    _assert_hl(code, 0)
    return s["FAST_END"] + 1 - s["PIPE_BUFFER_SIZE"]


def _wraparound_fixture(root: Path, s: dict[str, int], kernel: bytes) -> None:
    code = bytearray()
    buffer = _setup_pipe(code, s)
    pipe = s["pipe_table"]

    code += phase3_pipe_create._store_byte(pipe + s["PIPE_RPOS_O"], 0xFE)
    code += phase3_pipe_create._store_byte(pipe + s["PIPE_COUNT_O"], 4)
    code += phase3_pipe_create._store_byte(pipe + s["PIPE_COUNT_O"] + 1, 0)
    for address, value in ((buffer + 0xFE, 0x11), (buffer + 0xFF, 0x22), (buffer, 0x33), (buffer + 1, 0x44)):
        code += phase3_pipe_create._store_byte(address, value)
    for offset in range(4):
        code += phase3_pipe_create._store_byte(DEST + offset, 0xA5)

    _call_read(code, s, DEST, 4)
    code += phase1._jp_c(FAIL_PC)
    _assert_hl(code, 2)
    phase3_pipe_create._assert_byte(code, DEST, 0x11)
    phase3_pipe_create._assert_byte(code, DEST + 1, 0x22)
    phase3_pipe_create._assert_byte(code, DEST + 2, 0xA5)
    phase3_pipe_create._assert_byte(code, pipe + s["PIPE_RPOS_O"], 0)
    phase3_pipe_create._assert_word(code, pipe + s["PIPE_COUNT_O"], 2)

    _call_read(code, s, DEST + 2, 2)
    code += phase1._jp_c(FAIL_PC)
    _assert_hl(code, 2)
    phase3_pipe_create._assert_byte(code, DEST + 2, 0x33)
    phase3_pipe_create._assert_byte(code, DEST + 3, 0x44)
    phase3_pipe_create._assert_byte(code, pipe + s["PIPE_RPOS_O"], 2)
    phase3_pipe_create._assert_word(code, pipe + s["PIPE_COUNT_O"], 0)

    code += phase1._jp(PASS_PC)
    run_sna(root, bytes(code), patch=phase1._kernel_patch(kernel))


def _overcopy_fixture(root: Path, s: dict[str, int], kernel: bytes) -> None:
    code = bytearray()
    buffer = _setup_pipe(code, s)
    pipe = s["pipe_table"]

    code += phase3_pipe_create._store_byte(pipe + s["PIPE_RPOS_O"], 7)
    code += phase3_pipe_create._store_byte(pipe + s["PIPE_COUNT_O"], 5)
    code += phase3_pipe_create._store_byte(pipe + s["PIPE_COUNT_O"] + 1, 0)
    for offset, value in enumerate((0x51, 0x52, 0x53, 0x54, 0x55, 0xEE)):
        code += phase3_pipe_create._store_byte(buffer + 7 + offset, value)
    for offset in range(6):
        code += phase3_pipe_create._store_byte(DEST + offset, 0xA5)

    _call_read(code, s, DEST, 2)
    code += phase1._jp_c(FAIL_PC)
    _assert_hl(code, 2)
    phase3_pipe_create._assert_byte(code, DEST, 0x51)
    phase3_pipe_create._assert_byte(code, DEST + 1, 0x52)
    phase3_pipe_create._assert_byte(code, DEST + 2, 0xA5)
    phase3_pipe_create._assert_byte(code, pipe + s["PIPE_RPOS_O"], 9)
    phase3_pipe_create._assert_word(code, pipe + s["PIPE_COUNT_O"], 3)

    _call_read(code, s, DEST + 2, 5)
    code += phase1._jp_c(FAIL_PC)
    _assert_hl(code, 3)
    phase3_pipe_create._assert_byte(code, DEST + 2, 0x53)
    phase3_pipe_create._assert_byte(code, DEST + 3, 0x54)
    phase3_pipe_create._assert_byte(code, DEST + 4, 0x55)
    phase3_pipe_create._assert_byte(code, DEST + 5, 0xA5)
    phase3_pipe_create._assert_byte(code, pipe + s["PIPE_RPOS_O"], 12)
    phase3_pipe_create._assert_word(code, pipe + s["PIPE_COUNT_O"], 0)

    code += phase1._jp(PASS_PC)
    run_sna(root, bytes(code), patch=phase1._kernel_patch(kernel))


def dispatch(
    root: Path,
    action: str,
    step: str,
    *,
    sha256_file: Callable[[Path], str],
    run_command: Callable[..., Any],
    require_project_tool: Callable[[Path, str | Path], Path],
):
    if step != "P3.09":
        raise DriverError(f"Phase-3 pipe-read step is not registered: {step}")

    assertions = _source_contract(root)
    failed = [item["name"] for item in assertions if item["passed"] is not True]
    require(not failed, f"static P3.09 contract failures: {failed}")

    result, kernel, listing = phase1._assemble_kernel(root, run_command, require_project_tool)
    commands = [result]
    symbols = phase3_open_descriptions._symbols(
        listing.with_suffix(".sym"),
        (
            "zx48_memory_init", "zx48_process_init", "zx48_handles_init",
            "zx48_pipe_init", "zx48_process_prepare_pid1", "zx48_pipe_create",
            "zx48_pipe_read", "current_pid", "pipe_table",
            "PIPE_BUFFER_SIZE", "PIPE_RPOS_O", "PIPE_COUNT_O",
            "FAST_END",
        ),
    )
    require(symbols["PIPE_BUFFER_SIZE"] == 256, "normal pipe buffer must remain 256")

    if action == "test":
        kernel_bytes = kernel.read_bytes()
        _wraparound_fixture(root, symbols, kernel_bytes)
        _overcopy_fixture(root, symbols, kernel_bytes)
        assertions.extend([
            {"name": "wraparound-two-chunk-vector-exact", "passed": True},
            {"name": "request-limit-prevents-overcopy", "passed": True},
            {"name": "available-count-limit-prevents-overcopy", "passed": True},
            {"name": "read-index-and-count-updates-exact", "passed": True},
        ])

    hashes = {
        "v1/build/kernel.bin": sha256_file(kernel),
        "v1/src/kernel/pipe.asm": sha256_file(root / "v1/src/kernel/pipe.asm"),
        "v1/tools-host/test-driver/phase3_pipe_read.py": sha256_file(root / "v1/tools-host/test-driver/phase3_pipe_read.py"),
        "v1/tools-host/test-driver/run.py": sha256_file(root / "v1/tools-host/test-driver/run.py"),
        "v1/dist/certification/P3.08.test.json": sha256_file(root / "v1/dist/certification/P3.08.test.json"),
    }
    return commands, hashes, assertions
