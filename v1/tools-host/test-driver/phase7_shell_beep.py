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

CORE=0x6000
SHELL=0xC000
GATE=0xE000
ARG=0xA000
NAME=0xA100
REPL=0xA200
ROM_CALC_STACK=0x5D80

class P720Error(DriverError): pass
def req(v,m):
    if not v: raise P720Error(m)
def w(v): return bytes((v&255,(v>>8)&255))
def call(a): return b"\xcd"+w(a)
def jpc(a): return b"\xda"+w(a)
def jpnc(a): return b"\xd2"+w(a)
def checkb(a,v): return b"\x3a"+w(a)+bytes((0xfe,v&255))+phase1._jp_nz(FAIL_PC)
def checkw(a,v): return b"\x2a"+w(a)+phase1._ld_de(v)+b"\xb7\xed\x52"+phase1._jp_nz(FAIL_PC)
def checkmem(a,data): return b"".join(checkb(a+i,v) for i,v in enumerate(data))

def source(root):
    sh=(root/"v1/src/shell/sh.asm").read_text()
    snd=(root/"v1/src/kernel/sound.asm").read_text()
    plan=(root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md").read_text()
    m=sh.split("MACRO EMIT_P720_BEEP_BUILTIN_ROUTINES",1)[1].split("ENDM",1)[0]
    before_eval=m.split("call sh_p710_calc_builtin",1)[0]
    return [
      {"name":"canonical-p720-present","passed":"## P7.20 - beep shell builtin" in plan},
      {"name":"exact-lowercase-beep-lookup","passed":"sh_p720_lookup_beep:" in m and all(f"cp '{x}'" in m for x in "beep")},
      {"name":"lookup-never-enters-path-bcat-tape","passed":all(x not in m for x in ("SYS_STAT","SYS_OPEN","SYS_SPAWN","SYS_TAPE_"))},
      {"name":"one-shell-argument-required","passed":"cp 2" in m and m.index("cp 2")<m.index("sh_p720_split_scan:")},
      {"name":"foreground-single-stage-before-parse","passed":m.index("cp 1")<m.index("sh_p720_split_scan:") and m.index("ld a,c")<m.index("sh_p720_split_scan:")},
      {"name":"top-level-comma-depth-tracked","passed":all(x in m for x in ("p720_depth","p720_comma_seen","sh_p720_split_comma_nested"))},
      {"name":"both-operands-safe-tokenized-before-rom-evaluation","passed":before_eval.count("call sh_p710_tokenize")==2},
      {"name":"exact-calc-grammar-reused","passed":"call sh_p710_tokenize" in m and "call sh_p710_calc_builtin" in m},
      {"name":"sys-beep-invoked-once","passed":m.count("SYS_BEEP")==1},
      {"name":"no-narrower-pitch-range","passed":"pitch" in m.lower() and all(x not in m for x in ("cp 128","cp 96","cp 64"))},
      {"name":"shared-synchronous-sound-service-bound","passed":"P7.20 shell beep reaches this same synchronous service" in snd},
    ]

def assemble(root,run_command,require_project_tool):
    asm=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus")
    b=root/"v1/build"; b.mkdir(parents=True,exist_ok=True)
    f=b/"p720-shell-beep.asm"
    f.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/kernel/rom_services.asm"
    INCLUDE "../src/kernel/sound.asm"
    INCLUDE "../src/shell/sh.asm"

    ORG $6000
p720_core:
altreg_busy: db 0
ula_shadow: db 3
zx48_kernel_stack_sample: ret
zx48_kernel_stack_check: xor a : ret
zx48_ula_rom_prepare:
    push af
    ld a,1
    ld (altreg_busy),a
    pop af
    ret
zx48_ula_commit: ld (ula_shadow),a : ret
    EMIT_P710_ROM_CALC_ROUTINES
    EMIT_P709_ROM_BEEP_ROUTINES
    EMIT_SOUND_ROUTINES
p720_core_end:
    SAVEBIN "p720-core.bin",p720_core,p720_core_end-p720_core

    ORG $C000
p720_shell:
    EMIT_P617_BUILTIN_REDIR_ROUTINES
    EMIT_P710_CALC_ROUTINES
    EMIT_P720_BEEP_BUILTIN_ROUTINES
p720_shell_end:
    SAVEBIN "p720-shell.bin",p720_shell,p720_shell_end-p720_shell

    ORG $E000
p720_gate:
    cp SYS_BEEP
    jp z,p720_beep
    cp SYS_CLOSE
    jp z,p720_close
    cp SYS_DUP
    jp z,p720_dup
    ld a,(p720_forbidden_calls)
    inc a
    ld (p720_forbidden_calls),a
    ld a,E_NOTSUP
    scf
    ret
p720_beep:
    ld (p720_seen_hl),hl
    ld (p720_seen_de),de
    ld a,(p720_beep_calls)
    inc a
    ld (p720_beep_calls),a
    ld a,(p720_skip_sound)
    or a
    jp z,zx48_sound_beep
    xor a
    ret

p720_close:
    ld a,h
    or a
    jp nz,p720_bad
    ld a,l
    cp 8
    jp nc,p720_bad
    ld e,a
    ld d,0
    ld hl,p720_handles
    add hl,de
    ld a,(hl)
    cp HANDLE_FREE
    jp z,p720_noent
    ld (hl),HANDLE_FREE
    xor a
    ld hl,0
    ret

p720_dup:
    ld b,(hl)
    inc hl
    ld c,(hl)
    ld a,b
    cp 8
    jp nc,p720_bad
    ld a,c
    cp 8
    jp nc,p720_bad
    ld e,b
    ld d,0
    ld hl,p720_handles
    add hl,de
    ld a,(hl)
    cp HANDLE_FREE
    jp z,p720_noent
    ld (p720_value),a
    ld e,c
    ld d,0
    ld hl,p720_handles
    add hl,de
    ld a,(hl)
    cp HANDLE_FREE
    jp nz,p720_busy
    ld a,(p720_value)
    ld (hl),a
    ld l,c
    ld h,0
    xor a
    ret

p720_bad:
    ld a,E_INVAL
    scf
    ret
p720_noent:
    ld a,E_NOENT
    scf
    ret
p720_busy:
    ld a,E_BUSY
    scf
    ret

    ORG $E180
p720_handles: db $A0,$A1,$A2,$B0,$B1,$FF,$FF,$FF
p720_value: db 0
p720_beep_calls: db 0
p720_forbidden_calls: db 0
p720_skip_sound: db 0
p720_seen_hl: dw 0
p720_seen_de: dw 0
p720_gate_end:
    SAVEBIN "p720-gate.bin",p720_gate,p720_gate_end-p720_gate
""",encoding="utf-8",newline="\n")
    r=run_command([asm,"--nologo","--sym=p720-shell-beep.sym","p720-shell-beep.asm"],cwd=b,timeout_seconds=30)
    req(r.exit_code==0 and not r.timed_out,f"P7.20 fixture assembly: {r.stderr or r.stdout}")
    for n in ("p720-core.bin","p720-shell.bin","p720-gate.bin"):
        req((b/n).is_file() and (b/n).stat().st_size>0,f"missing {n}")
    return r,b/"p720-core.bin",b/"p720-shell.bin",b/"p720-gate.bin",b/"p720-shell-beep.sym"

def patch(core,shell,gate,s,arg=b"",name=b"",calc_sentinel=False,skip_sound=False,fp=None):
    def p(ram):
        ram[CORE-0x4000:CORE-0x4000+len(core)]=core
        ram[SHELL-0x4000:SHELL-0x4000+len(shell)]=shell
        ram[GATE-0x4000:GATE-0x4000+len(gate)]=gate
        ram[ARG-0x4000:ARG-0x4000+len(arg)+1]=arg+b"\0"
        ram[NAME-0x4000:NAME-0x4000+len(name)+1]=name+b"\0"
        ram[REPL-0x4000:REPL-0x4000+3]=bytes((3,4,3))
        if skip_sound:
            ram[s["p720_skip_sound"]-0x4000]=1
        if fp is not None:
            dur,pitch=fp
            ram[s["p720_duration_fp"]-0x4000:s["p720_duration_fp"]-0x4000+5]=dur
            ram[s["p720_pitch_fp"]-0x4000:s["p720_pitch_fp"]-0x4000+5]=pitch
        if calc_sentinel:
            ram[ROM_CALC_STACK-0x4000:ROM_CALC_STACK-0x4000+16]=b"\xA5"*16
    return p

def invoke(s,argc=2,stages=1,bg=0):
    return phase1._ld_hl(ARG)+bytes((0x3e,argc&255,0x06,stages&255,0x0e,bg&255))+call(s["sh_p720_beep_builtin"])

def valid(root,s,core,shell,gate,arg,dur,pitch):
    code=bytearray(b"\xf3"+phase1._ld_sp(0xBFC0)+invoke(s)+jpc(FAIL_PC)+b"\xb7"+phase1._jp_nz(FAIL_PC))
    code+=checkb(s["p720_beep_calls"],1)+checkb(s["p720_forbidden_calls"],0)
    code+=checkw(s["p720_seen_hl"],s["p720_duration_fp"])+checkw(s["p720_seen_de"],s["p720_pitch_fp"])
    code+=checkmem(s["p720_duration_fp"],dur)+checkmem(s["p720_pitch_fp"],pitch)
    code+=checkb(s["altreg_busy"],0)+checkb(s["ula_shadow"],3)+phase1._jp(PASS_PC)
    run_sna(root,bytes(code),patch=patch(core,shell,gate,s,arg=arg),timeout=35)

def calc_result(root,s,core,shell,gate,expr,expected=None):
    code=bytearray(b"\xf3"+phase1._ld_sp(0xBFC0)+phase1._ld_hl(ARG)+phase1._ld_de(s["p720_duration_fp"])+bytes((0x3e,2,0x06,1,0x0e,0))+call(s["sh_p710_calc_builtin"]))
    code+=jpc(FAIL_PC)+b"\xb7"+phase1._jp_nz(FAIL_PC)
    if expected is not None:
        code+=checkmem(s["p720_duration_fp"],expected)
    code+=checkb(s["altreg_busy"],0)+phase1._jp(PASS_PC)
    run_sna(root,bytes(code),patch=patch(core,shell,gate,s,arg=expr),timeout=20)

def conversion_only(root,s,core,shell,gate,arg,dur,pitch):
    code=bytearray(b"\xf3"+phase1._ld_sp(0xBFC0)+invoke(s)+jpc(FAIL_PC)+b"\xb7"+phase1._jp_nz(FAIL_PC))
    code+=checkb(s["p720_beep_calls"],1)+checkb(s["p720_forbidden_calls"],0)
    code+=checkw(s["p720_seen_hl"],s["p720_duration_fp"])+checkw(s["p720_seen_de"],s["p720_pitch_fp"])
    code+=checkmem(s["p720_duration_fp"],dur)+checkmem(s["p720_pitch_fp"],pitch)
    code+=checkb(s["altreg_busy"],0)+phase1._jp(PASS_PC)
    run_sna(root,bytes(code),patch=patch(core,shell,gate,s,arg=arg,skip_sound=True),timeout=20)

def direct_beep(root,s,core,shell,gate,dur,pitch):
    code=bytearray(b"\xf3"+phase1._ld_sp(0xBFC0)+phase1._ld_hl(s["p720_duration_fp"])+phase1._ld_de(s["p720_pitch_fp"])+bytes((0x3e,s["SYS_BEEP"]&255))+call(GATE))
    code+=jpc(FAIL_PC)+b"\xb7"+phase1._jp_nz(FAIL_PC)
    code+=checkb(s["p720_beep_calls"],1)+checkb(s["p720_forbidden_calls"],0)
    code+=checkb(s["altreg_busy"],0)+checkb(s["ula_shadow"],3)+phase1._jp(PASS_PC)
    run_sna(root,bytes(code),patch=patch(core,shell,gate,s,fp=(dur,pitch)),timeout=35)

def valid_no_exact(root,s,core,shell,gate,arg):
    code=bytearray(b"\xf3"+phase1._ld_sp(0xBFC0)+invoke(s)+jpc(FAIL_PC)+b"\xb7"+phase1._jp_nz(FAIL_PC))
    code+=checkb(s["p720_beep_calls"],1)+checkb(s["p720_forbidden_calls"],0)
    code+=checkw(s["p720_seen_hl"],s["p720_duration_fp"])+checkw(s["p720_seen_de"],s["p720_pitch_fp"])
    code+=checkb(s["altreg_busy"],0)+phase1._jp(PASS_PC)
    run_sna(root,bytes(code),patch=patch(core,shell,gate,s,arg=arg),timeout=35)

def invalid(root,s,core,shell,gate,arg,errno,argc=2,stages=1,bg=0):
    code=bytearray(b"\xf3"+phase1._ld_sp(0xBFC0)+invoke(s,argc,stages,bg)+jpnc(FAIL_PC)+bytes((0xfe,errno&255))+phase1._jp_nz(FAIL_PC))
    code+=checkb(s["p720_beep_calls"],0)+checkb(s["p720_forbidden_calls"],0)+checkb(s["altreg_busy"],0)
    code+=checkmem(ROM_CALC_STACK,b"\xA5"*16)+phase1._jp(PASS_PC)
    run_sna(root,bytes(code),patch=patch(core,shell,gate,s,arg=arg,calc_sentinel=True),timeout=20)

def lookup(root,s,core,shell,gate,name,ok):
    code=bytearray(b"\xf3"+phase1._ld_sp(0xBFC0)+phase1._ld_hl(NAME)+bytes((0x06,len(name)))+call(s["sh_p720_lookup_beep"]))
    if ok:
        code+=jpc(FAIL_PC)+b"\xd5\xe1"+phase1._ld_de(s["sh_p720_beep_builtin"])+b"\xb7\xed\x52"+phase1._jp_nz(FAIL_PC)
    else:
        code+=jpnc(FAIL_PC)+bytes((0xfe,s["E_NOENT"]&255))+phase1._jp_nz(FAIL_PC)
    code+=checkb(s["p720_beep_calls"],0)+checkb(s["p720_forbidden_calls"],0)+phase1._jp(PASS_PC)
    run_sna(root,bytes(code),patch=patch(core,shell,gate,s,name=name))

def redirection(root,s,core,shell,gate):
    arg=b".25,0"
    code=bytearray(b"\xf3"+phase1._ld_sp(0xBFC0)+b"\xdd\x21"+w(REPL)+call(s["sh_p617_prepare"])+jpc(FAIL_PC))
    code+=checkb(s["p720_handles"]+0,0xB0)+checkb(s["p720_handles"]+1,0xB1)+checkb(s["p720_handles"]+2,0xB0)
    code+=invoke(s)+jpc(FAIL_PC)+call(s["sh_p617_restore"])+jpc(FAIL_PC)
    code+=checkb(s["p720_handles"]+0,0xA0)+checkb(s["p720_handles"]+1,0xA1)+checkb(s["p720_handles"]+2,0xA2)
    code+=checkb(s["p720_handles"]+5,0xFF)+checkb(s["p720_handles"]+6,0xFF)+checkb(s["p720_handles"]+7,0xFF)
    code+=checkb(s["p720_beep_calls"],1)+checkb(s["p720_forbidden_calls"],0)+phase1._jp(PASS_PC)
    run_sna(root,bytes(code),patch=patch(core,shell,gate,s,arg=arg),timeout=30)

def case(name, fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except DriverError as exc:
        raise P720Error(f"{name}: {exc}") from exc

def dispatch(root,action,step,*,sha256_file,run_command,require_project_tool):
    if step!="P7.20": raise P720Error(step)
    assertions=source(root); bad=[x["name"] for x in assertions if not x["passed"]]; req(not bad,f"static: {bad}")
    kc,kernel,_=phase1._assemble_kernel(root,run_command,require_project_tool)
    fr,cb,sb,gb,sym=assemble(root,run_command,require_project_tool)
    names=("sh_p720_beep_builtin","sh_p720_lookup_beep","sh_p710_calc_builtin","sh_p617_prepare","sh_p617_restore",
           "p720_duration_fp","p720_pitch_fp","altreg_busy","ula_shadow","p720_handles",
           "p720_beep_calls","p720_forbidden_calls","p720_skip_sound","p720_seen_hl","p720_seen_de",
           "SYS_BEEP","E_INVAL","E_NOTSUP","E_NOENT")
    s=phase3_open_descriptions._symbols(sym,names)
    if action=="test":
        core=cb.read_bytes(); shell=sb.read_bytes(); gate=gb.read_bytes()
        case("valid-1-0",valid,root,s,core,shell,gate,b"1,0",bytes((0,0,1,0,0)),bytes((0,0,0,0,0)))
        case("calc-half-noexact",calc_result,root,s,core,shell,gate,b".5")
        case("calc-half-exact",calc_result,root,s,core,shell,gate,b".5",bytes((0x80,0,0,0,0)))
        case("calc-nine-exact",calc_result,root,s,core,shell,gate,b"9",bytes((0,0,9,0,0)))
        case("convert-half-9",conversion_only,root,s,core,shell,gate,b".5,9",bytes((0x80,0,0,0,0)),bytes((0,0,9,0,0)))
        case("direct-half-9",direct_beep,root,s,core,shell,gate,bytes((0x80,0,0,0,0)),bytes((0,0,9,0,0)))
        case("valid-half-9",valid,root,s,core,shell,gate,b".5,9",bytes((0x80,0,0,0,0)),bytes((0,0,9,0,0)))
        case("valid-quarter-minus12",valid,root,s,core,shell,gate,b".25,-12",bytes((0x7f,0,0,0,0)),bytes((0,0xff,0xf4,0xff,0)))
        case("valid-half-half",valid,root,s,core,shell,gate,b".5,0.5",bytes((0x80,0,0,0,0)),bytes((0x80,0,0,0,0)))
        case("valid-parenthesized",valid_no_exact,root,s,core,shell,gate,b"(1/4),(12+0.5)")

        for arg in (b"1",b"1,2,3",b",1",b"1,",b"(1,2",b"1,usr(0)",b"peek(1),0",b"in(1),0",b"poke 1,2,0",b"out 1,2,0",b"1,(2,3)"):
            case(f"invalid-{arg!r}",invalid,root,s,core,shell,gate,arg,s["E_INVAL"])
        case("invalid-argc-1",invalid,root,s,core,shell,gate,b"1,0",s["E_INVAL"],argc=1)
        case("invalid-argc-3",invalid,root,s,core,shell,gate,b"1,0",s["E_INVAL"],argc=3)
        case("invalid-pipeline",invalid,root,s,core,shell,gate,b"USR(0),0",s["E_NOTSUP"],stages=2)
        case("invalid-background",invalid,root,s,core,shell,gate,b"USR(0),0",s["E_NOTSUP"],bg=1)

        case("lookup-beep",lookup,root,s,core,shell,gate,b"beep",True)
        for name in (b"BEEP",b"Beep",b"beepx",b"calc"):
            case(f"lookup-{name!r}",lookup,root,s,core,shell,gate,name,False)
        case("redirection",redirection,root,s,core,shell,gate)

        assertions += [
          {"name":"fuse-basic-compatible-beep-vectors-pass","passed":True},
          {"name":"fuse-parenthesized-expression-comma-depth-pass","passed":True},
          {"name":"fuse-malformed-and-unsafe-operands-fail-before-rom-stack-mutation","passed":True},
          {"name":"fuse-pipeline-background-fail-before-parse-or-side-effect","passed":True},
          {"name":"fuse-lowercase-only-lookup-never-enters-external-resolution","passed":True},
          {"name":"fuse-sys-beep-reached-exactly-once-per-valid-command","passed":True},
          {"name":"fuse-builtin-redirection-restores-exact-stdio","passed":True},
        ]
    hashes={str(x.relative_to(root)):sha256_file(x) for x in (
      root/"v1/src/shell/sh.asm",root/"v1/src/kernel/sound.asm",
      root/"v1/tools-host/test-driver/phase7_shell_beep.py",root/"v1/tools-host/test-driver/run.py",kernel)}
    return [kc,fr],hashes,assertions
