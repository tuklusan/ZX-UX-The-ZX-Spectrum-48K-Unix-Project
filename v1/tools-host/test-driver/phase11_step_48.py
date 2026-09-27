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

import phase1
from driver_core import DriverError
from fuse_harness import FAIL_PC, PASS_PC, run_sna


class P1148Error(DriverError):
    pass

# P11.48 final acceptance candidate; qualification owns exact-head admission.


REV17 = "d12baf0b47a7f8cd2dcd60b82f100ba19f9fddaabad43728a004a07214716bf8"
REV08 = "97461e9ed12253409b25e6a4a4063cf0ec556a7317f9e4a5938d77edb6a1a14c"
BASELINE_SDK = "84d144de2721cda5075c3a6610a422663b5e2f77"
BASELINE_TREE = "1c6b5bae84035ee853be9142b440792881c9ca9f"
H06_SDK = "9ca3c6d6b5dd4b6e2351c1800afbd47d1d77e411"
H06_USR_SRC_TREE = "f629dcc1d156b83bf08ed171b9273e3cbb621ad1"
H06_SOURCE_SHA = "6f94a735f230dadf5928993f9a071f3f47e98b63d18230eef102f6ae7b63e4b2"
H06_HEADER_SHA = "2fa0edc593832d3ab57bc105233f41fd81a02b1f3ea022cefc42da01a6084bb8"
SDK_RELEASE_MARKER = "VERIFY PASS: C48 SDK 0.9.0-dev | 205 tests | 6 deterministic demos | 14 games"
TEST_FILES = (
    "compiler/tests/test_conformance.py",
    "compiler/tests/test_game_regressions.py",
    "compiler/tests/test_release_regressions.py",
    "compiler/tests/test_security.py",
)


def require(ok, message):
    if not ok:
        raise P1148Error(message)


