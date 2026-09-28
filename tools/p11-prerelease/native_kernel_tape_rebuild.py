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

"""Stage-E target proof: retained source TAP -> native OBJ1 -> native kernel."""

from __future__ import annotations
import argparse, hashlib, json, re, struct, subprocess, tempfile
from pathlib import Path
import source_tap

ROOT=Path(__file__).resolve().parents[2]
FIXTURE_BASE=0x4000
FIXTURE_CODE1_END=0x5B00
FIXTURE_CODE2_BASE=0x6000
FIXTURE_CODE2_END=0x6800
STACK_TOP=0x67F0
SOURCE_BASE=0x6800
OBJ_SIZE=8216
KERNEL_SIZE=8192
OUTPUT_BASE=SOURCE_BASE+OBJ_SIZE
KERNEL_BASE=0xE000
BLOCKER_SIZE=0x0800
SNAP_STACK=0x5AF0
DUMP_MARKER=0xD17E0001
PASS_MARKER=0xD17E0002

class Error(RuntimeError): pass
def require(v,m):
    if not v: raise Error(m)
def sha(b:bytes)->str:return hashlib.sha256(b).hexdigest()

def symbols(path:Path,names:tuple[str,...])->dict[str,int]:
    text=path.read_text(encoding="utf-8",errors="replace");out={}
    for name in names:
        m=re.search(rf"^{re.escape(name)}:\s+equ\s+0x([0-9a-f]+)\s*$",text,re.I|re.M)
        require(m,f"missing fixture symbol {name}");out[name]=int(m.group(1),16)
    return out

def make_sna(entry:int,fixture:bytes,kernel:bytes)->bytes:
    ram=bytearray(0xC000)
    ram[FIXTURE_BASE-0x4000:FIXTURE_BASE-0x4000+len(fixture)]=fixture
    ram[KERNEL_BASE-0x4000:KERNEL_BASE-0x4000+len(kernel)]=kernel
    struct.pack_into("<H",ram,SNAP_STACK-0x4000,entry)
    h=bytearray(27);h[0]=0xFE;h[19]=0x04;struct.pack_into("<H",h,23,SNAP_STACK);h[25]=1
    return bytes(h)+bytes(ram)

