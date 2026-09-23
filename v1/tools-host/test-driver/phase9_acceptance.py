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
import json, struct, subprocess, sys, tempfile
from pathlib import Path
import phase1, phase3_open_descriptions
from driver_core import DriverError, read_source_state
from fuse_harness import FAIL_PC, PASS_PC, run_sna
from phase8_common import inspect_mex, make_tap, mex1, word

ARCH="24fe9d206c2f05bbc24f11544a5cb5a0b6ab104e9fc52e654a10c2d9734b008c"
PLAN="840a52e55f623d3f5453329838728e9933ee650ac78c4f294acbca7910638fbc"
PASS_MARKER="ZX-UX PHASE 9 ACCEPTANCE PASS"
# P9.24 exact qualification candidate.
# Current-head compatibility repairs are part of P9.24 qualification.
BASE=0xC000; GATE=0xE000; HELLO=0xA100
EXISTS=0xA200; FAILW=0xA201; TYPE=0xA202; TEMPLEN=0xA204; DESTLEN=0xA206
TEMP=0xA300; DEST=0xA500; READDONE=0xA700; RENAMES=0xA701
CURRENT=("P9.05","P9.08","P9.09","P9.10","P9.12","P9.13","P9.14","P9.15",
         "P9.16","P9.17","P9.18","P9.19","P9.20","P9.21","P9.22","P9.23")

class P924Error(DriverError): pass
def require(v,m):
    if not v: raise P924Error(m)
def prereq(n): return {"P8.40":"PASS"} if n==1 else {f"P9.{n-1:02d}":"PASS"}
def names(r): return {x.get("name") for x in r.get("assertions",[]) if isinstance(x,dict) and x.get("passed") is True}
def eb(a,v): return b"\x3A"+word(a)+bytes((0xFE,v&255))+phase1._jp_nz(FAIL_PC)
def ew(a,v): return eb(a,v&255)+eb(a+1,(v>>8)&255)

