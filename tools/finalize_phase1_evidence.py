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
import traceback

ARCH_SHA = "a90d523f62a95e8cba6af0312b596a2d5f6bc1aa2ef92f39bb391509b7c15e1b"
STRICT_P140_ASSERTION = "accepted-im2-interrupt-observed-with-mid-ldir-bc"
P141_AGGREGATE_ASSERTION = "all-p1-01-through-p1-40-build-test-evidence-pass-same-source"
P141_SMOKE_ASSERTION = "minimal-phase1-aggregate-sna-smoke-pass"
P122_VISUAL_ASSERTION = "automated-visual-inspection-canonical-font-atlas-pass"
P122_PNG_ASSERTION = "font-atlas-png-screenshot-retained"
P122_PNG_VISUAL_ASSERTION = "automated-png-raster-inspection-canonical-font-atlas-pass"
P122_CORRESPONDENCE_ASSERTION = "captured-png-corresponds-to-automatically-inspected-scr-frame"
P122_PNG = "P1.22-font-atlas.png"
P122_SCR = "P1.22-font-atlas.scr"
TRACE_PREFIX = "ZX-UX P1 FINALIZER TRACE"


class FinalizeError(RuntimeError):
    pass


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path):
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise FinalizeError(f"{path.name}: object required")
    return value


def write(path: Path, value: dict) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def driver_names() -> list[str]:
    return [
        f"P1.{number:02d}.{action}.json"
        for number in range(1, 42)
        for action in ("build", "test")
    ]


def git_head(root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "--verify", "HEAD"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
        timeout=15,
    )
    if result.returncode != 0:
        raise FinalizeError(f"cannot resolve source HEAD: {result.stderr.strip()}")
    return result.stdout.strip()


def validator(root: Path):
    path = root / "v1/tools-host/test-driver/evidence.py"
    print(f"{TRACE_PREFIX} stage=validator-load path={path}")
    spec = importlib.util.spec_from_file_location("zxux_evidence_validator", path)
    if spec is None or spec.loader is None:
        raise FinalizeError("cannot load evidence validator")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    print(
        f"{TRACE_PREFIX} stage=validator-loaded "
        f"module_file={getattr(module, '__file__', None)!r}"
    )
    return module


def assertion_names(record: dict) -> set[str]:
    return {
        str(item.get("name"))
        for item in record.get("assertions", [])
        if isinstance(item, dict) and item.get("passed") is True
    }


def expected_prerequisite(step: str) -> dict[str, str]:
    number = int(step.split(".", 1)[1])
    return {"P0.34": "PASS"} if number == 1 else {f"P1.{number - 1:02d}": "PASS"}


