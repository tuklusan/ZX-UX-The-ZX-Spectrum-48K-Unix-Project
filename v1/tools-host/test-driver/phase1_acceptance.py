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

import ast
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Callable

from driver_core import DriverError, SourceState, read_source_state
import evidence
import phase1_gate
import phase1_probe

ARCH_SHA256 = "a90d523f62a95e8cba6af0312b596a2d5f6bc1aa2ef92f39bb391509b7c15e1b"
STRICT_P140_ASSERTION = "accepted-im2-interrupt-observed-with-mid-ldir-bc"

REQUIRED_TEST_ASSERTIONS: dict[str, tuple[str, ...]] = {
    "P1.13": (
        "sys-ticks-snapshot-is-coherent-and-four-bytes",
        "im2-never-mutates-cursor-bitmap-coordinate-wrap-or-depth",
        "two-delayed-transitions-coalesce-to-even-parity",
    ),
    "P1.15": ("break-isr-is-minimal-nonblocking-producer-only",),
    "P1.20": (
        "no-persistent-phantom-coordinate",
        "tty32-bottom-right-scroll-is-deferred",
    ),
    "P1.22": ("golden-boundary-cells-render-with-neighbor-preservation",),
    "P1.23": ("golden-24-row-scroll-byte-exact",),
    "P1.24": (
        "runtime-nested-hide-reconcile-once",
        "runtime-odd-even-parity-coalesces",
    ),
    "P1.25": (
        "runtime-border-sound-interleave-preserved",
        "runtime-rom-altreg-gate-balanced",
    ),
    "P1.26": ("runtime-cold-epoch-and-independent-ticks",),
    "P1.27": ("runtime-boot-get-and-invalid-eagain",),
    "P1.29": (
        "syscall-restores-canonical-iy",
        "rom-wrapper-restores-canonical-iy",
    ),
    "P1.30": (
        "fast-path-primary-state-preserved",
        "early-clear-negative-detects-corruption",
    ),
    "P1.31": (
        "break-raw-matrix-positive",
        "non-break-raw-matrix-negative",
    ),
    "P1.32": ("stale-pixel-restore-negative",),
    "P1.33": (
        "release-watermark-at-or-above-fb40",
        "architectural-64-byte-margin-untouched",
        "guard-corruption-panics-kstack",
    ),
    "P1.35": ("visible-cursor-putchar-mutation-is-reversible-and-balanced",),
    "P1.36": (
        "contiguous-split-and-putchar-streams-are-byte-identical-tty32",
        "contiguous-split-and-putchar-streams-are-byte-identical-tty64",
    ),
    "P1.37": ("due-cursor-parity-is-consumed-only-at-outer-end-runtime",),
    "P1.38": (
        "getpos-returns-real-max-coordinate-tty32-with-and-without-pending",
        "getpos-returns-real-max-coordinate-tty64-with-and-without-pending",
    ),
    "P1.39": ("setpos-valid-max-coordinates-and-clears-pending-runtime",),
    "P1.40": (STRICT_P140_ASSERTION,),
}


class Phase1AcceptanceError(DriverError):
    """A fail-closed Phase-1 aggregate acceptance failure."""


def _required_keys() -> tuple[tuple[str, str], ...]:
    return tuple(
        (f"P1.{number:02d}", action)
        for number in range(1, 41)
        for action in ("build", "test")
    )


def _expected_prerequisites(step: str) -> dict[str, str]:
    number = int(step.split(".", 1)[1])
    return {"P0.34": "PASS"} if number == 1 else {f"P1.{number - 1:02d}": "PASS"}


def _assertion_names(record: dict[str, Any]) -> set[str]:
    return {
        str(item.get("name"))
        for item in record.get("assertions", [])
        if isinstance(item, dict) and item.get("passed") is True
    }


