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
C_PATH=0xA100; A_PATH=0xA120; T_PATH=0xA140; G_PATH=0xA160
NC_PATH=0xA180; NA_PATH=0xA190; NU_PATH=0xA1A0
COLL=0xA300; FAILW=0xA301; FAILR=0xA302; REMOVES=0xA303; RENAMES=0xA304
LASTN=0xA305; CTYPE=0xA306; WCOUNT=0xA307; TDATA=0xA320

class P917Error(DriverError): pass
def require(v,m):
    if not v: raise P917Error(m)
def expect_byte(a,v): return b"\x3A"+word(a)+bytes((0xFE,v&255))+phase1._jp_nz(FAIL_PC)
def expect_word(a,v): return expect_byte(a,v&255)+expect_byte(a+1,(v>>8)&255)
def patch(image,gateway,sy,data=b"abc",collisions=0,fail_write=0,fail_rename=0):
    def apply(ram):
        ram[BASE-0x4000:BASE-0x4000+len(image)]=image
        ram[GATE-0x4000:GATE-0x4000+len(gateway)]=gateway
        for addr,val in [
            (C_PATH,b"cfile\0"),(A_PATH,b"afile\0"),(T_PATH,b"tfile\0"),(G_PATH,b"gfile\0"),
            (NC_PATH,b"new.c\0"),(NA_PATH,b"new.asm\0"),(NU_PATH,b"new.C\0"),
        ]:
            ram[addr-0x4000:addr-0x4000+len(val)]=val
        ram[sy["vi_buffer"]-0x4000:sy["vi_buffer"]-0x4000+len(data)]=data
        ram[sy["vi_buffer_len"]-0x4000:sy["vi_buffer_len"]-0x4000+2]=len(data).to_bytes(2,"little")
        ram[COLL-0x4000]=collisions
        ram[FAILW-0x4000]=fail_write
        ram[FAILR-0x4000]=fail_rename
        for addr in (REMOVES,RENAMES,LASTN,CTYPE,WCOUNT,WCOUNT+1):
            ram[addr-0x4000]=0
    return apply

def call_write(sy,path,expected_errno=None):
    code=bytearray(phase1._ld_hl(path)+phase1._call(sy["vi_p917_write_path"]))
    if expected_errno is None:
        code+=phase1._jp_c(FAIL_PC)
    else:
        code+=b"\xD2"+word(FAIL_PC)+b"\xFE"+bytes((expected_errno&255,))+phase1._jp_nz(FAIL_PC)
    return code

