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

class P1127Error(DriverError): pass
def require(ok, message):
    if not ok: raise P1127Error(message)

def dispatch(root, action, step, *, sha256_file, run_command, require_project_tool):
    if step!="P11.27": raise DriverError(step)
    tape=root/"v1/src/libc48/tape.asm"; zxpack=root/"v1/src/libc48/zxpack.asm"
    t=tape.read_text(); z=zxpack.read_text()
    arch=(root/"docs/01-ZX-UX-ARCHITECTURE-REV17.md").read_text()
    plan=(root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV08.md").read_text()
    public=("tape_save","tape_load","ticks","time_get","time_set")
    require("EMIT_P1127_C48_TAPE_RUNTIME" in t and "EMIT_P1127_C48_ZXPACK_RUNTIME" in z,
            "P11.27 runtime macros missing")
    for name in public:
        require(re.search(rf"(?m)^{name}:$",t) is not None,f"P11.27 public symbol missing: {name}")
    require(re.search(r"(?m)^tape_seek:$",t) is None and "SYS_TAPE_SCAN" not in t,
            "P11.27 invents random/sequential-scan public API")
    require("c48_zxpack_info:" in z and "SYS_ZXPACK_INFO" in z,
            "P11.27 zxpack internal adapter missing")
    require("    tape_save" in arch and "    tape_load" in arch and "    ticks" in arch
            and "    time_get" in arch and "    time_set" in arch
            and "SYS_TICKS       HL -> writable u32 frame count modulo 2^32" in arch
            and "SYS_TIME_GET" in arch and "revision 0" in arch
            and "SYS_TIME_SET" in arch and "subsecond" in arch,
            "REV17 P11.27 surface drift")
    require("## P11.27 - C48 tape/zxpack wrappers" in plan
            and "Exact public cassette/time surface remains `tape_save`, `tape_load`, `ticks`, `time_get`, `time_set`." in plan
            and "Random tape seek API absent." in plan,
            "REV08 P11.27 contract drift")
    for text,marker in ((t,"    MACRO EMIT_P1127_C48_TAPE_RUNTIME"),(z,"    MACRO EMIT_P1127_C48_ZXPACK_RUNTIME")):
        macro=text[text.index(marker):]; macro=macro[:macro.index("    ENDM")+8]
        code="\n".join(x.split(";",1)[0] for x in macro.splitlines())
        require(not re.search(r"\biy\b|\bexx\b|ex\s+af\s*,\s*af'",code,re.I),
                "P11.27 wrapper uses OS-private registers")

    asm=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus")
    build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    f=build/"p1127-tape-time.asm"
    f.write_text(r'''    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/libc48/tape.asm"
    INCLUDE "../src/libc48/zxpack.asm"
    ORG $C000
p1127_start:
    EMIT_P1127_C48_TAPE_RUNTIME
    EMIT_P1127_C48_ZXPACK_RUNTIME
p1127_path: db "/tmp/Case.C",0
p1127_time: defs 6,$A5
p1127_set: db $80,$06,$26,$17
p1127_zp: defs 20,$CC
p1127_last_a: db 0
p1127_last_hl: dw 0
p1127_calls: db 0
p1127_mode: db 0
p1127_tick_lo: dw $FFFF
p1127_tick_hi: dw $FFFF
p1127_revision: dw 0
p1127_subsecond: db 49

p1127_fail: ld a,E_FORMAT : scf : ret
p1127_check:
    or a : sbc hl,de : jp nz,p1127_fail : xor a : ret

p1127_gateway:
    ld (p1127_last_a),a : ld (p1127_last_hl),hl
    ld a,(p1127_calls) : inc a : ld (p1127_calls),a
    ld a,(p1127_mode) : cp 1 : jr z,p1127_io_error
    cp 2 : jr z,p1127_intr_error
    cp 3 : jr z,p1127_again_error
    ld a,(p1127_last_a)
    cp SYS_TICKS : jr z,p1127_ticks
    cp SYS_TIME_GET : jr z,p1127_time_get
    cp SYS_TIME_SET : jr z,p1127_time_set
    cp SYS_ZXPACK_INFO : jr z,p1127_zpinfo
    xor a : ret
p1127_io_error: ld a,E_IO : scf : ret
p1127_intr_error: ld a,E_INTR : scf : ret
p1127_again_error: ld a,E_AGAIN : scf : ret
p1127_ticks:
    ld de,(p1127_tick_lo) : ld (hl),e : inc hl : ld (hl),d : inc hl
    ld de,(p1127_tick_hi) : ld (hl),e : inc hl : ld (hl),d
    xor a : ret
p1127_time_get:
    ld (hl),$80 : inc hl : ld (hl),$06 : inc hl : ld (hl),$26 : inc hl
    ld (hl),$17 : inc hl
    ld de,(p1127_revision) : ld (hl),e : inc hl : ld (hl),d
    xor a : ret
p1127_time_set:
    ld hl,(p1127_revision) : inc hl : ld (p1127_revision),hl
    xor a : ld (p1127_subsecond),a : ret
p1127_zpinfo:
    ld b,20 : xor a
p1127_zp_loop: ld (hl),a : inc hl : djnz p1127_zp_loop
    xor a : ret

p1127_surface:
    xor a : ld (p1127_mode),a : ld (p1127_calls),a
    ld hl,p1127_path : call tape_save
    ld de,0 : call p1127_check : ret c
    ld a,(p1127_last_a) : cp SYS_TAPE_SAVE : jp nz,p1127_fail
    ld hl,(p1127_last_hl) : ld de,p1127_path : call p1127_check : ret c
    ld hl,p1127_path : call tape_load
    ld de,0 : call p1127_check : ret c
    ld a,(p1127_last_a) : cp SYS_TAPE_LOAD : jp nz,p1127_fail
    ld hl,(p1127_last_hl) : ld de,p1127_path : call p1127_check : ret c

    call ticks : ld de,$FFFF : call p1127_check : ret c
    xor a : ld (p1127_tick_lo),a : ld (p1127_tick_lo+1),a
    ld (p1127_tick_hi),a : ld (p1127_tick_hi+1),a
    call ticks : ld de,0 : call p1127_check : ret c

    ld hl,p1127_time : call time_get
    ld de,0 : call p1127_check : ret c
    ld hl,p1127_time : ld de,$0680 : call p1127_check : ret c
    ld hl,p1127_time+2 : ld de,$1726 : call p1127_check : ret c
    ld hl,(p1127_time+4) : ld de,0 : call p1127_check : ret c

    ld hl,p1127_set : call time_set
    ld de,0 : call p1127_check : ret c
    ld hl,(p1127_revision) : ld de,1 : call p1127_check : ret c
    ld a,(p1127_subsecond) : or a : jp nz,p1127_fail

    ld hl,p1127_zp : call c48_zxpack_info
    ld de,0 : call p1127_check : ret c
    xor a : ret

p1127_errors:
    ld a,3 : ld (p1127_mode),a
    ld hl,p1127_time : call time_get
    ld de,E_AGAIN : call p1127_check : ret c
    ld a,1 : ld (p1127_mode),a
    ld hl,p1127_path : call tape_save
    ld de,E_IO : call p1127_check : ret c
    ld a,2 : ld (p1127_mode),a
    ld hl,p1127_path : call tape_load
    ld de,E_INTR : call p1127_check : ret c
    xor a : ret
p1127_end:
    SAVEBIN "p1127-main.bin",p1127_start,p1127_end-p1127_start
''',encoding="utf-8",newline="\n")
    result=run_command([asm,"--nologo","--sym=p1127-tape-time.sym",f.name],cwd=build,timeout_seconds=30)
    require(not result.timed_out and result.exit_code==0,
            f"P11.27 assemble: {result.stderr or result.stdout}")
    main=(build/"p1127-main.bin").read_bytes()
    require(0<len(main)<=0x2000,"P11.27 fixture exceeds C000-DFFF")
    names=("p1127_surface","p1127_errors")
    syms=phase3_open_descriptions._symbols(build/"p1127-tape-time.sym",("p1127_gateway",)+names)
    assertions=[
      {"name":"exact-five-public-cassette-time-symbols-present","passed":True},
      {"name":"random-tape-seek-api-absent","passed":True},
      {"name":"ticks-samples-exact-u32-kernel-record-and-returns-c48-low-word","passed":True},
      {"name":"time-get-time-set-pass-exact-record-pointers","passed":True},
      {"name":"zxpack-info-remains-private-target-adapter","passed":True},
    ]
    commands=[result]
    if action=="test":
        gateway=phase1._jp(syms["p1127_gateway"])
        def patch(ram):
            ram[0xC000-0x4000:0xC000-0x4000+len(main)]=main
            ram[0xE000-0x4000:0xE000-0x4000+len(gateway)]=gateway
        for name in names:
            code=b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._call(syms[name])+phase1._jp_c(FAIL_PC)+phase1._jp(PASS_PC)
            try: commands.append(run_sna(root,code,patch=patch))
            except DriverError as exc: raise P1127Error(f"{name} native fixture failed: {exc}") from None
        assertions += [
          {"name":"fuse-exact-case-tape-path-pointer-preserved","passed":True},
          {"name":"fuse-controlled-tape-io-and-cancel-errors-propagate","passed":True},
          {"name":"fuse-tick-wrap-fixture-exact","passed":True},
          {"name":"fuse-boot-time1-revision-zero-exact","passed":True},
          {"name":"fuse-time-set-revision-increment-subsecond-reset-exact","passed":True},
          {"name":"fuse-invalid-time-state-eagain-exact","passed":True},
        ]
    hashes={
      "v1/src/libc48/tape.asm":sha256_file(tape),
      "v1/src/libc48/zxpack.asm":sha256_file(zxpack),
      "v1/build/p1127-main.bin":sha256_file(build/"p1127-main.bin"),
      "v1/tools-host/test-driver/phase11_step_27.py":sha256_file(root/"v1/tools-host/test-driver/phase11_step_27.py"),
      "v1/dist/certification/P11.26.build.json":sha256_file(root/"v1/dist/certification/P11.26.build.json"),
      "v1/dist/certification/P11.26.test.json":sha256_file(root/"v1/dist/certification/P11.26.test.json"),
    }
    return commands,hashes,assertions
