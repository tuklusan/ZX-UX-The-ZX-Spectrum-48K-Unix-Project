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
# Exact branch-repair candidate.
GATE=0xE000
CURSOR=0xA300
ROW=0xA301
COL=0xA302
OUT=0xA400


class P909Error(DriverError):
    pass


def require(value,message):
    if not value:
        raise P909Error(message)


def expect_byte(address,value):
    return b"\x3A"+word(address)+bytes((0xFE,value&0xFF))+phase1._jp_nz(FAIL_PC)


def patch(image,gateway,sy,data=b"abc"):
    def apply(ram):
        ram[BASE-0x4000:BASE-0x4000+len(image)]=image
        ram[GATE-0x4000:GATE-0x4000+len(gateway)]=gateway
        ram[sy["vi_handle"]-0x4000]=3
        ram[sy["vi_buffer"]-0x4000:sy["vi_buffer"]-0x4000+len(data)]=data
        ram[sy["vi_buffer_len"]-0x4000:sy["vi_buffer_len"]-0x4000+2]=len(data).to_bytes(2,"little")
        ram[CURSOR-0x4000]=0
        ram[ROW-0x4000]=0
        ram[COL-0x4000]=0
        ram[OUT-0x4000:OUT-0x4000+32]=b"?"*32
    return apply


def logical_expect(sy,pos,value):
    code=b"\x21"+word(pos)+phase1._call(sy["vi_p903_get_byte"])+phase1._jp_c(FAIL_PC)
    return code+bytes((0xFE,value))+phase1._jp_nz(FAIL_PC)


