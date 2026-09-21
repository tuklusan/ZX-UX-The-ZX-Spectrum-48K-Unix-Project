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
from fuse_harness import FAIL_PC, PASS_PC, run_sna
import phase1, phase3_open_descriptions

BASE=0xC000
ENV=0xA000
ARG=0xA200

class P606Error(DriverError): pass
def require(v,m):
    if not v: raise P606Error(m)
def word(v): return bytes((v&255,(v>>8)&255))
def env(entries):
    body=b"".join(k+b"="+v+b"\0" for k,v in entries)
    total=8+len(body)
    require(total<=256,"test ENV overflow")
    return b"ENV1"+bytes((len(entries),0))+word(total)+body
def initial():
    return env([(b"HOME",b"/home/alice"),(b"PATH",b"/bin:."),(b"SHELL",b"/bin/sh"),(b"USER",b"alice")])
def expect_byte(addr,val): return b"\x3A"+word(addr)+bytes((0xFE,val&255))+phase1._jp_nz(FAIL_PC)
def patch(module,block,arg):
    def p(ram):
        ram[BASE-0x4000:BASE-0x4000+len(module)]=module
        ram[ENV-0x4000:ENV-0x4000+256]=b"\xA5"*256
        ram[ENV-0x4000:ENV-0x4000+len(block)]=block
        ram[ARG-0x4000:ARG-0x4000+len(arg)]=arg
    return p
def call_ix_hl(symbol):
    return b"\xDD\x21"+word(ENV)+phase1._ld_hl(ARG)+phase1._call(symbol)

def dispatch(root:Path,action:str,step:str,*,sha256_file,run_command,require_project_tool):
    if step!="P6.06": raise DriverError(f"Phase-6 set/unset step is not registered: {step}")
    sp=root/"v1/src/shell/sh.asm"; text=sp.read_text(); macro=text.split("MACRO EMIT_P606_SET_UNSET_ROUTINES",1)[1].split("ENDM",1)[0]
    assertions=[
      {"name":"transactional-private-scratch","passed":"p606_scratch: defs 256,0" in macro and macro.index("call zx48_env1_validate") < macro.rindex("ldir")},
      {"name":"eight-entry-limit","passed":"cp 8" in macro and "E_NOSPC" in macro},
      {"name":"first-equals-delimiter","passed":"cp '='" in macro and "; first '='" not in macro},
      {"name":"name-lexical-upper-lower-digit-underscore","passed":"cp 'A'" in macro and "cp 'a'" in macro and "cp '0'" in macro and "cp '_'" in macro},
      {"name":"value-printable-63","passed":"cp $20" in macro and "cp $7f" in macro and "cp 63" in macro},
      {"name":"sorted-rebuild-uses-name-comparison","passed":"call sh_p606_compare_names" in macro and "sh_p606_set_old_before:" in macro},
      {"name":"magic-vars-not-protected","passed":"USER" not in macro and "HOME" not in macro and "SHELL" not in macro and "PATH" not in macro},
    ]
    require(all(a["passed"] for a in assertions),"P6.06 static contract failure")
    asm=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus"); build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    sf=build/"p606-fixture.asm"
    sf.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/kernel/process.asm"
    INCLUDE "../src/shell/sh.asm"
PANIC_SCHEDULER EQU $03
PANIC_ROM_CONTRACT EQU $05
zx48_alloc: ld a,E_NOMEM : scf : ret
    ORG $C000
p606_start:
    EMIT_ENV1_ROUTINES
    EMIT_P606_SET_UNSET_ROUTINES
p606_end:
    SAVEBIN "p606-fixture.bin",p606_start,p606_end-p606_start
