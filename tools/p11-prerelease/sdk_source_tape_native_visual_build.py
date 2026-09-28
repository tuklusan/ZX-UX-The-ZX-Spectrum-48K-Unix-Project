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

"""Exact SDK source TAP -> target-native visual cc -> OBJ1 -> native ld -> MEX1."""
from __future__ import annotations
import argparse,hashlib,json,re,struct,subprocess,tempfile
from pathlib import Path
import sdk_acquire as sdk

ROOT=Path(__file__).resolve().parents[2]
STACK=0x6F00
HEADER_BASE=0x7000
SOURCE_BASE=0x8800
OBJ_BASE=0xBA00
IMAGE_BASE=0xBB00
MEX_BASE=0xBC00
LOADER_BASE=0xC000
CAP=256
PASS_MARK=0xD1800002
OBJ_MARK=0xD1800003
MEX_MARK=0xD1800004

class Error(RuntimeError): pass
def req(v,m):
    if not v: raise Error(m)
def sha(b): return hashlib.sha256(b).hexdigest()

def symbols(path,names):
    t=path.read_text(encoding="utf-8",errors="replace");out={}
    for n in names:
        m=re.search(rf"^{re.escape(n)}:\s+equ\s+0x([0-9a-f]+)\s*$",t,re.I|re.M)
        req(m,f"missing fixture symbol {n}");out[n]=int(m.group(1),16)
    return out

def db10(name):
    raw=name.encode("ascii");req(1<=len(raw)<=10,f"invalid target name {name!r}")
    raw+=b"\0"*(10-len(raw))
    return ",".join("$%02x"%b for b in raw)

