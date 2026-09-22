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
from pathlib import Path
import importlib.util, struct, sys
from driver_core import DriverError
from fuse_harness import FAIL_PC, PASS_PC, run_sna
import phase1, phase3_open_descriptions

UTIL=0xC000; GATE=0xE000; ARG=0xA000; OLD=0xA100; NEW=0xA120; STATUS=0xA180; CALLS=0xA182

class P804Error(DriverError): pass
def require(v,m):
    if not v: raise P804Error(m)
def u16(v): return struct.pack("<H",v)
def crc16(data):
    crc=0xFFFF
    for b in data:
        crc ^= b<<8
        for _ in range(8): crc=((crc<<1)^0x1021)&0xFFFF if crc&0x8000 else (crc<<1)&0xFFFF
    return crc
def mex1(image):
    h=bytearray(24); h[:4]=b"MEX1"; h[4]=1; h[6:8]=u16(24); h[8:10]=u16(len(image)); h[14:16]=u16(256); h[18:20]=u16(24+len(image)); h[20:22]=u16(crc16(image)); h[22:24]=u16(crc16(bytes(h))); return bytes(h)+image
def load_module(path,name):
    s=importlib.util.spec_from_file_location(name,path); require(s and s.loader,f"cannot load {path}"); m=importlib.util.module_from_spec(s); sys.modules[name]=m; s.loader.exec_module(m); return m
def word(v): return bytes((v&255,(v>>8)&255))
def arg1(args):
    body=b"".join(x+b"\0" for x in args); return b"ARG1"+bytes((len(args),0))+word(8+len(body))+body
def expect(addr,val): return b"\x3A"+word(addr)+bytes((0xFE,val&255))+phase1._jp_nz(FAIL_PC)
def patch(util,gate,args,mode):
    block=arg1(args)
    def apply(ram):
        ram[UTIL-0x4000:UTIL-0x4000+len(util)]=util; ram[GATE-0x4000:GATE-0x4000+len(gate)]=gate
        ram[ARG-0x4000:ARG-0x4000+len(block)]=block; ram[STATUS-0x4000:STATUS-0x4000+8]=b"\0"*8
        ram[0xA181-0x4000]=mode
    return apply
def source_contract(root):
    s=(root/"v1/src/utils/mv.asm").read_text(); p=(root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md").read_text()
    return [
      {"name":"canonical-p804-present","passed":"## P8.04 - Utility `mv`" in p},
      {"name":"rename-only","passed":"SYS_RENAME" in s and "SYS_OPEN" not in s and "SYS_REMOVE" not in s},
      {"name":"ren1-record","passed":"mv_ren1" in s and "ld (mv_ren1+2),hl" in s},
      {"name":"exact-two-operands","passed":"cp 3" in s and "E_INVAL" in s},
      {"name":"kernel-errors-propagate","passed":"jr c,mv_error" in s or "jp c,mv_error" in s},
      {"name":"no-case-folding","passed":"casefold" not in s.lower()},
    ]
def dispatch(root,action,step,*,sha256_file,run_command,require_project_tool):
    if step!="P8.04": raise DriverError(f"Phase-8 mv step is not registered: {step}")
    assertions=source_contract(root); require(all(x["passed"] for x in assertions),"P8.04 static contract failure")
    asm=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus"); build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    src=build/"p804-mv-image.asm"; src.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/utils/mv.asm"
    ORG $0000
p804_image:
    EMIT_P804_MV_ROUTINES
p804_image_end:
    SAVEBIN "p804-mv-image.bin",p804_image,p804_image_end-p804_image
""",newline="\n")
    ir=run_command([asm,"--nologo","--lst=p804-mv-image.lst","--sym=p804-mv-image.sym","p804-mv-image.asm"],cwd=build,timeout_seconds=30); require(not ir.timed_out and ir.exit_code==0,f"P8.04 image assembly failed: {ir.stderr or ir.stdout}")
    image=(build/"p804-mv-image.bin").read_bytes(); require(24<=len(image)<1024,"P8.04 image size implausible")
    mex=build/"p804-mv.mex1"; mex.write_bytes(mex1(image)); insp=require_project_tool(root,"v1/tools-host/inspect-mex/inspect.py")
    xr=run_command([sys.executable,insp,str(mex),"--base","0x6000"],cwd=root,timeout_seconds=10); require(not xr.timed_out and xr.exit_code==0,f"P8.04 MEX inspect failed: {xr.stderr or xr.stdout}")
    mk=load_module(root/"v1/tools-host/maketap/maketap.py","zxux_p804_maketap"); tb=mk.m48o_blocks(mk.M48OObject("mv",mk.M48O_BIN,mk.DIR_BIN,mex.read_bytes())); tap=build/"p804-mv.tap"; tap.write_bytes(tb)
    fix=build/"p804-mv-fixture.asm"; fix.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/utils/mv.asm"
    ORG $C000
p804_fixture:
    EMIT_P804_MV_ROUTINES
p804_fixture_end:
    SAVEBIN "p804-mv-fixture.bin",p804_fixture,p804_fixture_end-p804_fixture
""",newline="\n")
    fr=run_command([asm,"--nologo","--lst=p804-mv-fixture.lst","--sym=p804-mv-fixture.sym","p804-mv-fixture.asm"],cwd=build,timeout_seconds=30); require(not fr.timed_out and fr.exit_code==0,f"P8.04 fixture assembly failed: {fr.stderr or fr.stdout}")
    gate=build/"p804-gateway.asm"; gate.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    ORG $E000
