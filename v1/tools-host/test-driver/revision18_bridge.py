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
REV17="d12baf0b47a7f8cd2dcd60b82f100ba19f9fddaabad43728a004a07214716bf8"
REV08="97461e9ed12253409b25e6a4a4063cf0ec556a7317f9e4a5938d77edb6a1a14c"
REV18="b13c551f854cf3c01d951212916c6cf787f23617e3b8b74fc7c1867f76ba2156"
REV09="9ff614ba04721961b3461d03638586260b91e9e82eac7687054ead1c9802869f"
PHASE11_TAG="263a203da3d54a398e8ac011284ae4195b1279c0"
PASS_MARKER="ZX-UX REV18 POST-PHASE11 AUTHORITY BRIDGE PASS"
class BridgeError(DriverError): pass
def require(ok:bool,msg:str)->None:
    if not ok: raise BridgeError(msg)
def _json(path:Path)->dict[str,Any]:
    value=json.loads(path.read_text(encoding="utf-8")); require(isinstance(value,dict),f"{path}: JSON object required"); return value
def _git(root:Path,run_command,*args:str)->tuple[Any,str]:
    r=run_command(["git",*args],cwd=root,timeout_seconds=30); require(not r.timed_out and r.exit_code==0,f"git {' '.join(args)} failed"); return r,r.stdout.strip()
def _no_p12(root:Path,run_command)->list[Any]:
    r,paths=_git(root,run_command,"ls-files"); pat=re.compile(r"(?:^|/)(?:P12(?:\.|/)|p12[^/]*(?:qualification|activation|dispatch)|phase-?12)",re.I)
    bad=[p for p in paths.splitlines() if pat.search(p) and not p.startswith(("docs/","scratch/"))]; require(not bad,f"Phase-12 state forbidden during R18 bridge: {bad}"); return [r]
def _historical(root:Path,sha256_file,run_command)->list[Any]:
    commands=[]; require(sha256_file(root/"docs/01-ZX-UX-ARCHITECTURE-REV17.md")==REV17,"REV17 changed"); require(sha256_file(root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV08.md")==REV08,"REV08 changed"); require(sha256_file(root/"docs/01-ZX-UX-ARCHITECTURE-REV18.md")==REV18,"REV18 identity mismatch"); require(sha256_file(root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV09.md")==REV09,"REV09 identity mismatch")
    r,tag=_git(root,run_command,"rev-parse","refs/tags/PHASE-11-COMPLETE"); commands.append(r); require(tag==PHASE11_TAG,"PHASE-11-COMPLETE moved")
    p=_json(root/"v1/dist/certification/P11.48.result.json"); require(p.get("status")=="PASS" and p.get("step")=="P11.48","P11.48 PASS required"); require(p.get("architecture_sha256")==REV17 and p.get("implementation_plan_sha256")==REV08,"P11.48 historical authority changed")
    aggregate=_json(root/"v1/dist/certification/phase-11.json"); require(aggregate.get("status")=="PASS","Phase-11 aggregate PASS required")
    step_re=re.compile(r"^P11\.\d{2}\.(?:build|test|result)\.json$")
    for path in sorted((root/"v1/dist/certification").glob("P11.*.json")):
        if not step_re.fullmatch(path.name): continue
        rec=_json(path); require(rec.get("architecture_sha256")==REV17,f"{path.name}: historical REV17 required"); require(rec.get("implementation_plan_sha256")==REV08,f"{path.name}: historical REV08 required")
    r,changed=_git(root,run_command,"diff","--name-only",PHASE11_TAG,"HEAD","--","v1/dist/certification","v1/dist/media"); commands.append(r)
    r18_evidence={"v1/dist/certification/R18.00.build.json","v1/dist/certification/R18.00.test.json","v1/dist/certification/R18.00.result.json"}
    bad=[p for p in changed.splitlines() if p and not p.startswith("v1/dist/media/P11.pre-release/") and p not in r18_evidence]; require(not bad,f"admitted P0-P11 evidence/media changed after PHASE-11-COMPLETE: {bad}"); return commands
def _authority_contract(root:Path)->None:
    arch=(root/"docs/01-ZX-UX-ARCHITECTURE-REV18.md").read_text(encoding="utf-8"); plan=(root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV09.md").read_text(encoding="utf-8"); exact="ld input.obj -o output -abs"; require(exact in arch and exact in plan,"exact fixed/absolute ld CLI contract missing")
    for f in ("generic development/linker mode","does not add `crt0`","BSS size is zero","relocation table is empty","DAT-typed RAM object","No kernel basename, source identity, object hash"): require(f in arch,f"REV18 fixed-link contract fragment missing: {f}")
    require("does not activate or authorize P12.01" in plan,"REV09 Phase-12 hard stop missing")
def _negative_schema(root:Path)->None:
    good=evidence.valid_fixture("R18.00"); good["architecture_sha256"]=REV18; good["implementation_plan_sha256"]=REV09; good["bridge_source_commit"]=good["source_commit"]; good["prerequisites"]={"P11.48":"PASS"}; evidence.validate_final_record(good)
    for label,field,value in (("wrong-arch","architecture_sha256","0"*64),("wrong-plan","implementation_plan_sha256","f"*64),("wrong-source","bridge_source_commit","f"*40),("wrong-marker","pass_marker","ZX-UX R18.00 CERTIFICATION PASS")):
        bad=json.loads(json.dumps(good)); bad[field]=value
        try: evidence.validate_final_record(bad)
        except evidence.EvidenceError: continue
        raise BridgeError(f"R18 negative unexpectedly passed: {label}")
def dispatch(root:Path,action:str,step:str,*,sha256_file:Callable[[Path],str],run_command:Callable[...,Any],require_project_tool:Callable[[Path,str|Path],Path]):
    require(step=="R18.00" and action in ("build","test"),f"unsupported bridge dispatch {step} {action}"); commands=_historical(root,sha256_file,run_command); commands.extend(_no_p12(root,run_command)); _authority_contract(root)
    assertions=[{"name":"rev18-identity-exact","passed":True},{"name":"rev09-identity-exact","passed":True},{"name":"rev17-rev08-historical-unchanged","passed":True},{"name":"phase11-complete-tag-fixed","passed":True},{"name":"p11-evidence-remains-rev17-rev08","passed":True},{"name":"no-phase12-state","passed":True},{"name":"fixed-absolute-shell-cli-exact","passed":True},{"name":"fixed-absolute-mode-generic-no-specialization","passed":True},{"name":"r18-does-not-activate-phase12","passed":True}]
    if action=="test": _negative_schema(root); assertions.append({"name":"r18-evidence-negative-suite-pass","passed":True})
    names=("docs/01-ZX-UX-ARCHITECTURE-REV17.md","docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV08.md","docs/01-ZX-UX-ARCHITECTURE-REV18.md","docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV09.md","v1/dist/certification/P11.48.result.json","v1/dist/certification/phase-11.json","v1/tools-host/test-driver/revision18_bridge.py","v1/tools-host/test-driver/driver_core.py","v1/tools-host/test-driver/evidence.py","v1/tools-host/test-driver/run.py")
    return commands,{name:sha256_file(root/name) for name in names if (root/name).is_file()},assertions
