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

BASE=0xC000; GATE=0xE000
CALLS=0xA300; LASTROW=0xA301; LASTCOL=0xA302; LASTBYTE=0xA303
CANARY0=0xA304; CANARY1=0xA305
# Exact P9.22 candidate.

class P922Error(DriverError): pass
def require(v,m):
    if not v: raise P922Error(m)
def expect_byte(a,v): return b"\x3A"+word(a)+bytes((0xFE,v&255))+phase1._jp_nz(FAIL_PC)
def expect_word(a,v): return expect_byte(a,v&255)+expect_byte(a+1,(v>>8)&255)
def run_case(root,name,code,patcher):
    try:
        run_sna(root,bytes(code),patch=patcher)
    except DriverError as exc:
        raise P922Error(f"P9.22 {name}: {exc}") from exc

def patch(image,gate,sy,data,cursor=0,xoff=0,number=0):
    def apply(ram):
        ram[BASE-0x4000:BASE-0x4000+len(image)]=image
        ram[GATE-0x4000:GATE-0x4000+len(gate)]=gate
        ram[sy["vi_buffer"]-0x4000:sy["vi_buffer"]-0x4000+len(data)]=data
        ram[sy["vi_buffer_len"]-0x4000:sy["vi_buffer_len"]-0x4000+2]=len(data).to_bytes(2,"little")
        ram[sy["vi_cursor_off"]-0x4000:sy["vi_cursor_off"]-0x4000+2]=cursor.to_bytes(2,"little")
        ram[sy["vi_view_xoff"]-0x4000:sy["vi_view_xoff"]-0x4000+2]=xoff.to_bytes(2,"little")
        ram[sy["vi_option_number"]-0x4000]=number
        ram[sy["vi_view_gutter"]-0x4000]=5 if number else 0
        ram[sy["vi_view_width"]-0x4000]=59 if number else 64
        ram[CALLS-0x4000]=0; ram[LASTROW-0x4000]=0; ram[LASTCOL-0x4000]=0; ram[LASTBYTE-0x4000]=0
        ram[CANARY0-0x4000]=0xA5; ram[CANARY1-0x4000]=0x5A
    return apply

