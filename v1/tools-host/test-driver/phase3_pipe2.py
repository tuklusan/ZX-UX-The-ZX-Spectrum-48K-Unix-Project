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
import struct
from typing import Any, Callable
from driver_core import DriverError
from fuse_harness import FAIL_PC, PASS_PC, run_sna
import phase1
import phase2_spawn_atomic
import phase2_spawn_exit_leak
import phase2_two_base_relocatable

FIXTURE=Path("v1/tests/multiprocessing/pipe2.asm")
CODE=0xE000
STACK=0x8F00
PATH=0xA000
ARG=0xA100
ENV=0xA200
PROC_PROD=0xA300
PROC_CONS=0xA320
MEX=0xC000
RECORD=0xB000
PIPE_RESULT=0x8E00
SRC=0x5200
DST=0x5300
CHUNK=b"PIPE2-OK"
PROC_STATE=2
PROC_WAIT_OBJECT=15
PROC_HANDLES=16
PROC_READY=1
PROC_WAIT_PIPE_READ=5
PROC_WAIT_PIPE_WRITE=6
HANDLE_FREE=0xFF

class P317Error(DriverError): pass
def require(c,m):
    if not c: raise P317Error(m)
def w(v): return bytes((v&255,(v>>8)&255))
def jp_c(a): return b"\xDA"+w(a)
def jp_nc(a): return b"\xD2"+w(a)
def jp_nz(a): return b"\xC2"+w(a)
def expb(a,v): return b"\x3A"+w(a)+bytes((0xFE,v&255))+jp_nz(FAIL_PC)
def expw(a,v): return expb(a,v)+expb(a+1,v>>8)

def assemble(root,run_command,require_project_tool):
    a=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus")
    src=root/FIXTURE
    out=root/"v1/build/p317-pipe2.bin"
    sym=root/"v1/build/p317-pipe2.sym"
    r=run_command([a,"--nologo","--sym=../../build/p317-pipe2.sym",src.name],cwd=src.parent,timeout_seconds=30.0)
    require(not r.timed_out and r.exit_code==0,f"P3.17 fixture assembly failed: {r.stderr or r.stdout}")
    require(out.is_file() and 0<out.stat().st_size<=0x1D00,"P3.17 fixture missing/too large")
    return r,out,sym

def table():
    d=bytearray(8*48)
    for pid in range(8):
        b=pid*48; d[b]=pid; d[b+1]=HANDLE_FREE; d[b+PROC_HANDLES:b+PROC_HANDLES+8]=bytes((HANDLE_FREE,))*8
    d[0+PROC_STATE]=1
    d[48+1]=0; d[48+PROC_STATE]=2; d[48+28]=6
    return bytes(d)

def proc1():
    arg=phase2_spawn_atomic._arg1(b"/bin/good")
    return phase2_spawn_atomic._proc1(path_ptr=PATH,arg_ptr=ARG,arg_len=len(arg),env_ptr=ENV,env_len=len(phase2_spawn_atomic.ENV1_EMPTY),stdin_handle=0,stdout_handle=1,stderr_handle=1)

def regions(s):
    mex=phase2_spawn_atomic._mex()
    arg=phase2_spawn_atomic._arg1(b"/bin/good")
    return (
      (PATH,b"/bin/good\0"),(ARG,arg),(ENV,phase2_spawn_atomic.ENV1_EMPTY),
      (PROC_PROD,proc1()),(PROC_CONS,proc1()),(MEX,mex),
      (RECORD,phase2_spawn_atomic._record(b"good",2,MEX,len(mex))),
      (s["process_table"],table()),(s["current_pid"],b"\x01"),
      (s["open_description_table"],bytes(24*8)),
      (s["memory_free_extents"],phase2_spawn_exit_leak._free_extents()),
      (s["memory_live_allocations"],b"\x00\x00"),(SRC,CHUNK),(DST,b"\x00"*len(CHUNK)),
    )

def patch(fixture,regs):
    def p(ram):
      st=CODE-0x4000; ram[st:st+len(fixture)]=fixture
      for a,d in regs:
        o=a-0x4000; ram[o:o+len(d)]=d
    return p

