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
from phase8_common import word

BASE=0xC000; GATE=0xE000; MODE=0xA000; REMOVES=0xA001
KEY=0xA100
class P839Error(DriverError):
    pass
def require(v,m):
    if not v: raise P839Error(m)
def jp_c(a): return b"\xDA"+word(a)
def jp_nc(a): return b"\xD2"+word(a)
def expect(a,v): return b"\x3A"+word(a)+bytes((0xFE,v&255))+phase1._jp_nz(FAIL_PC)
def patch(image,gate,mode,key=b""):
    def apply(ram):
        ram[BASE-0x4000:BASE-0x4000+len(image)]=image
        ram[GATE-0x4000:GATE-0x4000+len(gate)]=gate
        ram[MODE-0x4000]=mode; ram[REMOVES-0x4000]=0
        ram[KEY-0x4000:KEY-0x4000+len(key)]=key
    return apply

def dispatch(root,action,step,*,sha256_file,run_command,require_project_tool):
    if step!="P8.39": raise DriverError(step)
    cron=(root/"v1/src/utils/cron.asm").read_text(encoding="utf-8")
    interrupt=(root/"v1/src/kernel/interrupt.asm").read_text(encoding="utf-8")
    syscall=(root/"v1/src/kernel/syscall.asm").read_text(encoding="utf-8")
    plan=(root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md").read_text(encoding="utf-8")
    assertions=[
      {"name":"canonical-p839-present","passed":"## P8.39 - Cron lock and TIME1 dedupe transaction" in plan},
      {"name":"exact-lock-path","passed":"cron_lock_path: db '/tmp/.cron.lock',0" in cron},
      {"name":"exclusive-create","passed":"O_WRITE|O_CREATE|O_EXCL" in cron},
      {"name":"pid-lf-payload","passed":"cron_lock_payload" in cron and "ld (cron_lock_payload+1),a" in cron},
      {"name":"malformed-treated-live","passed":"cron_lock_malformed:" in cron and "cron_lock_busy:" in cron},
      {"name":"stale-proved-by-proc-info","passed":"SYS_PROC_INFO" in cron and "cp E_NOENT" in cron and "SYS_REMOVE" in cron},
      {"name":"dedupe-key-eight-bytes","passed":"cron_dedupe_key:" in cron and "cron_last_key: defs 8" in cron},
      {"name":"boot-revision-zero","passed":"ld hl,0" in interrupt and "ld (wall_revision),hl" in interrupt},
      {"name":"successful-set-increments-revision","passed":"ld hl,(wall_revision)" in syscall and "inc hl" in syscall and "ld (wall_revision),hl" in syscall},
      {"name":"invalid-time-suppresses-calendar","passed":"cp E_AGAIN" in cron},
    ]
    require(all(x["passed"] for x in assertions),"P8.39 static contract failure")
    tool=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus"); b=root/"v1/build"; b.mkdir(parents=True,exist_ok=True)
    fx=b/"p839-cron-fixture.asm"; fx.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/utils/cron.asm"
    ORG $C000
fixture:
    EMIT_P825_CRON_ROUTINES
fixture_end:
    SAVEBIN "p839-cron-fixture.bin",fixture,fixture_end-fixture
""",encoding="utf-8",newline="\n")
    fr=run_command([tool,"--nologo","--lst=p839-cron-fixture.lst","--sym=p839-cron-fixture.sym",fx.name],cwd=b,timeout_seconds=30)
    require(not fr.timed_out and fr.exit_code==0,f"P8.39 cron assemble: {fr.stderr or fr.stdout}")
    image=(b/"p839-cron-fixture.bin").read_bytes()
    gate=b/"p839-gateway.asm"; gate.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    ORG $E000
gate:
    cp SYS_GETPID
    jp z,g_pid
    cp SYS_OPEN
    jp z,g_open
    cp SYS_WRITE
    jp z,g_write
    cp SYS_CLOSE
    jp z,g_close
    cp SYS_READ
    jp z,g_read
    cp SYS_PROC_INFO
    jp z,g_proc
    cp SYS_REMOVE
    jp z,g_remove
    ld a,E_NOTSUP
    scf
    ret
g_pid:
    ld hl,2
    xor a
    ret
g_open:
    ld a,(g_open_count)
    inc a
    ld (g_open_count),a
    ld b,a
    ld a,($A000)
    or a
    jr z,g_open_success
    ld a,b
    cp 1
    jr nz,g_open_success
    ld a,E_EXIST
    scf
    ret
g_open_success:
    ld hl,3
    xor a
    ret
g_write:
    ld hl,2
    xor a
    ret
g_close:
    xor a
    ret
g_read:
    ld a,(g_read_count)
    inc a
    ld (g_read_count),a
    cp 2
    jr z,g_eof
    ld a,($A000)
    cp 3
    jr z,g_malformed
    ld a,'2'
    ld (hl),a
    inc hl
    ld a,10
    ld (hl),a
    ld hl,2
    xor a
    ret
g_malformed:
    ld a,'x'
    ld (hl),a
    inc hl
    ld (hl),a
    inc hl
    ld a,10
    ld (hl),a
    ld hl,3
    xor a
    ret
g_eof:
    ld hl,0
    xor a
    ret
g_proc:
    ld a,($A000)
    cp 2
    jr z,g_stale
    xor a
    ret
g_stale:
    ld a,E_NOENT
    scf
    ret
g_remove:
    ld a,($A001)
    inc a
    ld ($A001),a
    xor a
    ret
g_open_count: db 0
g_read_count: db 0
gate_end:
    SAVEBIN "p839-gateway.bin",gate,gate_end-gate
""",encoding="utf-8",newline="\n")
    gr=run_command([tool,"--nologo","--lst=p839-gateway.lst","--sym=p839-gateway.sym",gate.name],cwd=b,timeout_seconds=30)
    require(not gr.timed_out and gr.exit_code==0,f"P8.39 gateway assemble: {gr.stderr or gr.stdout}")
    commands=[fr,gr]
    if action=="test":
        sy=phase3_open_descriptions._symbols(b/"p839-cron-fixture.sym",("cron_lock_acquire","cron_dedupe_key","cron_key_valid","E_BUSY"))
        gb=(b/"p839-gateway.bin").read_bytes()
        # Fresh lock succeeds and removes nothing.
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._call(sy["cron_lock_acquire"])+jp_c(FAIL_PC)+expect(REMOVES,0)+phase1._jp(PASS_PC))
        run_sna(root,bytes(code),patch(image,gb,0),timeout=30)
        # Valid live owner rejects duplicate, never deletes.
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._call(sy["cron_lock_acquire"])+jp_nc(FAIL_PC)+bytes((0xFE,sy["E_BUSY"]&255))+phase1._jp_nz(FAIL_PC)+expect(REMOVES,0)+phase1._jp(PASS_PC))
        run_sna(root,bytes(code),patch(image,gb,1),timeout=30)
        # Valid stale owner is the only path that deletes and recreates.
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._call(sy["cron_lock_acquire"])+jp_c(FAIL_PC)+expect(REMOVES,1)+phase1._jp(PASS_PC))
        run_sna(root,bytes(code),patch(image,gb,2),timeout=30)
        # Malformed/unknown lock is conservatively live.
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._call(sy["cron_lock_acquire"])+jp_nc(FAIL_PC)+bytes((0xFE,sy["E_BUSY"]&255))+phase1._jp_nz(FAIL_PC)+expect(REMOVES,0)+phase1._jp(PASS_PC))
        run_sna(root,bytes(code),patch(image,gb,3),timeout=30)

        k0=bytes((0xEA,0x07,9,22,18,11,0,0))
        k1=bytes((0xEA,0x07,9,22,18,11,1,0))
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._ld_hl(KEY)+phase1._call(sy["cron_dedupe_key"])+phase1._jp_z(FAIL_PC))
        code+=phase1._ld_hl(KEY)+phase1._call(sy["cron_dedupe_key"])+phase1._jp_nz(FAIL_PC)
        # Change revision only: must be a new key, representing date -s reset.
        code+=bytes((0x3E,1,0x32))+word(KEY+6)+phase1._ld_hl(KEY)+phase1._call(sy["cron_dedupe_key"])+phase1._jp_z(FAIL_PC)+phase1._jp(PASS_PC)
        run_sna(root,bytes(code),patch(image,gb,0,k0),timeout=30)
        assertions += [
          {"name":"fuse-fresh-lock-exact-owner","passed":True},
          {"name":"fuse-live-owner-rejected","passed":True},
          {"name":"fuse-stale-valid-owner-healed","passed":True},
          {"name":"fuse-malformed-lock-treated-live","passed":True},
          {"name":"fuse-same-key-deduped","passed":True},
          {"name":"fuse-revision-change-clears-dedupe","passed":True},
        ]
    hashes={
      "v1/src/utils/cron.asm":sha256_file(root/"v1/src/utils/cron.asm"),
      "v1/src/kernel/interrupt.asm":sha256_file(root/"v1/src/kernel/interrupt.asm"),
      "v1/src/kernel/syscall.asm":sha256_file(root/"v1/src/kernel/syscall.asm"),
      "v1/tools-host/test-driver/phase8_cron_transaction.py":sha256_file(root/"v1/tools-host/test-driver/phase8_cron_transaction.py"),
      "v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
      "v1/dist/certification/P8.38.test.json":sha256_file(root/"v1/dist/certification/P8.38.test.json"),
    }
    return commands,hashes,assertions
