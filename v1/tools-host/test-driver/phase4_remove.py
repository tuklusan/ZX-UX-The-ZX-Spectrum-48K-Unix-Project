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
import phase4_list

MODULE_BASE = 0xC000
DATA_BASE = 0xA000
REQ_BASE = 0xA300
OUT_BASE = 0xA320
BCAT_BASE = 0xA500
PAYLOAD_BASE = 0xA600


class Phase4RemoveError(DriverError):
    """Raised when the P4.13 SYS_REMOVE contract regresses."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Phase4RemoveError(message)


def _word(value: int) -> bytes:
    return bytes((value & 0xFF, (value >> 8) & 0xFF))


def _jp_nc(address: int) -> bytes:
    return b"\xD2" + _word(address)


def _ld_a_mem(address: int) -> bytes:
    return b"\x3A" + _word(address)


def _ld_hl_mem(address: int) -> bytes:
    return b"\x2A" + _word(address)


def _record(name: bytes, directory: int, type_id: int, logical: int, storage: int, ptr: int, *, flags: int = 0) -> bytes:
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
    macro = objects.split("MACRO EMIT_P413_REMOVE_ROUTINES", 1)[1].split("ENDM", 1)[0]
    return [
        {"name": "remove-register-contract-is-path-in-hl", "passed": "HL=NUL-terminated path." in macro},
        {"name": "directory-and-device-are-protected", "passed": "cp PATH_KIND_DIR" in macro and "cp DIR_DEV" in macro and macro.count("zx48_p413_perm") >= 3},
        {"name": "catalog-only-bin-is-protected", "passed": "call zx48_p405_is_bcat" in macro and "jp z,zx48_p413_perm" in macro},
        {"name": "system-metadata-is-protected", "passed": "cp OBJ_SYS" in macro and "cp OBJ_FNT" in macro},
        {"name": "live-open-description-blocks-remove", "passed": "call zx48_object_no_open_references" in macro and "ret c" in macro},
        {"name": "payload-free-precedes-table-clear", "passed": macro.index("call zx48_free") < macro.index("ld bc,OBJ_RECORD_SIZE")},
        {"name": "odd-storage-rounded-before-free", "passed": "bit 0,c" in macro and "inc bc" in macro},
        {"name": "zxpack-candidate-state-cleared", "passed": all(x in macro for x in ("ld (zx_object_ptr),hl", "ld (zx_new_ptr),hl", "ld (zx_encoded_len),hl", "ld (zx_slot),a"))},
        {"name": "record-slot-cleared-as-one-bounded-record", "passed": "ld bc,OBJ_RECORD_SIZE" in macro and "ldir" in macro},
        {"name": "bcat-storage-never-mutated", "passed": "p412_bincat_ptr" not in macro and "p412_bcat_entry" not in macro},
        {"name": "allocator-corruption-panics", "passed": "ld a,PANIC_SCHEDULER" in macro and "jp zx48_panic" in macro},
    ]


def _assemble(root: Path, run_command: Callable[..., Any], require_project_tool: Callable[[Path, str | Path], Path]):
    assembler = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    fixture = build / "p413-remove.asm"
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
    INCLUDE "../src/kernel/handles.asm"
    INCLUDE "../src/kernel/syscall.asm"
    EMIT_NAMESPACE_ROUTINES
    EMIT_OBJECT_TYPE_ROUTINES
    EMIT_OBJECT_OPEN_ROUTINES
    EMIT_OBJECT_EXCLUSIVITY_ROUTINES
    EMIT_P406_EXCLUSIVITY_ROUTINES
zx48_od_create:
    ld a,E_NOSPC
    scf
    ret
    EMIT_USER_RANGE_VALIDATION_ROUTINE
    EMIT_P412_LIST_ROUTINES
    EMIT_P413_REMOVE_ROUTINES
zx48_free:
    ld (p413_test_free_ptr),hl
    ld (p413_test_free_len),bc
    ld a,(p413_test_free_count)
    inc a
    ld (p413_test_free_count),a
    xor a
    ret
zx48_panic:
    jp $0003
zx_object_ptr: dw 0
zx_new_ptr: dw 0
zx_encoded_len: dw 0
zx_slot: db 0
p413_test_free_count: db 0
p413_test_free_ptr: dw 0
p413_test_free_len: dw 0
fake_process: defs 48,0
    SAVEBIN "p413-remove.bin",$C000,$-$C000
""",
        encoding="utf-8",
        newline="\n",
    )
    result = run_command(
        [assembler, "--nologo", "--lst=p413-remove.lst", "--sym=p413-remove.sym", "p413-remove.asm"],
        cwd=build,
        timeout_seconds=30.0,
    )
    require(not result.timed_out and result.exit_code == 0, f"P4.13 fixture assembly failed: {result.stderr or result.stdout}")
    binary = build / "p413-remove.bin"
    listing = build / "p413-remove.lst"
    require(binary.is_file() and 0 < binary.stat().st_size < 16384, "P4.13 fixture binary missing/oversize")
    return result, binary, listing


