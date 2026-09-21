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
from fuse_harness import FAIL_PC,PASS_PC,run_sna
import phase1,phase3_open_descriptions
BASE=0xC000; NAME=0xA000; INFO=0xA100
class E(DriverError): pass
def req(v,m):
    if not v: raise E(m)
def word(v): return bytes((v&255,(v>>8)&255))
def expect(a,v): return b"\x3A"+word(a)+bytes((0xFE,v&255))+phase1._jp_nz(FAIL_PC)
def patch(module,name=b"worker\0\0\0\0",info_name=None):
    def p(ram):
        ram[BASE-0x4000:BASE-0x4000+len(module)]=module
        ram[NAME-0x4000:NAME-0x4000+10]=name[:10]
        inf=bytearray(16); inf[0]=2; inf[1]=1; inf[2]=1; inf[4:14]=(info_name or name)[:10]
        ram[INFO-0x4000:INFO-0x4000+16]=inf
    return p
def dispatch(root:Path,action:str,step:str,*,sha256_file,run_command,require_project_tool):
    if step!="P6.24": raise DriverError(f"Phase-6 jobs step is not registered: {step}")
    sp=root/"v1/src/shell/sh.asm"; text=sp.read_text(); m=text.split("MACRO EMIT_P624_JOBS_ROUTINES",1)[1].split("ENDM",1)[0]
    assertions=[{"name":"bounded-six-job-table","passed":"P624_JOB_MAX            EQU 6" in text},{"name":"exact-name-stale-pid-defense","passed":"sh_p624_name_cmp:" in m and "sh_p624_stale:" in m},{"name":"tracks-state-and-name","passed":"PROC_READY" in m and "ld (ix+1),a" in m},{"name":"remove-after-reap-surface","passed":"sh_p624_job_remove:" in m}]
    req(all(x["passed"] for x in assertions),"P6.24 static contract failure")
    asm=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus"); build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    sf=build/"p624-fixture.asm"; sf.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/shell/sh.asm"
    ORG $C000
p624_start:
    EMIT_P624_JOBS_ROUTINES
p624_end:
    SAVEBIN "p624-fixture.bin",p624_start,p624_end-p624_start
""",encoding="utf-8",newline="\n")
    sr=run_command([asm,"--nologo","--lst=p624-fixture.lst","--sym=p624-fixture.sym","p624-fixture.asm"],cwd=build,timeout_seconds=30)
    req(not sr.timed_out and sr.exit_code==0,f"P6.24 fixture failed: {sr.stderr or sr.stdout}")
    if action=="test":
        sy=phase3_open_descriptions._symbols(build/"p624-fixture.sym",("sh_p624_job_add","sh_p624_job_refresh","sh_p624_job_remove","p624_jobs","E_NOENT"))
        mod=(build/"p624-fixture.bin").read_bytes(); jobs=sy["p624_jobs"]
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+b"\x3E\x02"+phase1._ld_hl(NAME)+phase1._call(sy["sh_p624_job_add"])+phase1._jp_c(FAIL_PC))
        code+=expect(jobs,2)+expect(jobs+1,1)
        code+=b"\x3E\x02"+phase1._ld_hl(INFO)+phase1._call(sy["sh_p624_job_refresh"])+phase1._jp_c(FAIL_PC)
        code+=b"\x3E\x02"+phase1._call(sy["sh_p624_job_remove"])+phase1._jp_c(FAIL_PC)+expect(jobs,0)+phase1._jp(PASS_PC)
        run_sna(root,bytes(code),patch=patch(mod))
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+b"\x3E\x02"+phase1._ld_hl(NAME)+phase1._call(sy["sh_p624_job_add"])+phase1._jp_c(FAIL_PC))
        code+=b"\x3E\x02"+phase1._ld_hl(INFO)+phase1._call(sy["sh_p624_job_refresh"])+b"\xD2"+word(FAIL_PC)+bytes((0xFE,sy["E_NOENT"]&255))+phase1._jp_nz(FAIL_PC)+expect(jobs,0)+phase1._jp(PASS_PC)
        run_sna(root,bytes(code),patch=patch(mod,info_name=b"newpid\0\0\0\0"))
        assertions += [{"name":"fuse-job-add-refresh-remove","passed":True},{"name":"fuse-stale-pid-reuse-removed","passed":True}]
    hashes={"v1/src/shell/sh.asm":sha256_file(sp),"v1/tools-host/test-driver/phase6_jobs.py":sha256_file(root/"v1/tools-host/test-driver/phase6_jobs.py"),"v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),"v1/dist/certification/P6.23.build.json":sha256_file(root/"v1/dist/certification/P6.23.build.json"),"v1/dist/certification/P6.23.test.json":sha256_file(root/"v1/dist/certification/P6.23.test.json"),"v1/dist/media/P6.23/manifest.json":sha256_file(root/"v1/dist/media/P6.23/manifest.json")}
    return [sr],hashes,assertions
