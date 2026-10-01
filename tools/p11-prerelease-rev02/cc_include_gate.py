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
    INCLUDE "{(root / "v1/src/libc48/int_runtime.asm").as_posix()}"
cc_product_bss EQU $A000
ROOT_HANDLE EQU 1
HEADER_HANDLE EQU 2
    ORG $4000
fixture_start:
    EMIT_P1128_CC_OBJ1_WRITER
    EMIT_P1129_CC_TRANSACTION_ROUTINES
    EMIT_C48_INT_RUNTIME
    EMIT_REV02_CC_PRODUCT_CLI

root_done: db 0
fixture_source_ptr: dw 0
fixture_source_left: dw 0
header_done: db 0
open_count: db 0
close_count: db 0
stat_count: db 0
mode: db 0
probe_seen: db 0
probe_bad: db 0
probe_symbol: db 0
mul_symbol: db 0
div_symbol: db 0
shl_symbol: db 0
shr_symbol: db 0
cmp_symbol: db 0
divzero_seen: db 0
patch_left: db 0
patch_sym: db 0
patch_reloc_off: dw 0
patch_symbol_val: dw 0

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
dynamic_call_source:
    db 'int main(void){{int x;x=1;probe(x,x+1,3,4,5,6);return 0;}}',10
dynamic_call_source_end:
runtime_muldiv_source:
    db 'int main(void){{int x;int y;x=7;y=3;return x*y+x/y+x%y;}}',10
runtime_muldiv_source_end:
runtime_bitwise_source:
    db 'int main(void){{int x;int y;x=3855;y=243;return (x&y)^(x|y);}}',10
runtime_bitwise_source_end:
runtime_shift_source:
    db 'int main(void){{int x;x=3;return (x<<4)+(x>>1);}}',10
runtime_shift_source_end:
runtime_cmp_a_source:
    db 'int main(void){{int x;x=-3;return (x<2)+(x>=2)+(x!=2);}}',10
runtime_cmp_a_source_end:
runtime_cmp_b_source:
    db 'int main(void){{int x;x=-3;return (x<=2)+(x>2)+(x==2);}}',10
runtime_cmp_b_source_end:
runtime_logic_a_source:
    db 'int main(void){{int x;x=0;return !x+(x&&(1/0));}}',10
runtime_logic_a_source_end:
runtime_logic_b_source:
    db 'int main(void){{int x;x=1;return !x+(x||(1/0));}}',10
runtime_logic_b_source_end:
postfix_local_source:
    db 'int main(void){{int x;x=4;x++;x--;return x++;}}',10
postfix_local_source_end:
if_else_source:
    db 'int main(void){{int x;x=1;if (x) x=4;else x=9;if (!x) x=7;else x=x+1;return x;}}',10
if_else_source_end:
while_source:
    db 'int main(void){{int x;int y;x=2;y=2;while(x){{while(y)y--;x--;}}return x+y;}}',10
while_source_end:
for_source:
    db 'int main(void){{int x;int y;for(x=3;x;x--){{for(y=2;y;y--){{}}}}return x+y;}}',10
for_source_end:
break_continue_source:
    db 'int main(void){{int i;int s;i=0;s=0;while(8-i){{i++;if(i-2);else continue;'
    db 'if(i-6);else break;s=s+i;}}for(i=0;5-i;i++){{if(i-1);else continue;s=s+1;}}return s;}}',10
break_continue_source_end:
nested_break_source:
    db 'int main(void){{int x;int y;int s;x=2;s=0;while(x){{y=3;while(y){{y--;if(y-1);else break;s=s+1;}}x--;}}return s;}}',10
nested_break_source_end:
break_outside_source:
    db 'int main(void){{break;return 0;}}',10
break_outside_source_end:
continue_outside_source:
    db 'int main(void){{continue;return 0;}}',10
continue_outside_source_end:
recursive_params_source:
    db 'int dive(int n,int a,int b,int c,int d);int main(void){{dive(3,1,2,3,4);return 0;}}'
    db 'int dive(int n,int a,int b,int c,int d){{if(!n){{if(a-4)return 1/0;if(b-8)return 1/0;'
    db 'if(c-12)return 1/0;if(d-16)return 1/0;return 0;}}dive(n-1,a+1,b+2,c+3,d+4);return 0;}}',10
recursive_params_source_end:
global_scalar_source:
    db 'int bump(void);int g;char c;int main(void){{g=2;c=1;bump();return g+c;}}'
    db 'int bump(void){{g=4;c=3;g++;return g++ + c;}}',10
global_scalar_source_end:
global_array_source:
    db 'int a[4];char c[3];int main(void){{int i;i=0;for(i=0;i<4;i++)a[i]=i+1;'
    db 'c[1]=5;a[2]++;return a[0]+a[1]+a[2]+a[3]+c[1];}}',10
global_array_source_end:
global_init_source:
    db 'int a[4]={{1,-2,3}};unsigned char c[3]={{5,6,7}};int g=9;'
    db 'int main(void){{a[1]=2;return a[0]+a[1]+a[2]+a[3]+c[2]+g;}}',10
global_init_source_end:
local_array_source:
    db 'int main(void){{int a[4];char c[3];int i;i=0;for(i=0;i<4;i++)a[i]=i+1;'
    db 'c[0]=2;c[1]=3;c[2]=4;a[2]++;return a[0]+a[1]+a[2]+a[3]+c[0]+c[1]+c[2];}}',10
local_array_source_end:
pointer_basic_source:
    db 'void add3(int *p){{*p=*p+3;}}void setc(char *p){{*p=9;}}'
    db 'int main(void){{int x;char c;x=4;c=1;add3(&x);setc(&c);return x+c;}}',10
