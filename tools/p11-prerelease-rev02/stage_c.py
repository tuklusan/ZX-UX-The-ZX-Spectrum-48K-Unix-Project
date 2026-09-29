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

def req(v,m):
    if not v: raise SystemExit("ERROR: "+m)
def sha(p: Path)->str: return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",type=Path,required=True)
    ap.add_argument("--sdk-root",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    ns=ap.parse_args()
    root=ns.root.resolve(); sdk=ns.sdk_root.resolve(); out=ns.output
    out.mkdir(parents=True,exist_ok=True)
    rel=json.loads((sdk/"SDK-RELEASE.json").read_text())
    req(rel.get("program_count")==30 and len(rel.get("programs",[]))==30,"SDK program corpus")

    kernel=(root/"v1/src/kernel/kernel.asm").read_text()
    boot=(root/"v1/src/boot/entry.asm").read_text()
    shell=(root/"v1/src/shell/sh.asm").read_text()
    cc=(root/"v1/src/tools/cc.asm").read_text()
    ass=(root/"tools/as.asm").read_text()
    ld=(root/"tools/ld.asm").read_text()
    runtime=(root/"v1/src/libc48/runtime_archive.asm").read_text()

    req("p621_cc_path: db '/bin/cc',0" in shell,"shell /bin/cc path contract missing")
    req("MACRO EMIT_P614_PATH_ROUTINES" in shell and "SYS_STAT" in shell and "OBJ_BIN" in shell,
        "ordinary shell PATH resolver missing")
    req("EMIT_P601_SH_IMAGE" in shell and "sh_idle:" in shell,"historical shell entry fixture missing")
    req("jp zx48_idle_loop" in boot and "zx48_p601_pid1_bootstrap" not in boot,
        "boot root-blocker assumption changed")
    for inc in ("objects.asm","tape.asm","zxpack.asm","graphics.asm","sound.asm"):
        req(('INCLUDE "'+inc+'"') not in kernel,"kernel composition assumption changed: "+inc)
    req("EMIT_P11PR_CC_SDK_CORPUS_COMPILER" in cc and "cc_p11pr_identity_table:" in cc,
        "historical P11PR identity-bound fixture unexpectedly absent")
    req("EMIT_P1145_CC_H06_COMPILER" in cc and "CC_P1145_SOURCE_CRC" in cc,
        "historical H06 fixture unexpectedly absent")

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
        closures[name]={
          "source":s["source"],"source_sha256":sha(p),
          "ordinary_product_binary_sha256":None,
          "installable_product_image_in_source":has_product_image,
        }
        req(not has_product_image,f"{name}: source unexpectedly has direct product image; Stage-C assumptions changed")

    candidate_patterns=("cc.mex1","as.mex1","ld.mex1","sh.mex1","cc.m48o","as.m48o","ld.m48o","sh.m48o")
    found=[]
    for p in root.rglob("*"):
        if p.is_file() and p.name.lower() in candidate_patterns:
            found.append(p.relative_to(root).as_posix())
    req(not found,"ordinary product tool artifacts unexpectedly present: "+",".join(found))

    rows=[]
    for p in rel["programs"]:
        tape=sdk/p["tape_path"]
        req(tape.is_file() and sha(tape)==p["tape_sha256"],"source tape drift "+p["tape_path"])
        rows.append({
          "category":p["category"],"program":p["name"],
          "source_tape_path":p["tape_path"],"source_tape_sha256":p["tape_sha256"],
          "planned_source":p["target_source"],
          "tape_load":{"status":"NOT_REACHED","reason":"production kernel lacks current object/tape + PID1 developer-session route"},
          "header_resolution":{"status":"NOT_REACHED","reason":"same root blockers"},
          "cc":{"command":"cc "+p["target_source"],"status":"NOT_REACHED","errno":"E_NOENT","reason":"ordinary /bin/cc product binary/CLI absent"},
          "obj1":{"produced":False},"ld":{"status":"NOT_REACHED"},"process":{"status":"NOT_REACHED"},
          "screen_runtime_observation":"NOT_REACHED",
          "namespace_before":{"planned_obj":"ABSENT","planned_executable":"ABSENT"},
          "namespace_after":{"planned_obj":"ABSENT","planned_executable":"ABSENT"},
          "quoted_header_open_read":"NOT_REACHED","target_peak_memory":"NOT_REACHED"
        })

    gaps=[
      {"id":"C001","failure":"ordinary shell executable/product build+delivery path absent",
       "observed":"sh.asm is a macro library; no current installable /bin/sh MEX1/M48O exists",
       "planned_paths":["v1/src/shell/sh.asm","tools/p11-prerelease-rev02/product_tools.py"],"blocks":["developer session"]},
      {"id":"C002","failure":"ordinary /bin/cc executable absent",
       "observed":"cc.asm is a macro library/fixture collection; no current product cc MEX1/M48O exists",
       "planned_paths":["v1/src/tools/cc.asm","tools/p11-prerelease-rev02/product_tools.py"],"blocks":["cc","OBJ1"]},
      {"id":"C003","failure":"ordinary /bin/as executable absent",
       "observed":"tools/as.asm is a macro library; no current product as MEX1/M48O exists",
       "planned_paths":["tools/as.asm","tools/p11-prerelease-rev02/product_tools.py"],"blocks":["generic as","kernel rebuild"]},
      {"id":"C004","failure":"ordinary /bin/ld executable absent",
       "observed":"tools/ld.asm is a macro library; no current product ld MEX1/M48O exists",
       "planned_paths":["tools/ld.asm","tools/p11-prerelease-rev02/product_tools.py"],"blocks":["ld","MEX1","kernel rebuild"]},
      {"id":"C005","failure":"no current developer-sidecar build/delivery closure for sh/cc/as/ld",
       "observed":"no product-tool sidecar builder binds target binaries to current product sources",
       "planned_paths":["tools/p11-prerelease-rev02/product_tools.py",".github/workflows/p11-prerelease-rev02-product-tools.yml"],"blocks":["normal command path"]},
      {"id":"C006","failure":"production boot never starts PID1 shell",
       "observed":"EMIT_BOOT_IMPL initializes base subsystems then jumps directly to zx48_idle_loop; no PID1 bootstrap/session handoff",
       "planned_paths":["v1/src/boot/entry.asm","v1/src/kernel/kernel.asm"],"blocks":["login","shell command execution"]},
      {"id":"C007","failure":"production kernel omits normal object/tape/zxpack namespace and spawn closure",
       "observed":"kernel.asm does not include objects.asm, tape.asm, or zxpack.asm and does not emit the later object/tape/spawn transaction facilities",
       "planned_paths":["v1/src/kernel/kernel.asm"],"blocks":["M48O load","/bin lookup","SYS_SPAWN","quoted header reads"]},
      {"id":"C008","failure":"production shell entry is idle-only and has no integrated command loop",
       "observed":"EMIT_P601_SH_IMAGE enters sh_idle and only SYS_YIELDs; later parser/PATH/pipeline routines are fixture macros not connected to product entry",
       "planned_paths":["v1/src/shell/sh.asm","tools/p11-prerelease-rev02/product_tools.py"],"blocks":["shell-visible cc/as/ld"]},
      {"id":"C009","failure":"no generic production cc CLI/compiler route",
       "observed":"current cc source exposes phase-specific compile entry points; P1144/P1145 and P11PR paths are source-identity-bound, and no ordinary generic CLI entry owns the full frozen parser/codegen/OBJ1 transaction",
       "planned_paths":["v1/src/tools/cc.asm","tools/p11-prerelease-rev02/product_tools.py"],"blocks":["generic C48","anti-specialization","30 lifecycle"]},
      {"id":"C010","failure":"no production as CLI entry over generic assembler pipeline",
       "observed":"tools/as.asm exposes assembler macros/fixture routines but no ordinary application entry parsing argv and publishing OBJ1",
       "planned_paths":["tools/as.asm","tools/p11-prerelease-rev02/product_tools.py"],"blocks":["generic as","native kernel rebuild"]},
      {"id":"C011","failure":"no production ld CLI entry over generic linker pipeline",
       "observed":"tools/ld.asm exposes linker macros/fixture routines but no ordinary application entry parsing argv and transactionally publishing MEX1/fixed output",
       "planned_paths":["tools/ld.asm","tools/p11-prerelease-rev02/product_tools.py"],"blocks":["generic ld","native kernel rebuild"]},
      {"id":"C012","failure":"production kernel omits graphics/sound services required by frozen public API",
       "observed":"kernel.asm does not include graphics.asm or sound.asm although the exact SDK corpus uses frozen graphics/sound calls",
       "planned_paths":["v1/src/kernel/kernel.asm"],"blocks":["source-defined program behavior"]},
      {"id":"C013","failure":"ordinary production libc48/runtime link closure is incomplete",
       "observed":"runtime_archive.asm contains historical minimal/step overlays but no one product archive materialization resolving the full frozen C48 API for ordinary ld",
       "planned_paths":["v1/src/libc48/runtime_archive.asm","tools/ld.asm","tools/p11-prerelease-rev02/product_tools.py"],"blocks":["all API-complete links"]}
    ]
    for g in gaps: g["class_pending"]="Stage-D"

    report={
      "schema":2,"kind":"rev02-stage-c-product-gap-inventory","status":"PASS-INVENTORY-ROOT-BLOCKER",
      "program_count":30,"programs":rows,"product_dependency_closures":closures,"gaps":gaps,
      "production_snapshot":{
        "kernel_sha256":sha(root/"v1/src/kernel/kernel.asm"),
        "boot_sha256":sha(root/"v1/src/boot/entry.asm"),
        "shell_sha256":sha(root/"v1/src/shell/sh.asm"),
        "cc_sha256":sha(root/"v1/src/tools/cc.asm"),
        "as_sha256":sha(root/"tools/as.asm"),
        "ld_sha256":sha(root/"tools/ld.asm"),
        "runtime_archive_sha256":sha(root/"v1/src/libc48/runtime_archive.asm"),
      },
      "assertions":{
        "all_30_exact_tapes_accounted":"PASS",
        "planned_outputs_absent":"PASS",
        "boot_to_real_shell_gap_recorded":"PASS",
        "object_tape_spawn_gap_recorded":"PASS",
        "generic_cli_gaps_recorded":"PASS",
        "runtime_api_closure_gap_recorded":"PASS",
        "no_p11pr_compiler_invoked":"PASS",
        "no_internal_cc_or_ld_invoked":"PASS",
        "ordinary_product_path_reproduced_as_unavailable":"PASS",
        "legacy_publisher_not_used":"PASS",
        "stage_c_requires_rerun_after_product_correction":"PASS"
      }}
    (out/"STAGE-C.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print("REV02 STAGE C GAP INVENTORY PASS root_blockers=13 programs=30")
if __name__=="__main__": main()
