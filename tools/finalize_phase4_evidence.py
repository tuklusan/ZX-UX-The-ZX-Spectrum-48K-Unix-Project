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
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ARCH_SHA = "24fe9d206c2f05bbc24f11544a5cb5a0b6ab104e9fc52e654a10c2d9734b008c"
PLAN_SHA = "840a52e55f623d3f5453329838728e9933ee650ac78c4f294acbca7910638fbc"
P433_MARKER = "ZX-UX PHASE 4 ACCEPTANCE PASS"
PHASE_MARKER = "ZX-UX PHASE 4 CERTIFICATION PASS"

class FinalizeError(RuntimeError):
    pass

def load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise FinalizeError(f"{path.name}: object required")
    return value

def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def git(root: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=root, text=True, capture_output=True)
    if result.returncode:
        raise FinalizeError(result.stderr.strip() or result.stdout.strip())
    return result.stdout.strip()

def expected_prerequisite(step: str) -> dict[str, str]:
    number = int(step.split(".", 1)[1])
    return {"P3.21": "PASS"} if number == 1 else {f"P4.{number - 1:02d}": "PASS"}

def require_record(root: Path, path: Path, step: str, action: str, aggregate_source: str) -> dict:
    if not path.is_file():
        raise FinalizeError(f"missing durable evidence: {path.name}")
    record = load(path)
    if (
        record.get("step") != step
        or record.get("action") != action
        or record.get("status") != "PASS"
        or record.get("worktree_clean") is not True
    ):
        raise FinalizeError(f"{path.name}: clean PASS required")
    if record.get("architecture_sha256") != ARCH_SHA:
        raise FinalizeError(f"{path.name}: REV16 identity mismatch")
    if record.get("implementation_plan_sha256") != PLAN_SHA:
        raise FinalizeError(f"{path.name}: REV07 identity mismatch")
    if record.get("prerequisites") != expected_prerequisite(step):
        raise FinalizeError(f"{path.name}: prerequisite mismatch")
    source = record.get("source_commit")
    if not isinstance(source, str) or len(source) != 40:
        raise FinalizeError(f"{path.name}: invalid source commit")
    if subprocess.run(
        ["git", "merge-base", "--is-ancestor", source, aggregate_source],
        cwd=root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    ).returncode:
        raise FinalizeError(f"{path.name}: source is not an ancestor of P4.33 source")
    return record

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        root = Path(args.root).resolve()
        output = Path(args.output).resolve()
        cert = root / "v1/dist/certification"
        p433 = load(cert / "P4.33.result.json")
        aggregate_source = p433.get("source_commit")
        if not isinstance(aggregate_source, str) or len(aggregate_source) != 40:
            raise FinalizeError("P4.33.result.json: invalid source commit")
        if (
            p433.get("step") != "P4.33"
            or p433.get("action") != "result"
            or p433.get("status") != "PASS"
            or p433.get("pass_marker") != P433_MARKER
            or p433.get("architecture_sha256") != ARCH_SHA
            or p433.get("implementation_plan_sha256") != PLAN_SHA
            or p433.get("worktree_clean") is not True
            or p433.get("prerequisites") != {"P4.32": "PASS"}
        ):
            raise FinalizeError("P4.33.result.json: exact acceptance PASS required")

        head = git(root, "rev-parse", "HEAD")
        if subprocess.run(
            ["git", "merge-base", "--is-ancestor", aggregate_source, head],
            cwd=root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        ).returncode:
            raise FinalizeError("P4.33 source is not an ancestor of current HEAD")

        required_records: list[str] = []
        manifest: dict[str, str] = {}
        locks: set[str] = set()
        for number in range(1, 34):
            step = f"P4.{number:02d}"
            for action in ("build", "test"):
                name = f"{step}.{action}.json"
                record = require_record(root, cert / name, step, action, aggregate_source)
                required_records.append(name)
                manifest[name] = sha256(cert / name)
                lock = record.get("toolchain_lock_sha256")
                if not isinstance(lock, str) or len(lock) != 64:
                    raise FinalizeError(f"{name}: invalid toolchain identity")
                locks.add(lock)

        if load(cert / "P4.33.build.json").get("source_commit") != aggregate_source:
            raise FinalizeError("P4.33 build source mismatch")
        if load(cert / "P4.33.test.json").get("source_commit") != aggregate_source:
            raise FinalizeError("P4.33 test source mismatch")
        if len(locks) != 1:
            raise FinalizeError("Phase-4 toolchain identity mismatch")

        result_name = "P4.33.result.json"
        required_records.append(result_name)
        manifest[result_name] = sha256(cert / result_name)

        aggregate = {
            "schema": 2,
            "phase": 4,
            "action": "phase-result",
            "status": "PASS",
            "pass_marker": PHASE_MARKER,
            "source_commit": aggregate_source,
            "toolchain_lock_sha256": next(iter(locks)),
            "architecture_sha256": ARCH_SHA,
            "implementation_plan_sha256": PLAN_SHA,
            "worktree_clean": True,
            "required_records": required_records,
            "record_sha256": manifest,
            "assertions": [
                {"name": "p4-33-build-test-result-pass", "passed": True},
                {"name": "all-p4-01-through-p4-33-durable-evidence-pass", "passed": True},
                {"name": "rev16-rev07-authority-pass", "passed": True},
                {"name": "phase4-record-manifest-byte-exact", "passed": True},
                {"name": "phase4-acceptance-bullets-pass", "passed": True},
                {"name": "phase4-gate-stops-before-phase5", "passed": True},
            ],
        }
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(aggregate, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
        print("ZX-UX PHASE 4 EVIDENCE FINALIZATION PASS")
        print(f"evidence={output}")
        return 0
    except Exception as exc:
        print(f"ZX-UX PHASE 4 EVIDENCE FINALIZATION FAIL: {exc}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
