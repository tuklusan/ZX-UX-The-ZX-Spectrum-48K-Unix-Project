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
from fuse_harness import FAIL_PC, PASS_PC, run_sna
from phase8_common import arg1, word, mex1, inspect_mex, make_tap

BASE=0xC000; GATE=0xE000; ARG=0xA000; OUT=0xA400; MODE=0xA300; CUR=0xA301; STATUS=0xA302; SETM=0xA303; SETC=0xA304
class P823Error(DriverError):
    pass
def require(v,m):
    if not v: raise P823Error(m)
def expect(a,v): return b"\x3A"+word(a)+bytes((0xFE,v&255))+phase1._jp_nz(FAIL_PC)

def patch(image,gate,args,mode=64,cursor=1):
    block=arg1(args)
    def apply(ram):
        ram[BASE-0x4000:BASE-0x4000+len(image)]=image
        ram[GATE-0x4000:GATE-0x4000+len(gate)]=gate
        ram[ARG-0x4000:ARG-0x4000+len(block)]=block
        ram[OUT-0x4000:OUT-0x4000+256]=b"\xA5"*256
        ram[MODE-0x4000]=mode; ram[CUR-0x4000]=cursor; ram[STATUS-0x4000]=0xFF
        ram[SETM-0x4000]=0; ram[SETC-0x4000]=0
    return apply

