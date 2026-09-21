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
E_INVAL=0x01

class P708Error(DriverError): pass

def require(v:bool,m:str)->None:
    if not v: raise P708Error(m)

def _word(v:int)->bytes: return bytes((v&255,(v>>8)&255))
def _setb(a:int,v:int)->bytes: return bytes((0x3e,v&255,0x32))+_word(a)
def _expectb(a:int,v:int)->bytes: return b"\x3a"+_word(a)+bytes((0xfe,v&255))+phase1._jp_nz(FAIL_PC)
def _jp_c(a:int)->bytes: return b"\xda"+_word(a)
def _jp_nc(a:int)->bytes: return b"\xd2"+_word(a)

def _source(root:Path):
    gfx=(root/"v1/src/kernel/graphics.asm").read_text(encoding="utf-8")
    ula=(root/"v1/src/kernel/ula_io.asm").read_text(encoding="utf-8")
    plan=(root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md").read_text(encoding="utf-8")
    kernel_files=sorted((root/"v1/src/kernel").glob("*.asm"))
    direct=[]
    for p in kernel_files:
        for i,line in enumerate(p.read_text(encoding="utf-8").splitlines(),1):
            s=line.split(";",1)[0].lower()
            if "out (ula_port)" in s or "out ($fe)" in s or "out (254)" in s:
                direct.append((p.name,i,s.strip()))
    start=gfx.index("zx48_gfx_border:"); end=gfx.index("zx48_gfx_bad:",start); b=gfx[start:end]
    return [
      {"name":"canonical-p708-present","passed":"## P7.08 - SYS_GFX_BORDER via central ULA shadow" in plan},
      {"name":"border-validates-reserved-h-and-color-before-commit","passed":b.index("or a")<b.index("call zx48_ula_set_border") and b.index("cp 8")<b.index("jp zx48_ula_set_border")},
      {"name":"border-delegates-only-to-central-ula-owner","passed":"call zx48_ula_set_border" in b and "out " not in b.lower()},
      {"name":"central-border-update-preserves-nonborder-shadow-bits","passed":"and $f8" in ula and "or b" in ula and "jr zx48_ula_commit" in ula},
      {"name":"single-production-ula-output-owner","passed":len(direct)==1 and direct[0][0]=="ula_io.asm"},
      {"name":"ula-shadow-and-port-committed-together","passed":"ld (ula_shadow),a\n    out (ULA_PORT),a" in ula},
      {"name":"p708-contract-comment-present","passed":"P7.08:" in gfx and "central ULA shadow" in gfx},
    ]

def _assemble(root:Path,run_command:Callable[...,Any],require_project_tool:Callable[[Path,str|Path],Path]):
    asm=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus")
    build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    src=build/"p708-border.asm"; binary=build/"p708-border.bin"; sym=build/"p708-border.sym"
    src.write_text(
      "    DEVICE ZXSPECTRUM48\n"
      "    INCLUDE \"../include/zx48ux.inc\"\n"
      f"    ORG ${MODULE:04X}\n"
      "p708_start:\n"
      "tty_current_attr: db 7\n"
      "altreg_busy: db 0\n"
      "zx48_cursor_hide: ret\n"
      "zx48_cursor_show: ret\n"
      "zx48_bitmap_address: ret\n"
      "    INCLUDE \"../src/kernel/syscall.asm\"\n"
      "    INCLUDE \"../src/kernel/ula_io.asm\"\n"
      "    EMIT_USER_RANGE_VALIDATION_ROUTINE\n"
      "    EMIT_ULA_ROUTINES\n"
      "    EMIT_GRAPHICS_ROUTINES\n"
      "    EMIT_P701_GRAPHICS_SYSCALL_ROUTINES\n"
      "p708_end:\n"
      "    SAVEBIN \"p708-border.bin\",p708_start,p708_end-p708_start\n",
      encoding="utf-8",newline="\n")
    r=run_command([asm,"--nologo","--lst=p708-border.lst","--sym=p708-border.sym","p708-border.asm"],cwd=build,timeout_seconds=30.0)
    require(not r.timed_out and r.exit_code==0,f"P7.08 fixture assembly failed: {r.stderr or r.stdout}")
    require(binary.is_file() and 0<binary.stat().st_size<8192,"P7.08 fixture missing/oversize")
    return r,binary,sym

def _border_call(s:dict[str,int],h:int,l:int)->bytes:
    return phase1._ld_hl(((h&255)<<8)|(l&255))+b"\x22"+_word(s["syscall_arg_hl"])+bytes((0x3e,s["SYS_GFX_BORDER"]&255))+phase1._call(s["zx48_p701_gfx_dispatch"])

def _runtime(root:Path,s:dict[str,int],module:bytes):
    code=bytearray(b"\xf3"+phase1._ld_sp(phase1.USER_STACK))
    for initial in (0x00,0x18,0xa8,0xf8):
        for color in range(8):
            code+=_setb(s["ula_shadow"],initial)
            code+=_border_call(s,0,color)+_jp_c(FAIL_PC)+b"\xb7"+phase1._jp_nz(FAIL_PC)
            code+=_expectb(s["ula_shadow"],(initial&0xf8)|color)

    code+=_setb(s["ula_shadow"],0xb8)
    for h,l in ((1,0),(255,7),(0,8),(0,255)):
        code+=_border_call(s,h,l)+_jp_nc(FAIL_PC)+bytes((0xfe,E_INVAL))+phase1._jp_nz(FAIL_PC)
        code+=_expectb(s["ula_shadow"],0xb8)
    code+=phase1._jp(PASS_PC)

    def patch(ram:bytearray):
        ram[MODULE-0x4000:MODULE-0x4000+len(module)]=module
    run_sna(root,bytes(code),patch=patch,timeout=20.0)

def dispatch(root:Path,action:str,step:str,*,sha256_file,run_command,require_project_tool):
    if step!="P7.08": raise P708Error(f"unsupported {step} {action}")
    assertions=_source(root); failed=[x["name"] for x in assertions if x.get("passed") is not True]
    require(not failed,f"P7.08 static failure: {failed}")
    kc,kernel,_=phase1._assemble_kernel(root,run_command,require_project_tool)
    fc,binary,sym=_assemble(root,run_command,require_project_tool)
    names=("zx48_p701_gfx_dispatch","syscall_arg_hl","SYS_GFX_BORDER","ula_shadow")
    symbols=phase3_open_descriptions._symbols(sym,names)
    if action=="test":
        _runtime(root,symbols,binary.read_bytes())
        assertions += [
          {"name":"fuse-all-border-colors-preserve-mic-beeper-and-other-shadow-bits","passed":True},
          {"name":"fuse-invalid-h-or-color-fails-before-central-shadow-mutation","passed":True},
        ]
    hashes={
      "v1/build/kernel.bin":sha256_file(kernel),
      "v1/build/p708-border.bin":sha256_file(binary),
      "v1/src/kernel/graphics.asm":sha256_file(root/"v1/src/kernel/graphics.asm"),
      "v1/src/kernel/ula_io.asm":sha256_file(root/"v1/src/kernel/ula_io.asm"),
      "v1/tools-host/test-driver/phase7_border.py":sha256_file(root/"v1/tools-host/test-driver/phase7_border.py"),
      "v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
    }
    return [kc,fc],hashes,assertions
