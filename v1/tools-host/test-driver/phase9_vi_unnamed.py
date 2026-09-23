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
from phase8_common import arg1, inspect_mex, make_tap, mex1, word

# Exact P9.04 candidate driver.
BASE=0xC000
GATE=0xE000
ARG=0xA000
TYPE=0xA300
OUT=0xA400
READ_DONE=0xA500


class P904Error(DriverError):
    pass


def require(value,message):
    if not value:
        raise P904Error(message)


def expect_byte(address,value):
    return b"\x3A"+word(address)+bytes((0xFE,value&0xFF))+phase1._jp_nz(FAIL_PC)


def expect_word(address,value):
    return expect_byte(address,value&0xFF)+expect_byte(address+1,(value>>8)&0xFF)


def run_case(root,name,code,patcher):
    try:
        run_sna(root,bytes(code),patch=patcher)
    except DriverError as exc:
        raise P904Error(f"P9.04 {name}: {exc}") from exc


def patch(image,gateway,args,type_id=1):
    block=arg1(args)
    def apply(ram):
        ram[BASE-0x4000:BASE-0x4000+len(image)]=image
        ram[GATE-0x4000:GATE-0x4000+len(gateway)]=gateway
        ram[ARG-0x4000:ARG-0x4000+len(block)]=block
        ram[TYPE-0x4000]=type_id
        ram[OUT-0x4000:OUT-0x4000+64]=b"\xA5"*64
        ram[READ_DONE-0x4000]=0
    return apply


