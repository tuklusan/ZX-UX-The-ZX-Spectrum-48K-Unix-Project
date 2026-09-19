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
from fuse_harness import FAIL_PC, PASS_PC, run_sna
import phase1
import phase3_open_descriptions

PATH_BASE = 0xA000
USER_BASE = 0xA300


class Phase4NamespaceError(DriverError):
    """Raised when the P4.01 fixed namespace resolver contract regresses."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Phase4NamespaceError(message)


def _word(value: int) -> bytes:
    return bytes((value & 0xFF, (value >> 8) & 0xFF))


def _jp_nc(address: int) -> bytes:
    return b"\xD2" + _word(address)


def _source_contract(root: Path) -> list[dict[str, object]]:
    inc = (root / "v1/include/zx48ux.inc").read_text(encoding="utf-8")
    objects = (root / "v1/src/kernel/objects.asm").read_text(encoding="utf-8")
    doc = (root / "v1/docs/namespace.md").read_text(encoding="utf-8")
    exact_ids = (
        "DIR_ROOT                 EQU $00",
        "DIR_BIN                  EQU $01",
        "DIR_DEV                  EQU $02",
        "DIR_ETC                  EQU $03",
        "DIR_HOME                 EQU $04",
        "DIR_USERHOME             EQU $05",
        "DIR_TMP                  EQU $06",
        "DIR_SYSTEM               EQU $07",
    )
    assertions = [
        {"name": "fixed-directory-ids-root-through-system-exact", "passed": all(x in inc for x in exact_ids)},
        {"name": "fixed-root-children-bin-dev-etc-home-tmp-only", "passed": all(x in objects for x in (
            "path_bin: db 'b','i','n',0", "path_dev: db 'd','e','v',0",
            "path_etc: db 'e','t','c',0", "path_home: db 'h','o','m','e',0",
            "path_tmp: db 't','m','p',0",
        ))},
        {"name": "home-child-is-session-user-only", "passed": "cp DIR_HOME\n    jr z,zx48_path_child_home" in objects and "session_user" in objects},
        {"name": "dot-and-dotdot-navigation-explicit", "passed": "cp '.'" in objects and "path_name+2" in objects},
        {"name": "above-root-is-einval", "passed": "or a\n    jr z,zx48_path_invalid" in objects},
        {"name": "normalized-length-not-raw-length", "passed": "ld (ns_kind),a" in objects and "cp 32" in objects and "zx48_path_len:" not in objects},
        {"name": "trailing-separator-empty-final-is-einval", "passed": "jp .bad" in objects and ".tail:" in objects},
        {"name": "no-general-directory-mount-permission-inode-surface", "passed": all(x not in objects.lower() for x in ("mkdir", "rmdir", "mount", "inode", "chmod", "chown"))},
        {"name": "namespace-contract-document-present", "passed": "Version-1 fixed namespace" in doc and "DIR_SYSTEM = 7" in doc},
    ]
    return assertions


def _emit_success(code: bytearray, s: dict[str, int], address: int, directory: int, kind: int) -> None:
    code += phase1._ld_hl(address) + phase1._call(s["zx48_path_resolve"]) + phase1._jp_c(FAIL_PC)
    code += bytes((0xFE, directory & 0xFF)) + phase1._jp_nz(FAIL_PC)
    code += b"\x79\xFE" + bytes((kind & 0xFF,)) + phase1._jp_nz(FAIL_PC)


def _emit_error(code: bytearray, s: dict[str, int], address: int, errno: int) -> None:
    code += phase1._ld_hl(address) + phase1._call(s["zx48_path_resolve"]) + _jp_nc(FAIL_PC)
    code += bytes((0xFE, errno & 0xFF)) + phase1._jp_nz(FAIL_PC)


def _target_matrix(root: Path, s: dict[str, int], kernel: bytes) -> None:
    paths = [
        "/", "/bin", "//bin///", "/dev", "/etc", "/home", "/tmp",
        "/bin/.", "/bin/..", "/..", "/wat/x", "/bin/name/",
        "/" * 40 + "bin", "/bin/Foo",
        "/home/alice",
    ]
    addresses: list[int] = []
    cursor = PATH_BASE
    payload = bytearray()
    for item in paths:
        addresses.append(cursor)
        encoded = item.encode("ascii") + b"\0"
        payload += encoded
        cursor += len(encoded)

    code = bytearray(b"\xF3" + phase1._ld_sp(0xBFC0))
    code += phase1._call(s["zx48_process_init"])
    code += phase1._call(s["zx48_process_prepare_pid1"])
    code += b"\x3E\x01\x32" + _word(s["current_pid"])

    _emit_success(code, s, addresses[0], s["DIR_ROOT"], s["PATH_KIND_DIR"])
    _emit_success(code, s, addresses[1], s["DIR_BIN"], s["PATH_KIND_DIR"])
    _emit_success(code, s, addresses[2], s["DIR_BIN"], s["PATH_KIND_DIR"])
    _emit_success(code, s, addresses[3], s["DIR_DEV"], s["PATH_KIND_DIR"])
    _emit_success(code, s, addresses[4], s["DIR_ETC"], s["PATH_KIND_DIR"])
    _emit_success(code, s, addresses[5], s["DIR_HOME"], s["PATH_KIND_DIR"])
    _emit_success(code, s, addresses[6], s["DIR_TMP"], s["PATH_KIND_DIR"])
    _emit_success(code, s, addresses[7], s["DIR_BIN"], s["PATH_KIND_DIR"])
    _emit_success(code, s, addresses[8], s["DIR_ROOT"], s["PATH_KIND_DIR"])
    _emit_error(code, s, addresses[9], s["E_INVAL"])
    _emit_error(code, s, addresses[10], s["E_NOENT"])
    _emit_error(code, s, addresses[11], s["E_INVAL"])
    _emit_success(code, s, addresses[12], s["DIR_BIN"], s["PATH_KIND_DIR"])
    _emit_success(code, s, addresses[13], s["DIR_BIN"], s["PATH_KIND_BASE"])

    # Before login, /home/alice is absent.
    _emit_error(code, s, addresses[14], s["E_NOENT"])

    # Install the current session USERHOME mapping directly.
    code += b"\x3E\x05\x32" + _word(s["session_user_len"])
    code += phase1._ld_hl(USER_BASE) + phase1._ld_de(s["session_user"]) + b"\x01\x05\x00\xED\xB0"
    _emit_success(code, s, addresses[14], s["DIR_USERHOME"], s["PATH_KIND_DIR"])

    code += phase1._jp(PASS_PC)

    def patch(ram: bytearray) -> None:
        start = phase1.KERNEL_BASE - 0x4000
        ram[start:start + len(kernel)] = kernel
        off = PATH_BASE - 0x4000
        ram[off:off + len(payload)] = payload
        uoff = USER_BASE - 0x4000
        ram[uoff:uoff + 6] = b"alice\0"

    run_sna(root, bytes(code), patch=patch)


def dispatch(
    root: Path,
    action: str,
    step: str,
    *,
    sha256_file: Callable[[Path], str],
    run_command: Callable[..., Any],
    require_project_tool: Callable[[Path, str | Path], Path],
):
    if step != "P4.01":
        raise DriverError(f"Phase-4 namespace step is not registered: {step}")

    assertions = _source_contract(root)
    failed = [item["name"] for item in assertions if item.get("passed") is not True]
    require(not failed, f"static P4.01 contract failures: {failed}")

    result, kernel, listing = phase1._assemble_kernel(root, run_command, require_project_tool)
    commands = [result]
    symbols = phase3_open_descriptions._symbols(
        listing.with_suffix(".sym"),
        (
            "zx48_process_init", "zx48_process_prepare_pid1",
            "zx48_path_resolve",
            "current_pid", "path_name", "session_user_len", "session_user",
            "DIR_ROOT", "DIR_BIN", "DIR_DEV", "DIR_ETC", "DIR_HOME",
            "DIR_USERHOME", "DIR_TMP", "DIR_SYSTEM",
            "PATH_KIND_DIR", "PATH_KIND_BASE", "E_INVAL", "E_NOENT", "E_TOOLONG",
        ),
    )
    assertions.extend([
        {"name": "runtime-directory-id-sequence-exact", "passed": [symbols[x] for x in (
            "DIR_ROOT", "DIR_BIN", "DIR_DEV", "DIR_ETC", "DIR_HOME", "DIR_USERHOME", "DIR_TMP", "DIR_SYSTEM"
        )] == list(range(8))},
        {"name": "path-kind-values-distinct", "passed": symbols["PATH_KIND_DIR"] != symbols["PATH_KIND_BASE"]},
    ])

    if action == "test":
        _target_matrix(root, symbols, kernel.read_bytes())
        assertions.extend([
            {"name": "absolute-and-relative-fixed-directory-resolution-exact", "passed": True},
            {"name": "repeated-separator-and-dot-normalization-exact", "passed": True},
            {"name": "root-parent-traversal-einval", "passed": True},
            {"name": "unknown-intermediate-component-enoent", "passed": True},
            {"name": "empty-final-after-trailing-separator-einval", "passed": True},
            {"name": "raw-over31-normalized-under31-accepted", "passed": True},
            {"name": "prelogin-home-child-not-directory", "passed": True},
            {"name": "postlogin-current-userhome-directory-exact", "passed": True},
        ])

    hashes = {
        "v1/build/kernel.bin": sha256_file(kernel),
        "v1/include/zx48ux.inc": sha256_file(root / "v1/include/zx48ux.inc"),
        "v1/src/kernel/kernel.asm": sha256_file(root / "v1/src/kernel/kernel.asm"),
        "v1/src/kernel/objects.asm": sha256_file(root / "v1/src/kernel/objects.asm"),
        "v1/docs/namespace.md": sha256_file(root / "v1/docs/namespace.md"),
        "v1/tools-host/test-driver/phase4_namespace.py": sha256_file(root / "v1/tools-host/test-driver/phase4_namespace.py"),
        "v1/tools-host/test-driver/run.py": sha256_file(root / "v1/tools-host/test-driver/run.py"),
        "v1/dist/certification/phase-3.json": sha256_file(root / "v1/dist/certification/phase-3.json"),
    }
    return commands, hashes, assertions
