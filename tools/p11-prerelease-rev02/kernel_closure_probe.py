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
import argparse, json, re, subprocess, sys
from pathlib import Path

KERNEL_START=0xE000
KERNEL_POOL_BYTES=0x1B00

def req(v,m):
    if not v: raise SystemExit("ERROR: "+m)

def parse_symbols(path:Path)->dict[str,int]:
    pat=re.compile(r"^([^:]+): EQU 0x([0-9A-Fa-f]+)\s*$")
    symbols={}
    for line in path.read_text(encoding="utf-8",errors="replace").splitlines():
        m=pat.match(line.strip())
        if m: symbols[m.group(1)]=int(m.group(2),16)
    return symbols

def parse_symbol(path:Path,name:str)->int:
    symbols=parse_symbols(path)
    if name in symbols: return symbols[name]
    raise SystemExit("ERROR: missing probe symbol "+name)

def source_prefix(text:str,output_name:str)->str:
    marker="kernel_ordinary_used_end:"
    req(text.count(marker)==1,"kernel ordinary-end marker")
    prefix=text.split(marker,1)[0]
    return prefix+marker+"\n"+f'    SAVEBIN "../../build/{output_name}",kernel_image_start,kernel_ordinary_used_end-kernel_image_start\n'

def assemble(root:Path,name:str,text:str,start:int=KERNEL_START)->dict:
    srcdir=root/"v1/src/kernel"
    build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    sj=root/"tools/runtime/sjasmplus/bin/sjasmplus"
    req(sj.is_file(),"certified sjasmplus missing")
    source=srcdir/f"rev02-{name}-probe.asm"
    sym=build/f"rev02-{name}-probe.sym"
    binary=build/f"rev02-{name}-probe.bin"
    sym.unlink(missing_ok=True); binary.unlink(missing_ok=True)
    source.write_text(source_prefix(text,binary.name),encoding="utf-8",newline="\n")
    try:
        p=subprocess.run([str(sj),"--nologo",f"--sym={sym}",source.name],cwd=srcdir,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    finally:
        source.unlink(missing_ok=True)
    diagnostics=p.stdout+p.stderr
    row={"command_exit":p.returncode,"stdout":p.stdout[-16000:],"stderr":p.stderr[-16000:],
         "diagnostics_clean":not any(x in diagnostics for x in ("Label has different value in pass 3","truncated to 16bit"))}
    if p.returncode!=0:
        row.update({"status":"ASSEMBLY-FAIL","ordinary_bytes":None,"pool_bytes":KERNEL_POOL_BYTES,"slack_bytes":None})
        return row
    if not row["diagnostics_clean"]:
        row.update({"status":"ASSEMBLY-UNSTABLE","ordinary_bytes":None,"pool_bytes":KERNEL_POOL_BYTES,"slack_bytes":None})
        return row
    end=parse_symbol(sym,"kernel_ordinary_used_end")
    used=end-start
    req(0 < used < 0x8000,"ordinary byte measurement")
    req(binary.is_file() and binary.stat().st_size==used,"probe binary size")
    symbols=parse_symbols(sym)
    markers=[(n,v) for n,v in symbols.items() if n.startswith("kernel_mod_")]
    markers.append(("kernel_ordinary_used_end",end))
    markers.sort(key=lambda item:(item[1],item[0]))
    module_spans=[{"name":markers[i][0],"start":markers[i][1],"end":markers[i+1][1],"bytes":markers[i+1][1]-markers[i][1]}
                  for i in range(len(markers)-1)]
    row.update({"status":"PASS","ordinary_bytes":used,"pool_bytes":KERNEL_POOL_BYTES,
                "slack_bytes":KERNEL_POOL_BYTES-used,"overrun_bytes":max(0,used-KERNEL_POOL_BYTES),
                "module_spans":module_spans})
    return row

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    ns=ap.parse_args()
    root=ns.root.resolve(); out=ns.output.resolve(); out.mkdir(parents=True,exist_ok=True)
    kernel=(root/"v1/src/kernel/kernel.asm").read_text(encoding="utf-8")
    syscall=(root/"v1/src/kernel/syscall.asm").read_text(encoding="utf-8")
    baseline=assemble(root,"kernel-baseline",kernel)

    include_anchor='    INCLUDE "udg.asm"\n'
    req(kernel.count(include_anchor)==1,"UDG include anchor")
    req(syscall.count('    INCLUDE "graphics.asm"\n')==1,"syscall graphics include ownership")
    candidate=kernel.replace(include_anchor,include_anchor+'    INCLUDE "sound.asm"\n')
    measure_origin=0x8000
    origin_anchor="    ORG KERNEL_START\n"
    req(candidate.count(origin_anchor)==1,"kernel origin anchor")
    candidate=candidate.replace(origin_anchor,f"    ORG ${measure_origin:04X}\n",1)
    gateway_asserts=(
      ("    ASSERT $ = BOOT_GATEWAY\n",f"    ASSERT $ = ${measure_origin+3:04X}\n"),
      ("    ASSERT $ = BOOT_GATEWAY+3\n",f"    ASSERT $ = ${measure_origin+6:04X}\n"),
    )
    for old,new in gateway_asserts:
        req(candidate.count(old)==1,"kernel gateway assertion anchor")
        candidate=candidate.replace(old,new,1)
    emit_anchor="kernel_mod_udg:\n    EMIT_REV02_UDG_ROUTINES\n"
    req(candidate.count(emit_anchor)==1,"UDG emit anchor")
    extra="""kernel_mod_rev02_graphics:
    EMIT_GRAPHICS_ROUTINES
kernel_mod_rev02_sound:
    EMIT_SOUND_ROUTINES
kernel_mod_rev02_graphics_syscalls:
    EMIT_P701_GRAPHICS_SYSCALL_ROUTINES
kernel_mod_rev02_beep_syscall:
    EMIT_P709_BEEP_SYSCALL_ROUTINES
kernel_mod_rev02_rom_info_syscall:
    EMIT_P711_ROM_INFO_SYSCALL_ROUTINES
kernel_mod_rev02_udg_syscalls:
    EMIT_P714_UDG_SYSCALL_ROUTINES
    EMIT_P715_UDG_DRAW_SYSCALL_ROUTINES
kernel_mod_rev02_rom_beep:
    EMIT_P709_ROM_BEEP_ROUTINES
kernel_mod_rev02_rom_info:
    EMIT_REV02_P711_ROM_INFO_ROUTINES
kernel_mod_rev02_rom_fp_exec:
    EMIT_P1117_ROM_FP_EXEC_ROUTINES
kernel_mod_rev02_rom_fp_cast:
    EMIT_P1118_ROM_FP_CAST_ROUTINES
kernel_mod_rev02_rom_fp_cmp:
    EMIT_P1119_ROM_FP_CMP_ROUTINES
kernel_mod_rev02_rom_fp_to_text:
    EMIT_P1146_ROM_FP_TO_TEXT_ROUTINES
kernel_mod_rev02_rom_fp_from_text:
    EMIT_P1147_ROM_FP_FROM_TEXT_ROUTINES
kernel_mod_rev02_sys_fp_exec:
    EMIT_P1117_FP_EXEC_SYSCALL_ROUTINES
kernel_mod_rev02_sys_fp_cast:
    EMIT_P1118_FP_CAST_SYSCALL_ROUTINES
kernel_mod_rev02_sys_fp_cmp:
    EMIT_P1119_FP_CMP_SYSCALL_ROUTINES
kernel_mod_rev02_sys_fp_to_text:
    EMIT_P1146_FP_TO_TEXT_SYSCALL_ROUTINES
kernel_mod_rev02_sys_fp_from_text:
    EMIT_P1147_FP_FROM_TEXT_SYSCALL_ROUTINES
"""
    candidate=candidate.replace(emit_anchor,emit_anchor+extra)
    public_api=assemble(root,"kernel-public-api-lower-bound",candidate,start=measure_origin)

    report={"schema":1,"kind":"rev02-kernel-closure-probe","status":"PASS" if baseline["status"]=="PASS" and public_api["status"]=="PASS" else "FAIL",
            "kernel_pool_bytes":KERNEL_POOL_BYTES,
            "baseline":baseline,"public_api_lower_bound":public_api,
            "measurement_origin":measure_origin,
            "measurement_method":"size-only relocation preserves relative gateway placement; graphics macro is sourced once through syscall.asm; production kernel remains at $E000",
            "scope":"size-only relocated lower-bound: graphics/sound/UDG/ROM/FP handlers; excludes object/tape/zxpack/spawn closure and final selector routing"}
    (out/"KERNEL-CLOSURE-PROBE.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    req(baseline["status"]=="PASS","baseline kernel probe must assemble")
    if public_api["status"]!="PASS":
        print(public_api.get("stderr",""),file=sys.stderr)
        print(public_api.get("stdout",""),file=sys.stderr)
        raise SystemExit("ERROR: public API lower-bound probe must assemble")
    print("REV02 KERNEL CLOSURE PROBE PASS",json.dumps({"baseline":baseline.get("ordinary_bytes"),"public_api":public_api.get("ordinary_bytes"),"pool":KERNEL_POOL_BYTES}))
if __name__=="__main__": main()
