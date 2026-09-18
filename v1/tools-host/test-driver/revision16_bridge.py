#!/usr/bin/env python3
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Proprietary rights reserved except as expressly licensed herein.
#
# ZX-UX Sinclair ZX Spectrum Unix
# This file is governed by the SANYALnet Labs Non-Commercial License in the
# root LICENSE file. Non-Commercial use is permitted; Commercial Use and use
# for AI/ML model training are prohibited unless separately authorized.
#
# Attribution is required: "Based on original work by Supratim Sanyal of "
# "SANYALnet Labs." See LICENSE for full terms, warranty disclaimer, termination,
# patent, trademark, and governing-law provisions.

from __future__ import annotations
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Callable
from driver_core import DriverError
from fuse_harness import FAIL_PC, PASS_PC, run_sna
import evidence
import phase1
import phase1_getkey

REV12="a90d523f62a95e8cba6af0312b596a2d5f6bc1aa2ef92f39bb391509b7c15e1b"
REV03="067d96de9a8154d7f6e01bd5b96a3f35a9319a6c046f19125aea361182f055f7"
REV16="24fe9d206c2f05bbc24f11544a5cb5a0b6ab104e9fc52e654a10c2d9734b008c"
REV12_BLOB="56f509189de369038258cca0f61ae0f59ddd4a04"
REV03_BLOB="173c82c30c3787a0a020833b49e3e486e570840e"
PASS_MARKER="ZX-UX REV16 PHASE-3 BASELINE BRIDGE PASS"
class BridgeError(DriverError): pass
def require(ok:bool,msg:str)->None:
    if not ok: raise BridgeError(msg)
def _json(p:Path)->dict[str,Any]:
    d=json.loads(p.read_text(encoding="utf-8")); require(isinstance(d,dict),f"{p.name}: object required"); return d
def _blob(root:Path,path:str,run_command):
    r=run_command(["git","hash-object",path],cwd=root,timeout_seconds=15.0)
    require(not r.timed_out and r.exit_code==0,f"hash-object failed: {path}")
    return r,r.stdout.strip()
def _historical(root:Path,sha256_file,run_command):
    commands=[]
    for path,digest,blob in (("docs/01-ZX-UX-ARCHITECTURE-REV12.md",REV12,REV12_BLOB),("docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV03.md",REV03,REV03_BLOB)):
        require(sha256_file(root/path)==digest,f"{path}: historical digest mismatch")
        c,b=_blob(root,path,run_command); commands.append(c); require(b==blob,f"{path}: historical blob mismatch")
    for name in ("P2.24.build.json","P2.24.test.json","phase-2.json"):
        r=_json(root/"v1/dist/certification"/name)
        require(r.get("status")=="PASS",f"{name}: PASS required")
        require(r.get("architecture_sha256")==REV12,f"{name}: REV12 required")
    return commands
def _static(root:Path,sha256_file):
    require(sha256_file(root/"docs/01-ZX-UX-ARCHITECTURE-REV16.md")==REV16,"REV16 digest mismatch")
    plan=root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md"; pd=sha256_file(plan)
    require(REV16.upper() in plan.read_text(encoding="utf-8"),"REV07 REV16 binding mismatch")
    kb=(root/"v1/src/kernel/keyboard.asm").read_text(encoding="utf-8").lower()
    intr=(root/"v1/src/kernel/interrupt.asm").read_text(encoding="utf-8").lower()
    abi=(root/"v1/docs/abi.md").read_text(encoding="utf-8")
    require(all(token in kb for token in ("cp $27","cp $24","ld a,$1b","ret z")),"exact EDIT raw-key mapping missing")
    require("call zx48_rom_key" not in intr and "zx48_keyboard_decode" not in intr,"IM2 decoder edge forbidden")
    for token in ("CAPS SHIFT + 1","0x1B","CAPS SHIFT + SPACE","BREAK"): require(token in abi,f"ABI missing {token}")
    return [{"name":"rev16-identity-exact","passed":True},{"name":"rev07-identity-computed","passed":True,"sha256":pd},{"name":"edit-break-contract-static","passed":True},{"name":"historical-evidence-read-only","passed":True}]

