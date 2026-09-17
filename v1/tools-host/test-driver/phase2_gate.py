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


CERTIFIED_STEPS = ("P2.01", "P2.02", "P2.03", "P2.04", "P2.05", "P2.06", "P2.07")
CANDIDATE_STEPS: tuple[str, ...] = ("P2.08", "P2.09", "P2.10", "P2.11", "P2.12", "P2.13", "P2.14", "P2.15", "P2.16", "P2.17", "P2.18", "P2.19", "P2.20", "P2.21")
# P2.16 through P2.21 are intentionally included in the exact-head aggregate certification gate.
# P2.17 fixture constants are now explicit staged-fixture dependencies, matching their kernel definitions.
# P2.21 keeps production kernel bytes unchanged while qualifying the exact SYS_PROC_INFO/PINFOQ1 and PROC1 packed ABI.


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
                diagnostic_suffix = ""
                if step == "P2.08" and action == "test":
                    diagnostic_runner = root / "v1/tools-host/test-driver/phase2_context_diag.py"
                    diagnostic = run_command(
                        [python, diagnostic_runner],
                        cwd=root,
                        timeout_seconds=90.0,
                    )
                    records.append({
                        "kind": "diagnostic",
                        "step": step,
                        "action": "post-frame-diagnostic",
                        "result": asdict(diagnostic),
                    })
                    diagnostic_suffix = (
                        f" diagnostic_exit={diagnostic.exit_code} "
                        f"diagnostic_timed_out={diagnostic.timed_out} "
                        f"diagnostic_stdout={diagnostic.stdout!r} "
                        f"diagnostic_stderr={diagnostic.stderr!r}"
                    )
                failure = (
                    f"{step} {action} failed: exit={result.exit_code} "
                    f"timed_out={result.timed_out} stdout={result.stdout!r} "
                    f"stderr={result.stderr!r}{diagnostic_suffix}"
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
