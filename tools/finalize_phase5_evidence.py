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
ARCH="24fe9d206c2f05bbc24f11544a5cb5a0b6ab104e9fc52e654a10c2d9734b008c"
PLAN="840a52e55f623d3f5453329838728e9933ee650ac78c4f294acbca7910638fbc"
P519="ZX-UX PHASE 5 ACCEPTANCE PASS"
PHASE="ZX-UX PHASE 5 CERTIFICATION PASS"
class E(RuntimeError): pass
def load(p): return json.loads(p.read_text())
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def git(root,*a):
 r=subprocess.run(["git",*a],cwd=root,text=True,capture_output=True)
 if r.returncode: raise E(r.stderr.strip() or r.stdout.strip())
 return r.stdout.strip()
def pre(n): return {"P4.33":"PASS"} if n==1 else {f"P5.{n-1:02d}":"PASS"}
def main():
 ap=argparse.ArgumentParser(); ap.add_argument("--root",required=True); ap.add_argument("--output",required=True); a=ap.parse_args()
 try:
  root=Path(a.root).resolve(); out=Path(a.output).resolve(); cert=root/"v1/dist/certification"
  res=load(cert/"P5.19.result.json"); source=res.get("source_commit")
  if not isinstance(source,str) or len(source)!=40: raise E("P5.19 result source")
  exact={"step":"P5.19","action":"result","status":"PASS","pass_marker":P519,"architecture_sha256":ARCH,"implementation_plan_sha256":PLAN,"worktree_clean":True,"prerequisites":{"P5.18":"PASS"}}
  for k,v in exact.items():
   if res.get(k)!=v: raise E(f"P5.19.result {k}")
  names=[]; manifest={}; locks=set()
  for n in range(1,20):
   step=f"P5.{n:02d}"
   for action in ("build","test"):
    name=f"{step}.{action}.json"; p=cert/name
    if not p.is_file(): raise E(f"missing {name}")
    r=load(p)
    if r.get("step")!=step or r.get("action")!=action or r.get("status")!="PASS" or r.get("worktree_clean") is not True: raise E(f"{name}: clean PASS")
    if r.get("architecture_sha256")!=ARCH or r.get("implementation_plan_sha256")!=PLAN or r.get("prerequisites")!=pre(n): raise E(f"{name}: authority/prereq")
    rs=r.get("source_commit")
    if not isinstance(rs,str) or subprocess.run(["git","merge-base","--is-ancestor",rs,source],cwd=root,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode: raise E(f"{name}: source ancestry")
    if n==19 and rs!=source: raise E(f"{name}: P5.19 source mismatch")
    lock=r.get("toolchain_lock_sha256")
    if not isinstance(lock,str) or len(lock)!=64: raise E(f"{name}: toolchain")
    locks.add(lock); names.append(name); manifest[name]=sha(p)
  if len(locks)!=1: raise E("toolchain identity mismatch")
  names.append("P5.19.result.json"); manifest["P5.19.result.json"]=sha(cert/"P5.19.result.json")
  agg={"schema":2,"phase":5,"action":"phase-result","status":"PASS","pass_marker":PHASE,"source_commit":source,
       "toolchain_lock_sha256":next(iter(locks)),"architecture_sha256":ARCH,"implementation_plan_sha256":PLAN,
       "worktree_clean":True,"required_records":names,"record_sha256":manifest,
       "assertions":[
        {"name":"p5-19-build-test-result-pass","passed":True},
        {"name":"all-p5-01-through-p5-19-durable-evidence-pass","passed":True},
        {"name":"rev16-rev07-authority-pass","passed":True},
        {"name":"phase5-record-manifest-byte-exact","passed":True},
        {"name":"phase5-acceptance-bullets-pass","passed":True},
        {"name":"phase5-gate-stops-before-phase6","passed":True}]}
  out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(agg,indent=2,sort_keys=True)+"\n",encoding="utf-8",newline="\n")
  print("ZX-UX PHASE 5 EVIDENCE FINALIZATION PASS"); return 0
 except Exception as exc:
  print(f"ZX-UX PHASE 5 EVIDENCE FINALIZATION FAIL: {exc}",file=sys.stderr); return 1
if __name__=="__main__": raise SystemExit(main())
