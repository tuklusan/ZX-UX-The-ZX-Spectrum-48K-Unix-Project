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
# Final repaired qualification head.
GATE=0xE000
CURSOR=0xA300
ROW=0xA301
COL=0xA302
OUT=0xA400


class P910Error(DriverError):
    pass


def require(value,message):
    if not value:
        raise P910Error(message)


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


def logical_expect(sy,pos,value):
    code=b"\x21"+word(pos)+phase1._call(sy["vi_p903_get_byte"])+phase1._jp_c(FAIL_PC)
    return code+bytes((0xFE,value))+phase1._jp_nz(FAIL_PC)


def expect_word(address,value):
    return b"\x3A"+word(address)+bytes((0xFE,value&0xFF))+phase1._jp_nz(FAIL_PC)+b"\x3A"+word(address+1)+bytes((0xFE,(value>>8)&0xFF))+phase1._jp_nz(FAIL_PC)


def dispatch(root,action,step,*,sha256_file,run_command,require_project_tool):
    if step!="P9.10":
        raise DriverError(step)
    source=root/"tools/vi.asm"
    text=source.read_text(encoding="utf-8")
    plan=(root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md").read_text(encoding="utf-8")
    assertions=[
        {"name":"canonical-p910-present","passed":"## P9.10 - o O open-line commands" in plan},
        {"name":"case-sensitive-o-O","passed":"cp 'o'" in text[text.index("vi_p905_normal_key:"):text.index("vi_p905_insert_key:")] and "cp 'O'" in text[text.index("vi_p905_normal_key:"):text.index("vi_p905_insert_key:")]},
        {"name":"open-uses-gap-insert","passed":"call vi_p903_insert_byte" in text[text.index("vi_p910_open:"):]},
        {"name":"allocation-failure-before-cursor","passed":text.index("call vi_p903_insert_byte",text.index("vi_p910_open:")) < text.index("ld (vi_cursor_off),hl",text.index("vi_p910_open:"))},
    ]
    require(all(x["passed"] for x in assertions),"P9.10 static contract failure")

    assembler=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus")
    build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    fixture=build/"p910-vi.asm"
    fixture.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../../tools/vi.asm"
    ORG $C000
fixture:
    EMIT_P901_VI_ROUTINES
fixture_end:
    SAVEBIN "p910-vi.bin",fixture,fixture_end-fixture
""",encoding="utf-8",newline="\n")
    fr=run_command([assembler,"--nologo","--lst=p910-vi.lst","--sym=p910-vi.sym",fixture.name],cwd=build,timeout_seconds=30)
    require(not fr.timed_out and fr.exit_code==0,f"P9.10 assemble: {fr.stderr or fr.stdout}")
    image=(build/"p910-vi.bin").read_bytes()
    mex_path=build/"p910-vi.mex1"; mex_path.write_bytes(mex1(image))
    try:
        xr=inspect_mex(root,mex_path,run_command,require_project_tool)
        tap=make_tap(root,build,"vi","p910",mex_path)
    except RuntimeError as exc:
        raise P910Error(str(exc)) from exc

    gateway_source=build/"p910-gateway.asm"
    gateway_source.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    ORG $E000
gate:
    cp SYS_IOCTL
    jr z,g_ok
    cp SYS_CON_SETPOS
    jr z,g_ok
    cp SYS_CON_WRITE
    jr z,g_ok
    ld a,E_NOTSUP
    scf
    ret
g_ok:
    xor a
    ret
gate_end:
    SAVEBIN "p910-gateway.bin",gate,gate_end-gate
""",encoding="utf-8",newline="\n")
    gr=run_command([assembler,"--nologo","--lst=p910-gateway.lst","--sym=p910-gateway.sym",gateway_source.name],cwd=build,timeout_seconds=30)
    require(not gr.timed_out and gr.exit_code==0,f"P9.10 gateway: {gr.stderr or gr.stdout}")

    if action=="test":
        sy=phase3_open_descriptions._symbols(build/"p910-vi.sym",(
            "vi_handle","vi_p903_init","vi_p903_get_byte","vi_p905_init_mode","vi_p905_key",
            "vi_buffer","vi_buffer_len","vi_cursor_off","vi_fail_gap_alloc",
        ))
        gateway=(build/"p910-gateway.bin").read_bytes()
        data=b"abc\ndef"

        # o opens an empty line below the first line.
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._call(sy["vi_p903_init"])+phase1._jp_c(FAIL_PC))
        code+=phase1._call(sy["vi_p905_init_mode"])+phase1._jp_c(FAIL_PC)
        code+=b"\x21"+word(1)+b"\x22"+word(sy["vi_cursor_off"])
        code+=b"\x3E"+bytes((ord("o"),))+phase1._call(sy["vi_p905_key"])+phase1._jp_c(FAIL_PC)
        for pos,val in enumerate(b"abc\n\ndef"): code+=logical_expect(sy,pos,val)
        code+=expect_word(sy["vi_cursor_off"],4)+phase1._jp(PASS_PC)
        run_sna(root,bytes(code),patch=patch(image,gateway,sy,data))

        # O opens an empty line above the second line.
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._call(sy["vi_p903_init"])+phase1._jp_c(FAIL_PC))
        code+=phase1._call(sy["vi_p905_init_mode"])+phase1._jp_c(FAIL_PC)
        code+=b"\x21"+word(5)+b"\x22"+word(sy["vi_cursor_off"])
        code+=b"\x3E"+bytes((ord("O"),))+phase1._call(sy["vi_p905_key"])+phase1._jp_c(FAIL_PC)
        for pos,val in enumerate(b"abc\n\ndef"): code+=logical_expect(sy,pos,val)
        code+=expect_word(sy["vi_cursor_off"],4)+phase1._jp(PASS_PC)
        run_sna(root,bytes(code),patch=patch(image,gateway,sy,data))

        # Forced allocation failure is atomic.
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._call(sy["vi_p903_init"])+phase1._jp_c(FAIL_PC))
        code+=phase1._call(sy["vi_p905_init_mode"])+phase1._jp_c(FAIL_PC)
        code+=b"\x21"+word(1)+b"\x22"+word(sy["vi_cursor_off"])
        code+=b"\x3E\x01\x32"+word(sy["vi_fail_gap_alloc"])
        code+=b"\x3E"+bytes((ord("o"),))+phase1._call(sy["vi_p905_key"])+b"\xD2"+word(FAIL_PC)
        for pos,val in enumerate(data): code+=logical_expect(sy,pos,val)
        code+=expect_word(sy["vi_cursor_off"],1)+expect_byte(sy["vi_buffer_len"],len(data))+phase1._jp(PASS_PC)
        run_sna(root,bytes(code),patch=patch(image,gateway,sy,data))

        assertions += [
            {"name":"fuse-o-golden-bytes-cursor","passed":True},
            {"name":"fuse-O-golden-bytes-cursor","passed":True},
            {"name":"fuse-open-allocation-failure-atomic","passed":True},
        ]

    hashes={
        "tools/vi.asm":sha256_file(source),
        "v1/build/p910-vi.mex1":sha256_file(mex_path),
        "v1/build/p910-vi.tap":sha256_file(tap),
        "v1/tools-host/test-driver/phase9_vi_open.py":sha256_file(root/"v1/tools-host/test-driver/phase9_vi_open.py"),
        "v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
        "v1/dist/certification/P9.09.test.json":sha256_file(root/"v1/dist/certification/P9.09.test.json"),
    }
    return [fr,xr,gr],hashes,assertions
