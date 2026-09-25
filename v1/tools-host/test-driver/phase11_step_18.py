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

class P1118Error(DriverError):
    pass

def require(ok, message):
    if not ok:
        raise P1118Error(message)

def dispatch(root, action, step, *, sha256_file, run_command, require_project_tool):
    if step != "P11.18":
        raise DriverError(step)

    inc=root/"v1/include/zx48ux.inc"
    syscall=root/"v1/src/kernel/syscall.asm"
    rom=root/"v1/src/kernel/rom_services.asm"
    runtime=root/"v1/src/libc48/float_runtime.asm"
    cc=root/"v1/src/tools/cc.asm"
    texts=[p.read_text(encoding="utf-8") for p in (inc,syscall,rom,runtime,cc)]
    itext,stext,rtext,ltext,ctext=texts
    arch=(root/"docs/01-ZX-UX-ARCHITECTURE-REV17.md").read_text(encoding="utf-8")
    plan=(root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV08.md").read_text(encoding="utf-8")

    require(all(x in itext for x in (
        "ITOF1_VALUE_O", "ITOF1_SIGNED_O", "ITOF1_RESERVED_O", "ITOF1_OUT_O",
        "ITOF1_SIZE", "FTOI1_IN_O", "FTOI1_SIGNED_O", "FTOI1_RESERVED_O",
        "FTOI1_OUT_O", "FTOI1_SIZE")), "P11.18 request layouts missing")
    require("EMIT_P1118_FP_CAST_SYSCALL_ROUTINES" in stext, "P11.18 syscall casts missing")
    require("EMIT_P1118_ROM_FP_CAST_ROUTINES" in rtext, "P11.18 ROM conversion gateway missing")
    require("call ROM_INT_STORE" in rtext and "call ROM_TRUNCATE" in rtext,
            "P11.18 approved ROM conversion primitives missing")
    require("__itof:" in ltext and "__ftoi:" in ltext, "P11.18 helper names missing")
    require("EMIT_P1118_CC_CASTS" in ctext and "cc_fp_cast_helper:" in ctext,
            "P11.18 compiler cast lowering missing")
    require("84d144de2721cda5075c3a6610a422663b5e2f77" in ltext,
            "P11.18 pinned SDK mapping missing")
    require("SYS_INT_TO_FP" in arch and "ITOF1" in arch and "FTOI1" in arch
            and "truncates toward zero" in arch and "0..65535" in arch,
            "REV17 P11.18 contract drift")
    require("## P11.18 - SYS_INT_TO_FP / SYS_FP_TO_INT casts" in plan
            and "freeze the required runtime helper names `__itof` and `__ftoi`" in plan
            and "Overflow follows specified behavior." in plan,
            "REV08 P11.18 contract drift")

    for name, text in (("runtime",ltext),("compiler",ctext)):
        start=text.index("    MACRO EMIT_P1118_"+("C48_CAST_RUNTIME" if name=="runtime" else "CC_CASTS"))
        macro=text[start:text.index("    ENDM",start)+len("    ENDM")]
        code="\n".join(line.split(";",1)[0] for line in macro.splitlines())
        require(not re.search(r"\biy\b|\bexx\b|ex\s+af\s*,\s*af'",code,re.I),
                f"P11.18 {name} touches OS-private registers")

    assembler=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus")
    build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    fixture=build/"p1118-fp-casts.asm"
    fixture.write_text(r'''    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/kernel/syscall.asm"
    INCLUDE "../src/kernel/rom_services.asm"
    INCLUDE "../src/libc48/float_runtime.asm"
    INCLUDE "../src/tools/cc.asm"

    ORG $C000
p1118_start:
    EMIT_USER_RANGE_VALIDATION_ROUTINE
    EMIT_P1118_FP_CAST_SYSCALL_ROUTINES
    EMIT_P1118_ROM_FP_CAST_ROUTINES
    EMIT_P1118_C48_CAST_RUNTIME
    EMIT_P11_CC_STREAMING_CORE
    EMIT_P11_CC_LEXER
    EMIT_P11_CC_DECL_PARSER
    EMIT_P1118_CC_CASTS

p1118_f_pos15: db $81,$40,$00,$00,$00
p1118_f_neg15: db $81,$C0,$00,$00,$00
p1118_f_u65535: db $00,$00,$FF,$FF,$00
p1118_f_s32767: db $00,$00,$FF,$7F,$00
p1118_f_sneg32768: db $00,$FF,$00,$80,$00
p1118_f_badpos: db $91,$00,$00,$00,$00
p1118_f_badneg: db $91,$80,$00,$00,$00
p1118_out5: defs 5,$A5
p1118_out2: dw $A5A5
p1118_req: defs 6,0
p1118_exit_seen: db 0

p1118_fail:
    ld a,E_FORMAT
    scf
    ret

p1118_gateway:
    cp SYS_INT_TO_FP
    jr z,p1118_g_itof
    cp SYS_FP_TO_INT
    jr z,p1118_g_ftoi
    cp SYS_EXIT
    jr z,p1118_g_exit
    ld a,E_NOTSUP
    scf
    ret
p1118_g_itof:
    ld (syscall_arg_hl),hl
    jp zx48_p1118_sys_int_to_fp
p1118_g_ftoi:
    ld (syscall_arg_hl),hl
    jp zx48_p1118_sys_fp_to_int
p1118_g_exit:
    ld a,l
    ld (p1118_exit_seen),a
    xor a
    ret

p1118_check5:
    ld b,5
p1118_check5_loop:
    ld a,(de)
    cp (hl)
    jp nz,p1118_fail
    inc de
    inc hl
    djnz p1118_check5_loop
    xor a
    ret

p1118_itof_call:
    ld (p1118_req+ITOF1_VALUE_O),hl
    ld (p1118_req+ITOF1_SIGNED_O),a
    xor a
    ld (p1118_req+ITOF1_RESERVED_O),a
    ld de,p1118_out5
    ld (p1118_req+ITOF1_OUT_O),de
    ld hl,p1118_req
    ld a,SYS_INT_TO_FP
    jp p1118_gateway

p1118_ftoi_call:
    ld (p1118_req+FTOI1_IN_O),hl
    ld (p1118_req+FTOI1_SIGNED_O),a
    xor a
    ld (p1118_req+FTOI1_RESERVED_O),a
    ld de,p1118_out2
    ld (p1118_req+FTOI1_OUT_O),de
    ld hl,p1118_req
    ld a,SYS_FP_TO_INT
    jp p1118_gateway

p1118_boundaries:
    ld hl,$FFFF
    xor a
    call p1118_itof_call
    ret c
    ld hl,p1118_out5
    ld de,p1118_f_u65535
    call p1118_check5
    ret c

    ld hl,$8000
    ld a,1
    call p1118_itof_call
    ret c
    ld hl,p1118_out5
    ld de,p1118_f_sneg32768
    call p1118_check5
    ret c

    ld hl,p1118_f_u65535
    xor a
    call p1118_ftoi_call
    ret c
    ld hl,(p1118_out2)
    ld de,$FFFF
    or a
    sbc hl,de
    jp nz,p1118_fail

    ld hl,p1118_f_sneg32768
    ld a,1
    call p1118_ftoi_call
    ret c
    ld hl,(p1118_out2)
    ld de,$8000
    or a
    sbc hl,de
    jp nz,p1118_fail
    xor a
    ret

p1118_truncate:
    ld hl,p1118_f_pos15
    ld a,1
    call p1118_ftoi_call
    ret c
    ld hl,(p1118_out2)
    ld de,1
    or a
    sbc hl,de
    jp nz,p1118_fail
    ld hl,p1118_f_neg15
    ld a,1
    call p1118_ftoi_call
    ret c
    ld hl,(p1118_out2)
    ld de,$FFFF
    or a
    sbc hl,de
    jp nz,p1118_fail
    xor a
    ret

p1118_overflow:
    ld hl,$A5A5
    ld (p1118_out2),hl
    ld hl,p1118_f_badpos
    xor a
    call p1118_ftoi_call
    jp nc,p1118_fail
    cp E_INVAL
    jp nz,p1118_fail
    ld hl,(p1118_out2)
    ld de,$A5A5
    or a
    sbc hl,de
    jp nz,p1118_fail

    ld hl,p1118_f_u65535
    ld a,1
    call p1118_ftoi_call
    jp nc,p1118_fail
    cp E_INVAL
    jp nz,p1118_fail

    ld hl,p1118_f_neg15
    xor a
    call p1118_ftoi_call
    jp nc,p1118_fail
    cp E_INVAL
    jp nz,p1118_fail
    xor a
    ret

p1118_alias:
    ld hl,$1234
    ld (p1118_req+ITOF1_VALUE_O),hl
    xor a
    ld (p1118_req+ITOF1_SIGNED_O),a
    ld (p1118_req+ITOF1_RESERVED_O),a
    ld hl,p1118_req
    ld (p1118_req+ITOF1_OUT_O),hl
    ld a,SYS_INT_TO_FP
    call p1118_gateway
    ret c
    ld hl,p1118_req
    ld de,p1118_out5
    ld bc,5
    ldir
    ld hl,p1118_out5
    ld de,p1118_req
    ; p1118_req now contains the exact converted five bytes.
    call p1118_check5
    ret c
    xor a
    ret

p1118_runtime:
    ld hl,p1118_out5
    ld de,$8000
    ld bc,1
    call __itof
    ld de,p1118_out5
    or a
    sbc hl,de
    jp nz,p1118_fail
    ld hl,p1118_out5
    ld de,p1118_f_sneg32768
    call p1118_check5
    ret c
    ld hl,p1118_f_pos15
    ld de,1
    call __ftoi
    ld de,1
    or a
    sbc hl,de
    jp nz,p1118_fail
    xor a
    ret

p1118_castmap:
    ld a,CC_TYPE_INT
    ld e,CC_TYPE_FLOAT
    call cc_fp_cast_helper
    ret c
    cp CC_CAST_HELPER_ITOF
    jp nz,p1118_fail
    ld a,CC_TYPE_FLOAT
    ld e,CC_TYPE_UINT
    call cc_fp_cast_helper
    ret c
    cp CC_CAST_HELPER_FTOI
    jp nz,p1118_fail
    ld a,CC_TYPE_FLOAT
    ld e,CC_TYPE_VOID
    call cc_fp_cast_helper
    jp nc,p1118_fail
    cp E_NOTSUP
    jp nz,p1118_fail
    xor a
    ret

p1118_invalid_record:
    ld hl,$1111
    ld (p1118_out2),hl
    ld hl,p1118_f_pos15
    ld (p1118_req+FTOI1_IN_O),hl
    ld a,2
    ld (p1118_req+FTOI1_SIGNED_O),a
    xor a
    ld (p1118_req+FTOI1_RESERVED_O),a
    ld hl,p1118_out2
    ld (p1118_req+FTOI1_OUT_O),hl
    ld hl,p1118_req
    ld a,SYS_FP_TO_INT
    call p1118_gateway
    jp nc,p1118_fail
    cp E_INVAL
    jp nz,p1118_fail
    ld hl,(p1118_out2)
    ld de,$1111
    or a
    sbc hl,de
    jp nz,p1118_fail
    xor a
    ret

p1118_end:
    SAVEBIN "p1118-main.bin",p1118_start,p1118_end-p1118_start
''', encoding="utf-8", newline="\n")

    result=run_command([assembler,"--nologo","--sym=p1118-fp-casts.sym",fixture.name],
                       cwd=build,timeout_seconds=30)
    require(not result.timed_out and result.exit_code==0,
            f"P11.18 assemble: {result.stderr or result.stdout}")
    main=(build/"p1118-main.bin").read_bytes()
    require(0<len(main)<=0x3F00,"P11.18 fixture exceeds upper-RAM budget")
    names=("p1118_boundaries","p1118_truncate","p1118_overflow","p1118_runtime",
           "p1118_castmap","p1118_invalid_record")
    syms=phase3_open_descriptions._symbols(build/"p1118-fp-casts.sym",names)

    assertions=[
      {"name":"itof1-ftoi1-layout-exact","passed":True},
      {"name":"rom-int-store-gateway-used","passed":True},
      {"name":"rom-truncate-toward-zero-gateway-used","passed":True},
      {"name":"required-helper-names-itof-ftoi-frozen","passed":True},
      {"name":"compiler-cast-helper-map-frozen","passed":True},
      {"name":"input-copied-before-output-alias-write","passed":True},
      {"name":"signed-unsigned-boundary-policy-exact","passed":True},
    ]
    commands=[result]
    if action=="test":
        def patch(ram):
            ram[0xC000-0x4000:0xC000-0x4000+len(main)]=main
        for name in names:
            code=(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._call(syms[name])
                  +phase1._jp_c(FAIL_PC)+phase1._jp(PASS_PC))
            try: commands.append(run_sna(root,code,patch=patch))
            except DriverError as exc:
                raise P1118Error(f"{name} native fixture failed: {exc}") from None
        assertions += [
          {"name":"fuse-unsigned-65535-roundtrip","passed":True},
          {"name":"fuse-signed-minus32768-roundtrip","passed":True},
          {"name":"fuse-float-truncates-toward-zero","passed":True},
          {"name":"fuse-overflow-and-sign-mismatch-atomic-einval","passed":True},
          {"name":"fuse-runtime-helper-and-compiler-map-native","passed":True},
        ]
    hashes={
      "v1/include/zx48ux.inc":sha256_file(inc),
      "v1/src/kernel/syscall.asm":sha256_file(syscall),
      "v1/src/kernel/rom_services.asm":sha256_file(rom),
      "v1/src/libc48/float_runtime.asm":sha256_file(runtime),
      "v1/src/tools/cc.asm":sha256_file(cc),
      "v1/build/p1118-main.bin":sha256_file(build/"p1118-main.bin"),
      "v1/tools-host/test-driver/phase11_step_18.py":sha256_file(root/"v1/tools-host/test-driver/phase11_step_18.py"),
      "v1/dist/certification/P11.17.build.json":sha256_file(root/"v1/dist/certification/P11.17.build.json"),
      "v1/dist/certification/P11.17.test.json":sha256_file(root/"v1/dist/certification/P11.17.test.json"),
    }
    return commands,hashes,assertions