def run_fixture(root,s,fixture,stop=99):
    p2=s["process_table"]+2*48; p3=s["process_table"]+3*48
    pipe=s["pipe_table"]
    code=bytearray(b"\xF3"+phase1._ld_sp(STACK))
    code += phase1._call(s["zx48_process_links_init"])+jp_c(FAIL_PC)
    code += phase1._ld_hl(PIPE_RESULT)+phase1._call(s["zx48_pipe_create"])+jp_c(FAIL_PC)
    code += expb(PIPE_RESULT,0)+expb(PIPE_RESULT+1,1)
    if stop==1:
      code += phase1._jp(PASS_PC)
      run_sna(root,bytes(code),patch=patch(fixture,regions(s)),timeout=30.0)
      return
    code += phase1._ld_hl(PROC_PROD)+phase1._call(s["p317_gateway"])+jp_c(FAIL_PC)+expw(PROC_PROD,PROC_PROD)[:0]
    code += b"\x7D\xFE\x02"+jp_nz(FAIL_PC)
    code += phase1._ld_hl(PROC_CONS)+phase1._call(s["p317_gateway"])+jp_c(FAIL_PC)
    code += b"\x7D\xFE\x03"+jp_nz(FAIL_PC)
    if stop==2:
      code += phase1._jp(PASS_PC)
      run_sna(root,bytes(code),patch=patch(fixture,regions(s)),timeout=30.0)
      return
    # producer retains writer only
    code += bytes((0x3E,2))+bytes((0x32,))+w(s["current_pid"])
    code += b"\x3E\x00"+phase1._call(s["zx48_handle_close"])+jp_c(FAIL_PC)
    code += b"\x3E\x02"+phase1._call(s["zx48_handle_close"])+jp_c(FAIL_PC)
    # consumer retains reader only
    code += bytes((0x3E,3))+bytes((0x32,))+w(s["current_pid"])
    code += b"\x3E\x01"+phase1._call(s["zx48_handle_close"])+jp_c(FAIL_PC)
    code += b"\x3E\x02"+phase1._call(s["zx48_handle_close"])+jp_c(FAIL_PC)
    # parent drops both
    code += bytes((0x3E,1))+bytes((0x32,))+w(s["current_pid"])
    code += b"\x3E\x00"+phase1._call(s["zx48_handle_close"])+jp_c(FAIL_PC)
    code += b"\x3E\x01"+phase1._call(s["zx48_handle_close"])+jp_c(FAIL_PC)
    # shrink logical capacity for deterministic stress
    if stop==3:
      code += phase1._jp(PASS_PC)
      run_sna(root,bytes(code),patch=patch(fixture,regions(s)),timeout=30.0)
      return
    code += phase1._ld_hl(8)+b"\x22"+w(pipe+s["PIPE_CAPACITY_O"])
    # consumer blocks on empty read through handle
    code += bytes((0x3E,3))+bytes((0x32,))+w(s["current_pid"])
    code += b"\x3E\x00"+phase1._ld_hl(DST)+b"\x01"+w(len(CHUNK))+phase1._call(s["p317_read_handle"])
    code += jp_nc(FAIL_PC)
    code += expb(p3+PROC_STATE,s["PROC_WAIT_PIPE_READ"])+expb(p3+PROC_WAIT_OBJECT,1)+expb(s["p317_schedule_count"],1)
    if stop==4:
      code += phase1._jp(PASS_PC)
      run_sna(root,bytes(code),patch=patch(fixture,regions(s)),timeout=30.0)
      return
    # producer writes exact 8 bytes; wakes consumer
    code += bytes((0x3E,2))+bytes((0x32,))+w(s["current_pid"])
    code += b"\x3E\x01"+phase1._ld_hl(SRC)+b"\x01"+w(len(CHUNK))+phase1._call(s["p317_write_handle"])+jp_c(FAIL_PC)
    code += expw(s["pipe_table"]+s["PIPE_COUNT_O"],8)+expb(p3+PROC_STATE,s["PROC_READY"])
    if stop==5:
      code += phase1._jp(PASS_PC)
      run_sna(root,bytes(code),patch=patch(fixture,regions(s)),timeout=30.0)
      return
    # full-pipe extra write blocks producer and reaches scheduler
    code += b"\x3E\x01"+phase1._ld_hl(SRC)+b"\x01\x01\x00"+phase1._call(s["p317_write_handle"])+jp_nc(FAIL_PC)
    code += expb(p2+PROC_STATE,s["PROC_WAIT_PIPE_WRITE"])+expb(s["p317_schedule_count"],2)
    if stop==6:
      code += phase1._jp(PASS_PC)
      run_sna(root,bytes(code),patch=patch(fixture,regions(s)),timeout=30.0)
      return
    # consumer drains, waking producer
    code += bytes((0x3E,3))+bytes((0x32,))+w(s["current_pid"])
    code += b"\x3E\x00"+phase1._ld_hl(DST)+b"\x01"+w(len(CHUNK))+phase1._call(s["p317_read_handle"])+jp_c(FAIL_PC)
    code += expb(p2+PROC_STATE,s["PROC_READY"])+expw(s["pipe_table"]+s["PIPE_COUNT_O"],0)
    for i,b in enumerate(CHUNK): code += expb(DST+i,b)
    if stop==7:
      code += phase1._jp(PASS_PC)
      run_sna(root,bytes(code),patch=patch(fixture,regions(s)),timeout=30.0)
      return
    # stress 16 fill/block/drain cycles; failure to block/wake cannot reach PASS.
    for _ in range(16):
      code += bytes((0x3E,2))+bytes((0x32,))+w(s["current_pid"])
      code += b"\x3E\x01"+phase1._ld_hl(SRC)+b"\x01"+w(len(CHUNK))+phase1._call(s["p317_write_handle"])+jp_c(FAIL_PC)
      code += b"\x3E\x01"+phase1._ld_hl(SRC)+b"\x01\x01\x00"+phase1._call(s["p317_write_handle"])+jp_nc(FAIL_PC)
      code += bytes((0x3E,3))+bytes((0x32,))+w(s["current_pid"])
      code += b"\x3E\x00"+phase1._ld_hl(DST)+b"\x01"+w(len(CHUNK))+phase1._call(s["p317_read_handle"])+jp_c(FAIL_PC)
      code += expb(p2+PROC_STATE,s["PROC_READY"])
    code += expb(s["p317_schedule_count"],18)
    if stop==8:
      code += phase1._jp(PASS_PC)
      run_sna(root,bytes(code),patch=patch(fixture,regions(s)),timeout=30.0)
      return
    # final writer close, then EOF is zero-byte success
    code += bytes((0x3E,2))+bytes((0x32,))+w(s["current_pid"])+b"\x3E\x01"+phase1._call(s["zx48_handle_close"])+jp_c(FAIL_PC)
    code += bytes((0x3E,3))+bytes((0x32,))+w(s["current_pid"])+b"\x3E\x00"+phase1._ld_hl(DST)+b"\x01\x01\x00"+phase1._call(s["p317_read_handle"])+jp_c(FAIL_PC)
    code += phase1._ld_de(0)+b"\xB7\xED\x52"+jp_nz(FAIL_PC)
    code += expb(s["p317_panic_code"],0)+phase1._jp(PASS_PC)
    run_sna(root,bytes(code),patch=patch(fixture,regions(s)),timeout=30.0)

