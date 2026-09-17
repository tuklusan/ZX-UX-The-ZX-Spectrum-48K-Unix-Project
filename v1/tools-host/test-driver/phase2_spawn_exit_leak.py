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
import phase2_spawn_atomic

FIXTURE_SOURCE = Path("v1/tests/multiprocessing/p222-spawn-exit-leak.asm")
FIXTURE_CODE = 0xE000
PROGRAM_ADDRESS = 0x9000
TEST_STACK = 0x8F00
PROC_ADDRESS = 0xA300
GOOD_PATH_ADDRESS = 0xA000
ARG_ADDRESS = 0xA100
ENV_ADDRESS = 0xA200
GOOD_RECORD = 0xB000
GOOD_MEX = 0xC000
MIRROR_BASE = 0xC800

PROC_DESC_SIZE = 48
PROCESS_COUNT = 8
PROC_PARENT = 1
PROC_STATE = 2
PROC_HANDLES = 16
PROC_CWD = 28
PROC_RUNNING = 2
HANDLE_FREE = 0xFF
OD_SIZE = 8
OD_COUNT = 24
FREE_EXTENT_BYTES = 64
STRESS_WAVES = 64
CHILDREN_PER_WAVE = 6
EXPECTED_CYCLES = STRESS_WAVES * CHILDREN_PER_WAVE