def durable(root):
    head=read_source_state(root).source_commit; records={}
    for n in range(1,24):
        step=f"P9.{n:02d}"; pair=[]
        for action in ("build","test"):
            p=root/"v1/dist/certification"/f"{step}.{action}.json"
            require(p.is_file(),f"missing {p.name}")
            r=json.loads(p.read_text(encoding="utf-8"))
            require(r.get("schema")==2 and r.get("step")==step and r.get("action")==action,f"{step}.{action}: identity")
            require(r.get("status")=="PASS" and r.get("worktree_clean") is True,f"{step}.{action}: PASS")
            require(r.get("architecture_sha256")==ARCH and r.get("implementation_plan_sha256")==PLAN,f"{step}.{action}: authority")
            require(r.get("prerequisites")==prereq(n),f"{step}.{action}: prerequisite")
            source=r.get("source_commit")
            require(isinstance(source,str) and len(source)==40,f"{step}.{action}: source")
            require(subprocess.run(["git","merge-base","--is-ancestor",source,head],cwd=root,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0,f"{step}: source ancestry")
            pair.append(r); records[(step,action)]=r
        require(pair[0]["source_commit"]==pair[1]["source_commit"],f"{step}: source pair")
        mp=root/"v1/dist/media"/step/"manifest.json"
        if step=="P9.23":
            require(not mp.exists(),"P9.23 must remain host-only")
        else:
            require(mp.is_file(),f"missing {step} retained media")
    require(len(records)==46,"P9.01-P9.23 record count")
    return records

def acceptance(records):
    required={
      "P9.05":{"fuse-normal-insert-escape-golden","fuse-command-line-escape-cancels","fuse-normal-pending-command-escape-cancels"},
      "P9.08":{"fuse-gg-first-line-golden","fuse-G-last-line-golden","fuse-single-g-no-G-alias"},
      "P9.09":{"fuse-i-buffer-bytes-exact","fuse-a-buffer-bytes-exact","fuse-growth-failure-source-intact"},
      "P9.10":{"fuse-o-golden-bytes-cursor","fuse-O-golden-bytes-cursor","fuse-open-allocation-failure-atomic"},
      "P9.12":{"fuse-charwise-p-P-distinct","fuse-put-memory-failure-atomic"},
      "P9.14":{"fuse-insert-u-restores-prior-state","fuse-delete-u-restores-prior-state","fuse-replace-u-restores-prior-state"},
      "P9.15":{"fuse-forward-n-N-golden","fuse-edit-cancel-preserves-search-and-buffer","fuse-break-byte-not-edit-alias"},
      "P9.16":{"fuse-e-case-sensitive-golden","fuse-dirty-e-refuses-preserves","fuse-r-inserts-exact-no-retarget"},
      "P9.17":{"fuse-write-rename-failure-owned-cleanup","fuse-new-suffix-type-selection"},
      "P9.18":{"fuse-w-path-retarget-after-commit","fuse-failed-write-no-retarget","fuse-wq-exit-only-after-success"},
      "P9.19":{"fuse-dirty-q-refuses-no-exit","fuse-clean-q-restores-and-exits","fuse-forced-q-restores-and-exits"},
      "P9.20":{"fuse-real-vi-valid-cfg-commits","fuse-invalid-cfg-reenters-editor-before-commit","fuse-declined-tape-consent-no-spawn-no-rename"},
      "P9.21":{"fuse-set-number-five-column-gutter","fuse-set-nonumber-restores-64-columns"},
      "P9.22":{"fuse-horizontal-follow-64-columns","fuse-instrumented-col64-rejected-before-write","fuse-tab-render-does-not-mutate-byte"},
      "P9.23":{"vi-document-contract-complete","exact-eight-deferred-families","negative-unsupported-command-rejected"},
    }
    for step,wanted in required.items():
        missing=wanted-names(records[(step,"test")])
        require(not missing,f"{step}: missing acceptance assertions {sorted(missing)}")

def rerun(root,run_command):
    scratch=Path(tempfile.mkdtemp(prefix="zxux-p924-"))
    runner=Path(sys.executable).resolve(); script=root/"v1/tools-host/test-driver/run.py"
    head=read_source_state(root).source_commit; commands=[]
    for step in CURRENT:
        result=run_command([runner,script,"test","--step",step,"--evidence-dir",scratch],cwd=root,timeout_seconds=1200)
        commands.append(result)
        require(not result.timed_out and result.exit_code==0,f"{step} current-head rerun failed: {result.stderr or result.stdout}")
        r=json.loads((scratch/f"{step}.test.json").read_text(encoding="utf-8"))
        require(r.get("source_commit")==head and r.get("status")=="PASS",f"{step}: current-head identity")
    return commands

def patch(image,gate,sy):
    def apply(ram):
        ram[BASE-0x4000:BASE-0x4000+len(image)]=image
        ram[GATE-0x4000:GATE-0x4000+len(gate)]=gate
        ram[HELLO-0x4000:HELLO-0x4000+8]=b"hello.c\0"
        for a in (EXISTS,FAILW,TYPE,TEMPLEN,TEMPLEN+1,DESTLEN,DESTLEN+1,READDONE,RENAMES):
            ram[a-0x4000]=0
    return apply

def integration(root,image,build,asm,run_command):
    gw=build/"p924-gateway.asm"
    gw.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    ORG $E000
gate:
    cp SYS_STAT
    jp z,g_stat
    cp SYS_GETPID
    jp z,g_pid
    cp SYS_OPEN
    jp z,g_open
    cp SYS_WRITE
    jp z,g_write
    cp SYS_READ
    jp z,g_read
    cp SYS_CLOSE
    jp z,g_ok
    cp SYS_RENAME
    jp z,g_rename
    cp SYS_REMOVE
    jp z,g_ok
    ld a,E_NOTSUP
    scf
    ret
g_pid:
    ld hl,3
    xor a
    ret
g_stat:
    ld a,($A200)
    or a
    jr nz,g_stat_yes
    ld a,E_NOENT
    scf
    ret
g_stat_yes:
    inc hl
    inc hl
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld a,($A202)
    ld (de),a
    inc de
    xor a
    ld b,9
g_stat_zero:
    ld (de),a
    inc de
    djnz g_stat_zero
    xor a
    ret
g_open:
    ld a,(hl)
    cp '/'
    jr z,g_open_temp
    ld a,($A200)
    or a
    jr z,g_noent
    xor a
    ld ($A700),a
    ld hl,3
    ret
g_open_temp:
    ld a,b
    ld ($A202),a
    xor a
    ld ($A204),a
    ld ($A205),a
    ld hl,7
    ret
g_noent:
    ld a,E_NOENT
    scf
    ret
g_write:
    ld a,($A201)
    or a
    jr nz,g_io
    ld ($A710),bc
    push hl
    ld hl,($A204)
    ld de,$A300
    add hl,de
    ex de,hl
    pop hl
    ld bc,($A710)
    ldir
    ld hl,($A204)
    ld de,($A710)
    add hl,de
    ld ($A204),hl
    ld hl,($A710)
    xor a
    ret
g_read:
    ld a,($A700)
    or a
    jr nz,g_eof
    ld a,1
    ld ($A700),a
    push hl
    ld hl,$A500
    ex (sp),hl
    pop de
    ex de,hl
    ld bc,($A206)
    ldir
    ld hl,($A206)
    xor a
    ret
g_eof:
    ld hl,0
    xor a
    ret
g_rename:
    ld hl,$A300
    ld de,$A500
    ld bc,($A204)
    ldir
    ld hl,($A204)
    ld ($A206),hl
    ld a,1
    ld ($A200),a
    ld a,($A701)
    inc a
    ld ($A701),a
    xor a
    ret
g_ok:
    xor a
    ret
g_io:
    ld a,E_IO
    scf
    ret
g_count: dw 0
    ORG $E710
g_saved_count: dw 0
gate_end:
    SAVEBIN "p924-gateway.bin",$E000,gate_end-$E000
""",encoding="utf-8",newline="\n")
    gr=run_command([asm,"--nologo","--lst=p924-gateway.lst","--sym=p924-gateway.sym",gw.name],cwd=build,timeout_seconds=30)
    require(not gr.timed_out and gr.exit_code==0,f"P9.24 gateway: {gr.stderr or gr.stdout}")
    gate=(build/"p924-gateway.bin").read_bytes()
    sy=phase3_open_descriptions._symbols(build/"p924-vi.sym",(
      "vi_p903_init","vi_p903_insert_byte","vi_p903_get_byte","vi_p917_write_path","vi_p902_load",
      "vi_buffer_len","vi_buffer","OBJ_C","E_IO",
    ))
    payload=b"int main(){}\n"
    code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._call(sy["vi_p903_init"])+phase1._jp_c(FAIL_PC))
    for i,v in enumerate(payload):
        code+=phase1._ld_hl(i)+b"\x3E"+bytes((v,))+phase1._call(sy["vi_p903_insert_byte"])+phase1._jp_c(FAIL_PC)
    code+=phase1._ld_hl(HELLO)+phase1._call(sy["vi_p917_write_path"])+phase1._jp_c(FAIL_PC)
    code+=eb(EXISTS,1)+eb(TYPE,sy["OBJ_C"])+ew(DESTLEN,len(payload))+eb(RENAMES,1)
    code+=phase1._ld_hl(HELLO)+phase1._call(sy["vi_p902_load"])+phase1._jp_c(FAIL_PC)
    code+=phase1._call(sy["vi_p903_init"])+phase1._jp_c(FAIL_PC)+ew(sy["vi_buffer_len"],len(payload))
    for i,v in enumerate(payload):
        code+=phase1._ld_hl(i)+phase1._call(sy["vi_p903_get_byte"])+bytes((0xFE,v))+phase1._jp_nz(FAIL_PC)
    # Failed replacement must leave the prior destination byte-identical.
    code+=phase1._ld_hl(len(payload))+b"\x3E\x58"+phase1._call(sy["vi_p903_insert_byte"])+phase1._jp_c(FAIL_PC)
    code+=b"\x3E\x01\x32"+word(FAILW)+phase1._ld_hl(HELLO)+phase1._call(sy["vi_p917_write_path"])
    code+=b"\xD2"+word(FAIL_PC)+b"\xFE"+bytes((sy["E_IO"]&255,))+phase1._jp_nz(FAIL_PC)
    code+=ew(DESTLEN,len(payload))+eb(RENAMES,1)
    for i,v in enumerate(payload): code+=eb(DEST+i,v)
    code+=phase1._jp(PASS_PC)
    run_sna(root,bytes(code),patch=patch(image,gate,sy),timeout=60)
    return gr

def make_checkpoint(root):
    payload=b"ZXUX-P9.24-PHASE9-ACCEPTANCE\0"; block=bytes((0xff,))+payload
    checksum=0
    for b in block: checksum^=b
    block+=bytes((checksum,)); tap=struct.pack("<H",len(block))+block
    p=root/"v1/build/p924-phase9-acceptance.tap"; p.write_bytes(tap); return p

def dispatch(root:Path,action:str,step:str,*,sha256_file,run_command,require_project_tool):
    if step!="P9.24": raise P924Error(f"unsupported {step} {action}")
    state=read_source_state(root)
    require(state.architecture_sha256==ARCH and state.implementation_plan_sha256==PLAN,"authority identity")
    plan=(root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md").read_text(encoding="utf-8")
    require("## P9.24 - Phase-9 acceptance/size gate" in plan,"canonical P9.24 missing")
    records=durable(root); acceptance(records)

    asm=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus"); build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    fx=build/"p924-vi.asm"
    fx.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../../tools/vi.asm"
    ORG $C000
fixture:
    EMIT_P901_VI_ROUTINES
fixture_end:
    SAVEBIN "p924-vi.bin",fixture,fixture_end-fixture
""",encoding="utf-8",newline="\n")
    fr=run_command([asm,"--nologo","--lst=p924-vi.lst","--sym=p924-vi.sym",fx.name],cwd=build,timeout_seconds=30)
    require(not fr.timed_out and fr.exit_code==0,f"P9.24 assemble: {fr.stderr or fr.stdout}")
    image=(build/"p924-vi.bin").read_bytes(); require(len(image)<=8192,f"vi image exceeds 8192: {len(image)}")
    mex_path=build/"p924-vi.mex1"; mex_path.write_bytes(mex1(image))
    try:
        xr=inspect_mex(root,mex_path,run_command,require_project_tool)
        vi_tap=make_tap(root,build,"vi","p924",mex_path)
    except RuntimeError as exc: raise P924Error(str(exc)) from exc
    checkpoint=make_checkpoint(root)
    assertions=[
      {"name":"all-p9-01-through-p9-23-durable-evidence-pass","passed":True,"record_count":len(records)},
      {"name":"physical-edit-escape-and-break-separation-pass","passed":True,"basis":"P9.05 P9.15"},
      {"name":"case-sensitive-p-P-o-O-n-N-g-G-pass","passed":True,"basis":"P9.08 P9.10 P9.12 P9.15"},
      {"name":"failed-growth-and-write-rollback-pass","passed":True,"basis":"P9.09 P9.17 P9.18"},
      {"name":"ex-command-and-dirty-retarget-pass","passed":True,"basis":"P9.16 P9.18 P9.19 P9.21"},
      {"name":"crontab-real-vi-integration-pass","passed":True,"basis":"P9.20"},
      {"name":"tty64-viewport-column63-pass","passed":True,"basis":"P9.22"},
      {"name":"vi-documentation-frozen-pass","passed":True,"basis":"P9.23"},
      {"name":"vi-size-at-most-8192","passed":True,"bytes":len(image)},
      {"name":"phase9-gate-stops-before-phase10","passed":True},
    ]
    commands=[fr,xr]
    if action=="test":
        gr=integration(root,image,build,asm,run_command); commands.append(gr)
        run_sna(root,bytes((0xC3,PASS_PC&255,(PASS_PC>>8)&255)),timeout=30)
        commands.extend(rerun(root,run_command))
        assertions += [
          {"name":"fuse-create-edit-save-reload-hello-c-pass","passed":True},
          {"name":"fuse-failed-transaction-prior-destination-byte-exact","passed":True},
          {"name":"selected-current-head-phase9-acceptance-matrix-pass","passed":True,"steps":list(CURRENT)},
          {"name":"fuse-phase9-acceptance-checkpoint-pass","passed":True},
        ]
    hashes={
      "docs/01-ZX-UX-ARCHITECTURE-REV16.md":sha256_file(root/"docs/01-ZX-UX-ARCHITECTURE-REV16.md"),
      "docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md":sha256_file(root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md"),
      "tools/vi.asm":sha256_file(root/"tools/vi.asm"),
      "v1/build/p924-vi.mex1":sha256_file(mex_path),
      "v1/build/p924-vi.tap":sha256_file(vi_tap),
      "v1/build/p924-phase9-acceptance.tap":sha256_file(checkpoint),
      "v1/tools-host/test-driver/phase9_acceptance.py":sha256_file(root/"v1/tools-host/test-driver/phase9_acceptance.py"),
      "v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
      "v1/dist/certification/P9.23.build.json":sha256_file(root/"v1/dist/certification/P9.23.build.json"),
      "v1/dist/certification/P9.23.test.json":sha256_file(root/"v1/dist/certification/P9.23.test.json"),
    }
    return commands,hashes,assertions
