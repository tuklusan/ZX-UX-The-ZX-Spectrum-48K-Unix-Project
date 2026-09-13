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

SCREEN = 0x4000
ATTR = 0x5800
VERIFY_PC = 0xB100
PANIC_SCHEDULER = 3
BASE_BYTE = 0x3C
ATTR_BYTE = 0x47


class CursorCoreError(DriverError):
    """Raised when the P1.24 software-cursor core contract is violated."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise CursorCoreError(message)


def _word(value: int) -> bytes:
    return bytes((value & 0xFF, (value >> 8) & 0xFF))


def _call(address: int) -> bytes:
    return b"\xCD" + _word(address)


def _jp(address: int) -> bytes:
    return b"\xC3" + _word(address)


def _jp_z(address: int) -> bytes:
    return b"\xCA" + _word(address)


def _jp_nz(address: int) -> bytes:
    return b"\xC2" + _word(address)


def _jp_c(address: int) -> bytes:
    return b"\xDA" + _word(address)


def _jp_pe(address: int) -> bytes:
    return b"\xEA" + _word(address)


def _store_byte(address: int, value: int) -> bytes:
    return bytes((0x3E, value & 0xFF, 0x32)) + _word(address)


def _load_byte(address: int) -> bytes:
    return b"\x3A" + _word(address)


def _expect_byte(address: int, value: int) -> bytes:
    return _load_byte(address) + bytes((0xFE, value & 0xFF)) + _jp_nz(FAIL_PC)


def _pixel(scan: int, byte_col: int = 0) -> int:
    require(0 <= scan < 192 and 0 <= byte_col < 32, "invalid bitmap fixture coordinate")
    return SCREEN | ((scan & 0xC0) << 5) | ((scan & 7) << 8) | ((scan & 0x38) << 2) | byte_col


def _patch(kernel: bytes, extras: tuple[tuple[int, bytes], ...] = ()):
    def apply(ram: bytearray) -> None:
        start = phase1.KERNEL_BASE - SCREEN
        ram[start:start + len(kernel)] = kernel
        for scan in range(8):
            ram[_pixel(scan) - SCREEN] = BASE_BYTE
        ram[ATTR - SCREEN] = ATTR_BYTE
        for address, payload in extras:
            offset = address - SCREEN
            require(0 <= offset <= len(ram) - len(payload), "cursor fixture patch outside RAM")
            ram[offset:offset + len(payload)] = payload
    return apply


def _source_contract(root: Path) -> list[dict[str, object]]:
    cursor = (root / "v1/src/kernel/cursor.asm").read_text(encoding="utf-8").lower()
    console = (root / "v1/src/kernel/console.asm").read_text(encoding="utf-8").lower()
    interrupt = (root / "v1/src/kernel/interrupt.asm").read_text(encoding="utf-8").lower()
    architecture = " ".join(
        (root / "docs/01-ZX-UX-ARCHITECTURE-REV12.md").read_text(encoding="utf-8").lower().split()
    )
    service = cursor[cursor.index("zx48_cursor_service:"):cursor.index("zx48_cursor_blink:")]
    screen_begin = cursor[cursor.index("zx48_screen_begin:"):cursor.index("zx48_cursor_service:")]
    screen_end = cursor[cursor.index("zx48_screen_end:"):cursor.index("    endm")]
    mode_set = console[console.index("zx48_tty_set_mode:"):console.index("zx48_tty_get_size:")]
    shape_set = console[console.index("zx48_tty_set_cursor:"):console.index("zx48_tty_get_cursor:")]
    init = console[console.index("zx48_console_init:"):console.index("zx48_console_clear:")]
    return [
        {"name": "private-logical-phase-state", "passed": "cursor_phase             equ cursor_state_base+0" in cursor},
        {"name": "private-physical-drawn-state", "passed": "tty_cursor_visible" in console},
        {"name": "private-mutation-depth-state", "passed": "screen_mutation_depth    equ cursor_state_base+1" in cursor},
        {"name": "cold-defaults-phase-divider-parity-depth", "passed": all(token in init for token in ("ld hl,1", "ld (cursor_phase),hl", "ld (tty_cursor_shape),hl", "ld (tty_row),hl", "ld (cursor_service_parity),a", "ld (tty_wrap_pending),a", "ld (cursor_blink_divider),a", "ld a,tty_mode_64", "ld (tty_mode),a"))},
        {"name": "outer-begin-hides-only-drawn-cursor", "passed": "inc (hl)" in screen_begin and "jr nz,zx48_screen_begin_done" in screen_begin and "tty_cursor_visible" in screen_begin and "call zx48_cursor_xor" in screen_begin},
        {"name": "depth-wrap-panics", "passed": "jr z,zx48_cursor_depth_panic" in screen_begin and "panic_scheduler" in cursor},
        {"name": "strict-end-underflow-panics", "passed": "jr z,zx48_cursor_depth_panic" in screen_end and "dec (hl)" in screen_end},
        {"name": "atomic-parity-fetch-clear", "passed": all(token in service for token in ("ld a,(screen_mutation_depth)", "zx48_cursor_service_core:", "ld a,i", "di", "ld hl,cursor_service_parity", "ld (hl),0", "ld hl,cursor_phase", "xor (hl)", "ld (hl),a", "jp po,zx48_cursor_reconcile", "ei"))},
        {"name": "safe-service-detects-unbalanced-depth", "passed": "jr nz,zx48_cursor_depth_panic" in service},
        {"name": "outer-begin-preserves-live-coordinate-pointer", "passed": all(token in screen_begin for token in ("push hl", "pop hl"))},
        {"name": "shape-phase-reconcile-is-xor", "passed": "zx48_cursor_reconcile:" in service and cursor.index("zx48_cursor_reconcile:") < cursor.index("zx48_cursor_xor:")},
        {"name": "bitmap-xor-has-32-and-64-masks", "passed": all(token in cursor for token in ("xor $ff", "xor $f0", "xor $0f"))},
        {"name": "mode-change-hides-before-commit", "passed": mode_set.index("call zx48_cursor_hide") < mode_set.index("ld (tty_mode),a") and "zx48_console_clear_body" in mode_set},
        {"name": "shape-change-hides-before-commit", "passed": shape_set.index("call zx48_cursor_hide") < shape_set.index("ld (tty_cursor_shape),a") and any(token in shape_set[shape_set.index("ld (tty_cursor_shape),a"):] for token in ("call zx48_cursor_show", "jp zx48_cursor_show"))},
        {"name": "im2-only-produces-service-parity", "passed": "xor 1\n    ld (hl),a" in interrupt and "zx48_cursor_xor" not in interrupt and "screen_mutation_depth" not in interrupt},
        {"name": "architecture-nested-mutation-contract-present", "passed": all(token in architecture for token in ("cursor_phase", "cursor_drawn", "screen_mutation_depth", "atomically fetch-and-clear cursor_service_parity", "silent depth wrap is a defect"))},
        {"name": "architecture-shape-off-clock-contract-present", "passed": "shape off does not reset logical phase or the blink clock" in architecture or "shape off may span blink intervals" in architecture},
    ]


def _defaults_fixture(root: Path, labels: dict[str, int], kernel: bytes) -> None:
    code = bytearray(b"\xF3" + phase1._ld_sp(phase1.USER_STACK))
    dirty = (
        ("tty_mode", 32),
        ("tty_row", 9),
        ("tty_col", 17),
        ("tty_cursor_visible", 0),
        ("cursor_phase", 0),
        ("cursor_service_parity", 1),
        ("screen_mutation_depth", 5),
        ("tty_wrap_pending", 1),
        ("tty_cursor_shape", 2),
        ("cursor_blink_divider", 24),
    )
    for name, value in dirty:
        code += _store_byte(labels[name], value)
    code += _call(labels["zx48_console_init"])
    expected = (
        ("tty_mode", 64),
        ("tty_row", 0),
        ("tty_col", 0),
        ("tty_cursor_visible", 0),
        ("cursor_phase", 1),
        ("cursor_service_parity", 0),
        ("screen_mutation_depth", 0),
        ("tty_wrap_pending", 0),
        ("tty_cursor_shape", 1),
        ("cursor_blink_divider", 0),
    )
    for name, value in expected:
        code += _expect_byte(labels[name], value)
    code += _jp(PASS_PC)
    run_sna(root, bytes(code), patch=_patch(kernel))


def _nested_reversible_fixture(root: Path, labels: dict[str, int], kernel: bytes) -> None:
    code = bytearray(b"\xF3" + phase1._ld_sp(phase1.USER_STACK))
    code += _call(labels["zx48_console_init"])
    code += _store_byte(labels["tty_cursor_shape"], 2)
    code += _call(labels["zx48_cursor_service"])
    code += _expect_byte(labels["tty_cursor_visible"], 1)
    code += _expect_byte(labels["screen_mutation_depth"], 0)
    for scan in range(8):
        code += _expect_byte(_pixel(scan), BASE_BYTE ^ 0xF0)
    code += _expect_byte(ATTR, ATTR_BYTE)

    code += _call(labels["zx48_screen_begin"])
    code += _expect_byte(labels["screen_mutation_depth"], 1)
    code += _expect_byte(labels["tty_cursor_visible"], 0)
    for scan in range(8):
        code += _expect_byte(_pixel(scan), BASE_BYTE)

    code += _call(labels["zx48_screen_begin"])
    code += _expect_byte(labels["screen_mutation_depth"], 2)
    code += _expect_byte(labels["tty_cursor_visible"], 0)
    code += _call(labels["zx48_screen_end"])
    code += _expect_byte(labels["screen_mutation_depth"], 1)
    code += _expect_byte(labels["tty_cursor_visible"], 0)
    code += _call(labels["zx48_screen_end"])
    code += _expect_byte(labels["screen_mutation_depth"], 0)
    code += _expect_byte(labels["tty_cursor_visible"], 1)
    for scan in range(8):
        code += _expect_byte(_pixel(scan), BASE_BYTE ^ 0xF0)
    code += _expect_byte(ATTR, ATTR_BYTE)

    # Moving a visible 64-column cursor must restore the old nibble first.
    code += b"\x21\x01\x00" + _call(labels["zx48_console_setpos"]) + _jp_c(FAIL_PC)
    code += _expect_byte(labels["tty_col"], 1)
    for scan in range(8):
        code += _expect_byte(_pixel(scan), BASE_BYTE ^ 0x0F)
    code += _expect_byte(ATTR, ATTR_BYTE)

    # Paired hide/show must be byte-exact and preserve the caller's DI state.
    code += _call(labels["zx48_cursor_hide"])
    for scan in range(8):
        code += _expect_byte(_pixel(scan), BASE_BYTE)
    code += _call(labels["zx48_cursor_show"])
    code += b"\xED\x57" + _jp_pe(FAIL_PC)  # LD A,I: P/V must remain clear after a DI entry.
    for scan in range(8):
        code += _expect_byte(_pixel(scan), BASE_BYTE ^ 0x0F)

    # tty32 uses the same logical model with an eight-pixel XOR footprint.
    code += _call(labels["zx48_screen_begin"])
    code += _store_byte(labels["tty_mode"], 32) + _store_byte(labels["tty_col"], 0)
    code += _call(labels["zx48_screen_end"])
    code += _expect_byte(labels["tty_cursor_visible"], 1)
    for scan in range(8):
        code += _expect_byte(_pixel(scan), BASE_BYTE ^ 0xFF)
    code += _expect_byte(ATTR, ATTR_BYTE)
    code += _jp(PASS_PC)
    run_sna(root, bytes(code), patch=_patch(kernel))


def _parity_shape_fixture(root: Path, labels: dict[str, int], kernel: bytes) -> None:
    code = bytearray(b"\xF3" + phase1._ld_sp(phase1.USER_STACK))
    code += _call(labels["zx48_console_init"])
    code += _store_byte(labels["tty_cursor_shape"], 2)
    code += _store_byte(labels["cursor_blink_divider"], 17)
    code += _call(labels["zx48_cursor_service"])

    # Two deferred transitions coalesce to parity zero and leave phase on.
    code += _call(labels["zx48_screen_begin"])
    code += _call(labels["zx48_cursor_blink"]) + _expect_byte(labels["cursor_service_parity"], 1)
    code += _call(labels["zx48_cursor_blink"]) + _expect_byte(labels["cursor_service_parity"], 0)
    code += _expect_byte(labels["cursor_phase"], 1) + _expect_byte(labels["tty_cursor_visible"], 0)
    code += _call(labels["zx48_screen_end"])
    code += _expect_byte(labels["cursor_phase"], 1) + _expect_byte(labels["tty_cursor_visible"], 1)

    # One deferred transition toggles once at the matching outer end.
    code += _call(labels["zx48_screen_begin"])
    code += _call(labels["zx48_cursor_blink"])
    code += _call(labels["zx48_screen_end"])
    code += _expect_byte(labels["cursor_service_parity"], 0)
    code += _expect_byte(labels["cursor_phase"], 0) + _expect_byte(labels["tty_cursor_visible"], 0)

    # Direct safe service at depth zero toggles once, with no catch-up loop.
    code += _call(labels["zx48_cursor_blink"])
    code += _expect_byte(labels["cursor_phase"], 1) + _expect_byte(labels["tty_cursor_visible"], 1)

    # Shape off may span odd blink intervals without resetting divider or phase.
    code += _call(labels["zx48_screen_begin"])
    code += _store_byte(labels["tty_cursor_shape"], 0)
    code += _call(labels["zx48_screen_end"])
    code += _expect_byte(labels["tty_cursor_visible"], 0)
    for _ in range(3):
        code += _call(labels["zx48_cursor_blink"])
    code += _expect_byte(labels["cursor_phase"], 0)
    code += _expect_byte(labels["tty_cursor_visible"], 0)
    code += _expect_byte(labels["cursor_blink_divider"], 17)

    # Re-enable underline while logical phase is off: still hidden until next service.
    code += _call(labels["zx48_screen_begin"])
    code += _store_byte(labels["tty_cursor_shape"], 1)
    code += _call(labels["zx48_screen_end"])
    code += _expect_byte(labels["cursor_phase"], 0) + _expect_byte(labels["tty_cursor_visible"], 0)
    code += _call(labels["zx48_cursor_blink"])
    code += _expect_byte(labels["cursor_phase"], 1) + _expect_byte(labels["tty_cursor_visible"], 1)
    for scan in range(7):
        code += _expect_byte(_pixel(scan), BASE_BYTE)
    code += _expect_byte(_pixel(7), BASE_BYTE ^ 0xF0)
    code += _expect_byte(ATTR, ATTR_BYTE)
    code += _jp(PASS_PC)
    run_sna(root, bytes(code), patch=_patch(kernel))


def _panic_negative(root: Path, labels: dict[str, int], kernel: bytes, *, wrap: bool) -> None:
    panic_halt = labels["zx48_panic_halt"]
    panic_code = labels["kernel_panic_code"]
    patched = bytearray(kernel)
    offset = panic_halt - phase1.KERNEL_BASE
    require(0 <= offset <= len(patched) - 3, "panic halt outside kernel image")
    patched[offset:offset + 3] = _jp(VERIFY_PC)
    verifier = _expect_byte(panic_code, PANIC_SCHEDULER) + _jp(PASS_PC)

    code = bytearray(b"\xF3" + phase1._ld_sp(phase1.USER_STACK))
    code += _call(labels["zx48_console_init"])
    if wrap:
        code += _store_byte(labels["screen_mutation_depth"], 0xFF)
        code += _call(labels["zx48_screen_begin"])
    else:
        code += _call(labels["zx48_screen_end"])
    code += _jp(FAIL_PC)
    run_sna(root, bytes(code), patch=_patch(bytes(patched), ((VERIFY_PC, verifier),)))


def _unbalanced_negative(root: Path, labels: dict[str, int], kernel: bytes) -> None:
    patched = bytearray(kernel)
    end_offset = labels["zx48_screen_end"] - phase1.KERNEL_BASE
    require(0 <= end_offset < len(patched), "screen-end label outside kernel image")
    patched[end_offset] = 0xC9  # RET: deliberate mutant leaves the outer begin unbalanced.
    panic_offset = labels["zx48_panic_halt"] - phase1.KERNEL_BASE
    require(0 <= panic_offset <= len(patched) - 3, "panic halt outside kernel image")
    patched[panic_offset:panic_offset + 3] = _jp(VERIFY_PC)
    verifier = _expect_byte(labels["kernel_panic_code"], PANIC_SCHEDULER) + _jp(PASS_PC)

    code = bytearray(b"\xF3" + phase1._ld_sp(phase1.USER_STACK))
    code += _call(labels["zx48_console_init"])
    code += b"\x21\x01\x00" + _call(labels["zx48_console_setpos"]) + _jp_c(FAIL_PC)
    code += _expect_byte(labels["screen_mutation_depth"], 1)
    code += _call(labels["zx48_cursor_service"]) + _jp(FAIL_PC)
    run_sna(root, bytes(code), patch=_patch(bytes(patched), ((VERIFY_PC, verifier),)))


def dispatch(
    root: Path,
    action: str,
    step: str,
    *,
    sha256_file: Callable[[Path], str],
    run_command: Callable[..., Any],
    require_project_tool: Callable[[Path, str | Path], Path],
):
    if step != "P1.24":
        raise CursorCoreError(f"software-cursor core step is not registered: {step}")

    assertions = _source_contract(root)
    failed = [item["name"] for item in assertions if item["passed"] is not True]
    require(not failed, f"static P1.24 failures: {failed}")

    command, kernel_path, listing = phase1._assemble_kernel(root, run_command, require_project_tool)
    names = (
        "zx48_console_init",
        "zx48_console_setpos",
        "zx48_cursor_hide",
        "zx48_cursor_show",
        "zx48_screen_begin",
        "zx48_screen_end",
        "zx48_cursor_service",
        "zx48_cursor_blink",
        "tty_mode",
        "tty_row",
        "tty_col",
        "tty_cursor_visible",
        "cursor_phase",
        "cursor_service_parity",
        "screen_mutation_depth",
        "tty_wrap_pending",
        "tty_cursor_shape",
        "cursor_blink_divider",
        "kernel_panic_code",
        "zx48_panic_halt",
        "kernel_ordinary_used_end",
    )
    labels = phase1._labels(listing, names)
    ordinary_end = labels["kernel_ordinary_used_end"]
    assertions.append(
        {
            "name": "ordinary-code-pool-within-faff",
            "passed": ordinary_end <= 0xFB00,
            "used_end": f"0x{ordinary_end:04X}",
            "free_bytes": 0xFB00 - ordinary_end,
        }
    )
    require(ordinary_end <= 0xFB00, f"ordinary kernel code overflow: end=0x{ordinary_end:04X}")
    kernel = kernel_path.read_bytes()

    if action == "test":
        _defaults_fixture(root, labels, kernel)
        _nested_reversible_fixture(root, labels, kernel)
        _parity_shape_fixture(root, labels, kernel)
        _panic_negative(root, labels, kernel, wrap=False)
        _panic_negative(root, labels, kernel, wrap=True)
        _unbalanced_negative(root, labels, kernel)
        assertions.extend(
            (
                {"name": "runtime-default-state-exact", "passed": True},
                {"name": "runtime-xor-hide-show-byte-exact", "passed": True},
                {"name": "runtime-neighbor-nibble-and-attribute-preserved", "passed": True},
                {"name": "runtime-tty32-full-byte-xor", "passed": True},
                {"name": "runtime-nested-hide-reconcile-once", "passed": True},
                {"name": "runtime-odd-even-parity-coalesces", "passed": True},
                {"name": "runtime-shape-off-preserves-phase-clock", "passed": True},
                {"name": "runtime-depth-underflow-panics", "passed": True},
                {"name": "runtime-depth-wrap-panics", "passed": True},
                {"name": "unbalanced-end-negative-sensitive", "passed": True},
            )
        )

    paths = (
        root / "docs/01-ZX-UX-ARCHITECTURE-REV12.md",
        root / "v1/src/kernel/cursor.asm",
        root / "v1/src/kernel/console.asm",
        root / "v1/src/kernel/interrupt.asm",
        root / "v1/src/kernel/tty32.asm",
        root / "v1/tools-host/test-driver/phase1_cursor_core.py",
        kernel_path,
    )
    return [command], {str(path.relative_to(root)): sha256_file(path) for path in paths}, assertions
