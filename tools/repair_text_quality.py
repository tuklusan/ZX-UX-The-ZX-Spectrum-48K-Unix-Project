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

import hashlib
from pathlib import Path
import re
import sys

ROOT_MARKER = b"ZX-UX project root"
ARCHITECTURE = Path("docs/01-ZX-UX-ARCHITECTURE-REV11.md")
IMPLEMENTATION = Path("docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV02.md")
VERIFIER = Path("tools/scripts/verify-environment.py")
ARCH_LINE = re.compile(rb"(?im)^(Architecture SHA-256:\s*`)([0-9a-f]{64})(`\s*)$")
ARCH_FOOTER = re.compile(rb"(?im)(canonical REV11 SHA-256\s*\n`)([0-9a-f]{64})(`)")
VERIFIER_LINE = re.compile(rb'(?m)^(ARCHITECTURE_SHA256\s*=\s*")([0-9a-f]{64})("\s*)$')


class RepairError(RuntimeError):
    pass


def find_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        marker = candidate / ".zxux-root"
        if marker.is_file() and not marker.is_symlink() and marker.read_bytes() == ROOT_MARKER:
            return candidate
    raise RepairError("canonical project root not found")


def strip_trailing_horizontal_whitespace(data: bytes) -> bytes:
    lines = data.splitlines(keepends=True)
    repaired: list[bytes] = []
    for line in lines:
        if line.endswith(b"\r\n"):
            body, ending = line[:-2], b"\r\n"
        elif line.endswith(b"\n") or line.endswith(b"\r"):
            body, ending = line[:-1], line[-1:]
        else:
            body, ending = line, b""
        repaired.append(body.rstrip(b" \t") + ending)
    return b"".join(repaired)


def preserve_hex_case(original: bytes, replacement_lower: str) -> bytes:
    replacement = replacement_lower.encode("ascii")
    return replacement.upper() if original.isupper() else replacement


def replace_hash(pattern: re.Pattern[bytes], data: bytes, new_hash: str) -> tuple[bytes, int]:
    count = 0

    def replacement(match: re.Match[bytes]) -> bytes:
        nonlocal count
        count += 1
        return match.group(1) + preserve_hex_case(match.group(2), new_hash) + match.group(3)

    return pattern.sub(replacement, data), count


def main() -> int:
    try:
        root = find_root(Path(__file__).resolve())
        architecture = root / ARCHITECTURE
        implementation = root / IMPLEMENTATION
        verifier = root / VERIFIER
        for path in (architecture, implementation, verifier):
            if not path.is_file() or path.is_symlink():
                raise RepairError(f"required regular file missing: {path.relative_to(root)}")

        before_arch = architecture.read_bytes()
        after_arch = strip_trailing_horizontal_whitespace(before_arch)
        new_hash = hashlib.sha256(after_arch).hexdigest()

        impl_before = implementation.read_bytes()
        impl_after, header_count = replace_hash(ARCH_LINE, impl_before, new_hash)
        impl_after, footer_count = replace_hash(ARCH_FOOTER, impl_after, new_hash)
        if header_count != 1:
            raise RepairError(f"expected one implementation architecture header hash, found {header_count}")
        if footer_count != 1:
            raise RepairError(f"expected one implementation architecture footer hash, found {footer_count}")

        verifier_before = verifier.read_bytes()
        verifier_after, verifier_count = replace_hash(VERIFIER_LINE, verifier_before, new_hash)
        if verifier_count != 1:
            raise RepairError(f"expected one verifier architecture hash, found {verifier_count}")

        changed: list[str] = []
        if after_arch != before_arch:
            architecture.write_bytes(after_arch)
            changed.append(str(ARCHITECTURE))
        if impl_after != impl_before:
            implementation.write_bytes(impl_after)
            changed.append(str(IMPLEMENTATION))
        if verifier_after != verifier_before:
            verifier.write_bytes(verifier_after)
            changed.append(str(VERIFIER))

        if changed:
            print("repaired=" + ",".join(changed))
        else:
            print("clean=text-quality")
        print(f"architecture_sha256={new_hash}")
        return 0
    except (OSError, RepairError) as exc:
        print(f"ZX-UX TEXT QUALITY REPAIR FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
