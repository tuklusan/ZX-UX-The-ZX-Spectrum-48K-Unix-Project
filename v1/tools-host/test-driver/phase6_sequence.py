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
BASE=0xC000; STATUS=0xA000; ORDER=0xA010
class P619Error(DriverError): pass
def require(v,m):
    if not v: raise P619Error(m)
def word(v): return bytes((v&255,(v>>8)&255))
def eq(a,v): return b"\x3A"+word(a)+bytes((0xFE,v&255))+phase1._jp_nz(FAIL_PC)
def patch(module):
    def p(ram):
        ram[BASE-0x4000:BASE-0x4000+len(module)]=module
        ram[STATUS-0x4000]=0xA5
        ram[ORDER-0x4000:ORDER-0x4000+4]=bytes(4)
    return p
def dispatch(root:Path,action:str,step:str,*,sha256_file,run_command,require_project_tool):
    if step!="P6.19": raise DriverError(f"Phase-6 semicolon step is not registered: {step}")
    sp=root/"v1/src/shell/sh.asm"; text=sp.read_text(); macro=text.split("MACRO EMIT_P619_SEQUENCE_ROUTINES",1)[1].split("ENDM",1)[0]
    assertions=[
      {"name":"left-to-right-callback-table","passed":"sh_p619_next:" in macro and "jp (hl)" in macro},
      {"name":"status-updated-each-unit","passed":"ld (ix+0),a" in macro},
      {"name":"failure-does-not-short-circuit","passed":"ret c" not in macro},
    ]
    require(all(x["passed"] for x in assertions),"P6.19 static contract failure")
    asm=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus"); build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    src=build/"p619-fixture.asm"
    src.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/shell/sh.asm"
    ORG $C000
p619_start:
    EMIT_P619_SEQUENCE_ROUTINES
p619_a: ld a,1 : ld ($A010),a : ld a,7 : scf : ret
p619_b: ld a,2 : ld ($A011),a : xor a : ret
p619_c: ld a,3 : ld ($A012),a : ld a,5 : or a : ret
p619_table_test: dw p619_a,p619_b,p619_c
p619_end:
    SAVEBIN "p619-fixture.bin",p619_start,p619_end-p619_start
""",encoding="utf-8",newline="\n")
    sr=run_command([asm,"--nologo","--lst=p619-fixture.lst","--sym=p619-fixture.sym","p619-fixture.asm"],cwd=build,timeout_seconds=30)
    require(not sr.timed_out and sr.exit_code==0,f"P6.19 fixture failed: {sr.stderr or sr.stdout}")
    if action=="test":
        sy=phase3_open_descriptions._symbols(build/"p619-fixture.sym",("sh_p619_sequence","p619_table_test"))
        mod=(build/"p619-fixture.bin").read_bytes()
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._ld_hl(sy["p619_table_test"])+b"\x06\x03"+b"\xDD\x21"+word(STATUS)+phase1._call(sy["sh_p619_sequence"]))
        code+=eq(ORDER,1)+eq(ORDER+1,2)+eq(ORDER+2,3)+eq(STATUS,5)+phase1._jp(PASS_PC)
        run_sna(root,bytes(code),patch=patch(mod))
        assertions += [{"name":"fuse-a-b-c-order-exact","passed":True},{"name":"fuse-failed-a-does-not-skip-later-units","passed":True},{"name":"fuse-final-status-exact","passed":True}]
    hashes={"v1/src/shell/sh.asm":sha256_file(sp),"v1/tools-host/test-driver/phase6_sequence.py":sha256_file(root/"v1/tools-host/test-driver/phase6_sequence.py"),"v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),"v1/dist/certification/P6.18.build.json":sha256_file(root/"v1/dist/certification/P6.18.build.json"),"v1/dist/certification/P6.18.test.json":sha256_file(root/"v1/dist/certification/P6.18.test.json"),"v1/dist/media/P6.18/manifest.json":sha256_file(root/"v1/dist/media/P6.18/manifest.json")}
    return [sr],hashes,assertions
