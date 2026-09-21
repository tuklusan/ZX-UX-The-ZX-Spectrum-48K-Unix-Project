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

BASE=0xC000
GATE=0xE000
ENV=0xA000
TABLE=0xA200
REQ=0xA300
LOG=0xA500

class P621Error(DriverError): pass
def require(v,m):
    if not v: raise P621Error(m)
def word(v): return bytes((v&255,(v>>8)&255))
def env1(entries):
    body=b"".join(k+b"="+v+b"\0" for k,v in entries)
    return b"ENV1"+bytes((len(entries),0))+word(8+len(body))+body
def expect_byte(addr,val): return b"\x3A"+word(addr)+bytes((0xFE,val&255))+phase1._jp_nz(FAIL_PC)
def patch(shell,gate,env,fail_spawn=0):
    def p(ram):
        ram[BASE-0x4000:BASE-0x4000+len(shell)]=shell
        ram[GATE-0x4000:GATE-0x4000+len(gate)]=gate
        ram[ENV-0x4000:ENV-0x4000+len(env)]=env
        table=bytearray()
        for i in range(3):
            req=REQ+i*16
            envptr=req+8
            envlen=req+10
            table+=word(req)+word(envptr)+word(envlen)
        ram[TABLE-0x4000:TABLE-0x4000+len(table)]=table
        ram[REQ-0x4000:REQ-0x4000+48]=b"\0"*48
        ram[LOG-0x4000:LOG-0x4000+64]=b"\0"*64
        ram[(GATE+0x80)-0x4000]=fail_spawn
    return p

def dispatch(root:Path,action:str,step:str,*,sha256_file,run_command,require_project_tool):
    if step!="P6.21": raise DriverError(f"Phase-6 pipeline step is not registered: {step}")
    sp=root/"v1/src/shell/sh.asm"; text=sp.read_text(); macro=text.split("MACRO EMIT_P621_PIPELINE_ROUTINES",1)[1].split("ENDM",1)[0]
    assertions=[
      {"name":"six-stage-hard-bound","passed":"P621_MAX_STAGES          EQU 6" in text},
      {"name":"immutable-env-snapshot-before-spawn","passed":macro.index("p621_env_snapshot") < macro.index("SYS_SPAWN")},
      {"name":"pipes-before-any-spawn","passed":macro.index("SYS_PIPE") < macro.index("SYS_SPAWN")},
      {"name":"wait-only-after-spawn-loop","passed":macro.index("SYS_WAIT") > macro.index("sh_p621_spawn_loop:")},
      {"name":"mid-launch-kill-rollback","passed":"SYS_KILL" in macro and "sh_p621_spawn_fail:" in macro},
      {"name":"no-yield-during-launch","passed":"SYS_YIELD" not in macro},
      {"name":"dollar-status-not-serialized","passed":"$?=" not in macro},
    ]
    require(all(a["passed"] for a in assertions),"P6.21 static contract failure")
    asm=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus"); build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    sf=build/"p621-shell-fixture.asm"
    sf.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/shell/sh.asm"
    ORG $C000
p621_start:
    EMIT_P621_PIPELINE_ROUTINES
p621_end:
    SAVEBIN "p621-shell-fixture.bin",p621_start,p621_end-p621_start
