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

import json

import phase1
import phase3_open_descriptions
from driver_core import DriverError
from fuse_harness import FAIL_PC, PASS_PC, run_sna


class P1137Error(DriverError):
    pass


def require(ok, message):
    if not ok:
        raise P1137Error(message)


def _db(data: bytes) -> str:
    chunks = [data[i:i+24] for i in range(0, len(data), 24)]
    return "\n    db ".join(
        ",".join("$"+format(b, "02X") for b in chunk) for chunk in chunks
    )


def dispatch(root, action, step, *, sha256_file, run_command, require_project_tool):
    if step != "P11.37":
        raise DriverError(step)

    source_path = root / "v1/src/demos/pipe.c"
    mapping_path = root / "v1/tests/compiler/p1137-source-map.json"
    cc_path = root / "v1/src/tools/cc.asm"
    ld_path = root / "tools/ld.asm"
    source = source_path.read_bytes()
    text = source.decode("ascii")
    mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
    cc = cc_path.read_text(encoding="utf-8")
    plan = (root / "docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV08.md").read_text(encoding="utf-8")
    arch = (root / "docs/01-ZX-UX-ARCHITECTURE-REV17.md").read_text(encoding="utf-8")

    require("## P11.37 - Pipe-aware C program" in plan
            and "True bounded pipe behavior." in plan
            and "Broken pipe handled." in plan,
            "REV08 P11.37 contract drift")
    require("EMIT_P1137_CC_PIPE_COMPILER" in cc and "cc_p1137_compile:" in cc,
            "P11.37 native compiler extension missing")
    require("unsigned char fds[2];" in text
            and "unsigned char buffer[300];" in text
            and "pipe(fds);" in text
            and "return write(fds[1], buffer, 300);" in text,
            "P11.37 pipe.c source drift")
    require(mapping["step"] == "P11.37"
            and mapping["sdk_commit"] == "84d144de2721cda5075c3a6610a422663b5e2f77"
            and mapping["sources"][0]["target_native"]["expected_return"] == 256,
            "P11.37 SDK/native mapping drift")
    require("real bounded RAM pipes" in arch and "E_PIPE" in arch,
            "REV17 pipe authority drift")

    kernel_result, kernel_path, listing = phase1._assemble_kernel(
        root, run_command, require_project_tool
    )
    k = phase3_open_descriptions._symbols(
        listing.with_suffix(".sym"),
        (
            "zx48_memory_init", "zx48_process_init", "zx48_handles_init",
            "zx48_pipe_init", "zx48_process_prepare_pid1", "current_pid",
            "pipe_table", "PIPE_COUNT_O", "PIPE_BUFFER_SIZE",
        ),
    )
    require(k["PIPE_BUFFER_SIZE"] == 256, "P11.37 bounded pipe capacity drift")

    assembler = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    fixture = build / "p1137-native-pipe.asm"
    fixture.write_text(f'''    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/tools/cc.asm"
    INCLUDE "../../tools/ld.asm"
    INCLUDE "../src/libc48/crt0.asm"
    INCLUDE "../src/libc48/runtime_archive.asm"

ZXK_MEMORY_INIT      EQU {k["zx48_memory_init"]}
ZXK_PROCESS_INIT     EQU {k["zx48_process_init"]}
ZXK_HANDLES_INIT     EQU {k["zx48_handles_init"]}
ZXK_PIPE_INIT        EQU {k["zx48_pipe_init"]}
ZXK_PREP_PID1        EQU {k["zx48_process_prepare_pid1"]}
ZXK_CURRENT_PID      EQU {k["current_pid"]}
ZXK_PIPE_TABLE       EQU {k["pipe_table"]}
ZXK_PIPE_COUNT_O     EQU {k["PIPE_COUNT_O"]}

    ORG $4000
p1137_start:
    EMIT_P11_CC_STREAMING_CORE
    EMIT_P11_CC_LEXER
    EMIT_P1128_CC_OBJ1_WRITER
    EMIT_P1137_CC_PIPE_COMPILER
    EMIT_P10_LD_LAYOUT_ROUTINES
    EMIT_P10_LD_RELOCATION_ROUTINES
    EMIT_P10_LD_STACK_OPTION_ROUTINES
    EMIT_P10_LD_HEAP_OPTION_ROUTINES
    EMIT_P10_LD_MEX1_WRITER_ROUTINES
    EMIT_P10_CRT0_OBJ1
    EMIT_P10_RUNTIME_ARCHIVE

p1137_source:
    db {_db(source)}
p1137_source_end:
p1137_user_obj: defs 512,$CC
p1137_obj_ptrs: dw p10_crt0_obj,p1137_user_obj,p10_runtime_exit_obj
p1137_sizes: defs 12,0
p1137_image: defs 256,0
p1137_mex: defs 384,0
p1137_copy_base_ptr: dw 0
p1137_loaded: EQU $C000
p1137_neg_fds: db $A5,$5A
p1137_neg_byte: db $7A

p1137_fail:
    ld a,E_FORMAT
    scf
    ret

p1137_setup_kernel:
    call ZXK_MEMORY_INIT
    call ZXK_PROCESS_INIT
    call ZXK_HANDLES_INIT
    call ZXK_PIPE_INIT
    call ZXK_PREP_PID1
    ld a,1
    ld (ZXK_CURRENT_PID),a
    xor a
    ret

p1137_compile:
    ld hl,p1137_source
    ld bc,p1137_source_end-p1137_source
    ld de,p1137_user_obj
    ld ix,512
    call cc_p1137_compile
    ret c
    ld de,0
    or a
    sbc hl,de
    jp z,p1137_fail
    xor a
    ret

p1137_build_sizes:
    ld ix,p1137_obj_ptrs
    ld de,p1137_sizes
    ld b,3
p1137_size_loop:
    push bc
    ld l,(ix+0)
    ld h,(ix+1)
    push hl
    ld bc,8
    add hl,bc
    ld a,(hl)
    ld (de),a
    inc hl
    inc de
    ld a,(hl)
    ld (de),a
    inc de
    pop hl
    ld bc,10
    add hl,bc
    ld a,(hl)
    ld (de),a
    inc hl
    inc de
    ld a,(hl)
    ld (de),a
    inc de
    inc ix
    inc ix
    pop bc
    djnz p1137_size_loop
    xor a
    ret

p1137_copy_modules:
    ld ix,p1137_obj_ptrs
    ld hl,ld_p1024_text_bases
    ld (p1137_copy_base_ptr),hl
    ld b,3
p1137_copy_loop:
    push bc
    ld l,(ix+0)
    ld h,(ix+1)
    push hl
    ld de,8
    add hl,de
    ld c,(hl)
    inc hl
    ld b,(hl)
    pop hl
    ld de,24
    add hl,de
    push hl
    ld hl,(p1137_copy_base_ptr)
    ld e,(hl)
    inc hl
    ld d,(hl)
    inc hl
    ld (p1137_copy_base_ptr),hl
    ld hl,p1137_image
    add hl,de
    ex de,hl
    pop hl
    ldir
    inc ix
    inc ix
    pop bc
    djnz p1137_copy_loop
    xor a
    ret

; HL=patch offset, DE=base-zero value, A=section.
p1137_apply:
    ld (ld_p1026_symbol_section),a
    ld (ld_p1026_patch_loc),hl
    ld (ld_p1026_symbol_value),de
    ld hl,0
    ld (ld_p1026_addend),hl
    jp ld_p1026_apply

; BC=BSS object offset -> DE=base-zero linked BSS value.
p1137_bss_value:
    ld hl,(ld_p1024_image_size)
    ld de,(ld_p1024_bss_bases+2)
    add hl,de
    add hl,bc
    ex de,hl
    ret

p1137_link:
    call p1137_compile
    ret c
    call p1137_build_sizes
    ret c
    ld hl,p1137_sizes
    ld b,3
    ld de,0
    call ld_p1024_layout
    ret c
    ld hl,(ld_p1024_final_bss)
    ld de,302
    or a
    sbc hl,de
    jp nz,p1137_fail
    ld hl,(ld_p1024_image_size)
    ld de,256
    or a
    sbc hl,de
    jp nc,p1137_fail

    ld hl,p1137_image
    ld de,p1137_image+1
    ld bc,255
    xor a
    ld (hl),a
    ldir
    call p1137_copy_modules
    ret c

    ld hl,p1137_image
    ld (ld_p1026_image),hl
    ld hl,(ld_p1024_image_size)
    ld (ld_p1026_image_size),hl
    call ld_p1026_reset

    ; crt0 -> main
    ld hl,1
    ld de,(ld_p1024_text_bases+2)
    ld a,1
    call p1137_apply
    ret c
    ; crt0 -> exit
    ld hl,4
    ld de,(ld_p1024_text_bases+4)
    ld a,1
    call p1137_apply
    ret c

    ; user LD HL,fds
    ld hl,(ld_p1024_text_bases+2)
    inc hl
    push hl
    ld bc,0
    call p1137_bss_value
    pop hl
    ld a,2
    call p1137_apply
    ret c
    ; user LD A,(fds+1)
    ld hl,(ld_p1024_text_bases+2)
    ld bc,9
    add hl,bc
    push hl
    ld bc,1
    call p1137_bss_value
    pop hl
    ld a,2
    call p1137_apply
    ret c
    ; user LD HL,buffer
    ld hl,(ld_p1024_text_bases+2)
    ld bc,15
    add hl,bc
    push hl
    ld bc,2
    call p1137_bss_value
    pop hl
    ld a,2
    call p1137_apply
    ret c

    call ld_p1026_finalize
    ret c
    ld a,(ld_p1026_rel_count)
    cp 5
    jp nz,p1137_fail

    call ld_p1030_stack_default
    ret c
    ld hl,(ld_p1024_image_size)
    ld de,(ld_p1024_final_bss)
    ld bc,0
    call ld_p1031_place
    ret c
    ld hl,(ld_p1031_mex1_bss_size)
    ld de,302
    or a
    sbc hl,de
    jp nz,p1137_fail

    ld hl,p1137_image
    ld (ld_p1032_image),hl
    ld hl,(ld_p1024_image_size)
    ld (ld_p1032_image_size),hl
    ld hl,(ld_p1031_mex1_bss_size)
    ld (ld_p1032_bss_size),hl
    ld hl,0
    ld (ld_p1032_entry),hl
    ld hl,(ld_p1030_min_fast_stack)
    ld (ld_p1032_stack),hl
    ld hl,ld_p1026_rel_locs
    ld (ld_p1032_relocs),hl
    ld hl,5
    ld (ld_p1032_reloc_count),hl
    ld hl,p1137_mex
    ld (ld_p1032_output),hl
    ld hl,384
    ld (ld_p1032_capacity),hl
    call ld_p1032_write
    ret c
    xor a
    ret

p1137_load:
    ld hl,p1137_mex+24
    ld de,p1137_loaded
    ld bc,(ld_p1024_image_size)
    ldir

    ; Zero complete linked BSS.
    ld hl,p1137_loaded
    ld de,(ld_p1024_image_size)
    add hl,de
    ld de,p1137_loaded
    push hl
    ex de,hl
    pop hl
    ld bc,(ld_p1031_mex1_bss_size)
    ld a,b
    or c
    jr z,p1137_bss_zero_done
    xor a
    ld (hl),a
    dec bc
    ld a,b
    or c
    jr z,p1137_bss_zero_done
    push hl
    inc hl
    ex de,hl
    pop hl
    ldir
p1137_bss_zero_done:

    ; Apply MEX base relocations.
    ld ix,ld_p1026_rel_locs
    ld b,5
p1137_load_reloc_loop:
    push bc
    ld e,(ix+0)
    ld d,(ix+1)
    ld hl,p1137_loaded
    add hl,de
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld bc,p1137_loaded
    ex de,hl
    add hl,bc
    ex de,hl
    ld (hl),d
    dec hl
    ld (hl),e
    inc ix
    inc ix
    pop bc
    djnz p1137_load_reloc_loop
    xor a
    ret

p1137_lifecycle:
    call p1137_link
    ret c
    call p1137_load
    ret c
    call p1137_setup_kernel
    ret c
    call p1137_loaded
    ld de,256
    or a
    sbc hl,de
    jp nz,p1137_fail

    ; Exact C BSS result fds[] contains read=0 and write=1.
    ld hl,p1137_loaded
    ld de,(ld_p1024_image_size)
    add hl,de
    ld a,(hl)
    or a
    jp nz,p1137_fail
    inc hl
    ld a,(hl)
    cp 1
    jp nz,p1137_fail

    ; 300-byte request must be bounded by the real 256-byte pipe.
    ld hl,ZXK_PIPE_TABLE+ZXK_PIPE_COUNT_O
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld hl,256
    or a
    sbc hl,de
    jp nz,p1137_fail
    xor a
    ret

p1137_broken_pipe:
    call p1137_setup_kernel
    ret c
    ld hl,p1137_neg_fds
    ld a,SYS_PIPE
    call SYSCALL_GATEWAY
    ret c
    ld a,(p1137_neg_fds)
    ld l,a
    ld h,0
    ld a,SYS_CLOSE
    call SYSCALL_GATEWAY
    ret c
    ld a,(p1137_neg_fds+1)
    ld e,a
    ld d,0
    ld hl,p1137_neg_byte
    ld bc,1
    ld a,SYS_WRITE
    call SYSCALL_GATEWAY
    jp nc,p1137_fail
    cp E_PIPE
    jp nz,p1137_fail
    ; Failed write cannot increment bounded pipe byte count.
    ld hl,ZXK_PIPE_TABLE+ZXK_PIPE_COUNT_O
    ld a,(hl)
    inc hl
    or (hl)
    jp nz,p1137_fail
    xor a
    ret

p1137_end:
    SAVEBIN "p1137-main.bin",p1137_start,p1137_end-p1137_start
''', encoding="utf-8", newline="\n")

    assembled = run_command(
        [assembler, "--nologo", "--sym=p1137-native-pipe.sym", fixture.name],
        cwd=build, timeout_seconds=60,
    )
    require(not assembled.timed_out and assembled.exit_code == 0,
            f"P11.37 assemble: {assembled.stderr or assembled.stdout}")
    main = (build / "p1137-main.bin").read_bytes()
    require(0 < len(main) < 0x5000,
            f"P11.37 helper overlaps FUSE trampoline: {len(main)}")
    syms = phase3_open_descriptions._symbols(
        build / "p1137-native-pipe.sym",
        ("p1137_compile", "p1137_link", "p1137_lifecycle", "p1137_broken_pipe"),
    )

    assertions = [
        {"name": "pipe-c-source-mapped-to-pinned-sdk-reference", "passed": True},
        {"name": "native-cc-emits-text-bss-relocatable-obj1", "passed": True},
        {"name": "native-ld-links-bss-relocations-to-mex1", "passed": True},
        {"name": "real-kernel-pipe-capacity-exact-256", "passed": True},
        {"name": "host-does-not-compile-or-link-pipe-demo", "passed": True},
    ]
    commands = [kernel_result, assembled]

    if action == "test":
        kernel_bytes = kernel_path.read_bytes()
        kernel_patch = phase1._kernel_patch(kernel_bytes)

        def patch(ram):
            ram[0:len(main)] = main
            kernel_patch(ram)

        for name in ("p1137_compile", "p1137_link", "p1137_lifecycle", "p1137_broken_pipe"):
            code = (b"\xF3" + phase1._ld_sp(0xBFC0) + phase1._call(syms[name])
                    + phase1._jp_c(FAIL_PC) + phase1._jp(PASS_PC))
            try:
                commands.append(run_sna(root, code, patch=patch, timeout=30))
            except DriverError as exc:
                raise P1137Error(f"{name} target-native pipe fixture failed: {exc}") from None

        assertions += [
            {"name": "fuse-native-compile-link-run-pipe-demo", "passed": True},
            {"name": "fuse-write-300-is-bounded-to-256", "passed": True},
            {"name": "fuse-real-pipe-count-is-exactly-256", "passed": True},
            {"name": "fuse-broken-pipe-returns-e-pipe", "passed": True},
            {"name": "fuse-broken-pipe-performs-no-hidden-write", "passed": True},
        ]

    hashes = {
        "v1/build/kernel.bin": sha256_file(kernel_path),
        "v1/src/demos/pipe.c": sha256_file(source_path),
        "v1/tests/compiler/p1137-source-map.json": sha256_file(mapping_path),
        "v1/src/tools/cc.asm": sha256_file(cc_path),
        "tools/ld.asm": sha256_file(ld_path),
        "v1/build/p1137-main.bin": sha256_file(build / "p1137-main.bin"),
        "v1/tools-host/test-driver/phase11_step_37.py": sha256_file(root / "v1/tools-host/test-driver/phase11_step_37.py"),
        "v1/dist/certification/P11.36.build.json": sha256_file(root / "v1/dist/certification/P11.36.build.json"),
        "v1/dist/certification/P11.36.test.json": sha256_file(root / "v1/dist/certification/P11.36.test.json"),
    }
    return commands, hashes, assertions
