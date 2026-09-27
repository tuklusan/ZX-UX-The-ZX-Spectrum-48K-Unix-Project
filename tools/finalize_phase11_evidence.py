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

ARCH="d12baf0b47a7f8cd2dcd60b82f100ba19f9fddaabad43728a004a07214716bf8"
PLAN="97461e9ed12253409b25e6a4a4063cf0ec556a7317f9e4a5938d77edb6a1a14c"
P1148="ZX-UX PHASE 11 ACCEPTANCE PASS"
PHASE="ZX-UX PHASE 11 CERTIFICATION PASS"
class E(RuntimeError): pass
def load(p): return json.loads(p.read_text(encoding="utf-8"))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def pre(n): return {"R17.00":"PASS"} if n==1 else {f"P11.{n-1:02d}":"PASS"}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--root",required=True); ap.add_argument("--output",required=True); a=ap.parse_args()
    try:
        root=Path(a.root).resolve(); out=Path(a.output).resolve(); cert=root/"v1/dist/certification"
        res=load(cert/"P11.48.result.json"); source=res.get("source_commit")
        exact={"step":"P11.48","action":"result","status":"PASS","pass_marker":P1148,
               "architecture_sha256":ARCH,"implementation_plan_sha256":PLAN,
               "worktree_clean":True,"prerequisites":{"P11.47":"PASS"}}
        for k,v in exact.items():
            if res.get(k)!=v: raise E(f"P11.48.result {k}")
        if not isinstance(source,str) or len(source)!=40: raise E("P11.48 result source")
        phase_lock=res.get("toolchain_lock_sha256")
        if not isinstance(phase_lock,str) or len(phase_lock)!=64: raise E("P11.48 result toolchain")
        names=[]; manifest={}
        for n in range(1,49):
            step=f"P11.{n:02d}"
            for action in ("build","test"):
                name=f"{step}.{action}.json"; p=cert/name
                if not p.is_file(): raise E(f"missing {name}")
                r=load(p)
                if r.get("step")!=step or r.get("action")!=action or r.get("status")!="PASS" or r.get("worktree_clean") is not True:
                    raise E(f"{name}: clean PASS")
                if r.get("architecture_sha256")!=ARCH or r.get("implementation_plan_sha256")!=PLAN or r.get("prerequisites")!=pre(n):
                    raise E(f"{name}: authority/prereq")
                rs=r.get("source_commit")
                if not isinstance(rs,str) or subprocess.run(["git","merge-base","--is-ancestor",rs,source],cwd=root,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode:
                    raise E(f"{name}: source ancestry")
                if n==48 and rs!=source: raise E(f"{name}: P11.48 source mismatch")
                if not isinstance(r.get("toolchain_lock_sha256"),str): raise E(f"{name}: toolchain provenance")
                if n==48 and r.get("toolchain_lock_sha256")!=phase_lock: raise E(f"{name}: P11.48 toolchain")
                names.append(name); manifest[name]=sha(p)
        for name in ("P11.48.result.json","P11.48-sdk-admission.json"):
            p=cert/name
            if not p.is_file(): raise E(f"missing {name}")
            names.append(name); manifest[name]=sha(p)
        sdk=load(cert/"P11.48-sdk-admission.json")
        if sdk.get("step")!="P11.48" or sdk.get("status")!="PASS" or sdk.get("unresolved")!=[]:
            raise E("P11.48 SDK admission")
        h06=sdk.get("h06",{})
        if h06.get("pipeline")!="target-native cc -> OBJ1 -> target-native ld -> MEX1 -> execute" or h06.get("expected_status")!=0:
            raise E("P11.48 H06 lifecycle")
        got={x.get("name") for x in res.get("assertions",[]) if isinstance(x,dict) and x.get("passed") is True}
        required={
            "p11-01-through-p11-47-durable-evidence-clean-pass",
            "p11-24-edit-1b-break-separation-admitted",
            "baseline-sdk-tree-and-205-tests-byte-accounted",
            "no-imported-sdk-skip-xfail-or-weakened-intent",
            "all-sdk-expectations-have-native-owner-mapping",
            "docx-sdk-native-zero-unresolved-discrepancies",
            "complete-phase11-c-source-sdk-native-manifest",
            "h06-pinned-source-header-identities-exact",
            "h06-target-native-cc-obj1-ld-execute-proof-admitted",
            "h06-retained-sna-scr-png-fmf-visual-proof-present",
            "p11-40-through-p11-47-late-acceptance-areas-resolved",
            "negative-missing-source-sdk-test-unresolved-oracles-fail-closed",
            "exact-head-p11-45-transitive-native-compiler-matrix-pass",
            "exact-head-p11-46-fp-to-text-pass",
            "exact-head-p11-47-fp-from-text-pass",
            "p11-48-final-target-sna-execution-pass",
            "phase11-acceptance-stops-before-phase12",
            "same-clean-phase11-acceptance-source-candidate-all-records",
        }
        if not required.issubset(got): raise E("P11.48 acceptance assertions")
        tracked=subprocess.run(["git","ls-files"],cwd=root,text=True,capture_output=True,check=True).stdout.splitlines()
        forbidden=[p for p in tracked if p.startswith("v1/dist/certification/P12.") or p.startswith("v1/dist/media/P12.") or
                   p.startswith(".github/workflows/p12") or p.startswith("v1/tools-host/test-driver/phase12_step_")]
        if forbidden: raise E("Phase-12 state present: "+",".join(forbidden))
        agg={"schema":2,"phase":11,"action":"phase-result","status":"PASS","pass_marker":PHASE,
             "source_commit":source,"toolchain_lock_sha256":phase_lock,
             "architecture_sha256":ARCH,"implementation_plan_sha256":PLAN,"worktree_clean":True,
             "required_records":names,"record_sha256":manifest,
             "assertions":[
               {"name":"p11-48-build-test-result-pass","passed":True},
               {"name":"all-p11-01-through-p11-48-durable-evidence-pass","passed":True},
               {"name":"rev17-rev08-authority-pass","passed":True},
               {"name":"phase11-record-manifest-byte-exact","passed":True},
               {"name":"phase11-sdk-docx-native-h06-acceptance-pass","passed":True},
               {"name":"phase11-gate-stops-before-phase12","passed":True},
             ]}
        out.parent.mkdir(parents=True,exist_ok=True)
        out.write_text(json.dumps(agg,indent=2,sort_keys=True)+"\n",encoding="utf-8",newline="\n")
        print("ZX-UX PHASE 11 EVIDENCE FINALIZATION PASS"); return 0
    except Exception as exc:
        print(f"ZX-UX PHASE 11 EVIDENCE FINALIZATION FAIL: {exc}",file=sys.stderr); return 1

if __name__=="__main__": raise SystemExit(main())
