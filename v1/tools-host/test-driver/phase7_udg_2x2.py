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

LIB=0xC000
GATE=0xE000
BANK=0x7000

class P717Error(DriverError): pass
def req(v,m):
    if not v: raise P717Error(m)
def w(v): return bytes((v&255,(v>>8)&255))
def call(a): return b"\xcd"+w(a)
def checkb(a,v): return b"\x3a"+w(a)+bytes((0xfe,v&255))+phase1._jp_nz(FAIL_PC)
def checkw(a,v): return b"\x2a"+w(a)+phase1._ld_de(v)+b"\xb7\xed\x52"+phase1._jp_nz(FAIL_PC)

def bitmap_addr(y,col):
    return 0x4000 | ((y&7)<<8) | ((y&0xc0)<<5) | ((y&0x38)<<2) | col

def source(root):
    s=(root/"v1/src/libc48/udg.asm").read_text()
    p=(root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md").read_text()
    m=s.split("MACRO EMIT_P717_UDG_LIB_ROUTINES",1)[1].split("ENDM",1)[0]
    first=m.index("call udg_draw_2x2_one")
    return [
      {"name":"canonical-p717-present","passed":"## P7.17 - 2x2 UDG library helper" in p},
      {"name":"c48-regcall-register-validation","passed":all(x in m[:first] for x in ("ld a,h","ld a,d","ld a,b","cp 29","cp 23","cp 31"))},
      {"name":"all-fit-validation-before-first-draw","passed":m.index("cp 29")<first and m.index("cp 23")<first and m.index("cp 31")<first},
      {"name":"exact-four-sys-udg-draw-composition","passed":m.count("call udg_draw_2x2_one")==4 and "SYS_UDG_DRAW" in m},
      {"name":"no-kernel-state","passed":"kernel" not in s.lower() and "zx48_" not in m},
      {"name":"quadrant-offsets-explicit","passed":all(x in m for x in ("add a,2","add a,3","inc a"))},
    ]

def assemble(root,run_command,require_project_tool):
    asm=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus")
    b=root/"v1/build"; b.mkdir(parents=True,exist_ok=True)
    lf=b/"p717-lib.asm"
    lf.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/libc48/udg.asm"
    ORG $C000
p717_lib:
    EMIT_P717_UDG_LIB_ROUTINES
p717_lib_end:
    SAVEBIN "p717-lib.bin",p717_lib,p717_lib_end-p717_lib
""",encoding="utf-8",newline="\n")
    lr=run_command([asm,"--nologo","--sym=p717-lib.sym","p717-lib.asm"],cwd=b,timeout_seconds=30)
    req(lr.exit_code==0 and not lr.timed_out,f"library assembly: {lr.stderr or lr.stdout}")
    gf=b/"p717-gate.asm"
    gf.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/kernel/udg.asm"
    ORG $E000
p717_gate:
    cp SYS_UDG_DRAW
    jr nz,p717_gate_bad
    push hl
    ld de,(p717_log_ptr)
    ld a,(hl)
    ld (de),a
    inc hl
    inc de
    ld a,(hl)
    ld (de),a
    inc hl
    inc de
    ld a,(hl)
    ld (de),a
    inc de
    ld (p717_log_ptr),de
    ld a,(p717_count)
    inc a
    ld (p717_count),a
    pop hl
    call zx48_udg_draw
    ret
p717_gate_bad:
    ld a,E_NOTSUP
    scf
    ret

zx48_alloc:
    ld hl,$7000
    xor a
    ret
zx48_memory_pin_bytes: ret
zx48_memcpy: ldir : ret
zx48_cursor_hide: ret
zx48_cursor_show: ret
zx48_bitmap_address:
    ld a,b
    and 7
    or $40
    ld h,a
    ld a,b
    and $c0
    rrca
    rrca
    rrca
    or h
    ld h,a
    ld a,b
    and $38
    rlca
    rlca
    or c
    ld l,a
    ret
tty_current_attr: db $5d
    EMIT_UDG_ROUTINES
p717_count: db 0
p717_log_ptr: dw p717_log
p717_log: defs 12,0
p717_gate_end:
    SAVEBIN "p717-gate.bin",p717_gate,p717_gate_end-p717_gate
""",encoding="utf-8",newline="\n")
    gr=run_command([asm,"--nologo","--sym=p717-gate.sym","p717-gate.asm"],cwd=b,timeout_seconds=30)
    req(gr.exit_code==0 and not gr.timed_out,f"gateway assembly: {gr.stderr or gr.stdout}")
    return lr,gr,b/"p717-lib.bin",b/"p717-lib.sym",b/"p717-gate.bin",b/"p717-gate.sym"

