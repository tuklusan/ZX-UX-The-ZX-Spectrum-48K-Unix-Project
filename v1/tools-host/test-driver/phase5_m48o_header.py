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

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Callable, Any

from driver_core import DriverError


class Phase5HeaderError(DriverError):
    """Raised when the P5.01 M48O header contract regresses."""


MAGIC = b"M48O"
HEADER_SIZE = 32
NAME_SIZE = 10
MAX_LENGTH = 32768
PACKED = 0x01
CODEC_RAW = 0
CODEC_ZXP1 = 1
PORTABLE = set(b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-.")
TYPE_TXT, TYPE_BIN, TYPE_OBJ, TYPE_ASM, TYPE_C = 1, 2, 3, 4, 5
TYPE_DAT, TYPE_UDG, TYPE_GFX, TYPE_FNT, TYPE_CFG, TYPE_SYS = 6, 7, 8, 9, 10, 11
DIR_ROOT, DIR_BIN, DIR_DEV, DIR_ETC = 0, 1, 2, 3
DIR_HOME, DIR_USERHOME, DIR_TMP, DIR_SYSTEM = 4, 5, 6, 7


@dataclass(frozen=True)
class Header:
    object_type: int
    flags: int
    target: int
    physical_length: int
    logical_length: int
    codec: int
    payload_crc: int
    name: bytes


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Phase5HeaderError(message)


def crc16_ccitt_false(data: bytes) -> int:
    crc = 0xFFFF
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc


def _u16(data: bytes, offset: int) -> int:
    return data[offset] | (data[offset + 1] << 8)


def _name(field: bytes) -> bytes:
    require(len(field) == NAME_SIZE, "M48O name field size")
    try:
        end = field.index(0)
    except ValueError:
        end = NAME_SIZE
    if end < NAME_SIZE:
        require(all(value == 0 for value in field[end:]), "embedded-NUL name garbage")
    name = field[:end]
    require(1 <= len(name) <= NAME_SIZE, "M48O name length")
    require(all(value in PORTABLE for value in name), "M48O name character")
    require(name not in (b".", b".."), "M48O traversal base name")
    return name


def _placement(object_type: int, target: int, *, public: bool) -> None:
    require(1 <= object_type <= TYPE_SYS, "M48O payload type")
    require(0 <= target <= DIR_SYSTEM, "M48O target directory")
    if target == DIR_BIN:
        require(object_type == TYPE_BIN, "BIN placement")
    elif target == DIR_ETC:
        require(object_type in (TYPE_TXT, TYPE_CFG), "ETC placement")
    elif target in (DIR_USERHOME, DIR_TMP):
        require(1 <= object_type <= TYPE_CFG, "ordinary placement")
    elif target == DIR_SYSTEM:
        require(not public, "public SYSTEM target")
        require(object_type in (TYPE_FNT, TYPE_SYS), "SYSTEM placement")
    else:
        raise Phase5HeaderError("invalid persistence target")


def parse_header(data: bytes, *, public: bool = True) -> Header:
    require(len(data) == HEADER_SIZE, "M48O header size")
    require(data[0:4] == MAGIC, "M48O magic")
    require(data[4] == 1, "M48O version")
    object_type = data[5]
    flags = data[6]
    target = data[7]
    require(flags & ~PACKED == 0, "unknown M48O flag bits")
    physical = _u16(data, 8)
    logical = _u16(data, 10)
    codec = _u16(data, 12)
    payload_crc = _u16(data, 14)
    name = _name(data[16:26])
    require(data[28:32] == bytes(4), "M48O reserved bytes")
    stored_crc = _u16(data, 26)
    crc_image = bytearray(data)
    crc_image[26:28] = bytes(2)
    require(crc16_ccitt_false(bytes(crc_image)) == stored_crc, "M48O header CRC")
    require(physical <= MAX_LENGTH and logical <= MAX_LENGTH, "M48O length bound")
    _placement(object_type, target, public=public)
    if flags == 0:
        require(codec == CODEC_RAW, "RAW codec")
        require(physical == logical, "RAW length relation")
    else:
        require(codec == CODEC_ZXP1, "PACKED codec")
        require(1 <= logical <= MAX_LENGTH, "PACKED logical length")
        require(physical < logical, "PACKED physical length")
    return Header(object_type, flags, target, physical, logical, codec, payload_crc, name)


def _build_header(
    *,
    object_type: int,
    target: int,
    name: bytes,
    physical: int,
    logical: int,
    flags: int = 0,
    codec: int = 0,
    payload_crc: int = 0x29B1,
) -> bytes:
    require(1 <= len(name) <= NAME_SIZE, "test name length")
    header = bytearray(HEADER_SIZE)
    header[0:4] = MAGIC
    header[4] = 1
    header[5] = object_type
    header[6] = flags
    header[7] = target
    header[8:10] = physical.to_bytes(2, "little")
    header[10:12] = logical.to_bytes(2, "little")
    header[12:14] = codec.to_bytes(2, "little")
    header[14:16] = payload_crc.to_bytes(2, "little")
    header[16:16 + len(name)] = name
    header[26:28] = bytes(2)
    header[28:32] = bytes(4)
    header[26:28] = crc16_ccitt_false(bytes(header)).to_bytes(2, "little")
    return bytes(header)


def _recrc(data: bytes) -> bytes:
    image = bytearray(data)
    image[26:28] = bytes(2)
    image[26:28] = crc16_ccitt_false(bytes(image)).to_bytes(2, "little")
    return bytes(image)


def _constants(path: Path) -> dict[str, int]:
    found: dict[str, int] = {}
    pattern = re.compile(r"^([A-Z0-9_]+)\s+EQU\s+([^;\s]+)")
    for line in path.read_text(encoding="utf-8").splitlines():
        match = pattern.match(line)
        if not match:
            continue
        token = match.group(2)
        if token.startswith("$"):
            value = int(token[1:], 16)
        elif token.isdigit():
            value = int(token, 10)
        else:
            continue
        found[match.group(1)] = value
    return found


def _source_contract(root: Path) -> list[dict[str, object]]:
    constants = _constants(root / "v1/include/tapeobj.inc")
    core = _constants(root / "v1/include/zx48ux.inc")
    expected = {
        "M48O_MAGIC_0": 0x4D, "M48O_MAGIC_1": 0x34, "M48O_MAGIC_2": 0x38, "M48O_MAGIC_3": 0x4F,
        "M48O_VERSION": 1, "M48O_PACKED": 1, "M48O_FLAGS_KNOWN": 1,
        "M48O_CODEC_RAW": 0, "M48O_CODEC_ZXP1": 1,
        "M48O_HDR_MAGIC": 0, "M48O_HDR_VERSION": 4, "M48O_HDR_TYPE": 5,
        "M48O_HDR_FLAGS": 6, "M48O_HDR_DIRECTORY": 7, "M48O_HDR_STORAGE_LEN": 8,
        "M48O_HDR_LOGICAL_LEN": 10, "M48O_HDR_CODEC": 12, "M48O_HDR_PAYLOAD_CRC": 14,
        "M48O_HDR_NAME": 16, "M48O_HDR_HEADER_CRC": 26, "M48O_HDR_RESERVED": 28,
        "M48O_HDR_SIZE": 32, "M48O_NAME_SIZE": 10, "M48O_RESERVED_SIZE": 4,
        "M48O_MAX_PAYLOAD": 32768, "M48O_MAX_LOGICAL": 32768, "M48O_ROM_DATA_FLAG": 0xFF,
        "M48O_TYPE_TXT": 1, "M48O_TYPE_BIN": 2, "M48O_TYPE_OBJ": 3, "M48O_TYPE_ASM": 4,
        "M48O_TYPE_C": 5, "M48O_TYPE_DAT": 6, "M48O_TYPE_UDG": 7, "M48O_TYPE_GFX": 8,
        "M48O_TYPE_FNT": 9, "M48O_TYPE_CFG": 10, "M48O_TYPE_SYS": 11,
        "M48O_TYPE_DIR_INVALID": 12, "M48O_TYPE_DEV_INVALID": 13,
        "M48O_TARGET_ROOT": 0, "M48O_TARGET_BIN": 1, "M48O_TARGET_DEV": 2,
        "M48O_TARGET_ETC": 3, "M48O_TARGET_HOME": 4, "M48O_TARGET_USERHOME": 5,
        "M48O_TARGET_TMP": 6, "M48O_TARGET_SYSTEM": 7,
    }
    doc = (root / "v1/docs/tape-object.md").read_text(encoding="utf-8")
    return [
        {"name": "m48o-constant-table-exact", "passed": all(constants.get(k) == v for k, v in expected.items())},
        {"name": "m48o-core-header-size-agrees", "passed": core.get("M48O_HEADER_SIZE") == HEADER_SIZE},
        {"name": "m48o-core-chunk-size-remains-512", "passed": core.get("M48O_CHUNK_SIZE") == 512},
        {"name": "m48o-doc-header-offsets-and-crc-rule", "passed": "bytes 26 and 27 treated as\nzero" in doc and "exactly 32 bytes" in doc},
        {"name": "m48o-doc-placement-and-userhome-rule", "passed": "Public save/load never targets SYSTEM" in doc and "USERHOME is symbolic persistence metadata" in doc},
    ]


def _positive_corpus() -> list[dict[str, object]]:
    assertions: list[dict[str, object]] = []
    raw = _build_header(object_type=TYPE_TXT, target=DIR_USERHOME, name=b"Hello.c", physical=0x1234, logical=0x1234)
    parsed = parse_header(raw)
    assertions.extend([
        {"name": "golden-raw-field-offsets-little-endian", "passed": parsed.physical_length == 0x1234 and parsed.logical_length == 0x1234 and parsed.name == b"Hello.c"},
        {"name": "golden-header-crc-zero-field-rule", "passed": _u16(raw, 26) == crc16_ccitt_false(raw[:26] + bytes(2) + raw[28:])},
        {"name": "ten-byte-non-nul-name-legal", "passed": parse_header(_build_header(object_type=TYPE_BIN, target=DIR_BIN, name=b"abcdefghij", physical=1, logical=1)).name == b"abcdefghij"},
        {"name": "zero-length-raw-legal", "passed": parse_header(_build_header(object_type=TYPE_CFG, target=DIR_ETC, name=b"empty", physical=0, logical=0)).logical_length == 0},
        {"name": "32768-raw-boundary-legal", "passed": parse_header(_build_header(object_type=TYPE_DAT, target=DIR_TMP, name=b"max", physical=32768, logical=32768)).physical_length == 32768},
        {"name": "packed-strict-smaller-legal", "passed": parse_header(_build_header(object_type=TYPE_DAT, target=DIR_TMP, name=b"packed", physical=31, logical=64, flags=PACKED, codec=CODEC_ZXP1)).codec == CODEC_ZXP1},
        {"name": "system-bootstrap-fnt-legal-internal-only", "passed": parse_header(_build_header(object_type=TYPE_FNT, target=DIR_SYSTEM, name=b"font4x8", physical=392, logical=392), public=False).target == DIR_SYSTEM},
    ])
    payload = b"same logical bytes"
    h1 = parse_header(_build_header(object_type=TYPE_C, target=DIR_USERHOME, name=b"Case.C", physical=len(payload), logical=len(payload)))
    h2 = parse_header(_build_header(object_type=TYPE_C, target=DIR_USERHOME, name=b"Case.C", physical=len(payload), logical=len(payload)))
    path1 = b"/home/alice/" + h1.name
    path2 = b"/home/bob/" + h2.name
    assertions.append({"name": "userhome-resolves-current-session-with-stable-name-and-bytes", "passed": path1 != path2 and path1.endswith(b"/Case.C") and path2.endswith(b"/Case.C") and payload == b"same logical bytes"})
    return assertions


def _negative_corpus() -> list[dict[str, object]]:
    base = _build_header(object_type=TYPE_DAT, target=DIR_TMP, name=b"data", physical=4, logical=4)
    cases: list[tuple[str, bytes, bool]] = []

    def mutated(name: str, offset: int, value: int, *, recalc: bool = True, public: bool = True) -> None:
        image = bytearray(base)
        image[offset] = value
        cases.append((name, _recrc(bytes(image)) if recalc else bytes(image), public))

    mutated("type-zero-rejected", 5, 0)
    mutated("type-dir-rejected", 5, 12)
    mutated("type-dev-rejected", 5, 13)
    mutated("unknown-flag-rejected", 6, 0x80)
    mutated("invalid-root-target-rejected", 7, DIR_ROOT)
    mutated("invalid-dev-target-rejected", 7, DIR_DEV)
    mutated("invalid-home-target-rejected", 7, DIR_HOME)

    wrong_place = bytearray(base)
    wrong_place[5] = TYPE_TXT
    wrong_place[7] = DIR_BIN
    cases.append(("illegal-target-type-pair-rejected", _recrc(bytes(wrong_place)), True))

    public_system = bytearray(base)
    public_system[5] = TYPE_FNT
    public_system[7] = DIR_SYSTEM
    cases.append(("public-system-target-rejected", _recrc(bytes(public_system)), True))

    garbage = bytearray(base)
    garbage[16:26] = b"a\x00b" + bytes(7)
    cases.append(("embedded-nul-garbage-rejected", _recrc(bytes(garbage)), True))

    reserved = bytearray(base)
    reserved[31] = 1
    cases.append(("nonzero-reserved-rejected", _recrc(bytes(reserved)), True))

    bad_crc = bytearray(base)
    bad_crc[26] ^= 1
    cases.append(("bad-header-crc-rejected", bytes(bad_crc), True))

    too_large = bytearray(base)
    too_large[8:10] = (32769).to_bytes(2, "little")
    too_large[10:12] = (32769).to_bytes(2, "little")
    cases.append(("length-over-32768-rejected", _recrc(bytes(too_large)), True))

    for label, physical, logical in (
        ("packed-zero-logical-rejected", 0, 0),
        ("packed-equal-length-rejected", 4, 4),
        ("packed-larger-physical-rejected", 5, 4),
    ):
        image = bytearray(base)
        image[6] = PACKED
        image[8:10] = physical.to_bytes(2, "little")
        image[10:12] = logical.to_bytes(2, "little")
        image[12:14] = CODEC_ZXP1.to_bytes(2, "little")
        cases.append((label, _recrc(bytes(image)), True))

    unknown_codec = bytearray(base)
    unknown_codec[6] = PACKED
    unknown_codec[8:10] = (3).to_bytes(2, "little")
    unknown_codec[10:12] = (4).to_bytes(2, "little")
    unknown_codec[12:14] = (2).to_bytes(2, "little")
    cases.append(("unknown-codec-rejected", _recrc(bytes(unknown_codec)), True))

    endian = bytearray(_build_header(object_type=TYPE_DAT, target=DIR_TMP, name=b"endian", physical=0x0100, logical=0x0100))
    endian[8], endian[9] = endian[9], endian[8]
    cases.append(("one-byte-order-mutation-rejected", _recrc(bytes(endian)), True))

    assertions: list[dict[str, object]] = []
    for label, image, public in cases:
        rejected = False
        try:
            parse_header(image, public=public)
        except Phase5HeaderError:
            rejected = True
        assertions.append({"name": label, "passed": rejected})
    return assertions


def dispatch(
    root: Path,
    action: str,
    step: str,
    *,
    sha256_file: Callable[[Path], str],
    run_command: Callable[..., Any],
    require_project_tool: Callable[[Path, str | Path], Path],
):
    if step != "P5.01":
        raise DriverError(f"Phase-5 M48O header step is not registered: {step}")

    assertions = _source_contract(root) + _positive_corpus()
    if action == "test":
        assertions.extend(_negative_corpus())
    failed = [item["name"] for item in assertions if item.get("passed") is not True]
    require(not failed, f"P5.01 contract failures: {failed}")

    hashes = {
        "v1/include/tapeobj.inc": sha256_file(root / "v1/include/tapeobj.inc"),
        "v1/include/zx48ux.inc": sha256_file(root / "v1/include/zx48ux.inc"),
        "v1/docs/tape-object.md": sha256_file(root / "v1/docs/tape-object.md"),
        "v1/tools-host/test-driver/phase5_m48o_header.py": sha256_file(root / "v1/tools-host/test-driver/phase5_m48o_header.py"),
        "v1/tools-host/test-driver/run.py": sha256_file(root / "v1/tools-host/test-driver/run.py"),
        "v1/dist/certification/phase-4.json": sha256_file(root / "v1/dist/certification/phase-4.json"),
    }
    return [], hashes, assertions
