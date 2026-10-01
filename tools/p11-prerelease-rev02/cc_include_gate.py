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

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys


def req(value: bool, message: str) -> None:
    if not value:
        raise SystemExit("ERROR: " + message)


def run(argv, cwd: Path, env=None):
    p = subprocess.run([str(x) for x in argv], cwd=cwd, env=env, text=True,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    req(p.returncode == 0, "command failed: " + " ".join(map(str, argv)) + "\n" + p.stdout + "\n" + p.stderr)
    return p


def symbols(path: Path) -> dict[str, int]:
    out = {}
    for line in path.read_text().splitlines():
        if ": EQU 0x" not in line:
            continue
        name, raw = line.split(": EQU 0x", 1)
        try:
            out[name.strip()] = int(raw.strip(), 16)
        except ValueError:
            pass
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--assemble-only", action="store_true")
    ns = ap.parse_args()
    root = ns.root.resolve()
    out = ns.output.resolve()
    out.mkdir(parents=True, exist_ok=True)

    cc = (root / "v1/src/tools/cc.asm").read_text()
    block = cc.split("MACRO EMIT_REV02_CC_PRODUCT_CLI", 1)[1].split("ENDM", 1)[0]
    for needle in (
        "cc_rev02_pp_directive:", "cc_rev02_pp_name:", "SYS_STAT", "SYS_OPEN", "SYS_READ", "SYS_CLOSE",
        "CC_REV02_INCLUDE_CAP   EQU 64", "cc_rev02_includebuf", "cc_rev02_parent_read_left",
        "CC_REV02_MACRO_CAP     EQU 16", "CC_REV02_MACRO_REPL_CAP EQU 32",
        "cc_rev02_pp_define_word_start:", "cc_rev02_macro_try:", "cc_rev02_pp_system_c48:", "cc_rev02_pp_kw_c48",
    ):
        req(needle in block, "quoted-include product closure missing: " + needle)
    for forbidden in ("cc_p11pr_", "CC_P11PR", "source_crc", "source_sum", "source_sha", "identity_table"):
        req(forbidden.lower() not in block.lower(), "source-specialized marker in product include closure: " + forbidden)

    asm = out / "cc-include-gate.asm"
    main_bin = out / "cc-include-main.bin"
    gate_bin = out / "cc-include-gateway.bin"
    sym = out / "cc-include-gate.sym"
    asm.write_text(f'''    DEVICE ZXSPECTRUM48
    INCLUDE "{(root / "v1/include/zx48ux.inc").as_posix()}"
    INCLUDE "{(root / "v1/src/tools/cc.asm").as_posix()}"
cc_product_bss EQU $A000
ROOT_HANDLE EQU 1
HEADER_HANDLE EQU 2
    ORG $4000
fixture_start:
    EMIT_P1128_CC_OBJ1_WRITER
    EMIT_P1129_CC_TRANSACTION_ROUTINES
    EMIT_REV02_CC_PRODUCT_CLI

root_done: db 0
header_done: db 0
open_count: db 0
close_count: db 0
stat_count: db 0
mode: db 0

root_source:
    db '#define ANSWER 3 + 4',10
    db '#include "h.h"',10
    db 'int main(void){{return ANSWER;}}',10
root_source_end:
include_plain_source:
    db '#include "h.h"',10
    db 'int main(void){{return 7;}}',10
include_plain_source_end:
define_include_unused_source:
    db '#define ANSWER 3 + 4',10
    db '#include "h.h"',10
    db 'int main(void){{return 7;}}',10
define_include_unused_source_end:
define_single_source:
    db '#define ANSWER 7',10
    db 'int main(void){{return ANSWER;}}',10
define_single_source_end:
define_multi_source:
    db '#define ANSWER 3 + 4',10
    db 'int main(void){{return ANSWER;}}',10
define_multi_source_end:
recursive_source:
    db '#define SELF SELF',10
    db 'int main(void){{return SELF;}}',10
recursive_source_end:
function_macro_source:
    db '#define F(x) x',10
    db 'int main(void){{return 1;}}',10
function_macro_source_end:
generic_call_string_source:
    db 'int main(void){{cls();print_at(10,22,"hello");return 0;}}',10
generic_call_string_source_end:
header_source:
    db 'int helper(void);',10
header_source_end:
nested_header_source:
    db '#include "n.h"',10
    db 'int helper(void);',10
nested_header_source_end:
wrong_name_source:
    db '#include "../bad.h"',10
    db 'int main(void){{return 9;}}',10
wrong_name_source_end:
helper_source:
    db 'int helper(void){{return 9;}} int main(void){{helper();return 0;}}',10
helper_source_end:
builtin_c48_source:
    db '#include <c48.h>',10
    db 'int main(void){{cls();return 0;}}',10
builtin_c48_source_end:
local_scalar_source:
    db 'int main(void){{int x;int y;x=7;y=x+5;return y;}}',10
local_scalar_source_end:

fixture_reset:
    xor a
    ld (root_done),a
    ld (header_done),a
    ld (open_count),a
    ld (close_count),a
    ld (stat_count),a
    ld a,ROOT_HANDLE
    ld (cc_rev02_source_handle),a
    ret

test_define_single:
    ld a,6
    ld (mode),a
    call fixture_reset
    call cc_rev02_compile_stream
    ret c
    ld a,(stat_count)
    or a
    jp nz,test_fail
    ld a,(open_count)
    or a
    jp nz,test_fail
    ld hl,(cc_rev02_text_len)
    ld de,4
    or a
    sbc hl,de
    jp nz,test_fail
    ld hl,cc_rev02_text+1
    ld a,(hl)
    cp 7
    jp nz,test_fail
    inc hl
    ld a,(hl)
    or a
    jp nz,test_fail
    xor a
    ret


generic_call_compile_once:
    ld a,10
    ld (mode),a
    call fixture_reset
    call cc_rev02_compile_stream
    ret

test_generic_call_compile:
    call generic_call_compile_once
    ret

test_generic_call_symbols:
    ld a,10
    ld (mode),a
    call fixture_reset
    call cc_rev02_compile_stream
    ret c
    ld a,(cc_rev02_symbol_count)
    cp 4
    jp nz,test_fail
    xor a
    ret

test_generic_call_relocs:
    ld a,10
    ld (mode),a
    call fixture_reset
    call cc_rev02_compile_stream
    ret c
    ld a,(cc_rev02_reloc_count)
    cp 3
    jp nz,test_fail
    xor a
    ret

test_generic_call_text:
    ld a,10
    ld (mode),a
    call fixture_reset
    call cc_rev02_compile_stream
    ret c
    ld hl,(cc_rev02_text_len)
    ld de,25
    or a
    sbc hl,de
    jp nz,test_fail
    xor a
    ret

test_generic_call_obj:
    ld a,10
    ld (mode),a
    call fixture_reset
    call cc_rev02_compile_stream
    ret c
    ld hl,(cc_obj1_output_size)
    ld a,h
    or l
    jp z,test_fail
    xor a
    ret

test_builtin_c48:
    ld a,12
    ld (mode),a
    call fixture_reset
    call cc_rev02_compile_stream
    ret c
    ld a,(stat_count)
    or a
    jp nz,test_fail
    ld a,(open_count)
    or a
    jp nz,test_fail
    ld a,(close_count)
    or a
    jp nz,test_fail
    ld a,(cc_rev02_symbol_count)
    cp 2
    jp nz,test_fail
    ld a,(cc_rev02_reloc_count)
    cp 1
    jp nz,test_fail
    xor a
    ret

test_local_scalar_codegen:
    ld a,13
    ld (mode),a
    call fixture_reset
    call cc_rev02_compile_stream
    ret c
    ld a,(cc_rev02_symbol_count)
    cp 1
    jp nz,test_fail
    ld a,(cc_rev02_reloc_count)
    or a
    jp nz,test_fail
    call cc_rev02_text
    ld a,h
    or a
    jp nz,test_fail
    ld a,l
    cp 12
    jp nz,test_fail
    xor a
    ret

test_define_multi:
    ld a,7
    ld (mode),a
    call fixture_reset
    call cc_rev02_compile_stream
    ret c
    ld a,(stat_count)
    or a
    jp nz,test_fail
    ld a,(open_count)
    or a
    jp nz,test_fail
    ld hl,(cc_rev02_text_len)
    ld de,4
    or a
    sbc hl,de
    jp nz,test_fail
    ld hl,cc_rev02_text+1
    ld a,(hl)
    cp 7
    jp nz,test_fail
    inc hl
    ld a,(hl)
    or a
    jp nz,test_fail
    xor a
    ret

test_include_plain:
    ld a,8
    ld (mode),a
    call fixture_reset
    call cc_rev02_compile_stream
    ret c
    ld a,(open_count)
    cp 1
    jp nz,test_fail
    ld a,(close_count)
    cp 1
    jp nz,test_fail
    ld a,(stat_count)
    cp 1
    jp nz,test_fail
    ld hl,(cc_rev02_text_len)
    ld de,4
    or a
    sbc hl,de
    jp nz,test_fail
    ld hl,cc_rev02_text+1
    ld a,(hl)
    cp 7
    jp nz,test_fail
    inc hl
    ld a,(hl)
    or a
    jp nz,test_fail
    xor a
    ret

test_define_include_unused:
    ld a,9
    ld (mode),a
    call fixture_reset
    call cc_rev02_compile_stream
    ret c
    ld a,(open_count)
    cp 1
    jp nz,test_fail
    ld a,(close_count)
    cp 1
    jp nz,test_fail
    ld a,(stat_count)
    cp 1
    jp nz,test_fail
    ld hl,(cc_rev02_text_len)
    ld de,4
    or a
    sbc hl,de
    jp nz,test_fail
    ld hl,cc_rev02_text+1
    ld a,(hl)
    cp 7
    jp nz,test_fail
    inc hl
    ld a,(hl)
    or a
    jp nz,test_fail
    xor a
    ret

test_define_include_compile_only:
    xor a
    ld (mode),a
    call fixture_reset
    call cc_rev02_compile_stream
    ret

test_define_include_text:
    xor a
    ld (mode),a
    call fixture_reset
    call cc_rev02_compile_stream
    ret c
    ld hl,(cc_rev02_text_len)
    ld de,4
    or a
    sbc hl,de
    jp nz,test_fail
    ld hl,cc_rev02_text
    ld a,(hl)
    cp $21
    jp nz,test_fail
    inc hl
    ld a,(hl)
    cp 7
    jp nz,test_fail
    inc hl
    ld a,(hl)
    or a
    jp nz,test_fail
    inc hl
    ld a,(hl)
    cp $C9
    jp nz,test_fail
    xor a
    ret

test_include_ok:
    xor a
    ld (mode),a
    call fixture_reset
    call cc_rev02_compile_stream
    ret c
    ld a,(open_count)
    cp 1
    jp nz,test_fail
    ld a,(close_count)
    cp 1
    jp nz,test_fail
    ld a,(stat_count)
    cp 1
    jp nz,test_fail
    ld hl,(cc_rev02_text_len)
    ld de,4
    or a
    sbc hl,de
    jp nz,test_fail
    ld hl,cc_rev02_text
    ld a,(hl)
    cp $21
    jp nz,test_fail
    inc hl
    ld a,(hl)
    cp 7
    jp nz,test_fail
    inc hl
    ld a,(hl)
    or a
    jp nz,test_fail
    inc hl
    ld a,(hl)
    cp $C9
    jp nz,test_fail
    ld hl,(cc_obj1_output_size)
    ld a,h
    or l
    jp z,test_fail
    xor a
    ret

test_recursive_macro_reject:
    ld a,4
    ld (mode),a
    call fixture_reset
    call cc_rev02_compile_stream
    jp nc,test_fail
    cp E_NOTSUP
    jp nz,test_fail
    ld a,(stat_count)
    or a
    jp nz,test_fail
    ld a,(open_count)
    or a
    jp nz,test_fail
    xor a
    ret

test_function_macro_reject:
    ld a,5
    ld (mode),a
    call fixture_reset
    call cc_rev02_compile_stream
    jp nc,test_fail
    cp E_NOTSUP
    jp nz,test_fail
    ld a,(stat_count)
    or a
    jp nz,test_fail
    ld a,(open_count)
    or a
    jp nz,test_fail
    xor a
    ret

test_nested_reject:
    ld a,1
    ld (mode),a
    call fixture_reset
    call cc_rev02_compile_stream
    jp nc,test_fail
    cp E_NOTSUP
    jp nz,test_fail
    xor a
    ret

test_bad_name_reject:
    ld a,2
    ld (mode),a
    call fixture_reset
    call cc_rev02_compile_stream
    jp nc,test_fail
    cp E_INVAL
    jp nz,test_fail
    ld a,(stat_count)
    or a
    jp nz,test_fail
    ld a,(open_count)
    or a
    jp nz,test_fail
    xor a
    ret

test_wrong_type_reject:
    ld a,3
    ld (mode),a
    call fixture_reset
    call cc_rev02_compile_stream
    jp nc,test_fail
    cp E_FORMAT
    jp nz,test_fail
    ld a,(stat_count)
    cp 1
    jp nz,test_fail
    ld a,(open_count)
    or a
    jp nz,test_fail
    xor a
    ret

test_fail:
    ld a,E_FORMAT
    scf
    ret

fixture_end:
    SAVEBIN "{main_bin.as_posix()}",fixture_start,fixture_end-fixture_start

    ORG $E000
gateway_start:
    cp SYS_READ
    jp z,gate_read
    cp SYS_STAT
    jp z,gate_stat
    cp SYS_OPEN
    jp z,gate_open
    cp SYS_CLOSE
    jp z,gate_close
    ld a,E_NOTSUP
    scf
    ret

gate_stat:
    ld a,(stat_count)
    inc a
    ld (stat_count),a
    ld e,(hl)
    inc hl
    ld d,(hl)
    inc hl
    ld c,(hl)
    inc hl
    ld b,(hl)
    ex de,hl
    ld a,(hl)
    cp 'h'
    jp nz,gate_bad
    inc hl
    ld a,(hl)
    cp '.'
    jp nz,gate_bad
    inc hl
    ld a,(hl)
    cp 'h'
    jp nz,gate_bad
    inc hl
    ld a,(hl)
    or a
    jp nz,gate_bad
    ld h,b
    ld l,c
    ld a,(mode)
    cp 3
    ld a,OBJ_C
    jr nz,gate_stat_type
    ld a,OBJ_DAT
gate_stat_type:
    ld (hl),a
    xor a
    ret

gate_open:
    ld a,(open_count)
    inc a
    ld (open_count),a
    ld a,(hl)
    cp 'h'
    jp nz,gate_bad
    ld hl,HEADER_HANDLE
    xor a
    ret

gate_close:
    ld a,(close_count)
    inc a
    ld (close_count),a
    xor a
    ret

test_generic_helper_definition:
    ld a,11
    ld (mode),a
    call fixture_reset
    call cc_rev02_compile_stream
    ret c
    ld a,(cc_rev02_symbol_count)
    cp 2
    jp nz,test_fail
    ld a,(cc_rev02_reloc_count)
    cp 1
    jp nz,test_fail
    ld hl,cc_rev02_symbols
    ld a,(hl)
    cp 'h'
    jp nz,test_fail
    ld hl,cc_rev02_symbols+CC_OBJ1_SYMBOL_SIZE
    ld a,(hl)
    cp 'm'
    jp nz,test_fail
    xor a
    ret

gate_read:
    ld a,e
    cp ROOT_HANDLE
    jp z,gate_read_root
    cp HEADER_HANDLE
    jp z,gate_read_header
    jp gate_bad

gate_read_root:
    ld a,(root_done)
    or a
    jp z,gate_read_root_first
    cp 1
    jp nz,gate_read_eof
    ld a,(mode)
    or a
    jp nz,gate_read_eof
    ld a,2
    ld (root_done),a
    ex de,hl
    ld hl,root_source+CC_REV02_READ_CAP
    ld bc,root_source_end-root_source-CC_REV02_READ_CAP
    ldir
    ld hl,root_source_end-root_source-CC_REV02_READ_CAP
    xor a
    ret
gate_read_root_first:
    ld a,1
    ld (root_done),a
    ex de,hl
    ld a,(mode)
    cp 2
    jp z,gate_read_bad_name
    cp 4
    jp z,gate_read_recursive
    cp 5
    jp z,gate_read_function_macro
    cp 6
    jp z,gate_read_define_single
    cp 7
    jp z,gate_read_define_multi
    cp 8
    jp z,gate_read_include_plain
    cp 9
    jp z,gate_read_define_include_unused
    cp 10
    jp z,gate_read_generic_call_string
    cp 11
    jp z,gate_read_helper
    cp 12
    jp z,gate_read_builtin_c48
    cp 13
    jp z,gate_read_local_scalar
    ld hl,root_source
    ld bc,CC_REV02_READ_CAP
    ldir
    ld hl,CC_REV02_READ_CAP
    xor a
    ret
gate_read_local_scalar:
    ld hl,local_scalar_source
    ld bc,local_scalar_source_end-local_scalar_source
    ldir
    ld hl,local_scalar_source_end-local_scalar_source
    xor a
    ret
gate_read_builtin_c48:
    ld hl,builtin_c48_source
    ld bc,builtin_c48_source_end-builtin_c48_source
    ldir
    ld hl,builtin_c48_source_end-builtin_c48_source
    xor a
    ret
gate_read_helper:
    ld hl,helper_source
    ld bc,helper_source_end-helper_source
    ldir
    ld hl,helper_source_end-helper_source
    xor a
    ret

gate_read_bad_name:
    ld hl,wrong_name_source
    ld bc,wrong_name_source_end-wrong_name_source
    ldir
    ld hl,wrong_name_source_end-wrong_name_source
    xor a
    ret
gate_read_recursive:
    ld hl,recursive_source
    ld bc,recursive_source_end-recursive_source
    ldir
    ld hl,recursive_source_end-recursive_source
    xor a
    ret
gate_read_function_macro:
    ld hl,function_macro_source
    ld bc,function_macro_source_end-function_macro_source
    ldir
    ld hl,function_macro_source_end-function_macro_source
    xor a
    ret
gate_read_include_plain:
    ld hl,include_plain_source
    ld bc,include_plain_source_end-include_plain_source
    ldir
    ld hl,include_plain_source_end-include_plain_source
    xor a
    ret
gate_read_define_include_unused:
    ld hl,define_include_unused_source
    ld bc,define_include_unused_source_end-define_include_unused_source
    ldir
    ld hl,define_include_unused_source_end-define_include_unused_source
    xor a
    ret
gate_read_define_single:
    ld hl,define_single_source
    ld bc,define_single_source_end-define_single_source
    ldir
    ld hl,define_single_source_end-define_single_source
    xor a
    ret
gate_read_define_multi:
    ld hl,define_multi_source
    ld bc,define_multi_source_end-define_multi_source
    ldir
    ld hl,define_multi_source_end-define_multi_source
    xor a
    ret
gate_read_generic_call_string:
    ld hl,generic_call_string_source
    ld bc,generic_call_string_source_end-generic_call_string_source
    ldir
    ld hl,generic_call_string_source_end-generic_call_string_source
    xor a
    ret

gate_read_header:
    ld a,(header_done)
    or a
    jr nz,gate_read_eof
    ld a,1
    ld (header_done),a
    ex de,hl
    ld a,(mode)
    cp 1
    jp z,gate_read_nested
    ld hl,header_source
    ld bc,header_source_end-header_source
    ldir
    ld hl,header_source_end-header_source
    xor a
    ret
gate_read_nested:
    ld hl,nested_header_source
    ld bc,nested_header_source_end-nested_header_source
    ldir
    ld hl,nested_header_source_end-nested_header_source
    xor a
    ret

gate_read_eof:
    ld hl,0
    xor a
    ret

gate_bad:
    ld a,E_FORMAT
    scf
    ret

gateway_end:
    SAVEBIN "{gate_bin.as_posix()}",gateway_start,gateway_end-gateway_start
''', encoding="utf-8", newline="\n")

    sj = root / "tools/runtime/sjasmplus/bin/sjasmplus"
    req(sj.is_file(), "project assembler missing")
    run([sj, "--nologo", f"--sym={sym.as_posix()}", asm.as_posix()], out)
    req(main_bin.is_file() and gate_bin.is_file(), "fixture binaries missing")
    syms = symbols(sym)
    names = ("test_define_single", "test_generic_call_compile", "test_generic_call_symbols", "test_generic_call_relocs", "test_generic_call_text", "test_generic_call_obj", "test_builtin_c48", "test_local_scalar_codegen", "test_define_multi", "test_include_plain", "test_define_include_unused", "test_define_include_compile_only", "test_define_include_text", "test_include_ok", "test_generic_helper_definition", "test_recursive_macro_reject", "test_function_macro_reject", "test_nested_reject", "test_bad_name_reject", "test_wrong_type_reject")
    for name in names:
        req(name in syms, "fixture symbol missing: " + name)

    req(len(b"#define ANSWER 3 + 4\n#include \"h.h\"\nint main(void){return ANSWER;}\n") > 64,
        "combined define/include fixture must cross the 64-byte root read boundary")
    checks = {"assemble": "PASS", "anti_specialization": "PASS"}
    if not ns.assemble_only:
        driver = root / "v1/tools-host/test-driver"
        sys.path.insert(0, str(driver))
        import phase1  # type: ignore
        from fuse_harness import FAIL_PC, PASS_PC, run_sna  # type: ignore
        main_bytes = main_bin.read_bytes()
        gate_bytes = gate_bin.read_bytes()

        def patch(ram: bytearray) -> None:
            ram[0:len(main_bytes)] = main_bytes
            start = 0xE000 - 0x4000
            ram[start:start + len(gate_bytes)] = gate_bytes

        for name in names:
            print("REV02 CC INCLUDE TEST " + name, flush=True)
            code = (b"\xF3" + phase1._ld_sp(0xBFC0) + phase1._call(syms[name])
                    + phase1._jp_c(FAIL_PC) + phase1._jp(PASS_PC))
            run_sna(root, code, patch=patch, timeout=20)
            checks[name] = "PASS"

    report = {
        "schema": 1,
        "kind": "rev02-stage-e-cc-quoted-include-gate",
        "status": "PASS",
        "checks": checks,
        "assertions": {
            "one_level_local_include": "PASS" if not ns.assemble_only else "ASSEMBLED",
            "include_without_define": "PASS" if not ns.assemble_only else "ASSEMBLED",
            "define_survives_include_when_unused": "PASS" if not ns.assemble_only else "ASSEMBLED",
            "define_include_compile_only": "PASS" if not ns.assemble_only else "ASSEMBLED",
            "define_include_text_exact": "PASS" if not ns.assemble_only else "ASSEMBLED",
            "object_like_define_single_token": "PASS" if not ns.assemble_only else "ASSEMBLED",
            "object_like_define_multitoken": "PASS" if not ns.assemble_only else "ASSEMBLED",
            "generic_call_string_relocations": "PASS" if not ns.assemble_only else "ASSEMBLED",
            "generic_helper_definition_and_call": "PASS" if not ns.assemble_only else "ASSEMBLED",
            "builtin_c48_header": "PASS" if not ns.assemble_only else "ASSEMBLED",
            "generic_local_scalar_assignment_codegen": "PASS" if not ns.assemble_only else "ASSEMBLED",
            "recursive_macro_rejected": "PASS" if not ns.assemble_only else "ASSEMBLED",
            "function_macro_rejected": "PASS" if not ns.assemble_only else "ASSEMBLED",
            "ordinary_stat_open_read_close": "PASS" if not ns.assemble_only else "ASSEMBLED",
            "parent_unread_window_preserved": "PASS" if not ns.assemble_only else "ASSEMBLED",
            "parent_refill_after_include": "PASS" if not ns.assemble_only else "ASSEMBLED",
            "nested_include_rejected": "PASS" if not ns.assemble_only else "ASSEMBLED",
            "portable_basename_enforced_before_lookup": "PASS" if not ns.assemble_only else "ASSEMBLED",
            "wrong_object_type_rejected_before_open": "PASS" if not ns.assemble_only else "ASSEMBLED",
            "source_identity_dispatch_absent": "PASS",
        },
    }
    (out / "CC-INCLUDE-GATE.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print("REV02 STAGE E CC QUOTED INCLUDE GATE PASS" + (" (ASSEMBLE-ONLY)" if ns.assemble_only else ""))


if __name__ == "__main__":
    main()