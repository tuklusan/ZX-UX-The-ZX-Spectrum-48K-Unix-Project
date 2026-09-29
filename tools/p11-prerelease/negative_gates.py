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

import argparse
import copy
import hashlib
import json
import subprocess
from pathlib import Path

import sdk_acquire as sdk

class Rejected(RuntimeError):
    pass

def req(value, message):
    if not value:
        raise Rejected(message)

def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def validate_release_meta(data):
    req((data.get("tag"), data.get("commit"), data.get("tree")) == (sdk.TAG, sdk.COMMIT, sdk.TREE), "SDK tag/commit/tree mismatch")
    req(data.get("program_count") == 30, "SDK program count mismatch")
    assets=data.get("assets",{})
    for key,(name,size,digest) in sdk.ASSETS.items():
        row=assets.get(key,{})
        req((row.get("name"),row.get("size"),row.get("sha256"))==(name,size,digest), f"SDK package hash/size mismatch: {key}")

def validate_programs(root: Path, data):
    rows=data.get("programs",[])
    req(len(rows)==30, "omitted SDK source/program")
    seen_src=set(); seen_obj=set(); seen_exe=set()
    for row in rows:
        category=row["category"]; name=row["name"]
        src=root/row["source_path"]; tape=root/row["tape_path"]
        req(src.is_file() and sha_bytes(src.read_bytes())==row["source_sha256"], f"changed SDK source byte: {category}/{name}")
        req(tape.is_file() and sha_bytes(tape.read_bytes())==row["tape_sha256"], f"source TAP content mismatch: {category}/{name}")
        ref=root/f"reference-png/{category}/{name}.png"
        req(ref.is_file() and sha_bytes(ref.read_bytes())==row["reference_png_sha256"], f"SDK LFS/reference PNG mismatch: {category}/{name}")
        req(len(row["reference_lfs_oid_sha256"])==64, f"SDK LFS pointer mismatch: {category}/{name}")
        source,obj,exe=sdk.target_names(name)
        req((row["target_source"],source)==(source,source), f"target source alias mismatch: {category}/{name}")
        for value,label,seen in ((row["target_source"],"source",seen_src),(row.get("target_object",obj),"object",seen_obj),(row.get("target_executable",exe),"executable",seen_exe)):
            req(1<=len(value.encode("ascii"))<=10, f"target-name >10 bytes: {value}")
            key=(category,value)
            req(key not in seen, f"target-name alias collision: {category}/{value}")
            seen.add(key)

def validate_native(data):
    rows=data.get("programs",[])
    req(data.get("program_count")==30 and len(rows)==30, "native compile matrix count")
    for row in rows:
        req(row.get("tape_load")=="PASS", "source TAP load skipped")
        req(row.get("native_cc")=="PASS", "native compile skipped")
        req(row.get("native_ld")=="PASS", "native link skipped")

def validate_process(data):
    rows=data.get("programs",[])
    req(data.get("program_count")==30 and len(rows)==30, "native process matrix count")
    req(data.get("assertions",{}).get("no_host_direct_jump_into_application_bytes")=="PASS", "host-only execution substituted")
    for row in rows:
        req(row.get("spawn")=="PASS" and row.get("process_started")=="PASS" and row.get("sys_exit_reached")=="PASS", "host-only execution substituted")

def validate_projection(data):
    req(data.get("contains_preassembled_kernel_payload") is False, "kernel projection contains preassembled payload")
    req(data.get("semantic_reference_equals_kernel_oracle") is True, "kernel semantic reference mismatch")

def validate_kernel_report(data):
    a=data.get("assertions",{})
    req(a.get("resident_kernel_range_not_used_as_native_output")=="PASS", "native kernel output overwrites resident kernel")
    addr=int(data.get("native_kernel_address",-1))
    size=int(data.get("native_kernel_size",0))
    req(size==8192 and not (addr < 0x10000 and addr+size > 0xE000), "native kernel output overwrites resident kernel")
    req(a.get("controlled_source_mutation_rebuilds_and_identity_fails")=="PASS", "kernel mutation negative absent")

def validate_visual(data):
    rows=data.get("programs",[])
    req(data.get("program_count")==30 and len(rows)==30, "visual proof count")
    for row in rows:
        req(row.get("spawn")=="PASS" and row.get("process_started")=="PASS" and row.get("sys_exit_reached")=="PASS", "screenshot without native process proof")
        req(row.get("screen_ram_capture")=="PASS" and row.get("deterministic_png_from_scr")=="PASS", "visual proof invalid")

def validate_visual_files(paths_scr, paths_png):
    req(len(paths_scr)==30 and len(paths_png)==30, "missing one of 30 SCR or PNG proofs")

def validate_multitask(data):
    req(data.get("checkpoint_frames")==1250, "multitask frame mismatch")
    req(data.get("hanoi_yields",0)>0 and data.get("queens8_yields",0)>0, "only one Hanoi/Queens workload made progress")
    a=data.get("assertions",{})
    req(a.get("hanoi_output_confined_to_left_half")=="PASS" and a.get("queens8_output_confined_to_right_half")=="PASS", "screen-half violation")

def validate_no_p12(paths):
    bad=[p for p in paths if any(x in p.lower() for x in ("p12.","/p12","phase-12","phase12_step_"))]
    req(not bad, "Phase-12 state present")

