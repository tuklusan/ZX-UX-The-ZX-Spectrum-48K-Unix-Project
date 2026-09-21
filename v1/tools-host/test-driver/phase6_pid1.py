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
import importlib.util
from pathlib import Path
import struct, sys
from driver_core import DriverError
from fuse_harness import FAIL_PC, PASS_PC, run_sna
import phase1
import phase3_open_descriptions

class P601Error(DriverError): pass
def require(v,m):
    if not v: raise P601Error(m)
def u16(v): return struct.pack("<H",v)
def crc16(data):
    crc=0xffff
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            crc=((crc<<1)^0x1021)&0xffff if crc&0x8000 else (crc<<1)&0xffff
    return crc
def mex1(image):
    h=bytearray(24); h[:4]=b"MEX1"; h[4]=1; h[6:8]=u16(24)
    h[8:10]=u16(len(image)); h[12:14]=u16(0); h[14:16]=u16(128)
    h[18:20]=u16(24+len(image)); h[20:22]=u16(crc16(image))
    h[22:24]=u16(crc16(bytes(h)))
    return bytes(h)+image
def arg1(): return b"ARG1"+bytes((1,0))+u16(11)+b"sh\0"
def env1(): return b"ENV1"+bytes((0,0))+u16(8)

def load_module(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    require(spec is not None and spec.loader is not None,f"cannot load {path}")
    mod=importlib.util.module_from_spec(spec); sys.modules[name]=mod; spec.loader.exec_module(mod); return mod

def dispatch(root:Path,action:str,step:str,*,sha256_file,run_command,require_project_tool):
    if step!="P6.01": raise DriverError(f"Phase-6 PID1 step is not registered: {step}")
    sh=(root/"v1/src/shell/sh.asm").read_text()
    proc=(root/"v1/src/kernel/process.asm").read_text()
    macro=proc.split("MACRO EMIT_P601_PID1_BOOTSTRAP_ROUTINES",1)[1].split("ENDM",1)[0]
    assertions=[
      {"name":"shell-entry-uses-fixed-syscall-gateway","passed":"call SYSCALL_GATEWAY" in sh and "SYS_YIELD" in sh},
      {"name":"pid1-ready-published-last","passed":macro.rfind("ld (ix+PROC_STATE),PROC_READY") > macro.rfind("ld (tty_input_owner),a")},
      {"name":"pid1-root-and-canonical-name","passed":"ld (ix+PROC_CWD),DIR_ROOT" in macro and "p601_name_sh: db 's','h'" in macro},
      {"name":"stdin-read-stdout-stderr-shared-write","passed":"ld c,O_READ" in macro and "ld c,O_WRITE" in macro and "call zx48_od_retain" in macro},
      {"name":"malformed-bootstrap-panics-before-schedule","passed":"zx48_p601_boot_or_panic:" in macro and "jp zx48_panic" in macro and "zx48_schedule" not in macro},
      {"name":"canonical-cold-boot-arg-env-bounds","passed":"ld de,11" in macro and "ld de,8" in macro},
    ]
    require(all(a["passed"] for a in assertions),"P6.01 static contract failure")

    asm=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus")
    build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    sf=build/"p601-sh.asm"
    sf.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/shell/sh.asm"
    ORG $0000
p601_sh_image:
    EMIT_P601_SH_IMAGE
    SAVEBIN "p601-sh-image.bin",p601_sh_image,sh_image_end-p601_sh_image
""",encoding="utf-8",newline="\n")
    sr=run_command([asm,"--nologo","--lst=p601-sh.lst","--sym=p601-sh.sym","p601-sh.asm"],cwd=build,timeout_seconds=30)
    require(not sr.timed_out and sr.exit_code==0,f"P6.01 sh assembly failed: {sr.stderr or sr.stdout}")
    image=(build/"p601-sh-image.bin").read_bytes(); require(4<=len(image)<=64,"P6.01 sh image size implausible")
    mex=mex1(image); (build/"p601-sh.mex1").write_bytes(mex)

    inspector=require_project_tool(root,"v1/tools-host/inspect-mex/inspect.py")
    ir=run_command([sys.executable,inspector,str(build/"p601-sh.mex1"),"--base","0x6000"],cwd=root,timeout_seconds=10)
    require(not ir.timed_out and ir.exit_code==0,f"P6.01 MEX1 inspect failed: {ir.stderr or ir.stdout}")

    maketap=load_module(root/"v1/tools-host/maketap/maketap.py","zxux_p601_maketap")
    tap=maketap.m48o_blocks(maketap.M48OObject("sh",maketap.M48O_BIN,maketap.DIR_BIN,mex))
    (build/"p601-pid1.tap").write_bytes(tap)
    require(tap==maketap.m48o_blocks(maketap.M48OObject("sh",maketap.M48O_BIN,maketap.DIR_BIN,mex)),"P6.01 TAP nondeterministic")

    ff=build/"p601-pid1-fixture.asm"
    ff.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../include/mex1.inc"
    INCLUDE "../src/kernel/process.asm"
    INCLUDE "../src/kernel/handles.asm"
    ORG $C000
p601_fixture_start:
    EMIT_PROCESS_ROUTINES
    EMIT_ARG1_ROUTINES
    EMIT_ENV1_ROUTINES
    EMIT_HANDLE_ROUTINES
    EMIT_P601_PID1_BOOTSTRAP_ROUTINES
tty_input_owner: db 0
p601_test_panic: db 0
zx48_handles_close_all_current: xor a : ret
zx48_schedule: ret
zx48_pipe_endpoint_closed: xor a : ret
zx48_free: xor a : ret
zx48_panic: ld (p601_test_panic),a : ret
p601_fixture_end:
    SAVEBIN "p601-pid1-fixture.bin",p601_fixture_start,p601_fixture_end-p601_fixture_start
""",encoding="utf-8",newline="\n")
    fr=run_command([asm,"--nologo","--lst=p601-pid1-fixture.lst","--sym=p601-pid1-fixture.sym","p601-pid1-fixture.asm"],cwd=build,timeout_seconds=30)
    require(not fr.timed_out and fr.exit_code==0,f"P6.01 PID1 fixture assembly failed: {fr.stderr or fr.stdout}")

    if action=="test":
        sy=phase3_open_descriptions._symbols(build/"p601-pid1-fixture.sym",(
          "zx48_process_init","zx48_handles_init","zx48_p601_pid1_bootstrap","zx48_p601_boot_or_panic",
          "process_table","PROC_DESC_SIZE","PROC_STATE","PROC_CWD","PROC_HANDLES","PROC_ARG_PTR","PROC_ENV_PTR",
          "PROC_READY","DIR_ROOT","open_description_table","OD_REFS_O","tty_input_owner","p601_test_panic",
          "E_FORMAT","PANIC_ROM_CONTRACT"))
        module=(build/"p601-pid1-fixture.bin").read_bytes()
        ARG=0xA000; ENV=0xA100
        def word(v): return bytes((v&255,(v>>8)&255))
        def patch(arg=arg1(),env=env1()):
            def p(ram):
                ram[0xC000-0x4000:0xC000-0x4000+len(module)]=module
                ram[ARG-0x4000:ARG-0x4000+len(arg)]=arg
                ram[ENV-0x4000:ENV-0x4000+len(env)]=env
            return p
        def expect_byte(addr,val):
            return b"\x3A"+word(addr)+bytes((0xFE,val&255))+phase1._jp_nz(FAIL_PC)
        def expect_word(addr,val):
            return b"\x2A"+word(addr)+phase1._ld_de(val)+b"\xB7\xED\x52"+phase1._jp_nz(FAIL_PC)
        pid1=sy["process_table"]+sy["PROC_DESC_SIZE"]
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0))
        code+=phase1._call(sy["zx48_process_init"])+phase1._call(sy["zx48_handles_init"])
        code+=b"\xDD\x21"+word(ARG)+b"\x01"+word(len(arg1()))+phase1._ld_hl(ENV)+phase1._ld_de(len(env1()))
        code+=phase1._call(sy["zx48_p601_pid1_bootstrap"])+phase1._jp_c(FAIL_PC)
        code+=expect_byte(pid1+sy["PROC_STATE"],sy["PROC_READY"])
        code+=expect_byte(pid1+sy["PROC_CWD"],sy["DIR_ROOT"])
        code+=expect_byte(sy["tty_input_owner"],1)
        code+=expect_word(pid1+sy["PROC_ARG_PTR"],ARG)+expect_word(pid1+sy["PROC_ENV_PTR"],ENV)
        code+=expect_byte(pid1+sy["PROC_HANDLES"],0)+expect_byte(pid1+sy["PROC_HANDLES"]+1,1)+expect_byte(pid1+sy["PROC_HANDLES"]+2,1)
        code+=expect_byte(sy["open_description_table"]+sy["OD_REFS_O"],1)
        code+=expect_byte(sy["open_description_table"]+8+sy["OD_REFS_O"],2)
        code+=phase1._jp(PASS_PC)
        run_sna(root,bytes(code),patch=patch())

        bad=bytearray(arg1()); bad[0]=ord("X")
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0))
        code+=phase1._call(sy["zx48_process_init"])+phase1._call(sy["zx48_handles_init"])
        code+=b"\xDD\x21"+word(ARG)+b"\x01"+word(len(bad))+phase1._ld_hl(ENV)+phase1._ld_de(len(env1()))
        code+=phase1._call(sy["zx48_p601_boot_or_panic"])
        code+=expect_byte(pid1+sy["PROC_STATE"],0)+expect_byte(sy["tty_input_owner"],0)
        code+=expect_byte(sy["p601_test_panic"],sy["PANIC_ROM_CONTRACT"])+phase1._jp(PASS_PC)
        run_sna(root,bytes(code),patch=patch(bytes(bad),env1()))
        assertions += [
          {"name":"fuse-pid1-resources-before-first-dispatch","passed":True},
          {"name":"fuse-malformed-boot-contract-panics-before-ready","passed":True},
        ]

    hashes={
      "v1/src/shell/sh.asm":sha256_file(root/"v1/src/shell/sh.asm"),
      "v1/src/kernel/process.asm":sha256_file(root/"v1/src/kernel/process.asm"),
      "v1/build/p601-sh.mex1":sha256_file(build/"p601-sh.mex1"),
      "v1/build/p601-pid1.tap":sha256_file(build/"p601-pid1.tap"),
      "v1/tools-host/test-driver/phase6_pid1.py":sha256_file(root/"v1/tools-host/test-driver/phase6_pid1.py"),
      "v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
      "v1/dist/certification/P5.19.build.json":sha256_file(root/"v1/dist/certification/P5.19.build.json"),
      "v1/dist/certification/P5.19.test.json":sha256_file(root/"v1/dist/certification/P5.19.test.json"),
      "v1/dist/certification/P5.19.result.json":sha256_file(root/"v1/dist/certification/P5.19.result.json"),
      "v1/dist/certification/phase-5.json":sha256_file(root/"v1/dist/certification/phase-5.json"),
    }
    return [sr,ir,fr],hashes,assertions