def fixture_source(header_name,header_size,source_name,source_size):
    req(header_size<=SOURCE_BASE-HEADER_BASE,"support header exceeds proof slot")
    req(source_size<=OBJ_BASE-SOURCE_BASE,"C source exceeds proof slot")
    return f"""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../include/tapeobj.inc"
    INCLUDE "../include/mex1.inc"
    INCLUDE "../src/kernel/rom_services.asm"
    INCLUDE "../src/kernel/tape.asm"
    INCLUDE "../src/tools/cc.asm"
    INCLUDE "../../tools/ld.asm"

    ORG $4000
p11h_native_start:
    EMIT_P1128_CC_OBJ1_WRITER
    EMIT_P11PR_CC_SDK_CORPUS_COMPILER
    EMIT_P10_LD_INPUT_LOADER
    EMIT_P10_LD_RELOCATION_ROUTINES
    EMIT_P10_LD_STACK_OPTION_ROUTINES
    EMIT_P10_LD_MEX1_WRITER_ROUTINES
    ASSERT $ <= $6E00

p11h_positive:
    di
    ld sp,$6F00
    ld iy,$5C3A
    xor a
    ld (p11h_alloc_phase),a

    call p11h_read_header
    ld a,(p11h_header+M48O_HDR_TYPE)
    cp 1
    jp nz,p11h_fail
    ld a,(p11h_header+M48O_HDR_DIRECTORY)
    cp DIR_USERHOME
    jp nz,p11h_fail
    ld hl,p11h_header+M48O_HDR_NAME
    ld de,p11h_expected_header_name
    call p11h_name10_equal
    jp nz,p11h_fail
    ld hl,p11h_header
    call zx48_p504_raw_load
    jp c,p11h_fail
    ld (p11h_header_ptr),hl
    ld hl,{header_size}
    or a
    sbc hl,bc
    jp nz,p11h_fail
    ld hl,(p11h_header_ptr)
    ld de,{HEADER_BASE}
    or a
    sbc hl,de
    jp nz,p11h_fail

    call p11h_read_header
    ld a,(p11h_header+M48O_HDR_TYPE)
    cp 5
    jp nz,p11h_fail
    ld a,(p11h_header+M48O_HDR_DIRECTORY)
    cp DIR_USERHOME
    jp nz,p11h_fail
    ld hl,p11h_header+M48O_HDR_NAME
    ld de,p11h_expected_source_name
    call p11h_name10_equal
    jp nz,p11h_fail
    ld hl,p11h_header
    call zx48_p504_raw_load
    jp c,p11h_fail
    ld (p11h_source_ptr),hl
    ld (p11h_source_len),bc
    ld de,{SOURCE_BASE}
    or a
    sbc hl,de
    jp nz,p11h_fail
    ld hl,{source_size}
    or a
    sbc hl,bc
    jp nz,p11h_fail

    ld hl,(p11h_source_ptr)
    ld bc,(p11h_source_len)
    ld de,{OBJ_BASE}
    ld ix,256
    call cc_p11pr_sdk_compile_visual
    jp c,p11h_fail
    ld (p11h_obj_len),hl

    ld bc,(p11h_obj_len)
    ld hl,{OBJ_BASE}
    call ld_p1021_validate_memory
    jp c,p11h_fail

    ld hl,({OBJ_BASE+8})
    ld (p11h_text_len),hl
    ld a,h
    or a
    jp nz,p11h_fail
    ld a,l
    cp 128
    jp nc,p11h_fail
    ld hl,({OBJ_BASE+10})
    ld a,h
    or l
    jp nz,p11h_fail
    ld hl,({OBJ_BASE+12})
    ld de,2
    or a
    sbc hl,de
    jp nz,p11h_fail
    ld hl,({OBJ_BASE+14})
    ld de,1
    or a
    sbc hl,de
    jp nz,p11h_fail

    ld hl,{OBJ_BASE+24}
    ld de,{IMAGE_BASE}
    ld bc,(p11h_text_len)
    ldir

    ld hl,{IMAGE_BASE}
    ld (ld_p1026_image),hl
    ld hl,(p11h_text_len)
    ld (ld_p1026_image_size),hl
    call ld_p1026_reset
    ld hl,CC_P11PR_VIS_TITLE_OPERAND
    ld de,CC_P11PR_VIS_TEMPLATE_SIZE
    ld a,1
    call ld_p1026_apply
    jp c,p11h_fail
    call ld_p1026_finalize
    jp c,p11h_fail
    ld a,(ld_p1026_rel_count)
    cp 1
    jp nz,p11h_fail

    call ld_p1030_stack_default
    jp c,p11h_fail
    ld hl,{IMAGE_BASE}
    ld (ld_p1032_image),hl
    ld hl,(p11h_text_len)
    ld (ld_p1032_image_size),hl
    ld hl,0
    ld (ld_p1032_bss_size),hl
    ld (ld_p1032_entry),hl
    ld hl,(ld_p1030_min_fast_stack)
    ld (ld_p1032_stack),hl
    ld hl,ld_p1026_rel_locs
    ld (ld_p1032_relocs),hl
    ld hl,1
    ld (ld_p1032_reloc_count),hl
    ld hl,{MEX_BASE}
    ld (ld_p1032_output),hl
    ld hl,256
    ld (ld_p1032_capacity),hl
    call ld_p1032_write
    jp c,p11h_fail

    jp p11h_pass

p11h_read_header:
    ld ix,p11h_header
    ld de,M48O_HDR_SIZE
    ld a,M48O_ROM_DATA_FLAG
    scf
    call ROM_LD_BYTES
    jp nc,p11h_fail
    ret
p11h_name10_equal:
    ld b,10
p11h_name10_loop:
    ld a,(de)
    cp (hl)
    ret nz
    inc de
    inc hl
    djnz p11h_name10_loop
    xor a
    ret
p11h_pass:
    jp p11h_pass
p11h_fail:
    jp p11h_fail

p11h_expected_header_name: db {db10(header_name)}
p11h_expected_source_name: db {db10(source_name)}
p11h_header: defs M48O_HDR_SIZE,0
p11h_header_ptr: dw 0
p11h_source_ptr: dw 0
p11h_source_len: dw 0
p11h_obj_len: dw 0
p11h_text_len: dw 0
    ASSERT $ <= $7000

    ORG $C000
p11h_loader_segment:
    EMIT_P502_CRC16_ROUTINES
    EMIT_P503_FRAMING_ROUTINES
    EMIT_P504_RAW_LOADER_ROUTINES
zx48_alloc:
    ld (p11h_alloc_class),a
    ld a,(p11h_alloc_phase)
    or a
    jr z,p11h_alloc_header
    cp 1
    jr z,p11h_alloc_source
    ld a,E_NOMEM
    scf
    ret
p11h_alloc_header:
    ld hl,{header_size}
    or a
    sbc hl,bc
    jr nz,p11h_alloc_bad
    ld a,(p11h_alloc_class)
    and $03
    cp ALLOC_COLD_PREFERRED
    jr nz,p11h_alloc_bad
    ld a,1
    ld (p11h_alloc_phase),a
    ld hl,{HEADER_BASE}
    xor a
    ret
p11h_alloc_source:
    ld hl,{source_size}
    or a
    sbc hl,bc
    jr nz,p11h_alloc_bad
    ld a,(p11h_alloc_class)
    and $03
    cp ALLOC_COLD_PREFERRED
    jr nz,p11h_alloc_bad
    ld a,2
    ld (p11h_alloc_phase),a
    ld hl,{SOURCE_BASE}
    xor a
    ret
p11h_alloc_bad:
    ld a,E_NOMEM
    scf
    ret
zx48_free:
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
    jr nc,p11h_tape_error
    or a
    ret
p11h_tape_error:
    ld a,E_IO
    scf
    ret
p11h_alloc_phase: db 0
p11h_alloc_class: db 0
p11h_end:
    ASSERT p11h_end <= $E000
    SAVEBIN "p11h-sdk-native-visual-tape.bin",$4000,p11h_end-$4000
"""

