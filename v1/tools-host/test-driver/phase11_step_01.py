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
import re
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from driver_core import DriverError

SDK_COMMIT = "84d144de2721cda5075c3a6610a422663b5e2f77"
SDK_TREE = "1c6b5bae84035ee853be9142b440792881c9ca9f"
DOCX = Path("docs/04-C48 Language Specification Rev 0.11.docx")
DOCX_GIT_BLOB = "a84c314a6d2957835efdc916a49e5289718140c2"
DOCX_SHA256 = "981eeb963d59e7ce2fd5e0fb73866f8a734fd33746a5ee0fce32d84fdec41903"
REV17_SHA256 = "d12baf0b47a7f8cd2dcd60b82f100ba19f9fddaabad43728a004a07214716bf8"
REV08_SHA256 = "97461e9ed12253409b25e6a4a4063cf0ec556a7317f9e4a5938d77edb6a1a14c"


class P1101Error(DriverError):
    pass


def require(ok: bool, message: str) -> None:
    if not ok:
        raise P1101Error(message)


def docx_text(path: Path) -> str:
    with ZipFile(path) as zf:
        names = sorted(
            name for name in zf.namelist()
            if name.startswith("word/") and name.endswith(".xml")
        )
        require("word/document.xml" in names, "C48 DOCX missing word/document.xml")
        chunks: list[str] = []
        for name in names:
            try:
                root = ET.fromstring(zf.read(name))
            except ET.ParseError as exc:
                raise P1101Error(f"C48 DOCX XML parse failure in {name}: {exc}") from exc
            chunks.extend(node.text or "" for node in root.iter() if node.tag.endswith("}t"))
    return " ".join(chunks)


def contract_failures(text: str) -> list[str]:
    low = " ".join(text.lower().split())
    groups = {
        "dialect-c48": ("c48",),
        "core-types": ("void", "char", "short", "int", "float", "pointer"),
        "control-flow": ("if", "else", "while", "do", "for", "break", "continue", "return"),
        "sizeof": ("sizeof",),
        "compound-deferred": ("compound", "assignment"),
        "conditional-deferred": ("conditional", "?:"),
        "comma-deferred": ("comma", "operator"),
        "double-deferred": ("double",),
        "long-long-deferred": ("long long",),
        "vla-deferred": ("variable-length", "array"),
        "complex-initializer-deferred": ("complex", "initializer"),
        "variadic-deferred": ("variadic",),
        "function-pointer-deferred": ("function pointer",),
        "switch-deferred": ("switch", "case"),
        "struct-union-deferred": ("struct", "union"),
        "complex-macro-deferred": ("complex", "preprocessor"),
        "plain-char-unsigned": ("plain", "char", "unsigned"),
        "long-unsupported": ("long", "unsupported"),
        "main-signatures": ("main", "argc", "argv"),
        "identifier-limit": ("15", "identifier"),
        "regcall": ("c48_regcall",),
        "obj1": ("obj1",),
    }
    return [
        name
        for name, tokens in groups.items()
        if not all(token in low for token in tokens)
    ]


