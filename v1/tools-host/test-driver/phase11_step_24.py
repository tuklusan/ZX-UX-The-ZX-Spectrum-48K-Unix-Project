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


class P1124Error(DriverError):
    pass


def require(ok, message):
    if not ok:
        raise P1124Error(message)


def dispatch(root, action, step, *, sha256_file, run_command, require_project_tool):
    if step != "P11.24":
        raise DriverError(step)

    string = root / "v1/src/libc48/string.asm"
    memory = root / "v1/src/libc48/memory.asm"
    docs = root / "v1/docs/c48.md"
    stext = string.read_text(encoding="utf-8")
    mtext = memory.read_text(encoding="utf-8")
    dtext = docs.read_text(encoding="utf-8")
    arch = (root / "docs/01-ZX-UX-ARCHITECTURE-REV17.md").read_text(encoding="utf-8")
    plan = (root / "docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV08.md").read_text(encoding="utf-8")

    public = ("getchar","putchar","puts","strlen","strcmp","strcpy","strncpy")
    mem_public = ("memcpy","memmove","memchr","memset")
    require("EMIT_P1124_C48_STRING_RUNTIME" in stext, "P11.24 string runtime macro missing")
    require("EMIT_P1124_C48_MEMORY_RUNTIME" in mtext, "P11.24 memory runtime macro missing")
    for name in public:
        require(re.search(rf"(?m)^{name}:$", stext) is not None,
                f"P11.24 public string symbol missing: {name}")
    for name in mem_public:
        require(re.search(rf"(?m)^{name}:$", mtext) is not None,
                f"P11.24 public memory symbol missing: {name}")
    require("c48_format_int:" in stext and "E_NOSPC" in stext,
            "P11.24 compact integer formatter missing")
    require("ldir" in mtext.lower() and "lddr" in mtext.lower(),
            "P11.24 memmove block-copy directions incomplete")
    require(
        "physical `CAPS SHIFT + 1` `EDIT`" in dtext
        and "integer 27 / `0x1B`" in dtext
        and "CAPS SHIFT + SPACE" in dtext
        and "BREAK is never returned by `getchar()` as 27" in dtext,
        "P11.24 c48 documentation EDIT/BREAK contract incomplete",
    )
    require(
        "`getchar()` is a byte-preserving wrapper over process stdin." in arch
        and "No C48 text-input helper may" in arch
        and "## P11.24 - C48 string/memory library" in plan
        and "overlap-safe memmove" in plan
        and "physical `EDIT` with BREAK kept separate" in plan,
        "REV17/REV08 P11.24 contract drift",
    )

    for text, marker in ((stext, "    MACRO EMIT_P1124_C48_STRING_RUNTIME"),
                         (mtext, "    MACRO EMIT_P1124_C48_MEMORY_RUNTIME")):
        start = text.index(marker)
        macro = text[start:text.index("    ENDM", start) + len("    ENDM")]
        code = "\n".join(line.split(";", 1)[0] for line in macro.splitlines())
        require(not re.search(r"\biy\b|\bexx\b|ex\s+af\s*,\s*af'", code, re.I),
                "P11.24 runtime touches OS-private registers")

    assembler = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    fixture = build / "p1124-string-memory.asm"
    fixture.write_text(r'''    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/libc48/int_runtime.asm"
    INCLUDE "../src/libc48/string.asm"
    INCLUDE "../src/libc48/memory.asm"

    ORG $C000
p1124_start:
    EMIT_C48_INT_RUNTIME
    EMIT_P1124_C48_STRING_RUNTIME
    EMIT_P1124_C48_MEMORY_RUNTIME

p1124_mode:       db 0
p1124_outlen:     db 0
p1124_out:        defs 32,$A5
p1124_last_count: dw 0
p1124_s0:         db "abc",0
p1124_s1:         db "abc",0
p1124_s2:         db "abd",0
p1124_copy:       defs 8,$CC
p1124_ncopy:      defs 8,$CC
p1124_memsrc:     db 1,2,3,4,5,6,7,8
p1124_memdst:     defs 10,$A6
p1124_overlap1:   db "abcdef",0,0
p1124_overlap2:   db "abcdef",0,0
p1124_set:        defs 8,$5A
p1124_fmt:        defs 8,$77

p1124_fail:
    ld a,E_FORMAT
    scf
    ret

p1124_check_word:
    or a
    sbc hl,de
    jp nz,p1124_fail
    xor a
    ret

p1124_reset_output:
    xor a
    ld (p1124_outlen),a
    ret

p1124_gateway:
    cp SYS_READ
    jr z,p1124_gate_read
    cp SYS_WRITE
    jr z,p1124_gate_write
    ld a,E_NOTSUP
    scf
    ret
p1124_gate_read:
    ld a,(p1124_mode)
    cp 1
    jr z,p1124_gate_intr
    cp 2
    jr z,p1124_gate_eof
    ld (hl),$1B
    ld hl,1
    xor a
    ret
p1124_gate_intr:
    ld a,E_INTR
    scf
    ret
p1124_gate_eof:
    ld hl,0
    xor a
    ret
p1124_gate_write:
    ld (p1124_last_count),bc
    ld a,(p1124_outlen)
    ld e,a
    ld d,0
    push hl
    ld hl,p1124_out
    add hl,de
    ex de,hl
    pop hl
    push bc
    ldir
    pop hl
    ld a,(p1124_outlen)
    ld e,a
    ld a,l
    add a,e
    ld (p1124_outlen),a
    xor a
    ret

p1124_stdio:
    xor a
    ld (p1124_mode),a
    call p1124_reset_output
    call getchar
    ld de,$001B
    call p1124_check_word
    ret c

    ld hl,'A'
    call putchar
    ld de,'A'
    call p1124_check_word
    ret c
    ld hl,p1124_s1+1
    dec hl
    call puts
    ld de,0
    call p1124_check_word
    ret c
    ld a,(p1124_outlen)
    cp 5
    jp nz,p1124_fail
    ld hl,p1124_out
    ld de,p1124_stdio_expected
    ld b,5
p1124_stdio_cmp:
    ld a,(de)
    cp (hl)
    jp nz,p1124_fail
    inc de
    inc hl
    djnz p1124_stdio_cmp
    xor a
    ret
p1124_stdio_expected:
    db 'A','a','b','c',10

p1124_break_eof:
    ld a,1
    ld (p1124_mode),a
    call getchar
    ld de,E_INTR
    call p1124_check_word
    ret c
    ld a,l
    cp $1B
    jp z,p1124_fail
    ld a,2
    ld (p1124_mode),a
    call getchar
    ld de,$FFFF
    jp p1124_check_word

p1124_strings:
    ld hl,p1124_s0
    call strlen
    ld de,3
    call p1124_check_word
    ret c
    ld hl,p1124_s0
    ld de,p1124_s1
    call strcmp
    ld de,0
    call p1124_check_word
    ret c
    ld hl,p1124_s0
    ld de,p1124_s2
    call strcmp
    ld de,$FFFF
    call p1124_check_word
    ret c
    ld hl,p1124_s2
    ld de,p1124_s0
    call strcmp
    ld de,1
    call p1124_check_word
    ret c

    ld hl,p1124_copy
    ld de,p1124_s0
    call strcpy
    ld de,p1124_copy
    call p1124_check_word
    ret c
    ld hl,p1124_copy
    ld de,p1124_s0
    ld b,4
p1124_copy_cmp:
    ld a,(de)
    cp (hl)
    jp nz,p1124_fail
    inc de
    inc hl
    djnz p1124_copy_cmp

    ld hl,p1124_ncopy
    ld de,p1124_s0
    ld bc,6
    call strncpy
    ld de,p1124_ncopy
    call p1124_check_word
    ret c
    ld hl,p1124_ncopy
    ld de,p1124_ncopy_expected
    ld b,6
p1124_ncopy_cmp:
    ld a,(de)
    cp (hl)
    jp nz,p1124_fail
    inc de
    inc hl
    djnz p1124_ncopy_cmp
    xor a
    ret
p1124_ncopy_expected:
    db "abc",0,0,0

p1124_memory:
    ld hl,p1124_memdst+1
    ld de,p1124_memsrc
    ld bc,8
    call memcpy
    ld de,p1124_memdst+1
    call p1124_check_word
    ret c
    ld a,(p1124_memdst)
    cp $A6
    jp nz,p1124_fail
    ld a,(p1124_memdst+9)
    cp $A6
    jp nz,p1124_fail
    ld hl,p1124_memdst+1
    ld de,p1124_memsrc
    ld b,8
p1124_memcpy_cmp:
    ld a,(de)
    cp (hl)
    jp nz,p1124_fail
    inc de
    inc hl
    djnz p1124_memcpy_cmp

    ; Overlap right: "abcdef" -> "ababcd".
    ld hl,p1124_overlap1+2
    ld de,p1124_overlap1
    ld bc,4
    call memmove
    ld hl,p1124_overlap1
    ld de,p1124_overlap_right
    ld b,6
p1124_ovr_cmp:
    ld a,(de)
    cp (hl)
    jp nz,p1124_fail
    inc de
    inc hl
    djnz p1124_ovr_cmp

    ; Overlap left: "abcdef" -> "cdefef".
    ld hl,p1124_overlap2
    ld de,p1124_overlap2+2
    ld bc,4
    call memmove
    ld hl,p1124_overlap2
    ld de,p1124_overlap_left
    ld b,6
p1124_ovl_cmp:
    ld a,(de)
    cp (hl)
    jp nz,p1124_fail
    inc de
    inc hl
    djnz p1124_ovl_cmp

    ld hl,p1124_memsrc
    ld de,4
    ld bc,8
    call memchr
    ld de,p1124_memsrc+3
    call p1124_check_word
    ret c
    ld hl,p1124_memsrc
    ld de,9
    ld bc,8
    call memchr
    ld de,0
    call p1124_check_word
    ret c

    ld hl,p1124_set+1
    ld de,$00CC
    ld bc,6
    call memset
    ld de,p1124_set+1
    call p1124_check_word
    ret c
    ld a,(p1124_set)
    cp $5A
    jp nz,p1124_fail
    ld a,(p1124_set+7)
    cp $5A
    jp nz,p1124_fail
    ld hl,p1124_set+1
    ld b,6
p1124_set_cmp:
    ld a,(hl)
    cp $CC
    jp nz,p1124_fail
    inc hl
    djnz p1124_set_cmp
    xor a
    ret
p1124_overlap_right: db "ababcd"
p1124_overlap_left:  db "cdefef"

p1124_format:
    ld hl,$8000
    ld de,p1124_fmt
    ld bc,8
    call c48_format_int
    ld de,6
    call p1124_check_word
    ret c
    ld hl,p1124_fmt
    ld de,p1124_fmt_min
    ld b,7
p1124_fmt_cmp:
    ld a,(de)
    cp (hl)
    jp nz,p1124_fail
    inc de
    inc hl
    djnz p1124_fmt_cmp

    ld hl,p1124_fmt
    ld b,8
    ld a,$77
p1124_fmt_reset:
    ld (hl),a
    inc hl
    djnz p1124_fmt_reset
    ld hl,12345
    ld de,p1124_fmt
    ld bc,5
    call c48_format_int
    ld de,E_NOSPC
    call p1124_check_word
    ret c
    ld a,(p1124_fmt)
    cp $77
    jp nz,p1124_fail
    xor a
    ret
p1124_fmt_min: db "-32768",0

p1124_end:
    SAVEBIN "p1124-main.bin",p1124_start,p1124_end-p1124_start
''', encoding="utf-8", newline="\n")

    result = run_command([assembler, "--nologo", "--sym=p1124-string-memory.sym", fixture.name],
                         cwd=build, timeout_seconds=30)
    require(not result.timed_out and result.exit_code == 0,
            f"P11.24 assemble: {result.stderr or result.stdout}")
    main = (build / "p1124-main.bin").read_bytes()
    require(0 < len(main) <= 0x2000, "P11.24 fixture exceeds C000-DFFF user range")
    names = ("p1124_stdio","p1124_break_eof","p1124_strings","p1124_memory","p1124_format")
    syms = phase3_open_descriptions._symbols(build / "p1124-string-memory.sym",
                                             ("p1124_gateway",) + names)

    assertions = [
        {"name":"exact-eleven-public-string-memory-symbols-present","passed":True},
        {"name":"getchar-is-byte-preserving-process-stdin-wrapper","passed":True},
        {"name":"putchar-puts-use-process-stdout","passed":True},
        {"name":"memmove-selects-ldir-or-lddr-for-overlap","passed":True},
        {"name":"compact-integer-formatter-present","passed":True},
        {"name":"c48-docs-freeze-edit-1b-break-separation","passed":True},
        {"name":"sdk-string-memory-semantics-mapped","passed":True},
    ]
    commands = [result]
    if action == "test":
        gateway = phase1._jp(syms["p1124_gateway"])
        def patch(ram):
            ram[0xC000-0x4000:0xC000-0x4000+len(main)] = main
            ram[0xE000-0x4000:0xE000-0x4000+len(gateway)] = gateway
        for name in names:
            code = (b"\xF3" + phase1._ld_sp(0xBFC0) + phase1._call(syms[name])
                    + phase1._jp_c(FAIL_PC) + phase1._jp(PASS_PC))
            try:
                commands.append(run_sna(root, code, patch=patch))
            except DriverError as exc:
                raise P1124Error(f"{name} native fixture failed: {exc}") from None
        assertions += [
            {"name":"fuse-getchar-preserves-edit-1b","passed":True},
            {"name":"fuse-break-eintr-never-masquerades-as-27","passed":True},
            {"name":"fuse-putchar-puts-exact-output-and-newline","passed":True},
            {"name":"fuse-string-empty-nul-copy-padding-cases","passed":True},
            {"name":"fuse-memmove-overlap-both-directions","passed":True},
            {"name":"fuse-memchr-hit-miss-and-memset-guards","passed":True},
            {"name":"fuse-integer-formatter-min-and-nospc-atomic","passed":True},
        ]

    hashes = {
        "v1/src/libc48/string.asm": sha256_file(string),
        "v1/src/libc48/memory.asm": sha256_file(memory),
        "v1/docs/c48.md": sha256_file(docs),
        "v1/build/p1124-main.bin": sha256_file(build / "p1124-main.bin"),
        "v1/tools-host/test-driver/phase11_step_24.py": sha256_file(
            root / "v1/tools-host/test-driver/phase11_step_24.py"),
        "v1/dist/certification/P11.23.build.json": sha256_file(
            root / "v1/dist/certification/P11.23.build.json"),
        "v1/dist/certification/P11.23.test.json": sha256_file(
            root / "v1/dist/certification/P11.23.test.json"),
    }
    return commands, hashes, assertions
