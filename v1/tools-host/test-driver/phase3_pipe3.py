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
import phase1
import phase2_spawn_atomic
import phase2_spawn_exit_leak
import phase2_two_base_relocatable

FIXTURE=Path("v1/tests/multiprocessing/pipe3.asm")
CODE=0xE000
STACK=0x8F00
PATH=0xA000
ARG=0xA100
ENV=0xA200
PROC_A=0xA300
PROC_B=0xA320
PROC_C=0xA340
MEX=0xC000
RECORD=0xB000
PIPE1_RESULT=0x8E00
PIPE2_RESULT=0x8E10
SRC=0x5200
MID=0x5300
DST=0x5400
STATUS=0x5500
PAYLOAD=b"PIPE3-OK"
HANDLE_FREE=0xFF
PROC_STATE=2
PROC_READY=1
PROC_ZOMBIE=4
PROC_WAIT_OBJECT=15
PROC_HANDLES=16

class P318Error(DriverError): pass
def require(c,m):
    if not c: raise P318Error(m)
def w(v): return bytes((v&255,(v>>8)&255))
def jp_c(a): return b"\xDA"+w(a)
def jp_nc(a): return b"\xD2"+w(a)
def jp_nz(a): return b"\xC2"+w(a)
def expb(a,v): return b"\x3A"+w(a)+bytes((0xFE,v&255))+jp_nz(FAIL_PC)
def expw(a,v): return expb(a,v)+expb(a+1,v>>8)
def setpid(a,s): return bytes((0x3E,a&255,0x32))+w(s["current_pid"])

def assemble(root,run_command,require_project_tool):
    a=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus")
    src=root/FIXTURE
    out=root/"v1/build/p318-pipe3.bin"
    sym=root/"v1/build/p318-pipe3.sym"
    r=run_command([a,"--nologo","--sym=../../build/p318-pipe3.sym",src.name],cwd=src.parent,timeout_seconds=30.0)
    require(not r.timed_out and r.exit_code==0,f"P3.18 fixture assembly failed: {r.stderr or r.stdout}")
    require(out.is_file() and 0<out.stat().st_size<=0x1D00,"P3.18 fixture missing/too large")
    return r,out,sym

def table():
    d=bytearray(8*48)
    for pid in range(8):
        b=pid*48
        d[b]=pid
        d[b+1]=HANDLE_FREE
        d[b+PROC_HANDLES:b+PROC_HANDLES+8]=bytes((HANDLE_FREE,))*8
    d[PROC_STATE]=1
    d[48+1]=0
    d[48+PROC_STATE]=2
    d[48+28]=6
    return bytes(d)

def proc1(stdin_handle,stdout_handle,stderr_handle):
    arg=phase2_spawn_atomic._arg1(b"/bin/good")
    return phase2_spawn_atomic._proc1(path_ptr=PATH,arg_ptr=ARG,arg_len=len(arg),env_ptr=ENV,env_len=len(phase2_spawn_atomic.ENV1_EMPTY),stdin_handle=stdin_handle,stdout_handle=stdout_handle,stderr_handle=stderr_handle)

def regions(s):
    mex=phase2_spawn_atomic._mex()
    arg=phase2_spawn_atomic._arg1(b"/bin/good")
    return (
      (PATH,b"/bin/good\0"),(ARG,arg),(ENV,phase2_spawn_atomic.ENV1_EMPTY),
      (PROC_A,proc1(0,1,1)),(PROC_B,proc1(0,3,3)),(PROC_C,proc1(2,0,0)),(MEX,mex),
      (RECORD,phase2_spawn_atomic._record(b"good",2,MEX,len(mex))),
      (s["process_table"],table()),(s["current_pid"],b"\x01"),
      (s["open_description_table"],bytes(24*8)),
      (s["memory_free_extents"],phase2_spawn_exit_leak._free_extents()),
      (s["memory_live_allocations"],b"\x00\x00"),
      (SRC,PAYLOAD),(MID,b"\x00"*len(PAYLOAD)),(DST,b"\x00"*len(PAYLOAD)),(STATUS,b"\x00\x00\x00"),
    )

def patch(fixture,regs):
    def p(ram):
      st=CODE-0x4000
      ram[st:st+len(fixture)]=fixture
      for a,d in regs:
        o=a-0x4000
        ram[o:o+len(d)]=d
    return p

def close(code,s,pid,handles):
    code += setpid(pid,s)
    for h in handles:
        code += bytes((0x3E,h))+phase1._call(s["zx48_handle_close"])+jp_c(FAIL_PC)
    return code

def transfer(code,s,pid,handle,src,count,write):
    code += setpid(pid,s)+bytes((0x3E,handle))+phase1._ld_hl(src)+b"\x01"+w(count)
    code += phase1._call(s["p318_write_handle"] if write else s["p318_read_handle"])
    return code

