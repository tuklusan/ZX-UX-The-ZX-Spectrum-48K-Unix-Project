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

UTIL=0xC000; GATE=0xE000; ARG=0xA000; OUT=0xA400; STATUS=0xA300; TICKS=0xA304
class P829Error(DriverError):
    pass
def require(v,m):
    if not v: raise P829Error(m)
def expect(a,v): return b"\x3A"+word(a)+bytes((0xFE,v&255))+phase1._jp_nz(FAIL_PC)
def patch(util,gate,args,ticks):
    ab=arg1(args)
    def apply(ram):
        ram[UTIL-0x4000:UTIL-0x4000+len(util)]=util
        ram[GATE-0x4000:GATE-0x4000+len(gate)]=gate
        ram[ARG-0x4000:ARG-0x4000+len(ab)]=ab
        ram[OUT-0x4000:OUT-0x4000+32]=b"\xA5"*32
        ram[STATUS-0x4000]=0xFF
        ram[TICKS-0x4000:TICKS-0x4000+4]=ticks.to_bytes(4,"little")
    return apply

def dispatch(root,action,step,*,sha256_file,run_command,require_project_tool):
    if step!="P8.29": raise DriverError(step)
    s=(root/"v1/src/utils/uptime.asm").read_text(encoding="utf-8")
    p=(root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md").read_text(encoding="utf-8")
    assertions=[
      {"name":"canonical-p829-present","passed":"## P8.29 - Utility `uptime`" in p},
      {"name":"sys-ticks-only","passed":"SYS_TICKS" in s and "SYS_TIME_GET" not in s and "SYS_TIME_SET" not in s},
      {"name":"u32-format","passed":"uptime_div10:" in s and "uptime_ticks: defs 4" in s},
      {"name":"modulo-independent","passed":"uptime_format_u32:" in s},
      {"name":"short-write-safe","passed":"uptime_write_loop:" in s and "uptime_io:" in s},
      {"name":"arity","passed":"cp 1" in s and "E_INVAL" in s},
    ]
    require(all(x["passed"] for x in assertions),"P8.29 static contract failure")
    tool=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus"); b=root/"v1/build"; b.mkdir(parents=True,exist_ok=True)
    try:
        ir,image,mex=assemble_utility(root,b,tool,"uptime","p829","EMIT_P829_UPTIME_ROUTINES",run_command)
        xr=inspect_mex(root,mex,run_command,require_project_tool); tap=make_tap(root,b,"uptime","p829",mex)
    except RuntimeError as e: raise P829Error(str(e))
    fix=b/"p829-uptime-fixture.asm"; fix.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/utils/uptime.asm"
    ORG $C000
fixture:
    EMIT_P829_UPTIME_ROUTINES
fixture_end:
    SAVEBIN "p829-uptime-fixture.bin",fixture,fixture_end-fixture
""",encoding="utf-8",newline="\n")
    fr=run_command([tool,"--nologo","--lst=p829-uptime-fixture.lst","--sym=p829-uptime-fixture.sym",fix.name],cwd=b,timeout_seconds=30); require(not fr.timed_out and fr.exit_code==0,f"P8.29 fixture: {fr.stderr or fr.stdout}")
    gate=b/"p829-gateway.asm"; gate.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    ORG $E000
gate:
    cp SYS_TICKS
    jr z,g_ticks
    cp SYS_WRITE
    jr z,g_write
    cp SYS_EXIT
    jr z,g_exit
    ld a,E_NOTSUP
    scf
    ret
g_ticks:
    push hl
    ld de,$A304
    ex de,hl
    ld bc,4
    ldir
    pop hl
    xor a
    ret
g_write:
    ld a,e
    cp 1
    jr nz,g_bad
    ld a,d
    or a
    jr nz,g_bad
    push bc
    ld de,(g_out)
    ldir
    ld (g_out),de
    pop hl
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
    SAVEBIN "p829-gateway.bin",gate,gate_end-gate
""",encoding="utf-8",newline="\n")
    gr=run_command([tool,"--nologo","--lst=p829-gateway.lst","--sym=p829-gateway.sym",gate.name],cwd=b,timeout_seconds=30); require(not gr.timed_out and gr.exit_code==0,f"P8.29 gateway: {gr.stderr or gr.stdout}")
    if action=="test":
        sy=phase3_open_descriptions._symbols(b/"p829-uptime-fixture.sym",("uptime_entry","E_INVAL"))
        ub=(b/"p829-uptime-fixture.bin").read_bytes(); gb=(b/"p829-gateway.bin").read_bytes()
        for ticks,want in ((0,b"0\n"),(1,b"1\n"),(50,b"50\n"),(4294967295,b"4294967295\n")):
            args=[b"uptime"]; ab=arg1(args); code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._ld_hl(ARG)+b"\x01"+word(len(ab))+phase1._call(sy["uptime_entry"]))
            for i,v in enumerate(want): code+=expect(OUT+i,v)
            code+=expect(OUT+len(want),0xA5)+expect(STATUS,0)+phase1._jp(PASS_PC)
            run_sna(root,bytes(code),patch=patch(ub,gb,args,ticks),timeout=30)
        args=[b"uptime",b"x"]; ab=arg1(args); code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._ld_hl(ARG)+b"\x01"+word(len(ab))+phase1._call(sy["uptime_entry"])+expect(STATUS,sy["E_INVAL"]&255)+phase1._jp(PASS_PC))
        run_sna(root,bytes(code),patch=patch(ub,gb,args,0),timeout=30)
        assertions += [{"name":"fuse-u32-boundaries","passed":True},{"name":"fuse-wrap-value","passed":True},{"name":"fuse-arity","passed":True}]
    hashes={"v1/src/utils/uptime.asm":sha256_file(root/"v1/src/utils/uptime.asm"),"v1/build/p829-uptime.mex1":sha256_file(mex),"v1/build/p829-uptime.tap":sha256_file(tap),"v1/tools-host/test-driver/phase8_uptime.py":sha256_file(root/"v1/tools-host/test-driver/phase8_uptime.py"),"v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),"v1/dist/certification/P8.28.test.json":sha256_file(root/"v1/dist/certification/P8.28.test.json")}
    return [ir,xr,fr,gr],hashes,assertions
