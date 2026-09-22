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
REQ=0xA000
OUT=0xA100
E_INVAL=0x01
E_NOTSUP=0x0E
E_NOENT=0x02
CATS={0:"ALL",1:"KEYBOARD",2:"CONSOLE",3:"TAPE",4:"GRAPHICS",5:"SOUND",6:"MATH"}

class P711Error(DriverError): pass
def require(v:bool,m:str)->None:
    if not v: raise P711Error(m)
def _word(v:int)->bytes: return bytes((v&255,(v>>8)&255))
def _jp_c(a:int)->bytes: return b"\xda"+_word(a)
def _jp_nc(a:int)->bytes: return b"\xd2"+_word(a)
def _expectb(a:int,v:int)->bytes: return b"\x3a"+_word(a)+bytes((0xfe,v&255))+phase1._jp_nz(FAIL_PC)

def _source(root:Path):
    rom=(root/"v1/src/kernel/rom_services.asm").read_text(encoding="utf-8")
    syscall=(root/"v1/src/kernel/syscall.asm").read_text(encoding="utf-8")
    sh=(root/"v1/src/shell/sh.asm").read_text(encoding="utf-8")
    plan=(root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md").read_text(encoding="utf-8")
    p=rom.split("MACRO EMIT_P711_ROM_INFO_ROUTINES",1)[1].split("ENDM",1)[0]
    s=syscall.split("MACRO EMIT_P711_ROM_INFO_SYSCALL_ROUTINES",1)[1].split("ENDM",1)[0]
    return [
      {"name":"canonical-p711-present","passed":"## P7.11 - SYS_ROM_INFO diagnostic gateway / rom builtin" in plan},
      {"name":"romq1-complete-four-byte-validation-first","passed":s.index("ld bc,4")<s.index("ld a,(hl)")},
      {"name":"romout1-complete-24-byte-validation-before-lookup","passed":s.index("ld bc,24")<s.index("jp zx48_rom_info_lookup")},
      {"name":"category-domain-zero-through-six","passed":"cp 7" in s and "cp 7" in p},
      {"name":"fixed-record-layout-size-24","passed":"ROMINFO_RECORD_SIZE      EQU 24" in rom and "defs 16-nameLen,0" in rom},
      {"name":"all-three-classifications-present","passed":all(x in p for x in ("ROMINFO_CLASS_A","ROMINFO_CLASS_B","ROMINFO_CLASS_C"))},
      {"name":"all-contract-flag-bits-defined","passed":all(x in rom for x in ("ROMINFO_FLAG_ERROR","ROMINFO_FLAG_ALTREG","ROMINFO_FLAG_DI","ROMINFO_FLAG_NONREENT"))},
      {"name":"reserved-field-hardwired-zero","passed":"dw 0" in rom},
      {"name":"no-request-address-dispatch","passed":"jp (hl)" not in p and "call (hl)" not in p},
      {"name":"class-c-usr-is-metadata-only","passed":'ROMINFO_REC "USR",3,$34BC,ROMINFO_CLASS_C' in p},
      {"name":"rom-builtin-exact-lowercase-categories","passed":all(x in sh for x in ("'k','e','y','b','o','a','r','d'","'t','a','p','e'","'g','f','x'","'m','a','t','h'"))},
      {"name":"romcall-not-exposed","passed":"romcall" not in sh.lower()},
    ]

def _assemble(root:Path,run_command:Callable[...,Any],require_project_tool:Callable[[Path,str|Path],Path]):
    asm=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus")
    build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    src=build/"p711-rom-info.asm"; binary=build/"p711-rom-info.bin"; sym=build/"p711-rom-info.sym"
    src.write_text(
      "    DEVICE ZXSPECTRUM48\n"
      "    INCLUDE \"../include/zx48ux.inc\"\n"
      "    INCLUDE \"../src/kernel/rom_services.asm\"\n"
      "    INCLUDE \"../src/kernel/syscall.asm\"\n"
      "    INCLUDE \"../src/shell/sh.asm\"\n"
      f"    ORG ${MODULE:04X}\n"
      "p711_start:\n"
      "    EMIT_USER_RANGE_VALIDATION_ROUTINE\n"
      "    EMIT_P711_ROM_INFO_ROUTINES\n"
      "    EMIT_P711_ROM_INFO_SYSCALL_ROUTINES\n"
      "    EMIT_P711_ROM_BUILTIN_ROUTINES\n"
      "p711_end:\n"
      "    SAVEBIN \"p711-rom-info.bin\",p711_start,p711_end-p711_start\n",
      encoding="utf-8",newline="\n")
    r=run_command([asm,"--nologo","--lst=p711-rom-info.lst","--sym=p711-rom-info.sym","p711-rom-info.asm"],cwd=build,timeout_seconds=30.0)
    require(not r.timed_out and r.exit_code==0,f"P7.11 fixture assembly failed: {r.stderr or r.stdout}")
    require(binary.is_file() and 0<binary.stat().st_size<8192,"P7.11 fixture missing/oversize")
    return r,binary,sym

def _patch(module:bytes,req:bytes,arg:bytes=b""):
    def apply(ram:bytearray):
        ram[MODULE-0x4000:MODULE-0x4000+len(module)]=module
        ram[REQ-0x4000:REQ-0x4000+len(req)]=req
        ram[OUT-0x4000:OUT-0x4000+24]=b"\xa5"*24
        if arg: ram[REQ+16-0x4000:REQ+16-0x4000+len(arg)+1]=arg+b"\0"
    return apply

def _call_info(s:dict[str,int],idx:int,cat:int)->bytes:
    req=bytes((idx,cat,OUT&255,OUT>>8))
    code=bytearray(b"\xf3"+phase1._ld_sp(phase1.USER_STACK))
    code+=phase1._ld_hl(REQ)+b"\x22"+_word(s["syscall_arg_hl"])+phase1._call(s["zx48_p711_rom_info"])
    return req,code

def _info(root:Path,s:dict[str,int],module:bytes,idx:int,cat:int,expect:tuple[str,int,int,int,int]|None):
    req,code=_call_info(s,idx,cat)
    code+=_jp_c(FAIL_PC)+b"\xb7"+phase1._jp_nz(FAIL_PC)
    if expect is None:
        code+=b"\x7c\xb5"+phase1._jp_nz(FAIL_PC)
        for i in range(24): code+=_expectb(OUT+i,0xa5)
    else:
        name,addr,cls,ecat,flags=expect
        code+=b"\x7c\xb7"+phase1._jp_nz(FAIL_PC)+b"\x7d\xfe\x01"+phase1._jp_nz(FAIL_PC)
        raw=name.encode()+b"\0"*(16-len(name))+bytes((addr&255,addr>>8,cls,ecat,flags&255,flags>>8,0,0))
        require(len(raw)==24,"oracle record size")
        for i,v in enumerate(raw): code+=_expectb(OUT+i,v)
    code+=phase1._jp(PASS_PC)
    run_sna(root,bytes(code),patch=_patch(module,req),timeout=20.0)

def _bad(root:Path,s:dict[str,int],module:bytes,req:bytes):
    code=bytearray(b"\xf3"+phase1._ld_sp(phase1.USER_STACK)+phase1._ld_hl(REQ)+b"\x22"+_word(s["syscall_arg_hl"])+phase1._call(s["zx48_p711_rom_info"]))
    code+=_jp_nc(FAIL_PC)+bytes((0xfe,E_INVAL))+phase1._jp_nz(FAIL_PC)
    for i in range(24): code+=_expectb(OUT+i,0xa5)
    code+=phase1._jp(PASS_PC)
    run_sna(root,bytes(code),patch=_patch(module,req),timeout=20.0)

def _shell(root:Path,s:dict[str,int],module:bytes,arg:bytes|None,expected:int|None,stages:int=1,bg:int=0):
    argc=1 if arg is None else 2
    ptr=0 if arg is None else REQ+16
    code=bytearray(b"\xf3"+phase1._ld_sp(phase1.USER_STACK)+phase1._ld_hl(ptr)+bytes((0x3e,argc,0x06,stages,0x0e,bg))+phase1._call(s["sh_p711_rom_builtin"]))
    if expected is None:
        code+=_jp_nc(FAIL_PC)
    else:
        code+=_jp_c(FAIL_PC)+b"\x7c\xb7"+phase1._jp_nz(FAIL_PC)+b"\x7d"+bytes((0xfe,expected))+phase1._jp_nz(FAIL_PC)
    code+=phase1._jp(PASS_PC)
    run_sna(root,bytes(code),patch=_patch(module,b"\0"*4,arg or b""),timeout=20.0)

def dispatch(root:Path,action:str,step:str,*,sha256_file,run_command,require_project_tool):
    if step!="P7.11": raise P711Error(f"unsupported {step} {action}")
    assertions=_source(root); require(all(x["passed"] for x in assertions),"P7.11 static failure")
    kc,kernel,_=phase1._assemble_kernel(root,run_command,require_project_tool)
    fc,binary,sym=_assemble(root,run_command,require_project_tool)
    names=("zx48_p711_rom_info","syscall_arg_hl","sh_p711_rom_builtin")
    symbols=phase3_open_descriptions._symbols(sym,names)
    if action=="test":
        module=binary.read_bytes()
        cases = [
          ("keyboard-first", lambda: _info(root,symbols,module,0,1,("KEY-SCAN",0x028e,1,1,0))),
          ("keyboard-last", lambda: _info(root,symbols,module,2,1,("KEY-DECODE",0x0333,1,1,10))),
          ("console-first", lambda: _info(root,symbols,module,0,2,("PRINT-A",0x0010,1,2,11))),
          ("tape-last", lambda: _info(root,symbols,module,1,3,("LD-BYTES",0x0556,1,3,14))),
          ("graphics-last", lambda: _info(root,symbols,module,4,4,("DRAW-LINE",0x24ba,1,4,11))),
          ("sound-last", lambda: _info(root,symbols,module,1,5,("BEEP-COMMAND",0x03f8,2,5,15))),
          ("math-first", lambda: _info(root,symbols,module,0,6,("FP-CALC",0x0028,2,6,11))),
          ("math-last", lambda: _info(root,symbols,module,15,6,("USR",0x34bc,3,6,11))),
          ("math-past", lambda: _info(root,symbols,module,16,6,None)),
          ("all-past", lambda: _info(root,symbols,module,29,0,None)),
          ("bad-category", lambda: _bad(root,symbols,module,bytes((0,7,OUT&255,OUT>>8)))),
          ("bad-range", lambda: _bad(root,symbols,module,bytes((0,1,0xfe,0xdf)))),
          ("shell-all", lambda: _shell(root,symbols,module,None,0)),
          ("shell-keyboard", lambda: _shell(root,symbols,module,b"keyboard",1)),
          ("shell-tape", lambda: _shell(root,symbols,module,b"tape",3)),
          ("shell-gfx", lambda: _shell(root,symbols,module,b"gfx",4)),
          ("shell-math", lambda: _shell(root,symbols,module,b"math",6)),
          ("shell-sound-reject", lambda: _shell(root,symbols,module,b"sound",None)),
          ("shell-console-reject", lambda: _shell(root,symbols,module,b"console",None)),
          ("shell-case-reject", lambda: _shell(root,symbols,module,b"ROM",None)),
          ("shell-romcall-reject", lambda: _shell(root,symbols,module,b"romcall",None)),
          ("shell-pipeline-reject", lambda: _shell(root,symbols,module,b"math",None,stages=2)),
          ("shell-bg-reject", lambda: _shell(root,symbols,module,b"math",None,bg=1)),
        ]
        for name, case in cases:
            try:
                case()
            except Exception as exc:
                raise P711Error(f"P7.11 runtime vector {name} failed: {exc}") from exc
        assertions += [
          {"name":"fuse-every-category-first-last-past-end-layout-exact","passed":True},
          {"name":"fuse-classes-a-b-c-and-contract-flags-exact","passed":True},
          {"name":"fuse-invalid-category-and-malformed-output-range-fail-before-publish","passed":True},
          {"name":"fuse-rom-builtin-only-exposes-frozen-safe-categories","passed":True},
        ]
    hashes={
      "v1/build/kernel.bin":sha256_file(kernel),
      "v1/build/p711-rom-info.bin":sha256_file(binary),
      "v1/src/kernel/rom_services.asm":sha256_file(root/"v1/src/kernel/rom_services.asm"),
      "v1/src/kernel/syscall.asm":sha256_file(root/"v1/src/kernel/syscall.asm"),
      "v1/src/shell/sh.asm":sha256_file(root/"v1/src/shell/sh.asm"),
      "v1/tools-host/test-driver/phase7_rom_info.py":sha256_file(root/"v1/tools-host/test-driver/phase7_rom_info.py"),
      "v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
    }
    return [kc,fc],hashes,assertions
