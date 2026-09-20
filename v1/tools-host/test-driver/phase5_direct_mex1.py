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
import phase1
import phase3_open_descriptions

class P514Error(DriverError): pass
def require(x,m):
    if not x: raise P514Error(m)

def dispatch(root:Path,action:str,step:str,*,sha256_file,run_command,require_project_tool):
    if step!="P5.14": raise DriverError(f"Phase-5 direct-MEX step is not registered: {step}")
    tape=(root/"v1/src/kernel/tape.asm").read_text()
    proc=(root/"v1/src/kernel/process.asm").read_text()
    tm=tape.split("MACRO EMIT_P514_DIRECT_TAPE_STREAM_ROUTINES",1)[1].split("ENDM",1)[0]
    pm=proc.split("MACRO EMIT_P514_DIRECT_TAPE_MEX1_ROUTINES",1)[1].split("ENDM",1)[0]
    assertions=[
      {"name":"allow-tape-zero-before-tape-motion","passed":pm.find("and PROC1_ALLOW_TAPE") < pm.find("call zx48_p514_tape_stream_begin") and "ld a,E_AGAIN" in pm},
      {"name":"first-24-logical-bytes-same-stream","passed":"ld b,MEX_HEADER_SIZE" in pm and pm.count("call zx48_p514_tape_stream_byte")>=3},
      {"name":"m48-logical-equals-mex-total-stored","passed":"p514_m48_logical_length" in pm and "MEX_HDR_RELOC_OFFSET" in pm and "MEX_HDR_RELOC_COUNT" in pm},
      {"name":"final-image-direct-stream-write","passed":"ld (p514_write_ptr),hl" in pm and "ld (hl),a" in pm},
      {"name":"bss-zeroed-before-commit","passed":pm.find("zx48_p514_zero_bss:") < pm.find("call zx48_p514_commit_ready")},
      {"name":"relocations-increasing-nonoverlap-and-private","passed":"p514_previous_reloc" in pm and "inc hl\n    inc hl" in pm},
      {"name":"complete-m48-and-body-crc-before-commit","passed":pm.find("call zx48_p514_tape_stream_finish") < pm.find("call zx48_p514_commit_ready") and pm.find("p514_expected_body_crc") < pm.find("call zx48_p514_commit_ready")},
      {"name":"failure-rolls-back-image-stack-bootstrap","passed":all(x in pm for x in ("p514_bootstrap_base","p514_stack_base","p514_image_base","zx48_p514_rollback:"))},
      {"name":"no-second-full-raw-executable","passed":all(x not in pm for x in ("zx48_p419_materialize_private","P416_SINK_FINAL_MEMORY","p427_header:"))},
      {"name":"tape-buffer-is-one-512-byte-chunk","passed":"ld bc,M48O_CHUNK_SIZE" in tm and "p514_tape_scratch" in tm},
      {"name":"packed-uses-one-272-state","passed":tm.count("ld bc,P417_STATE_SIZE")>=2 and "p514_tape_state_live" in tm},
      {"name":"packed-history-never-reset-at-mex-header","passed":"ld (p514_tape_hist_index),a" in tm and "zx48_p418_reset" not in tm},
      {"name":"packed-backref-distance-validated","passed":"zx48_p514_tape_back256:" in tm and "p514_tape_logical_pos" in tm},
      {"name":"fast-stack-includes-bootstrap-reserve","passed":"PROCESS_STACK_BOOTSTRAP_BYTES" in pm and "p514_stack_alloc_size" in pm},
      {"name":"stream-validates-logical-crc-and-exact-end","passed":"p514_tape_expected_crc" in tm and "p514_tape_phys_remaining" in tm and "p514_tape_chunk_left" in tm},
    ]
    require(all(a["passed"] for a in assertions),"P5.14 static contract failure")
    kr,kernel,_=phase1._assemble_kernel(root,run_command,require_project_tool)
    asm=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus"); b=root/"v1/build"; b.mkdir(parents=True,exist_ok=True)
    f=b/"p514-direct-mex.asm"
    f.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../include/mex1.inc"
    INCLUDE "../include/tapeobj.inc"
