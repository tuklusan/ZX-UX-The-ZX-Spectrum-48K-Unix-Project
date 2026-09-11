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

import argparse
import json
from pathlib import Path
import re
import struct
import sys

HEADER_SIZE = 24
SYMBOL_SIZE = 20
RELOC_SIZE = 6
MAX_STORED = 32768
ASM_NAME = re.compile(rb"^[A-Za-z_.$][A-Za-z0-9_.$]{0,14}$")


class ObjError(ValueError):
    pass


def crc16_ccitt_false(data: bytes) -> int:
    crc = 0xFFFF
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc


def u16(data: bytes, offset: int) -> int:
    return data[offset] | data[offset + 1] << 8


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ObjError(message)


def decode_name(raw: bytes) -> str:
    first_zero = raw.find(0)
    if first_zero < 0:
        visible = raw
    else:
        visible = raw[:first_zero]
        require(not any(raw[first_zero:]), "OBJ1 symbol name has nonzero tail after NUL")
    require(1 <= len(visible) <= 15, "OBJ1 symbol name length outside 1..15")
    require(ASM_NAME.fullmatch(visible) is not None, "OBJ1 symbol name has illegal byte")
    return visible.decode("ascii")


def inspect_bytes(data: bytes) -> dict[str, object]:
    require(len(data) >= HEADER_SIZE, "truncated OBJ1 header")
    h = data[:HEADER_SIZE]
    require(h[:4] == b"OBJ1", "bad OBJ1 magic")
    require(h[4] == 1 and h[5] == 0, "unsupported OBJ1 version/flags")
    require(u16(h, 6) == HEADER_SIZE, "bad OBJ1 header size")
    text_size = u16(h, 8)
    bss_size = u16(h, 10)
    symbol_count = u16(h, 12)
    reloc_count = u16(h, 14)
    symbol_offset = u16(h, 16)
    reloc_offset = u16(h, 18)
    body_crc = u16(h, 20)
    header_crc = u16(h, 22)

    require(text_size + bss_size <= MAX_STORED, "OBJ1 text+BSS exceeds 32768")
    require(symbol_offset == HEADER_SIZE + text_size, "OBJ1 symbol-table offset mismatch")
    expected_reloc = symbol_offset + symbol_count * SYMBOL_SIZE
    require(expected_reloc <= MAX_STORED, "OBJ1 symbol table arithmetic overflow")
    require(reloc_offset == expected_reloc, "OBJ1 relocation-table offset mismatch")
    total = reloc_offset + reloc_count * RELOC_SIZE
    require(total <= MAX_STORED, "OBJ1 stored length exceeds 32768")
    require(total == len(data), "OBJ1 stored length/trailing-byte mismatch")
    require(not reloc_count or text_size >= 2, "OBJ1 relocations require text_size>=2")

    hh = bytearray(h)
    hh[22:24] = b"\x00\x00"
    require(crc16_ccitt_false(bytes(hh)) == header_crc, "OBJ1 header CRC mismatch")
    require(crc16_ccitt_false(data[HEADER_SIZE:]) == body_crc, "OBJ1 body CRC mismatch")

    symbols: list[dict[str, object]] = []
    names: set[str] = set()
    for index in range(symbol_count):
        pos = symbol_offset + index * SYMBOL_SIZE
        record = data[pos:pos + SYMBOL_SIZE]
        name = decode_name(record[:16])
        require(name not in names, "duplicate OBJ1 symbol")
        names.add(name)
        value = u16(record, 16)
        section = record[18]
        flags = record[19]
        require(section <= 3, "OBJ1 symbol section outside 0..3")
        require(flags & ~1 == 0, "OBJ1 symbol has unknown flag bits")
        if section == 0:
            require(value == 0 and flags == 1, "OBJ1 UNDEF must be GLOBAL with value zero")
        elif section == 1:
            require(value <= text_size, "OBJ1 TEXT symbol outside text")
        elif section == 2:
            require(value <= bss_size, "OBJ1 BSS symbol outside BSS")
        symbols.append({"name": name, "value": value, "section": section, "global": bool(flags)})

    relocs: list[dict[str, int]] = []
    previous = -2
    text = data[HEADER_SIZE:symbol_offset]
    for index in range(reloc_count):
        pos = reloc_offset + index * RELOC_SIZE
        record = data[pos:pos + RELOC_SIZE]
        offset = u16(record, 0)
        symbol = u16(record, 2)
        require(record[4] == 1 and record[5] == 0, "OBJ1 relocation type/reserved invalid")
        require(offset <= text_size - 2, "OBJ1 relocation outside text")
        require(offset >= previous + 2, "OBJ1 relocations unsorted/overlapping")
        require(symbol < symbol_count, "OBJ1 relocation symbol index outside table")
        addend_u = text[offset] | text[offset + 1] << 8
        addend = addend_u - 0x10000 if addend_u & 0x8000 else addend_u
        relocs.append({"offset": offset, "symbol": symbol, "addend": addend})
        previous = offset

    return {
        "magic": "OBJ1",
        "version": 1,
        "text_size": text_size,
        "bss_size": bss_size,
        "symbol_count": symbol_count,
        "relocation_count": reloc_count,
        "symbol_table_offset": symbol_offset,
        "relocation_table_offset": reloc_offset,
        "stored_length": total,
        "body_crc": body_crc,
        "header_crc": header_crc,
        "symbols": symbols,
        "relocations": relocs,
    }


def _make_fixture() -> bytes:
    text = b"\x00\x00\xc9"
    sym = bytearray(SYMBOL_SIZE)
    sym[:4] = b"main"
    struct.pack_into("<H", sym, 16, 0)
    sym[18] = 1
    sym[19] = 1
    rel = struct.pack("<HHBB", 0, 0, 1, 0)
    h = bytearray(HEADER_SIZE)
    h[:4] = b"OBJ1"
    h[4] = 1
    struct.pack_into("<H", h, 6, HEADER_SIZE)
    struct.pack_into("<H", h, 8, len(text))
    struct.pack_into("<H", h, 10, 0)
    struct.pack_into("<H", h, 12, 1)
    struct.pack_into("<H", h, 14, 1)
    struct.pack_into("<H", h, 16, HEADER_SIZE + len(text))
    struct.pack_into("<H", h, 18, HEADER_SIZE + len(text) + SYMBOL_SIZE)
    body = text + bytes(sym) + rel
    struct.pack_into("<H", h, 20, crc16_ccitt_false(body))
    struct.pack_into("<H", h, 22, 0)
    struct.pack_into("<H", h, 22, crc16_ccitt_false(bytes(h)))
    return bytes(h) + body


def self_test() -> None:
    good = _make_fixture()
    inspect_bytes(good)
    for offset in (0, 4, 20, 22, len(good) - 1):
        bad = bytearray(good)
        bad[offset] ^= 1
        try:
            inspect_bytes(bytes(bad))
        except ObjError:
            pass
        else:
            raise ObjError(f"one-bit mutation at {offset} unexpectedly accepted")
    try:
        inspect_bytes(good + b"\x00")
    except ObjError:
        pass
    else:
        raise ObjError("trailing byte unexpectedly accepted")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Inspect a ZX-UX OBJ1 object")
    parser.add_argument("path", nargs="?", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.self_test:
            self_test()
            print("OBJ1 inspector self-test PASS")
            return 0
        if args.path is None:
            parser.error("path is required unless --self-test is used")
        print(json.dumps(inspect_bytes(args.path.read_bytes()), sort_keys=True))
        return 0
    except (OSError, ObjError) as exc:
        print(f"inspect-obj: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
