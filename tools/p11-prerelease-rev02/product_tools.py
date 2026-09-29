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
def mex1(image: bytes, stack=128, bss=0, relocations=())->bytes:
    req(0 < len(image) <= 0x7fff,"image size")
    req(0 <= bss <= 0x7fff and len(image)+bss <= 0x8000,"image+bss size")
    relocs=tuple(int(x) for x in relocations)
    prev=-2
    for off in relocs:
        req(0 <= off <= len(image)-2,"relocation range")
        req(off >= prev+2,"relocation order/overlap")
        word=struct.unpack_from("<H",image,off)[0]
        req(word <= len(image)+bss,"relocation addend range")
        prev=off
    relblob=b"".join(struct.pack("<H",x) for x in relocs)
    h=bytearray(24); h[:4]=b"MEX1"; h[4]=1; h[5]=0
    h[6:8]=struct.pack("<H",24); h[8:10]=struct.pack("<H",len(image))
    h[10:12]=struct.pack("<H",bss); h[12:14]=b"\0\0"; h[14:16]=struct.pack("<H",stack)
    h[16:18]=struct.pack("<H",len(relocs)); h[18:20]=struct.pack("<H",24+len(image))
    body=image+relblob
    h[20:22]=struct.pack("<H",crc16(body)); h[22:24]=struct.pack("<H",crc16(bytes(h)))
    return bytes(h)+body