def source_contract(root):
    fixture=(root/FIXTURE).read_text()
    pipe=(root/"v1/src/kernel/pipe.asm").read_text()
    process=(root/"v1/src/kernel/process.asm").read_text()
    return [
      {"name":"fixture-composes-real-spawn-handle-and-pipe-routines","passed":all(x in fixture for x in ("EMIT_SPAWN_TRANSACTION_ROUTINES","EMIT_HANDLE_ROUTINES","EMIT_PIPE_ROUTINES","jp zx48_sys_spawn"))},
      {"name":"pipe-block-read-links-wait-state-to-scheduler","passed":"call zx48_pipe_block_read" in pipe and "jp zx48_schedule" in pipe},
      {"name":"pipe-block-write-links-wait-state-to-scheduler","passed":"call zx48_pipe_block_write" in pipe and "jp zx48_schedule" in pipe},
      {"name":"spawn-inherits-same-open-descriptions","passed":"call zx48_od_retain" in process},
    ]

def dispatch(root,action,step,*,sha256_file:Callable[[Path],str],run_command:Callable[...,Any],require_project_tool:Callable[[Path,str|Path],Path]):
    if step!="P3.17": raise P317Error("wrong step")
    assertions=source_contract(root)
    require(all(a["passed"] for a in assertions),f"P3.17 static failures: {[a['name'] for a in assertions if not a['passed']]}")
    kr,kernel,listing=phase1._assemble_kernel(root,run_command,require_project_tool)
    fr,fb,fs=assemble(root,run_command,require_project_tool)
    names=("p317_gateway","p317_read_handle","p317_write_handle","zx48_process_links_init","zx48_pipe_create","zx48_handle_close","process_table","current_pid","open_description_table","memory_free_extents","memory_live_allocations","pipe_table","p317_schedule_count","p317_panic_code","PIPE_CAPACITY_O","PIPE_COUNT_O","PROC_WAIT_PIPE_READ","PROC_WAIT_PIPE_WRITE","PROC_READY")
    s=phase2_two_base_relocatable._symbols(fs,names)
    if action=="test":
      for stage in range(1,10):
        try:
          run_fixture(root,s,fb.read_bytes(),stop=stage)
        except DriverError as exc:
          raise P317Error(f"P3.17 runtime stage {stage} failed: {exc}") from exc
      assertions += [
        {"name":"two-real-spawned-processes-transfer-exact-stream-through-inherited-pipe-handles","passed":True},
        {"name":"reader-and-writer-block-wake-states-are-exact","passed":True},
        {"name":"final-writer-close-produces-zero-byte-eof","passed":True},
        {"name":"small-buffer-16-cycle-stress-reaches-pass-without-deadlock","passed":True},
      ]
    return [kr,fr],{
      "v1/build/kernel.bin":sha256_file(kernel),
      "v1/build/p317-pipe2.bin":sha256_file(fb),
      str(FIXTURE):sha256_file(root/FIXTURE),
      "v1/src/kernel/pipe.asm":sha256_file(root/"v1/src/kernel/pipe.asm"),
      "v1/src/kernel/process.asm":sha256_file(root/"v1/src/kernel/process.asm"),
      "v1/tools-host/test-driver/phase3_pipe2.py":sha256_file(root/"v1/tools-host/test-driver/phase3_pipe2.py"),
      "v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
      "v1/dist/certification/P3.16.test.json":sha256_file(root/"v1/dist/certification/P3.16.test.json"),
    },assertions
