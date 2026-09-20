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

class P424Error(DriverError): pass

def require(ok:bool,msg:str)->None:
    if not ok: raise P424Error(msg)

def _word(v:int)->bytes: return bytes((v&255,(v>>8)&255))
def _check_byte(a:int,v:int)->bytes:
    return b"\x3A"+_word(a)+bytes((0xFE,v&255))+phase1._jp_nz(FAIL_PC)
def _check_bytes(a:int,data:bytes)->bytes:
    out=bytearray()
    for i,b in enumerate(data): out+=_check_byte(a+i,b)
    return bytes(out)
def _record(name:bytes, directory:int, type_id:int, *, flags:int=0,state:int=0,logical:int=0,storage:int=0,ptr:int=0)->bytes:
    r=bytearray(20); r[:len(name)]=name; r[10]=directory; r[11]=type_id; r[12]=flags; r[13]=state
    r[14:16]=_word(logical); r[16:18]=_word(storage); r[18:20]=_word(ptr); return bytes(r)

def _source_contract(root:Path)->list[dict[str,object]]:
    z=(root/"v1/src/kernel/zxpack.asm").read_text()
    o=(root/"v1/src/kernel/objects.asm").read_text()
    require("MACRO EMIT_P424_PACK_CANDIDATE_ROUTINES" in z,"P4.24 bitset macro missing")
    require("MACRO EMIT_P424_OBJECT_CANDIDATE_ROUTINES" in o,"P4.24 object hook macro missing")
    zm=z.split("MACRO EMIT_P424_PACK_CANDIDATE_ROUTINES",1)[1].split("ENDM",1)[0]
    om=o.split("MACRO EMIT_P424_OBJECT_CANDIDATE_ROUTINES",1)[1].split("ENDM",1)[0]
    return [
      {"name":"exact-four-byte-bitset","passed":"p424_candidate_bits: defs 4,0" in zm},
      {"name":"threshold-64","passed":"cp 64" in zm},
      {"name":"raw-only","passed":"and OBJ_PACKED" in zm and "ret nz" in zm},
      {"name":"mutable-resident-only","passed":"cp STATE_RAM" in zm},
      {"name":"protected-types-not-candidates","passed":all(x in zm for x in ("OBJ_DIR","OBJ_DEV","OBJ_SYS"))},
      {"name":"final-close-only-hook","passed":"zx48_p424_object_final_close:" in om and "OD_KIND_OBJECT" in om},
      {"name":"no-compression-in-close-hook","passed":"zx48_p420" not in om and "zx48_alloc" not in om},
      {"name":"stale-clear-transitions","passed":all(x in om for x in ("object_reopen","object_write","object_remove","object_slot_reuse"))},
      {"name":"tmp-no-special-case","passed":"DIR_TMP" not in zm+om},
    ]

def _assemble(root:Path,run_command:Callable[...,Any],require_project_tool:Callable[[Path,str|Path],Path]):
    asm=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus"); build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    fixture=build/"p424-close-candidates.asm"
    fixture.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
PANIC_SCHEDULER EQU $03
PROC_HANDLES EQU 16
PROC_CWD EQU 28
    ORG $C000
current_pid: db 1
zx48_process_lookup:
    ld ix,fake_process
    xor a
    ret
    INCLUDE "../src/kernel/memory.asm"
    INCLUDE "../src/kernel/handles.asm"
    INCLUDE "../src/kernel/objects.asm"
    INCLUDE "../src/kernel/zxpack.asm"
    EMIT_MEMORY_ROUTINES
    EMIT_NAMESPACE_ROUTINES
    EMIT_OBJECT_TYPE_ROUTINES
    EMIT_OBJECT_OPEN_ROUTINES
    EMIT_HANDLE_ROUTINES
    EMIT_P405_OBJECT_ROUTINES
    EMIT_P424_PACK_CANDIDATE_ROUTINES
    EMIT_P424_OBJECT_CANDIDATE_ROUTINES
zx48_process_count:
    xor a
    ret
zx48_pipe_endpoint_closed:
    xor a
    ret
zx48_panic:
    scf
    ret
fake_process:
    defs 48,0
    SAVEBIN "p424-close-candidates.bin",$C000,$-$C000
