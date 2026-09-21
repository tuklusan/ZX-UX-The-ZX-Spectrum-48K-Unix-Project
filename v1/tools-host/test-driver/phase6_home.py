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

SHELL_BASE=0xC000
GATE_BASE=0xE000
USER_ADDR=0xA000
HOME_ADDR=0xA100
PWD_ADDR=0xA200
KERNEL_CWD=0xA300

class P604Error(DriverError): pass
def require(v,m):
    if not v: raise P604Error(m)
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

def patch(shell,gate,user=b"alice"):
    def p(ram):
        ram[SHELL_BASE-0x4000:SHELL_BASE-0x4000+len(shell)]=shell
        ram[GATE_BASE-0x4000:GATE_BASE-0x4000+len(gate)]=gate
        ram[USER_ADDR-0x4000:USER_ADDR-0x4000+len(user)]=user
        ram[HOME_ADDR-0x4000:HOME_ADDR-0x4000+24]=b"\xA5"*24
        ram[PWD_ADDR-0x4000:PWD_ADDR-0x4000+24]=b"\xA5"*24
        ram[KERNEL_CWD-0x4000:KERNEL_CWD-0x4000+24]=b"\x00"*24
    return p

def dispatch(root:Path,action:str,step:str,*,sha256_file,run_command,require_project_tool):
    if step!="P6.04": raise DriverError(f"Phase-6 home step is not registered: {step}")
    sp=root/"v1/src/shell/sh.asm"; text=sp.read_text()
    macro=text.split("MACRO EMIT_P604_HOME_ROUTINES",1)[1].split("ENDM",1)[0]
    assertions=[
      {"name":"fixed-home-prefix-only","passed":"ld (hl),'/'" in macro and "ld (hl),'h'" in macro and "ld (hl),'o'" in macro and "ld (hl),'m'" in macro and "ld (hl),'e'" in macro},
      {"name":"no-dynamic-mkdir-surface","passed":"mkdir" not in macro.lower()},
      {"name":"chdir-after-full-path-termination","passed":macro.index("ld (hl),a") < macro.index("ld a,SYS_CHDIR")},
      {"name":"pwd-reads-kernel-cwd","passed":"sh_p604_getcwd:" in macro and "SYS_GETCWD" in macro},
      {"name":"username-revalidated-before-path-write","passed":macro.index("cp 9") < macro.index("ld (hl),'/'")},
    ]
    require(all(a["passed"] for a in assertions),"P6.04 static contract failure")
    asm=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus"); build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    sf=build/"p604-shell-fixture.asm"
    sf.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/shell/sh.asm"
    ORG $C000
p604_start:
    EMIT_P604_HOME_ROUTINES
p604_end:
    SAVEBIN "p604-shell-fixture.bin",p604_start,p604_end-p604_start
