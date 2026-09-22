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
UTIL=0xC000; GATE=0xE000; ARG=0xA000; STATUS=0xA300; COUNT=0xA301; MAXX=0xA302; MINY=0xA303; MAXY=0xA304
class P833Error(DriverError):
    pass
def require(v,m):
    if not v: raise P833Error(m)
def expect(a,v): return b"\x3A"+word(a)+bytes((0xFE,v&255))+phase1._jp_nz(FAIL_PC)
def patch(util,gate,args):
    ab=arg1(args)
    def apply(ram):
        ram[UTIL-0x4000:UTIL-0x4000+len(util)]=util
        ram[GATE-0x4000:GATE-0x4000+len(gate)]=gate
        ram[ARG-0x4000:ARG-0x4000+len(ab)]=ab
        ram[STATUS-0x4000]=0xFF; ram[COUNT-0x4000]=0; ram[MAXX-0x4000]=0; ram[MINY-0x4000]=0xFF; ram[MAXY-0x4000]=0
    return apply
def dispatch(root,action,step,*,sha256_file,run_command,require_project_tool):
    if step!="P8.33": raise DriverError(step)
    s=(root/"v1/src/utils/banner.asm").read_text(encoding="utf-8")
    p=(root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md").read_text(encoding="utf-8")
    assertions=[
      {"name":"canonical-p833-present","passed":"## P8.33 - Utility `banner`" in p},
      {"name":"rom-font","passed":"$3D00" in s and "ASCII 32..127" in s},
      {"name":"shared-pixel-api","passed":"SYS_GFX_PLOT" in s},
      {"name":"screen-width-bound","passed":"cp 33" in s and "E_TOOLONG" in s},
      {"name":"arity","passed":"cp 2" in s and "E_INVAL" in s},
    ]
    require(all(x["passed"] for x in assertions),"P8.33 static contract failure")
    tool=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus"); b=root/"v1/build"; b.mkdir(parents=True,exist_ok=True)
    try:
        ir,image,mex=assemble_utility(root,b,tool,"banner","p833","EMIT_P833_BANNER_ROUTINES",run_command)
        xr=inspect_mex(root,mex,run_command,require_project_tool); tap=make_tap(root,b,"banner","p833",mex)
    except RuntimeError as e: raise P833Error(str(e))
    fix=b/"p833-banner-fixture.asm"; fix.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/utils/banner.asm"
    ORG $C000
fixture:
    EMIT_P833_BANNER_ROUTINES
fixture_end:
    SAVEBIN "p833-banner-fixture.bin",fixture,fixture_end-fixture
""",encoding="utf-8",newline="\n")
    fr=run_command([tool,"--nologo","--lst=p833-banner-fixture.lst","--sym=p833-banner-fixture.sym",fix.name],cwd=b,timeout_seconds=30); require(not fr.timed_out and fr.exit_code==0,f"P8.33 fixture: {fr.stderr or fr.stdout}")
    gate=b/"p833-gateway.asm"; gate.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    ORG $E000
gate:
    cp SYS_GFX_PLOT
    jr z,g_plot
    cp SYS_EXIT
    jr z,g_exit
    ld a,E_NOTSUP
    scf
    ret
g_plot:
    ld a,l
    cp 192
    jr nc,g_bad
    cp 8
    jr c,g_bad
    cp 16
    jr nc,g_bad
    ld a,h
    ld b,a
    ld a,($A302)
    cp b
    jr nc,g_no_maxx
    ld a,b
    ld ($A302),a
g_no_maxx:
    ld a,l
    ld b,a
    ld a,($A303)
    cp b
    jr c,g_no_miny
    jr z,g_no_miny
    ld a,b
    ld ($A303),a
g_no_miny:
    ld a,l
    ld b,a
    ld a,($A304)
    cp b
    jr nc,g_no_maxy
    ld a,b
    ld ($A304),a
g_no_maxy:
    ld a,($A301)
    inc a
    ld ($A301),a
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
gate_end:
    SAVEBIN "p833-gateway.bin",gate,gate_end-gate
""",encoding="utf-8",newline="\n")
    gr=run_command([tool,"--nologo","--lst=p833-gateway.lst","--sym=p833-gateway.sym",gate.name],cwd=b,timeout_seconds=30); require(not gr.timed_out and gr.exit_code==0,f"P8.33 gateway: {gr.stderr or gr.stdout}")
    if action=="test":
        sy=phase3_open_descriptions._symbols(b/"p833-banner-fixture.sym",("banner_entry","E_INVAL","E_TOOLONG"))
        ub=(b/"p833-banner-fixture.bin").read_bytes(); gb=(b/"p833-gateway.bin").read_bytes()
        args=[b"banner",b"A"]; ab=arg1(args); code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._ld_hl(ARG)+b"\x01"+word(len(ab))+phase1._call(sy["banner_entry"]))
        code+=expect(STATUS,0)+b"\x3A"+word(COUNT)+b"\xB7"+phase1._jp_z(FAIL_PC)+b"\x3A"+word(MAXX)+bytes((0xFE,8))+phase1._jp_nc(FAIL_PC)+expect(MINY,8)+b"\x3A"+word(MAXY)+bytes((0xFE,16))+phase1._jp_nc(FAIL_PC)+phase1._jp(PASS_PC)
        run_sna(root,bytes(code),patch=patch(ub,gb,args),timeout=30)
        for args,status in (([b"banner"],sy["E_INVAL"]&255),([b"banner",b"x"*33],sy["E_TOOLONG"]&255),([b"banner",b"\x01"],sy["E_INVAL"]&255)):
            ab=arg1(args); code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._ld_hl(ARG)+b"\x01"+word(len(ab))+phase1._call(sy["banner_entry"])+expect(STATUS,status)+expect(COUNT,0)+phase1._jp(PASS_PC)); run_sna(root,bytes(code),patch=patch(ub,gb,args),timeout=30)
        assertions += [{"name":"fuse-rom-glyph-bounds","passed":True},{"name":"fuse-overlength","passed":True},{"name":"fuse-invalid-byte","passed":True}]
    hashes={"v1/src/utils/banner.asm":sha256_file(root/"v1/src/utils/banner.asm"),"v1/build/p833-banner.mex1":sha256_file(mex),"v1/build/p833-banner.tap":sha256_file(tap),"v1/tools-host/test-driver/phase8_banner.py":sha256_file(root/"v1/tools-host/test-driver/phase8_banner.py"),"v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),"v1/dist/certification/P8.32.test.json":sha256_file(root/"v1/dist/certification/P8.32.test.json")}
    return [ir,xr,fr,gr],hashes,assertions
