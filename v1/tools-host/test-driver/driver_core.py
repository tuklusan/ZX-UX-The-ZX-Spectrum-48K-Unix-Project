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

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import subprocess
import time
from typing import Sequence

ROOT_MARKER = b"ZX-UX project root"
DEFAULT_TIMEOUT_SECONDS = 30.0
CERT_DIR = Path("v1/dist/certification")


class DriverError(RuntimeError):
    """A deterministic build/test-driver failure."""


@dataclass(frozen=True)
class CommandResult:
    argv: list[str]
    cwd: str
    exit_code: int | None
    timed_out: bool
    duration_ms: int
    stdout: str
    stderr: str


def find_root(start: Path) -> Path:
    current = start.resolve()
    if current.is_file():
        current = current.parent
    for candidate in (current, *current.parents):
        marker = candidate / ".zxux-root"
        if marker.is_file() and not marker.is_symlink() and marker.read_bytes() == ROOT_MARKER:
            return candidate
    raise DriverError("canonical .zxux-root marker not found")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def root_path(root: Path, relative: str | Path) -> Path:
    path = (root / relative).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise DriverError(f"path escapes project root: {relative}") from exc
    return path


def require_project_tool(root: Path, relative: str | Path) -> Path:
    tool = root_path(root, relative)
    if not tool.is_file():
        raise DriverError(f"required project-local tool missing: {relative}")
    return tool


def run_command(
    argv: Sequence[str | Path],
    *,
    cwd: Path,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> CommandResult:
    if not argv:
        raise DriverError("empty argv")
    args = [str(item) for item in argv]
    started = time.monotonic()
    try:
        completed = subprocess.run(
            args,
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        elapsed = int((time.monotonic() - started) * 1000)
        stdout = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        return CommandResult(args, str(cwd), None, True, elapsed, stdout, stderr)
    elapsed = int((time.monotonic() - started) * 1000)
    return CommandResult(
        args,
        str(cwd),
        completed.returncode,
        False,
        elapsed,
        completed.stdout,
        completed.stderr,
    )


def write_evidence(
    root: Path,
    step: str,
    action: str,
    *,
    status: str,
    commands: list[CommandResult],
    hashes: dict[str, str],
    assertions: list[dict[str, object]],
) -> Path:
    destination = root_path(root, CERT_DIR / f"{step}.{action}.json")
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": 1,
        "step": step,
        "action": action,
        "status": status,
        "commands": [asdict(item) for item in commands],
        "hashes": dict(sorted(hashes.items())),
        "assertions": assertions,
    }
    destination.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return destination
