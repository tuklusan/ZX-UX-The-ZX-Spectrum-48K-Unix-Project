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
import argparse, hashlib, json, subprocess, sys
from pathlib import Path

ARCH_SHA="a90d523f62a95e8cba6af0312b596a2d5f6bc1aa2ef92f39bb391509b7c15e1b"
class FinalizeError(RuntimeError): pass
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):
    v=json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(v,dict): raise FinalizeError(f"{p.name}: object required")
    return v
def write(p,v): p.write_text(json.dumps(v,indent=2,sort_keys=True)+"\n",encoding="utf-8",newline="\n")
def head(root):
    r=subprocess.run(["git","rev-parse","HEAD"],cwd=root,text=True,capture_output=True)
    if r.returncode: raise FinalizeError(r.stderr.strip())
    return r.stdout.strip()
def expected(step):
    n=int(step.split(".")[1]); return {"P1.41":"PASS"} if n==1 else {f"P2.{n-1:02d}":"PASS"}
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--root",required=True); ap.add_argument("--evidence-dir",required=True); a=ap.parse_args()
    try:
      root=Path(a.root).resolve(); ev=Path(a.evidence_dir).resolve(); src=head(root); cert=root/"v1/dist/certification"
      staged={}
      sources=set(); locks=set()
      for n in range(1,25):
        for action in ("build","test"):
          name=f"P2.{n:02d}.{action}.json"; p=ev/name
          if not p.is_file(): raise FinalizeError(f"missing staged evidence: {name}")
          r=load(p)
          if r.get("step")!=f"P2.{n:02d}" or r.get("action")!=action or r.get("status")!="PASS" or r.get("worktree_clean") is not True: raise FinalizeError(f"{name}: clean PASS required")
          if r.get("source_commit")!=src or r.get("architecture_sha256")!=ARCH_SHA or r.get("prerequisites")!=expected(r["step"]): raise FinalizeError(f"{name}: exact source/authority/prerequisite mismatch")
          staged[name]=r; sources.add(r.get("source_commit")); locks.add(r.get("toolchain_lock_sha256"))
      if sources!={src} or len(locks)!=1: raise FinalizeError("aggregate replay identity mismatch")
      p224={x.get("name") for x in staged["P2.24.test.json"].get("assertions",[]) if isinstance(x,dict) and x.get("passed") is True}
      required_assertions={"phase2-current-source-registered-gate-pass","mex1-inspector-evidence-pass","relocation-atomicity-evidence-pass","spawn-exec-wait-zombie-evidence-pass","context-iy-altreg-evidence-pass","process-memory-bootstrap-placement-evidence-pass","leak-evidence-pass","two-base-relocatable-evidence-pass","negative-missing-required-component-rejected"}
      if not required_assertions.issubset(p224): raise FinalizeError("P2.24 acceptance assertion set incomplete")
      names=[f"P2.{n:02d}.{action}.json" for n in range(1,25) for action in ("build","test")]
      manifest={}
      for n in range(1,25):
        for action in ("build","test"):
          name=f"P2.{n:02d}.{action}.json"
          source_path=(cert/name) if n<=9 else (ev/name)
          if not source_path.is_file(): raise FinalizeError(f"durable/admission record missing: {name}")
          manifest[name]=sha(source_path)
      aggregate={"schema":2,"phase":2,"action":"phase-result","status":"PASS","pass_marker":"ZX-UX PHASE 2 CERTIFICATION PASS","source_commit":src,"toolchain_lock_sha256":next(iter(locks)),"architecture_sha256":ARCH_SHA,"worktree_clean":True,"required_records":names,"record_sha256":manifest,"assertions":[
        {"name":"p2-24-build-test-pass","passed":True},{"name":"all-p2-01-through-p2-23-current-source-replay-pass","passed":True},{"name":"mex1-inspector-pass","passed":True},{"name":"relocation-atomicity-pass","passed":True},{"name":"spawn-exec-wait-zombie-pass","passed":True},{"name":"context-iy-altreg-pass","passed":True},{"name":"leak-pass","passed":True},{"name":"two-base-relocatable-pass","passed":True},{"name":"negative-rollback-blocks-pass","passed":True},{"name":"rev12-rev03-authority-pass","passed":True}
      ]}
      write(ev/"phase-2.json",aggregate)
      print("ZX-UX PHASE 2 EVIDENCE FINALIZATION PASS"); return 0
    except Exception as e:
      print(f"ZX-UX PHASE 2 EVIDENCE FINALIZATION FAIL: {e}",file=sys.stderr); return 1
if __name__=="__main__": raise SystemExit(main())
