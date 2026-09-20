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
import struct
from typing import Any, Callable

from driver_core import DriverError
from fuse_harness import FAIL_PC, PASS_PC, run_sna
import phase1
import phase3_open_descriptions

MODULE_BASE = 0xC000
OUT = 0x9000
STACK_TOP = 0xBFC0


class P428Error(DriverError):
    pass


def require(ok: bool, msg: str) -> None:
    if not ok:
        raise P428Error(msg)


def _word(v: int) -> bytes:
    return bytes((v & 0xFF, (v >> 8) & 0xFF))


def _check_byte(addr: int, value: int) -> bytes:
    return b"\x3A" + _word(addr) + bytes((0xFE, value & 0xFF)) + phase1._jp_nz(FAIL_PC)


def _check_bytes(addr: int, data: bytes) -> bytes:
    out = bytearray()
    for i, value in enumerate(data):
        out += _check_byte(addr + i, value)
    return bytes(out)


def _record(name: bytes, directory: int, type_id: int, *, flags: int, logical: int, storage: int, ptr: int = 0) -> bytes:
    r = bytearray(20)
    r[:len(name)] = name
    r[10] = directory
    r[11] = type_id
    r[12] = flags
    r[13] = 0
    r[14:16] = _word(logical)
    r[16:18] = _word(storage)
    r[18:20] = _word(ptr)
    return bytes(r)


def _source_contract(root: Path) -> list[dict[str, object]]:
    zx = (root / "v1/src/kernel/zxpack.asm").read_text(encoding="utf-8")
    sc = (root / "v1/src/kernel/syscall.asm").read_text(encoding="utf-8")
    require("MACRO EMIT_P428_ZXPACK_INFO_ROUTINES" in zx, "P4.28 accounting macro missing")
    require("MACRO EMIT_P428_ZXPACK_INFO_SYSCALL_ROUTINES" in sc, "P4.28 syscall macro missing")
    zm = zx.split("MACRO EMIT_P428_ZXPACK_INFO_ROUTINES", 1)[1].split("ENDM", 1)[0]
    sm = sc.split("MACRO EMIT_P428_ZXPACK_INFO_SYSCALL_ROUTINES", 1)[1].split("ENDM", 1)[0]
    p422 = zx.split("MACRO EMIT_P422_SYS_PACK_CODEC_ROUTINES", 1)[1].split("ENDM", 1)[0]
    return [
        {"name": "exact-20-byte-zpinfo1", "passed": "ld bc,20" in sm and "defs 20,0" in zm},
        {"name": "exact-syscall-number", "passed": "SYS_ZXPACK_INFO" in sm},
        {"name": "complete-user-range-validation-before-write", "passed": sm.index("call zx48_user_range_validate") < sm.index("jp zx48_p428_zxpack_info")},
        {"name": "logical-total-u32", "passed": "p428_info_scratch+2" in zm and "zx48_p428_logical_no_carry" in zm},
        {"name": "physical-total-u16-checked", "passed": "p428_info_scratch+4" in zm and "jp c,zx48_p428_accounting_invalid" in zm},
        {"name": "bytes-saved-u32-no-underflow", "passed": "p428_info_scratch+6" in zm and "p428_info_scratch+8" in zm and "jp c,zx48_p428_accounting_invalid" in zm},
        {"name": "ram-only-object-accounting", "passed": "cp STATE_RAM" in zm},
        {"name": "raw-packed-counts", "passed": "p428_info_scratch+10" in zm and "p428_info_scratch+11" in zm},
        {"name": "shared-reader-state-accounting", "passed": "OD_AUX_O" in zm and "PACKED_READER_STATE_SIZE" in zm and "p428_info_scratch+12" in zm},
        {"name": "attempt-counter-modulo-u16", "passed": "p422_pack_attempts" in p422 and "inc hl" in p422},
        {"name": "success-counter-on-publication", "passed": "p422_pack_successes" in p422 and p422.index("p422_pack_successes") > p422.index("or OBJ_PACKED")},
        {"name": "reserved-zero", "passed": "p428_info_scratch+18" in zm and "p428_info_scratch+19" in zm},
    ]


def _assemble(root: Path, run_command: Callable[..., Any], require_project_tool: Callable[[Path, str | Path], Path]):
    asm = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    fixture = build / "p428-zxpack-info.asm"
    fixture.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
PANIC_SCHEDULER EQU $03
PROC_HANDLES EQU 16
PROC_CWD EQU 28
    ORG $C000
