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


# P10.11 exact-candidate marker.
class P1011Error(DriverError):
    pass


def require(ok, msg):
    if not ok:
        raise P1011Error(msg)


LD_FORMS = {
    "r,r","r,n","r,(hl)","(hl),r","(hl),n","a,(bc)","a,(de)","(bc),a","(de),a",
    "a,(nn)","(nn),a","rr,nn","hl,(nn)","(nn),hl","rr,(nn)","(nn),rr",
    "ix,nn","iy,nn","r,(ix+d)","r,(iy+d)","(ix+d),r","(iy+d),r",
    "sp,hl","sp,ix","sp,iy","a,i","a,r","i,a","r,a",
}


def inventory_forms(path: Path) -> set[str]:
    forms=set()
    for raw in path.read_text(encoding="utf-8").splitlines():
        if raw.startswith("ld|"):
            forms.add(raw.split("|",2)[1].strip())
    return forms


def dispatch(root, action, step, *, sha256_file, run_command, require_project_tool):
    if step != "P10.11":
        raise DriverError(step)
    source=root/"tools/as.asm"
    text=source.read_text(encoding="utf-8")
    inv=inventory_forms(root/"v1/tests/compiler/as-opcode-inventory")
    assertions=[
        {"name":"ld-inventory-exact-family-coverage","passed":inv==LD_FORMS},
        {"name":"native-register-encoder","passed":"as_p1011_ld_r_r:" in text and "as_p1011_ld_r_n:" in text},
        {"name":"native-pair-encoder","passed":"as_p1011_ld_rr_nn:" in text and "as_p1011_ld_rr_mem:" in text},
        {"name":"native-index-encoder","passed":"as_p1011_ld_index_r:" in text and "as_p1011_ld_index_nn:" in text},
        {"name":"native-range-validation","passed":"as_p1011_disp8:" in text and "as_p1011_imm8:" in text},
        {"name":"native-symbolic-abs16-relocation","passed":"as_p1011_abs16_reloc:" in text and "AS_OBJ1_RELOC_ABS16" in text},
        {"name":"fixed-special-load-table","passed":"as_p1011_fixed:" in text and "as_p1011_fixed_end:" in text},
    ]
    require(all(a["passed"] for a in assertions),"P10.11 static coverage failure")

    assembler=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus")
    build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)

    golden=build/"p1011-golden.asm"
    golden.write_text("""    DEVICE ZXSPECTRUM48
    ORG $C000
fixture:
    ld b,c
    ld a,b
    ld b,$12
    ld (hl),$34
    ld d,(hl)
    ld (hl),a
    ld a,(bc)
    ld a,(de)
    ld (bc),a
    ld (de),a
    ld a,($4567)
    ld ($4567),a
    ld bc,$4567
    ld sp,$4567
    ld hl,($4567)
    ld ($4567),hl
    ld bc,($4567)
    ld ($4567),de
    ld ix,$4567
    ld iy,$4567
    ld a,(ix-128)
    ld b,(iy+127)
    ld (ix-128),a
    ld (iy+127),c
    ld sp,hl
    ld sp,ix
    ld sp,iy
    ld a,i
    ld a,r
    ld i,a
    ld r,a
fixture_end:
    SAVEBIN "p1011-golden.bin",fixture,fixture_end-fixture
""",encoding="utf-8",newline="\n")
    g=run_command([assembler,"--nologo",golden.name],cwd=build,timeout_seconds=30)
    require(not g.timed_out and g.exit_code==0,f"P10.11 golden assemble: {g.stderr or g.stdout}")
    expected=bytes.fromhex(
        "41 78 06 12 36 34 56 77 0A 1A 02 12 "
        "3A 67 45 32 67 45 01 67 45 31 67 45 "
        "2A 67 45 22 67 45 ED 4B 67 45 ED 53 67 45 "
        "DD 21 67 45 FD 21 67 45 "
        "DD 7E 80 FD 46 7F DD 77 80 FD 71 7F "
        "F9 DD F9 FD F9 ED 57 ED 5F ED 47 ED 4F"
    )
    actual=(build/"p1011-golden.bin").read_bytes()
    assertions.append({"name":"sjasmplus-family-golden","passed":actual==expected})
    require(actual==expected,"P10.11 SjASMPlus golden mismatch")

    fixture=build/"p1011-native.asm"
    fixture.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../../tools/as.asm"
    ORG $C000
fixture:
    EMIT_P10_AS_OBJ1_RELOC_ROUTINES
    EMIT_P10_AS_LD_ENCODER
relocbuf: defs 6,0
fixture_end:
    SAVEBIN "p1011-native.bin",fixture,fixture_end-fixture
