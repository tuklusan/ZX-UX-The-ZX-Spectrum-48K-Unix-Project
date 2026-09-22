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
import phase1
import phase3_open_descriptions

MODULE=0xC000
DURATION=0xA000
PITCH=0xA010

class P718Error(DriverError): pass
def req(v,m):
    if not v: raise P718Error(m)
def w(v): return bytes((v&255,(v>>8)&255))
def call(a): return b"\xcd"+w(a)
def jpnc(a): return b"\xd2"+w(a)
def checkb(a,v): return b"\x3a"+w(a)+bytes((0xfe,v&255))+phase1._jp_nz(FAIL_PC)
def checkw(a,v): return b"\x2a"+w(a)+phase1._ld_de(v)+b"\xb7\xed\x52"+phase1._jp_nz(FAIL_PC)

def source(root):
    arch=(root/"docs/01-ZX-UX-ARCHITECTURE-REV16.md").read_text()
    plan=(root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md").read_text()
    syscall=(root/"v1/src/kernel/syscall.asm").read_text()
    return [
      {"name":"canonical-p718-present","passed":"## P7.18 - C48 beep ABI bridge fixture" in plan},
      {"name":"c48-beep-signature-frozen","passed":"int beep(float duration, float pitch)" in arch},
      {"name":"c48-regcall-float-pointer-contract-frozen","passed":"A C48 `float` argument is passed as a 16-bit pointer" in arch and "first argument     HL" in arch and "second argument    DE" in arch},
      {"name":"beep-shares-sys-beep-service","passed":"SYS_BEEP" in syscall and "zx48_p709_beep_dispatch" in syscall},
      {"name":"kernel-validates-both-five-byte-pointer-ranges","passed":syscall.count("ld bc,5\n    call zx48_user_range_validate")>=2},
      {"name":"kernel-forwards-exact-hl-de-pointers-to-sound","passed":"ld hl,(syscall_arg_hl)\n    ld de,(syscall_arg_de)\n    jp zx48_sound_beep" in syscall},
    ]

def assemble(root,run_command,require_project_tool):
    asm=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus")
    b=root/"v1/build"; b.mkdir(parents=True,exist_ok=True)
    f=b/"p718-c48-beep.asm"
    f.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/kernel/syscall.asm"

    ORG $C000
p718_bridge_start:
p718_c48_beep:
    ld a,SYS_BEEP
    call SYSCALL_GATEWAY
    jr c,p718_c48_beep_error
    ld hl,0
    ret
p718_c48_beep_error:
    ld l,a
    ld h,0
    ret
p718_bridge_end:

    ORG $E000
p718_gateway:
    ld (p718_last_sys),a
    ld (syscall_arg_hl),hl
    ld (syscall_arg_de),de
    call zx48_p709_beep_dispatch
    ret

zx48_sound_beep:
    ld (p718_seen_hl),hl
    ld (p718_seen_de),de
    ld a,(p718_sound_calls)
    inc a
    ld (p718_sound_calls),a
    ld a,(p718_mode)
    or a
    jr nz,p718_sound_error
    xor a
    ret
p718_sound_error:
    ld a,E_IO
    scf
    ret

    EMIT_USER_RANGE_VALIDATION_ROUTINE
    EMIT_P709_BEEP_SYSCALL_ROUTINES

p718_mode: db 0
p718_last_sys: db $ff
p718_sound_calls: db 0
p718_seen_hl: dw 0
p718_seen_de: dw 0
p718_gateway_end:
    SAVEBIN "p718-c48-beep.bin",p718_bridge_start,p718_bridge_end-p718_bridge_start
    SAVEBIN "p718-gateway.bin",p718_gateway,p718_gateway_end-p718_gateway
""",encoding="utf-8",newline="\n")
    r=run_command([asm,"--nologo","--sym=p718-c48-beep.sym","p718-c48-beep.asm"],cwd=b,timeout_seconds=30)
    req(r.exit_code==0 and not r.timed_out,f"P7.18 fixture assembly: {r.stderr or r.stdout}")
    return r,b/"p718-c48-beep.bin",b/"p718-gateway.bin",b/"p718-c48-beep.sym"

def patch(bridge,gateway,s,mode=0):
    def p(ram):
        ram[MODULE-0x4000:MODULE-0x4000+len(bridge)]=bridge
        ram[0xE000-0x4000:0xE000-0x4000+len(gateway)]=gateway
        ram[DURATION-0x4000:DURATION-0x4000+5]=bytes((0x80,0,0,0,0))
        ram[PITCH-0x4000:PITCH-0x4000+5]=bytes((0,0,9,0,0))
        ram[s["p718_mode"]-0x4000]=mode
    return p

def positive(root,s,bridge,gateway,mode=0):
    code=bytearray(b"\xf3"+phase1._ld_sp(0xBFC0)+phase1._ld_hl(DURATION)+phase1._ld_de(PITCH)+call(s["p718_c48_beep"]))
    expected=0 if mode==0 else s["E_IO"]
    code+=phase1._ld_de(expected)+b"\xb7\xed\x52"+phase1._jp_nz(FAIL_PC)
    code+=checkb(s["p718_last_sys"],s["SYS_BEEP"])+checkb(s["p718_sound_calls"],1)
    code+=checkw(s["p718_seen_hl"],DURATION)+checkw(s["p718_seen_de"],PITCH)+phase1._jp(PASS_PC)
    run_sna(root,bytes(code),patch=patch(bridge,gateway,s,mode))

def mismatch(root,s,bridge,gateway,bad_hl=True):
    hl=0x0080 if bad_hl else DURATION
    de=PITCH if bad_hl else 0x0009
    code=bytearray(b"\xf3"+phase1._ld_sp(0xBFC0)+phase1._ld_hl(hl)+phase1._ld_de(de)+call(s["p718_c48_beep"]))
    code+=phase1._ld_de(s["E_INVAL"])+b"\xb7\xed\x52"+phase1._jp_nz(FAIL_PC)
    code+=checkb(s["p718_last_sys"],s["SYS_BEEP"])+checkb(s["p718_sound_calls"],0)+phase1._jp(PASS_PC)
    run_sna(root,bytes(code),patch=patch(bridge,gateway,s,0))

def dispatch(root,action,step,*,sha256_file,run_command,require_project_tool):
    if step!="P7.18": raise P718Error(step)
    assertions=source(root); bad=[x["name"] for x in assertions if not x["passed"]]; req(not bad,f"static: {bad}")
    kc,kernel,_=phase1._assemble_kernel(root,run_command,require_project_tool)
    fc,bb,gb,sym=assemble(root,run_command,require_project_tool)
    names=("p718_c48_beep","p718_mode","p718_last_sys","p718_sound_calls","p718_seen_hl","p718_seen_de","SYS_BEEP","E_IO","E_INVAL")
    s=phase3_open_descriptions._symbols(sym,names)
    if action=="test":
        bridge=bb.read_bytes(); gateway=gb.read_bytes()
        positive(root,s,bridge,gateway,0)
        positive(root,s,bridge,gateway,1)
        mismatch(root,s,bridge,gateway,True)
        mismatch(root,s,bridge,gateway,False)
        assertions += [
          {"name":"fuse-c48-regcall-hl-de-float-pointers-reach-sys-beep-exact","passed":True},
          {"name":"fuse-c48-success-maps-to-int-zero","passed":True},
          {"name":"fuse-c48-kernel-errno-maps-to-positive-int","passed":True},
          {"name":"fuse-nonpointer-register-convention-rejected-before-sound","passed":True},
        ]
    hashes={str(x.relative_to(root)):sha256_file(x) for x in (
      root/"v1/src/kernel/syscall.asm",root/"v1/tools-host/test-driver/phase7_beep_c48.py",
      root/"v1/tools-host/test-driver/run.py",kernel)}
    return [kc,fc],hashes,assertions