""",encoding="utf-8",newline="\n")
    sr=run_command([asm,"--nologo","--lst=p606-fixture.lst","--sym=p606-fixture.sym","p606-fixture.asm"],cwd=build,timeout_seconds=30)
    require(not sr.timed_out and sr.exit_code==0,f"P6.06 fixture assembly failed: {sr.stderr or sr.stdout}")
    if action=="test":
        sy=phase3_open_descriptions._symbols(build/"p606-fixture.sym",("sh_p606_set","sh_p606_unset","E_INVAL","E_NOSPC"))
        module=(build/"p606-fixture.bin").read_bytes()
        cases=[
          (b"AAA=1\0",env([(b"AAA",b"1"),(b"HOME",b"/home/alice"),(b"PATH",b"/bin:."),(b"SHELL",b"/bin/sh"),(b"USER",b"alice")])),
          (b"USER=bob\0",env([(b"HOME",b"/home/alice"),(b"PATH",b"/bin:."),(b"SHELL",b"/bin/sh"),(b"USER",b"bob")])),
          (b"_12345678901234=\0",env([(b"HOME",b"/home/alice"),(b"PATH",b"/bin:."),(b"SHELL",b"/bin/sh"),(b"USER",b"alice"),(b"_12345678901234",b"")])),
        ]
        for arg,want in cases:
            code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+call_ix_hl(sy["sh_p606_set"])+phase1._jp_c(FAIL_PC))
            for off,val in enumerate(want): code+=expect_byte(ENV+off,val)
            code+=phase1._jp(PASS_PC)
            run_sna(root,bytes(code),patch=patch(module,initial(),arg))

        arg=b"PATH\0"; want=env([(b"HOME",b"/home/alice"),(b"SHELL",b"/bin/sh"),(b"USER",b"alice")])
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+call_ix_hl(sy["sh_p606_unset"])+phase1._jp_c(FAIL_PC))
        for off,val in enumerate(want): code+=expect_byte(ENV+off,val)
        code+=phase1._jp(PASS_PC)
        run_sna(root,bytes(code),patch=patch(module,initial(),arg))

        arg=b"HOME\0"; want=env([(b"PATH",b"/bin:."),(b"SHELL",b"/bin/sh"),(b"USER",b"alice")])
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+call_ix_hl(sy["sh_p606_unset"])+phase1._jp_c(FAIL_PC))
        for off,val in enumerate(want): code+=expect_byte(ENV+off,val)
        code+=phase1._jp(PASS_PC)
        run_sna(root,bytes(code),patch=patch(module,initial(),arg))

        bad=b"$?=0\0"
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+call_ix_hl(sy["sh_p606_set"])+b"\xD2"+word(FAIL_PC)+bytes((0xFE,sy["E_INVAL"]&255))+phase1._jp_nz(FAIL_PC))
        before=initial()
        for off,val in enumerate(before): code+=expect_byte(ENV+off,val)
        code+=phase1._jp(PASS_PC)
        run_sna(root,bytes(code),patch=patch(module,before,bad))

        big=env([(bytes((65+i,)),b"x"*32) for i in range(7)])
        arg=b"Z=1\0"
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+call_ix_hl(sy["sh_p606_set"])+b"\xD2"+word(FAIL_PC)+bytes((0xFE,sy["E_NOSPC"]&255))+phase1._jp_nz(FAIL_PC))
        for off,val in enumerate(big): code+=expect_byte(ENV+off,val)
        code+=phase1._jp(PASS_PC)
        run_sna(root,bytes(code),patch=patch(module,big,arg))
        assertions += [
          {"name":"fuse-set-unset-boundary-corpus","passed":True},
          {"name":"fuse-magic-entries-mutable","passed":True},
          {"name":"fuse-invalid-dollar-status-rejected","passed":True},
          {"name":"fuse-size-overflow-transaction-unchanged","passed":True},
        ]
    hashes={
      "v1/src/shell/sh.asm":sha256_file(sp),"v1/tools-host/test-driver/phase6_set_unset.py":sha256_file(root/"v1/tools-host/test-driver/phase6_set_unset.py"),"v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
      "v1/dist/certification/P6.05.build.json":sha256_file(root/"v1/dist/certification/P6.05.build.json"),"v1/dist/certification/P6.05.test.json":sha256_file(root/"v1/dist/certification/P6.05.test.json"),"v1/dist/media/P6.05/manifest.json":sha256_file(root/"v1/dist/media/P6.05/manifest.json")}
    return [sr],hashes,assertions