def _validate_record(
    record: dict[str, Any],
    *,
    step: str,
    action: str,
    state: SourceState,
) -> None:
    try:
        evidence.validate_driver_record(record)
    except (evidence.EvidenceError, ValueError, TypeError) as exc:
        raise Phase1AcceptanceError(f"{step}.{action}: invalid evidence: {exc}") from exc
    if record.get("step") != step or record.get("action") != action:
        raise Phase1AcceptanceError(f"{step}.{action}: evidence identity mismatch")
    if record.get("status") != "PASS" or record.get("worktree_clean") is not True:
        raise Phase1AcceptanceError(f"{step}.{action}: PASS from a clean worktree required")
    if record.get("source_commit") != state.source_commit:
        raise Phase1AcceptanceError(f"{step}.{action}: source commit mismatch")
    if record.get("toolchain_lock_sha256") != state.toolchain_lock_sha256:
        raise Phase1AcceptanceError(f"{step}.{action}: toolchain contract mismatch")
    if record.get("architecture_sha256") != state.architecture_sha256:
        raise Phase1AcceptanceError(f"{step}.{action}: architecture identity mismatch")
    expected = _expected_prerequisites(step)
    if record.get("prerequisites") != expected:
        raise Phase1AcceptanceError(
            f"{step}.{action}: prerequisite chain mismatch: expected {expected!r}"
        )
    if action == "test":
        required = set(REQUIRED_TEST_ASSERTIONS.get(step, ()))
        missing = sorted(required - _assertion_names(record))
        if missing:
            raise Phase1AcceptanceError(
                f"{step}.test: required acceptance assertion(s) missing: {', '.join(missing)}"
            )


def _validate_bundle(
    records: dict[tuple[str, str], dict[str, Any]],
    *,
    state: SourceState,
) -> None:
    required = set(_required_keys())
    present = set(records)
    missing = sorted(required - present)
    extra = sorted(present - required)
    if missing:
        names = ", ".join(f"{step}.{action}" for step, action in missing)
        raise Phase1AcceptanceError(f"missing Phase-1 prerequisite evidence: {names}")
    if extra:
        names = ", ".join(f"{step}.{action}" for step, action in extra)
        raise Phase1AcceptanceError(f"unexpected aggregate evidence keys: {names}")
    for step, action in _required_keys():
        _validate_record(records[(step, action)], step=step, action=action, state=state)


def _evidence_dir(state: SourceState) -> Path:
    configured = os.environ.get("ZXUX_EVIDENCE_DIR")
    if configured:
        return Path(configured).expanduser().resolve()
    return (Path(tempfile.gettempdir()) / "zxux-certification" / state.source_commit).resolve()


def _load_prerequisites(state: SourceState) -> dict[tuple[str, str], dict[str, Any]]:
    directory = _evidence_dir(state)
    records: dict[tuple[str, str], dict[str, Any]] = {}
    for step, action in _required_keys():
        path = directory / f"{step}.{action}.json"
        if not path.is_file():
            raise Phase1AcceptanceError(f"missing Phase-1 prerequisite evidence: {path.name}")
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise Phase1AcceptanceError(f"malformed Phase-1 prerequisite evidence {path.name}: {exc}") from exc
        if not isinstance(record, dict):
            raise Phase1AcceptanceError(f"{path.name}: JSON object required")
        records[(step, action)] = record
    _validate_bundle(records, state=state)
    return records


def _fixture_record(step: str, action: str, state: SourceState) -> dict[str, Any]:
    assertions = [{"name": "fixture", "passed": True}]
    if action == "test":
        assertions.extend(
            {"name": name, "passed": True}
            for name in REQUIRED_TEST_ASSERTIONS.get(step, ())
        )
    return {
        "schema": 2,
        "step": step,
        "action": action,
        "status": "PASS",
        "source_commit": state.source_commit,
        "toolchain_lock_sha256": state.toolchain_lock_sha256,
        "architecture_sha256": state.architecture_sha256,
        "worktree_clean": True,
        "prerequisites": _expected_prerequisites(step),
        "commands": [],
        "hashes": {"v1/tools-host/test-driver/phase1_acceptance.py": "0" * 64},
        "assertions": assertions,
    }


def _fixture_bundle(state: SourceState) -> dict[tuple[str, str], dict[str, Any]]:
    return {
        (step, action): _fixture_record(step, action, state)
        for step, action in _required_keys()
    }


