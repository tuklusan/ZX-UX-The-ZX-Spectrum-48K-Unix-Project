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
from typing import Any, Callable, Iterable

from driver_core import DriverError
from fuse_harness import ENTRY_PC, FAIL_PC, PASS_PC, run_sna
import phase1

SRC = 0x6000
DST = 0x6100
AUX = 0x6200
REF = 0x6300
AUX2 = 0x6400
REF2 = 0x6500
PIPE_RESULT = 0x6800
PIPE_SRC1 = 0x6000
PIPE_OUT1 = 0x6100
PIPE_SRC2 = 0x6200
PIPE_OUT2 = 0x6300
PIPE_REF2 = 0x6400
LONG_SRC = 0x6000
LONG_DST = 0x7100
LONG_COUNT = 0x1000
SYS_READ = 0x12
SYS_WRITE = 0x13
SYS_PIPE = 0x20
PAL_FRAME_TSTATES = 69888
LDIR_REPEAT_TSTATES = 21

SMALL_COPY_EXCEPTIONS: tuple[dict[str, object], ...] = ()


class PrimitiveContractError(DriverError):
    """Raised when the P1.40 canonical primitive contract is violated."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise PrimitiveContractError(message)


def _word(value: int) -> bytes:
    return bytes((value & 0xFF, (value >> 8) & 0xFF))


def _call(address: int) -> bytes:
    return b"\xCD" + _word(address)


def _jp(address: int) -> bytes:
    return b"\xC3" + _word(address)


def _jp_z(address: int) -> bytes:
    return b"\xCA" + _word(address)


def _jp_nz(address: int) -> bytes:
    return b"\xC2" + _word(address)


def _jp_c(address: int) -> bytes:
    return b"\xDA" + _word(address)


def _jp_nc(address: int) -> bytes:
    return b"\xD2" + _word(address)


def _ld_bc(value: int) -> bytes:
    return b"\x01" + _word(value)


def _ld_a(value: int) -> bytes:
    return bytes((0x3E, value & 0xFF))


def _store_byte(address: int, value: int) -> bytes:
    return _ld_a(value) + b"\x32" + _word(address)


def _expect_byte(address: int, value: int) -> bytes:
    return b"\x3A" + _word(address) + bytes((0xFE, value & 0xFF)) + _jp_nz(FAIL_PC)


def _expect_word(address: int, value: int) -> bytes:
    return b"\x2A" + _word(address) + phase1._ld_de(value) + b"\xB7\xED\x52" + _jp_nz(FAIL_PC)


def _strip(text: str) -> str:
    return "\n".join(line.split(";", 1)[0].rstrip().lower() for line in text.splitlines())


def _block(text: str, start: str, end: str) -> str:
    first = text.find(start)
    last = text.find(end, first + len(start)) if first >= 0 else -1
    require(0 <= first < last, f"missing source block {start}..{end}")
    return text[first:last]


def _small_exception_valid(item: dict[str, object]) -> bool:
    return (
        isinstance(item.get("name"), str)
        and isinstance(item.get("bytes"), int)
        and int(item["bytes"]) > 0
        and isinstance(item.get("bytes_saved_or_tied"), int)
        and isinstance(item.get("cycles_saved_or_tied"), int)
        and isinstance(item.get("rationale"), str)
        and bool(str(item["rationale"]).strip())
    )


def _families_complete(text: str) -> bool:
    lowered = _strip(text)
    required = (
        "zx48_memcpy:", "ldir", "zx48_memmove:", "lddr",
        "zx48_copy_one_fwd:", "ldi", "zx48_copy_one_back:", "ldd",
        "zx48_memchr:", "cpir", "zx48_memrchr:", "cpdr",
        "zx48_compare_one_fwd:", "cpi", "zx48_compare_one_back:", "cpd",
    )
    return all(token in lowered for token in required)


def _ownership_violations(kernel: str, pipe: str, udg: str) -> list[str]:
    violations: list[str] = []
    kernel_l = _strip(kernel)
    pipe_l = _strip(pipe)
    udg_l = _strip(udg)
    if kernel_l.count('include "z80_primitives.asm"') != 1 or kernel_l.count("emit_z80_primitives") != 1:
        violations.append("canonical primitive owner is not emitted exactly once")
    read = _block(pipe_l, "zx48_pipe_read:", "zx48_pipe_write:")
    write = _block(pipe_l, "zx48_pipe_write:", "zx48_pipe_broken:")
    if "call zx48_memcpy" not in read or "call zx48_memcpy" not in write:
        violations.append("pipe read/write does not resolve contiguous chunks to zx48_memcpy")
    if "zx48_pipe_chunk_limit:" not in pipe_l:
        violations.append("pipe chunk copy has no explicit ring-tail limiter")
    define = _block(udg_l, "zx48_udg_define:", "zx48_udg_get:")
    get = _block(udg_l, "zx48_udg_get:", "zx48_udg_clear:")
    for name, block in (("udg-define", define), ("udg-get", get)):
        if "call zx48_memcpy" not in block:
            violations.append(f"{name} does not resolve to zx48_memcpy")
        if re.search(r"(?m)^\s*ldir\s*$", block):
            violations.append(f"{name} retains an independent LDIR copy")
    return violations


def _source_contract(root: Path) -> list[dict[str, object]]:
    primitives_raw = (root / "v1/src/kernel/z80_primitives.asm").read_text(encoding="utf-8")
    kernel = (root / "v1/src/kernel/kernel.asm").read_text(encoding="utf-8")
    pipe = (root / "v1/src/kernel/pipe.asm").read_text(encoding="utf-8")
    udg = (root / "v1/src/kernel/udg.asm").read_text(encoding="utf-8")
    boot = (root / "v1/src/boot/entry.asm").read_text(encoding="utf-8")
    ownership = _ownership_violations(kernel, pipe, udg)
    lower_raw = primitives_raw.lower()
    return [
        {"name": "all-z80-block-transfer-search-families-owned", "passed": _families_complete(primitives_raw)},
        {"name": "memmove-explicitly-selects-backward-and-forward-repeat", "passed": "lddr" in lower_raw and lower_raw.count("ldir") >= 2},
        {"name": "repeated-block-instructions-declared-interruptible", "passed": "interruptible" in lower_raw and "no caller may treat them as a critical-section boundary" in lower_raw},
        {"name": "canonical-owner-emitted-exactly-once", "passed": not any("owner" in item for item in ownership)},
        {"name": "phase1-live-pipe-chunks-use-canonical-memcpy", "passed": not any(item.startswith("pipe") for item in ownership)},
        {"name": "phase1-live-udg-set-copies-use-canonical-memcpy", "passed": not any(item.startswith("udg") for item in ownership)},
        {"name": "phase1-boot-has-no-independent-loader-copy-consumer", "passed": not re.search(r"(?m)^\s*(?:ldi|ldir|ldd|lddr|cpi|cpir|cpd|cpdr)\s*$", _strip(boot))},
        {"name": "live-small-copy-exception-manifest-is-measured", "passed": all(_small_exception_valid(item) for item in SMALL_COPY_EXCEPTIONS), "count": len(SMALL_COPY_EXCEPTIONS)},
        {"name": "canonical-ownership-has-no-live-violations", "passed": not ownership, "violations": ownership},
    ]


def _patch(kernel: bytes, extras: Iterable[tuple[int, bytes]] = ()):  # noqa: ANN201
    extras = tuple(extras)
    def apply(ram: bytearray) -> None:
        start = phase1.KERNEL_BASE - 0x4000
        ram[start:start + len(kernel)] = kernel
        for address, payload in extras:
            offset = address - 0x4000
            require(0 <= offset <= len(ram) - len(payload), f"fixture patch outside RAM: 0x{address:04X}")
            ram[offset:offset + len(payload)] = payload
    return apply


def _compare_regions(code: bytearray, left: int, right: int, count: int) -> None:
    require(count > 0, "comparison length must be nonzero")
    code += phase1._ld_hl(left) + phase1._ld_de(right) + _ld_bc(count)
    loop = ENTRY_PC + len(code)
    code += b"\x1A\xBE" + _jp_nz(FAIL_PC) + b"\x13\x23\x0B\x78\xB1" + _jp_nz(loop)


def _copy_move_fixture(root: Path, labels: dict[str, int], kernel: bytes) -> None:
    src = bytes(range(1, 17))
    overlap = bytes(range(32))
    back_expected = overlap[:4] + overlap[:16] + overlap[20:]
    fwd_expected = overlap[4:20] + overlap[16:]
    extras = (
        (SRC - 1, b"\xA1" + src + b"\xA2"),
        (DST - 1, b"\xB1" + b"\xCC" * 16 + b"\xB2"),
        (AUX - 1, b"\xC1" + overlap + b"\xC2"),
        (REF, back_expected),
        (AUX2 - 1, b"\xD1" + overlap + b"\xD2"),
        (REF2, fwd_expected),
    )
    code = bytearray(b"\xF3" + phase1._ld_sp(phase1.USER_STACK))
    code += phase1._ld_hl(SRC) + phase1._ld_de(DST) + _ld_bc(16) + _call(labels["zx48_memcpy"])
    _compare_regions(code, SRC, DST, 16)
    code += _expect_byte(SRC - 1, 0xA1) + _expect_byte(SRC + 16, 0xA2)
    code += _expect_byte(DST - 1, 0xB1) + _expect_byte(DST + 16, 0xB2)
    code += phase1._ld_hl(SRC) + phase1._ld_de(DST) + _ld_bc(0) + _call(labels["zx48_memcpy"])
    code += _expect_byte(DST, 1)
    code += phase1._ld_hl(AUX) + phase1._ld_de(AUX + 4) + _ld_bc(16) + _call(labels["zx48_memmove"])
    _compare_regions(code, AUX, REF, len(back_expected))
    code += _expect_byte(AUX - 1, 0xC1) + _expect_byte(AUX + 32, 0xC2)
    code += phase1._ld_hl(AUX2 + 4) + phase1._ld_de(AUX2) + _ld_bc(16) + _call(labels["zx48_memmove"])
    _compare_regions(code, AUX2, REF2, len(fwd_expected))
    code += _expect_byte(AUX2 - 1, 0xD1) + _expect_byte(AUX2 + 32, 0xD2) + _jp(PASS_PC)
    run_sna(root, bytes(code), patch=_patch(kernel, extras))


def _search_and_single_step_fixture(root: Path, labels: dict[str, int], kernel: bytes) -> None:
    data = b"abacad"
    extras = (
        (SRC, data),
        (DST, b"\xA5"),
        (DST + 0x10, b"\x00"),
        (DST + 0x20, b"\x5A"),
        (DST + 0x30, b"\x00"),
    )
    code = bytearray(b"\xF3" + phase1._ld_sp(phase1.USER_STACK))
    code += _ld_a(ord("c")) + phase1._ld_hl(SRC) + _ld_bc(len(data)) + _call(labels["zx48_memchr"]) + _jp_c(FAIL_PC)
    code += phase1._ld_de(SRC + 3) + b"\xB7\xED\x52" + _jp_nz(FAIL_PC)
    code += _ld_a(ord("z")) + phase1._ld_hl(SRC) + _ld_bc(len(data)) + _call(labels["zx48_memchr"]) + _jp_nc(FAIL_PC)
    code += _ld_a(ord("a")) + phase1._ld_hl(SRC + len(data) - 1) + _ld_bc(len(data)) + _call(labels["zx48_memrchr"]) + _jp_c(FAIL_PC)
    code += phase1._ld_de(SRC + 4) + b"\xB7\xED\x52" + _jp_nz(FAIL_PC)
    code += phase1._ld_hl(DST) + phase1._ld_de(DST + 0x10) + _ld_bc(1) + _call(labels["zx48_copy_one_fwd"])
    code += _expect_byte(DST + 0x10, 0xA5)
    code += phase1._ld_hl(DST + 0x20) + phase1._ld_de(DST + 0x30) + _ld_bc(1) + _call(labels["zx48_copy_one_back"])
    code += _expect_byte(DST + 0x30, 0x5A)
    code += _ld_a(0xA5) + phase1._ld_hl(DST) + _ld_bc(1) + _call(labels["zx48_compare_one_fwd"]) + _jp_nz(FAIL_PC)
    code += _ld_a(0x5A) + phase1._ld_hl(DST + 0x20) + _ld_bc(1) + _call(labels["zx48_compare_one_back"]) + _jp_nz(FAIL_PC)
    code += _jp(PASS_PC)
    run_sna(root, bytes(code), patch=_patch(kernel, extras))


def _string_fixture(root: Path, labels: dict[str, int], kernel: bytes) -> None:
    extras = ((SRC, b"alpha\x00alpha\x00alpHb\x00"),)
    code = bytearray(b"\xF3" + phase1._ld_sp(phase1.USER_STACK))
    code += phase1._ld_hl(SRC) + _call(labels["zx48_strlen"])
    code += b"\xC5\xE1" + phase1._ld_de(5) + b"\xB7\xED\x52" + _jp_nz(FAIL_PC)
    code += phase1._ld_hl(SRC) + phase1._ld_de(SRC + 6) + _call(labels["zx48_strcmp"]) + _jp_nz(FAIL_PC)
    code += phase1._ld_hl(SRC) + phase1._ld_de(SRC + 12) + _call(labels["zx48_strcmp"]) + _jp_z(FAIL_PC)
    code += _jp(PASS_PC)
    run_sna(root, bytes(code), patch=_patch(kernel, extras))


def _udg_fixture(root: Path, labels: dict[str, int], kernel: bytes) -> None:
    glyph = bytes((0x81, 0x42, 0x24, 0x18, 0x18, 0x24, 0x42, 0x81))
    extras = ((SRC, glyph), (DST, b"\x00" * 8))
    code = bytearray(b"\xF3" + phase1._ld_sp(phase1.USER_STACK))
    code += _call(labels["zx48_memory_init"]) + _call(labels["zx48_udg_init"]) + _jp_c(FAIL_PC)
    code += phase1._ld_hl(SRC) + b"\x06\x00\x0E\x05" + _call(labels["zx48_udg_define"]) + _jp_c(FAIL_PC)
    code += phase1._ld_hl(DST) + b"\x06\x00\x0E\x05" + _call(labels["zx48_udg_get"]) + _jp_c(FAIL_PC)
    _compare_regions(code, SRC, DST, 8)
    code += _jp(PASS_PC)
    run_sna(root, bytes(code), patch=_patch(kernel, extras))


def _load_handle(result_addr: int) -> bytes:
    return b"\x3A" + _word(result_addr) + b"\x5F\x16\x00"


def _sys_rw(syscall: int, handle_addr: int, buffer: int, count: int) -> bytes:
    return _load_handle(handle_addr) + phase1._ld_hl(buffer) + _ld_bc(count) + _ld_a(syscall) + _call(0xE000)


def _pipe_fixture(root: Path, labels: dict[str, int], kernel: bytes) -> None:
    src1 = bytes((i * 3 + 7) & 0xFF for i in range(200))
    src2 = bytes((0x80 + i * 5) & 0xFF for i in range(100))
    remaining = src1[180:] + src2
    extras = (
        (PIPE_SRC1, src1), (PIPE_OUT1, b"\xCC" * 180),
        (PIPE_SRC2, src2), (PIPE_OUT2, b"\xDD" * 120),
        (PIPE_REF2, remaining),
    )
    code = bytearray(b"\xF3" + phase1._ld_sp(phase1.USER_STACK))
    for label in ("zx48_kernel_stack_init", "zx48_memory_init", "zx48_process_init", "zx48_handles_init", "zx48_pipe_init"):
        code += _call(labels[label])
    code += phase1._ld_hl(PIPE_RESULT) + _ld_a(SYS_PIPE) + _call(0xE000) + _jp_c(FAIL_PC)
    code += _sys_rw(SYS_WRITE, PIPE_RESULT + 1, PIPE_SRC1, 200) + _jp_c(FAIL_PC)
    code += phase1._ld_de(200) + b"\xB7\xED\x52" + _jp_nz(FAIL_PC)
    code += _sys_rw(SYS_READ, PIPE_RESULT, PIPE_OUT1, 180) + _jp_c(FAIL_PC)
    code += phase1._ld_de(180) + b"\xB7\xED\x52" + _jp_nz(FAIL_PC)
    _compare_regions(code, PIPE_SRC1, PIPE_OUT1, 180)
    # WPOS=200: only 56 bytes fit before the 256-byte ring wraps.
    code += _sys_rw(SYS_WRITE, PIPE_RESULT + 1, PIPE_SRC2, 100) + _jp_c(FAIL_PC)
    code += phase1._ld_de(56) + b"\xB7\xED\x52" + _jp_nz(FAIL_PC)
    code += _sys_rw(SYS_WRITE, PIPE_RESULT + 1, PIPE_SRC2 + 56, 44) + _jp_c(FAIL_PC)
    code += phase1._ld_de(44) + b"\xB7\xED\x52" + _jp_nz(FAIL_PC)
    # RPOS=180: read returns the 76-byte tail, then the 44-byte head.
    code += _sys_rw(SYS_READ, PIPE_RESULT, PIPE_OUT2, 120) + _jp_c(FAIL_PC)
    code += phase1._ld_de(76) + b"\xB7\xED\x52" + _jp_nz(FAIL_PC)
    code += _sys_rw(SYS_READ, PIPE_RESULT, PIPE_OUT2 + 76, 44) + _jp_c(FAIL_PC)
    code += phase1._ld_de(44) + b"\xB7\xED\x52" + _jp_nz(FAIL_PC)
    _compare_regions(code, PIPE_REF2, PIPE_OUT2, 120)
    table = labels["pipe_table"]
    code += _expect_byte(table + 2, 44) + _expect_byte(table + 3, 44)
    code += _expect_word(table + 4, 0) + _expect_word(table + 6, 0x0100)
    code += _jp(PASS_PC)
    run_sna(root, bytes(code), patch=_patch(kernel, extras))


def _interrupt_restart_fixture(root: Path, labels: dict[str, int], kernel: bytes) -> None:
    require(LONG_COUNT * LDIR_REPEAT_TSTATES > PAL_FRAME_TSTATES, "interrupt copy must exceed one PAL frame")
    source = bytes((i * 17 + (i >> 4) + 0x31) & 0xFF for i in range(LONG_COUNT))
    extras = (
        (LONG_SRC - 1, b"\x91" + source + b"\x92"),
        (LONG_DST - 1, b"\xA1" + b"\xCC" * LONG_COUNT + b"\xA2"),
    )
    code = bytearray(b"\xF3" + phase1._ld_sp(phase1.USER_STACK))
    code += _call(labels["zx48_kernel_stack_init"]) + _call(labels["zx48_im2_init"])
    code += _store_byte(labels["kernel_ticks"], 0) + _store_byte(labels["kernel_ticks"] + 1, 0)
    code += _store_byte(labels["kernel_ticks"] + 2, 0) + _store_byte(labels["kernel_ticks"] + 3, 0)
    code += phase1._ld_hl(LONG_SRC) + phase1._ld_de(LONG_DST) + _ld_bc(LONG_COUNT)
    code += b"\xFB" + _call(labels["zx48_memcpy"]) + b"\xF3"
    code += b"\x3A" + _word(labels["kernel_ticks"]) + b"\x4F"
    code += b"\x3A" + _word(labels["kernel_ticks"] + 1) + b"\xB1" + _jp_z(FAIL_PC)
    _compare_regions(code, LONG_SRC, LONG_DST, LONG_COUNT)
    code += _expect_byte(LONG_SRC - 1, 0x91) + _expect_byte(LONG_SRC + LONG_COUNT, 0x92)
    code += _expect_byte(LONG_DST - 1, 0xA1) + _expect_byte(LONG_DST + LONG_COUNT, 0xA2)
    code += _jp(PASS_PC)
    run_sna(root, bytes(code), patch=_patch(kernel, extras), timeout=20.0)


def _wrong_overlap_oracle(root: Path, kernel: bytes) -> None:
    payload = bytes(range(32))
    code = bytearray(b"\xF3" + phase1._ld_sp(phase1.USER_STACK))
    code += phase1._ld_hl(SRC) + phase1._ld_de(SRC + 4) + _ld_bc(16) + b"\xED\xB0"
    code += b"\x3A" + _word(SRC + 8) + b"\xFE\x04" + _jp_nz(PASS_PC) + _jp(FAIL_PC)
    run_sna(root, bytes(code), patch=_patch(kernel, ((SRC, payload),)))


def _negative_static_oracles(root: Path) -> None:
    primitives = (root / "v1/src/kernel/z80_primitives.asm").read_text(encoding="utf-8")
    kernel = (root / "v1/src/kernel/kernel.asm").read_text(encoding="utf-8")
    pipe = (root / "v1/src/kernel/pipe.asm").read_text(encoding="utf-8")
    udg = (root / "v1/src/kernel/udg.asm").read_text(encoding="utf-8")
    require(not _families_complete(primitives.replace("cpdr", "nop", 1)), "family-omission oracle failed")
    bad_udg = udg.replace("call zx48_memcpy", "ldir", 1)
    require(any(item.startswith("udg") for item in _ownership_violations(kernel, pipe, bad_udg)), "duplicate-copy ownership oracle failed")
    require(not _small_exception_valid({"name": "synthetic", "bytes": 4, "rationale": "missing measurements"}), "small-copy measurement oracle failed")


def dispatch(root: Path, action: str, step: str, *, sha256_file: Callable[[Path], str], run_command: Callable[..., Any], require_project_tool: Callable[[Path, str | Path], Path]):
    if step != "P1.40":
        raise PrimitiveContractError(f"primitive step is not registered: {step}")
    assertions = _source_contract(root)
    failed = [item["name"] for item in assertions if item["passed"] is not True]
    require(not failed, f"static P1.40 failures: {failed}")
    command, kernel_path, listing = phase1._assemble_kernel(root, run_command, require_project_tool)
    labels = phase1._labels(listing, (
        "zx48_memcpy", "zx48_memmove", "zx48_copy_one_fwd", "zx48_copy_one_back",
        "zx48_memchr", "zx48_memrchr", "zx48_compare_one_fwd", "zx48_compare_one_back",
        "zx48_strlen", "zx48_strcmp", "zx48_kernel_stack_init", "zx48_im2_init", "kernel_ticks",
        "zx48_memory_init", "zx48_process_init", "zx48_handles_init", "zx48_pipe_init", "pipe_table",
        "zx48_udg_init", "zx48_udg_define", "zx48_udg_get", "kernel_ordinary_used_end",
    ))
    kernel = kernel_path.read_bytes()
    ordinary_bytes = labels["kernel_ordinary_used_end"] - phase1.KERNEL_BASE
    assertions.append({"name": "ordinary-kernel-pool-budget", "passed": ordinary_bytes <= 0x1B00, "bytes": ordinary_bytes, "limit": 0x1B00})
    require(ordinary_bytes <= 0x1B00, f"ordinary kernel pool exceeds 6912 bytes: {ordinary_bytes}")
    if action == "test":
        _copy_move_fixture(root, labels, kernel)
        _search_and_single_step_fixture(root, labels, kernel)
        _string_fixture(root, labels, kernel)
        _udg_fixture(root, labels, kernel)
        _pipe_fixture(root, labels, kernel)
        _interrupt_restart_fixture(root, labels, kernel)
        _wrong_overlap_oracle(root, kernel)
        _negative_static_oracles(root)
        assertions.extend((
            {"name": "copy-move-golden-vectors-and-guards-runtime", "passed": True},
            {"name": "search-and-all-single-step-block-families-runtime", "passed": True},
            {"name": "strlen-strcmp-runtime", "passed": True},
            {"name": "live-udg-canonical-copy-runtime", "passed": True},
            {"name": "live-pipe-ring-wrap-short-count-canonical-chunk-copy-runtime", "passed": True},
            {"name": "accepted-im2-interrupt-between-ldir-iterations-completes-exactly", "passed": True, "bytes": LONG_COUNT},
            {"name": "wrong-overlap-direction-negative-oracle", "passed": True},
            {"name": "ownership-family-and-measurement-negative-oracles", "passed": True},
        ))
    paths = (
        root / "docs/01-ZX-UX-ARCHITECTURE-REV12.md",
        root / "v1/docs/test-plan.md",
        root / "v1/src/kernel/kernel.asm",
        root / "v1/src/kernel/z80_primitives.asm",
        root / "v1/src/kernel/pipe.asm",
        root / "v1/src/kernel/udg.asm",
        root / "v1/src/kernel/interrupt.asm",
        root / "v1/tools-host/test-driver/phase1_primitives.py",
        kernel_path,
    )
    return [command], {str(path.relative_to(root)): sha256_file(path) for path in paths}, assertions
