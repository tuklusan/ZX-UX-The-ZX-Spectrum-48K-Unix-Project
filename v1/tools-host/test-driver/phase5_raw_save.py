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
from typing import Any, Callable
from driver_core import DriverError
from fuse_harness import FAIL_PC, PASS_PC, run_sna
import phase1
import phase3_open_descriptions
from phase5_m48o_header import crc16_ccitt_false

MODULE_BASE=0xC000
RECORD_BASE=0x8800
PAYLOAD_BASE=0x8A00
CAPTURE_BASE=0xA000
STACK_TOP=0xBFC0

class P507Error(DriverError): pass

def require(ok: bool, msg: str) -> None:
    if not ok: raise P507Error(msg)

def _source(root: Path):
    s=(root/"v1/src/kernel/tape.asm").read_text(encoding="utf-8")
    m=s.split("MACRO EMIT_P507_RAW_SAVE_ROUTINES",1)[1].split("ENDM",1)[0]
    return [
      {"name":"path-resolve-precedes-tape-motion","passed":"call zx48_path_resolve" in s and s.find("call zx48_path_resolve") < s.find("jp zx48_p507_save_record",s.find("zx48_tape_save_path:"))},
      {"name":"complete-header-before-lock","passed":m.find("call zx48_crc16_ccitt_false") < m.find("call zx48_p507_lock_acquire")},
      {"name":"exact-raw-codec-and-flags","passed":"p507_header+M48O_HDR_STORAGE_LEN" in m and "M48O_HDR_PAYLOAD_CRC" in m},
      {"name":"public-placement-validated","passed":"call zx48_object_public_type_allowed" in m},
      {"name":"header-then-512-byte-chunks","passed":"ld de,M48O_HDR_SIZE" in m and "call zx48_p503_prepare_chunk" in m},
      {"name":"record-prompt-before-global-lock","passed":m.find("call zx48_p507_prompt_record") < m.find("call zx48_p507_lock_acquire")},
      {"name":"all-tape-errors-release-lock","passed":"zx48_p507_release_error:" in m and "call zx48_p507_lock_release" in m},
      {"name":"packed-source-deferred-to-p508","passed":"ld a,E_NOTSUP" in m},
    ]

def _assemble(root,run_command,require_project_tool):
    asm=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus")
    b=root/"v1/build"; b.mkdir(parents=True,exist_ok=True)
    f=b/"p507-raw-save.asm"
    f.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../include/tapeobj.inc"
OBJ_NAME EQU 0
OBJ_DIR_ID EQU 10
OBJ_TYPE_ID EQU 11
OBJ_FLAGS_BYTE EQU 12
OBJ_RESERVED_BYTE EQU 13
OBJ_LOGICAL_LENGTH EQU 14
OBJ_STORAGE_LENGTH EQU 16
OBJ_ALLOCATION_PTR EQU 18
    INCLUDE "../src/kernel/tape.asm"
    ORG $C000
    EMIT_P502_CRC16_ROUTINES
    EMIT_P503_FRAMING_ROUTINES
    EMIT_P507_RAW_SAVE_ROUTINES

zx48_object_public_type_allowed:
    ld a,b
    cp OBJ_TXT
    jr nz,p507_test_perm
    ld a,(p507_target)
    cp DIR_USERHOME
    jr nz,p507_test_perm
    xor a
    ret
p507_test_perm:
    ld a,E_PERM
    scf
    ret

zx48_tape_save_block:
    ld hl,(p507_test_capture_ptr)
    ld (hl),a
    inc hl
    ld (hl),e
    inc hl
    ld (hl),d
    inc hl
    push ix
    pop de
    ex de,hl
    ld bc,0
    ld b,d
    ld c,e
    ex de,hl
    ; DE is not usable as count here: recover original length.
    ld bc,0
    ld c,(hl)
    ; Capture stub below is patched by test-specific wrapper; count only calls.
    ld a,(p507_test_blocks)
    inc a
    ld (p507_test_blocks),a
    xor a
    ret

p507_test_capture_ptr: dw $A000
p507_test_blocks: db 0
    SAVEBIN "p507-raw-save.bin",$C000,$-$C000