def dispatch(root,action,step,*,sha256_file,run_command,require_project_tool):
    if step!="P9.04":
        raise DriverError(step)
    source=root/"tools/vi.asm"
    text=source.read_text(encoding="utf-8")
    plan=(root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md").read_text(encoding="utf-8")
    assertions=[
        {"name":"canonical-p904-present","passed":"## P9.04 - Unnamed/new buffer state" in plan},
        {"name":"exact-argc-one-or-two","passed":"cp 1" in text[text.index("vi_p904_invocation:"):text.index("vi_p904_new:")] and "cp 2" in text[text.index("vi_p904_invocation:"):text.index("vi_p904_new:")]},
        {"name":"unnamed-default-txt","passed":"ld a,OBJ_TXT" in text[text.index("vi_p904_new:"):text.index("vi_p904_invalid:")]},
        {"name":"failed-write-does-not-retarget","passed":"vi_p904_failed_write:" in text and "ld (vi_named)" not in text[text.index("vi_p904_failed_write:"):text.index("vi_p904_require_target:")]},
        {"name":"exact-no-file-name-message","passed":"vi_no_name_msg: db 'v','i',':',' ','n','o',' ','f','i','l','e',' ','n','a','m','e',10" in text},
        {"name":"target-commit-clears-dirty","passed":"vi_p904_commit_target:" in text and "ld (vi_dirty),a" in text[text.index("vi_p904_commit_target:"):text.index("vi_p904_failed_write:")]},
    ]
    require(all(x["passed"] for x in assertions),"P9.04 static contract failure")

    assembler=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus")
    build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    fixture=build/"p904-vi.asm"
    fixture.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../../tools/vi.asm"
    ORG $C000
fixture:
    EMIT_P901_VI_ROUTINES
fixture_end:
    SAVEBIN "p904-vi.bin",fixture,fixture_end-fixture
""",encoding="utf-8",newline="\n")
    fr=run_command([assembler,"--nologo","--lst=p904-vi.lst","--sym=p904-vi.sym",fixture.name],cwd=build,timeout_seconds=30)
    require(not fr.timed_out and fr.exit_code==0,f"P9.04 assemble: {fr.stderr or fr.stdout}")
    image=(build/"p904-vi.bin").read_bytes()
    mex_path=build/"p904-vi.mex1"; mex_path.write_bytes(mex1(image))
    try:
        xr=inspect_mex(root,mex_path,run_command,require_project_tool)
        tap=make_tap(root,build,"vi","p904",mex_path)
    except RuntimeError as exc:
        raise P904Error(str(exc)) from exc

    gateway_source=build/"p904-gateway.asm"
    gateway_source.write_text("""    DEVICE ZXSPECTRUM48
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
    cp SYS_WRITE
    jr z,g_write
    ld a,E_NOTSUP
    scf
    ret
g_stat:
    inc hl
    inc hl
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld a,($A300)
    ld (de),a
    inc de
    xor a
    ld b,9
g_zero:
    ld (de),a
    inc de
    djnz g_zero
    xor a
    ret
g_open:
    ld hl,3
    xor a
    ret
g_read:
    ld a,($A500)
    or a
    jr nz,g_eof
    ld de,g_data
    ex de,hl
    ld bc,4
    ldir
    ld a,1
    ld ($A500),a
    ld hl,4
    xor a
    ret
g_eof:
    ld hl,0
    xor a
    ret
g_close:
    xor a
    ret
g_write:
    ld a,e
    cp 1
    jr nz,g_bad
    ld a,d
    or a
    jr nz,g_bad
    ld de,$A400
    ldir
    ld h,b
    ld l,c
    xor a
    ret
g_bad:
    ld a,E_INVAL
    scf
    ret
g_data: db 'a','b','c',10
gate_end:
    SAVEBIN "p904-gateway.bin",gate,gate_end-gate
""",encoding="utf-8",newline="\n")
    gr=run_command([assembler,"--nologo","--lst=p904-gateway.lst","--sym=p904-gateway.sym",gateway_source.name],cwd=build,timeout_seconds=30)
    require(not gr.timed_out and gr.exit_code==0,f"P9.04 gateway: {gr.stderr or gr.stdout}")

    if action=="test":
        sy=phase3_open_descriptions._symbols(build/"p904-vi.sym",(
            "vi_p904_invocation","vi_p904_require_target","vi_p904_failed_write","vi_p904_commit_target",
            "vi_named","vi_target_type","vi_target","vi_dirty","vi_buffer_len","vi_buffer_ready",
            "vi_line_count","vi_gap_start","vi_source_open","OBJ_TXT","OBJ_C","E_INVAL","E_NOENT","E_IO",
        ))
        gateway=(build/"p904-gateway.bin").read_bytes()

        block=arg1([b"vi"])
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._ld_hl(ARG)+phase1._call(sy["vi_p904_invocation"])+phase1._jp_c(FAIL_PC))
        code+=expect_byte(sy["vi_named"],0)+expect_byte(sy["vi_target_type"],sy["OBJ_TXT"])+expect_byte(sy["vi_dirty"],0)
        code+=expect_word(sy["vi_buffer_len"],0)+expect_byte(sy["vi_buffer_ready"],1)+expect_byte(sy["vi_line_count"],1)+expect_word(sy["vi_gap_start"],0)
        code+=phase1._jp(PASS_PC)
        run_case(root,"unnamed-empty",code,patch(image,gateway,[b"vi"],sy["OBJ_TXT"]))

        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._ld_hl(ARG)+phase1._call(sy["vi_p904_invocation"])+phase1._jp_c(FAIL_PC))
        code+=expect_byte(sy["vi_named"],1)+expect_byte(sy["vi_target_type"],sy["OBJ_TXT"])+expect_byte(sy["vi_dirty"],0)
        code+=expect_word(sy["vi_buffer_len"],4)+expect_byte(sy["vi_source_open"],0)+expect_byte(sy["vi_line_count"],2)
        for i,v in enumerate(b"/tmp/x\0"): code+=expect_byte(sy["vi_target"]+i,v)
        code+=phase1._jp(PASS_PC)
        run_case(root,"existing-path",code,patch(image,gateway,[b"vi",b"/tmp/x"],sy["OBJ_TXT"]))

        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._ld_hl(ARG)+phase1._call(sy["vi_p904_invocation"]))
        code+=b"\xD2"+word(FAIL_PC)+b"\xFE"+bytes((sy["E_INVAL"]&0xFF,))+phase1._jp_nz(FAIL_PC)+phase1._jp(PASS_PC)
        run_case(root,"two-paths",code,patch(image,gateway,[b"vi",b"a",b"b"],sy["OBJ_TXT"]))

        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._ld_hl(ARG)+phase1._call(sy["vi_p904_invocation"])+phase1._jp_c(FAIL_PC))
        code+=b"\x3E\x01\x32"+word(sy["vi_dirty"])
        code+=phase1._call(sy["vi_p904_require_target"])
        code+=b"\xD2"+word(FAIL_PC)+b"\xFE"+bytes((sy["E_NOENT"]&0xFF,))+phase1._jp_nz(FAIL_PC)
        for i,v in enumerate(b"vi: no file name\n"): code+=expect_byte(OUT+i,v)
        code+=expect_byte(sy["vi_named"],0)+expect_byte(sy["vi_dirty"],1)+phase1._jp(PASS_PC)
        run_case(root,"no-name",code,patch(image,gateway,[b"vi"],sy["OBJ_TXT"]))

        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._ld_hl(ARG)+phase1._call(sy["vi_p904_invocation"])+phase1._jp_c(FAIL_PC))
        code+=b"\x3E\x01\x32"+word(sy["vi_dirty"])
        code+=b"\x3E"+bytes((sy["E_IO"]&0xFF,))+phase1._call(sy["vi_p904_failed_write"])
        code+=b"\xD2"+word(FAIL_PC)+b"\xFE"+bytes((sy["E_IO"]&0xFF,))+phase1._jp_nz(FAIL_PC)
        code+=expect_byte(sy["vi_named"],0)+expect_byte(sy["vi_dirty"],1)
        code+=phase1._ld_hl(ARG+8+3)+b"\x3E"+bytes((sy["OBJ_C"]&0xFF,))+phase1._call(sy["vi_p904_commit_target"])+phase1._jp_c(FAIL_PC)
        code+=expect_byte(sy["vi_named"],1)+expect_byte(sy["vi_target_type"],sy["OBJ_C"])+expect_byte(sy["vi_dirty"],0)+phase1._jp(PASS_PC)
        run_case(root,"retarget-transaction",code,patch(image,gateway,[b"vi",b"new.c"],sy["OBJ_TXT"]))

        assertions += [
            {"name":"fuse-unnamed-empty-txt","passed":True},
            {"name":"fuse-existing-path-load-and-bind","passed":True},
            {"name":"fuse-two-paths-invalid","passed":True},
            {"name":"fuse-no-name-exact-refusal","passed":True},
            {"name":"fuse-failed-write-no-retarget","passed":True},
            {"name":"fuse-successful-write-retargets","passed":True},
        ]

    hashes={
        "tools/vi.asm":sha256_file(source),
        "v1/build/p904-vi.mex1":sha256_file(mex_path),
        "v1/build/p904-vi.tap":sha256_file(tap),
        "v1/tools-host/test-driver/phase9_vi_unnamed.py":sha256_file(root/"v1/tools-host/test-driver/phase9_vi_unnamed.py"),
        "v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
        "v1/dist/certification/P9.03.test.json":sha256_file(root/"v1/dist/certification/P9.03.test.json"),
    }
    return [fr,xr,gr],hashes,assertions
