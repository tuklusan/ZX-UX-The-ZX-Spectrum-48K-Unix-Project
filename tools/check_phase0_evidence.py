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
import argparse, hashlib, importlib.util, json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CERT = ROOT / "v1/dist/certification"
ARCH_SHA = "ea23eb1c4815490830325b235e885d11b475a27ce6dcb9c70f4716d5c604fea0"
LOCK_PATH = "tools/manifest/toolchain.lock.json"
ARCH_PATH = "docs/01-ZX-UX-ARCHITECTURE-REV12.md"

class CertificationError(RuntimeError): pass

def git(*args: str) -> str:
    p=subprocess.run(["git",*args],cwd=ROOT,text=True,capture_output=True,check=False)
    if p.returncode: raise CertificationError(f"git {' '.join(args)} failed: {p.stderr.strip()}")
    return p.stdout

def git_bytes(*args: str) -> bytes:
    p=subprocess.run(["git",*args],cwd=ROOT,capture_output=True,check=False)
    if p.returncode:
        message=p.stderr.decode("utf-8","replace").strip()
        raise CertificationError(f"git {' '.join(args)} failed: {message}")
    return p.stdout

def sha_bytes(value: bytes)->str: return hashlib.sha256(value).hexdigest()
def sha(path: Path)->str: return sha_bytes(path.read_bytes())

def names()->list[str]:
    result=[f"{p}.{n:02d}.{a}.json" for p,m in (("E0",6),("P0",34)) for n in range(1,m+1) for a in ("build","test")]
    return result+["E0.04.result.json","P0.34.result.json"]

def validator():
    path=ROOT/"v1/tools-host/test-driver/evidence.py"
    spec=importlib.util.spec_from_file_location("zxux_evidence_validator",path)
    if spec is None or spec.loader is None: raise CertificationError("cannot load evidence validator")
    module=importlib.util.module_from_spec(spec); sys.modules[spec.name]=module; spec.loader.exec_module(module); return module

def load(path: Path):
    try: value=json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc: raise CertificationError(f"malformed evidence {path.name}: {exc}") from exc
    if not isinstance(value,dict): raise CertificationError(f"{path.name}: JSON object required")
    return value

def activation()->str|None:
    commits=[x for x in git("log","--format=%H","--","v1/dist/certification/phase-0.json").splitlines() if x]
    return commits[0] if commits else None

def validate_activation(act: str, source: str)->None:
    parent=git("rev-parse",f"{act}^").strip()
    if parent!=source:
        raise CertificationError("latest Phase-0 activation is not a direct child of its certified source")
    subject=git("log","-1","--format=%s",act).strip()
    if subject!=f"R&R-06 activate Phase-0 certification evidence for {source}":
        raise CertificationError("latest Phase-0 activation commit message/source mismatch")
    changed=[p for p in git("diff-tree","--no-commit-id","--name-only","-r",parent,act).splitlines() if p]
    if not changed or any(not (p.startswith("v1/dist/certification/") and p.endswith(".json")) for p in changed):
        raise CertificationError("latest Phase-0 activation is not evidence-only")

def validate_historical_activation_unchanged(act: str, aggregate: dict)->None:
    source=aggregate.get("source_commit")
    if not isinstance(source,str):
        raise CertificationError("historical Phase-0 aggregate has invalid source identity")
    if sha(ROOT/ARCH_PATH) != ARCH_SHA:
        raise CertificationError("current architecture bytes do not match the frozen rebaseline digest")
    if subprocess.run(["git","merge-base","--is-ancestor",act,"HEAD"],cwd=ROOT,capture_output=True).returncode:
        raise CertificationError("historical Phase-0 activation is not an ancestor of HEAD")
    validate_activation(act,source)
    required=aggregate.get("required_records")
    if not isinstance(required,list) or any(not isinstance(name,str) for name in required):
        raise CertificationError("historical Phase-0 aggregate has invalid required_records")
    paths=["phase-0.json",*required]
    for name in paths:
        path=CERT/name
        if not path.is_file():
            raise CertificationError(f"historical durable evidence missing during rebaseline: {name}")
        if path.read_bytes()!=git_bytes("show",f"{act}:v1/dist/certification/{name}"):
            raise CertificationError(f"historical durable evidence changed during rebaseline: {name}")

def validate_source_identity(source: str, lock: str)->None:
    if len(source)!=40 or any(ch not in "0123456789abcdef" for ch in source):
        raise CertificationError("invalid certified source")
    if len(lock)!=64 or any(ch not in "0123456789abcdef" for ch in lock):
        raise CertificationError("invalid toolchain digest")
    p=subprocess.run(["git","merge-base","--is-ancestor",source,"HEAD"],cwd=ROOT,capture_output=True)
    if p.returncode: raise CertificationError("certified source is not an ancestor of HEAD")
    if sha_bytes(git_bytes("show",f"{source}:{LOCK_PATH}"))!=lock:
        raise CertificationError("toolchain digest does not match certified source bytes")
    if sha_bytes(git_bytes("show",f"{source}:{ARCH_PATH}"))!=ARCH_SHA:
        raise CertificationError("architecture digest does not match certified source bytes")

