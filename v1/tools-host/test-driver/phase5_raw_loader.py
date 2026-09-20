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

import importlib.util
from pathlib import Path
import sys
import tempfile
from typing import Any, Callable

from driver_core import DriverError
from fuse_harness import FAIL_PC, PASS_PC, make_sna, run_sna
import phase1
import phase3_open_descriptions
import phase5_chunk_framing

MODULE_BASE = 0xC000
HEADER_BASE = 0x9800
PAYLOAD_BASE = 0xA000
STACK_TOP = 0xBFC0
ROM_LD_BYTES = 0x0556
ROM_IY_ANCHOR = 0x5C3A
MAKETAP = "v1/tools-host/maketap/maketap.py"


class Phase5RawLoaderError(DriverError):
    """Raised when the P5.04 RAW loader contract regresses."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Phase5RawLoaderError(message)


def _load_host(root: Path):
    path = root / MAKETAP
    spec = importlib.util.spec_from_file_location("zxux_p504_maketap", path)
    require(spec is not None and spec.loader is not None, "P5.04 cannot load maketap")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _source_contract(root: Path) -> list[dict[str, object]]:
    text = (root / "v1/src/kernel/tape.asm").read_text(encoding="utf-8")
    require("MACRO EMIT_P504_RAW_LOADER_ROUTINES" in text, "P5.04 RAW loader macro missing")
    body = text.split("MACRO EMIT_P504_RAW_LOADER_ROUTINES", 1)[1].split("ENDM", 1)[0]
    validation = body.find("zx48_p504_header_crc:")
    allocation = body.find("call zx48_alloc")
    publish = body.find("ld (p504_published),a", body.find("zx48_p504_complete:"))
    return [
        {"name": "complete-header-validation-precedes-allocation", "passed": 0 < validation < allocation},
        {"name": "raw-length-equality-and-32768-bound", "passed": "sbc hl,de" in body and "cp $80" in body},
        {"name": "raw-codec-and-flags-required", "passed": "M48O_HDR_CODEC" in body and "or (hl)" in body},
        {"name": "public-placement-and-name-validated-before-allocation", "passed": body.find("zx48_p504_name_loop:") < allocation and body.find("zx48_p504_place_bin:") < allocation},
        {"name": "final-allocation-only-no-payload-staging-copy", "passed": "ldir" not in body and body.count("call zx48_alloc") == 1},
        {"name": "stream-direct-to-allocation-in-512-blocks", "passed": "ld ix,(p504_write_ptr)" in body and "call zx48_p503_prepare_chunk" in body and "call zx48_tape_load_block" in body},
        {"name": "incremental-logical-crc-over-final-bytes", "passed": "call zx48_p504_crc_update" in body and "ld de,(p504_crc)" in body},
        {"name": "publication-after-length-and-crc-only", "passed": publish > body.find("zx48_p504_complete:") and publish > body.find("sbc hl,de", body.find("zx48_p504_complete:"))},
        {"name": "failure-frees-private-allocation-and-clears-publication", "passed": "call zx48_free" in body and "zx48_p504_cleanup:" in body},
    ]


def _assemble_fixture(
    root: Path,
    run_command: Callable[..., Any],
    require_project_tool: Callable[[Path, str | Path], Path],
):
    asm = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    source = build / "p504-raw-loader.asm"
    source.write_text(
        """    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../include/tapeobj.inc"
    INCLUDE "../src/kernel/rom_services.asm"
    INCLUDE "../src/kernel/tape.asm"
    ORG $C000
    EMIT_P502_CRC16_ROUTINES
    EMIT_P503_FRAMING_ROUTINES
    EMIT_P504_RAW_LOADER_ROUTINES

zx48_alloc:
    ld a,(p504_test_alloc_fail)
    or a
    jr z,p504_test_alloc_ok
    ld a,E_NOMEM
    scf
    ret
p504_test_alloc_ok:
    ld hl,$A000
    xor a
    or a
    ret

zx48_free:
    ld a,(p504_test_free_count)
    inc a
    ld (p504_test_free_count),a
    xor a
    or a
    ret

zx48_tape_load_block:
    ld a,(p504_test_transport_fail)
    or a
    jr z,p504_test_rom_load
    ld a,E_IO
    scf
    ret
p504_test_rom_load:
    ld a,M48O_ROM_DATA_FLAG
    scf
    call ROM_LD_BYTES
    jr nc,p504_test_rom_error
    or a
    ret
p504_test_rom_error:
    ld a,E_IO
    scf
    ret

p504_test_alloc_fail: db 0
p504_test_transport_fail: db 0
p504_test_free_count: db 0
    SAVEBIN "p504-raw-loader.bin",$C000,$-$C000
