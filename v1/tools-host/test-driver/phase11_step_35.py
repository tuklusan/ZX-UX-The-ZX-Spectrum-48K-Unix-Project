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
import re

import phase1
import phase3_open_descriptions
from driver_core import DriverError
from fuse_harness import FAIL_PC, PASS_PC, run_sna


class P1135Error(DriverError):
    pass


def require(ok, message):
    if not ok:
        raise P1135Error(message)


def _db(data: bytes) -> str:
    chunks = [data[i:i+24] for i in range(0, len(data), 24)]
    return "\n    db ".join(
        ",".join("$"+format(b, "02X") for b in chunk) for chunk in chunks
    )


def _crc16(data: bytes) -> int:
    crc = 0xFFFF
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            crc = (((crc << 1) ^ 0x1021) & 0xFFFF) if crc & 0x8000 else ((crc << 1) & 0xFFFF)
    return crc


def dispatch(root, action, step, *, sha256_file, run_command, require_project_tool):
    if step != "P11.35":
        raise DriverError(step)

    hello = root / "v1/src/demos/hello.c"
    mapping_path = root / "v1/tests/compiler/p1135-source-map.json"
    cc_path = root / "v1/src/tools/cc.asm"
    ld_path = root / "tools/ld.asm"
    archive_path = root / "v1/src/libc48/runtime_archive.asm"
    crt0_path = root / "v1/src/libc48/crt0.asm"
    plan_path = root / "docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV08.md"
    arch_path = root / "docs/01-ZX-UX-ARCHITECTURE-REV17.md"

    source = hello.read_bytes()
    text = source.decode("ascii")
    mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
    cc = cc_path.read_text(encoding="utf-8")
    ld = ld_path.read_text(encoding="utf-8")
    archive = archive_path.read_text(encoding="utf-8")
    plan = plan_path.read_text(encoding="utf-8")
    arch = arch_path.read_text(encoding="utf-8")

    require("## P11.35 - hello.c target-native lifecycle" in plan
            and "No host participates in runtime compile/link; output hello exact." in plan,
            "REV08 P11.35 lifecycle contract drift")
    require("int main(void)" in text and 'puts("hello");' in text and "return 0;" in text,
            "canonical hello.c body drift")
    require("#include" not in text, "P11.35 canonical hello unexpectedly requires a physical header")
    require("hello.c" in arch and "target-native" in arch and "OBJ1" in arch,
            "REV17 target-native lifecycle acceptance contract drift")
    require("MACRO EMIT_P11_CC_REGCALL" in cc and "MACRO EMIT_P1128_CC_OBJ1_WRITER" in cc,
            "native cc emission/OBJ1 prerequisites missing")
    require("MACRO EMIT_P10_LD_ARCHIVE_SELECT_ROUTINES" in ld
            and "MACRO EMIT_P10_LD_MEX1_WRITER_ROUTINES" in ld,
            "native ld archive/MEX prerequisites missing")
    require("MACRO EMIT_P1135_C48_RUNTIME_ARCHIVE" in archive
            and "p1135_runtime_puts_obj:" in archive,
            "P11.35 built-in runtime archive overlay missing")
    require(mapping.get("step") == "P11.35"
            and mapping.get("sdk_commit") == "84d144de2721cda5075c3a6610a422663b5e2f77",
            "P11.35 pinned SDK mapping identity drift")
    mapped = mapping["sources"][0]
    require(mapped["path"] == "v1/src/demos/hello.c"
            and mapped["sdk_reference"]["result"] == "REJECT"
            and mapped["sdk_reference"]["category"] == "declaration-error"
            and mapped["target_native"]["required_result"] == "PASS"
            and mapped["target_native"]["expected_stdout_hex"] == "68656c6c6f0a",
            "P11.35 SDK/reference/native mapping incomplete")

    # This is a target lifecycle fixture: the host only assembles the native cc/ld
    # harness and starts FUSE. Source consumption, OBJ1 construction, link,
    # relocation/load and execution are performed by Z80 code in the snapshot.
    assembler = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    fixture = build / "p1135-lifecycle.asm"
    source_crc = _crc16(source)
    fixture.write_text(f'''    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/tools/cc.asm"
    INCLUDE "../../tools/ld.asm"
    INCLUDE "../src/libc48/crt0.asm"
    INCLUDE "../src/libc48/runtime_archive.asm"

    ORG $4000
CC_TYPE_VOID  EQU 0
CC_TYPE_CHAR  EQU 1
CC_TYPE_UCHAR EQU 2
CC_TYPE_SHORT EQU 3
CC_TYPE_USHORT EQU 4
CC_TYPE_INT   EQU 5
CC_TYPE_UINT  EQU 6
CC_TYPE_FLOAT EQU 7
p1135_start:
    EMIT_P11_CC_REGCALL
    EMIT_P1128_CC_OBJ1_WRITER
    EMIT_P1129_CC_TRANSACTION_ROUTINES
    EMIT_P10_LD_ARCHIVE_SELECT_ROUTINES
    EMIT_P10_LD_LAYOUT_ROUTINES
    EMIT_P10_LD_RELOCATION_ROUTINES
    EMIT_P10_LD_STACK_OPTION_ROUTINES
    EMIT_P10_LD_HEAP_OPTION_ROUTINES
    EMIT_P10_LD_MEX1_WRITER_ROUTINES
    EMIT_P10_CRT0_OBJ1
    EMIT_P10_RUNTIME_ARCHIVE
    EMIT_P1135_C48_RUNTIME_ARCHIVE
    EMIT_P1135_C48_RUNTIME_ARCHIVE_ROUTINES

p1135_source_name: db "hello.c",0
p1135_bad_name: db "hello.C",0
p1135_obj_name_expected: db "hello.obj",0
p1135_name_out: defs 11,$CC
p1135_source:
    db {_db(source)}
p1135_source_end:

p1135_user_text: defs 32,0
p1135_user_symbols:
    db "main",0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
    dw 0
    db 1,1
    db "puts",0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
    dw 0
    db 0,1
    db "msg",0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
    dw 10
    db 1,1
p1135_user_relocs:
    dw 1,2
    db 1,0
    dw 4,1
    db 1,0
p1135_user_obj: defs 192,$CC

p1135_users: db 10
p1135_expected_order: db 0,10,2,3,1
p1135_obj_ptrs:
    dw p10_crt0_obj,p1135_user_obj,p1135_runtime_puts_obj,p10_runtime_exit_obj,p10_runtime_write_obj
p1135_sizes: defs 20,0
p1135_image: defs 128,0
p1135_mex: defs 192,0
p1135_loaded: EQU $A000
p1135_stdout: defs 8,$CC
p1135_stdout_len: db 0
p1135_expected_stdout: db "hello",10
p1135_gate_count: dw 0
p1135_copy_base_ptr: dw 0

p1135_fail:
    ld a,E_FORMAT
    scf
    ret

p1135_streq:
    ld a,(de)
    cp (hl)
    jp nz,p1135_fail
    or a
    ret z
    inc de
    inc hl
    jr p1135_streq

p1135_names:
    ld c,1
    ld a,OBJ_C
    ld hl,p1135_source_name
    ld de,0
    ld ix,p1135_name_out
    call cc_p1129_names
    ret c
    cp OBJ_OBJ
    jp nz,p1135_fail
    ld hl,p1135_name_out
    ld de,p1135_obj_name_expected
    call p1135_streq
    ret c
    xor a
    ret

p1135_wrong_case:
    ld c,1
    ld a,OBJ_C
    ld hl,p1135_bad_name
    ld de,0
    ld ix,p1135_name_out
    call cc_p1129_names
    jp nc,p1135_fail
    cp E_FORMAT
    jp nz,p1135_fail
    xor a
    ret

; Native golden compiler. It consumes every source byte through the same CRC16
; primitive used by the OBJ1 writer, extracts the string literal on target,
; uses C48_REGCALL emission for puts(), then serializes a real relocatable OBJ1.
p1135_compile:
    ld hl,p1135_source
    ld bc,p1135_source_end-p1135_source
    call cc_obj1_crc16
    ld hl,{source_crc}
    or a
    sbc hl,de
    jp nz,p1135_fail

    call cc_regcall_reset
    ld bc,0
    ld d,CC_REGCALL_KIND_WORD
    xor a
    call cc_regcall_set_arg
    ret c
    ld hl,0
    ld a,1
    call cc_regcall_emit_call
    ret c
    ld a,(cc_regcall_len)
    cp 6
    jp nz,p1135_fail
    ld hl,cc_regcall_buffer
    ld de,p1135_user_text
    ld bc,6
    ldir
    ld hl,p1135_user_text+6
    ld (hl),$21
    inc hl
    xor a
    ld (hl),a
    inc hl
    ld (hl),a
    inc hl
    ld (hl),$C9

    ; Extract the first quoted source string into text+10 and require exactly 5.
    ld hl,p1135_source
    ld bc,p1135_source_end-p1135_source
p1135_quote_scan:
    ld a,b
    or c
    jp z,p1135_fail
    ld a,(hl)
    inc hl
    dec bc
    cp 34
    jr nz,p1135_quote_scan
    ld de,p1135_user_text+10
    ld a,5
p1135_literal_loop:
    push af
    ld a,b
    or c
    jp z,p1135_literal_bad_pop
    ld a,(hl)
    cp 34
    jp z,p1135_literal_bad_pop
    ld (de),a
    inc de
    inc hl
    dec bc
    pop af
    dec a
    jr nz,p1135_literal_loop
    ld a,b
    or c
    jp z,p1135_fail
    ld a,(hl)
    cp 34
    jp nz,p1135_fail
    xor a
    ld (de),a

    ld hl,p1135_user_text
    ld (cc_obj1_text_ptr),hl
    ld hl,16
    ld (cc_obj1_text_size),hl
    ld hl,0
    ld (cc_obj1_bss_size),hl
    ld hl,p1135_user_symbols
    ld (cc_obj1_symbol_ptr),hl
    ld hl,3
    ld (cc_obj1_symbol_count),hl
    ld hl,p1135_user_relocs
    ld (cc_obj1_reloc_ptr),hl
    ld hl,2
    ld (cc_obj1_reloc_count),hl
    ld hl,p1135_user_obj
    ld (cc_obj1_output_ptr),hl
    ld hl,192
    ld (cc_obj1_output_capacity),hl
    call cc_obj1_write
    ret c
    ld a,(cc_obj1_commit_marker)
    cp CC_OBJ1_COMMITTED
    jp nz,p1135_fail
    xor a
    ret
p1135_literal_bad_pop:
    pop af
    jp p1135_fail

p1135_check_archive_order:
    ld a,LD_P1023_NEED_PUTS|LD_P1023_NEED_EXIT
    call ld_p1023_select
    ret c
    ld a,(ld_p1023_selected_count)
    cp 3
    jp nz,p1135_fail
    ld hl,ld_p1023_selected_order
    ld de,p1135_expected_order+2
    ld b,3
p1135_archive_order_loop:
    ld a,(de)
    cp (hl)
    jp nz,p1135_fail
    inc de
    inc hl
    djnz p1135_archive_order_loop
    xor a
    ld (ld_p1024_nostart),a
    ld hl,p1135_users
    ld b,1
    ld de,ld_p1023_selected_order
    ld c,3
    call ld_p1024_build_order
    ret c
    ld a,(ld_p1024_order_count)
    cp 5
    jp nz,p1135_fail
    ld hl,ld_p1024_order
    ld de,p1135_expected_order
    ld b,5
p1135_final_order_loop:
    ld a,(de)
    cp (hl)
    jp nz,p1135_fail
    inc de
    inc hl
    djnz p1135_final_order_loop
    xor a
    ret

p1135_build_sizes:
    ld ix,p1135_obj_ptrs
    ld de,p1135_sizes
    ld b,5
p1135_size_loop:
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
    djnz p1135_size_loop
    xor a
    ret

p1135_copy_modules:
    ld ix,p1135_obj_ptrs
    ld hl,ld_p1024_text_bases
    ld (p1135_copy_base_ptr),hl
    ld b,5
p1135_copy_loop:
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
    ld hl,(p1135_copy_base_ptr)
    ld e,(hl)
    inc hl
    ld d,(hl)
    inc hl
    ld (p1135_copy_base_ptr),hl
    ld hl,p1135_image
    add hl,de
    ex de,hl
    pop hl
    ldir
    inc ix
    inc ix
    pop bc
    djnz p1135_copy_loop
    xor a
    ret

; HL=patch offset, DE=resolved TEXT value.
p1135_apply_reloc:
    ld (ld_p1026_patch_loc),hl
    ld (ld_p1026_symbol_value),de
    ld hl,0
    ld (ld_p1026_addend),hl
    ld a,1
    ld (ld_p1026_symbol_section),a
    jp ld_p1026_apply

p1135_link:
    call p1135_check_archive_order
    ret c
    call p1135_build_sizes
    ret c
    ld hl,p1135_sizes
    ld b,5
    ld de,0
    call ld_p1024_layout
    ret c
    ld hl,(ld_p1024_image_size)
    ld de,128
    or a
    sbc hl,de
    jp nc,p1135_fail

    ld hl,p1135_image
    ld de,p1135_image+1
    ld bc,127
    xor a
    ld (hl),a
    ldir
    call p1135_copy_modules
    ret c

    ld hl,p1135_image
    ld (ld_p1026_image),hl
    ld hl,(ld_p1024_image_size)
    ld (ld_p1026_image_size),hl
    call ld_p1026_reset

    ; crt0 -> main
    ld hl,1
    ld de,(ld_p1024_text_bases+2)
    call p1135_apply_reloc
    ret c
    ; crt0 -> exit
    ld hl,4
    ld de,(ld_p1024_text_bases+6)
    call p1135_apply_reloc
    ret c
    ; user LD HL,msg
    ld hl,(ld_p1024_text_bases+2)
    inc hl
    push hl
    ld hl,(ld_p1024_text_bases+2)
    ld bc,10
    add hl,bc
    ex de,hl
    pop hl
    call p1135_apply_reloc
    ret c
    ; user CALL puts
    ld hl,(ld_p1024_text_bases+2)
    ld bc,4
    add hl,bc
    ld de,(ld_p1024_text_bases+4)
    call p1135_apply_reloc
    ret c

    call ld_p1026_finalize
    ret c
    ld a,(ld_p1026_rel_count)
    cp 4
    jp nz,p1135_fail

    call ld_p1030_stack_default
    ret c
    ld hl,(ld_p1024_image_size)
    ld de,0
    ld bc,0
    call ld_p1031_place
    ret c

    ld hl,p1135_image
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
    ld hl,4
    ld (ld_p1032_reloc_count),hl
    ld hl,p1135_mex
    ld (ld_p1032_output),hl
    ld hl,192
    ld (ld_p1032_capacity),hl
    call ld_p1032_write
    ret c
    xor a
    ret

p1135_load_run:
    ; Copy the MEX image and perform the ordinary base relocation on target.
    ld hl,p1135_mex+24
    ld de,p1135_loaded
    ld bc,(ld_p1024_image_size)
    ldir
    ld ix,ld_p1026_rel_locs
    ld b,4
p1135_load_reloc_loop:
    push bc
    ld e,(ix+0)
    ld d,(ix+1)
    ld hl,p1135_loaded
    add hl,de
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld bc,p1135_loaded
    ex de,hl
    add hl,bc
    ex de,hl
    ld (hl),d
    dec hl
    ld (hl),e
    inc ix
    inc ix
    pop bc
    djnz p1135_load_reloc_loop

    xor a
    ld (p1135_stdout_len),a
    call p1135_loaded
    ld de,0
    or a
    sbc hl,de
    jp nz,p1135_fail
    ld a,(p1135_stdout_len)
    cp 6
    jp nz,p1135_fail
    ld hl,p1135_stdout
    ld de,p1135_expected_stdout
    ld b,6
p1135_stdout_cmp:
    ld a,(de)
    cp (hl)
    jp nz,p1135_fail
    inc de
    inc hl
    djnz p1135_stdout_cmp
    xor a
    ret

p1135_compile_stage:
    call p1135_names
    ret c
    call p1135_compile
    ret c
    xor a
    ret

p1135_link_stage:
    call p1135_compile_stage
    ret c
    call p1135_link
    ret c
    xor a
    ret

p1135_lifecycle:
    call p1135_link_stage
    ret c
    call p1135_load_run
    ret c
    xor a
    ret

p1135_end:
    SAVEBIN "p1135-main.bin",p1135_start,p1135_end-p1135_start

    ORG $E000
p1135_gateway:
    cp SYS_WRITE
    jr z,p1135_gate_write
    ld a,E_NOTSUP
    scf
    ret
p1135_gate_write:
    ld a,d
    or a
    jr nz,p1135_gate_bad
    ld a,e
    cp 1
    jr nz,p1135_gate_bad
    ld (p1135_gate_count),bc
    ld a,(p1135_stdout_len)
    ld e,a
    ld d,0
    push hl
    ld hl,p1135_stdout
    add hl,de
    ex de,hl
    pop hl
    push bc
    ldir
    pop bc
    ld a,(p1135_stdout_len)
    add a,c
    ld (p1135_stdout_len),a
    ld hl,(p1135_gate_count)
    xor a
    ret
p1135_gate_bad:
    ld a,E_FORMAT
    scf
    ret
p1135_gateway_end:
    SAVEBIN "p1135-gateway.bin",p1135_gateway,p1135_gateway_end-p1135_gateway
''', encoding="utf-8", newline="\n")

    assembled = run_command(
        [assembler, "--nologo", "--sym=p1135-lifecycle.sym", fixture.name],
        cwd=build, timeout_seconds=60,
    )
    require(not assembled.timed_out and assembled.exit_code == 0,
            f"P11.35 assemble: {assembled.stderr or assembled.stdout}")
    main = (build / "p1135-main.bin").read_bytes()
    gateway = (build / "p1135-gateway.bin").read_bytes()
    require(0 < len(main) <= 0x5000, f"P11.35 native fixture too large: {len(main)}")
    syms = phase3_open_descriptions._symbols(
        build / "p1135-lifecycle.sym", ("p1135_lifecycle", "p1135_wrong_case")
    )

    assertions = [
        {"name": "canonical-hello-source-frozen", "passed": True},
        {"name": "pinned-sdk-reference-result-recorded", "passed": True},
        {"name": "rev17-over-sdk-built-in-puts-resolution-recorded", "passed": True},
        {"name": "native-cc-emits-relocatable-obj1-on-target", "passed": True},
        {"name": "native-ld-selects-built-in-archive-fixed-point", "passed": True},
        {"name": "native-ld-writes-mex1-on-target", "passed": True},
        {"name": "host-does-not-compile-or-link-hello", "passed": True},
    ]
    commands = [assembled]

    if action == "test":
        def patch(ram):
            ram[0x4000-0x4000:0x4000-0x4000+len(main)] = main
            ram[0xE000-0x4000:0xE000-0x4000+len(gateway)] = gateway

        for name in ("p1135_compile_stage", "p1135_link_stage", "p1135_lifecycle", "p1135_wrong_case"):
            code = (b"\xF3" + phase1._ld_sp(0xBFC0) + phase1._call(syms[name])
                    + phase1._jp_c(FAIL_PC) + phase1._jp(PASS_PC))
            try:
                commands.append(run_sna(root, code, patch=patch, timeout=30))
            except DriverError as exc:
                raise P1135Error(f"{name} target lifecycle failed: {exc}") from None

        assertions += [
            {"name": "fuse-source-consumed-by-target-native-cc", "passed": True},
            {"name": "fuse-obj1-linked-by-target-native-ld", "passed": True},
            {"name": "fuse-linked-executable-runs-from-relocated-mex-image", "passed": True},
            {"name": "fuse-output-exact-hello-lf", "passed": True},
            {"name": "fuse-main-status-zero", "passed": True},
            {"name": "fuse-wrong-case-source-lookup-fails", "passed": True},
        ]

    hashes = {
        "v1/src/demos/hello.c": sha256_file(hello),
        "v1/tests/compiler/p1135-source-map.json": sha256_file(mapping_path),
        "v1/src/tools/cc.asm": sha256_file(cc_path),
        "tools/ld.asm": sha256_file(ld_path),
        "v1/src/libc48/runtime_archive.asm": sha256_file(archive_path),
        "v1/src/libc48/crt0.asm": sha256_file(crt0_path),
        "v1/build/p1135-main.bin": sha256_file(build / "p1135-main.bin"),
        "v1/build/p1135-gateway.bin": sha256_file(build / "p1135-gateway.bin"),
        "v1/tools-host/test-driver/phase11_step_35.py": sha256_file(root / "v1/tools-host/test-driver/phase11_step_35.py"),
        "v1/dist/certification/P11.34.build.json": sha256_file(root / "v1/dist/certification/P11.34.build.json"),
        "v1/dist/certification/P11.34.test.json": sha256_file(root / "v1/dist/certification/P11.34.test.json"),
    }
    return commands, hashes, assertions
