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
import json, shutil, subprocess, sys, tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def run(*a,cwd=ROOT): return subprocess.run(a,cwd=cwd,text=True,capture_output=True)
def mutate(p,k,v):
    d=json.loads(p.read_text(encoding="utf-8")); d[k]=v
    p.write_text(json.dumps(d,indent=2,sort_keys=True)+"\n",encoding="utf-8",newline="\n")

def main():
    current=run(sys.executable,"tools/check_phase8_evidence.py")
    if "PRE-ACTIVATION PASS" in current.stdout:
        required=run(sys.executable,"tools/check_phase8_evidence.py","--require-active")
        if required.returncode==0: return 1
        print("ZX-UX PHASE 8 EVIDENCE NEGATIVE PRE-ACTIVATION PASS")
        return 0
    if current.returncode: return 1
    work=Path(tempfile.mkdtemp(prefix="zxux-phase8-negative-"))
    try:
        shutil.rmtree(work)
        if run("git","worktree","add","--detach",str(work),"HEAD").returncode: return 1
        target=work/"v1/dist/certification/P8.40.result.json"
        for name,change in [
            ("missing",lambda p:p.unlink()),
            ("wrong-source",lambda p:mutate(p,"source_commit","0"*40)),
            ("failed",lambda p:mutate(p,"status","FAIL")),
        ]:
            run("git","reset","--hard","HEAD",cwd=work); run("git","clean","-fd",cwd=work); change(target)
            if run(sys.executable,"tools/check_phase8_evidence.py","--require-active",cwd=work).returncode==0:
                raise RuntimeError("negative case passed: "+name)
        print("ZX-UX PHASE 8 EVIDENCE NEGATIVE PASS")
        return 0
    finally:
        run("git","worktree","remove","--force",str(work)); shutil.rmtree(work,ignore_errors=True)

if __name__=="__main__":
    raise SystemExit(main())
