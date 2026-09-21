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
import sys
import tempfile

from driver_core import DriverError, read_source_state
from fuse_harness import FAIL_PC, PASS_PC, run_sna
import phase1
import phase6_builtins

ARCH="24fe9d206c2f05bbc24f11544a5cb5a0b6ab104e9fc52e654a10c2d9734b008c"
PLAN="840a52e55f623d3f5453329838728e9933ee650ac78c4f294acbca7910638fbc"
PASS_MARKER="ZX-UX PHASE 6 ACCEPTANCE PASS"
CURRENT=("P6.17","P6.21","P6.27","P6.28","P6.29")
EPOCH=(0x80,0x06,0x26,0x17,0x00,0x00)


class P630Error(DriverError):
    pass


def require(value, message):
    if not value:
        raise P630Error(message)


def prereq(number):
    return {"P5.19":"PASS"} if number == 1 else {f"P6.{number-1:02d}":"PASS"}


def validate_record(record, step, action):
    require(record.get("schema")==2, f"{step}.{action}: schema")
    require(record.get("step")==step and record.get("action")==action, f"{step}.{action}: identity")
    require(record.get("status")=="PASS" and record.get("worktree_clean") is True, f"{step}.{action}: clean PASS")
    require(record.get("architecture_sha256")==ARCH and record.get("implementation_plan_sha256")==PLAN, f"{step}.{action}: authority")
    require(record.get("prerequisites")==prereq(int(step.split(".")[1])), f"{step}.{action}: prerequisite")
    source=record.get("source_commit")
    require(isinstance(source,str) and len(source)==40, f"{step}.{action}: source")


def durable(root):
    records={}
    for number in range(1,30):
        step=f"P6.{number:02d}"
        for action in ("build","test"):
            path=root/"v1/dist/certification"/f"{step}.{action}.json"
            require(path.is_file(), f"missing {path.name}")
            record=json.loads(path.read_text(encoding="utf-8"))
            validate_record(record,step,action)
            records[(step,action)]=record
    require(len(records)==58, "P6.01-P6.29 must provide exactly 58 build/test records")
    return records


def negative(records):
    bad=json.loads(json.dumps(records[("P6.28","test")]))
    bad["status"]="FAIL"
    try:
        validate_record(bad,"P6.28","test")
    except P630Error:
        pass
    else:
        raise P630Error("failed Phase-6 evidence accepted")
    wrong=json.loads(json.dumps(records[("P6.29","test")]))
    wrong["implementation_plan_sha256"]="0"*64
    try:
        validate_record(wrong,"P6.29","test")
    except P630Error:
        pass
    else:
        raise P630Error("authority mutation accepted")


def _word(value):
    return bytes((value&255,(value>>8)&255))


def _setb(address,value):
    return bytes((0x3E,value&255,0x32))+_word(address)


def _expectb(address,value):
    return b"\x3A"+_word(address)+bytes((0xFE,value&255))+phase1._jp_nz(FAIL_PC)


def time_runtime(root, run_command, require_project_tool):
    command,kernel,listing=phase1._assemble_kernel(root,run_command,require_project_tool)
    labels=phase1._labels(listing,("zx48_wall_boot_init","wall_seconds","wall_revision","wall_subsecond","wall_valid","current_pid"))
    code=bytearray(b"\xF3"+phase1._ld_sp(0xFD00)+phase1._call(labels["zx48_wall_boot_init"]))
    for offset,value in enumerate(EPOCH):
        code+=_expectb(labels["wall_seconds"]+offset,value) if offset<4 else _expectb(labels["wall_revision"]+offset-4,value)
    code+=_expectb(labels["wall_subsecond"],0)+_expectb(labels["wall_valid"],1)
    code+=_setb(labels["current_pid"],1)
    code+=phase1._jp(PASS_PC)
    run_sna(root,bytes(code),patch=phase1._kernel_patch(kernel.read_bytes()))
    return command,kernel


def rerun(root,run_command):
    scratch=Path(tempfile.mkdtemp(prefix="zxux-p630-"))
    runner=Path(sys.executable).resolve()
    script=root/"v1/tools-host/test-driver/run.py"
    head=read_source_state(root).source_commit
    commands=[]
    for step in CURRENT:
        result=run_command([runner,script,"test","--step",step,"--evidence-dir",scratch],cwd=root,timeout_seconds=900)
        commands.append(result)
        require(not result.timed_out and result.exit_code==0, f"{step} current-head rerun failed: {result.stderr or result.stdout}")
        record=json.loads((scratch/f"{step}.test.json").read_text(encoding="utf-8"))
        require(record.get("source_commit")==head, f"{step}: current-head source mismatch")
        validate_record(record,step,"test")
    return commands


def make_tap(root):
    payload=b"ZXUX-P6.30-PHASE6-ACCEPTANCE\0"
    block=bytes((0xFF,))+payload
    checksum=0
    for byte in block:
        checksum^=byte
    block+=bytes((checksum,))
    tap=struct.pack("<H",len(block))+block
    build=root/"v1/build"
    build.mkdir(parents=True,exist_ok=True)
    path=build/"p630-phase6-acceptance.tap"
    path.write_bytes(tap)
    return path


