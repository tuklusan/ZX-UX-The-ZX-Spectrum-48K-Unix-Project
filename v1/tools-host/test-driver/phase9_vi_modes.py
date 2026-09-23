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
GATE=0xE000
CURSOR=0xA300
ROW=0xA301
COL=0xA302
OUT=0xA400


class P905Error(DriverError):
    pass


def require(value,message):
    if not value:
        raise P905Error(message)


def expect_byte(address,value):
    return b"\x3A"+word(address)+bytes((0xFE,value&0xFF))+phase1._jp_nz(FAIL_PC)


def run_case(root,name,code,patcher):
    try:
        run_sna(root,bytes(code),patch=patcher)
    except DriverError as exc:
        raise P905Error(f"P9.05 {name}: {exc}") from exc


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


def dispatch(root,action,step,*,sha256_file,run_command,require_project_tool):
    if step!="P9.05":
        raise DriverError(step)
    source=root/"tools/vi.asm"
    text=source.read_text(encoding="utf-8")
    plan=(root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md").read_text(encoding="utf-8")
    assertions=[
        {"name":"canonical-p905-present","passed":"## P9.05 - Normal/insert/command-line mode state machine" in plan},
        {"name":"exact-three-mode-constants","passed":all(x in text for x in ("VI_MODE_NORMAL          EQU 0","VI_MODE_INSERT          EQU 1","VI_MODE_COMMAND         EQU 2"))},
        {"name":"canonical-escape-byte","passed":"VI_ESC                  EQU $1B" in text},
        {"name":"exact-insert-literal","passed":"vi_insert_msg: db '-','-',' ','I','N','S','E','R','T',' ','-','-'" in text},
        {"name":"status-row-23","passed":"ld hl,$1700" in text},
        {"name":"insert-and-command-underline","passed":text.count("call vi_p905_cursor_underline")>=2},
        {"name":"normal-block-cursor","passed":"vi_p905_cursor_block:" in text and "ld a,VI_CURSOR_BLOCK" in text},
        {"name":"escape-clears-pending-command","passed":"vi_p905_escape:" in text and "ld (vi_normal_pending),a" in text[text.index("vi_p905_escape:"):] and "ld (vi_command_len),a" in text[text.index("vi_p905_escape:"):]},
        {"name":"break-not-escape-alias","passed":"BREAK" in text[text.index("; P9.05"):text.index("vi_editor_mode:")] and "VI_ESC" in text},
    ]
    require(all(x["passed"] for x in assertions),"P9.05 static contract failure")

    assembler=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus")
    build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    fixture=build/"p905-vi.asm"
    fixture.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../../tools/vi.asm"
    ORG $C000
fixture:
    EMIT_P901_VI_ROUTINES
fixture_end:
    SAVEBIN "p905-vi.bin",fixture,fixture_end-fixture
""",encoding="utf-8",newline="\n")
    fr=run_command([assembler,"--nologo","--lst=p905-vi.lst","--sym=p905-vi.sym",fixture.name],cwd=build,timeout_seconds=30)
    require(not fr.timed_out and fr.exit_code==0,f"P9.05 assemble: {fr.stderr or fr.stdout}")
    image=(build/"p905-vi.bin").read_bytes()
    mex_path=build/"p905-vi.mex1"; mex_path.write_bytes(mex1(image))
    try:
        xr=inspect_mex(root,mex_path,run_command,require_project_tool)
        tap=make_tap(root,build,"vi","p905",mex_path)
    except RuntimeError as exc:
        raise P905Error(str(exc)) from exc

    gateway_source=build/"p905-gateway.asm"
    gateway_source.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    ORG $E000
gate:
    cp SYS_IOCTL
    jr z,g_ioctl
    cp SYS_CON_SETPOS
    jr z,g_setpos
    cp SYS_CON_WRITE
    jr z,g_write
    ld a,E_NOTSUP
    scf
    ret
g_ioctl:
    inc hl
    ld a,(hl)
    cp 4
    jr nz,g_bad
    inc hl
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld a,(de)
    ld ($A300),a
    xor a
    ret
g_setpos:
    ld a,h
    ld ($A301),a
    ld a,l
    ld ($A302),a
    xor a
    ret
g_write:
    ld de,$A400
    ldir
    xor a
    ret
g_bad:
    ld a,E_INVAL
    scf
    ret
gate_end:
    SAVEBIN "p905-gateway.bin",gate,gate_end-gate
""",encoding="utf-8",newline="\n")
    gr=run_command([assembler,"--nologo","--lst=p905-gateway.lst","--sym=p905-gateway.sym",gateway_source.name],cwd=build,timeout_seconds=30)
    require(not gr.timed_out and gr.exit_code==0,f"P9.05 gateway: {gr.stderr or gr.stdout}")

    if action=="test":
        sy=phase3_open_descriptions._symbols(build/"p905-vi.sym",(
            "vi_p905_init_mode","vi_p905_key","vi_editor_mode","vi_normal_pending","vi_command_len",
            "vi_handle","vi_buffer","vi_buffer_len","VI_MODE_NORMAL","VI_MODE_INSERT","VI_MODE_COMMAND",
        ))
        gateway=(build/"p905-gateway.bin").read_bytes()

        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._call(sy["vi_p905_init_mode"])+phase1._jp_c(FAIL_PC))
        code+=expect_byte(sy["vi_editor_mode"],sy["VI_MODE_NORMAL"])+expect_byte(CURSOR,2)+expect_byte(ROW,23)+expect_byte(COL,0)
        code+=b"\x3E"+bytes((ord("i"),))+phase1._call(sy["vi_p905_key"])+phase1._jp_c(FAIL_PC)
        code+=expect_byte(sy["vi_editor_mode"],sy["VI_MODE_INSERT"])+expect_byte(CURSOR,1)+expect_byte(ROW,23)+expect_byte(COL,0)
        for i,v in enumerate(b"-- INSERT --"): code+=expect_byte(OUT+i,v)
        code+=b"\x3E\x1B"+phase1._call(sy["vi_p905_key"])+phase1._jp_c(FAIL_PC)
        code+=expect_byte(sy["vi_editor_mode"],sy["VI_MODE_NORMAL"])+expect_byte(CURSOR,2)
        for i in range(12): code+=expect_byte(OUT+i,ord(" "))
        for i,v in enumerate(b"abc"): code+=expect_byte(sy["vi_buffer"]+i,v)
        code+=phase1._jp(PASS_PC)
        run_case(root,"normal-insert-escape",code,patch(image,gateway,sy))

        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._call(sy["vi_p905_init_mode"])+phase1._jp_c(FAIL_PC))
        code+=b"\x3E"+bytes((ord(":"),))+phase1._call(sy["vi_p905_key"])+phase1._jp_c(FAIL_PC)
        code+=expect_byte(sy["vi_editor_mode"],sy["VI_MODE_COMMAND"])+expect_byte(CURSOR,1)+expect_byte(OUT,ord(":"))
        code+=b"\x3E"+bytes((ord("q"),))+phase1._call(sy["vi_p905_key"])+phase1._jp_c(FAIL_PC)+expect_byte(sy["vi_command_len"],1)
        code+=b"\x3E\x1B"+phase1._call(sy["vi_p905_key"])+phase1._jp_c(FAIL_PC)
        code+=expect_byte(sy["vi_editor_mode"],sy["VI_MODE_NORMAL"])+expect_byte(sy["vi_command_len"],0)+expect_byte(CURSOR,2)
        for i in range(12): code+=expect_byte(OUT+i,ord(" "))
        code+=phase1._jp(PASS_PC)
        run_case(root,"command-escape",code,patch(image,gateway,sy))

        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._call(sy["vi_p905_init_mode"])+phase1._jp_c(FAIL_PC))
        code+=b"\x3E"+bytes((ord("d"),))+phase1._call(sy["vi_p905_key"])+phase1._jp_c(FAIL_PC)+expect_byte(sy["vi_normal_pending"],1)
        code+=b"\x3E\x1B"+phase1._call(sy["vi_p905_key"])+phase1._jp_c(FAIL_PC)
        code+=expect_byte(sy["vi_editor_mode"],sy["VI_MODE_NORMAL"])+expect_byte(sy["vi_normal_pending"],0)
        code+=phase1._jp(PASS_PC)
        run_case(root,"pending-normal-escape",code,patch(image,gateway,sy))

        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._call(sy["vi_p905_init_mode"])+phase1._jp_c(FAIL_PC))
        code+=b"\x3E"+bytes((ord("i"),))+phase1._call(sy["vi_p905_key"])+phase1._jp_c(FAIL_PC)
        code+=b"\x3E\x03"+phase1._call(sy["vi_p905_key"])+phase1._jp_c(FAIL_PC)
        code+=expect_byte(sy["vi_editor_mode"],sy["VI_MODE_INSERT"])+expect_byte(CURSOR,1)
        code+=phase1._jp(PASS_PC)
        run_case(root,"break-not-escape",code,patch(image,gateway,sy))

        assertions += [
            {"name":"fuse-normal-insert-escape-golden","passed":True},
            {"name":"fuse-command-line-escape-cancels","passed":True},
            {"name":"fuse-normal-pending-command-escape-cancels","passed":True},
            {"name":"fuse-nonescape-byte-does-not-exit-insert","passed":True},
            {"name":"fuse-escape-does-not-mutate-buffer","passed":True},
        ]

    hashes={
        "tools/vi.asm":sha256_file(source),
        "v1/build/p905-vi.mex1":sha256_file(mex_path),
        "v1/build/p905-vi.tap":sha256_file(tap),
        "v1/tools-host/test-driver/phase9_vi_modes.py":sha256_file(root/"v1/tools-host/test-driver/phase9_vi_modes.py"),
        "v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
        "v1/dist/certification/P9.04.test.json":sha256_file(root/"v1/dist/certification/P9.04.test.json"),
    }
    return [fr,xr,gr],hashes,assertions
