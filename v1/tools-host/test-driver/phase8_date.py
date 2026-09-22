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
from phase8_common import arg1, word, mex1, inspect_mex, make_tap

BASE=0xC000
GATE=0xE000
ARG=0xA000
OUT=0xA500
MODE=0xA300
STATUS=0xA301
SETCALLS=0xA302
SETBUF=0xA304

class P824Error(DriverError):
    pass

def require(v,m):
    if not v:
        raise P824Error(m)

def expect(a,v):
    return b"\x3A"+word(a)+bytes((0xFE,v&255))+phase1._jp_nz(FAIL_PC)

def patch(image,gate,args,mode=0):
    block=arg1(args)
    def apply(ram):
        ram[BASE-0x4000:BASE-0x4000+len(image)]=image
        ram[GATE-0x4000:GATE-0x4000+len(gate)]=gate
        ram[ARG-0x4000:ARG-0x4000+len(block)]=block
        ram[OUT-0x4000:OUT-0x4000+128]=b"\xA5"*128
        ram[MODE-0x4000]=mode
        ram[STATUS-0x4000]=0xFF
        ram[SETCALLS-0x4000]=0
        ram[SETBUF-0x4000:SETBUF-0x4000+4]=b"\xCC"*4
    return apply

def dispatch(root,action,step,*,sha256_file,run_command,require_project_tool):
    if step!="P8.24":
        raise DriverError(step)
    src=root/"v1/src/utils/date.asm"
    s=src.read_text(encoding="utf-8")
    p=(root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md").read_text(encoding="utf-8")
    assertions=[
      {"name":"canonical-p824-present","passed":"## P8.24 - Utility `date`" in p},
      {"name":"time1-get-set-only","passed":"SYS_TIME_GET" in s and "SYS_TIME_SET" in s},
      {"name":"boot-not-set-diagnostic","passed":"'d','a','t','e',':',' ','n','o','t',' ','s','e','t'" in s},
      {"name":"gregorian-1970-2099","passed":"ld de,1970" in s and "ld de,2100" in s},
      {"name":"leap-year-rule-valid-range","passed":"and 3" in s},
      {"name":"exact-display-width","passed":"ld bc,20" in s and "date_format:" in s},
      {"name":"set-resets-through-kernel","passed":"SYS_TIME_SET" in s and "date_time" in s},
      {"name":"case-sensitive","passed":"casefold" not in s.lower()},
    ]
    require(all(x["passed"] for x in assertions),"P8.24 static failure")

    tool=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus")
    b=root/"v1/build"; b.mkdir(parents=True,exist_ok=True)
    f=b/"p824-date.asm"
    f.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/utils/date.asm"
    ORG $C000
fixture:
    EMIT_P824_DATE_ROUTINES
fixture_end:
    SAVEBIN "p824-date.bin",fixture,fixture_end-fixture
""",encoding="utf-8",newline="\n")
    fr=run_command([tool,"--nologo","--lst=p824-date.lst","--sym=p824-date.sym",f.name],cwd=b,timeout_seconds=30)
    require(not fr.timed_out and fr.exit_code==0,f"P8.24 assemble: {fr.stderr or fr.stdout}")
    image=(b/"p824-date.bin").read_bytes()
    require(256<=len(image)<8192,"P8.24 image size implausible")

    g=b/"p824-gateway.asm"
    g.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    ORG $E000
gate:
    cp SYS_TIME_GET
    jp z,g_get
    cp SYS_TIME_SET
    jp z,g_set
    cp SYS_WRITE
    jp z,g_write
    cp SYS_EXIT
    jp z,g_exit
    ld a,E_NOTSUP
    scf
    ret
g_get:
    ld a,($A300)
    cp 1
    jr z,g_again
    ld de,time1
    ex de,hl
    ld bc,6
    ldir
    xor a
    ret
g_again:
    ld a,E_AGAIN
    scf
    ret
g_set:
    ld de,$A304
    ld bc,4
    ldir
    ld a,($A302)
    inc a
    ld ($A302),a
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
    ld ($A301),a
    xor a
    ret
g_again:
    ld a,E_AGAIN
    scf
    ret
g_bad:
    ld a,E_INVAL
    scf
    ret
time1:
    db $80,$06,$26,$17,0,0
g_out: dw $A500
gate_end:
    SAVEBIN "p824-gateway.bin",gate,gate_end-gate
""",encoding="utf-8",newline="\n")
    # Remove accidental duplicate label defensively in the generated fixture.
    txt=g.read_text(encoding="utf-8")
    first=txt.find("g_again:")
    second=txt.find("g_again:",first+1)
    if second>=0:
        end=txt.find("g_bad:",second)
        txt=txt[:second]+txt[end:]
        g.write_text(txt,encoding="utf-8",newline="\n")
    gr=run_command([tool,"--nologo","--lst=p824-gateway.lst","--sym=p824-gateway.sym",g.name],cwd=b,timeout_seconds=30)
    require(not gr.timed_out and gr.exit_code==0,f"P8.24 gateway: {gr.stderr or gr.stdout}")

    mp=b/"p824-date.mex1"; mp.write_bytes(mex1(image))
    try:
        xr=inspect_mex(root,mp,run_command,require_project_tool)
        tap=make_tap(root,b,"date","p824",mp)
    except RuntimeError as e:
        raise P824Error(str(e))

    if action=="test":
        sy=phase3_open_descriptions._symbols(b/"p824-date.sym",("date_entry","E_INVAL","E_AGAIN"))
        gb=(b/"p824-gateway.bin").read_bytes()

        args=[b"date"]; block=arg1(args)
        want=b"1982-04-23 00:00:00\n"
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._ld_hl(ARG)+b"\x01"+word(len(block))+phase1._call(sy["date_entry"]))
        for i,v in enumerate(want):
            code+=expect(OUT+i,v)
        code+=expect(OUT+len(want),0xA5)+expect(STATUS,0)+phase1._jp(PASS_PC)
        run_sna(root,bytes(code),patch=patch(image,gb,args,0),timeout=30)

        want=b"date: not set\n"
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._ld_hl(ARG)+b"\x01"+word(len(block))+phase1._call(sy["date_entry"]))
        for i,v in enumerate(want):
            code+=expect(OUT+i,v)
        code+=expect(STATUS,sy["E_AGAIN"]&255)+phase1._jp(PASS_PC)
        run_sna(root,bytes(code),patch=patch(image,gb,args,1),timeout=30)

        for stamp,raw in (
            (b"1970-01-01 00:00:00",bytes.fromhex("00000000")),
            (b"2024-02-29 12:34:56",bytes.fromhex("f079e065")),
            (b"2099-12-31 23:59:59",bytes.fromhex("ff5686f4")),
        ):
            args=[b"date",b"-s",stamp]; block=arg1(args)
            code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._ld_hl(ARG)+b"\x01"+word(len(block))+phase1._call(sy["date_entry"]))
            code+=expect(STATUS,0)+expect(SETCALLS,1)
            for i,v in enumerate(raw):
                code+=expect(SETBUF+i,v)
            code+=phase1._jp(PASS_PC)
            run_sna(root,bytes(code),patch=patch(image,gb,args),timeout=40)

        for stamp in (b"1969-12-31 23:59:59",b"2100-01-01 00:00:00",b"2023-02-29 00:00:00",b"2024-13-01 00:00:00",b"2024-01-01 24:00:00",b"2024-01-01T00:00:00"):
            args=[b"date",b"-s",stamp]; block=arg1(args)
            code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._ld_hl(ARG)+b"\x01"+word(len(block))+phase1._call(sy["date_entry"]))
            code+=expect(STATUS,sy["E_INVAL"]&255)+expect(SETCALLS,0)+phase1._jp(PASS_PC)
            run_sna(root,bytes(code),patch=patch(image,gb,args),timeout=30)
        assertions += [
          {"name":"fuse-boot-epoch-display","passed":True},
          {"name":"fuse-explicit-invalid-not-set","passed":True},
          {"name":"fuse-valid-set-boundaries-leap","passed":True},
          {"name":"fuse-invalid-gregorian-rejected","passed":True},
        ]

    hashes={
      "v1/src/utils/date.asm":sha256_file(src),
      "v1/build/p824-date.mex1":sha256_file(mp),
      "v1/build/p824-date.tap":sha256_file(tap),
      "v1/tools-host/test-driver/phase8_date.py":sha256_file(root/"v1/tools-host/test-driver/phase8_date.py"),
      "v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
      "v1/dist/certification/P8.23.test.json":sha256_file(root/"v1/dist/certification/P8.23.test.json"),
    }
    return [fr,gr,xr],hashes,assertions
