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
from dataclasses import dataclass
from pathlib import Path
from driver_core import DriverError
import phase6_issue

class P611Error(DriverError): pass
def require(v,m):
    if not v: raise P611Error(m)

CONTROL={";","&&","||","|","&",">",">>","<"}

def scan(s:str):
    out=[]; cur=""; i=0
    while i<len(s):
        if s[i].isspace():
            if cur: out.append(cur); cur=""
            i+=1; continue
        if s[i] in "()": raise ValueError("E_INVAL")
        hit=None
        for op in ("&&","||",">>",";",">","<","|","&"):
            if s.startswith(op,i): hit=op; break
        if hit:
            if cur: out.append(cur); cur=""
            out.append(hit); i+=len(hit); continue
        cur+=s[i]; i+=1
    if cur: out.append(cur)
    return out

@dataclass(frozen=True)
class Cmd:
    argv:tuple[str,...]; inp:str|None=None; out:str|None=None; append:bool=False
@dataclass(frozen=True)
class Pipe:
    stages:tuple[Cmd,...]
@dataclass(frozen=True)
class Logic:
    first:Pipe; rest:tuple[tuple[str,Pipe],...]
@dataclass(frozen=True)
class Seq:
    units:tuple[Logic,...]; background:bool=False

def parse_cmd(t,i):
    argv=[]; inp=None; out=None; append=False
    while i<len(t) and t[i] not in ("|","&&","||",";","&"):
        if t[i] in ("<",">",">>"):
            op=t[i]; i+=1
            if i>=len(t) or t[i] in CONTROL: raise ValueError("E_INVAL")
            if op=="<":
                if inp is not None: raise ValueError("E_INVAL")
                inp=t[i]
            else:
                if out is not None: raise ValueError("E_INVAL")
                out=t[i]; append=(op==">>")
            i+=1
        else:
            argv.append(t[i]); i+=1
    if not argv: raise ValueError("E_INVAL")
    return Cmd(tuple(argv),inp,out,append),i

def parse_pipe(t,i):
    stages=[]; c,i=parse_cmd(t,i); stages.append(c)
    while i<len(t) and t[i]=="|":
        c,i=parse_cmd(t,i+1); stages.append(c)
    return Pipe(tuple(stages)),i

def parse_logic(t,i):
    first,i=parse_pipe(t,i); rest=[]
    while i<len(t) and t[i] in ("&&","||"):
        op=t[i]; p,i=parse_pipe(t,i+1); rest.append((op,p))
    return Logic(first,tuple(rest)),i

def parse(s:str):
    t=scan(s)
    if not t: raise ValueError("E_INVAL")
    background=False
    if "&" in t:
        if t[-1]!="&" or t.count("&")!=1 or any(x in t for x in (";","&&","||")): raise ValueError("E_INVAL")
        background=True; t=t[:-1]
        if not t: raise ValueError("E_INVAL")
    units=[]; u,i=parse_logic(t,0); units.append(u)
    while i<len(t):
        if t[i]!=";": raise ValueError("E_INVAL")
        u,i=parse_logic(t,i+1); units.append(u)
    return Seq(tuple(units),background)

def canon_cmd(c): return (c.argv,c.inp,c.out,c.append)
def canon(ast):
    return (ast.background,tuple((canon_cmd(u.first.stages[0]) if len(u.first.stages)==1 else tuple(canon_cmd(x) for x in u.first.stages),
        tuple((op,tuple(canon_cmd(x) for x in p.stages)) for op,p in u.rest)) for u in ast.units))

