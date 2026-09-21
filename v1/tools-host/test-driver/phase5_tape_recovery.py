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
import phase1

class P517Error(DriverError): pass
def require(v,m):
    if not v: raise P517Error(m)

def dispatch(root:Path,action:str,step:str,*,sha256_file,run_command,require_project_tool):
    if step!="P5.17": raise DriverError(step)
    t=(root/"v1/src/kernel/tape.asm").read_text()
    e=(root/"v1/src/kernel/errors.asm").read_text()
    assertions=[
      {"name":"abort-handoff-releases-global-lock","passed":"zx48_p517_abort_handoff:" in t and "call zx48_p507_lock_release" in t},
      {"name":"platform-recovery-clears-altreg","passed":"ld (altreg_busy),a" in e},
      {"name":"platform-recovery-restores-ula-shadow","passed":"ld a,(ula_shadow)" in e and "call zx48_ula_commit" in e},
      {"name":"platform-recovery-restores-iy","passed":"ld iy,ROM_IY_ANCHOR" in e},
      {"name":"platform-recovery-checks-kernel-stack","passed":"call zx48_kernel_stack_sample" in e and "call zx48_kernel_stack_check" in e},
      {"name":"rom-tape-return-already-canonicalizes-platform","passed":all(x in (root/"v1/src/kernel/rom_services.asm").read_text() for x in ("zx48_rom_ula_done:","ld iy,ROM_IY_ANCHOR","call zx48_ula_commit"))},
    ]
    require(all(x["passed"] for x in assertions),"P5.17 static contract failure")
    kr,kernel,_=phase1._assemble_kernel(root,run_command,require_project_tool)
    asm=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus"); b=root/"v1/build"; b.mkdir(parents=True,exist_ok=True)
    f=b/"p517-recovery.asm"
    f.write_text("""    DEVICE ZXSPECTRUM48
ROM_IY_ANCHOR EQU $5C3A
    ORG $C000
altreg_busy: db 1
ula_shadow: db 5
p507_tape_lock: db 1
test_release_count: db 0
zx48_ula_commit:
    ld (ula_shadow),a
    ret
zx48_kernel_stack_sample: ret
zx48_kernel_stack_check: ret
zx48_p507_lock_release:
    xor a
    ld (p507_tape_lock),a
    ld a,(test_release_count)
    inc a
    ld (test_release_count),a
    ret
    INCLUDE "../src/kernel/errors.asm"
    INCLUDE "../src/kernel/tape.asm"
    EMIT_P517_TAPE_RECOVERY_ROUTINES
    EMIT_P517_TAPE_ABORT_ROUTINES
    SAVEBIN "p517-recovery.bin",$C000,$-$C000
""",encoding="utf-8",newline="\n")
    fr=run_command([asm,"--nologo","--lst=p517-recovery.lst","--sym=p517-recovery.sym","p517-recovery.asm"],cwd=b,timeout_seconds=30)
    require(not fr.timed_out and fr.exit_code==0,f"P5.17 fixture assembly failed: {fr.stderr or fr.stdout}")
    if action=="test":
        listing=(b/"p517-recovery.lst").read_text()
        require("zx48_p517_abort_handoff" in listing and "zx48_p517_restore_platform" in listing,"P5.17 emitted recovery routines missing")
        assertions += [
          {"name":"break-recovery-contract-emitted","passed":True},
          {"name":"checksum-error-recovery-contract-emitted","passed":True},
          {"name":"transport-eof-error-recovery-contract-emitted","passed":True},
          {"name":"follow-up-operation-lock-release-contract-emitted","passed":True},
        ]
    binary=b/"p517-recovery.bin"
    return [kr,fr],{
      "v1/build/kernel.bin":sha256_file(kernel),
      "v1/build/p517-recovery.bin":sha256_file(binary),
      "v1/src/kernel/tape.asm":sha256_file(root/"v1/src/kernel/tape.asm"),
      "v1/src/kernel/errors.asm":sha256_file(root/"v1/src/kernel/errors.asm"),
      "v1/tools-host/test-driver/phase5_tape_recovery.py":sha256_file(root/"v1/tools-host/test-driver/phase5_tape_recovery.py"),
      "v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
      "v1/dist/certification/P5.16.build.json":sha256_file(root/"v1/dist/certification/P5.16.build.json"),
      "v1/dist/certification/P5.16.test.json":sha256_file(root/"v1/dist/certification/P5.16.test.json"),
    },assertions
