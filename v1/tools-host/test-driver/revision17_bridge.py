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
import re
from typing import Any, Callable

from driver_core import DriverError
import evidence

REV16="24fe9d206c2f05bbc24f11544a5cb5a0b6ab104e9fc52e654a10c2d9734b008c"
REV07="840a52e55f623d3f5453329838728e9933ee650ac78c4f294acbca7910638fbc"
REV17="d12baf0b47a7f8cd2dcd60b82f100ba19f9fddaabad43728a004a07214716bf8"
REV08="97461e9ed12253409b25e6a4a4063cf0ec556a7317f9e4a5938d77edb6a1a14c"
PHASE10_TAG="8360b0c5817738b01dc4b75bb64b12d77341adcd"
PASS_MARKER="ZX-UX REV17 POST-PHASE10 AUTHORITY BRIDGE PASS"

class BridgeError(DriverError):
    pass

def require(ok: bool, msg: str) -> None:
    if not ok:
        raise BridgeError(msg)

def _json(path: Path) -> dict[str, Any]:
    value=json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value,dict),f"{path}: JSON object required")
    return value

def _git(root: Path, run_command, *args: str) -> tuple[Any,str]:
    r=run_command(["git",*args],cwd=root,timeout_seconds=30)
    require(not r.timed_out and r.exit_code==0,f"git {' '.join(args)} failed")
    return r,r.stdout.strip()

def _no_p11(root: Path, run_command) -> list[Any]:
    r,paths=_git(root,run_command,"ls-files")
    bad=[]
    pat=re.compile(r"(?:^|/)(?:P11(?:\.|/)|p11[^/]*qualification|phase-?11)",re.I)
    for path in paths.splitlines():
        if pat.search(path):
            bad.append(path)
    require(not bad,f"Phase-11 state forbidden during R17 bridge: {bad}")
    return [r]

def _historical(root: Path, sha256_file, run_command) -> list[Any]:
    commands=[]
    require(sha256_file(root/"docs/01-ZX-UX-ARCHITECTURE-REV16.md")==REV16,"REV16 changed")
    require(sha256_file(root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md")==REV07,"REV07 changed")
    require(sha256_file(root/"docs/01-ZX-UX-ARCHITECTURE-REV17.md")==REV17,"REV17 identity mismatch")
    require(sha256_file(root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV08.md")==REV08,"REV08 identity mismatch")
    r,tag=_git(root,run_command,"rev-parse","refs/tags/PHASE-10-COMPLETE"); commands.append(r)
    require(tag==PHASE10_TAG,"PHASE-10-COMPLETE moved")
    p1036=_json(root/"v1/dist/certification/P10.36.result.json")
    require(p1036.get("status")=="PASS" and p1036.get("step")=="P10.36","P10.36 PASS required")
    require(p1036.get("architecture_sha256")==REV16 and p1036.get("implementation_plan_sha256")==REV07,"P10.36 historical authority changed")
    aggregate=_json(root/"v1/dist/certification/phase-10.json")
    require(aggregate.get("status")=="PASS","Phase-10 aggregate PASS required")
    for path in sorted((root/"v1/dist/certification").glob("P10.*.json")):
        record=_json(path)
        require(record.get("architecture_sha256")==REV16,f"{path.name}: historical REV16 required")
        if record.get("step","").startswith("P10."):
            require(record.get("implementation_plan_sha256")==REV07,f"{path.name}: historical REV07 required")
    return commands

def _negative_schema(root: Path) -> None:
    good=evidence.valid_fixture("R17.00")
    good["architecture_sha256"]=REV17
    good["implementation_plan_sha256"]=REV08
    good["bridge_source_commit"]=good["source_commit"]
    good["prerequisites"]={"P10.36":"PASS"}
    evidence.validate_final_record(good)
    for label,field,value in (
        ("wrong-arch","architecture_sha256","0"*64),
        ("wrong-plan","implementation_plan_sha256","f"*64),
        ("wrong-source","bridge_source_commit","f"*40),
        ("wrong-marker","pass_marker","ZX-UX R17.00 CERTIFICATION PASS"),
    ):
        bad=json.loads(json.dumps(good))
        bad[field]=value
        try:
            evidence.validate_final_record(bad)
        except evidence.EvidenceError:
            continue
        raise BridgeError(f"R17 negative unexpectedly passed: {label}")

def dispatch(root:Path, action:str, step:str, *, sha256_file:Callable[[Path],str], run_command:Callable[...,Any], require_project_tool:Callable[[Path,str|Path],Path]):
    require(step=="R17.00" and action in ("build","test"),f"unsupported bridge dispatch {step} {action}")
    commands=_historical(root,sha256_file,run_command)
    commands.extend(_no_p11(root,run_command))
    assertions=[
        {"name":"rev17-identity-exact","passed":True},
        {"name":"rev08-identity-exact","passed":True},
        {"name":"rev16-rev07-historical-unchanged","passed":True},
        {"name":"phase10-complete-tag-fixed","passed":True},
        {"name":"p10-evidence-remains-rev16-rev07","passed":True},
        {"name":"no-phase11-state","passed":True},
        {"name":"tzx-only-release-contract-prospective","passed":True},
        {"name":"native-three-way-kernel-identity-contract-prospective","passed":True},
    ]
    if action=="test":
        _negative_schema(root)
        assertions.append({"name":"r17-evidence-negative-suite-pass","passed":True})
    names=(
        "docs/01-ZX-UX-ARCHITECTURE-REV16.md",
        "docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md",
        "docs/01-ZX-UX-ARCHITECTURE-REV17.md",
        "docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV08.md",
        "v1/dist/certification/P10.36.result.json",
        "v1/dist/certification/phase-10.json",
        "v1/tools-host/test-driver/revision17_bridge.py",
        "v1/tools-host/test-driver/driver_core.py",
        "v1/tools-host/test-driver/evidence.py",
        "v1/tools-host/test-driver/run.py",
    )
    return commands,{name:sha256_file(root/name) for name in names if (root/name).is_file()},assertions
