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

import importlib.util
from pathlib import Path
import struct

import phase1
import phase3_open_descriptions
from driver_core import DriverError
from fuse_harness import PASS_PC, FAIL_PC, run_sna


# P10.21 exact-candidate marker; branch-range repair.
class P1021Error(DriverError):
    pass


def require(ok, msg):
    if not ok:
        raise P1021Error(msg)


def inspector(root: Path):
    path=root/"v1/tools-host/inspect-obj/inspect.py"
    spec=importlib.util.spec_from_file_location("zxux_p1021_inspector",path)
    require(spec is not None and spec.loader is not None,"inspector import")
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def make_obj(mod):
    text=b"\x00\x00\xC9"
    sym=bytearray(20); sym[:4]=b"main"; sym[18]=1; sym[19]=1
    rel=struct.pack("<HHBB",0,0,1,0)
    body=text+bytes(sym)+rel
    h=bytearray(24); h[:4]=b"OBJ1"; h[4]=1
    struct.pack_into("<H",h,6,24)
    struct.pack_into("<H",h,8,len(text))
    struct.pack_into("<H",h,10,2)
    struct.pack_into("<H",h,12,1)
    struct.pack_into("<H",h,14,1)
    struct.pack_into("<H",h,16,24+len(text))
    struct.pack_into("<H",h,18,24+len(text)+20)
    struct.pack_into("<H",h,20,mod.crc16_ccitt_false(body))
    struct.pack_into("<H",h,22,0)
    struct.pack_into("<H",h,22,mod.crc16_ccitt_false(bytes(h)))
    return bytes(h)+body


def db(data: bytes)->str:
    return ",".join(f"$%02X"%b for b in data)