pointer_basic_source_end:
local_pointer_assign_source:
    db 'int main(void){{char *p;p="ABC";return 66;}}',10
local_pointer_assign_source_end:
local_pointer_value_source:
    db 'int main(void){{char *p;p="ABC";return p;}}',10
local_pointer_value_source_end:
local_pointer_deref_source:
    db 'int main(void){{char *p;p="ABC";return *p;}}',10
local_pointer_deref_source_end:
local_pointer_source:
    db 'int main(void){{char *p;p="ABC";return p[1];}}',10
local_pointer_source_end:
char_literal_source:
    db "int main(void){{return 'A';}}",10
char_literal_source_end:
diag_s0:
    db '__s0',0
diag_p:
    db 'p',0
fixture_reset:
    xor a
    ld (root_done),a
    ld (fixture_source_ptr),a
    ld (fixture_source_ptr+1),a
    ld (fixture_source_left),a
    ld (fixture_source_left+1),a
    ld (header_done),a
    ld (open_count),a
    ld (close_count),a
    ld (stat_count),a
    ld (divzero_seen),a
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
    ld a,h
    or l
    jp z,test_fail
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

test_dynamic_call_abi:
    ld a,14
    ld (mode),a
    call fixture_reset
    xor a
    ld (probe_seen),a
    ld (probe_bad),a
    call cc_rev02_compile_stream
    ret c
    ld a,(cc_rev02_symbol_count)
    cp 2
    jp nz,test_fail
    ld a,(cc_rev02_reloc_count)
    cp 1
    jp nz,test_fail
    ld hl,probe_name
    call cc_rev02_symbol_find
    jp c,test_fail
    ld (probe_symbol),a
    ld a,(cc_rev02_reloc_count)
    ld b,a
    ld hl,cc_rev02_relocs
test_dynamic_find_reloc:
    ld a,b
    or a
    jp z,test_fail
    ld e,(hl)
    inc hl
    ld d,(hl)
    inc hl
    ld a,(probe_symbol)
    cp (hl)
    jr z,test_dynamic_patch_reloc
    ld de,4
    add hl,de
    djnz test_dynamic_find_reloc
    jp test_fail
test_dynamic_patch_reloc:
    ld hl,cc_rev02_text
    add hl,de
    ld de,probe_stub
    ld (hl),e
    inc hl
    ld (hl),d
    call cc_rev02_text
    ld a,(probe_seen)
    cp 1
    jp nz,test_fail
    ld a,(probe_bad)
    or a
    jp nz,test_fail
    xor a
    ret
probe_stub:
    ld a,1
    ld (probe_seen),a
    ld a,h
    or a
    jr nz,probe_mark_bad
    ld a,l
    cp 1
    jr nz,probe_mark_bad
    ld a,d
    or a
    jr nz,probe_mark_bad
    ld a,e
    cp 2
    jr nz,probe_mark_bad
    ld a,b
    or a
    jr nz,probe_mark_bad
    ld a,c
    cp 3
    jr nz,probe_mark_bad
    ld hl,2
    add hl,sp
    ld a,(hl)
    cp 4
    jr nz,probe_mark_bad
    inc hl
    ld a,(hl)
    or a
    jr nz,probe_mark_bad
    inc hl
    ld a,(hl)
    cp 5
    jr nz,probe_mark_bad
    inc hl
    ld a,(hl)
    or a
    jr nz,probe_mark_bad
    inc hl
    ld a,(hl)
    cp 6
    jr nz,probe_mark_bad
    inc hl
    ld a,(hl)
    or a
    jr nz,probe_mark_bad
    ld hl,0
    ret
probe_mark_bad:
    ld a,1
    ld (probe_bad),a
    ld hl,0
    ret
probe_name:
    db 'probe',0

test_runtime_muldiv_codegen:
    ld a,15
    ld (mode),a
    call fixture_reset
    call cc_rev02_compile_stream
    ret c
    ld hl,cc_rev02_rt_s16_mul
    call cc_rev02_symbol_find
    jp c,test_fail
    ld (mul_symbol),a
    ld hl,cc_rev02_rt_s16_divmod
    call cc_rev02_symbol_find
    jp c,test_fail
    ld (div_symbol),a
    ld a,(cc_rev02_reloc_count)
    cp 3
    jp nz,test_fail
    ld b,a
    ld ix,cc_rev02_relocs
test_runtime_patch_loop:
    ld e,(ix+0)
    ld d,(ix+1)
    ld a,(ix+2)
    ld c,a
    ld a,(mul_symbol)
    cp c
    jr z,test_runtime_patch_mul
    ld a,(div_symbol)
    cp c
    jp nz,test_fail
    ld hl,c48_s16_divmod
    jr test_runtime_patch_target
test_runtime_patch_mul:
    ld hl,c48_s16_mul
test_runtime_patch_target:
    push bc
    push ix
    push hl
    ld hl,cc_rev02_text
    add hl,de
    pop de
    ld (hl),e
    inc hl
    ld (hl),d
    pop ix
    pop bc
    ld de,CC_OBJ1_RELOC_SIZE
    add ix,de
    djnz test_runtime_patch_loop
    call cc_rev02_text
    ld a,h
    or a
    jp nz,test_fail
    ld a,l
    cp 24
    jp nz,test_fail
    xor a
    ret

test_runtime_bitwise_codegen:
    ld a,16
    ld (mode),a
    call fixture_reset
    call cc_rev02_compile_stream
    ret c
    call cc_rev02_text
    ld de,4092
    or a
    sbc hl,de
    jp nz,test_fail
    xor a
    ret

