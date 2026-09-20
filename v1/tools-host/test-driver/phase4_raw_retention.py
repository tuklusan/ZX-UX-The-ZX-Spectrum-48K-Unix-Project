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
from typing import Any, Callable

from driver_core import DriverError
from fuse_harness import FAIL_PC, PASS_PC, run_sna
import phase1
import phase3_open_descriptions

MODULE_BASE = 0xC000
SRC_BASE = 0xA000
DST_BASE = 0xB000
STACK_TOP = 0xBFC0


class P421Error(DriverError):
    pass


def require(ok: bool, msg: str) -> None:
    if not ok:
        raise P421Error(msg)


def _word(value: int) -> bytes:
    return bytes((value & 0xFF, (value >> 8) & 0xFF))


def _ld_bc(value: int) -> bytes:
    return b"\x01" + _word(value)


def _check_byte(address: int, value: int) -> bytes:
    return b"\x3A" + _word(address) + bytes((0xFE, value & 0xFF)) + phase1._jp_nz(FAIL_PC)


def _check_hl(value: int) -> bytes:
    return phase1._ld_de(value) + b"\xB7\xED\x52" + phase1._jp_nz(FAIL_PC)


def _source_contract(root: Path) -> list[dict[str, object]]:
    zx = (root / "v1/src/kernel/zxpack.asm").read_text(encoding="utf-8")
    require("MACRO EMIT_P421_PACK_DECISION_ROUTINES" in zx, "P4.21 pack decision macro missing")
    m = zx.split("MACRO EMIT_P421_PACK_DECISION_ROUTINES", 1)[1].split("ENDM", 1)[0]
    return [
        {"name": "zero-length-short-circuit-raw", "passed": "ld a,b\n    or c\n    jr nz,zx48_p421_nonempty" in m and "ld hl,0" in m},
        {"name": "nonempty-delegates-exact-target-encoder", "passed": "jp zx48_p420_two_pass" in m},
        {"name": "strict-smaller-guard-frozen-in-encoder", "passed": "jp nc,zx48_p420_no_saving" in zx},
        {"name": "raw-sentinel-zero-return", "passed": "zx48_p420_no_saving:" in zx and "ld hl,0" in zx.split("zx48_p420_no_saving:",1)[1][:80]},
    ]


def _assemble(root: Path, run_command: Callable[..., Any], require_project_tool: Callable[[Path, str | Path], Path]):
    asm = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    fixture = build / "p421-pack-decision.asm"
    fixture.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
PANIC_SCHEDULER EQU $03
    ORG $C000
    INCLUDE "../src/kernel/memory.asm"
    INCLUDE "../src/kernel/zxpack.asm"
    EMIT_MEMORY_ROUTINES
    EMIT_P420_TARGET_ENCODER_ROUTINES
    EMIT_P421_PACK_DECISION_ROUTINES
zx48_process_count:
    xor a
    ret
zx48_panic:
    scf
    ret
    SAVEBIN "p421-pack-decision.bin",$C000,$-$C000
