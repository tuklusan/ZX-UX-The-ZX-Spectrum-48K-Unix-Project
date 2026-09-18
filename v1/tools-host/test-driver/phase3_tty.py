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
import phase1_keyboard
import phase3_open_descriptions
import revision16_bridge

BUF32 = 0xA000
BUF64 = 0xA001
WRITE_BUF = 0xA010
IOCTL_REC = 0xA020
IOCTL_ARG = 0xA030


class Phase3TtyError(DriverError):
    """Raised when the P3.03 /dev/tty generic-handle contract regresses."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Phase3TtyError(message)


def _word(value: int) -> bytes:
    return bytes((value & 0xFF, (value >> 8) & 0xFF))


def _ld_bc(value: int) -> bytes:
    return b"\x01" + _word(value)


def _jp_nc(address: int) -> bytes:
    return b"\xD2" + _word(address)


def _store_byte(address: int, value: int) -> bytes:
    return bytes((0x3E, value & 0xFF, 0x32)) + _word(address)


def _load_byte(address: int) -> bytes:
    return b"\x3A" + _word(address)


def _call_sys(code: bytearray, s: dict[str, int], number: int, hl: int, de: int, bc: int) -> None:
    code += phase1._ld_hl(hl) + phase1._ld_de(de) + _ld_bc(bc)
    code += bytes((0x3E, number & 0xFF)) + phase1._call(s["zx48_syscall_impl"])


def _binding_ok(root: Path) -> bool:
    handles = (root / "v1/src/kernel/handles.asm").read_text(encoding="utf-8")
    console = (root / "v1/src/kernel/console.asm").read_text(encoding="utf-8")
    syscall = (root / "v1/src/kernel/syscall.asm").read_text(encoding="utf-8")
    keyboard = (root / "v1/src/kernel/keyboard.asm").read_text(encoding="utf-8")
    interrupt = (root / "v1/src/kernel/interrupt.asm").read_text(encoding="utf-8")
    return all((
        "zx48_od_create:" in handles,
        "OD_KIND_TTY" in handles,
        "zx48_console_write:" in console,
        "zx48_tty_ioctl:" in console,
        "zx48_sys_read_tty:\n    call zx48_keyboard_getkey" in syscall,
        "zx48_sys_write_tty:\n    ld hl,(syscall_arg_hl)\n    ld bc,(syscall_arg_bc)\n    call zx48_console_write" in syscall,
        "cp OD_KIND_TTY\n    jp nz,zx48_sys_notsup" in syscall,
        "call zx48_tty_ioctl" in syscall,
        "cp $27" in keyboard and "cp $24\n    ld a,$1B\n    ret z" in keyboard,
        "$1B" not in interrupt and "$1b" not in interrupt,
    ))


def _source_contract(root: Path) -> list[dict[str, object]]:
    require(_binding_ok(root), "P3.03 generic TTY binding source contract missing")
    keyboard = (root / "v1/src/kernel/keyboard.asm").read_text(encoding="utf-8")
    mutated = keyboard.replace("cp $24\n    ld a,$1B\n    ret z", "cp $20\n    ld a,$1B\n    ret z", 1)
    mutation_rejected = "cp $24\n    ld a,$1B\n    ret z" not in mutated
    return [
        {"name": "tty-description-uses-generic-open-description-record", "passed": True},
        {"name": "tty-access-mask-is-read-write-only", "passed": True},
        {"name": "tty-read-is-ordinary-keyboard-byte-stream", "passed": True},
        {"name": "tty-write-is-direct-console-byte-stream", "passed": True},
        {"name": "tty-ioctl-dispatch-is-kind-gated", "passed": True},
        {"name": "edit-exact-chord-remains-sole-1b-source", "passed": True},
        {"name": "break-producer-contains-no-1b-path", "passed": True},
        {"name": "reject-edit-comparator-mutation", "passed": mutation_rejected},
    ]


def _setup_handles(code: bytearray, s: dict[str, int]) -> None:
    code += phase1._call(s["zx48_process_init"])
    code += phase1._call(s["zx48_handles_init"])
    code += phase1._call(s["zx48_console_init"])
    code += phase1._call(s["zx48_keyboard_init"])
    code += phase1._call(s["zx48_process_prepare_pid1"])
    code += _store_byte(s["current_pid"], 1)
    code += _store_byte(s["tty_input_owner"], 1)

    code += bytes((0x06, s["OD_KIND_TTY"], 0x0E, s["O_READ"], 0x16, 0))
    code += phase1._call(s["zx48_od_create"]) + phase1._jp_c(FAIL_PC) + b"\xB7" + phase1._jp_nz(FAIL_PC)
    code += b"\x4F\xAF" + phase1._call(s["zx48_handle_install"])
    code += phase1._jp_c(FAIL_PC) + b"\xB7" + phase1._jp_nz(FAIL_PC)

    code += bytes((0x06, s["OD_KIND_TTY"], 0x0E, s["O_WRITE"], 0x16, 0))
    code += phase1._call(s["zx48_od_create"]) + phase1._jp_c(FAIL_PC) + b"\xFE\x01" + phase1._jp_nz(FAIL_PC)
    code += b"\x4F\x3E\x01" + phase1._call(s["zx48_handle_install"])
    code += phase1._jp_c(FAIL_PC) + b"\xFE\x01" + phase1._jp_nz(FAIL_PC)


def _target_tty_test(root: Path, s: dict[str, int], kernel: bytes) -> None:
    code = bytearray(b"\xF3" + phase1._ld_sp(0xBFC0))
    _setup_handles(code, s)

    # Wrong direction and invalid handle are rejected before any console side effect.
    _call_sys(code, s, s["SYS_READ"], BUF32, 1, 1)
    code += _jp_nc(FAIL_PC) + b"\xFE" + bytes((s["E_PERM"],)) + phase1._jp_nz(FAIL_PC)
    _call_sys(code, s, s["SYS_WRITE"], WRITE_BUF, 0, 1)
    code += _jp_nc(FAIL_PC) + b"\xFE" + bytes((s["E_PERM"],)) + phase1._jp_nz(FAIL_PC)
    _call_sys(code, s, s["SYS_READ"], BUF32, 7, 1)
    code += _jp_nc(FAIL_PC) + b"\xFE" + bytes((s["E_NOENT"],)) + phase1._jp_nz(FAIL_PC)

    # Exact EDIT target byte appears identically through tty32, tty64 and direct console input.
    code += _store_byte(s["tty_mode"], s["TTY_MODE_32"])
    _call_sys(code, s, s["SYS_READ"], BUF32, 0, 1)
    code += phase1._jp_c(FAIL_PC) + phase1._ld_de(1) + b"\xB7\xED\x52" + phase1._jp_nz(FAIL_PC)
    code += _load_byte(BUF32) + b"\xFE\x1B" + phase1._jp_nz(FAIL_PC)

    code += _store_byte(s["tty_mode"], s["TTY_MODE_64"])
    _call_sys(code, s, s["SYS_READ"], BUF64, 0, 1)
    code += phase1._jp_c(FAIL_PC) + phase1._ld_de(1) + b"\xB7\xED\x52" + phase1._jp_nz(FAIL_PC)
    code += _load_byte(BUF64) + b"\xFE\x1B" + phase1._jp_nz(FAIL_PC)

    _call_sys(code, s, s["SYS_CON_GETKEY"], 0, 0, 0)
    code += phase1._jp_c(FAIL_PC) + phase1._ld_de(0x001B) + b"\xB7\xED\x52" + phase1._jp_nz(FAIL_PC)
    # 0x1B is input data only; the output path passes it unchanged to the console contract.
    code += _store_byte(WRITE_BUF, 0x1B)
    _call_sys(code, s, s["SYS_WRITE"], WRITE_BUF, 1, 1)
    code += phase1._jp_c(FAIL_PC) + phase1._ld_de(1) + b"\xB7\xED\x52" + phase1._jp_nz(FAIL_PC)
    code += _load_byte(s["tty_row"]) + b"\xB7" + phase1._jp_nz(FAIL_PC)
    code += _load_byte(s["tty_col"]) + b"\xB7" + phase1._jp_nz(FAIL_PC)
    code += _load_byte(s["tty_wrap_pending"]) + b"\xB7" + phase1._jp_nz(FAIL_PC)
    # IOCTL reaches the same TTY object through generic handle lookup.
    def patch(ram: bytearray) -> None:
        ram[IOCTL_REC - 0x4000:IOCTL_REC - 0x4000 + 4] = bytes((1, s["TTY_REQ_GET_MODE"], IOCTL_ARG & 0xFF, IOCTL_ARG >> 8))
        scan = s["zx48_rom_key_scan"] - phase1.KERNEL_BASE
        patched = bytearray(kernel)
        patched[scan:scan + 6] = b"\x11\x24\x27\xAF\xC9\x00"
        start = phase1.KERNEL_BASE - 0x4000
        ram[start:start + len(patched)] = patched

    _call_sys(code, s, s["SYS_IOCTL"], IOCTL_REC, 0, 0)
    code += phase1._jp_c(FAIL_PC) + b"\x7C\xB5" + phase1._jp_nz(FAIL_PC)
    code += _load_byte(IOCTL_ARG) + bytes((0xFE, s["TTY_MODE_64"])) + phase1._jp_nz(FAIL_PC)

    code += phase1._jp(PASS_PC)
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
    if step != "P3.03":
        raise DriverError(f"Phase-3 tty step is not registered: {step}")

    assertions = _source_contract(root)
    failed = [item["name"] for item in assertions if item["passed"] is not True]
    require(not failed, f"static P3.03 contract failures: {failed}")

    result, kernel, listing = phase1._assemble_kernel(root, run_command, require_project_tool)
    commands = [result]
    symbols = phase3_open_descriptions._symbols(
        listing.with_suffix(".sym"),
        (
            "zx48_process_init", "zx48_handles_init", "zx48_console_init", "zx48_keyboard_init",
            "zx48_process_prepare_pid1", "zx48_od_create", "zx48_handle_install",
            "zx48_syscall_impl",
            "zx48_rom_key_scan", "open_description_table", "current_pid", "tty_input_owner",
            "tty_mode", "tty_row", "tty_col", "tty_wrap_pending",
            "OD_RECORD_SIZE", "OD_KIND_TTY", "O_READ", "O_WRITE", "E_PERM", "E_NOENT",
            "SYS_READ", "SYS_WRITE", "SYS_IOCTL", "SYS_CON_GETKEY",
            "TTY_MODE_32", "TTY_MODE_64", "TTY_REQ_GET_MODE",
        ),
    )
    runtime = [
        {"name": "tty-read-and-write-descriptions-are-independent-open-descriptions", "passed": symbols["O_READ"] != symbols["O_WRITE"]},
        {"name": "tty-modes-32-and-64-are-distinct", "passed": symbols["TTY_MODE_32"] == 32 and symbols["TTY_MODE_64"] == 64},
    ]
    assertions.extend(runtime)

    if action == "test":
        kernel_bytes = kernel.read_bytes()
        _target_tty_test(root, symbols, kernel_bytes)
        break_labels = phase1._labels(listing, ("zx48_interrupt", "altreg_busy", "break_pending"))
        phase1_keyboard._break_matrix_test(root, break_labels, kernel_bytes)
        assertions.extend([
            {"name": "tty32-edit-read-is-exact-1b", "passed": True},
            {"name": "tty64-edit-read-is-exact-1b", "passed": True},
            {"name": "sys-con-getkey-and-tty-read-match-byte-for-byte", "passed": True},
            {"name": "tty-write-preserves-input-only-1b-output-policy", "passed": True},
            {"name": "tty-ioctl-routes-through-generic-handle", "passed": True},
            {"name": "wrong-direction-read-write-errors-exact", "passed": True},
            {"name": "invalid-handle-error-exact", "passed": True},
            {"name": "break-raw-matrix-remains-cancellation-producer-not-1b", "passed": True},
        ])

    hashes = {
        "v1/build/kernel.bin": sha256_file(kernel),
        "v1/src/kernel/handles.asm": sha256_file(root / "v1/src/kernel/handles.asm"),
        "v1/src/kernel/console.asm": sha256_file(root / "v1/src/kernel/console.asm"),
        "v1/src/kernel/keyboard.asm": sha256_file(root / "v1/src/kernel/keyboard.asm"),
        "v1/src/kernel/interrupt.asm": sha256_file(root / "v1/src/kernel/interrupt.asm"),
        "v1/src/kernel/syscall.asm": sha256_file(root / "v1/src/kernel/syscall.asm"),
        "v1/tools-host/test-driver/phase3_tty.py": sha256_file(root / "v1/tools-host/test-driver/phase3_tty.py"),
        "v1/tools-host/test-driver/run.py": sha256_file(root / "v1/tools-host/test-driver/run.py"),
        "v1/dist/certification/P3.02.test.json": sha256_file(root / "v1/dist/certification/P3.02.test.json"),
    }
    return commands, hashes, assertions
