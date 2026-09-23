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
import re
from typing import Callable, Any

from driver_core import DriverError

MAGIC = b"OBJ1"
HEADER_SIZE = 24
MAX_SIZE = 32768
SYMBOL_SIZE = 20
RELOC_SIZE = 6


class Obj1HeaderError(DriverError):
    pass


def require(ok: bool, message: str) -> None:
    if not ok:
        raise Obj1HeaderError(message)


def crc16_ccitt_false(data: bytes) -> int:
    crc = 0xFFFF
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc


def u16(data: bytes, off: int) -> int:
    return data[off] | (data[off + 1] << 8)


def build_obj(text: bytes=b"", bss: int=0, symbols: bytes=b"", relocs: bytes=b"") -> bytes:
    require(len(symbols) % SYMBOL_SIZE == 0, "symbol fixture alignment")
    require(len(relocs) % RELOC_SIZE == 0, "reloc fixture alignment")
    sc = len(symbols) // SYMBOL_SIZE
    rc = len(relocs) // RELOC_SIZE
    so = HEADER_SIZE + len(text)
    ro = so + len(symbols)
    h = bytearray(HEADER_SIZE)
    h[0:4] = MAGIC
    h[4] = 1
    h[5] = 0
    h[6:8] = HEADER_SIZE.to_bytes(2, "little")
    h[8:10] = len(text).to_bytes(2, "little")
    h[10:12] = bss.to_bytes(2, "little")
    h[12:14] = sc.to_bytes(2, "little")
    h[14:16] = rc.to_bytes(2, "little")
    h[16:18] = so.to_bytes(2, "little")
    h[18:20] = ro.to_bytes(2, "little")
    body = text + symbols + relocs
    h[20:22] = crc16_ccitt_false(body).to_bytes(2, "little")
    h[22:24] = b"\x00\x00"
    h[22:24] = crc16_ccitt_false(bytes(h)).to_bytes(2, "little")
    return bytes(h) + body


def parse_obj(data: bytes) -> dict[str, int]:
    require(len(data) >= HEADER_SIZE, "E_FORMAT short header")
    h = data[:HEADER_SIZE]
    require(h[0:4] == MAGIC, "E_FORMAT magic")
    require(h[4] == 1, "E_FORMAT version")
    require(h[5] == 0, "E_FORMAT flags")
    require(u16(h, 6) == HEADER_SIZE, "E_FORMAT header_size")
    text = u16(h, 8)
    bss = u16(h, 10)
    sc = u16(h, 12)
    rc = u16(h, 14)
    so = u16(h, 16)
    ro = u16(h, 18)
    require(text + bss <= MAX_SIZE, "E_FORMAT text+bss")
    expected_so = HEADER_SIZE + text
    expected_ro = expected_so + sc * SYMBOL_SIZE
    expected_total = expected_ro + rc * RELOC_SIZE
    require(so == expected_so, "E_FORMAT symbol offset")
    require(ro == expected_ro, "E_FORMAT relocation offset")
    require(expected_total <= MAX_SIZE, "E_FORMAT stored length")
    require(len(data) == expected_total, "E_FORMAT exact total length")
    require(rc == 0 or text >= 2, "E_FORMAT relocation requires text word")
    require(crc16_ccitt_false(data[HEADER_SIZE:]) == u16(h, 20), "E_FORMAT body CRC")
    hc = bytearray(h)
    hc[22:24] = b"\x00\x00"
    require(crc16_ccitt_false(bytes(hc)) == u16(h, 22), "E_FORMAT header CRC")
    return {"text_size": text, "bss_size": bss, "symbol_count": sc, "relocation_count": rc, "symbol_offset": so, "relocation_offset": ro, "total": expected_total}


def constants(path: Path) -> dict[str, int]:
    out: dict[str, int] = {}
    rx = re.compile(r"^([A-Z0-9_]+)\s+EQU\s+([^;\s]+)")
    for line in path.read_text(encoding="utf-8").splitlines():
        m = rx.match(line)
        if not m:
            continue
        token = m.group(2)
        try:
            out[m.group(1)] = int(token[1:], 16) if token.startswith("$") else int(token, 10)
        except ValueError:
            pass
    return out


def source_assertions(root: Path) -> list[dict[str, object]]:
    c = constants(root / "v1/include/obj1.inc")
    expected = {
        "OBJ1_MAGIC_0":0x4F, "OBJ1_MAGIC_1":0x42, "OBJ1_MAGIC_2":0x4A, "OBJ1_MAGIC_3":0x31,
        "OBJ1_HEADER_SIZE":24, "OBJ1_VERSION":1, "OBJ1_FLAGS":0,
        "OBJ1_HDR_MAGIC":0, "OBJ1_HDR_VERSION":4, "OBJ1_HDR_FLAGS":5, "OBJ1_HDR_SIZE":6,
        "OBJ1_HDR_TEXT_SIZE":8, "OBJ1_HDR_BSS_SIZE":10, "OBJ1_HDR_SYMBOL_COUNT":12,
        "OBJ1_HDR_RELOC_COUNT":14, "OBJ1_HDR_SYMBOL_OFFSET":16, "OBJ1_HDR_RELOC_OFFSET":18,
        "OBJ1_HDR_BODY_CRC":20, "OBJ1_HDR_HEADER_CRC":22, "OBJ1_SYMBOL_SIZE":20,
        "OBJ1_RELOC_SIZE":6, "OBJ1_MAX_TEXT_BSS":32768, "OBJ1_MAX_STORED":32768,
    }
    d = (root / "v1/docs/obj1.md").read_text(encoding="utf-8")
    return [
        {"name":"obj1-header-constants-exact","passed":all(c.get(k)==v for k,v in expected.items())},
        {"name":"obj1-doc-exact-header-size","passed":"header is exactly 24 bytes" in d and "must be exactly 24" in d},
        {"name":"obj1-doc-body-crc-complete","passed":"every stored byte after the header" in d and "every relocation record" in d},
        {"name":"obj1-doc-widened-arithmetic-and-no-trailing","passed":"widened arithmetic" in d and "No trailing bytes" in d},
    ]


