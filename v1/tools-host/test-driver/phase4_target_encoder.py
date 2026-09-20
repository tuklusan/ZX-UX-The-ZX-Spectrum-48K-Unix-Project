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


class P420Error(DriverError):
    pass


def require(ok: bool, msg: str) -> None:
    if not ok:
        raise P420Error(msg)


def _word(value: int) -> bytes:
    return bytes((value & 0xFF, (value >> 8) & 0xFF))


def _ld_bc(value: int) -> bytes:
    return b"\x01" + _word(value)


def _jp_nc(address: int) -> bytes:
    return b"\xD2" + _word(address)


def _check_byte(address: int, value: int) -> bytes:
    return b"\x3A" + _word(address) + bytes((0xFE, value & 0xFF)) + phase1._jp_nz(FAIL_PC)


def _check_word(address: int, value: int) -> bytes:
    return b"\x2A" + _word(address) + phase1._ld_de(value) + b"\xB7\xED\x52" + phase1._jp_nz(FAIL_PC)


def _check_hl(value: int) -> bytes:
    return phase1._ld_de(value) + b"\xB7\xED\x52" + phase1._jp_nz(FAIL_PC)


def _check_bytes(address: int, data: bytes) -> bytes:
    out = bytearray()
    for i, value in enumerate(data):
        out += _check_byte(address + i, value)
    return bytes(out)


def _target_encode(data: bytes) -> bytes:
    table: list[int | None] = [None] * 256
    out = bytearray()
    literals = bytearray()
    p = 0

    def flush() -> None:
        nonlocal literals
        if literals:
            out.append(len(literals) - 1)
            out.extend(literals)
            literals = bytearray()

    while p < len(data):
        q = table[data[p]]
        back_len = 0
        distance = 0
        if q is not None and 1 <= p - q <= 256:
            distance = p - q
            while back_len < 130 and p + back_len < len(data) and data[q + back_len] == data[p + back_len]:
                back_len += 1

        rle_len = 1
        while rle_len < 66 and p + rle_len < len(data) and data[p + rle_len] == data[p]:
            rle_len += 1

        if rle_len >= 3 and rle_len >= back_len:
            flush()
            out.extend(((rle_len - 3) | 0x40, data[p]))
            count = rle_len
        elif back_len >= 3:
            flush()
            out.extend(((back_len - 3) | 0x80, distance - 1))
            count = back_len
        else:
            literals.append(data[p])
            count = 1
            if len(literals) == 64:
                flush()

        for k in range(count):
            table[data[p + k]] = p + k
        p += count

    flush()
    return bytes(out)


def _source_contract(root: Path) -> list[dict[str, object]]:
    zx = (root / "v1/src/kernel/zxpack.asm").read_text(encoding="utf-8")
    require("MACRO EMIT_P420_TARGET_ENCODER_ROUTINES" in zx, "P4.20 encoder macro missing")
    m = zx.split("MACRO EMIT_P420_TARGET_ENCODER_ROUTINES", 1)[1].split("ENDM", 1)[0]
    return [
        {"name": "exact-512-byte-workspace", "passed": m.count("ld bc,512") >= 2 and "ld bc,511" in m},
        {"name": "workspace-cold-no-compact", "passed": "ALLOC_COLD_PREFERRED|ALLOC_NO_COMPACT" in m},
        {"name": "table-init-ffff", "passed": "ld (hl),$ff" in m and "ld bc,511" in m},
        {"name": "nearest-only-u16-table", "passed": "zx48_p420_table_entry:" in m and "p420_q" in m and "p420_back_distance" in m},
        {"name": "backref-limit-130", "passed": "cp 130" in m},
        {"name": "rle-limit-66", "passed": "cp 66" in m},
        {"name": "literal-limit-64", "passed": "cp 64" in m},
        {"name": "rle-wins-equal-tie", "passed": "jr z,zx48_p420_emit_rle" in m},
        {"name": "every-consumed-position-updates-table", "passed": "zx48_p420_update_positions:" in m and m.count("call zx48_p420_update_positions") == 3},
        {"name": "two-distinct-workspace-passes", "passed": m.count("call zx48_p420_workspace_begin") == 2 and "p420_workspace_allocs" in m},
        {"name": "non-smaller-rejected-before-pass2", "passed": "jp nc,zx48_p420_no_saving" in m},
        {"name": "explicit-enomem-background-skip", "passed": "ld a,E_NOMEM" in m and "zx48_p420_background_skip:" in m},
        {"name": "pass2-length-matches-pass1", "passed": "p420_measured_len" in m and "jp nz,zx48_p420_format" in m},
    ]