def build_fixture(header_name,header_size,source_name,source_size):
    b=ROOT/"v1/build";b.mkdir(parents=True,exist_ok=True)
    p=b/"p11h-sdk-native-visual-tape.asm"
    p.write_text(fixture_source(header_name,header_size,source_name,source_size),encoding="utf-8",newline="\n")
    sj=ROOT/"tools/runtime/sjasmplus/bin/sjasmplus";req(sj.is_file(),"project sjasmplus missing")
    r=subprocess.run([str(sj),"--nologo","--sym=p11h-sdk-native-visual-tape.sym",p.name],cwd=b,text=True,capture_output=True,timeout=60)
    req(r.returncode==0,f"fixture assembly failed:\n{r.stdout}\n{r.stderr}")
    blob=(b/"p11h-sdk-native-visual-tape.bin").read_bytes()
    sy=symbols(b/"p11h-sdk-native-visual-tape.sym",("p11h_positive","p11h_pass","p11h_fail"))
    return blob,sy

def make_sna(entry,fixture):
    req(len(fixture)<=0xA000,"fixture exceeds RAM")
    ram=bytearray(0xC000);ram[:len(fixture)]=fixture
    struct.pack_into("<H",ram,STACK-0x4000,entry)
    h=bytearray(27);h[0]=0xFE;h[19]=0x04;struct.pack_into("<H",h,23,STACK);h[25]=1
    return bytes(h)+bytes(ram)

def debugger(sy):
    x=[f"breakpoint 0x{sy['p11h_pass']:04x}","commands 1",f"print 0x{PASS_MARK:x}",f"print 0x{OBJ_MARK:x}"]
    x += [f"print [0x{a:04x}]" for a in range(OBJ_BASE,OBJ_BASE+CAP)]
    x += [f"print 0x{MEX_MARK:x}"]
    x += [f"print [0x{a:04x}]" for a in range(MEX_BASE,MEX_BASE+CAP)]
    x += ["exit 0","end",f"breakpoint 0x{sy['p11h_fail']:04x}","commands 2","exit 1","end","continue"]
    return "\n".join(x)

def run(fuse,sna,tape,sy):
    return subprocess.run(["/usr/bin/env","SDL_VIDEODRIVER=dummy","SDL_AUDIODRIVER=dummy",str(fuse),
      "--machine","48","--no-sound","--no-confirm-actions","--tape",str(tape),
      "--debugger-command",debugger(sy),str(sna)],cwd=ROOT,text=True,capture_output=True,timeout=90)

def dump_after(values,marker):
    req(marker in values,f"debugger marker 0x{marker:x} missing")
    i=values.index(marker);d=values[i+1:i+1+CAP]
    req(len(d)==CAP and all(0<=x<=255 for x in d),"target dump truncated")
    return bytes(d)

def obj_bytes(d):
    req(d[:4]==b"OBJ1" and d[4]==1,"native OBJ1 identity")
    text,bss,ns,nr=struct.unpack_from("<HHHH",d,8);so,ro=struct.unpack_from("<HH",d,16)
    req(0<text<128 and bss==0 and ns==2 and nr==1,"native visual OBJ1 shape")
    req(so==24+text and ro==so+40,"native visual OBJ1 offsets")
    end=ro+6;req(end<=len(d),"native visual OBJ1 truncated")
    return d[:end],text

