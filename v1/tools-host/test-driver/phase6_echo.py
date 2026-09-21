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

ECHO=0xC000
GATE=0xE000
ARG=0xA000
OUT=0xA200
STATUS=0xA300

class P616Error(DriverError): pass
def require(v,m):
    if not v: raise P616Error(m)
def u16(v): return struct.pack("<H",v)
def crc16(data):
    crc=0xffff
    for byte in data:
        crc ^= byte<<8
        for _ in range(8): crc=((crc<<1)^0x1021)&0xffff if crc&0x8000 else (crc<<1)&0xffff
    return crc
def mex1(image):
    h=bytearray(24); h[:4]=b"MEX1"; h[4]=1; h[6:8]=u16(24); h[8:10]=u16(len(image))
    h[12:14]=u16(0); h[14:16]=u16(128); h[18:20]=u16(24+len(image))
    h[20:22]=u16(crc16(image)); h[22:24]=u16(crc16(bytes(h))); return bytes(h)+image
def load_module(path,name):
    spec=importlib.util.spec_from_file_location(name,path); require(spec is not None and spec.loader is not None,f"cannot load {path}")
    mod=importlib.util.module_from_spec(spec); sys.modules[name]=mod; spec.loader.exec_module(mod); return mod
def word(v): return bytes((v&255,(v>>8)&255))
def arg1(args):
    body=b"".join(x+b"\0" for x in args); total=8+len(body)
    return b"ARG1"+bytes((len(args),0))+word(total)+body
def expect_byte(addr,val): return b"\x3A"+word(addr)+bytes((0xFE,val&255))+phase1._jp_nz(FAIL_PC)
def patch(echo,gate,args):
    block=arg1(args)
    def p(ram):
        ram[ECHO-0x4000:ECHO-0x4000+len(echo)]=echo
        ram[GATE-0x4000:GATE-0x4000+len(gate)]=gate
        ram[ARG-0x4000:ARG-0x4000+len(block)]=block
        ram[OUT-0x4000:OUT-0x4000+128]=b"\xA5"*128
        ram[STATUS-0x4000:STATUS-0x4000+3]=b"\0\0\0"
    return p

def dispatch(root:Path,action:str,step:str,*,sha256_file,run_command,require_project_tool):
    if step!="P6.16": raise DriverError(f"Phase-6 echo step is not registered: {step}")
    ep=root/"v1/src/utils/echo.asm"; text=ep.read_text()
    macro=text.split("MACRO EMIT_P616_ECHO_ROUTINES",1)[1].split("ENDM",1)[0]
    sh=(root/"v1/src/shell/sh.asm").read_text()
    assertions=[
      {"name":"echo-is-external-only","passed":"echo_entry:" in macro and "P613_BUILTIN_" in sh and "P613_BUILTIN_ECHO" not in sh},
      {"name":"stdout-handle-one","passed":macro.count("ld de,1")>=2 and "SYS_WRITE" in macro},
      {"name":"single-space-separator","passed":"ld hl,$0020" in macro},
      {"name":"single-lf-terminator","passed":"ld hl,$000a" in macro},
      {"name":"status-zero","passed":"ld l,0" in macro and "SYS_EXIT" in macro},
    ]
    require(all(a["passed"] for a in assertions),"P6.16 static contract failure")
    asm=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus"); build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)

    src=build/"p616-echo-image.asm"
    src.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/utils/echo.asm"
    ORG $0000
p616_image:
    EMIT_P616_ECHO_ROUTINES
p616_image_end:
    SAVEBIN "p616-echo-image.bin",p616_image,p616_image_end-p616_image
