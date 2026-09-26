# ============================================================================
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Proprietary rights reserved except as expressly licensed herein.
#
# ZX-UX C48 SDK
# This file is governed by the SANYALnet Labs Non-Commercial License in the
# root LICENSE file. Non-Commercial use is permitted; Commercial Use and use
# for AI/ML model training are prohibited unless separately authorized.
#
# Attribution is required: "Based on original work by Supratim Sanyal of
# SANYALnet Labs." See LICENSE for full terms, warranty disclaimer, termination,
# patent, trademark, and governing-law provisions.
# ============================================================================
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .errors import RuntimeC48Error
from .screen import ZXScreen
from .typesys import CHAR,UCHAR,CType,align_up

USER_LO=0x6000
USER_HI=0xE000
SCREEN_LO=0x4000
SCREEN_HI=0x5B00

@dataclass
class Allocation:
    aid:int
    start:int
    size:int
    ctype:CType|None
    kind:str
    readonly:bool=False
    live:bool=True
    @property
    def end(self)->int:return self.start+self.size

@dataclass(frozen=True)
class PointerRecord:
    address:int
    aid:int|None
    offset:int|None

class C48Memory:
    def __init__(self,screen:ZXScreen|None=None):
        self.ram=bytearray(65536)
        self.init=bytearray(65536)
        self.screen=screen
        self.allocations:dict[int,Allocation]={}
        self.next_aid=1
        self.ptr_shadow:dict[int,PointerRecord]={}
        if screen is not None:
            self.init[SCREEN_LO:SCREEN_HI]=b'\x01'*(SCREEN_HI-SCREEN_LO)

    def _segments(self)->list[Allocation]:
        return sorted((a for a in self.allocations.values() if a.live),key=lambda a:a.start)

    def allocate(self,size:int,align:int,ctype:CType|None,kind:str,*,zero:bool=False,readonly:bool=False)->Allocation:
        if size<0:raise RuntimeC48Error("negative allocation size")
        if size==0:raise RuntimeC48Error("zero-size object allocation is invalid")
        cursor=USER_LO
        for a in self._segments():
            p=align_up(cursor,align)
            if p+size<=a.start:break
            cursor=max(cursor,a.end)
        p=align_up(cursor,align)
        if p+size>USER_HI:raise RuntimeC48Error("not enough C48 logical memory")
        aid=self.next_aid;self.next_aid+=1
        a=Allocation(aid,p,size,ctype,kind,readonly,True);self.allocations[aid]=a
        # Poison uninitialized bytes to make accidental dependence visible in dumps.
        self.ram[p:p+size]=b'\xA5'*size
        self.init[p:p+size]=b'\x00'*size
        if zero:
            self.ram[p:p+size]=b'\x00'*size;self.init[p:p+size]=b'\x01'*size
        return a

    def free(self,aid:int)->None:
        a=self.allocations.get(aid)
        if not a or not a.live:raise RuntimeC48Error("free/use of non-live allocation")
        a.live=False
        self.init[a.start:a.end]=b'\x00'*a.size
        # Pointer objects stored *inside* the freed allocation disappear with
        # that storage.  Pointer objects elsewhere deliberately keep their old
        # allocation id so a later allocation at the same numeric address can
        # never resurrect a stale pointer (ABA defense).
        for loc in list(self.ptr_shadow):
            if a.start <= loc < a.end:
                self.ptr_shadow.pop(loc, None)

    def allocation(self,aid:int|None)->Allocation|None:
        if aid is None:return None
        a=self.allocations.get(aid)
        return a if a and a.live else None

    def pointer_for(self,a:Allocation,offset:int=0)->PointerRecord:
        if offset<0 or offset>a.size:raise RuntimeC48Error("pointer outside allocation/provenance")
        return PointerRecord((a.start+offset)&0xFFFF,a.aid,offset)

    def check_access(self,pr:PointerRecord,t:CType,*,write:bool=False)->int:
        if pr.address==0:raise RuntimeC48Error("null pointer dereference")
        if t.is_void or t.is_function or t.is_array:raise RuntimeC48Error("invalid dereference object type")
        if pr.address % t.alignment:raise RuntimeC48Error("misaligned C48 pointer dereference")
        a=self.allocation(pr.aid)
        if a is None:
            raise RuntimeC48Error(
                "pointer does not designate live C48 object storage"
            )
        off = pr.address - a.start
        if pr.offset is None or pr.offset != off:
            raise RuntimeC48Error("pointer provenance/offset mismatch")
        if off<0 or off+t.size>a.size:raise RuntimeC48Error("pointer dereference outside live object or at one-past")
        if write and a.readonly:raise RuntimeC48Error("write through pointer to read-only C48 object")
        # Exact aliasing rule except byte views and heap/raw storage.
        if a.ctype is not None and a.kind not in {"heap","raw","argv"}:
            declared=a.ctype
            allowed=False
            if t in {CHAR,UCHAR}:allowed=True
            elif declared==t:allowed=True
            elif declared.is_array and declared.base==t and off%t.size==0:allowed=True
            if not allowed:raise RuntimeC48Error(f"typed pointer access {t} incompatible with object type {declared}")
        return pr.address

    def _screen_index(self,address:int)->int|None:
        if self.screen is not None and SCREEN_LO<=address<SCREEN_HI:return address-SCREEN_LO
        return None

    def read8(self,address:int,*,require_init:bool=True)->int:
        address&=0xFFFF;si=self._screen_index(address)
        if si is not None:return self.screen.mem[si]
        if require_init and not self.init[address]:raise RuntimeC48Error("read of uninitialized C48 object byte")
        return self.ram[address]
    def write8(self,address:int,value:int)->None:
        address&=0xFFFF;si=self._screen_index(address)
        if si is not None:self.screen.mem[si]=value&0xFF
        else:self.ram[address]=value&0xFF;self.init[address]=1
        self.ptr_shadow.pop(address,None);self.ptr_shadow.pop((address-1)&0xFFFF,None)
    def read_bytes(self,address:int,count:int,*,require_init:bool=True)->bytes:
        return bytes(self.read8(address+i,require_init=require_init) for i in range(count))
    def write_bytes(self,address:int,data:bytes)->None:
        for i,b in enumerate(data):self.write8(address+i,b)

    def load_integer(self,address:int,t:CType)->int:
        if t.bits==8:return self.read8(address)
        u=self.read8(address)|(self.read8(address+1)<<8)
        if t.is_signed and u&0x8000:return u-65536
        return u
    def store_integer(self,address:int,t:CType,value:int)->None:
        mask=(1<<t.bits)-1;u=value&mask
        self.write8(address,u)
        if t.bits==16:self.write8(address+1,u>>8)
    def load_pointer(self,address:int)->PointerRecord:
        lo=self.read8(address);hi=self.read8(address+1);addr=lo|(hi<<8)
        pr=self.ptr_shadow.get(address)
        if pr is not None and pr.address == addr:
            # Preserve stale provenance.  Never infer a new allocation id merely
            # because a dead pointer's numeric address has been reused.
            return pr
        if addr == 0:
            return PointerRecord(0,None,None)
        # Bytes that did not originate from a pointer store/copy have no C48
        # provenance.  They may compare as an address but cannot be dereferenced.
        return PointerRecord(addr,None,None)
    def store_pointer(self,address:int,pr:PointerRecord)->None:
        self.write8(address,pr.address&0xFF);self.write8(address+1,(pr.address>>8)&0xFF)
        self.ptr_shadow[address]=pr

    def require_range(
        self, pr:PointerRecord, count:int, *, write:bool=False
    )->Allocation:
        if count<0:raise RuntimeC48Error("negative byte count")
        if pr.address==0:
            raise RuntimeC48Error("null range pointer")
        a=self.allocation(pr.aid)
        if a is None:
            raise RuntimeC48Error("range pointer not in live allocation")
        off=pr.address-a.start
        if pr.offset is None or pr.offset!=off:
            raise RuntimeC48Error("range pointer provenance/offset mismatch")
        if off<0 or off+count>a.size:
            raise RuntimeC48Error("byte range outside live allocation")
        if write and a.readonly:
            raise RuntimeC48Error("write to read-only allocation")
        return a

    def copy_bytes(
        self, dst:PointerRecord, src:PointerRecord, count:int, *, move:bool=False
    )->None:
        self.require_range(dst,count,write=True)
        self.require_range(src,count)
        data=self.read_bytes(src.address,count)
        shadows=[
            (loc-src.address,pr)
            for loc,pr in self.ptr_shadow.items()
            if src.address<=loc and loc+2<=src.address+count
        ]
        self.write_bytes(dst.address,data)
        for rel,pr in shadows:self.ptr_shadow[dst.address+rel]=pr
    def memset(self,dst:PointerRecord,value:int,count:int)->None:
        self.require_range(dst,count,write=True)
        self.write_bytes(dst.address,bytes([value&0xFF])*count)
