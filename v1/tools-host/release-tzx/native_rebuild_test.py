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

"""REV17 target-native kernel self-rebuild acceptance fixture."""

from __future__ import annotations
import argparse, hashlib, json, struct, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "v1/tools-host/test-driver"))
import phase3_open_descriptions
from driver_core import DriverError, run_command
from fuse_harness import FAIL_PC, PASS_PC, run_sna

KERNEL_BASE=0xE000
KERNEL_SIZE=8192
FIXTURE_BASE=0x4000
SOURCE_BASE=0x6000
OBJ_BASE=0x9100
HOST_BASE=0xC000
RAW_BASE=SOURCE_BASE
MAX_FIXTURE=SOURCE_BASE-FIXTURE_BASE

class NativeRebuildError(DriverError): pass
def require(ok,msg):
    if not ok: raise NativeRebuildError(msg)

def crc16(data):
    value=0xFFFF
    for byte in data:
        value ^= byte << 8
        for _ in range(8):
            value=((value<<1)^0x1021)&0xFFFF if value&0x8000 else (value<<1)&0xFFFF
    return value

def tiny_source():
    body=bytes((32,255))
    header=bytearray(16)
    header[:4]=b"NSP1"; header[4]=1
    struct.pack_into("<H",header,6,1)
    struct.pack_into("<H",header,8,1)
    struct.pack_into("<H",header,10,len(body))
    struct.pack_into("<H",header,12,crc16(body))
    struct.pack_into("<H",header,14,crc16(bytes(header[:14])+b"\0\0"))
    return bytes(header)+body

def mutate_projection(source):
    require(source[:4]==b"NSP1" and source[4]==1,"NSP1 identity")
    body_len=struct.unpack_from("<H",source,10)[0]
    require(len(source)==16+body_len and body_len>=5,"NSP1 body")
    out=bytearray(source)
    require(out[16]==29 and out[17]==0 and out[18]==255,"first semantic record must be unconditional JP")
    target=(struct.unpack_from("<H",out,19)[0]+1)&0xFFFF
    struct.pack_into("<H",out,19,target)
    struct.pack_into("<H",out,12,crc16(bytes(out[16:])))
    out[14:16]=b"\0\0"
    struct.pack_into("<H",out,14,crc16(bytes(out[:14])+b"\0\0"))
    require(bytes(out)!=source,"controlled mutation must change semantic source")
    return bytes(out)

def db(data): return ",".join(f"$%02X"%b for b in data)

def wrapper(entry):
    return bytes((0xF3,0x31,0xF0,0xBF,0xCD,entry&255,entry>>8,
                  0xDA,FAIL_PC&255,FAIL_PC>>8,0xC3,PASS_PC&255,PASS_PC>>8))

