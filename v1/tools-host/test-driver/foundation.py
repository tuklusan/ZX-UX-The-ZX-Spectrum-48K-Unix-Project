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
import shutil
import tempfile
from typing import Any

import asm_policy
import emulator_safety
import evidence as evidence_contract
from driver_core import DriverError, ROOT_MARKER


def self_build(
    root: Path,
    *,
    sha256_file: Any,
    run_command: Any,
    require_project_tool: Any,
) -> tuple[list[Any], dict[str, str], list[dict[str, object]]]:
    driver = root / "v1/tools-host/test-driver/run.py"
    plan = root / "v1/docs/test-plan.md"
    verifier = root / "tools/scripts/verify-environment.py"
    lock = root / "tools/manifest/toolchain.lock.json"
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
        [python_tool, "-B", "-c", syntax_code, driver],
        cwd=root,
        timeout_seconds=15.0,
    )
    if check.timed_out or check.exit_code != 0:
        raise DriverError("E0.03 driver syntax check failed")

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
        {"name": "syntax-check-no-bytecode", "passed": "-B" in check.argv},
    ]
    return [check], hashes, assertions


def self_test(
    root: Path,
    *,
    sha256_file: Any,
    run_command: Any,
    require_project_tool: Any,
) -> tuple[list[Any], dict[str, str], list[dict[str, object]]]:
    python_tool = require_project_tool(root, "tools/runtime/python/bin/python")
    echo_code = "import sys; print(sys.argv[1]); print(sys.argv[2])"
    echo = run_command(
        [python_tool, "-B", "-c", echo_code, "two words", "literal * value"],
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
        [python_tool, "-B", "-c", timeout_code],
        cwd=root,
        timeout_seconds=0.1,
    )
    if not timed.timed_out:
        raise DriverError("E0.03 timeout self-test did not terminate the child")

    with tempfile.TemporaryDirectory(prefix="zxux-e003-") as temporary:
        copied_root = Path(temporary) / "moved-project"
        copied_driver_dir = copied_root / "v1/tools-host/test-driver"
        copied_driver_dir.mkdir(parents=True)
        (copied_root / ".zxux-root").write_bytes(ROOT_MARKER)
        for module in Path(__file__).resolve().parent.glob("*.py"):
            shutil.copyfile(module, copied_driver_dir / module.name)
        copied_driver = copied_driver_dir / "run.py"
        relocated = run_command(
            [python_tool, "-B", copied_driver, "build", "--step", "E0.03", "--probe-root"],
            cwd=Path(temporary),
            timeout_seconds=5.0,
        )
        if relocated.timed_out or relocated.exit_code != 0:
            raise DriverError("E0.03 relocated-root self-test failed")
        if relocated.stdout.strip() != str(copied_root.resolve()):
            raise DriverError("E0.03 relocated-root resolution mismatch")

    driver_path = Path(__file__).resolve().with_name("run.py")
    hashes = {"v1/tools-host/test-driver/run.py": sha256_file(driver_path)}
    assertions = [
        {"name": "argv-preserved", "passed": True},
        {"name": "timeout-enforced", "passed": True, "duration_ms": timed.duration_ms},
        {"name": "no-shell-flattening", "passed": True},
        {"name": "relocated-root", "passed": True},
    ]
    return [echo, timed, relocated], hashes, assertions


def e004_build(root: Path, *, sha256_file: Any, **_: Any) -> tuple[list[Any], dict[str, str], list[dict[str, object]]]:
    validator = root / "v1/tools-host/test-driver/evidence.py"
    plan = root / "v1/docs/test-plan.md"
    readme = root / "v1/dist/certification/README.md"
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


def e004_test(root: Path, *, sha256_file: Any, **_: Any) -> tuple[list[Any], dict[str, str], list[dict[str, object]]]:
    validator = root / "v1/tools-host/test-driver/evidence.py"
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


def e005_build(root: Path, *, sha256_file: Any, **_: Any) -> tuple[list[Any], dict[str, str], list[dict[str, object]]]:
    oracle = root / "v1/tools-host/test-driver/asm_policy.py"
    abi = root / "v1/docs/abi.md"
    include = root / "v1/include/zx48ux.inc"
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
    source_root = root / "v1/src"
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


def e005_test(root: Path, *, sha256_file: Any, **_: Any) -> tuple[list[Any], dict[str, str], list[dict[str, object]]]:
    oracle = root / "v1/tools-host/test-driver/asm_policy.py"
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


def e006_build(root: Path, *, sha256_file: Any, **_: Any) -> tuple[list[Any], dict[str, str], list[dict[str, object]]]:
    validator = root / "v1/tools-host/test-driver/emulator_safety.py"
    contract = root / "v1/tests/emulator/safety-contract.toml"
    plan = root / "v1/docs/test-plan.md"
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


def e006_test(root: Path, *, sha256_file: Any, **_: Any) -> tuple[list[Any], dict[str, str], list[dict[str, object]]]:
    validator = root / "v1/tools-host/test-driver/emulator_safety.py"
    contract = root / "v1/tests/emulator/safety-contract.toml"
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


def fuse_probe(
    root: Path,
    *,
    sha256_file: Any,
    run_command: Any,
    require_project_tool: Any,
) -> tuple[list[Any], dict[str, str], list[dict[str, object]]]:
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


def dispatch(
    root: Path,
    action: str,
    step: str,
    *,
    sha256_file: Any,
    run_command: Any,
    require_project_tool: Any,
) -> tuple[list[Any], dict[str, str], list[dict[str, object]]]:
    kwargs = {
        "sha256_file": sha256_file,
        "run_command": run_command,
        "require_project_tool": require_project_tool,
    }
    if step == "E0.03":
        return self_build(root, **kwargs) if action == "build" else self_test(root, **kwargs)
    if step == "E0.04":
        return e004_build(root, **kwargs) if action == "build" else e004_test(root, **kwargs)
    if step == "E0.05":
        return e005_build(root, **kwargs) if action == "build" else e005_test(root, **kwargs)
    if step == "E0.06":
        return e006_build(root, **kwargs) if action == "build" else e006_test(root, **kwargs)
    if step == "E0.FUSE":
        return fuse_probe(root, **kwargs)
    raise DriverError(f"foundation step is not registered: {step}")
