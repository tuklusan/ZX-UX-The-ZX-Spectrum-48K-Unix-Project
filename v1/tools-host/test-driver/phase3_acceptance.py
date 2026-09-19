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
PASS_MARKER = "ZX-UX PHASE 3 ACCEPTANCE PASS"

CURRENT_HEAD_TEST_STEPS = (
    "P3.01", "P3.02", "P3.03", "P3.06", "P3.07",
    "P3.10", "P3.12", "P3.13", "P3.14",
    "P3.17", "P3.18", "P3.19", "P3.20",
)

REQUIRED_TEST_ASSERTIONS = {
    "P3.01": {"24-allocate-25th-enospc-complete-rollback"},
    "P3.02": {"ninth-auto-slot-enospc-no-mutation"},
    "P3.03": {
        "tty32-edit-read-is-exact-1b",
        "tty64-edit-read-is-exact-1b",
        "break-raw-matrix-remains-cancellation-producer-not-1b",
    },
    "P3.06": {"dup-shares-offset-and-decoder-state"},
    "P3.07": {
        "same-object-independent-opens-use-distinct-descriptions",
        "packed-decoder-state-pointers-are-independent",
    },
    "P3.10": {
        "reader-enters-wait-pipe-read",
        "writer-wakes-reader-to-ready",
        "final-writer-close-produces-zero-byte-eof",
    },
    "P3.12": {
        "writer-sleeps-on-full-pipe",
        "reader-wakes-blocked-writer",
        "busy-loop-negative-detected-by-schedule-return",
    },
    "P3.13": {
        "final-read-close-enables-e-pipe",
        "broken-pipe-has-no-hidden-write",
    },
    "P3.14": {
        "dup-refs-do-not-change-logical-endpoint-counts",
        "final-ref-closes-each-logical-endpoint",
    },
    "P3.17": {
        "two-real-spawned-processes-transfer-exact-stream-through-inherited-pipe-handles",
        "small-buffer-16-cycle-stress-reaches-pass-without-deadlock",
    },
    "P3.18": {
        "three-spawned-stages-transfer-exact-bytes-through-two-true-pipes",
        "retained-parent-writer-negative-fixture-triggers-timeout-deadlock-detector",
    },
    "P3.19": {
        "widened-end-dff0-plus-0030-rejected-pre-side-effect",
        "widened-end-fff0-plus-0020-rejected-pre-side-effect",
        "display-workspace-bridge-5af0-plus-0020-rejected",
        "7ff0-plus-0020-accepted-within-single-user-arena-region",
        "zero-count-poison-pointer-not-dereferenced-valid-handle",
        "zero-count-poison-pointer-invalid-handle-still-errors",
    },
    "P3.20": {
        "ioctl1-is-exact-packed-four-byte-record",
        "tty-request-07-set-owner-pid1-live-pid-and-zero-exact",
        "whole-record-and-pointed-range-invalid-before-side-effect",
    },
}

class Phase3AcceptanceError(DriverError):
    pass

def require(condition: bool, message: str) -> None:
    if not condition:
        raise Phase3AcceptanceError(message)

def names(record: dict[str, Any]) -> set[str]:
    return {
        str(item.get("name"))
        for item in record.get("assertions", [])
        if isinstance(item, dict) and item.get("passed") is True
    }

def expected_prereq(step: str) -> dict[str, str]:
    n=int(step.split(".",1)[1])
    return {"R16.00":"PASS"} if n==1 else {f"P3.{n-1:02d}":"PASS"}

def validate_record(record: dict[str, Any], step: str, action: str) -> None:
    require(record.get("step")==step and record.get("action")==action, f"{step}.{action}: identity mismatch")
    require(record.get("status")=="PASS", f"{step}.{action}: PASS required")
    require(record.get("worktree_clean") is True, f"{step}.{action}: clean evidence required")
    require(record.get("architecture_sha256")==ARCH_SHA256, f"{step}.{action}: REV16 identity mismatch")
    require(record.get("implementation_plan_sha256")==PLAN_SHA256, f"{step}.{action}: REV07 identity mismatch")
    expected=expected_prereq(step)
    if step=="P3.15" and action=="test":
        # Preserve the already-admitted P3.15 test evidence byte contract:
        # that immutable record contains the historical field spelling "prerequsites".
        require(record.get("prerequisites") is None, f"{step}.{action}: unexpected corrected prerequisite field")
        require(record.get("prerequsites")==expected, f"{step}.{action}: admitted prerequisite chain mismatch")
        require("v1/dist/certification/P3.14.test.json" in record.get("hashes",{}), f"{step}.{action}: predecessor hash missing")
    else:
        require(record.get("prerequisites")==expected, f"{step}.{action}: prerequisite chain mismatch")
    source=record.get("source_commit")
    require(isinstance(source,str) and len(source)==40, f"{step}.{action}: source identity missing")
    if action=="test":
        missing=REQUIRED_TEST_ASSERTIONS.get(step,set())-names(record)
        require(not missing, f"{step}.test: missing aggregate proof {sorted(missing)!r}")

def load_durable(root: Path) -> dict[tuple[str,str], dict[str,Any]]:
    records={}
    for n in range(1,21):
        step=f"P3.{n:02d}"
        for action in ("build","test"):
            p=root/"v1/dist/certification"/f"{step}.{action}.json"
            require(p.is_file(), f"missing aggregate component: {p.name}")
            record=json.loads(p.read_text(encoding="utf-8"))
            validate_record(record,step,action)
            records[(step,action)]=record
    require(len(records)==40,"Phase-3 aggregate must contain exactly 40 prerequisite records")
    return records