def dispatch(root,action,step,*,sha256_file,run_command,require_project_tool):
    if step!="P8.23": raise DriverError(step)
    src=root/"v1/src/utils/stty.asm"; s=src.read_text(encoding="utf-8")
    p=(root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md").read_text(encoding="utf-8")
    assertions=[
      {"name":"canonical-p823-present","passed":"## P8.23 - Utility `stty`" in p},
      {"name":"six-public-forms","passed":all(x in s for x in ("stty_word_cols","stty_word_cursor","stty_word_block","stty_word_underline","stty_word_off"))},
      {"name":"tty-ioctl-only","passed":"SYS_IOCTL" in s and "SYS_OPEN" in s and "SYS_CLOSE" in s},
      {"name":"default-exact-report","passed":all(x in s for x in ("stty_cols_prefix","stty_rows_cursor","stty_underline"))},
      {"name":"short-write-safe","passed":"stty_write_loop:" in s and "stty_write_zero:" in s},
      {"name":"case-sensitive","passed":"casefold" not in s.lower()},
    ]
    require(all(x["passed"] for x in assertions),"P8.23 static failure")
    tool=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus"); b=root/"v1/build"; b.mkdir(parents=True,exist_ok=True)
    f=b/"p823-stty.asm"; f.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/utils/stty.asm"
    ORG $C000
fixture:
    EMIT_P823_STTY_ROUTINES
fixture_end:
    SAVEBIN "p823-stty.bin",fixture,fixture_end-fixture
""",encoding="utf-8",newline="\n")
    fr=run_command([tool,"--nologo","--lst=p823-stty.lst","--sym=p823-stty.sym",f.name],cwd=b,timeout_seconds=30)
    require(not fr.timed_out and fr.exit_code==0,f"P8.23 assemble: {fr.stderr or fr.stdout}")
    image=(b/"p823-stty.bin").read_bytes()
    g=b/"p823-gateway.asm"; g.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    ORG $E000
gate:
    cp SYS_OPEN
    jp z,g_open
    cp SYS_CLOSE
    jp z,g_close
    cp SYS_IOCTL
    jp z,g_ioctl
    cp SYS_WRITE
    jp z,g_write
    cp SYS_EXIT
    jp z,g_exit
    ld a,E_NOTSUP
    scf
    ret
g_open:
    ld hl,3
    xor a
    ret
g_close:
    xor a
    ret
g_ioctl:
    ld a,(hl)
    cp 3
    jr nz,g_bad
    inc hl
    ld a,(hl)
    inc hl
    ld e,(hl)
    inc hl
    ld d,(hl)
    cp 1
    jr z,g_get_mode
    cp 2
    jr z,g_set_mode
    cp 4
    jr z,g_set_cursor
    cp 5
    jr z,g_get_cursor
    jr g_bad
g_get_mode:
    ld a,($A300)
    ld (de),a
    xor a
    ret
g_set_mode:
    ld a,(de)
    ld ($A303),a
    ld ($A300),a
    xor a
    ret
g_get_cursor:
    ld a,($A301)
    ld (de),a
    xor a
    ret
g_set_cursor:
    ld a,(de)
    ld ($A304),a
    ld ($A301),a
    xor a
    ret
g_write:
    ld a,e
    cp 1
    jr nz,g_bad
    ld a,d
    or a
    jr nz,g_bad
    push bc
    ld de,(g_out)
    ldir
    ld (g_out),de
    pop hl
    xor a
    ret
g_exit:
    ld a,l
    ld ($A302),a
    xor a
    ret
g_bad:
    ld a,E_INVAL
    scf
    ret
g_out: dw $A400
gate_end:
    SAVEBIN "p823-gateway.bin",gate,gate_end-gate
""",encoding="utf-8",newline="\n")
    gr=run_command([tool,"--nologo","--lst=p823-gateway.lst","--sym=p823-gateway.sym",g.name],cwd=b,timeout_seconds=30)
    require(not gr.timed_out and gr.exit_code==0,f"P8.23 gateway: {gr.stderr or gr.stdout}")
    mp=b/"p823-stty.mex1"; mp.write_bytes(mex1(image))
    try:
        xr=inspect_mex(root,mp,run_command,require_project_tool); tap=make_tap(root,b,"stty","p823",mp)
    except RuntimeError as e: raise P823Error(str(e))
    if action=="test":
        sy=phase3_open_descriptions._symbols(b/"p823-stty.sym",("stty_entry","E_INVAL"))
        gb=(b/"p823-gateway.bin").read_bytes()
        tests=[
          ([b"stty"],64,1,b"cols 64 rows 24 cursor underline\n",0,0),
          ([b"stty"],32,2,b"cols 32 rows 24 cursor block\n",0,0),
          ([b"stty",b"cols",b"64"],32,1,b"",64,0),
          ([b"stty",b"cols",b"32"],64,1,b"",32,0),
          ([b"stty",b"cursor",b"block"],64,1,b"",0,2),
          ([b"stty",b"cursor",b"underline"],64,2,b"",0,1),
          ([b"stty",b"cursor",b"off"],64,1,b"",0,0),
        ]
        for args,mode,cursor,want,setm,setc in tests:
            block=arg1(args)
            code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._ld_hl(ARG)+b"\x01"+word(len(block))+phase1._call(sy["stty_entry"]))
            for i,v in enumerate(want): code+=expect(OUT+i,v)
            code+=expect(OUT+len(want),0xA5)+expect(STATUS,0)
            if setm: code+=expect(SETM,setm)
            if args[1:2]==[b"cursor"]: code+=expect(SETC,setc)
            code+=phase1._jp(PASS_PC)
            run_sna(root,bytes(code),patch=patch(image,gb,args,mode,cursor))
        for args in ([b"stty",b"Cols",b"64"],[b"stty",b"cols",b"48"],[b"stty",b"cursor",b"fat"],[b"stty",b"x"]):
            block=arg1(list(args)); code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._ld_hl(ARG)+b"\x01"+word(len(block))+phase1._call(sy["stty_entry"])+expect(STATUS,sy["E_INVAL"]&255)+phase1._jp(PASS_PC))
            run_sna(root,bytes(code),patch=patch(image,gb,list(args)))
        assertions += [{"name":"fuse-default-report","passed":True},{"name":"fuse-all-setters","passed":True},{"name":"fuse-invalid-case-range","passed":True}]
    hashes={
      "v1/src/utils/stty.asm":sha256_file(src),"v1/build/p823-stty.mex1":sha256_file(mp),"v1/build/p823-stty.tap":sha256_file(tap),
      "v1/tools-host/test-driver/phase8_stty.py":sha256_file(root/"v1/tools-host/test-driver/phase8_stty.py"),
      "v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
      "v1/dist/certification/P8.22.test.json":sha256_file(root/"v1/dist/certification/P8.22.test.json"),
    }
    return [fr,gr,xr],hashes,assertions
