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

ROOT=Path(__file__).resolve().parents[1]
CERT=ROOT/"v1/dist/certification"
ARCH="24fe9d206c2f05bbc24f11544a5cb5a0b6ab104e9fc52e654a10c2d9734b008c"
PLAN="840a52e55f623d3f5453329838728e9933ee650ac78c4f294acbca7910638fbc"
PREFIX="phase10: activate Phase-10 aggregate evidence for "
P1036="ZX-UX PHASE 10 ACCEPTANCE PASS"
PHASE="ZX-UX PHASE 10 CERTIFICATION PASS"

class E(RuntimeError): pass
def git(*a):
    r=subprocess.run(["git",*a],cwd=ROOT,text=True,capture_output=True)
    if r.returncode: raise E(r.stderr.strip() or r.stdout.strip())
    return r.stdout.strip()
def load(p): return json.loads(p.read_text(encoding="utf-8"))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def pre(n): return {"P9.24":"PASS"} if n==1 else {f"P10.{n-1:02d}":"PASS"}
def activation():
    xs=git("log","--format=%H","--","v1/dist/certification/phase-10.json").splitlines()
    return xs[0] if xs else None

def validate():
    a=load(CERT/"phase-10.json")
    for k,v in {"schema":2,"phase":10,"action":"phase-result","status":"PASS","pass_marker":PHASE,
                "worktree_clean":True,"architecture_sha256":ARCH,"implementation_plan_sha256":PLAN}.items():
        if a.get(k)!=v: raise E(f"phase-10 {k}")
    source=a.get("source_commit"); lock=a.get("toolchain_lock_sha256")
    if not isinstance(source,str) or len(source)!=40 or not isinstance(lock,str) or len(lock)!=64: raise E("phase identity")
    names=[f"P10.{n:02d}.{action}.json" for n in range(1,37) for action in ("build","test")]+["P10.36.result.json"]
    if a.get("required_records")!=names: raise E("required-record ordering")
    manifest=a.get("record_sha256")
    if not isinstance(manifest,dict) or set(manifest)!=set(names): raise E("manifest keys")
    for n in range(1,37):
        step=f"P10.{n:02d}"
        for action in ("build","test"):
            name=f"{step}.{action}.json"; p=CERT/name
            if not p.is_file(): raise E(f"missing {name}")
            r=load(p)
            if r.get("step")!=step or r.get("action")!=action or r.get("status")!="PASS" or r.get("worktree_clean") is not True: raise E(f"{name}: PASS")
            if r.get("architecture_sha256")!=ARCH or r.get("implementation_plan_sha256")!=PLAN or r.get("prerequisites")!=pre(n): raise E(f"{name}: identity")
            if not isinstance(r.get("toolchain_lock_sha256"),str): raise E(f"{name}: toolchain provenance")
            if n==36 and r.get("toolchain_lock_sha256")!=lock: raise E(f"{name}: P10.36 toolchain")
            rs=r.get("source_commit")
            if not isinstance(rs,str) or subprocess.run(["git","merge-base","--is-ancestor",rs,source],cwd=ROOT,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode: raise E(f"{name}: ancestry")
            if n==36 and rs!=source: raise E(f"{name}: source")
            if manifest.get(name)!=sha(p): raise E(f"{name}: bytes")
    res=load(CERT/"P10.36.result.json")
    for k,v in {"step":"P10.36","action":"result","status":"PASS","pass_marker":P1036,"source_commit":source,
                "architecture_sha256":ARCH,"implementation_plan_sha256":PLAN,"toolchain_lock_sha256":lock,
                "worktree_clean":True,"prerequisites":{"P10.35":"PASS"}}.items():
        if res.get(k)!=v: raise E(f"P10.36.result {k}")
    if manifest.get("P10.36.result.json")!=sha(CERT/"P10.36.result.json"): raise E("P10.36.result bytes")
    req={"p10-36-build-test-result-pass","all-p10-01-through-p10-36-durable-evidence-pass",
         "rev16-rev07-authority-pass","phase10-record-manifest-byte-exact",
         "phase10-acceptance-bullets-pass","phase10-gate-stops-before-phase11"}
    got={x.get("name") for x in a.get("assertions",[]) if isinstance(x,dict) and x.get("passed") is True}
    if not req.issubset(got): raise E("aggregate assertions")
    return a

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--require-active",action="store_true"); args=ap.parse_args()
    try:
        act=activation()
        if act is None:
            if args.require_active: raise E("Phase-10 aggregate evidence has not been activated")
            print("ZX-UX PHASE 10 EVIDENCE PRE-ACTIVATION PASS"); return 0
        a=validate(); source=a["source_commit"]; parent=git("rev-parse",f"{act}^")
        if subprocess.run(["git","merge-base","--is-ancestor",source,parent],cwd=ROOT,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode: raise E("activation ancestry")
        if git("log","-1","--format=%s",act)!=PREFIX+source: raise E("activation message")
        changed=git("diff-tree","--no-commit-id","--name-only","-r",parent,act).splitlines()
        if changed!=["v1/dist/certification/phase-10.json"]: raise E("activation must be aggregate-only")
        original=subprocess.run(["git","show",f"{act}:v1/dist/certification/phase-10.json"],cwd=ROOT,capture_output=True).stdout
        if (CERT/"phase-10.json").read_bytes()!=original: raise E("aggregate changed after activation")
        print("ZX-UX PHASE 10 DURABLE EVIDENCE PASS"); return 0
    except Exception as exc:
        print(f"ZX-UX PHASE 10 EVIDENCE FAIL: {exc}",file=sys.stderr); return 1

if __name__=="__main__": raise SystemExit(main())
