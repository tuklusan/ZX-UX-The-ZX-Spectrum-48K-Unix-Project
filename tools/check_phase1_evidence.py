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
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
CERT = ROOT / "v1/dist/certification"
ARCH_SHA = "a90d523f62a95e8cba6af0312b596a2d5f6bc1aa2ef92f39bb391509b7c15e1b"
LOCK_PATH = "tools/manifest/toolchain.lock.json"
ARCH_PATH = "docs/01-ZX-UX-ARCHITECTURE-REV12.md"
ACTIVATION_PREFIX = "phase1: activate Phase-1 certification evidence for "
STRICT_P140_ASSERTION = "accepted-im2-interrupt-observed-with-mid-ldir-bc"
P141_AGGREGATE_ASSERTION = "all-p1-01-through-p1-40-build-test-evidence-pass-same-source"
P141_SMOKE_ASSERTION = "minimal-phase1-aggregate-sna-smoke-pass"
REQUIRED_AGGREGATE_ASSERTIONS = {
    "all-p1-build-test-pass",
    "p1-41-result-pass",
    "durable-phase0-prerequisite-pass",
    "strict-p1-40-mid-ldir-proof-pass",
    "p1-41-aggregate-sna-smoke-pass",
    "single-clean-source",
    "exact-toolchain-lock",
    "exact-architecture-digest",
}


class CertificationError(RuntimeError):
    pass


def git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=ROOT, text=True, capture_output=True, check=False
    )
    if result.returncode:
        raise CertificationError(
            f"git {' '.join(args)} failed: {result.stderr.strip()}"
        )
    return result.stdout


def git_bytes(*args: str) -> bytes:
    result = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, check=False)
    if result.returncode:
        message = result.stderr.decode("utf-8", "replace").strip()
        raise CertificationError(f"git {' '.join(args)} failed: {message}")
    return result.stdout


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def names() -> list[str]:
    records = [
        f"P1.{number:02d}.{action}.json"
        for number in range(1, 42)
        for action in ("build", "test")
    ]
    return records + ["P1.41.result.json"]


def validator():
    path = ROOT / "v1/tools-host/test-driver/evidence.py"
    spec = importlib.util.spec_from_file_location("zxux_evidence_validator", path)
    if spec is None or spec.loader is None:
        raise CertificationError("cannot load evidence validator")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load(path: Path):
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise CertificationError(f"malformed evidence {path.name}: {exc}") from exc
    if not isinstance(value, dict):
        raise CertificationError(f"{path.name}: JSON object required")
    return value


def assertion_names(record: dict) -> set[str]:
    return {
        str(item.get("name"))
        for item in record.get("assertions", [])
        if isinstance(item, dict) and item.get("passed") is True
    }


def activation() -> str | None:
    commits = [
        value
        for value in git(
            "log", "--format=%H", "--", "v1/dist/certification/phase-1.json"
        ).splitlines()
        if value
    ]
    return commits[0] if commits else None


def validate_activation(act: str, source: str) -> None:
    parent = git("rev-parse", f"{act}^").strip()
    if parent != source:
        raise CertificationError(
            "latest Phase-1 activation is not a direct child of its certified source"
        )
    subject = git("log", "-1", "--format=%s", act).strip()
    if subject != ACTIVATION_PREFIX + source:
        raise CertificationError("latest Phase-1 activation commit message/source mismatch")
    changed = [
        path
        for path in git(
            "diff-tree", "--no-commit-id", "--name-only", "-r", parent, act
        ).splitlines()
        if path
    ]
    if not changed or any(
        not (path.startswith("v1/dist/certification/") and path.endswith(".json"))
        for path in changed
    ):
        raise CertificationError("latest Phase-1 activation is not evidence-only")


def validate_source_identity(source: str, lock: str) -> None:
    if len(source) != 40 or any(ch not in "0123456789abcdef" for ch in source):
        raise CertificationError("invalid certified source")
    if len(lock) != 64 or any(ch not in "0123456789abcdef" for ch in lock):
        raise CertificationError("invalid toolchain digest")
    descendant = subprocess.run(
        ["git", "merge-base", "--is-ancestor", source, "HEAD"],
        cwd=ROOT,
        capture_output=True,
    )
    if descendant.returncode:
        raise CertificationError("certified source is not an ancestor of HEAD")
    if sha_bytes(git_bytes("show", f"{source}:{LOCK_PATH}")) != lock:
        raise CertificationError("toolchain digest does not match certified source bytes")
    if sha_bytes(git_bytes("show", f"{source}:{ARCH_PATH}")) != ARCH_SHA:
        raise CertificationError("architecture digest does not match certified source bytes")


def require_phase0() -> None:
    result = subprocess.run(
        [sys.executable, "tools/check_phase0_evidence.py", "--require-active"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )
    if result.returncode:
        raise CertificationError(
            "durable Phase-0 prerequisite is not active: "
            + (result.stderr.strip() or result.stdout.strip())
        )


def validate_historical_activation_unchanged(act: str, aggregate: dict) -> None:
    source = aggregate.get("source_commit")
    if not isinstance(source, str):
        raise CertificationError("historical Phase-1 aggregate has invalid source identity")
    if sha(ROOT / ARCH_PATH) != ARCH_SHA:
        raise CertificationError("current architecture bytes do not match the frozen digest")
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", act, "HEAD"],
        cwd=ROOT,
        capture_output=True,
    )
    if ancestor.returncode:
        raise CertificationError("historical Phase-1 activation is not an ancestor of HEAD")
    validate_activation(act, source)
    required = aggregate.get("required_records")
    if not isinstance(required, list) or any(not isinstance(name, str) for name in required):
        raise CertificationError("historical Phase-1 aggregate has invalid required_records")
    for name in ["phase-1.json", *required]:
        path = CERT / name
        if not path.is_file():
            raise CertificationError(f"historical durable evidence missing: {name}")
        if path.read_bytes() != git_bytes(
            "show", f"{act}:v1/dist/certification/{name}"
        ):
            raise CertificationError(f"historical durable evidence changed: {name}")


