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

import importlib.util
from pathlib import Path
import sys
from typing import Any, Callable

from driver_core import DriverError
from fuse_harness import FAIL_PC, PASS_PC, run_sna
import phase1
import phase3_open_descriptions

MODULE_BASE = 0xC000
SRC_BASE = 0xA000
STACK_TOP = 0xBFC0
MAKETAP = "v1/tools-host/maketap/maketap.py"


class Phase5CRCError(DriverError):
    """Raised when the P5.02 CRC-16/CCITT-FALSE contract regresses."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Phase5CRCError(message)


def _oracle(data: bytes) -> int:
    crc = 0xFFFF
    for value in data:
        crc ^= value << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc


def _load_host(root: Path):
    path = root / MAKETAP
    spec = importlib.util.spec_from_file_location("zxux_p502_maketap", path)
    require(spec is not None and spec.loader is not None, "P5.02 cannot load maketap host implementation")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _source_contract(root: Path) -> list[dict[str, object]]:
    tape = (root / "v1/src/kernel/tape.asm").read_text(encoding="utf-8")
    host = (root / MAKETAP).read_text(encoding="utf-8")
    require("MACRO EMIT_P502_CRC16_ROUTINES" in tape, "P5.02 target CRC macro missing")
    body = tape.split("MACRO EMIT_P502_CRC16_ROUTINES", 1)[1].split("ENDM", 1)[0]
    tape_body = tape.split("MACRO EMIT_TAPE_ROUTINES", 1)[1].split("ENDM", 1)[0]
    return [
        {
            "name": "target-ccitt-false-parameters-exact",
            "passed": all(token in body for token in ("ld de,M48O_CRC16_INIT", "xor $21", "xor $10", "sla e", "rl d")),
        },
        {
            "name": "target-zero-length-is-init-value",
            "passed": "ld a,b\n    or c\n    ret z" in body,
        },
        {
            "name": "target-crc-routine-emitted-in-kernel",
            "passed": "EMIT_P502_CRC16_ROUTINES" in tape_body,
        },
        {
            "name": "host-ccitt-false-parameters-exact",
            "passed": all(
                token in host
                for token in (
                    "CRC16_CCITT_FALSE_POLY = 0x1021",
                    "CRC16_CCITT_FALSE_INIT = 0xFFFF",
                    "CRC16_CCITT_FALSE_XOROUT = 0x0000",
                    "CRC16_CCITT_FALSE_REFIN = False",
                    "CRC16_CCITT_FALSE_REFOUT = False",
                )
            ),
        },
    ]


def _assemble_crc(
    root: Path,
    run_command: Callable[..., Any],
    require_project_tool: Callable[[Path, str | Path], Path],
):
    asm = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    fixture = build / "p502-crc16.asm"
    fixture.write_text(
        """    DEVICE ZXSPECTRUM48
    INCLUDE "../include/tapeobj.inc"
    INCLUDE "../src/kernel/tape.asm"
    ORG $C000
    EMIT_P502_CRC16_ROUTINES
    SAVEBIN "p502-crc16.bin",$C000,$-$C000
