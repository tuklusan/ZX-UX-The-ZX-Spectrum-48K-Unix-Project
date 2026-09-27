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
ARCH="d12baf0b47a7f8cd2dcd60b82f100ba19f9fddaabad43728a004a07214716bf8"
PLAN="97461e9ed12253409b25e6a4a4063cf0ec556a7317f9e4a5938d77edb6a1a14c"
PREFIX="phase11: activate Phase-11 aggregate evidence for "
P1148="ZX-UX PHASE 11 ACCEPTANCE PASS"
PHASE="ZX-UX PHASE 11 CERTIFICATION PASS"

class E(RuntimeError): pass
def git(*a):
    r=subprocess.run(["git",*a],cwd=ROOT,text=True,capture_output=True)
    if r.returncode: raise E(r.stderr.strip() or r.stdout.strip())
    return r.stdout.strip()
def load(p): return json.loads(p.read_text(encoding="utf-8"))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def pre(n): return {"R17.00":"PASS"} if n==1 else {f"P11.{n-1:02d}":"PASS"}
def activation():
    xs=git("log","--format=%H","--","v1/dist/certification/phase-11.json").splitlines()
    return xs[0] if xs else None

def validate():
    a=load(CERT/"phase-11.json")
    for k,v in {"schema":2,"phase":11,"action":"phase-result","status":"PASS","pass_marker":PHASE,
                "worktree_clean":True,"architecture_sha256":ARCH,"implementation_plan_sha256":PLAN}.items():
        if a.get(k)!=v: raise E(f"phase-11 {k}")
    source=a.get("source_commit"); lock=a.get("toolchain_lock_sha256")
    if not isinstance(source,str) or len(source)!=40 or not isinstance(lock,str) or len(lock)!=64: raise E("phase identity")
    names=[f"P11.{n:02d}.{action}.json" for n in range(1,49) for action in ("build","test")]+["P11.48.result.json","P11.48-sdk-admission.json"]
    if a.get("required_records")!=names: raise E("required-record ordering")
    manifest=a.get("record_sha256")
    if not isinstance(manifest,dict) or set(manifest)!=set(names): raise E("manifest keys")
    for n in range(1,49):
        step=f"P11.{n:02d}"
        for action in ("build","test"):
            name=f"{step}.{action}.json"; p=CERT/name
            if not p.is_file(): raise E(f"missing {name}")
            r=load(p)
            if r.get("step")!=step or r.get("action")!=action or r.get("status")!="PASS" or r.get("worktree_clean") is not True:
                raise E(f"{name}: PASS")
            if r.get("architecture_sha256")!=ARCH or r.get("implementation_plan_sha256")!=PLAN or r.get("prerequisites")!=pre(n):
                raise E(f"{name}: identity")
            if not isinstance(r.get("toolchain_lock_sha256"),str): raise E(f"{name}: toolchain provenance")
            if n==48 and r.get("toolchain_lock_sha256")!=lock: raise E(f"{name}: P11.48 toolchain")
            rs=r.get("source_commit")
            if not isinstance(rs,str) or subprocess.run(["git","merge-base","--is-ancestor",rs,source],cwd=ROOT,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode:
                raise E(f"{name}: ancestry")
            if n==48 and rs!=source: raise E(f"{name}: source")
            if manifest.get(name)!=sha(p): raise E(f"{name}: bytes")
    res=load(CERT/"P11.48.result.json")
    for k,v in {"step":"P11.48","action":"result","status":"PASS","pass_marker":P1148,"source_commit":source,
                "architecture_sha256":ARCH,"implementation_plan_sha256":PLAN,"toolchain_lock_sha256":lock,
                "worktree_clean":True,"prerequisites":{"P11.47":"PASS"}}.items():
        if res.get(k)!=v: raise E(f"P11.48.result {k}")
    if manifest.get("P11.48.result.json")!=sha(CERT/"P11.48.result.json"): raise E("P11.48.result bytes")
    sdk=load(CERT/"P11.48-sdk-admission.json")
    if sdk.get("step")!="P11.48" or sdk.get("status")!="PASS" or sdk.get("unresolved")!=[]: raise E("P11.48 SDK admission")
    if manifest.get("P11.48-sdk-admission.json")!=sha(CERT/"P11.48-sdk-admission.json"): raise E("P11.48 SDK admission bytes")
    req={"p11-48-build-test-result-pass","all-p11-01-through-p11-48-durable-evidence-pass",
         "rev17-rev08-authority-pass","phase11-record-manifest-byte-exact",
         "phase11-sdk-docx-native-h06-acceptance-pass","phase11-gate-stops-before-phase12"}
    got={x.get("name") for x in a.get("assertions",[]) if isinstance(x,dict) and x.get("passed") is True}
    if not req.issubset(got): raise E("aggregate assertions")
    tracked=git("ls-files").splitlines()
    forbidden=[p for p in tracked if p.startswith("v1/dist/certification/P12.") or p.startswith("v1/dist/media/P12.") or
               p.startswith(".github/workflows/p12") or p.startswith("v1/tools-host/test-driver/phase12_step_")]
    if forbidden: raise E("Phase-12 state present")
    return a

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--require-active",action="store_true"); args=ap.parse_args()
    try:
        act=activation()
        if act is None:
            if args.require_active: raise E("Phase-11 aggregate evidence has not been activated")
            res=load(CERT/"P11.48.result.json")
            if res.get("status")!="PASS" or res.get("pass_marker")!=P1148: raise E("P11.48 acceptance missing")
            print("ZX-UX PHASE 11 EVIDENCE PRE-ACTIVATION PASS"); return 0
        a=validate(); source=a["source_commit"]; parent=git("rev-parse",f"{act}^")
        if subprocess.run(["git","merge-base","--is-ancestor",source,parent],cwd=ROOT,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode:
            raise E("activation ancestry")
        if git("log","-1","--format=%s",act)!=PREFIX+source: raise E("activation message")
        changed=git("diff-tree","--no-commit-id","--name-only","-r",parent,act).splitlines()
        if changed!=["v1/dist/certification/phase-11.json"]: raise E("activation must be aggregate-only")
        original=subprocess.run(["git","show",f"{act}:v1/dist/certification/phase-11.json"],cwd=ROOT,capture_output=True).stdout
        if (CERT/"phase-11.json").read_bytes()!=original: raise E("aggregate changed after activation")
        print("ZX-UX PHASE 11 DURABLE EVIDENCE PASS"); return 0
    except Exception as exc:
        print(f"ZX-UX PHASE 11 EVIDENCE FAIL: {exc}",file=sys.stderr); return 1

if __name__=="__main__": raise SystemExit(main())