def fixture_source(source_size:int)->str:
    tail=source_size-OBJ_SIZE
    require(tail>0 and not tail&1,"source/OBJ tail must be positive even")
    return f"""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../include/tapeobj.inc"
    INCLUDE "../src/kernel/objects.asm"
    INCLUDE "../src/kernel/rom_services.asm"
    INCLUDE "../src/kernel/tape.asm"
    INCLUDE "../../tools/as.asm"
    INCLUDE "../../tools/as_text.asm"
    INCLUDE "../../tools/ld.asm"

    ORG $4000
r17e_seg1:
    EMIT_R17_AS_NSP1_OBJ1
    EMIT_R17_AS_TEXT_OBJ1
    ASSERT $ <= $5B00

    ORG $6000
r17e_seg2:
    EMIT_R17_LD_ABSOLUTE_OBJ1
    EMIT_OBJECT_RECORD_ROUTINES
    EMIT_P502_CRC16_ROUTINES
    EMIT_P503_FRAMING_ROUTINES
    EMIT_P504_RAW_LOADER_ROUTINES

r17e_positive:
    xor a
    ld (r17e_negative_mode),a
    jp r17e_common
r17e_negative:
    ld a,1
    ld (r17e_negative_mode),a
r17e_common:
    di
    ld sp,$67F0
    ld iy,$5C3A
    xor a
    ld (r17e_alloc_phase),a
    call zx48_object_records_init

    ld hl,$E000
    ld bc,8192
    call zx48_crc16_ccitt_false
    ld (r17e_resident_crc),de

    ld ix,r17e_header
    ld de,M48O_HDR_SIZE
    ld a,M48O_ROM_DATA_FLAG
    scf
    call ROM_LD_BYTES
    jp nc,r17e_fail
    ld hl,r17e_header
    call zx48_p504_raw_load
    jp c,r17e_fail
    ld (r17e_source_ptr),hl
    ld (r17e_source_len),bc
    ld de,$6800
    push hl
    or a
    sbc hl,de
    pop hl
    jp nz,r17e_fail
    ld hl,{source_size}
    or a
    sbc hl,bc
    jp nz,r17e_fail

    ld a,(r17e_header+M48O_HDR_TYPE)
    cp OBJ_ASM
    jp nz,r17e_fail
    ld a,(r17e_header+M48O_HDR_DIRECTORY)
    cp DIR_USERHOME
    jp nz,r17e_fail
    ld hl,r17e_header+M48O_HDR_NAME
    ld de,r17e_source_name
    ld b,10
r17e_name_check:
    ld a,(de)
    cp (hl)
    jp nz,r17e_fail
    inc de
    inc hl
    djnz r17e_name_check

    call zx48_object_record_claim
    jp c,r17e_fail
    push ix
    pop de
    ld hl,r17e_source_name
    ld bc,10
    ldir
    ld (ix+OBJ_DIR_ID),DIR_USERHOME
    ld (ix+OBJ_TYPE_ID),OBJ_ASM
    xor a
    ld (ix+OBJ_FLAGS_BYTE),a
    ld (ix+OBJ_RESERVED_BYTE),a
    ld hl,{source_size}
    ld (ix+OBJ_LOGICAL_LENGTH),l
    ld (ix+OBJ_LOGICAL_LENGTH+1),h
    ld (ix+OBJ_STORAGE_LENGTH),l
    ld (ix+OBJ_STORAGE_LENGTH+1),h
    ld hl,(r17e_source_ptr)
    ld (ix+OBJ_ALLOCATION_PTR),l
    ld (ix+OBJ_ALLOCATION_PTR+1),h
    call zx48_object_record_validate
    jp c,r17e_fail
    ld a,1
    ld (r17e_loaded_namespace_valid),a

    ld hl,(r17e_source_ptr)
    ld de,(r17e_source_len)
    call r17_as_text_obj1_inplace
    jp c,r17e_fail
    ld de,{OBJ_SIZE}
    or a
    sbc hl,de
    jp nz,r17e_fail

    ld hl,(r17e_source_ptr)
    ld de,{OBJ_SIZE}
    add hl,de
    ld bc,{tail}
    call zx48_free
    jp c,r17e_fail

    xor a
    call zx48_object_record_ptr
    jp c,r17e_fail
    push ix
    pop de
    ld hl,r17e_obj_name
    ld bc,10
    ldir
    ld (ix+OBJ_TYPE_ID),OBJ_OBJ
    ld hl,{OBJ_SIZE}
    ld (ix+OBJ_LOGICAL_LENGTH),l
    ld (ix+OBJ_LOGICAL_LENGTH+1),h
    ld (ix+OBJ_STORAGE_LENGTH),l
    ld (ix+OBJ_STORAGE_LENGTH+1),h
    call zx48_object_record_validate
    jp c,r17e_fail

    ld bc,8192
    ld a,ALLOC_ANY
    call zx48_alloc
    jp c,r17e_fail
    ld (r17e_output_ptr),hl
    ld de,$8818
    push hl
    or a
    sbc hl,de
    pop hl
    jp nz,r17e_fail

    ex de,hl
    ld hl,(r17e_source_ptr)
    ld bc,{OBJ_SIZE}
    call r17_ld_obj1_absolute
    jp c,r17e_fail
    ld de,8192
    or a
    sbc hl,de
    jp nz,r17e_fail

    ld hl,(r17e_output_ptr)
    ld de,$E000
    ld bc,8192
r17e_compare:
    ld a,(de)
    cp (hl)
    jr nz,r17e_mismatch
    inc de
    inc hl
    dec bc
    ld a,b
    or c
    jr nz,r17e_compare
    ld a,(r17e_negative_mode)
    or a
    jp nz,r17e_fail

    ld hl,$E000
    ld bc,8192
    call zx48_crc16_ccitt_false
    ld hl,(r17e_resident_crc)
    or a
    sbc hl,de
    jp nz,r17e_fail
    jp r17e_pass
r17e_mismatch:
    ld a,(r17e_negative_mode)
    or a
    jp z,r17e_fail
    jp r17e_pass

; Deterministic proof-session allocator.  The production M48O loader and
; object-record validation remain exact admitted target code; only placement is
; pinned so the 30,554-byte source and its native outputs fit the 48K proof
; session without overwriting resident kernel or proof helpers.
zx48_alloc:
    ld (r17e_alloc_class),a
    ld a,(r17e_alloc_phase)
    or a
    jr z,r17e_alloc_source
    cp 2
    jr z,r17e_alloc_output
    ld a,E_NOMEM
    scf
    ret
r17e_alloc_source:
    ld hl,{source_size}
    or a
    sbc hl,bc
    jr nz,r17e_alloc_bad
    ld a,(r17e_alloc_class)
    and $03
    cp ALLOC_COLD_PREFERRED
    jr nz,r17e_alloc_bad
    ld a,1
    ld (r17e_alloc_phase),a
    ld hl,$6800
    xor a
    ret
r17e_alloc_output:
    ld hl,8192
    or a
    sbc hl,bc
    jr nz,r17e_alloc_bad
    ld a,3
    ld (r17e_alloc_phase),a
    ld hl,$8818
    xor a
    ret
r17e_alloc_bad:
    ld a,E_NOMEM
    scf
    ret

zx48_free:
    ld a,(r17e_alloc_phase)
    cp 1
    jr nz,r17e_free_bad
    push hl
    ld de,$8818
    or a
    sbc hl,de
    pop hl
    jr nz,r17e_free_bad
    push bc
    ld hl,{tail}
    or a
    sbc hl,bc
    pop bc
    jr nz,r17e_free_bad
    ld a,2
    ld (r17e_alloc_phase),a
    xor a
    ret
r17e_free_bad:
    ld a,E_INVAL
    scf
    ret

zx48_process_count:
    xor a
    ret

zx48_tape_load_block:
    ld a,M48O_ROM_DATA_FLAG
    scf
    call ROM_LD_BYTES
    jr nc,r17e_tape_error
    or a
    ret
r17e_tape_error:
    ld a,E_IO
    scf
    ret

r17e_pass:
    jp r17e_pass
r17e_fail:
    jp r17e_fail

r17e_source_name: db "kernel.asm"
r17e_obj_name: db "kernel.obj"
r17e_header: defs M48O_HDR_SIZE,0
r17e_source_ptr: dw 0
r17e_source_len: dw 0
r17e_output_ptr: dw 0
r17e_resident_crc: dw 0
r17e_loaded_namespace_valid: db 0
r17e_negative_mode: db 0
r17e_alloc_phase: db 0
r17e_alloc_class: db 0
r17e_end:
    ASSERT r17e_end <= $6800
    SAVEBIN "r17e-fixture.bin",$4000,r17e_end-$4000
"""

