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
from fuse_harness import PASS_PC, run_sna
from phase8_common import arg1, word, assemble_utility, inspect_mex, make_tap

UTIL=0xC000; GATE=0xE000; ARG=0xA000; STATUS=0xA100; CALLS=0xA102
class P814Error(DriverError): pass
def require(v,m):
    if not v: raise P814Error(m)
def expect(addr,val): return b"\x3A"+word(addr)+bytes((0xFE,val&255))+phase1._jp_nz(0x8F00)
def patch(util,gate,args):
    block=arg1(args)
    def apply(ram):
        ram[UTIL-0x4000:UTIL-0x4000+len(util)]=util
        ram[GATE-0x4000:GATE-0x4000+len(gate)]=gate
        ram[ARG-0x4000:ARG-0x4000+len(block)]=block
        ram[STATUS-0x4000:STATUS-0x4000+8]=b"\0"*8
    return apply
def source_contract(root):
    s=(root/"v1/src/utils/false.asm").read_text()
    p=(root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md").read_text()
    return [
      {"name":"canonical-p814-present","passed":"## P8.14 - Utility `false`" in p},
      {"name":"status-one","passed":"ld l,1" in s and "SYS_EXIT" in s},
      {"name":"no-output","passed":"SYS_WRITE" not in s},
      {"name":"no-input-io","passed":"SYS_READ" not in s and "SYS_OPEN" not in s},
    ]
def dispatch(root,action,step,*,sha256_file,run_command,require_project_tool):
    if step!="P8.14": raise DriverError(f"Phase-8 false step is not registered: {step}")
    assertions=source_contract(root); require(all(x["passed"] for x in assertions),"P8.14 static contract failure")
    tool=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus"); build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    try: ir,image,mex=assemble_utility(root,build,tool,"false","p814","EMIT_P814_FALSE_ROUTINES",run_command); xr=inspect_mex(root,mex,run_command,require_project_tool); tap=make_tap(root,build,"false","p814",mex)
    except RuntimeError as e: raise P814Error(str(e))
    require(4<=len(image)<128,"P8.14 image size implausible")
    fix=build/"p814-false-fixture.asm"; fix.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/utils/false.asm"
    ORG $C000
fixture:
    EMIT_P814_FALSE_ROUTINES
fixture_end:
    SAVEBIN "p814-false-fixture.bin",fixture,fixture_end-fixture
""",newline="\n")
    fr=run_command([tool,"--nologo","--lst=p814-false-fixture.lst","--sym=p814-false-fixture.sym","p814-false-fixture.asm"],cwd=build,timeout_seconds=30); require(not fr.timed_out and fr.exit_code==0,f"P8.14 fixture assembly failed: {fr.stderr or fr.stdout}")
    gate=build/"p814-gateway.asm"; gate.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    ORG $E000
gate:
    cp SYS_EXIT
    jr z,g_exit
    ld a,($A102)
    inc a
    ld ($A102),a
    ld a,E_NOTSUP
    scf
    ret
g_exit:
    ld a,l
    ld ($A100),a
    ld a,1
    ld ($A101),a
    xor a
    ret
gate_end:
    SAVEBIN "p814-gateway.bin",gate,gate_end-gate
""",newline="\n")
    gr=run_command([tool,"--nologo","--lst=p814-gateway.lst","--sym=p814-gateway.sym","p814-gateway.asm"],cwd=build,timeout_seconds=30); require(not gr.timed_out and gr.exit_code==0,f"P8.14 gateway assembly failed: {gr.stderr or gr.stdout}")
    if action=="test":
        sy=phase3_open_descriptions._symbols(build/"p814-false-fixture.sym",("false_entry",)); ub=(build/"p814-false-fixture.bin").read_bytes(); gb=(build/"p814-gateway.bin").read_bytes()
        for args in ([b"false"],[b"false",b"ignored"]):
            block=arg1(args); code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._ld_hl(ARG)+b"\x01"+word(len(block))+phase1._call(sy["false_entry"]))
            code+=expect(STATUS,1)+expect(STATUS+1,1)+expect(CALLS,0)+phase1._jp(PASS_PC)
            run_sna(root,bytes(code),patch=patch(ub,gb,args))
        assertions += [{"name":"fuse-status-one","passed":True},{"name":"fuse-no-nonexit-syscalls","passed":True},{"name":"fuse-extra-args-do-not-change-status","passed":True}]
    hashes={"v1/src/utils/false.asm":sha256_file(root/"v1/src/utils/false.asm"),"v1/build/p814-false.mex1":sha256_file(mex),"v1/build/p814-false.tap":sha256_file(tap),"v1/tools-host/test-driver/phase8_false.py":sha256_file(root/"v1/tools-host/test-driver/phase8_false.py"),"v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),"v1/dist/certification/P8.13.test.json":sha256_file(root/"v1/dist/certification/P8.13.test.json")}
    return [ir,xr,fr,gr],hashes,assertions
