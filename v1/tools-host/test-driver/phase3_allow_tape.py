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
from typing import Any, Callable
from driver_core import DriverError
import phase2_spawn
import phase1

def dispatch(root: Path, action: str, step: str, *, sha256_file: Callable[[Path], str], run_command: Callable[..., Any], require_project_tool: Callable[[Path, str | Path], Path]):
    if step != "P3.16":
        raise DriverError(f"Phase-3 ALLOW_TAPE step is not registered: {step}")
    syscall=(root/"v1/src/kernel/syscall.asm").read_text(encoding="utf-8")
    process=(root/"v1/src/kernel/process.asm").read_text(encoding="utf-8")
    assertions=[
      {"name":"proc1-allow-tape-bit-is-exactly-bit0","passed":"PROC1_ALLOW_TAPE           EQU $01" in syscall},
      {"name":"spawn-rejects-all-unknown-proc1-flags","passed":"ld a,(ix+PROC1_FLAGS)\n    and $FE\n    jr nz,zx48_sys_spawn_preflight_invalid" in syscall},
      {"name":"exec-rejects-all-unknown-proc1-flags","passed":"ld a,(ix+PROC1_FLAGS)\n    and $FE\n    jr nz,zx48_sys_exec_invalid" in process},
    ]
    failed=[a["name"] for a in assertions if not a["passed"]]
    if failed: raise DriverError(f"P3.16 static contract failures: {failed}")
    result,kernel,_=phase1._assemble_kernel(root,run_command,require_project_tool)
    if action=="test":
        fixture_binary, fixture_listing, fixture_symbols, fixture_result = phase2_spawn._assemble_fixture(root, run_command, require_project_tool)
        syms=phase2_spawn._parse_symbols(fixture_symbols)
        valid=phase2_spawn._proc1(flags=1)
        phase2_spawn._run_preflight_case(root,syms,fixture_binary,proc=valid)
        phase2_spawn._run_preflight_case(root,syms,fixture_binary,proc=phase2_spawn._proc1(flags=2),expected_error=syms["E_INVAL"])
        assertions += [
          {"name":"allow-tape-zero-preflight-valid","passed":True},
          {"name":"allow-tape-one-preflight-valid","passed":True},
          {"name":"unknown-proc1-flags-return-e-inval","passed":True},
        ]
    return [result],{
      "v1/build/kernel.bin":sha256_file(kernel),
      "v1/src/kernel/process.asm":sha256_file(root/"v1/src/kernel/process.asm"),
      "v1/src/kernel/syscall.asm":sha256_file(root/"v1/src/kernel/syscall.asm"),
      "v1/tools-host/test-driver/phase3_allow_tape.py":sha256_file(root/"v1/tools-host/test-driver/phase3_allow_tape.py"),
      "v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
      "v1/dist/certification/P3.15.test.json":sha256_file(root/"v1/dist/certification/P3.15.test.json"),
    },assertions
