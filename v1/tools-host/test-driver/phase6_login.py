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
import struct, sys
from driver_core import DriverError
from fuse_harness import FAIL_PC, PASS_PC, run_sna
import phase1, phase3_open_descriptions

PROMPT=b"login: "
SHELL_BASE=0xC000
GATE_BASE=0xE000
INPUT_ADDR=0xA000
PROMPT_ADDR=0xA100
OUTPUT_ADDR=0xD000

class P603Error(DriverError): pass
def require(v,m):
    if not v: raise P603Error(m)
def u16(v): return struct.pack("<H",v)
def crc16(data):
    crc=0xffff
    for byte in data:
        crc ^= byte<<8
        for _ in range(8): crc=((crc<<1)^0x1021)&0xffff if crc&0x8000 else (crc<<1)&0xffff
    return crc
def mex1(image):
    h=bytearray(24); h[:4]=b"MEX1"; h[4]=1; h[6:8]=u16(24); h[8:10]=u16(len(image)); h[14:16]=u16(128); h[18:20]=u16(24+len(image)); h[20:22]=u16(crc16(image)); h[22:24]=u16(crc16(bytes(h))); return bytes(h)+image
def load_module(path,name):
    spec=importlib.util.spec_from_file_location(name,path); require(spec is not None and spec.loader is not None,f"cannot load {path}")
    mod=importlib.util.module_from_spec(spec); sys.modules[name]=mod; spec.loader.exec_module(mod); return mod
def word(v): return bytes((v&255,(v>>8)&255))
def expect_byte(addr,val): return b"\x3A"+word(addr)+bytes((0xFE,val&255))+phase1._jp_nz(FAIL_PC)
def expect_word(addr,val): return b"\x2A"+word(addr)+phase1._ld_de(val)+b"\xB7\xED\x52"+phase1._jp_nz(FAIL_PC)
def patch(shell,gateway,data=b"a"):
    def p(ram):
        ram[SHELL_BASE-0x4000:SHELL_BASE-0x4000+len(shell)]=shell
        ram[GATE_BASE-0x4000:GATE_BASE-0x4000+len(gateway)]=gateway
        ram[INPUT_ADDR-0x4000:INPUT_ADDR-0x4000+len(data)]=data
        ram[PROMPT_ADDR-0x4000:PROMPT_ADDR-0x4000+len(PROMPT)]=PROMPT
        ram[OUTPUT_ADDR-0x4000:OUTPUT_ADDR-0x4000+16]=b"\xA5"*16
    return p

def dispatch(root:Path,action:str,step:str,*,sha256_file,run_command,require_project_tool):
    if step!="P6.03": raise DriverError(f"Phase-6 login step is not registered: {step}")
    shell_path=root/"v1/src/shell/sh.asm"; text=shell_path.read_text()
    macro=text.split("MACRO EMIT_P603_LOGIN_ROUTINES",1)[1].split("ENDM",1)[0]
    assertions=[
      {"name":"length-bound-1-through-8","passed":"cp 9" in macro and "jr z,sh_p603_invalid" in macro},
      {"name":"first-byte-lowercase-only","passed":"cp 'a'" in macro and "cp 'z'+1" in macro},
      {"name":"tail-allows-lower-digit-underscore-hyphen","passed":"cp '0'" in macro and "cp '_'" in macro and "cp '-'" in macro},
      {"name":"invalid-input-reprompts-exact-login-token","passed":"sh_p603_validate_or_reprompt:" in macro and "ld bc,P602_LOGIN_LENGTH" in macro and "ld a,SYS_CON_WRITE" in macro},
    ]
    require(all(a["passed"] for a in assertions),"P6.03 static contract failure")
    asm=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus"); build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    sf=build/"p603-shell-fixture.asm"
    sf.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/shell/sh.asm"
    ORG $C000
p603_start:
    EMIT_P603_LOGIN_ROUTINES
p603_end:
    SAVEBIN "p603-shell-fixture.bin",p603_start,p603_end-p603_start
