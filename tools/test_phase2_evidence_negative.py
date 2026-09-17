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
def main():
 current=run(sys.executable,"tools/check_phase2_evidence.py")
 if "PRE-ACTIVATION PASS" in current.stdout:
  required=run(sys.executable,"tools/check_phase2_evidence.py","--require-active")
  if required.returncode==0: return 1
  print("ZX-UX PHASE 2 EVIDENCE NEGATIVE PRE-ACTIVATION PASS"); return 0
 if current.returncode: return 1
 work=Path(tempfile.mkdtemp(prefix="zxux-phase2-evidence-negative-"))
 try:
  shutil.rmtree(work); r=run("git","worktree","add","--detach",str(work),"HEAD")
  if r.returncode: raise RuntimeError(r.stderr)
  cases=[("missing",lambda p:p.unlink()),("wrong-source",lambda p:_mut(p,"source_commit","0"*40)),("failed",lambda p:_mut(p,"status","FAIL"))]
  target=work/"v1/dist/certification/P2.24.test.json"
  for name,fn in cases:
   run("git","reset","--hard","HEAD",cwd=work); run("git","clean","-fd",cwd=work); fn(target)
   if run(sys.executable,"tools/check_phase2_evidence.py","--require-active",cwd=work).returncode==0: raise RuntimeError(f"negative case passed: {name}")
  print("ZX-UX PHASE 2 EVIDENCE NEGATIVE PASS"); return 0
 finally:
  run("git","worktree","remove","--force",str(work)); shutil.rmtree(work,ignore_errors=True)
def _mut(p,k,v):
 d=json.loads(p.read_text()); d[k]=v; p.write_text(json.dumps(d,indent=2,sort_keys=True)+"\n")
if __name__=="__main__": raise SystemExit(main())
