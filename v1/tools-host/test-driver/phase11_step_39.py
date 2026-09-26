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

import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
import tempfile

from driver_core import DriverError
from fuse_harness import FAIL_PC, PASS_PC, run_sna


class P1139Error(DriverError):
    pass


SDK_COMMIT = "84d144de2721cda5075c3a6610a422663b5e2f77"
SDK_TREE = "1c6b5bae84035ee853be9142b440792881c9ca9f"
REV17 = "d12baf0b47a7f8cd2dcd60b82f100ba19f9fddaabad43728a004a07214716bf8"
REV08 = "97461e9ed12253409b25e6a4a4063cf0ec556a7317f9e4a5938d77edb6a1a14c"
TEST_FILES = (
    "compiler/tests/test_conformance.py",
    "compiler/tests/test_game_regressions.py",
    "compiler/tests/test_release_regressions.py",
    "compiler/tests/test_security.py",
)
NATIVE_REVALIDATION = tuple(f"P11.{number:02d}" for number in range(2, 39))


def require(ok, message):
    if not ok:
        raise P1139Error(message)


def git_blob(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def imported_test_ids(sdk_root: Path) -> list[str]:
    out = []
    rx = re.compile(r"^\s+def (test_[A-Za-z0-9_]+)\(", re.MULTILINE)
    forbidden = (
        "@unittest.skip", "@unittest.expectedFailure", ".skipTest(",
        "pytest.mark.skip", "pytest.mark.xfail", "@pytest.mark.xfail",
    )
    for rel in TEST_FILES:
        text = (sdk_root / rel).read_text(encoding="utf-8")
        require(not any(token in text for token in forbidden),
                f"P11.39 imported SDK test skip/xfail marker forbidden: {rel}")
        out.extend(f"{rel}::{name}" for name in rx.findall(text))
    return out


def validate_test_map(mapping: dict, test_ids: list[str]) -> None:
    require(mapping.get("schema") == 1 and mapping.get("step") == "P11.39",
            "P11.39 SDK test mapping identity drift")
    require(mapping.get("sdk_commit") == SDK_COMMIT
            and mapping.get("expected_test_count") == 205,
            "P11.39 SDK test mapping pin/count drift")
    rows = mapping.get("tests")
    require(isinstance(rows, list) and len(rows) == 205,
            "P11.39 SDK test mapping must contain exactly 205 rows")
    ids = [row.get("id") for row in rows]
    require(ids == test_ids and len(set(ids)) == 205,
            "P11.39 SDK test mapping is incomplete, reordered, or duplicated")
    allowed = {f"P11.{n:02d}" for n in range(2, 39)}
    for row in rows:
        owners = row.get("native_owner_steps")
        adapter = row.get("adapter")
        require(isinstance(owners, list) and owners
                and all(owner in allowed for owner in owners),
                f"P11.39 invalid native owner mapping: {row.get('id')}")
        require(row.get("original_intent_preserved") is True,
                f"P11.39 weakened imported test intent: {row.get('id')}")
        require(adapter is None or (isinstance(adapter, str) and adapter.strip()),
                f"P11.39 invalid host adapter rationale: {row.get('id')}")


def validate_source_manifest(root: Path, data: dict) -> list[Path]:
    require(data.get("schema") == 1 and data.get("step") == "P11.39"
            and data.get("sdk_commit") == SDK_COMMIT,
            "P11.39 C-source manifest identity drift")
    current = sorted((root / "v1/src/demos").glob("*.c"))
    rows = data.get("sources")
    require(isinstance(rows, list) and len(rows) == len(current) == 13,
            "P11.39 C-source manifest must cover exactly all 13 Phase-11 demo C sources")
    require([row.get("path") for row in rows] == [p.relative_to(root).as_posix() for p in current],
            "P11.39 C-source manifest path set/order drift")
    for path, row in zip(current, rows):
        require(row.get("git_blob") == git_blob(path.read_bytes()),
                f"P11.39 source identity drift: {path.name}")
        sdk = row.get("sdk_reference", {})
        native = row.get("target_native", {})
        require(sdk.get("required_result") == "REJECT"
                and sdk.get("category") == "declaration-error",
                f"P11.39 source SDK result missing: {path.name}")
        require(native.get("required_result") == "PASS"
                and native.get("owner_step") in {"P11.35","P11.36","P11.37","P11.38"}
                and native.get("p1139_revalidation") is True,
                f"P11.39 source native mapping missing: {path.name}")
    return current


def validate_three_way(data: dict) -> None:
    require(data.get("schema") == 1 and data.get("step") == "P11.39"
            and data.get("sdk_commit") == SDK_COMMIT,
            "P11.39 three-way comparison identity drift")
    require(data.get("status") == "RESOLVED" and data.get("unresolved") == [],
            "P11.39 unresolved DOCX/SDK/native discrepancy")
    areas = data.get("areas")
    require(isinstance(areas, list) and len(areas) >= 18,
            "P11.39 three-way comparison coverage incomplete")
    require(all(row.get("unresolved") is False
                and row.get("native_steps")
                and row.get("resolution")
                for row in areas),
            "P11.39 incomplete three-way comparison row")


def validate_prior_evidence(root: Path) -> None:
    cert = root / "v1/dist/certification"
    for number in range(1, 39):
        step = f"P11.{number:02d}"
        expected = {"R17.00": "PASS"} if number == 1 else {f"P11.{number-1:02d}": "PASS"}
        for action in ("build", "test"):
            record = json.loads((cert / f"{step}.{action}.json").read_text(encoding="utf-8"))
            require(record.get("schema") == 2 and record.get("step") == step
                    and record.get("action") == action and record.get("status") == "PASS"
                    and record.get("worktree_clean") is True,
                    f"P11.39 prerequisite evidence invalid: {step}.{action}")
            require(record.get("prerequisites") == expected
                    and record.get("architecture_sha256") == REV17
                    and record.get("implementation_plan_sha256") == REV08,
                    f"P11.39 prerequisite authority drift: {step}.{action}")


def wrong_native_expected_result_must_fail(root: Path) -> bool:
    # The fixture produces HL=0 but deliberately expects 1.  The exact target
    # harness must therefore reach FAIL_PC; accepting it would weaken P11.39.
    code = bytes((
        0xF3,                    # DI
        0x21, 0x00, 0x00,       # LD HL,0
        0x11, 0x01, 0x00,       # LD DE,1 (intentionally wrong expected value)
        0xB7,                    # OR A (clear carry)
        0xED, 0x52,              # SBC HL,DE => nonzero
        0xC2, FAIL_PC & 0xFF, FAIL_PC >> 8,
        0xC3, PASS_PC & 0xFF, PASS_PC >> 8,
    ))
    try:
        run_sna(root, code, timeout=15)
    except DriverError:
        return True
    return False


def negative_self_tests(mapping: dict, test_ids: list[str], sources: dict, three: dict) -> None:
    rejected = 0
    try:
        bad = dict(mapping)
        bad["tests"] = list(mapping["tests"][:-1])
        validate_test_map(bad, test_ids)
    except P1139Error:
        rejected += 1
    try:
        bad = json.loads(json.dumps(mapping))
        bad["tests"][0]["original_intent_preserved"] = False
        validate_test_map(bad, test_ids)
    except P1139Error:
        rejected += 1
    try:
        bad = json.loads(json.dumps(three))
        bad["status"] = "UNRESOLVED"
        bad["unresolved"] = ["intentional negative"]
        validate_three_way(bad)
    except P1139Error:
        rejected += 1
    try:
        bad = json.loads(json.dumps(sources))
        bad["sources"] = bad["sources"][:-1]
        validate_source_manifest(ROOT_FOR_NEGATIVE, bad)
    except P1139Error:
        rejected += 1
    require(rejected == 4, "P11.39 negative golden-suite oracles did not all fail closed")


ROOT_FOR_NEGATIVE: Path


def dispatch(root: Path, action: str, step: str, *, sha256_file, run_command, require_project_tool):
    global ROOT_FOR_NEGATIVE
    ROOT_FOR_NEGATIVE = root
    if step != "P11.39":
        raise DriverError(step)

    sdk_root = root / "v1/tests/compiler/sdk-reference/sdk"
    map_path = root / "v1/tests/compiler/p1139-sdk-test-map.json"
    source_path = root / "v1/tests/compiler/p1139-c-source-manifest.json"
    three_path = root / "v1/tests/compiler/p1139-three-way-map.json"
    provenance = root / "v1/tests/compiler/sdk-reference/SDK-PROVENANCE.md"

    require(sdk_root.is_dir(), "P11.39 imported SDK root missing")
    tree_cmd = run_command(
        ["git", "rev-parse", f"HEAD:{sdk_root.relative_to(root).as_posix()}"],
        cwd=root, timeout_seconds=10,
    )
    require(not tree_cmd.timed_out and tree_cmd.exit_code == 0
            and tree_cmd.stdout.strip() == SDK_TREE,
            "P11.39 imported SDK Git tree identity mismatch")
    test_ids = imported_test_ids(sdk_root)
    require(len(test_ids) == 205 and len(set(test_ids)) == 205,
            f"P11.39 pinned SDK test count mismatch: {len(test_ids)}")

    mapping = json.loads(map_path.read_text(encoding="utf-8"))
    source_manifest = json.loads(source_path.read_text(encoding="utf-8"))
    three = json.loads(three_path.read_text(encoding="utf-8"))
    validate_test_map(mapping, test_ids)
    phase_sources = validate_source_manifest(root, source_manifest)
    validate_three_way(three)
    validate_prior_evidence(root)
    require("complete pinned SDK corpus import" in provenance.read_text(encoding="utf-8")
            and SDK_TREE in provenance.read_text(encoding="utf-8"),
            "P11.39 SDK provenance import record missing")

    commands = [tree_cmd]
    if action == "build":
        sdk_tests = run_command(
            [sys.executable, "-B", str(sdk_root / "compiler/run_tests.py")],
            cwd=sdk_root, timeout_seconds=300,
        )
        require(not sdk_tests.timed_out and sdk_tests.exit_code == 0,
                f"P11.39 imported SDK run_tests.py failed: {sdk_tests.stdout}\n{sdk_tests.stderr}")
        report = sdk_tests.stdout + sdk_tests.stderr
        require(re.search(r"Ran 205 tests", report) is not None and "OK" in report,
                "P11.39 imported SDK suite did not report exact 205-test PASS")
        commands.append(sdk_tests)
    else:
        release = run_command(
            [sys.executable, "-B", str(sdk_root / "compiler/verify_release.py")],
            cwd=sdk_root, timeout_seconds=600,
        )
        require(not release.timed_out and release.exit_code == 0,
                f"P11.39 imported SDK release gate failed: {release.stdout}\n{release.stderr}")
        marker = "VERIFY PASS: C48 SDK 0.9.0-dev | 205 tests | 6 deterministic demos | 14 games"
        require(marker in release.stdout,
                "P11.39 imported SDK release gate completion marker missing")
        commands.append(release)

    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    sdk_compile_dir = build / "p1139-sdk-source-results"
    if sdk_compile_dir.exists():
        shutil.rmtree(sdk_compile_dir)
    sdk_compile_dir.mkdir(parents=True)
    for source in phase_sources:
        output = sdk_compile_dir / (source.stem + ".c48b")
        result = run_command(
            [sys.executable, "-B", str(sdk_root / "compiler/c48.py"),
             str(source), "-o", str(output)],
            cwd=sdk_root, timeout_seconds=30,
        )
        require(not result.timed_out and result.exit_code != 0 and not output.exists(),
                f"P11.39 pinned SDK expected REJECT drift: {source.name}")
        commands.append(result)

    native_results = []
    if action == "test":
        native_root = Path(tempfile.mkdtemp(prefix="zxux-p1139-native-suite-"))
        runner = root / "v1/tools-host/test-driver/run.py"
        try:
            for owner in NATIVE_REVALIDATION:
                evidence = native_root / owner.replace(".", "")
                result = run_command(
                    [sys.executable, str(runner), "test", "--step", owner,
                     "--evidence-dir", str(evidence)],
                    cwd=root, timeout_seconds=180,
                )
                require(not result.timed_out and result.exit_code == 0,
                        f"P11.39 exact-head native owner revalidation failed: {owner}: "
                        f"{result.stdout}\n{result.stderr}")
                require(f"ZX-UX {owner} TEST PASS" in result.stdout,
                        f"P11.39 native owner missing PASS marker: {owner}")
                commands.append(result)
                native_results.append(owner)
        finally:
            shutil.rmtree(native_root, ignore_errors=True)

        negative_self_tests(mapping, test_ids, source_manifest, three)
        require(wrong_native_expected_result_must_fail(root),
                "P11.39 intentionally wrong native expected result did not fail harness")

    assertions = [
        {"name": "pinned-sdk-tree-byte-and-mode-identical", "passed": True},
        {"name": "complete-imported-sdk-test-count-exact-205", "passed": True},
        {"name": "no-imported-sdk-skip-xfail-or-weakened-intent", "passed": True},
        {"name": "all-205-sdk-tests-mechanically-mapped", "passed": True},
        {"name": "complete-phase11-c-source-sdk-result-native-mapping", "passed": True},
        {"name": "docx-sdk-native-zero-unresolved-discrepancies", "passed": True},
        {"name": "p11-01-through-p11-38-admitted-evidence-valid", "passed": True},
        {"name": "copied-sdk-runner-or-release-gate-passes", "passed": True},
    ]
    if action == "test":
        assertions += [
            {"name": "exact-head-native-owner-suite-p11-02-through-p11-38", "passed": native_results == list(NATIVE_REVALIDATION)},
            {"name": "negative-missing-weakened-unresolved-source-oracles-fail-closed", "passed": True},
            {"name": "intentionally-wrong-native-expected-result-fails-harness", "passed": True},
        ]

    hashes = {
        "v1/tests/compiler/sdk-reference/SDK-PROVENANCE.md": sha256_file(provenance),
        "v1/tests/compiler/sdk-reference/sdk/MANIFEST.sha256": sha256_file(sdk_root / "MANIFEST.sha256"),
        "v1/tests/compiler/sdk-reference/sdk/compiler/run_tests.py": sha256_file(sdk_root / "compiler/run_tests.py"),
        "v1/tests/compiler/sdk-reference/sdk/compiler/verify_release.py": sha256_file(sdk_root / "compiler/verify_release.py"),
        "v1/tests/compiler/sdk-reference/sdk/compiler/release_expectations.json": sha256_file(sdk_root / "compiler/release_expectations.json"),
        "v1/tests/compiler/p1139-sdk-test-map.json": sha256_file(map_path),
        "v1/tests/compiler/p1139-c-source-manifest.json": sha256_file(source_path),
        "v1/tests/compiler/p1139-three-way-map.json": sha256_file(three_path),
        "tools/check_license_headers.sh": sha256_file(root / "tools/check_license_headers.sh"),
        "tools/ci.sh": sha256_file(root / "tools/ci.sh"),
        "v1/tools-host/test-driver/phase11_step_39.py": sha256_file(root / "v1/tools-host/test-driver/phase11_step_39.py"),
        "v1/dist/certification/P11.38.build.json": sha256_file(root / "v1/dist/certification/P11.38.build.json"),
        "v1/dist/certification/P11.38.test.json": sha256_file(root / "v1/dist/certification/P11.38.test.json"),
    }
    for source in phase_sources:
        hashes[source.relative_to(root).as_posix()] = sha256_file(source)
    return commands, hashes, assertions
