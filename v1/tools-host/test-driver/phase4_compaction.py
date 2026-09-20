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


class P426Error(DriverError):
    pass


def require(ok: bool, msg: str) -> None:
    if not ok:
        raise P426Error(msg)


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


def _record(name: bytes, directory: int, type_id: int, *, flags: int = 0, state: int = 0, logical: int = 0, storage: int = 0, ptr: int = 0) -> bytes:
    raw = bytearray(20)
    raw[:len(name)] = name
    raw[10] = directory
    raw[11] = type_id
    raw[12] = flags
    raw[13] = state
    raw[14:16] = _word(logical)
    raw[16:18] = _word(storage)
    raw[18:20] = _word(ptr)
    return bytes(raw)


def _source_contract(root: Path) -> list[dict[str, object]]:
    memory = (root / "v1/src/kernel/memory.asm").read_text(encoding="utf-8")
    zx = (root / "v1/src/kernel/zxpack.asm").read_text(encoding="utf-8")
    require("MACRO EMIT_P426_COMPACT_ALLOC_ROUTINES" in memory, "P4.26 allocator wrapper macro missing")
    require("MACRO EMIT_P426_COMPACTION_ROUTINES" in zx, "P4.26 victim service macro missing")
    mm = memory.split("MACRO EMIT_P426_COMPACT_ALLOC_ROUTINES", 1)[1].split("ENDM", 1)[0]
    zm = zx.split("MACRO EMIT_P426_COMPACTION_ROUTINES", 1)[1].split("ENDM", 1)[0]
    return [
        {"name": "only-any-cold-failure-may-compact", "passed": "bit 7,a" in mm and "cp ALLOC_FAST_REQUIRED" in mm},
        {"name": "depth-guard-nonrecursive", "passed": "p426_compact_depth" in mm and "or ALLOC_NO_COMPACT" in mm},
        {"name": "one-victim-call-and-one-retry", "passed": mm.count("call zx48_p426_try_one_victim") == 1 and mm.count("jp zx48_alloc") == 1},
        {"name": "independent-of-pack-candidate", "passed": "p424_candidate_bits" not in zm},
        {"name": "largest-logical-selection", "passed": all(x in zm for x in ("p426_best_length", "p426_candidate_length", "sbc hl,de"))},
        {"name": "exact-path-name-tiebreak", "passed": "zx48_p426_name_compare:" in zm and "OBJ_DIR_ID" in zm and "cp 10" in zm},
        {"name": "raw-mutable-closed-only", "passed": all(x in zm for x in ("OBJ_TYPE_ID", "OBJ_RESERVED_BYTE", "STATE_RAM", "OBJ_PACKED", "zx48_od_object_any_live"))},
        {"name": "direct-owner-exclusion", "passed": "p426_direct_owner_bits" in zm and "zx48_p426_direct_owner_test" in zm},
        {"name": "exact-512-dry-run", "passed": "call zx48_p420_workspace_begin" in zm and "ld bc,512" in zm},
        {"name": "exact-destination-preflight", "passed": "p426_encoded_length" in zm and "p426_probe_dest" in zm and "p426_probe_workspace" in zm},
        {"name": "guarded-probe-allocations", "passed": zm.count("ALLOC_COLD_PREFERRED|ALLOC_NO_COMPACT") >= 2},
        {"name": "single-pack-transaction", "passed": zm.count("call zx48_p422_pack_record") == 1},
    ]


def _assemble(root: Path, run_command: Callable[..., Any], require_project_tool: Callable[[Path, str | Path], Path]):
    asm = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    fixture = build / "p426-compaction.asm"
    fixture.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
PANIC_SCHEDULER EQU $03
PROC_HANDLES EQU 16
PROC_CWD EQU 28
    ORG $C000
current_pid: db 0
zx48_process_lookup:
    ld ix,fake_process
    xor a
    ret
    INCLUDE "../src/kernel/memory.asm"
    INCLUDE "../src/kernel/handles.asm"
    INCLUDE "../src/kernel/objects.asm"
    INCLUDE "../src/kernel/zxpack.asm"
    EMIT_MEMORY_ROUTINES
    EMIT_P426_COMPACT_ALLOC_ROUTINES
    EMIT_NAMESPACE_ROUTINES
    EMIT_OBJECT_TYPE_ROUTINES
    EMIT_OBJECT_OPEN_ROUTINES
    EMIT_HANDLE_ROUTINES
    EMIT_P406_EXCLUSIVITY_ROUTINES
    EMIT_P416_ZXP1_DECODER
    EMIT_P420_TARGET_ENCODER_ROUTINES
    EMIT_P422_SYS_PACK_CODEC_ROUTINES
    EMIT_P424_PACK_CANDIDATE_ROUTINES
    EMIT_P426_COMPACTION_ROUTINES
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
    SAVEBIN "p426-compaction.bin",$C000,$-$C000
