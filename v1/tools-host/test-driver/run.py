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
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import shutil
import tempfile
import time
from typing import Sequence

import asm_policy
import emulator_safety
import evidence as evidence_contract

ROOT_MARKER = b"ZX-UX project root"
DEFAULT_TIMEOUT_SECONDS = 30.0
CERT_DIR = Path("v1/dist/certification")


class DriverError(RuntimeError):
    """A deterministic build/test-driver failure."""


@dataclass(frozen=True)
class CommandResult:
    argv: list[str]
    cwd: str
    exit_code: int | None
    timed_out: bool
    duration_ms: int
    stdout: str
    stderr: str


def find_root(start: Path) -> Path:
    current = start.resolve()
    if current.is_file():
        current = current.parent
    for candidate in (current, *current.parents):
        marker = candidate / ".zxux-root"
        if marker.is_file() and not marker.is_symlink() and marker.read_bytes() == ROOT_MARKER:
            return candidate
    raise DriverError("canonical .zxux-root marker not found")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def root_path(root: Path, relative: str | Path) -> Path:
    path = (root / relative).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise DriverError(f"path escapes project root: {relative}") from exc
    return path


def require_project_tool(root: Path, relative: str | Path) -> Path:
    tool = root_path(root, relative)
    if not tool.is_file():
        raise DriverError(f"required project-local tool missing: {relative}")
    return tool


