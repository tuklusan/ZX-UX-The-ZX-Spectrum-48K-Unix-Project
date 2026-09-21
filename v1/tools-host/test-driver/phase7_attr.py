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
FONT=0xA000
E_INVAL=0x01

class P707Error(DriverError): pass

def require(v:bool,m:str)->None:
    if not v: raise P707Error(m)

def _word(v:int)->bytes: return bytes((v&255,(v>>8)&255))
def _setb(a:int,v:int)->bytes: return bytes((0x3e,v&255,0x32))+_word(a)
def _expectb(a:int,v:int)->bytes: return b"\x3a"+_word(a)+bytes((0xfe,v&255))+phase1._jp_nz(FAIL_PC)
def _jp_c(a:int)->bytes: return b"\xda"+_word(a)
def _jp_nc(a:int)->bytes: return b"\xd2"+_word(a)

def _source(root:Path):
    gfx=(root/"v1/src/kernel/graphics.asm").read_text(encoding="utf-8")
    tty64=(root/"v1/src/kernel/tty64.asm").read_text(encoding="utf-8")
    plan=(root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md").read_text(encoding="utf-8")
    start=gfx.index("zx48_gfx_attr:"); end=gfx.index("; H=0,L=color.",start); a=gfx[start:end]
    return [
      {"name":"canonical-p707-present","passed":"## P7.07 - SYS_GFX_ATTR state API" in plan},
      {"name":"selectors-zero-through-five-only","passed":"cp 6" in a and "jp nc,zx48_gfx_bad" in a},
      {"name":"ink-paper-native-domain-zero-through-seven","passed":"cp 8" in a},
      {"name":"bright-flash-inverse-over-domain-zero-one","passed":"cp 2" in a},
      {"name":"validation-precedes-state-commit","passed":a.index("cp 2")<a.index("ld hl,gfx_attr_state")},
      {"name":"hardware-attribute-pack-is-ink-paper-bright-flash","passed":all(t in a for t in ("and 7","rlca","or $40","or $80","ld (tty_current_attr),a"))},
      {"name":"tty64-adjacent-columns-share-one-hardware-cell","passed":"srl a" in tty64 and "ld a,(tty_current_attr)" in tty64},
      {"name":"shared-console-graphics-contract-recorded","passed":"P7.07 shared console/graphics state" in gfx},
    ]

def _assemble(root:Path,run_command:Callable[...,Any],require_project_tool:Callable[[Path,str|Path],Path]):
    asm=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus")
    build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    src=build/"p707-attr.asm"; binary=build/"p707-attr.bin"; sym=build/"p707-attr.sym"
    src.write_text(
      "    DEVICE ZXSPECTRUM48\n"
      "    INCLUDE \"../include/zx48ux.inc\"\n"
      f"    ORG ${MODULE:04X}\n"
      "p707_start:\n"
      "tty_row: db 0\n"
      "tty_col: db 0\n"
      "tty_mode: db 64\n"
      "zx48_alloc: scf : ret\n"
      "zx48_memcpy: ret\n"
      "zx48_memory_pin_bytes: xor a : ret\n"
      "zx48_cursor_hide: ret\n"
      "zx48_cursor_show: ret\n"
      "zx48_ula_set_border: xor a : ret\n"
      "zx48_bitmap_address:\n"
      "    ld a,b\n    and 7\n    or $40\n    ld h,a\n"
      "    ld a,b\n    and $c0\n    rrca\n    rrca\n    rrca\n    or h\n    ld h,a\n"
      "    ld a,b\n    and $38\n    rlca\n    rlca\n    or c\n    ld l,a\n    ret\n"
      "    INCLUDE \"../src/kernel/syscall.asm\"\n"
      "    INCLUDE \"../src/kernel/tty64.asm\"\n"
      "    EMIT_USER_RANGE_VALIDATION_ROUTINE\n"
      "    EMIT_GRAPHICS_ROUTINES\n"
      "    EMIT_P701_GRAPHICS_SYSCALL_ROUTINES\n"
      "    EMIT_TTY64_ROUTINES\n"
      "p707_end:\n"
      "    SAVEBIN \"p707-attr.bin\",p707_start,p707_end-p707_start\n",
      encoding="utf-8",newline="\n")
    r=run_command([asm,"--nologo","--lst=p707-attr.lst","--sym=p707-attr.sym","p707-attr.asm"],cwd=build,timeout_seconds=30.0)
    require(not r.timed_out and r.exit_code==0,f"P7.07 fixture assembly failed: {r.stderr or r.stdout}")
    require(binary.is_file() and 0<binary.stat().st_size<8192,"P7.07 fixture missing/oversize")
    return r,binary,sym

def _attr_call(s:dict[str,int],selector:int,value:int)->bytes:
    return phase1._ld_hl(((selector&255)<<8)|(value&255))+b"\x22"+_word(s["syscall_arg_hl"])+bytes((0x3e,s["SYS_GFX_ATTR"]&255))+phase1._call(s["zx48_p701_gfx_dispatch"])

def _runtime(root:Path,s:dict[str,int],module:bytes):
    code=bytearray(b"\xf3"+phase1._ld_sp(phase1.USER_STACK))

    # Every legal native value round-trips into shared state and exact hardware byte.
    for v in range(8):
        code+=_attr_call(s,0,v)+_jp_c(FAIL_PC)+_expectb(s["gfx_attr_state"],v)
        code+=_expectb(s["tty_current_attr"],v)
    for v in range(8):
        code+=_attr_call(s,1,v)+_jp_c(FAIL_PC)+_expectb(s["gfx_attr_state"]+1,v)
        code+=_expectb(s["tty_current_attr"],(v<<3)|7)
    for selector,offset,bit in ((2,2,0x40),(3,3,0x80)):
        code+=_attr_call(s,selector,0)+_jp_c(FAIL_PC)+_expectb(s["gfx_attr_state"]+offset,0)
        code+=_attr_call(s,selector,1)+_jp_c(FAIL_PC)+_expectb(s["gfx_attr_state"]+offset,1)
        expected=0xff if selector==3 else 0x7f
        code+=_expectb(s["tty_current_attr"],expected)
    for selector,offset in ((4,4),(5,5)):
        before=0xff
        code+=_attr_call(s,selector,0)+_jp_c(FAIL_PC)+_expectb(s["gfx_attr_state"]+offset,0)+_expectb(s["tty_current_attr"],before)
        code+=_attr_call(s,selector,1)+_jp_c(FAIL_PC)+_expectb(s["gfx_attr_state"]+offset,1)+_expectb(s["tty_current_attr"],before)

    # Invalid selector/value cannot alter any public graphics state.
    for i in range(6): code+=_setb(s["gfx_attr_state"]+i,0x20+i)
    code+=_setb(s["tty_current_attr"],0xa5)
    for selector,value in ((0,8),(1,8),(2,2),(3,2),(4,2),(5,2),(6,0),(255,0)):
        code+=_attr_call(s,selector,value)+_jp_nc(FAIL_PC)+bytes((0xfe,E_INVAL))+phase1._jp_nz(FAIL_PC)
        for i in range(6): code+=_expectb(s["gfx_attr_state"]+i,0x20+i)
        code+=_expectb(s["tty_current_attr"],0xa5)

    # tty64 logical columns 10 and 11 publish into exactly the same physical attr cell.
    code+=phase1._ld_hl(FONT)+b"\x22"+_word(s["tty64_font_ptr"])
    code+=_setb(s["tty_row"],2)+_setb(s["tty_col"],10)+_setb(s["tty_current_attr"],0x12)
    code+=bytes((0x3e,0x20))+phase1._call(s["zx48_tty64_draw_char"])+_jp_c(FAIL_PC)
    cell=0x5800+2*32+5
    code+=_expectb(cell,0x12)+_expectb(cell-1,0x00)+_expectb(cell+1,0x00)
    code+=_setb(s["tty_col"],11)+_setb(s["tty_current_attr"],0x6d)
    code+=bytes((0x3e,0x20))+phase1._call(s["zx48_tty64_draw_char"])+_jp_c(FAIL_PC)
    code+=_expectb(cell,0x6d)+_expectb(cell-1,0x00)+_expectb(cell+1,0x00)
    code+=phase1._jp(PASS_PC)

    def patch(ram:bytearray):
        ram[MODULE-0x4000:MODULE-0x4000+len(module)]=module
        ram[FONT-0x4000:FONT-0x4000+4]=bytes((0xf0,0x0f,0xa5,0x5a))
    run_sna(root,bytes(code),patch=patch,timeout=20.0)

def dispatch(root:Path,action:str,step:str,*,sha256_file,run_command,require_project_tool):
    if step!="P7.07": raise P707Error(f"unsupported {step} {action}")
    assertions=_source(root); failed=[x["name"] for x in assertions if x.get("passed") is not True]
    require(not failed,f"P7.07 static failure: {failed}")
    kc,kernel,_=phase1._assemble_kernel(root,run_command,require_project_tool)
    fc,binary,sym=_assemble(root,run_command,require_project_tool)
    names=("zx48_p701_gfx_dispatch","syscall_arg_hl","SYS_GFX_ATTR","gfx_attr_state","tty_current_attr",
           "tty64_font_ptr","zx48_tty64_draw_char","tty_row","tty_col")
    symbols=phase3_open_descriptions._symbols(sym,names)
    if action=="test":
        _runtime(root,symbols,binary.read_bytes())
        assertions += [
          {"name":"fuse-all-native-attr-values-publish-exact-shared-state","passed":True},
          {"name":"fuse-invalid-selector-values-fail-before-state-mutation","passed":True},
          {"name":"fuse-tty64-logical-column-pair-shares-exact-one-hardware-attribute-cell","passed":True},
        ]
    hashes={
      "v1/build/kernel.bin":sha256_file(kernel),
      "v1/build/p707-attr.bin":sha256_file(binary),
      "v1/src/kernel/graphics.asm":sha256_file(root/"v1/src/kernel/graphics.asm"),
      "v1/src/kernel/tty64.asm":sha256_file(root/"v1/src/kernel/tty64.asm"),
      "v1/tools-host/test-driver/phase7_attr.py":sha256_file(root/"v1/tools-host/test-driver/phase7_attr.py"),
      "v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
    }
    return [kc,fc],hashes,assertions
