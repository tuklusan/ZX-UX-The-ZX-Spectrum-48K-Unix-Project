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
        "CC_REV02_T_FLOAT", "cc_rev02_add_float_literal:", "SYS_FP_FROM_TEXT",
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
; Keep the proof image, its execution stack, product BSS, and the E000 syscall
; gateway disjoint.  Compiler growth made the old A000 harness BSS overlap the
; assembled proof image; this address is harness-only and is not a product ABI.
cc_product_bss EQU $C000
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
fp_count: db 0
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
integer_cast_source:
    db 'int g=(char)321;int main(void){{int x;x=321;return g+(char)x+(int)1+(unsigned int)2;}}',10
integer_cast_source_end:
pointer_post_source:
    db 'int main(void){{int a[2];int *p;char *q;a[0]=10;a[1]=20;p=&a[0];q="AB";return *p++ + *p + *q++ + *q;}}',10
pointer_post_source_end:
pointer_array_source:
    db 'char *v[2]={{"AB","CD"}};int main(void){{return v[1][0]+v[0][1];}}',10
pointer_array_source_end:
float_literal_source:
    db 'int probe(float a,float b,float c,float d){{return 7;}}'
    db 'int main(void){{probe(0.25,4.0F,2.5e-1,.5);return 0;}}',10
float_literal_source_end:
void_return_source:
    db 'void touch(int *p){{*p=9;return;}}int main(void){{int x;x=1;touch(&x);return x;}}',10
void_return_source_end:
call_expression_source:
    db 'int add(int a,int b){{return a+b;}}int main(void){{int x;x=add(3,4);return x+add(5,6);}}',10
call_expression_source_end:
mixed_call_arg_source:
    db 'int add(int a,int b){{return a+b;}}int main(void){{int x;x=3;return add(2+x,4);}}',10
mixed_call_arg_source_end:
local_array_init_source:
    db 'int main(void){{unsigned char a[8]={{24,60,126}};return a[0]+a[1]+a[2]+a[3]+a[7];}}',10
local_array_init_source_end:
local_pointer_init_source:
    db 'int main(void){{char *p="ABC";return p[1];}}',10
local_pointer_init_source_end:
nested_call_source:
    db 'int inc(int x){{return x+1;}}int sum(int a,int b){{return a+b;}}'
    db 'int main(void){{return sum(inc(3),inc(4))+inc(sum(1,2));}}',10
nested_call_source_end:
wide_call_source:
    db 'int wide9(int a,int b,int c,int d,int e,int f,int g,int h,int i){{'
    db 'int j;int k;int l;int m;int n;int o;int p;int q;int r;int s;'
    db 'return a+b+c+d+e+f+g+h+i;}}int main(void){{return wide9(1,2,3,4,5,6,7,8,9);}}',10
wide_call_source_end:
symbol_capacity_source:
    db 'int f00(void){{return 0;}}',10
    db 'int f01(void){{return 1;}}',10
    db 'int f02(void){{return 2;}}',10
    db 'int f03(void){{return 3;}}',10
    db 'int f04(void){{return 4;}}',10
    db 'int f05(void){{return 5;}}',10
    db 'int f06(void){{return 6;}}',10
    db 'int f07(void){{return 7;}}',10
    db 'int f08(void){{return 8;}}',10
    db 'int f09(void){{return 9;}}',10
    db 'int f10(void){{return 10;}}',10
    db 'int f11(void){{return 11;}}',10
    db 'int f12(void){{return 12;}}',10
    db 'int f13(void){{return 13;}}',10
    db 'int f14(void){{return 14;}}',10
    db 'int f15(void){{return 15;}}',10
    db 'int f16(void){{return 16;}}',10
    db 'int f17(void){{return 17;}}',10
    db 'int f18(void){{return 18;}}',10
    db 'int f19(void){{return 19;}}',10
    db 'int f20(void){{return 20;}}',10
    db 'int f21(void){{return 21;}}',10
    db 'int f22(void){{return 22;}}',10
    db 'int f23(void){{return 23;}}',10
    db 'int f24(void){{return 24;}}',10
    db 'int f25(void){{return 25;}}',10
    db 'int f26(void){{return 26;}}',10
    db 'int f27(void){{return 27;}}',10
    db 'int f28(void){{return 28;}}',10
    db 'int f29(void){{return 29;}}',10
    db 'int f30(void){{return 30;}}',10
    db 'int f31(void){{return 31;}}',10
    db 'int f32(void){{return 32;}}',10
    db 'int f33(void){{return 33;}}',10
    db 'int f34(void){{return 34;}}',10
    db 'int f35(void){{return 35;}}',10
    db 'int f36(void){{return 36;}}',10
    db 'int f37(void){{return 37;}}',10
    db 'int f38(void){{return 38;}}',10
    db 'int f39(void){{return 39;}}',10
    db 'int main(void){{return f39();}}',10
