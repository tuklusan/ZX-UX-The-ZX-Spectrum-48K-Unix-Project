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
import argparse, hashlib, importlib.util, json, sys
from pathlib import Path

ARCH_SHA="1d736641e685c1d6136b66fc57d0c16fc662ce6ca4dfd640991743bb01bb706f"
class FinalizeError(RuntimeError): pass

def sha(path:Path)->str: return hashlib.sha256(path.read_bytes()).hexdigest()
def load(path:Path):
    value=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value,dict): raise FinalizeError(f"{path.name}: object required")
    return value
def write(path:Path,value:dict): path.write_text(json.dumps(value,indent=2,sort_keys=True)+"\n",encoding="utf-8",newline="\n")
def driver_names(): return [f"{p}.{n:02d}.{a}.json" for p,m in (("E0",6),("P0",34)) for n in range(1,m+1) for a in ("build","test")]
def validator(root:Path):
    path=root/"v1/tools-host/test-driver/evidence.py"; spec=importlib.util.spec_from_file_location("zxux_evidence_validator",path)
    if spec is None or spec.loader is None: raise FinalizeError("cannot load evidence validator")
    module=importlib.util.module_from_spec(spec); sys.modules[spec.name]=module; spec.loader.exec_module(module); return module

def result_record(step:str,source:dict,prereq:dict[str,str]):
    return {"schema":2,"step":step,"action":"result","status":"PASS","pass_marker":f"ZX-UX {step} CERTIFICATION PASS","source_commit":source["source_commit"],"toolchain_lock_sha256":source["toolchain_lock_sha256"],"architecture_sha256":source["architecture_sha256"],"worktree_clean":True,"prerequisites":prereq,"commands":[],"hashes":dict(source.get("hashes",{})),"assertions":[{"name":"build-record-pass","passed":True},{"name":"test-record-pass","passed":True},{"name":"same-clean-source","passed":True}]}

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument("--root",required=True); ap.add_argument("--evidence-dir",required=True); args=ap.parse_args()
    try:
        root=Path(args.root).resolve(); evidence=Path(args.evidence_dir).resolve()
        try: evidence.relative_to(root)
        except ValueError: pass
        else: raise FinalizeError("evidence staging must be outside source worktree")
        v=validator(root); records={}; sources=set(); locks=set(); archs=set()
        for name in driver_names():
            path=evidence/name
            if not path.is_file(): raise FinalizeError(f"missing driver evidence: {name}")
            record=load(path); v.validate_driver_record(record)
            if record.get("status")!="PASS" or record.get("worktree_clean") is not True: raise FinalizeError(f"{name}: not clean PASS")
            records[name]=record; sources.add(record.get("source_commit")); locks.add(record.get("toolchain_lock_sha256")); archs.add(record.get("architecture_sha256"))
        if len(sources)!=1 or len(locks)!=1 or archs!={ARCH_SHA}: raise FinalizeError("evidence does not name one exact source/toolchain/architecture state")
        boundaries=(("E0.04.result.json",result_record("E0.04",records["E0.04.test.json"],{"E0.03":"PASS"})),("P0.34.result.json",result_record("P0.34",records["P0.34.test.json"],{"P0.33":"PASS"})))
        for name,record in boundaries: v.validate_final_record(record); write(evidence/name,record)
        required=driver_names()+[x[0] for x in boundaries]
        aggregate={"schema":2,"phase":0,"action":"phase-result","status":"PASS","pass_marker":"ZX-UX PHASE 0 CERTIFICATION PASS","source_commit":next(iter(sources)),"toolchain_lock_sha256":next(iter(locks)),"architecture_sha256":ARCH_SHA,"worktree_clean":True,"required_records":required,"record_sha256":{name:sha(evidence/name) for name in required},"assertions":[{"name":"all-e0-build-test-pass","passed":True},{"name":"all-p0-build-test-pass","passed":True},{"name":"e0-04-result-pass","passed":True},{"name":"p0-34-result-pass","passed":True},{"name":"single-clean-source","passed":True},{"name":"exact-toolchain-lock","passed":True},{"name":"exact-architecture-digest","passed":True}]}
        write(evidence/"phase-0.json",aggregate); print("ZX-UX PHASE 0 EVIDENCE FINALIZATION PASS"); return 0
    except Exception as exc:
        print(f"ZX-UX PHASE 0 EVIDENCE FINALIZATION FAIL: {exc}",file=sys.stderr); return 1
if __name__=="__main__": raise SystemExit(main())
