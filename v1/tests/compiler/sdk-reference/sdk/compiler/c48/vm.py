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
from pathlib import Path
from typing import Any, Callable
import os, time

from .errors import RuntimeC48Error, RuntimeExit
from .float5 import Float5,Float5Error
from .limits import VM_CALL_DEPTH
from .memory import C48Memory,Allocation,PointerRecord
from .screen import ZXScreen
from .typesys import CHAR,FLOAT,INT,SHORT,UCHAR,UINT,USHORT,VOID,CType,arithmetic_common,integer_promotion,ptr

@dataclass(frozen=True)
class Value:
    ctype:CType
    data:int|Float5|PointerRecord|None

@dataclass(frozen=True)
class LValue:
    ctype:CType
    pointer:PointerRecord
    readonly:bool=False

class ReturnSignal(Exception):
    def __init__(self,value:Value|None):self.value=value
class BreakSignal(Exception):pass
class ContinueSignal(Exception):pass

class C48VM:
    def __init__(self,program:dict[str,Any],screen:ZXScreen,*,argv:list[str]|None=None,
                 approximate_rom_math:bool=False,input_provider:Callable[[],int]|None=None,
                 display_update:Callable[[],None]|None=None, heap_size:int=1024,
                 max_steps:int|None=None):
        if not isinstance(heap_size,int) or isinstance(heap_size,bool) or heap_size < 0 or heap_size > 8192 or (heap_size & 1):
            raise RuntimeC48Error("host heap size must be an even value from 0..8192")
        if max_steps is not None and (
            not isinstance(max_steps, int) or isinstance(max_steps, bool) or max_steps <= 0
        ):
            raise RuntimeC48Error("host max_steps must be a positive integer or None")
        self.program=program;self.screen=screen;self.mem=C48Memory(screen)
        self.argv=argv or ["program"]
        self.heap_size=heap_size
        self.heap_live_bytes=0
        self.approximate_rom_math=approximate_rom_math
        self.input_provider=input_provider or self._stdin_char
        self.display_update=display_update or (lambda:None)
        self.functions:dict[str,dict[str,Any]]={}
        self.global_lvalues:dict[str,LValue]={}
        self.scope_stack:list[dict[str,LValue]]=[]
        self.scope_allocs:list[list[int]]=[]
        self.string_allocs:dict[int,Allocation]={}
        self.heap_allocs:set[int]=set()
        self.start_time=time.monotonic()
        self.max_steps=max_steps
        self.steps=0
        self.call_depth=0
        self.builtins=self._builtin_table()
        self._index_program()

    def _index_program(self)->None:
        for item in self.program.get("items",[]):
            if item["kind"]=="function_definition":self.functions[item["declarator"]["name"]]=item
        # Allocate all file-scope object definitions before applying initializers.
        for item in self.program.get("items",[]):
            if item["kind"]!="declaration":continue
            for idecl in item["declarators"]:
                if not idecl.get("definition"):continue
                t=CType.from_dict(idecl["ctype"])
                if t.is_function:continue
                a=self.mem.allocate(t.size,t.alignment,t,"global",zero=True)
                self.global_lvalues[idecl["declarator"]["name"]]=LValue(t,self.mem.pointer_for(a))
        for item in self.program.get("items",[]):
            if item["kind"]!="declaration":continue
            for idecl in item["declarators"]:
                name=idecl["declarator"]["name"]
                if name in self.global_lvalues and idecl.get("definition") and idecl.get("initializer") is not None:
                    self._initialize(self.global_lvalues[name],idecl["initializer"],zero_remainder=True)

    @staticmethod
    def _stdin_char()->int:
        b=os.sys.stdin.buffer.read(1)
        return -1 if not b else b[0]

    def _tick(self)->None:
        if self.max_steps is None:
            return
        self.steps += 1
        if self.steps > self.max_steps:
            raise RuntimeC48Error(
                f"C48 execution step limit exceeded ({self.max_steps})"
            )

    def run(self)->int:
        f=self.functions.get("main")
        if not f:raise RuntimeC48Error("program has no main definition")
        ft=CType.from_dict(f["ctype"])
        try:
            if len(ft.params or ())==0:
                rv=self._call_user("main",[])
            else:
                argc,argvp=self._build_argv()
                rv=self._call_user("main",[Value(INT,argc),Value(ptr(ptr(CHAR)),argvp)])
            if rv is None:raise RuntimeC48Error("main returned no value")
            return self._to_unsigned(self._convert(rv,INT))&0xFF
        except RuntimeExit as e:
            return e.status

    def _build_argv(self)->tuple[int,PointerRecord]:
        if not 1<=len(self.argv)<=16:raise RuntimeC48Error("host argv count must be 1..16")
        encoded=[]
        for s in self.argv:
            try:b=s.encode("ascii")
            except UnicodeEncodeError:raise RuntimeC48Error("argv is not canonical ASCII") from None
            if b"\0" in b:raise RuntimeC48Error("argv contains NUL")
            encoded.append(b)
        # Native ARG1 is an 8-byte header followed by exactly argc NUL-terminated strings.
        if 8+sum(len(b)+1 for b in encoded)>256:
            raise RuntimeC48Error("host argv exceeds the 256-byte ZX-UX ARG1 limit")
        ptrs=[]
        for b in encoded:
            a=self.mem.allocate(len(b)+1,1,None,"argv",zero=True,readonly=False)
            self.mem.write_bytes(a.start,b+b"\0");a.readonly=True
            ptrs.append(self.mem.pointer_for(a))
        va=self.mem.allocate((len(ptrs)+1)*2,2,None,"argv",zero=True,readonly=False)
        for i,p in enumerate(ptrs):self.mem.store_pointer(va.start+i*2,p)
        self.mem.store_pointer(va.start+len(ptrs)*2,PointerRecord(0,None,None));va.readonly=True
        return len(ptrs),self.mem.pointer_for(va)

    def _push_scope(self)->None:self.scope_stack.append({});self.scope_allocs.append([])
    def _pop_scope(self)->None:
        allocs=self.scope_allocs.pop();self.scope_stack.pop()
        for aid in reversed(allocs):
            a=self.mem.allocations.get(aid)
            if a and a.live:self.mem.free(aid)

    def _lookup_lv(self,name:str)->LValue:
        for s in reversed(self.scope_stack):
            if name in s:return s[name]
        if name in self.global_lvalues:return self.global_lvalues[name]
        raise RuntimeC48Error(f"runtime object lookup failed: {name}")

    def _allocate_local(self,name:str,t:CType,*,zero:bool=False)->LValue:
        a=self.mem.allocate(t.size,t.alignment,t,"auto",zero=zero)
        lv=LValue(t,self.mem.pointer_for(a));self.scope_stack[-1][name]=lv;self.scope_allocs[-1].append(a.aid);return lv

    def _call_user(self,name:str,args:list[Value])->Value|None:
        f=self.functions.get(name)
        if f is None:return self._call_builtin(name,args)
        if self.call_depth >= VM_CALL_DEPTH:
            raise RuntimeC48Error(
                f"C48 function-call depth limit exceeded ({VM_CALL_DEPTH})"
            )
        ft=CType.from_dict(f["ctype"]);params=ft.params or ()
        if len(args)!=len(params):raise RuntimeC48Error("internal argument-count mismatch")
        self.call_depth += 1
        self._push_scope()
        try:
            pnodes=f["declarator"]["suffix"]["params"]
            for pn,pt,arg in zip(pnodes,params,args):
                lv=self._allocate_local(pn["name"],pt)
                self._store(lv,self._convert(arg,pt))
            try:self._exec_compound(f["body"],reuse_scope=True)
            except ReturnSignal as r:
                if ft.ret==VOID:return None
                if r.value is None:raise RuntimeC48Error("non-void function returned without value")
                return self._convert(r.value,ft.ret)
            if ft.ret==VOID:return None
            raise RuntimeExit(1)  # required non-void fall-through runtime-error path
        finally:
            self._pop_scope()
            self.call_depth -= 1

    def _exec_compound(self,b:dict[str,Any],*,reuse_scope:bool=False)->None:
        if not reuse_scope:self._push_scope()
        try:
            for d in b["declarations"]:
                for idecl in d["declarators"]:
                    t=CType.from_dict(idecl["ctype"]);lv=self._allocate_local(idecl["declarator"]["name"],t)
                    init=idecl.get("initializer")
                    if init is not None:self._initialize(lv,init,zero_remainder=True)
            for s in b["statements"]:self._exec_stmt(s)
        finally:
            if not reuse_scope:self._pop_scope()

    def _exec_stmt(self,s:dict[str,Any])->None:
        self._tick()
        k=s["kind"]
        if k=="compound":self._exec_compound(s);return
        if k=="expr_stmt":
            if s["value"] is not None:self.eval(s["value"])
            return
        if k=="if":
            if self._truth(self.eval(s["condition"])):self._exec_stmt(s["then"])
            elif s["otherwise"] is not None:self._exec_stmt(s["otherwise"])
            return
        if k=="while":
            while self._truth(self.eval(s["condition"])):
                try:self._exec_stmt(s["body"])
                except ContinueSignal:pass
                except BreakSignal:break
            return
        if k=="do_while":
            while True:
                try:self._exec_stmt(s["body"])
                except ContinueSignal:pass
                except BreakSignal:break
                if not self._truth(self.eval(s["condition"])):break
            return
        if k=="for":
            if s["init"] is not None:self.eval(s["init"])
            while s["condition"] is None or self._truth(self.eval(s["condition"])):
                try:self._exec_stmt(s["body"])
                except ContinueSignal:pass
                except BreakSignal:break
                if s["step"] is not None:self.eval(s["step"])
            return
        if k=="break":raise BreakSignal()
        if k=="continue":raise ContinueSignal()
        if k=="return":raise ReturnSignal(None if s["value"] is None else self.eval(s["value"]))
        raise RuntimeC48Error(f"unknown statement {k}")

    def eval(self,n:dict[str,Any])->Value:
        self._tick()
        k=n["kind"]
        if k=="identifier":
            if n.get("entity")=="function":raise RuntimeC48Error("function designator used as value")
            lv=self._lookup_lv(n["name"])
            if lv.ctype.is_array:
                assert lv.ctype.base is not None
                return Value(ptr(lv.ctype.base),lv.pointer)
            return self._load(lv)
        if k=="integer_literal":
            t=CType.from_dict(n["ctype"]);return Value(t,self._norm_int(int(n["value"]),t))
        if k=="character_literal":return Value(INT,int(n["value"]))
        if k=="floating_literal":return Value(FLOAT,Float5(bytes.fromhex(n["float5"])))
        if k=="string_literal":
            sid=int(n["sid"]);a=self.string_allocs.get(sid)
            if a is None:
                data=bytes(n["bytes"])+b"\0";t=CType("array",base=CHAR,length=len(data))
                a=self.mem.allocate(len(data),1,t,"string",zero=True,readonly=False);self.mem.write_bytes(a.start,data);a.readonly=True;self.string_allocs[sid]=a
            return Value(ptr(CHAR),self.mem.pointer_for(a))
        if k in {"sizeof_type","sizeof_expr"}:return Value(UINT,int(n["sizeof_value"]))
        if k=="cast":return self._convert(self.eval(n["operand"]),CType.from_dict(n["ctype"]))
        if k=="assign":
            lv=self.lvalue(n["left"])  # destination address first
            rhs=self.eval(n["right"])
            val=self._convert(rhs,lv.ctype)
            self._store(lv,val);return val
        if k in {"unary","postfix"}:
            return self._eval_unary(n)
        if k=="index":return self._load(self.lvalue(n))
        if k=="call":
            name=n["function"]["name"];ft=CType.from_dict(n["function"]["ctype"]);params=ft.params or ()
            captured=[]
            # conversion/capture occurs immediately after each argument evaluation.
            for arg,p in zip(n["args"],params):captured.append(self._convert(self.eval(arg),p))
            rv=self._call_user(name,captured)
            if rv is None:
                if CType.from_dict(n["ctype"])==VOID:
                    return Value(VOID, None)
                raise RuntimeC48Error("function returned no value")
            return rv
        if k=="binary":return self._eval_binary(n)
        raise RuntimeC48Error(f"unknown expression {k}")

    def lvalue(self,n:dict[str,Any])->LValue:
        k=n["kind"]
        if k=="identifier":return self._lookup_lv(n["name"])
        if k=="unary" and n["op"]=="*":
            p=self.eval(n["operand"]);pr=self._as_pointer(p);t=CType.from_dict(n["ctype"]);self.mem.check_access(pr,t)
            a=self.mem.allocation(pr.aid);return LValue(t,pr,bool(a.readonly if a else False))
        if k=="index":
            base=self.eval(n["base"]);idx=self.eval(n["index"]);pr=self._as_pointer(base);bt=base.ctype.base
            if bt is None:raise RuntimeC48Error("index on incomplete pointer")
            pr2=self._pointer_shift(pr,self._int_math(idx)*bt.size)
            self.mem.check_access(pr2,bt);a=self.mem.allocation(pr2.aid);return LValue(bt,pr2,bool(a.readonly if a else False))
        raise RuntimeC48Error("expression is not an lvalue")

    def _eval_unary(self,n:dict[str,Any])->Value:
        op=n["op"]
        if op=="&":
            lv=self.lvalue(n["operand"]);return Value(CType.from_dict(n["ctype"]),lv.pointer)
        if op=="*":return self._load(self.lvalue(n))
        if op in {"++","--"} or n["kind"]=="postfix":
            lv=self.lvalue(n["operand"]);old=self._load(lv);new=self._inc(old,1 if op=="++" else -1);self._store(lv,new)
            return old if n["kind"]=="postfix" else new
        a=self.eval(n["operand"]);rt=CType.from_dict(n["ctype"])
        if op=="!":return Value(INT,0 if self._truth(a) else 1)
        if op=="+":return self._convert(a,rt)
        if op=="-":
            a=self._convert(a,rt)
            if rt.is_float:
                try:return Value(FLOAT,a.data.neg()) # type: ignore[union-attr]
                except Float5Error:raise RuntimeExit(1)
            return Value(rt,self._norm_int(-self._int_math(a),rt))
        if op=="~":
            a=self._convert(a,rt);return Value(rt,self._norm_int(~self._int_math(a),rt))
        raise RuntimeC48Error(f"unknown unary {op}")

    def _eval_binary(self,n:dict[str,Any])->Value:
        op=n["op"]
        left=self.eval(n["left"])
        if op=="&&":
            if not self._truth(left):return Value(INT,0)
            return Value(INT,1 if self._truth(self.eval(n["right"])) else 0)
        if op=="||":
            if self._truth(left):return Value(INT,1)
            return Value(INT,1 if self._truth(self.eval(n["right"])) else 0)
        right=self.eval(n["right"])
        rt=CType.from_dict(n["ctype"])
        if op in {"<<",">>"}:
            count=self._int_math(right)&(7 if left.ctype.bits==8 else 15);av=self._int_math(left)
            if op=="<<":v=av<<count
            elif left.ctype.is_signed:v=av>>count
            else:v=(av&((1<<left.ctype.bits)-1))>>count
            return Value(rt,self._norm_int(v,rt))
        if left.ctype.is_pointer or right.ctype.is_pointer:
            return self._pointer_binary(op,left,right,rt)
        common=arithmetic_common(left.ctype,right.ctype);a=self._convert(left,common);b=self._convert(right,common)
        if common.is_float:
            fa,fb=a.data,b.data;assert isinstance(fa,Float5) and isinstance(fb,Float5)
            try:
                if op=="+":return Value(FLOAT,fa.add(fb))
                if op=="-":return Value(FLOAT,fa.sub(fb))
                if op=="*":return Value(FLOAT,fa.mul(fb))
                if op=="/":return Value(FLOAT,fa.div(fb))
                c=fa.compare(fb);ok={"==":c==0,"!=":c!=0,"<":c<0,"<=":c<=0,">":c>0,">=":c>=0}[op];return Value(INT,int(ok))
            except Float5Error:raise RuntimeExit(1)
        av=self._int_math(a);bv=self._int_math(b)
        if op=="+":v=av+bv
        elif op=="-":v=av-bv
        elif op=="*":v=av*bv
        elif op in {"/","%"}:
            if bv==0:raise RuntimeExit(1)
            if common.is_signed:q=abs(av)//abs(bv);q=-q if (av<0)^(bv<0) else q
            else:q=(av&0xFFFF)//(bv&0xFFFF)
            v=q if op=="/" else av-q*bv
        elif op=="&":v=(av&0xFFFF)&(bv&0xFFFF)
        elif op=="|":v=(av&0xFFFF)|(bv&0xFFFF)
        elif op=="^":v=(av&0xFFFF)^(bv&0xFFFF)
        elif op in {"==","!=","<","<=",">",">="}:
            ok={"==":av==bv,"!=":av!=bv,"<":av<bv,"<=":av<=bv,">":av>bv,">=":av>=bv}[op];return Value(INT,int(ok))
        else:raise RuntimeC48Error(f"unknown binary op {op}")
        return Value(rt,self._norm_int(v,rt))

    def _pointer_binary(self,op:str,a:Value,b:Value,rt:CType)->Value:
        if op in {"==","!="}:
            aa=self._as_pointer(a) if a.ctype.is_pointer else PointerRecord(self._int_math(a)&0xFFFF,None,None)
            bb=self._as_pointer(b) if b.ctype.is_pointer else PointerRecord(self._int_math(b)&0xFFFF,None,None)
            eq=aa.address==bb.address;return Value(INT,int(eq if op=="==" else not eq))
        if a.ctype.is_pointer and b.ctype.is_integer and op in {"+","-"}:
            assert a.ctype.base is not None;delta=self._int_math(b)*a.ctype.base.size
            if op=="-":delta=-delta
            return Value(a.ctype,self._pointer_shift(self._as_pointer(a),delta))
        if a.ctype.is_integer and b.ctype.is_pointer and op=="+":
            assert b.ctype.base is not None;return Value(b.ctype,self._pointer_shift(self._as_pointer(b),self._int_math(a)*b.ctype.base.size))
        if a.ctype.is_pointer and b.ctype.is_pointer:
            pa,pb=self._as_pointer(a),self._as_pointer(b)
            if pa.aid is None or pa.aid!=pb.aid:raise RuntimeC48Error("unrelated pointer ordering/subtraction is outside strict C48 contract")
            if op=="-":
                assert a.ctype.base is not None;d=(pa.offset or 0)-(pb.offset or 0)
                if d%a.ctype.base.size:raise RuntimeC48Error("pointer difference not on element boundary")
                return Value(INT,self._norm_int(d//a.ctype.base.size,INT))
            x=(pa.offset or 0);y=(pb.offset or 0);ok={"<":x<y,"<=":x<=y,">":x>y,">=":x>=y}[op];return Value(INT,int(ok))
        raise RuntimeC48Error("invalid pointer operation")

    def _pointer_shift(self,p:PointerRecord,delta:int)->PointerRecord:
        if p.aid is None:
            if p.address==0:raise RuntimeC48Error("pointer arithmetic on null pointer is outside strict C48 contract")
            raise RuntimeC48Error("pointer arithmetic without live provenance")
        a=self.mem.allocation(p.aid)
        if a is None:raise RuntimeC48Error("pointer arithmetic on dead object")
        off=(p.offset if p.offset is not None else p.address-a.start)+delta
        if not 0<=off<=a.size:raise RuntimeC48Error("pointer arithmetic leaves object/one-past range")
        return PointerRecord((a.start+off)&0xFFFF,a.aid,off)

    def _inc(self,v:Value,delta:int)->Value:
        if v.ctype.is_integer:return Value(v.ctype,self._norm_int(self._int_math(v)+delta,v.ctype))
        if v.ctype.is_pointer:
            assert v.ctype.base is not None;return Value(v.ctype,self._pointer_shift(self._as_pointer(v),delta*v.ctype.base.size))
        if v.ctype.is_float:
            try:
                one=Float5.from_int(1);f=v.data;assert isinstance(f,Float5);return Value(FLOAT,f.add(one) if delta>0 else f.sub(one))
            except Float5Error:raise RuntimeExit(1)
        raise RuntimeC48Error("invalid increment")

    def _load(self,lv:LValue)->Value:
        t=lv.ctype
        if t.is_array:raise RuntimeC48Error("array value requires decay")
        addr=self.mem.check_access(lv.pointer,t)
        if t.is_integer:return Value(t,self.mem.load_integer(addr,t))
        if t.is_pointer:return Value(t,self.mem.load_pointer(addr))
        if t.is_float:return Value(t,Float5(self.mem.read_bytes(addr,5)))
        raise RuntimeC48Error("cannot load non-scalar")
    def _store(self,lv:LValue,v:Value)->None:
        t=lv.ctype
        addr=self.mem.check_access(lv.pointer,t,write=True)
        if t.is_integer:self.mem.store_integer(addr,t,self._int_math(v));return
        if t.is_pointer:self.mem.store_pointer(addr,self._as_pointer(v));return
        if t.is_float:
            f=v.data;assert isinstance(f,Float5);self.mem.write_bytes(addr,f.raw);return
        raise RuntimeC48Error("cannot store non-scalar")

    def _initialize(self,lv:LValue,init:dict[str,Any],*,zero_remainder:bool)->None:
        t=lv.ctype
        if not t.is_array:
            if init["kind"]=="string_initializer":v=self.eval(init["value"])
            else:v=self.eval(init["value"])
            self._store(lv,self._convert(v,t));return
        assert t.base is not None and t.length is not None
        # Arrays are aggregate storage; zero entire object first for C48 remainder semantics.
        a=self.mem.allocation(lv.pointer.aid);assert a
        self.mem.ram[a.start:a.end]=b'\0'*a.size;self.mem.init[a.start:a.end]=b'\x01'*a.size
        if init["kind"]=="string_initializer":
            data=bytes(init["value"]["bytes"])+b"\0"
            for i,b in enumerate(data):self.mem.store_integer(a.start+i,t.base,b)
            return
        if init["kind"]!="init_list":raise RuntimeC48Error("invalid array initializer")
        for i,e in enumerate(init["values"]):
            elv=LValue(t.base,PointerRecord(a.start+i*t.base.size,a.aid,i*t.base.size))
            self._store(elv,self._convert(self.eval(e),t.base))

    def _convert(self,v:Value,dst:CType)->Value:
        if v.ctype==dst:
            # Float pass-by-value is naturally immutable; pointer/integer are scalar copies.
            return v
        if dst.is_integer and v.ctype.is_integer:return Value(dst,self._norm_int(self._int_math(v),dst))
        if dst.is_float and v.ctype.is_integer:
            try:return Value(FLOAT,Float5.from_int(self._int_math(v)))
            except Float5Error:raise RuntimeExit(1)
        if dst.is_integer and v.ctype.is_float:
            f=v.data;assert isinstance(f,Float5);x=f.trunc_int()
            if dst in {SHORT,INT} and not -32768<=x<=32767:raise RuntimeExit(1)
            if dst in {USHORT,UINT} and not 0<=x<=65535:raise RuntimeExit(1)
            if dst in {CHAR,UCHAR} and not 0<=x<=65535:raise RuntimeExit(1)
            return Value(dst,self._norm_int(x,dst))
        if dst.is_pointer and v.ctype.is_pointer:
            return Value(dst,self._as_pointer(v))
        if dst.is_pointer and v.ctype.is_integer and self._int_math(v)==0:return Value(dst,PointerRecord(0,None,None))
        raise RuntimeC48Error(f"unsupported conversion {v.ctype} -> {dst}")

    @staticmethod
    def _norm_int(x:int,t:CType)->int:
        u=x&((1<<t.bits)-1)
        return u-(1<<t.bits) if t.is_signed and u&(1<<(t.bits-1)) else u
    @staticmethod
    def _int_math(v:Value)->int:
        if not v.ctype.is_integer:raise RuntimeC48Error("integer value required")
        return int(v.data)
    @staticmethod
    def _to_unsigned(v:Value)->int:return int(v.data)&((1<<v.ctype.bits)-1)
    @staticmethod
    def _as_pointer(v:Value)->PointerRecord:
        if not v.ctype.is_pointer or not isinstance(v.data,PointerRecord):raise RuntimeC48Error("pointer value required")
        return v.data
    def _truth(self,v:Value)->bool:
        if v.ctype.is_integer:return self._int_math(v)!=0
        if v.ctype.is_pointer:return self._as_pointer(v).address!=0
        if v.ctype.is_float:
            f=v.data;assert isinstance(f,Float5);return not f.is_zero()
        raise RuntimeC48Error("scalar truth value required")

    def _read_cstr(self,p:PointerRecord)->bytes:
        if p.address==0:raise RuntimeC48Error("null string pointer")
        a=self.mem.allocation(p.aid)
        if a is None:raise RuntimeC48Error("string pointer outside live object")
        if p.offset is None or p.offset != p.address - a.start:
            raise RuntimeC48Error("string pointer provenance/offset mismatch")
        out=bytearray();addr=p.address
        while addr<a.end:
            b=self.mem.read8(addr)
            if b==0:return bytes(out)
            out.append(b);addr+=1
        raise RuntimeC48Error("unterminated string within live object")
    def _read_cstr_prefix(self,p:PointerRecord,n:int)->tuple[bytes,bool]:
        """Read at most n source bytes, stopping at NUL without reading beyond n."""
        if n==0:return b"",False
        if p.address==0:raise RuntimeC48Error("null string pointer")
        a=self.mem.allocation(p.aid)
        if a is None:raise RuntimeC48Error("string pointer outside live object")
        if p.offset is None or p.offset != p.address - a.start:
            raise RuntimeC48Error("string pointer provenance/offset mismatch")
        out=bytearray();addr=p.address
        for _ in range(n):
            if addr>=a.end:raise RuntimeC48Error("bounded string read leaves live object")
            b=self.mem.read8(addr);addr+=1
            if b==0:return bytes(out),True
            out.append(b)
        return bytes(out),False

    def _builtin_table(self):
        return {
            "exit":self._b_exit,"yield":self._b_yield,"sleep":self._b_sleep,"getpid":lambda a:Value(INT,1),
            "getchar":self._b_getchar,"putchar":self._b_putchar,"puts":self._b_puts,
            "strlen":self._b_strlen,"strcmp":self._b_strcmp,"strcpy":self._b_strcpy,"strncpy":self._b_strncpy,
            "memcpy":self._b_memcpy,"memmove":self._b_memmove,"memchr":self._b_memchr,"memset":self._b_memset,
            "malloc":self._b_malloc,"free":self._b_free,
            "cls":lambda a:self._screen0(self.screen.cls),"plot":self._b_plot,"point":self._b_point,"draw":self._b_draw,"circle":self._b_circle,
            "ink":lambda a:self._screen1(self.screen.ink,a),"paper":lambda a:self._screen1(self.screen.paper,a),
            "bright":lambda a:self._screen1(self.screen.bright,a),"flash":lambda a:self._screen1(self.screen.flash,a),
            "inverse":lambda a:self._screen1(self.screen.inverse,a),"over":lambda a:self._screen1(self.screen.over,a),
            "border":lambda a:self._screen1(self.screen.border,a),"print_at":self._b_print_at,
            "udg_define":self._b_udg_define,"udg_get":self._b_udg_get,"udg_draw":self._b_udg_draw,
            "udg_clear":self._b_udg_clear,"udg_draw_2x2":self._b_udg_draw_2x2,
            "sin":lambda a:self._math1("sin",a),"cos":lambda a:self._math1("cos",a),"tan":lambda a:self._math1("tan",a),
            "asin":lambda a:self._math1("asin",a),"acos":lambda a:self._math1("acos",a),"atan":lambda a:self._math1("atan",a),
            "sqrt":lambda a:self._math1("sqrt",a),"exp":lambda a:self._math1("exp",a),"log":lambda a:self._math1("log",a),
            "fabs":lambda a:Value(FLOAT,self._farg(a,0).abs()),"pow":self._b_pow,
            "ticks":lambda a:Value(UINT,int((time.monotonic()-self.start_time)*50)&0xFFFF),
        }
    def _call_builtin(self,name,args):
        fn=self.builtins.get(name)
        if fn is None:raise RuntimeC48Error(f"external function {name!r} has no host runtime implementation")
        return fn(args)
    def _b_exit(self,a):raise RuntimeExit(self._to_unsigned(a[0])&0xFF)
    def _b_yield(self,a):self.display_update();return Value(INT,0)
    def _b_sleep(self,a):
        # Host profile interprets argument as 50-Hz ticks to mirror SYS_SLEEP semantics.
        ticks=self._to_unsigned(a[0]);time.sleep(ticks/50.0);self.display_update();return Value(INT,0)
    def _b_getchar(self,a):return Value(INT,self.input_provider())
    def _b_putchar(self,a):
        c=self._to_unsigned(a[0])&0xFF;self.screen.putchar(c);self.display_update();return Value(INT,c)
    def _b_puts(self,a):self.screen.puts(self._read_cstr(self._as_pointer(a[0])));self.display_update();return Value(INT,0)
    def _b_strlen(self,a):return Value(UINT,len(self._read_cstr(self._as_pointer(a[0]))))
    def _b_strcmp(self,a):
        x=self._read_cstr(self._as_pointer(a[0]));y=self._read_cstr(self._as_pointer(a[1]));return Value(INT,0 if x==y else (-1 if x<y else 1))
    def _b_strcpy(self,a):
        dst=self._as_pointer(a[0]);data=self._read_cstr(self._as_pointer(a[1]))+b'\0';self.mem.require_range(dst,len(data),write=True);self.mem.write_bytes(dst.address,data);return Value(a[0].ctype,dst)
    def _b_strncpy(self,a):
        dst=self._as_pointer(a[0]);srcp=self._as_pointer(a[1]);n=self._to_unsigned(a[2])
        if n==0:return Value(a[0].ctype,dst)
        self.mem.require_range(dst,n,write=True)
        prefix,terminated=self._read_cstr_prefix(srcp,n)
        data=prefix+(b'\0'*(n-len(prefix)) if terminated else b'')
        self.mem.write_bytes(dst.address,data);return Value(a[0].ctype,dst)
    def _b_memcpy(self,a):
        d=self._as_pointer(a[0]);s=self._as_pointer(a[1]);n=self._to_unsigned(a[2])
        if n==0:return Value(a[0].ctype,d)
        self.mem.copy_bytes(d,s,n);return Value(a[0].ctype,d)
    def _b_memmove(self,a):return self._b_memcpy(a)
    def _b_memchr(self,a):
        p=self._as_pointer(a[0]);c=self._to_unsigned(a[1])&255;n=self._to_unsigned(a[2])
        if n==0:return Value(ptr(VOID),PointerRecord(0,None,None))
        al=self.mem.require_range(p,n)
        for i in range(n):
            if self.mem.read8(p.address+i)==c:
                off=p.address-al.start+i
                found=PointerRecord(p.address+i,al.aid,off)
                return Value(ptr(VOID),found)
        return Value(ptr(VOID),PointerRecord(0,None,None))
    def _b_memset(self,a):
        p=self._as_pointer(a[0]);c=self._to_unsigned(a[1])&255;n=self._to_unsigned(a[2])
        if n==0:return Value(a[0].ctype,p)
        self.mem.memset(p,c,n);return Value(a[0].ctype,p)
    def _b_malloc(self,a):
        n=self._to_unsigned(a[0])
        if n==0:return Value(ptr(VOID),PointerRecord(0,None,None))
        # Native C48 malloc is confined to the link-time BSS heap.  The host VM
        # enforces the same configured byte ceiling (1024 by default); address
        # placement/allocator metadata are intentionally host-profile details.
        if self.heap_live_bytes + n > self.heap_size:
            return Value(ptr(VOID),PointerRecord(0,None,None))
        try:
            al=self.mem.allocate(n,2,None,"heap",zero=False)
            self.heap_allocs.add(al.aid);self.heap_live_bytes += n
            return Value(ptr(VOID),self.mem.pointer_for(al))
        except RuntimeC48Error:return Value(ptr(VOID),PointerRecord(0,None,None))
    def _b_free(self,a):
        p=self._as_pointer(a[0])
        if p.address==0:return None
        if p.aid not in self.heap_allocs:raise RuntimeC48Error("free requires pointer returned by malloc")
        al=self.mem.allocation(p.aid)
        if al is None or p.offset != 0 or p.address != al.start:
            raise RuntimeC48Error("free requires the exact base pointer returned by malloc")
        self.heap_live_bytes -= al.size
        self.mem.free(p.aid);self.heap_allocs.remove(p.aid);return None
    def _screen0(self,fn):r=fn();self.display_update();return Value(INT,r)
    def _screen1(self,fn,a):r=fn(self._int_math(a[0]));self.display_update();return Value(INT,r)
    def _b_plot(self,a):r=self.screen.plot(self._int_math(a[0]),self._int_math(a[1]));self.display_update();return Value(INT,r)
    def _b_point(self,a):return Value(INT,self.screen.point(self._int_math(a[0]),self._int_math(a[1])))
    def _b_draw(self,a):r=self.screen.draw(*(self._int_math(x) for x in a[:4]));self.display_update();return Value(INT,r)
    def _b_circle(self,a):r=self.screen.circle(*(self._int_math(x) for x in a[:3]));self.display_update();return Value(INT,r)
    def _b_print_at(self,a):
        row=self._int_math(a[0]);col=self._int_math(a[1])
        if not (0<=row<24 and 0<=col<64):return Value(INT,1)
        r=self.screen.print_at(row,col,self._read_cstr(self._as_pointer(a[2])));self.display_update();return Value(INT,r)
    def _b_udg_define(self,a):
        slot=self._int_math(a[0])
        if not 0<=slot<32:return Value(INT,1)
        p=self._as_pointer(a[1]);self.mem.require_range(p,8);data=self.mem.read_bytes(p.address,8)
        return Value(INT,self.screen.udg_define(slot,data))
    def _b_udg_get(self,a):
        slot=self._int_math(a[0])
        if not 0<=slot<32:return Value(INT,1)
        p=self._as_pointer(a[1]);self.mem.require_range(p,8,write=True);data=self.screen.udg_get(slot)
        self.mem.write_bytes(p.address,data);return Value(INT,0)
    def _b_udg_draw(self,a):
        r=self.screen.udg_draw(self._int_math(a[0]),self._int_math(a[1]),self._int_math(a[2]));self.display_update();return Value(INT,r)
    def _b_udg_clear(self,a):return Value(INT,self.screen.udg_clear(self._int_math(a[0])))
    def _b_udg_draw_2x2(self,a):
        r=self.screen.udg_draw_2x2(self._int_math(a[0]),self._int_math(a[1]),self._int_math(a[2]));self.display_update();return Value(INT,r)

    def _farg(self,a,i):
        f=a[i].data
        if not isinstance(f,Float5):raise RuntimeC48Error("float argument required")
        return f
    def _math1(self,name,a):
        if not self.approximate_rom_math:raise RuntimeC48Error(f"{name} requires --allow-approx-rom-math; byte-exact ROM oracle not certified")
        try:return Value(FLOAT,self._farg(a,0).approx_unary(name))
        except Float5Error:raise RuntimeExit(1)
    def _b_pow(self,a):
        if not self.approximate_rom_math:raise RuntimeC48Error("pow requires --allow-approx-rom-math; byte-exact ROM oracle not certified")
        try:return Value(FLOAT,self._farg(a,0).approx_pow(self._farg(a,1)))
        except Float5Error:raise RuntimeExit(1)