def _target(root: Path, s: dict[str, int], module: bytes) -> None:
    paths = ("/tmp/gone", "/tmp/sys", "/tmp/missing", "/tmp", "/dev/tty", "/bin/sh", "/bin")
    addresses: dict[str, int] = {}
    payload = bytearray()
    cursor = DATA_BASE
    for path in paths:
        addresses[path] = cursor
        encoded = path.encode("ascii") + b"\0"
        payload += encoded
        cursor += len(encoded)

    table = s["p405_object_table"]
    od_table = s["open_description_table"]

    def patch(path: str, *, records: bytes = b"", open_slot: int | None = None, catalog: bytes = b"", seed_zx: bool = False):
        def apply(ram: bytearray) -> None:
            ram[MODULE_BASE - 0x4000:MODULE_BASE - 0x4000 + len(module)] = module
            ram[DATA_BASE - 0x4000:DATA_BASE - 0x4000 + len(payload)] = payload
            if records:
                ram[table - 0x4000:table - 0x4000 + len(records)] = records
            if open_slot is not None:
                off = od_table - 0x4000
                ram[off + 0] = s["OD_KIND_OBJECT"]
                ram[off + 1] = s["O_READ"]
                ram[off + 2] = 1
                ram[off + 3] = open_slot
            if catalog:
                ram[BCAT_BASE - 0x4000:BCAT_BASE - 0x4000 + len(catalog)] = catalog
            if seed_zx:
                ram[s["zx_object_ptr"] - 0x4000:s["zx_object_ptr"] - 0x4000 + 2] = _word(table)
                ram[s["zx_new_ptr"] - 0x4000:s["zx_new_ptr"] - 0x4000 + 2] = _word(PAYLOAD_BASE + 0x20)
                ram[s["zx_encoded_len"] - 0x4000:s["zx_encoded_len"] - 0x4000 + 2] = _word(3)
                ram[s["zx_slot"] - 0x4000] = 7
        return apply

    def mem_eq(address: int, expected: bytes) -> bytes:
        code = bytearray()
        for offset, value in enumerate(expected):
            code += _ld_a_mem(address + offset) + bytes((0xFE, value)) + phase1._jp_nz(FAIL_PC)
        return bytes(code)

    def word_eq(address: int, expected: int) -> bytes:
        code = _ld_hl_mem(address)
        code += bytes((0x7C, 0xFE, (expected >> 8) & 0xFF)) + phase1._jp_nz(FAIL_PC)
        code += bytes((0x7D, 0xFE, expected & 0xFF)) + phase1._jp_nz(FAIL_PC)
        return code

    def execute(label: str, code: bytes, patcher) -> None:
        body = bytes((0xF3,)) + phase1._ld_sp(0xBFC0) + code + phase1._jp(PASS_PC)
        try:
            run_sna(root, body, patch=patcher)
        except DriverError as exc:
            raise Phase4RemoveError(f"P4.13 target case failed: {label}: {exc}") from exc

    closed = _record(b"gone", s["DIR_TMP"], s["OBJ_DAT"], 5, 5, PAYLOAD_BASE)
    code = phase1._ld_hl(addresses["/tmp/gone"]) + phase1._call(s["zx48_p413_sys_remove"]) + phase1._jp_c(FAIL_PC)
    code += b"\x7C\xB5" + phase1._jp_nz(FAIL_PC)
    code += mem_eq(table, bytes(20))
    code += _ld_a_mem(s["p413_test_free_count"]) + b"\xFE\x01" + phase1._jp_nz(FAIL_PC)
    code += word_eq(s["p413_test_free_ptr"], PAYLOAD_BASE)
    code += word_eq(s["p413_test_free_len"], 6)
    code += word_eq(s["zx_object_ptr"], 0) + word_eq(s["zx_new_ptr"], 0) + word_eq(s["zx_encoded_len"], 0)
    code += _ld_a_mem(s["zx_slot"]) + b"\xB7" + phase1._jp_nz(FAIL_PC)
    execute("closed-object-freed-and-slot-cleared", code, patch("/tmp/gone", records=closed, seed_zx=True))

    code = phase1._ld_hl(addresses["/tmp/gone"]) + phase1._call(s["zx48_p413_sys_remove"]) + _jp_nc(FAIL_PC)
    code += bytes((0xFE, s["E_BUSY"])) + phase1._jp_nz(FAIL_PC)
    code += mem_eq(table, closed)
    code += _ld_a_mem(s["p413_test_free_count"]) + b"\xB7" + phase1._jp_nz(FAIL_PC)
    execute("open-object-busy-and-unchanged", code, patch("/tmp/gone", records=closed, open_slot=0))

    protected = _record(b"sys", s["DIR_TMP"], s["OBJ_SYS"], 4, 4, PAYLOAD_BASE)
    code = phase1._ld_hl(addresses["/tmp/sys"]) + phase1._call(s["zx48_p413_sys_remove"]) + _jp_nc(FAIL_PC)
    code += bytes((0xFE, s["E_PERM"])) + phase1._jp_nz(FAIL_PC)
    code += mem_eq(table, protected)
    execute("system-metadata-perm", code, patch("/tmp/sys", records=protected))

    for label, path in (("directory-perm", "/tmp"), ("device-perm", "/dev/tty"), ("catalog-only-perm", "/bin/sh")):
        code = phase1._ld_hl(addresses[path]) + phase1._call(s["zx48_p413_sys_remove"]) + _jp_nc(FAIL_PC)
        code += bytes((0xFE, s["E_PERM"])) + phase1._jp_nz(FAIL_PC)
        execute(label, code, patch(path))

    code = phase1._ld_hl(addresses["/tmp/missing"]) + phase1._call(s["zx48_p413_sys_remove"]) + _jp_nc(FAIL_PC)
    code += bytes((0xFE, s["E_NOENT"])) + phase1._jp_nz(FAIL_PC)
    execute("missing-noent", code, patch("/tmp/missing"))

    # Exact-name BCAT entry becomes visible immediately after its resident shadow is removed.
    shadow = _record(b"sh", s["DIR_BIN"], s["OBJ_BIN"], 2, 2, PAYLOAD_BASE)
    catalog = phase4_list._bcat([b"sh"])
    code = phase1._ld_hl(BCAT_BASE) + b"\x01" + _word(len(catalog)) + phase1._call(s["zx48_p412_bincat_admit"]) + phase1._jp_c(FAIL_PC)
    code += phase1._ld_hl(addresses["/bin/sh"]) + phase1._call(s["zx48_p413_sys_remove"]) + phase1._jp_c(FAIL_PC)
    ram_list_req = _word(addresses["/bin"]) + bytes((0, 0)) + _word(OUT_BASE)
    code += phase1._ld_hl(REQ_BASE) + phase1._call(s["zx48_p412_sys_list"]) + phase1._jp_c(FAIL_PC)
    expected = phase4_list._listout(b"sh", s["OBJ_BIN"], 0, 0xFFFF, s["STATE_TAPE_BACKED"], s["DIR_BIN"])
    code += mem_eq(OUT_BASE, expected)
    def shadow_patch(ram: bytearray) -> None:
        patch("/bin/sh", records=shadow, catalog=catalog)(ram)
        ram[REQ_BASE - 0x4000:REQ_BASE - 0x4000 + 6] = ram_list_req
    execute("removed-bin-shadow-reveals-bcat", code, shadow_patch)