def build_fixture(source_size:int)->tuple[bytes,dict[str,int]]:
    build=ROOT/"v1/build";build.mkdir(parents=True,exist_ok=True)
    src=build/"r17e-fixture.asm";src.write_text(fixture_source(source_size),encoding="utf-8",newline="\n")
    sj=ROOT/"tools/runtime/sjasmplus/bin/sjasmplus";require(sj.is_file(),"project sjasmplus missing")
    p=subprocess.run([str(sj),"--nologo","--sym=r17e-fixture.sym",src.name],cwd=build,text=True,capture_output=True,timeout=60)
    require(p.returncode==0,f"Stage-E fixture assembly failed:\n{p.stdout}\n{p.stderr}")
    binary=(build/"r17e-fixture.bin").read_bytes()
    require(len(binary)<=FIXTURE_CODE2_END-FIXTURE_BASE,f"Stage-E fixture too large: {len(binary)}")
    sy=symbols(build/"r17e-fixture.sym",("r17e_positive","r17e_negative","r17e_pass","r17e_fail","r17e_loaded_namespace_valid"))
    return binary,sy

def debugger(pass_pc:int,fail_pc:int,dump_start:int|None=None,dump_len:int=0)->str:
    lines=[f"breakpoint 0x{pass_pc:04x}","commands 1",f"print 0x{PASS_MARKER:x}"]
    if dump_start is not None:
        lines.append(f"print 0x{DUMP_MARKER:x}")
        lines.extend(f"print [0x{a:04x}]" for a in range(dump_start,dump_start+dump_len))
    lines += ["exit 0","end",f"breakpoint 0x{fail_pc:04x}","commands 2","exit 1","end","continue"]
    return "\n".join(lines)

