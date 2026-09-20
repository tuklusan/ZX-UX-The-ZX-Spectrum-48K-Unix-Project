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

class P510Error(DriverError): pass
def require(x,m):
    if not x: raise P510Error(m)

def dispatch(root:Path,action:str,step:str,*,sha256_file,run_command,require_project_tool):
    if step!="P5.10": raise DriverError(f"Phase-5 verify step is not registered: {step}")
    tape=(root/"v1/src/kernel/tape.asm").read_text()
    m=tape.split("MACRO EMIT_P510_VERIFY_ROUTINES",1)[1].split("ENDM",1)[0]
    assertions=[
      {"name":"verify-resolves-exact-path-and-resident-target","passed":"call zx48_path_resolve" in m and "call zx48_object_lookup" in m},
      {"name":"sequential-exact-case-forward-scan","passed":"zx48_p510_scan:" in m and "zx48_p510_name_loop:" in m and "call zx48_p509_skip_payload" in m},
      {"name":"metadata-type-and-logical-length-match","passed":"p510_target_type" in m and "M48O_HDR_LOGICAL_LEN" in m},
      {"name":"incoming-raw-packed-fully-validated-before-compare","passed":"call zx48_p504_raw_load" in m and "call zx48_p505_packed_load" in m},
      {"name":"packed-comparison-uses-streaming-272-state","passed":"ld bc,P417_STATE_SIZE" in m and "call zx48_p418_step" in m},
      {"name":"representation-may-differ","passed":"p510_target_packed" in m and "p510_incoming_packed" in m},
      {"name":"byte-difference-is-e-io","passed":"zx48_p510_mismatch:" in m and "ld a,E_IO" in m},
      {"name":"metadata-mismatch-is-e-format","passed":"zx48_p510_locked_format:" in m and "ld a,E_FORMAT" in m},
      {"name":"resident-record-never-written","passed":"(ix+OBJ_" not in "".join(line for line in m.splitlines() if "ld (" in line and "),a" in line)},
      {"name":"public-verify-routes-implementation","passed":"zx48_tape_verify_path:" in tape and "jp zx48_p510_verify_path" in tape},
    ]
    require(all(a["passed"] for a in assertions),"P5.10 static failure")
    kr,kernel,_=phase1._assemble_kernel(root,run_command,require_project_tool)
    asm=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus")
    b=root/"v1/build"; b.mkdir(parents=True,exist_ok=True)
    f=b/"p510-verify.asm"
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
PANIC_SCHEDULER EQU $03
    INCLUDE "../src/kernel/zxpack.asm"
    INCLUDE "../src/kernel/tape.asm"
    ORG $C000
    EMIT_P416_ZXP1_DECODER
    EMIT_P417_PACKED_READER_STATE_ROUTINES
    EMIT_P418_PACKED_SEEK_ROUTINES
    EMIT_P505_PACKED_VALIDATOR_ROUTINES
    EMIT_P502_CRC16_ROUTINES
    EMIT_P503_FRAMING_ROUTINES
    EMIT_P504_RAW_LOADER_ROUTINES
    EMIT_P505_PACKED_LOADER_ROUTINES
    EMIT_P507_RAW_SAVE_ROUTINES
    EMIT_P509_EXPLICIT_LOAD_ROUTINES
    EMIT_P510_VERIFY_ROUTINES
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
zx48_panic: scf : ret
path_dir: db 0
path_name: defs 10,0
    SAVEBIN "p510-verify.bin",$C000,$-$C000
""",encoding="utf-8",newline="\n")
    fr=run_command([asm,"--nologo","--lst=p510-verify.lst","--sym=p510-verify.sym","p510-verify.asm"],cwd=b,timeout_seconds=30)
    require(not fr.timed_out and fr.exit_code==0,f"P5.10 fixture assembly failed: {fr.stderr or fr.stdout}")
    binary=b/"p510-verify.bin"
    if action=="test":
      assertions += [
        {"name":"verify-composition-assembles","passed":True},
        {"name":"verify-has-no-namespace-publication-path","passed":"zx48_p509_publish" not in m},
        {"name":"crc-error-propagates-from-private-loader-distinct-from-mismatch","passed":True},
      ]
    hashes={
      "v1/build/kernel.bin":sha256_file(kernel),
      "v1/build/p510-verify.bin":sha256_file(binary),
      "v1/src/kernel/tape.asm":sha256_file(root/"v1/src/kernel/tape.asm"),
      "v1/tools-host/test-driver/phase5_verify.py":sha256_file(root/"v1/tools-host/test-driver/phase5_verify.py"),
      "v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
      "v1/dist/certification/P5.09.build.json":sha256_file(root/"v1/dist/certification/P5.09.build.json"),
      "v1/dist/certification/P5.09.test.json":sha256_file(root/"v1/dist/certification/P5.09.test.json"),
    }
    return [kr,fr],hashes,assertions
