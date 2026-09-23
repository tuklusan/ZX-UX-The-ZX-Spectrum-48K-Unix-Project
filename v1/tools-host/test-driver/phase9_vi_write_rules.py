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
from phase8_common import inspect_mex, make_tap, mex1, word

BASE=0xC000; GATE=0xE000
NEW=0xA100; EDIT=0xA120; READ=0xA140; BAD=0xA160
FAILW=0xA300; FAILR=0xA301; OUTLEN=0xA302; OUT=0xA320
# Exact P9.18 qualification candidate.

class P918Error(DriverError): pass
def require(v,m):
    if not v: raise P918Error(m)
def expect_byte(a,v): return b"\x3A"+word(a)+bytes((0xFE,v&255))+phase1._jp_nz(FAIL_PC)
def expect_word(a,v): return expect_byte(a,v&255)+expect_byte(a+1,(v>>8)&255)
def logical_byte(sy,off,val):
    return phase1._ld_hl(off)+phase1._call(sy["vi_p903_get_byte"])+bytes((0xFE,val&255))+phase1._jp_nz(FAIL_PC)
def patch(image,gateway,sy,data=b"old\n",dirty=1,named=1,target=b"orig.c",failw=0,failr=0):
    def apply(ram):
        ram[BASE-0x4000:BASE-0x4000+len(image)]=image
        ram[GATE-0x4000:GATE-0x4000+len(gateway)]=gateway
        for addr,val in ((NEW,b"new.c\0"),(EDIT,b"edit.c\0"),(READ,b"read.c\0"),(BAD,b"x\0")):
            ram[addr-0x4000:addr-0x4000+len(val)]=val
        ram[sy["vi_buffer"]-0x4000:sy["vi_buffer"]-0x4000+len(data)]=data
        ram[sy["vi_buffer_len"]-0x4000:sy["vi_buffer_len"]-0x4000+2]=len(data).to_bytes(2,"little")
        ram[sy["vi_dirty"]-0x4000]=dirty
        ram[sy["vi_named"]-0x4000]=named
        ram[sy["vi_target"]-0x4000:sy["vi_target"]-0x4000+len(target)+1]=target+b"\0"
        ram[FAILW-0x4000]=failw; ram[FAILR-0x4000]=failr; ram[OUTLEN-0x4000]=0
    return apply