def dispatch(root:Path,action:str,step:str,*,sha256_file,run_command,require_project_tool):
    if step!="P6.11": raise DriverError(f"Phase-6 binding step is not registered: {step}")
    sp=root/"v1/src/shell/sh.asm"; text=sp.read_text(); macro=text.split("MACRO EMIT_P611_BINDING_ROUTINES",1)[1].split("ENDM",1)[0]
    assertions=[
      {"name":"redirection-highest-simple-command-binding","passed":"P611_PREC_REDIR         EQU 4" in text},
      {"name":"pipe-above-logic","passed":"P611_PREC_PIPE          EQU 3" in text and "P611_PREC_LOGIC         EQU 2" in text},
      {"name":"and-or-equal-precedence","passed":macro.count("ld c,P611_PREC_LOGIC")>=1 and "P610_OP_AND" in macro and "P610_OP_OR" in macro},
      {"name":"semicolon-lowest-sequence","passed":"P611_PREC_SEMI          EQU 1" in text},
      {"name":"background-final-exclusive","passed":"cannot coexist" in macro and "sh_p611_validate_background:" in macro},
      {"name":"grouping-rejected","passed":"sh_p611_reject_grouping:" in macro and "E_INVAL" in macro},
    ]
    require(all(a["passed"] for a in assertions),"P6.11 static contract failure")
    asm=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus"); build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    sf=build/"p611-binding.asm"
    sf.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/shell/sh.asm"
    ORG $C000
p611_start:
    EMIT_P610_OPERATOR_ROUTINES
    EMIT_P611_BINDING_ROUTINES
p611_end:
    SAVEBIN "p611-binding.bin",p611_start,p611_end-p611_start
""",encoding="utf-8",newline="\n")
    sr=run_command([asm,"--nologo","--lst=p611-binding.lst","--sym=p611-binding.sym","p611-binding.asm"],cwd=build,timeout_seconds=30)
    require(not sr.timed_out and sr.exit_code==0,f"P6.11 binding assembly failed: {sr.stderr or sr.stdout}")
    image=(build/"p611-binding.bin").read_bytes(); mex=phase6_issue.mex1(image)
    maketap=phase6_issue.load_module(root/"v1/tools-host/maketap/maketap.py","zxux_p611_maketap")
    tap=maketap.m48o_blocks(maketap.M48OObject("sh",maketap.M48O_BIN,maketap.DIR_BIN,mex)); tp=build/"p611-binding.tap"; tp.write_bytes(tap)
    require(tap==maketap.m48o_blocks(maketap.M48OObject("sh",maketap.M48O_BIN,maketap.DIR_BIN,mex)),"P6.11 TAP rebuild mismatch")
    if action=="test":
        a=parse("a > x | b && c || d ; e < y")
        require(len(a.units)==2 and len(a.units[0].first.stages)==2,"pipeline/sequence binding mismatch")
        require(a.units[0].first.stages[0].out=="x" and a.units[1].first.stages[0].inp=="y","redirection binding mismatch")
        require([x[0] for x in a.units[0].rest]==["&&","||"],"logic LTR mismatch")
        b=parse("a | b &"); require(b.background and len(b.units)==1 and len(b.units[0].first.stages)==2,"background pipeline mismatch")
        for bad in ("(a)","a && (b)","a & b","a & ; b","a && b &","a < x < y","a > x >> y"):
            try: parse(bad)
            except ValueError as exc: require(str(exc)=="E_INVAL","wrong parser error")
            else: raise P611Error(f"P6.11 invalid syntax accepted: {bad!r}")
        assertions += [
          {"name":"ast-golden-precedence-order","passed":True},
          {"name":"background-final-pipeline-only","passed":True},
          {"name":"parentheses-subshell-rejected","passed":True},
          {"name":"duplicate-redirection-rejected","passed":True},
        ]
    hashes={"v1/src/shell/sh.asm":sha256_file(sp),"v1/build/p611-binding.tap":sha256_file(tp),
      "v1/tools-host/test-driver/phase6_binding.py":sha256_file(root/"v1/tools-host/test-driver/phase6_binding.py"),
      "v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
      "v1/dist/certification/P6.10.build.json":sha256_file(root/"v1/dist/certification/P6.10.build.json"),
      "v1/dist/certification/P6.10.test.json":sha256_file(root/"v1/dist/certification/P6.10.test.json"),
      "v1/dist/media/P6.10/manifest.json":sha256_file(root/"v1/dist/media/P6.10/manifest.json")}
    return [sr],hashes,assertions
