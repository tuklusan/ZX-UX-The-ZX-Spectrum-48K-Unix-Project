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

SHELL=0xC000
GATE=0xE000
REPL=0xA000
SIDE=0xA010

class P617Error(DriverError): pass
def require(v,m):
    if not v: raise P617Error(m)
def word(v): return bytes((v&255,(v>>8)&255))
def expect_byte(addr,val): return b"\x3A"+word(addr)+bytes((0xFE,val&255))+phase1._jp_nz(FAIL_PC)

def patch(shell,gate,repl=(3,4,3),fail=0):
    def p(ram):
        ram[SHELL-0x4000:SHELL-0x4000+len(shell)]=shell
        ram[GATE-0x4000:GATE-0x4000+len(gate)]=gate
        ram[REPL-0x4000:REPL-0x4000+3]=bytes(repl)
        ram[SIDE-0x4000]=0
        # gate handles 0..7: original stdio A0/A1/A2, redirection refs B0/B1, spare free
        ram[0xE180-0x4000:0xE188-0x4000]=bytes((0xA0,0xA1,0xA2,0xB0,0xB1,0xFF,0xFF,0xFF))
        ram[0xE188-0x4000]=fail
        ram[0xE189-0x4000]=0
    return p

def dispatch(root:Path,action:str,step:str,*,sha256_file,run_command,require_project_tool):
    if step!="P6.17": raise DriverError(f"Phase-6 builtin-redirection step is not registered: {step}")
    sp=root/"v1/src/shell/sh.asm"; text=sp.read_text(); macro=text.split("MACRO EMIT_P617_BUILTIN_REDIR_ROUTINES",1)[1].split("ENDM",1)[0]
    assertions=[
      {"name":"spare-handles-5-6-7","passed":"P617_SAVE_STDIN         EQU 5" in text and "P617_SAVE_STDOUT        EQU 6" in text and "P617_SAVE_STDERR        EQU 7" in text},
      {"name":"preserve-before-replacement","passed":macro.index("call sh_p617_preserve_all") < macro.index("sh_p617_apply_loop:")},
      {"name":"failure-rolls-back","passed":"sh_p617_prepare_fail:" in macro and "call sh_p617_restore" in macro},
      {"name":"restore-standard-before-closing-spares","passed":macro.index("ld a,P617_SAVE_STDIN\n    ld (p617_dup_req),a\n    xor a") < macro.index("ld a,P617_SAVE_STDIN\n    call sh_p617_close_handle_ignore")},
      {"name":"builtin-side-effect-outside-prepare","passed":"SIDE" not in macro},
    ]
    require(all(a["passed"] for a in assertions),"P6.17 static contract failure")
    asm=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus"); build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    sf=build/"p617-shell-fixture.asm"
    sf.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/shell/sh.asm"
    ORG $C000
p617_start:
    EMIT_P617_BUILTIN_REDIR_ROUTINES
p617_end:
    SAVEBIN "p617-shell-fixture.bin",p617_start,p617_end-p617_start