current_pid: db 1
zx48_process_lookup:
    ld ix,fake_process
    xor a
    ret
    INCLUDE "../src/kernel/memory.asm"
    INCLUDE "../src/kernel/handles.asm"
    INCLUDE "../src/kernel/objects.asm"
    INCLUDE "../src/kernel/zxpack.asm"
    INCLUDE "../src/kernel/syscall.asm"
    EMIT_MEMORY_ROUTINES
    EMIT_NAMESPACE_ROUTINES
    EMIT_OBJECT_TYPE_ROUTINES
    EMIT_OBJECT_OPEN_ROUTINES
    EMIT_HANDLE_ROUTINES
    EMIT_P406_EXCLUSIVITY_ROUTINES
    EMIT_P416_ZXP1_DECODER
    EMIT_P420_TARGET_ENCODER_ROUTINES
    EMIT_P422_SYS_PACK_CODEC_ROUTINES
    EMIT_P428_ZXPACK_INFO_ROUTINES
    EMIT_USER_RANGE_VALIDATION_ROUTINE
    EMIT_P428_ZXPACK_INFO_SYSCALL_ROUTINES
zx48_process_count:
    xor a
    ret
zx48_pipe_endpoint_closed:
    xor a
    ret
zx48_panic:
    scf
    ret
fake_process:
    defs 48,0
    SAVEBIN "p428-zxpack-info.bin",$C000,$-$C000