""",encoding="utf-8",newline="\n")
    sr=run_command([asm,"--nologo","--lst=p604-shell-fixture.lst","--sym=p604-shell-fixture.sym","p604-shell-fixture.asm"],cwd=build,timeout_seconds=30)
    require(not sr.timed_out and sr.exit_code==0,f"P6.04 shell fixture failed: {sr.stderr or sr.stdout}")
    image=(build/"p604-shell-fixture.bin").read_bytes(); mp=build/"p604-home.mex1"; mp.write_bytes(mex1(image))
    inspector=require_project_tool(root,"v1/tools-host/inspect-mex/inspect.py")
    ir=run_command([sys.executable,inspector,str(mp),"--base","0x6000"],cwd=root,timeout_seconds=10)
    require(not ir.timed_out and ir.exit_code==0,f"P6.04 MEX1 inspect failed: {ir.stderr or ir.stdout}")
    maketap=load_module(root/"v1/tools-host/maketap/maketap.py","zxux_p604_maketap")
    tap=maketap.m48o_blocks(maketap.M48OObject("sh",maketap.M48O_BIN,maketap.DIR_BIN,mp.read_bytes())); tp=build/"p604-home.tap"; tp.write_bytes(tap)
    require(tap==maketap.m48o_blocks(maketap.M48OObject("sh",maketap.M48O_BIN,maketap.DIR_BIN,mp.read_bytes())),"P6.04 TAP rebuild mismatch")
    gf=build/"p604-gateway.asm"
    gf.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    ORG $E000
p604_gate:
    cp SYS_CHDIR
    jr z,p604_chdir
    cp SYS_GETCWD
    jr z,p604_getcwd
    ld a,E_NOTSUP
    scf
    ret
p604_chdir:
    ld de,$A300
p604_copy_in:
    ld a,(hl)
    ld (de),a
    inc hl
    inc de
    or a
    jr nz,p604_copy_in
    xor a
    ret
p604_getcwd:
    ld de,$A300
p604_copy_out:
    ld a,b
    or c
    jr z,p604_small
    ld a,(de)
    ld (hl),a
    inc de
    inc hl
    dec bc
    or a
    jr nz,p604_copy_out
    xor a
    ret
p604_small:
    ld a,E_TOOLONG
    scf
    ret
p604_gate_end:
    SAVEBIN "p604-gateway.bin",p604_gate,p604_gate_end-p604_gate
""",encoding="utf-8",newline="\n")
    gr=run_command([asm,"--nologo","--lst=p604-gateway.lst","--sym=p604-gateway.sym","p604-gateway.asm"],cwd=build,timeout_seconds=30)
    require(not gr.timed_out and gr.exit_code==0,f"P6.04 gateway fixture failed: {gr.stderr or gr.stdout}")
    if action=="test":
        sy=phase3_open_descriptions._symbols(build/"p604-shell-fixture.sym",("sh_p604_session_home","sh_p604_getcwd","E_INVAL"))
        shell=(build/"p604-shell-fixture.bin").read_bytes(); gate=(build/"p604-gateway.bin").read_bytes()
        user=b"alice"; expected=b"/home/alice\0"
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._ld_hl(USER_ADDR)+b"\x01"+word(len(user))+phase1._ld_de(HOME_ADDR))
        code+=phase1._call(sy["sh_p604_session_home"])+phase1._jp_c(FAIL_PC)
        code+=phase1._ld_hl(PWD_ADDR)+b"\x01"+word(24)+phase1._call(sy["sh_p604_getcwd"])+phase1._jp_c(FAIL_PC)
        for off,val in enumerate(expected):
            code+=expect_byte(HOME_ADDR+off,val)+expect_byte(PWD_ADDR+off,val)
        code+=phase1._jp(PASS_PC)
        run_sna(root,bytes(code),patch=patch(shell,gate,user))
        bad=b"../root"
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._ld_hl(USER_ADDR)+b"\x01"+word(len(bad))+phase1._ld_de(HOME_ADDR))
        code+=phase1._call(sy["sh_p604_session_home"])+b"\xD2"+word(FAIL_PC)
        code+=bytes((0xFE,sy["E_INVAL"]&255))+phase1._jp_nz(FAIL_PC)
        code+=expect_byte(HOME_ADDR,0xA5)+expect_byte(KERNEL_CWD,0)+phase1._jp(PASS_PC)
        run_sna(root,bytes(code),patch=patch(shell,gate,bad))
        assertions += [{"name":"fuse-pwd-exact-home-user","passed":True},{"name":"fuse-invalid-topology-cannot-escape-home","passed":True}]
    hashes={
      "v1/src/shell/sh.asm":sha256_file(sp),"v1/build/p604-home.mex1":sha256_file(mp),"v1/build/p604-home.tap":sha256_file(tp),
      "v1/tools-host/test-driver/phase6_home.py":sha256_file(root/"v1/tools-host/test-driver/phase6_home.py"),"v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
      "v1/dist/certification/P6.03.build.json":sha256_file(root/"v1/dist/certification/P6.03.build.json"),"v1/dist/certification/P6.03.test.json":sha256_file(root/"v1/dist/certification/P6.03.test.json"),"v1/dist/media/P6.03/manifest.json":sha256_file(root/"v1/dist/media/P6.03/manifest.json")}
    return [sr,ir,gr],hashes,assertions