def dispatch(root,action,step,*,sha256_file,run_command,require_project_tool):
    if step!="P9.09":
        raise DriverError(step)
    source=root/"tools/vi.asm"
    text=source.read_text(encoding="utf-8")
    plan=(root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md").read_text(encoding="utf-8")
    assertions=[
        {"name":"canonical-p909-present","passed":"## P9.09 - i a insert commands" in plan},
        {"name":"i-enters-insert","passed":"cp 'i'" in text[text.index("vi_p905_normal_key:"):text.index("vi_p905_insert_key:")]},
        {"name":"a-enters-append","passed":"cp 'a'" in text[text.index("vi_p905_normal_key:"):text.index("vi_p905_insert_key:")] and "vi_p909_enter_append:" in text},
        {"name":"insert-uses-gap-primitive","passed":"call vi_p903_insert_byte" in text[text.index("vi_p909_insert_byte:"):]},
        {"name":"failure-before-cursor-advance","passed":text.index("call vi_p903_insert_byte",text.index("vi_p909_insert_byte:")) < text.index("inc hl",text.index("vi_p909_insert_byte:"))},
    ]
    require(all(x["passed"] for x in assertions),"P9.09 static contract failure")

    assembler=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus")
    build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    fixture=build/"p909-vi.asm"
    fixture.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../../tools/vi.asm"
    ORG $C000
fixture:
    EMIT_P901_VI_ROUTINES
fixture_end:
    SAVEBIN "p909-vi.bin",fixture,fixture_end-fixture
""",encoding="utf-8",newline="\n")
    fr=run_command([assembler,"--nologo","--lst=p909-vi.lst","--sym=p909-vi.sym",fixture.name],cwd=build,timeout_seconds=30)
    require(not fr.timed_out and fr.exit_code==0,f"P9.09 assemble: {fr.stderr or fr.stdout}")
    image=(build/"p909-vi.bin").read_bytes()
    mex_path=build/"p909-vi.mex1"; mex_path.write_bytes(mex1(image))
    try:
        xr=inspect_mex(root,mex_path,run_command,require_project_tool)
        tap=make_tap(root,build,"vi","p909",mex_path)
    except RuntimeError as exc:
        raise P909Error(str(exc)) from exc

    gateway_source=build/"p909-gateway.asm"
    gateway_source.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    ORG $E000
gate:
    cp SYS_IOCTL
    jr z,g_ioctl
    cp SYS_CON_SETPOS
    jr z,g_ok
    cp SYS_CON_WRITE
    jr z,g_ok
    ld a,E_NOTSUP
    scf
    ret
g_ioctl:
    xor a
    ret
g_ok:
    xor a
    ret
gate_end:
    SAVEBIN "p909-gateway.bin",gate,gate_end-gate
""",encoding="utf-8",newline="\n")
    gr=run_command([assembler,"--nologo","--lst=p909-gateway.lst","--sym=p909-gateway.sym",gateway_source.name],cwd=build,timeout_seconds=30)
    require(not gr.timed_out and gr.exit_code==0,f"P9.09 gateway: {gr.stderr or gr.stdout}")

    if action=="test":
        sy=phase3_open_descriptions._symbols(build/"p909-vi.sym",(
            "vi_p903_init","vi_p903_get_byte","vi_p905_init_mode","vi_p905_key",
            "vi_buffer","vi_buffer_len","vi_cursor_off","vi_fail_gap_alloc","vi_editor_mode",
        ))
        gateway=(build/"p909-gateway.bin").read_bytes()

        # i inserts before the cursor.
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._call(sy["vi_p903_init"])+phase1._jp_c(FAIL_PC))
        code+=phase1._call(sy["vi_p905_init_mode"])+phase1._jp_c(FAIL_PC)
        code+=b"\x21"+word(1)+b"\x22"+word(sy["vi_cursor_off"])
        code+=b"\x3E"+bytes((ord("i"),))+phase1._call(sy["vi_p905_key"])+phase1._jp_c(FAIL_PC)
        code+=b"\x3E"+bytes((ord("X"),))+phase1._call(sy["vi_p905_key"])+phase1._jp_c(FAIL_PC)
        for pos,val in enumerate(b"aXbc"): code+=logical_expect(sy,pos,val)
        code+=expect_byte(sy["vi_buffer_len"],4)+phase1._jp(PASS_PC)
        run_sna(root,bytes(code),patch=patch(image,gateway,sy,b"abc"))

        # a inserts after the cursor.
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._call(sy["vi_p903_init"])+phase1._jp_c(FAIL_PC))
        code+=phase1._call(sy["vi_p905_init_mode"])+phase1._jp_c(FAIL_PC)
        code+=b"\x21"+word(0)+b"\x22"+word(sy["vi_cursor_off"])
        code+=b"\x3E"+bytes((ord("a"),))+phase1._call(sy["vi_p905_key"])+phase1._jp_c(FAIL_PC)
        code+=b"\x3E"+bytes((ord("Y"),))+phase1._call(sy["vi_p905_key"])+phase1._jp_c(FAIL_PC)
        for pos,val in enumerate(b"aYbc"): code+=logical_expect(sy,pos,val)
        code+=phase1._jp(PASS_PC)
        run_sna(root,bytes(code),patch=patch(image,gateway,sy,b"abc"))

        # Forced growth failure must preserve source and length.
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._call(sy["vi_p903_init"])+phase1._jp_c(FAIL_PC))
        code+=phase1._call(sy["vi_p905_init_mode"])+phase1._jp_c(FAIL_PC)
        code+=b"\x21"+word(1)+b"\x22"+word(sy["vi_cursor_off"])
        code+=b"\x3E"+bytes((ord("i"),))+phase1._call(sy["vi_p905_key"])+phase1._jp_c(FAIL_PC)
        code+=b"\x3E\x01\x32"+word(sy["vi_fail_gap_alloc"])
        code+=b"\x3E"+bytes((ord("Z"),))+phase1._call(sy["vi_p905_key"])+phase1._jp_nc(FAIL_PC)
        for pos,val in enumerate(b"abc"): code+=logical_expect(sy,pos,val)
        code+=expect_byte(sy["vi_buffer_len"],3)+phase1._jp(PASS_PC)
        run_sna(root,bytes(code),patch=patch(image,gateway,sy,b"abc"))

        assertions += [
            {"name":"fuse-i-buffer-bytes-exact","passed":True},
            {"name":"fuse-a-buffer-bytes-exact","passed":True},
            {"name":"fuse-growth-failure-source-intact","passed":True},
        ]

    hashes={
        "tools/vi.asm":sha256_file(source),
        "v1/build/p909-vi.mex1":sha256_file(mex_path),
        "v1/build/p909-vi.tap":sha256_file(tap),
        "v1/tools-host/test-driver/phase9_vi_insert.py":sha256_file(root/"v1/tools-host/test-driver/phase9_vi_insert.py"),
        "v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
        "v1/dist/certification/P9.08.test.json":sha256_file(root/"v1/dist/certification/P9.08.test.json"),
    }
    return [fr,xr,gr],hashes,assertions
