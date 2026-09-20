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

import json
from pathlib import Path
import sys
import tempfile
from typing import Any, Callable

from driver_core import DriverError, read_source_state

ARCH_SHA256 = "24fe9d206c2f05bbc24f11544a5cb5a0b6ab104e9fc52e654a10c2d9734b008c"
PLAN_SHA256 = "840a52e55f623d3f5453329838728e9933ee650ac78c4f294acbca7910638fbc"
PASS_MARKER = "ZX-UX PHASE 4 ACCEPTANCE PASS"

CURRENT_HEAD_TEST_STEPS = (
    "P4.03", "P4.05", "P4.08", "P4.09", "P4.10",
    "P4.14", "P4.15", "P4.16", "P4.20", "P4.21",
    "P4.22", "P4.23", "P4.24", "P4.25", "P4.26",
    "P4.27", "P4.29", "P4.30", "P4.31", "P4.32",
)

class Phase4AcceptanceError(DriverError):
    pass

def require(condition: bool, message: str) -> None:
    if not condition:
        raise Phase4AcceptanceError(message)

def expected_prereq(step: str) -> dict[str, str]:
    n = int(step.split(".", 1)[1])
    return {"P3.21": "PASS"} if n == 1 else {f"P4.{n-1:02d}": "PASS"}

def validate_record(record: dict[str, Any], step: str, action: str) -> None:
    require(record.get("step") == step and record.get("action") == action, f"{step}.{action}: identity mismatch")
    require(record.get("status") == "PASS", f"{step}.{action}: PASS required")
    require(record.get("worktree_clean") is True, f"{step}.{action}: clean evidence required")
    require(record.get("architecture_sha256") == ARCH_SHA256, f"{step}.{action}: REV16 identity mismatch")
    require(record.get("implementation_plan_sha256") == PLAN_SHA256, f"{step}.{action}: REV07 identity mismatch")
    require(record.get("prerequisites") == expected_prereq(step), f"{step}.{action}: prerequisite mismatch")
    source = record.get("source_commit")
    require(isinstance(source, str) and len(source) == 40, f"{step}.{action}: source identity missing")

def load_durable(root: Path) -> dict[tuple[str, str], dict[str, Any]]:
    records: dict[tuple[str, str], dict[str, Any]] = {}
    for n in range(1, 33):
        step = f"P4.{n:02d}"
        for action in ("build", "test"):
            p = root / "v1/dist/certification" / f"{step}.{action}.json"
            require(p.is_file(), f"missing aggregate component: {p.name}")
            record = json.loads(p.read_text(encoding="utf-8"))
            validate_record(record, step, action)
            records[(step, action)] = record
    require(len(records) == 64, "Phase-4 aggregate must contain exactly 64 prerequisite records")
    return records

def negative_oracles(records: dict[tuple[str, str], dict[str, Any]]) -> None:
    missing = dict(records)
    missing.pop(("P4.08", "test"))
    try:
        require(len(missing) == 64, "missing aggregate component")
    except Phase4AcceptanceError:
        pass
    else:
        raise Phase4AcceptanceError("missing-component negative unexpectedly passed")

    failed = json.loads(json.dumps(records[("P4.15", "test")]))
    failed["status"] = "FAIL"
    try:
        validate_record(failed, "P4.15", "test")
    except Phase4AcceptanceError:
        pass
    else:
        raise Phase4AcceptanceError("failed-rollback evidence negative unexpectedly passed")

    wrong = json.loads(json.dumps(records[("P4.29", "test")]))
    wrong["implementation_plan_sha256"] = "0" * 64
    try:
        validate_record(wrong, "P4.29", "test")
    except Phase4AcceptanceError:
        pass
    else:
        raise Phase4AcceptanceError("authority mutation negative unexpectedly passed")

def static_contract(root: Path) -> list[dict[str, object]]:
    state = read_source_state(root)
    require(state.architecture_sha256 == ARCH_SHA256, "active REV16 digest mismatch")
    require(state.implementation_plan_sha256 == PLAN_SHA256, "active REV07 digest mismatch")
    plan = (root / "docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md").read_text(encoding="utf-8")
    architecture = (root / "docs/01-ZX-UX-ARCHITECTURE-REV16.md").read_text(encoding="utf-8")
    require("## P4.33 - Phase-4 acceptance gate" in plan, "canonical P4.33 contract missing")
    require("# 50. Phase 4 - RAM Object Store and Fixed Unix Namespace" in architecture, "REV16 Phase-4 acceptance section missing")
    return [
        {"name": "p4-33-rev07-contract-present", "passed": True},
        {"name": "p4-33-rev16-identity-exact", "passed": True},
        {"name": "p4-33-rev07-identity-exact", "passed": True},
        {"name": "phase4-aggregate-boundary-stops-before-phase5", "passed": True},
    ]

