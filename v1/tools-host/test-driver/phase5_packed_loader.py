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
import tempfile
from typing import Any, Callable

from driver_core import DriverError
from fuse_harness import FAIL_PC, PASS_PC, make_sna, run_sna
import phase1
import phase3_open_descriptions
import phase5_chunk_framing
from phase5_m48o_header import crc16_ccitt_false

MODULE_BASE = 0xC000
HEADER_BASE = 0x9800
PACKED_BASE = 0xA000
DECODER_BASE = 0xB000
STACK_TOP = 0xBFC0
ROM_LD_BYTES = 0x0556
ROM_IY_ANCHOR = 0x5C3A
P417_STATE_SIZE = 272


class Phase5PackedLoaderError(DriverError):
    """Raised when the P5.05 PACKED loader contract regresses."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Phase5PackedLoaderError(message)


def _source_contract(root: Path) -> list[dict[str, object]]:
    tape = (root / "v1/src/kernel/tape.asm").read_text(encoding="utf-8")
    zxpack = (root / "v1/src/kernel/zxpack.asm").read_text(encoding="utf-8")
    require("MACRO EMIT_P505_PACKED_LOADER_ROUTINES" in tape, "P5.05 packed loader macro missing")
    body = tape.split("MACRO EMIT_P505_PACKED_LOADER_ROUTINES", 1)[1].split("ENDM", 1)[0]
    helper = zxpack.split("MACRO EMIT_P505_PACKED_VALIDATOR_ROUTINES", 1)[1].split("ENDM", 1)[0]
    first_alloc = body.find("call zx48_alloc")
    decoder_alloc = body.find("call zx48_alloc", first_alloc + 1)
    stream = body.find("zx48_p505_chunk_loop:")
    validate = body.find("call zx48_p505_validate_zxp1")
    publish = body.find("ld (p505_published),a", body.find("zx48_p505_validate:"))
    return [
        {"name": "complete-packed-header-validation-precedes-allocation", "passed": 0 < body.find("zx48_p505_header_crc:") < first_alloc},
        {"name": "packed-requires-strict-smaller-physical-length", "passed": "zx48_p505_compare_lengths:" in body and "jp z,zx48_p505_format" in body},
        {"name": "packed-codec-is-zxp1", "passed": "M48O_CODEC_ZXP1" in body},
        {"name": "physical-final-allocation-precedes-exact-decoder-state", "passed": 0 < first_alloc < decoder_alloc < stream},
        {"name": "decoder-state-is-exact-272-bytes", "passed": body.count("P417_STATE_SIZE") >= 3 and re.search(r"^P417_STATE_SIZE\\s+EQU\\s+272$", zxpack, re.MULTILINE) is not None},
        {"name": "physical-bytes-stream-direct-to-final-allocation", "passed": "ld ix,(p505_write_ptr)" in body and "call zx48_tape_load_block" in body and "ldir" not in body},
        {"name": "discard-validation-after-complete-physical-stream", "passed": stream < validate < publish and "P416_SINK_DISCARD" in helper},
        {"name": "logical-crc-validated-before-publication", "passed": "ld hl,(p416_crc)" in body and body.find("ld hl,(p416_crc)") < publish},
        {"name": "no-raw-logical-materialization", "passed": "P416_SINK_FINAL_MEMORY" not in body and "P416_SINK_FINAL_MEMORY" not in helper},
        {"name": "decoder-state-freed-before-packed-publication", "passed": body.find("call zx48_free", validate) < publish},
        {"name": "failure-cleans-private-physical-and-decoder-state", "passed": "zx48_p505_cleanup:" in body and body.count("call zx48_free") >= 3},
    ]


def _rle_pack(logical: bytes) -> bytes:
    require(logical and len(set(logical)) == 1, "P5.05 fixture requires uniform logical data")
    value = logical[0]
    out = bytearray()
    left = len(logical)
    while left:
        count = min(66, left)
        require(count >= 3, "P5.05 RLE fixture tail too short")
        out.extend((0x40 | (count - 3), value))
        left -= count
    return bytes(out)


def _header(name: str, physical: bytes, logical: bytes, *, payload_crc: int | None = None) -> bytes:
    encoded = name.encode("ascii")
    header = bytearray(32)
    header[0:4] = b"M48O"
    header[4] = 1
    header[5] = 1
    header[6] = 1
    header[7] = 3
    header[8:10] = len(physical).to_bytes(2, "little")
    header[10:12] = len(logical).to_bytes(2, "little")
    header[12:14] = (1).to_bytes(2, "little")
    crc = crc16_ccitt_false(logical) if payload_crc is None else payload_crc
    header[14:16] = crc.to_bytes(2, "little")
    header[16:26] = encoded.ljust(10, b"\0")
    header[26:28] = b"\0\0"
    header[28:32] = b"\0\0\0\0"
    header[26:28] = crc16_ccitt_false(bytes(header)).to_bytes(2, "little")
    return bytes(header)


def _image(header: bytes, physical: bytes) -> bytes:
    return phase5_chunk_framing._raw_tap(0xFF, header) + b"".join(
        phase5_chunk_framing._raw_tap(0xFF, physical[offset:offset + 512])
        for offset in range(0, len(physical), 512)
    )


def _assemble_fixture(
    root: Path,
    run_command: Callable[..., Any],
    require_project_tool: Callable[[Path, str | Path], Path],
):
    asm = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    source = build / "p505-packed-loader.asm"
    source.write_text(
        """    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../include/tapeobj.inc"
    INCLUDE "../src/kernel/rom_services.asm"
    INCLUDE "../src/kernel/zxpack.asm"
    INCLUDE "../src/kernel/tape.asm"
    ORG $C000
    EMIT_P416_ZXP1_DECODER
    EMIT_P417_PACKED_READER_STATE_ROUTINES
    EMIT_P505_PACKED_VALIDATOR_ROUTINES
    EMIT_P502_CRC16_ROUTINES
    EMIT_P503_FRAMING_ROUTINES
    EMIT_P505_PACKED_LOADER_ROUTINES

