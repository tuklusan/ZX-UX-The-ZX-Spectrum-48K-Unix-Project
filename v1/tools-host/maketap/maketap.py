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
from typing import Iterable

PROGRAM_TYPE = 0
CODE_TYPE = 3
SCREEN_START = 0x4000
SCREEN_SIZE = 6912
KERNEL_START = 0xE000
KERNEL_SIZE = 8192
BOOT_GATEWAY = 0xE003
BOOT_GATEWAY_DECIMAL = 57347

TOK_SCREEN = 0xAA
TOK_CODE = 0xAF
TOK_USR = 0xC0
TOK_INK = 0xD9
TOK_PAPER = 0xDA
TOK_BORDER = 0xE7
TOK_LOAD = 0xEF
TOK_RANDOMIZE = 0xF9
TOK_CLS = 0xFB
TOK_CLEAR = 0xFD


class TapeError(ValueError):
    pass


@dataclass(frozen=True)
class LogicalFile:
    name: str
    file_type: int
    data: bytes
    param1: int
    param2: int


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise TapeError(message)


def _u16(value: int) -> bytes:
    _require(0 <= value <= 0xFFFF, "u16 out of range")
    return struct.pack("<H", value)


def _integer_number(value: int) -> bytes:
    _require(0 <= value <= 0xFFFF, "loader integer out of range")
    digits = str(value).encode("ascii")
    return digits + b"\x0e\x00\x00" + _u16(value) + b"\x00"


def _basic_line(line_number: int, body: bytes) -> bytes:
    _require(0 <= line_number <= 9999, "BASIC line number out of range")
    content = body + b"\x0d"
    return struct.pack(">H", line_number) + _u16(len(content)) + content


def tokenized_loader(source: str) -> bytes:
    expected = (
        "10 BORDER 0: PAPER 0: INK 7: CLS\n"
        "20 CLEAR 24575\n"
        "30 LOAD \"\" SCREEN$\n"
        "40 LOAD \"\" CODE\n"
        "50 RANDOMIZE USR 57347\n"
    )
    _require(source == expected, "canonical five-line loader text mismatch")

    n0 = _integer_number(0)
    n7 = _integer_number(7)
    n24575 = _integer_number(24575)
    n57347 = _integer_number(BOOT_GATEWAY_DECIMAL)
    lines = (
        _basic_line(
            10,
            bytes((TOK_BORDER, 0x20)) + n0 + b": "
            + bytes((TOK_PAPER, 0x20)) + n0 + b": "
            + bytes((TOK_INK, 0x20)) + n7 + b": "
            + bytes((TOK_CLS,)),
        ),
        _basic_line(20, bytes((TOK_CLEAR, 0x20)) + n24575),
        _basic_line(30, bytes((TOK_LOAD, 0x20, 0x22, 0x22, 0x20, TOK_SCREEN))),
        _basic_line(40, bytes((TOK_LOAD, 0x20, 0x22, 0x22, 0x20, TOK_CODE))),
        _basic_line(50, bytes((TOK_RANDOMIZE, 0x20, TOK_USR, 0x20)) + n57347),
    )
    return b"".join(lines)


def _checksum(payload_without_checksum: bytes) -> int:
    value = 0
    for byte in payload_without_checksum:
        value ^= byte
    return value


def tap_block(flag: int, body: bytes) -> bytes:
    _require(flag in (0x00, 0xFF), "invalid Spectrum TAP flag")
    payload = bytes((flag,)) + body
    payload += bytes((_checksum(payload),))
    return _u16(len(payload)) + payload


def header_body(file: LogicalFile) -> bytes:
    encoded = file.name.encode("ascii")
    _require(file.name == file.name.lower(), "Spectrum header name must be lower-case")
    _require(1 <= len(encoded) <= 10, "Spectrum header name length must be 1..10")
    _require(file.file_type in (PROGRAM_TYPE, CODE_TYPE), "unsupported Phase-0 Spectrum file type")
    return (
        bytes((file.file_type,))
        + encoded.ljust(10, b" ")
        + _u16(len(file.data))
        + _u16(file.param1)
        + _u16(file.param2)
    )


def logical_file_blocks(file: LogicalFile) -> bytes:
    return tap_block(0x00, header_body(file)) + tap_block(0xFF, file.data)


def validate_bootstrap_contract(
    *,
    loader_source: str,
    screen: bytes,
    kernel: bytes,
    kernel_start: int = KERNEL_START,
    boot_gateway: int = BOOT_GATEWAY,
    names: tuple[str, str, str] = ("zx48ux", "zx48uxscr", "kernel"),
) -> tuple[LogicalFile, LogicalFile, LogicalFile]:
    _require(len(screen) == SCREEN_SIZE, "loading screen must be exactly 6912 bytes")
    _require(len(kernel) == KERNEL_SIZE, "kernel image must be exactly 8192 bytes")
    _require(kernel_start == KERNEL_START, "kernel CODE start must be E000")
    _require(boot_gateway == BOOT_GATEWAY, "loader boot gateway must be E003")
    _require(names == ("zx48ux", "zx48uxscr", "kernel"), "bootstrap native-file name/order mismatch")

    program = tokenized_loader(loader_source)
    files = (
        LogicalFile("zx48ux", PROGRAM_TYPE, program, 10, len(program)),
        LogicalFile("zx48uxscr", CODE_TYPE, screen, SCREEN_START, 0x8000),
        LogicalFile("kernel", CODE_TYPE, kernel, KERNEL_START, 0x8000),
    )
    return files


def build_bootstrap_prefix(
    *,
    loader_source: str,
    screen: bytes,
    kernel: bytes,
    kernel_start: int = KERNEL_START,
    boot_gateway: int = BOOT_GATEWAY,
    names: tuple[str, str, str] = ("zx48ux", "zx48uxscr", "kernel"),
) -> bytes:
    files = validate_bootstrap_contract(
        loader_source=loader_source,
        screen=screen,
        kernel=kernel,
        kernel_start=kernel_start,
        boot_gateway=boot_gateway,
        names=names,
    )
    return b"".join(logical_file_blocks(item) for item in files)


def append_logical_files(prefix: bytes, files: Iterable[LogicalFile]) -> bytes:
    out = bytearray(prefix)
    for file in files:
        out.extend(logical_file_blocks(file))
    return bytes(out)
