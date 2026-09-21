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
from pathlib import Path
import re
import shutil
import sys

ALLOWED_SUFFIXES = frozenset({".sna", ".tap", ".tzx", ".scr", ".fmf", ".wav", ".flac", ".png"})
STEP_RE = re.compile(r"^P(?:[6-9]|1[0-2])\.\d{2}$")


def fail(message: str) -> None:
    raise SystemExit(f"ERROR: {message}")


def load_action_manifest(path: Path, step: str, action: str) -> dict[str, object]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        fail(f"cannot read staged media manifest {path}: {exc}")
    if data.get("schema") != 1 or data.get("step") != step or data.get("action") != action:
        fail(f"staged media manifest identity mismatch: {path}")
    commit = data.get("source_commit")
    if not isinstance(commit, str) or len(commit) != 40 or any(ch not in "0123456789abcdef" for ch in commit):
        fail(f"invalid staged media source commit: {path}")
    files = data.get("files")
    if not isinstance(files, list):
        fail(f"invalid staged media file list: {path}")
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description="Finalize externally staged ZX-UX Spectrum media into the repository.")
    parser.add_argument("--step", required=True)
    parser.add_argument("--evidence-dir", required=True)
    parser.add_argument("--destination", default="v1/dist/media")
    args = parser.parse_args()

    if not STEP_RE.fullmatch(args.step):
        fail(f"media finalization is restricted to P6-P12 steps: {args.step}")
    evidence_dir = Path(args.evidence_dir).resolve()
    staged_root = evidence_dir / "media-staging" / args.step
    destination_root = Path(args.destination).resolve()
    step_destination = destination_root / args.step
    if step_destination.exists():
        fail(f"durable retained-media directory already exists: {step_destination}")
    if not staged_root.is_dir():
        fail(f"staged retained-media directory missing: {staged_root}")

    source_commit: str | None = None
    entries: list[dict[str, object]] = []
    pending: list[tuple[Path, Path]] = []
    for action in ("build", "test"):
        action_dir = staged_root / action
        manifest_path = action_dir / "manifest.json"
        if not manifest_path.is_file():
            continue
        data = load_action_manifest(manifest_path, args.step, action)
        commit = str(data["source_commit"])
        if source_commit is None:
            source_commit = commit
        elif source_commit != commit:
            fail("build/test retained-media manifests bind different source commits")
        seen_names: set[str] = set()
        for item in data["files"]:
            if not isinstance(item, dict):
                fail(f"invalid staged media entry: {manifest_path}")
            name = item.get("name")
            if not isinstance(name, str) or Path(name).name != name or name in seen_names:
                fail(f"invalid or duplicate staged media name: {name!r}")
            seen_names.add(name)
            source = action_dir / name
            suffix = source.suffix.lower()
            if suffix not in ALLOWED_SUFFIXES or not source.is_file() or source.is_symlink():
                fail(f"invalid staged media file: {source}")
            payload = source.read_bytes()
            digest = hashlib.sha256(payload).hexdigest()
            if item.get("sha256") != digest or item.get("size") != len(payload):
                fail(f"staged media hash/size mismatch: {source}")
            relative = Path(action) / name
            pending.append((source, step_destination / relative))
            entries.append(
                {
                    "action": action,
                    "path": relative.as_posix(),
                    "sha256": digest,
                    "size": len(payload),
                }
            )

    if source_commit is None or not entries:
        fail(f"no generated Spectrum media staged for {args.step}")

    step_destination.mkdir(parents=True)
    for source, destination in pending:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)

    durable = {
        "schema": 1,
        "step": args.step,
        "source_commit": source_commit,
        "files": sorted(entries, key=lambda item: (str(item["action"]), str(item["path"]))),
    }
    (step_destination / "manifest.json").write_text(
        json.dumps(durable, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(step_destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
