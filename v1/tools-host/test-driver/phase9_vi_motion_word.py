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
# Exact P9.07 qualification candidate.


class P907Error(DriverError):
    pass


def require(value,message):
    if not value:
        raise P907Error(message)


def expect_word(address,value):
    return b"\x3A"+word(address)+bytes((0xFE,value&0xFF))+phase1._jp_nz(FAIL_PC)+b"\x3A"+word(address+1)+bytes((0xFE,(value>>8)&0xFF))+phase1._jp_nz(FAIL_PC)


def patch(image,sy,data):
    def apply(ram):
        ram[BASE-0x4000:BASE-0x4000+len(image)]=image
        ram[sy["vi_buffer"]-0x4000:sy["vi_buffer"]-0x4000+len(data)]=data
        ram[sy["vi_buffer_len"]-0x4000:sy["vi_buffer_len"]-0x4000+2]=len(data).to_bytes(2,"little")
    return apply


def move_code(sy,start,commands,expected):
    code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._call(sy["vi_p903_init"])+phase1._jp_c(FAIL_PC))
    code+=b"\x21"+word(start)+b"\x22"+word(sy["vi_cursor_off"])
    for cmd,pos in zip(commands,expected):
        code+=b"\x3E"+bytes((ord(cmd),))+phase1._call(sy["vi_p907_move"])+phase1._jp_c(FAIL_PC)
        code+=expect_word(sy["vi_cursor_off"],pos)
    code+=phase1._jp(PASS_PC)
    return bytes(code)


def dispatch(root,action,step,*,sha256_file,run_command,require_project_tool):
    if step!="P9.07":
        raise DriverError(step)
    source=root/"tools/vi.asm"
    text=source.read_text(encoding="utf-8")
    plan=(root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md").read_text(encoding="utf-8")
    assertions=[
        {"name":"canonical-p907-present","passed":"## P9.07 - w b e word motions" in plan},
        {"name":"three-word-keys","passed":all(f"cp '{x}'" in text[text.index("vi_p907_move:"):] for x in ("w","b","e"))},
        {"name":"ascii-word-class","passed":all(x in text[text.index("vi_p907_class:"):] for x in ("cp '_'","cp '0'","cp 'A'","cp 'a'"))},
        {"name":"line-bounded","passed":"call vi_p906_current_end" in text[text.index("vi_p907_move:"):]},
    ]
    require(all(x["passed"] for x in assertions),"P9.07 static contract failure")

    assembler=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus")
    build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    fixture=build/"p907-vi.asm"
    fixture.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../../tools/vi.asm"
    ORG $C000
fixture:
    EMIT_P901_VI_ROUTINES
fixture_end:
    SAVEBIN "p907-vi.bin",fixture,fixture_end-fixture
""",encoding="utf-8",newline="\n")
    fr=run_command([assembler,"--nologo","--lst=p907-vi.lst","--sym=p907-vi.sym",fixture.name],cwd=build,timeout_seconds=30)
    require(not fr.timed_out and fr.exit_code==0,f"P9.07 assemble: {fr.stderr or fr.stdout}")
    image=(build/"p907-vi.bin").read_bytes()
    mex_path=build/"p907-vi.mex1"; mex_path.write_bytes(mex1(image))
    try:
        xr=inspect_mex(root,mex_path,run_command,require_project_tool)
        tap=make_tap(root,build,"vi","p907",mex_path)
    except RuntimeError as exc:
        raise P907Error(str(exc)) from exc

    if action=="test":
        sy=phase3_open_descriptions._symbols(build/"p907-vi.sym",(
            "vi_p903_init","vi_p907_move","vi_buffer","vi_buffer_len","vi_cursor_off",
        ))
        data=b"one two,xx\nabc"
        run_sna(root,move_code(sy,0,["w","w","w","w"],[4,7,8,8]),patch=patch(image,sy,data))
        run_sna(root,move_code(sy,8,["b","b","b"],[7,4,0]),patch=patch(image,sy,data))
        run_sna(root,move_code(sy,0,["e"],[2]),patch=patch(image,sy,data))
        run_sna(root,move_code(sy,3,["e"],[6]),patch=patch(image,sy,data))
        run_sna(root,move_code(sy,7,["e"],[7]),patch=patch(image,sy,data))
        run_sna(root,move_code(sy,11,["b","w","e"],[11,11,13]),patch=patch(image,sy,data))
        assertions += [
            {"name":"fuse-w-golden-ascii-positions","passed":True},
            {"name":"fuse-b-golden-ascii-positions","passed":True},
            {"name":"fuse-e-golden-ascii-positions","passed":True},
            {"name":"fuse-line-edges-stable","passed":True},
        ]

    hashes={
        "tools/vi.asm":sha256_file(source),
        "v1/build/p907-vi.mex1":sha256_file(mex_path),
        "v1/build/p907-vi.tap":sha256_file(tap),
        "v1/tools-host/test-driver/phase9_vi_motion_word.py":sha256_file(root/"v1/tools-host/test-driver/phase9_vi_motion_word.py"),
        "v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
        "v1/dist/certification/P9.06.test.json":sha256_file(root/"v1/dist/certification/P9.06.test.json"),
    }
    return [fr,xr],hashes,assertions
