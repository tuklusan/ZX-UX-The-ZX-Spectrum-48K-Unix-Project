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
import sys
from typing import Any, Callable

from driver_core import DriverError
from fuse_harness import FAIL_PC, PASS_PC, run_sna
import phase1
import phase3_open_descriptions

MODULE_BASE = 0xC000
SRC_BASE = 0x8000
DST_BASE = 0xA000
HISTORY_BASE = 0xA800
STACK_TOP = 0xBFC0
ZXPACK_HOST = "v1/tools-host/zxpack/zxpack.py"


class P416Error(DriverError):
    pass


def require(ok: bool, msg: str) -> None:
    if not ok:
        raise P416Error(msg)


def _source_contract(root: Path) -> list[dict[str, object]]:
    text = (root / "v1/src/kernel/zxpack.asm").read_text(encoding="utf-8")
    require("MACRO EMIT_P416_ZXP1_DECODER" in text, "P4.16 decoder macro missing")
    m = text.split("MACRO EMIT_P416_ZXP1_DECODER", 1)[1].split("ENDM", 1)[0]
    constants = (
        "P416_SINK_FINAL_MEMORY  EQU 0",
        "P416_SINK_CALLER_STREAM EQU 1",
        "P416_SINK_DISCARD       EQU 2",
        "P416_SINK_TAPE_PIPE     EQU 3",
    )
    return [
        {"name": "exact-four-sinks", "passed": all(x in text for x in constants)},
        {"name": "single-token-parser", "passed": m.count("zx48_p416_loop:") == 1},
        {"name": "literal-rle-backref-grammar", "passed": all(x in m for x in ("cp $40", "cp $80", "and $3f", "and $7f", "add a,3"))},
        {"name": "exact-physical-completion", "passed": "zx48_p416_finish:" in m and "p416_phys_left" in m and "jp nz,zx48_p416_format" in m},
        {"name": "exact-logical-completion", "passed": "p416_logical_total" in m and "p416_logical_pos" in m},
        {"name": "prewrite-logical-overrun-guard", "passed": "call zx48_p416_check_advance" in m and m.count("call zx48_p416_check_advance") == 3},
        {"name": "widened-input-span-guard", "passed": "add hl,bc\n    jp c,zx48_p416_format" in m},
        {"name": "widened-output-span-guard", "passed": "add hl,bc\n    jp c,zx48_p416_inval" in m},
        {"name": "widened-logical-advance-guard", "passed": "add hl,de\n    jp c,zx48_p416_format" in m},
        {"name": "distance-256-explicitly-valid", "passed": "ld bc,256" in m and "cp 1" in m and "zx48_p416_history_distance_ok:" in m},
        {"name": "byte-at-a-time-overlap", "passed": "zx48_p416_back_loop:" in m and "call zx48_p416_history_read" in m and "call zx48_p416_emit" in m},
        {"name": "optional-logical-crc", "passed": "zx48_p416_crc_byte:" in m and "xor $10" in m and "xor $21" in m},
        {"name": "no-terminator", "passed": "terminator" not in m.lower()},
    ]


def _load_host(root: Path):
    path = root / ZXPACK_HOST
    spec = importlib.util.spec_from_file_location("zxux_p416_host", path)
    require(spec is not None and spec.loader is not None, "P4.16 cannot load host ZXP1 oracle")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _assemble(root: Path, run_command: Callable[..., Any], require_project_tool: Callable[[Path, str | Path], Path]):
    asm = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    fixture = build / "p416-zxpack-decoder.asm"
    fixture.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/kernel/zxpack.asm"
    ORG $C000
    EMIT_P416_ZXP1_DECODER
    SAVEBIN "p416-zxpack-decoder.bin",$C000,$-$C000
