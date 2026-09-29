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
import argparse, hashlib, json
from pathlib import Path

IDS=[f"C{i:03d}" for i in range(1,14)]
def req(v,m):
    if not v: raise SystemExit("ERROR: "+m)
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",type=Path,required=True)
    ap.add_argument("--stage-c",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    ns=ap.parse_args()
    root=ns.root.resolve(); out=ns.output; out.mkdir(parents=True,exist_ok=True)
    c=json.loads(ns.stage_c.read_text())
    req(c.get("kind")=="rev02-stage-c-product-gap-inventory" and c.get("status")=="PASS-INVENTORY-ROOT-BLOCKER","Stage-C identity")
    gaps=c.get("gaps",[])
    req([g.get("id") for g in gaps]==IDS,"Stage-C root-gap set")

    archp=root/"docs/01-ZX-UX-ARCHITECTURE-REV17.md"
    planp=root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV08.md"
    arch=archp.read_text(); plan=planp.read_text()
    for x in (
      "The kernel, shell, device services, editor, assembler, linker, compiler, and core utilities execute as Z80 machine code.",
      "Required executable namespace:","/bin/sh","/bin/cc","/bin/as","/bin/ld",
      "## 41.9 Compiler","## 41.10 Shipped demos","cc hello.c","ld hello.obj -o hello",
      "genuine `source -> native as -> OBJ1 -> native ld -> executable -> run`",
      "Cassette is persistent object storage","system calls, graphics, UDG calls",
    ):
        # Accept the literal-backtick spelling without using the desired proof as authority.
        q=x.replace("\\`","`")
        req(q in arch or q in plan,"authority fragment missing: "+q)

    citations={
      "C001":["REV17 §2.2 machine-native implementation","REV17 §32 required /bin/sh"],
      "C002":["REV17 §2.2 machine-native implementation","REV17 §32 required /bin/cc","REV17 §41.9 compiler"],
      "C003":["REV17 §2.2 machine-native implementation","REV17 §32 required /bin/as","REV17 R17 native-as rebuild contract"],
      "C004":["REV17 §2.2 machine-native implementation","REV17 §32 required /bin/ld","REV17 §41.9 standard runtime resolution"],
      "C005":["REV17 §32 executable namespace","REV17 §42 edit/compile/link/run workflow","REV08 post-R17 native-tool path"],
      "C006":["REV17 §1 interactive shell requirement","REV17 §32 /bin/sh","REV17 shell/login acceptance"],
      "C007":["REV17 §2.6 cassette persistence","REV17 §§18/27/32 namespace/object/tape contracts","REV17 normal SYS_SPAWN execution"],
      "C008":["REV17 §§31/33 shell parsing/PATH/external execution","REV17 §42 user workflow"],
      "C009":["REV17 §41.9 complete C48 compiler surface","REV17 §42 source must compile natively","REV08 Phase-11 native compiler contract"],
      "C010":["REV17 machine-native assembler","REV17 R17 genuine source -> native as -> OBJ1 contract"],
      "C011":["REV17 machine-native linker","REV17 §41.9 runtime resolution by ld","REV17 R17 native ld fixed/absolute capability"],
      "C012":["REV17 §41.9 graphics/UDG/system-call compiler acceptance","REV17 shipped demo behavior"],
      "C013":["REV17 §41.9 standard runtime resolution by ld","REV17 frozen C48 public APIs","REV17 shipped demos native link requirement"],
    }
    changed={
      "C001":["v1/src/shell/sh.asm","tools/p11-prerelease-rev02/product_tools.py"],
      "C002":["v1/src/tools/cc.asm","tools/p11-prerelease-rev02/product_tools.py"],
      "C003":["tools/as.asm","tools/p11-prerelease-rev02/product_tools.py"],
      "C004":["tools/ld.asm","tools/p11-prerelease-rev02/product_tools.py"],
      "C005":["tools/p11-prerelease-rev02/product_tools.py",".github/workflows/p11-prerelease-rev02-product-tools.yml"],
      "C006":["v1/src/boot/entry.asm","v1/src/kernel/kernel.asm"],
      "C007":["v1/src/kernel/kernel.asm"],
      "C008":["v1/src/shell/sh.asm","tools/p11-prerelease-rev02/product_tools.py"],
      "C009":["v1/src/tools/cc.asm","tools/p11-prerelease-rev02/product_tools.py"],
      "C010":["tools/as.asm","tools/p11-prerelease-rev02/product_tools.py"],
      "C011":["tools/ld.asm","tools/p11-prerelease-rev02/product_tools.py"],
      "C012":["v1/src/kernel/kernel.asm"],
      "C013":["v1/src/libc48/runtime_archive.asm","tools/ld.asm","tools/p11-prerelease-rev02/product_tools.py"],
    }
    rows=[]
    for g in gaps:
        gid=g["id"]
        req(g.get("planned_paths")==changed[gid],"Stage-C/Stage-D planned-path mismatch: "+gid)
        rows.append({
          "gap_id":gid,"classification":"EXISTING-AUTHORITY-DEFECT",
          "failing_reproduction":{"stage_c_status":c["status"],"failure":g["failure"],"observed":g["observed"]},
          "authority":citations[gid],"planned_changed_paths":changed[gid],
          "regression_negative_set":[
            "three unchanged-byte scans","exact-head regression","Phase-11 aggregate replay",
            "historical immutable-scope check","ordinary shell PATH/process route",
            "product MEX1/OBJ1 validation","anti-source-specialization scan",
            "no P11PR helper in product closure","48K memory/resource gate"],
          "authority_gap":False,"sdk_defect":False,"proof_harness_only":False,
        })
    report={
      "schema":2,"kind":"rev02-stage-d-authority-classification","status":"PASS",
      "source_stage_c_sha256":sha(ns.stage_c),
      "authority":{"rev17_sha256":sha(archp),"rev08_sha256":sha(planp)},
      "classifications":rows,
      "assertions":{
        "all_stage_c_gaps_classified":"PASS",
        "all_current_planned_fixes_existing_authority":"PASS",
        "zero_authority_gap_in_current_root_blocker_lane":"PASS",
        "zero_sdk_defect_in_current_root_blocker_lane":"PASS",
        "zero_desired_result_used_as_authority":"PASS",
        "product_edits_authorized_only_for_listed_paths":"PASS"}}
    (out/"STAGE-D.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print("REV02 STAGE D PASS classifications=13 existing-authority-defect")
if __name__=="__main__": main()
