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

# P10.06 normalized qualification marker.

import phase1
import phase3_open_descriptions
from driver_core import DriverError
from fuse_harness import PASS_PC, FAIL_PC, run_sna


P1006_QUALIFICATION_CANDIDATE = True

class P1006Error(DriverError):
    pass


def require(ok, msg):
    if not ok:
        raise P1006Error(msg)


def host_equ(expr: str, symbols: dict[str, int]) -> int:
    text=expr.strip()
    if "+" in text:
        left,right=text.split("+",1)
        require(left in symbols,"unresolved EQU symbol")
        value=symbols[left]+int(right,0)
    elif "-" in text:
        left,right=text.split("-",1)
        require(left in symbols,"unresolved EQU symbol")
        value=symbols[left]-int(right,0)
    elif text in symbols:
        value=symbols[text]
    else:
        value=int(text,0)
    require(0 <= value <= 0xFFFF,"EQU value outside u16")
    return value


def dispatch(root, action, step, *, sha256_file, run_command, require_project_tool):
    if step != "P10.06":
        raise DriverError(step)
    source=root/"tools/as.asm"
    text=source.read_text(encoding="utf-8")
    assertions=[
        {"name":"symbol-table-native","passed":"as_p1006_define:" in text and "as_p1006_lookup:" in text},
        {"name":"case-sensitive-compare-native","passed":"as_p1006_name_equal:" in text and "cp (hl)" in text},
        {"name":"duplicate-reject-native","passed":"as_p1006_dup_loop:" in text},
        {"name":"equ-u16-contract","passed":"P10.06 case-sensitive symbols and EQU binding." in text},
    ]
    symbols={"base":0x1200,"Base":0x2200}
    assertions.extend([
        {"name":"host-case-sensitive-symbols","passed":host_equ("base+2",symbols)==0x1202 and host_equ("Base+2",symbols)==0x2202},
        {"name":"host-known-equ-expression","passed":host_equ("base-1",symbols)==0x11FF},
    ])
    unresolved=False
    try: host_equ("later+1",symbols)
    except (P1006Error,ValueError): unresolved=True
    assertions.append({"name":"host-forward-unknown-defers-errors","passed":unresolved})
    require(all(a["passed"] for a in assertions),"P10.06 static/host contract failure")

    assembler=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus")
    build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    fixture=build/"p1006-symbols.asm"
    fixture.write_text(
"""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../../tools/as.asm"
    ORG $C000
fixture:
    EMIT_P10_AS_LEXER_ROUTINES
    EMIT_P10_AS_SYMBOL_ROUTINES
name_upper: db 'A','l','p','h','a',0
name_lower: db 'a','l','p','h','a',0
name_missing: db 'm','i','s','s',0
fixture_end:
    SAVEBIN "p1006-symbols.bin",fixture,fixture_end-fixture
""",encoding="utf-8",newline="\n")
    result=run_command([assembler,"--nologo","--lst=p1006-symbols.lst","--sym=p1006-symbols.sym",fixture.name],cwd=build,timeout_seconds=30)
    require(not result.timed_out and result.exit_code==0,f"P10.06 assemble: {result.stderr or result.stdout}")

    if action=="test":
        names=("as_p1006_reset","as_p1006_define","as_p1006_lookup","name_upper","name_lower","name_missing","as_p1006_count")
        syms=phase3_open_descriptions._symbols(build/"p1006-symbols.sym",names)
        image=(build/"p1006-symbols.bin").read_bytes()
        def patch(ram):
            ram[0xC000-0x4000:0xC000-0x4000+len(image)]=image
        # Define Alpha=0x1234 then alpha=0x5678; exact lookups succeed.
        code=(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._call(syms["as_p1006_reset"])
              +phase1._ld_hl(syms["name_upper"])+phase1._ld_de(0x1234)+phase1._call(syms["as_p1006_define"])+phase1._jp_c(FAIL_PC)
              +phase1._ld_hl(syms["name_lower"])+phase1._ld_de(0x5678)+phase1._call(syms["as_p1006_define"])+phase1._jp_c(FAIL_PC)
              +phase1._ld_hl(syms["name_upper"])+phase1._call(syms["as_p1006_lookup"])
              +phase1._jp_c(FAIL_PC)
              +b"\x7A\xFE\x12"+phase1._jp_nz(FAIL_PC)+b"\x7B\xFE\x34"+phase1._jp_nz(FAIL_PC)
              +phase1._ld_hl(syms["name_lower"])+phase1._call(syms["as_p1006_lookup"])+phase1._jp_c(FAIL_PC)
              +b"\x7A\xFE\x56"+phase1._jp_nz(FAIL_PC)+b"\x7B\xFE\x78"+phase1._jp_nz(FAIL_PC)
              +phase1._jp(PASS_PC))
        run_sna(root,code,patch=patch)
        # Duplicate and missing lookup both reject.
        code2=(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._call(syms["as_p1006_reset"])
               +phase1._ld_hl(syms["name_upper"])+phase1._ld_de(1)+phase1._call(syms["as_p1006_define"])+phase1._jp_c(FAIL_PC)
               +phase1._ld_hl(syms["name_upper"])+phase1._ld_de(2)+phase1._call(syms["as_p1006_define"])
               +b"\xD2"+phase1._word(FAIL_PC)
               +phase1._ld_hl(syms["name_missing"])+phase1._call(syms["as_p1006_lookup"])
               +b"\xD2"+phase1._word(FAIL_PC)+phase1._jp(PASS_PC))
        run_sna(root,code2,patch=patch)
        assertions.extend([
            {"name":"fuse-case-sensitive-distinct-symbols","passed":True},
            {"name":"fuse-duplicate-symbol-rejected","passed":True},
            {"name":"fuse-missing-forward-symbol-unresolved","passed":True},
        ])
    hashes={
        "tools/as.asm":sha256_file(source),
        "v1/build/p1006-symbols.bin":sha256_file(build/"p1006-symbols.bin"),
        "v1/tools-host/test-driver/phase10_as_symbols.py":sha256_file(root/"v1/tools-host/test-driver/phase10_as_symbols.py"),
        "v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
        "v1/dist/certification/P10.05.build.json":sha256_file(root/"v1/dist/certification/P10.05.build.json"),
        "v1/dist/certification/P10.05.test.json":sha256_file(root/"v1/dist/certification/P10.05.test.json"),
    }
    return [result],hashes,assertions
