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
import os
from pathlib import Path
import re
import shutil

from driver_core import DriverError

ALLOWED_SUFFIXES = frozenset({".sna", ".tap", ".tzx", ".scr", ".fmf", ".wav", ".flac", ".png"})
_STEP_RE = re.compile(r"^P(?:[6-9]|1[0-2])\.\d{2}$")


def configure_media_stage(evidence_dir: Path, step: str, action: str) -> Path:
    if not _STEP_RE.fullmatch(step):
        os.environ.pop("ZXUX_MEDIA_STAGE", None)
        os.environ.pop("ZXUX_ACTIVE_STEP", None)
        os.environ.pop("ZXUX_ACTIVE_ACTION", None)
        return evidence_dir
    if action not in {"build", "test"}:
        raise DriverError(f"invalid media-retention action: {action}")
    stage = (evidence_dir / "media-staging").resolve()
    stage.mkdir(parents=True, exist_ok=True)
    os.environ["ZXUX_MEDIA_STAGE"] = str(stage)
    os.environ["ZXUX_ACTIVE_STEP"] = step
    os.environ["ZXUX_ACTIVE_ACTION"] = action
    return stage


def _context() -> tuple[Path, str, str] | None:
    raw_stage = os.environ.get("ZXUX_MEDIA_STAGE")
    step = os.environ.get("ZXUX_ACTIVE_STEP")
    action = os.environ.get("ZXUX_ACTIVE_ACTION")
    if not raw_stage or not step or not action:
        return None
    if not _STEP_RE.fullmatch(step) or action not in {"build", "test"}:
        raise DriverError("invalid active media-retention context")
    return Path(raw_stage).resolve(), step, action


def _safe_label(label: str) -> str:
    value = re.sub(r"[^A-Za-z0-9._-]+", "-", label).strip("-.")
    return value or "media"


def retain_media_bytes(data: bytes, suffix: str, *, label: str = "media") -> Path | None:
    context = _context()
    if context is None:
        return None
    suffix = suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise DriverError(f"unsupported retained-media suffix: {suffix}")
    stage, step, action = context
    digest = hashlib.sha256(data).hexdigest()
    directory = stage / step / action
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / f"{_safe_label(label)}-{digest}{suffix}"
    if destination.exists():
        if destination.read_bytes() != data:
            raise DriverError(f"retained-media collision: {destination}")
    else:
        destination.write_bytes(data)
    return destination


def retain_media_file(path: Path, *, label: str | None = None) -> Path | None:
    source = Path(path)
    suffix = source.suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        return None
    if not source.is_file() or source.is_symlink():
        raise DriverError(f"retained media must be a regular file: {source}")
    return retain_media_bytes(source.read_bytes(), suffix, label=label or source.stem)


def capture_project_media(root: Path) -> list[Path]:
    captured: list[Path] = []
    build = root / "v1/build"
    if not build.is_dir():
        return captured
    for path in sorted(build.rglob("*")):
        if path.is_file() and not path.is_symlink() and path.suffix.lower() in ALLOWED_SUFFIXES:
            relative = path.relative_to(build).as_posix().replace("/", "-")
            retained = retain_media_file(path, label=f"build-{relative[:-len(path.suffix)]}")
            if retained is not None:
                captured.append(retained)
    return captured


def write_action_manifest(source_commit: str) -> Path | None:
    context = _context()
    if context is None:
        return None
    if len(source_commit) != 40 or any(ch not in "0123456789abcdef" for ch in source_commit):
        raise DriverError("invalid source commit for retained-media manifest")
    stage, step, action = context
    directory = stage / step / action
    directory.mkdir(parents=True, exist_ok=True)
    files = []
    for path in sorted(directory.iterdir()):
        if not path.is_file() or path.name == "manifest.json":
            continue
        if path.suffix.lower() not in ALLOWED_SUFFIXES:
            raise DriverError(f"unexpected staged retained-media file: {path}")
        payload = path.read_bytes()
        files.append(
            {
                "name": path.name,
                "sha256": hashlib.sha256(payload).hexdigest(),
                "size": len(payload),
            }
        )
    manifest = {
        "schema": 1,
        "step": step,
        "action": action,
        "source_commit": source_commit,
        "files": files,
    }
    destination = directory / "manifest.json"
    destination.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return destination
