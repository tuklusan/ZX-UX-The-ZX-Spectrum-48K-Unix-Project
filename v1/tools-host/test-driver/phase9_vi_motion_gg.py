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

import phase1
import phase3_open_descriptions
from driver_core import DriverError
from fuse_harness import FAIL_PC, PASS_PC, run_sna
from phase8_common import inspect_mex, make_tap, mex1, word

BASE=0xC000
# Exact P9.08 qualification candidate.
# Word positions are logical offsets within one LF-delimited line.


class P908Error(DriverError):
    pass


def require(value,message):
    if not value:
        raise P908Error(message)


def expect_word(address,value):
    return b"\x3A"+word(address)+bytes((0xFE,value&0xFF))+phase1._jp_nz(FAIL_PC)+b"\x3A"+word(address+1)+bytes((0xFE,(value>>8)&0xFF))+phase1._jp_nz(FAIL_PC)


def patch(image,sy,data):
    def apply(ram):
        ram[BASE-0x4000:BASE-0x4000+len(image)]=image
        ram[sy["vi_buffer"]-0x4000:sy["vi_buffer"]-0x4000+len(data)]=data
        ram[sy["vi_buffer_len"]-0x4000:sy["vi_buffer_len"]-0x4000+2]=len(data).to_bytes(2,"little")
    return apply


def key_code(sy,start,keys,expected,pending):
    code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._call(sy["vi_p903_init"])+phase1._jp_c(FAIL_PC))
    code+=b"\x21"+word(start)+b"\x22"+word(sy["vi_cursor_off"])
    for key,pos,pend in zip(keys,expected,pending):
        code+=b"\x3E"+bytes((ord(key),))+phase1._call(sy["vi_p908_key"])
        code+=phase1._jp_c(FAIL_PC)
        code+=expect_word(sy["vi_cursor_off"],pos)
        code+=b"\x3A"+word(sy["vi_normal_pending"])+bytes((0xFE,pend))+phase1._jp_nz(FAIL_PC)
    code+=phase1._jp(PASS_PC)
    return bytes(code)


def dispatch(root,action,step,*,sha256_file,run_command,require_project_tool):
    if step!="P9.08":
        raise DriverError(step)
    source=root/"tools/vi.asm"
    text=source.read_text(encoding="utf-8")
    plan=(root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md").read_text(encoding="utf-8")
    assertions=[
        {"name":"canonical-p908-present","passed":"## P9.08 - gg and G case-sensitive motions" in plan},
        {"name":"case-sensitive-gg-G","passed":"vi_p908_after_g:" in text and "cp 'g'" in text[text.index("vi_p908_key:"):] and "cp 'G'" in text[text.index("vi_p908_key:"):]},
        {"name":"single-g-pending-only","passed":"vi_p908_arm_g:" in text and "ld (vi_normal_pending),a" in text[text.index("vi_p908_arm_g:"):]},
        {"name":"last-line-indexed","passed":"call vi_p906_line_start" in text[text.index("vi_p908_last:"):]},
    ]
    require(all(x["passed"] for x in assertions),"P9.08 static contract failure")

    assembler=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus")
    build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    fixture=build/"p908-vi.asm"
    fixture.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../../tools/vi.asm"
    ORG $C000
fixture:
    EMIT_P901_VI_ROUTINES
fixture_end:
    SAVEBIN "p908-vi.bin",fixture,fixture_end-fixture
""",encoding="utf-8",newline="\n")
    fr=run_command([assembler,"--nologo","--lst=p908-vi.lst","--sym=p908-vi.sym",fixture.name],cwd=build,timeout_seconds=30)
    require(not fr.timed_out and fr.exit_code==0,f"P9.08 assemble: {fr.stderr or fr.stdout}")
    image=(build/"p908-vi.bin").read_bytes()
    mex_path=build/"p908-vi.mex1"; mex_path.write_bytes(mex1(image))
    try:
        xr=inspect_mex(root,mex_path,run_command,require_project_tool)
        tap=make_tap(root,build,"vi","p908",mex_path)
    except RuntimeError as exc:
        raise P908Error(str(exc)) from exc

    if action=="test":
        sy=phase3_open_descriptions._symbols(build/"p908-vi.sym",(
            "vi_p903_init","vi_p908_key","vi_buffer","vi_buffer_len","vi_cursor_off","vi_normal_pending",
        ))
        data=b"one\ntwo\nthree"
        run_sna(root,key_code(sy,5,["g","g"],[5,0],[ord("g"),0]),patch=patch(image,sy,data))
        run_sna(root,key_code(sy,0,["G"],[8],[0]),patch=patch(image,sy,data))

        # Negative: one lowercase g must not alias uppercase G or move the cursor.
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._call(sy["vi_p903_init"])+phase1._jp_c(FAIL_PC))
        code+=b"\x21"+word(5)+b"\x22"+word(sy["vi_cursor_off"])
        code+=b"\x3E"+bytes((ord("g"),))+phase1._call(sy["vi_p908_key"])+phase1._jp_c(FAIL_PC)
        code+=expect_word(sy["vi_cursor_off"],5)
        code+=b"\x3A"+word(sy["vi_normal_pending"])+bytes((0xFE,ord("g")))+phase1._jp_nz(FAIL_PC)
        code+=phase1._jp(PASS_PC)
        run_sna(root,bytes(code),patch=patch(image,sy,data))

        assertions += [
            {"name":"fuse-gg-first-line-golden","passed":True},
            {"name":"fuse-G-last-line-golden","passed":True},
            {"name":"fuse-single-g-no-G-alias","passed":True},
        ]

    hashes={
        "tools/vi.asm":sha256_file(source),
        "v1/build/p908-vi.mex1":sha256_file(mex_path),
        "v1/build/p908-vi.tap":sha256_file(tap),
        "v1/tools-host/test-driver/phase9_vi_motion_gg.py":sha256_file(root/"v1/tools-host/test-driver/phase9_vi_motion_gg.py"),
        "v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
        "v1/dist/certification/P9.07.test.json":sha256_file(root/"v1/dist/certification/P9.07.test.json"),
    }
    return [fr,xr],hashes,assertions
