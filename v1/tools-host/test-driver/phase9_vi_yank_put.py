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
# Exact P9.12 qualification candidate.
class P912Error(DriverError): pass
def require(v,m):
    if not v: raise P912Error(m)
def expect_byte(a,v): return b"\x3A"+word(a)+bytes((0xFE,v&255))+phase1._jp_nz(FAIL_PC)
def expect_word(a,v): return expect_byte(a,v&255)+expect_byte(a+1,(v>>8)&255)
def logical_byte(sy,off,val):
    return phase1._ld_hl(off)+phase1._call(sy["vi_p903_get_byte"])+bytes((0xFE,val&255))+phase1._jp_nz(FAIL_PC)
def patch(image,sy,data,cursor=0):
    def apply(ram):
        ram[BASE-0x4000:BASE-0x4000+len(image)]=image
        ram[sy["vi_buffer"]-0x4000:sy["vi_buffer"]-0x4000+len(data)]=data
        ram[sy["vi_buffer_len"]-0x4000:sy["vi_buffer_len"]-0x4000+2]=len(data).to_bytes(2,"little")
        ram[sy["vi_cursor_off"]-0x4000:sy["vi_cursor_off"]-0x4000+2]=cursor.to_bytes(2,"little")
    return apply
def seed_char_yank(sy,byte):
    return (b"\x3E"+bytes((byte,))+b"\x32"+word(sy["vi_yank_buf"])+
            b"\x21\x01\x00\x22"+word(sy["vi_yank_len"])+
            b"\xAF\x32"+word(sy["vi_yank_linewise"]))

def dispatch(root,action,step,*,sha256_file,run_command,require_project_tool):
    if step!="P9.12": raise DriverError(step)
    source=root/"tools/vi.asm"; text=source.read_text(encoding="utf-8")
    plan=(root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md").read_text(encoding="utf-8")
    assertions=[
      {"name":"canonical-p912-present","passed":"## P9.12 - yy p P yank/put" in plan},
      {"name":"single-yank-buffer","passed":text.count("vi_yank_buf:") == 1},
      {"name":"yy-entry","passed":"vi_p912_yy:" in text},
      {"name":"distinct-p-P","passed":"cp 'P'" in text[text.index("vi_p912_put:"):]},
      {"name":"preflight-before-insert","passed":text.index("call vi_p912_preflight",text.index("vi_p912_put:")) < text.index("call vi_p903_insert_byte",text.index("vi_p912_put:"))},
    ]
    require(all(x["passed"] for x in assertions),"P9.12 static contract failure")
    asm=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus")
    build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    fixture=build/"p912-vi.asm"
    fixture.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../../tools/vi.asm"
    ORG $C000
fixture:
    EMIT_P901_VI_ROUTINES
fixture_end:
    SAVEBIN "p912-vi.bin",fixture,fixture_end-fixture
""",encoding="utf-8",newline="\n")
    fr=run_command([asm,"--nologo","--lst=p912-vi.lst","--sym=p912-vi.sym",fixture.name],cwd=build,timeout_seconds=30)
    require(not fr.timed_out and fr.exit_code==0,f"P9.12 assemble: {fr.stderr or fr.stdout}")
    image=(build/"p912-vi.bin").read_bytes()
    mex_path=build/"p912-vi.mex1"; mex_path.write_bytes(mex1(image))
    try:
        xr=inspect_mex(root,mex_path,run_command,require_project_tool); tap=make_tap(root,build,"vi","p912",mex_path)
    except RuntimeError as exc: raise P912Error(str(exc)) from exc
    if action=="test":
        sy=phase3_open_descriptions._symbols(build/"p912-vi.sym",(
          "vi_p903_init","vi_p903_get_byte","vi_p912_yy","vi_p912_put",
          "vi_buffer","vi_buffer_len","vi_cursor_off","vi_yank_len","vi_yank_linewise","vi_yank_buf",
          "vi_fail_gap_alloc","E_NOMEM",
        ))
        data=b"aa\nbb\n"
        # yy linewise then P before current line.
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._call(sy["vi_p903_init"])+phase1._jp_c(FAIL_PC))
        code+=b"\x21"+word(4)+b"\x22"+word(sy["vi_cursor_off"])+phase1._call(sy["vi_p912_yy"])+phase1._jp_c(FAIL_PC)
        code+=expect_word(sy["vi_yank_len"],3)+expect_byte(sy["vi_yank_linewise"],1)
        code+=b"\x3E"+bytes((ord("P"),))+phase1._call(sy["vi_p912_put"])+phase1._jp_c(FAIL_PC)
        code+=expect_word(sy["vi_cursor_off"],3)
        for i,v in enumerate(b"aa\nbb\nbb\n"): code+=logical_byte(sy,i,v)
        code+=phase1._jp(PASS_PC); run_sna(root,bytes(code),patch=patch(image,sy,data,4))
        # charwise P and p have distinct locations.
        for cmd,expected_bytes,expected_cursor in [
          ("P",b"aXbc",1),("p",b"abXc",2)
        ]:
            data2=b"abc"
            code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._call(sy["vi_p903_init"])+phase1._jp_c(FAIL_PC))
            code+=seed_char_yank(sy,ord("X"))
            code+=b"\x21"+word(1)+b"\x22"+word(sy["vi_cursor_off"])
            code+=b"\x3E"+bytes((ord(cmd),))+phase1._call(sy["vi_p912_put"])+phase1._jp_c(FAIL_PC)
            code+=expect_word(sy["vi_cursor_off"],expected_cursor)
            for i,v in enumerate(expected_bytes): code+=logical_byte(sy,i,v)
            code+=phase1._jp(PASS_PC); run_sna(root,bytes(code),patch=patch(image,sy,data2,1))
        # Forced allocation failure is atomic.
        data3=b"abc"
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._call(sy["vi_p903_init"])+phase1._jp_c(FAIL_PC))
        code+=seed_char_yank(sy,ord("X"))+b"\x3E\x01\x32"+word(sy["vi_fail_gap_alloc"])
        code+=b"\x21"+word(1)+b"\x22"+word(sy["vi_cursor_off"])+b"\x3E"+bytes((ord("p"),))+phase1._call(sy["vi_p912_put"])
        code+=b"\xD2"+word(FAIL_PC)+b"\xFE"+bytes((sy["E_NOMEM"]&255,))+phase1._jp_nz(FAIL_PC)
        code+=expect_word(sy["vi_buffer_len"],3)+expect_word(sy["vi_cursor_off"],1)
        for i,v in enumerate(data3): code+=logical_byte(sy,i,v)
        code+=phase1._jp(PASS_PC); run_sna(root,bytes(code),patch=patch(image,sy,data3,1))
        assertions += [
          {"name":"fuse-yy-linewise-P-golden","passed":True},
          {"name":"fuse-charwise-p-P-distinct","passed":True},
          {"name":"fuse-put-memory-failure-atomic","passed":True},
        ]
    hashes={
      "tools/vi.asm":sha256_file(source),"v1/build/p912-vi.mex1":sha256_file(mex_path),
      "v1/build/p912-vi.tap":sha256_file(tap),
      "v1/tools-host/test-driver/phase9_vi_yank_put.py":sha256_file(root/"v1/tools-host/test-driver/phase9_vi_yank_put.py"),
      "v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
      "v1/dist/certification/P9.11.test.json":sha256_file(root/"v1/dist/certification/P9.11.test.json"),
    }
    return [fr,xr],hashes,assertions
