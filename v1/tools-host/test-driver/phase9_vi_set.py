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
from phase8_common import inspect_mex, make_tap, mex1, word

BASE=0xC000; GATE=0xE000; ARG=0xA300; ROW=0xA340; COL=0xA341; OUT=0xA360
# Exact P9.21 candidate.

class P921Error(DriverError): pass

def require(v,m):
    if not v: raise P921Error(m)

def expect_byte(a,v):
    return b"\x3A"+word(a)+bytes((0xFE,v&255))+phase1._jp_nz(FAIL_PC)

def patch(image,gate,sy,arg=b"",number=0):
    def apply(ram):
        ram[BASE-0x4000:BASE-0x4000+len(image)]=image
        ram[GATE-0x4000:GATE-0x4000+len(gate)]=gate
        ram[ARG-0x4000:ARG-0x4000+len(arg)]=arg
        ram[ROW-0x4000]=0; ram[COL-0x4000]=0
        ram[OUT-0x4000:OUT-0x4000+16]=b"?"*16
        ram[sy["vi_buffer"]-0x4000:sy["vi_buffer"]-0x4000+4]=b"ABCD"
        ram[sy["vi_option_number"]-0x4000]=number
        ram[sy["vi_view_gutter"]-0x4000]=5 if number else 0
        ram[sy["vi_view_width"]-0x4000]=59 if number else 64
    return apply

def unchanged(sy):
    code=bytearray()
    for i,v in enumerate(b"ABCD"):
        code+=expect_byte(sy["vi_buffer"]+i,v)
    return bytes(code)

