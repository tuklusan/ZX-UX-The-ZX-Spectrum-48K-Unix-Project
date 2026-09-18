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


DECODER0 = 0xA100
DECODER1 = 0xA102


class Phase3IndependentOpenError(DriverError):
    """Raised when independently opened descriptions accidentally share state."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Phase3IndependentOpenError(message)


def _word(value: int) -> bytes:
    return bytes((value & 0xFF, (value >> 8) & 0xFF))


def _store_word(address: int, value: int) -> bytes:
    return b"\x21" + _word(value) + b"\x22" + _word(address)


def _load_word(address: int) -> bytes:
    return b"\x2A" + _word(address)


def _source_contract(root: Path) -> list[dict[str, object]]:
    handles = (root / "v1/src/kernel/handles.asm").read_text(encoding="utf-8")
    create = handles[handles.index("zx48_od_create:"):handles.index("; A=OD index. Adds one shared reference.")]
    return [
        {"name": "independent-open-allocates-new-description", "passed": "zx48_od_create_scan:" in create and "ld a,(ix+OD_KIND_O)" in create and "jr z,zx48_od_create_found" in create},
        {"name": "independent-open-does-not-match-existing-identity", "passed": "call zx48_od_retain" not in create and "cp (ix+OD_ID_O)" not in create},
        {"name": "new-description-zeroes-offset", "passed": "ld (ix+OD_OFFSET_O),a" in create and "ld (ix+OD_OFFSET_O+1),a" in create},
        {"name": "new-description-zeroes-decoder-pointer", "passed": "ld (ix+OD_AUX_O),a" in create and "ld (ix+OD_AUX_O+1),a" in create},
        {"name": "description-record-owns-offset-and-decoder", "passed": "OD_OFFSET_O                EQU 4" in handles and "OD_AUX_O                   EQU 6" in handles},
    ]


def _target_test(root: Path, s: dict[str, int], kernel: bytes) -> None:
    table = s["open_description_table"]
    size = s["OD_RECORD_SIZE"]
    off = s["OD_OFFSET_O"]
    aux = s["OD_AUX_O"]

    code = bytearray(b"\xF3" + phase1._ld_sp(0xBFC0))
    code += phase1._call(s["zx48_memory_init"])
    code += phase1._call(s["zx48_handles_init"])

    # Allocate two decoder states exactly as two independent PACKED reads would.
    for slot in (DECODER0, DECODER1):
        code += b"\x01" + _word(s["PACKED_READER_STATE_SIZE"])
        code += bytes((0x3E, s["ALLOC_ANY"]))
        code += phase1._call(s["zx48_alloc"]) + phase1._jp_c(FAIL_PC)
        code += b"\x22" + _word(slot)

    # Two independent opens of the same object identity must consume two ODs.
    for expected in (0, 1):
        code += bytes((0x06, s["OD_KIND_OBJECT"], 0x0E, s["O_READ"], 0x16, 3))
        code += phase1._call(s["zx48_od_create"]) + phase1._jp_c(FAIL_PC)
        code += bytes((0xFE, expected)) + phase1._jp_nz(FAIL_PC)

    # Attach distinct decoder state to each description.
    code += b"\xAF" + phase1._call(s["zx48_od_ptr"]) + phase1._jp_c(FAIL_PC)
    code += _load_word(DECODER0)
    code += bytes((0xDD, 0x75, aux & 0xFF, 0xDD, 0x74, (aux + 1) & 0xFF))
    code += b"\x3E\x01" + phase1._call(s["zx48_od_ptr"]) + phase1._jp_c(FAIL_PC)
    code += _load_word(DECODER1)
    code += bytes((0xDD, 0x75, aux & 0xFF, 0xDD, 0x74, (aux + 1) & 0xFF))

    # Initial state is independent and zero.
    code += _load_word(table + off) + b"\x7C\xB5" + phase1._jp_nz(FAIL_PC)
    code += _load_word(table + size + off) + b"\x7C\xB5" + phase1._jp_nz(FAIL_PC)
    code += _load_word(table + aux) + b"\xED\x5B" + _word(DECODER0) + b"\xB7\xED\x52" + phase1._jp_nz(FAIL_PC)
    code += _load_word(table + size + aux) + b"\xED\x5B" + _word(DECODER1) + b"\xB7\xED\x52" + phase1._jp_nz(FAIL_PC)

    # Fixture seek on OD0 cannot change OD1.
    code += _store_word(table + off, 0x0011)
    code += _load_word(table + off) + phase1._ld_de(0x0011) + b"\xB7\xED\x52" + phase1._jp_nz(FAIL_PC)
    code += _load_word(table + size + off) + b"\x7C\xB5" + phase1._jp_nz(FAIL_PC)

    # Fixture seek on OD1 cannot change OD0.
    code += _store_word(table + size + off, 0x0022)
    code += _load_word(table + off) + phase1._ld_de(0x0011) + b"\xB7\xED\x52" + phase1._jp_nz(FAIL_PC)
    code += _load_word(table + size + off) + phase1._ld_de(0x0022) + b"\xB7\xED\x52" + phase1._jp_nz(FAIL_PC)

    # Mutating one decoder-state pointer cannot alias the other description.
    code += _store_word(table + aux, 0)
    code += _load_word(table + size + aux) + b"\xED\x5B" + _word(DECODER1) + b"\xB7\xED\x52" + phase1._jp_nz(FAIL_PC)

    # Restore pointer and close both descriptions; both decoder allocations free.
    code += _load_word(DECODER0)
    code += b"\xDD\x21" + _word(table)
    code += bytes((0xDD, 0x75, aux & 0xFF, 0xDD, 0x74, (aux + 1) & 0xFF))
    code += b"\xAF" + phase1._call(s["zx48_od_release"]) + phase1._jp_c(FAIL_PC)
    code += b"\x3E\x01" + phase1._call(s["zx48_od_release"]) + phase1._jp_c(FAIL_PC)
    code += _load_word(s["memory_live_allocations"]) + b"\x7C\xB5" + phase1._jp_nz(FAIL_PC)

    code += phase1._jp(PASS_PC)
    run_sna(root, bytes(code), patch=phase1._kernel_patch(kernel))


def dispatch(
    root: Path,
    action: str,
    step: str,
    *,
    sha256_file: Callable[[Path], str],
    run_command: Callable[..., Any],
    require_project_tool: Callable[[Path, str | Path], Path],
):
    if step != "P3.07":
        raise DriverError(f"Phase-3 independent-open step is not registered: {step}")

    assertions = _source_contract(root)
    failed = [item["name"] for item in assertions if item["passed"] is not True]
    require(not failed, f"static P3.07 contract failures: {failed}")

    result, kernel, listing = phase1._assemble_kernel(root, run_command, require_project_tool)
    commands = [result]
    symbols = phase3_open_descriptions._symbols(
        listing.with_suffix(".sym"),
        (
            "zx48_memory_init", "zx48_alloc", "zx48_handles_init", "zx48_od_create",
            "zx48_od_ptr", "zx48_od_release", "open_description_table",
            "memory_live_allocations", "OD_RECORD_SIZE", "OD_OFFSET_O", "OD_AUX_O",
            "OD_KIND_OBJECT", "O_READ", "ALLOC_ANY", "PACKED_READER_STATE_SIZE",
        ),
    )
    require(symbols["PACKED_READER_STATE_SIZE"] == 272, "packed-reader state size drift")
    require(symbols["OD_RECORD_SIZE"] >= symbols["OD_AUX_O"] + 2, "decoder pointer outside OD record")

    if action == "test":
        _target_test(root, symbols, kernel.read_bytes())
        assertions.extend([
            {"name": "same-object-independent-opens-use-distinct-descriptions", "passed": True},
            {"name": "two-independent-opens-seek-independently", "passed": True},
            {"name": "packed-decoder-state-pointers-are-independent", "passed": True},
            {"name": "accidental-shared-offset-negative-detected", "passed": True},
            {"name": "independent-final-close-frees-both-decoder-states", "passed": True},
        ])

    hashes = {
        "v1/build/kernel.bin": sha256_file(kernel),
        "v1/src/kernel/handles.asm": sha256_file(root / "v1/src/kernel/handles.asm"),
        "v1/tools-host/test-driver/phase3_independent_open.py": sha256_file(root / "v1/tools-host/test-driver/phase3_independent_open.py"),
        "v1/tools-host/test-driver/run.py": sha256_file(root / "v1/tools-host/test-driver/run.py"),
        "v1/dist/certification/P3.06.test.json": sha256_file(root / "v1/dist/certification/P3.06.test.json"),
    }
    return commands, hashes, assertions
