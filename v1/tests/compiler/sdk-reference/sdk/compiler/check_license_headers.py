#!/usr/bin/env python3
# ============================================================================
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Proprietary rights reserved except as expressly licensed herein.
#
# ZX-UX C48 SDK
# This file is governed by the SANYALnet Labs Non-Commercial License in the
# root LICENSE file. Non-Commercial use is permitted; Commercial Use and use
# for AI/ML model training are prohibited unless separately authorized.
#
# Attribution is required: "Based on original work by Supratim Sanyal of
# SANYALnet Labs." See LICENSE for full terms, warranty disclaimer, termination,
# patent, trademark, and governing-law provisions.
# ============================================================================
from __future__ import annotations

import argparse
from pathlib import Path
import sys

COPYRIGHT = "Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs."
ATTRIBUTION_PREFIX = 'Attribution is required: \"Based on original work by Supratim Sanyal of'
ATTRIBUTION_SUFFIX = 'SANYALnet Labs.\" See LICENSE for full terms'
PROJECT = "ZX-UX C48 SDK"

# Header-safe source/document formats owned by this project.
HEADER_SUFFIXES = {".py", ".c", ".h", ".md", ".txt", ".bat", ".yml", ".yaml"}
HEADER_NAMES = {"c48", "c48run", ".gitignore", ".gitattributes"}

# Deliberate exemptions: adding text would corrupt the syntax/format/container,
# or LICENSE must remain the exact license text rather than recursively header itself.
EXEMPT_NAMES = {"LICENSE", "VERSION", "MANIFEST.sha256"}
EXEMPT_SUFFIXES = {".json", ".bin", ".c48b", ".docx", ".zip"}


def classify(path: Path) -> str:
    if path.name in HEADER_NAMES or path.suffix.lower() in HEADER_SUFFIXES:
        return "header"
    if path.name in EXEMPT_NAMES or path.suffix.lower() in EXEMPT_SUFFIXES:
        return "exempt"
    return "unknown"


def check_tree(root: Path) -> list[str]:
    errors: list[str] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or ".git" in path.relative_to(root).parts:
            continue
        rel = path.relative_to(root).as_posix()
        kind = classify(path)
        if kind == "unknown":
            errors.append(f"unclassified artifact: {rel}")
            continue
        if kind == "exempt":
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeError as exc:
            errors.append(f"header-eligible file is not UTF-8 text: {rel}: {exc}")
            continue
        # Header must be near the top; shebang/@echo-off may precede it.
        top = text[:3000]
        if rel.startswith("dev/src/") and path.suffix.lower() in {".c", ".h"}:
            # C48 artifacts use a deliberately compact <=64-column header.
            required_markers = (
                COPYRIGHT, PROJECT, "Non-Commercial License",
                "Attribution required: Based on original work by Supratim",
                "Sanyal of SANYALnet Labs. See root LICENSE for full terms.",
            )
        else:
            required_markers = (
                COPYRIGHT, PROJECT, ATTRIBUTION_PREFIX, ATTRIBUTION_SUFFIX,
                "root LICENSE file",
            )
        for required in required_markers:
            if required not in top:
                errors.append(
                    f"missing license header marker {required!r}: {rel}"
                )
        # The header itself must contain a copyright marker. User-facing CLI
        # --about text may legitimately repeat the same copyright notice later.
        if COPYRIGHT not in top[:1800]:
            errors.append(f"copyright marker is not in the header block: {rel}")
    # Section 1(b) of LICENSE requires discoverable attribution in every
    # user-facing text interface. The two Python CLI entry points expose it
    # through --about, which is also listed by --help.
    for rel in ("compiler/c48.py", "compiler/c48run.py"):
        text = (root / rel).read_text(encoding="utf-8")
        for required in ("--about", COPYRIGHT, "Based on original work by Supratim Sanyal of SANYALnet Labs."):
            if required not in text:
                errors.append(f"CLI attribution/about marker {required!r} missing: {rel}")
    return errors


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Enforce ZX-UX C48 SDK license headers")
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    ns = ap.parse_args(argv)
    errors = check_tree(ns.root.resolve())
    if errors:
        for error in errors:
            print(f"LICENSE HEADER ERROR: {error}", file=sys.stderr)
        return 1
    print("LICENSE HEADER PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
