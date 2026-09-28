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

"""Create the Phase-11 pre-release plain-text native kernel assembler source.

The input is the already-qualified semantic projection, not kernel.bin.  Every
output line is ordinary documented Z80 assembler syntax frozen by P10.05-P10.33.
Instruction records are always rendered as mnemonics.  DB/DW/DEFS are emitted
only for semantic source data/directive records, never as an opcode-byte escape.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct

import kernel_native_projection as n

R8=("b","c","d","e","h","l","(hl)","a")
RR=("bc","de","hl","sp")
CC=("nz","z","nc","c","po","pe","p","m")
IDX=("ix","iy")
ALU=("add","adc","sub","sbc","and","xor","or","cp")
BIT=("bit","res","set")
SHIFT=("rlc","rrc","rl","rr","sla","sra","srl")
FIXED={v:k for k,v in n.FIXED_ID.items()}

def hx8(v:int)->str: return f"${v&255:02x}"
def hx16(v:int)->str: return f"${v&0xffff:04x}"
def sdisp(v:int)->str:
    v &= 255
    if v & 0x80: return f"-${256-v:02x}"
    return f"+${v:02x}"
def ind_index(i:int,d:int)->str: return f"({IDX[i]}{sdisp(d)})"

def render(r:bytes)->str:
    k=r[0]
    if k==n.FIXED: return FIXED[r[1]]
    if k==n.LD_R_R: return f"ld {R8[r[1]]},{R8[r[2]]}"
    if k==n.LD_R_N: return f"ld {R8[r[1]]},{hx8(r[2])}"
    if k==n.LD_R_MEMHL: return f"ld {R8[r[1]]},(hl)"
    if k==n.LD_MEMHL_R: return f"ld (hl),{R8[r[1]]}"
    if k==n.LD_MEMHL_N: return f"ld (hl),{hx8(r[1])}"
    if k==n.LD_A_MEMPAIR: return f"ld a,({('bc','de')[r[1]]})"
    if k==n.LD_MEMPAIR_A: return f"ld ({('bc','de')[r[1]]}),a"
    if k==n.LD_A_MEMABS: return f"ld a,({hx16(struct.unpack_from('<H',r,1)[0])})"
    if k==n.LD_MEMABS_A: return f"ld ({hx16(struct.unpack_from('<H',r,1)[0])}),a"
    if k==n.LD_RR_N: return f"ld {RR[r[1]]},{hx16(struct.unpack_from('<H',r,2)[0])}"
    if k==n.LD_RR_MEM: return f"ld {RR[r[1]]},({hx16(struct.unpack_from('<H',r,2)[0])})"
    if k==n.LD_MEMABS_RR: return f"ld ({hx16(struct.unpack_from('<H',r,2)[0])}),{RR[r[1]]}"
    if k==n.LD_INDEX_N: return f"ld {IDX[r[1]]},{hx16(struct.unpack_from('<H',r,2)[0])}"
    if k==n.LD_INDEX_MEM: return f"ld {IDX[r[1]]},({hx16(struct.unpack_from('<H',r,2)[0])})"
    if k==n.LD_MEMABS_INDEX: return f"ld ({hx16(struct.unpack_from('<H',r,2)[0])}),{IDX[r[1]]}"
    if k==n.LD_SP_INDEX: return f"ld sp,{IDX[r[1]]}"
    if k==n.LD_SPECIAL: return ("ld a,i","ld a,r","ld i,a","ld r,a")[r[1]]
    if k==n.LD_INDEX_R:
        idx,disp,store,reg=r[1:5]
        return f"ld {ind_index(idx,disp)},{R8[reg]}" if store else f"ld {R8[reg]},{ind_index(idx,disp)}"
    if k==n.LD_INDEX_N8: return f"ld {ind_index(r[1],r[2])},{hx8(r[3])}"
    if k in (n.ALU_R,n.ALU_N,n.ALU_INDEX):
        fam=r[1]; mn=ALU[fam]
        if k==n.ALU_R: op=R8[r[2]]
        elif k==n.ALU_N: op=hx8(r[2])
        else: op=ind_index(r[2],r[3])
        return f"{mn} a,{op}" if fam in (0,1,3) else f"{mn} {op}"
    if k==n.INCDEC_R: return f"{'dec' if r[2] else 'inc'} {R8[r[1]]}"
    if k==n.INCDEC_RR: return f"{'dec' if r[2] else 'inc'} {RR[r[1]]}"
    if k==n.ADD_HL_RR: return f"add hl,{RR[r[1]]}"
    if k==n.ADC_SBC_HL_RR: return f"{'sbc' if r[1] else 'adc'} hl,{RR[r[2]]}"
    if k==n.ADD_INDEX_RR: return f"add {IDX[r[1]]},{RR[r[2]]}"
    if k==n.JP_CALL:
        op="jp" if r[1]==0 else "call"; cc=r[2]; v=struct.unpack_from("<H",r,3)[0]
        return f"{op} {hx16(v)}" if cc==255 else f"{op} {CC[cc]},{hx16(v)}"
    if k==n.JR:
        cc=r[1];v=struct.unpack_from("<H",r,2)[0]
        return f"jr {hx16(v)}" if cc==255 else f"jr {CC[cc]},{hx16(v)}"
    if k==n.DJNZ: return f"djnz {hx16(struct.unpack_from('<H',r,1)[0])}"
    if k==n.RET: return "ret" if r[1]==255 else f"ret {CC[r[1]]}"
    if k==n.BITOP: return f"{BIT[r[1]]} {r[2]},{R8[r[3]]}"
    if k==n.BITOP_INDEX: return f"{BIT[r[1]]} {r[2]},{ind_index(r[3],r[4])}"
    if k==n.SHIFT: return f"{SHIFT[r[1]]} {R8[r[2]]}"
    if k==n.PUSHPOP:
        op="pop" if r[1] else "push"; p=r[2]
        name=("bc","de","hl","af","ix","iy")[p]
        return f"{op} {name}"
    if k==n.EX: return ("ex de,hl","ex (sp),hl","ex af,af'")[r[1]]
    if k==n.IM: return f"im {r[1]}"
    if k==n.INOUT: return ("in a,(c)","out (c),a")[r[1]]
    if k==n.OUT_N_A: return f"out ({hx8(r[1])}),a"
    if k==n.DB: return f"db {hx8(r[1])}"
    if k==n.DW: return f"dw {hx16(struct.unpack_from('<H',r,1)[0])}"
    if k==n.DS:
        count,fill=struct.unpack_from("<HB",r,1)
        return f"defs {hx16(count)},{hx8(fill)}"
    if k==n.RST: return f"rst {hx8(struct.unpack_from('<H',r,1)[0])}"
    raise ValueError(f"unrendered semantic kind {k}")

def records(blob:bytes)->list[bytes]:
    if blob[:4]!=n.MAGIC or blob[4]!=n.VERSION: raise ValueError("bad NSP1")
    count=struct.unpack_from("<H",blob,6)[0]; pos=16; out=[]
    for _ in range(count):
        z=n.record_length(blob,pos);out.append(blob[pos:pos+z]);pos+=z
    if pos!=len(blob): raise ValueError("NSP1 trailing bytes")
    return out

def emitted_len(r:bytes,pc:int)->int: return len(n.encode_record(r,pc))

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--listing",type=Path,required=True)
    ap.add_argument("--symbols",type=Path,required=True)
    ap.add_argument("--kernel",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    ap.add_argument("--map",type=Path,required=True)
    a=ap.parse_args()
    sem,ref,audit=n.build_projection(a.listing,a.symbols)
    kernel=a.kernel.read_bytes()
    if ref!=kernel or len(kernel)!=n.KERNEL_SIZE: raise SystemExit("semantic projection/kernel mismatch")
    rs=records(sem)
    lines=["org $e000"]; mapping=[]; pc=n.KERNEL_BASE; i=0
    while i<len(rs):
        r=rs[i]; k=r[0]; start=pc; used=[i]
        if k==n.DB:
            vals=[r[1]]; j=i+1
            while j<len(rs) and rs[j][0]==n.DB and len(vals)<24:
                vals.append(rs[j][1]);used.append(j);j+=1
            line="db "+",".join(hx8(v) for v in vals)
            pc+=len(vals);i=j
        elif k==n.DW:
            vals=[struct.unpack_from("<H",r,1)[0]]; j=i+1
            while j<len(rs) and rs[j][0]==n.DW and len(vals)<12:
                vals.append(struct.unpack_from("<H",rs[j],1)[0]);used.append(j);j+=1
            line="dw "+",".join(hx16(v) for v in vals)
            pc+=2*len(vals);i=j
        else:
            line=render(r);pc+=emitted_len(r,pc);i+=1
        lines.append(line)
        mapping.append({"line":len(lines),"address":start,"size":pc-start,"semantic_records":used,"text":line})
    source=("\n".join(lines)+"\n").encode("ascii")
    if b"\r" in source or len(source)>32768: raise SystemExit(f"native text source size invalid: {len(source)}")
    if pc!=n.KERNEL_BASE+n.KERNEL_SIZE: raise SystemExit(f"native text source emitted span invalid: {pc:#x}")
    for m in mapping:
        if m["text"].startswith("db "):
            if any(audit[x]["kind"]!=n.DB for x in m["semantic_records"]): raise SystemExit("opcode rendered through DB")
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_bytes(source)
    report={"schema":1,"kind":"phase11-pre-release-native-kernel-text-source",
      "base":n.KERNEL_BASE,"kernel_size":n.KERNEL_SIZE,"source_size":len(source),
      "source_sha256":hashlib.sha256(source).hexdigest(),"semantic_projection_sha256":hashlib.sha256(sem).hexdigest(),
      "kernel_sha256":hashlib.sha256(kernel).hexdigest(),"contains_preassembled_kernel_payload":False,
      "lf_only":True,"ordinary_documented_syntax_only":True,"lines":mapping}
    a.map.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8",newline="\n")
    print(f"source_size={len(source)}")
    print(f"source_sha256={report['source_sha256']}")
    print("ZX-UX NATIVE TEXT KERNEL SOURCE PASS")
    return 0
if __name__=="__main__": raise SystemExit(main())