zx48_alloc:
    ld a,(p505_test_alloc_count)
    inc a
    ld (p505_test_alloc_count),a
    cp 2
    jr nz,p505_test_alloc_physical
    ld a,(p505_test_fail_decoder)
    or a
    jr z,p505_test_alloc_decoder
    ld a,E_NOMEM
    scf
    ret
p505_test_alloc_decoder:
    ld hl,$B000
    xor a
    ret
p505_test_alloc_physical:
    ld hl,$A000
    xor a
    ret

zx48_free:
    ld a,(p505_test_free_count)
    inc a
    ld (p505_test_free_count),a
    xor a
    ret

zx48_tape_load_block:
    ld a,(p505_test_transport_fail)
    or a
    jr z,p505_test_rom_load
    ld a,E_IO
    scf
    ret
p505_test_rom_load:
    ld a,M48O_ROM_DATA_FLAG
    scf
    call ROM_LD_BYTES
    jr nc,p505_test_rom_error
    or a
    ret
p505_test_rom_error:
    ld a,E_IO
    scf
    ret

p505_test_fail_decoder: db 0
p505_test_transport_fail: db 0
p505_test_alloc_count: db 0
p505_test_free_count: db 0
    SAVEBIN "p505-packed-loader.bin",$C000,$-$C000
