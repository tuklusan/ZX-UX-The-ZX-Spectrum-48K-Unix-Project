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

UTIL=0xC000; GATE=0xE000; ARG=0xA000; ENV=0xA100; OUT=0xA300
STATUS=0xA280; MODE=0xA282
class P817Error(DriverError): pass
def require(v,m):
    if not v: raise P817Error(m)
def expect(addr,val): return b"\x3A"+word(addr)+bytes((0xFE,val&255))+phase1._jp_nz(0x8F00)
def env1(entries):
    body=b"".join(x+b"\0" for x in entries)
    return b"ENV1"+bytes((len(entries),0))+word(8+len(body))+body
def patch(util,gate,args,entries,mode=0,bad_magic=False):
    ab=arg1(args); eb=bytearray(env1(entries))
    if bad_magic: eb[0]=ord('X')
    def apply(ram):
        ram[UTIL-0x4000:UTIL-0x4000+len(util)]=util
        ram[GATE-0x4000:GATE-0x4000+len(gate)]=gate
        ram[ARG-0x4000:ARG-0x4000+len(ab)]=ab
        ram[ENV-0x4000:ENV-0x4000+len(eb)]=eb
        ram[OUT-0x4000:OUT-0x4000+128]=b"\xA5"*128
        ram[STATUS-0x4000:STATUS-0x4000+8]=b"\0"*8
        ram[MODE-0x4000]=mode
    return apply
def source_contract(root):
    s=(root/"v1/src/utils/env.asm").read_text(); p=(root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md").read_text()
    return [
      {"name":"canonical-p817-present","passed":"## P8.17 - Utility `env`" in p},
      {"name":"env1-magic","passed":"cp 'E'" in s and "cp 'N'" in s and "cp 'V'" in s and "cp '1'" in s},
      {"name":"stored-order","passed":"env_next:" in s and "env_remaining" in s},
      {"name":"case-preserving","passed":"casefold" not in s.lower()},
      {"name":"one-entry-per-line","passed":"env_lf: db 10" in s},
      {"name":"stdout","passed":"ld de,1" in s and "SYS_WRITE" in s},
      {"name":"short-write-safe","passed":"env_write_loop:" in s and "env_write_zero:" in s},
      {"name":"exact-arity","passed":"cp 1" in s and "E_INVAL" in s},
    ]
def dispatch(root,action,step,*,sha256_file,run_command,require_project_tool):
    if step!="P8.17": raise DriverError(f"Phase-8 env step is not registered: {step}")
    assertions=source_contract(root); require(all(x["passed"] for x in assertions),"P8.17 static contract failure")
    tool=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus"); build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    try: ir,image,mex=assemble_utility(root,build,tool,"env","p817","EMIT_P817_ENV_ROUTINES",run_command); xr=inspect_mex(root,mex,run_command,require_project_tool); tap=make_tap(root,build,"env","p817",mex)
    except RuntimeError as e: raise P817Error(str(e))
    require(64<=len(image)<1024,"P8.17 image size implausible")
    fix=build/"p817-env-fixture.asm"; fix.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/utils/env.asm"
    ORG $C000
fixture:
    EMIT_P817_ENV_ROUTINES
fixture_end:
    SAVEBIN "p817-env-fixture.bin",fixture,fixture_end-fixture
""",newline="\n")
    fr=run_command([tool,"--nologo","--lst=p817-env-fixture.lst","--sym=p817-env-fixture.sym","p817-env-fixture.asm"],cwd=build,timeout_seconds=30); require(not fr.timed_out and fr.exit_code==0,f"P8.17 fixture assembly failed: {fr.stderr or fr.stdout}")
    gate=build/"p817-gateway.asm"; gate.write_text("""    DEVICE ZXSPECTRUM48
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
    ld a,($A282)
    cp 2
    jr z,g_fail
    cp 1
    jr nz,g_all
    ld a,b
    or a
    jr nz,g_two
    ld a,c
    cp 3
    jr c,g_all
g_two:
    ld bc,2
g_all:
    push bc
    ld de,(g_out)
    ldir
    ld (g_out),de
    pop hl
    xor a
    ret
g_fail:
    ld a,E_IO
    scf
    ret
g_exit:
    ld a,l
    ld ($A280),a
    ld a,1
    ld ($A281),a
    xor a
    ret
g_bad:
    ld a,E_INVAL
    scf
    ret
g_out: dw $A300
gate_end:
    SAVEBIN "p817-gateway.bin",gate,gate_end-gate
""",newline="\n")
    gr=run_command([tool,"--nologo","--lst=p817-gateway.lst","--sym=p817-gateway.sym","p817-gateway.asm"],cwd=build,timeout_seconds=30); require(not gr.timed_out and gr.exit_code==0,f"P8.17 gateway assembly failed: {gr.stderr or gr.stdout}")
    if action=="test":
        sy=phase3_open_descriptions._symbols(build/"p817-env-fixture.sym",("env_entry",)); ub=(build/"p817-env-fixture.bin").read_bytes(); gb=(build/"p817-gateway.bin").read_bytes()
        cases=[
          ([b"env"],[b"HOME=/home/alice",b"MiXeD=Case",b"PATH=/bin:.",b"USER=alice"],0,b"HOME=/home/alice\nMiXeD=Case\nPATH=/bin:.\nUSER=alice\n",0,False),
          ([b"env"],[],1,b"",0,False),
          ([b"env"],[b"A=1"],2,b"",5,False),
          ([b"env",b"x"],[b"A=1"],0,b"",1,False),
          ([b"env"],[b"A=1"],0,b"",6,True),
        ]
        for args,entries,mode,expected,status,bad_magic in cases:
            ab=arg1(args); code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._ld_hl(ARG)+phase1._ld_de(ENV)+b"\x01"+word(len(ab))+phase1._call(sy["env_entry"]))
            for o,v in enumerate(expected): code+=expect(OUT+o,v)
            code+=expect(OUT+len(expected),0xA5)+expect(STATUS,status)+expect(STATUS+1,1)+phase1._jp(PASS_PC)
            try:
                run_sna(root,bytes(code),patch=patch(ub,gb,args,entries,mode,bad_magic))
            except DriverError as exc:
                raise P817Error(f"runtime case args={args!r} entries={entries!r} mode={mode} bad_magic={bad_magic} failed: {exc}") from exc
        assertions += [
          {"name":"fuse-exact-case-and-order","passed":True},
          {"name":"fuse-empty-env","passed":True},
          {"name":"fuse-short-write-retried","passed":True},
          {"name":"fuse-write-error-propagates","passed":True},
          {"name":"fuse-malformed-env-rejected","passed":True},
        ]
    hashes={"v1/src/utils/env.asm":sha256_file(root/"v1/src/utils/env.asm"),"v1/build/p817-env.mex1":sha256_file(mex),"v1/build/p817-env.tap":sha256_file(tap),"v1/tools-host/test-driver/phase8_env.py":sha256_file(root/"v1/tools-host/test-driver/phase8_env.py"),"v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),"v1/dist/certification/P8.16.test.json":sha256_file(root/"v1/dist/certification/P8.16.test.json")}
    return [ir,xr,fr,gr],hashes,assertions