""", encoding="utf-8", newline="\n")
    result = run_command([asm, "--nologo", "--lst=p421-pack-decision.lst", "--sym=p421-pack-decision.sym", "p421-pack-decision.asm"], cwd=build, timeout_seconds=30.0)
    require(not result.timed_out and result.exit_code == 0, f"P4.21 fixture assembly failed: {result.stderr or result.stdout}")
    binary = build / "p421-pack-decision.bin"
    listing = build / "p421-pack-decision.lst"
    require(binary.is_file() and 0 < binary.stat().st_size < 16384, "P4.21 fixture binary missing/oversize")
    return result, binary, listing


def _runtime(root: Path, s: dict[str, int], module: bytes) -> None:
    free = s["memory_free_extents"]
    live = s["memory_live_allocations"]
    arena_start = s["ARENA_START"]
    arena_size = s["ARENA_SIZE"]

    def patch(data: bytes):
        def apply(ram: bytearray) -> None:
            ram[MODULE_BASE-0x4000:MODULE_BASE-0x4000+len(module)] = module
            ram[SRC_BASE-0x4000:SRC_BASE-0x4000+len(data)] = data
            ram[DST_BASE-0x4000:DST_BASE-0x4000+64] = b"\xA5" * 64
            ram[free-0x4000:free-0x4000+64] = bytes(64)
            ram[free-0x4000:free-0x4000+4] = _word(arena_start) + _word(arena_size)
            ram[live-0x4000:live-0x4000+2] = _word(0)
        return apply

    def call(data: bytes) -> bytes:
        return b"\xAF" + phase1._ld_hl(SRC_BASE) + _ld_bc(len(data)) + phase1._ld_de(DST_BASE) + phase1._call(s["zx48_p421_encode_if_smaller"])

    def execute(label: str, data: bytes, code: bytes) -> None:
        body = b"\xF3" + phase1._ld_sp(STACK_TOP) + code + phase1._jp(PASS_PC)
        try:
            run_sna(root, body, patch=patch(data))
        except DriverError as exc:
            raise P421Error(f"P4.21 runtime case failed: {label}: {exc}") from exc

    code = call(b"") + phase1._jp_c(FAIL_PC)
    code += _check_hl(0)
    code += _check_byte(DST_BASE, 0xA5)
    code += _check_byte(s["p420_workspace_allocs"], 0)
    code += _check_hl(0)
    execute("zero-length-remains-raw-without-workspace", b"", code)

    incompressible = bytes(range(64))
    code = call(incompressible) + phase1._jp_c(FAIL_PC)
    code += _check_hl(0)
    code += _check_byte(DST_BASE, 0xA5)
    code += _check_byte(s["p420_workspace_allocs"], 1)
    execute("incompressible-remains-raw", incompressible, code)

    equal = b"\x00\x00\x00\x01"
    code = call(equal) + phase1._jp_c(FAIL_PC)
    code += _check_hl(0)
    code += _check_byte(DST_BASE, 0xA5)
    code += _check_byte(s["p420_workspace_allocs"], 1)
    execute("equal-size-packed-result-rejected", equal, code)

    compressible = b"Q" * 66
    code = call(compressible) + phase1._jp_c(FAIL_PC)
    code += _check_hl(2)
    code += _check_byte(DST_BASE, 0x7F)
    code += _check_byte(DST_BASE + 1, ord("Q"))
    code += _check_byte(s["p420_workspace_allocs"], 2)
    execute("strictly-smaller-eligible", compressible, code)


def dispatch(root: Path, action: str, step: str, *, sha256_file, run_command, require_project_tool):
    if step != "P4.21":
        raise DriverError(f"Phase-4 RAW retention step is not registered: {step}")
    assertions = _source_contract(root)
    failed = [x["name"] for x in assertions if x.get("passed") is not True]
    require(not failed, f"static P4.21 contract failures: {failed}")

    kernel_result, kernel, _ = phase1._assemble_kernel(root, run_command, require_project_tool)
    fixture_result, binary, listing = _assemble(root, run_command, require_project_tool)
    names = (
        "zx48_p421_encode_if_smaller", "p420_workspace_allocs",
        "memory_free_extents", "memory_live_allocations", "ARENA_START", "ARENA_SIZE",
    )
    symbols = phase3_open_descriptions._symbols(listing.with_suffix(".sym"), names)

    if action == "test":
        _runtime(root, symbols, binary.read_bytes())
        assertions += [
            {"name": "random-incompressible-retains-raw-runtime", "passed": True},
            {"name": "equal-size-result-rejected-runtime", "passed": True},
            {"name": "zero-length-raw-runtime", "passed": True},
            {"name": "strictly-smaller-result-eligible-runtime", "passed": True},
        ]

    hashes = {
        "v1/build/kernel.bin": sha256_file(kernel),
        "v1/build/p421-pack-decision.bin": sha256_file(binary),
        "v1/src/kernel/zxpack.asm": sha256_file(root / "v1/src/kernel/zxpack.asm"),
        "v1/tools-host/test-driver/phase4_raw_retention.py": sha256_file(root / "v1/tools-host/test-driver/phase4_raw_retention.py"),
        "v1/tools-host/test-driver/run.py": sha256_file(root / "v1/tools-host/test-driver/run.py"),
        "v1/dist/certification/P4.20.test.json": sha256_file(root / "v1/dist/certification/P4.20.test.json"),
    }
    return [kernel_result, fixture_result], hashes, assertions
