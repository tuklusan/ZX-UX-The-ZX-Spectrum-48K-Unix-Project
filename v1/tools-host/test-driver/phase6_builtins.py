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
import importlib.util, struct, sys
from driver_core import DriverError
from fuse_harness import FAIL_PC, PASS_PC, run_sna
import phase1, phase3_open_descriptions

BASE=0xC000
NAME=0xA000
CORE=[b"cd",b"pwd",b"set",b"unset",b"jobs",b"wait",b"kill",b"mem",b"ps",b"clear",b"save",b"load",b"verify",b"tape",b"exit"]
HOOKS=[b"calc",b"beep",b"plot",b"line",b"circle",b"point",b"ink",b"paper",b"bright",b"flash",b"inverse",b"over",b"border",b"rom"]

class P613Error(DriverError): pass
def require(v,m):
    if not v: raise P613Error(m)
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
def word(v): return bytes((v&255,(v>>8)&255))
def patch(module,name):
    def p(ram):
        ram[BASE-0x4000:BASE-0x4000+len(module)]=module
        ram[NAME-0x4000:NAME-0x4000+len(name)]=name
    return p

def dispatch(root:Path,action:str,step:str,*,sha256_file,run_command,require_project_tool):
    if step!="P6.13": raise DriverError(f"Phase-6 builtin step is not registered: {step}")
    sp=root/"v1/src/shell/sh.asm"; text=sp.read_text(); macro=text.split("MACRO EMIT_P613_BUILTIN_ROUTINES",1)[1].split("ENDM",1)[0]
    assertions=[
      {"name":"all-core-builtins-present","passed":all((f"'{chr(n[0])}'" if False else n.decode()) for n in CORE) and all(n.decode() in macro.replace("','","") for n in [])},
      {"name":"exact-bytewise-no-casefold","passed":"cp (hl)" in macro and "tolower" not in macro.lower()},
      {"name":"rom-hook-table-explicit","passed":"p613_rom_hook_table:" in macro and macro.count("dw 0")>=14},
      {"name":"rom-hooks-not-in-core-table","passed":macro.index("p613_core_table:") < macro.index("p613_rom_hook_table:")},
      {"name":"unknown-is-enoent","passed":"ld a,E_NOENT" in macro},
    ]
    core_section=macro.split("p613_core_table:",1)[1].split("p613_rom_hook_table:",1)[0]
    hook_section=macro.split("p613_rom_hook_table:",1)[1]
    def encoded(name):
        return ",".join(f"'{chr(ch)}'" for ch in name)
    assertions[0]["passed"]=all(encoded(n) in core_section for n in CORE)
    assertions[3]["passed"]=all(encoded(n) not in core_section for n in HOOKS) and all(encoded(n) in hook_section for n in HOOKS)
    require(all(a["passed"] for a in assertions),"P6.13 static contract failure")
    asm=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus"); build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    sf=build/"p613-fixture.asm"
    sf.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/shell/sh.asm"
    ORG $C000
p613_start:
    EMIT_P613_BUILTIN_ROUTINES
p613_end:
    SAVEBIN "p613-fixture.bin",p613_start,p613_end-p613_start
""",encoding="utf-8",newline="\n")
    sr=run_command([asm,"--nologo","--lst=p613-fixture.lst","--sym=p613-fixture.sym","p613-fixture.asm"],cwd=build,timeout_seconds=30)
    require(not sr.timed_out and sr.exit_code==0,f"P6.13 fixture assembly failed: {sr.stderr or sr.stdout}")
    image=(build/"p613-fixture.bin").read_bytes(); mp=build/"p613-builtins.mex1"; mp.write_bytes(mex1(image))
    maketap=load_module(root/"v1/tools-host/maketap/maketap.py","zxux_p613_maketap")
    tap=maketap.m48o_blocks(maketap.M48OObject("sh",maketap.M48O_BIN,maketap.DIR_BIN,mp.read_bytes())); tp=build/"p613-builtins.tap"; tp.write_bytes(tap)
    require(tap==maketap.m48o_blocks(maketap.M48OObject("sh",maketap.M48O_BIN,maketap.DIR_BIN,mp.read_bytes())),"P6.13 TAP rebuild mismatch")
    if action=="test":
        sy=phase3_open_descriptions._symbols(build/"p613-fixture.sym",("sh_p613_lookup_builtin","E_NOENT"))
        module=(build/"p613-fixture.bin").read_bytes()
        for idx,name in enumerate(CORE,1):
            code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._ld_hl(NAME)+bytes((0x06,len(name)))+phase1._call(sy["sh_p613_lookup_builtin"])+phase1._jp_c(FAIL_PC))
            code+=bytes((0xFE,idx))+phase1._jp_nz(FAIL_PC)+phase1._jp(PASS_PC)
            run_sna(root,bytes(code),patch=patch(module,name))
        misses=[b"CD",b"Pwd",b"quit",b"echo"]+HOOKS
        for name in misses:
            code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._ld_hl(NAME)+bytes((0x06,len(name)))+phase1._call(sy["sh_p613_lookup_builtin"])+b"\xD2"+word(FAIL_PC))
            code+=bytes((0xFE,sy["E_NOENT"]&255))+phase1._jp_nz(FAIL_PC)+phase1._jp(PASS_PC)
            run_sna(root,bytes(code),patch=patch(module,name))
        assertions += [{"name":"fuse-all-core-exact-lowercase","passed":True},{"name":"fuse-mixed-case-aliases-hooks-miss","passed":True}]
    hashes={
      "v1/src/shell/sh.asm":sha256_file(sp),"v1/build/p613-builtins.mex1":sha256_file(mp),"v1/build/p613-builtins.tap":sha256_file(tp),
      "v1/tools-host/test-driver/phase6_builtins.py":sha256_file(root/"v1/tools-host/test-driver/phase6_builtins.py"),"v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
      "v1/dist/certification/P6.12.build.json":sha256_file(root/"v1/dist/certification/P6.12.build.json"),"v1/dist/certification/P6.12.test.json":sha256_file(root/"v1/dist/certification/P6.12.test.json"),"v1/dist/media/P6.12/manifest.json":sha256_file(root/"v1/dist/media/P6.12/manifest.json")}
    return [sr],hashes,assertions
