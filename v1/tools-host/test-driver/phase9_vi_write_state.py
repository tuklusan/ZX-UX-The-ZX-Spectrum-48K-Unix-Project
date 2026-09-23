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

BASE=0xC000; GATE=0xE000; NEW=0xA100
# Exact P9.18 qualification candidate.
FAILR=0xA200; OUT=0xA300

class P918Error(DriverError): pass
def require(v,m):
    if not v: raise P918Error(m)
def eb(a,v): return b"\x3A"+word(a)+bytes((0xFE,v&255))+phase1._jp_nz(FAIL_PC)
def ew(a,v): return eb(a,v&255)+eb(a+1,(v>>8)&255)
def patch(image,gateway,sy,*,named=1,dirty=1,fail_rename=0):
    def apply(ram):
        ram[BASE-0x4000:BASE-0x4000+len(image)]=image
        ram[GATE-0x4000:GATE-0x4000+len(gateway)]=gateway
        ram[NEW-0x4000:NEW-0x4000+6]=b"new.c\0"
        ram[FAILR-0x4000]=fail_rename
        ram[sy["vi_named"]-0x4000]=named
        ram[sy["vi_dirty"]-0x4000]=dirty
        ram[sy["vi_target"]-0x4000:sy["vi_target"]-0x4000+7]=b"orig.c\0"
        ram[sy["vi_target_type"]-0x4000]=sy["OBJ_C"] & 255
        ram[sy["vi_buffer"]-0x4000:sy["vi_buffer"]-0x4000+3]=b"abc"
        ram[sy["vi_buffer_len"]-0x4000:sy["vi_buffer_len"]-0x4000+2]=(3).to_bytes(2,"little")
        ram[OUT-0x4000:OUT-0x4000+24]=b"?"*24
    return apply

