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
import phase1, phase3_open_descriptions
from driver_core import DriverError
from fuse_harness import PASS_PC, run_sna
from phase8_common import arg1, word, assemble_utility, inspect_mex, make_tap

UTIL=0xC000; GATE=0xE000; ARG=0xA000; ENV=0xA100; OUT=0xA300  # exact fixture map
STATUS=0xA280; MODE=0xA282
class P827Error(DriverError):
    pass
def require(v,m):
    if not v: raise P827Error(m)
def expect(addr,val): return b"\x3A"+word(addr)+bytes((0xFE,val&255))+phase1._jp_nz(0x8F00)
def env1(entries):
    body=b"".join(x+b"\0" for x in entries)
    return b"ENV1"+bytes((len(entries),0))+word(8+len(body))+body
def patch(util,gate,args,entries,mode=0,bad_magic=False):
    ab=arg1(args); eb=bytearray(env1(entries))
    if bad_magic: eb[0]=ord('X')
    def apply(ram):
        ram[UTIL-0x4000:UTIL-0x4000+len(util)]=util
        ram[GATE-0x4000:GATE-0x4000+len(gate)]=gate
        ram[ARG-0x4000:ARG-0x4000+len(ab)]=ab
        ram[ENV-0x4000:ENV-0x4000+len(eb)]=eb
        ram[OUT-0x4000:OUT-0x4000+128]=b"\xA5"*128
        ram[STATUS-0x4000:STATUS-0x4000+8]=b"\0"*8
        ram[MODE-0x4000]=mode
    return apply
def source_contract(root):
    s=(root/"v1/src/utils/man.asm").read_text(); p=(root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md").read_text()
    return [
      {"name":"canonical-p827-present","passed":"## P8.27 - Utility `man`" in p},
      {"name":"exact-manual-url","passed":"man_line1:" in s and "\'h\',\'t\',\'t\',\'p\',\'s\',\':\',\'/\',\'/\'" in s and "\'b\',\'l\',\'o\',\'g\',\'s\',\'p\',\'o\',\'t\'" in s},
      {"name":"search-zxus","passed":"Search for ZXUS" not in s and "'S','e','a','r','c','h',' ','f','o','r',' ','Z','X','U','S'" in s},
      {"name":"no-local-loader","passed":"SYS_OPEN" not in s and "SYS_READ" not in s},
      {"name":"short-write-safe","passed":"man_write_loop:" in s and "man_io:" in s},
      {"name":"arity-one-or-two","passed":"cp 1" in s and "cp 2" in s and "E_INVAL" in s},
    ]
def dispatch(root,action,step,*,sha256_file,run_command,require_project_tool):
    if step!="P8.27": raise DriverError(f"Phase-8 man step is not registered: {step}")
    assertions=source_contract(root); require(all(x["passed"] for x in assertions),"P8.27 static contract failure")
    tool=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus"); build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    try: ir,image,mex=assemble_utility(root,build,tool,"man","p827","EMIT_P827_MAN_ROUTINES",run_command); xr=inspect_mex(root,mex,run_command,require_project_tool); tap=make_tap(root,build,"man","p827",mex)
    except RuntimeError as e: raise P827Error(str(e))
    require(64<=len(image)<2048,"P8.27 image size implausible")
    fix=build/"p827-man-fixture.asm"; fix.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/utils/man.asm"
    ORG $C000
fixture:
    EMIT_P827_MAN_ROUTINES
fixture_end:
    SAVEBIN "p827-man-fixture.bin",fixture,fixture_end-fixture
""",newline="\n")
    fr=run_command([tool,"--nologo","--lst=p827-man-fixture.lst","--sym=p827-man-fixture.sym","p827-man-fixture.asm"],cwd=build,timeout_seconds=30); require(not fr.timed_out and fr.exit_code==0,f"P8.27 fixture assembly failed: {fr.stderr or fr.stdout}")
    gate=build/"p827-gateway.asm"; gate.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    ORG $E000
gate:
    cp SYS_WRITE
    jr z,g_write
    cp SYS_EXIT
    jr z,g_exit
    ld a,E_NOTSUP
    scf
    ret
g_write:
    ld a,e
    cp 1
    jr nz,g_bad
    ld a,d
    or a
    jr nz,g_bad
    ld a,($A282)
    cp 2
    jr z,g_fail
    cp 1
    jr nz,g_all
    ld a,b
    or a
    jr nz,g_two
    ld a,c
    cp 3
    jr c,g_all
g_two:
    ld bc,2
g_all:
    push bc
    ld de,(g_out)
    ldir
    ld (g_out),de
    pop hl
    xor a
    ret
g_fail:
    ld a,E_IO
    scf
    ret
g_exit:
    ld a,l
    ld ($A280),a
    ld a,1
    ld ($A281),a
    xor a
    ret
g_bad:
    ld a,E_INVAL
    scf
    ret
g_out: dw $A300
gate_end:
    SAVEBIN "p827-gateway.bin",gate,gate_end-gate
""",newline="\n")
    gr=run_command([tool,"--nologo","--lst=p827-gateway.lst","--sym=p827-gateway.sym","p827-gateway.asm"],cwd=build,timeout_seconds=30); require(not gr.timed_out and gr.exit_code==0,f"P8.27 gateway assembly failed: {gr.stderr or gr.stdout}")
    if action=="test":
        sy=phase3_open_descriptions._symbols(build/"p827-man-fixture.sym",("man_entry",)); ub=(build/"p827-man-fixture.bin").read_bytes(); gb=(build/"p827-gateway.bin").read_bytes()
        cases=[
          ([b"man"],b"Manuals: https://supratim-sanyal.blogspot.com/\nSearch for ZXUS\n",0),
          ([b"man",b"cron"],b"Manuals: https://supratim-sanyal.blogspot.com/\nSearch for ZXUS\nTopic: cron\n",0),
          ([b"man",b"a",b"b"],b"",1),
        ]
        for args,expected,status in cases:
            ab=arg1(args); code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._ld_hl(ARG)+b"\x01"+word(len(ab))+phase1._call(sy["man_entry"]))
            for o,v in enumerate(expected): code+=expect(OUT+o,v)
            code+=expect(OUT+len(expected),0xA5)+expect(STATUS,status)+expect(STATUS+1,1)+phase1._jp(PASS_PC)
            run_sna(root,bytes(code),patch=patch(ub,gb,args,[],0,False))
        assertions += [{"name":"fuse-base-lines","passed":True},{"name":"fuse-topic-suggestion","passed":True},{"name":"fuse-arity","passed":True}]
    hashes={"v1/src/utils/man.asm":sha256_file(root/"v1/src/utils/man.asm"),"v1/build/p827-man.mex1":sha256_file(mex),"v1/build/p827-man.tap":sha256_file(tap),"v1/tools-host/test-driver/phase8_man.py":sha256_file(root/"v1/tools-host/test-driver/phase8_man.py"),"v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),"v1/dist/certification/P8.26.test.json":sha256_file(root/"v1/dist/certification/P8.26.test.json")}
    return [ir,xr,fr,gr],hashes,assertions