test_runtime_shift_codegen:
    ld a,17
    ld (mode),a
    call fixture_reset
    call cc_rev02_compile_stream
    ret c
    ld hl,cc_rev02_rt_s16_shl
    call cc_rev02_symbol_find
    jp c,test_fail
    ld (shl_symbol),a
    ld hl,cc_rev02_rt_s16_shr
    call cc_rev02_symbol_find
    jp c,test_fail
    ld (shr_symbol),a
    ld a,(cc_rev02_reloc_count)
    cp 2
    jp nz,test_fail
    ld b,a
    ld ix,cc_rev02_relocs
test_shift_patch_loop:
    ld e,(ix+0)
    ld d,(ix+1)
    ld a,(ix+2)
    ld c,a
    ld a,(shl_symbol)
    cp c
    jr z,test_shift_patch_shl
    ld a,(shr_symbol)
    cp c
    jp nz,test_fail
    ld hl,c48_s16_shr
    jr test_shift_patch_target
test_shift_patch_shl:
    ld hl,c48_s16_shl
test_shift_patch_target:
    push bc
    push ix
    push hl
    ld hl,cc_rev02_text
    add hl,de
    pop de
    ld (hl),e
    inc hl
    ld (hl),d
    pop ix
    pop bc
    ld de,CC_OBJ1_RELOC_SIZE
    add ix,de
    djnz test_shift_patch_loop
    call cc_rev02_text
    ld a,h
    or a
    jp nz,test_fail
    ld a,l
    cp 49
    jp nz,test_fail
    xor a
    ret

test_patch_cmp_relocs:
    ld hl,cc_rev02_rt_cmp_s16
    call cc_rev02_symbol_find
    ret c
    ld (cmp_symbol),a
    ld a,(cc_rev02_reloc_count)
    cp 3
    jr nz,test_patch_cmp_bad
    ld b,a
    ld ix,cc_rev02_relocs
test_patch_cmp_loop:
    ld a,(ix+2)
    ld c,a
    ld a,(cmp_symbol)
    cp c
    jr nz,test_patch_cmp_bad
    ld e,(ix+0)
    ld d,(ix+1)
    push bc
    push ix
    ld hl,cc_rev02_text
    add hl,de
    ld de,c48_cmp_s16
    ld (hl),e
    inc hl
    ld (hl),d
    pop ix
    pop bc
    ld de,CC_OBJ1_RELOC_SIZE
    add ix,de
    djnz test_patch_cmp_loop
    xor a
    ret
test_patch_cmp_bad:
    ld a,E_FORMAT
    scf
    ret

test_runtime_compare_a:
    ld a,18
    ld (mode),a
    call fixture_reset
    call cc_rev02_compile_stream
    ret c
    call test_patch_cmp_relocs
    ret c
    call cc_rev02_text
    ld a,h
    or a
    jp nz,test_fail
    ld a,l
    cp 2
    jp nz,test_fail
    xor a
    ret

test_runtime_compare_b:
    ld a,19
    ld (mode),a
    call fixture_reset
    call cc_rev02_compile_stream
    ret c
    call test_patch_cmp_relocs
    ret c
    call cc_rev02_text
    ld a,h
    or a
    jp nz,test_fail
    ld a,l
    cp 1
    jp nz,test_fail
    xor a
    ret

test_patch_logic_relocs:
    ld a,(cc_rev02_reloc_count)
    ld (patch_left),a
    ld ix,cc_rev02_relocs
test_patch_logic_loop:
    ld a,(patch_left)
    or a
    ret z
    ld e,(ix+0)
    ld d,(ix+1)
    ld (patch_reloc_off),de
    ld a,(ix+2)
    ld (patch_sym),a
    call cc_rev02_symbol_ptr_for_index
    ld de,16
    add hl,de
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld (patch_symbol_val),de
    inc hl
    ld a,(hl)
    or a
    jr z,test_patch_logic_undef
    cp 1
    jr z,test_patch_logic_text
    cp 2
    jr z,test_patch_logic_bss
    jp test_fail

test_patch_logic_text:
    ld hl,cc_rev02_text
    ld de,(patch_reloc_off)
    add hl,de
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld hl,(patch_symbol_val)
    add hl,de
    ld de,cc_rev02_text
    add hl,de
    ex de,hl
    jr test_patch_logic_write

test_patch_logic_bss:
    ld hl,cc_rev02_text
    ld de,(patch_reloc_off)
    add hl,de
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld hl,(cc_rev02_text_len)
    add hl,de
    ld de,(patch_symbol_val)
    add hl,de
    ld de,cc_rev02_text
    add hl,de
    ex de,hl
    jr test_patch_logic_write

test_patch_logic_undef:
    ld hl,cc_rev02_rt_cmp_s16
    call cc_rev02_symbol_find
    jr c,test_patch_logic_undef_div
    ld c,a
    ld a,(patch_sym)
    cp c
    jr nz,test_patch_logic_undef_div
    ld de,c48_cmp_s16
    jr test_patch_logic_write
test_patch_logic_undef_div:
    ld hl,cc_rev02_rt_s16_divmod
    call cc_rev02_symbol_find
    jp c,test_fail
    ld c,a
    ld a,(patch_sym)
    cp c
    jp nz,test_fail
    ld de,c48_s16_divmod

test_patch_logic_write:
    ld hl,cc_rev02_text
    ld bc,(patch_reloc_off)
    add hl,bc
    ld (hl),e
    inc hl
    ld (hl),d
    ld de,CC_OBJ1_RELOC_SIZE
    add ix,de
    ld hl,patch_left
    dec (hl)
    jp test_patch_logic_loop

