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
import phase1, phase3_open_descriptions
from driver_core import DriverError
from fuse_harness import FAIL_PC, PASS_PC, run_sna
from phase8_common import arg1, word, assemble_utility, inspect_mex, make_tap

UTIL=0xC000; GATE=0xE000; ARG=0xA000; OUT=0xA200; MODE=0xA3F0; STATUS=0xA3F1; COUNTERS=0xA3F3
class P806Error(DriverError): pass
def require(v,m):
    if not v: raise P806Error(m)
def expect(addr,val): return b"\x3A"+word(addr)+bytes((0xFE,val&255))+phase1._jp_nz(FAIL_PC)
def patch(util,gate,args,mode):
    block=arg1(args)
    def apply(ram):
        ram[UTIL-0x4000:UTIL-0x4000+len(util)]=util; ram[GATE-0x4000:GATE-0x4000+len(gate)]=gate
        ram[ARG-0x4000:ARG-0x4000+len(block)]=block; ram[OUT-0x4000:OUT-0x4000+64]=b"\xA5"*64
        ram[MODE-0x4000]=mode; ram[STATUS-0x4000:STATUS-0x4000+10]=b"\0"*10
    return apply
def source_contract(root):
    s=(root/"v1/src/utils/pack.asm").read_text(); p=(root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md").read_text()
    return [
      {"name":"canonical-p806-present","passed":"## P8.06 - Utility `pack`" in p},
      {"name":"sys-pack","passed":"SYS_PACK" in s},
      {"name":"post-pack-stat","passed":"SYS_STAT" in s and "pack_stat_out" in s},
      {"name":"packed-only-report","passed":"and OBJ_PACKED" in s},
      {"name":"logical-physical-arrow","passed":"pack_arrow: db ' ','-','>',' '" in s},
      {"name":"short-write-safe","passed":"pack_write_loop:" in s and "pack_write_zero:" in s},
      {"name":"noncompressible-success","passed":"jr z,pack_success" in s},
      {"name":"exact-one-operand","passed":"cp 2" in s and "E_INVAL" in s},
      {"name":"no-case-folding","passed":"casefold" not in s.lower()},
    ]
def dispatch(root,action,step,*,sha256_file,run_command,require_project_tool):
    if step!="P8.06": raise DriverError(f"Phase-8 pack step is not registered: {step}")
    assertions=source_contract(root); require(all(x["passed"] for x in assertions),"P8.06 static contract failure")
    tool=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus"); build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    try: ir,image,mex=assemble_utility(root,build,tool,"pack","p806","EMIT_P806_PACK_ROUTINES",run_command)
    except RuntimeError as e: raise P806Error(str(e))
    require(64<=len(image)<2048,"P8.06 image size implausible")
    try: xr=inspect_mex(root,mex,run_command,require_project_tool); tap=make_tap(root,build,"pack","p806",mex)
    except RuntimeError as e: raise P806Error(str(e))
    fix=build/"p806-pack-fixture.asm"; fix.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/utils/pack.asm"
    ORG $C000
fixture:
    EMIT_P806_PACK_ROUTINES
fixture_end:
    SAVEBIN "p806-pack-fixture.bin",fixture,fixture_end-fixture
""",newline="\n")
    fr=run_command([tool,"--nologo","--lst=p806-pack-fixture.lst","--sym=p806-pack-fixture.sym","p806-pack-fixture.asm"],cwd=build,timeout_seconds=30); require(not fr.timed_out and fr.exit_code==0,f"P8.06 fixture assembly failed: {fr.stderr or fr.stdout}")
    gate=build/"p806-gateway.asm"; gate.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    ORG $E000
gate:
    cp SYS_PACK
    jp z,g_pack
    cp SYS_STAT
    jp z,g_stat
    cp SYS_WRITE
    jp z,g_write
    cp SYS_EXIT
    jp z,g_exit
    ld a,E_NOTSUP
    scf
    ret
g_pack:
    ld a,($A3F3)
    inc a
    ld ($A3F3),a
    ld a,($A3F0)
    cp 2
    jr z,g_pack_fail
    ld hl,60
    xor a
    ret
g_pack_fail:
    ld a,E_BUSY
    scf
    ret
g_stat:
    ld a,($A3F4)
    inc a
    ld ($A3F4),a
    inc hl
    inc hl
    ld e,(hl)
    inc hl
    ld d,(hl)
    ex de,hl
    ld a,($A3F0)
    cp 1
    jr z,g_stat_raw
    ld (hl),OBJ_DAT
    inc hl
    ld (hl),OBJ_PACKED
    inc hl
    ld (hl),100
    inc hl
    ld (hl),0
    inc hl
    ld (hl),40
    inc hl
    ld (hl),0
    jr g_stat_tail
g_stat_raw:
    ld (hl),OBJ_DAT
    inc hl
    ld (hl),0
    inc hl
    ld (hl),100
    inc hl
    ld (hl),0
    inc hl
    ld (hl),100
    inc hl
    ld (hl),0
g_stat_tail:
    inc hl
    ld (hl),DIR_TMP
    inc hl
    ld (hl),STATE_RAM
    inc hl
    xor a
    ld (hl),a
    inc hl
    ld (hl),a
    xor a
    ret
g_write:
    ld a,($A3F5)
    inc a
    ld ($A3F5),a
    ld a,e
    cp 1
    jr nz,g_bad
    ld a,d
    or a
    jr nz,g_bad
    ld a,($A3F0)
    cp 3
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
    ld ($A3F1),a
    ld a,1
    ld ($A3F6),a
    xor a
    ret
g_bad:
    ld a,E_INVAL
    scf
    ret
g_out: dw $A200
gate_end:
    SAVEBIN "p806-gateway.bin",gate,gate_end-gate
""",newline="\n")
    gr=run_command([tool,"--nologo","--lst=p806-gateway.lst","--sym=p806-gateway.sym","p806-gateway.asm"],cwd=build,timeout_seconds=30); require(not gr.timed_out and gr.exit_code==0,f"P8.06 gateway assembly failed: {gr.stderr or gr.stdout}")
    if action=="test":
        sy=phase3_open_descriptions._symbols(build/"p806-pack-fixture.sym",("pack_entry",)); ub=(build/"p806-pack-fixture.bin").read_bytes(); gb=(build/"p806-gateway.bin").read_bytes()
        for args,mode,expected,status,counters in [([b"pack",b"MiXeD"],0,b"100 -> 40\n",0,(1,1)),([b"pack",b"raw"],1,b"",0,(1,1)),([b"pack",b"busy"],2,b"",4,(1,0)),([b"pack",b"short"],3,b"100 -> 40\n",0,(1,1)),([b"pack"],0,b"",1,(0,0))]:
            block=arg1(args); code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._ld_hl(ARG)+b"\x01"+word(len(block))+phase1._call(sy["pack_entry"]))
            for o,v in enumerate(expected): code+=expect(OUT+o,v)
            code+=expect(OUT+len(expected),0xA5)+expect(STATUS,status)+expect(COUNTERS,counters[0])+expect(COUNTERS+1,counters[1])+expect(STATUS+5,1)+phase1._jp(PASS_PC)
            run_sna(root,bytes(code),patch=patch(ub,gb,args,mode))
        assertions += [{"name":"fuse-packed-report","passed":True},{"name":"fuse-raw-noncompressible-success","passed":True},{"name":"fuse-pack-error-propagates","passed":True},{"name":"fuse-short-write-retried","passed":True},{"name":"fuse-invalid-arity-no-pack","passed":True}]
    hashes={"v1/src/utils/pack.asm":sha256_file(root/"v1/src/utils/pack.asm"),"v1/build/p806-pack.mex1":sha256_file(mex),"v1/build/p806-pack.tap":sha256_file(tap),"v1/tools-host/test-driver/phase8_pack.py":sha256_file(root/"v1/tools-host/test-driver/phase8_pack.py"),"v1/tools-host/test-driver/phase8_common.py":sha256_file(root/"v1/tools-host/test-driver/phase8_common.py"),"v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),"v1/dist/certification/P8.05.test.json":sha256_file(root/"v1/dist/certification/P8.05.test.json")}
    return [ir,xr,fr,gr],hashes,assertions
