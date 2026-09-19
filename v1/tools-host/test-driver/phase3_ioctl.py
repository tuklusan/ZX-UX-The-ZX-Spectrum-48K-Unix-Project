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
from typing import Any, Callable

from driver_core import DriverError
from fuse_harness import FAIL_PC, PASS_PC, run_sna
import phase1
import phase3_open_descriptions
import phase3_tty

IOCTL_REC = 0xA200
IOCTL_ARG = 0xA210
CANARY = 0xA220

class Phase3IoctlError(DriverError):
    """Raised when the P3.20 SYS_IOCTL / IOCTL1 contract regresses."""

def require(condition: bool, message: str) -> None:
    if not condition:
        raise Phase3IoctlError(message)

def w(value: int) -> bytes:
    return bytes((value & 0xFF, (value >> 8) & 0xFF))

def jp_nc(address: int) -> bytes:
    return b"\xD2" + w(address)

def store(address: int, value: int) -> bytes:
    return bytes((0x3E, value & 0xFF, 0x32)) + w(address)

def load(address: int) -> bytes:
    return b"\x3A" + w(address)

def expect_error(code: bytearray, error: int) -> None:
    code += jp_nc(FAIL_PC) + bytes((0xFE, error & 0xFF)) + phase1._jp_nz(FAIL_PC)

def expect_byte(code: bytearray, address: int, value: int) -> None:
    code += load(address) + bytes((0xFE, value & 0xFF)) + phase1._jp_nz(FAIL_PC)

def set_record(code: bytearray, handle: int, request: int, arg_ptr: int) -> None:
    code += store(IOCTL_REC + 0, handle)
    code += store(IOCTL_REC + 1, request)
    code += store(IOCTL_REC + 2, arg_ptr & 0xFF)
    code += store(IOCTL_REC + 3, (arg_ptr >> 8) & 0xFF)

def ioctl(code: bytearray, s: dict[str, int], handle: int, request: int, arg_ptr: int) -> None:
    set_record(code, handle, request, arg_ptr)
    phase3_tty._call_sys(code, s, s["SYS_IOCTL"], IOCTL_REC, 0, 0)

def ok(code: bytearray) -> None:
    code += phase1._jp_c(FAIL_PC) + b"\x7C\xB5" + phase1._jp_nz(FAIL_PC)

def create_handle(code: bytearray, s: dict[str, int], handle: int, kind: int, identity: int = 0) -> None:
    code += bytes((0x06, kind & 0xFF, 0x0E, (s["O_READ"] | s["O_WRITE"]) & 0xFF, 0x16, identity & 0xFF))
    code += phase1._call(s["zx48_od_create"]) + phase1._jp_c(FAIL_PC)
    code += b"\x4F" + bytes((0x3E, handle & 0xFF)) + phase1._call(s["zx48_handle_install"])
    code += phase1._jp_c(FAIL_PC) + bytes((0xFE, handle & 0xFF)) + phase1._jp_nz(FAIL_PC)

def setup(code: bytearray, s: dict[str, int]) -> None:
    code += phase1._call(s["zx48_process_init"])
    code += phase1._call(s["zx48_handles_init"])
    code += phase1._call(s["zx48_console_init"])
    code += phase1._call(s["zx48_process_prepare_pid1"])
    code += store(s["current_pid"], 1) + store(s["tty_input_owner"], 1)
    create_handle(code, s, 0, s["OD_KIND_TTY"])
    create_handle(code, s, 1, s["OD_KIND_NULL"])
    create_handle(code, s, 2, s["OD_KIND_TAPE"])
    pid2_state = s["process_table"] + 2 * s["PROC_DESC_SIZE"] + s["PROC_STATE"]
    code += store(pid2_state, s["PROC_READY"])

