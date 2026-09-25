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

"""Independent structural inspector for the REV17 fast-loader TZX."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import struct

PROG_BASE = 0x5CCB
HOOK_ADDR = 0x5E4F
RENDER_ROW_ADDR = 0x5E62
FINAL_HOLD_ADDR = 0x5EB4
STARTUP_BEEP_ADDR = 0x5F2A
KERNEL_BASE = 0xE000
KERNEL_SIZE = 8192
HANDOFF = 0xE003
FINAL_LOADER_AFTER = FINAL_HOLD_ADDR
DUMMY_SHA256 = "0e59ef9290ffc4391b0ae999177cd9d7d9eafb6fcd86a45b13f9a4bd0b08c9ce"
CHUNK_LENGTHS = (342,) * 8 + (341,) * 16


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def loader_check(data: bytes) -> int:
    # Independent implementation of the loader's received-byte check:
    # E starts at 1; after each byte A := byte + E (mod 256), RLCA A, E := A.
    e = 1
    for value in data:
        s = (value + e) & 0xFF
        e = ((s & 0x7F) << 1) | (s >> 7)
    return e


def parse_tzx(data: bytes):
    if data[:10] != b"ZXTape!\x1a\x01\x14":
        raise ValueError("bad TZX header")
    p = 10
    blocks = []
    while p < len(data):
        start = p
        bid = data[p]
        p += 1
        if bid == 0x30:
            n = data[p]
            p += 1
            blocks.append((bid, start, p + n, data[p:p+n]))
            p += n
        elif bid == 0x10:
            pause, n = struct.unpack_from("<HH", data, p)
            p += 4
            blocks.append((bid, start, p + n, (pause, data[p:p+n])))
            p += n
        elif bid == 0x20:
            pause = struct.unpack_from("<H", data, p)[0]
            p += 2
            blocks.append((bid, start, p, pause))
        elif bid == 0x19:
            n = struct.unpack_from("<I", data, p)[0]
            p += 4
            blocks.append((bid, start, p + n, data[p:p+n]))
            p += n
        else:
            raise ValueError(f"unexpected TZX block {bid:#x} at {start:#x}")
        if p > len(data):
            raise ValueError("truncated TZX")
    if p != len(data):
        raise ValueError("TZX parse did not end at EOF")
    return blocks


def generalized_data(body: bytes) -> bytes:
    o = 2
    total_pilot = struct.unpack_from("<I", body, o)[0]
    o += 4
    npp, asp = body[o], body[o+1]
    o += 2
    total_data_bits = struct.unpack_from("<I", body, o)[0]
    o += 4
    npd, asd = body[o], body[o+1]
    o += 2
    o += (asp or 256) * (1 + 2 * npp)
    o += total_pilot * 3
    o += (asd or 256) * (1 + 2 * npd)
    size = (total_data_bits + 7) // 8
    if o + size > len(body):
        raise ValueError("generalized-data stream overrun")
    return body[o:o+size]


def inspect(data: bytes) -> dict:
    blocks = parse_tzx(data)
    std = [b for b in blocks if b[0] == 0x10]
    if len(std) != 2:
        raise ValueError(f"expected exactly two standard-speed BASIC blocks, got {len(std)}")
    header = std[0][3][1]
    if len(header) != 19 or header[0] != 0 or header[2:12] != b"ZX-UX Unix":
        raise ValueError("unexpected BASIC bootstrap header")
    data = std[1][3][1]
    if len(data) < 3 or data[0] != 0xFF:
        raise ValueError("unexpected BASIC bootstrap data block")
    basic = data[1:-1]
    if not (0 <= HOOK_ADDR - PROG_BASE < len(basic)):
        raise ValueError("loader hook lies outside BASIC program")

    def basic_bytes(address: int, size: int) -> bytes:
        offset = address - PROG_BASE
        if offset < 0 or offset + size > len(basic):
            raise ValueError(f"BASIC address range {address:#06x}+{size} is out of bounds")
        return basic[offset:offset + size]

    expected_hold = bytes(
        [0xCD, RENDER_ROW_ADDR & 0xFF, RENDER_ROW_ADDR >> 8,
         0xCD, STARTUP_BEEP_ADDR & 0xFF, STARTUP_BEEP_ADDR >> 8,
         0xC3, HANDOFF & 0xFF, HANDOFF >> 8]
    ) + bytes(5)
    if basic_bytes(FINAL_HOLD_ADDR, 14) != expected_hold:
        raise ValueError("final_hold is not final-row render, startup beep, then E003")
    if basic_bytes(STARTUP_BEEP_ADDR, 15) != bytes.fromhex(
        "dde511e00021ca01cdb503f3dde1c9"
    ):
        raise ValueError("startup BEEPER routine drifted")
    if basic_bytes(0x5EF7, 2) != bytes([24, 0]):
        raise ValueError("loader display callback state is not 24 rows from row zero")

    # A SCREEN$ CODE header would require an additional standard-speed pair.
    gen = [generalized_data(b[3]) for b in blocks if b[0] == 0x19]
    if len(gen) != 48:
        raise ValueError(f"expected 48 generalized-data blocks, got {len(gen)}")
    headers, chunks = gen[0::2], gen[1::2]
    if tuple(map(len, chunks)) != CHUNK_LENGTHS:
        raise ValueError("payload chunk lengths do not match REV17 contract")

    offset = 0
    checks = []
    destinations = []
    for i, (h, chunk) in enumerate(zip(headers, chunks)):
        if len(h) != 17:
            raise ValueError(f"header {i} must be 17 bytes")
        length, load_addr, dest_addr, zero, check, after, tail1, tail2, tail3, tail4, tail5 = struct.unpack(
            "<HHHBBHHBHBB", h
        )
        expected = loader_check(chunk)
        if check != expected:
            raise ValueError(f"header {i} loader-check mismatch: {check:#04x} != {expected:#04x}")
        if zero != 0 or length != len(chunk):
            raise ValueError(f"header {i} length/zero mismatch")
        logical_dest = dest_addr or load_addr
        expected_dest = KERNEL_BASE + offset
        if logical_dest != expected_dest:
            raise ValueError(
                f"header {i} logical destination {logical_dest:#06x} != {expected_dest:#06x}"
            )
        if i < 23 and after != 0x0100:
            raise ValueError(f"header {i} continuation word drifted")
        if i == 23 and (load_addr, dest_addr, after) != (
            0x9000, 0xFEAB, FINAL_LOADER_AFTER
        ):
            raise ValueError("final temporary-copy/destination/finalizer tuple drifted")
        checks.append(check)
        destinations.append(logical_dest)
        offset += len(chunk)

    kernel = b"".join(chunks)
    if len(kernel) != KERNEL_SIZE or offset != KERNEL_SIZE:
        raise ValueError("reconstructed kernel is not exactly 8192 bytes")
    kernel_hash = sha256(kernel)
    if kernel_hash == DUMMY_SHA256:
        raise ValueError("known seed dummy payload present")

    return {
        "tzx_sha256": sha256(data),
        "tzx_size": len(data),
        "kernel_sha256": kernel_hash,
        "kernel_size": len(kernel),
        "kernel": kernel,
        "checks": checks,
        "destinations": destinations,
        "handoff": HANDOFF,
        "handoff_path_verified": True,
        "final_loader_after": FINAL_LOADER_AFTER,
        "standard_speed_blocks": len(std),
        "generalized_blocks": len(gen),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("tzx", type=Path)
    ap.add_argument("--kernel", type=Path, help="required expected kernel for exact bytewise comparison")
    ap.add_argument("--extract", type=Path)
    args = ap.parse_args()
    result = inspect(args.tzx.read_bytes())
    kernel = result.pop("kernel")
    if args.kernel:
        expected = args.kernel.read_bytes()
        if len(expected) != KERNEL_SIZE:
            raise SystemExit("expected kernel is not exactly 8192 bytes")
        if kernel != expected:
            for i, (a, b) in enumerate(zip(kernel, expected)):
                if a != b:
                    raise SystemExit(f"embedded kernel mismatch at offset {i}: {a:#04x} != {b:#04x}")
            raise SystemExit("embedded kernel mismatch")
    if args.extract:
        args.extract.parent.mkdir(parents=True, exist_ok=True)
        args.extract.write_bytes(kernel)
    for key in ("tzx_sha256", "tzx_size", "kernel_sha256", "kernel_size", "standard_speed_blocks", "generalized_blocks"):
        print(f"{key}={result[key]}")
    print(f"final_loader_after=0x{result['final_loader_after']:04X}")
    print("handoff=0xE003")
    print("ZX-UX RELEASE TZX INSPECTION PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
