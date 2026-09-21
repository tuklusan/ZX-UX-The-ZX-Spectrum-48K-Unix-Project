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
import sys
from driver_core import DriverError
from fuse_harness import FAIL_PC, PASS_PC, run_sna
import phase1, phase3_open_descriptions

BASE=0xC000
USER=0xA000
ENV=0xA100
STATUS=0xA200
BAD=0xA300

class P605Error(DriverError): pass
def require(v,m):
    if not v: raise P605Error(m)
def word(v): return bytes((v&255,(v>>8)&255))
def expected(user:bytes):
    entries=[b"HOME=/home/"+user,b"PATH=/bin:.",b"SHELL=/bin/sh",b"USER="+user]
    body=b"".join(x+b"\0" for x in entries)
    total=8+len(body)
    return b"ENV1"+bytes((4,0))+word(total)+body
def expect_byte(addr,val): return b"\x3A"+word(addr)+bytes((0xFE,val&255))+phase1._jp_nz(FAIL_PC)

def patch(module,user=b"alice",bad=None):
    def p(ram):
        ram[BASE-0x4000:BASE-0x4000+len(module)]=module
        ram[USER-0x4000:USER-0x4000+len(user)]=user
        ram[ENV-0x4000:ENV-0x4000+256]=b"\xA5"*256
        ram[STATUS-0x4000]=0xA5
        if bad is not None: ram[BAD-0x4000:BAD-0x4000+len(bad)]=bad
    return p

def dispatch(root:Path,action:str,step:str,*,sha256_file,run_command,require_project_tool):
    if step!="P6.05": raise DriverError(f"Phase-6 initial env step is not registered: {step}")
    sp=root/"v1/src/shell/sh.asm"; text=sp.read_text(); macro=text.split("MACRO EMIT_P605_ENV_ROUTINES",1)[1].split("ENDM",1)[0]
    assertions=[
      {"name":"env1-four-entry-table","passed":"ld a,4" in macro and "ld a,'E'" in macro and "ld a,'N'" in macro and "ld a,'V'" in macro},
      {"name":"sorted-home-path-shell-user","passed":macro.index("; HOME=")<macro.index("; PATH=")<macro.index("; SHELL=")<macro.index("; USER=")},
      {"name":"required-path-shell-values","passed":"ld a,':'" in macro and "ld a,'.'" in macro and macro.count("ld a,'/'")>=4},
      {"name":"status-separate-from-env","passed":"sh_p605_status_init:" in macro and "$?" not in macro},
    ]
    require(all(a["passed"] for a in assertions),"P6.05 static contract failure")
    asm=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus"); build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    sf=build/"p605-fixture.asm"
    sf.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/kernel/process.asm"
    INCLUDE "../src/shell/sh.asm"
PANIC_SCHEDULER EQU $03
PANIC_ROM_CONTRACT EQU $05
    ORG $C000
p605_start:
    EMIT_ENV1_ROUTINES
    EMIT_P605_ENV_ROUTINES
p605_end:
    SAVEBIN "p605-fixture.bin",p605_start,p605_end-p605_start
""",encoding="utf-8",newline="\n")
    sr=run_command([asm,"--nologo","--lst=p605-fixture.lst","--sym=p605-fixture.sym","p605-fixture.asm"],cwd=build,timeout_seconds=30)
    require(not sr.timed_out and sr.exit_code==0,f"P6.05 fixture assembly failed: {sr.stderr or sr.stdout}")
    if action=="test":
        sy=phase3_open_descriptions._symbols(build/"p605-fixture.sym",("sh_p605_init_env","sh_p605_status_init","zx48_env1_validate","E_FORMAT"))
        module=(build/"p605-fixture.bin").read_bytes()
        user=b"alice"; exp=expected(user)
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._ld_hl(USER)+b"\x01"+word(len(user))+phase1._ld_de(ENV))
        code+=phase1._call(sy["sh_p605_init_env"])+phase1._jp_c(FAIL_PC)
        code+=phase1._ld_hl(STATUS)+phase1._call(sy["sh_p605_status_init"])+phase1._jp_c(FAIL_PC)
        for off,val in enumerate(exp): code+=expect_byte(ENV+off,val)
        code+=expect_byte(ENV+len(exp),0xA5)+expect_byte(STATUS,0)+phase1._jp(PASS_PC)
        run_sna(root,bytes(code),patch=patch(module,user))

        bad_entries=[b"HOME=/home/alice",b"PATH=/bin:.",b"SHELL=/bin/sh",b"USER=alice",b"$?=0"]
        body=b"".join(x+b"\0" for x in bad_entries); bad=b"ENV1"+bytes((5,0))+word(8+len(body))+body
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+b"\xDD\x21"+word(BAD)+b"\x01"+word(len(bad)))
        code+=phase1._call(sy["zx48_env1_validate"])+b"\xD2"+word(FAIL_PC)
        code+=bytes((0xFE,sy["E_FORMAT"]&255))+phase1._jp_nz(FAIL_PC)+phase1._jp(PASS_PC)
        run_sna(root,bytes(code),patch=patch(module,user,bad))
        assertions += [{"name":"fuse-initial-env-exact-sorted","passed":True},{"name":"fuse-dollar-question-not-env-entry","passed":True}]
    hashes={
      "v1/src/shell/sh.asm":sha256_file(sp),"v1/tools-host/test-driver/phase6_env.py":sha256_file(root/"v1/tools-host/test-driver/phase6_env.py"),"v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
      "v1/dist/certification/P6.04.build.json":sha256_file(root/"v1/dist/certification/P6.04.build.json"),"v1/dist/certification/P6.04.test.json":sha256_file(root/"v1/dist/certification/P6.04.test.json"),"v1/dist/media/P6.04/manifest.json":sha256_file(root/"v1/dist/media/P6.04/manifest.json")}
    return [sr],hashes,assertions
