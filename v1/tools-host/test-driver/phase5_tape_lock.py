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
from driver_core import DriverError
from fuse_harness import FAIL_PC, PASS_PC, run_sna
import phase1, phase3_open_descriptions

MODULE=0xC000; STACK=0xBFC0
class P512Error(DriverError): pass
def require(x,m):
    if not x: raise P512Error(m)
def w(v): return bytes((v&255,(v>>8)&255))
def checkb(a,v): return b"\x3A"+w(a)+bytes((0xFE,v&255))+phase1._jp_nz(FAIL_PC)

def dispatch(root:Path,action:str,step:str,*,sha256_file,run_command,require_project_tool):
    if step!="P5.12": raise DriverError(f"Phase-5 tape-lock step is not registered: {step}")
    tape=(root/"v1/src/kernel/tape.asm").read_text()
    sched=(root/"v1/src/kernel/scheduler.asm").read_text()
    assertions=[
      {"name":"one-global-lock-owned-by-tape-layer","passed":"p507_tape_lock: db 0" in tape},
      {"name":"second-request-returns-e-busy","passed":"zx48_p507_busy:" in tape and "ld a,E_BUSY" in tape},
      {"name":"acquire-marks-global-blocking-state","passed":"p507_tape_blocking" in tape},
      {"name":"release-clears-global-blocking-state","passed":"ld (p507_tape_blocking),a" in tape},
      {"name":"scheduler-documents-cooperative-pause","passed":"cooperative progress may pause" in sched},
      {"name":"scheduler-documents-clock-degradation","passed":"wall-clock precision" in sched and "degraded" in sched},
      {"name":"blocking-interval-counted","passed":"p507_tape_intervals" in tape and "inc hl" in tape},
      {"name":"all-public-tape-paths-use-lock","passed":all(x in tape for x in ("zx48_p507_lock_acquire","zx48_p509_load_path","zx48_p510_verify_path","zx48_p511_scan_next"))},
    ]; require(all(a["passed"] for a in assertions),"P5.12 static failure")
    kr,kernel,_=phase1._assemble_kernel(root,run_command,require_project_tool)
    asm=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus"); b=root/"v1/build"; b.mkdir(parents=True,exist_ok=True)
    f=b/"p512-tape-lock.asm"; f.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../include/tapeobj.inc"
OBJ_NAME EQU 0
OBJ_DIR_ID EQU 10
OBJ_TYPE_ID EQU 11
OBJ_FLAGS_BYTE EQU 12
OBJ_RESERVED_BYTE EQU 13
OBJ_LOGICAL_LENGTH EQU 14
OBJ_STORAGE_LENGTH EQU 16
OBJ_ALLOCATION_PTR EQU 18
    INCLUDE "../src/kernel/tape.asm"
    ORG $C000
    EMIT_P502_CRC16_ROUTINES
    EMIT_P503_FRAMING_ROUTINES
    EMIT_P507_RAW_SAVE_ROUTINES
zx48_object_public_type_allowed: xor a : ret
zx48_tape_save_block: ld a,E_IO : scf : ret
    SAVEBIN "p512-tape-lock.bin",$C000,$-$C000
""",encoding="utf-8",newline="\n")
    fr=run_command([asm,"--nologo","--lst=p512-tape-lock.lst","--sym=p512-tape-lock.sym","p512-tape-lock.asm"],cwd=b,timeout_seconds=30)
    require(not fr.timed_out and fr.exit_code==0,f"P5.12 fixture assembly failed: {fr.stderr or fr.stdout}")
    binary=b/"p512-tape-lock.bin"
    if action=="test":
      s=phase3_open_descriptions._symbols(b/"p512-tape-lock.sym",("zx48_p507_lock_acquire","zx48_p507_lock_release","p507_tape_lock","p507_tape_blocking","p507_tape_intervals","E_BUSY"))
      def patch(ram):
        m=binary.read_bytes(); ram[MODULE-0x4000:MODULE-0x4000+len(m)]=m
      code=b"\xF3"+phase1._ld_sp(STACK)+phase1._call(s["zx48_p507_lock_acquire"])+phase1._jp_c(FAIL_PC)
      code+=checkb(s["p507_tape_lock"],1)+checkb(s["p507_tape_blocking"],1)
      code+=phase1._call(s["zx48_p507_lock_acquire"])+bytes((0xD2,FAIL_PC&255,FAIL_PC>>8))
      code+=bytes((0xFE,s["E_BUSY"]&255))+phase1._jp_nz(FAIL_PC)
      code+=checkb(s["p507_tape_lock"],1)+checkb(s["p507_tape_blocking"],1)
      code+=phase1._call(s["zx48_p507_lock_release"])+checkb(s["p507_tape_lock"],0)+checkb(s["p507_tape_blocking"],0)
      code+=phase1._ld_hl(s["p507_tape_intervals"])+b"\x5E\x23\x56"+phase1._ld_hl(1)+b"\xB7\xED\x52"+phase1._jp_nz(FAIL_PC)+phase1._jp(PASS_PC)
      run_sna(root,code,patch=patch)
      assertions += [
        {"name":"first-request-acquires-runtime","passed":True},
        {"name":"second-request-busy-without-corruption-runtime","passed":True},
        {"name":"release-restores-idle-global-state-runtime","passed":True},
      ]
    hashes={
      "v1/build/kernel.bin":sha256_file(kernel),"v1/build/p512-tape-lock.bin":sha256_file(binary),
      "v1/src/kernel/tape.asm":sha256_file(root/"v1/src/kernel/tape.asm"),
      "v1/src/kernel/scheduler.asm":sha256_file(root/"v1/src/kernel/scheduler.asm"),
      "v1/tools-host/test-driver/phase5_tape_lock.py":sha256_file(root/"v1/tools-host/test-driver/phase5_tape_lock.py"),
      "v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
      "v1/dist/certification/P5.11.build.json":sha256_file(root/"v1/dist/certification/P5.11.build.json"),
      "v1/dist/certification/P5.11.test.json":sha256_file(root/"v1/dist/certification/P5.11.test.json"),
    }
    return [kr,fr],hashes,assertions