def dispatch(root,action,step,*,sha256_file,run_command,require_project_tool):
    if step!="P9.18": raise DriverError(step)
    source=root/"tools/vi.asm"; text=source.read_text(encoding="utf-8")
    plan=(root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md").read_text(encoding="utf-8")
    sec=text[text.index("; P9.18"):]
    assertions=[
      {"name":"canonical-p918-present","passed":"## P9.18 - :w path, :wq and retarget rules" in plan},
      {"name":"bare-write-requires-target","passed":"call vi_p904_require_target" in sec[sec.index("vi_p918_w_current:"):sec.index("vi_p918_w_path:")]},
      {"name":"retarget-after-transaction","passed":sec.index("call vi_p917_write_path",sec.index("vi_p918_w_path:")) < sec.index("jp vi_p904_commit_target",sec.index("vi_p918_w_path:"))},
      {"name":"wq-exit-after-save","passed":sec.index("call vi_p918_w_current",sec.index("vi_p918_wq:")) < sec.index("ld (vi_should_exit),a",sec.index("vi_p918_wq:")+40)},
      {"name":"dirty-e-refusal-retained","passed":"ld a,E_BUSY" in text[text.index("vi_p916_e:"):text.index("vi_p916_e_clean:")]},
      {"name":"read-never-retargets-retained","passed":"vi_p904_commit_target" not in text[text.index("vi_p916_r:"):text.index("vi_p916_r_preflight:")]},
    ]
    require(all(x["passed"] for x in assertions),"P9.18 static contract failure")

    asm=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus")
    build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    fixture=build/"p918-vi.asm"
    fixture.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../../tools/vi.asm"
    ORG $C000
fixture:
    EMIT_P901_VI_ROUTINES
fixture_end:
    SAVEBIN "p918-vi.bin",fixture,fixture_end-fixture
""",encoding="utf-8",newline="\n")
    fr=run_command([asm,"--nologo","--lst=p918-vi.lst","--sym=p918-vi.sym",fixture.name],cwd=build,timeout_seconds=30)
    require(not fr.timed_out and fr.exit_code==0,f"P9.18 assemble: {fr.stderr or fr.stdout}")
    image=(build/"p918-vi.bin").read_bytes()
    mex_path=build/"p918-vi.mex1"; mex_path.write_bytes(mex1(image))
    try:
        xr=inspect_mex(root,mex_path,run_command,require_project_tool); tap=make_tap(root,build,"vi","p918",mex_path)
    except RuntimeError as exc: raise P918Error(str(exc)) from exc

    gw=build/"p918-gateway.asm"
    gw.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    ORG $E000
gate:
    cp SYS_STAT
    jp z,g_stat
    cp SYS_GETPID
    jp z,g_pid
    cp SYS_OPEN
    jp z,g_open
    cp SYS_READ
    jp z,g_read
    cp SYS_WRITE
    jp z,g_write
    cp SYS_CLOSE
    jp z,g_close
    cp SYS_RENAME
    jp z,g_rename
    cp SYS_REMOVE
    jp z,g_remove
    ld a,E_NOTSUP
    scf
    ret
g_pid:
    ld hl,3
    xor a
    ret
g_stat:
    ld e,(hl)
    inc hl
    ld d,(hl)
    inc hl
    ld c,(hl)
    inc hl
    ld b,(hl)
    ld a,(de)
    cp 'e'
    jr z,g_stat_c
    cp 'r'
    jr z,g_stat_txt
    cp 'o'
    jr z,g_stat_c
    ld a,E_NOENT
    scf
    ret
g_stat_c:
    ld a,OBJ_C
    jr g_stat_store
g_stat_txt:
    ld a,OBJ_TXT
g_stat_store:
    ld (bc),a
    xor a
    ret
g_open:
    ld a,c
    cp O_READ
    jr z,g_open_read
    ld hl,7
    xor a
    ret
g_open_read:
    ld a,(hl)
    ld ($A304),a
    xor a
    ld ($A305),a
    ld hl,5
    ret
g_read:
    ld a,($A305)
    or a
    jr nz,g_read_eof
    inc a
    ld ($A305),a
    ld a,($A304)
    cp 'e'
    jr z,g_read_edit
    ld de,g_data_read
    ld bc,3
    jr g_read_copy
g_read_edit:
    ld de,g_data_edit
    ld bc,4
g_read_copy:
    push bc
g_read_loop:
    ld a,(de)
    ld (hl),a
    inc de
    inc hl
    dec bc
    ld a,b
    or c
    jr nz,g_read_loop
    pop hl
    xor a
    ret
g_read_eof:
    ld hl,0
    xor a
    ret
g_write:
    ld a,d
    or e
    jr nz,g_console
    ld a,($A300)
    or a
    jr nz,g_write_fail
    ld hl,1
    xor a
    ret
g_console:
    ld a,c
    ld ($A302),a
    ld de,$A320
g_console_loop:
    ld a,b
    or c
    jr z,g_console_done
    ld a,(hl)
    ld (de),a
    inc hl
    inc de
    dec bc
    jr g_console_loop
g_console_done:
    xor a
    ret
g_write_fail:
    ld a,E_IO
    scf
    ret
g_close:
    xor a
    ret
g_rename:
    ld a,($A301)
    or a
    jr nz,g_rename_fail
    xor a
    ret
g_rename_fail:
    ld a,E_IO
    scf
    ret
g_remove:
    xor a
    ret
g_data_edit: db 'N','E','W',10
g_data_read: db 'Z','Z',10
gate_end:
    SAVEBIN "p918-gateway.bin",gate,gate_end-gate
""",encoding="utf-8",newline="\n")
    gr=run_command([asm,"--nologo","--lst=p918-gateway.lst","--sym=p918-gateway.sym",gw.name],cwd=build,timeout_seconds=30)
    require(not gr.timed_out and gr.exit_code==0,f"P9.18 gateway: {gr.stderr or gr.stdout}")

    if action=="test":
        sy=phase3_open_descriptions._symbols(build/"p918-vi.sym",(
          "vi_p903_init","vi_p903_get_byte","vi_p918_session_init","vi_p918_w_current","vi_p918_w_path","vi_p918_wq",
          "vi_p916_e","vi_p916_r","vi_buffer","vi_buffer_len","vi_dirty","vi_named","vi_target","vi_should_exit",
          "E_NOENT","E_IO","E_BUSY",
        ))
        gateway=(build/"p918-gateway.bin").read_bytes()
        # Named :w succeeds, clears dirty, keeps target.
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._call(sy["vi_p903_init"])+phase1._jp_c(FAIL_PC))
        code+=phase1._call(sy["vi_p918_session_init"])+phase1._call(sy["vi_p918_w_current"])+phase1._jp_c(FAIL_PC)
        code+=expect_byte(sy["vi_dirty"],0)+expect_byte(sy["vi_named"],1)+expect_byte(sy["vi_should_exit"],0)
        for i,v in enumerate(b"orig.c\0"): code+=expect_byte(sy["vi_target"]+i,v)
        code+=phase1._jp(PASS_PC); run_sna(root,bytes(code),patch=patch(image,gateway,sy))

        # Successful :w path retargets and clears dirty only after commit.
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._call(sy["vi_p903_init"])+phase1._jp_c(FAIL_PC))
        code+=phase1._ld_hl(NEW)+phase1._call(sy["vi_p918_w_path"])+phase1._jp_c(FAIL_PC)
        code+=expect_byte(sy["vi_dirty"],0)+expect_byte(sy["vi_named"],1)
        for i,v in enumerate(b"new.c\0"): code+=expect_byte(sy["vi_target"]+i,v)
        code+=phase1._jp(PASS_PC); run_sna(root,bytes(code),patch=patch(image,gateway,sy))

        # Write/rename failure does not clear dirty or retarget.
        for fw,fr in ((1,0),(0,1)):
            code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._call(sy["vi_p903_init"])+phase1._jp_c(FAIL_PC))
            code+=phase1._ld_hl(NEW)+phase1._call(sy["vi_p918_w_path"])+b"\xD2"+word(FAIL_PC)+b"\xFE"+bytes((sy["E_IO"]&255,))+phase1._jp_nz(FAIL_PC)
            code+=expect_byte(sy["vi_dirty"],1)+expect_byte(sy["vi_named"],1)
            for i,v in enumerate(b"orig.c\0"): code+=expect_byte(sy["vi_target"]+i,v)
            code+=phase1._jp(PASS_PC); run_sna(root,bytes(code),patch=patch(image,gateway,sy,failw=fw,failr=fr))

        # :wq exits only after successful save.
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._call(sy["vi_p903_init"])+phase1._jp_c(FAIL_PC))
        code+=phase1._call(sy["vi_p918_session_init"])+phase1._call(sy["vi_p918_wq"])+phase1._jp_c(FAIL_PC)
        code+=expect_byte(sy["vi_dirty"],0)+expect_byte(sy["vi_should_exit"],1)+phase1._jp(PASS_PC)
        run_sna(root,bytes(code),patch=patch(image,gateway,sy))
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._call(sy["vi_p903_init"])+phase1._jp_c(FAIL_PC))
        code+=phase1._call(sy["vi_p918_session_init"])+phase1._call(sy["vi_p918_wq"])+b"\xD2"+word(FAIL_PC)
        code+=expect_byte(sy["vi_dirty"],1)+expect_byte(sy["vi_should_exit"],0)+phase1._jp(PASS_PC)
        run_sna(root,bytes(code),patch=patch(image,gateway,sy,failw=1))

        # Unnamed :w and :wq report exact no-file-name and preserve dirty/running.
        for fn in ("vi_p918_w_current","vi_p918_wq"):
            code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._call(sy["vi_p903_init"])+phase1._jp_c(FAIL_PC))
            code+=phase1._call(sy["vi_p918_session_init"])+phase1._call(sy[fn])+b"\xD2"+word(FAIL_PC)+b"\xFE"+bytes((sy["E_NOENT"]&255,))+phase1._jp_nz(FAIL_PC)
            code+=expect_byte(sy["vi_dirty"],1)+expect_byte(sy["vi_named"],0)+expect_byte(sy["vi_should_exit"],0)
            for i,v in enumerate(b"vi: no file name\n"): code+=expect_byte(OUT+i,v)
            code+=phase1._jp(PASS_PC); run_sna(root,bytes(code),patch=patch(image,gateway,sy,named=0,target=b""))

        # Clean :e replaces/retargets; dirty :e refuses and preserves.
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._call(sy["vi_p903_init"])+phase1._jp_c(FAIL_PC))
        code+=phase1._ld_hl(EDIT)+phase1._call(sy["vi_p916_e"])+phase1._jp_c(FAIL_PC)
        for i,v in enumerate(b"NEW\n"): code+=logical_byte(sy,i,v)
        for i,v in enumerate(b"edit.c\0"): code+=expect_byte(sy["vi_target"]+i,v)
        code+=expect_byte(sy["vi_dirty"],0)+phase1._jp(PASS_PC)
        run_sna(root,bytes(code),patch=patch(image,gateway,sy,dirty=0))
        old=b"old\n"
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._call(sy["vi_p903_init"])+phase1._jp_c(FAIL_PC))
        code+=phase1._ld_hl(EDIT)+phase1._call(sy["vi_p916_e"])+b"\xD2"+word(FAIL_PC)+b"\xFE"+bytes((sy["E_BUSY"]&255,))+phase1._jp_nz(FAIL_PC)
        for i,v in enumerate(old): code+=logical_byte(sy,i,v)
        for i,v in enumerate(b"orig.c\0"): code+=expect_byte(sy["vi_target"]+i,v)
        code+=phase1._jp(PASS_PC); run_sna(root,bytes(code),patch=patch(image,gateway,sy,dirty=1))

        # :r inserts, dirties, never retargets; failed load preserves state.
        data=b"aa\nbb\n"
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._call(sy["vi_p903_init"])+phase1._jp_c(FAIL_PC))
        code+=phase1._ld_hl(READ)+phase1._call(sy["vi_p916_r"])+phase1._jp_c(FAIL_PC)
        for i,v in enumerate(b"aa\nZZ\nbb\n"): code+=logical_byte(sy,i,v)
        code+=expect_byte(sy["vi_dirty"],1)
        for i,v in enumerate(b"orig.c\0"): code+=expect_byte(sy["vi_target"]+i,v)
        code+=phase1._jp(PASS_PC); run_sna(root,bytes(code),patch=patch(image,gateway,sy,data=data,dirty=0))
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._call(sy["vi_p903_init"])+phase1._jp_c(FAIL_PC))
        code+=phase1._ld_hl(BAD)+phase1._call(sy["vi_p916_r"])+b"\xD2"+word(FAIL_PC)
        for i,v in enumerate(old): code+=logical_byte(sy,i,v)
        for i,v in enumerate(b"orig.c\0"): code+=expect_byte(sy["vi_target"]+i,v)
        code+=expect_byte(sy["vi_dirty"],1)+phase1._jp(PASS_PC)
        run_sna(root,bytes(code),patch=patch(image,gateway,sy,dirty=1))

        assertions += [
          {"name":"fuse-named-unnamed-write-golden","passed":True},
          {"name":"fuse-write-path-retarget-after-success","passed":True},
          {"name":"fuse-write-rename-failure-preserves-dirty-target","passed":True},
          {"name":"fuse-wq-success-failure-exit-state","passed":True},
          {"name":"fuse-clean-dirty-e-rules","passed":True},
          {"name":"fuse-r-never-retargets","passed":True},
        ]

    hashes={
      "tools/vi.asm":sha256_file(source),"v1/build/p918-vi.mex1":sha256_file(mex_path),
      "v1/build/p918-vi.tap":sha256_file(tap),
      "v1/tools-host/test-driver/phase9_vi_write_rules.py":sha256_file(root/"v1/tools-host/test-driver/phase9_vi_write_rules.py"),
      "v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
      "v1/dist/certification/P9.17.test.json":sha256_file(root/"v1/dist/certification/P9.17.test.json"),
    }
    return [fr,xr,gr],hashes,assertions
