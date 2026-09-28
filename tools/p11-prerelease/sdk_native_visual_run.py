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

"""Run all 30 source-tape-built visual MEX1 files and retain real SCR/PNG proof."""

from __future__ import annotations
import argparse
import hashlib
import json
import re
import struct
import subprocess
import tempfile
import zlib
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"v1/tools-host/test-driver"))

import sdk_acquire as sdk
import sdk_native_process_run as proc
from fuse_harness import FAIL_PC, PASS_PC, make_sna

FONT=0xD000
SCREEN=6912
PALETTE_NORMAL=((0,0,0),(0,0,205),(205,0,0),(205,0,205),(0,205,0),(0,205,205),(205,205,0),(205,205,205))
PALETTE_BRIGHT=((0,0,0),(0,0,255),(255,0,0),(255,0,255),(0,255,0),(0,255,255),(255,255,0),(255,255,255))

class Error(RuntimeError): pass
def req(v,m):
    if not v: raise Error(m)
def sha(b): return hashlib.sha256(b).hexdigest()

def bitmap_offset(x,y):
    return ((y&0xC0)<<5)|((y&0x07)<<8)|((y&0x38)<<2)|(x>>3)

def png_chunk(kind,data):
    return struct.pack(">I",len(data))+kind+data+struct.pack(">I",zlib.crc32(kind+data)&0xffffffff)

def render_png(scr):
    req(len(scr)==SCREEN,"SCR length")
    raw=bytearray()
    for y in range(192):
        raw.append(0)
        for x in range(256):
            a=scr[6144+(y>>3)*32+(x>>3)]
            ink=a&7; paper=(a>>3)&7; bright=(a>>6)&1
            bit=bool(scr[bitmap_offset(x,y)]&(0x80>>(x&7)))
            raw.extend((PALETTE_BRIGHT if bright else PALETTE_NORMAL)[ink if bit else paper])
    ihdr=struct.pack(">IIBBBBB",256,192,8,2,0,0,0)
    return b"\x89PNG\r\n\x1a\n"+png_chunk(b"IHDR",ihdr)+png_chunk(b"IDAT",zlib.compress(bytes(raw),9))+png_chunk(b"IEND",b"")

def visual_regions(sy,exe_name,mex,font):
    path=f"/bin/{exe_name}".encode("ascii")
    arg=proc.p210._arg1(path)
    env=proc.p210.ENV1_EMPTY
    desc=proc.p210._proc1(path_ptr=proc.PATH,arg_ptr=proc.ARG,arg_len=len(arg),env_ptr=proc.ENV,env_len=len(env))
    record=proc.p210._record(exe_name.encode("ascii"),2,proc.MEX,len(mex))
    return (
        (proc.PATH,path+b"\0"),
        (proc.ARG,arg),
        (proc.ENV,env),
        (proc.PROC,desc),
        (proc.MEX,mex),
        (proc.RECORD,record),
        (FONT,font),
        (sy["process_table"],proc.p222._process_table()),
        (sy["current_pid"],b"\x01"),
        (sy["open_description_table"],proc.p222._open_descriptions()),
        (sy["memory_free_extents"],proc.free_extents()),
        (sy["memory_live_allocations"],b"\x00\x00"),
        (sy["tty_input_owner"],b"\x01"),
        (sy["p11pr_exit_seen"],b"\x00"),
    )

def bootstrap(sy):
    code=bytearray(b"\xF3\x31"+proc.word(proc.TEST_STACK))
    code+=proc.call(sy["zx48_process_links_init"])+proc.jp_c(FAIL_PC)
    code+=b"\x21"+proc.word(proc.PROC)
    code+=bytes((0x3E,sy["SYS_SPAWN"]&0xff))
    code+=proc.call(sy["p11pr_gateway"])+proc.jp_c(FAIL_PC)
    code+=b"\x7C\xB7"+proc.jp_nz(FAIL_PC)
    code+=b"\x7D\xFE\x02"+proc.jp_nz(FAIL_PC)
    child=sy["process_table"]+2*proc.PROC_DESC_SIZE+proc.PROC_STATE
    code+=b"\x3A"+proc.word(child)+bytes((0xFE,proc.PROC_READY))+proc.jp_nz(FAIL_PC)
    code+=proc.call(sy["p11pr_run_child"])
    code+=b"\xC3"+proc.word(FAIL_PC)
    return bytes(code)

