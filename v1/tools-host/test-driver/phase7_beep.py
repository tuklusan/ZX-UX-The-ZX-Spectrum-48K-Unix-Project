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

MODULE=0xC000
DURATION=0xA000
PITCH=0xA010
E_INVAL=0x01

FP_ZERO=bytes((0,0,0,0,0))
FP_ONE=bytes((0x81,0,0,0,0))
FP_HALF=bytes((0x80,0,0,0,0))
FP_QUARTER=bytes((0x7f,0,0,0,0))
FP_NINE=bytes((0,0,9,0,0))
FP_NEG12=bytes((0,0xff,0xf4,0xff,0))
FP_HALF_PITCH=FP_HALF

class P709Error(DriverError): pass

def require(v:bool,m:str)->None:
    if not v: raise P709Error(m)

def _word(v:int)->bytes: return bytes((v&255,(v>>8)&255))
def _jp_c(a:int)->bytes: return b"\xda"+_word(a)
def _jp_nc(a:int)->bytes: return b"\xd2"+_word(a)
def _expectb(a:int,v:int)->bytes: return b"\x3a"+_word(a)+bytes((0xfe,v&255))+phase1._jp_nz(FAIL_PC)

def _source(root:Path):
    sound=(root/"v1/src/kernel/sound.asm").read_text(encoding="utf-8")
    rom=(root/"v1/src/kernel/rom_services.asm").read_text(encoding="utf-8")
    syscall=(root/"v1/src/kernel/syscall.asm").read_text(encoding="utf-8")
    plan=(root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md").read_text(encoding="utf-8")
    return [
      {"name":"canonical-p709-present","passed":"## P7.09 - SYS_BEEP five-byte operands" in plan},
      {"name":"sound-delegates-to-isolated-rom-beep-gateway","passed":"call zx48_rom_beep_values" in sound},
      {"name":"rom-beep-command-address-frozen","passed":"ROM_BEEP_COMMAND          EQU $03F8" in rom},
      {"name":"complete-duration-and-pitch-ranges-validated","passed":syscall.count("ld bc,5\n    call zx48_user_range_validate")>=2},
      {"name":"both-ranges-validated-before-sound-entry","passed":syscall.index("ld bc,5\n    call zx48_user_range_validate")<syscall.index("jp zx48_sound_beep")},
      {"name":"calculator-stack-is-private-protected-workspace","passed":"ROM_BEEP_STACK            EQU $5D00" in rom and "ld (ROM_STKEND),hl" in rom},
      {"name":"rom-errors-return-einval-not-basic","passed":"zx48_rom_beep_error:" in rom and "ld a,E_INVAL\n    scf\n    ret" in rom},
      {"name":"error-gateway-restores-rom-system-pointers","passed":all(t in rom for t in ("rom_beep_saved_err_sp","rom_beep_saved_stkbot","rom_beep_saved_stkend","rom_beep_saved_mem"))},
      {"name":"synchronous-ula-critical-section-is-serialized","passed":"call zx48_ula_rom_prepare" in rom and "ld (altreg_busy),a" in rom},
      {"name":"no-tick-backfill-path-in-beep","passed":"tick" not in sound.lower() and "wall" not in sound.lower()},
    ]

def _assemble(root:Path,run_command:Callable[...,Any],require_project_tool:Callable[[Path,str|Path],Path]):
    asm=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus")
    build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    src=build/"p709-beep.asm"; binary=build/"p709-beep.bin"; sym=build/"p709-beep.sym"
    src.write_text(
      "    DEVICE ZXSPECTRUM48\n"
      "    INCLUDE \"../include/zx48ux.inc\"\n"
      f"    ORG ${MODULE:04X}\n"
      "p709_start:\n"
      "altreg_busy: db 0\n"
      "ula_shadow: db 0\n"
      "zx48_kernel_stack_sample: ret\n"
      "zx48_kernel_stack_check: xor a : ret\n"
      "zx48_ula_rom_prepare:\n"
      "    push af\n    ld a,1\n    ld (altreg_busy),a\n    pop af\n    ret\n"
      "zx48_ula_commit: ld (ula_shadow),a : ret\n"
      "    INCLUDE \"../src/kernel/syscall.asm\"\n"
      "    INCLUDE \"../src/kernel/rom_services.asm\"\n"
      "    INCLUDE \"../src/kernel/sound.asm\"\n"
      "    EMIT_USER_RANGE_VALIDATION_ROUTINE\n"
      "    EMIT_ROM_SERVICE_ROUTINES\n"
      "    EMIT_SOUND_ROUTINES\n"
      "    EMIT_P709_BEEP_SYSCALL_ROUTINES\n"
      "p709_end:\n"
      "    SAVEBIN \"p709-beep.bin\",p709_start,p709_end-p709_start\n",
      encoding="utf-8",newline="\n")
    r=run_command([asm,"--nologo","--lst=p709-beep.lst","--sym=p709-beep.sym","p709-beep.asm"],cwd=build,timeout_seconds=30.0)
    require(not r.timed_out and r.exit_code==0,f"P7.09 fixture assembly failed: {r.stderr or r.stdout}")
    require(binary.is_file() and 0<binary.stat().st_size<8192,"P7.09 fixture missing/oversize")
    return r,binary,sym

def _call(s:dict[str,int])->bytes:
    return phase1._ld_hl(DURATION)+b"\x22"+_word(s["syscall_arg_hl"])+phase1._ld_de(PITCH)+b"\xed\x53"+_word(s["syscall_arg_de"])+bytes((0x3e,s["SYS_BEEP"]&255))+phase1._call(s["zx48_p709_beep_dispatch"])

def _patch(module:bytes,d:bytes,p:bytes):
    def apply(ram:bytearray):
        ram[MODULE-0x4000:MODULE-0x4000+len(module)]=module
        ram[DURATION-0x4000:DURATION-0x4000+5]=d
        ram[PITCH-0x4000:PITCH-0x4000+5]=p
    return apply

def _run_vector(root:Path,s:dict[str,int],module:bytes,d:bytes,p:bytes):
    code=bytearray(b"\xf3"+phase1._ld_sp(phase1.USER_STACK))
    code+=_call(s)+_jp_c(FAIL_PC)+b"\xb7"+phase1._jp_nz(FAIL_PC)
    code+=_expectb(s["altreg_busy"],0)+phase1._jp(PASS_PC)
    run_sna(root,bytes(code),patch=_patch(module,d,p),timeout=30.0)

def _run_invalid_pointer(root:Path,s:dict[str,int],module:bytes):
    code=bytearray(b"\xf3"+phase1._ld_sp(phase1.USER_STACK))
    code+=phase1._ld_hl(0xdffc)+b"\x22"+_word(s["syscall_arg_hl"])+phase1._ld_de(PITCH)+b"\xed\x53"+_word(s["syscall_arg_de"])
    code+=bytes((0x3e,s["SYS_BEEP"]&255))+phase1._call(s["zx48_p709_beep_dispatch"])
    code+=_jp_nc(FAIL_PC)+bytes((0xfe,E_INVAL))+phase1._jp_nz(FAIL_PC)
    code+=_expectb(s["altreg_busy"],0)+phase1._jp(PASS_PC)
    run_sna(root,bytes(code),patch=_patch(module,FP_ONE,FP_ZERO),timeout=20.0)

def dispatch(root:Path,action:str,step:str,*,sha256_file,run_command,require_project_tool):
    if step!="P7.09": raise P709Error(f"unsupported {step} {action}")
    assertions=_source(root); failed=[x["name"] for x in assertions if x.get("passed") is not True]
    require(not failed,f"P7.09 static failure: {failed}")
    kc,kernel,_=phase1._assemble_kernel(root,run_command,require_project_tool)
    fc,binary,sym=_assemble(root,run_command,require_project_tool)
    names=("zx48_p709_beep_dispatch","syscall_arg_hl","syscall_arg_de","SYS_BEEP","altreg_busy")
    symbols=phase3_open_descriptions._symbols(sym,names)
    if action=="test":
        module=binary.read_bytes()
        for d,p in ((FP_ONE,FP_ZERO),(FP_HALF,FP_NINE),(FP_QUARTER,FP_NEG12),(FP_HALF,FP_HALF_PITCH)):
            _run_vector(root,symbols,module,d,p)
        _run_invalid_pointer(root,symbols,module)
        assertions += [
          {"name":"fuse-beep-1-0-completes-synchronously","passed":True},
          {"name":"fuse-beep-half-9-completes-synchronously","passed":True},
          {"name":"fuse-beep-quarter-minus12-completes-synchronously","passed":True},
          {"name":"fuse-beep-half-halfpitch-completes-synchronously","passed":True},
          {"name":"fuse-invalid-complete-pointer-range-rejected-before-rom","passed":True},
          {"name":"accepted-frame-tick-backfill-absent-by-construction","passed":True},
        ]
    hashes={
      "v1/build/kernel.bin":sha256_file(kernel),
      "v1/build/p709-beep.bin":sha256_file(binary),
      "v1/src/kernel/sound.asm":sha256_file(root/"v1/src/kernel/sound.asm"),
      "v1/src/kernel/rom_services.asm":sha256_file(root/"v1/src/kernel/rom_services.asm"),
      "v1/src/kernel/syscall.asm":sha256_file(root/"v1/src/kernel/syscall.asm"),
      "v1/tools-host/test-driver/phase7_beep.py":sha256_file(root/"v1/tools-host/test-driver/phase7_beep.py"),
      "v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
    }
    return [kc,fc],hashes,assertions
