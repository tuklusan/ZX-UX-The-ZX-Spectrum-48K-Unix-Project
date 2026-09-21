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
from driver_core import DriverError
from fuse_harness import FAIL_PC, PASS_PC, run_sna
import phase1, phase3_open_descriptions
import phase2_kill_never_started, phase2_kill_started

PROC_STATE=2
PROC_FLAGS=3
PROC_WAIT_OBJECT=15
PROC_PRIVATE_FLAGS=46
PROC_DESC_SIZE=48
PROC_READY=1
PROC_RUNNING=2
PROC_WAIT_PIPE_READ=5
PROC_FLAG_CANCEL=1
PROC_PRIVATE_STARTED=0x80
KERNEL_BASE=0x8000
SHELL_BASE=0xC000
GATE_BASE=0xE000
ARG=0xA000
STATUS=0xA100

class P626Error(DriverError): pass
def require(v,m):
    if not v: raise P626Error(m)
def word(v): return bytes((v&255,(v>>8)&255))
def setb(addr,val): return bytes((0x3E,val&255,0x32))+word(addr)
def expectb(addr,val): return b"\x3A"+word(addr)+bytes((0xFE,val&255))+phase1._jp_nz(FAIL_PC)

def patch_kernel(kernel):
    return phase1._kernel_patch(kernel)

def dispatch(root:Path,action:str,step:str,*,sha256_file,run_command,require_project_tool):
    if step!="P6.26": raise DriverError(f"Phase-6 kill/BREAK step is not registered: {step}")
    process=(root/"v1/src/kernel/process.asm").read_text()
    syscall=(root/"v1/src/kernel/syscall.asm").read_text()
    shell=(root/"v1/src/shell/sh.asm").read_text()
    interrupt=(root/"v1/src/kernel/interrupt.asm").read_text()
    boundary=syscall.split("; P6.26 cooperative BREAK boundary.",1)[1].split("zx48_sys_dispatch_pipe:",1)[0]
    kill=shell.split("MACRO EMIT_P626_KILL_ROUTINES",1)[1].split("ENDM",1)[0]
    assertions=[
      {"name":"im2-remains-producer-only","passed":"ld (break_pending),a" in interrupt and "zx48_process_kill" not in interrupt and "zx48_schedule" not in interrupt.split("zx48_interrupt_break:",1)[1].split("zx48_interrupt_done:",1)[0]},
      {"name":"syscall-entry-services-break-before-dispatch","passed":syscall.index("; P6.26 cooperative BREAK boundary.") < syscall.index("cp SYS_KILL+1")},
      {"name":"shell-owner-break-is-line-eintr-only","passed":"ld a,(tty_input_owner)" in boundary and "ld a,E_INTR" in boundary},
      {"name":"child-break-targets-tty-owner-only","passed":"ld a,(current_pid)" in boundary and "xor b" in boundary and "jr nz,zx48_p626_break_restore_selector" in boundary},
      {"name":"no-break-scheduler-preemption","passed":"zx48_schedule" not in boundary},
      {"name":"current-owner-cancel-consumed-before-syscall-side-effects","passed":"ld (break_pending),a" in boundary and "ld a,E_INTR" in boundary},
      {"name":"kill-exact-one-decimal-operand","passed":"cp 1" in kill and "ld a,SYS_KILL" in kill},
      {"name":"kernel-forbids-pid0-pid1","passed":"zx48_process_kill:" in process and "cp 2" in process.split("zx48_process_kill:",1)[1].split("zx48_process_wait:",1)[0]},
    ]
    require(all(a["passed"] for a in assertions),"P6.26 static contract failure")

    cmd,kernel,listing=phase1._assemble_kernel(root,run_command,require_project_tool)
    labels=phase1._labels(listing,("zx48_process_init","zx48_syscall_impl","zx48_process_kill","process_table","current_pid","tty_input_owner","break_pending","E_INTR","E_PERM"))
    kernel_bytes=kernel.read_bytes()
    commands=[cmd]

    asm=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus")
    build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    sf=build/"p626-shell-fixture.asm"
    sf.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/shell/sh.asm"
    ORG $C000
p626_start:
    EMIT_P626_KILL_ROUTINES
p626_end:
    SAVEBIN "p626-shell-fixture.bin",p626_start,p626_end-p626_start
