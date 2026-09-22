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
ARGS=0xA000
E_INVAL=1
E_NOTSUP=14

class P712Error(DriverError): pass
def require(v:bool,m:str)->None:
    if not v: raise P712Error(m)
def _word(v:int)->bytes: return bytes((v&255,(v>>8)&255))
def _jp_c(a:int)->bytes: return b"\xda"+_word(a)
def _jp_nc(a:int)->bytes: return b"\xd2"+_word(a)
def _expectb(a:int,v:int)->bytes: return b"\x3a"+_word(a)+bytes((0xfe,v&255))+phase1._jp_nz(FAIL_PC)

def _source(root:Path):
    sh=(root/"v1/src/shell/sh.asm").read_text(encoding="utf-8")
    plan=(root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md").read_text(encoding="utf-8")
    p=sh.split("MACRO EMIT_P712_GRAPHICS_BUILTIN_ROUTINES",1)[1].split("ENDM",1)[0]
    names=("plot","line","circle","point","ink","paper","bright","flash","inverse","over","border")
    selectors=("SYS_GFX_PLOT","SYS_GFX_DRAW","SYS_GFX_CIRCLE","SYS_GFX_POINT","SYS_GFX_ATTR","SYS_GFX_BORDER")
    return [
      {"name":"canonical-p712-present","passed":"## P7.12 - Graphics/attribute shell builtins" in plan},
      {"name":"all-exact-lowercase-builtins-present","passed":all("p712_name_"+n in p for n in names)},
      {"name":"all-kernel-graphics-selectors-wired","passed":all(s in p for s in selectors)},
      {"name":"foreground-single-stage-guard-before-handlers","passed":"cp 1\n    jr nz,sh_p712_notsup" in p and "ld a,c\n    or a\n    jr nz,sh_p712_notsup" in p},
      {"name":"draw-and-circle-copy-exact-record-sizes","passed":"ld bc,4\n    ldir" in p and "ld bc,3\n    ldir" in p},
      {"name":"attribute-selectors-zero-through-five","passed":all(f"ld d,{i}" in p for i in range(6))},
      {"name":"no-bcat-or-tape-path-in-builtin-wiring","passed":"bcat" not in p.lower() and "tape" not in p.lower()},
    ]

def _assemble(root:Path,run_command:Callable[...,Any],require_project_tool:Callable[[Path,str|Path],Path]):
    asm=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus")
    build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    src=build/"p712-shell-gfx.asm"; binary=build/"p712-shell-gfx.bin"; sym=build/"p712-shell-gfx.sym"
    src.write_text(
      "    DEVICE ZXSPECTRUM48\n"
      "    INCLUDE \"../include/zx48ux.inc\"\n"
      "    INCLUDE \"../src/shell/sh.asm\"\n"
      f"    ORG ${MODULE:04X}\n"
      "p712_start:\n"
      "    EMIT_P712_GRAPHICS_BUILTIN_ROUTINES\n"
      "p712_gateway:\n"
      "    ld (p712_last_selector),a\n"
      "    ld (p712_last_hl),hl\n"
      "    ld hl,p712_call_count\n"
      "    inc (hl)\n"
      "    xor a\n"
      "    ret\n"
      "p712_call_count: db 0\n"
      "p712_last_selector: db 0\n"
      "p712_last_hl: dw 0\n"
      "p712_end:\n"
      "    SAVEBIN \"p712-shell-gfx.bin\",p712_start,p712_end-p712_start\n",
      encoding="utf-8",newline="\n")
    r=run_command([asm,"--nologo","--lst=p712-shell-gfx.lst","--sym=p712-shell-gfx.sym","p712-shell-gfx.asm"],cwd=build,timeout_seconds=30.0)
    require(not r.timed_out and r.exit_code==0,f"P7.12 fixture assembly failed: {r.stderr or r.stdout}")
    require(binary.is_file() and 0<binary.stat().st_size<8192,"P7.12 fixture missing/oversize")
    return r,binary,sym

def _patch(module:bytes,args:bytes,gateway:int):
    def apply(ram:bytearray):
        ram[MODULE-0x4000:MODULE-0x4000+len(module)]=module
        ram[ARGS-0x4000:ARGS-0x4000+len(args)]=args
        off=0xE000-0x4000
        ram[off:off+3]=b"\xc3"+_word(gateway)
    return apply

def _invoke(addr:int,argc:int,stages:int=1,bg:int=0)->bytes:
    return bytes((0x3e,argc&255,0x06,stages&255,0x0e,bg&255))+phase1._ld_hl(ARGS)+phase1._call(addr)

def _ok(root,s,module,name,argc,args,selector,hl_value=None):
    code=bytearray(b"\xf3"+phase1._ld_sp(phase1.USER_STACK))
    code+=b"\xaf\x32"+_word(s["p712_call_count"])
    code+=_invoke(s[name],argc)+_jp_c(FAIL_PC)
    code+=_expectb(s["p712_call_count"],1)+_expectb(s["p712_last_selector"],selector)
    if hl_value is not None:
        code+=b"\x2a"+_word(s["p712_last_hl"])+phase1._ld_de(hl_value)+b"\xb7\xed\x52"+phase1._jp_nz(FAIL_PC)
    code+=phase1._jp(PASS_PC)
    run_sna(root,bytes(code),patch=_patch(module,args,s["p712_gateway"]),timeout=20.0)

def _reject(root,s,module,name,argc,args,errno,stages=1,bg=0):
    code=bytearray(b"\xf3"+phase1._ld_sp(phase1.USER_STACK))
    code+=b"\xaf\x32"+_word(s["p712_call_count"])
    code+=_invoke(s[name],argc,stages,bg)+_jp_nc(FAIL_PC)+bytes((0xfe,errno))+phase1._jp_nz(FAIL_PC)
    code+=_expectb(s["p712_call_count"],0)+phase1._jp(PASS_PC)
    run_sna(root,bytes(code),patch=_patch(module,args,s["p712_gateway"]),timeout=20.0)

def dispatch(root:Path,action:str,step:str,*,sha256_file,run_command,require_project_tool):
    if step!="P7.12": raise P712Error(f"unsupported {step} {action}")
    assertions=_source(root); require(all(x["passed"] for x in assertions),"P7.12 static failure")
    kc,kernel,_=phase1._assemble_kernel(root,run_command,require_project_tool)
    fc,binary,sym=_assemble(root,run_command,require_project_tool)
    names=("p712_gateway","p712_call_count","p712_last_selector","p712_last_hl","p712_line_req","p712_circle_req",
           "sh_p712_plot","sh_p712_line","sh_p712_circle","sh_p712_point","sh_p712_ink","sh_p712_paper",
           "sh_p712_bright","sh_p712_flash","sh_p712_inverse","sh_p712_over","sh_p712_border")
    s=phase3_open_descriptions._symbols(sym,names)
    if action=="test":
        m=binary.read_bytes()
        _ok(root,s,m,"sh_p712_plot",3,bytes((10,20)),0x40,(10<<8)|20)
        _ok(root,s,m,"sh_p712_point",3,bytes((30,40)),0x45,(30<<8)|40)
        _ok(root,s,m,"sh_p712_line",5,bytes((1,2,3,4)),0x41,s["p712_line_req"])
        _ok(root,s,m,"sh_p712_circle",4,bytes((5,6,7)),0x42,s["p712_circle_req"])
        for name,sel in (("sh_p712_ink",0),("sh_p712_paper",1),("sh_p712_bright",2),("sh_p712_flash",3),("sh_p712_inverse",4),("sh_p712_over",5)):
            _ok(root,s,m,name,2,bytes((1,)),0x43,(sel<<8)|1)
        _ok(root,s,m,"sh_p712_border",2,bytes((7,)),0x44,7)
        _reject(root,s,m,"sh_p712_plot",2,bytes((1,2)),E_INVAL)
        _reject(root,s,m,"sh_p712_plot",3,bytes((1,2)),E_NOTSUP,stages=2)
        _reject(root,s,m,"sh_p712_border",2,bytes((1,)),E_NOTSUP,bg=1)
        assertions += [
          {"name":"fuse-all-graphics-and-attribute-builtins-reach-exact-kernel-selectors","passed":True},
          {"name":"fuse-line-circle-record-pointers-and-coordinate-registers-exact","passed":True},
          {"name":"fuse-pipeline-background-and-bad-arity-fail-before-syscall","passed":True},
        ]
    hashes={
      "v1/build/kernel.bin":sha256_file(kernel),
      "v1/build/p712-shell-gfx.bin":sha256_file(binary),
      "v1/src/shell/sh.asm":sha256_file(root/"v1/src/shell/sh.asm"),
      "v1/tools-host/test-driver/phase7_shell_graphics.py":sha256_file(root/"v1/tools-host/test-driver/phase7_shell_graphics.py"),
      "v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
    }
    return [kc,fc],hashes,assertions
