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
STATE0 = 0xA000
STATE1 = 0xA200
SENTINEL = 0xA500


class P417Error(DriverError):
    pass


def require(ok: bool, msg: str) -> None:
    if not ok:
        raise P417Error(msg)


def _source_contract(root: Path) -> list[dict[str, object]]:
    zx = (root / "v1/src/kernel/zxpack.asm").read_text(encoding="utf-8")
    hd = (root / "v1/src/kernel/handles.asm").read_text(encoding="utf-8")
    zm = zx.split("MACRO EMIT_P417_PACKED_READER_STATE_ROUTINES", 1)[1].split("ENDM", 1)[0]
    hm = hd.split("MACRO EMIT_P417_PACKED_OD_ROUTINES", 1)[1].split("ENDM", 1)[0]
    return [
        {"name": "exact-256-plus-16-layout", "passed": all(x in zx for x in (
            "P417_HISTORY_SIZE             EQU 256",
            "P417_CONTROL_SIZE             EQU 16",
            "P417_STATE_SIZE               EQU 272",
            "P417_CONTROL_O                EQU 256",
        ))},
        {"name": "control-fields-frozen", "passed": all(x in zx for x in (
            "P417_CTRL_PHYSICAL_POS_O", "P417_CTRL_LOGICAL_POS_O",
            "P417_CTRL_HISTORY_INDEX_O", "P417_CTRL_HISTORY_COUNT_O",
            "P417_CTRL_PENDING_KIND_O", "P417_CTRL_PENDING_COUNT_O",
            "P417_CTRL_PARAMETER_O",
        ))},
        {"name": "state-init-exact-size", "passed": "ld bc,P417_STATE_SIZE-1" in zm and "ldir" in zm},
        {"name": "packed-readonly-only", "passed": "and O_READ|O_WRITE" in hm and "cp O_READ" in hm and "and OBJ_PACKED" in hm},
        {"name": "exact-272-cold-allocation", "passed": "ld bc,PACKED_READER_STATE_SIZE" in hm and "ld a,ALLOC_COLD_PREFERRED" in hm and "call zx48_alloc" in hm},
        {"name": "state-attached-to-shared-od", "passed": "(ix+OD_AUX_O)" in hm and "(ix+OD_AUX_O+1)" in hm},
        {"name": "enomem-rolls-back-description", "passed": "zx48_p417_od_alloc_fail:" in hm and "call zx48_od_release" in hm},
        {"name": "final-release-frees-272", "passed": "ld bc,PACKED_READER_STATE_SIZE" in hd and "call zx48_free" in hd},
        {"name": "retain-does-not-allocate", "passed": "zx48_od_retain:" in hd and "zx48_alloc" not in hd.split("zx48_od_retain:",1)[1].split("zx48_od_release:",1)[0]},
    ]


def _assemble(root: Path, run_command: Callable[..., Any], require_project_tool: Callable[[Path, str | Path], Path]):
    asm = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    fixture = build / "p417-packed-state.asm"
    fixture.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
PANIC_SCHEDULER EQU $03
PROC_HANDLES EQU 16
    INCLUDE "../src/kernel/handles.asm"
    INCLUDE "../src/kernel/zxpack.asm"
    ORG $C000
current_pid: db 1
zx48_process_lookup:
    scf
    ret
zx48_pipe_endpoint_closed:
    xor a
    ret
zx48_panic:
    jp $B001

test_alloc_mode: db 0
test_alloc_calls: db 0
test_alloc_bad: db 0
test_next_ptr: dw $A000
test_free_calls: db 0
test_free_ptr: dw 0
test_free_len: dw 0

zx48_alloc:
    push af
    ld a,b
    cp 1
    jr nz,test_alloc_bad_req
    ld a,c
    cp $10
    jr nz,test_alloc_bad_req
    pop af
    cp ALLOC_COLD_PREFERRED
    jr nz,test_alloc_bad_policy
    jr test_alloc_checked
test_alloc_bad_req:
    pop af
test_alloc_bad_policy:
    ld a,1
    ld (test_alloc_bad),a
test_alloc_checked:
    ld a,(test_alloc_calls)
    inc a
    ld (test_alloc_calls),a
    ld a,(test_alloc_mode)
    or a
    jr nz,test_alloc_fail
    ld hl,(test_next_ptr)
    push hl
    ld de,$0200
    add hl,de
    ld (test_next_ptr),hl
    pop hl
    xor a
    ret
test_alloc_fail:
    ld a,E_NOMEM
    scf
    ret

zx48_free:
    ld (test_free_ptr),hl
    ld (test_free_len),bc
    ld a,(test_free_calls)
    inc a
    ld (test_free_calls),a
    xor a
    ret

    EMIT_HANDLE_ROUTINES
    EMIT_P417_PACKED_READER_STATE_ROUTINES
    EMIT_P417_PACKED_OD_ROUTINES
    SAVEBIN "p417-packed-state.bin",$C000,$-$C000
