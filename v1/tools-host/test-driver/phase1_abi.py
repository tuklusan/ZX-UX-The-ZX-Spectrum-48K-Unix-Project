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


class Phase1AbiError(DriverError):
    """Raised when the P1.09 public ABI freeze is violated."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Phase1AbiError(message)


SYSCALLS = {
    "SYS_VERSION": 0x00,
    "SYS_EXIT": 0x01,
    "SYS_YIELD": 0x02,
    "SYS_SLEEP": 0x03,
    "SYS_GETPID": 0x04,
    "SYS_SPAWN": 0x05,
    "SYS_EXEC": 0x06,
    "SYS_WAIT": 0x07,
    "SYS_KILL": 0x08,
    "SYS_OPEN": 0x10,
    "SYS_CLOSE": 0x11,
    "SYS_READ": 0x12,
    "SYS_WRITE": 0x13,
    "SYS_SEEK": 0x14,
    "SYS_STAT": 0x15,
    "SYS_REMOVE": 0x16,
    "SYS_RENAME": 0x17,
    "SYS_LIST": 0x18,
    "SYS_CHDIR": 0x19,
    "SYS_GETCWD": 0x1A,
    "SYS_PACK": 0x1B,
    "SYS_UNPACK": 0x1C,
    "SYS_PIPE": 0x20,
    "SYS_DUP": 0x21,
    "SYS_IOCTL": 0x22,
    "SYS_CON_GETKEY": 0x30,
    "SYS_CON_PUTCHAR": 0x31,
    "SYS_CON_WRITE": 0x32,
    "SYS_CON_CLEAR": 0x33,
    "SYS_CON_GETPOS": 0x34,
    "SYS_CON_SETPOS": 0x35,
    "SYS_GFX_PLOT": 0x40,
    "SYS_GFX_DRAW": 0x41,
    "SYS_GFX_CIRCLE": 0x42,
    "SYS_GFX_ATTR": 0x43,
    "SYS_GFX_BORDER": 0x44,
    "SYS_GFX_POINT": 0x45,
    "SYS_BEEP": 0x46,
    "SYS_UDG_DEFINE": 0x48,
    "SYS_UDG_DRAW": 0x49,
    "SYS_UDG_GET": 0x4A,
    "SYS_UDG_CLEAR": 0x4B,
    "SYS_TAPE_SAVE": 0x50,
    "SYS_TAPE_LOAD": 0x51,
    "SYS_TAPE_VERIFY": 0x52,
    "SYS_TAPE_SCAN": 0x53,
    "SYS_MEM_INFO": 0x60,
    "SYS_PROC_INFO": 0x61,
    "SYS_TICKS": 0x62,
    "SYS_TIME_GET": 0x63,
    "SYS_TIME_SET": 0x64,
    "SYS_ZXPACK_INFO": 0x65,
    "SYS_FP_EXEC": 0x68,
    "SYS_FP_TO_TEXT": 0x69,
    "SYS_FP_FROM_TEXT": 0x6A,
    "SYS_ROM_INFO": 0x6B,
    "SYS_INT_TO_FP": 0x6C,
    "SYS_FP_TO_INT": 0x6D,
    "SYS_FP_CMP": 0x6E,
}

ERRNOS = {
    "E_OK": 0,
    "E_INVAL": 1,
    "E_NOENT": 2,
    "E_NOMEM": 3,
    "E_BUSY": 4,
    "E_IO": 5,
    "E_EOF": 6,
    "E_PERM": 7,
    "E_CHILD": 8,
    "E_PIPE": 9,
    "E_TOOLONG": 10,
    "E_FORMAT": 11,
    "E_NOSPC": 12,
    "E_AGAIN": 13,
    "E_NOTSUP": 14,
    "E_INTR": 15,
    "E_EXIST": 16,
}

FPOPS = {
    "FPOP_INVALID": 0,
    "FPOP_ADD": 1,
    "FPOP_SUB": 2,
    "FPOP_MUL": 3,
    "FPOP_DIV": 4,
    "FPOP_POW": 5,
    "FPOP_ABS": 6,
    "FPOP_SGN": 7,
    "FPOP_INT": 8,
    "FPOP_EXP": 9,
    "FPOP_LN": 10,
    "FPOP_SIN": 11,
    "FPOP_COS": 12,
    "FPOP_TAN": 13,
    "FPOP_ASN": 14,
    "FPOP_ACS": 15,
    "FPOP_ATN": 16,
    "FPOP_SQR": 17,
}

RECORD_CONSTANTS = {
    "FPOP1_OP_O": 0,
    "FPOP1_RESERVED_O": 1,
    "FPOP1_LHS_O": 2,
    "FPOP1_RHS_O": 4,
    "FPOP1_OUT_O": 6,
    "FPOP1_SIZE": 8,
    "ROMQ1_INDEX_O": 0,
    "ROMQ1_CATEGORY_O": 1,
    "ROMQ1_OUT_PTR_O": 2,
    "ROMQ1_SIZE": 4,
    "ROMOUT1_NAME_O": 0,
    "ROMOUT1_ADDRESS_O": 16,
    "ROMOUT1_CLASSIFICATION_O": 18,
    "ROMOUT1_CATEGORY_O": 19,
    "ROMOUT1_CONTRACT_FLAGS_O": 20,
    "ROMOUT1_RESERVED_O": 22,
    "ROMOUT1_SIZE": 24,
    "ROMCAT_ALL": 0,
    "ROMCAT_KEYBOARD": 1,
    "ROMCAT_CONSOLE": 2,
    "ROMCAT_TAPE": 3,
    "ROMCAT_GRAPHICS": 4,
    "ROMCAT_SOUND": 5,
    "ROMCAT_MATH": 6,
    "ROM_CLASS_A": 1,
    "ROM_CLASS_B": 2,
    "ROM_CLASS_C": 3,
    "ROMCF_MAY_ERROR_RESTART": 1,
    "ROMCF_ALTREG_SENSITIVE": 2,
    "ROMCF_DISABLES_INTERRUPTS": 4,
    "ROMCF_NONREENTRANT": 8,
}

_EQU = re.compile(r"^\s*([A-Z][A-Z0-9_]*)\s+EQU\s+(\$[0-9A-Fa-f]+|[0-9]+)\s*(?:;.*)?$")


def _literal_constants(text: str) -> dict[str, int]:
    found: dict[str, int] = {}
    for line in text.splitlines():
        match = _EQU.match(line)
        if match is None:
            continue
        token = match.group(2)
        found[match.group(1)] = int(token[1:], 16) if token.startswith("$") else int(token, 10)
    return found


def _exact_family(constants: dict[str, int], prefix: str, expected: dict[str, int]) -> bool:
    actual = {name: value for name, value in constants.items() if name.startswith(prefix)}
    return actual == expected


def _errno_aliases_only(text: str) -> bool:
    aliases = {}
    pattern = re.compile(r"^\s*(ZX_E_[A-Z0-9_]+)\s+EQU\s+(E_[A-Z0-9_]+)\s*$")
    for line in text.splitlines():
        if line.strip().startswith("ZX_E_"):
            match = pattern.match(line)
            if match is None:
                return False
            aliases[match.group(1)] = match.group(2)
    expected = {f"ZX_{name}": name for name in ERRNOS}
    return aliases == expected


def _syscall_helper_has_no_number_ownership(text: str) -> bool:
    return re.search(r"^\s*SYS_[A-Z0-9_]+\s+EQU\b", text, flags=re.MULTILINE) is None


def _abi_doc_contract(doc: str) -> bool:
    required = [
        "Entry registers are `A=syscall number`, `HL=primary argument/pointer`,",
        "AF/BC/DE/HL are volatile across a syscall; IX is preserved;",
        "`FPOP1` is exactly 8 bytes",
        "`ROMQ1` is exactly 4 bytes",
        "`ROMOUT1` is exactly 24 bytes",
        "MAY_ERROR_RESTART",
        "ALTREG_SENSITIVE",
        "DISABLES_INTERRUPTS",
        "NONREENTRANT",
        "end_exclusive",
        "0x4000-0x5AFF",
        "0x6000-0xDFFF",
    ]
    if not all(token in doc for token in required):
        return False
    for name, value in SYSCALLS.items():
        if f"| `{name}` | `0x{value:02X}` |" not in doc:
            return False
    return True


def _source_contract(root: Path) -> list[dict[str, object]]:
    canonical_text = (root / "v1/include/zx48ux.inc").read_text(encoding="utf-8")
    syscall_text = (root / "v1/include/syscall.inc").read_text(encoding="utf-8")
    errno_text = (root / "v1/include/errno.inc").read_text(encoding="utf-8")
    doc = (root / "v1/docs/abi.md").read_text(encoding="utf-8")
    kernel = (root / "v1/src/kernel/kernel.asm").read_text(encoding="utf-8")
    syscall_asm = (root / "v1/src/kernel/syscall.asm").read_text(encoding="utf-8")
    constants = _literal_constants(canonical_text)
    syscall_constants = _literal_constants(syscall_text)

    assertions = [
        {"name": "exact-59-syscall-assignments", "passed": _exact_family(constants, "SYS_", SYSCALLS)},
        {"name": "exact-errno-values", "passed": all(constants.get(name) == value for name, value in ERRNOS.items())},
        {"name": "exact-fpop-values", "passed": all(syscall_constants.get(name) == value for name, value in FPOPS.items())},
        {
            "name": "exact-packed-record-offsets",
            "passed": all(syscall_constants.get(name) == value for name, value in RECORD_CONSTANTS.items()),
        },
        {"name": "syscall-helper-does-not-redeclare-numbers", "passed": _syscall_helper_has_no_number_ownership(syscall_text)},
        {"name": "errno-helper-is-alias-only", "passed": _errno_aliases_only(errno_text)},
        {
            "name": "kernel-consumes-shared-abi-includes",
            "passed": (
                'INCLUDE "../../include/zx48ux.inc"' in kernel
                and 'INCLUDE "../../include/syscall.inc"' in kernel
            ),
        },
        {
            "name": "validated-table-dispatch-selected",
            "passed": all(
                token in syscall_asm
                for token in (
                    "zx48_sys_dispatch_index:",
                    "add a,a",
                    "add hl,de",
                    "jp (hl)",
                    "jp c,zx48_sys_notsup",
                    "jp nc,zx48_sys_notsup",
                )
            ),
        },
        {"name": "abi-document-mirrors-freeze", "passed": _abi_doc_contract(doc)},
    ]
    return assertions


def _negative_contract_tests(root: Path) -> list[dict[str, object]]:
    canonical_text = (root / "v1/include/zx48ux.inc").read_text(encoding="utf-8")
    syscall_text = (root / "v1/include/syscall.inc").read_text(encoding="utf-8")
    errno_text = (root / "v1/include/errno.inc").read_text(encoding="utf-8")

    renumbered = canonical_text.replace("SYS_KILL                 EQU $08", "SYS_KILL                 EQU $09", 1)
    aliased = canonical_text + "\nSYS_GAP_ALIAS            EQU $09\n"
    errno_changed = canonical_text.replace("E_INTR                   EQU $0F", "E_INTR                   EQU $10", 1)
    record_changed = syscall_text.replace("ROMOUT1_SIZE             EQU $18", "ROMOUT1_SIZE             EQU $17", 1)
    helper_owns_gap = syscall_text + "\nSYS_GAP_ALIAS EQU $09\n"
    numeric_errno_alias = errno_text.replace("ZX_E_INVAL               EQU E_INVAL", "ZX_E_INVAL               EQU $01", 1)

    return [
        {
            "name": "reject-syscall-renumbering",
            "passed": not _exact_family(_literal_constants(renumbered), "SYS_", SYSCALLS),
        },
        {
            "name": "reject-gap-alias",
            "passed": not _exact_family(_literal_constants(aliased), "SYS_", SYSCALLS),
        },
        {
            "name": "reject-errno-renumbering",
            "passed": _literal_constants(errno_changed).get("E_INTR") != ERRNOS["E_INTR"],
        },
        {
            "name": "reject-record-size-drift",
            "passed": _literal_constants(record_changed).get("ROMOUT1_SIZE") != RECORD_CONSTANTS["ROMOUT1_SIZE"],
        },
        {
            "name": "reject-syscall-helper-number-ownership",
            "passed": not _syscall_helper_has_no_number_ownership(helper_owns_gap),
        },
        {
            "name": "reject-numeric-errno-alias",
            "passed": not _errno_aliases_only(numeric_errno_alias),
        },
    ]


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


def _ld_hl(value: int) -> bytes:
    return b"\x21" + _word(value)


def _ld_bc(value: int) -> bytes:
    return b"\x01" + _word(value)


def _compare_hl(value: int) -> bytes:
    return b"\x11" + _word(value) + b"\xB7\xED\x52" + _jp_nz(FAIL_PC)


def _expect_range(validator: int, start: int, length: int, ok: bool) -> bytes:
    code = bytearray(_ld_hl(start) + _ld_bc(length) + _call(validator))
    code += _jp_c(FAIL_PC) if ok else _jp_nc(FAIL_PC)
    if not ok:
        code += b"\xFE" + bytes((ERRNOS["E_INVAL"],)) + _jp_nz(FAIL_PC)
    return bytes(code)


def _runtime_test(root: Path, labels: dict[str, int], kernel_bytes: bytes) -> None:
    stack_init = labels["zx48_kernel_stack_init"]
    validator = labels["zx48_user_range_validate"]

    code = bytearray()
    code += b"\xF3\x31" + _word(phase1.USER_STACK) + _call(stack_init)

    code += b"\xDD\x21\x34\x12\xFD\x21\x00\x20\xAF" + _call(phase1.KERNEL_BASE)
    code += _jp_c(FAIL_PC)
    code += b"\xB7" + _jp_nz(FAIL_PC)
    code += _compare_hl(0x0100)
    code += b"\xDD\xE5\xE1" + _compare_hl(0x1234)
    code += b"\xFD\xE5\xE1" + _compare_hl(0x5C3A)

    assigned = set(SYSCALLS.values())
    for number in range(256):
        if number in assigned:
            continue
        code += bytes((0x3E, number)) + _call(phase1.KERNEL_BASE)
        code += _jp_nc(FAIL_PC)
        code += bytes((0xFE, ERRNOS["E_NOTSUP"])) + _jp_nz(FAIL_PC)

    cases = (
        (0x0000, 0x0000, True),
        (0x4000, 0x0001, True),
        (0x4000, 0x1B00, True),
        (0x5AFF, 0x0001, True),
        (0x5AFF, 0x0002, False),
        (0x5B00, 0x0001, False),
        (0x5FFF, 0x0001, False),
        (0x6000, 0x0001, True),
        (0x6000, 0x8000, True),
        (0xDFFF, 0x0001, True),
        (0xDFFF, 0x0002, False),
        (0xE000, 0x0001, False),
        (0x3FFF, 0x0001, False),
        (0xFFFF, 0x0002, False),
    )
    for start, length, ok in cases:
        code += _expect_range(validator, start, length, ok)

    code += _jp(PASS_PC)

    def patch(ram: bytearray) -> None:
        start = phase1.KERNEL_BASE - 0x4000
        ram[start:start + len(kernel_bytes)] = kernel_bytes

    run_sna(root, bytes(code), patch=patch)


def dispatch(
    root: Path,
    action: str,
    step: str,
    *,
    sha256_file: Callable[[Path], str],
    run_command: Callable[..., Any],
    require_project_tool: Callable[[Path, str | Path], Path],
):
    if step != "P1.09":
        raise Phase1AbiError(f"ABI freeze step is not registered: {step}")

    assertions = _source_contract(root)
    failed = [str(item["name"]) for item in assertions if item["passed"] is not True]
    require(not failed, f"P1.09 static ABI freeze failed: {failed}")

    command, kernel, listing = phase1._assemble_kernel(root, run_command, require_project_tool)
    labels = phase1._labels(
        listing,
        (
            "zx48_kernel_stack_init",
            "zx48_user_range_validate",
            "zx48_syscall_impl",
            "zx48_sys_version",
            "zx48_sys_process_table",
            "syscall_user_sp",
        ),
    )
    kernel_bytes = kernel.read_bytes()

    dispatcher_code_bytes = labels["zx48_sys_version"] - labels["zx48_syscall_impl"]
    dispatcher_table_bytes = labels["syscall_user_sp"] - labels["zx48_sys_process_table"]
    compact_bytes = dispatcher_code_bytes + dispatcher_table_bytes
    long_chain_bytes = len(SYSCALLS) * 5 + 3
    require(0 < compact_bytes < long_chain_bytes, "measured validated table dispatch is not smaller than long chain")
    assertions.append(
        {
            "name": "measured-table-dispatch-smaller-than-59-way-chain",
            "passed": True,
            "compact_current_bytes": compact_bytes,
            "long_chain_bytes": long_chain_bytes,
        }
    )

    if action == "test":
        _runtime_test(root, labels, kernel_bytes)
        assertions.extend(
            [
                {"name": "syscall-success-register-contract", "passed": True},
                {"name": "all-unassigned-syscall-values-return-enotsup", "passed": True, "count": 256 - len(SYSCALLS)},
                {"name": "generic-user-range-boundaries-and-overflow", "passed": True},
                *_negative_contract_tests(root),
            ]
        )
        failed = [str(item["name"]) for item in assertions if item["passed"] is not True]
        require(not failed, f"P1.09 runtime/negative ABI freeze failed: {failed}")

    paths = (
        root / "v1/include/zx48ux.inc",
        root / "v1/include/syscall.inc",
        root / "v1/include/errno.inc",
        root / "v1/docs/abi.md",
        root / "v1/src/kernel/syscall.asm",
        root / "v1/tools-host/test-driver/phase1_abi.py",
        kernel,
    )
    hashes = {str(path.relative_to(root)).replace("\\", "/"): sha256_file(path) for path in paths}
    return [command], hashes, assertions