def dispatch(root,action,step,*,sha256_file,run_command,require_project_tool):
    if step!="P9.17": raise DriverError(step)
    source=root/"tools/vi.asm"; text=source.read_text(encoding="utf-8")
    plan=(root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md").read_text(encoding="utf-8")
    sec=text[text.index("; P9.17"):]
    assertions=[
      {"name":"canonical-p917-present","passed":"## P9.17 - Transactional :w" in plan},
      {"name":"exact-temp-pattern","passed":"vi_temp_name: db '/','t','m','p','/','.','v','i','0','.','0',0" in sec},
      {"name":"exclusive-create","passed":"O_WRITE|O_CREATE|O_EXCL" in sec},
      {"name":"retry-only-exist","passed":"cp E_EXIST" in sec and "cp 9" in sec},
      {"name":"atomic-rename-after-close","passed":sec.index("call vi_p917_close_temp") < sec.index("ld a,SYS_RENAME")},
      {"name":"cleanup-owned-only","passed":"ld a,(vi_temp_owned)" in sec[sec.index("vi_p917_cleanup_error:"):]},
      {"name":"lowercase-suffix-types","passed":all(x in sec for x in ("cp 'c'","cp 'a'","cp 's'","cp 'm'"))},
    ]
    require(all(x["passed"] for x in assertions),"P9.17 static contract failure")
    asm=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus")
    build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    fixture=build/"p917-vi.asm"
    fixture.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../../tools/vi.asm"
    ORG $C000
fixture:
    EMIT_P901_VI_ROUTINES
fixture_end:
    SAVEBIN "p917-vi.bin",fixture,fixture_end-fixture
""",encoding="utf-8",newline="\n")
    fr=run_command([asm,"--nologo","--lst=p917-vi.lst","--sym=p917-vi.sym",fixture.name],cwd=build,timeout_seconds=30)
    require(not fr.timed_out and fr.exit_code==0,f"P9.17 assemble: {fr.stderr or fr.stdout}")
    image=(build/"p917-vi.bin").read_bytes()
    mex_path=build/"p917-vi.mex1"; mex_path.write_bytes(mex1(image))
    try:
        xr=inspect_mex(root,mex_path,run_command,require_project_tool); tap=make_tap(root,build,"vi","p917",mex_path)
    except RuntimeError as exc: raise P917Error(str(exc)) from exc

    gw=build/"p917-gateway.asm"
    gw.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    ORG $E000
gate:
    cp SYS_STAT
    jr z,g_stat
    cp SYS_GETPID
    jr z,g_pid
    cp SYS_OPEN
    jr z,g_open
    cp SYS_WRITE
    jr z,g_write
    cp SYS_CLOSE
    jr z,g_close
    cp SYS_RENAME
    jr z,g_rename
    cp SYS_REMOVE
    jr z,g_remove
    ld a,E_NOTSUP
    scf
    ret
g_pid:
    ld hl,3
    xor a
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
    cp 'c'
    jr z,g_stat_c
    cp 'a'
    jr z,g_stat_asm
    cp 't'
    jr z,g_stat_txt
    cp 'g'
    jr z,g_stat_cfg
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
    jr g_stat_store
g_stat_cfg:
    ld a,OBJ_CFG
g_stat_store:
    ld (bc),a
    xor a
    ret
g_open:
    push bc
    ld de,10
    add hl,de
    ld a,(hl)
    sub '0'
    ld ($A305),a
    ld d,a
    ld a,($A300)
    cp d
    jr z,g_open_success
    jr c,g_open_success
    pop bc
    ld a,E_EXIST
    scf
    ret
g_open_success:
    pop bc
    ld a,b
    ld ($A306),a
    ld hl,7
    xor a
    ret
g_write:
    ld a,($A301)
    or a
    jr nz,g_write_fail
    ld a,($A307)
    ld e,a
    ld d,0
    push hl
    ld hl,$A320
    add hl,de
    ex de,hl
    pop hl
    ld a,(hl)
    ld (de),a
    ld hl,($A307)
    inc hl
    ld ($A307),hl
    ld hl,1
    xor a
    ret
g_write_fail:
    ld a,E_IO
    scf
    ret
g_close:
    xor a
    ret
g_rename:
    ld a,($A302)
    or a
    jr nz,g_rename_fail
    ld a,($A304)
    inc a
    ld ($A304),a
    xor a
    ret
g_rename_fail:
    ld a,E_IO
    scf
    ret
g_remove:
    ld a,($A303)
    inc a
    ld ($A303),a
    xor a
    ret
gate_end:
    SAVEBIN "p917-gateway.bin",gate,gate_end-gate
""",encoding="utf-8",newline="\n")
    gr=run_command([asm,"--nologo","--lst=p917-gateway.lst","--sym=p917-gateway.sym",gw.name],cwd=build,timeout_seconds=30)
    require(not gr.timed_out and gr.exit_code==0,f"P9.17 gateway: {gr.stderr or gr.stdout}")

    if action=="test":
        sy=phase3_open_descriptions._symbols(build/"p917-vi.sym",(
          "vi_p903_init","vi_p917_write_path","vi_buffer","vi_buffer_len",
          "E_EXIST","E_IO","OBJ_C","OBJ_ASM","OBJ_TXT","OBJ_CFG",
        ))
        gateway=(build/"p917-gateway.bin").read_bytes()
        # n=0..8 collide; n=9 succeeds. Unknown collisions are never removed.
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._call(sy["vi_p903_init"])+phase1._jp_c(FAIL_PC))
        code+=call_write(sy,NC_PATH)
        code+=expect_byte(LASTN,9)+expect_byte(CTYPE,sy["OBJ_C"])+expect_word(WCOUNT,3)
        for i,v in enumerate(b"abc"): code+=expect_byte(TDATA+i,v)
        code+=expect_byte(RENAMES,1)+expect_byte(REMOVES,0)+phase1._jp(PASS_PC)
        run_sna(root,bytes(code),patch=patch(image,gateway,sy,collisions=9))
        # All ten collide -> controlled E_EXIST, no remove/rename.
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._call(sy["vi_p903_init"])+phase1._jp_c(FAIL_PC))
        code+=call_write(sy,NC_PATH,sy["E_EXIST"])+expect_byte(LASTN,9)+expect_byte(RENAMES,0)+expect_byte(REMOVES,0)+phase1._jp(PASS_PC)
        run_sna(root,bytes(code),patch=patch(image,gateway,sy,collisions=10))
        # Write and rename failures clean only owned temp.
        for fw,frn in ((1,0),(0,1)):
            code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._call(sy["vi_p903_init"])+phase1._jp_c(FAIL_PC))
            code+=call_write(sy,NC_PATH,sy["E_IO"])+expect_byte(RENAMES,0 if fw else 0)+expect_byte(REMOVES,1)+phase1._jp(PASS_PC)
            run_sna(root,bytes(code),patch=patch(image,gateway,sy,fail_write=fw,fail_rename=frn))
        # Preserve existing object types.
        for path,typ in ((C_PATH,sy["OBJ_C"]),(A_PATH,sy["OBJ_ASM"]),(T_PATH,sy["OBJ_TXT"]),(G_PATH,sy["OBJ_CFG"])):
            code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._call(sy["vi_p903_init"])+phase1._jp_c(FAIL_PC))
            code+=call_write(sy,path)+expect_byte(CTYPE,typ)+phase1._jp(PASS_PC)
            run_sna(root,bytes(code),patch=patch(image,gateway,sy))
        # New suffix selection is exact/lower-case.
        for path,typ in ((NC_PATH,sy["OBJ_C"]),(NA_PATH,sy["OBJ_ASM"]),(NU_PATH,sy["OBJ_TXT"])):
            code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._call(sy["vi_p903_init"])+phase1._jp_c(FAIL_PC))
            code+=call_write(sy,path)+expect_byte(CTYPE,typ)+phase1._jp(PASS_PC)
            run_sna(root,bytes(code),patch=patch(image,gateway,sy))
        assertions += [
          {"name":"fuse-collisions-0-through-8-then-9","passed":True},{"name":"fuse-all-ten-collisions-no-remove","passed":True},
          {"name":"fuse-write-rename-failure-owned-cleanup","passed":True},{"name":"fuse-existing-type-preservation","passed":True},
          {"name":"fuse-new-suffix-type-selection","passed":True},
        ]
    hashes={
      "tools/vi.asm":sha256_file(source),"v1/build/p917-vi.mex1":sha256_file(mex_path),
      "v1/build/p917-vi.tap":sha256_file(tap),
      "v1/tools-host/test-driver/phase9_vi_write_tx.py":sha256_file(root/"v1/tools-host/test-driver/phase9_vi_write_tx.py"),
      "v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
      "v1/dist/certification/P9.16.test.json":sha256_file(root/"v1/dist/certification/P9.16.test.json"),
    }
    return [fr,xr,gr],hashes,assertions