symbol_capacity_source_end:
unsigned_runtime_source:
    db 'unsigned int ug=44257u;unsigned int half(unsigned int x){{return x>>1;}}',10
    db 'int main(void){{unsigned int u;u=ug;if(half(u)!=22128u)return 1;',10
    db 'if(u%97u!=25u)return 2;if(!(u>1000u))return 3;',10
    db 'u=(unsigned int)-1;if((u>>15)!=1u)return 4;return 0;}}',10
unsigned_runtime_source_end:
main_argv_source:
    db 'int first(char *p){{return *p;}}',10
    db 'int main(int argc,char **argv){{if(argc<2)return 0;return first(argv[1]);}}',10
main_argv_source_end:
do_while_source:
    db 'int main(void){{int x;int y;x=0;y=0;do{{x++;if(x==2)continue;y=y+x;',10
    db 'if(x==4)break;}}while(x<6);return x*10+y;}}',10
do_while_source_end:
sizeof_source:
    db 'int ga[sizeof(int)+1];char gc;float gf[2];int main(void){{char c;int a[sizeof(int)+2];int *p;c=7;p=&a[0];',10
    db 'return sizeof(char)+sizeof(unsigned char)+sizeof(short)+sizeof(unsigned short)+',10
    db 'sizeof(int)+sizeof(unsigned int)+sizeof(float)+sizeof(void*)+sizeof ga+sizeof gf+sizeof a+',10
    db 'sizeof c+sizeof p+sizeof *p+sizeof(a[1])+sizeof("abc")+sizeof(',39,'A',39,')+sizeof(1)+',10
    db 'sizeof(1.0)+sizeof(c++)+sizeof(c+1)+10*(sizeof(int)>-1)+c;}}',10
sizeof_source_end:
sizeof_void_source:
    db 'int main(void){{return sizeof(void);}}',10
sizeof_void_source_end:
sizeof_type_source:
    db 'int main(void){{return sizeof(char)+sizeof(unsigned char)+sizeof(short)+',10
    db 'sizeof(unsigned short)+sizeof(int)+sizeof(unsigned int)+sizeof(float)+sizeof(void*);}}',10
sizeof_type_source_end:
sizeof_bounds_source:
    db 'int ga[sizeof(int)+1];int main(void){{int a[sizeof(int)+2];',10
    db 'return sizeof ga+sizeof a;}}',10
sizeof_bounds_source_end:
sizeof_object_source:
    db 'int main(void){{char c;int a[4];int *p;c=7;p=&a[0];',10
    db 'return sizeof c+sizeof p+sizeof *p+sizeof(a[1])+sizeof(c++)+sizeof(c+1);}}',10
sizeof_object_source_end:
sizeof_literal_source:
    db 'int main(void){{return sizeof("abc")+sizeof(',39,'A',39,')+sizeof(1)+sizeof(1.0);}}',10
sizeof_literal_source_end:
sizeof_unsigned_source:
    db 'int main(void){{return 10*(sizeof(int)>-1);}}',10
sizeof_unsigned_source_end:
argv0_text: db 'P',0
argv1_text: db 'Z',0
argv_words: dw argv0_text,argv1_text
fp_oracle_table:
    db 4,'0','.','2','5',0,0,0,0,$11,$12,$13,$14,$15
    db 3,'4','.','0',0,0,0,0,0,$21,$22,$23,$24,$25
    db 6,'2','.','5','e','-','1',0,0,$31,$32,$33,$34,$35
    db 2,'.','5',0,0,0,0,0,0,$41,$42,$43,$44,$45
fp_expected_bytes:
    db $11,$12,$13,$14,$15,$21,$22,$23,$24,$25
    db $31,$32,$33,$34,$35,$41,$42,$43,$44,$45