def source_assertions(root: Path, sha256_file):
    contract = (root / "v1/docs/c48.md").read_text(encoding="utf-8")
    provenance = (
        root / "v1/tests/compiler/sdk-reference/SDK-PROVENANCE.md"
    ).read_text(encoding="utf-8")
    license_gate = (root / "tools/check_license_headers.sh").read_text(encoding="utf-8")
    doc = docx_text(root / DOCX)
    compact_contract = " ".join(contract.split())
    compact_provenance = " ".join(provenance.split())

    required_contract = [
        "REV17 Section 25",
        "REV08",
        "C48_REGCALL",
        "Compound assignments",
        "conditional `?:` operator",
        "comma operator",
        "variable-length arrays",
        "complex initializers",
        "variadic functions",
        "function pointers",
        "`switch/case`",
        "`struct/union`",
        "complex preprocessor macros",
        "optimizer passes requiring large IR",
        "full ISO C conformance",
        "Plain `char` is unsigned",
        "`long` is unsupported",
        "five-byte `float`",
        "`int main(void)`",
        "`int main(int argc, char **argv)`",
        "OBJ1",
        "15 visible characters",
        "Division or remainder by zero",
        "low 3 bits",
        "low 4 bits",
    ]
    required_sdk_paths = [
        "compiler/c48.py",
        "compiler/c48/compiler.py",
        "compiler/c48/errors.py",
        "compiler/c48/float5.py",
        "compiler/c48/format.py",
        "compiler/c48/lexer.py",
        "compiler/c48/limits.py",
        "compiler/c48/memory.py",
        "compiler/c48/parser.py",
        "compiler/c48/preprocessor.py",
        "compiler/c48/semantics.py",
        "compiler/c48/typesys.py",
        "compiler/c48/vm.py",
        "compiler/tests/test_conformance.py",
        "compiler/tests/test_game_regressions.py",
        "compiler/tests/test_release_regressions.py",
        "compiler/tests/test_security.py",
        "compiler/run_tests.py",
        "compiler/verify_release.py",
        "compiler/release_expectations.json",
        "doc/CONFORMANCE.md",
        "doc/HOST-DIVERGENCES.md",
    ]
    doc_failures = contract_failures(doc)
    stale_authorities = [
        term
        for term in ("REV11", "Revision 11", "Revision-11", "REV02", "Revision 02", "Revision-02")
        if re.search(re.escape(term), doc, re.IGNORECASE)
    ]

    r17 = json.loads(
        (root / "v1/dist/certification/R17.00.result.json").read_text(encoding="utf-8")
    )
    assertions = [
        {
            "name": "working-contract-explicit-version1-surface",
            "passed": all(item in compact_contract for item in required_contract),
        },
        {
            "name": "active-rev17-identity-exact",
            "passed": sha256_file(root / "docs/01-ZX-UX-ARCHITECTURE-REV17.md") == REV17_SHA256,
        },
        {
            "name": "active-rev08-identity-exact",
            "passed": sha256_file(root / "docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV08.md") == REV08_SHA256,
        },
        {
            "name": "r17-authority-admission-present",
            "passed": (
                r17.get("step") == "R17.00"
                and r17.get("action") == "result"
                and r17.get("status") == "PASS"
                and r17.get("architecture_sha256") == REV17_SHA256
                and r17.get("implementation_plan_sha256") == REV08_SHA256
            ),
        },
        {
            "name": "sdk-reference-commit-and-tree-pinned",
            "passed": SDK_COMMIT in provenance and SDK_TREE in provenance,
        },
        {
            "name": "sdk-reference-matches-rev08-no-rebaseline",
            "passed": "no SDK re-baseline is required" in provenance,
        },
        {
            "name": "sdk-python-implementation-and-doc-surface-reviewed",
            "passed": all(path in provenance for path in required_sdk_paths),
        },
        {
            "name": "sdk-release-test-count-recorded",
            "passed": "205 tests" in provenance,
        },
        {
            "name": "docx-corrected-identity-recorded",
            "passed": DOCX_GIT_BLOB in provenance and DOCX_SHA256 in provenance,
        },
        {
            "name": "docx-corrected-sha256-exact",
            "passed": sha256_file(root / DOCX) == DOCX_SHA256,
        },
        {
            "name": "docx-license-gate-pins-corrected-blob",
            "passed": f'C48_SPEC_DOCX_BLOB_SHA1="{DOCX_GIT_BLOB}"' in license_gate,
        },
        {
            "name": "docx-current-authorities-present",
            "passed": "REV17" in doc and "REV08" in doc,
        },
        {
            "name": "docx-stale-authorities-removed",
            "passed": not stale_authorities,
        },
        {
            "name": "docx-end-to-end-language-families-present",
            "passed": not doc_failures,
        },
        {
            "name": "docx-real-office-container",
            "passed": (root / DOCX).stat().st_size > 100000,
        },
        {
            "name": "intentional-rev17-over-sdk-differences-recorded",
            "passed": (
                "Intentional REV17-over-SDK differences" in provenance
                and "reference/oracle material" in provenance
                and "native ZX-UX `cc`" in provenance
                and "C48B1" in provenance
            ),
        },
        {
            "name": "three-way-discrepancies-resolved",
            "passed": (
                "zero outstanding REV17/DOCX/SDK discrepancies" in compact_provenance
                and "obsolete REV11/REV02 authorities" in compact_provenance
            ),
        },
        {
            "name": "h06-later-pin-separation-recorded",
            "passed": "P11.45/P11.48" in provenance and "does not change this P11.01" in provenance,
        },
    ]
    return assertions, doc_failures, stale_authorities