def dispatch(root,action,step,*,sha256_file,run_command,require_project_tool):
    if step!="P9.18": raise DriverError(step)
    source=root/"tools/vi.asm"; st=source.read_text(encoding="utf-8")
    plan=(root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md").read_text(encoding="utf-8")
    sec=st[st.index("; P9.18"):]
    assertions=[
      {"name":"canonical-p918-present","passed":"## P9.18 - :w path, :wq and retarget rules" in plan},
      {"name":"unnamed-requires-target","passed":"call vi_p904_require_target" in sec},
      {"name":"retarget-after-transaction","passed":sec.index("call vi_p917_write_path",sec.index("vi_p918_w_path:")) < sec.index("jp vi_p904_commit_target",sec.index("vi_p918_w_path:"))},
      {"name":"wq-exit-after-write","passed":sec.index("call vi_p918_w_current",sec.index("vi_p918_wq:")) < sec.index("ld (vi_should_exit),a",sec.index("vi_p918_wq:")+40)},
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
    cp 'o'
    jr nz,g_noent
    ld a,OBJ_C
    ld (bc),a
    xor a
    ret
g_noent:
    ld a,E_NOENT
    scf
    ret
g_open:
    ld hl,7
    xor a
    ret
g_write:
    ld a,d
    or a
    jr nz,g_file_write
    ld a,e
    cp 1
    jr nz,g_file_write
    ld de,$A300
    ldir
    xor a
    ret
g_file_write:
    ld hl,1
    xor a
    ret
g_close:
    xor a
    ret
g_rename:
    ld a,($A200)
    or a
    jr z,g_rename_ok
    ld a,E_IO
    scf
    ret
g_rename_ok:
    xor a
    ret
g_remove:
    xor a
    ret
gate_end:
    SAVEBIN "p918-gateway.bin",gate,gate_end-gate
""",encoding="utf-8",newline="\n")
    gr=run_command([asm,"--nologo","--lst=p918-gateway.lst","--sym=p918-gateway.sym",gw.name],cwd=build,timeout_seconds=30)
    require(not gr.timed_out and gr.exit_code==0,f"P9.18 gateway: {gr.stderr or gr.stdout}")

    if action=="test":
        sy=phase3_open_descriptions._symbols(build/"p918-vi.sym",(
          "vi_p903_init","vi_p918_session_init","vi_p918_w_current","vi_p918_w_path","vi_p918_wq",
          "vi_named","vi_dirty","vi_target","vi_target_type","vi_should_exit","vi_buffer","vi_buffer_len",
          "E_NOENT","E_IO","OBJ_C",
        ))
        gateway=(build/"p918-gateway.bin").read_bytes()
        # unnamed bare :w exact diagnostic and state unchanged
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._call(sy["vi_p903_init"])+phase1._jp_c(FAIL_PC))
        code+=b"\x3E\x01\x32"+word(sy["vi_dirty"])+phase1._call(sy["vi_p918_w_current"])
        code+=b"\xD2"+word(FAIL_PC)+b"\xFE"+bytes((sy["E_NOENT"]&255,))+phase1._jp_nz(FAIL_PC)
        code+=eb(sy["vi_dirty"],1)
        for i,v in enumerate(b"vi: no file name\n"): code+=eb(OUT+i,v)
        code+=phase1._jp(PASS_PC); run_sna(root,bytes(code),patch=patch(image,gateway,sy,named=0,dirty=1))
        # named :w clears dirty, keeps target
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._call(sy["vi_p903_init"])+phase1._jp_c(FAIL_PC))
        code+=b"\x3E\x01\x32"+word(sy["vi_dirty"])+phase1._call(sy["vi_p918_w_current"])+phase1._jp_c(FAIL_PC)+eb(sy["vi_dirty"],0)
        for i,v in enumerate(b"orig.c\0"): code+=eb(sy["vi_target"]+i,v)
        code+=phase1._jp(PASS_PC); run_sna(root,bytes(code),patch=patch(image,gateway,sy))
        # :w path retargets only after successful transaction
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._call(sy["vi_p903_init"])+phase1._jp_c(FAIL_PC))
        code+=b"\x3E\x01\x32"+word(sy["vi_dirty"])+phase1._ld_hl(NEW)+phase1._call(sy["vi_p918_w_path"])+phase1._jp_c(FAIL_PC)+eb(sy["vi_dirty"],0)
        for i,v in enumerate(b"new.c\0"): code+=eb(sy["vi_target"]+i,v)
        code+=phase1._jp(PASS_PC); run_sna(root,bytes(code),patch=patch(image,gateway,sy))
        # failed :w path retains old target and dirty
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._call(sy["vi_p903_init"])+phase1._jp_c(FAIL_PC))
        code+=b"\x3E\x01\x32"+word(sy["vi_dirty"])+phase1._ld_hl(NEW)+phase1._call(sy["vi_p918_w_path"])
        code+=b"\xD2"+word(FAIL_PC)+b"\xFE"+bytes((sy["E_IO"]&255,))+phase1._jp_nz(FAIL_PC)+eb(sy["vi_dirty"],1)
        for i,v in enumerate(b"orig.c\0"): code+=eb(sy["vi_target"]+i,v)
        code+=phase1._jp(PASS_PC); run_sna(root,bytes(code),patch=patch(image,gateway,sy,fail_rename=1))
        # :wq exits only after save success
        for fail,exitv,dirtyv in ((0,1,0),(1,0,1)):
            code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._call(sy["vi_p903_init"])+phase1._jp_c(FAIL_PC)+phase1._call(sy["vi_p918_session_init"]))
            code+=b"\x3E\x01\x32"+word(sy["vi_dirty"])+phase1._call(sy["vi_p918_wq"])
            if fail: code+=b"\xD2"+word(FAIL_PC)
            else: code+=phase1._jp_c(FAIL_PC)
            code+=eb(sy["vi_should_exit"],exitv)+eb(sy["vi_dirty"],dirtyv)+phase1._jp(PASS_PC)
            run_sna(root,bytes(code),patch=patch(image,gateway,sy,fail_rename=fail))
        assertions += [
          {"name":"fuse-unnamed-w-exact-diagnostic","passed":True},{"name":"fuse-named-w-clears-dirty","passed":True},
          {"name":"fuse-w-path-retarget-after-commit","passed":True},{"name":"fuse-failed-write-no-retarget","passed":True},
          {"name":"fuse-wq-exit-only-after-success","passed":True},
        ]
    hashes={
      "tools/vi.asm":sha256_file(source),"v1/build/p918-vi.mex1":sha256_file(mex_path),
      "v1/build/p918-vi.tap":sha256_file(tap),
      "v1/tools-host/test-driver/phase9_vi_write_state.py":sha256_file(root/"v1/tools-host/test-driver/phase9_vi_write_state.py"),
      "v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
      "v1/dist/certification/P9.17.test.json":sha256_file(root/"v1/dist/certification/P9.17.test.json"),
    }
    return [fr,xr,gr],hashes,assertions
