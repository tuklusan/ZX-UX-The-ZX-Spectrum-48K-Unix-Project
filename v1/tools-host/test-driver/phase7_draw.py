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

MODULE = 0xC000
DATA = 0xA000
MIRROR = 0x6000
DISPLAY_BYTES = 0x1B00
E_INVAL = 0x01


class P704Error(DriverError):
    pass


def require(value: bool, message: str) -> None:
    if not value:
        raise P704Error(message)


def _word(value: int) -> bytes:
    return bytes((value & 0xFF, (value >> 8) & 0xFF))


def _setb(address: int, value: int) -> bytes:
    return bytes((0x3E, value & 0xFF, 0x32)) + _word(address)


def _expectb(address: int, value: int) -> bytes:
    return b"\x3A" + _word(address) + bytes((0xFE, value & 0xFF)) + phase1._jp_nz(FAIL_PC)


def _jp_c(address: int) -> bytes:
    return b"\xDA" + _word(address)


def _jp_nc(address: int) -> bytes:
    return b"\xD2" + _word(address)


def _addr(x: int, y: int) -> int:
    return 0x4000 | ((y & 0xC0) << 5) | ((y & 0x07) << 8) | ((y & 0x38) << 2) | (x >> 3)


def _attr(x: int, y: int) -> int:
    return 0x5800 + (y >> 3) * 32 + (x >> 3)


def _line(x1: int, y1: int, x2: int, y2: int) -> list[tuple[int, int]]:
    points: list[tuple[int, int]] = []
    dx = abs(x2 - x1)
    sx = 1 if x1 < x2 else -1
    dy = -abs(y2 - y1)
    sy = 1 if y1 < y2 else -1
    err = dx + dy
    while True:
        points.append((x1, y1))
        if x1 == x2 and y1 == y2:
            return points
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x1 += sx
        if e2 <= dx:
            err += dx
            y1 += sy


def _expected_display(points: list[tuple[int, int]], attr: int) -> bytes:
    display = bytearray(DISPLAY_BYTES)
    for x, y in points:
        address = _addr(x, y)
        display[address - 0x4000] |= 0x80 >> (x & 7)
        display[_attr(x, y) - 0x4000] = attr
    return bytes(display)


def _source_contract(root: Path) -> list[dict[str, object]]:
    gfx = (root / "v1/src/kernel/graphics.asm").read_text(encoding="utf-8")
    rom = (root / "v1/src/kernel/rom_services.asm").read_text(encoding="utf-8")
    plan = (root / "docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md").read_text(encoding="utf-8")
    start = gfx.index("zx48_gfx_draw:")
    end = gfx.index("; HL -> x,y,radius.", start)
    draw = gfx[start:end]
    first_store = min(draw.index("ld (gfx_x),a"), draw.index("ld (gfx_y),a"))
    second_validation = draw.index("cp 192", draw.index("cp 192") + 1)
    return [
        {"name": "canonical-p704-present", "passed": "## P7.04 - SYS_GFX_DRAW" in plan},
        {"name": "rom-lower-draw-ledger-remains-24ba", "passed": "ROM_DRAW_LINE             EQU $24BA" in rom},
        {"name": "native-draw-replacement-rationale-recorded", "passed": "lower ROM path ultimately reaches PLOT-SUB" in gfx and "0..191 coordinate ABI" in gfx},
        {"name": "both-y-endpoints-validated-before-scratch-or-display-side-effects", "passed": second_validation < first_store and "zx48_gfx_draw_bad:" in draw},
        {"name": "draw-raster-delegates-every-visible-point-to-qualified-plot", "passed": "call zx48_gfx_plot" in draw},
        {"name": "draw-uses-sixteen-bit-error-scratch", "passed": "ld (gfx_err),hl" in draw and "ld (gfx_e2),hl" in draw},
        {"name": "public-draw-pointer-validates-complete-four-byte-record", "passed": "ld bc,4\n    call zx48_user_range_validate" in (root / "v1/src/kernel/syscall.asm").read_text(encoding="utf-8")},
    ]