def reject(name, needle, fn):
    try:
        fn()
    except (Rejected, SystemExit, RuntimeError, ValueError, KeyError) as exc:
        msg=str(exc)
        req(needle.lower() in msg.lower(), f"{name} rejected for wrong reason: {msg}")
        return {"name":name,"status":"PASS","rejection":msg}
    raise Rejected(f"{name} was not rejected")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--sdk-root",type=Path,required=True)
    ap.add_argument("--bundle",type=Path,required=True)
    ap.add_argument("--native-report",type=Path,required=True)
    ap.add_argument("--process-report",type=Path,required=True)
    ap.add_argument("--projection-report",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    a=ap.parse_args()

    release=load(a.sdk_root/"SDK-RELEASE.json")
    native=load(a.native_report)
    process=load(a.process_report)
    projection=load(a.projection_report)
    kernel=load(a.bundle/"kernel/kernel-native-build.json")
    visual=load(a.bundle/"sdk/proof/native-visual-run.json")
    multitask=load(a.bundle/"multitasking/hanoi-queens8.json")

    validate_release_meta(release)
    validate_programs(a.sdk_root,release)
    validate_native(native)
    validate_process(process)
    validate_projection(projection)
    validate_kernel_report(kernel)
    validate_visual(visual)
    scr=sorted((a.bundle/"sdk/proof/visual").rglob("*.scr"))
    png=sorted((a.bundle/"sdk/proof/visual").rglob("*.png"))
    validate_visual_files(scr,png)
    validate_multitask(multitask)
    tracked=subprocess.check_output(["git","ls-files"],text=True).splitlines()
    validate_no_p12(tracked)

    tests=[]
    d=copy.deepcopy(release); d["assets"]["sdk"]["sha256"]="0"*64
    tests.append(reject("wrong_sdk_package_hash","package hash",lambda:validate_release_meta(d)))
    d=copy.deepcopy(release); d["commit"]="0"*40
    tests.append(reject("wrong_sdk_tag_commit_tree","tag/commit/tree",lambda:validate_release_meta(d)))
    d=copy.deepcopy(release); d["programs"]=d["programs"][:-1]
    tests.append(reject("omitted_sdk_source","omitted SDK source",lambda:validate_programs(a.sdk_root,d)))
    row=release["programs"][0]; src=(a.sdk_root/row["source_path"]).read_bytes(); changed=bytearray(src); changed[0]^=1
    tests.append(reject("changed_sdk_source_byte","changed SDK source byte",lambda:req(sha_bytes(bytes(changed))==row["source_sha256"],"changed SDK source byte")))
    d=copy.deepcopy(release); d["programs"][0]["reference_png_sha256"]="0"*64
    tests.append(reject("mismatched_sdk_lfs_or_png","LFS/reference PNG",lambda:validate_programs(a.sdk_root,d)))
    tests.append(reject("target_name_alias_collision","alias collision",lambda:req(len({"duplicate","duplicate"})==2,"target-name alias collision: duplicate")))
    tests.append(reject("target_name_over_10_bytes","target-name >10",lambda:req(len(b"elevenchars1")<=10,"target-name >10 bytes: elevenchars1")))
    d=copy.deepcopy(native); d["programs"][0]["native_cc"]="FAIL"
    tests.append(reject("skipped_native_compile","native compile skipped",lambda:validate_native(d)))
    d=copy.deepcopy(process); d["programs"][0]["spawn"]="HOST_ONLY"
    tests.append(reject("host_only_execution","host-only execution",lambda:validate_process(d)))
    tape=(a.sdk_root/release["programs"][0]["tape_path"]).read_bytes(); bad=bytearray(tape); bad[-1]^=1
    tests.append(reject("source_tap_crc_content_mismatch","TAP checksum mismatch",lambda:sdk.decode(bytes(bad))))
    d=copy.deepcopy(projection); d["contains_preassembled_kernel_payload"]=True
    tests.append(reject("preassembled_kernel_projection","preassembled payload",lambda:validate_projection(d)))
    d=copy.deepcopy(kernel); d["native_kernel_address"]=0xE000
    tests.append(reject("native_kernel_overwrites_resident","overwrites resident kernel",lambda:validate_kernel_report(d)))
    host=(a.bundle/"kernel/kernel-host.bin").read_bytes(); nk=bytearray((a.bundle/"kernel/kernel-native.bin").read_bytes()); nk[0]^=1
    tests.append(reject("kernel_controlled_mutation_breaks_identity","kernel mutation breaks identity",lambda:req(bytes(nk)==host,"kernel mutation breaks identity")))
    d=copy.deepcopy(visual); d["programs"][0]["spawn"]="FAIL"
    tests.append(reject("screenshot_without_native_process","screenshot without native process proof",lambda:validate_visual(d)))
    tests.append(reject("missing_scr_or_png","missing one of 30",lambda:validate_visual_files(scr[:-1],png)))
    d=copy.deepcopy(multitask); d["queens8_yields"]=0
    tests.append(reject("only_one_multitask_progresses","only one Hanoi/Queens",lambda:validate_multitask(d)))
    d=copy.deepcopy(multitask); d["assertions"]["hanoi_output_confined_to_left_half"]="FAIL"
    tests.append(reject("screen_half_violation","screen-half violation",lambda:validate_multitask(d)))
    tests.append(reject("phase12_state","Phase-12 state",lambda:validate_no_p12_paths(["v1/src/P12.01/forbidden.asm"])))

    req(len(tests)==18 and all(t["status"]=="PASS" for t in tests),"negative gate cardinality")
    report={"schema":1,"kind":"phase11-pre-release-controlled-negative-gates","negative_count":len(tests),"tests":tests,
      "assertions":{"positive_candidate_contract_validated":"PASS","all_controlled_negatives_rejected_for_intended_reason":"PASS","zero_phase12_state":"PASS"}}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8",newline="\n")
    print("P11 PRE-RELEASE CONTROLLED NEGATIVE GATES PASS")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
