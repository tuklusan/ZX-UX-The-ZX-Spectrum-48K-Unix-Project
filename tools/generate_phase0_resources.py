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
import hashlib
import sys

ROOT_MARKER = b"ZX-UX project root"

ISSUE = (
    b"\x7f Supratim Sanyal, SANYALnet Labs\n"
    b"https://supratim-sanyal.blogspot.com/\n"
    b"48K. One Z80. No excuses.\n"
)


def find_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        marker = candidate / ".zxux-root"
        if marker.is_file() and not marker.is_symlink() and marker.read_bytes() == ROOT_MARKER:
            return candidate
    raise RuntimeError("canonical project root not found")


def loading_screen() -> bytes:
    # Native 6912-byte Spectrum screen: 6144 bitmap bytes followed by 768 attributes.
    # The frozen Phase-0 artwork is deliberately minimal: black bitmap with bright-white
    # ink on black paper. Later terminal initialization deliberately replaces it.
    bitmap = bytes(6144)
    attributes = bytes([0x47]) * 768
    result = bitmap + attributes
    if len(result) != 6912:
        raise AssertionError("loading screen size")
    return result


def font4x8() -> bytes:
    # 98 glyphs x 4 bytes. Each byte contains two 4-pixel rows packed high/low nibble.
    # Phase 0 freezes size/identity; the deliberately simple seed font is replaced only
    # by an explicit resource revision, never by implicit host-font conversion.
    out = bytearray()
    for code in range(0x20, 0x82):
        nibble = code & 0x0F
        out.extend((nibble << 4 | nibble,) * 4)
    if len(out) != 392:
        raise AssertionError("font4x8 size")
    return bytes(out)


def bincat() -> bytes:
    # Frozen BCAT bootstrap shape: 8-byte header + forty 12-byte empty records.
    # Records are deliberately empty in Phase 0; later phases replace entries in place.
    header = b"BCAT" + bytes((1, 40, 0, 0))
    records = bytes(40 * 12)
    result = header + records
    if len(result) != 488:
        raise AssertionError("BCAT size")
    return result


def write_if_changed(path: Path, data: bytes) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file() and path.read_bytes() == data:
        return False
    path.write_bytes(data)
    return True


def main() -> int:
    try:
        root = find_root(Path(__file__).resolve())
        resources = {
            Path("v1/assets/loading.scr"): loading_screen(),
            Path("v1/assets/font4x8.bin"): font4x8(),
            Path("v1/assets/issue.txt"): ISSUE,
            Path("v1/assets/crontab.txt"): b"",
            Path("v1/assets/bincat.bin"): bincat(),
        }
        changed: list[str] = []
        for relative, data in resources.items():
            if write_if_changed(root / relative, data):
                changed.append(relative.as_posix())
            print(f"resource={relative.as_posix()} size={len(data)} sha256={hashlib.sha256(data).hexdigest()}")
        print("changed=" + (",".join(changed) if changed else "none"))
        return 0
    except (OSError, RuntimeError, AssertionError) as exc:
        print(f"ZX-UX PHASE0 RESOURCE GENERATION FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