def _must_reject(
    records: dict[tuple[str, str], dict[str, Any]],
    *,
    state: SourceState,
    label: str,
) -> None:
    try:
        _validate_bundle(records, state=state)
    except Phase1AcceptanceError:
        return
    raise Phase1AcceptanceError(f"negative oracle did not reject {label}")


def _negative_oracles(state: SourceState) -> None:
    missing = _fixture_bundle(state)
    missing.pop(("P1.17", "test"))
    _must_reject(missing, state=state, label="missing prerequisite evidence")

    failed = _fixture_bundle(state)
    failed[("P1.24", "build")]["status"] = "FAIL"
    _must_reject(failed, state=state, label="failed prerequisite")

    wrong_chain = _fixture_bundle(state)
    wrong_chain[("P1.31", "test")]["prerequisites"] = {"P1.29": "PASS"}
    _must_reject(wrong_chain, state=state, label="broken prerequisite chain")

    weakened = _fixture_bundle(state)
    weakened[("P1.36", "test")]["assertions"] = [{"name": "fixture", "passed": True}]
    _must_reject(weakened, state=state, label="missing split-write identity proof")

    no_strict = _fixture_bundle(state)
    no_strict[("P1.40", "test")]["assertions"] = [{"name": "fixture", "passed": True}]
    _must_reject(no_strict, state=state, label="missing strict P1.40 interrupt proof")


def _static_acceptance(root: Path, state: SourceState) -> list[dict[str, object]]:
    run_text = (root / "v1/tools-host/test-driver/run.py").read_text(encoding="utf-8")
    plan_text = (root / "docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV03.md").read_text(encoding="utf-8")
    this_text = (root / "v1/tools-host/test-driver/phase1_acceptance.py").read_text(encoding="utf-8")
    phase1_workflow_text = (root / ".github/workflows/phase1-certification.yml").read_text(encoding="utf-8")
    quality_workflow_text = (root / ".github/workflows/quality-and-ci.yml").read_text(encoding="utf-8")

    if state.architecture_sha256 != ARCH_SHA256:
        raise Phase1AcceptanceError("Phase-1 acceptance architecture digest mismatch")
    if "## P1.41 - Phase-1 acceptance gate" not in plan_text:
        raise Phase1AcceptanceError("canonical P1.41 implementation-plan contract missing")
    if "import phase1_acceptance" not in run_text or 'if step == "P1.41":' not in run_text:
        raise Phase1AcceptanceError("P1.41 is not explicitly routed to the aggregate acceptance owner")
    if "return phase1_acceptance.dispatch" not in run_text:
        raise Phase1AcceptanceError("P1.41 aggregate dispatch route missing")
    if "P1.40" not in phase1_gate.CERTIFIED_STEPS:
        raise Phase1AcceptanceError("P1.40 must be certified before P1.41 can run")
    if "P1.41" not in (*phase1_gate.CERTIFIED_STEPS, *phase1_gate.CANDIDATE_STEPS):
        raise Phase1AcceptanceError("P1.41 must be registered with the Phase-1 gate")
    tree = ast.parse(this_text)
    imported_modules = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in (node.names if isinstance(node, ast.Import) else [ast.alias(name=node.module or "")])
    }
    if any(name.startswith(("phase2", "phase3", "phase4", "phase5", "phase6", "phase7", "phase8", "phase9", "phase10", "phase11", "phase12")) for name in imported_modules):
        raise Phase1AcceptanceError("P1.41 acceptance owner must not import later-phase semantics")
    if len(_required_keys()) != 80:
        raise Phase1AcceptanceError("P1.41 aggregate must require exactly 80 P1.01-P1.40 records")
    finalize_marker = "tools/finalize_phase1_evidence.py --root"
    gate_marker = "v1/tools-host/test-driver/phase1_gate.py"
    if finalize_marker not in phase1_workflow_text:
        raise Phase1AcceptanceError("Phase-1 workflow does not finalize aggregate evidence")
    if phase1_workflow_text.index(finalize_marker) <= phase1_workflow_text.index(gate_marker):
        raise Phase1AcceptanceError("Phase-1 aggregate finalization must run after the registered gate")
    quality_markers = (
        "phase1-evidence:",
        "tools/check_phase1_evidence.py",
        "tools/test_phase1_evidence_negative.py",
    )
    if any(marker not in quality_workflow_text for marker in quality_markers):
        raise Phase1AcceptanceError("Quality workflow does not enforce durable Phase-1 evidence")
    project_ci_text = quality_workflow_text.split("  project-ci:", 1)[-1]
    needs_line = next(
        (line for line in project_ci_text.splitlines() if line.strip().startswith("needs:")),
        "",
    )
    if "phase1-evidence" not in needs_line:
        raise Phase1AcceptanceError("Quality project-ci does not depend on durable Phase-1 evidence")
    _negative_oracles(state)
    return [
        {"name": "phase1-acceptance-plan-contract-present", "passed": True},
        {"name": "phase1-acceptance-architecture-identity-exact", "passed": True},
        {"name": "p1-40-certified-before-p1-41", "passed": True},
        {"name": "p1-41-explicitly-routed-to-aggregate-owner", "passed": True},
        {"name": "aggregate-requires-exactly-80-prerequisite-records", "passed": True},
        {"name": "aggregate-requires-source-toolchain-architecture-identity", "passed": True},
        {"name": "aggregate-requires-exact-prerequisite-chain", "passed": True},
        {"name": "aggregate-requires-critical-phase1-acceptance-assertions", "passed": True},
        {"name": "aggregate-requires-strict-p1-40-mid-ldir-proof", "passed": True},
        {"name": "phase1-finalizer-wired-after-gate", "passed": True},
        {"name": "phase1-durable-evidence-validator-wired-into-quality", "passed": True},
        {"name": "negative-missing-prerequisite-evidence-rejected", "passed": True},
        {"name": "negative-failed-prerequisite-rejected", "passed": True},
        {"name": "negative-broken-prerequisite-chain-rejected", "passed": True},
        {"name": "negative-missing-split-write-proof-rejected", "passed": True},
        {"name": "negative-missing-strict-p140-proof-rejected", "passed": True},
        {"name": "no-later-phase-semantic-dependency", "passed": True},
    ]


