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

DATA = 0xA000


class P701Error(DriverError):
    pass


def require(value: bool, message: str) -> None:
    if not value:
        raise P701Error(message)


def _word(value: int) -> bytes:
    return bytes((value & 0xFF, (value >> 8) & 0xFF))


def _setb(address: int, value: int) -> bytes:
    return bytes((0x3E, value & 0xFF, 0x32)) + _word(address)


def _expectb(address: int, value: int) -> bytes:
    return b"\x3a" + _word(address) + bytes((0xFE, value & 0xFF)) + phase1._jp_nz(FAIL_PC)


def _jp_nc(address: int) -> bytes:
    return b"\xd2" + _word(address)


def _source_contract(root: Path) -> list[dict[str, object]]:
    inc = (root / "v1/include/zx48ux.inc").read_text(encoding="utf-8")
    syscall = (root / "v1/src/kernel/syscall.asm").read_text(encoding="utf-8")
    gfx = (root / "v1/src/kernel/graphics.asm").read_text(encoding="utf-8")
    plan = (root / "docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md").read_text(encoding="utf-8")
    values = (
        "SYS_GFX_PLOT             EQU $40",
        "SYS_GFX_DRAW             EQU $41",
        "SYS_GFX_CIRCLE           EQU $42",
        "SYS_GFX_ATTR             EQU $43",
        "SYS_GFX_BORDER           EQU $44",
        "SYS_GFX_POINT            EQU $45",
    )
    table = (
        "dw zx48_sys_gfx_plot,zx48_sys_gfx_draw,zx48_sys_gfx_circle",
        "dw zx48_sys_gfx_attr,zx48_sys_gfx_border,zx48_sys_gfx_point",
    )
    labels = (
        "zx48_gfx_plot:", "zx48_gfx_draw:", "zx48_gfx_circle:",
        "zx48_gfx_attr:", "zx48_gfx_border:", "zx48_gfx_point:",
    )
    return [
        {"name": "canonical-p701-present", "passed": "## P7.01 - Graphics syscall ABI" in plan},
        {"name": "six-public-gfx-selector-values-exact", "passed": all(x in inc for x in values)},
        {"name": "graphics-source-included-once", "passed": syscall.count('INCLUDE "graphics.asm"') == 1},
        {"name": "graphics-dispatch-range-exact", "passed": all(x in syscall for x in ("cp SYS_GFX_PLOT", "cp SYS_GFX_POINT+1", "sub SYS_GFX_PLOT", "zx48_sys_dispatch_gfx:"))},
        {"name": "graphics-dispatch-table-order-exact", "passed": all(x in syscall for x in table)},
        {"name": "record-pointers-validated-before-draw-circle", "passed": "ld bc,4\n    call zx48_user_range_validate" in syscall and "ld bc,3\n    call zx48_user_range_validate" in syscall},
        {"name": "all-six-native-entrypoints-present", "passed": all(x in gfx for x in labels)},
        {"name": "plot-point-y-domain-fail-closed", "passed": gfx.count("cp 192") >= 2 and "zx48_gfx_bad:" in gfx},
        {"name": "attr-border-domain-validation-present", "passed": all(x in gfx for x in ("cp 6", "cp 8", "zx48_gfx_border:"))},
        {"name": "canonical-iy-restored-by-public-gateway", "passed": "ld iy,ROM_IY_ANCHOR" in syscall},
        {"name": "graphics-routines-emitted-once", "passed": syscall.count("EMIT_GRAPHICS_ROUTINES") == 1},
    ]


