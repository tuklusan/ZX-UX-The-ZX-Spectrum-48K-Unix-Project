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
import platform
import re
import subprocess
import sys

ROOT_MARKER = b"ZX-UX project root"
CANONICAL_LOCK = Path("tools/manifest/toolchain.lock.json")
ARCHITECTURE = Path("docs/01-ZX-UX-ARCHITECTURE-REV11.md")
ARCHITECTURE_SHA256 = "1d736641e685c1d6136b66fc57d0c16fc662ce6ca4dfd640991743bb01bb706f"
FINAL_MARKER = "ZX-UX DEVELOPMENT ENVIRONMENT CERTIFICATION PASS"
REQUIRED_ARTIFACTS = {
    "python": ("source", "tools/runtime/python"),
    "sjasmplus": ("source", "tools/runtime/sjasmplus"),
    "libspectrum": ("source", "tools/runtime/libspectrum"),
    "fuse": ("source", "tools/runtime/fuse"),
    "fuse-utils": ("source", "tools/runtime/fuse-utils"),
    "zx48-rom": ("binary", "tools/runtime/fuse/roms/48.rom"),
}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


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


def read_json(path: Path) -> dict:
    require(path.is_file() and not path.is_symlink(), f"manifest is not a regular file: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(data, dict), "manifest root must be an object")
    return data


def validate_manifest(data: dict) -> dict[str, dict]:
    require(data.get("schema") == 1, "manifest schema must be 1")
    require(data.get("project") == "ZX-UX", "manifest project identity mismatch")
    require(data.get("root_marker") == ROOT_MARKER.decode("ascii"), "manifest root marker mismatch")

    bootstrap = data.get("bootstrap")
    require(isinstance(bootstrap, dict), "manifest bootstrap metadata missing")
    require(bootstrap.get("platform") == "linux", "bootstrap platform must be linux")
    require(bootstrap.get("bootstrap_python") == "3.13.15", "bootstrap Python must be 3.13.15")
    require(
        bootstrap.get("certified_python") == "tools/runtime/python/bin/python",
        "certified Python path mismatch",
    )
    require(bootstrap.get("download_policy") == "https-size-sha256", "bootstrap download policy mismatch")
    prerequisites = bootstrap.get("native_build_prerequisites")
    require(
        isinstance(prerequisites, list)
        and prerequisites
        and all(isinstance(item, str) and item for item in prerequisites)
        and len(set(prerequisites)) == len(prerequisites),
        "native build prerequisites must be a non-empty unique string list",
    )

    artifacts = data.get("artifacts")
    require(isinstance(artifacts, list), "manifest artifacts must be a list")
    by_id: dict[str, dict] = {}
    for item in artifacts:
        require(isinstance(item, dict), "manifest artifact entry must be an object")
        artifact_id = item.get("id")
        require(isinstance(artifact_id, str) and artifact_id not in by_id, "duplicate/invalid artifact id")
        by_id[artifact_id] = item

    require(set(by_id) == set(REQUIRED_ARTIFACTS), "manifest artifact set mismatch")
    for artifact_id, (kind, runtime_path) in REQUIRED_ARTIFACTS.items():
        item = by_id[artifact_id]
        require(item.get("kind") == kind, f"{artifact_id}: kind mismatch")
        require(isinstance(item.get("version"), str) and item["version"], f"{artifact_id}: version required")
        require(str(item.get("url", "")).startswith("https://"), f"{artifact_id}: HTTPS URL required")
        require(
            isinstance(item.get("sha256"), str) and SHA256_RE.fullmatch(item["sha256"]) is not None,
            f"{artifact_id}: lowercase SHA-256 required",
        )
        require(isinstance(item.get("size"), int) and item["size"] > 0, f"{artifact_id}: positive size required")
        require(item.get("runtime_path") == runtime_path, f"{artifact_id}: runtime_path mismatch")
    return by_id


def load_manifest(root: Path, requested: str | None) -> tuple[Path, dict, dict[str, dict]]:
    canonical_path = (root / CANONICAL_LOCK).resolve()
    canonical = read_json(canonical_path)
    canonical_by_id = validate_manifest(canonical)

    if requested is None:
        return canonical_path, canonical, canonical_by_id

    candidate_path = Path(requested)
    if not candidate_path.is_absolute():
        candidate_path = (root / candidate_path).resolve()
    candidate = read_json(candidate_path)
    by_id = validate_manifest(candidate)
    require(candidate == canonical, "manifest content mismatch against canonical lock")
    return candidate_path, candidate, by_id


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


def validate_runtime(root: Path, artifacts: dict[str, dict]) -> None:
    require(platform.system() == "Linux", f"Linux certification required, got {platform.system()}")
    python_item = artifacts["python"]
    expected_version = tuple(int(part) for part in python_item["version"].split("."))
    require(len(expected_version) == 3, "python version must contain three numeric components")
    require(sys.version_info[:3] == expected_version, f"Python {python_item['version']} required, got {sys.version.split()[0]}")

    certified_python = root / "tools/runtime/python/bin/python"
    require(certified_python.is_file() and os.access(certified_python, os.X_OK), "project-local Python missing")
    require(
        Path(sys.executable).resolve() == certified_python.resolve(),
        f"certification must run under {certified_python}",
    )

    sjasmplus = root / artifacts["sjasmplus"]["runtime_path"] / "bin/sjasmplus"
    fuse = root / artifacts["fuse"]["runtime_path"] / "bin/fuse"
    tzxlist = root / artifacts["fuse-utils"]["runtime_path"] / "bin/tzxlist"
    rom = root / artifacts["zx48-rom"]["runtime_path"]

    require(sjasmplus.is_file(), "sjasmplus executable missing")
    require(fuse.is_file(), "Fuse executable missing")
    require(tzxlist.is_file(), "Fuse-utils tzxlist executable missing")
    require(rom.is_file() and not rom.is_symlink(), "canonical 48K ROM missing")
    require(rom.stat().st_size == artifacts["zx48-rom"]["size"], "canonical 48K ROM size mismatch")
    require(digest(rom) == artifacts["zx48-rom"]["sha256"], "canonical 48K ROM sha256 mismatch")

    check_program([str(sjasmplus), "--version"], artifacts["sjasmplus"]["version"], "sjasmplus")
    check_program([str(fuse), "--version"], artifacts["fuse"]["version"], "Fuse")
    check_program([str(tzxlist), "--version"], artifacts["fuse-utils"]["version"], "Fuse-utils")


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify the pinned ZX-UX Linux development environment.")
    parser.add_argument("--manifest", help="manifest path used only by the E0.01 negative-test harness")
    parser.add_argument("--metadata-only", action="store_true", help="validate lock and architecture without runtime tools")
    args = parser.parse_args()

    try:
        root = find_root(Path(__file__).resolve())
        manifest_path, _, artifacts = load_manifest(root, args.manifest)
        architecture = root / ARCHITECTURE
        architecture_sha256 = verify_architecture(architecture)
        if not args.metadata_only:
            validate_runtime(root, artifacts)
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
