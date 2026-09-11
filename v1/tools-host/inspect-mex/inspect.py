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
import struct
import sys

HEADER_SIZE = 24
MAX_STORED = 32768
MIN_STACK = 64
MAX_STACK = 4096


class MexError(ValueError):
    pass


def crc16_ccitt_false(data: bytes) -> int:
    crc = 0xFFFF
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc


def u16(data: bytes, offset: int) -> int:
    return data[offset] | (data[offset + 1] << 8)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise MexError(message)


def inspect_bytes(data: bytes, *, base: int | None = None) -> dict[str, object]:
    require(len(data) >= HEADER_SIZE, "truncated MEX1 header")
    h = data[:HEADER_SIZE]
    require(h[:4] == b"MEX1", "bad MEX1 magic")
    require(h[4] == 1 and h[5] == 0, "unsupported MEX1 version/flags")
    require(u16(h, 6) == HEADER_SIZE, "bad MEX1 header size")
    image_size = u16(h, 8)
    bss_size = u16(h, 10)
    entry = u16(h, 12)
    stack = u16(h, 14)
    reloc_count = u16(h, 16)
    reloc_offset = u16(h, 18)
    body_crc = u16(h, 20)
    header_crc = u16(h, 22)

    require(image_size >= 1, "MEX1 image must be nonempty")
    require(image_size + bss_size <= MAX_STORED, "MEX1 image+BSS exceeds arena limit")
    require(entry < image_size, "MEX1 entry outside image")
    require(MIN_STACK <= stack <= MAX_STACK, "MEX1 stack outside 64..4096")
    require(reloc_offset == HEADER_SIZE + image_size, "MEX1 relocation offset mismatch")
    require(not reloc_count or image_size >= 2, "relocations require image_size>=2")
    total = reloc_offset + reloc_count * 2
    require(total <= MAX_STORED, "MEX1 stored length exceeds 32768")
    require(total == len(data), "MEX1 stored length/trailing-byte mismatch")

    hh = bytearray(h)
    hh[22:24] = b"\x00\x00"
    require(crc16_ccitt_false(bytes(hh)) == header_crc, "MEX1 header CRC mismatch")
    require(crc16_ccitt_false(data[HEADER_SIZE:]) == body_crc, "MEX1 body CRC mismatch")

    image = data[HEADER_SIZE:reloc_offset]
    relocs: list[int] = []
    previous = -2
    for index in range(reloc_count):
        offset = u16(data, reloc_offset + index * 2)
        require(offset <= image_size - 2, "MEX1 relocation outside image")
        require(offset >= previous + 2, "MEX1 relocations unsorted/overlapping")
        word = image[offset] | (image[offset + 1] << 8)
        require(word <= image_size + bss_size, "MEX1 relocation addend outside image+BSS")
        if base is not None:
            require(0 <= base <= 0xFFFF, "relocation base outside u16")
            require(word + base <= 0xFFFF, "MEX1 relocated word wraps u16")
            require(base + image_size + bss_size <= 0x10000, "MEX1 allocation wraps address space")
        relocs.append(offset)
        previous = offset

    return {
        "magic": "MEX1",
        "version": 1,
        "image_size": image_size,
        "bss_size": bss_size,
        "entry_offset": entry,
        "minimum_stack_size": stack,
        "relocation_count": reloc_count,
        "relocation_table_offset": reloc_offset,
        "stored_length": total,
        "body_crc": body_crc,
        "header_crc": header_crc,
        "relocations": relocs,
    }


def _make_fixture() -> bytes:
    image = bytearray(b"\x01\x00\xc9")
    relocs = struct.pack("<H", 0)
    h = bytearray(HEADER_SIZE)
    h[:4] = b"MEX1"
    h[4] = 1
    struct.pack_into("<H", h, 6, HEADER_SIZE)
    struct.pack_into("<H", h, 8, len(image))
    struct.pack_into("<H", h, 10, 0)
    struct.pack_into("<H", h, 12, 2)
    struct.pack_into("<H", h, 14, 64)
    struct.pack_into("<H", h, 16, 1)
    struct.pack_into("<H", h, 18, HEADER_SIZE + len(image))
    body = bytes(image) + relocs
    struct.pack_into("<H", h, 20, crc16_ccitt_false(body))
    struct.pack_into("<H", h, 22, 0)
    struct.pack_into("<H", h, 22, crc16_ccitt_false(bytes(h)))
    return bytes(h) + body


def self_test() -> None:
    good = _make_fixture()
    inspect_bytes(good, base=0x6000)
    for offset in (0, 4, 20, 22, len(good) - 1):
        bad = bytearray(good)
        bad[offset] ^= 1
        try:
            inspect_bytes(bytes(bad), base=0x6000)
        except MexError:
            pass
        else:
            raise MexError(f"one-bit mutation at {offset} unexpectedly accepted")
    try:
        inspect_bytes(good + b"\x00")
    except MexError:
        pass
    else:
        raise MexError("trailing byte unexpectedly accepted")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Inspect a ZX-UX MEX1 executable")
    parser.add_argument("path", nargs="?", type=Path)
    parser.add_argument("--base", type=lambda value: int(value, 0))
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.self_test:
            self_test()
            print("MEX1 inspector self-test PASS")
            return 0
        if args.path is None:
            parser.error("path is required unless --self-test is used")
        print(json.dumps(inspect_bytes(args.path.read_bytes(), base=args.base), sort_keys=True))
        return 0
    except (OSError, MexError) as exc:
        print(f"inspect-mex: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
