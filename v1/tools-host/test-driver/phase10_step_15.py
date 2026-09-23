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


# P10.15 exact-candidate marker.
class P1015Error(DriverError):
    pass


def require(ok,msg):
    if not ok:
        raise P1015Error(msg)


REQUIRED={
 "push":{"rr","ix","iy"},"pop":{"rr","ix","iy"},
 "ex":{"af,af'","de,hl","(sp),hl","(sp),ix","(sp),iy"},"exx":{""},
 "di":{""},"ei":{""},"im":{"0","1","2"},"halt":{""},"nop":{""},
 "reti":{""},"retn":{""},
 "ld":{"a,i","a,r","i,a","r,a"},
}


def inventory(path:Path):
    got={}
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw or raw.startswith("#"): continue
        m,form,_=raw.split("|",2)
        if m in REQUIRED and (m!="ld" or form.strip() in REQUIRED["ld"]):
            got.setdefault(m,set()).add(form.strip())
    return got


def dispatch(root,action,step,*,sha256_file,run_command,require_project_tool):
    if step!="P10.15": raise DriverError(step)
    source=root/"tools/as.asm"; text=source.read_text(encoding="utf-8")
    got=inventory(root/"v1/tests/compiler/as-opcode-inventory")
    assertions=[
      {"name":"special-inventory-family-coverage","passed":all(got.get(k,set())==v for k,v in REQUIRED.items())},
      {"name":"native-stack-encoders","passed":"as_p1015_stack:" in text and "as_p1015_stack_index:" in text},
      {"name":"native-exchange-encoder","passed":"as_p1015_exchange:" in text},
      {"name":"native-im-encoder","passed":"as_p1015_im:" in text and "as_p1015_im_table:" in text},
      {"name":"native-special-encoder","passed":"as_p1015_special:" in text},
      {"name":"native-ir-transfer-encoder","passed":"as_p1015_ir:" in text},
      {"name":"undocumented-special-rejection","passed":"as_p1015_reject_undocumented:" in text},
    ]
    require(all(a["passed"] for a in assertions),"P10.15 static encoder coverage failure")

    assembler=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus")
    build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    golden=build/"p1015-golden.asm"
    golden.write_text("""    DEVICE ZXSPECTRUM48
    ORG $C000
fixture:
    push bc
    push de
    push hl
    push af
    pop bc
    pop de
    pop hl
    pop af
    push ix
    push iy
    pop ix
    pop iy
    ex af,af'
    ex de,hl
    ex (sp),hl
    ex (sp),ix
    ex (sp),iy
    exx
    di
    ei
    im 0
    im 1
    im 2
    halt
    nop
    reti
    retn
    ld a,i
    ld a,r
    ld i,a
    ld r,a
fixture_end:
    SAVEBIN "p1015-golden.bin",fixture,fixture_end-fixture
""",encoding="utf-8",newline="\n")
    g=run_command([assembler,"--nologo",golden.name],cwd=build,timeout_seconds=30)
    require(not g.timed_out and g.exit_code==0,f"P10.15 golden assemble: {g.stderr or g.stdout}")
    expected=bytes.fromhex(
      "C5 D5 E5 F5 C1 D1 E1 F1 DD E5 FD E5 DD E1 FD E1 "
      "08 EB E3 DD E3 FD E3 D9 F3 FB ED 46 ED 56 ED 5E "
      "76 00 ED 4D ED 45 ED 57 ED 5F ED 47 ED 4F"
    )
    actual=(build/"p1015-golden.bin").read_bytes()
    assertions.append({"name":"sjasmplus-special-golden","passed":actual==expected})
    require(actual==expected,"P10.15 SjASMPlus golden mismatch")

    fixture=build/"p1015-native.asm"
    fixture.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../../tools/as.asm"
    ORG $C000
fixture:
    EMIT_P10_AS_SPECIAL_ENCODER
fixture_end:
    SAVEBIN "p1015-native.bin",fixture,fixture_end-fixture
