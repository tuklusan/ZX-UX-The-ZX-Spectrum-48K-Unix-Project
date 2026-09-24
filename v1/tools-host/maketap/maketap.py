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

CRC16_CCITT_FALSE_POLY = 0x1021
CRC16_CCITT_FALSE_INIT = 0xFFFF
CRC16_CCITT_FALSE_XOROUT = 0x0000
CRC16_CCITT_FALSE_REFIN = False
CRC16_CCITT_FALSE_REFOUT = False

M48O_HEADER_SIZE = 32
M48O_CHUNK_SIZE = 512
M48O_DATA_FLAG = 0xFF

M48O_TXT = 1
M48O_BIN = 2
M48O_FNT = 9
M48O_UDG = 7
M48O_CFG = 10
M48O_SYS = 11
DIR_BIN = 1
DIR_ETC = 3
DIR_USERHOME = 5
DIR_TMP = 6
DIR_SYSTEM = 7

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


@dataclass(frozen=True)
class M48OObject:
    name: str
    object_type: int
    target_directory: int
    payload: bytes


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise TapeError(message)


def _u16(value: int) -> bytes:
    _require(0 <= value <= 0xFFFF, "u16 out of range")
    return struct.pack("<H", value)


def crc16_ccitt_false(data: bytes) -> int:
    crc = CRC16_CCITT_FALSE_INIT
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            crc = (
                ((crc << 1) ^ CRC16_CCITT_FALSE_POLY) & 0xFFFF
                if crc & 0x8000
                else (crc << 1) & 0xFFFF
            )
    return crc ^ CRC16_CCITT_FALSE_XOROUT


def _integer_number(value: int) -> bytes:
    _require(0 <= value <= 0xFFFF, "loader integer out of range")
    digits = str(value).encode("ascii")
    return digits + b"\x0e\x00\x00" + _u16(value) + b"\x00"


def _basic_line(line_number: int, body: bytes) -> bytes:
    _require(0 <= line_number <= 9999, "BASIC line number out of range")
    content = body + b"\x0d"
    return struct.pack(">H", line_number) + _u16(len(content)) + content


def loader_with_extra_code_loads(
    source: str,
    line_numbers: tuple[int, ...] = (),
) -> str:
    expected = (
        "10 BORDER 0: PAPER 0: INK 7: CLS\n"
        "20 CLEAR 24575\n"
        "30 LOAD \"\" SCREEN$\n"
        "40 LOAD \"\" CODE\n"
        "50 RANDOMIZE USR 57347\n"
    )
    _require(source == expected, "canonical five-line loader text mismatch")
    _require(
        line_numbers == tuple(sorted(set(line_numbers))),
        "extra CODE-load line numbers must be unique and ascending",
    )
    _require(
        all(41 <= line_number <= 49 for line_number in line_numbers),
        "extra CODE-load line number must be between 41 and 49",
    )
    lines = source.splitlines()
    extras = tuple(f'{line_number} LOAD \"\" CODE' for line_number in line_numbers)
    return "\n".join((*lines[:-1], *extras, lines[-1])) + "\n"