def run_command(
    argv: Sequence[str | Path],
    *,
    cwd: Path,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> CommandResult:
    if not argv:
        raise DriverError("empty argv")
    args = [str(item) for item in argv]
    started = time.monotonic()
    try:
        completed = subprocess.run(
            args,
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        elapsed = int((time.monotonic() - started) * 1000)
        stdout = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        return CommandResult(args, str(cwd), None, True, elapsed, stdout, stderr)
    elapsed = int((time.monotonic() - started) * 1000)
    return CommandResult(
        args,
        str(cwd),
        completed.returncode,
        False,
        elapsed,
        completed.stdout,
        completed.stderr,
    )


def write_evidence(
    root: Path,
    step: str,
    action: str,
    *,
    status: str,
    commands: list[CommandResult],
    hashes: dict[str, str],
    assertions: list[dict[str, object]],
) -> Path:
    destination = root_path(root, CERT_DIR / f"{step}.{action}.json")
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": 1,
        "step": step,
        "action": action,
        "status": status,
        "commands": [asdict(item) for item in commands],
        "hashes": dict(sorted(hashes.items())),
        "assertions": assertions,
    }
    destination.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return destination


def self_build(root: Path) -> tuple[list[CommandResult], dict[str, str], list[dict[str, object]]]:
    driver = root_path(root, "v1/tools-host/test-driver/run.py")
    plan = root_path(root, "v1/docs/test-plan.md")
    verifier = root_path(root, "tools/scripts/verify-environment.py")
    lock = root_path(root, "tools/manifest/toolchain.lock.json")
    for required in (driver, plan, verifier, lock):
        if not required.is_file():
            raise DriverError(f"E0.03 required file missing: {required.relative_to(root)}")

    python_tool = require_project_tool(root, "tools/runtime/python/bin/python")
    syntax_code = (
        "import ast,pathlib,sys; "
        "p=pathlib.Path(sys.argv[1]); "
        "ast.parse(p.read_text(encoding='utf-8'), filename=str(p))"
    )
    check = run_command(
        [python_tool, "-c", syntax_code, driver],
        cwd=root,
        timeout_seconds=15.0,
    )
    if check.timed_out or check.exit_code != 0:
        raise DriverError("E0.03 driver syntax check failed")
    bytecode_dir = driver.parent / "__pycache__"
    if bytecode_dir.exists():
        raise DriverError("E0.03 syntax check created repository bytecode")

    hashes = {
        str(driver.relative_to(root)): sha256_file(driver),
        str(plan.relative_to(root)): sha256_file(plan),
        str(verifier.relative_to(root)): sha256_file(verifier),
        str(lock.relative_to(root)): sha256_file(lock),
    }
    assertions = [
        {"name": "root-marker", "passed": True, "detail": str(root)},
        {"name": "project-local-python", "passed": True, "detail": str(python_tool.relative_to(root))},
        {"name": "absolute-tool-path", "passed": Path(check.argv[0]).is_absolute()},
        {"name": "argv-is-list", "passed": isinstance(check.argv, list)},
        {"name": "syntax-check-no-bytecode", "passed": not bytecode_dir.exists()},
    ]
    return [check], hashes, assertions


def self_test(root: Path) -> tuple[list[CommandResult], dict[str, str], list[dict[str, object]]]:
    python_tool = require_project_tool(root, "tools/runtime/python/bin/python")
    echo_code = "import sys; print(sys.argv[1]); print(sys.argv[2])"
    echo = run_command(
        [python_tool, "-c", echo_code, "two words", "literal * value"],
        cwd=root,
        timeout_seconds=5.0,
    )
    if echo.timed_out or echo.exit_code != 0:
        raise DriverError("E0.03 argv preservation self-test failed")
    expected = "two words\nliteral * value\n"
    if echo.stdout != expected:
        raise DriverError(f"E0.03 argv preservation mismatch: {echo.stdout!r}")

    timeout_code = "import time; time.sleep(5)"
    timed = run_command(
        [python_tool, "-c", timeout_code],
        cwd=root,
        timeout_seconds=0.1,
    )
    if not timed.timed_out:
        raise DriverError("E0.03 timeout self-test did not terminate the child")

    with tempfile.TemporaryDirectory(prefix="zxux-e003-") as temporary:
        copied_root = Path(temporary) / "moved-project"
        copied_driver = copied_root / "v1/tools-host/test-driver/run.py"
        copied_driver.parent.mkdir(parents=True)
        (copied_root / ".zxux-root").write_bytes(ROOT_MARKER)
        shutil.copyfile(Path(__file__).resolve(), copied_driver)
        for module_name in ("evidence.py", "asm_policy.py", "emulator_safety.py"):
            shutil.copyfile(Path(__file__).with_name(module_name), copied_driver.with_name(module_name))
        relocated = run_command(
            [python_tool, copied_driver, "build", "--step", "E0.03", "--probe-root"],
            cwd=Path(temporary),
            timeout_seconds=5.0,
        )
        if relocated.timed_out or relocated.exit_code != 0:
            raise DriverError("E0.03 relocated-root self-test failed")
        if relocated.stdout.strip() != str(copied_root.resolve()):
            raise DriverError("E0.03 relocated-root resolution mismatch")

    hashes = {"v1/tools-host/test-driver/run.py": sha256_file(Path(__file__).resolve())}
    assertions = [
        {"name": "argv-preserved", "passed": True},
        {"name": "timeout-enforced", "passed": True, "duration_ms": timed.duration_ms},
        {"name": "no-shell-flattening", "passed": True},
        {"name": "relocated-root", "passed": True},
    ]
    return [echo, timed, relocated], hashes, assertions


def e004_build(root: Path) -> tuple[list[CommandResult], dict[str, str], list[dict[str, object]]]:
    validator = root_path(root, "v1/tools-host/test-driver/evidence.py")
    plan = root_path(root, "v1/docs/test-plan.md")
    readme = root_path(root, "v1/dist/certification/README.md")
    for required in (validator, plan, readme):
        if not required.is_file():
            raise DriverError(f"E0.04 required file missing: {required.relative_to(root)}")

    fixture = evidence_contract.valid_fixture()
    try:
        evidence_contract.validate_final_record(fixture)
    except evidence_contract.EvidenceError as exc:
        raise DriverError(f"E0.04 valid evidence fixture rejected: {exc}") from exc

    hashes = {
        str(validator.relative_to(root)): sha256_file(validator),
        str(plan.relative_to(root)): sha256_file(plan),
        str(readme.relative_to(root)): sha256_file(readme),
    }
    assertions = [
        {"name": "valid-final-record-accepted", "passed": True},
        {"name": "required-hashes-present", "passed": True},
        {"name": "pass-marker-present", "passed": True},
        {"name": "clean-worktree-claim-present", "passed": True},
    ]
    return [], hashes, assertions


def e004_test(root: Path) -> tuple[list[CommandResult], dict[str, str], list[dict[str, object]]]:
    validator = root_path(root, "v1/tools-host/test-driver/evidence.py")
    cases: list[tuple[str, dict[str, object]]] = []

    missing_hash = evidence_contract.valid_fixture()
    missing_hash.pop("toolchain_lock_sha256")
    cases.append(("missing-hash", missing_hash))

    missing_marker = evidence_contract.valid_fixture()
    missing_marker.pop("pass_marker")
    cases.append(("missing-pass-marker", missing_marker))

    dirty = evidence_contract.valid_fixture()
    dirty["worktree_clean"] = False
    cases.append(("dirty-worktree", dirty))

    failed_prerequisite = evidence_contract.valid_fixture()
    failed_prerequisite["prerequisites"] = {"E0.03": "FAIL"}
    cases.append(("failed-prerequisite", failed_prerequisite))

    assertions: list[dict[str, object]] = []
    for name, record in cases:
        rejected = False
        detail = ""
        try:
            evidence_contract.validate_final_record(record)
        except evidence_contract.EvidenceError as exc:
            rejected = True
            detail = str(exc)
        if not rejected:
            raise DriverError(f"E0.04 negative fixture unexpectedly passed: {name}")
        assertions.append({"name": name, "passed": True, "detail": detail})

    return [], {str(validator.relative_to(root)): sha256_file(validator)}, assertions


def e005_build(root: Path) -> tuple[list[CommandResult], dict[str, str], list[dict[str, object]]]:
    oracle = root_path(root, "v1/tools-host/test-driver/asm_policy.py")
    abi = root_path(root, "v1/docs/abi.md")
    include = root_path(root, "v1/include/zx48ux.inc")
    for required in (oracle, abi, include):
        if not required.is_file():
            raise DriverError(f"E0.05 required file missing: {required.relative_to(root)}")

    fixture_path, fixture_text, review_evidence = asm_policy.positive_fixture()
    findings = asm_policy.scan_source(fixture_path, fixture_text)
    findings.extend(asm_policy.review_findings(review_evidence))
    if findings:
        raise DriverError(f"E0.05 positive policy fixture failed: {findings!r}")

    repository_findings: list[str] = []
    candidate_paths = [include]
    source_root = root_path(root, "v1/src")
    if source_root.is_dir():
        candidate_paths.extend(sorted(source_root.rglob("*.asm")))
        candidate_paths.extend(sorted(source_root.rglob("*.inc")))
    for candidate in candidate_paths:
        relative = candidate.relative_to(root)
        for finding in asm_policy.scan_source(relative, candidate.read_text(encoding="utf-8")):
            repository_findings.append(f"{relative}:{finding.line}:{finding.rule}:{finding.detail}")
    if repository_findings:
        raise DriverError("E0.05 repository policy findings: " + " | ".join(repository_findings))

    hashes = {
        str(oracle.relative_to(root)): sha256_file(oracle),
        str(abi.relative_to(root)): sha256_file(abi),
        str(include.relative_to(root)): sha256_file(include),
    }
    assertions = [
        {"name": "positive-policy-fixture", "passed": True},
        {"name": "repository-assembly-policy", "passed": True},
        {"name": "review-evidence-complete", "passed": True},
    ]
    return [], hashes, assertions


def e005_test(root: Path) -> tuple[list[CommandResult], dict[str, str], list[dict[str, object]]]:
    oracle = root_path(root, "v1/tools-host/test-driver/asm_policy.py")
    assertions: list[dict[str, object]] = []

    for expected_rule, path, text in asm_policy.negative_fixtures():
        rules = {finding.rule for finding in asm_policy.scan_source(path, text)}
        if expected_rule not in rules:
            raise DriverError(f"E0.05 negative fixture did not trigger {expected_rule}: {sorted(rules)}")
        assertions.append({"name": f"reject-{expected_rule}", "passed": True})

    seed_rules = {
        finding.rule
        for finding in asm_policy.scan_source(
            Path("v1/src/kernel/keyboard.asm"),
            "    ld a,r ; NONSECURITY_SEED_ONLY\n",
        )
    }
    if "r-not-correctness-source" in seed_rules:
        raise DriverError("E0.05 legal non-security R seed fixture was rejected")
    assertions.append({"name": "allow-r-nonsecurity-seed", "passed": True})

    for review_rule in asm_policy.REVIEW_ONLY_RULES:
        review = {name: True for name in asm_policy.REVIEW_ONLY_RULES}
        review[review_rule] = False
        rules = {finding.rule for finding in asm_policy.review_findings(review)}
        expected = f"review-evidence:{review_rule}"
        if expected not in rules:
            raise DriverError(f"E0.05 missing review evidence did not trigger {expected}")
        assertions.append({"name": f"require-{review_rule}", "passed": True})

    return [], {str(oracle.relative_to(root)): sha256_file(oracle)}, assertions


def e006_build(root: Path) -> tuple[list[CommandResult], dict[str, str], list[dict[str, object]]]:
    validator = root_path(root, "v1/tools-host/test-driver/emulator_safety.py")
    contract = root_path(root, "v1/tests/emulator/safety-contract.toml")
    plan = root_path(root, "v1/docs/test-plan.md")
    for required in (validator, contract, plan):
        if not required.is_file():
            raise DriverError(f"E0.06 required file missing: {required.relative_to(root)}")
    try:
        emulator_safety.validate(emulator_safety.load(contract))
    except emulator_safety.SafetyContractError as exc:
        raise DriverError(f"E0.06 safety contract rejected: {exc}") from exc
    hashes = {
        str(validator.relative_to(root)): sha256_file(validator),
        str(contract.relative_to(root)): sha256_file(contract),
        str(plan.relative_to(root)): sha256_file(plan),
    }
    assertions = [
        {"name": "four-level-evidence-hierarchy", "passed": True},
        {"name": "known-writable-rom-call-stack", "passed": True},
        {"name": "hard-emulator-timeout", "passed": True},
        {"name": "physical-claim-boundary", "passed": True},
    ]
    return [], hashes, assertions


def e006_test(root: Path) -> tuple[list[CommandResult], dict[str, str], list[dict[str, object]]]:
    validator = root_path(root, "v1/tools-host/test-driver/emulator_safety.py")
    contract = root_path(root, "v1/tests/emulator/safety-contract.toml")
    valid = emulator_safety.load(contract)
    assertions: list[dict[str, object]] = []
    for name, fixture in emulator_safety.negative_fixtures(valid):
        rejected = False
        detail = ""
        try:
            emulator_safety.validate(fixture)
        except emulator_safety.SafetyContractError as exc:
            rejected = True
            detail = str(exc)
        if not rejected:
            raise DriverError(f"E0.06 unsafe fixture unexpectedly passed: {name}")
        assertions.append({"name": name, "passed": True, "detail": detail})
    return [], {str(validator.relative_to(root)): sha256_file(validator)}, assertions


def fuse_probe(root: Path) -> tuple[list[CommandResult], dict[str, str], list[dict[str, object]]]:
    fuse = require_project_tool(root, "tools/runtime/fuse/bin/fuse")
    result = run_command([fuse, "--version"], cwd=root, timeout_seconds=15.0)
    passed = not result.timed_out and result.exit_code == 0 and "1.9.2" in (result.stdout + result.stderr)
    if not passed:
        raise DriverError("pinned FUSE version probe failed")
    return (
        [result],
        {"tools/runtime/fuse/bin/fuse": sha256_file(fuse)},
        [
            {"name": "fuse-argv-list", "passed": True},
            {"name": "fuse-version-1.9.2", "passed": True},
        ],
    )


def dispatch(root: Path, action: str, step: str) -> tuple[list[CommandResult], dict[str, str], list[dict[str, object]]]:
    if step == "E0.03":
        return self_build(root) if action == "build" else self_test(root)
    if step == "E0.04":
        return e004_build(root) if action == "build" else e004_test(root)
    if step == "E0.05":
        return e005_build(root) if action == "build" else e005_test(root)
    if step == "E0.06":
        return e006_build(root) if action == "build" else e006_test(root)
    if step == "E0.FUSE":
        return fuse_probe(root)
    raise DriverError(f"step is not registered with the test driver: {step}")


def main() -> int:
    parser = argparse.ArgumentParser(description="ZX-UX deterministic host build/test driver.")
    parser.add_argument("action", choices=("build", "test"))
    parser.add_argument("--step", required=True)
    parser.add_argument("--probe-root", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()

    try:
        root = find_root(Path(__file__))
        if args.probe_root:
            print(root)
            return 0
        commands, hashes, assertions = dispatch(root, args.action, args.step)
        failed_assertions = [item for item in assertions if item.get("passed") is not True]
        status = "PASS" if not failed_assertions else "FAIL"
        evidence_path = write_evidence(
            root,
            args.step,
            args.action,
            status=status,
            commands=commands,
            hashes=hashes,
            assertions=assertions,
        )
        if failed_assertions:
            raise DriverError(f"{len(failed_assertions)} assertion(s) failed")
        print(f"ZX-UX {args.step} {args.action.upper()} PASS")
        print(f"evidence={evidence_path.relative_to(root)}")
        return 0
    except (DriverError, OSError, ValueError) as exc:
        print(f"ZX-UX TEST DRIVER FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
