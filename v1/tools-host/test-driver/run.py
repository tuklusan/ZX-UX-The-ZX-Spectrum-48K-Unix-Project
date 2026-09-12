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

import argparse
from pathlib import Path
import sys

sys.dont_write_bytecode = True

import foundation
import foundation_rr
import phase0
import phase0_layout
import phase0_boot
import phase0_im2
import phase0_rom
import phase0_alt
import phase0_loader
import phase0_media
import phase0_rr
import phase1
import phase1_alt
import phase1_keyboard
import phase1_cursor
import phase1_stack
import phase1_startup
import phase1_memory
from driver_core import (
    DriverError,
    find_root,
    read_source_state,
    require_clean_source,
    require_project_tool,
    resolve_evidence_dir,
    run_command,
    sha256_file,
    write_evidence,
)

E0_MODULE = {
    "E0.01": foundation_rr,
    "E0.02": foundation_rr,
    "E0.03": foundation,
    "E0.04": foundation,
    "E0.05": foundation,
    "E0.06": foundation,
}
P0_MODULE = {
    "P0.01": phase0,
    "P0.02": phase0_layout,
    "P0.03": phase0_boot,
    "P0.04": phase0_im2,
    "P0.05": phase0_rom,
    "P0.06": phase0_alt,
    "P0.07": phase0_loader,
    "P0.08": phase0_media,
    "P0.09": phase0_media,
    "P0.10": phase0_media,
    **{f"P0.{number:02d}": phase0_rr for number in range(11, 35)},
}


def dispatch(root: Path, action: str, step: str):
    kwargs = {
        "sha256_file": sha256_file,
        "run_command": run_command,
        "require_project_tool": require_project_tool,
    }
    module = E0_MODULE.get(step)
    if module is not None:
        return module.dispatch(root, action, step, **kwargs)
    module = P0_MODULE.get(step)
    if module is not None:
        if module is phase0_media:
            return module.dispatch(root, action, step)
        return module.dispatch(root, action, step, **kwargs)
    if step.startswith(("E0.", "P0.")):
        raise DriverError(f"numbered foundation/Phase-0 step is not registered: {step}")
    if step == "P1.01":
        return phase1_startup.dispatch(root, action, step, **kwargs)
    if step in ("P1.02", "P1.03", "P1.04", "P1.05"):
        return phase1_memory.dispatch(root, action, step, **kwargs)
    if step == "P1.30":
        return phase1_alt.dispatch(root, action, step, **kwargs)
    if step == "P1.31":
        return phase1_keyboard.dispatch(root, action, step, **kwargs)
    if step == "P1.32":
        return phase1_cursor.dispatch(root, action, step, **kwargs)
    if step == "P1.33":
        return phase1_stack.dispatch(root, action, step, **kwargs)
    if step.startswith("P1."):
        return phase1.dispatch(root, action, step, **kwargs)
    raise DriverError(f"step is not registered with the deterministic test driver: {step}")


def prerequisite_statuses(step: str) -> dict[str, str]:
    if step in E0_MODULE:
        number = int(step.split(".", 1)[1])
        return {} if number == 1 else {f"E0.{number - 1:02d}": "PASS"}
    if step in P0_MODULE:
        number = int(step.split(".", 1)[1])
        return {"E0.06": "PASS"} if number == 1 else {f"P0.{number - 1:02d}": "PASS"}
    return {}


def source_state_unchanged(before, after) -> bool:
    return (
        before.source_commit == after.source_commit
        and before.toolchain_lock_sha256 == after.toolchain_lock_sha256
        and before.architecture_sha256 == after.architecture_sha256
        and after.worktree_clean
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="ZX-UX deterministic host build/test driver.")
    parser.add_argument("action", choices=("build", "test"))
    parser.add_argument("--step", required=True)
    parser.add_argument("--evidence-dir", help="external scratch evidence directory")
    parser.add_argument("--probe-root", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()

    try:
        root = find_root(Path(__file__))
        if args.probe_root:
            print(root)
            return 0
        source_state = require_clean_source(root)
        evidence_dir = resolve_evidence_dir(root, source_state.source_commit, args.evidence_dir)
        commands, hashes, assertions = dispatch(root, args.action, args.step)
        after = read_source_state(root)
        if not source_state_unchanged(source_state, after):
            raise DriverError("step changed the source checkout or certification inputs")
        failed_assertions = [item for item in assertions if item.get("passed") is not True]
        status = "PASS" if not failed_assertions else "FAIL"
        evidence_path = write_evidence(
            root,
            evidence_dir,
            source_state,
            args.step,
            args.action,
            status=status,
            prerequisites=prerequisite_statuses(args.step),
            commands=commands,
            hashes=hashes,
            assertions=assertions,
        )
        if failed_assertions:
            raise DriverError(f"{len(failed_assertions)} assertion(s) failed")
        print(f"ZX-UX {args.step} {args.action.upper()} PASS")
        print(f"evidence={evidence_path}")
        return 0
    except (DriverError, OSError, ValueError) as exc:
        print(f"ZX-UX TEST DRIVER FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
