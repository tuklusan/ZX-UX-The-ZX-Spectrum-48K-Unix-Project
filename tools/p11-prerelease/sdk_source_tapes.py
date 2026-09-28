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

"""Verify the exact SDK 1.0.2 example/demo source-TAP corpus for Stage F."""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
from pathlib import Path
import sys

import sdk_acquire as sdk

def fail(message: str) -> None:
    raise SystemExit("ERROR: " + message)

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",type=Path,required=True)
    ap.add_argument("--report",type=Path,required=True)
    a=ap.parse_args()
    root=a.root
    release=json.loads((root/"SDK-RELEASE.json").read_text(encoding="utf-8"))
    manifest=json.loads((root/"compiler/source_tape_manifest.json").read_text(encoding="utf-8"))
    if release.get("tag")!=sdk.TAG or release.get("commit")!=sdk.COMMIT or release.get("tree")!=sdk.TREE:
        fail("SDK release identity drift")
    tapes=manifest.get("tapes")
    if manifest.get("tape_count")!=57 or not isinstance(tapes,list) or len(tapes)!=57:
        fail("source tape manifest must declare exactly 57 tapes")
    by={row.get("output"):row for row in tapes}
    sys.path.insert(0,str(root/"compiler"))
    builder=importlib.import_module("c48srctap")
    rows=[]
    seen=set()
    for category,name in sdk.programs():
        source_rel=f"usr/src/{category}/{name}.c"
        tape_rel=f"usr/bin/{category}/{name}.src.tap"
        item=by.get(tape_rel)
        if not item:
            fail("missing in-scope canonical tape: "+tape_rel)
        canonical=(root/tape_rel).read_bytes()
        decoded=sdk.decode(canonical)
        got={x[0]:x for x in decoded}
        source_name,target_obj,target_exe=sdk.target_names(name)
        expected_sources=item.get("sources")
        if not isinstance(expected_sources,list) or len(expected_sources)!=2:
            fail("in-scope source tape must contain exactly header+C source: "+tape_rel)
        rebuilt_inputs=[]
        name_overrides=[]
        object_rows=[]
        for src in expected_sources:
            rel=src.get("path"); target=src.get("name")
            if not isinstance(rel,str) or not isinstance(target,str):
                fail("invalid source tape manifest row: "+tape_rel)
            p=root/rel
            if not p.is_file():
                fail("retained exact SDK source missing: "+rel)
            payload=p.read_bytes()
            obj=got.get(target)
            if obj is None or obj[2]!=5 or obj[3]!=payload:
                fail("canonical tape does not reconstruct retained SDK bytes: "+rel)
            expected_type=5 if rel.endswith(".c") else 1
            if obj[1]!=expected_type:
                fail("canonical tape object type mismatch: "+rel)
            rebuilt_inputs.append(str(p))
            if Path(rel).name!=target:
                name_overrides.append([str(p),target])
            object_rows.append({"sdk_path":rel,"target_name":target,"type":obj[1],
                                "size":len(payload),"sha256":sha(payload)})
        if source_name not in got or got[source_name][3]!=(root/source_rel).read_bytes():
            fail("canonical C source identity mismatch: "+source_rel)
        specs=builder.collect_sources(rebuilt_inputs,name_overrides)
        regenerated=builder.build_tape(specs)
        if regenerated!=canonical:
            fail("pinned c48srctap regeneration differs from release tape: "+tape_rel)
        for target in (source_name,target_obj,target_exe):
            if not 1<=len(target.encode("ascii"))<=10:
                fail("derived target name outside ZX-UX namespace: "+target)
        if target_exe in seen:
            fail("derived executable target-name collision: "+target_exe)
        seen.add(target_exe)
        rows.append({
            "category":category,"program":name,"sdk_source_path":source_rel,
            "source_sha256":sha((root/source_rel).read_bytes()),
            "source_tape_path":tape_rel,"source_tape_size":len(canonical),
            "source_tape_sha256":sha(canonical),"target_source":source_name,
            "target_object":target_obj,"target_executable":target_exe,
            "objects":object_rows,"independent_decode":"PASS",
            "pinned_builder_regeneration":"PASS"})
    if len(rows)!=30 or len(seen)!=30:
        fail("exact 30-program Stage-F corpus not established")
    report={
        "schema":1,"kind":"phase11-pre-release-sdk-source-tape-corpus",
        "sdk":{"tag":sdk.TAG,"commit":sdk.COMMIT,"tree":sdk.TREE},
        "source_tape_manifest_count":57,"in_scope_program_count":30,
        "programs":rows,
        "assertions":{
            "exact_release_tapes_retained":"PASS",
            "all_tap_rom_m48o_checksums_and_crcs_verified":"PASS",
            "all_header_and_c_payloads_byte_identical":"PASS",
            "all_objects_target_userhome":"PASS",
            "all_types_exact_txt_or_c":"PASS",
            "pinned_c48srctap_regeneration_byte_identical":"PASS",
            "target_names_collision_free_and_at_most_10_bytes":"PASS",
        }}
    a.report.parent.mkdir(parents=True,exist_ok=True)
    a.report.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8",newline="\n")
    print("P11 PRE-RELEASE STAGE F PASS")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
