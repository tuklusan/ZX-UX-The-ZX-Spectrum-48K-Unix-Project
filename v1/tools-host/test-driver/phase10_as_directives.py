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

# P10.07 qualification retrigger marker, normalized guard.

import phase1
import phase3_open_descriptions
from driver_core import DriverError
from fuse_harness import PASS_PC, FAIL_PC, run_sna

P1007_QUALIFICATION_CANDIDATE = True

class P1007Error(DriverError):
    pass

def require(ok,msg):
    if not ok: raise P1007Error(msg)

def dispatch(root,action,step,*,sha256_file,run_command,require_project_tool):
    if step!="P10.07": raise DriverError(step)
    source=root/"tools/as.asm"; text=source.read_text(encoding="utf-8")
    assertions=[
      {"name":"db-native","passed":"as_p1007_db:" in text},
      {"name":"dw-native-little-endian","passed":"as_p1007_dw:" in text and "ld (hl),e" in text and "ld (hl),d" in text},
      {"name":"ds-native-zero-fill","passed":"as_p1007_ds:" in text and "as_p1007_ds_loop:" in text},
      {"name":"transactional-reserve","passed":"as_p1007_reserve:" in text and "as_p1007_reserve_fail_pop:" in text},
    ]
    require(all(a["passed"] for a in assertions),"P10.07 static contract failure")
    assembler=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus")
    build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    fixture=build/"p1007-directives.asm"
    fixture.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../../tools/as.asm"
    ORG $C000
fixture:
    EMIT_P10_AS_DIRECTIVE_ROUTINES
buffer: defs 16,$AA
fixture_end:
    SAVEBIN "p1007-directives.bin",fixture,fixture_end-fixture
""",encoding="utf-8",newline="\n")
    result=run_command([assembler,"--nologo","--lst=p1007-directives.lst","--sym=p1007-directives.sym",fixture.name],cwd=build,timeout_seconds=30)
    require(not result.timed_out and result.exit_code==0,f"P10.07 assemble: {result.stderr or result.stdout}")
    if action=="test":
        names=("as_p1007_reset","as_p1007_db","as_p1007_dw","as_p1007_ds","as_p1007_size","buffer")
        syms=phase3_open_descriptions._symbols(build/"p1007-directives.sym",names)
        image=(build/"p1007-directives.bin").read_bytes()
        def patch(ram): ram[0xC000-0x4000:0xC000-0x4000+len(image)]=image
        buf=syms["buffer"]; limit=buf+16
        code=(b"\xF3"+phase1._ld_sp(0xBFC0)
          +phase1._ld_hl(buf)+phase1._ld_de(limit)+phase1._call(syms["as_p1007_reset"])
          +b"\x3E\x12"+phase1._call(syms["as_p1007_db"])+phase1._jp_c(FAIL_PC)
          +phase1._ld_de(0x3456)+phase1._call(syms["as_p1007_dw"])+phase1._jp_c(FAIL_PC)
          +b"\x01\x03\x00"+phase1._call(syms["as_p1007_ds"])+phase1._jp_c(FAIL_PC)
          +phase1._call(syms["as_p1007_size"])
          +b"\x7C\xB7"+phase1._jp_nz(FAIL_PC)+b"\x7D\xFE\x06"+phase1._jp_nz(FAIL_PC)
          +phase1._ld_hl(buf)+b"\x7E\xFE\x12"+phase1._jp_nz(FAIL_PC)
          +b"\x23\x7E\xFE\x56"+phase1._jp_nz(FAIL_PC)
          +b"\x23\x7E\xFE\x34"+phase1._jp_nz(FAIL_PC)
          +b"\x23\x7E\xB7"+phase1._jp_nz(FAIL_PC)
          +b"\x23\x7E\xB7"+phase1._jp_nz(FAIL_PC)
          +b"\x23\x7E\xB7"+phase1._jp_nz(FAIL_PC)
          +phase1._jp(PASS_PC))
        run_sna(root,code,patch=patch)
        # Reinitialize with only two bytes available; DW exactly fits, next DB must reject without write.
        code2=(b"\xF3"+phase1._ld_sp(0xBFC0)
          +phase1._ld_hl(buf)+phase1._ld_de(buf+2)+phase1._call(syms["as_p1007_reset"])
          +phase1._ld_de(0xBEEF)+phase1._call(syms["as_p1007_dw"])+phase1._jp_c(FAIL_PC)
          +b"\x3E\x77"+phase1._call(syms["as_p1007_db"])+phase1._jp_nc(FAIL_PC)
          +phase1._call(syms["as_p1007_size"])+b"\x7D\xFE\x02"+phase1._jp_nz(FAIL_PC)
          +phase1._jp(PASS_PC))
        run_sna(root,code2,patch=patch)
        assertions += [
          {"name":"fuse-golden-db-dw-ds","passed":True},
          {"name":"fuse-overflow-rejected-transactionally","passed":True},
        ]
    hashes={
      "tools/as.asm":sha256_file(source),
      "v1/build/p1007-directives.bin":sha256_file(build/"p1007-directives.bin"),
      "v1/tools-host/test-driver/phase10_as_directives.py":sha256_file(root/"v1/tools-host/test-driver/phase10_as_directives.py"),
      "v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
      "v1/dist/certification/P10.06.build.json":sha256_file(root/"v1/dist/certification/P10.06.build.json"),
      "v1/dist/certification/P10.06.test.json":sha256_file(root/"v1/dist/certification/P10.06.test.json"),
    }
    return [result],hashes,assertions