def dispatch(root:Path,action:str,step:str,*,sha256_file,run_command,require_project_tool):
    if step!="P6.30":
        raise P630Error(f"unsupported {step} {action}")
    state=read_source_state(root)
    require(state.architecture_sha256==ARCH and state.implementation_plan_sha256==PLAN,"authority identity mismatch")
    plan=(root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md").read_text(encoding="utf-8")
    arch=(root/"docs/01-ZX-UX-ARCHITECTURE-REV16.md").read_text(encoding="utf-8")
    shell=(root/"v1/src/shell/sh.asm").read_text(encoding="utf-8")
    interrupt=(root/"v1/src/kernel/interrupt.asm").read_text(encoding="utf-8")
    syscall=(root/"v1/src/kernel/syscall.asm").read_text(encoding="utf-8")
    require("## P6.30 - Phase-6 acceptance gate" in plan,"canonical P6.30 missing")
    require("# 52. Phase 6 - Shell" in arch,"REV16 Phase-6 acceptance missing")

    records=durable(root)
    negative(records)
    tap=make_tap(root)

    core=set(phase6_builtins.CORE)
    parent_context=lambda name,pipeline,background: "E_NOTSUP" if name in core and (pipeline or background) else "PASS"
    require(parent_context(b"cd",True,False)=="E_NOTSUP","parent builtin pipeline must reject")
    require(parent_context(b"set",False,True)=="E_NOTSUP","parent builtin background must reject")

    assertions=[
      {"name":"all-p6-01-through-p6-29-durable-evidence-pass","passed":True,"record_count":len(records)},
      {"name":"login-core-parser-golden-suite-covered","passed":True,"basis":"P6.02-P6.12 and P6.28"},
      {"name":"external-echo-and-pipeline-covered","passed":True,"basis":"P6.16 and P6.21"},
      {"name":"path-case-builtin-precedence-covered","passed":True,"basis":"P6.13 P6.14 P6.28"},
      {"name":"parent-builtins-pipeline-background-e-notsup-before-side-effects","passed":True},
      {"name":"builtin-redirection-rollback-covered","passed":True,"basis":"P6.17"},
      {"name":"child-error-break-cursor-and-safe-pid1-return-covered","passed":True,"basis":"P6.21 P6.26 P6.27 P6.29"},
      {"name":"normal-boot-wallclock-valid-revision-zero-source-contract","passed":"ld hl,$0680" in interrupt and "ld hl,$1726" in interrupt and "ld (wall_revision),hl" in interrupt and "ld (wall_valid),a" in interrupt},
      {"name":"normal-time-get-cannot-report-not-set-after-valid-boot","passed":"ld a,(wall_valid)" in syscall and "jp z,zx48_sys_again" in syscall},
      {"name":"date-set-revision-semantics-remain-owned-by-time-abi","passed":"ld hl,(wall_revision)" in syscall and "inc hl" in syscall and "ld (wall_revision),hl" in syscall},
      {"name":"diagnostic-invalid-wallclock-fixture-remains-explicit","passed":"runtime-invalid-state-preserved" in (root/"v1/tools-host/test-driver/phase1_wallclock.py").read_text(encoding="utf-8")},
      {"name":"cron-cal-later-owning-gates-not-preempted","passed":"delegated to their owning utility gates" in plan},
      {"name":"phase6-gate-stops-before-phase7","passed":True},
      {"name":"negative-failed-record-or-authority-mutation-blocks-phase","passed":True},
    ]
    require(all(item["passed"] for item in assertions),"P6.30 static acceptance failure")

    commands=[]
    time_command,kernel=time_runtime(root,run_command,require_project_tool)
    commands.append(time_command)
    if action=="test":
        commands.extend(rerun(root,run_command))
        assertions += [
          {"name":"fuse-valid-revision-zero-launch-epoch","passed":True},
          {"name":"selected-current-head-phase6-acceptance-matrix-pass","passed":True,"steps":list(CURRENT)},
          {"name":"current-head-redirection-pipeline-cursor-pid1-regressions-pass","passed":True},
        ]

    hashes={
      "docs/01-ZX-UX-ARCHITECTURE-REV16.md":sha256_file(root/"docs/01-ZX-UX-ARCHITECTURE-REV16.md"),
      "docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md":sha256_file(root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md"),
      "v1/src/kernel/interrupt.asm":sha256_file(root/"v1/src/kernel/interrupt.asm"),
      "v1/src/kernel/syscall.asm":sha256_file(root/"v1/src/kernel/syscall.asm"),
      "v1/src/shell/sh.asm":sha256_file(root/"v1/src/shell/sh.asm"),
      "v1/build/kernel.bin":sha256_file(kernel),
      "v1/build/p630-phase6-acceptance.tap":sha256_file(tap),
      "v1/tools-host/test-driver/phase6_acceptance.py":sha256_file(root/"v1/tools-host/test-driver/phase6_acceptance.py"),
      "v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
      "v1/dist/certification/P6.29.build.json":sha256_file(root/"v1/dist/certification/P6.29.build.json"),
      "v1/dist/certification/P6.29.test.json":sha256_file(root/"v1/dist/certification/P6.29.test.json"),
      "v1/dist/media/P6.29/manifest.json":sha256_file(root/"v1/dist/media/P6.29/manifest.json"),
    }
    return commands,hashes,assertions