def dispatch(root,action,step,*,sha256_file,run_command,require_project_tool):
    if step!="P9.22": raise DriverError(step)
    source=root/"tools/vi.asm"; text=source.read_text(encoding="utf-8")
    plan=(root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md").read_text(encoding="utf-8")
    assertions=[
      {"name":"canonical-p922-present","passed":"## P9.22 - tty64 viewport and column-63 safety" in plan},
      {"name":"edit-rows-0-22","passed":"VI_EDIT_LAST_ROW        EQU 22" in text},
      {"name":"hard-col63","passed":"VI_TTY_LAST_COL         EQU 63" in text},
      {"name":"central-safe-emitter","passed":"vi_p922_emit_at:" in text and "cp VI_TTY_LAST_COL+1" in text},
      {"name":"tab-storage-independent","passed":"cp 9" in text[text.index("vi_p922_cursor_column:"):] and "ld a,' '" in text[text.index("vi_p922_render_cell:"):]},
      {"name":"horizontal-offset-state","passed":"vi_view_xoff: dw 0" in text and "vi_p922_follow_cursor:" in text},
      {"name":"negative-col64-oracle","passed":"vi_p922_probe_col64:" in text and "ld e,64" in text[text.index("vi_p922_probe_col64:"):]},
    ]
    require(all(x["passed"] for x in assertions),"P9.22 static contract failure")

    asm=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus")
    build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    fx=build/"p922-vi.asm"
    fx.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../../tools/vi.asm"
    ORG $C000
fixture:
    EMIT_P901_VI_ROUTINES
fixture_end:
    SAVEBIN "p922-vi.bin",fixture,fixture_end-fixture
""",encoding="utf-8",newline="\n")
    fr=run_command([asm,"--nologo","--lst=p922-vi.lst","--sym=p922-vi.sym",fx.name],cwd=build,timeout_seconds=30)
    require(not fr.timed_out and fr.exit_code==0,f"P9.22 assemble: {fr.stderr or fr.stdout}")
    image=(build/"p922-vi.bin").read_bytes()
    mex_path=build/"p922-vi.mex1"; mex_path.write_bytes(mex1(image))
    try:
        xr=inspect_mex(root,mex_path,run_command,require_project_tool); tap=make_tap(root,build,"vi","p922",mex_path)
    except RuntimeError as exc: raise P922Error(str(exc)) from exc

    gw=build/"p922-gateway.asm"
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
    ld a,l
    cp 64
    jr nc,g_bad
    ld a,h
    cp 24
    jr nc,g_bad
    ld ($A301),a
    ld a,l
    ld ($A302),a
    ld a,($A300)
    inc a
    ld ($A300),a
    xor a
    ret
g_write:
    ld a,($A302)
    cp 64
    jr nc,g_bad
    ld a,(hl)
    ld ($A303),a
    ld a,($A300)
    inc a
    ld ($A300),a
    xor a
    ret
g_bad:
    ld a,E_INVAL
    scf
    ret
gate_end:
    SAVEBIN "p922-gateway.bin",gate,gate_end-gate
""",encoding="utf-8",newline="\n")
    gr=run_command([asm,"--nologo","--lst=p922-gateway.lst","--sym=p922-gateway.sym",gw.name],cwd=build,timeout_seconds=30)
    require(not gr.timed_out and gr.exit_code==0,f"P9.22 gateway: {gr.stderr or gr.stdout}")

    if action=="test":
        sy=phase3_open_descriptions._symbols(build/"p922-vi.sym",(
          "vi_p903_init","vi_p903_get_byte","vi_p922_cursor_column","vi_p922_follow_cursor","vi_p922_screen_col",
          "vi_p922_emit_at","vi_p922_render_cell","vi_p922_probe_col64","vi_buffer","vi_buffer_len",
          "vi_cursor_off","vi_view_xoff","vi_p922_scan_off","vi_p922_logical_col","vi_option_number","vi_view_gutter","vi_view_width","E_INVAL",
        ))
        gate=(build/"p922-gateway.bin").read_bytes()
        require(len(image) <= 8192, f"P9.22 vi image exceeds 8192 bytes: {len(image)}")


        # TAB is one file byte yet advances display column to the next multiple of eight.
        data=b"a\tb"
        # Confirm the logical-byte prerequisite seen by the column scanner.
        for off,val,label in ((0,ord("a"),"tab-byte0"),(1,9,"tab-byte1")):
            code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._call(sy["vi_p903_init"])+phase1._jp_c(FAIL_PC)+phase1._ld_hl(off)+phase1._call(sy["vi_p903_get_byte"])+bytes((0xFE,val))+phase1._jp_nz(FAIL_PC)+phase1._jp(PASS_PC))
            run_case(root,label,code,patch(image,gate,sy,data,cursor=2))

        # Cursor starts at supplied offset 2; prove state before and after the column scan.
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._call(sy["vi_p903_init"])+phase1._jp_c(FAIL_PC)+b"\x21\x02\x00\x22"+word(sy["vi_cursor_off"])+expect_word(sy["vi_cursor_off"],2)+phase1._jp(PASS_PC))
        run_case(root,"cursor-before-column-scan",code,patch(image,gate,sy,data,cursor=2))
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._call(sy["vi_p903_init"])+phase1._jp_c(FAIL_PC)+b"\x21\x02\x00\x22"+word(sy["vi_cursor_off"])+phase1._call(sy["vi_p922_cursor_column"])+expect_word(sy["vi_cursor_off"],2)+phase1._jp(PASS_PC))
        run_case(root,"cursor-after-column-scan",code,patch(image,gate,sy,data,cursor=2))
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._call(sy["vi_p903_init"])+phase1._jp_c(FAIL_PC)+expect_word(sy["vi_buffer_len"],3)+phase1._jp(PASS_PC))
        run_case(root,"buffer-len-after-init",code,patch(image,gate,sy,data,cursor=2))
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._call(sy["vi_p903_init"])+phase1._jp_c(FAIL_PC)+b"\x21\x02\x00\x22"+word(sy["vi_cursor_off"])+phase1._call(sy["vi_p922_cursor_column"]))
        code+=expect_word(sy["vi_p922_scan_off"],2)+expect_word(sy["vi_p922_logical_col"],8)+b"\x7C\xB5"+phase1._jp_z(FAIL_PC)+expect_byte(sy["vi_p922_logical_col"],8)+phase1._jp(PASS_PC)
        run_case(root,"tab-column-scan",code,patch(image,gate,sy,data,cursor=2))

        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._call(sy["vi_p903_init"])+phase1._jp_c(FAIL_PC))
        code+=expect_byte(sy["vi_buffer"]+1,9)+phase1._jp(PASS_PC)
        run_case(root,"tab-byte-preserved",code,patch(image,gate,sy,data,cursor=2))

        # Unnumbered: logical column 69 scrolls to xoff 6, landing at screen column 63.
        data=b"x"*70
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._call(sy["vi_p903_init"])+phase1._jp_c(FAIL_PC)+b"\x21\x45\x00\x22"+word(sy["vi_cursor_off"])+phase1._call(sy["vi_p922_follow_cursor"])+phase1._jp_c(FAIL_PC))
        code+=expect_word(sy["vi_view_xoff"],6)+phase1._ld_hl(69)+phase1._call(sy["vi_p922_screen_col"])+phase1._jp_c(FAIL_PC)
        code+=b"\x7D\xFE\x3F"+phase1._jp_nz(FAIL_PC)+phase1._jp(PASS_PC)
        run_case(root,"unnumbered-follow",code,patch(image,gate,sy,data,cursor=69))

        # Numbered: width 59 plus five-column gutter still lands at column 63.
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._call(sy["vi_p903_init"])+phase1._jp_c(FAIL_PC)+phase1._call(sy["vi_p922_follow_cursor"])+phase1._jp_c(FAIL_PC))
        code+=expect_word(sy["vi_view_xoff"],11)+phase1._ld_hl(69)+phase1._call(sy["vi_p922_screen_col"])+phase1._jp_c(FAIL_PC)
        code+=b"\x7D\xFE\x3F"+phase1._jp_nz(FAIL_PC)+phase1._jp(PASS_PC)
        run_case(root,"numbered-follow",code,patch(image,gate,sy,data,cursor=69,number=1))

        # Exact edge row22/col63 may write; canaries remain intact.
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+b"\x16\x16\x1E\x3F\x3E\x5A"+phase1._call(sy["vi_p922_emit_at"])+phase1._jp_c(FAIL_PC))
        code+=expect_byte(CALLS,2)+expect_byte(LASTROW,22)+expect_byte(LASTCOL,63)+expect_byte(LASTBYTE,0x5A)+expect_byte(CANARY0,0xA5)+expect_byte(CANARY1,0x5A)+phase1._jp(PASS_PC)
        run_case(root,"edge-oracle",code,patch(image,gate,sy,b""))

        # Instrumented column64 attempt must be rejected before either terminal syscall.
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._call(sy["vi_p922_probe_col64"]))
        code+=b"\xD2"+word(FAIL_PC)+b"\xFE"+bytes((sy["E_INVAL"]&255,))+phase1._jp_nz(FAIL_PC)+expect_byte(CALLS,0)+expect_byte(CANARY0,0xA5)+expect_byte(CANARY1,0x5A)+phase1._jp(PASS_PC)
        run_case(root,"col64-negative",code,patch(image,gate,sy,b""))

        # Row23 is status-only and cannot be reached by edit rendering.
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+b"\x16\x17\x1E\x00\x3E\x58"+phase1._call(sy["vi_p922_emit_at"]))
        code+=b"\xD2"+word(FAIL_PC)+expect_byte(CALLS,0)+phase1._jp(PASS_PC)
        run_case(root,"row23-negative",code,patch(image,gate,sy,b""))

        # Rendering a TAB emits a space but does not rewrite stored 0x09.
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._ld_hl(8)+b"\x16\x00\x3E\x09"+phase1._call(sy["vi_p922_render_cell"])+phase1._jp_c(FAIL_PC))
        code+=expect_byte(LASTCOL,8)+expect_byte(LASTBYTE,ord(" "))+expect_byte(sy["vi_buffer"],9)+phase1._jp(PASS_PC)
        run_case(root,"tab-render",code,patch(image,gate,sy,b"\t"))

        assertions += [
          {"name":"fuse-tab-logical-column-exact","passed":True},
          {"name":"fuse-horizontal-follow-64-columns","passed":True},
          {"name":"fuse-number-gutter-exact-five-columns","passed":True},
          {"name":"fuse-row22-col63-safe-canaries","passed":True},
          {"name":"fuse-instrumented-col64-rejected-before-write","passed":True},
          {"name":"fuse-row23-edit-write-rejected","passed":True},
          {"name":"fuse-tab-render-does-not-mutate-byte","passed":True},
        ]

    hashes={
      "tools/vi.asm":sha256_file(source),
      "v1/build/p922-vi.mex1":sha256_file(mex_path),
      "v1/build/p922-vi.tap":sha256_file(tap),
      "v1/tools-host/test-driver/phase9_vi_viewport.py":sha256_file(root/"v1/tools-host/test-driver/phase9_vi_viewport.py"),
      "v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
      "v1/dist/certification/P9.21.test.json":sha256_file(root/"v1/dist/certification/P9.21.test.json"),
    }
    return [fr,xr,gr],hashes,assertions
