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
EXPR=0xA000
OUT=0xA100
E_INVAL=0x01
E_NOTSUP=0x0F
E_NOENT=0x02

class P710Error(DriverError): pass
def require(v:bool,m:str)->None:
    if not v: raise P710Error(m)
def _word(v:int)->bytes: return bytes((v&255,(v>>8)&255))
def _jp_c(a:int)->bytes: return b"\xda"+_word(a)
def _jp_nc(a:int)->bytes: return b"\xd2"+_word(a)
def _expectb(a:int,v:int)->bytes: return b"\x3a"+_word(a)+bytes((0xfe,v&255))+phase1._jp_nz(FAIL_PC)

def _source(root:Path):
    sh=(root/"v1/src/shell/sh.asm").read_text(encoding="utf-8")
    rom=(root/"v1/src/kernel/rom_services.asm").read_text(encoding="utf-8")
    plan=(root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md").read_text(encoding="utf-8")
    m=sh.split("MACRO EMIT_P710_CALC_ROUTINES",1)[1].split("ENDM",1)[0]
    allowed=(("pi","P710_TOKEN_PI"),("abs","P710_TOKEN_ABS"),("sgn","P710_TOKEN_SGN"),("int","P710_TOKEN_INT"),
             ("sqrt","P710_TOKEN_SQR"),("exp","P710_TOKEN_EXP"),("ln","P710_TOKEN_LN"),("sin","P710_TOKEN_SIN"),
             ("cos","P710_TOKEN_COS"),("tan","P710_TOKEN_TAN"),("asin","P710_TOKEN_ASN"),("acos","P710_TOKEN_ACS"),("atan","P710_TOKEN_ATN"))
    return [
      {"name":"canonical-p710-present","passed":"## P7.10 - calc final safe expression gateway" in plan},
      {"name":"exact-lowercase-token-table","passed":all((",".join(f"'{c}'" for c in n)) in m and t in m for n,t in allowed)},
      {"name":"rnd-deferred","passed":"db 3,'r','n','d'" not in m},
      {"name":"only-decimal-safe-operators-accepted-directly","passed":all(f"cp '{x}'" in m for x in ".+-*/^()")},
      {"name":"unknown-or-uppercase-byte-families-reject","passed":"cp 'a'" in m and "cp 'z'+1" in m and "sh_p710_invalid" in m},
      {"name":"exact-one-argument-before-tokenizer","passed":m.index("cp 2")<m.index("call sh_p710_tokenize")},
      {"name":"single-stage-foreground-before-tokenizer","passed":m.index("cp 1")<m.index("call sh_p710_tokenize") and m.index("ld a,c")<m.index("call sh_p710_tokenize")},
      {"name":"calc-lookup-is-exact-and-no-external-resolution","passed":"sh_p710_lookup_calc:" in m and "SYS_STAT" not in m and "SYS_OPEN" not in m and "SYS_SPAWN" not in m},
      {"name":"rom-entry-after-shell-allowlist","passed":m.index("call sh_p710_tokenize")<m.index("jp zx48_rom_calc_expr")},
      {"name":"rom-scanner-isolated-stack-and-error-gateway","passed":all(t in rom for t in ("ROM_SCANNING","ROM_CALC_STACK","zx48_rom_calc_error:","rom_calc_saved_err_sp","rom_calc_saved_chadd","rom_calc_saved_flags"))},
      {"name":"rom-numeric-type-required-and-state-restored","passed":"bit 6,a" in rom and "zx48_rom_calc_cleanup:" in rom},
      {"name":"serialized-altreg-critical-section","passed":"ld (altreg_busy),a" in rom and "zx48_rom_calc_busy:" in rom},
    ]

def _assemble(root:Path,run_command:Callable[...,Any],require_project_tool:Callable[[Path,str|Path],Path]):
    asm=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus")
    build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    src=build/"p710-calc.asm"; binary=build/"p710-calc.bin"; sym=build/"p710-calc.sym"
    src.write_text(
      "    DEVICE ZXSPECTRUM48\n"
      "    INCLUDE \"../include/zx48ux.inc\"\n"
      "    INCLUDE \"../src/kernel/rom_services.asm\"\n"
      "    INCLUDE \"../src/shell/sh.asm\"\n"
      f"    ORG ${MODULE:04X}\n"
      "p710_start:\n"
      "altreg_busy: db 0\n"
      "    EMIT_P710_ROM_CALC_ROUTINES\n"
      "    EMIT_P710_CALC_ROUTINES\n"
      "p710_end:\n"
      "    SAVEBIN \"p710-calc.bin\",p710_start,p710_end-p710_start\n",
      encoding="utf-8",newline="\n")
    r=run_command([asm,"--nologo","--lst=p710-calc.lst","--sym=p710-calc.sym","p710-calc.asm"],cwd=build,timeout_seconds=30.0)
    require(not r.timed_out and r.exit_code==0,f"P7.10 fixture assembly failed: {r.stderr or r.stdout}")
    require(binary.is_file() and 0<binary.stat().st_size<8192,"P7.10 fixture missing/oversize")
    return r,binary,sym

def _patch(module:bytes,expr:bytes):
    def apply(ram:bytearray):
        ram[MODULE-0x4000:MODULE-0x4000+len(module)]=module
        ram[EXPR-0x4000:EXPR-0x4000+len(expr)+1]=expr+b"\0"
        ram[OUT-0x4000:OUT-0x4000+5]=b"\xA5"*5
    return apply

def _call(s:dict[str,int],argc:int=2,stages:int=1,bg:int=0)->bytes:
    return phase1._ld_hl(EXPR)+phase1._ld_de(OUT)+bytes((0x3e,argc&255,0x06,stages&255,0x0e,bg&255))+phase1._call(s["sh_p710_calc_builtin"])

def _positive(root:Path,s:dict[str,int],module:bytes,expr:bytes,exact:bytes|None=None):
    code=bytearray(b"\xf3"+phase1._ld_sp(phase1.USER_STACK))
    code+=_call(s)+_jp_c(FAIL_PC)+b"\xb7"+phase1._jp_nz(FAIL_PC)
    code+=_expectb(s["altreg_busy"],0)
    if exact is not None:
        for i,v in enumerate(exact): code+=_expectb(OUT+i,v)
    else:
        # Require the gateway to have published a result rather than leaving canary.
        code+=b"\x3a"+_word(OUT)+bytes((0xfe,0xa5))
        nz=0x9000+len(code)+3
        code+=b"\xc2"+_word(nz)
        for i in range(1,5):
            code+=b"\x3a"+_word(OUT+i)+bytes((0xfe,0xa5))+phase1._jp_nz(nz)
        code+=phase1._jp(FAIL_PC)
    code+=phase1._jp(PASS_PC)
    run_sna(root,bytes(code),patch=_patch(module,expr),timeout=20.0)

def _negative(root:Path,s:dict[str,int],module:bytes,expr:bytes,errno:int=E_INVAL,argc:int=2,stages:int=1,bg:int=0):
    code=bytearray(b"\xf3"+phase1._ld_sp(phase1.USER_STACK))
    code+=_call(s,argc,stages,bg)+_jp_nc(FAIL_PC)+bytes((0xfe,errno))+phase1._jp_nz(FAIL_PC)
    code+=_expectb(s["altreg_busy"],0)
    for i in range(5): code+=_expectb(OUT+i,0xa5)
    code+=phase1._jp(PASS_PC)
    run_sna(root,bytes(code),patch=_patch(module,expr),timeout=20.0)

def _lookup(root:Path,s:dict[str,int],module:bytes,name:bytes,ok:bool):
    code=bytearray(b"\xf3"+phase1._ld_sp(phase1.USER_STACK)+phase1._ld_hl(EXPR)+bytes((0x06,len(name)))+phase1._call(s["sh_p710_lookup_calc"]))
    if ok:
        code+=_jp_c(FAIL_PC)
        code+=b"\x7a"+bytes((0xfe,(s["sh_p710_calc_builtin"]>>8)&255))+phase1._jp_nz(FAIL_PC)
        code+=b"\x7b"+bytes((0xfe,s["sh_p710_calc_builtin"]&255))+phase1._jp_nz(FAIL_PC)
    else:
        code+=_jp_nc(FAIL_PC)+bytes((0xfe,E_NOENT))+phase1._jp_nz(FAIL_PC)
    code+=phase1._jp(PASS_PC)
    run_sna(root,bytes(code),patch=_patch(module,name),timeout=20.0)

def dispatch(root:Path,action:str,step:str,*,sha256_file,run_command,require_project_tool):
    if step!="P7.10": raise P710Error(f"unsupported {step} {action}")
    assertions=_source(root); failed=[x["name"] for x in assertions if x.get("passed") is not True]
    require(not failed,f"P7.10 static failure: {failed}")
    kc,kernel,_=phase1._assemble_kernel(root,run_command,require_project_tool)
    fc,binary,sym=_assemble(root,run_command,require_project_tool)
    names=("sh_p710_calc_builtin","sh_p710_lookup_calc","altreg_busy")
    symbols=phase3_open_descriptions._symbols(sym,names)
    if action=="test":
        module=binary.read_bytes()
        positives=(b"1",b"-1",b"1+2*3",b"(1+2)/3",b"2^3",b"pi",b"abs(-2)",b"sgn(-2)",b"int(1.5)",
                   b"sqrt(4)",b"exp(0)",b"ln(1)",b"sin(0)",b"cos(0)",b"tan(0)",b"asin(0)",b"acos(1)",b"atan(0)")
        for expr in positives: _positive(root,symbols,module,expr)
        negatives=(b"rnd",b"SIN(0)",b"peek(1)",b"in(1)",b"inkey$",b"screen$",b"attr(1,1)",b"point(1,1)",
                   b"usr(0)",b"poke 1,2",b"out 1,2",b"clear",b"new",b"run",b"load",b"save",b"merge",
                   b"randomize usr 0",b"a=1",b"\"x\"")
        for expr in negatives: _negative(root,symbols,module,expr)
        _negative(root,symbols,module,b"1",argc=1)
        _negative(root,symbols,module,b"1",argc=3)
        _negative(root,symbols,module,b"1",errno=E_NOTSUP,stages=2)
        _negative(root,symbols,module,b"1",errno=E_NOTSUP,bg=1)
        _lookup(root,symbols,module,b"calc",True)
        for name in (b"CALC",b"Calc",b"calC",b"beep"):_lookup(root,symbols,module,name,False)
        assertions += [
          {"name":"fuse-every-allowed-grammar-family-returns-controlled-five-byte-result","passed":True},
          {"name":"fuse-forbidden-token-families-reject-safely","passed":True},
          {"name":"fuse-arity-pipeline-background-fail-before-result-mutation","passed":True},
          {"name":"fuse-exact-case-calc-builtin-lookup-bypasses-external-resolution","passed":True},
        ]
    hashes={
      "v1/build/kernel.bin":sha256_file(kernel),
      "v1/build/p710-calc.bin":sha256_file(binary),
      "v1/src/shell/sh.asm":sha256_file(root/"v1/src/shell/sh.asm"),
      "v1/src/kernel/rom_services.asm":sha256_file(root/"v1/src/kernel/rom_services.asm"),
      "v1/tools-host/test-driver/phase7_calc.py":sha256_file(root/"v1/tools-host/test-driver/phase7_calc.py"),
      "v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
    }
    return [kc,fc],hashes,assertions