diag_f0:
    db '__f0',0
diag_f3:
    db '__f3',0
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
    ld (fp_count),a
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
    jp test_patch_logic_write

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
    jp test_patch_logic_write

test_patch_logic_undef:
    ld hl,cc_rev02_rt_cmp_s16
    call cc_rev02_symbol_find
    jr c,test_patch_logic_undef_cmp_u
    ld c,a
    ld a,(patch_sym)
    cp c
    jr nz,test_patch_logic_undef_cmp_u
    ld de,c48_cmp_s16
    jp test_patch_logic_write
test_patch_logic_undef_cmp_u:
    ld hl,cc_rev02_rt_cmp_u16
    call cc_rev02_symbol_find
    jr c,test_patch_logic_undef_div_s
    ld c,a
    ld a,(patch_sym)
    cp c
    jr nz,test_patch_logic_undef_div_s
    ld de,c48_cmp_u16
    jp test_patch_logic_write
test_patch_logic_undef_div_s:
    ld hl,cc_rev02_rt_s16_divmod
    call cc_rev02_symbol_find
    jr c,test_patch_logic_undef_div_u
    ld c,a
    ld a,(patch_sym)
    cp c
    jr nz,test_patch_logic_undef_div_u
    ld de,c48_s16_divmod
    jp test_patch_logic_write
test_patch_logic_undef_div_u:
    ld hl,cc_rev02_rt_u16_divmod
    call cc_rev02_symbol_find
    jr c,test_patch_logic_undef_shr_u
    ld c,a
    ld a,(patch_sym)
    cp c
    jr nz,test_patch_logic_undef_shr_u
    ld de,c48_u16_divmod
    jp test_patch_logic_write
test_patch_logic_undef_shr_u:
    ld hl,cc_rev02_rt_u16_shr
    call cc_rev02_symbol_find
    jr c,test_patch_logic_undef_mul
    ld c,a
    ld a,(patch_sym)
    cp c
    jr nz,test_patch_logic_undef_mul
    ld de,c48_u16_shr
    jp test_patch_logic_write
test_patch_logic_undef_mul:
    ld hl,cc_rev02_rt_s16_mul
    call cc_rev02_symbol_find
    jp c,test_fail
    ld c,a
    ld a,(patch_sym)
    cp c
    jp nz,test_fail
    ld de,c48_s16_mul

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
    cp $81                 ; plain char is unsigned; high bit carries unsigned metadata
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

test_integer_cast_codegen:
    ld a,41
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
    cp 133
    jp nz,test_fail
    xor a
    ret

test_pointer_post_codegen:
    ld a,42
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
    cp 161
    jp nz,test_fail
    xor a
    ret

test_pointer_array_codegen:
    ld a,43
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
    cp 133
    jp nz,test_fail
    xor a
    ret

test_float_literal_codegen:
    ld a,44
    ld (mode),a
    call fixture_reset
    call cc_rev02_compile_stream
    ret c
    ld a,(fp_count)
    cp 4
    jp nz,test_fail
    ld hl,(cc_rev02_literal_len)
    ld a,h
    or a
    jp nz,test_fail
    ld a,l
    cp 20
    jp nz,test_fail
    ld hl,cc_rev02_literals
    ld de,fp_expected_bytes
    ld b,20
test_float_literal_bytes:
    ld a,(de)
    cp (hl)
    jp nz,test_fail
    inc de
    inc hl
    djnz test_float_literal_bytes
    ld hl,diag_f0
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
    cp $11
    jp nz,test_fail
    ld hl,diag_f3
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
    cp $41
    jp nz,test_fail
    call test_patch_logic_relocs
    ret c
    call call_compiled_main
    ld a,h
    or a
    jp nz,test_fail
    ld a,l
    or a
    jp nz,test_fail
    xor a
    ret

test_void_return_codegen:
    ld a,45
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
    cp 9
    jp nz,test_fail
    xor a
    ret

test_call_expression_codegen:
    ld a,46
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
    cp 18
    jp nz,test_fail
    xor a
    ret

test_mixed_call_arg_codegen:
    ld a,47
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
    cp 9
    jp nz,test_fail
    xor a
    ret

test_local_array_init_codegen:
    ld a,48
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
    cp 210
    jp nz,test_fail
    xor a
    ret

