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
import re
import struct
import sys
from types import ModuleType
from typing import Callable

from driver_core import DriverError


class Phase2Mex1Error(DriverError):
    """Raised when the frozen P2.01 MEX1 format contract regresses."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Phase2Mex1Error(message)


def _equ_values(path: Path) -> dict[str, int]:
    values: dict[str, int] = {}
    for name, expression in re.findall(r"(?m)^\s*([A-Z][A-Z0-9_]*)\s+EQU\s+([^;\n]+?)\s*$", path.read_text(encoding="utf-8")):
        expression = expression.strip()
        if re.fullmatch(r"'[ -~]'", expression):
            values[name] = ord(expression[1])
        elif re.fullmatch(r"\$[0-9A-Fa-f]+", expression):
            values[name] = int(expression[1:], 16)
        elif re.fullmatch(r"[0-9]+", expression):
            values[name] = int(expression, 10)
    return values


def _load_inspector(path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location("zxux_p201_inspect_mex", path)
    if spec is None or spec.loader is None:
        raise Phase2Mex1Error(f"cannot load MEX1 inspector: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _crc16(data: bytes) -> int:
    crc = 0xFFFF
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc


def _fixture(
    *,
    image: bytes = b"\x01\x00\xC9",
    bss_size: int = 0,
    entry: int = 2,
    stack: int = 64,
    relocations: tuple[int, ...] = (0,),
    magic: bytes = b"MEX1",
    version: int = 1,
    flags: int = 0,
    header_size: int = 24,
    relocation_offset: int | None = None,
) -> bytes:
    header = bytearray(24)
    header[:4] = magic
    header[4] = version & 0xFF
    header[5] = flags & 0xFF
    struct.pack_into("<H", header, 6, header_size & 0xFFFF)
    struct.pack_into("<H", header, 8, len(image) & 0xFFFF)
    struct.pack_into("<H", header, 10, bss_size & 0xFFFF)
    struct.pack_into("<H", header, 12, entry & 0xFFFF)
    struct.pack_into("<H", header, 14, stack & 0xFFFF)
    struct.pack_into("<H", header, 16, len(relocations) & 0xFFFF)
    reloc_offset = 24 + len(image) if relocation_offset is None else relocation_offset
    struct.pack_into("<H", header, 18, reloc_offset & 0xFFFF)
    body = image + b"".join(struct.pack("<H", offset) for offset in relocations)
    struct.pack_into("<H", header, 20, _crc16(body))
    struct.pack_into("<H", header, 22, 0)
    struct.pack_into("<H", header, 22, _crc16(bytes(header)))
    return bytes(header) + body


def _rewrite_u16(candidate: bytes, offset: int, value: int) -> bytes:
    data = bytearray(candidate)
    struct.pack_into("<H", data, offset, value & 0xFFFF)
    struct.pack_into("<H", data, 22, 0)
    struct.pack_into("<H", data, 22, _crc16(bytes(data[:24])))
    return bytes(data)


def _expect_reject(inspector: ModuleType, name: str, candidate: bytes) -> dict[str, object]:
    try:
        inspector.inspect_bytes(candidate, base=0x6000)
    except inspector.MexError:
        return {"name": name, "passed": True}
    raise Phase2Mex1Error(f"negative MEX1 fixture unexpectedly accepted: {name}")


def _static_contract(root: Path) -> list[dict[str, object]]:
    include_path = root / "v1/include/mex1.inc"
    doc_path = root / "v1/docs/mex1.md"
    values = _equ_values(include_path)
    expected = {
        "MEX_MAGIC0": ord("M"),
        "MEX_MAGIC1": ord("E"),
        "MEX_MAGIC2": ord("X"),
        "MEX_MAGIC3": ord("1"),
        "MEX_VERSION": 1,
        "MEX_FLAGS": 0,
        "MEX_HEADER_SIZE": 24,
        "MEX_IMAGE_OFFSET": 24,
        "MEX_RELOC_ENTRY_SIZE": 2,
        "MEX_MAX_STORED": 32768,
        "MEX_CRC16_POLY": 0x1021,
        "MEX_CRC16_INIT": 0xFFFF,
        "MEX_CRC16_REFIN": 0,
        "MEX_CRC16_REFOUT": 0,
        "MEX_CRC16_XOROUT": 0,
        "MEX_HDR_MAGIC": 0,
        "MEX_HDR_VERSION": 4,
        "MEX_HDR_FLAGS": 5,
        "MEX_HDR_SIZE": 6,
        "MEX_HDR_IMAGE_SIZE": 8,
        "MEX_HDR_BSS_SIZE": 10,
        "MEX_HDR_ENTRY": 12,
        "MEX_HDR_STACK": 14,
        "MEX_HDR_RELOC_COUNT": 16,
        "MEX_HDR_RELOC_OFFSET": 18,
        "MEX_HDR_BODY_CRC": 20,
        "MEX_HDR_HEADER_CRC": 22,
        "MEX_MIN_STACK": 64,
        "MEX_MAX_STACK": 4096,
    }
    doc = doc_path.read_text(encoding="utf-8")
    arithmetic_tokens = (
        "`24 + image_size`",
        "`relocation_count * 2`",
        "`relocation_table_offset + relocation_count * 2`",
        "`image_size + bss_size`",
        "low\n16-bit wrap",
    )
    return [
        {"name": "mex1-header-constants-exact", "passed": all(values.get(name) == value for name, value in expected.items())},
        {"name": "mex1-doc-freezes-no-trailing-data", "passed": "Trailing bytes are invalid." in doc},
        {"name": "mex1-doc-freezes-widened-arithmetic", "passed": all(token in doc for token in arithmetic_tokens)},
        {"name": "mex1-doc-freezes-reloc-image-minimum", "passed": "If `relocation_count` is nonzero, `image_size` is at least 2." in doc},
        {"name": "mex1-doc-freezes-crc16-ccitt-false", "passed": all(token in doc for token in ("0x1021", "0xFFFF", "final XOR zero"))},
    ]


def _negative_contract(inspector: ModuleType) -> list[dict[str, object]]:
    good = _fixture()
    assertions = [
        _expect_reject(inspector, "reject-bad-magic", _fixture(magic=b"NEX1")),
        _expect_reject(inspector, "reject-bad-version", _fixture(version=2)),
        _expect_reject(inspector, "reject-nonzero-flags", _fixture(flags=1)),
        _expect_reject(inspector, "reject-bad-header-size", _fixture(header_size=23)),
        _expect_reject(inspector, "reject-truncated-header", good[:23]),
        _expect_reject(inspector, "reject-truncated-body", good[:-1]),
        _expect_reject(inspector, "reject-trailing-byte", good + b"\x00"),
        _expect_reject(inspector, "reject-empty-image", _fixture(image=b"", entry=0, relocations=())),
        _expect_reject(inspector, "reject-entry-at-image-end", _fixture(entry=3)),
        _expect_reject(inspector, "reject-image-bss-over-32768", _fixture(bss_size=32766)),
        _expect_reject(inspector, "reject-stack-below-64", _fixture(stack=63)),
        _expect_reject(inspector, "reject-stack-over-4096", _fixture(stack=4097)),
        _expect_reject(inspector, "reject-relocation-offset-mismatch", _fixture(relocation_offset=26)),
        _expect_reject(inspector, "reject-reloc-with-image-under-2", _fixture(image=b"\xC9", entry=0, relocations=(0,))),
    ]

    bad_body_crc = bytearray(good)
    bad_body_crc[24] ^= 1
    assertions.append(_expect_reject(inspector, "reject-body-crc-mutation", bytes(bad_body_crc)))
    bad_header_crc = bytearray(good)
    bad_header_crc[22] ^= 1
    assertions.append(_expect_reject(inspector, "reject-header-crc-mutation", bytes(bad_header_crc)))

    # Adversarial arithmetic vectors: each would become deceptively small if an
    # implementation multiplied or added in 16 bits before validating the result.
    count_wrap = _rewrite_u16(_fixture(relocations=()), 16, 0x8000)
    assertions.append(_expect_reject(inspector, "reject-reloc-count-times-two-wrap", count_wrap))
    offset_wrap = _rewrite_u16(_fixture(relocations=()), 18, 8)
    offset_wrap = _rewrite_u16(offset_wrap, 8, 0xFFF0)
    assertions.append(_expect_reject(inspector, "reject-24-plus-image-size-wrap", offset_wrap))
    size_wrap = _fixture(image=b"\xC9", bss_size=0xFFFF, entry=0, relocations=())
    assertions.append(_expect_reject(inspector, "reject-image-plus-bss-u16-wrap", size_wrap))
    image_offset_wrap = _fixture(image=b"\x00" * 0xFFFF, entry=0, relocations=())
    assertions.append(_expect_reject(inspector, "reject-24-plus-image-size-u16-wrap", image_offset_wrap))
    return assertions


def dispatch(
    root: Path,
    action: str,
    step: str,
    *,
    sha256_file: Callable[[Path], str],
    run_command: Callable[..., object],
    require_project_tool: Callable[[Path, str], Path],
):
    if step != "P2.01":
        raise DriverError(f"Phase-2 MEX1 step is not registered: {step}")
    inspector_path = require_project_tool(root, "v1/tools-host/inspect-mex/inspect.py")
    command = run_command([sys.executable, inspector_path, "--self-test"], cwd=root, timeout_seconds=10.0)
    require(not command.timed_out, "MEX1 inspector self-test timed out")
    require(command.exit_code == 0, f"MEX1 inspector self-test failed: {command.stderr.strip()}")

    assertions = _static_contract(root)
    inspector = _load_inspector(inspector_path)
    golden = _fixture()
    result = inspector.inspect_bytes(golden, base=0x6000)
    assertions += [
        {"name": "golden-mex1-accepted", "passed": result["stored_length"] == len(golden)},
        {"name": "golden-layout-exact", "passed": result["relocation_table_offset"] == 27 and result["relocation_count"] == 1},
        {"name": "golden-crcs-exact", "passed": result["body_crc"] == _crc16(golden[24:]) and result["header_crc"] == _crc16(golden[:22] + b"\x00\x00")},
    ]
    if action == "test":
        assertions.extend(_negative_contract(inspector))

    return [command], {
        "v1/include/mex1.inc": sha256_file(root / "v1/include/mex1.inc"),
        "v1/docs/mex1.md": sha256_file(root / "v1/docs/mex1.md"),
        "v1/tools-host/inspect-mex/inspect.py": sha256_file(inspector_path),
    }, assertions