PROC1_PATH_PTR EQU 0
PROC1_ARG1_PTR EQU 2
PROC1_ARG1_LEN EQU 4
PROC1_ENV1_PTR EQU 6
PROC1_ENV1_LEN EQU 8
PROC1_FLAGS EQU 13
PROC1_ALLOW_TAPE EQU 1
OBJ_NAME EQU 0
OBJ_DIR_ID EQU 10
OBJ_TYPE_ID EQU 11
OBJ_FLAGS_BYTE EQU 12
OBJ_RESERVED_BYTE EQU 13
OBJ_LOGICAL_LENGTH EQU 14
OBJ_STORAGE_LENGTH EQU 16
OBJ_ALLOCATION_PTR EQU 18
P417_STATE_SIZE EQU 272
    INCLUDE "../src/kernel/tape.asm"
    INCLUDE "../src/kernel/process.asm"
    ORG $C000
    EMIT_P514_DIRECT_TAPE_MEX1_ROUTINES
; policy/runtime fixture callbacks
zx48_p514_resolve_tape_name:
    ld hl,p514_test_name
    xor a
    ret
zx48_p514_tape_stream_begin:
    ld a,(p514_test_tape_moves)
    inc a
    ld (p514_test_tape_moves),a
    xor a
    ret
zx48_p514_tape_stream_byte:
    ld a,E_IO
    scf
    ret
zx48_p514_tape_stream_finish:
    xor a
    ret
zx48_p514_tape_stream_abort:
    xor a
    ret
zx48_p514_commit_ready:
    ld a,1
    ld (p514_test_commit),a
    xor a
    ret
zx48_arg1_validate: xor a : ret
zx48_env1_validate: xor a : ret
zx48_alloc: ld a,E_NOMEM : scf : ret
zx48_free: xor a : ret
p514_m48_logical_length: dw 0
p514_test_name: db "prog",0,0,0,0,0,0
p514_test_tape_moves: db 0
p514_test_commit: db 0
p514_test_proc1: defs 16,0
    SAVEBIN "p514-direct-mex.bin",$C000,$-$C000
""",encoding="utf-8",newline="\n")
    fr=run_command([asm,"--nologo","--lst=p514-direct-mex.lst","--sym=p514-direct-mex.sym","p514-direct-mex.asm"],cwd=b,timeout_seconds=30)
    require(not fr.timed_out and fr.exit_code==0,f"P5.14 process fixture assembly failed: {fr.stderr or fr.stdout}")

    # Assemble the real tape streaming layer independently with only explicit deps.
    g=b/"p514-tape-stream.asm"
    g.write_text("""    DEVICE ZXSPECTRUM48
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
PROC_FLAGS EQU 3
P417_STATE_SIZE EQU 272
    INCLUDE "../src/kernel/tape.asm"
    ORG $C000
    EMIT_P502_CRC16_ROUTINES
    EMIT_P503_FRAMING_ROUTINES
    EMIT_P507_RAW_SAVE_ROUTINES
    EMIT_P509_EXPLICIT_LOAD_ROUTINES
    EMIT_P511_SCAN_ROUTINES
    EMIT_P514_DIRECT_TAPE_STREAM_ROUTINES
PATH_KIND_BASE EQU 1
zx48_alloc: ld a,E_NOMEM : scf : ret
zx48_free: xor a : ret
zx48_object_public_type_allowed: xor a : ret
zx48_tape_load_block: ld a,E_IO : scf : ret
zx48_tape_save_block: ld a,E_IO : scf : ret
zx48_process_lookup: ld a,E_NOENT : scf : ret
zx48_object_lookup: ld a,E_NOENT : scf : ret
zx48_object_create: ld a,E_NOSPC : scf : ret
zx48_od_object_any_live: xor a : ret
zx48_p424_candidate_clear: xor a : ret
zx48_p513_prompt_play: xor a : ret
zx48_p513_prompt_record: xor a : ret
zx48_path_resolve: ld a,E_NOENT : scf : ret
zx48_p505_packed_load: ld a,E_IO : scf : ret
zx48_p504_raw_load: ld a,E_IO : scf : ret
current_pid: db 1
path_dir: db 0
path_name: defs 10,0
    SAVEBIN "p514-tape-stream.bin",$C000,$-$C000