test_local_pointer_init_codegen:
    ld a,49
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

test_nested_call_codegen:
    ld a,50
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
    cp 13
    jp nz,test_fail
    xor a
    ret

test_wide_call_codegen:
    ld a,51
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
    cp 45
    jp nz,test_fail
    xor a
    ret

test_symbol_capacity_codegen:
    ld a,52
    ld (mode),a
    call fixture_reset
    call cc_rev02_compile_stream
    ret c
    ld a,(cc_rev02_symbol_count)
    cp 41
    jp nz,test_fail
    call test_patch_logic_relocs
    ret c
    call call_compiled_main
    ld a,h
    or a
    jp nz,test_fail
    ld a,l
    cp 39
    jp nz,test_fail
    xor a
    ret

test_unsigned_runtime_codegen:
    ld a,53
    ld (mode),a
    call fixture_reset
    call cc_rev02_compile_stream
    ret c
    call test_patch_logic_relocs
    ret c
    call call_compiled_main
    ld a,h
    or l
    jp nz,test_fail
    xor a
    ret

test_main_argv_codegen:
    ld a,54
    ld (mode),a
    call fixture_reset
    call cc_rev02_compile_stream
    ret c
    call test_patch_logic_relocs
    ret c
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
    ld bc,test_main_argv_return
    push bc
    push hl
    ld hl,2
    ld de,argv_words
    ret
test_main_argv_return:
    ld a,h
    or a
    jp nz,test_fail
    ld a,l
    cp 'Z'
    jp nz,test_fail
    xor a
    ret

test_do_while_codegen:
    ld a,55
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
    cp 48
    jp nz,test_fail
    xor a
    ret

test_sizeof_type_compile:
    ld a,58
    ld (mode),a
    call fixture_reset
    call cc_rev02_compile_stream
    ret

test_sizeof_bounds_compile:
    ld a,59
    ld (mode),a
    call fixture_reset
    call cc_rev02_compile_stream
    ret

test_sizeof_object_compile:
    ld a,60
    ld (mode),a
    call fixture_reset
    call cc_rev02_compile_stream
    ret

test_sizeof_literal_compile:
    ld a,61
    ld (mode),a
    call fixture_reset
    call cc_rev02_compile_stream
    ret

test_sizeof_unsigned_compile:
    ld a,62
    ld (mode),a
    call fixture_reset
    call cc_rev02_compile_stream
    ret

test_sizeof_compile:
    ld a,56
    ld (mode),a
    call fixture_reset
    call cc_rev02_compile_stream
    ret

test_sizeof_bss:
    ld a,56
    ld (mode),a
    call fixture_reset
    call cc_rev02_compile_stream
    ret c
    ld hl,(cc_obj1_bss_size)
    ld de,17
    or a
    sbc hl,de
    jp nz,test_fail
    xor a
    ret

test_sizeof_symbols:
    ld a,56
    ld (mode),a
    call fixture_reset
    call cc_rev02_compile_stream
    ret c
    ld a,(cc_rev02_symbol_count)
    cp 6
    jp nz,test_fail
    xor a
    ret

test_sizeof_relocs:
    ld a,56
    ld (mode),a
    call fixture_reset
    call cc_rev02_compile_stream
    ret c
    ld a,(cc_rev02_reloc_count)
    cp 2
    jp nz,test_fail
    xor a
    ret

test_sizeof_codegen:
    ld a,56
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
    cp 71
    jp nz,test_fail
    xor a
    ret

test_sizeof_void_reject:
    ld a,57
    ld (mode),a
    call fixture_reset
    call cc_rev02_compile_stream
    jp nc,test_fail
    cp E_FORMAT
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
    ASSERT fixture_end <= $B800
    ASSERT cc_product_bss+CC_REV02_BSS_BYTES <= $E000
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
    cp SYS_FP_FROM_TEXT
    jp z,gate_fp_from_text
    ld a,E_NOTSUP
    scf
    ret

gate_fp_from_text:
    push bc
    push de
    ld a,(fp_count)
    cp 4
    jp nc,gate_fp_bad_stack
    ld ix,fp_oracle_table
    or a
    jr z,gate_fp_record_ready
    ld b,a
    ld de,14
