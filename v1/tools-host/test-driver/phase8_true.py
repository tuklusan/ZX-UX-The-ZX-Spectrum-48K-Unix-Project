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
class P813Error(DriverError): pass
def require(v,m):
    if not v: raise P813Error(m)
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
    s=(root/"v1/src/utils/true.asm").read_text()
    p=(root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md").read_text()
    return [
      {"name":"canonical-p813-present","passed":"## P8.13 - Utility `true`" in p},
      {"name":"status-zero","passed":"ld l,0" in s and "SYS_EXIT" in s},
      {"name":"no-output","passed":"SYS_WRITE" not in s},
      {"name":"no-input-io","passed":"SYS_READ" not in s and "SYS_OPEN" not in s},
    ]
def dispatch(root,action,step,*,sha256_file,run_command,require_project_tool):
    if step!="P8.13": raise DriverError(f"Phase-8 true step is not registered: {step}")
    assertions=source_contract(root); require(all(x["passed"] for x in assertions),"P8.13 static contract failure")
    tool=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus"); build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    try: ir,image,mex=assemble_utility(root,build,tool,"true","p813","EMIT_P813_TRUE_ROUTINES",run_command); xr=inspect_mex(root,mex,run_command,require_project_tool); tap=make_tap(root,build,"true","p813",mex)
    except RuntimeError as e: raise P813Error(str(e))
    require(4<=len(image)<128,"P8.13 image size implausible")
    fix=build/"p813-true-fixture.asm"; fix.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/utils/true.asm"
    ORG $C000
fixture:
    EMIT_P813_TRUE_ROUTINES
fixture_end:
    SAVEBIN "p813-true-fixture.bin",fixture,fixture_end-fixture
""",newline="\n")
    fr=run_command([tool,"--nologo","--lst=p813-true-fixture.lst","--sym=p813-true-fixture.sym","p813-true-fixture.asm"],cwd=build,timeout_seconds=30); require(not fr.timed_out and fr.exit_code==0,f"P8.13 fixture assembly failed: {fr.stderr or fr.stdout}")
    gate=build/"p813-gateway.asm"; gate.write_text("""    DEVICE ZXSPECTRUM48
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
    SAVEBIN "p813-gateway.bin",gate,gate_end-gate
""",newline="\n")
    gr=run_command([tool,"--nologo","--lst=p813-gateway.lst","--sym=p813-gateway.sym","p813-gateway.asm"],cwd=build,timeout_seconds=30); require(not gr.timed_out and gr.exit_code==0,f"P8.13 gateway assembly failed: {gr.stderr or gr.stdout}")
    if action=="test":
        sy=phase3_open_descriptions._symbols(build/"p813-true-fixture.sym",("true_entry",)); ub=(build/"p813-true-fixture.bin").read_bytes(); gb=(build/"p813-gateway.bin").read_bytes()
        for args in ([b"true"],[b"true",b"ignored"]):
            block=arg1(args); code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._ld_hl(ARG)+b"\x01"+word(len(block))+phase1._call(sy["true_entry"]))
            code+=expect(STATUS,0)+expect(STATUS+1,1)+expect(CALLS,0)+phase1._jp(PASS_PC)
            run_sna(root,bytes(code),patch=patch(ub,gb,args))
        assertions += [{"name":"fuse-status-zero","passed":True},{"name":"fuse-no-nonexit-syscalls","passed":True},{"name":"fuse-extra-args-do-not-change-status","passed":True}]
    hashes={"v1/src/utils/true.asm":sha256_file(root/"v1/src/utils/true.asm"),"v1/build/p813-true.mex1":sha256_file(mex),"v1/build/p813-true.tap":sha256_file(tap),"v1/tools-host/test-driver/phase8_true.py":sha256_file(root/"v1/tools-host/test-driver/phase8_true.py"),"v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),"v1/dist/certification/P8.12.test.json":sha256_file(root/"v1/dist/certification/P8.12.test.json")}
    return [ir,xr,fr,gr],hashes,assertions
