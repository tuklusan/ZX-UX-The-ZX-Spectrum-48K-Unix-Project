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
MIRROR=0x6000
DISPLAY_BYTES=0x1B00
E_INVAL=0x01

class P706Error(DriverError): pass

def require(v:bool,m:str)->None:
    if not v: raise P706Error(m)

def _word(v:int)->bytes: return bytes((v&255,(v>>8)&255))
def _jp_c(a:int)->bytes: return b"\xda"+_word(a)
def _jp_nc(a:int)->bytes: return b"\xd2"+_word(a)
def _addr(x:int,y:int)->int:
    return 0x4000 | ((y&0xc0)<<5) | ((y&7)<<8) | ((y&0x38)<<2) | (x>>3)

def _source(root:Path):
    gfx=(root/"v1/src/kernel/graphics.asm").read_text(encoding="utf-8")
    plan=(root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md").read_text(encoding="utf-8")
    start=gfx.index("zx48_gfx_point:"); end=gfx.index("; H=x,L=y -> bitmap HL",start); point=gfx[start:end]
    return [
      {"name":"canonical-p706-present","passed":"## P7.06 - SYS_GFX_POINT" in plan},
      {"name":"point-validates-y-before-bitmap-access","passed":point.index("cp 192")<point.index("call zx48_gfx_pixel_addr")},
      {"name":"point-returns-only-zero-or-one","passed":"ld hl,1" in point and "ld hl,0" in point},
      {"name":"point-success-canonical-zero-carry-clear","passed":point.count("xor a\n    or a\n    ret")==2},
      {"name":"point-does-not-call-cursor-or-write-display","passed":"cursor_" not in point and "ld (hl),a" not in point},
      {"name":"point-uses-p702-canonical-address-path","passed":"call zx48_gfx_pixel_addr" in point and "call zx48_bitmap_address" in gfx},
      {"name":"p706-contract-comment-present","passed":"P7.06:" in gfx and "no visible/cursor/attribute mutation" in gfx},
    ]

def _assemble(root:Path,run_command:Callable[...,Any],require_project_tool:Callable[[Path,str|Path],Path]):
    asm=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus")
    build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    src=build/"p706-point.asm"; binary=build/"p706-point.bin"; sym=build/"p706-point.sym"
    src.write_text(
      "    DEVICE ZXSPECTRUM48\n"
      "    INCLUDE \"../include/zx48ux.inc\"\n"
      f"    ORG ${MODULE:04X}\n"
      "p706_start:\n"
      "tty_current_attr: db 7\n"
      "p706_hide_count: db 0\n"
      "p706_show_count: db 0\n"
      "zx48_cursor_hide: ld a,(p706_hide_count) : inc a : ld (p706_hide_count),a : ret\n"
      "zx48_cursor_show: ld a,(p706_show_count) : inc a : ld (p706_show_count),a : ret\n"
      "zx48_ula_set_border: xor a : ret\n"
      "zx48_bitmap_address:\n"
      "    ld a,b\n    and 7\n    or $40\n    ld h,a\n"
      "    ld a,b\n    and $c0\n    rrca\n    rrca\n    rrca\n    or h\n    ld h,a\n"
      "    ld a,b\n    and $38\n    rlca\n    rlca\n    or c\n    ld l,a\n    ret\n"
      "    INCLUDE \"../src/kernel/syscall.asm\"\n"
      "    EMIT_GRAPHICS_ROUTINES\n"
      "    EMIT_P701_GRAPHICS_SYSCALL_ROUTINES\n"
      "p706_end:\n"
      "    SAVEBIN \"p706-point.bin\",p706_start,p706_end-p706_start\n",
      encoding="utf-8",newline="\n")
    r=run_command([asm,"--nologo","--lst=p706-point.lst","--sym=p706-point.sym","p706-point.asm"],cwd=build,timeout_seconds=30.0)
    require(not r.timed_out and r.exit_code==0,f"P7.06 fixture assembly failed: {r.stderr or r.stdout}")
    require(binary.is_file() and 0<binary.stat().st_size<8192,"P7.06 fixture missing/oversize")
    return r,binary,sym

def _compare(code:bytearray):
    code+=phase1._ld_hl(0x4000)+phase1._ld_de(MIRROR)+b"\x01"+_word(DISPLAY_BYTES)
    loop=0x9000+len(code)
    code+=b"\x1a\xbe"+phase1._jp_nz(FAIL_PC)+b"\x23\x13\x0b\x78\xb1"+phase1._jp_nz(loop)

def _runtime(root:Path,s:dict[str,int],module:bytes):
    pattern=bytes(((i*37+11)&255) for i in range(DISPLAY_BYTES))
    vectors=((0,0),(255,0),(0,191),(255,191),(37,88),(128,96))
    code=bytearray(b"\xf3"+phase1._ld_sp(phase1.USER_STACK))
    for i in range(6): code+=bytes((0x3e,0x40+i,0x32))+_word(s["gfx_attr_state"]+i)
    for x,y in vectors:
        expected=1 if pattern[_addr(x,y)-0x4000]&(0x80>>(x&7)) else 0
        code+=phase1._ld_hl(((x&255)<<8)|(y&255))+b"\x22"+_word(s["syscall_arg_hl"])
        code+=bytes((0x3e,s["SYS_GFX_POINT"]&255))+phase1._call(s["zx48_p701_gfx_dispatch"])
        code+=_jp_c(FAIL_PC)+b"\xb7"+phase1._jp_nz(FAIL_PC)
        code+=b"\x7c\xb7"+phase1._jp_nz(FAIL_PC)
        code+=b"\x7d"+bytes((0xfe,expected))+phase1._jp_nz(FAIL_PC)
    for y in (192,255):
        code+=phase1._ld_hl((99<<8)|y)+b"\x22"+_word(s["syscall_arg_hl"])
        code+=bytes((0x3e,s["SYS_GFX_POINT"]&255))+phase1._call(s["zx48_p701_gfx_dispatch"])
        code+=_jp_nc(FAIL_PC)+bytes((0xfe,E_INVAL))+phase1._jp_nz(FAIL_PC)
    code+=b"\x3a"+_word(s["p706_hide_count"])+b"\xb7"+phase1._jp_nz(FAIL_PC)
    code+=b"\x3a"+_word(s["p706_show_count"])+b"\xb7"+phase1._jp_nz(FAIL_PC)
    for i in range(6):
        code+=b"\x3a"+_word(s["gfx_attr_state"]+i)+bytes((0xfe,0x40+i))+phase1._jp_nz(FAIL_PC)
    _compare(code); code+=phase1._jp(PASS_PC)
    def patch(ram:bytearray):
        ram[MODULE-0x4000:MODULE-0x4000+len(module)]=module
        ram[0:DISPLAY_BYTES]=pattern
        ram[MIRROR-0x4000:MIRROR-0x4000+DISPLAY_BYTES]=pattern
    run_sna(root,bytes(code),patch=patch,timeout=20.0)

def dispatch(root:Path,action:str,step:str,*,sha256_file,run_command,require_project_tool):
    if step!="P7.06": raise P706Error(f"unsupported {step} {action}")
    assertions=_source(root); failed=[x["name"] for x in assertions if x.get("passed") is not True]
    require(not failed,f"P7.06 static failure: {failed}")
    kc,kernel,_=phase1._assemble_kernel(root,run_command,require_project_tool)
    fc,binary,sym=_assemble(root,run_command,require_project_tool)
    names=("zx48_p701_gfx_dispatch","syscall_arg_hl","SYS_GFX_POINT","gfx_attr_state","p706_hide_count","p706_show_count")
    symbols=phase3_open_descriptions._symbols(sym,names)
    if action=="test":
        _runtime(root,symbols,binary.read_bytes())
        assertions += [
          {"name":"fuse-corners-and-interiors-return-exact-zero-one","passed":True},
          {"name":"fuse-whole-display-cursor-and-graphics-state-byte-identical","passed":True},
          {"name":"fuse-y192-y255-return-einval-without-side-effects","passed":True},
        ]
    hashes={
      "v1/build/kernel.bin":sha256_file(kernel),
      "v1/build/p706-point.bin":sha256_file(binary),
      "v1/src/kernel/graphics.asm":sha256_file(root/"v1/src/kernel/graphics.asm"),
      "v1/src/kernel/syscall.asm":sha256_file(root/"v1/src/kernel/syscall.asm"),
      "v1/tools-host/test-driver/phase7_point.py":sha256_file(root/"v1/tools-host/test-driver/phase7_point.py"),
      "v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
    }
    return [kc,fc],hashes,assertions
