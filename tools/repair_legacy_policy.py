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
MAX_EXPECTED_OCCURRENCES = 8


class RepairError(RuntimeError):
    pass


def find_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        marker = candidate / ".zxux-root"
        if marker.is_file() and not marker.is_symlink() and marker.read_bytes() == ROOT_MARKER:
            return candidate
    raise RepairError("canonical project root not found")


def replace_case_insensitive(data: bytes, needle: bytes, replacement: bytes) -> tuple[bytes, int]:
    lowered = data.lower()
    offsets: list[int] = []
    start = 0
    while True:
        offset = lowered.find(needle, start)
        if offset < 0:
            break
        offsets.append(offset)
        start = offset + len(needle)
    if len(offsets) > MAX_EXPECTED_OCCURRENCES:
        raise RepairError(f"unexpected legacy policy occurrence count: {len(offsets)}")
    if not offsets:
        return data, 0

    parts: list[bytes] = []
    cursor = 0
    for offset in offsets:
        parts.append(data[cursor:offset])
        parts.append(replacement)
        cursor = offset + len(needle)
    parts.append(data[cursor:])
    return b"".join(parts), len(offsets)


def main() -> int:
    try:
        root = find_root(Path(__file__).resolve())
        target = root / TARGET
        if not target.is_file() or target.is_symlink():
            raise RepairError(f"target is not a regular file: {TARGET}")
        before = target.read_bytes()
        after, count = replace_case_insensitive(before, _NEEDLE, _REPLACEMENT)
        if count:
            if _NEEDLE in after.lower():
                raise RepairError("legacy policy occurrence remains after replacement")
            target.write_bytes(after)
            print(f"repaired={TARGET} count={count}")
        else:
            print(f"clean={TARGET}")
        return 0
    except (OSError, RepairError) as exc:
        print(f"ZX-UX LEGACY POLICY REPAIR FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
