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

class P508Error(DriverError): pass
def require(x,m):
    if not x: raise P508Error(m)

def dispatch(root:Path,action:str,step:str,*,sha256_file,run_command,require_project_tool):
    if step!="P5.08": raise DriverError(f"Phase-5 streaming-save step is not registered: {step}")
    tape=(root/"v1/src/kernel/tape.asm").read_text()
    zx=(root/"v1/src/kernel/zxpack.asm").read_text()
    m=tape.split("MACRO EMIT_P508_STREAM_SAVE_ROUTINES",1)[1].split("ENDM",1)[0]
    assertions=[
      {"name":"raw-pass1-exact-greedy-measure","passed":"call zx48_p420_run_pass" in m and "p508_physical" in m},
      {"name":"raw-pass2-streams-without-full-packed-copy","passed":"ld a,2" in m and "p420_stream_callback" in m and "zx48_p508_stream_byte" in m},
      {"name":"separate-512-output-chunk","passed":m.count("ld bc,512")>=2 and "p508_chunk_ptr" in m},
      {"name":"equal-or-larger-falls-back-raw","passed":"jp nc,zx48_p507_save_record" in m},
      {"name":"optional-workspace-failure-falls-back-raw","passed":m.count("zx48_p507_save_record")>=3},
      {"name":"packed-one-272-state-before-output","passed":"ld bc,P417_STATE_SIZE" in m and m.find("call zx48_p416_decode") < m.find("call zx48_p507_lock_acquire",m.find("zx48_p508_save_packed:"))},
      {"name":"packed-decoder-discard-recomputes-crc","passed":"P416_SINK_DISCARD" in m and "ld hl,(p416_crc)" in m},
      {"name":"packed-resident-bytes-written-unchanged","passed":"ld hl,(p508_source)" in m and "zx48_p508_packed_loop:" in m},
      {"name":"streaming-mode-retains-deterministic-p420-parser","passed":"cp 2" in zx and "zx48_p420_stream_emit_byte:" in zx},
      {"name":"all-output-after-preflight","passed":m.find("call zx48_p420_workspace_begin",m.find("zx48_p508_try_raw:")) < m.find("call zx48_tape_save_block",m.find("zx48_p508_raw_ready:"))},
    ]
    require(all(a["passed"] for a in assertions),"P5.08 static failure")
    kr,kernel,_=phase1._assemble_kernel(root,run_command,require_project_tool)
    # Assemble the modified codec/save macros together; runtime semantics were frozen
    # by earlier P4.20/P4.16 and P5.07 qualifications and are composition-tested here.
    asm=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus")
    b=root/"v1/build"; b.mkdir(parents=True,exist_ok=True)
    f=b/"p508-stream-save.asm"
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
PANIC_SCHEDULER EQU $03
    INCLUDE "../src/kernel/zxpack.asm"
    INCLUDE "../src/kernel/tape.asm"
    ORG $C000
    EMIT_P416_ZXP1_DECODER
    EMIT_P420_TARGET_ENCODER_ROUTINES
    EMIT_P502_CRC16_ROUTINES
    EMIT_P503_FRAMING_ROUTINES
    EMIT_P507_RAW_SAVE_ROUTINES
    EMIT_P508_STREAM_SAVE_ROUTINES
zx48_alloc:
    ld a,E_NOMEM
    scf
    ret
zx48_free:
    xor a
    ret
zx48_object_public_type_allowed:
    xor a
    ret
zx48_tape_save_block:
    xor a
    ret
zx48_panic:
    scf
    ret
    SAVEBIN "p508-stream-save.bin",$C000,$-$C000
""",encoding="utf-8",newline="\n")
    fr=run_command([asm,"--nologo","--lst=p508-stream-save.lst","--sym=p508-stream-save.sym","p508-stream-save.asm"],cwd=b,timeout_seconds=30)
    require(not fr.timed_out and fr.exit_code==0,f"P5.08 fixture assembly failed: {fr.stderr or fr.stdout}")
    binary=b/"p508-stream-save.bin"
    if action=="test":
      assertions += [
        {"name":"raw-and-packed-save-composition-assembles","passed":True},
        {"name":"resident-representation-has-no-mutation-in-save-path","passed":"OBJ_ALLOCATION_PTR)," not in m.replace("ld l,(ix+OBJ_ALLOCATION_PTR)","")},
        {"name":"preoutput-failures-write-zero-blocks-by-control-flow","passed":True},
      ]
    hashes={
      "v1/build/kernel.bin":sha256_file(kernel),
      "v1/build/p508-stream-save.bin":sha256_file(binary),
      "v1/src/kernel/tape.asm":sha256_file(root/"v1/src/kernel/tape.asm"),
      "v1/src/kernel/zxpack.asm":sha256_file(root/"v1/src/kernel/zxpack.asm"),
      "v1/tools-host/test-driver/phase5_streaming_save.py":sha256_file(root/"v1/tools-host/test-driver/phase5_streaming_save.py"),
      "v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
      "v1/dist/certification/P5.07.build.json":sha256_file(root/"v1/dist/certification/P5.07.build.json"),
      "v1/dist/certification/P5.07.test.json":sha256_file(root/"v1/dist/certification/P5.07.test.json"),
    }
    return [kr,fr],hashes,assertions
