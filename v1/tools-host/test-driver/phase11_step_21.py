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

class P1121Error(DriverError):
    pass

def require(ok, message):
    if not ok:
        raise P1121Error(message)

def dispatch(root, action, step, *, sha256_file, run_command, require_project_tool):
    if step != "P11.21":
        raise DriverError(step)

    memory=root/"v1/src/libc48/memory.asm"
    text=memory.read_text(encoding="utf-8")
    linker=(root/"tools/ld.asm").read_text(encoding="utf-8")
    arch=(root/"docs/01-ZX-UX-ARCHITECTURE-REV17.md").read_text(encoding="utf-8")
    plan=(root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV08.md").read_text(encoding="utf-8")

    require("EMIT_P1121_C48_MEMORY" in text and "malloc:" in text and "free:" in text,
            "P11.21 allocator surface incomplete")
    require("__heap_start" in text and "__heap_end" in text,
            "P11.21 allocator is not linker-bound")
    require("SYS_ALLOC" not in text, "P11.21 allocator depends on forbidden kernel allocation")
    require("LD_P1031_HEAP_NORMAL_DEFAULT  EQU 1024" in linker
            and "LD_P1031_HEAP_NOSTART_DEFAULT EQU 0" in linker
            and "LD_P1031_HEAP_MAX             EQU 8192" in linker,
            "P11.21 linker heap defaults drift")
    require("Version 1 has no user `SYS_ALLOC`." in arch
            and "__heap_start" in arch and "__heap_end" in arch
            and "may select an even value from 0..8192" in arch,
            "REV17 P11.21 heap contract drift")
    require("## P11.21 - C48 malloc/free BSS heap" in plan
            and "default1024, heap0, heap8192 accounting" in plan
            and "Static scan rejects SYS_ALLOC dependency." in plan,
            "REV08 P11.21 acceptance contract drift")

    start=text.index("    MACRO EMIT_P1121_C48_MEMORY")
    macro=text[start:text.index("    ENDM",start)+len("    ENDM")]
    code="\n".join(line.split(";",1)[0] for line in macro.splitlines())
    require(not re.search(r"\biy\b|\bexx\b|ex\s+af\s*,\s*af'",code,re.I),
            "P11.21 allocator touches OS-private registers")
    require("call SYSCALL_GATEWAY" not in code,
            "P11.21 allocator attempts a kernel allocation path")

    assembler=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus")
    build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    fixture=build/"p1121-memory.asm"
    fixture.write_text(r'''    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/libc48/memory.asm"

    ORG $C000
p1121_start:
    EMIT_P1121_C48_MEMORY

p1121_fail:
    ld a,E_FORMAT
    scf
    ret

p1121_check_word:
    or a
    sbc hl,de
    jp nz,p1121_fail
    xor a
    ret

p1121_init_default:
    ld de,p1121_heap_default
    ld bc,p1121_heap_default_end
    jp c48_heap_init_bounds

p1121_default:
    call p1121_init_default
    ld hl,100
    call malloc
    ld a,h
    or l
    jp z,p1121_fail
    ld (p1121_p0),hl
    bit 0,l
    jp nz,p1121_fail

    ld hl,200
    call malloc
    ld a,h
    or l
    jp z,p1121_fail
    ld (p1121_p1),hl

    ld hl,(p1121_p0)
    call free
    ld hl,96
    call malloc
    ld de,(p1121_p0)
    call p1121_check_word
    ret c

    ld hl,(p1121_p1)
    call free
    ld hl,(p1121_p0)
    call free
    ld hl,1018
    call malloc
    ld a,h
    or l
    jp z,p1121_fail
    ld hl,2
    call malloc
    ld a,h
    or l
    jp nz,p1121_fail
    xor a
    ret

p1121_heap0:
    ld de,p1121_heap_zero
    ld bc,p1121_heap_zero
    call c48_heap_init_bounds
    ld hl,2
    call malloc
    ld a,h
    or l
    jp nz,p1121_fail
    xor a
    ret

p1121_heap8192:
    ld de,p1121_heap_big
    ld bc,p1121_heap_big_end
    call c48_heap_init_bounds
    ld hl,8188
    call malloc
    ld de,p1121_heap_big+C48_HEAP_HEADER_SIZE
    call p1121_check_word
    ret c
    ld hl,2
    call malloc
    ld a,h
    or l
    jp nz,p1121_fail

    ld hl,p1121_heap_big+C48_HEAP_HEADER_SIZE
    call free
    ld hl,4092
    call malloc
    ld a,h
    or l
    jp z,p1121_fail
    ld (p1121_p0),hl
    ld hl,4092
    call malloc
    ld a,h
    or l
    jp z,p1121_fail
    ld (p1121_p1),hl
    ld hl,(p1121_p0)
    call free
    ld hl,(p1121_p1)
    call free
    ld hl,8188
    call malloc
    ld a,h
    or l
    jp z,p1121_fail
    xor a
    ret

p1121_edges:
    call p1121_init_default
    ld hl,0
    call malloc
    ld a,h
    or l
    jp nz,p1121_fail
    ld hl,1
    call malloc
    ld a,h
    or l
    jp z,p1121_fail
    bit 0,l
    jp nz,p1121_fail
    ld (p1121_p0),hl
    call free
    ld hl,(p1121_p0)
    call free
    ld hl,p1121_heap_default+1
    call free
    ld hl,1020
    call malloc
    ld a,h
    or l
    jp z,p1121_fail
    xor a
    ret

p1121_p0: dw 0
p1121_p1: dw 0
p1121_end:
    SAVEBIN "p1121-main.bin",p1121_start,p1121_end-p1121_start

    ORG $8000
p1121_heap_big:
    defs 8192,$A5
p1121_heap_big_end:

    ORG $A800
p1121_heap_default:
__heap_start:
    defs 1024,$5A
__heap_end:
p1121_heap_default_end:
p1121_heap_zero:
''',encoding="utf-8",newline="\n")

    result=run_command([assembler,"--nologo","--sym=p1121-memory.sym",fixture.name],
                       cwd=build,timeout_seconds=30)
    require(not result.timed_out and result.exit_code==0,
            f"P11.21 assemble: {result.stderr or result.stdout}")
    main=(build/"p1121-main.bin").read_bytes()
    require(0<len(main)<=0x2000,"P11.21 fixture code exceeds C000-DFFF user range")
    names=("p1121_default","p1121_heap0","p1121_heap8192","p1121_edges")
    syms=phase3_open_descriptions._symbols(build/"p1121-memory.sym",names)

    assertions=[
      {"name":"malloc-free-public-symbols-present","passed":True},
      {"name":"allocator-bound-only-to-linker-heap-symbols","passed":True},
      {"name":"default-linker-heap-is-1024-bytes","passed":True},
      {"name":"nostart-default-heap-is-zero-bytes","passed":True},
      {"name":"maximum-configurable-heap-is-8192-bytes","passed":True},
      {"name":"no-kernel-allocation-dependency","passed":True},
      {"name":"allocation-alignment-is-two-bytes","passed":True},
    ]
    commands=[result]
    if action=="test":
        def patch(ram):
            ram[0xC000-0x4000:0xC000-0x4000+len(main)]=main
            ram[0x8000-0x4000:0xA000-0x4000]=bytes([0xA5])*8192
            ram[0xA800-0x4000:0xAC00-0x4000]=bytes([0x5A])*1024
        for name in names:
            code=(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._call(syms[name])
                  +phase1._jp_c(FAIL_PC)+phase1._jp(PASS_PC))
            try: commands.append(run_sna(root,code,patch=patch))
            except DriverError as exc:
                raise P1121Error(f"{name} native fixture failed: {exc}") from None
        assertions += [
          {"name":"fuse-default1024-allocation-accounting","passed":True},
          {"name":"fuse-heap0-malloc-returns-null","passed":True},
          {"name":"fuse-heap8192-full-range-accounting","passed":True},
          {"name":"fuse-free-reuse-and-neighbour-coalescing","passed":True},
          {"name":"fuse-zero-odd-invalid-double-free-controlled","passed":True},
        ]

    hashes={
      "v1/src/libc48/memory.asm":sha256_file(memory),
      "tools/ld.asm":sha256_file(root/"tools/ld.asm"),
      "v1/build/p1121-main.bin":sha256_file(build/"p1121-main.bin"),
      "v1/tools-host/test-driver/phase11_step_21.py":sha256_file(root/"v1/tools-host/test-driver/phase11_step_21.py"),
      "v1/dist/certification/P11.20.build.json":sha256_file(root/"v1/dist/certification/P11.20.build.json"),
      "v1/dist/certification/P11.20.test.json":sha256_file(root/"v1/dist/certification/P11.20.test.json"),
    }
    return commands,hashes,assertions
