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
from pathlib import Path
from typing import Any, Callable
from driver_core import DriverError
from fuse_harness import FAIL_PC, PASS_PC, run_sna
import phase1
import phase3_open_descriptions

MODULE=0xC000
DATA=0xA000
MIRROR=0x6000
DISPLAY_BYTES=0x1B00
E_INVAL=0x01

class P705Error(DriverError): pass

def require(v:bool,m:str)->None:
    if not v: raise P705Error(m)

def _word(v:int)->bytes: return bytes((v&255,(v>>8)&255))
def _setb(a:int,v:int)->bytes: return bytes((0x3e,v&255,0x32))+_word(a)
def _jp_c(a:int)->bytes: return b"\xda"+_word(a)
def _jp_nc(a:int)->bytes: return b"\xd2"+_word(a)

def _addr(x:int,y:int)->int:
    return 0x4000 | ((y&0xc0)<<5) | ((y&7)<<8) | ((y&0x38)<<2) | (x>>3)

def _attr(x:int,y:int)->int: return 0x5800+(y>>3)*32+(x>>3)

def _circle(cx:int,cy:int,r:int)->set[tuple[int,int]]:
    if r==0: return {(cx,cy)}
    out:set[tuple[int,int]]=set()
    x=r; y=0; err=1-r
    while True:
        for px,py in ((cx+x,cy+y),(cx+y,cy+x),(cx-y,cy+x),(cx-x,cy+y),
                      (cx-x,cy-y),(cx-y,cy-x),(cx+y,cy-x),(cx+x,cy-y)):
            if 0<=px<=255 and 0<=py<=191: out.add((px,py))
        if y>=x: return out
        y+=1
        if err<0:
            err += 2*y+1
        else:
            x-=1
            err += 2*(y-x)+1

def _display(points:set[tuple[int,int]],attr:int)->bytes:
    d=bytearray(DISPLAY_BYTES)
    for x,y in points:
        d[_addr(x,y)-0x4000] |= 0x80>>(x&7)
        d[_attr(x,y)-0x4000] = attr
    return bytes(d)