""",encoding="utf-8",newline="\n")
    n=run_command([assembler,"--nologo","--sym=p1011-native.sym",fixture.name],cwd=build,timeout_seconds=30)
    require(not n.timed_out and n.exit_code==0,f"P10.11 native assemble: {n.stderr or n.stdout}")

    if action=="test":
        syms=phase3_open_descriptions._symbols(
            build/"p1011-native.sym",
            ("as_p1011_ld_r_r","as_p1011_ld_r_n","as_p1011_ld_rr_nn",
             "as_p1011_ld_rr_mem","as_p1011_ld_index_r","as_p1011_disp8",
             "as_p1011_imm8","as_p1011_abs16_reloc","relocbuf"),
        )
        image=(build/"p1011-native.bin").read_bytes()
        def patch(ram):
            ram[0xC000-0x4000:0xC000-0x4000+len(image)]=image

        def call_expect_a(addr, setup, want):
            code=b"\xF3"+phase1._ld_sp(0xBFC0)+setup+phase1._call(addr)+phase1._jp_c(FAIL_PC)+bytes((0xFE,want))+phase1._jp_nz(FAIL_PC)+phase1._jp(PASS_PC)
            run_sna(root,code,patch=patch)

        call_expect_a(syms["as_p1011_ld_r_r"],bytes((0x06,0,0x0E,1)),0x41)
        call_expect_a(syms["as_p1011_ld_r_n"],bytes((0x06,7)),0x3E)
        call_expect_a(syms["as_p1011_ld_rr_nn"],bytes((0x06,3)),0x31)
        call_expect_a(syms["as_p1011_disp8"],phase1._ld_hl(0xFF80),0x80)
        call_expect_a(syms["as_p1011_disp8"],phase1._ld_hl(0x007F),0x7F)
        call_expect_a(syms["as_p1011_imm8"],phase1._ld_hl(0x00FF),0xFF)

        for addr,setup in (
            (syms["as_p1011_ld_r_r"],bytes((0x06,6,0x0E,6))),
            (syms["as_p1011_disp8"],phase1._ld_hl(0x0080)),
            (syms["as_p1011_disp8"],phase1._ld_hl(0xFF7F)),
            (syms["as_p1011_imm8"],phase1._ld_hl(0x0100)),
        ):
            code=b"\xF3"+phase1._ld_sp(0xBFC0)+setup+phase1._call(addr)+b"\xD2"+phase1._word(FAIL_PC)+phase1._jp(PASS_PC)
            run_sna(root,code,patch=patch)

        # Emit one relocation and validate all six bytes in target RAM.
        rb=syms["relocbuf"]
        code=(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._ld_bc(rb)+phase1._ld_hl(0x1234)+phase1._ld_de(0x0002)
              +phase1._call(syms["as_p1011_abs16_reloc"])
              +phase1._ld_hl(rb)+bytes((0x7E,0xFE,0x34))+phase1._jp_nz(FAIL_PC)
              +bytes((0x23,0x7E,0xFE,0x12))+phase1._jp_nz(FAIL_PC)
              +bytes((0x23,0x7E,0xFE,0x02))+phase1._jp_nz(FAIL_PC)
              +bytes((0x23,0x7E,0xB7))+phase1._jp_nz(FAIL_PC)
              +bytes((0x23,0x7E,0xFE,0x01))+phase1._jp_nz(FAIL_PC)
              +bytes((0x23,0x7E,0xB7))+phase1._jp_nz(FAIL_PC)+phase1._jp(PASS_PC))
        run_sna(root,code,patch=patch)
        assertions += [
            {"name":"fuse-register-pair-range-vectors","passed":True},
            {"name":"fuse-displacement-boundaries","passed":True},
            {"name":"fuse-immediate-overflow","passed":True},
            {"name":"fuse-abs16-relocation-record","passed":True},
        ]

    hashes={
        "tools/as.asm":sha256_file(source),
        "v1/tests/compiler/as-opcode-inventory":sha256_file(root/"v1/tests/compiler/as-opcode-inventory"),
        "v1/build/p1011-golden.bin":sha256_file(build/"p1011-golden.bin"),
        "v1/build/p1011-native.bin":sha256_file(build/"p1011-native.bin"),
        "v1/tools-host/test-driver/phase10_step_11.py":sha256_file(root/"v1/tools-host/test-driver/phase10_step_11.py"),
        "v1/dist/certification/P10.10.build.json":sha256_file(root/"v1/dist/certification/P10.10.build.json"),
        "v1/dist/certification/P10.10.test.json":sha256_file(root/"v1/dist/certification/P10.10.test.json"),
    }
    return [g,n],hashes,assertions
