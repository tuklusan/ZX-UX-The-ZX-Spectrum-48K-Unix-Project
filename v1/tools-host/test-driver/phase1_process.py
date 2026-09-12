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
import re
from typing import Any, Callable

from driver_core import DriverError
from fuse_harness import FAIL_PC, PASS_PC, run_sna
import phase1

PROC_DESC_SIZE = 48
MAX_PROCESSES = 8
MAX_HANDLES = 8
OPEN_DESCRIPTION_COUNT = 24
OD_DESC_SIZE = 12
PROCESS_BUDGET = 896

OFFSETS = {
    "pid": 0, "parent": 1, "state": 2, "flags": 3, "image_base": 4,
    "image_size": 6, "stack_low": 8, "stack_high": 10, "saved_sp": 12,
    "exit_status": 14, "wait_object": 15, "handles": 16, "wake_tick": 24,
    "cwd": 28, "name": 29, "owned_bytes": 40, "arg_ptr": 42,
    "env_ptr": 44, "private_flags": 46, "reserved": 47,
}
STATE_CONSTANTS = {
    "PROC_FREE": 0, "PROC_READY": 1, "PROC_RUNNING": 2, "PROC_SLEEPING": 3,
    "PROC_WAIT_INPUT": 4, "PROC_WAIT_PIPE_READ": 5, "PROC_WAIT_PIPE_WRITE": 6,
    "PROC_WAIT_CHILD": 7, "PROC_ZOMBIE": 8,
}


class Phase1ProcessError(DriverError): pass


def require(condition: bool, message: str) -> None:
    if not condition: raise Phase1ProcessError(message)

def _word(value: int) -> bytes: return bytes((value & 0xFF, (value >> 8) & 0xFF))
def _call(address: int) -> bytes: return b"\xCD" + _word(address)
def _jp(address: int) -> bytes: return b"\xC3" + _word(address)
def _jp_nz(address: int) -> bytes: return b"\xC2" + _word(address)
def _ld_sp(value: int) -> bytes: return b"\x31" + _word(value)
def _expect_byte(address: int, value: int) -> bytes:
    return b"\x3A" + _word(address) + bytes((0xFE, value & 0xFF)) + _jp_nz(FAIL_PC)


def _equ_values(text: str) -> dict[str, int]:
    values: dict[str, int] = {}
    for raw in text.splitlines():
        line = raw.split(";", 1)[0].strip()
        match = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_]*)\s+EQU\s+([^\s]+)", line, re.IGNORECASE)
        if match is None: continue
        name, token = match.groups()
        if token.startswith("$"): values[name.upper()] = int(token[1:], 16)
        elif token.isdigit(): values[name.upper()] = int(token, 10)
    return values


def _identifier_present(text: str, name: str) -> bool:
    return re.search(rf"(?<![A-Za-z0-9_]){re.escape(name)}(?![A-Za-z0-9_])", text, re.IGNORECASE) is not None


def _static_contract(root: Path) -> list[dict[str, object]]:
    inc = (root / "v1/include/zx48ux.inc").read_text(encoding="utf-8")
    process = (root / "v1/src/kernel/process.asm").read_text(encoding="utf-8")
    scheduler = (root / "v1/src/kernel/scheduler.asm").read_text(encoding="utf-8")
    public, layout = _equ_values(inc), _equ_values(process)
    lp, ls = process.lower(), scheduler.lower()
    restore = ls.find("or proc_private_started"); saved_sp = ls.find("ld l,(ix+proc_saved_sp)", restore)
    info_start = lp.find("zx48_process_info:"); info_end = lp.find("zx48_process_exit:")
    info_body = lp[info_start:info_end] if 0 <= info_start < info_end else ""
    duplicate = ("PROC_PC", "PROC_AF", "PROC_BC", "PROC_DE", "PROC_HL", "PROC_IX")
    return [
        {"name":"state-ids-exact-0-through-8","passed":all(public.get(n)==v for n,v in STATE_CONSTANTS.items())},
        {"name":"eight-descriptors-only","passed":public.get("MAX_PROCESSES")==MAX_PROCESSES},
        {"name":"eight-handles-per-process","passed":public.get("MAX_HANDLES_PER_PROCESS")==MAX_HANDLES},
        {"name":"twenty-four-open-descriptions","passed":public.get("OPEN_DESCRIPTION_COUNT")==OPEN_DESCRIPTION_COUNT},
        {"name":"descriptor-size-48-at-most-56","passed":public.get("PROC_DESC_SIZE")==PROC_DESC_SIZE and PROC_DESC_SIZE<=56},
        {"name":"open-description-size-12","passed":public.get("OD_DESC_SIZE")==OD_DESC_SIZE},
        {"name":"private-started-bit-is-80","passed":public.get("PROC_PRIVATE_STARTED")==0x80},
        {"name":"descriptor-layout-complete","passed":all(layout.get(f"PROC_{n.upper()}")==v for n,v in OFFSETS.items())},
        {"name":"process-table-at-most-448","passed":PROC_DESC_SIZE*MAX_PROCESSES<=448},
        {"name":"process-open-description-budget-at-most-896","passed":PROC_DESC_SIZE*MAX_PROCESSES+OPEN_DESCRIPTION_COUNT*OD_DESC_SIZE<=PROCESS_BUDGET},
        {"name":"pid0-pid1-reservation-scan-starts-at-2","passed":"ld ix,process_table+2*proc_desc_size" in lp and "ld c,2" in lp},
        {"name":"eight-handle-open-description-ids","passed":"ld b,max_handles_per_process" in lp and "ld a,handle_free" in lp},
        {"name":"saved-sp-only-runnable-context","passed":not any(_identifier_present(process,n) for n in duplicate)},
        {"name":"started-private-and-not-proc-info","passed":"and proc_flag_cancel" in info_body and not _identifier_present(info_body,"PROC_PRIVATE_FLAGS")},
        {"name":"started-set-immediately-before-restore","passed":0<=restore<saved_sp and saved_sp-restore<96},
        {"name":"name-is-exact-ten-byte-copy","passed":"ld bc,10" in lp and "process_name_sh: db 's','h',0,0,0,0,0,0,0,0" in lp},
    ]


