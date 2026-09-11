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

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any

HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
STEP_ID = re.compile(r"^(?:E0|P(?:0|[1-9]|10))\.[0-9]{2}$")
REQUIRED_FINAL_FIELDS = (
    "schema",
    "step",
    "status",
    "pass_marker",
    "source_commit",
    "toolchain_lock_sha256",
    "architecture_sha256",
    "worktree_clean",
    "prerequisites",
)


class EvidenceError(ValueError):
    """Raised when certification evidence is incomplete or inconsistent."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise EvidenceError(message)


def validate_hash(value: Any, field: str) -> None:
    require(isinstance(value, str) and HEX64.fullmatch(value) is not None, f"{field}: 64 lower-case hexadecimal digits required")


def validate_final_record(record: Any) -> None:
    require(isinstance(record, dict), "final certification record must be an object")
    missing = [field for field in REQUIRED_FINAL_FIELDS if field not in record]
    require(not missing, f"missing required field(s): {', '.join(missing)}")
    require(record["schema"] == 1, "schema must be 1")
    require(isinstance(record["step"], str) and STEP_ID.fullmatch(record["step"]) is not None, "invalid step identifier")
    require(record["status"] == "PASS", "status must be PASS")
    require(
        isinstance(record["pass_marker"], str)
        and record["pass_marker"].startswith("ZX-UX ")
        and record["pass_marker"].endswith(" PASS")
        and record["step"] in record["pass_marker"],
        "valid step-specific PASS marker required",
    )
    require(
        isinstance(record["source_commit"], str) and HEX40.fullmatch(record["source_commit"]) is not None,
        "source_commit must be 40 lower-case hexadecimal digits",
    )
    validate_hash(record["toolchain_lock_sha256"], "toolchain_lock_sha256")
    validate_hash(record["architecture_sha256"], "architecture_sha256")
    require(record["worktree_clean"] is True, "dirty-worktree certification is forbidden")

    prerequisites = record["prerequisites"]
    require(isinstance(prerequisites, dict), "prerequisites must be an object")
    for name, status in prerequisites.items():
        require(isinstance(name, str) and name, "prerequisite name must be nonempty")
        require(status == "PASS", f"prerequisite {name!r} is not PASS")


def validate_driver_record(record: Any) -> None:
    require(isinstance(record, dict), "driver evidence record must be an object")
    for field in ("schema", "step", "action", "status", "commands", "hashes", "assertions"):
        require(field in record, f"driver record missing {field}")
    require(record["schema"] == 1, "driver schema must be 1")
    require(isinstance(record["step"], str) and record["step"], "driver step missing")
    require(record["action"] in ("build", "test"), "driver action must be build or test")
    require(record["status"] in ("PASS", "FAIL"), "driver status invalid")
    require(isinstance(record["commands"], list), "driver commands must be a list")
    require(isinstance(record["hashes"], dict), "driver hashes must be an object")
    for name, value in record["hashes"].items():
        require(isinstance(name, str) and name, "driver hash path must be nonempty")
        validate_hash(value, f"hash {name}")
    require(isinstance(record["assertions"], list), "driver assertions must be a list")
    for assertion in record["assertions"]:
        require(isinstance(assertion, dict), "assertion must be an object")
        require(isinstance(assertion.get("name"), str) and assertion["name"], "assertion name required")
        require(isinstance(assertion.get("passed"), bool), "assertion passed must be Boolean")


def valid_fixture(step: str = "E0.04") -> dict[str, Any]:
    return {
        "schema": 1,
        "step": step,
        "status": "PASS",
        "pass_marker": f"ZX-UX {step} CERTIFICATION PASS",
        "source_commit": "0" * 40,
        "toolchain_lock_sha256": "1" * 64,
        "architecture_sha256": "2" * 64,
        "worktree_clean": True,
        "prerequisites": {"E0.03": "PASS"},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate ZX-UX certification evidence JSON.")
    parser.add_argument("path", type=Path)
    parser.add_argument("--driver-record", action="store_true")
    args = parser.parse_args()
    try:
        record = json.loads(args.path.read_text(encoding="utf-8"))
        if args.driver_record:
            validate_driver_record(record)
        else:
            validate_final_record(record)
        print("ZX-UX EVIDENCE VALIDATION PASS")
        return 0
    except (OSError, json.JSONDecodeError, EvidenceError) as exc:
        print(f"ZX-UX EVIDENCE VALIDATION FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
