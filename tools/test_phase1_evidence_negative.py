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
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def run(*args: str, cwd: Path = ROOT, check: bool = True):
    result = subprocess.run(args, cwd=cwd, text=True, capture_output=True)
    if check and result.returncode:
        raise RuntimeError(result.stderr or result.stdout)
    return result


def mutate_json(path: Path, key: str, value) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    data[key] = value
    path.write_text(
        json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def main() -> int:
    if not (ROOT / "v1/dist/certification/phase-1.json").is_file():
        print("ZX-UX PHASE 1 EVIDENCE NEGATIVE PRE-ACTIVATION SKIP")
        return 0

    current = run(sys.executable, "tools/check_phase1_evidence.py", cwd=ROOT, check=False)
    if current.returncode:
        print(
            "ZX-UX PHASE 1 EVIDENCE NEGATIVE FAIL: current evidence probe failed",
            file=sys.stderr,
        )
        return 1
    if "PRE-ACTIVATION PASS" in current.stdout:
        required = run(
            sys.executable,
            "tools/check_phase1_evidence.py",
            "--require-active",
            cwd=ROOT,
            check=False,
        )
        if required.returncode == 0:
            print(
                "ZX-UX PHASE 1 EVIDENCE NEGATIVE FAIL: pre-activation state passed --require-active",
                file=sys.stderr,
            )
            return 1
        print("ZX-UX PHASE 1 EVIDENCE NEGATIVE PRE-ACTIVATION PASS")
        return 0

    work = Path(tempfile.mkdtemp(prefix="zxux-phase1-evidence-negative-"))
    try:
        shutil.rmtree(work)
        run("git", "worktree", "add", "--detach", str(work), "HEAD")
        target = work / "v1/dist/certification/P1.01.build.json"
        cases = []

        def missing() -> None:
            target.unlink()

        cases.append(("missing-record", missing))
        cases.append(("wrong-source", lambda: mutate_json(target, "source_commit", "0" * 40)))
        cases.append(
            (
                "wrong-toolchain",
                lambda: mutate_json(target, "toolchain_lock_sha256", "0" * 64),
            )
        )
        cases.append(
            (
                "wrong-architecture",
                lambda: mutate_json(target, "architecture_sha256", "0" * 64),
            )
        )
        cases.append(("non-clean", lambda: mutate_json(target, "worktree_clean", False)))
        cases.append(("wrong-step-identity", lambda: mutate_json(target, "step", "P1.02")))
        cases.append(
            (
                "wrong-prerequisite",
                lambda: mutate_json(target, "prerequisites", {"P0.33": "PASS"}),
            )
        )

        def rewritten() -> None:
            target.write_text(
                target.read_text(encoding="utf-8") + "\n", encoding="utf-8"
            )

        cases.append(("rewritten-durable-bytes", rewritten))
        for name, mutation in cases:
            run("git", "reset", "--hard", "HEAD", cwd=work)
            run("git", "clean", "-fd", cwd=work)
            mutation()
            result = run(
                sys.executable,
                "tools/check_phase1_evidence.py",
                "--require-active",
                cwd=work,
                check=False,
            )
            if result.returncode == 0:
                raise RuntimeError(f"negative case unexpectedly passed: {name}")

        run("git", "reset", "--hard", "HEAD", cwd=work)
        run("git", "clean", "-fd", cwd=work)
        strict = work / "v1/dist/certification/P1.40.test.json"
        data = json.loads(strict.read_text(encoding="utf-8"))
        data["assertions"] = [
            item
            for item in data.get("assertions", [])
            if item.get("name") != "accepted-im2-interrupt-observed-with-mid-ldir-bc"
        ]
        strict.write_text(
            json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        strict_result = run(
            sys.executable,
            "tools/check_phase1_evidence.py",
            "--require-active",
            cwd=work,
            check=False,
        )
        if strict_result.returncode == 0:
            raise RuntimeError("missing strict P1.40 proof unexpectedly passed")

        run("git", "reset", "--hard", "HEAD", cwd=work)
        run("git", "clean", "-fd", cwd=work)
        aggregate = work / "v1/dist/certification/phase-1.json"
        aggregate_data = json.loads(aggregate.read_text(encoding="utf-8"))
        aggregate_data["assertions"] = [
            item
            for item in aggregate_data.get("assertions", [])
            if item.get("name") != "p1-41-aggregate-sna-smoke-pass"
        ]
        aggregate.write_text(
            json.dumps(aggregate_data, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        aggregate_result = run(
            sys.executable,
            "tools/check_phase1_evidence.py",
            "--require-active",
            cwd=work,
            check=False,
        )
        if aggregate_result.returncode == 0:
            raise RuntimeError("missing Phase-1 aggregate proof unexpectedly passed")

        run("git", "reset", "--hard", "HEAD", cwd=work)
        run("git", "clean", "-fd", cwd=work)
        run("git", "config", "user.name", "ZX-UX CI Probe", cwd=work)
        run("git", "config", "user.email", "zxux-ci-probe@example.invalid", cwd=work)
        probe = work / ".phase1-descendant-probe"
        probe.write_text("future source descendant\n", encoding="utf-8")
        run("git", "add", probe.name, cwd=work)
        run("git", "commit", "-m", "Phase-1 descendant acceptance probe", cwd=work)
        descendant = run(
            sys.executable,
            "tools/check_phase1_evidence.py",
            "--require-active",
            cwd=work,
            check=False,
        )
        if descendant.returncode:
            raise RuntimeError(
                "valid later source descendant was rejected: "
                + (descendant.stderr or descendant.stdout)
            )
        print("ZX-UX PHASE 1 EVIDENCE NEGATIVE PASS")
        return 0
    except Exception as exc:
        print(f"ZX-UX PHASE 1 EVIDENCE NEGATIVE FAIL: {exc}", file=sys.stderr)
        return 1
    finally:
        run("git", "worktree", "remove", "--force", str(work), check=False)
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
