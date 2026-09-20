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
from phase4_target_encoder import _target_encode
from phase5_m48o_header import crc16_ccitt_false

MODULE_BASE = 0xC000
HEADER_BASE = 0x9800
SOURCE_BASE = 0x8400
FONT_DEST = 0xA000
BINCAT_DEST = 0xB000
STACK_TOP = 0xBFC0


class Phase5BootstrapResourceError(DriverError):
    """Raised when the P5.06 pinned bootstrap-resource contract regresses."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Phase5BootstrapResourceError(message)


def _source_contract(root: Path) -> list[dict[str, object]]:
    tape = (root / "v1/src/kernel/tape.asm").read_text(encoding="utf-8")
    boot = (root / "v1/src/boot/entry.asm").read_text(encoding="utf-8")
    require("MACRO EMIT_P506_PINNED_SYSTEM_ROUTINES" in tape, "P5.06 target macro missing")
    body = tape.split("MACRO EMIT_P506_PINNED_SYSTEM_ROUTINES", 1)[1].split("ENDM", 1)[0]
    hook = boot.split("MACRO EMIT_P506_BOOT_INIT_ROUTINES", 1)[1].split("ENDM", 1)[0]
    return [
        {"name": "font-is-fast-required", "passed": "ALLOC_FAST_REQUIRED" in body and "p506_font_ptr" in body},
        {"name": "bincat-is-cold-pinned-system", "passed": "ALLOC_COLD_PREFERRED" in body and "p506_bincat_ptr" in body},
        {"name": "packed-decodes-into-final-raw-allocation", "passed": "P416_SINK_CALLER_STREAM" in body and "ld iy,(p506_alloc_ptr)" in body and "P417_STATE_SIZE" in body},
        {"name": "raw-and-packed-logical-crc-before-publication", "passed": "p506_expected_crc" in body and body.find("zx48_p506_crc_check:") < body.find("zx48_p506_publish:")},
        {"name": "font-f4x8-structure-frozen", "passed": "ld de,392" in body and "cp 96" in body and "cp $20" in body},
        {"name": "bincat-bcat-40-entry-structure-frozen", "passed": "ld de,488" in body and "cp 40" in body and "ld b,40" in body},
        {"name": "crontab-zero-length-must-be-raw", "passed": "zx48_p506_crontab:" in body and "jp nz,zx48_p506_format" in body},
        {"name": "malformed-bootstrap-routes-to-panic", "passed": "call zx48_p506_boot_resource" in hook and "jp zx48_panic" in hook and "PANIC_ROM_CONTRACT" in hook},
        {"name": "failed-private-allocation-freed-before-publication", "passed": "call zx48_free" in body and "p506_alloc_live" in body},
    ]


def _header(name: str, object_type: int, target: int, logical: bytes, physical: bytes, packed: bool) -> bytes:
    encoded = name.encode("ascii")
    h = bytearray(32)
    h[0:4] = b"M48O"
    h[4] = 1
    h[5] = object_type
    h[6] = 1 if packed else 0
    h[7] = target
    h[8:10] = len(physical).to_bytes(2, "little")
    h[10:12] = len(logical).to_bytes(2, "little")
    h[12:14] = (1 if packed else 0).to_bytes(2, "little")
    h[14:16] = crc16_ccitt_false(logical).to_bytes(2, "little")
    h[16:26] = encoded.ljust(10, b"\0")
    h[26:28] = b"\0\0"
    h[28:32] = b"\0\0\0\0"
    h[26:28] = crc16_ccitt_false(bytes(h)).to_bytes(2, "little")
    return bytes(h)


def _assemble_fixture(root: Path, run_command: Callable[..., Any], require_project_tool: Callable[[Path, str | Path], Path]):
    asm = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    source = build / "p506-bootstrap-resources.asm"
    source.write_text(
        """    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../include/tapeobj.inc"
PANIC_ROM_CONTRACT EQU $05
    INCLUDE "../src/kernel/zxpack.asm"
    INCLUDE "../src/kernel/tape.asm"
    INCLUDE "../src/boot/entry.asm"
    ORG $C000
    EMIT_P416_ZXP1_DECODER
    EMIT_P502_CRC16_ROUTINES
    EMIT_P506_PINNED_SYSTEM_ROUTINES
    EMIT_P506_BOOT_INIT_ROUTINES

zx48_alloc:
    ld (p506_test_policy),a
    ld a,(p506_test_alloc_count)
    inc a
    ld (p506_test_alloc_count),a
    cp 1
    jr z,p506_test_final_alloc
    ld hl,$8800
    xor a
    ret
p506_test_final_alloc:
    ld a,(p506_test_policy)
    ld (p506_test_first_policy),a
    and $7f
    cp ALLOC_FAST_REQUIRED
    jr nz,p506_test_cold_first
    ld hl,$A000
    xor a
    ret
