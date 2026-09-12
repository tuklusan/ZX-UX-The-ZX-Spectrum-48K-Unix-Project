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

import os
from pathlib import Path
import sys

from driver_core import DriverError, find_root, run_command
import phase1_probe

# New ordered Phase-1 implementation runs here before admission to the certified
# set. A red early gate cannot be hidden by the already-certified correction set.
PRE_ADMISSION_STEPS = (
    "P1.09",
)

# P1.01-P1.08 were admitted after clean pinned-environment runs of their exact
# build/test pairs plus Quality/CI. P1.28-P1.33 remain the earlier certified
# correction suite. Every admitted step is replayed on every relevant push.
CERTIFIED_STEPS = (
    "P1.01",
    "P1.02",
    "P1.03",
    "P1.04",
    "P1.05",
    "P1.06",
    "P1.07",
    "P1.08",
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


def _persist_failure(message: str) -> None:
    evidence = os.environ.get("ZXUX_EVIDENCE_DIR")
    if not evidence:
        return
    path = Path(evidence)
    path.mkdir(parents=True, exist_ok=True)
    (path / "phase1-failure.txt").write_text(message + "\n", encoding="utf-8")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (DriverError, OSError, ValueError) as exc:
        message = f"ZX-UX PHASE 1 CERTIFICATION FAIL: {exc}"
        _persist_failure(message)
        print(message, file=sys.stderr)
        raise SystemExit(1)
