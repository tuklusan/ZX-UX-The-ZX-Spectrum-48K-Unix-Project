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
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

PHASE11 = "263a203da3d54a398e8ac011284ae4195b1279c0"
REV01_FAILED = "a20adeceade081f4dbe9c09a70b6528d17877205"
REV01_PARENT = "f6fe98b122d6207c67c0e6cb156135cf0a8856eb"
REV01_PATH = "scratch/ZX-UX-PHASE-11-PRE-RELEASE-RUNBOOK-REV01.md"
REV02_PATH = "scratch/ZX-UX-PHASE-11-PRE-RELEASE-RUNBOOK-REV02.md"
FAST_PATH = "scratch/ZX-UX-FAST-LOADER-TZX-RELEASE-MIGRATION-RUNBOOK-REV01.md"
FAILED_PUBLICATION_COMMIT = "ca3bede90247bb19570e9c994775c3ca0a9434f8"
FAILED_PUBLICATION_TREE = "6f3f7e3f310426e73cb54eeb6d86bf0b7664307f"
FAILED_BUNDLE_TREE = "a784cf8cd05f655bb7db8ef8cb5b971133995446"
P1139_TREE = "1c6b5bae84035ee853be9142b440792881c9ca9f"

AUTHORITY_PATHS = (
    "docs/03-ZX-UX-DEVELOPMENT-WORKFLOW.md",
    "docs/--W-A-R-N-I-N-G--.md",
    "docs/01-ZX-UX-ARCHITECTURE-REV17.md",
    "docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV08.md",
    "docs/04-C48 Language Specification Rev 0.11.docx",
    "docs/05-C48 Compiler User Manual Rev 0.11.docx",
    "v1/docs/c48.md",
    "v1/docs/abi.md",
    "v1/docs/assembler.md",
    "v1/docs/obj1.md",
    "v1/docs/mex1.md",
    "v1/docs/tape-object.md",
)