def source_contract(root: Path) -> list[dict[str, object]]:
    syscall=(root/"v1/src/kernel/syscall.asm").read_text(encoding="utf-8")
    console=(root/"v1/src/kernel/console.asm").read_text(encoding="utf-8")
    process=(root/"v1/src/kernel/process.asm").read_text(encoding="utf-8")
    block=syscall[syscall.index("zx48_sys_ioctl:"):syscall.index("zx48_sys_con_getkey:")]
    tty=console[console.index("TTY_REQ_GET_MODE"):console.index("CONSOLE_STATE_BASE")]
    impl=console[console.index("zx48_tty_ioctl:"):console.index("    ENDM",console.index("zx48_tty_ioctl:"))]
    return [
      {"name":"ioctl1-is-exact-packed-four-byte-record","passed":"HL -> IOCTL1 {handle,request,u16 arg_ptr}" in block and "ld bc,4" in block},
      {"name":"complete-ioctl1-range-precedes-handle-record-dereference","passed":block.index("call zx48_user_range_validate") < block.index("ld a,(hl)") < block.index("call zx48_handle_lookup")},
      {"name":"tty-kind-gate-precedes-request-dispatch","passed":block.index("cp OD_KIND_TTY") < block.index("cp TTY_REQ_GET_MODE")},
      {"name":"pointed-range-validated-before-tty-action","passed":block.index("call zx48_user_range_validate",block.index("zx48_sys_ioctl_arg:")) < block.index("call zx48_tty_ioctl")},
      {"name":"all-seven-request-ids-frozen-literal-01-through-07","passed":all(f"TTY_REQ_{n}" in tty for n in ("GET_MODE","SET_MODE","GET_SIZE","SET_CURSOR","GET_CURSOR","GET_OWNER","SET_OWNER")) and all(f"EQU {i}" in tty for i in range(1,8))},
      {"name":"get-size-is-only-two-byte-pointed-record","passed":"cp TTY_REQ_GET_SIZE\n    jr nz,zx48_sys_ioctl_arg\n    inc bc" in block},
      {"name":"unknown-tty-request-is-enotsup","passed":"ld a,E_NOTSUP\n    scf\n    ret" in impl},
      {"name":"set-owner-is-pid1-only-and-nonzero-owner-must-be-live","passed":"cp 1\n    jr nz,zx48_tty_perm" in impl and "call zx48_process_live_lookup" in impl},
      {"name":"owner-exit-restores-live-pid1-or-pid0","passed":"zx48_process_restore_tty_owner:" in process and "call zx48_process_live_lookup" in process and "zx48_process_tty_owner_zero:" in process},
      {"name":"ioctl-nontty-path-has-no-tape-motion","passed":"tape" not in block.lower()},
    ]

