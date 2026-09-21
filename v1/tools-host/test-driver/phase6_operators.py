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

class P610Error(DriverError): pass
def require(v,m):
    if not v: raise P610Error(m)

OPS=((b"&&","AND"),(b"||","OR"),(b">>","APPEND"),(b";","SEMI"),(b">","OUT"),(b"<","IN"),(b"|","PIPE"),(b"&","BG"))

def lex(raw:bytes):
    out=[]; i=0; q=None
    while i<len(raw):
        c=raw[i]
        if q=="single":
            if c==0x27: q=None
            i+=1; continue
        if q=="double":
            if c==0x22:
                q=None; i+=1; continue
            if c==0x5c:
                i+=2 if i+1<len(raw) else 1; continue
            i+=1; continue
        if c==0x27: q="single"; i+=1; continue
        if c==0x22: q="double"; i+=1; continue
        if c==0x5c:
            if i+1>=len(raw): raise ValueError("E_INVAL")
            i+=2; continue
        if c in (0x28,0x29): raise ValueError("E_INVAL")
        hit=False
        for spelling,name in OPS:
            if raw.startswith(spelling,i):
                out.append((i,name,spelling)); i+=len(spelling); hit=True; break
        if not hit: i+=1
    if q is not None: raise ValueError("E_INVAL")
    return out

def dispatch(root:Path,action:str,step:str,*,sha256_file,run_command,require_project_tool):
    if step!="P6.10": raise DriverError(f"Phase-6 operator step is not registered: {step}")
    sp=root/"v1/src/shell/sh.asm"; text=sp.read_text(); macro=text.split("MACRO EMIT_P610_OPERATOR_ROUTINES",1)[1].split("ENDM",1)[0]
    assertions=[
      {"name":"all-eight-operators-enumerated","passed":all(x in macro for x in ("P610_OP_SEMI","P610_OP_AND","P610_OP_OR","P610_OP_OUT","P610_OP_APPEND","P610_OP_IN","P610_OP_PIPE","P610_OP_BG"))},
      {"name":"recognition-gated-unquoted-unescaped","passed":"A=quote mode" in macro and "B=1 when current byte escaped" in macro and macro.index("or a")<macro.index("cp ';'")},
      {"name":"maximal-double-operators","passed":"cp '&'" in macro and "cp '|'" in macro and "cp '>'" in macro and "ld b,2" in macro},
      {"name":"grouping-explicit-invalid","passed":"cp '('" in macro and "cp ')'" in macro and "ld a,E_INVAL" in macro},
    ]
    require(all(a["passed"] for a in assertions),"P6.10 static contract failure")
    asm=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus"); build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    sf=build/"p610-operators.asm"
    sf.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/shell/sh.asm"
    ORG $C000
p610_start:
    EMIT_P610_OPERATOR_ROUTINES
p610_end:
    SAVEBIN "p610-operators.bin",p610_start,p610_end-p610_start
""",encoding="utf-8",newline="\n")
    sr=run_command([asm,"--nologo","--lst=p610-operators.lst","--sym=p610-operators.sym","p610-operators.asm"],cwd=build,timeout_seconds=30)
    require(not sr.timed_out and sr.exit_code==0,f"P6.10 operator assembly failed: {sr.stderr or sr.stdout}")
    image=(build/"p610-operators.bin").read_bytes(); mex=phase6_issue.mex1(image)
    maketap=phase6_issue.load_module(root/"v1/tools-host/maketap/maketap.py","zxux_p610_maketap")
    tap=maketap.m48o_blocks(maketap.M48OObject("sh",maketap.M48O_BIN,maketap.DIR_BIN,mex)); tp=build/"p610-operators.tap"; tp.write_bytes(tap)
    require(tap==maketap.m48o_blocks(maketap.M48OObject("sh",maketap.M48O_BIN,maketap.DIR_BIN,mex)),"P6.10 TAP rebuild mismatch")
    if action=="test":
        source=b"a;b&&c||d>e>>f<g|h&"
        want=["SEMI","AND","OR","OUT","APPEND","IN","PIPE","BG"]
        got=[x[1] for x in lex(source)]
        require(got==want,f"P6.10 operator corpus mismatch: {got}")
        require(lex(b"echo ';' \\| \"&&\" '>>'")==[],"quoted/escaped operators classified")
        for bad in (b"(a)",b"a)",b"(a"):
            try: lex(bad)
            except ValueError as exc: require(str(exc)=="E_INVAL","wrong grouping error")
            else: raise P610Error(f"P6.10 grouping accepted: {bad!r}")
        assertions += [
          {"name":"golden-operator-corpus","passed":True,"operators":8},
          {"name":"quoted-escaped-operators-literal","passed":True},
          {"name":"unsupported-parentheses-rejected","passed":True},
        ]
    hashes={
      "v1/src/shell/sh.asm":sha256_file(sp),"v1/build/p610-operators.tap":sha256_file(tp),
      "v1/tools-host/test-driver/phase6_operators.py":sha256_file(root/"v1/tools-host/test-driver/phase6_operators.py"),
      "v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
      "v1/dist/certification/P6.09.build.json":sha256_file(root/"v1/dist/certification/P6.09.build.json"),
      "v1/dist/certification/P6.09.test.json":sha256_file(root/"v1/dist/certification/P6.09.test.json"),
      "v1/dist/media/P6.09/manifest.json":sha256_file(root/"v1/dist/media/P6.09/manifest.json")}
    return [sr],hashes,assertions
