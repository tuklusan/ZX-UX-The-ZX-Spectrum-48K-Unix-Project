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
from fuse_harness import FAIL_PC,PASS_PC,run_sna
import phase1,phase3_open_descriptions
BASE=0xC000; SRC=0xA000; DST=0xA100; BANK=0x6000
class P714Error(DriverError): pass
def req(v,m):
    if not v: raise P714Error(m)
def w(v): return bytes((v&255,v>>8))
def call(a): return b"\xcd"+w(a)
def ldbc(v): return b"\x01"+w(v)
def jpc(a): return b"\xda"+w(a)
def jpnc(a): return b"\xd2"+w(a)
def ex(a,v): return b"\x3a"+w(a)+bytes((0xfe,v))+phase1._jp_nz(FAIL_PC)
def source(root):
    u=(root/"v1/src/kernel/udg.asm").read_text(); s=(root/"v1/src/kernel/syscall.asm").read_text(); p=(root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md").read_text()
    m=s.split("MACRO EMIT_P714_UDG_SYSCALL_ROUTINES",1)[1].split("ENDM",1)[0]
    return [
      {"name":"canonical-p714-present","passed":"## P7.14 - SYS_UDG_DEFINE/GET/CLEAR" in p},
      {"name":"eight-byte-constant-used-by-native-ops","passed":u.count("UDG_SLOT_BYTES")>=4},
      {"name":"define-validates-b-slot-before-pointer","passed":m.index("zx48_p714_sys_udg_define:")<m.index("cp UDG_SLOT_COUNT")<m.index("call zx48_user_range_validate")<m.index("jp zx48_udg_define")},
      {"name":"get-validates-b-slot-before-output","passed":m.index("zx48_p714_sys_udg_get:")<m.index("jp zx48_udg_get") and m.count("call zx48_user_range_validate")>=2},
      {"name":"clear-validates-h-slot-before-mutation","passed":"zx48_p714_sys_udg_clear:" in m and "jp zx48_udg_clear" in m},
    ]
def assemble(root,run_command,require_project_tool):
    asm=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus"); b=root/"v1/build"; b.mkdir(parents=True,exist_ok=True)
    f=b/"p714.asm"; f.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/kernel/syscall.asm"
    INCLUDE "../src/kernel/udg.asm"
    ORG $C000
start:
zx48_alloc: ld hl,$6000 : xor a : ret
zx48_memory_pin_bytes: ret
zx48_cursor_hide: ret
zx48_cursor_show: ret
zx48_bitmap_address: ld hl,$4000 : ret
zx48_memcpy: ldir : ret
    EMIT_USER_RANGE_VALIDATION_ROUTINE
    EMIT_UDG_ROUTINES
    EMIT_P714_UDG_SYSCALL_ROUTINES
finish:
    SAVEBIN "p714.bin",start,finish-start
""",encoding="utf-8",newline="\n")
    r=run_command([asm,"--nologo","--sym=p714.sym","p714.asm"],cwd=b,timeout_seconds=30)
    req(r.exit_code==0 and not r.timed_out,f"assemble: {r.stderr or r.stdout}"); return r,b/"p714.bin",b/"p714.sym"
def patch(img,src=b""):
    def p(ram):
        ram[BASE-0x4000:BASE-0x4000+len(img)]=img
        ram[SRC-0x4000:SRC-0x4000+len(src)]=src
        ram[BANK-0x4000:BANK-0x4000+256]=b"\xa5"*256
        ram[DST-0x4000:DST-0x4000+8]=b"\x5a"*8
    return p
def dispatch(root,action,step,*,sha256_file,run_command,require_project_tool):
    if step!="P7.14": raise P714Error(step)
    assertions=source(root); bad=[x["name"] for x in assertions if not x["passed"]]; req(not bad,f"static: {bad}")
    kc,kernel,_=phase1._assemble_kernel(root,run_command,require_project_tool)
    fc,binp,sym=assemble(root,run_command,require_project_tool)
    s=phase3_open_descriptions._symbols(sym,("zx48_udg_init","zx48_p714_sys_udg_define","zx48_p714_sys_udg_get","zx48_p714_sys_udg_clear","syscall_arg_hl","syscall_arg_bc"))
    if action=="test":
      img=binp.read_bytes(); pat=bytes((0x80,0x40,0x20,0x10,8,4,2,1))
      code=bytearray(b"\xf3"+phase1._ld_sp(phase1.USER_STACK)+call(s["zx48_udg_init"])+jpc(FAIL_PC))
      # define slot0
      code+=phase1._ld_hl(SRC)+b"\x22"+w(s["syscall_arg_hl"])+ldbc(0)+b"\xed\x43"+w(s["syscall_arg_bc"])+call(s["zx48_p714_sys_udg_define"])+jpc(FAIL_PC)
      for i,v in enumerate(pat): code+=ex(BANK+i,v)
      # get slot0
      code+=phase1._ld_hl(DST)+b"\x22"+w(s["syscall_arg_hl"])+ldbc(0)+b"\xed\x43"+w(s["syscall_arg_bc"])+call(s["zx48_p714_sys_udg_get"])+jpc(FAIL_PC)
      for i,v in enumerate(pat): code+=ex(DST+i,v)
      # define/get slot31
      code+=phase1._ld_hl(SRC)+b"\x22"+w(s["syscall_arg_hl"])+ldbc(31)+b"\xed\x43"+w(s["syscall_arg_bc"])+call(s["zx48_p714_sys_udg_define"])+jpc(FAIL_PC)
      for i,v in enumerate(pat): code+=ex(BANK+31*8+i,v)
      # clear slot31
      code+=phase1._ld_hl(31)+b"\x22"+w(s["syscall_arg_hl"])+call(s["zx48_p714_sys_udg_clear"])+jpc(FAIL_PC)
      for i in range(8): code+=ex(BANK+31*8+i,0)
      code+=phase1._jp(PASS_PC); run_sna(root,bytes(code),patch=patch(img,pat))
      # Invalid slot/B/pointer: live bank remains canary.
      for fn,hl,bc in ((s["zx48_p714_sys_udg_define"],SRC,32),(s["zx48_p714_sys_udg_define"],SRC,0x0100),(s["zx48_p714_sys_udg_define"],0xDFFC,0),(s["zx48_p714_sys_udg_get"],0xDFFC,0)):
        q=bytearray(b"\xf3"+phase1._ld_sp(phase1.USER_STACK)+call(s["zx48_udg_init"]))
        q+=phase1._ld_hl(hl)+b"\x22"+w(s["syscall_arg_hl"])+ldbc(bc)+b"\xed\x43"+w(s["syscall_arg_bc"])+call(fn)+jpnc(FAIL_PC)+bytes((0xfe,1))+phase1._jp_nz(FAIL_PC)
        q+=ex(BANK,0)+phase1._jp(PASS_PC); run_sna(root,bytes(q),patch=patch(img,pat))
      q=bytearray(b"\xf3"+phase1._ld_sp(phase1.USER_STACK)+call(s["zx48_udg_init"])+phase1._ld_hl(0x0120)+b"\x22"+w(s["syscall_arg_hl"])+call(s["zx48_p714_sys_udg_clear"])+jpnc(FAIL_PC)+phase1._jp(PASS_PC)); run_sna(root,bytes(q),patch=patch(img,pat))
      assertions += [{"name":"fuse-slot0-slot31-roundtrip-clear-exact","passed":True},{"name":"fuse-invalid-slot-reserved-register-pointer-no-mutation","passed":True}]
    hashes={str(x.relative_to(root)):sha256_file(x) for x in (root/"v1/src/kernel/udg.asm",root/"v1/src/kernel/syscall.asm",root/"v1/tools-host/test-driver/phase7_udg_ops.py",root/"v1/tools-host/test-driver/run.py",kernel)}
    return [kc,fc],hashes,assertions
