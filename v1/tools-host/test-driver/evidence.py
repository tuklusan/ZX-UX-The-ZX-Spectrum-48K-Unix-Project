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
from pathlib import Path, PurePosixPath
import re
import sys
from typing import Any

SCHEMA = 2
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
STEP_ID = re.compile(r"^(?:E0|P(?:0|[1-9]|10))\.[0-9]{2}$")
COMMON_FIELDS = (
    "schema",
    "step",
    "status",
    "source_commit",
    "toolchain_lock_sha256",
    "architecture_sha256",
    "worktree_clean",
    "prerequisites",
    "commands",
    "hashes",
    "assertions",
)


class EvidenceError(ValueError):
    """Raised when certification evidence is incomplete or inconsistent."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise EvidenceError(message)


def validate_hash(value: Any, field: str) -> None:
    require(
        isinstance(value, str) and HEX64.fullmatch(value) is not None,
        f"{field}: 64 lower-case hexadecimal digits required",
    )


def validate_relative_path(value: Any, field: str) -> None:
    require(isinstance(value, str) and value, f"{field}: nonempty root-relative path required")
    require("\\" not in value, f"{field}: '/' separators required")
    path = PurePosixPath(value)
    require(not path.is_absolute(), f"{field}: absolute paths are forbidden")
    require(value not in (".", ".."), f"{field}: project file path required")
    require(
        all(part not in ("", ".", "..") for part in path.parts),
        f"{field}: normalized root-relative path required",
    )
    require(str(path) == value, f"{field}: normalized root-relative path required")


def validate_commands(commands: Any) -> None:
    require(isinstance(commands, list), "commands must be a list")
    for index, command in enumerate(commands):
        prefix = f"commands[{index}]"
        require(isinstance(command, dict), f"{prefix}: object required")
        required = ("argv", "cwd", "exit_code", "timed_out", "duration_ms", "stdout", "stderr")
        missing = [field for field in required if field not in command]
        require(not missing, f"{prefix}: missing {', '.join(missing)}")
        require(
            isinstance(command["argv"], list)
            and command["argv"]
            and all(isinstance(item, str) for item in command["argv"]),
            f"{prefix}.argv: nonempty string list required",
        )
        require(isinstance(command["cwd"], str) and command["cwd"], f"{prefix}.cwd: string required")
        require(
            command["exit_code"] is None or isinstance(command["exit_code"], int),
            f"{prefix}.exit_code: integer or null required",
        )
        require(isinstance(command["timed_out"], bool), f"{prefix}.timed_out: Boolean required")
        require(
            isinstance(command["duration_ms"], int) and command["duration_ms"] >= 0,
            f"{prefix}.duration_ms: nonnegative integer required",
        )
        require(
            isinstance(command["stdout"], str) and isinstance(command["stderr"], str),
            f"{prefix}: stdout/stderr strings required",
        )


def validate_hashes(hashes: Any) -> None:
    require(isinstance(hashes, dict), "hashes must be an object")
    require(hashes, "hashes must not be empty")
    for name, value in hashes.items():
        validate_relative_path(name, "hash path")
        validate_hash(value, f"hash {name}")


def validate_assertions(assertions: Any, status: str) -> None:
    require(isinstance(assertions, list) and assertions, "assertions must be a nonempty list")
    names: set[str] = set()
    for assertion in assertions:
        require(isinstance(assertion, dict), "assertion must be an object")
        name = assertion.get("name")
        require(isinstance(name, str) and name, "assertion name required")
        require(name not in names, f"duplicate assertion name: {name}")
        names.add(name)
        require(isinstance(assertion.get("passed"), bool), "assertion passed must be Boolean")
    if status == "PASS":
        failed = [item["name"] for item in assertions if item["passed"] is not True]
        require(not failed, f"PASS record contains failed assertion(s): {', '.join(failed)}")


def validate_prerequisites(prerequisites: Any, status: str) -> None:
    require(isinstance(prerequisites, dict), "prerequisites must be an object")
    for name, prerequisite_status in prerequisites.items():
        require(
            isinstance(name, str) and STEP_ID.fullmatch(name) is not None,
            f"invalid prerequisite step: {name!r}",
        )
        require(
            prerequisite_status in ("PASS", "FAIL"),
            f"prerequisite {name!r}: PASS or FAIL required",
        )
        if status == "PASS":
            require(prerequisite_status == "PASS", f"prerequisite {name!r} is not PASS")


def validate_common(record: Any) -> None:
    require(isinstance(record, dict), "certification record must be an object")
    missing = [field for field in COMMON_FIELDS if field not in record]
    require(not missing, f"missing required field(s): {', '.join(missing)}")
    require(record["schema"] == SCHEMA, f"schema must be {SCHEMA}")
    require(
        isinstance(record["step"], str) and STEP_ID.fullmatch(record["step"]) is not None,
        "invalid step identifier",
    )
    require(record["status"] in ("PASS", "FAIL"), "status must be PASS or FAIL")
    require(
        isinstance(record["source_commit"], str) and HEX40.fullmatch(record["source_commit"]) is not None,
        "source_commit must be 40 lower-case hexadecimal digits",
    )
    validate_hash(record["toolchain_lock_sha256"], "toolchain_lock_sha256")
    validate_hash(record["architecture_sha256"], "architecture_sha256")
    require(isinstance(record["worktree_clean"], bool), "worktree_clean must be Boolean")
    if record["status"] == "PASS":
        require(record["worktree_clean"] is True, "dirty-worktree PASS certification is forbidden")
    validate_prerequisites(record["prerequisites"], record["status"])
    validate_commands(record["commands"])
    validate_hashes(record["hashes"])
    validate_assertions(record["assertions"], record["status"])


def validate_driver_record(record: Any) -> None:
    validate_common(record)
    require(record.get("action") in ("build", "test"), "driver action must be build or test")
    require("pass_marker" not in record, "driver build/test record must not contain pass_marker")


def validate_final_record(record: Any) -> None:
    validate_common(record)
    require(record.get("action") == "result", "final result action must be result")
    marker = record.get("pass_marker")
    require(
        isinstance(marker, str)
        and marker.startswith("ZX-UX ")
        and marker.endswith(" PASS")
        and record["step"] in marker,
        "valid step-specific PASS marker required",
    )
    require(record["status"] == "PASS", "final result status must be PASS")


def valid_fixture(step: str = "E0.04") -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "step": step,
        "action": "result",
        "status": "PASS",
        "pass_marker": f"ZX-UX {step} CERTIFICATION PASS",
        "source_commit": "0" * 40,
        "toolchain_lock_sha256": "1" * 64,
        "architecture_sha256": "2" * 64,
        "worktree_clean": True,
        "prerequisites": {"E0.03": "PASS"},
        "commands": [
            {
                "argv": ["tools/runtime/python/bin/python", "validator.py"],
                "cwd": ".",
                "exit_code": 0,
                "timed_out": False,
                "duration_ms": 1,
                "stdout": "",
                "stderr": "",
            }
        ],
        "hashes": {"v1/tools-host/test-driver/evidence.py": "3" * 64},
        "assertions": [{"name": "fixture", "passed": True}],
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
