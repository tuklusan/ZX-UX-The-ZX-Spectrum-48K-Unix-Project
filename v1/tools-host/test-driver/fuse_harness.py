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
import struct
import tempfile
from typing import Callable

from driver_core import DriverError, run_command

RAM_START = 0x4000
RAM_SIZE = 0xC000
PASS_PC = 0xB000
FAIL_PC = 0xB001
ENTRY_PC = 0x9000
SNAPSHOT_STACK = 0xBFFE


def make_sna(code: bytes, *, entry: int = ENTRY_PC, patch: Callable[[bytearray], None] | None = None) -> bytes:
    if not (RAM_START <= entry < 0x10000) or entry + len(code) > 0x10000:
        raise DriverError("SNA code placement outside RAM")
    ram = bytearray(RAM_SIZE)
    ram[entry - RAM_START:entry - RAM_START + len(code)] = code
    # 48K SNA stores the resumed PC on the snapshot stack.
    struct.pack_into("<H", ram, SNAPSHOT_STACK - RAM_START, entry)
    if patch is not None:
        patch(ram)
    header = bytearray(27)
    header[0] = 0xFE  # I: canonical ZX-UX IM2 high byte is harmless before fixture changes IM.
    header[19] = 0x04  # IFF2 set.
    struct.pack_into("<H", header, 23, SNAPSHOT_STACK)
    header[25] = 1  # IM 1 until fixture deliberately changes it.
    header[26] = 0  # border.
    return bytes(header) + bytes(ram)


def run_sna(root: Path, code: bytes, *, patch: Callable[[bytearray], None] | None = None, timeout: float = 15.0):
    fuse = root / "tools/runtime/fuse/bin/fuse"
    if not fuse.is_file():
        raise DriverError("project-local FUSE executable missing")
    with tempfile.TemporaryDirectory(prefix="zxux-fuse-") as temporary:
        sna = Path(temporary) / "fixture.sna"
        sna.write_bytes(make_sna(code, patch=patch))
        command = (
            f"breakpoint 0x{PASS_PC:04x}\n"
            "commands 1\n"
            "exit 0\n"
            "end\n"
            f"breakpoint 0x{FAIL_PC:04x}\n"
            "commands 2\n"
            "exit 1\n"
            "end\n"
            "continue"
        )
        result = run_command(
            [
                "/usr/bin/env",
                "SDL_VIDEODRIVER=dummy",
                "SDL_AUDIODRIVER=dummy",
                fuse,
                "--machine", "48",
                "--no-sound",
                "--no-confirm-actions",
                "--debugger-command", command,
                sna,
            ],
            cwd=root,
            timeout_seconds=timeout,
        )
        if result.timed_out or result.exit_code != 0:
            raise DriverError(
                "headless FUSE fixture failed: "
                f"exit={result.exit_code} timed_out={result.timed_out} "
                f"stdout={result.stdout!r} stderr={result.stderr!r}"
            )
        return result


def jp(address: int) -> bytes:
    return bytes((0xC3, address & 0xFF, address >> 8))
