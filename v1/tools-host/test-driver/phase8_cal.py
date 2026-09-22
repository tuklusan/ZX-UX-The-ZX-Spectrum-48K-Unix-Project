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

UTIL=0xC000; GATE=0xE000; ARG=0xA000; OUT=0xA400; STATUS=0xA300; MODE=0xA301
class P828Error(DriverError):
    pass
def require(v,m):
    if not v: raise P828Error(m)
def expect(a,v): return b"\x3A"+word(a)+bytes((0xFE,v&255))+phase1._jp_nz(0x8F00)
def patch(util,gate,args,mode=0):
    ab=arg1(args)
    def apply(ram):
        ram[UTIL-0x4000:UTIL-0x4000+len(util)]=util
        ram[GATE-0x4000:GATE-0x4000+len(gate)]=gate
        ram[ARG-0x4000:ARG-0x4000+len(ab)]=ab
        ram[OUT-0x4000:OUT-0x4000+256]=b"\xA5"*256
        ram[STATUS-0x4000]=0xFF; ram[MODE-0x4000]=mode
    return apply

def dispatch(root,action,step,*,sha256_file,run_command,require_project_tool):
    if step!="P8.28": raise DriverError(step)
    s=(root/"v1/src/utils/cal.asm").read_text(encoding="utf-8")
    p=(root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md").read_text(encoding="utf-8")
    assertions=[
      {"name":"canonical-p828-present","passed":"## P8.28 - Utility `cal`" in p},
      {"name":"forms","passed":"cal_current:" in s and "cal_one:" in s and "cal_render:" in s},
      {"name":"time-gated-current","passed":"SYS_TIME_GET" in s and "cal: date not set" not in s and "cal_not_set:" in s},
      {"name":"range-1970-2099","passed":"ld bc,1970" in s and "ld bc,2100" in s},
      {"name":"gregorian-months","passed":"cal_month_lengths:" in s and "and 3" in s},
      {"name":"short-write-safe","passed":"cal_write_loop:" in s and "cal_write_io:" in s},
      {"name":"case-sensitive","passed":"casefold" not in s.lower()},
    ]
    require(all(x["passed"] for x in assertions),"P8.28 static contract failure")
    tool=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus"); b=root/"v1/build"; b.mkdir(parents=True,exist_ok=True)
    try:
        ir,image,mex=assemble_utility(root,b,tool,"cal","p828","EMIT_P828_CAL_ROUTINES",run_command)
        xr=inspect_mex(root,mex,run_command,require_project_tool); tap=make_tap(root,b,"cal","p828",mex)
    except RuntimeError as e: raise P828Error(str(e))
    require(256<=len(image)<8192,"P8.28 image size implausible")
    fix=b/"p828-cal-fixture.asm"; fix.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/utils/cal.asm"
    ORG $C000
fixture:
    EMIT_P828_CAL_ROUTINES
fixture_end:
    SAVEBIN "p828-cal-fixture.bin",fixture,fixture_end-fixture
""",encoding="utf-8",newline="\n")
    fr=run_command([tool,"--nologo","--lst=p828-cal-fixture.lst","--sym=p828-cal-fixture.sym",fix.name],cwd=b,timeout_seconds=30); require(not fr.timed_out and fr.exit_code==0,f"P8.28 fixture: {fr.stderr or fr.stdout}")
    gate=b/"p828-gateway.asm"; gate.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    ORG $E000
gate:
    cp SYS_TIME_GET
    jr z,g_time
    cp SYS_WRITE
    jr z,g_write
    cp SYS_EXIT
    jr z,g_exit
    ld a,E_NOTSUP
    scf
    ret
g_time:
    ld a,($A301)
    or a
    jr nz,g_again
    xor a
    ld (hl),a
    inc hl
    ld (hl),a
    inc hl
    ld (hl),a
    inc hl
    ld (hl),a
    inc hl
    ld (hl),a
    inc hl
    ld (hl),a
    ret
g_again:
    ld a,E_AGAIN
    scf
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
    SAVEBIN "p828-gateway.bin",gate,gate_end-gate
""",encoding="utf-8",newline="\n")
    gr=run_command([tool,"--nologo","--lst=p828-gateway.lst","--sym=p828-gateway.sym",gate.name],cwd=b,timeout_seconds=30); require(not gr.timed_out and gr.exit_code==0,f"P8.28 gateway: {gr.stderr or gr.stdout}")
    if action=="test":
        sy=phase3_open_descriptions._symbols(b/"p828-cal-fixture.sym",("cal_entry","E_INVAL","E_AGAIN"))
        ub=(b/"p828-cal-fixture.bin").read_bytes(); gb=(b/"p828-gateway.bin").read_bytes()
        cases=[
          ([b"cal"],0,b"1970-01\n",0),
          ([b"cal",b"2"],0,b"1970-02\n",0),
          ([b"cal",b"2",b"2024"],1,b"2024-02\n",0),
          ([b"cal"],1,b"cal: date not set\n",sy["E_AGAIN"]&255),
        ]
        for args,mode,prefix,status in cases:
            ab=arg1(args); code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._ld_hl(ARG)+b"\x01"+word(len(ab))+phase1._call(sy["cal_entry"]))
            for i,v in enumerate(prefix): code+=expect(OUT+i,v)
            code+=expect(STATUS,status)+phase1._jp(PASS_PC)
            try:\n                run_sna(root,bytes(code),patch=patch(ub,gb,args,mode),timeout=30)\n            except Exception as e:\n                raise P828Error(f"P8.28 case {args!r} failed: {e}")
        for args in ([b"cal",b"0"],[b"cal",b"13"],[b"cal",b"1",b"1969"],[b"cal",b"1",b"2100"],[b"cal",b"1",b"2024",b"x"]):
            ab=arg1(list(args)); code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._ld_hl(ARG)+b"\x01"+word(len(ab))+phase1._call(sy["cal_entry"])+expect(STATUS,sy["E_INVAL"]&255)+phase1._jp(PASS_PC))
            try:\n                run_sna(root,bytes(code),patch=patch(ub,gb,list(args),0),timeout=30)\n            except Exception as e:\n                raise P828Error(f"P8.28 invalid case {args!r} failed: {e}")
        assertions += [{"name":"fuse-current-month-year","passed":True},{"name":"fuse-two-arg-independent","passed":True},{"name":"fuse-invalid-wall-state","passed":True},{"name":"fuse-range-rejection","passed":True}]
    hashes={"v1/src/utils/cal.asm":sha256_file(root/"v1/src/utils/cal.asm"),"v1/build/p828-cal.mex1":sha256_file(mex),"v1/build/p828-cal.tap":sha256_file(tap),"v1/tools-host/test-driver/phase8_cal.py":sha256_file(root/"v1/tools-host/test-driver/phase8_cal.py"),"v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),"v1/dist/certification/P8.27.test.json":sha256_file(root/"v1/dist/certification/P8.27.test.json")}
    return [ir,xr,fr,gr],hashes,assertions
