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
import phase0
import phase0_layout
import phase0_boot
from driver_core import (
    DriverError,
    find_root,
    require_project_tool,
    run_command,
    sha256_file,
    write_evidence,
)


def dispatch(root: Path, action: str, step: str):
    kwargs = {
        "sha256_file": sha256_file,
        "run_command": run_command,
        "require_project_tool": require_project_tool,
    }
    if step.startswith("E0."):
        return foundation.dispatch(root, action, step, **kwargs)
    if step == "P0.02":
        return phase0_layout.dispatch(root, action, step, **kwargs)
    if step == "P0.03":
        return phase0_boot.dispatch(root, action, step, **kwargs)
    if step.startswith("P0."):
        return phase0.dispatch(root, action, step, **kwargs)
    raise DriverError(f"step is not registered with the deterministic test driver: {step}")


def main() -> int:
    parser = argparse.ArgumentParser(description="ZX-UX deterministic host build/test driver.")
    parser.add_argument("action", choices=("build", "test"))
    parser.add_argument("--step", required=True)
    parser.add_argument("--probe-root", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()

    try:
        root = find_root(Path(__file__))
        if args.probe_root:
            print(root)
            return 0
        commands, hashes, assertions = dispatch(root, args.action, args.step)
        failed_assertions = [item for item in assertions if item.get("passed") is not True]
        status = "PASS" if not failed_assertions else "FAIL"
        evidence_path = write_evidence(
            root,
            args.step,
            args.action,
            status=status,
            commands=commands,
            hashes=hashes,
            assertions=assertions,
        )
        if failed_assertions:
            raise DriverError(f"{len(failed_assertions)} assertion(s) failed")
        print(f"ZX-UX {args.step} {args.action.upper()} PASS")
        print(f"evidence={evidence_path.relative_to(root)}")
        return 0
    except (DriverError, OSError, ValueError) as exc:
        print(f"ZX-UX TEST DRIVER FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
