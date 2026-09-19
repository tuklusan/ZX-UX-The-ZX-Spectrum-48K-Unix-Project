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
P321_MARKER = "ZX-UX PHASE 3 ACCEPTANCE PASS"
PHASE_MARKER = "ZX-UX PHASE 3 CERTIFICATION PASS"


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
    return {"R16.00": "PASS"} if number == 1 else {f"P3.{number - 1:02d}": "PASS"}


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
    if step == "P3.15" and action == "test":
        if "prerequisites" in record or record.get("prerequsites") != {"P3.14": "PASS"}:
            raise FinalizeError("P3.15.test.json: frozen prerequisite-key typo changed")
    elif record.get("prerequisites") != expected_prerequisite(step):
        raise FinalizeError(f"{path.name}: prerequisite mismatch")
    source = record.get("source_commit")
    if not isinstance(source, str) or len(source) != 40:
        raise FinalizeError(f"{path.name}: invalid source commit")
    if subprocess.run(
        ["git", "merge-base", "--is-ancestor", source, aggregate_source],
        cwd=root,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    ).returncode:
        raise FinalizeError(f"{path.name}: source is not an ancestor of P3.21 source")
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
        p321 = load(cert / "P3.21.result.json")
        aggregate_source = p321.get("source_commit")
        if not isinstance(aggregate_source, str) or len(aggregate_source) != 40:
            raise FinalizeError("P3.21.result.json: invalid source commit")
        if (
            p321.get("step") != "P3.21"
            or p321.get("action") != "result"
            or p321.get("status") != "PASS"
            or p321.get("pass_marker") != P321_MARKER
            or p321.get("architecture_sha256") != ARCH_SHA
            or p321.get("implementation_plan_sha256") != PLAN_SHA
            or p321.get("worktree_clean") is not True
        ):
            raise FinalizeError("P3.21.result.json: exact acceptance PASS required")
        head = git(root, "rev-parse", "HEAD")
        if subprocess.run(
            ["git", "merge-base", "--is-ancestor", aggregate_source, head],
            cwd=root,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ).returncode:
            raise FinalizeError("P3.21 source is not an ancestor of current HEAD")

        required_records: list[str] = []
        manifest: dict[str, str] = {}
        locks: set[str] = set()
        for number in range(1, 22):
            step = f"P3.{number:02d}"
            for action in ("build", "test"):
                name = f"{step}.{action}.json"
                record = require_record(root, cert / name, step, action, aggregate_source)
                required_records.append(name)
                manifest[name] = sha256(cert / name)
                lock = record.get("toolchain_lock_sha256")
                if not isinstance(lock, str) or len(lock) != 64:
                    raise FinalizeError(f"{name}: invalid toolchain identity")
                locks.add(lock)

        if load(cert / "P3.21.build.json").get("source_commit") != aggregate_source:
            raise FinalizeError("P3.21 build source mismatch")
        if load(cert / "P3.21.test.json").get("source_commit") != aggregate_source:
            raise FinalizeError("P3.21 test source mismatch")
        if len(locks) != 1:
            raise FinalizeError("Phase-3 toolchain identity mismatch")

        result_name = "P3.21.result.json"
        required_records.append(result_name)
        manifest[result_name] = sha256(cert / result_name)

        aggregate = {
            "schema": 2,
            "phase": 3,
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
                {"name": "p3-21-build-test-result-pass", "passed": True},
                {"name": "all-p3-01-through-p3-21-durable-evidence-pass", "passed": True},
                {"name": "rev16-rev07-authority-pass", "passed": True},
                {"name": "frozen-p3-15-test-prerequisite-key-typo-preserved", "passed": True},
                {"name": "phase3-record-manifest-byte-exact", "passed": True},
                {"name": "phase3-gate-stops-before-phase4", "passed": True},
            ],
        }
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(aggregate, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        print("ZX-UX PHASE 3 EVIDENCE FINALIZATION PASS")
        print(f"evidence={output}")
        return 0
    except Exception as exc:
        print(f"ZX-UX PHASE 3 EVIDENCE FINALIZATION FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
