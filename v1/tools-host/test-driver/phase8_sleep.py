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

UTIL=0xC000; GATE=0xE000; ARG=0xA000; STATUS=0xA100; CALLS=0xA102; TICKS=0xA110; MODE=0xA106
class P815Error(DriverError): pass
def require(v,m):
    if not v: raise P815Error(m)
def expect(addr,val): return b"\x3A"+word(addr)+bytes((0xFE,val&255))+phase1._jp_nz(0x8F00)
def patch(util,gate,args,mode=0):
    block=arg1(args)
    def apply(ram):
        ram[UTIL-0x4000:UTIL-0x4000+len(util)]=util
        ram[GATE-0x4000:GATE-0x4000+len(gate)]=gate
        ram[ARG-0x4000:ARG-0x4000+len(block)]=block
        ram[STATUS-0x4000:STATUS-0x4000+32]=b"\0"*32
        ram[MODE-0x4000]=mode
    return apply
def source_contract(root):
    s=(root/"v1/src/utils/sleep.asm").read_text()
    p=(root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md").read_text()
    return [
      {"name":"canonical-p815-present","passed":"## P8.15 - Utility `sleep`" in p},
      {"name":"exact-one-operand","passed":"cp 2" in s and "E_INVAL" in s},
      {"name":"decimal-only","passed":"cp '0'" in s and "cp '9'+1" in s},
      {"name":"range-65535","passed":"cp $19" in s and "cp $99" in s and "cp 6" in s},
      {"name":"fifty-hz-conversion","passed":"ld a,50" in s and "sleep_tick_loop:" in s},
      {"name":"sys-sleep-pointer","passed":"ld hl,sleep_ticks" in s and "SYS_SLEEP" in s},
      {"name":"error-propagation","passed":"jr c,sleep_error" in s},
    ]
def dispatch(root,action,step,*,sha256_file,run_command,require_project_tool):
    if step!="P8.15": raise DriverError(f"Phase-8 sleep step is not registered: {step}")
    assertions=source_contract(root); require(all(x["passed"] for x in assertions),"P8.15 static contract failure")
    tool=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus"); build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    try: ir,image,mex=assemble_utility(root,build,tool,"sleep","p815","EMIT_P815_SLEEP_ROUTINES",run_command); xr=inspect_mex(root,mex,run_command,require_project_tool); tap=make_tap(root,build,"sleep","p815",mex)
    except RuntimeError as e: raise P815Error(str(e))
    require(32<=len(image)<512,"P8.15 image size implausible")
    fix=build/"p815-sleep-fixture.asm"; fix.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/utils/sleep.asm"
    ORG $C000
fixture:
    EMIT_P815_SLEEP_ROUTINES
fixture_end:
    SAVEBIN "p815-sleep-fixture.bin",fixture,fixture_end-fixture
""",newline="\n")
    fr=run_command([tool,"--nologo","--lst=p815-sleep-fixture.lst","--sym=p815-sleep-fixture.sym","p815-sleep-fixture.asm"],cwd=build,timeout_seconds=30); require(not fr.timed_out and fr.exit_code==0,f"P8.15 fixture assembly failed: {fr.stderr or fr.stdout}")
    gate=build/"p815-gateway.asm"; gate.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    ORG $E000
gate:
    cp SYS_SLEEP
    jr z,g_sleep
    cp SYS_EXIT
    jr z,g_exit
    ld a,E_NOTSUP
    scf
    ret
g_sleep:
    ld a,($A102)
    inc a
    ld ($A102),a
    ld de,$A110
    ld bc,4
    ldir
    ld a,($A106)
    or a
    jr z,g_sleep_ok
    ld a,E_IO
    scf
    ret
g_sleep_ok:
    xor a
    ret
g_exit:
    ld a,l
    ld ($A100),a
    ld a,1
    ld ($A101),a
    xor a
    ret
gate_end:
    SAVEBIN "p815-gateway.bin",gate,gate_end-gate
""",newline="\n")
    gr=run_command([tool,"--nologo","--lst=p815-gateway.lst","--sym=p815-gateway.sym","p815-gateway.asm"],cwd=build,timeout_seconds=30); require(not gr.timed_out and gr.exit_code==0,f"P8.15 gateway assembly failed: {gr.stderr or gr.stdout}")
    if action=="test":
        sy=phase3_open_descriptions._symbols(build/"p815-sleep-fixture.sym",("sleep_entry",)); ub=(build/"p815-sleep-fixture.bin").read_bytes(); gb=(build/"p815-gateway.bin").read_bytes()
        cases=[
          ([b"sleep",b"0"],0,0,0,1),
          ([b"sleep",b"1"],0,50,0,1),
          ([b"sleep",b"65535"],0,65535*50,0,1),
          ([b"sleep",b"12"],1,12*50,5,1),
          ([b"sleep",b"-1"],0,0,1,0),
          ([b"sleep",b"65536"],0,0,1,0),
          ([b"sleep",b"1x"],0,0,1,0),
          ([b"sleep"],0,0,1,0),
          ([b"sleep",b"1",b"2"],0,0,1,0),
        ]
        for args,mode,ticks,status,calls in cases:
            block=arg1(args); code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._ld_hl(ARG)+b"\x01"+word(len(block))+phase1._call(sy["sleep_entry"]))
            code+=expect(STATUS,status)+expect(STATUS+1,1)+expect(CALLS,calls)
            if calls:
                for n in range(4): code+=expect(TICKS+n,(ticks>>(8*n))&255)
            code+=phase1._jp(PASS_PC)
            run_sna(root,bytes(code),patch=patch(ub,gb,args,mode))
        assertions += [
          {"name":"fuse-zero-one-max-seconds","passed":True},
          {"name":"fuse-sleep-error-propagates","passed":True},
          {"name":"fuse-negative-overflow-malformed-rejected","passed":True},
          {"name":"fuse-excess-arity-rejected-before-sleep","passed":True},
        ]
    hashes={"v1/src/utils/sleep.asm":sha256_file(root/"v1/src/utils/sleep.asm"),"v1/build/p815-sleep.mex1":sha256_file(mex),"v1/build/p815-sleep.tap":sha256_file(tap),"v1/tools-host/test-driver/phase8_sleep.py":sha256_file(root/"v1/tools-host/test-driver/phase8_sleep.py"),"v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),"v1/dist/certification/P8.14.test.json":sha256_file(root/"v1/dist/certification/P8.14.test.json")}
    return [ir,xr,fr,gr],hashes,assertions
