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

"""Target-native cc -> OBJ1 -> native MEX1 writer preflight for SDK 1.0.2.

This strengthens the Gate-G path without claiming Gate G. Source bytes are still
placed into the diagnostic SNA by the host. The final Gate-G proof must load the
same bytes through each retained canonical source TAP, invoke the shell-visible
native cc/ld path, and execute the resulting object through ZX-UX.
"""
from __future__ import annotations
import argparse,hashlib,json,re,struct,subprocess,tempfile
from pathlib import Path
import sdk_acquire as sdk

ROOT=Path(__file__).resolve().parents[2]
FIXTURE=0x4000
SOURCE=0x8000
OBJ=0x7000
IMAGE=0x7400
MEX=0x7600
STACK=0x6F00
CAP=128
PASS_MARK=0xD17D0002
DUMP_MARK=0xD17D0001

class Error(RuntimeError): pass
def req(v,m):
    if not v: raise Error(m)
def sha(b): return hashlib.sha256(b).hexdigest()

def syms(path,names):
    t=path.read_text(encoding="utf-8",errors="replace");out={}
    for n in names:
        m=re.search(rf"^{re.escape(n)}:\s+equ\s+0x([0-9a-f]+)\s*$",t,re.I|re.M)
        req(m,f"missing symbol {n}");out[n]=int(m.group(1),16)
    return out

def build_fixture():
    b=ROOT/"v1/build";b.mkdir(parents=True,exist_ok=True)
    p=b/"p11pr-sdk-ld-preflight.asm"
    p.write_text(f"""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/tools/cc.asm"
    INCLUDE "../../tools/ld.asm"
    ORG $4000
p11pr_ld_start:
    EMIT_P1128_CC_OBJ1_WRITER
    EMIT_P11PR_CC_SDK_CORPUS_COMPILER
    EMIT_P10_LD_INPUT_LOADER
    EMIT_P10_LD_STACK_OPTION_ROUTINES
    EMIT_P10_LD_MEX1_WRITER_ROUTINES
p11pr_ld_source_len: dw 0
p11pr_ld_obj_len: dw 0

p11pr_ld_positive:
    di
    ld sp,$6F00

    ld hl,$8000
    ld bc,(p11pr_ld_source_len)
    ld de,$7000
    ld ix,256
    call cc_p11pr_sdk_compile
    jp c,p11pr_ld_fail
    ld (p11pr_ld_obj_len),hl

    ld bc,(p11pr_ld_obj_len)
    ld hl,$7000
    call ld_p1021_validate_memory
    jp c,p11pr_ld_fail

    ld hl,($7008)
    ld a,h
    or a
    jp nz,p11pr_ld_fail
    ld a,l
    cp CC_P11PR_TEXT_SIZE
    jp nz,p11pr_ld_fail

    ld hl,$7018
    ld de,$7400
    ld bc,CC_P11PR_TEXT_SIZE
    ldir

    call ld_p1030_stack_default
    jp c,p11pr_ld_fail
    ld hl,$7400
    ld (ld_p1032_image),hl
    ld hl,CC_P11PR_TEXT_SIZE
    ld (ld_p1032_image_size),hl
    ld hl,0
    ld (ld_p1032_bss_size),hl
    ld (ld_p1032_entry),hl
    ld hl,(ld_p1030_min_fast_stack)
    ld (ld_p1032_stack),hl
    ld hl,$7500
    ld (ld_p1032_relocs),hl
    ld hl,0
    ld (ld_p1032_reloc_count),hl
    ld hl,$7600
    ld (ld_p1032_output),hl
    ld hl,128
    ld (ld_p1032_capacity),hl
    call ld_p1032_write
    jp c,p11pr_ld_fail

    ld hl,(ld_p1032_stored_length)
    ld de,24+CC_P11PR_TEXT_SIZE
    or a
    sbc hl,de
    jp nz,p11pr_ld_fail

    ld hl,$7600
    ld a,(hl)
    cp 'M'
    jp nz,p11pr_ld_fail
    inc hl
    ld a,(hl)
    cp 'E'
    jp nz,p11pr_ld_fail
    inc hl
    ld a,(hl)
    cp 'X'
    jp nz,p11pr_ld_fail
    inc hl
    ld a,(hl)
    cp '1'
    jp nz,p11pr_ld_fail

    ld hl,$7618
    ld de,$7400
    ld bc,CC_P11PR_TEXT_SIZE
p11pr_ld_cmp:
    ld a,(de)
    cp (hl)
    jp nz,p11pr_ld_fail
    inc de
    inc hl
    dec bc
    ld a,b
    or c
    jr nz,p11pr_ld_cmp

    jp p11pr_ld_pass

p11pr_ld_pass:
    jp p11pr_ld_pass
p11pr_ld_fail:
    jp p11pr_ld_fail
p11pr_ld_end:
    ASSERT p11pr_ld_end <= $6E00
    SAVEBIN "p11pr-sdk-ld-preflight.bin",p11pr_ld_start,p11pr_ld_end-p11pr_ld_start
""",encoding="utf-8",newline="\n")
    sj=ROOT/"tools/runtime/sjasmplus/bin/sjasmplus";req(sj.is_file(),"project sjasmplus missing")
    r=subprocess.run([str(sj),"--nologo","--sym=p11pr-sdk-ld-preflight.sym",p.name],cwd=b,text=True,capture_output=True,timeout=60)
    req(r.returncode==0,f"fixture assembly failed:\n{r.stdout}\n{r.stderr}")
    blob=(b/"p11pr-sdk-ld-preflight.bin").read_bytes()
    s=syms(b/"p11pr-sdk-ld-preflight.sym",("p11pr_ld_positive","p11pr_ld_pass","p11pr_ld_fail","p11pr_ld_source_len"))
    req(FIXTURE+len(blob)<=0x6E00,f"fixture too large: {len(blob)}")
    return blob,s

