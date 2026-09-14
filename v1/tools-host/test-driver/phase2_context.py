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
import struct
from typing import Any, Callable

from driver_core import DriverError
from fuse_harness import FAIL_PC, PASS_PC, run_sna
import phase1
import phase2_mex1

FIXTURE_CODE = 0xE000
PROGRAM_ADDRESS = 0x9000
TEST_STACK = 0xBFC0
MEX_ADDRESS = 0xC000
ARG_ADDRESS = 0xC400
ENV_ADDRESS = 0xC500
SEED_ADDRESS = 0xC600
RESULT_BASE = 0xC700
USER_SCRATCH = 0xC740
ARENA_START = 0x6000
FAST_START = 0x8000
FAST_END_EXCLUSIVE = 0xE000
CROSSING_BLOCKER_SIZE = 0x1FF0
ARG1_HEADER_SIZE = 8
ENV1_HEADER_SIZE = 8
MEX_MIN_STACK = 64
BOOTSTRAP_BYTES = 64
CONTEXT_FRAME_BYTES = 12
BSS_SIZE = 4

RESULT_IMAGE_BASE = RESULT_BASE + 0
RESULT_IMAGE_ALLOC = RESULT_BASE + 2
RESULT_STACK_BASE = RESULT_BASE + 4
RESULT_STACK_SIZE = RESULT_BASE + 6
RESULT_STACK_END = RESULT_BASE + 8
RESULT_ARG_PTR = RESULT_BASE + 10
RESULT_ARG_LEN = RESULT_BASE + 12
RESULT_ENV_PTR = RESULT_BASE + 14
RESULT_SAVED_SP = RESULT_BASE + 16


