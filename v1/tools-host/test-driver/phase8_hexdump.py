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
from fuse_harness import PASS_PC, run_sna
from phase8_common import arg1, word, assemble_utility, inspect_mex, make_tap

UTIL=0xC000; GATE=0xE000; ARG=0xA000; OUT=0xA300; MODE=0xA2F0; STATUS=0xA2F1
class P818Error(DriverError): pass
def require(v,m):
    if not v: raise P818Error(m)
def expect(addr,val): return b"\x3A"+word(addr)+bytes((0xFE,val&255))+phase1._jp_nz(0x8F00)
def expected(data:bytes)->bytes:
    out=bytearray()
    for off in range(0,len(data),8):
        row=data[off:off+8]
        out += f"{off:04X}  ".encode()
        out += b"".join(f"{b:02X} ".encode() for b in row)
        out += b"   "*(8-len(row))
        out += b" "
        out += bytes(b if 0x20<=b<0x7f else ord(".") for b in row)
        out += b"\n"
    return bytes(out)
def patch(util,gate,args,mode):
    ab=arg1(args)
    def apply(ram):
        ram[UTIL-0x4000:UTIL-0x4000+len(util)]=util
        ram[GATE-0x4000:GATE-0x4000+len(gate)]=gate
        ram[ARG-0x4000:ARG-0x4000+len(ab)]=ab
        ram[OUT-0x4000:OUT-0x4000+256]=b"\xA5"*256
        ram[MODE-0x4000]=mode
        ram[STATUS-0x4000:STATUS-0x4000+16]=b"\0"*16
    return apply