def build_relocatable(sj: Path, out: Path, name: str, include_lines: str, emit_lines: str):
    def source(origin: int, suffix: str, with_table: bool)->str:
        table=(f"{name}_product_relocs:\n    RELOCATE_TABLE\n"
               f"{name}_product_relocs_end:\n") if with_table else ""
        reloc_save=(f'    SAVEBIN "{name}-product.reloc",{name}_product_relocs,'
                    f'{name}_product_relocs_end-{name}_product_relocs\n') if with_table else ""
        return f"""    DEVICE ZXSPECTRUM48
{include_lines}    ORG ${origin:04X}
    RELOCATE_START
{name}_product_image:
{emit_lines}{name}_product_end:
    RELOCATE_END
{table}    SAVEBIN "{name}-product{suffix}.bin",{name}_product_image,{name}_product_end-{name}_product_image
{reloc_save}"""

    asm=out/f"{name}-product.asm"
    asm.write_text(source(0,"",True),encoding="utf-8",newline="\n")
    run([sj,"--nologo",asm.name],out)
    base_asm=out/f"{name}-product-base.asm"
    base_asm.write_text(source(0x1000,"-base",False),encoding="utf-8",newline="\n")
    run([sj,"--nologo",base_asm.name],out)

    image=out/f"{name}-product.bin"
    image_bytes=image.read_bytes()
    base_bytes=(out/f"{name}-product-base.bin").read_bytes()
    req(len(base_bytes)==len(image_bytes),f"{name} two-origin image size drift")
    reloc_blob=(out/f"{name}-product.reloc").read_bytes()
    req(len(reloc_blob)%2==0,f"{name} relocation table size")
    raw_relocs=struct.unpack("<"+"H"*(len(reloc_blob)//2),reloc_blob) if reloc_blob else ()
    # The bundled assembler can conservatively tag fixed EQU operands.  Prove
    # each retained relocation by an independent second-origin assembly: a
    # true image-base word changes by exactly +0x1000; fixed ROM/syscall and
    # numeric constants remain byte-identical and are excluded.
    relocs=[]
    for off in raw_relocs:
        req(0 <= off <= len(image_bytes)-2,f"{name} relocation candidate range")
        w0=struct.unpack_from("<H",image_bytes,off)[0]
        w1=struct.unpack_from("<H",base_bytes,off)[0]
        if ((w1-w0)&0xFFFF)==0x1000:
            relocs.append(off)
    # Reconstructing the base image from the retained relocation set must be
    # byte exact. This also catches missed or spurious candidate sites.
    rebuilt=bytearray(image_bytes)
    for off in relocs:
        w=struct.unpack_from("<H",rebuilt,off)[0]
        struct.pack_into("<H",rebuilt,off,(w+0x1000)&0xFFFF)
    req(bytes(rebuilt)==base_bytes,f"{name} two-origin relocation closure")
    return asm,image,tuple(relocs)
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
    asm,image,sh_relocs=build_relocatable(
        sj,out,"sh",
        f'    INCLUDE "{(root/"v1/include/zx48ux.inc").as_posix()}"\n    INCLUDE "{(root/"v1/src/shell/sh.asm").as_posix()}"\n',
        '    EMIT_P601_SH_IMAGE\n')
    req(image.is_file() and 4 <= image.stat().st_size <= 64,"shell preflight image")
    mex=mex1(image.read_bytes(),relocations=sh_relocs); (out/"sh.mex1").write_bytes(mex)
    inspect=root/"v1/tools-host/inspect-mex/inspect.py"
    run([sys.executable,inspect,out/"sh.mex1","--base","0x6000"],root)
    mt=load_maketap(root)
    tap=mt.m48o_blocks(mt.M48OObject("sh",mt.M48O_BIN,mt.DIR_BIN,mex))
    (out/"sh.m48o.tap").write_bytes(tap)
    req(tap==mt.m48o_blocks(mt.M48OObject("sh",mt.M48O_BIN,mt.DIR_BIN,mex)),"M48O nondeterminism")

    # First prospective ordinary /bin/cc image.  It contains the generic
    # ARG1/source-open/transaction scaffold only; historical source-bound
    # P1144/P1145/P11PR compiler macros are deliberately not expanded.
    cc_asm,cc_image,cc_relocs=build_relocatable(
        sj,out,"cc",
        f'    INCLUDE "{(root/"v1/include/zx48ux.inc").as_posix()}"\n    INCLUDE "{(root/"v1/src/tools/cc.asm").as_posix()}"\n',
        '    EMIT_P1128_CC_OBJ1_WRITER\n    EMIT_P1129_CC_TRANSACTION_ROUTINES\n    EMIT_REV02_CC_PRODUCT_CLI\n')
    req(cc_image.is_file() and 64 <= cc_image.stat().st_size <= 20480,"cc product image size")
    cc_mex=mex1(cc_image.read_bytes(),stack=512,relocations=cc_relocs); (out/"cc.mex1").write_bytes(cc_mex)
    run([sys.executable,inspect,out/"cc.mex1","--base","0x6000"],root)
    cc_tap=mt.m48o_blocks(mt.M48OObject("cc",mt.M48O_BIN,mt.DIR_BIN,cc_mex))
    (out/"cc.m48o.tap").write_bytes(cc_tap)
    req(cc_tap==mt.m48o_blocks(mt.M48OObject("cc",mt.M48O_BIN,mt.DIR_BIN,cc_mex)),"cc M48O nondeterminism")
    cc_wrapper=cc_asm.read_text()
    for forbidden in ("EMIT_P1144_CC_RECURSION_COMPILER","EMIT_P1145_CC_H06_COMPILER",
                      "EMIT_P11PR_CC_SDK_CORPUS_COMPILER","EMIT_P11PR_CC_SDK_MULTITASK_COMPILER",
                      "cc_p11pr_"):
        req(forbidden not in "\n".join(line for line in cc_wrapper.splitlines()
                                       if not line.lstrip().startswith("INCLUDE")),
            "source-bound compiler expanded in product wrapper: "+forbidden)


    # Prospective ordinary /bin/as image: generic ARG1/source-open scaffold only.
    as_asm,as_image,as_relocs=build_relocatable(
        sj,out,"as",
        f'    INCLUDE "{(root/"v1/include/zx48ux.inc").as_posix()}"\n    INCLUDE "{(root/"tools/as.asm").as_posix()}"\n',
        '    EMIT_REV02_AS_PRODUCT_CLI\n')
    req(as_image.is_file() and 64 <= as_image.stat().st_size <= 12288,"as product image size")
    as_mex=mex1(as_image.read_bytes(),stack=512,relocations=as_relocs); (out/"as.mex1").write_bytes(as_mex)
    run([sys.executable,inspect,out/"as.mex1","--base","0x6000"],root)
    as_tap=mt.m48o_blocks(mt.M48OObject("as",mt.M48O_BIN,mt.DIR_BIN,as_mex))
    (out/"as.m48o.tap").write_bytes(as_tap)
    req(as_tap==mt.m48o_blocks(mt.M48OObject("as",mt.M48O_BIN,mt.DIR_BIN,as_mex)),"as M48O nondeterminism")

    # Prospective ordinary /bin/ld image: generic ARG1/OBJ1-open scaffold only.
    ld_asm,ld_image,ld_relocs=build_relocatable(
        sj,out,"ld",
        f'    INCLUDE "{(root/"v1/include/zx48ux.inc").as_posix()}"\n    INCLUDE "{(root/"tools/ld.asm").as_posix()}"\n',
        '    EMIT_REV02_LD_PRODUCT_CLI\n')
    req(ld_image.is_file() and 64 <= ld_image.stat().st_size <= 8192,"ld product image size")
    ld_mex=mex1(ld_image.read_bytes(),stack=512,relocations=ld_relocs); (out/"ld.mex1").write_bytes(ld_mex)
    run([sys.executable,inspect,out/"ld.mex1","--base","0x6000"],root)
    ld_tap=mt.m48o_blocks(mt.M48OObject("ld",mt.M48O_BIN,mt.DIR_BIN,ld_mex))
    (out/"ld.m48o.tap").write_bytes(ld_tap)
    req(ld_tap==mt.m48o_blocks(mt.M48OObject("ld",mt.M48O_BIN,mt.DIR_BIN,ld_mex)),"ld M48O nondeterminism")

    report={
      "schema":1,"kind":"rev02-product-tools-preflight","status":"PASS",
      "shell":{
        "source":"v1/src/shell/sh.asm","source_sha256":sha(shsrc),
        "image_sha256":sha(image),"relocation_count":len(sh_relocs),"mex1_sha256":sha(out/"sh.mex1"),"m48o_tap_sha256":sha(out/"sh.m48o.tap"),
        "entry":"EMIT_P601_SH_IMAGE","semantic_status":"PACKAGING-ONLY-IDLE-ENTRY-NOT-GATE-G-READY"},
      "cc":{
        "source":"v1/src/tools/cc.asm","source_sha256":sha(ccsrc),
        "image_sha256":sha(cc_image),"image_bytes":cc_image.stat().st_size,"relocation_count":len(cc_relocs),
        "mex1_sha256":sha(out/"cc.mex1"),"m48o_tap_sha256":sha(out/"cc.m48o.tap"),
        "entry":"EMIT_REV02_CC_PRODUCT_CLI",
        "semantic_status":"GENERIC-CLI-AND-SOURCE-OPEN-SCAFFOLD; CODEGEN-NOT-YET-ATTACHED"},
      "as":{
        "source":"tools/as.asm","source_sha256":sha(assrc),
        "image_sha256":sha(as_image),"image_bytes":as_image.stat().st_size,"relocation_count":len(as_relocs),
        "mex1_sha256":sha(out/"as.mex1"),"m48o_tap_sha256":sha(out/"as.m48o.tap"),
        "entry":"EMIT_REV02_AS_PRODUCT_CLI",
        "semantic_status":"GENERIC-CLI-AND-SOURCE-OPEN-SCAFFOLD; ASSEMBLER-NOT-YET-ATTACHED"},
      "ld":{
        "source":"tools/ld.asm","source_sha256":sha(ldsrc),
        "image_sha256":sha(ld_image),"image_bytes":ld_image.stat().st_size,"relocation_count":len(ld_relocs),
        "mex1_sha256":sha(out/"ld.mex1"),"m48o_tap_sha256":sha(out/"ld.m48o.tap"),
        "entry":"EMIT_REV02_LD_PRODUCT_CLI",
        "semantic_status":"GENERIC-CLI-AND-OBJ1-OPEN-SCAFFOLD; LINKER-NOT-YET-ATTACHED"},
      "assertions":{
        "deterministic_shell_mex1":"PASS","deterministic_m48o":"PASS","mex1_inspection":"PASS",
        "deterministic_cc_mex1":"PASS","deterministic_cc_m48o":"PASS","cc_mex1_inspection":"PASS",
        "deterministic_as_mex1":"PASS","deterministic_as_m48o":"PASS","as_mex1_inspection":"PASS",
        "deterministic_ld_mex1":"PASS","deterministic_ld_m48o":"PASS","ld_mex1_inspection":"PASS",
        "normal_project_assembler_used":"PASS","relocatable_product_mex1":"PASS","p11pr_not_in_product_closure":"PASS",
        "not_claimed_as_real_shell_session":"PASS"}}
    (out/"PRODUCT-TOOLS-PREFLIGHT.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print("REV02 PRODUCT TOOLS PREFLIGHT PASS")
if __name__=="__main__": main()
