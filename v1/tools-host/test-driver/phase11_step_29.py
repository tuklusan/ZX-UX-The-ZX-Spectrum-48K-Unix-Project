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
import phase10_obj1_header
import phase10_obj1_inspector
from driver_core import DriverError
from fuse_harness import FAIL_PC, PASS_PC, run_sna

class P1129Error(DriverError):
    pass

def require(ok, message):
    if not ok:
        raise P1129Error(message)

def _db(data: bytes) -> str:
    return ",".join("$" + format(byte, "02X") for byte in data)

def dispatch(root, action, step, *, sha256_file, run_command, require_project_tool):
    if step != "P11.29":
        raise DriverError(step)
    cc_path = root / "v1/src/tools/cc.asm"
    cc = cc_path.read_text(encoding="utf-8")
    arch = (root / "docs/01-ZX-UX-ARCHITECTURE-REV17.md").read_text(encoding="utf-8")
    plan = (root / "docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV08.md").read_text(encoding="utf-8")
    marker = "    MACRO EMIT_P1129_CC_TRANSACTION_ROUTINES"
    require(marker in cc, "P11.29 transaction macro missing")
    macro = cc[cc.index(marker):]
    macro = macro[:macro.index("    ENDM") + 8]
    code = "\n".join(line.split(";", 1)[0] for line in macro.splitlines())
    require("cp OBJ_C" in macro and "ld a,OBJ_OBJ" in macro,
            "P11.29 explicit source/output kernel types missing")
    require("cc_p1129_obj_suffix: db '.obj',0" in macro and "cp 'c'" in macro and "cp '.'" in macro,
            "P11.29 exact default suffix mapping missing")
    require("cc_p1129_temp_name:  db '/','t','m','p','/','.','c','c','0','.','0',0" in macro,
            "P11.29 exact temporary namespace missing")
    require("O_WRITE|O_CREATE|O_EXCL" in macro and "ld b,OBJ_OBJ" in macro,
            "P11.29 exclusive explicit-OBJ temporary creation missing")
    write_at = macro.index("ld a,SYS_WRITE")
    close_at = macro.index("call cc_p1129_close_temp", write_at)
    validate_at = macro.index("call cc_p1129_validate_candidate", close_at)
    rename_at = macro.index("ld a,SYS_RENAME", validate_at)
    require(write_at < close_at < validate_at < rename_at,
            "P11.29 write/close/validate/rename order drift")
    require("cc_p1129_owned" in macro and "ld a,SYS_REMOVE" in macro,
            "P11.29 owned-temporary cleanup missing")
    require("cc_p1129_unique_symbols:" in macro and "call cc_obj1_validate_relocs" in macro,
            "P11.29 complete serialized OBJ1 validation missing")
    require(not re.search(r"\biy\b|\bexx\b|ex\s+af\s*,\s*af'", code, re.I),
            "P11.29 uses OS-private registers")
    require("accepts exactly one C-typed input object." in arch and "/tmp/.cc<pid>.<n>" in arch
            and "The kernel never infers types from" in arch, "REV17 P11.29 transaction contract drift")
    require("## P11.29 - Compiler transactional output" in plan
            and "Write unique temp object then atomic rename" in plan
            and "Wrong input type, uppercase/missing" in plan,
            "REV08 P11.29 contract drift")

    candidate = phase10_obj1_header.build_obj(text=b"\xC9", bss=2)
    inspector = phase10_obj1_inspector.load_inspector(root)
    decoded = inspector.inspect_bytes(candidate)
    require(decoded["stored_length"] == len(candidate) and decoded["text_size"] == 1
            and decoded["bss_size"] == 2, "P11.29 host OBJ1 candidate mismatch")

    assembler = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    fixture = build / "p1129-transaction.asm"
    fixture.write_text(f'''    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/tools/cc.asm"
    ORG $C000
p1129_start:
    EMIT_P1128_CC_OBJ1_WRITER
    EMIT_P1129_CC_TRANSACTION_ROUTINES

p1129_source: db "hello.c",0
p1129_explicit_source: db "MiXSrc",0
p1129_explicit_name: db "MiX.Out",0
p1129_upper: db "hello.C",0
p1129_missing: db "hello",0
p1129_long_default: db "abcdefgh.c",0
p1129_long_output: db "12345678901",0
p1129_expected_default: db "hello.obj",0
p1129_expected_explicit: db "MiX.Out",0
p1129_name_out: defs 11,$CC
p1129_dest: db "old.obj",0
p1129_candidate: db {_db(candidate)}
p1129_candidate_end:
p1129_dest_bytes: defs 16,$A5
p1129_mode: db 0
p1129_open_calls: db 0
p1129_write_calls: db 0
p1129_close_calls: db 0
p1129_rename_calls: db 0
p1129_remove_calls: db 0

p1129_fail:
    ld a,E_FORMAT
    scf
    ret

p1129_clear_counters:
    xor a
    ld (p1129_open_calls),a
    ld (p1129_write_calls),a
    ld (p1129_close_calls),a
    ld (p1129_rename_calls),a
    ld (p1129_remove_calls),a
    ret

p1129_fill_dest:
    ld hl,p1129_dest_bytes
    ld b,16
    ld a,$A5
p1129_fill_dest_loop:
    ld (hl),a
    inc hl
    djnz p1129_fill_dest_loop
    ret

p1129_check_dest_a5:
    ld hl,p1129_dest_bytes
    ld b,16
p1129_check_dest_a5_loop:
    ld a,(hl)
    cp $A5
    jp nz,p1129_fail
    inc hl
    djnz p1129_check_dest_a5_loop
    xor a
    ret

p1129_check_dest_5a:
    ld hl,p1129_dest_bytes
    ld b,16
p1129_check_dest_5a_loop:
    ld a,(hl)
    cp $5A
    jp nz,p1129_fail
    inc hl
    djnz p1129_check_dest_5a_loop
    xor a
    ret

p1129_arm_candidate:
    ld a,1
    ld (p1129_candidate+4),a
    ld hl,p1129_candidate
    ld (cc_obj1_output_ptr),hl
    ld hl,p1129_candidate_end-p1129_candidate
    ld (cc_obj1_output_size),hl
    ld a,CC_OBJ1_COMMITTED
    ld (cc_obj1_commit_marker),a
    ret

p1129_reset:
    call p1129_clear_counters
    call p1129_fill_dest
    call p1129_arm_candidate
    xor a
    ld (p1129_mode),a
    ret

p1129_call:
    ld hl,p1129_dest
    ld de,p1129_candidate
    ld bc,p1129_candidate_end-p1129_candidate
    jp cc_p1129_publish

p1129_streq:
    ld a,(de)
    cp (hl)
    jp nz,p1129_fail
    or a
    ret z
    inc de
    inc hl
    jp p1129_streq

p1129_names_positive:
    ld c,1
    ld a,OBJ_C
    ld hl,p1129_source
    ld de,0
    ld ix,p1129_name_out
    call cc_p1129_names
    jp c,p1129_fail
    cp OBJ_OBJ
    jp nz,p1129_fail
    ld hl,p1129_name_out
    ld de,p1129_expected_default
    call p1129_streq
    ret c
    ld c,1
    ld a,OBJ_C
    ld hl,p1129_explicit_source
    ld de,p1129_explicit_name
    ld ix,p1129_name_out
    call cc_p1129_names
    jp c,p1129_fail
    cp OBJ_OBJ
    jp nz,p1129_fail
    ld hl,p1129_name_out
    ld de,p1129_expected_explicit
    call p1129_streq
    ret c
    xor a
    ret

p1129_expect_name_fail:
    call cc_p1129_names
    jp nc,p1129_fail
    cp E_FORMAT
    jp nz,p1129_fail
    xor a
    ret

p1129_names_negative:
    ld c,0
    ld a,OBJ_C
    ld hl,p1129_source
    ld de,0
    ld ix,p1129_name_out
    call p1129_expect_name_fail
    ret c
    ld c,1
    ld a,OBJ_TXT
    ld hl,p1129_source
    ld de,0
    ld ix,p1129_name_out
    call p1129_expect_name_fail
    ret c
    ld c,1
    ld a,OBJ_C
    ld hl,p1129_upper
    ld de,0
    ld ix,p1129_name_out
    call p1129_expect_name_fail
    ret c
    ld c,1
    ld a,OBJ_C
    ld hl,p1129_missing
    ld de,0
    ld ix,p1129_name_out
    call p1129_expect_name_fail
    ret c
    ld c,1
    ld a,OBJ_C
    ld hl,p1129_long_default
    ld de,0
    ld ix,p1129_name_out
    call p1129_expect_name_fail
    ret c
    ld c,1
    ld a,OBJ_C
    ld hl,p1129_explicit_source
    ld de,p1129_long_output
    ld ix,p1129_name_out
    call p1129_expect_name_fail
    ret c
    xor a
    ret

p1129_validate_direct:
    call p1129_reset
    call cc_p1129_validate_candidate
    ret

p1129_publish_raw:
    call p1129_reset
    jp p1129_call

p1129_publish_success:
    call p1129_reset
    call p1129_call
    jp c,p1129_fail
    call p1129_check_dest_5a
    ret c
    ld a,(p1129_open_calls)
    cp 1
    jp nz,p1129_fail
    ld a,(p1129_write_calls)
    cp 1
    jp nz,p1129_fail
    ld a,(p1129_close_calls)
    cp 1
    jp nz,p1129_fail
    ld a,(p1129_rename_calls)
    cp 1
    jp nz,p1129_fail
    ld a,(p1129_remove_calls)
    or a
    jp nz,p1129_fail
    ld a,(cc_p1129_temp_name+8)
    cp '3'
    jp nz,p1129_fail
    ld a,(cc_p1129_temp_name+10)
    cp '0'
    jp nz,p1129_fail
    xor a
    ret

p1129_collision:
    call p1129_reset
    ld a,1
    ld (p1129_mode),a
    call p1129_call
    jp c,p1129_fail
    ld a,(p1129_open_calls)
    cp 2
    jp nz,p1129_fail
    ld a,(cc_p1129_temp_name+10)
    cp '1'
    jp nz,p1129_fail
    ld a,(p1129_remove_calls)
    or a
    jp nz,p1129_fail
    call p1129_check_dest_5a
    ret

p1129_compile_fail:
    call p1129_reset
    ld hl,p1129_dest
    ld de,p1129_candidate
    ld bc,p1129_candidate_end-p1129_candidate
    ld a,E_FORMAT
    call cc_p1129_commit
    jp nc,p1129_fail
    cp E_FORMAT
    jp nz,p1129_fail
    ld a,(p1129_open_calls)
    or a
    jp nz,p1129_fail
    call p1129_check_dest_a5
    ret

p1129_alloc_fail:
    call p1129_reset
    ld a,2
    ld (p1129_mode),a
    call p1129_call
    jp nc,p1129_fail
    cp E_NOSPC
    jp nz,p1129_fail
    ld a,(p1129_write_calls)
    or a
    jp nz,p1129_fail
    ld a,(p1129_remove_calls)
    or a
    jp nz,p1129_fail
    call p1129_check_dest_a5
    ret

p1129_write_fail:
    call p1129_reset
    ld a,3
    ld (p1129_mode),a
    call p1129_call
    jp nc,p1129_fail
    cp E_NOSPC
    jp nz,p1129_fail
    ld a,(p1129_rename_calls)
    or a
    jp nz,p1129_fail
    ld a,(p1129_remove_calls)
    cp 1
    jp nz,p1129_fail
    call p1129_check_dest_a5
    ret

p1129_close_fail:
    call p1129_reset
    ld a,4
    ld (p1129_mode),a
    call p1129_call
    jp nc,p1129_fail
    cp E_IO
    jp nz,p1129_fail
    ld a,(p1129_close_calls)
    cp 2
    jp nz,p1129_fail
    ld a,(p1129_remove_calls)
    cp 1
    jp nz,p1129_fail
    ld a,(p1129_rename_calls)
    or a
    jp nz,p1129_fail
    call p1129_check_dest_a5
    ret

p1129_postvalidate_fail:
    call p1129_reset
    ld a,5
    ld (p1129_mode),a
    call p1129_call
    jp nc,p1129_fail
    cp E_FORMAT
    jp nz,p1129_fail
    ld a,(p1129_rename_calls)
    or a
    jp nz,p1129_fail
    ld a,(p1129_remove_calls)
    cp 1
    jp nz,p1129_fail
    call p1129_check_dest_a5
    ret

p1129_rename_fail:
    call p1129_reset
    ld a,6
    ld (p1129_mode),a
    call p1129_call
    jp nc,p1129_fail
    cp E_BUSY
    jp nz,p1129_fail
    ld a,(p1129_rename_calls)
    cp 1
    jp nz,p1129_fail
    ld a,(p1129_remove_calls)
    cp 1
    jp nz,p1129_fail
    call p1129_check_dest_a5
    ret

p1129_collision_exhausted:
    call p1129_reset
    ld a,7
    ld (p1129_mode),a
    call p1129_call
    jp nc,p1129_fail
    cp E_EXIST
    jp nz,p1129_fail
    ld a,(p1129_open_calls)
    cp 10
    jp nz,p1129_fail
    ld a,(p1129_remove_calls)
    or a
    jp nz,p1129_fail
    call p1129_check_dest_a5
    ret

p1129_short_write:
    call p1129_reset
    ld a,8
    ld (p1129_mode),a
    call p1129_call
    jp nc,p1129_fail
    cp E_IO
    jp nz,p1129_fail
    ld a,(p1129_remove_calls)
    cp 1
    jp nz,p1129_fail
    ld a,(p1129_rename_calls)
    or a
    jp nz,p1129_fail
    call p1129_check_dest_a5
    ret

p1129_end:
    SAVEBIN "p1129-main.bin",p1129_start,p1129_end-p1129_start

    ORG $E000
p1129_gateway:
    cp SYS_GETPID
    jp z,p1129_sys_getpid
    cp SYS_OPEN
    jp z,p1129_sys_open
    cp SYS_WRITE
    jp z,p1129_sys_write
    cp SYS_CLOSE
    jp z,p1129_sys_close
    cp SYS_RENAME
    jp z,p1129_sys_rename
    cp SYS_REMOVE
    jp z,p1129_sys_remove
    ld a,E_NOTSUP
    scf
    ret

p1129_sys_getpid:
    ld hl,3
    xor a
    ret

p1129_check_temp:
    ld de,p1129_temp_prefix
    ld b,8
p1129_check_temp_prefix:
    ld a,(de)
    cp (hl)
    jp nz,p1129_sys_format
    inc de
    inc hl
    djnz p1129_check_temp_prefix
    ld a,(hl)
    cp '3'
    jp nz,p1129_sys_format
    inc hl
    ld a,(hl)
    cp '.'
    jp nz,p1129_sys_format
    inc hl
    ld a,(hl)
    cp '0'
    jp c,p1129_sys_format
    cp '9'+1
    jp nc,p1129_sys_format
    inc hl
    ld a,(hl)
    or a
    jp nz,p1129_sys_format
    xor a
    ret

p1129_sys_open:
    push bc
    push hl
    call p1129_check_temp
    pop hl
    pop bc
    ret c
    ld a,c
    cp O_WRITE|O_CREATE|O_EXCL
    jp nz,p1129_sys_format
    ld a,b
    cp OBJ_OBJ
    jp nz,p1129_sys_format
    ld a,(p1129_open_calls)
    inc a
    ld (p1129_open_calls),a
    ld a,(p1129_mode)
    cp 7
    jp z,p1129_sys_exist
    cp 2
    jp z,p1129_sys_nospc
    cp 1
    jp nz,p1129_sys_open_ok
    ld a,(p1129_open_calls)
    cp 1
    jp z,p1129_sys_exist
p1129_sys_open_ok:
    ld hl,4
    xor a
    ret

p1129_sys_write:
    ld a,(p1129_write_calls)
    inc a
    ld (p1129_write_calls),a
    ld a,d
    or a
    jp nz,p1129_sys_format
    ld a,e
    cp 4
    jp nz,p1129_sys_format
    ld de,p1129_candidate
    or a
    sbc hl,de
    jp nz,p1129_sys_format
    ld hl,p1129_candidate_end-p1129_candidate
    or a
    sbc hl,bc
    jp nz,p1129_sys_format
    ld a,(p1129_mode)
    cp 3
    jp z,p1129_sys_nospc
    cp 5
    jp nz,p1129_sys_write_short_check
    ld a,2
    ld (p1129_candidate+4),a
p1129_sys_write_short_check:
    ld a,(p1129_mode)
    cp 8
    jp nz,p1129_sys_write_ok
    push bc
    pop hl
    dec hl
    xor a
    ret
p1129_sys_write_ok:
    push bc
    pop hl
    xor a
    ret

p1129_sys_close:
    ld a,(p1129_close_calls)
    inc a
    ld (p1129_close_calls),a
    ld a,h
    or a
    jp nz,p1129_sys_format
    ld a,l
    cp 4
    jp nz,p1129_sys_format
    ld a,(p1129_mode)
    cp 4
    jp nz,p1129_sys_close_ok
    ld a,(p1129_close_calls)
    cp 1
    jp nz,p1129_sys_close_ok
    ld a,E_IO
    scf
    ret
p1129_sys_close_ok:
    xor a
    ret

p1129_sys_rename:
    ld a,(p1129_rename_calls)
    inc a
    ld (p1129_rename_calls),a
    ld e,(hl)
    inc hl
    ld d,(hl)
    inc hl
    ld c,(hl)
    inc hl
    ld b,(hl)
    push bc
    ld h,d
    ld l,e
    ld de,cc_p1129_temp_name
    or a
    sbc hl,de
    pop de
    jp nz,p1129_sys_format
    ld hl,p1129_dest
    or a
    sbc hl,de
    jp nz,p1129_sys_format
    ld a,(p1129_mode)
    cp 6
    jp z,p1129_sys_busy
    ld hl,p1129_dest_bytes
    ld b,16
    ld a,$5A
p1129_rename_fill:
    ld (hl),a
    inc hl
    djnz p1129_rename_fill
    xor a
    ret

p1129_sys_remove:
    ld a,(p1129_remove_calls)
    inc a
    ld (p1129_remove_calls),a
    ld de,cc_p1129_temp_name
    or a
    sbc hl,de
    jp nz,p1129_sys_format
    xor a
    ret

p1129_sys_exist:
    ld a,E_EXIST
    scf
    ret
p1129_sys_nospc:
    ld a,E_NOSPC
    scf
    ret
p1129_sys_busy:
    ld a,E_BUSY
    scf
    ret
p1129_sys_format:
    ld a,E_FORMAT
    scf
    ret

p1129_temp_prefix: db '/','t','m','p','/','.','c','c'
p1129_gateway_end:
    SAVEBIN "p1129-gateway.bin",p1129_gateway,p1129_gateway_end-p1129_gateway
''', encoding="utf-8", newline="\n")

    assembled = run_command([assembler, "--nologo", "--sym=p1129-transaction.sym", fixture.name],
                            cwd=build, timeout_seconds=30)
    require(not assembled.timed_out and assembled.exit_code == 0,
            f"P11.29 assemble: {assembled.stderr or assembled.stdout}")
    main = (build / "p1129-main.bin").read_bytes()
    gateway = (build / "p1129-gateway.bin").read_bytes()
    require(0 < len(main) <= 0x2000, "P11.29 fixture overlaps syscall gateway")
    names = ("p1129_names_positive","p1129_names_negative","p1129_validate_direct",
             "p1129_publish_raw","p1129_publish_success",
             "p1129_collision","p1129_compile_fail","p1129_alloc_fail","p1129_write_fail",
             "p1129_close_fail","p1129_postvalidate_fail","p1129_rename_fail",
             "p1129_collision_exhausted","p1129_short_write")
    syms = phase3_open_descriptions._symbols(build / "p1129-transaction.sym", names)
    assertions = [
        {"name":"exactly-one-kernel-typed-c-input-required","passed":True},
        {"name":"default-exact-lowercase-c-to-obj-name-bounded","passed":True},
        {"name":"explicit-output-exact-case-sensitive-and-explicit-obj-type","passed":True},
        {"name":"exclusive-unique-temp-and-owned-cleanup-contract","passed":True},
        {"name":"complete-write-close-validate-atomic-rename-order","passed":True},
        {"name":"serialized-obj1-revalidated-before-rename","passed":True},
        {"name":"host-candidate-valid-obj1","passed":True},
    ]
    commands = [assembled]
    if action == "test":
        def patch(ram):
            ram[0xC000-0x4000:0xC000-0x4000+len(main)] = main
            ram[0xE000-0x4000:0xE000-0x4000+len(gateway)] = gateway
        for name in names:
            code = b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._call(syms[name])+phase1._jp_c(FAIL_PC)+phase1._jp(PASS_PC)
            try:
                commands.append(run_sna(root, code, patch=patch))
            except DriverError as exc:
                raise P1129Error(f"{name} native fixture failed: {exc}") from None
        assertions += [
            {"name":"fuse-default-and-explicit-name-resolution-exact","passed":True},
            {"name":"fuse-wrong-type-case-suffix-and-name-bounds-rejected","passed":True},
            {"name":"fuse-success-renames-only-after-close-and-revalidation","passed":True},
            {"name":"fuse-eexist-retries-without-removing-unknown-temp","passed":True},
            {"name":"fuse-compile-failure-has-no-output-side-effect","passed":True},
            {"name":"fuse-allocation-failure-preserves-prior-destination","passed":True},
            {"name":"fuse-write-and-short-write-failures-preserve-prior-destination","passed":True},
            {"name":"fuse-close-failure-preserves-prior-destination","passed":True},
            {"name":"fuse-postwrite-invalid-obj1-blocks-rename","passed":True},
            {"name":"fuse-rename-failure-preserves-prior-destination","passed":True},
            {"name":"fuse-temp-collision-exhaustion-does-not-remove-unknown-temps","passed":True},
        ]
    hashes = {
        "v1/src/tools/cc.asm":sha256_file(cc_path),
        "v1/build/p1129-main.bin":sha256_file(build/"p1129-main.bin"),
        "v1/build/p1129-gateway.bin":sha256_file(build/"p1129-gateway.bin"),
        "v1/tools-host/inspect-obj/inspect.py":sha256_file(root/"v1/tools-host/inspect-obj/inspect.py"),
        "v1/tools-host/test-driver/phase11_step_29.py":sha256_file(root/"v1/tools-host/test-driver/phase11_step_29.py"),
        "v1/dist/certification/P11.28.build.json":sha256_file(root/"v1/dist/certification/P11.28.build.json"),
        "v1/dist/certification/P11.28.test.json":sha256_file(root/"v1/dist/certification/P11.28.test.json"),
    }
    return commands, hashes, assertions
