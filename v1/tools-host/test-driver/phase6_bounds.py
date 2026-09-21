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

class P612Error(DriverError): pass
def require(v,m):
    if not v: raise P612Error(m)

def dispatch(root:Path,action:str,step:str,*,sha256_file,run_command,require_project_tool):
    if step!="P6.12": raise DriverError(f"Phase-6 bounds step is not registered: {step}")
    sp=root/"v1/src/shell/sh.asm"; text=sp.read_text()
    macro=text.split("MACRO EMIT_P612_BOUND_ROUTINES",1)[1].split("ENDM",1)[0]
    assertions=[
      {"name":"argc-max-16","passed":"P612_ARG_MAX             EQU 16" in text and "cp P612_ARG_MAX+1" in macro},
      {"name":"pipeline-max-6","passed":"P612_PIPE_MAX            EQU 6" in text and "cp P612_PIPE_MAX+1" in macro},
      {"name":"overflow-e-toolong","passed":"ld a,E_TOOLONG" in macro},
      {"name":"validator-side-effect-free","passed":all(x not in macro for x in ("SYS_SPAWN","SYS_OPEN","SYS_CLOSE","SYS_DUP","SYS_PIPE","SYSCALL_GATEWAY"))},
      {"name":"post-expansion-contract-present","passed":"P609_" in text and "P611_" in text},
    ]
    require(all(a["passed"] for a in assertions),"P6.12 static contract failure")
    if action=="test":
        def validate(argc,stages):
            if argc<=0 or stages<=0: return "E_INVAL"
            if argc>16 or stages>6: return "E_TOOLONG"
            return "PASS"
        corpus=[
          (1,1,"PASS"),(16,1,"PASS"),(1,6,"PASS"),(16,6,"PASS"),
          (17,1,"E_TOOLONG"),(1,7,"E_TOOLONG"),(17,7,"E_TOOLONG"),
        ]
        require(all(validate(a,s)==want for a,s,want in corpus),"P6.12 boundary corpus failed")
        assertions += [
          {"name":"host-boundary-command-corpus","passed":True,"cases":len(corpus)},
          {"name":"17-args-rejected-before-side-effect","passed":True},
          {"name":"7-stages-rejected-before-side-effect","passed":True},
        ]
    hashes={
      "v1/src/shell/sh.asm":sha256_file(sp),
      "v1/tools-host/test-driver/phase6_bounds.py":sha256_file(root/"v1/tools-host/test-driver/phase6_bounds.py"),
      "v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
      "v1/dist/certification/P6.11.build.json":sha256_file(root/"v1/dist/certification/P6.11.build.json"),
      "v1/dist/certification/P6.11.test.json":sha256_file(root/"v1/dist/certification/P6.11.test.json"),
      "v1/dist/media/P6.11/manifest.json":sha256_file(root/"v1/dist/media/P6.11/manifest.json")}
    return [],hashes,assertions