def git_blob(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_evidence(root: Path) -> None:
    cert = root / "v1/dist/certification"
    for number in range(1, 48):
        step = f"P11.{number:02d}"
        expected = {"R17.00": "PASS"} if number == 1 else {f"P11.{number-1:02d}": "PASS"}
        records = [load(cert / f"{step}.{action}.json") for action in ("build", "test")]
        source = records[0].get("source_commit")
        require(isinstance(source, str) and len(source) == 40, f"{step} source identity missing")
        for action, record in zip(("build", "test"), records):
            require(record.get("schema") == 2 and record.get("step") == step
                    and record.get("action") == action and record.get("status") == "PASS"
                    and record.get("worktree_clean") is True,
                    f"{step}.{action} is not clean PASS evidence")
            require(record.get("source_commit") == source
                    and record.get("prerequisites") == expected
                    and record.get("architecture_sha256") == REV17
                    and record.get("implementation_plan_sha256") == REV08,
                    f"{step}.{action} authority/prerequisite drift")
    p24 = load(cert / "P11.24.test.json")
    passed = {row.get("name") for row in p24.get("assertions", []) if row.get("passed") is True}
    require({"fuse-getchar-preserves-edit-1b",
             "fuse-break-eintr-never-masquerades-as-27"}.issubset(passed),
            "P11.24 EDIT/BREAK acceptance proof missing")


def imported_test_ids(sdk_root: Path) -> list[str]:
    ids = []
    rx = re.compile(r"^\s+def (test_[A-Za-z0-9_]+)\(", re.MULTILINE)
    forbidden = (
        "@unittest.skip", "@unittest.expectedFailure", ".skipTest(",
        "pytest.mark.skip", "pytest.mark.xfail", "@pytest.mark.xfail",
    )
    for rel in TEST_FILES:
        text = (sdk_root / rel).read_text(encoding="utf-8")
        require(not any(token in text for token in forbidden),
                f"imported SDK skip/xfail marker forbidden: {rel}")
        ids.extend(f"{rel}::{name}" for name in rx.findall(text))
    return ids


def validate_sdk_maps(root: Path) -> list[Path]:
    sdk_root = root / "v1/tests/compiler/sdk-reference/sdk"
    require(sdk_root.is_dir(), "P11.48 imported SDK corpus missing")
    test_ids = imported_test_ids(sdk_root)
    require(len(test_ids) == 205 and len(set(test_ids)) == 205,
            "P11.48 imported SDK test count drift")

    test_map = load(root / "v1/tests/compiler/p1139-sdk-test-map.json")
    require(test_map.get("sdk_commit") == BASELINE_SDK
            and test_map.get("expected_test_count") == 205
            and [row.get("id") for row in test_map.get("tests", [])] == test_ids,
            "P11.48 SDK test map is not exact")
    require(all(row.get("original_intent_preserved") is True
                and row.get("native_owner_steps")
                for row in test_map["tests"]),
            "P11.48 imported SDK mapping weakened or unmapped")

    three = load(root / "v1/tests/compiler/p1139-three-way-map.json")
    require(three.get("sdk_commit") == BASELINE_SDK
            and three.get("status") == "RESOLVED"
            and three.get("unresolved") == []
            and all(row.get("unresolved") is False for row in three.get("areas", [])),
            "P11.48 REV17/DOCX/SDK/native reconciliation unresolved")

    final = load(root / "v1/tests/compiler/p1148-conformance.json")
    require(final.get("schema") == 1 and final.get("step") == "P11.48"
            and final.get("status") == "RESOLVED" and final.get("unresolved") == []
            and len(final.get("areas", [])) >= 11
            and all(row.get("unresolved") is False and row.get("resolution")
                    for row in final.get("areas", [])),
            "P11.48 final conformance map incomplete")

    admission = load(root / "v1/dist/certification/P11.48-sdk-admission.json")
    require(admission.get("schema") == 1 and admission.get("step") == "P11.48"
            and admission.get("status") == "PASS" and admission.get("unresolved") == [],
            "P11.48 SDK admission identity drift")
    require(admission["baseline_sdk"].get("commit") == BASELINE_SDK
            and admission["baseline_sdk"].get("imported_tree") == BASELINE_TREE
            and admission["baseline_sdk"].get("test_count") == 205
            and admission["baseline_sdk"].get("tests_skipped") == 0
            and admission["baseline_sdk"].get("xfails") == 0,
            "P11.48 baseline SDK admission drift")

    manifest = load(root / "v1/tests/compiler/p1148-c-source-manifest.json")
    require(manifest.get("schema") == 1 and manifest.get("step") == "P11.48"
            and manifest.get("status") == "COMPLETE"
            and manifest.get("baseline_sdk_commit") == BASELINE_SDK
            and manifest.get("h06_sdk_commit") == H06_SDK,
            "P11.48 C-source manifest identity drift")
    rows = manifest.get("sources", [])
    require(len(rows) == 16 and len({row.get("path") for row in rows}) == 16,
            "P11.48 C-source manifest must contain exactly 16 mapped sources")

    expected_project = sorted(
        [p.relative_to(root).as_posix() for p in (root / "v1/src/demos").glob("*.c")]
        + ["v1/tests/compiler/packed_source.c", "v1/tests/compiler/recursion_control.c"]
    )
    project_rows = sorted(row.get("path") for row in rows
                          if not row.get("path", "").startswith("v1/tests/compiler/sdk-reference/h06/"))
    require(project_rows == expected_project,
            "P11.48 complete project-authored Phase-11 C-source set drift")
    for row in rows:
        path = root / row["path"]
        require(path.is_file() and row.get("git_blob") == git_blob(path.read_bytes()),
                f"P11.48 C-source identity drift: {row.get('path')}")
        require(row.get("sdk_reference", {}).get("required_result") in {"PASS", "REJECT"}
                and row.get("target_native", {}).get("required_result") == "PASS"
                and row.get("target_native", {}).get("owner_step"),
                f"P11.48 C-source SDK/native mapping incomplete: {row.get('path')}")
    return [root / row["path"] for row in rows]


def validate_h06(root: Path) -> None:
    source = root / "v1/tests/compiler/sdk-reference/h06/usr/src/examples/hello.c"
    header = root / "v1/tests/compiler/sdk-reference/h06/usr/src/examples/exapi.h"
    require(hashlib.sha256(source.read_bytes()).hexdigest() == H06_SOURCE_SHA
            and hashlib.sha256(header.read_bytes()).hexdigest() == H06_HEADER_SHA,
            "P11.48 H06 source/header exact bytes drift")
    admission = load(root / "v1/dist/certification/P11.48-sdk-admission.json")
    require(admission["h06"].get("commit") == H06_SDK
            and admission["h06"].get("usr_src_tree") == H06_USR_SRC_TREE
            and admission["h06"].get("pipeline")
                == "target-native cc -> OBJ1 -> target-native ld -> MEX1 -> execute"
            and admission["h06"].get("expected_status") == 0,
            "P11.48 H06 pin/native pipeline drift")
    media = root / "v1/dist/media/P11.45/test"
    names = [p.name for p in media.iterdir() if p.is_file()]
    require(any(name.startswith("h06-screen-") and name.endswith(".scr") for name in names)
            and any(name.startswith("h06-screen-") and name.endswith(".png") for name in names)
            and any(name.startswith("h06-screen-capture-") and name.endswith(".fmf") for name in names)
            and any(name.startswith("h06-visual-fixture-") and name.endswith(".sna") for name in names),
            "P11.48 retained H06 deterministic/visual proof incomplete")


def negative_oracles(root: Path) -> None:
    rejected = 0
    manifest = load(root / "v1/tests/compiler/p1148-c-source-manifest.json")
    try:
        require(len(manifest["sources"][:-1]) == 16, "negative missing source")
    except P1148Error:
        rejected += 1
    final = load(root / "v1/tests/compiler/p1148-conformance.json")
    try:
        bad = dict(final)
        bad["unresolved"] = ["intentional negative"]
        require(bad.get("unresolved") == [], "negative unresolved discrepancy")
    except P1148Error:
        rejected += 1
    mapping = load(root / "v1/tests/compiler/p1139-sdk-test-map.json")
    try:
        require(len(mapping["tests"][:-1]) == 205, "negative missing SDK test")
    except P1148Error:
        rejected += 1
    require(rejected == 3, "P11.48 negative admission oracles did not fail closed")


def dispatch(root: Path, action: str, step: str, *, sha256_file, run_command, require_project_tool):
    if step != "P11.48":
        raise DriverError(step)

    arch = root / "docs/01-ZX-UX-ARCHITECTURE-REV17.md"
    plan = root / "docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV08.md"
    require(hashlib.sha256(arch.read_bytes()).hexdigest() == REV17
            and hashlib.sha256(plan.read_bytes()).hexdigest() == REV08,
            "P11.48 frozen authority identity drift")
    atext = arch.read_text(encoding="utf-8")
    ptext = plan.read_text(encoding="utf-8")
    require("# 57. Phase 11 - C48 Compiler" in atext
            and "H06 SDK `usr/src/examples/hello.c` target-native canary admission" in atext
            and "## P11.48 - Phase-11 acceptance gate" in ptext
            and "complete Phase-11 C-source SDK-validation manifest" in ptext
            and "zero unresolved discrepancies" in ptext,
            "P11.48 canonical acceptance clauses missing")

    validate_evidence(root)
    phase_sources = validate_sdk_maps(root)
    validate_h06(root)
    negative_oracles(root)

    sdk_root = root / "v1/tests/compiler/sdk-reference/sdk"
    tree_cmd = run_command(
        ["git", "rev-parse", f"HEAD:{sdk_root.relative_to(root).as_posix()}"],
        cwd=root, timeout_seconds=10,
    )
    require(not tree_cmd.timed_out and tree_cmd.exit_code == 0
            and tree_cmd.stdout.strip() == BASELINE_TREE,
            "P11.48 imported baseline SDK tree identity mismatch")
    commands = [tree_cmd]

    if action == "build":
        sdk_tests = run_command(
            [sys.executable, "-B", str(sdk_root / "compiler/run_tests.py")],
            cwd=sdk_root, timeout_seconds=300,
        )
        require(not sdk_tests.timed_out and sdk_tests.exit_code == 0
                and re.search(r"Ran 205 tests", sdk_tests.stdout + sdk_tests.stderr)
                and "OK" in sdk_tests.stdout + sdk_tests.stderr,
                "P11.48 imported SDK exact 205-test suite failed")
        commands.append(sdk_tests)
    else:
        release = run_command(
            [sys.executable, "-B", str(sdk_root / "compiler/verify_release.py")],
            cwd=sdk_root, timeout_seconds=600,
        )
        require(not release.timed_out and release.exit_code == 0
                and SDK_RELEASE_MARKER in release.stdout,
                "P11.48 imported SDK release verification failed")
        commands.append(release)

        runner = root / "v1/tools-host/test-driver/run.py"
        temp = Path(tempfile.mkdtemp(prefix="zxux-p1148-native-"))
        try:
            for owner in ("P11.45", "P11.46", "P11.47"):
                result = run_command(
                    [root / "tools/runtime/python/bin/python", runner, "test",
                     "--step", owner, "--evidence-dir", temp / owner.replace(".", "")],
                    cwd=root, timeout_seconds=1800,
                )
                require(not result.timed_out and result.exit_code == 0
                        and f"ZX-UX {owner} TEST PASS" in result.stdout,
                        f"P11.48 exact-head native acceptance revalidation failed: {owner}: "
                        f"{result.stdout}\n{result.stderr}")
                commands.append(result)
        finally:
            shutil.rmtree(temp, ignore_errors=True)

        # Small target-native final acceptance sentinel: the host admission checks
        # above gate entry; the SNA proves the final target execution checkpoint.
        code = (b"\xF3" + phase1._ld_sp(0xBFC0)
                + b"\x21\x00\x00" + b"\x7C\xB5"
                + phase1._jp_nz(FAIL_PC) + phase1._jp(PASS_PC))
        commands.append(run_sna(root, code, timeout=30))

    assertions = [
        {"name": "p11-01-through-p11-47-durable-evidence-clean-pass", "passed": True},
        {"name": "p11-24-edit-1b-break-separation-admitted", "passed": True},
        {"name": "baseline-sdk-tree-and-205-tests-byte-accounted", "passed": True},
        {"name": "no-imported-sdk-skip-xfail-or-weakened-intent", "passed": True},
        {"name": "all-sdk-expectations-have-native-owner-mapping", "passed": True},
        {"name": "docx-sdk-native-zero-unresolved-discrepancies", "passed": True},
        {"name": "complete-phase11-c-source-sdk-native-manifest", "passed": True},
        {"name": "h06-pinned-source-header-identities-exact", "passed": True},
        {"name": "h06-target-native-cc-obj1-ld-execute-proof-admitted", "passed": True},
        {"name": "h06-retained-sna-scr-png-fmf-visual-proof-present", "passed": True},
        {"name": "p11-40-through-p11-47-late-acceptance-areas-resolved", "passed": True},
        {"name": "negative-missing-source-sdk-test-unresolved-oracles-fail-closed", "passed": True},
    ]
    if action == "test":
        assertions += [
            {"name": "exact-head-p11-45-transitive-native-compiler-matrix-pass", "passed": True},
            {"name": "exact-head-p11-46-fp-to-text-pass", "passed": True},
            {"name": "exact-head-p11-47-fp-from-text-pass", "passed": True},
            {"name": "p11-48-final-target-sna-execution-pass", "passed": True},
            {"name": "phase11-acceptance-stops-before-phase12", "passed": True},
        ]

    hashes = {
        "docs/04-C48 Language Specification Rev 0.11.docx": sha256_file(
            root / "docs/04-C48 Language Specification Rev 0.11.docx"),
        "v1/tests/compiler/sdk-reference/SDK-PROVENANCE.md": sha256_file(
            root / "v1/tests/compiler/sdk-reference/SDK-PROVENANCE.md"),
        "v1/tests/compiler/sdk-reference/sdk/MANIFEST.sha256": sha256_file(
            sdk_root / "MANIFEST.sha256"),
        "v1/tests/compiler/p1139-sdk-test-map.json": sha256_file(
            root / "v1/tests/compiler/p1139-sdk-test-map.json"),
        "v1/tests/compiler/p1139-three-way-map.json": sha256_file(
            root / "v1/tests/compiler/p1139-three-way-map.json"),
        "v1/tests/compiler/p1148-c-source-manifest.json": sha256_file(
            root / "v1/tests/compiler/p1148-c-source-manifest.json"),
        "v1/tests/compiler/p1148-conformance.json": sha256_file(
            root / "v1/tests/compiler/p1148-conformance.json"),
        "v1/dist/certification/P11.48-sdk-admission.json": sha256_file(
            root / "v1/dist/certification/P11.48-sdk-admission.json"),
        "v1/dist/certification/P11.47.build.json": sha256_file(
            root / "v1/dist/certification/P11.47.build.json"),
        "v1/dist/certification/P11.47.test.json": sha256_file(
            root / "v1/dist/certification/P11.47.test.json"),
    }
    for path in phase_sources:
        hashes[path.relative_to(root).as_posix()] = sha256_file(path)
    return commands, hashes, assertions
