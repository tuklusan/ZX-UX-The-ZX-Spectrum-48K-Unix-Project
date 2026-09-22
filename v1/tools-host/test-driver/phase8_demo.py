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

UTIL=0xC000; GATE=0xE000; ARG=0xA000; ENV=0xA120; OUT=0xA400; STATUS=0xA300; MODE=0xA301; LOADS=0xA302; SPAWNED=0xA303
class P836Error(DriverError):
    pass
def require(v,m):
    if not v: raise P836Error(m)
def expect(a,v): return b"\x3A"+word(a)+bytes((0xFE,v&255))+phase1._jp_nz(FAIL_PC)
def env1():
    body=b"USER=ada\0HOME=/home/ada\0PATH=/bin:.\0"
    return b"ENV1"+bytes((3,0))+word(8+len(body))+body
def patch(util,gate,args,mode):
    ab=arg1(args); eb=env1()
    def apply(ram):
        ram[UTIL-0x4000:UTIL-0x4000+len(util)]=util
        ram[GATE-0x4000:GATE-0x4000+len(gate)]=gate
        ram[ARG-0x4000:ARG-0x4000+len(ab)]=ab
        ram[ENV-0x4000:ENV-0x4000+len(eb)]=eb
        ram[OUT-0x4000:OUT-0x4000+256]=b"\xA5"*256
        ram[STATUS-0x4000]=0xFF; ram[MODE-0x4000]=mode; ram[LOADS-0x4000]=0; ram[SPAWNED-0x4000]=0
    return apply