def spawn(code,s,ptr,want):
    code += phase1._ld_hl(ptr)+phase1._call(s["p318_gateway"])+jp_c(FAIL_PC)
    code += b"\x7D"+bytes((0xFE,want))+jp_nz(FAIL_PC)
    return code

def wait_zombie(code,s,pid,status_off):
    p=s["process_table"]+pid*48
    code += setpid(1,s)
    code += bytes((0x3E,PROC_ZOMBIE,0x32))+w(p+PROC_STATE)
    code += bytes((0x11,))+w(STATUS+status_off)+bytes((0x3E,pid))+phase1._call(s["zx48_process_wait_specific"])+jp_c(FAIL_PC)
    code += b"\x7D"+bytes((0xFE,pid))+jp_nz(FAIL_PC)
    code += expb(p+PROC_STATE,0)
    return code

def run_fixture(root,s,fixture,retain_parent_writer=False,stop=99):
    p4=s["process_table"]+4*48
    pipe2=s["pipe_table"]+s["PIPE_RECORD_SIZE"]
    code=bytearray(b"\xF3"+phase1._ld_sp(STACK))
    code += phase1._call(s["zx48_process_links_init"])+jp_c(FAIL_PC)
    code += phase1._ld_hl(PIPE1_RESULT)+phase1._call(s["zx48_pipe_create"])+jp_c(FAIL_PC)
    code += expb(PIPE1_RESULT,0)+expb(PIPE1_RESULT+1,1)
    code += phase1._ld_hl(PIPE2_RESULT)+phase1._call(s["zx48_pipe_create"])+jp_c(FAIL_PC)
    code += expb(PIPE2_RESULT,2)+expb(PIPE2_RESULT+1,3)
    if stop==1:
        code += phase1._jp(PASS_PC)
        run_sna(root,bytes(code),patch=patch(fixture,regions(s)),timeout=30.0); return
    code=spawn(code,s,PROC_A,2)
    code=spawn(code,s,PROC_B,3)
    code=spawn(code,s,PROC_C,4)
    if stop==2:
        code += phase1._jp(PASS_PC)
        run_sna(root,bytes(code),patch=patch(fixture,regions(s)),timeout=30.0); return

    # Stage A retains pipe1 writer only; stage B links pipe1 reader to pipe2 writer;
    # stage C retains pipe2 reader only.
    code=close(code,s,2,(0,2))
    code=close(code,s,3,(2,))
    code=close(code,s,4,(1,2))
    # Parent always drops pipe1 refs and pipe2 reader. Positive path also drops the
    # final pipe2 writer; the negative fixture intentionally retains that one ref.
    code=close(code,s,1,(0,1,2))
    if not retain_parent_writer:
        code=close(code,s,1,(3,))
    if stop==3:
        code += phase1._jp(PASS_PC)
        run_sna(root,bytes(code),patch=patch(fixture,regions(s)),timeout=30.0); return

    code=transfer(code,s,2,1,SRC,len(PAYLOAD),True)+jp_c(FAIL_PC)
    code=transfer(code,s,3,0,MID,len(PAYLOAD),False)+jp_c(FAIL_PC)
    for i,b in enumerate(PAYLOAD): code += expb(MID+i,b)
    code=transfer(code,s,3,1,MID,len(PAYLOAD),True)+jp_c(FAIL_PC)
    code=transfer(code,s,4,0,DST,len(PAYLOAD),False)+jp_c(FAIL_PC)
    for i,b in enumerate(PAYLOAD): code += expb(DST+i,b)
    if stop==4:
        code += phase1._jp(PASS_PC)
        run_sna(root,bytes(code),patch=patch(fixture,regions(s)),timeout=30.0); return

    # Final stage writers close. Pipe2 EOF is governed by the final writer ref.
    code=close(code,s,2,(1,))
    code=close(code,s,3,(0,1))
    code += expw(pipe2+s["PIPE_COUNT_O"],0)
    code=transfer(code,s,4,0,DST,1,False)
    if retain_parent_writer:
        code += jp_nc(FAIL_PC)
        code += expb(p4+PROC_STATE,s["PROC_WAIT_PIPE_READ"])
        code=close(code,s,1,(3,))
        code=transfer(code,s,4,0,DST,1,False)+jp_c(FAIL_PC)
    else:
        code += jp_c(FAIL_PC)
    code += phase1._ld_de(0)+b"\xB7\xED\x52"+jp_nz(FAIL_PC)
    code=close(code,s,4,(0,))
    if stop==5:
        code += phase1._jp(PASS_PC)
        run_sna(root,bytes(code),patch=patch(fixture,regions(s)),timeout=30.0); return

    # Parent performs real wait/reap operations on all three completed pipeline
    # children after dropping its stream references.
    code=wait_zombie(code,s,2,0)
    if stop==6:
        code += phase1._jp(PASS_PC)
        run_sna(root,bytes(code),patch=patch(fixture,regions(s)),timeout=30.0); return
    code=wait_zombie(code,s,3,1)
    if stop==7:
        code += phase1._jp(PASS_PC)
        run_sna(root,bytes(code),patch=patch(fixture,regions(s)),timeout=30.0); return
    code=wait_zombie(code,s,4,2)
    if stop==8:
        code += phase1._jp(PASS_PC)
        run_sna(root,bytes(code),patch=patch(fixture,regions(s)),timeout=30.0); return
    code += expb(s["p318_panic_code"],0)+phase1._jp(PASS_PC)
    run_sna(root,bytes(code),patch=patch(fixture,regions(s)),timeout=30.0)

