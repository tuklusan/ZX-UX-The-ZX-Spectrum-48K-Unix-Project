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

SHELL=0xC000; GATE=0xE000; DESC=0xA000; INP=0xA020; OUT=0xA040; TAPE=0xA060

class P618Error(DriverError): pass
def require(v,m):
    if not v: raise P618Error(m)
def word(v): return bytes((v&255,(v>>8)&255))
def expect_byte(a,v): return b"\x3A"+word(a)+bytes((0xFE,v&255))+phase1._jp_nz(FAIL_PC)

def patch(shell,gate,desc,fail_output=False):
    def p(ram):
        ram[SHELL-0x4000:SHELL-0x4000+len(shell)]=shell
        ram[GATE-0x4000:GATE-0x4000+len(gate)]=gate
        ram[DESC-0x4000:DESC-0x4000+len(desc)]=desc
        ram[INP-0x4000:INP-0x4000+10]=b"/tmp/in\0"
        ram[OUT-0x4000:OUT-0x4000+11]=b"/tmp/out\0"
        ram[TAPE-0x4000:TAPE-0x4000+10]=b"/dev/tape\0"
        ram[0xE180-0x4000]=3
        ram[0xE181-0x4000]=1 if fail_output else 0
        ram[0xE182-0x4000]=0
        ram[0xE183-0x4000]=0
        ram[0xE184-0x4000]=0
    return p

def dispatch(root:Path,action:str,step:str,*,sha256_file,run_command,require_project_tool):
    if step!="P6.18": raise DriverError(f"Phase-6 external-redirection step is not registered: {step}")
    sp=root/"v1/src/shell/sh.asm"; text=sp.read_text(); macro=text.split("MACRO EMIT_P618_EXTERNAL_REDIR_ROUTINES",1)[1].split("ENDM",1)[0]
    assertions=[
      {"name":"one-in-one-out-bound","passed":"cp 2" in macro and macro.count("cp 2")>=2},
      {"name":"input-open-read-only","passed":"ld c,O_READ" in macro},
      {"name":"truncate-flags-dat","passed":"O_WRITE+O_CREATE+O_TRUNC" in macro and "ld b,OBJ_DAT" in macro},
      {"name":"append-flags-dat","passed":"O_WRITE+O_CREATE+O_APPEND" in macro and "ld b,OBJ_DAT" in macro},
      {"name":"tape-random-redirection-rejected","passed":"p618_tape_path: db '/dev/tape',0" in macro and "ld a,E_NOTSUP" in macro},
      {"name":"allocation-failure-closes-prior-input","passed":"sh_p618_rollback:" in macro and "ld a,SYS_CLOSE" in macro},
    ]
    require(all(a["passed"] for a in assertions),"P6.18 static contract failure")
    asm=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus"); build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    sf=build/"p618-shell-fixture.asm"
    sf.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
OBJ_DAT EQU $07
    INCLUDE "../src/shell/sh.asm"
    ORG $C000
p618_start:
    EMIT_P618_EXTERNAL_REDIR_ROUTINES
p618_end:
    SAVEBIN "p618-shell-fixture.bin",p618_start,p618_end-p618_start
