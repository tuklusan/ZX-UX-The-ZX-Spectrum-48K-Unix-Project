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
from driver_core import DriverError
from fuse_harness import FAIL_PC, PASS_PC, run_sna
import phase1, phase3_open_descriptions

SHELL_BASE=0xC000
GATE_BASE=0xE000
INPUT=0xA000
DEST=0xA300

class P607Error(DriverError): pass
def require(v,m):
    if not v: raise P607Error(m)
def word(v): return bytes((v&255,(v>>8)&255))
def expect_byte(addr,val): return b"\x3A"+word(addr)+bytes((0xFE,val&255))+phase1._jp_nz(FAIL_PC)
def patch(shell,gate,data):
    def p(ram):
        ram[SHELL_BASE-0x4000:SHELL_BASE-0x4000+len(shell)]=shell
        ram[GATE_BASE-0x4000:GATE_BASE-0x4000+len(gate)]=gate
        ram[INPUT-0x4000:INPUT-0x4000+len(data)]=data
        ram[DEST-0x4000:DEST-0x4000+260]=b"\xA5"*260
    return p

def dispatch(root:Path,action:str,step:str,*,sha256_file,run_command,require_project_tool):
    if step!="P6.07": raise DriverError(f"Phase-6 line-input step is not registered: {step}")
    sp=root/"v1/src/shell/sh.asm"; text=sp.read_text(); macro=text.split("MACRO EMIT_P607_LINE_ROUTINES",1)[1].split("ENDM",1)[0]
    assertions=[
      {"name":"line-bound-exact-247","passed":"P607_LINE_MAX            EQU 247" in text and "cp P607_LINE_MAX" in macro},
      {"name":"input-through-sys-read-handle-zero","passed":"ld de,0" in macro and "ld a,SYS_READ" in macro and "call SYSCALL_GATEWAY" in macro},
      {"name":"transactional-destination","passed":macro.index("p607_scratch") < macro.index("sh_p607_commit:") and macro.index("ld de,(p607_dest)") > macro.index("sh_p607_commit:")},
      {"name":"editing-backspace-owned-in-line-path","passed":"cp $08" in macro and "cp $7f" in macro and "sh_p607_backspace:" in macro},
      {"name":"overlength-e-toolong","passed":"ld a,E_TOOLONG" in macro},
    ]
    require(all(a["passed"] for a in assertions),"P6.07 static contract failure")
    asm=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus"); build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    sf=build/"p607-shell-fixture.asm"
    sf.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/shell/sh.asm"
    ORG $C000
p607_start:
    EMIT_P607_LINE_ROUTINES
p607_end:
    SAVEBIN "p607-shell-fixture.bin",p607_start,p607_end-p607_start
""",encoding="utf-8",newline="\n")
    sr=run_command([asm,"--nologo","--lst=p607-shell-fixture.lst","--sym=p607-shell-fixture.sym","p607-shell-fixture.asm"],cwd=build,timeout_seconds=30)
    require(not sr.timed_out and sr.exit_code==0,f"P6.07 shell fixture failed: {sr.stderr or sr.stdout}")
    gf=build/"p607-gateway.asm"
    gf.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    ORG $E000
p607_gate:
    cp SYS_READ
    jr nz,p607_notsup
    ld a,d
    or a
    jr nz,p607_bad
    ld a,e
    or a
    jr nz,p607_bad
    ld a,b
    or a
    jr nz,p607_bad
    ld a,c
    cp 1
    jr nz,p607_bad
    push hl
    ld hl,(p607_source)
    ld a,(hl)
    inc hl
    ld (p607_source),hl
    pop hl
    ld (hl),a
    ld hl,1
    xor a
    ret
p607_bad:
    ld a,E_INVAL
    scf
    ret
p607_notsup:
    ld a,E_NOTSUP
    scf
    ret
p607_source: dw $A000
p607_gate_end:
    SAVEBIN "p607-gateway.bin",p607_gate,p607_gate_end-p607_gate
""",encoding="utf-8",newline="\n")
    gr=run_command([asm,"--nologo","--lst=p607-gateway.lst","--sym=p607-gateway.sym","p607-gateway.asm"],cwd=build,timeout_seconds=30)
    require(not gr.timed_out and gr.exit_code==0,f"P6.07 gateway fixture failed: {gr.stderr or gr.stdout}")
    if action=="test":
        sy=phase3_open_descriptions._symbols(build/"p607-shell-fixture.sym",("sh_p607_read_line","E_TOOLONG"))
        shell=(build/"p607-shell-fixture.bin").read_bytes(); gate=(build/"p607-gateway.bin").read_bytes()

        data=b"a"*247+b"\n"
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+b"\xDD\x21"+word(DEST)+phase1._call(sy["sh_p607_read_line"])+phase1._jp_c(FAIL_PC))
        code+=phase1._ld_de(247)+b"\xB7\xED\x52"+phase1._jp_nz(FAIL_PC)
        for off in range(247): code+=expect_byte(DEST+off,ord("a"))
        code+=expect_byte(DEST+247,0)+expect_byte(DEST+248,0xA5)+phase1._jp(PASS_PC)
        run_sna(root,bytes(code),patch=patch(shell,gate,data))

        data=b"a"*248+b"\n"
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+b"\xDD\x21"+word(DEST)+phase1._call(sy["sh_p607_read_line"])+b"\xD2"+word(FAIL_PC))
        code+=bytes((0xFE,sy["E_TOOLONG"]&255))+phase1._jp_nz(FAIL_PC)
        for off in range(0,260,17): code+=expect_byte(DEST+off,0xA5)
        code+=phase1._jp(PASS_PC)
        run_sna(root,bytes(code),patch=patch(shell,gate,data))

        data=b"ab\x08c\n"
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+b"\xDD\x21"+word(DEST)+phase1._call(sy["sh_p607_read_line"])+phase1._jp_c(FAIL_PC))
        code+=expect_byte(DEST,ord("a"))+expect_byte(DEST+1,ord("c"))+expect_byte(DEST+2,0)+phase1._jp(PASS_PC)
        run_sna(root,bytes(code),patch=patch(shell,gate,data))
        assertions += [
          {"name":"fuse-247-byte-line-accepted","passed":True},
          {"name":"fuse-248-byte-line-toolong-destination-unchanged","passed":True},
          {"name":"fuse-backspace-editing","passed":True},
        ]
    hashes={
      "v1/src/shell/sh.asm":sha256_file(sp),
      "v1/tools-host/test-driver/phase6_line.py":sha256_file(root/"v1/tools-host/test-driver/phase6_line.py"),
      "v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
      "v1/dist/certification/P6.06.build.json":sha256_file(root/"v1/dist/certification/P6.06.build.json"),
      "v1/dist/certification/P6.06.test.json":sha256_file(root/"v1/dist/certification/P6.06.test.json"),
      "v1/dist/media/P6.06/manifest.json":sha256_file(root/"v1/dist/media/P6.06/manifest.json")}
    return [sr,gr],hashes,assertions
