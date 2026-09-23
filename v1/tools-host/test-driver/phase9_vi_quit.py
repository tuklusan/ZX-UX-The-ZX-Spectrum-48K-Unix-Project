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
MODE=0xA300; CURSOR=0xA301; CLOSED=0xA302; EXITED=0xA303
# Exact P9.19 qualification candidate.
# Final exact candidate after workflow creation.

class P919Error(DriverError): pass
def require(v,m):
    if not v: raise P919Error(m)
def expect_byte(a,v): return b"\x3A"+word(a)+bytes((0xFE,v&255))+phase1._jp_nz(FAIL_PC)
def patch(image,gateway,sy,dirty):
    def apply(ram):
        ram[BASE-0x4000:BASE-0x4000+len(image)]=image
        ram[GATE-0x4000:GATE-0x4000+len(gateway)]=gateway
        ram[sy["vi_dirty"]-0x4000]=dirty
        ram[sy["vi_should_exit"]-0x4000]=0
        ram[sy["vi_handle"]-0x4000]=3
        ram[sy["vi_saved_mode"]-0x4000]=32
        ram[sy["vi_saved_cursor"]-0x4000]=1
        ram[sy["vi_have_mode"]-0x4000]=1
        ram[sy["vi_have_cursor"]-0x4000]=1
        for a in (MODE,CURSOR,CLOSED,EXITED): ram[a-0x4000]=0
    return apply

def dispatch(root,action,step,*,sha256_file,run_command,require_project_tool):
    if step!="P9.19": raise DriverError(step)
    source=root/"tools/vi.asm"; text=source.read_text(encoding="utf-8")
    plan=(root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md").read_text(encoding="utf-8")
    sec=text[text.index("; P9.19"):]
    assertions=[
      {"name":"canonical-p919-present","passed":"## P9.19 - :q and :q!" in plan},
      {"name":"dirty-q-refusal","passed":"ld a,(vi_dirty)" in sec and "ld a,E_BUSY" in sec},
      {"name":"forced-quit-distinct","passed":"vi_p919_q_force:" in sec},
      {"name":"shared-terminal-unwind","passed":"jp vi_normal_exit" in sec[sec.index("vi_p919_exit_if_requested:"):]},
    ]
    require(all(x["passed"] for x in assertions),"P9.19 static contract failure")

    asm=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus")
    build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    fixture=build/"p919-vi.asm"
    fixture.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../../tools/vi.asm"
    ORG $C000
fixture:
    EMIT_P901_VI_ROUTINES
fixture_end:
    SAVEBIN "p919-vi.bin",fixture,fixture_end-fixture
""",encoding="utf-8",newline="\n")
    fr=run_command([asm,"--nologo","--lst=p919-vi.lst","--sym=p919-vi.sym",fixture.name],cwd=build,timeout_seconds=30)
    require(not fr.timed_out and fr.exit_code==0,f"P9.19 assemble: {fr.stderr or fr.stdout}")
    image=(build/"p919-vi.bin").read_bytes()
    mex_path=build/"p919-vi.mex1"; mex_path.write_bytes(mex1(image))
    try:
        xr=inspect_mex(root,mex_path,run_command,require_project_tool); tap=make_tap(root,build,"vi","p919",mex_path)
    except RuntimeError as exc: raise P919Error(str(exc)) from exc

    gw=build/"p919-gateway.asm"
    gw.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    ORG $E000
gate:
    cp SYS_IOCTL
    jr z,g_ioctl
    cp SYS_CLOSE
    jr z,g_close
    cp SYS_EXIT
    jr z,g_exit
    ld a,E_NOTSUP
    scf
    ret
g_ioctl:
    inc hl
    ld a,(hl)
    inc hl
    ld e,(hl)
    inc hl
    ld d,(hl)
    cp 2
    jr z,g_mode
    cp 4
    jr z,g_cursor
    ld a,E_INVAL
    scf
    ret
g_mode:
    ld a,(de)
    ld ($A300),a
    xor a
    ret
g_cursor:
    ld a,(de)
    ld ($A301),a
    xor a
    ret
g_close:
    ld a,1
    ld ($A302),a
    xor a
    ret
g_exit:
    ld a,1
    ld ($A303),a
    xor a
    ret
gate_end:
    SAVEBIN "p919-gateway.bin",gate,gate_end-gate
""",encoding="utf-8",newline="\n")
    gr=run_command([asm,"--nologo","--lst=p919-gateway.lst","--sym=p919-gateway.sym",gw.name],cwd=build,timeout_seconds=30)
    require(not gr.timed_out and gr.exit_code==0,f"P9.19 gateway: {gr.stderr or gr.stdout}")

    if action=="test":
        sy=phase3_open_descriptions._symbols(build/"p919-vi.sym",(
          "vi_p919_q","vi_p919_q_force","vi_p919_exit_if_requested","vi_dirty","vi_should_exit",
          "vi_handle","vi_saved_mode","vi_saved_cursor","vi_have_mode","vi_have_cursor","E_BUSY",
        ))
        gateway=(build/"p919-gateway.bin").read_bytes()

        # Dirty :q refuses and no exit/unwind is attempted.
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._call(sy["vi_p919_q"]))
        code+=b"\xD2"+word(FAIL_PC)+b"\xFE"+bytes((sy["E_BUSY"]&255,))+phase1._jp_nz(FAIL_PC)
        code+=expect_byte(sy["vi_dirty"],1)+expect_byte(sy["vi_should_exit"],0)
        code+=phase1._call(sy["vi_p919_exit_if_requested"])+expect_byte(EXITED,0)+expect_byte(CLOSED,0)+phase1._jp(PASS_PC)
        run_sna(root,bytes(code),patch=patch(image,gateway,sy,1))

        # Clean :q exits through the shared tty restoration path.
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._call(sy["vi_p919_q"])+phase1._jp_c(FAIL_PC))
        code+=expect_byte(sy["vi_should_exit"],1)+phase1._call(sy["vi_p919_exit_if_requested"])
        code+=expect_byte(MODE,32)+expect_byte(CURSOR,1)+expect_byte(CLOSED,1)+expect_byte(EXITED,1)+phase1._jp(PASS_PC)
        run_sna(root,bytes(code),patch=patch(image,gateway,sy,0))

        # :q! exits even when dirty, with bytes/state untouched until process exit.
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._call(sy["vi_p919_q_force"])+phase1._jp_c(FAIL_PC))
        code+=expect_byte(sy["vi_dirty"],1)+expect_byte(sy["vi_should_exit"],1)+phase1._call(sy["vi_p919_exit_if_requested"])
        code+=expect_byte(MODE,32)+expect_byte(CURSOR,1)+expect_byte(CLOSED,1)+expect_byte(EXITED,1)+phase1._jp(PASS_PC)
        run_sna(root,bytes(code),patch=patch(image,gateway,sy,1))

        assertions += [
          {"name":"fuse-dirty-q-refuses-no-exit","passed":True},
          {"name":"fuse-clean-q-restores-and-exits","passed":True},
          {"name":"fuse-forced-q-restores-and-exits","passed":True},
        ]

    hashes={
      "tools/vi.asm":sha256_file(source),"v1/build/p919-vi.mex1":sha256_file(mex_path),
      "v1/build/p919-vi.tap":sha256_file(tap),
      "v1/tools-host/test-driver/phase9_vi_quit.py":sha256_file(root/"v1/tools-host/test-driver/phase9_vi_quit.py"),
      "v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
      "v1/dist/certification/P9.18.test.json":sha256_file(root/"v1/dist/certification/P9.18.test.json"),
    }
    return [fr,xr,gr],hashes,assertions
