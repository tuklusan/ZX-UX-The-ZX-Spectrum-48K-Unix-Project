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

ROOT = Path(__file__).resolve().parents[1]
CERT = ROOT / "v1/dist/certification"
ARCH_SHA = "24fe9d206c2f05bbc24f11544a5cb5a0b6ab104e9fc52e654a10c2d9734b008c"
PLAN_SHA = "840a52e55f623d3f5453329838728e9933ee650ac78c4f294acbca7910638fbc"
PREFIX = "phase4: activate Phase-4 aggregate evidence for "
P433_MARKER = "ZX-UX PHASE 4 ACCEPTANCE PASS"
PHASE_MARKER = "ZX-UX PHASE 4 CERTIFICATION PASS"

class CertificationError(RuntimeError):
    pass

def git(*args: str) -> str:
    result = subprocess.run(["git", *args], cwd=ROOT, text=True, capture_output=True)
    if result.returncode:
        raise CertificationError(result.stderr.strip() or result.stdout.strip())
    return result.stdout.strip()

def load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise CertificationError(f"{path.name}: object required")
    return value

def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def activation_commit() -> str | None:
    commits = git("log", "--format=%H", "--", "v1/dist/certification/phase-4.json").splitlines()
    return commits[0] if commits else None

def expected_prerequisite(step: str) -> dict[str, str]:
    number = int(step.split(".", 1)[1])
    return {"P3.21": "PASS"} if number == 1 else {f"P4.{number - 1:02d}": "PASS"}

def validate_complete() -> dict:
    aggregate = load(CERT / "phase-4.json")
    exact = {
        "schema": 2,
        "phase": 4,
        "action": "phase-result",
        "status": "PASS",
        "pass_marker": PHASE_MARKER,
        "worktree_clean": True,
        "architecture_sha256": ARCH_SHA,
        "implementation_plan_sha256": PLAN_SHA,
    }
    for key, value in exact.items():
        if aggregate.get(key) != value:
            raise CertificationError(f"phase-4.json {key} mismatch")

    source = aggregate.get("source_commit")
    lock = aggregate.get("toolchain_lock_sha256")
    if not isinstance(source, str) or len(source) != 40:
        raise CertificationError("invalid Phase-4 source identity")
    if not isinstance(lock, str) or len(lock) != 64:
        raise CertificationError("invalid Phase-4 toolchain identity")
    if subprocess.run(
        ["git", "merge-base", "--is-ancestor", source, "HEAD"],
        cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    ).returncode:
        raise CertificationError("certified Phase-4 source is not an ancestor")

    names = [
        f"P4.{number:02d}.{action}.json"
        for number in range(1, 34)
        for action in ("build", "test")
    ] + ["P4.33.result.json"]
    if aggregate.get("required_records") != names:
        raise CertificationError("aggregate required-record ordering mismatch")
    manifest = aggregate.get("record_sha256")
    if not isinstance(manifest, dict) or set(manifest) != set(names):
        raise CertificationError("aggregate record manifest mismatch")

    for number in range(1, 34):
        step = f"P4.{number:02d}"
        for action in ("build", "test"):
            name = f"{step}.{action}.json"
            path = CERT / name
            if not path.is_file():
                raise CertificationError(f"missing durable evidence: {name}")
            record = load(path)
            if (
                record.get("step") != step
                or record.get("action") != action
                or record.get("status") != "PASS"
                or record.get("worktree_clean") is not True
                or record.get("architecture_sha256") != ARCH_SHA
                or record.get("implementation_plan_sha256") != PLAN_SHA
                or record.get("toolchain_lock_sha256") != lock
                or record.get("prerequisites") != expected_prerequisite(step)
            ):
                raise CertificationError(f"{name}: invalid PASS/authority/prerequisite identity")
            record_source = record.get("source_commit")
            if not isinstance(record_source, str) or subprocess.run(
                ["git", "merge-base", "--is-ancestor", record_source, source],
                cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            ).returncode:
                raise CertificationError(f"{name}: source is not historical ancestor")
            if number == 33 and record_source != source:
                raise CertificationError(f"{name}: P4.33 must name aggregate source")
            if manifest.get(name) != sha256(path):
                raise CertificationError(f"{name}: bytes differ from aggregate manifest")

    result = load(CERT / "P4.33.result.json")
    if (
        result.get("step") != "P4.33"
        or result.get("action") != "result"
        or result.get("status") != "PASS"
        or result.get("pass_marker") != P433_MARKER
        or result.get("source_commit") != source
        or result.get("architecture_sha256") != ARCH_SHA
        or result.get("implementation_plan_sha256") != PLAN_SHA
        or result.get("worktree_clean") is not True
        or result.get("prerequisites") != {"P4.32": "PASS"}
    ):
        raise CertificationError("P4.33.result.json exact PASS mismatch")
    if manifest.get("P4.33.result.json") != sha256(CERT / "P4.33.result.json"):
        raise CertificationError("P4.33.result.json differs from aggregate manifest")

    passed = {
        item.get("name")
        for item in aggregate.get("assertions", [])
        if isinstance(item, dict) and item.get("passed") is True
    }
    required_assertions = {
        "p4-33-build-test-result-pass",
        "all-p4-01-through-p4-33-durable-evidence-pass",
        "rev16-rev07-authority-pass",
        "phase4-record-manifest-byte-exact",
        "phase4-acceptance-bullets-pass",
        "phase4-gate-stops-before-phase5",
    }
    if not required_assertions.issubset(passed):
        raise CertificationError("aggregate acceptance assertion missing")
    return aggregate

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-active", action="store_true")
    args = parser.parse_args()
    try:
        activation = activation_commit()
        if activation is None:
            if args.require_active:
                raise CertificationError("Phase-4 aggregate evidence has not been activated")
            print("ZX-UX PHASE 4 EVIDENCE PRE-ACTIVATION PASS")
            return 0

        aggregate = validate_complete()
        source = aggregate["source_commit"]
        parent = git("rev-parse", f"{activation}^")
        if subprocess.run(
            ["git", "merge-base", "--is-ancestor", source, parent],
            cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        ).returncode:
            raise CertificationError("aggregate activation parent does not descend from certified source")
        if git("log", "-1", "--format=%s", activation) != PREFIX + source:
            raise CertificationError("aggregate activation commit message mismatch")
        changed = git("diff-tree", "--no-commit-id", "--name-only", "-r", parent, activation).splitlines()
        if changed != ["v1/dist/certification/phase-4.json"]:
            raise CertificationError("aggregate activation is not a single-artifact evidence-only commit")
        original = subprocess.run(
            ["git", "show", f"{activation}:v1/dist/certification/phase-4.json"],
            cwd=ROOT, capture_output=True,
        ).stdout
        if (CERT / "phase-4.json").read_bytes() != original:
            raise CertificationError("durable Phase-4 aggregate changed after activation")
        print("ZX-UX PHASE 4 DURABLE EVIDENCE PASS")
        return 0
    except Exception as exc:
        print(f"ZX-UX PHASE 4 EVIDENCE FAIL: {exc}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
