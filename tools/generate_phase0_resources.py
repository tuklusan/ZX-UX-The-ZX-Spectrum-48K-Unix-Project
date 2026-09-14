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
    b"ZX-UX - Inspired by Unix for the Sinclair ZX Spectrum 48K\n"
    b"64-column shell, native tools, C compiler, cassette storage\n"
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


FONT4X8_SOURCE = Path("v1/assets/font4x8-zxux.bin")
FONT4X8_SHA256 = "90f6818cf81cf3f13509cff32c091075691195d9638dbe801d12daceec1c9339"


def validate_font4x8_source(root: Path) -> bytes:
    path = root / FONT4X8_SOURCE
    if path.is_symlink() or not path.is_file():
        raise AssertionError("canonical font4x8-zxux source missing or not a regular file")
    data = path.read_bytes()
    if len(data) != 392 or data[:8] != b"F4X8" + bytes((1, 0x20, 96, 0)):
        raise AssertionError("canonical font4x8-zxux structure mismatch")
    if hashlib.sha256(data).hexdigest() != FONT4X8_SHA256:
        raise AssertionError("canonical font4x8-zxux SHA-256 mismatch")
    return data


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
        font = validate_font4x8_source(root)
        print(f"resource={FONT4X8_SOURCE.as_posix()} size={len(font)} sha256={hashlib.sha256(font).hexdigest()} source=canonical")
        resources = {
            Path("v1/assets/loading.scr"): loading_screen(),
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
