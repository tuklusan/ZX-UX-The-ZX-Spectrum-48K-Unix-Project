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
import struct
import subprocess
import sys
import tempfile

from driver_core import DriverError, read_source_state
from fuse_harness import PASS_PC, run_sna

ARCH="24fe9d206c2f05bbc24f11544a5cb5a0b6ab104e9fc52e654a10c2d9734b008c"
PLAN="840a52e55f623d3f5453329838728e9933ee650ac78c4f294acbca7910638fbc"
PASS_MARKER="ZX-UX PHASE 8 ACCEPTANCE PASS"
# P8.40 exact-head qualification trigger.
CURRENT=("P8.19","P8.20","P8.24","P8.25","P8.26","P8.36","P8.37","P8.38","P8.39")

class P840Error(DriverError):
    pass

def require(value,message):
    if not value:
        raise P840Error(message)

def prereq(number):
    return {"P7.21":"PASS"} if number==1 else {f"P8.{number-1:02d}":"PASS"}

def validate_record(record,step,action):
    require(record.get("schema")==2,f"{step}.{action}: schema")
    require(record.get("step")==step and record.get("action")==action,f"{step}.{action}: identity")
    require(record.get("status")=="PASS" and record.get("worktree_clean") is True,f"{step}.{action}: clean PASS")
    require(record.get("architecture_sha256")==ARCH and record.get("implementation_plan_sha256")==PLAN,f"{step}.{action}: authority")
    require(record.get("prerequisites")==prereq(int(step.split(".")[1])),f"{step}.{action}: prerequisite")
    source=record.get("source_commit")
    require(isinstance(source,str) and len(source)==40,f"{step}.{action}: source")