def dispatch(root,action,step,*,sha256_file,run_command,require_project_tool):
    if step!="P9.21": raise DriverError(step)
    source=root/"tools/vi.asm"; text=source.read_text(encoding="utf-8")
    plan=(root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md").read_text(encoding="utf-8")
    assertions=[
      {"name":"canonical-p921-present","passed":"## P9.21 - :set, :set number and :set nonumber" in plan},
      {"name":"exact-set-entry","passed":"vi_p921_set_cmd:" in text},
      {"name":"five-column-gutter","passed":"ld a,5\n    ld (vi_view_gutter),a" in text},
      {"name":"number-width-59","passed":"ld a,59\n    ld (vi_view_width),a" in text},
      {"name":"nonumber-width-64","passed":"ld a,64\n    ld (vi_view_width),a" in text},
      {"name":"exact-literals","passed":"vi_p921_number_word: db 'n','u','m','b','e','r'" in text and "vi_p921_nonumber_word: db 'n','o','n','u','m','b','e','r'" in text},
      {"name":"status-row-report","passed":"call vi_p905_status_pos" in text[text.index("vi_p921_report:"):]},
    ]
    require(all(x["passed"] for x in assertions),"P9.21 static contract failure")

    asm=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus")
    build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    fx=build/"p921-vi.asm"
    fx.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../../tools/vi.asm"
    ORG $C000
fixture:
    EMIT_P901_VI_ROUTINES
fixture_end:
    SAVEBIN "p921-vi.bin",fixture,fixture_end-fixture
""",encoding="utf-8",newline="\n")
    fr=run_command([asm,"--nologo","--lst=p921-vi.lst","--sym=p921-vi.sym",fx.name],cwd=build,timeout_seconds=30)
    require(not fr.timed_out and fr.exit_code==0,f"P9.21 assemble: {fr.stderr or fr.stdout}")
    image=(build/"p921-vi.bin").read_bytes()
    mex_path=build/"p921-vi.mex1"; mex_path.write_bytes(mex1(image))
    try:
        xr=inspect_mex(root,mex_path,run_command,require_project_tool); tap=make_tap(root,build,"vi","p921",mex_path)
    except RuntimeError as exc: raise P921Error(str(exc)) from exc

    gw=build/"p921-gateway.asm"
    gw.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    ORG $E000
gate:
    cp SYS_CON_SETPOS
    jp z,g_setpos
    cp SYS_CON_WRITE
    jp z,g_write
    ld a,E_NOTSUP
    scf
    ret
g_setpos:
    ld a,h
    ld ($A340),a
    ld a,l
    ld ($A341),a
    xor a
    ret
g_write:
    ld de,$A360
    ldir
    xor a
    ret
gate_end:
    SAVEBIN "p921-gateway.bin",gate,gate_end-gate
""",encoding="utf-8",newline="\n")
    gr=run_command([asm,"--nologo","--lst=p921-gateway.lst","--sym=p921-gateway.sym",gw.name],cwd=build,timeout_seconds=30)
    require(not gr.timed_out and gr.exit_code==0,f"P9.21 gateway: {gr.stderr or gr.stdout}")

    if action=="test":
        sy=phase3_open_descriptions._symbols(build/"p921-vi.sym",(
          "vi_p921_set_cmd","vi_option_number","vi_view_gutter","vi_view_width","vi_buffer","E_INVAL",
        ))
        gate=(build/"p921-gateway.bin").read_bytes()

        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._ld_hl(ARG)+b"\x01\x06\x00"+phase1._call(sy["vi_p921_set_cmd"])+phase1._jp_c(FAIL_PC))
        code+=expect_byte(sy["vi_option_number"],1)+expect_byte(sy["vi_view_gutter"],5)+expect_byte(sy["vi_view_width"],59)+unchanged(sy)+phase1._jp(PASS_PC)
        run_sna(root,bytes(code),patch=patch(image,gate,sy,b"number"))

        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._ld_hl(ARG)+b"\x01\x00\x00"+phase1._call(sy["vi_p921_set_cmd"])+phase1._jp_c(FAIL_PC))
        code+=expect_byte(ROW,23)+expect_byte(COL,0)
        for i,v in enumerate(b"number"): code+=expect_byte(OUT+i,v)
        code+=unchanged(sy)+phase1._jp(PASS_PC)
        run_sna(root,bytes(code),patch=patch(image,gate,sy,b"",number=1))

        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._ld_hl(ARG)+b"\x01\x08\x00"+phase1._call(sy["vi_p921_set_cmd"])+phase1._jp_c(FAIL_PC))
        code+=expect_byte(sy["vi_option_number"],0)+expect_byte(sy["vi_view_gutter"],0)+expect_byte(sy["vi_view_width"],64)+unchanged(sy)+phase1._jp(PASS_PC)
        run_sna(root,bytes(code),patch=patch(image,gate,sy,b"nonumber",number=1))

        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._ld_hl(ARG)+b"\x01\x06\x00"+phase1._call(sy["vi_p921_set_cmd"]))
        code+=b"\xD2"+word(FAIL_PC)+b"\xFE"+bytes((sy["E_INVAL"]&255,))+phase1._jp_nz(FAIL_PC)
        code+=expect_byte(sy["vi_option_number"],0)+expect_byte(sy["vi_view_gutter"],0)+expect_byte(sy["vi_view_width"],64)+unchanged(sy)+phase1._jp(PASS_PC)
        run_sna(root,bytes(code),patch=patch(image,gate,sy,b"Number"))

        assertions += [
          {"name":"fuse-set-number-five-column-gutter","passed":True},
          {"name":"fuse-set-report-current-option","passed":True},
          {"name":"fuse-set-nonumber-restores-64-columns","passed":True},
          {"name":"fuse-malformed-set-buffer-unchanged","passed":True},
        ]

    hashes={
      "tools/vi.asm":sha256_file(source),
      "v1/build/p921-vi.mex1":sha256_file(mex_path),
      "v1/build/p921-vi.tap":sha256_file(tap),
      "v1/tools-host/test-driver/phase9_vi_set.py":sha256_file(root/"v1/tools-host/test-driver/phase9_vi_set.py"),
      "v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
      "v1/dist/certification/P9.20.test.json":sha256_file(root/"v1/dist/certification/P9.20.test.json"),
    }
    return [fr,xr,gr],hashes,assertions