def dispatch(root,action,step,*,sha256_file,run_command,require_project_tool):
    if step!="P10.21":
        raise DriverError(step)

    mod=inspector(root)
    good=make_obj(mod)
    mod.inspect_bytes(good)
    bad=bytearray(good); bad[0]^=1
    source=(root/"tools/ld.asm").read_text(encoding="utf-8")
    assertions=[
        {"name":"one-or-more-input-gate","passed":"ld_p1021_require_inputs:" in source},
        {"name":"kernel-object-type-authority","passed":"cp OBJ_OBJ" in source and "SYS_STAT" in source},
        {"name":"suffix-not-used-for-type","passed":"suffix" in source and "irrelevant" in source},
        {"name":"read-close-validate-path","passed":all(x in source for x in ("SYS_OPEN","SYS_READ","SYS_CLOSE","ld_p1021_validate_memory:"))},
        {"name":"complete-obj1-validator","passed":all(x in source for x in ("ld_p1021_validate_symbols:","ld_p1021_validate_relocs:","ld_p1021_crc16:"))},
        {"name":"archive-memory-validation-entry","passed":"Used for both file-loaded inputs and selected built-in archive members." in source},
    ]
    require(all(a["passed"] for a in assertions),"P10.21 static input-loader contract failure")

    assembler=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus")
    build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    fixture=build/"p1021-loader.asm"
    fixture.write_text(f"""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../../tools/ld.asm"
    ORG $C000
fixture:
    EMIT_P10_LD_INPUT_LOADER

p1021_path_weird: db '/','t','m','p','/','w','e','i','r','d','.','b','i','n',0
p1021_path_fake: db '/','t','m','p','/','f','a','k','e','.','o','b','j',0
p1021_source: db {db(good)}
p1021_source_end:
p1021_bad_source: db {db(bytes(bad))}
p1021_bad_source_end:
p1021_buffer: defs 96,$CC

p1021_mode: db 0
p1021_read_done: db 0
p1021_stat_calls: db 0
p1021_open_calls: db 0
p1021_read_calls: db 0
p1021_close_calls: db 0

p1021_reset:
    xor a
    ld (p1021_mode),a
    ld (p1021_read_done),a
    ld (p1021_stat_calls),a
    ld (p1021_open_calls),a
    ld (p1021_read_calls),a
    ld (p1021_close_calls),a
    ret

p1021_fail:
    ld a,E_FORMAT
    scf
    ret

p1021_count_good:
    ld c,1
    jp ld_p1021_require_inputs
p1021_count_bad:
    ld c,0
    jp ld_p1021_require_inputs

p1021_load_good:
    call p1021_reset
    ld hl,p1021_path_weird
    ld de,p1021_buffer
    ld bc,96
    call ld_p1021_load_file
    ret c
    ld de,p1021_source_end-p1021_source
    or a
    sbc hl,de
    jp nz,p1021_fail
    ld a,(p1021_open_calls)
    cp 1
    jp nz,p1021_fail
    ld a,(p1021_close_calls)
    cp 1
    jp nz,p1021_fail
    xor a
    ret

p1021_wrong_type:
    call p1021_reset
    ld a,1
    ld (p1021_mode),a
    ld hl,p1021_path_fake
    ld de,p1021_buffer
    ld bc,96
    call ld_p1021_load_file
    jp nc,p1021_fail
    cp E_FORMAT
    jp nz,p1021_fail
    ld a,(p1021_open_calls)
    or a
    jp nz,p1021_fail
    xor a
    ret

p1021_malformed:
    call p1021_reset
    ld a,2
    ld (p1021_mode),a
    ld hl,p1021_path_weird
    ld de,p1021_buffer
    ld bc,96
    call ld_p1021_load_file
    jp nc,p1021_fail
    cp E_FORMAT
    jp nz,p1021_fail
    ld a,(p1021_close_calls)
    cp 1
    jp nz,p1021_fail
    xor a
    ret

p1021_overflow:
    call p1021_reset
    ld a,3
    ld (p1021_mode),a
    ld hl,p1021_path_weird
    ld de,p1021_buffer
    ld bc,p1021_source_end-p1021_source
    call ld_p1021_load_file
    jp nc,p1021_fail
    cp E_NOSPC
    jp nz,p1021_fail
    ld a,(p1021_close_calls)
    cp 1
    jp nz,p1021_fail
    xor a
    ret

p1021_archive_good:
    ld hl,p1021_source
    ld bc,p1021_source_end-p1021_source
    jp ld_p1021_validate_memory

p1021_archive_bad:
    ld hl,p1021_bad_source
    ld bc,p1021_bad_source_end-p1021_bad_source
    jp ld_p1021_validate_memory

fixture_end:
    SAVEBIN "p1021-main.bin",fixture,fixture_end-fixture

    ORG $E000
p1021_gateway:
    cp SYS_STAT
    jp z,p1021_sys_stat
    cp SYS_OPEN
    jp z,p1021_sys_open
    cp SYS_READ
    jp z,p1021_sys_read
    cp SYS_CLOSE
    jp z,p1021_sys_close
    ld a,E_NOTSUP
    scf
    ret

p1021_sys_stat:
    ld a,(p1021_stat_calls)
    inc a
    ld (p1021_stat_calls),a
    inc hl
    inc hl
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld a,(p1021_mode)
    cp 1
    ld a,OBJ_TXT
    jp z,p1021_stat_store
    ld a,OBJ_OBJ
p1021_stat_store:
    ld (de),a
    xor a
    ret

p1021_sys_open:
    ld a,(p1021_open_calls)
    inc a
    ld (p1021_open_calls),a
    ld a,c
    cp O_READ
    jp nz,p1021_sys_format
    ld a,b
    or a
    jp nz,p1021_sys_format
    ld hl,4
    xor a
    ret

p1021_sys_read:
    ld a,(p1021_read_calls)
    inc a
    ld (p1021_read_calls),a
    ld a,d
    or a
    jp nz,p1021_sys_format
    ld a,e
    cp 4
    jp nz,p1021_sys_format
    ld a,(p1021_mode)
    cp 3
    jp z,p1021_read_overflow
    ld a,(p1021_read_done)
    or a
    jp nz,p1021_read_eof
    ld a,1
    ld (p1021_read_done),a
    ex de,hl
    ld a,(p1021_mode)
    cp 2
    ld hl,p1021_source
    jp nz,p1021_read_copy
    ld hl,p1021_bad_source
p1021_read_copy:
    ld bc,p1021_source_end-p1021_source
    ldir
    ld hl,p1021_source_end-p1021_source
    xor a
    ret
p1021_read_eof:
    ld hl,0
    xor a
    ret

p1021_read_overflow:
    ld a,(p1021_read_done)
    or a
    jp nz,p1021_read_extra
    ld a,1
    ld (p1021_read_done),a
    ex de,hl
    ld hl,p1021_source
    ld bc,p1021_source_end-p1021_source
    ldir
    ld hl,p1021_source_end-p1021_source
    xor a
    ret
p1021_read_extra:
    ld hl,1
    xor a
    ret

p1021_sys_close:
    ld a,(p1021_close_calls)
    inc a
    ld (p1021_close_calls),a
    xor a
    ret
p1021_sys_format:
    ld a,E_FORMAT
    scf
    ret
p1021_gateway_end:
    SAVEBIN "p1021-gateway.bin",p1021_gateway,p1021_gateway_end-p1021_gateway
""",encoding="utf-8",newline="\n")

    result=run_command([assembler,"--nologo","--sym=p1021-loader.sym",fixture.name],cwd=build,timeout_seconds=30)
    require(not result.timed_out and result.exit_code==0,f"P10.21 assemble: {result.stderr or result.stdout}")
    main=(build/"p1021-main.bin").read_bytes()
    gateway=(build/"p1021-gateway.bin").read_bytes()
    require(len(main)<=0x2000,"P10.21 fixture overlaps syscall gateway")

    if action=="test":
        names=("p1021_count_good","p1021_count_bad","p1021_load_good","p1021_wrong_type","p1021_malformed","p1021_overflow","p1021_archive_good","p1021_archive_bad")
        syms=phase3_open_descriptions._symbols(build/"p1021-loader.sym",names)
        def patch(ram):
            ram[0xC000-0x4000:0xC000-0x4000+len(main)]=main
            ram[0xE000-0x4000:0xE000-0x4000+len(gateway)]=gateway
        for name in ("p1021_count_good","p1021_load_good","p1021_archive_good","p1021_wrong_type","p1021_malformed","p1021_overflow"):
            code=b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._call(syms[name])+phase1._jp_c(FAIL_PC)+phase1._jp(PASS_PC)
            run_sna(root,code,patch=patch)
        for name in ("p1021_count_bad","p1021_archive_bad"):
            code=b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._call(syms[name])+b"\xD2"+phase1._word(FAIL_PC)+phase1._jp(PASS_PC)
            run_sna(root,code,patch=patch)
        assertions += [
            {"name":"fuse-one-input-required","passed":True},
            {"name":"fuse-explicit-obj-type-load-with-nonobj-suffix","passed":True},
            {"name":"fuse-wrong-type-obj-suffix-rejected-before-open","passed":True},
            {"name":"fuse-malformed-obj-rejected-after-close","passed":True},
            {"name":"fuse-capacity-overflow-rejected","passed":True},
            {"name":"fuse-built-in-memory-member-validation","passed":True},
        ]

    hashes={
        "tools/ld.asm":sha256_file(root/"tools/ld.asm"),
        "v1/include/obj1.inc":sha256_file(root/"v1/include/obj1.inc"),
        "v1/tools-host/inspect-obj/inspect.py":sha256_file(root/"v1/tools-host/inspect-obj/inspect.py"),
        "v1/build/p1021-main.bin":sha256_file(build/"p1021-main.bin"),
        "v1/build/p1021-gateway.bin":sha256_file(build/"p1021-gateway.bin"),
        "v1/tools-host/test-driver/phase10_step_21.py":sha256_file(root/"v1/tools-host/test-driver/phase10_step_21.py"),
        "v1/dist/certification/P10.20.build.json":sha256_file(root/"v1/dist/certification/P10.20.build.json"),
        "v1/dist/certification/P10.20.test.json":sha256_file(root/"v1/dist/certification/P10.20.test.json"),
    }
    return [result],hashes,assertions
