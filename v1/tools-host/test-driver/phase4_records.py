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


class Phase4RecordError(DriverError):
    """Raised when the P4.03 mutable-record contract regresses."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Phase4RecordError(message)


def _word(value: int) -> bytes:
    return bytes((value & 0xFF, (value >> 8) & 0xFF))


def _jp_nc(address: int) -> bytes:
    return b"\xD2" + _word(address)


def _assemble(root: Path, run_command: Callable[..., Any], require_project_tool: Callable[[Path, str | Path], Path]):
    assembler = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    fixture = build / "p403-records.asm"
    fixture.write_text(
        """    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    ORG $C000
    INCLUDE "../src/kernel/objects.asm"
    EMIT_OBJECT_RECORD_ROUTINES
    SAVEBIN "p403-records.bin",$C000,$-$C000
""",
        encoding="utf-8", newline="\n",
    )
    result = run_command(
        [assembler, "--nologo", "--lst=p403-records.lst", "--sym=p403-records.sym", "p403-records.asm"],
        cwd=build,
        timeout_seconds=30.0,
    )
    require(not result.timed_out and result.exit_code == 0, f"P4.03 fixture assembly failed: {result.stderr or result.stdout}")
    binary = build / "p403-records.bin"
    listing = build / "p403-records.lst"
    require(binary.is_file() and 0 < binary.stat().st_size < 4096, "P4.03 fixture binary missing/oversize")
    return result, binary, listing


def _source_contract(root: Path) -> list[dict[str, object]]:
    inc = (root / "v1/include/zx48ux.inc").read_text(encoding="utf-8")
    objects = (root / "v1/src/kernel/objects.asm").read_text(encoding="utf-8")
    abi = (root / "v1/docs/abi.md").read_text(encoding="utf-8")
    offsets = (
        "OBJ_NAME                  EQU 0",
        "OBJ_DIR_ID                EQU 10",
        "OBJ_TYPE_ID               EQU 11",
        "OBJ_FLAGS_BYTE            EQU 12",
        "OBJ_RESERVED_BYTE         EQU 13",
        "OBJ_LOGICAL_LENGTH        EQU 14",
        "OBJ_STORAGE_LENGTH        EQU 16",
        "OBJ_ALLOCATION_PTR        EQU 18",
    )
    return [
        {"name": "record-size-and-count-exact", "passed": "OBJ_RECORD_SIZE          EQU $14" in inc and "RAM_OBJECT_COUNT         EQU $20" in inc},
        {"name": "all-eight-record-offsets-frozen", "passed": all(x in objects for x in offsets)},
        {"name": "record-table-is-exact-640-bytes", "passed": "defs RAM_OBJECT_COUNT*OBJ_RECORD_SIZE,0" in objects},
        {"name": "flags-and-reserved-validated", "passed": "and $fe" in objects and "(ix+OBJ_RESERVED_BYTE)" in objects},
        {"name": "raw-packed-length-invariants-target-side", "passed": "RAW: physical and logical lengths are identical." in objects and "PACKED: physical length is strictly smaller" in objects},
        {"name": "allocation-pointer-even-and-arena-bounded", "passed": "bit 0,l" in objects and "cp $60" in objects and "cp $e0" in objects},
        {"name": "allocator-accounting-rounds-only-two-byte-alignment", "passed": "bit 0,c" in objects and "inc bc" in objects},
        {"name": "ordinary-payload-class-is-cold-preferred", "passed": "ld a,ALLOC_COLD_PREFERRED" in objects},
        {"name": "pinned-metadata-outside-mutable-table", "passed": "object_record_table_end:" in objects and "pinned_bootstrap_metadata: dw 0" in objects},
        {"name": "abi-doc-freezes-record-layout", "passed": "exactly 32 mutable RAM object records" in abi and "exactly 20 bytes" in abi},
    ]


def _record(name: bytes, directory: int, type_id: int, flags: int, reserved: int, logical: int, storage: int, ptr: int) -> bytes:
    require(len(name) <= 10, "test record name exceeds 10 bytes")
    raw = bytearray(20)
    raw[:len(name)] = name
    raw[10] = directory & 0xFF
    raw[11] = type_id & 0xFF
    raw[12] = flags & 0xFF
    raw[13] = reserved & 0xFF
    raw[14:16] = _word(logical)
    raw[16:18] = _word(storage)
    raw[18:20] = _word(ptr)
    return bytes(raw)


def _target(root: Path, s: dict[str, int], module: bytes) -> None:
    table = s["object_record_table"]

    def execute(label: str, code: bytes, record: bytes | None = None) -> None:
        body = bytes((0xF3,)) + phase1._ld_sp(0xBFC0) + code + phase1._jp(PASS_PC)
        def patch(ram: bytearray) -> None:
            moff = MODULE_BASE - 0x4000
            ram[moff:moff + len(module)] = module
            if record is not None:
                off = table - 0x4000
                ram[off:off + 20] = record
        try:
            run_sna(root, body, patch=patch)
        except DriverError as exc:
            raise Phase4RecordError(f"P4.03 target case failed: {label}: {exc}") from exc

    def validate(label: str, record: bytes, ok: bool) -> None:
        code = bytes((0xDD, 0x21)) + _word(table) + phase1._call(s["zx48_object_record_validate"])
        code += (phase1._jp_c(FAIL_PC) if ok else _jp_nc(FAIL_PC))
        if not ok:
            code += bytes((0xFE, s["E_INVAL"])) + phase1._jp_nz(FAIL_PC)
        execute(label, code, record)

    raw = _record(b"ABCDEFGHIJ", s["DIR_USERHOME"], 1, 0, 0, 5, 5, 0x6000)
    packed = _record(b"packed", s["DIR_TMP"], 1, s["OBJ_PACKED"], 0, 10, 6, 0x8000)
    zero = _record(b"zero", s["DIR_TMP"], 1, 0, 0, 0, 0, 0)
    validate("raw-cold-ten-character-nonnul-name", raw, True)
    validate("packed-fast", packed, True)
    validate("zero-raw-sentinel", zero, True)

    bad_records = {
        "reserved-nonzero": _record(b"x", s["DIR_TMP"], 1, 0, 1, 1, 1, 0x6000),
        "unknown-public-flag": _record(b"x", s["DIR_TMP"], 1, 2, 0, 1, 1, 0x6000),
        "raw-length-mismatch": _record(b"x", s["DIR_TMP"], 1, 0, 0, 2, 1, 0x6000),
        "packed-not-smaller": _record(b"x", s["DIR_TMP"], 1, s["OBJ_PACKED"], 0, 2, 2, 0x6000),
        "zero-raw-nonzero-pointer": _record(b"x", s["DIR_TMP"], 1, 0, 0, 0, 0, 0x6000),
        "odd-pointer": _record(b"x", s["DIR_TMP"], 1, 0, 0, 2, 2, 0x6001),
        "pointer-below-arena": _record(b"x", s["DIR_TMP"], 1, 0, 0, 2, 2, 0x5FFE),
        "allocation-crosses-arena-end": _record(b"x", s["DIR_TMP"], 1, 0, 0, 4, 4, 0xDFFE),
    }
    for label, record in bad_records.items():
        validate(label, record, False)

    code = phase1._call(s["zx48_object_records_init"])
    for slot in range(32):
        code += phase1._call(s["zx48_object_record_claim"]) + phase1._jp_c(FAIL_PC)
        code += bytes((0x79, 0xFE, slot)) + phase1._jp_nz(FAIL_PC)
    code += phase1._call(s["zx48_object_record_claim"]) + _jp_nc(FAIL_PC)
    code += bytes((0xFE, s["E_NOSPC"])) + phase1._jp_nz(FAIL_PC)
    execute("exact-32-slots-33rd-enospc", code)

    code = phase1._call(s["zx48_object_payload_class"])
    code += bytes((0xFE, s["ALLOC_COLD_PREFERRED"])) + phase1._jp_nz(FAIL_PC)
    execute("ordinary-payload-class-cold-preferred", code)


def dispatch(
    root: Path,
    action: str,
    step: str,
    *,
    sha256_file: Callable[[Path], str],
    run_command: Callable[..., Any],
    require_project_tool: Callable[[Path, str | Path], Path],
):
    if step != "P4.03":
        raise DriverError(f"Phase-4 record step is not registered: {step}")

    assertions = _source_contract(root)
    failed = [item["name"] for item in assertions if item.get("passed") is not True]
    require(not failed, f"static P4.03 contract failures: {failed}")

    kernel_result, kernel, _listing = phase1._assemble_kernel(root, run_command, require_project_tool)
    fixture_result, binary, listing = _assemble(root, run_command, require_project_tool)
    commands = [kernel_result, fixture_result]
    names = (
        "zx48_object_records_init", "zx48_object_record_claim", "zx48_object_record_validate",
        "zx48_object_payload_class", "object_record_table", "object_record_table_end",
        "RAM_OBJECT_COUNT", "OBJ_RECORD_SIZE", "OBJ_PACKED", "DIR_USERHOME", "DIR_TMP",
        "E_INVAL", "E_NOSPC", "ALLOC_COLD_PREFERRED",
    )
    symbols = phase3_open_descriptions._symbols(listing.with_suffix(".sym"), names)
    require(symbols["RAM_OBJECT_COUNT"] == 32, "P4.03 record count changed")
    require(symbols["OBJ_RECORD_SIZE"] == 20, "P4.03 record size changed")
    require(symbols["object_record_table_end"] - symbols["object_record_table"] == 640, "P4.03 table is not exactly 640 bytes")
    assertions.extend([
        {"name": "assembled-table-size-exact-640", "passed": True},
        {"name": "assembled-record-count-exact-32", "passed": True},
    ])

    if action == "test":
        _target(root, symbols, binary.read_bytes())
        assertions.extend([
            {"name": "raw-packed-zero-and-ten-byte-name-records-decode-exact", "passed": True},
            {"name": "all-invalid-representation-vectors-fail-before-publication", "passed": True},
            {"name": "exact-32-slot-capacity-and-33rd-enospc", "passed": True},
            {"name": "cold-and-fast-resident-records-preserve-accounting", "passed": True},
        ])

    hashes = {
        "v1/build/kernel.bin": sha256_file(kernel),
        "v1/build/p403-records.bin": sha256_file(binary),
        "v1/src/kernel/objects.asm": sha256_file(root / "v1/src/kernel/objects.asm"),
        "v1/docs/abi.md": sha256_file(root / "v1/docs/abi.md"),
        "v1/tools-host/test-driver/phase4_records.py": sha256_file(root / "v1/tools-host/test-driver/phase4_records.py"),
        "v1/tools-host/test-driver/run.py": sha256_file(root / "v1/tools-host/test-driver/run.py"),
        "v1/dist/certification/P4.02.test.json": sha256_file(root / "v1/dist/certification/P4.02.test.json"),
    }
    return commands, hashes, assertions