""",
        encoding="utf-8",
        newline="\n",
    )
    result = run_command(
        [asm, "--nologo", "--lst=p505-packed-loader.lst", "--sym=p505-packed-loader.sym", "p505-packed-loader.asm"],
        cwd=build,
        timeout_seconds=30.0,
    )
    require(not result.timed_out and result.exit_code == 0, f"P5.05 fixture assembly failed: {result.stderr or result.stdout}")
    binary = build / "p505-packed-loader.bin"
    symbols = build / "p505-packed-loader.sym"
    require(binary.is_file() and 0 < binary.stat().st_size <= 4096, "P5.05 PACKED loader fixture missing/oversize")
    return result, binary, symbols


def _word(value: int) -> bytes:
    return bytes((value & 0xFF, (value >> 8) & 0xFF))


def _ld_ix(value: int) -> bytes:
    return b"\xDD\x21" + _word(value)


def _check_byte(address: int, value: int) -> bytes:
    return b"\x3A" + _word(address) + bytes((0xFE, value & 0xFF)) + phase1._jp_nz(FAIL_PC)


def _check_word(address: int, value: int) -> bytes:
    return b"\x2A" + _word(address) + phase1._ld_de(value) + b"\xB7\xED\x52" + phase1._jp_nz(FAIL_PC)


def _rom_load_header() -> bytes:
    return _ld_ix(HEADER_BASE) + phase1._ld_de(32) + b"\x3E\xFF\x37" + phase1._call(ROM_LD_BYTES)


def _patch_module(
    module: bytes,
    *,
    header: bytes | None = None,
    fail_decoder: int = 0,
    transport_fail: int = 0,
    symbols: dict[str, int],
):
    def apply(ram: bytearray) -> None:
        start = MODULE_BASE - 0x4000
        ram[start:start + len(module)] = module
        if header is not None:
            off = HEADER_BASE - 0x4000
            ram[off:off + len(header)] = header
        ram[symbols["p505_test_fail_decoder"] - 0x4000] = fail_decoder
        ram[symbols["p505_test_transport_fail"] - 0x4000] = transport_fail
        ram[symbols["p505_test_alloc_count"] - 0x4000] = 0
        ram[symbols["p505_test_free_count"] - 0x4000] = 0
    return apply


def _fuse_case(
    root: Path,
    run_command: Callable[..., Any],
    symbols: dict[str, int],
    module: bytes,
    image: bytes,
    physical: bytes,
    logical_length: int,
    *,
    success: bool,
):
    fuse = root / "tools/runtime/fuse/bin/fuse"
    require(fuse.is_file(), "project-local FUSE executable missing")
    code = bytearray(b"\xF3")
    code += phase1._ld_sp(STACK_TOP)
    code += b"\xFD\x21" + _word(ROM_IY_ANCHOR)
    code += _rom_load_header()
    code += phase1._ld_hl(HEADER_BASE)
    code += phase1._call(symbols["zx48_p505_packed_load"])
    if success:
        code += phase1._jp_c(FAIL_PC)
        code += _check_byte(symbols["p505_published"], 1)
        code += _check_word(symbols["p505_alloc_ptr"], PACKED_BASE)
        code += _check_word(symbols["p505_storage_length"], len(physical))
        code += _check_word(symbols["p505_logical_length"], logical_length)
        code += _check_byte(symbols["p505_test_alloc_count"], 2)
        code += _check_byte(symbols["p505_test_free_count"], 1)
        for index, value in enumerate(physical):
            code += _check_byte(PACKED_BASE + index, value)
    else:
        code += b"\xD2" + _word(FAIL_PC)
        code += _check_byte(symbols["p505_published"], 0)
        code += _check_byte(symbols["p505_test_alloc_count"], 2)
        code += _check_byte(symbols["p505_test_free_count"], 2)
    code += phase1._jp(PASS_PC)

    with tempfile.TemporaryDirectory(prefix="zxux-p505-fuse-") as temporary:
        tmp = Path(temporary)
        sna = tmp / "p505.sna"
        tap = tmp / "p505.tap"
        sna.write_bytes(make_sna(bytes(code), patch=_patch_module(module, symbols=symbols)))
        tap.write_bytes(image)
        debugger = (
            f"breakpoint 0x{PASS_PC:04x}\ncommands 1\nexit 0\nend\n"
            f"breakpoint 0x{FAIL_PC:04x}\ncommands 2\nexit 1\nend\ncontinue"
        )
        result = run_command(
            [
                "/usr/bin/env", "SDL_VIDEODRIVER=dummy", "SDL_AUDIODRIVER=dummy",
                fuse, "--machine", "48", "--no-sound", "--no-confirm-actions",
                "--tape", tap, "--debugger-command", debugger, sna,
            ],
            cwd=root,
            timeout_seconds=20.0,
        )
        require(not result.timed_out and result.exit_code == 0, f"P5.05 FUSE case failed: {result.stderr or result.stdout}")
        return result


def _unit_failure_cases(root: Path, symbols: dict[str, int], module: bytes, header: bytes) -> None:
    # Header defect fails before allocation.
    bad = bytearray(header)
    bad[12:14] = b"\0\0"
    bad[26:28] = b"\0\0"
    bad[26:28] = crc16_ccitt_false(bytes(bad)).to_bytes(2, "little")
    code = bytearray(b"\xF3") + phase1._ld_sp(STACK_TOP)
    code += phase1._ld_hl(HEADER_BASE) + phase1._call(symbols["zx48_p505_packed_load"])
    code += b"\xD2" + _word(FAIL_PC)
    code += _check_byte(symbols["p505_published"], 0)
    code += _check_byte(symbols["p505_test_alloc_count"], 0)
    code += _check_byte(symbols["p505_test_free_count"], 0)
    code += phase1._jp(PASS_PC)
    run_sna(root, bytes(code), patch=_patch_module(module, header=bytes(bad), symbols=symbols))

    # Decoder-state allocation failure frees only the private packed allocation.
    code = bytearray(b"\xF3") + phase1._ld_sp(STACK_TOP)
    code += phase1._ld_hl(HEADER_BASE) + phase1._call(symbols["zx48_p505_packed_load"])
    code += b"\xD2" + _word(FAIL_PC)
    code += _check_byte(symbols["p505_published"], 0)
    code += _check_byte(symbols["p505_test_alloc_count"], 2)
    code += _check_byte(symbols["p505_test_free_count"], 1)
    code += phase1._jp(PASS_PC)
    run_sna(root, bytes(code), patch=_patch_module(module, header=header, fail_decoder=1, symbols=symbols))

    # Transport failure after both allocations releases both private allocations.
    code = bytearray(b"\xF3") + phase1._ld_sp(STACK_TOP)
    code += phase1._ld_hl(HEADER_BASE) + phase1._call(symbols["zx48_p505_packed_load"])
    code += b"\xD2" + _word(FAIL_PC)
    code += _check_byte(symbols["p505_published"], 0)
    code += _check_byte(symbols["p505_test_alloc_count"], 2)
    code += _check_byte(symbols["p505_test_free_count"], 2)
    code += phase1._jp(PASS_PC)
    run_sna(root, bytes(code), patch=_patch_module(module, header=header, transport_fail=1, symbols=symbols))


def dispatch(
    root: Path,
    action: str,
    step: str,
    *,
    sha256_file: Callable[[Path], str],
    run_command: Callable[..., Any],
    require_project_tool: Callable[[Path, str | Path], Path],
):
    if step != "P5.05":
        raise DriverError(f"Phase-5 PACKED loader step is not registered: {step}")

    assertions = _source_contract(root)
    kernel_result, kernel, _ = phase1._assemble_kernel(root, run_command, require_project_tool)
    fixture_result, binary, symbols_path = _assemble_fixture(root, run_command, require_project_tool)
    names = (
        "zx48_p505_packed_load", "p505_published", "p505_alloc_ptr",
        "p505_storage_length", "p505_logical_length", "p505_decoder_ptr",
        "p505_test_fail_decoder", "p505_test_transport_fail",
        "p505_test_alloc_count", "p505_test_free_count",
    )
    symbols = phase3_open_descriptions._symbols(symbols_path, names)
    commands = [kernel_result, fixture_result]

    logical = b"Q" * 528
    physical = _rle_pack(logical)
    require(len(physical) == 16, "P5.05 deterministic packed fixture size drift")
    header = _header("packload", physical, logical)
    image = _image(header, physical)

    if action == "test":
        commands.append(_fuse_case(root, run_command, symbols, binary.read_bytes(), image, physical, len(logical), success=True))
        _unit_failure_cases(root, symbols, binary.read_bytes(), header)

        bad_crc_header = _header("packload", physical, logical, payload_crc=crc16_ccitt_false(logical) ^ 1)
        commands.append(_fuse_case(
            root, run_command, symbols, binary.read_bytes(),
            _image(bad_crc_header, physical), physical, len(logical), success=False,
        ))

        malformed = bytes((0x80, 0x00)) + physical[2:]
        malformed_header = _header("packload", malformed, logical)
        commands.append(_fuse_case(
            root, run_command, symbols, binary.read_bytes(),
            _image(malformed_header, malformed), malformed, len(logical), success=False,
        ))

        trailing = physical + b"\x00"
        trailing_header = _header("packload", trailing, logical)
        commands.append(_fuse_case(
            root, run_command, symbols, binary.read_bytes(),
            _image(trailing_header, trailing), trailing, len(logical), success=False,
        ))

        short_header = _header("packload", physical + b"\x00", logical)
        commands.append(_fuse_case(
            root, run_command, symbols, binary.read_bytes(),
            _image(short_header, physical), physical + b"\x00", len(logical), success=False,
        ))
        assertions.extend(
            [
                {"name": "packed-resident-bytes-remain-exact-zxp1", "passed": True},
                {"name": "one-272-byte-decoder-state-high-water", "passed": True},
                {"name": "decoded-logical-length-and-crc-validated", "passed": True},
                {"name": "decoder-allocation-failure-before-tape-publication", "passed": True},
                {"name": "malformed-zxp1-no-publication", "passed": True},
                {"name": "logical-crc-mismatch-no-publication", "passed": True},
                {"name": "physical-trailing-byte-rejected", "passed": True},
                {"name": "physical-short-stream-rejected", "passed": True},
                {"name": "transport-failure-cleans-private-state", "passed": True},
            ]
        )

    failed = [item["name"] for item in assertions if item.get("passed") is not True]
    require(not failed, f"P5.05 PACKED loader failures: {failed}")

    hashes = {
        "v1/build/kernel.bin": sha256_file(kernel),
        "v1/build/p505-packed-loader.bin": sha256_file(binary),
        "v1/src/kernel/tape.asm": sha256_file(root / "v1/src/kernel/tape.asm"),
        "v1/src/kernel/zxpack.asm": sha256_file(root / "v1/src/kernel/zxpack.asm"),
        "v1/tools-host/test-driver/phase5_packed_loader.py": sha256_file(root / "v1/tools-host/test-driver/phase5_packed_loader.py"),
        "v1/tools-host/test-driver/run.py": sha256_file(root / "v1/tools-host/test-driver/run.py"),
        "v1/dist/certification/P5.04.build.json": sha256_file(root / "v1/dist/certification/P5.04.build.json"),
        "v1/dist/certification/P5.04.test.json": sha256_file(root / "v1/dist/certification/P5.04.test.json"),
    }
    return commands, hashes, assertions