def run(*args: str, binary: bool = False) -> bytes | str:
    cp = subprocess.run(args, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return cp.stdout if binary else cp.stdout.decode("utf-8", "strict")

def req(ok: bool, msg: str) -> None:
    if not ok:
        raise SystemExit("ERROR: " + msg)

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def git_blob(ref: str, path: str) -> bytes:
    return run("git", "show", f"{ref}:{path}", binary=True)

def tree_entries(ref: str) -> dict[str, dict[str, object]]:
    raw = run("git", "ls-tree", "-r", "-l", "-z", ref, binary=True)
    out: dict[str, dict[str, object]] = {}
    for rec in raw.split(b"\0"):
        if not rec:
            continue
        meta, path_b = rec.split(b"\t", 1)
        mode, typ, sha, size = meta.decode("ascii").split()
        path = path_b.decode("utf-8")
        out[path] = {"mode": mode, "type": typ, "git_blob": sha, "size": int(size)}
    return out

def immutable_path(path: str) -> bool:
    if path.startswith("v1/dist/certification/"):
        return True
    if path.startswith("v1/dist/media/P11.pre-release/"):
        return False
    if re.match(r"^v1/dist/media/P(?:[0-9]|10|11)(?:[./]|$)", path):
        return True
    if re.match(r"^docs/01-ZX-UX-ARCHITECTURE-REV[0-9]+\.md$", path):
        return True
    if re.match(r"^docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV[0-9]+\.md$", path):
        return True
    return path in {
        "docs/03-ZX-UX-DEVELOPMENT-WORKFLOW.md",
        "docs/--W-A-R-N-I-N-G--.md",
    }

def recursive_identity(rows: list[dict[str, object]]) -> str:
    h = hashlib.sha256()
    for row in rows:
        h.update(
            (
                f"{row['path']}\0{row['mode']}\0{row['git_blob']}\0"
                f"{row['size']}\n"
            ).encode("utf-8")
        )
    return h.hexdigest()

def failed_bundle_digest(commit: str) -> tuple[str, int]:
    prefix = "v1/dist/media/P11.pre-release/"
    entries = tree_entries(commit)
    rows = []
    for path, meta in sorted(entries.items()):
        if not path.startswith(prefix) or meta["type"] != "blob":
            continue
        rel = path[len(prefix):]
        data = git_blob(commit, path)
        rows.append((rel, len(data), sha256_bytes(data)))
    req(rows, "failed REV01 bundle is empty")
    h = hashlib.sha256()
    for rel, size, digest in rows:
        h.update(rel.encode() + b"\0" + str(size).encode() + b"\0" + digest.encode() + b"\n")
    return h.hexdigest(), len(rows)

def grep_inventory() -> dict[str, object]:
    tracked = run("git", "ls-files").splitlines()
    roots = (".github/", "tools/", "v1/src/", "v1/tools-host/")
    files = [p for p in tracked if p.startswith(roots)]
    tokens = ("P11PR", "p11pr", "p11-prerelease")
    hits = []
    product_invocations = []
    prerelease_scripts = []
    for path in files:
        p = Path(path)
        if path.startswith("tools/p11-prerelease/") or (
            path.startswith(".github/workflows/") and "p11" in path.lower() and "release" in path.lower()
        ):
            prerelease_scripts.append(path)
        try:
            text = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for n, line in enumerate(text.splitlines(), 1):
            if any(t in line for t in tokens):
                hits.append({"path": path, "line": n, "text": line.strip()[:300]})
            if path.startswith("v1/src/") and "EMIT_P11PR" in line:
                stripped = line.strip()
                if "MACRO" not in stripped and not stripped.startswith(";"):
                    product_invocations.append({"path": path, "line": n, "text": stripped[:300]})
    return {
        "hits": hits,
        "pre_release_scripts_and_workflows": sorted(set(prerelease_scripts)),
        "product_emit_invocations": product_invocations,
        "product_emit_reachable": bool(product_invocations),
    }

def active_failed_publishers() -> list[str]:
    bad = []
    for path in run("git", "ls-files", ".github/workflows").splitlines():
        if not path.endswith((".yml", ".yaml")):
            continue
        text = Path(path).read_text(encoding="utf-8")
        write = bool(re.search(r"(?m)^\s*contents:\s*write\s*$", text))
        legacy = any(
            marker in text
            for marker in (
                "v1/dist/media/P11.pre-release/",
                "tools/p11-prerelease/build.sh",
                "tools/p11-prerelease/finalize.sh",
                "tools/p11-prerelease/publish.sh",
            )
        )
        if write and legacy:
            bad.append(path)
    return bad

def phase12_state_paths() -> list[str]:
    out = []
    for path in run("git", "ls-files").splitlines():
        low = path.lower()
        if (
            low.startswith("v1/dist/certification/p12")
            or low.startswith("v1/dist/media/p12")
            or low == "v1/dist/certification/phase-12.json"
            or low.startswith(".github/workflows/p12-")
            or re.search(r"(^|/)p12\.[0-9]", low)
        ):
            out.append(path)
    return out

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    head = run("git", "rev-parse", "HEAD").strip()
    tree = run("git", "rev-parse", "HEAD^{tree}").strip()
    expected_head = os.environ.get("GITHUB_SHA")
    if expected_head:
        req(head == expected_head, "workflow checkout is not exact GITHUB_SHA")

    req(run("git", "rev-parse", "PHASE-11-COMPLETE").strip() == PHASE11, "PHASE-11-COMPLETE moved")
    rev01_now = Path(REV01_PATH).read_bytes()
    req(run("git", "rev-parse", f"HEAD:{REV01_PATH}").strip() == run("git", "rev-parse", f"{REV01_FAILED}:{REV01_PATH}").strip(), "REV01 changed after FAILED-CLOSED checkpoint")
    rev01_old = git_blob(REV01_PARENT, REV01_PATH)
    old_status = b"**Status:** CLOSED"
    new_status = b"**Status:** FAILED-CLOSED"
    req(rev01_now.count(new_status) == 1, "REV01 FAILED-CLOSED status missing/ambiguous")
    req(rev01_old.count(old_status) == 1, "REV01 prior CLOSED status missing/ambiguous")
    req(rev01_now.replace(new_status, old_status, 1) == rev01_old, "REV01 is not status-only relative to failed-closure parent")

    req(b"**Status:** CLOSED" in Path(FAST_PATH).read_bytes(), "fast-loader migration runbook not CLOSED")
    rev02 = Path(REV02_PATH).read_text(encoding="utf-8")
    req("**Status:** OPEN" in rev02 and "DRAFT — REVIEW REQUIRED — DO NOT EXECUTE" not in rev02, "REV02 not OPEN")
    successors = sorted(run("git", "ls-files", "scratch/ZX-UX-PHASE-11-PRE-RELEASE-RUNBOOK-REV*.md").splitlines())
    req(successors == [REV01_PATH, REV02_PATH], "unexpected Phase-11 pre-release successor runbook")

    tag_entries = tree_entries(PHASE11)
    cur_entries = tree_entries("HEAD")
    immutable_rows = []
    drift = []
    for path, meta in sorted(tag_entries.items()):
        if meta["type"] != "blob" or not immutable_path(path):
            continue
        row = {"path": path, **meta}
        immutable_rows.append(row)
        now = cur_entries.get(path)
        if now != meta:
            drift.append({"path": path, "phase11": meta, "current": now})
    req(not drift, "admitted P0-P11 evidence/media or authority drift")
    immutable_digest = recursive_identity(immutable_rows)

    p1148_rows = [r for r in immutable_rows if r["path"].startswith("v1/dist/media/P11.48/") or r["path"].startswith("v1/dist/certification/P11.48") or r["path"] == "v1/dist/certification/phase-11.json"]
    req(p1148_rows, "P11.48/Phase-11 aggregate baseline set empty")
    p1148_digest = recursive_identity(p1148_rows)

    authority_hashes = []
    for path in AUTHORITY_PATHS:
        req(Path(path).is_file(), "missing authority/reconciliation input: " + path)
        authority_hashes.append({
            "path": path,
            "size": Path(path).stat().st_size,
            "sha256": sha256_file(path),
            "git_blob": run("git", "rev-parse", f"HEAD:{path}").strip(),
        })

    p1139 = run("git", "rev-parse", "HEAD:v1/tests/compiler/sdk-reference/sdk").strip()
    req(p1139 == P1139_TREE, "historical P11.39 SDK tree changed")
    req(run("git", "rev-parse", f"{PHASE11}:v1/tests/compiler/sdk-reference/sdk").strip() == P1139_TREE, "Phase-11 P11.39 anchor mismatch")

    req(run("git", "rev-parse", f"{FAILED_PUBLICATION_COMMIT}^{{tree}}").strip() == FAILED_PUBLICATION_TREE, "failed publication root tree mismatch")
    req(run("git", "rev-parse", f"{FAILED_PUBLICATION_COMMIT}:v1/dist/media/P11.pre-release").strip() == FAILED_BUNDLE_TREE, "failed publication bundle tree mismatch")
    failed_digest, failed_count = failed_bundle_digest(FAILED_PUBLICATION_COMMIT)

    p12 = phase12_state_paths()
    req(not p12, "Phase-12 state exists")
    publishers = active_failed_publishers()
    req(not publishers, "active write-capable failed REV01 publisher remains")

    inventory = grep_inventory()
    result = {
        "schema": 1,
        "kind": "phase11-pre-release-rev02-stage-a",
        "status": "PASS",
        "head": head,
        "tree": tree,
        "anchors": {
            "phase11_complete": PHASE11,
            "rev01_failed_closed_commit": REV01_FAILED,
            "rev01_failed_closed_blob": run("git", "rev-parse", f"{REV01_FAILED}:{REV01_PATH}").strip(),
            "fast_loader_status": "CLOSED",
            "rev02_status": "OPEN",
            "p11_39_sdk_tree": p1139,
        },
        "authority_inputs": authority_hashes,
        "immutable_scope": {
            "source_commit": PHASE11,
            "file_count": len(immutable_rows),
            "recursive_git_identity_sha256": immutable_digest,
            "files": immutable_rows,
            "p11_48_and_phase11_file_count": len(p1148_rows),
            "p11_48_and_phase11_recursive_git_identity_sha256": p1148_digest,
        },
        "legacy_inventory": inventory,
        "failed_rev01_bundle": {
            "recovery_commit": FAILED_PUBLICATION_COMMIT,
            "recovery_root_tree": FAILED_PUBLICATION_TREE,
            "bundle_tree": FAILED_BUNDLE_TREE,
            "file_count": failed_count,
            "recursive_content_sha256": failed_digest,
        },
        "publisher_quarantine": {
            "legacy_workflow": ".github/workflows/p11-prerelease-build.yml",
            "write_capable_failed_publishers": publishers,
            "status": "PASS",
        },
        "phase12_state_paths": p12,
        "assertions": {
            "rev01_failed_closed_status_only": "PASS",
            "phase11_complete_unchanged": "PASS",
            "p11_48_and_phase11_aggregate_unchanged": "PASS",
            "fast_loader_runbook_closed": "PASS",
            "immutable_scope_unchanged": "PASS",
            "failed_rev01_bundle_recovery_identity_bound": "PASS",
            "zero_phase12_state": "PASS",
            "historical_p11_39_sdk_unchanged": "PASS",
            "legacy_rev01_publisher_quarantined": "PASS",
            "rev02_sole_successor_and_open": "PASS",
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("REV02 STAGE A PASS")

if __name__ == "__main__":
    main()
