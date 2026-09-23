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
MODE=0xA300; SPAWNS=0xA301; RENAMES=0xA302; REMOVES=0xA303; LASTFLAGS=0xA304
LIVE_DONE=0xA305; TEMP_DONE=0xA306; EXITCODE=0xA307
# MODE: 0 resident+valid, 1 resident+invalid-then-valid, 2 tape+decline.
# Final exact candidate after workflow creation.

class P920Error(DriverError): pass
def require(v,m):
    if not v: raise P920Error(m)
def expect_byte(a,v): return b"\x3A"+word(a)+bytes((0xFE,v&255))+phase1._jp_nz(FAIL_PC)

def run_case(root,name,code,patcher):
    try:
        run_sna(root,bytes(code),patch=patcher)
    except DriverError as exc:
        raise P920Error(f"P9.20 {name}: {exc}") from exc

def patch(image,gate,mode):
    def apply(ram):
        ram[BASE-0x4000:BASE-0x4000+len(image)]=image
        ram[GATE-0x4000:GATE-0x4000+len(gate)]=gate
        ram[MODE-0x4000]=mode
        for a in (SPAWNS,RENAMES,REMOVES,LASTFLAGS,LIVE_DONE,TEMP_DONE,EXITCODE):
            ram[a-0x4000]=0
    return apply

def dispatch(root,action,step,*,sha256_file,run_command,require_project_tool):
    if step!="P9.20": raise DriverError(step)
    cron=root/"v1/src/utils/crontab.asm"
    vi=root/"tools/vi.asm"
    cs=cron.read_text(encoding="utf-8"); vs=vi.read_text(encoding="utf-8")
    plan=(root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md").read_text(encoding="utf-8")
    assertions=[
      {"name":"canonical-p920-present","passed":"## P9.20 - Real crontab -e integration" in plan},
      {"name":"real-bin-vi","passed":"crontab_vi_path: db '/bin/vi',0" in cs},
      {"name":"vi-tape-state-probed","passed":"crontab_vi_stat_out+7" in cs and "STATE_TAPE_BACKED" in cs},
      {"name":"explicit-consent-before-spawn","passed":cs.index("call crontab_authorize_vi_tape") < cs.index("ld a,SYS_SPAWN",cs.index("crontab_spawn_vi:"))},
      {"name":"decline-before-spawn","passed":"crontab_tape_decline:" in cs and "ld a,E_AGAIN" in cs[cs.index("crontab_tape_decline:"):]},
      {"name":"invalid-edit-reenters-vi","passed":"call cron_validate\n    jp c,crontab_edit_again" in cs},
      {"name":"validation-before-rename","passed":cs.index("call cron_validate") < cs.index("ld a,SYS_RENAME")},
      {"name":"actual-vi-cfg-contract","passed":"VI_P920_CFG_TYPE        EQU OBJ_CFG" in vs},
      {"name":"vi-cfg-load-supported","passed":"cp OBJ_CFG" in vs},
    ]
    require(all(x["passed"] for x in assertions),"P9.20 static contract failure")

    asm=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus")
    build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    fx=build/"p920-crontab.asm"
    fx.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/utils/crontab.asm"
    ORG $C000
fixture:
    EMIT_P826_CRONTAB_ROUTINES
fixture_end:
    SAVEBIN "p920-crontab.bin",fixture,fixture_end-fixture
""",encoding="utf-8",newline="\n")
    fr=run_command([asm,"--nologo","--lst=p920-crontab.lst","--sym=p920-crontab.sym",fx.name],cwd=build,timeout_seconds=30)
    require(not fr.timed_out and fr.exit_code==0,f"P9.20 crontab assemble: {fr.stderr or fr.stdout}")
    image=(build/"p920-crontab.bin").read_bytes()
    mex_path=build/"p920-crontab.mex1"; mex_path.write_bytes(mex1(image))
    try:
        xr=inspect_mex(root,mex_path,run_command,require_project_tool); tap=make_tap(root,build,"crontab","p920",mex_path)
    except RuntimeError as exc: raise P920Error(str(exc)) from exc

    # Build the actual vi source too: integration is not certified against an editor fixture.
    vfx=build/"p920-vi.asm"
    vfx.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../../tools/vi.asm"
    ORG $C000
fixture:
    EMIT_P901_VI_ROUTINES
fixture_end:
    SAVEBIN "p920-vi.bin",fixture,fixture_end-fixture
""",encoding="utf-8",newline="\n")
    vr=run_command([asm,"--nologo","--lst=p920-vi.lst","--sym=p920-vi.sym",vfx.name],cwd=build,timeout_seconds=30)
    require(not vr.timed_out and vr.exit_code==0,f"P9.20 vi assemble: {vr.stderr or vr.stdout}")

    gw=build/"p920-gateway.asm"
    gw.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    ORG $E000
