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

RESULT = 0xA100


class Phase3PipeCreateError(DriverError):
    """Raised when the P3.08 atomic pipe-allocation contract regresses."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Phase3PipeCreateError(message)


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


def _assert_word(code: bytearray, address: int, expected: int) -> None:
    code += _load_word(address) + phase1._ld_de(expected) + b"\xB7\xED\x52" + phase1._jp_nz(FAIL_PC)


def _assert_byte(code: bytearray, address: int, expected: int) -> None:
    code += _load_byte(address) + bytes((0xFE, expected & 0xFF)) + phase1._jp_nz(FAIL_PC)


def _source_contract(root: Path) -> list[dict[str, object]]:
    inc = (root / "v1/include/zx48ux.inc").read_text(encoding="utf-8")
    pipe = (root / "v1/src/kernel/pipe.asm").read_text(encoding="utf-8")
    syscall = (root / "v1/src/kernel/syscall.asm").read_text(encoding="utf-8")
    create = pipe[pipe.index("zx48_pipe_create:"):pipe.index("; A=pipe slot, HL=destination")]
    preflight = pipe[pipe.index("zx48_pipe_preflight:"):pipe.index("; HL points to two result bytes")]
    return [
        {"name": "pipe-count-exact-four", "passed": "PIPE_COUNT               EQU $04" in inc},
        {"name": "normal-buffer-exact-256", "passed": "PIPE_BUFFER_SIZE         EQU $0100" in inc},
        {"name": "single-fallback-exact-128", "passed": "PIPE_FALLBACK_SIZE         EQU 128" in pipe and create.count("PIPE_FALLBACK_SIZE") == 1},
        {"name": "pipe-record-has-buffer-indices-count-capacity-endpoint-counts", "passed": all(token in pipe for token in (
            "PIPE_PTR_O                 EQU 0",
            "PIPE_RPOS_O                EQU 2",
            "PIPE_WPOS_O                EQU 3",
            "PIPE_COUNT_O               EQU 4",
            "PIPE_CAPACITY_O            EQU 6",
            "PIPE_READERS_O             EQU 8",
            "PIPE_WRITERS_O             EQU 9",
        ))},
        {"name": "waiter-bookkeeping-is-linked-by-pipe-slot", "passed": all(token in pipe for token in (
            "ld (ix+PROC_WAIT_OBJECT),c",
            "ld (ix+PROC_STATE),d",
            "zx48_pipe_waiter_scan:",
            "ld a,(ix+PROC_WAIT_OBJECT)",
        ))},
        {"name": "preflight-requires-two-process-handles", "passed": "cp 2\n    jr c,zx48_pipe_nospc" in preflight},
        {"name": "preflight-requires-two-open-descriptions", "passed": preflight.count("cp 2\n    jr c,zx48_pipe_nospc") >= 2},
        {"name": "preflight-reserves-one-free-pipe-slot", "passed": "zx48_pipe_slot_scan:" in preflight and "jr z,zx48_pipe_preflight_ok" in preflight},
        {"name": "buffer-policy-fast-required-normal-and-fallback", "passed": create.count("ld a,ALLOC_FAST_REQUIRED") == 2},
        {"name": "two-endpoint-descriptions-created-before-publication", "passed": create.index("ld b,OD_KIND_PIPE_READ") < create.index("ld b,OD_KIND_PIPE_WRITE") < create.index("ld hl,(pipe_result_ptr)")},
        {"name": "two-handles-installed-before-publication", "passed": create.count("call zx48_handle_install") == 2 and create.rindex("call zx48_handle_install") < create.index("ld hl,(pipe_result_ptr)")},
        {"name": "result-slots-written-only-at-commit", "passed": create.count("ld (hl),a") == 2 and create.index("ld hl,(pipe_result_ptr)") > create.rindex("call zx48_handle_install")},
        {"name": "rollback-paths-release-handles-descriptions-buffer", "passed": all(token in create for token in (
            "zx48_pipe_rollback_read_handle:",
            "call zx48_handle_close",
            "zx48_pipe_rollback_write_od:",
            "call zx48_od_release",
            "zx48_pipe_rollback_buffer:",
            "call zx48_free",
        ))},
        {"name": "sys-pipe-validates-two-byte-result-range-first", "passed": "zx48_sys_pipe:\n    ld hl,(syscall_arg_hl)\n    ld bc,2\n    call zx48_user_range_validate\n    ret c" in syscall},
    ]


def _setup(code: bytearray, s: dict[str, int]) -> None:
    code += b"\xF3" + phase1._ld_sp(0xBFC0)
    code += phase1._call(s["zx48_memory_init"])
    code += phase1._call(s["zx48_process_init"])
    code += phase1._call(s["zx48_handles_init"])
    code += phase1._call(s["zx48_pipe_init"])
    code += phase1._call(s["zx48_process_prepare_pid1"])
    code += _store_byte(s["current_pid"], 1)


def _call_pipe(code: bytearray, s: dict[str, int]) -> None:
    phase3_tty._call_sys(code, s, s["SYS_PIPE"], RESULT, 0, 0)


def _poison_result(code: bytearray) -> None:
    code += _store_byte(RESULT, 0xA5) + _store_byte(RESULT + 1, 0x5A)


def _assert_result_poison(code: bytearray) -> None:
    _assert_byte(code, RESULT, 0xA5)
    _assert_byte(code, RESULT + 1, 0x5A)


def _normal_fixture(root: Path, s: dict[str, int], kernel: bytes) -> None:
    code = bytearray()
    _setup(code, s)
    _poison_result(code)
    _call_pipe(code, s)
    code += phase1._jp_c(FAIL_PC) + b"\x7C\xB5" + phase1._jp_nz(FAIL_PC)

    _assert_byte(code, RESULT, 0)
    _assert_byte(code, RESULT + 1, 1)
    slot = s["process_table"] + s["PROC_DESC_SIZE"] + s["PROC_HANDLES"]
    _assert_byte(code, slot + 0, 0)
    _assert_byte(code, slot + 1, 1)

    od0 = s["open_description_table"]
    od1 = od0 + s["OD_RECORD_SIZE"]
    _assert_byte(code, od0 + s["OD_KIND_O"], s["OD_KIND_PIPE_READ"])
    _assert_byte(code, od0 + s["OD_ACCESS_O"], s["O_READ"])
    _assert_byte(code, od0 + s["OD_REFS_O"], 1)
    _assert_byte(code, od0 + s["OD_ID_O"], 0)
    _assert_byte(code, od1 + s["OD_KIND_O"], s["OD_KIND_PIPE_WRITE"])
    _assert_byte(code, od1 + s["OD_ACCESS_O"], s["O_WRITE"])
    _assert_byte(code, od1 + s["OD_REFS_O"], 1)
    _assert_byte(code, od1 + s["OD_ID_O"], 0)

    pipe = s["pipe_table"]
    expected_ptr = s["FAST_END"] + 1 - s["PIPE_BUFFER_SIZE"]
    _assert_word(code, pipe + s["PIPE_PTR_O"], expected_ptr)
    _assert_byte(code, pipe + s["PIPE_RPOS_O"], 0)
    _assert_byte(code, pipe + s["PIPE_WPOS_O"], 0)
    _assert_word(code, pipe + s["PIPE_COUNT_O"], 0)
    _assert_word(code, pipe + s["PIPE_CAPACITY_O"], s["PIPE_BUFFER_SIZE"])
    _assert_byte(code, pipe + s["PIPE_READERS_O"], 1)
    _assert_byte(code, pipe + s["PIPE_WRITERS_O"], 1)
    _assert_word(code, s["memory_live_allocations"], 1)

    code += phase1._jp(PASS_PC)
    run_sna(root, bytes(code), patch=phase1._kernel_patch(kernel))


def _fallback_fixture(root: Path, s: dict[str, int], kernel: bytes) -> None:
    code = bytearray()
    _setup(code, s)
    fast_size = s["FAST_END"] + 1 - s["FAST_START"]
    prealloc = fast_size - s["PIPE_FALLBACK_SIZE"]
    code += b"\x01" + _word(prealloc) + bytes((0x3E, s["ALLOC_FAST_REQUIRED"]))
    code += phase1._call(s["zx48_alloc"]) + phase1._jp_c(FAIL_PC)
    _poison_result(code)
    _call_pipe(code, s)
    code += phase1._jp_c(FAIL_PC) + b"\x7C\xB5" + phase1._jp_nz(FAIL_PC)
    _assert_word(code, s["pipe_table"] + s["PIPE_PTR_O"], s["FAST_START"])
    _assert_word(code, s["pipe_table"] + s["PIPE_CAPACITY_O"], s["PIPE_FALLBACK_SIZE"])
    _assert_word(code, s["memory_live_allocations"], 2)
    _assert_byte(code, RESULT, 0)
    _assert_byte(code, RESULT + 1, 1)
    code += phase1._jp(PASS_PC)
    run_sna(root, bytes(code), patch=phase1._kernel_patch(kernel))


def _enomem_fixture(root: Path, s: dict[str, int], kernel: bytes) -> None:
    code = bytearray()
    _setup(code, s)
    fast_size = s["FAST_END"] + 1 - s["FAST_START"]
    prealloc = fast_size - 64
    code += b"\x01" + _word(prealloc) + bytes((0x3E, s["ALLOC_FAST_REQUIRED"]))
    code += phase1._call(s["zx48_alloc"]) + phase1._jp_c(FAIL_PC)
    _poison_result(code)
    _call_pipe(code, s)
    code += _jp_nc(FAIL_PC) + b"\xFE" + bytes((s["E_NOMEM"],)) + phase1._jp_nz(FAIL_PC)
    _assert_result_poison(code)
    slot = s["process_table"] + s["PROC_DESC_SIZE"] + s["PROC_HANDLES"]
    _assert_byte(code, slot + 0, s["HANDLE_FREE"])
    _assert_byte(code, slot + 1, s["HANDLE_FREE"])
    _assert_byte(code, s["open_description_table"] + s["OD_KIND_O"], 0)
    _assert_byte(code, s["open_description_table"] + s["OD_RECORD_SIZE"] + s["OD_KIND_O"], 0)
    _assert_word(code, s["pipe_table"] + s["PIPE_PTR_O"], 0)
    _assert_byte(code, s["pipe_table"] + s["PIPE_READERS_O"], 0)
    _assert_byte(code, s["pipe_table"] + s["PIPE_WRITERS_O"], 0)
    _assert_word(code, s["memory_live_allocations"], 1)
    code += phase1._jp(PASS_PC)
    run_sna(root, bytes(code), patch=phase1._kernel_patch(kernel))


def _handle_exhaustion_fixture(root: Path, s: dict[str, int], kernel: bytes) -> None:
    code = bytearray()
    _setup(code, s)
    for handle in range(7):
        code += bytes((0x06, s["OD_KIND_NULL"], 0x0E, s["O_READ"], 0x16, handle))
        code += phase1._call(s["zx48_od_create"]) + phase1._jp_c(FAIL_PC)
        code += bytes((0xFE, handle)) + phase1._jp_nz(FAIL_PC) + b"\x4F" + bytes((0x3E, handle))
        code += phase1._call(s["zx48_handle_install"]) + phase1._jp_c(FAIL_PC)
    _poison_result(code)
    _call_pipe(code, s)
    code += _jp_nc(FAIL_PC) + b"\xFE" + bytes((s["E_NOSPC"],)) + phase1._jp_nz(FAIL_PC)
    _assert_result_poison(code)
    slot = s["process_table"] + s["PROC_DESC_SIZE"] + s["PROC_HANDLES"]
    for handle in range(7):
        _assert_byte(code, slot + handle, handle)
    _assert_byte(code, slot + 7, s["HANDLE_FREE"])
    _assert_byte(code, s["open_description_table"] + 7 * s["OD_RECORD_SIZE"] + s["OD_KIND_O"], 0)
    _assert_word(code, s["memory_live_allocations"], 0)
    _assert_word(code, s["pipe_table"] + s["PIPE_PTR_O"], 0)
    code += phase1._jp(PASS_PC)
    run_sna(root, bytes(code), patch=phase1._kernel_patch(kernel))


def _description_exhaustion_fixture(root: Path, s: dict[str, int], kernel: bytes) -> None:
    code = bytearray()
    _setup(code, s)
    for index in range(s["OPEN_DESCRIPTION_COUNT"] - 1):
        code += bytes((0x06, s["OD_KIND_NULL"], 0x0E, s["O_READ"], 0x16, index & 0xFF))
        code += phase1._call(s["zx48_od_create"]) + phase1._jp_c(FAIL_PC)
        code += bytes((0xFE, index & 0xFF)) + phase1._jp_nz(FAIL_PC)
    _poison_result(code)
    _call_pipe(code, s)
    code += _jp_nc(FAIL_PC) + b"\xFE" + bytes((s["E_NOSPC"],)) + phase1._jp_nz(FAIL_PC)
    _assert_result_poison(code)
    _assert_word(code, s["memory_live_allocations"], 0)
    _assert_word(code, s["pipe_table"] + s["PIPE_PTR_O"], 0)
    _assert_byte(code, s["open_description_table"] + (s["OPEN_DESCRIPTION_COUNT"] - 1) * s["OD_RECORD_SIZE"] + s["OD_KIND_O"], 0)
    code += phase1._jp(PASS_PC)
    run_sna(root, bytes(code), patch=phase1._kernel_patch(kernel))


def _pipe_slot_exhaustion_fixture(root: Path, s: dict[str, int], kernel: bytes) -> None:
    code = bytearray()
    _setup(code, s)
    for index in range(s["PIPE_COUNT"]):
        code += _store_byte(s["pipe_table"] + index * s["PIPE_RECORD_SIZE"] + s["PIPE_READERS_O"], 1)
    _poison_result(code)
    _call_pipe(code, s)
    code += _jp_nc(FAIL_PC) + b"\xFE" + bytes((s["E_NOSPC"],)) + phase1._jp_nz(FAIL_PC)
    _assert_result_poison(code)
    _assert_word(code, s["memory_live_allocations"], 0)
    _assert_byte(code, s["open_description_table"] + s["OD_KIND_O"], 0)
    code += phase1._jp(PASS_PC)
    run_sna(root, bytes(code), patch=phase1._kernel_patch(kernel))


def _rollback_fixture(root: Path, s: dict[str, int], kernel: bytes) -> None:
    code = bytearray()
    _setup(code, s)
    _poison_result(code)
    _call_pipe(code, s)
    code += _jp_nc(FAIL_PC) + b"\xFE" + bytes((s["E_NOSPC"],)) + phase1._jp_nz(FAIL_PC)
    _assert_result_poison(code)
    slot = s["process_table"] + s["PROC_DESC_SIZE"] + s["PROC_HANDLES"]
    _assert_byte(code, slot + 0, s["HANDLE_FREE"])
    _assert_byte(code, slot + 1, s["HANDLE_FREE"])
    _assert_byte(code, s["open_description_table"] + s["OD_KIND_O"], 0)
    _assert_byte(code, s["open_description_table"] + s["OD_RECORD_SIZE"] + s["OD_KIND_O"], 0)
    _assert_word(code, s["pipe_table"] + s["PIPE_PTR_O"], 0)
    _assert_byte(code, s["pipe_table"] + s["PIPE_READERS_O"], 0)
    _assert_byte(code, s["pipe_table"] + s["PIPE_WRITERS_O"], 0)
    _assert_word(code, s["memory_live_allocations"], 0)
    code += phase1._jp(PASS_PC)

    patched = bytearray(kernel)
    offset = s["zx48_handle_install"] - phase1.KERNEL_BASE
    payload = bytes((0x3E, s["E_NOSPC"], 0x37, 0xC9))
    require(0 <= offset <= len(patched) - len(payload), "handle-install patch outside kernel")
    patched[offset:offset + len(payload)] = payload
    run_sna(root, bytes(code), patch=phase1._kernel_patch(bytes(patched)))


def dispatch(
    root: Path,
    action: str,
    step: str,
    *,
    sha256_file: Callable[[Path], str],
    run_command: Callable[..., Any],
    require_project_tool: Callable[[Path, str | Path], Path],
):
    if step != "P3.08":
        raise DriverError(f"Phase-3 pipe-create step is not registered: {step}")

    assertions = _source_contract(root)
    failed = [item["name"] for item in assertions if item["passed"] is not True]
    require(not failed, f"static P3.08 contract failures: {failed}")

    result, kernel, listing = phase1._assemble_kernel(root, run_command, require_project_tool)
    commands = [result]
    symbols = phase3_open_descriptions._symbols(
        listing.with_suffix(".sym"),
        (
            "zx48_memory_init", "zx48_alloc", "zx48_process_init", "zx48_handles_init",
            "zx48_pipe_init", "zx48_process_prepare_pid1", "zx48_od_create",
            "zx48_handle_install", "zx48_syscall_impl",
            "memory_live_allocations", "process_table", "current_pid",
            "open_description_table", "pipe_table",
            "PROC_DESC_SIZE", "PROC_HANDLES", "HANDLE_FREE",
            "OPEN_DESCRIPTION_COUNT", "OD_RECORD_SIZE", "OD_KIND_O", "OD_ACCESS_O",
            "OD_REFS_O", "OD_ID_O", "OD_KIND_NULL", "OD_KIND_PIPE_READ",
            "OD_KIND_PIPE_WRITE", "O_READ", "O_WRITE",
            "PIPE_COUNT", "PIPE_BUFFER_SIZE", "PIPE_FALLBACK_SIZE", "PIPE_RECORD_SIZE",
            "PIPE_PTR_O", "PIPE_RPOS_O", "PIPE_WPOS_O", "PIPE_COUNT_O",
            "PIPE_CAPACITY_O", "PIPE_READERS_O", "PIPE_WRITERS_O",
            "FAST_START", "FAST_END", "ALLOC_FAST_REQUIRED",
            "SYS_PIPE", "E_NOMEM", "E_NOSPC",
        ),
    )
    require(symbols["PIPE_BUFFER_SIZE"] == 256, "normal pipe buffer must remain 256")
    require(symbols["PIPE_FALLBACK_SIZE"] == 128, "pipe fallback must remain exactly 128")
    require(symbols["PIPE_COUNT"] == 4, "pipe count drift")

    if action == "test":
        kernel_bytes = kernel.read_bytes()
        _normal_fixture(root, symbols, kernel_bytes)
        _fallback_fixture(root, symbols, kernel_bytes)
        _enomem_fixture(root, symbols, kernel_bytes)
        _handle_exhaustion_fixture(root, symbols, kernel_bytes)
        _description_exhaustion_fixture(root, symbols, kernel_bytes)
        _pipe_slot_exhaustion_fixture(root, symbols, kernel_bytes)
        _rollback_fixture(root, symbols, kernel_bytes)
        assertions.extend([
            {"name": "normal-256-fast-buffer-and-state-exact", "passed": True},
            {"name": "single-128-fast-fallback-exact", "passed": True},
            {"name": "buffer-exhaustion-enomem-atomic", "passed": True},
            {"name": "handle-exhaustion-enospc-preallocation-atomic", "passed": True},
            {"name": "description-exhaustion-enospc-preallocation-atomic", "passed": True},
            {"name": "pipe-slot-exhaustion-enospc-preallocation-atomic", "passed": True},
            {"name": "forced-postallocation-handle-failure-rolls-back-all-state", "passed": True},
            {"name": "endpoint-results-publish-only-after-complete-commit", "passed": True},
        ])

    hashes = {
        "v1/build/kernel.bin": sha256_file(kernel),
        "v1/include/zx48ux.inc": sha256_file(root / "v1/include/zx48ux.inc"),
        "v1/src/kernel/pipe.asm": sha256_file(root / "v1/src/kernel/pipe.asm"),
        "v1/src/kernel/handles.asm": sha256_file(root / "v1/src/kernel/handles.asm"),
        "v1/src/kernel/memory.asm": sha256_file(root / "v1/src/kernel/memory.asm"),
        "v1/src/kernel/syscall.asm": sha256_file(root / "v1/src/kernel/syscall.asm"),
        "v1/tools-host/test-driver/phase3_pipe_create.py": sha256_file(root / "v1/tools-host/test-driver/phase3_pipe_create.py"),
        "v1/tools-host/test-driver/run.py": sha256_file(root / "v1/tools-host/test-driver/run.py"),
        "v1/dist/certification/P3.07.test.json": sha256_file(root / "v1/dist/certification/P3.07.test.json"),
    }
    return commands, hashes, assertions
