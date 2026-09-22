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

from pathlib import Path
from driver_core import DriverError
from fuse_harness import FAIL_PC, PASS_PC, run_sna
import phase1, phase3_open_descriptions

UTIL=0xC000
GATE=0xE000
LIVE=0x7000
LOAD=0x9000
STAGED=0x9200
TARGET=0x9400
PATH=0xA000
ARG1=0xA100

class P716Error(DriverError): pass
def req(v,m):
    if not v: raise P716Error(m)
def w(v): return bytes((v&255,(v>>8)&255))
def call(a): return b"\xcd"+w(a)
def jpnc(a): return b"\xd2"+w(a)
def checkb(a,v): return b"\x3a"+w(a)+bytes((0xfe,v&255))+phase1._jp_nz(FAIL_PC)
def storeb(a,v): return bytes((0x3e,v&255,0x32))+w(a)
def checkmem(a,data):
    return b"".join(checkb(a+i,v) for i,v in enumerate(data))

def source(root):
    u=(root/"v1/src/utils/udg.asm").read_text()
    p=(root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md").read_text()
    inc=(root/"v1/include/zx48ux.inc").read_text()
    return [
      {"name":"canonical-p716-present","passed":"## P7.16 - UDG1 RAM persistence" in p},
      {"name":"udg1-public-constants","passed":all(x in inc for x in ("UDG1_HEADER_SIZE","UDG1_VERSION","UDG1_MAX_GLYPHS","UDG1_FULL_SIZE"))},
      {"name":"save-full-32-slot-header","passed":all(x in u for x in ("'U'","'D'","'G'","'1'","UDG1_VERSION","UDG1_MAX_GLYPHS","SYS_UDG_GET"))},
      {"name":"save-exclusive-temp-and-atomic-rename","passed":all(x in u for x in ("O_WRITE|O_CREATE|O_EXCL","OBJ_UDG","SYS_RENAME","SYS_REMOVE"))},
      {"name":"load-ram-udg-only","passed":"SYS_STAT" in u and "OBJ_UDG" in u and "STATE_RAM" in u},
      {"name":"raw-packed-logical-read","passed":"OBJ_PACKED" not in u and "SYS_READ" in u},
      {"name":"whole-payload-validated-before-define","passed":u.index("udg_load_validate:") < u.index("udg_load_apply_loop:") and "ld a,SYS_UDG_DEFINE" in u.split("udg_load_apply_loop:",1)[1].split("udg_load_format:",1)[0]},
      {"name":"no-secondary-checksum","passed":"crc" not in u.lower() and "checksum" not in u.lower()},
      {"name":"no-cassette-motion-path","passed":"SYS_TAPE_" not in u},
    ]

def assemble(root,run_command,require_project_tool):
    asm=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus")
    b=root/"v1/build"; b.mkdir(parents=True,exist_ok=True)
    f=b/"p716-util.asm"
    f.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/utils/udg.asm"
    ORG $C000
p716_util:
    EMIT_P716_UDG_UTILITY_ROUTINES
p716_util_end:
    SAVEBIN "p716-util.bin",p716_util,p716_util_end-p716_util
""",encoding="utf-8",newline="\n")
    ur=run_command([asm,"--nologo","--sym=p716-util.sym","p716-util.asm"],cwd=b,timeout_seconds=30)
    req(ur.exit_code==0 and not ur.timed_out,f"utility assembly: {ur.stderr or ur.stdout}")
    g=b/"p716-gate.asm"
    g.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
LIVE EQU $7000
LOAD EQU $9000
STAGED EQU $9200
TARGET EQU $9400
    ORG $E000
p716_gate:
    cp SYS_GETPID
    jp z,p716_getpid
    cp SYS_OPEN
    jp z,p716_open
    cp SYS_CLOSE
    jp z,p716_ok
    cp SYS_READ
    jp z,p716_read
    cp SYS_WRITE
    jp z,p716_write
    cp SYS_STAT
    jp z,p716_stat
    cp SYS_REMOVE
    jp z,p716_remove
    cp SYS_RENAME
    jp z,p716_rename
    cp SYS_UDG_GET
    jp z,p716_udg_get
    cp SYS_UDG_DEFINE
    jp z,p716_udg_define
    cp SYS_EXIT
    jp z,p716_exit
    cp SYS_TAPE_SAVE
    jr c,p716_unknown
    cp SYS_TAPE_SCAN+1
    jr nc,p716_unknown
    ld a,(p716_tape_motion)
    inc a
    ld (p716_tape_motion),a
    ld a,E_NOTSUP
    scf
    ret
p716_unknown:
    ld a,E_NOTSUP
    scf
    ret
p716_ok:
    xor a
    ret
p716_getpid:
    ld hl,1
    xor a
    ret
p716_open:
    ld a,c
    and O_CREATE
    jr z,p716_open_read
    ld a,(p716_force_open)
    or a
    jp nz,p716_io_fail
    ld a,b
    ld (p716_create_type),a
    ld a,c
    ld (p716_create_flags),a
    ld hl,3
    xor a
    ret
p716_open_read:
    ld hl,4
    xor a
    ret
p716_write:
    ld a,(p716_force_write)
    or a
    jp nz,p716_io_fail
    ld a,d
    or a
    jp nz,p716_bad
    ld a,e
    cp 3
    jp nz,p716_bad
    ld (p716_staged_len),bc
    push bc
    ld de,STAGED
    ldir
    pop hl
    xor a
    ret
p716_read:
    ld a,(p716_force_read)
    or a
    jp nz,p716_io_fail
    ld a,d
    or a
    jp nz,p716_bad
    ld a,e
    cp 4
    jp nz,p716_bad
    push bc
    push hl
    ld hl,LOAD
    pop de
    ldir
    pop hl
    xor a
    ret
p716_stat:
    inc hl
    inc hl
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld a,(p716_load_type)
    ld (de),a
    inc de
    ld a,(p716_load_flags)
    ld (de),a
    inc de
    ld hl,(p716_load_len)
    ld a,l
    ld (de),a
    inc de
    ld a,h
    ld (de),a
    inc de
    ld a,l
    ld (de),a
    inc de
    ld a,h
    ld (de),a
    inc de
    ld a,DIR_USERHOME
    ld (de),a
    inc de
    ld a,(p716_load_state)
    ld (de),a
    inc de
    xor a
    ld (de),a
    inc de
    ld (de),a
    ret
p716_remove:
    ld a,(p716_remove_calls)
    inc a
    ld (p716_remove_calls),a
    xor a
    ret
p716_rename:
    ld a,(p716_force_rename)
    or a
    jp nz,p716_io_fail
    ld a,1
    ld (p716_committed),a
    ld bc,(p716_staged_len)
    ld hl,STAGED
    ld de,TARGET
    ldir
    xor a
    ret
p716_udg_get:
    ld a,b
    or a
    jp nz,p716_bad
    ld a,c
    cp 32
    jp nc,p716_bad
    push hl
    add a,a
    add a,a
    add a,a
    ld e,a
    ld d,0
    ld hl,LIVE
    add hl,de
    ex de,hl
    pop hl
    ex de,hl
    ld bc,8
    ldir
    xor a
    ret
p716_udg_define:
    ld a,b
    or a
    jp nz,p716_bad
    ld a,c
    cp 32
    jp nc,p716_bad
    push hl
    add a,a
    add a,a
    add a,a
    ld e,a
    ld d,0
    ld hl,LIVE
    add hl,de
    ex de,hl
    pop hl
    ld bc,8
    ldir
    ld a,(p716_define_calls)
    inc a
    ld (p716_define_calls),a
    xor a
    ret
p716_exit:
    ld a,l
    ld (p716_exit_status),a
    xor a
    ret
p716_io_fail:
    ld a,E_IO
    scf
    ret
p716_bad:
    ld a,E_INVAL
    scf
    ret
p716_force_open: db 0
p716_force_write: db 0
p716_force_read: db 0
p716_force_rename: db 0
p716_create_type: db 0
p716_create_flags: db 0
p716_committed: db 0
p716_remove_calls: db 0
p716_tape_motion: db 0
p716_define_calls: db 0
p716_exit_status: db $ff
p716_load_type: db OBJ_UDG
p716_load_flags: db 0
p716_load_state: db STATE_RAM
p716_staged_len: dw 0
p716_load_len: dw 0
p716_gate_end:
    SAVEBIN "p716-gate.bin",p716_gate,p716_gate_end-p716_gate
""",encoding="utf-8",newline="\n")
    gr=run_command([asm,"--nologo","--sym=p716-gate.sym","p716-gate.asm"],cwd=b,timeout_seconds=30)
    req(gr.exit_code==0 and not gr.timed_out,f"gateway assembly: {gr.stderr or gr.stdout}")
    return ur,gr,b/"p716-util.bin",b/"p716-util.sym",b/"p716-gate.bin",b/"p716-gate.sym"