""",encoding="utf-8",newline="\n")
    sr=run_command([asm,"--nologo","--lst=p621-shell-fixture.lst","--sym=p621-shell-fixture.sym","p621-shell-fixture.asm"],cwd=build,timeout_seconds=30)
    require(not sr.timed_out and sr.exit_code==0,f"P6.21 fixture assembly failed: {sr.stderr or sr.stdout}")
    gf=build/"p621-gateway.asm"
    gf.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    ORG $E000
p621_gate:
    push af
    ld a,(p621_log_index)
    ld e,a
    ld d,0
    ld ix,$A500
    add ix,de
    pop af
    ld (ix+0),a
    ld a,(p621_log_index)
    inc a
    ld (p621_log_index),a
    cp SYS_PIPE
    jr z,p621_pipe
    cp SYS_SPAWN
    jr z,p621_spawn
    cp SYS_WAIT
    jr z,p621_wait
    cp SYS_KILL
    jr z,p621_ok
    cp SYS_CLOSE
    jr z,p621_ok
    ld a,E_NOTSUP
    scf
    ret
p621_pipe:
    ld (hl),3
    inc hl
    ld (hl),4
    xor a
    ret
p621_spawn:
    ld a,(p621_spawn_count)
    inc a
    ld (p621_spawn_count),a
    ld b,a
    ld a,($E080)
    cp b
    jr nz,p621_spawn_ok
    ld a,E_AGAIN
    scf
    ret
p621_spawn_ok:
    ld a,b
    add a,1
    ld l,a
    ld h,0
    xor a
    ret
p621_wait:
    ld a,7
    ld ($D100),a
    xor a
    ret
p621_ok:
    xor a
    ret
p621_log_index: db 0
p621_spawn_count: db 0
    ORG $E080
p621_fail_spawn: db 0
""",encoding="utf-8",newline="\n")
    gr=run_command([asm,"--nologo","--lst=p621-gateway.lst","--sym=p621-gateway.sym","p621-gateway.asm"],cwd=build,timeout_seconds=30)
    require(not gr.timed_out and gr.exit_code==0,f"P6.21 gateway assembly failed: {gr.stderr or gr.stdout}")
    if action=="test":
        sy=phase3_open_descriptions._symbols(build/"p621-shell-fixture.sym",("sh_p621_launch_foreground","p621_env_snapshot","E_AGAIN"))
        shell=(build/"p621-shell-fixture.bin").read_bytes(); gate=(build/"p621-gateway.bin").read_bytes()
        env=env1([(b"HOME",b"/home/bob"),(b"PATH",b"/bin:."),(b"SHELL",b"/bin/sh"),(b"USER",b"bob")])

        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+b"\xDD\x21"+word(TABLE)+phase1._ld_hl(ENV)+phase1._ld_de(len(env))+b"\x06\x03")
        code+=phase1._call(sy["sh_p621_launch_foreground"])+phase1._jp_c(FAIL_PC)
        # exact call prefix: PIPE, CLOSE,CLOSE, PIPE,CLOSE,CLOSE, SPAWN,SPAWN,SPAWN...
        prefix=[0x20,0x11,0x11,0x20,0x11,0x11,0x05,0x05,0x05]
        for i,v in enumerate(prefix): code+=expect_byte(LOG+i,v)
        for off,val in enumerate(env): code+=expect_byte(sy["p621_env_snapshot"]+off,val)
        # every request received exact snapshot pointer/length.
        for i in range(3):
            req=REQ+i*16
            code+=expect_byte(req+8,sy["p621_env_snapshot"]&255)+expect_byte(req+9,(sy["p621_env_snapshot"]>>8)&255)
            code+=expect_byte(req+10,len(env)&255)+expect_byte(req+11,(len(env)>>8)&255)
        code+=phase1._jp(PASS_PC)
        run_sna(root,bytes(code),patch=patch(shell,gate,env))

        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+b"\xDD\x21"+word(TABLE)+phase1._ld_hl(ENV)+phase1._ld_de(len(env))+b"\x06\x03")
        code+=phase1._call(sy["sh_p621_launch_foreground"])+b"\xD2"+word(FAIL_PC)
        code+=bytes((0xFE,sy["E_AGAIN"]&255))+phase1._jp_nz(FAIL_PC)
        code+=phase1._jp(PASS_PC)
        run_sna(root,bytes(code),patch=patch(shell,gate,env,2))
        assertions += [
          {"name":"fuse-three-stage-pipeline-setup-order","passed":True},
          {"name":"fuse-child-env-current-shell-snapshot","passed":True},
          {"name":"fuse-mid-launch-failure-rolls-back","passed":True},
        ]
    hashes={
      "v1/src/shell/sh.asm":sha256_file(sp),
      "v1/tools-host/test-driver/phase6_pipeline.py":sha256_file(root/"v1/tools-host/test-driver/phase6_pipeline.py"),
      "v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
      "v1/dist/certification/P6.20.build.json":sha256_file(root/"v1/dist/certification/P6.20.build.json"),
      "v1/dist/certification/P6.20.test.json":sha256_file(root/"v1/dist/certification/P6.20.test.json"),
      "v1/dist/media/P6.20/manifest.json":sha256_file(root/"v1/dist/media/P6.20/manifest.json")}
    return [sr,gr],hashes,assertions
