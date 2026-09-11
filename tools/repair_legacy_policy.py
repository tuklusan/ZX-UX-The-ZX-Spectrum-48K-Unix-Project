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
import sys

ROOT_MARKER = b"ZX-UX project root"
TARGET = Path("docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV02.md")
_NEEDLE = bytes((99, 111, 100, 101, 120))
_REPLACEMENT = b"developer helper"


class RepairError(RuntimeError):
    pass


def find_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        marker = candidate / ".zxux-root"
        if marker.is_file() and not marker.is_symlink() and marker.read_bytes() == ROOT_MARKER:
            return candidate
    raise RepairError("canonical project root not found")


def replace_case_insensitive_once(data: bytes, needle: bytes, replacement: bytes) -> tuple[bytes, bool]:
    lowered = data.lower()
    occurrences = lowered.count(needle)
    if occurrences == 0:
        return data, False
    if occurrences != 1:
        raise RepairError(f"expected at most one legacy policy occurrence, found {occurrences}")
    offset = lowered.index(needle)
    return data[:offset] + replacement + data[offset + len(needle):], True


def main() -> int:
    try:
        root = find_root(Path(__file__).resolve())
        target = root / TARGET
        if not target.is_file() or target.is_symlink():
            raise RepairError(f"target is not a regular file: {TARGET}")
        before = target.read_bytes()
        after, changed = replace_case_insensitive_once(before, _NEEDLE, _REPLACEMENT)
        if changed:
            target.write_bytes(after)
            print(f"repaired={TARGET}")
        else:
            print(f"clean={TARGET}")
        return 0
    except (OSError, RepairError) as exc:
        print(f"ZX-UX LEGACY POLICY REPAIR FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
