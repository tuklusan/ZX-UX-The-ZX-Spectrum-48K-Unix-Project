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
import argparse, hashlib, json, struct
from pathlib import Path

MAGIC=b"M48O\x01"
TYPE_ASM=4
USERHOME=5
FLAG=0xff
CHUNK=512

def crc16(data:bytes)->int:
    c=0xffff
    for v in data:
        c^=v<<8
        for _ in range(8):
            c=((c<<1)^0x1021)&0xffff if c&0x8000 else (c<<1)&0xffff
    return c

def rom_block(payload:bytes)->bytes:
    body=bytes((FLAG,))+payload
    x=0
    for v in body:x^=v
    body+=bytes((x,))
    return struct.pack("<H",len(body))+body

def header(name:str,payload:bytes)->bytes:
    nb=name.encode("ascii")
    if not 1<=len(nb)<=10 or any(x not in b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-." for x in nb) or name in (".",".."):
        raise ValueError("invalid M48O name")
    if len(payload)>32768:raise ValueError("M48O logical payload too large")
    h=bytearray(32);h[:5]=MAGIC;h[5]=TYPE_ASM;h[6]=0;h[7]=USERHOME
    struct.pack_into("<HHHH",h,8,len(payload),len(payload),0,crc16(payload))
    h[16:16+len(nb)]=nb
    struct.pack_into("<H",h,26,crc16(h))
    return bytes(h)

def make(name:str,payload:bytes)->bytes:
    h=header(name,payload)
    return rom_block(h)+b"".join(rom_block(payload[i:i+CHUNK]) for i in range(0,len(payload),CHUNK))

def blocks(data:bytes)->list[bytes]:
    o=[];p=0
    while p<len(data):
        if p+2>len(data):raise ValueError("truncated TAP length")
        n=struct.unpack_from("<H",data,p)[0];p+=2
        if n<2 or p+n>len(data):raise ValueError("bad TAP block length")
        b=data[p:p+n];p+=n;x=0
        for v in b:x^=v
        if x:raise ValueError("ROM TAP checksum mismatch")
        if b[0]!=FLAG:raise ValueError("wrong ROM block flag")
        o.append(b[1:-1])
    if p!=len(data):raise ValueError("TAP trailing bytes")
    return o

def decode(data:bytes,expected_name:str)->tuple[bytes,bytes,int]:
    bs=blocks(data)
    if not bs or len(bs[0])!=32:raise ValueError("missing exact M48O header")
    raw_h=bytes(bs[0]);h=bytearray(raw_h)
    if h[:5]!=MAGIC or h[5]!=TYPE_ASM or h[6]!=0 or h[7]!=USERHOME:raise ValueError("wrong M48O source envelope")
    if any(h[28:]):raise ValueError("reserved M48O bytes nonzero")
    field=bytes(h[16:26]);name=field.split(b"\0",1)[0]
    if name!=expected_name.encode("ascii"):raise ValueError("wrong M48O source name")
    if len(name)<10 and any(field[len(name)+1:]):raise ValueError("nonzero M48O name padding")
    hc=struct.unpack_from("<H",h,26)[0];h[26:28]=b"\0\0"
    if crc16(h)!=hc:raise ValueError("M48O header CRC mismatch")
    storage,logical,codec,pcrc=struct.unpack_from("<HHHH",h,8)
    if codec or storage!=logical:raise ValueError("source M48O is not RAW")
    chunks=bs[1:]
    expected_chunks=(logical+CHUNK-1)//CHUNK if logical else 0
    if len(chunks)!=expected_chunks:raise ValueError("M48O payload block count mismatch")
    if any(not 1<=len(x)<=CHUNK for x in chunks):raise ValueError("invalid M48O payload chunk size")
    if chunks and any(len(x)!=CHUNK for x in chunks[:-1]):raise ValueError("short non-final M48O payload chunk")
    payload=b"".join(chunks)
    if len(payload)!=logical:raise ValueError("M48O chunk coverage mismatch")
    if crc16(payload)!=pcrc:raise ValueError("M48O payload CRC mismatch")
    return raw_h,payload,hc

def sha(b:bytes)->str:return hashlib.sha256(b).hexdigest()

def main()->int:
    ap=argparse.ArgumentParser();ap.add_argument("--source",type=Path,required=True);ap.add_argument("--output",type=Path,required=True);ap.add_argument("--report",type=Path,required=True);ap.add_argument("--name",default="kernel.asm")
    a=ap.parse_args();src=a.source.read_bytes()
    if b"\r" in src or not src.endswith(b"\n"):raise SystemExit("source is not canonical LF text")
    if a.name!="kernel.asm":raise SystemExit("expanded pre-release kernel source name must be kernel.asm")
    tap=make(a.name,src);h,out,hcrc=decode(tap,a.name)
    if out!=src:raise SystemExit("independent TAP decode differs from source")
    if hashlib.sha256(out).digest()!=hashlib.sha256(src).digest():raise SystemExit("decoded source SHA-256 mismatch")
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_bytes(tap)
    d={"schema":1,"kind":"phase11-pre-release-native-kernel-source-tap","name":a.name,
       "object_type":TYPE_ASM,"target":USERHOME,"flags":0,"codec":0,
       "source_size":len(src),"source_sha256":sha(src),"tap_size":len(tap),"tap_sha256":sha(tap),
       "header_crc16":hcrc,"payload_crc16":crc16(src),
       "payload_blocks":(len(src)+CHUNK-1)//CHUNK,"max_payload_chunk":CHUNK,
       "decoded_source_identity":"PASS"}
    a.report.write_text(json.dumps(d,indent=2,sort_keys=True)+"\n",encoding="utf-8",newline="\n")
    print("P11 PRE-RELEASE KERNEL SOURCE TAP PASS")
    return 0
if __name__=="__main__":raise SystemExit(main())
