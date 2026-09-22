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
from fuse_harness import FAIL_PC, PASS_PC, run_sna
from phase8_common import arg1, word, assemble_utility, inspect_mex, make_tap

UTIL=0xC000; GATE=0xE000; ARG=0xA000; OUT=0xA400; STATUS=0xA300; MODE=0xA301; YIELDS=0xA302
class P835Error(DriverError):
    pass
def require(v,m):
    if not v: raise P835Error(m)
def expect(a,v): return b"\x3A"+word(a)+bytes((0xFE,v&255))+phase1._jp_nz(FAIL_PC)
def patch(util,gate,args,mode):
    ab=arg1(args)
    def apply(ram):
        ram[UTIL-0x4000:UTIL-0x4000+len(util)]=util
        ram[GATE-0x4000:GATE-0x4000+len(gate)]=gate
        ram[ARG-0x4000:ARG-0x4000+len(ab)]=ab
        ram[OUT-0x4000:OUT-0x4000+128]=b"\xA5"*128
        ram[STATUS-0x4000]=0xFF; ram[MODE-0x4000]=mode; ram[YIELDS-0x4000]=0
    return apply

def dispatch(root,action,step,*,sha256_file,run_command,require_project_tool):
    if step!="P8.35": raise DriverError(step)
    s=(root/"v1/src/utils/yes.asm").read_text(encoding="utf-8")
    p=(root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md").read_text(encoding="utf-8")
    assertions=[
      {"name":"canonical-p835-present","passed":"## P8.35 - Utility `yes`" in p},
      {"name":"zero-one-argument","passed":"cp 1" in s and "cp 2" in s and "E_INVAL" in s},
      {"name":"default-y","passed":"yes_y: db 'y'" in s},
      {"name":"lf-per-line","passed":"yes_lf: db 10" in s},
      {"name":"yield-per-line","passed":"SYS_YIELD" in s and s.index("SYS_YIELD") > s.index("yes_lf")},
      {"name":"short-write-safe","passed":"yes_write_loop:" in s and "yes_io:" in s},
    ]
    require(all(x["passed"] for x in assertions),"P8.35 static contract failure")
    tool=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus"); b=root/"v1/build"; b.mkdir(parents=True,exist_ok=True)
    try:
        ir,image,mex=assemble_utility(root,b,tool,"yes","p835","EMIT_P835_YES_ROUTINES",run_command)
        xr=inspect_mex(root,mex,run_command,require_project_tool); tap=make_tap(root,b,"yes","p835",mex)
    except RuntimeError as e: raise P835Error(str(e))
    fix=b/"p835-yes-fixture.asm"; fix.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/utils/yes.asm"
    ORG $C000
fixture:
    EMIT_P835_YES_ROUTINES
fixture_end:
    SAVEBIN "p835-yes-fixture.bin",fixture,fixture_end-fixture
""",encoding="utf-8",newline="\n")
    fr=run_command([tool,"--nologo","--lst=p835-yes-fixture.lst","--sym=p835-yes-fixture.sym",fix.name],cwd=b,timeout_seconds=30); require(not fr.timed_out and fr.exit_code==0,f"P8.35 fixture: {fr.stderr or fr.stdout}")
    gate=b/"p835-gateway.asm"; gate.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    ORG $E000
gate:
    cp SYS_WRITE
    jr z,g_write
    cp SYS_YIELD
    jr z,g_yield
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
    ld a,($A301)
    cp 2
    jr z,g_pipe
    push bc
    ld de,(g_out)
    ldir
    ld (g_out),de
    pop hl
    xor a
    ret
g_pipe:
    ld a,E_PIPE
    scf
    ret
g_yield:
    ld a,($A302)
    inc a
    ld ($A302),a
    cp 3
    jr c,g_yield_ok
    ld a,E_INTR
    scf
    ret
g_yield_ok:
    xor a
    ret
g_exit:
    ld a,l
    ld ($A300),a
    xor a
    ret
g_bad:
    ld a,E_INVAL
    scf
    ret
g_out: dw $A400
gate_end:
    SAVEBIN "p835-gateway.bin",gate,gate_end-gate
""",encoding="utf-8",newline="\n")
    gr=run_command([tool,"--nologo","--lst=p835-gateway.lst","--sym=p835-gateway.sym",gate.name],cwd=b,timeout_seconds=30); require(not gr.timed_out and gr.exit_code==0,f"P8.35 gateway: {gr.stderr or gr.stdout}")
    if action=="test":
        sy=phase3_open_descriptions._symbols(b/"p835-yes-fixture.sym",("yes_entry","E_INVAL","E_INTR","E_PIPE"))
        ub=(b/"p835-yes-fixture.bin").read_bytes(); gb=(b/"p835-gateway.bin").read_bytes()
        for args,want in (([b"yes"],b"y\ny\ny\n"),([b"yes",b"ok"],b"ok\nok\nok\n")):
            ab=arg1(args); code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._ld_hl(ARG)+b"\x01"+word(len(ab))+phase1._call(sy["yes_entry"]))
            for i,v in enumerate(want): code+=expect(OUT+i,v)
            code+=expect(OUT+len(want),0xA5)+expect(STATUS,sy["E_INTR"]&255)+expect(YIELDS,3)+phase1._jp(PASS_PC)
            run_sna(root,bytes(code),patch=patch(ub,gb,args,0),timeout=30)
        args=[b"yes"]; ab=arg1(args); code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._ld_hl(ARG)+b"\x01"+word(len(ab))+phase1._call(sy["yes_entry"])+expect(STATUS,sy["E_PIPE"]&255)+expect(YIELDS,0)+phase1._jp(PASS_PC))
        run_sna(root,bytes(code),patch=patch(ub,gb,args,2),timeout=30)
        args=[b"yes",b"a",b"b"]; ab=arg1(args); code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._ld_hl(ARG)+b"\x01"+word(len(ab))+phase1._call(sy["yes_entry"])+expect(STATUS,sy["E_INVAL"]&255)+phase1._jp(PASS_PC))
        run_sna(root,bytes(code),patch=patch(ub,gb,args,0),timeout=30)
        assertions += [{"name":"fuse-default-y-and-yield","passed":True},{"name":"fuse-one-argument","passed":True},{"name":"fuse-pipe-error","passed":True},{"name":"fuse-extra-argument","passed":True}]
    hashes={"v1/src/utils/yes.asm":sha256_file(root/"v1/src/utils/yes.asm"),"v1/build/p835-yes.mex1":sha256_file(mex),"v1/build/p835-yes.tap":sha256_file(tap),"v1/tools-host/test-driver/phase8_yes.py":sha256_file(root/"v1/tools-host/test-driver/phase8_yes.py"),"v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),"v1/dist/certification/P8.34.test.json":sha256_file(root/"v1/dist/certification/P8.34.test.json")}
    return [ir,xr,fr,gr],hashes,assertions
