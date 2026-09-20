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
STATE_BASE = 0xA000
STACK_TOP = 0xBFC0
SENTINEL = 0xA500
ZXPACK_HOST = "v1/tools-host/zxpack/zxpack.py"


class P418Error(DriverError):
    pass


def require(ok: bool, msg: str) -> None:
    if not ok:
        raise P418Error(msg)


def _load_host(root: Path):
    path = root / ZXPACK_HOST
    spec = importlib.util.spec_from_file_location("zxux_p418_host", path)
    require(spec is not None and spec.loader is not None, "P4.18 cannot load host ZXP1 oracle")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _source_contract(root: Path) -> list[dict[str, object]]:
    zx = (root / "v1/src/kernel/zxpack.asm").read_text(encoding="utf-8")
    require("MACRO EMIT_P418_PACKED_SEEK_ROUTINES" in zx, "P4.18 seek macro missing")
    m = zx.split("MACRO EMIT_P418_PACKED_SEEK_ROUTINES", 1)[1].split("ENDM", 1)[0]
    return [
        {"name": "seek-bounds-inclusive-eof", "passed": "p418_logical_length" in m and "zx48_p418_inval:" in m},
        {"name": "backward-reset", "passed": "jr c,zx48_p418_forward" in m and "call zx48_p418_reset" in m},
        {"name": "forward-continues-current-state", "passed": "zx48_p418_forward:" in m and "zx48_p418_step" in m},
        {"name": "discard-only-no-materialization", "passed": "FINAL_MEMORY" not in m and "zx48_alloc" not in m},
        {"name": "persistent-physical-logical-cursors", "passed": all(x in m for x in ("P418_C_PHYSICAL_POS", "P418_C_LOGICAL_POS")) and all(x in zx for x in ("P417_CTRL_PHYSICAL_POS_O", "P417_CTRL_LOGICAL_POS_O"))},
        {"name": "persistent-pending-command", "passed": all(x in m for x in ("P418_C_PENDING_KIND", "P418_C_PENDING_COUNT", "P418_C_PARAMETER")) and all(x in zx for x in ("P417_CTRL_PENDING_KIND_O", "P417_CTRL_PENDING_COUNT_O", "P417_CTRL_PARAMETER_O"))},
        {"name": "overlap-history-ring", "passed": all(x in m for x in ("P418_C_HISTORY_INDEX", "P418_C_HISTORY_COUNT")) and all(x in zx for x in ("P417_CTRL_HISTORY_INDEX_O", "P417_CTRL_HISTORY_COUNT_O"))},
        {"name": "exact-eof-physical-completion", "passed": "P418_C_PHYSICAL_LENGTH" in m and "P418_CTRL_PHYSICAL_LENGTH_O" in zx and "jp nz,zx48_p418_format" in m},
        {"name": "source-span-prevalidated", "passed": "dec bc\n    add hl,bc" in m and "jp c,zx48_p418_format" in m},
        {"name": "no-duplicate-state-allocation", "passed": "ALLOC_COLD_PREFERRED" not in m},
    ]


def _assemble(root: Path, run_command: Callable[..., Any], require_project_tool: Callable[[Path, str | Path], Path]):
    asm = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    fixture = build / "p418-packed-seek.asm"
    fixture.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/kernel/zxpack.asm"
    ORG $C000
    EMIT_P418_PACKED_SEEK_ROUTINES
    SAVEBIN "p418-packed-seek.bin",$C000,$-$C000
