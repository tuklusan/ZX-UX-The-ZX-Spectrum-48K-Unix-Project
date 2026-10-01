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

def build_relocatable(sj: Path, out: Path, name: str, include_lines: str, emit_lines: str, bss_lines: str = ""):
    bss_enabled = bool(bss_lines)
    def source(origin: int, suffix: str, with_table: bool)->str:
        table=(f"{name}_product_relocs:\n    RELOCATE_TABLE\n"
               f"{name}_product_relocs_end:\n") if with_table else ""
        reloc_save=(f'    SAVEBIN "{name}-product.reloc",{name}_product_relocs,'
                    f'{name}_product_relocs_end-{name}_product_relocs\n') if with_table else ""
        bss_save=(f'    SAVEBIN "{name}-product{suffix}.bss",{name}_product_bss,'
                  f'{name}_product_bss_end-{name}_product_bss\n') if bss_enabled else ""
        return f"""    DEVICE ZXSPECTRUM48
{include_lines}    ORG ${origin:04X}
    RELOCATE_START
{name}_product_image:
{emit_lines}{name}_product_end:
{name}_product_bss:
{bss_lines}{name}_product_bss_end:
    RELOCATE_END
{table}    SAVEBIN "{name}-product{suffix}.bin",{name}_product_image,{name}_product_end-{name}_product_image
{bss_save}{reloc_save}"""

    asm=out/f"{name}-product.asm"
    asm.write_text(source(0,"",True),encoding="utf-8",newline="\n")
    run([sj,"--nologo",asm.name],out)
    base_asm=out/f"{name}-product-base.asm"
    base_asm.write_text(source(0x1000,"-base",False),encoding="utf-8",newline="\n")
    run([sj,"--nologo",base_asm.name],out)

    image=out/f"{name}-product.bin"
    image_bytes=image.read_bytes()
    base_bytes=(out/f"{name}-product-base.bin").read_bytes()
    if bss_enabled:
        bss_bytes=(out/f"{name}-product.bss").read_bytes()
        base_bss_bytes=(out/f"{name}-product-base.bss").read_bytes()
        req(len(base_bss_bytes)==len(bss_bytes),f"{name} two-origin BSS size drift")
        req(not any(bss_bytes) and not any(base_bss_bytes),f"{name} BSS must be zero-filled declaration space")
    else:
        bss_bytes=b""
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
    return asm,image,tuple(relocs),len(bss_bytes)
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

C48_RUNTIME_PUBLIC = (
    "exit","yield","sleep","spawn","wait","kill","chdir","getcwd","getenv","getpid",
    "open","open_typed","close","read","write","seek","stat","remove","rename","list",
    "pipe","dup","ioctl","read_full","write_full","getchar","putchar","puts","strlen","strcmp",
    "strcpy","strncpy","memcpy","memmove","memchr","memset","malloc","free","cls","print_at",
    "plot","point","draw","circle","ink","paper","bright","flash","inverse","over","border","beep",
    "udg_define","udg_get","udg_draw","udg_clear","udg_draw_2x2","tape_save","tape_load","ticks",
    "time_get","time_set","sin","cos","tan","asin","acos","atan","sqrt","exp","log","pow","fabs",
)
C48_RUNTIME_INTERNAL = (
    "__fadd","__fsub","__fmul","__fdiv","__fpow","__fabs","__fsgn","__fint","__fexp","__fln",
    "__fsin","__fcos","__ftan","__fasin","__facos","__fatan","__fsqrt","__itof","__ftoi","__fcmp","__ftruth",
)

def obj1_symbol(name: str, value: int, section: int, flags: int)->bytes:
    raw=name.encode("ascii")
    req(1 <= len(raw) <= 15 and raw.decode("ascii")==name,"OBJ1 symbol name")
    req(0 <= value <= 0xffff and section in (0,1,2,3) and flags in (0,1),"OBJ1 symbol fields")
    return raw+b"\0"*(16-len(raw))+struct.pack("<HBB",value,section,flags)

