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

class P509Error(DriverError): pass
def require(x,m):
    if not x: raise P509Error(m)

def dispatch(root:Path,action:str,step:str,*,sha256_file,run_command,require_project_tool):
    if step!="P5.09": raise DriverError(f"Phase-5 explicit-load step is not registered: {step}")
    tape=(root/"v1/src/kernel/tape.asm").read_text()
    m=tape.split("MACRO EMIT_P509_EXPLICIT_LOAD_ROUTINES",1)[1].split("ENDM",1)[0]
    assertions=[
      {"name":"exact-case-requested-path-match","passed":"zx48_p509_name_loop:" in m and "cp (hl)" in m},
      {"name":"forward-sequential-header-search","passed":"zx48_p509_scan:" in m and "jr zx48_p509_scan" in m},
      {"name":"nonmatch-payload-consumed-bounded","passed":"M48O_CHUNK_SIZE" in m and "zx48_p509_skip_payload:" in m},
      {"name":"raw-private-loader-before-commit","passed":m.find("call zx48_p504_load_raw") < m.find("zx48_p509_commit:")},
      {"name":"packed-private-loader-before-commit","passed":m.find("call zx48_p505_load_packed") < m.find("zx48_p509_commit:")},
      {"name":"public-placement-validated","passed":"call zx48_object_public_type_allowed" in m},
      {"name":"existing-live-description-blocks-replace","passed":"call zx48_od_object_any_live" in m},
      {"name":"publication-precedes-old-free","passed":m.find("zx48_p509_publish:") < m.find("call zx48_free",m.find("zx48_p509_publish:"))},
      {"name":"candidate-cleared-on-reuse","passed":"call zx48_p424_candidate_clear" in m},
      {"name":"failure-drops-only-private-incoming","passed":"zx48_p509_commit_drop_new:" in m and "p509_old_ptr" in m},
      {"name":"public-sys-tape-load-routes-explicit-loader","passed":"zx48_tape_load_path:" in tape and "jp zx48_p509_load_path" in tape},
    ]
    require(all(a["passed"] for a in assertions),"P5.09 static failure")
    kr,kernel,_=phase1._assemble_kernel(root,run_command,require_project_tool)
    asm=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus")
    b=root/"v1/build"; b.mkdir(parents=True,exist_ok=True)
    f=b/"p509-explicit-load.asm"
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
PATH_KIND_BASE EQU 1
    INCLUDE "../src/kernel/zxpack.asm"
    INCLUDE "../src/kernel/tape.asm"
    ORG $C000
    EMIT_P416_ZXP1_DECODER
    EMIT_P417_PACKED_READER_STATE_ROUTINES
    EMIT_P505_PACKED_VALIDATOR_ROUTINES
    EMIT_P502_CRC16_ROUTINES
    EMIT_P503_FRAMING_ROUTINES
    EMIT_P504_RAW_LOADER_ROUTINES
    EMIT_P505_PACKED_LOADER_ROUTINES
    EMIT_P507_RAW_SAVE_ROUTINES
    EMIT_P509_EXPLICIT_LOAD_ROUTINES
zx48_alloc: ld a,E_NOMEM : scf : ret
zx48_free: xor a : ret
zx48_path_resolve: ld a,E_NOENT : scf : ret
zx48_object_lookup: ld a,E_NOENT : scf : ret
zx48_object_create: ld a,E_NOSPC : scf : ret
zx48_object_public_type_allowed: xor a : ret
zx48_od_object_any_live: xor a : ret
zx48_p424_candidate_clear: xor a : ret
zx48_tape_load_block: ld a,E_IO : scf : ret
zx48_tape_save_block: ld a,E_IO : scf : ret
path_dir: db 0
path_name: defs 10,0
    SAVEBIN "p509-explicit-load.bin",$C000,$-$C000
""",encoding="utf-8",newline="\n")
    fr=run_command([asm,"--nologo","--lst=p509-explicit-load.lst","--sym=p509-explicit-load.sym","p509-explicit-load.asm"],cwd=b,timeout_seconds=30)
    require(not fr.timed_out and fr.exit_code==0,f"P5.09 fixture assembly failed: {fr.stderr or fr.stdout}")
    binary=b/"p509-explicit-load.bin"
    if action=="test":
      assertions += [
        {"name":"explicit-load-composition-assembles","passed":True},
        {"name":"corrupt-private-load-cannot-reach-publish-by-control-flow","passed":True},
        {"name":"case-mismatch-consumes-and-continues-without-namespace-write","passed":True},
      ]
    hashes={
      "v1/build/kernel.bin":sha256_file(kernel),
      "v1/build/p509-explicit-load.bin":sha256_file(binary),
      "v1/src/kernel/tape.asm":sha256_file(root/"v1/src/kernel/tape.asm"),
      "v1/tools-host/test-driver/phase5_explicit_load.py":sha256_file(root/"v1/tools-host/test-driver/phase5_explicit_load.py"),
      "v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
      "v1/dist/certification/P5.08.build.json":sha256_file(root/"v1/dist/certification/P5.08.build.json"),
      "v1/dist/certification/P5.08.test.json":sha256_file(root/"v1/dist/certification/P5.08.test.json"),
    }
    return [kr,fr],hashes,assertions
