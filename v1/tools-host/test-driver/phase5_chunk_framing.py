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
import struct
import sys
import tempfile
from typing import Any, Callable

from driver_core import DriverError
from fuse_harness import FAIL_PC, PASS_PC, make_sna
import phase1
import phase3_open_descriptions

MODULE_BASE = 0xC000
HEADER_BASE = 0xA000
CHUNK_BASE = 0xA100
TAIL_BASE = 0xA300
STACK_TOP = 0xBFC0
ROM_LD_BYTES = 0x0556
ROM_IY_ANCHOR = 0x5C3A
MAKETAP = "v1/tools-host/maketap/maketap.py"


class Phase5FramingError(DriverError):
    """Raised when the P5.03 M48O ROM-block framing contract regresses."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Phase5FramingError(message)


def _load_host(root: Path):
    path = root / MAKETAP
    spec = importlib.util.spec_from_file_location("zxux_p503_maketap", path)
    require(spec is not None and spec.loader is not None, "P5.03 cannot load maketap")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _tap_blocks(image: bytes) -> list[tuple[int, bytes]]:
    offset = 0
    blocks: list[tuple[int, bytes]] = []
    while offset < len(image):
        require(offset + 2 <= len(image), "truncated TAP length")
        length = struct.unpack_from("<H", image, offset)[0]
        require(length >= 2, "short TAP framed block")
        end = offset + 2 + length
        require(end <= len(image), "truncated TAP block")
        payload = image[offset + 2:end]
        checksum = 0
        for value in payload:
            checksum ^= value
        require(checksum == 0, "bad ROM checksum")
        blocks.append((payload[0], payload[1:-1]))
        offset = end
    return blocks


def _parse_one(image: bytes, offset: int = 0) -> tuple[int, bytes, bytes, list[int]]:
    blocks: list[tuple[int, bytes, int]] = []
    cursor = offset
    while cursor < len(image):
        require(cursor + 2 <= len(image), "truncated TAP length")
        length = struct.unpack_from("<H", image, cursor)[0]
        require(length >= 2, "short TAP framed block")
        end = cursor + 2 + length
        require(end <= len(image), "truncated TAP block")
        payload = image[cursor + 2:end]
        checksum = 0
        for value in payload:
            checksum ^= value
        require(checksum == 0, "bad ROM checksum")
        blocks.append((payload[0], payload[1:-1], end))
        cursor = end
        if len(blocks) == 1:
            break
    require(blocks, "missing M48O header block")
    flag, header, cursor = blocks[0]
    require(flag == 0xFF, "M48O header flag")
    require(len(header) == 32 and header[:4] == b"M48O", "separate 32-byte M48O header block")
    physical = header[8] | (header[9] << 8)
    remaining = physical
    payload_out = bytearray()
    sizes: list[int] = []
    while remaining:
        require(cursor + 2 <= len(image), "missing M48O payload block")
        length = struct.unpack_from("<H", image, cursor)[0]
        require(length >= 2, "short M48O TAP block")
        end = cursor + 2 + length
        require(end <= len(image), "truncated M48O payload block")
        framed = image[cursor + 2:end]
        checksum = 0
        for value in framed:
            checksum ^= value
        require(checksum == 0, "bad ROM checksum")
        require(framed[0] == 0xFF, "M48O payload flag")
        body = framed[1:-1]
        expected = min(remaining, 512)
        require(len(body) == expected, "M48O payload chunk size")
        payload_out.extend(body)
        sizes.append(len(body))
        remaining -= len(body)
        cursor = end
    return cursor, header, bytes(payload_out), sizes


def _raw_tap(flag: int, body: bytes, *, corrupt_checksum: bool = False) -> bytes:
    framed = bytes((flag,)) + body
    checksum = 0
    for value in framed:
        checksum ^= value
    if corrupt_checksum:
        checksum ^= 1
    payload = framed + bytes((checksum,))
    return struct.pack("<H", len(payload)) + payload


def _source_contract(root: Path) -> list[dict[str, object]]:
    tape = (root / "v1/src/kernel/tape.asm").read_text(encoding="utf-8")
    host = (root / MAKETAP).read_text(encoding="utf-8")
    require("MACRO EMIT_P503_FRAMING_ROUTINES" in tape, "P5.03 target framing macro missing")
    body = tape.split("MACRO EMIT_P503_FRAMING_ROUTINES", 1)[1].split("ENDM", 1)[0]
    m48o = host.split("def m48o_blocks", 1)[1].split("def bootstrap_resources", 1)[0]
    return [
        {"name": "target-header-is-separate-32-byte-data-block", "passed": "M48O_ROM_DATA_FLAG" in body and "M48O_HEADER_SIZE" in body},
        {"name": "target-chunk-bound-is-canonical-512", "passed": "M48O_CHUNK_SIZE" in body and "zx48_p503_next_chunk:" in body},
        {"name": "host-framing-constants-exact", "passed": all(x in host for x in ("M48O_HEADER_SIZE = 32", "M48O_CHUNK_SIZE = 512", "M48O_DATA_FLAG = 0xFF"))},
        {"name": "host-header-and-payload-are-separate-blocks", "passed": "tap_block(M48O_DATA_FLAG, m48o_header(obj))" in m48o},
        {"name": "host-payload-chunking-uses-512-bound", "passed": "range(0, len(obj.payload), M48O_CHUNK_SIZE)" in m48o},
    ]


def _assemble_fixture(
    root: Path,
    run_command: Callable[..., Any],
    require_project_tool: Callable[[Path, str | Path], Path],
):
    asm = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    source = build / "p503-framing.asm"
    source.write_text(
        """    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../include/tapeobj.inc"
    INCLUDE "../src/kernel/tape.asm"
    ORG $C000
    EMIT_P503_FRAMING_ROUTINES
    SAVEBIN "p503-framing.bin",$C000,$-$C000