p506_test_cold_first:
    ld hl,$B000
    xor a
    ret

zx48_free:
    ld a,(p506_test_free_count)
    inc a
    ld (p506_test_free_count),a
    xor a
    ret

zx48_memory_pin_bytes:
    ld hl,(p506_test_pinned_bytes)
    add hl,bc
    ld (p506_test_pinned_bytes),hl
    ret

zx48_panic:
    ld (p506_test_panic),a
    ret

p506_test_policy: db 0
p506_test_first_policy: db 0
p506_test_alloc_count: db 0
p506_test_free_count: db 0
p506_test_panic: db 0
p506_test_pinned_bytes: dw 0
    SAVEBIN "p506-bootstrap-resources.bin",$C000,$-$C000
""",
        encoding="utf-8",
        newline="\n",
    )
    result = run_command(
        [asm, "--nologo", "--lst=p506-bootstrap-resources.lst", "--sym=p506-bootstrap-resources.sym", "p506-bootstrap-resources.asm"],
        cwd=build,
        timeout_seconds=30.0,
    )
    require(not result.timed_out and result.exit_code == 0, f"P5.06 fixture assembly failed: {result.stderr or result.stdout}")
    binary = build / "p506-bootstrap-resources.bin"
    symbols = build / "p506-bootstrap-resources.sym"
    require(binary.is_file() and 0 < binary.stat().st_size <= 8192, "P5.06 fixture missing/oversize")
    return result, binary, symbols


def _word(value: int) -> bytes:
    return bytes((value & 0xFF, (value >> 8) & 0xFF))


def _ld_ix(value: int) -> bytes:
    return b"\xDD\x21" + _word(value)


def _check_byte(address: int, value: int) -> bytes:
    return b"\x3A" + _word(address) + bytes((0xFE, value & 0xFF)) + phase1._jp_nz(FAIL_PC)


def _check_word(address: int, value: int) -> bytes:
    return b"\x2A" + _word(address) + phase1._ld_de(value) + b"\xB7\xED\x52" + phase1._jp_nz(FAIL_PC)


def _patch(module: bytes, symbols: dict[str, int], header: bytes, physical: bytes):
    def apply(ram: bytearray) -> None:
        ram[MODULE_BASE-0x4000:MODULE_BASE-0x4000+len(module)] = module
        ram[HEADER_BASE-0x4000:HEADER_BASE-0x4000+len(header)] = header
        ram[SOURCE_BASE-0x4000:SOURCE_BASE-0x4000+len(physical)] = physical
        for name in ("p506_test_first_policy", "p506_test_alloc_count", "p506_test_free_count", "p506_test_panic"):
            ram[symbols[name]-0x4000] = 0
        ram[symbols["p506_test_pinned_bytes"]-0x4000:symbols["p506_test_pinned_bytes"]-0x4000+2] = b"\0\0"
    return apply


def _call_resource(symbols: dict[str, int]) -> bytes:
    return phase1._ld_hl(HEADER_BASE) + _ld_ix(SOURCE_BASE) + phase1._call(symbols["zx48_p506_boot_resource"])


def _runtime(root: Path, symbols: dict[str, int], module: bytes, font: bytes, bincat: bytes) -> None:
    def execute(label: str, header: bytes, physical: bytes, code: bytes) -> None:
        body = b"\xF3" + phase1._ld_sp(STACK_TOP) + code + phase1._jp(PASS_PC)
        try:
            run_sna(root, body, patch=_patch(module, symbols, header, physical))
        except DriverError as exc:
            raise Phase5BootstrapResourceError(f"P5.06 runtime case failed: {label}: {exc}") from exc

    packed_font = _target_encode(font)
    require(0 < len(packed_font) < len(font), "canonical font must have a smaller ZXP1 form")
    font_header = _header("font4x8", 9, 7, font, packed_font, True)
    code = _call_resource(symbols) + phase1._jp_c(FAIL_PC)
    code += _check_word(symbols["p506_font_ptr"], FONT_DEST)
    code += _check_byte(symbols["p506_font_ready"], 1)
    code += _check_byte(symbols["p506_test_first_policy"], symbols["ALLOC_FAST_REQUIRED"])
    code += _check_word(symbols["p506_test_pinned_bytes"], len(font))
    for i, value in enumerate(font[:16] + font[-16:]):
        address = FONT_DEST + (i if i < 16 else len(font) - 32 + i)
        code += _check_byte(address, value)
    execute("packed-font-final-fast-pinned-raw", font_header, packed_font, code)

    packed_bincat = _target_encode(bincat)
    require(0 < len(packed_bincat) < len(bincat), "canonical bincat must have a smaller ZXP1 form")
    bincat_header = _header("bincat", 11, 7, bincat, packed_bincat, True)
    code = _call_resource(symbols) + phase1._jp_c(FAIL_PC)
    code += _check_word(symbols["p506_bincat_ptr"], BINCAT_DEST)
    code += _check_byte(symbols["p506_bincat_ready"], 1)
    code += _check_byte(symbols["p506_test_first_policy"], symbols["ALLOC_COLD_PREFERRED"])
    code += _check_word(symbols["p506_test_pinned_bytes"], len(bincat))
    execute("packed-bincat-final-cold-pinned-raw", bincat_header, packed_bincat, code)

    # The official zero-length crontab is accepted only in RAW form.
    raw_crontab = _header("crontab", 10, 3, b"", b"", False)
    code = _call_resource(symbols) + phase1._jp_c(FAIL_PC)
    code += _check_byte(symbols["p506_test_alloc_count"], 0)
    code += _check_byte(symbols["p506_test_panic"], 0)
    execute("zero-length-raw-crontab", raw_crontab, b"", code)

    packed_crontab = _header("crontab", 10, 3, b"", b"", True)
    code = phase1._ld_hl(HEADER_BASE) + _ld_ix(SOURCE_BASE) + phase1._call(symbols["zx48_p506_boot_resource_or_panic"])
    code += _check_byte(symbols["p506_test_panic"], symbols["PANIC_ROM_CONTRACT"])
    code += _check_byte(symbols["p506_test_alloc_count"], 0)
    execute("packed-zero-length-crontab-panics", packed_crontab, b"", code)


def dispatch(root: Path, action: str, step: str, *, sha256_file, run_command, require_project_tool):
    if step != "P5.06":
        raise DriverError(f"Phase-5 bootstrap-resource step is not registered: {step}")

    assertions = _source_contract(root)
    failed = [item["name"] for item in assertions if item.get("passed") is not True]
    require(not failed, f"P5.06 static failures: {failed}")

    kernel_result, kernel, _ = phase1._assemble_kernel(root, run_command, require_project_tool)
    fixture_result, binary, symbols_path = _assemble_fixture(root, run_command, require_project_tool)
    names = (
        "zx48_p506_boot_resource", "zx48_p506_boot_resource_or_panic",
        "p506_font_ptr", "p506_bincat_ptr", "p506_font_ready", "p506_bincat_ready",
        "p506_test_policy", "p506_test_first_policy", "p506_test_alloc_count", "p506_test_free_count",
        "p506_test_panic", "p506_test_pinned_bytes",
        "ALLOC_FAST_REQUIRED", "ALLOC_COLD_PREFERRED", "PANIC_ROM_CONTRACT",
    )
    symbols = phase3_open_descriptions._symbols(symbols_path, names)
    font = (root / "v1/assets/font4x8-zxux.bin").read_bytes()
    bincat = (root / "v1/assets/bincat.bin").read_bytes()
    require(len(font) == 392, "canonical font length changed")
    require(sha256_file(root / "v1/assets/font4x8-zxux.bin") == "90f6818cf81cf3f13509cff32c091075691195d9638dbe801d12daceec1c9339", "canonical font identity changed")
    require(len(bincat) == 488 and bincat[:6] == b"BCAT\x01\x28", "canonical BCAT shape changed")

    if action == "test":
        _runtime(root, symbols, binary.read_bytes(), font, bincat)
        assertions += [
            {"name": "canonical-packed-font-decodes-directly-to-final-fast-raw", "passed": True},
            {"name": "canonical-packed-bincat-decodes-directly-to-final-cold-raw", "passed": True},
            {"name": "valid-system-resources-pinned-before-publication-runtime", "passed": True},
            {"name": "raw-zero-length-crontab-accepted-runtime", "passed": True},
            {"name": "packed-zero-length-crontab-routes-to-boot-panic-runtime", "passed": True},
        ]

    hashes = {
        "v1/build/kernel.bin": sha256_file(kernel),
        "v1/build/p506-bootstrap-resources.bin": sha256_file(binary),
        "v1/src/kernel/tape.asm": sha256_file(root / "v1/src/kernel/tape.asm"),
        "v1/src/boot/entry.asm": sha256_file(root / "v1/src/boot/entry.asm"),
        "v1/tools-host/test-driver/phase5_bootstrap_resources.py": sha256_file(root / "v1/tools-host/test-driver/phase5_bootstrap_resources.py"),
        "v1/tools-host/test-driver/run.py": sha256_file(root / "v1/tools-host/test-driver/run.py"),
        "v1/assets/font4x8-zxux.bin": sha256_file(root / "v1/assets/font4x8-zxux.bin"),
        "v1/assets/bincat.bin": sha256_file(root / "v1/assets/bincat.bin"),
        "v1/dist/certification/P5.05.build.json": sha256_file(root / "v1/dist/certification/P5.05.build.json"),
        "v1/dist/certification/P5.05.test.json": sha256_file(root / "v1/dist/certification/P5.05.test.json"),
    }
    return [kernel_result, fixture_result], hashes, assertions
