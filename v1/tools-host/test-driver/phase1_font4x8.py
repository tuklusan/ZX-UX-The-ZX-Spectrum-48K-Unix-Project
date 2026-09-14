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
import hashlib
from typing import Any, Callable

from driver_core import DriverError
from fuse_harness import FAIL_PC, PASS_PC, run_sna
import phase1

F4X8_SIZE = 392
F4X8_HEADER = b"F4X8\x01\x20\x60\x00"
F4X8_SHA256 = "90f6818cf81cf3f13509cff32c091075691195d9638dbe801d12daceec1c9339"
SOURCE = 0xB200
ROWS = 0xA000
CHAR_STATE = 0xB100
ROW_STATE = 0xB102
EXPECTED_RESOURCE = 0xDE78
EXPECTED_FONT = EXPECTED_RESOURCE + 8
EXPECTED_FREE_LENGTH = 0x7E78
COLD_ONLY_LENGTH = 0x2000


class Font4x8Error(DriverError):
    """Raised when the F4X8 validation/pinning contract is violated."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Font4x8Error(message)


def _word(value: int) -> bytes:
    return bytes((value & 0xFF, (value >> 8) & 0xFF))


def _call(address: int) -> bytes:
    return b"\xCD" + _word(address)


def _jp(address: int) -> bytes:
    return b"\xC3" + _word(address)


def _jp_c(address: int) -> bytes:
    return b"\xDA" + _word(address)


def _jp_nc(address: int) -> bytes:
    return b"\xD2" + _word(address)


def _jp_nz(address: int) -> bytes:
    return b"\xC2" + _word(address)


def _store_byte(address: int, value: int) -> bytes:
    return bytes((0x3E, value & 0xFF, 0x32)) + _word(address)


def _store_word(address: int, value: int) -> bytes:
    return b"\x21" + _word(value) + b"\x22" + _word(address)


def _expect_byte(address: int, value: int) -> bytes:
    return b"\x3A" + _word(address) + bytes((0xFE, value & 0xFF)) + _jp_nz(FAIL_PC)


def _expect_word(address: int, value: int) -> bytes:
    return b"\x2A" + _word(address) + b"\x11" + _word(value) + b"\xB7\xED\x52" + _jp_nz(FAIL_PC)


def _patch(kernel: bytes, extras: tuple[tuple[int, bytes], ...]):
    def apply(ram: bytearray) -> None:
        base = phase1.KERNEL_BASE - 0x4000
        ram[base:base + len(kernel)] = kernel
        for address, payload in extras:
            offset = address - 0x4000
            require(0 <= offset <= len(ram) - len(payload), "P1.21 fixture patch outside RAM")
            ram[offset:offset + len(payload)] = payload
    return apply


def _decode(payload: bytes) -> bytes:
    require(len(payload) == F4X8_SIZE, "F4X8 payload must be exactly 392 bytes")
    require(payload[:8] == F4X8_HEADER, "F4X8 header mismatch")
    rows = bytearray()
    for packed in payload[8:]:
        rows.append((packed >> 4) & 0x0F)
        rows.append(packed & 0x0F)
    require(len(rows) == 96 * 8, "F4X8 decode must produce 96*8 rows")
    return bytes(rows)


def _source_contract(root: Path, asset: bytes) -> list[dict[str, object]]:
    tty64 = (root / "v1/src/kernel/tty64.asm").read_text(encoding="utf-8").lower()
    include = (root / "v1/include/zx48ux.inc").read_text(encoding="utf-8").lower()
    docs = (root / "v1/docs/font4x8.md").read_text(encoding="utf-8").lower()
    rows = _decode(asset)
    swapped = bytearray()
    for packed in asset[8:]:
        swapped.append(packed & 0x0F)
        swapped.append((packed >> 4) & 0x0F)
    require(bytes(swapped) != rows, "fixture must distinguish high/low nibble ordering")
    installer = tty64[tty64.index("zx48_tty64_install_font:"):tty64.index("zx48_tty64_draw_char:")]
    renderer = tty64[tty64.index("zx48_tty64_draw_char:"):tty64.index("zx48_tty64_bad:")]
    return [
        {"name": "canonical-source-is-exact-392-byte-f4x8", "passed": len(asset) == F4X8_SIZE and asset[:8] == F4X8_HEADER},
        {"name": "canonical-source-sha256", "passed": hashlib.sha256(asset).hexdigest() == F4X8_SHA256},
        {"name": "host-decoder-produces-96x8-rows", "passed": len(rows) == 768},
        {"name": "host-decoder-distinguishes-altered-nibble-order", "passed": bytes(swapped) != rows},
        {"name": "target-validates-exact-length", "passed": "cp f4x8_size/256" in installer and "cp f4x8_size&$ff" in installer},
        {"name": "target-validates-complete-header", "passed": all(token in installer for token in ("cp 'f'", "cp '4'", "cp 'x'", "cp '8'", "cp 1", "cp $20", "cp 96", "or a"))},
        {"name": "target-uses-fast-required-without-cold-policy", "passed": "ld a,alloc_fast_required" in installer and "alloc_cold" not in installer},
        {"name": "target-copies-and-pins-exact-resource", "passed": installer.count("ld bc,f4x8_size") >= 3 and "call zx48_memcpy" in installer and "call zx48_memory_pin_bytes" in installer},
        {"name": "target-font-pointer-skips-header", "passed": "ld de,8" in installer and "ld (tty64_font_ptr),hl" in installer},
        {"name": "target-decoder-high-nibble-before-low", "passed": renderer.index("rrca") < renderer.index("zx48_tty64_nibble:") and "and 1" in renderer},
        {"name": "physical-pointers-not-public-abi", "passed": "tty64_resource_ptr" not in include and "tty64_font_ptr" not in include},
        {"name": "docs-freeze-canonical-phase0-identity", "passed": all(token in docs for token in ("392-byte", "high nibble", "low nibble", "alloc_fast_required", "no cold fallback", "font4x8-zxux.bin", F4X8_SHA256, "re-verifies"))},
    ]


def _install_prefix(labels: dict[str, int], length: int = F4X8_SIZE) -> bytearray:
    code = bytearray(b"\xF3" + phase1._ld_sp(phase1.USER_STACK))
    code += _call(labels["zx48_memory_init"])
    code += b"\x21" + _word(SOURCE)
    code += b"\x01" + _word(length)
    code += _call(labels["zx48_tty64_install_font"])
    return code


def _run_fixture(root: Path, name: str, code: bytes, patch) -> None:
    try:
        run_sna(root, code, patch=patch)
    except DriverError as exc:
        raise Font4x8Error(f"P1.21 runtime fixture {name} failed: {exc}") from exc


def _valid_runtime(root: Path, labels: dict[str, int], kernel: bytes, asset: bytes, rows: bytes) -> None:
    install = _install_prefix(labels)
    install += _jp_c(FAIL_PC)
    install += _expect_word(labels["tty64_resource_ptr"], EXPECTED_RESOURCE)
    install += _expect_word(labels["tty64_font_ptr"], EXPECTED_FONT)
    install += _expect_word(labels["memory_pinned_bytes"], F4X8_SIZE)
    install += _expect_word(labels["memory_live_allocations"], 1)
    install += _expect_word(labels["memory_free_extents"], 0x6000)
    install += _expect_word(labels["memory_free_extents"] + 2, EXPECTED_FREE_LENGTH)
    install += _expect_byte(labels["tty_mode"], 64)
    install += _jp(PASS_PC)
    _run_fixture(root, "valid-install-state", bytes(install), _patch(kernel, ((SOURCE, asset),)))

    copy = _install_prefix(labels)
    copy += _jp_c(FAIL_PC)
    copy += b"\x21" + _word(SOURCE) + b"\x11" + _word(EXPECTED_RESOURCE) + b"\x01" + _word(F4X8_SIZE)
    compare_loop = len(copy)
    copy += b"\x1A\xBE" + _jp_nz(FAIL_PC) + b"\x13\x23\x0B\x78\xB1"
    rel = compare_loop - (len(copy) + 2)
    require(-128 <= rel <= 127, "copy-compare loop displacement out of range")
    copy += bytes((0x20, rel & 0xFF))
    copy += _jp(PASS_PC)
    _run_fixture(root, "valid-exact-copy", bytes(copy), _patch(kernel, ((SOURCE, asset),)))

    render = _install_prefix(labels)
    render += _jp_c(FAIL_PC)
    render += _store_byte(labels["tty_row"], 0) + _store_byte(labels["tty_col"], 0)
    render += _store_byte(CHAR_STATE, 0x20)
    render += _store_word(ROW_STATE, ROWS)
    glyph_loop = len(render)
    render += b"\x3A" + _word(CHAR_STATE) + _call(labels["zx48_tty64_draw_char"]) + _jp_c(FAIL_PC)
    render += b"\x2A" + _word(ROW_STATE)
    for scan in range(8):
        address = 0x4000 + scan * 0x100
        render += b"\x3A" + _word(address) + b"\xE6\xF0\xBE" + _jp_nz(FAIL_PC) + b"\x23"
    render += b"\x22" + _word(ROW_STATE)
    render += b"\x3A" + _word(CHAR_STATE) + b"\x3C\x32" + _word(CHAR_STATE) + b"\xFE\x80"
    rel = glyph_loop - (len(render) + 2)
    require(-128 <= rel <= 127, "glyph loop displacement out of range")
    render += bytes((0x20, rel & 0xFF))
    render += _jp(PASS_PC)
    shifted_rows = bytes(value << 4 for value in rows)
    _run_fixture(
        root,
        "valid-render-96x8",
        bytes(render),
        _patch(kernel, ((SOURCE, asset), (ROWS, shifted_rows))),
    )

def _invalid_runtime(root: Path, labels: dict[str, int], kernel: bytes, asset: bytes, *, offset: int | None = None, value: int | None = None, length: int = F4X8_SIZE) -> None:
    mutant = bytearray(asset)
    if offset is not None:
        require(value is not None, "mutant value missing")
        mutant[offset] = value & 0xFF
    code = _install_prefix(labels, length)
    code += _jp_nc(FAIL_PC)
    code += bytes((0xFE, labels["E_INVAL"] & 0xFF)) + _jp_nz(FAIL_PC)
    code += _expect_word(labels["memory_live_allocations"], 0)
    code += _expect_word(labels["memory_pinned_bytes"], 0)
    code += _expect_word(labels["tty64_resource_ptr"], 0)
    code += _jp(PASS_PC)
    identity = f"invalid-header-{offset}" if offset is not None else f"invalid-length-{length}"
    _run_fixture(root, identity, bytes(code), _patch(kernel, ((SOURCE, bytes(mutant)),)))


def _fast_failure_runtime(root: Path, labels: dict[str, int], kernel: bytes, asset: bytes) -> None:
    code = bytearray(b"\xF3" + phase1._ld_sp(phase1.USER_STACK))
    code += _call(labels["zx48_memory_init"])
    code += _store_word(labels["memory_free_extents"], 0x6000)
    code += _store_word(labels["memory_free_extents"] + 2, COLD_ONLY_LENGTH)
    code += b"\x21" + _word(SOURCE) + b"\x01" + _word(F4X8_SIZE)
    code += _call(labels["zx48_tty64_install_font"])
    code += _jp_nc(FAIL_PC)
    code += bytes((0xFE, labels["E_NOMEM"] & 0xFF)) + _jp_nz(FAIL_PC)
    code += _expect_word(labels["memory_live_allocations"], 0)
    code += _expect_word(labels["memory_pinned_bytes"], 0)
    code += _expect_word(labels["memory_free_extents"], 0x6000)
    code += _expect_word(labels["memory_free_extents"] + 2, COLD_ONLY_LENGTH)
    code += _jp(PASS_PC)
    _run_fixture(root, "fast-required-no-cold-spill", bytes(code), _patch(kernel, ((SOURCE, asset),)))


def dispatch(
    root: Path,
    action: str,
    step: str,
    *,
    sha256_file: Callable[[Path], str],
    run_command: Callable[..., Any],
    require_project_tool: Callable[[Path, str | Path], Path],
):
    if step != "P1.21":
        raise Font4x8Error(f"F4X8 step is not registered: {step}")

    asset_path = root / "v1/assets/font4x8-zxux.bin"
    asset = asset_path.read_bytes()
    rows = _decode(asset)
    assertions = _source_contract(root, asset)
    failed = [item["name"] for item in assertions if item["passed"] is not True]
    require(not failed, f"static P1.21 failures: {failed}")

    command, kernel_path, listing = phase1._assemble_kernel(root, run_command, require_project_tool)
    labels = phase1._labels(
        listing,
        (
            "zx48_memory_init",
            "zx48_tty64_install_font",
            "zx48_tty64_draw_char",
            "tty64_resource_ptr",
            "tty64_font_ptr",
            "memory_pinned_bytes",
            "memory_live_allocations",
            "memory_free_extents",
            "tty_mode",
            "tty_row",
            "tty_col",
            "E_INVAL",
            "E_NOMEM",
        ),
    )
    kernel = kernel_path.read_bytes()
    if action == "test":
        _valid_runtime(root, labels, kernel, asset, rows)
        for offset, value in ((0, ord("X")), (1, ord("X")), (2, ord("Y")), (3, ord("X")), (4, 2), (5, 0x21), (6, 95), (7, 1)):
            _invalid_runtime(root, labels, kernel, asset, offset=offset, value=value)
        _invalid_runtime(root, labels, kernel, asset, length=F4X8_SIZE - 1)
        _invalid_runtime(root, labels, kernel, asset, length=F4X8_SIZE + 1)
        _fast_failure_runtime(root, labels, kernel, asset)
        assertions.extend(
            [
                {"name": "valid-resource-pins-fast-and-copies-exactly", "passed": True},
                {"name": "all-96x8-target-rows-match-host-decoder", "passed": True},
                {"name": "malformed-header-and-length-matrix-rejected", "passed": True},
                {"name": "fast-required-failure-does-not-spill-cold", "passed": True},
            ]
        )

    paths = (
        asset_path,
        root / "v1/include/zx48ux.inc",
        root / "v1/src/kernel/tty64.asm",
        root / "v1/src/kernel/memory.asm",
        root / "v1/docs/font4x8.md",
        root / "v1/tools-host/test-driver/phase1_font4x8.py",
        kernel_path,
    )
    return [command], {str(path.relative_to(root)): sha256_file(path) for path in paths}, assertions
