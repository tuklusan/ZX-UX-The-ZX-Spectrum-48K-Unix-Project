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

BASE=0xC000; GATE=0xE000; CURSOR=0xA300; OUT=0xA400
# Exact P9.15 qualification candidate.
class P915Error(DriverError): pass
def require(v,m):
    if not v: raise P915Error(m)
def expect_byte(a,v): return b"\x3A"+word(a)+bytes((0xFE,v&255))+phase1._jp_nz(FAIL_PC)
def expect_word(a,v): return expect_byte(a,v&255)+expect_byte(a+1,(v>>8)&255)
def logical_byte(sy,off,val):
    return phase1._ld_hl(off)+phase1._call(sy["vi_p903_get_byte"])+bytes((0xFE,val&255))+phase1._jp_nz(FAIL_PC)
def patch(image,gateway,sy,data,cursor=0):
    def apply(ram):
        ram[BASE-0x4000:BASE-0x4000+len(image)]=image
        ram[GATE-0x4000:GATE-0x4000+len(gateway)]=gateway
        ram[sy["vi_handle"]-0x4000]=3
        ram[sy["vi_buffer"]-0x4000:sy["vi_buffer"]-0x4000+len(data)]=data
        ram[sy["vi_buffer_len"]-0x4000:sy["vi_buffer_len"]-0x4000+2]=len(data).to_bytes(2,"little")
        ram[sy["vi_cursor_off"]-0x4000:sy["vi_cursor_off"]-0x4000+2]=cursor.to_bytes(2,"little")
    return apply

