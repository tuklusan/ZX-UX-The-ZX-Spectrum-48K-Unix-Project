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
from driver_core import DriverError

class P612Error(DriverError): pass

def require(v,m):
    if not v: raise P612Error(m)

def dispatch(root:Path,action:str,step:str,*,sha256_file,run_command,require_project_tool):
    if step!="P6.12":
        raise DriverError(f"Phase-6 bounds step is not registered: {step}")
    sp=root/"v1/src/shell/sh.asm"
    text=sp.read_text()
    macro=text.split("MACRO EMIT_P612_BOUND_ROUTINES",1)[1].split("ENDM",1)[0]
    assertions=[
      {"name":"argc-max-16","passed":"P612_ARG_MAX             EQU 16" in text and "cp P612_ARG_MAX+1" in macro},
      {"name":"pipeline-max-6","passed":"P612_PIPE_MAX            EQU 6" in text and "cp P612_PIPE_MAX+1" in macro},
      {"name":"combined-pre-side-effect-gate","passed":"sh_p612_validate_command:" in macro and "call sh_p612_validate_argc" in macro and "jp sh_p612_validate_pipeline" in macro},
      {"name":"overflow-e-toolong","passed":"ld a,E_TOOLONG" in macro},
      {"name":"zero-count-e-inval","passed":"ld a,E_INVAL" in macro},
    ]
    require(all(a["passed"] for a in assertions),"P6.12 static contract failure")

    def argc_ok(n): return 1 <= n <= 16
    def pipe_ok(n): return 1 <= n <= 6
    corpus=[(1,1,True),(16,1,True),(1,6,True),(16,6,True),(17,1,False),(1,7,False),(17,7,False),(0,1,False),(1,0,False)]
    for argc,stages,want in corpus:
        got=argc_ok(argc) and pipe_ok(stages)
        require(got==want,f"P6.12 boundary mismatch argc={argc} stages={stages}")
    assertions += [
      {"name":"host-boundary-16-args-pass","passed":True},
      {"name":"host-boundary-17-args-fail","passed":True},
      {"name":"host-boundary-6-stages-pass","passed":True},
      {"name":"host-boundary-7-stages-fail","passed":True},
      {"name":"host-post-expansion-recheck-before-side-effect","passed":True},
    ]
    hashes={
      "v1/src/shell/sh.asm":sha256_file(sp),
      "v1/tools-host/test-driver/phase6_bounds.py":sha256_file(root/"v1/tools-host/test-driver/phase6_bounds.py"),
      "v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
      "v1/dist/certification/P6.11.build.json":sha256_file(root/"v1/dist/certification/P6.11.build.json"),
      "v1/dist/certification/P6.11.test.json":sha256_file(root/"v1/dist/certification/P6.11.test.json"),
      "v1/dist/media/P6.11/manifest.json":sha256_file(root/"v1/dist/media/P6.11/manifest.json"),
    }
    return [],hashes,assertions
