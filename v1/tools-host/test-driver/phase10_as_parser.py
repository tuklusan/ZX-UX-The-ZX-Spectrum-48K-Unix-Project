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

import phase1
import phase3_open_descriptions
from driver_core import DriverError
from fuse_harness import PASS_PC, FAIL_PC, run_sna


class P1005Error(DriverError):
    pass


def require(ok, msg):
    if not ok:
        raise P1005Error(msg)


def dispatch(root, action, step, *, sha256_file, run_command, require_project_tool):
    if step != "P10.05":
        raise DriverError(step)

    source = root / "tools/as.asm"
    text = source.read_text(encoding="utf-8")
    assertions = [
        {"name":"native-line-parser-present","passed":"as_p1005_parse_line:" in text},
        {"name":"include-rejected","passed":"as_p1005_is_include:" in text and "as_p1005_include_word: db 'include'" in text},
        {"name":"comment-and-label-paths","passed":"cp ';'" in text and "as_p1005_label:" in text},
        {"name":"no-source-inclusion-contract","passed":"forbidden INCLUDE directive" in text},
    ]
    require(all(a["passed"] for a in assertions), "P10.05 static parser contract failure")

    assembler = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    fixture = build / "p1005-parser.asm"
    fixture.write_text(
        """    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../../tools/as.asm"
    ORG $C000
fixture:
    EMIT_P10_AS_LEXER_ROUTINES
line_empty: db 0
line_comment: db ';','x',0
line_label: db 'l','a','b','e','l',':',' ','l','d',' ','a',',','1',0
line_token: db 'n','o','p',0
line_include: db 'I','N','C','L','U','D','E',' ','x',0
line_bad: db '9','b','a','d',0
fixture_end:
    SAVEBIN "p1005-parser.bin",fixture,fixture_end-fixture
""",
        encoding="utf-8",
        newline="\n",
    )
    result = run_command(
        [assembler, "--nologo", "--lst=p1005-parser.lst", "--sym=p1005-parser.sym", fixture.name],
        cwd=build,
        timeout_seconds=30,
    )
    require(not result.timed_out and result.exit_code == 0, f"P10.05 assemble: {result.stderr or result.stdout}")

    if action == "test":
        symbols = phase3_open_descriptions._symbols(
            build / "p1005-parser.sym",
            ("as_p1005_parse_line","line_empty","line_comment","line_label","line_token","line_include","line_bad"),
        )
        image = (build / "p1005-parser.bin").read_bytes()

        def patch(ram):
            ram[0xC000-0x4000:0xC000-0x4000+len(image)] = image

        for name in ("line_empty","line_comment","line_label","line_token"):
            code = (
                b"\xF3"
                + phase1._ld_sp(0xBFC0)
                + phase1._ld_hl(symbols[name])
                + phase1._call(symbols["as_p1005_parse_line"])
                + phase1._jp_c(FAIL_PC)
                + phase1._jp(PASS_PC)
            )
            run_sna(root, code, patch=patch)

        for name in ("line_include","line_bad"):
            code = (
                b"\xF3"
                + phase1._ld_sp(0xBFC0)
                + phase1._ld_hl(symbols[name])
                + phase1._call(symbols["as_p1005_parse_line"])
                + phase1._jp_nc(FAIL_PC)
                + phase1._jp(PASS_PC)
            )
            run_sna(root, code, patch=patch)

        assertions.extend([
            {"name":"fuse-empty-comment-label-token-accept","passed":True},
            {"name":"fuse-include-reject","passed":True},
            {"name":"fuse-malformed-token-reject","passed":True},
        ])

    hashes = {
        "tools/as.asm": sha256_file(source),
        "v1/build/p1005-parser.bin": sha256_file(build / "p1005-parser.bin"),
        "v1/tools-host/test-driver/phase10_as_parser.py": sha256_file(root / "v1/tools-host/test-driver/phase10_as_parser.py"),
        "v1/tools-host/test-driver/run.py": sha256_file(root / "v1/tools-host/test-driver/run.py"),
        "v1/dist/certification/P10.04.build.json": sha256_file(root / "v1/dist/certification/P10.04.build.json"),
        "v1/dist/certification/P10.04.test.json": sha256_file(root / "v1/dist/certification/P10.04.test.json"),
    }
    return [result], hashes, assertions
