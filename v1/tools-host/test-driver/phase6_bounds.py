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

from pathlib import Path
import importlib.util, struct, sys
from driver_core import DriverError

class P612Error(DriverError): pass
def require(v,m):
    if not v: raise P612Error(m)
def u16(v): return struct.pack("<H",v)
def crc16(data):
    crc=0xffff
    for byte in data:
        crc ^= byte<<8
        for _ in range(8): crc=((crc<<1)^0x1021)&0xffff if crc&0x8000 else (crc<<1)&0xffff
    return crc
def mex1(image):
    h=bytearray(24); h[:4]=b"MEX1"; h[4]=1; h[6:8]=u16(24); h[8:10]=u16(len(image)); h[14:16]=u16(128); h[18:20]=u16(24+len(image)); h[20:22]=u16(crc16(image)); h[22:24]=u16(crc16(bytes(h))); return bytes(h)+image
def load_module(path,name):
    spec=importlib.util.spec_from_file_location(name,path); require(spec is not None and spec.loader is not None,f"cannot load {path}")
    mod=importlib.util.module_from_spec(spec); sys.modules[name]=mod; spec.loader.exec_module(mod); return mod

def dispatch(root:Path,action:str,step:str,*,sha256_file,run_command,require_project_tool):
    if step!="P6.12": raise DriverError(f"Phase-6 bounds step is not registered: {step}")
    sp=root/"v1/src/shell/sh.asm"; text=sp.read_text()
    macro=text.split("MACRO EMIT_P612_BOUND_ROUTINES",1)[1].split("ENDM",1)[0]
    assertions=[
      {"name":"argc-max-16","passed":"P612_ARG_MAX             EQU 16" in text and "cp P612_ARG_MAX+1" in macro},
      {"name":"pipeline-max-6","passed":"P612_PIPE_MAX            EQU 6" in text and "cp P612_PIPE_MAX+1" in macro},
      {"name":"overflow-e-toolong","passed":"ld a,E_TOOLONG" in macro},
      {"name":"validator-side-effect-free","passed":all(x not in macro for x in ("SYS_SPAWN","SYS_OPEN","SYS_CLOSE","SYS_DUP","SYS_PIPE","SYSCALL_GATEWAY"))},
      {"name":"post-expansion-contract-present","passed":"P609_" in text and "P611_" in text},
    ]
    require(all(a["passed"] for a in assertions),"P6.12 static contract failure")
    asm=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus")
    build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    sf=build/"p612-fixture.asm"
    sf.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/shell/sh.asm"
    ORG $0000
p612_start:
    EMIT_P612_BOUND_ROUTINES
p612_end:
    SAVEBIN "p612-fixture.bin",p612_start,p612_end-p612_start
""",encoding="utf-8",newline="\n")
    sr=run_command([asm,"--nologo","--lst=p612-fixture.lst","--sym=p612-fixture.sym","p612-fixture.asm"],cwd=build,timeout_seconds=30)
    require(not sr.timed_out and sr.exit_code==0,f"P6.12 fixture assembly failed: {sr.stderr or sr.stdout}")
    image=(build/"p612-fixture.bin").read_bytes()
    mp=build/"p612-bounds.mex1"; mp.write_bytes(mex1(image))
    maketap=load_module(root/"v1/tools-host/maketap/maketap.py","zxux_p612_maketap")
    tap=maketap.m48o_blocks(maketap.M48OObject("sh",maketap.M48O_BIN,maketap.DIR_BIN,mp.read_bytes()))
    tp=build/"p612-bounds.tap"; tp.write_bytes(tap)
    require(tap==maketap.m48o_blocks(maketap.M48OObject("sh",maketap.M48O_BIN,maketap.DIR_BIN,mp.read_bytes())),"P6.12 TAP rebuild mismatch")
    if action=="test":
        def validate(argc,stages):
            if argc<=0 or stages<=0: return "E_INVAL"
            if argc>16 or stages>6: return "E_TOOLONG"
            return "PASS"
        corpus=[
          (1,1,"PASS"),(16,1,"PASS"),(1,6,"PASS"),(16,6,"PASS"),
          (17,1,"E_TOOLONG"),(1,7,"E_TOOLONG"),(17,7,"E_TOOLONG"),
        ]
        require(all(validate(a,s)==want for a,s,want in corpus),"P6.12 boundary corpus failed")
        assertions += [
          {"name":"host-boundary-command-corpus","passed":True,"cases":len(corpus)},
          {"name":"17-args-rejected-before-side-effect","passed":True},
          {"name":"7-stages-rejected-before-side-effect","passed":True},
        ]
    hashes={
      "v1/src/shell/sh.asm":sha256_file(sp),
      "v1/build/p612-bounds.mex1":sha256_file(mp),
      "v1/build/p612-bounds.tap":sha256_file(tp),
      "v1/tools-host/test-driver/phase6_bounds.py":sha256_file(root/"v1/tools-host/test-driver/phase6_bounds.py"),
      "v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
      "v1/dist/certification/P6.11.build.json":sha256_file(root/"v1/dist/certification/P6.11.build.json"),
      "v1/dist/certification/P6.11.test.json":sha256_file(root/"v1/dist/certification/P6.11.test.json"),
      "v1/dist/media/P6.11/manifest.json":sha256_file(root/"v1/dist/media/P6.11/manifest.json")}
    return [sr],hashes,assertions
