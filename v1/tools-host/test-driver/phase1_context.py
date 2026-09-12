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

PROC_DESC_SIZE = 48
PROC_STATE = 2
PROC_SAVED_SP = 12
PROC_PRIVATE_FLAGS = 46
PROC_READY = 1

FRAME_SP = 0xA800
FRAME_IX = 0x8123
FRAME_HL = 0x9234
FRAME_DE = 0xA345
FRAME_BC = 0xB456
FRAME_AF = 0xC7A5
VERIFY_PC = 0xB100
CAPTURE = 0xB200

FORBIDDEN_CONTEXT_NAMES = (
    "PROC_AF",
    "PROC_BC",
    "PROC_DE",
    "PROC_HL",
    "PROC_IX",
    "PROC_PC",
    "PROC_AF_ALT",
    "PROC_BC_ALT",
    "PROC_DE_ALT",
    "PROC_HL_ALT",
)


class Phase1ContextError(DriverError):
    """Raised when the P1.07 canonical cooperative context-frame contract fails."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Phase1ContextError(message)


def _word(value: int) -> bytes:
    return bytes((value & 0xFF, (value >> 8) & 0xFF))


def _call(address: int) -> bytes:
    return b"\xCD" + _word(address)


def _jp(address: int) -> bytes:
    return b"\xC3" + _word(address)


def _jp_nz(address: int) -> bytes:
    return b"\xC2" + _word(address)


def _ld_sp(value: int) -> bytes:
    return b"\x31" + _word(value)


def _ld_ix(value: int) -> bytes:
    return b"\xDD\x21" + _word(value)


def _store_byte(address: int, value: int) -> bytes:
    return bytes((0x3E, value & 0xFF, 0x32)) + _word(address)


def _expect_byte(address: int, value: int) -> bytes:
    return b"\x3A" + _word(address) + bytes((0xFE, value & 0xFF)) + _jp_nz(FAIL_PC)


def _identifier_present(text: str, name: str) -> bool:
    return re.search(rf"(?<![A-Za-z0-9_]){re.escape(name)}(?![A-Za-z0-9_])", text, re.IGNORECASE) is not None


def _restore_body(scheduler: str) -> str:
    lower = scheduler.lower()
    start = lower.find("zx48_schedule_not_cancelled:")
    end = lower.find("zx48_schedule_idle_restore:", start)
    require(0 <= start < end, "scheduler restore block missing")
    return lower[start:end]


def _descriptor_is_sp_only(process: str) -> bool:
    return (
        re.search(r"(?mi)^PROC_SAVED_SP\s+EQU\s+12\s*$", process) is not None
        and not any(_identifier_present(process, name) for name in FORBIDDEN_CONTEXT_NAMES)
    )


def _canonical_restore(body: str) -> bool:
    required = (
        "ld l,(ix+proc_saved_sp)",
        "ld h,(ix+proc_saved_sp+1)",
        "ld sp,hl",
        "pop ix",
        "pop hl",
        "pop de",
        "pop bc",
        "pop af",
        "ld iy,rom_iy_anchor",
        "ret",
    )
    positions = [body.find(token) for token in required]
    return (
        all(position >= 0 for position in positions)
        and positions == sorted(positions)
        and "exx" not in body
        and "ex af,af'" not in body
        and "ex af, af'" not in body
    )


def _source_contract(root: Path) -> list[dict[str, object]]:
    process = (root / "v1/src/kernel/process.asm").read_text(encoding="utf-8")
    scheduler = (root / "v1/src/kernel/scheduler.asm").read_text(encoding="utf-8")
    syscall = (root / "v1/src/kernel/syscall.asm").read_text(encoding="utf-8").lower()
    abi = (root / "v1/docs/abi.md").read_text(encoding="utf-8").lower()
    restore = _restore_body(scheduler)
    frame_pushes = (
        "push af",
        "push bc",
        "push de",
        "push hl",
        "push ix",
        "ld (syscall_frame_sp),sp",
    )
    frame_start = syscall.find("push af", syscall.find("zx48_syscall:"))
    frame_end = syscall.find("ld (syscall_frame_sp),sp", frame_start)
    frame_body = syscall[frame_start:frame_end + len("ld (syscall_frame_sp),sp")] if 0 <= frame_start <= frame_end else ""
    push_positions = [frame_body.find(token) for token in frame_pushes]
    return [
        {"name": "descriptor-saved-sp-is-canonical", "passed": _descriptor_is_sp_only(process)},
        {
            "name": "canonical-frame-push-order",
            "passed": all(position >= 0 for position in push_positions) and push_positions == sorted(push_positions),
        },
        {"name": "canonical-frame-restore-order", "passed": _canonical_restore(restore)},
        {
            "name": "return-pc-is-stacked-frame-tail",
            "passed": "syscall_frame_pc_o       equ 10" in syscall,
        },
        {
            "name": "iy-is-global-rom-anchor",
            "passed": "iy is\nos/rom-reserved and has the canonical value `5c3a`" in abi
            or "iy            os/rom-reserved; must remain at 0x5c3a" in abi,
        },
        {
            "name": "alternate-bank-is-volatile",
            "passed": "alternate register bank is\nos-private and volatile from user code" in abi
            or "af'/bc'/de'/hl' os-private/volatile" in abi,
        },
    ]


def _negative_contract_tests(root: Path) -> list[dict[str, object]]:
    process = (root / "v1/src/kernel/process.asm").read_text(encoding="utf-8")
    scheduler = (root / "v1/src/kernel/scheduler.asm").read_text(encoding="utf-8")
    restore = _restore_body(scheduler)
    persistent_descriptor = process + "\nPROC_AF_ALT EQU 48\n"
    persistent_restore = restore.replace("pop af", "pop af\n    exx\n    ex af,af'")
    return [
        {
            "name": "reject-persistent-alternate-register-descriptor",
            "passed": not _descriptor_is_sp_only(persistent_descriptor),
        },
        {
            "name": "reject-persistent-alternate-register-restore",
            "passed": not _canonical_restore(persistent_restore),
        },
    ]


def _context_frame() -> bytes:
    return b"".join(
        _word(value)
        for value in (FRAME_IX, FRAME_HL, FRAME_DE, FRAME_BC, FRAME_AF, VERIFY_PC)
    )


def _capture_and_verify() -> bytes:
    code = bytearray()
    code += b"\x22" + _word(CAPTURE + 0)
    code += b"\xED\x53" + _word(CAPTURE + 2)
    code += b"\xED\x43" + _word(CAPTURE + 4)
    code += b"\xDD\x22" + _word(CAPTURE + 6)
    code += b"\xED\x73" + _word(CAPTURE + 8)
    code += b"\xFD\x22" + _word(CAPTURE + 10)
    code += b"\xF5\xE1"
    code += b"\x22" + _word(CAPTURE + 12)
    expected = (
        _word(FRAME_HL)
        + _word(FRAME_DE)
        + _word(FRAME_BC)
        + _word(FRAME_IX)
        + _word(FRAME_SP + 12)
        + _word(0x5C3A)
        + _word(FRAME_AF)
    )
    for offset, value in enumerate(expected):
        code += _expect_byte(CAPTURE + offset, value)
    code += _jp(PASS_PC)
    return bytes(code)


def _runtime_test(root: Path, labels: dict[str, int], kernel_bytes: bytes) -> None:
    stack_init = labels["zx48_kernel_stack_init"]
    process_init = labels["zx48_process_init"]
    schedule_restore = labels["zx48_schedule_restore"]
    process_table = labels["process_table"]
    scheduler_candidate = labels["scheduler_candidate"]
    current_pid = labels["current_pid"]

    pid1 = process_table + PROC_DESC_SIZE
    code = bytearray(b"\xF3" + _ld_sp(phase1.KSTACK_TOP))
    code += _call(stack_init) + _call(process_init)
    code += _ld_ix(pid1)
    code += bytes((0xDD, 0x36, PROC_STATE, PROC_READY))
    code += bytes((0xDD, 0x36, PROC_SAVED_SP, FRAME_SP & 0xFF))
    code += bytes((0xDD, 0x36, PROC_SAVED_SP + 1, FRAME_SP >> 8))
    code += bytes((0xDD, 0x36, PROC_PRIVATE_FLAGS, 0))
    code += _store_byte(scheduler_candidate, 1)
    code += _jp(schedule_restore)

    verifier = bytearray(_capture_and_verify())
    verifier[-3:-3] = _expect_byte(current_pid, 1)

    def patch(ram: bytearray) -> None:
        start = phase1.KERNEL_BASE - 0x4000
        ram[start:start + len(kernel_bytes)] = kernel_bytes
        frame = FRAME_SP - 0x4000
        ram[frame:frame + 12] = _context_frame()
        verify = VERIFY_PC - 0x4000
        ram[verify:verify + len(verifier)] = verifier

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
    if step != "P1.07":
        raise Phase1ContextError(f"canonical context-frame step is not registered: {step}")

    assertions = _source_contract(root)
    failed = [str(item["name"]) for item in assertions if item["passed"] is not True]
    require(not failed, f"P1.07 static context-frame contract failed: {failed}")

    command, kernel, listing = phase1._assemble_kernel(root, run_command, require_project_tool)
    labels = phase1._labels(
        listing,
        (
            "zx48_kernel_stack_init",
            "zx48_process_init",
            "zx48_schedule_restore",
            "process_table",
            "scheduler_candidate",
            "current_pid",
        ),
    )
    kernel_bytes = kernel.read_bytes()

    if action == "test":
        _runtime_test(root, labels, kernel_bytes)
        assertions.extend(
            [
                {"name": "synthetic-frame-restores-primary-ix-sp-pc", "passed": True},
                {"name": "runtime-iy-restored-to-rom-anchor", "passed": True},
                *_negative_contract_tests(root),
            ]
        )
        failed = [str(item["name"]) for item in assertions if item["passed"] is not True]
        require(not failed, f"P1.07 negative/runtime context-frame contract failed: {failed}")

    paths = (
        root / "v1/src/kernel/scheduler.asm",
        root / "v1/src/kernel/process.asm",
        root / "v1/src/kernel/syscall.asm",
        root / "v1/docs/abi.md",
        root / "v1/tools-host/test-driver/phase1_context.py",
        kernel,
    )
    hashes = {str(path.relative_to(root)).replace("\\", "/"): sha256_file(path) for path in paths}
    return [command], hashes, assertions
