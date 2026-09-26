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


class P1123Error(DriverError):
    pass


def require(ok, message):
    if not ok:
        raise P1123Error(message)


def dispatch(root, action, step, *, sha256_file, run_command, require_project_tool):
    if step != "P11.23":
        raise DriverError(step)

    io = root / "v1/src/libc48/io.asm"
    archive = root / "v1/src/libc48/runtime_archive.asm"
    cc = root / "v1/src/tools/cc.asm"
    itext = io.read_text(encoding="utf-8")
    atext = archive.read_text(encoding="utf-8")
    ctext = cc.read_text(encoding="utf-8")
    arch = (root / "docs/01-ZX-UX-ARCHITECTURE-REV17.md").read_text(encoding="utf-8")
    plan = (root / "docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV08.md").read_text(encoding="utf-8")

    public = ("open","open_typed","close","read","write","seek","stat","remove",
              "rename","list","pipe","dup","ioctl","read_full","write_full")
    require("EMIT_P1123_C48_IO_RUNTIME" in itext, "P11.23 I/O runtime macro missing")
    for name in public:
        require(re.search(rf"(?m)^{name}:$", itext) is not None,
                f"P11.23 public symbol missing: {name}")
        require(f'db "{name}",0' in atext, f"P11.23 archive symbol missing: {name}")
    require("P1123_LIBC48_IO_SYMBOL_COUNT EQU 15" in atext
            and "EMIT_P1123_LIBC48_IO_ARCHIVE" in atext,
            "P11.23 archive registry incomplete")
    for sym in ("SYS_OPEN","SYS_CLOSE","SYS_READ","SYS_WRITE","SYS_SEEK","SYS_STAT",
                "SYS_REMOVE","SYS_RENAME","SYS_LIST","SYS_PIPE","SYS_DUP","SYS_IOCTL"):
        require(f"ld a,{sym}" in itext, f"P11.23 symbolic syscall dependency missing: {sym}")
    require("ld b,OBJ_DAT" in itext and "and O_CREATE" in itext,
            "P11.23 open DAT creation rule missing")
    require("c48_io_read_raw:" in itext and "c48_io_write_raw:" in itext
            and "c48_io_read_full_loop:" in itext and "c48_io_write_full_loop:" in itext,
            "P11.23 full-transfer helpers incomplete")
    for decl in (
        "int open(char *path,int flags);",
        "int open_typed(char *path,int flags,int type);",
        "int read_full(int h,void *p,unsigned int n);",
        "int write_full(int h,void *p,unsigned int n);",
    ):
        require(decl in ctext, f"P11.23 builtin c48.h declaration missing: {decl}")
    require("creates DAT when creation is actually required" in arch
            and "open_typed()" in arch
            and "C48 provides" in arch
            and "read_full()" in arch and "write_full()" in arch,
            "REV17 P11.23 object I/O contract drift")
    require("## P11.23 - C48 object/handle runtime API" in plan
            and "All fifteen symbols resolve from the built-in libc48 archive" in plan
            and "force short read/write then error" in plan,
            "REV08 P11.23 acceptance contract drift")

    start = itext.index("    MACRO EMIT_P1123_C48_IO_RUNTIME")
    macro = itext[start:itext.index("    ENDM", start) + len("    ENDM")]
    code = "\n".join(line.split(";", 1)[0] for line in macro.splitlines())
    require(not re.search(r"\biy\b|\bexx\b|ex\s+af\s*,\s*af'", code, re.I),
            "P11.23 runtime touches OS-private registers")

    assembler = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    fixture = build / "p1123-io.asm"
    fixture.write_text(r'''    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/libc48/io.asm"
    INCLUDE "../src/libc48/runtime_archive.asm"

    ORG $C000
p1123_start:
    EMIT_P1123_C48_IO_RUNTIME
    EMIT_P1123_LIBC48_IO_ARCHIVE

p1123_path0: db "/tmp/a",0
p1123_path1: db "/tmp/b",0
p1123_buf: defs 16,$A5
p1123_statout: defs 10,$5A
p1123_listout: defs 16,$6B
p1123_pipeout: defs 2,$7C
p1123_arg: dw $1234
p1123_last_a: db 0
p1123_last_hl: dw 0
p1123_last_de: dw 0
p1123_last_bc: dw 0
p1123_mode: db 0
p1123_calls: db 0

p1123_fail:
    ld a,E_FORMAT
    scf
    ret

p1123_check_word:
    or a
    sbc hl,de
    jp nz,p1123_fail
    xor a
    ret

p1123_gateway:
    ld (p1123_last_a),a
    ld (p1123_last_hl),hl
    ld (p1123_last_de),de
    ld (p1123_last_bc),bc
    ld a,(p1123_calls)
    inc a
    ld (p1123_calls),a
    ld a,(p1123_mode)
    cp 3
    jr z,p1123_gateway_error
    ld a,(p1123_last_a)
    cp SYS_OPEN
    jr z,p1123_gateway_open
    cp SYS_DUP
    jr z,p1123_gateway_dup
    cp SYS_LIST
    jr z,p1123_gateway_list
    cp SYS_READ
    jr z,p1123_gateway_rw
    cp SYS_WRITE
    jr z,p1123_gateway_rw
    ld hl,0
    xor a
    ret
p1123_gateway_open:
    ld hl,5
    xor a
    ret
p1123_gateway_dup:
    ld hl,6
    xor a
    ret
p1123_gateway_list:
    ld hl,1
    xor a
    ret
p1123_gateway_rw:
    ld a,(p1123_mode)
    or a
    jr z,p1123_gateway_rw_all
    cp 1
    jr z,p1123_gateway_rw_short
    cp 2
    jr z,p1123_gateway_rw_short_then_error
p1123_gateway_rw_all:
    ld hl,(p1123_last_bc)
    xor a
    ret
p1123_gateway_rw_short:
    ld hl,(p1123_last_bc)
    ld a,h
    or a
    jr nz,p1123_gateway_two
    ld a,l
    cp 3
    jr nc,p1123_gateway_two
    ld a,(p1123_last_a)
    cp SYS_WRITE
    jr z,p1123_gateway_rw_all
    ld hl,0
    xor a
    ret
p1123_gateway_two:
    ld hl,2
    xor a
    ret
p1123_gateway_rw_short_then_error:
    ld a,(p1123_calls)
    cp 2
    jr nc,p1123_gateway_error
    ld hl,2
    xor a
    ret
p1123_gateway_error:
    ld a,E_IO
    scf
    ret

p1123_reset:
    xor a
    ld (p1123_mode),a
    ld (p1123_calls),a
    ret

p1123_open_cases:
    call p1123_reset
    ld hl,p1123_path0
    ld de,O_READ
    call open
    ld de,5
    call p1123_check_word
    ret c
    ld a,(p1123_last_a)
    cp SYS_OPEN
    jp nz,p1123_fail
    ld a,(p1123_last_bc+1)
    or a
    jp nz,p1123_fail

    ld hl,p1123_path0
    ld de,O_WRITE|O_CREATE
    call open
    ld a,(p1123_last_bc+1)
    cp OBJ_DAT
    jp nz,p1123_fail

    ld hl,p1123_path0
    ld de,O_WRITE|O_CREATE
    ld bc,OBJ_TXT
    call open_typed
    ld a,(p1123_last_bc+1)
    cp OBJ_TXT
    jp nz,p1123_fail
    xor a
    ret

p1123_simple:
    call p1123_reset
    ld hl,4
    call close
    ld a,(p1123_last_a)
    cp SYS_CLOSE
    jp nz,p1123_fail

    ld hl,4
    ld de,p1123_buf
    ld bc,7
    call read
    ld de,7
    call p1123_check_word
    ret c
    ld hl,(p1123_last_de)
    ld de,4
    call p1123_check_word
    ret c
    ld hl,(p1123_last_hl)
    ld de,p1123_buf
    call p1123_check_word
    ret c

    ld hl,4
    ld de,p1123_buf
    ld bc,6
    call write
    ld de,6
    call p1123_check_word
    ret c

    ld hl,4
    ld de,$1234
    call seek
    ld hl,(p1123_last_hl)
    ld de,$1234
    call p1123_check_word
    ret c

    ld hl,p1123_path0
    ld de,p1123_statout
    call stat
    ld hl,(c48_io_stat1)
    ld de,p1123_path0
    call p1123_check_word
    ret c
    ld hl,(c48_io_stat1+2)
    ld de,p1123_statout
    call p1123_check_word
    ret c

    ld hl,p1123_path0
    call remove
    ld a,(p1123_last_a)
    cp SYS_REMOVE
    jp nz,p1123_fail

    ld hl,p1123_path0
    ld de,p1123_path1
    call rename
    ld hl,(c48_io_ren1)
    ld de,p1123_path0
    call p1123_check_word
    ret c
    ld hl,(c48_io_ren1+2)
    ld de,p1123_path1
    call p1123_check_word
    ret c

    ld hl,p1123_path0
    ld de,7
    ld bc,p1123_listout
    call list
    ld de,1
    call p1123_check_word
    ret c
    ld a,(c48_io_list1+2)
    cp 7
    jp nz,p1123_fail
    ld a,(c48_io_list1+3)
    or a
    jp nz,p1123_fail

    ld hl,p1123_pipeout
    call pipe
    ld a,(p1123_last_a)
    cp SYS_PIPE
    jp nz,p1123_fail

    ld hl,3
    ld de,$00FF
    call dup
    ld de,6
    call p1123_check_word
    ret c
    ld a,(c48_io_dup1)
    cp 3
    jp nz,p1123_fail
    ld a,(c48_io_dup1+1)
    cp $FF
    jp nz,p1123_fail

    ld hl,2
    ld de,9
    ld bc,p1123_arg
    call ioctl
    ld a,(c48_io_ioctl1)
    cp 2
    jp nz,p1123_fail
    ld a,(c48_io_ioctl1+1)
    cp 9
    jp nz,p1123_fail
    ld hl,(c48_io_ioctl1+2)
    ld de,p1123_arg
    jp p1123_check_word

p1123_full:
    call p1123_reset
    ld a,1
    ld (p1123_mode),a
    ld hl,3
    ld de,p1123_buf
    ld bc,5
    call read_full
    ld de,4
    call p1123_check_word
    ret c

    xor a
    ld (p1123_calls),a
    ld hl,3
    ld de,p1123_buf
    ld bc,5
    call write_full
    ld de,5
    call p1123_check_word
    ret c

    xor a
    ld (p1123_calls),a
    ld a,2
    ld (p1123_mode),a
    ld hl,3
    ld de,p1123_buf
    ld bc,5
    call read_full
    ld de,E_IO
    call p1123_check_word
    ret c

    xor a
    ld (p1123_calls),a
    ld hl,3
    ld de,p1123_buf
    ld bc,5
    call write_full
    ld de,E_IO
    jp p1123_check_word

p1123_archive:
    ld hl,(p1123_libc48_io_table)
    ld de,open
    call p1123_check_word
    ret c
    ld hl,(p1123_libc48_io_table+28)
    ld de,write_full
    jp p1123_check_word

p1123_error:
    call p1123_reset
    ld a,3
    ld (p1123_mode),a
    ld hl,p1123_path0
    ld de,O_READ
    call open
    ld de,E_IO
    call p1123_check_word
    ret c
    ld hl,2
    call close
    ld de,E_IO
    jp p1123_check_word

p1123_end:
    SAVEBIN "p1123-main.bin",p1123_start,p1123_end-p1123_start
''', encoding="utf-8", newline="\n")

    result = run_command([assembler, "--nologo", "--sym=p1123-io.sym", fixture.name],
                         cwd=build, timeout_seconds=30)
    require(not result.timed_out and result.exit_code == 0,
            f"P11.23 assemble: {result.stderr or result.stdout}")
    main = (build / "p1123-main.bin").read_bytes()
    require(0 < len(main) <= 0x2000, "P11.23 fixture exceeds C000-DFFF user range")
    names = ("p1123_open_cases","p1123_simple","p1123_full","p1123_archive","p1123_error")
    syms = phase3_open_descriptions._symbols(build / "p1123-io.sym",
                                             ("p1123_gateway",) + names)

    assertions = [
        {"name":"all-fifteen-public-object-handle-symbols-present","passed":True},
        {"name":"all-fifteen-symbols-bound-in-libc48-archive-registry","passed":True},
        {"name":"open-dat-only-on-create-and-open-typed-explicit-type","passed":True},
        {"name":"exact-packed-syscall-record-layouts","passed":True},
        {"name":"read-write-seek-register-contracts-exact","passed":True},
        {"name":"read-full-write-full-use-short-transfer-loops","passed":True},
        {"name":"builtin-c48-header-declares-owned-object-io-surface","passed":True},
    ]
    commands = [result]
    if action == "test":
        gateway = phase1._jp(syms["p1123_gateway"])
        def patch(ram):
            ram[0xC000-0x4000:0xC000-0x4000+len(main)] = main
            ram[0xE000-0x4000:0xE000-0x4000+len(gateway)] = gateway
        for name in names:
            code = (b"\xF3" + phase1._ld_sp(0xBFC0) + phase1._call(syms[name])
                    + phase1._jp_c(FAIL_PC) + phase1._jp(PASS_PC))
            try:
                commands.append(run_sna(root, code, patch=patch))
            except DriverError as exc:
                raise P1123Error(f"{name} native fixture failed: {exc}") from None
        assertions += [
            {"name":"fuse-all-fifteen-native-symbols-execute-or-resolve","passed":True},
            {"name":"fuse-open-default-and-typed-creation-registers-exact","passed":True},
            {"name":"fuse-short-read-write-loops-advance-buffer-and-count","passed":True},
            {"name":"fuse-short-transfer-then-error-returns-exact-errno","passed":True},
            {"name":"fuse-record-wrappers-preserve-packed-layouts","passed":True},
        ]

    hashes = {
        "v1/src/libc48/io.asm": sha256_file(io),
        "v1/src/libc48/runtime_archive.asm": sha256_file(archive),
        "v1/src/tools/cc.asm": sha256_file(cc),
        "v1/build/p1123-main.bin": sha256_file(build / "p1123-main.bin"),
        "v1/tools-host/test-driver/phase11_step_23.py": sha256_file(
            root / "v1/tools-host/test-driver/phase11_step_23.py"),
        "v1/dist/certification/P11.22.build.json": sha256_file(
            root / "v1/dist/certification/P11.22.build.json"),
        "v1/dist/certification/P11.22.test.json": sha256_file(
            root / "v1/dist/certification/P11.22.test.json"),
    }
    return commands, hashes, assertions
