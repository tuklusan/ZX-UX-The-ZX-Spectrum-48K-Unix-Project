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

DUP_REC = 0xA100
DECODER_PTR = 0xA110


class Phase3DupError(DriverError):
    """Raised when the P3.06 shared-description DUP1 contract regresses."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Phase3DupError(message)


def _word(value: int) -> bytes:
    return bytes((value & 0xFF, (value >> 8) & 0xFF))


def _jp_nc(address: int) -> bytes:
    return b"\xD2" + _word(address)


def _store_byte(address: int, value: int) -> bytes:
    return bytes((0x3E, value & 0xFF, 0x32)) + _word(address)


def _load_byte(address: int) -> bytes:
    return b"\x3A" + _word(address)


def _load_word(address: int) -> bytes:
    return b"\x2A" + _word(address)


def _store_dup(code: bytearray, source: int, destination: int) -> None:
    code += _store_byte(DUP_REC, source)
    code += _store_byte(DUP_REC + 1, destination)


def _call_dup(code: bytearray, s: dict[str, int]) -> None:
    phase3_tty._call_sys(code, s, s["SYS_DUP"], DUP_REC, 0, 0)


def _source_contract(root: Path) -> list[dict[str, object]]:
    handles = (root / "v1/src/kernel/handles.asm").read_text(encoding="utf-8")
    syscall = (root / "v1/src/kernel/syscall.asm").read_text(encoding="utf-8")
    dup = handles[handles.index("zx48_handle_dup:"):handles.index("; Close every live handle")]
    sysdup = syscall[syscall.index("zx48_sys_dup:"):syscall.index("; HL -> IOCTL1")]
    return [
        {"name": "dup1-record-is-exact-two-byte-source-destination", "passed": "ld bc,2" in sysdup and "ld b,(hl)" in sysdup and "ld c,(hl)" in sysdup},
        {"name": "source-must-be-live-handle", "passed": "call zx48_handle_lookup" in dup},
        {"name": "destination-ff-selects-auto-slot", "passed": "cp HANDLE_FREE" in dup and "call zx48_handle_install" in dup},
        {"name": "source-equals-explicit-destination-is-noop", "passed": "ld a,(handle_dup_source)" in dup and "cp b" in dup and "ld a,b" in dup},
        {"name": "dup-retains-existing-description", "passed": "call zx48_od_retain" in dup},
        {"name": "dup-never-allocates-description", "passed": "zx48_od_create" not in dup},
        {"name": "failed-install-rolls-back-retain", "passed": "call zx48_od_release" in dup},
        {"name": "sysdup-rejects-source-outside-0-through-7", "passed": "cp MAX_HANDLES_PER_PROCESS" in sysdup},
        {"name": "sysdup-rejects-explicit-destination-outside-0-through-7", "passed": sysdup.count("cp MAX_HANDLES_PER_PROCESS") >= 2},
    ]


def _setup(code: bytearray, s: dict[str, int]) -> None:
    code += phase1._call(s["zx48_memory_init"])
    code += phase1._call(s["zx48_process_init"])
    code += phase1._call(s["zx48_handles_init"])
    code += phase1._call(s["zx48_process_prepare_pid1"])
    code += _store_byte(s["current_pid"], 1)

    code += b"\x01" + _word(s["PACKED_READER_STATE_SIZE"])
    code += bytes((0x3E, s["ALLOC_ANY"]))
    code += phase1._call(s["zx48_alloc"]) + phase1._jp_c(FAIL_PC)
    code += b"\x22" + _word(DECODER_PTR)

    code += bytes((0x06, s["OD_KIND_OBJECT"], 0x0E, s["O_READ"], 0x16, 0))
    code += phase1._call(s["zx48_od_create"]) + phase1._jp_c(FAIL_PC)
    code += b"\xB7" + phase1._jp_nz(FAIL_PC)
    code += b"\x4F"
    code += _load_word(DECODER_PTR)
    code += bytes((0xDD, 0x75, s["OD_AUX_O"] & 0xFF, 0xDD, 0x74, (s["OD_AUX_O"] + 1) & 0xFF))
    code += phase1._ld_hl(0x3456)
    code += bytes((0xDD, 0x75, s["OD_OFFSET_O"] & 0xFF, 0xDD, 0x74, (s["OD_OFFSET_O"] + 1) & 0xFF))
    code += b"\xAF" + phase1._call(s["zx48_handle_install"]) + phase1._jp_c(FAIL_PC)
    code += b"\xB7" + phase1._jp_nz(FAIL_PC)


def _target_test(root: Path, s: dict[str, int], kernel: bytes) -> None:
    code = bytearray(b"\xF3" + phase1._ld_sp(0xBFC0))
    _setup(code, s)
    slot_base = s["process_table"] + s["PROC_DESC_SIZE"] + s["PROC_HANDLES"]
    od0 = s["open_description_table"]

    # source==explicit destination succeeds as a strict no-op.
    _store_dup(code, 0, 0)
    _call_dup(code, s)
    code += phase1._jp_c(FAIL_PC) + b"\x7C\xB5" + phase1._jp_nz(FAIL_PC)
    code += _load_byte(od0 + s["OD_REFS_O"]) + b"\xFE\x01" + phase1._jp_nz(FAIL_PC)

    # FF selects the lowest free slot and shares the exact description.
    _store_dup(code, 0, 0xFF)
    _call_dup(code, s)
    code += phase1._jp_c(FAIL_PC) + phase1._ld_de(1) + b"\xB7\xED\x52" + phase1._jp_nz(FAIL_PC)
    code += _load_byte(slot_base + 1) + b"\xB7" + phase1._jp_nz(FAIL_PC)
    code += _load_byte(od0 + s["OD_REFS_O"]) + b"\xFE\x02" + phase1._jp_nz(FAIL_PC)
    code += _load_byte(od0 + s["OD_RECORD_SIZE"] + s["OD_KIND_O"]) + b"\xB7" + phase1._jp_nz(FAIL_PC)
    code += _load_word(od0 + s["OD_OFFSET_O"]) + phase1._ld_de(0x3456) + b"\xB7\xED\x52" + phase1._jp_nz(FAIL_PC)
    code += _load_word(od0 + s["OD_AUX_O"]) + b"\xED\x5B" + _word(DECODER_PTR) + b"\xB7\xED\x52" + phase1._jp_nz(FAIL_PC)
    code += _load_word(s["memory_live_allocations"]) + phase1._ld_de(1) + b"\xB7\xED\x52" + phase1._jp_nz(FAIL_PC)

    # Install a distinct occupied destination and prove no dup2 close/replace.
    code += bytes((0x06, s["OD_KIND_NULL"], 0x0E, s["O_READ"], 0x16, 0))
    code += phase1._call(s["zx48_od_create"]) + phase1._jp_c(FAIL_PC)
    code += b"\xFE\x01" + phase1._jp_nz(FAIL_PC) + b"\x4F\x3E\x02"
    code += phase1._call(s["zx48_handle_install"]) + phase1._jp_c(FAIL_PC)
    code += b"\xFE\x02" + phase1._jp_nz(FAIL_PC)
    _store_dup(code, 0, 2)
    _call_dup(code, s)
    code += _jp_nc(FAIL_PC) + b"\xFE" + bytes((s["E_BUSY"],)) + phase1._jp_nz(FAIL_PC)
    code += _load_byte(slot_base + 2) + b"\xFE\x01" + phase1._jp_nz(FAIL_PC)
    code += _load_byte(od0 + s["OD_REFS_O"]) + b"\xFE\x02" + phase1._jp_nz(FAIL_PC)
    code += _load_byte(od0 + s["OD_RECORD_SIZE"] + s["OD_REFS_O"]) + b"\xFE\x01" + phase1._jp_nz(FAIL_PC)

    # Dead source is rejected before any retain/install side effect.
    _store_dup(code, 7, 0xFF)
    _call_dup(code, s)
    code += _jp_nc(FAIL_PC) + b"\xFE" + bytes((s["E_NOENT"],)) + phase1._jp_nz(FAIL_PC)
    code += _load_byte(od0 + s["OD_REFS_O"]) + b"\xFE\x02" + phase1._jp_nz(FAIL_PC)

    # Fill handles 3..7 with distinct descriptions.
    for handle in range(3, 8):
        expected_od = handle - 1
        code += bytes((0x06, s["OD_KIND_NULL"], 0x0E, s["O_READ"], 0x16, handle))
        code += phase1._call(s["zx48_od_create"]) + phase1._jp_c(FAIL_PC)
        code += bytes((0xFE, expected_od)) + phase1._jp_nz(FAIL_PC)
        code += b"\x4F" + bytes((0x3E, handle))
        code += phase1._call(s["zx48_handle_install"]) + phase1._jp_c(FAIL_PC)
        code += bytes((0xFE, handle)) + phase1._jp_nz(FAIL_PC)

    # No free handle: E_NOSPC and the temporary retain is fully rolled back.
    _store_dup(code, 0, 0xFF)
    _call_dup(code, s)
    code += _jp_nc(FAIL_PC) + b"\xFE" + bytes((s["E_NOSPC"],)) + phase1._jp_nz(FAIL_PC)
    code += _load_byte(od0 + s["OD_REFS_O"]) + b"\xFE\x02" + phase1._jp_nz(FAIL_PC)
    for handle in range(2, 8):
        expected_od = handle - 1
        code += _load_byte(slot_base + handle) + bytes((0xFE, expected_od)) + phase1._jp_nz(FAIL_PC)

    # Closing one duplicate preserves shared state; final close destroys it and frees decoder state.
    phase3_tty._call_sys(code, s, s["SYS_CLOSE"], 0, 0, 0)
    code += phase1._jp_c(FAIL_PC)
    code += _load_byte(od0 + s["OD_REFS_O"]) + b"\xFE\x01" + phase1._jp_nz(FAIL_PC)
    code += _load_word(od0 + s["OD_OFFSET_O"]) + phase1._ld_de(0x3456) + b"\xB7\xED\x52" + phase1._jp_nz(FAIL_PC)
    code += _load_word(od0 + s["OD_AUX_O"]) + b"\xED\x5B" + _word(DECODER_PTR) + b"\xB7\xED\x52" + phase1._jp_nz(FAIL_PC)
    code += _load_word(s["memory_live_allocations"]) + phase1._ld_de(1) + b"\xB7\xED\x52" + phase1._jp_nz(FAIL_PC)

    phase3_tty._call_sys(code, s, s["SYS_CLOSE"], 1, 0, 0)
    code += phase1._jp_c(FAIL_PC)
    code += _load_byte(od0 + s["OD_KIND_O"]) + b"\xB7" + phase1._jp_nz(FAIL_PC)
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
    if step != "P3.06":
        raise DriverError(f"Phase-3 dup step is not registered: {step}")

    assertions = _source_contract(root)
    failed = [item["name"] for item in assertions if item["passed"] is not True]
    require(not failed, f"static P3.06 contract failures: {failed}")

    result, kernel, listing = phase1._assemble_kernel(root, run_command, require_project_tool)
    commands = [result]
    symbols = phase3_open_descriptions._symbols(
        listing.with_suffix(".sym"),
        (
            "zx48_memory_init", "zx48_alloc", "zx48_process_init", "zx48_handles_init",
            "zx48_process_prepare_pid1", "zx48_od_create", "zx48_handle_install",
            "zx48_syscall_impl", "memory_live_allocations", "process_table", "current_pid",
            "open_description_table", "PROC_DESC_SIZE", "PROC_HANDLES", "OD_RECORD_SIZE",
            "OD_KIND_O", "OD_REFS_O", "OD_OFFSET_O", "OD_AUX_O", "OD_KIND_OBJECT",
            "OD_KIND_NULL", "O_READ", "ALLOC_ANY", "PACKED_READER_STATE_SIZE",
            "SYS_DUP", "SYS_CLOSE", "E_BUSY", "E_NOENT", "E_NOSPC",
        ),
    )
    require(symbols["PACKED_READER_STATE_SIZE"] == 272, "packed-reader state size drift")

    if action == "test":
        _target_test(root, symbols, kernel.read_bytes())
        assertions.extend([
            {"name": "source-self-explicit-destination-noop", "passed": True},
            {"name": "destination-ff-chooses-lowest-free-slot", "passed": True},
            {"name": "dup-shares-offset-and-decoder-state", "passed": True},
            {"name": "dup-does-not-allocate-open-description", "passed": True},
            {"name": "occupied-different-destination-ebusy-atomic", "passed": True},
            {"name": "dead-source-enoent-atomic", "passed": True},
            {"name": "no-free-handle-enospc-retain-rollback", "passed": True},
            {"name": "duplicate-final-close-lifetime-exact", "passed": True},
        ])

    hashes = {
        "v1/build/kernel.bin": sha256_file(kernel),
        "v1/src/kernel/handles.asm": sha256_file(root / "v1/src/kernel/handles.asm"),
        "v1/src/kernel/syscall.asm": sha256_file(root / "v1/src/kernel/syscall.asm"),
        "v1/tools-host/test-driver/phase3_dup.py": sha256_file(root / "v1/tools-host/test-driver/phase3_dup.py"),
        "v1/tools-host/test-driver/run.py": sha256_file(root / "v1/tools-host/test-driver/run.py"),
        "v1/dist/certification/P3.05.test.json": sha256_file(root / "v1/dist/certification/P3.05.test.json"),
    }
    return commands, hashes, assertions
