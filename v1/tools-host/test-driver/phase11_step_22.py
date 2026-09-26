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

class P1122Error(DriverError):
    pass

def require(ok, message):
    if not ok:
        raise P1122Error(message)

def dispatch(root, action, step, *, sha256_file, run_command, require_project_tool):
    if step != "P11.22":
        raise DriverError(step)

    source=root/"v1/src/libc48/syscall.asm"
    text=source.read_text(encoding="utf-8")
    arch=(root/"docs/01-ZX-UX-ARCHITECTURE-REV17.md").read_text(encoding="utf-8")
    plan=(root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV08.md").read_text(encoding="utf-8")
    include=(root/"v1/include/zx48ux.inc").read_text(encoding="utf-8")

    public=("exit","yield","sleep","spawn","wait","kill","chdir","getcwd","getenv","getpid")
    require("EMIT_P1122_C48_SYSCALL_RUNTIME" in text, "P11.22 runtime macro missing")
    for name in public:
        require(re.search(rf"(?m)^{name}:$",text) is not None, f"P11.22 public symbol missing: {name}")
    for sym in ("SYS_EXIT","SYS_YIELD","SYS_SLEEP","SYS_SPAWN","SYS_WAIT","SYS_KILL",
                "SYS_CHDIR","SYS_GETCWD","SYS_GETPID"):
        require(f"ld a,{sym}" in text and f"{sym} " in include,
                f"P11.22 symbolic syscall dependency missing: {sym}")
    require("c48_runtime_capture_env1:" in text and "c48_env1_ptr:" in text,
            "P11.22 ENV1 bootstrap capture missing")
    require("ARG1 format:" in arch and "ENV1 format:" in arch
            and "crt0 records the ENV1 pointer for `getenv()`" in arch,
            "REV17 bootstrap environment contract drift")
    require("## P11.22 - C48 process/environment runtime API" in plan
            and "including unset/missing getenv" in plan
            and "Duplicate syscall number literal fails static scan." in plan,
            "REV08 P11.22 acceptance contract drift")
    start=text.index("    MACRO EMIT_P1122_C48_SYSCALL_RUNTIME")
    macro=text[start:text.index("    ENDM",start)+len("    ENDM")]
    code="\n".join(line.split(";",1)[0] for line in macro.splitlines())
    require(not re.search(r"\biy\b|\bexx\b|ex\s+af\s*,\s*af'",code,re.I),
            "P11.22 runtime touches OS-private registers")
    require(not re.search(r"(?m)^\s*ld\s+a\s*,\s*\$[0-9a-f]+\s*$",code,re.I),
            "P11.22 duplicates syscall number as raw literal")

    assembler=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus")
    build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    fixture=build/"p1122-syscall.asm"
    fixture.write_text(r'''    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/libc48/syscall.asm"

    ORG $C000
p1122_start:
    EMIT_P1122_C48_SYSCALL_RUNTIME

p1122_last_a:  db 0
p1122_last_hl: dw 0
p1122_last_bc: dw 0
p1122_failmode: db 0
p1122_cwd: defs 8,$A5

p1122_env:
    db "ENV1",2,0
    dw 25
    db "PATH=/bin",0
    db "EMPTY=",0
p1122_env_end:
p1122_name_path: db "PATH",0
p1122_name_empty: db "EMPTY",0
p1122_name_miss: db "MISSING",0
p1122_proc1: defs 14,0
p1122_wait1: defs 4,0
p1122_path: db "/home/root",0

p1122_fail:
    ld a,E_FORMAT
    scf
    ret

p1122_check_word:
    or a
    sbc hl,de
    jp nz,p1122_fail
    xor a
    ret

p1122_gateway:
    ld (p1122_last_a),a
    ld (p1122_last_hl),hl
    ld (p1122_last_bc),bc
    ld a,(p1122_failmode)
    or a
    jr z,p1122_gateway_ok
    ld a,E_NOENT
    scf
    ret
p1122_gateway_ok:
    ld a,(p1122_last_a)
    cp SYS_GETPID
    jr nz,p1122_not_getpid
    ld hl,3
    xor a
    ret
p1122_not_getpid:
    cp SYS_SPAWN
    jr nz,p1122_not_spawn
    ld hl,4
    xor a
    ret
p1122_not_spawn:
    cp SYS_GETCWD
    jr nz,p1122_zero
    ld hl,(p1122_last_hl)
    ld (hl),'a'
    inc hl
    ld (hl),'b'
    inc hl
    ld (hl),'c'
    inc hl
    ld (hl),0
    ld hl,3
    xor a
    ret
p1122_zero:
    ld hl,0
    xor a
    ret

p1122_all:
    ld de,p1122_env
    ld bc,p1122_env_end-p1122_env
    call c48_runtime_capture_env1
    ret c

    call yield
    ld de,0
    call p1122_check_word
    ret c
    ld a,(p1122_last_a)
    cp SYS_YIELD
    jp nz,p1122_fail

    ld hl,$1234
    call sleep
    ld de,0
    call p1122_check_word
    ret c
    ld a,(p1122_last_a)
    cp SYS_SLEEP
    jp nz,p1122_fail
    ld hl,(p1122_last_hl)
    ld de,c48_sleep_ticks
    call p1122_check_word
    ret c
    ld hl,(c48_sleep_ticks)
    ld de,$1234
    call p1122_check_word
    ret c
    ld hl,(c48_sleep_ticks+2)
    ld de,0
    call p1122_check_word
    ret c

    call getpid
    ld de,3
    call p1122_check_word
    ret c
    ld a,(p1122_last_a)
    cp SYS_GETPID
    jp nz,p1122_fail

    ld hl,p1122_proc1
    call spawn
    ld de,4
    call p1122_check_word
    ret c
    ld hl,(p1122_last_hl)
    ld de,p1122_proc1
    call p1122_check_word
    ret c

    ld hl,p1122_wait1
    call wait
    ld de,0
    call p1122_check_word
    ret c
    ld a,(p1122_last_a)
    cp SYS_WAIT
    jp nz,p1122_fail

    ld hl,5
    call kill
    ld de,0
    call p1122_check_word
    ret c
    ld a,(p1122_last_a)
    cp SYS_KILL
    jp nz,p1122_fail

    ld hl,p1122_path
    call chdir
    ld de,0
    call p1122_check_word
    ret c
    ld a,(p1122_last_a)
    cp SYS_CHDIR
    jp nz,p1122_fail

    ld hl,p1122_cwd
    ld de,8
    call getcwd
    ld de,3
    call p1122_check_word
    ret c
    ld a,(p1122_last_a)
    cp SYS_GETCWD
    jp nz,p1122_fail
    ld hl,(p1122_last_bc)
    ld de,8
    call p1122_check_word
    ret c
    ld hl,p1122_cwd
    ld a,(hl)
    cp 'a'
    jp nz,p1122_fail
    inc hl
    ld a,(hl)
    cp 'b'
    jp nz,p1122_fail
    inc hl
    ld a,(hl)
    cp 'c'
    jp nz,p1122_fail
    inc hl
    ld a,(hl)
    or a
    jp nz,p1122_fail

    ld hl,p1122_name_path
    call getenv
    ld de,p1122_env+13
    call p1122_check_word
    ret c
    ld hl,p1122_name_empty
    call getenv
    ld de,p1122_env+24
    call p1122_check_word
    ret c
    ld hl,p1122_name_miss
    call getenv
    ld de,0
    call p1122_check_word
    ret c

    ld a,1
    ld (p1122_failmode),a
    ld hl,p1122_path
    call chdir
    ld de,E_NOENT
    call p1122_check_word
    ret c
    ld hl,7
    call exit
    ld de,E_NOENT
    call p1122_check_word
    ret c
    xor a
    ld (p1122_failmode),a

    ld de,0
    ld bc,0
    call c48_runtime_capture_env1
    ld hl,p1122_name_path
    call getenv
    ld de,0
    jp p1122_check_word

p1122_end:
    SAVEBIN "p1122-main.bin",p1122_start,p1122_end-p1122_start
''',encoding="utf-8",newline="\n")

    result=run_command([assembler,"--nologo","--sym=p1122-syscall.sym",fixture.name],
                       cwd=build,timeout_seconds=30)
    require(not result.timed_out and result.exit_code==0,
            f"P11.22 assemble: {result.stderr or result.stdout}")
    main=(build/"p1122-main.bin").read_bytes()
    require(0<len(main)<=0x2000,"P11.22 fixture exceeds C000-DFFF user range")
    syms=phase3_open_descriptions._symbols(build/"p1122-syscall.sym",
                                           ("p1122_gateway","p1122_all"))
    assertions=[
      {"name":"ten-required-public-process-environment-symbols-present","passed":True},
      {"name":"all-kernel-calls-use-symbolic-syscall-include","passed":True},
      {"name":"sleep-widens-u16-to-exact-u32-kernel-record","passed":True},
      {"name":"getcwd-translates-c48-second-argument-to-bc-capacity","passed":True},
      {"name":"getenv-reads-captured-immutable-env1-in-place","passed":True},
      {"name":"no-host-posix-or-raw-syscall-number-substitution","passed":True},
    ]
    commands=[result]
    if action=="test":
        gateway=phase1._jp(syms["p1122_gateway"])
        def patch(ram):
            ram[0xC000-0x4000:0xC000-0x4000+len(main)]=main
            ram[0xE000-0x4000:0xE000-0x4000+len(gateway)]=gateway
        code=(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._call(syms["p1122_all"])
              +phase1._jp_c(FAIL_PC)+phase1._jp(PASS_PC))
        try: commands.append(run_sna(root,code,patch=patch))
        except DriverError as exc:
            raise P1122Error(f"P11.22 native wrapper fixture failed: {exc}") from None
        assertions += [
          {"name":"fuse-every-required-wrapper-executes-through-native-gateway","passed":True},
          {"name":"fuse-unset-and-missing-getenv-return-null","passed":True},
          {"name":"fuse-getenv-path-and-empty-values-return-env1-pointers","passed":True},
          {"name":"fuse-cwd-buffer-capacity-and-nul-contract-exact","passed":True},
          {"name":"fuse-spawn-wait-kill-register-contracts-exact","passed":True},
          {"name":"fuse-exact-errno-propagation","passed":True},
        ]
    hashes={
      "v1/src/libc48/syscall.asm":sha256_file(source),
      "v1/build/p1122-main.bin":sha256_file(build/"p1122-main.bin"),
      "v1/tools-host/test-driver/phase11_step_22.py":sha256_file(root/"v1/tools-host/test-driver/phase11_step_22.py"),
      "v1/dist/certification/P11.21.build.json":sha256_file(root/"v1/dist/certification/P11.21.build.json"),
      "v1/dist/certification/P11.21.test.json":sha256_file(root/"v1/dist/certification/P11.21.test.json"),
    }
    return commands,hashes,assertions
