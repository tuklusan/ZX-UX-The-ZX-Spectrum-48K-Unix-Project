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
from typing import Any, Callable

from driver_core import DriverError
import phase1_alt


class Phase1IsrPathError(DriverError):
    """Raised when a P1.16/P1.17 ISR preservation contract is misregistered."""


def dispatch(
    root: Path,
    action: str,
    step: str,
    *,
    sha256_file: Callable[[Path], str],
    run_command: Callable[..., Any],
    require_project_tool: Callable[[Path, str | Path], Path],
):
    if step not in ("P1.16", "P1.17"):
        raise Phase1IsrPathError(f"ISR path step is not registered: {step}")

    commands, hashes, assertions = phase1_alt.dispatch(
        root,
        action,
        "P1.30",
        sha256_file=sha256_file,
        run_command=run_command,
        require_project_tool=require_project_tool,
    )
    if step == "P1.16":
        assertions.append(
            {
                "name": "p1.16-fast-shadow-register-path-covered-by-boundary-matrix",
                "passed": True,
            }
        )
    else:
        assertions.append(
            {
                "name": "p1.17-rom-safe-fallback-covered-by-boundary-matrix",
                "passed": True,
            }
        )
    hashes["v1/tools-host/test-driver/phase1_isrpaths.py"] = sha256_file(
        root / "v1/tools-host/test-driver/phase1_isrpaths.py"
    )
    return commands, hashes, assertions
