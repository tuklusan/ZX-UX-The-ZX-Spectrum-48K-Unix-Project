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


RUNTIME_PATH = Path("v1/tools-host/test-driver/phase2_wait_specific_runtime.py")


def replace_once(text: str, old: str, new: str, name: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{name}: expected exactly one old-text match, found {count}")
    return text.replace(old, new, 1)


def main() -> None:
    runtime = RUNTIME_PATH.read_text(encoding="utf-8")

    # SjASMPlus IFDEF tests preprocessor DEFINE identifiers, not EQU labels.
    # The previous EQU therefore appeared in the symbol file but did not enable
    # the conditional P2.15 syscall continuation.  Define the compile switch in
    # the preprocessor namespace before the kernel source includes instead.
    runtime = replace_once(
        runtime,
        '        "ZX48_P2_15_WAIT_ENABLED EQU 1\\n"',
        '        "    DEFINE ZX48_P2_15_WAIT_ENABLED\\n"',
        "runtime P2.15 preprocessor switch",
    )

    RUNTIME_PATH.write_text(runtime, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
