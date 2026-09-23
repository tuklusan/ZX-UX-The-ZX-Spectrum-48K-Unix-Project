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

BASE=0xC000; GATE=0xE000; PATH1=0xA100; PATH2=0xA120; PATH3=0xA140
# Exact P9.16 qualification candidate.
class P916Error(DriverError): pass
def require(v,m):
    if not v: raise P916Error(m)
def expect_byte(a,v): return b"\x3A"+word(a)+bytes((0xFE,v&255))+phase1._jp_nz(FAIL_PC)
def expect_word(a,v): return expect_byte(a,v&255)+expect_byte(a+1,(v>>8)&255)
def logical_byte(sy,off,val):
    return phase1._ld_hl(off)+phase1._call(sy["vi_p903_get_byte"])+bytes((0xFE,val&255))+phase1._jp_nz(FAIL_PC)
def patch(image,gateway,sy,data=b"old\n",cursor=0,dirty=0,named=1,target=b"orig.c"):
    def apply(ram):
        ram[BASE-0x4000:BASE-0x4000+len(image)]=image
        ram[GATE-0x4000:GATE-0x4000+len(gateway)]=gateway
        ram[PATH1-0x4000:PATH1-0x4000+8]=b"hello.c\0"
        ram[PATH2-0x4000:PATH2-0x4000+8]=b"HELLO.C\0"
        ram[PATH3-0x4000:PATH3-0x4000+7]=b"read.c\0"
        ram[sy["vi_buffer"]-0x4000:sy["vi_buffer"]-0x4000+len(data)]=data
        ram[sy["vi_buffer_len"]-0x4000:sy["vi_buffer_len"]-0x4000+2]=len(data).to_bytes(2,"little")
        ram[sy["vi_cursor_off"]-0x4000:sy["vi_cursor_off"]-0x4000+2]=cursor.to_bytes(2,"little")
        ram[sy["vi_dirty"]-0x4000]=dirty
        ram[sy["vi_named"]-0x4000]=named
        ram[sy["vi_target"]-0x4000:sy["vi_target"]-0x4000+len(target)+1]=target+b"\0"
    return apply

