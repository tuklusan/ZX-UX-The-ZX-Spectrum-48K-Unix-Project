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
import phase4_rename

MODULE_BASE = 0xC000
DATA_BASE = 0xA000
REQ_BASE = 0xA300
PAYLOAD_A = 0xA600
PAYLOAD_B = 0xA680


class P415Error(DriverError):
    pass


def require(ok: bool, msg: str) -> None:
    if not ok:
        raise P415Error(msg)


def _source_contract(root: Path) -> list[dict[str, object]]:
    text = (root / "v1/src/kernel/objects.asm").read_text(encoding="utf-8")
    m = text.split("MACRO EMIT_P415_RENAME_REPLACEMENT_ROUTINES", 1)[1].split("ENDM", 1)[0]
    publish = m.index("Single metadata publication step")
    free = m.index("call zx48_free")
    return [
        {"name": "delegates-p414-unless-distinct-destination", "passed": "call zx48_p414_sys_rename" in m and "cp E_EXIST" in m},
        {"name": "source-and-destination-closed-before-commit", "passed": m.count("call zx48_object_no_open_references") == 2},
        {"name": "records-validated-before-commit", "passed": m.count("call zx48_p415_record_validate") == 2 and m.rindex("call zx48_p415_record_validate") < publish},
        {"name": "destination-compatibility-before-commit", "passed": "call zx48_object_public_type_allowed" in m and m.index("call zx48_object_public_type_allowed") < publish},
        {"name": "publish-before-old-destination-free", "passed": publish < free},
        {"name": "source-cleared-after-free", "passed": free < m.index("zx48_p415_remove_source:")},
        {"name": "payload-alias-rejected-precommit", "passed": "jr z,zx48_p415_invalid" in m[:publish]},
        {"name": "no-payload-copy-or-recompression", "passed": "zx48_alloc" not in m and "zx48_zxpack" not in m},
    ]


def _assemble(root: Path, run_command: Callable[..., Any], require_project_tool: Callable[[Path, str | Path], Path]):
    asm = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    fixture = build / "p415-rename-replace.asm"
    fixture.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
PANIC_SCHEDULER EQU $03
PROC_CWD EQU 28
    ORG $C000
current_pid: db 1
zx48_process_lookup:
    ld ix,fake_process
    xor a
    ret
zx48_od_create:
    xor a
    ret
    INCLUDE "../src/kernel/handles.asm"
    INCLUDE "../src/kernel/objects.asm"
    INCLUDE "../src/kernel/syscall.asm"
    EMIT_NAMESPACE_ROUTINES
    EMIT_OBJECT_TYPE_ROUTINES
    EMIT_OBJECT_OPEN_ROUTINES
    EMIT_USER_RANGE_VALIDATION_ROUTINE
    EMIT_P406_EXCLUSIVITY_ROUTINES
    EMIT_OBJECT_EXCLUSIVITY_ROUTINES
    EMIT_P414_RENAME_ROUTINES
    EMIT_P415_RENAME_REPLACEMENT_ROUTINES
zx48_free:
    ld (test_free_ptr),hl
    ld (test_free_len),bc
    ld a,1
    ld (test_free_seen),a
    xor a
    ret
zx48_panic:
    scf
    ret
test_free_ptr: dw 0
test_free_len: dw 0
test_free_seen: db 0
fake_process: defs 48,0
    SAVEBIN "p415-rename-replace.bin",$C000,$-$C000
