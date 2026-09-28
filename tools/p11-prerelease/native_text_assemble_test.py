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

"""Target-native acceptance for the REV17 ordinary textual assembler parser.

This is the Stage-C parser qualification only.  The canonical source is copied
into a synthetic proof SNA here so parser defects can be isolated cheaply.
Stage E separately requires the same bytes to enter through the retained TAP and
real target M48O loader before this native parser is invoked.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
import subprocess
import tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
FIXTURE_BASE=0x4000
SOURCE_BASE=0x68A6
SOURCE_MAX=0xE000-SOURCE_BASE
STACK_TOP=SOURCE_BASE
SNAP_STACK=0x67F0
KERNEL_BASE=0xE000
KERNEL_SIZE=8192
OBJ_SIZE=8216
PASS=0
FAIL=0

class Error(RuntimeError): pass
def require(x,m):
    if not x: raise Error(m)

def symbols(path:Path,names):
    text=path.read_text(encoding="utf-8",errors="replace")
    out={}
    for name in names:
        m=re.search(rf"^{re.escape(name)}:\s+equ\s+0x([0-9a-f]+)\s*$",text,re.I|re.M)
        require(m,f"missing symbol {name}")
        out[name]=int(m.group(1),16)
    return out

def make_sna(entry:int,fixture:bytes,source:bytes,kernel:bytes)->bytes:
    ram=bytearray(0xC000)
    def put(addr,data):
        require(0x4000<=addr and addr+len(data)<=0x10000,f"placement {addr:04x}")
        ram[addr-0x4000:addr-0x4000+len(data)]=data
    put(FIXTURE_BASE,fixture); put(SOURCE_BASE,source); put(KERNEL_BASE,kernel)
    struct.pack_into("<H",ram,SNAP_STACK-0x4000,entry)
    h=bytearray(27); h[0]=0xFE; h[19]=0x04
    struct.pack_into("<H",h,23,SNAP_STACK); h[25]=1; h[26]=0
    return bytes(h)+bytes(ram)

DIAG_MARKER=0xD17A0001

def run_sna(fuse:Path,sna:Path,pass_pc:int,fail_pc:int,diag_addrs:tuple[int,...])->subprocess.CompletedProcess:
    fail_commands=[f"print 0x{DIAG_MARKER:x}","print z80:pc"]
    fail_commands.extend(f"print [0x{addr:04x}]" for addr in diag_addrs)
    cmd=(
      f"breakpoint 0x{pass_pc:04x}\ncommands 1\nexit 0\nend\n"
      f"breakpoint 0x{fail_pc:04x}\ncommands 2\n"
      +"\n".join(fail_commands)
      +"\nexit 1\nend\ncontinue"
    )
    return subprocess.run(
      ["/usr/bin/env","SDL_VIDEODRIVER=dummy","SDL_AUDIODRIVER=dummy",str(fuse),
       "--machine","48","--no-sound","--no-confirm-actions","--debugger-command",cmd,str(sna)],
      cwd=ROOT,text=True,capture_output=True,timeout=90,check=False)

def diagnostic_text(stdout:str,source:bytes)->str:
    values=[int(x,16) for x in re.findall(r"0x([0-9a-f]+)",stdout,re.I)]
    try: i=values.index(DIAG_MARKER)
    except ValueError: return "diagnostics=missing"
    v=values[i+1:i+15]
    if len(v)!=14: return f"diagnostics=truncated values={v!r}"
    pc=v[0]; line=v[1]|(v[2]<<8); pos=v[3]|(v[4]<<8)
    produced=v[5]|(v[6]<<8); logical_pc=v[7]|(v[8]<<8)
    ident,family,op_type,tmp0,tmp1=v[9:14]
    off=line-SOURCE_BASE
    current=b""
    if 0<=off<len(source):
        current=source[off:source.find(b"\n",off) if b"\n" in source[off:] else len(source)]
    return (f"pc=0x{pc:04x} line=0x{line:04x} source_offset={off} "
            f"parse_ptr=0x{pos:04x} produced={produced} logical_pc=0x{logical_pc:04x} "
            f"id={ident} family={family} op_type={op_type} tmp0={tmp0} tmp1={tmp1} "
            f"source_line={current!r}")

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--source",type=Path,required=True)
    ap.add_argument("--kernel",type=Path,required=True)
    ap.add_argument("--report",type=Path,required=True)
    a=ap.parse_args()
    source=a.source.read_bytes(); kernel=a.kernel.read_bytes()
    require(len(source)<=SOURCE_MAX,f"text source too large for 48K fixture: {len(source)} > {SOURCE_MAX}")
    require(len(kernel)==KERNEL_SIZE,"kernel size")
    require(source.endswith(b"\n") and b"\r" not in source and b"\0" not in source,"canonical LF text")

    build=ROOT/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    asm=build/"r17-text-as-fixture.asm"
    asm.write_text(f"""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../../tools/as.asm"
    INCLUDE "../../tools/as_text.asm"

    ORG $4000
r17_txt_fixture_start:
    EMIT_R17_AS_NSP1_OBJ1
    EMIT_R17_AS_TEXT_OBJ1

r17_txt_positive:
    di
    ld sp,$68A6
    ld hl,$68A6
    ld de,{len(source)}
    call r17_as_text_obj1_inplace
    jp c,r17_txt_fail
    ld de,{OBJ_SIZE}
    or a
    sbc hl,de
    jp nz,r17_txt_fail
    ld hl,$68BE
    ld de,$E000
    ld bc,8192
