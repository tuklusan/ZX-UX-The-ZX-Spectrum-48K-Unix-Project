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
STACK_TOP = 0xBFC0


class P419Error(DriverError):
    pass


def require(ok: bool, msg: str) -> None:
    if not ok:
        raise P419Error(msg)


def _word(value: int) -> bytes:
    return bytes((value & 0xFF, (value >> 8) & 0xFF))


def _jp_nc(address: int) -> bytes:
    return b"\xD2" + _word(address)


def _check_byte(address: int, value: int) -> bytes:
    return b"\x3A" + _word(address) + bytes((0xFE, value & 0xFF)) + phase1._jp_nz(FAIL_PC)


def _check_word(address: int, value: int) -> bytes:
    return b"\x2A" + _word(address) + phase1._ld_de(value) + b"\xB7\xED\x52" + phase1._jp_nz(FAIL_PC)


def _check_bytes(address: int, data: bytes) -> bytes:
    out = bytearray()
    for i, value in enumerate(data):
        out += _check_byte(address + i, value)
    return bytes(out)


def _record(name: bytes, directory: int, type_id: int, *, flags: int, logical: int, storage: int, ptr: int) -> bytes:
    raw = bytearray(20)
    raw[:len(name)] = name
    raw[10] = directory
    raw[11] = type_id
    raw[12] = flags
    raw[14:16] = _word(logical)
    raw[16:18] = _word(storage)
    raw[18:20] = _word(ptr)
    return bytes(raw)


def _source_contract(root: Path) -> list[dict[str, object]]:
    objects = (root / "v1/src/kernel/objects.asm").read_text(encoding="utf-8")
    zxpack = (root / "v1/src/kernel/zxpack.asm").read_text(encoding="utf-8")
    require("MACRO EMIT_P419_WRITABLE_OPEN_ROUTINES" in objects, "P4.19 writable-open macro missing")
    require("MACRO EMIT_P419_PACKED_WRITE_ROUTINES" in zxpack, "P4.19 materialization macro missing")
    om = objects.split("MACRO EMIT_P419_WRITABLE_OPEN_ROUTINES", 1)[1].split("ENDM", 1)[0]
    zm = zxpack.split("MACRO EMIT_P419_PACKED_WRITE_ROUTINES", 1)[1].split("ENDM", 1)[0]
    reserve = om.index("call zx48_p406_od_create")
    install = om.index("call zx48_handle_install")
    materialize = om.index("call zx48_p419_materialize_private")
    expose = om.index("zx48_p419_open_success:")
    decode = zm.index("call zx48_p416_decode")
    publish = zm.index("ld (ix+OBJ_ALLOCATION_PTR),l", decode)
    release = zm.index("call zx48_free", publish)
    return [
        {"name": "reserve-before-representation-change", "passed": reserve < install < materialize < expose},
        {"name": "writer-return-after-materialization", "passed": materialize < expose and "ld hl,0" not in om[materialize:expose]},
        {"name": "trunc-direct-empty-raw-path", "passed": "and O_TRUNC" in om and "call zx48_p405_object_truncate" in om},
        {"name": "private-exact-logical-allocation", "passed": "ld bc,(p419_logical_length)" in zm and "ALLOC_COLD_PREFERRED" in zm},
        {"name": "p416-final-memory-validation", "passed": "P416_SINK_FINAL_MEMORY" in zm and decode >= 0},
        {"name": "publish-only-after-complete-decode", "passed": decode < publish},
        {"name": "release-old-only-after-publication", "passed": publish < release},
        {"name": "decode-failure-frees-private-only", "passed": "zx48_p419_decode_fail:" in zm and "ld hl,(p419_new_ptr)" in zm and "ld hl,(p419_old_ptr)" not in zm.split("zx48_p419_decode_fail:",1)[1]},
        {"name": "failed-materialization-rolls-back-handle", "passed": "zx48_p419_open_materialize_fail:" in om and "call zx48_handle_close" in om},
        {"name": "packed-empty-is-format-error", "passed": "jp z,zx48_p419_format" in zm},
    ]