""", encoding="utf-8", newline="\n")
    result = run_command([asm, "--nologo", "--lst=p415-rename-replace.lst", "--sym=p415-rename-replace.sym", "p415-rename-replace.asm"], cwd=build, timeout_seconds=30.0)
    require(not result.timed_out and result.exit_code == 0, f"P4.15 fixture assembly failed: {result.stderr or result.stdout}")
    binary = build / "p415-rename-replace.bin"
    listing = build / "p415-rename-replace.lst"
    require(binary.is_file() and 0 < binary.stat().st_size < 24576, "P4.15 fixture binary missing/oversize")
    return result, binary, listing


def _target(root: Path, s: dict[str, int], module: bytes) -> None:
    paths = ("/tmp/foo", "/tmp/bar", "/tmp/tool", "/bin/tool")
    addrs: dict[str, int] = {}
    data = bytearray()
    p = DATA_BASE
    for name in paths:
        addrs[name] = p
        b = name.encode("ascii") + b"\0"
        data += b
        p += len(b)

    table = s["p405_object_table"]
    od = s["open_description_table"]

    def mem_eq(address: int, expected: bytes) -> bytes:
        out = bytearray()
        for i, value in enumerate(expected):
            out += phase4_rename._ld_a_mem(address + i) + bytes((0xFE, value)) + phase1._jp_nz(FAIL_PC)
        return bytes(out)

    def patch(old: str, new: str, records: bytes, open_slot: int | None = None):
        def apply(ram: bytearray) -> None:
            ram[MODULE_BASE-0x4000:MODULE_BASE-0x4000+len(module)] = module
            ram[DATA_BASE-0x4000:DATA_BASE-0x4000+len(data)] = data
            ram[table-0x4000:table-0x4000+640] = bytes(640)
            ram[table-0x4000:table-0x4000+len(records)] = records
            ram[REQ_BASE-0x4000:REQ_BASE-0x4000+4] = phase4_rename._word(addrs[old]) + phase4_rename._word(addrs[new])
            ram[PAYLOAD_A-0x4000:PAYLOAD_A-0x4000+8] = b"SOURCE!!"
            ram[PAYLOAD_B-0x4000:PAYLOAD_B-0x4000+8] = b"DESTOLD!"
            ram[od-0x4000:od-0x4000+192] = bytes(192)
            ram[s["test_free_ptr"]-0x4000:s["test_free_ptr"]-0x4000+5] = bytes(5)
            if open_slot is not None:
                base = od - 0x4000
                ram[base] = s["OD_KIND_OBJECT"]
                ram[base+2] = 1
                ram[base+3] = open_slot
        return apply

    def execute(label: str, code: bytes, patcher) -> None:
        body = b"\xF3" + phase1._ld_sp(0xBFC0) + code + phase1._jp(PASS_PC)
        try:
            run_sna(root, body, patch=patcher)
        except DriverError as exc:
            raise P415Error(f"P4.15 target case failed: {label}: {exc}") from exc

    call = phase1._ld_hl(REQ_BASE) + phase1._call(s["zx48_p415_sys_rename"])
    zero = bytes(20)

    src = phase4_rename._record(b"foo", s["DIR_TMP"], s["OBJ_DAT"], 5, 5, PAYLOAD_A)
    dst = phase4_rename._record(b"bar", s["DIR_TMP"], s["OBJ_DAT"], 5, 5, PAYLOAD_B)
    out = phase4_rename._record(b"bar", s["DIR_TMP"], s["OBJ_DAT"], 5, 5, PAYLOAD_A)
    pair = src + dst
    code = call + phase1._jp_c(FAIL_PC) + mem_eq(table, zero) + mem_eq(table+20, out)
    code += mem_eq(s["test_free_seen"], b"\x01") + mem_eq(s["test_free_ptr"], phase4_rename._word(PAYLOAD_B)) + mem_eq(s["test_free_len"], phase4_rename._word(6))
    execute("replace", code, patch("/tmp/foo", "/tmp/bar", pair))

    src_bin = phase4_rename._record(b"tool", s["DIR_TMP"], s["OBJ_BIN"], 7, 7, PAYLOAD_A)
    dst_bin = phase4_rename._record(b"tool", s["DIR_BIN"], s["OBJ_BIN"], 4, 4, PAYLOAD_B)
    out_bin = phase4_rename._record(b"tool", s["DIR_BIN"], s["OBJ_BIN"], 7, 7, PAYLOAD_A)
    code = call + phase1._jp_c(FAIL_PC) + mem_eq(table, zero) + mem_eq(table+20, out_bin)
    execute("cross-dir-replace", code, patch("/tmp/tool", "/bin/tool", src_bin + dst_bin))

    for label, slot in (("open-source", 0), ("open-destination", 1)):
        code = call + phase4_rename._jp_nc(FAIL_PC) + bytes((0xFE, s["E_BUSY"])) + phase1._jp_nz(FAIL_PC) + mem_eq(table, pair) + mem_eq(s["test_free_seen"], b"\x00")
        execute(label, code, patch("/tmp/foo", "/tmp/bar", pair, slot))

    bad = bytearray(dst)
    bad[13] = 1
    bad_pair = src + bytes(bad)
    code = call + phase4_rename._jp_nc(FAIL_PC) + bytes((0xFE, s["E_INVAL"])) + phase1._jp_nz(FAIL_PC) + mem_eq(table, bad_pair)
    execute("precommit-invalid-rollback", code, patch("/tmp/foo", "/tmp/bar", bad_pair))

    protected = phase4_rename._record(b"bar", s["DIR_TMP"], s["OBJ_SYS"], 5, 5, PAYLOAD_B)
    protected_pair = src + protected
    code = call + phase4_rename._jp_nc(FAIL_PC) + bytes((0xFE, s["E_PERM"])) + phase1._jp_nz(FAIL_PC) + mem_eq(table, protected_pair)
    execute("protected-destination", code, patch("/tmp/foo", "/tmp/bar", protected_pair))

    moved = phase4_rename._record(b"tool", s["DIR_BIN"], s["OBJ_BIN"], 7, 7, PAYLOAD_A)
    code = call + phase1._jp_c(FAIL_PC) + mem_eq(table, moved) + mem_eq(s["test_free_seen"], b"\x00")
    execute("p414-nonreplacement", code, patch("/tmp/tool", "/bin/tool", src_bin))


def dispatch(root: Path, action: str, step: str, *, sha256_file, run_command, require_project_tool):
    if step != "P4.15":
        raise DriverError(f"Phase-4 rename replacement step is not registered: {step}")
    assertions = _source_contract(root)
    failed = [x["name"] for x in assertions if x.get("passed") is not True]
    require(not failed, f"static P4.15 contract failures: {failed}")
    kernel_result, kernel, _ = phase1._assemble_kernel(root, run_command, require_project_tool)
    fixture_result, binary, listing = _assemble(root, run_command, require_project_tool)
    names = ("zx48_p415_sys_rename", "p405_object_table", "open_description_table", "test_free_ptr", "test_free_len", "test_free_seen", "OD_KIND_OBJECT", "OBJ_BIN", "OBJ_DAT", "OBJ_SYS", "DIR_BIN", "DIR_TMP", "E_BUSY", "E_INVAL", "E_PERM")
    symbols = phase3_open_descriptions._symbols(listing.with_suffix(".sym"), names)
    if action == "test":
        _target(root, symbols, binary.read_bytes())
        assertions += [
            {"name": "distinct-replacement-runtime", "passed": True},
            {"name": "cross-directory-replacement-runtime", "passed": True},
            {"name": "open-source-destination-ebusy-runtime", "passed": True},
            {"name": "precommit-failure-rolls-back-runtime", "passed": True},
            {"name": "protected-destination-eperm-runtime", "passed": True},
            {"name": "p414-nonreplacement-preserved-runtime", "passed": True},
        ]
    hashes = {
        "v1/build/kernel.bin": sha256_file(kernel),
        "v1/build/p415-rename-replace.bin": sha256_file(binary),
        "v1/src/kernel/objects.asm": sha256_file(root / "v1/src/kernel/objects.asm"),
        "v1/tools-host/test-driver/phase4_rename_replace.py": sha256_file(root / "v1/tools-host/test-driver/phase4_rename_replace.py"),
        "v1/tools-host/test-driver/run.py": sha256_file(root / "v1/tools-host/test-driver/run.py"),
        "v1/dist/certification/P4.14.test.json": sha256_file(root / "v1/dist/certification/P4.14.test.json"),
    }
    return [kernel_result, fixture_result], hashes, assertions
