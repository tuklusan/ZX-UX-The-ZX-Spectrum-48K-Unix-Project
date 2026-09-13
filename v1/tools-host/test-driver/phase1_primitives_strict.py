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
import phase1_primitives as base

SHIM = 0xA800
MID_REPEAT_MARK = 0xA820


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


def _store_byte(address: int, value: int) -> bytes:
    return bytes((0x3E, value & 0xFF, 0x32)) + _word(address)


def _expect_byte(address: int, value: int) -> bytes:
    return b"\x3A" + _word(address) + bytes((0xFE, value & 0xFF)) + _jp_nz(FAIL_PC)


def _im2_observer(interrupt: int) -> bytes:
    # Preserve AF, leave BC/DE/HL untouched, and mark only a genuine mid-LDIR
    # observation: BC is neither its initial 0x1000 nor terminal zero value.
    return (
        b"\xF5"              # push af
        b"\x78\xB1"         # ld a,b / or c
        b"\x28\x0E"         # jr z,no_mid
        b"\x78\xFE\x10"    # ld a,b / cp 0x10
        b"\x20\x04"         # jr nz,mid
        b"\x79\xB7"         # ld a,c / or a
        b"\x28\x05"         # jr z,no_mid (exactly 0x1000)
        b"\x3E\x01\x32" + _word(MID_REPEAT_MARK) +
        b"\xF1" +            # no_mid: pop af
        _jp(interrupt)
    )


def _strict_interrupt_fixture(root: Path, labels: dict[str, int], kernel: bytes) -> None:
    source = bytes((i * 17 + (i >> 4) + 0x31) & 0xFF for i in range(base.LONG_COUNT))
    extras = (
        (base.LONG_SRC - 1, b"\x91" + source + b"\x92"),
        (base.LONG_DST - 1, b"\xA1" + b"\xCC" * base.LONG_COUNT + b"\xA2"),
        (labels["kernel_im2_trampoline"], _jp(SHIM)),
        (SHIM, _im2_observer(labels["zx48_interrupt"])),
        (MID_REPEAT_MARK, b"\x00"),
    )
    code = bytearray(b"\xF3" + phase1._ld_sp(phase1.USER_STACK))
    code += _call(labels["zx48_kernel_stack_init"]) + _call(labels["zx48_im2_init"])
    for offset in range(4):
        code += _store_byte(labels["kernel_ticks"] + offset, 0)
    code += _store_byte(MID_REPEAT_MARK, 0)
    code += phase1._ld_hl(base.LONG_SRC) + phase1._ld_de(base.LONG_DST) + base._ld_bc(base.LONG_COUNT)
    code += b"\xFB" + _call(labels["zx48_memcpy"]) + b"\xF3"
    code += _expect_byte(MID_REPEAT_MARK, 1)
    code += b"\x3A" + _word(labels["kernel_ticks"]) + b"\x4F"
    code += b"\x3A" + _word(labels["kernel_ticks"] + 1) + b"\xB1" + _jp_z(FAIL_PC)
    base._compare_regions(code, base.LONG_SRC, base.LONG_DST, base.LONG_COUNT)
    code += _expect_byte(base.LONG_SRC - 1, 0x91) + _expect_byte(base.LONG_SRC + base.LONG_COUNT, 0x92)
    code += _expect_byte(base.LONG_DST - 1, 0xA1) + _expect_byte(base.LONG_DST + base.LONG_COUNT, 0xA2)
    code += _jp(PASS_PC)
    run_sna(root, bytes(code), patch=base._patch(kernel, extras), timeout=20.0)


def _base_dispatch_with_named_fixtures(
    root: Path,
    action: str,
    step: str,
    *,
    sha256_file: Callable[[Path], str],
    run_command: Callable[..., Any],
    require_project_tool: Callable[[Path, str | Path], Path],
):
    """Run the base suite while preserving the exact failing fixture in diagnostics."""
    fixture_names = iter((
        "copy-move",
        "search-single-step",
        "strings",
        "udg",
        "pipe-ring-wrap",
        "interrupt-restart",
        "wrong-overlap-negative",
    ))
    original_run_sna = base.run_sna

    def named_run_sna(*args: Any, **kwargs: Any):  # noqa: ANN202
        name = next(fixture_names, "unexpected-extra")
        try:
            return original_run_sna(*args, **kwargs)
        except DriverError as exc:
            raise base.PrimitiveContractError(f"P1.40 {name} fixture failed: {exc}") from exc

    base.run_sna = named_run_sna
    try:
        return base.dispatch(
            root,
            action,
            step,
            sha256_file=sha256_file,
            run_command=run_command,
            require_project_tool=require_project_tool,
        )
    finally:
        base.run_sna = original_run_sna


def dispatch(
    root: Path,
    action: str,
    step: str,
    *,
    sha256_file: Callable[[Path], str],
    run_command: Callable[..., Any],
    require_project_tool: Callable[[Path, str | Path], Path],
):
    commands, hashes, assertions = _base_dispatch_with_named_fixtures(
        root,
        action,
        step,
        sha256_file=sha256_file,
        run_command=run_command,
        require_project_tool=require_project_tool,
    )
    this_file = root / "v1/tools-host/test-driver/phase1_primitives_strict.py"
    hashes[str(this_file.relative_to(root))] = sha256_file(this_file)
    if action == "test":
        command, kernel_path, listing = phase1._assemble_kernel(root, run_command, require_project_tool)
        commands.append(command)
        labels = phase1._labels(listing, (
            "zx48_memcpy",
            "zx48_kernel_stack_init",
            "zx48_im2_init",
            "kernel_im2_trampoline",
            "zx48_interrupt",
            "kernel_ticks",
        ))
        try:
            _strict_interrupt_fixture(root, labels, kernel_path.read_bytes())
        except DriverError as exc:
            raise base.PrimitiveContractError(f"P1.40 strict-mid-ldir fixture failed: {exc}") from exc
        assertions.append({
            "name": "accepted-im2-interrupt-observed-with-mid-ldir-bc",
            "passed": True,
            "initial_bc": base.LONG_COUNT,
        })
    return commands, hashes, assertions
