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
from phase8_common import word, mex1, make_tap, inspect_mex

BASE=0xC000
GATE=0xE000
OUT=0xA400
ARG=0xA2E0
MODE=0xA2F0

class P820Error(DriverError):
    pass

def require(v,m):
    if not v:
        raise P820Error(m)

def expect(addr,val):
    return b"\x3A"+word(addr)+bytes((0xFE,val&255))+phase1._jp_nz(FAIL_PC)

def patch(module,gate,mode,arg=b""):
    def apply(ram):
        ram[BASE-0x4000:BASE-0x4000+len(module)]=module
        ram[GATE-0x4000:GATE-0x4000+len(gate)]=gate
        ram[OUT-0x4000:OUT-0x4000+768]=b"\xA5"*768
        ram[MODE-0x4000]=mode
        ram[ARG-0x4000:ARG-0x4000+len(arg)]=arg
    return apply

def dispatch(root,action,step,*,sha256_file,run_command,require_project_tool):
    if step!="P8.20":
        raise DriverError(f"Phase-8 mem step is not registered: {step}")
    sp=root/"v1/src/shell/sh.asm"
    s=sp.read_text()
    p=(root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md").read_text()
    assertions=[
      {"name":"canonical-p820-present","passed":"## P8.20 - Built-in `mem` Phase-8 regression" in p},
      {"name":"mem-remains-p613-builtin","passed":"db 3,'m','e','m',P613_BUILTIN_MEM" in s},
      {"name":"no-external-mem-module","passed":not (root/"v1/src/utils/mem.asm").exists()},
      {"name":"public-memory-accounting","passed":all(x in s.split("MACRO EMIT_P820_MEM_ROUTINES",1)[1] for x in ("SYS_MEM_INFO","SYS_ZXPACK_INFO","SYS_PROC_INFO"))},
      {"name":"fast-contended-largest","passed":all(x in s for x in ("p820_s_fast_largest","p820_s_contended_largest"))},
      {"name":"process-object-pipe-pinned","passed":all(x in s for x in ("p820_s_process","p820_s_object","p820_s_pipe","p820_s_pinned"))},
      {"name":"compression-accounting","passed":all(x in s for x in ("p820_s_logical","p820_s_saved","p820_s_raw","p820_s_packed","p820_s_decoder","p820_s_attempts","p820_s_successes"))},
      {"name":"single-foreground-only","passed":"sh_p820_notsup:" in s},
      {"name":"stdout-short-write-safe","passed":"sh_p820_write_loop:" in s and "sh_p820_write_zero:" in s},
    ]
    require(all(x["passed"] for x in assertions),"P8.20 static contract failure")

    tool=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus")
    build=root/"v1/build"
    build.mkdir(parents=True,exist_ok=True)
    fixture=build/"p820-mem-fixture.asm"
    fixture.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/shell/sh.asm"
    ORG $C000
fixture:
    EMIT_P613_BUILTIN_ROUTINES
    EMIT_P820_MEM_ROUTINES
fixture_end:
    SAVEBIN "p820-mem-fixture.bin",fixture,fixture_end-fixture
""",newline="\n")
    fr=run_command([tool,"--nologo","--lst=p820-mem-fixture.lst","--sym=p820-mem-fixture.sym","p820-mem-fixture.asm"],cwd=build,timeout_seconds=30)
    require(not fr.timed_out and fr.exit_code==0,f"P8.20 fixture assembly failed: {fr.stderr or fr.stdout}")
    image=(build/"p820-mem-fixture.bin").read_bytes()
    require(256<=len(image)<8192,"P8.20 image size implausible")

    gate=build/"p820-gateway.asm"
    gate.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    ORG $E000
gate:
    cp SYS_MEM_INFO
    jp z,g_mem
    cp SYS_ZXPACK_INFO
    jp z,g_zp
    cp SYS_PROC_INFO
    jp z,g_proc
    cp SYS_WRITE
    jp z,g_write
    ld a,E_NOTSUP
    scf
    ret
g_mem:
    ld a,($A2F0)
    cp 2
    jr z,g_io
    ex de,hl
    ld hl,mem_data
    ld bc,16
    ldir
    xor a
    ret
g_zp:
    ld a,($A2F0)
    cp 4
    jr z,g_io
    ex de,hl
    ld hl,zp_data
    ld bc,20
    ldir
    xor a
    ret
g_proc:
    ld a,(hl)
    ld ($A2F1),a
    ld a,($A2F0)
    cp 3
    jr nz,g_proc_continue
    ld a,($A2F1)
    cp 1
    jr z,g_io
g_proc_continue:
    inc hl
    inc hl
    ld e,(hl)
    inc hl
    ld d,(hl)
    push de
    ld a,($A2F1)
    or a
    jr z,g_proc0
    cp 1
    jr z,g_proc1
    pop de
    ld a,E_NOENT
    scf
    ret
g_proc0:
    ld hl,proc0
    jr g_proc_copy
g_proc1:
    ld hl,proc1
g_proc_copy:
    pop de
    ld bc,16
    ldir
    xor a
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
    jr nz,g_two
    ld a,c
    cp 4
    jr c,g_write_all
g_two:
    ld bc,3
g_write_all:
    push bc
    ld de,(g_out)
    ldir
    ld (g_out),de
    pop hl
    xor a
    ret
g_io:
    ld a,E_IO
    scf
    ret
g_bad:
    ld a,E_INVAL
    scf
    ret
mem_data:
    dw 17000,9000,10000,6000,27000,7,500
    db 2,0
zp_data:
    db $70,$11,$01,$00
    dw 1500
    db $94,$0B,$01,$00
    db 2,1
    dw 272,9,7,0
proc0:
    db 0,$ff,1,0
    db 'i','d','l','e',0,0,0,0,0,0
    dw 1000
proc1:
    db 1,0,2,0
    db 's','h',0,0,0,0,0,0,0,0
    dw 2000
g_out: dw $A400
gate_end:
    SAVEBIN "p820-gateway.bin",gate,gate_end-gate
""",newline="\n")
    gr=run_command([tool,"--nologo","--lst=p820-gateway.lst","--sym=p820-gateway.sym","p820-gateway.asm"],cwd=build,timeout_seconds=30)
    require(not gr.timed_out and gr.exit_code==0,f"P8.20 gateway assembly failed: {gr.stderr or gr.stdout}")

    mp=build/"p820-mem.mex1"
    mp.write_bytes(mex1(image))
    try:
        xr=inspect_mex(root,mp,run_command,require_project_tool)
        tap=make_tap(root,build,"mem-builtin","p820",mp)
    except RuntimeError as e:
        raise P820Error(str(e))

    if action=="test":
        sy=phase3_open_descriptions._symbols(
            build/"p820-mem-fixture.sym",
            ("sh_p820_mem_builtin","E_INVAL","E_NOTSUP","E_IO"),
        )
        gb=(build/"p820-gateway.bin").read_bytes()
        normal=(
            b"arena_used 5768\n"
            b"total_free 27000\n"
            b"fast_free 17000\n"
            b"fast_largest 9000\n"
            b"contended_free 10000\n"
            b"contended_largest 6000\n"
            b"process_bytes 3000\n"
            b"object_physical 1500\n"
            b"pipe_bytes 496\n"
            b"pinned_bytes 500\n"
        )
        detail=normal+(
            b"logical_object_bytes 0x00011170\n"
            b"physical_object_bytes 1500\n"
            b"bytes_saved 0x00010B94\n"
            b"raw_objects 1\n"
            b"packed_objects 2\n"
            b"decoder_state_bytes 272\n"
            b"pack_attempts 9\n"
            b"pack_successes 7\n"
        )
        for mode,argc,arg,expected in ((0,1,b"",normal),(1,2,b"-c\0",detail)):
            hl=ARG if argc==2 else 0
            code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+bytes((0x3E,argc,0x06,1,0x0E,0))+phase1._ld_hl(hl)+phase1._call(sy["sh_p820_mem_builtin"])+phase1._jp_c(FAIL_PC))
            for o,v in enumerate(expected):
                code+=expect(OUT+o,v)
            code+=expect(OUT+len(expected),0xA5)+phase1._jp(PASS_PC)
            run_sna(root,bytes(code),patch=patch(image,gb,mode,arg))

        for mode,err in ((2,sy["E_IO"]&255),(3,sy["E_IO"]&255),(4,sy["E_IO"]&255)):
            code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+bytes((0x3E,1,0x06,1,0x0E,0))+phase1._ld_hl(0)+phase1._call(sy["sh_p820_mem_builtin"])+b"\xD2"+word(FAIL_PC)+bytes((0xFE,err))+phase1._jp_nz(FAIL_PC)+phase1._jp(PASS_PC))
            run_sna(root,bytes(code),patch=patch(image,gb,mode))

        for argc,stages,bg,arg,err in (
            (3,1,0,b"",sy["E_INVAL"]&255),
            (2,1,0,b"-x\0",sy["E_INVAL"]&255),
            (1,2,0,b"",sy["E_NOTSUP"]&255),
            (1,1,1,b"",sy["E_NOTSUP"]&255),
        ):
            hl=ARG if arg else 0
            code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+bytes((0x3E,argc,0x06,stages,0x0E,bg))+phase1._ld_hl(hl)+phase1._call(sy["sh_p820_mem_builtin"])+b"\xD2"+word(FAIL_PC)+bytes((0xFE,err))+phase1._jp_nz(FAIL_PC)+phase1._jp(PASS_PC))
            run_sna(root,bytes(code),patch=patch(image,gb,0,arg))
        assertions += [
            {"name":"fuse-normal-memory-report","passed":True},
            {"name":"fuse-compression-detail-report","passed":True},
            {"name":"fuse-short-write-retried","passed":True},
            {"name":"fuse-accounting-errors-propagate","passed":True},
            {"name":"fuse-builtin-context-errors","passed":True},
        ]

    hashes={
        "v1/src/shell/sh.asm":sha256_file(sp),
        "v1/build/p820-mem.mex1":sha256_file(mp),
        "v1/build/p820-mem-builtin.tap":sha256_file(tap),
        "v1/tools-host/test-driver/phase8_mem.py":sha256_file(root/"v1/tools-host/test-driver/phase8_mem.py"),
        "v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
        "v1/dist/certification/P8.19.test.json":sha256_file(root/"v1/dist/certification/P8.19.test.json"),
    }
    return [fr,gr,xr],hashes,assertions
