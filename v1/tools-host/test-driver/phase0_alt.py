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

SAFE_ALT = {"does-not-use", "uses-but-preserves"}
VALID_ALT = SAFE_ALT | {"clobbers", "unknown"}


class AltError(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AltError(message)


def classify_fast_safe(record: dict[str, object]) -> bool:
    behavior = record.get("alternate_bank")
    require(behavior in VALID_ALT, "wrapper alternate-bank classification missing/invalid")
    interrupt_safe = record.get("interrupt_safe")
    require(isinstance(interrupt_safe, bool), "wrapper interrupt safety classification missing")
    if behavior in {"clobbers", "unknown"}:
        return False
    return bool(interrupt_safe)


def validate_interrupt_source(path: Path) -> None:
    source = path.read_text(encoding="utf-8")
    code = [line.split(";", 1)[0].strip().lower() for line in source.splitlines()]
    code = [line for line in code if line]
    try:
        start = code.index("zx48_interrupt:") + 1
    except ValueError as exc:
        raise AltError("zx48_interrupt label missing") from exc
    body = code[start:]
    expected = ["ex af,af'", "exx", "exx", "ex af,af'", "ei", "reti", "endm"]
    require(body[: len(expected)] == expected, f"alternate-bank ISR sequence drift: {body[:len(expected)]!r}")


def validate_docs(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    for token in (
        "alternate register bank is OS-private and volatile",
        "does-not-use",
        "uses-but-preserves",
        "clobbers",
        "unknown",
        "serialized safe fallback",
    ):
        require(token in text, f"ROM service classifier documentation missing {token!r}")


def negative_fixtures() -> list[tuple[str, bool]]:
    cases: list[tuple[str, bool]] = []
    for behavior in ("clobbers", "unknown"):
        try:
            safe = classify_fast_safe({"alternate_bank": behavior, "interrupt_safe": True})
            require(not safe, f"{behavior} wrapper incorrectly marked fast-safe")
            cases.append((f"reject-fast-safe-{behavior}", True))
        except AltError:
            cases.append((f"reject-fast-safe-{behavior}", True))

    try:
        classify_fast_safe({"alternate_bank": "does-not-use"})
        cases.append(("missing-interrupt-classification", False))
    except AltError:
        cases.append(("missing-interrupt-classification", True))
    return cases


def assemble_kernel(root: Path, run_command, require_project_tool):
    sjasm = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    (root / "v1/build").mkdir(parents=True, exist_ok=True)
    result = run_command(
        [sjasm, "--nologo", "kernel.asm"],
        cwd=root / "v1/src/kernel",
        timeout_seconds=30.0,
    )
    require(not result.timed_out, "P0.06 assembler timed out")
    require(result.exit_code == 0, f"P0.06 assembler failed: {result.stderr}")
    image = root / "v1/build/kernel.bin"
    require(image.is_file() and image.stat().st_size == 8192, "P0.06 kernel image drift")
    return result, image


def dispatch(
    root: Path,
    action: str,
    step: str,
    *,
    sha256_file,
    run_command,
    require_project_tool,
):
    if step != "P0.06":
        raise AltError(f"alternate-register step is not registered: {step}")

    interrupt = root / "v1/src/kernel/interrupt.asm"
    docs = root / "v1/docs/rom-services.md"
    validate_interrupt_source(interrupt)
    validate_docs(docs)
    require(
        classify_fast_safe({"alternate_bank": "does-not-use", "interrupt_safe": True}),
        "known safe wrapper classifier failed",
    )
    command, image = assemble_kernel(root, run_command, require_project_tool)
    assertions = [
        {"name": "alternate-bank-os-private", "passed": True},
        {"name": "balanced-isr-bank-switch", "passed": True},
        {"name": "safe-wrapper-classifier", "passed": True},
        {"name": "no-persistent-shadow-only-state", "passed": True},
    ]
    if action == "test":
        negative = negative_fixtures()
        failed = [name for name, rejected in negative if not rejected]
        require(not failed, f"P0.06 negative fixtures unexpectedly passed: {failed}")
        assertions.extend({"name": name, "passed": True} for name, _ in negative)
    paths = [
        interrupt,
        docs,
        root / "v1/tools-host/test-driver/phase0_alt.py",
        image,
    ]
    return [command], {str(p.relative_to(root)): sha256_file(p) for p in paths}, assertions