class Phase222Error(DriverError):
    """Raised when the P2.22 repeated spawn/exit accounting contract regresses."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Phase222Error(message)


def _word(value: int) -> bytes:
    return bytes((value & 0xFF, (value >> 8) & 0xFF))


def _jp_c(address: int) -> bytes:
    return b"\xDA" + _word(address)


def _jp_nz(address: int) -> bytes:
    return b"\xC2" + _word(address)


def _symbols(path: Path, names: tuple[str, ...]) -> dict[str, int]:
    text = path.read_text(encoding="utf-8", errors="replace")
    found: dict[str, int] = {}
    for name in names:
        pattern = re.compile(
            rf"^{re.escape(name)}:\s+equ\s+0x([0-9A-Fa-f]+)\s*$",
            re.IGNORECASE | re.MULTILINE,
        )
        match = pattern.search(text)
        require(match is not None, f"P2.22 symbol missing from assembler output: {name}")
        found[name] = int(match.group(1), 16)
    return found


def _macro(text: str, name: str) -> str:
    marker = f"    MACRO {name}"
    start = text.index(marker)
    end = text.index("    ENDM\n", start)
    return text[start:end]


def _source_contract(root: Path) -> list[dict[str, object]]:
    process = (root / "v1/src/kernel/process.asm").read_text(encoding="utf-8")
    memory = (root / "v1/src/kernel/memory.asm").read_text(encoding="utf-8")
    handles = (root / "v1/src/kernel/handles.asm").read_text(encoding="utf-8")
    fixture = (root / FIXTURE_SOURCE).read_text(encoding="utf-8")

    spawn = _macro(process, "EMIT_SPAWN_TRANSACTION_ROUTINES")
    zombie = _macro(process, "EMIT_ZOMBIE_TRANSITION_ROUTINES")
    wait_specific = _macro(process, "EMIT_WAIT_SPECIFIC_ROUTINES")
    allocator = _macro(memory, "EMIT_MEMORY_ROUTINES")
    handle_routines = _macro(handles, "EMIT_HANDLE_ROUTINES")

    return [
        {
            "name": "stress-fixture-runs-64-waves-over-all-six-spawnable-pid-slots",
            "passed": "ld a,64" in fixture
            and all(f"cp {pid}" in fixture for pid in range(2, 8))
            and fixture.count("call p222_exit_reap") == CHILDREN_PER_WAVE,
            "waves": STRESS_WAVES,
            "cycles": EXPECTED_CYCLES,
        },
        {
            "name": "stress-fixture-composes-real-spawn-parent-link-zombie-and-specific-reap-routines",
            "passed": all(
                token in fixture
                for token in (
                    "EMIT_SPAWN_TRANSACTION_ROUTINES",
                    "EMIT_PARENT_CHILD_ROUTINES",
                    "EMIT_ZOMBIE_TRANSITION_ROUTINES",
                    "EMIT_WAIT_SPECIFIC_ROUTINES",
                    "call zx48_process_exit_to_zombie",
                    "call zx48_process_wait_specific",
                )
            ),
        },
        {
            "name": "spawn-transaction-owns-image-stack-bootstrap-and-three-inherited-handle-retains",
            "passed": spawn.count("call zx48_alloc") >= 3
            and "process_spawn_retained" in spawn
            and "call zx48_od_retain" in spawn,
        },
        {
            "name": "zombie-transition-closes-handles-and-frees-all-three-private-allocation-classes",
            "passed": "call zx48_handles_close_all_current" in zombie
            and zombie.count("call zx48_free") >= 3
            and all(
                token in zombie
                for token in (
                    "PROC_IMAGE_BASE",
                    "PROC_STACK_LOW",
                    "PROC_ARG_PTR",
                    "PROC_OWNED_BYTES",
                )
            ),
        },
        {
            "name": "specific-wait-reap-unlinks-generation-identity-and-clears-descriptor",
            "passed": "zx48_process_wait_specific_release:" in wait_specific
            and "call zx48_process_unlink_child" in wait_specific
            and "ld bc,PROC_DESC_SIZE-1" in wait_specific
            and "ldir" in wait_specific,
        },
        {
            "name": "allocator-exposes-exact-live-allocation-count-and-free-extent-accounting",
            "passed": "memory_live_allocations" in allocator
            and "memory_free_extents" in allocator
            and "zx48_free:" in allocator,
        },
        {
            "name": "handle-close-final-reference-accounting-is-owned-by-production-handle-routines",
            "passed": "zx48_handle_close:" in handle_routines
            and "zx48_od_release:" in handle_routines
            and "open_description_table" in handle_routines,
        },
    ]


def _assemble_fixture(
    root: Path,
    run_command: Callable[..., Any],
    require_project_tool: Callable[[Path, str | Path], Path],
):
    assembler = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    source = root / FIXTURE_SOURCE
    binary = build / "p222-spawn-exit-leak.bin"
    symbols = build / "p222-spawn-exit-leak.sym"
    result = run_command(
        [assembler, "--nologo", "--sym=../../build/p222-spawn-exit-leak.sym", source.name],
        cwd=source.parent,
        timeout_seconds=30.0,
    )
    require(
        not result.timed_out and result.exit_code == 0,
        f"P2.22 stress fixture assembly failed: {result.stderr or result.stdout}",
    )
    require(binary.is_file() and 0 < binary.stat().st_size <= 0x1D00, "P2.22 fixture missing or overlaps FAST reserve")
    require(symbols.is_file(), "P2.22 fixture symbols missing")
    return result, binary, symbols


def _process_table() -> bytes:
    table = bytearray(PROCESS_COUNT * PROC_DESC_SIZE)
    for pid in range(PROCESS_COUNT):
        base = pid * PROC_DESC_SIZE
        table[base] = pid
        table[base + PROC_PARENT] = HANDLE_FREE
        table[base + PROC_HANDLES : base + PROC_HANDLES + 8] = bytes((HANDLE_FREE,)) * 8

    p0 = 0
    table[p0 + PROC_STATE] = PROC_RUNNING

    p1 = PROC_DESC_SIZE
    table[p1 + PROC_PARENT] = 0
    table[p1 + PROC_STATE] = PROC_RUNNING
    table[p1 + PROC_HANDLES : p1 + PROC_HANDLES + 8] = bytes(
        (0, 1, 1, HANDLE_FREE, HANDLE_FREE, HANDLE_FREE, HANDLE_FREE, HANDLE_FREE)
    )
    table[p1 + PROC_CWD] = 6
    return bytes(table)


def _open_descriptions() -> bytes:
    data = bytearray(OD_COUNT * OD_SIZE)
    data[0] = 1
    data[1] = 1
    data[2] = 1
    base = OD_SIZE
    data[base + 0] = 1
    data[base + 1] = 2
    data[base + 2] = 2
    return bytes(data)


def _free_extents() -> bytes:
    data = bytearray(FREE_EXTENT_BYTES)
    struct.pack_into("<HH", data, 0, 0x6000, 0x8000)
    return bytes(data)


def _proc1() -> bytes:
    arg = phase2_spawn_atomic._arg1(b"/bin/good")
    return phase2_spawn_atomic._proc1(
        path_ptr=GOOD_PATH_ADDRESS,
        arg_ptr=ARG_ADDRESS,
        arg_len=len(arg),
        env_ptr=ENV_ADDRESS,
        env_len=len(phase2_spawn_atomic.ENV1_EMPTY),
    )


def _regions(symbols: dict[str, int]) -> tuple[tuple[int, bytes], ...]:
    good = phase2_spawn_atomic._mex()
    arg = phase2_spawn_atomic._arg1(b"/bin/good")
    return (
        (GOOD_PATH_ADDRESS, b"/bin/good\0"),
        (ARG_ADDRESS, arg),
        (ENV_ADDRESS, phase2_spawn_atomic.ENV1_EMPTY),
        (PROC_ADDRESS, _proc1()),
        (GOOD_MEX, good),
        (GOOD_RECORD, phase2_spawn_atomic._record(b"good", 2, GOOD_MEX, len(good))),
        (symbols["process_table"], _process_table()),
        (symbols["current_pid"], b"\x01"),
        (symbols["open_description_table"], _open_descriptions()),
        (symbols["memory_free_extents"], _free_extents()),
        (symbols["memory_live_allocations"], b"\x00\x00"),
        (symbols["tty_input_owner"], b"\x01"),
    )


def _patch(fixture: bytes, regions: tuple[tuple[int, bytes], ...]):
    def patch(ram: bytearray) -> None:
        start = FIXTURE_CODE - 0x4000
        ram[start : start + len(fixture)] = fixture
        for address, payload in regions:
            require(0x4000 <= address < 0x10000, f"P2.22 patch address outside RAM: 0x{address:04X}")
            require(address + len(payload) <= 0x10000, f"P2.22 patch crosses RAM: 0x{address:04X}")
            offset = address - 0x4000
            ram[offset : offset + len(payload)] = payload

    return patch


def _append_compare(code: bytearray, actual: int, expected: int, length: int) -> None:
    code += phase1._ld_hl(actual) + phase1._ld_de(expected) + b"\x01" + _word(length)
    loop = PROGRAM_ADDRESS + len(code)
    code += b"\x1A\xBE" + _jp_nz(FAIL_PC) + b"\x23\x13\x0B\x78\xB1" + _jp_nz(loop)


def _expect_byte(address: int, value: int) -> bytes:
    return b"\x3A" + _word(address) + bytes((0xFE, value & 0xFF)) + _jp_nz(FAIL_PC)


def _expect_word(address: int, value: int) -> bytes:
    return _expect_byte(address, value & 0xFF) + _expect_byte(address + 1, (value >> 8) & 0xFF)


def _accounting_oracle(code: bytearray, symbols: dict[str, int], *, mirrors: bool) -> tuple[tuple[int, bytes], ...]:
    free = _free_extents()
    ods = _open_descriptions()
    parent = _process_table()[PROC_DESC_SIZE : 2 * PROC_DESC_SIZE]

    free_mirror = MIRROR_BASE
    od_mirror = free_mirror + len(free)
    parent_mirror = od_mirror + len(ods)

    _append_compare(code, symbols["memory_free_extents"], free_mirror, len(free))
    _append_compare(code, symbols["open_description_table"], od_mirror, len(ods))
    _append_compare(code, symbols["process_table"] + PROC_DESC_SIZE, parent_mirror, len(parent))
    code += _expect_word(symbols["memory_live_allocations"], 0)
    code += _expect_byte(symbols["current_pid"], 1)
    code += _expect_byte(symbols["p222_panic_code"], 0)
    for pid in range(2, 8):
        code += _expect_byte(symbols["process_table"] + pid * PROC_DESC_SIZE + PROC_STATE, 0)

    if not mirrors:
        return ()
    return ((free_mirror, free), (od_mirror, ods), (parent_mirror, parent))


def _positive_base(symbols: dict[str, int]) -> bytearray:
    code = bytearray(b"\xF3" + phase1._ld_sp(TEST_STACK))
    code += phase1._call(symbols["p222_stress"]) + _jp_c(FAIL_PC)
    return code


def _run_positive_probe(
    root: Path,
    symbols: dict[str, int],
    fixture: bytes,
    label: str,
    code: bytearray,
    extra_regions: tuple[tuple[int, bytes], ...] = (),
) -> None:
    probe = bytearray(code)
    probe += phase1._jp(PASS_PC)
    try:
        run_sna(
            root,
            bytes(probe),
            patch=_patch(fixture, _regions(symbols) + extra_regions),
            timeout=30.0,
        )
    except DriverError as exc:
        raise Phase222Error(f"P2.22 positive diagnostic failed at {label}: {exc}") from exc


def _diagnose_positive_failure(
    root: Path,
    symbols: dict[str, int],
    fixture: bytes,
    original: DriverError,
) -> None:
    code = bytearray(b"\xF3" + phase1._ld_sp(TEST_STACK))
    code += phase1._call(symbols["zx48_process_links_init"]) + _jp_c(FAIL_PC)
    _run_positive_probe(root, symbols, fixture, "process-links-init", code)

    for last_pid in range(2, 8):
        code = bytearray(b"\xF3" + phase1._ld_sp(TEST_STACK))
        code += phase1._call(symbols["zx48_process_links_init"]) + _jp_c(FAIL_PC)
        for pid in range(2, last_pid + 1):
            code += phase1._ld_hl(PROC_ADDRESS) + phase1._call(symbols["p222_gateway"]) + _jp_c(FAIL_PC)
            code += b"\x7C\xB7" + _jp_nz(FAIL_PC)
            code += b"\x7D\xFE" + bytes((pid,)) + _jp_nz(FAIL_PC)
        _run_positive_probe(root, symbols, fixture, f"spawns-through-pid{last_pid}", code)

    for last_pid in range(2, 8):
        code = bytearray(b"\xF3" + phase1._ld_sp(TEST_STACK))
        code += phase1._call(symbols["zx48_process_links_init"]) + _jp_c(FAIL_PC)
        for pid in range(2, 8):
            code += phase1._ld_hl(PROC_ADDRESS) + phase1._call(symbols["p222_gateway"]) + _jp_c(FAIL_PC)
            code += b"\x7C\xB7" + _jp_nz(FAIL_PC)
            code += b"\x7D\xFE" + bytes((pid,)) + _jp_nz(FAIL_PC)
        for pid in range(2, last_pid + 1):
            code += b"\x3E" + bytes((pid,)) + phase1._call(symbols["p222_exit_reap"]) + _jp_c(FAIL_PC)
        _run_positive_probe(root, symbols, fixture, f"exit-reap-through-pid{last_pid}", code)

    code = _positive_base(symbols)
    _run_positive_probe(root, symbols, fixture, "64-wave-stress-return", code)

    code = _positive_base(symbols)
    code += _expect_byte(symbols["p222_cycles_done"], STRESS_WAVES)
    _run_positive_probe(root, symbols, fixture, "cycles-done-64", code)

    free = _free_extents()
    code = _positive_base(symbols)
    _append_compare(code, symbols["memory_free_extents"], MIRROR_BASE, len(free))
    _run_positive_probe(
        root,
        symbols,
        fixture,
        "free-extents-baseline",
        code,
        ((MIRROR_BASE, free),),
    )

    ods = _open_descriptions()
    code = _positive_base(symbols)
    _append_compare(code, symbols["open_description_table"], MIRROR_BASE, len(ods))
    _run_positive_probe(
        root,
        symbols,
        fixture,
        "open-descriptions-baseline",
        code,
        ((MIRROR_BASE, ods),),
    )

    parent = _process_table()[PROC_DESC_SIZE : 2 * PROC_DESC_SIZE]
    code = _positive_base(symbols)
    _append_compare(code, symbols["process_table"] + PROC_DESC_SIZE, MIRROR_BASE, len(parent))
    _run_positive_probe(
        root,
        symbols,
        fixture,
        "parent-descriptor-baseline",
        code,
        ((MIRROR_BASE, parent),),
    )

    code = _positive_base(symbols)
    code += _expect_word(symbols["memory_live_allocations"], 0)
    _run_positive_probe(root, symbols, fixture, "live-allocation-count-zero", code)

    code = _positive_base(symbols)
    code += _expect_byte(symbols["current_pid"], 1)
    _run_positive_probe(root, symbols, fixture, "current-pid-parent", code)

    code = _positive_base(symbols)
    code += _expect_byte(symbols["p222_panic_code"], 0)
    _run_positive_probe(root, symbols, fixture, "panic-code-clear", code)

    code = _positive_base(symbols)
    for pid in range(2, 8):
        code += _expect_byte(symbols["process_table"] + pid * PROC_DESC_SIZE + PROC_STATE, 0)
    _run_positive_probe(root, symbols, fixture, "child-slots-free", code)

    raise Phase222Error(
        "P2.22 full positive oracle failed although all isolated diagnostic probes passed: "
        f"{original}"
    ) from original


def _positive(root: Path, symbols: dict[str, int], fixture: bytes) -> None:
    code = _positive_base(symbols)
    code += _expect_byte(symbols["p222_cycles_done"], STRESS_WAVES)
    mirrors = _accounting_oracle(code, symbols, mirrors=True)
    code += phase1._jp(PASS_PC)
    try:
        run_sna(root, bytes(code), patch=_patch(fixture, _regions(symbols) + mirrors), timeout=30.0)
    except DriverError as exc:
        _diagnose_positive_failure(root, symbols, fixture, exc)


def _negative_skipped_free(root: Path, symbols: dict[str, int], fixture: bytes) -> None:
    code = bytearray(b"\xF3" + phase1._ld_sp(TEST_STACK))
    code += phase1._call(symbols["zx48_process_links_init"]) + _jp_c(FAIL_PC)
    code += phase1._ld_hl(PROC_ADDRESS) + phase1._call(symbols["p222_gateway"]) + _jp_c(FAIL_PC)
    mirrors = _accounting_oracle(code, symbols, mirrors=True)
    code += phase1._jp(PASS_PC)
    try:
        run_sna(root, bytes(code), patch=_patch(fixture, _regions(symbols) + mirrors), timeout=20.0)
    except DriverError as exc:
        require("exit=1 timed_out=False" in str(exc), f"P2.22 skipped-free mutation failed for an unexpected reason: {exc}")
    else:
        raise Phase222Error("P2.22 accounting oracle failed to detect deliberately skipped free")


def dispatch(root: Path, action: str, step: str, *, sha256_file: Callable[[Path], str], run_command: Callable[..., Any], require_project_tool: Callable[[Path, str | Path], Path]):
    if step != "P2.22":
        raise Phase222Error(f"P2.22 driver received unexpected step: {step}")

    assertions = _source_contract(root)
    failed = [item["name"] for item in assertions if item.get("passed") is not True]
    require(not failed, f"static P2.22 contract failures: {failed}")

    kernel_command, kernel, listing = phase1._assemble_kernel(root, run_command, require_project_tool)
    fixture_command, fixture_binary, fixture_symbols = _assemble_fixture(root, run_command, require_project_tool)
    kernel_values = phase1._labels(listing, ("kernel_ordinary_used_end", "KERNEL_CODE_END"))
    free_bytes = kernel_values["KERNEL_CODE_END"] + 1 - kernel_values["kernel_ordinary_used_end"]
    require(free_bytes >= 0, "P2.22 resident ordinary kernel exceeds hard ceiling")
    assertions.append({"name": "resident-kernel-ordinary-code-remains-within-faff-ceiling", "passed": True, "free_bytes": free_bytes})

    symbols = _symbols(fixture_symbols, ("p222_stress", "p222_gateway", "p222_exit_reap", "p222_cycles_done", "p222_panic_code", "zx48_process_links_init", "process_table", "current_pid", "open_description_table", "memory_free_extents", "memory_live_allocations", "tty_input_owner", "PROC_DESC_SIZE", "MAX_PROCESSES"))
    require(symbols["PROC_DESC_SIZE"] == PROC_DESC_SIZE, "P2.22 process descriptor ABI changed")
    require(symbols["MAX_PROCESSES"] == PROCESS_COUNT, "P2.22 process-count ABI changed")

    if action == "test":
        fixture = fixture_binary.read_bytes()
        _positive(root, symbols, fixture)
        _negative_skipped_free(root, symbols, fixture)
        assertions.extend([
            {"name": "384-real-spawn-exit-reap-cycles-return-byte-exact-allocator-open-accounting", "passed": True, "cycles": EXPECTED_CYCLES},
            {"name": "all-pid2-through-pid7-slots-are-filled-and-reused-each-wave", "passed": True, "waves": STRESS_WAVES},
            {"name": "deliberately-skipped-free-is-detected-by-same-accounting-oracle", "passed": True},
        ])

    hashes = {
        "v1/build/kernel.bin": sha256_file(kernel),
        "v1/build/p222-spawn-exit-leak.bin": sha256_file(fixture_binary),
        "v1/src/kernel/process.asm": sha256_file(root / "v1/src/kernel/process.asm"),
        "v1/src/kernel/memory.asm": sha256_file(root / "v1/src/kernel/memory.asm"),
        "v1/src/kernel/handles.asm": sha256_file(root / "v1/src/kernel/handles.asm"),
        str(FIXTURE_SOURCE): sha256_file(root / FIXTURE_SOURCE),
        "v1/tools-host/test-driver/phase2_spawn_exit_leak.py": sha256_file(root / "v1/tools-host/test-driver/phase2_spawn_exit_leak.py"),
        "v1/tools-host/test-driver/run.py": sha256_file(root / "v1/tools-host/test-driver/run.py"),
        "v1/tools-host/test-driver/phase2_gate.py": sha256_file(root / "v1/tools-host/test-driver/phase2_gate.py"),
    }
    return [kernel_command, fixture_command], hashes, assertions
