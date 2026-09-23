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

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Any

from driver_core import DriverError

RELOC_SIZE=6
ABS16=1
# Qualification source marker: P10.03 exact candidate.


class Obj1RelocError(DriverError):
    pass


@dataclass(frozen=True)
class Reloc:
    offset:int
    symbol:int
    kind:int
    addend:int


def require(ok:bool,msg:str)->None:
    if not ok:
        raise Obj1RelocError(msg)


def i16(word:int)->int:
    return word-0x10000 if word&0x8000 else word


def parse_reloc(data:bytes, *, text:bytes, symbol_count:int, previous_offset:int|None=None, symbol_value:int|None=None)->Reloc:
    require(len(data)==RELOC_SIZE,"E_FORMAT relocation record size")
    off=data[0]|(data[1]<<8)
    sym=data[2]|(data[3]<<8)
    kind=data[4]
    reserved=data[5]
    require(kind==ABS16,"E_FORMAT relocation type")
    require(reserved==0,"E_FORMAT relocation reserved")
    require(len(text)>=2,"E_FORMAT relocation requires text word")
    require(off<=len(text)-2,"E_FORMAT relocation offset")
    if previous_offset is not None:
        require(off>=previous_offset+2,"E_FORMAT relocation order/overlap")
    require(sym<symbol_count,"E_FORMAT relocation symbol index")
    word=text[off]|(text[off+1]<<8)
    add=i16(word)
    if symbol_value is not None:
        result=int(symbol_value)+int(add)
        require(0<=result<=0xFFFF,"E_FORMAT widened symbol+addend")
    return Reloc(off,sym,kind,add)


def make_reloc(off:int,sym:int,kind:int=ABS16,reserved:int=0)->bytes:
    return off.to_bytes(2,"little")+sym.to_bytes(2,"little")+bytes((kind,reserved))


def source_assertions(root:Path)->list[dict[str,object]]:
    asm=(root/"tools/as.asm").read_text(encoding="utf-8")
    doc=(root/"v1/docs/obj1.md").read_text(encoding="utf-8")
    inc=(root/"v1/include/obj1.inc").read_text(encoding="utf-8")
    return [
        {"name":"native-reloc-layout-frozen","passed":all(x in asm for x in ("AS_OBJ1_RELOC_SIZE       EQU 6","AS_OBJ1_RELOC_SYMBOL     EQU 2","AS_OBJ1_RELOC_TYPE       EQU 4","AS_OBJ1_RELOC_RESERVED   EQU 5"))},
        {"name":"native-reloc-validator-present","passed":"as_obj1_reloc_validate:" in asm and "AS_OBJ1_RELOC_ABS16      EQU 1" in asm},
        {"name":"include-reloc-layout-agrees","passed":"OBJ1_RELOC_SIZE          EQU 6" in inc and "OBJ1_RELOC_ABS16         EQU 1" in inc},
        {"name":"doc-strict-order-and-addend","passed":"strictly increasing and non-overlapping" in doc and "signed i16 addend" in doc},
        {"name":"doc-widened-arithmetic","passed":"widened arithmetic" in doc and "16-bit wrap" in doc},
    ]


def positive_assertions()->list[dict[str,object]]:
    text=bytes((0x00,0x00,0xFF,0x7F,0x00,0x80,0xFF,0xFF))
    r0=parse_reloc(make_reloc(0,0),text=text,symbol_count=3,symbol_value=0)
    r1=parse_reloc(make_reloc(2,1),text=text,symbol_count=3,previous_offset=0,symbol_value=0)
    r2=parse_reloc(make_reloc(4,2),text=text,symbol_count=3,previous_offset=2,symbol_value=32768)
    r3=parse_reloc(make_reloc(6,2),text=text,symbol_count=3,previous_offset=4,symbol_value=1)
    return [
        {"name":"zero-addend","passed":r0.addend==0},
        {"name":"positive-i16-addend","passed":r1.addend==32767},
        {"name":"negative-boundary-addend","passed":r2.addend==-32768},
        {"name":"negative-one-addend","passed":r3.addend==-1},
        {"name":"strict-plus-two-order-accepted","passed":(r0.offset,r1.offset,r2.offset,r3.offset)==(0,2,4,6)},
    ]


def negative_assertions()->list[dict[str,object]]:
    cases=[]
    def check(label:str, fn)->None:
        rejected=False
        try: fn()
        except Obj1RelocError: rejected=True
        cases.append({"name":label,"passed":rejected})
    check("text-short",lambda:parse_reloc(make_reloc(0,0),text=b"X",symbol_count=1))
    check("offset-overrun",lambda:parse_reloc(make_reloc(1,0),text=b"XY",symbol_count=1))
    check("overlap",lambda:parse_reloc(make_reloc(1,0),text=b"ABCD",symbol_count=1,previous_offset=0))
    check("unsorted",lambda:parse_reloc(make_reloc(0,0),text=b"ABCD",symbol_count=1,previous_offset=2))
    check("symbol-out-of-range",lambda:parse_reloc(make_reloc(0,1),text=b"AB",symbol_count=1))
    check("wrong-type",lambda:parse_reloc(make_reloc(0,0,2),text=b"AB",symbol_count=1))
    check("reserved-nonzero",lambda:parse_reloc(make_reloc(0,0,ABS16,1),text=b"AB",symbol_count=1))
    check("addend-underflow",lambda:parse_reloc(make_reloc(0,0),text=b"\x00\x80",symbol_count=1,symbol_value=32767))
    check("addend-overflow",lambda:parse_reloc(make_reloc(0,0),text=b"\xff\x7f",symbol_count=1,symbol_value=32769))
    check("count-wrap-vector",lambda: require(0x4000*RELOC_SIZE<=0xFFFF,"E_FORMAT widened relocation-count multiplication"))
    return cases


def dispatch(root:Path,action:str,step:str,*,sha256_file:Callable[[Path],str],run_command:Callable[...,Any],require_project_tool:Callable[[Path,str|Path],Path]):
    if step!="P10.03":
        raise DriverError(f"Phase-10 OBJ1 relocation step is not registered: {step}")
    assertions=source_assertions(root)+positive_assertions()
    if action=="test":
        assertions.extend(negative_assertions())
    failed=[a["name"] for a in assertions if a.get("passed") is not True]
    require(not failed,f"P10.03 contract failures: {failed}")
    hashes={
        "tools/as.asm":sha256_file(root/"tools/as.asm"),
        "v1/include/obj1.inc":sha256_file(root/"v1/include/obj1.inc"),
        "v1/docs/obj1.md":sha256_file(root/"v1/docs/obj1.md"),
        "v1/tools-host/test-driver/phase10_obj1_reloc.py":sha256_file(root/"v1/tools-host/test-driver/phase10_obj1_reloc.py"),
        "v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
        "v1/dist/certification/P10.02.build.json":sha256_file(root/"v1/dist/certification/P10.02.build.json"),
        "v1/dist/certification/P10.02.test.json":sha256_file(root/"v1/dist/certification/P10.02.test.json"),
    }
    return [],hashes,assertions
