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

import importlib.util
from pathlib import Path
import struct
import sys

from driver_core import DriverError
import phase6_tokenizer
import phase6_expansion
import phase6_operators
import phase6_binding
import phase6_builtins


class P628Error(DriverError):
    pass


def require(value, message):
    if not value:
        raise P628Error(message)


def _load(path: Path):
    spec = importlib.util.spec_from_file_location("zxux_shell_p628_golden", path)
    require(spec is not None and spec.loader is not None, f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def dispatch(root: Path, action: str, step: str, *, sha256_file, run_command, require_project_tool):
    if step != "P6.28":
        raise DriverError(f"Phase-6 shell-golden step is not registered: {step}")

    vector_path = root / "tests/emulator/shell_p628_golden.py"
    source = vector_path.read_text(encoding="utf-8")
    assertions = [
        {"name": "host-only-no-emulator-dependency",
         "passed": "fuse_harness" not in source and "run_sna" not in source},
        {"name": "no-host-shell-execution",
         "passed": all(token not in source for token in ("subprocess", "os.system", "shell=True", "/bin/sh"))},
        {"name": "rev16-vector-domains-covered",
         "passed": all(token in source for token in ("golden-quoting-escaping", "golden-expansion", "golden-operator", "golden-path", "golden-builtin", "negative-unsupported", "host-shell-divergence"))},
    ]
    require(all(item["passed"] for item in assertions), "P6.28 static contract failure")

    # P6+ admission retains generated Spectrum media. P6.28 remains host-only:
    # this deterministic TAP is a frozen golden-vector carrier and is never run.
    payload = b"ZXUX-P6.28-HOST-GOLDEN\0"
    block = bytes((0xFF,)) + payload
    block += bytes((0xFF ^ payload[0] if len(payload) == 1 else 0,))
    checksum = 0
    for byte in block[:-1]:
        checksum ^= byte
    block = block[:-1] + bytes((checksum,))
    tap = struct.pack("<H", len(block)) + block
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    tap_path = build / "p628-shell-golden.tap"
    tap_path.write_bytes(tap)

    if action == "test":
        vectors = _load(vector_path)
        assertions += vectors.run_vectors(
            phase6_tokenizer.tokenize,
            phase6_expansion.expand,
            phase6_operators.lex,
            phase6_binding.parse,
            phase6_builtins.CORE,
            phase6_builtins.HOOKS,
        )
        require(all(item.get("passed") is True for item in assertions), "P6.28 golden vector failure")

    hashes = {
        "tests/emulator/shell_p628_golden.py": sha256_file(vector_path),
        "v1/build/p628-shell-golden.tap": sha256_file(tap_path),
        "v1/tools-host/test-driver/phase6_shell_golden.py": sha256_file(root / "v1/tools-host/test-driver/phase6_shell_golden.py"),
        "v1/tools-host/test-driver/phase6_tokenizer.py": sha256_file(root / "v1/tools-host/test-driver/phase6_tokenizer.py"),
        "v1/tools-host/test-driver/phase6_expansion.py": sha256_file(root / "v1/tools-host/test-driver/phase6_expansion.py"),
        "v1/tools-host/test-driver/phase6_operators.py": sha256_file(root / "v1/tools-host/test-driver/phase6_operators.py"),
        "v1/tools-host/test-driver/phase6_binding.py": sha256_file(root / "v1/tools-host/test-driver/phase6_binding.py"),
        "v1/tools-host/test-driver/phase6_builtins.py": sha256_file(root / "v1/tools-host/test-driver/phase6_builtins.py"),
        "v1/tools-host/test-driver/run.py": sha256_file(root / "v1/tools-host/test-driver/run.py"),
        "v1/dist/certification/P6.27.build.json": sha256_file(root / "v1/dist/certification/P6.27.build.json"),
        "v1/dist/certification/P6.27.test.json": sha256_file(root / "v1/dist/certification/P6.27.test.json"),
        "v1/dist/media/P6.27/manifest.json": sha256_file(root / "v1/dist/media/P6.27/manifest.json"),
    }
    return [], hashes, assertions