gate_fp_record_seek:
    add ix,de
    djnz gate_fp_record_seek
gate_fp_record_ready:
    pop de
    pop bc
    ld a,b
    or a
    jp nz,gate_bad
    ld a,(ix+0)
    cp c
    jp nz,gate_bad
    ld b,c
    push ix
    inc ix
gate_fp_text_loop:
    ld a,(ix+0)
    cp (hl)
    jr nz,gate_fp_text_bad
    inc ix
    inc hl
    djnz gate_fp_text_loop
    pop ix
    ld a,(ix+9)
    ld (de),a
    inc de
    ld a,(ix+10)
    ld (de),a
    inc de
    ld a,(ix+11)
    ld (de),a
    inc de
    ld a,(ix+12)
    ld (de),a
    inc de
    ld a,(ix+13)
    ld (de),a
    ld hl,fp_count
    inc (hl)
    xor a
    ret
gate_fp_text_bad:
    pop ix
    jp gate_bad
gate_fp_bad_stack:
    pop de
    pop bc
    jp gate_bad

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
    cp 41
    jp z,gate_read_integer_cast
    cp 42
    jp z,gate_read_pointer_post
    cp 43
    jp z,gate_read_pointer_array
    cp 44
    jp z,gate_read_float_literal
    cp 45
    jp z,gate_read_void_return
    cp 46
    jp z,gate_read_call_expression
    cp 47
    jp z,gate_read_mixed_call_arg
    cp 48
    jp z,gate_read_local_array_init
    cp 49
    jp z,gate_read_local_pointer_init
    cp 50
    jp z,gate_read_nested_call
    cp 51
    jp z,gate_read_wide_call
    cp 52
    jp z,gate_read_symbol_capacity
    cp 53
    jp z,gate_read_unsigned_runtime
    cp 54
    jp z,gate_read_main_argv
    cp 55
    jp z,gate_read_do_while
    cp 56
    jp z,gate_read_sizeof
    cp 57
    jp z,gate_read_sizeof_void
    cp 58
    jp z,gate_read_sizeof_type
    cp 59
    jp z,gate_read_sizeof_bounds
    cp 60
    jp z,gate_read_sizeof_object
    cp 61
    jp z,gate_read_sizeof_literal
    cp 62
    jp z,gate_read_sizeof_unsigned
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
gate_read_integer_cast:
    ld hl,integer_cast_source
    ld (fixture_source_ptr),hl
    ld hl,integer_cast_source_end-integer_cast_source
    ld (fixture_source_left),hl
    jp gate_read_fixture_chunk
gate_read_pointer_post:
    ld hl,pointer_post_source
    ld (fixture_source_ptr),hl
    ld hl,pointer_post_source_end-pointer_post_source
    ld (fixture_source_left),hl
    jp gate_read_fixture_chunk
gate_read_pointer_array:
    ld hl,pointer_array_source
    ld (fixture_source_ptr),hl
    ld hl,pointer_array_source_end-pointer_array_source
    ld (fixture_source_left),hl
    jp gate_read_fixture_chunk
gate_read_float_literal:
    ld hl,float_literal_source
    ld (fixture_source_ptr),hl
    ld hl,float_literal_source_end-float_literal_source
    ld (fixture_source_left),hl
    jp gate_read_fixture_chunk
gate_read_void_return:
    ld hl,void_return_source
    ld (fixture_source_ptr),hl
    ld hl,void_return_source_end-void_return_source
    ld (fixture_source_left),hl
    jp gate_read_fixture_chunk
gate_read_call_expression:
    ld hl,call_expression_source
    ld (fixture_source_ptr),hl
    ld hl,call_expression_source_end-call_expression_source
    ld (fixture_source_left),hl
    jp gate_read_fixture_chunk
gate_read_mixed_call_arg:
    ld hl,mixed_call_arg_source
    ld (fixture_source_ptr),hl
    ld hl,mixed_call_arg_source_end-mixed_call_arg_source
    ld (fixture_source_left),hl
    jp gate_read_fixture_chunk
gate_read_local_array_init:
    ld hl,local_array_init_source
    ld (fixture_source_ptr),hl
    ld hl,local_array_init_source_end-local_array_init_source
    ld (fixture_source_left),hl
    jp gate_read_fixture_chunk
