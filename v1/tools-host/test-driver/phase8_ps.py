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
from phase8_common import word

BASE=0xC000; GATE=0xE000; OUT=0xA300; MODE=0xA2F0
class P819Error(DriverError): pass
def require(v,m):
    if not v: raise P819Error(m)
def expect(addr,val): return b"\x3A"+word(addr)+bytes((0xFE,val&255))+phase1._jp_nz(FAIL_PC)
def patch(module,gate,mode=0):
    def apply(ram):
        ram[BASE-0x4000:BASE-0x4000+len(module)]=module
        ram[GATE-0x4000:GATE-0x4000+len(gate)]=gate
        ram[OUT-0x4000:OUT-0x4000+256]=b"\xA5"*256
        ram[MODE-0x4000]=mode
    return apply
def dispatch(root,action,step,*,sha256_file,run_command,require_project_tool):
    if step!="P8.19": raise DriverError(f"Phase-8 ps step is not registered: {step}")
    sp=root/"v1/src/shell/sh.asm"; s=sp.read_text(); p=(root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md").read_text()
    assertions=[
      {"name":"canonical-p819-present","passed":"## P8.19 - Built-in `ps` Phase-8 regression" in p},
      {"name":"ps-remains-p613-builtin","passed":"db 2,'p','s',P613_BUILTIN_PS" in s},
      {"name":"no-external-ps-module","passed":not (root/"v1/src/utils/ps.asm").exists()},
      {"name":"proc-info-source","passed":"MACRO EMIT_P819_PS_ROUTINES" in s and "SYS_PROC_INFO" in s.split("MACRO EMIT_P819_PS_ROUTINES",1)[1]},
      {"name":"pid-state-memory-name","passed":all(x in s.split("MACRO EMIT_P819_PS_ROUTINES",1)[1] for x in ("p819_info+2","p819_info+14","p819_info+4"))},
      {"name":"stdout-short-write-safe","passed":"sh_p819_write_loop:" in s and "sh_p819_write_zero:" in s},
      {"name":"single-foreground-only","passed":"sh_p819_notsup:" in s},
    ]
    require(all(x["passed"] for x in assertions),"P8.19 static contract failure")
    tool=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus"); build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    fixture=build/"p819-ps-fixture.asm"; fixture.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/shell/sh.asm"
    ORG $C000
fixture:
    EMIT_P613_BUILTIN_ROUTINES
    EMIT_P819_PS_ROUTINES
fixture_end:
    SAVEBIN "p819-ps-fixture.bin",fixture,fixture_end-fixture
""",newline="\n")
    fr=run_command([tool,"--nologo","--lst=p819-ps-fixture.lst","--sym=p819-ps-fixture.sym","p819-ps-fixture.asm"],cwd=build,timeout_seconds=30); require(not fr.timed_out and fr.exit_code==0,f"P8.19 fixture assembly failed: {fr.stderr or fr.stdout}")
    image=(build/"p819-ps-fixture.bin").read_bytes(); require(128<=len(image)<4096,"P8.19 image size implausible")
    gate=build/"p819-gateway.asm"; gate.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    ORG $E000
gate:
    cp SYS_PROC_INFO
    jp z,g_proc
    cp SYS_WRITE
    jp z,g_write
    ld a,E_NOTSUP
    scf
    ret
g_proc:
    ld a,(hl)
    ld ($A2F1),a
    inc hl
    inc hl
    ld e,(hl)
    inc hl
    ld d,(hl)
    ex de,hl
    ld a,($A2F0)
    cp 2
    jr nz,g_proc_cases
    ld a,($A2F1)
    cp 1
    jr nz,g_proc_cases
    ld a,E_IO
    scf
    ret
g_proc_cases:
    ld a,($A2F1)
    or a
    jr z,g_p0
    cp 1
    jr z,g_p1
    cp 3
    jr z,g_p3
    ld a,E_NOENT
    scf
    ret
g_p0:
    ld a,0
    ld (hl),a
    inc hl
    ld (hl),$ff
    inc hl
    ld (hl),1
    inc hl
    xor a
    ld (hl),a
    inc hl
    ld de,n_idle
    ld bc,10
    ldir
    ld (hl),100
    inc hl
    xor a
    ld (hl),a
    xor a
    ret
g_p1:
    ld a,1
    ld (hl),a
    inc hl
    ld (hl),0
    inc hl
    ld (hl),2
    inc hl
    xor a
    ld (hl),a
    inc hl
    ld de,n_sh
    ld bc,10
    ldir
    ld (hl),0
    inc hl
    ld (hl),2
    xor a
    ret
g_p3:
    ld a,3
    ld (hl),a
    inc hl
    ld (hl),1
    inc hl
    ld (hl),3
    inc hl
    xor a
    ld (hl),a
    inc hl
    ld de,n_full
    ld bc,10
    ldir
    xor a
    ld (hl),a
    inc hl
    ld (hl),4
    xor a
    ret
g_write:
    ld a,e
    cp 1
    jr nz,g_bad
    ld a,d
    or a
    jr nz,g_bad
    ld a,($A2F0)
    cp 1
    jr nz,g_write_all
    ld a,b
    or a
    jr nz,g_two
    ld a,c
    cp 3
    jr c,g_write_all
g_two:
    ld bc,2
g_write_all:
    push bc
    ld de,(g_out)
    ldir
    ld (g_out),de
    pop hl
    xor a
    ret
g_bad:
    ld a,E_INVAL
    scf
    ret
n_idle: db 'i','d','l','e',0,0,0,0,0,0
n_sh: db 's','h',0,0,0,0,0,0,0,0
n_full: db 'a','b','c','d','e','f','g','h','i','j'
g_out: dw $A300
gate_end:
    SAVEBIN "p819-gateway.bin",gate,gate_end-gate
""",newline="\n")
    gr=run_command([tool,"--nologo","--lst=p819-gateway.lst","--sym=p819-gateway.sym","p819-gateway.asm"],cwd=build,timeout_seconds=30); require(not gr.timed_out and gr.exit_code==0,f"P8.19 gateway assembly failed: {gr.stderr or gr.stdout}")
    mp=build/"p819-ps.mex1"; from phase8_common import mex1; mp.write_bytes(mex1(image))
    from phase8_common import make_tap, inspect_mex
    try: xr=inspect_mex(root,mp,run_command,require_project_tool); tap=make_tap(root,build,"ps-builtin","p819",mp)
    except RuntimeError as e: raise P819Error(str(e))
    if action=="test":
        sy=phase3_open_descriptions._symbols(build/"p819-ps-fixture.sym",("sh_p819_ps_builtin","sh_p613_lookup_builtin","E_INVAL","E_NOTSUP","E_NOENT"))
        gb=(build/"p819-gateway.bin").read_bytes()
        expected=b"0 READY 100 idle\n1 RUNNING 512 sh\n3 SLEEPING 1024 abcdefghij\n"
        for mode in (0,1):
            code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+bytes((0x3E,1,0x06,1,0x0E,0))+phase1._call(sy["sh_p819_ps_builtin"])+phase1._jp_c(FAIL_PC))
            for o,v in enumerate(expected): code+=expect(OUT+o,v)
            code+=expect(OUT+len(expected),0xA5)+phase1._jp(PASS_PC)
            try:
                run_sna(root,bytes(code),patch=patch(image,gb,mode))
            except DriverError as exc:
                raise P819Error(f"P8.19 output case mode={mode} failed: {exc}") from exc
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+bytes((0x3E,1,0x06,1,0x0E,0))+phase1._call(sy["sh_p819_ps_builtin"])+b"\xD2"+word(FAIL_PC)+bytes((0xFE,5))+phase1._jp_nz(FAIL_PC)+phase1._jp(PASS_PC))
        try:
            run_sna(root,bytes(code),patch=patch(image,gb,2))
        except DriverError as exc:
            raise P819Error(f"P8.19 PROC_INFO error case failed: {exc}") from exc
        for argc,stages,bg,err in ((2,1,0,sy["E_INVAL"]&255),(1,2,0,sy["E_NOTSUP"]&255),(1,1,1,sy["E_NOTSUP"]&255)):
            code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+bytes((0x3E,argc,0x06,stages,0x0E,bg))+phase1._call(sy["sh_p819_ps_builtin"])+b"\xD2"+word(FAIL_PC)+bytes((0xFE,err))+phase1._jp_nz(FAIL_PC)+phase1._jp(PASS_PC))
            try:
                run_sna(root,bytes(code),patch=patch(image,gb,0))
            except DriverError as exc:
                raise P819Error(f"P8.19 builtin-context argc={argc} stages={stages} bg={bg} failed: {exc}") from exc
        assertions += [{"name":"fuse-pid-state-memory-name","passed":True},{"name":"fuse-short-write-retried","passed":True},{"name":"fuse-proc-info-error-propagates","passed":True},{"name":"fuse-builtin-context-errors","passed":True}]
    hashes={"v1/src/shell/sh.asm":sha256_file(sp),"v1/build/p819-ps.mex1":sha256_file(mp),"v1/build/p819-ps-builtin.tap":sha256_file(tap),"v1/tools-host/test-driver/phase8_ps.py":sha256_file(root/"v1/tools-host/test-driver/phase8_ps.py"),"v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),"v1/dist/certification/P8.18.test.json":sha256_file(root/"v1/dist/certification/P8.18.test.json")}
    return [fr,gr,xr],hashes,assertions