def require_phase0(root: Path) -> None:
    print(f"{TRACE_PREFIX} stage=phase0-prerequisite start")
    result = subprocess.run(
        [sys.executable, "tools/check_phase0_evidence.py", "--require-active"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )
    print(
        f"{TRACE_PREFIX} stage=phase0-prerequisite rc={result.returncode} "
        f"stdout={result.stdout.strip()!r} stderr={result.stderr.strip()!r}"
    )
    if result.returncode != 0:
        raise FinalizeError(
            "durable Phase-0 prerequisite is not active: "
            + (result.stderr.strip() or result.stdout.strip())
        )


def result_record(source: dict) -> dict:
    return {
        "schema": 2,
        "step": "P1.41",
        "action": "result",
        "status": "PASS",
        "pass_marker": "ZX-UX P1.41 CERTIFICATION PASS",
        "source_commit": source["source_commit"],
        "toolchain_lock_sha256": source["toolchain_lock_sha256"],
        "architecture_sha256": source["architecture_sha256"],
        "worktree_clean": True,
        "prerequisites": {"P1.40": "PASS"},
        "commands": [],
        "hashes": dict(source.get("hashes", {})),
        "assertions": [
            {"name": "build-record-pass", "passed": True},
            {"name": "test-record-pass", "passed": True},
            {"name": "same-clean-source", "passed": True},
            {"name": "phase1-aggregate-contract-pass", "passed": True},
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--evidence-dir", required=True)
    args = parser.parse_args()
    try:
        root = Path(args.root).resolve()
        evidence = Path(args.evidence_dir).resolve()
        head = git_head(root)
        print(
            f"{TRACE_PREFIX} stage=start head={head} root={root} "
            f"evidence={evidence} executable={sys.executable}"
        )
        try:
            evidence.relative_to(root)
        except ValueError:
            pass
        else:
            raise FinalizeError("evidence staging must be outside source worktree")

        require_phase0(root)
        evidence_validator = validator(root)
        records: dict[str, dict] = {}
        sources: set[object] = set()
        locks: set[object] = set()
        archs: set[object] = set()
        for index, name in enumerate(driver_names()):
            path = evidence / name
            if not path.is_file():
                raise FinalizeError(f"missing driver evidence: {name}")
            record = load(path)
            if index == 0:
                print(
                    f"{TRACE_PREFIX} stage=first-record file={name} "
                    f"record_source={record.get('source_commit')!r} head={head!r} "
                    f"record_step={record.get('step')!r} record_action={record.get('action')!r}"
                )
            try:
                evidence_validator.validate_driver_record(record)
            except Exception as exc:
                raise FinalizeError(
                    f"{name}: validator failure "
                    f"class={type(exc).__module__}.{type(exc).__name__}: {exc}"
                ) from exc
            parts = name.split(".")
            expected_step = ".".join(parts[:2])
            expected_action = parts[2]
            if record.get("step") != expected_step or record.get("action") != expected_action:
                raise FinalizeError(f"{name}: evidence identity mismatch")
            if record.get("status") != "PASS" or record.get("worktree_clean") is not True:
                raise FinalizeError(f"{name}: not clean PASS")
            step = str(record.get("step"))
            if record.get("prerequisites") != expected_prerequisite(step):
                raise FinalizeError(f"{name}: exact prerequisite chain mismatch")
            records[name] = record
            sources.add(record.get("source_commit"))
            locks.add(record.get("toolchain_lock_sha256"))
            archs.add(record.get("architecture_sha256"))

        print(
            f"{TRACE_PREFIX} stage=identity-sets head={head!r} "
            f"sources={sorted(map(repr, sources))!r} "
            f"locks={sorted(map(repr, locks))!r} archs={sorted(map(repr, archs))!r}"
        )
        if len(sources) != 1 or len(locks) != 1 or archs != {ARCH_SHA}:
            raise FinalizeError(
                "evidence does not name one exact source/toolchain/architecture state"
            )
        source = next(iter(sources))
        if source != head:
            raise FinalizeError(
                f"staged evidence source does not match checked-out HEAD: "
                f"evidence={source!r} head={head!r}"
            )

        p122 = records["P1.22.test.json"]
        p122_names = assertion_names(p122)
        for required in (P122_VISUAL_ASSERTION, P122_PNG_VISUAL_ASSERTION, P122_PNG_ASSERTION, P122_CORRESPONDENCE_ASSERTION):
            if required not in p122_names:
                raise FinalizeError(f"P1.22 visual-proof assertion missing: {required}")
        p122_by_name = {
            str(item.get("name")): item
            for item in p122.get("assertions", [])
            if isinstance(item, dict) and item.get("passed") is True
        }
        for required_name, artifact_name in (
            (P122_VISUAL_ASSERTION, P122_SCR),
            (P122_PNG_ASSERTION, P122_PNG),
        ):
            item = p122_by_name[required_name]
            if item.get("artifact") != artifact_name:
                raise FinalizeError(f"P1.22 visual artifact identity mismatch: {required_name}")
            expected_sha = item.get("sha256")
            path = evidence / artifact_name
            if not path.is_file():
                raise FinalizeError(f"P1.22 visual artifact missing: {artifact_name}")
            if not isinstance(expected_sha, str) or sha(path) != expected_sha:
                raise FinalizeError(f"P1.22 visual artifact SHA-256 mismatch: {artifact_name}")
        visual_frame = p122_by_name[P122_VISUAL_ASSERTION].get("frame_id")
        png_visual = p122_by_name[P122_PNG_VISUAL_ASSERTION]
        png_visual_frame = png_visual.get("frame_id")
        png_frame = p122_by_name[P122_PNG_ASSERTION].get("frame_id")
        correspondence_frame = p122_by_name[P122_CORRESPONDENCE_ASSERTION].get("frame_id")
        if not isinstance(visual_frame, str) or visual_frame != png_visual_frame or visual_frame != png_frame or visual_frame != correspondence_frame:
            raise FinalizeError("P1.22 SCR/PNG captured-frame identity mismatch")
        if png_visual.get("width") != 320 or png_visual.get("height") != 240:
            raise FinalizeError("P1.22 automated PNG inspection dimensions mismatch")
        if not isinstance(png_visual.get("foreground_pixels"), int) or png_visual["foreground_pixels"] <= 0:
            raise FinalizeError("P1.22 automated PNG inspection foreground proof missing")
        scr_bytes = (evidence / P122_SCR).read_bytes()
        png_bytes = (evidence / P122_PNG).read_bytes()
        if len(scr_bytes) != 6912:
            raise FinalizeError("P1.22 retained SCR screenshot is not exactly 6912 bytes")
        if not png_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
            raise FinalizeError("P1.22 retained PNG screenshot has invalid signature")

        p140_names = assertion_names(records["P1.40.test.json"])
        if STRICT_P140_ASSERTION not in p140_names:
            raise FinalizeError("P1.40 strict mid-LDIR interrupt proof missing")
        p141_names = assertion_names(records["P1.41.test.json"])
        for required in (P141_AGGREGATE_ASSERTION, P141_SMOKE_ASSERTION):
            if required not in p141_names:
                raise FinalizeError(f"P1.41 acceptance assertion missing: {required}")

        boundary_name = "P1.41.result.json"
        boundary = result_record(records["P1.41.test.json"])
        evidence_validator.validate_final_record(boundary)
        write(evidence / boundary_name, boundary)

        required = driver_names() + [boundary_name]
        aggregate = {
            "schema": 2,
            "phase": 1,
            "action": "phase-result",
            "status": "PASS",
            "pass_marker": "ZX-UX PHASE 1 CERTIFICATION PASS",
            "source_commit": next(iter(sources)),
            "toolchain_lock_sha256": next(iter(locks)),
            "architecture_sha256": ARCH_SHA,
            "worktree_clean": True,
            "required_records": required,
            "record_sha256": {name: sha(evidence / name) for name in required},
            "assertions": [
                {"name": "all-p1-build-test-pass", "passed": True},
                {"name": "p1-41-result-pass", "passed": True},
                {"name": "durable-phase0-prerequisite-pass", "passed": True},
                {"name": "p1-22-captured-font-screenshot-pass", "passed": True},
                {"name": "p1-22-automated-visual-inspection-pass", "passed": True},
                {"name": "p1-22-automated-png-raster-inspection-pass", "passed": True},
                {"name": "strict-p1-40-mid-ldir-proof-pass", "passed": True},
                {"name": "p1-41-aggregate-sna-smoke-pass", "passed": True},
                {"name": "single-clean-source", "passed": True},
                {"name": "exact-toolchain-lock", "passed": True},
                {"name": "exact-architecture-digest", "passed": True},
            ],
        }
        write(evidence / "phase-1.json", aggregate)
        print("ZX-UX PHASE 1 EVIDENCE FINALIZATION PASS")
        return 0
    except Exception as exc:
        traceback.print_exc(file=sys.stderr)
        print(f"ZX-UX PHASE 1 EVIDENCE FINALIZATION FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
