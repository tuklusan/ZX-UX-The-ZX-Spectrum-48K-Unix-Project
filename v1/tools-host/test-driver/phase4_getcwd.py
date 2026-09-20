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

MODULE_BASE = 0xC000
OUT_BASE = 0xA400
STACK_TOP = 0xBFC0

class P432Error(DriverError):
    pass

def require(ok: bool, message: str) -> None:
    if not ok:
        raise P432Error(message)

def _word(v: int) -> bytes:
    return bytes((v & 0xFF, (v >> 8) & 0xFF))

def _jp_nc(addr: int) -> bytes:
    return b"\xD2" + _word(addr)

def _ld_bc(v: int) -> bytes:
    return b"\x01" + _word(v)

def _ld_a_mem(addr: int) -> bytes:
    return b"\x3A" + _word(addr)

def _mem_eq(addr: int, expected: bytes) -> bytes:
    code = bytearray()
    for off, value in enumerate(expected):
        code += _ld_a_mem(addr + off) + bytes((0xFE, value)) + phase1._jp_nz(FAIL_PC)
    return bytes(code)

def _source_contract(root: Path) -> list[dict[str, object]]:
    objects = (root / "v1/src/kernel/objects.asm").read_text(encoding="utf-8")
    syscall = (root / "v1/src/kernel/syscall.asm").read_text(encoding="utf-8")
    om = objects.split("MACRO EMIT_P432_GETCWD_OBJECT_ROUTINES", 1)[1].split("ENDM", 1)[0]
    sm = syscall.split("MACRO EMIT_P432_GETCWD_SYSCALL_ROUTINES", 1)[1].split("ENDM", 1)[0]
    return [
        {"name": "exact-hl-bc-register-contract", "passed": "HL=destination, BC=capacity" in sm},
        {"name": "complete-declared-output-range-prevalidated", "passed": "call zx48_user_range_validate" in sm and sm.index("call zx48_user_range_validate") < sm.index("jp zx48_p432_getcwd")},
        {"name": "all-fixed-directory-ids-covered", "passed": all(x in om for x in ("DIR_ROOT","DIR_BIN","DIR_DEV","DIR_ETC","DIR_HOME","DIR_USERHOME","DIR_TMP"))},
        {"name": "canonical-userhome-prefix-and-session-user", "passed": "p432_home_prefix" in om and "session_user_len" in om and "session_user" in om},
        {"name": "capacity-includes-terminating-nul", "passed": "inc hl" in om and "p432_capacity" in om and "E_NOSPC" in om},
        {"name": "private-stage-before-publication", "passed": om.index("ld de,p432_path") < om.index("ld de,(p432_out_ptr)")},
        {"name": "single-final-ldir-publication", "passed": "ld hl,p432_path" in om and "ld de,(p432_out_ptr)" in om and "ldir" in om},
        {"name": "success-returns-length-excluding-nul", "passed": "ld a,(p432_length)" in om and "ld l,a" in om and "ld h,0" in om},
        {"name": "invalid-cwd-fails-closed", "passed": "zx48_p432_invalid:" in om and "ld a,E_INVAL" in om},
    ]

def _assemble(root: Path, run_command: Callable[..., Any], require_project_tool: Callable[[Path, str | Path], Path]):
    assembler = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    fixture = build / "p432-getcwd.asm"
    fixture.write_text(
        """    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
PANIC_SCHEDULER EQU $03
PROC_CWD EQU 28
    ORG $C000
current_pid: db 1
zx48_process_lookup:
    ld ix,fake_process
    xor a
    ret
    INCLUDE "../src/kernel/objects.asm"
    INCLUDE "../src/kernel/syscall.asm"
    EMIT_NAMESPACE_ROUTINES
    EMIT_P432_GETCWD_OBJECT_ROUTINES
    EMIT_USER_RANGE_VALIDATION_ROUTINE
    EMIT_P432_GETCWD_SYSCALL_ROUTINES
fake_process: defs 48,0
    SAVEBIN "p432-getcwd.bin",$C000,$-$C000
""",
        encoding="utf-8",
        newline="\n",
    )
    result = run_command(
        [assembler, "--nologo", "--lst=p432-getcwd.lst", "--sym=p432-getcwd.sym", "p432-getcwd.asm"],
        cwd=build,
        timeout_seconds=30.0,
    )
    require(not result.timed_out and result.exit_code == 0, f"P4.32 fixture assembly failed: {result.stderr or result.stdout}")
    binary = build / "p432-getcwd.bin"
    listing = build / "p432-getcwd.lst"
    require(binary.is_file() and 0 < binary.stat().st_size < 16384, "P4.32 fixture missing/oversize")
    return result, binary, listing

