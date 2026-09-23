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


class P906Error(DriverError):
    pass


def require(value,message):
    if not value:
        raise P906Error(message)


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
        code+=b"\x3E"+bytes((ord(cmd),))+phase1._call(sy["vi_p906_move"])+phase1._jp_c(FAIL_PC)
        code+=expect_word(sy["vi_cursor_off"],pos)
    code+=phase1._jp(PASS_PC)
    return bytes(code)


def dispatch(root,action,step,*,sha256_file,run_command,require_project_tool):
    if step!="P9.06":
        raise DriverError(step)
    source=root/"tools/vi.asm"
    text=source.read_text(encoding="utf-8")
    plan=(root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md").read_text(encoding="utf-8")
    assertions=[
        {"name":"canonical-p906-present","passed":"## P9.06 - h j k l 0 $ movement" in plan},
        {"name":"six-exact-motion-keys","passed":all(f"cp '{x}'" in text[text.index("vi_p906_move:"):] for x in ("h","j","k","l","0","$"))},
        {"name":"logical-cursor-offset","passed":"vi_cursor_off: dw 0" in text},
        {"name":"indexed-line-boundaries","passed":"vi_p906_line_start:" in text and "vi_p906_line_end_for_a:" in text},
        {"name":"empty-buffer-stable","passed":"ld (vi_cursor_off),hl" in text[text.index("vi_p906_move:"):text.index("vi_p906_nonempty:")]},
    ]
    require(all(x["passed"] for x in assertions),"P9.06 static contract failure")

    assembler=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus")
    build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    fixture=build/"p906-vi.asm"
    fixture.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../../tools/vi.asm"
    ORG $C000
fixture:
    EMIT_P901_VI_ROUTINES
fixture_end:
    SAVEBIN "p906-vi.bin",fixture,fixture_end-fixture
""",encoding="utf-8",newline="\n")
    fr=run_command([assembler,"--nologo","--lst=p906-vi.lst","--sym=p906-vi.sym",fixture.name],cwd=build,timeout_seconds=30)
    require(not fr.timed_out and fr.exit_code==0,f"P9.06 assemble: {fr.stderr or fr.stdout}")
    image=(build/"p906-vi.bin").read_bytes()
    mex_path=build/"p906-vi.mex1"; mex_path.write_bytes(mex1(image))
    try:
        xr=inspect_mex(root,mex_path,run_command,require_project_tool)
        tap=make_tap(root,build,"vi","p906",mex_path)
    except RuntimeError as exc:
        raise P906Error(str(exc)) from exc

    if action=="test":
        sy=phase3_open_descriptions._symbols(build/"p906-vi.sym",(
            "vi_p903_init","vi_p906_move","vi_buffer","vi_buffer_len","vi_cursor_off",
        ))
        data=b"abc\nde\nxyz"
        run_sna(root,move_code(sy,1,["h","h","l","0","$","l"],[0,0,1,0,2,2]),patch=patch(image,sy,data))
        run_sna(root,move_code(sy,2,["j","j","j"],[5,8,8]),patch=patch(image,sy,data))
        run_sna(root,move_code(sy,8,["k","k","k"],[5,1,1]),patch=patch(image,sy,data))
        run_sna(root,move_code(sy,4,["0","$","h"],[4,5,4]),patch=patch(image,sy,data))
        empty=b""
        run_sna(root,move_code(sy,0,["h","j","k","l","0","$"],[0,0,0,0,0,0]),patch=patch(image,sy,empty))
        assertions += [
            {"name":"fuse-horizontal-boundaries-exact","passed":True},
            {"name":"fuse-down-boundaries-exact","passed":True},
            {"name":"fuse-up-boundaries-exact","passed":True},
            {"name":"fuse-zero-dollar-exact","passed":True},
            {"name":"fuse-empty-no-under-overflow","passed":True},
        ]

    hashes={
        "tools/vi.asm":sha256_file(source),
        "v1/build/p906-vi.mex1":sha256_file(mex_path),
        "v1/build/p906-vi.tap":sha256_file(tap),
        "v1/tools-host/test-driver/phase9_vi_motion_basic.py":sha256_file(root/"v1/tools-host/test-driver/phase9_vi_motion_basic.py"),
        "v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
        "v1/dist/certification/P9.05.test.json":sha256_file(root/"v1/dist/certification/P9.05.test.json"),
    }
    return [fr,xr],hashes,assertions