def symbols(path,names):
    return phase3_open_descriptions._symbols(path,names)

def basepatch(util,gate,live=None,load=None,target=None,gv=None):
    def p(ram):
        ram[UTIL-0x4000:UTIL-0x4000+len(util)]=util
        ram[GATE-0x4000:GATE-0x4000+len(gate)]=gate
        ram[PATH-0x4000:PATH-0x4000+6]=b"icons\0"
        ram[LIVE-0x4000:LIVE-0x4000+256]=live if live is not None else b"\xa5"*256
        ram[LOAD-0x4000:LOAD-0x4000+264]=b"\0"*264
        if load is not None: ram[LOAD-0x4000:LOAD-0x4000+len(load)]=load
        ram[STAGED-0x4000:STAGED-0x4000+264]=b"\xcc"*264
        ram[TARGET-0x4000:TARGET-0x4000+264]=target if target is not None else b"\x5a"*264
        if gv:
            for a,v in gv.items():
                if isinstance(v,int) and v<=255: ram[a-0x4000]=v
                else:
                    vv=int(v); ram[a-0x4000:a-0x4000+2]=w(vv)
    return p

def runtime(root,u,g,util,gate):
    def execute(label, code, patch):
        try:
            run_sna(root,code,patch=patch)
        except DriverError as exc:
            raise P716Error(f"{label}: {exc}") from exc
    live=bytes(((i*37+11)&255) for i in range(256))
    want=b"UDG1"+bytes((1,0,32,0))+live
    code=bytearray(b"\xf3"+phase1._ld_sp(0xBFC0)+phase1._ld_hl(PATH)+call(u["udg_save_path"])+phase1._jp_c(FAIL_PC))
    code+=checkb(g["p716_create_type"],g["OBJ_UDG"])+checkb(g["p716_create_flags"],g["O_WRITE"]|g["O_CREATE"]|g["O_EXCL"])
    code+=checkb(g["p716_committed"],1)+checkb(g["p716_tape_motion"],0)+checkmem(TARGET,want)+phase1._jp(PASS_PC)
    execute("save-full",bytes(code),basepatch(util,gate,live=live))
    for flag in ("p716_force_write","p716_force_rename"):
        old=bytes(((i*13+7)&255) for i in range(264))
        code=bytearray(b"\xf3"+phase1._ld_sp(0xBFC0)+phase1._ld_hl(PATH)+call(u["udg_save_path"])+jpnc(FAIL_PC)+bytes((0xfe,g["E_IO"]))+phase1._jp_nz(FAIL_PC))
        code+=checkb(g["p716_committed"],0)+checkb(g["p716_remove_calls"],1)+checkb(g["p716_tape_motion"],0)+checkmem(TARGET,old)+phase1._jp(PASS_PC)
        execute(f"save-failure-{flag}",bytes(code),basepatch(util,gate,live=live,target=old,gv={g[flag]:1}))
    payload=b"UDG1"+bytes((1,2,2,0))+bytes(range(16))
    for flags in (0,g["OBJ_PACKED"]):
        code=bytearray(b"\xf3"+phase1._ld_sp(0xBFC0)+phase1._ld_hl(PATH)+call(u["udg_load_path"])+phase1._jp_c(FAIL_PC))
        code+=checkb(g["p716_define_calls"],2)+checkb(g["p716_tape_motion"],0)
        code+=checkmem(LIVE+16,bytes(range(16)))+checkmem(LIVE+8,b"\xa5"*8)+checkmem(LIVE+32,b"\xa5"*8)+phase1._jp(PASS_PC)
        execute(f"load-range-flags-{flags}",bytes(code),basepatch(util,gate,load=payload,gv={g["p716_load_len"]:len(payload),g["p716_load_flags"]:flags}))
    full=b"UDG1"+bytes((1,0,32,0))+live
    code=bytearray(b"\xf3"+phase1._ld_sp(0xBFC0)+phase1._ld_hl(PATH)+call(u["udg_load_path"])+phase1._jp_c(FAIL_PC))
    code+=checkb(g["p716_define_calls"],32)+checkmem(LIVE,live)+phase1._jp(PASS_PC)
    execute("load-full",bytes(code),basepatch(util,gate,load=full,gv={g["p716_load_len"]:len(full)}))
    bad=[]
    x=bytearray(payload); x[0]=ord("X"); bad.append(bytes(x))
    x=bytearray(payload); x[4]=2; bad.append(bytes(x))
    x=bytearray(payload); x[7]=1; bad.append(bytes(x))
    x=bytearray(payload); x[6]=0; bad.append(bytes(x))
    x=bytearray(payload); x[5]=31; x[6]=2; bad.append(bytes(x))
    for malformed in bad:
        code=bytearray(b"\xf3"+phase1._ld_sp(0xBFC0)+phase1._ld_hl(PATH)+call(u["udg_load_path"])+jpnc(FAIL_PC)+bytes((0xfe,g["E_FORMAT"]))+phase1._jp_nz(FAIL_PC))
        code+=checkb(g["p716_define_calls"],0)+checkb(LIVE,0xa5)+checkb(LIVE+255,0xa5)+checkb(g["p716_tape_motion"],0)+phase1._jp(PASS_PC)
        execute("load-malformed",bytes(code),basepatch(util,gate,load=malformed,gv={g["p716_load_len"]:len(malformed)}))
    code=bytearray(b"\xf3"+phase1._ld_sp(0xBFC0)+phase1._ld_hl(PATH)+call(u["udg_load_path"])+jpnc(FAIL_PC)+bytes((0xfe,g["E_FORMAT"]))+phase1._jp_nz(FAIL_PC))
    code+=checkb(g["p716_define_calls"],0)+checkb(LIVE,0xa5)+checkb(g["p716_tape_motion"],0)+phase1._jp(PASS_PC)
    execute("load-length-mismatch",bytes(code),basepatch(util,gate,load=payload+b"\0",gv={g["p716_load_len"]:len(payload)+1}))
    code=bytearray(b"\xf3"+phase1._ld_sp(0xBFC0)+phase1._ld_hl(PATH)+call(u["udg_load_path"])+jpnc(FAIL_PC)+bytes((0xfe,g["E_IO"]))+phase1._jp_nz(FAIL_PC))
    code+=checkb(g["p716_define_calls"],0)+checkb(LIVE,0xa5)+checkb(g["p716_tape_motion"],0)+phase1._jp(PASS_PC)
    execute("load-read-failure",bytes(code),basepatch(util,gate,load=payload,gv={g["p716_load_len"]:len(payload),g["p716_force_read"]:1}))

