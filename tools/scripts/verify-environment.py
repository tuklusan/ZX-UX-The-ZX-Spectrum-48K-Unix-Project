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
import os
from pathlib import Path
import subprocess
import sys

ROOT_MARKER = b"ZX-UX project root"
CANONICAL_LOCK = Path("tools/manifest/toolchain.lock.json")
RECONSTRUCTED_LOCK_SHA256 = "8a2e38fbd7b99e166f279d4e2163b0200c52e1ee95672e834e861a1a47b337bc"
ARCHITECTURE = Path("docs/01-ZX-UX-ARCHITECTURE-REV11.md")
ARCHITECTURE_SHA256 = "f76281fab2e5ae73b7321fc2a69e6776f7ccd8bfe3955a6ed6fb3bec44f762c7"
FINAL_MARKER = "ZX-UX DEVELOPMENT ENVIRONMENT CERTIFICATION PASS"

EXPECTED = {
    "python": ("3.13.15", "1e66a7945a48390ee4c2a4268a0e4185884059a13c4aab6d148aa208deea4a76", 23160540),
    "sjasmplus": ("1.24.0", "0b5013f07e8d8505f9e296529655668b6fdf0268625c19e883b0fff484e209f1", 1290980),
    "libspectrum": ("1.6.4", "4cce5764227f040238877d9e0ce3aede2bac1b1adfa8ed535d68bb405df395c3", 703518),
    "fuse": ("1.9.2", "ad04be2c67172c5387fd2cd84350ed8215958fa5b8a52a4990862867f089f489", 1850564),
    "fuse-utils": ("1.4.7", "1a2e7be6447476d45c606c44536805cdb0dfb29d7f41632602d9a6883bf1e4b6", 561628),
    "zx48-rom": ("1982-original", "d55daa439b673b0e3f5897f99ac37ecb45f974d1862b4dadb85dec34af99cb42", 16384),
}


class CertificationError(RuntimeError):
    pass


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def find_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        marker = candidate / ".zxux-root"
        if marker.is_file() and not marker.is_symlink() and marker.read_bytes() == ROOT_MARKER:
            return candidate
    raise CertificationError("canonical .zxux-root marker not found")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise CertificationError(message)


def load_manifest(root: Path, requested: str | None) -> tuple[Path, dict]:
    path = (root / requested).resolve() if requested else (root / CANONICAL_LOCK).resolve()
    require(path.is_file() and not path.is_symlink(), f"manifest is not a regular file: {path}")
    canonical = (root / CANONICAL_LOCK).resolve()
    if path == canonical:
        require(digest(path) == RECONSTRUCTED_LOCK_SHA256, "canonical reconstructed lock hash mismatch")
    data = json.loads(path.read_text(encoding="utf-8"))
    require(data.get("schema") == 1, "manifest schema must be 1")
    require(data.get("project") == "ZX-UX", "manifest project identity mismatch")
    require(data.get("root_marker") == ROOT_MARKER.decode("ascii"), "manifest root marker mismatch")
    freeze = data.get("aggregate_freeze", {})
    require(freeze.get("reconstructed_under_owner_override") is True, "owner override record missing")
    artifacts = data.get("artifacts")
    require(isinstance(artifacts, list), "manifest artifacts must be a list")
    by_id = {}
    for item in artifacts:
        require(isinstance(item, dict), "manifest artifact entry must be an object")
        artifact_id = item.get("id")
        require(isinstance(artifact_id, str) and artifact_id not in by_id, "duplicate/invalid artifact id")
        by_id[artifact_id] = item
        require(str(item.get("url", "")).startswith("https://"), f"{artifact_id}: HTTPS URL required")
        require(isinstance(item.get("runtime_path"), str) and item["runtime_path"], f"{artifact_id}: runtime_path required")
    require(set(by_id) == set(EXPECTED), "manifest artifact set mismatch")
    for artifact_id, (version, sha256, size) in EXPECTED.items():
        item = by_id[artifact_id]
        require(item.get("version") == version, f"{artifact_id}: version mismatch")
        require(item.get("sha256") == sha256, f"{artifact_id}: sha256 mismatch")
        require(item.get("size") == size, f"{artifact_id}: size mismatch")
    return path, data


def verify_architecture(path: Path) -> str:
    require(path.is_file() and not path.is_symlink(), "canonical architecture file missing")
    actual = digest(path)
    require(
        actual == ARCHITECTURE_SHA256,
        "canonical architecture SHA-256 mismatch: "
        f"expected={ARCHITECTURE_SHA256} actual={actual}",
    )
    return actual


def check_program(argv: list[str], expected_text: str, label: str) -> None:
    try:
        result = subprocess.run(argv, check=False, capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise CertificationError(f"{label}: cannot execute: {exc}") from exc
    output = (result.stdout + "\n" + result.stderr).strip()
    require(result.returncode == 0, f"{label}: version command failed ({result.returncode})")
    require(expected_text in output, f"{label}: expected version {expected_text!r}, got {output!r}")


def validate_runtime(root: Path) -> None:
    require(sys.version_info[:3] == (3, 13, 15), f"Python 3.13.15 required, got {sys.version.split()[0]}")
    wrapper = root / "tools/runtime/python/bin/python"
    require(wrapper.is_file() and os.access(wrapper, os.X_OK), "project-local Python wrapper missing")

    sjasmplus = root / "tools/runtime/sjasmplus/bin/sjasmplus"
    fuse = root / "tools/runtime/fuse/bin/fuse"
    tzxlist = root / "tools/runtime/fuse-utils/bin/tzxlist"
    rom = root / "tools/runtime/fuse/roms/48.rom"

    require(sjasmplus.is_file(), "sjasmplus executable missing")
    require(fuse.is_file(), "Fuse executable missing")
    require(tzxlist.is_file(), "Fuse-utils tzxlist executable missing")
    require(rom.is_file() and not rom.is_symlink(), "canonical 48K ROM missing")
    require(rom.stat().st_size == EXPECTED["zx48-rom"][2], "canonical 48K ROM size mismatch")
    require(digest(rom) == EXPECTED["zx48-rom"][1], "canonical 48K ROM sha256 mismatch")

    check_program([str(sjasmplus), "--version"], "1.24.0", "sjasmplus")
    check_program([str(fuse), "--version"], "1.9.2", "Fuse")
    check_program([str(tzxlist), "--version"], "1.4.7", "Fuse-utils")


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify the pinned ZX-UX development environment.")
    parser.add_argument("--manifest", help="root-relative manifest path, used by the negative-test harness")
    parser.add_argument("--metadata-only", action="store_true", help="validate lock and architecture without runtime tools")
    args = parser.parse_args()

    try:
        root = find_root(Path(__file__).resolve())
        manifest_path, _ = load_manifest(root, args.manifest)
        architecture = root / ARCHITECTURE
        architecture_sha256 = verify_architecture(architecture)
        if not args.metadata_only:
            validate_runtime(root)
        print(f"root={root}")
        print(f"manifest={manifest_path}")
        print(f"architecture_sha256={architecture_sha256}")
        print(FINAL_MARKER)
        return 0
    except (CertificationError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ZX-UX DEVELOPMENT ENVIRONMENT CERTIFICATION FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
