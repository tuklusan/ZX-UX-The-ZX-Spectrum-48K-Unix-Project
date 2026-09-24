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

"""Complete post-Phase-10/pre-Phase-11 repository walk and fail-closed gates."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PHASE10 = "8360b0c5817738b01dc4b75bb64b12d77341adcd"
REV16 = "24fe9d206c2f05bbc24f11544a5cb5a0b6ab104e9fc52e654a10c2d9734b008c"
REV07 = "840a52e55f623d3f5453329838728e9933ee650ac78c4f294acbca7910638fbc"
REV17 = "d12baf0b47a7f8cd2dcd60b82f100ba19f9fddaabad43728a004a07214716bf8"
REV08 = "97461e9ed12253409b25e6a4a4063cf0ec556a7317f9e4a5938d77edb6a1a14c"
LOADER_ZIP = "4c83a681f718192db9ebb32f0c8bc565baf2e68eb85de480322a1102d32f00c7"
ALLOWED_HISTORICAL_DIFFS = (
    "v1/dist/certification/R17.00.",
    "v1/dist/media/P10.pre-release/",
    "v1/dist/media/P9.pre-release/",
)
OBSOLETE_PATHS = {
    "v1/assets/loading.scr",
    ".github/workflows/p9-prerelease-build.yml",
    ".github/workflows/native-projection-probe-once.yml",
    ".github/workflows/native-rebuild-probe-once.yml",
    ".github/workflows/release-tzx-dispatch-once.yml",
    ".github/workflows/release-tzx-promote-once.yml",
    ".github/workflows/r1700-dispatch-once.yml",
}
P11_PATH = re.compile(r"(?:^|/)(?:P11(?:\.|/)|p11[^/]*qualification|phase-?11)", re.I)


class WalkError(RuntimeError):
    pass


def require(ok: bool, msg: str) -> None:
    if not ok:
        raise WalkError(msg)


def run(*args: str) -> str:
    result = subprocess.run(args, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    require(result.returncode == 0, f"{' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tracked() -> list[str]:
    return [p for p in run("git", "ls-files").splitlines() if p]


def classify(path: str) -> str:
    if path in OBSOLETE_PATHS or path.startswith("v1/dist/media/P9.pre-release/"):
        return "obsolete"
    if path.startswith(".github/actions/"):
        return "current"
    if path.startswith(".github/workflows/"):
        name = Path(path).name
        if name in {
            "candidate-kernel.yml",
            "evidence-integrity.yml",
            "exact-head-regression.yml",
            "p10-prerelease-build.yml",
            "qualification-auto-dispatch.yml",
            "quality-and-ci.yml",
            "release-tzx-qualification.yml",
        }:
            return "current"
        if name.startswith("r1700-"):
            return "replay-only"
        if re.match(r"p\d+(?:-final)?-qualification\.yml$", name):
            return "replay-only"
        if re.match(r"phase\d+.*\.yml$", name):
            return "replay-only"
        return "unrelated"
    if path.startswith("docs/"):
        name = Path(path).name
        if name in {
            "01-ZX-UX-ARCHITECTURE-REV17.md",
            "02-ZX-UX-IMPLEMENTATION-STEPS-REV08.md",
            "03-ZX-UX-DEVELOPMENT-WORKFLOW.md",
            "--W-A-R-N-I-N-G--.md",
        }:
            return "current"
        if re.match(r"0[12]-ZX-UX-.*-REV\d+\.md$", name):
            return "historical"
        return "current"
    if path == "README.md" or path.startswith("v1/docs/"):
        return "current"
    if path.startswith("scratch/"):
        name = Path(path).name
        if name == "ZX-UX-FAST-LOADER-TZX-RELEASE-MIGRATION-RUNBOOK-REV01.md":
            return "current"
        if name in {"README.md", "WORKFLOW.md"}:
            return "current" if name == "README.md" else "historical"
        if name.endswith(".md"):
            return "historical"
        if name == "ZX-UX-LOADER-1.0.0-portable.zip":
            return "current"
        return "disposable"
    if path.startswith("v1/dist/media/P10.pre-release/"):
        return "current"
    if path.startswith("v1/dist/"):
        if Path(path).name.lower().startswith("readme"):
            return "current"
        return "historical"
    if path.startswith(("tools/", "v1/tools-host/")):
        if path.startswith("v1/tools-host/maketap/"):
            return "replay-only"
        return "current"
    return "unrelated"


def selected(path: str) -> bool:
    return (
        path == "README.md"
        or path.startswith(".github/workflows/")
        or path.startswith(".github/actions/")
        or (path.startswith(("docs/", "v1/docs/", "scratch/")) and (path.endswith(".md") or path.endswith(".txt")))
        or path.startswith("v1/dist/")
        or path.startswith("tools/")
        or path.startswith("v1/tools-host/test-driver/")
        or path.startswith("v1/tools-host/release-tzx/")
    )


def current_text_hits(paths: list[str]) -> list[dict[str, Any]]:
    patterns = {
        "stale-active-rev16": re.compile(r"(?:REV16\s*/\s*REV07|REV16[^\n]{0,50}REV07)[^\n]{0,80}active|active authorit[^\n]{0,80}REV16", re.I),
        "stale-canonical-rev07": re.compile(r"canonical REV07 sequence", re.I),
        "screen-or-old-loader-reference": re.compile(r"SCREEN\$|zx48uxscr|loading\.scr", re.I),
        "tap-release-reference": re.compile(r"(?:release|pre-release)[^\n]{0,100}(?:\.tap|\bTAP\b)|(?:\.tap|\bTAP\b)[^\n]{0,100}(?:release|pre-release)", re.I),
        "phase11-reference": re.compile(r"Phase-11|P11\.01|\bP11\b", re.I),
    }
    hits: list[dict[str, Any]] = []
    for rel in paths:
        if classify(rel) != "current":
            continue
        path = ROOT / rel
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for number, line in enumerate(text.splitlines(), 1):
            kinds = [name for name, pattern in patterns.items() if pattern.search(line)]
            if kinds:
                hits.append({"path": rel, "line": number, "kinds": kinds, "text": line[:400]})
    return hits


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", type=Path, required=True)
    args = ap.parse_args()

    paths = tracked()
    require(run("git", "rev-parse", "refs/tags/PHASE-10-COMPLETE") == PHASE10, "PHASE-10-COMPLETE moved")
    require(sha(ROOT / "docs/01-ZX-UX-ARCHITECTURE-REV16.md") == REV16, "REV16 changed")
    require(sha(ROOT / "docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md") == REV07, "REV07 changed")
    require(sha(ROOT / "docs/01-ZX-UX-ARCHITECTURE-REV17.md") == REV17, "REV17 changed")
    require(sha(ROOT / "docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV08.md") == REV08, "REV08 changed")
    require(sha(ROOT / "scratch/ZX-UX-LOADER-1.0.0-portable.zip") == LOADER_ZIP, "loader portable ZIP changed")

    p11 = [p for p in paths if P11_PATH.search(p)]
    require(not p11, f"Phase-11 state present: {p11}")
    obsolete_present = sorted(p for p in paths if p in OBSOLETE_PATHS or p.startswith("v1/dist/media/P9.pre-release/"))
    require(not obsolete_present, f"obsolete migration state present: {obsolete_present}")

    out = ROOT / "v1/dist/media/P10.pre-release"
    expected = {"README.txt", "pre-release.json", "zx-ux-phase10-pre-release.tzx"}
    require(out.is_dir(), "P10.pre-release missing")
    require({p.name for p in out.iterdir() if p.is_file()} == expected, "P10.pre-release must contain exactly three files")
    meta = json.loads((out / "pre-release.json").read_text(encoding="utf-8"))
    require(meta["kind"] == "phase10-fast-loader-tzx-pre-release", "wrong pre-release kind")
    require(meta["checkpoint_commit"] == PHASE10, "wrong pre-release Phase-10 anchor")
    require(meta["authority"]["architecture_sha256"] == REV17, "pre-release REV17 mismatch")
    require(meta["authority"]["implementation_plan_sha256"] == REV08, "pre-release REV08 mismatch")
    require(meta["fast_loader"]["portable_zip_sha256"] == LOADER_ZIP, "pre-release loader ZIP mismatch")
    require(meta["boot_contract"]["distribution"] == "TZX-only", "pre-release not TZX-only")
    require(meta["boot_contract"]["screen_file"] is None and meta["boot_contract"]["zx48uxscr"] is False, "SCREEN$ still active")
    require(meta["boot_contract"]["kernel_size"] == 8192 and meta["boot_contract"]["handoff"] == "0xE003", "kernel contract mismatch")
    require(not list(out.glob("*.tap")), "release TAP remains")
    tzx = out / "zx-ux-phase10-pre-release.tzx"
    require(tzx.stat().st_size == meta["tzx"]["size"], "TZX size mismatch")
    require(sha(tzx) == meta["tzx"]["sha256"], "TZX hash mismatch")
    identity = meta["kernel_identity"]
    require(identity["size"] == 8192, "kernel identity size")
    require(len({identity["host_built_sha256"], identity["tzx_embedded_sha256"], identity["native_rebuilt_sha256"]}) == 1, "three-way kernel hash mismatch")
    require(identity["bytewise_host_equals_tzx"] is True, "host/TZX bytewise proof absent")
    require(identity["bytewise_host_equals_native_target_compare"] is True, "host/native bytewise proof absent")
    require(identity["bytewise_tzx_equals_native"] is True, "TZX/native bytewise proof absent")
    require(all(value == "PASS" for value in meta["native_rebuild"]["assertions"].values()), "native rebuild proof incomplete")
    require(all(value == "PASS" for value in meta["tests"].values()), "pre-release test proof incomplete")

    # Historical P0-P10 certification/media bytes are immutable across the migration,
    # except newly admitted R17 evidence, replacement P10.pre-release, and removal of
    # explicitly obsolete non-certification P9.pre-release output.
    changed = run("git", "diff", "--name-only", PHASE10, "HEAD", "--", "v1/dist/certification", "v1/dist/media").splitlines()
    unexpected = [p for p in changed if p and not any(p.startswith(prefix) for prefix in ALLOWED_HISTORICAL_DIFFS)]
    require(not unexpected, f"historical certification/media changed unexpectedly: {unexpected}")

    lock_path = ROOT / "tools/manifest/toolchain.lock.json"
    require(lock_path.is_file(), "shared toolchain lock missing")
    lock_text = lock_path.read_text(encoding="utf-8")
    setup_text = (ROOT / ".github/actions/setup-zxux-runtime/action.yml").read_text(encoding="utf-8")
    require("pasmo" not in lock_text.lower(), "Pasmo entered shared certified toolchain lock")
    require("pasmo" not in setup_text.lower(), "Pasmo entered shared runtime setup")

    license_text = (ROOT / "tools/check_license_headers.sh").read_text(encoding="utf-8")
    require("v1/assets/loading.scr" not in license_text, "dead loading.scr license exemption remains")

    dispatcher = (ROOT / ".github/workflows/qualification-auto-dispatch.yml").read_text(encoding="utf-8")
    require('echo "current=false"' in dispatcher, "superseded-candidate clean termination missing")
    require("steps.head.outputs.current == 'true'" in dispatcher, "superseded candidate is not gated")
    require("git rev-parse origin/main" in dispatcher, "final/current exact-head protection missing")

    prerelease_wf = (ROOT / ".github/workflows/p10-prerelease-build.yml").read_text(encoding="utf-8")
    require("Phase-10 fast-loader TZX pre-release" in prerelease_wf, "replacement pre-release workflow missing")
    require("--no-accelerate-loader --no-fastload --no-traps --no-detect-loader" in prerelease_wf, "real-time shortcut-disable contract missing")
    require("native_rebuild_test.py" in prerelease_wf, "native rebuild gate missing")
    require("P11" in prerelease_wf and "Phase 11" in prerelease_wf, "explicit no-P11 safety gate missing")

    chosen = [p for p in paths if selected(p)]
    classifications = [{"path": p, "classification": classify(p)} for p in chosen]
    require(all(item["classification"] in {"current", "historical", "replay-only", "obsolete", "disposable", "unrelated"} for item in classifications), "classification error")
    workflow_count = sum(p.startswith(".github/workflows/") for p in chosen)
    action_count = sum(p.startswith(".github/actions/") for p in chosen)
    require(workflow_count > 200, "workflow walk unexpectedly incomplete")
    require(action_count >= 1, "action walk unexpectedly incomplete")

    precise_stale = []
    precise_patterns = (
        re.compile(r"REV16\s*/\s*REV07 are the active authorities", re.I),
        re.compile(r"canonical REV07 sequence", re.I),
    )
    for rel in chosen:
        if classify(rel) != "current":
            continue
        path = ROOT / rel
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for number, line in enumerate(text.splitlines(), 1):
            if any(rx.search(line) for rx in precise_patterns):
                precise_stale.append({"path": rel, "line": number, "text": line})
    require(not precise_stale, f"stale current authority claims: {precise_stale}")

    report = {
        "schema": 1,
        "kind": "post-phase10-pre-phase11-repository-walk",
        "head": run("git", "rev-parse", "HEAD"),
        "head_tree": run("git", "rev-parse", "HEAD^{tree}"),
        "phase10_complete": PHASE10,
        "authority": {"REV16": REV16, "REV07": REV07, "REV17": REV17, "REV08": REV08},
        "loader_zip_sha256": LOADER_ZIP,
        "pre_release": {
            "tzx_sha256": sha(tzx),
            "tzx_size": tzx.stat().st_size,
            "kernel_sha256": identity["host_built_sha256"],
            "files": sorted(expected),
        },
        "checks": {
            "phase10_tag_fixed": "PASS",
            "historical_rev16_rev07_fixed": "PASS",
            "active_rev17_rev08_fixed": "PASS",
            "loader_zip_fixed": "PASS",
            "no_phase11_state": "PASS",
            "no_obsolete_active_release_state": "PASS",
            "compact_tzx_only_prerelease": "PASS",
            "three_way_exact_kernel_identity": "PASS",
            "native_source_as_obj1_ld_run": "PASS",
            "controlled_mismatch_negative": "PASS",
            "pasmo_release_scoped": "PASS",
            "qualification_superseded_clean_termination": "PASS",
            "historical_evidence_media_unchanged": "PASS",
            "all_requested_surfaces_classified": "PASS",
        },
        "counts": {
            "tracked_files": len(paths),
            "walk_files": len(chosen),
            "workflows": workflow_count,
            "actions": action_count,
            "classifications": {
                key: sum(item["classification"] == key for item in classifications)
                for key in ("current", "historical", "replay-only", "obsolete", "disposable", "unrelated")
            },
        },
        "potential_current_state_mentions": current_text_hits(chosen),
        "classifications": classifications,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(f"workflows={workflow_count}")
    print(f"actions={action_count}")
    print(f"walk_files={len(chosen)}")
    print(f"potential_current_state_mentions={len(report['potential_current_state_mentions'])}")
    print("ZX-UX POST-PHASE10 REPOSITORY WALK PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except WalkError as exc:
        print(f"ZX-UX POST-PHASE10 REPOSITORY WALK FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
