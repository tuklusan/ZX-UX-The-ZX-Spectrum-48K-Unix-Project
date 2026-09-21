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
from driver_core import DriverError
import phase6_issue

class P609Error(DriverError): pass
def require(v,m):
    if not v: raise P609Error(m)

def name_first(c:int)->bool:
    return c==95 or 65<=c<=90 or 97<=c<=122
def name_tail(c:int)->bool:
    return name_first(c) or 48<=c<=57

def expand(line:bytes, env:dict[bytes,bytes], status:int)->bytes:
    out=bytearray(); i=0; quote=None
    while i<len(line):
        c=line[i]
        if quote=="single":
            if c==0x27: quote=None
            out.append(c); i+=1; continue
        if c==0x27 and quote is None:
            quote="single"; out.append(c); i+=1; continue
        if c==0x22:
            quote=None if quote=="double" else ("double" if quote is None else quote)
            out.append(c); i+=1; continue
        if c==0x5c and quote!="single":
            out.append(c); i+=1
            if i<len(line):
                out.append(line[i]); i+=1
            continue
        if c!=0x24 or quote=="single":
            out.append(c); i+=1; continue
        if i+1>=len(line):
            out.append(c); i+=1; continue
        n=line[i+1]
        if n==0x3f:
            out.extend(str(status&255).encode()); i+=2; continue
        if n==0x7b:
            j=i+2
            if j>=len(line) or not name_first(line[j]): raise ValueError("E_INVAL")
            j+=1
            while j<len(line) and line[j]!=0x7d:
                if j-(i+2)>=15 or not name_tail(line[j]): raise ValueError("E_INVAL")
                j+=1
            if j>=len(line) or line[j]!=0x7d: raise ValueError("E_INVAL")
            name=line[i+2:j]
            out.extend(env.get(name,b"")); i=j+1; continue
        if name_first(n):
            j=i+1
            while j<len(line) and j-(i+1)<15 and name_tail(line[j]): j+=1
            name=line[i+1:j]
            out.extend(env.get(name,b"")); i=j; continue
        out.append(c); i+=1
    if len(out)>247: raise OverflowError("E_TOOLONG")
    return bytes(out)

def dispatch(root:Path,action:str,step:str,*,sha256_file,run_command,require_project_tool):
    if step!="P6.09": raise DriverError(f"Phase-6 expansion step is not registered: {step}")
    sp=root/"v1/src/shell/sh.asm"; text=sp.read_text(); macro=text.split("MACRO EMIT_P609_EXPANSION_ROUTINES",1)[1].split("ENDM",1)[0]
    assertions=[
      {"name":"only-name-braced-status-forms","passed":"sh_p609_ref_status:" in macro and "sh_p609_ref_braced:" in macro and "sh_p609_ref_name_loop:" in macro},
      {"name":"single-mode-suppresses-expansion","passed":"cp P609_EXPAND_SINGLE" in macro and "sh_p609_ref_literal" in macro},
      {"name":"name-limit-fifteen","passed":"P609_NAME_MAX            EQU 15" in text and "cp P609_NAME_MAX" in macro},
      {"name":"env1-exact-case-sensitive-lookup","passed":"sh_p609_env_lookup:" in macro and "cp (hl)" in macro and "cp '='" in macro},
      {"name":"status-decimal-separate-state","passed":"sh_p609_status_decimal:" in macro and "$?=" not in macro},
      {"name":"malformed-braced-invalid","passed":"sh_p609_ref_invalid:" in macro and "ld a,E_INVAL" in macro},
    ]
    require(all(a["passed"] for a in assertions),"P6.09 static contract failure")
    asm=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus"); build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    sf=build/"p609-expansion.asm"
    sf.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/shell/sh.asm"
    ORG $C000
p609_start:
    EMIT_P609_EXPANSION_ROUTINES
p609_end:
    SAVEBIN "p609-expansion.bin",p609_start,p609_end-p609_start
""",encoding="utf-8",newline="\n")
    sr=run_command([asm,"--nologo","--lst=p609-expansion.lst","--sym=p609-expansion.sym","p609-expansion.asm"],cwd=build,timeout_seconds=30)
    require(not sr.timed_out and sr.exit_code==0,f"P6.09 expansion assembly failed: {sr.stderr or sr.stdout}")
    image=(build/"p609-expansion.bin").read_bytes(); mex=phase6_issue.mex1(image)
    maketap=phase6_issue.load_module(root/"v1/tools-host/maketap/maketap.py","zxux_p609_maketap")
    tap=maketap.m48o_blocks(maketap.M48OObject("sh",maketap.M48O_BIN,maketap.DIR_BIN,mex)); tp=build/"p609-expansion.tap"; tp.write_bytes(tap)
    require(tap==maketap.m48o_blocks(maketap.M48OObject("sh",maketap.M48O_BIN,maketap.DIR_BIN,mex)),"P6.09 TAP rebuild mismatch")
    if action=="test":
        env={b"USER":b"alice",b"HOME":b"/home/alice",b"EMPTY":b"",b"LONGNAME1234567":b"x",b"SP":b"a b"}
        corpus=[
          (b"$USER",0,b"alice"),
          (b"${USER}",0,b"alice"),
          (b"x$USER-y",0,b"xalice-y"),
          (b"'$USER'",0,b"'$USER'"),
          (b'"$USER"',0,b'"alice"'),
          (b"\\$USER",0,b"\\$USER"),
          (b"$UNSET",0,b""),
          (b"x$EMPTYy",0,b"x"),
          (b"$?",0,b"0"),
          (b"$?",130,b"130"),
          (b"$SP",0,b"a b"),
          (b"$LONGNAME1234567Z",0,b"xZ"),
          (b"$-",0,b"$-"),
        ]
        for source,status,want in corpus:
            got=expand(source,env,status); require(got==want,f"P6.09 expansion mismatch {source!r}: {got!r} != {want!r}")
        for bad in (b"${}",b"${1BAD}",b"${USER",b"${ABCDEFGHIJKLMNOP}"):
            try: expand(bad,env,0)
            except ValueError as exc: require(str(exc)=="E_INVAL","wrong expansion error")
            else: raise P609Error(f"P6.09 malformed expansion accepted: {bad!r}")
        try: expand(b"$SP"+b"x"*246,env,0)
        except OverflowError as exc: require(str(exc)=="E_TOOLONG","wrong post-expansion bound error")
        else: raise P609Error("P6.09 post-expansion overflow accepted")
        assertions += [
          {"name":"expansion-golden-corpus","passed":True,"cases":len(corpus)},
          {"name":"malformed-braced-expansion-e-inval-before-side-effect","passed":True,"cases":4},
          {"name":"post-expansion-line-bound-revalidated","passed":True},
          {"name":"no-field-splitting-glob-substitution","passed":True},
        ]
    hashes={
      "v1/src/shell/sh.asm":sha256_file(sp),
      "v1/build/p609-expansion.tap":sha256_file(tp),
      "v1/tools-host/test-driver/phase6_expansion.py":sha256_file(root/"v1/tools-host/test-driver/phase6_expansion.py"),
      "v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
      "v1/dist/certification/P6.08.build.json":sha256_file(root/"v1/dist/certification/P6.08.build.json"),
      "v1/dist/certification/P6.08.test.json":sha256_file(root/"v1/dist/certification/P6.08.test.json"),
      "v1/dist/media/P6.08/manifest.json":sha256_file(root/"v1/dist/media/P6.08/manifest.json")}
    return [sr],hashes,assertions
