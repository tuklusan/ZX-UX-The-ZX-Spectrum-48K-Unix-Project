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
import os
from pathlib import Path
import stat
import sys

ROOT = Path(__file__).resolve().parents[1]
PRESERVED_REFERENCE_DIR = "reference"
PRESERVED_REFERENCE_TREE_SHA1 = "a4e06de3b8b193b43597cdb4d259b5b206e7e3ad"


class ReferenceTreeError(RuntimeError):
    pass


def git_object_sha1(kind: bytes, payload: bytes) -> bytes:
    header = kind + b" " + str(len(payload)).encode("ascii") + b"\0"
    return hashlib.sha1(header + payload).digest()


def tree_sha1(path: Path) -> tuple[bytes | None, int]:
    entries: list[tuple[bytes, bytes]] = []
    file_count = 0
    with os.scandir(path) as scan:
        for entry in scan:
            name = os.fsencode(entry.name)
            if entry.is_symlink():
                raise ReferenceTreeError(f"reference tree contains unsupported symlink: {entry.path}")
            if entry.is_dir(follow_symlinks=False):
                object_id, nested_count = tree_sha1(Path(entry.path))
                if object_id is None:
                    continue
                file_count += nested_count
                mode = b"40000"
                sort_key = name + b"/"
            elif entry.is_file(follow_symlinks=False):
                info = entry.stat(follow_symlinks=False)
                execute_mask = stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
                mode = b"100755" if info.st_mode & execute_mask else b"100644"
                payload = Path(entry.path).read_bytes()
                object_id = git_object_sha1(b"blob", payload)
                file_count += 1
                sort_key = name
            else:
                raise ReferenceTreeError(f"reference tree contains unsupported artifact: {entry.path}")
            record = mode + b" " + name + b"\0" + object_id
            entries.append((sort_key, record))
    if not entries:
        return None, file_count
    payload = b"".join(record for _, record in sorted(entries, key=lambda item: item[0]))
    return git_object_sha1(b"tree", payload), file_count


def verify_reference_tree(root: Path | None = None) -> tuple[str, int]:
    reference = root if root is not None else ROOT / PRESERVED_REFERENCE_DIR
    if reference.is_symlink() or not reference.is_dir():
        raise ReferenceTreeError("approved H03 reference corpus must exist as a real directory")
    tree_id, file_count = tree_sha1(reference)
    if tree_id is None:
        raise ReferenceTreeError("reference tree contains no tracked artifacts")
    actual = tree_id.hex()
    if actual != PRESERVED_REFERENCE_TREE_SHA1:
        raise ReferenceTreeError(
            "preserved reference corpus does not match the approved H03 tree identity: "
            f"expected {PRESERVED_REFERENCE_TREE_SHA1}, got {actual}"
        )
    return actual, file_count


def main() -> int:
    try:
        actual, file_count = verify_reference_tree()
    except ReferenceTreeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"H03 reference tree verification passed: {file_count} file(s); tree {actual}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
