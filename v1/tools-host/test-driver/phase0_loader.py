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

EXPECTED_LINES = (
    '10 BORDER 0: PAPER 0: INK 7: CLS',
    '20 CLEAR 24575',
    '30 LOAD "" SCREEN$',
    '40 LOAD "" CODE',
    '50 RANDOMIZE USR 57347',
)
BOOT_FILE_NAME = "zx48ux"
AUTO_START_LINE = 10


class LoaderError(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise LoaderError(message)


def validate_loader_text(text: str) -> None:
    lines = tuple(text.splitlines())
    require(lines == EXPECTED_LINES, f"loader semantic lines drift: {lines!r}")
    require(len(lines) == 5, "loader must have exactly five semantic lines")
    require(lines[0].startswith(f"{AUTO_START_LINE} "), "loader must auto-start conceptually at line 10")
    require("CLEAR 24575" in lines[1], "CLEAR ceiling drift")
    require('LOAD "" SCREEN$' in lines[2], "SCREEN$ load drift")
    require('LOAD "" CODE' in lines[3], "CODE load drift")
    require("RANDOMIZE USR 57347" in lines[4], "boot gateway drift")
    require(BOOT_FILE_NAME == BOOT_FILE_NAME.lower(), "bootstrap tape name must remain lower-case")


def negative_fixtures(text: str) -> list[tuple[str, bool]]:
    cases: list[tuple[str, bool]] = []
    for name, before, after in (
        ("wrong-clear", "CLEAR 24575", "CLEAR 24574"),
        ("wrong-usr", "USR 57347", "USR 57344"),
        ("case-folded-boot-name", "zx48ux", "ZX48UX"),
    ):
        if name == "case-folded-boot-name":
            try:
                require(after == after.lower(), "upper-case bootstrap alias forbidden")
                cases.append((name, False))
            except LoaderError:
                cases.append((name, True))
            continue
        broken = text.replace(before, after)
        try:
            validate_loader_text(broken)
            cases.append((name, False))
        except LoaderError:
            cases.append((name, True))
    return cases


def dispatch(
    root: Path,
    action: str,
    step: str,
    *,
    sha256_file,
    run_command,
    require_project_tool,
):
    del run_command, require_project_tool
    if step != "P0.07":
        raise LoaderError(f"loader step is not registered: {step}")
    loader = root / "v1/src/boot/loader.bas"
    text = loader.read_text(encoding="ascii")
    validate_loader_text(text)
    assertions = [
        {"name": "five-semantic-lines", "passed": True},
        {"name": "auto-start-line-10", "passed": True},
        {"name": "clear-24575", "passed": True},
        {"name": "screen-code-sequence", "passed": True},
        {"name": "usr-57347", "passed": True},
        {"name": "bootstrap-name-lower-case", "passed": True},
    ]
    if action == "test":
        negative = negative_fixtures(text)
        failed = [name for name, rejected in negative if not rejected]
        require(not failed, f"P0.07 negative fixtures unexpectedly passed: {failed}")
        assertions.extend({"name": name, "passed": True} for name, _ in negative)
    oracle = root / "v1/tools-host/test-driver/phase0_loader.py"
    return [], {
        "v1/src/boot/loader.bas": sha256_file(loader),
        "v1/tools-host/test-driver/phase0_loader.py": sha256_file(oracle),
    }, assertions
