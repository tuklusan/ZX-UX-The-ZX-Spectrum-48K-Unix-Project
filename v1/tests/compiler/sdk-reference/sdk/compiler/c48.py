#!/usr/bin/env python3
# ============================================================================
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Proprietary rights reserved except as expressly licensed herein.
#
# ZX-UX C48 SDK
# This file is governed by the SANYALnet Labs Non-Commercial License in the
# root LICENSE file. Non-Commercial use is permitted; Commercial Use and use
# for AI/ML model training are prohibited unless separately authorized.
#
# Attribution is required: "Based on original work by Supratim Sanyal of
# SANYALnet Labs." See LICENSE for full terms, warranty disclaimer, termination,
# patent, trademark, and governing-law provisions.
# ============================================================================
from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.dont_write_bytecode = True

# Allow running directly from compiler/ without installation.
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SDK_VERSION = "0.9.0-dev"

from c48.compiler import compile_file
from c48.errors import C48Error, UsageC48Error
from c48.format import write


def default_output(source: Path) -> Path:
    source = source.resolve()
    sdk = ROOT.parent
    dev_src = (sdk / "dev" / "src").resolve()
    try:
        rel = source.relative_to(dev_src)
    except ValueError:
        return source.with_suffix(".c48b")
    return (sdk / "dev" / "bin" / rel).with_suffix(".c48b")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="c48", description="Portable ZX-UX C48 host compiler")
    ap.add_argument("--version", action="version", version=f"%(prog)s {SDK_VERSION}")
    ap.add_argument(
        "--about",
        action="version",
        version=(
            f"%(prog)s {SDK_VERSION}\n"
            "ZX-UX C48 SDK\n"
            "Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.\n"
            "Based on original work by Supratim Sanyal of SANYALnet Labs.\n"
            "SANYALnet Labs Non-Commercial License; see the root LICENSE file."
        ),
        help="show attribution and license information and exit",
    )
    ap.add_argument("source", type=Path)
    ap.add_argument("-o", "--output", type=Path)
    ns = ap.parse_args(argv)
    src = ns.source
    out = ns.output or default_output(src)
    try:
        # Never allow a host output path to destroy the input source.  This mirrors
        # the native cc same-input/output usage rejection while still allowing long
        # host development paths outside the ZX-UX namespace.
        if src.resolve() == out.resolve():
            raise UsageC48Error("input and output paths must be different")
        program = compile_file(src)
        write(out, program)
        return 0
    except C48Error as exc:
        # Host SDK preserves the frozen class words but identifies itself as c48.
        if exc.pos:
            print(f"c48: {exc.pos.format()}: {exc.category}: {exc.message}", file=sys.stderr)
        else:
            print(f"c48: {exc.category}: {exc.message}", file=sys.stderr)
        return exc.exit_status
    except RecursionError:
        print(
            "c48: resource-limit: host recursion safety ceiling exceeded",
            file=sys.stderr,
        )
        return 1
    except MemoryError:
        print(
            "c48: resource-limit: host memory safety ceiling exceeded",
            file=sys.stderr,
        )
        return 1
    except OSError as exc:
        print(f"c48: io: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