def dispatch(
    root: Path,
    action: str,
    step: str,
    *,
    sha256_file: Callable[[Path], str],
    run_command: Callable[..., Any],
    require_project_tool: Callable[[Path, str | Path], Path],
):
    del run_command, require_project_tool
    if step != "P1.41":
        raise Phase1AcceptanceError(f"phase1 acceptance owner cannot handle {step}")
    if action not in ("build", "test"):
        raise Phase1AcceptanceError(f"unsupported P1.41 action: {action}")

    state = read_source_state(root)
    assertions = _static_acceptance(root, state)
    files = (
        "docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV03.md",
        "v1/docs/test-plan.md",
        "v1/tools-host/test-driver/evidence.py",
        "v1/tools-host/test-driver/run.py",
        "v1/tools-host/test-driver/phase1_gate.py",
        "v1/tools-host/test-driver/phase1_probe.py",
        "v1/tools-host/test-driver/phase1_primitives_strict.py",
        "v1/tools-host/test-driver/phase1_acceptance.py",
        "tools/finalize_phase1_evidence.py",
        "tools/check_phase1_evidence.py",
        "tools/test_phase1_evidence_negative.py",
        ".github/workflows/phase1-certification.yml",
        ".github/workflows/quality-and-ci.yml",
    )
    hashes = {name: sha256_file(root / name) for name in files}
    commands: list[Any] = []

    if action == "test":
        records = _load_prerequisites(state)
        assertions.extend((
            {
                "name": "all-p1-01-through-p1-40-build-test-evidence-pass-same-source",
                "passed": len(records) == 80,
                "record_count": len(records),
            },
            {
                "name": "complete-p1-40-canonical-primitive-suite-present",
                "passed": STRICT_P140_ASSERTION in _assertion_names(records[("P1.40", "test")]),
            },
        ))
        phase1_probe.run(root)
        assertions.append({
            "name": "minimal-phase1-aggregate-sna-smoke-pass",
            "passed": True,
        })

    return commands, hashes, assertions
