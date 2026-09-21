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
MIRROR = 0x6000
DISPLAY_BYTES = 0x1B00
ROM_BASIC_MAX_Y = 175
E_INVAL = 0x01


class P703Error(DriverError):
    pass


def require(value: bool, message: str) -> None:
    if not value:
        raise P703Error(message)


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


def _mask(x: int) -> int:
    return 0x80 >> (x & 7)


def _source_contract(root: Path) -> list[dict[str, object]]:
    gfx = (root / "v1/src/kernel/graphics.asm").read_text(encoding="utf-8")
    plan = (root / "docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md").read_text(encoding="utf-8")
    start = gfx.index("zx48_gfx_plot:")
    end = gfx.index("; H=x,L=y -> H=0,L=0/1.", start)
    plot = gfx[start:end]
    validation = plot.index("cp 192")
    hide = plot.index("call zx48_cursor_hide")
    store = plot.index("ld (hl),a")
    attr_store = plot.index("ld a,(tty_current_attr)")
    return [
        {"name": "canonical-p703-present", "passed": "## P7.03 - SYS_GFX_PLOT" in plan},
        {"name": "plot-validates-y-before-visible-mutation", "passed": validation < hide},
        {"name": "plot-public-domain-is-full-256x192", "passed": "cp 192" in plot and ROM_BASIC_MAX_Y < 191},
        {"name": "native-replacement-rationale-records-rom-domain-mismatch", "passed": "rejects y>175" in gfx and "full top-origin 0..191" in gfx},
        {"name": "plot-delegates-to-p702-canonical-bitmap-helper", "passed": "call zx48_gfx_pixel_addr" in plot and "call zx48_bitmap_address" in gfx},
        {"name": "plot-publishes-current-hardware-attribute-after-pixel", "passed": store < attr_store and "ld bc,ATTR_START" in plot},
        {"name": "plot-exact-over-inverse-four-mode-shape", "passed": all(token in plot for token in (
            "OVER 1 + INVERSE 1 leaves pixel unchanged",
            "OVER 1 + INVERSE 0 toggles the pixel",
            "OVER 0 + INVERSE 0 sets the pixel",
            "OVER 0 + INVERSE 1 clears the pixel",
        ))},
        {"name": "plot-success-is-canonical-zero-carry-clear", "passed": "call zx48_cursor_show\n    xor a\n    or a\n    ret" in plot},
    ]


def _assemble(root: Path, run_command: Callable[..., Any], require_project_tool: Callable[[Path, str | Path], Path]):
    assembler = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    source = build / "p703-plot.asm"
    binary = build / "p703-plot.bin"
    symbols = build / "p703-plot.sym"
    source.write_text(
        "    DEVICE ZXSPECTRUM48\n"
        "    INCLUDE \"../include/zx48ux.inc\"\n"
        f"    ORG ${MODULE:04X}\n"
        "tty_current_attr: db 7\n"
        "p703_hide_count: db 0\n"
        "p703_show_count: db 0\n"
        "zx48_cursor_hide:\n"
        "    ld a,(p703_hide_count)\n"
        "    inc a\n"
        "    ld (p703_hide_count),a\n"
        "    ret\n"
        "zx48_cursor_show:\n"
        "    ld a,(p703_show_count)\n"
        "    inc a\n"
        "    ld (p703_show_count),a\n"
        "    ret\n"
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
        "    INCLUDE \"../src/kernel/graphics.asm\"\n"
        "    EMIT_GRAPHICS_ROUTINES\n"
        "p703_end:\n"
        "    SAVEBIN \"p703-plot.bin\",$C000,p703_end-$C000\n",
        encoding="utf-8",
        newline="\n",
    )
    result = run_command(
        [assembler, "--nologo", "--lst=p703-plot.lst", "--sym=p703-plot.sym", "p703-plot.asm"],
        cwd=build,
        timeout_seconds=30.0,
    )
    require(not result.timed_out and result.exit_code == 0, f"P7.03 fixture assembly failed: {result.stderr or result.stdout}")
    require(binary.is_file() and 0 < binary.stat().st_size < 4096, "P7.03 fixture missing/oversize")
    require(symbols.is_file(), "P7.03 fixture symbols missing")
    return result, binary, symbols


def _call_plot(address: int, x: int, y: int) -> bytes:
    return phase1._ld_hl(((x & 0xFF) << 8) | (y & 0xFF)) + phase1._call(address)


def _copy_display_to_mirror() -> bytes:
    return phase1._ld_hl(0x4000) + phase1._ld_de(MIRROR) + b"\x01" + _word(DISPLAY_BYTES) + b"\xED\xB0"


def _compare_display_to_mirror(program_address: int, code: bytearray) -> None:
    code += phase1._ld_hl(0x4000) + phase1._ld_de(MIRROR) + b"\x01" + _word(DISPLAY_BYTES)
    loop = program_address + len(code)
    code += b"\x1A\xBE" + phase1._jp_nz(FAIL_PC) + b"\x23\x13\x0B\x78\xB1" + phase1._jp_nz(loop)


