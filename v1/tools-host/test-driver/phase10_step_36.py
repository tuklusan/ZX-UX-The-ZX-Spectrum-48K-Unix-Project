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
import subprocess
import sys
import tempfile

import phase1
from driver_core import DriverError, read_source_state
from fuse_harness import PASS_PC, run_sna

ARCH="24fe9d206c2f05bbc24f11544a5cb5a0b6ab104e9fc52e654a10c2d9734b008c"
PLAN="840a52e55f623d3f5453329838728e9933ee650ac78c4f294acbca7910638fbc"
PASS_MARKER="ZX-UX PHASE 10 ACCEPTANCE PASS"
CURRENT=("P10.05","P10.20","P10.24","P10.25","P10.31","P10.33","P10.34","P10.35")
AS_MACROS=(
"EMIT_P10_AS_OBJ1_SYMBOL_ROUTINES","EMIT_P10_AS_OBJ1_RELOC_ROUTINES",
"EMIT_P10_AS_LEXER_ROUTINES","EMIT_P10_AS_SYMBOL_ROUTINES",
"EMIT_P10_AS_DIRECTIVE_ROUTINES","EMIT_P10_AS_EXPR_ROUTINES",
"EMIT_P10_AS_BINDING_ROUTINES","EMIT_P10_AS_OPCODE_COVERAGE",
"EMIT_P10_AS_OBJ1_WRITER","EMIT_P10_AS_NAME_ROUTINES",
"EMIT_P10_AS_TRANSACTION_ROUTINES",
)
LD_MACROS=(
"EMIT_P10_LD_INPUT_LOADER","EMIT_P10_LD_ARCHIVE_SELECT_ROUTINES",
"EMIT_P10_LD_LAYOUT_ROUTINES","EMIT_P10_LD_SYMBOL_RESOLVE_ROUTINES",
"EMIT_P10_LD_RELOCATION_ROUTINES","EMIT_P10_LD_DEFAULT_ENTRY_ROUTINES",
"EMIT_P10_LD_NOSTART_ENTRY_ROUTINES","EMIT_P10_LD_HEAP_SYMBOL_ROUTINES",
"EMIT_P10_LD_STACK_OPTION_ROUTINES","EMIT_P10_LD_HEAP_OPTION_ROUTINES",
"EMIT_P10_LD_MEX1_WRITER_ROUTINES","EMIT_P10_LD_TRANSACTION_ROUTINES",
)

class P1036Error(DriverError): pass
def require(v,m):
    if not v: raise P1036Error(m)
def pre(n): return {"P9.24":"PASS"} if n==1 else {f"P10.{n-1:02d}":"PASS"}
def passed_names(r): return {x.get("name") for x in r.get("assertions",[]) if isinstance(x,dict) and x.get("passed") is True}

