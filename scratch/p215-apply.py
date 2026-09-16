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
#
# Temporary guarded P2.15 cloud repair helper. Remove after P2.15 certification.

from pathlib import Path


PROCESS_PATH = Path("v1/src/kernel/process.asm")
SYSCALL_PATH = Path("v1/src/kernel/syscall.asm")
STATIC_PATH = Path("v1/tools-host/test-driver/phase2_wait_specific.py")
RUNTIME_PATH = Path("v1/tools-host/test-driver/phase2_wait_specific_runtime.py")


def replace_once(text: str, old: str, new: str, name: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{name}: expected exactly one old-text match, found {count}")
    return text.replace(old, new, 1)


def replace_all_checked(text: str, old: str, new: str, expected: int, name: str) -> str:
    count = text.count(old)
    if count != expected:
        raise SystemExit(f"{name}: expected {expected} old-text matches, found {count}")
    return text.replace(old, new)


def main() -> None:
    process = PROCESS_PATH.read_text(encoding="utf-8")
    syscall = SYSCALL_PATH.read_text(encoding="utf-8")
    static = STATIC_PATH.read_text(encoding="utf-8")
    runtime = RUNTIME_PATH.read_text(encoding="utf-8")

    # SjASMPlus conditionals inside emitted macros are directives only when
    # indented. The first P2.15 draft left these two macro-local blocks at
    # column zero, where they were parsed as duplicate labels/instructions.
    process = replace_once(
        process,
        "ret nz\nIFDEF ZX48_P2_15_WAIT_EMITTED\n",
        "ret nz\n    IFDEF ZX48_P2_15_WAIT_EMITTED\n",
        "P2.14 selective wake IFDEF indentation",
    )
    process = replace_once(
        process,
        "    ret c\nENDIF\n    ld (ix+PROC_STATE),PROC_READY\n",
        "    ret c\n    ENDIF\n    ld (ix+PROC_STATE),PROC_READY\n",
        "P2.14 selective wake ENDIF indentation",
    )
    syscall = replace_all_checked(
        syscall,
        "\nIFDEF ZX48_P2_15_WAIT_EMITTED\n",
        "\n    IFDEF ZX48_P2_15_WAIT_EMITTED\n",
        2,
        "P2.15 syscall IFDEF indentation",
    )
    syscall = replace_all_checked(
        syscall,
        "\nENDIF\n",
        "\n    ENDIF\n",
        2,
        "P2.15 syscall ENDIF indentation",
    )

    # The shared E_CHILD epilogue deliberately centralizes fail-closed exits,
    # but several early conditional relative jumps cannot reach it once the
    # complete continuation is emitted. Use conditional absolute JP there.
    wait_start = process.index("    MACRO EMIT_WAIT_SPECIFIC_ROUTINES\n")
    wait_end = process.index("    ENDM\n", wait_start)
    prefix = process[:wait_start]
    wait = process[wait_start:wait_end]
    suffix = process[wait_end:]
    conversions = (
        ("    jr nc,zx48_process_wait_specific_child\n", "    jp nc,zx48_process_wait_specific_child\n"),
        ("    jr c,zx48_process_wait_specific_record_failed\n", "    jp c,zx48_process_wait_specific_record_failed\n"),
        ("    jr c,zx48_process_wait_specific_child\n", "    jp c,zx48_process_wait_specific_child\n"),
        ("    jr z,zx48_process_wait_specific_child\n", "    jp z,zx48_process_wait_specific_child\n"),
        ("    jr nz,zx48_process_wait_specific_child\n", "    jp nz,zx48_process_wait_specific_child\n"),
    )
    converted = 0
    for old, new in conversions:
        count = wait.count(old)
        if count:
            wait = wait.replace(old, new)
            converted += count
    if converted < 10:
        raise SystemExit(f"P2.15 far-branch repair: expected at least 10 conversions, got {converted}")
    process = prefix + wait + suffix

    # Static proof follows the actual composition: P2.14 wake calls one helper;
    # the helper owns the wait-pid/generation table accesses in the P2.15 macro.
    static = replace_once(
        static,
        '"passed": "zx48_process_zombie_wait_specific_match" in zombie\n            and "process_wait_pid" in wake\n            and "process_wait_generation" in wake,',
        '"passed": "call zx48_process_zombie_wait_specific_match" in wake\n            and "process_wait_pid" in wait_specific\n            and "process_wait_generation" in wait_specific,',
        "selective wake static composition assertion",
    )

    # The target fixture emits syscall.asm without the rest of the resident
    # console/error modules. Supply exactly the canonical constants those
    # unrelated handlers reference, and keep status guard bytes distinct from
    # the tested exit status so a two-byte write cannot hide in plain sight.
    runtime = replace_once(
        runtime,
        '        "    INCLUDE \\\"../src/kernel/scheduler.asm\\\"\\n"\n        f"    ORG ${FIXTURE_CODE:04X}\\n"',
        '        "    INCLUDE \\\"../src/kernel/scheduler.asm\\\"\\n"\n        "PANIC_SCHEDULER EQU $03\\n"\n        "TTY_REQ_GET_MODE EQU 1\\n"\n        "TTY_REQ_GET_SIZE EQU 3\\n"\n        "TTY_REQ_SET_OWNER EQU 7\\n"\n        f"    ORG ${FIXTURE_CODE:04X}\\n"',
        "runtime dependency constants",
    )
    runtime = replace_all_checked(runtime, "_set_byte(STATUS_PTR + 1, 0x5A)", "_set_byte(STATUS_PTR + 1, 0x7E)", 1, "status upper guard setup")
    runtime = replace_all_checked(runtime, "_expect_byte(STATUS_PTR + 1, 0x5A)", "_expect_byte(STATUS_PTR + 1, 0x7E)", 3, "status upper guard assertions")

    PROCESS_PATH.write_text(process, encoding="utf-8", newline="\n")
    SYSCALL_PATH.write_text(syscall, encoding="utf-8", newline="\n")
    STATIC_PATH.write_text(static, encoding="utf-8", newline="\n")
    RUNTIME_PATH.write_text(runtime, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
