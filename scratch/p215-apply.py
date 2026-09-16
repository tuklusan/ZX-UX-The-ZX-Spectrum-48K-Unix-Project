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
    runtime = RUNTIME_PATH.read_text(encoding="utf-8")

    # SjASMPlus decides macro-body conditionals while the source is parsed.
    # The previous marker was created only when EMIT_WAIT_SPECIFIC_ROUTINES ran,
    # which is too late for syscall.asm's earlier macro definitions.  Use a
    # separate composition switch that the staged fixture defines before any
    # kernel source include.  Keep ZX48_P2_15_WAIT_EMITTED as the emitted marker.
    process = replace_once(
        process,
        "    IFDEF ZX48_P2_15_WAIT_EMITTED\n",
        "    IFDEF ZX48_P2_15_WAIT_ENABLED\n",
        "P2.14 selective wake early composition guard",
    )
    syscall = replace_all_checked(
        syscall,
        "    IFDEF ZX48_P2_15_WAIT_EMITTED\n",
        "    IFDEF ZX48_P2_15_WAIT_ENABLED\n",
        2,
        "P2.15 syscall early composition guards",
    )
    runtime = replace_once(
        runtime,
        '        "    DEVICE ZXSPECTRUM48\\n"\n        "    INCLUDE \\\"../include/zx48ux.inc\\\"\\n"',
        '        "    DEVICE ZXSPECTRUM48\\n"\n        "ZX48_P2_15_WAIT_ENABLED EQU 1\\n"\n        "    INCLUDE \\\"../include/zx48ux.inc\\\"\\n"',
        "runtime early P2.15 composition switch",
    )

    PROCESS_PATH.write_text(process, encoding="utf-8", newline="\n")
    SYSCALL_PATH.write_text(syscall, encoding="utf-8", newline="\n")
    RUNTIME_PATH.write_text(runtime, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
