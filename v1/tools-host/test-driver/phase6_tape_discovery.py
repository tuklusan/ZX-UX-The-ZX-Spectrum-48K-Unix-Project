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

SHELL=0xC000
GATE=0xE000
PROC=0xA000
OUT=0xA100
REPLY=0xA200
MOTION=0xA300

class P615Error(DriverError): pass
def require(v,m):
    if not v: raise P615Error(m)
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
def patch(shell,gate,reply):
    def p(ram):
        ram[SHELL-0x4000:SHELL-0x4000+len(shell)]=shell
        ram[GATE-0x4000:GATE-0x4000+len(gate)]=gate
        ram[PROC-0x4000:PROC-0x4000+16]=b"\0"*16
        ram[OUT-0x4000:OUT-0x4000+80]=b"\xA5"*80
        ram[REPLY-0x4000]=reply
        ram[MOTION-0x4000]=0x5A
    return p

def dispatch(root:Path,action:str,step:str,*,sha256_file,run_command,require_project_tool):
    if step!="P6.15": raise DriverError(f"Phase-6 tape discovery step is not registered: {step}")
    sp=root/"v1/src/shell/sh.asm"; text=sp.read_text(); macro=text.split("MACRO EMIT_P615_TAPE_DISCOVERY_ROUTINES",1)[1].split("ENDM",1)[0]
    assertions=[
      {"name":"only-tape-backed-prompts","passed":"cp STATE_TAPE_BACKED" in macro},
      {"name":"allow-tape-bit-set-after-read","passed":macro.index("ld a,SYS_READ") < macro.index("or P615_ALLOW_TAPE")},
      {"name":"shell-owns-visible-prompt","passed":"SYS_CON_WRITE" in macro and "p615_prompt:" in macro},
      {"name":"decline-e-again","passed":"ld a,E_AGAIN" in macro},
      {"name":"no-tape-motion-syscall-before-consent","passed":all(x not in macro for x in ("SYS_TAPE_LOAD","SYS_TAPE_SCAN","SYS_TAPE_SAVE","SYS_TAPE_VERIFY"))},
    ]
    require(all(a["passed"] for a in assertions),"P6.15 static contract failure")
    asm=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus"); build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    sf=build/"p615-shell-fixture.asm"
    sf.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/shell/sh.asm"
    ORG $C000
p615_start:
    EMIT_P615_TAPE_DISCOVERY_ROUTINES
p615_end:
    SAVEBIN "p615-shell-fixture.bin",p615_start,p615_end-p615_start
""",encoding="utf-8",newline="\n")
    sr=run_command([asm,"--nologo","--lst=p615-shell-fixture.lst","--sym=p615-shell-fixture.sym","p615-shell-fixture.asm"],cwd=build,timeout_seconds=30)
    require(not sr.timed_out and sr.exit_code==0,f"P6.15 shell fixture failed: {sr.stderr or sr.stdout}")
    image=(build/"p615-shell-fixture.bin").read_bytes(); mp=build/"p615-tape-discovery.mex1"; mp.write_bytes(mex1(image))
    maketap=load_module(root/"v1/tools-host/maketap/maketap.py","zxux_p615_maketap")
    tap=maketap.m48o_blocks(maketap.M48OObject("sh",maketap.M48O_BIN,maketap.DIR_BIN,mp.read_bytes())); tp=build/"p615-tape-discovery.tap"; tp.write_bytes(tap)

    gf=build/"p615-gateway.asm"
    gf.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    ORG $E000
p615_gate:
    cp SYS_CON_WRITE
    jr z,p615_write
    cp SYS_READ
    jr z,p615_read
    ld a,E_NOTSUP
    scf
    ret
p615_write:
    ld de,$A100
    ldir
    xor a
    ret
p615_read:
    ld a,d
    or e
    jr nz,p615_bad
    ld a,($A200)
    ld (hl),a
    ld hl,1
    xor a
    ret
p615_bad:
    ld a,E_INVAL
    scf
    ret
p615_gate_end:
    SAVEBIN "p615-gateway.bin",p615_gate,p615_gate_end-p615_gate
""",encoding="utf-8",newline="\n")
    gr=run_command([asm,"--nologo","--lst=p615-gateway.lst","--sym=p615-gateway.sym","p615-gateway.asm"],cwd=build,timeout_seconds=30)
    require(not gr.timed_out and gr.exit_code==0,f"P6.15 gateway fixture failed: {gr.stderr or gr.stdout}")
    if action=="test":
        sy=phase3_open_descriptions._symbols(build/"p615-shell-fixture.sym",("sh_p615_authorize_tape","P615_PROC1_FLAGS","E_AGAIN"))
        shell=(build/"p615-shell-fixture.bin").read_bytes(); gate=(build/"p615-gateway.bin").read_bytes()
        helper=sy["sh_p615_authorize_tape"]; flags=PROC+sy["P615_PROC1_FLAGS"]
        # resident: no prompt, no tape bit
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+bytes((0x0E,0))+phase1._ld_hl(PROC)+phase1._call(helper)+phase1._jp_c(FAIL_PC))
        code+=expect_byte(flags,0)+expect_byte(OUT,0xA5)+expect_byte(MOTION,0x5A)+phase1._jp(PASS_PC)
        run_sna(root,bytes(code),patch=patch(shell,gate,ord("n")))
        # consent
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+bytes((0x0E,1))+phase1._ld_hl(PROC)+phase1._call(helper)+phase1._jp_c(FAIL_PC))
        code+=expect_byte(flags,1)+expect_byte(OUT,ord("c"))+expect_byte(MOTION,0x5A)+phase1._jp(PASS_PC)
        run_sna(root,bytes(code),patch=patch(shell,gate,ord("y")))
        # decline
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+bytes((0x0E,1))+phase1._ld_hl(PROC)+phase1._call(helper)+b"\xD2"+word(FAIL_PC))
        code+=bytes((0xFE,sy["E_AGAIN"]&255))+phase1._jp_nz(FAIL_PC)+expect_byte(flags,0)+expect_byte(MOTION,0x5A)+phase1._jp(PASS_PC)
        run_sna(root,bytes(code),patch=patch(shell,gate,ord("n")))
        assertions += [{"name":"fuse-resident-no-prompt","passed":True},{"name":"fuse-consent-sets-allow-tape","passed":True},{"name":"fuse-decline-keeps-tape-unmoved","passed":True}]
    hashes={
      "v1/src/shell/sh.asm":sha256_file(sp),"v1/build/p615-tape-discovery.mex1":sha256_file(mp),"v1/build/p615-tape-discovery.tap":sha256_file(tp),
      "v1/tools-host/test-driver/phase6_tape_discovery.py":sha256_file(root/"v1/tools-host/test-driver/phase6_tape_discovery.py"),"v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
      "v1/dist/certification/P6.14.build.json":sha256_file(root/"v1/dist/certification/P6.14.build.json"),"v1/dist/certification/P6.14.test.json":sha256_file(root/"v1/dist/certification/P6.14.test.json"),"v1/dist/media/P6.14/manifest.json":sha256_file(root/"v1/dist/media/P6.14/manifest.json")}
    return [sr,gr],hashes,assertions
