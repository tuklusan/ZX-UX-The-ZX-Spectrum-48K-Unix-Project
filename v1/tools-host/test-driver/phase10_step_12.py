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
import phase1
import phase3_open_descriptions
from driver_core import DriverError
from fuse_harness import PASS_PC, FAIL_PC, run_sna


# P10.12 exact-candidate marker.
class P1012Error(DriverError):
    pass


def require(ok,msg):
    if not ok:
        raise P1012Error(msg)


REQUIRED={
 "add":{"a,r","a,n","hl,rr","ix,rr","iy,rr"},
 "adc":{"a,r","a,n","hl,rr"},
 "sub":{"r","n"},
 "sbc":{"a,r","a,n","hl,rr"},
 "and":{"r","n"},"xor":{"r","n"},"or":{"r","n"},"cp":{"r","n"},
 "inc":{"r","rr"},"dec":{"r","rr"},
 "neg":{""},"daa":{""},"cpl":{""},"ccf":{""},"scf":{""},
}


def inventory(path:Path):
    got={}
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw or raw.startswith("#"): continue
        m,form,_=raw.split("|",2)
        if m in REQUIRED: got.setdefault(m,set()).add(form.strip())
    return got


def dispatch(root,action,step,*,sha256_file,run_command,require_project_tool):
    if step!="P10.12": raise DriverError(step)
    source=root/"tools/as.asm"; text=source.read_text(encoding="utf-8")
    got=inventory(root/"v1/tests/compiler/as-opcode-inventory")
    assertions=[
      {"name":"arithmetic-inventory-family-coverage","passed":all(got.get(k,set())==v for k,v in REQUIRED.items())},
      {"name":"native-alu-register-and-immediate","passed":"as_p1012_alu_r:" in text and "as_p1012_alu_n:" in text},
      {"name":"native-incdec","passed":"as_p1012_incdec_r:" in text and "as_p1012_incdec_rr:" in text},
      {"name":"native-16bit-arithmetic","passed":"as_p1012_add_hl_rr:" in text and "as_p1012_adc_sbc_hl_rr:" in text},
      {"name":"native-index-arithmetic","passed":"as_p1012_add_index_rr:" in text},
      {"name":"documented-fixed-only","passed":"as_p1012_fixed:" in text and "db $ED,$44" in text},
    ]
    require(all(a["passed"] for a in assertions),"P10.12 static encoder coverage failure")

    assembler=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus")
    build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    golden=build/"p1012-golden.asm"
    golden.write_text("""    DEVICE ZXSPECTRUM48
    ORG $C000
fixture:
    add a,b
    adc a,c
    sub d
    sbc a,e
    and h
    xor l
    or (hl)
    cp a
    add a,$12
    adc a,$12
    sub $12
    sbc a,$12
    and $12
    xor $12
    or $12
    cp $12
    inc b
    dec a
    inc bc
    dec sp
    add hl,bc
    add hl,sp
    add ix,de
    add iy,sp
    adc hl,bc
    sbc hl,sp
    neg
    daa
    cpl
    ccf
    scf
fixture_end:
    SAVEBIN "p1012-golden.bin",fixture,fixture_end-fixture
""",encoding="utf-8",newline="\n")
    g=run_command([assembler,"--nologo",golden.name],cwd=build,timeout_seconds=30)
    require(not g.timed_out and g.exit_code==0,f"P10.12 golden assemble: {g.stderr or g.stdout}")
    expected=bytes.fromhex(
      "80 89 92 9B A4 AD B6 BF "
      "C6 12 CE 12 D6 12 DE 12 E6 12 EE 12 F6 12 FE 12 "
      "04 3D 03 3B 09 39 DD 19 FD 39 ED 4A ED 72 ED 44 27 2F 3F 37"
    )
    actual=(build/"p1012-golden.bin").read_bytes()
    assertions.append({"name":"sjasmplus-arithmetic-golden","passed":actual==expected})
    require(actual==expected,"P10.12 SjASMPlus golden mismatch")

    fixture=build/"p1012-native.asm"
    fixture.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../../tools/as.asm"
    ORG $C000
fixture:
    EMIT_P10_AS_ALU_ENCODER
fixture_end:
    SAVEBIN "p1012-native.bin",fixture,fixture_end-fixture
""",encoding="utf-8",newline="\n")
    n=run_command([assembler,"--nologo","--sym=p1012-native.sym",fixture.name],cwd=build,timeout_seconds=30)
    require(not n.timed_out and n.exit_code==0,f"P10.12 native assemble: {n.stderr or n.stdout}")

    if action=="test":
        syms=phase3_open_descriptions._symbols(build/"p1012-native.sym",
          ("as_p1012_alu_r","as_p1012_alu_n","as_p1012_incdec_r","as_p1012_incdec_rr","as_p1012_add_hl_rr"))
        image=(build/"p1012-native.bin").read_bytes()
        def patch(ram): ram[0xC000-0x4000:0xC000-0x4000+len(image)]=image
        def acheck(addr,setup,want):
            code=b"\xF3"+phase1._ld_sp(0xBFC0)+setup+phase1._call(addr)+phase1._jp_c(FAIL_PC)+bytes((0xFE,want))+phase1._jp_nz(FAIL_PC)+phase1._jp(PASS_PC)
            run_sna(root,code,patch=patch)
        acheck(syms["as_p1012_alu_r"],bytes((0x3E,0,0x06,0)),0x80)
        acheck(syms["as_p1012_alu_r"],bytes((0x3E,7,0x06,7)),0xBF)
        acheck(syms["as_p1012_alu_n"],bytes((0x3E,3)),0xDE)
        acheck(syms["as_p1012_incdec_r"],bytes((0x06,7,0x0E,1)),0x3D)
        acheck(syms["as_p1012_incdec_rr"],bytes((0x06,3,0x0E,1)),0x3B)
        acheck(syms["as_p1012_add_hl_rr"],bytes((0x06,3)),0x39)
        for addr,setup in (
          (syms["as_p1012_alu_r"],bytes((0x3E,8,0x06,0))),
          (syms["as_p1012_alu_r"],bytes((0x3E,0,0x06,8))),
          (syms["as_p1012_incdec_rr"],bytes((0x06,4,0x0E,0))),
        ):
            code=b"\xF3"+phase1._ld_sp(0xBFC0)+setup+phase1._call(addr)+b"\xD2"+phase1._word(FAIL_PC)+phase1._jp(PASS_PC)
            run_sna(root,code,patch=patch)
        assertions += [
          {"name":"fuse-alu-boundary-vectors","passed":True},
          {"name":"fuse-invalid-width-register-pair-rejection","passed":True},
        ]

    hashes={
      "tools/as.asm":sha256_file(source),
      "v1/tests/compiler/as-opcode-inventory":sha256_file(root/"v1/tests/compiler/as-opcode-inventory"),
      "v1/build/p1012-golden.bin":sha256_file(build/"p1012-golden.bin"),
      "v1/build/p1012-native.bin":sha256_file(build/"p1012-native.bin"),
      "v1/tools-host/test-driver/phase10_step_12.py":sha256_file(root/"v1/tools-host/test-driver/phase10_step_12.py"),
      "v1/dist/certification/P10.11.build.json":sha256_file(root/"v1/dist/certification/P10.11.build.json"),
      "v1/dist/certification/P10.11.test.json":sha256_file(root/"v1/dist/certification/P10.11.test.json"),
    }
    return [g,n],hashes,assertions
