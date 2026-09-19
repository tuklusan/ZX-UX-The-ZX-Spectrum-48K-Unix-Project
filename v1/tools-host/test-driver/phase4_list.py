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
DATA_BASE = 0xA000
REQ_BASE = 0xA300
OUT_BASE = 0xA320
BCAT_BASE = 0xA500


class Phase4ListError(DriverError):
    """Raised when the P4.12 SYS_LIST/BCAT contract regresses."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Phase4ListError(message)


def _word(value: int) -> bytes:
    return bytes((value & 0xFF, (value >> 8) & 0xFF))


def _jp_nc(address: int) -> bytes:
    return b"\xD2" + _word(address)


def _ld_a_mem(address: int) -> bytes:
    return b"\x3A" + _word(address)


def _record(name: bytes, directory: int, type_id: int, logical: int, *, flags: int = 0) -> bytes:
    raw = bytearray(20)
    raw[:len(name)] = name
    raw[10] = directory
    raw[11] = type_id
    raw[12] = flags
    raw[14:16] = _word(logical)
    raw[16:18] = _word(logical)
    return bytes(raw)


def _listout(name: bytes, type_id: int, flags: int, length: int, state: int, directory: int) -> bytes:
    return name.ljust(10, b"\0") + bytes((type_id, flags)) + _word(length) + bytes((state, directory))


def _bcat(entries: list[bytes]) -> bytes:
    raw = bytearray(b"BCAT" + bytes((1, len(entries), 0, 0)))
    for name in entries:
        require(1 <= len(name) <= 10, "BCAT fixture name length")
        raw += name.ljust(10, b"\0") + bytes((2, 1))
    return bytes(raw)


def _source_contract(root: Path) -> list[dict[str, object]]:
    objects = (root / "v1/src/kernel/objects.asm").read_text(encoding="utf-8")
    macro = objects.split("MACRO EMIT_P412_LIST_ROUTINES", 1)[1].split("ENDM", 1)[0]
    return [
        {"name": "list1-exact-six-byte-record", "passed": "HL -> LIST1 {path_ptr,u8 index,u8 reserved,u16 out_ptr}." in macro and "ld bc,6" in macro},
        {"name": "listout1-exact-sixteen-byte-range", "passed": "ld bc,16" in macro and "p412_out_ptr" in macro},
        {"name": "reserved-byte-must-be-zero", "passed": "jp nz,zx48_p412_invalid" in macro},
        {"name": "index-255-unconditional-terminator", "passed": macro.index("inc a\n    jr z,zx48_p412_end") < macro.index("call zx48_path_resolve")},
        {"name": "fixed-root-and-dev-tables-exact", "passed": all(x in macro for x in ("p412_root_entries:", "p412_dev_entries:", "'b','i','n'", "'n','u','l','l'"))},
        {"name": "dynamic-order-uses-minimum-selection", "passed": all(x in macro for x in ("zx48_p412_select_next:", "zx48_p412_accept_candidate:", "p412_prev_name"))},
        {"name": "bcat-count-224-rejected", "passed": "cp 224" in macro and "jp nc,zx48_p412_bcat_format" in macro},
        {"name": "bcat-exact-length-validated", "passed": "ld hl,8" in macro and "ld de,12" in macro and "p412_bincat_length" in macro},
        {"name": "bcat-strict-sort-and-duplicate-rejection", "passed": "Strict previous < current: carry only." in macro and "jp nc,zx48_p412_bcat_format" in macro},
        {"name": "resident-bin-shadows-exact-bcat-name", "passed": "zx48_p412_bcat_shadowed:" in macro and "cp DIR_BIN" in macro},
        {"name": "bcat-only-length-unknown", "passed": "STATE_TAPE_BACKED" in macro and "ld a,$ff" in macro},
        {"name": "ram-list-length-is-logical", "passed": "OBJ_LOGICAL_LENGTH" in macro and "STATE_RAM" in macro},
    ]


def _assemble(root: Path, run_command: Callable[..., Any], require_project_tool: Callable[[Path, str | Path], Path]):
    assembler = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    fixture = build / "p412-list.asm"
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
    EMIT_OBJECT_TYPE_ROUTINES
    EMIT_OBJECT_OPEN_ROUTINES
    EMIT_USER_RANGE_VALIDATION_ROUTINE
    EMIT_P412_LIST_ROUTINES
zx48_free:
    xor a
    ret
zx48_panic:
    scf
    ret
fake_process: defs 48,0
    SAVEBIN "p412-list.bin",$C000,$-$C000
""",
        encoding="utf-8",
        newline="\n",
    )
    result = run_command(
        [assembler, "--nologo", "--lst=p412-list.lst", "--sym=p412-list.sym", "p412-list.asm"],
        cwd=build,
        timeout_seconds=30.0,
    )
    require(not result.timed_out and result.exit_code == 0, f"P4.12 fixture assembly failed: {result.stderr or result.stdout}")
    binary = build / "p412-list.bin"
    listing = build / "p412-list.lst"
    require(binary.is_file() and 0 < binary.stat().st_size < 16384, "P4.12 fixture binary missing/oversize")
    return result, binary, listing


