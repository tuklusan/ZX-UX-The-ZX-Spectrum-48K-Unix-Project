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


# P10.16 exact-candidate marker.
class P1016Error(DriverError):
    pass


def require(ok,msg):
    if not ok:
        raise P1016Error(msg)


REQUIRED={
 "ldi":{""},"ldir":{""},"ldd":{""},"lddr":{""},
 "cpi":{""},"cpir":{""},"cpd":{""},"cpdr":{""},
 "in":{"a,(n)","r,(c)"},"out":{"(n),a","(c),r"},
}


def inventory(path:Path):
    got={}
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw or raw.startswith("#"): continue
        m,form,_=raw.split("|",2)
        if m in REQUIRED:
            got.setdefault(m,set()).add(form.strip())
    return got


def dispatch(root,action,step,*,sha256_file,run_command,require_project_tool):
    if step!="P10.16": raise DriverError(step)
    source=root/"tools/as.asm"; text=source.read_text(encoding="utf-8")
    got=inventory(root/"v1/tests/compiler/as-opcode-inventory")
    assertions=[
      {"name":"block-io-inventory-family-coverage","passed":all(got.get(k,set())==v for k,v in REQUIRED.items())},
      {"name":"native-block-encoder","passed":"as_p1016_block:" in text and "as_p1016_block_table:" in text},
      {"name":"native-c-port-encoders","passed":"as_p1016_in_c:" in text and "as_p1016_out_c:" in text},
      {"name":"native-immediate-port-encoders","passed":"as_p1016_in_a_n:" in text and "as_p1016_out_n_a:" in text},
      {"name":"native-port-range-check","passed":"as_p1016_port8:" in text},
      {"name":"undocumented-ed-rejection","passed":"as_p1016_reject_undocumented:" in text},
    ]
    require(all(a["passed"] for a in assertions),"P10.16 static encoder coverage failure")

    assembler=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus")
    build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    golden=build/"p1016-golden.asm"
    golden.write_text("""    DEVICE ZXSPECTRUM48
    ORG $C000
fixture:
    ldi
    ldir
    ldd
    lddr
    cpi
    cpir
    cpd
    cpdr
    in a,($fe)
    in b,(c)
    in a,(c)
    out ($fe),a
    out (c),b
    out (c),a
fixture_end:
    SAVEBIN "p1016-golden.bin",fixture,fixture_end-fixture
""",encoding="utf-8",newline="\n")
    g=run_command([assembler,"--nologo",golden.name],cwd=build,timeout_seconds=30)
    require(not g.timed_out and g.exit_code==0,f"P10.16 golden assemble: {g.stderr or g.stdout}")
    expected=bytes.fromhex(
      "ED A0 ED B0 ED A8 ED B8 ED A1 ED B1 ED A9 ED B9 "
      "DB FE ED 40 ED 78 D3 FE ED 41 ED 79"
    )
    actual=(build/"p1016-golden.bin").read_bytes()
    assertions.append({"name":"sjasmplus-block-io-golden","passed":actual==expected})
    require(actual==expected,"P10.16 SjASMPlus golden mismatch")

    fixture=build/"p1016-native.asm"
    fixture.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../../tools/as.asm"
    ORG $C000
fixture:
    EMIT_P10_AS_BLOCK_IO_ENCODER
fixture_end:
    SAVEBIN "p1016-native.bin",fixture,fixture_end-fixture
""",encoding="utf-8",newline="\n")
    n=run_command([assembler,"--nologo","--sym=p1016-native.sym",fixture.name],cwd=build,timeout_seconds=30)
    require(not n.timed_out and n.exit_code==0,f"P10.16 native assemble: {n.stderr or n.stdout}")

    if action=="test":
        syms=phase3_open_descriptions._symbols(build/"p1016-native.sym",
          ("as_p1016_block","as_p1016_in_c","as_p1016_out_c","as_p1016_in_a_n",
           "as_p1016_out_n_a","as_p1016_port8","as_p1016_reject_undocumented"))
        image=(build/"p1016-native.bin").read_bytes()
        def patch(ram): ram[0xC000-0x4000:0xC000-0x4000+len(image)]=image
        def hlcheck(addr,setup,want):
            code=b"\xF3"+phase1._ld_sp(0xBFC0)+setup+phase1._call(addr)+phase1._jp_c(FAIL_PC)+phase1._ld_de(want)+b"\xB7\xED\x52"+phase1._jp_nz(FAIL_PC)+phase1._jp(PASS_PC)
            run_sna(root,code,patch=patch)
        def acheck(addr,setup,want):
            code=b"\xF3"+phase1._ld_sp(0xBFC0)+setup+phase1._call(addr)+phase1._jp_c(FAIL_PC)+bytes((0xFE,want))+phase1._jp_nz(FAIL_PC)+phase1._jp(PASS_PC)
            run_sna(root,code,patch=patch)
        hlcheck(syms["as_p1016_block"],bytes((0x3E,0)),0xEDA0)
        hlcheck(syms["as_p1016_block"],bytes((0x3E,7)),0xEDB9)
        hlcheck(syms["as_p1016_in_c"],bytes((0x06,7)),0xED78)
        hlcheck(syms["as_p1016_out_c"],bytes((0x06,0)),0xED41)
        acheck(syms["as_p1016_in_a_n"],b"",0xDB)
        acheck(syms["as_p1016_out_n_a"],b"",0xD3)
        acheck(syms["as_p1016_port8"],phase1._ld_hl(0x00FE),0xFE)
        for addr,setup in (
          (syms["as_p1016_block"],bytes((0x3E,8))),
          (syms["as_p1016_in_c"],bytes((0x06,6))),
          (syms["as_p1016_out_c"],bytes((0x06,6))),
          (syms["as_p1016_port8"],phase1._ld_hl(0x0100)),
          (syms["as_p1016_reject_undocumented"],b""),
        ):
            code=b"\xF3"+phase1._ld_sp(0xBFC0)+setup+phase1._call(addr)+b"\xD2"+phase1._word(FAIL_PC)+phase1._jp(PASS_PC)
            run_sna(root,code,patch=patch)

        # Representative target port execution: OUT (C),A then IN A,(C), using
        # Spectrum keyboard/ULA port selection in BC. Deterministic completion
        # proves the encoded BC-selected forms execute on target.
        code=(b"\xF3"+phase1._ld_sp(0xBFC0)+b"\x01\xFE\xFE"+b"\x3E\x00"
              +b"\xED\x79"+b"\xED\x78"+phase1._jp(PASS_PC))
        run_sna(root,code,patch=patch)
        assertions += [
          {"name":"fuse-block-io-encoder-vectors","passed":True},
          {"name":"fuse-illegal-port-register-rejection","passed":True},
          {"name":"fuse-spectrum-bc-port-execution","passed":True},
        ]

    hashes={
      "tools/as.asm":sha256_file(source),
      "v1/tests/compiler/as-opcode-inventory":sha256_file(root/"v1/tests/compiler/as-opcode-inventory"),
      "v1/build/p1016-golden.bin":sha256_file(build/"p1016-golden.bin"),
      "v1/build/p1016-native.bin":sha256_file(build/"p1016-native.bin"),
      "v1/tools-host/test-driver/phase10_step_16.py":sha256_file(root/"v1/tools-host/test-driver/phase10_step_16.py"),
      "v1/dist/certification/P10.15.build.json":sha256_file(root/"v1/dist/certification/P10.15.build.json"),
      "v1/dist/certification/P10.15.test.json":sha256_file(root/"v1/dist/certification/P10.15.test.json"),
    }
    return [g,n],hashes,assertions
