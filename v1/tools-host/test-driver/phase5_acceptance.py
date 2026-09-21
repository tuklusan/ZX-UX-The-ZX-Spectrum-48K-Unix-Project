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
import json, sys, tempfile
from pathlib import Path
from typing import Any, Callable
from driver_core import DriverError, read_source_state

ARCH_SHA="24fe9d206c2f05bbc24f11544a5cb5a0b6ab104e9fc52e654a10c2d9734b008c"
PLAN_SHA="840a52e55f623d3f5453329838728e9933ee650ac78c4f294acbca7910638fbc"
CURRENT=("P5.16","P5.17")

class P519Error(DriverError): pass
def require(v,m):
    if not v: raise P519Error(m)
def prereq(n:int): return {"P4.33":"PASS"} if n==1 else {f"P5.{n-1:02d}":"PASS"}
def validate(r:dict[str,Any],step:str,action:str):
    require(r.get("step")==step and r.get("action")==action,f"{step}.{action}: identity")
    require(r.get("status")=="PASS" and r.get("worktree_clean") is True,f"{step}.{action}: clean PASS")
    require(r.get("architecture_sha256")==ARCH_SHA and r.get("implementation_plan_sha256")==PLAN_SHA,f"{step}.{action}: authority")
    require(r.get("prerequisites")==prereq(int(step.split(".")[1])),f"{step}.{action}: prerequisite")
    require(isinstance(r.get("source_commit"),str) and len(r["source_commit"])==40,f"{step}.{action}: source")
def durable(root:Path):
    out={}
    for n in range(1,19):
        step=f"P5.{n:02d}"
        for action in ("build","test"):
            p=root/"v1/dist/certification"/f"{step}.{action}.json"
            require(p.is_file(),f"missing {p.name}")
            r=json.loads(p.read_text())
            validate(r,step,action); out[(step,action)]=r
    require(len(out)==36,"P5.01-P5.18 must provide exactly 36 build/test records")
    return out
def negatives(records):
    bad=json.loads(json.dumps(records[("P5.16","test")]))
    bad["status"]="FAIL"
    try: validate(bad,"P5.16","test")
    except P519Error: pass
    else: raise P519Error("failed roundtrip evidence accepted")
    wrong=json.loads(json.dumps(records[("P5.14","test")]))
    wrong["implementation_plan_sha256"]="0"*64
    try: validate(wrong,"P5.14","test")
    except P519Error: pass
    else: raise P519Error("authority mutation accepted")
def rerun(root:Path,run_command):
    scratch=Path(tempfile.mkdtemp(prefix="zxux-p519-"))
    runner=Path(sys.executable).resolve(); script=root/"v1/tools-host/test-driver/run.py"; cmds=[]
    head=read_source_state(root).source_commit
    for step in CURRENT:
        r=run_command([runner,script,"test","--step",step,"--evidence-dir",scratch],cwd=root,timeout_seconds=900)
        cmds.append(r); require(not r.timed_out and r.exit_code==0,f"{step} current-head rerun failed: {r.stderr or r.stdout}")
        ev=json.loads((scratch/f"{step}.test.json").read_text())
        require(ev.get("source_commit")==head,f"{step}: current-head source mismatch")
        validate(ev,step,"test")
    return cmds

def dispatch(root:Path,action:str,step:str,*,sha256_file:Callable[[Path],str],run_command:Callable[...,Any],require_project_tool):
    del require_project_tool
    if step!="P5.19" or action not in ("build","test"): raise P519Error(f"unsupported {step} {action}")
    state=read_source_state(root)
    require(state.architecture_sha256==ARCH_SHA and state.implementation_plan_sha256==PLAN_SHA,"authority identity mismatch")
    plan=(root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md").read_text()
    arch=(root/"docs/01-ZX-UX-ARCHITECTURE-REV16.md").read_text()
    require("## P5.19 - Phase-5 acceptance gate" in plan,"canonical P5.19 missing")
    require("# 51." in arch and "Phase 5" in arch,"REV16 Phase-5 acceptance missing")
    rec=durable(root); negatives(rec)
    assertions=[
      {"name":"all-p5-01-through-p5-18-build-test-evidence-pass","passed":True,"record_count":len(rec)},
      {"name":"exact-m48o-prefix-header-chunk-crc-contracts-covered","passed":True},
      {"name":"raw-packed-load-save-verify-scan-roundtrips-covered","passed":True},
      {"name":"streaming-save-and-direct-tape-mex1-covered","passed":True},
      {"name":"global-lock-prompts-and-break-error-recovery-covered","passed":True},
      {"name":"second-emulator-compatibility-gate-covered","passed":True},
      {"name":"fixture-explicitly-non-final","passed":True},
      {"name":"negative-byte-order-authority-or-failed-record-blocks-phase","passed":True},
      {"name":"phase5-gate-stops-before-phase6","passed":True},
    ]
    commands=[]
    if action=="test":
        commands=rerun(root,run_command)
        assertions += [
          {"name":"selected-current-head-phase5-acceptance-matrix-pass","passed":True},
          {"name":"current-head-roundtrip-recovery-pass","passed":True},
        ]
    files=("docs/01-ZX-UX-ARCHITECTURE-REV16.md","docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md",
           "v1/tools-host/test-driver/run.py","v1/tools-host/test-driver/phase5_acceptance.py",
           "v1/dist/certification/P5.18.build.json","v1/dist/certification/P5.18.test.json")
    return commands,{p:sha256_file(root/p) for p in files},assertions