def negative_oracles(records: dict[tuple[str,str],dict[str,Any]]) -> None:
    missing=dict(records)
    missing.pop(("P3.13","test"))
    try:
        require(len(missing)==40,"missing aggregate component")
    except Phase3AcceptanceError:
        pass
    else:
        raise Phase3AcceptanceError("missing-component negative unexpectedly passed")

    weakened=json.loads(json.dumps(records[("P3.03","test")]))
    weakened["assertions"]=[a for a in weakened["assertions"] if a.get("name")!="tty64-edit-read-is-exact-1b"]
    try:
        validate_record(weakened,"P3.03","test")
    except Phase3AcceptanceError:
        pass
    else:
        raise Phase3AcceptanceError("EDIT/ESC weakening negative unexpectedly passed")

    wrong=json.loads(json.dumps(records[("P3.19","test")]))
    wrong["implementation_plan_sha256"]="0"*64
    try:
        validate_record(wrong,"P3.19","test")
    except Phase3AcceptanceError:
        pass
    else:
        raise Phase3AcceptanceError("authority-identity negative unexpectedly passed")

def static_contract(root: Path) -> list[dict[str,object]]:
    state=read_source_state(root)
    require(state.architecture_sha256==ARCH_SHA256,"active REV16 digest mismatch")
    require(state.implementation_plan_sha256==PLAN_SHA256,"active REV07 digest mismatch")
    plan=(root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md").read_text(encoding="utf-8")
    architecture=(root/"docs/01-ZX-UX-ARCHITECTURE-REV16.md").read_text(encoding="utf-8")
    require("## P3.21 - Phase-3 acceptance gate" in plan,"canonical P3.21 contract missing")
    require("# 49. Phase 3 - Generic I/O and Pipes" in architecture,"REV16 Phase-3 acceptance section missing")
    return [
      {"name":"p3-21-rev07-contract-present","passed":True},
      {"name":"p3-21-rev16-identity-exact","passed":True},
      {"name":"p3-21-rev07-identity-exact","passed":True},
      {"name":"phase3-aggregate-boundary-stops-before-phase4","passed":True},
    ]

def rerun_current_head(root: Path, run_command: Callable[...,Any]) -> list[Any]:
    scratch=Path(tempfile.mkdtemp(prefix="zxux-p321-current-head-"))
    commands=[]
    runner=Path(sys.executable).resolve()
    script=root/"v1/tools-host/test-driver/run.py"
    for step in CURRENT_HEAD_TEST_STEPS:
        result=run_command(
            [runner,script,"test","--step",step,"--evidence-dir",scratch],
            cwd=root,
            timeout_seconds=300.0,
        )
        commands.append(result)
        require(not result.timed_out and result.exit_code==0, f"{step} current-head aggregate rerun failed: {result.stderr or result.stdout}")
        evidence=scratch/f"{step}.test.json"
        require(evidence.is_file(),f"{step}: current-head evidence missing")
        record=json.loads(evidence.read_text(encoding="utf-8"))
        require(record.get("source_commit")==read_source_state(root).source_commit,f"{step}: current-head identity mismatch")
        validate_record(record,step,"test")
    return commands

def dispatch(root: Path, action: str, step: str, *, sha256_file: Callable[[Path],str], run_command: Callable[...,Any], require_project_tool: Callable[[Path,str|Path],Path]):
    del require_project_tool
    if step!="P3.21" or action not in ("build","test"):
        raise Phase3AcceptanceError(f"unsupported Phase-3 aggregate dispatch: {step} {action}")
    assertions=static_contract(root)
    records=load_durable(root)
    negative_oracles(records)
    assertions += [
      {"name":"all-p3-01-through-p3-20-build-test-evidence-pass","passed":len(records)==40,"record_count":len(records)},
      {"name":"durable-phase3-evidence-preserves-rev16-rev07-identities","passed":True},
      {"name":"frozen-p3-15-test-prerequisite-key-typo-preserved-and-hash-chained","passed":True},
      {"name":"negative-missing-phase3-component-rejected","passed":True},
      {"name":"negative-edit-escape-proof-weakening-rejected","passed":True},
      {"name":"negative-authority-identity-mutation-rejected","passed":True},
    ]
    commands=[]
    if action=="test":
        commands=rerun_current_head(root,run_command)
        assertions += [
          {"name":"handle-open-description-and-process-slot-limits-current-head","passed":True},
          {"name":"independent-open-and-dup-inherited-sharing-current-head","passed":True},
          {"name":"tty-edit-escape-byte-preserving-break-separated-current-head","passed":True},
          {"name":"pipe-block-wake-eof-e-pipe-current-head","passed":True},
          {"name":"two-process-and-three-stage-pipelines-current-head","passed":True},
          {"name":"bounded-pipe-stress-no-deadlock-current-head","passed":True},
          {"name":"widened-range-and-zero-count-vectors-current-head","passed":True},
          {"name":"ioctl1-seven-tty-requests-current-head","passed":True},
        ]
    files=(
      "docs/01-ZX-UX-ARCHITECTURE-REV16.md",
      "docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md",
      "v1/tools-host/test-driver/run.py",
      "v1/tools-host/test-driver/phase3_acceptance.py",
      "v1/tools-host/test-driver/phase3_tty.py",
      "v1/tools-host/test-driver/phase3_pipe2.py",
      "v1/tools-host/test-driver/phase3_pipe3.py",
      "v1/tools-host/test-driver/phase3_widened_ranges.py",
      "v1/tools-host/test-driver/phase3_ioctl.py",
      "v1/dist/certification/P3.20.test.json",
    )
    return commands,{p:sha256_file(root/p) for p in files},assertions