def _target(root: Path, s: dict[str, int], module: bytes) -> None:
    paths = ("/", "/dev", "/home", "/tmp", "/bin")
    addresses: dict[str, int] = {}
    payload = bytearray()
    cursor = DATA_BASE
    for path in paths:
        addresses[path] = cursor
        encoded = path.encode("ascii") + b"\0"
        payload += encoded
        cursor += len(encoded)

    table = s["p405_object_table"]

    def patch(path: str, index: int, *, records: bytes = b"", bcat: bytes = b"", reserved: int = 0, out_ptr: int = OUT_BASE, user: bytes = b""):
        def apply(ram: bytearray) -> None:
            ram[MODULE_BASE - 0x4000:MODULE_BASE - 0x4000 + len(module)] = module
            ram[DATA_BASE - 0x4000:DATA_BASE - 0x4000 + len(payload)] = payload
            ram[REQ_BASE - 0x4000:REQ_BASE - 0x4000 + 6] = _word(addresses[path]) + bytes((index, reserved)) + _word(out_ptr)
            if records:
                ram[table - 0x4000:table - 0x4000 + len(records)] = records
            if bcat:
                ram[BCAT_BASE - 0x4000:BCAT_BASE - 0x4000 + len(bcat)] = bcat
            if user:
                ram[s["session_user_len"] - 0x4000] = len(user)
                ram[s["session_user"] - 0x4000:s["session_user"] - 0x4000 + len(user)] = user
            if 0x4000 <= out_ptr < 0xE000:
                count = min(16, 0xE000 - out_ptr)
                ram[out_ptr - 0x4000:out_ptr - 0x4000 + count] = bytes((0xA5,)) * count
        return apply

    def mem_eq(address: int, expected: bytes) -> bytes:
        code = bytearray()
        for offset, value in enumerate(expected):
            code += _ld_a_mem(address + offset) + bytes((0xFE, value)) + phase1._jp_nz(FAIL_PC)
        return bytes(code)

    def execute(label: str, code: bytes, patcher) -> None:
        body = bytes((0xF3,)) + phase1._ld_sp(0xBFC0) + code + phase1._jp(PASS_PC)
        try:
            run_sna(root, body, patch=patcher)
        except DriverError as exc:
            raise Phase4ListError(f"P4.12 target case failed: {label}: {exc}") from exc

    def admit(catalog: bytes) -> bytes:
        return phase1._ld_hl(BCAT_BASE) + b"\x01" + _word(len(catalog)) + phase1._call(s["zx48_p412_bincat_admit"]) + phase1._jp_c(FAIL_PC)

    def list_call() -> bytes:
        return phase1._ld_hl(REQ_BASE) + phase1._call(s["zx48_p412_sys_list"])

    def success(label: str, path: str, index: int, expected: bytes, *, records: bytes = b"", catalog: bytes = b"", user: bytes = b"") -> None:
        code = (admit(catalog) if catalog else b"") + list_call() + phase1._jp_c(FAIL_PC)
        code += b"\x7C\xB5" + phase1._jp_nz(FAIL_PC)
        code += b"\x2C" + phase1._jp_nz(FAIL_PC)
        code += mem_eq(OUT_BASE, expected)
        execute(label, code, patch(path, index, records=records, bcat=catalog, user=user))

    root_names = (b"bin", b"dev", b"etc", b"home", b"tmp")
    for index, name in enumerate(root_names):
        success(f"root-{name.decode()}", "/", index, _listout(name, s["OBJ_DIR"], 0, 0, s["STATE_PSEUDO"], s["DIR_ROOT"]))
    dev_names = (b"null", b"tape", b"tty")
    for index, name in enumerate(dev_names):
        success(f"dev-{name.decode()}", "/dev", index, _listout(name, s["OBJ_DEV"], 0, 0, s["STATE_PSEUDO"], s["DIR_DEV"]))

    code = list_call() + phase1._jp_c(FAIL_PC)
    code += b"\x7C\xB5" + phase1._jp_nz(FAIL_PC)
    code += mem_eq(OUT_BASE, bytes((0xA5,)) * 16)
    execute("home-prelogin-empty", code, patch("/home", 0))
    success("home-postlogin-user", "/home", 0, _listout(b"alice", s["OBJ_DIR"], 0, 0, s["STATE_PSEUDO"], s["DIR_HOME"]), user=b"alice")

    dynamic = b"".join((
        _record(b"z", s["DIR_TMP"], s["OBJ_DAT"], 3),
        _record(b"a", s["DIR_TMP"], s["OBJ_DAT"], 2),
        _record(b"A", s["DIR_TMP"], s["OBJ_DAT"], 1),
    ))
    for index, (name, length) in enumerate(((b"A", 1), (b"a", 2), (b"z", 3))):
        success(f"tmp-sorted-{index}", "/tmp", index, _listout(name, s["OBJ_DAT"], 0, length, s["STATE_RAM"], s["DIR_TMP"]), records=dynamic)

    catalog = _bcat([b"aa", b"mid", b"zz"])
    union = b"".join((
        _record(b"mid", s["DIR_BIN"], s["OBJ_BIN"], 7),
        _record(b"Mid", s["DIR_BIN"], s["OBJ_BIN"], 4),
        _record(b"bb", s["DIR_BIN"], s["OBJ_BIN"], 5),
    ))
    expected = (
        (b"Mid", s["STATE_RAM"], 4),
        (b"aa", s["STATE_TAPE_BACKED"], 0xFFFF),
        (b"bb", s["STATE_RAM"], 5),
        (b"mid", s["STATE_RAM"], 7),
        (b"zz", s["STATE_TAPE_BACKED"], 0xFFFF),
    )
    for index, (name, state, length) in enumerate(expected):
        success(f"bin-union-{index}", "/bin", index, _listout(name, s["OBJ_BIN"], 0, length, state, s["DIR_BIN"]), records=union, catalog=catalog)

    unshadowed = b"".join((
        _record(b"Mid", s["DIR_BIN"], s["OBJ_BIN"], 4),
        _record(b"bb", s["DIR_BIN"], s["OBJ_BIN"], 5),
    ))
    success("bin-shadow-removal-reveals-bcat", "/bin", 3, _listout(b"mid", s["OBJ_BIN"], 0, 0xFFFF, s["STATE_TAPE_BACKED"], s["DIR_BIN"]), records=unshadowed, catalog=catalog)

    code = list_call() + phase1._jp_c(FAIL_PC)
    code += b"\x7C\xB5" + phase1._jp_nz(FAIL_PC)
    code += mem_eq(OUT_BASE, bytes((0xA5,)) * 16)
    execute("index-255-unconditional-terminator", code, patch("/tmp", 255, records=dynamic))

    entries223 = [f"a{n:03d}".encode("ascii") for n in range(223)]
    bcat223 = _bcat(entries223)
    code = phase1._ld_hl(BCAT_BASE) + b"\x01" + _word(len(bcat223)) + phase1._call(s["zx48_p412_bincat_admit"]) + phase1._jp_c(FAIL_PC)
    execute("bcat-223-accepted", code, patch("/bin", 0, bcat=bcat223))

    header224 = b"BCAT" + bytes((1, 224, 0, 0))
    code = phase1._ld_hl(BCAT_BASE) + b"\x01" + _word(len(header224)) + phase1._call(s["zx48_p412_bincat_admit"]) + _jp_nc(FAIL_PC)
    code += bytes((0xFE, s["E_FORMAT"])) + phase1._jp_nz(FAIL_PC)
    execute("bcat-224-rejected", code, patch("/bin", 0, bcat=header224))

    for label, bad in (
        ("bcat-duplicate-rejected", _bcat([b"aa", b"aa"])),
        ("bcat-unsorted-rejected", _bcat([b"bb", b"aa"])),
    ):
        code = phase1._ld_hl(BCAT_BASE) + b"\x01" + _word(len(bad)) + phase1._call(s["zx48_p412_bincat_admit"]) + _jp_nc(FAIL_PC)
        code += bytes((0xFE, s["E_FORMAT"])) + phase1._jp_nz(FAIL_PC)
        execute(label, code, patch("/bin", 0, bcat=bad))

    code = list_call() + _jp_nc(FAIL_PC) + bytes((0xFE, s["E_INVAL"])) + phase1._jp_nz(FAIL_PC)
    code += mem_eq(OUT_BASE, bytes((0xA5,)) * 16)
    execute("list-reserved-rejected-before-output", code, patch("/tmp", 0, records=dynamic, reserved=1))

    code = list_call() + _jp_nc(FAIL_PC) + bytes((0xFE, s["E_INVAL"])) + phase1._jp_nz(FAIL_PC)
    execute("list-output-crosses-protected-range", code, patch("/tmp", 0, records=dynamic, out_ptr=0x5AF8))


