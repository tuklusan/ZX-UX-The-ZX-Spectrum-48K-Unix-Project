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

"""Target-native exact-source cc admission preflight for SDK 1.0.2.

This isolates native cc qualification. The host places already-verified exact
source bytes in a diagnostic SNA; it does not compile or link them. Gate G still
requires the same bytes to arrive through the retained TAP and continue through
native ld and ZX-UX process execution.
"""
from __future__ import annotations
import argparse,hashlib,json,re,struct,subprocess,tempfile
from pathlib import Path
import sdk_acquire as sdk

ROOT=Path(__file__).resolve().parents[2]
FIXTURE=0x4000; OUTPUT=0x7000; SOURCE=0x8000; STACK=0x6F00; CAP=256
PASS_MARK=0xD17C0002; DUMP_MARK=0xD17C0001

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
    p=b/"p11pr-sdk-cc-preflight.asm"
    p.write_text(f"""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/tools/cc.asm"
    ORG $4000
p11pr_cc_start:
    EMIT_P1128_CC_OBJ1_WRITER
    EMIT_P11PR_CC_SDK_CORPUS_COMPILER
p11pr_cc_source_len: dw 0
p11pr_cc_positive:
    di
    ld sp,$6F00
    ld hl,$8000
    ld bc,(p11pr_cc_source_len)
    ld de,$7000
    ld ix,256
    call cc_p11pr_sdk_compile
    jp c,p11pr_cc_fail
    ld a,h
    or l
    jp z,p11pr_cc_fail
    ld hl,$7000
    ld a,(hl)
    cp 'O'
    jp nz,p11pr_cc_fail
    inc hl
    ld a,(hl)
    cp 'B'
    jp nz,p11pr_cc_fail
    inc hl
    ld a,(hl)
    cp 'J'
    jp nz,p11pr_cc_fail
    inc hl
    ld a,(hl)
    cp '1'
    jp nz,p11pr_cc_fail
    ld hl,($7008)
    ld de,CC_P11PR_TEXT_SIZE
    or a
    sbc hl,de
    jp nz,p11pr_cc_fail
    jp p11pr_cc_pass
p11pr_cc_negative:
    di
    ld sp,$6F00
    ld a,$A5
    ld ($7000),a
    ld hl,$8000
    ld bc,(p11pr_cc_source_len)
    ld de,$7000
    ld ix,256
    call cc_p11pr_sdk_compile
    jp nc,p11pr_cc_fail
    cp E_FORMAT
    jp nz,p11pr_cc_fail
    ld a,($7000)
    cp $A5
    jp nz,p11pr_cc_fail
    jp p11pr_cc_pass
p11pr_cc_pass:
    jp p11pr_cc_pass
p11pr_cc_fail:
    jp p11pr_cc_fail
p11pr_cc_end:
    ASSERT p11pr_cc_end <= $6E00
    SAVEBIN "p11pr-sdk-cc-preflight.bin",p11pr_cc_start,p11pr_cc_end-p11pr_cc_start
""",encoding="utf-8",newline="\n")
    sj=ROOT/"tools/runtime/sjasmplus/bin/sjasmplus";req(sj.is_file(),"project sjasmplus missing")
    r=subprocess.run([str(sj),"--nologo","--sym=p11pr-sdk-cc-preflight.sym",p.name],cwd=b,text=True,capture_output=True,timeout=60)
    req(r.returncode==0,f"fixture assembly failed:\n{r.stdout}\n{r.stderr}")
    blob=(b/"p11pr-sdk-cc-preflight.bin").read_bytes()
    s=syms(b/"p11pr-sdk-cc-preflight.sym",("p11pr_cc_positive","p11pr_cc_negative","p11pr_cc_pass","p11pr_cc_fail","p11pr_cc_source_len"))
    req(FIXTURE+len(blob)<=0x6E00,f"fixture too large: {len(blob)}")
    return blob,s

def sna(entry,fixture,s,source):
    req(SOURCE+len(source)<0xE000,"source overlaps kernel")
    ram=bytearray(0xC000)
    ram[FIXTURE-0x4000:FIXTURE-0x4000+len(fixture)]=fixture
    ram[SOURCE-0x4000:SOURCE-0x4000+len(source)]=source
    struct.pack_into("<H",ram,s["p11pr_cc_source_len"]-0x4000,len(source))
    struct.pack_into("<H",ram,STACK-0x4000,entry)
    h=bytearray(27);h[0]=0xFE;h[19]=0x04;struct.pack_into("<H",h,23,STACK);h[25]=1
    return bytes(h)+bytes(ram)