def run_case(fuse:Path,sna:Path,tap:Path,sy:dict[str,int],entry:str,*,dump_start:int|None=None,dump_len:int=0)->subprocess.CompletedProcess:
    return subprocess.run([
      "/usr/bin/env","SDL_VIDEODRIVER=dummy","SDL_AUDIODRIVER=dummy",str(fuse),
      "--machine","48","--no-sound","--no-confirm-actions","--tape",str(tap),
      "--debugger-command",debugger(sy["r17e_pass"],sy["r17e_fail"],dump_start,dump_len),str(sna)
    ],cwd=ROOT,text=True,capture_output=True,timeout=90,check=False)

def extract_dump(stdout:str,count:int)->bytes:
    vals=[int(x,16) for x in re.findall(r"0x([0-9a-f]+)",stdout,re.I)]
    require(PASS_MARKER in vals,"PASS marker absent from extraction")
    try:i=vals.index(DUMP_MARKER)
    except ValueError:raise Error("dump marker absent")
    data=vals[i+1:i+1+count]
    require(len(data)==count,f"truncated debugger dump {len(data)}/{count}")
    require(all(0<=x<=255 for x in data),"non-byte debugger dump value")
    return bytes(data)

def extract_target(fuse:Path,sna:Path,tap:Path,sy:dict[str,int],start:int,length:int)->bytes:
    out=bytearray()
    step=2048
    for off in range(0,length,step):
        n=min(step,length-off)
        r=run_case(fuse,sna,tap,sy,"r17e_positive",dump_start=start+off,dump_len=n)
        require(r.returncode==0,f"target extraction run failed at {off}: {r.stdout!r} {r.stderr!r}")
        out.extend(extract_dump(r.stdout,n))
    return bytes(out)

