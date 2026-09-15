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
import phase2_spawn_atomic


class Phase2HandleInheritanceError(DriverError):
    """Raised when the P2.11 shared-open-description scaffold regresses."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Phase2HandleInheritanceError(message)


def _source_contract(root: Path) -> list[dict[str, object]]:
    process = (root / "v1/src/kernel/process.asm").read_text(encoding="utf-8")
    handles = (root / "v1/src/kernel/handles.asm").read_text(encoding="utf-8")

    retain_sequence = (
        "ld a,(process_spawn_od0)\n    call zx48_od_retain",
        "ld a,(process_spawn_od1)\n    call zx48_od_retain",
        "ld a,(process_spawn_od2)\n    call zx48_od_retain",
    )
    child_slots = (
        "ld a,(process_spawn_od0)\n    ld (ix+PROC_HANDLES+0),a",
        "ld a,(process_spawn_od1)\n    ld (ix+PROC_HANDLES+1),a",
        "ld a,(process_spawn_od2)\n    ld (ix+PROC_HANDLES+2),a",
    )
    rollback_releases = (
        "ld a,(process_spawn_od2)\n    call zx48_od_release",
        "ld a,(process_spawn_od1)\n    call zx48_od_release",
        "ld a,(process_spawn_od0)\n    call zx48_od_release",
    )

    return [
        {"name": "spawn-retains-each-inherited-std-open-description", "passed": all(item in process for item in retain_sequence)},
        {"name": "child-std-slots-store-parent-open-description-identities", "passed": all(item in process for item in child_slots)},
        {"name": "duplicate-parent-std-selection-retains-duplicate-shared-reference", "passed": "Duplicate\n    ; selected parent handles therefore acquire duplicate references" in process},
        {"name": "retain-overflow-is-fail-closed", "passed": "cp $ff\n    jp z,zx48_handle_busy" in handles},
        {"name": "spawn-rollback-releases-every-successful-retain", "passed": all(item in process for item in rollback_releases)},
        {"name": "open-description-offset-is-shared-record-state", "passed": "OD_OFFSET_O                EQU 4" in handles and "open_description_table" in handles},
        {"name": "handle-dup-retains-shared-description-not-independent-offset", "passed": "call zx48_od_retain" in handles and "call zx48_handle_install" in handles},
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
    if step != "P2.11":
        raise DriverError(f"Phase-2 handle-inheritance step is not registered: {step}")

    static_assertions = _source_contract(root)
    failed = [item["name"] for item in static_assertions if item["passed"] is not True]
    require(not failed, f"static P2.11 contract failures: {failed}")

    # P2.10's deterministic SNA is deliberately reused as the smallest executable
    # fixture for this already-present scaffold: it proves that stdout/stderr may
    # select one OD, that child slots preserve OD identity, that each inherited
    # slot increments the same record, and that retain overflow rolls the complete
    # spawn transaction back.  P2.11 adds independent source assertions so this is
    # certification of the handle contract rather than a blind prerequisite rerun.
    commands, hashes, runtime_assertions = phase2_spawn_atomic.dispatch(
        root,
        action,
        "P2.10",
        sha256_file=sha256_file,
        run_command=run_command,
        require_project_tool=require_project_tool,
    )
    assertions = static_assertions + runtime_assertions
    return commands, hashes, assertions