def source_contract(root):
    fixture=(root/FIXTURE).read_text()
    pipe=(root/"v1/src/kernel/pipe.asm").read_text()
    process=(root/"v1/src/kernel/process.asm").read_text()
    return [
      {"name":"fixture-composes-three-stage-spawn-handle-pipe-and-wait-routines","passed":all(x in fixture for x in ("EMIT_SPAWN_TRANSACTION_ROUTINES","EMIT_HANDLE_ROUTINES","EMIT_PIPE_ROUTINES","EMIT_PARENT_CHILD_ROUTINES","jp zx48_sys_spawn"))},
      {"name":"pipe-eof-is-reference-counted-on-final-writer","passed":"PIPE_WRITERS_O" in pipe and "zx48_pipe_close_reader" in pipe},
      {"name":"spawn-inherits-open-description-references","passed":"call zx48_od_retain" in process},
      {"name":"wait-reaps-zombie-child","passed":"zx48_process_wait_reap:" in process},
    ]

def dispatch(root,action,step,*,sha256_file:Callable[[Path],str],run_command:Callable[...,Any],require_project_tool:Callable[[Path,str|Path],Path]):
    if step!="P3.18": raise P318Error("wrong step")
    assertions=source_contract(root)
    require(all(a["passed"] for a in assertions),f"P3.18 static failures: {[a['name'] for a in assertions if not a['passed']]}")
    kr,kernel,listing=phase1._assemble_kernel(root,run_command,require_project_tool)
    fr,fb,fs=assemble(root,run_command,require_project_tool)
    names=("p318_gateway","p318_read_handle","p318_write_handle","zx48_process_links_init","zx48_process_wait_specific","zx48_pipe_create","zx48_handle_close","process_table","current_pid","open_description_table","memory_free_extents","memory_live_allocations","pipe_table","p318_panic_code","PIPE_RECORD_SIZE","PIPE_COUNT_O","PROC_WAIT_PIPE_READ")
    s=phase2_two_base_relocatable._symbols(fs,names)
    if action=="test":
      for stage in range(1,9):
        try:
          run_fixture(root,s,fb.read_bytes(),retain_parent_writer=False,stop=stage)
        except DriverError as exc:
          raise P318Error(f"P3.18 positive runtime stage {stage} failed: {exc}") from exc
      try:
        run_fixture(root,s,fb.read_bytes(),retain_parent_writer=False)
      except DriverError as exc:
        raise P318Error(f"P3.18 full positive pipeline failed: {exc}") from exc
      assertions += [
        {"name":"three-spawned-stages-transfer-exact-bytes-through-two-true-pipes","passed":True},
        {"name":"parent-drops-stream-references-and-waits-for-all-three-children","passed":True},
        {"name":"eof-arrives-only-after-final-writer-reference-closes","passed":True},
      ]
      try:
        run_fixture(root,s,fb.read_bytes(),retain_parent_writer=True)
      except DriverError as exc:
        raise P318Error(f"P3.18 retained-parent-writer negative fixture failed: {exc}") from exc
      assertions.append({"name":"retained-parent-writer-negative-fixture-detects-blocked-eof-before-release","passed":True})
    return [kr,fr],{
      "v1/build/kernel.bin":sha256_file(kernel),
      "v1/build/p318-pipe3.bin":sha256_file(fb),
      str(FIXTURE):sha256_file(root/FIXTURE),
      "v1/src/kernel/pipe.asm":sha256_file(root/"v1/src/kernel/pipe.asm"),
      "v1/src/kernel/process.asm":sha256_file(root/"v1/src/kernel/process.asm"),
      "v1/tools-host/test-driver/phase3_pipe3.py":sha256_file(root/"v1/tools-host/test-driver/phase3_pipe3.py"),
      "v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
      "v1/dist/certification/P3.17.test.json":sha256_file(root/"v1/dist/certification/P3.17.test.json"),
    },assertions