def dispatch(root,action,step,*,sha256_file,run_command,require_project_tool):
    if step!="P8.36": raise DriverError(step)
    s=(root/"v1/src/utils/demo.asm").read_text(encoding="utf-8")
    p=(root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md").read_text(encoding="utf-8")
    assertions=[
      {"name":"canonical-p836-present","passed":"## P8.36 - Utility `demo`" in p},
      {"name":"all-thirteen-pairs","passed":"DEMO_COUNT EQU 13" in s and "demo_s12:" in s and "demo_n12:" in s},
      {"name":"exact-case-table","passed":"casefold" not in s.lower() and "demo_streq:" in s},
      {"name":"preserve-resident","passed":"demo_ensure:" in s and "SYS_STAT" in s and "SYS_TAPE_LOAD" in s},
      {"name":"wrong-type-refusal","passed":"demo_wrong_type:" in s and "E_FORMAT" in s},
      {"name":"spawn-wait","passed":"SYS_SPAWN" in s and "SYS_WAIT" in s},
      {"name":"rebuild-hint","passed":"demo_print_hint:" in s and "Edit/rebuild" not in s},
    ]
    require(all(x["passed"] for x in assertions),"P8.36 static contract failure")
    tool=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus"); b=root/"v1/build"; b.mkdir(parents=True,exist_ok=True)
    try:
        ir,image,mex=assemble_utility(root,b,tool,"demo","p836","EMIT_P836_DEMO_ROUTINES",run_command)
        xr=inspect_mex(root,mex,run_command,require_project_tool); tap=make_tap(root,b,"demo","p836",mex)
    except RuntimeError as e: raise P836Error(str(e))
    require(512<=len(image)<8192,"P8.36 image size implausible")
    fix=b/"p836-demo-fixture.asm"; fix.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/utils/demo.asm"
    ORG $C000
fixture:
    EMIT_P836_DEMO_ROUTINES
fixture_end:
    SAVEBIN "p836-demo-fixture.bin",fixture,fixture_end-fixture
""",encoding="utf-8",newline="\n")
    fr=run_command([tool,"--nologo","--lst=p836-demo-fixture.lst","--sym=p836-demo-fixture.sym",fix.name],cwd=b,timeout_seconds=30); require(not fr.timed_out and fr.exit_code==0,f"P8.36 fixture: {fr.stderr or fr.stdout}")
    gate=b/"p836-gateway.asm"; gate.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    ORG $E000
gate:
    cp SYS_STAT
    jp z,g_stat
    cp SYS_TAPE_LOAD
    jp z,g_load
    cp SYS_WRITE
    jp z,g_write
    cp SYS_SPAWN
    jp z,g_spawn
    cp SYS_WAIT
    jp z,g_wait
    cp SYS_EXIT
    jp z,g_exit
    ld a,E_NOTSUP
    scf
    ret
g_stat:
    ld e,(hl)
    inc hl
    ld d,(hl)
    inc hl
    ld c,(hl)
    inc hl
    ld b,(hl)
    ex de,hl
    push bc
    ld de,g_ship_c
    call g_streq
    pop bc
    jr z,g_stat_source
    push bc
    ld de,g_ship
    call g_streq
    pop bc
    jr z,g_stat_exec
    ld a,E_NOENT
    scf
    ret
g_stat_source:
    ld a,($A301)
    cp 1
    jr nz,g_source_present
    ld a,(g_loaded_source)
    or a
    jr nz,g_source_present
    ld a,E_NOENT
    scf
    ret
g_source_present:
    ld a,($A301)
    cp 2
    ld a,OBJ_C
    jr nz,g_stat_store
    ld a,OBJ_TXT
    jr g_stat_store
g_stat_exec:
    ld a,OBJ_BIN
g_stat_store:
    ld h,b
    ld l,c
    ld (hl),a
    inc hl
    xor a
    ld (hl),a
    inc hl
    ld b,8
g_stat_zero:
    ld (hl),a
    inc hl
    djnz g_stat_zero
    xor a
    ret
g_load:
    push hl
    ld de,g_ship_c
    call g_streq
    pop hl
    jr nz,g_load_bad
    ld a,1
    ld (g_loaded_source),a
    ld a,($A302)
    inc a
    ld ($A302),a
    xor a
    ret
g_load_bad:
    ld a,E_NOENT
    scf
    ret
g_spawn:
    ld e,(hl)
    inc hl
    ld d,(hl)
    ex de,hl
    ld de,g_ship
    call g_streq
    jr nz,g_bad
    ld a,1
    ld ($A303),a
    ld hl,2
    xor a
    ret
g_wait:
    ld e,(hl)
    inc hl
    ld d,(hl)
    inc hl
    ld e,(hl)
    inc hl
    ld d,(hl)
    ex de,hl
    xor a
    ld (hl),a
    ld hl,0
    xor a
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
g_streq:
    ld a,(de)
    cp (hl)
    ret nz
    or a
    ret z
    inc de
    inc hl
    jr g_streq
g_bad:
    ld a,E_INVAL
    scf
    ret
g_ship: db "ship",0
g_ship_c: db "ship.c",0
g_loaded_source: db 0
g_out: dw $A400
gate_end:
    SAVEBIN "p836-gateway.bin",gate,gate_end-gate
""",encoding="utf-8",newline="\n")
    gr=run_command([tool,"--nologo","--lst=p836-gateway.lst","--sym=p836-gateway.sym",gate.name],cwd=b,timeout_seconds=30); require(not gr.timed_out and gr.exit_code==0,f"P8.36 gateway: {gr.stderr or gr.stdout}")
    if action=="test":
        sy=phase3_open_descriptions._symbols(b/"p836-demo-fixture.sym",("demo_entry","E_NOENT","E_FORMAT"))
        ub=(b/"p836-demo-fixture.bin").read_bytes(); gb=(b/"p836-gateway.bin").read_bytes()
        list_expected=(b"hello hello.c\ncolors colors.c\nlines lines.c\nship ship.c\nball ball.c\nstars stars.c\nlife life.c\nmaze maze.c\nsine sine.c\nmandel mandel.c\ntune tune.c\npipe pipe.c\nmulti multi.c\n")
        args=[b"demo"]; ab=arg1(args); code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._ld_hl(ARG)+b"\x01"+word(len(ab))+b"\x11"+word(ENV)+phase1._call(sy["demo_entry"]))
        for i,v in enumerate(list_expected): code+=expect(OUT+i,v)
        code+=expect(OUT+len(list_expected),0xA5)+expect(STATUS,0)+phase1._jp(PASS_PC)
        try: run_sna(root,bytes(code),patch=patch(ub,gb,args,0),timeout=30)
        except Exception as e: raise P836Error(f"P8.36 list case failed: {e}")
        for mode,loads,status,spawned in ((0,0,0,1),(1,1,0,1),(2,0,sy["E_FORMAT"]&255,0)):
            args=[b"demo",b"ship"]; ab=arg1(args)
            observed={}
            for label,addr,want in (("status",STATUS,status),("loads",LOADS,loads),("spawned",SPAWNED,spawned)):
                actual=None
                for candidate in range(256):
                    code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._ld_hl(ARG)+b"\x01"+word(len(ab))+b"\x11"+word(ENV)+phase1._call(sy["demo_entry"])+expect(addr,candidate)+phase1._jp(PASS_PC))
                    try:
                        run_sna(root,bytes(code),patch=patch(ub,gb,args,mode),timeout=30)
                        actual=candidate
                        break
                    except Exception:
                        pass
                observed[label]=(actual,want)
            if any(actual != want for actual,want in observed.values()):
                raise P836Error(f"P8.36 ship mode={mode}: {observed}")
        args=[b"demo",b"SHIP"]; ab=arg1(args); code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._ld_hl(ARG)+b"\x01"+word(len(ab))+b"\x11"+word(ENV)+phase1._call(sy["demo_entry"])+expect(STATUS,sy["E_NOENT"]&255)+expect(SPAWNED,0)+phase1._jp(PASS_PC))
        try: run_sna(root,bytes(code),patch=patch(ub,gb,args,0),timeout=30)
        except Exception as e: raise P836Error(f"P8.36 wrong-case failed: {e}")
        assertions += [{"name":"fuse-list-all-pairs","passed":True},{"name":"fuse-resident-preserved","passed":True},{"name":"fuse-load-only-missing","passed":True},{"name":"fuse-wrong-type-refusal","passed":True},{"name":"fuse-wrong-case-refusal","passed":True}]
    hashes={"v1/src/utils/demo.asm":sha256_file(root/"v1/src/utils/demo.asm"),"v1/build/p836-demo.mex1":sha256_file(mex),"v1/build/p836-demo.tap":sha256_file(tap),"v1/tools-host/test-driver/phase8_demo.py":sha256_file(root/"v1/tools-host/test-driver/phase8_demo.py"),"v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),"v1/dist/certification/P8.35.test.json":sha256_file(root/"v1/dist/certification/P8.35.test.json")}
    return [ir,xr,fr,gr],hashes,assertions
