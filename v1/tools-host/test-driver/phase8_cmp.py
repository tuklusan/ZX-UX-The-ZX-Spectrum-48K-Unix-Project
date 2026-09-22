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

UTIL=0xC000; GATE=0xE000; ARG=0xA000; MODE=0xA2F0; STATUS=0xA2F1; COUNTERS=0xA2F3
class P812Error(DriverError): pass
def require(v,m):
    if not v: raise P812Error(m)
def expect(addr,val): return b"\x3A"+word(addr)+bytes((0xFE,val&255))+phase1._jp_nz(0x8F00)
def patch(util,gate,args,mode):
    block=arg1(args)
    def apply(ram):
        ram[UTIL-0x4000:UTIL-0x4000+len(util)]=util; ram[GATE-0x4000:GATE-0x4000+len(gate)]=gate
        ram[ARG-0x4000:ARG-0x4000+len(block)]=block; ram[MODE-0x4000]=mode
        ram[STATUS-0x4000:STATUS-0x4000+16]=b"\0"*16
    return apply
def source_contract(root):
    s=(root/"v1/src/utils/cmp.asm").read_text(); p=(root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md").read_text()
    return [
      {"name":"canonical-p812-present","passed":"## P8.12 - Utility `cmp`" in p},
      {"name":"exact-two-operands","passed":"cp 3" in s and "E_INVAL" in s},
      {"name":"ram-only-stat","passed":"SYS_STAT" in s and "cp STATE_RAM" in s and "E_PERM" in s},
      {"name":"two-read-handles","passed":"cmp_handle_a" in s and "cmp_handle_b" in s and "SYS_READ" in s},
      {"name":"bytewise","passed":"cmp_byte_a" in s and "cmp_byte_b" in s and "cp b" in s},
      {"name":"length-difference","passed":"cmp_count_a" in s and "cmp_count_b" in s and "cmp_different:" in s},
      {"name":"equal-zero-different-one","passed":"ld l,0" in s and "ld l,1" in s},
      {"name":"close-cleanup","passed":"cmp_close_best:" in s and "SYS_CLOSE" in s},
      {"name":"no-output","passed":"SYS_WRITE" not in s},
    ]
def dispatch(root,action,step,*,sha256_file,run_command,require_project_tool):
    if step!="P8.12": raise DriverError(f"Phase-8 cmp step is not registered: {step}")
    assertions=source_contract(root); require(all(x["passed"] for x in assertions),"P8.12 static contract failure")
    tool=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus"); build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    try: ir,image,mex=assemble_utility(root,build,tool,"cmp","p812","EMIT_P812_CMP_ROUTINES",run_command); xr=inspect_mex(root,mex,run_command,require_project_tool); tap=make_tap(root,build,"cmp","p812",mex)
    except RuntimeError as e: raise P812Error(str(e))
    require(96<=len(image)<2048,"P8.12 image size implausible")
    fix=build/"p812-cmp-fixture.asm"; fix.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/utils/cmp.asm"
    ORG $C000
fixture:
    EMIT_P812_CMP_ROUTINES
fixture_end:
    SAVEBIN "p812-cmp-fixture.bin",fixture,fixture_end-fixture
""",newline="\n")
    fr=run_command([tool,"--nologo","--lst=p812-cmp-fixture.lst","--sym=p812-cmp-fixture.sym","p812-cmp-fixture.asm"],cwd=build,timeout_seconds=30); require(not fr.timed_out and fr.exit_code==0,f"P8.12 fixture assembly failed: {fr.stderr or fr.stdout}")
    gate=build/"p812-gateway.asm"; gate.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    ORG $E000
gate:
    cp SYS_STAT
    jp z,g_stat
    cp SYS_OPEN
    jp z,g_open
    cp SYS_READ
    jp z,g_read
    cp SYS_CLOSE
    jp z,g_close
    cp SYS_EXIT
    jp z,g_exit
    ld a,E_NOTSUP
    scf
    ret
g_stat:
    ld a,($A2F3)
    inc a
    ld ($A2F3),a
    inc hl
    inc hl
    ld e,(hl)
    inc hl
    ld d,(hl)
    ex de,hl
    ld (hl),OBJ_DAT
    inc hl
    xor a
    ld (hl),a
    inc hl
    ld (hl),3
    inc hl
    xor a
    ld (hl),a
    inc hl
    ld (hl),3
    inc hl
    xor a
    ld (hl),a
    inc hl
    ld (hl),DIR_TMP
    inc hl
    ld a,($A2F0)
    cp 4
    jr nz,g_stat_ram
    ld a,($A2F3)
    cp 2
    jr nz,g_stat_ram
    ld a,STATE_TAPE_BACKED
    jr g_stat_state
g_stat_ram:
    ld a,STATE_RAM
g_stat_state:
    ld (hl),a
    inc hl
    xor a
    ld (hl),a
    inc hl
    ld (hl),a
    xor a
    ret
g_open:
    ld a,($A2F4)
    inc a
    ld ($A2F4),a
    ld b,a
    ld a,($A2F0)
    cp 5
    jr nz,g_open_ok
    ld a,b
    cp 2
    jr nz,g_open_ok
    ld a,E_NOENT
    scf
    ret
g_open_ok:
    ld a,b
    add a,2
    ld l,a
    ld h,0
    xor a
    ret
g_read:
    ld a,($A2F0)
    cp 3
    jr nz,g_read_select
    ld a,e
    cp 4
    jr nz,g_read_select
    ld a,E_IO
    scf
    ret
g_read_select:
    ld a,e
    cp 3
    jr z,g_read_a
    ld de,g_data_b
    ld a,(g_idx_b)
    ld c,a
    ld a,($A2F0)
    cp 1
    jr z,g_b_diff
    cp 2
    jr z,g_b_short
    ld b,3
    jr g_read_common
g_b_diff:
    ld de,g_data_b_diff
    ld b,3
    jr g_read_common
g_b_short:
    ld de,g_data_b
    ld b,2
    jr g_read_common
g_read_a:
    ld de,g_data_a
    ld a,(g_idx_a)
    ld c,a
    ld b,3
g_read_common:
    ld a,c
    cp b
    jr z,g_eof
    push hl
    ld h,0
    ld l,c
    add hl,de
    ld a,(hl)
    pop hl
    ld (hl),a
    ld a,e
    ld a,($A2F0)
    ; increment the index corresponding to handle saved in syscall DE.
    ; Handle is still in E only for entry, so use destination stream order:
    ld a,($A2F6)
    xor a
    ; Determine by source base selected above.
    ld a,d
    ; explicit branches below avoid relying on this scratch value.
    ld a,($A2F0)
    ; Re-read syscall handle is unavailable after DE reuse; infer by comparing selected base.
    push hl
    ld hl,g_data_a
    or a
    sbc hl,de
    pop hl
    jr nz,g_inc_b
    ld a,(g_idx_a)
    inc a
    ld (g_idx_a),a
    jr g_one
g_inc_b:
    ld a,(g_idx_b)
    inc a
    ld (g_idx_b),a
g_one:
    ld hl,1
    xor a
    ret
g_eof:
    ld hl,0
    xor a
    ret
g_close:
    ld a,($A2F5)
    inc a
    ld ($A2F5),a
    xor a
    ret
g_exit:
    ld a,l
    ld ($A2F1),a
    ld a,1
    ld ($A2F6),a
    xor a
    ret
g_data_a: db 'a','b','c'
g_data_b: db 'a','b','c'
g_data_b_diff: db 'a','b','d'
g_idx_a: db 0
g_idx_b: db 0
gate_end:
    SAVEBIN "p812-gateway.bin",gate,gate_end-gate
""",newline="\n")
    gr=run_command([tool,"--nologo","--lst=p812-gateway.lst","--sym=p812-gateway.sym","p812-gateway.asm"],cwd=build,timeout_seconds=30); require(not gr.timed_out and gr.exit_code==0,f"P8.12 gateway assembly failed: {gr.stderr or gr.stdout}")
    if action=="test":
        sy=phase3_open_descriptions._symbols(build/"p812-cmp-fixture.sym",("cmp_entry",)); ub=(build/"p812-cmp-fixture.bin").read_bytes(); gb=(build/"p812-gateway.bin").read_bytes()
        cases=[([b"cmp",b"a",b"b"],0,0),([b"cmp",b"a",b"b"],1,1),([b"cmp",b"a",b"b"],2,1),([b"cmp",b"a",b"b"],3,5),([b"cmp",b"a",b"b"],4,7),([b"cmp",b"a",b"b"],5,2),([b"cmp",b"a"],0,1)]
        for args,mode,status in cases:
            block=arg1(args); code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._ld_hl(ARG)+b"\x01"+word(len(block))+phase1._call(sy["cmp_entry"]))
            code+=expect(STATUS,status)+expect(STATUS+5,1)+phase1._jp(PASS_PC)
            run_sna(root,bytes(code),patch=patch(ub,gb,args,mode))
        assertions += [{"name":"fuse-equal-zero","passed":True},{"name":"fuse-byte-different-one","passed":True},{"name":"fuse-length-different-one","passed":True},{"name":"fuse-read-error","passed":True},{"name":"fuse-nonram-eperm","passed":True},{"name":"fuse-open-error","passed":True},{"name":"fuse-invalid-arity","passed":True}]
    hashes={"v1/src/utils/cmp.asm":sha256_file(root/"v1/src/utils/cmp.asm"),"v1/build/p812-cmp.mex1":sha256_file(mex),"v1/build/p812-cmp.tap":sha256_file(tap),"v1/tools-host/test-driver/phase8_cmp.py":sha256_file(root/"v1/tools-host/test-driver/phase8_cmp.py"),"v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),"v1/dist/certification/P8.11.test.json":sha256_file(root/"v1/dist/certification/P8.11.test.json")}
    return [ir,xr,fr,gr],hashes,assertions