class Phase2ContextError(DriverError):
    """Raised when the P2.08 initial user-context contract regresses."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Phase2ContextError(message)


def _word(value: int) -> bytes:
    return bytes((value & 0xFF, (value >> 8) & 0xFF))


def _ld_ix(value: int) -> bytes:
    return b"\xDD\x21" + _word(value)


def _ld_iy(value: int) -> bytes:
    return b"\xFD\x21" + _word(value)


def _ld_bc(value: int) -> bytes:
    return b"\x01" + _word(value)


def _ld_a(value: int) -> bytes:
    return bytes((0x3E, value & 0xFF))


def _jp_nc(address: int) -> bytes:
    return b"\xD2" + _word(address)


def _ld_mem_hl(address: int) -> bytes:
    return b"\x22" + _word(address)


def _ld_hl_mem(address: int) -> bytes:
    return b"\x2A" + _word(address)


def _ld_mem_bc(address: int) -> bytes:
    return b"\xED\x43" + _word(address)


def _ld_mem_de(address: int) -> bytes:
    return b"\xED\x53" + _word(address)


def _ld_de_mem(address: int) -> bytes:
    return b"\xED\x5B" + _word(address)


def _ld_sp_mem(address: int) -> bytes:
    return b"\xED\x7B" + _word(address)


def _expect_hl(value: int) -> bytes:
    return phase1._ld_de(value) + b"\xB7\xED\x52" + phase1._jp_nz(FAIL_PC)


def _expect_word(address: int, value: int) -> bytes:
    return _ld_hl_mem(address) + _expect_hl(value)


def _expect_ix_word(offset: int, expected_address: int | None = None, expected_value: int | None = None) -> bytes:
    require((expected_address is None) != (expected_value is None), "P2.08 IX-word check needs exactly one expected source")
    code = bytearray(b"\xDD\x6E" + bytes((offset & 0xFF,)) + b"\xDD\x66" + bytes(((offset + 1) & 0xFF,)))
    if expected_address is not None:
        code += _ld_de_mem(expected_address)
    else:
        code += phase1._ld_de(int(expected_value))
    code += b"\xB7\xED\x52" + phase1._jp_nz(FAIL_PC)
    return bytes(code)


def _arg1(argument: bytes = b"x") -> bytes:
    payload = argument + b"\0"
    length = ARG1_HEADER_SIZE + len(payload)
    return b"ARG1" + bytes((1, 0)) + struct.pack("<H", length) + payload


def _env1() -> bytes:
    return b"ENV1" + bytes((0, 0)) + struct.pack("<H", ENV1_HEADER_SIZE)


def _patch(fixture: bytes, regions: tuple[tuple[int, bytes], ...]):
    def patch(ram: bytearray) -> None:
        start = FIXTURE_CODE - 0x4000
        ram[start:start + len(fixture)] = fixture
        for address, payload in regions:
            require(0x4000 <= address <= 0xFFFF, f"P2.08 patch address outside RAM: 0x{address:04X}")
            require(address + len(payload) <= 0x10000, f"P2.08 patch crosses address space: 0x{address:04X}")
            offset = address - 0x4000
            ram[offset:offset + len(payload)] = payload
    return patch


def _assemble_fixture(
    root: Path,
    run_command: Callable[..., Any],
    require_project_tool: Callable[[Path, str | Path], Path],
):
    assembler = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    source = build / "p208-context.asm"
    binary = build / "p208-context.bin"
    listing = build / "p208-context.lst"
    symbols = build / "p208-context.sym"
    source.write_text(
        "    DEVICE ZXSPECTRUM48\n"
        "    INCLUDE \"../include/zx48ux.inc\"\n"
        "    INCLUDE \"../include/mex1.inc\"\n"
        "    INCLUDE \"../src/kernel/memory.asm\"\n"
        "    INCLUDE \"../src/kernel/process.asm\"\n"
        f"    ORG ${FIXTURE_CODE:04X}\n"
        "p208_gateway:\n"
        "    cp SYS_EXIT\n"
        f"    jp nz,${FAIL_PC:04X}\n"
        "    ld a,h\n"
        "    or a\n"
        f"    jp nz,${FAIL_PC:04X}\n"
        "    ld a,l\n"
        "    or a\n"
        f"    jp nz,${FAIL_PC:04X}\n"
        f"    jp ${PASS_PC:04X}\n"
        "p208_context_start:\n"
        "    EMIT_MEMORY_ROUTINES\n"
        "    EMIT_MEX1_RELOCATION_ROUTINES\n"
        "    EMIT_MEX1_IMAGE_LOAD_ROUTINES\n"
        "    EMIT_MEX1_STACK_ROUTINES\n"
        "    EMIT_ENV1_ROUTINES\n"
        "    EMIT_INITIAL_CONTEXT_ROUTINES\n"
        "zx48_process_count:\n"
        "    xor a\n"
        "    ret\n"
        "p208_context_end:\n"
        "    SAVEBIN \"p208-context.bin\",p208_gateway,p208_context_end-p208_gateway\n",
        encoding="utf-8",
        newline="\n",
    )
    result = run_command(
        [assembler, "--nologo", "--lst=p208-context.lst", "--sym=p208-context.sym", "p208-context.asm"],
        cwd=build,
        timeout_seconds=30.0,
    )
    require(not result.timed_out and result.exit_code == 0, f"P2.08 context fixture assembly failed: {result.stderr or result.stdout}")
    require(binary.is_file() and 0 < binary.stat().st_size < 0x2000, "P2.08 context fixture binary missing or too large")
    require(symbols.is_file() and listing.is_file(), "P2.08 context fixture symbols/listing missing")
    return result, binary, symbols


def _assemble_user(
    root: Path,
    run_command: Callable[..., Any],
    require_project_tool: Callable[[Path, str | Path], Path],
):
    assembler = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    source = build / "p208-user.asm"
    binary = build / "p208-user.bin"
    listing = build / "p208-user.lst"
    symbols = build / "p208-user.sym"
    source.write_text(
        "    DEVICE ZXSPECTRUM48\n"
        "    INCLUDE \"../include/zx48ux.inc\"\n"
        "    ORG $6000\n"
        "p208_user_start:\n"
        "    or a\n"
        f"    jp nz,${FAIL_PC:04X}\n"
        f"    ld (${USER_SCRATCH:04X}),hl\n"
        f"    ld (${USER_SCRATCH + 2:04X}),de\n"
        f"    ld (${USER_SCRATCH + 4:04X}),bc\n"
        "    push iy\n"
        "    pop hl\n"
        f"    ld (${USER_SCRATCH + 6:04X}),hl\n"
        "    push ix\n"
        "    pop hl\n"
        f"    ld (${USER_SCRATCH + 8:04X}),hl\n"
        "    ld hl,0\n"
        "    add hl,sp\n"
        f"    ld (${USER_SCRATCH + 10:04X}),hl\n"
        f"    ld hl,(${USER_SCRATCH:04X})\n"
        f"    ld de,(${RESULT_ARG_PTR:04X})\n"
        "    or a\n"
        "    sbc hl,de\n"
        f"    jp nz,${FAIL_PC:04X}\n"
        f"    ld hl,(${USER_SCRATCH + 2:04X})\n"
        f"    ld de,(${RESULT_ENV_PTR:04X})\n"
        "    or a\n"
        "    sbc hl,de\n"
        f"    jp nz,${FAIL_PC:04X}\n"
        f"    ld hl,(${USER_SCRATCH + 4:04X})\n"
        f"    ld de,(${RESULT_ARG_LEN:04X})\n"
        "    or a\n"
        "    sbc hl,de\n"
        f"    jp nz,${FAIL_PC:04X}\n"
        f"    ld hl,(${USER_SCRATCH + 6:04X})\n"
        "    ld de,ROM_IY_ANCHOR\n"
        "    or a\n"
        "    sbc hl,de\n"
        f"    jp nz,${FAIL_PC:04X}\n"
        f"    ld hl,(${USER_SCRATCH + 8:04X})\n"
        "    ld de,0\n"
        "    or a\n"
        "    sbc hl,de\n"
        f"    jp nz,${FAIL_PC:04X}\n"
        f"    ld hl,(${USER_SCRATCH + 10:04X})\n"
        f"    ld de,(${RESULT_STACK_END:04X})\n"
        "    or a\n"
        "    sbc hl,de\n"
        f"    jp nz,${FAIL_PC:04X}\n"
        "    db $CD\n"
        "p208_main_call_word:\n"
        "    dw p208_main-p208_user_start\n"
        "    ld hl,0\n"
        "    ld a,SYS_EXIT\n"
        "    call SYSCALL_GATEWAY\n"
        f"    jp ${FAIL_PC:04X}\n"
        "p208_main:\n"
        "    ret\n"
        "p208_user_end:\n"
        "    SAVEBIN \"p208-user.bin\",p208_user_start,p208_user_end-p208_user_start\n",
        encoding="utf-8",
        newline="\n",
    )
    result = run_command(
        [assembler, "--nologo", "--lst=p208-user.lst", "--sym=p208-user.sym", "p208-user.asm"],
        cwd=build,
        timeout_seconds=30.0,
    )
    require(not result.timed_out and result.exit_code == 0, f"P2.08 user fixture assembly failed: {result.stderr or result.stdout}")
    require(binary.is_file() and 0 < binary.stat().st_size < 512, "P2.08 user fixture binary missing or implausibly large")
    require(symbols.is_file() and listing.is_file(), "P2.08 user fixture symbols/listing missing")
    return result, binary, symbols


def _symbols(path: Path, names: tuple[str, ...]) -> dict[str, int]:
    text = path.read_text(encoding="utf-8", errors="replace")
    found: dict[str, int] = {}
    for name in names:
        pattern = re.compile(rf"^{re.escape(name)}:\s+equ\s+0x([0-9A-Fa-f]+)\s*$", re.IGNORECASE)
        for line in text.splitlines():
            match = pattern.match(line.strip())
            if match is not None:
                found[name] = int(match.group(1), 16)
                break
        require(name in found, f"P2.08 fixture symbol missing: {name}")
    return found


def _seed(image_base: int, stack_base: int, stack_size: int, arg_ptr: int, arg_len: int, env_ptr: int) -> bytes:
    return b"".join(_word(value) for value in (image_base, stack_base, stack_size, arg_ptr, arg_len, env_ptr))


def _copy_result_word_to_seed(result_address: int, seed_address: int) -> bytes:
    return _ld_hl_mem(result_address) + _ld_mem_hl(seed_address)


def _check_bss_zero(image_size: int, bss_size: int, program_address: int) -> bytes:
    code = bytearray(_ld_hl_mem(RESULT_IMAGE_BASE) + phase1._ld_de(image_size) + b"\x19" + bytes((0x06, bss_size & 0xFF)))
    loop = program_address + len(code)
    code += b"\x7E\xB7" + phase1._jp_nz(FAIL_PC) + b"\x23\x05" + phase1._jp_nz(loop)
    return bytes(code)


def _frame_checks() -> bytes:
    code = bytearray(_ld_hl_mem(RESULT_SAVED_SP) + b"\xE5\xDD\xE1")
    code += _expect_ix_word(0, expected_value=0)
    code += _expect_ix_word(2, expected_address=RESULT_ARG_PTR)
    code += _expect_ix_word(4, expected_address=RESULT_ENV_PTR)
    code += _expect_ix_word(6, expected_address=RESULT_ARG_LEN)
    code += _expect_ix_word(8, expected_value=0)
    code += _expect_ix_word(10, expected_address=RESULT_IMAGE_BASE)
    return bytes(code)


def _first_dispatch_case(
    root: Path,
    symbols: dict[str, int],
    fixture: bytes,
    mex: bytes,
    user_image_size: int,
    arg: bytes,
    env: bytes,
    *,
    crossing: bool,
    canonicalize_iy: bool = True,
    expect_failure: bool = False,
) -> None:
    memory_init = symbols["zx48_memory_init"]
    alloc = symbols["zx48_alloc"]
    load_image = symbols["zx48_mex1_load_image"]
    alloc_stack = symbols["zx48_mex1_alloc_stack"]
    build_bootstrap = symbols["zx48_env1_build"]
    build_context = symbols["zx48_process_build_initial_context"]
    live_count = symbols["memory_live_allocations"]
    expected_image_base = ARENA_START + (CROSSING_BLOCKER_SIZE if crossing else 0)
    stack_total = MEX_MIN_STACK + BOOTSTRAP_BYTES
    expected_stack_base = FAST_END_EXCLUSIVE - stack_total
    expected_live = 4 if crossing else 3

    code = bytearray(b"\xF3" + phase1._ld_sp(TEST_STACK))
    code += phase1._call(memory_init)
    if crossing:
        code += _ld_a(symbols["ALLOC_ANY"]) + _ld_bc(CROSSING_BLOCKER_SIZE) + phase1._call(alloc) + phase1._jp_c(FAIL_PC)
        code += _expect_hl(ARENA_START)

    code += _ld_ix(MEX_ADDRESS) + phase1._call(load_image) + phase1._jp_c(FAIL_PC)
    code += _ld_mem_hl(RESULT_IMAGE_BASE) + _ld_mem_bc(RESULT_IMAGE_ALLOC)
    code += _expect_word(RESULT_IMAGE_BASE, expected_image_base)
    code += _check_bss_zero(user_image_size, BSS_SIZE, PROGRAM_ADDRESS + len(code))

    code += _ld_ix(MEX_ADDRESS) + phase1._call(alloc_stack) + phase1._jp_c(FAIL_PC)
    code += _ld_mem_hl(RESULT_STACK_BASE) + _ld_mem_bc(RESULT_STACK_SIZE)
    code += _expect_word(RESULT_STACK_BASE, expected_stack_base)
    code += _expect_word(RESULT_STACK_SIZE, stack_total)
    code += _ld_hl_mem(RESULT_STACK_BASE) + b"\x09" + _ld_mem_hl(RESULT_STACK_END)
    code += _expect_word(RESULT_STACK_END, FAST_END_EXCLUSIVE)

    code += _ld_ix(ARG_ADDRESS) + _ld_bc(len(arg)) + phase1._ld_hl(ENV_ADDRESS) + phase1._ld_de(len(env)) + phase1._call(build_bootstrap) + phase1._jp_c(FAIL_PC)
    code += _ld_mem_hl(RESULT_ARG_PTR) + _ld_mem_bc(RESULT_ARG_LEN) + _ld_mem_de(RESULT_ENV_PTR)
    code += _expect_word(RESULT_ARG_LEN, len(arg))

    code += _copy_result_word_to_seed(RESULT_IMAGE_BASE, SEED_ADDRESS + 0)
    code += _copy_result_word_to_seed(RESULT_STACK_BASE, SEED_ADDRESS + 2)
    code += _copy_result_word_to_seed(RESULT_STACK_SIZE, SEED_ADDRESS + 4)
    code += _copy_result_word_to_seed(RESULT_ARG_PTR, SEED_ADDRESS + 6)
    code += _copy_result_word_to_seed(RESULT_ARG_LEN, SEED_ADDRESS + 8)
    code += _copy_result_word_to_seed(RESULT_ENV_PTR, SEED_ADDRESS + 10)

    code += _ld_ix(MEX_ADDRESS) + phase1._ld_hl(SEED_ADDRESS) + phase1._call(build_context) + phase1._jp_c(FAIL_PC)
    code += _ld_mem_hl(RESULT_SAVED_SP)
    code += _ld_hl_mem(RESULT_STACK_END) + phase1._ld_de(CONTEXT_FRAME_BYTES) + b"\xB7\xED\x52" + _ld_de_mem(RESULT_SAVED_SP) + b"\xB7\xED\x52" + phase1._jp_nz(FAIL_PC)
    code += _expect_word(live_count, expected_live)
    code += _frame_checks()

    # The frozen scheduler restore path is emulated byte-for-byte here. Dirty IY
    # is intentional: the canonicalization immediately before RET is observable
    # at the first MEX1 instruction and the user fixture rejects any other value.
    code += _ld_iy(0x9999) + _ld_sp_mem(RESULT_SAVED_SP)
    code += b"\xDD\xE1\xE1\xD1\xC1\xF1"
    if canonicalize_iy:
        code += _ld_iy(symbols["ROM_IY_ANCHOR"])
    code += b"\xC9"

    if crossing:
        image_alloc = (user_image_size + BSS_SIZE + 1) & ~1
        require(expected_image_base < FAST_START < expected_image_base + image_alloc, "P2.08 crossing fixture no longer crosses 0x7FFF/0x8000")

    if expect_failure:
        try:
            run_sna(
                root,
                bytes(code),
                patch=_patch(fixture, ((MEX_ADDRESS, mex), (ARG_ADDRESS, arg), (ENV_ADDRESS, env))),
            )
        except DriverError as exc:
            require("exit=1 timed_out=False" in str(exc), f"P2.08 dirty-IY negative failed for an unexpected reason: {exc}")
        else:
            raise Phase2ContextError("P2.08 dirty-IY restore unexpectedly reached PASS without canonicalization")
        return

    run_sna(
        root,
        bytes(code),
        patch=_patch(fixture, ((MEX_ADDRESS, mex), (ARG_ADDRESS, arg), (ENV_ADDRESS, env))),
    )


def _nonzero_entry_case(root: Path, symbols: dict[str, int], fixture: bytes, mex: bytes, entry_offset: int) -> None:
    builder = symbols["zx48_process_build_initial_context"]
    stack_size = MEX_MIN_STACK + BOOTSTRAP_BYTES
    stack_base = FAST_START
    expected_saved_sp = stack_base + stack_size - CONTEXT_FRAME_BYTES
    seed = _seed(ARENA_START, stack_base, stack_size, 0x6100, 10, 0x610A)

    code = bytearray(b"\xF3" + phase1._ld_sp(TEST_STACK))
    code += _ld_ix(MEX_ADDRESS) + phase1._ld_hl(SEED_ADDRESS) + phase1._call(builder) + phase1._jp_c(FAIL_PC)
    code += _expect_hl(expected_saved_sp)
    code += b"\xE5\xDD\xE1"
    code += _expect_ix_word(10, expected_value=ARENA_START + entry_offset)
    code += phase1._jp(PASS_PC)
    run_sna(root, bytes(code), patch=_patch(fixture, ((MEX_ADDRESS, mex), (SEED_ADDRESS, seed))))


def _invalid_seed_case(root: Path, symbols: dict[str, int], fixture: bytes, mex: bytes) -> None:
    builder = symbols["zx48_process_build_initial_context"]
    e_format = symbols["E_FORMAT"]
    bad_stack_size = MEX_MIN_STACK + BOOTSTRAP_BYTES - 2
    frame_candidate = FAST_START + bad_stack_size - CONTEXT_FRAME_BYTES
    canary = bytes((0xA5,)) * CONTEXT_FRAME_BYTES
    seed = _seed(ARENA_START, FAST_START, bad_stack_size, 0x6100, 10, 0x610A)

    code = bytearray(b"\xF3" + phase1._ld_sp(TEST_STACK))
    code += _ld_ix(MEX_ADDRESS) + phase1._ld_hl(SEED_ADDRESS) + phase1._call(builder) + _jp_nc(FAIL_PC)
    code += bytes((0xFE, e_format & 0xFF)) + phase1._jp_nz(FAIL_PC)
    code += phase1._ld_hl(frame_candidate) + phase1._ld_de(USER_SCRATCH) + _ld_bc(CONTEXT_FRAME_BYTES)
    loop = PROGRAM_ADDRESS + len(code)
    code += b"\x1A\xBE" + phase1._jp_nz(FAIL_PC) + b"\x23\x13\x0B\x78\xB1" + phase1._jp_nz(loop)
    code += phase1._jp(PASS_PC)
    run_sna(root, bytes(code), patch=_patch(fixture, ((MEX_ADDRESS, mex), (SEED_ADDRESS, seed), (frame_candidate, canary), (USER_SCRATCH, canary))))


def _target_tests(root: Path, symbols: dict[str, int], fixture: bytes, mex: bytes, user_image: bytes) -> list[dict[str, object]]:
    require(symbols["ALLOC_ANY"] == 0, "P2.08 ALLOC_ANY ABI value changed")
    require(symbols["ALLOC_FAST_REQUIRED"] == 1, "P2.08 ALLOC_FAST_REQUIRED ABI value changed")
    require(symbols["E_FORMAT"] == 0x0B, "P2.08 E_FORMAT ABI value changed")
    require(symbols["ROM_IY_ANCHOR"] == 0x5C3A, "P2.08 canonical IY anchor changed")
    require(symbols["PROCESS_STACK_BOOTSTRAP_BYTES"] == BOOTSTRAP_BYTES, "P2.08 stack bootstrap reserve changed")
    require(symbols["PROCESS_CONTEXT_FRAME_BYTES"] == CONTEXT_FRAME_BYTES, "P2.08 context frame size changed")
    require(symbols["INITIAL_CONTEXT_SEED_SIZE"] == 12, "P2.08 context seed size changed")

    arg = _arg1()
    env = _env1()
    user_image_size = len(user_image)
    _first_dispatch_case(root, symbols, fixture, mex, user_image_size, arg, env, crossing=False)
    _first_dispatch_case(root, symbols, fixture, mex, user_image_size, arg, env, crossing=True)
    _first_dispatch_case(
        root, symbols, fixture, mex, user_image_size, arg, env,
        crossing=False, canonicalize_iy=False, expect_failure=True,
    )
    nonzero_entry = 3
    nonzero_mex = phase2_mex1._fixture(
        image=user_image,
        bss_size=BSS_SIZE,
        entry=nonzero_entry,
        stack=MEX_MIN_STACK,
        relocations=(),
    )
    _nonzero_entry_case(root, symbols, fixture, nonzero_mex, nonzero_entry)
    _invalid_seed_case(root, symbols, fixture, mex)

    return [
        {"name": "first-dispatch-enters-mex1-with-exact-hl-bc-de-a-register-contract", "passed": True},
        {"name": "dirty-pre-dispatch-iy-is-canonicalized-to-5c3a-before-first-instruction", "passed": True},
        {"name": "omitting-iy-canonicalization-fails-the-first-instruction-oracle", "passed": True},
        {"name": "nonzero-mex-entry-offset-is-added-to-the-actual-image-base-in-frame-pc", "passed": True},
        {"name": "initial-saved-sp-frame-is-exact-ix-hl-de-bc-af-pc-and-consumes-twelve-bytes", "passed": True},
        {"name": "minimum-fast-stack-retains-separate-fixed-64-byte-bootstrap-reserve", "passed": True, "advertised": MEX_MIN_STACK, "allocated": MEX_MIN_STACK + BOOTSTRAP_BYTES},
        {"name": "image-load-bss-zero-stack-bootstrap-and-context-construction-occur-in-prerequisite-order", "passed": True},
        {"name": "any-image-can-cross-7fff-8000-while-process-stack-remains-fast-required", "passed": True},
        {"name": "plain-return-from-synthetic-c48-entry-path-reaches-sys-exit-gateway", "passed": True},
        {"name": "invalid-context-seed-is-rejected-before-target-stack-frame-write", "passed": True},
    ]


def _source_contract(root: Path) -> list[dict[str, object]]:
    process = (root / "v1/src/kernel/process.asm").read_text(encoding="utf-8")
    kernel = (root / "v1/src/kernel/kernel.asm").read_text(encoding="utf-8")
    scheduler = (root / "v1/src/kernel/scheduler.asm").read_text(encoding="utf-8")
    start = process.index("    MACRO EMIT_INITIAL_CONTEXT_ROUTINES")
    routine = process[start:]
    end = routine.index("    ENDM\n")
    routine = routine[:end]
    resident_end = process.index("    ENDM\n", process.index("    MACRO EMIT_PROCESS_ROUTINES"))
    write_at = routine.index("zx48_initial_context_write:")
    before_write = routine[:write_at]
    restore = scheduler[scheduler.index("zx48_schedule_not_cancelled:"):scheduler.index("zx48_schedule_idle_restore:")]
    routine_code = "\n".join(line.split(";", 1)[0] for line in routine.splitlines())
    frame_tokens = (
        "ld de,(process_context_arg_ptr)",
        "ld de,(process_context_env_ptr)",
        "ld de,(process_context_arg_len)",
        "ld de,(process_context_entry)",
    )
    return [
        {"name": "initial-context-routines-remain-staged-outside-resident-process-macro", "passed": resident_end < start},
        {"name": "production-kernel-does-not-prematurely-emit-p208-helper", "passed": "EMIT_INITIAL_CONTEXT_ROUTINES" not in kernel},
        {"name": "initial-context-frame-size-is-exactly-twelve-bytes", "passed": "PROCESS_CONTEXT_FRAME_BYTES   EQU 12" in process},
        {"name": "fixed-64-bootstrap-reserve-covers-frame-plus-seventeen-pointer-vector", "passed": CONTEXT_FRAME_BYTES + 17 * 2 <= BOOTSTRAP_BYTES and "PROCESS_STACK_BOOTSTRAP_BYTES EQU 64" in process},
        {"name": "context-constructor-revalidates-image-entry-and-fast-stack-bounds", "passed": all(token in before_write for token in ("MEX_HDR_IMAGE_SIZE", "MEX_HDR_BSS_SIZE", "MEX_HDR_ENTRY", "ARENA_START", "KERNEL_START", "MEX_HDR_STACK", "MEX_MIN_STACK", "MEX_MAX_STACK", "FAST_START", "PROCESS_STACK_BOOTSTRAP_BYTES"))},
        {"name": "context-constructor-requires-contiguous-arg1-then-env1-pointer-shape", "passed": all(token in before_write for token in ("process_context_arg_ptr", "process_context_arg_len", "process_context_env_ptr", "add hl,bc"))},
        {"name": "context-constructor-completes-validation-before-first-target-stack-write", "passed": "ld (process_context_saved_sp),hl" in before_write and "ld (hl),a" not in before_write},
        {"name": "context-constructor-materializes-exact-entry-register-frame", "passed": all(token in routine[write_at:] for token in frame_tokens) and routine[write_at:].count("ld (hl),a") >= 4},
        {"name": "context-constructor-does-not-allocate-or-publish-process-state", "passed": all(token not in routine for token in ("zx48_alloc", "zx48_free", "PROC_STATE", "PROC_READY", "PROC_SAVED_SP", "process_table"))},
        {"name": "context-constructor-does-not-use-iy-or-alternate-register-bank", "passed": re.search(r"(?im)^\s*(?:ld\s+iy|push\s+iy|pop\s+iy|exx|ex\s+af)", routine_code) is None},
        {"name": "scheduler-restore-order-matches-frame-and-canonicalizes-iy-before-ret", "passed": all(token in restore for token in ("pop ix", "pop hl", "pop de", "pop bc", "pop af", "ld iy,ROM_IY_ANCHOR", "ret")) and restore.index("pop ix") < restore.index("pop hl") < restore.index("pop de") < restore.index("pop bc") < restore.index("pop af") < restore.index("ld iy,ROM_IY_ANCHOR") < restore.index("ret")},
        {"name": "context-constructor-returns-only-unpublished-saved-sp", "passed": "ld hl,(process_context_saved_sp)" in routine[write_at:] and "xor a\n    ret" in routine[write_at:]},
    ]


def dispatch(
    root: Path,
    action: str,
    step: str,
    *,
    sha256_file: Callable[[Path], str],
    run_command: Callable[..., Any],
    require_project_tool: Callable[[Path, str | Path], Path],
):
    if step != "P2.08":
        raise DriverError(f"Phase-2 context step is not registered: {step}")

    assertions = _source_contract(root)
    failed = [item["name"] for item in assertions if item["passed"] is not True]
    require(not failed, f"static P2.08 contract failures: {failed}")

    fixture_command, fixture_binary, fixture_symbols = _assemble_fixture(root, run_command, require_project_tool)
    user_command, user_binary, user_symbols = _assemble_user(root, run_command, require_project_tool)
    user_symbol_values = _symbols(user_symbols, ("p208_user_start", "p208_main_call_word"))
    user_image = user_binary.read_bytes()
    reloc_offset = user_symbol_values["p208_main_call_word"] - user_symbol_values["p208_user_start"]
    require(0 <= reloc_offset <= len(user_image) - 2, "P2.08 user relocation word outside image")
    mex = phase2_mex1._fixture(
        image=user_image,
        bss_size=BSS_SIZE,
        entry=0,
        stack=MEX_MIN_STACK,
        relocations=(reloc_offset,),
    )
    mex_path = root / "v1/build/p208-user.mex"
    mex_path.write_bytes(mex)

    symbol_names = (
        "zx48_memory_init",
        "zx48_alloc",
        "zx48_mex1_load_image",
        "zx48_mex1_alloc_stack",
        "zx48_env1_build",
        "zx48_process_build_initial_context",
        "memory_live_allocations",
        "ALLOC_ANY",
        "ALLOC_FAST_REQUIRED",
        "E_FORMAT",
        "ROM_IY_ANCHOR",
        "PROCESS_STACK_BOOTSTRAP_BYTES",
        "PROCESS_CONTEXT_FRAME_BYTES",
        "INITIAL_CONTEXT_SEED_SIZE",
    )
    symbols = _symbols(fixture_symbols, symbol_names)
    fixture = fixture_binary.read_bytes()
    if action == "test":
        assertions.extend(_target_tests(root, symbols, fixture, mex, user_image))

    return [fixture_command, user_command], {
        "v1/build/p208-context.bin": sha256_file(fixture_binary),
        "v1/build/p208-user.bin": sha256_file(user_binary),
        "v1/build/p208-user.mex": sha256_file(mex_path),
        "v1/src/kernel/process.asm": sha256_file(root / "v1/src/kernel/process.asm"),
        "v1/src/kernel/scheduler.asm": sha256_file(root / "v1/src/kernel/scheduler.asm"),
        "v1/tools-host/test-driver/phase2_context.py": sha256_file(root / "v1/tools-host/test-driver/phase2_context.py"),
    }, assertions
