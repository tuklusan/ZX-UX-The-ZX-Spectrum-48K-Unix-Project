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

BIN_COMMANDS = tuple(sorted((
    "cron", "crontab", "vi", "as", "cc", "ld", "ls", "cat", "echo", "cp",
    "mv", "rm", "pack", "unpack", "hexdump", "grep", "wc", "head", "tail", "cmp",
    "true", "false", "sleep", "which", "env", "stty", "date", "man", "whoami", "uname",
    "uptime", "cal", "fortune", "banner", "rev", "yes", "udg", "gfxdemo", "demo", "sh",
)))


def find_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        marker = candidate / ".zxux-root"
        if marker.is_file() and not marker.is_symlink() and marker.read_bytes() == ROOT_MARKER:
            return candidate
    raise RuntimeError("canonical project root not found")


def loading_screen() -> bytes:
    bitmap = bytes(6144)
    attributes = bytes([0x47]) * 768
    result = bitmap + attributes
    if len(result) != 6912:
        raise AssertionError("loading screen size")
    return result


def font4x8() -> bytes:
    # F4X8 header plus 96 glyphs x 4 packed bytes, codes 0x20..0x7f.
    header = b"F4X8" + bytes((1, 0x20, 96, 0))
    glyphs = bytearray()
    for code in range(0x20, 0x80):
        if code == 0x20:
            rows = (0, 0, 0, 0, 0, 0, 0, 0)
        elif code == 0x7F:
            rows = (0x6, 0x9, 0xA, 0xA, 0xA, 0x9, 0x6, 0x0)
        else:
            # Deterministic compact seed glyph. The format, code coverage, and byte
            # identity are frozen; no host font or locale can influence the result.
            low = code & 0x0F
            high = (code >> 4) & 0x0F
            rows = (low, high, low ^ 0x0F, high ^ 0x0F, high, low, high ^ low, 0)
        for row in range(0, 8, 2):
            glyphs.append(((rows[row] & 0x0F) << 4) | (rows[row + 1] & 0x0F))
    result = header + bytes(glyphs)
    if len(glyphs) != 384 or len(result) != 392:
        raise AssertionError("font4x8 size")
    return result


def bincat() -> bytes:
    if len(BIN_COMMANDS) != 40 or len(set(BIN_COMMANDS)) != 40:
        raise AssertionError("BCAT command-set cardinality")
    records = bytearray()
    for name in BIN_COMMANDS:
        encoded = name.encode("ascii")
        if name != name.lower() or not (1 <= len(encoded) <= 10):
            raise AssertionError(f"invalid BCAT command name: {name}")
        records.extend(encoded.ljust(10, b"\0"))
        records.extend((2, 1))  # object type BIN, tape-backed flag only
    result = b"BCAT" + bytes((1, 40, 0, 0)) + bytes(records)
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