""", encoding="utf-8", newline="\n")
    result = run_command([asm, "--nologo", "--lst=p428-zxpack-info.lst", "--sym=p428-zxpack-info.sym", "p428-zxpack-info.asm"], cwd=build, timeout_seconds=30.0)
    require(not result.timed_out and result.exit_code == 0, f"P4.28 fixture assembly failed: {result.stderr or result.stdout}")
    binary = build / "p428-zxpack-info.bin"
    listing = build / "p428-zxpack-info.lst"
    require(binary.is_file() and 0 < binary.stat().st_size < 24576, "P4.28 fixture binary missing/oversize")
    return result, binary, listing


def _zpinfo(logical: int, physical: int, packed: int, raw: int, reader_bytes: int, attempts: int, successes: int) -> bytes:
    return struct.pack("<IHI2B4H", logical, physical, logical - physical, packed, raw, reader_bytes, attempts, successes, 0)


def _runtime(root: Path, s: dict[str, int], module: bytes) -> None:
    def execute(label: str, code: bytes, patcher) -> None:
        try:
            run_sna(root, code, patch=patcher)
        except DriverError as exc:
            raise P428Error(f"P4.28 runtime case failed: {label}: {exc}") from exc

    table = s["p405_object_table"]
    od = s["open_description_table"]
    attempts = s["p422_pack_attempts"]
    successes = s["p422_pack_successes"]

    def base_patch(records: list[bytes], *, attempt_value: int, success_value: int, readers: int = 0):
        def apply(ram: bytearray) -> None:
            ram[MODULE_BASE-0x4000:MODULE_BASE-0x4000+len(module)] = module
            ram[table-0x4000:table-0x4000+640] = bytes(640)
            for i, record in enumerate(records):
                ram[table-0x4000+i*20:table-0x4000+(i+1)*20] = record
            ram[od-0x4000:od-0x4000+s["OPEN_DESCRIPTION_COUNT"]*8] = bytes(s["OPEN_DESCRIPTION_COUNT"]*8)
            for i in range(readers):
                p = od-0x4000+i*8
                ram[p+s["OD_KIND_O"]] = s["OD_KIND_OBJECT"]
                ram[p+s["OD_REFS_O"]] = 1
                ram[p+s["OD_AUX_O"]:p+s["OD_AUX_O"]+2] = _word(0x8000 + i*0x120)
            ram[attempts-0x4000:attempts-0x4000+2] = _word(attempt_value)
            ram[successes-0x4000:successes-0x4000+2] = _word(success_value)
            ram[OUT-0x4000:OUT-0x4000+20] = b"\xA5" * 20
        return apply

    records = []
    for i in range(20):
        records.append(_record(f"p{i}".encode(), s["DIR_TMP"], s["OBJ_DAT"], flags=s["OBJ_PACKED"], logical=4000, storage=2))
    records.append(_record(b"r0", s["DIR_TMP"], s["OBJ_DAT"], flags=0, logical=100, storage=100))
    records.append(_record(b"r1", s["DIR_TMP"], s["OBJ_DAT"], flags=0, logical=100, storage=100))
    expected = _zpinfo(80200, 240, 20, 2, 544, 0xFFFF, 0x1234)
    code = bytearray(b"\xF3" + phase1._ld_sp(STACK_TOP))
    code += bytes((0x3E, s["SYS_ZXPACK_INFO"])) + phase1._ld_hl(OUT) + phase1._call(s["zx48_p428_sys_zxpack_info"])
    code += phase1._jp_c(FAIL_PC) + _check_bytes(OUT, expected) + phase1._jp(PASS_PC)
    execute("wide-zpinfo-reader-accounting", bytes(code), base_patch(records, attempt_value=0xFFFF, success_value=0x1234, readers=2))

    # Invalid 20-byte destination must fail before any output write.
    code = bytearray(b"\xF3" + phase1._ld_sp(STACK_TOP))
    code += bytes((0x3E, s["SYS_ZXPACK_INFO"])) + phase1._ld_hl(0xDFF8) + phase1._call(s["zx48_p428_sys_zxpack_info"])
    code += b"\xD2" + _word(FAIL_PC) + bytes((0xFE, s["E_INVAL"])) + phase1._jp_nz(FAIL_PC)
    code += _check_bytes(OUT, b"\xA5" * 20) + phase1._jp(PASS_PC)
    execute("invalid-output-range", bytes(code), base_patch(records, attempt_value=1, success_value=1))

    # Attempt counter wraps modulo 65536 even when already PACKED is a no-op.
    one = [_record(b"x", s["DIR_TMP"], s["OBJ_DAT"], flags=s["OBJ_PACKED"], logical=66, storage=2, ptr=s["ARENA_START"])]
    code = bytearray(b"\xF3" + phase1._ld_sp(STACK_TOP))
    code += b"\xDD\x21" + _word(table) + bytes((0x16, 0)) + phase1._call(s["zx48_p422_pack_record"])
    code += phase1._jp_c(FAIL_PC)
    code += bytes((0x3E, s["SYS_ZXPACK_INFO"])) + phase1._ld_hl(OUT) + phase1._call(s["zx48_p428_sys_zxpack_info"])
    code += phase1._jp_c(FAIL_PC) + _check_byte(OUT+14, 0) + _check_byte(OUT+15, 0) + phase1._jp(PASS_PC)
    execute("attempt-counter-wrap", bytes(code), base_patch(one, attempt_value=0xFFFF, success_value=7))


def dispatch(root: Path, action: str, step: str, *, sha256_file, run_command, require_project_tool):
    if step != "P4.28":
        raise DriverError(f"Phase-4 ZXPACK info step is not registered: {step}")
    assertions = _source_contract(root)
    failed = [x["name"] for x in assertions if x.get("passed") is not True]
    require(not failed, f"static P4.28 contract failures: {failed}")
    kernel_result, kernel, _ = phase1._assemble_kernel(root, run_command, require_project_tool)
    fixture_result, binary, listing = _assemble(root, run_command, require_project_tool)
    names = (
        "zx48_p428_sys_zxpack_info", "zx48_p422_pack_record", "p405_object_table",
        "open_description_table", "p422_pack_attempts", "p422_pack_successes",
        "OPEN_DESCRIPTION_COUNT", "OD_KIND_O", "OD_REFS_O", "OD_AUX_O", "OD_KIND_OBJECT",
        "DIR_TMP", "OBJ_DAT", "OBJ_PACKED", "ARENA_START", "SYS_ZXPACK_INFO", "E_INVAL",
    )
    symbols = phase3_open_descriptions._symbols(listing.with_suffix(".sym"), names)
    if action == "test":
        _runtime(root, symbols, binary.read_bytes())
        assertions += [
            {"name": "zpinfo1-byte-exact-runtime", "passed": True},
            {"name": "greater-than-65535-logical-runtime", "passed": True},
            {"name": "packed-reader-shared-state-runtime", "passed": True},
            {"name": "attempt-counter-wrap-runtime", "passed": True},
            {"name": "invalid-output-range-no-write-runtime", "passed": True},
        ]
    hashes = {
        "v1/build/kernel.bin": sha256_file(kernel),
        "v1/build/p428-zxpack-info.bin": sha256_file(binary),
        "v1/src/kernel/zxpack.asm": sha256_file(root / "v1/src/kernel/zxpack.asm"),
        "v1/src/kernel/syscall.asm": sha256_file(root / "v1/src/kernel/syscall.asm"),
        "v1/tools-host/test-driver/phase4_zxpack_info.py": sha256_file(root / "v1/tools-host/test-driver/phase4_zxpack_info.py"),
        "v1/tools-host/test-driver/run.py": sha256_file(root / "v1/tools-host/test-driver/run.py"),
        "v1/dist/certification/P4.27.test.json": sha256_file(root / "v1/dist/certification/P4.27.test.json"),
    }
    return [kernel_result, fixture_result], hashes, assertions
