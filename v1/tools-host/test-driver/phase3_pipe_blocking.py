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


SCRATCH = 0xA140


class Phase3PipeBlockingError(DriverError):
    """Raised when the P3.10 blocking/EOF contract regresses."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Phase3PipeBlockingError(message)


def _word(value: int) -> bytes:
    return bytes((value & 0xFF, (value >> 8) & 0xFF))


def _jp_nc(address: int) -> bytes:
    return b"\xD2" + _word(address)


def _assert_hl(code: bytearray, expected: int) -> None:
    code += phase1._ld_de(expected) + b"\xB7\xED\x52" + phase1._jp_nz(FAIL_PC)


def _setup_pipe(code: bytearray, s: dict[str, int]) -> None:
    phase3_pipe_create._setup(code, s)
    code += b"\x21" + _word(0xA100)
    code += phase1._call(s["zx48_pipe_create"])
    code += phase1._jp_c(FAIL_PC)
    _assert_hl(code, 0)


def _source_contract(root: Path) -> list[dict[str, object]]:
    pipe = (root / "v1/src/kernel/pipe.asm").read_text(encoding="utf-8")
    handles = (root / "v1/src/kernel/handles.asm").read_text(encoding="utf-8")
    read = pipe[pipe.index("zx48_pipe_read:"):pipe.index("; A=pipe slot, HL=source")]
    block = pipe[pipe.index("zx48_pipe_block_read:"):pipe.index("; C=slot. Wake only waiters")]
    wake = pipe[pipe.index("zx48_pipe_wake_readers:"):pipe.index("; A=kind,C=pipe slot")]
    release = handles[handles.index("zx48_od_release:"):handles.index("; A=handle -> HL=current-process slot.")]
    return [
        {"name":"empty-with-writers-enters-read-wait","passed":"ld a,(ix+PIPE_WRITERS_O)\n    or a\n    ret z" in read and "call zx48_pipe_block_read" in read},
        {"name":"empty-without-writers-returns-zero","passed":"ld hl,0" in read and "ret z" in read},
        {"name":"block-records-pipe-and-wait-state","passed":"ld (ix+PROC_WAIT_OBJECT),c" in block and "ld (ix+PROC_STATE),d" in block},
        {"name":"block-yields-through-scheduler","passed":"jp zx48_schedule" in block},
        {"name":"writer-wake-selects-read-waiters","passed":"zx48_pipe_wake_readers:" in wake and "PROC_WAIT_PIPE_READ" in wake},
        {"name":"wake-clears-object-and-readies-task","passed":"ld (ix+PROC_WAIT_OBJECT),a" in wake and "ld (ix+PROC_STATE),PROC_READY" in wake},
        {"name":"write-path-wakes-readers","passed":"call zx48_pipe_wake_readers" in pipe[pipe.index("zx48_pipe_write:"):pipe.index("zx48_pipe_chunk_limit:")]},
        {"name":"pipe-endpoint-close-only-after-final-od-ref","passed":"dec a\n    ld (ix+OD_REFS_O),a\n    ret nz" in release and "jp zx48_pipe_endpoint_closed" in release},
    ]


def _sleep_wake_fixture(root: Path, s: dict[str, int], kernel: bytes) -> None:
    code = bytearray()
    _setup_pipe(code, s)
    proc = s["process_table"] + s["PROC_DESC_SIZE"]

    code += b"\x0E\x00"
    code += phase1._call(s["zx48_pipe_block_read"])
    phase3_pipe_create._assert_byte(code, proc + s["PROC_STATE"], s["PROC_WAIT_PIPE_READ"])
    phase3_pipe_create._assert_byte(code, proc + s["PROC_WAIT_OBJECT"], 1)

    code += phase3_pipe_create._store_byte(SCRATCH, 0x6D)
    code += b"\x3E\x00"
    code += b"\x21" + _word(SCRATCH)
    code += b"\x01\x01\x00"
    code += phase1._call(s["zx48_pipe_write"])
    code += phase1._jp_c(FAIL_PC)
    _assert_hl(code, 1)
    phase3_pipe_create._assert_byte(code, proc + s["PROC_STATE"], s["PROC_READY"])
    phase3_pipe_create._assert_byte(code, proc + s["PROC_WAIT_OBJECT"], 0)
    phase3_pipe_create._assert_word(code, s["pipe_table"] + s["PIPE_COUNT_O"], 1)
    code += phase1._jp(PASS_PC)

    patched = bytearray(kernel)
    offset = s["zx48_schedule"] - phase1.KERNEL_BASE
    require(0 <= offset < len(patched), "schedule patch outside kernel")
    patched[offset] = 0xC9
    run_sna(root, bytes(code), patch=phase1._kernel_patch(bytes(patched)))


def _dup_eof_fixture(root: Path, s: dict[str, int], kernel: bytes) -> None:
    code = bytearray()
    _setup_pipe(code, s)
    pipe = s["pipe_table"]

    code += b"\x3E\x01" + phase1._call(s["zx48_od_retain"]) + phase1._jp_c(FAIL_PC)
    code += b"\x3E\x01" + phase1._call(s["zx48_od_release"]) + phase1._jp_c(FAIL_PC)
    phase3_pipe_create._assert_byte(code, pipe + s["PIPE_WRITERS_O"], 1)

    code += b"\x3E\x00"
    code += b"\x21" + _word(SCRATCH)
    code += b"\x01\x01\x00"
    code += phase1._call(s["zx48_pipe_read"])
    code += _jp_nc(FAIL_PC)
    code += bytes((0xFE, s["E_INTR"])) + phase1._jp_nz(FAIL_PC)

    code += b"\x3E\x01" + phase1._call(s["zx48_od_release"]) + phase1._jp_c(FAIL_PC)
    phase3_pipe_create._assert_byte(code, pipe + s["PIPE_WRITERS_O"], 0)

    code += b"\x3E\x00"
    code += b"\x21" + _word(SCRATCH)
    code += b"\x01\x04\x00"
    code += phase1._call(s["zx48_pipe_read"])
    code += phase1._jp_c(FAIL_PC)
    _assert_hl(code, 0)
    code += phase1._jp(PASS_PC)

    patched = bytearray(kernel)
    offset = s["zx48_pipe_block_read"] - phase1.KERNEL_BASE
    payload = bytes((0x3E, s["E_INTR"], 0x37, 0xC9))
    require(0 <= offset <= len(patched) - len(payload), "block-read patch outside kernel")
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
    if step != "P3.10":
        raise DriverError(f"Phase-3 pipe-blocking step is not registered: {step}")

    assertions = _source_contract(root)
    failed = [item["name"] for item in assertions if item["passed"] is not True]
    require(not failed, f"static P3.10 contract failures: {failed}")

    result, kernel, listing = phase1._assemble_kernel(root, run_command, require_project_tool)
    commands = [result]
    symbols = phase3_open_descriptions._symbols(
        listing.with_suffix(".sym"),
        (
            "zx48_memory_init","zx48_process_init","zx48_handles_init","zx48_pipe_init",
            "zx48_process_prepare_pid1","zx48_pipe_create","zx48_pipe_read","zx48_pipe_write",
            "zx48_pipe_block_read","zx48_schedule","zx48_od_retain","zx48_od_release",
            "current_pid","process_table","pipe_table","PROC_DESC_SIZE","PROC_STATE",
            "PROC_WAIT_OBJECT","PROC_WAIT_PIPE_READ","PROC_READY","PIPE_COUNT_O",
            "PIPE_WRITERS_O","E_INTR",
        ),
    )

    if action == "test":
        kernel_bytes = kernel.read_bytes()
        _sleep_wake_fixture(root, symbols, kernel_bytes)
        _dup_eof_fixture(root, symbols, kernel_bytes)
        assertions.extend([
            {"name":"reader-enters-wait-pipe-read","passed":True},
            {"name":"writer-wakes-reader-to-ready","passed":True},
            {"name":"duplicate-writer-prevents-premature-eof","passed":True},
            {"name":"final-writer-close-produces-zero-byte-eof","passed":True},
        ])

    hashes = {
        "v1/build/kernel.bin": sha256_file(kernel),
        "v1/src/kernel/pipe.asm": sha256_file(root / "v1/src/kernel/pipe.asm"),
        "v1/src/kernel/scheduler.asm": sha256_file(root / "v1/src/kernel/scheduler.asm"),
        "v1/src/kernel/handles.asm": sha256_file(root / "v1/src/kernel/handles.asm"),
        "v1/tools-host/test-driver/phase3_pipe_blocking.py": sha256_file(root / "v1/tools-host/test-driver/phase3_pipe_blocking.py"),
        "v1/tools-host/test-driver/run.py": sha256_file(root / "v1/tools-host/test-driver/run.py"),
        "v1/dist/certification/P3.09.test.json": sha256_file(root / "v1/dist/certification/P3.09.test.json"),
    }
    return commands, hashes, assertions