def mex_bytes(d,text):
    req(d[:4]==b"MEX1" and d[4]==1 and d[6:8]==b"\x18\x00","native MEX1 identity")
    image,bss,entry,stack,rc,ro=struct.unpack_from("<HHHHHH",d,8)
    req((image,bss,entry,stack,rc,ro)==(text,0,0,512,1,24+text),"native visual MEX1 shape")
    end=ro+2;req(end<=len(d),"native visual MEX1 truncated")
    return d[:end]

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--root",type=Path,required=True);ap.add_argument("--output",type=Path,required=True);ap.add_argument("--report",type=Path,required=True);a=ap.parse_args()
    release=json.loads((a.root/"SDK-RELEASE.json").read_text())
    req((release.get("tag"),release.get("commit"),release.get("tree"))==(sdk.TAG,sdk.COMMIT,sdk.TREE),"SDK identity drift")
    fuse=ROOT/"tools/runtime/fuse/bin/fuse";req(fuse.is_file(),"project FUSE missing")
    a.output.mkdir(parents=True,exist_ok=True);rows=[]
    with tempfile.TemporaryDirectory(prefix="zxux-p11h-visual-tape-") as td:
        td=Path(td)
        for category,name in sdk.programs():
            tape=a.root/f"usr/bin/{category}/{name}.src.tap";canonical=tape.read_bytes();decoded=sdk.decode(canonical)
            req(len(decoded)==2,f"{category}/{name} source tape object count")
            header_obj=next((x for x in decoded if x[1]==1),None);source_obj=next((x for x in decoded if x[1]==5),None)
            req(header_obj and source_obj,f"{category}/{name} TXT+C objects absent")
            source_name,obj_name,exe_name=sdk.target_names(name)
            req(source_obj[0]==source_name,f"{category}/{name} target source name drift")
            fixture,sy=build_fixture(header_obj[0],len(header_obj[3]),source_obj[0],len(source_obj[3]))
            sna=td/f"{name}.sna";sna.write_bytes(make_sna(sy["p11h_positive"],fixture))
            r=run(fuse,sna,tape,sy)
            req(r.returncode==0,f"{category}/{name} native visual build failed: {r.stdout!r} {r.stderr!r}")
            vals=[int(v,16) for v in re.findall(r"0x([0-9a-f]+)",r.stdout,re.I)]
            req(PASS_MARK in vals,f"{category}/{name} PASS marker absent")
            obj,text=obj_bytes(dump_after(vals,OBJ_MARK));mex=mex_bytes(dump_after(vals,MEX_MARK),text)
            od=a.output/category/(obj_name+".visual");ex=a.output/category/(exe_name+".visual")
            od.parent.mkdir(parents=True,exist_ok=True);od.write_bytes(obj);ex.write_bytes(mex)
            rows.append({"category":category,"program":name,"source_tape_path":f"usr/bin/{category}/{name}.src.tap",
              "source_tape_sha256":sha(canonical),"target_source":source_name,"source_sha256":sha(source_obj[3]),
              "target_object":obj_name+".visual","native_obj1_size":len(obj),"native_obj1_sha256":sha(obj),
              "target_executable":exe_name+".visual","native_mex1_size":len(mex),"native_mex1_sha256":sha(mex),
              "text_size":text,"tape_load":"PASS","native_visual_cc":"PASS","native_ld":"PASS"})
    req(len(rows)==30,"not all 30 visual native builds passed")
    report={"schema":1,"kind":"phase11-pre-release-sdk-source-tape-native-visual-build","program_count":30,"programs":rows,
      "assertions":{"all_30_inputs_are_exact_pinned_release_tapes":"PASS","all_30_loaded_sources_consumed_by_target_native_visual_cc":"PASS",
      "all_30_visual_obj1_outputs_target_created":"PASS","all_30_visual_mex1_outputs_native_linked":"PASS",
      "host_did_not_construct_or_repair_obj1_or_mex1":"PASS"}}
    a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8",newline="\n")
    print("P11 PRE-RELEASE SDK SOURCE-TAPE NATIVE VISUAL BUILD PASS")
    return 0
if __name__=="__main__":raise SystemExit(main())