def run_visual(fixture,sy,mex,exe_name,font):
    sna=make_sna(bootstrap(sy),patch=proc.patch(fixture,visual_regions(sy,exe_name,mex,font)))
    fuse=ROOT/"tools/runtime/fuse/bin/fuse"
    fmfconv=ROOT/"tools/runtime/fuse-utils/bin/fmfconv"
    req(fuse.is_file() and fmfconv.is_file(),"project Fuse runtime missing")
    dbg=f"breakpoint 0x{PASS_PC:04x}\ncommands 1\nexit 0\nend\nbreakpoint 0x{FAIL_PC:04x}\ncommands 2\nexit 1\nend\ncontinue"
    with tempfile.TemporaryDirectory(prefix="zxux-p11pr-visual-") as td:
        td=Path(td); sp=td/"visual.sna"; movie=td/"visual.fmf"; sp.write_bytes(sna)
        r=subprocess.run(["/usr/bin/env","SDL_VIDEODRIVER=dummy","SDL_AUDIODRIVER=dummy",str(fuse),
            "--machine","48","--no-sound","--no-confirm-actions","--movie-start",str(movie),
            "--debugger-command",dbg,str(sp)],cwd=ROOT,text=True,capture_output=True,timeout=45)
        req(r.returncode==0,f"{exe_name} visual process failed: {r.stdout!r} {r.stderr!r}")
        req(movie.is_file() and movie.stat().st_size>0,f"{exe_name} FMF missing")
        r=subprocess.run([str(fmfconv),"-S","-y",str(movie),str(td/"frame.scr")],
            cwd=ROOT,text=True,capture_output=True,timeout=30)
        req(r.returncode==0,f"{exe_name} SCR extraction failed: {r.stderr!r}")
        frames=sorted(td.glob("frame-*.scr"))
        req(frames,f"{exe_name} no SCR frames")
        frame=frames[-1]
        scr=frame.read_bytes(); req(len(scr)==SCREEN,f"{exe_name} SCR size")
        m=re.search(r"-(\d+)$",frame.stem); req(m,f"{exe_name} frame number")
        return scr,int(m.group(1))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",type=Path,required=True)
    ap.add_argument("--native",type=Path,required=True)
    ap.add_argument("--native-report",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    ap.add_argument("--report",type=Path,required=True)
    a=ap.parse_args()
    release=json.loads((a.root/"SDK-RELEASE.json").read_text())
    req((release.get("tag"),release.get("commit"),release.get("tree"))==(sdk.TAG,sdk.COMMIT,sdk.TREE),"SDK identity drift")
    nr=json.loads(a.native_report.read_text())
    req(nr.get("program_count")==30 and len(nr.get("programs",[]))==30,"visual native matrix")
    by={(x["category"],x["program"]):x for x in nr["programs"]}
    fixture,sy=proc.build_fixture()
    font=(ROOT/"v1/assets/font4x8-zxux.bin").read_bytes()
    req(len(font)==392 and font[:4]==b"F4X8","font identity")
    rows=[]
    for category,name in sdk.programs():
        _,_,exe_name=sdk.target_names(name)
        prior=by[(category,name)]
        mex_path=a.native/category/(exe_name+".visual")
        mex=mex_path.read_bytes()
        req(sha(mex)==prior["native_mex1_sha256"],f"{category}/{name} visual MEX1 drift")
        scr,frame=run_visual(fixture,sy,mex,exe_name,font)
        req(any(scr[:6144]),f"{category}/{name} blank bitmap")
        req(set(scr[6144:])=={7},f"{category}/{name} unexpected attributes")
        png=render_png(scr)
        out=a.output/category
        out.mkdir(parents=True,exist_ok=True)
        (out/f"{name}.scr").write_bytes(scr)
        (out/f"{name}.png").write_bytes(png)
        ref=a.root/f"reference-png/{category}/{name}.png"
        rows.append({"category":category,"program":name,"target_executable":exe_name,
            "native_visual_mex1_sha256":sha(mex),"capture_frame":frame,
            "capture_checkpoint":"final stable target screen immediately before SYS_EXIT",
            "scr_size":len(scr),"scr_sha256":sha(scr),"png_sha256":sha(png),
            "reference_png_sha256":sha(ref.read_bytes()),"spawn":"PASS","process_started":"PASS",
            "sys_exit_reached":"PASS","screen_ram_capture":"PASS","deterministic_png_from_scr":"PASS"})
    req(len(rows)==30,"not all 30 visual runs passed")
    report={"schema":1,"kind":"phase11-pre-release-sdk-native-visual-run","program_count":30,
        "programs":rows,"assertions":{"all_30_visual_executables_are_target_native_outputs":"PASS",
        "all_30_launch_through_admitted_sys_spawn_transaction":"PASS",
        "all_30_capture_exact_6912_byte_spectrum_screens":"PASS",
        "all_30_pngs_are_deterministic_renders_of_retained_scr":"PASS",
        "no_host_synthesized_screen_output":"PASS"}}
    a.report.parent.mkdir(parents=True,exist_ok=True)
    a.report.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8",newline="\n")
    print("P11 PRE-RELEASE SDK NATIVE VISUAL RUN PASS")
    return 0

if __name__=="__main__": raise SystemExit(main())
