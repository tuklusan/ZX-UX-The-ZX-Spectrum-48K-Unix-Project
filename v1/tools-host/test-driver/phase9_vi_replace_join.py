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

BASE=0xC000
# Exact P9.13 qualification candidate.
# Current-head acceptance diagnostics.
class P913Error(DriverError): pass
def require(v,m):
    if not v: raise P913Error(m)
def expect_byte(a,v): return b"\x3A"+word(a)+bytes((0xFE,v&255))+phase1._jp_nz(FAIL_PC)
def logical_byte(sy,off,val):
    return phase1._ld_hl(off)+phase1._call(sy["vi_p903_get_byte"])+bytes((0xFE,val&255))+phase1._jp_nz(FAIL_PC)

def run_case(root,name,code,patcher):
    try:
        run_sna(root,bytes(code),patch=patcher)
    except DriverError as exc:
        raise P913Error(f"P9.13 {name}: {exc}") from exc
def patch(image,sy,data,cursor=0):
    def apply(ram):
        ram[BASE-0x4000:BASE-0x4000+len(image)]=image
        ram[sy["vi_buffer"]-0x4000:sy["vi_buffer"]-0x4000+len(data)]=data
        ram[sy["vi_buffer_len"]-0x4000:sy["vi_buffer_len"]-0x4000+2]=len(data).to_bytes(2,"little")
        ram[sy["vi_cursor_off"]-0x4000:sy["vi_cursor_off"]-0x4000+2]=cursor.to_bytes(2,"little")
    return apply

def dispatch(root,action,step,*,sha256_file,run_command,require_project_tool):
    if step!="P9.13": raise DriverError(step)
    source=root/"tools/vi.asm"; text=source.read_text(encoding="utf-8")
    plan=(root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md").read_text(encoding="utf-8")
    assertions=[
      {"name":"canonical-p913-present","passed":"## P9.13 - r J replacement/join" in plan},
      {"name":"two-stage-r","passed":"vi_p913_r_begin:" in text and "vi_p913_r_char:" in text},
      {"name":"join-next-line-only","passed":"vi_p913_J:" in text and "call vi_p906_current_end" in text[text.index("vi_p913_J:"):]},
      {"name":"same-size-replace","passed":"vi_p913_set_byte:" in text},
    ]
    require(all(x["passed"] for x in assertions),"P9.13 static contract failure")
    asm=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus")
    build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    fixture=build/"p913-vi.asm"
    fixture.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../../tools/vi.asm"
    ORG $C000
fixture:
    EMIT_P901_VI_ROUTINES
fixture_end:
    SAVEBIN "p913-vi.bin",fixture,fixture_end-fixture
""",encoding="utf-8",newline="\n")
    fr=run_command([asm,"--nologo","--lst=p913-vi.lst","--sym=p913-vi.sym",fixture.name],cwd=build,timeout_seconds=30)
    require(not fr.timed_out and fr.exit_code==0,f"P9.13 assemble: {fr.stderr or fr.stdout}")
    image=(build/"p913-vi.bin").read_bytes()
    mex_path=build/"p913-vi.mex1"; mex_path.write_bytes(mex1(image))
    try:
        xr=inspect_mex(root,mex_path,run_command,require_project_tool); tap=make_tap(root,build,"vi","p913",mex_path)
    except RuntimeError as exc: raise P913Error(str(exc)) from exc
    if action=="test":
        sy=phase3_open_descriptions._symbols(build/"p913-vi.sym",(
          "vi_p903_init","vi_p903_get_byte","vi_p913_r_begin","vi_p913_r_char","vi_p913_J",
          "vi_buffer","vi_buffer_len","vi_cursor_off","vi_replace_pending","vi_dirty","E_INVAL",
        ))
        # r replacement
        data=b"abc"
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._call(sy["vi_p903_init"])+phase1._jp_c(FAIL_PC))
        code+=b"\x21"+word(1)+b"\x22"+word(sy["vi_cursor_off"])+phase1._call(sy["vi_p913_r_begin"])+phase1._jp_c(FAIL_PC)
        code+=expect_byte(sy["vi_replace_pending"],1)+b"\x3E"+bytes((ord("X"),))+phase1._call(sy["vi_p913_r_char"])+phase1._jp_c(FAIL_PC)
        for i,v in enumerate(b"aXc"): code+=logical_byte(sy,i,v)
        code+=expect_byte(sy["vi_dirty"],1)+phase1._jp(PASS_PC)
        run_case(root,"replace",code,patch(image,sy,data,1))
        # J joins with one space and updates index.
        data2=b"aa\nbb"
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._call(sy["vi_p903_init"])+phase1._jp_c(FAIL_PC))
        code+=phase1._call(sy["vi_p913_J"])+phase1._jp_c(FAIL_PC)
        for i,v in enumerate(b"aa bb"): code+=logical_byte(sy,i,v)
        code+=expect_byte(sy["vi_dirty"],1)+phase1._jp(PASS_PC)
        run_case(root,"join",code,patch(image,sy,data2,0))
        # Missing replacement char: begin only, byte-identical.
        data3=b"abc"
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._call(sy["vi_p903_init"])+phase1._jp_c(FAIL_PC))
        code+=phase1._call(sy["vi_p913_r_begin"])+phase1._jp_c(FAIL_PC)
        for i,v in enumerate(data3): code+=logical_byte(sy,i,v)
        code+=phase1._jp(PASS_PC)
        run_case(root,"missing-replacement",code,patch(image,sy,data3,0))
        # J on final/only line safe.
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._call(sy["vi_p903_init"])+phase1._jp_c(FAIL_PC))
        code+=phase1._call(sy["vi_p913_J"])+phase1._jp_c(FAIL_PC)
        for i,v in enumerate(data3): code+=logical_byte(sy,i,v)
        code+=phase1._jp(PASS_PC)
        run_case(root,"final-line-join",code,patch(image,sy,data3,0))
        assertions += [
          {"name":"fuse-r-golden","passed":True},{"name":"fuse-J-golden","passed":True},
          {"name":"fuse-missing-replacement-safe","passed":True},{"name":"fuse-no-next-line-safe","passed":True},
        ]
    hashes={
      "tools/vi.asm":sha256_file(source),"v1/build/p913-vi.mex1":sha256_file(mex_path),
      "v1/build/p913-vi.tap":sha256_file(tap),
      "v1/tools-host/test-driver/phase9_vi_replace_join.py":sha256_file(root/"v1/tools-host/test-driver/phase9_vi_replace_join.py"),
      "v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
      "v1/dist/certification/P9.12.test.json":sha256_file(root/"v1/dist/certification/P9.12.test.json"),
    }
    return [fr,xr],hashes,assertions
