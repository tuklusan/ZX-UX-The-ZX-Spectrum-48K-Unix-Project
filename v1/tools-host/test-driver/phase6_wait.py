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
from fuse_harness import FAIL_PC,PASS_PC,run_sna
import phase1,phase3_open_descriptions

BASE=0xC000
GATE=0xE000
ARG=0xA000
NAME2=0xA040
NAME4=0xA050
STATUS=0xA060

class E(DriverError): pass
def req(v,m):
    if not v: raise E(m)
def word(v): return bytes((v&255,(v>>8)&255))
def expect(a,v): return b"\x3A"+word(a)+bytes((0xFE,v&255))+phase1._jp_nz(FAIL_PC)

def patch(module,gate,arg=b"",name2=b"job2\0\0\0\0\0\0",name4=b"job4\0\0\0\0\0\0"):
    def p(ram):
        ram[BASE-0x4000:BASE-0x4000+len(module)]=module
        ram[GATE-0x4000:GATE-0x4000+len(gate)]=gate
        ram[ARG-0x4000:ARG-0x4000+len(arg)]=arg
        ram[NAME2-0x4000:NAME2-0x4000+10]=name2[:10]
        ram[NAME4-0x4000:NAME4-0x4000+10]=name4[:10]
        ram[STATUS-0x4000]=0xA5
    return p

def add_job(symbol,pid,name_addr):
    return bytes((0x3E,pid))+phase1._ld_hl(name_addr)+phase1._call(symbol)+phase1._jp_c(FAIL_PC)

def dispatch(root:Path,action:str,step:str,*,sha256_file,run_command,require_project_tool):
    if step!="P6.25": raise DriverError(f"Phase-6 wait step is not registered: {step}")
    sp=root/"v1/src/shell/sh.asm"; text=sp.read_text(); m=text.split("MACRO EMIT_P625_WAIT_ROUTINES",1)[1].split("ENDM",1)[0]
    assertions=[
      {"name":"wait-exact-zero-or-one-operands","passed":"cp 1" in m and "sh_p625_invalid:" in m},
      {"name":"wait-specific-uses-sys-wait","passed":"ld a,SYS_WAIT" in m and "p625_wait_req" in m},
      {"name":"wait-all-scans-only-bounded-job-table","passed":"p624_jobs" in m and "cp P624_JOB_MAX" in m},
      {"name":"wait-success-removes-shell-job","passed":"call sh_p624_job_remove" in m},
      {"name":"decimal-nonchild-maps-e-child","passed":"sh_p625_parse_pid:" in m and "ld a,E_CHILD" in m},
    ]
    req(all(x["passed"] for x in assertions),"P6.25 static contract failure")
    asm=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus"); build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    sf=build/"p625-fixture.asm"
    sf.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/shell/sh.asm"
    ORG $C000
p625_start:
    EMIT_P624_JOBS_ROUTINES
    EMIT_P625_WAIT_ROUTINES
p625_end:
    SAVEBIN "p625-fixture.bin",p625_start,p625_end-p625_start