def dispatch(
    root: Path,
    action: str,
    step: str,
    *,
    sha256_file: Callable[[Path], str],
    run_command: Callable[..., Any],
    require_project_tool: Callable[[Path, str | Path], Path],
):
    if step != "P4.12":
        raise DriverError(f"Phase-4 list step is not registered: {step}")

    assertions = _source_contract(root)
    failed = [item["name"] for item in assertions if item.get("passed") is not True]
    require(not failed, f"static P4.12 contract failures: {failed}")

    kernel_result, kernel, _ = phase1._assemble_kernel(root, run_command, require_project_tool)
    fixture_result, binary, listing = _assemble(root, run_command, require_project_tool)
    commands = [kernel_result, fixture_result]
    names = (
        "zx48_p412_sys_list", "zx48_p412_bincat_admit", "p405_object_table",
        "session_user_len", "session_user", "OBJ_BIN", "OBJ_DAT", "OBJ_DIR", "OBJ_DEV",
        "DIR_ROOT", "DIR_BIN", "DIR_DEV", "DIR_HOME", "DIR_TMP",
        "STATE_RAM", "STATE_TAPE_BACKED", "STATE_PSEUDO", "E_INVAL", "E_FORMAT",
    )
    symbols = phase3_open_descriptions._symbols(listing.with_suffix(".sym"), names)

    if action == "test":
        _target(root, symbols, binary.read_bytes())
        assertions.extend([
            {"name": "fixed-root-dev-home-listings-exact-runtime", "passed": True},
            {"name": "dynamic-listing-unsigned-bytewise-case-sensitive-runtime", "passed": True},
            {"name": "bin-resident-bcat-union-shadowing-runtime", "passed": True},
            {"name": "shadow-removal-reveals-bcat-runtime", "passed": True},
            {"name": "index255-terminates-without-output-runtime", "passed": True},
            {"name": "bcat-223-accept-224-reject-runtime", "passed": True},
            {"name": "bcat-duplicate-unsorted-rejected-runtime", "passed": True},
            {"name": "list1-reserved-and-output-range-negative-runtime", "passed": True},
        ])

    hashes = {
        "v1/build/kernel.bin": sha256_file(kernel),
        "v1/build/p412-list.bin": sha256_file(binary),
        "v1/src/kernel/objects.asm": sha256_file(root / "v1/src/kernel/objects.asm"),
        "v1/tools-host/test-driver/phase4_list.py": sha256_file(root / "v1/tools-host/test-driver/phase4_list.py"),
        "v1/tools-host/test-driver/run.py": sha256_file(root / "v1/tools-host/test-driver/run.py"),
        "v1/dist/certification/P4.11.test.json": sha256_file(root / "v1/dist/certification/P4.11.test.json"),
        "v1/dist/certification/P4.11.requalification.test.json": sha256_file(root / "v1/dist/certification/P4.11.requalification.test.json"),
    }
    return commands, hashes, assertions
