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
import re
import phase1
import phase3_open_descriptions
from driver_core import DriverError
from fuse_harness import FAIL_PC, PASS_PC, run_sna

class P1125Error(DriverError):
    pass

def require(ok, message):
    if not ok:
        raise P1125Error(message)

def dispatch(root, action, step, *, sha256_file, run_command, require_project_tool):
    if step != "P11.25":
        raise DriverError(step)
    graphics=root/"v1/src/libc48/graphics.asm"; udg=root/"v1/src/libc48/udg.asm"
    g=graphics.read_text(); u=udg.read_text()
    plan=(root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV08.md").read_text()
    arch=(root/"docs/01-ZX-UX-ARCHITECTURE-REV17.md").read_text()
    names=("cls","print_at","plot","point","draw","circle","ink","paper","bright","flash",
           "inverse","over","border","udg_define","udg_get","udg_draw","udg_clear","udg_draw_2x2")
    require("EMIT_P1125_C48_GRAPHICS_RUNTIME" in g and "EMIT_P1125_C48_UDG_RUNTIME" in u,
            "P11.25 runtime macros missing")
    for name in names:
        text=g if not name.startswith("udg_") else u
        require(re.search(rf"(?m)^{name}:$",text) is not None,f"P11.25 symbol missing: {name}")
    require("## P11.25 - Graphics/UDG library" in plan and "all eighteen names" in plan,
            "REV08 P11.25 contract drift")
    require("    cls" in arch and "    udg_draw_2x2" in arch,"REV17 P11.25 surface drift")
    for text,marker in ((g,"    MACRO EMIT_P1125_C48_GRAPHICS_RUNTIME"),
                        (u,"    MACRO EMIT_P1125_C48_UDG_RUNTIME")):
        start=text.index(marker); macro=text[start:text.index("    ENDM",start)+8]
        code="\n".join(line.split(";",1)[0] for line in macro.splitlines())
        require(not re.search(r"\biy\b|\bexx\b|ex\s+af\s*,\s*af'",code,re.I),
                "P11.25 wrapper uses OS-private registers")
    require(all(x in g for x in ("SYS_CON_CLEAR","SYS_CON_SETPOS","SYS_CON_WRITE",
                                 "SYS_GFX_PLOT","SYS_GFX_POINT","SYS_GFX_DRAW",
                                 "SYS_GFX_CIRCLE","SYS_GFX_ATTR","SYS_GFX_BORDER")),
            "P11.25 graphics syscall mapping incomplete")
    require(all(x in u for x in ("SYS_UDG_DEFINE","SYS_UDG_GET","SYS_UDG_DRAW","SYS_UDG_CLEAR")),
            "P11.25 UDG syscall mapping incomplete")
    # Mandatory pinned SDK signature reconciliation.
    require("C48_REGCALL" in u and "Fourth C48_REGCALL word is at SP+2." in g,
            "P11.25 C48_REGCALL mapping missing")

    asm=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus")
    build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    f=build/"p1125-graphics-udg.asm"
    f.write_text(r'''    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/libc48/graphics.asm"
    INCLUDE "../src/libc48/udg.asm"
    INCLUDE "../src/kernel/graphics.asm"
    INCLUDE "../src/kernel/udg.asm"
    ORG $C000
p1125_start:
tty_current_attr: db 7
ula_shadow: db 0
p1125_cls_calls: db 0
p1125_pos: dw 0
p1125_print_len: dw 0
p1125_printed: defs 16,0
p1125_text: db "OK",0
p1125_pat: db $81,$42,$24,$18,$18,$24,$42,$81
p1125_get: defs 8,0
p1125_bank: defs 256,0
p1125_fail: ld a,E_FORMAT : scf : ret
p1125_check:
    or a
    sbc hl,de
    jp nz,p1125_fail
    xor a
    ret
zx48_alloc:
    ld hl,p1125_bank
    xor a
    ret
zx48_memory_pin_bytes:
    xor a
    ret
zx48_cursor_hide: ret
zx48_cursor_show: ret
zx48_ula_set_border: and 7 : ld (ula_shadow),a : xor a : ret
zx48_memcpy: ldir : ret
zx48_bitmap_address:
    ld a,b : and 7 : or $40 : ld h,a
    ld a,b : and $C0 : rrca : rrca : rrca : or h : ld h,a
    ld a,b : and $38 : rlca : rlca : or c : ld l,a : ret
p1125_gateway:
    cp SYS_CON_CLEAR : jr z,p1125_clear
    cp SYS_CON_SETPOS : jr z,p1125_setpos
    cp SYS_CON_WRITE : jr z,p1125_write
    cp SYS_GFX_PLOT : jp z,zx48_gfx_plot
    cp SYS_GFX_POINT : jp z,zx48_gfx_point
    cp SYS_GFX_DRAW : jp z,zx48_gfx_draw
    cp SYS_GFX_CIRCLE : jp z,zx48_gfx_circle
    cp SYS_GFX_ATTR : jp z,zx48_gfx_attr
    cp SYS_GFX_BORDER : jp z,zx48_gfx_border
    cp SYS_UDG_DEFINE : jp z,zx48_udg_define
    cp SYS_UDG_GET : jp z,zx48_udg_get
    cp SYS_UDG_DRAW : jp z,zx48_udg_draw
    cp SYS_UDG_CLEAR : jp z,zx48_udg_clear
    ld a,E_NOTSUP : scf : ret
p1125_clear: ld a,(p1125_cls_calls) : inc a : ld (p1125_cls_calls),a : xor a : ret
p1125_setpos: ld (p1125_pos),hl : xor a : ret
p1125_write:
    ld (p1125_print_len),bc
    push bc : ld de,p1125_printed : ldir : pop hl : xor a : ret
    EMIT_GRAPHICS_ROUTINES
    EMIT_UDG_ROUTINES
    EMIT_P1125_C48_GRAPHICS_RUNTIME
    EMIT_P1125_C48_UDG_RUNTIME
p1125_matrix:
    ld iy,ROM_IY_ANCHOR
    ld hl,p1125_bank : ld (udg_bank_ptr),hl : ld (ROM_UDG),hl
    xor a : ld ($4000),a : ld ($4100),a : ld ($4021),a : ld ($5800),a
    call cls
    ld a,(p1125_cls_calls) : cp 1 : jp nz,p1125_fail
    ld hl,2 : ld de,3 : ld bc,p1125_text : call print_at
    ld hl,(p1125_pos) : ld de,$0203 : call p1125_check : ret c
    ld hl,(p1125_print_len) : ld de,2 : call p1125_check : ret c
    ld a,(p1125_printed) : cp 'O' : jp nz,p1125_fail
    ld a,(p1125_printed+1) : cp 'K' : jp nz,p1125_fail
    ld hl,2 : call ink
    ld hl,4 : call paper
    ld hl,1 : call bright
    ld hl,0 : call flash
    ld hl,0 : call inverse
    ld hl,0 : call over
    ld a,(tty_current_attr) : cp $62 : jp nz,p1125_fail
    ld hl,0 : ld de,0 : call plot
    ld a,($4000) : cp $80 : jp nz,p1125_fail
    ld a,($5800) : cp $62 : jp nz,p1125_fail
    ld hl,0 : ld de,0 : call point
    ld de,1 : call p1125_check : ret c
    ld hl,1 : push hl : ld hl,1 : ld de,1 : ld bc,3 : call draw : pop de
    ld a,($4100) : cp $70 : jp nz,p1125_fail
    ld hl,8 : ld de,8 : ld bc,0 : call circle
    ld a,($4021) : cp $80 : jp nz,p1125_fail
    ld hl,3 : call border
    ld a,(ula_shadow) : cp 3 : jp nz,p1125_fail
    ld hl,3 : ld de,p1125_pat : call udg_define
    ld hl,3 : ld de,p1125_get : call udg_get
    ld hl,p1125_pat : ld de,p1125_get : ld b,8
p1125_pat_cmp:
    ld a,(de) : cp (hl) : jp nz,p1125_fail : inc de : inc hl : djnz p1125_pat_cmp
    ld hl,3 : ld de,1 : ld bc,2 : call udg_draw
    ld a,($4022) : cp $81 : jp nz,p1125_fail
    ld a,($5822) : cp $62 : jp nz,p1125_fail
    ld hl,3 : call udg_clear
    ld hl,p1125_bank+24 : ld b,8
p1125_clear_cmp:
    ld a,(hl) : or a : jp nz,p1125_fail : inc hl : djnz p1125_clear_cmp
    ld hl,4
p1125_define_loop:
    push hl : ld de,p1125_pat : call udg_define : pop hl
    inc l : ld a,l : cp 8 : jr nz,p1125_define_loop
    ld hl,4 : ld de,2 : ld bc,4 : call udg_draw_2x2
    ld a,($4044) : cp $81 : jp nz,p1125_fail
    ld a,($4045) : cp $81 : jp nz,p1125_fail
    ld a,($4064) : cp $81 : jp nz,p1125_fail
    ld a,($4065) : cp $81 : jp nz,p1125_fail
    push iy : pop hl : ld de,ROM_IY_ANCHOR : jp p1125_check
p1125_negative:
    ld iy,ROM_IY_ANCHOR
    ld a,$5A : ld ($4000),a
    ld hl,$0100 : ld de,0 : call plot
    ld de,E_INVAL : call p1125_check : ret c
    ld a,($4000) : cp $5A : jp nz,p1125_fail
    push iy : pop hl : ld de,ROM_IY_ANCHOR : jp p1125_check
p1125_end:
    SAVEBIN "p1125-main.bin",p1125_start,p1125_end-p1125_start
''',encoding="utf-8",newline="\n")
    result=run_command([asm,"--nologo","--sym=p1125-graphics-udg.sym",f.name],
                       cwd=build,timeout_seconds=30)
    require(not result.timed_out and result.exit_code==0,
            f"P11.25 assemble: {result.stderr or result.stdout}")
    main=(build/"p1125-main.bin").read_bytes()
    require(0<len(main)<=0x2000,"P11.25 fixture exceeds C000-DFFF user range")
    syms=phase3_open_descriptions._symbols(build/"p1125-graphics-udg.sym",
                                           ("p1125_gateway","p1125_matrix","p1125_negative"))
    assertions=[
      {"name":"all-eighteen-public-graphics-udg-symbols-present","passed":True},
      {"name":"wrappers-use-frozen-console-graphics-udg-syscalls","passed":True},
      {"name":"draw-fourth-argument-uses-regcall-stack-word","passed":True},
      {"name":"pinned-sdk-signature-mapping-reviewed","passed":True},
    ]
    commands=[result]
    if action=="test":
        gateway=phase1._jp(syms["p1125_gateway"])
        def patch(ram):
            ram[0xC000-0x4000:0xC000-0x4000+len(main)]=main
            ram[0xE000-0x4000:0xE000-0x4000+len(gateway)]=gateway
        for name in ("p1125_matrix","p1125_negative"):
            code=b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._call(syms[name])+phase1._jp_c(FAIL_PC)+phase1._jp(PASS_PC)
            try:
                commands.append(run_sna(root,code,patch=patch))
            except DriverError as exc:
                raise P1125Error(f"{name} native fixture failed: {exc}") from None
        assertions += [
          {"name":"fuse-colors-lines-point-circle-screen-bytes-exact","passed":True},
          {"name":"fuse-attribute-and-ula-shadow-exact","passed":True},
          {"name":"fuse-udg-define-get-draw-clear-2x2-exact","passed":True},
          {"name":"fuse-print-at-console-contract-exact","passed":True},
          {"name":"fuse-iy-preserved-negative-coordinate-nonmutating","passed":True},
        ]
    hashes={
      "v1/src/libc48/graphics.asm":sha256_file(graphics),
      "v1/src/libc48/udg.asm":sha256_file(udg),
      "v1/build/p1125-main.bin":sha256_file(build/"p1125-main.bin"),
      "v1/tools-host/test-driver/phase11_step_25.py":sha256_file(root/"v1/tools-host/test-driver/phase11_step_25.py"),
      "v1/dist/certification/P11.24.build.json":sha256_file(root/"v1/dist/certification/P11.24.build.json"),
      "v1/dist/certification/P11.24.test.json":sha256_file(root/"v1/dist/certification/P11.24.test.json"),
    }
    return commands,hashes,assertions