def _assemble(root: Path, run_command: Callable[..., Any], require_project_tool: Callable[[Path, str | Path], Path]):
    asm = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    fixture = build / "p420-target-encoder.asm"
    fixture.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
PANIC_SCHEDULER EQU $03
    ORG $C000
    INCLUDE "../src/kernel/memory.asm"
    INCLUDE "../src/kernel/zxpack.asm"
    EMIT_MEMORY_ROUTINES
    EMIT_P420_TARGET_ENCODER_ROUTINES
zx48_process_count:
    xor a
    ret
zx48_panic:
    scf
    ret
    SAVEBIN "p420-target-encoder.bin",$C000,$-$C000
""", encoding="utf-8", newline="\n")
    result = run_command([asm, "--nologo", "--lst=p420-target-encoder.lst", "--sym=p420-target-encoder.sym", "p420-target-encoder.asm"], cwd=build, timeout_seconds=30.0)
    require(not result.timed_out and result.exit_code == 0, f"P4.20 fixture assembly failed: {result.stderr or result.stdout}")
    binary = build / "p420-target-encoder.bin"
    listing = build / "p420-target-encoder.lst"
    require(binary.is_file() and 0 < binary.stat().st_size < 16384, "P4.20 fixture binary missing/oversize")
    return result, binary, listing


def _runtime(root: Path, s: dict[str, int], module: bytes) -> None:
    free = s["memory_free_extents"]
    live = s["memory_live_allocations"]
    arena_start = s["ARENA_START"]
    arena_size = s["ARENA_SIZE"]

    def patch(data: bytes, *, free_bytes: int | None = None, dst_fill: int = 0xA5):
        def apply(ram: bytearray) -> None:
            ram[MODULE_BASE-0x4000:MODULE_BASE-0x4000+len(module)] = module
            ram[SRC_BASE-0x4000:SRC_BASE-0x4000+len(data)] = data
            ram[DST_BASE-0x4000:DST_BASE-0x4000+512] = bytes((dst_fill,)) * 512
            ram[free-0x4000:free-0x4000+64] = bytes(64)
            extent = arena_size if free_bytes is None else free_bytes
            ram[free-0x4000:free-0x4000+4] = _word(arena_start) + _word(extent)
            ram[live-0x4000:live-0x4000+2] = _word(0)
        return apply

    def call(data: bytes, mode: int = 0) -> bytes:
        return bytes((0x3E, mode & 0xFF)) + phase1._ld_hl(SRC_BASE) + _ld_bc(len(data)) + phase1._ld_de(DST_BASE) + phase1._call(s["zx48_p420_two_pass"])

    def execute(label: str, data: bytes, code: bytes, **kwargs) -> None:
        body = b"\xF3" + phase1._ld_sp(STACK_TOP) + code + phase1._jp(PASS_PC)
        try:
            run_sna(root, body, patch=patch(data, **kwargs))
        except DriverError as exc:
            raise P420Error(f"P4.20 runtime case failed: {label}: {exc}") from exc

    vectors = (
        ("rle-backref-equal-tie-prefers-rle", b"ababaaaa"),
        ("nearest-only-candidate", b"aaaabaaa"),
        ("literal-run-splits-at-64", bytes(range(70)) + b"\\xff" * 100),
        ("rle-splits-at-66", b"A" * 70),
        ("backref-splits-at-130", bytes(range(65)) * 3),
        ("mixed", b"abcabcabcXYZXYZXYZ" + bytes(range(40)) + b"QQQQQQQ"),
    )
    for label, data in vectors:
        expected = _target_encode(data)
        require(len(expected) < len(data), f"P4.20 vector unexpectedly non-compressible: {label}")
        code = call(data) + phase1._jp_c(FAIL_PC)
        code += _check_hl(len(expected))
        code += _check_bytes(DST_BASE, expected)
        code += _check_byte(s["p420_workspace_allocs"], 2)
        code += _check_word(s["p420_workspace_bytes"], 512)
        code += _check_word(live, 0)
        execute(label, data, code)

    nonsmaller = b"abc"
    code = call(nonsmaller) + phase1._jp_c(FAIL_PC)
    code += _check_hl(0)
    code += _check_byte(DST_BASE, 0xA5)
    code += _check_byte(s["p420_workspace_allocs"], 1)
    code += _check_word(live, 0)
    execute("non-smaller-remains-raw", nonsmaller, code)

    compressible = b"Z" * 66
    code = call(compressible) + _jp_nc(FAIL_PC)
    code += bytes((0xFE, s["E_NOMEM"])) + phase1._jp_nz(FAIL_PC)
    code += _check_byte(DST_BASE, 0xA5)
    code += _check_byte(s["p420_workspace_allocs"], 0)
    code += _check_word(live, 0)
    execute("explicit-workspace-failure-enomem", compressible, code, free_bytes=510)

    code = call(compressible, 1) + phase1._jp_c(FAIL_PC)
    code += _check_hl(0)
    code += _check_byte(DST_BASE, 0xA5)
    code += _check_byte(s["p420_workspace_allocs"], 0)
    code += _check_word(live, 0)
    execute("background-workspace-failure-skip", compressible, code, free_bytes=510)


def dispatch(root: Path, action: str, step: str, *, sha256_file, run_command, require_project_tool):
    if step != "P4.20":
        raise DriverError(f"Phase-4 target encoder step is not registered: {step}")
    assertions = _source_contract(root)
    failed = [x["name"] for x in assertions if x.get("passed") is not True]
    require(not failed, f"static P4.20 contract failures: {failed}")

    kernel_result, kernel, _ = phase1._assemble_kernel(root, run_command, require_project_tool)
    fixture_result, binary, listing = _assemble(root, run_command, require_project_tool)
    names = (
        "zx48_p420_two_pass", "p420_workspace_allocs", "p420_workspace_bytes",
        "memory_free_extents", "memory_live_allocations", "ARENA_START", "ARENA_SIZE", "E_NOMEM",
    )
    symbols = phase3_open_descriptions._symbols(listing.with_suffix(".sym"), names)
    require(symbols["ARENA_SIZE"] == 0x8000, "P4.20 arena-size contract changed")

    if action == "test":
        _runtime(root, symbols, binary.read_bytes())
        assertions += [
            {"name": "golden-target-greedy-vectors-runtime", "passed": True},
            {"name": "nearest-only-backref-runtime", "passed": True},
            {"name": "rle-equal-tie-runtime", "passed": True},
            {"name": "literal-rle-backref-limits-runtime", "passed": True},
            {"name": "exact-512-workspace-each-pass-runtime", "passed": True},
            {"name": "explicit-workspace-enomem-preserves-output-runtime", "passed": True},
            {"name": "background-workspace-failure-skips-runtime", "passed": True},
            {"name": "non-smaller-output-not-emitted-runtime", "passed": True},
        ]

    hashes = {
        "v1/build/kernel.bin": sha256_file(kernel),
        "v1/build/p420-target-encoder.bin": sha256_file(binary),
        "v1/src/kernel/zxpack.asm": sha256_file(root / "v1/src/kernel/zxpack.asm"),
        "v1/tools-host/test-driver/phase4_target_encoder.py": sha256_file(root / "v1/tools-host/test-driver/phase4_target_encoder.py"),
        "v1/tools-host/test-driver/run.py": sha256_file(root / "v1/tools-host/test-driver/run.py"),
        "v1/dist/certification/P4.19.test.json": sha256_file(root / "v1/dist/certification/P4.19.test.json"),
    }
    return [kernel_result, fixture_result], hashes, assertions