test_runtime_logic_a:
    ld a,20
    ld (mode),a
    call fixture_reset
    call cc_rev02_compile_stream
    ret c
    ld a,(cc_rev02_symbol_count)
    cp 2
    jp nz,test_fail
    call test_patch_logic_relocs
    ret c
    call cc_rev02_text
    ld a,(divzero_seen)
    or a
    jp nz,test_fail
    ld a,h
    or a
    jp nz,test_fail
    ld a,l
    cp 1
    jp nz,test_fail
    xor a
    ret

test_runtime_logic_b:
    ld a,21
    ld (mode),a
    call fixture_reset
    call cc_rev02_compile_stream
    ret c
    ld a,(cc_rev02_symbol_count)
    cp 2
    jp nz,test_fail
    call test_patch_logic_relocs
    ret c
    call cc_rev02_text
    ld a,(divzero_seen)
    or a
    jp nz,test_fail
    ld a,h
    or a
    jp nz,test_fail
    ld a,l
    cp 1
    jp nz,test_fail
    xor a
    ret

test_postfix_local_codegen:
    ld a,22
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
    cp 4
    jp nz,test_fail
    xor a
    ret

test_if_else_codegen:
    ld a,23
    ld (mode),a
    call fixture_reset
    call cc_rev02_compile_stream
    ret c
    ld a,(cc_rev02_symbol_count)
    cp 1
    jp nz,test_fail
    ld a,(cc_rev02_reloc_count)
    cp 4
    jp nz,test_fail
    call test_patch_logic_relocs
    ret c
    call cc_rev02_text
    ld a,h
    or a
    jp nz,test_fail
    ld a,l
    cp 5
    jp nz,test_fail
    xor a
    ret

test_while_codegen:
    ld a,24
    ld (mode),a
    call fixture_reset
    call cc_rev02_compile_stream
    ret c
    ld a,(cc_rev02_symbol_count)
    cp 1
    jp nz,test_fail
    ld a,(cc_rev02_reloc_count)
    cp 4
    jp nz,test_fail
    call test_patch_logic_relocs
    ret c
    call cc_rev02_text
    ld a,h
    or l
    jp nz,test_fail
    xor a
    ret

test_for_codegen:
    ld a,25
    ld (mode),a
    call fixture_reset
    call cc_rev02_compile_stream
    ret c
    ld a,(cc_rev02_symbol_count)
    cp 1
    jp nz,test_fail
    ld a,(cc_rev02_reloc_count)
    cp 8
    jp nz,test_fail
    call test_patch_logic_relocs
    ret c
    call cc_rev02_text
    ld a,h
    or l
    jp nz,test_fail
    xor a
    ret

test_break_continue_codegen:
    ld a,26
    ld (mode),a
    call fixture_reset
    call cc_rev02_compile_stream
    ret c
    ld a,(cc_rev02_symbol_count)
    cp 1
    jp nz,test_fail
    call test_patch_logic_relocs
    ret c
    call cc_rev02_text
    ld a,h
    or a
    jp nz,test_fail
    ld a,l
    cp 17
    jp nz,test_fail
    xor a
    ret

test_nested_break_codegen:
    ld a,27
    ld (mode),a
    call fixture_reset
    call cc_rev02_compile_stream
    ret c
    ld a,(cc_rev02_symbol_count)
    cp 1
    jp nz,test_fail
    call test_patch_logic_relocs
    ret c
    call cc_rev02_text
    ld a,h
    or a
    jp nz,test_fail
    ld a,l
    cp 2
    jp nz,test_fail
    xor a
    ret

test_break_outside_reject:
    ld a,28
    ld (mode),a
    call fixture_reset
    call cc_rev02_compile_stream
    jp nc,test_fail
    cp E_NOTSUP
    jp nz,test_fail
    xor a
    ret

test_continue_outside_reject:
    ld a,29
    ld (mode),a
    call fixture_reset
    call cc_rev02_compile_stream
    jp nc,test_fail
    cp E_NOTSUP
    jp nz,test_fail
    xor a
    ret

test_recursive_params_codegen:
    ld a,30
    ld (mode),a
    call fixture_reset
    call cc_rev02_compile_stream
    ret c
    ld a,(cc_rev02_symbol_count)
    cp 3
    jp nz,test_fail
    call test_patch_logic_relocs
    ret c
    call cc_rev02_text
    ld a,(divzero_seen)
    or a
    jp nz,test_fail
    ld a,h
    or l
    jp nz,test_fail
    xor a
    ret

test_global_scalar_codegen:
    ld a,31
    ld (mode),a
    call fixture_reset
    call cc_rev02_compile_stream
    ret c
    ld hl,(cc_obj1_bss_size)
    ld a,h
    or a
    jp nz,test_fail
    ld a,l
    cp 3
    jp nz,test_fail
    ld a,(cc_rev02_symbol_count)
    cp 4
    jp nz,test_fail
    call test_patch_logic_relocs
    ret c
    call cc_rev02_text
    ld a,h
    or a
    jp nz,test_fail
    ld a,l
    cp 9
    jp nz,test_fail
    xor a
    ret

test_global_array_compile:
    ld a,32
    ld (mode),a
    call fixture_reset
    call cc_rev02_compile_stream
    ret

test_global_array_bss:
    ld a,32
    ld (mode),a
    call fixture_reset
    call cc_rev02_compile_stream
    ret c
    ld hl,(cc_obj1_bss_size)
    ld a,h
    or a
    jp nz,test_fail
    ld a,l
    cp 11
    jp nz,test_fail
    xor a
    ret