def dispatch(root,action,step,*,sha256_file,run_command,require_project_tool):
    if step!="P7.16": raise P716Error(step)
    assertions=source(root); bad=[x["name"] for x in assertions if not x["passed"]]; req(not bad,f"static: {bad}")
    kc,kernel,_=phase1._assemble_kernel(root,run_command,require_project_tool)
    ur,gr,ub,us,gb,gs=assemble(root,run_command,require_project_tool)
    un=("udg_save_path","udg_load_path","udg_entry")
    gn=("p716_force_open","p716_force_write","p716_force_read","p716_force_rename","p716_create_type","p716_create_flags","p716_committed","p716_remove_calls","p716_tape_motion","p716_define_calls","p716_exit_status","p716_load_type","p716_load_flags","p716_load_state","p716_staged_len","p716_load_len","OBJ_UDG","OBJ_PACKED","O_WRITE","O_CREATE","O_EXCL","E_IO","E_FORMAT")
    u=symbols(us,un); g=symbols(gs,gn)
    if action=="test":
        runtime(root,u,g,ub.read_bytes(),gb.read_bytes())
        assertions += [
          {"name":"fuse-save-full-udg1-exact-and-atomic-rename","passed":True},
          {"name":"fuse-save-failure-preserves-prior-object","passed":True},
          {"name":"fuse-raw-packed-load-identical-live-bytes","passed":True},
          {"name":"fuse-full-and-ranged-bank-load-exact","passed":True},
          {"name":"fuse-invalid-payload-zero-live-mutation","passed":True},
          {"name":"fuse-no-tape-motion","passed":True},
        ]
    hashes={str(x.relative_to(root)):sha256_file(x) for x in (
      root/"v1/include/zx48ux.inc",root/"v1/src/utils/udg.asm",
      root/"v1/tools-host/test-driver/phase7_udg_persistence.py",root/"v1/tools-host/test-driver/run.py",kernel)}
    return [kc,ur,gr],hashes,assertions