""",encoding="utf-8",newline="\n")
    n=run_command([assembler,"--nologo","--sym=p1015-native.sym",fixture.name],cwd=build,timeout_seconds=30)
    require(not n.timed_out and n.exit_code==0,f"P10.15 native assemble: {n.stderr or n.stdout}")

    if action=="test":
        syms=phase3_open_descriptions._symbols(build/"p1015-native.sym",
          ("as_p1015_stack","as_p1015_stack_index","as_p1015_exchange","as_p1015_im",
           "as_p1015_special","as_p1015_ir","as_p1015_reject_undocumented"))
        image=(build/"p1015-native.bin").read_bytes()
        def patch(ram): ram[0xC000-0x4000:0xC000-0x4000+len(image)]=image
        def acheck(addr,setup,want):
            code=b"\xF3"+phase1._ld_sp(0xBFC0)+setup+phase1._call(addr)+phase1._jp_c(FAIL_PC)+bytes((0xFE,want))+phase1._jp_nz(FAIL_PC)+phase1._jp(PASS_PC)
            run_sna(root,code,patch=patch)
        def hlcheck(addr,setup,want):
            code=b"\xF3"+phase1._ld_sp(0xBFC0)+setup+phase1._call(addr)+phase1._jp_c(FAIL_PC)+phase1._ld_de(want)+b"\xB7\xED\x52"+phase1._jp_nz(FAIL_PC)+phase1._jp(PASS_PC)
            run_sna(root,code,patch=patch)
        acheck(syms["as_p1015_stack"],bytes((0x3E,1,0x06,3)),0xF5)
        acheck(syms["as_p1015_stack"],bytes((0x3E,0,0x06,0)),0xC1)
        hlcheck(syms["as_p1015_stack_index"],bytes((0x3E,1,0x06,1)),0xFDE5)
        hlcheck(syms["as_p1015_exchange"],bytes((0x3E,4)),0xFDE3)
        hlcheck(syms["as_p1015_im"],bytes((0x3E,2)),0xED5E)
        hlcheck(syms["as_p1015_special"],bytes((0x3E,4)),0xED4D)
        hlcheck(syms["as_p1015_ir"],bytes((0x3E,3)),0xED4F)
        for addr,setup in (
          (syms["as_p1015_stack"],bytes((0x3E,0,0x06,4))),
          (syms["as_p1015_stack_index"],bytes((0x3E,2,0x06,0))),
          (syms["as_p1015_exchange"],bytes((0x3E,6))),
          (syms["as_p1015_im"],bytes((0x3E,3))),
          (syms["as_p1015_special"],bytes((0x3E,6))),
          (syms["as_p1015_ir"],bytes((0x3E,4))),
          (syms["as_p1015_reject_undocumented"],b""),
        ):
            code=b"\xF3"+phase1._ld_sp(0xBFC0)+setup+phase1._call(addr)+b"\xD2"+phase1._word(FAIL_PC)+phase1._jp(PASS_PC)
            run_sna(root,code,patch=patch)
        assertions += [
          {"name":"fuse-stack-special-vectors","passed":True},
          {"name":"fuse-invalid-im-register-pair-rejection","passed":True},
          {"name":"fuse-undocumented-special-rejection","passed":True},
        ]

    hashes={
      "tools/as.asm":sha256_file(source),
      "v1/tests/compiler/as-opcode-inventory":sha256_file(root/"v1/tests/compiler/as-opcode-inventory"),
      "v1/build/p1015-golden.bin":sha256_file(build/"p1015-golden.bin"),
      "v1/build/p1015-native.bin":sha256_file(build/"p1015-native.bin"),
      "v1/tools-host/test-driver/phase10_step_15.py":sha256_file(root/"v1/tools-host/test-driver/phase10_step_15.py"),
      "v1/dist/certification/P10.14.build.json":sha256_file(root/"v1/dist/certification/P10.14.build.json"),
      "v1/dist/certification/P10.14.test.json":sha256_file(root/"v1/dist/certification/P10.14.test.json"),
    }
    return [g,n],hashes,assertions
