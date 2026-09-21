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

SHELL=0xC000
GATE=0xE000
CMD=0xA000
PATH=0xA080
OUT=0xA180

class P614Error(DriverError): pass
def require(v,m):
    if not v: raise P614Error(m)
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
def expect_byte(addr,val): return b"\x3A"+word(addr)+bytes((0xFE,val&255))+phase1._jp_nz(FAIL_PC)
def patch(shell,gate,cmd,path=b""):
    def p(ram):
        ram[SHELL-0x4000:SHELL-0x4000+len(shell)]=shell
        ram[GATE-0x4000:GATE-0x4000+len(gate)]=gate
        ram[CMD-0x4000:CMD-0x4000+len(cmd)+1]=cmd+b"\0"
        ram[PATH-0x4000:PATH-0x4000+len(path)+1]=path+b"\0"
        ram[OUT-0x4000:OUT-0x4000+40]=b"\xA5"*40
    return p
def call_lookup(symbol,path_ptr=PATH):
    return phase1._ld_hl(CMD)+b"\xDD\x21"+word(path_ptr)+phase1._ld_de(OUT)+phase1._call(symbol)
def assert_cstr(addr,data):
    code=bytearray()
    for i,b in enumerate(data+b"\0"): code+=expect_byte(addr+i,b)
    return bytes(code)

def dispatch(root:Path,action:str,step:str,*,sha256_file,run_command,require_project_tool):
    if step!="P6.14": raise DriverError(f"Phase-6 PATH step is not registered: {step}")
    sp=root/"v1/src/shell/sh.asm"; text=sp.read_text(); macro=text.split("MACRO EMIT_P614_PATH_ROUTINES",1)[1].split("ENDM",1)[0]
    assertions=[
      {"name":"colon-left-to-right","passed":"sh_p614_component_start:" in macro and "cp ':'" in macro},
      {"name":"empty-component-dot","passed":"ld (hl),'.'" in macro},
      {"name":"unset-empty-no-search","passed":"ld (p614_path_ptr),ix" in macro and "jp z,sh_p614_noent" in macro},
      {"name":"slash-bypasses-path","passed":"p614_has_slash" in macro and "sh_p614_direct:" in macro},
      {"name":"skip-nondir-wrongtype","passed":"cp OBJ_DIR" in macro and "cp OBJ_BIN" in macro},
      {"name":"direct-does-not-precheck-bin","passed":"sh_p614_direct_stat:" in macro and macro.split("sh_p614_direct_stat:",1)[1].split("sh_p614_build_candidate:",1)[0].find("cp OBJ_BIN")==-1},
      {"name":"path-limit-31","passed":"P614_PATH_MAX            EQU 31" in text},
      {"name":"no-hidden-default","passed":"'/bin:.'" not in macro},
    ]
    require(all(a["passed"] for a in assertions),"P6.14 static contract failure")
    asm=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus"); build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    sf=build/"p614-shell-fixture.asm"
    sf.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/shell/sh.asm"
    ORG $C000
p614_start:
    EMIT_P614_PATH_ROUTINES
p614_end:
    SAVEBIN "p614-shell-fixture.bin",p614_start,p614_end-p614_start
