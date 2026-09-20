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
from pathlib import Path
from driver_core import DriverError
from fuse_harness import FAIL_PC, PASS_PC, run_sna
import phase1, phase3_open_descriptions

MODULE=0xC000; STACK=0xBFC0
class P513Error(DriverError): pass
def require(x,m):
    if not x: raise P513Error(m)
def w(v): return bytes((v&255,(v>>8)&255))
def checkb(a,v): return b"\x3A"+w(a)+bytes((0xFE,v&255))+phase1._jp_nz(FAIL_PC)

def dispatch(root:Path,action:str,step:str,*,sha256_file,run_command,require_project_tool):
    if step!="P5.13": raise DriverError(f"Phase-5 tape-prompt step is not registered: {step}")
    tape=(root/"v1/src/kernel/tape.asm").read_text()
    m=tape.split("MACRO EMIT_P513_TAPE_PROMPT_ROUTINES",1)[1].split("ENDM",1)[0]
    assertions=[
      {"name":"play-prompt-explicitly-mentions-position-rewind-and-play","passed":'Position or rewind cassette, press PLAY' in m},
      {"name":"record-prompt-explicitly-mentions-position-and-record","passed":'Position cassette, press RECORD' in m},
      {"name":"prompt-requires-shell-foreground-hook","passed":"zx48_p513_foreground_enter:" in m and "p513_interactive" in m},
      {"name":"consent-wait-precedes-tape-operation","passed":"call zx48_shell_tape_prompt_wait" in m},
      {"name":"noninteractive-fails-before-prompt-callback","passed":m.find("zx48_p513_noninteractive:")>0 and "ld a,E_AGAIN" in m},
      {"name":"save-routes-record-prompt","passed":"zx48_p507_prompt_record:" in tape and "jp zx48_p513_prompt_record" in tape},
      {"name":"load-verify-route-play-prompt","passed":"zx48_p509_prompt_play:" in tape and "jp zx48_p513_prompt_play" in tape},
      {"name":"scan-routes-play-prompt-before-lock","passed":tape.find("call zx48_p513_prompt_play",tape.find("zx48_p511_scan_next:")) < tape.find("call zx48_p507_lock_acquire",tape.find("zx48_p511_scan_next:"))},
      {"name":"background-never-reaches-tape-prompt-write","passed":m.find("or a") < m.find("call zx48_shell_tape_prompt_write")},
    ]; require(all(a["passed"] for a in assertions),"P5.13 static failure")
    kr,kernel,_=phase1._assemble_kernel(root,run_command,require_project_tool)
    asm=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus"); b=root/"v1/build"; b.mkdir(parents=True,exist_ok=True)
    f=b/"p513-prompts.asm"; f.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../include/tapeobj.inc"
    INCLUDE "../src/kernel/tape.asm"
    ORG $C000
    EMIT_P513_TAPE_PROMPT_ROUTINES
zx48_shell_tape_prompt_write:
    ld a,(test_writes)
    inc a
    ld (test_writes),a
    ld (test_last_ptr),hl
    ld (test_last_len),bc
    xor a
    ret
zx48_shell_tape_prompt_wait:
    ld a,(test_waits)
    inc a
    ld (test_waits),a
    ld a,(test_decline)
    or a
    jr z,test_wait_ok
    ld a,E_INTR
    scf
    ret
test_wait_ok:
    xor a
    ret
test_writes: db 0
test_waits: db 0
test_decline: db 0
test_last_ptr: dw 0
test_last_len: dw 0
    SAVEBIN "p513-prompts.bin",$C000,$-$C000
""",encoding="utf-8",newline="\n")
    fr=run_command([asm,"--nologo","--lst=p513-prompts.lst","--sym=p513-prompts.sym","p513-prompts.asm"],cwd=b,timeout_seconds=30)
    require(not fr.timed_out and fr.exit_code==0,f"P5.13 fixture assembly failed: {fr.stderr or fr.stdout}")
    binary=b/"p513-prompts.bin"
    if action=="test":
      names=("zx48_p513_foreground_enter","zx48_p513_foreground_leave","zx48_p513_prompt_play","zx48_p513_prompt_record","p513_interactive","p513_prompt_kind","test_writes","test_waits","test_decline","P513_PROMPT_PLAY","P513_PROMPT_RECORD","E_AGAIN","E_INTR")
      s=phase3_open_descriptions._symbols(b/"p513-prompts.sym",names)
      def patch(ram):
        m=binary.read_bytes(); ram[MODULE-0x4000:MODULE-0x4000+len(m)]=m
      # Background/cron: no write/wait callback, E_AGAIN.
      code=b"\xF3"+phase1._ld_sp(STACK)+phase1._call(s["zx48_p513_prompt_play"])
      code+=bytes((0xD2,FAIL_PC&255,FAIL_PC>>8,0xFE,s["E_AGAIN"]&255))+phase1._jp_nz(FAIL_PC)
      code+=checkb(s["test_writes"],0)+checkb(s["test_waits"],0)+phase1._jp(PASS_PC)
      run_sna(root,code,patch=patch)
      # Foreground PLAY then RECORD: each visibly emits and waits before success.
      code=b"\xF3"+phase1._ld_sp(STACK)+phase1._call(s["zx48_p513_foreground_enter"])+phase1._jp_c(FAIL_PC)
      code+=phase1._call(s["zx48_p513_prompt_play"])+phase1._jp_c(FAIL_PC)+checkb(s["p513_prompt_kind"],s["P513_PROMPT_PLAY"])+checkb(s["test_writes"],1)+checkb(s["test_waits"],1)
      code+=phase1._call(s["zx48_p513_prompt_record"])+phase1._jp_c(FAIL_PC)+checkb(s["p513_prompt_kind"],s["P513_PROMPT_RECORD"])+checkb(s["test_writes"],2)+checkb(s["test_waits"],2)
      code+=phase1._call(s["zx48_p513_foreground_leave"])+checkb(s["p513_interactive"],0)+phase1._jp(PASS_PC)
      run_sna(root,code,patch=patch)
      # Declined consent returns E_INTR and does not imply cassette authorization.
      def decline(ram):
        patch(ram); ram[s["test_decline"]-0x4000]=1
      code=b"\xF3"+phase1._ld_sp(STACK)+phase1._call(s["zx48_p513_foreground_enter"])+phase1._call(s["zx48_p513_prompt_play"])
      code+=bytes((0xD2,FAIL_PC&255,FAIL_PC>>8,0xFE,s["E_INTR"]&255))+phase1._jp_nz(FAIL_PC)+phase1._jp(PASS_PC)
      run_sna(root,code,patch=decline)
      assertions += [
        {"name":"background-prompt-suppressed-runtime","passed":True},
        {"name":"foreground-play-record-prompt-state-runtime","passed":True},
        {"name":"declined-consent-is-e-intr-runtime","passed":True},
      ]
    hashes={
      "v1/build/kernel.bin":sha256_file(kernel),"v1/build/p513-prompts.bin":sha256_file(binary),
      "v1/src/kernel/tape.asm":sha256_file(root/"v1/src/kernel/tape.asm"),
      "v1/tools-host/test-driver/phase5_tape_prompts.py":sha256_file(root/"v1/tools-host/test-driver/phase5_tape_prompts.py"),
      "v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
      "v1/dist/certification/P5.12.build.json":sha256_file(root/"v1/dist/certification/P5.12.build.json"),
      "v1/dist/certification/P5.12.test.json":sha256_file(root/"v1/dist/certification/P5.12.test.json"),
    }
    return [kr,fr],hashes,assertions
