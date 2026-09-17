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
ROOT=Path(__file__).resolve().parents[1]; CERT=ROOT/"v1/dist/certification"
ARCH_SHA="a90d523f62a95e8cba6af0312b596a2d5f6bc1aa2ef92f39bb391509b7c15e1b"
PREFIX="phase2: activate Phase-2 certification evidence for "
class CertificationError(RuntimeError): pass
def git(*a):
 r=subprocess.run(["git",*a],cwd=ROOT,text=True,capture_output=True)
 if r.returncode: raise CertificationError(r.stderr.strip())
 return r.stdout.strip()
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):
 v=json.loads(p.read_text(encoding="utf-8"))
 if not isinstance(v,dict): raise CertificationError(f"{p.name}: object required")
 return v
def activation():
 xs=git("log","--format=%H","--","v1/dist/certification/phase-2.json").splitlines(); return xs[0] if xs else None
def expected(step):
 n=int(step.split(".")[1]); return {"P1.41":"PASS"} if n==1 else {f"P2.{n-1:02d}":"PASS"}
def validate_complete():
 agg=load(CERT/"phase-2.json")
 exact={"schema":2,"phase":2,"action":"phase-result","status":"PASS","pass_marker":"ZX-UX PHASE 2 CERTIFICATION PASS","worktree_clean":True,"architecture_sha256":ARCH_SHA}
 for k,v in exact.items():
  if agg.get(k)!=v: raise CertificationError(f"phase-2.json {k} mismatch")
 source=agg.get("source_commit"); lock=agg.get("toolchain_lock_sha256")
 if not isinstance(source,str) or len(source)!=40 or not isinstance(lock,str) or len(lock)!=64: raise CertificationError("invalid aggregate identity")
 if subprocess.run(["git","merge-base","--is-ancestor",source,"HEAD"],cwd=ROOT).returncode: raise CertificationError("certified source is not an ancestor")
 names=[f"P2.{n:02d}.{a}.json" for n in range(1,25) for a in ("build","test")]
 if agg.get("required_records")!=names or set(agg.get("record_sha256",{}))!=set(names): raise CertificationError("aggregate record manifest mismatch")
 for n in range(1,25):
  for action in ("build","test"):
   name=f"P2.{n:02d}.{action}.json"; p=CERT/name
   if not p.is_file(): raise CertificationError(f"missing durable evidence: {name}")
   r=load(p)
   if r.get("step")!=f"P2.{n:02d}" or r.get("action")!=action or r.get("status")!="PASS" or r.get("worktree_clean") is not True: raise CertificationError(f"{name}: invalid PASS record")
   if r.get("architecture_sha256")!=ARCH_SHA or r.get("prerequisites")!=expected(r["step"]): raise CertificationError(f"{name}: authority/prerequisite mismatch")
   rs=r.get("source_commit")
   if not isinstance(rs,str) or subprocess.run(["git","merge-base","--is-ancestor",rs,source],cwd=ROOT).returncode: raise CertificationError(f"{name}: source is not historical ancestor of aggregate source")
   if n>=10 and rs!=source: raise CertificationError(f"{name}: Phase-2 final tranche must name aggregate source")
   if agg["record_sha256"].get(name)!=sha(p): raise CertificationError(f"{name}: bytes differ from aggregate manifest")
 req={x.get("name") for x in agg.get("assertions",[]) if isinstance(x,dict) and x.get("passed") is True}
 must={"p2-24-build-test-pass","all-p2-01-through-p2-23-current-source-replay-pass","mex1-inspector-pass","relocation-atomicity-pass","spawn-exec-wait-zombie-pass","context-iy-altreg-pass","leak-pass","two-base-relocatable-pass","negative-rollback-blocks-pass","rev12-rev03-authority-pass"}
 if not must.issubset(req): raise CertificationError("aggregate acceptance assertion missing")
 return agg
def main():
 ap=argparse.ArgumentParser(); ap.add_argument("--require-active",action="store_true"); a=ap.parse_args()
 try:
  act=activation()
  if act is None:
   if a.require_active: raise CertificationError("Phase-2 evidence has not been activated")
   print("ZX-UX PHASE 2 EVIDENCE PRE-ACTIVATION PASS"); return 0
  agg=validate_complete(); source=agg["source_commit"]
  if git("rev-parse",f"{act}^")!=source: raise CertificationError("activation is not direct child of certified source")
  if git("log","-1","--format=%s",act)!=PREFIX+source: raise CertificationError("activation commit message mismatch")
  changed=git("diff-tree","--no-commit-id","--name-only","-r",source,act).splitlines()
  if not changed or any(not (p.startswith("v1/dist/certification/") and p.endswith(".json")) for p in changed): raise CertificationError("activation is not evidence-only")
  original=subprocess.run(["git","show",f"{act}:v1/dist/certification/phase-2.json"],cwd=ROOT,capture_output=True).stdout
  if (CERT/"phase-2.json").read_bytes()!=original: raise CertificationError("durable Phase-2 aggregate changed after activation")
  print("ZX-UX PHASE 2 DURABLE EVIDENCE PASS"); return 0
 except Exception as e:
  print(f"ZX-UX PHASE 2 EVIDENCE FAIL: {e}",file=sys.stderr); return 1
if __name__=="__main__": raise SystemExit(main())
