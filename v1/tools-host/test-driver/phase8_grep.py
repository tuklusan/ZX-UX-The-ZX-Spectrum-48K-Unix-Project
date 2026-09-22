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
import phase1, phase3_open_descriptions
from driver_core import DriverError
from fuse_harness import PASS_PC, run_sna
from phase8_common import arg1, word, assemble_utility, inspect_mex, make_tap

UTIL=0xC000; GATE=0xE000; ARG=0xA000; OUT=0xA300; MODE=0xA2F0; STATUS=0xA2F1; COUNTERS=0xA2F3
class P808Error(DriverError): pass
def require(v,m):
    if not v: raise P808Error(m)
def expect(addr,val): return b"\x3A"+word(addr)+bytes((0xFE,val&255))+phase1._jp_nz(0x8F00)
def patch(util,gate,args,mode):
    block=arg1(args)
    def apply(ram):
        ram[UTIL-0x4000:UTIL-0x4000+len(util)]=util; ram[GATE-0x4000:GATE-0x4000+len(gate)]=gate
        ram[ARG-0x4000:ARG-0x4000+len(block)]=block; ram[OUT-0x4000:OUT-0x4000+128]=b"\xA5"*128
        ram[MODE-0x4000]=mode; ram[STATUS-0x4000:STATUS-0x4000+12]=b"\0"*12
    return apply
