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

import re
import phase1
import phase3_open_descriptions
from driver_core import DriverError
from fuse_harness import PASS_PC, FAIL_PC, run_sna

class P1008Error(DriverError):
    pass

def require(ok,msg):
    if not ok: raise P1008Error(msg)

PREC={"|":1,"^":2,"&":3,"<<":4,">>":4,"+":5,"-":5,"*":6,"/":6,"%":6}
TOK=re.compile(r"\s*(<<|>>|[()+\-*/%&|^~]|\$[0-9A-Fa-f]+|[0-9]+)")

def tokenize(s):
    out=[]; p=0
    while p<len(s):
        m=TOK.match(s,p)
        require(m is not None, f"invalid token at {p}")
        out.append(m.group(1)); p=m.end()
    out.append("<eof>")
    return out

def eval_expr(s):
    t=tokenize(s); pos=0
    def atom():
        nonlocal pos
        x=t[pos]; pos+=1
        if x=="(":
            v=expr(1); require(t[pos]==")","missing )"); pos+=1; return v
        if x in ("-","~"):
            v=atom()
            return ((-v) if x=="-" else (~v)) & 0xFFFF
        if x.startswith("$"): return int(x[1:],16)
        require(x.isdigit(),"expected atom")
        return int(x,10)
    def expr(minp):
        nonlocal pos
        lhs=atom()
        while t[pos] in PREC and PREC[t[pos]]>=minp:
            op=t[pos]; p=PREC[op]; pos+=1
            rhs=expr(p+1)
            if op=="+": lhs=(lhs+rhs)&0xFFFF
            elif op=="-": lhs=(lhs-rhs)&0xFFFF
            elif op=="*": lhs=(lhs*rhs)&0xFFFF
            elif op=="/":
                require(rhs!=0,"divide by zero"); lhs=lhs//rhs
            elif op=="%":
                require(rhs!=0,"modulo by zero"); lhs=lhs%rhs
            elif op=="&": lhs=lhs&rhs
            elif op=="|": lhs=lhs|rhs
            elif op=="^": lhs=lhs^rhs
            elif op=="<<": lhs=(lhs<<(rhs&15))&0xFFFF
            elif op==">>": lhs=(lhs>>(rhs&15))&0xFFFF
        return lhs
    v=expr(1); require(t[pos]=="<eof>","trailing token"); return v

def dispatch(root,action,step,*,sha256_file,run_command,require_project_tool):
    if step!="P10.08": raise DriverError(step)
    source=root/"tools/as.asm"; text=source.read_text(encoding="utf-8")
    assertions=[
      {"name":"operator-core-present","passed":"as_p1008_apply:" in text},
      {"name":"precedence-authority-present","passed":"as_p1008_precedence:" in text},
      {"name":"unary-ops-present","passed":"as_p1008_neg:" in text and "as_p1008_not:" in text},
      {"name":"divide-zero-path","passed":"as_p1008_udiv:" in text and "jr z,as_p1008_error" in text},
    ]
    goldens={
      "1+2*3":7,
      "(1+2)*3":9,
      "$10|3":19,
      "15&6^1":7,
      "1<<4+1":32,
      "64>>2+1":8,
      "~0":0xFFFF,
      "-1":0xFFFF,
      "20/3":6,
      "20%3":2,
    }
    assertions.extend({"name":f"golden-{i}","passed":eval_expr(e)==v} for i,(e,v) in enumerate(goldens.items(),1))
    rejected=False
    try: eval_expr("7/0")
    except P1008Error: rejected=True
    assertions.append({"name":"divide-zero-rejected","passed":rejected})
    require(all(a["passed"] for a in assertions),"P10.08 expression contract failure")

    assembler=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus")
    build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    fixture=build/"p1008-expr.asm"
    fixture.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../../tools/as.asm"
    ORG $C000
fixture:
    EMIT_P10_AS_EXPR_ROUTINES
fixture_end:
    SAVEBIN "p1008-expr.bin",fixture,fixture_end-fixture
""",encoding="utf-8",newline="\n")
    result=run_command([assembler,"--nologo","--lst=p1008-expr.lst","--sym=p1008-expr.sym",fixture.name],cwd=build,timeout_seconds=30)
    require(not result.timed_out and result.exit_code==0,f"P10.08 assemble: {result.stderr or result.stdout}")

    if action=="test":
        names=("as_p1008_apply","as_p1008_neg","as_p1008_not")
        syms=phase3_open_descriptions._symbols(build/"p1008-expr.sym",names)
        image=(build/"p1008-expr.bin").read_bytes()
        def patch(ram): ram[0xC000-0x4000:0xC000-0x4000+len(image)]=image
        def check(op,lhs,rhs,want):
            code=(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._ld_hl(lhs)+phase1._ld_de(rhs)+bytes((0x3E,op))
                  +phase1._call(syms["as_p1008_apply"])+phase1._jp_c(FAIL_PC)+phase1._ld_de(want)
                  +b"\xB7\xED\x52"+phase1._jp_nz(FAIL_PC)+phase1._jp(PASS_PC))
            run_sna(root,code,patch=patch)
        for v in ((1,5,7,12),(2,5,7,0xFFFE),(3,7,6,42),(4,20,3,6),(5,20,3,2),(6,0xF0F0,0x0FF0,0x00F0),(7,0xF000,0x00F0,0xF0F0),(8,0xAAAA,0x0F0F,0xA5A5),(9,1,4,16),(10,64,3,8)):
            check(*v)
        code=(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._ld_hl(1)+phase1._call(syms["as_p1008_neg"])
              +phase1._ld_de(0xFFFF)+b"\xB7\xED\x52"+phase1._jp_nz(FAIL_PC)+phase1._jp(PASS_PC))
        run_sna(root,code,patch=patch)
        code=(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._ld_hl(0)+phase1._call(syms["as_p1008_not"])
              +phase1._ld_de(0xFFFF)+b"\xB7\xED\x52"+phase1._jp_nz(FAIL_PC)+phase1._jp(PASS_PC))
        run_sna(root,code,patch=patch)
        code=(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._ld_hl(7)+phase1._ld_de(0)+bytes((0x3E,4))
              +phase1._call(syms["as_p1008_apply"])+b"\xD2"+phase1._word(FAIL_PC)+phase1._jp(PASS_PC))
        run_sna(root,code,patch=patch)
        assertions += [
          {"name":"fuse-binary-operator-corpus","passed":True},
          {"name":"fuse-unary-operator-corpus","passed":True},
          {"name":"fuse-divzero-rejection","passed":True},
        ]

    hashes={
      "tools/as.asm":sha256_file(source),
      "v1/build/p1008-expr.bin":sha256_file(build/"p1008-expr.bin"),
      "v1/tools-host/test-driver/phase10_as_expressions.py":sha256_file(root/"v1/tools-host/test-driver/phase10_as_expressions.py"),
      "v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
      "v1/dist/certification/P10.07.build.json":sha256_file(root/"v1/dist/certification/P10.07.build.json"),
      "v1/dist/certification/P10.07.test.json":sha256_file(root/"v1/dist/certification/P10.07.test.json"),
    }
    return [result],hashes,assertions