test_global_array_symbols:
    ld a,32
    ld (mode),a
    call fixture_reset
    call cc_rev02_compile_stream
    ret c
    ; a, c, main, and the ordinary comparison helper used by i<4.
    ld a,(cc_rev02_symbol_count)
    cp 4
    jp nz,test_fail
    xor a
    ret

test_global_array_patch:
    ld a,32
    ld (mode),a
    call fixture_reset
    call cc_rev02_compile_stream
    ret c
    call test_patch_logic_relocs
    ret

test_global_array_codegen:
    ld a,32
    ld (mode),a
    call fixture_reset
    call cc_rev02_compile_stream
    ret c
    ld hl,(cc_obj1_bss_size)
    ld a,h
    or a
    jp nz,test_fail
    ld a,l
    cp 11
    jp nz,test_fail
    ld a,(cc_rev02_symbol_count)
    cp 4
    jp nz,test_fail
    call test_patch_logic_relocs
    ret c
    call cc_rev02_text
    ld a,h
    or a
    jp nz,test_fail
    ld a,l
    cp 16
    jp nz,test_fail
    xor a
    ret

call_compiled_main:
    ld hl,cc_rev02_kw_main
    call cc_rev02_symbol_find
    jp c,test_fail
    call cc_rev02_symbol_ptr_for_index
    ld de,16
    add hl,de
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld hl,cc_rev02_text
    add hl,de
    jp (hl)

test_global_init_codegen:
    ld a,33
    ld (mode),a
    call fixture_reset
    call cc_rev02_compile_stream
    ret c
    ld hl,(cc_obj1_bss_size)
    ld a,h
    or l
    jp nz,test_fail
    ld a,(cc_rev02_symbol_count)
    cp 4
    jp nz,test_fail
    call test_patch_logic_relocs
    ret c
    call call_compiled_main
    ld a,h
    or a
    jp nz,test_fail
    ld a,l
    cp 22
    jp nz,test_fail
    xor a
    ret

test_local_array_codegen:
    ld a,34
    ld (mode),a
    call fixture_reset
    call cc_rev02_compile_stream
    ret c
    ld hl,(cc_obj1_bss_size)
    ld a,h
    or l
    jp nz,test_fail
    ld a,(cc_rev02_symbol_count)
    cp 2
    jp nz,test_fail
    call test_patch_logic_relocs
    ret c
    call call_compiled_main
    ld a,h
    or a
    jp nz,test_fail
    ld a,l
    cp 20
    jp nz,test_fail
    xor a
    ret

test_pointer_basic_codegen:
    ld a,35
    ld (mode),a
    call fixture_reset
    call cc_rev02_compile_stream
    ret c
    ld hl,(cc_obj1_bss_size)
    ld a,h
    or l
    jp nz,test_fail
    ld a,(cc_rev02_symbol_count)
    cp 3
    jp nz,test_fail
    call test_patch_logic_relocs
    ret c
    call call_compiled_main
    ld a,h
    or a
    jp nz,test_fail
    ld a,l
    cp 16
    jp nz,test_fail
    xor a
    ret

test_local_pointer_assign_codegen:
    ld a,36
    ld (mode),a
    call fixture_reset
    call cc_rev02_compile_stream
    ret c
    call test_patch_logic_relocs
    ret c
    call call_compiled_main
    ld a,h
    or a
    jp nz,test_fail
    ld a,l
    cp 66
    jp nz,test_fail
    xor a
    ret

test_local_pointer_metadata:
    ld a,37
    ld (mode),a
    call fixture_reset
    call cc_rev02_compile_stream
    ret c
    ld hl,diag_p
    call cc_rev02_local_find
    jp c,test_fail
    ld a,(cc_rev02_local_symbol)
    call cc_rev02_local_size_ptr
    ld a,(hl)
    cp 2
    jp nz,test_fail
    ld a,(cc_rev02_local_symbol)
    call cc_rev02_local_kind_ptr
    ld a,(hl)
    cp 2
    jp nz,test_fail
    ld a,(cc_rev02_local_symbol)
    call cc_rev02_local_pointee_ptr
    ld a,(hl)
    cp 1
    jp nz,test_fail
    xor a
    ret

test_local_pointer_literal:
    ld a,37
    ld (mode),a
    call fixture_reset
    call cc_rev02_compile_stream
    ret c
    ld hl,diag_s0
    call cc_rev02_symbol_find
    jp c,test_fail
    call cc_rev02_symbol_ptr_for_index
    ld de,16
    add hl,de
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld hl,cc_rev02_text
    add hl,de
    ld a,(hl)
    cp 'A'
    jp nz,test_fail
    inc hl
    ld a,(hl)
    cp 'B'
    jp nz,test_fail
    inc hl
    ld a,(hl)
    cp 'C'
    jp nz,test_fail
    inc hl
    ld a,(hl)
    or a
    jp nz,test_fail
    xor a
    ret

test_local_pointer_value_codegen:
    ld a,37
    ld (mode),a
    call fixture_reset
    call cc_rev02_compile_stream
    ret c
    call test_patch_logic_relocs
    ret c
    call call_compiled_main
    push hl
    ld hl,diag_s0
    call cc_rev02_symbol_find
    jp c,test_fail
    call cc_rev02_symbol_ptr_for_index
    ld de,16
    add hl,de
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld hl,cc_rev02_text
    add hl,de
    pop de
    or a
    sbc hl,de
    jp nz,test_fail
    xor a
    ret

test_local_pointer_deref_codegen:
    ld a,38
    ld (mode),a
    call fixture_reset
    call cc_rev02_compile_stream
    ret c
    call test_patch_logic_relocs
    ret c
    call call_compiled_main
    ld a,h
    or a
    jp nz,test_fail
    ld a,l
    cp 65
    jp nz,test_fail
    xor a
    ret

