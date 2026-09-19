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

from pathlib import Path
from typing import Any, Callable
from driver_core import DriverError
from fuse_harness import FAIL_PC, PASS_PC, run_sna
import phase1, phase3_null, phase3_open_descriptions, phase3_tty

GUARD=0xA180
class P319Error(DriverError): pass
def require(c,m):
    if not c: raise P319Error(m)
def w(v): return bytes((v&255,(v>>8)&255))
def jp_nc(a): return b"\xD2"+w(a)
def err(code,e): code += jp_nc(FAIL_PC)+bytes((0xFE,e&255))+phase1._jp_nz(FAIL_PC)
def hl_eq(code,v): code += phase1._ld_de(v)+b"\xB7\xED\x52"+phase1._jp_nz(FAIL_PC)

def oracle(start,length):
    if length==0: return (True,start)
    end=int(start)+int(length)
    if end<=start or end>0x10000: return (False,end)
    last=end-1
    same=(0x4000<=start<=0x5AFF and 0x4000<=last<=0x5AFF) or (0x6000<=start<=0xDFFF and 0x6000<=last<=0xDFFF)
    return (same,end)

def source_contract(root):
    s=(root/"v1/src/kernel/syscall.asm").read_text()
    v=s[s.index("zx48_user_range_validate:"):s.index("    ENDM",s.index("zx48_user_range_validate:"))]
    p=s[s.index("zx48_sys_rw_prepare:"):s.index("; E=handle,D=0,HL=buffer,BC=count.")]
    q=s[s.index("zx48_sys_spawn_preflight:"):s.index("    ENDM",s.index("zx48_sys_spawn_preflight:"))]
    return [
      {"name":"target-validator-uses-17th-bit-carry-before-region-decision","passed":"add hl,bc" in v and "jr c,zx48_user_range_wrap" in v},
      {"name":"target-validator-enforces-single-display-or-user-arena-region","passed":all(x in v for x in ("cp $5B","cp $60","cp $E0"))},
      {"name":"zero-count-validates-handle-before-skipping-buffer","passed":p.index("call zx48_handle_lookup")<p.index("ret z")<p.index("call zx48_user_range_validate")},
      {"name":"bounded-path-scan-validates-each-byte-before-dereference","passed":"ld bc,1\n    call zx48_user_range_validate" in q and "ld a,E_TOOLONG" in q},
    ]

def matrix(root,s,kernel):
    code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)); phase3_null._setup(code,s); code+=phase3_null._store_byte(GUARD,0xA5)
    vectors=((0xDFF0,0x0030,False),(0xFFF0,0x0020,False),(0x5AF0,0x0020,False),(0x7FF0,0x0020,True))
    for ptr,count,ok in vectors:
        accepted,end=oracle(ptr,count); require(accepted==ok,f"host widened oracle mismatch {ptr:04x}+{count:04x} end={end:05x}")
        phase3_tty._call_sys(code,s,s["SYS_WRITE"],ptr,0,count)
        if ok: code+=phase1._jp_c(FAIL_PC); hl_eq(code,count)
        else: err(code,s["E_INVAL"])
    phase3_tty._call_sys(code,s,s["SYS_READ"],0x0000,0,0); code+=phase1._jp_c(FAIL_PC); hl_eq(code,0)
    phase3_tty._call_sys(code,s,s["SYS_READ"],0x0000,7,0); err(code,s["E_NOENT"])
    code+=phase3_null._load_byte(GUARD)+b"\xFE\xA5"+phase1._jp_nz(FAIL_PC)
    code+=phase1._jp(PASS_PC); run_sna(root,bytes(code),patch=phase1._kernel_patch(kernel))

def dispatch(root,action,step,*,sha256_file:Callable[[Path],str],run_command:Callable[...,Any],require_project_tool:Callable[[Path,str|Path],Path]):
    if step!="P3.19": raise P319Error("wrong step")
    assertions=source_contract(root); require(all(x["passed"] for x in assertions),"P3.19 static contract failure")
    r,k,l=phase1._assemble_kernel(root,run_command,require_project_tool)
    s=phase3_open_descriptions._symbols(l.with_suffix(".sym"),("zx48_memory_init","zx48_process_init","zx48_handles_init","zx48_process_prepare_pid1","zx48_od_create","zx48_handle_install","zx48_syscall_impl","current_pid","OD_KIND_NULL","O_READ","O_WRITE","SYS_READ","SYS_WRITE","E_INVAL","E_NOENT"))
    if action=="test":
        matrix(root,s,k.read_bytes())
        assertions += [
          {"name":"widened-end-dff0-plus-0030-rejected-pre-side-effect","passed":True,"end_exclusive":0xE020},
          {"name":"widened-end-fff0-plus-0020-rejected-pre-side-effect","passed":True,"end_exclusive":0x10010},
          {"name":"display-workspace-bridge-5af0-plus-0020-rejected","passed":True,"end_exclusive":0x5B10},
          {"name":"7ff0-plus-0020-accepted-within-single-user-arena-region","passed":True,"end_exclusive":0x8010},
          {"name":"zero-count-poison-pointer-not-dereferenced-valid-handle","passed":True},
          {"name":"zero-count-poison-pointer-invalid-handle-still-errors","passed":True},
        ]
    return [r],{"v1/build/kernel.bin":sha256_file(k),"v1/src/kernel/syscall.asm":sha256_file(root/"v1/src/kernel/syscall.asm"),"v1/tools-host/test-driver/phase3_widened_ranges.py":sha256_file(root/"v1/tools-host/test-driver/phase3_widened_ranges.py"),"v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),"v1/dist/certification/P3.18.test.json":sha256_file(root/"v1/dist/certification/P3.18.test.json")},assertions
