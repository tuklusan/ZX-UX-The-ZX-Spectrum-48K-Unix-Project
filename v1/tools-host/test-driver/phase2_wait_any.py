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
import phase2_wait_any_runtime


class Phase2WaitAnyError(DriverError):
    """Raised when the P2.16 wait-any contract regresses."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Phase2WaitAnyError(message)


def _symbols(path: Path, names: tuple[str, ...]) -> dict[str, int]:
    text = path.read_text(encoding="utf-8", errors="replace")
    found: dict[str, int] = {}
    for name in names:
        pattern = re.compile(
            rf"^{re.escape(name)}:\s+equ\s+0x([0-9A-Fa-f]+)\s*$",
            re.IGNORECASE | re.MULTILINE,
        )
        match = pattern.search(text)
        require(match is not None, f"P2.16 symbol missing from assembler output: {name}")
        found[name] = int(match.group(1), 16)
    return found


def _assemble_kernel(
    root: Path,
    run_command: Callable[..., Any],
    require_project_tool: Callable[[Path, str | Path], Path],
):
    assembler = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    result = run_command(
        [assembler, "--nologo", "--lst=../../build/kernel-p216.lst", "--sym=../../build/kernel-p216.sym", "kernel.asm"],
        cwd=root / "v1/src/kernel",
        timeout_seconds=30.0,
    )
    require(
        not result.timed_out and result.exit_code == 0,
        f"P2.16 resident kernel assembly failed: {result.stderr or result.stdout}",
    )
    binary = build / "kernel.bin"
    symbols = build / "kernel-p216.sym"
    require(binary.is_file() and binary.stat().st_size == 8192, "P2.16 resident kernel must remain exactly 8192 bytes")
    require(symbols.is_file(), "P2.16 resident kernel symbols missing")
    return result, binary, symbols


def _macro(text: str, name: str) -> str:
    marker = f"    MACRO {name}"
    try:
        start = text.index(marker)
        end = text.index("    ENDM\n", start)
    except ValueError as exc:
        raise Phase2WaitAnyError(f"P2.16 cannot locate macro {name}") from exc
    return text[start:end]


def _source_contract(root: Path) -> list[dict[str, object]]:
    process = (root / "v1/src/kernel/process.asm").read_text(encoding="utf-8")
    wait_any = _macro(process, "EMIT_WAIT_ANY_ROUTINES")
    zombie = _macro(process, "EMIT_ZOMBIE_TRANSITION_ROUTINES")
    p215 = _macro(process, "EMIT_WAIT_SPECIFIC_ROUTINES")

    scan_start = wait_any.index("zx48_process_wait_any_scan:")
    block_start = wait_any.index("zx48_process_wait_any_block:")
    reap_start = wait_any.index("zx48_process_wait_any_reap:")
    none_start = wait_any.index("zx48_process_wait_any_none:")
    scan = wait_any[scan_start:block_start]
    reap = wait_any[reap_start:none_start]

    return [
        {
            "name": "p216-is-separate-staged-emitter-after-p215",
            "passed": "ZX48_P2_16_WAIT_ANY_EMITTED EQU 1" in wait_any
            and process.index("    MACRO EMIT_WAIT_SPECIFIC_ROUTINES") < process.index("    MACRO EMIT_WAIT_ANY_ROUTINES"),
        },
        {
            "name": "wait-any-accepts-only-minus-one-entry-token",
            "passed": "zx48_process_wait:\n    cp $ff" in wait_any and "ld a,E_CHILD" in wait_any,
        },
        {
            "name": "wait-any-reuses-p215-validated-status-pointer-side-metadata",
            "passed": "zx48_process_wait_status_ptr_slot" in wait_any
            and "process_wait_status_ptr: defs MAX_PROCESSES*2,0" in p215,
        },
        {
            "name": "wait-any-scan-is-deterministic-lowest-pid-first",
            "passed": "ld a,2" in scan
            and "ld (process_wait_any_candidate_pid),a" in scan
            and "cp MAX_PROCESSES" in scan
            and scan.index("call zx48_process_wait_any_match") < scan.index("cp PROC_ZOMBIE"),
        },
        {
            "name": "wait-any-child-membership-is-parent-generation-qualified",
            "passed": all(
                token in wait_any
                for token in (
                    "call zx48_process_generation_get",
                    "call zx48_process_parent_generation_ptr",
                    "call zx48_process_pid_bit",
                    "call zx48_process_child_mask_ptr",
                    "process_wait_any_parent_generation",
                )
            ),
        },
        {
            "name": "wait-any-reaps-zombie-before-blocking",
            "passed": "cp PROC_ZOMBIE" in scan
            and "jp z,zx48_process_wait_any_reap" in scan
            and scan.index("cp PROC_ZOMBIE") < wait_any.index("zx48_process_wait_any_block:"),
        },
        {
            "name": "wait-any-block-installs-dedicated-resume-continuation-before-wait-state",
            "passed": "ld de,zx48_syscall_resume_wait_any" in wait_any
            and wait_any.index("ld de,zx48_syscall_resume_wait_any") < wait_any.index("ld (ix+PROC_STATE),PROC_WAIT_CHILD"),
        },
        {
            "name": "wait-any-wake-bypasses-specific-child-filter-only-when-any-flag-is-set",
            "passed": "IFDEF ZX48_P2_16_WAIT_ANY_ENABLED" in zombie
            and "call zx48_process_wait_any_flag_ptr" in zombie
            and "jr nz,zx48_process_zombie_wake_ready" in zombie
            and zombie.index("call zx48_process_wait_any_flag_ptr") < zombie.index("call zx48_process_zombie_wait_specific_match"),
        },
        {
            "name": "wait-any-copies-status-before-unlink-and-descriptor-reclaim",
            "passed": "ld (de),a" in reap
            and "call zx48_process_wait_specific_release" in reap
            and reap.index("ld (de),a") < reap.index("call zx48_process_wait_specific_release"),
        },
        {
            "name": "wait-any-reuses-generation-safe-p215-release",
            "passed": "call zx48_process_wait_specific_release" in reap
            and "call zx48_process_unlink_child" in p215
            and "ld bc,PROC_DESC_SIZE-1" in p215,
        },
        {
            "name": "wait-any-success-and-no-child-clear-continuation-metadata",
            "passed": "zx48_process_wait_any_clear:" in wait_any
            and "ld (hl),0" in wait_any[wait_any.index("zx48_process_wait_any_clear:") :]
            and "call zx48_process_wait_specific_clear" in wait_any[wait_any.index("zx48_process_wait_any_clear:") :],
        },
        {
            "name": "wait-any-no-child-fails-echild-without-status-write",
            "passed": "zx48_process_wait_any_none:" in wait_any
            and "call zx48_process_wait_any_clear" in wait_any[none_start:]
            and "ld a,E_CHILD" in wait_any[none_start:],
        },
    ]


def dispatch(
    root: Path,
    action: str,
    step: str,
    *,
    sha256_file: Callable[[Path], str],
    run_command: Callable[..., Any],
    require_project_tool: Callable[[Path, str | Path], Path],
):
    if step != "P2.16":
        raise DriverError(f"Phase-2 wait-any step is not registered: {step}")

    assertions = _source_contract(root)
    failed = [item["name"] for item in assertions if item.get("passed") is not True]
    require(not failed, f"static P2.16 contract failures: {failed}")

    kernel_command, kernel_binary, kernel_symbols = _assemble_kernel(root, run_command, require_project_tool)
    kernel_values = _symbols(kernel_symbols, ("kernel_ordinary_used_end", "KERNEL_CODE_END"))
    free_bytes = kernel_values["KERNEL_CODE_END"] + 1 - kernel_values["kernel_ordinary_used_end"]
    require(free_bytes >= 0, "P2.16 resident ordinary kernel exceeds hard ceiling")
    assertions.append(
        {
            "name": "resident-kernel-ordinary-code-remains-within-faff-ceiling",
            "passed": True,
            "used_end": f"0x{kernel_values['kernel_ordinary_used_end']:04X}",
            "code_end": f"0x{kernel_values['KERNEL_CODE_END']:04X}",
            "free_bytes": free_bytes,
        }
    )

    runtime_command, runtime_binary, runtime_assertions = phase2_wait_any_runtime.run(
        root,
        execute=action == "test",
        runner=run_command,
        project_tool=require_project_tool,
    )
    assertions.extend(runtime_assertions)

    return [kernel_command, runtime_command], {
        "v1/build/kernel.bin": sha256_file(kernel_binary),
        "v1/build/p216-wait-any.bin": sha256_file(runtime_binary),
        "v1/src/kernel/process.asm": sha256_file(root / "v1/src/kernel/process.asm"),
        "v1/tools-host/test-driver/phase2_wait_any.py": sha256_file(root / "v1/tools-host/test-driver/phase2_wait_any.py"),
        "v1/tools-host/test-driver/phase2_wait_any_runtime.py": sha256_file(root / "v1/tools-host/test-driver/phase2_wait_any_runtime.py"),
        "v1/tools-host/test-driver/run.py": sha256_file(root / "v1/tools-host/test-driver/run.py"),
        "v1/tools-host/test-driver/phase2_gate.py": sha256_file(root / "v1/tools-host/test-driver/phase2_gate.py"),
    }, assertions