test_local_pointer_codegen:
    ld a,39
    ld (mode),a
    call fixture_reset
    call cc_rev02_compile_stream
    ret c
    ld hl,(cc_obj1_bss_size)
    ld a,h
    or l
    jp nz,test_fail
    call test_patch_logic_relocs
    ret c
    call call_compiled_main
    ld a,h
    or a
    jp nz,test_fail
    ld a,l
    cp 66
    jp nz,test_fail
    xor a
    ret

test_character_literal_codegen:
    ld a,40
    ld (mode),a
    call fixture_reset
    call cc_rev02_compile_stream
    ret c
    call test_patch_logic_relocs
    ret c
    call call_compiled_main
    ld a,h
    or a
    jp nz,test_fail
    ld a,l
    cp 65
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
    call cc_rev02_text
    ld a,h
    or a
    jp nz,test_fail
    ld a,l
    cp 7
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
    call cc_rev02_text
    ld a,h
    or a
    jp nz,test_fail
    ld a,l
    cp 7
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
    call cc_rev02_text
    ld a,h
    or a
    jp nz,test_fail
    ld a,l
    cp 7
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
    cp SYS_EXIT
    jp z,gate_exit
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

gate_exit:
    ld a,1
    ld (divzero_seen),a
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
    cp 13
    jr c,gate_read_root_legacy_continue
    ex de,hl
    jp gate_read_fixture_chunk
gate_read_root_legacy_continue:
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
    cp 14
    jp z,gate_read_dynamic_call
    cp 15
    jp z,gate_read_runtime_muldiv
    cp 16
    jp z,gate_read_runtime_bitwise
    cp 17
    jp z,gate_read_runtime_shift
    cp 18
    jp z,gate_read_runtime_cmp_a
    cp 19
    jp z,gate_read_runtime_cmp_b
    cp 20
    jp z,gate_read_runtime_logic_a
    cp 21
    jp z,gate_read_runtime_logic_b
    cp 22
    jp z,gate_read_postfix_local
    cp 23
    jp z,gate_read_if_else
    cp 24
    jp z,gate_read_while
    cp 25
    jp z,gate_read_for
    cp 26
    jp z,gate_read_break_continue
    cp 27
    jp z,gate_read_nested_break
    cp 28
    jp z,gate_read_break_outside
    cp 29
    jp z,gate_read_continue_outside
    cp 30
    jp z,gate_read_recursive_params
    cp 31
    jp z,gate_read_global_scalar
    cp 32
    jp z,gate_read_global_array
    cp 33
    jp z,gate_read_global_init
    cp 34
    jp z,gate_read_local_array
    cp 35
    jp z,gate_read_pointer_basic
    cp 36
    jp z,gate_read_local_pointer_assign
    cp 37
    jp z,gate_read_local_pointer_value
    cp 38
    jp z,gate_read_local_pointer_deref
    cp 39
    jp z,gate_read_local_pointer
    cp 40
    jp z,gate_read_char_literal
    ld hl,root_source
    ld bc,CC_REV02_READ_CAP
    ldir
    ld hl,CC_REV02_READ_CAP
    xor a
    ret
gate_read_local_scalar:
    ld hl,local_scalar_source
    ld (fixture_source_ptr),hl
    ld hl,local_scalar_source_end-local_scalar_source
    ld (fixture_source_left),hl
    jp gate_read_fixture_chunk
gate_read_dynamic_call:
    ld hl,dynamic_call_source
    ld (fixture_source_ptr),hl
    ld hl,dynamic_call_source_end-dynamic_call_source
    ld (fixture_source_left),hl
    jp gate_read_fixture_chunk
gate_read_runtime_muldiv:
    ld hl,runtime_muldiv_source
    ld (fixture_source_ptr),hl
    ld hl,runtime_muldiv_source_end-runtime_muldiv_source
    ld (fixture_source_left),hl
    jp gate_read_fixture_chunk
gate_read_runtime_bitwise:
    ld hl,runtime_bitwise_source
    ld (fixture_source_ptr),hl
    ld hl,runtime_bitwise_source_end-runtime_bitwise_source
    ld (fixture_source_left),hl
    jp gate_read_fixture_chunk
gate_read_runtime_shift:
    ld hl,runtime_shift_source
    ld (fixture_source_ptr),hl
    ld hl,runtime_shift_source_end-runtime_shift_source
    ld (fixture_source_left),hl
    jp gate_read_fixture_chunk
gate_read_runtime_cmp_a:
    ld hl,runtime_cmp_a_source
    ld (fixture_source_ptr),hl
    ld hl,runtime_cmp_a_source_end-runtime_cmp_a_source
    ld (fixture_source_left),hl
    jp gate_read_fixture_chunk
gate_read_runtime_cmp_b:
    ld hl,runtime_cmp_b_source
    ld (fixture_source_ptr),hl
    ld hl,runtime_cmp_b_source_end-runtime_cmp_b_source
    ld (fixture_source_left),hl
    jp gate_read_fixture_chunk
gate_read_runtime_logic_a:
    ld hl,runtime_logic_a_source
    ld (fixture_source_ptr),hl
    ld hl,runtime_logic_a_source_end-runtime_logic_a_source
    ld (fixture_source_left),hl
    jp gate_read_fixture_chunk
gate_read_runtime_logic_b:
    ld hl,runtime_logic_b_source
    ld (fixture_source_ptr),hl
    ld hl,runtime_logic_b_source_end-runtime_logic_b_source
    ld (fixture_source_left),hl
    jp gate_read_fixture_chunk