""",
        encoding="utf-8",
        newline="\n",
    )
    result = run_command(
        [asm, "--nologo", "--lst=p502-crc16.lst", "--sym=p502-crc16.sym", "p502-crc16.asm"],
        cwd=build,
        timeout_seconds=30.0,
    )
    require(not result.timed_out and result.exit_code == 0, f"P5.02 fixture assembly failed: {result.stderr or result.stdout}")
    binary = build / "p502-crc16.bin"
    symbols = build / "p502-crc16.sym"
    require(binary.is_file() and 0 < binary.stat().st_size <= 128, "P5.02 CRC fixture missing/oversize")
    require(symbols.is_file(), "P5.02 CRC symbols missing")
    return result, binary, symbols


def _word(value: int) -> bytes:
    return bytes((value & 0xFF, (value >> 8) & 0xFF))


def _ld_bc(value: int) -> bytes:
    return b"\x01" + _word(value)


def _jp_z(address: int) -> bytes:
    return b"\xCA" + _word(address)


def _patch(module: bytes, data: bytes):
    def apply(ram: bytearray) -> None:
        moff = MODULE_BASE - 0x4000
        ram[moff:moff + len(module)] = module
        if data:
            off = SRC_BASE - 0x4000
            ram[off:off + len(data)] = data
    return apply


def _target_vector(root: Path, routine: int, module: bytes, data: bytes, expected: int) -> None:
    code = bytearray(b"\xF3")
    code += phase1._ld_sp(STACK_TOP)
    code += phase1._ld_hl(SRC_BASE) + _ld_bc(len(data))
    code += phase1._call(routine)
    code += b"\xEB" + phase1._ld_de(expected) + b"\xB7\xED\x52" + phase1._jp_nz(FAIL_PC)
    code += phase1._jp(PASS_PC)
    run_sna(root, bytes(code), patch=_patch(module, data))


def _target_reject_corruption(root: Path, routine: int, module: bytes, data: bytes, expected_good: int) -> None:
    code = bytearray(b"\xF3")
    code += phase1._ld_sp(STACK_TOP)
    code += phase1._ld_hl(SRC_BASE) + _ld_bc(len(data))
    code += phase1._call(routine)
    code += b"\xEB" + phase1._ld_de(expected_good) + b"\xB7\xED\x52" + _jp_z(FAIL_PC)
    code += phase1._jp(PASS_PC)
    run_sna(root, bytes(code), patch=_patch(module, data))


def dispatch(
    root: Path,
    action: str,
    step: str,
    *,
    sha256_file: Callable[[Path], str],
    run_command: Callable[..., Any],
    require_project_tool: Callable[[Path, str | Path], Path],
):
    if step != "P5.02":
        raise DriverError(f"Phase-5 CRC step is not registered: {step}")

    assertions = _source_contract(root)
    host = _load_host(root)
    vectors = (
        ("empty", b"", 0xFFFF),
        ("check-123456789", b"123456789", 0x29B1),
        ("single-zero", b"\x00", 0xE1F0),
        ("zxux", b"ZX-UX", 0x5C48),
        ("byte-ramp", bytes(range(256)), 0x3FBD),
    )
    for label, data, expected in vectors:
        assertions.append(
            {
                "name": f"host-known-vector-{label}",
                "passed": _oracle(data) == expected and host.crc16_ccitt_false(data) == expected,
            }
        )

    kernel_result, kernel, _ = phase1._assemble_kernel(root, run_command, require_project_tool)
    fixture_result, binary, symbol_path = _assemble_crc(root, run_command, require_project_tool)
    symbols = phase3_open_descriptions._symbols(symbol_path, ("zx48_crc16_ccitt_false",))

    if action == "test":
        module = binary.read_bytes()
        for _, data, expected in vectors:
            _target_vector(root, symbols["zx48_crc16_ccitt_false"], module, data, expected)
        good = b"123456789"
        corrupt = good[:-1] + bytes((good[-1] ^ 0x01,))
        expected_good = 0x29B1
        require(_oracle(corrupt) != expected_good, "P5.02 one-bit corruption oracle did not change")
        require(host.crc16_ccitt_false(corrupt) != expected_good, "P5.02 host failed to reject one-bit corruption")
        _target_reject_corruption(root, symbols["zx48_crc16_ccitt_false"], module, corrupt, expected_good)
        assertions.extend(
            [
                {"name": "target-known-vectors-match-host", "passed": True},
                {"name": "one-bit-payload-corruption-rejected-host", "passed": True},
                {"name": "one-bit-payload-corruption-rejected-target", "passed": True},
            ]
        )

    failed = [item["name"] for item in assertions if item.get("passed") is not True]
    require(not failed, f"P5.02 CRC failures: {failed}")

    hashes = {
        "v1/build/kernel.bin": sha256_file(kernel),
        "v1/build/p502-crc16.bin": sha256_file(binary),
        "v1/src/kernel/tape.asm": sha256_file(root / "v1/src/kernel/tape.asm"),
        "v1/include/tapeobj.inc": sha256_file(root / "v1/include/tapeobj.inc"),
        "v1/tools-host/maketap/maketap.py": sha256_file(root / MAKETAP),
        "v1/tools-host/test-driver/phase5_crc16.py": sha256_file(root / "v1/tools-host/test-driver/phase5_crc16.py"),
        "v1/tools-host/test-driver/run.py": sha256_file(root / "v1/tools-host/test-driver/run.py"),
        "v1/dist/certification/P5.01.build.json": sha256_file(root / "v1/dist/certification/P5.01.build.json"),
        "v1/dist/certification/P5.01.test.json": sha256_file(root / "v1/dist/certification/P5.01.test.json"),
    }
    return [kernel_result, fixture_result], hashes, assertions
