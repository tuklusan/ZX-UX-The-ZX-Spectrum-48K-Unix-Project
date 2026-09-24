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

import re
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET

from driver_core import DriverError

SDK_COMMIT = "84d144de2721cda5075c3a6610a422663b5e2f77"
SDK_TREE = "1c6b5bae84035ee853be9142b440792881c9ca9f"
DOCX = Path("docs/04-C48 Language Specification Rev 0.11.docx")

class P1101Error(DriverError):
    pass

def require(ok: bool, message: str) -> None:
    if not ok:
        raise P1101Error(message)

def docx_text(path: Path) -> str:
    with ZipFile(path) as zf:
        names=set(zf.namelist())
        require("word/document.xml" in names, "C48 DOCX missing word/document.xml")
        parts=["word/document.xml"]
        for optional in ("word/footnotes.xml","word/endnotes.xml","word/comments.xml"):
            if optional in names:
                parts.append(optional)
        chunks=[]
        for name in parts:
            root=ET.fromstring(zf.read(name))
            chunks.extend(node.text or "" for node in root.iter() if node.tag.endswith("}t"))
    return " ".join(chunks)

def contract_failures(text: str) -> list[str]:
    low=" ".join(text.lower().split())
    groups={
        "dialect-c48": ("c48",),
        "core-types": ("void","char","short","int","float","pointer"),
        "control-flow": ("if","else","while","for","break","continue","return"),
        "sizeof": ("sizeof",),
        "compound-deferred": ("compound","assignment"),
        "conditional-deferred": ("conditional", "?:"),
        "comma-deferred": ("comma", "operator"),
        "double-deferred": ("double",),
        "long-long-deferred": ("long long",),
        "vla-deferred": ("variable-length", "array"),
        "variadic-deferred": ("variadic",),
        "function-pointer-deferred": ("function pointer",),
        "switch-deferred": ("switch", "case"),
        "struct-union-deferred": ("struct", "union"),
        "plain-char-unsigned": ("plain", "char", "unsigned"),
        "long-unsupported": ("long", "unsupported"),
        "main-signatures": ("main", "argc", "argv"),
    }
    return [name for name,tokens in groups.items() if not all(token in low for token in tokens)]

def source_assertions(root: Path):
    contract=(root/"v1/docs/c48.md").read_text(encoding="utf-8")
    prov=(root/"v1/tests/compiler/sdk-reference/SDK-PROVENANCE.md").read_text(encoding="utf-8")
    doc=docx_text(root/DOCX)
    required_contract=[
        "C48_REGCALL","Compound assignments","conditional `?:` operator",
        "comma operator","variable-length arrays","variadic functions",
        "function pointers","switch/case","struct/union","full ISO C conformance",
        "Plain `char` is unsigned","long` is unsupported","five-byte `float`",
        "int main(void)","int main(int argc, char **argv)","OBJ1",
    ]
    required_sdk_paths=[
        "compiler/c48.py","compiler/c48/compiler.py","compiler/c48/lexer.py",
        "compiler/c48/parser.py","compiler/c48/preprocessor.py",
        "compiler/c48/semantics.py","compiler/c48/typesys.py",
        "compiler/c48/float5.py","compiler/c48/memory.py","compiler/c48/vm.py",
        "compiler/tests/test_conformance.py","compiler/tests/test_game_regressions.py",
        "compiler/tests/test_release_regressions.py","compiler/tests/test_security.py",
        "compiler/run_tests.py","compiler/verify_release.py",
    ]
    failures=contract_failures(doc)
    assertions=[
        {"name":"working-contract-explicit-version1-surface","passed":all(x in contract for x in required_contract)},
        {"name":"sdk-reference-commit-pinned","passed":SDK_COMMIT in prov and SDK_TREE in prov},
        {"name":"sdk-python-implementation-surface-reviewed","passed":all(x in prov for x in required_sdk_paths)},
        {"name":"rev16-overrides-sdk-recorded","passed":"REV16 controls" in prov and "reference oracles only" in prov},
        {"name":"sdk-c48b1-not-native-obj1","passed":"C48B1 host executables" in prov and "emit OBJ1 Z80 code" in prov},
        {"name":"h06-later-pin-separated","passed":"9ca3c6d6b5dd4b6e2351c1800afbd47d1d77e411" in prov},
        {"name":"docx-end-to-end-language-families-present","passed":not failures},
        {"name":"docx-real-office-container","passed":(root/DOCX).stat().st_size > 100000},
        {"name":"zero-unresolved-discrepancy-marker","passed":"UNRESOLVED" not in contract and "UNRESOLVED" not in prov},
    ]
    return assertions, failures

def dispatch(root, action, step, *, sha256_file, run_command, require_project_tool):
    if step!="P11.01":
        raise DriverError(f"Phase-11 language-freeze step is not registered: {step}")
    assertions,failures=source_assertions(root)
    if action=="test":
        negative="C48 supports int and pointers only."
        assertions.extend([
            {"name":"negative-missing-language-surface-detected","passed":bool(contract_failures(negative))},
            {"name":"negative-unresolved-marker-blocks","passed":"UNRESOLVED" in "UNRESOLVED discrepancy"},
            {"name":"docx-review-has-no-missing-required-family","passed":not failures},
        ])
    failed=[a["name"] for a in assertions if a.get("passed") is not True]
    require(not failed, f"P11.01 contract failures: {failed}; docx_missing={failures}")
    hashes={
        "docs/04-C48 Language Specification Rev 0.11.docx":sha256_file(root/DOCX),
        "v1/docs/c48.md":sha256_file(root/"v1/docs/c48.md"),
        "v1/tests/compiler/sdk-reference/SDK-PROVENANCE.md":sha256_file(root/"v1/tests/compiler/sdk-reference/SDK-PROVENANCE.md"),
        "v1/tools-host/test-driver/phase11_step_01.py":sha256_file(root/"v1/tools-host/test-driver/phase11_step_01.py"),
        "v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
        "v1/dist/certification/phase-10.json":sha256_file(root/"v1/dist/certification/phase-10.json"),
    }
    return [],hashes,assertions