gate_read_postfix_local:
    ld hl,postfix_local_source
    ld (fixture_source_ptr),hl
    ld hl,postfix_local_source_end-postfix_local_source
    ld (fixture_source_left),hl
    jp gate_read_fixture_chunk
gate_read_if_else:
    ld hl,if_else_source
    ld (fixture_source_ptr),hl
    ld hl,if_else_source_end-if_else_source
    ld (fixture_source_left),hl
    jp gate_read_fixture_chunk
gate_read_while:
    ld hl,while_source
    ld (fixture_source_ptr),hl
    ld hl,while_source_end-while_source
    ld (fixture_source_left),hl
    jp gate_read_fixture_chunk
gate_read_for:
    ld hl,for_source
    ld (fixture_source_ptr),hl
    ld hl,for_source_end-for_source
    ld (fixture_source_left),hl
    jp gate_read_fixture_chunk
gate_read_break_continue:
    ld hl,break_continue_source
    ld (fixture_source_ptr),hl
    ld hl,break_continue_source_end-break_continue_source
    ld (fixture_source_left),hl
    jp gate_read_fixture_chunk
gate_read_nested_break:
    ld hl,nested_break_source
    ld (fixture_source_ptr),hl
    ld hl,nested_break_source_end-nested_break_source
    ld (fixture_source_left),hl
    jp gate_read_fixture_chunk
gate_read_break_outside:
    ld hl,break_outside_source
    ld (fixture_source_ptr),hl
    ld hl,break_outside_source_end-break_outside_source
    ld (fixture_source_left),hl
    jp gate_read_fixture_chunk
gate_read_continue_outside:
    ld hl,continue_outside_source
    ld (fixture_source_ptr),hl
    ld hl,continue_outside_source_end-continue_outside_source
    ld (fixture_source_left),hl
    jp gate_read_fixture_chunk
gate_read_recursive_params:
    ld hl,recursive_params_source
    ld (fixture_source_ptr),hl
    ld hl,recursive_params_source_end-recursive_params_source
    ld (fixture_source_left),hl
    jp gate_read_fixture_chunk
gate_read_global_scalar:
    ld hl,global_scalar_source
    ld (fixture_source_ptr),hl
    ld hl,global_scalar_source_end-global_scalar_source
    ld (fixture_source_left),hl
    jp gate_read_fixture_chunk
gate_read_global_array:
    ld hl,global_array_source
    ld (fixture_source_ptr),hl
    ld hl,global_array_source_end-global_array_source
    ld (fixture_source_left),hl
    jp gate_read_fixture_chunk
gate_read_global_init:
    ld hl,global_init_source
    ld (fixture_source_ptr),hl
    ld hl,global_init_source_end-global_init_source
    ld (fixture_source_left),hl
    jp gate_read_fixture_chunk
gate_read_local_array:
    ld hl,local_array_source
    ld (fixture_source_ptr),hl
    ld hl,local_array_source_end-local_array_source
    ld (fixture_source_left),hl
    jp gate_read_fixture_chunk
gate_read_pointer_basic:
    ld hl,pointer_basic_source
    ld (fixture_source_ptr),hl
    ld hl,pointer_basic_source_end-pointer_basic_source
    ld (fixture_source_left),hl
    jp gate_read_fixture_chunk
gate_read_local_pointer_assign:
    ld hl,local_pointer_assign_source
    ld (fixture_source_ptr),hl
    ld hl,local_pointer_assign_source_end-local_pointer_assign_source
    ld (fixture_source_left),hl
    jp gate_read_fixture_chunk
gate_read_local_pointer_value:
    ld hl,local_pointer_value_source
    ld (fixture_source_ptr),hl
    ld hl,local_pointer_value_source_end-local_pointer_value_source
    ld (fixture_source_left),hl
    jp gate_read_fixture_chunk
gate_read_local_pointer_deref:
    ld hl,local_pointer_deref_source
    ld (fixture_source_ptr),hl
    ld hl,local_pointer_deref_source_end-local_pointer_deref_source
    ld (fixture_source_left),hl
    jp gate_read_fixture_chunk
gate_read_local_pointer:
    ld hl,local_pointer_source
    ld (fixture_source_ptr),hl
    ld hl,local_pointer_source_end-local_pointer_source
    ld (fixture_source_left),hl
    jp gate_read_fixture_chunk
gate_read_char_literal:
    ld hl,char_literal_source
    ld (fixture_source_ptr),hl
    ld hl,char_literal_source_end-char_literal_source
    ld (fixture_source_left),hl
    jp gate_read_fixture_chunk

; Direct source fixtures obey the compiler's bounded read contract exactly.
; DE is the caller destination. Each read returns at most CC_REV02_READ_CAP.
gate_read_fixture_chunk:
    ld hl,(fixture_source_left)
    ld a,h
    or l
    jp z,gate_read_eof
    ld bc,CC_REV02_READ_CAP
    ld a,h
    or a
    jr nz,gate_read_fixture_count_ready
    ld a,l
    cp CC_REV02_READ_CAP
    jr nc,gate_read_fixture_count_ready
    ld c,a
    ld b,0
