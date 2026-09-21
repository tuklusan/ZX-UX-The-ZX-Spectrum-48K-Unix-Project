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

from driver_core import DriverError
from fuse_harness import FAIL_PC, PASS_PC, run_sna
import phase1
import phase3_open_descriptions


class P629Error(DriverError):
    pass


def require(value, message):
    if not value:
        raise P629Error(message)


def word(value):
    return bytes((value & 0xFF, (value >> 8) & 0xFF))


def setb(address, value):
    return bytes((0x3E, value & 0xFF, 0x32)) + word(address)


def expectb(address, value):
    return b"\x3A" + word(address) + bytes((0xFE, value & 0xFF)) + phase1._jp_nz(FAIL_PC)


def dispatch(root: Path, action: str, step: str, *, sha256_file, run_command, require_project_tool):
    if step != "P6.29":
        raise DriverError(f"Phase-6 PID1 reap/exit step is not registered: {step}")

    shell_path = root / "v1/src/shell/sh.asm"
    process_path = root / "v1/src/kernel/process.asm"
    shell = shell_path.read_text(encoding="utf-8")
    process = process_path.read_text(encoding="utf-8")
    block = shell.split("MACRO EMIT_P629_REAP_EXIT_ROUTINES", 1)[1].split("ENDM", 1)[0]
    exit_block = process.split("zx48_process_exit:", 1)[1].split("zx48_process_wake_parent:", 1)[0]

    assertions = [
        {"name": "prompt-and-jobs-share-reaper",
         "passed": "sh_p629_before_prompt:" in block and "sh_p629_jobs_refresh:" in block and "jp sh_p629_reap" in block},
        {"name": "reaper-scans-exact-pid2-through-pid7",
         "passed": "ld a,2" in block and "cp MAX_PROCESSES" in block and "SYS_PROC_INFO" in block},
        {"name": "zombie-is-waited-immediately",
         "passed": "cp P629_PROC_ZOMBIE" in block and "SYS_WAIT" in block},
        {"name": "job-table-remove-does-not-create-adopted-jobs",
         "passed": "call sh_p624_job_remove" in block and "Adopted" in block},
        {"name": "unexpected-proc-info-error-fails-closed",
         "passed": block.count("cp E_NOENT") >= 2 and "ret nz" in block},
        {"name": "exit-reaps-before-live-scan",
         "passed": block.index("sh_p629_exit:") < block.index("call sh_p629_reap", block.index("sh_p629_exit:")) < block.index("sh_p629_exit_scan:")},
        {"name": "exit-live-child-is-busy",
         "passed": "sh_p629_busy:" in block and "ld a,E_BUSY" in block},
        {"name": "exit-prints-exact-system-halted-before-sys-exit",
         "passed": "p629_halt_text: db 's','y','s','t','e','m',' ','h','a','l','t','e','d'" in block and block.index("SYS_CON_WRITE") < block.index("SYS_EXIT")},
        {"name": "kernel-pid1-exit-is-di-halt-loop-not-zombie",
         "passed": "cp 1" in exit_block and "zx48_process_exit_pid1:" in exit_block and "di\nzx48_process_exit_pid1_halt:\n    halt\n    jr zx48_process_exit_pid1_halt" in exit_block},
    ]
    require(all(item["passed"] for item in assertions), "P6.29 static contract failure")

    asm = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)

    sf = build / "p629-shell-fixture.asm"
    sf.write_text(
        """    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/shell/sh.asm"
    ORG $C000
p629_start:
    EMIT_P624_JOBS_ROUTINES
    EMIT_P629_REAP_EXIT_ROUTINES
p629_end:
    SAVEBIN "p629-shell-fixture.bin",p629_start,p629_end-p629_start
""",
        encoding="utf-8",
        newline="\n",
    )
    sr = run_command([asm, "--nologo", "--lst=p629-shell-fixture.lst", "--sym=p629-shell-fixture.sym", "p629-shell-fixture.asm"], cwd=build, timeout_seconds=30)
    require(not sr.timed_out and sr.exit_code == 0, f"P6.29 shell fixture assembly failed: {sr.stderr or sr.stdout}")

    kr, kernel, listing = phase1._assemble_kernel(root, run_command, require_project_tool)
    labels = phase1._labels(
        listing,
        ("zx48_process_init", "zx48_process_exit", "zx48_process_exit_pid1_halt", "process_table", "current_pid"),
    )
    kernel_bytes = kernel.read_bytes()

    if action == "test":
        # PID1 exit must reach only the permanent halt path. Replace the HALT
        # instruction with JP PASS for deterministic debugger observation.
        patched = bytearray(kernel_bytes)
        off = labels["zx48_process_exit_pid1_halt"] - phase1.KERNEL_BASE
        require(0 <= off <= len(patched) - 3, "P6.29 PID1 halt label outside kernel")
        patched[off:off + 3] = phase1._jp(PASS_PC)
        table = labels["process_table"]
        p1 = table + 48
        code = bytearray(b"\xF3" + phase1._ld_sp(0xFD00))
        code += phase1._call(labels["zx48_process_init"])
        code += setb(p1 + 2, 2)
        code += setb(labels["current_pid"], 1)
        code += b"\x3E\x00" + phase1._call(labels["zx48_process_exit"])
        code += phase1._jp(FAIL_PC)
        run_sna(root, bytes(code), patch=phase1._kernel_patch(bytes(patched)))
        assertions.append({"name": "fuse-pid1-exit-reaches-permanent-halt-boundary", "passed": True})

    hashes = {
        "v1/src/shell/sh.asm": sha256_file(shell_path),
        "v1/src/kernel/process.asm": sha256_file(process_path),
        "v1/build/kernel.bin": sha256_file(kernel),
        "v1/build/p629-shell-fixture.bin": sha256_file(build / "p629-shell-fixture.bin"),
        "v1/tools-host/test-driver/phase6_pid1_exit.py": sha256_file(root / "v1/tools-host/test-driver/phase6_pid1_exit.py"),
        "v1/tools-host/test-driver/run.py": sha256_file(root / "v1/tools-host/test-driver/run.py"),
        "v1/dist/certification/P6.28.build.json": sha256_file(root / "v1/dist/certification/P6.28.build.json"),
        "v1/dist/certification/P6.28.test.json": sha256_file(root / "v1/dist/certification/P6.28.test.json"),
        "v1/dist/media/P6.28/manifest.json": sha256_file(root / "v1/dist/media/P6.28/manifest.json"),
    }
    return [sr, kr], hashes, assertions