gate_read_local_pointer_init:
    ld hl,local_pointer_init_source
    ld (fixture_source_ptr),hl
    ld hl,local_pointer_init_source_end-local_pointer_init_source
    ld (fixture_source_left),hl
    jp gate_read_fixture_chunk
gate_read_nested_call:
    ld hl,nested_call_source
    ld (fixture_source_ptr),hl
    ld hl,nested_call_source_end-nested_call_source
    ld (fixture_source_left),hl
    jp gate_read_fixture_chunk
gate_read_wide_call:
    ld hl,wide_call_source
    ld (fixture_source_ptr),hl
    ld hl,wide_call_source_end-wide_call_source
    ld (fixture_source_left),hl
    jp gate_read_fixture_chunk
gate_read_symbol_capacity:
    ld hl,symbol_capacity_source
    ld (fixture_source_ptr),hl
    ld hl,symbol_capacity_source_end-symbol_capacity_source
    ld (fixture_source_left),hl
    jp gate_read_fixture_chunk
gate_read_unsigned_runtime:
    ld hl,unsigned_runtime_source
    ld (fixture_source_ptr),hl
    ld hl,unsigned_runtime_source_end-unsigned_runtime_source
    ld (fixture_source_left),hl
    jp gate_read_fixture_chunk
gate_read_main_argv:
    ld hl,main_argv_source
    ld (fixture_source_ptr),hl
    ld hl,main_argv_source_end-main_argv_source
    ld (fixture_source_left),hl
    jp gate_read_fixture_chunk
gate_read_do_while:
    ld hl,do_while_source
    ld (fixture_source_ptr),hl
    ld hl,do_while_source_end-do_while_source
    ld (fixture_source_left),hl
    jp gate_read_fixture_chunk
gate_read_sizeof:
    ld hl,sizeof_source
    ld (fixture_source_ptr),hl
    ld hl,sizeof_source_end-sizeof_source
    ld (fixture_source_left),hl
    jp gate_read_fixture_chunk
gate_read_sizeof_void:
    ld hl,sizeof_void_source
    ld (fixture_source_ptr),hl
    ld hl,sizeof_void_source_end-sizeof_void_source
    ld (fixture_source_left),hl
    jp gate_read_fixture_chunk

gate_read_sizeof_type:
    ld hl,sizeof_type_source
    ld (fixture_source_ptr),hl
    ld hl,sizeof_type_source_end-sizeof_type_source
    ld (fixture_source_left),hl
    jp gate_read_fixture_chunk
gate_read_sizeof_bounds:
    ld hl,sizeof_bounds_source
    ld (fixture_source_ptr),hl
    ld hl,sizeof_bounds_source_end-sizeof_bounds_source
    ld (fixture_source_left),hl
    jp gate_read_fixture_chunk
gate_read_sizeof_object:
    ld hl,sizeof_object_source
    ld (fixture_source_ptr),hl
    ld hl,sizeof_object_source_end-sizeof_object_source
    ld (fixture_source_left),hl
    jp gate_read_fixture_chunk
gate_read_sizeof_literal:
    ld hl,sizeof_literal_source
    ld (fixture_source_ptr),hl
    ld hl,sizeof_literal_source_end-sizeof_literal_source
    ld (fixture_source_left),hl
    jp gate_read_fixture_chunk
