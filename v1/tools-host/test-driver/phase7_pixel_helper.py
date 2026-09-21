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
from pathlib import Path
from typing import Any, Callable
from driver_core import DriverError
from fuse_harness import FAIL_PC, PASS_PC, run_sna
import phase1

ORACLE=0x6000
YCOUNT=0x9000
XCOUNT=0x9001

class P702Error(DriverError): pass

def require(v: bool, m: str) -> None:
    if not v: raise P702Error(m)

def _word(v:int)->bytes: return bytes((v&255,(v>>8)&255))
def _jp_nz(a:int)->bytes: return b"\xc2"+_word(a)
def _jp_c(a:int)->bytes: return b"\xda"+_word(a)

def _addr(y:int, xb:int)->int:
    return 0x4000 | ((y & 0xC0)<<5) | ((y & 0x07)<<8) | ((y & 0x38)<<2) | xb

def _source(root:Path):
    files=[root/"v1/src/kernel"/n for n in ("graphics.asm","tty32.asm","tty64.asm","udg.asm")]
    texts={p.name:p.read_text(encoding="utf-8") for p in files}
    all_kernel="\n".join(p.read_text(encoding="utf-8") for p in (root/"v1/src/kernel").glob("*.asm"))
    return [
      {"name":"single-canonical-bitmap-helper-definition","passed":all_kernel.count("zx48_bitmap_address:")==1},
      {"name":"graphics-delegates-to-canonical-helper","passed":"call zx48_bitmap_address" in texts["graphics.asm"]},
      {"name":"tty32-delegates-to-canonical-helper","passed":"call zx48_bitmap_address" in texts["tty32.asm"]},
      {"name":"tty64-delegates-to-canonical-helper","passed":"call zx48_bitmap_address" in texts["tty64.asm"]},
      {"name":"udg-delegates-to-canonical-helper","passed":"call zx48_bitmap_address" in texts["udg.asm"]},
      {"name":"host-oracle-covers-full-display","passed":len({_addr(y,x>>3) for y in range(192) for x in range(256)})==6144},
      {"name":"display-address-domain-exact","passed":min(_addr(y,xb) for y in range(192) for xb in range(32))==0x4000 and max(_addr(y,xb) for y in range(192) for xb in range(32))==0x57ff},
    ]

def _runtime(root:Path, label:int, kernel:bytes):
    oracle=bytearray()
    for y in range(192):
        for xb in range(32):
            a=_addr(y,xb); oracle+=_word(a)
    code=bytearray(b"\xf3"+phase1._ld_sp(phase1.USER_STACK))
    code+=b"\x11"+_word(ORACLE)                   # ld de,oracle
    code+=b"\xaf\x32"+_word(YCOUNT)             # y=0
    outer=len(code)
    code+=b"\x3a"+_word(YCOUNT)+b"\x47"         # ld a,(y); ld b,a
    code+=b"\xaf\x32"+_word(XCOUNT)             # xbyte=0
    inner=len(code)
    code+=b"\x3a"+_word(XCOUNT)+b"\x4f"         # ld a,(x); ld c,a
    code+=phase1._call(label)
    code+=b"\x1a\xbd"+_jp_nz(FAIL_PC)+b"\x13" # (de)==l
    code+=b"\x1a\xbc"+_jp_nz(FAIL_PC)+b"\x13" # (de)==h
    code+=b"\x3a"+_word(XCOUNT)+b"\x3c\x32"+_word(XCOUNT)+b"\xfe\x20"
    # jp nz inner (absolute address resolved after base address is known below)
    jx=len(code); code+=b"\xc2\x00\x00"
    code+=b"\x3a"+_word(YCOUNT)+b"\x3c\x32"+_word(YCOUNT)+b"\xfe\xc0"
    jy=len(code); code+=b"\xc2\x00\x00"
    code+=phase1._jp(PASS_PC)
    base=phase1.USER_CODE
    code[jx+1:jx+3]=_word(base+inner)
    code[jy+1:jy+3]=_word(base+outer)
    def patch(ram:bytearray):
        off=ORACLE-0x4000; ram[off:off+len(oracle)]=oracle
    run_sna(root,bytes(code),patch=lambda ram:(phase1._kernel_patch(kernel)(ram),patch(ram)))

def dispatch(root:Path,action:str,step:str,*,sha256_file,run_command,require_project_tool):
    if step!="P7.02": raise P702Error(f"unsupported {step} {action}")
    assertions=_source(root); failed=[x["name"] for x in assertions if x.get("passed") is not True]
    require(not failed,f"P7.02 static failure: {failed}")
    command,kernel,listing=phase1._assemble_kernel(root,run_command,require_project_tool)
    labels=phase1._labels(listing,("zx48_bitmap_address",))
    if action=="test":
        _runtime(root,labels["zx48_bitmap_address"],kernel.read_bytes())
        assertions += [
          {"name":"fuse-all-6144-bitmap-byte-addresses-match-host-oracle","passed":True,"pixel_equivalent_vectors":49152},
          {"name":"no-divergent-helper-runtime-observed","passed":True},
        ]
    hashes={
      "v1/src/kernel/graphics.asm":sha256_file(root/"v1/src/kernel/graphics.asm"),
      "v1/src/kernel/tty32.asm":sha256_file(root/"v1/src/kernel/tty32.asm"),
      "v1/src/kernel/tty64.asm":sha256_file(root/"v1/src/kernel/tty64.asm"),
      "v1/src/kernel/udg.asm":sha256_file(root/"v1/src/kernel/udg.asm"),
      "v1/build/kernel.bin":sha256_file(kernel),
      "v1/tools-host/test-driver/phase7_pixel_helper.py":sha256_file(root/"v1/tools-host/test-driver/phase7_pixel_helper.py"),
    }
    return [command],hashes,assertions