""",encoding="utf-8",newline="\n")
    sr=run_command([asm,"--nologo","--lst=p617-shell-fixture.lst","--sym=p617-shell-fixture.sym","p617-shell-fixture.asm"],cwd=build,timeout_seconds=30)
    require(not sr.timed_out and sr.exit_code==0,f"P6.17 shell fixture failed: {sr.stderr or sr.stdout}")
    gf=build/"p617-gateway.asm"
    gf.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    ORG $E000
p617_gate:
    cp SYS_CLOSE
    jr z,p617_close
    cp SYS_DUP
    jr z,p617_dup
    ld a,E_NOTSUP
    scf
    ret
p617_close:
    ld a,h
    or a
    jr nz,p617_bad
    ld a,l
    cp 8
    jr nc,p617_bad
    ld e,a
    ld d,0
    ld hl,p617_handles
    add hl,de
    ld a,(hl)
    cp HANDLE_FREE
    jr z,p617_noent
    ld (hl),HANDLE_FREE
    xor a
    ld hl,0
    ret
p617_dup:
    ld b,(hl)
    inc hl
    ld c,(hl)
    ld a,b
    cp 8
    jr nc,p617_bad
    ld a,c
    cp 8
    jr nc,p617_bad
    ld e,b
    ld d,0
    ld hl,p617_handles
    add hl,de
    ld a,(hl)
    cp HANDLE_FREE
    jr z,p617_noent
    ld (p617_value),a
    ld a,c
    cp 3
    jr nc,p617_dup_install
    ld a,(p617_attempt)
    inc a
    ld (p617_attempt),a
    ld b,a
    ld a,(p617_fail_on)
    cp b
    jr z,p617_injected
p617_dup_install:
    ld e,c
    ld d,0
    ld hl,p617_handles
    add hl,de
    ld a,(hl)
    cp HANDLE_FREE
    jr nz,p617_busy
    ld a,(p617_value)
    ld (hl),a
    ld l,c
    ld h,0
    xor a
    ret
p617_injected:
    ld a,E_NOSPC
    scf
    ret
p617_bad:
    ld a,E_INVAL
    scf
    ret
p617_noent:
    ld a,E_NOENT
    scf
    ret
p617_busy:
    ld a,E_BUSY
    scf
    ret
    ORG $E180
p617_handles: db $A0,$A1,$A2,$B0,$B1,$FF,$FF,$FF
p617_fail_on: db 0
p617_attempt: db 0
p617_value: db 0
p617_gate_end:
    SAVEBIN "p617-gateway.bin",p617_gate,p617_gate_end-p617_gate
""",encoding="utf-8",newline="\n")
    gr=run_command([asm,"--nologo","--lst=p617-gateway.lst","--sym=p617-gateway.sym","p617-gateway.asm"],cwd=build,timeout_seconds=30)
    require(not gr.timed_out and gr.exit_code==0,f"P6.17 gateway fixture failed: {gr.stderr or gr.stdout}")
    if action=="test":
        sy=phase3_open_descriptions._symbols(build/"p617-shell-fixture.sym",("sh_p617_prepare","sh_p617_restore",))
        shell=(build/"p617-shell-fixture.bin").read_bytes(); gate=(build/"p617-gateway.bin").read_bytes()
        # Success: redirected refs visible during builtin, then exact originals restored.
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+b"\xDD\x21"+word(REPL)+phase1._call(sy["sh_p617_prepare"])+phase1._jp_c(FAIL_PC))
        code+=expect_byte(0xE180,0xB0)+expect_byte(0xE181,0xB1)+expect_byte(0xE182,0xB0)
        code+=b"\x3E\x01\x32"+word(SIDE)
        code+=phase1._call(sy["sh_p617_restore"])+phase1._jp_c(FAIL_PC)
        code+=expect_byte(0xE180,0xA0)+expect_byte(0xE181,0xA1)+expect_byte(0xE182,0xA2)
        code+=expect_byte(0xE185,0xFF)+expect_byte(0xE186,0xFF)+expect_byte(0xE187,0xFF)+expect_byte(SIDE,1)+phase1._jp(PASS_PC)
        run_sna(root,bytes(code),patch=patch(shell,gate))

        # Inject failure at each replacement. Caller never executes builtin side effect.
        for fail in (1,2,3):
            code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+b"\xDD\x21"+word(REPL)+phase1._call(sy["sh_p617_prepare"])+b"\xD2"+word(FAIL_PC))
            code+=expect_byte(0xE180,0xA0)+expect_byte(0xE181,0xA1)+expect_byte(0xE182,0xA2)
            code+=expect_byte(0xE185,0xFF)+expect_byte(0xE186,0xFF)+expect_byte(0xE187,0xFF)+expect_byte(SIDE,0)+phase1._jp(PASS_PC)
            run_sna(root,bytes(code),patch=patch(shell,gate,fail=fail))
        assertions += [
          {"name":"fuse-success-restore-exact-stdio","passed":True},
          {"name":"fuse-failure-after-replacement-1-rolls-back","passed":True},
          {"name":"fuse-failure-after-replacement-2-rolls-back","passed":True},
          {"name":"fuse-failure-after-replacement-3-rolls-back","passed":True},
          {"name":"fuse-next-command-sees-original-stdout","passed":True},
        ]
    hashes={
      "v1/src/shell/sh.asm":sha256_file(sp),
      "v1/tools-host/test-driver/phase6_builtin_redir.py":sha256_file(root/"v1/tools-host/test-driver/phase6_builtin_redir.py"),
      "v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
      "v1/dist/certification/P6.16.build.json":sha256_file(root/"v1/dist/certification/P6.16.build.json"),
      "v1/dist/certification/P6.16.test.json":sha256_file(root/"v1/dist/certification/P6.16.test.json"),
      "v1/dist/media/P6.16/manifest.json":sha256_file(root/"v1/dist/media/P6.16/manifest.json")}
    return [sr,gr],hashes,assertions