gate_read_sizeof_unsigned:
    ld hl,sizeof_unsigned_source
    ld (fixture_source_ptr),hl
    ld hl,sizeof_unsigned_source_end-sizeof_unsigned_source
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
    names = ("test_define_single", "test_generic_call_compile", "test_generic_call_symbols", "test_generic_call_relocs", "test_generic_call_text", "test_generic_call_obj", "test_builtin_c48", "test_local_scalar_codegen", "test_dynamic_call_abi", "test_runtime_muldiv_codegen", "test_runtime_bitwise_codegen", "test_runtime_shift_codegen", "test_runtime_compare_a", "test_runtime_compare_b", "test_runtime_logic_a", "test_runtime_logic_b", "test_postfix_local_codegen", "test_if_else_codegen", "test_while_codegen", "test_for_codegen", "test_break_continue_codegen", "test_nested_break_codegen", "test_break_outside_reject", "test_continue_outside_reject", "test_recursive_params_codegen", "test_global_scalar_codegen", "test_global_array_compile", "test_global_array_bss", "test_global_array_symbols", "test_global_array_patch", "test_global_array_codegen", "test_global_init_codegen", "test_local_array_codegen", "test_pointer_basic_codegen", "test_local_pointer_assign_codegen", "test_local_pointer_metadata", "test_local_pointer_literal", "test_local_pointer_value_codegen", "test_local_pointer_deref_codegen", "test_local_pointer_codegen", "test_character_literal_codegen", "test_integer_cast_codegen", "test_pointer_post_codegen", "test_pointer_array_codegen", "test_float_literal_codegen", "test_void_return_codegen", "test_call_expression_codegen", "test_mixed_call_arg_codegen", "test_local_array_init_codegen", "test_local_pointer_init_codegen", "test_nested_call_codegen", "test_wide_call_codegen", "test_symbol_capacity_codegen", "test_unsigned_runtime_codegen", "test_main_argv_codegen", "test_do_while_codegen", "test_sizeof_type_compile", "test_sizeof_bounds_compile", "test_sizeof_object_compile", "test_sizeof_literal_compile", "test_sizeof_unsigned_compile", "test_sizeof_compile", "test_sizeof_bss", "test_sizeof_symbols", "test_sizeof_relocs", "test_sizeof_codegen", "test_sizeof_void_reject", "test_define_multi", "test_include_plain", "test_define_include_unused", "test_define_include_compile_only", "test_define_include_text", "test_include_ok", "test_generic_helper_definition", "test_recursive_macro_reject", "test_function_macro_reject", "test_nested_reject", "test_bad_name_reject", "test_wrong_type_reject")
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
    req(len(b"int wide9(int a,int b,int c,int d,int e,int f,int g,int h,int i){int j;int k;int l;int m;int n;int o;int p;int q;int r;int s;return a+b+c+d+e+f+g+h+i;}int main(void){return wide9(1,2,3,4,5,6,7,8,9);}\n") > 64,
        "wide-call fixture must cross the 64-byte direct-source read boundary")
    req(len(b"int first(char *p){return *p;}\nint main(int argc,char **argv){if(argc<2)return 0;return first(argv[1]);}\n") > 64,
        "main argc/argv fixture must cross the 64-byte direct-source read boundary")
    req(len(b"int main(void){int x;int y;x=0;y=0;do{x++;if(x==2)continue;y=y+x;if(x==4)break;}while(x<6);return x*10+y;}\n") > 64,
        "do/while fixture must cross the 64-byte direct-source read boundary")
    req(len(b"int ga[sizeof(int)+1];char gc;float gf[2];int main(void){char c;int a[sizeof(int)+2];int *p;c=7;p=&a[0];return sizeof(char)+sizeof(unsigned char)+sizeof(short)+sizeof(unsigned short)+sizeof(int)+sizeof(unsigned int)+sizeof(float)+sizeof(void*)+sizeof ga+sizeof gf+sizeof a+sizeof c+sizeof p+sizeof *p+sizeof(a[1])+sizeof(\"abc\")+sizeof('A')+sizeof(1)+sizeof(1.0)+sizeof(c++)+sizeof(c+1)+10*(sizeof(int)>-1)+c;}\n") > 64,
        "sizeof fixture must cross the 64-byte direct-source read boundary")
    req(len(b"int main(void){int a[4];char c[3];int i;i=0;for(i=0;i<4;i++)a[i]=i+1;c[0]=2;c[1]=3;c[2]=4;a[2]++;return a[0]+a[1]+a[2]+a[3]+c[0]+c[1]+c[2];}\n") > 64,
        "local-array fixture must cross the 64-byte direct-source read boundary")
    req(len(b"void add3(int *p){*p=*p+3;}void setc(char *p){*p=9;}int main(void){int x;char c;x=4;c=1;add3(&x);setc(&c);return x+c;}\n") > 64,
        "pointer fixture must cross the 64-byte direct-source read boundary")
    checks = {"assemble": "PASS", "anti_specialization": "PASS"}
    if not ns.assemble_only:
        driver = root / "v1/tools-host/test-driver"
        sys.path.insert(0, str(driver))
        import phase1  # type: ignore
        import fuse_harness  # type: ignore
        # This fixture now legitimately extends beyond the generic harness's
        # historical B000/B001 sentinels. Keep proof code/sentinels/stack/BSS
        # disjoint without changing the shared historical harness defaults.
        PASS_PC = 0xB900
        FAIL_PC = 0xB901
        fuse_harness.PASS_PC = PASS_PC
        fuse_harness.FAIL_PC = FAIL_PC
        run_sna = fuse_harness.run_sna
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
            run_sna(root, code, patch=patch, timeout=20, entry=0xB800)
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
            "generic_integer_casts": "PASS" if not ns.assemble_only else "ASSEMBLED",
            "generic_pointer_postfix_scaling": "PASS" if not ns.assemble_only else "ASSEMBLED",
            "generic_pointer_array_string_initializers": "PASS" if not ns.assemble_only else "ASSEMBLED",
            "generic_float_literals_via_sys_fp_from_text": "PASS" if not ns.assemble_only else "ASSEMBLED",
            "generic_void_return_statement": "PASS" if not ns.assemble_only else "ASSEMBLED",
            "generic_function_call_expressions": "PASS" if not ns.assemble_only else "ASSEMBLED",
            "generic_mixed_runtime_call_arguments": "PASS" if not ns.assemble_only else "ASSEMBLED",
            "generic_local_array_constant_initializers": "PASS" if not ns.assemble_only else "ASSEMBLED",
            "generic_local_pointer_initializers": "PASS" if not ns.assemble_only else "ASSEMBLED",
            "generic_nested_function_calls": "PASS" if not ns.assemble_only else "ASSEMBLED",
            "generic_wide_regcall_and_local_capacity": "PASS" if not ns.assemble_only else "ASSEMBLED",
            "generic_symbol_capacity_over_32": "PASS" if not ns.assemble_only else "ASSEMBLED",
            "generic_unsigned_integer_runtime_semantics": "PASS" if not ns.assemble_only else "ASSEMBLED",
            "generic_main_argc_argv_regcall": "PASS" if not ns.assemble_only else "ASSEMBLED",
            "generic_do_while_control_flow": "PASS" if not ns.assemble_only else "ASSEMBLED",
            "generic_sizeof_type_forms_compile": "PASS" if not ns.assemble_only else "ASSEMBLED",
            "generic_sizeof_constant_array_bounds_compile": "PASS" if not ns.assemble_only else "ASSEMBLED",
            "generic_sizeof_object_expression_compile": "PASS" if not ns.assemble_only else "ASSEMBLED",
            "generic_sizeof_literal_expression_compile": "PASS" if not ns.assemble_only else "ASSEMBLED",
            "generic_sizeof_unsigned_result_expression_compile": "PASS" if not ns.assemble_only else "ASSEMBLED",
            "generic_sizeof_compile": "PASS" if not ns.assemble_only else "ASSEMBLED",
            "generic_sizeof_object_bss": "PASS" if not ns.assemble_only else "ASSEMBLED",
            "generic_sizeof_symbol_closure": "PASS" if not ns.assemble_only else "ASSEMBLED",
            "generic_sizeof_relocation_closure": "PASS" if not ns.assemble_only else "ASSEMBLED",
            "generic_sizeof_type_expression_data_model": "PASS" if not ns.assemble_only else "ASSEMBLED",
            "sizeof_constant_expression_array_bounds": "PASS" if not ns.assemble_only else "ASSEMBLED",
            "sizeof_side_effect_operand_not_executed": "PASS" if not ns.assemble_only else "ASSEMBLED",
            "sizeof_array_and_string_nondecay": "PASS" if not ns.assemble_only else "ASSEMBLED",
            "sizeof_float_array_stride_five": "PASS" if not ns.assemble_only else "ASSEMBLED",
            "sizeof_result_unsigned_int": "PASS" if not ns.assemble_only else "ASSEMBLED",
            "sizeof_void_object_rejected": "PASS" if not ns.assemble_only else "ASSEMBLED",
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
            "proof_fixture_code_entry_sentinels_stack_bss_gateway_disjoint": "PASS",
            "source_identity_dispatch_absent": "PASS",
        },
    }
    (out / "CC-INCLUDE-GATE.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print("REV02 STAGE E CC QUOTED INCLUDE GATE PASS" + (" (ASSEMBLE-ONLY)" if ns.assemble_only else ""))


if __name__ == "__main__":
    main()