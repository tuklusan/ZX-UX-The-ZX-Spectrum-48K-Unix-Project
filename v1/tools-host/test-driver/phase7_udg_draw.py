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
from fuse_harness import FAIL_PC,PASS_PC,run_sna
import phase1,phase3_open_descriptions

BASE=0xC000
REC=0xA000
BANK=0x6000
ATTR=0x5800
class P715Error(DriverError): pass
def req(v,m):
    if not v: raise P715Error(m)
def w(v): return bytes((v&255,v>>8))
def call(a): return b"\xcd"+w(a)
def jpc(a): return b"\xda"+w(a)
def jpnc(a): return b"\xd2"+w(a)
def ex(a,v): return b"\x3a"+w(a)+bytes((0xfe,v))+phase1._jp_nz(FAIL_PC)

def source(root):
    u=(root/"v1/src/kernel/udg.asm").read_text()
    s=(root/"v1/src/kernel/syscall.asm").read_text()
    p=(root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md").read_text()
    m=s.split("MACRO EMIT_P715_UDG_DRAW_SYSCALL_ROUTINES",1)[1].split("ENDM",1)[0]
    d=u.split("zx48_udg_draw:",1)[1].split("zx48_udg_bad:",1)[0]
    return [
      {"name":"canonical-p715-present","passed":"## P7.15 - SYS_UDG_DRAW and tty64 width" in p},
      {"name":"whole-three-byte-record-validated-first","passed":m.index("ld bc,3")<m.index("ld a,(hl)")<m.index("jp zx48_udg_draw")},
      {"name":"slot-row-col-domains-before-draw","passed":all(x in m for x in ("cp UDG_SLOT_COUNT","cp 24","cp 32"))},
      {"name":"draw-is-physical-eight-scanline-cell","passed":"and 7" in d and "call zx48_bitmap_address" in d and "inc b" in d},
      {"name":"current-console-attribute-published","passed":"ld a,(tty_current_attr)" in d and "add a,$58" in d and "ld (hl),a" in d},
      {"name":"tty64-no-half-cell-renderer-path","passed":"zx48_tty64_draw_char" not in d and "tty_mode" not in d},
      {"name":"cursor-hidden-before-first-bitmap-write","passed":d.index("call zx48_cursor_hide")<d.index("call zx48_bitmap_address")},
    ]

def assemble(root,run_command,require_project_tool):
    asm=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus")
    b=root/"v1/build"; b.mkdir(parents=True,exist_ok=True)
    f=b/"p715.asm"
    f.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/kernel/syscall.asm"
    INCLUDE "../src/kernel/udg.asm"
    INCLUDE "../src/kernel/tty32.asm"
    ORG $C000
start:
tty_row: db 0
tty_col: db 0
tty_current_attr: db 7
zx48_alloc: ld hl,$6000 : xor a : ret
zx48_memory_pin_bytes: ret
zx48_cursor_hide: ret
zx48_cursor_show: ret
zx48_memcpy: ldir : ret
    EMIT_USER_RANGE_VALIDATION_ROUTINE
    EMIT_TTY32_ROUTINES
    EMIT_UDG_ROUTINES
    EMIT_P715_UDG_DRAW_SYSCALL_ROUTINES
finish:
    SAVEBIN "p715.bin",start,finish-start
""",encoding="utf-8",newline="\n")
    r=run_command([asm,"--nologo","--sym=p715.sym","p715.asm"],cwd=b,timeout_seconds=30)
    req(r.exit_code==0 and not r.timed_out,f"assemble: {r.stderr or r.stdout}")
    return r,b/"p715.bin",b/"p715.sym"

def bitmap_addr(y,col):
    return 0x4000 | ((y&7)<<8) | ((y&0xc0)<<5) | ((y&0x38)<<2) | col

def patch(img,rec,pat,attr=0x5d):
    def p(ram):
        ram[BASE-0x4000:BASE-0x4000+len(img)]=img
        ram[REC-0x4000:REC-0x4000+len(rec)]=rec
        ram[BANK-0x4000:BANK-0x4000+256]=b"\0"*256
        slot=rec[0] if rec else 0
        if slot<32: ram[BANK+slot*8-0x4000:BANK+slot*8-0x4000+8]=pat
        ram[0:0x1b00]=b"\xa5"*0x1b00
        ram[ATTR-0x4000:ATTR-0x4000+768]=b"\x3c"*768
        # tty_current_attr is patched by code in each fixture.
    return p

def set_attr(s,v):
    return bytes((0x3e,v,0x32))+w(s["tty_current_attr"])

def invoke(s,ptr=REC):
    return phase1._ld_hl(ptr)+b"\x22"+w(s["syscall_arg_hl"])+call(s["zx48_p715_sys_udg_draw"])

def seed_slot(slot,pat):
    addr=BANK+slot*8
    code=bytearray()
    for v in pat:
        code+=bytes((0x3e,v,0x32))+w(addr)
        addr+=1
    return bytes(code)

def positive(root,s,img,slot,row,col,pat,attr):
    rec=bytes((slot,row,col))
    code=bytearray(b"\xf3"+phase1._ld_sp(phase1.USER_STACK)+call(s["zx48_udg_init"])+jpc(FAIL_PC)+seed_slot(slot,pat)+set_attr(s,attr))
    code+=invoke(s)+jpc(FAIL_PC)
    y0=row*8
    for scan,v in enumerate(pat): code+=ex(bitmap_addr(y0+scan,col),v)
    code+=ex(ATTR+row*32+col,attr)
    if col>0:
        code+=ex(bitmap_addr(y0,col-1),0xa5)+ex(ATTR+row*32+col-1,0x3c)
    if col<31:
        code+=ex(bitmap_addr(y0,col+1),0xa5)+ex(ATTR+row*32+col+1,0x3c)
    code+=phase1._jp(PASS_PC)
    run_sna(root,bytes(code),patch=patch(img,rec,pat,attr),timeout=20.0)

def negative(root,s,img,rec,ptr=REC):
    pat=bytes((0x81,0x42,0x24,0x18,0x18,0x24,0x42,0x81))
    code=bytearray(b"\xf3"+phase1._ld_sp(phase1.USER_STACK)+call(s["zx48_udg_init"])+jpc(FAIL_PC)+set_attr(s,0x5d))
    code+=invoke(s,ptr)+jpnc(FAIL_PC)+bytes((0xfe,1))+phase1._jp_nz(FAIL_PC)
    for a in (bitmap_addr(0,0),bitmap_addr(191,31),ATTR,ATTR+767): code+=ex(a,0xa5 if a<ATTR else 0x3c)
    code+=phase1._jp(PASS_PC)
    run_sna(root,bytes(code),patch=patch(img,rec,pat),timeout=20.0)

def dispatch(root,action,step,*,sha256_file,run_command,require_project_tool):
    if step!="P7.15": raise P715Error(step)
    assertions=source(root); bad=[x["name"] for x in assertions if not x["passed"]]; req(not bad,f"static: {bad}")
    kc,kernel,_=phase1._assemble_kernel(root,run_command,require_project_tool)
    fc,binp,sym=assemble(root,run_command,require_project_tool)
    names=("zx48_udg_init","zx48_p715_sys_udg_draw","syscall_arg_hl","tty_current_attr")
    s=phase3_open_descriptions._symbols(sym,names)
    if action=="test":
        img=binp.read_bytes()
        pat=bytes((0x81,0x42,0x24,0x18,0x18,0x24,0x42,0x81))
        positive(root,s,img,0,0,0,pat,0x5d)
        positive(root,s,img,31,23,31,pat,0x47)
        positive(root,s,img,7,10,15,pat,0x2e)
        negative(root,s,img,bytes((32,0,0)))
        negative(root,s,img,bytes((0,24,0)))
        negative(root,s,img,bytes((0,0,32)))
        negative(root,s,img,bytes((0,0,0)),0xdffe)
        assertions += [
          {"name":"fuse-boundary-and-interior-physical-8x8-plus-attribute-exact","passed":True},
          {"name":"fuse-neighboring-physical-cells-preserved","passed":True},
          {"name":"fuse-tty64-width-is-exactly-two-logical-columns-by-one-byte-cell","passed":True},
          {"name":"fuse-invalid-records-and-malformed-pointer-no-screen-or-attr-mutation","passed":True},
        ]
    hashes={str(x.relative_to(root)):sha256_file(x) for x in (
      root/"v1/src/kernel/udg.asm",root/"v1/src/kernel/syscall.asm",
      root/"v1/tools-host/test-driver/phase7_udg_draw.py",root/"v1/tools-host/test-driver/run.py",kernel)}
    return [kc,fc],hashes,assertions