""",encoding="utf-8",newline="\n")
    sr=run_command([asm,"--nologo","--lst=p614-shell-fixture.lst","--sym=p614-shell-fixture.sym","p614-shell-fixture.asm"],cwd=build,timeout_seconds=30)
    require(not sr.timed_out and sr.exit_code==0,f"P6.14 shell fixture failed: {sr.stderr or sr.stdout}")
    image=(build/"p614-shell-fixture.bin").read_bytes(); mp=build/"p614-path.mex1"; mp.write_bytes(mex1(image))
    maketap=load_module(root/"v1/tools-host/maketap/maketap.py","zxux_p614_maketap")
    tap=maketap.m48o_blocks(maketap.M48OObject("sh",maketap.M48O_BIN,maketap.DIR_BIN,mp.read_bytes())); tp=build/"p614-path.tap"; tp.write_bytes(tap)

    gf=build/"p614-gateway.asm"
    gf.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    ORG $E000
p614_gate:
    cp SYS_STAT
    jr nz,p614_gate_notsup
    ld e,(hl)
    inc hl
    ld d,(hl)
    inc hl
    ld c,(hl)
    inc hl
    ld b,(hl)
    ex de,hl
    ld ix,p614_cases
p614_case_loop:
    ld a,(ix+0)
    cp $ff
    jr z,p614_gate_noent
    ld e,(ix+1)
    ld d,(ix+2)
    push hl
p614_case_cmp:
    ld a,(de)
    cp (hl)
    jr nz,p614_case_miss
    or a
    jr z,p614_case_hit
    inc de
    inc hl
    jr p614_case_cmp
p614_case_miss:
    pop hl
    ld de,5
    add ix,de
    jr p614_case_loop
p614_case_hit:
    pop hl
    ld a,(ix+3)
    or a
    jr nz,p614_case_error
    ld a,(ix+4)
    ld (bc),a
    inc bc
    xor a
    ld (bc),a
    inc bc
    ld (bc),a
    inc bc
    ld (bc),a
    inc bc
    ld (bc),a
    inc bc
    ld (bc),a
    inc bc
    ld (bc),a
    inc bc
    ld a,(ix+0)
    ld (bc),a
    inc bc
    xor a
    ld (bc),a
    inc bc
    ld (bc),a
    ld hl,0
    xor a
    ret
p614_case_error:
    scf
    ret
p614_gate_noent:
    ld a,E_NOENT
    scf
    ret
p614_gate_notsup:
    ld a,E_NOTSUP
    scf
    ret

; entry: state, ptr, error(0 success), type
p614_cases:
    db 3
    dw p614_s_bin
    db 0,OBJ_DIR
    db 3
    dw p614_s_dot
    db 0,OBJ_DIR
    db 3
    dw p614_s_bad
    db 0,OBJ_TXT
    db 0
    dw p614_s_bin_ls
    db 0,OBJ_BIN
    db 0
    dw p614_s_alt
    db 0,OBJ_DIR
    db 0
    dw p614_s_alt_ls
    db 0,OBJ_TXT
    db 0
    dw p614_s_later
    db 0,OBJ_DIR
    db 0
    dw p614_s_later_ls
    db 0,OBJ_BIN
    db 0
    dw p614_s_direct_txt
    db 0,OBJ_TXT
    db $ff,0,0,0,0
p614_s_bin: db '/','b','i','n',0
p614_s_dot: db '.',0
p614_s_bad: db '/','b','a','d',0
p614_s_bin_ls: db '/','b','i','n','/','l','s',0
p614_s_alt: db '/','a','l','t',0
p614_s_alt_ls: db '/','a','l','t','/','l','s',0
p614_s_later: db '/','l','a','t','e','r',0
p614_s_later_ls: db '/','l','a','t','e','r','/','l','s',0
p614_s_direct_txt: db '/','d','i','r','e','c','t','.','t','x','t',0
p614_gate_end:
    SAVEBIN "p614-gateway.bin",p614_gate,p614_gate_end-p614_gate
""",encoding="utf-8",newline="\n")
    gr=run_command([asm,"--nologo","--lst=p614-gateway.lst","--sym=p614-gateway.sym","p614-gateway.asm"],cwd=build,timeout_seconds=30)
    require(not gr.timed_out and gr.exit_code==0,f"P6.14 gateway fixture failed: {gr.stderr or gr.stdout}")
    if action=="test":
        sy=phase3_open_descriptions._symbols(build/"p614-shell-fixture.sym",("sh_p614_lookup_external","E_NOENT","E_TOOLONG"))
        shell=(build/"p614-shell-fixture.bin").read_bytes(); gate=(build/"p614-gateway.bin").read_bytes()
        def good(cmd,path,want,path_ptr=PATH):
            code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+call_lookup(sy["sh_p614_lookup_external"],path_ptr)+phase1._jp_c(FAIL_PC))
            code+=assert_cstr(OUT,want)+phase1._jp(PASS_PC)
            run_sna(root,bytes(code),patch=patch(shell,gate,cmd,path))
        good(b"ls",b"/bad:/alt:/bin",b"/bin/ls")
        good(b"ls",b":/bin",b"/bin/ls")
        good(b"ls",b"/alt:/later",b"/later/ls")
        good(b"/direct.txt",b"/bin",b"/direct.txt")
        for path,path_ptr in ((b"",PATH),(b"/bin",0)):
            code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+call_lookup(sy["sh_p614_lookup_external"],path_ptr)+b"\xD2"+word(FAIL_PC)+bytes((0xFE,sy["E_NOENT"]&255))+phase1._jp_nz(FAIL_PC)+phase1._jp(PASS_PC))
            run_sna(root,bytes(code),patch=patch(shell,gate,b"ls",path))
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+call_lookup(sy["sh_p614_lookup_external"])+b"\xD2"+word(FAIL_PC)+bytes((0xFE,sy["E_NOENT"]&255))+phase1._jp_nz(FAIL_PC)+phase1._jp(PASS_PC))
        run_sna(root,bytes(code),patch=patch(shell,gate,b"LS",b"/bin"))
        longdirect=b"/"+b"a"*31
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+call_lookup(sy["sh_p614_lookup_external"])+b"\xD2"+word(FAIL_PC)+bytes((0xFE,sy["E_TOOLONG"]&255))+phase1._jp_nz(FAIL_PC)+phase1._jp(PASS_PC))
        run_sna(root,bytes(code),patch=patch(shell,gate,longdirect,b"/bin"))
        assertions += [{"name":"fuse-path-lookup-matrix","passed":True},{"name":"fuse-direct-nonbin-bypasses-type-filter","passed":True},{"name":"fuse-case-sensitive-LS-miss","passed":True},{"name":"fuse-direct-overlength-toolong","passed":True}]
    hashes={
      "v1/src/shell/sh.asm":sha256_file(sp),"v1/build/p614-path.mex1":sha256_file(mp),"v1/build/p614-path.tap":sha256_file(tp),
      "v1/tools-host/test-driver/phase6_path.py":sha256_file(root/"v1/tools-host/test-driver/phase6_path.py"),"v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
      "v1/dist/certification/P6.13.build.json":sha256_file(root/"v1/dist/certification/P6.13.build.json"),"v1/dist/certification/P6.13.test.json":sha256_file(root/"v1/dist/certification/P6.13.test.json"),"v1/dist/media/P6.13/manifest.json":sha256_file(root/"v1/dist/media/P6.13/manifest.json")}
    return [sr,gr],hashes,assertions