def tokenized_loader(
    source: str,
    *,
    extra_code_load_lines: tuple[int, ...] = (),
) -> bytes:
    loader_with_extra_code_loads(source, extra_code_load_lines)

    n0 = _integer_number(0)
    n7 = _integer_number(7)
    n24575 = _integer_number(24575)
    n57347 = _integer_number(BOOT_GATEWAY_DECIMAL)
    lines = [
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
    ]
    lines.extend(
        _basic_line(
            line_number,
            bytes((TOK_LOAD, 0x20, 0x22, 0x22, 0x20, TOK_CODE)),
        )
        for line_number in extra_code_load_lines
    )
    lines.append(
        _basic_line(50, bytes((TOK_RANDOMIZE, 0x20, TOK_USR, 0x20)) + n57347)
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


def minimal_shell_mex1() -> bytes:
    # LD A,SYS_EXIT ; LD HL,0 ; JP 0xE000. No relocations are required because
    # the syscall gateway is fixed by the public ABI.
    image = bytes((0x3E, 0x01, 0x21, 0x00, 0x00, 0xC3, 0x00, 0xE0))
    header = bytearray(24)
    header[0:4] = b"MEX1"
    header[4] = 1
    header[5] = 0
    header[6:8] = _u16(24)
    header[8:10] = _u16(len(image))
    header[10:12] = _u16(0)
    header[12:14] = _u16(0)
    header[14:16] = _u16(128)
    header[16:18] = _u16(0)
    header[18:20] = _u16(24 + len(image))
    header[20:22] = _u16(crc16_ccitt_false(image))
    header[22:24] = b"\0\0"
    header[22:24] = _u16(crc16_ccitt_false(bytes(header)))
    return bytes(header) + image


def m48o_header(obj: M48OObject) -> bytes:
    encoded = obj.name.encode("ascii")
    _require(1 <= len(encoded) <= 10, "M48O base name must be 1..10 bytes")
    _require(all(chr(b).isalnum() or chr(b) in "_.-" for b in encoded), "invalid M48O base-name byte")
    _require(1 <= obj.object_type <= M48O_SYS, "invalid persistent object type")
    if obj.target_directory == DIR_BIN:
        _require(obj.object_type == M48O_BIN, "BIN target accepts only BIN")
    elif obj.target_directory == DIR_ETC:
        _require(obj.object_type in (M48O_TXT, M48O_CFG), "ETC target accepts only TXT/CFG")
    elif obj.target_directory in (DIR_USERHOME, DIR_TMP):
        _require(1 <= obj.object_type <= M48O_CFG, "ordinary target accepts types 1..10")
    elif obj.target_directory == DIR_SYSTEM:
        _require(obj.object_type in (M48O_FNT, M48O_SYS), "SYSTEM target accepts only FNT/SYS")
    else:
        raise TapeError("invalid M48O target directory")
    _require(len(obj.payload) <= 32768, "M48O payload too large")

    header = bytearray(M48O_HEADER_SIZE)
    header[0:4] = b"M48O"
    header[4] = 1
    header[5] = obj.object_type
    header[6] = 0  # RAW
    header[7] = obj.target_directory
    header[8:10] = _u16(len(obj.payload))
    header[10:12] = _u16(len(obj.payload))
    header[12:14] = _u16(0)
    header[14:16] = _u16(crc16_ccitt_false(obj.payload))
    header[16:26] = encoded.ljust(10, b"\0")
    header[26:28] = b"\0\0"
    header[28:32] = b"\0\0\0\0"
    header[26:28] = _u16(crc16_ccitt_false(bytes(header)))
    return bytes(header)


def m48o_blocks(obj: M48OObject) -> bytes:
    out = bytearray(tap_block(M48O_DATA_FLAG, m48o_header(obj)))
    for offset in range(0, len(obj.payload), M48O_CHUNK_SIZE):
        out.extend(
            tap_block(
                M48O_DATA_FLAG,
                obj.payload[offset:offset + M48O_CHUNK_SIZE],
            )
        )
    return bytes(out)


def bootstrap_resources(*, font: bytes, issue: bytes, crontab: bytes, bincat: bytes) -> tuple[M48OObject, ...]:
    resources = (
        M48OObject("sh", M48O_BIN, DIR_BIN, minimal_shell_mex1()),
        M48OObject("font4x8", M48O_FNT, DIR_SYSTEM, font),
        M48OObject("issue", M48O_TXT, DIR_ETC, issue),
        M48OObject("crontab", M48O_CFG, DIR_ETC, crontab),
        M48OObject("bincat", M48O_SYS, DIR_SYSTEM, bincat),
    )
    _require(tuple(item.name for item in resources) == ("sh", "font4x8", "issue", "crontab", "bincat"), "bootstrap resource order")
    return resources


def validate_bootstrap_contract(
    *, loader_source: str, screen: bytes, kernel: bytes,
    kernel_start: int = KERNEL_START, boot_gateway: int = BOOT_GATEWAY,
    names: tuple[str, str, str] = ("zx48ux", "zx48uxscr", "kernel"),
    extra_code_load_lines: tuple[int, ...] = (),
) -> tuple[LogicalFile, LogicalFile, LogicalFile]:
    _require(len(screen) == SCREEN_SIZE, "loading screen must be exactly 6912 bytes")
    _require(len(kernel) == KERNEL_SIZE, "kernel image must be exactly 8192 bytes")
    _require(kernel_start == KERNEL_START, "kernel CODE start must be E000")
    _require(boot_gateway == BOOT_GATEWAY, "loader boot gateway must be E003")
    _require(names == ("zx48ux", "zx48uxscr", "kernel"), "bootstrap native-file name/order mismatch")
    program = tokenized_loader(
        loader_source,
        extra_code_load_lines=extra_code_load_lines,
    )
    return (
        LogicalFile("zx48ux", PROGRAM_TYPE, program, 10, len(program)),
        LogicalFile("zx48uxscr", CODE_TYPE, screen, SCREEN_START, 0x8000),
        LogicalFile("kernel", CODE_TYPE, kernel, KERNEL_START, 0x8000),
    )


def build_bootstrap_prefix(
    *, loader_source: str, screen: bytes, kernel: bytes,
    kernel_start: int = KERNEL_START, boot_gateway: int = BOOT_GATEWAY,
    names: tuple[str, str, str] = ("zx48ux", "zx48uxscr", "kernel"),
    extra_code_load_lines: tuple[int, ...] = (),
) -> bytes:
    files = validate_bootstrap_contract(
        loader_source=loader_source, screen=screen, kernel=kernel,
        kernel_start=kernel_start, boot_gateway=boot_gateway, names=names,
        extra_code_load_lines=extra_code_load_lines,
    )
    return b"".join(logical_file_blocks(item) for item in files)


def build_boot_tape(*, loader_source: str, screen: bytes, kernel: bytes, font: bytes, issue: bytes, crontab: bytes, bincat: bytes) -> bytes:
    out = bytearray(build_bootstrap_prefix(loader_source=loader_source, screen=screen, kernel=kernel))
    for obj in bootstrap_resources(font=font, issue=issue, crontab=crontab, bincat=bincat):
        out.extend(m48o_blocks(obj))
    return bytes(out)


def append_logical_files(prefix: bytes, files: Iterable[LogicalFile]) -> bytes:
    out = bytearray(prefix)
    for file in files:
        out.extend(logical_file_blocks(file))
    return bytes(out)


PHASE5_FIXTURE_LABEL = "zxux-phase5-fixture-non-final"
PHASE5_FIXTURE_STUB_NAMES = (
    "cron", "crontab", "vi", "as", "cc", "ld", "ls", "cat", "echo", "cp",
    "mv", "rm", "pack", "unpack", "hexdump", "grep", "wc", "head", "tail",
    "cmp", "true", "false", "sleep", "which", "env", "stty", "date", "man",
    "whoami", "uname", "uptime", "cal", "fortune", "banner", "rev", "yes",
    "udg", "gfxdemo", "demo",
)

def phase5_fixture_stub_objects() -> tuple[M48OObject, ...]:
    payload = minimal_shell_mex1()
    return tuple(M48OObject(name, M48O_BIN, DIR_BIN, payload) for name in PHASE5_FIXTURE_STUB_NAMES)

def build_phase5_fixture_tape(
    *, loader_source: str, screen: bytes, kernel: bytes, font: bytes,
    issue: bytes, crontab: bytes, bincat: bytes,
    fixture_label: str = PHASE5_FIXTURE_LABEL,
) -> bytes:
    _require(fixture_label == PHASE5_FIXTURE_LABEL, "Phase-5 fixture label must be explicitly non-final")
    out = bytearray(build_boot_tape(
        loader_source=loader_source, screen=screen, kernel=kernel,
        font=font, issue=issue, crontab=crontab, bincat=bincat,
    ))
    for obj in phase5_fixture_stub_objects():
        out.extend(m48o_blocks(obj))
    return bytes(out)
