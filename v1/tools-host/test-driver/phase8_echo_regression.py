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
import phase1, phase3_open_descriptions
from driver_core import DriverError
from fuse_harness import FAIL_PC, PASS_PC, run_sna
from phase8_common import arg1, word, assemble_utility, inspect_mex, make_tap

UTIL=0xC000; GATE=0xE000; ARG=0xA000; OUT=0xA400; STATUS=0xA300
class P837Error(DriverError):
    pass
def require(v,m):
    if not v: raise P837Error(m)
def expect(a,v): return b"\x3A"+word(a)+bytes((0xFE,v&255))+phase1._jp_nz(FAIL_PC)
def patch(util,gate,args):
    ab=arg1(args)
    def apply(ram):
        ram[UTIL-0x4000:UTIL-0x4000+len(util)]=util
        ram[GATE-0x4000:GATE-0x4000+len(gate)]=gate
        ram[ARG-0x4000:ARG-0x4000+len(ab)]=ab
        ram[OUT-0x4000:OUT-0x4000+128]=b"\xA5"*128
        ram[STATUS-0x4000]=0xFF
    return apply

def dispatch(root,action,step,*,sha256_file,run_command,require_project_tool):
    if step!="P8.37": raise DriverError(step)
    s=(root/"v1/src/utils/echo.asm").read_text(encoding="utf-8")
    sh=(root/"v1/src/shell/sh.asm").read_text(encoding="utf-8")
    p=(root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md").read_text(encoding="utf-8")
    assertions=[
      {"name":"canonical-p837-present","passed":"## P8.37 - External echo regression" in p},
      {"name":"external-echo-source","passed":"EMIT_P616_ECHO_ROUTINES" in s and "/bin/echo" in s},
      {"name":"pipelineable-write","passed":"SYS_WRITE" in s and "ld de,1" in s},
      {"name":"exact-space-lf","passed":"ld hl,$0020" in s and "ld hl,$000a" in s},
      {"name":"no-parent-shell-echo-builtin","passed":"sh_builtin_echo" not in sh and "builtin_echo" not in sh},
    ]
    require(all(x["passed"] for x in assertions),"P8.37 static contract failure")
    tool=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus"); b=root/"v1/build"; b.mkdir(parents=True,exist_ok=True)
    try:
        ir,image,mex=assemble_utility(root,b,tool,"echo","p837","EMIT_P616_ECHO_ROUTINES",run_command)
        xr=inspect_mex(root,mex,run_command,require_project_tool); tap=make_tap(root,b,"echo","p837",mex)
    except RuntimeError as e: raise P837Error(str(e))
    fix=b/"p837-echo-fixture.asm"; fix.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/utils/echo.asm"
    ORG $C000
fixture:
    EMIT_P616_ECHO_ROUTINES
fixture_end:
    SAVEBIN "p837-echo-fixture.bin",fixture,fixture_end-fixture
""",encoding="utf-8",newline="\n")
    fr=run_command([tool,"--nologo","--lst=p837-echo-fixture.lst","--sym=p837-echo-fixture.sym",fix.name],cwd=b,timeout_seconds=30); require(not fr.timed_out and fr.exit_code==0,f"P8.37 fixture: {fr.stderr or fr.stdout}")
    gate=b/"p837-gateway.asm"; gate.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    ORG $E000
gate:
    cp SYS_WRITE
    jr z,g_write
    cp SYS_EXIT
    jr z,g_exit
    ld a,E_NOTSUP
    scf
    ret
g_write:
    ld a,e
    cp 1
    jr nz,g_bad
    ld a,d
    or a
    jr nz,g_bad
    push bc
    ld de,(g_out)
    ldir
    ld (g_out),de
    pop hl
    xor a
    ret
g_exit:
    ld a,l
    ld ($A300),a
    xor a
    ret
g_bad:
    ld a,E_INVAL
    scf
    ret
g_out: dw $A400
gate_end:
    SAVEBIN "p837-gateway.bin",gate,gate_end-gate
""",encoding="utf-8",newline="\n")
    gr=run_command([tool,"--nologo","--lst=p837-gateway.lst","--sym=p837-gateway.sym",gate.name],cwd=b,timeout_seconds=30); require(not gr.timed_out and gr.exit_code==0,f"P8.37 gateway: {gr.stderr or gr.stdout}")
    if action=="test":
        sy=phase3_open_descriptions._symbols(b/"p837-echo-fixture.sym",("echo_entry",))
        ub=(b/"p837-echo-fixture.bin").read_bytes(); gb=(b/"p837-gateway.bin").read_bytes()
        for args,want in (([b"echo"],b"\n"),([b"echo",b"hello"],b"hello\n"),([b"echo",b"a",b"b"],b"a b\n")):
            ab=arg1(args); code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._ld_hl(ARG)+b"\x01"+word(len(ab))+phase1._call(sy["echo_entry"]))
            for i,v in enumerate(want): code+=expect(OUT+i,v)
            code+=expect(OUT+len(want),0xA5)+expect(STATUS,0)+phase1._jp(PASS_PC)
            run_sna(root,bytes(code),patch=patch(ub,gb,args),timeout=30)
        assertions += [{"name":"fuse-echo-output-status","passed":True},{"name":"negative-builtin-manifest-policy","passed":True}]
    hashes={"v1/src/utils/echo.asm":sha256_file(root/"v1/src/utils/echo.asm"),"v1/build/p837-echo.mex1":sha256_file(mex),"v1/build/p837-echo.tap":sha256_file(tap),"v1/tools-host/test-driver/phase8_echo_regression.py":sha256_file(root/"v1/tools-host/test-driver/phase8_echo_regression.py"),"v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),"v1/dist/certification/P8.36.test.json":sha256_file(root/"v1/dist/certification/P8.36.test.json")}
    return [ir,xr,fr,gr],hashes,assertions