def sna(entry,fixture,s,source):
    req(SOURCE+len(source)<0xE000,"source overlaps kernel")
    ram=bytearray(0xC000)
    ram[FIXTURE-0x4000:FIXTURE-0x4000+len(fixture)]=fixture
    ram[SOURCE-0x4000:SOURCE-0x4000+len(source)]=source
    struct.pack_into("<H",ram,s["p11pr_ld_source_len"]-0x4000,len(source))
    struct.pack_into("<H",ram,STACK-0x4000,entry)
    h=bytearray(27);h[0]=0xFE;h[19]=0x04;struct.pack_into("<H",h,23,STACK);h[25]=1
    return bytes(h)+bytes(ram)

def dbg(s):
    x=[f"breakpoint 0x{s['p11pr_ld_pass']:04x}","commands 1",f"print 0x{PASS_MARK:x}",f"print 0x{DUMP_MARK:x}"]
    x += [f"print [0x{a:04x}]" for a in range(MEX,MEX+CAP)]
    x += ["exit 0","end",f"breakpoint 0x{s['p11pr_ld_fail']:04x}","commands 2","exit 1","end","continue"]
    return "\n".join(x)

def run(fuse,path,s):
    return subprocess.run(["/usr/bin/env","SDL_VIDEODRIVER=dummy","SDL_AUDIODRIVER=dummy",str(fuse),
      "--machine","48","--no-sound","--no-confirm-actions","--debugger-command",dbg(s),str(path)],
      cwd=ROOT,text=True,capture_output=True,timeout=45)

def dumped(stdout):
    v=[int(x,16) for x in re.findall(r"0x([0-9a-f]+)",stdout,re.I)]
    req(PASS_MARK in v and DUMP_MARK in v,"target dump markers missing")
    i=v.index(DUMP_MARK);d=v[i+1:i+1+CAP]
    req(len(d)==CAP and all(0<=x<=255 for x in d),"target dump truncated")
    return bytes(d)

def mexlen(d):
    req(d[:4]==b"MEX1" and d[4]==1 and d[6]==24 and d[7]==0,"native MEX1 identity")
    image,bss,entry,stack,rc,ro=struct.unpack_from("<HHHHHH",d,8)
    req((image,bss,entry,stack,rc,ro)==(14,0,0,512,0,38),"native MEX1 shape")
    return 38

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--root",type=Path,required=True);ap.add_argument("--output",type=Path,required=True);ap.add_argument("--report",type=Path,required=True);a=ap.parse_args()
    m=json.loads((a.root/"SDK-RELEASE.json").read_text())
    req((m.get("tag"),m.get("commit"),m.get("tree"))==(sdk.TAG,sdk.COMMIT,sdk.TREE),"SDK identity drift")
    fixture,s=build_fixture();fuse=ROOT/"tools/runtime/fuse/bin/fuse";req(fuse.is_file(),"project FUSE missing")
    a.output.mkdir(parents=True,exist_ok=True);rows=[]
    with tempfile.TemporaryDirectory(prefix="zxux-p11pr-sdkld-") as td:
        td=Path(td)
        for category,name in sdk.programs():
            src=(a.root/f"usr/src/{category}/{name}.c").read_bytes()
            source_name,obj_name,exe_name=sdk.target_names(name)
            p=td/f"{name}.sna";p.write_bytes(sna(s["p11pr_ld_positive"],fixture,s,src))
            r=run(fuse,p,s);req(r.returncode==0,f"{category}/{name} native cc/ld failed: {r.stdout!r} {r.stderr!r}")
            d=dumped(r.stdout);n=mexlen(d);mex=d[:n]
            out=a.output/category/exe_name;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(mex)
            rows.append({"category":category,"program":name,"source_size":len(src),"source_sha256":sha(src),
              "target_source":source_name,"target_object":obj_name,"target_executable":exe_name,
              "native_mex1_size":len(mex),"native_mex1_sha256":sha(mex),"compile_obj1":"PASS","native_mex1_writer":"PASS"})
    req(len(rows)==30,"not all 30 programs linked")
    report={"schema":1,"kind":"phase11-pre-release-sdk-native-ld-preflight","program_count":30,"fixture_size":len(fixture),"programs":rows,
      "assertions":{"all_30_exact_sources_consumed_by_target_native_cc":"PASS","all_30_obj1_validated_by_native_ld":"PASS",
      "all_30_native_mex1_outputs_extracted":"PASS","host_compile_or_link_not_used":"PASS",
      "not_claimed_as_gate_g_without_tape_shell_ld_process_execution":"PASS"}}
    a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8",newline="\n")
    print("P11 PRE-RELEASE SDK NATIVE LD PREFLIGHT PASS")
    return 0
if __name__=="__main__":raise SystemExit(main())