def _source(root:Path):
    gfx=(root/"v1/src/kernel/graphics.asm").read_text(encoding="utf-8")
    syscall=(root/"v1/src/kernel/syscall.asm").read_text(encoding="utf-8")
    plan=(root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md").read_text(encoding="utf-8")
    start=gfx.index("zx48_gfx_circle:"); end=gfx.index("; H=selector,L=value.",start); c=gfx[start:end]
    return [
      {"name":"canonical-p705-present","passed":"## P7.05 - SYS_GFX_CIRCLE" in plan},
      {"name":"circle-validates-center-y-before-scratch","passed":c.index("cp 192")<c.index("ld (gfx_cx),a")},
      {"name":"radius-zero-plots-center-once","passed":"or a\n    jr nz,zx48_gfx_circle_init" in c and "jp zx48_gfx_plot" in c},
      {"name":"circle-uses-16-bit-midpoint-decision","passed":"ld (gfx_circle_d),hl" in c and "gfx_circle_d: dw 0" in gfx},
      {"name":"circle-clipping-checks-x-carry-borrow-and-y-domain","passed":all(t in c for t in ("jr c,zx48_gfx_circle_pp_done","jr nc,zx48_gfx_circle_pp_done","ret c"))},
      {"name":"circle-deduplicates-axis-and-diagonal-symmetry","passed":"zx48_gfx_circle_axis:" in c and "zx48_gfx_circle_diag:" in c},
      {"name":"native-fallback-rationale-recorded","passed":"ROM graphics path inherits BASIC's y<=175/origin" in gfx},
      {"name":"syscall-validates-complete-three-byte-record","passed":"ld bc,3\n    call zx48_user_range_validate" in syscall},
    ]

def _assemble(root:Path,run_command:Callable[...,Any],require_project_tool:Callable[[Path,str|Path],Path]):
    asm=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus")
    build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    src=build/"p705-circle.asm"; binary=build/"p705-circle.bin"; sym=build/"p705-circle.sym"
    src.write_text(
      "    DEVICE ZXSPECTRUM48\n"
      "    INCLUDE \"../include/zx48ux.inc\"\n"
      f"    ORG ${MODULE:04X}\n"
      "p705_start:\n"
      "tty_current_attr: db 7\n"
      "zx48_cursor_hide: ret\n"
      "zx48_cursor_show: ret\n"
      "zx48_ula_set_border: xor a : ret\n"
      "zx48_bitmap_address:\n"
      "    ld a,b\n    and 7\n    or $40\n    ld h,a\n"
      "    ld a,b\n    and $c0\n    rrca\n    rrca\n    rrca\n    or h\n    ld h,a\n"
      "    ld a,b\n    and $38\n    rlca\n    rlca\n    or c\n    ld l,a\n    ret\n"
      "    INCLUDE \"../src/kernel/syscall.asm\"\n"
      "    EMIT_USER_RANGE_VALIDATION_ROUTINE\n"
      "    EMIT_GRAPHICS_ROUTINES\n"
      "    EMIT_P701_GRAPHICS_SYSCALL_ROUTINES\n"
      "p705_end:\n"
      "    SAVEBIN \"p705-circle.bin\",p705_start,p705_end-p705_start\n",
      encoding="utf-8",newline="\n")
    r=run_command([asm,"--nologo","--lst=p705-circle.lst","--sym=p705-circle.sym","p705-circle.asm"],cwd=build,timeout_seconds=30.0)
    require(not r.timed_out and r.exit_code==0,f"P7.05 fixture assembly failed: {r.stderr or r.stdout}")
    require(binary.is_file() and 0<binary.stat().st_size<8192,"P7.05 fixture missing/oversize")
    return r,binary,sym

def _patch(module:bytes,record:bytes,expected:bytes):
    def apply(ram:bytearray):
        ram[MODULE-0x4000:MODULE-0x4000+len(module)]=module
        ram[DATA-0x4000:DATA-0x4000+len(record)]=record
        ram[MIRROR-0x4000:MIRROR-0x4000+len(expected)]=expected
    return apply

def _compare(code:bytearray):
    code+=phase1._ld_hl(0x4000)+phase1._ld_de(MIRROR)+b"\x01"+_word(DISPLAY_BYTES)
    loop=0x9000+len(code)
    code+=b"\x1a\xbe"+phase1._jp_nz(FAIL_PC)+b"\x23\x13\x0b\x78\xb1"+phase1._jp_nz(loop)

def _run(root:Path,s:dict[str,int],module:bytes,v:tuple[int,int,int]):
    attr=0x47; expected=_display(_circle(*v),attr)
    code=bytearray(b"\xf3"+phase1._ld_sp(phase1.USER_STACK))
    code+=_setb(s["tty_current_attr"],attr)+_setb(s["gfx_attr_state"]+4,0)+_setb(s["gfx_attr_state"]+5,0)
    code+=phase1._ld_hl(DATA)+b"\x22"+_word(s["syscall_arg_hl"])
    code+=bytes((0x3e,s["SYS_GFX_CIRCLE"]&255))+phase1._call(s["zx48_p701_gfx_dispatch"])
    code+=_jp_c(FAIL_PC)+b"\xb7"+phase1._jp_nz(FAIL_PC)
    _compare(code); code+=phase1._jp(PASS_PC)
    run_sna(root,bytes(code),patch=_patch(module,bytes(v),expected),timeout=20.0)

def _negative(root:Path,s:dict[str,int],module:bytes):
    expected=bytes(DISPLAY_BYTES); record=bytes((17,192,9))
    code=bytearray(b"\xf3"+phase1._ld_sp(phase1.USER_STACK))
    for i,n in enumerate(("gfx_cx","gfx_cy","gfx_r","gfx_circle_x","gfx_circle_y")): code+=_setb(s[n],0xa0+i)
    code+=phase1._ld_hl(DATA)+b"\x22"+_word(s["syscall_arg_hl"])
    code+=bytes((0x3e,s["SYS_GFX_CIRCLE"]&255))+phase1._call(s["zx48_p701_gfx_dispatch"])
    code+=_jp_nc(FAIL_PC)+bytes((0xfe,E_INVAL))+phase1._jp_nz(FAIL_PC)
    for i,n in enumerate(("gfx_cx","gfx_cy","gfx_r","gfx_circle_x","gfx_circle_y")):
        code+=b"\x3a"+_word(s[n])+bytes((0xfe,0xa0+i))+phase1._jp_nz(FAIL_PC)
    _compare(code)
    code+=phase1._ld_hl(0xdffe)+b"\x22"+_word(s["syscall_arg_hl"])
    code+=bytes((0x3e,s["SYS_GFX_CIRCLE"]&255))+phase1._call(s["zx48_p701_gfx_dispatch"])
    code+=_jp_nc(FAIL_PC)+bytes((0xfe,E_INVAL))+phase1._jp_nz(FAIL_PC)
    _compare(code); code+=phase1._jp(PASS_PC)
    run_sna(root,bytes(code),patch=_patch(module,record,expected),timeout=20.0)

def dispatch(root:Path,action:str,step:str,*,sha256_file,run_command,require_project_tool):
    if step!="P7.05": raise P705Error(f"unsupported {step} {action}")
    assertions=_source(root); failed=[x["name"] for x in assertions if x.get("passed") is not True]
    require(not failed,f"P7.05 static failure: {failed}")
    kc,kernel,_=phase1._assemble_kernel(root,run_command,require_project_tool)
    fc,binary,sym=_assemble(root,run_command,require_project_tool)
    names=("zx48_p701_gfx_dispatch","syscall_arg_hl","SYS_GFX_CIRCLE","tty_current_attr","gfx_attr_state",
           "gfx_cx","gfx_cy","gfx_r","gfx_circle_x","gfx_circle_y")
    symbols=phase3_open_descriptions._symbols(sym,names)
    if action=="test":
        module=binary.read_bytes()
        for v in ((17,19,0),(80,80,5),(0,0,12),(255,191,12),(128,96,64),(0,191,255)):
            _run(root,symbols,module,v)
        _negative(root,symbols,module)
        assertions += [
          {"name":"fuse-radius-zero-visible-and-clipped-circles-match-independent-oracle","passed":True},
          {"name":"fuse-radius-255-domain-vector-clips-not-rejects","passed":True},
          {"name":"fuse-invalid-center-and-malformed-pointer-fail-before-mutation","passed":True},
        ]
    hashes={
      "v1/build/kernel.bin":sha256_file(kernel),
      "v1/build/p705-circle.bin":sha256_file(binary),
      "v1/src/kernel/graphics.asm":sha256_file(root/"v1/src/kernel/graphics.asm"),
      "v1/src/kernel/syscall.asm":sha256_file(root/"v1/src/kernel/syscall.asm"),
      "v1/tools-host/test-driver/phase7_circle.py":sha256_file(root/"v1/tools-host/test-driver/phase7_circle.py"),
      "v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
    }
    return [kc,fc],hashes,assertions