""",encoding="utf-8",newline="\n")
    sr=run_command([asm,"--nologo","--lst=p625-fixture.lst","--sym=p625-fixture.sym","p625-fixture.asm"],cwd=build,timeout_seconds=30)
    req(not sr.timed_out and sr.exit_code==0,f"P6.25 fixture failed: {sr.stderr or sr.stdout}")

    gf=build/"p625-gateway.asm"
    gf.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    ORG $E000
p625_gate:
    cp SYS_WAIT
    jr nz,p625_notsup
    ld a,(hl)
    cp 6
    jr z,p625_child_error
    ld e,a
    ld d,0
    inc hl
    inc hl
    ld c,(hl)
    inc hl
    ld b,(hl)
    push bc
    ld a,e
    add a,10
    pop hl
    ld (hl),a
    ld a,(p625_calls)
    inc a
    ld (p625_calls),a
    ld a,e
    cp 2
    jr z,p625_mark2
    cp 3
    jr z,p625_mark3
    cp 4
    jr z,p625_mark4
    jr p625_return_pid
p625_mark2:
    ld a,(p625_mask)
    or 4
    ld (p625_mask),a
    jr p625_return_pid
p625_mark3:
    ld a,(p625_mask)
    or 8
    ld (p625_mask),a
    jr p625_return_pid
p625_mark4:
    ld a,(p625_mask)
    or 16
    ld (p625_mask),a
p625_return_pid:
    ld h,0
    ld l,e
    xor a
    ret
p625_child_error:
    ld a,E_CHILD
    scf
    ret
p625_notsup:
    ld a,E_NOTSUP
    scf
    ret
p625_calls: db 0
p625_mask: db 0
p625_gate_end:
    SAVEBIN "p625-gateway.bin",p625_gate,p625_gate_end-p625_gate
""",encoding="utf-8",newline="\n")
    gr=run_command([asm,"--nologo","--lst=p625-gateway.lst","--sym=p625-gateway.sym","p625-gateway.asm"],cwd=build,timeout_seconds=30)
    req(not gr.timed_out and gr.exit_code==0,f"P6.25 gateway failed: {gr.stderr or gr.stdout}")

    if action=="test":
        sy=phase3_open_descriptions._symbols(build/"p625-fixture.sym",("sh_p624_job_add","sh_p625_wait","p624_jobs","E_CHILD","E_INVAL"))
        gy=phase3_open_descriptions._symbols(build/"p625-gateway.sym",("p625_calls","p625_mask"))
        mod=(build/"p625-fixture.bin").read_bytes(); gate=(build/"p625-gateway.bin").read_bytes(); jobs=sy["p624_jobs"]

        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0))
        code+=add_job(sy["sh_p624_job_add"],2,NAME2)+add_job(sy["sh_p624_job_add"],4,NAME4)
        code+=phase1._ld_hl(ARG)+b"\xDD\x21"+word(STATUS)+b"\x06\x00"+phase1._call(sy["sh_p625_wait"])+phase1._jp_c(FAIL_PC)
        code+=expect(jobs,0)+expect(jobs+12,0)+expect(STATUS,14)+expect(gy["p625_calls"],2)+expect(gy["p625_mask"],20)+phase1._jp(PASS_PC)
        run_sna(root,bytes(code),patch=patch(mod,gate))

        arg=b"03\0"
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._ld_hl(ARG)+b"\xDD\x21"+word(STATUS)+b"\x06\x01"+phase1._call(sy["sh_p625_wait"])+phase1._jp_c(FAIL_PC))
        code+=expect(STATUS,13)+expect(gy["p625_calls"],1)+expect(gy["p625_mask"],8)+phase1._jp(PASS_PC)
        run_sna(root,bytes(code),patch=patch(mod,gate,arg))

        arg=b"6\0"
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+add_job(sy["sh_p624_job_add"],2,NAME2))
        code+=phase1._ld_hl(ARG)+b"\xDD\x21"+word(STATUS)+b"\x06\x01"+phase1._call(sy["sh_p625_wait"])+b"\xD2"+word(FAIL_PC)
        code+=bytes((0xFE,sy["E_CHILD"]&255))+phase1._jp_nz(FAIL_PC)+expect(jobs,2)+expect(STATUS,0xA5)+phase1._jp(PASS_PC)
        run_sna(root,bytes(code),patch=patch(mod,gate,arg))

        for arg,argc in ((b"x\0",1),(b"2\0",2)):
            code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._ld_hl(ARG)+b"\xDD\x21"+word(STATUS)+bytes((0x06,argc))+phase1._call(sy["sh_p625_wait"])+b"\xD2"+word(FAIL_PC))
            code+=bytes((0xFE,sy["E_INVAL"]&255))+phase1._jp_nz(FAIL_PC)+expect(gy["p625_calls"],0)+expect(STATUS,0xA5)+phase1._jp(PASS_PC)
            run_sna(root,bytes(code),patch=patch(mod,gate,arg))

        assertions += [
          {"name":"fuse-wait-all-drains-exact-job-launch-set","passed":True},
          {"name":"fuse-wait-specific-adopted-child-status","passed":True},
          {"name":"fuse-nonchild-failure-preserves-job-table","passed":True},
          {"name":"fuse-invalid-arity-and-decimal-before-wait","passed":True},
        ]
    hashes={
      "v1/src/shell/sh.asm":sha256_file(sp),
      "v1/tools-host/test-driver/phase6_wait.py":sha256_file(root/"v1/tools-host/test-driver/phase6_wait.py"),
      "v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
      "v1/dist/certification/P6.24.build.json":sha256_file(root/"v1/dist/certification/P6.24.build.json"),
      "v1/dist/certification/P6.24.test.json":sha256_file(root/"v1/dist/certification/P6.24.test.json"),
      "v1/dist/media/P6.24/manifest.json":sha256_file(root/"v1/dist/media/P6.24/manifest.json")}
    return [sr,gr],hashes,assertions