def dispatch(root,action,step,*,sha256_file,run_command,require_project_tool):
    if step!="P9.15": raise DriverError(step)
    source=root/"tools/vi.asm"; text=source.read_text(encoding="utf-8")
    plan=(root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md").read_text(encoding="utf-8")
    sec=text[text.index("; P9.15"):]
    assertions=[
      {"name":"canonical-p915-present","passed":"## P9.15 - Literal /text search and n/N repeat" in plan},
      {"name":"literal-case-sensitive-compare","passed":"vi_p915_match_at:" in sec and "cp c" in sec},
      {"name":"n-N-distinct","passed":"vi_p915_repeat_same:" in sec and "vi_p915_repeat_opposite:" in sec},
      {"name":"edit-escape-only-1b","passed":"cp VI_ESC" in sec and "cp 3" not in sec},
      {"name":"cancel-preserves-committed-pattern","passed":"vi_p915_cancel:" in sec and "vi_search_pattern" not in sec[sec.index("vi_p915_cancel:"):sec.index("vi_p915_commit:")]},
      {"name":"question-reverse-not-invented","passed":"cp '?'" in sec and "vi_p915_unsupported" in sec},
    ]
    require(all(x["passed"] for x in assertions),"P9.15 static contract failure")
    asm=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus")
    build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    fixture=build/"p915-vi.asm"
    fixture.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../../tools/vi.asm"
    ORG $C000
fixture:
    EMIT_P901_VI_ROUTINES
fixture_end:
    SAVEBIN "p915-vi.bin",fixture,fixture_end-fixture
""",encoding="utf-8",newline="\n")
    fr=run_command([asm,"--nologo","--lst=p915-vi.lst","--sym=p915-vi.sym",fixture.name],cwd=build,timeout_seconds=30)
    require(not fr.timed_out and fr.exit_code==0,f"P9.15 assemble: {fr.stderr or fr.stdout}")
    image=(build/"p915-vi.bin").read_bytes()
    mex_path=build/"p915-vi.mex1"; mex_path.write_bytes(mex1(image))
    try:
        xr=inspect_mex(root,mex_path,run_command,require_project_tool); tap=make_tap(root,build,"vi","p915",mex_path)
    except RuntimeError as exc: raise P915Error(str(exc)) from exc

    gateway_source=build/"p915-gateway.asm"
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
    SAVEBIN "p915-gateway.bin",gate,gate_end-gate
""",encoding="utf-8",newline="\n")
    gr=run_command([asm,"--nologo","--lst=p915-gateway.lst","--sym=p915-gateway.sym",gateway_source.name],cwd=build,timeout_seconds=30)
    require(not gr.timed_out and gr.exit_code==0,f"P9.15 gateway: {gr.stderr or gr.stdout}")

    if action=="test":
        sy=phase3_open_descriptions._symbols(build/"p915-vi.sym",(
          "vi_p903_init","vi_p903_get_byte","vi_p915_begin","vi_p915_input","vi_p915_normal_key",
          "vi_buffer","vi_buffer_len","vi_cursor_off","vi_handle","vi_editor_mode","vi_search_entry",
          "vi_search_edit_len","vi_search_len","vi_search_dir","vi_search_pattern","E_NOENT","E_NOTSUP","VI_MODE_NORMAL",
        ))
        gateway=(build/"p915-gateway.bin").read_bytes()
        data=b"one two one two"
        # /two, n, N exact positions.
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._call(sy["vi_p903_init"])+phase1._jp_c(FAIL_PC))
        code+=phase1._call(sy["vi_p915_begin"])+phase1._jp_c(FAIL_PC)
        for ch in b"two\n": code+=b"\x3E"+bytes((ch,))+phase1._call(sy["vi_p915_input"])+phase1._jp_c(FAIL_PC)
        code+=expect_word(sy["vi_cursor_off"],4)+expect_byte(sy["vi_search_len"],3)
        code+=b"\x3E"+bytes((ord("n"),))+phase1._call(sy["vi_p915_normal_key"])+phase1._jp_c(FAIL_PC)+expect_word(sy["vi_cursor_off"],12)
        code+=b"\x3E"+bytes((ord("N"),))+phase1._call(sy["vi_p915_normal_key"])+phase1._jp_c(FAIL_PC)+expect_word(sy["vi_cursor_off"],4)
        code+=phase1._jp(PASS_PC); run_sna(root,bytes(code),patch=patch(image,gateway,sy,data,0))

        # Cancel unfinished new search: prior pattern/direction/cursor/buffer survive.
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._call(sy["vi_p903_init"])+phase1._jp_c(FAIL_PC))
        code+=phase1._call(sy["vi_p915_begin"])+phase1._jp_c(FAIL_PC)
        for ch in b"two\n": code+=b"\x3E"+bytes((ch,))+phase1._call(sy["vi_p915_input"])+phase1._jp_c(FAIL_PC)
        code+=phase1._call(sy["vi_p915_begin"])+phase1._jp_c(FAIL_PC)
        for ch in b"xy": code+=b"\x3E"+bytes((ch,))+phase1._call(sy["vi_p915_input"])+phase1._jp_c(FAIL_PC)
        code+=b"\x3E\x1B"+phase1._call(sy["vi_p915_input"])+phase1._jp_c(FAIL_PC)
        code+=expect_word(sy["vi_cursor_off"],4)+expect_byte(sy["vi_search_len"],3)+expect_byte(sy["vi_search_dir"],1)+expect_byte(sy["vi_search_entry"],0)+expect_byte(sy["vi_editor_mode"],sy["VI_MODE_NORMAL"])
        for i,v in enumerate(b"two"): code+=expect_byte(sy["vi_search_pattern"]+i,v)
        for i,v in enumerate(data): code+=logical_byte(sy,i,v)
        code+=phase1._jp(PASS_PC); run_sna(root,bytes(code),patch=patch(image,gateway,sy,data,0))

        # Case-sensitive not-found leaves cursor; unsupported ? is not reverse search.
        data2=b"one two"
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._call(sy["vi_p903_init"])+phase1._jp_c(FAIL_PC))
        code+=phase1._call(sy["vi_p915_begin"])+phase1._jp_c(FAIL_PC)
        for ch in b"TWO": code+=b"\x3E"+bytes((ch,))+phase1._call(sy["vi_p915_input"])+phase1._jp_c(FAIL_PC)
        code+=b"\x3E\x0A"+phase1._call(sy["vi_p915_input"])+b"\xD2"+word(FAIL_PC)+b"\xFE"+bytes((sy["E_NOENT"]&255,))+phase1._jp_nz(FAIL_PC)
        code+=expect_word(sy["vi_cursor_off"],0)
        code+=b"\x3E"+bytes((ord("?"),))+phase1._call(sy["vi_p915_normal_key"])+b"\xD2"+word(FAIL_PC)+b"\xFE"+bytes((sy["E_NOTSUP"]&255,))+phase1._jp_nz(FAIL_PC)
        code+=phase1._jp(PASS_PC); run_sna(root,bytes(code),patch=patch(image,gateway,sy,data2,0))

        # Byte 0x03 does not masquerade as EDIT/0x1B.
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._call(sy["vi_p903_init"])+phase1._jp_c(FAIL_PC))
        code+=phase1._call(sy["vi_p915_begin"])+phase1._jp_c(FAIL_PC)+b"\x3E\x03"+phase1._call(sy["vi_p915_input"])+phase1._jp_c(FAIL_PC)
        code+=expect_byte(sy["vi_search_entry"],1)+expect_byte(sy["vi_search_edit_len"],1)+phase1._jp(PASS_PC)
        run_sna(root,bytes(code),patch=patch(image,gateway,sy,data2,0))
        assertions += [
          {"name":"fuse-forward-n-N-golden","passed":True},{"name":"fuse-edit-cancel-preserves-search-and-buffer","passed":True},
          {"name":"fuse-case-sensitive-not-found","passed":True},{"name":"fuse-question-reverse-unsupported","passed":True},
          {"name":"fuse-break-byte-not-edit-alias","passed":True},
        ]
    hashes={
      "tools/vi.asm":sha256_file(source),"v1/build/p915-vi.mex1":sha256_file(mex_path),
      "v1/build/p915-vi.tap":sha256_file(tap),
      "v1/tools-host/test-driver/phase9_vi_search.py":sha256_file(root/"v1/tools-host/test-driver/phase9_vi_search.py"),
      "v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
      "v1/dist/certification/P9.14.test.json":sha256_file(root/"v1/dist/certification/P9.14.test.json"),
    }
    return [fr,xr,gr],hashes,assertions
