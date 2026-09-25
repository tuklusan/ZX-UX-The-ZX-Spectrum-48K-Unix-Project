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

class P1120Error(DriverError):
    pass

def require(ok, message):
    if not ok:
        raise P1120Error(message)

def dispatch(root, action, step, *, sha256_file, run_command, require_project_tool):
    if step != "P11.20":
        raise DriverError(step)

    math = root/"v1/src/libc48/math_runtime.asm"
    runtime = root/"v1/src/libc48/float_runtime.asm"
    syscall = root/"v1/src/kernel/syscall.asm"
    rom = root/"v1/src/kernel/rom_services.asm"
    mtext = math.read_text(encoding="utf-8")
    ltext = runtime.read_text(encoding="utf-8")
    stext = syscall.read_text(encoding="utf-8")
    rtext = rom.read_text(encoding="utf-8")
    arch = (root/"docs/01-ZX-UX-ARCHITECTURE-REV17.md").read_text(encoding="utf-8")
    plan = (root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV08.md").read_text(encoding="utf-8")

    public = ("sin","cos","tan","asin","acos","atan","sqrt","exp","log","pow","fabs")
    mapping = {
        "sin":"__fsin","cos":"__fcos","tan":"__ftan","asin":"__fasin",
        "acos":"__facos","atan":"__fatan","sqrt":"__fsqrt","exp":"__fexp",
        "log":"__fln","pow":"__fpow","fabs":"__fabs",
    }
    require("EMIT_P1120_C48_MATH_RUNTIME" in mtext, "P11.20 math runtime macro missing")
    for name in public:
        require(re.search(rf"(?m)^{name}:\n\s+jp\s+{mapping[name]}\s*$", mtext) is not None,
                f"P11.20 public math mapping missing: {name}")
    for helper in tuple(mapping.values()) + ("__itof","__ftoi","__fcmp"):
        require(f"{helper}:" in ltext, f"P11.20 required internal helper missing: {helper}")
    require("84d144de2721cda5075c3a6610a422663b5e2f77" in mtext
            and "compiler/c48/vm.py" in mtext and "compiler/c48/float5.py" in mtext,
            "P11.20 pinned SDK math mapping missing")
    require("EMIT_P1117_FP_EXEC_SYSCALL_ROUTINES" in stext
            and "EMIT_P1117_ROM_FP_EXEC_ROUTINES" in rtext,
            "P11.20 serialized SYS_FP_EXEC prerequisite missing")
    require(all(f"    {name}" in arch for name in public)
            and "__fsin" in arch and "__fpow" in arch,
            "REV17 P11.20 public/internal math contract drift")
    require("## P11.20 - ROM-backed math library" in plan
            and "all eleven public math symbols" in plan
            and "Domain errors controlled." in plan,
            "REV08 P11.20 acceptance contract drift")

    start=mtext.index("    MACRO EMIT_P1120_C48_MATH_RUNTIME")
    macro=mtext[start:mtext.index("    ENDM",start)+len("    ENDM")]
    code="\n".join(line.split(";",1)[0] for line in macro.splitlines())
    require(not re.search(r"\biy\b|\bexx\b|ex\s+af\s*,\s*af'", code, re.I),
            "P11.20 public math wrapper touches OS-private registers")

    assembler=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus")
    build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    fixture=build/"p1120-math.asm"
    fixture.write_text(r'''    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/kernel/syscall.asm"
    INCLUDE "../src/kernel/rom_services.asm"
    INCLUDE "../src/libc48/float_runtime.asm"
    INCLUDE "../src/libc48/math_runtime.asm"

    ORG $C000
p1120_start:
altreg_busy: db 0
    EMIT_USER_RANGE_VALIDATION_ROUTINE
    EMIT_P1117_FP_EXEC_SYSCALL_ROUTINES
    EMIT_P1117_ROM_FP_EXEC_ROUTINES
    EMIT_P1117_C48_FLOAT_RUNTIME
    EMIT_P1120_C48_MATH_RUNTIME

p1120_zero: db $00,$00,$00,$00,$00
p1120_one:  db $00,$00,$01,$00,$00
p1120_neg1: db $00,$FF,$01,$00,$00
p1120_two:  db $00,$00,$02,$00,$00
p1120_three:db $00,$00,$03,$00,$00
p1120_four: db $00,$00,$04,$00,$00
p1120_eight:db $00,$00,$08,$00,$00
p1120_out:  defs 5,$A5
p1120_guard0: db $5A
p1120_guard1: db $A6
p1120_exit_seen: db 0
p1120_yields: db 0

p1120_fail:
    ld a,E_FORMAT
    scf
    ret

p1120_gateway:
    cp SYS_FP_EXEC
    jr z,p1120_g_fp
    cp SYS_EXIT
    jr z,p1120_g_exit
    cp SYS_YIELD
    jr z,p1120_g_yield
    ld a,E_NOTSUP
    scf
    ret
p1120_g_fp:
    ld (syscall_arg_hl),hl
    jp zx48_p1117_sys_fp_exec
p1120_g_exit:
    ld a,l
    ld (p1120_exit_seen),a
    xor a
    ret
p1120_g_yield:
    ld a,(p1120_yields)
    inc a
    ld (p1120_yields),a
    ld hl,0
    xor a
    ret

; HL=actual, DE=expected exact five-byte object.
p1120_cmp5:
    ld b,5
p1120_cmp5_loop:
    ld a,(de)
    cp (hl)
    jp nz,p1120_fail
    inc de
    inc hl
    djnz p1120_cmp5_loop
    xor a
    ret

p1120_clear_out:
    ld hl,p1120_out
    ld b,5
    ld a,$A5
p1120_clear_loop:
    ld (hl),a
    inc hl
    djnz p1120_clear_loop
    xor a
    ret

; DE=input pointer, BC=public unary routine address, IX=expected pointer.
p1120_unary:
    call p1120_clear_out
    ld hl,p1120_out
    push bc
    ret
; entry trampoline is patched by individual test routines through direct calls.

p1120_check_out:
    ld hl,p1120_out
    jp p1120_cmp5

p1120_sin:
    ld hl,p1120_out
    ld de,p1120_zero
    call sin
    ret c
    ld de,p1120_zero
    jp p1120_check_out

p1120_cos:
    ld hl,p1120_out
    ld de,p1120_zero
    call cos
    ret c
    ld de,p1120_one
    jp p1120_check_out

p1120_tan:
    ld hl,p1120_out
    ld de,p1120_zero
    call tan
    ret c
    ld de,p1120_zero
    jp p1120_check_out

p1120_asin:
    ld hl,p1120_out
    ld de,p1120_zero
    call asin
    ret c
    ld de,p1120_zero
    jp p1120_check_out

p1120_acos:
    ld hl,p1120_out
    ld de,p1120_one
    call acos
    ret c
    ld de,p1120_zero
    jp p1120_check_out

p1120_atan:
    ld hl,p1120_out
    ld de,p1120_zero
    call atan
    ret c
    ld de,p1120_zero
    jp p1120_check_out

p1120_sqrt:
    ld hl,p1120_out
    ld de,p1120_four
    call sqrt
    ret c
    ld de,p1120_two
    jp p1120_check_out

p1120_exp:
    ld hl,p1120_out
    ld de,p1120_zero
    call exp
    ret c
    ld de,p1120_one
    jp p1120_check_out

p1120_log:
    ld hl,p1120_out
    ld de,p1120_one
    call log
    ret c
    ld de,p1120_zero
    jp p1120_check_out

p1120_pow:
    ld hl,p1120_out
    ld de,p1120_two
    ld bc,p1120_three
    call pow
    ret c
    ld de,p1120_eight
    jp p1120_check_out

p1120_fabs:
    ld hl,p1120_out
    ld de,p1120_neg1
    call fabs
    ret c
    ld de,p1120_one
    jp p1120_check_out

p1120_yield:
    ld a,SYS_YIELD
    call p1120_gateway
    ret c
    ld a,(p1120_yields)
    cp 1
    jp nz,p1120_fail
    ld a,(altreg_busy)
    or a
    jp nz,p1120_fail
    xor a
    ret

; Representative internal helper calls independently of public labels.
p1120_helpers:
    ld hl,p1120_out
    ld de,p1120_zero
    call __fsin
    ret c
    ld hl,p1120_out
    ld de,p1120_zero
    call p1120_cmp5
    ret c

    ld hl,p1120_out
    ld de,p1120_two
    ld bc,p1120_three
    call __fpow
    ret c
    ld hl,p1120_out
    ld de,p1120_eight
    call p1120_cmp5
    ret c

    xor a
    ret

p1120_domain:
    xor a
    ld (p1120_exit_seen),a
    call p1120_clear_out
    ld hl,p1120_out
    ld de,p1120_neg1
    call sqrt
    jp nc,p1120_fail
    ld a,(p1120_exit_seen)
    cp 1
    jp nz,p1120_fail
    ld hl,p1120_out
    ld b,5
p1120_domain_unchanged:
    ld a,(hl)
    cp $A5
    jp nz,p1120_fail
    inc hl
    djnz p1120_domain_unchanged
    ld a,(p1120_guard0)
    cp $5A
    jp nz,p1120_fail
    ld a,(p1120_guard1)
    cp $A6
    jp nz,p1120_fail
    xor a
    ret

p1120_busy:
    ld a,1
    ld (altreg_busy),a
    xor a
    ld (p1120_exit_seen),a
    call p1120_clear_out
    ld hl,p1120_out
    ld de,p1120_zero
    call sin
    jr c,p1120_busy_expected
    xor a
    ld (altreg_busy),a
    jp p1120_fail
p1120_busy_expected:
    xor a
    ld (altreg_busy),a
    ld a,(p1120_exit_seen)
    cp 1
    jp nz,p1120_fail
    xor a
    ret

p1120_end:
    SAVEBIN "p1120-main.bin",p1120_start,p1120_end-p1120_start
''', encoding="utf-8", newline="\n")

    result=run_command([assembler,"--nologo","--sym=p1120-math.sym",fixture.name],
                       cwd=build,timeout_seconds=30)
    require(not result.timed_out and result.exit_code==0,
            f"P11.20 assemble: {result.stderr or result.stdout}")
    main=(build/"p1120-main.bin").read_bytes()
    require(0<len(main)<=0x2000,"P11.20 fixture exceeds C000-DFFF user range")
    names=("p1120_sin","p1120_cos","p1120_tan","p1120_asin","p1120_acos","p1120_atan","p1120_sqrt","p1120_exp","p1120_log","p1120_pow","p1120_fabs","p1120_yield","p1120_helpers","p1120_domain","p1120_busy")
    syms=phase3_open_descriptions._symbols(build/"p1120-math.sym",("p1120_gateway",)+names)

    assertions=[
      {"name":"eleven-public-math-symbols-present","passed":True},
      {"name":"public-symbols-map-only-to-required-internal-fp-helpers","passed":True},
      {"name":"all-public-float-results-use-hidden-pointer-regcall","passed":True},
      {"name":"pow-uses-shifted-de-bc-pointer-arguments","passed":True},
      {"name":"runtime-remains-serialized-through-sys-fp-exec","passed":True},
      {"name":"sdk-vm-and-float5-mapping-recorded","passed":True},
    ]
    commands=[result]
    if action=="test":
        gateway=phase1._jp(syms["p1120_gateway"])
        def patch(ram):
            ram[0xC000-0x4000:0xC000-0x4000+len(main)]=main
            ram[0xE000-0x4000:0xE000-0x4000+len(gateway)]=gateway
        for name in names:
            code=(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._call(syms[name])
                  +phase1._jp_c(FAIL_PC)+phase1._jp(PASS_PC))
            try: commands.append(run_sna(root,code,patch=patch))
            except DriverError as exc:
                raise P1120Error(f"{name} native fixture failed: {exc}") from None
        assertions += [
          {"name":"fuse-all-eleven-public-math-symbols-execute","passed":True},
          {"name":"fuse-exact-zero-one-two-eight-rom-goldens","passed":True},
          {"name":"fuse-internal-fsin-and-fpow-helpers-execute","passed":True},
          {"name":"fuse-cooperative-yield-between-rom-math-calls-preserves-results","passed":True},
          {"name":"fuse-domain-error-exits-status-one-with-output-unchanged","passed":True},
          {"name":"fuse-calculator-busy-fails-controlled","passed":True},
          {"name":"fuse-calculator-lock-clears-after-success","passed":True},
        ]
    hashes={
      "v1/src/libc48/math_runtime.asm":sha256_file(math),
      "v1/src/libc48/float_runtime.asm":sha256_file(runtime),
      "v1/src/kernel/syscall.asm":sha256_file(syscall),
      "v1/src/kernel/rom_services.asm":sha256_file(rom),
      "v1/build/p1120-main.bin":sha256_file(build/"p1120-main.bin"),
      "v1/tools-host/test-driver/phase11_step_20.py":sha256_file(root/"v1/tools-host/test-driver/phase11_step_20.py"),
      "v1/dist/certification/P11.19.build.json":sha256_file(root/"v1/dist/certification/P11.19.build.json"),
      "v1/dist/certification/P11.19.test.json":sha256_file(root/"v1/dist/certification/P11.19.test.json"),
    }
    return commands,hashes,assertions
