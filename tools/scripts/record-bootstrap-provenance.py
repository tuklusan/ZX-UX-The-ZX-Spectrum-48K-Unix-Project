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
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys


ROOT_MARKER = b"ZX-UX project root"
LOCK_PATH = Path("tools/manifest/toolchain.lock.json")
PROVENANCE_CLASS = "informational-provenance-only"


class ProvenanceError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def find_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        marker = candidate / ".zxux-root"
        if marker.is_file() and marker.read_bytes() == ROOT_MARKER:
            return candidate
    raise ProvenanceError("canonical .zxux-root marker not found")


def run(argv: list[str], *, timeout: int = 30) -> str:
    result = subprocess.run(
        argv,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.returncode != 0:
        raise ProvenanceError(
            f"command failed ({result.returncode}): {' '.join(argv)}: "
            f"{result.stderr.strip() or result.stdout.strip()}"
        )
    return result.stdout


def installed_packages() -> list[dict[str, str]]:
    output = run([
        "dpkg-query",
        "-W",
        "-f=${binary:Package}\t${Version}\t${Architecture}\t${db:Status-Abbrev}\n",
    ])
    records: list[dict[str, str]] = []
    for line in output.splitlines():
        package, version, architecture, status = line.split("\t", 3)
        if not status.startswith("ii"):
            continue
        records.append({
            "package": package,
            "version": version,
            "architecture": architecture,
        })
    records.sort(key=lambda item: (item["package"], item["architecture"], item["version"]))
    return records


def run_optional(argv: list[str], *, timeout: int = 30) -> tuple[int, str, str]:
    result = subprocess.run(
        argv,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return result.returncode, result.stdout, result.stderr


def requested_packages(names: list[str]) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for requested in names:
        rc, stdout, stderr = run_optional([
            "dpkg-query",
            "-W",
            "-f=${binary:Package}\t${Version}\t${Architecture}\t${db:Status-Abbrev}\n",
            requested,
        ])
        record: dict[str, object] = {
            "requested": requested,
            "directly_installed": False,
            "apt_policy": run_optional(["apt-cache", "policy", requested])[1].strip(),
            "apt_showpkg": run_optional(["apt-cache", "showpkg", requested])[1].strip(),
        }
        if rc == 0 and stdout.strip():
            package, version, architecture, status = stdout.strip().split("\t", 3)
            if status.startswith("ii"):
                record.update({
                    "directly_installed": True,
                    "package": package,
                    "version": version,
                    "architecture": architecture,
                })
        else:
            record["dpkg_query_note"] = (stderr or stdout).strip()
        records.append(record)
    return records


def apt_history_tail() -> str:
    path = Path("/var/log/apt/history.log")
    if not path.is_file():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    return text[-50000:]

def first_nonempty(argv: list[str]) -> str:
    for line in run(argv).splitlines():
        if line.strip():
            return line.strip()
    return ""


def os_release() -> dict[str, str]:
    path = Path("/etc/os-release")
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key] = value.strip().strip('"')
    return values


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Record non-normative ZX-UX bootstrap-platform provenance."
    )
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    root = find_root(Path(__file__).resolve())
    lock = json.loads((root / LOCK_PATH).read_text(encoding="utf-8"))
    requested = list(lock["bootstrap"]["native_build_prerequisites"])
    output = Path(args.output)
    if not output.is_absolute():
        output = root / output
    output.parent.mkdir(parents=True, exist_ok=True)

    files = {
        "toolchain_lock": root / "tools/manifest/toolchain.lock.json",
        "bootstrap_script": root / "tools/scripts/bootstrap-environment.py",
        "verification_script": root / "tools/scripts/verify-environment.py",
        "runtime_setup_action": root / ".github/actions/setup-zxux-runtime/action.yml",
        "provenance_recorder": root / "tools/scripts/record-bootstrap-provenance.py",
    }

    payload = {
        "schema": 1,
        "classification": PROVENANCE_CLASS,
        "certification_requirement": False,
        "note": (
            "Recorded for historical reconstruction only. Resolved platform/package "
            "versions are not pinned acceptance criteria and are not consumed by "
            "verify-environment.py."
        ),
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "source": {
            "repository": os.environ.get("GITHUB_REPOSITORY"),
            "commit_sha": os.environ.get("GITHUB_SHA"),
            "git_head": first_nonempty(["git", "-C", str(root), "rev-parse", "HEAD"]),
            "workflow": os.environ.get("GITHUB_WORKFLOW"),
            "job": os.environ.get("GITHUB_JOB"),
            "run_id": os.environ.get("GITHUB_RUN_ID"),
            "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
        },
        "runner": {
            "runner_os": os.environ.get("RUNNER_OS"),
            "runner_arch": os.environ.get("RUNNER_ARCH"),
            "image_os": os.environ.get("ImageOS"),
            "image_version": os.environ.get("ImageVersion"),
            "os_release": os_release(),
            "kernel": {
                "system": platform.system(),
                "release": platform.release(),
                "version": platform.version(),
                "machine": platform.machine(),
            },
        },
        "bootstrap": {
            "python_executable": sys.executable,
            "python_version": platform.python_version(),
            "requested_native_build_prerequisites": requested_packages(requested),
            "installed_dpkg_packages": installed_packages(),
            "apt_history_tail": apt_history_tail(),
            "tool_versions": {
                "gcc": first_nonempty(["gcc", "--version"]),
                "g++": first_nonempty(["g++", "--version"]),
                "ld": first_nonempty(["ld", "--version"]),
                "make": first_nonempty(["make", "--version"]),
                "cmake": first_nonempty(["cmake", "--version"]),
                "pkg-config": first_nonempty(["pkg-config", "--version"]),
                "perl": first_nonempty(["perl", "-v"]),
                "dpkg": first_nonempty(["dpkg", "--version"]),
                "apt": first_nonempty(["apt-get", "--version"]),
            },
        },
        "zxux_inputs": {
            "sha256": {name: sha256(path) for name, path in files.items()},
            "toolchain_artifacts": [
                {
                    "id": item["id"],
                    "version": item["version"],
                    "kind": item["kind"],
                    "url": item["url"],
                    "size": item["size"],
                    "sha256": item["sha256"],
                }
                for item in lock["artifacts"]
            ],
        },
    }

    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    print(f"ZX-UX BOOTSTRAP PROVENANCE {PROVENANCE_CLASS}")
    print(f"provenance_file={output}")
    print(f"provenance_sha256={sha256(output)}")
    print(f"runner_image={payload['runner']['image_os']} {payload['runner']['image_version']}")
    for item in payload["bootstrap"]["requested_native_build_prerequisites"]:
        if item["directly_installed"]:
            print(
                "apt="
                f"{item['requested']}={item['version']} "
                f"package={item['package']} arch={item['architecture']}"
            )
        else:
            print(
                "apt="
                f"{item['requested']} resolved without a same-name installed package; "
                "provider/transaction detail retained in provenance"
            )

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, json.JSONDecodeError, subprocess.TimeoutExpired, ProvenanceError) as exc:
        print(f"ZX-UX BOOTSTRAP PROVENANCE FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