""",
        encoding="utf-8",
        newline="\n",
    )
    result = run_command(
        [asm, "--nologo", "--lst=p503-framing.lst", "--sym=p503-framing.sym", "p503-framing.asm"],
        cwd=build,
        timeout_seconds=30.0,
    )
    require(not result.timed_out and result.exit_code == 0, f"P5.03 fixture assembly failed: {result.stderr or result.stdout}")
    binary = build / "p503-framing.bin"
    symbols = build / "p503-framing.sym"
    require(binary.is_file() and 0 < binary.stat().st_size <= 128, "P5.03 framing fixture missing/oversize")
    return result, binary, symbols


def _word(value: int) -> bytes:
    return bytes((value & 0xFF, (value >> 8) & 0xFF))


def _ld_bc(value: int) -> bytes:
    return b"\x01" + _word(value)


def _ld_ix(value: int) -> bytes:
    return b"\xDD\x21" + _word(value)


def _check_a(value: int) -> bytes:
    return bytes((0xFE, value & 0xFF)) + phase1._jp_nz(FAIL_PC)


def _check_de(value: int) -> bytes:
    return b"\xD5\xE1" + phase1._ld_de(value) + b"\xB7\xED\x52" + phase1._jp_nz(FAIL_PC)


def _check_byte(address: int, value: int) -> bytes:
    return b"\x3A" + _word(address) + bytes((0xFE, value & 0xFF)) + phase1._jp_nz(FAIL_PC)


def _target_chunk_runtime(root: Path, symbols: dict[str, int], module: bytes) -> None:
    code = bytearray(b"\xF3")
    code += phase1._ld_sp(STACK_TOP)
    code += phase1._call(symbols["zx48_p503_prepare_header_block"])
    code += _check_a(0xFF) + _check_de(32)
    for remaining, expected in ((0, 0), (1, 1), (511, 511), (512, 512), (513, 512), (1024, 512), (1025, 512)):
        code += _ld_bc(remaining)
        code += phase1._call(symbols["zx48_p503_prepare_chunk"])
        code += _check_a(0xFF) + _check_de(expected)
    code += phase1._jp(PASS_PC)

    def patch(ram: bytearray) -> None:
        start = MODULE_BASE - 0x4000
        ram[start:start + len(module)] = module

    from fuse_harness import run_sna
    run_sna(root, bytes(code), patch=patch)


def _rom_load(destination: int, length: int) -> bytes:
    return (
        _ld_ix(destination)
        + phase1._ld_de(length)
        + b"\x3E\xFF\x37"
        + phase1._call(ROM_LD_BYTES)
    )


def _fuse_tap_runtime(
    root: Path,
    run_command: Callable[..., Any],
    image: bytes,
    header: bytes,
    payload: bytes,
):
    fuse = root / "tools/runtime/fuse/bin/fuse"
    require(fuse.is_file(), "project-local FUSE executable missing")
    code = bytearray(b"\xF3")
    code += phase1._ld_sp(STACK_TOP)
    code += b"\xFD\x21" + _word(ROM_IY_ANCHOR)
    code += _rom_load(HEADER_BASE, 32)
    code += _rom_load(CHUNK_BASE, 512)
    code += _rom_load(TAIL_BASE, 1)
    for index, value in enumerate(header[:16]):
        code += _check_byte(HEADER_BASE + index, value)
    for index, value in enumerate(payload[:16]):
        code += _check_byte(CHUNK_BASE + index, value)
    for index, value in enumerate(payload[496:512]):
        code += _check_byte(CHUNK_BASE + 496 + index, value)
    code += _check_byte(TAIL_BASE, payload[512])
    code += phase1._jp(PASS_PC)

    with tempfile.TemporaryDirectory(prefix="zxux-p503-fuse-") as temporary:
        root_tmp = Path(temporary)
        sna = root_tmp / "p503.sna"
        tap = root_tmp / "p503.tap"
        sna.write_bytes(make_sna(bytes(code)))
        tap.write_bytes(image)
        debugger = (
            f"breakpoint 0x{PASS_PC:04x}\n"
            "commands 1\nexit 0\nend\n"
            f"breakpoint 0x{FAIL_PC:04x}\n"
            "commands 2\nexit 1\nend\n"
            "continue"
        )
        result = run_command(
            [
                "/usr/bin/env",
                "SDL_VIDEODRIVER=dummy",
                "SDL_AUDIODRIVER=dummy",
                fuse,
                "--machine", "48",
                "--no-sound",
                "--no-confirm-actions",
                "--tape", tap,
                "--debugger-command", debugger,
                sna,
            ],
            cwd=root,
            timeout_seconds=20.0,
        )
        require(
            not result.timed_out and result.exit_code == 0,
            f"P5.03 FUSE TAP framing failed: exit={result.exit_code} timed_out={result.timed_out} stdout={result.stdout!r} stderr={result.stderr!r}",
        )
        return result


def _boundary_assertions(host) -> list[dict[str, object]]:
    assertions: list[dict[str, object]] = []
    for length in (0, 1, 511, 512, 513, 1024, 1025):
        payload = bytes(((index * 37 + 11) & 0xFF) for index in range(length))
        obj = host.M48OObject("frame", host.M48O_TXT, host.DIR_ETC, payload)
        image = host.m48o_blocks(obj)
        end, header, decoded, sizes = _parse_one(image)
        expected_sizes = []
        remaining = length
        while remaining:
            chunk = min(remaining, 512)
            expected_sizes.append(chunk)
            remaining -= chunk
        require(end == len(image), f"P5.03 trailing bytes at boundary {length}")
        assertions.append(
            {
                "name": f"boundary-{length}-separate-header-and-chunks",
                "passed": len(header) == 32 and decoded == payload and sizes == expected_sizes,
            }
        )
    return assertions


def _negative_assertions(host) -> list[dict[str, object]]:
    payload = bytes((index & 0xFF) for index in range(513))
    obj = host.M48OObject("badframe", host.M48O_TXT, host.DIR_ETC, payload)
    header = host.m48o_header(obj)
    zero = host.M48OObject("zero", host.M48O_TXT, host.DIR_ETC, b"")
    cases = (
        ("reject-combined-header-payload-block", _raw_tap(0xFF, header + payload)),
        ("reject-non-ff-data-flag", _raw_tap(0x00, header)),
        ("reject-bad-rom-checksum", _raw_tap(0xFF, header, corrupt_checksum=True)),
        (
            "reject-short-nonfinal-chunk",
            _raw_tap(0xFF, header) + _raw_tap(0xFF, payload[:511]) + _raw_tap(0xFF, payload[511:]),
        ),
        ("reject-over-512-chunk", _raw_tap(0xFF, header) + _raw_tap(0xFF, payload)),
        (
            "reject-payload-block-for-zero-length",
            _raw_tap(0xFF, host.m48o_header(zero)) + _raw_tap(0xFF, b"X"),
        ),
    )
    assertions: list[dict[str, object]] = []
    for name, image in cases:
        rejected = False
        try:
            end, _, _, _ = _parse_one(image)
            require(end == len(image), "trailing unexpected M48O block")
        except Phase5FramingError:
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
    if step != "P5.03":
        raise DriverError(f"Phase-5 framing step is not registered: {step}")

    host = _load_host(root)
    assertions = _source_contract(root) + _boundary_assertions(host)
    kernel_result, kernel, _ = phase1._assemble_kernel(root, run_command, require_project_tool)
    fixture_result, binary, symbols_path = _assemble_fixture(root, run_command, require_project_tool)
    symbols = phase3_open_descriptions._symbols(
        symbols_path,
        ("zx48_p503_prepare_header_block", "zx48_p503_prepare_chunk"),
    )

    commands = [kernel_result, fixture_result]
    if action == "test":
        _target_chunk_runtime(root, symbols, binary.read_bytes())
        assertions.extend(_negative_assertions(host))

        payload = bytes(((index * 13 + 7) & 0xFF) for index in range(513))
        obj = host.M48OObject("fuseframe", host.M48O_TXT, host.DIR_ETC, payload)
        image = host.m48o_blocks(obj)
        header = host.m48o_header(obj)
        fuse_result = _fuse_tap_runtime(root, run_command, image, header, payload)
        commands.append(fuse_result)
        assertions.extend(
            [
                {"name": "target-chunk-boundaries-runtime", "passed": True},
                {"name": "fuse-consumes-separate-ff-header-512-and-final-1-blocks", "passed": True},
            ]
        )

    failed = [item["name"] for item in assertions if item.get("passed") is not True]
    require(not failed, f"P5.03 framing failures: {failed}")

    hashes = {
        "v1/build/kernel.bin": sha256_file(kernel),
        "v1/build/p503-framing.bin": sha256_file(binary),
        "v1/src/kernel/tape.asm": sha256_file(root / "v1/src/kernel/tape.asm"),
        "v1/tools-host/maketap/maketap.py": sha256_file(root / MAKETAP),
        "v1/tools-host/test-driver/phase5_chunk_framing.py": sha256_file(root / "v1/tools-host/test-driver/phase5_chunk_framing.py"),
        "v1/tools-host/test-driver/run.py": sha256_file(root / "v1/tools-host/test-driver/run.py"),
        "v1/dist/certification/P5.02.build.json": sha256_file(root / "v1/dist/certification/P5.02.build.json"),
        "v1/dist/certification/P5.02.test.json": sha256_file(root / "v1/dist/certification/P5.02.test.json"),
    }
    return commands, hashes, assertions