""", encoding="utf-8", newline="\n")
    result = run_command([asm, "--nologo", "--lst=p426-compaction.lst", "--sym=p426-compaction.sym", "p426-compaction.asm"], cwd=build, timeout_seconds=30.0)
    require(not result.timed_out and result.exit_code == 0, f"P4.26 fixture assembly failed: {result.stderr or result.stdout}")
    binary = build / "p426-compaction.bin"
    listing = build / "p426-compaction.lst"
    require(binary.is_file() and 0 < binary.stat().st_size < 16384, "P4.26 fixture binary missing/oversize")
    return result, binary, listing


def _runtime(root: Path, s: dict[str, int], module: bytes) -> None:
    table = s["p405_object_table"]
    od = s["open_description_table"]
    free = s["memory_free_extents"]
    live = s["memory_live_allocations"]
    direct = s["p426_direct_owner_bits"]
    old = s["ARENA_START"]
    arena = s["ARENA_SIZE"]

    def patch(records: list[bytes], payloads: list[tuple[int, bytes]], *, free_start: int, free_len: int, live_count: int, open_slot: int | None = None, direct_bits: bytes = b"\x00\x00\x00\x00"):
        def apply(ram: bytearray) -> None:
            ram[MODULE_BASE-0x4000:MODULE_BASE-0x4000+len(module)] = module
            ram[table-0x4000:table-0x4000+640] = bytes(640)
            for index, record in enumerate(records):
                ram[table-0x4000+index*20:table-0x4000+(index+1)*20] = record
            for ptr, data in payloads:
                ram[ptr-0x4000:ptr-0x4000+len(data)] = data
            ram[od-0x4000:od-0x4000+s["OPEN_DESCRIPTION_COUNT"]*8] = bytes(s["OPEN_DESCRIPTION_COUNT"]*8)
            if open_slot is not None:
                ram[od-0x4000:od-0x4000+8] = bytes((s["OD_KIND_OBJECT"], s["O_READ"], 1, open_slot, 0, 0, 0, 0))
            ram[direct-0x4000:direct-0x4000+4] = direct_bits
            ram[free-0x4000:free-0x4000+64] = bytes(64)
            ram[free-0x4000:free-0x4000+4] = _word(free_start) + _word(free_len)
            ram[live-0x4000:live-0x4000+2] = _word(live_count)
        return apply

    def execute(label: str, code: bytes, patcher) -> None:
        body = b"\xF3" + phase1._ld_sp(STACK_TOP) + code + phase1._jp(PASS_PC)
        try:
            run_sna(root, body, patch=patcher)
        except DriverError as exc:
            raise P426Error(f"P4.26 runtime case failed: {label}: {exc}") from exc

    def raw(name: bytes, length: int, ptr: int) -> bytes:
        return _record(name, s["DIR_TMP"], s["OBJ_DAT"], state=s["STATE_RAM"], logical=length, storage=length, ptr=ptr)

    r80a = raw(b"a", 80, old)
    r100b = raw(b"b", 100, old + 80)
    code = phase1._call(s["zx48_p426_try_one_victim"]) + phase1._jp_c(FAIL_PC)
    code += _check_byte(s["p426_victim_attempted"], 1) + _check_byte(s["p426_victim_succeeded"], 1)
    code += _check_byte(table + 12, 0) + _check_byte(table + 20 + 12, s["OBJ_PACKED"])
    execute("largest-logical-victim", code, patch([r80a, r100b], [(old, b"A"*80), (old+80, b"B"*100)], free_start=old+180, free_len=arena-180, live_count=2))

    r80z = raw(b"z", 80, old)
    r80a2 = raw(b"a", 80, old + 80)
    code = phase1._call(s["zx48_p426_try_one_victim"]) + phase1._jp_c(FAIL_PC)
    code += _check_byte(table + 12, 0) + _check_byte(table + 20 + 12, s["OBJ_PACKED"])
    execute("exact-name-tiebreak", code, patch([r80z, r80a2], [(old, b"Z"*80), (old+80, b"A"*80)], free_start=old+160, free_len=arena-160, live_count=2))

    r120 = raw(b"a", 120, old)
    r80 = raw(b"b", 80, old + 120)
    code = phase1._call(s["zx48_p426_try_one_victim"]) + phase1._jp_c(FAIL_PC)
    code += _check_byte(table + 12, 0) + _check_byte(table + 20 + 12, s["OBJ_PACKED"])
    execute("open-largest-excluded", code, patch([r120, r80], [(old, b"A"*120), (old+120, b"B"*80)], free_start=old+200, free_len=arena-200, live_count=2, open_slot=0))

    code = phase1._call(s["zx48_p426_try_one_victim"]) + phase1._jp_c(FAIL_PC)
    code += _check_byte(table + 12, 0) + _check_byte(table + 20 + 12, s["OBJ_PACKED"])
    execute("direct-owner-largest-excluded", code, patch([r120, r80], [(old, b"A"*120), (old+120, b"B"*80)], free_start=old+200, free_len=arena-200, live_count=2, direct_bits=b"\x01\x00\x00\x00"))

    incompress = bytes(range(80))
    r90bad = raw(b"a", 80, old)
    r70good = raw(b"b", 70, old + 80)
    code = phase1._call(s["zx48_p426_try_one_victim"]) + phase1._jp_c(FAIL_PC)
    code += _check_byte(s["p426_victim_attempted"], 1) + _check_byte(s["p426_victim_succeeded"], 0)
    code += _check_byte(table + 12, 0) + _check_byte(table + 20 + 12, 0)
    code += _check_bytes(old, incompress[:8])
    execute("one-victim-no-fallthrough", code, patch([r90bad, r70good], [(old, incompress), (old+80, b"B"*70)], free_start=old+150, free_len=arena-150, live_count=2))

    r80 = raw(b"a", 80, old)
    code = phase1._call(s["zx48_p426_try_one_victim"]) + phase1._jp_c(FAIL_PC)
    code += _check_byte(s["p426_victim_attempted"], 1) + _check_byte(s["p426_victim_succeeded"], 0)
    code += _check_bytes(table, r80) + _check_bytes(old, b"A"*8)
    execute("insufficient-512-scratch-preserves-state", code, patch([r80], [(old, b"A"*80)], free_start=old+80, free_len=510, live_count=1))

    code = bytes((0x3E, s["ALLOC_ANY"] | s["ALLOC_NO_COMPACT"])) + b"\x01" + _word(600)
    code += phase1._call(s["zx48_p426_alloc"]) + _jp_nc(FAIL_PC)
    code += bytes((0xFE, s["E_NOMEM"])) + phase1._jp_nz(FAIL_PC)
    code += _check_byte(s["p426_victim_attempted"], 0) + _check_bytes(table, r80)
    execute("no-compact-guard-blocks-recursion", code, patch([r80], [(old, b"A"*80)], free_start=old+80, free_len=510, live_count=1))

    code = bytes((0x3E, s["ALLOC_ANY"])) + b"\x01" + _word(600)
    code += phase1._call(s["zx48_p426_alloc"]) + _jp_nc(FAIL_PC)
    code += bytes((0xFE, s["E_NOMEM"])) + phase1._jp_nz(FAIL_PC)
    code += _check_byte(s["p426_victim_attempted"], 1) + _check_byte(s["p426_victim_succeeded"], 0)
    code += _check_bytes(table, r80)
    execute("ordinary-pressure-attempts-exactly-one-victim", code, patch([r80], [(old, b"A"*80)], free_start=old+80, free_len=512, live_count=1))


def dispatch(root: Path, action: str, step: str, *, sha256_file, run_command, require_project_tool):
    if step != "P4.26":
        raise DriverError(f"Phase-4 compaction step is not registered: {step}")
    assertions = _source_contract(root)
    failed = [x["name"] for x in assertions if x.get("passed") is not True]
    require(not failed, f"static P4.26 contract failures: {failed}")
    kr, kernel, _ = phase1._assemble_kernel(root, run_command, require_project_tool)
    fr, binary, listing = _assemble(root, run_command, require_project_tool)
    names = (
        "zx48_p426_alloc", "zx48_p426_try_one_victim", "p426_victim_attempted", "p426_victim_succeeded",
        "p426_direct_owner_bits", "p405_object_table", "open_description_table", "memory_free_extents",
        "memory_live_allocations", "ARENA_START", "ARENA_SIZE", "OPEN_DESCRIPTION_COUNT",
        "OD_KIND_OBJECT", "O_READ", "DIR_TMP", "OBJ_DAT", "OBJ_PACKED", "STATE_RAM",
        "ALLOC_ANY", "ALLOC_NO_COMPACT", "E_NOMEM",
    )
    symbols = phase3_open_descriptions._symbols(listing.with_suffix(".sym"), names)
    if action == "test":
        _runtime(root, symbols, binary.read_bytes())
        assertions += [
            {"name": "largest-logical-victim-runtime", "passed": True},
            {"name": "exact-name-tiebreak-runtime", "passed": True},
            {"name": "open-and-direct-owner-exclusions-runtime", "passed": True},
            {"name": "one-victim-limit-runtime", "passed": True},
            {"name": "scratch-destination-preflight-runtime", "passed": True},
            {"name": "no-compact-depth-guard-runtime", "passed": True},
            {"name": "ordinary-pressure-one-attempt-runtime", "passed": True},
        ]
    hashes = {
        "v1/build/kernel.bin": sha256_file(kernel),
        "v1/build/p426-compaction.bin": sha256_file(binary),
        "v1/src/kernel/memory.asm": sha256_file(root / "v1/src/kernel/memory.asm"),
        "v1/src/kernel/zxpack.asm": sha256_file(root / "v1/src/kernel/zxpack.asm"),
        "v1/tools-host/test-driver/phase4_compaction.py": sha256_file(root / "v1/tools-host/test-driver/phase4_compaction.py"),
        "v1/tools-host/test-driver/run.py": sha256_file(root / "v1/tools-host/test-driver/run.py"),
        "v1/dist/certification/P4.25.test.json": sha256_file(root / "v1/dist/certification/P4.25.test.json"),
    }
    return [kr, fr], hashes, assertions