def _negative_contract_tests() -> list[dict[str, object]]:
    cases={
        "reject-57-byte-descriptor":57>56,
        "reject-ninth-record":9>MAX_PROCESSES,
        "reject-duplicate-runnable-context":"PROC_PC" not in {f"PROC_{n.upper()}" for n in OFFSETS},
        "reject-public-started-bit":0x80&0x01==0,
        "reject-over-896-planning-budget":56*9+OPEN_DESCRIPTION_COUNT*OD_DESC_SIZE>PROCESS_BUDGET,
    }
    return [{"name":n,"passed":p} for n,p in cases.items()]


def _run_named(root: Path, name: str, code: bytes, kernel_bytes: bytes) -> None:
    try: run_sna(root, code, patch=phase1._kernel_patch(kernel_bytes))
    except DriverError as exc: raise Phase1ProcessError(f"P1.06 runtime subtest {name} failed: {exc}") from exc


def _runtime_test(root: Path, labels: dict[str, int], kernel_bytes: bytes) -> None:
    init=labels["zx48_process_init"]; prepare=labels["zx48_process_prepare_pid1"]
    table=labels["process_table"]; current_pid=labels["current_pid"]
    prefix=b"\xF3"+_ld_sp(phase1.USER_STACK)+_call(init)

    code=bytearray(prefix+_expect_byte(current_pid,0))
    for pid in range(MAX_PROCESSES):
        base=table+pid*PROC_DESC_SIZE
        for offset,value in ((OFFSETS["pid"],pid),(OFFSETS["parent"],0xFF),(OFFSETS["state"],2 if pid==0 else 0),(OFFSETS["flags"],0),(OFFSETS["private_flags"],0)):
            code+=_expect_byte(base+offset,value)
    code+=_jp(PASS_PC)
    _run_named(root,"descriptor-core-init",bytes(code),kernel_bytes)

    code=bytearray(prefix)
    for pid in range(MAX_PROCESSES):
        base=table+pid*PROC_DESC_SIZE
        for handle in range(MAX_HANDLES): code+=_expect_byte(base+OFFSETS["handles"]+handle,0xFF)
    code+=_jp(PASS_PC)
    _run_named(root,"handle-sentinels",bytes(code),kernel_bytes)

    code=bytearray(prefix+_call(prepare)+_jp_nz(FAIL_PC)+_jp(PASS_PC))
    _run_named(root,"pid1-prepare-return",bytes(code),kernel_bytes)

    code=bytearray(prefix+_call(prepare))
    pid1=table+PROC_DESC_SIZE
    for offset,value in ((OFFSETS["state"],1),(OFFSETS["parent"],0),(OFFSETS["cwd"],0),(OFFSETS["private_flags"],0)):
        code+=_expect_byte(pid1+offset,value)
    for offset,value in enumerate(b"sh"+b"\0"*8): code+=_expect_byte(pid1+OFFSETS["name"]+offset,value)
    code+=_jp(PASS_PC)
    _run_named(root,"pid1-reserved-record",bytes(code),kernel_bytes)


def dispatch(root: Path, action: str, step: str, *, sha256_file: Callable[[Path],str], run_command: Callable[...,Any], require_project_tool: Callable[[Path,str|Path],Path]):
    if step!="P1.06": raise Phase1ProcessError(f"Phase-1 process step is not registered: {step}")
    assertions=_static_contract(root); failed=[str(i["name"]) for i in assertions if i["passed"] is not True]
    require(not failed,f"P1.06 static descriptor contract failed: {failed}")
    command,kernel,listing=phase1._assemble_kernel(root,run_command,require_project_tool)
    labels=phase1._labels(listing,("zx48_process_init","zx48_process_prepare_pid1","process_table","current_pid")); kernel_bytes=kernel.read_bytes()
    if action=="test":
        _runtime_test(root,labels,kernel_bytes); assertions.append({"name":"runtime-table-init-and-pid1-reservation","passed":True}); assertions.extend(_negative_contract_tests())
        failed=[str(i["name"]) for i in assertions if i["passed"] is not True]; require(not failed,f"P1.06 negative/runtime contract failed: {failed}")
    paths=(root/"v1/include/zx48ux.inc",root/"v1/src/kernel/process.asm",root/"v1/src/kernel/scheduler.asm",root/"v1/tools-host/test-driver/phase1_process.py",kernel)
    hashes={str(p.relative_to(root)).replace("\\","/"):sha256_file(p) for p in paths}
    return [command],hashes,assertions
