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

NAMESPACE_BASE = 0xC000
DATA_BASE = 0xA000


class Phase4NameError(DriverError):
    """Raised when the P4.02 base-name contract regresses."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Phase4NameError(message)


def _word(value: int) -> bytes:
    return bytes((value & 0xFF, (value >> 8) & 0xFF))


def _jp_nc(address: int) -> bytes:
    return b"\xD2" + _word(address)


def _assemble(root: Path, run_command: Callable[..., Any], require_project_tool: Callable[[Path, str | Path], Path]):
    assembler = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    fixture = build / "p402-names.asm"
    fixture.write_text(
        """    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
PROC_CWD EQU 28
    ORG $C000
current_pid: db 1
zx48_process_lookup:
    ld ix,fake_process
    xor a
    ret
    INCLUDE "../src/kernel/objects.asm"
    EMIT_NAMESPACE_ROUTINES
fake_process: defs 48,0
    SAVEBIN "p402-names.bin",$C000,$-$C000
""",
        encoding="utf-8", newline="\n",
    )
    result = run_command(
        [assembler, "--nologo", "--lst=p402-names.lst", "--sym=p402-names.sym", "p402-names.asm"],
        cwd=build,
        timeout_seconds=30.0,
    )
    require(not result.timed_out and result.exit_code == 0, f"P4.02 fixture assembly failed: {result.stderr or result.stdout}")
    binary = build / "p402-names.bin"
    listing = build / "p402-names.lst"
    require(binary.is_file() and 0 < binary.stat().st_size < 4096, "P4.02 fixture binary missing/oversize")
    return result, binary, listing


def _source_contract(root: Path) -> list[dict[str, object]]:
    objects = (root / "v1/src/kernel/objects.asm").read_text(encoding="utf-8")
    return [
        {"name": "basename-length-exactly-one-through-ten", "passed": "cp 11" in objects and "ld b,0" in objects},
        {"name": "portable-character-set-is-literal", "passed": all(x in objects for x in ("cp '0'", "cp '9'+1", "cp 'A'", "cp 'Z'+1", "cp 'a'", "cp 'z'+1", "cp '_'", "cp '-'", "cp '.'"))},
        {"name": "exact-dot-and-dotdot-rejected", "passed": ".check_dot:" in objects and "cp 2" in objects and "cp '.'" in objects},
        {"name": "path-base-validates-before-publication", "passed": ".base:\n    ld hl,path_name\n    call zx48_name_validate\n    ret c" in objects},
        {"name": "exact-case-comparator-has-no-folding", "passed": "zx48_cstr_equal:\n    ld a,(de)\n    cp (hl)" in objects and "tolower" not in objects.lower() and "toupper" not in objects.lower()},
    ]


def _target(root: Path, s: dict[str, int], module: bytes) -> None:
    values = ["hello.c", "Hello.c", "HELLO.C", ".cron.lock", "", ".", "..", "abcdefghijk", "bad+name"]
    addresses: dict[str, int] = {}
    cursor = DATA_BASE
    payload = bytearray()
    for value in values:
        addresses[value] = cursor
        encoded = value.encode("ascii") + bytes((0,))
        payload += encoded
        cursor += len(encoded)

    def patch(ram: bytearray) -> None:
        moff = NAMESPACE_BASE - 0x4000
        ram[moff:moff + len(module)] = module
        off = DATA_BASE - 0x4000
        ram[off:off + len(payload)] = payload

    def execute(label: str, code: bytes) -> None:
        body = bytes((0xF3,)) + phase1._ld_sp(0xBFC0) + code + phase1._jp(PASS_PC)
        try:
            run_sna(root, body, patch=patch)
        except DriverError as exc:
            raise Phase4NameError(f"P4.02 target case failed: {label}: {exc}") from exc

    def valid(value: str) -> None:
        code = phase1._ld_hl(addresses[value]) + phase1._call(s["zx48_name_validate"]) + phase1._jp_c(FAIL_PC)
        code += bytes((0xFE, len(value))) + phase1._jp_nz(FAIL_PC)
        execute(f"valid-{value}", code)

    def invalid(value: str, errno: int) -> None:
        code = phase1._ld_hl(addresses[value]) + phase1._call(s["zx48_name_validate"]) + _jp_nc(FAIL_PC)
        code += bytes((0xFE, errno & 0xFF)) + phase1._jp_nz(FAIL_PC)
        execute(f"invalid-{value!r}", code)

    def compare(a: str, b: str, equal: bool) -> None:
        code = phase1._ld_hl(addresses[a]) + phase1._ld_de(addresses[b]) + phase1._call(s["zx48_cstr_equal"])
        code += (phase1._jp_nz(FAIL_PC) if equal else phase1._jp_z(FAIL_PC))
        execute(f"compare-{a}-{b}", code)

    for value in ("hello.c", "Hello.c", "HELLO.C", ".cron.lock"):
        valid(value)
    invalid("", s["E_INVAL"])
    invalid(".", s["E_INVAL"])
    invalid("..", s["E_INVAL"])
    invalid("abcdefghijk", s["E_TOOLONG"])
    invalid("bad+name", s["E_INVAL"])
    compare("hello.c", "hello.c", True)
    compare("hello.c", "Hello.c", False)
    compare("Hello.c", "HELLO.C", False)
    compare(".cron.lock", ".cron.lock", True)


def dispatch(
    root: Path,
    action: str,
    step: str,
    *,
    sha256_file: Callable[[Path], str],
    run_command: Callable[..., Any],
    require_project_tool: Callable[[Path, str | Path], Path],
):
    if step != "P4.02":
        raise DriverError(f"Phase-4 name step is not registered: {step}")

    assertions = _source_contract(root)
    failed = [item["name"] for item in assertions if item.get("passed") is not True]
    require(not failed, f"static P4.02 contract failures: {failed}")

    kernel_result, kernel, _listing = phase1._assemble_kernel(root, run_command, require_project_tool)
    fixture_result, binary, listing = _assemble(root, run_command, require_project_tool)
    commands = [kernel_result, fixture_result]
    symbols = phase3_open_descriptions._symbols(
        listing.with_suffix(".sym"),
        ("zx48_name_validate", "zx48_cstr_equal", "E_INVAL", "E_TOOLONG"),
    )

    if action == "test":
        _target(root, symbols, binary.read_bytes())
        assertions.extend([
            {"name": "hello-case-variants-validate-and-remain-distinct", "passed": True},
            {"name": "legal-dot-prefixed-name-roundtrips-exactly", "passed": True},
            {"name": "empty-overlong-nonportable-dot-dotdot-rejected", "passed": True},
        ])

    hashes = {
        "v1/build/kernel.bin": sha256_file(kernel),
        "v1/build/p402-names.bin": sha256_file(binary),
        "v1/src/kernel/objects.asm": sha256_file(root / "v1/src/kernel/objects.asm"),
        "v1/tools-host/test-driver/phase4_names.py": sha256_file(root / "v1/tools-host/test-driver/phase4_names.py"),
        "v1/tools-host/test-driver/run.py": sha256_file(root / "v1/tools-host/test-driver/run.py"),
        "v1/dist/certification/P4.01.test.json": sha256_file(root / "v1/dist/certification/P4.01.test.json"),
    }
    return commands, hashes, assertions
