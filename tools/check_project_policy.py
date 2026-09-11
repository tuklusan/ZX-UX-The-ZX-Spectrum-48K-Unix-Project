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

import json
import os
from pathlib import Path
import sys

ROOT = Path(".")
INTERNAL_DIR = ".git"

# Project-owner-defined prohibited names are encoded numerically so the names
# themselves never appear in repository content, checker output, or examples.
_PROHIBITED_CODES = (
    (67, 108, 97, 117, 100, 101),
    (79, 112, 101, 110, 65, 73),
    (67, 111, 100, 101, 120),
    (67, 104, 97, 116, 71, 80, 84),
)
PROHIBITED = tuple(bytes(code).lower() for code in _PROHIBITED_CODES)


def contains_prohibited(data: bytes) -> bool:
    lowered = data.lower()
    return any(token in lowered for token in PROHIBITED)


def report(kind: str, location: str) -> None:
    print(f"ERROR: prohibited project name found in {kind}: {location}", file=sys.stderr)


def scan_paths_and_files() -> int:
    failures = 0

    for path in sorted(ROOT.rglob("*")):
        relative = path.relative_to(ROOT)
        if relative.parts and relative.parts[0] == INTERNAL_DIR:
            continue

        display = relative.as_posix()
        if contains_prohibited(display.encode("utf-8", errors="surrogateescape")):
            report("path", display)
            failures += 1

        if path.is_symlink():
            target = os.readlink(path)
            if contains_prohibited(target.encode("utf-8", errors="surrogateescape")):
                report("symlink target", display)
                failures += 1
            continue

        if not path.is_file():
            continue

        try:
            data = path.read_bytes()
        except OSError as exc:
            print(f"ERROR: cannot read project artifact {display}: {exc}", file=sys.stderr)
            failures += 1
            continue

        if contains_prohibited(data):
            report("artifact", display)
            failures += 1

    return failures


def scan_workflow_metadata() -> int:
    failures = 0

    for name in ("GITHUB_REF", "GITHUB_HEAD_REF", "GITHUB_BASE_REF"):
        value = os.environ.get(name, "")
        if value and contains_prohibited(value.encode("utf-8", errors="replace")):
            report("workflow ref metadata", name)
            failures += 1

    event_path = os.environ.get("GITHUB_EVENT_PATH", "")
    if not event_path:
        return failures

    try:
        payload = json.loads(Path(event_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: cannot inspect workflow event metadata: {exc}", file=sys.stderr)
        return failures + 1

    values: list[tuple[str, str]] = []
    ref = payload.get("ref")
    if isinstance(ref, str):
        values.append(("event ref", ref))

    head_commit = payload.get("head_commit")
    if isinstance(head_commit, dict) and isinstance(head_commit.get("message"), str):
        values.append(("head check-in message", head_commit["message"]))

    commits = payload.get("commits")
    if isinstance(commits, list):
        for index, commit in enumerate(commits):
            if isinstance(commit, dict) and isinstance(commit.get("message"), str):
                values.append((f"check-in message {index + 1}", commit["message"]))

    for label, value in values:
        if contains_prohibited(value.encode("utf-8", errors="replace")):
            report("workflow event metadata", label)
            failures += 1

    return failures


def main() -> int:
    failures = scan_paths_and_files() + scan_workflow_metadata()
    if failures:
        print(f"Project policy gate failed with {failures} violation(s).", file=sys.stderr)
        return 1

    print("Project policy gate passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