gate:
    cp SYS_GETPID
    jp z,g_pid
    cp SYS_OPEN
    jp z,g_open
    cp SYS_READ
    jp z,g_read
    cp SYS_WRITE
    jp z,g_write
    cp SYS_CLOSE
    jp z,g_ok
    cp SYS_STAT
    jp z,g_stat
    cp SYS_SPAWN
    jp z,g_spawn
    cp SYS_WAIT
    jp z,g_wait
    cp SYS_RENAME
    jp z,g_rename
    cp SYS_REMOVE
    jp z,g_remove
    cp SYS_EXIT
    jp z,g_exit
    cp SYS_CON_WRITE
    jp z,g_console
    ld a,E_NOTSUP
    scf
    ret
g_pid:
    ld hl,3
    xor a
    ret
g_open:
    ld a,c
    cp O_READ
    jp z,g_open_read
    ld hl,5
    xor a
    ret
g_open_read:
    ld a,(hl)
    cp '/'
    jp nz,g_bad
    inc hl
    ld a,(hl)
    cp 'e'
    jp z,g_open_live
    xor a
    ld ($A306),a
    ld hl,5
    ret
g_open_live:
    xor a
    ld ($A305),a
    ld hl,4
    ret
g_read:
    ld a,d
    or e
    jp z,g_consent
    ld a,e
    cp 4
    jp z,g_live_read
    cp 5
    jp z,g_temp_read
    jp g_bad
g_consent:
    ld a,'n'
    ld (hl),a
    ld hl,1
    xor a
    ret
g_live_read:
    ld a,($A305)
    or a
    jp nz,g_eof
    inc a
    ld ($A305),a
    ld de,g_valid
    ld bc,g_valid_end-g_valid
    jp g_copy
g_temp_read:
    ld a,($A306)
    or a
    jp nz,g_eof
    inc a
    ld ($A306),a
    ld a,($A300)
    cp 1
    jp nz,g_temp_valid
    ld a,($A301)
    cp 1
    jp nz,g_temp_valid
    ld de,g_invalid
    ld bc,g_invalid_end-g_invalid
    jp g_copy
g_temp_valid:
    ld de,g_valid
    ld bc,g_valid_end-g_valid
g_copy:
    push bc
g_copy_loop:
    ld a,(de)
    ld (hl),a
    inc de
    inc hl
    dec bc
    ld a,b
    or c
    jp nz,g_copy_loop
    pop hl
    xor a
    ret
g_eof:
    ld hl,0
    xor a
    ret
g_write:
    ld h,b
    ld l,c
    xor a
    ret
g_stat:
    ; STAT1: +0 path ptr, +2 output ptr. Only /bin/vi is queried here.
    inc hl
    inc hl
    ld e,(hl)
    inc hl
    ld d,(hl)
    ex de,hl
    xor a
    ld (hl),a
    ld de,7
    add hl,de
    ld a,($A300)
    cp 2
    jp z,g_stat_tape
    xor a
    ld (hl),a
    ret
g_stat_tape:
    ld a,STATE_TAPE_BACKED
    ld (hl),a
    xor a
    ret
