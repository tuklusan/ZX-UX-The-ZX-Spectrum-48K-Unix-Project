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
import struct


class CassetteImageError(ValueError):
    pass


@dataclass(frozen=True)
class TapBlock:
    flag: int
    body: bytes


@dataclass(frozen=True)
class SpectrumFile:
    name: str
    file_type: int
    length: int
    param1: int
    param2: int
    data: bytes


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise CassetteImageError(message)


def _checksum_ok(payload: bytes) -> bool:
    value = 0
    for byte in payload:
        value ^= byte
    return value == 0


def parse_blocks(image: bytes) -> list[TapBlock]:
    offset = 0
    blocks: list[TapBlock] = []
    while offset < len(image):
        _require(offset + 2 <= len(image), "truncated TAP block length")
        length = struct.unpack_from("<H", image, offset)[0]
        offset += 2
        _require(length >= 2, "TAP payload too short")
        _require(offset + length <= len(image), "truncated TAP payload")
        payload = image[offset:offset + length]
        offset += length
        _require(_checksum_ok(payload), "TAP block checksum mismatch")
        flag = payload[0]
        _require(flag in (0x00, 0xFF), "unexpected TAP block flag")
        blocks.append(TapBlock(flag, payload[1:-1]))
    _require(offset == len(image), "TAP trailing bytes")
    return blocks


def parse_files(image: bytes) -> list[SpectrumFile]:
    blocks = parse_blocks(image)
    _require(len(blocks) % 2 == 0, "native header/data pairing incomplete")
    files: list[SpectrumFile] = []
    for index in range(0, len(blocks), 2):
        header, data_block = blocks[index:index + 2]
        _require(header.flag == 0x00, "logical file header flag must be 00")
        _require(data_block.flag == 0xFF, "logical file data flag must be FF")
        _require(len(header.body) == 17, "Spectrum header body must be 17 bytes")
        file_type = header.body[0]
        name_bytes = header.body[1:11]
        try:
            name = name_bytes.rstrip(b" ").decode("ascii")
        except UnicodeDecodeError as exc:
            raise CassetteImageError("non-ASCII Spectrum header name") from exc
        length, param1, param2 = struct.unpack_from("<HHH", header.body, 11)
        _require(length == len(data_block.body), "header/data length mismatch")
        _require(name and name == name.lower(), "Spectrum native filename must be lower-case")
        files.append(SpectrumFile(name, file_type, length, param1, param2, data_block.body))
    return files


def assert_bootstrap_prefix(image: bytes) -> list[SpectrumFile]:
    files = parse_files(image)
    _require(len(files) >= 3, "bootstrap prefix requires at least three native files")
    first = files[:3]
    _require([item.name for item in first] == ["zx48ux", "zx48uxscr", "kernel"], "bootstrap order mismatch")
    _require(first[0].file_type == 0 and first[0].param1 == 10, "loader header contract mismatch")
    _require(first[1].file_type == 3 and first[1].length == 6912 and first[1].param1 == 0x4000, "SCREEN$ header contract mismatch")
    _require(first[2].file_type == 3 and first[2].length == 8192 and first[2].param1 == 0xE000, "kernel header contract mismatch")
    return files