def _assemble(root: Path, run_command: Callable[..., Any], require_project_tool: Callable[[Path, str | Path], Path]):
    assembler = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    source = build / "p704-draw.asm"
    binary = build / "p704-draw.bin"
    symbols = build / "p704-draw.sym"
    source.write_text(
        "    DEVICE ZXSPECTRUM48\n"
        "    INCLUDE \"../include/zx48ux.inc\"\n"
        f"    ORG ${MODULE:04X}\\n"
        "p704_start:\n"
        "tty_current_attr: db 7\n"
        "zx48_cursor_hide: ret\n"
        "zx48_cursor_show: ret\n"
        "zx48_ula_set_border: xor a : ret\n"
        "zx48_bitmap_address:\n"
        "    ld a,b\n"
        "    and 7\n"
        "    or $40\n"
        "    ld h,a\n"
        "    ld a,b\n"
        "    and $c0\n"
        "    rrca\n"
        "    rrca\n"
        "    rrca\n"
        "    or h\n"
        "    ld h,a\n"
        "    ld a,b\n"
        "    and $38\n"
        "    rlca\n"
        "    rlca\n"
        "    or c\n"
        "    ld l,a\n"
        "    ret\n"
        "    INCLUDE \"../src/kernel/syscall.asm\"\n"
        "    EMIT_USER_RANGE_VALIDATION_ROUTINE\n"
        "    EMIT_GRAPHICS_ROUTINES\n"
        "    EMIT_P701_GRAPHICS_SYSCALL_ROUTINES\n"
        "p704_end:\n"
        "    SAVEBIN \"p704-draw.bin\",p704_start,p704_end-p704_start\n",
        encoding="utf-8",
        newline="\n",
    )
    result = run_command(
        [assembler, "--nologo", "--lst=p704-draw.lst", "--sym=p704-draw.sym", "p704-draw.asm"],
        cwd=build,
        timeout_seconds=30.0,
    )
    require(not result.timed_out and result.exit_code == 0, f"P7.04 fixture assembly failed: {result.stderr or result.stdout}")
    require(binary.is_file() and 0 < binary.stat().st_size < 8192, "P7.04 fixture missing/oversize")
    require(symbols.is_file(), "P7.04 fixture symbols missing")
    return result, binary, symbols


def _compare_display(code: bytearray) -> None:
    code += phase1._ld_hl(0x4000) + phase1._ld_de(MIRROR) + b"\x01" + _word(DISPLAY_BYTES)
    loop = 0x9000 + len(code)
    code += b"\x1A\xBE" + phase1._jp_nz(FAIL_PC) + b"\x23\x13\x0B\x78\xB1" + phase1._jp_nz(loop)


def _patch(module: bytes, record: bytes, expected: bytes):
    def apply(ram: bytearray) -> None:
        ram[MODULE - 0x4000:MODULE - 0x4000 + len(module)] = module
        ram[DATA - 0x4000:DATA - 0x4000 + len(record)] = record
        ram[MIRROR - 0x4000:MIRROR - 0x4000 + len(expected)] = expected
    return apply


def _run_vector(root: Path, symbols: dict[str, int], module: bytes, vector: tuple[int, int, int, int]) -> None:
    x1, y1, x2, y2 = vector
    attr = 0x47
    expected = _expected_display(_line(x1, y1, x2, y2), attr)
    code = bytearray(b"\xF3" + phase1._ld_sp(phase1.USER_STACK))
    code += _setb(symbols["tty_current_attr"], attr)
    code += _setb(symbols["gfx_attr_state"] + 4, 0) + _setb(symbols["gfx_attr_state"] + 5, 0)
    code += phase1._ld_hl(DATA) + b"\x22" + _word(symbols["syscall_arg_hl"])
    code += bytes((0x3E, symbols["SYS_GFX_DRAW"] & 0xFF)) + phase1._call(symbols["zx48_p701_gfx_dispatch"])
    code += _jp_c(FAIL_PC) + b"\xB7" + phase1._jp_nz(FAIL_PC)
    _compare_display(code)
    code += phase1._jp(PASS_PC)
    run_sna(root, bytes(code), patch=_patch(module, bytes(vector), expected), timeout=20.0)