def expected_prerequisite(step: str) -> dict[str, str]:
    number = int(step.split(".", 1)[1])
    return {"P0.34": "PASS"} if number == 1 else {f"P1.{number - 1:02d}": "PASS"}


def validate_complete():
    require_phase0()
    evidence_validator = validator()
    aggregate_path = CERT / "phase-1.json"
    if not aggregate_path.is_file():
        raise CertificationError("phase-1.json missing after activation")
    aggregate = load(aggregate_path)
    exact = {
        "schema": 2,
        "phase": 1,
        "action": "phase-result",
        "status": "PASS",
        "worktree_clean": True,
        "architecture_sha256": ARCH_SHA,
        "pass_marker": "ZX-UX PHASE 1 CERTIFICATION PASS",
    }
    for key, value in exact.items():
        if aggregate.get(key) != value:
            raise CertificationError(f"phase-1.json {key} mismatch")
    source = aggregate.get("source_commit")
    lock = aggregate.get("toolchain_lock_sha256")
    if not isinstance(source, str) or not isinstance(lock, str):
        raise CertificationError("invalid certified source/toolchain identity")
    validate_source_identity(source, lock)

    required = names()
    manifest = aggregate.get("record_sha256")
    if aggregate.get("required_records") != required:
        raise CertificationError("phase-1 required_records mismatch")
    if not isinstance(manifest, dict) or set(manifest) != set(required):
        raise CertificationError("phase-1 record manifest mismatch")

    records: dict[tuple[str, str], dict] = {}
    for name in required:
        path = CERT / name
        if not path.is_file():
            raise CertificationError(f"missing durable evidence: {name}")
        record = load(path)
        if name.endswith(".result.json"):
            evidence_validator.validate_final_record(record)
            expected_step = "P1.41"
            expected_action = "result"
        else:
            evidence_validator.validate_driver_record(record)
            parts = name.split(".")
            expected_step = ".".join(parts[:2])
            expected_action = parts[2]
        if record.get("step") != expected_step or record.get("action") != expected_action:
            raise CertificationError(f"{name}: evidence identity mismatch")
        if record.get("status") != "PASS" or record.get("worktree_clean") is not True:
            raise CertificationError(f"{name}: non-clean/non-PASS")
        if record.get("source_commit") != source:
            raise CertificationError(f"{name}: wrong source commit")
        if record.get("toolchain_lock_sha256") != lock:
            raise CertificationError(f"{name}: wrong toolchain digest")
        if record.get("architecture_sha256") != ARCH_SHA:
            raise CertificationError(f"{name}: wrong architecture digest")
        if manifest.get(name) != sha(path):
            raise CertificationError(f"{name}: bytes differ from aggregate manifest")
        records[(str(record.get("step")), str(record.get("action")))] = record

    for (step, action), record in records.items():
        expected = {"P1.40": "PASS"} if action == "result" else expected_prerequisite(step)
        if record.get("prerequisites") != expected:
            raise CertificationError(f"{step}.{action}: invalid prerequisite chain")

    if STRICT_P140_ASSERTION not in assertion_names(records[("P1.40", "test")]):
        raise CertificationError("durable P1.40 strict mid-LDIR proof missing")
    p141_names = assertion_names(records[("P1.41", "test")])
    for required_assertion in (P141_AGGREGATE_ASSERTION, P141_SMOKE_ASSERTION):
        if required_assertion not in p141_names:
            raise CertificationError(f"durable P1.41 proof missing: {required_assertion}")
    aggregate_names = assertion_names(aggregate)
    missing_aggregate = sorted(REQUIRED_AGGREGATE_ASSERTIONS - aggregate_names)
    if missing_aggregate:
        raise CertificationError(
            "phase-1 aggregate assertion(s) missing: " + ", ".join(missing_aggregate)
        )
    return aggregate


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-active", action="store_true")
    args = parser.parse_args()
    try:
        act = activation()
        if act is None:
            if args.require_active:
                raise CertificationError("Phase-1 evidence has not been activated")
            print("ZX-UX PHASE 1 EVIDENCE PRE-ACTIVATION PASS")
            return 0

        aggregate_path = CERT / "phase-1.json"
        if aggregate_path.is_file():
            aggregate = load(aggregate_path)
            if aggregate.get("architecture_sha256") != ARCH_SHA:
                validate_historical_activation_unchanged(act, aggregate)
                if args.require_active:
                    raise CertificationError(
                        "Phase-1 evidence has not been activated for the current architecture"
                    )
                print("ZX-UX PHASE 1 EVIDENCE PRE-ACTIVATION PASS")
                return 0

        aggregate = validate_complete()
        source = aggregate.get("source_commit")
        if not isinstance(source, str):
            raise CertificationError("invalid certified source")
        validate_activation(act, source)
        original_bytes = git_bytes(
            "show", f"{act}:v1/dist/certification/phase-1.json"
        )
        if aggregate_path.read_bytes() != original_bytes:
            raise CertificationError(
                "durable Phase-1 aggregate changed after latest activation"
            )
        original = json.loads(original_bytes)
        if aggregate.get("record_sha256") != original.get("record_sha256"):
            raise CertificationError(
                "durable Phase-1 evidence manifest changed after latest activation"
            )
        print("ZX-UX PHASE 1 DURABLE EVIDENCE PASS")
        return 0
    except Exception as exc:
        print(f"ZX-UX PHASE 1 EVIDENCE FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