def negative_assertions() -> list[dict[str, object]]:
    good = build_obj(text=b"AB")
    cases: list[tuple[str, bytes]] = []

    def mutate(name: str, off: int, value: int):
        x=bytearray(good)
        x[off]=value
        x[22:24]=b"\x00\x00"
        x[22:24]=crc16_ccitt_false(bytes(x[:24])).to_bytes(2,"little")
        cases.append((name,bytes(x)))

    mutate("bad-magic",0,0)
    mutate("bad-version",4,2)
    mutate("bad-flags",5,1)
    x=bytearray(good); x[6:8]=(23).to_bytes(2,"little"); x[22:24]=b"\x00\x00"; x[22:24]=crc16_ccitt_false(bytes(x[:24])).to_bytes(2,"little"); cases.append(("bad-header-size",bytes(x)))
    cases.append(("trailing-byte",good+b"X"))
    x=bytearray(good); x[20]^=1; cases.append(("body-crc",bytes(x)))
    x=bytearray(good); x[22]^=1; cases.append(("header-crc",bytes(x)))
    cases.append(("reloc-with-text-lt-two",build_obj(text=b"", relocs=b"\x00"*6)))
    wrap_symbols = bytearray(HEADER_SIZE)
    wrap_symbols[0:4] = MAGIC
    wrap_symbols[4] = 1
    wrap_symbols[6:8] = HEADER_SIZE.to_bytes(2, "little")
    wrap_symbols[12:14] = (0x4000).to_bytes(2, "little")
    wrap_symbols[16:18] = HEADER_SIZE.to_bytes(2, "little")
    wrap_symbols[18:20] = HEADER_SIZE.to_bytes(2, "little")
    wrap_symbols[20:22] = crc16_ccitt_false(b"").to_bytes(2, "little")
    wrap_symbols[22:24] = b"\x00\x00"
    wrap_symbols[22:24] = crc16_ccitt_false(bytes(wrap_symbols)).to_bytes(2, "little")
    cases.append(("symbol-count-16-bit-wrap-rejected", bytes(wrap_symbols)))
    wrap_relocs = bytearray(HEADER_SIZE + 2)
    wrap_relocs[0:4] = MAGIC
    wrap_relocs[4] = 1
    wrap_relocs[6:8] = HEADER_SIZE.to_bytes(2, "little")
    wrap_relocs[8:10] = (2).to_bytes(2, "little")
    wrap_relocs[14:16] = (0x4000).to_bytes(2, "little")
    wrap_relocs[16:18] = (HEADER_SIZE + 2).to_bytes(2, "little")
    wrap_relocs[18:20] = (HEADER_SIZE + 2).to_bytes(2, "little")
    wrap_relocs[20:22] = crc16_ccitt_false(bytes(wrap_relocs[HEADER_SIZE:])).to_bytes(2, "little")
    wrap_relocs[22:24] = b"\x00\x00"
    wrap_relocs[22:24] = crc16_ccitt_false(bytes(wrap_relocs[:HEADER_SIZE])).to_bytes(2, "little")
    cases.append(("relocation-count-16-bit-wrap-rejected", bytes(wrap_relocs)))
    assertions=[]
    for name,image in cases:
        rejected=False
        try:
            parse_obj(image)
        except Obj1HeaderError:
            rejected=True
        assertions.append({"name":name,"passed":rejected})
    return assertions


def dispatch(root: Path, action: str, step: str, *, sha256_file: Callable[[Path], str], run_command: Callable[..., Any], require_project_tool: Callable[[Path, str | Path], Path]):
    if step != "P10.01":
        raise DriverError(f"Phase-10 OBJ1 header step is not registered: {step}")
    assertions = source_assertions(root)
    golden = build_obj(text=b"\x34\x12", bss=7)
    parsed = parse_obj(golden)
    assertions.extend([
        {"name":"golden-magic-and-version","passed":golden[:6]==b"OBJ1\x01\x00"},
        {"name":"golden-offsets","passed":parsed["symbol_offset"]==26 and parsed["relocation_offset"]==26 and parsed["total"]==26},
        {"name":"golden-text-bss","passed":parsed["text_size"]==2 and parsed["bss_size"]==7},
        {"name":"golden-header-crc-zero-field","passed":crc16_ccitt_false(golden[:22]+b"\x00\x00")==u16(golden,22)},
    ])
    if action == "test":
        assertions.extend(negative_assertions())
    failed=[a["name"] for a in assertions if a.get("passed") is not True]
    require(not failed, f"P10.01 contract failures: {failed}")
    hashes={
        "v1/include/obj1.inc":sha256_file(root/"v1/include/obj1.inc"),
        "v1/docs/obj1.md":sha256_file(root/"v1/docs/obj1.md"),
        "v1/tools-host/test-driver/phase10_obj1_header.py":sha256_file(root/"v1/tools-host/test-driver/phase10_obj1_header.py"),
        "v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
        "v1/dist/certification/phase-9.json":sha256_file(root/"v1/dist/certification/phase-9.json"),
    }
    return [], hashes, assertions
