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

from dataclasses import asdict
import json
import os
from pathlib import Path
import sys

from driver_core import DriverError, find_root, run_command


CERTIFIED_STEPS = ("P2.01", "P2.02")
CANDIDATE_STEPS: tuple[str, ...] = ()


def _diagnostic_path() -> Path | None:
    configured = os.environ.get("ZXUX_EVIDENCE_DIR")
    if not configured:
        return None
    directory = Path(configured).expanduser().resolve()
    directory.mkdir(parents=True, exist_ok=True)
    return directory / "phase2-gate-diagnostic.json"


def _write_diagnostic(
    records: list[dict[str, object]],
    *,
    status: str,
    failure: str | None = None,
) -> None:
    destination = _diagnostic_path()
    if destination is None:
        return
    payload: dict[str, object] = {
        "schema": 1,
        "status": status,
        "records": records,
    }
    if failure is not None:
        payload["failure"] = failure
    destination.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def main() -> int:
    root = find_root(Path(__file__))
    runner = root / "v1/tools-host/test-driver/run.py"
    python = Path(sys.executable).resolve()
    if not runner.is_file():
        raise DriverError("deterministic test driver missing")

    records: list[dict[str, object]] = []
    for step in (*CERTIFIED_STEPS, *CANDIDATE_STEPS):
        for action in ("build", "test"):
            result = run_command(
                [python, runner, action, "--step", step],
                cwd=root,
                timeout_seconds=90.0,
            )
            record = {
                "kind": "driver",
                "step": step,
                "action": action,
                "result": asdict(result),
            }
            records.append(record)
            if result.timed_out or result.exit_code != 0:
                failure = (
                    f"{step} {action} failed: exit={result.exit_code} "
                    f"timed_out={result.timed_out} stdout={result.stdout!r} "
                    f"stderr={result.stderr!r}"
                )
                _write_diagnostic(records, status="FAIL", failure=failure)
                raise DriverError(failure)
            _write_diagnostic(records, status="RUNNING")

    _write_diagnostic(records, status="PASS")
    print("ZX-UX PHASE 2 REGISTERED/CANDIDATE GATE PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (DriverError, OSError, ValueError) as exc:
        print(f"ZX-UX PHASE 2 VALIDATION FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
