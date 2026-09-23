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

import phase1
import phase3_open_descriptions
from driver_core import DriverError
from fuse_harness import PASS_PC, FAIL_PC, run_sna

# P10.09 exact-candidate marker.
class P1009Error(DriverError):
    pass

def require(ok,msg):
    if not ok: raise P1009Error(msg)

def dispatch(root,action,step,*,sha256_file,run_command,require_project_tool):
    if step!="P10.09": raise DriverError(step)
    source=root/"tools/as.asm"; text=source.read_text(encoding="utf-8")
    assertions=[
      {"name":"obj1-binding-record-size","passed":"AS_P1009_RECORD_SIZE  EQU 20" in text},
      {"name":"global-flag-frozen","passed":"AS_P1009_GLOBAL       EQU 1" in text},
      {"name":"export-sections-frozen","passed":all(x in text for x in ("AS_P1009_TEXT         EQU 1","AS_P1009_BSS          EQU 2","AS_P1009_ABS          EQU 3"))},
      {"name":"undefined-import-zero","passed":"as_p1009_import:" in text and "AS_P1009_UNDEF        EQU 0" in text},
      {"name":"case-sensitive-search","passed":"as_p1009_name_equal:" in text and "cp (hl)" in text},
      {"name":"duplicate-binding-rejected","passed":"as_p1009_dup_scan:" in text and "jp z,as_p1009_error" in text},
    ]
    require(all(a["passed"] for a in assertions),"P10.09 static binding contract failure")

    assembler=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus")
    build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    fixture=build/"p1009-bindings.asm"
    fixture.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../../tools/as.asm"
    ORG $C000
fixture:
    EMIT_P10_AS_BINDING_ROUTINES
name_export: db 'foo',0
name_import: db 'bar',0
name_case: db 'Foo',0
fixture_end:
    SAVEBIN "p1009-bindings.bin",fixture,fixture_end-fixture
""",encoding="utf-8",newline="\n")
    result=run_command([assembler,"--nologo","--lst=p1009-bindings.lst","--sym=p1009-bindings.sym",fixture.name],cwd=build,timeout_seconds=30)
    require(not result.timed_out and result.exit_code==0,f"P10.09 assemble: {result.stderr or result.stdout}")

    if action=="test":
        names=("as_p1009_reset","as_p1009_export","as_p1009_import","as_p1009_find","as_p1009_count","as_p1009_table","name_export","name_import","name_case")
        s=phase3_open_descriptions._symbols(build/"p1009-bindings.sym",names)
        image=(build/"p1009-bindings.bin").read_bytes()
        def patch(ram): ram[0xC000-0x4000:0xC000-0x4000+len(image)]=image

        # Export foo as TEXT value 0x1234, import bar as UNDEF value 0.
        code=(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._call(s["as_p1009_reset"])
          +phase1._ld_hl(s["name_export"])+phase1._ld_de(0x1234)+b"\x3E\x01"+phase1._call(s["as_p1009_export"])+phase1._jp_c(FAIL_PC)
          +phase1._ld_hl(s["name_import"])+phase1._call(s["as_p1009_import"])+phase1._jp_c(FAIL_PC)
          +b"\x3A"+phase1._word(s["as_p1009_count"])+b"\xFE\x02"+phase1._jp_nz(FAIL_PC)
          +phase1._ld_hl(s["name_export"])+phase1._call(s["as_p1009_find"])+phase1._jp_c(FAIL_PC)
          +b"\xDD\xE5\xE1"+phase1._ld_de(16)+b"\x19\x7E\xFE\x34"+phase1._jp_nz(FAIL_PC)
          +b"\x23\x7E\xFE\x12"+phase1._jp_nz(FAIL_PC)
          +b"\x23\x7E\xFE\x01"+phase1._jp_nz(FAIL_PC)
          +b"\x23\x7E\xFE\x01"+phase1._jp_nz(FAIL_PC)
          +phase1._ld_hl(s["name_import"])+phase1._call(s["as_p1009_find"])+phase1._jp_c(FAIL_PC)
          +b"\xDD\xE5\xE1"+phase1._ld_de(16)+b"\x19\x7E\xB7"+phase1._jp_nz(FAIL_PC)
          +b"\x23\x7E\xB7"+phase1._jp_nz(FAIL_PC)
          +b"\x23\x7E\xB7"+phase1._jp_nz(FAIL_PC)
          +b"\x23\x7E\xFE\x01"+phase1._jp_nz(FAIL_PC)
          +phase1._jp(PASS_PC))
        run_sna(root,code,patch=patch)

        # Case-sensitive miss and duplicate export must reject.
        code2=(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._call(s["as_p1009_reset"])
          +phase1._ld_hl(s["name_export"])+phase1._ld_de(1)+b"\x3E\x01"+phase1._call(s["as_p1009_export"])+phase1._jp_c(FAIL_PC)
          +phase1._ld_hl(s["name_case"])+phase1._call(s["as_p1009_find"])+b"\xD2"+phase1._word(FAIL_PC)
          +phase1._ld_hl(s["name_export"])+phase1._ld_de(2)+b"\x3E\x01"+phase1._call(s["as_p1009_export"])+b"\xD2"+phase1._word(FAIL_PC)
          +phase1._jp(PASS_PC))
        run_sna(root,code2,patch=patch)
        assertions += [
          {"name":"fuse-export-import-records","passed":True},
          {"name":"fuse-case-and-duplicate-rejection","passed":True},
        ]

    hashes={
      "tools/as.asm":sha256_file(source),
      "v1/build/p1009-bindings.bin":sha256_file(build/"p1009-bindings.bin"),
      "v1/tools-host/test-driver/phase10_as_bindings.py":sha256_file(root/"v1/tools-host/test-driver/phase10_as_bindings.py"),
      "v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
      "v1/dist/certification/P10.08.build.json":sha256_file(root/"v1/dist/certification/P10.08.build.json"),
      "v1/dist/certification/P10.08.test.json":sha256_file(root/"v1/dist/certification/P10.08.test.json"),
    }
    return [result],hashes,assertions
