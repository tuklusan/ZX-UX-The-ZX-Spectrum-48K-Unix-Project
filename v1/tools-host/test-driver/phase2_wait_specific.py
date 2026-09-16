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


class Phase2WaitSpecificError(DriverError):
    """Raised when P2.15 specific-child WAIT instrumentation cannot run."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Phase2WaitSpecificError(message)


def _symbols(path: Path, names: tuple[str, ...]) -> dict[str, int]:
    text = path.read_text(encoding="utf-8", errors="replace")
    found: dict[str, int] = {}
    for name in names:
        pattern = re.compile(
            rf"^{re.escape(name)}:\s+equ\s+0x([0-9A-Fa-f]+)\s*$",
            re.IGNORECASE | re.MULTILINE,
        )
        match = pattern.search(text)
        require(match is not None, f"P2.15 symbol missing from assembler output: {name}")
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
        [assembler, "--nologo", "--lst=../../build/kernel-p215-diag.lst", "--sym=../../build/kernel-p215-diag.sym", "kernel.asm"],
        cwd=root / "v1/src/kernel",
        timeout_seconds=30.0,
    )
    require(
        not result.timed_out and result.exit_code == 0,
        f"P2.15 diagnostic resident kernel assembly failed: {result.stderr or result.stdout}",
    )
    binary = build / "kernel.bin"
    symbols = build / "kernel-p215-diag.sym"
    require(binary.is_file() and binary.stat().st_size == 8192, "P2.15 resident kernel must remain exactly 8192 bytes")
    require(symbols.is_file(), "P2.15 resident kernel diagnostic symbols missing")
    return result, binary, symbols


def _section(text: str, start: str, end: str, *, description: str) -> str:
    try:
        first = text.index(start)
        last = text.index(end, first)
    except ValueError as exc:
        raise Phase2WaitSpecificError(f"P2.15 diagnostic cannot locate {description}") from exc
    return text[first:last]


def _macro(text: str, name: str) -> str:
    marker = f"    MACRO {name}"
    try:
        start = text.index(marker)
        end = text.index("    ENDM\n", start)
    except ValueError as exc:
        raise Phase2WaitSpecificError(f"P2.15 diagnostic cannot locate macro {name}") from exc
    return text[start:end]


def _source_contract(root: Path, *, target: bool) -> list[dict[str, object]]:
    process = (root / "v1/src/kernel/process.asm").read_text(encoding="utf-8")
    syscall = (root / "v1/src/kernel/syscall.asm").read_text(encoding="utf-8")
    scheduler = (root / "v1/src/kernel/scheduler.asm").read_text(encoding="utf-8")

    sys_wait = _section(syscall, "zx48_sys_wait:\n", "zx48_sys_kill:\n", description="SYS_WAIT handler")
    legacy_wait = _section(process, "zx48_process_wait:\n", "process_name_sh:", description="legacy process WAIT helper")
    links = _macro(process, "EMIT_PARENT_CHILD_ROUTINES")
    zombie = _macro(process, "EMIT_ZOMBIE_TRANSITION_ROUTINES")
    scheduler_body = _macro(scheduler, "EMIT_SCHEDULER_ROUTINES")
    wake = _section(
        zombie,
        "zx48_process_zombie_wake_parent:\n",
        "zx48_process_zombie_panic:\n",
        description="P2.14 zombie parent wake",
    )

    status_validate = sys_wait.find("ld bc,1\n    call zx48_user_range_validate")
    process_wait_call = sys_wait.find("call zx48_process_wait")
    baseline = [
        {
            "name": "diagnostic-locates-exact-sys-wait-handler",
            "passed": True,
            "legacy_call_present": process_wait_call >= 0,
        },
        {
            "name": "diagnostic-confirms-status-byte-prevalidation-precedes-current-wait-helper",
            "passed": status_validate >= 0 and process_wait_call >= 0 and status_validate < process_wait_call,
        },
        {
            "name": "diagnostic-locates-p213-generation-qualified-specific-wait-token",
            "passed": all(
                token in links
                for token in (
                    "zx48_process_wait_record_specific:",
                    "zx48_process_wait_matches:",
                    "process_wait_pid: defs MAX_PROCESSES,HANDLE_FREE",
                    "process_wait_generation: defs MAX_PROCESSES*2,0",
                )
            ),
        },
        {
            "name": "diagnostic-locates-p214-zombie-wake-boundary",
            "passed": "cp PROC_WAIT_CHILD" in wake and "ld (ix+PROC_STATE),PROC_READY" in wake,
        },
        {
            "name": "diagnostic-locates-scheduler-frame-continuation-boundary",
            "passed": "zx48_schedule_finish_syscall:" in scheduler_body
            and "zx48_syscall_resume_ok" in scheduler_body
            and "zx48_schedule_restore:" in scheduler_body,
        },
        {
            "name": "diagnostic-locates-current-descriptor-reclaim-boundary",
            "passed": "ld bc,PROC_DESC_SIZE-1" in legacy_wait and "ldir" in legacy_wait,
        },
    ]
    if not target:
        return baseline

    wait_specific = _macro(process, "EMIT_WAIT_SPECIFIC_ROUTINES") if "    MACRO EMIT_WAIT_SPECIFIC_ROUTINES" in process else ""
    resume_specific = "zx48_syscall_resume_wait_specific:" in syscall
    status_storage = "process_wait_status_ptr: defs MAX_PROCESSES*2,0" in wait_specific
    specific_entry = "zx48_process_wait_specific:" in wait_specific
    block_entry = "zx48_process_wait_specific_block:" in wait_specific
    reap_entry = "zx48_process_wait_specific_reap:" in wait_specific
    clear_entry = "zx48_process_wait_specific_clear:" in wait_specific

    target_assertions = [
        {
            "name": "specific-wait-dispatches-to-p215-generation-qualified-path",
            "passed": "call zx48_process_wait_specific" in sys_wait and specific_entry,
        },
        {
            "name": "specific-wait-retains-status-pointer-outside-48-byte-descriptor",
            "passed": status_storage and "PROC_DESC_SIZE" not in wait_specific[wait_specific.find("process_wait_status_ptr:") :],
        },
        {
            "name": "specific-wait-block-records-pid-generation-before-wait-state-publication",
            "passed": block_entry
            and "call zx48_process_wait_record_specific" in wait_specific
            and wait_specific.find("call zx48_process_wait_record_specific") < wait_specific.find("ld (ix+PROC_STATE),PROC_WAIT_CHILD"),
        },
        {
            "name": "blocked-specific-wait-installs-dedicated-syscall-resume-continuation",
            "passed": resume_specific and "zx48_syscall_resume_wait_specific" in wait_specific,
        },
        {
            "name": "zombie-wake-requires-exact-wait-pid-and-generation-match",
            "passed": "zx48_process_zombie_wait_specific_match" in zombie
            and "process_wait_pid" in wake
            and "process_wait_generation" in wake,
        },
        {
            "name": "specific-wait-resume-reloads-retained-status-pointer",
            "passed": resume_specific and "zx48_process_wait_specific_resume" in syscall and status_storage,
        },
        {
            "name": "specific-wait-rechecks-generation-qualified-zombie-before-reap",
            "passed": reap_entry
            and "call zx48_process_wait_matches" in wait_specific
            and "cp PROC_ZOMBIE" in wait_specific,
        },
        {
            "name": "specific-wait-captures-status-before-descriptor-release",
            "passed": reap_entry
            and "PROC_EXIT_STATUS" in wait_specific
            and "zx48_process_wait_specific_release" in wait_specific
            and wait_specific.find("PROC_EXIT_STATUS", wait_specific.find("zx48_process_wait_specific_reap:"))
            < wait_specific.find("zx48_process_wait_specific_release", wait_specific.find("zx48_process_wait_specific_reap:")),
        },
        {
            "name": "specific-wait-release-clears-descriptor-exactly-once",
            "passed": "zx48_process_wait_specific_release:" in wait_specific
            and wait_specific.count("ld bc,PROC_DESC_SIZE-1") == 1,
        },
        {
            "name": "specific-wait-success-clears-pid-generation-status-continuation-metadata",
            "passed": clear_entry
            and "process_wait_pid" in wait_specific[wait_specific.find("zx48_process_wait_specific_clear:") :]
            and "process_wait_generation" in wait_specific[wait_specific.find("zx48_process_wait_specific_clear:") :]
            and "process_wait_status_ptr" in wait_specific[wait_specific.find("zx48_process_wait_specific_clear:") :],
        },
        {
            "name": "specific-wait-invalid-or-nonchild-fails-echild-without-blocking",
            "passed": specific_entry and "ld a,E_CHILD" in wait_specific and "PROC_WAIT_CHILD" in wait_specific,
        },
        {
            "name": "p215-does-not-implement-wait-any",
            "passed": "$ff" not in wait_specific.lower() and "wait_any" not in wait_specific.lower(),
        },
    ]
    return baseline + target_assertions


def dispatch(
    root: Path,
    action: str,
    step: str,
    *,
    sha256_file: Callable[[Path], str],
    run_command: Callable[..., Any],
    require_project_tool: Callable[[Path, str | Path], Path],
):
    if step != "P2.15":
        raise DriverError(f"Phase-2 specific WAIT step is not registered: {step}")

    assertions = _source_contract(root, target=action == "test")
    baseline_failed = [
        item["name"] for item in assertions[:6] if item.get("passed") is not True
    ]
    require(not baseline_failed, f"P2.15 instrumentation baseline failures: {baseline_failed}")

    kernel_command, kernel_binary, kernel_symbols = _assemble_kernel(root, run_command, require_project_tool)
    kernel_values = _symbols(kernel_symbols, ("kernel_ordinary_used_end", "KERNEL_CODE_END"))
    free_bytes = kernel_values["KERNEL_CODE_END"] + 1 - kernel_values["kernel_ordinary_used_end"]
    require(free_bytes >= 0, "P2.15 resident ordinary kernel exceeds hard ceiling")
    assertions.append(
        {
            "name": "resident-kernel-ordinary-code-remains-within-faff-ceiling",
            "passed": True,
            "used_end": f"0x{kernel_values['kernel_ordinary_used_end']:04X}",
            "code_end": f"0x{kernel_values['KERNEL_CODE_END']:04X}",
            "free_bytes": free_bytes,
        }
    )

    return [kernel_command], {
        "v1/build/kernel.bin": sha256_file(kernel_binary),
        "v1/src/kernel/process.asm": sha256_file(root / "v1/src/kernel/process.asm"),
        "v1/src/kernel/syscall.asm": sha256_file(root / "v1/src/kernel/syscall.asm"),
        "v1/src/kernel/scheduler.asm": sha256_file(root / "v1/src/kernel/scheduler.asm"),
        "v1/tools-host/test-driver/phase2_wait_specific.py": sha256_file(root / "v1/tools-host/test-driver/phase2_wait_specific.py"),
        "v1/tools-host/test-driver/run.py": sha256_file(root / "v1/tools-host/test-driver/run.py"),
        "v1/tools-host/test-driver/phase2_gate.py": sha256_file(root / "v1/tools-host/test-driver/phase2_gate.py"),
    }, assertions