def _run_negative(root: Path, symbols: dict[str, int], module: bytes, record: bytes) -> None:
    expected = bytes(DISPLAY_BYTES)
    code = bytearray(b"\xF3" + phase1._ld_sp(phase1.USER_STACK))
    scratch = ("gfx_x", "gfx_y", "gfx_x2", "gfx_y2", "gfx_dx", "gfx_dy", "gfx_sx", "gfx_sy")
    for index, name in enumerate(scratch):
        code += _setb(symbols[name], 0x80 + index)
    code += phase1._ld_hl(DATA) + b"\x22" + _word(symbols["syscall_arg_hl"])
    code += bytes((0x3E, symbols["SYS_GFX_DRAW"] & 0xFF)) + phase1._call(symbols["zx48_p701_gfx_dispatch"])
    code += _jp_nc(FAIL_PC) + bytes((0xFE, E_INVAL)) + phase1._jp_nz(FAIL_PC)
    for index, name in enumerate(scratch):
        code += _expectb(symbols[name], 0x80 + index)
    _compare_display(code)

    code += phase1._ld_hl(0xDFFE) + b"\x22" + _word(symbols["syscall_arg_hl"])
    code += bytes((0x3E, symbols["SYS_GFX_DRAW"] & 0xFF)) + phase1._call(symbols["zx48_p701_gfx_dispatch"])
    code += _jp_nc(FAIL_PC) + bytes((0xFE, E_INVAL)) + phase1._jp_nz(FAIL_PC)
    _compare_display(code)
    code += phase1._jp(PASS_PC)
    run_sna(root, bytes(code), patch=_patch(module, record, expected), timeout=20.0)


def dispatch(root: Path, action: str, step: str, *, sha256_file, run_command, require_project_tool):
    if step != "P7.04":
        raise P704Error(f"unsupported {step} {action}")
    assertions = _source_contract(root)
    failed = [item["name"] for item in assertions if item.get("passed") is not True]
    require(not failed, f"P7.04 static failure: {failed}")

    kernel_command, kernel, _listing = phase1._assemble_kernel(root, run_command, require_project_tool)
    fixture_command, binary, symbols_path = _assemble(root, run_command, require_project_tool)
    names = (
        "zx48_p701_gfx_dispatch", "syscall_arg_hl", "SYS_GFX_DRAW", "tty_current_attr", "gfx_attr_state",
        "gfx_x", "gfx_y", "gfx_x2", "gfx_y2", "gfx_dx", "gfx_dy", "gfx_sx", "gfx_sy",
    )
    symbols = phase3_open_descriptions._symbols(symbols_path, names)
    if action == "test":
        module = binary.read_bytes()
        for vector in (
            (0, 0, 255, 0),
            (255, 191, 0, 191),
            (0, 0, 0, 191),
            (255, 191, 255, 0),
            (0, 0, 191, 191),
            (191, 191, 0, 0),
            (32, 40, 96, 104),
        ):
            _run_vector(root, symbols, module, vector)
        _run_negative(root, symbols, module, bytes((1, 192, 3, 1)))
        _run_negative(root, symbols, module, bytes((1, 1, 3, 255)))
        assertions.extend((
            {"name": "fuse-horizontal-vertical-diagonal-reverse-boundary-vectors-match-independent-oracle", "passed": True},
            {"name": "fuse-invalid-endpoints-and-malformed-record-fail-before-visible-or-scratch-mutation", "passed": True},
        ))

    hashes = {
        "v1/build/kernel.bin": sha256_file(kernel),
        "v1/build/p704-draw.bin": sha256_file(binary),
        "v1/src/kernel/graphics.asm": sha256_file(root / "v1/src/kernel/graphics.asm"),
        "v1/src/kernel/syscall.asm": sha256_file(root / "v1/src/kernel/syscall.asm"),
        "v1/src/kernel/rom_services.asm": sha256_file(root / "v1/src/kernel/rom_services.asm"),
        "v1/tools-host/test-driver/phase7_draw.py": sha256_file(root / "v1/tools-host/test-driver/phase7_draw.py"),
        "v1/tools-host/test-driver/run.py": sha256_file(root / "v1/tools-host/test-driver/run.py"),
    }
    return [kernel_command, fixture_command], hashes, assertions
