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

ROM_UDG=0x5C7B
BANK=0x6000
BITMAP=0x4000
class P713Error(DriverError): pass
def require(v:bool,m:str)->None:
    if not v: raise P713Error(m)
def w(v:int)->bytes:return bytes((v&255,(v>>8)&255))
def call(a:int)->bytes:return b"\xcd"+w(a)
def jp(a:int)->bytes:return b"\xc3"+w(a)
def jpc(a:int)->bytes:return b"\xda"+w(a)
def jpnc(a:int)->bytes:return b"\xd2"+w(a)
def st(a:int,v:int)->bytes:return bytes((0x3e,v&255,0x32))+w(a)
def ex(a:int,v:int)->bytes:return b"\x3a"+w(a)+bytes((0xfe,v&255))+phase1._jp_nz(FAIL_PC)
def exw(a:int,v:int)->bytes:return ex(a,v&255)+ex(a+1,(v>>8)&255)

def source(root:Path):
    u=(root/"v1/src/kernel/udg.asm").read_text()
    t=(root/"v1/src/kernel/tty32.asm").read_text()
    c=(root/"v1/src/kernel/console.asm").read_text()
    p=(root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md").read_text()
    init=u.split("zx48_udg_init:",1)[1].split("zx48_udg_slot_ptr:",1)[0]
    return [
      {"name":"canonical-p713-present","passed":"## P7.13 - UDG subsystem on boot-pinned 32-slot bank" in p},
      {"name":"exact-slot-count-size-code-range","passed":all(x in u for x in ("UDG_SLOT_COUNT           EQU 32","UDG_SLOT_BYTES           EQU 8","UDG_CODE_FIRST           EQU $80","UDG_CODE_LAST            EQU $9F"))},
      {"name":"reuses-p114-single-cold-pinned-bank","passed":init.count("call zx48_alloc")==1 and "ALLOC_COLD_PREFERRED" in init and "ld (ROM_UDG),hl" in init and "call zx48_memory_pin_bytes" in init},
      {"name":"no-second-bank-or-free-repoint","passed":u.count("call zx48_alloc")==1 and "call zx48_free" not in u and u.count("ld (ROM_UDG),hl")==1},
      {"name":"tty32-maps-80-through-9f-to-existing-bank","passed":"ld hl,(udg_bank_ptr)" in t and "sub UDG_CODE_FIRST" in t and "cp UDG_CODE_LAST+1" in t},
      {"name":"glyph-byte-is-copied-without-bit-reversal","passed":"ld a,(hl)\n    inc hl\n    ld (tty32_glyph),hl" in t and "ld (hl),a" in t},
      {"name":"console-admits-only-through-final-udg-code","passed":"cp UDG_CODE_LAST+1" in c},
      {"name":"tty64-renderer-rejects-udg-text-codes","passed":"cp $80" in (root/"v1/src/kernel/tty64.asm").read_text()},
    ]

def runtime(root:Path,labels:dict[str,int],image:bytes):
    code=bytearray(b"\xf3"+phase1._ld_sp(phase1.USER_STACK))
    code+=call(labels["zx48_memory_init"])+call(labels["zx48_udg_init"])+jpc(FAIL_PC)
    code+=exw(labels["udg_bank_ptr"],BANK)+exw(ROM_UDG,BANK)
    code+=exw(labels["memory_pinned_bytes"],0x100)+exw(labels["memory_live_allocations"],1)
    # Slot 0 row0 = 80h (leftmost pixel), slot31 row0 = 01h (rightmost pixel).
    code+=st(BANK,0x80)+st(BANK+31*8,0x01)
    code+=st(labels["tty_row"],0)+st(labels["tty_col"],0)+bytes((0x3e,0x80))+call(labels["zx48_tty32_draw_char"])+jpc(FAIL_PC)
    code+=ex(BITMAP,0x80)
    code+=st(labels["tty_col"],1)+bytes((0x3e,0x9f))+call(labels["zx48_tty32_draw_char"])+jpc(FAIL_PC)
    code+=ex(BITMAP+1,0x01)
    # Out-of-range identifier is rejected.
    code+=bytes((0x3e,0xa0))+call(labels["zx48_tty32_draw_char"])+jpnc(FAIL_PC)+bytes((0xfe,1))+phase1._jp_nz(FAIL_PC)
    # tty64 must not interpret 80h as a 4x8 glyph and must not mutate bitmap.
    code+=st(BITMAP+2,0x5a)+bytes((0x3e,0x80))+call(labels["zx48_tty64_draw_char"])+jpnc(FAIL_PC)+bytes((0xfe,1))+phase1._jp_nz(FAIL_PC)+ex(BITMAP+2,0x5a)
    code+=exw(labels["udg_bank_ptr"],BANK)+exw(ROM_UDG,BANK)+exw(labels["memory_live_allocations"],1)
    code+=jp(PASS_PC)
    run_sna(root,bytes(code),patch=phase1._kernel_patch(image),timeout=20.0)

def dispatch(root:Path,action:str,step:str,*,sha256_file:Callable[[Path],str],run_command:Callable[...,Any],require_project_tool:Callable[[Path,str|Path],Path]):
    if step!="P7.13": raise P713Error(f"unsupported {step} {action}")
    assertions=source(root); require(all(x["passed"] for x in assertions),"P7.13 static failure")
    cmd,kernel,lst=phase1._assemble_kernel(root,run_command,require_project_tool)
    labels=phase1._labels(lst,("zx48_memory_init","zx48_udg_init","udg_bank_ptr","memory_pinned_bytes","memory_live_allocations","tty_row","tty_col","zx48_tty32_draw_char","zx48_tty64_draw_char"))
    if action=="test":
        runtime(root,labels,kernel.read_bytes())
        assertions += [
          {"name":"fuse-p114-bank-pointer-and-rom-udg-identity-remain-6000","passed":True},
          {"name":"fuse-slot0-slot31-code-mapping-is-exact","passed":True},
          {"name":"fuse-bit7-leftmost-and-bit0-rightmost-orientation-exact","passed":True},
          {"name":"fuse-tty64-does-not-interpret-udg-as-4x8-text","passed":True},
          {"name":"fuse-one-pinned-256-byte-bank-only","passed":True},
        ]
    hashes={str(p.relative_to(root)):sha256_file(p) for p in (
      root/"v1/src/kernel/udg.asm",root/"v1/src/kernel/tty32.asm",root/"v1/src/kernel/console.asm",
      root/"v1/tools-host/test-driver/phase7_udg_bank.py",root/"v1/tools-host/test-driver/run.py",kernel)}
    return [cmd],hashes,assertions
