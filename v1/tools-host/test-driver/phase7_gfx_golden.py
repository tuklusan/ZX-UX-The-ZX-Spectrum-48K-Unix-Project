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

MODULE=0xC000
BANK=0x7000
PATTERN=0xA100
RECORD=0xA120
SCREEN_SUM=0x0342
ATTR=0x62
CANARIES=(0x6000,0x6fff,0x7100,0x7fff,0xa300,0xb100)

class P719Error(DriverError): pass
def req(v,m):
    if not v: raise P719Error(m)
def w(v): return bytes((v&255,(v>>8)&255))
def call(a): return b"\xcd"+w(a)
def jpc(a): return b"\xda"+w(a)
def jpnc(a): return b"\xd2"+w(a)
def checkb(a,v): return b"\x3a"+w(a)+bytes((0xfe,v&255))+phase1._jp_nz(FAIL_PC)
def checkw(a,v): return b"\x2a"+w(a)+phase1._ld_de(v)+b"\xb7\xed\x52"+phase1._jp_nz(FAIL_PC)

def bitmap_addr(y,col):
    return 0x4000 | ((y&7)<<8) | ((y&0xc0)<<5) | ((y&0x38)<<2) | col

def source(root):
    plan=(root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md").read_text()
    gfx=(root/"v1/src/kernel/graphics.asm").read_text()
    udg=(root/"v1/src/kernel/udg.asm").read_text()
    snd=(root/"v1/src/kernel/sound.asm").read_text()
    rom=(root/"v1/src/kernel/rom_services.asm").read_text()
    return [
      {"name":"canonical-p719-present","passed":"## P7.19 - GFX golden program" in plan},
      {"name":"golden-uses-production-graphics-routines","passed":"MACRO EMIT_GRAPHICS_ROUTINES" in gfx and "zx48_gfx_plot:" in gfx and "zx48_gfx_attr:" in gfx},
      {"name":"golden-uses-production-udg-routines","passed":"MACRO EMIT_UDG_ROUTINES" in udg and "zx48_udg_draw:" in udg and "ld (ROM_UDG),hl" in udg},
      {"name":"golden-uses-production-sound-rom-gateway","passed":"call zx48_rom_beep_values" in snd and "ROM_BEEP_COMMAND" in rom},
      {"name":"screen-domain-frozen","passed":"BITMAP_START" in (root/"v1/include/zx48ux.inc").read_text() and "ATTR_END" in (root/"v1/include/zx48ux.inc").read_text()},
      {"name":"udg-bank-is-256-bytes","passed":"UDG_BANK_SIZE" in (root/"v1/include/zx48ux.inc").read_text() and "UDG_SLOT_COUNT           EQU 32" in udg},
    ]

def assemble(root,run_command,require_project_tool):
    asm=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus")
    b=root/"v1/build"; b.mkdir(parents=True,exist_ok=True)
    f=b/"p719-golden.asm"
    f.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/kernel/graphics.asm"
    INCLUDE "../src/kernel/udg.asm"
    INCLUDE "../src/kernel/rom_services.asm"
    INCLUDE "../src/kernel/sound.asm"

    ORG $C000
p719_start:
altreg_busy: db 0
ula_shadow: db 3
tty_current_attr: db 7
p719_pin_calls: db 0

zx48_kernel_stack_sample: ret
zx48_kernel_stack_check: xor a : ret
zx48_cursor_hide: ret
zx48_cursor_show: ret
zx48_ula_set_border:
    ld a,l
    and 7
    ld (ula_shadow),a
    xor a
    ret
zx48_ula_rom_prepare:
    push af
    ld a,1
    ld (altreg_busy),a
    pop af
    ret
zx48_ula_commit: ld (ula_shadow),a : ret
zx48_alloc:
    ld hl,$7000
    xor a
    ret
zx48_memory_pin_bytes:
    ld a,(p719_pin_calls)
    inc a
    ld (p719_pin_calls),a
    xor a
    ret
zx48_memcpy: ldir : ret

zx48_bitmap_address:
    ld a,b
    and 7
    or $40
    ld h,a
    ld a,b
    and $c0
    rrca
    rrca
    rrca
    or h
    ld h,a
    ld a,b
    and $38
    rlca
    rlca
    or c
    ld l,a
    ret

p719_screen_sum:
    ld hl,$4000
    ld de,0
    ld bc,$1b00
p719_sum_loop:
    ld a,(hl)
    add a,e
    ld e,a
    jr nc,p719_sum_nocarry
    inc d
p719_sum_nocarry:
    inc hl
    dec bc
    ld a,b
    or c
    jr nz,p719_sum_loop
    ex de,hl
    ret

p719_guard_check:
    ld a,($6000)
    cp $a5
    jr nz,p719_guard_bad
    ld a,($6fff)
    cp $a5
    jr nz,p719_guard_bad
    ld a,($7100)
    cp $a5
    jr nz,p719_guard_bad
    ld a,($7fff)
    cp $a5
    jr nz,p719_guard_bad
    ld a,($a300)
    cp $a5
    jr nz,p719_guard_bad
    ld a,($b100)
    cp $a5
    jr nz,p719_guard_bad
    xor a
    ret
p719_guard_bad:
    ld a,E_IO
    scf
    ret

    EMIT_GRAPHICS_ROUTINES
    EMIT_UDG_ROUTINES
    EMIT_ROM_SERVICE_ROUTINES
    EMIT_P709_ROM_BEEP_ROUTINES
    EMIT_SOUND_ROUTINES
p719_end:
    SAVEBIN "p719-golden.bin",p719_start,p719_end-p719_start
""",encoding="utf-8",newline="\n")
    r=run_command([asm,"--nologo","--sym=p719-golden.sym","p719-golden.asm"],cwd=b,timeout_seconds=30)
    req(r.exit_code==0 and not r.timed_out,f"P7.19 assembly: {r.stderr or r.stdout}")
    binary=b/"p719-golden.bin"
    req(binary.is_file() and 0<binary.stat().st_size<8192,"P7.19 golden fixture missing/oversize")
    return r,binary,b/"p719-golden.sym"

def patch(module,s,corrupt_guard=False):
    pattern=bytes((0x81,0x42,0x24,0x18,0x18,0x24,0x42,0x81))
    def p(ram):
        ram[MODULE-0x4000:MODULE-0x4000+len(module)]=module
        ram[PATTERN-0x4000:PATTERN-0x4000+8]=pattern
        ram[RECORD-0x4000:RECORD-0x4000+3]=bytes((3,1,2))
        for a in CANARIES: ram[a-0x4000]=0xa5
        if corrupt_guard: ram[CANARIES[2]-0x4000]=0xa4
        ram[0xA140-0x4000:0xA145-0x4000]=phase7_beep.FP_QUARTER
        ram[0xA150-0x4000:0xA155-0x4000]=phase7_beep.FP_ZERO
    return p

def positive(root,s,module):
    code=bytearray(b"\xf3"+phase1._ld_sp(0xBFC0))
    code+=call(s["zx48_udg_init"])+jpc(FAIL_PC)
    code+=checkw(0x5c7b,BANK)+checkb(s["p719_pin_calls"],1)

    for sel,val in ((0,2),(1,4),(2,1)):
        code+=phase1._ld_hl((sel<<8)|val)+call(s["zx48_gfx_attr"])+jpc(FAIL_PC)
    code+=checkb(s["tty_current_attr"],ATTR)

    code+=phase1._ld_hl(0)+call(s["zx48_gfx_plot"])+jpc(FAIL_PC)

    code+=phase1._ld_hl(PATTERN)+bytes((0x01,3,0))+call(s["zx48_udg_define"])+jpc(FAIL_PC)
    code+=phase1._ld_hl(RECORD)+call(s["zx48_udg_draw"])+jpc(FAIL_PC)

    code+=phase1._ld_hl(0xA140)+phase1._ld_de(0xA150)+call(s["zx48_sound_beep"])+jpc(FAIL_PC)
    code+=checkb(s["altreg_busy"],0)+checkb(s["ula_shadow"],3)

    code+=call(s["p719_screen_sum"])+phase1._ld_de(SCREEN_SUM)+b"\xb7\xed\x52"+phase1._jp_nz(FAIL_PC)
    code+=checkb(0x4000,0x80)+checkb(0x5800,ATTR)
    pattern=bytes((0x81,0x42,0x24,0x18,0x18,0x24,0x42,0x81))
    for i,v in enumerate(pattern):
        code+=checkb(BANK+3*8+i,v)
        code+=checkb(bitmap_addr(8+i,2),v)
    code+=checkb(0x5800+1*32+2,ATTR)
    code+=checkb(BANK,0)+checkb(BANK+255,0)
    code+=checkw(0x5c7b,BANK)
    code+=call(s["p719_guard_check"])+jpc(FAIL_PC)

    code+=b"\xfd\xe5\xe1"+phase1._ld_de(0x5c3a)+b"\xb7\xed\x52"+phase1._jp_nz(FAIL_PC)
    code+=phase1._jp(PASS_PC)
    run_sna(root,bytes(code),patch=patch(module,s),timeout=30)

def negative_guard(root,s,module):
    code=bytearray(b"\xf3"+phase1._ld_sp(0xBFC0)+call(s["p719_guard_check"])+jpnc(FAIL_PC))
    code+=bytes((0xfe,s["E_IO"]&255))+phase1._jp_nz(FAIL_PC)+phase1._jp(PASS_PC)
    run_sna(root,bytes(code),patch=patch(module,s,True),timeout=20)

def dispatch(root,action,step,*,sha256_file,run_command,require_project_tool):
    if step!="P7.19": raise P719Error(step)
    assertions=source(root); bad=[x["name"] for x in assertions if not x["passed"]]; req(not bad,f"static: {bad}")
    kc,kernel,_=phase1._assemble_kernel(root,run_command,require_project_tool)
    fr,binary,sym=assemble(root,run_command,require_project_tool)
    names=("zx48_udg_init","zx48_udg_define","zx48_udg_draw","zx48_gfx_attr","zx48_gfx_plot","zx48_sound_beep",
           "p719_screen_sum","p719_guard_check","p719_pin_calls","tty_current_attr","altreg_busy","ula_shadow","E_IO")
    s=phase3_open_descriptions._symbols(sym,names)
    if action=="test":
        module=binary.read_bytes()
        positive(root,s,module)
        negative_guard(root,s,module)
        assertions += [
          {"name":"fuse-integrated-gfx-udg-sound-golden-passes","passed":True},
          {"name":"fuse-screen-sum-and-exact-touched-bytes-match","passed":True},
          {"name":"fuse-attribute-cells-and-udg-bank-bytes-exact","passed":True},
          {"name":"fuse-rom-udg-pointer-and-iy-exact","passed":True},
          {"name":"fuse-guard-canaries-survive-approved-writes","passed":True},
          {"name":"fuse-negative-guard-corruption-detected","passed":True},
        ]
    hashes={str(x.relative_to(root)):sha256_file(x) for x in (
      root/"v1/src/kernel/graphics.asm",root/"v1/src/kernel/udg.asm",root/"v1/src/kernel/sound.asm",
      root/"v1/src/kernel/rom_services.asm",root/"v1/tools-host/test-driver/phase7_gfx_golden.py",
      root/"v1/tools-host/test-driver/run.py",kernel)}
    return [kc,fr],hashes,assertions
