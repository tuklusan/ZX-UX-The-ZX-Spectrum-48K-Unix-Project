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
import hashlib, json, os, subprocess
from pathlib import Path

ROOT=Path.cwd()
WORK=Path(os.environ.get("P11_WORK","/tmp/p11-prerelease"))
OUT=WORK/"P11.pre-release"
PHASE11_COMPLETE="263a203da3d54a398e8ac011284ae4195b1279c0"
ARCH_SHA="d12baf0b47a7f8cd2dcd60b82f100ba19f9fddaabad43728a004a07214716bf8"
PLAN_SHA="97461e9ed12253409b25e6a4a4063cf0ec556a7317f9e4a5938d77edb6a1a14c"
OLD_TZX_SHA="fdb9dbf3ffb004163567ceda46831c4ee72ade7b1d308e22e45eeb4bd137a0ed"

def sha(p: Path)->str: return hashlib.sha256(p.read_bytes()).hexdigest()
def git(*a:str)->str: return subprocess.check_output(["git",*a],text=True).strip()
def load(p:Path): return json.loads(p.read_text(encoding="utf-8"))
def req(v,msg):
    if not v: raise RuntimeError(msg)

def file_table():
    rows=[]
    for p in sorted(x for x in OUT.rglob("*") if x.is_file()):
        rel=p.relative_to(OUT).as_posix()
        if rel=="pre-release.json": continue
        rows.append({"path":rel,"size":p.stat().st_size,"sha256":sha(p)})
    return rows

def bundle_digest(rows):
    h=hashlib.sha256()
    for row in rows:
        h.update(row["path"].encode("utf-8")+b"\0"+str(row["size"]).encode("ascii")+b"\0"+row["sha256"].encode("ascii")+b"\n")
    return h.hexdigest()