""", encoding="utf-8", newline="\n")
    result = run_command([asm, "--nologo", "--lst=p418-packed-seek.lst", "--sym=p418-packed-seek.sym", "p418-packed-seek.asm"], cwd=build, timeout_seconds=30.0)
    require(not result.timed_out and result.exit_code == 0, f"P4.18 fixture assembly failed: {result.stderr or result.stdout}")
    binary = build / "p418-packed-seek.bin"
    listing = build / "p418-packed-seek.lst"
    require(binary.is_file() and 0 < binary.stat().st_size < 4096, "P4.18 fixture binary missing/oversize")
    return result, binary, listing


def _ld_bc(value: int) -> bytes:
    return b"\x01" + phase1._word(value)


def _ld_ix(value: int) -> bytes:
    return b"\xDD\x21" + phase1._word(value)


def _check_byte(address: int, value: int) -> bytes:
    return b"\x3A" + phase1._word(address) + bytes((0xFE, value)) + phase1._jp_nz(FAIL_PC)


def _check_word(address: int, value: int) -> bytes:
    return b"\x2A" + phase1._word(address) + phase1._ld_de(value) + b"\xB7\xED\x52" + phase1._jp_nz(FAIL_PC)


def _bind(s: dict[str, int], physical_len: int, src: int = SRC_BASE) -> bytes:
    return _ld_ix(STATE_BASE) + phase1._ld_hl(src) + _ld_bc(physical_len) + phase1._call(s["zx48_p418_state_bind"])


def _seek(s: dict[str, int], target: int, logical_len: int) -> bytes:
    return _ld_ix(STATE_BASE) + phase1._ld_hl(target) + phase1._ld_de(logical_len) + phase1._call(s["zx48_p418_seek"])


def _run_sequence(root: Path, s: dict[str, int], module: bytes, encoded: bytes, logical: bytes) -> None:
    sequence = (0, 1, 17, 64, 129, 7, 200, 33, len(logical) - 1, len(logical))
    code = bytearray(b"\xF3")
    code += phase1._ld_sp(STACK_TOP)
    code += _bind(s, len(encoded)) + phase1._jp_c(FAIL_PC)
    code += bytes((0x3E, s["OBJ_PACKED"])) + b"\x32" + phase1._word(SENTINEL)
    for target in sequence:
        code += _seek(s, target, len(logical)) + phase1._jp_c(FAIL_PC)
        code += _check_word(STATE_BASE + s["P417_CTRL_LOGICAL_POS_O"], target)
        code += _check_byte(SENTINEL, s["OBJ_PACKED"])
        if target < len(logical):
            code += phase1._call(s["zx48_p418_step"]) + phase1._jp_c(FAIL_PC)
            code += _check_byte(s["p418_byte"], logical[target])
            code += _check_word(STATE_BASE + s["P417_CTRL_LOGICAL_POS_O"], target + 1)
    code += phase1._jp(PASS_PC)

    def patch(ram: bytearray) -> None:
        ram[MODULE_BASE-0x4000:MODULE_BASE-0x4000+len(module)] = module
        ram[SRC_BASE-0x4000:SRC_BASE-0x4000+len(encoded)] = encoded
        ram[STATE_BASE-0x4000:STATE_BASE-0x4000+272] = b"\xA5" * 272
        ram[SENTINEL-0x4000] = 0

    run_sna(root, bytes(code), patch=patch)


def _run_pending(root: Path, s: dict[str, int], module: bytes) -> None:
    encoded = b"\x7fA"
    logical_len = 66
    code = bytearray(b"\xF3")
    code += phase1._ld_sp(STACK_TOP)
    code += _bind(s, len(encoded)) + phase1._jp_c(FAIL_PC)
    code += _seek(s, 5, logical_len) + phase1._jp_c(FAIL_PC)
    code += _check_word(STATE_BASE + s["P417_CTRL_PHYSICAL_POS_O"], 2)
    code += _check_byte(STATE_BASE + s["P417_CTRL_PENDING_KIND_O"], s["P418_PENDING_RLE"])
    code += _check_byte(STATE_BASE + s["P417_CTRL_PENDING_COUNT_O"], 61)
    code += _seek(s, 10, logical_len) + phase1._jp_c(FAIL_PC)
    code += _check_word(STATE_BASE + s["P417_CTRL_PHYSICAL_POS_O"], 2)
    code += _check_byte(STATE_BASE + s["P417_CTRL_PENDING_COUNT_O"], 56)
    code += _seek(s, 3, logical_len) + phase1._jp_c(FAIL_PC)
    code += _check_word(STATE_BASE + s["P417_CTRL_PHYSICAL_POS_O"], 2)
    code += _check_byte(STATE_BASE + s["P417_CTRL_PENDING_COUNT_O"], 63)
    code += _seek(s, logical_len, logical_len) + phase1._jp_c(FAIL_PC)
    code += _check_word(STATE_BASE + s["P417_CTRL_PHYSICAL_POS_O"], 2)
    code += _check_byte(STATE_BASE + s["P417_CTRL_PENDING_COUNT_O"], 0)
    code += phase1._jp(PASS_PC)

    def patch(ram: bytearray) -> None:
        ram[MODULE_BASE-0x4000:MODULE_BASE-0x4000+len(module)] = module
        ram[SRC_BASE-0x4000:SRC_BASE-0x4000+len(encoded)] = encoded
        ram[STATE_BASE-0x4000:STATE_BASE-0x4000+272] = bytes(272)

    run_sna(root, bytes(code), patch=patch)


def _run_failure(root: Path, s: dict[str, int], module: bytes, encoded: bytes, logical_len: int, target: int, expected: int, *, src: int = SRC_BASE) -> None:
    code = bytearray(b"\xF3")
    code += phase1._ld_sp(STACK_TOP)
    code += _bind(s, len(encoded), src)
    if expected == s["E_FORMAT"] and src == 0xFFFF and len(encoded) > 1:
        code += b"\xD2" + phase1._word(FAIL_PC)
        code += bytes((0xFE, expected)) + phase1._jp_nz(FAIL_PC) + phase1._jp(PASS_PC)
    else:
        code += phase1._jp_c(FAIL_PC)
        code += _seek(s, target, logical_len)
        code += b"\xD2" + phase1._word(FAIL_PC)
        code += bytes((0xFE, expected)) + phase1._jp_nz(FAIL_PC) + phase1._jp(PASS_PC)

    def patch(ram: bytearray) -> None:
        ram[MODULE_BASE-0x4000:MODULE_BASE-0x4000+len(module)] = module
        if encoded and src >= 0x4000 and src + len(encoded) <= 0x10000:
            ram[src-0x4000:src-0x4000+len(encoded)] = encoded
        ram[STATE_BASE-0x4000:STATE_BASE-0x4000+272] = bytes(272)

    run_sna(root, bytes(code), patch=patch)


def _runtime(root: Path, s: dict[str, int], module: bytes) -> None:
    z = _load_host(root)
    logical = bytes(range(64)) * 4 + b"A" * 100 + b"abcdef" * 30
    encoded = z.encode(logical)
    require(z.decode(encoded, len(logical)) == logical, "P4.18 host oracle round-trip mismatch")
    cases = [
        ("seek-sequence", lambda: _run_sequence(root, s, module, encoded, logical)),
        ("pending-command", lambda: _run_pending(root, s, module)),
        ("seek-beyond-eof", lambda: _run_failure(root, s, module, b"\x00A", 1, 2, s["E_INVAL"])),
        ("trailing-physical-data", lambda: _run_failure(root, s, module, b"\x00A\x00B", 1, 1, s["E_FORMAT"])),
        ("truncated-rle", lambda: _run_failure(root, s, module, b"\x40", 3, 3, s["E_FORMAT"])),
        ("truncated-backref", lambda: _run_failure(root, s, module, b"\x80\x00", 3, 3, s["E_FORMAT"])),
        ("source-span-wrap", lambda: _run_failure(root, s, module, b"XY", 1, 0, s["E_FORMAT"], src=0xFFFF)),
    ]
    for name, case in cases:
        try:
            case()
        except DriverError as exc:
            raise P418Error(f"P4.18 runtime case {name} failed: {exc}") from exc


def dispatch(root: Path, action: str, step: str, *, sha256_file, run_command, require_project_tool):
    if step != "P4.18":
        raise DriverError(f"Phase-4 packed seek step is not registered: {step}")
    assertions = _source_contract(root)
    failed = [x["name"] for x in assertions if x.get("passed") is not True]
    require(not failed, f"static P4.18 contract failures: {failed}")
    kernel_result, kernel, _ = phase1._assemble_kernel(root, run_command, require_project_tool)
    fixture_result, binary, listing = _assemble(root, run_command, require_project_tool)
    names = (
        "zx48_p418_state_bind", "zx48_p418_seek", "zx48_p418_step", "p418_byte",
        "P417_CTRL_PHYSICAL_POS_O", "P417_CTRL_LOGICAL_POS_O", "P417_CTRL_PENDING_KIND_O",
        "P417_CTRL_PENDING_COUNT_O", "P418_PENDING_RLE", "OBJ_PACKED", "E_FORMAT", "E_INVAL",
    )
    symbols = phase3_open_descriptions._symbols(listing.with_suffix(".sym"), names)
    if action == "test":
        _runtime(root, symbols, binary.read_bytes())
        assertions += [
            {"name": "random-forward-backward-seek-read-raw-oracle-runtime", "passed": True},
            {"name": "forward-mid-command-continues-runtime", "passed": True},
            {"name": "backward-mid-command-restarts-runtime", "passed": True},
            {"name": "seek-to-eof-exact-runtime", "passed": True},
            {"name": "seek-beyond-eof-einval-runtime", "passed": True},
            {"name": "malformed-packed-stream-eformat-runtime", "passed": True},
            {"name": "packed-representation-unchanged-runtime", "passed": True},
        ]
    hashes = {
        "v1/build/kernel.bin": sha256_file(kernel),
        "v1/build/p418-packed-seek.bin": sha256_file(binary),
        "v1/src/kernel/zxpack.asm": sha256_file(root / "v1/src/kernel/zxpack.asm"),
        "v1/tools-host/test-driver/phase4_packed_seek.py": sha256_file(root / "v1/tools-host/test-driver/phase4_packed_seek.py"),
        "v1/tools-host/test-driver/run.py": sha256_file(root / "v1/tools-host/test-driver/run.py"),
        "v1/tools-host/zxpack/zxpack.py": sha256_file(root / ZXPACK_HOST),
        "v1/dist/certification/P4.17.test.json": sha256_file(root / "v1/dist/certification/P4.17.test.json"),
    }
    return [kernel_result, fixture_result], hashes, assertions
