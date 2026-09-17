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
import re
from typing import Any, Callable

from driver_core import DriverError
from fuse_harness import FAIL_PC, PASS_PC, run_sna
import phase1
import phase2_spawn

TEST_STACK = 0xFD00
QUERY_BUFFER = 0x8900
INFO_BUFFER = 0x8920
PROC_PARENT = 1
PROC_STATE = 2
PROC_FLAGS = 3
PROC_NAME = 29
PROC_OWNED_BYTES = 40
PROC_PRIVATE_FLAGS = 46
PROC_DESC_SIZE = 48
PROC_READY = 1
PROC_FLAG_CANCEL = 0x01
NAME10 = b"ProcInfo21"


class Phase221Error(DriverError):
    """Raised when the P2.21 SYS_PROC_INFO/PROC1 ABI contract is violated."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Phase221Error(message)


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


def _set_byte(address: int, value: int) -> bytes:
    return bytes((0x3E, value & 0xFF, 0x32)) + _word(address)


def _set_word(address: int, value: int) -> bytes:
    return phase1._ld_hl(value) + b"\x22" + _word(address)


def _expect_byte(address: int, value: int) -> bytes:
    return b"\x3A" + _word(address) + bytes((0xFE, value & 0xFF)) + _jp_nz(FAIL_PC)


def _slice(text: str, start: str, end: str) -> str:
    begin = text.index(start)
    finish = text.index(end, begin)
    return text[begin:finish]


def _ordered(text: str, *tokens: str) -> bool:
    pos = 0
    for token in tokens:
        found = text.find(token, pos)
        if found < 0:
            return False
        pos = found + len(token)
    return True


def _source_contract(root: Path) -> list[dict[str, object]]:
    syscall = (root / "v1/src/kernel/syscall.asm").read_text(encoding="utf-8")
    process = (root / "v1/src/kernel/process.asm").read_text(encoding="utf-8")
    proc_info = _slice(syscall, "zx48_sys_proc_info:\n", "zx48_sys_ticks:\n")
    process_info = _slice(process, "zx48_process_info:\n", "zx48_process_exit:\n")
    spawn_macro = _slice(
        syscall,
        "    MACRO EMIT_SPAWN_PREFLIGHT_ROUTINES\n",
        "    ENDM\n",
    )
    spawn_preflight = spawn_macro[spawn_macro.index("zx48_sys_spawn_preflight:\n") :]

    return [
        {
            "name": "pinfoq1-exact-four-byte-query-zero-reserved-and-sixteen-byte-output",
            "passed": _ordered(
                proc_info,
                "ld bc,4",
                "call zx48_user_range_validate",
                "ld (syscall_temp),a",
                "jp nz,zx48_sys_invalid",
                "ld bc,16",
                "call zx48_user_range_validate",
                "ld a,(syscall_temp)",
                "call zx48_process_info",
            ),
        },
        {
            "name": "proc-info-public-flags-are-cancel-pending-bit0-only",
            "passed": _ordered(
                process_info,
                "ld a,(ix+PROC_FLAGS)",
                "and PROC_FLAG_CANCEL",
                "ld (hl),a",
            ),
        },
        {
            "name": "proc-info-exact-name-and-owned-byte-fields-remain-frozen",
            "passed": all(
                token in process_info
                for token in (
                    "ld de,PROC_NAME",
                    "ld b,10",
                    "djnz zx48_process_info_name",
                    "ld a,(ix+PROC_OWNED_BYTES)",
                    "ld a,(ix+PROC_OWNED_BYTES+1)",
                )
            ),
        },
        {
            "name": "started-is-kernel-private-and-not-the-public-flags-field",
            "passed": re.search(r"^PROC_PRIVATE_FLAGS\s+EQU\s+46$", process, re.MULTILINE) is not None
            and "PROC_PRIVATE_STARTED" in process,
        },
        {
            "name": "proc1-layout-and-allow-tape-control-bit-remain-frozen",
            "passed": all(
                re.search(pattern, syscall, re.MULTILINE) is not None
                for pattern in (
                    r"^PROC1_PATH_PTR\s+EQU\s+0$",
                    r"^PROC1_ARG1_PTR\s+EQU\s+2$",
                    r"^PROC1_ARG1_LEN\s+EQU\s+4$",
                    r"^PROC1_ENV1_PTR\s+EQU\s+6$",
                    r"^PROC1_ENV1_LEN\s+EQU\s+8$",
                    r"^PROC1_STDIN_HANDLE\s+EQU\s+10$",
                    r"^PROC1_STDOUT_HANDLE\s+EQU\s+11$",
                    r"^PROC1_STDERR_HANDLE\s+EQU\s+12$",
                    r"^PROC1_FLAGS\s+EQU\s+13$",
                    r"^PROC1_RESERVED\s+EQU\s+14$",
                    r"^PROC1_SIZE\s+EQU\s+16$",
                    r"^PROC1_ALLOW_TAPE\s+EQU\s+\$01$",
                )
            ),
        },
        {
            "name": "proc1-preflight-rejects-unknown-flags-and-nonzero-reserved-word",
            "passed": _ordered(
                spawn_preflight,
                "ld a,(ix+PROC1_FLAGS)",
                "and $FE",
                "jr nz,zx48_sys_spawn_preflight_invalid",
                "ld a,(ix+PROC1_RESERVED)",
                "or (ix+PROC1_RESERVED+1)",
                "jr nz,zx48_sys_spawn_preflight_invalid",
            ),
        },
    ]


def _proc_info_vector(root: Path, labels: dict[str, int], kernel_bytes: bytes) -> None:
    require(len(NAME10) == 10, "P2.21 name vector is not exactly ten bytes")
    child = labels["process_table"] + 2 * PROC_DESC_SIZE
    code = bytearray(b"\xF3" + phase1._ld_sp(TEST_STACK))
    code += _call(labels["zx48_kernel_stack_init"])
    code += _call(labels["zx48_process_init"])
    code += _set_byte(child + PROC_PARENT, 1)
    code += _set_byte(child + PROC_STATE, PROC_READY)
    code += _set_byte(child + PROC_FLAGS, 0xFF)
    code += _set_byte(child + PROC_PRIVATE_FLAGS, 0xFF)
    code += _set_word(child + PROC_OWNED_BYTES, 0x1234)
    for index, byte in enumerate(NAME10):
        code += _set_byte(child + PROC_NAME + index, byte)

    code += _set_byte(QUERY_BUFFER, 2)
    code += _set_byte(QUERY_BUFFER + 1, 0)
    code += _set_word(QUERY_BUFFER + 2, INFO_BUFFER)
    code += _set_word(labels["syscall_arg_hl"], QUERY_BUFFER)
    code += _call(labels["zx48_sys_proc_info"]) + _jp_c(FAIL_PC)
    code += _expect_byte(INFO_BUFFER, 2)
    code += _expect_byte(INFO_BUFFER + 1, 1)
    code += _expect_byte(INFO_BUFFER + 2, PROC_READY)
    code += _expect_byte(INFO_BUFFER + 3, PROC_FLAG_CANCEL)
    for index, byte in enumerate(NAME10):
        code += _expect_byte(INFO_BUFFER + 4 + index, byte)
    code += _expect_byte(INFO_BUFFER + 14, 0x34)
    code += _expect_byte(INFO_BUFFER + 15, 0x12)

    code += _set_byte(child + PROC_FLAGS, 0)
    code += _set_byte(INFO_BUFFER + 3, 0xA5)
    code += _call(labels["zx48_sys_proc_info"]) + _jp_c(FAIL_PC)
    code += _expect_byte(INFO_BUFFER + 3, 0)

    code += _set_byte(QUERY_BUFFER, 0)
    code += _call(labels["zx48_sys_proc_info"]) + _jp_c(FAIL_PC)
    code += _expect_byte(INFO_BUFFER, 0)
    code += _expect_byte(INFO_BUFFER + 1, 0xFF)

    code += _set_byte(QUERY_BUFFER, 3)
    code += _call(labels["zx48_sys_proc_info"]) + _jp_nc(FAIL_PC)
    code += bytes((0xFE, labels["E_NOENT"] & 0xFF)) + _jp_nz(FAIL_PC)

    code += _set_byte(QUERY_BUFFER, 2)
    code += _set_byte(QUERY_BUFFER + 1, 1)
    code += _call(labels["zx48_sys_proc_info"]) + _jp_nc(FAIL_PC)
    code += bytes((0xFE, labels["E_INVAL"] & 0xFF)) + _jp_nz(FAIL_PC)
    code += _jp(PASS_PC)
    run_sna(root, bytes(code), patch=phase1._kernel_patch(kernel_bytes), timeout=20.0)


def _proc1_vectors(root: Path, run_command: Callable[..., Any], require_project_tool: Callable[[Path, str | Path], Path]):
    command, binary, _listing, symbols_path = phase2_spawn._assemble_fixture(root, run_command, require_project_tool)
    symbols = phase2_spawn._symbols(
        symbols_path,
        (
            "p209_gateway", "p209_bad_gateway", "zx48_sys_spawn", "zx48_sys_spawn_preflight",
            "process_table", "p209_allocator_state", "p209_open_state", "SYS_SPAWN",
            "PROC1_SIZE", "PROC1_PATH_MAX", "MAX_PROCESSES", "PROC_DESC_SIZE",
            "E_INVAL", "E_TOOLONG", "E_AGAIN", "E_NOTSUP",
        ),
    )
    fixture = binary.read_bytes()
    phase2_spawn._run_preflight_case(root, symbols, fixture, proc=phase2_spawn._proc1(flags=0))
    phase2_spawn._run_preflight_case(root, symbols, fixture, proc=phase2_spawn._proc1(flags=1))
    phase2_spawn._run_preflight_case(root, symbols, fixture, proc=phase2_spawn._proc1(flags=2), expected_error=symbols["E_INVAL"])
    phase2_spawn._run_preflight_case(root, symbols, fixture, proc=phase2_spawn._proc1(reserved=1), expected_error=symbols["E_INVAL"])
    return command, binary


def dispatch(root: Path, action: str, step: str, *, sha256_file: Callable[[Path], str], run_command: Callable[..., Any], require_project_tool: Callable[[Path, str | Path], Path]):
    if step != "P2.21":
        raise Phase221Error(f"P2.21 driver received unexpected step: {step}")
    assertions = _source_contract(root)
    failed = [item["name"] for item in assertions if item["passed"] is not True]
    require(not failed, f"static P2.21 contract failures: {failed}")

    kernel_command, kernel, listing = phase1._assemble_kernel(root, run_command, require_project_tool)
    labels = phase1._labels(
        listing,
        ("zx48_kernel_stack_init", "zx48_process_init", "zx48_sys_proc_info", "syscall_arg_hl", "process_table", "E_NOENT", "E_INVAL"),
    )
    commands: list[Any] = [kernel_command]
    proc1_binary: Path | None = None
    if action == "test":
        _proc_info_vector(root, labels, kernel.read_bytes())
        proc1_command, proc1_binary = _proc1_vectors(root, run_command, require_project_tool)
        commands.append(proc1_command)
        assertions.extend(
            [
                {"name": "target-pinfoq1-and-exact-16-byte-proc-info-layout-pass", "passed": True},
                {"name": "target-private-flags-do-not-leak-and-cancel-is-bit0-only", "passed": True},
                {"name": "target-free-pid-and-reserved-query-byte-fail-correctly", "passed": True},
                {"name": "target-proc1-allow-tape-bit0-accepted-unknown-bits-and-reserved-rejected", "passed": True},
            ]
        )

    hashes = {
        "v1/build/kernel.bin": sha256_file(kernel),
        "v1/src/kernel/process.asm": sha256_file(root / "v1/src/kernel/process.asm"),
        "v1/src/kernel/syscall.asm": sha256_file(root / "v1/src/kernel/syscall.asm"),
        "v1/tools-host/test-driver/phase2_proc_info.py": sha256_file(root / "v1/tools-host/test-driver/phase2_proc_info.py"),
        "v1/tools-host/test-driver/run.py": sha256_file(root / "v1/tools-host/test-driver/run.py"),
    }
    if proc1_binary is not None:
        hashes["v1/build/p209-spawn.bin"] = sha256_file(proc1_binary)
    return commands, hashes, assertions