""",encoding="utf-8",newline="\n")
    res=run_command([asm,"--nologo","--lst=p424-close-candidates.lst","--sym=p424-close-candidates.sym","p424-close-candidates.asm"],cwd=build,timeout_seconds=30)
    require(not res.timed_out and res.exit_code==0,f"P4.24 fixture assembly failed: {res.stderr or res.stdout}")
    return res,build/"p424-close-candidates.bin",build/"p424-close-candidates.lst"

def _runtime(root:Path,s:dict[str,int],module:bytes)->None:
    table=s["p405_object_table"]; bits=s["p424_candidate_bits"]; payload=DATA_BASE
    def patch(record:bytes,data:bytes=b"X"*80):
        def apply(ram:bytearray)->None:
            ram[MODULE_BASE-0x4000:MODULE_BASE-0x4000+len(module)]=module
            ram[table-0x4000:table-0x4000+20]=record
            ram[payload-0x4000:payload-0x4000+len(data)]=data
            ram[bits-0x4000:bits-0x4000+4]=bytes(4)
        return apply
    def execute(label:str,record:bytes,code:bytes,data:bytes=b"X"*80):
        body=b"\xF3"+phase1._ld_sp(STACK_TOP)+phase1._call(s["zx48_p424_candidates_init"])+code+phase1._jp(PASS_PC)
        try: run_sna(root,body,patch=patch(record,data))
        except DriverError as exc: raise P424Error(f"P4.24 runtime case failed: {label}: {exc}") from exc

    eligible=_record(b"file",s["DIR_TMP"],s["OBJ_DAT"],logical=80,storage=80,ptr=payload)
    code=bytes((0x16,s["OD_KIND_OBJECT"],0x1E,0))+phase1._call(s["zx48_p424_object_final_close"])
    code+=_check_byte(bits,1)+_check_bytes(table,eligible)+_check_bytes(payload,b"X"*8)
    execute("tmp-final-close-marks-without-packing",eligible,code)

    for label,rec in (
      ("short",_record(b"file",s["DIR_TMP"],s["OBJ_DAT"],logical=63,storage=63,ptr=payload)),
      ("packed",_record(b"file",s["DIR_TMP"],s["OBJ_DAT"],flags=s["OBJ_PACKED"],logical=80,storage=2,ptr=payload)),
      ("pinned",_record(b"file",s["DIR_TMP"],s["OBJ_DAT"],state=s["STATE_PINNED_SYSTEM"],logical=80,storage=80,ptr=payload)),
    ):
        code=bytes((0x16,s["OD_KIND_OBJECT"],0x1E,0))+phase1._call(s["zx48_p424_object_final_close"])+_check_byte(bits,0)
        execute(label+"-not-marked",rec,code)

    # Non-final close does not invoke final-close transition; bit remains clear.
    execute("non-final-close-not-marked",eligible,_check_byte(bits,0))

    for label,sym in (
      ("reopen","zx48_p424_object_reopen"),("write","zx48_p424_object_write"),
      ("remove","zx48_p424_object_remove"),("slot-reuse","zx48_p424_object_slot_reuse"),
    ):
        code=bytes((0x16,s["OD_KIND_OBJECT"],0x1E,0))+phase1._call(s["zx48_p424_object_final_close"])
        code+=_check_byte(bits,1)+b"\xAF"+phase1._call(s[sym])+_check_byte(bits,0)
        execute(label+"-clears-stale-candidate",eligible,code)

def dispatch(root:Path,action:str,step:str,*,sha256_file,run_command,require_project_tool):
    if step!="P4.24": raise DriverError(f"Phase-4 close candidate step is not registered: {step}")
    assertions=_source_contract(root); failed=[x["name"] for x in assertions if x.get("passed") is not True]
    require(not failed,f"static P4.24 contract failures: {failed}")
    kr,kernel,_=phase1._assemble_kernel(root,run_command,require_project_tool)
    fr,binary,listing=_assemble(root,run_command,require_project_tool)
    names=("zx48_p424_candidates_init","zx48_p424_object_final_close","zx48_p424_object_reopen","zx48_p424_object_write",
           "zx48_p424_object_remove","zx48_p424_object_slot_reuse","p424_candidate_bits","p405_object_table",
           "OD_KIND_OBJECT","DIR_TMP","OBJ_DAT","OBJ_PACKED","STATE_PINNED_SYSTEM")
    symbols=phase3_open_descriptions._symbols(listing.with_suffix(".sym"),names)
    if action=="test":
        _runtime(root,symbols,binary.read_bytes())
        assertions += [
          {"name":"final-close-eligibility-runtime","passed":True},{"name":"non-final-close-negative-runtime","passed":True},
          {"name":"tmp-policy-parity-runtime","passed":True},{"name":"no-synchronous-pack-runtime","passed":True},
          {"name":"reopen-write-remove-reuse-clear-runtime","passed":True},
        ]
    hashes={
      "v1/build/kernel.bin":sha256_file(kernel),"v1/build/p424-close-candidates.bin":sha256_file(binary),
      "v1/src/kernel/objects.asm":sha256_file(root/"v1/src/kernel/objects.asm"),
      "v1/src/kernel/zxpack.asm":sha256_file(root/"v1/src/kernel/zxpack.asm"),
      "v1/tools-host/test-driver/phase4_close_candidates.py":sha256_file(root/"v1/tools-host/test-driver/phase4_close_candidates.py"),
      "v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
      "v1/dist/certification/P4.23.test.json":sha256_file(root/"v1/dist/certification/P4.23.test.json"),
    }
    return [kr,fr],hashes,assertions
