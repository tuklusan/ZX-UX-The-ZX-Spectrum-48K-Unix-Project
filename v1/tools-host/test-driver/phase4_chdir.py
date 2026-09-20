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

MODULE_BASE=0xC000
DATA_BASE=0xA000
STACK_TOP=0xBFC0

class P431Error(DriverError): pass
def require(ok,msg):
    if not ok: raise P431Error(msg)
def _word(v): return bytes((v&255,(v>>8)&255))
def _jp_nc(a): return b"\xD2"+_word(a)

def _source_contract(root:Path):
    o=(root/"v1/src/kernel/objects.asm").read_text(encoding="utf-8")
    s=(root/"v1/src/kernel/syscall.asm").read_text(encoding="utf-8")
    om=o.split("MACRO EMIT_P431_CHDIR_OBJECT_ROUTINES",1)[1].split("ENDM",1)[0]
    sm=s.split("MACRO EMIT_P431_CHDIR_SYSCALL_ROUTINES",1)[1].split("ENDM",1)[0]
    return [
      {"name":"exact-hl-cstr-contract","passed":"p431_chdir_path" in sm and "zx48_p431_sys_chdir:" in sm},
      {"name":"complete-cstr-range-validation","passed":"call zx48_user_range_validate" in sm and sm.index("call zx48_user_range_validate") < sm.index("jp zx48_p431_chdir")},
      {"name":"fixed-directory-only","passed":"cp PATH_KIND_DIR" in om and "zx48_p431_chdir_noent:" in om},
      {"name":"atomic-commit-after-resolution","passed":om.index("call zx48_path_resolve") < om.index("ld (ix+PROC_CWD),a")},
      {"name":"non-directory-noent","passed":"ld a,E_NOENT" in om},
      {"name":"zero-result-success","passed":"ld hl,0" in om},
    ]

def _assemble(root,run_command,require_project_tool):
    asm=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus")
    build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    fixture=build/"p431-chdir.asm"
    fixture.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
PANIC_SCHEDULER EQU $03
PROC_CWD EQU 28
    ORG $C000
current_pid: db 1
zx48_process_lookup:
    ld ix,fake_process
    xor a
    ret
    INCLUDE "../src/kernel/objects.asm"
    INCLUDE "../src/kernel/syscall.asm"
    EMIT_NAMESPACE_ROUTINES
    EMIT_P431_CHDIR_OBJECT_ROUTINES
    EMIT_USER_RANGE_VALIDATION_ROUTINE
    EMIT_P431_CHDIR_SYSCALL_ROUTINES
fake_process: defs 48,0
    SAVEBIN "p431-chdir.bin",$C000,$-$C000
