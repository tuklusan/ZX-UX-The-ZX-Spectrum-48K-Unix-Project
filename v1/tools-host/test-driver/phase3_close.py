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
import phase3_tty

DECODER_PTR = 0xA100


class Phase3CloseError(DriverError):
    """Raised when the P3.05 final-reference close contract regresses."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Phase3CloseError(message)


def _word(value: int) -> bytes:
    return bytes((value & 0xFF, (value >> 8) & 0xFF))


def _jp_nc(address: int) -> bytes:
    return b"\xD2" + _word(address)


def _load_byte(address: int) -> bytes:
    return b"\x3A" + _word(address)


def _load_word(address: int) -> bytes:
    return b"\x2A" + _word(address)


def _store_byte(address: int, value: int) -> bytes:
    return bytes((0x3E, value & 0xFF, 0x32)) + _word(address)


def _source_contract(root: Path) -> list[dict[str, object]]:
    handles = (root / "v1/src/kernel/handles.asm").read_text(encoding="utf-8")
    syscall = (root / "v1/src/kernel/syscall.asm").read_text(encoding="utf-8")
    return [
        {"name": "close-validates-h-zero-before-handle-drop", "passed": "zx48_sys_close:\n    ld hl,(syscall_arg_hl)\n    ld a,h\n    or a\n    jp nz,zx48_sys_invalid" in syscall},
        {"name": "close-clears-process-slot-before-description-release", "passed": "ld (hl),HANDLE_FREE\n    call zx48_od_release" in handles},
        {"name": "nonfinal-release-preserves-description", "passed": "dec a\n    ld (ix+OD_REFS_O),a\n    ret nz" in handles},
        {"name": "final-release-frees-packed-reader-state", "passed": all(token in handles for token in (
            "PACKED_READER_STATE_SIZE  EQU 272",
            "ld l,(ix+OD_AUX_O)",
            "ld h,(ix+OD_AUX_O+1)",
            "ld bc,PACKED_READER_STATE_SIZE",
            "call zx48_free",
        ))},
        {"name": "final-release-clears-complete-description", "passed": "ld b,OD_COMPACT_SIZE" in handles and "zx48_od_release_clear:" in handles},
        {"name": "final-pipe-release-delegates-endpoint-close", "passed": "jp zx48_pipe_endpoint_closed" in handles},
        {"name": "close-all-visits-exact-eight-handle-numbers", "passed": "cp MAX_HANDLES_PER_PROCESS\n    jr c,zx48_handles_close_all_loop" in handles},
    ]


def _target_test(root: Path, s: dict[str, int], kernel: bytes) -> None:
    code = bytearray(b"\xF3" + phase1._ld_sp(0xBFC0))
    code += phase1._call(s["zx48_memory_init"])
    code += phase1._call(s["zx48_process_init"])
    code += phase1._call(s["zx48_handles_init"])
    code += phase1._call(s["zx48_process_prepare_pid1"])
    code += _store_byte(s["current_pid"], 1)

    code += b"\x01" + _word(s["PACKED_READER_STATE_SIZE"])
    code += bytes((0x3E, s["ALLOC_ANY"]))
    code += phase1._call(s["zx48_alloc"]) + phase1._jp_c(FAIL_PC)
    code += b"\x22" + _word(DECODER_PTR)
    code += _load_word(s["memory_live_allocations"]) + phase1._ld_de(1) + b"\xB7\xED\x52" + phase1._jp_nz(FAIL_PC)

    code += bytes((0x06, s["OD_KIND_OBJECT"], 0x0E, s["O_READ"], 0x16, 0))
    code += phase1._call(s["zx48_od_create"]) + phase1._jp_c(FAIL_PC) + b"\xB7" + phase1._jp_nz(FAIL_PC)
    code += b"\x4F" + _load_word(DECODER_PTR)
    code += bytes((0xDD, 0x75, s["OD_AUX_O"] & 0xFF, 0xDD, 0x74, (s["OD_AUX_O"] + 1) & 0xFF))
    code += b"\xAF" + phase1._call(s["zx48_handle_install"]) + phase1._jp_c(FAIL_PC) + b"\xB7" + phase1._jp_nz(FAIL_PC)

    # H must be zero. A malformed H must not consume the only reference.
    phase3_tty._call_sys(code, s, s["SYS_CLOSE"], 0x0100, 0, 0)
    code += _jp_nc(FAIL_PC) + b"\xFE" + bytes((s["E_INVAL"],)) + phase1._jp_nz(FAIL_PC)
    code += _load_byte(s["process_table"] + s["PROC_DESC_SIZE"] + s["PROC_HANDLES"]) + b"\xB7" + phase1._jp_nz(FAIL_PC)
    code += _load_byte(s["open_description_table"] + s["OD_REFS_O"]) + b"\xFE\x01" + phase1._jp_nz(FAIL_PC)

    # DUP shares the same description. Closing one handle must preserve the other.
    code += b"\x06\x00\x0E\x01" + phase1._call(s["zx48_handle_dup"])
    code += phase1._jp_c(FAIL_PC) + b"\xFE\x01" + phase1._jp_nz(FAIL_PC)
    code += _load_byte(s["open_description_table"] + s["OD_REFS_O"]) + b"\xFE\x02" + phase1._jp_nz(FAIL_PC)
    code += b"\xAF" + phase1._call(s["zx48_handle_close"]) + phase1._jp_c(FAIL_PC)
    code += _load_byte(s["process_table"] + s["PROC_DESC_SIZE"] + s["PROC_HANDLES"]) + b"\xFE\xFF" + phase1._jp_nz(FAIL_PC)
    code += _load_byte(s["process_table"] + s["PROC_DESC_SIZE"] + s["PROC_HANDLES"] + 1) + b"\xB7" + phase1._jp_nz(FAIL_PC)
    code += _load_byte(s["open_description_table"] + s["OD_REFS_O"]) + b"\xFE\x01" + phase1._jp_nz(FAIL_PC)
    code += _load_word(s["open_description_table"] + s["OD_AUX_O"]) + b"\xED\x5B" + _word(DECODER_PTR) + b"\xB7\xED\x52" + phase1._jp_nz(FAIL_PC)
    code += _load_word(s["memory_live_allocations"]) + phase1._ld_de(1) + b"\xB7\xED\x52" + phase1._jp_nz(FAIL_PC)

    # Final reference releases decoder allocation, clears OD, and frees the slot.
    code += b"\x3E\x01" + phase1._call(s["zx48_handle_close"]) + phase1._jp_c(FAIL_PC)
    code += _load_byte(s["process_table"] + s["PROC_DESC_SIZE"] + s["PROC_HANDLES"] + 1) + b"\xFE\xFF" + phase1._jp_nz(FAIL_PC)
    code += _load_byte(s["open_description_table"] + s["OD_KIND_O"]) + b"\xB7" + phase1._jp_nz(FAIL_PC)
    code += _load_word(s["open_description_table"] + s["OD_AUX_O"]) + b"\x7C\xB5" + phase1._jp_nz(FAIL_PC)
    code += _load_word(s["memory_live_allocations"]) + b"\x7C\xB5" + phase1._jp_nz(FAIL_PC)

    # Double-close is an invalid handle and cannot mutate allocator state.
    code += b"\x3E\x01" + phase1._call(s["zx48_handle_close"])
    code += _jp_nc(FAIL_PC) + b"\xFE" + bytes((s["E_NOENT"],)) + phase1._jp_nz(FAIL_PC)
    code += _load_word(s["memory_live_allocations"]) + b"\x7C\xB5" + phase1._jp_nz(FAIL_PC)

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
    if step != "P3.05":
        raise DriverError(f"Phase-3 close step is not registered: {step}")

    assertions = _source_contract(root)
    failed = [item["name"] for item in assertions if item["passed"] is not True]
    require(not failed, f"static P3.05 contract failures: {failed}")

    result, kernel, listing = phase1._assemble_kernel(root, run_command, require_project_tool)
    commands = [result]
    symbols = phase3_open_descriptions._symbols(
        listing.with_suffix(".sym"),
        (
            "zx48_memory_init", "zx48_alloc", "zx48_process_init", "zx48_handles_init",
            "zx48_process_prepare_pid1", "zx48_od_create", "zx48_handle_install",
            "zx48_handle_dup", "zx48_handle_close", "zx48_syscall_impl",
            "memory_live_allocations", "process_table", "current_pid", "open_description_table",
            "PROC_DESC_SIZE", "PROC_HANDLES", "OD_KIND_O", "OD_REFS_O", "OD_AUX_O",
            "OD_KIND_OBJECT", "O_READ", "ALLOC_ANY", "PACKED_READER_STATE_SIZE",
            "SYS_CLOSE", "E_INVAL", "E_NOENT",
        ),
    )
    require(symbols["PACKED_READER_STATE_SIZE"] == 272, "packed-reader state size drift")

    if action == "test":
        _target_test(root, symbols, kernel.read_bytes())
        assertions.extend([
            {"name": "close-h-high-byte-negative-is-pre-side-effect", "passed": True},
            {"name": "dup-close-one-preserves-shared-description", "passed": True},
            {"name": "final-close-frees-packed-reader-state", "passed": True},
            {"name": "final-close-clears-description-and-handle", "passed": True},
            {"name": "double-close-returns-enoent-without-mutation", "passed": True},
        ])

    hashes = {
        "v1/build/kernel.bin": sha256_file(kernel),
        "v1/src/kernel/handles.asm": sha256_file(root / "v1/src/kernel/handles.asm"),
        "v1/src/kernel/syscall.asm": sha256_file(root / "v1/src/kernel/syscall.asm"),
        "v1/tools-host/test-driver/phase3_close.py": sha256_file(root / "v1/tools-host/test-driver/phase3_close.py"),
        "v1/tools-host/test-driver/run.py": sha256_file(root / "v1/tools-host/test-driver/run.py"),
        "v1/dist/certification/P3.04.test.json": sha256_file(root / "v1/dist/certification/P3.04.test.json"),
    }
    return commands, hashes, assertions