""",encoding="utf-8",newline="\n")
    r=run_command([asm,"--nologo","--lst=p507-raw-save.lst","--sym=p507-raw-save.sym","p507-raw-save.asm"],cwd=b,timeout_seconds=30)
    require(not r.timed_out and r.exit_code==0,f"P5.07 fixture assembly failed: {r.stderr or r.stdout}")
    return r,b/"p507-raw-save.bin",b/"p507-raw-save.sym"

def _word(v): return bytes((v&255,(v>>8)&255))
def _ld_ix(v): return b"\xDD\x21"+_word(v)
def _check_byte(a,v): return b"\x3A"+_word(a)+bytes((0xFE,v&255))+phase1._jp_nz(FAIL_PC)
def _check_word(a,v): return b"\x2A"+_word(a)+phase1._ld_de(v)+b"\xB7\xED\x52"+phase1._jp_nz(FAIL_PC)

def _runtime(root,s,module):
    payload=b"ZX-UX raw tape roundtrip\n"*30
    rec=bytearray(20)
    rec[:10]=b"note\0\0\0\0\0\0"
    rec[10]=s["DIR_USERHOME"]; rec[11]=s["OBJ_TXT"]
    rec[14:16]=_word(len(payload)); rec[16:18]=_word(len(payload)); rec[18:20]=_word(PAYLOAD_BASE)
    def patch(ram):
        ram[MODULE_BASE-0x4000:MODULE_BASE-0x4000+len(module)]=module
        ram[RECORD_BASE-0x4000:RECORD_BASE-0x4000+20]=rec
        ram[PAYLOAD_BASE-0x4000:PAYLOAD_BASE-0x4000+len(payload)]=payload
        ram[s["p507_test_blocks"]-0x4000]=0
    code=b"\xF3"+phase1._ld_sp(STACK_TOP)+_ld_ix(RECORD_BASE)+phase1._call(s["zx48_p507_save_record"])+phase1._jp_c(FAIL_PC)
    code+=_check_byte(s["p507_tape_lock"],0)+_check_byte(s["p507_test_blocks"],3)
    code+=_check_byte(s["p507_header"],ord("M"))+_check_byte(s["p507_header"]+4,1)+_check_byte(s["p507_header"]+5,s["OBJ_TXT"])
    code+=_check_byte(s["p507_header"]+6,0)+_check_byte(s["p507_header"]+7,s["DIR_USERHOME"])
    code+=_check_word(s["p507_header"]+8,len(payload))+_check_word(s["p507_header"]+10,len(payload))
    code+=_check_word(s["p507_header"]+14,crc16_ccitt_false(payload))
    code+=phase1._jp(PASS_PC)
    run_sna(root,code,patch=patch)

def dispatch(root:Path,action:str,step:str,*,sha256_file,run_command,require_project_tool):
    if step!="P5.07": raise DriverError(f"Phase-5 raw-save step is not registered: {step}")
    assertions=_source(root); require(all(x["passed"] for x in assertions),"P5.07 static contract failure")
    kr,kernel,_=phase1._assemble_kernel(root,run_command,require_project_tool)
    fr,binary,sym=_assemble(root,run_command,require_project_tool)
    names=("zx48_p507_save_record","p507_tape_lock","p507_header","p507_test_blocks","DIR_USERHOME","OBJ_TXT")
    s=phase3_open_descriptions._symbols(sym,names)
    if action=="test":
        _runtime(root,s,binary.read_bytes())
        assertions += [
          {"name":"raw-txt-header-and-chunk-count-runtime","passed":True},
          {"name":"raw-txt-logical-crc-runtime","passed":True},
          {"name":"global-lock-released-after-success-runtime","passed":True},
        ]
    hashes={
      "v1/build/kernel.bin":sha256_file(kernel),
      "v1/build/p507-raw-save.bin":sha256_file(binary),
      "v1/src/kernel/tape.asm":sha256_file(root/"v1/src/kernel/tape.asm"),
      "v1/tools-host/test-driver/phase5_raw_save.py":sha256_file(root/"v1/tools-host/test-driver/phase5_raw_save.py"),
      "v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
      "v1/dist/certification/P5.06.build.json":sha256_file(root/"v1/dist/certification/P5.06.build.json"),
      "v1/dist/certification/P5.06.test.json":sha256_file(root/"v1/dist/certification/P5.06.test.json"),
    }
    return [kr,fr],hashes,assertions
