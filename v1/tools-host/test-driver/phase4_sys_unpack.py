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

class P423Error(DriverError):
    pass

def require(ok: bool, msg: str) -> None:
    if not ok:
        raise P423Error(msg)

def _word(v:int)->bytes:
    return bytes((v&0xff,(v>>8)&0xff))

def _jp_nc(addr:int)->bytes:
    return b"\xD2"+_word(addr)

def _check_byte(addr:int,v:int)->bytes:
    return b"\x3A"+_word(addr)+bytes((0xFE,v&0xff))+phase1._jp_nz(FAIL_PC)

def _check_word(addr:int,v:int)->bytes:
    return b"\x2A"+_word(addr)+phase1._ld_de(v)+b"\xB7\xED\x52"+phase1._jp_nz(FAIL_PC)

def _check_hl(v:int)->bytes:
    return phase1._ld_de(v)+b"\xB7\xED\x52"+phase1._jp_nz(FAIL_PC)

def _check_bytes(addr:int,data:bytes)->bytes:
    out=bytearray()
    for i,b in enumerate(data):
        out+=_check_byte(addr+i,b)
    return bytes(out)

def _record(name:bytes, directory:int, type_id:int, *, flags:int=0, state:int=0, logical:int=0, storage:int=0, ptr:int=0)->bytes:
    r=bytearray(20)
    r[:len(name)]=name
    r[10]=directory
    r[11]=type_id
    r[12]=flags
    r[13]=state
    r[14:16]=_word(logical)
    r[16:18]=_word(storage)
    r[18:20]=_word(ptr)
    return bytes(r)

def _source_contract(root:Path)->list[dict[str,object]]:
    zx=(root/"v1/src/kernel/zxpack.asm").read_text(encoding="utf-8")
    ob=(root/"v1/src/kernel/objects.asm").read_text(encoding="utf-8")
    require("MACRO EMIT_P423_SYS_UNPACK_CODEC_ROUTINES" in zx,"P4.23 codec macro missing")
    require("MACRO EMIT_P423_SYS_UNPACK_OBJECT_ROUTINES" in ob,"P4.23 object macro missing")
    m=zx.split("MACRO EMIT_P423_SYS_UNPACK_CODEC_ROUTINES",1)[1].split("ENDM",1)[0]
    o=ob.split("MACRO EMIT_P423_SYS_UNPACK_OBJECT_ROUTINES",1)[1].split("ENDM",1)[0]
    alloc=m.index("call zx48_alloc")
    decode=m.index("call zx48_p416_decode")
    publish=m.index("ld (ix+OBJ_ALLOCATION_PTR),l",decode)
    release=m.index("call zx48_free",publish)
    return [
        {"name":"exact-path-register-contract","passed":"zx48_p423_sys_unpack:" in o and "call zx48_path_resolve" in o},
        {"name":"raw-noop-returns-logical-length","passed":"ld hl,(p423_logical)" in m and m.index("ld hl,(p423_logical)") < m.index("zx48_p423_packed:")},
        {"name":"packed-live-handle-ebusy","passed":"call zx48_od_object_any_live" in m},
        {"name":"exact-logical-destination-allocation","passed":"ld bc,(p423_logical)" in m and alloc < decode},
        {"name":"whole-stream-final-memory-sink","passed":"P416_SINK_FINAL_MEMORY" in m and "ld ix,0" in m},
        {"name":"no-separate-history-allocation","passed":"256" not in m},
        {"name":"validate-before-publish","passed":decode < publish},
        {"name":"publish-before-packed-free","passed":publish < release},
        {"name":"decode-failure-private-cleanup","passed":"zx48_p423_decode_fail:" in m},
    ]

def _assemble(root:Path,run_command:Callable[...,Any],require_project_tool:Callable[[Path,str|Path],Path]):
    asm=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus")
    build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    fixture=build/"p423-sys-unpack.asm"
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
    EMIT_P406_EXCLUSIVITY_ROUTINES
    EMIT_P416_ZXP1_DECODER
    EMIT_P423_SYS_UNPACK_CODEC_ROUTINES
    EMIT_P423_SYS_UNPACK_OBJECT_ROUTINES
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
    defs 16,0
    defs 8,HANDLE_FREE
    defs 24,0
    SAVEBIN "p423-sys-unpack.bin",$C000,$-$C000
