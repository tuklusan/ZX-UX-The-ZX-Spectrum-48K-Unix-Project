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


class Phase3PipeLifetimeError(DriverError):
    """Raised when the P3.14 endpoint/refcount lifetime contract regresses."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Phase3PipeLifetimeError(message)


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
    handles = (root / "v1/src/kernel/handles.asm").read_text(encoding="utf-8")
    process = (root / "v1/src/kernel/process.asm").read_text(encoding="utf-8")

    dup = handles[handles.index("zx48_handle_dup:"):handles.index("; Close every live handle")]
    release = handles[handles.index("zx48_od_release:"):handles.index("; A=handle -> HL=current-process slot.")]
    close = pipe[pipe.index("zx48_pipe_endpoint_closed:"):pipe.index("zx48_pipe_noent:")]
    block = pipe[pipe.index("zx48_pipe_block:"):pipe.index("; C=slot. Wake only waiters")]
    wake = pipe[pipe.index("zx48_pipe_wake:"):pipe.index("; A=kind,C=pipe slot")]
    spawn = process[process.index("; Acquire one shared OD reference"):process.index("zx48_process_spawn_rollback:")]

    return [
        {"name":"dup-retains-same-open-description","passed":"call zx48_od_retain" in dup and "call zx48_handle_install" in dup and "zx48_od_create" not in dup},
        {"name":"spawn-retains-existing-open-descriptions","passed":spawn.count("call zx48_od_retain") >= 3 and "zx48_od_create" not in spawn},
        {"name":"spawn-installs-same-od-identities","passed":all(token in spawn for token in ("ld a,(process_spawn_od0)","ld (ix+PROC_HANDLES+0),a","ld a,(process_spawn_od1)","ld (ix+PROC_HANDLES+1),a","ld a,(process_spawn_od2)","ld (ix+PROC_HANDLES+2),a"))},
        {"name":"final-ref-only-closes-logical-endpoint","passed":"dec a\n    ld (ix+OD_REFS_O),a\n    ret nz" in release and "jp zx48_pipe_endpoint_closed" in release},
        {"name":"logical-endpoint-counts-distinct-from-od-refs","passed":"PIPE_READERS_O" in pipe and "PIPE_WRITERS_O" in pipe and "OD_REFS_O" in handles},
        {"name":"pipe-free-requires-both-endpoints-closed","passed":"ld a,(ix+PIPE_READERS_O)\n    or (ix+PIPE_WRITERS_O)\n    ret nz" in close},
        {"name":"pipe-free-scans-all-waiters","passed":"zx48_pipe_waiter_scan:" in close and "cp c\n    jr z,zx48_pipe_waiter_exists" in close},
        {"name":"block-links-before-schedule","passed":"ld (ix+PROC_WAIT_OBJECT),c\n    ld (ix+PROC_STATE),d\n    jp zx48_schedule" in block},
        {"name":"wake-unlinks-before-ready","passed":"ld (ix+PROC_WAIT_OBJECT),a\n    ld (ix+PROC_STATE),PROC_READY" in wake},
    ]


def _dup_lifetime_and_waiter_fixture(root: Path, s: dict[str, int], kernel: bytes) -> None:
    code = bytearray()
    buffer = _setup_pipe(code, s)
    pipe = s["pipe_table"]
    proc = s["process_table"] + s["PROC_DESC_SIZE"]
    od0 = s["open_description_table"]
    od1 = od0 + s["OD_RECORD_SIZE"]

    code += b"\x3E\x00" + phase1._call(s["zx48_od_retain"]) + phase1._jp_c(FAIL_PC)
    code += b"\x3E\x01" + phase1._call(s["zx48_od_retain"]) + phase1._jp_c(FAIL_PC)
    phase3_pipe_create._assert_byte(code, od0 + s["OD_REFS_O"], 2)
    phase3_pipe_create._assert_byte(code, od1 + s["OD_REFS_O"], 2)
    phase3_pipe_create._assert_byte(code, pipe + s["PIPE_READERS_O"], 1)
    phase3_pipe_create._assert_byte(code, pipe + s["PIPE_WRITERS_O"], 1)

    code += b"\x3E\x00" + phase1._call(s["zx48_od_release"]) + phase1._jp_c(FAIL_PC)
    code += b"\x3E\x01" + phase1._call(s["zx48_od_release"]) + phase1._jp_c(FAIL_PC)
    phase3_pipe_create._assert_byte(code, od0 + s["OD_REFS_O"], 1)
    phase3_pipe_create._assert_byte(code, od1 + s["OD_REFS_O"], 1)
    phase3_pipe_create._assert_byte(code, pipe + s["PIPE_READERS_O"], 1)
    phase3_pipe_create._assert_byte(code, pipe + s["PIPE_WRITERS_O"], 1)

    code += phase3_pipe_create._store_byte(proc + s["PROC_WAIT_OBJECT"], 1)
    code += phase3_pipe_create._store_byte(proc + s["PROC_STATE"], s["PROC_WAIT_CHILD"])

    code += b"\x3E\x00" + phase1._call(s["zx48_od_release"]) + phase1._jp_c(FAIL_PC)
    phase3_pipe_create._assert_byte(code, pipe + s["PIPE_READERS_O"], 0)
    phase3_pipe_create._assert_byte(code, pipe + s["PIPE_WRITERS_O"], 1)
    phase3_pipe_create._assert_word(code, pipe + s["PIPE_PTR_O"], buffer)

    code += b"\x3E\x01" + phase1._call(s["zx48_od_release"]) + phase1._jp_c(FAIL_PC)
    phase3_pipe_create._assert_byte(code, pipe + s["PIPE_READERS_O"], 0)
    phase3_pipe_create._assert_byte(code, pipe + s["PIPE_WRITERS_O"], 0)
    phase3_pipe_create._assert_word(code, pipe + s["PIPE_PTR_O"], buffer)
    phase3_pipe_create._assert_word(code, pipe + s["PIPE_CAPACITY_O"], s["PIPE_BUFFER_SIZE"])

    code += phase3_pipe_create._store_byte(proc + s["PROC_WAIT_OBJECT"], 0)
    code += phase3_pipe_create._store_byte(proc + s["PROC_STATE"], s["PROC_READY"])
    code += b"\xAF" + phase1._call(s["zx48_pipe_try_free"]) + phase1._jp_c(FAIL_PC)
    phase3_pipe_create._assert_word(code, pipe + s["PIPE_PTR_O"], 0)
    phase3_pipe_create._assert_word(code, pipe + s["PIPE_CAPACITY_O"], 0)

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
    if step != "P3.14":
        raise DriverError(f"Phase-3 pipe-lifetime step is not registered: {step}")

    assertions = _source_contract(root)
    failed = [item["name"] for item in assertions if item["passed"] is not True]
    require(not failed, f"static P3.14 contract failures: {failed}")

    result, kernel, listing = phase1._assemble_kernel(root, run_command, require_project_tool)
    commands = [result]
    symbols = phase3_open_descriptions._symbols(
        listing.with_suffix(".sym"),
        (
            "zx48_memory_init","zx48_process_init","zx48_handles_init","zx48_pipe_init",
            "zx48_process_prepare_pid1","zx48_pipe_create","zx48_pipe_try_free",
            "zx48_od_retain","zx48_od_release","current_pid","process_table","pipe_table",
            "open_description_table","PROC_DESC_SIZE","PROC_STATE","PROC_WAIT_OBJECT",
            "PROC_WAIT_CHILD","PROC_READY","OD_RECORD_SIZE","OD_REFS_O",
            "PIPE_BUFFER_SIZE","PIPE_PTR_O","PIPE_CAPACITY_O","PIPE_READERS_O",
            "PIPE_WRITERS_O","FAST_END",
        ),
    )
    require(symbols["PIPE_BUFFER_SIZE"] == 256, "normal pipe buffer must remain 256")

    if action == "test":
        _dup_lifetime_and_waiter_fixture(root, symbols, kernel.read_bytes())
        assertions.extend([
            {"name":"dup-refs-do-not-change-logical-endpoint-counts","passed":True},
            {"name":"final-ref-closes-each-logical-endpoint","passed":True},
            {"name":"pipe-object-retained-while-waiter-exists","passed":True},
            {"name":"pipe-object-freed-after-final-ends-and-waiter-unlink","passed":True},
        ])

    hashes = {
        "v1/build/kernel.bin": sha256_file(kernel),
        "v1/src/kernel/pipe.asm": sha256_file(root / "v1/src/kernel/pipe.asm"),
        "v1/src/kernel/handles.asm": sha256_file(root / "v1/src/kernel/handles.asm"),
        "v1/src/kernel/process.asm": sha256_file(root / "v1/src/kernel/process.asm"),
        "v1/tools-host/test-driver/phase3_pipe_lifetime.py": sha256_file(root / "v1/tools-host/test-driver/phase3_pipe_lifetime.py"),
        "v1/tools-host/test-driver/run.py": sha256_file(root / "v1/tools-host/test-driver/run.py"),
        "v1/dist/certification/P3.13.test.json": sha256_file(root / "v1/dist/certification/P3.13.test.json"),
    }
    return commands, hashes, assertions