""", encoding="utf-8", newline="\n")
    result = run_command(
        [asm, "--nologo", "--lst=p416-zxpack-decoder.lst", "--sym=p416-zxpack-decoder.sym", "p416-zxpack-decoder.asm"],
        cwd=build,
        timeout_seconds=30.0,
    )
    require(not result.timed_out and result.exit_code == 0, f"P4.16 fixture assembly failed: {result.stderr or result.stdout}")
    binary = build / "p416-zxpack-decoder.bin"
    listing = build / "p416-zxpack-decoder.lst"
    require(binary.is_file() and 0 < binary.stat().st_size <= 2048, "P4.16 decoder fixture missing/oversize")
    return result, binary, listing


def _ld_bc(value: int) -> bytes:
    return b"\x01" + phase1._word(value)


def _ld_ix(value: int) -> bytes:
    return b"\xDD\x21" + phase1._word(value)


def _check_byte(address: int, value: int) -> bytes:
    return b"\x3A" + phase1._word(address) + bytes((0xFE, value)) + phase1._jp_nz(FAIL_PC)


def _check_word(address: int, value: int) -> bytes:
    return b"\x2A" + phase1._word(address) + phase1._ld_de(value) + b"\xB7\xED\x52" + phase1._jp_nz(FAIL_PC)


def _check_bytes(address: int, data: bytes) -> bytes:
    out = bytearray()
    for i, value in enumerate(data):
        out += _check_byte(address + i, value)
    return bytes(out)


def _crc16(data: bytes) -> int:
    crc = 0xFFFF
    for value in data:
        crc ^= value << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc


def _ring_image(data: bytes) -> bytes:
    ring = bytearray(256)
    for i, value in enumerate(data):
        ring[i & 0xFF] = value
    return bytes(ring)


def _run_success(root: Path, s: dict[str, int], module: bytes, label: str, encoded: bytes, logical: bytes, sink: int, *, crc: bool = True, src: int = SRC_BASE) -> None:
    code = bytearray(b"\xF3")
    code += phase1._ld_sp(STACK_TOP)
    code += bytes((0x3E, sink))
    code += phase1._ld_hl(src) + _ld_bc(len(encoded)) + phase1._ld_de(len(logical))
    code += _ld_ix(HISTORY_BASE) + phase1._ld_iy(DST_BASE)
    code += phase1._call(s["zx48_p416_decode"]) + phase1._jp_c(FAIL_PC)
    code += _check_word(s["p416_logical_pos"], len(logical))
    code += _check_word(s["p416_phys_left"], 0)
    if crc:
        code += _check_word(s["p416_crc"], _crc16(logical))
    if sink in (s["P416_SINK_FINAL_MEMORY"], s["P416_SINK_CALLER_STREAM"]):
        code += _check_bytes(DST_BASE, logical)
    else:
        code += _check_bytes(DST_BASE, b"\xA5" * min(16, max(1, len(logical))))
    if sink != s["P416_SINK_FINAL_MEMORY"]:
        ring = _ring_image(logical)
        touched = min(len(logical), 256)
        for i in range(touched):
            code += _check_byte(HISTORY_BASE + i, ring[i])
    code += phase1._jp(PASS_PC)

    def patch(ram: bytearray) -> None:
        ram[MODULE_BASE-0x4000:MODULE_BASE-0x4000+len(module)] = module
        if encoded:
            off = src - 0x4000
            ram[off:off+len(encoded)] = encoded
        ram[DST_BASE-0x4000:DST_BASE-0x4000+max(512, len(logical)+16)] = b"\xA5" * max(512, len(logical)+16)
        ram[HISTORY_BASE-0x4000:HISTORY_BASE-0x4000+256] = bytes(256)
        ram[s["p416_crc_enable"]-0x4000] = 1 if crc else 0

    try:
        run_sna(root, bytes(code), patch=patch)
    except DriverError as exc:
        raise P416Error(f"P4.16 success case failed: {label}/sink={sink}: {exc}") from exc


def _run_failure(root: Path, s: dict[str, int], module: bytes, label: str, encoded: bytes, logical_len: int, error: int, *, sink: int = 0, src: int = SRC_BASE, dst: int = DST_BASE, unchanged: int = 0) -> None:
    code = bytearray(b"\xF3")
    code += phase1._ld_sp(STACK_TOP)
    code += bytes((0x3E, sink))
    code += phase1._ld_hl(src) + _ld_bc(len(encoded)) + phase1._ld_de(logical_len)
    code += _ld_ix(HISTORY_BASE) + phase1._ld_iy(dst)
    code += phase1._call(s["zx48_p416_decode"])
    code += b"\xD2" + phase1._word(FAIL_PC)
    code += bytes((0xFE, error)) + phase1._jp_nz(FAIL_PC)
    if unchanged:
        code += _check_bytes(dst, b"\xA5" * unchanged)
    code += phase1._jp(PASS_PC)

    def patch(ram: bytearray) -> None:
        ram[MODULE_BASE-0x4000:MODULE_BASE-0x4000+len(module)] = module
        if encoded and src >= 0x4000 and src + len(encoded) <= 0x10000:
            ram[src-0x4000:src-0x4000+len(encoded)] = encoded
        if 0x4000 <= dst < 0x10000:
            count = min(512, 0x10000-dst)
            ram[dst-0x4000:dst-0x4000+count] = b"\xA5" * count
        ram[HISTORY_BASE-0x4000:HISTORY_BASE-0x4000+256] = bytes(256)
        ram[s["p416_crc_enable"]-0x4000] = 0

    try:
        run_sna(root, bytes(code), patch=patch)
    except DriverError as exc:
        raise P416Error(f"P4.16 failure case failed: {label}: {exc}") from exc


def _runtime(root: Path, s: dict[str, int], module: bytes) -> None:
    z = _load_host(root)
    boundary = [
        ("literal-1", b"\x00Z", b"Z"),
        ("literal-64", b"\x3f" + bytes(range(64)), bytes(range(64))),
        ("rle-3", b"\x40Q", b"Q" * 3),
        ("rle-66", b"\x7fR", b"R" * 66),
        ("backref-overlap-distance-1", b"\x00A\xff\x00", b"A" * 131),
        ("backref-overlap-pattern", b"\x02abc\x86\x02", b"abcabcabcabc"),
    ]
    seed = bytes(range(64)) * 4
    boundary.append(("backref-distance-256", (b"\x3f" + bytes(range(64))) * 4 + b"\x80\xff", seed + seed[:3]))
    for label, encoded, logical in boundary:
        for sink in range(4):
            _run_success(root, s, module, label, encoded, logical, sink)

    for index, logical in enumerate((b"123456789", b"abcdef" * 50, bytes(range(256)) * 2)):
        encoded = z.encode(logical)
        require(z.decode(encoded, len(logical)) == logical, f"P4.16 host oracle round-trip mismatch {index}")
        for sink in range(4):
            _run_success(root, s, module, f"host-oracle-{index}", encoded, logical, sink)

    _run_success(root, s, module, "physical-end-ffff", b"\x00X", b"X", 0, src=0xFFFE)

    ef = s["E_FORMAT"]
    ei = s["E_INVAL"]
    malformed = (
        ("truncated-literal", b"\x00", 1),
        ("truncated-rle", b"\x40", 3),
        ("truncated-backref-param", b"\x80", 3),
        ("distance-before-start", b"\x80\x00", 3),
        ("distance-beyond-output", b"\x00A\x80\x01", 4),
        ("logical-overrun", b"\x40A", 2),
        ("logical-underrun", b"\x00A", 2),
        ("trailing-physical", b"\x00A\x00B", 1),
    )
    for label, encoded, logical_len in malformed:
        _run_failure(root, s, module, label, encoded, logical_len, ef, unchanged=2 if label == "logical-overrun" else 0)
    _run_failure(root, s, module, "invalid-sink", b"", 0, ei, sink=4)
    _run_failure(root, s, module, "physical-span-wrap", b"X", 1, ef, src=0xFFFF)
    _run_failure(root, s, module, "output-span-wrap", b"\x01XY", 2, ei, dst=0xFFFF)

    code = bytearray(b"\xF3")
    code += phase1._ld_sp(STACK_TOP)
    code += phase1._call(s["zx48_p416_check_advance"])
    code += b"\xD2" + phase1._word(FAIL_PC)
    code += bytes((0xFE, ef)) + phase1._jp_nz(FAIL_PC) + phase1._jp(PASS_PC)
    def patch_advance(ram: bytearray) -> None:
        ram[MODULE_BASE-0x4000:MODULE_BASE-0x4000+len(module)] = module
        ram[s["p416_logical_pos"]-0x4000:s["p416_logical_pos"]-0x4000+2] = phase1._word(0xFFFE)
        ram[s["p416_logical_total"]-0x4000:s["p416_logical_total"]-0x4000+2] = phase1._word(0xFFFF)
        ram[s["p416_count"]-0x4000] = 3
    run_sna(root, bytes(code), patch=patch_advance)


def dispatch(root: Path, action: str, step: str, *, sha256_file, run_command, require_project_tool):
    if step != "P4.16":
        raise DriverError(f"Phase-4 ZXP1 decoder step is not registered: {step}")
    assertions = _source_contract(root)
    failed = [x["name"] for x in assertions if x.get("passed") is not True]
    require(not failed, f"static P4.16 contract failures: {failed}")
    kernel_result, kernel, _ = phase1._assemble_kernel(root, run_command, require_project_tool)
    fixture_result, binary, listing = _assemble(root, run_command, require_project_tool)
    names = (
        "zx48_p416_decode", "zx48_p416_check_advance", "p416_crc_enable", "p416_crc",
        "p416_phys_left", "p416_logical_total", "p416_logical_pos", "p416_count",
        "P416_SINK_FINAL_MEMORY", "P416_SINK_CALLER_STREAM", "P416_SINK_DISCARD", "P416_SINK_TAPE_PIPE",
        "E_FORMAT", "E_INVAL",
    )
    symbols = phase3_open_descriptions._symbols(listing.with_suffix(".sym"), names)
    if action == "test":
        _runtime(root, symbols, binary.read_bytes())
        assertions += [
            {"name": "all-four-sinks-identical-runtime", "passed": True},
            {"name": "literal-rle-backref-boundaries-runtime", "passed": True},
            {"name": "distance-1-and-256-overlap-runtime", "passed": True},
            {"name": "host-optimized-oracle-runtime", "passed": True},
            {"name": "crc-ccitt-false-runtime", "passed": True},
            {"name": "exact-physical-logical-completion-runtime", "passed": True},
            {"name": "malformed-and-truncated-rejected-runtime", "passed": True},
            {"name": "widened-wrap-guards-runtime", "passed": True},
        ]
    hashes = {
        "v1/build/kernel.bin": sha256_file(kernel),
        "v1/build/p416-zxpack-decoder.bin": sha256_file(binary),
        "v1/src/kernel/zxpack.asm": sha256_file(root / "v1/src/kernel/zxpack.asm"),
        "v1/tools-host/test-driver/phase4_zxpack_decoder.py": sha256_file(root / "v1/tools-host/test-driver/phase4_zxpack_decoder.py"),
        "v1/tools-host/test-driver/run.py": sha256_file(root / "v1/tools-host/test-driver/run.py"),
        "v1/tools-host/zxpack/zxpack.py": sha256_file(root / ZXPACK_HOST),
        "v1/dist/certification/P4.15.test.json": sha256_file(root / "v1/dist/certification/P4.15.test.json"),
    }
    return [kernel_result, fixture_result], hashes, assertions
