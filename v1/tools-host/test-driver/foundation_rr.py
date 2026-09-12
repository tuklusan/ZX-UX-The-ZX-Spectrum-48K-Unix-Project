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

import json
from pathlib import Path
import tempfile
from typing import Any

from driver_core import DriverError

ARCHITECTURE = "docs/01-ZX-UX-ARCHITECTURE-REV11.md"
ARCH_SHA256 = "1d736641e685c1d6136b66fc57d0c16fc662ce6ca4dfd640991743bb01bb706f"


def _e001(root: Path, action: str, *, sha256_file: Any, run_command: Any, require_project_tool: Any):
    python_tool = require_project_tool(root, "tools/runtime/python/bin/python")
    verifier = root / "tools/scripts/verify-environment.py"
    lock = root / "tools/manifest/toolchain.lock.json"
    if not verifier.is_file() or not lock.is_file():
        raise DriverError("E0.01 verifier/lock missing")
    hashes = {
        "tools/scripts/verify-environment.py": sha256_file(verifier),
        "tools/manifest/toolchain.lock.json": sha256_file(lock),
    }
    if action == "build":
        result = run_command([python_tool, verifier], cwd=root, timeout_seconds=60.0)
        marker = "ZX-UX DEVELOPMENT ENVIRONMENT CERTIFICATION PASS"
        if result.timed_out or result.exit_code != 0 or not result.stdout.rstrip().endswith(marker):
            raise DriverError("E0.01 final project-local environment certification failed")
        return [result], hashes, [
            {"name": "project-local-runtime", "passed": True},
            {"name": "final-certification-marker", "passed": True},
            {"name": "canonical-lock-authoritative", "passed": True},
        ]

    with tempfile.TemporaryDirectory(prefix="zxux-e001-") as temporary:
        candidate = Path(temporary) / "toolchain.lock.json"
        data = json.loads(lock.read_text(encoding="utf-8"))
        data["artifacts"][0]["sha256"] = "0" * 64
        candidate.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        result = run_command(
            [python_tool, verifier, "--metadata-only", "--manifest", candidate],
            cwd=root,
            timeout_seconds=30.0,
        )
    if result.timed_out or result.exit_code == 0:
        raise DriverError("E0.01 altered-lock negative fixture unexpectedly passed")
    return [result], hashes, [
        {"name": "altered-lock-rejected", "passed": True},
        {"name": "negative-failure-is-deterministic", "passed": True},
    ]


def _verify_architecture(path: Path, expected: str, sha256_file: Any) -> str:
    if not path.is_file() or path.is_symlink():
        raise DriverError("E0.02 canonical architecture path must be a regular non-symlink file")
    actual = sha256_file(path)
    if actual != expected:
        raise DriverError(f"E0.02 architecture digest mismatch: {actual}")
    return actual


def _e002(root: Path, action: str, *, sha256_file: Any, **_: Any):
    architecture = root / ARCHITECTURE
    if action == "build":
        actual = _verify_architecture(architecture, ARCH_SHA256, sha256_file)
        return [], {ARCHITECTURE: actual}, [
            {"name": "canonical-architecture-path", "passed": True},
            {"name": "architecture-sha256-exact", "passed": actual == ARCH_SHA256},
            {"name": "architecture-not-symlink", "passed": True},
        ]
    rejected = False
    detail = ""
    try:
        _verify_architecture(architecture, "0" * 64, sha256_file)
    except DriverError as exc:
        rejected = True
        detail = str(exc)
    if not rejected:
        raise DriverError("E0.02 wrong-digest negative fixture unexpectedly passed")
    return [], {ARCHITECTURE: sha256_file(architecture)}, [
        {"name": "wrong-architecture-digest-rejected", "passed": True, "detail": detail},
    ]


def dispatch(root: Path, action: str, step: str, **kwargs: Any):
    table = {"E0.01": _e001, "E0.02": _e002}
    handler = table.get(step)
    if handler is None:
        raise DriverError(f"R&R foundation step is not registered: {step}")
    return handler(root, action, **kwargs)
