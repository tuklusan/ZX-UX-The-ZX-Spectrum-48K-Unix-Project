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

"""Generate the REV17 semantic/tokenized native kernel source projection.

The projection is source-only semantic IR. It contains Z80 operations, register
identities, source literal values, resolved source expressions, and fill
directives. It never copies machine-code bytes from the host assembler listing
or from kernel.bin. Listing machine bytes are used only as a Boolean indication
that an expanded source statement emitted output; kernel.bin is optional and is
used only as a final independent oracle after the semantic projection has been
encoded by this module's reference assembler.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
import re
import struct

MAGIC=b"NSP1"
VERSION=1
KERNEL_BASE=0xE000
KERNEL_SIZE=8192

# Semantic record kinds. These are source operations, not target opcodes.
FIXED=1; LD_R_R=2; LD_R_N=3; LD_R_MEMHL=4; LD_MEMHL_R=5; LD_MEMHL_N=6
LD_A_MEMPAIR=7; LD_MEMPAIR_A=8; LD_A_MEMABS=9; LD_MEMABS_A=10
LD_RR_N=11; LD_RR_MEM=12; LD_MEMABS_RR=13; LD_INDEX_N=14
LD_INDEX_MEM=15; LD_MEMABS_INDEX=16; LD_SP_INDEX=17; LD_SPECIAL=18
LD_INDEX_R=19; LD_INDEX_N8=20; ALU_R=21; ALU_N=22; ALU_INDEX=23
INCDEC_R=24; INCDEC_RR=25; ADD_HL_RR=26; ADC_SBC_HL_RR=27
ADD_INDEX_RR=28; JP_CALL=29; JR=30; DJNZ=31; RET=32; BITOP=33
BITOP_INDEX=34; SHIFT=35; PUSHPOP=36; EX=37; IM=38; INOUT=39
DB=40; DW=41; DS=42; RST=43; OUT_N_A=44

REG8={"b":0,"c":1,"d":2,"e":3,"h":4,"l":5,"(hl)":6,"a":7}
PAIR={"bc":0,"de":1,"hl":2,"sp":3}
COND={"nz":0,"z":1,"nc":2,"c":3,"po":4,"pe":5,"p":6,"m":7}
INDEX={"ix":0,"iy":1}
ALU={"add":0,"adc":1,"sub":2,"sbc":3,"and":4,"xor":5,"or":6,"cp":7}
BIT_FAMILY={"bit":0,"res":1,"set":2}
SHIFT_FAMILY={"rlc":0,"rrc":1,"rl":2,"rr":3,"sla":4,"sra":5,"srl":6}
FIXED_ID={
    "nop":0,"rlca":1,"rrca":2,"rla":3,"rra":4,"daa":5,"cpl":6,"scf":7,
    "ccf":8,"halt":9,"di":10,"ei":11,"exx":12,"reti":13,"neg":14,
    "ldi":15,"ldir":16,"ldd":17,"lddr":18,"cpi":19,"cpir":20,"cpd":21,"cpdr":22,
}
FIXED_BYTES={
    0:b"\x00",1:b"\x07",2:b"\x0f",3:b"\x17",4:b"\x1f",5:b"\x27",
    6:b"\x2f",7:b"\x37",8:b"\x3f",9:b"\x76",10:b"\xf3",11:b"\xfb",
    12:b"\xd9",13:b"\xed\x4d",14:b"\xed\x44",15:b"\xed\xa0",
    16:b"\xed\xb0",17:b"\xed\xa8",18:b"\xed\xb8",19:b"\xed\xa1",
    20:b"\xed\xb1",21:b"\xed\xa9",22:b"\xed\xb9",23:b"\xe9",24:b"\xf9",
}
IMM_ALU=(0xC6,0xCE,0xD6,0xDE,0xE6,0xEE,0xF6,0xFE)
SHIFT_BASE=(0x00,0x08,0x10,0x18,0x20,0x28,0x38)

class ProjectionError(ValueError): pass

def crc16(data:bytes)->int:
    c=0xffff
    for b in data:
        c ^= b<<8
        for _ in range(8):
            c=((c<<1)^0x1021)&0xffff if c&0x8000 else (c<<1)&0xffff
    return c

def split_args(text:str)->list[str]:
    out=[]; cur=[]; depth=0; quote=None
    for ch in text:
        if quote:
            cur.append(ch)
            if ch==quote: quote=None
            continue
        if ch in "'\"": quote=ch; cur.append(ch); continue
        if ch=="(": depth+=1
        elif ch==")": depth-=1
        if ch=="," and depth==0:
            out.append("".join(cur).strip());cur=[]
        else: cur.append(ch)
    if cur or text.strip(): out.append("".join(cur).strip())
    return out

def symbols(path:Path)->dict[str,int]:
    out={}
    rx=re.compile(r"^([^:\s]+):\s+equ\s+0x([0-9a-f]+)\s*$",re.I)
    for line in path.read_text(encoding="utf-8",errors="replace").splitlines():
        m=rx.match(line.strip())
        if m: out[m.group(1)]=int(m.group(2),16)
    if not out: raise ProjectionError("no symbols parsed")
    return out

def eval_expr(expr:str, syms:dict[str,int], pc:int)->int:
    expr=expr.strip()
    if not expr: raise ProjectionError("empty expression")
    if len(expr) >= 2 and expr[0] in "'\"" and expr[-1] == expr[0]:
        value = ast.literal_eval(expr)
        if isinstance(value, str) and len(value) == 1:
            return ord(value)
        raise ProjectionError(f"character literal required: {expr!r}")
    expr=re.sub(r"\$([0-9a-fA-F]+)",lambda m:"0x"+m.group(1),expr)
    expr=re.sub(r"%([01]+)",lambda m:"0b"+m.group(1),expr)
    expr=expr.replace("$",str(pc))
    token=re.compile(r"\b[A-Za-z_.$][A-Za-z0-9_.$]*\b")
    def sub(m):
        name=m.group(0)
        if name in syms:return str(syms[name])
        low=name.lower()
        for k,v in syms.items():
            if k.lower()==low:return str(v)
        raise ProjectionError(f"unknown symbol {name!r} in {expr!r}")
    expr=token.sub(sub,expr)
    expr=expr.replace("/", "//")
    try: tree=ast.parse(expr,mode="eval")
    except SyntaxError as exc: raise ProjectionError(f"bad expression {expr!r}") from exc
    allowed=(ast.Expression,ast.Constant,ast.UnaryOp,ast.BinOp,ast.Add,ast.Sub,ast.Mult,
             ast.FloorDiv,ast.Mod,ast.BitAnd,ast.BitOr,ast.BitXor,ast.LShift,ast.RShift,
             ast.USub,ast.UAdd,ast.Invert)
    if any(not isinstance(n,allowed) for n in ast.walk(tree)):
        raise ProjectionError(f"unsafe expression {expr!r}")
    return int(eval(compile(tree,"<nsp-expr>","eval"),{"__builtins__":{}},{}))

def listing_statements(path:Path):
    # Parse only address and expanded source text. Machine-byte values are never returned.
    for raw in path.read_text(encoding="utf-8",errors="replace").splitlines():
        m=re.match(r"^\s*\d+\+?\s+([0-9A-Fa-f]{4})\s+(.*)$",raw)
        if not m: continue
        address=int(m.group(1),16); rest=m.group(2)
        src=None; emitted=False
        if ">" in rest:
            left,right=rest.split(">",1); src=right.strip()
            # Boolean only: did listing show at least one emitted-byte token?
            emitted=bool(re.search(r"(?:^|\s)[0-9A-Fa-f]{2}(?:\s|$)",left))
        else:
            # Normal non-macro listing lines place source after a wide byte column.
            mm=re.match(r"((?:(?:[0-9A-Fa-f]{2})(?:\s+|$)|\.\.\.|\s)+?)\s{2,}(.*)$",rest)
            if mm:
                left,src=mm.group(1),mm.group(2).strip()
                emitted=bool(re.search(r"(?:^|\s)[0-9A-Fa-f]{2}(?:\s|$)",left))
        if emitted and src:
            src=src.split(";",1)[0].strip()
            if src: yield address,src

def strip_label(src:str)->str:
    m=re.match(r"^[A-Za-z_.$][A-Za-z0-9_.$]*:\s*(.*)$",src)
    return m.group(1).strip() if m else src.strip()

def rec(kind:int,*values:int)->bytes:
    fmt={FIXED:"BB",LD_R_R:"BBB",LD_R_N:"BBH",LD_R_MEMHL:"BB",LD_MEMHL_R:"BB",
         LD_MEMHL_N:"BH",LD_A_MEMPAIR:"BB",LD_MEMPAIR_A:"BB",LD_A_MEMABS:"BH",
         LD_MEMABS_A:"BH",LD_RR_N:"BBH",LD_RR_MEM:"BBH",LD_MEMABS_RR:"BBH",
         LD_INDEX_N:"BBH",LD_INDEX_MEM:"BBH",LD_MEMABS_INDEX:"BBH",LD_SP_INDEX:"BB",
         LD_SPECIAL:"BB",LD_INDEX_R:"BBBBB",LD_INDEX_N8:"BBBB",ALU_R:"BBB",
         ALU_N:"BBH",ALU_INDEX:"BBBB",INCDEC_R:"BBB",INCDEC_RR:"BBB",
         ADD_HL_RR:"BB",ADC_SBC_HL_RR:"BBB",ADD_INDEX_RR:"BBB",JP_CALL:"BBBH",
         JR:"BBH",DJNZ:"BH",RET:"BB",BITOP:"BBBB",BITOP_INDEX:"BBBBB",
         SHIFT:"BBB",PUSHPOP:"BBB",EX:"BB",IM:"BB",INOUT:"BB",DB:"BH",
         DW:"BH",DS:"BHH",RST:"BH",OUT_N_A:"BB"}[kind]
    return struct.pack("<"+fmt,kind,*values)

def u8(v:int)->int:
    if not -128<=v<=255: raise ProjectionError(f"8-bit value out of range: {v}")
    return v&255
def u16(v:int)->int:
    if not -32768<=v<=0xffff: raise ProjectionError(f"16-bit value out of range: {v}")
    return v&0xffff

def indexed(op:str, syms, pc):
    m=re.fullmatch(r"\((ix|iy)([+-].+)?\)",op.strip(),re.I)
    if not m:return None
    idx=INDEX[m.group(1).lower()]
    disp=0 if not m.group(2) else eval_expr(m.group(2),syms,pc)
    return idx,u8(disp)

def encode_source(src:str,address:int,syms:dict[str,int])->list[bytes]:
    src=strip_label(src)
    if not src:return []
    parts=src.split(None,1); mn=parts[0].lower(); tail=parts[1].strip() if len(parts)>1 else ""
    if mn in {"assert","org","device","include","macro","endm","if","else","endif","ifdef","ifndef"}:
        return []
    if mn in FIXED_ID:return [rec(FIXED,FIXED_ID[mn])]
    if mn in ("db","defb"):
        out=[]
        for arg in split_args(tail):
            if len(arg)>=2 and arg[0] in "'\"" and arg[-1]==arg[0]:
                # Character/string literal: source data, not preassembled payload.
                value=ast.literal_eval(arg)
                if not isinstance(value,str):raise ProjectionError(arg)
                out.extend(rec(DB,ord(ch)) for ch in value)
            else:
                out.append(rec(DB,u8(eval_expr(arg,syms,address))))
        return out
    if mn in ("dw","defw"):
        return [rec(DW,u16(eval_expr(a,syms,address))) for a in split_args(tail)]
    if mn in ("defs","ds"):
        args=split_args(tail); count=eval_expr(args[0],syms,address); fill=eval_expr(args[1],syms,address) if len(args)>1 else 0
        if not 0<=count<=0xffff:raise ProjectionError("DS count")
        return [rec(DS,count,u8(fill))]
    if mn=="ld":
        a=split_args(tail)
        if len(a)!=2:raise ProjectionError(src)
        d,s=a[0].lower(),a[1].lower()
        di=indexed(d,syms,address); si=indexed(s,syms,address)
        if d in REG8 and s in REG8:return [rec(LD_R_R,REG8[d],REG8[s])]
        if d in REG8 and s=="(hl)":return [rec(LD_R_MEMHL,REG8[d])]
        if d=="(hl)" and s in REG8:return [rec(LD_MEMHL_R,REG8[s])]
        if d=="(hl)":return [rec(LD_MEMHL_N,u8(eval_expr(s,syms,address)))]
        if di and s in REG8:return [rec(LD_INDEX_R,di[0],di[1],1,REG8[s])]
        if di:return [rec(LD_INDEX_N8,di[0],di[1],u8(eval_expr(s,syms,address)))]
        if d in REG8 and si:return [rec(LD_INDEX_R,si[0],si[1],0,REG8[d])]
        if d in REG8:
            if s in ("(bc)","(de)") and d=="a":return [rec(LD_A_MEMPAIR,0 if s=="(bc)" else 1)]
            if d=="a" and s=="i":return [rec(LD_SPECIAL,0)]
            if d=="a" and s=="r":return [rec(LD_SPECIAL,1)]
            if s.startswith("(") and s.endswith(")"):
                if d!="a":raise ProjectionError(src)
                return [rec(LD_A_MEMABS,u16(eval_expr(s[1:-1],syms,address)))]
            return [rec(LD_R_N,REG8[d],u8(eval_expr(s,syms,address)))]
        if d in ("i","r") and s=="a":return [rec(LD_SPECIAL,2 if d=="i" else 3)]
        if d=="sp" and s=="hl":return [rec(FIXED,24)]
        if d=="sp" and s in INDEX:return [rec(LD_SP_INDEX,INDEX[s])]
        if d in PAIR:
            if s.startswith("(") and s.endswith(")"):return [rec(LD_RR_MEM,PAIR[d],u16(eval_expr(s[1:-1],syms,address)))]
            return [rec(LD_RR_N,PAIR[d],u16(eval_expr(s,syms,address)))]
        if d in INDEX:
            if s.startswith("(") and s.endswith(")"):return [rec(LD_INDEX_MEM,INDEX[d],u16(eval_expr(s[1:-1],syms,address)))]
            return [rec(LD_INDEX_N,INDEX[d],u16(eval_expr(s,syms,address)))]
        if d.startswith("(") and d.endswith(")"):
            inner=d[1:-1]
            if s=="a":
                if inner.lower() in ("bc","de"):return [rec(LD_MEMPAIR_A,0 if inner.lower()=="bc" else 1)]
                return [rec(LD_MEMABS_A,u16(eval_expr(inner,syms,address)))]
            if s in PAIR:return [rec(LD_MEMABS_RR,PAIR[s],u16(eval_expr(inner,syms,address)))]
            if s in INDEX:return [rec(LD_MEMABS_INDEX,INDEX[s],u16(eval_expr(inner,syms,address)))]
        raise ProjectionError(src)
    if mn in ALU:
        args=split_args(tail)
        if mn in ("add","adc","sbc") and len(args)==2 and args[0].lower()=="hl" and args[1].lower() in PAIR:
            if mn=="add":return [rec(ADD_HL_RR,PAIR[args[1].lower()])]
            return [rec(ADC_SBC_HL_RR,0 if mn=="adc" else 1,PAIR[args[1].lower()])]
        if mn=="add" and len(args)==2 and args[0].lower() in INDEX and args[1].lower() in PAIR:
            return [rec(ADD_INDEX_RR,INDEX[args[0].lower()],PAIR[args[1].lower()])]
        op=args[-1].lower()
        ix=indexed(op,syms,address)
        if ix:return [rec(ALU_INDEX,ALU[mn],ix[0],ix[1])]
        if op in REG8:return [rec(ALU_R,ALU[mn],REG8[op])]
        return [rec(ALU_N,ALU[mn],u8(eval_expr(op,syms,address)))]
    if mn in ("inc","dec"):
        op=tail.lower()
        if op in REG8:return [rec(INCDEC_R,REG8[op],1 if mn=="dec" else 0)]
        if op in PAIR:return [rec(INCDEC_RR,PAIR[op],1 if mn=="dec" else 0)]
        raise ProjectionError(src)
    if mn in ("jp","call"):
        a=split_args(tail); cond=255; target=a[-1].lower()
        if len(a)==2:cond=COND[a[0].lower()]
        if target=="(hl)":
            if mn!="jp" or cond!=255:return [][0]
            return [rec(FIXED,23)]  # special JP(HL), host encoder handles id 23
        return [rec(JP_CALL,0 if mn=="jp" else 1,cond,u16(eval_expr(target,syms,address)))]
    if mn=="jr":
        a=split_args(tail); cond=255
        if len(a)==2:cond=COND[a[0].lower()]
        return [rec(JR,cond,u16(eval_expr(a[-1],syms,address)))]
    if mn=="djnz":return [rec(DJNZ,u16(eval_expr(tail,syms,address)))]
    if mn=="ret":
        cond=255 if not tail else COND[tail.lower()]
        return [rec(RET,cond)]
    if mn=="rst":return [rec(RST,u16(eval_expr(tail,syms,address)))]
    if mn in BIT_FAMILY:
        a=split_args(tail); bit=eval_expr(a[0],syms,address); op=a[1].lower(); ix=indexed(op,syms,address)
        if ix:return [rec(BITOP_INDEX,BIT_FAMILY[mn],bit,ix[0],ix[1])]
        return [rec(BITOP,BIT_FAMILY[mn],bit,REG8[op])]
    if mn in SHIFT_FAMILY:
        op=tail.lower()
        if op not in REG8:raise ProjectionError(src)
        return [rec(SHIFT,SHIFT_FAMILY[mn],REG8[op])]
    if mn in ("push","pop"):
        op=tail.lower(); pp=0 if mn=="push" else 1
        if op in ("bc","de","hl","af"):return [rec(PUSHPOP,pp,{"bc":0,"de":1,"hl":2,"af":3}[op])]
        if op in INDEX:return [rec(PUSHPOP,pp,4+INDEX[op])]
        raise ProjectionError(src)
    if mn=="ex":
        v=tail.lower().replace(" ","")
        return [rec(EX,{"de,hl":0,"(sp),hl":1,"af,af'":2}[v])]
    if mn=="im":return [rec(IM,eval_expr(tail,syms,address))]
    if mn=="in":
        if tail.lower().replace(" ","")=="a,(c)":return [rec(INOUT,0)]
        raise ProjectionError(src)
    if mn=="out":
        compact=tail.lower().replace(" ","")
        if compact=="(c),a":return [rec(INOUT,1)]
        m=re.fullmatch(r"\((.+)\),a",tail.strip(),re.I)
        if m:return [rec(OUT_N_A,u8(eval_expr(m.group(1),syms,address)))]
        raise ProjectionError(src)
    raise ProjectionError(f"unsupported emitting source at {address:#06x}: {src}")

def encode_record(record:bytes,pc:int)->bytes:
    k=record[0]
    if k==FIXED:
        i=record[1]
        return FIXED_BYTES[i]
    if k==LD_R_R:return bytes([0x40+record[1]*8+record[2]])
    if k==LD_R_N:return bytes([0x06+record[1]*8,record[2]])
    if k==LD_R_MEMHL:return bytes([0x46+record[1]*8])
    if k==LD_MEMHL_R:return bytes([0x70+record[1]])
    if k==LD_MEMHL_N:return bytes([0x36,record[1]])
    if k==LD_A_MEMPAIR:return bytes([0x0A if record[1]==0 else 0x1A])
    if k==LD_MEMPAIR_A:return bytes([0x02 if record[1]==0 else 0x12])
    if k in (LD_A_MEMABS,LD_MEMABS_A):
        v=struct.unpack_from("<H",record,1)[0];return bytes([0x3A if k==LD_A_MEMABS else 0x32,v&255,v>>8])
    if k==LD_RR_N:
        pair=record[1];v=struct.unpack_from("<H",record,2)[0];return bytes([0x01+pair*0x10,v&255,v>>8])
    if k in (LD_RR_MEM,LD_MEMABS_RR):
        pair=record[1];v=struct.unpack_from("<H",record,2)[0]
        if pair==2:op=0x2A if k==LD_RR_MEM else 0x22;return bytes([op,v&255,v>>8])
        op=(0x4B if k==LD_RR_MEM else 0x43)+pair*0x10;return bytes([0xED,op,v&255,v>>8])
    if k in (LD_INDEX_N,LD_INDEX_MEM,LD_MEMABS_INDEX):
        idx=record[1];v=struct.unpack_from("<H",record,2)[0];op={LD_INDEX_N:0x21,LD_INDEX_MEM:0x2A,LD_MEMABS_INDEX:0x22}[k]
        return bytes([0xDD if idx==0 else 0xFD,op,v&255,v>>8])
    if k==LD_SP_INDEX:return bytes([0xDD if record[1]==0 else 0xFD,0xF9])
    if k==LD_SPECIAL:return (b"\xed\x57",b"\xed\x5f",b"\xed\x47",b"\xed\x4f")[record[1]]
    if k==LD_INDEX_R:
        idx,disp,store,r=record[1:5];return bytes([0xDD if idx==0 else 0xFD,(0x70+r) if store else (0x46+r*8),disp])
    if k==LD_INDEX_N8:return bytes([0xDD if record[1]==0 else 0xFD,0x36,record[2],record[3]])
    if k==ALU_R:return bytes([0x80+record[1]*8+record[2]])
    if k==ALU_N:return bytes([IMM_ALU[record[1]],record[2]])
    if k==ALU_INDEX:return bytes([0xDD if record[2]==0 else 0xFD,0x80+record[1]*8+6,record[3]])
    if k==INCDEC_R:return bytes([0x04+record[1]*8+record[2]])
    if k==INCDEC_RR:return bytes([0x03+record[1]*0x10+record[2]*8])
    if k==ADD_HL_RR:return bytes([0x09+record[1]*0x10])
    if k==ADC_SBC_HL_RR:return bytes([0xED,(0x4A if record[1]==0 else 0x42)+record[2]*0x10])
    if k==ADD_INDEX_RR:return bytes([0xDD if record[1]==0 else 0xFD,0x09+record[2]*0x10])
    if k==JP_CALL:
        op,cond=record[1],record[2];v=struct.unpack_from("<H",record,3)[0]
        opcode=(0xC3 if op==0 else 0xCD) if cond==255 else ((0xC2 if op==0 else 0xC4)+cond*8)
        return bytes([opcode,v&255,v>>8])
    if k==JR:
        cond=record[1];target=struct.unpack_from("<H",record,2)[0];d=(target-(pc+2))&0xffff
        if d>=0xff80:d-=0x10000
        if not -128<=d<=127:raise ProjectionError("JR range")
        opcode=0x18 if cond==255 else 0x20+cond*8
        return bytes([opcode,d&255])
    if k==DJNZ:
        target=struct.unpack_from("<H",record,1)[0];d=(target-(pc+2))&0xffff
        if d>=0xff80:d-=0x10000
        if not -128<=d<=127:raise ProjectionError("DJNZ range")
        return bytes([0x10,d&255])
    if k==RET:return bytes([0xC9 if record[1]==255 else 0xC0+record[1]*8])
    if k==BITOP:return bytes([0xCB,(0x40,0x80,0xC0)[record[1]]+record[2]*8+record[3]])
    if k==BITOP_INDEX:return bytes([0xDD if record[3]==0 else 0xFD,0xCB,record[4],(0x40,0x80,0xC0)[record[1]]+record[2]*8+6])
    if k==SHIFT:return bytes([0xCB,SHIFT_BASE[record[1]]+record[2]])
    if k==PUSHPOP:
        pop=record[1];pair=record[2]
        if pair<4:return bytes([(0xC1 if pop else 0xC5)+pair*0x10])
        return bytes([0xDD if pair==4 else 0xFD,0xE1 if pop else 0xE5])
    if k==EX:return (b"\xeb",b"\xe3",b"\x08")[record[1]]
    if k==IM:return b"\xed"+bytes([{0:0x46,1:0x56,2:0x5e}[record[1]]])
    if k==INOUT:return b"\xed"+bytes([0x78 if record[1]==0 else 0x79])
    if k==OUT_N_A:return bytes([0xD3,record[1]])
    if k==DB:return bytes([record[1]])
    if k==DW:
        v=struct.unpack_from("<H",record,1)[0];return struct.pack("<H",v)
    if k==DS:
        count,fill=struct.unpack_from("<HB",record,1);return bytes([fill])*count
    if k==RST:
        v=struct.unpack_from("<H",record,1)[0]
        if v>0x38 or v&7:raise ProjectionError("RST")
        return bytes([0xC7|v])
    raise ProjectionError(f"unknown record kind {k}")

def record_length(blob:bytes,pos:int)->int:
    k=blob[pos]
    sizes={FIXED:2,LD_R_R:3,LD_R_N:4,LD_R_MEMHL:2,LD_MEMHL_R:2,LD_MEMHL_N:3,
      LD_A_MEMPAIR:2,LD_MEMPAIR_A:2,LD_A_MEMABS:3,LD_MEMABS_A:3,LD_RR_N:4,
      LD_RR_MEM:4,LD_MEMABS_RR:4,LD_INDEX_N:4,LD_INDEX_MEM:4,LD_MEMABS_INDEX:4,
      LD_SP_INDEX:2,LD_SPECIAL:2,LD_INDEX_R:5,LD_INDEX_N8:4,ALU_R:3,ALU_N:4,
      ALU_INDEX:4,INCDEC_R:3,INCDEC_RR:3,ADD_HL_RR:2,ADC_SBC_HL_RR:3,
      ADD_INDEX_RR:3,JP_CALL:5,JR:4,DJNZ:3,RET:2,BITOP:4,BITOP_INDEX:5,
      SHIFT:3,PUSHPOP:3,EX:2,IM:2,INOUT:2,DB:3,DW:3,DS:5,RST:3,OUT_N_A:2}
    return sizes[k]

def build_projection(listing:Path,sym:Path)->tuple[bytes,bytes,list[dict]]:
    syms=symbols(sym); records=[]; audit=[]; ref=bytearray(); pc=KERNEL_BASE
    for addr,src in listing_statements(listing):
        if not (KERNEL_BASE<=addr<=0xffff):continue
        if addr!=pc:
            # Labels/non-emitting lines are filtered. Any real gap must come from an emitting directive.
            if addr<pc: continue
            raise ProjectionError(f"source projection gap {pc:#06x}->{addr:#06x} before {src!r}")
        try: rs=encode_source(src,addr,syms)
        except Exception as exc: raise ProjectionError(f"{listing}:{addr:#06x}: {src}: {exc}") from exc
        for r in rs:
            out=encode_record(r,pc)
            records.append(r); ref.extend(out)
            audit.append({"address":pc,"source":strip_label(src),"kind":r[0],"length":len(out)})
            pc=(pc+len(out))&0xffff
    if len(ref)>KERNEL_SIZE:raise ProjectionError(f"projection emitted {len(ref)} bytes")
    if len(ref)<KERNEL_SIZE:
        # Canonical top-level final reserves are source directives but some listing modes
        # elide their expanded bytes. Parse them from kernel.asm is intentionally not
        # guessed here; fail closed so the caller can expose any missing source line.
        raise ProjectionError(f"projection emitted only {len(ref)} of {KERNEL_SIZE} bytes")
    body=b"".join(records)
    header=bytearray(16)
    header[:4]=MAGIC;header[4]=VERSION
    struct.pack_into("<H",header,6,len(records))
    struct.pack_into("<H",header,8,len(ref))
    struct.pack_into("<H",header,10,len(body))
    struct.pack_into("<H",header,12,crc16(body))
    struct.pack_into("<H",header,14,crc16(bytes(header[:14])+b"\0\0"))
    return bytes(header)+body,bytes(ref),audit

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--listing",type=Path,required=True)
    ap.add_argument("--symbols",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    ap.add_argument("--audit",type=Path,required=True)
    ap.add_argument("--kernel",type=Path)
    args=ap.parse_args()
    projection,reference,audit=build_projection(args.listing,args.symbols)
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_bytes(projection)
    report={"schema":1,"format":"NSP1 semantic tokenized source","records":len(audit),
      "projection_size":len(projection),"text_size":len(reference),
      "projection_sha256":hashlib.sha256(projection).hexdigest(),
      "semantic_reference_sha256":hashlib.sha256(reference).hexdigest(),
      "contains_preassembled_kernel_payload":False,"audit":audit}
    if args.kernel:
        kernel=args.kernel.read_bytes()
        if len(kernel)!=KERNEL_SIZE:raise ProjectionError("kernel oracle size")
        if reference!=kernel:
            n=min(len(reference),len(kernel));off=next((i for i in range(n) if reference[i]!=kernel[i]),n)
            raise ProjectionError(f"semantic source projection differs from kernel oracle at offset {off:#x}")
        report["kernel_oracle_sha256"]=hashlib.sha256(kernel).hexdigest()
        report["semantic_reference_equals_kernel_oracle"]=True
    args.audit.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(f"records={len(audit)}")
    print(f"projection_size={len(projection)}")
    print(f"text_size={len(reference)}")
    print(f"projection_sha256={report['projection_sha256']}")
    print(f"semantic_reference_sha256={report['semantic_reference_sha256']}")
    print("ZX-UX NATIVE KERNEL SOURCE PROJECTION PASS")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
