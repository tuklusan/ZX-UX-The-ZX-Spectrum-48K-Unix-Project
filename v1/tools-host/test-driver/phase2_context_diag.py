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
import sys

sys.dont_write_bytecode = True

from driver_core import DriverError, find_root, require_project_tool, run_command
from fuse_harness import FAIL_PC, PASS_PC
import phase1
import phase2_context as context
import phase2_mex1

MEX1_HEADER_SIZE = 24


class ContextDiagnosticError(DriverError):
    """Raised when a named P2.08 post-frame diagnostic boundary fails."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ContextDiagnosticError(message)


def _diagnostic_mex(mex: bytes, prefix: bytes, user_image_size: int) -> bytes:
    require(len(mex) >= MEX1_HEADER_SIZE + user_image_size, "diagnostic MEX shorter than image")
    require(len(prefix) <= user_image_size, "diagnostic prefix does not fit user image")
    patched = bytearray(mex)
    patched[MEX1_HEADER_SIZE:MEX1_HEADER_SIZE + len(prefix)] = prefix
    return bytes(patched)


def _entry_compare_hl(expected_address: int) -> bytes:
    return context._ld_de_mem(expected_address) + b"\xB7\xED\x52" + phase1._jp_nz(FAIL_PC) + phase1._jp(PASS_PC)


def _entry_compare_de(expected_address: int) -> bytes:
    return b"\xD5\xE1" + _entry_compare_hl(expected_address)


def _entry_compare_bc(expected_address: int) -> bytes:
    return b"\x60\x69" + _entry_compare_hl(expected_address)


def _entry_compare_index(prefix: bytes, expected_value: int) -> bytes:
    return prefix + phase1._ld_de(expected_value) + b"\xB7\xED\x52" + phase1._jp_nz(FAIL_PC) + phase1._jp(PASS_PC)


def _entry_compare_sp() -> bytes:
    return phase1._ld_hl(0) + b"\x39" + _entry_compare_hl(context.RESULT_STACK_END)


def _run_case(root: Path, symbols: dict[str, int], fixture: bytes, mex: bytes, user_image_size: int, arg: bytes, env: bytes, stage: str) -> None:
    try:
        context._first_dispatch_case(root, symbols, fixture, mex, user_image_size, arg, env, crossing=False)
    except DriverError as exc:
        raise ContextDiagnosticError(f"P2.08 post-frame dispatch probe failed at {stage}: {exc}") from exc


def main() -> int:
    root = find_root(Path(__file__))
    _, fixture_binary, fixture_symbols = context._assemble_fixture(root, run_command, require_project_tool)
    _, user_binary, user_symbols = context._assemble_user(root, run_command, require_project_tool)
    user_values = context._symbols(user_symbols, ("p208_user_start", "p208_main_call_word"))
    user_image = user_binary.read_bytes()
    user_image_size = len(user_image)
    reloc_offset = user_values["p208_main_call_word"] - user_values["p208_user_start"]
    require(3 <= reloc_offset < user_image_size - 2, "diagnostic relocation offset implausible")

    mex = phase2_mex1._fixture(
        image=user_image,
        bss_size=context.BSS_SIZE,
        entry=0,
        stack=context.MEX_MIN_STACK,
        relocations=(reloc_offset,),
    )
    names = (
        "zx48_memory_init", "zx48_alloc", "zx48_mex1_load_image", "zx48_mex1_alloc_stack",
        "zx48_env1_build", "zx48_process_build_initial_context", "memory_live_allocations",
        "ALLOC_ANY", "ALLOC_FAST_REQUIRED", "E_FORMAT", "ROM_IY_ANCHOR",
        "PROCESS_STACK_BOOTSTRAP_BYTES", "PROCESS_CONTEXT_FRAME_BYTES", "INITIAL_CONTEXT_SEED_SIZE",
        "SYS_EXIT",
    )
    symbols = context._symbols(fixture_symbols, names)
    fixture = fixture_binary.read_bytes()
    arg = context._arg1()
    env = context._env1()

    probes: list[tuple[str, bytes]] = [
        ("scheduler-restore-ret", phase1._jp(PASS_PC)),
        ("entry-a-zero", b"\xB7" + phase1._jp_nz(FAIL_PC) + phase1._jp(PASS_PC)),
        ("entry-hl-arg1", _entry_compare_hl(context.RESULT_ARG_PTR)),
        ("entry-de-env1", _entry_compare_de(context.RESULT_ENV_PTR)),
        ("entry-bc-arg1-length", _entry_compare_bc(context.RESULT_ARG_LEN)),
        ("entry-iy-canonical", _entry_compare_index(b"\xFD\xE5\xE1", symbols["ROM_IY_ANCHOR"])),
        ("entry-ix-zero", _entry_compare_index(b"\xDD\xE5\xE1", 0)),
        ("entry-sp-stack-end", _entry_compare_sp()),
        ("entry-direct-exit-gateway", phase1._ld_hl(0) + context._ld_a(symbols["SYS_EXIT"]) + phase1._call(0xE000) + phase1._jp(FAIL_PC)),
    ]
    for stage, prefix in probes:
        require(len(prefix) <= reloc_offset - 1, f"diagnostic prefix overlaps relocation at {stage}")
        _run_case(root, symbols, fixture, _diagnostic_mex(mex, prefix, user_image_size), user_image_size, arg, env, stage)

    before_main = bytearray(user_image)
    before_main[reloc_offset - 1] = 0xC3
    bypass_offset = reloc_offset + 2
    require(bypass_offset <= user_image_size - 3, "diagnostic bypass target implausible")
    before_main[reloc_offset:reloc_offset + 2] = context._word(bypass_offset)
    before_main[bypass_offset:bypass_offset + 3] = phase1._jp(PASS_PC)
    _run_case(root, symbols, fixture, _diagnostic_mex(mex, bytes(before_main), user_image_size), user_image_size, arg, env, "original-entry-before-main-call")

    after_main = bytearray(user_image)
    after_main[reloc_offset + 2:reloc_offset + 5] = phase1._jp(PASS_PC)
    _run_case(root, symbols, fixture, _diagnostic_mex(mex, bytes(after_main), user_image_size), user_image_size, arg, env, "relocated-main-call-return")

    print("P2.08 POST-FRAME DIAGNOSTIC PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (DriverError, OSError, ValueError) as exc:
        print(f"P2.08 POST-FRAME DIAGNOSTIC FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