def target_matrix(root: Path, s: dict[str, int], kernel: bytes) -> None:
    code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0))
    setup(code,s)
    code += store(IOCTL_ARG+0,0xA5)+store(IOCTL_ARG+1,0x5A)+store(IOCTL_ARG+2,0xC3)

    # 01 GET_MODE: writable u8 only.
    ioctl(code,s,0,s["TTY_REQ_GET_MODE"],IOCTL_ARG); ok(code)
    expect_byte(code,IOCTL_ARG,s["TTY_MODE_64"]); expect_byte(code,IOCTL_ARG+1,0x5A)

    # 02 SET_MODE: readable u8, exact 32/64 values.
    code += store(IOCTL_ARG,s["TTY_MODE_32"])
    ioctl(code,s,0,s["TTY_REQ_SET_MODE"],IOCTL_ARG); ok(code)
    expect_byte(code,s["tty_mode"],s["TTY_MODE_32"])
    code += store(IOCTL_ARG,s["TTY_MODE_64"])
    ioctl(code,s,0,s["TTY_REQ_SET_MODE"],IOCTL_ARG); ok(code)
    expect_byte(code,s["tty_mode"],s["TTY_MODE_64"])

    # 03 GET_SIZE: exactly two writable bytes: cols,24.
    code += store(IOCTL_ARG,0xA5)+store(IOCTL_ARG+1,0x5A)+store(IOCTL_ARG+2,0xC3)
    ioctl(code,s,0,s["TTY_REQ_GET_SIZE"],IOCTL_ARG); ok(code)
    expect_byte(code,IOCTL_ARG,s["TTY_MODE_64"]); expect_byte(code,IOCTL_ARG+1,24); expect_byte(code,IOCTL_ARG+2,0xC3)

    # 04/05 cursor shape: all exact values 0/1/2.
    for shape in (0,1,2):
        code += store(IOCTL_ARG,shape)
        ioctl(code,s,0,s["TTY_REQ_SET_CURSOR"],IOCTL_ARG); ok(code)
        expect_byte(code,s["tty_cursor_shape"],shape)
        code += store(IOCTL_ARG,0xA5)+store(IOCTL_ARG+1,0x5A)
        ioctl(code,s,0,s["TTY_REQ_GET_CURSOR"],IOCTL_ARG); ok(code)
        expect_byte(code,IOCTL_ARG,shape); expect_byte(code,IOCTL_ARG+1,0x5A)

    # 06 GET_INPUT_OWNER.
    code += store(IOCTL_ARG,0xA5)+store(IOCTL_ARG+1,0x5A)
    ioctl(code,s,0,s["TTY_REQ_GET_OWNER"],IOCTL_ARG); ok(code)
    expect_byte(code,IOCTL_ARG,1); expect_byte(code,IOCTL_ARG+1,0x5A)

    # 07 SET_INPUT_OWNER: PID1 may assign live PID2 and PID0.
    code += store(IOCTL_ARG,2)
    ioctl(code,s,0,s["TTY_REQ_SET_OWNER"],IOCTL_ARG); ok(code)
    expect_byte(code,s["tty_input_owner"],2)
    code += store(IOCTL_ARG,0)
    ioctl(code,s,0,s["TTY_REQ_SET_OWNER"],IOCTL_ARG); ok(code)
    expect_byte(code,s["tty_input_owner"],0)

    # Dead nonzero PID is E_NOENT and leaves owner unchanged.
    code += store(IOCTL_ARG,3)
    ioctl(code,s,0,s["TTY_REQ_SET_OWNER"],IOCTL_ARG); expect_error(code,s["E_NOENT"])
    expect_byte(code,s["tty_input_owner"],0)

    # Non-PID1 cannot set owner.
    code += store(s["current_pid"],2)+store(IOCTL_ARG,2)
    ioctl(code,s,0,s["TTY_REQ_SET_OWNER"],IOCTL_ARG); expect_error(code,s["E_PERM"])
    expect_byte(code,s["tty_input_owner"],0)
    code += store(s["current_pid"],1)

    # Unknown request, invalid handle, NULL and TAPE are exact no-side-effect errors.
    code += store(s["tty_mode"],s["TTY_MODE_64"])+store(s["tty_cursor_shape"],2)+store(s["tty_input_owner"],1)
    ioctl(code,s,0,8,IOCTL_ARG); expect_error(code,s["E_NOTSUP"])
    ioctl(code,s,7,s["TTY_REQ_GET_MODE"],IOCTL_ARG); expect_error(code,s["E_NOENT"])
    ioctl(code,s,1,s["TTY_REQ_GET_MODE"],IOCTL_ARG); expect_error(code,s["E_NOTSUP"])
    ioctl(code,s,2,s["TTY_REQ_GET_MODE"],IOCTL_ARG); expect_error(code,s["E_NOTSUP"])
    expect_byte(code,s["tty_mode"],s["TTY_MODE_64"]); expect_byte(code,s["tty_cursor_shape"],2); expect_byte(code,s["tty_input_owner"],1)

    # Malformed packing: swapped handle/request resolves to NULL and is rejected.
    set_record(code,s["TTY_REQ_GET_MODE"],0,IOCTL_ARG)
    phase3_tty._call_sys(code,s,s["SYS_IOCTL"],IOCTL_REC,0,0); expect_error(code,s["E_NOTSUP"])
    expect_byte(code,s["tty_mode"],s["TTY_MODE_64"])

    # Complete IOCTL1 and request-specific pointed ranges fail before side effect.
    phase3_tty._call_sys(code,s,s["SYS_IOCTL"],0xDFFE,0,0); expect_error(code,s["E_INVAL"])
    code += store(s["tty_mode"],s["TTY_MODE_64"])
    ioctl(code,s,0,s["TTY_REQ_SET_MODE"],0xE000); expect_error(code,s["E_INVAL"])
    expect_byte(code,s["tty_mode"],s["TTY_MODE_64"])
    ioctl(code,s,0,s["TTY_REQ_GET_SIZE"],0xDFFF); expect_error(code,s["E_INVAL"])
    expect_byte(code,s["tty_mode"],s["TTY_MODE_64"])

    # Invalid request-specific values are exact E_INVAL and atomic.
    code += store(IOCTL_ARG,33)
    ioctl(code,s,0,s["TTY_REQ_SET_MODE"],IOCTL_ARG); expect_error(code,s["E_INVAL"])
    expect_byte(code,s["tty_mode"],s["TTY_MODE_64"])
    code += store(IOCTL_ARG,3)
    ioctl(code,s,0,s["TTY_REQ_SET_CURSOR"],IOCTL_ARG); expect_error(code,s["E_INVAL"])
    expect_byte(code,s["tty_cursor_shape"],2)

    # Owner-exit restoration helper: live PID1, then absent PID1 -> PID0.
    code += store(s["current_pid"],1)+store(IOCTL_ARG,2)
    ioctl(code,s,0,s["TTY_REQ_SET_OWNER"],IOCTL_ARG); ok(code)
    code += store(s["current_pid"],2)+phase1._call(s["zx48_process_restore_tty_owner"])
    expect_byte(code,s["tty_input_owner"],1)
    code += store(s["current_pid"],1)+store(IOCTL_ARG,2)
    ioctl(code,s,0,s["TTY_REQ_SET_OWNER"],IOCTL_ARG); ok(code)
    pid1_state=s["process_table"]+s["PROC_DESC_SIZE"]+s["PROC_STATE"]
    code += store(pid1_state,0)+store(s["current_pid"],2)+phase1._call(s["zx48_process_restore_tty_owner"])
    expect_byte(code,s["tty_input_owner"],0)

    code += phase1._jp(PASS_PC)
    run_sna(root,bytes(code),patch=phase1._kernel_patch(kernel))

