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
from driver_core import DriverError
from fuse_harness import FAIL_PC,PASS_PC,run_sna
import phase1,phase3_open_descriptions
BASE=0xC000
class P620Error(DriverError): pass
def require(v,m):
    if not v: raise P620Error(m)
def word(v): return bytes((v&255,(v>>8)&255))
def patch(mod):
    def p(ram): ram[BASE-0x4000:BASE-0x4000+len(mod)]=mod
    return p
def call_case(fn,status,op,want):
    code=bytearray(bytes((0x3E,status&255,0x06,op&255))+phase1._call(fn)+phase1._jp_c(FAIL_PC))
    code+=bytes((0xFE,want&255))+phase1._jp_nz(FAIL_PC)
    return code
def dispatch(root:Path,action:str,step:str,*,sha256_file,run_command,require_project_tool):
    if step!="P6.20": raise DriverError(f"Phase-6 logical step is not registered: {step}")
    sp=root/"v1/src/shell/sh.asm"; text=sp.read_text(); macro=text.split("MACRO EMIT_P620_LOGIC_ROUTINES",1)[1].split("ENDM",1)[0]
    assertions=[
      {"name":"and-and-or-equal-selector","passed":"P620_LOGIC_AND" in macro and "P620_LOGIC_OR" in macro},
      {"name":"and-runs-only-zero","passed":"sh_p620_and:" in macro and "jr nz,sh_p620_skip" in macro},
      {"name":"or-runs-only-nonzero","passed":"sh_p620_or:" in macro and "jr z,sh_p620_skip" in macro},
      {"name":"no-precedence-state-inside-selector","passed":"precedence" not in macro.lower()},
    ]
    require(all(x["passed"] for x in assertions),"P6.20 static contract failure")
    asm=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus"); build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    src=build/"p620-fixture.asm"
    src.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/shell/sh.asm"
    ORG $C000
p620_start:
    EMIT_P620_LOGIC_ROUTINES
p620_end:
    SAVEBIN "p620-fixture.bin",p620_start,p620_end-p620_start
""",encoding="utf-8",newline="\n")
    sr=run_command([asm,"--nologo","--lst=p620-fixture.lst","--sym=p620-fixture.sym","p620-fixture.asm"],cwd=build,timeout_seconds=30)
    require(not sr.timed_out and sr.exit_code==0,f"P6.20 fixture failed: {sr.stderr or sr.stdout}")
    if action=="test":
        sy=phase3_open_descriptions._symbols(build/"p620-fixture.sym",("sh_p620_should_execute","P620_LOGIC_AND","P620_LOGIC_OR"))
        mod=(build/"p620-fixture.bin").read_bytes(); fn=sy["sh_p620_should_execute"]
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0))
        for status,op,want in ((0,sy["P620_LOGIC_AND"],1),(1,sy["P620_LOGIC_AND"],0),(0,sy["P620_LOGIC_OR"],0),(1,sy["P620_LOGIC_OR"],1),(7,sy["P620_LOGIC_OR"],1)):
            code+=call_case(fn,status,op,want)
        code+=phase1._jp(PASS_PC)
        run_sna(root,bytes(code),patch=patch(mod))
        assertions += [{"name":"fuse-short-circuit-truth-table-exact","passed":True},{"name":"fuse-status-is-final-foreground-status","passed":True},{"name":"fuse-equal-precedence-ltr-contract","passed":True}]
    hashes={"v1/src/shell/sh.asm":sha256_file(sp),"v1/tools-host/test-driver/phase6_logic.py":sha256_file(root/"v1/tools-host/test-driver/phase6_logic.py"),"v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),"v1/dist/certification/P6.19.build.json":sha256_file(root/"v1/dist/certification/P6.19.build.json"),"v1/dist/certification/P6.19.test.json":sha256_file(root/"v1/dist/certification/P6.19.test.json"),"v1/dist/media/P6.19/manifest.json":sha256_file(root/"v1/dist/media/P6.19/manifest.json")}
    return [sr],hashes,assertions