def _assemble(root: Path, run_command: Callable[..., Any], require_project_tool: Callable[[Path, str | Path], Path]):
    asm = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    fixture = build / "p419-packed-write.asm"
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
    EMIT_MEMORY_ROUTINES
    EMIT_NAMESPACE_ROUTINES
    EMIT_OBJECT_TYPE_ROUTINES
    EMIT_OBJECT_OPEN_ROUTINES
    EMIT_HANDLE_ROUTINES
    EMIT_P406_EXCLUSIVITY_ROUTINES
    EMIT_P416_ZXP1_DECODER
    EMIT_P419_PACKED_WRITE_ROUTINES
    EMIT_P419_WRITABLE_OPEN_ROUTINES
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
    defs 16,0
    defs 8,HANDLE_FREE
    defs 24,0
    SAVEBIN "p419-packed-write.bin",$C000,$-$C000
""", encoding="utf-8", newline="\n")
    result = run_command([asm, "--nologo", "--lst=p419-packed-write.lst", "--sym=p419-packed-write.sym", "p419-packed-write.asm"], cwd=build, timeout_seconds=30.0)
    require(not result.timed_out and result.exit_code == 0, f"P4.19 fixture assembly failed: {result.stderr or result.stdout}")
    binary = build / "p419-packed-write.bin"
    listing = build / "p419-packed-write.lst"
    require(binary.is_file() and 0 < binary.stat().st_size < 16384, "P4.19 fixture binary missing/oversize")
    return result, binary, listing


def _runtime(root: Path, s: dict[str, int], module: bytes) -> None:
    table = s["p405_object_table"]
    od = s["open_description_table"]
    fake = s["fake_process"]
    free = s["memory_free_extents"]
    live = s["memory_live_allocations"]
    old = s["ARENA_START"]
    arena = s["ARENA_SIZE"]
    write = s["O_WRITE"]
    trunc = s["O_TRUNC"]
    packed_flag = s["OBJ_PACKED"]
    packed_ok = b"\x7fA"
    packed_bad = b"\x40"

    def patch(record: bytes, payload: bytes, *, free_len: int | None = None, handles_full: bool = False):
        storage = record[16] | (record[17] << 8)
        def apply(ram: bytearray) -> None:
            ram[MODULE_BASE-0x4000:MODULE_BASE-0x4000+len(module)] = module
            ram[table-0x4000:table-0x4000+20] = record
            ram[old-0x4000:old-0x4000+len(payload)] = payload
            ram[free-0x4000:free-0x4000+64] = bytes(64)
            avail = arena - ((storage + 1) & ~1) if free_len is None else free_len
            ram[free-0x4000:free-0x4000+4] = _word(old + ((storage + 1) & ~1)) + _word(avail)
            ram[live-0x4000:live-0x4000+2] = _word(1)
            if handles_full:
                ram[fake-0x4000+16:fake-0x4000+24] = bytes((0,))*8
        return apply

    def call(flags: int) -> bytes:
        return bytes((0x3E, flags & 0xFF, 0x0E, 0x00)) + phase1._call(s["zx48_p419_open_existing"])

    def execute(label: str, code: bytes, record: bytes, payload: bytes, **kwargs) -> None:
        body = b"\xF3" + phase1._ld_sp(STACK_TOP) + code + phase1._jp(PASS_PC)
        try:
            run_sna(root, body, patch=patch(record, payload, **kwargs))
        except DriverError as exc:
            raise P419Error(f"P4.19 runtime case failed: {label}: {exc}") from exc

    success_record = _record(b"file", s["DIR_TMP"], s["OBJ_DAT"], flags=packed_flag, logical=66, storage=2, ptr=old)
    code = call(write) + phase1._jp_c(FAIL_PC)
    code += _check_word(table + 16, 66)
    code += _check_word(table + 18, old + 2)
    code += _check_byte(table + 12, 0)
    code += _check_bytes(old + 2, b"A" * 66)
    code += _check_byte(fake + 16, 0)
    code += _check_byte(od + s["OD_KIND_O"], s["OD_KIND_OBJECT"])
    code += _check_byte(od + s["OD_ACCESS_O"], write)
    code += _check_word(live, 1)
    execute("packed-write-private-decode-then-publish", code, success_record, packed_ok)

    bad_record = _record(b"file", s["DIR_TMP"], s["OBJ_DAT"], flags=packed_flag, logical=3, storage=1, ptr=old)
    code = call(write) + _jp_nc(FAIL_PC)
    code += bytes((0xFE, s["E_FORMAT"])) + phase1._jp_nz(FAIL_PC)
    code += _check_bytes(table, bad_record)
    code += _check_byte(old, packed_bad[0])
    code += _check_byte(fake + 16, s["HANDLE_FREE"])
    code += _check_byte(od + s["OD_KIND_O"], 0)
    code += _check_word(live, 1)
    execute("codec-failure-preserves-packed-and-hides-writer", code, bad_record, packed_bad)

    code = call(write) + _jp_nc(FAIL_PC)
    code += bytes((0xFE, s["E_NOMEM"])) + phase1._jp_nz(FAIL_PC)
    code += _check_bytes(table, success_record)
    code += _check_bytes(old, packed_ok)
    code += _check_byte(fake + 16, s["HANDLE_FREE"])
    code += _check_byte(od + s["OD_KIND_O"], 0)
    code += _check_word(live, 1)
    execute("allocation-failure-preserves-packed-and-hides-writer", code, success_record, packed_ok, free_len=2)

    empty = bytearray(success_record)
    empty[12] = 0
    empty[13] = 0
    empty[14:20] = bytes(6)
    code = call(write | trunc) + phase1._jp_c(FAIL_PC)
    code += _check_bytes(table, bytes(empty))
    code += _check_byte(fake + 16, 0)
    code += _check_word(live, 0)
    execute("trunc-packed-direct-empty-raw", code, success_record, packed_ok)

    code = call(write) + _jp_nc(FAIL_PC)
    code += bytes((0xFE, s["E_NOSPC"])) + phase1._jp_nz(FAIL_PC)
    code += _check_bytes(table, success_record)
    execute("resource-exhaustion-before-materialization", code, success_record, packed_ok, handles_full=True)


def dispatch(root: Path, action: str, step: str, *, sha256_file, run_command, require_project_tool):
    if step != "P4.19":
        raise DriverError(f"Phase-4 packed write step is not registered: {step}")
    assertions = _source_contract(root)
    failed = [x["name"] for x in assertions if x.get("passed") is not True]
    require(not failed, f"static P4.19 contract failures: {failed}")

    kernel_result, kernel, _ = phase1._assemble_kernel(root, run_command, require_project_tool)
    fixture_result, binary, listing = _assemble(root, run_command, require_project_tool)
    names = (
        "zx48_p419_open_existing", "p405_object_table", "open_description_table", "fake_process",
        "memory_free_extents", "memory_live_allocations", "ARENA_START", "ARENA_SIZE",
        "OD_KIND_O", "OD_ACCESS_O", "OD_KIND_OBJECT", "O_WRITE", "O_TRUNC",
        "OBJ_DAT", "OBJ_PACKED", "DIR_TMP", "HANDLE_FREE", "E_FORMAT", "E_NOMEM", "E_NOSPC",
    )
    symbols = phase3_open_descriptions._symbols(listing.with_suffix(".sym"), names)
    if action == "test":
        _runtime(root, symbols, binary.read_bytes())
        assertions += [
            {"name": "packed-write-materializes-before-return-runtime", "passed": True},
            {"name": "forced-allocation-error-preserves-packed-runtime", "passed": True},
            {"name": "forced-codec-error-preserves-packed-runtime", "passed": True},
            {"name": "failed-materialization-hides-writer-runtime", "passed": True},
            {"name": "trunc-packed-direct-empty-raw-runtime", "passed": True},
            {"name": "reservation-failure-precedes-object-mutation-runtime", "passed": True},
        ]

    hashes = {
        "v1/build/kernel.bin": sha256_file(kernel),
        "v1/build/p419-packed-write.bin": sha256_file(binary),
        "v1/src/kernel/objects.asm": sha256_file(root / "v1/src/kernel/objects.asm"),
        "v1/src/kernel/zxpack.asm": sha256_file(root / "v1/src/kernel/zxpack.asm"),
        "v1/tools-host/test-driver/phase4_packed_write.py": sha256_file(root / "v1/tools-host/test-driver/phase4_packed_write.py"),
        "v1/tools-host/test-driver/run.py": sha256_file(root / "v1/tools-host/test-driver/run.py"),
        "v1/dist/certification/P4.18.test.json": sha256_file(root / "v1/dist/certification/P4.18.test.json"),
    }
    return [kernel_result, fixture_result], hashes, assertions