def _runtime(root: Path, labels: dict[str, int], kernel: bytes) -> None:
    code = bytearray(b"\xf3" + phase1._ld_sp(phase1.USER_STACK))
    # Valid PLOT through the selector dispatcher: (0,0) sets bitmap bit 7.
    code += _setb(0x4000, 0)
    code += phase1._ld_hl(0x0000) + bytes((0x3E, 0x40)) + phase1._call(labels["zx48_syscall_impl"])
    code += phase1._jp_c(FAIL_PC) + _expectb(0x4000, 0x80)
    # Invalid Y must fail before any display mutation.
    code += _setb(0x4000, 0x5A)
    code += phase1._ld_hl(0x00C0) + bytes((0x3E, 0x40)) + phase1._call(labels["zx48_syscall_impl"])
    code += _jp_nc(FAIL_PC) + _expectb(0x4000, 0x5A)
    # POINT returns exactly H=0,L=1 and is read-only.
    code += _setb(0x4000, 0x80)
    code += phase1._ld_hl(0x0000) + bytes((0x3E, 0x45)) + phase1._call(labels["zx48_syscall_impl"])
    code += phase1._jp_c(FAIL_PC) + b"\x7c\xb7" + phase1._jp_nz(FAIL_PC)
    code += b"\x7d\xfe\x01" + phase1._jp_nz(FAIL_PC) + _expectb(0x4000, 0x80)
    # ATTR exact selector/value register contract and fail-closed bad selector.
    code += phase1._ld_hl(0x0003) + bytes((0x3E, 0x43)) + phase1._call(labels["zx48_syscall_impl"])
    code += phase1._jp_c(FAIL_PC) + _expectb(labels["gfx_attr_state"], 3)
    code += phase1._ld_hl(0x0600) + bytes((0x3E, 0x43)) + phase1._call(labels["zx48_syscall_impl"])
    code += _jp_nc(FAIL_PC) + _expectb(labels["gfx_attr_state"], 3)
    # DRAW validates a complete four-byte readable record before mutation.
    code += phase1._ld_hl(0x5AFE) + bytes((0x3E, 0x41)) + phase1._call(labels["zx48_syscall_impl"])
    code += _jp_nc(FAIL_PC)
    # Valid DRAW record and radius-zero CIRCLE record both dispatch cleanly.
    for off, value in enumerate((1, 1, 3, 1)):
        code += _setb(DATA + off, value)
    code += phase1._ld_hl(DATA) + bytes((0x3E, 0x41)) + phase1._call(labels["zx48_syscall_impl"])
    code += phase1._jp_c(FAIL_PC)
    for off, value in enumerate((10, 10, 0)):
        code += _setb(DATA + 8 + off, value)
    code += phase1._ld_hl(DATA + 8) + bytes((0x3E, 0x42)) + phase1._call(labels["zx48_syscall_impl"])
    code += phase1._jp_c(FAIL_PC)
    # BORDER validates H and color; invalid H must not succeed.
    code += phase1._ld_hl(0x0100) + bytes((0x3E, 0x44)) + phase1._call(labels["zx48_syscall_impl"])
    code += _jp_nc(FAIL_PC)
    code += phase1._jp(PASS_PC)
    run_sna(root, bytes(code), patch=phase1._kernel_patch(kernel))


def dispatch(
    root: Path,
    action: str,
    step: str,
    *,
    sha256_file: Callable[[Path], str],
    run_command: Callable[..., Any],
    require_project_tool: Callable[[Path, str | Path], Path],
):
    if step != "P7.01":
        raise P701Error(f"unsupported {step} {action}")
    assertions = _source_contract(root)
    failed = [x["name"] for x in assertions if x.get("passed") is not True]
    require(not failed, f"P7.01 static contract failure: {failed}")
    command, kernel, listing = phase1._assemble_kernel(root, run_command, require_project_tool)
    commands = [command]
    labels = phase1._labels(listing, ("zx48_syscall_impl", "gfx_attr_state"))
    if action == "test":
        _runtime(root, labels, kernel.read_bytes())
        assertions.extend([
            {"name": "fuse-six-selector-dispatch-smoke-pass", "passed": True},
            {"name": "bad-user-parameters-before-screen-mutation", "passed": True},
            {"name": "plot-point-register-result-contract-runtime", "passed": True},
        ])
    hashes = {
        "docs/01-ZX-UX-ARCHITECTURE-REV16.md": sha256_file(root / "docs/01-ZX-UX-ARCHITECTURE-REV16.md"),
        "docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md": sha256_file(root / "docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md"),
        "v1/include/zx48ux.inc": sha256_file(root / "v1/include/zx48ux.inc"),
        "v1/src/kernel/graphics.asm": sha256_file(root / "v1/src/kernel/graphics.asm"),
        "v1/src/kernel/syscall.asm": sha256_file(root / "v1/src/kernel/syscall.asm"),
        "v1/build/kernel.bin": sha256_file(kernel),
        "v1/tools-host/test-driver/phase7_graphics_abi.py": sha256_file(root / "v1/tools-host/test-driver/phase7_graphics_abi.py"),
        "v1/tools-host/test-driver/run.py": sha256_file(root / "v1/tools-host/test-driver/run.py"),
    }
    return commands, hashes, assertions
