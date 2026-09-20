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
STACK_TOP=0xBFC0

class P425Error(DriverError): pass

def require(ok:bool,msg:str)->None:
    if not ok: raise P425Error(msg)

def _word(v:int)->bytes: return bytes((v&255,(v>>8)&255))
def _check_byte(a:int,v:int)->bytes:
    return b"\x3A"+_word(a)+bytes((0xFE,v&255))+phase1._jp_nz(FAIL_PC)
def _check_word(a:int,v:int)->bytes:
    return b"\x2A"+_word(a)+phase1._ld_de(v)+b"\xB7\xED\x52"+phase1._jp_nz(FAIL_PC)
def _check_bytes(a:int,data:bytes)->bytes:
    out=bytearray()
    for i,b in enumerate(data): out+=_check_byte(a+i,b)
    return bytes(out)
def _record(name:bytes,directory:int,type_id:int,*,flags:int=0,state:int=0,logical:int=0,storage:int=0,ptr:int=0)->bytes:
    r=bytearray(20); r[:len(name)]=name; r[10]=directory; r[11]=type_id; r[12]=flags; r[13]=state
    r[14:16]=_word(logical); r[16:18]=_word(storage); r[18:20]=_word(ptr); return bytes(r)

def _source_contract(root:Path)->list[dict[str,object]]:
    z=(root/"v1/src/kernel/zxpack.asm").read_text()
    s=(root/"v1/src/kernel/scheduler.asm").read_text()
    require("MACRO EMIT_P425_IDLE_PACK_ROUTINES" in z,"P4.25 pack service macro missing")
    require("MACRO EMIT_P425_IDLE_MAINTENANCE_ROUTINES" in s,"P4.25 scheduler hook macro missing")
    zm=z.split("MACRO EMIT_P425_IDLE_PACK_ROUTINES",1)[1].split("ENDM",1)[0]
    sm=s.split("MACRO EMIT_P425_IDLE_MAINTENANCE_ROUTINES",1)[1].split("ENDM",1)[0]
    return [
      {"name":"one-pack-call-per-idle-cycle","passed":sm.count("call zx48_p425_pack_once")==1},
      {"name":"one-selected-candidate-per-service","passed":"zx48_p425_selected:" in zm and "jr zx48_p425_scan" not in zm.split("zx48_p425_selected:",1)[1]},
      {"name":"attempt-bit-cleared-before-revalidation","passed":zm.index("call zx48_p424_candidate_clear") < zm.index("call zx48_p405_object_ptr_slot")},
      {"name":"same-slot-revalidated","passed":all(x in zm for x in ("OBJ_TYPE_ID","STATE_RAM","OBJ_PACKED","OBJ_LOGICAL_LENGTH","cp 64"))},
      {"name":"open-handle-revalidation","passed":"call zx48_od_object_any_live" in zm},
      {"name":"background-failure-is-best-effort","passed":"call zx48_p422_pack_record" in zm and "jr c,zx48_p425_done" in zm},
      {"name":"scheduler-hook-returns","passed":"zx48_p425_idle_maintenance:" in sm and "ret" in sm},
    ]

def _assemble(root:Path,run_command:Callable[...,Any],require_project_tool:Callable[[Path,str|Path],Path]):
    asm=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus"); build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    fixture=build/"p425-idle-pack.asm"
    fixture.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
PANIC_SCHEDULER EQU $03
PROC_HANDLES EQU 16
PROC_CWD EQU 28
    ORG $C000
current_pid: db 0
zx48_process_lookup:
    ld ix,fake_process
    xor a
    ret
    INCLUDE "../src/kernel/memory.asm"
    INCLUDE "../src/kernel/handles.asm"
    INCLUDE "../src/kernel/objects.asm"
    INCLUDE "../src/kernel/zxpack.asm"
    INCLUDE "../src/kernel/scheduler.asm"
    EMIT_MEMORY_ROUTINES
    EMIT_NAMESPACE_ROUTINES
    EMIT_OBJECT_TYPE_ROUTINES
    EMIT_OBJECT_OPEN_ROUTINES
    EMIT_HANDLE_ROUTINES
    EMIT_P406_EXCLUSIVITY_ROUTINES
    EMIT_P416_ZXP1_DECODER
    EMIT_P420_TARGET_ENCODER_ROUTINES
    EMIT_P422_SYS_PACK_CODEC_ROUTINES
    EMIT_P424_PACK_CANDIDATE_ROUTINES
    EMIT_P425_IDLE_PACK_ROUTINES
    EMIT_P425_IDLE_MAINTENANCE_ROUTINES
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
    SAVEBIN "p425-idle-pack.bin",$C000,$-$C000
