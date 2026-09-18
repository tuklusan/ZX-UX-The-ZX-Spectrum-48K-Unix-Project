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
DST = 0xA190


class Phase3PipeFullError(DriverError):
    """Raised when the P3.12 full-pipe blocking contract regresses."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Phase3PipeFullError(message)


def _word(value: int) -> bytes:
    return bytes((value & 0xFF, (value >> 8) & 0xFF))


def _assert_hl(code: bytearray, expected: int) -> None:
    code += phase1._ld_de(expected) + b"\xB7\xED\x52" + phase1._jp_nz(FAIL_PC)


def _setup_pipe(code: bytearray, s: dict[str, int]) -> int:
    phase3_pipe_create._setup(code, s)
    code += b"\x21" + _word(0xA100)
    code += phase1._call(s["zx48_pipe_create"]) + phase1._jp_c(FAIL_PC)
    _assert_hl(code, 0)
    return s["FAST_END"] + 1 - s["PIPE_BUFFER_SIZE"]


def _source_contract(root: Path) -> list[dict[str, object]]:
    pipe = (root / "v1/src/kernel/pipe.asm").read_text(encoding="utf-8")
    scheduler = (root / "v1/src/kernel/scheduler.asm").read_text(encoding="utf-8")
    write = pipe[pipe.index("zx48_pipe_write:"):pipe.index("; A=ring position, BC=candidate.")]
    block = pipe[pipe.index("zx48_pipe_block_write:"):pipe.index("; C=slot. Wake only waiters")]
    read = pipe[pipe.index("zx48_pipe_read:"):pipe.index("; A=pipe slot, HL=source")]
    wake = pipe[pipe.index("zx48_pipe_wake_writers:"):pipe.index("; A=kind,C=pipe slot")]
    return [
        {"name":"full-write-blocks-when-readers-remain","passed":"call zx48_pipe_block_write" in write and "jr zx48_pipe_write_retry" in write},
        {"name":"write-block-records-wait-object","passed":"ld (ix+PROC_WAIT_OBJECT),c" in block},
        {"name":"write-block-records-wait-state","passed":"zx48_pipe_block_write:\n    ld a,PROC_WAIT_PIPE_WRITE" in block and "ld (ix+PROC_STATE),d" in block},
        {"name":"write-block-yields-to-scheduler","passed":"jp zx48_schedule" in block},
        {"name":"reader-wakes-writers","passed":"call zx48_pipe_wake_writers" in read},
        {"name":"wake-selects-write-waiters","passed":"zx48_pipe_wake_writers:\n    ld a,PROC_WAIT_PIPE_WRITE" in wake},
        {"name":"wake-clears-object-and-readies","passed":"ld (ix+PROC_WAIT_OBJECT),a" in wake and "ld (ix+PROC_STATE),PROC_READY" in wake},
        {"name":"scheduler-has-ready-selection","passed":"PROC_READY" in scheduler and "zx48_schedule" in scheduler},
    ]


def _full_block_wake_fixture(root: Path, s: dict[str, int], kernel: bytes) -> None:
    code = bytearray()
    buffer = _setup_pipe(code, s)
    pipe = s["pipe_table"]
    proc = s["process_table"] + s["PROC_DESC_SIZE"]

    code += phase3_pipe_create._store_byte(buffer, 0x51)
    code += phase3_pipe_create._store_byte(SRC, 0x7A)
    code += phase3_pipe_create._store_byte(pipe + s["PIPE_COUNT_O"], 0x00)
    code += phase3_pipe_create._store_byte(pipe + s["PIPE_COUNT_O"] + 1, 0x01)

    code += b"\x3E\x00"
    code += b"\x21" + _word(SRC)
    code += b"\x01\x01\x00"
    code += phase1._call(s["zx48_pipe_write"])
    phase3_pipe_create._assert_byte(code, proc + s["PROC_STATE"], s["PROC_WAIT_PIPE_WRITE"])
    phase3_pipe_create._assert_byte(code, proc + s["PROC_WAIT_OBJECT"], 1)
    phase3_pipe_create._assert_word(code, pipe + s["PIPE_COUNT_O"], 0x0100)
    phase3_pipe_create._assert_byte(code, buffer, 0x51)

    code += b"\x3E\x00"
    code += b"\x21" + _word(DST)
    code += b"\x01\x01\x00"
    code += phase1._call(s["zx48_pipe_read"]) + phase1._jp_c(FAIL_PC)
    _assert_hl(code, 1)
    phase3_pipe_create._assert_byte(code, DST, 0x51)
    phase3_pipe_create._assert_word(code, pipe + s["PIPE_COUNT_O"], 0x00FF)
    phase3_pipe_create._assert_byte(code, proc + s["PROC_STATE"], s["PROC_READY"])
    phase3_pipe_create._assert_byte(code, proc + s["PROC_WAIT_OBJECT"], 0)
    code += phase1._jp(PASS_PC)

    patched = bytearray(kernel)
    offset = s["zx48_schedule"] - phase1.KERNEL_BASE
    payload = b"\x37\xC9"
    require(0 <= offset <= len(patched) - len(payload), "schedule patch outside kernel")
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
    if step != "P3.12":
        raise DriverError(f"Phase-3 full-pipe step is not registered: {step}")

    assertions = _source_contract(root)
    failed = [item["name"] for item in assertions if item["passed"] is not True]
    require(not failed, f"static P3.12 contract failures: {failed}")

    result, kernel, listing = phase1._assemble_kernel(root, run_command, require_project_tool)
    commands = [result]
    symbols = phase3_open_descriptions._symbols(
        listing.with_suffix(".sym"),
        (
            "zx48_memory_init","zx48_process_init","zx48_handles_init","zx48_pipe_init",
            "zx48_process_prepare_pid1","zx48_pipe_create","zx48_pipe_write","zx48_pipe_read",
            "zx48_schedule","current_pid","process_table","pipe_table","PROC_DESC_SIZE",
            "PROC_STATE","PROC_WAIT_OBJECT","PROC_WAIT_PIPE_WRITE","PROC_READY",
            "PIPE_BUFFER_SIZE","PIPE_COUNT_O","FAST_END",
        ),
    )
    require(symbols["PIPE_BUFFER_SIZE"] == 256, "normal pipe buffer must remain 256")

    if action == "test":
        _full_block_wake_fixture(root, symbols, kernel.read_bytes())
        assertions.extend([
            {"name":"writer-sleeps-on-full-pipe","passed":True},
            {"name":"full-write-has-no-hidden-copy","passed":True},
            {"name":"reader-wakes-blocked-writer","passed":True},
            {"name":"busy-loop-negative-detected-by-schedule-return","passed":True},
        ])

    hashes = {
        "v1/build/kernel.bin": sha256_file(kernel),
        "v1/src/kernel/pipe.asm": sha256_file(root / "v1/src/kernel/pipe.asm"),
        "v1/src/kernel/scheduler.asm": sha256_file(root / "v1/src/kernel/scheduler.asm"),
        "v1/tools-host/test-driver/phase3_pipe_full.py": sha256_file(root / "v1/tools-host/test-driver/phase3_pipe_full.py"),
        "v1/tools-host/test-driver/run.py": sha256_file(root / "v1/tools-host/test-driver/run.py"),
        "v1/dist/certification/P3.11.test.json": sha256_file(root / "v1/dist/certification/P3.11.test.json"),
    }
    return commands, hashes, assertions
