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


class Phase3PipeBrokenError(DriverError):
    """Raised when the P3.13 broken-pipe contract regresses."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Phase3PipeBrokenError(message)


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


def _source_contract(root: Path) -> list[dict[str, object]]:
    pipe = (root / "v1/src/kernel/pipe.asm").read_text(encoding="utf-8")
    handles = (root / "v1/src/kernel/handles.asm").read_text(encoding="utf-8")
    write = pipe[pipe.index("zx48_pipe_write:"):pipe.index("; A=ring position, BC=candidate.")]
    close = pipe[pipe.index("zx48_pipe_endpoint_closed:"):pipe.index("; A=slot. Free only after both logical ends are closed")]
    release = handles[handles.index("zx48_od_release:"):handles.index("; A=handle -> HL=current-process slot.")]
    return [
        {"name":"write-checks-read-endpoint-before-copy","passed":"ld a,(ix+PIPE_READERS_O)\n    or a\n    jp z,zx48_pipe_broken" in write},
        {"name":"broken-pipe-returns-e-pipe","passed":"zx48_pipe_broken:\n    ld a,E_PIPE\n    scf\n    ret" in pipe},
        {"name":"final-read-close-clears-logical-reader","passed":"zx48_pipe_close_reader:" in close and "ld (ix+PIPE_READERS_O),a" in close},
        {"name":"read-close-wakes-writers","passed":"call zx48_pipe_wake_writers" in close},
        {"name":"od-release-defers-endpoint-close-until-final-ref","passed":"dec a\n    ld (ix+OD_REFS_O),a\n    ret nz" in release},
        {"name":"final-read-od-release-closes-pipe-endpoint","passed":"cp OD_KIND_PIPE_READ" in release and "jp zx48_pipe_endpoint_closed" in release},
    ]


def _dup_read_fixture(root: Path, s: dict[str, int], kernel: bytes) -> None:
    code = bytearray()
    buffer = _setup_pipe(code, s)
    pipe = s["pipe_table"]

    code += phase3_pipe_create._store_byte(SRC, 0x61)
    code += phase3_pipe_create._store_byte(SRC + 1, 0x62)
    code += phase3_pipe_create._store_byte(buffer + 1, 0xCC)

    code += b"\x3E\x00" + phase1._call(s["zx48_od_retain"]) + phase1._jp_c(FAIL_PC)
    code += b"\x3E\x00" + phase1._call(s["zx48_od_release"]) + phase1._jp_c(FAIL_PC)
    phase3_pipe_create._assert_byte(code, pipe + s["PIPE_READERS_O"], 1)

    code += b"\x3E\x00"
    code += b"\x21" + _word(SRC)
    code += b"\x01\x01\x00"
    code += phase1._call(s["zx48_pipe_write"]) + phase1._jp_c(FAIL_PC)
    _assert_hl(code, 1)
    phase3_pipe_create._assert_word(code, pipe + s["PIPE_COUNT_O"], 1)
    phase3_pipe_create._assert_byte(code, buffer, 0x61)

    code += b"\x3E\x00" + phase1._call(s["zx48_od_release"]) + phase1._jp_c(FAIL_PC)
    phase3_pipe_create._assert_byte(code, pipe + s["PIPE_READERS_O"], 0)

    code += b"\x3E\x00"
    code += b"\x21" + _word(SRC + 1)
    code += b"\x01\x01\x00"
    code += phase1._call(s["zx48_pipe_write"])
    code += _jp_nc(FAIL_PC)
    code += bytes((0xFE, s["E_PIPE"])) + phase1._jp_nz(FAIL_PC)
    phase3_pipe_create._assert_word(code, pipe + s["PIPE_COUNT_O"], 1)
    phase3_pipe_create._assert_byte(code, buffer + 1, 0xCC)

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
    if step != "P3.13":
        raise DriverError(f"Phase-3 broken-pipe step is not registered: {step}")

    assertions = _source_contract(root)
    failed = [item["name"] for item in assertions if item["passed"] is not True]
    require(not failed, f"static P3.13 contract failures: {failed}")

    result, kernel, listing = phase1._assemble_kernel(root, run_command, require_project_tool)
    commands = [result]
    symbols = phase3_open_descriptions._symbols(
        listing.with_suffix(".sym"),
        (
            "zx48_memory_init","zx48_process_init","zx48_handles_init","zx48_pipe_init",
            "zx48_process_prepare_pid1","zx48_pipe_create","zx48_pipe_write",
            "zx48_od_retain","zx48_od_release","current_pid","pipe_table",
            "PIPE_BUFFER_SIZE","PIPE_COUNT_O","PIPE_READERS_O","FAST_END","E_PIPE",
        ),
    )
    require(symbols["PIPE_BUFFER_SIZE"] == 256, "normal pipe buffer must remain 256")

    if action == "test":
        _dup_read_fixture(root, symbols, kernel.read_bytes())
        assertions.extend([
            {"name":"duplicate-read-ref-prevents-premature-e-pipe","passed":True},
            {"name":"final-read-close-enables-e-pipe","passed":True},
            {"name":"broken-pipe-has-no-hidden-write","passed":True},
        ])

    hashes = {
        "v1/build/kernel.bin": sha256_file(kernel),
        "v1/src/kernel/pipe.asm": sha256_file(root / "v1/src/kernel/pipe.asm"),
        "v1/src/kernel/handles.asm": sha256_file(root / "v1/src/kernel/handles.asm"),
        "v1/tools-host/test-driver/phase3_pipe_broken.py": sha256_file(root / "v1/tools-host/test-driver/phase3_pipe_broken.py"),
        "v1/tools-host/test-driver/run.py": sha256_file(root / "v1/tools-host/test-driver/run.py"),
        "v1/dist/certification/P3.12.test.json": sha256_file(root / "v1/dist/certification/P3.12.test.json"),
    }
    return commands, hashes, assertions