def dispatch(
    root: Path,
    action: str,
    step: str,
    *,
    sha256_file: Callable[[Path], str],
    run_command: Callable[..., Any],
    require_project_tool: Callable[[Path, str | Path], Path],
):
    if step != "P4.13":
        raise DriverError(f"Phase-4 remove step is not registered: {step}")

    assertions = _source_contract(root)
    failed = [item["name"] for item in assertions if item.get("passed") is not True]
    require(not failed, f"static P4.13 contract failures: {failed}")

    kernel_result, kernel, _ = phase1._assemble_kernel(root, run_command, require_project_tool)
    fixture_result, binary, listing = _assemble(root, run_command, require_project_tool)
    commands = [kernel_result, fixture_result]
    names = (
        "zx48_p413_sys_remove", "zx48_p412_bincat_admit", "zx48_p412_sys_list",
        "p405_object_table", "open_description_table", "p413_test_free_count",
        "p413_test_free_ptr", "p413_test_free_len", "zx_object_ptr", "zx_new_ptr",
        "zx_encoded_len", "zx_slot", "OD_KIND_OBJECT", "O_READ", "OBJ_BIN",
        "OBJ_DAT", "OBJ_SYS", "DIR_BIN", "DIR_TMP", "STATE_TAPE_BACKED",
        "E_BUSY", "E_PERM", "E_NOENT",
    )
    symbols = phase3_open_descriptions._symbols(listing.with_suffix(".sym"), names)

    if action == "test":
        _target(root, symbols, binary.read_bytes())
        assertions.extend([
            {"name": "closed-object-freed-and-slot-cleared-runtime", "passed": True},
            {"name": "open-object-ebusy-unchanged-runtime", "passed": True},
            {"name": "protected-pseudo-catalog-eperm-runtime", "passed": True},
            {"name": "missing-object-enoent-runtime", "passed": True},
            {"name": "zxpack-candidate-state-cleared-runtime", "passed": True},
            {"name": "bin-shadow-removal-reveals-bcat-runtime", "passed": True},
        ])

    hashes = {
        "v1/build/kernel.bin": sha256_file(kernel),
        "v1/build/p413-remove.bin": sha256_file(binary),
        "v1/src/kernel/objects.asm": sha256_file(root / "v1/src/kernel/objects.asm"),
        "v1/tools-host/test-driver/phase4_remove.py": sha256_file(root / "v1/tools-host/test-driver/phase4_remove.py"),
        "v1/tools-host/test-driver/run.py": sha256_file(root / "v1/tools-host/test-driver/run.py"),
        "v1/dist/certification/P4.12.test.json": sha256_file(root / "v1/dist/certification/P4.12.test.json"),
    }
    return commands, hashes, assertions