def source_contract(root):
    s=(root/"v1/src/utils/hexdump.asm").read_text()
    p=(root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md").read_text()
    return [
      {"name":"canonical-p818-present","passed":"## P8.18 - Utility `hexdump`" in p},
      {"name":"stdin-stream","passed":"ld de,0" in s and "SYS_READ" in s},
      {"name":"hex-ascii","passed":"hexdump_hex_byte:" in s and "hexdump_ascii_loop:" in s},
      {"name":"uppercase-hex","passed":"add a,'A'-10" in s},
      {"name":"eight-byte-rows","passed":"cp 8" in s and "ld de,8" in s},
      {"name":"stdout","passed":"ld de,1" in s and "SYS_WRITE" in s},
      {"name":"short-write-safe","passed":"hexdump_write_loop:" in s and "hexdump_write_zero:" in s},
      {"name":"exact-no-arg-form","passed":"cp 1" in s and "E_INVAL" in s},
    ]
def dispatch(root,action,step,*,sha256_file,run_command,require_project_tool):
    if step!="P8.18": raise DriverError(f"Phase-8 hexdump step is not registered: {step}")
    assertions=source_contract(root); require(all(x["passed"] for x in assertions),"P8.18 static contract failure")
    tool=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus"); build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    try:
        ir,image,mex=assemble_utility(root,build,tool,"hexdump","p818","EMIT_P818_HEXDUMP_ROUTINES",run_command)
        xr=inspect_mex(root,mex,run_command,require_project_tool)
        tap=make_tap(root,build,"hexdump","p818",mex)
    except RuntimeError as e: raise P818Error(str(e))
    require(128<=len(image)<2048,"P8.18 image size implausible")
    fix=build/"p818-hexdump-fixture.asm"; fix.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/utils/hexdump.asm"
    ORG $C000
fixture:
    EMIT_P818_HEXDUMP_ROUTINES
fixture_end:
    SAVEBIN "p818-hexdump-fixture.bin",fixture,fixture_end-fixture
""",newline="\n")
    fr=run_command([tool,"--nologo","--lst=p818-hexdump-fixture.lst","--sym=p818-hexdump-fixture.sym","p818-hexdump-fixture.asm"],cwd=build,timeout_seconds=30); require(not fr.timed_out and fr.exit_code==0,f"P8.18 fixture assembly failed: {fr.stderr or fr.stdout}")
    gate=build/"p818-gateway.asm"; gate.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    ORG $E000
gate:
    cp SYS_READ
    jp z,g_read
    cp SYS_WRITE
    jp z,g_write
    cp SYS_EXIT
    jp z,g_exit
    ld a,E_NOTSUP
    scf
    ret
g_read:
    ld (g_dest),hl
    ld a,($A2F0)
    cp 2
    jr z,g_read_fail
    cp 3
    jr z,g_empty
    ld a,(g_index)
    ld c,a
    ld a,g_data_end-g_data
    cp c
    jr z,g_empty
    ld e,c
    ld d,0
    ld hl,g_data
    add hl,de
    ld a,(hl)
    ld hl,(g_dest)
    ld (hl),a
    ld a,(g_index)
    inc a
    ld (g_index),a
    ld hl,1
    xor a
    ret
g_empty:
    ld hl,0
    xor a
    ret
g_read_fail:
    ld a,E_IO
    scf
    ret
g_write:
    ld a,e
    cp 1
    jr nz,g_bad
    ld a,d
    or a
    jr nz,g_bad
    ld a,($A2F0)
    cp 1
    jr nz,g_write_all
    ld a,b
    or a
    jr nz,g_write_two
    ld a,c
    cp 3
    jr c,g_write_all
g_write_two:
    ld bc,2
g_write_all:
    push bc
    ld de,(g_out)
    ldir
    ld (g_out),de
    pop hl
    xor a
    ret
g_exit:
    ld a,l
    ld ($A2F1),a
    ld a,1
    ld ($A2F2),a
    xor a
    ret
g_bad:
    ld a,E_INVAL
    scf
    ret
g_data: db $41,$00,$7e,$20,$5a,$0a,$31,$ff,$42
g_data_end:
g_index: db 0
g_dest: dw 0
g_out: dw $A300
gate_end:
    SAVEBIN "p818-gateway.bin",gate,gate_end-gate
""",newline="\n")
    gr=run_command([tool,"--nologo","--lst=p818-gateway.lst","--sym=p818-gateway.sym","p818-gateway.asm"],cwd=build,timeout_seconds=30); require(not gr.timed_out and gr.exit_code==0,f"P8.18 gateway assembly failed: {gr.stderr or gr.stdout}")
    if action=="test":
        sy=phase3_open_descriptions._symbols(build/"p818-hexdump-fixture.sym",("hexdump_entry",)); ub=(build/"p818-hexdump-fixture.bin").read_bytes(); gb=(build/"p818-gateway.bin").read_bytes()
        data=bytes((0x41,0x00,0x7e,0x20,0x5a,0x0a,0x31,0xff,0x42))
        cases=[
          ([b"hexdump"],0,expected(data),0),
          ([b"hexdump"],1,expected(data),0),
          ([b"hexdump"],2,b"",5),
          ([b"hexdump"],3,b"",0),
          ([b"hexdump",b"x"],0,b"",1),
        ]
        for args,mode,want,status in cases:
            ab=arg1(args); code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._ld_hl(ARG)+b"\x01"+word(len(ab))+phase1._call(sy["hexdump_entry"]))
            for o,v in enumerate(want): code+=expect(OUT+o,v)
            code+=expect(OUT+len(want),0xA5)+expect(STATUS,status)+expect(STATUS+1,1)+phase1._jp(PASS_PC)
            run_sna(root,bytes(code),patch=patch(ub,gb,args,mode))
        assertions += [
          {"name":"fuse-hex-ascii-two-row-view","passed":True},
          {"name":"fuse-short-write-retried","passed":True},
          {"name":"fuse-read-error-propagates","passed":True},
          {"name":"fuse-empty-input-success","passed":True},
          {"name":"fuse-extra-arg-rejected","passed":True},
        ]
    hashes={"v1/src/utils/hexdump.asm":sha256_file(root/"v1/src/utils/hexdump.asm"),"v1/build/p818-hexdump.mex1":sha256_file(mex),"v1/build/p818-hexdump.tap":sha256_file(tap),"v1/tools-host/test-driver/phase8_hexdump.py":sha256_file(root/"v1/tools-host/test-driver/phase8_hexdump.py"),"v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),"v1/dist/certification/P8.17.test.json":sha256_file(root/"v1/dist/certification/P8.17.test.json")}
    return [ir,xr,fr,gr],hashes,assertions
