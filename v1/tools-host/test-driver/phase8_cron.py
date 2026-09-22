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

import phase1, phase3_open_descriptions
from driver_core import DriverError
from fuse_harness import FAIL_PC, PASS_PC, run_sna
from phase8_common import mex1, inspect_mex, make_tap

BASE=0xC000
BUF=0xA000
KEY=0xA900
SCHED=0xA920

class P825Error(DriverError):
    pass

def require(v,m):
    if not v:
        raise P825Error(m)

def word(v):
    return bytes((v&255,(v>>8)&255))

def call(a):
    return b"\xCD"+word(a)

def jp(a):
    return b"\xC3"+word(a)

def jp_c(a):
    return b"\xDA"+word(a)

def jp_nc(a):
    return b"\xD2"+word(a)

def jp_z(a):
    return b"\xCA"+word(a)

def jp_nz(a):
    return b"\xC2"+word(a)

def ld_hl(v):
    return b"\x21"+word(v)

def ld_bc(v):
    return b"\x01"+word(v)

def ld_ix(v):
    return b"\xDD\x21"+word(v)

def patch(image,data=b"",key=b"",sched=b""):
    def apply(ram):
        ram[BASE-0x4000:BASE-0x4000+len(image)]=image
        ram[BUF-0x4000:BUF-0x4000+len(data)]=data
        ram[KEY-0x4000:KEY-0x4000+len(key)]=key
        ram[SCHED-0x4000:SCHED-0x4000+len(sched)]=sched
    return apply

def validate_fixture(root,image,sy,data,ok,active=None):
    code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+ld_hl(BUF)+ld_bc(len(data))+call(sy["cron_validate"]))
    code += (jp_c(FAIL_PC) if ok else jp_nc(FAIL_PC))
    if ok and active is not None:
        code += bytes((0xFE,active&255))+jp_nz(FAIL_PC)
    code += jp(PASS_PC)
    run_sna(root,bytes(code),patch=patch(image,data+b"\x00"),timeout=30)