def dispatch(root,action,step,*,sha256_file,run_command,require_project_tool):
    if step!="P9.16": raise DriverError(step)
    source=root/"tools/vi.asm"; text=source.read_text(encoding="utf-8")
    plan=(root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md").read_text(encoding="utf-8")
    sec=text[text.index("; P9.16"):]
    assertions=[
      {"name":"canonical-p916-present","passed":"## P9.16 - Ex :e and :r" in plan},
      {"name":"dirty-e-refusal","passed":"ld a,E_BUSY" in sec[sec.index("vi_p916_e:"):sec.index("vi_p916_e_clean:")]},
      {"name":"staging-before-live-copy","passed":sec.index("call vi_p916_stage_load") < sec.index("ld de,vi_buffer")},
      {"name":"r-never-retargets","passed":"vi_p904_commit_target" not in sec[sec.index("vi_p916_r:"):sec.index("vi_p916_r_preflight:")]},
      {"name":"editable-types-only","passed":all(x in sec for x in ("cp OBJ_TXT","cp OBJ_C","cp OBJ_ASM","cp OBJ_CFG"))},
    ]
    require(all(x["passed"] for x in assertions),"P9.16 static contract failure")
    asm=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus")
    build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    fixture=build/"p916-vi.asm"
    fixture.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../../tools/vi.asm"
    ORG $C000
fixture:
    EMIT_P901_VI_ROUTINES
fixture_end:
    SAVEBIN "p916-vi.bin",fixture,fixture_end-fixture
""",encoding="utf-8",newline="\n")
    fr=run_command([asm,"--nologo","--lst=p916-vi.lst","--sym=p916-vi.sym",fixture.name],cwd=build,timeout_seconds=30)
    require(not fr.timed_out and fr.exit_code==0,f"P9.16 assemble: {fr.stderr or fr.stdout}")
    image=(build/"p916-vi.bin").read_bytes()
    mex_path=build/"p916-vi.mex1"; mex_path.write_bytes(mex1(image))
    try:
        xr=inspect_mex(root,mex_path,run_command,require_project_tool); tap=make_tap(root,build,"vi","p916",mex_path)
    except RuntimeError as exc: raise P916Error(str(exc)) from exc

    gw=build/"p916-gateway.asm"
    gw.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    ORG $E000
gate:
    cp SYS_STAT
    jr z,g_stat
    cp SYS_OPEN
    jr z,g_open
    cp SYS_READ
    jr z,g_read
    cp SYS_CLOSE
    jr z,g_close
    ld a,E_NOTSUP
    scf
    ret
g_stat:
    ld e,(hl)
    inc hl
    ld d,(hl)
    inc hl
    ld c,(hl)
    inc hl
    ld b,(hl)
    ld a,(de)
    cp 'x'
    jr z,g_noent
    cp 'H'
    jr z,g_stat_asm
    cp 'h'
    jr z,g_stat_c
    cp 'r'
    jr z,g_stat_txt
g_noent:
    ld a,E_NOENT
    scf
    ret
g_stat_c:
    ld a,OBJ_C
    jr g_stat_store
g_stat_asm:
    ld a,OBJ_ASM
    jr g_stat_store
g_stat_txt:
    ld a,OBJ_TXT
g_stat_store:
    ld (bc),a
    xor a
    ret
g_open:
    ld a,(hl)
    ld ($A200),a
    xor a
    ld ($A201),a
    ld hl,5
    ret
g_read:
    ld a,($A201)
    or a
    jr nz,g_read_eof
    inc a
    ld ($A201),a
    ld a,($A200)
    cp 'H'
    jr z,g_read_upper
    cp 'h'
    jr z,g_read_lower
    ld de,g_data_read
    ld bc,3
    jr g_read_copy
g_read_upper:
    ld de,g_data_upper
    ld bc,6
    jr g_read_copy
g_read_lower:
    ld de,g_data_lower
    ld bc,6
g_read_copy:
    push bc
g_read_copy_loop:
    ld a,(de)
    ld (hl),a
    inc de
    inc hl
    dec bc
    ld a,b
    or c
    jr nz,g_read_copy_loop
    pop hl
    xor a
    ret
g_read_eof:
    ld hl,0
    xor a
    ret
g_close:
    xor a
    ret
g_data_lower: db 'l','o','w','e','r',10
g_data_upper: db 'U','P','P','E','R',10
g_data_read:  db 'Z','Z',10
gate_end:
    SAVEBIN "p916-gateway.bin",gate,gate_end-gate
""",encoding="utf-8",newline="\n")
    gr=run_command([asm,"--nologo","--lst=p916-gateway.lst","--sym=p916-gateway.sym",gw.name],cwd=build,timeout_seconds=30)
    require(not gr.timed_out and gr.exit_code==0,f"P9.16 gateway: {gr.stderr or gr.stdout}")

    if action=="test":
        sy=phase3_open_descriptions._symbols(build/"p916-vi.sym",(
          "vi_p903_init","vi_p903_get_byte","vi_p916_e","vi_p916_r","vi_buffer","vi_buffer_len",
          "vi_cursor_off","vi_dirty","vi_named","vi_target","vi_target_type","E_BUSY","OBJ_C","OBJ_ASM",
        ))
        gateway=(build/"p916-gateway.bin").read_bytes()
        # :e lower-case path.
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._call(sy["vi_p903_init"])+phase1._jp_c(FAIL_PC))
        code+=phase1._ld_hl(PATH1)+phase1._call(sy["vi_p916_e"])+phase1._jp_c(FAIL_PC)
        code+=expect_word(sy["vi_buffer_len"],6)+expect_byte(sy["vi_target_type"],sy["OBJ_C"])+expect_byte(sy["vi_dirty"],0)
        for i,v in enumerate(b"lower\n"): code+=logical_byte(sy,i,v)
        for i,v in enumerate(b"hello.c\0"): code+=expect_byte(sy["vi_target"]+i,v)
        code+=phase1._jp(PASS_PC); run_sna(root,bytes(code),patch=patch(image,gateway,sy))
        # Exact case differs.
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._call(sy["vi_p903_init"])+phase1._jp_c(FAIL_PC))
        code+=phase1._ld_hl(PATH2)+phase1._call(sy["vi_p916_e"])+phase1._jp_c(FAIL_PC)
        code+=expect_byte(sy["vi_target_type"],sy["OBJ_ASM"])
        for i,v in enumerate(b"UPPER\n"): code+=logical_byte(sy,i,v)
        code+=phase1._jp(PASS_PC); run_sna(root,bytes(code),patch=patch(image,gateway,sy))
        # Dirty :e refuses without changing bytes/target.
        old=b"old\n"
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._call(sy["vi_p903_init"])+phase1._jp_c(FAIL_PC))
        code+=b"\x3E\x01\x32"+word(sy["vi_dirty"])+phase1._ld_hl(PATH1)+phase1._call(sy["vi_p916_e"])
        code+=b"\xD2"+word(FAIL_PC)+b"\xFE"+bytes((sy["E_BUSY"]&255,))+phase1._jp_nz(FAIL_PC)
        for i,v in enumerate(old): code+=logical_byte(sy,i,v)
        for i,v in enumerate(b"orig.c\0"): code+=expect_byte(sy["vi_target"]+i,v)
        code+=phase1._jp(PASS_PC); run_sna(root,bytes(code),patch=patch(image,gateway,sy,old,dirty=1))
        # :r exact bytes after current line, dirty, no retarget.
        data=b"aa\nbb\n"
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._call(sy["vi_p903_init"])+phase1._jp_c(FAIL_PC))
        code+=phase1._ld_hl(PATH3)+phase1._call(sy["vi_p916_r"])+phase1._jp_c(FAIL_PC)
        for i,v in enumerate(b"aa\nZZ\nbb\n"): code+=logical_byte(sy,i,v)
        code+=expect_byte(sy["vi_dirty"],1)
        for i,v in enumerate(b"orig.c\0"): code+=expect_byte(sy["vi_target"]+i,v)
        code+=phase1._jp(PASS_PC); run_sna(root,bytes(code),patch=patch(image,gateway,sy,data,0))
        assertions += [
          {"name":"fuse-e-case-sensitive-golden","passed":True},{"name":"fuse-dirty-e-refuses-preserves","passed":True},
          {"name":"fuse-r-inserts-exact-no-retarget","passed":True},
        ]
    hashes={
      "tools/vi.asm":sha256_file(source),"v1/build/p916-vi.mex1":sha256_file(mex_path),
      "v1/build/p916-vi.tap":sha256_file(tap),
      "v1/tools-host/test-driver/phase9_vi_ex_read.py":sha256_file(root/"v1/tools-host/test-driver/phase9_vi_ex_read.py"),
      "v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
      "v1/dist/certification/P9.15.test.json":sha256_file(root/"v1/dist/certification/P9.15.test.json"),
    }
    return [fr,xr,gr],hashes,assertions