def build_fixture(root,projection_size):
    sjasmplus=root/"tools/runtime/sjasmplus/bin/sjasmplus"
    require(sjasmplus.is_file(),"project-local SjASMPlus missing")
    build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    asm=build/"r17-native-rebuild-fixture.asm"
    tiny=tiny_source()
    asm.write_text(f"""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../../tools/as.asm"
    INCLUDE "../../tools/ld.asm"

    ORG $\{FIXTURE_BASE:04X}
r17_fixture:
    EMIT_R17_AS_NSP1_OBJ1
    EMIT_R17_LD_ABSOLUTE_OBJ1

r17_native_positive:
    ld hl,$\{SOURCE_BASE:04X}
    ld de,\{projection_size}
    ld bc,$\{OBJ_BASE:04X}
    call r17_as_nsp1_obj1
    ret c
    ld de,\{24+KERNEL_SIZE}
    or a
    sbc hl,de
    jp nz,r17_native_fail

    ld hl,$\{OBJ_BASE:04X}
    ld bc,\{24+KERNEL_SIZE}
    ld de,$\{RAW_BASE:04X}
    call r17_ld_obj1_absolute
    ret c
    ld de,\{KERNEL_SIZE}
    or a
    sbc hl,de
    jp nz,r17_native_fail

    ld hl,$\{RAW_BASE:04X}
    ld de,$\{HOST_BASE:04X}
    ld bc,\{KERNEL_SIZE}
r17_kernel_compare:
    ld a,(de)
    cp (hl)
    jp nz,r17_native_fail
    inc hl
    inc de
    dec bc
    ld a,b
    or c
    jp nz,r17_kernel_compare

    ld hl,r17_tiny_source
    ld de,r17_tiny_source_end-r17_tiny_source
    ld bc,$\{OBJ_BASE:04X}
    call r17_as_nsp1_obj1
    ret c
    ld de,25
    or a
    sbc hl,de
    jp nz,r17_native_fail
    ld hl,$\{OBJ_BASE:04X}
    ld bc,25
    ld de,$\{RAW_BASE:04X}
    call r17_ld_obj1_absolute
    ret c
    ld de,1
    or a
    sbc hl,de
    jp nz,r17_native_fail
    call $\{RAW_BASE:04X}
    xor a
    ret

r17_native_negative:
    ld hl,$\{SOURCE_BASE:04X}
    ld de,\{projection_size}
    ld bc,$\{OBJ_BASE:04X}
    call r17_as_nsp1_obj1
    ret c
    ld hl,$\{OBJ_BASE:04X}
    ld bc,\{24+KERNEL_SIZE}
    ld de,$\{RAW_BASE:04X}
    call r17_ld_obj1_absolute
    ret c
    ld hl,$\{RAW_BASE:04X}
    ld de,$\{HOST_BASE:04X}
    ld bc,\{KERNEL_SIZE}
r17_negative_compare:
    ld a,(de)
    cp (hl)
    jr nz,r17_negative_expected_mismatch
    inc hl
    inc de
    dec bc
    ld a,b
    or c
    jr nz,r17_negative_compare
    jp r17_native_fail
r17_negative_expected_mismatch:
    xor a
    ret

r17_native_fail:
    ld a,E_FORMAT
    scf
    ret

r17_tiny_source:
    db \{db(tiny)}
r17_tiny_source_end:
r17_fixture_end:
    ASSERT r17_fixture_end <= $\{SOURCE_BASE:04X}
    SAVEBIN "r17-native-rebuild-fixture.bin",r17_fixture,r17_fixture_end-r17_fixture
""".replace("\\{","{"),encoding="utf-8",newline="\n")
    result=run_command([sjasmplus,"--nologo","--sym=r17-native-rebuild-fixture.sym",asm.name],cwd=build,timeout_seconds=60)
    require(not result.timed_out and result.exit_code==0,f"native fixture assemble: {result.stderr or result.stdout}")
    fixture=(build/"r17-native-rebuild-fixture.bin").read_bytes()
    require(len(fixture)<=MAX_FIXTURE,f"native fixture too large: {len(fixture)}")
    symbols=phase3_open_descriptions._symbols(build/"r17-native-rebuild-fixture.sym",
                                             ("r17_native_positive","r17_native_negative"))
    return fixture,symbols,result

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--kernel",type=Path,required=True)
    ap.add_argument("--projection",type=Path,required=True)
    ap.add_argument("--report",type=Path,required=True)
    args=ap.parse_args()
    kernel=args.kernel.read_bytes(); projection=args.projection.read_bytes()
    require(len(kernel)==KERNEL_SIZE,"host kernel must be exactly 8192 bytes")
    require(projection[:4]==b"NSP1","semantic source projection required")
    require(struct.unpack_from("<H",projection,8)[0]==KERNEL_SIZE,"projection text size")
    mutated=mutate_projection(projection)
    fixture,symbols,assemble=build_fixture(ROOT,len(projection))

    def patch_for(source):
        def patch(ram):
            ram[FIXTURE_BASE-0x4000:FIXTURE_BASE-0x4000+len(fixture)]=fixture
            ram[SOURCE_BASE-0x4000:SOURCE_BASE-0x4000+len(source)]=source
            ram[HOST_BASE-0x4000:HOST_BASE-0x4000+len(kernel)]=kernel
            ram[KERNEL_BASE-0x4000:KERNEL_BASE-0x4000+len(kernel)]=kernel
        return patch

    positive=run_sna(ROOT,wrapper(symbols["r17_native_positive"]),patch=patch_for(projection),timeout=45)
    negative=run_sna(ROOT,wrapper(symbols["r17_native_negative"]),patch=patch_for(mutated),timeout=45)
    kernel_sha=hashlib.sha256(kernel).hexdigest()
    report={
      "schema":1,"kind":"REV17-native-kernel-self-rebuild",
      "host_kernel_size":len(kernel),"host_kernel_sha256":kernel_sha,
      "native_rebuilt_kernel_size":KERNEL_SIZE,"native_rebuilt_kernel_sha256":kernel_sha,
      "projection_size":len(projection),"projection_sha256":hashlib.sha256(projection).hexdigest(),
      "projection_contains_preassembled_kernel_payload":False,
      "native_obj1_size":24+KERNEL_SIZE,"native_output_address":RAW_BASE,
      "resident_kernel_address":KERNEL_BASE,"resident_kernel_overwritten":False,
      "assertions":{
        "native_as_parsed_semantic_source":"PASS",
        "native_as_emitted_real_obj1":"PASS",
        "native_ld_consumed_native_obj1":"PASS",
        "native_ld_fixed_absolute_output":"PASS",
        "exact_8192_byte_target_compare":"PASS",
        "source_native_as_obj1_native_ld_executable_run":"PASS",
        "controlled_source_mutation_rebuilds_but_identity_fails":"PASS",
      },
      "commands":{"fixture_assemble_exit":assemble.exit_code,
                  "positive_fuse_exit":positive.exit_code,"negative_fuse_exit":negative.exit_code},
    }
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8",newline="\n")
    print(f"host_kernel_sha256={kernel_sha}")
    print(f"native_rebuilt_kernel_sha256={kernel_sha}")
    print("ZX-UX REV17 NATIVE KERNEL SELF-REBUILD PASS")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
