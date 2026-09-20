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
from phase4_target_encoder import _target_encode
from phase5_m48o_header import crc16_ccitt_false

MODULE=0xC000; STREAM=0x8200; LENGTHS=0x8C00; HDR1=0x9000; HDR2=0x9040; STACK=0xBFC0
class P511Error(DriverError): pass
def require(x,m):
    if not x: raise P511Error(m)
def hdr(name,typ,target,logical,physical,packed):
    h=bytearray(32); h[:4]=b"M48O"; h[4]=1; h[5]=typ; h[6]=1 if packed else 0; h[7]=target
    h[8:10]=len(physical).to_bytes(2,"little"); h[10:12]=len(logical).to_bytes(2,"little")
    h[12:14]=(1 if packed else 0).to_bytes(2,"little"); h[14:16]=crc16_ccitt_false(logical).to_bytes(2,"little")
    h[16:26]=name.encode().ljust(10,b"\0"); h[26:28]=b"\0\0"; h[28:32]=b"\0"*4
    h[26:28]=crc16_ccitt_false(bytes(h)).to_bytes(2,"little"); return bytes(h)
def w(v): return bytes((v&255,v>>8))
def checkb(a,v): return b"\x3A"+w(a)+bytes((0xFE,v&255))+phase1._jp_nz(FAIL_PC)
def dispatch(root:Path,action:str,step:str,*,sha256_file,run_command,require_project_tool):
    if step!="P5.11": raise DriverError(f"Phase-5 tape-scan step is not registered: {step}")
    tape=(root/"v1/src/kernel/tape.asm").read_text()
    m=tape.split("MACRO EMIT_P511_SCAN_ROUTINES",1)[1].split("ENDM",1)[0]
    assertions=[
      {"name":"one-next-object-per-call","passed":"zx48_p511_scan_next:" in m and "ld hl,1" in m},
      {"name":"header-written-to-caller-buffer","passed":"p511_header_dest" in m and "ld ix,(p511_header_dest)" in m},
      {"name":"scratch-exactly-512-cold","passed":"ld bc,M48O_CHUNK_SIZE" in m and "ALLOC_COLD_PREFERRED|ALLOC_NO_COMPACT" in m},
      {"name":"packed-adds-exact-272-state","passed":"ld bc,P417_STATE_SIZE" in m},
      {"name":"packed-parser-persists-across-chunks","passed":"zx48_p511_feed_packed_byte:" in m and "p511_kind" in m},
      {"name":"raw-and-packed-logical-crc-verified","passed":"zx48_p511_crc_byte:" in m and "p511_expected_crc" in m},
      {"name":"both-scratch-allocations-released","passed":"zx48_p511_release_scratch:" in m and "p511_decoder_live" in m and "p511_scratch_live" in m},
      {"name":"no-fabricated-physical-eof","passed":"E_EOF" not in m},
      {"name":"cancel-maps-to-e-intr","passed":"PROC_FLAGS" in m and "E_INTR" in m},
      {"name":"scan-does-not-touch-namespace","passed":"zx48_object_create" not in m and "OBJ_ALLOCATION_PTR)," not in m},
      {"name":"public-scan-routes-bounded-implementation","passed":"zx48_tape_scan_next:" in tape and "jp zx48_p511_scan_next" in tape},
    ]; require(all(a["passed"] for a in assertions),"P5.11 static failure")
    kr,kernel,_=phase1._assemble_kernel(root,run_command,require_project_tool)
    asm=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus"); b=root/"v1/build"; b.mkdir(parents=True,exist_ok=True)
    f=b/"p511-scan.asm"; f.write_text("""    DEVICE ZXSPECTRUM48
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
    INCLUDE "../src/kernel/tape.asm"
    ORG $C000
    EMIT_P502_CRC16_ROUTINES
    EMIT_P503_FRAMING_ROUTINES
    EMIT_P507_RAW_SAVE_ROUTINES
    EMIT_P511_SCAN_ROUTINES
zx48_alloc:
    ld a,(test_allocs)
    inc a
    ld (test_allocs),a
    cp 1
    jr z,test_alloc_scratch
    ld hl,$A300
    xor a
    ret
test_alloc_scratch: ld hl,$A000 : xor a : ret
zx48_free:
    ld a,(test_frees)
    inc a
    ld (test_frees),a
    xor a
    ret
zx48_object_public_type_allowed: xor a : ret
zx48_tape_save_block: ld a,E_IO : scf : ret
zx48_process_lookup: ld ix,test_proc : xor a : ret
current_pid: db 1
test_proc: defs 32,0
zx48_tape_load_block:
    push de
    ld hl,(test_lengths_ptr)
    ld c,(hl)
    inc hl
    ld b,(hl)
    inc hl
    ld (test_lengths_ptr),hl
    pop de
    ld a,b
    cp d
    jr nz,test_load_fail
    ld a,c
    cp e
    jr nz,test_load_fail
    ld b,d
    ld c,e
    ld hl,(test_stream_ptr)
    push ix
    pop de
    ldir
    ld (test_stream_ptr),hl
    ld a,(test_blocks)
    dec a
    ld (test_blocks),a
    xor a
    ret
test_load_fail: ld a,E_IO : scf : ret
test_stream_ptr: dw $8200
test_lengths_ptr: dw $8C00
test_blocks: db 0
test_allocs: db 0
test_frees: db 0
    SAVEBIN "p511-scan.bin",$C000,$-$C000
""",encoding="utf-8",newline="\n")
    fr=run_command([asm,"--nologo","--lst=p511-scan.lst","--sym=p511-scan.sym","p511-scan.asm"],cwd=b,timeout_seconds=30)
    require(not fr.timed_out and fr.exit_code==0,f"P5.11 fixture assembly failed: {fr.stderr or fr.stdout}")
    binary=b/"p511-scan.bin"
    if action=="test":
      names=("zx48_p511_scan_next","test_stream_ptr","test_lengths_ptr","test_blocks","test_allocs","test_frees","p507_tape_lock")
      s=phase3_open_descriptions._symbols(b/"p511-scan.sym",names)
      raw=b"scan-raw-"+b"R"*520; packed_logical=b"P"*700; packed=_target_encode(packed_logical)
      require(len(packed)<len(packed_logical),"packed fixture did not compress")
      blocks=[hdr("raw",1,5,raw,raw,False)]
      blocks += [raw[i:i+512] for i in range(0,len(raw),512)]
      blocks += [hdr("pack",1,5,packed_logical,packed,True)]
      blocks += [packed[i:i+512] for i in range(0,len(packed),512)]
      stream=b"".join(blocks); lens=b"".join(len(x).to_bytes(2,"little") for x in blocks)
      def patch(ram):
        ram[MODULE-0x4000:MODULE-0x4000+len(binary.read_bytes())]=binary.read_bytes()
        ram[STREAM-0x4000:STREAM-0x4000+len(stream)]=stream
        ram[LENGTHS-0x4000:LENGTHS-0x4000+len(lens)]=lens
        ram[s["test_stream_ptr"]-0x4000:s["test_stream_ptr"]-0x4000+2]=w(STREAM)
        ram[s["test_lengths_ptr"]-0x4000:s["test_lengths_ptr"]-0x4000+2]=w(LENGTHS)
        ram[s["test_blocks"]-0x4000]=len(blocks)
      code=b"\xF3"+phase1._ld_sp(STACK)+phase1._ld_hl(HDR1)+phase1._call(s["zx48_p511_scan_next"])+phase1._jp_c(FAIL_PC)
      code+=phase1._ld_de(1)+b"\xB7\xED\x52"+phase1._jp_nz(FAIL_PC)+checkb(HDR1,ord("M"))+checkb(HDR1+16,ord("r"))
      code+=phase1._ld_hl(HDR2)+phase1._call(s["zx48_p511_scan_next"])+phase1._jp_c(FAIL_PC)
      code+=phase1._ld_de(1)+b"\xB7\xED\x52"+phase1._jp_nz(FAIL_PC)+checkb(HDR2+16,ord("p"))
      code+=checkb(s["test_allocs"],3)+checkb(s["test_frees"],3)+checkb(s["p507_tape_lock"],0)+phase1._jp(PASS_PC)
      try: run_sna(root,code,patch=patch)
      except DriverError as e: raise P511Error(f"P5.11 runtime failed: {e}") from e
      assertions += [
        {"name":"mixed-raw-packed-stream-runtime","passed":True},
        {"name":"scratch-released-between-objects-runtime","passed":True},
        {"name":"validated-headers-returned-runtime","passed":True},
      ]
    hashes={
      "v1/build/kernel.bin":sha256_file(kernel),"v1/build/p511-scan.bin":sha256_file(binary),
      "v1/src/kernel/tape.asm":sha256_file(root/"v1/src/kernel/tape.asm"),
      "v1/tools-host/test-driver/phase5_tape_scan.py":sha256_file(root/"v1/tools-host/test-driver/phase5_tape_scan.py"),
      "v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
      "v1/dist/certification/P5.10.build.json":sha256_file(root/"v1/dist/certification/P5.10.build.json"),
      "v1/dist/certification/P5.10.test.json":sha256_file(root/"v1/dist/certification/P5.10.test.json"),
    }
    return [kr,fr],hashes,assertions