def patch(lib,gate,g,patterns,attr=0x5d):
    def p(ram):
        ram[LIB-0x4000:LIB-0x4000+len(lib)]=lib
        ram[GATE-0x4000:GATE-0x4000+len(gate)]=gate
        ram[0:0x1b00]=b"\xa5"*0x1b00
        ram[BANK-0x4000:BANK-0x4000+256]=b"\0"*256
        for slot,pat in patterns.items():
            ram[BANK+slot*8-0x4000:BANK+slot*8-0x4000+8]=pat
        ram[g["udg_bank_ptr"]-0x4000:g["udg_bank_ptr"]-0x4000+2]=w(BANK)
        ram[g["tty_current_attr"]-0x4000]=attr
    return p

def invoke(s,base,row,col):
    return phase1._ld_hl(base)+phase1._ld_de(row)+bytes((0x01,))+w(col)+call(s["udg_draw_2x2"])

def valid_case(root,s,g,lib,gate,base,row,col,patterns,attr):
    code=bytearray(b"\xf3"+phase1._ld_sp(0xBFC0)+invoke(s,base,row,col))
    code+=bytes((0x7c,0xb5))+phase1._jp_nz(FAIL_PC)
    want=bytes((base,row,col,base+1,row,col+1,base+2,row+1,col,base+3,row+1,col+1))
    for i,v in enumerate(want): code+=checkb(g["p717_log"]+i,v)
    code+=checkb(g["p717_count"],4)
    for slot,rr,cc in ((base,row,col),(base+1,row,col+1),(base+2,row+1,col),(base+3,row+1,col+1)):
        pat=patterns[slot]
        for scan,v in enumerate(pat): code+=checkb(bitmap_addr(rr*8+scan,cc),v)
        code+=checkb(0x5800+rr*32+cc,attr)
    if col>0: code+=checkb(bitmap_addr(row*8,col-1),0xa5)+checkb(0x5800+row*32+col-1,0xa5)
    code+=phase1._jp(PASS_PC)
    run_sna(root,bytes(code),patch=patch(lib,gate,g,patterns,attr))

def invalid_case(root,s,g,lib,gate,base,row,col):
    code=bytearray(b"\xf3"+phase1._ld_sp(0xBFC0)+invoke(s,base,row,col))
    code+=phase1._ld_de(g["E_INVAL"])+b"\xb7\xed\x52"+phase1._jp_nz(FAIL_PC)
    code+=checkb(g["p717_count"],0)+checkb(0x4000,0xa5)+checkb(0x5aff,0xa5)+phase1._jp(PASS_PC)
    run_sna(root,bytes(code),patch=patch(lib,gate,g,{}))

def dispatch(root,action,step,*,sha256_file,run_command,require_project_tool):
    if step!="P7.17": raise P717Error(step)
    assertions=source(root); bad=[x["name"] for x in assertions if not x["passed"]]; req(not bad,f"static: {bad}")
    kc,kernel,_=phase1._assemble_kernel(root,run_command,require_project_tool)
    lr,gr,lb,ls,gb,gs=assemble(root,run_command,require_project_tool)
    s=phase3_open_descriptions._symbols(ls,("udg_draw_2x2",))
    g=phase3_open_descriptions._symbols(gs,("p717_count","p717_log","udg_bank_ptr","tty_current_attr","E_INVAL"))
    if action=="test":
        pats={
          4:bytes((0x81,0x42,0x24,0x18,0x18,0x24,0x42,0x81)),
          5:bytes((0xff,0x81,0x81,0x81,0x81,0x81,0x81,0xff)),
          6:bytes((0x18,0x3c,0x7e,0xff,0xff,0x7e,0x3c,0x18)),
          7:bytes((0xaa,0x55,0xaa,0x55,0xaa,0x55,0xaa,0x55)),
        }
        valid_case(root,s,g,lb.read_bytes(),gb.read_bytes(),4,10,15,pats,0x5d)
        edge={28:bytes((0x80,))*8,29:bytes((0x40,))*8,30:bytes((0x20,))*8,31:bytes((0x10,))*8}
        valid_case(root,s,g,lb.read_bytes(),gb.read_bytes(),28,22,30,edge,0x47)
        for args in ((29,0,0),(0,23,0),(0,0,31),(0x100,0,0),(0,0x100,0),(0,0,0x100)):
            invalid_case(root,s,g,lb.read_bytes(),gb.read_bytes(),*args)
        assertions += [
          {"name":"fuse-golden-2x2-quadrant-slot-order-exact","passed":True},
          {"name":"fuse-current-attribute-applied-to-all-four-cells","passed":True},
          {"name":"fuse-boundary-base28-row22-col30-exact","passed":True},
          {"name":"fuse-invalid-all-four-fit-rejected-before-first-draw","passed":True},
        ]
    hashes={str(x.relative_to(root)):sha256_file(x) for x in (
      root/"v1/src/libc48/udg.asm",root/"v1/tools-host/test-driver/phase7_udg_2x2.py",
      root/"v1/tools-host/test-driver/run.py",kernel)}
    return [kc,lr,gr],hashes,assertions