def _target(root: Path, s: dict[str, int], module: bytes) -> None:
    fixed = [
        ("root", s["DIR_ROOT"], b"/\0"),
        ("bin", s["DIR_BIN"], b"/bin\0"),
        ("dev", s["DIR_DEV"], b"/dev\0"),
        ("etc", s["DIR_ETC"], b"/etc\0"),
        ("home", s["DIR_HOME"], b"/home\0"),
        ("tmp", s["DIR_TMP"], b"/tmp\0"),
        ("userhome", s["DIR_USERHOME"], b"/home/alice\0"),
    ]

    def base_patch(cwd: int, out: int = OUT_BASE, fill_len: int = 32):
        def apply(ram: bytearray) -> None:
            ram[MODULE_BASE - 0x4000:MODULE_BASE - 0x4000 + len(module)] = module
            ram[s["fake_process"] - 0x4000 + s["PROC_CWD"]] = cwd & 0xFF
            ram[s["session_user_len"] - 0x4000] = 5
            ram[s["session_user"] - 0x4000:s["session_user"] - 0x4000 + 6] = b"alice\0"
            if 0x4000 <= out < 0xE000:
                n = min(fill_len, 0xE000 - out)
                ram[out - 0x4000:out - 0x4000 + n] = bytes((0xA5,)) * n
        return apply

    for label, cwd, expected in fixed:
        path_len = len(expected) - 1
        code = bytearray(b"\xF3" + phase1._ld_sp(STACK_TOP))
        code += phase1._ld_hl(OUT_BASE) + _ld_bc(len(expected))
        code += phase1._call(s["zx48_p432_sys_getcwd"]) + phase1._jp_c(FAIL_PC)
        code += bytes((0x7C, 0xB7)) + phase1._jp_nz(FAIL_PC)
        code += bytes((0x7D, 0xFE, path_len)) + phase1._jp_nz(FAIL_PC)
        code += _mem_eq(OUT_BASE, expected + b"\xA5")
        code += phase1._jp(PASS_PC)
        try:
            run_sna(root, bytes(code), patch=base_patch(cwd))
        except DriverError as exc:
            raise P432Error(f"P4.32 success case failed: {label}: {exc}") from exc

    # Exact short capacity: path_len rather than path_len+1. No byte may change.
    expected = b"/home/alice\0"
    code = bytearray(b"\xF3" + phase1._ld_sp(STACK_TOP))
    code += phase1._ld_hl(OUT_BASE) + _ld_bc(len(expected) - 1)
    code += phase1._call(s["zx48_p432_sys_getcwd"]) + _jp_nc(FAIL_PC)
    code += bytes((0xFE, s["E_NOSPC"])) + phase1._jp_nz(FAIL_PC)
    code += _mem_eq(OUT_BASE, bytes((0xA5,)) * 16) + phase1._jp(PASS_PC)
    run_sna(root, bytes(code), patch=base_patch(s["DIR_USERHOME"]))

    # Zero capacity also reports E_NOSPC without dereferencing or writing.
    code = bytearray(b"\xF3" + phase1._ld_sp(STACK_TOP))
    code += phase1._ld_hl(OUT_BASE) + _ld_bc(0)
    code += phase1._call(s["zx48_p432_sys_getcwd"]) + _jp_nc(FAIL_PC)
    code += bytes((0xFE, s["E_NOSPC"])) + phase1._jp_nz(FAIL_PC)
    code += _mem_eq(OUT_BASE, bytes((0xA5,)) * 16) + phase1._jp(PASS_PC)
    run_sna(root, bytes(code), patch=base_patch(s["DIR_TMP"]))

    # Declared writable range crosses the protected 0x5B00 boundary.
    cross = 0x5AF8
    code = bytearray(b"\xF3" + phase1._ld_sp(STACK_TOP))
    code += phase1._ld_hl(cross) + _ld_bc(16)
    code += phase1._call(s["zx48_p432_sys_getcwd"]) + _jp_nc(FAIL_PC)
    code += bytes((0xFE, s["E_INVAL"])) + phase1._jp_nz(FAIL_PC)
    code += _mem_eq(cross, bytes((0xA5,)) * 8) + phase1._jp(PASS_PC)
    run_sna(root, bytes(code), patch=base_patch(s["DIR_ROOT"], out=cross, fill_len=8))

    # 16-bit wrapped declared range must fail before publication.
    wrap = 0xDFF0
    code = bytearray(b"\xF3" + phase1._ld_sp(STACK_TOP))
    code += phase1._ld_hl(wrap) + _ld_bc(0x3000)
    code += phase1._call(s["zx48_p432_sys_getcwd"]) + _jp_nc(FAIL_PC)
    code += bytes((0xFE, s["E_INVAL"])) + phase1._jp_nz(FAIL_PC)
    code += _mem_eq(wrap, bytes((0xA5,)) * 16) + phase1._jp(PASS_PC)
    run_sna(root, bytes(code), patch=base_patch(s["DIR_BIN"], out=wrap, fill_len=16))

    # Impossible cwd metadata is rejected without output mutation.
    code = bytearray(b"\xF3" + phase1._ld_sp(STACK_TOP))
    code += phase1._ld_hl(OUT_BASE) + _ld_bc(16)
    code += phase1._call(s["zx48_p432_sys_getcwd"]) + _jp_nc(FAIL_PC)
    code += bytes((0xFE, s["E_INVAL"])) + phase1._jp_nz(FAIL_PC)
    code += _mem_eq(OUT_BASE, bytes((0xA5,)) * 16) + phase1._jp(PASS_PC)
    run_sna(root, bytes(code), patch=base_patch(s["DIR_SYSTEM"]))