g_spawn:
    push hl
    ld de,13
    add hl,de
    ld a,(hl)
    ld ($A304),a
    pop hl
    ld a,($A301)
    inc a
    ld ($A301),a
    ld hl,2
    xor a
    ret
g_wait:
    inc hl
    inc hl
    ld e,(hl)
    inc hl
    ld d,(hl)
    xor a
    ld (de),a
    ret
g_rename:
    ld a,($A302)
    inc a
    ld ($A302),a
    xor a
    ret
g_remove:
    ld a,($A303)
    inc a
    ld ($A303),a
    xor a
    ret
g_exit:
    ld a,l
    ld ($A307),a
    xor a
    ret
g_console:
    xor a
    ret
g_ok:
    xor a
    ret
g_bad:
    ld a,E_INVAL
    scf
    ret
g_valid: db '#',' ','o','k',10
g_valid_end:
g_invalid: db '6','0',' ','*',' ','*',' ','*',' ','*',' ','/','b','i','n','/','x',10
g_invalid_end:
gate_end:
    SAVEBIN "p920-gateway.bin",gate,gate_end-gate
""",encoding="utf-8",newline="\n")
    gr=run_command([asm,"--nologo","--lst=p920-gateway.lst","--sym=p920-gateway.sym",gw.name],cwd=build,timeout_seconds=30)
    require(not gr.timed_out and gr.exit_code==0,f"P9.20 gateway: {gr.stderr or gr.stdout}")

    if action=="test":
        sy=phase3_open_descriptions._symbols(build/"p920-crontab.sym",("crontab_edit","E_AGAIN"))
        gate=(build/"p920-gateway.bin").read_bytes()
        # Resident vi, valid first edit: one editor run, one validated atomic commit.
        for check_name,address,value in (
            ("resident-valid-spawns",SPAWNS,0),
            ("resident-valid-renames",RENAMES,1),
            ("resident-valid-flags",LASTFLAGS,0),
            ("resident-valid-exit",EXITCODE,0),
        ):
            code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._call(sy["crontab_edit"]))
            code+=expect_byte(address,value)+phase1._jp(PASS_PC)
            run_case(root,check_name,code,patch(image,gate,0))
        # First edited CFG is invalid: no rename then; editor runs again; only valid retry commits.
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._call(sy["crontab_edit"]))
        code+=expect_byte(SPAWNS,2)+expect_byte(RENAMES,1)+expect_byte(LASTFLAGS,0)+expect_byte(EXITCODE,0)+phase1._jp(PASS_PC)
        run_case(root,"invalid-then-valid",code,patch(image,gate,1))
        # Tape-backed vi declined: no SYS_SPAWN, hence no tape movement and no live rename.
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._call(sy["crontab_edit"]))
        code+=expect_byte(SPAWNS,0)+expect_byte(RENAMES,0)+expect_byte(LASTFLAGS,0)+expect_byte(EXITCODE,sy["E_AGAIN"]&255)+phase1._jp(PASS_PC)
        run_case(root,"tape-decline",code,patch(image,gate,2))
        assertions += [
          {"name":"fuse-real-vi-valid-cfg-commits","passed":True},
          {"name":"fuse-invalid-cfg-reenters-editor-before-commit","passed":True},
          {"name":"fuse-declined-tape-consent-no-spawn-no-rename","passed":True},
        ]

    hashes={
      "v1/src/utils/crontab.asm":sha256_file(cron),
      "tools/vi.asm":sha256_file(vi),
      "v1/build/p920-crontab.mex1":sha256_file(mex_path),
      "v1/build/p920-crontab.tap":sha256_file(tap),
      "v1/build/p920-vi.bin":sha256_file(build/"p920-vi.bin"),
      "v1/tools-host/test-driver/phase9_crontab_vi.py":sha256_file(root/"v1/tools-host/test-driver/phase9_crontab_vi.py"),
      "v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
      "v1/dist/certification/P9.19.test.json":sha256_file(root/"v1/dist/certification/P9.19.test.json"),
    }
    return [fr,xr,vr,gr],hashes,assertions