def _word(value:int)->bytes:
    return bytes((value & 0xFF,(value >> 8) & 0xFF))
def _call(address:int)->bytes:
    return b"\xCD"+_word(address)
def _jp(address:int)->bytes:
    return b"\xC3"+_word(address)
def _jp_c(address:int)->bytes:
    return b"\xDA"+_word(address)
def _jp_nc(address:int)->bytes:
    return b"\xD2"+_word(address)
def _jp_nz(address:int)->bytes:
    return b"\xC2"+_word(address)
def _replace_kernel(kernel_bytes:bytes,replacements:tuple[tuple[int,bytes],...]):
    patched=bytearray(kernel_bytes)
    for address,payload in replacements:
        offset=address-phase1.KERNEL_BASE
        require(0 <= offset <= len(patched)-6,"R16 fixture patch outside kernel")
        require(len(payload) <= 6,"R16 fixture stub too large")
        patched[offset:offset+6]=payload+b"\x00"*(6-len(payload))
    return phase1._kernel_patch(bytes(patched))
def _target_input_tests(root:Path,labels:dict[str,int],kernel_bytes:bytes)->None:
    decode=labels["zx48_keyboard_decode"]; scan=labels["zx48_rom_key_scan"]; ktest=labels["zx48_rom_k_test"]; e_again=labels["E_AGAIN"]
    base=b"\xF3"+b"\x31"+_word(phase1.USER_STACK)
    exact=bytearray(base)+_call(decode)+_jp_c(FAIL_PC)+bytes((0xFE,0x1B))+_jp_nz(FAIL_PC)+_jp(PASS_PC)
    run_sna(root,bytes(exact),patch=_replace_kernel(kernel_bytes,((scan,b"\x11\x24\x27\xAF\xC9"),)))
    invalid=bytearray(base)+_call(decode)+_jp_nc(FAIL_PC)+bytes((0xFE,e_again & 0xFF))+_jp_nz(FAIL_PC)+_jp(PASS_PC)
    run_sna(root,bytes(invalid),patch=_replace_kernel(kernel_bytes,((scan,b"\x11\x24\x27\xF6\x01\xC9"),)))
    shifts=bytearray(base)+_call(decode)+_jp_nc(FAIL_PC)+bytes((0xFE,e_again & 0xFF))+_jp_nz(FAIL_PC)+_jp(PASS_PC)
    run_sna(root,bytes(shifts),patch=_replace_kernel(kernel_bytes,((scan,b"\x11\x18\x27\xAF\xC9"),(ktest,b"\xB7\xC9"))))
    old=phase1_getkey.KEY_VALUE
    try:
        phase1_getkey.KEY_VALUE=0x1B
        phase1_getkey._success_fixture(root,labels,kernel_bytes)
    finally:
        phase1_getkey.KEY_VALUE=old
