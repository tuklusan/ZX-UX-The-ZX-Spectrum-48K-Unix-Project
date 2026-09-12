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
import sys

from driver_core import DriverError, find_root, run_command
import phase1_probe

# These probes exercise implementation that is not yet admitted to the ordered
# Phase-1 certification set because P1.01 still owns the preceding startup/BSS
# gate. They run on every relevant push so allocator/accounting regressions are
# caught without pretending the phase order has been satisfied.
PRE_ADMISSION_STEPS = (
    "P1.02",
    "P1.03",
    "P1.04",
    "P1.05",
)

# Each entry is admitted only after its implementation and deterministic driver
# have passed the normal check-in review. The workflow executes every admitted
# step on every relevant push, so later changes cannot silently regress an
# earlier Phase-1 correction gate.
CERTIFIED_STEPS = (
    "P1.28",
    "P1.29",
    "P1.30",
    "P1.31",
    "P1.32",
    "P1.33",
)


def _run_step_set(root: Path, runner: Path, python: Path, steps: tuple[str, ...], label: str) -> None:
    for step in steps:
        for action in ("build", "test"):
            result = run_command(
                [python, runner, action, "--step", step],
                cwd=root,
                timeout_seconds=60.0,
            )
            if result.timed_out or result.exit_code != 0:
                raise DriverError(
                    f"{label} {step} {action} failed: exit={result.exit_code} "
                    f"timed_out={result.timed_out} stdout={result.stdout!r} "
                    f"stderr={result.stderr!r}"
                )


def main() -> int:
    root = find_root(Path(__file__))
    runner = root / "v1/tools-host/test-driver/run.py"
    python = Path(sys.executable).resolve()
    if not runner.is_file():
        raise DriverError("deterministic test driver missing")

    phase1_probe.run(root)
    _run_step_set(root, runner, python, PRE_ADMISSION_STEPS, "pre-admission")
    _run_step_set(root, runner, python, CERTIFIED_STEPS, "certified")
    print("ZX-UX PHASE 1 REGISTERED CERTIFICATION PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (DriverError, OSError, ValueError) as exc:
        print(f"ZX-UX PHASE 1 CERTIFICATION FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