""",encoding="utf-8",newline="\n")
    res=run_command([asm,"--nologo","--lst=p423-sys-unpack.lst","--sym=p423-sys-unpack.sym","p423-sys-unpack.asm"],cwd=build,timeout_seconds=30.0)
    require(not res.timed_out and res.exit_code==0,f"P4.23 fixture assembly failed: {res.stderr or res.stdout}")
    binary=build/"p423-sys-unpack.bin"; listing=build/"p423-sys-unpack.lst"
    require(binary.is_file() and 0<binary.stat().st_size<24576,"P4.23 fixture binary missing/oversize")
    return res,binary,listing

def _runtime(root:Path,s:dict[str,int],module:bytes)->None:
    path=DATA_BASE
    table=s["p405_object_table"]
    od=s["open_description_table"]
    free=s["memory_free_extents"]
    live=s["memory_live_allocations"]
    old=s["ARENA_START"]
    arena=s["ARENA_SIZE"]

    def patch(record:bytes,payload:bytes,*,live_handle:bool=False,free_bytes:int|None=None):
        storage=record[16]|(record[17]<<8)
        owned=(storage+1)&~1 if storage else 0
        def apply(ram:bytearray)->None:
            ram[MODULE_BASE-0x4000:MODULE_BASE-0x4000+len(module)]=module
            ram[path-0x4000:path-0x4000+10]=b"/tmp/file\x00"
            ram[table-0x4000:table-0x4000+20]=record
            if payload:
                ram[old-0x4000:old-0x4000+len(payload)]=payload
            ram[free-0x4000:free-0x4000+64]=bytes(64)
            avail=arena-owned if free_bytes is None else free_bytes
            ram[free-0x4000:free-0x4000+4]=_word(old+owned)+_word(avail)
            ram[live-0x4000:live-0x4000+2]=_word(1 if owned else 0)
            if live_handle:
                ram[od-0x4000+s["OD_KIND_O"]]=s["OD_KIND_OBJECT"]
                ram[od-0x4000+s["OD_ID_O"]]=0
                ram[od-0x4000+s["OD_ACCESS_O"]]=s["O_READ"]
        return apply

    def call()->bytes:
        return phase1._ld_hl(path)+phase1._call(s["zx48_p423_sys_unpack"])

    def execute(label:str,record:bytes,payload:bytes,code:bytes,**kwargs)->None:
        body=b"\xF3"+phase1._ld_sp(STACK_TOP)+code+phase1._jp(PASS_PC)
        try:
            run_sna(root,body,patch=patch(record,payload,**kwargs))
        except DriverError as exc:
            raise P423Error(f"P4.23 runtime case failed: {label}: {exc}") from exc

    raw=b"abcdef"*11
    rawrec=_record(b"file",s["DIR_TMP"],s["OBJ_DAT"],logical=len(raw),storage=len(raw),ptr=old)
    code=call()+phase1._jp_c(FAIL_PC)+_check_hl(len(raw))+_check_bytes(table,rawrec)+_check_bytes(old,raw[:8])
    execute("raw-noop",rawrec,raw,code,live_handle=True)

    packed=b"\x7fQ"
    packedrec=_record(b"file",s["DIR_TMP"],s["OBJ_DAT"],flags=s["OBJ_PACKED"],logical=66,storage=2,ptr=old)
    code=call()+_jp_nc(FAIL_PC)+bytes((0xFE,s["E_BUSY"]))+phase1._jp_nz(FAIL_PC)+_check_bytes(table,packedrec)
    execute("packed-live-handle-ebusy",packedrec,packed,code,live_handle=True)

    malformed=b"\x80\x00"
    badrec=_record(b"file",s["DIR_TMP"],s["OBJ_DAT"],flags=s["OBJ_PACKED"],logical=66,storage=2,ptr=old)
    code=call()+_jp_nc(FAIL_PC)+bytes((0xFE,s["E_FORMAT"]))+phase1._jp_nz(FAIL_PC)+_check_bytes(table,badrec)+_check_bytes(old,malformed)
    execute("decode-failure-preserves-packed",badrec,malformed,code)

    code=call()+_jp_nc(FAIL_PC)+bytes((0xFE,s["E_NOMEM"]))+phase1._jp_nz(FAIL_PC)+_check_bytes(table,packedrec)
    execute("allocation-failure-preserves-packed",packedrec,packed,code,free_bytes=64)

    code=call()+phase1._jp_c(FAIL_PC)+_check_hl(66)
    code+=_check_byte(table+12,0)+_check_word(table+14,66)+_check_word(table+16,66)+_check_word(table+18,old+2)
    code+=_check_bytes(old+2,b"Q"*8)+_check_word(live,1)
    execute("packed-to-raw-atomic",packedrec,packed,code)

def dispatch(root:Path,action:str,step:str,*,sha256_file,run_command,require_project_tool):
    if step!="P4.23":
        raise DriverError(f"Phase-4 SYS_UNPACK step is not registered: {step}")
    assertions=_source_contract(root)
    failed=[x["name"] for x in assertions if x.get("passed") is not True]
    require(not failed,f"static P4.23 contract failures: {failed}")
    kernel_result,kernel,_=phase1._assemble_kernel(root,run_command,require_project_tool)
    fixture_result,binary,listing=_assemble(root,run_command,require_project_tool)
    names=(
        "zx48_p423_sys_unpack","p405_object_table","open_description_table",
        "memory_free_extents","memory_live_allocations","ARENA_START","ARENA_SIZE",
        "OD_KIND_O","OD_ID_O","OD_ACCESS_O","OD_KIND_OBJECT","O_READ",
        "OBJ_DAT","OBJ_PACKED","DIR_TMP","E_BUSY","E_FORMAT","E_NOMEM",
    )
    symbols=phase3_open_descriptions._symbols(listing.with_suffix(".sym"),names)
    if action=="test":
        _runtime(root,symbols,binary.read_bytes())
        assertions += [
            {"name":"raw-noop-logical-length-runtime","passed":True},
            {"name":"packed-busy-gate-runtime","passed":True},
            {"name":"whole-stream-direct-memory-backref-runtime","passed":True},
            {"name":"failure-preserves-packed-runtime","passed":True},
            {"name":"atomic-packed-to-raw-swap-runtime","passed":True},
        ]
    hashes={
        "v1/build/kernel.bin":sha256_file(kernel),
        "v1/build/p423-sys-unpack.bin":sha256_file(binary),
        "v1/src/kernel/objects.asm":sha256_file(root/"v1/src/kernel/objects.asm"),
        "v1/src/kernel/zxpack.asm":sha256_file(root/"v1/src/kernel/zxpack.asm"),
        "v1/tools-host/test-driver/phase4_sys_unpack.py":sha256_file(root/"v1/tools-host/test-driver/phase4_sys_unpack.py"),
        "v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
        "v1/dist/certification/P4.22.test.json":sha256_file(root/"v1/dist/certification/P4.22.test.json"),
    }
    return [kernel_result,fixture_result],hashes,assertions