p804_gate:
    cp SYS_RENAME
    jr z,p804_rename
    cp SYS_EXIT
    jr z,p804_exit
    ld a,E_NOTSUP
    scf
    ret
p804_rename:
    ld a,($A182)
    inc a
    ld ($A182),a
    ld e,(hl)
    inc hl
    ld d,(hl)
    ex de,hl
    ld de,$A100
    ld bc,16
    ldir
    ex de,hl
    ld e,(hl)
    inc hl
    ld d,(hl)
    ex de,hl
    ld de,$A120
    ld bc,16
    ldir
    ld a,($A181)
    or a
    jr z,p804_ok
    scf
    ret
p804_ok:
    xor a
    ret
p804_exit:
    ld a,l
    ld ($A180),a
    ld a,1
    ld ($A183),a
    xor a
    ret
p804_gate_end:
    SAVEBIN "p804-gateway.bin",p804_gate,p804_gate_end-p804_gate
""",newline="\n")
    gr=run_command([asm,"--nologo","--lst=p804-gateway.lst","--sym=p804-gateway.sym","p804-gateway.asm"],cwd=build,timeout_seconds=30); require(not gr.timed_out and gr.exit_code==0,f"P8.04 gateway assembly failed: {gr.stderr or gr.stdout}")
    if action=="test":
        sy=phase3_open_descriptions._symbols(build/"p804-mv-fixture.sym",("mv_entry",)); ub=(build/"p804-mv-fixture.bin").read_bytes(); gb=(build/"p804-gateway.bin").read_bytes()
        for args,mode,status,calls in [([b"mv",b"Foo",b"foo"],0,0,1),([b"mv",b"src",b"dst"],4,4,1),([b"mv",b"only"],0,1,0)]:
            block=arg1(args); code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._ld_hl(ARG)+b"\x01"+word(len(block))+phase1._call(sy["mv_entry"]))
            code+=expect(STATUS,status)+expect(STATUS+2,calls)+expect(STATUS+3,1)+phase1._jp(PASS_PC)
            run_sna(root,bytes(code),patch=patch(ub,gb,args,mode))
        assertions += [{"name":"fuse-case-only-delegated","passed":True},{"name":"fuse-ebusy-propagated","passed":True},{"name":"fuse-invalid-arity-no-rename","passed":True}]
    hashes={"v1/src/utils/mv.asm":sha256_file(root/"v1/src/utils/mv.asm"),"v1/build/p804-mv.mex1":sha256_file(mex),"v1/build/p804-mv.tap":sha256_file(tap),"v1/tools-host/test-driver/phase8_mv.py":sha256_file(root/"v1/tools-host/test-driver/phase8_mv.py"),"v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),"v1/dist/certification/P8.03.test.json":sha256_file(root/"v1/dist/certification/P8.03.test.json")}
    return [ir,xr,fr,gr],hashes,assertions