""",encoding="utf-8",newline="\n")
    sr=run_command([asm,"--nologo","--lst=p603-shell-fixture.lst","--sym=p603-shell-fixture.sym","p603-shell-fixture.asm"],cwd=build,timeout_seconds=30)
    require(not sr.timed_out and sr.exit_code==0,f"P6.03 shell fixture failed: {sr.stderr or sr.stdout}")
    image=(build/"p603-shell-fixture.bin").read_bytes(); mex=mex1(image); mp=build/"p603-login.mex1"; mp.write_bytes(mex)
    inspector=require_project_tool(root,"v1/tools-host/inspect-mex/inspect.py")
    ir=run_command([sys.executable,inspector,str(mp),"--base","0x6000"],cwd=root,timeout_seconds=10)
    require(not ir.timed_out and ir.exit_code==0,f"P6.03 MEX1 inspect failed: {ir.stderr or ir.stdout}")
    maketap=load_module(root/"v1/tools-host/maketap/maketap.py","zxux_p603_maketap")
    tap=maketap.m48o_blocks(maketap.M48OObject("sh",maketap.M48O_BIN,maketap.DIR_BIN,mex)); tp=build/"p603-login.tap"; tp.write_bytes(tap)
    require(tap==maketap.m48o_blocks(maketap.M48OObject("sh",maketap.M48O_BIN,maketap.DIR_BIN,mex)),"P6.03 TAP rebuild mismatch")
    gf=build/"p603-gateway.asm"
    gf.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    ORG $E000
p603_gate:
    cp SYS_CON_WRITE
    jr nz,p603_notsup
    ld de,(p603_out)
    ldir
    ld (p603_out),de
    xor a
    ret
p603_notsup: ld a,E_NOTSUP : scf : ret
p603_out: dw $D000
p603_gate_end:
    SAVEBIN "p603-gateway.bin",p603_gate,p603_gate_end-p603_gate
""",encoding="utf-8",newline="\n")
    gr=run_command([asm,"--nologo","--lst=p603-gateway.lst","--sym=p603-gateway.sym","p603-gateway.asm"],cwd=build,timeout_seconds=30)
    require(not gr.timed_out and gr.exit_code==0,f"P6.03 gateway fixture failed: {gr.stderr or gr.stdout}")
    if action=="test":
        sy=phase3_open_descriptions._symbols(build/"p603-shell-fixture.sym",("sh_p603_validate_username","sh_p603_validate_or_reprompt","E_INVAL"))
        gsy=phase3_open_descriptions._symbols(build/"p603-gateway.sym",("p603_out",))
        shell=(build/"p603-shell-fixture.bin").read_bytes(); gate=(build/"p603-gateway.bin").read_bytes()
        valid=(b"a",b"z9_-abcd",b"abc12345")
        for data in valid:
            code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._ld_hl(INPUT_ADDR)+b"\x01"+word(len(data)))
            code+=phase1._call(sy["sh_p603_validate_username"])+phase1._jp_c(FAIL_PC)+phase1._jp(PASS_PC)
            run_sna(root,bytes(code),patch=patch(shell,gate,data))
        invalid=(b"",b"A",b"abcdefghi",b"a.",b"0abc",b"aB")
        for data in invalid:
            code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._ld_hl(INPUT_ADDR)+b"\x01"+word(len(data))+b"\xDD\x21"+word(PROMPT_ADDR))
            code+=phase1._call(sy["sh_p603_validate_or_reprompt"])+b"\xD2"+word(FAIL_PC)
            code+=bytes((0xFE,sy["E_INVAL"]&255))+phase1._jp_nz(FAIL_PC)
            for off,val in enumerate(PROMPT): code+=expect_byte(OUTPUT_ADDR+off,val)
            code+=expect_byte(OUTPUT_ADDR+len(PROMPT),0xA5)+expect_word(gsy["p603_out"],OUTPUT_ADDR+len(PROMPT))+phase1._jp(PASS_PC)
            run_sna(root,bytes(code),patch=patch(shell,gate,data))
        assertions += [{"name":"fuse-boundary-login-corpus","passed":True},{"name":"fuse-invalid-login-reprompt","passed":True}]
    hashes={
      "v1/src/shell/sh.asm":sha256_file(shell_path),"v1/build/p603-login.mex1":sha256_file(mp),"v1/build/p603-login.tap":sha256_file(tp),
      "v1/tools-host/test-driver/phase6_login.py":sha256_file(root/"v1/tools-host/test-driver/phase6_login.py"),"v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
      "v1/dist/certification/P6.02.build.json":sha256_file(root/"v1/dist/certification/P6.02.build.json"),"v1/dist/certification/P6.02.test.json":sha256_file(root/"v1/dist/certification/P6.02.test.json"),"v1/dist/media/P6.02/manifest.json":sha256_file(root/"v1/dist/media/P6.02/manifest.json")}
    return [sr,ir,gr],hashes,assertions