""",encoding="utf-8",newline="\n")
    sr=run_command([asm,"--nologo","--lst=p616-echo-image.lst","--sym=p616-echo-image.sym","p616-echo-image.asm"],cwd=build,timeout_seconds=30)
    require(not sr.timed_out and sr.exit_code==0,f"P6.16 echo image assembly failed: {sr.stderr or sr.stdout}")
    image=(build/"p616-echo-image.bin").read_bytes()
    require(16<=len(image)<=192,"P6.16 echo image size implausible")
    mp=build/"p616-echo.mex1"; mp.write_bytes(mex1(image))
    inspector=require_project_tool(root,"v1/tools-host/inspect-mex/inspect.py")
    ir=run_command([sys.executable,inspector,str(mp),"--base","0x6000"],cwd=root,timeout_seconds=10)
    require(not ir.timed_out and ir.exit_code==0,f"P6.16 MEX1 inspect failed: {ir.stderr or ir.stdout}")
    maketap=load_module(root/"v1/tools-host/maketap/maketap.py","zxux_p616_maketap")
    tap=maketap.m48o_blocks(maketap.M48OObject("echo",maketap.M48O_BIN,maketap.DIR_BIN,mp.read_bytes()))
    tp=build/"p616-echo.tap"; tp.write_bytes(tap)
    require(tap==maketap.m48o_blocks(maketap.M48OObject("echo",maketap.M48O_BIN,maketap.DIR_BIN,mp.read_bytes())),"P6.16 TAP rebuild mismatch")

    ff=build/"p616-echo-fixture.asm"
    ff.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/utils/echo.asm"
    ORG $C000
p616_fixture:
    EMIT_P616_ECHO_ROUTINES
p616_fixture_end:
    SAVEBIN "p616-echo-fixture.bin",p616_fixture,p616_fixture_end-p616_fixture
""",encoding="utf-8",newline="\n")
    fr=run_command([asm,"--nologo","--lst=p616-echo-fixture.lst","--sym=p616-echo-fixture.sym","p616-echo-fixture.asm"],cwd=build,timeout_seconds=30)
    require(not fr.timed_out and fr.exit_code==0,f"P6.16 echo fixture assembly failed: {fr.stderr or fr.stdout}")
    gf=build/"p616-gateway.asm"
    gf.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    ORG $E000
p616_gate:
    cp SYS_WRITE
    jr z,p616_write
    cp SYS_EXIT
    jr z,p616_exit
    ld a,E_NOTSUP
    scf
    ret
p616_write:
    ld a,d
    or a
    jr nz,p616_bad
    ld a,e
    cp 1
    jr nz,p616_bad
    ld de,(p616_out)
    ldir
    ld (p616_out),de
    xor a
    ret
p616_exit:
    ld a,l
    ld ($A300),a
    ld a,1
    ld ($A301),a
    xor a
    ret
p616_bad:
    ld a,E_INVAL
    scf
    ret
p616_out: dw $A200
p616_gate_end:
    SAVEBIN "p616-gateway.bin",p616_gate,p616_gate_end-p616_gate
""",encoding="utf-8",newline="\n")
    gr=run_command([asm,"--nologo","--lst=p616-gateway.lst","--sym=p616-gateway.sym","p616-gateway.asm"],cwd=build,timeout_seconds=30)
    require(not gr.timed_out and gr.exit_code==0,f"P6.16 gateway fixture failed: {gr.stderr or gr.stdout}")

    if action=="test":
        sy=phase3_open_descriptions._symbols(build/"p616-echo-fixture.sym",("echo_entry",))
        echo=(build/"p616-echo-fixture.bin").read_bytes(); gate=(build/"p616-gateway.bin").read_bytes()
        for args,want in [
            ([b"echo"],b"\n"),
            ([b"echo",b"hello"],b"hello\n"),
            ([b"echo",b"hello",b"world"],b"hello world\n"),
        ]:
            block=arg1(args)
            code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._ld_hl(ARG)+b"\x01"+word(len(block))+phase1._call(sy["echo_entry"]))
            for off,val in enumerate(want): code+=expect_byte(OUT+off,val)
            code+=expect_byte(OUT+len(want),0xA5)+expect_byte(STATUS,0)+expect_byte(STATUS+1,1)+phase1._jp(PASS_PC)
            run_sna(root,bytes(code),patch=patch(echo,gate,args))
        assertions += [
          {"name":"fuse-echo-noargs-lf","passed":True},
          {"name":"fuse-echo-hello-phase3-sink-exact","passed":True},
          {"name":"fuse-echo-multiarg-single-spaces","passed":True},
        ]
    hashes={
      "v1/src/utils/echo.asm":sha256_file(ep),"v1/build/p616-echo.mex1":sha256_file(mp),"v1/build/p616-echo.tap":sha256_file(tp),
      "v1/tools-host/test-driver/phase6_echo.py":sha256_file(root/"v1/tools-host/test-driver/phase6_echo.py"),"v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
      "v1/dist/certification/P6.15.build.json":sha256_file(root/"v1/dist/certification/P6.15.build.json"),"v1/dist/certification/P6.15.test.json":sha256_file(root/"v1/dist/certification/P6.15.test.json"),"v1/dist/media/P6.15/manifest.json":sha256_file(root/"v1/dist/media/P6.15/manifest.json")}
    return [sr,ir,fr,gr],hashes,assertions