def dispatch(
    root: Path,
    action: str,
    step: str,
    *,
    sha256_file: Callable[[Path], str],
    run_command: Callable[..., Any],
    require_project_tool: Callable[[Path, str | Path], Path],
):
    if step != "P4.32":
        raise DriverError(f"Phase-4 getcwd step is not registered: {step}")

    assertions = _source_contract(root)
    bad = [a["name"] for a in assertions if a.get("passed") is not True]
    require(not bad, f"P4.32 static failures: {bad}")

    kernel_result, kernel, _ = phase1._assemble_kernel(root, run_command, require_project_tool)
    fixture_result, binary, listing = _assemble(root, run_command, require_project_tool)
    names = (
        "zx48_p432_sys_getcwd", "fake_process", "session_user_len", "session_user", "PROC_CWD",
        "DIR_ROOT", "DIR_BIN", "DIR_DEV", "DIR_ETC", "DIR_HOME", "DIR_USERHOME", "DIR_TMP", "DIR_SYSTEM",
        "E_INVAL", "E_NOSPC",
    )
    symbols = phase3_open_descriptions._symbols(listing.with_suffix(".sym"), names)

    if action == "test":
        _target(root, symbols, binary.read_bytes())
        assertions.extend([
            {"name": "all-canonical-fixed-paths-exact-runtime", "passed": True},
            {"name": "userhome-current-session-path-exact-runtime", "passed": True},
            {"name": "return-count-excludes-nul-runtime", "passed": True},
            {"name": "capacity-equals-pathlen-nospc-no-write", "passed": True},
            {"name": "zero-capacity-nospc-no-write", "passed": True},
            {"name": "cross-boundary-output-range-invalid-no-write", "passed": True},
            {"name": "wrapped-output-range-invalid-no-write", "passed": True},
            {"name": "invalid-cwd-id-no-write", "passed": True},
        ])

    hashes = {
        "v1/build/kernel.bin": sha256_file(kernel),
        "v1/build/p432-getcwd.bin": sha256_file(binary),
        "v1/src/kernel/objects.asm": sha256_file(root / "v1/src/kernel/objects.asm"),
        "v1/src/kernel/syscall.asm": sha256_file(root / "v1/src/kernel/syscall.asm"),
        "v1/tools-host/test-driver/phase4_getcwd.py": sha256_file(root / "v1/tools-host/test-driver/phase4_getcwd.py"),
        "v1/tools-host/test-driver/run.py": sha256_file(root / "v1/tools-host/test-driver/run.py"),
        "v1/dist/certification/P4.31.test.json": sha256_file(root / "v1/dist/certification/P4.31.test.json"),
    }
    return [kernel_result, fixture_result], hashes, assertions