def verify_obj1(obj:bytes,kernel:bytes)->None:
    require(len(obj)==OBJ_SIZE and obj[:4]==b"OBJ1" and obj[4]==1 and obj[5]==0,"native OBJ1 identity")
    require(struct.unpack_from("<H",obj,6)[0]==24,"native OBJ1 header size")
    require(struct.unpack_from("<H",obj,8)[0]==8192 and obj[10:16]==b"\0"*6,"native OBJ1 text/BSS/symbol/reloc contract")
    require(struct.unpack_from("<H",obj,16)[0]==OBJ_SIZE and struct.unpack_from("<H",obj,18)[0]==OBJ_SIZE,"native OBJ1 offsets")
    require(obj[24:]==kernel,"native OBJ1 TEXT differs from native kernel")
    hc=struct.unpack_from("<H",obj,22)[0];tmp=bytearray(obj[:24]);tmp[22:24]=b"\0\0"
    require(source_tap.crc16(bytes(tmp))==hc,"native OBJ1 header CRC")
    require(source_tap.crc16(obj[24:])==struct.unpack_from("<H",obj,20)[0],"native OBJ1 text CRC")

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--source",type=Path,required=True)
    ap.add_argument("--tap",type=Path,required=True)
    ap.add_argument("--host-kernel",type=Path,required=True)
    ap.add_argument("--embedded-kernel",type=Path,required=True)
    ap.add_argument("--obj-output",type=Path,required=True)
    ap.add_argument("--kernel-output",type=Path,required=True)
    ap.add_argument("--report",type=Path,required=True)
    a=ap.parse_args()
    source=a.source.read_bytes();tap=a.tap.read_bytes();host=a.host_kernel.read_bytes();embedded=a.embedded_kernel.read_bytes()
    require(len(host)==len(embedded)==KERNEL_SIZE and host==embedded,"host/TZX kernel baseline mismatch")
    h,payload,_=source_tap.decode(tap,"kernel.asm")
    require(payload==source,"retained source TAP does not reconstruct exact source")
    require(h[5]==4 and h[7]==5 and h[6]==0,"retained source TAP envelope")
    fixture,sy=build_fixture(len(source))
    fuse=ROOT/"tools/runtime/fuse/bin/fuse";require(fuse.is_file(),"project FUSE missing")

    mutated=bytearray(source);needle=b"jp $e006\n";pos=mutated.find(needle);require(pos>=0,"mutation anchor missing")
    mutated[pos+len(b"jp $e00")]=ord("7")
    mut_tap=source_tap.make("kernel.asm",bytes(mutated))

    with tempfile.TemporaryDirectory(prefix="zxux-stage-e-") as td:
        td=Path(td);sna=td/"stage-e.sna";sna.write_bytes(make_sna(sy["r17e_positive"],fixture,host))
        pos_tap=td/"kernel.tap";pos_tap.write_bytes(tap)
        positive=run_case(fuse,sna,pos_tap,sy,"r17e_positive")
        require(positive.returncode==0,f"Stage-E positive failed: {positive.stdout!r} {positive.stderr!r}")
        neg_sna=td/"stage-e-neg.sna";neg_sna.write_bytes(make_sna(sy["r17e_negative"],fixture,host))
        neg_tap=td/"kernel-mutated.tap";neg_tap.write_bytes(mut_tap)
        negative=run_case(fuse,neg_sna,neg_tap,sy,"r17e_negative")
        require(negative.returncode==0,f"Stage-E mutation negative failed: {negative.stdout!r} {negative.stderr!r}")
        obj=extract_target(fuse,sna,pos_tap,sy,SOURCE_BASE,OBJ_SIZE)
        native=extract_target(fuse,sna,pos_tap,sy,OUTPUT_BASE,KERNEL_SIZE)

    verify_obj1(obj,native)
    require(native==host==embedded,"Stage-E three-way 8192-byte identity mismatch")
    a.obj_output.parent.mkdir(parents=True,exist_ok=True);a.obj_output.write_bytes(obj)
    a.kernel_output.parent.mkdir(parents=True,exist_ok=True);a.kernel_output.write_bytes(native)
    report={
      "schema":1,"kind":"phase11-pre-release-native-kernel-from-source-tap",
      "source_size":len(source),"source_sha256":sha(source),"source_tap_size":len(tap),"source_tap_sha256":sha(tap),
      "fixture_size":len(fixture),"source_target_address":SOURCE_BASE,"native_obj1_size":len(obj),"native_obj1_sha256":sha(obj),
      "native_kernel_address":OUTPUT_BASE,"native_kernel_size":len(native),"native_kernel_sha256":sha(native),
      "host_kernel_sha256":sha(host),"tzx_embedded_kernel_sha256":sha(embedded),"resident_kernel_address":KERNEL_BASE,
      "controlled_mutation_source_sha256":sha(bytes(mutated)),"controlled_mutation_tap_sha256":sha(mut_tap),
      "assertions":{
        "retained_tap_loaded_by_real_rom_m48o_path":"PASS",
        "loaded_object_exact_type_asm_name_kernel_asm_userhome":"PASS",
        "loaded_raw_payload_transport_crc_and_exact_source_identity":"PASS",
        "ordinary_native_text_as_consumed_loaded_source":"PASS",
        "genuine_native_obj1_emitted_and_extracted":"PASS",
        "native_ld_consumed_native_obj1":"PASS",
        "native_ld_emitted_nonresident_8192_kernel":"PASS",
        "resident_kernel_range_not_used_as_native_output":"PASS",
        "host_tzx_native_three_way_byte_identity":"PASS",
        "controlled_source_mutation_rebuilds_and_identity_fails":"PASS",
      }}
    a.report.parent.mkdir(parents=True,exist_ok=True)
    a.report.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8",newline="\n")
    print(f"native_obj1_sha256={sha(obj)}")
    print(f"native_kernel_sha256={sha(native)}")
    print("ZX-UX PHASE-11 PRE-RELEASE NATIVE KERNEL SOURCE-TAP REBUILD PASS")
    return 0
if __name__=="__main__":raise SystemExit(main())
