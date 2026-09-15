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
import phase2_exec_runtime


class Phase2ExecError(DriverError):
    """Raised when the P2.12 atomic exec contract regresses."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Phase2ExecError(message)


def _static(root: Path) -> list[dict[str, Any]]:
    process = (root / "v1/src/kernel/process.asm").read_text(encoding="utf-8")
    start = process.index("    MACRO EMIT_EXEC_TRANSACTION_ROUTINES")
    end = process.index("    ENDM\n", start)
    source = process[start:end]
    checks = {
        "exec consumes PROC1 through staged syscall entry": "zx48_sys_exec:" in source and "PROC1_SIZE" in source,
        "exec requires all std selector bytes to be 0xFF": all(token in source for token in ("PROC1_STDIN_HANDLE", "PROC1_STDOUT_HANDLE", "PROC1_STDERR_HANDLE", "cp HANDLE_FREE")),
        "exec preserves descriptor identity fields by excluding them from commit": all(token not in source.split("; Commit contains no fallible operation.", 1)[-1].split("; Only after publication", 1)[0] for token in ("PROC_PID", "PROC_PARENT", "PROC_HANDLES", "PROC_CWD")),
        "ARG1 validates before replacement allocation": source.index("call zx48_arg1_validate") < source.index("call zx48_alloc"),
        "ENV1 validates before replacement allocation": source.index("call zx48_env1_validate") < source.index("call zx48_alloc"),
        "old image release follows descriptor commit": source.index("ld (ix+PROC_IMAGE_BASE),l") < source.index("ld hl,(process_exec_old_image)"),
        "wrong object type is E_FORMAT": "cp OBJ_BIN" in source and "zx48_process_exec_format:" in source,
        "ALLOW_TAPE is the sole admitted PROC1 flag": "and $FE" in source,
        "successful exec restores new frame instead of old syscall return": all(token in source for token in ("ld sp,hl", "pop ix", "pop hl", "pop de", "pop bc", "pop af", "ld iy,ROM_IY_ANCHOR", "ret")),
        "failure rollback frees only private replacement allocations": all(token in source for token in ("zx48_process_exec_rollback:", "process_exec_bootstrap_base", "process_exec_stack_base", "process_exec_image_base")),
    }
    return [{"name": name, "passed": bool(passed)} for name, passed in checks.items()]


def _assemble(root: Path, run_command: Callable[..., Any], require_project_tool: Callable[[Path, str | Path], Path]):
    assembler = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    fixture = build / "p212-exec-syntax.asm"
    fixture.write_text(
        "    DEVICE ZXSPECTRUM48\n"
        "    INCLUDE \"../include/zx48ux.inc\"\n"
        "    INCLUDE \"../include/mex1.inc\"\n"
        "    INCLUDE \"../src/kernel/syscall.asm\"\n"
        "    INCLUDE \"../src/kernel/memory.asm\"\n"
        "    INCLUDE \"../src/kernel/process.asm\"\n"
        "    INCLUDE \"../src/kernel/handles.asm\"\n"
        "    INCLUDE \"../src/kernel/objects.asm\"\n"
        "PANIC_SCHEDULER EQU $03\n"
        "    ORG $6000\n"
        "    EMIT_MEMORY_ROUTINES\n"
        "    EMIT_USER_RANGE_VALIDATION_ROUTINE\n"
        "    EMIT_PROCESS_CAPACITY_ROUTINE\n"
        "    EMIT_MEX1_RELOCATION_ROUTINES\n"
        "    EMIT_ARG1_ROUTINES\n"
        "    EMIT_ENV1_ROUTINES\n"
        "    EMIT_INITIAL_CONTEXT_ROUTINES\n"
        "    EMIT_SPAWN_TRANSACTION_ROUTINES\n"
        "    EMIT_EXEC_TRANSACTION_ROUTINES\n"
        "zx48_process_count: xor a : ret\n"
        "zx48_process_lookup: xor a : ret\n"
        "zx48_handle_lookup: ld c,a : xor a : ret\n"
        "zx48_od_retain: xor a : ret\n"
        "zx48_od_release: xor a : ret\n"
        "zx48_spawn_resolve_ram_object: ld ix,$A000 : xor a : ret\n"
        "zx48_pipe_endpoint_closed: xor a : ret\n"
        "zx48_panic: jp $0000\n"
        "syscall_arg_hl: dw 0\n"
        "current_pid: db 1\n"
        "process_table: defs MAX_PROCESSES*PROC_DESC_SIZE,0\n",
        encoding="utf-8", newline="\n")
    result = run_command([assembler, "--nologo", "--lst=p212-exec-syntax.lst", "p212-exec-syntax.asm"], cwd=build, timeout_seconds=30.0)
    require(not result.timed_out and result.exit_code == 0, f"P2.12 staged exec assembly failed: {result.stderr or result.stdout}")
    return result


def dispatch(root: Path, action: str, step: str, **kwargs):
    if step != "P2.12":
        raise Phase2ExecError(f"phase2_exec cannot run {step}")
    run_command = kwargs["run_command"]
    require_project_tool = kwargs["require_project_tool"]
    result = _assemble(root, run_command, require_project_tool)
    assertions = _static(root)
    runtime_result, runtime_binary, runtime_assertions = phase2_exec_runtime.run(
        root,
        execute=action == "test",
        run_command=run_command,
        require_project_tool=require_project_tool,
    )
    assertions.extend(runtime_assertions)
    commands = [
        {"argv": list(result.argv), "cwd": result.cwd, "exit_code": result.exit_code, "timed_out": result.timed_out},
        {"argv": list(runtime_result.argv), "cwd": runtime_result.cwd, "exit_code": runtime_result.exit_code, "timed_out": runtime_result.timed_out},
    ]
    hashes = {
        "v1/src/kernel/process.asm": kwargs["sha256_file"](root / "v1/src/kernel/process.asm"),
        "v1/tools-host/test-driver/phase2_exec.py": kwargs["sha256_file"](root / "v1/tools-host/test-driver/phase2_exec.py"),
        "v1/tools-host/test-driver/phase2_exec_runtime.py": kwargs["sha256_file"](root / "v1/tools-host/test-driver/phase2_exec_runtime.py"),
        "v1/build/p212-exec.bin": kwargs["sha256_file"](runtime_binary),
    }
    return commands, hashes, assertions

# temporary watched-path CI trigger
