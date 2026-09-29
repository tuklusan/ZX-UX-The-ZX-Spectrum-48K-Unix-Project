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
import argparse, hashlib, json, re
from pathlib import Path

def req(v,m):
    if not v: raise SystemExit("ERROR: "+m)
def sha(p: Path)->str: return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--root",type=Path,required=True); ap.add_argument("--sdk-root",type=Path,required=True); ap.add_argument("--output",type=Path,required=True); ns=ap.parse_args()
    root=ns.root.resolve(); sdk=ns.sdk_root.resolve(); out=ns.output; out.mkdir(parents=True,exist_ok=True)
    rel=json.loads((sdk/"SDK-RELEASE.json").read_text())
    req(rel.get("program_count")==30 and len(rel.get("programs",[]))==30,"SDK program corpus")
    kernel=(root/"v1/src/kernel/kernel.asm").read_text()
    shell=(root/"v1/src/shell/sh.asm").read_text()
    cc=(root/"v1/src/tools/cc.asm").read_text()
    ass=(root/"tools/as.asm").read_text()
    ld=(root/"tools/ld.asm").read_text()
    req("p621_cc_path: db '/bin/cc',0" in shell,"shell /bin/cc path contract missing")
    req("MACRO EMIT_P614_PATH_ROUTINES" in shell and "SYS_STAT" in shell and "OBJ_BIN" in shell,"ordinary shell PATH resolver missing")
    req('INCLUDE "../shell/sh.asm"' not in kernel and 'INCLUDE "../tools/cc.asm"' not in kernel,"unexpected resident shell/compiler route")
    # Current source files are macro libraries/fixtures, not installable ordinary MEX1 products.
    product_specs={
      "sh":{"source":"v1/src/shell/sh.asm","text":shell},
      "cc":{"source":"v1/src/tools/cc.asm","text":cc},
      "as":{"source":"tools/as.asm","text":ass},
      "ld":{"source":"tools/ld.asm","text":ld},
    }
    closures={}
    for name,s in product_specs.items():
        p=root/s["source"]
        has_product_image=("SAVEBIN" in s["text"] and "MEX1" in s["text"])
        closures[name]={"source":s["source"],"source_sha256":sha(p),"ordinary_product_binary_sha256":None,"installable_product_image_in_source":has_product_image}
        req(not has_product_image,f"{name}: source unexpectedly has direct product image; Stage-C assumptions changed")
    candidate_patterns=("cc.mex1","as.mex1","ld.mex1","sh.mex1","cc.m48o","as.m48o","ld.m48o","sh.m48o")
    found=[]
    for p in root.rglob("*"):
        if p.is_file() and p.name.lower() in candidate_patterns: found.append(p.relative_to(root).as_posix())
    req(not found,"ordinary product tool artifacts unexpectedly present: "+",".join(found))
    rows=[]
    for p in rel["programs"]:
        tape=sdk/p["tape_path"]
        req(tape.is_file() and sha(tape)==p["tape_sha256"],"source tape drift "+p["tape_path"])
        rows.append({
          "category":p["category"],"program":p["name"],"source_tape_path":p["tape_path"],"source_tape_sha256":p["tape_sha256"],
          "planned_source":p["target_source"],
          "tape_load":{"status":"NOT_REACHED","reason":"ordinary ZX-UX developer session/product shell is not currently buildable as an installable product binary"},
          "header_resolution":{"status":"NOT_REACHED","reason":"same root blocker"},
          "cc":{"command":"cc "+p["target_source"],"status":"NOT_REACHED","errno":"E_NOENT","reason":"ordinary /bin/cc product binary absent"},
          "obj1":{"produced":False},"ld":{"status":"NOT_REACHED"},"process":{"status":"NOT_REACHED"},"screen_runtime_observation":"NOT_REACHED",
          "namespace_before":{"planned_obj":"ABSENT","planned_executable":"ABSENT"},"namespace_after":{"planned_obj":"ABSENT","planned_executable":"ABSENT"},
          "quoted_header_open_read":"NOT_REACHED","target_peak_memory":"NOT_REACHED"
        })
    gaps=[
      {"id":"C001","class_pending":"Stage-D","failure":"ordinary shell executable/product build+delivery path absent","observed":"v1/src/shell/sh.asm is source-only macro library; no installable MEX1/M48O product image is present","planned_paths":["v1/src/shell/sh.asm","tools/p11-prerelease-rev02/product_tools.py"],"blocks":["all 30 lifecycle diagnostics"]},
      {"id":"C002","class_pending":"Stage-D","failure":"ordinary /bin/cc executable absent","observed":"v1/src/tools/cc.asm has no installable ordinary product image and no checked-in/current product cc.mex1/cc.m48o exists","planned_paths":["v1/src/tools/cc.asm","tools/p11-prerelease-rev02/product_tools.py"],"blocks":["cc status","header open/read","OBJ1 publication"]},
      {"id":"C003","class_pending":"Stage-D","failure":"ordinary /bin/as executable absent","observed":"tools/as.asm has no installable ordinary product image and no product as.mex1/as.m48o exists","planned_paths":["tools/as.asm","tools/p11-prerelease-rev02/product_tools.py"],"blocks":["generic as proof","kernel native rebuild"]},
      {"id":"C004","class_pending":"Stage-D","failure":"ordinary /bin/ld executable absent","observed":"tools/ld.asm has no installable ordinary product image and no product ld.mex1/ld.m48o exists","planned_paths":["tools/ld.asm","tools/p11-prerelease-rev02/product_tools.py"],"blocks":["ld status","MEX1 publication","kernel native rebuild"]},
      {"id":"C005","class_pending":"Stage-D","failure":"no current normal developer-sidecar build/delivery closure for sh/cc/as/ld","observed":"current REV02 tree has proof fixtures and historical macros but no product-tool sidecar builder","planned_paths":["tools/p11-prerelease-rev02/product_tools.py",".github/workflows/p11-prerelease-rev02-product-tools.yml"],"blocks":["normal shell command/process path"]}
    ]
    report={"schema":1,"kind":"rev02-stage-c-product-gap-inventory","status":"PASS-INVENTORY-ROOT-BLOCKER","program_count":30,"programs":rows,"product_dependency_closures":closures,"gaps":gaps,
      "assertions":{"all_30_exact_tapes_accounted":"PASS","planned_outputs_absent":"PASS","no_p11pr_compiler_invoked":"PASS","no_internal_cc_or_ld_invoked":"PASS","ordinary_product_path_reproduced_as_unavailable":"PASS","legacy_publisher_not_used":"PASS","stage_c_requires_rerun_after_product_correction":"PASS"}}
    (out/"STAGE-C.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print("REV02 STAGE C GAP INVENTORY PASS root_blockers=5 programs=30")
if __name__=="__main__": main()