""",encoding="utf-8",newline="\n")
    res=run_command([asm,"--nologo","--lst=p431-chdir.lst","--sym=p431-chdir.sym","p431-chdir.asm"],cwd=build,timeout_seconds=30.0)
    require(not res.timed_out and res.exit_code==0,f"P4.31 fixture assembly failed: {res.stderr or res.stdout}")
    binary=build/"p431-chdir.bin"; listing=build/"p431-chdir.lst"
    require(binary.is_file() and 0<binary.stat().st_size<16384,"P4.31 fixture missing/oversize")
    return res,binary,listing

def _target(root,s,module):
    cases=[
      ("root",b"/\0",s["DIR_TMP"],s["DIR_ROOT"],None),
      ("absolute-tmp",b"/tmp\0",s["DIR_ROOT"],s["DIR_TMP"],None),
      ("relative-tmp",b"tmp\0",s["DIR_ROOT"],s["DIR_TMP"],None),
      ("dot-preserves",b".\0",s["DIR_TMP"],s["DIR_TMP"],None),
      ("dotdot-userhome",b"..\0",s["DIR_USERHOME"],s["DIR_HOME"],None),
      ("home-user",b"/home/alice\0",s["DIR_ROOT"],s["DIR_USERHOME"],None),
      ("wrong-case",b"/Tmp\0",s["DIR_TMP"],s["DIR_TMP"],s["E_NOENT"]),
      ("non-directory",b"/tmp/file\0",s["DIR_HOME"],s["DIR_HOME"],s["E_NOENT"]),
      ("overlength-component",b"/tmp/abcdefghijk\0",s["DIR_BIN"],s["DIR_BIN"],s["E_TOOLONG"]),
    ]
    for idx,(label,path,start,expected,err) in enumerate(cases):
        addr=DATA_BASE+idx*48
        def patch(ram,addr=addr,path=path,start=start):
            ram[MODULE_BASE-0x4000:MODULE_BASE-0x4000+len(module)]=module
            ram[addr-0x4000:addr-0x4000+len(path)]=path
            ram[s["fake_process"]-0x4000+s["PROC_CWD"]]=start
            ram[s["session_user_len"]-0x4000]=5
            ram[s["session_user"]-0x4000:s["session_user"]-0x4000+6]=b"alice\0"
        code=bytearray(b"\xF3"+phase1._ld_sp(STACK_TOP)+phase1._ld_hl(addr)+phase1._call(s["zx48_p431_sys_chdir"]))
        if err is None:
            code+=phase1._jp_c(FAIL_PC)
        else:
            code+=_jp_nc(FAIL_PC)+bytes((0xFE,err))+phase1._jp_nz(FAIL_PC)
        code+=b"\x3A"+_word(s["fake_process"]+s["PROC_CWD"])+bytes((0xFE,expected))+phase1._jp_nz(FAIL_PC)+phase1._jp(PASS_PC)
        try: run_sna(root,bytes(code),patch=patch)
        except DriverError as exc: raise P431Error(f"P4.31 case failed: {label}: {exc}") from exc

    # Unterminated path hitting protected display/ROM-compatible boundary must fail
    # before cwd mutation.
    addr=0x5AFF
    def patch_bad(ram):
        ram[MODULE_BASE-0x4000:MODULE_BASE-0x4000+len(module)]=module
        ram[addr-0x4000]=ord("x")
        ram[s["fake_process"]-0x4000+s["PROC_CWD"]]=s["DIR_TMP"]
    code=bytearray(b"\xF3"+phase1._ld_sp(STACK_TOP)+phase1._ld_hl(addr)+phase1._call(s["zx48_p431_sys_chdir"]))
    code+=_jp_nc(FAIL_PC)+bytes((0xFE,s["E_INVAL"]))+phase1._jp_nz(FAIL_PC)
    code+=b"\x3A"+_word(s["fake_process"]+s["PROC_CWD"])+bytes((0xFE,s["DIR_TMP"]))+phase1._jp_nz(FAIL_PC)+phase1._jp(PASS_PC)
    run_sna(root,bytes(code),patch=patch_bad)

def dispatch(root,action,step,*,sha256_file,run_command,require_project_tool):
    if step!="P4.31": raise DriverError(f"Phase-4 chdir step is not registered: {step}")
    assertions=_source_contract(root)
    bad=[a["name"] for a in assertions if a.get("passed") is not True]
    require(not bad,f"P4.31 static failures: {bad}")
    kcmd,kernel,_=phase1._assemble_kernel(root,run_command,require_project_tool)
    fcmd,binary,listing=_assemble(root,run_command,require_project_tool)
    names=("zx48_p431_sys_chdir","fake_process","session_user_len","session_user","PROC_CWD",
           "DIR_ROOT","DIR_BIN","DIR_HOME","DIR_USERHOME","DIR_TMP","E_INVAL","E_NOENT","E_TOOLONG")
    symbols=phase3_open_descriptions._symbols(listing.with_suffix(".sym"),names)
    if action=="test":
        _target(root,symbols,binary.read_bytes())
        assertions += [
          {"name":"absolute-relative-dot-dotdot-runtime","passed":True},
          {"name":"current-session-home-runtime","passed":True},
          {"name":"wrong-case-nondir-overlength-runtime","passed":True},
          {"name":"all-failures-cwd-byte-identical","passed":True},
          {"name":"invalid-user-range-before-mutation","passed":True},
        ]
    hashes={
      "v1/build/kernel.bin":sha256_file(kernel),
      "v1/build/p431-chdir.bin":sha256_file(binary),
      "v1/src/kernel/objects.asm":sha256_file(root/"v1/src/kernel/objects.asm"),
      "v1/src/kernel/syscall.asm":sha256_file(root/"v1/src/kernel/syscall.asm"),
      "v1/tools-host/test-driver/phase4_chdir.py":sha256_file(root/"v1/tools-host/test-driver/phase4_chdir.py"),
      "v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
      "v1/dist/certification/P4.30.test.json":sha256_file(root/"v1/dist/certification/P4.30.test.json"),
    }
    return [kcmd,fcmd],hashes,assertions
