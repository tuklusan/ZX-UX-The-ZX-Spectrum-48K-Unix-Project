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
import phase7_gfx_golden

ARCH="24fe9d206c2f05bbc24f11544a5cb5a0b6ab104e9fc52e654a10c2d9734b008c"
PLAN="840a52e55f623d3f5453329838728e9933ee650ac78c4f294acbca7910638fbc"
PASS_MARKER="ZX-UX PHASE 7 ACCEPTANCE PASS"
CURRENT=("P7.02","P7.08","P7.10","P7.11","P7.12","P7.16","P7.18","P7.20")

class P721Error(DriverError):
    pass

def require(value,message):
    if not value:
        raise P721Error(message)

def prereq(number):
    return {"P6.30":"PASS"} if number==1 else {f"P7.{number-1:02d}":"PASS"}

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
    for number in range(1,21):
        step=f"P7.{number:02d}"
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
    require(len(records)==40,"P7.01-P7.20 must provide exactly 40 build/test records")
    return records

def names(record):
    return {x.get("name") for x in record.get("assertions",[]) if isinstance(x,dict) and x.get("passed") is True}

def acceptance(records):
    required={
      "P7.02":{"display-address-domain-exact","fuse-all-6144-bitmap-byte-addresses-match-host-oracle"},
      "P7.08":{"fuse-all-border-colors-preserve-mic-beeper-and-other-shadow-bits"},
      "P7.09":{"fuse-beep-1-0-completes-synchronously","fuse-beep-half-9-completes-synchronously","fuse-beep-quarter-minus12-completes-synchronously","fuse-beep-half-halfpitch-completes-synchronously"},
      "P7.10":{"fuse-every-allowed-grammar-family-returns-controlled-five-byte-result","fuse-forbidden-token-families-reject-safely"},
      "P7.11":{"fuse-every-category-first-last-past-end-layout-exact","fuse-classes-a-b-c-and-contract-flags-exact","fuse-rom-builtin-only-exposes-frozen-safe-categories"},
      "P7.12":{"fuse-all-graphics-and-attribute-builtins-reach-exact-kernel-selectors","fuse-line-circle-record-pointers-and-coordinate-registers-exact","fuse-pipeline-background-and-bad-arity-fail-before-syscall"},
      "P7.16":{"fuse-raw-packed-load-identical-live-bytes","fuse-invalid-payload-zero-live-mutation"},
      "P7.18":{"fuse-c48-regcall-hl-de-float-pointers-reach-sys-beep-exact","fuse-c48-success-maps-to-int-zero","fuse-c48-kernel-errno-maps-to-positive-int"},
      "P7.19":{"fuse-integrated-gfx-udg-sound-golden-passes","fuse-screen-sum-and-exact-touched-bytes-match","fuse-attribute-cells-and-udg-bank-bytes-exact","fuse-rom-udg-pointer-and-iy-exact","fuse-guard-canaries-survive-approved-writes","fuse-negative-guard-corruption-detected"},
      "P7.20":{"fuse-basic-compatible-beep-vectors-pass","fuse-parenthesized-expression-comma-depth-pass","fuse-malformed-and-unsafe-operands-fail-before-rom-stack-mutation","fuse-pipeline-background-fail-before-parse-or-side-effect","fuse-lowercase-only-lookup-never-enters-external-resolution","fuse-builtin-redirection-restores-exact-stdio"},
    }
    for step,wanted in required.items():
        missing=wanted-names(records[(step,"test")])
        require(not missing,f"{step}: missing acceptance assertions {sorted(missing)}")

def negative(records):
    bad=json.loads(json.dumps(records[("P7.20","test")]))
    bad["status"]="FAIL"
    try:
        validate_record(bad,"P7.20","test")
    except P721Error:
        pass
    else:
        raise P721Error("failed Phase-7 evidence accepted")
    wrong=json.loads(json.dumps(records[("P7.19","test")]))
    wrong["architecture_sha256"]="0"*64
    try:
        validate_record(wrong,"P7.19","test")
    except P721Error:
        pass
    else:
        raise P721Error("ULA/IY/golden authority drift accepted")

def rerun(root,run_command):
    scratch=Path(tempfile.mkdtemp(prefix="zxux-p721-"))
    runner=Path(sys.executable).resolve()
    script=root/"v1/tools-host/test-driver/run.py"
    head=read_source_state(root).source_commit
    commands=[]
    for step in CURRENT:
        result=run_command([runner,script,"test","--step",step,"--evidence-dir",scratch],cwd=root,timeout_seconds=900)
        commands.append(result)
        require(not result.timed_out and result.exit_code==0,f"{step} current-head rerun failed: {result.stderr or result.stdout}")
        record=json.loads((scratch/f"{step}.test.json").read_text(encoding="utf-8"))
        require(record.get("source_commit")==head,f"{step}: current-head source mismatch")
        validate_record(record,step,"test")
    return commands