r17_txt_cmp:
    ld a,(de)
    cp (hl)
    jp nz,r17_txt_fail
    inc de
    inc hl
    dec bc
    ld a,b
    or c
    jp nz,r17_txt_cmp
    jp r17_txt_pass

r17_txt_negative:
    di
    ld sp,$68A6
    ld hl,$68A6
    ld de,{len(source)}
    call r17_as_text_obj1_inplace
    jp c,r17_txt_fail
    ld hl,$68BE
    ld de,$E000
    ld bc,8192
r17_txt_neg_cmp:
    ld a,(de)
    cp (hl)
    jr nz,r17_txt_pass
    inc de
    inc hl
    dec bc
    ld a,b
    or c
    jp nz,r17_txt_neg_cmp
    jp r17_txt_fail

r17_txt_pass:
    jr r17_txt_pass
r17_txt_fail:
    jr r17_txt_fail
r17_txt_fixture_end:
    ASSERT r17_txt_fixture_end <= $66A6
    SAVEBIN "r17-text-as-fixture.bin",r17_txt_fixture_start,r17_txt_fixture_end-r17_txt_fixture_start
""",encoding="utf-8",newline="\n")
    sj=ROOT/"tools/runtime/sjasmplus/bin/sjasmplus"
    require(sj.is_file(),"project sjasmplus missing")
    p=subprocess.run([str(sj),"--nologo","--sym=r17-text-as-fixture.sym",asm.name],cwd=build,text=True,capture_output=True,timeout=60)
    require(p.returncode==0,f"fixture assembly failed:\n{p.stdout}\n{p.stderr}")
    fixture=(build/"r17-text-as-fixture.bin").read_bytes()
    sy=symbols(build/"r17-text-as-fixture.sym",(
        "r17_txt_positive","r17_txt_negative","r17_txt_pass","r17_txt_fail",
        "r17_txt_line_start","r17_txt_p","r17_as_produced","r17_as_pc",
        "r17_txt_id","r17_txt_family","r17_txt_op_type","r17_txt_tmp0","r17_txt_tmp1",
    ))
    require(FIXTURE_BASE+len(fixture)<=0x66A6,f"fixture too large: {len(fixture)}")
    diag_addrs=(
        sy["r17_txt_line_start"],sy["r17_txt_line_start"]+1,
        sy["r17_txt_p"],sy["r17_txt_p"]+1,
        sy["r17_as_produced"],sy["r17_as_produced"]+1,
        sy["r17_as_pc"],sy["r17_as_pc"]+1,
        sy["r17_txt_id"],sy["r17_txt_family"],sy["r17_txt_op_type"],
        sy["r17_txt_tmp0"],sy["r17_txt_tmp1"],
    )

    fuse=ROOT/"tools/runtime/fuse/bin/fuse"; require(fuse.is_file(),"project FUSE missing")
    mutated=bytearray(source)
    needle=b"jp $e006\n"
    pos=mutated.find(needle)
    require(pos>=0,"controlled mutation anchor missing")
    mutated[pos+len(b"jp $e00")]=ord("7")
    require(bytes(mutated)!=source,"mutation unchanged")

    with tempfile.TemporaryDirectory(prefix="zxux-r17-text-") as td:
        td=Path(td)
        sp=td/"positive.sna"; sp.write_bytes(make_sna(sy["r17_txt_positive"],fixture,source,kernel))
        rp=run_sna(fuse,sp,sy["r17_txt_pass"],sy["r17_txt_fail"],diag_addrs)
        require(rp.returncode==0,
                f"positive target parser failed exit={rp.returncode}: "
                f"{diagnostic_text(rp.stdout,source)} stdout={rp.stdout!r} stderr={rp.stderr!r}")
        sn=td/"negative.sna"; sn.write_bytes(make_sna(sy["r17_txt_negative"],fixture,bytes(mutated),kernel))
        rn=run_sna(fuse,sn,sy["r17_txt_pass"],sy["r17_txt_fail"],diag_addrs)
        require(rn.returncode==0,
                f"negative target parser oracle failed exit={rn.returncode}: "
                f"{diagnostic_text(rn.stdout,bytes(mutated))} stdout={rn.stdout!r} stderr={rn.stderr!r}")

    report={
      "schema":1,"kind":"REV17-native-textual-assembler-parser",
      "source_size":len(source),"source_sha256":hashlib.sha256(source).hexdigest(),
      "kernel_size":len(kernel),"kernel_sha256":hashlib.sha256(kernel).hexdigest(),
      "fixture_size":len(fixture),"obj1_size":OBJ_SIZE,
      "assertions":{
        "ordinary_lf_text_parsed_on_target":"PASS",
        "documented_mnemonics_and_directives_only":"PASS",
        "native_semantic_encoder_emitted_obj1":"PASS",
        "native_obj1_text_equals_exact_8192_kernel":"PASS",
        "controlled_source_mutation_changes_native_output":"PASS",
        "inplace_emission_never_overtook_unconsumed_source":"PASS",
      }}
    a.report.parent.mkdir(parents=True,exist_ok=True)
    a.report.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8",newline="\n")
    print(f"fixture_size={len(fixture)}")
    print("ZX-UX REV17 NATIVE TEXTUAL ASSEMBLER PASS")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
