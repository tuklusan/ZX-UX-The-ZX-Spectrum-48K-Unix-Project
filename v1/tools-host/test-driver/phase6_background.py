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
BASE=0xC000; GATE=0xE000; REQ=0xA000; STATUS=0xA100; LOG=0xA200
class E(DriverError): pass
def req(v,m):
    if not v: raise E(m)
def word(v): return bytes((v&255,(v>>8)&255))
def expect(a,v): return b"\x3A"+word(a)+bytes((0xFE,v&255))+phase1._jp_nz(FAIL_PC)
def patch(shell,gate,fail=False):
    def p(ram):
        ram[BASE-0x4000:BASE-0x4000+len(shell)]=shell
        ram[GATE-0x4000:GATE-0x4000+len(gate)]=gate
        ram[REQ-0x4000:REQ-0x4000+32]=b"\0"*32
        ram[STATUS-0x4000]=0xA5
        ram[LOG-0x4000:LOG-0x4000+8]=b"\0"*8
        ram[(GATE+0x70)-0x4000]=1 if fail else 0
    return p
def dispatch(root:Path,action:str,step:str,*,sha256_file,run_command,require_project_tool):
    if step!="P6.23": raise DriverError(f"Phase-6 background step is not registered: {step}")
    sp=root/"v1/src/shell/sh.asm"; text=sp.read_text(); macro=text.split("MACRO EMIT_P623_BACKGROUND_ROUTINES",1)[1].split("ENDM",1)[0]
    assertions=[
      {"name":"default-stdin-dev-null","passed":"p623_dev_null: db '/dev/null',0" in macro and "O_READ" in macro},
      {"name":"no-tty-owner-change","passed":"SYS_IOCTL" not in macro and "P622_SET_OWNER" not in macro},
      {"name":"successful-launch-status-zero","passed":"ld (ix+0),a" in macro and "p623_job_pid" in macro},
      {"name":"failure-status-actual-no-phantom","passed":"p623_error" in macro and macro.index("p623_job_pid")>macro.index("SYS_SPAWN")},
    ]; req(all(x["passed"] for x in assertions),"P6.23 static contract failure")
    asm=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus"); build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    sf=build/"p623-fixture.asm"; sf.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/shell/sh.asm"
    ORG $C000
p623_start:
    EMIT_P623_BACKGROUND_ROUTINES
p623_end:
    SAVEBIN "p623-fixture.bin",p623_start,p623_end-p623_start
""",encoding="utf-8",newline="\n")
    sr=run_command([asm,"--nologo","--lst=p623-fixture.lst","--sym=p623-fixture.sym","p623-fixture.asm"],cwd=build,timeout_seconds=30)
    req(not sr.timed_out and sr.exit_code==0,f"P6.23 fixture failed: {sr.stderr or sr.stdout}")
    gf=build/"p623-gate.asm"; gf.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    ORG $E000
p623_gate:
    cp SYS_OPEN
    jr z,p623_open
    cp SYS_SPAWN
    jr z,p623_spawn
    cp SYS_CLOSE
    jr z,p623_close
    ld a,E_NOTSUP
    scf
    ret
p623_open:
    ld a,1
    ld ($A200),a
    ld hl,5
    xor a
    ret
p623_spawn:
    ld a,2
    ld ($A201),a
    ld a,($E070)
    or a
    jr z,p623_spawn_ok
    ld a,E_AGAIN
    scf
    ret
p623_spawn_ok:
    ld hl,3
    xor a
    ret
p623_close:
    ld a,3
    ld ($A202),a
    xor a
    ret
    ORG $E070
p623_fail: db 0
p623_gate_end:
    SAVEBIN "p623-gate.bin",p623_gate,p623_gate_end-p623_gate
""",encoding="utf-8",newline="\n")
    gr=run_command([asm,"--nologo","--lst=p623-gate.lst","--sym=p623-gate.sym","p623-gate.asm"],cwd=build,timeout_seconds=30)
    req(not gr.timed_out and gr.exit_code==0,f"P6.23 gate failed: {gr.stderr or gr.stdout}")
    if action=="test":
        sy=phase3_open_descriptions._symbols(build/"p623-fixture.sym",("sh_p623_launch_background","p623_job_pid","E_AGAIN"))
        shell=(build/"p623-fixture.bin").read_bytes(); gate=(build/"p623-gate.bin").read_bytes()
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._ld_hl(REQ)+phase1._ld_de(REQ)+b"\x06\x00"+b"\xDD\x21"+word(STATUS))
        code+=phase1._call(sy["sh_p623_launch_background"])+phase1._jp_c(FAIL_PC)+expect(REQ,5)+expect(STATUS,0)+expect(sy["p623_job_pid"],3)+expect(LOG,1)+expect(LOG+1,2)+expect(LOG+2,3)+phase1._jp(PASS_PC)
        run_sna(root,bytes(code),patch=patch(shell,gate))
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._ld_hl(REQ)+phase1._ld_de(REQ)+b"\x06\x00"+b"\xDD\x21"+word(STATUS))
        code+=phase1._call(sy["sh_p623_launch_background"])+b"\xD2"+word(FAIL_PC)+bytes((0xFE,sy["E_AGAIN"]&255))+phase1._jp_nz(FAIL_PC)+expect(STATUS,sy["E_AGAIN"])+expect(sy["p623_job_pid"],0)+phase1._jp(PASS_PC)
        run_sna(root,bytes(code),patch=patch(shell,gate,True))
        assertions += [{"name":"fuse-background-null-stdin-and-prompt-status","passed":True},{"name":"fuse-launch-failure-no-phantom-job","passed":True}]
    hashes={"v1/src/shell/sh.asm":sha256_file(sp),"v1/tools-host/test-driver/phase6_background.py":sha256_file(root/"v1/tools-host/test-driver/phase6_background.py"),"v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),"v1/dist/certification/P6.22.build.json":sha256_file(root/"v1/dist/certification/P6.22.build.json"),"v1/dist/certification/P6.22.test.json":sha256_file(root/"v1/dist/certification/P6.22.test.json"),"v1/dist/media/P6.22/manifest.json":sha256_file(root/"v1/dist/media/P6.22/manifest.json")}
    return [sr,gr],hashes,assertions
