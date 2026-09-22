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

UTIL=0xC000; GATE=0xE000; ARG=0xA000; ENV=0xA100; OUT=0xA400; STATUS=0xA300
class P830Error(DriverError):
    pass
def require(v,m):
    if not v: raise P830Error(m)
def expect(a,v): return b"\x3A"+word(a)+bytes((0xFE,v&255))+phase1._jp_nz(FAIL_PC)
def env1(entries):
    body=b"".join(x+b"\0" for x in entries)
    return b"ENV1"+bytes((len(entries),0))+word(8+len(body))+body
def patch(util,gate,args,entries,bad=False):
    ab=arg1(args); eb=bytearray(env1(entries))
    if bad: eb[0]=ord("X")
    def apply(ram):
        ram[UTIL-0x4000:UTIL-0x4000+len(util)]=util
        ram[GATE-0x4000:GATE-0x4000+len(gate)]=gate
        ram[ARG-0x4000:ARG-0x4000+len(ab)]=ab
        ram[ENV-0x4000:ENV-0x4000+len(eb)]=eb
        ram[OUT-0x4000:OUT-0x4000+64]=b"\xA5"*64
        ram[STATUS-0x4000]=0xFF
    return apply

def dispatch(root,action,step,*,sha256_file,run_command,require_project_tool):
    if step!="P8.30": raise DriverError(step)
    s=(root/"v1/src/utils/whoami.asm").read_text(encoding="utf-8")
    p=(root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md").read_text(encoding="utf-8")
    assertions=[
      {"name":"canonical-p830-present","passed":"## P8.30 - Utility `whoami`" in p},
      {"name":"mutable-env-user","passed":"whoami_user_key" in s and "'U','S','E','R','='" in s},
      {"name":"env1-validated","passed":"cp 'E'" in s and "cp 'N'" in s and "cp 'V'" in s and "cp '1'" in s},
      {"name":"no-fixed-user","passed":"db 'r','o','o','t'" not in s.lower()},
      {"name":"short-write-safe","passed":"whoami_write_loop:" in s and "whoami_io:" in s},
      {"name":"case-sensitive","passed":"casefold" not in s.lower()},
    ]
    require(all(x["passed"] for x in assertions),"P8.30 static contract failure")
    tool=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus"); b=root/"v1/build"; b.mkdir(parents=True,exist_ok=True)
    try:
        ir,image,mex=assemble_utility(root,b,tool,"whoami","p830","EMIT_P830_WHOAMI_ROUTINES",run_command)
        xr=inspect_mex(root,mex,run_command,require_project_tool); tap=make_tap(root,b,"whoami","p830",mex)
    except RuntimeError as e: raise P830Error(str(e))
    fix=b/"p830-whoami-fixture.asm"; fix.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/utils/whoami.asm"
    ORG $C000
fixture:
    EMIT_P830_WHOAMI_ROUTINES
fixture_end:
    SAVEBIN "p830-whoami-fixture.bin",fixture,fixture_end-fixture
""",encoding="utf-8",newline="\n")
    fr=run_command([tool,"--nologo","--lst=p830-whoami-fixture.lst","--sym=p830-whoami-fixture.sym",fix.name],cwd=b,timeout_seconds=30); require(not fr.timed_out and fr.exit_code==0,f"P8.30 fixture: {fr.stderr or fr.stdout}")
    gate=b/"p830-gateway.asm"; gate.write_text("""    DEVICE ZXSPECTRUM48
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
    SAVEBIN "p830-gateway.bin",gate,gate_end-gate
""",encoding="utf-8",newline="\n")
    gr=run_command([tool,"--nologo","--lst=p830-gateway.lst","--sym=p830-gateway.sym",gate.name],cwd=b,timeout_seconds=30); require(not gr.timed_out and gr.exit_code==0,f"P8.30 gateway: {gr.stderr or gr.stdout}")
    if action=="test":
        sy=phase3_open_descriptions._symbols(b/"p830-whoami-fixture.sym",("whoami_entry","E_INVAL","E_FORMAT","E_NOENT"))
        ub=(b/"p830-whoami-fixture.bin").read_bytes(); gb=(b/"p830-gateway.bin").read_bytes()
        cases=[([b"whoami"],[b"HOME=/home/ada",b"USER=ada",b"PATH=/bin:."],b"ada\n",0,False),([b"whoami"],[b"USER=bob"],b"bob\n",0,False),([b"whoami"],[b"HOME=/home/x"],b"",sy["E_NOENT"]&255,False),([b"whoami"],[b"USER=x"],b"",sy["E_FORMAT"]&255,True)]
        for args,entries,want,status,bad in cases:
            ab=arg1(args); code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._ld_hl(ARG)+b"\x01"+word(len(ab))+b"\x11"+word(ENV)+phase1._call(sy["whoami_entry"]))
            for i,v in enumerate(want): code+=expect(OUT+i,v)
            code+=expect(OUT+len(want),0xA5)+expect(STATUS,status)+phase1._jp(PASS_PC)
            run_sna(root,bytes(code),patch=patch(ub,gb,args,entries,bad),timeout=30)
        args=[b"whoami",b"x"]; ab=arg1(args); code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._ld_hl(ARG)+b"\x01"+word(len(ab))+b"\x11"+word(ENV)+phase1._call(sy["whoami_entry"])+expect(STATUS,sy["E_INVAL"]&255)+phase1._jp(PASS_PC)); run_sna(root,bytes(code),patch=patch(ub,gb,args,[b"USER=x"]),timeout=30)
        assertions += [{"name":"fuse-mutable-user","passed":True},{"name":"fuse-missing-user","passed":True},{"name":"fuse-bad-env1","passed":True},{"name":"fuse-arity","passed":True}]
    hashes={"v1/src/utils/whoami.asm":sha256_file(root/"v1/src/utils/whoami.asm"),"v1/build/p830-whoami.mex1":sha256_file(mex),"v1/build/p830-whoami.tap":sha256_file(tap),"v1/tools-host/test-driver/phase8_whoami.py":sha256_file(root/"v1/tools-host/test-driver/phase8_whoami.py"),"v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),"v1/dist/certification/P8.29.test.json":sha256_file(root/"v1/dist/certification/P8.29.test.json")}
    return [ir,xr,fr,gr],hashes,assertions