""", encoding="utf-8", newline="\n")
    result = run_command([asm, "--nologo", "--lst=p417-packed-state.lst", "--sym=p417-packed-state.sym", "p417-packed-state.asm"], cwd=build, timeout_seconds=30.0)
    require(not result.timed_out and result.exit_code == 0, f"P4.17 fixture assembly failed: {result.stderr or result.stdout}")
    binary = build / "p417-packed-state.bin"
    listing = build / "p417-packed-state.lst"
    require(binary.is_file() and 0 < binary.stat().st_size < 8192, "P4.17 fixture binary missing/oversize")
    return result, binary, listing


def _ld_mem_a(address: int) -> bytes:
    return b"\x32" + phase1._word(address)


def _check_byte(address: int, value: int) -> bytes:
    return b"\x3A" + phase1._word(address) + bytes((0xFE, value)) + phase1._jp_nz(FAIL_PC)


def _check_word(address: int, value: int) -> bytes:
    return b"\x2A" + phase1._word(address) + phase1._ld_de(value) + b"\xB7\xED\x52" + phase1._jp_nz(FAIL_PC)


def _call_create(s: dict[str, int], flags: int, access: int, identity: int) -> bytes:
    return bytes((0x3E, flags, 0x06, s["OD_KIND_OBJECT"], 0x0E, access, 0x16, identity)) + phase1._call(s["zx48_p417_od_create"])


def _runtime(root: Path, s: dict[str, int], module: bytes) -> None:
    table = s["open_description_table"]
    aux = s["OD_AUX_O"]
    refs = s["OD_REFS_O"]
    offset = s["OD_OFFSET_O"]
    rec = s["OD_COMPACT_SIZE"]
    packed = s["OBJ_PACKED"]
    read = s["O_READ"]
    write = s["O_WRITE"]

    code = bytearray(b"\xF3")
    code += phase1._ld_sp(STACK_TOP) + phase1._call(s["zx48_handles_init"])
    code += _call_create(s, packed, read, 7) + phase1._jp_c(FAIL_PC)
    code += bytes((0xFE, 0)) + phase1._jp_nz(FAIL_PC)
    code += _check_word(table + aux, STATE0) + _check_byte(table + refs, 1)
    code += _call_create(s, packed, read, 7) + phase1._jp_c(FAIL_PC)
    code += bytes((0xFE, 1)) + phase1._jp_nz(FAIL_PC)
    code += _check_word(table + rec + aux, STATE1) + _check_byte(s["test_alloc_calls"], 2) + _check_byte(s["test_alloc_bad"], 0)

    for a in (STATE0, STATE0 + 255, STATE0 + s["P417_CTRL_PHYSICAL_POS_O"], STATE0 + s["P417_CTRL_LOGICAL_POS_O"],
              STATE0 + s["P417_CTRL_HISTORY_INDEX_O"], STATE0 + s["P417_CTRL_HISTORY_COUNT_O"],
              STATE0 + s["P417_CTRL_PENDING_KIND_O"], STATE0 + s["P417_CTRL_PENDING_COUNT_O"],
              STATE0 + s["P417_CTRL_PARAMETER_O"], STATE0 + 271):
        code += _check_byte(a, 0)

    code += bytes((0x3E, 0x11)) + _ld_mem_a(STATE0 + s["P417_CTRL_LOGICAL_POS_O"])
    code += bytes((0x3E, 0x22)) + _ld_mem_a(STATE1 + s["P417_CTRL_LOGICAL_POS_O"])
    code += _check_byte(STATE0 + s["P417_CTRL_LOGICAL_POS_O"], 0x11)
    code += _check_byte(STATE1 + s["P417_CTRL_LOGICAL_POS_O"], 0x22)

    code += bytes((0x3E, 0)) + phase1._call(s["zx48_od_retain"]) + phase1._jp_c(FAIL_PC)
    code += _check_byte(table + refs, 2) + _check_word(table + aux, STATE0) + _check_byte(s["test_alloc_calls"], 2)
    code += bytes((0x3E, 0x34)) + _ld_mem_a(table + offset)
    code += _check_byte(table + offset, 0x34)

    code += bytes((0x3E, 0)) + phase1._call(s["zx48_od_release"]) + phase1._jp_c(FAIL_PC)
    code += _check_byte(table + refs, 1) + _check_byte(s["test_free_calls"], 0)
    code += bytes((0x3E, 0)) + phase1._call(s["zx48_od_release"]) + phase1._jp_c(FAIL_PC)
    code += _check_byte(s["test_free_calls"], 1) + _check_word(s["test_free_ptr"], STATE0) + _check_word(s["test_free_len"], 272)
    code += _check_byte(table, 0)
    code += bytes((0x3E, 1)) + phase1._call(s["zx48_od_release"]) + phase1._jp_c(FAIL_PC)
    code += _check_byte(s["test_free_calls"], 2) + _check_word(s["test_free_ptr"], STATE1)

    code += _call_create(s, 0, read, 8) + phase1._jp_c(FAIL_PC)
    code += _check_word(table + aux, 0) + _check_byte(s["test_alloc_calls"], 2)
    code += bytes((0x3E, 0)) + phase1._call(s["zx48_od_release"]) + phase1._jp_c(FAIL_PC)
    code += _call_create(s, packed, write, 8) + phase1._jp_c(FAIL_PC)
    code += _check_word(table + aux, 0) + _check_byte(s["test_alloc_calls"], 2)
    code += bytes((0x3E, 0)) + phase1._call(s["zx48_od_release"]) + phase1._jp_c(FAIL_PC)
    code += phase1._jp(PASS_PC)

    def patch(ram: bytearray) -> None:
        ram[MODULE_BASE-0x4000:MODULE_BASE-0x4000+len(module)] = module
        ram[STATE0-0x4000:STATE0-0x4000+272] = b"\xA5" * 272
        ram[STATE1-0x4000:STATE1-0x4000+272] = b"\xA5" * 272

    run_sna(root, bytes(code), patch=patch)

    fail = bytearray(b"\xF3")
    fail += phase1._ld_sp(STACK_TOP) + phase1._call(s["zx48_handles_init"])
    fail += bytes((0x3E, 1)) + _ld_mem_a(s["test_alloc_mode"])
    fail += bytes((0x3E, 0x5A)) + _ld_mem_a(SENTINEL)
    fail += _call_create(s, packed, read, 9)
    fail += b"\xD2" + phase1._word(FAIL_PC)
    fail += bytes((0xFE, s["E_NOMEM"])) + phase1._jp_nz(FAIL_PC)
    fail += _check_byte(table, 0) + _check_byte(s["test_alloc_calls"], 1) + _check_byte(s["test_free_calls"], 0)
    fail += _check_byte(SENTINEL, 0x5A) + phase1._jp(PASS_PC)

    def patch_fail(ram: bytearray) -> None:
        ram[MODULE_BASE-0x4000:MODULE_BASE-0x4000+len(module)] = module
        for name in ("test_alloc_calls", "test_free_calls", "test_alloc_bad"):
            ram[s[name]-0x4000] = 0

    run_sna(root, bytes(fail), patch=patch_fail)


def dispatch(root: Path, action: str, step: str, *, sha256_file, run_command, require_project_tool):
    if step != "P4.17":
        raise DriverError(f"Phase-4 packed reader-state step is not registered: {step}")
    assertions = _source_contract(root)
    failed = [x["name"] for x in assertions if x.get("passed") is not True]
    require(not failed, f"static P4.17 contract failures: {failed}")
    kernel_result, kernel, _ = phase1._assemble_kernel(root, run_command, require_project_tool)
    fixture_result, binary, listing = _assemble(root, run_command, require_project_tool)
    names = (
        "zx48_handles_init", "zx48_p417_od_create", "zx48_od_retain", "zx48_od_release",
        "open_description_table", "OD_AUX_O", "OD_REFS_O", "OD_OFFSET_O", "OD_COMPACT_SIZE",
        "OD_KIND_OBJECT", "OBJ_PACKED", "O_READ", "O_WRITE", "E_NOMEM",
        "P417_CTRL_PHYSICAL_POS_O", "P417_CTRL_LOGICAL_POS_O", "P417_CTRL_HISTORY_INDEX_O",
        "P417_CTRL_HISTORY_COUNT_O", "P417_CTRL_PENDING_KIND_O", "P417_CTRL_PENDING_COUNT_O",
        "P417_CTRL_PARAMETER_O", "test_alloc_mode", "test_alloc_calls", "test_alloc_bad",
        "test_free_calls", "test_free_ptr", "test_free_len",
    )
    symbols = phase3_open_descriptions._symbols(listing.with_suffix(".sym"), names)
    if action == "test":
        _runtime(root, symbols, binary.read_bytes())
        assertions += [
            {"name": "independent-opens-distinct-272-state-runtime", "passed": True},
            {"name": "control-layout-zeroed-runtime", "passed": True},
            {"name": "interleaved-state-independent-runtime", "passed": True},
            {"name": "dup-inheritance-retain-shares-state-runtime", "passed": True},
            {"name": "final-reference-frees-state-runtime", "passed": True},
            {"name": "nonpacked-and-writable-no-state-runtime", "passed": True},
            {"name": "forced-state-allocation-enomem-rollback-runtime", "passed": True},
        ]
    hashes = {
        "v1/build/kernel.bin": sha256_file(kernel),
        "v1/build/p417-packed-state.bin": sha256_file(binary),
        "v1/src/kernel/zxpack.asm": sha256_file(root / "v1/src/kernel/zxpack.asm"),
        "v1/src/kernel/handles.asm": sha256_file(root / "v1/src/kernel/handles.asm"),
        "v1/tools-host/test-driver/phase4_packed_state.py": sha256_file(root / "v1/tools-host/test-driver/phase4_packed_state.py"),
        "v1/tools-host/test-driver/run.py": sha256_file(root / "v1/tools-host/test-driver/run.py"),
        "v1/dist/certification/P4.16.test.json": sha256_file(root / "v1/dist/certification/P4.16.test.json"),
    }
    return [kernel_result, fixture_result], hashes, assertions
