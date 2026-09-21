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

from driver_core import DriverError
from fuse_harness import FAIL_PC, PASS_PC, run_sna
import phase1


class P627Error(DriverError):
    pass


def require(value, message):
    if not value:
        raise P627Error(message)


def _word(value):
    return bytes((value & 0xFF, (value >> 8) & 0xFF))


def _setb(address, value):
    return bytes((0x3E, value & 0xFF, 0x32)) + _word(address)


def _expectb(address, value):
    return b"\x3A" + _word(address) + bytes((0xFE, value & 0xFF)) + phase1._jp_nz(FAIL_PC)


def dispatch(root: Path, action: str, step: str, *, sha256_file, run_command, require_project_tool):
    if step != "P6.27":
        raise DriverError(f"Phase-6 cursor-restoration step is not registered: {step}")

    shell = (root / "v1/src/shell/sh.asm").read_text(encoding="utf-8")
    cursor = (root / "v1/src/kernel/cursor.asm").read_text(encoding="utf-8")
    block = shell.split("MACRO EMIT_P627_CURSOR_ROUTINES", 1)[1].split("ENDM", 1)[0]
    assertions = [
        {"name": "foreground-wrapper-hides-before-launch",
         "passed": block.index("call sh_p627_cursor_begin") < block.index("call sh_p621_launch_foreground")},
        {"name": "foreground-wrapper-restores-after-all-launch-returns",
         "passed": "call sh_p621_launch_foreground\n    push af\n    call sh_p627_cursor_end" in block},
        {"name": "snapshot-public-mode-and-shape",
         "passed": "P627_GET_MODE" in block and "P627_GET_CURSOR" in block},
        {"name": "hide-uses-public-shape-off",
         "passed": "P627_SET_CURSOR" in block and "xor a\n    ld (p627_arg),a" in block},
        {"name": "restore-mode-only-if-changed",
         "passed": "p627_current_mode" in block and "P627_SET_MODE" in block},
        {"name": "cleanup-restores-shape-even-after-mode-error",
         "passed": "sh_p627_record_error:" in block and "sh_p627_restore_shape:" in block},
        {"name": "cursor-phase-is-not-reset-by-shell-hide",
         "passed": "P627_CURSOR_HIDDEN_SHAPE EQU TTY_CURSOR_OFF" in cursor},
    ]
    require(all(item["passed"] for item in assertions), "P6.27 static contract failure")

    cmd, kernel, listing = phase1._assemble_kernel(root, run_command, require_project_tool)
    commands = [cmd]
    labels = phase1._labels(
        listing,
        (
            "zx48_console_init",
            "zx48_cursor_service",
            "zx48_cursor_hide",
            "zx48_cursor_show",
            "tty_mode",
            "tty_cursor_shape",
            "tty_cursor_visible",
            "cursor_phase",
            "screen_mutation_depth",
        ),
    )
    kernel_bytes = kernel.read_bytes()

    if action == "test":
        code = bytearray(b"\xF3" + phase1._ld_sp(0xFD00))
        code += phase1._call(labels["zx48_console_init"])
        code += phase1._call(labels["zx48_cursor_service"])
        code += _expectb(labels["tty_mode"], 64)
        code += _expectb(labels["tty_cursor_shape"], 1)
        code += _expectb(labels["cursor_phase"], 1)
        code += _expectb(labels["tty_cursor_visible"], 1)
        code += phase1._call(labels["zx48_cursor_hide"])
        code += _expectb(labels["screen_mutation_depth"], 1)
        code += _expectb(labels["tty_cursor_visible"], 0)
        code += _setb(labels["tty_cursor_shape"], 0)
        code += phase1._call(labels["zx48_cursor_show"])
        code += _expectb(labels["screen_mutation_depth"], 0)
        code += _expectb(labels["tty_cursor_visible"], 0)
        code += _setb(labels["tty_cursor_shape"], 1)
        code += phase1._call(labels["zx48_cursor_service"])
        code += _expectb(labels["cursor_phase"], 1)
        code += _expectb(labels["tty_cursor_visible"], 1)
        code += phase1._jp(PASS_PC)
        run_sna(root, bytes(code), patch=phase1._kernel_patch(kernel_bytes))
        assertions += [
            {"name": "fuse-hide-removes-drawn-xor", "passed": True},
            {"name": "fuse-restore-reconciles-saved-shape", "passed": True},
            {"name": "fuse-restore-preserves-logical-blink-phase", "passed": True},
        ]

    hashes = {
        "v1/src/shell/sh.asm": sha256_file(root / "v1/src/shell/sh.asm"),
        "v1/src/kernel/cursor.asm": sha256_file(root / "v1/src/kernel/cursor.asm"),
        "v1/build/kernel.bin": sha256_file(kernel),
        "v1/tools-host/test-driver/phase6_cursor_restore.py": sha256_file(root / "v1/tools-host/test-driver/phase6_cursor_restore.py"),
        "v1/tools-host/test-driver/run.py": sha256_file(root / "v1/tools-host/test-driver/run.py"),
        "v1/dist/certification/P6.26.build.json": sha256_file(root / "v1/dist/certification/P6.26.build.json"),
        "v1/dist/certification/P6.26.test.json": sha256_file(root / "v1/dist/certification/P6.26.test.json"),
        "v1/dist/media/P6.26/manifest.json": sha256_file(root / "v1/dist/media/P6.26/manifest.json"),
    }
    return commands, hashes, assertions