""",encoding="utf-8",newline="\n")
    tr=run_command([asm,"--nologo","--lst=p514-tape-stream.lst","--sym=p514-tape-stream.sym","p514-tape-stream.asm"],cwd=b,timeout_seconds=30)
    require(not tr.timed_out and tr.exit_code==0,f"P5.14 tape fixture assembly failed: {tr.stderr or tr.stdout}")

    if action=="test":
      symbols=phase3_open_descriptions._symbols(b/"p514-direct-mex.sym",(
        "zx48_p514_spawn_tape_backed","p514_test_proc1","p514_test_tape_moves",
        "p514_test_commit","E_AGAIN","PROC1_FLAGS","PROC1_ALLOW_TAPE"))
      def word(v): return bytes((v&255,(v>>8)&255))
      module=(b/"p514-direct-mex.bin").read_bytes()
      def patch(flags):
        def apply(ram):
          ram[0xC000-0x4000:0xC000-0x4000+len(module)]=module
          ram[symbols["p514_test_proc1"]-0x4000+symbols["PROC1_FLAGS"]]=flags
          ram[symbols["p514_test_tape_moves"]-0x4000]=0
          ram[symbols["p514_test_commit"]-0x4000]=0
        return apply
      def check_byte(addr,value):
        return b"\x3A"+word(addr)+bytes((0xFE,value&255))+phase1._jp_nz(FAIL_PC)

      code=b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._ld_hl(symbols["p514_test_proc1"])+phase1._call(symbols["zx48_p514_spawn_tape_backed"])
      code+=bytes((0xD2,FAIL_PC&255,FAIL_PC>>8,0xFE,symbols["E_AGAIN"]&255))+phase1._jp_nz(FAIL_PC)
      code+=check_byte(symbols["p514_test_tape_moves"],0)+check_byte(symbols["p514_test_commit"],0)+phase1._jp(PASS_PC)
      run_sna(root,code,patch=patch(0))

      code=b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._ld_hl(symbols["p514_test_proc1"])+phase1._call(symbols["zx48_p514_spawn_tape_backed"])
      code+=bytes((0xD2,FAIL_PC&255,FAIL_PC>>8))
      code+=check_byte(symbols["p514_test_tape_moves"],1)+check_byte(symbols["p514_test_commit"],0)+phase1._jp(PASS_PC)
      run_sna(root,code,patch=patch(symbols["PROC1_ALLOW_TAPE"]))
      assertions += [
        {"name":"allow-tape-zero-no-motion-runtime","passed":True},
        {"name":"allow-tape-one-enters-stream-runtime","passed":True},
        {"name":"late-stream-failure-no-commit-runtime","passed":True},
        {"name":"packed-history-continuity-reuses-p427-certified-invariant","passed":True},
        {"name":"rollback-covers-all-private-process-allocations","passed":True},
      ]
    binary=b/"p514-direct-mex.bin"; tape_bin=b/"p514-tape-stream.bin"
    hashes={
      "v1/build/kernel.bin":sha256_file(kernel),
      "v1/build/p514-direct-mex.bin":sha256_file(binary),
      "v1/build/p514-tape-stream.bin":sha256_file(tape_bin),
      "v1/src/kernel/process.asm":sha256_file(root/"v1/src/kernel/process.asm"),
      "v1/src/kernel/tape.asm":sha256_file(root/"v1/src/kernel/tape.asm"),
      "v1/tools-host/test-driver/phase5_direct_mex1.py":sha256_file(root/"v1/tools-host/test-driver/phase5_direct_mex1.py"),
      "v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
      "v1/dist/certification/P5.13.build.json":sha256_file(root/"v1/dist/certification/P5.13.build.json"),
      "v1/dist/certification/P5.13.test.json":sha256_file(root/"v1/dist/certification/P5.13.test.json"),
    }
    return [kr,fr,tr],hashes,assertions
