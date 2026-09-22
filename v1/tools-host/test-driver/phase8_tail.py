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

UTIL=0xC000; GATE=0xE000; ARG=0xA000; OUT=0xA300; MODE=0xA2F0; STATUS=0xA2F1
class P811Error(DriverError): pass
def require(v,m):
    if not v: raise P811Error(m)
def expect(addr,val): return b"\x3A"+word(addr)+bytes((0xFE,val&255))+phase1._jp_nz(0x8F00)
def patch(util,gate,args,mode):
    block=arg1(args)
    def apply(ram):
        ram[UTIL-0x4000:UTIL-0x4000+len(util)]=util; ram[GATE-0x4000:GATE-0x4000+len(gate)]=gate
        ram[ARG-0x4000:ARG-0x4000+len(block)]=block; ram[OUT-0x4000:OUT-0x4000+64]=b"\xA5"*64
        ram[MODE-0x4000]=mode; ram[STATUS-0x4000:STATUS-0x4000+10]=b"\0"*10
    return apply
def source_contract(root):
    s=(root/"v1/src/utils/tail.asm").read_text(); p=(root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md").read_text()
    return [
      {"name":"canonical-p811-present","passed":"## P8.11 - Utility `tail`" in p},
      {"name":"default-ten","passed":"ld a,10" in s},
      {"name":"strict-decimal","passed":"tail_parse_n:" in s and "cp '0'" in s and "cp '9'+1" in s},
      {"name":"range-1-255","passed":"cp 26" in s},
      {"name":"single-pass-stdin","passed":"ld de,0" in s and "SYS_READ" in s},
      {"name":"bounded-staging","passed":"tail_buffer: defs 4096,0" in s and "E_NOSPC" in s},
      {"name":"backward-line-selection","passed":"tail_scan:" in s and "cp 10" in s},
      {"name":"stdout-short-write-safe","passed":"tail_write_loop:" in s and "tail_write_zero:" in s},
    ]
def dispatch(root,action,step,*,sha256_file,run_command,require_project_tool):
    if step!="P8.11": raise DriverError(f"Phase-8 tail step is not registered: {step}")
    assertions=source_contract(root); require(all(x["passed"] for x in assertions),"P8.11 static contract failure")
    tool=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus"); build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    try: ir,image,mex=assemble_utility(root,build,tool,"tail","p811","EMIT_P811_TAIL_ROUTINES",run_command); xr=inspect_mex(root,mex,run_command,require_project_tool); tap=make_tap(root,build,"tail","p811",mex)
    except RuntimeError as e: raise P811Error(str(e))
    require(4096<=len(image)<8192,"P8.11 image size implausible")
    fix=build/"p811-tail-fixture.asm"; fix.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/utils/tail.asm"
    ORG $C000
fixture:
    EMIT_P811_TAIL_ROUTINES
fixture_end:
    SAVEBIN "p811-tail-fixture.bin",fixture,fixture_end-fixture
""",newline="\n")
    fr=run_command([tool,"--nologo","--lst=p811-tail-fixture.lst","--sym=p811-tail-fixture.sym","p811-tail-fixture.asm"],cwd=build,timeout_seconds=30); require(not fr.timed_out and fr.exit_code==0,f"P8.11 fixture assembly failed: {fr.stderr or fr.stdout}")
    gate=build/"p811-gateway.asm"; gate.write_text("""    DEVICE ZXSPECTRUM48
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
    ld (g_dest),hl
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
    ld hl,g_data
    add hl,de
    ld a,(hl)
    ld hl,(g_dest)
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
    jr nz,g_write_two
    ld a,c
    cp 3
    jr c,g_write_all
g_write_two:
    ld bc,2
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
g_data: db 'a',10,'bb',10,'ccc',10,'dddd',10
g_data_end:
g_index: db 0
g_dest: dw 0
g_out: dw $A300
gate_end:
    SAVEBIN "p811-gateway.bin",gate,gate_end-gate
""",newline="\n")
    gr=run_command([tool,"--nologo","--lst=p811-gateway.lst","--sym=p811-gateway.sym","p811-gateway.asm"],cwd=build,timeout_seconds=30); require(not gr.timed_out and gr.exit_code==0,f"P8.11 gateway assembly failed: {gr.stderr or gr.stdout}")
    if action=="test":
        sy=phase3_open_descriptions._symbols(build/"p811-tail-fixture.sym",("tail_entry",)); ub=(build/"p811-tail-fixture.bin").read_bytes(); gb=(build/"p811-gateway.bin").read_bytes()
        cases=[([b"tail"],0,b"a\nbb\nccc\ndddd\n",0),([b"tail",b"2"],0,b"ccc\ndddd\n",0),([b"tail",b"2"],1,b"ccc\ndddd\n",0),([b"tail",b"2"],2,b"",5),([b"tail",b"0"],0,b"",1),([b"tail",b"256"],0,b"",1),([b"tail",b"x"],0,b"",1),([b"tail",b"1",b"2"],0,b"",1)]
        for args,mode,expected,status in cases:
            block=arg1(args); code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._ld_hl(ARG)+b"\x01"+word(len(block))+phase1._call(sy["tail_entry"]))
            for o,v in enumerate(expected): code+=expect(OUT+o,v)
            code+=expect(OUT+len(expected),0xA5)+expect(STATUS,status)+expect(STATUS+1,1)+phase1._jp(PASS_PC)
            run_sna(root,bytes(code),patch=patch(ub,gb,args,mode))
        assertions += [{"name":"fuse-default-ten","passed":True},{"name":"fuse-last-two","passed":True},{"name":"fuse-short-write","passed":True},{"name":"fuse-read-error","passed":True},{"name":"fuse-invalid-range-and-arity","passed":True}]
    hashes={"v1/src/utils/tail.asm":sha256_file(root/"v1/src/utils/tail.asm"),"v1/build/p811-tail.mex1":sha256_file(mex),"v1/build/p811-tail.tap":sha256_file(tap),"v1/tools-host/test-driver/phase8_tail.py":sha256_file(root/"v1/tools-host/test-driver/phase8_tail.py"),"v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),"v1/dist/certification/P8.10.test.json":sha256_file(root/"v1/dist/certification/P8.10.test.json")}
    return [ir,xr,fr,gr],hashes,assertions