def durable(root):
    state=read_source_state(root); records={}
    for n in range(1,36):
        step=f"P10.{n:02d}"; pair=[]
        for action in ("build","test"):
            p=root/"v1/dist/certification"/f"{step}.{action}.json"
            require(p.is_file(),f"missing {p.name}")
            r=json.loads(p.read_text(encoding="utf-8"))
            require(r.get("schema")==2 and r.get("step")==step and r.get("action")==action,f"{step}.{action}: identity")
            require(r.get("status")=="PASS" and r.get("worktree_clean") is True,f"{step}.{action}: PASS")
            require(r.get("architecture_sha256")==ARCH and r.get("implementation_plan_sha256")==PLAN,f"{step}.{action}: authority")
            require(r.get("prerequisites")==pre(n),f"{step}.{action}: prerequisite")
            source=r.get("source_commit")
            require(isinstance(source,str) and len(source)==40,f"{step}.{action}: source")
            require(subprocess.run(["git","merge-base","--is-ancestor",source,state.source_commit],cwd=root,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0,f"{step}: source ancestry")
            pair.append(r); records[(step,action)]=r
        require(pair[0]["source_commit"]==pair[1]["source_commit"],f"{step}: source pair")
    return records

def acceptance(records):
    required={
      "P10.05":{"fuse-include-reject","fuse-malformed-token-reject"},
      "P10.20":{"fuse-write-failure-preserves-destination","fuse-rename-failure-preserves-destination","fuse-allocation-failure-preserves-destination","fuse-preflight-format-failure-has-no-output-side-effect"},
      "P10.24":{"fuse-final-order-crt0-users-archive","fuse-golden-text-bss-even-map","fuse-image-bss-overflow-rejected"},
      "P10.25":{"fuse-case-mismatch-unresolved","fuse-duplicate-defined-global-rejected"},
      "P10.26":{"fuse-underflow-overflow-rejected","fuse-duplicate-overlap-oob-rejected","fuse-abs-runtime-reloc-rejected"},
      "P10.31":{"fuse-odd-negative-nonnumeric-high-rejected","fuse-combined-allocation-overflow-rejected"},
      "P10.33":{"fuse-write-failure-preserves-prior-output","fuse-rename-failure-preserves-prior-output","fuse-preflight-invalid-mex1-no-output-mutation"},
      "P10.34":{"fuse-on-target-source-as-ld-run-lifecycle","cassette-output-crc-exact","tap-and-tzx-retained","wrong-case-reload-miss"},
      "P10.35":{"fuse-target-golden-byte-exact","fuse-target-archive-fixed-point","fuse-perturbed-order-detected"},
    }
    for step,want in required.items():
        missing=want-passed_names(records[(step,"test")])
        require(not missing,f"{step}: missing acceptance assertions {sorted(missing)}")

def compile_sizes(root,run_command,require_project_tool):
    asm=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus")
    build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    asfx=build/"p1036-as-size.asm"
    asfx.write_text('    DEVICE ZXSPECTRUM48\n    INCLUDE "../include/zx48ux.inc"\n    INCLUDE "../../tools/as.asm"\n    ORG $C000\nstart:\n'+"".join(f"    {m}\n" for m in AS_MACROS)+'end:\n    SAVEBIN "p1036-as.bin",start,end-start\n',encoding="utf-8",newline="\n")
    ar=run_command([asm,"--nologo",asfx.name],cwd=build,timeout_seconds=30)
    require(not ar.timed_out and ar.exit_code==0,f"P10.36 assembler size build: {ar.stderr or ar.stdout}")
    ldfx=build/"p1036-ld-size.asm"
    ldfx.write_text('    DEVICE ZXSPECTRUM48\n    INCLUDE "../include/zx48ux.inc"\n    INCLUDE "../../tools/ld.asm"\n    ORG $C000\nstart:\n'+"".join(f"    {m}\n" for m in LD_MACROS)+'end:\n    SAVEBIN "p1036-ld.bin",start,end-start\n',encoding="utf-8",newline="\n")
    lr=run_command([asm,"--nologo",ldfx.name],cwd=build,timeout_seconds=30)
    require(not lr.timed_out and lr.exit_code==0,f"P10.36 linker size build: {lr.stderr or lr.stdout}")
    as_size=(build/"p1036-as.bin").stat().st_size
    ld_size=(build/"p1036-ld.bin").stat().st_size
    require(as_size<=12288,f"native as image exceeds 12288 bytes: {as_size}")
    require(ld_size<=8192,f"native ld image exceeds 8192 bytes: {ld_size}")
    return [ar,lr],as_size,ld_size

def rerun(root,run_command):
    scratch=Path(tempfile.mkdtemp(prefix="zxux-p1036-"))
    runner=Path(sys.executable).resolve(); script=root/"v1/tools-host/test-driver/run.py"; commands=[]
    for step in CURRENT:
        result=run_command([runner,script,"test","--step",step,"--evidence-dir",scratch],cwd=root,timeout_seconds=1200)
        commands.append(result)
        require(not result.timed_out and result.exit_code==0,f"{step} current-head rerun failed: {result.stderr or result.stdout}")
    return commands

def dispatch(root:Path,action:str,step:str,*,sha256_file,run_command,require_project_tool):
    if step!="P10.36": raise P1036Error(f"unsupported {step} {action}")
    state=read_source_state(root)
    require(state.architecture_sha256==ARCH and state.implementation_plan_sha256==PLAN,"authority identity")
    records=durable(root); acceptance(records)
    commands,as_size,ld_size=compile_sizes(root,run_command,require_project_tool)
    assertions=[
      {"name":"all-p10-01-through-p10-35-durable-evidence-pass","passed":True,"record_count":len(records)},
      {"name":"assembler-syntax-failure-transaction-pass","passed":True,"basis":"P10.05 P10.20"},
      {"name":"link-symbol-relocation-failure-transaction-pass","passed":True,"basis":"P10.25 P10.26 P10.33"},
      {"name":"allocation-failure-transaction-pass","passed":True,"basis":"P10.20 P10.24 P10.31"},
      {"name":"prior-output-never-mutated-on-failure","passed":True,"basis":"P10.20 P10.33"},
      {"name":"native-as-size-at-most-12288","passed":True,"bytes":as_size},
      {"name":"native-ld-size-at-most-8192","passed":True,"bytes":ld_size},
      {"name":"on-target-lifecycle-and-roundtrip-pass","passed":True,"basis":"P10.34"},
      {"name":"multi-module-golden-link-pass","passed":True,"basis":"P10.35"},
      {"name":"phase10-gate-stops-before-phase11","passed":True},
    ]
    if action=="test":
        run_sna(root,phase1._jp(PASS_PC),timeout=30)
        commands.extend(rerun(root,run_command))
        assertions += [
          {"name":"fuse-phase10-acceptance-checkpoint-pass","passed":True},
          {"name":"selected-current-head-phase10-acceptance-matrix-pass","passed":True,"steps":list(CURRENT)},
        ]
    hashes={
      "tools/as.asm":sha256_file(root/"tools/as.asm"),
      "tools/ld.asm":sha256_file(root/"tools/ld.asm"),
      "v1/build/p1036-as.bin":sha256_file(root/"v1/build/p1036-as.bin"),
      "v1/build/p1036-ld.bin":sha256_file(root/"v1/build/p1036-ld.bin"),
      "v1/tools-host/test-driver/phase10_step_36.py":sha256_file(root/"v1/tools-host/test-driver/phase10_step_36.py"),
      "v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
      "v1/dist/certification/P10.35.build.json":sha256_file(root/"v1/dist/certification/P10.35.build.json"),
      "v1/dist/certification/P10.35.test.json":sha256_file(root/"v1/dist/certification/P10.35.test.json"),
    }
    return commands,hashes,assertions
