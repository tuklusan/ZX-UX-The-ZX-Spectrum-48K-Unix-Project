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
import phase3_open_descriptions
import phase3_pipe_create

BUF=0x7FF0

class Phase3RWValidationError(DriverError): pass

def require(c: bool,m: str)->None:
    if not c: raise Phase3RWValidationError(m)

def _word(v:int)->bytes: return bytes((v&255,(v>>8)&255))
def _jp_nc(a:int)->bytes: return b"\xD2"+_word(a)

def _source_contract(root:Path)->list[dict[str,object]]:
    s=(root/"v1/src/kernel/syscall.asm").read_text(encoding="utf-8")
    prep=s[s.index("zx48_sys_rw_prepare:"):s.index("; E=handle,D=0,HL=buffer,BC=count.")]
    read=s[s.index("zx48_sys_read:"):s.index("zx48_sys_write:")]
    write=s[s.index("zx48_sys_write:"):s.index("zx48_sys_zero_result:")]
    vr=s[s.index("zx48_user_range_validate:"):s.index("    ENDM",s.index("zx48_user_range_validate:"))]
    return [
      {"name":"rw-validates-d-zero-first","passed":"ld de,(syscall_arg_de)\n    ld a,d\n    or a" in prep},
      {"name":"rw-validates-handle","passed":"call zx48_handle_lookup" in prep},
      {"name":"rw-validates-access","passed":"ld a,(ix+OD_ACCESS_O)\n    and b" in prep},
      {"name":"zero-count-before-buffer-validation","passed":"ld bc,(syscall_arg_bc)\n    ld a,b\n    or c\n    ret z" in prep},
      {"name":"nonzero-validates-full-range","passed":"call zx48_user_range_validate" in prep},
      {"name":"read-zero-returns-hl0","passed":"jr z,zx48_sys_zero_result" in read},
      {"name":"write-zero-returns-hl0","passed":"jr z,zx48_sys_zero_result" in write},
      {"name":"read-register-contract","passed":"ld hl,(syscall_arg_hl)" in read and "ld bc,(syscall_arg_bc)" in read},
      {"name":"write-register-contract","passed":"ld hl,(syscall_arg_hl)" in write and "ld bc,(syscall_arg_bc)" in write},
      {"name":"range-rejects-wrap","passed":"add hl,bc\n    jr c,zx48_user_range_wrap" in vr},
      {"name":"range-separates-display-and-arena","passed":"cp $5B" in vr and "cp $60" in vr and "cp $E0" in vr},
    ]

def _fixture(root:Path,s:dict[str,int],kernel:bytes)->None:
    code=bytearray()
    phase3_pipe_create._setup(code,s)
    code += b"\x21"+_word(0xA100)+phase1._call(s["zx48_pipe_create"])+phase1._jp_c(FAIL_PC)
    guard=BUF
    code += phase3_pipe_create._store_byte(guard,0xA5)
    # Invalid D must fail even when count zero.
    code += b"\x21"+_word(guard)+b"\x11\x00\x01\x01\x00\x00"
    code += bytes((0x3E,s["SYS_READ"]))+phase1._call(s["zx48_syscall_impl"])
    code += _jp_nc(FAIL_PC)+bytes((0xFE,s["E_INVAL"]))+phase1._jp_nz(FAIL_PC)
    phase3_pipe_create._assert_byte(code,guard,0xA5)
    # Invalid handle must fail with count zero without touching poisoned buffer.
    code += b"\x21\x00\x00\x11\x07\x00\x01\x00\x00"
    code += bytes((0x3E,s["SYS_READ"]))+phase1._call(s["zx48_syscall_impl"])
    code += _jp_nc(FAIL_PC)
    # Valid /dev/null write handle 1, zero count, invalid buffer accepted untouched.
    code += b"\x21\x00\x00\x11\x01\x00\x01\x00\x00"
    code += bytes((0x3E,s["SYS_WRITE"]))+phase1._call(s["zx48_syscall_impl"])+phase1._jp_c(FAIL_PC)
    code += phase1._ld_de(0)+b"\xB7\xED\x52"+phase1._jp_nz(FAIL_PC)
    # Nonzero wraparound buffer rejected.
    code += b"\x21\xF0\xFF\x11\x01\x00\x01\x20\x00"
    code += bytes((0x3E,s["SYS_WRITE"]))+phase1._call(s["zx48_syscall_impl"])
    code += _jp_nc(FAIL_PC)+bytes((0xFE,s["E_INVAL"]))+phase1._jp_nz(FAIL_PC)
    code += phase1._jp(PASS_PC)
    run_sna(root,bytes(code),patch=phase1._kernel_patch(kernel))

def dispatch(root:Path,action:str,step:str,*,sha256_file:Callable[[Path],str],run_command:Callable[...,Any],require_project_tool:Callable[[Path,str|Path],Path]):
    if step!="P3.15": raise DriverError(f"Phase-3 rw-validation step is not registered: {step}")
    assertions=_source_contract(root)
    require(all(x["passed"] for x in assertions),f"static P3.15 contract failures: {[x['name'] for x in assertions if not x['passed']]}")
    result,kernel,listing=phase1._assemble_kernel(root,run_command,require_project_tool)
    syms=phase3_open_descriptions._symbols(listing.with_suffix(".sym"),(
      "zx48_memory_init","zx48_process_init","zx48_handles_init","zx48_pipe_init","zx48_process_prepare_pid1",
      "zx48_syscall_impl","zx48_pipe_create","SYS_READ","SYS_WRITE","E_INVAL","current_pid"
    ))
    if action=="test":
      _fixture(root,syms,kernel.read_bytes())
      assertions += [
        {"name":"zero-count-validates-nonbuffer-args","passed":True},
        {"name":"zero-count-never-dereferences-buffer","passed":True},
        {"name":"wraparound-range-rejected","passed":True},
      ]
    return [result],{
      "v1/build/kernel.bin":sha256_file(kernel),
      "v1/src/kernel/syscall.asm":sha256_file(root/"v1/src/kernel/syscall.asm"),
      "v1/tools-host/test-driver/phase3_rw_validation.py":sha256_file(root/"v1/tools-host/test-driver/phase3_rw_validation.py"),
      "v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
      "v1/dist/certification/P3.14.test.json":sha256_file(root/"v1/dist/certification/P3.14.test.json"),
    },assertions
