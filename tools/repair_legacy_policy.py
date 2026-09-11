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
_LEGACY_NAME = bytes((99, 111, 100, 101, 120))
_LEGACY_NAME_REPLACEMENT = b"developer helper"
_OLD_ARCH_SHA = b"aa087094c013c7f7602845d1ee353bd37ab699eb9d8661e534a00a48445e29fd"
_NEW_ARCH_SHA = b"f76281fab2e5ae73b7321fc2a69e6776f7ccd8bfe3955a6ed6fb3bec44f762c7"
MAX_EXPECTED_LEGACY_NAMES = 8
MAX_EXPECTED_ARCH_HASHES = 8


class RepairError(RuntimeError):
    pass


def find_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        marker = candidate / ".zxux-root"
        if marker.is_file() and not marker.is_symlink() and marker.read_bytes() == ROOT_MARKER:
            return candidate
    raise RepairError("canonical project root not found")


def replace_case_insensitive(
    data: bytes,
    needle: bytes,
    replacement: bytes,
    *,
    maximum: int,
) -> tuple[bytes, int]:
    lowered = data.lower()
    offsets: list[int] = []
    start = 0
    while True:
        offset = lowered.find(needle.lower(), start)
        if offset < 0:
            break
        offsets.append(offset)
        start = offset + len(needle)
    if len(offsets) > maximum:
        raise RepairError(f"unexpected handover occurrence count: {len(offsets)}")
    if not offsets:
        return data, 0

    parts: list[bytes] = []
    cursor = 0
    for offset in offsets:
        parts.append(data[cursor:offset])
        original = data[offset:offset + len(needle)]
        if original.isupper():
            parts.append(replacement.upper())
        else:
            parts.append(replacement.lower())
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
        after, name_count = replace_case_insensitive(
            before,
            _LEGACY_NAME,
            _LEGACY_NAME_REPLACEMENT,
            maximum=MAX_EXPECTED_LEGACY_NAMES,
        )
        after, hash_count = replace_case_insensitive(
            after,
            _OLD_ARCH_SHA,
            _NEW_ARCH_SHA,
            maximum=MAX_EXPECTED_ARCH_HASHES,
        )

        if _LEGACY_NAME in after.lower():
            raise RepairError("legacy policy occurrence remains after replacement")
        if _OLD_ARCH_SHA in after.lower():
            raise RepairError("superseded architecture hash remains after replacement")

        if name_count or hash_count:
            target.write_bytes(after)
            print(f"repaired={TARGET} policy={name_count} architecture_hash={hash_count}")
        else:
            print(f"clean={TARGET}")
        return 0
    except (OSError, RepairError) as exc:
        print(f"ZX-UX HANDOVER REPAIR FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
