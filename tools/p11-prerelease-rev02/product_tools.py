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
import argparse, hashlib, importlib.util, json, struct, subprocess, sys
from pathlib import Path

def req(v,m):
    if not v: raise SystemExit("ERROR: "+m)
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def crc16(data: bytes)->int:
    crc=0xffff
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            crc=((crc<<1)^0x1021)&0xffff if crc&0x8000 else (crc<<1)&0xffff
    return crc
def mex1(image: bytes, stack=128)->bytes:
    req(0 < len(image) <= 0x7fff,"image size")
    h=bytearray(24); h[:4]=b"MEX1"; h[4]=1; h[5]=0
    h[6:8]=struct.pack("<H",24); h[8:10]=struct.pack("<H",len(image))
    h[10:12]=b"\0\0"; h[12:14]=b"\0\0"; h[14:16]=struct.pack("<H",stack)
    h[16:18]=b"\0\0"; h[18:20]=struct.pack("<H",24+len(image))
    h[20:22]=struct.pack("<H",crc16(image)); h[22:24]=struct.pack("<H",crc16(bytes(h)))
    return bytes(h)+image
def load_maketap(root: Path):
    path=root/"v1/tools-host/maketap/maketap.py"
    spec=importlib.util.spec_from_file_location("zxux_rev02_maketap",path)
    req(spec is not None and spec.loader is not None,"maketap loader")
    mod=importlib.util.module_from_spec(spec); sys.modules[spec.name]=mod; spec.loader.exec_module(mod)
    return mod
def run(argv,cwd):
    p=subprocess.run([str(x) for x in argv],cwd=cwd,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    req(p.returncode==0,"command failed: "+" ".join(map(str,argv))+"\n"+p.stdout+"\n"+p.stderr)
    return p
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--root",type=Path,required=True); ap.add_argument("--output",type=Path,required=True); ns=ap.parse_args()
    root=ns.root.resolve(); out=ns.output.resolve(); out.mkdir(parents=True,exist_ok=True)
    sj=root/"tools/runtime/sjasmplus/bin/sjasmplus"; req(sj.is_file(),"project sjasmplus missing")
    shsrc=root/"v1/src/shell/sh.asm"; sh=shsrc.read_text()
    ccsrc=root/"v1/src/tools/cc.asm"; assrc=root/"tools/as.asm"; ldsrc=root/"tools/ld.asm"
    req("EMIT_P601_SH_IMAGE" in sh and "sh_idle:" in sh,"shell entry fixture changed")
    # Product closure deliberately includes no historical P11PR compiler helper.
    req("EMIT_P11PR_CC_SDK_CORPUS_COMPILER" in ccsrc.read_text(),"historical fixture identity missing")
    asm=out/"sh-product-preflight.asm"
    asm.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "v1/include/zx48ux.inc"
    INCLUDE "v1/src/shell/sh.asm"
    ORG $0000
sh_product_image:
    EMIT_P601_SH_IMAGE
sh_product_end:
    SAVEBIN "sh-product.bin",sh_product_image,sh_product_end-sh_product_image
""",encoding="utf-8",newline="\n")
    run([sj,"--nologo",asm.name],out)
    image=out/"sh-product.bin"; req(image.is_file() and 4 <= image.stat().st_size <= 64,"shell preflight image")
    mex=mex1(image.read_bytes()); (out/"sh.mex1").write_bytes(mex)
    inspect=root/"v1/tools-host/inspect-mex/inspect.py"
    run([sys.executable,inspect,out/"sh.mex1","--base","0x6000"],root)
    mt=load_maketap(root)
    tap=mt.m48o_blocks(mt.M48OObject("sh",mt.M48O_BIN,mt.DIR_BIN,mex))
    (out/"sh.m48o.tap").write_bytes(tap)
    req(tap==mt.m48o_blocks(mt.M48OObject("sh",mt.M48O_BIN,mt.DIR_BIN,mex)),"M48O nondeterminism")
    report={
      "schema":1,"kind":"rev02-product-tools-preflight","status":"PASS",
      "shell":{
        "source":"v1/src/shell/sh.asm","source_sha256":sha(shsrc),
        "image_sha256":sha(image),"mex1_sha256":sha(out/"sh.mex1"),"m48o_tap_sha256":sha(out/"sh.m48o.tap"),
        "entry":"EMIT_P601_SH_IMAGE","semantic_status":"PACKAGING-ONLY-IDLE-ENTRY-NOT-GATE-G-READY"},
      "pending_product_entries":{
        "cc":{"source":"v1/src/tools/cc.asm","source_sha256":sha(ccsrc)},
        "as":{"source":"tools/as.asm","source_sha256":sha(assrc)},
        "ld":{"source":"tools/ld.asm","source_sha256":sha(ldsrc)}},
      "assertions":{
        "deterministic_shell_mex1":"PASS","deterministic_m48o":"PASS","mex1_inspection":"PASS",
        "normal_project_assembler_used":"PASS","p11pr_not_in_product_closure":"PASS",
        "not_claimed_as_real_shell_session":"PASS"}}
    (out/"PRODUCT-TOOLS-PREFLIGHT.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print("REV02 PRODUCT TOOLS PREFLIGHT PASS")
if __name__=="__main__": main()