def source_contract(root):
    s=(root/"v1/src/utils/grep.asm").read_text(); p=(root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md").read_text()
    return [
      {"name":"canonical-p808-present","passed":"## P8.08 - Utility `grep`" in p},
      {"name":"literal-no-regex","passed":"grep_match_inner:" in s and "regex" not in s.lower()},
      {"name":"case-sensitive-compare","passed":"cp (hl)" in s and "casefold" not in s.lower()},
      {"name":"stdin-or-named","passed":"grep_stdin_args:" in s and "SYS_OPEN" in s and "O_READ" in s},
      {"name":"line-streaming","passed":"grep_finish_line:" in s and "SYS_READ" in s},
      {"name":"matching-lines-stdout","passed":"grep_process_match:" in s and "SYS_WRITE" in s},
      {"name":"short-write-safe","passed":"grep_write_loop:" in s and "grep_write_zero:" in s},
      {"name":"status-no-match-one","passed":"ld a,1" in s and "grep_any" in s},
      {"name":"bounded-line-fail-closed","passed":"cp 255" in s and "E_NOSPC" in s},
    ]
def dispatch(root,action,step,*,sha256_file,run_command,require_project_tool):
    if step!="P8.08": raise DriverError(f"Phase-8 grep step is not registered: {step}")
    assertions=source_contract(root); require(all(x["passed"] for x in assertions),"P8.08 static contract failure")
    tool=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus"); build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    try: ir,image,mex=assemble_utility(root,build,tool,"grep","p808","EMIT_P808_GREP_ROUTINES",run_command); xr=inspect_mex(root,mex,run_command,require_project_tool); tap=make_tap(root,build,"grep","p808",mex)
    except RuntimeError as e: raise P808Error(str(e))
    require(256<=len(image)<4096,"P8.08 image size implausible")
    fix=build/"p808-grep-fixture.asm"; fix.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/utils/grep.asm"
    ORG $C000
fixture:
    EMIT_P808_GREP_ROUTINES
fixture_end:
    SAVEBIN "p808-grep-fixture.bin",fixture,fixture_end-fixture
""",newline="\n")
    fr=run_command([tool,"--nologo","--lst=p808-grep-fixture.lst","--sym=p808-grep-fixture.sym","p808-grep-fixture.asm"],cwd=build,timeout_seconds=30); require(not fr.timed_out and fr.exit_code==0,f"P8.08 fixture assembly failed: {fr.stderr or fr.stdout}")
    gate=build/"p808-gateway.asm"; gate.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    ORG $E000
gate:
    cp SYS_OPEN
    jp z,g_open
    cp SYS_READ
    jp z,g_read
    cp SYS_WRITE
    jp z,g_write
    cp SYS_CLOSE
    jp z,g_close
    cp SYS_EXIT
    jp z,g_exit
    ld a,E_NOTSUP
    scf
    ret
g_open:
    ld a,($A2F3)
    inc a
    ld ($A2F3),a
    ld a,($A2F0)
    cp 5
    jr z,g_open_fail
    ld hl,3
    xor a
    ret
g_open_fail:
    ld a,E_NOENT
    scf
    ret
g_read:
    ld (g_dest),hl
    ld a,($A2F4)
    inc a
    ld ($A2F4),a
    ld a,($A2F0)
    cp 3
    jr z,g_read_fail
    cp 2
    jr z,g_data_nomatch
    ld hl,g_data_match
    ld c,g_data_match_end-g_data_match
    jr g_read_selected
g_data_nomatch:
    ld hl,g_data_none
    ld c,g_data_none_end-g_data_none
g_read_selected:
    ld a,(g_index)
    cp c
    jr nc,g_eof
    ld e,a
    ld d,0
    add hl,de
    ld a,(hl)
    ld hl,(g_dest)
    ld (hl),a
    ld a,(g_index)
    inc a
    ld (g_index),a
    ld hl,1
    xor a
    ret
g_eof:
    ld hl,0
    xor a
    ret
g_read_fail:
    ld a,E_IO
    scf
    ret
g_write:
    ld a,($A2F5)
    inc a
    ld ($A2F5),a
    ld a,e
    cp 1
    jr nz,g_bad
    ld a,d
    or a
    jr nz,g_bad
    ld a,($A2F0)
    cp 4
    jr nz,g_write_all
    ld a,b
    or a
    jr nz,g_write_two
    ld a,c
    cp 3
    jr c,g_write_all
g_write_two:
    ld bc,2
g_write_all:
    push bc
    ld de,(g_out)
    ldir
    ld (g_out),de
    pop hl
    xor a
    ret
g_close:
    ld a,($A2F6)
    inc a
    ld ($A2F6),a
    xor a
    ret
g_exit:
    ld a,l
    ld ($A2F1),a
    ld a,1
    ld ($A2F7),a
    xor a
    ret
g_bad:
    ld a,E_INVAL
    scf
    ret
g_data_match: db 'Alpha',10,'beta Alpha',10,'ALPHA',10
g_data_match_end:
g_data_none: db 'alpha',10,'beta',10
g_data_none_end:
g_index: db 0
g_dest: dw 0
g_out: dw $A300
gate_end:
    SAVEBIN "p808-gateway.bin",gate,gate_end-gate
""",newline="\n")
    gr=run_command([tool,"--nologo","--lst=p808-gateway.lst","--sym=p808-gateway.sym","p808-gateway.asm"],cwd=build,timeout_seconds=30); require(not gr.timed_out and gr.exit_code==0,f"P8.08 gateway assembly failed: {gr.stderr or gr.stdout}")
    if action=="test":
        sy=phase3_open_descriptions._symbols(build/"p808-grep-fixture.sym",("grep_entry",)); ub=(build/"p808-grep-fixture.bin").read_bytes(); gb=(build/"p808-gateway.bin").read_bytes()
        cases=[
          ([b"grep",b"Alpha"],0,b"Alpha\nbeta Alpha\n",0,0,0),
          ([b"grep",b"Alpha",b"MiXeD"],0,b"Alpha\nbeta Alpha\n",0,1,1),
          ([b"grep",b"Alpha"],2,b"",1,0,0),
          ([b"grep",b"Alpha"],3,b"",5,0,0),
          ([b"grep",b"Alpha"],4,b"Alpha\nbeta Alpha\n",0,0,0),
          ([b"grep",b"Alpha",b"missing"],5,b"",2,1,0),
          ([b"grep"],0,b"",1,0,0),
        ]
        for args,mode,expected,status,opens,closes in cases:
            block=arg1(args); code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._ld_hl(ARG)+b"\x01"+word(len(block))+phase1._call(sy["grep_entry"]))
            for o,v in enumerate(expected): code+=expect(OUT+o,v)
            code+=expect(OUT+len(expected),0xA5)+expect(STATUS,status)+expect(COUNTERS,opens)+expect(COUNTERS+3,closes)+expect(COUNTERS+4,1)+phase1._jp(PASS_PC)
            run_sna(root,bytes(code),patch=patch(ub,gb,args,mode))
        assertions += [{"name":"fuse-stdin-case-sensitive-literal","passed":True},{"name":"fuse-named-object-open-close","passed":True},{"name":"fuse-no-match-status-one","passed":True},{"name":"fuse-read-error-propagation","passed":True},{"name":"fuse-short-write-retried","passed":True},{"name":"fuse-open-error-propagation","passed":True},{"name":"fuse-invalid-arity","passed":True}]
    hashes={"v1/src/utils/grep.asm":sha256_file(root/"v1/src/utils/grep.asm"),"v1/build/p808-grep.mex1":sha256_file(mex),"v1/build/p808-grep.tap":sha256_file(tap),"v1/tools-host/test-driver/phase8_grep.py":sha256_file(root/"v1/tools-host/test-driver/phase8_grep.py"),"v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),"v1/dist/certification/P8.07.test.json":sha256_file(root/"v1/dist/certification/P8.07.test.json")}
    return [ir,xr,fr,gr],hashes,assertions