def dispatch(root: Path, action: str, step: str, *, sha256_file: Callable[[Path],str], run_command: Callable[...,Any], require_project_tool: Callable[[Path,str|Path],Path]):
    if step!="P3.20":
        raise DriverError(f"Phase-3 IOCTL step is not registered: {step}")
    assertions=source_contract(root)
    failed=[x["name"] for x in assertions if x["passed"] is not True]
    require(not failed,f"static P3.20 contract failures: {failed}")
    result,kernel,listing=phase1._assemble_kernel(root,run_command,require_project_tool)
    s=phase3_open_descriptions._symbols(listing.with_suffix(".sym"),(
      "zx48_process_init","zx48_handles_init","zx48_console_init","zx48_process_prepare_pid1",
      "zx48_process_restore_tty_owner","zx48_od_create","zx48_handle_install","zx48_syscall_impl",
      "current_pid","process_table","tty_input_owner","tty_mode","tty_cursor_shape",
      "PROC_DESC_SIZE","PROC_STATE","PROC_READY","OD_KIND_TTY","OD_KIND_NULL","OD_KIND_TAPE",
      "O_READ","O_WRITE","SYS_IOCTL","E_INVAL","E_NOENT","E_NOTSUP","E_PERM",
      "TTY_MODE_32","TTY_MODE_64","TTY_REQ_GET_MODE","TTY_REQ_SET_MODE","TTY_REQ_GET_SIZE",
      "TTY_REQ_SET_CURSOR","TTY_REQ_GET_CURSOR","TTY_REQ_GET_OWNER","TTY_REQ_SET_OWNER",
    ))
    require([s[f"TTY_REQ_{n}"] for n in ("GET_MODE","SET_MODE","GET_SIZE","SET_CURSOR","GET_CURSOR","GET_OWNER","SET_OWNER")]==list(range(1,8)),"P3.20 request IDs changed")
    if action=="test":
        target_matrix(root,s,kernel.read_bytes())
        assertions += [
          {"name":"tty-request-01-get-mode-u8-exact","passed":True},
          {"name":"tty-request-02-set-mode-u8-32-64-exact","passed":True},
          {"name":"tty-request-03-get-size-two-bytes-cols-rows-exact","passed":True},
          {"name":"tty-request-04-05-cursor-shape-0-1-2-exact","passed":True},
          {"name":"tty-request-06-get-owner-u8-exact","passed":True},
          {"name":"tty-request-07-set-owner-pid1-live-pid-and-zero-exact","passed":True},
          {"name":"dead-owner-nonpid1-unknown-invalid-null-tape-errors-exact","passed":True},
          {"name":"ioctl1-packing-mutation-rejected-without-state-change","passed":True},
          {"name":"whole-record-and-pointed-range-invalid-before-side-effect","passed":True},
          {"name":"invalid-mode-and-cursor-values-atomic-einval","passed":True},
          {"name":"owner-exit-restores-live-pid1-else-pid0","passed":True},
        ]
    return [result],{
      "v1/build/kernel.bin":sha256_file(kernel),
      "v1/src/kernel/syscall.asm":sha256_file(root/"v1/src/kernel/syscall.asm"),
      "v1/src/kernel/handles.asm":sha256_file(root/"v1/src/kernel/handles.asm"),
      "v1/src/kernel/console.asm":sha256_file(root/"v1/src/kernel/console.asm"),
      "v1/src/kernel/process.asm":sha256_file(root/"v1/src/kernel/process.asm"),
      "v1/tools-host/test-driver/phase3_ioctl.py":sha256_file(root/"v1/tools-host/test-driver/phase3_ioctl.py"),
      "v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
      "v1/dist/certification/P3.19.test.json":sha256_file(root/"v1/dist/certification/P3.19.test.json"),
    },assertions
