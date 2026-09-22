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

BASE=0xC000; GATE=0xE000; ARG=0xA000; STATUS=0xA200; CALLS=0xA210; MODE=0xA220
class P822Error(DriverError): pass
def require(v,m):
    if not v: raise P822Error(m)
def expect(a,v): return b"\x3A"+word(a)+bytes((0xFE,v&255))+phase1._jp_nz(FAIL_PC)

def patch(image,gate,mode=0):
    block=arg1([b"gfxdemo"])
    def apply(ram):
        ram[BASE-0x4000:BASE-0x4000+len(image)]=image
        ram[GATE-0x4000:GATE-0x4000+len(gate)]=gate
        ram[ARG-0x4000:ARG-0x4000+len(block)]=block
        ram[STATUS-0x4000]=0xFF
        ram[CALLS-0x4000:CALLS-0x4000+8]=b"\0"*8
        ram[MODE-0x4000]=mode
    return apply

def dispatch(root,action,step,*,sha256_file,run_command,require_project_tool):
    if step!="P8.22": raise DriverError(step)
    src=root/"v1/src/utils/gfxdemo.asm"
    s=src.read_text(encoding="utf-8")
    p=(root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md").read_text(encoding="utf-8")
    assertions=[
      {"name":"canonical-p822-present","passed":"## P8.22 - Utility `gfxdemo`" in p},
      {"name":"external-gfxdemo-source","passed":"MACRO EMIT_P822_GFXDEMO_ROUTINES" in s},
      {"name":"six-graphics-apis","passed":all(x in s for x in ("SYS_GFX_PLOT","SYS_GFX_DRAW","SYS_GFX_CIRCLE","SYS_GFX_ATTR","SYS_GFX_BORDER","SYS_GFX_POINT"))},
      {"name":"exact-one-argument","passed":"cp 1" in s and "E_INVAL" in s},
      {"name":"error-propagation","passed":"gfxdemo_exit_error:" in s},
      {"name":"no-case-folding","passed":"casefold" not in s.lower()},
    ]
    require(all(x["passed"] for x in assertions),"P8.22 static failure")
    tool=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus")
    b=root/"v1/build"; b.mkdir(parents=True,exist_ok=True)
    f=b/"p822-gfxdemo.asm"
    f.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/utils/gfxdemo.asm"
    ORG $C000
fixture:
    EMIT_P822_GFXDEMO_ROUTINES
fixture_end:
    SAVEBIN "p822-gfxdemo.bin",fixture,fixture_end-fixture
""",encoding="utf-8",newline="\n")
    fr=run_command([tool,"--nologo","--lst=p822-gfxdemo.lst","--sym=p822-gfxdemo.sym",f.name],cwd=b,timeout_seconds=30)
    require(not fr.timed_out and fr.exit_code==0,f"P8.22 assemble: {fr.stderr or fr.stdout}")
    image=(b/"p822-gfxdemo.bin").read_bytes()
    g=b/"p822-gateway.asm"
    g.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    ORG $E000
gate:
    cp SYS_GFX_PLOT
    jp z,g_plot
    cp SYS_GFX_DRAW
    jp z,g_draw
    cp SYS_GFX_CIRCLE
    jp z,g_circle
    cp SYS_GFX_ATTR
    jp z,g_attr
    cp SYS_GFX_BORDER
    jp z,g_border
    cp SYS_GFX_POINT
    jp z,g_point
    cp SYS_EXIT
    jp z,g_exit
    ld a,E_NOTSUP
    scf
    ret
g_plot: ld hl,$0000 : jr g_call
g_draw: ld hl,$0001 : jr g_call
g_circle: ld hl,$0002 : jr g_call
g_attr: ld hl,$0003 : jr g_call
g_border: ld hl,$0004 : jr g_call
g_point: ld hl,$0005
g_call:
    push hl
    ld de,$A210
    add hl,de
    inc (hl)
    pop hl
    ld a,($A220)
    cp l
    jr z,g_fail
    xor a
    ret
g_fail:
    ld a,E_IO
    scf
    ret
g_exit:
    ld a,l
    ld ($A200),a
    xor a
    ret
gate_end:
    SAVEBIN "p822-gateway.bin",gate,gate_end-gate
""",encoding="utf-8",newline="\n")
    gr=run_command([tool,"--nologo","--lst=p822-gateway.lst","--sym=p822-gateway.sym",g.name],cwd=b,timeout_seconds=30)
    require(not gr.timed_out and gr.exit_code==0,f"P8.22 gateway: {gr.stderr or gr.stdout}")
    mp=b/"p822-gfxdemo.mex1"; mp.write_bytes(mex1(image))
    try:
        xr=inspect_mex(root,mp,run_command,require_project_tool); tap=make_tap(root,b,"gfxdemo","p822",mp)
    except RuntimeError as e: raise P822Error(str(e))
    if action=="test":
        sy=phase3_open_descriptions._symbols(b/"p822-gfxdemo.sym",("gfxdemo_entry","E_IO","E_INVAL"))
        gb=(b/"p822-gateway.bin").read_bytes(); block=arg1([b"gfxdemo"])
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._ld_hl(ARG)+b"\x01"+word(len(block))+phase1._call(sy["gfxdemo_entry"]))
        code+=expect(STATUS,0)
        for i in range(6): code+=expect(CALLS+i,1)
        code+=phase1._jp(PASS_PC)
        run_sna(root,bytes(code),patch=patch(image,gb,255))
        for fail in range(6):
            code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._ld_hl(ARG)+b"\x01"+word(len(block))+phase1._call(sy["gfxdemo_entry"]))
            code+=expect(STATUS,sy["E_IO"]&255)+phase1._jp(PASS_PC)
            run_sna(root,bytes(code),patch=patch(image,gb,fail))
        assertions += [{"name":"fuse-six-graphics-calls","passed":True},{"name":"fuse-error-propagation","passed":True}]
    hashes={
      "v1/src/utils/gfxdemo.asm":sha256_file(src),
      "v1/build/p822-gfxdemo.mex1":sha256_file(mp),
      "v1/build/p822-gfxdemo.tap":sha256_file(tap),
      "v1/tools-host/test-driver/phase8_gfxdemo.py":sha256_file(root/"v1/tools-host/test-driver/phase8_gfxdemo.py"),
      "v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
      "v1/dist/certification/P8.21.test.json":sha256_file(root/"v1/dist/certification/P8.21.test.json"),
    }
    return [fr,gr,xr],hashes,assertions