def obj1_image(text: bytes, symbols, relocs)->bytes:
    req(0 < len(text) <= 0x7fff,"runtime OBJ1 text size")
    symblob=b"".join(obj1_symbol(*row) for row in symbols)
    relblob=b"".join(struct.pack("<HHBB",off,idx,1,0) for off,idx in relocs)
    so=24+len(text); ro=so+len(symblob)
    req(ro+len(relblob) <= 0x8000,"runtime OBJ1 stored size")
    h=bytearray(24); h[:4]=b"OBJ1"; h[4]=1; h[5]=0; h[6:8]=struct.pack("<H",24)
    h[8:10]=struct.pack("<H",len(text)); h[10:12]=b"\0\0"
    h[12:14]=struct.pack("<H",len(symbols)); h[14:16]=struct.pack("<H",len(relocs))
    h[16:18]=struct.pack("<H",so); h[18:20]=struct.pack("<H",ro)
    body=text+symblob+relblob
    h[20:22]=struct.pack("<H",crc16(body)); h[22:24]=b"\0\0"; h[22:24]=struct.pack("<H",crc16(bytes(h)))
    return bytes(h)+body

def parse_sym(path: Path):
    out={}
    for line in path.read_text().splitlines():
        if ": EQU 0x" not in line: continue
        name,raw=line.split(": EQU 0x",1)
        try: out[name.strip()]=int(raw.strip(),16)
        except ValueError: pass
    return out

