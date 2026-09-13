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
from typing import Any, Callable

from driver_core import DriverError
import phase1
import phase1_keyboard as keyboard


class BreakSamplingError(DriverError):
    """Raised when the P1.15 minimal BREAK sampling contract is violated."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise BreakSamplingError(message)


def _strip_asm(text: str) -> str:
    return "\n".join(line.split(";", 1)[0].rstrip().lower() for line in text.splitlines())


def _block(text: str, start: str, end: str) -> str:
    first = text.find(start.lower())
    last = text.find(end.lower(), first + len(start))
    require(0 <= first < last, f"source block missing: {start}..{end}")
    return text[first:last]


def _isr_has_only_minimal_break_producer(interrupt_raw: str) -> bool:
    interrupt = _strip_asm(interrupt_raw)
    handler = _block(interrupt, "zx48_interrupt:", "zx48_interrupt_work:")
    work = _block(interrupt, "zx48_interrupt_work:", "    endm")
    calls = re.findall(r"(?m)^\s*call\s+([a-z0-9_']+)", handler)
    forbidden = (
        "zx48_schedule",
        "zx48_keyboard_decode",
        "zx48_keyboard_getkey",
        "zx48_process_kill",
        "zx48_process_exit",
        "zx48_pipe",
        "zx48_alloc",
        "zx48_free",
        "zx48_rom_",
    )
    return (
        set(calls) <= {"zx48_kernel_stack_sample", "zx48_interrupt_work"}
        and calls.count("zx48_interrupt_work") == 2
        and "call " not in work
        and not any(token in work for token in forbidden)
        and "ld (break_pending),a" in work
    )


def _source_contract(root: Path) -> list[dict[str, object]]:
    interrupt = (root / "v1/src/kernel/interrupt.asm").read_text(encoding="utf-8")
    assertions = keyboard._source_contract(root)
    assertions.append(
        {
            "name": "break-isr-is-minimal-nonblocking-producer-only",
            "passed": _isr_has_only_minimal_break_producer(interrupt),
        }
    )
    return assertions


def _negative_contract(root: Path) -> dict[str, object]:
    interrupt = (root / "v1/src/kernel/interrupt.asm").read_text(encoding="utf-8")
    mutated = interrupt.replace(
        "zx48_interrupt_done:\n    ret",
        "zx48_interrupt_done:\n    call zx48_schedule\n    ret",
        1,
    )
    return {
        "name": "reject-blocking-service-call-from-im2",
        "passed": not _isr_has_only_minimal_break_producer(mutated),
    }


def dispatch(
    root: Path,
    action: str,
    step: str,
    *,
    sha256_file: Callable[[Path], str],
    run_command: Callable[..., Any],
    require_project_tool: Callable[[Path, str | Path], Path],
):
    if step != "P1.15":
        raise BreakSamplingError(f"BREAK sampling step is not registered: {step}")

    assertions = _source_contract(root)
    failed = [item["name"] for item in assertions if item["passed"] is not True]
    require(not failed, f"static P1.15 BREAK failures: {failed}")

    command, kernel, listing = phase1._assemble_kernel(root, run_command, require_project_tool)
    labels = phase1._labels(listing, ("zx48_interrupt", "altreg_busy", "break_pending"))
    kernel_bytes = kernel.read_bytes()

    if action == "test":
        keyboard._break_matrix_test(root, labels, kernel_bytes)
        assertions.append(_negative_contract(root))
        assertions.extend(
            [
                {"name": "break-transition-matrix-without-isr-task-switch", "passed": True},
                {"name": "break-cancellation-policy-remains-outside-im2", "passed": True},
            ]
        )

    paths = (
        root / "v1/src/kernel/interrupt.asm",
        root / "v1/src/kernel/keyboard.asm",
        root / "v1/tools-host/test-driver/phase1_break.py",
        root / "v1/tools-host/test-driver/phase1_keyboard.py",
        kernel,
    )
    return [command], {str(path.relative_to(root)): sha256_file(path) for path in paths}, assertions