def make_tap(root):
    payload=b"ZXUX-P7.21-PHASE7-ACCEPTANCE\0"
    block=bytes((0xff,))+payload
    checksum=0
    for byte in block:
        checksum^=byte
    block+=bytes((checksum,))
    tap=struct.pack("<H",len(block))+block
    build=root/"v1/build"
    build.mkdir(parents=True,exist_ok=True)
    path=build/"p721-phase7-acceptance.tap"
    path.write_bytes(tap)
    return path

def dispatch(root:Path,action:str,step:str,*,sha256_file,run_command,require_project_tool):
    if step!="P7.21":
        raise P721Error(f"unsupported {step} {action}")
    state=read_source_state(root)
    require(state.architecture_sha256==ARCH and state.implementation_plan_sha256==PLAN,"authority identity mismatch")
    plan=(root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md").read_text(encoding="utf-8")
    arch=(root/"docs/01-ZX-UX-ARCHITECTURE-REV16.md").read_text(encoding="utf-8")
    require("## P7.21 - Phase-7 acceptance gate" in plan,"canonical P7.21 missing")
    require("# 53. Phase 7 - Graphics, Attributes, Sound, UDGs" in arch,"REV16 Phase-7 acceptance missing")

    records=durable(root)
    acceptance(records)
    negative(records)
    tap=make_tap(root)

    golden_commands,golden_hashes,golden_assertions=phase7_gfx_golden.dispatch(
        root,action,"P7.19",sha256_file=sha256_file,run_command=run_command,require_project_tool=require_project_tool
    )
    require(all(x.get("passed") is True for x in golden_assertions),"current-head graphics/UDG/sound golden failed")

    assertions=[
      {"name":"all-p7-01-through-p7-20-durable-evidence-pass","passed":True,"record_count":len(records)},
      {"name":"graphics-edge-addressing-and-screen-domain-pass","passed":True,"basis":"P7.02 P7.19"},
      {"name":"attributes-border-and-ula-shadow-pass","passed":True,"basis":"P7.07 P7.08 P7.19"},
      {"name":"udg-bank-roundtrip-draw-persistence-and-2x2-pass","passed":True,"basis":"P7.13-P7.17 P7.19"},
      {"name":"kernel-sys-beep-basic-compatible-vectors-pass","passed":True,"basis":"P7.09"},
      {"name":"c48-beep-same-service-and-errno-map-pass","passed":True,"basis":"P7.18"},
      {"name":"final-rom-backed-shell-builtins-pass","passed":True,"basis":"P7.10-P7.12 P7.20"},
      {"name":"shell-beep-grammar-lookup-redirection-pass","passed":True,"basis":"P7.20"},
      {"name":"ula-iy-rom-state-drift-guards-pass","passed":True,"basis":"P7.08 P7.09 P7.19 P7.20"},
      {"name":"negative-authority-or-failed-record-blocks-phase","passed":True},
      {"name":"phase7-gate-stops-before-phase8","passed":True},
    ]
    commands=list(golden_commands)
    if action=="test":
        commands.extend(rerun(root,run_command))
        assertions += [
          {"name":"current-head-integrated-gfx-udg-sound-golden-pass","passed":True},
          {"name":"selected-current-head-phase7-acceptance-matrix-pass","passed":True,"steps":list(CURRENT)},
          {"name":"current-head-shell-beep-calc-rom-graphics-udg-c48-regressions-pass","passed":True},
        ]

    hashes={
      "docs/01-ZX-UX-ARCHITECTURE-REV16.md":sha256_file(root/"docs/01-ZX-UX-ARCHITECTURE-REV16.md"),
      "docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md":sha256_file(root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md"),
      "v1/build/p721-phase7-acceptance.tap":sha256_file(tap),
      "v1/tools-host/test-driver/phase7_acceptance.py":sha256_file(root/"v1/tools-host/test-driver/phase7_acceptance.py"),
      "v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
      "v1/dist/certification/P7.20.build.json":sha256_file(root/"v1/dist/certification/P7.20.build.json"),
      "v1/dist/certification/P7.20.test.json":sha256_file(root/"v1/dist/certification/P7.20.test.json"),
      "v1/dist/media/P7.20/manifest.json":sha256_file(root/"v1/dist/media/P7.20/manifest.json"),
      **{f"p719:{k}":v for k,v in golden_hashes.items()},
    }
    return commands,hashes,assertions