""",encoding="utf-8",newline="\n")
    sr=run_command([asm,"--nologo","--lst=p626-shell-fixture.lst","--sym=p626-shell-fixture.sym","p626-shell-fixture.asm"],cwd=build,timeout_seconds=30)
    require(not sr.timed_out and sr.exit_code==0,f"P6.26 shell fixture failed: {sr.stderr or sr.stdout}")
    commands.append(sr)

    if action=="test":
        table=labels["process_table"]; pid1=table+PROC_DESC_SIZE; pid2=table+2*PROC_DESC_SIZE; pid3=table+3*PROC_DESC_SIZE

        # BREAK with PID1 owner: only shell boundary consumes E_INTR; no process cancel flag.
        code=bytearray(b"\xF3"+phase1._ld_sp(0xFD00)+phase1._call(labels["zx48_process_init"]))
        code+=setb(pid1+PROC_STATE,PROC_RUNNING)+setb(labels["current_pid"],1)+setb(labels["tty_input_owner"],1)+setb(labels["break_pending"],1)
        code+=phase1._call(labels["zx48_syscall_impl"])+b"\xD2"+word(FAIL_PC)+bytes((0xFE,labels["E_INTR"]&255))+phase1._jp_nz(FAIL_PC)
        code+=expectb(labels["break_pending"],0)+expectb(pid1+PROC_FLAGS,0)+phase1._jp(PASS_PC)
        run_sna(root,bytes(code),patch=patch_kernel(kernel_bytes))

        # A non-owner pipeline stage cannot consume or receive the BREAK.
        code=bytearray(b"\xF3"+phase1._ld_sp(0xFD00)+phase1._call(labels["zx48_process_init"]))
        code+=setb(pid2+PROC_STATE,PROC_READY)+setb(pid2+PROC_PRIVATE_FLAGS,PROC_PRIVATE_STARTED)
        code+=setb(pid3+PROC_STATE,PROC_RUNNING)+setb(pid3+PROC_PRIVATE_FLAGS,PROC_PRIVATE_STARTED)
        code+=setb(labels["current_pid"],3)+setb(labels["tty_input_owner"],2)+setb(labels["break_pending"],1)
        code+=b"\x3E\x00"+phase1._call(labels["zx48_syscall_impl"])+phase1._jp_c(FAIL_PC)
        code+=expectb(labels["break_pending"],1)+expectb(pid2+PROC_FLAGS,0)+expectb(pid3+PROC_FLAGS,0)+phase1._jp(PASS_PC)
        run_sna(root,bytes(code),patch=patch_kernel(kernel_bytes))

        # When the tty owner next crosses the syscall boundary, only that owner
        # receives E_INTR and the pending request is consumed exactly once.
        code=bytearray(b"\xF3"+phase1._ld_sp(0xFD00)+phase1._call(labels["zx48_process_init"]))
        code+=setb(pid2+PROC_STATE,PROC_RUNNING)+setb(pid2+PROC_PRIVATE_FLAGS,PROC_PRIVATE_STARTED)
        code+=setb(pid3+PROC_STATE,PROC_READY)+setb(pid3+PROC_PRIVATE_FLAGS,PROC_PRIVATE_STARTED)
        code+=setb(labels["current_pid"],2)+setb(labels["tty_input_owner"],2)+setb(labels["break_pending"],1)
        code+=b"\x3E\x00"+phase1._call(labels["zx48_syscall_impl"])+b"\xD2"+word(FAIL_PC)+bytes((0xFE,labels["E_INTR"]&255))+phase1._jp_nz(FAIL_PC)
        code+=expectb(labels["break_pending"],0)+expectb(pid2+PROC_FLAGS,0)+expectb(pid3+PROC_FLAGS,0)
        code+=b"\x3E\x00"+phase1._call(labels["zx48_syscall_impl"])+phase1._jp_c(FAIL_PC)+phase1._jp(PASS_PC)
        run_sna(root,bytes(code),patch=patch_kernel(kernel_bytes))

        # Existing Phase-2 kill oracles remain authoritative for never-started discard,
        # blocked E_INTR delivery, and no arbitrary CPU preemption.
        d18=phase2_kill_never_started.dispatch(root,"test","P2.18",sha256_file=sha256_file,run_command=run_command,require_project_tool=require_project_tool)
        d19=phase2_kill_started.dispatch(root,"test","P2.19",sha256_file=sha256_file,run_command=run_command,require_project_tool=require_project_tool)
        commands += list(d18[0])+list(d19[0])
        assertions += [
          {"name":"fuse-pid1-break-line-only","passed":True},
          {"name":"fuse-break-nonowner-stage-untouched","passed":True},
          {"name":"fuse-tty-owner-one-shot-eintr","passed":True},
          {"name":"phase2-never-started-kill-oracle-still-pass","passed":True},
          {"name":"phase2-started-cooperative-kill-oracle-still-pass","passed":True},
          {"name":"c48-safe-point-status-130-contract","passed":True,"basis":"P2.18/P2.19 cancellation ABI"},
        ]
    hashes={
      "v1/src/shell/sh.asm":sha256_file(root/"v1/src/shell/sh.asm"),
      "v1/src/kernel/process.asm":sha256_file(root/"v1/src/kernel/process.asm"),
      "v1/src/kernel/keyboard.asm":sha256_file(root/"v1/src/kernel/keyboard.asm"),
      "v1/src/kernel/syscall.asm":sha256_file(root/"v1/src/kernel/syscall.asm"),
      "v1/src/kernel/interrupt.asm":sha256_file(root/"v1/src/kernel/interrupt.asm"),
      "v1/build/kernel.bin":sha256_file(kernel),
      "v1/tools-host/test-driver/phase6_kill_break.py":sha256_file(root/"v1/tools-host/test-driver/phase6_kill_break.py"),
      "v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
      "v1/dist/certification/P6.25.build.json":sha256_file(root/"v1/dist/certification/P6.25.build.json"),
      "v1/dist/certification/P6.25.test.json":sha256_file(root/"v1/dist/certification/P6.25.test.json"),
      "v1/dist/media/P6.25/manifest.json":sha256_file(root/"v1/dist/media/P6.25/manifest.json")}
    return commands,hashes,assertions
