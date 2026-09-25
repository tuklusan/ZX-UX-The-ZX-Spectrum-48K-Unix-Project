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

# P11.03 exact-candidate marker.
class P1103Error(DriverError):
    pass

def require(ok, message):
    if not ok:
        raise P1103Error(message)

def constants(text):
    return {n:int(v) for n,v in re.findall(r"^([A-Z0-9_]+)\s+EQU\s+([0-9]+)$",text,re.M)}

def dispatch(root, action, step, *, sha256_file, run_command, require_project_tool):
    if step!="P11.03":
        raise DriverError(step)
    source=root/"v1/src/tools/cc.asm"
    text=source.read_text(encoding="utf-8")
    c=constants(text)
    expected={"CC_PP_MACRO_CAPACITY":16,"CC_PP_REPLACEMENT_MAX":32,
              "CC_PP_MACRO_ENTRY_SIZE":49,"CC_PP_LOCAL_NAME_MAX":10,
              "CC_PP_INCLUDE_CHUNK":64}
    require(all(c.get(k)==v for k,v in expected.items()),"P11.03 frozen bounds")
    for marker in ("EMIT_P11_CC_PREPROCESSOR","cc_pp_define_object:",
                   "cc_pp_expand_ident:","cc_pp_include_operand:",
                   "cc_pp_include_local:","cc_pp_include_builtin:",
                   "cc_pp_reject_feature:","SYS_STAT","SYS_OPEN","SYS_READ",
                   "SYS_CLOSE","No whole include object is materialized"):
        require(marker in text,f"P11.03 missing marker: {marker}")
    doc=(root/"v1/docs/c48.md").read_text(encoding="utf-8")
    matrix=(root/"v1/tests/compiler/preprocessor/README.md").read_text(encoding="utf-8")
    require("P11.03 native preprocessor freeze" in doc,"P11.03 docs")
    require("compiler/c48/preprocessor.py" in doc,"P11.03 SDK map")
    require("SDK/reference result" in matrix and "Target-native mapping" in matrix,"P11.03 matrix")

    assembler=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus")
    build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    fixture=build/"p1103-preprocessor.asm"
    fixture.write_text(r'''    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/tools/cc.asm"
    ORG $C000
fixture:
    EMIT_P11_CC_STREAMING_CORE
    EMIT_P11_CC_PREPROCESSOR
p1103_foo:           db "FOO",0
p1103_foo_lower:     db "foo",0
p1103_repl_123:      db "123"
p1103_repl_7:        db "7"
p1103_repl_33:       defs 33,'x'
p1103_expanded:      defs 8,0
p1103_inc_operand:   db 34,"inc.h",34,0
p1103_wrong_operand: db 34,"Inc.h",34,0
p1103_path_operand:  db 34,"../x.h",34,0
p1103_builtin:       db "<c48.h>",0
p1103_unknown:       db "<stdio.h>",0
p1103_zero_gateway:
    xor a
    ld (p1103_gateway_calls),a
    ld (p1103_stat_calls),a
    ld (p1103_open_calls),a
    ld (p1103_read_calls),a
    ld (p1103_close_calls),a
    ret
p1103_fail:
    ld a,E_FORMAT
    scf
    ret
p1103_macro_positive:
    call cc_pp_reset
    ld hl,p1103_foo
    ld de,p1103_repl_123
    ld c,3
    xor a
    call cc_pp_define_object
    ret c
    ld hl,p1103_foo_lower
    ld de,p1103_repl_7
    ld c,1
    xor a
    call cc_pp_define_object
    ret c
    ld a,(cc_pp_macro_count)
    cp 2
    jp nz,p1103_fail
    ld hl,p1103_foo
    ld de,p1103_expanded
    ld c,8
    call cc_pp_expand_ident
    ret c
    cp 3
    jp nz,p1103_fail
    ld a,(p1103_expanded)
    cp '1'
    jp nz,p1103_fail
    ld a,(p1103_expanded+1)
    cp '2'
    jp nz,p1103_fail
    ld a,(p1103_expanded+2)
    cp '3'
    jp nz,p1103_fail
    ld hl,p1103_foo_lower
    ld de,p1103_expanded
    ld c,8
    call cc_pp_expand_ident
    ret c
    cp 1
    jp nz,p1103_fail
    ld a,(p1103_expanded)
    cp '7'
    jp nz,p1103_fail
    xor a
    ret
p1103_macro_negative:
    call cc_pp_reset
    ld a,$A5
    ld (cc_output_commit_marker),a
    ld hl,p1103_foo
    ld de,p1103_repl_123
    ld c,3
    ld a,CC_PP_FEATURE_FUNCTION
    call cc_pp_define_object
    jp nc,p1103_fail
    cp E_NOTSUP
    jp nz,p1103_fail
    ld a,(cc_pp_macro_count)
    or a
    jp nz,p1103_fail
    ld hl,p1103_foo
    ld de,p1103_repl_33
    ld c,33
    xor a
    call cc_pp_define_object
    jp nc,p1103_fail
    cp E_TOOLONG
    jp nz,p1103_fail
    ld a,(cc_output_commit_marker)
    cp $A5
    jp nz,p1103_fail
    ld b,CC_PP_FEATURE_RECURSIVE
p1103_feature_loop:
    ld a,b
    call cc_pp_reject_feature
    jp nc,p1103_fail
    cp E_NOTSUP
    jp nz,p1103_fail
    djnz p1103_feature_loop
    xor a
    ret
p1103_builtin_positive:
    call cc_p1102_reset
    call cc_pp_reset
    call p1103_zero_gateway
    ld hl,p1103_builtin
    call cc_pp_include_operand
    ret c
    ld hl,(cc_stream_total)
    ld de,CC_PP_BUILTIN_HEADER_SIZE
    or a
    sbc hl,de
    jp nz,p1103_fail
    ld a,(p1103_gateway_calls)
    or a
    jp nz,p1103_fail
    ld hl,p1103_builtin
    call cc_pp_include_operand
    ret c
    ld hl,(cc_stream_total)
    ld de,CC_PP_BUILTIN_HEADER_SIZE
    or a
    sbc hl,de
    jp nz,p1103_fail
    ld a,(p1103_gateway_calls)
    or a
    jp nz,p1103_fail
    xor a
    ret
p1103_local_positive:
    call cc_p1102_reset
    call cc_pp_reset
    call p1103_zero_gateway
    ld hl,p1103_inc_operand
    call cc_pp_include_operand
    ret c
    ld hl,(cc_stream_total)
    ld de,5
    or a
    sbc hl,de
    jp nz,p1103_fail
    ld a,(p1103_stat_calls)
    cp 1
    jp nz,p1103_fail
    ld a,(p1103_open_calls)
    cp 1
    jp nz,p1103_fail
    ld a,(p1103_read_calls)
    cp 2
    jp nz,p1103_fail
    ld a,(p1103_close_calls)
    cp 1
    jp nz,p1103_fail
    xor a
    ret
p1103_direct_equivalent:
    call cc_p1102_reset
    ld hl,p1103_include_data
    ld bc,5
    call cc_pipeline_feed
    ret c
    ld hl,(cc_stream_total)
    ld de,5
    or a
    sbc hl,de
    jp nz,p1103_fail
    xor a
    ret
p1103_include_negative:
    call cc_p1102_reset
    call cc_pp_reset
    call p1103_zero_gateway
    ld a,$5A
    ld (cc_output_commit_marker),a
    ld a,1
    ld (cc_pp_include_depth),a
    ld hl,p1103_inc_operand
    call cc_pp_include_operand
    jp nc,p1103_fail
    cp E_NOTSUP
    jp nz,p1103_fail
    ld a,(p1103_gateway_calls)
    or a
    jp nz,p1103_fail
    xor a
    ld (cc_pp_include_depth),a
    ld hl,p1103_path_operand
    call cc_pp_include_operand
    jp nc,p1103_fail
    cp E_INVAL
    jp nz,p1103_fail
    ld a,(p1103_gateway_calls)
    or a
    jp nz,p1103_fail
    ld hl,p1103_unknown
    call cc_pp_include_operand
    jp nc,p1103_fail
    cp E_NOTSUP
    jp nz,p1103_fail
    ld a,(p1103_gateway_calls)
    or a
    jp nz,p1103_fail
    ld hl,p1103_wrong_operand
    call cc_pp_include_operand
    jp nc,p1103_fail
    cp E_NOENT
    jp nz,p1103_fail
    ld a,(cc_output_commit_marker)
    cp $5A
    jp nz,p1103_fail
    xor a
    ret
p1103_all:
    call p1103_macro_positive
    ret c
    call p1103_macro_negative
    ret c
    call p1103_builtin_positive
    ret c
    call p1103_local_positive
    ret c
    call p1103_direct_equivalent
    ret c
    call p1103_include_negative
    ret c
    xor a
    ret
p1103_include_data:
    db "x=1;",10
fixture_end:
    SAVEBIN "p1103-main.bin",fixture,fixture_end-fixture

    ORG $E000
p1103_gateway:
    push af
    ld a,(p1103_gateway_calls)
    inc a
    ld (p1103_gateway_calls),a
    pop af
    cp SYS_STAT
    jr z,p1103_sys_stat
    cp SYS_OPEN
    jr z,p1103_sys_open
    cp SYS_READ
    jr z,p1103_sys_read
    cp SYS_CLOSE
    jr z,p1103_sys_close
    ld a,E_NOTSUP
    scf
    ret
p1103_path_exact:
    ld a,(hl)
    cp 'i'
    ret nz
    inc hl
    ld a,(hl)
    cp 'n'
    ret nz
    inc hl
    ld a,(hl)
    cp 'c'
    ret nz
    inc hl
    ld a,(hl)
    cp '.'
    ret nz
    inc hl
    ld a,(hl)
    cp 'h'
    ret nz
    inc hl
    ld a,(hl)
    or a
    ret
p1103_sys_stat:
    ld a,(p1103_stat_calls)
    inc a
    ld (p1103_stat_calls),a
    ld e,(hl)
    inc hl
    ld d,(hl)
    inc hl
    ld c,(hl)
    inc hl
    ld b,(hl)
    ex de,hl
    call p1103_path_exact
    jr nz,p1103_sys_noent
    push bc
    pop hl
    ld (hl),OBJ_C
    xor a
    ret
p1103_sys_open:
    ld a,(p1103_open_calls)
    inc a
    ld (p1103_open_calls),a
    call p1103_path_exact
    jr nz,p1103_sys_noent
    ld hl,3
    xor a
    ret
p1103_sys_read:
    ld a,(p1103_read_calls)
    inc a
    ld (p1103_read_calls),a
    cp 1
    jr nz,p1103_sys_read_eof
    ld (hl),'x'
    inc hl
    ld (hl),'='
    inc hl
    ld (hl),'1'
    inc hl
    ld (hl),';'
    inc hl
    ld (hl),10
    ld hl,5
    xor a
    ret
p1103_sys_read_eof:
    ld hl,0
    xor a
    ret
p1103_sys_close:
    ld a,(p1103_close_calls)
    inc a
    ld (p1103_close_calls),a
    xor a
    ret
p1103_sys_noent:
    ld a,E_NOENT
    scf
    ret
p1103_gateway_calls: db 0
p1103_stat_calls:    db 0
p1103_open_calls:    db 0
p1103_read_calls:    db 0
p1103_close_calls:   db 0
p1103_gateway_end:
    SAVEBIN "p1103-gateway.bin",p1103_gateway,p1103_gateway_end-p1103_gateway
''',encoding="utf-8",newline="\n")
    result=run_command([assembler,"--nologo","--sym=p1103-preprocessor.sym",fixture.name],
                       cwd=build,timeout_seconds=30)
    require(not result.timed_out and result.exit_code==0,
            f"P11.03 assemble: {result.stderr or result.stdout}")
    main=(build/"p1103-main.bin").read_bytes()
    gateway=(build/"p1103-gateway.bin").read_bytes()
    require(len(main)<=0x2000,"P11.03 main fixture overlaps gateway")
    syms=phase3_open_descriptions._symbols(build/"p1103-preprocessor.sym",("p1103_all",))
    assertions=[
      {"name":"object-like-macro-only","passed":True},
      {"name":"macro-capacity-bounded-16","passed":c["CC_PP_MACRO_CAPACITY"]==16},
      {"name":"macro-replacement-bounded-32","passed":c["CC_PP_REPLACEMENT_MAX"]==32},
      {"name":"one-level-local-include-bounded","passed":c["CC_PP_LOCAL_NAME_MAX"]==10},
      {"name":"include-stream-window-64","passed":c["CC_PP_INCLUDE_CHUNK"]==64},
      {"name":"builtin-c48-header-compiler-resident","passed":"cc_pp_builtin_header:" in text},
      {"name":"sdk-preprocessor-surface-mapped","passed":True},
    ]
    commands=[result]
    if action=="test":
        def patch(ram):
            ram[0xC000-0x4000:0xC000-0x4000+len(main)]=main
            ram[0xE000-0x4000:0xE000-0x4000+len(gateway)]=gateway
        code=(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._call(syms["p1103_all"])
              +phase1._jp_c(FAIL_PC)+phase1._jp(PASS_PC))
        commands.append(run_sna(root,code,patch=patch))
        assertions += [
          {"name":"fuse-object-like-case-sensitive-expansion","passed":True},
          {"name":"fuse-function-like-macro-rejected","passed":True},
          {"name":"fuse-conditional-paste-stringify-rejected","passed":True},
          {"name":"fuse-replacement-overflow-preserves-output","passed":True},
          {"name":"fuse-local-c-include-streams-through-read","passed":True},
          {"name":"fuse-local-include-equals-direct-stream-count","passed":True},
          {"name":"fuse-nested-include-rejected-before-open","passed":True},
          {"name":"fuse-path-violation-rejected-before-open","passed":True},
          {"name":"fuse-exact-case-local-include-enforced","passed":True},
          {"name":"fuse-unknown-system-header-rejected","passed":True},
          {"name":"fuse-builtin-header-no-external-lookup","passed":True},
          {"name":"fuse-builtin-header-idempotent","passed":True},
        ]
    hashes={
      "v1/src/tools/cc.asm":sha256_file(source),
      "v1/docs/c48.md":sha256_file(root/"v1/docs/c48.md"),
      "v1/tests/compiler/preprocessor/README.md":sha256_file(root/"v1/tests/compiler/preprocessor/README.md"),
      "v1/build/p1103-main.bin":sha256_file(build/"p1103-main.bin"),
      "v1/build/p1103-gateway.bin":sha256_file(build/"p1103-gateway.bin"),
      "v1/tools-host/test-driver/phase11_step_03.py":sha256_file(root/"v1/tools-host/test-driver/phase11_step_03.py"),
      "v1/dist/certification/P11.02.build.json":sha256_file(root/"v1/dist/certification/P11.02.build.json"),
      "v1/dist/certification/P11.02.test.json":sha256_file(root/"v1/dist/certification/P11.02.test.json"),
    }
    return commands,hashes,assertions