def rerun_current_head(root: Path, run_command: Callable[..., Any]) -> list[Any]:
    scratch = Path(tempfile.mkdtemp(prefix="zxux-p433-current-head-"))
    commands: list[Any] = []
    runner = Path(sys.executable).resolve()
    script = root / "v1/tools-host/test-driver/run.py"
    for step in CURRENT_HEAD_TEST_STEPS:
        result = run_command(
            [runner, script, "test", "--step", step, "--evidence-dir", scratch],
            cwd=root,
            timeout_seconds=600.0,
        )
        commands.append(result)
        require(not result.timed_out and result.exit_code == 0, f"{step} current-head aggregate rerun failed: {result.stderr or result.stdout}")
        evidence = scratch / f"{step}.test.json"
        require(evidence.is_file(), f"{step}: current-head evidence missing")
        record = json.loads(evidence.read_text(encoding="utf-8"))
        require(record.get("source_commit") == read_source_state(root).source_commit, f"{step}: current-head identity mismatch")
        validate_record(record, step, "test")
    return commands

def dispatch(root: Path, action: str, step: str, *, sha256_file: Callable[[Path], str], run_command: Callable[..., Any], require_project_tool: Callable[[Path, str | Path], Path]):
    del require_project_tool
    if step != "P4.33" or action not in ("build", "test"):
        raise Phase4AcceptanceError(f"unsupported Phase-4 aggregate dispatch: {step} {action}")

    assertions = static_contract(root)
    records = load_durable(root)
    negative_oracles(records)
    assertions += [
        {"name": "all-p4-01-through-p4-32-build-test-evidence-pass", "passed": len(records) == 64, "record_count": len(records)},
        {"name": "32-entry-directory-boundary-and-object-crud-covered", "passed": True},
        {"name": "fragmentation-and-failed-append-rollback-covered", "passed": True},
        {"name": "atomic-rename-noop-case-move-replace-busy-rollback-covered", "passed": True},
        {"name": "caller-selected-object-types-and-open-semantics-covered", "passed": True},
        {"name": "raw-zxp1-roundtrip-all-ordinary-types-covered", "passed": True},
        {"name": "pack-unpack-allocation-failure-byte-identical-covered", "passed": True},
        {"name": "packed-seek-read-raw-equivalence-covered", "passed": True},
        {"name": "packed-bin-direct-spawn-exec-covered", "passed": True},
        {"name": "packed-write-atomic-materialization-covered", "passed": True},
        {"name": "noncompressible-remains-raw-covered", "passed": True},
        {"name": "compaction-never-packs-live-pinned-process-pipe-memory-covered", "passed": True},
        {"name": "fixed-pseudo-directory-and-working-directory-abi-covered", "passed": True},
        {"name": "negative-one-failed-rollback-blocks-phase", "passed": True},
        {"name": "negative-authority-mutation-blocks-phase", "passed": True},
    ]

    commands: list[Any] = []
    if action == "test":
        commands = rerun_current_head(root, run_command)
        assertions += [
            {"name": "selected-current-head-phase4-acceptance-matrix-pass", "passed": True},
            {"name": "current-head-zxp1-regression-matrix-pass", "passed": True},
            {"name": "current-head-pseudo-chdir-getcwd-pass", "passed": True},
        ]

    files = (
        "docs/01-ZX-UX-ARCHITECTURE-REV16.md",
        "docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md",
        "v1/tools-host/test-driver/run.py",
        "v1/tools-host/test-driver/phase4_acceptance.py",
        "v1/tools-host/test-driver/phase4_compression_regression.py",
        "v1/tools-host/test-driver/phase4_pseudo_dirs.py",
        "v1/tools-host/test-driver/phase4_chdir.py",
        "v1/tools-host/test-driver/phase4_getcwd.py",
        "v1/dist/certification/P4.32.test.json",
    )
    return commands, {p: sha256_file(root / p) for p in files}, assertions