def build_runtime_obj1(root: Path, sj: Path, out: Path)->Path:
    sources=("int_runtime.asm","float_bridge.asm","float_runtime.asm","math_runtime.asm","memory.asm",
             "string.asm","syscall.asm","io.asm","graphics.asm","sound.asm","udg.asm","tape.asm")
    emits=("EMIT_C48_INT_RUNTIME","EMIT_P11_C48_FLOAT5_BRIDGE","EMIT_P1117_C48_FLOAT_RUNTIME",
           "EMIT_P1118_C48_CAST_RUNTIME","EMIT_P1119_C48_FCMP_RUNTIME","EMIT_P1120_C48_MATH_RUNTIME",
           "EMIT_P1121_C48_MEMORY","EMIT_P1124_C48_MEMORY_RUNTIME","EMIT_P1124_C48_STRING_RUNTIME",
           "EMIT_P1122_C48_SYSCALL_RUNTIME","EMIT_P1123_C48_IO_RUNTIME","EMIT_P1125_C48_GRAPHICS_RUNTIME",
           "EMIT_P1126_C48_SOUND_RUNTIME","EMIT_P1125_C48_UDG_RUNTIME","EMIT_P1127_C48_TAPE_RUNTIME")
    inc=''.join(f'    INCLUDE "{(root/"v1/src/libc48"/x).as_posix()}"\n' for x in sources)
    def asm_text(origin:int,suffix:str,with_relocs:bool):
        table='runtime_relocs:\n    RELOCATE_TABLE\nruntime_relocs_end:\n' if with_relocs else ''
        save_rel='    SAVEBIN "runtime.reloc",runtime_relocs,runtime_relocs_end-runtime_relocs\n' if with_relocs else ''
        return (f'    DEVICE ZXSPECTRUM48\n    INCLUDE "{(root/"v1/include/zx48ux.inc").as_posix()}"\n'+inc+
                '__heap_start EQU 0\n__heap_end EQU 0\n'+f'    ORG ${origin:04X}\n    RELOCATE_START\nruntime_image:\n'+
                ''.join('    '+x+'\n' for x in emits)+'runtime_end:\n    RELOCATE_END\n'+table+
                f'    SAVEBIN "runtime{suffix}.bin",runtime_image,runtime_end-runtime_image\n'+save_rel)
    a0=out/'runtime-product.asm'; a0.write_text(asm_text(0,'',True),encoding='utf-8',newline='\n')
    run([sj,'--nologo','--sym=runtime-product.sym',a0.name],out)
    a1=out/'runtime-product-base.asm'; a1.write_text(asm_text(0x1000,'-base',False),encoding='utf-8',newline='\n')
    run([sj,'--nologo',a1.name],out)
    text=(out/'runtime.bin').read_bytes(); base=(out/'runtime-base.bin').read_bytes()
    req(len(text)==len(base),"runtime two-origin size drift")
    raw=(out/'runtime.reloc').read_bytes(); req(len(raw)%2==0,"runtime relocation table size")
    candidates=struct.unpack('<'+'H'*(len(raw)//2),raw) if raw else ()
    local=[]
    for off in candidates:
        req(0 <= off <= len(text)-2,"runtime relocation range")
        w0=struct.unpack_from('<H',text,off)[0]; w1=struct.unpack_from('<H',base,off)[0]
        if ((w1-w0)&0xffff)==0x1000: local.append(off)
    rebuilt=bytearray(text)
    for off in local:
        w=struct.unpack_from('<H',rebuilt,off)[0]; struct.pack_into('<H',rebuilt,off,(w+0x1000)&0xffff)
    req(bytes(rebuilt)==base,"runtime two-origin relocation closure")
    syms=parse_sym(out/'runtime-product.sym')
    exports=C48_RUNTIME_PUBLIC+C48_RUNTIME_INTERNAL
    req(len(C48_RUNTIME_PUBLIC)==73,"runtime public declaration count")
    req(len(exports)==len(set(exports)),"runtime export duplicate")
    for name in exports: req(name in syms and 0 <= syms[name] < len(text),"runtime export missing: "+name)
    req('c48_heap_init_linker' in syms,"runtime heap init symbol")
    ho=syms['c48_heap_init_linker']; req(text[ho:ho+6]==b'\x11\0\0\x01\0\0',"runtime heap relocation shape")
    symbols=[('__rtbase',0,1,0)] + [(name,syms[name],1,1) for name in exports] + [('__heap_start',0,0,1),('__heap_end',0,0,1)]
    heap_start_idx=len(symbols)-2; heap_end_idx=len(symbols)-1
    relocs=[(off,0) for off in local] + [(ho+1,heap_start_idx),(ho+4,heap_end_idx)]
    relocs.sort()
    prev=-2
    for off,idx in relocs:
        req(off >= prev+2,"runtime relocation overlap/order"); prev=off
        req(0 <= idx < len(symbols),"runtime relocation symbol")
    obj=obj1_image(text,symbols,relocs); path=out/'libc48-runtime.obj1'; path.write_bytes(obj)
    inspect=root/'v1/tools-host/inspect-obj/inspect.py'; run([sys.executable,inspect,path],root)
    return path

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--root",type=Path,required=True); ap.add_argument("--output",type=Path,required=True); ns=ap.parse_args()
    root=ns.root.resolve(); out=ns.output.resolve(); out.mkdir(parents=True,exist_ok=True)
    sj=root/"tools/runtime/sjasmplus/bin/sjasmplus"; req(sj.is_file(),"project sjasmplus missing")
    shsrc=root/"v1/src/shell/sh.asm"; sh=shsrc.read_text()
    ccsrc=root/"v1/src/tools/cc.asm"; assrc=root/"tools/as.asm"; astextsrc=root/"tools/as_text.asm"; ldsrc=root/"tools/ld.asm"
    as_source=assrc.read_text(); as_support=astextsrc.read_text()
    req("EMIT_P601_SH_IMAGE" in sh and "sh_idle:" in sh,"shell entry fixture changed")
    cc_source=ccsrc.read_text()
    req(all(marker in cc_source for marker in (
        "cc_rev02_parse_simple_body:","cc_rev02_parse_call_args:",
        "cc_rev02_symbol_get_undef:","cc_rev02_add_reloc:",
        "cc_rev02_lex_string:","cc_rev02_pp_system_c48:","cc_rev02_pp_kw_c48",
        "cc_rev02_local_add:","cc_rev02_emit_local_load:","cc_rev02_parse_value_expr:","cc_rev02_value_lor:","cc_rev02_value_land:","cc_rev02_value_bor:","cc_rev02_value_bxor:","cc_rev02_value_band:","cc_rev02_value_eq:","cc_rev02_value_rel:","cc_rev02_value_shift:","cc_rev02_value_mul:","cc_rev02_emit_named_call:","cc_rev02_emit_call_marshal:",
        "CC_REV02_SYMBOL_CAP     EQU 32")),
        "ordinary cc generic prototype/call/string OBJ1 closure missing")
    req(all(marker not in cc_source.split("MACRO EMIT_REV02_CC_PRODUCT_CLI",1)[1].split("ENDM",1)[0]
            for marker in ("cc_p11pr_","CC_P11PR","source_crc","source_sha","identity_table")),
        "ordinary cc product closure contains source-specialized marker")
    req(all(marker in as_source for marker in (
        "as_rev02_sym_define:","as_rev02_validate_symbols:","as_rev02_record_reloc:",
        "as_rev02_kw_global:","as_rev02_kw_extern:","as_rev02_require_abs_expr:",
        "as_rev02_reopen_source:","as_rev02_write_obj1:",
        'canonicalizes to "label:ld a,1"')),
        "ordinary as full symbol/relocation driver closure missing")
    req(all(marker in as_support for marker in (
        "R17_TXT_M_DS    EQU 20","r17_txt_ds:",'db 2,"ds",R17_TXT_M_DS',
        "r17_txt_expr_hook:","r17_txt_reloc_hook:")),
        "ordinary as public DS/expression hook closure missing")
    # Product closure deliberately includes no historical P11PR compiler helper.
    req("EMIT_P11PR_CC_SDK_CORPUS_COMPILER" in ccsrc.read_text(),"historical fixture identity missing")
    asm,image,sh_relocs,sh_bss=build_relocatable(
        sj,out,"sh",
        f'    INCLUDE "{(root/"v1/include/zx48ux.inc").as_posix()}"\n    INCLUDE "{(root/"v1/src/shell/sh.asm").as_posix()}"\n',
        '    EMIT_P601_SH_IMAGE\n')
    req(image.is_file() and 4 <= image.stat().st_size <= 64,"shell preflight image")
    mex=mex1(image.read_bytes(),bss=sh_bss,relocations=sh_relocs); (out/"sh.mex1").write_bytes(mex)
    inspect=root/"v1/tools-host/inspect-mex/inspect.py"
    run([sys.executable,inspect,out/"sh.mex1","--base","0x6000"],root)
    mt=load_maketap(root)
    runtime_obj=build_runtime_obj1(root,sj,out)
    tap=mt.m48o_blocks(mt.M48OObject("sh",mt.M48O_BIN,mt.DIR_BIN,mex))
    (out/"sh.m48o.tap").write_bytes(tap)
    req(tap==mt.m48o_blocks(mt.M48OObject("sh",mt.M48O_BIN,mt.DIR_BIN,mex)),"M48O nondeterminism")

    # Ordinary /bin/cc image.  REV02 attaches one generic bounded streaming
    # source-semantic compiler path; historical source-bound P1144/P1145/P11PR
    # compiler macros are deliberately not expanded or reachable.
    cc_asm,cc_image,cc_relocs,cc_bss=build_relocatable(
        sj,out,"cc",
        f'    INCLUDE "{(root/"v1/include/zx48ux.inc").as_posix()}"\n    INCLUDE "{(root/"v1/src/tools/cc.asm").as_posix()}"\n',
        '    EMIT_P1128_CC_OBJ1_WRITER\n    EMIT_P1129_CC_TRANSACTION_ROUTINES\n    EMIT_REV02_CC_PRODUCT_CLI\n',
        '    defs CC_REV02_BSS_BYTES,0\n')
    req(cc_image.is_file() and 64 <= cc_image.stat().st_size <= 20480,"cc product image size")
    cc_resident=cc_image.stat().st_size+cc_bss+512
    req(cc_resident <= 20480,"cc frozen 20KiB process-owned image+BSS+stack gate")
    cc_mex=mex1(cc_image.read_bytes(),stack=512,bss=cc_bss,relocations=cc_relocs); (out/"cc.mex1").write_bytes(cc_mex)
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
    as_asm,as_image,as_relocs,as_bss=build_relocatable(
        sj,out,"as",
        f'    INCLUDE "{(root/"v1/include/zx48ux.inc").as_posix()}"\n    INCLUDE "{(root/"tools/as.asm").as_posix()}"\n    INCLUDE "{(root/"tools/as_text.asm").as_posix()}"\n',
        '    EMIT_P10_AS_OBJ1_SYMBOL_ROUTINES\n    EMIT_P10_AS_OBJ1_RELOC_ROUTINES\n    EMIT_P10_AS_EXPR_ROUTINES\n    EMIT_P10_AS_OBJ1_WRITER\n    EMIT_P10_AS_NAME_ROUTINES\n    EMIT_P10_AS_TRANSACTION_ROUTINES\n    EMIT_R17_AS_NSP1_OBJ1\n    EMIT_R17_AS_TEXT_OBJ1\n    EMIT_REV02_AS_PRODUCT_CLI\n',
        '    defs AS_REV02_BSS_BYTES,0\n')
    req(as_image.is_file() and 64 <= as_image.stat().st_size <= 12288,"as product image size")
    as_resident=as_image.stat().st_size+as_bss+512
    req(as_resident <= 32768,"as 48K process residency")
    as_mex=mex1(as_image.read_bytes(),stack=512,bss=as_bss,relocations=as_relocs); (out/"as.mex1").write_bytes(as_mex)
    run([sys.executable,inspect,out/"as.mex1","--base","0x6000"],root)
    as_tap=mt.m48o_blocks(mt.M48OObject("as",mt.M48O_BIN,mt.DIR_BIN,as_mex))
    (out/"as.m48o.tap").write_bytes(as_tap)
    req(as_tap==mt.m48o_blocks(mt.M48OObject("as",mt.M48O_BIN,mt.DIR_BIN,as_mex)),"as M48O nondeterminism")

    # Prospective ordinary /bin/ld image: generic normal single-OBJ1 linker plus REV18 -abs route.
    ld_asm,ld_image,ld_relocs,ld_bss=build_relocatable(
        sj,out,"ld",
        f'    INCLUDE "{(root/"v1/include/zx48ux.inc").as_posix()}"\n    INCLUDE "{(root/"tools/ld.asm").as_posix()}"\n    INCLUDE "{(root/"v1/src/libc48/crt0.asm").as_posix()}"\n    INCLUDE "{(root/"v1/src/libc48/runtime_archive.asm").as_posix()}"\n',
        '    EMIT_P10_LD_INPUT_LOADER\n    EMIT_P10_LD_ARCHIVE_SELECT_ROUTINES\n    EMIT_P10_LD_LAYOUT_ROUTINES\n    EMIT_P10_LD_SYMBOL_RESOLVE_ROUTINES\n    EMIT_REV02_LD_RELOCATION_ROUTINES\n    EMIT_P10_LD_DEFAULT_ENTRY_ROUTINES\n    EMIT_P10_LD_STACK_OPTION_ROUTINES\n    EMIT_P10_LD_MEX1_WRITER_ROUTINES\n    EMIT_P10_LD_TRANSACTION_ROUTINES\n    EMIT_P10_CRT0_OBJ1\n    EMIT_P10_RUNTIME_ARCHIVE\n    EMIT_P1135_C48_RUNTIME_ARCHIVE\n    EMIT_REV02_FULL_RUNTIME_ARCHIVE\n    EMIT_REV02_FULL_RUNTIME_ARCHIVE_ROUTINES\n    EMIT_REV02_LD_PRODUCT_CLI\n',
        '    defs LD_REV02_NORMAL_BSS_BYTES,0\n')
    req(ld_image.is_file() and 64 <= ld_image.stat().st_size <= 20480,"ld product image size")
    req(ld_image.read_bytes().count(runtime_obj.read_bytes())==1,"full runtime archive member embedding")
    ld_resident=ld_image.stat().st_size+ld_bss+512
    req(ld_resident <= 32768,"ld 48K process residency")
    ld_mex=mex1(ld_image.read_bytes(),stack=512,bss=ld_bss,relocations=ld_relocs); (out/"ld.mex1").write_bytes(ld_mex)
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
        "image_sha256":sha(cc_image),"image_bytes":cc_image.stat().st_size,"bss_bytes":cc_bss,"resident_bytes_including_stack":cc_resident,"relocation_count":len(cc_relocs),
        "mex1_sha256":sha(out/"cc.mex1"),"m48o_tap_sha256":sha(out/"cc.m48o.tap"),
        "entry":"EMIT_REV02_CC_PRODUCT_CLI",
        "semantic_status":"GENERIC-STREAMING-NATIVE-C-CHECKPOINT; ONE-LEVEL-QUOTED-LOCAL-INCLUDE; BUILTIN-C48-HEADER; FROZEN-BOUNDED-OBJECT-LIKE-DEFINES; GENERIC-PROTOTYPES/CALLS/STRINGS/ABS16-RELOCS; INT-LOCALS/ASSIGNMENT/RVALUE/ADDITIVE-CODEGEN; RUNTIME-EXPRESSION-C48_REGCALL-ARGS-1-TO-6; RUNTIME-INT-MUL-DIV-MOD; RUNTIME-INT-BITWISE; RUNTIME-INT-SHIFTS; RUNTIME-SIGNED-COMPARISONS; RUNTIME-LOGICAL-SHORT-CIRCUIT; INTEGER-CONSTANT-EXPRESSIONS; FULL-C48-PENDING"},
      "as":{
        "source":"tools/as.asm","source_sha256":sha(assrc),"support_source":"tools/as_text.asm","support_source_sha256":sha(astextsrc),
        "image_sha256":sha(as_image),"image_bytes":as_image.stat().st_size,"bss_bytes":as_bss,"resident_bytes_including_stack":as_resident,"relocation_count":len(as_relocs),
        "mex1_sha256":sha(out/"as.mex1"),"m48o_tap_sha256":sha(out/"as.m48o.tap"),
        "entry":"EMIT_REV02_AS_PRODUCT_CLI",
        "semantic_status":"GENERIC-NATIVE-AS-FULL-P10-SYNTAX-DRIVER; LABEL/EQU/DB/DW/DS/GLOBAL/EXTERN/EXPRESSIONS; DETERMINISTIC-OBJ1-ABS16-RELOC; TRANSACTIONAL-PUBLISH"},
      "runtime_archive":{
        "source":"v1/src/libc48/*.asm","obj1_sha256":sha(runtime_obj),"obj1_bytes":runtime_obj.stat().st_size,
        "public_symbol_count":len(C48_RUNTIME_PUBLIC),"embedded_in_ld":ld_image.read_bytes().count(runtime_obj.read_bytes())==1,
        "semantic_status":"FULL-FROZEN-C48-RUNTIME-OBJ1-EMBEDDED-AS-ONE-GENERIC-ARCHIVE-MEMBER-AND-NORMAL-LINK-SELECTED"},
      "ld":{
        "source":"tools/ld.asm","source_sha256":sha(ldsrc),
        "image_sha256":sha(ld_image),"image_bytes":ld_image.stat().st_size,"bss_bytes":ld_bss,"resident_bytes":ld_resident,"relocation_count":len(ld_relocs),
        "mex1_sha256":sha(out/"ld.mex1"),"m48o_tap_sha256":sha(out/"ld.m48o.tap"),
        "entry":"EMIT_REV02_LD_PRODUCT_CLI",
        "semantic_status":"GENERIC-CRT0-USER-FULL-C48-RUNTIME-NORMAL-LINK-WITH-1024-BYTE-HEAP-PLUS-REV18-ABS"},
      "assertions":{
        "deterministic_shell_mex1":"PASS","deterministic_m48o":"PASS","mex1_inspection":"PASS",
        "deterministic_cc_mex1":"PASS","deterministic_cc_m48o":"PASS","cc_mex1_inspection":"PASS","generic_cc_prototype_call_string_checkpoint":"PASS",
        "deterministic_as_mex1":"PASS","deterministic_as_m48o":"PASS","as_mex1_inspection":"PASS","generic_as_full_p10_source_driver":"PASS",
        "deterministic_ld_mex1":"PASS","deterministic_ld_m48o":"PASS","ld_mex1_inspection":"PASS",
        "normal_project_assembler_used":"PASS","relocatable_product_mex1":"PASS","full_runtime_archive_embedded_once":"PASS","p11pr_not_in_product_closure":"PASS",
        "not_claimed_as_real_shell_session":"PASS"}}
    (out/"PRODUCT-TOOLS-PREFLIGHT.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print("REV02 PRODUCT TOOLS PREFLIGHT PASS")
if __name__=="__main__": main()
