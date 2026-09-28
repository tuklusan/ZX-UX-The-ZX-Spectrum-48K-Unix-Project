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

"""Stage exact SDK 1.0.2 provenance and native Gate-G artifacts into the candidate bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

import sdk_acquire as sdk


class Error(RuntimeError):
    pass


def req(value: object, message: str) -> None:
    if not value:
        raise Error(message)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def copy(src: Path, dst: Path) -> None:
    req(src.is_file() and not src.is_symlink(), f"missing regular source: {src}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--native", type=Path, required=True)
    ap.add_argument("--source-tape-report", type=Path, required=True)
    ap.add_argument("--native-report", type=Path, required=True)
    ap.add_argument("--process-report", type=Path, required=True)
    ap.add_argument("--cc-preflight-report", type=Path, required=True)
    ap.add_argument("--ld-preflight-report", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    release = json.loads((args.root / "SDK-RELEASE.json").read_text(encoding="utf-8"))
    req(
        (release.get("tag"), release.get("commit"), release.get("tree"))
        == (sdk.TAG, sdk.COMMIT, sdk.TREE),
        "SDK identity drift",
    )
    req(release.get("program_count") == 30, "SDK program count drift")

    source_tape = json.loads(args.source_tape_report.read_text(encoding="utf-8"))
    native = json.loads(args.native_report.read_text(encoding="utf-8"))
    process = json.loads(args.process_report.read_text(encoding="utf-8"))
    req(source_tape.get("in_scope_program_count") == 30, "source-tape report count")
    req(native.get("program_count") == 30, "native report count")
    req(process.get("program_count") == 30, "process report count")

    out = args.output / "sdk"
    shutil.rmtree(out, ignore_errors=True)

    copy(args.root / "SDK-RELEASE.json", out / "SDK-RELEASE.json")
    copy(args.root / "compiler/source_tape_manifest.json", out / "SOURCE-TAPE-MANIFEST.json")
    copy(args.root / "TARGET-NAME-MAP.json", out / "TARGET-NAME-MAP.json")

    for header in sdk.HEADERS:
        copy(args.root / header, out / "sources/headers" / Path(header).name)

    native_rows = {(r["category"], r["program"]): r for r in native["programs"]}
    process_rows = {(r["category"], r["program"]): r for r in process["programs"]}
    req(len(native_rows) == len(process_rows) == 30, "native/process matrix cardinality")

    matrix = []
    for category, name in sdk.programs():
        source_name, obj_name, exe_name = sdk.target_names(name)
        source_rel = Path("usr/src") / category / f"{name}.c"
        tape_rel = Path("usr/bin") / category / f"{name}.src.tap"
        src = args.root / source_rel
        tape = args.root / tape_rel
        obj = args.native / category / obj_name
        exe = args.native / category / exe_name
        nr = native_rows[(category, name)]
        pr = process_rows[(category, name)]

        req(nr["target_source"] == source_name, f"{category}/{name} target source drift")
        req(nr["target_object"] == obj_name, f"{category}/{name} target object drift")
        req(nr["target_executable"] == exe_name, f"{category}/{name} target executable drift")
        req(pr["target_executable"] == exe_name, f"{category}/{name} process executable drift")
        req(sha(obj) == nr["native_obj1_sha256"], f"{category}/{name} OBJ1 hash drift")
        req(sha(exe) == nr["native_mex1_sha256"] == pr["native_mex1_sha256"], f"{category}/{name} MEX1 hash drift")

        copy(src, out / "sources" / category / src.name)
        copy(tape, out / "tapes" / category / tape.name)
        copy(obj, out / "native" / category / obj.name)
        copy(exe, out / "native" / category / exe.name)
        copy(args.root / f"docs/images/{category}/{name}.png", out / "reference-lfs" / category / f"{name}.png")
        copy(args.root / f"reference-png/{category}/{name}.png", out / "reference-png" / category / f"{name}.png")

        matrix.append({
            "category": category,
            "program": name,
            "sdk_source_path": source_rel.as_posix(),
            "source_sha256": sha(src),
            "source_tape_path": tape_rel.as_posix(),
            "source_tape_sha256": sha(tape),
            "target_source": source_name,
            "target_object": obj_name,
            "native_obj1_size": obj.stat().st_size,
            "native_obj1_sha256": sha(obj),
            "target_executable": exe_name,
            "native_mex1_size": exe.stat().st_size,
            "native_mex1_sha256": sha(exe),
            "spawn": pr["spawn"],
            "process_started": pr["process_started"],
            "sys_exit_reached": pr["sys_exit_reached"],
            "reference_lfs_oid_sha256": next(
                p["reference_lfs_oid_sha256"] for p in release["programs"]
                if p["category"] == category and p["name"] == name
            ),
            "reference_png_sha256": sha(args.root / f"reference-png/{category}/{name}.png"),
        })

    copy(args.source_tape_report, out / "proof/source-tape-corpus.json")
    copy(args.native_report, out / "proof/native-build.json")
    copy(args.process_report, out / "proof/process-run.json")
    copy(args.cc_preflight_report, out / "proof/native-cc-preflight.json")
    copy(args.ld_preflight_report, out / "proof/native-ld-preflight.json")

    files = []
    for p in sorted(x for x in out.rglob("*") if x.is_file()):
        if p.name == "PROVENANCE.json":
            continue
        files.append({
            "path": p.relative_to(out).as_posix(),
            "size": p.stat().st_size,
            "sha256": sha(p),
        })
    provenance = {
        "schema": 1,
        "kind": "phase11-pre-release-sdk-staged-bundle",
        "sdk": {"tag": sdk.TAG, "commit": sdk.COMMIT, "tree": sdk.TREE},
        "program_count": 30,
        "programs": matrix,
        "assertions": {
            "exact_30_sources_retained": "PASS",
            "exact_30_release_source_tapes_retained": "PASS",
            "all_30_native_obj1_retained": "PASS",
            "all_30_native_mex1_retained": "PASS",
            "all_30_spawn_process_proofs_retained": "PASS",
            "all_30_reference_lfs_pointers_retained": "PASS",
            "all_30_reference_png_payloads_retained": "PASS",
        },
        "files": files,
    }
    (out / "PROVENANCE.json").write_text(
        json.dumps(provenance, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    req(len(matrix) == 30, "staged matrix count")
    req(len(list((out / "tapes").rglob("*.src.tap"))) == 30, "staged tape count")
    req(len([p for p in (out / "native").rglob("*") if p.is_file()]) == 60, "staged native artifact count")
    req(len(list((out / "reference-lfs").rglob("*.png"))) == 30, "staged LFS pointer count")
    req(len(list((out / "reference-png").rglob("*.png"))) == 30, "staged reference PNG count")
    print("P11 PRE-RELEASE SDK CANDIDATE STAGING PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
