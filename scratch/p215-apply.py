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


def replace_once(text: str, old: str, new: str, name: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{name}: expected exactly one old-text match, found {count}")
    return text.replace(old, new, 1)


def main() -> None:
    process = PROCESS_PATH.read_text(encoding="utf-8")

    # Z80 has no direct absolute-memory load into B. With SjASMPlus relaxed
    # syntax, `ld b,(label)` is not a safe memory dereference. Load the durable
    # parent PID through A, copy it to B, then restore the exiting child PID in A
    # for the exact generation-qualified matcher.
    old = """    ld a,(process_zombie_pid)
    ld b,(process_zombie_parent_pid)
    call zx48_process_zombie_wait_specific_match
"""
    new = """    ld a,(process_zombie_parent_pid)
    ld b,a
    ld a,(process_zombie_pid)
    call zx48_process_zombie_wait_specific_match
"""
    process = replace_once(process, old, new, "P2.15 legal wake parent PID load")
    PROCESS_PATH.write_text(process, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