""",
        encoding="utf-8",
        newline="\n",
    )
    result = run_command(
        [asm, "--nologo", "--lst=p504-raw-loader.lst", "--sym=p504-raw-loader.sym", "p504-raw-loader.asm"],
        cwd=build,
        timeout_seconds=30.0,
    )
    require(not result.timed_out and result.exit_code == 0, f"P5.04 fixture assembly failed: {result.stderr or result.stdout}")
    binary = build / "p504-raw-loader.bin"
    symbols = build / "p504-raw-loader.sym"
    require(binary.is_file() and 0 < binary.stat().st_size <= 2048, "P5.04 RAW loader fixture missing/oversize")
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
    return (
        _ld_ix(HEADER_BASE)
        + phase1._ld_de(32)
        + b"\x3E\xFF\x37"
        + phase1._call(ROM_LD_BYTES)
    )


def _patch_module(module: bytes, *, header: bytes | None = None, alloc_fail: int = 0, transport_fail: int = 0, symbols=None):
    def apply(ram: bytearray) -> None:
        start = MODULE_BASE - 0x4000
        ram[start:start + len(module)] = module
        if header is not None:
            off = HEADER_BASE - 0x4000
            ram[off:off + len(header)] = header
        if symbols is not None:
            ram[symbols["p504_test_alloc_fail"] - 0x4000] = alloc_fail
            ram[symbols["p504_test_transport_fail"] - 0x4000] = transport_fail
            ram[symbols["p504_test_free_count"] - 0x4000] = 0
    return apply


def _fuse_case(
    root: Path,
    run_command: Callable[..., Any],
    symbols: dict[str, int],
    module: bytes,
    image: bytes,
    payload: bytes,
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
    code += phase1._call(symbols["zx48_p504_raw_load"])
    if success:
        code += phase1._jp_c(FAIL_PC)
        code += _check_byte(symbols["p504_published"], 1)
        code += _check_word(symbols["p504_alloc_ptr"], PAYLOAD_BASE)
        code += _check_word(symbols["p504_length"], len(payload))
        code += _check_byte(symbols["p504_test_free_count"], 0)
        for index, value in enumerate(payload[:16]):
            code += _check_byte(PAYLOAD_BASE + index, value)
        for index, value in enumerate(payload[-16:]):
            code += _check_byte(PAYLOAD_BASE + len(payload) - 16 + index, value)
    else:
        code += b"\xD2" + _word(FAIL_PC)
        code += _check_byte(symbols["p504_published"], 0)
        code += _check_byte(symbols["p504_test_free_count"], 1)
    code += phase1._jp(PASS_PC)

    with tempfile.TemporaryDirectory(prefix="zxux-p504-fuse-") as temporary:
        tmp = Path(temporary)
        sna = tmp / "p504.sna"
        tap = tmp / "p504.tap"
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
        require(not result.timed_out and result.exit_code == 0, f"P5.04 FUSE case failed: {result.stderr or result.stdout}")
        return result


def _unit_failure_cases(root: Path, symbols: dict[str, int], module: bytes, header: bytes) -> None:
    # Header defect must fail before allocation/publication.
    bad = bytearray(header)
    bad[6] = 1
    bad[26:28] = b"\0\0"
    from phase5_m48o_header import crc16_ccitt_false
    bad[26:28] = crc16_ccitt_false(bytes(bad)).to_bytes(2, "little")

    code = bytearray(b"\xF3") + phase1._ld_sp(STACK_TOP)
    code += phase1._ld_hl(HEADER_BASE) + phase1._call(symbols["zx48_p504_raw_load"])
    code += b"\xD2" + _word(FAIL_PC)
    code += _check_byte(symbols["p504_published"], 0)
    code += _check_byte(symbols["p504_test_free_count"], 0)
    code += phase1._jp(PASS_PC)
    run_sna(root, bytes(code), patch=_patch_module(module, header=bytes(bad), symbols=symbols))

    # Allocation failure: validated header, no private allocation to free.
    code = bytearray(b"\xF3") + phase1._ld_sp(STACK_TOP)
    code += phase1._ld_hl(HEADER_BASE) + phase1._call(symbols["zx48_p504_raw_load"])
    code += b"\xD2" + _word(FAIL_PC)
    code += _check_byte(symbols["p504_published"], 0)
    code += _check_byte(symbols["p504_test_free_count"], 0)
    code += phase1._jp(PASS_PC)
    run_sna(root, bytes(code), patch=_patch_module(module, header=header, alloc_fail=1, symbols=symbols))

    # Transport failure after allocation must free private state and never publish.
    code = bytearray(b"\xF3") + phase1._ld_sp(STACK_TOP)
    code += phase1._ld_hl(HEADER_BASE) + phase1._call(symbols["zx48_p504_raw_load"])
    code += b"\xD2" + _word(FAIL_PC)
    code += _check_byte(symbols["p504_published"], 0)
    code += _check_byte(symbols["p504_test_free_count"], 1)
    code += phase1._jp(PASS_PC)
    run_sna(root, bytes(code), patch=_patch_module(module, header=header, transport_fail=1, symbols=symbols))


def _malformed_transport_assertions(host, header: bytes, payload: bytes) -> list[dict[str, object]]:
    raw = phase5_chunk_framing._raw_tap
    cases = (
        ("truncation-rejected-before-publication", raw(0xFF, header) + raw(0xFF, payload[:512])),
        ("extra-chunk-bytes-rejected-before-publication", raw(0xFF, header) + raw(0xFF, payload)),
        ("rom-checksum-failure-rejected-before-publication", raw(0xFF, header) + raw(0xFF, payload[:512], corrupt_checksum=True) + raw(0xFF, payload[512:])),
    )
    assertions = []
    for name, image in cases:
        rejected = False
        try:
            end, _, _, _ = phase5_chunk_framing._parse_one(image)
            require(end == len(image), "unexpected trailing transport bytes")
        except DriverError:
            rejected = True
        assertions.append({"name": name, "passed": rejected})
    return assertions


def dispatch(
    root: Path,
    action: str,
    step: str,
    *,
    sha256_file: Callable[[Path], str],
    run_command: Callable[..., Any],
    require_project_tool: Callable[[Path, str | Path], Path],
):
    if step != "P5.04":
        raise DriverError(f"Phase-5 RAW loader step is not registered: {step}")

    assertions = _source_contract(root)
    host = _load_host(root)
    kernel_result, kernel, _ = phase1._assemble_kernel(root, run_command, require_project_tool)
    fixture_result, binary, symbols_path = _assemble_fixture(root, run_command, require_project_tool)
    names = (
        "zx48_p504_raw_load", "p504_published", "p504_alloc_ptr", "p504_length",
        "p504_test_alloc_fail", "p504_test_transport_fail", "p504_test_free_count",
    )
    symbols = phase3_open_descriptions._symbols(symbols_path, names)
    commands = [kernel_result, fixture_result]

    payload = bytes(((index * 29 + 3) & 0xFF) for index in range(513))
    obj = host.M48OObject("rawload", host.M48O_TXT, host.DIR_ETC, payload)
    header = host.m48o_header(obj)
    image = host.m48o_blocks(obj)

    if action == "test":
        commands.append(_fuse_case(root, run_command, symbols, binary.read_bytes(), image, payload, success=True))
        _unit_failure_cases(root, symbols, binary.read_bytes(), header)

        bad_crc = bytearray(header)
        wrong = (host.crc16_ccitt_false(payload) ^ 1) & 0xFFFF
        bad_crc[14:16] = wrong.to_bytes(2, "little")
        bad_crc[26:28] = b"\0\0"
        bad_crc[26:28] = host.crc16_ccitt_false(bytes(bad_crc)).to_bytes(2, "little")
        bad_image = (
            phase5_chunk_framing._raw_tap(0xFF, bytes(bad_crc))
            + phase5_chunk_framing._raw_tap(0xFF, payload[:512])
            + phase5_chunk_framing._raw_tap(0xFF, payload[512:])
        )
        commands.append(_fuse_case(root, run_command, symbols, binary.read_bytes(), bad_image, payload, success=False))
        assertions.extend(_malformed_transport_assertions(host, header, payload))
        assertions.extend(
            [
                {"name": "raw-load-final-allocation-bytes-and-equal-lengths-runtime", "passed": True},
                {"name": "logical-crc-mismatch-frees-private-state-no-publication", "passed": True},
                {"name": "allocation-failure-no-publication", "passed": True},
                {"name": "header-rejected-before-allocation", "passed": True},
                {"name": "transport-failure-frees-private-state-no-publication", "passed": True},
            ]
        )

    failed = [item["name"] for item in assertions if item.get("passed") is not True]
    require(not failed, f"P5.04 RAW loader failures: {failed}")

    hashes = {
        "v1/build/kernel.bin": sha256_file(kernel),
        "v1/build/p504-raw-loader.bin": sha256_file(binary),
        "v1/src/kernel/tape.asm": sha256_file(root / "v1/src/kernel/tape.asm"),
        "v1/tools-host/test-driver/phase5_raw_loader.py": sha256_file(root / "v1/tools-host/test-driver/phase5_raw_loader.py"),
        "v1/tools-host/test-driver/run.py": sha256_file(root / "v1/tools-host/test-driver/run.py"),
        "v1/dist/certification/P5.03.build.json": sha256_file(root / "v1/dist/certification/P5.03.build.json"),
        "v1/dist/certification/P5.03.test.json": sha256_file(root / "v1/dist/certification/P5.03.test.json"),
    }
    return commands, hashes, assertions