def validate_complete():
    v=validator(); aggregate_path=CERT/"phase-0.json"
    if not aggregate_path.is_file(): raise CertificationError("phase-0.json missing after activation")
    agg=load(aggregate_path)
    exact={"schema":2,"phase":0,"action":"phase-result","status":"PASS","worktree_clean":True,"architecture_sha256":ARCH_SHA,"pass_marker":"ZX-UX PHASE 0 CERTIFICATION PASS"}
    for key,value in exact.items():
        if agg.get(key)!=value: raise CertificationError(f"phase-0.json {key} mismatch")
    source=agg.get("source_commit"); lock=agg.get("toolchain_lock_sha256")
    if not isinstance(source,str) or not isinstance(lock,str): raise CertificationError("invalid certified source/toolchain identity")
    validate_source_identity(source,lock)
    required=names(); manifest=agg.get("record_sha256")
    if agg.get("required_records")!=required: raise CertificationError("phase-0 required_records mismatch")
    if not isinstance(manifest,dict) or set(manifest)!=set(required): raise CertificationError("phase-0 record manifest mismatch")
    records={}
    for name in required:
        path=CERT/name
        if not path.is_file(): raise CertificationError(f"missing durable evidence: {name}")
        record=load(path)
        (v.validate_final_record if name.endswith(".result.json") else v.validate_driver_record)(record)
        if record.get("status")!="PASS" or record.get("worktree_clean") is not True: raise CertificationError(f"{name}: non-clean/non-PASS")
        if record.get("source_commit")!=source: raise CertificationError(f"{name}: wrong source commit")
        if record.get("toolchain_lock_sha256")!=lock: raise CertificationError(f"{name}: wrong toolchain digest")
        if record.get("architecture_sha256")!=ARCH_SHA: raise CertificationError(f"{name}: wrong architecture digest")
        if manifest.get(name)!=sha(path): raise CertificationError(f"{name}: bytes differ from aggregate manifest")
        records[(str(record.get("step")),str(record.get("action")))]=record
    for (step,_),record in records.items():
        for prereq,status in record.get("prerequisites",{}).items():
            if status!="PASS" or not any(k[0]==prereq and r.get("status")=="PASS" for k,r in records.items()):
                raise CertificationError(f"{step}: invalid prerequisite {prereq}")
    return agg

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument("--require-active",action="store_true"); args=ap.parse_args()
    try:
        act=activation()
        if act is None:
            if args.require_active: raise CertificationError("Phase-0 evidence has not been activated")
            print("ZX-UX PHASE 0 EVIDENCE PRE-ACTIVATION PASS"); return 0

        # During an architecture rebaseline the previous durable evidence remains
        # immutable historical evidence until the certification workflow publishes
        # a new evidence-only child commit.  A normal CI read must recognize that
        # controlled transition instead of misclassifying the old architecture's
        # still-valid records as corrupt current evidence.  --require-active stays
        # fail-closed so no consumer can claim the new architecture is certified
        # before its matching activation exists.
        aggregate_path=CERT/"phase-0.json"
        if aggregate_path.is_file():
            aggregate=load(aggregate_path)
            if aggregate.get("architecture_sha256") != ARCH_SHA:
                validate_historical_activation_unchanged(act,aggregate)
                if args.require_active:
                    raise CertificationError("Phase-0 evidence has not been activated for the current architecture")
                print("ZX-UX PHASE 0 EVIDENCE PRE-ACTIVATION PASS"); return 0

        agg=validate_complete()
        source=agg.get("source_commit")
        if not isinstance(source,str): raise CertificationError("invalid certified source")
        validate_activation(act,source)
        original_bytes=git_bytes("show",f"{act}:v1/dist/certification/phase-0.json")
        if (CERT/"phase-0.json").read_bytes()!=original_bytes:
            raise CertificationError("durable Phase-0 aggregate changed after latest activation")
        original=json.loads(original_bytes)
        if agg.get("record_sha256")!=original.get("record_sha256"):
            raise CertificationError("durable Phase-0 evidence manifest changed after latest activation")
        print("ZX-UX PHASE 0 DURABLE EVIDENCE PASS"); return 0
    except Exception as exc:
        print(f"ZX-UX PHASE 0 EVIDENCE FAIL: {exc}",file=sys.stderr); return 1
if __name__=="__main__": raise SystemExit(main())
