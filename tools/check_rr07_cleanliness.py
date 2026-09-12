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

from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
RECONCILIATION_PLAN = "docs/05-ZX-UX-BASELINE-REPAIR-RECONCILIATION-REV01.md"
IMPLEMENTATION_PLAN = "docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV02.md"
SKIP_PREFIXES = ("v1/dist/certification/", "v1/build/", "tools/runtime/")


def joined(*parts: str) -> str:
    return "".join(parts)


LEGACY_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("L01", re.compile(joined("transfer", r"\s*-\s*", "era"), re.IGNORECASE)),
    ("L02", re.compile(joined("transfer", r"\s*-\s*", "time", r"\s+provenance"), re.IGNORECASE)),
    ("L03", re.compile(joined("historical", r"\s*-?\s*", "host"), re.IGNORECASE)),
    ("L04", re.compile(joined("historical", r"\s+", "workstation"), re.IGNORECASE)),
    ("L05", re.compile(joined("windows", r"\s+", "installation"), re.IGNORECASE)),
    ("L06", re.compile(joined("fixed", r"\s+", "drive", r"\s+", "letter"), re.IGNORECASE)),
    ("L07", re.compile(joined("fixed", r"\s+", "user", r"\s+", "profile"), re.IGNORECASE)),
    ("L08", re.compile(joined("owner", r"\s*-?\s*", "override", r"s?"), re.IGNORECASE)),
    ("L09", re.compile(joined("pre", r"\s*-?\s*", "existing", r"(?:\s+project\s*-?\s*local)?\s+runtime"), re.IGNORECASE)),
    ("L10", re.compile(joined("alternative", r"\s+", "acceptance", r"\s+path"), re.IGNORECASE)),
)

WINDOWS_ABSOLUTE_PATH = re.compile(
    r"(?<![A-Za-z0-9])(?:[A-Za-z]:[\\/][^\s\"'`<>|]*|\\\\[A-Za-z0-9._-]+\\[A-Za-z0-9.$_-]+(?:\\[^\s\"'`<>|]*)?)"
)

PROHIBITION_MARKERS = (
    " no ",
    " not ",
    "without",
    "must not",
    "may not",
    "never",
    "remove",
    "removed",
    "reject",
    "cannot",
    "prohibit",
    "forbid",
    "is not part",
    "does not authorize",
    "silently",
)


def tracked_paths() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.decode("utf-8", "replace").strip() or "git ls-files failed")
    return [item.decode("utf-8") for item in result.stdout.split(b"\0") if item]


def line_number(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def context_for(text: str, line: int) -> str:
    lines = text.splitlines()
    first = max(0, line - 2)
    last = min(len(lines), line + 1)
    return " ".join(lines[first:last]).lower()


def intentional_legacy_reference(path: str, text: str, offset: int) -> bool:
    if path == RECONCILIATION_PLAN:
        return True
    if path != IMPLEMENTATION_PLAN:
        return False
    context = " " + context_for(text, line_number(text, offset)) + " "
    return any(marker in context for marker in PROHIBITION_MARKERS)


def main() -> int:
    failures: list[str] = []
    classified: list[str] = []
    text_count = 0

    for relative in tracked_paths():
        if relative.startswith(SKIP_PREFIXES) or "/build/" in relative:
            continue
        path = ROOT / relative
        if not path.is_file() or path.is_symlink():
            continue
        raw = path.read_bytes()
        if b"\0" in raw:
            continue
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            continue
        text_count += 1

        for match in WINDOWS_ABSOLUTE_PATH.finditer(text):
            line = line_number(text, match.start())
            failures.append(f"{relative}:{line}: Windows absolute path residue: {match.group(0)!r}")

        for label, pattern in LEGACY_PATTERNS:
            for match in pattern.finditer(text):
                line = line_number(text, match.start())
                if intentional_legacy_reference(relative, text, match.start()):
                    classified.append(f"{relative}:{line}: {label} -> intentional prohibition/change-control text")
                else:
                    rendered = " ".join(match.group(0).split())
                    failures.append(f"{relative}:{line}: unclassified {label}: {rendered!r}")

    for item in classified:
        print(f"R&R-07 CLASSIFIED: {item}")
    if failures:
        for item in failures:
            print(f"R&R-07 CLEANLINESS FAIL: {item}", file=sys.stderr)
        return 1

    print(
        f"ZX-UX R&R-07 CLEANLINESS PASS: {text_count} tracked text files scanned; "
        f"{len(classified)} intentional legacy references classified"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