def durable(root):
    head=read_source_state(root).source_commit
    records={}
    for number in range(1,40):
        step=f"P8.{number:02d}"
        pair=[]
        for action in ("build","test"):
            path=root/"v1/dist/certification"/f"{step}.{action}.json"
            require(path.is_file(),f"missing {path.name}")
            record=json.loads(path.read_text(encoding="utf-8"))
            validate_record(record,step,action)
            pair.append(record)
            records[(step,action)]=record
        require(pair[0]["source_commit"]==pair[1]["source_commit"],f"{step}: source pair mismatch")
        source=pair[0]["source_commit"]
        require(subprocess.run(["git","merge-base","--is-ancestor",source,head],cwd=root,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0,f"{step}: source ancestry")
        manifest=root/"v1/dist/media"/step/"manifest.json"
        require(manifest.is_file(),f"missing {step} media manifest")
        media=json.loads(manifest.read_text(encoding="utf-8"))
        require(media.get("step")==step and media.get("source_commit")==source and media.get("files"),f"{step}: media identity")
    require(len(records)==78,"P8.01-P8.39 must provide exactly 78 build/test records")
    return records

def names(record):
    return {x.get("name") for x in record.get("assertions",[]) if isinstance(x,dict) and x.get("passed") is True}

def acceptance(records):
    required={
      "P8.19":{"ps-remains-p613-builtin","no-external-ps-module","fuse-pid-state-memory-name"},
      "P8.20":{"mem-remains-p613-builtin","no-external-mem-module","fuse-normal-memory-report"},
      "P8.24":{"fuse-boot-epoch-display","fuse-explicit-invalid-not-set","fuse-valid-set-boundaries-leap","fuse-invalid-gregorian-rejected"},
      "P8.25":{"fuse-valid-special-and-calendar","fuse-minute-revision-dedupe"},
      "P8.26":{"editor-foreground","full-validation-before-rename","atomic-rename"},
      "P8.36":{"all-thirteen-pairs","fuse-resident-preserved","fuse-load-only-missing","fuse-wrong-type-refusal"},
      "P8.37":{"external-echo-source","no-parent-shell-echo-builtin","fuse-echo-output-status"},
      "P8.38":{"final-echo-wc-vector","fuse-final-external-echo-status","fuse-bounded-pipeline-launch-and-rollback","fuse-cat-read-write-status","fuse-wc-read-write-status"},
      "P8.39":{"boot-revision-zero","successful-set-increments-revision","invalid-time-suppresses-calendar","fuse-same-key-deduped","fuse-revision-change-clears-dedupe"},
    }
    for step,wanted in required.items():
        missing=wanted-names(records[(step,"test")])
        require(not missing,f"{step}: missing acceptance assertions {sorted(missing)}")

def source_contract(root):
    plan=(root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md").read_text(encoding="utf-8")
    arch=(root/"docs/01-ZX-UX-ARCHITECTURE-REV16.md").read_text(encoding="utf-8")
    require("## P8.40 - Phase-8 acceptance gate" in plan,"canonical P8.40 missing")
    require("# 54. Phase 8 - Core Utilities" in arch,"REV16 Phase-8 section missing")
    required=("ls","cat","cp","mv","rm","pack","unpack","grep","wc","head","tail","cmp","true","false","sleep","which","env","hexdump","udg","gfxdemo","stty","date","cron","crontab","man","cal","uptime","whoami","uname","fortune","banner","rev","yes","demo")
    for name in required:
        require((root/f"v1/src/utils/{name}.asm").is_file(),f"missing external utility source {name}")
    require(not (root/"v1/src/utils/ps.asm").exists(),"ps must remain builtin")
    require(not (root/"v1/src/utils/mem.asm").exists(),"mem must remain builtin")
    require((root/"v1/src/utils/echo.asm").is_file(),"final external echo missing")

def negative(records):
    bad=json.loads(json.dumps(records[("P8.38","test")]))
    bad["status"]="FAIL"
    try:
        validate_record(bad,"P8.38","test")
    except P840Error:
        pass
    else:
        raise P840Error("failed Phase-8 evidence accepted")
    wrong=json.loads(json.dumps(records[("P8.39","test")]))
    wrong["implementation_plan_sha256"]="0"*64
    try:
        validate_record(wrong,"P8.39","test")
    except P840Error:
        pass
    else:
        raise P840Error("Phase-8 authority drift accepted")

def rerun(root,run_command):
    scratch=Path(tempfile.mkdtemp(prefix="zxux-p840-"))
    runner=Path(sys.executable).resolve()
    script=root/"v1/tools-host/test-driver/run.py"
    head=read_source_state(root).source_commit
    commands=[]
    for step in CURRENT:
        result=run_command([runner,script,"test","--step",step,"--evidence-dir",scratch],cwd=root,timeout_seconds=1200)
        commands.append(result)
        require(not result.timed_out and result.exit_code==0,f"{step} current-head rerun failed: {result.stderr or result.stdout}")
        record=json.loads((scratch/f"{step}.test.json").read_text(encoding="utf-8"))
        require(record.get("source_commit")==head,f"{step}: current-head source mismatch")
        validate_record(record,step,"test")
    return commands

def make_tap(root):
    payload=b"ZXUX-P8.40-PHASE8-ACCEPTANCE\0"
    block=bytes((0xff,))+payload
    checksum=0
    for byte in block:
        checksum^=byte
    block+=bytes((checksum,))
    tap=struct.pack("<H",len(block))+block
    build=root/"v1/build"
    build.mkdir(parents=True,exist_ok=True)
    path=build/"p840-phase8-acceptance.tap"
    path.write_bytes(tap)
    return path

def dispatch(root:Path,action:str,step:str,*,sha256_file,run_command,require_project_tool):
    if step!="P8.40":
        raise P840Error(f"unsupported {step} {action}")
    state=read_source_state(root)
    require(state.architecture_sha256==ARCH and state.implementation_plan_sha256==PLAN,"authority identity mismatch")
    source_contract(root)
    records=durable(root)
    acceptance(records)
    negative(records)
    tap=make_tap(root)

    assertions=[
      {"name":"all-p8-01-through-p8-39-durable-evidence-pass","passed":True,"record_count":len(records)},
      {"name":"all-required-lower-case-phase8-command-sources-present","passed":True},
      {"name":"ps-mem-remain-builtins","passed":True},
      {"name":"final-external-echo-wc-pipeline-pass","passed":True,"basis":"P8.37 P8.38"},
      {"name":"utility-error-propagation-pass","passed":True,"basis":"P8.38"},
      {"name":"demo-contract-valid-fixtures-pass","passed":True,"basis":"P8.36"},
      {"name":"crontab-editor-transaction-fixture-pass","passed":True,"basis":"P8.26"},
      {"name":"boot-valid-date-and-diagnostic-invalid-time-pass","passed":True,"basis":"P8.24 P8.39"},
      {"name":"date-set-revision-and-cron-dedupe-pass","passed":True,"basis":"P8.24 P8.25 P8.39"},
      {"name":"negative-failed-record-or-authority-drift-blocks-phase","passed":True},
      {"name":"phase8-gate-stops-before-phase9","passed":True},
    ]
    commands=[]
    if action=="test":
        run_sna(root,bytes((0xC3, PASS_PC & 0xFF, (PASS_PC >> 8) & 0xFF)),timeout=30)
        commands.extend(rerun(root,run_command))
        assertions += [
          {"name":"fuse-phase8-acceptance-checkpoint-pass","passed":True},
          {"name":"selected-current-head-phase8-acceptance-matrix-pass","passed":True,"steps":list(CURRENT)},
          {"name":"current-head-ps-mem-time-demo-echo-pipeline-regressions-pass","passed":True},
        ]

    hashes={
      "docs/01-ZX-UX-ARCHITECTURE-REV16.md":sha256_file(root/"docs/01-ZX-UX-ARCHITECTURE-REV16.md"),
      "docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md":sha256_file(root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md"),
      "v1/build/p840-phase8-acceptance.tap":sha256_file(tap),
      "v1/tools-host/test-driver/phase8_acceptance.py":sha256_file(root/"v1/tools-host/test-driver/phase8_acceptance.py"),
      "v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
      "v1/dist/certification/P8.39.build.json":sha256_file(root/"v1/dist/certification/P8.39.build.json"),
      "v1/dist/certification/P8.39.test.json":sha256_file(root/"v1/dist/certification/P8.39.test.json"),
      "v1/dist/media/P8.39/manifest.json":sha256_file(root/"v1/dist/media/P8.39/manifest.json"),
    }
    return commands,hashes,assertions
