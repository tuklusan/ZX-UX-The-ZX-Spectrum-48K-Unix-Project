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

UTIL=0xC000; GATE=0xE000; ARG=0xA000; STATUS=0xA140; CALLS=0xA142
class P807Error(DriverError): pass
def require(v,m):
    if not v: raise P807Error(m)
def expect(addr,val): return b"\x3A"+word(addr)+bytes((0xFE,val&255))+phase1._jp_nz(0x8F00)
def patch(util,gate,args,mode):
    block=arg1(args)
    def apply(ram):
        ram[UTIL-0x4000:UTIL-0x4000+len(util)]=util; ram[GATE-0x4000:GATE-0x4000+len(gate)]=gate
        ram[ARG-0x4000:ARG-0x4000+len(block)]=block; ram[STATUS-0x4000:STATUS-0x4000+8]=b"\0"*8; ram[0xA141-0x4000]=mode
    return apply
def source_contract(root):
    s=(root/"v1/src/utils/unpack.asm").read_text(); p=(root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md").read_text()
    return [
      {"name":"canonical-p807-present","passed":"## P8.07 - Utility `unpack`" in p},
      {"name":"sys-unpack","passed":"SYS_UNPACK" in s},
      {"name":"exact-one-operand","passed":"cp 2" in s and "E_INVAL" in s},
      {"name":"error-propagation","passed":"jr c,unpack_error" in s or "jp c,unpack_error" in s},
      {"name":"no-metadata-rewrite","passed":"SYS_RENAME" not in s and "SYS_REMOVE" not in s},
      {"name":"no-case-folding","passed":"casefold" not in s.lower()},
    ]
def dispatch(root,action,step,*,sha256_file,run_command,require_project_tool):
    if step!="P8.07": raise DriverError(f"Phase-8 unpack step is not registered: {step}")
    assertions=source_contract(root); require(all(x["passed"] for x in assertions),"P8.07 static contract failure")
    tool=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus"); build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    try: ir,image,mex=assemble_utility(root,build,tool,"unpack","p807","EMIT_P807_UNPACK_ROUTINES",run_command); xr=inspect_mex(root,mex,run_command,require_project_tool); tap=make_tap(root,build,"unpack","p807",mex)
    except RuntimeError as e: raise P807Error(str(e))
    require(16<=len(image)<512,"P8.07 image size implausible")
    fix=build/"p807-unpack-fixture.asm"; fix.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/utils/unpack.asm"
    ORG $C000
fixture:
    EMIT_P807_UNPACK_ROUTINES
fixture_end:
    SAVEBIN "p807-unpack-fixture.bin",fixture,fixture_end-fixture
""",newline="\n")
    fr=run_command([tool,"--nologo","--lst=p807-unpack-fixture.lst","--sym=p807-unpack-fixture.sym","p807-unpack-fixture.asm"],cwd=build,timeout_seconds=30); require(not fr.timed_out and fr.exit_code==0,f"P8.07 fixture assembly failed: {fr.stderr or fr.stdout}")
    gate=build/"p807-gateway.asm"; gate.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    ORG $E000
gate:
    cp SYS_UNPACK
    jr z,g_unpack
    cp SYS_EXIT
    jr z,g_exit
    ld a,E_NOTSUP
    scf
    ret
g_unpack:
    ld a,($A142)
    inc a
    ld ($A142),a
    ld a,($A141)
    or a
    jr nz,g_fail
    ld hl,123
    xor a
    ret
g_fail:
    scf
    ret
g_exit:
    ld a,l
    ld ($A140),a
    ld a,1
    ld ($A143),a
    xor a
    ret
gate_end:
    SAVEBIN "p807-gateway.bin",gate,gate_end-gate
""",newline="\n")
    gr=run_command([tool,"--nologo","--lst=p807-gateway.lst","--sym=p807-gateway.sym","p807-gateway.asm"],cwd=build,timeout_seconds=30); require(not gr.timed_out and gr.exit_code==0,f"P8.07 gateway assembly failed: {gr.stderr or gr.stdout}")
    if action=="test":
        sy=phase3_open_descriptions._symbols(build/"p807-unpack-fixture.sym",("unpack_entry",)); ub=(build/"p807-unpack-fixture.bin").read_bytes(); gb=(build/"p807-gateway.bin").read_bytes()
        for args,mode,status,calls in [([b"unpack",b"MiXeD"],0,0,1),([b"unpack",b"busy"],4,4,1),([b"unpack"],0,1,0)]:
            block=arg1(args); code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._ld_hl(ARG)+b"\x01"+word(len(block))+phase1._call(sy["unpack_entry"]))
            code+=expect(STATUS,status)+expect(CALLS,calls)+expect(STATUS+3,1)+phase1._jp(PASS_PC); run_sna(root,bytes(code),patch=patch(ub,gb,args,mode))
        assertions += [{"name":"fuse-unpack-success","passed":True},{"name":"fuse-allocation-busy-error","passed":True},{"name":"fuse-invalid-arity-no-unpack","passed":True}]
    hashes={"v1/src/utils/unpack.asm":sha256_file(root/"v1/src/utils/unpack.asm"),"v1/build/p807-unpack.mex1":sha256_file(mex),"v1/build/p807-unpack.tap":sha256_file(tap),"v1/tools-host/test-driver/phase8_unpack.py":sha256_file(root/"v1/tools-host/test-driver/phase8_unpack.py"),"v1/tools-host/test-driver/phase8_common.py":sha256_file(root/"v1/tools-host/test-driver/phase8_common.py"),"v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),"v1/dist/certification/P8.06.test.json":sha256_file(root/"v1/dist/certification/P8.06.test.json")}
    return [ir,xr,fr,gr],hashes,assertions
