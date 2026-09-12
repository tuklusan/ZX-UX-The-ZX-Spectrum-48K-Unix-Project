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
import os
from pathlib import Path
import subprocess
import tempfile
import time
from typing import Sequence

ROOT_MARKER = b"ZX-UX project root"
DEFAULT_TIMEOUT_SECONDS = 30.0
TOOLCHAIN_LOCK = Path("tools/manifest/toolchain.lock.json")
ARCHITECTURE = Path("docs/01-ZX-UX-ARCHITECTURE-REV11.md")


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


@dataclass(frozen=True)
class SourceState:
    source_commit: str
    toolchain_lock_sha256: str
    architecture_sha256: str
    worktree_clean: bool


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


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        timeout=15,
    )
    if result.returncode != 0:
        raise DriverError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def read_source_state(root: Path) -> SourceState:
    source_commit = _git(root, "rev-parse", "--verify", "HEAD").strip()
    if len(source_commit) != 40 or any(ch not in "0123456789abcdef" for ch in source_commit):
        raise DriverError(f"invalid source commit identity: {source_commit!r}")
    status = _git(root, "status", "--porcelain=v1", "--untracked-files=all")
    return SourceState(
        source_commit=source_commit,
        toolchain_lock_sha256=sha256_file(root_path(root, TOOLCHAIN_LOCK)),
        architecture_sha256=sha256_file(root_path(root, ARCHITECTURE)),
        worktree_clean=(status == ""),
    )


def require_clean_source(root: Path) -> SourceState:
    state = read_source_state(root)
    if not state.worktree_clean:
        raise DriverError("source worktree must be clean before certification")
    return state


def resolve_evidence_dir(root: Path, source_commit: str, requested: str | Path | None = None) -> Path:
    if requested is None:
        configured = os.environ.get("ZXUX_EVIDENCE_DIR")
        requested = configured if configured else Path(tempfile.gettempdir()) / "zxux-certification" / source_commit
    destination = Path(requested).expanduser().resolve()
    root_resolved = root.resolve()
    try:
        destination.relative_to(root_resolved)
    except ValueError:
        pass
    else:
        raise DriverError("certification staging directory must be outside the source worktree")
    destination.mkdir(parents=True, exist_ok=True)
    return destination


def _normalize_project_path(root: Path, value: str) -> str:
    candidate = Path(value)
    if not candidate.is_absolute():
        return value
    try:
        return candidate.resolve().relative_to(root.resolve()).as_posix()
    except (OSError, ValueError):
        return value


def serialize_command(root: Path, command: CommandResult) -> dict[str, object]:
    data = asdict(command)
    data["argv"] = [_normalize_project_path(root, item) for item in command.argv]
    cwd = Path(command.cwd)
    try:
        data["cwd"] = cwd.resolve().relative_to(root.resolve()).as_posix() or "."
    except (OSError, ValueError):
        data["cwd"] = command.cwd
    if data["cwd"] == "":
        data["cwd"] = "."
    return data


def write_evidence(
    root: Path,
    evidence_dir: Path,
    source_state: SourceState,
    step: str,
    action: str,
    *,
    status: str,
    prerequisites: dict[str, str],
    commands: list[CommandResult],
    hashes: dict[str, str],
    assertions: list[dict[str, object]],
) -> Path:
    destination = evidence_dir / f"{step}.{action}.json"
    payload = {
        "schema": 2,
        "step": step,
        "action": action,
        "status": status,
        "source_commit": source_state.source_commit,
        "toolchain_lock_sha256": source_state.toolchain_lock_sha256,
        "architecture_sha256": source_state.architecture_sha256,
        "worktree_clean": source_state.worktree_clean,
        "prerequisites": dict(sorted(prerequisites.items())),
        "commands": [serialize_command(root, item) for item in commands],
        "hashes": dict(sorted(hashes.items())),
        "assertions": assertions,
    }
    destination.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return destination