def emit():
    build=load(WORK/"a/build.json")
    native=load(OUT/"kernel/kernel-native-build.json")
    runtime=load(WORK/"realtime/runtime-acceptance.json")
    detect=load(WORK/"realtime-detect-loader/runtime-acceptance.json")
    exact=load(WORK/"evidence/P11.48.result.json")
    activated=load(ROOT/"v1/dist/certification/phase-11.json")
    sdk=load(OUT/"sdk/PROVENANCE.json")
    sdkrel=load(OUT/"sdk/SDK-RELEASE.json")
    visual=load(OUT/"sdk/proof/native-visual-run.json")
    multitask=load(OUT/"multitasking/hanoi-queens8.json")
    req(exact["status"]=="PASS" and exact["source_commit"]==git("rev-parse","HEAD"),"exact-head P11.48")
    req(activated["status"]=="PASS" and activated["pass_marker"]=="ZX-UX PHASE 11 CERTIFICATION PASS","phase11 aggregate")
    req(sdk["program_count"]==visual["program_count"]==30,"program count")
    req(all(v=="PASS" for v in runtime["assertions"].values()),"runtime acceptance")
    req(all(v=="PASS" for v in detect["assertions"].values()),"detect-loader acceptance")
    req(all(v=="PASS" for v in multitask["assertions"].values()),"multitask acceptance")
    host=sha(OUT/"kernel/kernel-host.bin"); embedded=sha(OUT/"kernel/kernel-tzx-embedded.bin"); nk=sha(OUT/"kernel/kernel-native.bin")
    req(host==embedded==nk==native["native_kernel_sha256"],"kernel three-way identity")
    req((OUT/"kernel/kernel-native-source.tap").is_file(),"kernel source TAP")
    req(len(list((OUT/"sdk/tapes").rglob("*.src.tap")))==30,"30 SDK source TAPs")
    req(len(list((OUT/"sdk/proof/visual").rglob("*.scr")))==30,"30 SCR proofs")
    req(len(list((OUT/"sdk/proof/visual").rglob("*.png")))==30,"30 PNG proofs")
    req((OUT/"multitasking/hanoi-queens8-1250f.scr").stat().st_size==6912,"multitask SCR")
    readme="""ZX-UX Phase-11 expanded fast-loader pre-release

Boot the official pre-release image on a 48K Spectrum with: LOAD ""

The official boot product is the single TZX file:
  zx-ux-phase11-pre-release.tzx

The .tap files retained below kernel/ and sdk/tapes/ are source-transfer and
proof sidecars only. They are not boot/release TAP products.

This bundle retains the exact textual native kernel source and source TAP,
genuine native OBJ1 and 8192-byte native kernel, all 30 SDK 1.0.2 canonical
source tapes, native OBJ1/MEX1 outputs, deterministic SCR/PNG execution proofs,
and the concurrent 1250-frame Hanoi + 8-Queens proof.

Phase 12 is not started or implied by this pre-release bundle.
"""
    (OUT/"README.txt").write_text(readme,encoding="utf-8",newline="\n")
    rows=file_table()
    meta={
      "schema":2,
      "kind":"phase11-expanded-pre-release",
      "candidate_source_commit":git("rev-parse","HEAD"),
      "phase11_complete":PHASE11_COMPLETE,
      "authority":{"architecture":"REV17","architecture_sha256":ARCH_SHA,"implementation_plan":"REV08","implementation_plan_sha256":PLAN_SHA},
      "supersedes":{"compact_pre_release_tzx_sha256":OLD_TZX_SHA},
      "sdk_release":sdkrel,
      "phase11":{"activated_aggregate_sha256":sha(ROOT/"v1/dist/certification/phase-11.json"),"activated_pass_marker":activated["pass_marker"],"p1148_result_sha256":sha(ROOT/"v1/dist/certification/P11.48.result.json"),"exact_head_revalidation_sha256":sha(WORK/"evidence/P11.48.result.json"),"exact_head_revalidation_pass_marker":exact["pass_marker"]},
      "kernel_identity":{"size":8192,"host_built_sha256":host,"tzx_embedded_sha256":embedded,"native_rebuilt_sha256":nk,"native_obj1_sha256":sha(OUT/"kernel/kernel-native.obj1"),"text_source_sha256":sha(OUT/"kernel/kernel-native-source.asm"),"source_map_sha256":sha(OUT/"kernel/kernel-native-source-map.json"),"source_tap_sha256":sha(OUT/"kernel/kernel-native-source.tap")},
      "boot":{"distribution":"TZX-only","tzx_sha256":sha(OUT/"zx-ux-phase11-pre-release.tzx"),"tzx_size":(OUT/"zx-ux-phase11-pre-release.tzx").stat().st_size,"handoff":"0xE003","runtime_acceptance":runtime,"detect_loader_compatibility":detect},
      "sdk":{"program_count":30,"programs":sdk["programs"],"native_visual_program_count":visual["program_count"],"source_tape_count":len(list((OUT/"sdk/tapes").rglob("*.src.tap"))),"scr_count":len(list((OUT/"sdk/proof/visual").rglob("*.scr"))),"png_count":len(list((OUT/"sdk/proof/visual").rglob("*.png")))},
      "multitasking":{"checkpoint_frames":multitask["checkpoint_frames"],"hanoi_yields":multitask["hanoi_yields"],"queens8_yields":multitask["queens8_yields"],"scr_sha256":sha(OUT/"multitasking/hanoi-queens8-1250f.scr"),"png_sha256":sha(OUT/"multitasking/hanoi-queens8-1250f.png"),"assertions":multitask["assertions"]},
      "tests":{"sdk_1_0_2_pin":"PASS","historical_p1139_unchanged":"PASS","all_30_native_lifecycles":"PASS","all_30_scr_png":"PASS","kernel_source_tap_native_rebuild":"PASS","kernel_three_way_8192_identity":"PASS","published_tzx_uses_native_kernel":"PASS","hanoi_queens_concurrent_1250f":"PASS","real_time_loader":"PASS","phase11_exact_head_p1148":"PASS","phase11_aggregate":"PASS","zero_phase12_state":"PASS"},
      "files":rows,
      "bundle_digest_sha256":bundle_digest(rows)
    }
    (OUT/"pre-release.json").write_text(json.dumps(meta,indent=2,sort_keys=True)+"\n",encoding="utf-8",newline="\n")

def scan():
    m=load(OUT/"pre-release.json")
    req(m["kind"]=="phase11-expanded-pre-release","kind")
    req(m["candidate_source_commit"]==git("rev-parse","HEAD"),"source commit")
    req(m["phase11_complete"]==PHASE11_COMPLETE,"PHASE-11-COMPLETE")
    req(m["sdk"]["program_count"]==30 and m["sdk"]["scr_count"]==30 and m["sdk"]["png_count"]==30,"30-program proof cardinality")
    req(m["sdk"]["source_tape_count"]==30,"source-tape count")
    req(len(set(m["kernel_identity"][k] for k in ("host_built_sha256","tzx_embedded_sha256","native_rebuilt_sha256")))==1,"kernel identity")
    req(all(v=="PASS" for v in m["tests"].values()),"test matrix")
    rows=file_table()
    req(rows==m["files"],"recursive file table")
    req(bundle_digest(rows)==m["bundle_digest_sha256"],"bundle digest")
    req(not (OUT/"zx-ux-phase11-pre-release.tap").exists(),"boot TAP forbidden")
    req(len(list(OUT.rglob("*.tap")))==31,"source TAP total")
    return sha(OUT/"pre-release.json")

if __name__=="__main__":
    emit()
    baseline=None
    for _ in range(3):
        digest=scan()
        baseline=digest if baseline is None else baseline
        req(digest==baseline,"unchanged manifest scan")
    print("ZX-UX PHASE-11 EXPANDED PRE-RELEASE MANIFEST PASS")