def _runtime(root: Path, symbols: dict[str, int], module: bytes) -> None:
    code = bytearray(b"\xF3" + phase1._ld_sp(phase1.USER_STACK))
    code += _setb(symbols["tty_current_attr"], 0x47)
    code += _setb(symbols["gfx_attr_state"] + 4, 0)
    code += _setb(symbols["gfx_attr_state"] + 5, 0)
    valid_calls = 0

    vectors = ((0, 0), (255, 0), (0, 191), (255, 191), (1, 1), (127, 95), (128, 96), (42, 173))
    for x, y in vectors:
        address = _addr(x, y)
        attr = _attr(x, y)
        guard = address + 1 if address < 0x57FF else address - 1
        attr_guard = attr + 1 if attr < 0x5AFF else attr - 1
        code += _setb(address, 0x00) + _setb(guard, 0x5A)
        code += _setb(attr, 0xA5) + _setb(attr_guard, 0x3C)
        code += _call_plot(symbols["zx48_gfx_plot"], x, y) + _jp_c(FAIL_PC) + b"\xB7" + phase1._jp_nz(FAIL_PC)
        code += _expectb(address, _mask(x)) + _expectb(guard, 0x5A)
        code += _expectb(attr, 0x47) + _expectb(attr_guard, 0x3C)
        valid_calls += 1

    mode_x, mode_y = 37, 88
    address = _addr(mode_x, mode_y)
    attr = _attr(mode_x, mode_y)
    mask = _mask(mode_x)
    modes = (
        (0, 0, 0x12, 0x12 | mask),
        (0, 1, 0xFF, 0xFF & (~mask & 0xFF)),
        (1, 0, 0x55, 0x55 ^ mask),
        (1, 1, 0xAA, 0xAA),
    )
    for over, inverse, initial, expected in modes:
        code += _setb(symbols["gfx_attr_state"] + 5, over)
        code += _setb(symbols["gfx_attr_state"] + 4, inverse)
        code += _setb(address, initial) + _setb(attr, 0xA5)
        code += _call_plot(symbols["zx48_gfx_plot"], mode_x, mode_y) + _jp_c(FAIL_PC)
        code += b"\xB7" + phase1._jp_nz(FAIL_PC)
        code += _expectb(address, expected) + _expectb(attr, 0x47)
        valid_calls += 1

    code += _expectb(symbols["p703_hide_count"], valid_calls)
    code += _expectb(symbols["p703_show_count"], valid_calls)

    code += _copy_display_to_mirror()
    code += _setb(symbols["gfx_attr_state"] + 4, 0x5A)
    code += _setb(symbols["gfx_attr_state"] + 5, 0xA5)
    for y in (192, 255):
        code += _call_plot(symbols["zx48_gfx_plot"], 99, y)
        code += _jp_nc(FAIL_PC) + bytes((0xFE, E_INVAL)) + phase1._jp_nz(FAIL_PC)
    code += _expectb(symbols["gfx_attr_state"] + 4, 0x5A)
    code += _expectb(symbols["gfx_attr_state"] + 5, 0xA5)
    code += _expectb(symbols["p703_hide_count"], valid_calls)
    code += _expectb(symbols["p703_show_count"], valid_calls)
    _compare_display_to_mirror(0x9000, code)
    code += phase1._jp(PASS_PC)

    def patch(ram: bytearray) -> None:
        off = MODULE - 0x4000
        ram[off:off + len(module)] = module

    run_sna(root, bytes(code), patch=patch, timeout=20.0)


def dispatch(root: Path, action: str, step: str, *, sha256_file, run_command, require_project_tool):
    if step != "P7.03":
        raise P703Error(f"unsupported {step} {action}")
    assertions = _source_contract(root)
    failed = [item["name"] for item in assertions if item.get("passed") is not True]
    require(not failed, f"P7.03 static failure: {failed}")

    kernel_command, kernel, _listing = phase1._assemble_kernel(root, run_command, require_project_tool)
    fixture_command, binary, symbols_path = _assemble(root, run_command, require_project_tool)
    symbols = phase3_open_descriptions._symbols(
        symbols_path,
        ("zx48_gfx_plot", "gfx_attr_state", "tty_current_attr", "p703_hide_count", "p703_show_count"),
    )
    if action == "test":
        _runtime(root, symbols, binary.read_bytes())
        assertions.extend((
            {"name": "fuse-four-corners-and-interiors-set-exact-pixel-and-attribute", "passed": True},
            {"name": "fuse-over-inverse-four-mode-rom-visible-semantics", "passed": True},
            {"name": "fuse-y192-y255-einval-before-screen-cursor-or-state-mutation", "passed": True},
        ))

    hashes = {
        "v1/build/kernel.bin": sha256_file(kernel),
        "v1/build/p703-plot.bin": sha256_file(binary),
        "v1/src/kernel/graphics.asm": sha256_file(root / "v1/src/kernel/graphics.asm"),
        "v1/src/kernel/syscall.asm": sha256_file(root / "v1/src/kernel/syscall.asm"),
        "v1/src/kernel/rom_services.asm": sha256_file(root / "v1/src/kernel/rom_services.asm"),
        "v1/tools-host/test-driver/phase7_plot.py": sha256_file(root / "v1/tools-host/test-driver/phase7_plot.py"),
        "v1/tools-host/test-driver/run.py": sha256_file(root / "v1/tools-host/test-driver/run.py"),
    }
    return [kernel_command, fixture_command], hashes, assertions