gate_read_fixture_count_ready:
    push bc
    ld hl,(fixture_source_ptr)
    ldir
    ld (fixture_source_ptr),hl
    pop bc
    push bc
    ld hl,(fixture_source_left)
    or a
    sbc hl,bc
    ld (fixture_source_left),hl
    pop hl
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
    names = ("test_define_single", "test_generic_call_compile", "test_generic_call_symbols", "test_generic_call_relocs", "test_generic_call_text", "test_generic_call_obj", "test_builtin_c48", "test_local_scalar_codegen", "test_dynamic_call_abi", "test_runtime_muldiv_codegen", "test_runtime_bitwise_codegen", "test_runtime_shift_codegen", "test_runtime_compare_a", "test_runtime_compare_b", "test_runtime_logic_a", "test_runtime_logic_b", "test_postfix_local_codegen", "test_if_else_codegen", "test_while_codegen", "test_for_codegen", "test_break_continue_codegen", "test_nested_break_codegen", "test_break_outside_reject", "test_continue_outside_reject", "test_recursive_params_codegen", "test_global_scalar_codegen", "test_global_array_compile", "test_global_array_bss", "test_global_array_symbols", "test_global_array_patch", "test_global_array_codegen", "test_global_init_codegen", "test_local_array_codegen", "test_pointer_basic_codegen", "test_local_pointer_assign_codegen", "test_local_pointer_metadata", "test_local_pointer_literal", "test_local_pointer_value_codegen", "test_local_pointer_deref_codegen", "test_local_pointer_codegen", "test_character_literal_codegen", "test_define_multi", "test_include_plain", "test_define_include_unused", "test_define_include_compile_only", "test_define_include_text", "test_include_ok", "test_generic_helper_definition", "test_recursive_macro_reject", "test_function_macro_reject", "test_nested_reject", "test_bad_name_reject", "test_wrong_type_reject")
    for name in names:
        req(name in syms, "fixture symbol missing: " + name)

    req(len(b"#define ANSWER 3 + 4\n#include \"h.h\"\nint main(void){return ANSWER;}\n") > 64,
        "combined define/include fixture must cross the 64-byte root read boundary")
    req(len(b"int main(void){int x;x=1;if (x) x=4;else x=9;if (!x) x=7;else x=x+1;return x;}\n") > 64,
        "if/else fixture must cross the 64-byte direct-source read boundary")
    req(len(b"int main(void){int x;int y;x=2;y=2;while(x){while(y)y--;x--;}return x+y;}\n") > 64,
        "nested while fixture must cross the 64-byte direct-source read boundary")
    req(len(b"int main(void){int x;int y;for(x=3;x;x--){for(y=2;y;y--){}}return x+y;}\n") > 64,
        "nested for fixture must cross the 64-byte direct-source read boundary")
    req(len(b"int main(void){int a[4];char c[3];int i;i=0;for(i=0;i<4;i++)a[i]=i+1;c[0]=2;c[1]=3;c[2]=4;a[2]++;return a[0]+a[1]+a[2]+a[3]+c[0]+c[1]+c[2];}\n") > 64,
        "local-array fixture must cross the 64-byte direct-source read boundary")
    req(len(b"void add3(int *p){*p=*p+3;}void setc(char *p){*p=9;}int main(void){int x;char c;x=4;c=1;add3(&x);setc(&c);return x+c;}\n") > 64,
        "pointer fixture must cross the 64-byte direct-source read boundary")
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
            "define_include_text_semantic": "PASS" if not ns.assemble_only else "ASSEMBLED",
            "object_like_define_single_token": "PASS" if not ns.assemble_only else "ASSEMBLED",
            "object_like_define_multitoken": "PASS" if not ns.assemble_only else "ASSEMBLED",
            "generic_call_string_relocations": "PASS" if not ns.assemble_only else "ASSEMBLED",
            "generic_helper_definition_and_call": "PASS" if not ns.assemble_only else "ASSEMBLED",
            "builtin_c48_header": "PASS" if not ns.assemble_only else "ASSEMBLED",
            "generic_local_scalar_assignment_codegen": "PASS" if not ns.assemble_only else "ASSEMBLED",
            "generic_runtime_expression_c48_regcall_abi": "PASS" if not ns.assemble_only else "ASSEMBLED",
            "generic_runtime_int_mul_div_mod": "PASS" if not ns.assemble_only else "ASSEMBLED",
            "generic_runtime_int_bitwise": "PASS" if not ns.assemble_only else "ASSEMBLED",
            "generic_runtime_int_shifts": "PASS" if not ns.assemble_only else "ASSEMBLED",
            "generic_runtime_signed_comparisons": "PASS" if not ns.assemble_only else "ASSEMBLED",
            "generic_runtime_logical_short_circuit": "PASS" if not ns.assemble_only else "ASSEMBLED",
            "generic_local_postfix_inc_dec": "PASS" if not ns.assemble_only else "ASSEMBLED",
            "generic_character_literal": "PASS" if not ns.assemble_only else "ASSEMBLED",
            "generic_if_else_control_flow": "PASS" if not ns.assemble_only else "ASSEMBLED",
            "generic_nested_while_control_flow": "PASS" if not ns.assemble_only else "ASSEMBLED",
            "generic_nested_for_control_flow": "PASS" if not ns.assemble_only else "ASSEMBLED",
            "generic_break_continue_control_flow": "PASS" if not ns.assemble_only else "ASSEMBLED",
            "generic_nested_break_scope": "PASS" if not ns.assemble_only else "ASSEMBLED",
            "break_continue_outside_loop_rejected": "PASS" if not ns.assemble_only else "ASSEMBLED",
            "generic_regcall_parameter_spill_recursion": "PASS" if not ns.assemble_only else "ASSEMBLED",
            "generic_global_scalar_bss": "PASS" if not ns.assemble_only else "ASSEMBLED",
            "generic_global_array_bss_indexing": "PASS" if not ns.assemble_only else "ASSEMBLED",
            "generic_constant_global_initializers": "PASS" if not ns.assemble_only else "ASSEMBLED",
            "generic_direct_source_multiread": "PASS" if not ns.assemble_only else "ASSEMBLED",
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