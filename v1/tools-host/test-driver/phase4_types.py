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

MODULE_BASE = 0xC000


class Phase4TypeError(DriverError):
    """Raised when the P4.04 type/state placement contract regresses."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Phase4TypeError(message)


def _word(value: int) -> bytes:
    return bytes((value & 0xFF, (value >> 8) & 0xFF))


def _jp_nc(address: int) -> bytes:
    return b"\xD2" + _word(address)


def _assemble(root: Path, run_command: Callable[..., Any], require_project_tool: Callable[[Path, str | Path], Path]):
    assembler = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    fixture = build / "p404-types.asm"
    fixture.write_text(
        """    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    ORG $C000
    INCLUDE "../src/kernel/objects.asm"
    EMIT_OBJECT_TYPE_ROUTINES
    SAVEBIN "p404-types.bin",$C000,$-$C000
""",
        encoding="utf-8", newline="\n",
    )
    result = run_command(
        [assembler, "--nologo", "--lst=p404-types.lst", "--sym=p404-types.sym", "p404-types.asm"],
        cwd=build,
        timeout_seconds=30.0,
    )
    require(not result.timed_out and result.exit_code == 0, f"P4.04 fixture assembly failed: {result.stderr or result.stdout}")
    binary = build / "p404-types.bin"
    listing = build / "p404-types.lst"
    require(binary.is_file() and 0 < binary.stat().st_size < 4096, "P4.04 fixture binary missing/oversize")
    return result, binary, listing


def _source_contract(root: Path) -> list[dict[str, object]]:
    inc = (root / "v1/include/zx48ux.inc").read_text(encoding="utf-8")
    objects = (root / "v1/src/kernel/objects.asm").read_text(encoding="utf-8")
    abi_path = root / "v1/docs/abi.md"
    abi = abi_path.read_text(encoding="utf-8")
    exact = (
        "OBJ_TXT                  EQU $01", "OBJ_BIN                  EQU $02",
        "OBJ_OBJ                  EQU $03", "OBJ_ASM                  EQU $04",
        "OBJ_C                    EQU $05", "OBJ_DAT                  EQU $06",
        "OBJ_UDG                  EQU $07", "OBJ_GFX                  EQU $08",
        "OBJ_FNT                  EQU $09", "OBJ_CFG                  EQU $0A",
        "OBJ_SYS                  EQU $0B", "OBJ_DIR                  EQU $0C",
        "OBJ_DEV                  EQU $0D", "STATE_RAM                EQU $00",
        "STATE_TAPE_BACKED        EQU $01", "STATE_PINNED_SYSTEM      EQU $02",
        "STATE_PSEUDO             EQU $03", "OBJ_PACKED               EQU $01",
    )
    text_suffixes = {".asm", ".inc", ".c", ".h", ".py", ".md", ".txt"}
    crlf = [
        str(path.relative_to(root))
        for path in (root / "v1").rglob("*")
        if path.is_file() and path.suffix.lower() in text_suffixes and b"\r\n" in path.read_bytes()
    ]
    macro = objects.split("MACRO EMIT_OBJECT_TYPE_ROUTINES", 1)[1].split("ENDM", 1)[0]
    return [
        {"name": "type-state-flag-ids-exact", "passed": all(item in inc for item in exact)},
        {"name": "public-placement-matrix-explicit", "passed": all(item in macro for item in ("DIR_BIN", "DIR_ETC", "DIR_USERHOME", "DIR_TMP", "OBJ_BIN", "OBJ_TXT", "OBJ_CFG"))},
        {"name": "system-bootstrap-fnt-sys-only", "passed": all(item in macro for item in ("DIR_SYSTEM", "OBJ_FNT", "OBJ_SYS"))},
        {"name": "m48o-payload-range-excludes-dir-dev", "passed": "cp OBJ_SYS+1" in macro and "cp OBJ_TXT" in macro},
        {"name": "namespace-dir-dev-length-zero-check", "passed": "cp OBJ_DIR" in macro and "cp OBJ_DEV" in macro and ".must_zero" in macro},
        {"name": "tape-backed-visible-length-unknown", "passed": "cp STATE_TAPE_BACKED" in macro and "ld hl,$ffff" in macro},
        {"name": "lf-byte-is-canonical-target-separator", "passed": "zx48_text_line_separator:" in macro and "ld a,$0a" in macro},
        {"name": "type-placement-does-not-infer-suffix", "passed": all(token not in macro for token in ("zx48_name_", "path_name", "cp '.'", "tolower", "toupper"))},
        {"name": "phase4-text-corpus-is-lf-only", "passed": not crlf},
        {"name": "abi-doc-freezes-placement-and-lf", "passed": "Public mutable placement is exact" in abi and "target tools never emit CRLF" in abi and "infer type from a suffix" in abi},
    ]


def _target(root: Path, s: dict[str, int], module: bytes) -> None:
    def patch(ram: bytearray) -> None:
        off = MODULE_BASE - 0x4000
        ram[off:off + len(module)] = module

    def execute(label: str, code: bytes) -> None:
        body = bytes((0xF3,)) + phase1._ld_sp(0xBFC0) + code + phase1._jp(PASS_PC)
        try:
            run_sna(root, body, patch=patch)
        except DriverError as exc:
            raise Phase4TypeError(f"P4.04 target case failed: {label}: {exc}") from exc

    def call_ab(label: str, routine: str, directory: int, type_id: int, ok: bool, errno: int) -> None:
        code = bytes((0x3E, directory & 0xFF, 0x06, type_id & 0xFF)) + phase1._call(s[routine])
        code += (phase1._jp_c(FAIL_PC) if ok else _jp_nc(FAIL_PC))
        if not ok:
            code += bytes((0xFE, errno & 0xFF)) + phase1._jp_nz(FAIL_PC)
        execute(label, code)

    def call_b(label: str, routine: str, type_id: int, ok: bool, errno: int) -> None:
        code = bytes((0x06, type_id & 0xFF)) + phase1._call(s[routine])
        code += (phase1._jp_c(FAIL_PC) if ok else _jp_nc(FAIL_PC))
        if not ok:
            code += bytes((0xFE, errno & 0xFF)) + phase1._jp_nz(FAIL_PC)
        execute(label, code)

    for type_id in range(s["OBJ_TXT"], s["OBJ_SYS"] + 1):
        call_b(f"payload-type-{type_id}", "zx48_object_payload_type_validate", type_id, True, s["E_INVAL"])
    for type_id in (0, s["OBJ_DIR"], s["OBJ_DEV"], s["OBJ_DEV"] + 1):
        call_b(f"payload-reject-{type_id}", "zx48_object_payload_type_validate", type_id, False, s["E_INVAL"])

    call_ab("bin-bin", "zx48_object_public_type_allowed", s["DIR_BIN"], s["OBJ_BIN"], True, s["E_PERM"])
    call_ab("bin-c-rejected", "zx48_object_public_type_allowed", s["DIR_BIN"], s["OBJ_C"], False, s["E_PERM"])
    call_ab("etc-txt", "zx48_object_public_type_allowed", s["DIR_ETC"], s["OBJ_TXT"], True, s["E_PERM"])
    call_ab("etc-cfg", "zx48_object_public_type_allowed", s["DIR_ETC"], s["OBJ_CFG"], True, s["E_PERM"])
    call_ab("etc-c-rejected", "zx48_object_public_type_allowed", s["DIR_ETC"], s["OBJ_C"], False, s["E_PERM"])
    for directory in (s["DIR_USERHOME"], s["DIR_TMP"]):
        for type_id in range(s["OBJ_TXT"], s["OBJ_CFG"] + 1):
            call_ab(f"ordinary-{directory}-{type_id}", "zx48_object_public_type_allowed", directory, type_id, True, s["E_PERM"])
    for directory in (s["DIR_ROOT"], s["DIR_DEV"], s["DIR_HOME"], s["DIR_SYSTEM"]):
        call_ab(f"fixed-public-reject-{directory}", "zx48_object_public_type_allowed", directory, s["OBJ_TXT"], False, s["E_PERM"])
    call_ab("system-fnt-bootstrap", "zx48_object_bootstrap_type_allowed", s["DIR_SYSTEM"], s["OBJ_FNT"], True, s["E_PERM"])
    call_ab("system-sys-bootstrap", "zx48_object_bootstrap_type_allowed", s["DIR_SYSTEM"], s["OBJ_SYS"], True, s["E_PERM"])
    call_ab("system-bin-bootstrap-rejected", "zx48_object_bootstrap_type_allowed", s["DIR_SYSTEM"], s["OBJ_BIN"], False, s["E_PERM"])
    call_ab("tmp-sys-bootstrap-rejected", "zx48_object_bootstrap_type_allowed", s["DIR_TMP"], s["OBJ_SYS"], False, s["E_PERM"])

    for state in range(s["STATE_RAM"], s["STATE_PSEUDO"] + 1):
        code = bytes((0x3E, state)) + phase1._call(s["zx48_namespace_state_validate"]) + phase1._jp_c(FAIL_PC)
        execute(f"state-{state}", code)
    code = bytes((0x3E, s["STATE_PSEUDO"] + 1)) + phase1._call(s["zx48_namespace_state_validate"]) + _jp_nc(FAIL_PC)
    code += bytes((0xFE, s["E_INVAL"])) + phase1._jp_nz(FAIL_PC)
    execute("state-invalid", code)

    for flags in (0, s["OBJ_PACKED"]):
        code = bytes((0x3E, flags)) + phase1._call(s["zx48_object_public_flags_validate"]) + phase1._jp_c(FAIL_PC)
        execute(f"flags-{flags}", code)
    for flags in (2, 0xFF):
        code = bytes((0x3E, flags)) + phase1._call(s["zx48_object_public_flags_validate"]) + _jp_nc(FAIL_PC)
        code += bytes((0xFE, s["E_INVAL"])) + phase1._jp_nz(FAIL_PC)
        execute(f"flags-invalid-{flags}", code)

    for type_id in (s["OBJ_DIR"], s["OBJ_DEV"]):
        code = bytes((0x06, type_id)) + phase1._ld_hl(0) + phase1._call(s["zx48_object_namespace_length_validate"]) + phase1._jp_c(FAIL_PC)
        execute(f"namespace-zero-{type_id}", code)
        code = bytes((0x06, type_id)) + phase1._ld_hl(1) + phase1._call(s["zx48_object_namespace_length_validate"]) + _jp_nc(FAIL_PC)
        code += bytes((0xFE, s["E_INVAL"])) + phase1._jp_nz(FAIL_PC)
        execute(f"namespace-nonzero-{type_id}", code)

    code = bytes((0x3E, s["STATE_TAPE_BACKED"])) + phase1._ld_hl(0x1234) + phase1._call(s["zx48_object_visible_length"]) + phase1._jp_c(FAIL_PC)
    code += bytes((0x7C, 0xFE, 0xFF)) + phase1._jp_nz(FAIL_PC) + bytes((0x7D, 0xFE, 0xFF)) + phase1._jp_nz(FAIL_PC)
    execute("tape-backed-unknown-length", code)
    code = bytes((0x3E, s["STATE_RAM"])) + phase1._ld_hl(0x1234) + phase1._call(s["zx48_object_visible_length"]) + phase1._jp_c(FAIL_PC)
    code += bytes((0x7C, 0xFE, 0x12)) + phase1._jp_nz(FAIL_PC) + bytes((0x7D, 0xFE, 0x34)) + phase1._jp_nz(FAIL_PC)
    execute("ram-visible-length-exact", code)

    code = phase1._call(s["zx48_text_line_separator"]) + bytes((0xFE, 0x0A)) + phase1._jp_nz(FAIL_PC)
    execute("lf-separator-exact", code)


def dispatch(
    root: Path,
    action: str,
    step: str,
    *,
    sha256_file: Callable[[Path], str],
    run_command: Callable[..., Any],
    require_project_tool: Callable[[Path, str | Path], Path],
):
    if step != "P4.04":
        raise DriverError(f"Phase-4 type-placement step is not registered: {step}")

    assertions = _source_contract(root)
    failed = [item["name"] for item in assertions if item.get("passed") is not True]
    require(not failed, f"static P4.04 contract failures: {failed}")

    kernel_result, kernel, _listing = phase1._assemble_kernel(root, run_command, require_project_tool)
    fixture_result, binary, listing = _assemble(root, run_command, require_project_tool)
    commands = [kernel_result, fixture_result]
    names = (
        "zx48_object_payload_type_validate", "zx48_object_public_type_allowed",
        "zx48_object_bootstrap_type_allowed", "zx48_namespace_state_validate",
        "zx48_object_public_flags_validate", "zx48_object_namespace_length_validate",
        "zx48_object_visible_length", "zx48_text_line_separator",
        "OBJ_TXT", "OBJ_BIN", "OBJ_C", "OBJ_FNT", "OBJ_CFG", "OBJ_SYS", "OBJ_DIR", "OBJ_DEV",
        "STATE_RAM", "STATE_TAPE_BACKED", "STATE_PINNED_SYSTEM", "STATE_PSEUDO", "OBJ_PACKED",
        "DIR_ROOT", "DIR_BIN", "DIR_DEV", "DIR_ETC", "DIR_HOME", "DIR_USERHOME", "DIR_TMP", "DIR_SYSTEM",
        "E_INVAL", "E_PERM",
    )
    symbols = phase3_open_descriptions._symbols(listing.with_suffix(".sym"), names)
    expected = {
        "OBJ_TXT": 1, "OBJ_BIN": 2, "OBJ_C": 5, "OBJ_FNT": 9, "OBJ_CFG": 10,
        "OBJ_SYS": 11, "OBJ_DIR": 12, "OBJ_DEV": 13,
        "STATE_RAM": 0, "STATE_TAPE_BACKED": 1, "STATE_PINNED_SYSTEM": 2, "STATE_PSEUDO": 3,
        "OBJ_PACKED": 1,
    }
    require(all(symbols[name] == value for name, value in expected.items()), "P4.04 numeric type/state/flag IDs changed")

    if action == "test":
        _target(root, symbols, binary.read_bytes())
        assertions.extend([
            {"name": "exact-type-state-flag-runtime-matrix", "passed": True},
            {"name": "public-and-bootstrap-placement-matrix-exact", "passed": True},
            {"name": "dir-dev-zero-and-tape-unknown-length-exact", "passed": True},
            {"name": "lf-only-runtime-separator-exact", "passed": True},
        ])

    hashes = {
        "v1/build/kernel.bin": sha256_file(kernel),
        "v1/build/p404-types.bin": sha256_file(binary),
        "v1/include/zx48ux.inc": sha256_file(root / "v1/include/zx48ux.inc"),
        "v1/src/kernel/objects.asm": sha256_file(root / "v1/src/kernel/objects.asm"),
        "v1/docs/abi.md": sha256_file(root / "v1/docs/abi.md"),
        "v1/tools-host/test-driver/phase4_types.py": sha256_file(root / "v1/tools-host/test-driver/phase4_types.py"),
        "v1/tools-host/test-driver/run.py": sha256_file(root / "v1/tools-host/test-driver/run.py"),
        "v1/dist/certification/P4.03.test.json": sha256_file(root / "v1/dist/certification/P4.03.test.json"),
    }
    return commands, hashes, assertions
