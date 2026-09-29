#!/usr/bin/env python3
# ============================================================================
# Copyright (c) 2026 SANYALnet Labs.
# Proprietary rights reserved except as expressly licensed herein.
#
# ZX-UX C48 SDK
# This file is governed by the SANYALnet Labs Non-Commercial License in the
# root LICENSE file. Non-Commercial use is permitted; Commercial Use and use
# restricted model training is prohibited unless separately authorized.
#
# Attribution required: SANYALnet Labs. See LICENSE for full terms,
# warranty disclaimer, termination, patent, trademark, and governing-law
# provisions.
# ============================================================================
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

import c48srctap

ROOT = Path(__file__).resolve().parent
SDK = ROOT.parent
MANIFEST = ROOT / "source_tape_manifest.json"


def load_manifest() -> dict[str, object]:
    data = json.loads(MANIFEST.read_text(encoding="ascii"))
    if data.get("schema") != 1 or data.get("tape_count") != 57:
        raise SystemExit("source tape manifest identity mismatch")
    return data


def build_args(item: dict[str, object]) -> list[str]:
    args = []
    for source in item["sources"]:
        args.append(str(SDK / source["path"]))
    args.extend(["-o", str(SDK / item["output"]), "--force"])
    for source in item["sources"]:
        path = str(SDK / source["path"])
        if Path(path).name != source["name"]:
            args.extend(["--name", path, source["name"]])
    return args


def check_one(item: dict[str, object]) -> None:
    source_args = [str(SDK / source["path"]) for source in item["sources"]]
    names = []
    for source, path in zip(item["sources"], source_args):
        if Path(path).name != source["name"]:
            names.append([path, source["name"]])
    specs = c48srctap.collect_sources(source_args, names)
    expected = c48srctap.build_tape(specs)
    output = SDK / item["output"]
    if not output.is_file() or output.read_bytes() != expected:
        raise SystemExit("source tape mismatch: " + item["output"])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Regenerate or verify the locked C48 source tape corpus."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify tracked tapes without modifying them",
    )
    ns = parser.parse_args(argv)
    manifest = load_manifest()
    for item in manifest["tapes"]:
        if ns.check:
            check_one(item)
            continue
        cp = subprocess.run(
            [sys.executable, "-B", str(ROOT / "c48srctap.py"), *build_args(item)],
            cwd=SDK,
            check=False,
        )
        if cp.returncode != 0:
            return cp.returncode
    print(
        "source tape corpus: "
        + ("verified " if ns.check else "generated ")
        + str(manifest["tape_count"])
        + " tapes"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
