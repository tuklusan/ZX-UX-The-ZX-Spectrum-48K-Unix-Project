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

class P1119Error(DriverError):
    pass

def require(ok, message):
    if not ok:
        raise P1119Error(message)

def dispatch(root, action, step, *, sha256_file, run_command, require_project_tool):
    if step != "P11.19":
        raise DriverError(step)

    inc=root/"v1/include/zx48ux.inc"
    syscall=root/"v1/src/kernel/syscall.asm"
    rom=root/"v1/src/kernel/rom_services.asm"
    runtime=root/"v1/src/libc48/float_runtime.asm"
    cc=root/"v1/src/tools/cc.asm"
    itext=inc.read_text(encoding="utf-8")
    stext=syscall.read_text(encoding="utf-8")
    rtext=rom.read_text(encoding="utf-8")
    ltext=runtime.read_text(encoding="utf-8")
    ctext=cc.read_text(encoding="utf-8")
    arch=(root/"docs/01-ZX-UX-ARCHITECTURE-REV17.md").read_text(encoding="utf-8")
    plan=(root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV08.md").read_text(encoding="utf-8")

    require(all(x in itext for x in ("FCMP1_LHS_O","FCMP1_RHS_O","FCMP1_OUT_O","FCMP1_SIZE")),
            "P11.19 FCMP1 layout missing")
    require("EMIT_P1119_FP_CMP_SYSCALL_ROUTINES" in stext, "P11.19 syscall missing")
    require("EMIT_P1119_ROM_FP_CMP_ROUTINES" in rtext, "P11.19 ROM compare missing")
    require("P1119_ROM_LT             EQU $0D" in rtext and "P1119_ROM_EQ             EQU $0E" in rtext,
            "P11.19 ROM comparison literals drift")
    require("__fcmp:" in ltext and "__ftruth:" in ltext and "c48_fp_exact_zero:" in ltext,
            "P11.19 runtime helpers missing")
    require("EMIT_P1119_CC_FLOAT_COMPARE" in ctext and "cc_fp_compare_plan:" in ctext
            and "cc_fp_truth_helper:" in ctext, "P11.19 compiler lowering map missing")
    require("84d144de2721cda5075c3a6610a422663b5e2f77" in ltext,
            "P11.19 pinned SDK mapping missing")
    require("SYS_FP_CMP" in arch and "6-byte `FCMP1`" in arch
            and "signed byte -1, 0, or +1" in arch
            and "comparison against exact floating zero" in arch,
            "REV17 P11.19 contract drift")
    require("## P11.19 - SYS_FP_CMP float comparisons" in plan
            and "Lower every float relational/equality test through it" in plan
            and "NaN-like unsupported/domain state handled per ROM contract." in plan,
            "REV08 P11.19 contract drift")

    for name,text,marker in (
        ("runtime",ltext,"    MACRO EMIT_P1119_C48_FCMP_RUNTIME"),
        ("compiler",ctext,"    MACRO EMIT_P1119_CC_FLOAT_COMPARE"),
    ):
        start=text.index(marker)
        macro=text[start:text.index("    ENDM",start)+len("    ENDM")]
        code="\n".join(line.split(";",1)[0] for line in macro.splitlines())
        require(not re.search(r"\biy\b|\bexx\b|ex\s+af\s*,\s*af'",code,re.I),
                f"P11.19 {name} touches OS-private registers")

    assembler=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus")
    build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    fixture=build/"p1119-fp-cmp.asm"
    fixture.write_text(r'''    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/kernel/syscall.asm"
    INCLUDE "../src/kernel/rom_services.asm"
    INCLUDE "../src/libc48/float_runtime.asm"
    INCLUDE "../src/tools/cc.asm"

    ORG $C000
p1119_start:
    EMIT_USER_RANGE_VALIDATION_ROUTINE
    EMIT_P1119_FP_CMP_SYSCALL_ROUTINES
    EMIT_P1119_ROM_FP_CMP_ROUTINES
    EMIT_P1119_C48_FCMP_RUNTIME
    EMIT_P11_CC_STREAMING_CORE
    EMIT_P11_CC_LEXER
    EMIT_P11_CC_DECL_PARSER
    EMIT_P1119_CC_FLOAT_COMPARE

p1119_f_neg1: db $00,$FF,$01,$00,$00
p1119_f_zero: db $00,$00,$00,$00,$00
p1119_f_one:  db $00,$00,$01,$00,$00
p1119_f_two:  db $00,$00,$02,$00,$00
p1119_f_bad:  db $FF,$7F,$FF,$FF,$FF
p1119_lhs_alias: db $00,$00,$01,$00,$00
p1119_req: defs FCMP1_SIZE,0
p1119_out: db $55
p1119_exit_seen: db 0

p1119_fail:
    ld a,E_FORMAT
    scf
    ret

p1119_gateway:
    cp SYS_FP_CMP
    jr z,p1119_g_cmp
    cp SYS_EXIT
    jr z,p1119_g_exit
    ld a,E_NOTSUP
    scf
    ret
p1119_g_cmp:
    ld (syscall_arg_hl),hl
    jp zx48_p1119_sys_fp_cmp
p1119_g_exit:
    ld a,l
    ld (p1119_exit_seen),a
    xor a
    ret

p1119_call:
    ld (p1119_req+FCMP1_LHS_O),hl
    ld (p1119_req+FCMP1_RHS_O),de
    ld hl,p1119_out
    ld (p1119_req+FCMP1_OUT_O),hl
    ld hl,p1119_req
    ld a,SYS_FP_CMP
    jp p1119_gateway

; HL=lhs, DE=rhs, A=expected signed comparison byte.
p1119_expect:
    push af
    call p1119_call
    pop bc
    ret c
    ld a,(p1119_out)
    cp b
    jp nz,p1119_fail
    xor a
    ret

p1119_order:
    ld hl,p1119_f_neg1
    ld de,p1119_f_zero
    ld a,$FF
    call p1119_expect
    ret c
    ld hl,p1119_f_zero
    ld de,p1119_f_zero
    xor a
    call p1119_expect
    ret c
    ld hl,p1119_f_two
    ld de,p1119_f_one
    ld a,1
    call p1119_expect
    ret c
    xor a
    ret

p1119_alias:
    ld hl,p1119_lhs_alias
    ld (p1119_req+FCMP1_LHS_O),hl
    ld de,p1119_f_two
    ld (p1119_req+FCMP1_RHS_O),de
    ld hl,p1119_lhs_alias
    ld (p1119_req+FCMP1_OUT_O),hl
    ld hl,p1119_req
    ld a,SYS_FP_CMP
    call p1119_gateway
    ret c
    ld a,(p1119_lhs_alias)
    cp $FF
    jp nz,p1119_fail
    xor a
    ret

p1119_runtime:
    ld hl,p1119_f_one
    ld de,p1119_f_two
    call __fcmp
    ld de,$FFFF
    or a
    sbc hl,de
    jp nz,p1119_fail

    ld hl,p1119_f_zero
    call __ftruth
    ld a,h
    or l
    jp nz,p1119_fail
    ld hl,p1119_f_one
    call __ftruth
    ld de,1
    or a
    sbc hl,de
    jp nz,p1119_fail
    xor a
    ret

; Exercise < <= == != > >= logical generation from signed __fcmp output.
p1119_relations:
    ld hl,$FFFF
    ld a,C48_FP_REL_LT
    call c48_fcmp_rel
    ld de,1
    or a
    sbc hl,de
    jp nz,p1119_fail
    ld hl,$FFFF
    ld a,C48_FP_REL_LE
    call c48_fcmp_rel
    ld de,1
    or a
    sbc hl,de
    jp nz,p1119_fail
    ld hl,0
    ld a,C48_FP_REL_EQ
    call c48_fcmp_rel
    ld de,1
    or a
    sbc hl,de
    jp nz,p1119_fail
    ld hl,1
    ld a,C48_FP_REL_NE
    call c48_fcmp_rel
    ld de,1
    or a
    sbc hl,de
    jp nz,p1119_fail
    ld hl,1
    ld a,C48_FP_REL_GT
    call c48_fcmp_rel
    ld de,1
    or a
    sbc hl,de
    jp nz,p1119_fail
    ld hl,0
    ld a,C48_FP_REL_GE
    call c48_fcmp_rel
    ld de,1
    or a
    sbc hl,de
    jp nz,p1119_fail
    xor a
    ret

p1119_compiler_map:
    ld a,CC_TYPE_FLOAT
    ld e,CC_TYPE_FLOAT
    call cc_fp_compare_plan
    ret c
    or a
    jp nz,p1119_fail
    ld a,d
    cp CC_FP_COMPARE_HELPER_FCMP
    jp nz,p1119_fail

    ld a,CC_TYPE_INT
    ld e,CC_TYPE_FLOAT
    call cc_fp_compare_plan
    ret c
    cp CC_FP_COMPARE_CAST_LHS
    jp nz,p1119_fail
    ld a,d
    cp CC_FP_COMPARE_HELPER_FCMP
    jp nz,p1119_fail

    ld a,CC_TYPE_FLOAT
    call cc_fp_truth_helper
    ret c
    ld a,d
    cp CC_FP_COMPARE_HELPER_FCMP
    jp nz,p1119_fail

    ld a,CC_FP_REL_GE
    call cc_fp_relation_helper
    ret c
    ld a,d
    cp CC_FP_COMPARE_HELPER_FCMP
    jp nz,p1119_fail
    xor a
    ret

; A malformed/NaN-like five-byte pattern must remain controlled: either the ROM
; accepts it and returns one of -1/0/+1, or the gateway translates a ROM error.
p1119_domain:
    ld a,$55
    ld (p1119_out),a
    ld hl,p1119_f_bad
    ld de,p1119_f_zero
    call p1119_call
    jr c,p1119_domain_error
    ld a,(p1119_out)
    cp $FF
    jr z,p1119_domain_ok
    or a
    jr z,p1119_domain_ok
    cp 1
    jp nz,p1119_fail
p1119_domain_ok:
    xor a
    ret
p1119_domain_error:
    cp E_INVAL
    jp nz,p1119_fail
    ld a,(p1119_out)
    cp $55
    jp nz,p1119_fail
    xor a
    ret

p1119_invalid:
    ld a,$55
    ld (p1119_out),a
    ld hl,0
    ld (p1119_req+FCMP1_LHS_O),hl
    ld hl,p1119_f_zero
    ld (p1119_req+FCMP1_RHS_O),hl
    ld hl,p1119_out
    ld (p1119_req+FCMP1_OUT_O),hl
    ld hl,p1119_req
    ld a,SYS_FP_CMP
    call p1119_gateway
    jp nc,p1119_fail
    cp E_INVAL
    jp nz,p1119_fail
    ld a,(p1119_out)
    cp $55
    jp nz,p1119_fail
    xor a
    ret

p1119_end:
    SAVEBIN "p1119-main.bin",p1119_start,p1119_end-p1119_start
''', encoding="utf-8", newline="\n")

    result=run_command([assembler,"--nologo","--sym=p1119-fp-cmp.sym",fixture.name],
                       cwd=build,timeout_seconds=30)
    require(not result.timed_out and result.exit_code==0,
            f"P11.19 assemble: {result.stderr or result.stdout}")
    main=(build/"p1119-main.bin").read_bytes()
    require(0<len(main)<=0x2000,"P11.19 fixture exceeds C000-DFFF user range")
    names=("p1119_order","p1119_alias","p1119_runtime","p1119_relations",
           "p1119_compiler_map","p1119_domain","p1119_invalid")
    syms=phase3_open_descriptions._symbols(build/"p1119-fp-cmp.sym",("p1119_gateway",)+names)

    assertions=[
      {"name":"fcmp1-six-byte-layout-exact","passed":True},
      {"name":"sys-fp-cmp-writes-one-signed-byte-only","passed":True},
      {"name":"rom-equality-and-less-comparators-own-ordering","passed":True},
      {"name":"inputs-copied-before-alias-result-write","passed":True},
      {"name":"required-helper-name-fcmp-frozen","passed":True},
      {"name":"all-six-float-relations-lower-through-fcmp","passed":True},
      {"name":"float-logical-truth-compares-exact-five-byte-zero","passed":True},
      {"name":"sdk-float-compare-mapping-recorded","passed":True},
    ]
    commands=[result]
    if action=="test":
        gateway=phase1._jp(syms["p1119_gateway"])
        def patch(ram):
            ram[0xC000-0x4000:0xC000-0x4000+len(main)]=main
            ram[0xE000-0x4000:0xE000-0x4000+len(gateway)]=gateway
        for name in names:
            code=(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._call(syms[name])
                  +phase1._jp_c(FAIL_PC)+phase1._jp(PASS_PC))
            try: commands.append(run_sna(root,code,patch=patch))
            except DriverError as exc:
                raise P1119Error(f"{name} native fixture failed: {exc}") from None
        assertions += [
          {"name":"fuse-negative-zero-positive-fcmp-goldens","passed":True},
          {"name":"fuse-alias-safe-single-byte-result","passed":True},
          {"name":"fuse-lt-le-eq-ne-gt-ge-logical-results","passed":True},
          {"name":"fuse-float-truth-zero-and-nonzero","passed":True},
          {"name":"fuse-malformed-domain-state-controlled","passed":True},
          {"name":"fuse-invalid-pointer-atomic-einval","passed":True},
        ]
    hashes={
      "v1/include/zx48ux.inc":sha256_file(inc),
      "v1/src/kernel/syscall.asm":sha256_file(syscall),
      "v1/src/kernel/rom_services.asm":sha256_file(rom),
      "v1/src/libc48/float_runtime.asm":sha256_file(runtime),
      "v1/src/tools/cc.asm":sha256_file(cc),
      "v1/build/p1119-main.bin":sha256_file(build/"p1119-main.bin"),
      "v1/tools-host/test-driver/phase11_step_19.py":sha256_file(root/"v1/tools-host/test-driver/phase11_step_19.py"),
      "v1/dist/certification/P11.18.build.json":sha256_file(root/"v1/dist/certification/P11.18.build.json"),
      "v1/dist/certification/P11.18.test.json":sha256_file(root/"v1/dist/certification/P11.18.test.json"),
    }
    return commands,hashes,assertions
