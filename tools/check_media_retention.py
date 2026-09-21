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

import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md"
CERTIFICATION = ROOT / "v1/dist/certification"
MEDIA = ROOT / "v1/dist/media"
ALLOWED_SUFFIXES = frozenset({".sna", ".tap", ".tzx", ".scr", ".fmf", ".wav", ".flac", ".png"})
STEP_RE = re.compile(r"^P(?:[6-9]|1[0-2])\.\d{2}$")
HEADING_RE = re.compile(r"^## (P(?:[6-9]|1[0-2])\.\d{2}) - ")
ARTIFACT_PREFIX = "6. **Emulator test artifact:** "


class MediaError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def plan_requirements() -> dict[str, set[str]]:
    text = PLAN.read_text(encoding="utf-8")
    requirements: dict[str, set[str]] = {}
    current: str | None = None
    for line in text.splitlines():
        heading = HEADING_RE.match(line)
        if heading:
            current = heading.group(1)
            requirements.setdefault(current, set())
            continue
        if current is not None and line.startswith(ARTIFACT_PREFIX):
            field = line[len(ARTIFACT_PREFIX):]
            requirements[current] = {
                f".{token.lower()}" for token in ("SNA", "TAP", "TZX") if re.search(rf"\b{token}\b", field)
            }
    return requirements


def admitted_source_commit(step: str) -> str | None:
    path = CERTIFICATION / f"{step}.test.json"
    if not path.is_file():
        return None
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise MediaError(f"invalid admitted test evidence {path}: {exc}") from exc
    if record.get("step") != step or record.get("action") != "test":
        raise MediaError(f"test evidence identity mismatch: {path}")
    if record.get("status") != "PASS":
        return None
    commit = record.get("source_commit")
    if not isinstance(commit, str) or len(commit) != 40 or any(ch not in "0123456789abcdef" for ch in commit):
        raise MediaError(f"invalid source commit in admitted test evidence: {path}")
    return commit


def validate_manifest(step: str, expected_source: str | None) -> set[str]:
    directory = MEDIA / step
    manifest_path = directory / "manifest.json"
    if not directory.is_dir() or directory.is_symlink():
        raise MediaError(f"durable retained-media directory missing or invalid: {directory.relative_to(ROOT)}")
    if not manifest_path.is_file() or manifest_path.is_symlink():
        raise MediaError(f"durable retained-media manifest missing: {manifest_path.relative_to(ROOT)}")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise MediaError(f"invalid retained-media manifest {manifest_path.relative_to(ROOT)}: {exc}") from exc
    if manifest.get("schema") != 1 or manifest.get("step") != step:
        raise MediaError(f"retained-media manifest identity mismatch: {manifest_path.relative_to(ROOT)}")
    source_commit = manifest.get("source_commit")
    if not isinstance(source_commit, str) or len(source_commit) != 40 or any(ch not in "0123456789abcdef" for ch in source_commit):
        raise MediaError(f"invalid retained-media source commit: {manifest_path.relative_to(ROOT)}")
    if expected_source is not None and source_commit != expected_source:
        raise MediaError(f"retained-media source commit does not match admitted evidence for {step}")
    entries = manifest.get("files")
    if not isinstance(entries, list) or not entries:
        raise MediaError(f"retained-media manifest has no files: {manifest_path.relative_to(ROOT)}")

    listed: set[Path] = set()
    suffixes: set[str] = set()
    for item in entries:
        if not isinstance(item, dict):
            raise MediaError(f"invalid retained-media entry in {manifest_path.relative_to(ROOT)}")
        relative_text = item.get("path")
        action = item.get("action")
        if action not in {"build", "test"} or not isinstance(relative_text, str):
            raise MediaError(f"invalid retained-media action/path in {manifest_path.relative_to(ROOT)}")
        relative = Path(relative_text)
        if relative.is_absolute() or ".." in relative.parts or relative.parts[:1] != (action,):
            raise MediaError(f"unsafe retained-media path: {relative_text}")
        path = directory / relative
        if path in listed:
            raise MediaError(f"duplicate retained-media path: {relative_text}")
        listed.add(path)
        if not path.is_file() or path.is_symlink():
            raise MediaError(f"retained media missing or non-regular: {path.relative_to(ROOT)}")
        suffix = path.suffix.lower()
        if suffix not in ALLOWED_SUFFIXES:
            raise MediaError(f"unsupported retained-media suffix: {path.relative_to(ROOT)}")
        suffixes.add(suffix)
        size = path.stat().st_size
        digest = sha256(path)
        if item.get("size") != size or item.get("sha256") != digest:
            raise MediaError(f"retained-media hash/size mismatch: {path.relative_to(ROOT)}")

    actual = {
        path
        for path in directory.rglob("*")
        if path.is_file() and path != manifest_path
    }
    if actual != listed:
        extra = sorted(str(path.relative_to(ROOT)) for path in actual - listed)
        missing = sorted(str(path.relative_to(ROOT)) for path in listed - actual)
        raise MediaError(f"retained-media manifest/file-set mismatch for {step}: extra={extra} missing={missing}")
    return suffixes


def main() -> int:
    try:
        requirements = plan_requirements()
        if not requirements:
            raise MediaError("no P6-P12 emulator-artifact requirements parsed from REV07")

        existing_steps: set[str] = set()
        if MEDIA.exists():
            if not MEDIA.is_dir() or MEDIA.is_symlink():
                raise MediaError("v1/dist/media must be a real directory")
            for child in MEDIA.iterdir():
                if not child.is_dir() or child.is_symlink() or not STEP_RE.fullmatch(child.name):
                    raise MediaError(f"unexpected retained-media entry: {child.relative_to(ROOT)}")
                existing_steps.add(child.name)

        validated_suffixes: dict[str, set[str]] = {}
        for step in sorted(existing_steps):
            validated_suffixes[step] = validate_manifest(step, admitted_source_commit(step))

        for step, required_suffixes in sorted(requirements.items()):
            if not required_suffixes:
                continue
            source_commit = admitted_source_commit(step)
            if source_commit is None:
                continue
            if step not in validated_suffixes:
                validated_suffixes[step] = validate_manifest(step, source_commit)
            missing = required_suffixes - validated_suffixes[step]
            if missing:
                raise MediaError(f"{step} admitted without required durable media format(s): {sorted(missing)}")

        print(f"ZX-UX retained media gate passed: {len(existing_steps)} durable step manifest(s) validated.")
        return 0
    except (MediaError, OSError, UnicodeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
