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
from pathlib import Path
from driver_core import DriverError
from fuse_harness import FAIL_PC, PASS_PC, run_sna
import phase1, phase3_open_descriptions

BASE=0xC000
GATE=0xE000
STATE=0xA000

class P622Error(DriverError): pass
def require(v,m):
    if not v: raise P622Error(m)
def word(v): return bytes((v&255,(v>>8)&255))
def expect_byte(addr,val): return b"\x3A"+word(addr)+bytes((0xFE,val&255))+phase1._jp_nz(FAIL_PC)
def patch(shell,gate):
    def p(ram):
        ram[BASE-0x4000:BASE-0x4000+len(shell)]=shell
        ram[GATE-0x4000:GATE-0x4000+len(gate)]=gate
        ram[STATE-0x4000:STATE-0x4000+16]=b"\0"*16
    return p

def dispatch(root:Path,action:str,step:str,*,sha256_file,run_command,require_project_tool):
    if step!="P6.22": raise DriverError(f"Phase-6 tty-owner step is not registered: {step}")
    sp=root/"v1/src/shell/sh.asm"; cp=root/"v1/src/kernel/console.asm"
    text=sp.read_text(); console=cp.read_text()
    macro=text.split("MACRO EMIT_P622_TTY_OWNER_ROUTINES",1)[1].split("ENDM",1)[0]
    assertions=[
      {"name":"shell-owner-change-via-tty-ioctl","passed":"SYS_IOCTL" in macro and "P622_SET_OWNER           EQU 7" in text},
      {"name":"foreground-owner-live-user-pid-range","passed":"cp 2" in macro and "cp MAX_PROCESSES" in macro},
      {"name":"shell-owner-restored-to-pid1","passed":"sh_p622_restore_shell_owner:" in macro and "ld a,1" in macro},
      {"name":"kernel-only-pid1-can-set-owner","passed":"cp 1" in console and "zx48_tty_perm" in console},
      {"name":"kernel-nonowner-input-e-busy-contract","passed":"P622_TTY_SET_INPUT_OWNER EQU TTY_REQ_SET_OWNER" in console},
      {"name":"background-does-not-steal-owner","passed":"background" in text[text.index("; P6.22"):].lower()},
    ]
    require(all(a["passed"] for a in assertions),"P6.22 static contract failure")
    asm=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus"); build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    sf=build/"p622-shell-fixture.asm"
    sf.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/shell/sh.asm"
    ORG $C000
p622_start:
    EMIT_P622_TTY_OWNER_ROUTINES
p622_end:
    SAVEBIN "p622-shell-fixture.bin",p622_start,p622_end-p622_start
""",encoding="utf-8",newline="\n")
    sr=run_command([asm,"--nologo","--lst=p622-shell-fixture.lst","--sym=p622-shell-fixture.sym","p622-shell-fixture.asm"],cwd=build,timeout_seconds=30)
    require(not sr.timed_out and sr.exit_code==0,f"P6.22 shell fixture failed: {sr.stderr or sr.stdout}")
    gf=build/"p622-gateway.asm"
    gf.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    ORG $E000
p622_gate:
    cp SYS_IOCTL
    jr nz,p622_notsup
    ld a,(hl)
    or a
    jr nz,p622_bad
    inc hl
    ld a,(hl)
    cp 7
    jr nz,p622_bad
    inc hl
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld a,(de)
    ld ($A000),a
    xor a
    ret
p622_bad: ld a,E_INVAL : scf : ret
p622_notsup: ld a,E_NOTSUP : scf : ret
p622_gate_end:
    SAVEBIN "p622-gateway.bin",p622_gate,p622_gate_end-p622_gate
""",encoding="utf-8",newline="\n")
    gr=run_command([asm,"--nologo","--lst=p622-gateway.lst","--sym=p622-gateway.sym","p622-gateway.asm"],cwd=build,timeout_seconds=30)
    require(not gr.timed_out and gr.exit_code==0,f"P6.22 gateway failed: {gr.stderr or gr.stdout}")
    if action=="test":
        sy=phase3_open_descriptions._symbols(build/"p622-shell-fixture.sym",("sh_p622_set_foreground_owner","sh_p622_restore_shell_owner","E_INVAL"))
        shell=(build/"p622-shell-fixture.bin").read_bytes(); gate=(build/"p622-gateway.bin").read_bytes()
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+b"\x3E\x02"+phase1._call(sy["sh_p622_set_foreground_owner"])+phase1._jp_c(FAIL_PC))
        code+=expect_byte(STATE,2)+phase1._call(sy["sh_p622_restore_shell_owner"])+phase1._jp_c(FAIL_PC)+expect_byte(STATE,1)+phase1._jp(PASS_PC)
        run_sna(root,bytes(code),patch=patch(shell,gate))
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+b"\x3E\x01"+phase1._call(sy["sh_p622_set_foreground_owner"])+b"\xD2"+word(FAIL_PC))
        code+=bytes((0xFE,sy["E_INVAL"]&255))+phase1._jp_nz(FAIL_PC)+expect_byte(STATE,0)+phase1._jp(PASS_PC)
        run_sna(root,bytes(code),patch=patch(shell,gate))
        assertions += [{"name":"fuse-owner-handoff-and-restore","passed":True},{"name":"fuse-invalid-owner-no-side-effect","passed":True}]
    hashes={
      "v1/src/shell/sh.asm":sha256_file(sp),"v1/src/kernel/console.asm":sha256_file(cp),
      "v1/tools-host/test-driver/phase6_tty_owner.py":sha256_file(root/"v1/tools-host/test-driver/phase6_tty_owner.py"),
      "v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
      "v1/dist/certification/P6.21.build.json":sha256_file(root/"v1/dist/certification/P6.21.build.json"),
      "v1/dist/certification/P6.21.test.json":sha256_file(root/"v1/dist/certification/P6.21.test.json"),
      "v1/dist/media/P6.21/manifest.json":sha256_file(root/"v1/dist/media/P6.21/manifest.json")}
    return [sr,gr],hashes,assertions