def dbg(s,dump):
    x=[f"breakpoint 0x{s['p11pr_cc_pass']:04x}","commands 1",f"print 0x{PASS_MARK:x}"]
    if dump:
        x.append(f"print 0x{DUMP_MARK:x}")
        x += [f"print [0x{a:04x}]" for a in range(OUTPUT,OUTPUT+CAP)]
    x += ["exit 0","end",f"breakpoint 0x{s['p11pr_cc_fail']:04x}","commands 2","exit 1","end","continue"]
    return "\n".join(x)

def run(fuse,path,s,dump):
    return subprocess.run(["/usr/bin/env","SDL_VIDEODRIVER=dummy","SDL_AUDIODRIVER=dummy",str(fuse),
      "--machine","48","--no-sound","--no-confirm-actions","--debugger-command",dbg(s,dump),str(path)],
      cwd=ROOT,text=True,capture_output=True,timeout=45)

def dumped(stdout):
    v=[int(x,16) for x in re.findall(r"0x([0-9a-f]+)",stdout,re.I)]
    req(PASS_MARK in v and DUMP_MARK in v,"target dump markers missing")
    i=v.index(DUMP_MARK);d=v[i+1:i+1+CAP]
    req(len(d)==CAP and all(0<=x<=255 for x in d),"target dump truncated")
    return bytes(d)

def objlen(d):
    req(d[:4]==b"OBJ1" and d[4]==1,"native OBJ1 identity")
    text,bss,ns,nr=struct.unpack_from("<HHHH",d,8)
    so,ro=struct.unpack_from("<HH",d,16)
    req((text,bss,ns,nr)==(14,0,1,0),"native OBJ1 shape")
    req(so==24+text and ro==so+16,"native OBJ1 offsets")
    return ro

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--root",type=Path,required=True);ap.add_argument("--output",type=Path,required=True);ap.add_argument("--report",type=Path,required=True);a=ap.parse_args()
    m=json.loads((a.root/"SDK-RELEASE.json").read_text())
    req((m.get("tag"),m.get("commit"),m.get("tree"))==(sdk.TAG,sdk.COMMIT,sdk.TREE),"SDK identity drift")
    fixture,s=build_fixture();fuse=ROOT/"tools/runtime/fuse/bin/fuse";req(fuse.is_file(),"project FUSE missing")
    a.output.mkdir(parents=True,exist_ok=True);rows=[]
    with tempfile.TemporaryDirectory(prefix="zxux-p11pr-sdkcc-") as td:
        td=Path(td)
        for category,name in sdk.programs():
            src=(a.root/f"usr/src/{category}/{name}.c").read_bytes()
            source_name,obj_name,exe_name=sdk.target_names(name)
            p=td/f"{name}.sna";p.write_bytes(sna(s["p11pr_cc_positive"],fixture,s,src))
            r=run(fuse,p,s,True);req(r.returncode==0,f"{category}/{name} native cc failed: {r.stdout!r} {r.stderr!r}")
            d=dumped(r.stdout);n=objlen(d);obj=d[:n]
            out=a.output/category/obj_name;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(obj)
            bad=bytearray(src);bad[-1]^=1
            p=td/f"{name}-bad.sna";p.write_bytes(sna(s["p11pr_cc_negative"],fixture,s,bytes(bad)))
            r=run(fuse,p,s,False);req(r.returncode==0,f"{category}/{name} mutation rejection failed")
            rows.append({"category":category,"program":name,"source_size":len(src),"source_sha256":sha(src),
              "target_source":source_name,"target_object":obj_name,"target_executable":exe_name,
              "native_obj1_size":len(obj),"native_obj1_sha256":sha(obj),"compile":"PASS","mutation_rejected":"PASS"})
    req(len(rows)==30,"not all 30 programs compiled")
    report={"schema":1,"kind":"phase11-pre-release-sdk-native-cc-preflight","program_count":30,"fixture_size":len(fixture),"programs":rows,
      "assertions":{"all_30_exact_sources_consumed_by_target_native_cc":"PASS","all_30_native_obj1_extracted":"PASS",
      "all_30_changed_source_negatives_rejected":"PASS","host_compile_or_link_not_used":"PASS",
      "not_claimed_as_gate_g_without_tape_ld_process_execution":"PASS"}}
    a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8",newline="\n")
    print("P11 PRE-RELEASE SDK NATIVE CC PREFLIGHT PASS")
    return 0
if __name__=="__main__":raise SystemExit(main())
