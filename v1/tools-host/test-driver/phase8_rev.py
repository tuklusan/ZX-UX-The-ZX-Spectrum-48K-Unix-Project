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

UTIL=0xC000; GATE=0xE000; ARG=0xA000; OUT=0xA300; MODE=0xA2F0; STATUS=0xA2F1
class P834Error(DriverError):
    pass
def require(v,m):
    if not v: raise P834Error(m)
def expect(a,v): return b"\x3A"+word(a)+bytes((0xFE,v&255))+phase1._jp_nz(FAIL_PC)
def patch(util,gate,args,mode):
    ab=arg1(args)
    def apply(ram):
        ram[UTIL-0x4000:UTIL-0x4000+len(util)]=util
        ram[GATE-0x4000:GATE-0x4000+len(gate)]=gate
        ram[ARG-0x4000:ARG-0x4000+len(ab)]=ab
        ram[OUT-0x4000:OUT-0x4000+64]=b"\xA5"*64
        ram[MODE-0x4000]=mode
        ram[STATUS-0x4000:STATUS-0x4000+4]=b"\0"*4
    return apply

def dispatch(root,action,step,*,sha256_file,run_command,require_project_tool):
    if step!="P8.34": raise DriverError(step)
    s=(root/"v1/src/utils/rev.asm").read_text(encoding="utf-8")
    p=(root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md").read_text(encoding="utf-8")
    assertions=[
      {"name":"canonical-p834-present","passed":"## P8.34 - Utility `rev`" in p},
      {"name":"stdin-stream","passed":"SYS_READ" in s and "ld de,0" in s},
      {"name":"line-bounded","passed":"rev_buffer: defs 255" in s and "E_TOOLONG" in s},
      {"name":"lf-preserved","passed":"rev_lf: db 10" in s},
      {"name":"short-write-safe","passed":"rev_write_loop:" in s and "rev_io:" in s},
      {"name":"no-whole-input-buffer","passed":"rev_read_loop:" in s and "rev_emit_line:" in s},
    ]
    require(all(x["passed"] for x in assertions),"P8.34 static contract failure")
    tool=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus"); b=root/"v1/build"; b.mkdir(parents=True,exist_ok=True)
    try:
        ir,image,mex=assemble_utility(root,b,tool,"rev","p834","EMIT_P834_REV_ROUTINES",run_command)
        xr=inspect_mex(root,mex,run_command,require_project_tool); tap=make_tap(root,b,"rev","p834",mex)
    except RuntimeError as e: raise P834Error(str(e))
    fix=b/"p834-rev-fixture.asm"; fix.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/utils/rev.asm"
    ORG $C000
fixture:
    EMIT_P834_REV_ROUTINES
fixture_end:
    SAVEBIN "p834-rev-fixture.bin",fixture,fixture_end-fixture
""",encoding="utf-8",newline="\n")
    fr=run_command([tool,"--nologo","--lst=p834-rev-fixture.lst","--sym=p834-rev-fixture.sym",fix.name],cwd=b,timeout_seconds=30)
    require(not fr.timed_out and fr.exit_code==0,f"P8.34 fixture: {fr.stderr or fr.stdout}")
    gate=b/"p834-gateway.asm"; gate.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    ORG $E000
gate:
    cp SYS_READ
    jp z,g_read
    cp SYS_WRITE
    jp z,g_write
    cp SYS_EXIT
    jp z,g_exit
    ld a,E_NOTSUP
    scf
    ret
g_read:
    ld a,($A2F0)
    cp 2
    jr z,g_read_fail
    ld a,(g_index)
    ld c,a
    ld a,g_data_end-g_data
    cp c
    jr z,g_eof
    ld e,c
    ld d,0
    push hl
    ld hl,g_data
    add hl,de
    ld a,(hl)
    pop hl
    ld (hl),a
    ld a,(g_index)
    inc a
    ld (g_index),a
    ld hl,1
    xor a
    ret
g_eof:
    ld hl,0
    xor a
    ret
g_read_fail:
    ld a,E_IO
    scf
    ret
g_write:
    ld a,e
    cp 1
    jr nz,g_bad
    ld a,d
    or a
    jr nz,g_bad
    ld a,($A2F0)
    cp 1
    jr nz,g_write_all
    ld a,b
    or a
    jr nz,g_write_one
    ld a,c
    cp 2
    jr c,g_write_all
g_write_one:
    ld bc,1
g_write_all:
    push bc
    ld de,(g_out)
    ldir
    ld (g_out),de
    pop hl
    xor a
    ret
g_exit:
    ld a,l
    ld ($A2F1),a
    ld a,1
    ld ($A2F2),a
    xor a
    ret
g_bad:
    ld a,E_INVAL
    scf
    ret
g_data: db 'a','b','c',10,'1','2',10,'x','y','z'
g_data_end:
g_index: db 0
g_out: dw $A300
gate_end:
    SAVEBIN "p834-gateway.bin",gate,gate_end-gate
""",encoding="utf-8",newline="\n")
    gr=run_command([tool,"--nologo","--lst=p834-gateway.lst","--sym=p834-gateway.sym",gate.name],cwd=b,timeout_seconds=30)
    require(not gr.timed_out and gr.exit_code==0,f"P8.34 gateway: {gr.stderr or gr.stdout}")
    if action=="test":
        sy=phase3_open_descriptions._symbols(b/"p834-rev-fixture.sym",("rev_entry","E_INVAL"))
        ub=(b/"p834-rev-fixture.bin").read_bytes(); gb=(b/"p834-gateway.bin").read_bytes()
        want=b"cba\n21\nzyx"
        for mode,status in ((0,0),(1,0),(2,5)):
            args=[b"rev"]; ab=arg1(args); code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._ld_hl(ARG)+b"\x01"+word(len(ab))+phase1._call(sy["rev_entry"]))
            if mode!=2:
                for i,v in enumerate(want): code+=expect(OUT+i,v)
                code+=expect(OUT+len(want),0xA5)
            code+=expect(STATUS,status)+expect(STATUS+1,1)+phase1._jp(PASS_PC)
            run_sna(root,bytes(code),patch=patch(ub,gb,args,mode),timeout=30)
        args=[b"rev",b"x"]; ab=arg1(args); code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._ld_hl(ARG)+b"\x01"+word(len(ab))+phase1._call(sy["rev_entry"])+expect(STATUS,sy["E_INVAL"]&255)+phase1._jp(PASS_PC))
        run_sna(root,bytes(code),patch=patch(ub,gb,args,0),timeout=30)
        assertions += [{"name":"fuse-lines-and-final-partial","passed":True},{"name":"fuse-short-write","passed":True},{"name":"fuse-read-error","passed":True},{"name":"fuse-arity","passed":True}]
    hashes={"v1/src/utils/rev.asm":sha256_file(root/"v1/src/utils/rev.asm"),"v1/build/p834-rev.mex1":sha256_file(mex),"v1/build/p834-rev.tap":sha256_file(tap),"v1/tools-host/test-driver/phase8_rev.py":sha256_file(root/"v1/tools-host/test-driver/phase8_rev.py"),"v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),"v1/dist/certification/P8.33.test.json":sha256_file(root/"v1/dist/certification/P8.33.test.json")}
    return [ir,xr,fr,gr],hashes,assertions
