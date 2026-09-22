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
import phase7_beep

CORE=0xC000
BRIDGE=0xD000
GATE=0xE000
DURATION=0xA000
PITCH=0xA010

class P718Error(DriverError): pass
def req(v,m):
    if not v: raise P718Error(m)
def w(v): return bytes((v&255,(v>>8)&255))
def call(a): return b"\xcd"+w(a)
def checkb(a,v): return b"\x3a"+w(a)+bytes((0xfe,v&255))+phase1._jp_nz(FAIL_PC)
def checkw(a,v): return b"\x2a"+w(a)+phase1._ld_de(v)+b"\xb7\xed\x52"+phase1._jp_nz(FAIL_PC)

def source(root):
    arch=(root/"docs/01-ZX-UX-ARCHITECTURE-REV16.md").read_text()
    plan=(root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md").read_text()
    return [
      {"name":"canonical-p718-present","passed":"## P7.18 - C48 beep ABI bridge fixture" in plan},
      {"name":"c48-regcall-first-second-slots-hl-de","passed":"first argument     HL" in arch and "second argument    DE" in arch},
      {"name":"float-arguments-are-pointer-slots","passed":"A C48 `float` argument is passed as a 16-bit pointer" in arch},
      {"name":"beep-public-return-contract","passed":"int beep(float duration, float pitch)" in arch and "positive ZX-UX errno" in arch},
    ]

def assemble(root,run_command,require_project_tool):
    asm=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus")
    b=root/"v1/build"; b.mkdir(parents=True,exist_ok=True)
    f=b/"p718-c48-beep.asm"
    f.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"

    ORG $C000
p718_core:
altreg_busy: db 0
ula_shadow: db 0
zx48_kernel_stack_sample: ret
zx48_kernel_stack_check: xor a : ret
zx48_ula_rom_prepare:
    push af
    ld a,1
    ld (altreg_busy),a
    pop af
    ret
zx48_ula_commit: ld (ula_shadow),a : ret
    INCLUDE "../src/kernel/syscall.asm"
    INCLUDE "../src/kernel/rom_services.asm"
    INCLUDE "../src/kernel/sound.asm"
    EMIT_USER_RANGE_VALIDATION_ROUTINE
    EMIT_ROM_SERVICE_ROUTINES
    EMIT_P709_ROM_BEEP_ROUTINES
    EMIT_SOUND_ROUTINES
    EMIT_P709_BEEP_SYSCALL_ROUTINES
p718_core_end:
    SAVEBIN "p718-core.bin",p718_core,p718_core_end-p718_core

    ORG $D000
c48_beep_bridge:
    ; C48_REGCALL: HL=duration float pointer, DE=pitch float pointer.
    ; No hidden result slot exists because the public return type is int.
    ld a,SYS_BEEP
    call SYSCALL_GATEWAY
    jr c,c48_beep_errno
    ld hl,0
    ret
c48_beep_errno:
    ld l,a
    ld h,0
    ret
p718_bridge_end:
    SAVEBIN "p718-bridge.bin",c48_beep_bridge,p718_bridge_end-c48_beep_bridge

    ORG $E000
p718_gateway:
    cp SYS_BEEP
    jr nz,p718_gateway_bad
    ld (p718_seen_hl),hl
    ld (p718_seen_de),de
    ld (p718_seen_bc),bc
    ld (syscall_arg_hl),hl
    ld (syscall_arg_de),de
    ld a,SYS_BEEP
    jp zx48_p709_beep_dispatch
p718_gateway_bad:
    ld a,E_NOTSUP
    scf
    ret
p718_seen_hl: dw 0
p718_seen_de: dw 0
p718_seen_bc: dw 0
p718_gateway_end:
    SAVEBIN "p718-gateway.bin",p718_gateway,p718_gateway_end-p718_gateway
""",encoding="utf-8",newline="\n")
    r=run_command([asm,"--nologo","--sym=p718-c48-beep.sym","p718-c48-beep.asm"],cwd=b,timeout_seconds=30)
    req(r.exit_code==0 and not r.timed_out,f"fixture assembly: {r.stderr or r.stdout}")
    return r,b/"p718-core.bin",b/"p718-bridge.bin",b/"p718-gateway.bin",b/"p718-c48-beep.sym"

def patch(core,bridge,gate,dur,pitch):
    def p(ram):
        ram[CORE-0x4000:CORE-0x4000+len(core)]=core
        ram[BRIDGE-0x4000:BRIDGE-0x4000+len(bridge)]=bridge
        ram[GATE-0x4000:GATE-0x4000+len(gate)]=gate
        ram[DURATION-0x4000:DURATION-0x4000+5]=dur
        ram[PITCH-0x4000:PITCH-0x4000+5]=pitch
    return p

def valid(root,s,core,bridge,gate):
    code=bytearray(b"\xf3"+phase1._ld_sp(phase1.USER_STACK)+phase1._ld_hl(DURATION)+phase1._ld_de(PITCH)+bytes((0x01,0xef,0xbe))+call(s["c48_beep_bridge"]))
    code+=bytes((0x7c,0xb5))+phase1._jp_nz(FAIL_PC)
    code+=checkw(s["p718_seen_hl"],DURATION)+checkw(s["p718_seen_de"],PITCH)+checkw(s["p718_seen_bc"],0xbeef)
    code+=checkb(s["altreg_busy"],0)+phase1._jp(PASS_PC)
    run_sna(root,bytes(code),patch=patch(core,bridge,gate,phase7_beep.FP_HALF,phase7_beep.FP_NINE),timeout=30)

def invalid_pointer(root,s,core,bridge,gate):
    code=bytearray(b"\xf3"+phase1._ld_sp(phase1.USER_STACK)+phase1._ld_hl(0xdffc)+phase1._ld_de(PITCH)+call(s["c48_beep_bridge"]))
    code+=phase1._ld_de(s["E_INVAL"])+b"\xb7\xed\x52"+phase1._jp_nz(FAIL_PC)
    code+=checkw(s["p718_seen_hl"],0xdffc)+checkw(s["p718_seen_de"],PITCH)+checkb(s["altreg_busy"],0)+phase1._jp(PASS_PC)
    run_sna(root,bytes(code),patch=patch(core,bridge,gate,phase7_beep.FP_ONE,phase7_beep.FP_ZERO),timeout=20)

def hidden_mismatch(root,s,core,bridge,gate):
    # Deliberately call as though an unsupported hidden result pointer occupied HL.
    code=bytearray(b"\xf3"+phase1._ld_sp(phase1.USER_STACK)+phase1._ld_hl(0)+phase1._ld_de(DURATION)+bytes((0x01,))+w(PITCH)+call(s["c48_beep_bridge"]))
    code+=phase1._ld_de(s["E_INVAL"])+b"\xb7\xed\x52"+phase1._jp_nz(FAIL_PC)
    code+=checkw(s["p718_seen_hl"],0)+checkw(s["p718_seen_de"],DURATION)+checkw(s["p718_seen_bc"],PITCH)+checkb(s["altreg_busy"],0)+phase1._jp(PASS_PC)
    run_sna(root,bytes(code),patch=patch(core,bridge,gate,phase7_beep.FP_ONE,phase7_beep.FP_ZERO),timeout=20)

def dispatch(root,action,step,*,sha256_file,run_command,require_project_tool):
    if step!="P7.18": raise P718Error(step)
    assertions=source(root); bad=[x["name"] for x in assertions if not x["passed"]]; req(not bad,f"static: {bad}")
    kc,kernel,_=phase1._assemble_kernel(root,run_command,require_project_tool)
    fr,core,bridge,gate,sym=assemble(root,run_command,require_project_tool)
    names=("c48_beep_bridge","p718_seen_hl","p718_seen_de","p718_seen_bc","altreg_busy","E_INVAL")
    s=phase3_open_descriptions._symbols(sym,names)
    if action=="test":
        valid(root,s,core.read_bytes(),bridge.read_bytes(),gate.read_bytes())
        invalid_pointer(root,s,core.read_bytes(),bridge.read_bytes(),gate.read_bytes())
        hidden_mismatch(root,s,core.read_bytes(),bridge.read_bytes(),gate.read_bytes())
        assertions += [
          {"name":"fuse-c48-regcall-float-pointers-reach-sys-beep-exact","passed":True},
          {"name":"fuse-success-maps-to-int-zero","passed":True},
          {"name":"fuse-syscall-error-maps-to-positive-errno","passed":True},
          {"name":"fuse-hidden-result-pointer-convention-mismatch-fails","passed":True},
        ]
    hashes={str(x.relative_to(root)):sha256_file(x) for x in (
      root/"v1/src/kernel/sound.asm",root/"v1/src/kernel/rom_services.asm",root/"v1/src/kernel/syscall.asm",
      root/"v1/tools-host/test-driver/phase7_c48_beep.py",root/"v1/tools-host/test-driver/run.py",kernel)}
    return [kc,fr],hashes,assertions
