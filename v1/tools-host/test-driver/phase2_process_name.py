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
from typing import Any, Callable

from driver_core import DriverError
from fuse_harness import FAIL_PC, PASS_PC, run_sna
import phase1

TEST_STACK = 0xFD00
INFO_BUFFER = 0x8900
NAME10_ADDRESS = 0x8A00
NAME11_ADDRESS = 0x8A20
VALIDATOR_ORG = 0xE000

PROC_PARENT = 1
PROC_STATE = 2
PROC_FLAGS = 3
PROC_NAME = 29
PROC_OWNED_BYTES = 40
PROC_DESC_SIZE = 48
PROC_READY = 1

NAME10 = b"AbC9-_.xYz"
NAME11 = b"AbC9-_.xYzQ"


class Phase220Error(DriverError):
    """Raised when the P2.20 exact-case process-name contract is violated."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Phase220Error(message)


def _word(value: int) -> bytes:
    return bytes((value & 0xFF, (value >> 8) & 0xFF))


def _call(address: int) -> bytes:
    return b"\xCD" + _word(address)


def _jp(address: int) -> bytes:
    return b"\xC3" + _word(address)


def _jp_c(address: int) -> bytes:
    return b"\xDA" + _word(address)


def _jp_nc(address: int) -> bytes:
    return b"\xD2" + _word(address)


def _jp_nz(address: int) -> bytes:
    return b"\xC2" + _word(address)


def _ld_sp(address: int) -> bytes:
    return b"\x31" + _word(address)


def _ld_hl(address: int) -> bytes:
    return b"\x21" + _word(address)


def _set_byte(address: int, value: int) -> bytes:
    return bytes((0x3E, value & 0xFF, 0x32)) + _word(address)


def _set_word(address: int, value: int) -> bytes:
    return _ld_hl(value) + b"\x22" + _word(address)


def _expect_byte(address: int, value: int) -> bytes:
    return b"\x3A" + _word(address) + bytes((0xFE, value & 0xFF)) + _jp_nz(FAIL_PC)


def _symbols(path: Path, names: tuple[str, ...]) -> dict[str, int]:
    text = path.read_text(encoding="utf-8", errors="replace")
    found: dict[str, int] = {}
    for name in names:
        pattern = re.compile(
            rf"^{re.escape(name)}:\s+equ\s+0x([0-9A-Fa-f]+)\s*$",
            re.IGNORECASE | re.MULTILINE,
        )
        match = pattern.search(text)
        require(match is not None, f"P2.20 symbol missing from assembler output: {name}")
        found[name] = int(match.group(1), 16)
    return found


def _macro(text: str, name: str) -> str:
    marker = f"    MACRO {name}\n"
    start = text.index(marker)
    end = text.index("    ENDM\n", start)
    return text[start:end]


def _ordered(text: str, tokens: tuple[str, ...]) -> bool:
    position = 0
    for token in tokens:
        found = text.find(token, position)
        if found < 0:
            return False
        position = found + len(token)
    return True


def _source_contract(root: Path) -> list[dict[str, object]]:
    process = (root / "v1/src/kernel/process.asm").read_text(encoding="utf-8")
    objects = (root / "v1/src/kernel/objects.asm").read_text(encoding="utf-8")

    info_start = process.index("zx48_process_info:\n")
    info_end = process.index("zx48_process_exit:\n", info_start)
    info = process[info_start:info_end]

    spawn = _macro(process, "EMIT_SPAWN_TRANSACTION_ROUTINES")
    exec_tx = _macro(process, "EMIT_EXEC_TRANSACTION_ROUTINES")

    validate_start = objects.index("zx48_name_validate:\n")
    validate_end = objects.index("; HL=NUL name, DE=fixed name[10]. Z iff exact.", validate_start)
    validate = objects[validate_start:validate_end]

    create_start = objects.index("zx48_object_create:\n")
    create_end = objects.index("zx48_object_exists:\n", create_start)
    create = objects[create_start:create_end]

    return [
        {
            "name": "process-descriptor-retains-ten-byte-name-field-at-offset29",
            "passed": re.search(r"^PROC_NAME\s+EQU\s+29$", process, re.MULTILINE) is not None,
        },
        {
            "name": "proc-info-copies-all-ten-name-bytes-without-case-folding",
            "passed": _ordered(
                info,
                (
                    "ld de,PROC_NAME",
                    "ld b,10",
                    "zx48_process_info_name:",
                    "ld a,(de)",
                    "ld (hl),a",
                    "djnz zx48_process_info_name",
                ),
            ),
        },
        {
            "name": "spawn-publishes-exact-ten-byte-object-name",
            "passed": _ordered(
                spawn,
                (
                    "ld hl,PROC_NAME",
                    "add hl,de",
                    "ex de,hl",
                    "ld hl,(process_spawn_object)",
                    "ld bc,10",
                    "ldir",
                ),
            ),
        },
        {
            "name": "exec-replaces-process-name-with-exact-ten-byte-object-name",
            "passed": _ordered(
                exec_tx,
                (
                    "ld hl,PROC_NAME",
                    "add hl,de",
                    "ex de,hl",
                    "ld hl,(process_exec_object)",
                    "ld bc,10",
                    "ldir",
                ),
            ),
        },
        {
            "name": "upstream-name-validator-allows-exact-case-and-rejects-byte11",
            "passed": all(
                token in validate
                for token in (
                    "cp 11",
                    "jr nc,zx48_name_long",
                    "ld a,E_TOOLONG",
                    "cp 'A'",
                    "cp 'Z'+1",
                    "cp 'a'",
                    "cp 'z'+1",
                )
            ),
        },
        {
            "name": "object-create-copies-up-to-ten-bytes-with-nul-padding-only-for-shorter-names",
            "passed": _ordered(
                create,
                (
                    "ld b,10",
                    "zx48_object_name_copy:",
                    "ld a,(hl)",
                    "ld (de),a",
                    "or a",
                    "jr z,zx48_object_name_pad",
                    "djnz zx48_object_name_copy",
                    "zx48_object_name_pad:",
                ),
            ),
        },
    ]


def _assemble_validator(
    root: Path,
    run_command: Callable[..., Any],
    require_project_tool: Callable[[Path, str | Path], Path],
):
    assembler = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    objects = (root / "v1/src/kernel/objects.asm").read_text(encoding="utf-8")
    start = objects.index("zx48_name_validate:\n")
    end = objects.index("; HL=NUL name, DE=fixed name[10]. Z iff exact.", start)
    validator = objects[start:end].rstrip() + "\n"

    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    source = build / "p220-name-validator.asm"
    binary = build / "p220-name-validator.bin"
    symbols = build / "p220-name-validator.sym"
    source.write_text(
        "    DEVICE ZXSPECTRUM48\n"
        "    INCLUDE \"../include/zx48ux.inc\"\n"
        f"    ORG ${VALIDATOR_ORG:04X}\n"
        "p220_validator_start:\n"
        + validator
        + "object_name_ptr: dw 0\n"
        "p220_validator_end:\n"
        "    SAVEBIN \"p220-name-validator.bin\",p220_validator_start,p220_validator_end-p220_validator_start\n",
        encoding="utf-8",
        newline="\n",
    )
    result = run_command(
        [assembler, "--nologo", "--sym=p220-name-validator.sym", "p220-name-validator.asm"],
        cwd=build,
        timeout_seconds=30.0,
    )
    require(
        not result.timed_out and result.exit_code == 0,
        f"P2.20 exact production name-validator assembly failed: {result.stderr or result.stdout}",
    )
    require(binary.is_file() and binary.stat().st_size > 0, "P2.20 name-validator fixture missing")
    require(symbols.is_file(), "P2.20 name-validator symbols missing")
    return result, binary, symbols


def _process_info_vector(root: Path, labels: dict[str, int], kernel_bytes: bytes) -> None:
    require(len(NAME10) == 10, "P2.20 positive name vector is not exactly ten bytes")
    process_table = labels["process_table"]
    child = process_table + 2 * PROC_DESC_SIZE

    code = bytearray(b"\xF3" + _ld_sp(TEST_STACK))
    code += _call(labels["zx48_kernel_stack_init"])
    code += _call(labels["zx48_process_init"])
    code += _set_byte(child + PROC_PARENT, 1)
    code += _set_byte(child + PROC_STATE, PROC_READY)
    code += _set_byte(child + PROC_FLAGS, 0)
    code += _set_word(child + PROC_OWNED_BYTES, 0x1234)
    for index, byte in enumerate(NAME10):
        code += _set_byte(child + PROC_NAME + index, byte)

    code += _ld_hl(INFO_BUFFER)
    code += bytes((0x3E, 2)) + _call(labels["zx48_process_info"]) + _jp_c(FAIL_PC)

    code += _expect_byte(INFO_BUFFER + 0, 2)
    code += _expect_byte(INFO_BUFFER + 1, 1)
    code += _expect_byte(INFO_BUFFER + 2, PROC_READY)
    code += _expect_byte(INFO_BUFFER + 3, 0)
    for index, byte in enumerate(NAME10):
        code += _expect_byte(INFO_BUFFER + 4 + index, byte)
        code += _expect_byte(child + PROC_NAME + index, byte)
    code += _expect_byte(INFO_BUFFER + 14, 0x34)
    code += _expect_byte(INFO_BUFFER + 15, 0x12)
    code += _jp(PASS_PC)

    run_sna(root, bytes(code), patch=phase1._kernel_patch(kernel_bytes), timeout=20.0)


def _validator_patch(fixture: bytes):
    def patch(ram: bytearray) -> None:
        fixture_offset = VALIDATOR_ORG - 0x4000
        ram[fixture_offset : fixture_offset + len(fixture)] = fixture
        for address, payload in (
            (NAME10_ADDRESS, NAME10 + b"\0"),
            (NAME11_ADDRESS, NAME11 + b"\0"),
        ):
            offset = address - 0x4000
            ram[offset : offset + len(payload)] = payload

    return patch


def _validator_vector(
    root: Path,
    symbols: dict[str, int],
    fixture: bytes,
) -> None:
    require(len(NAME10) == 10 and len(NAME11) == 11, "P2.20 boundary vectors changed length")
    code = bytearray(b"\xF3" + _ld_sp(0x8F00))

    code += _ld_hl(NAME10_ADDRESS)
    code += _call(symbols["zx48_name_validate"])
    code += _jp_c(FAIL_PC)
    code += bytes((0xFE, 10)) + _jp_nz(FAIL_PC)
    for index, byte in enumerate(NAME10):
        code += _expect_byte(NAME10_ADDRESS + index, byte)

    code += _ld_hl(NAME11_ADDRESS)
    code += _call(symbols["zx48_name_validate"])
    code += _jp_nc(FAIL_PC)
    code += bytes((0xFE, symbols["E_TOOLONG"] & 0xFF)) + _jp_nz(FAIL_PC)
    for index, byte in enumerate(NAME11):
        code += _expect_byte(NAME11_ADDRESS + index, byte)

    code += _jp(PASS_PC)
    run_sna(root, bytes(code), patch=_validator_patch(fixture), timeout=20.0)


def dispatch(
    root: Path,
    action: str,
    step: str,
    *,
    sha256_file: Callable[[Path], str],
    run_command: Callable[..., Any],
    require_project_tool: Callable[[Path, str | Path], Path],
):
    if step != "P2.20":
        raise Phase220Error(f"P2.20 driver received unexpected step: {step}")

    assertions = _source_contract(root)
    failed = [item["name"] for item in assertions if item["passed"] is not True]
    require(not failed, f"static P2.20 contract failures: {failed}")

    kernel_command, kernel, listing = phase1._assemble_kernel(root, run_command, require_project_tool)
    validator_command, validator_binary, validator_symbols = _assemble_validator(
        root,
        run_command,
        require_project_tool,
    )
    commands: list[Any] = [kernel_command, validator_command]

    labels = phase1._labels(
        listing,
        (
            "zx48_kernel_stack_init",
            "zx48_process_init",
            "zx48_process_info",
            "process_table",
        ),
    )
    validator_labels = _symbols(
        validator_symbols,
        (
            "zx48_name_validate",
            "E_TOOLONG",
        ),
    )

    if action == "test":
        _process_info_vector(root, labels, kernel.read_bytes())
        _validator_vector(root, validator_labels, validator_binary.read_bytes())
        assertions.extend(
            [
                {
                    "name": "ten-byte-mixed-case-name-round-trips-byte-exact-through-proc-info",
                    "passed": True,
                    "name_hex": NAME10.hex(),
                },
                {
                    "name": "eleventh-name-byte-is-rejected-upstream-with-e-toolong",
                    "passed": True,
                    "name10_length": len(NAME10),
                    "name11_length": len(NAME11),
                },
            ]
        )

    hashes = {
        "v1/build/kernel.bin": sha256_file(kernel),
        "v1/build/p220-name-validator.bin": sha256_file(validator_binary),
        "v1/src/kernel/process.asm": sha256_file(root / "v1/src/kernel/process.asm"),
        "v1/src/kernel/objects.asm": sha256_file(root / "v1/src/kernel/objects.asm"),
        "v1/tools-host/test-driver/phase2_process_name.py": sha256_file(
            root / "v1/tools-host/test-driver/phase2_process_name.py"
        ),
        "v1/tools-host/test-driver/run.py": sha256_file(root / "v1/tools-host/test-driver/run.py"),
        "v1/tools-host/test-driver/phase2_gate.py": sha256_file(
            root / "v1/tools-host/test-driver/phase2_gate.py"
        ),
    }
    return commands, hashes, assertions
