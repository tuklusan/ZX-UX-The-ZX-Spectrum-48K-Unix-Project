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

import ast
import importlib.util
from pathlib import Path
import sys
from types import ModuleType
from typing import Callable

from driver_core import DriverError


class Phase2InspectorError(DriverError):
    """Raised when the independent P2.02 MEX1 inspector contract regresses."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Phase2InspectorError(message)


def _load(path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location("zxux_p202_inspect_mex", path)
    if spec is None or spec.loader is None:
        raise Phase2InspectorError(f"cannot load MEX1 inspector: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _import_roots(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".", 1)[0])
    return roots


def _rejects_exact(inspector: ModuleType, candidate: bytes, message: str) -> bool:
    try:
        inspector.inspect_bytes(candidate, base=0x6000)
    except inspector.MexError as exc:
        return str(exc) == message
    return False


def dispatch(
    root: Path,
    action: str,
    step: str,
    *,
    sha256_file: Callable[[Path], str],
    run_command: Callable[..., object],
    require_project_tool: Callable[[Path, str], Path],
):
    if step != "P2.02":
        raise DriverError(f"Phase-2 inspector step is not registered: {step}")

    inspector_path = require_project_tool(root, "v1/tools-host/inspect-mex/inspect.py")
    command = run_command([sys.executable, inspector_path, "--self-test"], cwd=root, timeout_seconds=10.0)
    require(not command.timed_out, "MEX1 inspector self-test timed out")
    require(command.exit_code == 0, f"MEX1 inspector self-test failed: {command.stderr.strip()}")
    require(command.stdout.strip() == "MEX1 inspector self-test PASS", "MEX1 inspector self-test output changed")

    inspector = _load(inspector_path)
    observed = inspector.inspect_bytes(inspector.SELF_TEST_GOLDEN, base=0x6000)
    allowed_imports = {"__future__", "argparse", "json", "pathlib", "sys"}
    imports = _import_roots(inspector_path)
    assertions = [
        {"name": "inspector-golden-bytes-exact", "passed": inspector.SELF_TEST_GOLDEN.hex() == "4d45583101001800030000000200400001001b003b03fda20100c90000"},
        {"name": "inspector-golden-decode-exact", "passed": observed == inspector.SELF_TEST_EXPECTED},
        {"name": "inspector-is-project-independent", "passed": imports <= allowed_imports},
        {"name": "inspector-self-test-command-exact", "passed": command.stdout.strip() == "MEX1 inspector self-test PASS"},
    ]

    if action == "test":
        header_crc_flip = bytearray(inspector.SELF_TEST_GOLDEN)
        header_crc_flip[22] ^= 1
        body_flip = bytearray(inspector.SELF_TEST_GOLDEN)
        body_flip[24] ^= 1
        assertions.extend([
            {"name": "reject-one-bit-header-crc-mutation", "passed": _rejects_exact(inspector, bytes(header_crc_flip), "MEX1 header CRC mismatch")},
            {"name": "reject-one-bit-body-mutation", "passed": _rejects_exact(inspector, bytes(body_flip), "MEX1 body CRC mismatch")},
            {"name": "reject-trailing-byte", "passed": _rejects_exact(inspector, inspector.SELF_TEST_GOLDEN + b"\x00", "MEX1 stored length/trailing-byte mismatch")},
        ])

    return [command], {
        "v1/tools-host/inspect-mex/inspect.py": sha256_file(inspector_path),
    }, assertions
