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
STATUS=0xA280; STATCALLS=0xA282; WRITECALLS=0xA283; MODE=0xA284
class P816Error(DriverError): pass
def require(v,m):
    if not v: raise P816Error(m)
def expect(addr,val): return b"\x3A"+word(addr)+bytes((0xFE,val&255))+phase1._jp_nz(0x8F00)
def env1(path:bytes)->bytes:
    entry=b"PATH="+path+b"\0"
    return b"ENV1"+bytes((1,0))+word(8+len(entry))+entry
def patch(util,gate,args,path,mode=0):
    ab=arg1(args); eb=env1(path)
    def apply(ram):
        ram[UTIL-0x4000:UTIL-0x4000+len(util)]=util
        ram[GATE-0x4000:GATE-0x4000+len(gate)]=gate
        ram[ARG-0x4000:ARG-0x4000+len(ab)]=ab
        ram[ENV-0x4000:ENV-0x4000+len(eb)]=eb
        ram[OUT-0x4000:OUT-0x4000+96]=b"\xA5"*96
        ram[STATUS-0x4000:STATUS-0x4000+16]=b"\0"*16
        ram[MODE-0x4000]=mode
    return apply
def source_contract(root):
    s=(root/"v1/src/utils/which.asm").read_text(); p=(root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md").read_text()
    return [
      {"name":"canonical-p816-present","passed":"## P8.16 - Utility `which`" in p},
      {"name":"shell-path-algorithm-reused","passed":"EMIT_P614_PATH_ROUTINES" in s and "sh_p614_lookup_external" in s},
      {"name":"exact-path-env","passed":"which_path_key: db 'P','A','T','H','='" in s},
      {"name":"builtin-filter","passed":"which_builtin_table:" in s and "db 2,'c','d'" in s and "db 3,'r','o','m'" in s},
      {"name":"bin-only-path-resolution","passed":"cp OBJ_BIN" in (root/"v1/src/shell/sh.asm").read_text()},
      {"name":"catalog-only-no-tape-motion","passed":"SYS_OPEN" not in s and "SYS_SPAWN" not in s},
      {"name":"stdout-path-lf","passed":"ld (hl),10" in s and "SYS_WRITE" in s},
      {"name":"short-write-safe","passed":"which_write_loop:" in s and "which_write_zero:" in s},
    ]
def dispatch(root,action,step,*,sha256_file,run_command,require_project_tool):
    if step!="P8.16": raise DriverError(f"Phase-8 which step is not registered: {step}")
    assertions=source_contract(root); require(all(x["passed"] for x in assertions),"P8.16 static contract failure")
    tool=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus"); build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    try: ir,image,mex=assemble_utility(root,build,tool,"which","p816","EMIT_P816_WHICH_ROUTINES",run_command); xr=inspect_mex(root,mex,run_command,require_project_tool); tap=make_tap(root,build,"which","p816",mex)
    except RuntimeError as e: raise P816Error(str(e))
    require(256<=len(image)<4096,"P8.16 image size implausible")
    fix=build/"p816-which-fixture.asm"; fix.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/utils/which.asm"
    ORG $C000
fixture:
    EMIT_P816_WHICH_ROUTINES
fixture_end:
    SAVEBIN "p816-which-fixture.bin",fixture,fixture_end-fixture
""",newline="\n")
    fr=run_command([tool,"--nologo","--lst=p816-which-fixture.lst","--sym=p816-which-fixture.sym","p816-which-fixture.asm"],cwd=build,timeout_seconds=30); require(not fr.timed_out and fr.exit_code==0,f"P8.16 fixture assembly failed: {fr.stderr or fr.stdout}")
    gate=build/"p816-gateway.asm"; gate.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    ORG $E000
gate:
    cp SYS_STAT
    jp z,g_stat
    cp SYS_WRITE
    jp z,g_write
    cp SYS_EXIT
    jp z,g_exit
    ld a,E_NOTSUP
    scf
    ret
g_stat:
    ld a,($A282)
    inc a
    ld ($A282),a
    ld e,(hl)
    inc hl
    ld d,(hl)
    inc hl
    ld c,(hl)
    inc hl
    ld b,(hl)
    ex de,hl
    ld ix,g_cases
g_case_loop:
    ld a,(ix+0)
    cp $ff
    jr z,g_noent
    ld e,(ix+1)
    ld d,(ix+2)
    push hl
g_cmp:
    ld a,(de)
    cp (hl)
    jr nz,g_miss
    or a
    jr z,g_hit
    inc de
    inc hl
    jr g_cmp
g_miss:
    pop hl
    ld de,5
    add ix,de
    jr g_case_loop
g_hit:
    pop hl
    ld a,(ix+4)
    ld (bc),a
    inc bc
    xor a
    ld (bc),a
    inc bc
    ld (bc),a
    inc bc
    ld (bc),a
    inc bc
    ld (bc),a
    inc bc
    ld (bc),a
    inc bc
    ld (bc),a
    inc bc
    ld a,(ix+0)
    ld (bc),a
    inc bc
    xor a
    ld (bc),a
    inc bc
    ld (bc),a
    inc bc
    ld (bc),a
    ld hl,0
    xor a
    ret
g_noent:
    ld a,E_NOENT
    scf
    ret
g_write:
    ld a,($A283)
    inc a
    ld ($A283),a
    ld a,e
    cp 1
    jr nz,g_bad
    ld a,d
    or a
    jr nz,g_bad
    ld a,($A284)
    or a
    jr z,g_write_all
    ld a,b
    or a
    jr nz,g_write_two
    ld a,c
    cp 3
    jr c,g_write_all
g_write_two:
    ld bc,2
g_write_all:
    push bc
    ld de,(g_out)
    ldir
    ld (g_out),de
    pop hl
    xor a
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
; state/name/error/type encoded as state, ptr, unused, type
g_cases:
    db 0
    dw s_bin
    db 0,OBJ_DIR
    db 0
    dw s_dot
    db 0,OBJ_DIR
    db 0
    dw s_bin_ls
    db 0,OBJ_BIN
    db 0
    dw s_bin_text
    db 0,OBJ_TXT
    db 0
    dw s_dot_text
    db 0,OBJ_BIN
    db 1
    dw s_bin_lazy
    db 0,OBJ_BIN
    db $ff,0,0,0,0
s_bin: db '/','b','i','n',0
s_dot: db '.',0
s_bin_ls: db '/','b','i','n','/','l','s',0
s_bin_text: db '/','b','i','n','/','t','e','x','t',0
s_dot_text: db '.','/','t','e','x','t',0
s_bin_lazy: db '/','b','i','n','/','l','a','z','y',0
g_out: dw $A300
gate_end:
    SAVEBIN "p816-gateway.bin",gate,gate_end-gate
""",newline="\n")
    gr=run_command([tool,"--nologo","--lst=p816-gateway.lst","--sym=p816-gateway.sym","p816-gateway.asm"],cwd=build,timeout_seconds=30); require(not gr.timed_out and gr.exit_code==0,f"P8.16 gateway assembly failed: {gr.stderr or gr.stdout}")
    if action=="test":
        sy=phase3_open_descriptions._symbols(build/"p816-which-fixture.sym",("which_entry",)); ub=(build/"p816-which-fixture.bin").read_bytes(); gb=(build/"p816-gateway.bin").read_bytes()
        cases=[
          ([b"which",b"ls"],b"/bad:/bin:.",b"/bin/ls\n",0,0),
          ([b"which",b"text"],b"/bin:.",b"./text\n",0,1),
          ([b"which",b"lazy"],b"/bin:.",b"/bin/lazy\n",0,0),
          ([b"which",b"cd"],b"/bin:.",b"",1,0),
          ([b"which",b"LS"],b"/bin:.",b"",1,0),
          ([b"which",b"missing"],b"/bin:.",b"",1,0),
          ([b"which"],b"/bin:.",b"",1,0),
        ]
        for args,path,expected,status,mode in cases:
            ab=arg1(args); code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._ld_hl(ARG)+phase1._ld_de(ENV)+b"\x01"+word(len(ab))+phase1._call(sy["which_entry"]))
            for o,v in enumerate(expected): code+=expect(OUT+o,v)
            code+=expect(OUT+len(expected),0xA5)+expect(STATUS,status)+expect(STATUS+1,1)+phase1._jp(PASS_PC)
            try:
                run_sna(root,bytes(code),patch=patch(ub,gb,args,path,mode))
            except DriverError as exc:
                raise P816Error(f"runtime case {args!r} path={path!r} failed: {exc}") from exc
        assertions += [
          {"name":"fuse-path-left-to-right-exact-case","passed":True},
          {"name":"fuse-wrong-type-skipped","passed":True},
          {"name":"fuse-tape-backed-catalog-only","passed":True},
          {"name":"fuse-builtin-not-reported","passed":True},
          {"name":"fuse-short-write-retried","passed":True},
        ]
    hashes={"v1/src/utils/which.asm":sha256_file(root/"v1/src/utils/which.asm"),"v1/src/shell/sh.asm":sha256_file(root/"v1/src/shell/sh.asm"),"v1/build/p816-which.mex1":sha256_file(mex),"v1/build/p816-which.tap":sha256_file(tap),"v1/tools-host/test-driver/phase8_which.py":sha256_file(root/"v1/tools-host/test-driver/phase8_which.py"),"v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),"v1/dist/certification/P8.15.test.json":sha256_file(root/"v1/dist/certification/P8.15.test.json")}
    return [ir,xr,fr,gr],hashes,assertions