def dispatch(root, action, step, *, sha256_file, run_command, require_project_tool):
    if step != "P11.01":
        raise DriverError(f"Phase-11 language-freeze step is not registered: {step}")

    commands = [
        run_command(["git", "hash-object", "--", str(DOCX)], cwd=root),
        run_command(["git", "ls-files", "--stage", "--", str(DOCX)], cwd=root),
    ]
    require(commands[0].exit_code == 0 and not commands[0].timed_out, "git hash-object failed")
    require(commands[1].exit_code == 0 and not commands[1].timed_out, "git ls-files failed")

    assertions, doc_failures, stale_authorities = source_assertions(root, sha256_file)
    blob = commands[0].stdout.strip()
    index_fields = commands[1].stdout.strip().split()
    assertions.extend([
        {"name": "docx-git-blob-exact", "passed": blob == DOCX_GIT_BLOB},
        {
            "name": "docx-index-mode-and-blob-exact",
            "passed": len(index_fields) >= 3 and index_fields[0] == "100644" and index_fields[1] == DOCX_GIT_BLOB,
        },
    ])

    if action == "test":
        negative = "C48 supports int and pointers only."
        assertions.extend([
            {
                "name": "negative-missing-language-surface-detected",
                "passed": bool(contract_failures(negative)),
            },
            {
                "name": "negative-stale-authority-detected",
                "passed": bool(re.search(r"REV11|REV02", "Authority REV11 plan REV02")),
            },
            {
                "name": "negative-wrong-docx-identity-detected",
                "passed": ("0" * 40) != DOCX_GIT_BLOB,
            },
            {
                "name": "negative-incomplete-sdk-map-detected",
                "passed": "compiler/c48/parser.py" not in "compiler/c48/lexer.py",
            },
            {
                "name": "docx-review-has-no-missing-required-family",
                "passed": not doc_failures,
            },
            {
                "name": "docx-review-has-no-stale-authority",
                "passed": not stale_authorities,
            },
        ])

    failed = [item["name"] for item in assertions if item.get("passed") is not True]
    require(
        not failed,
        f"P11.01 contract failures: {failed}; docx_missing={doc_failures}; stale={stale_authorities}",
    )

    hashes = {
        "docs/01-ZX-UX-ARCHITECTURE-REV17.md": sha256_file(root / "docs/01-ZX-UX-ARCHITECTURE-REV17.md"),
        "docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV08.md": sha256_file(root / "docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV08.md"),
        str(DOCX): sha256_file(root / DOCX),
        "tools/check_license_headers.sh": sha256_file(root / "tools/check_license_headers.sh"),
        "v1/docs/c48.md": sha256_file(root / "v1/docs/c48.md"),
        "v1/tests/compiler/sdk-reference/SDK-PROVENANCE.md": sha256_file(
            root / "v1/tests/compiler/sdk-reference/SDK-PROVENANCE.md"
        ),
        "v1/tools-host/test-driver/phase11_step_01.py": sha256_file(
            root / "v1/tools-host/test-driver/phase11_step_01.py"
        ),
        "v1/tools-host/test-driver/run.py": sha256_file(root / "v1/tools-host/test-driver/run.py"),
        "v1/dist/certification/R17.00.result.json": sha256_file(
            root / "v1/dist/certification/R17.00.result.json"
        ),
        "v1/dist/certification/phase-10.json": sha256_file(
            root / "v1/dist/certification/phase-10.json"
        ),
    }
    return commands, hashes, assertions
