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
class P914Error(DriverError): pass
def require(v,m):
    if not v: raise P914Error(m)
def expect_byte(a,v): return b"\x3A"+word(a)+bytes((0xFE,v&255))+phase1._jp_nz(FAIL_PC)
def expect_word(a,v): return expect_byte(a,v&255)+expect_byte(a+1,(v>>8)&255)
def logical_byte(sy,off,val):
    return phase1._ld_hl(off)+phase1._call(sy["vi_p903_get_byte"])+bytes((0xFE,val&255))+phase1._jp_nz(FAIL_PC)
def patch(image,sy,data,cursor=0,dirty=0):
    def apply(ram):
        ram[BASE-0x4000:BASE-0x4000+len(image)]=image
        ram[sy["vi_buffer"]-0x4000:sy["vi_buffer"]-0x4000+len(data)]=data
        ram[sy["vi_buffer_len"]-0x4000:sy["vi_buffer_len"]-0x4000+2]=len(data).to_bytes(2,"little")
        ram[sy["vi_cursor_off"]-0x4000:sy["vi_cursor_off"]-0x4000+2]=cursor.to_bytes(2,"little")
        ram[sy["vi_dirty"]-0x4000]=dirty
    return apply

def dispatch(root,action,step,*,sha256_file,run_command,require_project_tool):
    if step!="P9.14": raise DriverError(step)
    source=root/"tools/vi.asm"; text=source.read_text(encoding="utf-8")
    plan=(root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md").read_text(encoding="utf-8")
    section=text[text.index("; P9.14"):]
    assertions=[
      {"name":"canonical-p914-present","passed":"## P9.14 - One-level undo" in plan},
      {"name":"bounded-delta-not-file-copy","passed":"vi_undo_data: defs VI_YANK_CAPACITY,0" in section and "defs VI_LOAD_CAPACITY" not in section},
      {"name":"exact-three-inverse-kinds","passed":all(x in section for x in ("VI_UNDO_INSERT","VI_UNDO_DELETE","VI_UNDO_REPLACE"))},
      {"name":"successful-u-consumes-history","passed":"ld (vi_undo_kind),a" in section[section.index("vi_p914_finish:"):]},
      {"name":"edit-hooks-installed","passed":text.count("call vi_p914_stage_state")>=6 and text.count("call vi_p914_commit_insert")>=3 and "call vi_p914_commit_delete_from_yank" in text and "call vi_p914_commit_replace" in text},
    ]
    require(all(x["passed"] for x in assertions),"P9.14 static contract failure")
    asm=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus")
    build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    fixture=build/"p914-vi.asm"
    fixture.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../../tools/vi.asm"
    ORG $C000
fixture:
    EMIT_P901_VI_ROUTINES
fixture_end:
    SAVEBIN "p914-vi.bin",fixture,fixture_end-fixture
""",encoding="utf-8",newline="\n")
    fr=run_command([asm,"--nologo","--lst=p914-vi.lst","--sym=p914-vi.sym",fixture.name],cwd=build,timeout_seconds=30)
    require(not fr.timed_out and fr.exit_code==0,f"P9.14 assemble: {fr.stderr or fr.stdout}")
    image=(build/"p914-vi.bin").read_bytes()
    mex_path=build/"p914-vi.mex1"; mex_path.write_bytes(mex1(image))
    try:
        xr=inspect_mex(root,mex_path,run_command,require_project_tool); tap=make_tap(root,build,"vi","p914",mex_path)
    except RuntimeError as exc: raise P914Error(str(exc)) from exc
    if action=="test":
        sy=phase3_open_descriptions._symbols(build/"p914-vi.sym",(
          "vi_p903_init","vi_p903_get_byte","vi_p909_insert_byte","vi_p911_x","vi_p913_r_begin","vi_p913_r_char","vi_p914_undo",
          "vi_buffer","vi_buffer_len","vi_cursor_off","vi_dirty","vi_undo_kind","E_NOTSUP",
        ))
        # insert then u
        data=b"abc"
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._call(sy["vi_p903_init"])+phase1._jp_c(FAIL_PC))
        code+=b"\x21"+word(1)+b"\x22"+word(sy["vi_cursor_off"])+b"\x3E"+bytes((ord("X"),))+phase1._call(sy["vi_p909_insert_byte"])+phase1._jp_c(FAIL_PC)
        code+=phase1._call(sy["vi_p914_undo"])+phase1._jp_c(FAIL_PC)
        code+=expect_word(sy["vi_buffer_len"],3)+expect_word(sy["vi_cursor_off"],1)+expect_byte(sy["vi_dirty"],0)
        for i,v in enumerate(data): code+=logical_byte(sy,i,v)
        code+=phase1._jp(PASS_PC); run_sna(root,bytes(code),patch=patch(image,sy,data,1,0))
        # delete then u
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._call(sy["vi_p903_init"])+phase1._jp_c(FAIL_PC))
        code+=b"\x21"+word(1)+b"\x22"+word(sy["vi_cursor_off"])+phase1._call(sy["vi_p911_x"])+phase1._jp_c(FAIL_PC)
        code+=phase1._call(sy["vi_p914_undo"])+phase1._jp_c(FAIL_PC)
        code+=expect_word(sy["vi_buffer_len"],3)+expect_word(sy["vi_cursor_off"],1)+expect_byte(sy["vi_dirty"],0)
        for i,v in enumerate(data): code+=logical_byte(sy,i,v)
        code+=phase1._jp(PASS_PC); run_sna(root,bytes(code),patch=patch(image,sy,data,1,0))
        # replace then u, then a second u must be unsupported and byte-identical.
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._call(sy["vi_p903_init"])+phase1._jp_c(FAIL_PC))
        code+=b"\x21"+word(1)+b"\x22"+word(sy["vi_cursor_off"])+phase1._call(sy["vi_p913_r_begin"])+phase1._jp_c(FAIL_PC)
        code+=b"\x3E"+bytes((ord("X"),))+phase1._call(sy["vi_p913_r_char"])+phase1._jp_c(FAIL_PC)
        code+=phase1._call(sy["vi_p914_undo"])+phase1._jp_c(FAIL_PC)
        code+=phase1._call(sy["vi_p914_undo"])+b"\xD2"+word(FAIL_PC)+b"\xFE"+bytes((sy["E_NOTSUP"]&255,))+phase1._jp_nz(FAIL_PC)
        code+=expect_byte(sy["vi_undo_kind"],0)+expect_word(sy["vi_cursor_off"],1)+expect_byte(sy["vi_dirty"],0)
        for i,v in enumerate(data): code+=logical_byte(sy,i,v)
        code+=phase1._jp(PASS_PC); run_sna(root,bytes(code),patch=patch(image,sy,data,1,0))
        assertions += [
          {"name":"fuse-insert-u-restores-prior-state","passed":True},
          {"name":"fuse-delete-u-restores-prior-state","passed":True},
          {"name":"fuse-replace-u-restores-prior-state","passed":True},
          {"name":"fuse-second-history-not-invented","passed":True},
        ]
    hashes={
      "tools/vi.asm":sha256_file(source),"v1/build/p914-vi.mex1":sha256_file(mex_path),
      "v1/build/p914-vi.tap":sha256_file(tap),
      "v1/tools-host/test-driver/phase9_vi_undo.py":sha256_file(root/"v1/tools-host/test-driver/phase9_vi_undo.py"),
      "v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
      "v1/dist/certification/P9.13.test.json":sha256_file(root/"v1/dist/certification/P9.13.test.json"),
    }
    return [fr,xr],hashes,assertions