""",encoding="utf-8",newline="\n")
    sr=run_command([asm,"--nologo","--lst=p618-shell-fixture.lst","--sym=p618-shell-fixture.sym","p618-shell-fixture.asm"],cwd=build,timeout_seconds=30)
    require(not sr.timed_out and sr.exit_code==0,f"P6.18 shell fixture failed: {sr.stderr or sr.stdout}")
    gf=build/"p618-gateway.asm"
    gf.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    ORG $E000
p618_gate:
    cp SYS_OPEN
    jr z,p618_open
    cp SYS_CLOSE
    jr z,p618_close
    ld a,E_NOTSUP
    scf
    ret
p618_open:
    ld a,(p618_fail_output)
    or a
    jr z,p618_open_ok
    ld a,c
    and O_WRITE
    jr z,p618_open_ok
    ld a,E_NOSPC
    scf
    ret
p618_open_ok:
    ld a,(p618_next_handle)
    ld l,a
    ld h,0
    inc a
    ld (p618_next_handle),a
    ld a,(p618_open_count)
    inc a
    ld (p618_open_count),a
    xor a
    ret
p618_close:
    ld a,(p618_close_count)
    inc a
    ld (p618_close_count),a
    ld hl,0
    xor a
    ret
    ORG $E180
p618_next_handle: db 3
p618_fail_output: db 0
p618_open_count: db 0
p618_close_count: db 0
p618_gate_end:
    SAVEBIN "p618-gateway.bin",p618_gate,p618_gate_end-p618_gate
""",encoding="utf-8",newline="\n")
    gr=run_command([asm,"--nologo","--lst=p618-gateway.lst","--sym=p618-gateway.sym","p618-gateway.asm"],cwd=build,timeout_seconds=30)
    require(not gr.timed_out and gr.exit_code==0,f"P6.18 gateway fixture failed: {gr.stderr or gr.stdout}")
    if action=="test":
        sy=phase3_open_descriptions._symbols(build/"p618-shell-fixture.sym",("sh_p618_open_redirections","p618_input_handle","p618_output_handle","E_NOTSUP","E_INVAL"))
        shell=(build/"p618-shell-fixture.bin").read_bytes(); gate=(build/"p618-gateway.bin").read_bytes()
        # < in > out
        desc=bytes((1,1))+word(INP)+word(OUT)+bytes((1,))
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+b"\xDD\x21"+word(DESC)+phase1._call(sy["sh_p618_open_redirections"])+phase1._jp_c(FAIL_PC))
        code+=expect_byte(sy["p618_input_handle"],3)+expect_byte(sy["p618_output_handle"],4)+expect_byte(0xE182,2)+expect_byte(0xE183,0)+phase1._jp(PASS_PC)
        run_sna(root,bytes(code),patch=patch(shell,gate,desc))
        # output allocation failure closes prior input.
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+b"\xDD\x21"+word(DESC)+phase1._call(sy["sh_p618_open_redirections"])+b"\xD2"+word(FAIL_PC))
        code+=expect_byte(sy["p618_input_handle"],0xFF)+expect_byte(0xE183,1)+phase1._jp(PASS_PC)
        run_sna(root,bytes(code),patch=patch(shell,gate,desc,True))
        # /dev/tape rejected before open.
        desc=bytes((0,1))+word(0)+word(TAPE)+bytes((2,))
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+b"\xDD\x21"+word(DESC)+phase1._call(sy["sh_p618_open_redirections"])+b"\xD2"+word(FAIL_PC))
        code+=bytes((0xFE,sy["E_NOTSUP"]&255))+phase1._jp_nz(FAIL_PC)+expect_byte(0xE182,0)+phase1._jp(PASS_PC)
        run_sna(root,bytes(code),patch=patch(shell,gate,desc))
        # duplicate output count rejected before open.
        desc=bytes((0,2))+word(0)+word(OUT)+bytes((1,))
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+b"\xDD\x21"+word(DESC)+phase1._call(sy["sh_p618_open_redirections"])+b"\xD2"+word(FAIL_PC))
        code+=bytes((0xFE,sy["E_INVAL"]&255))+phase1._jp_nz(FAIL_PC)+expect_byte(0xE182,0)+phase1._jp(PASS_PC)
        run_sna(root,bytes(code),patch=patch(shell,gate,desc))
        assertions += [
          {"name":"fuse-golden-input-output-redirection","passed":True},
          {"name":"fuse-output-allocation-failure-rolls-back-input","passed":True},
          {"name":"fuse-dev-tape-redirection-rejected-before-open","passed":True},
          {"name":"fuse-duplicate-redirection-rejected-before-open","passed":True},
        ]
    hashes={
      "v1/src/shell/sh.asm":sha256_file(sp),
      "v1/tools-host/test-driver/phase6_external_redir.py":sha256_file(root/"v1/tools-host/test-driver/phase6_external_redir.py"),
      "v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
      "v1/dist/certification/P6.17.build.json":sha256_file(root/"v1/dist/certification/P6.17.build.json"),
      "v1/dist/certification/P6.17.test.json":sha256_file(root/"v1/dist/certification/P6.17.test.json"),
      "v1/dist/media/P6.17/manifest.json":sha256_file(root/"v1/dist/media/P6.17/manifest.json")}
    return [sr,gr],hashes,assertions