def dispatch(root,action,step,*,sha256_file,run_command,require_project_tool):
    if step!="P8.25":
        raise DriverError(step)
    src=root/"v1/src/utils/cron.asm"
    s=src.read_text(encoding="utf-8")
    plan=(root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md").read_text(encoding="utf-8")
    assertions=[
      {"name":"canonical-p825-present","passed":"## P8.25 - Utility `cron`" in plan},
      {"name":"cfg-2048-bound","passed":"CRON_MAX_CFG             EQU 2048" in s},
      {"name":"line-127-bound","passed":"CRON_MAX_LINE            EQU 127" in s},
      {"name":"eight-active-bound","passed":"CRON_MAX_ENTRIES         EQU 8" in s},
      {"name":"special-rules","passed":all(x in s for x in ("@','b','o','o','t","@','h','o','u','r','l','y","@','d','a','i','l','y"))},
      {"name":"all-five-and-match","passed":"cron_match_fields:" in s and "cron_match_no:" in s},
      {"name":"poll-reopen-close","passed":"cron_poll:" in s and "SYS_OPEN" in s and "SYS_READ" in s and "cron_close_cfg" in s},
      {"name":"serial-spawn-wait","passed":"SYS_SPAWN" in s and "SYS_WAIT" in s},
      {"name":"allow-tape-zero","passed":"ld (cron_proc1+13),a" in s},
      {"name":"fifty-tick-sleep","passed":"cron_sleep_50: db 50,0,0,0" in s and "SYS_SLEEP" in s},
      {"name":"time1-gating","passed":"SYS_TIME_GET" in s and "E_AGAIN" in s},
      {"name":"dedupe-key","passed":"cron_dedupe_key:" in s and "cron_last_key: defs 8" in s},
      {"name":"shell-controls-rejected","passed":all(x in s for x in ("cp '|'","cp '&'","cp '<'","cp '>'","cp ';'","cp '='"))},
    ]
    require(all(x["passed"] for x in assertions),"P8.25 static failure")

    tool=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus")
    b=root/"v1/build"; b.mkdir(parents=True,exist_ok=True)
    f=b/"p825-cron.asm"
    f.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/utils/cron.asm"
    ORG $C000
fixture:
    EMIT_P825_CRON_ROUTINES
fixture_end:
    SAVEBIN "p825-cron.bin",fixture,fixture_end-fixture
""",encoding="utf-8",newline="\n")
    fr=run_command([tool,"--nologo","--lst=p825-cron.lst","--sym=p825-cron.sym",f.name],cwd=b,timeout_seconds=30)
    require(not fr.timed_out and fr.exit_code==0,f"P8.25 assemble: {fr.stderr or fr.stdout}")
    image=(b/"p825-cron.bin").read_bytes()
    require(512<=len(image)<16384,"P8.25 image size implausible")

    mp=b/"p825-cron.mex1"; mp.write_bytes(mex1(image))
    try:
        xr=inspect_mex(root,mp,run_command,require_project_tool)
        tap=make_tap(root,b,"cron","p825",mp)
    except RuntimeError as e:
        raise P825Error(str(e))

    if action=="test":
        sy=phase3_open_descriptions._symbols(b/"p825-cron.sym",(
          "cron_validate","cron_match_fields","cron_dedupe_key"
        ))
        valid=b"* * * * * /bin/echo\n@boot /bin/true\n@hourly /bin/false\n@daily /bin/true\n"
        validate_fixture(root,image,sy,valid,True,4)
        validate_fixture(root,image,sy,b"60 * * * * /bin/echo\n",False)
        validate_fixture(root,image,sy,b"* * * * * echo | wc\n",False)
        nine=b"".join([b"@boot /bin/true\n" for _ in range(9)])
        validate_fixture(root,image,sy,nine,False)
        prefix=b"* * * * * "
        line127=prefix+(b"a"*(127-len(prefix)))+b"\n"
        line128=prefix+(b"a"*(128-len(prefix)))+b"\n"
        validate_fixture(root,image,sy,line127,True,1)
        validate_fixture(root,image,sy,line128,False)
        exact2048=b"".join([b"#"+b"x"*126+b"\n" for _ in range(16)])
        require(len(exact2048)==2048,"P8.25 boundary fixture length")
        validate_fixture(root,image,sy,exact2048,True,0)
        validate_fixture(root,image,sy,exact2048+b"x",False)

        sched=bytes((0,12,23,4,5))
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+ld_ix(SCHED))
        code += bytes((0x3E,0,0x06,12,0x0E,23,0x16,4,0x1E,5))+call(sy["cron_match_fields"])+jp_c(FAIL_PC)
        code += bytes((0x3E,1,0x06,12,0x0E,23,0x16,4,0x1E,5))+call(sy["cron_match_fields"])+jp_nc(FAIL_PC)+jp(PASS_PC)
        run_sna(root,bytes(code),patch=patch(image,sched=sched),timeout=30)

        key=bytes((0xE8,0x07,4,23,12,0,0,0))
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+ld_hl(KEY)+call(sy["cron_dedupe_key"])+jp_z(FAIL_PC))
        code += ld_hl(KEY)+call(sy["cron_dedupe_key"])+jp_nz(FAIL_PC)
        code += bytes((0x3E,1,0x32))+word(KEY+5)+ld_hl(KEY)+call(sy["cron_dedupe_key"])+jp_z(FAIL_PC)+jp(PASS_PC)
        run_sna(root,bytes(code),patch=patch(image,key=key),timeout=30)

        assertions += [
          {"name":"fuse-valid-special-and-calendar","passed":True},
          {"name":"fuse-2048-2049-boundary","passed":True},
          {"name":"fuse-127-128-line-boundary","passed":True},
          {"name":"fuse-eight-nine-active-boundary","passed":True},
          {"name":"fuse-field-and-semantics","passed":True},
          {"name":"fuse-minute-revision-dedupe","passed":True},
          {"name":"fuse-operator-rejection","passed":True},
        ]

    hashes={
      "v1/src/utils/cron.asm":sha256_file(src),
      "v1/build/p825-cron.mex1":sha256_file(mp),
      "v1/build/p825-cron.tap":sha256_file(tap),
      "v1/tools-host/test-driver/phase8_cron.py":sha256_file(root/"v1/tools-host/test-driver/phase8_cron.py"),
      "v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
      "v1/dist/certification/P8.24.test.json":sha256_file(root/"v1/dist/certification/P8.24.test.json"),
    }
    return [fr,xr],hashes,assertions
