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

import phase1, phase3_open_descriptions, phase7_udg_persistence
from driver_core import DriverError
from fuse_harness import FAIL_PC, PASS_PC, run_sna
from phase8_common import arg1, word, mex1, inspect_mex, make_tap

BASE=0xC000
GATE=0xE000
ARG=0xA000
OUT=0xA400
MODE=0xA3F0
STATUS=0xA3F1
GETS=0xA3F2

class P821Error(DriverError): pass

def require(v,m):
    if not v: raise P821Error(m)

def expect(addr,val):
    return b"\x3A"+word(addr)+bytes((0xFE,val&255))+phase1._jp_nz(FAIL_PC)

def patch(image,gate,args,mode=0):
    block=arg1(args)
    def apply(ram):
        ram[BASE-0x4000:BASE-0x4000+len(image)]=image
        ram[GATE-0x4000:GATE-0x4000+len(gate)]=gate
        ram[ARG-0x4000:ARG-0x4000+len(block)]=block
        ram[OUT-0x4000:OUT-0x4000+256]=b"\xA5"*256
        ram[MODE-0x4000]=mode
        ram[STATUS-0x4000]=0xFF
        ram[GETS-0x4000]=0
    return apply

def dispatch(root,action,step,*,sha256_file,run_command,require_project_tool):
    if step!="P8.21": raise DriverError(f"Phase-8 udg step is not registered: {step}")
    src=root/"v1/src/utils/udg.asm"
    s=src.read_text(encoding="utf-8")
    p=(root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md").read_text(encoding="utf-8")
    assertions=[
      {"name":"canonical-p821-present","passed":"## P8.21 - Utility `udg`" in p},
      {"name":"four-form-wrapper","passed":"MACRO EMIT_P821_UDG_ROUTINES" in s and all(x in s for x in ("udg_p821_list:","udg_p821_show:","udg_save_path:","udg_load_path:"))},
      {"name":"list-32-slots","passed":"cp UDG1_MAX_GLYPHS" in s.split("udg_p821_list:",1)[1]},
      {"name":"show-one-get","passed":"ld a,SYS_UDG_GET" in s.split("udg_p821_three:",1)[1].split("udg_p821_bad:",1)[0]},
      {"name":"save-full-bank","passed":"ld a,UDG1_MAX_GLYPHS" in s and "SYS_UDG_GET" in s},
      {"name":"load-validates-before-write","passed":s.index("udg_load_validate:") < s.index("udg_load_apply_loop:")},
      {"name":"no-cassette-motion","passed":"SYS_TAPE_" not in s},
      {"name":"short-write-safe","passed":"udg_p821_write_loop:" in s and "udg_p821_write_zero:" in s},
    ]
    require(all(x["passed"] for x in assertions),"P8.21 static contract failure")

    tool=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus")
    build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    ff=build/"p821-udg-fixture.asm"
    ff.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/utils/udg.asm"
    ORG $C000
fixture:
    EMIT_P821_UDG_ROUTINES
fixture_end:
    SAVEBIN "p821-udg-fixture.bin",fixture,fixture_end-fixture
""",encoding="utf-8",newline="\n")
    fr=run_command([tool,"--nologo","--lst=p821-udg-fixture.lst","--sym=p821-udg-fixture.sym",ff.name],cwd=build,timeout_seconds=30)
    require(not fr.timed_out and fr.exit_code==0,f"P8.21 fixture assembly failed: {fr.stderr or fr.stdout}")
    image=(build/"p821-udg-fixture.bin").read_bytes()
    require(256<=len(image)<4096,"P8.21 image size implausible")

    gf=build/"p821-gateway.asm"
    gf.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    ORG $E000
gate:
    cp SYS_WRITE
    jp z,g_write
    cp SYS_UDG_GET
    jp z,g_get
    cp SYS_EXIT
    jp z,g_exit
    ld a,E_NOTSUP
    scf
    ret
g_get:
    ld a,b
    or a
    jr nz,g_bad
    ld a,c
    cp 32
    jr nc,g_bad
    ld a,($A3F2)
    inc a
    ld ($A3F2),a
    ld a,c
    ld b,8
g_get_loop:
    ld (hl),a
    inc a
    inc hl
    djnz g_get_loop
    xor a
    ret
g_write:
    ld a,e
    cp 1
    jr nz,g_bad
    ld a,d
    or a
    jr nz,g_bad
    ld a,($A3F0)
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
    ld ($A3F1),a
    xor a
    ret
g_bad:
    ld a,E_INVAL
    scf
    ret
g_out: dw $A400
gate_end:
    SAVEBIN "p821-gateway.bin",gate,gate_end-gate
""",encoding="utf-8",newline="\n")
    gr=run_command([tool,"--nologo","--lst=p821-gateway.lst","--sym=p821-gateway.sym",gf.name],cwd=build,timeout_seconds=30)
    require(not gr.timed_out and gr.exit_code==0,f"P8.21 gateway assembly failed: {gr.stderr or gr.stdout}")

    mp=build/"p821-udg.mex1"; mp.write_bytes(mex1(image))
    try:
        xr=inspect_mex(root,mp,run_command,require_project_tool)
        tap=make_tap(root,build,"udg","p821",mp)
    except RuntimeError as e:
        raise P821Error(str(e))

    if action=="test":
        sy=phase3_open_descriptions._symbols(build/"p821-udg-fixture.sym",("udg_p821_entry","E_INVAL"))
        gb=(build/"p821-gateway.bin").read_bytes()
        cases=[]
        expected_list=b"".join(str(i).encode()+b"\n" for i in range(32))
        cases.append(([b"udg",b"list"],0,expected_list,0,0))
        cases.append(([b"udg",b"list"],1,expected_list,0,0))
        cases.append(([b"udg",b"show",b"7"],0,b"7: 0708090A0B0C0D0E\n",0,1))
        for args,mode,want,status,gets in cases:
            block=arg1(args)
            code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._ld_hl(ARG)+b"\x01"+word(len(block))+phase1._call(sy["udg_p821_entry"]))
            for i,v in enumerate(want): code+=expect(OUT+i,v)
            code+=expect(OUT+len(want),0xA5)+expect(STATUS,status)+expect(GETS,gets)+phase1._jp(PASS_PC)
            run_sna(root,bytes(code),patch=patch(image,gb,args,mode))
        for args in ([b"udg",b"List"],[b"udg",b"show",b"32"],[b"udg",b"show",b"-1"],[b"udg"]):
            block=arg1(list(args))
            code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._ld_hl(ARG)+b"\x01"+word(len(block))+phase1._call(sy["udg_p821_entry"]))
            code+=expect(STATUS,sy["E_INVAL"]&255)+expect(GETS,0)+expect(OUT,0xA5)+phase1._jp(PASS_PC)
            run_sna(root,bytes(code),patch=patch(image,gb,list(args)))

        # Re-run the certified P7.16 persistence corpus against the evolved source.
        ur,ug,ub,us,ugb,ugs=phase7_udg_persistence.assemble(root,run_command,require_project_tool)
        un=phase7_udg_persistence.symbols(us,("udg_save_path","udg_load_path","udg_entry"))
        gn=phase7_udg_persistence.symbols(ugs,("p716_force_open","p716_force_write","p716_force_read","p716_force_rename","p716_create_type","p716_create_flags","p716_committed","p716_remove_calls","p716_tape_motion","p716_define_calls","p716_exit_status","p716_load_type","p716_load_flags","p716_load_state","p716_staged_len","p716_load_len","OBJ_UDG","OBJ_PACKED","O_WRITE","O_CREATE","O_EXCL","E_IO","E_FORMAT"))
        phase7_udg_persistence.runtime(root,un,gn,ub.read_bytes(),ugb.read_bytes())
        assertions += [
          {"name":"fuse-list-all-32","passed":True},
          {"name":"fuse-show-exact-one-slot","passed":True},
          {"name":"fuse-list-short-write","passed":True},
          {"name":"fuse-invalid-case-range","passed":True},
          {"name":"fuse-save-load-regression","passed":True},
        ]

    hashes={
      "v1/src/utils/udg.asm":sha256_file(src),
      "v1/build/p821-udg.mex1":sha256_file(mp),
      "v1/build/p821-udg.tap":sha256_file(tap),
      "v1/tools-host/test-driver/phase8_udg.py":sha256_file(root/"v1/tools-host/test-driver/phase8_udg.py"),
      "v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
      "v1/dist/certification/P8.20.test.json":sha256_file(root/"v1/dist/certification/P8.20.test.json"),
    }
    return [fr,gr,xr],hashes,assertions