def _schema_negatives(root:Path,sha256_file)->None:
    plan=sha256_file(root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md")
    good=evidence.valid_fixture("R16.00")
    good["implementation_plan_sha256"]=plan
    good["bridge_source_commit"]=good["source_commit"]
    evidence.validate_final_record(good)
    for label,mutate in (
        ("missing-plan",lambda r:r.pop("implementation_plan_sha256")),
        ("wrong-plan",lambda r:r.__setitem__("implementation_plan_sha256","0"*64)),
        ("wrong-bridge-source",lambda r:r.__setitem__("bridge_source_commit","f"*40)),
    ):
        bad=json.loads(json.dumps(good)); mutate(bad)
        try:
            evidence.validate_final_record(bad)
        except evidence.EvidenceError:
            continue
        raise BridgeError(f"prospective evidence negative oracle unexpectedly passed: {label}")
    evidence.validate_final_record(evidence.valid_fixture("E0.04"))

def _regress(root:Path,run_command,python_tool:Path):
    commands=[]; driver=root/"v1/tools-host/test-driver/run.py"
    old_evidence=os.environ.get("ZXUX_EVIDENCE_DIR")
    try:
        with tempfile.TemporaryDirectory(prefix="zxux-r1600-") as tmp:
            base=Path(tmp)
            os.environ["ZXUX_EVIDENCE_DIR"]=str(base/"e0")
            for step in ("E0.01","E0.03","E0.04"):
                for action in ("build","test"):
                    r=run_command([python_tool,driver,action,"--step",step,"--evidence-dir",base/"e0"],cwd=root,timeout_seconds=2700.0); commands.append(r)
                    require(not r.timed_out and r.exit_code==0,f"{step} {action} regression failed: stdout={r.stdout!r} stderr={r.stderr!r}")
            for phase,last,out in ((1,41,"p1"),(2,24,"p2")):
                evidence_dir=base/out
                os.environ["ZXUX_EVIDENCE_DIR"]=str(evidence_dir)
                for n in range(1,last+1):
                    step=f"P{phase}.{n:02d}"
                    for action in ("build","test"):
                        r=run_command([python_tool,driver,action,"--step",step,"--evidence-dir",evidence_dir],cwd=root,timeout_seconds=2700.0); commands.append(r)
                        require(not r.timed_out and r.exit_code==0,f"{step} {action} regression failed: stdout={r.stdout!r} stderr={r.stderr!r}")
    finally:
        if old_evidence is None:
            os.environ.pop("ZXUX_EVIDENCE_DIR",None)
        else:
            os.environ["ZXUX_EVIDENCE_DIR"]=old_evidence
    return commands

def dispatch(root:Path,action:str,step:str,*,sha256_file:Callable[[Path],str],run_command:Callable[...,Any],require_project_tool:Callable[[Path,str|Path],Path]):
    require(step=="R16.00" and action in ("build","test"),f"unsupported bridge dispatch: {step} {action}")
    commands=_historical(root,sha256_file,run_command); assertions=_static(root,sha256_file)
    r,kernel,listing=phase1._assemble_kernel(root,run_command,require_project_tool)
    commands.append(r)
    require(kernel.is_file() and kernel.stat().st_size==8192,"kernel must be 8192 bytes")
    require(listing.is_file() and listing.with_suffix(".sym").is_file(),"kernel listing/symbol table missing")
    assertions.append({"name":"kernel-build-8192","passed":True})
    assertions.append({"name":"kernel-symbol-table-present","passed":True})
    if action=="test":
        labels=phase1._labels(listing,("zx48_keyboard_decode","zx48_rom_key_scan","zx48_rom_k_test","E_AGAIN","zx48_kernel_stack_init","current_pid","tty_input_owner","cursor_service_parity","screen_mutation_depth","tty_cursor_shape","tty_cursor_visible","tty_row","tty_col","tty_wrap_pending"))
        kernel_bytes=kernel.read_bytes()
        _target_input_tests(root,labels,kernel_bytes)
        _schema_negatives(root,sha256_file)
        assertions.extend([
            {"name":"exact-edit-raw-chord-to-1b-runtime","passed":True},
            {"name":"invalid-multikey-edit-negative-runtime","passed":True},
            {"name":"caps-symbol-not-esc-runtime","passed":True},
            {"name":"sys-con-getkey-h0-l1b-runtime","passed":True},
            {"name":"prospective-schema-negative-suite-pass","passed":True},
        ])
        commands.extend(_regress(root,run_command,require_project_tool(root,"tools/runtime/python/bin/python")))
        assertions.extend([{"name":"e001-e003-e004-regression-pass","passed":True},{"name":"p1-41-current-tree-non-admitting-regression-pass","passed":True},{"name":"p2-24-current-tree-non-admitting-regression-pass","passed":True}])
    names=("docs/01-ZX-UX-ARCHITECTURE-REV12.md","docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV03.md","docs/01-ZX-UX-ARCHITECTURE-REV16.md","docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md","v1/src/kernel/interrupt.asm","v1/src/kernel/keyboard.asm","v1/src/kernel/console.asm","v1/src/kernel/syscall.asm","v1/docs/abi.md","tools/scripts/verify-environment.py","v1/tools-host/test-driver/run.py","v1/tools-host/test-driver/driver_core.py","v1/tools-host/test-driver/evidence.py","v1/tools-host/test-driver/revision16_bridge.py","v1/docs/test-plan.md","v1/dist/certification/README.md","v1/build/kernel.bin")
    return commands,{n:sha256_file(root/n) for n in names if (root/n).is_file()},assertions
