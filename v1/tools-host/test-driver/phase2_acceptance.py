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
import sys
from typing import Any, Callable

from driver_core import DriverError, read_source_state

ARCH_SHA256 = "a90d523f62a95e8cba6af0312b596a2d5f6bc1aa2ef92f39bb391509b7c15e1b"

class Phase2AcceptanceError(DriverError):
    pass

def _dir() -> Path:
    value = os.environ.get("ZXUX_EVIDENCE_DIR")
    if not value:
        raise Phase2AcceptanceError("P2.24 requires ZXUX_EVIDENCE_DIR")
    return Path(value).expanduser().resolve()

def _load_all(state) -> dict[tuple[str,str], dict[str,Any]]:
    out={}
    d=_dir()
    for n in range(1,24):
        step=f"P2.{n:02d}"
        for action in ("build","test"):
            p=d/f"{step}.{action}.json"
            if not p.is_file():
                raise Phase2AcceptanceError(f"missing aggregate component: {p.name}")
            r=json.loads(p.read_text(encoding="utf-8"))
            if r.get("step")!=step or r.get("action")!=action or r.get("status")!="PASS":
                raise Phase2AcceptanceError(f"{p.name}: clean PASS required")
            if r.get("worktree_clean") is not True or r.get("source_commit")!=state.source_commit:
                raise Phase2AcceptanceError(f"{p.name}: exact clean source required")
            if r.get("toolchain_lock_sha256")!=state.toolchain_lock_sha256 or r.get("architecture_sha256")!=state.architecture_sha256:
                raise Phase2AcceptanceError(f"{p.name}: authority/toolchain identity mismatch")
            out[(step,action)]=r
    return out

def _names(r: dict[str,Any]) -> set[str]:
    return {str(x.get("name")) for x in r.get("assertions",[]) if isinstance(x,dict) and x.get("passed") is True}

def _validate_components(records):
    required={
      ("P2.02","test"): {"inspector-golden-bytes-exact","inspector-golden-decode-exact"},
      ("P2.03","test"): {"relocator-two-pass-atomic-order","reject-unsorted-atomic","reject-end-overrun-atomic"},
      ("P2.08","test"): {"dirty-pre-dispatch-iy-is-canonicalized-to-5c3a-before-first-instruction","initial-saved-sp-frame-is-exact-ix-hl-de-bc-af-pc-and-consumes-twelve-bytes","minimum-fast-stack-retains-separate-fixed-64-byte-bootstrap-reserve","context-constructor-does-not-use-iy-or-alternate-register-bank"},
      ("P2.22","test"): {"384-real-spawn-exit-reap-cycles-return-byte-exact-allocator-open-accounting","deliberately-skipped-free-is-detected-by-same-accounting-oracle"},
      ("P2.23","test"): {"same-mex1-executes-through-real-spawn-at-two-distinct-bases","relocated-words-and-observable-result-are-exact-at-both-bases"},
    }
    for key,names in required.items():
        missing=names-_names(records[key])
        if missing:
            raise Phase2AcceptanceError(f"{key[0]}.{key[1]} missing acceptance proof: {sorted(missing)!r}")
    for step in ("P2.09","P2.12","P2.14","P2.15","P2.16","P2.17","P2.19"):
        if records[(step,"test")].get("status")!="PASS":
            raise Phase2AcceptanceError(f"{step} process lifecycle evidence failed")

def _must_reject_missing(records, state):
    copy=dict(records); copy.pop(("P2.22","test"))
    try:
        if len(copy)!=46:
            raise Phase2AcceptanceError("missing aggregate component")
        _validate_components(copy)
    except Phase2AcceptanceError:
        return
    raise Phase2AcceptanceError("negative missing-component oracle unexpectedly passed")

def _static(root: Path, state) -> list[dict[str,object]]:
    if state.architecture_sha256 != ARCH_SHA256:
        raise Phase2AcceptanceError("REV12 identity mismatch")
    plan=(root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV03.md").read_text(encoding="utf-8")
    run=(root/"v1/tools-host/test-driver/run.py").read_text(encoding="utf-8")
    gate=(root/"v1/tools-host/test-driver/phase2_gate.py").read_text(encoding="utf-8")
    this=(root/"v1/tools-host/test-driver/phase2_acceptance.py").read_text(encoding="utf-8")
    if "## P2.24 - Phase-2 acceptance gate" not in plan:
        raise Phase2AcceptanceError("canonical P2.24 contract missing")
    if "import phase2_acceptance" not in run or 'if step == "P2.24":' not in run:
        raise Phase2AcceptanceError("P2.24 deterministic-driver route missing")
    if '"P2.23"' not in gate or '"P2.24"' in gate.split("def _diagnostic_path",1)[0]:
        raise Phase2AcceptanceError("registered aggregate gate boundary mismatch")
    tree=ast.parse(this)
    imported={a.name for node in ast.walk(tree) if isinstance(node,ast.Import) for a in node.names}
    if any(x.startswith("phase3") for x in imported):
        raise Phase2AcceptanceError("P2.24 must not depend on Phase 3")
    return [
      {"name":"p2-24-rev03-contract-present","passed":True},
      {"name":"p2-24-rev12-identity-exact","passed":True},
      {"name":"p2-24-explicit-driver-route","passed":True},
      {"name":"phase2-registered-gate-stops-at-p2-23","passed":True},
      {"name":"no-phase3-semantic-dependency","passed":True},
    ]

def dispatch(root: Path, action: str, step: str, *, sha256_file: Callable[[Path],str], run_command: Callable[...,Any], require_project_tool: Callable[[Path,str|Path],Path]):
    del require_project_tool
    if step!="P2.24" or action not in ("build","test"):
        raise Phase2AcceptanceError(f"unsupported acceptance dispatch: {step} {action}")
    state=read_source_state(root)
    assertions=_static(root,state)
    commands=[]
    if action=="test":
        result=run_command([Path(sys.executable).resolve(), root/"v1/tools-host/test-driver/phase2_gate.py"],cwd=root,timeout_seconds=2700.0)
        commands.append(result)
        if result.timed_out or result.exit_code!=0:
            raise Phase2AcceptanceError(f"registered Phase-2 aggregate gate failed: {result.stderr or result.stdout}")
        records=_load_all(state)
        _validate_components(records)
        _must_reject_missing(records,state)
        assertions.extend([
          {"name":"phase2-current-source-registered-gate-pass","passed":True,"record_count":len(records)},
          {"name":"mex1-inspector-evidence-pass","passed":True},
          {"name":"relocation-atomicity-evidence-pass","passed":True},
          {"name":"spawn-exec-wait-zombie-evidence-pass","passed":True},
          {"name":"context-iy-altreg-evidence-pass","passed":True},
          {"name":"process-memory-bootstrap-placement-evidence-pass","passed":True},
          {"name":"leak-evidence-pass","passed":True},
          {"name":"two-base-relocatable-evidence-pass","passed":True},
          {"name":"negative-missing-required-component-rejected","passed":True},
        ])
    files=("docs/01-ZX-UX-ARCHITECTURE-REV12.md","docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV03.md","v1/tools-host/test-driver/run.py","v1/tools-host/test-driver/phase2_gate.py","v1/tools-host/test-driver/phase2_acceptance.py")
    return commands,{p:sha256_file(root/p) for p in files},assertions
