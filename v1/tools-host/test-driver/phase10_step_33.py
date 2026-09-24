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

import phase1
import phase3_open_descriptions
from driver_core import DriverError
from fuse_harness import PASS_PC, FAIL_PC, run_sna


class P1033Error(DriverError):
    pass


def require(ok, msg):
    if not ok:
        raise P1033Error(msg)


GOLDEN = bytes.fromhex("4d45583101001800030000000200400001001b003b03fda20100c90000")


def db(data):
    return ",".join(f"$%02X" % b for b in data)


def dispatch(root, action, step, *, sha256_file, run_command, require_project_tool):
    if step != "P10.33":
        raise DriverError(step)
    source = (root / "tools/ld.asm").read_text(encoding="utf-8")
    assertions = [
        {"name":"exclusive-bin-temp","passed":"O_WRITE|O_CREATE|O_EXCL" in source and "ld_p1033_temp_name: db '/','t','m','p','/','.','l','d'" in source and "ld b,OBJ_BIN" in source},
        {"name":"only-eexist-retried","passed":"cp E_EXIST" in source and "ld_p1033_open_retry:" in source},
        {"name":"write-close-revalidate-rename","passed":source.index("ld_p1033_write_complete:") < source.index("call ld_p1033_close_temp", source.index("ld_p1033_write_complete:")) < source.index("call ld_p1033_validate_mex1", source.index("ld_p1033_write_complete:")) < source.index("ld a,SYS_RENAME", source.index("ld_p1033_write_complete:"))},
        {"name":"owned-temp-cleanup","passed":"ld_p1033_owned" in source and "ld a,SYS_REMOVE" in source},
        {"name":"output-name-1-to-10-case-exact","passed":"ld_p1033_validate_name:" in source and "no case folding" in source},
    ]
    require(all(a["passed"] for a in assertions), "P10.33 static transaction contract failure")

    assembler = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    fixture = build / "p1033-transaction.asm"
    fixture.write_text(f"""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../../tools/ld.asm"
    ORG $C000
fixture:
    EMIT_P10_LD_TRANSACTION_ROUTINES

p1033_dest: db "output",0
p1033_long: db "12345678901",0
p1033_candidate: db {db(GOLDEN)}
p1033_candidate_end:
p1033_mode: db 0
p1033_open_calls: db 0
p1033_write_calls: db 0
p1033_close_calls: db 0
p1033_rename_calls: db 0
p1033_remove_calls: db 0
p1033_dest_marker: db $A5

p1033_reset:
    xor a
    ld (p1033_mode),a
    ld (p1033_open_calls),a
    ld (p1033_write_calls),a
    ld (p1033_close_calls),a
    ld (p1033_rename_calls),a
    ld (p1033_remove_calls),a
    ld a,$A5
    ld (p1033_dest_marker),a
    ld a,1
    ld (p1033_candidate+4),a
    ret

p1033_call:
    ld hl,p1033_dest
    ld de,p1033_candidate
    ld bc,p1033_candidate_end-p1033_candidate
    jp ld_p1033_publish

p1033_fail:
    ld a,E_FORMAT
    scf
    ret

p1033_success:
    call p1033_reset
    call p1033_call
    ret c
    ld a,(p1033_dest_marker)
    cp $5A
    jp nz,p1033_fail
    ld a,(p1033_open_calls)
    cp 1
    jp nz,p1033_fail
    ld a,(p1033_write_calls)
    cp 1
    jp nz,p1033_fail
    ld a,(p1033_close_calls)
    cp 1
    jp nz,p1033_fail
    ld a,(p1033_rename_calls)
    cp 1
    jp nz,p1033_fail
    xor a
    ret

p1033_collision:
    call p1033_reset
    ld a,1
    ld (p1033_mode),a
    call p1033_call
    ret c
    ld a,(p1033_open_calls)
    cp 2
    jp nz,p1033_fail
    ld a,(ld_p1033_temp_name+10)
    cp '1'
    jp nz,p1033_fail
    xor a
    ret

p1033_write_fail:
    call p1033_reset
    ld a,2
    ld (p1033_mode),a
    call p1033_call
    jp nc,p1033_fail
    cp E_NOSPC
    jp nz,p1033_fail
    ld a,(p1033_dest_marker)
    cp $A5
    jp nz,p1033_fail
    ld a,(p1033_rename_calls)
    or a
    jp nz,p1033_fail
    ld a,(p1033_remove_calls)
    cp 1
    jp nz,p1033_fail
    xor a
    ret

p1033_rename_fail:
    call p1033_reset
    ld a,3
    ld (p1033_mode),a
    call p1033_call
    jp nc,p1033_fail
    cp E_BUSY
    jp nz,p1033_fail
    ld a,(p1033_dest_marker)
    cp $A5
    jp nz,p1033_fail
    ld a,(p1033_remove_calls)
    cp 1
    jp nz,p1033_fail
    xor a
    ret

p1033_invalid:
    call p1033_reset
    ld a,2
    ld (p1033_candidate+4),a
    call p1033_call
    jp nc,p1033_fail
    cp E_FORMAT
    jp nz,p1033_fail
    ld a,1
    ld (p1033_candidate+4),a
    ld a,(p1033_open_calls)
    or a
    jp nz,p1033_fail
    xor a
    ret

p1033_long_name:
    call p1033_reset
    ld hl,p1033_long
    ld de,p1033_candidate
    ld bc,p1033_candidate_end-p1033_candidate
    call ld_p1033_publish
    jp nc,p1033_fail
    cp E_FORMAT
    jp nz,p1033_fail
    ld a,(p1033_open_calls)
    or a
    jp nz,p1033_fail
    xor a
    ret

fixture_end:
    SAVEBIN "p1033-main.bin",fixture,fixture_end-fixture

    ORG $E000
p1033_gateway:
    cp SYS_GETPID
    jr z,p1033_getpid
    cp SYS_OPEN
    jr z,p1033_open
    cp SYS_WRITE
    jr z,p1033_write
    cp SYS_CLOSE
    jr z,p1033_close
    cp SYS_RENAME
    jr z,p1033_rename
    cp SYS_REMOVE
    jr z,p1033_remove
    ld a,E_NOTSUP
    scf
    ret
p1033_getpid:
    ld hl,3
    xor a
    ret
p1033_open:
    ld a,(p1033_open_calls)
    inc a
    ld (p1033_open_calls),a
    ld a,c
    cp O_WRITE|O_CREATE|O_EXCL
    jr nz,p1033_gw_format
    ld a,b
    cp OBJ_BIN
    jr nz,p1033_gw_format
    ld a,(p1033_mode)
    cp 1
    jr nz,p1033_open_ok
    ld a,(p1033_open_calls)
    cp 1
    jr nz,p1033_open_ok
    ld a,E_EXIST
    scf
    ret
p1033_open_ok:
    ld hl,4
    xor a
    ret
p1033_write:
    ld a,(p1033_write_calls)
    inc a
    ld (p1033_write_calls),a
    ld a,(p1033_mode)
    cp 2
    jr z,p1033_nospc
    push bc
    pop hl
    xor a
    ret
p1033_close:
    ld a,(p1033_close_calls)
    inc a
    ld (p1033_close_calls),a
    xor a
    ret
p1033_rename:
    ld a,(p1033_rename_calls)
    inc a
    ld (p1033_rename_calls),a
    ld a,(p1033_mode)
    cp 3
    jr z,p1033_busy
    ld a,$5A
    ld (p1033_dest_marker),a
    xor a
    ret
p1033_remove:
    ld a,(p1033_remove_calls)
    inc a
    ld (p1033_remove_calls),a
    xor a
    ret
p1033_nospc:
    ld a,E_NOSPC
    scf
    ret
p1033_busy:
    ld a,E_BUSY
    scf
    ret
p1033_gw_format:
    ld a,E_FORMAT
    scf
    ret
p1033_gateway_end:
    SAVEBIN "p1033-gateway.bin",p1033_gateway,p1033_gateway_end-p1033_gateway
""", encoding="utf-8", newline="\n")

    result = run_command([assembler, "--nologo", "--sym=p1033-transaction.sym", fixture.name], cwd=build, timeout_seconds=30)
    require(not result.timed_out and result.exit_code == 0, f"P10.33 assemble: {result.stderr or result.stdout}")
    main = (build / "p1033-main.bin").read_bytes()
    gateway = (build / "p1033-gateway.bin").read_bytes()
    require(len(main) <= 0x2000, "P10.33 fixture overlaps syscall gateway")
    if action == "test":
        names = ("p1033_success","p1033_collision","p1033_write_fail","p1033_rename_fail","p1033_invalid","p1033_long_name")
        syms = phase3_open_descriptions._symbols(build / "p1033-transaction.sym", names)
        def patch(ram):
            ram[0xC000-0x4000:0xC000-0x4000+len(main)] = main
            ram[0xE000-0x4000:0xE000-0x4000+len(gateway)] = gateway
        for name in names:
            code = b"\xF3" + phase1._ld_sp(0xBFC0) + phase1._call(syms[name]) + phase1._jp_c(FAIL_PC) + phase1._jp(PASS_PC)
            run_sna(root, code, patch=patch)
        assertions += [
            {"name":"fuse-atomic-success","passed":True},
            {"name":"fuse-temp-collision-safe","passed":True},
            {"name":"fuse-write-failure-preserves-prior-output","passed":True},
            {"name":"fuse-rename-failure-preserves-prior-output","passed":True},
            {"name":"fuse-preflight-invalid-mex1-no-output-mutation","passed":True},
            {"name":"fuse-overlength-output-name-rejected","passed":True},
        ]
    hashes = {
        "tools/ld.asm": sha256_file(root / "tools/ld.asm"),
        "v1/build/p1033-main.bin": sha256_file(build / "p1033-main.bin"),
        "v1/build/p1033-gateway.bin": sha256_file(build / "p1033-gateway.bin"),
        "v1/tools-host/test-driver/phase10_step_33.py": sha256_file(root / "v1/tools-host/test-driver/phase10_step_33.py"),
        "v1/dist/certification/P10.32.build.json": sha256_file(root / "v1/dist/certification/P10.32.build.json"),
        "v1/dist/certification/P10.32.test.json": sha256_file(root / "v1/dist/certification/P10.32.test.json"),
    }
    return [result], hashes, assertions
