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

class P1126Error(DriverError): pass
def require(ok, message):
    if not ok: raise P1126Error(message)

def dispatch(root, action, step, *, sha256_file, run_command, require_project_tool):
    if step != "P11.26": raise DriverError(step)
    sound=root/"v1/src/libc48/sound.asm"; text=sound.read_text()
    syscall=(root/"v1/src/kernel/syscall.asm").read_text()
    ksnd=(root/"v1/src/kernel/sound.asm").read_text()
    arch=(root/"docs/01-ZX-UX-ARCHITECTURE-REV17.md").read_text()
    plan=(root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV08.md").read_text()
    require("EMIT_P1126_C48_SOUND_RUNTIME" in text and re.search(r"(?m)^beep:$",text),
            "P11.26 public beep missing")
    require("ld a,SYS_BEEP" in text and "call SYSCALL_GATEWAY" in text,
            "P11.26 SYS_BEEP mapping missing")
    require("int beep(float duration, float pitch)" in arch
            and "fractional pitch is supported" in arch
            and "adding/subtracting 12 changes pitch by one octave" in arch,
            "REV17 beep contract drift")
    require("## P11.26 - C48 beep wrapper" in plan
            and "same synchronous SYS_BEEP" in plan,
            "REV08 P11.26 contract drift")
    require("ld hl,(syscall_arg_hl)" in syscall and "ld de,(syscall_arg_de)" in syscall
            and "jp zx48_sound_beep" in syscall and "call zx48_rom_beep_values" in ksnd,
            "kernel beep path drift")
    macro=text[text.index("    MACRO EMIT_P1126_C48_SOUND_RUNTIME"):]
    macro=macro[:macro.index("    ENDM")+8]
    code="\n".join(x.split(";",1)[0] for x in macro.splitlines())
    require(not re.search(r"\biy\b|\bexx\b|ex\s+af\s*,\s*af'",code,re.I),
            "P11.26 uses OS-private registers")

    asm=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus")
    build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    f=build/"p1126-beep.asm"
    f.write_text(r'''    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/libc48/sound.asm"
    ORG $C000
p1126_start:
p1126_d1:    db $81,$00,$00,$00,$00
p1126_dh:    db $80,$00,$00,$00,$00
p1126_dq:    db $7F,$00,$00,$00,$00
p1126_p0:    db $00,$00,$00,$00,$00
p1126_p9:    db $00,$00,$09,$00,$00
p1126_pm12:  db $00,$FF,$F4,$00,$00
p1126_pp12:  db $00,$00,$0C,$00,$00
p1126_phalf: db $80,$00,$00,$00,$00
p1126_seen_hl: dw 0
p1126_seen_de: dw 0
p1126_calls: db 0
p1126_done: db 0
p1126_mode: db 0
p1126_before: defs 10,0
p1126_after: defs 10,0

p1126_fail: ld a,E_FORMAT : scf : ret

p1126_gateway:
    cp SYS_BEEP : jp nz,p1126_fail
    ld (p1126_seen_hl),hl : ld (p1126_seen_de),de
    push hl : push de
    ld de,p1126_before : ld bc,5 : ldir
    pop hl : ld de,p1126_before+5 : ld bc,5 : ldir
    pop hl
    ld a,(p1126_calls) : inc a : ld (p1126_calls),a
    ld a,1 : ld (p1126_done),a
    ld a,(p1126_mode) : or a : jr nz,p1126_domain_error
    xor a : ret
p1126_domain_error: ld a,E_INVAL : scf : ret

    EMIT_P1126_C48_SOUND_RUNTIME

p1126_copy_after:
    push hl : push de
    ld de,p1126_after : ld bc,5 : ldir
    pop hl : ld de,p1126_after+5 : ld bc,5 : ldir
    pop hl : ret
p1126_cmp10:
    ld hl,p1126_before : ld de,p1126_after : ld b,10
p1126_cmp10_loop:
    ld a,(de) : cp (hl) : jp nz,p1126_fail
    inc de : inc hl : djnz p1126_cmp10_loop
    xor a : ret

; HL=duration pointer, DE=pitch pointer, C=expected errno.
p1126_one:
    push bc : push de : push hl
    call beep
    ld b,h : ld c,l
    pop hl : pop de
    push bc
    call p1126_copy_after
    call p1126_cmp10
    jp c,p1126_fail
    pop hl : pop bc
    ld a,c : cp l : jp nz,p1126_fail
    ld a,h : or a : jp nz,p1126_fail
    ld a,(p1126_done) : cp 1 : jp nz,p1126_fail
    xor a : ld (p1126_done),a : ret

p1126_vectors:
    xor a : ld (p1126_mode),a
    ld hl,p1126_d1 : ld de,p1126_p0 : ld c,0 : call p1126_one : ret c
    ld hl,p1126_dh : ld de,p1126_p9 : ld c,0 : call p1126_one : ret c
    ld hl,p1126_dq : ld de,p1126_pm12 : ld c,0 : call p1126_one : ret c
    ld hl,p1126_dq : ld de,p1126_pp12 : ld c,0 : call p1126_one : ret c
    ld hl,p1126_dq : ld de,p1126_phalf : ld c,0 : call p1126_one : ret c
    ld a,(p1126_calls) : cp 5 : jp nz,p1126_fail
    xor a : ret
p1126_negative:
    ld a,1 : ld (p1126_mode),a
    ld hl,p1126_dq : ld de,p1126_phalf : ld c,E_INVAL
    call p1126_one : ret c
    ld a,(p1126_calls) : cp 1 : jp nz,p1126_fail
    xor a : ret
p1126_end:
    SAVEBIN "p1126-main.bin",p1126_start,p1126_end-p1126_start
''',encoding="utf-8",newline="\n")
    result=run_command([asm,"--nologo","--sym=p1126-beep.sym",f.name],cwd=build,timeout_seconds=30)
    require(not result.timed_out and result.exit_code==0,
            f"P11.26 assemble: {result.stderr or result.stdout}")
    main=(build/"p1126-main.bin").read_bytes()
    require(0<len(main)<=0x2000,"P11.26 fixture exceeds C000-DFFF")
    syms=phase3_open_descriptions._symbols(build/"p1126-beep.sym",
                                           ("p1126_gateway","p1126_vectors","p1126_negative"))
    # P11.26 assertions bind the public wrapper to the already-certified synchronous kernel path.
    assertions=[
      {"name":"public-beep-symbol-exact","passed":True},
      {"name":"beep-uses-synchronous-sys-beep","passed":True},
      {"name":"float-pointer-abi-preserved","passed":True},
      {"name":"fractional-negative-octave-domain-not-narrowed","passed":True},
    ]
    commands=[result]
    if action=="test":
        gateway=phase1._jp(syms["p1126_gateway"])
        def patch(ram):
            ram[0xC000-0x4000:0xC000-0x4000+len(main)]=main
            ram[0xE000-0x4000:0xE000-0x4000+len(gateway)]=gateway
        for name in ("p1126_vectors","p1126_negative"):
            code=b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._call(syms[name])+phase1._jp_c(FAIL_PC)+phase1._jp(PASS_PC)
            try: commands.append(run_sna(root,code,patch=patch))
            except DriverError as exc: raise P1126Error(f"{name} native fixture failed: {exc}") from None
        assertions += [
          {"name":"fuse-mandatory-fractional-octave-vectors-synchronous","passed":True},
          {"name":"fuse-operands-byte-unchanged","passed":True},
          {"name":"fuse-invalid-rom-domain-positive-errno","passed":True},
        ]
    hashes={
      "v1/src/libc48/sound.asm":sha256_file(sound),
      "v1/build/p1126-main.bin":sha256_file(build/"p1126-main.bin"),
      "v1/tools-host/test-driver/phase11_step_26.py":sha256_file(root/"v1/tools-host/test-driver/phase11_step_26.py"),
      "v1/dist/certification/P11.25.build.json":sha256_file(root/"v1/dist/certification/P11.25.build.json"),
      "v1/dist/certification/P11.25.test.json":sha256_file(root/"v1/dist/certification/P11.25.test.json"),
    }
    return commands,hashes,assertions