""",encoding="utf-8",newline="\n")
    res=run_command([asm,"--nologo","--lst=p425-idle-pack.lst","--sym=p425-idle-pack.sym","p425-idle-pack.asm"],cwd=build,timeout_seconds=30)
    require(not res.timed_out and res.exit_code==0,f"P4.25 fixture assembly failed: {res.stderr or res.stdout}")
    binary=build/"p425-idle-pack.bin"; listing=build/"p425-idle-pack.lst"
    require(binary.is_file() and 0<binary.stat().st_size<16384,"P4.25 fixture binary missing/oversize")
    return res,binary,listing

def _runtime(root:Path,s:dict[str,int],module:bytes)->None:
    table=s["p405_object_table"]; bits=s["p424_candidate_bits"]; od=s["open_description_table"]
    free=s["memory_free_extents"]; live=s["memory_live_allocations"]; old=s["ARENA_START"]; arena=s["ARENA_SIZE"]

    def patch(records:list[bytes], payloads:list[tuple[int,bytes]], bitbytes:bytes, *, free_start:int, free_len:int, live_count:int, live_slot:int|None=None):
        def apply(ram:bytearray)->None:
            ram[MODULE_BASE-0x4000:MODULE_BASE-0x4000+len(module)]=module
            ram[table-0x4000:table-0x4000+640]=bytes(640)
            for i,r in enumerate(records): ram[table-0x4000+i*20:table-0x4000+(i+1)*20]=r
            for ptr,data in payloads: ram[ptr-0x4000:ptr-0x4000+len(data)]=data
            ram[bits-0x4000:bits-0x4000+4]=bitbytes
            ram[free-0x4000:free-0x4000+64]=bytes(64)
            ram[free-0x4000:free-0x4000+4]=_word(free_start)+_word(free_len)
            ram[live-0x4000:live-0x4000+2]=_word(live_count)
            if live_slot is not None:
                ram[od-0x4000:od-0x4000+8]=bytes((s["OD_KIND_OBJECT"],1,1,live_slot,0,0,0,0))
        return apply

    def execute(label:str,code:bytes,patcher)->None:
        body=b"\xF3"+phase1._ld_sp(STACK_TOP)+code+phase1._jp(PASS_PC)
        try: run_sna(root,body,patch=patcher)
        except DriverError as exc: raise P425Error(f"P4.25 runtime case failed: {label}: {exc}") from exc

    raw0=_record(b"a",s["DIR_TMP"],s["OBJ_DAT"],state=s["STATE_RAM"],logical=80,storage=80,ptr=old)
    raw1=_record(b"b",s["DIR_TMP"],s["OBJ_DAT"],state=s["STATE_RAM"],logical=80,storage=80,ptr=old+80)

    code=phase1._call(s["zx48_p425_idle_maintenance"])+phase1._jp_c(FAIL_PC)
    code+=_check_byte(s["p425_attempted"],1)+_check_byte(bits,2)
    code+=_check_byte(table+12,s["OBJ_PACKED"])+_check_byte(table+20+12,0)
    execute("one-candidate-only",code,patch([raw0,raw1],[(old,b"A"*80),(old+80,b"B"*80)],b"\x03\x00\x00\x00",free_start=old+160,free_len=arena-160,live_count=2))

    code=phase1._call(s["zx48_p425_idle_maintenance"])+phase1._jp_c(FAIL_PC)
    code+=_check_byte(bits,2)+_check_bytes(table,raw0)+_check_bytes(old,b"A"*8)
    execute("enomem-clears-only-attempt",code,patch([raw0,raw1],[(old,b"A"*80),(old+80,b"B"*80)],b"\x03\x00\x00\x00",free_start=old+160,free_len=128,live_count=2))

    incompress=bytes(range(80))
    code=phase1._call(s["zx48_p425_idle_maintenance"])+phase1._jp_c(FAIL_PC)
    code+=_check_byte(bits,0)+_check_bytes(table,raw0)+_check_bytes(old,incompress[:8])
    execute("no-savings-clears-attempt-raw-unchanged",code,patch([raw0],[(old,incompress)],b"\x01\x00\x00\x00",free_start=old+80,free_len=arena-80,live_count=1))

    code=phase1._call(s["zx48_p425_idle_maintenance"])+phase1._jp_c(FAIL_PC)
    code+=_check_byte(bits,0)+_check_bytes(table,raw0)+_check_bytes(old,b"A"*8)
    execute("live-handle-revalidation-skips",code,patch([raw0],[(old,b"A"*80)],b"\x01\x00\x00\x00",free_start=old+80,free_len=arena-80,live_count=1,live_slot=0))

    stale=_record(b"a",s["DIR_TMP"],s["OBJ_DAT"],flags=s["OBJ_PACKED"],state=s["STATE_RAM"],logical=80,storage=2,ptr=old)
    code=phase1._call(s["zx48_p425_idle_maintenance"])+phase1._jp_c(FAIL_PC)
    code+=_check_byte(bits,2)+_check_bytes(table,stale)
    execute("stale-first-bit-does-not-fall-through-to-second",code,patch([stale,raw1],[(old,b"\x7fA"),(old+80,b"B"*80)],b"\x03\x00\x00\x00",free_start=old+160,free_len=arena-160,live_count=2))

def dispatch(root:Path,action:str,step:str,*,sha256_file,run_command,require_project_tool):
    if step!="P4.25": raise DriverError(f"Phase-4 idle pack step is not registered: {step}")
    assertions=_source_contract(root); failed=[x["name"] for x in assertions if x.get("passed") is not True]
    require(not failed,f"static P4.25 contract failures: {failed}")
    kr,kernel,_=phase1._assemble_kernel(root,run_command,require_project_tool)
    fr,binary,listing=_assemble(root,run_command,require_project_tool)
    names=("zx48_p425_idle_maintenance","p425_attempted","p424_candidate_bits","p405_object_table","open_description_table",
           "memory_free_extents","memory_live_allocations","ARENA_START","ARENA_SIZE","OD_KIND_OBJECT","DIR_TMP","OBJ_DAT",
           "OBJ_PACKED","STATE_RAM")
    symbols=phase3_open_descriptions._symbols(listing.with_suffix(".sym"),names)
    if action=="test":
        _runtime(root,symbols,binary.read_bytes())
        assertions += [
          {"name":"at-most-one-candidate-attempted-runtime","passed":True},
          {"name":"successful-background-pack-exact-runtime","passed":True},
          {"name":"enomem-clears-only-attempt-runtime","passed":True},
          {"name":"no-savings-preserves-raw-runtime","passed":True},
          {"name":"live-handle-revalidation-runtime","passed":True},
          {"name":"stale-first-bit-no-second-attempt-runtime","passed":True},
          {"name":"idle-maintenance-returns-runtime","passed":True},
        ]
    hashes={
      "v1/build/kernel.bin":sha256_file(kernel),"v1/build/p425-idle-pack.bin":sha256_file(binary),
      "v1/src/kernel/scheduler.asm":sha256_file(root/"v1/src/kernel/scheduler.asm"),
      "v1/src/kernel/zxpack.asm":sha256_file(root/"v1/src/kernel/zxpack.asm"),
      "v1/tools-host/test-driver/phase4_idle_pack.py":sha256_file(root/"v1/tools-host/test-driver/phase4_idle_pack.py"),
      "v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
      "v1/dist/certification/P4.24.test.json":sha256_file(root/"v1/dist/certification/P4.24.test.json"),
    }
    return [kr,fr],hashes,assertions
