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
import struct
from typing import Any, Callable

from driver_core import DriverError
from fuse_harness import FAIL_PC, PASS_PC, run_sna
import phase1

SOURCE = 0xC000
TARGET1 = 0x7000
TARGET2 = 0xA000
RELOC_CODE = 0xA800
TEST_STACK = 0xBFC0


class Phase2RelocationError(DriverError):
    """Raised when the P2.03 ABS16 relocation contract regresses."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Phase2RelocationError(message)


def _word(value: int) -> bytes:
    return bytes((value & 0xFF, (value >> 8) & 0xFF))


def _ld_ix(value: int) -> bytes:
    return b"\xDD\x21" + _word(value)


def _jp_nc(address: int) -> bytes:
    return b"\xD2" + _word(address)


def _expect_word(address: int, value: int) -> bytes:
    return (
        b"\x2A" + _word(address)
        + phase1._ld_de(value)
        + b"\xB7\xED\x52"
        + phase1._jp_nz(FAIL_PC)
    )


def _expect_byte(address: int, value: int) -> bytes:
    return b"\x3A" + _word(address) + bytes((0xFE, value & 0xFF)) + phase1._jp_nz(FAIL_PC)


def _patch(relocator: bytes, extras: tuple[tuple[int, bytes], ...]):
    def patch(ram: bytearray) -> None:
        start = RELOC_CODE - 0x4000
        ram[start:start + len(relocator)] = relocator
        for address, payload in extras:
            require(0x4000 <= address <= 0xFFFF, f"fixture address outside RAM: 0x{address:04X}")
            require(address + len(payload) <= 0x10000, f"fixture crosses address space: 0x{address:04X}")
            offset = address - 0x4000
            ram[offset:offset + len(payload)] = payload
    return patch


def _mex(
    image: bytes,
    *,
    bss_size: int = 0,
    relocations: tuple[int, ...] = (),
    image_size: int | None = None,
    relocation_count: int | None = None,
    relocation_offset: int | None = None,
    include_body: bool = True,
) -> bytes:
    declared_image = len(image) if image_size is None else image_size
    declared_count = len(relocations) if relocation_count is None else relocation_count
    declared_offset = (24 + declared_image) & 0xFFFF if relocation_offset is None else relocation_offset & 0xFFFF
    header = bytearray(24)
    header[:4] = b"MEX1"
    header[4] = 1
    struct.pack_into("<H", header, 6, 24)
    struct.pack_into("<H", header, 8, declared_image & 0xFFFF)
    struct.pack_into("<H", header, 10, bss_size & 0xFFFF)
    struct.pack_into("<H", header, 12, 0)
    struct.pack_into("<H", header, 14, 64)
    struct.pack_into("<H", header, 16, declared_count & 0xFFFF)
    struct.pack_into("<H", header, 18, declared_offset)
    if not include_body:
        return bytes(header)
    padding = image
    if len(padding) < declared_image:
        padding += b"\x00" * (declared_image - len(padding))
    table = b"".join(struct.pack("<H", item & 0xFFFF) for item in relocations)
    return bytes(header) + padding + table


def _assemble_fixture(
    root: Path,
    run_command: Callable[..., Any],
    require_project_tool: Callable[[Path, str | Path], Path],
):
    assembler = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    source = build / "p203-reloc.asm"
    binary = build / "p203-reloc.bin"
    listing = build / "p203-reloc.lst"
    symbols = build / "p203-reloc.sym"
    source.write_text(
        "DEVICE ZXSPECTRUM48\n"
        "INCLUDE \"../include/zx48ux.inc\"\n"
        "INCLUDE \"../include/mex1.inc\"\n"
        "INCLUDE \"../src/kernel/process.asm\"\n"
        f"ORG ${RELOC_CODE:04X}\n"
        "p203_reloc_start:\n"
        "    EMIT_MEX1_RELOCATION_ROUTINES\n"
        "p203_reloc_end:\n"
        "SAVEBIN \"p203-reloc.bin\",p203_reloc_start,p203_reloc_end-p203_reloc_start\n",
        encoding="utf-8",
        newline="\n",
    )
    result = run_command(
        [assembler, "--nologo", "--lst=p203-reloc.lst", "--sym=p203-reloc.sym", "p203-reloc.asm"],
        cwd=build,
        timeout_seconds=30.0,
    )
    require(not result.timed_out and result.exit_code == 0, f"P2.03 relocation fixture assembly failed: {result.stderr or result.stdout}")
    require(binary.is_file() and 0 < binary.stat().st_size < 0x0800, "P2.03 relocation fixture binary missing or implausibly large")
    require(symbols.is_file() and listing.is_file(), "P2.03 relocation fixture symbols/listing missing")
    return result, binary, symbols


def _symbols(path: Path, names: tuple[str, ...]) -> dict[str, int]:
    text = path.read_text(encoding="utf-8", errors="replace")
    found: dict[str, int] = {}
    for name in names:
        pattern = re.compile(rf"^{re.escape(name)}:\s+equ\s+0x([0-9A-Fa-f]+)\s*$", re.IGNORECASE)
        for line in text.splitlines():
            match = pattern.match(line.strip())
            if match is not None:
                found[name] = int(match.group(1), 16)
                break
        require(name in found, f"P2.03 fixture symbol missing: {name}")
    return found


def _call_relocator(relocator: int, base: int) -> bytes:
    return _ld_ix(SOURCE) + phase1._ld_de(base) + phase1._call(relocator)


def _golden_fixture(root: Path, relocator: int, relocator_bytes: bytes) -> None:
    image = b"\x04\x00\x08\x00\xC9\x00"
    source = _mex(image, bss_size=4, relocations=(0, 2))
    code = bytearray(b"\xF3" + phase1._ld_sp(TEST_STACK))
    code += _call_relocator(relocator, TARGET1) + phase1._jp_c(FAIL_PC)
    code += _expect_word(TARGET1, TARGET1 + 4) + _expect_word(TARGET1 + 2, TARGET1 + 8)
    code += _call_relocator(relocator, TARGET2) + phase1._jp_c(FAIL_PC)
    code += _expect_word(TARGET2, TARGET2 + 4) + _expect_word(TARGET2 + 2, TARGET2 + 8)
    code += phase1._jp(PASS_PC)
    run_sna(
        root,
        bytes(code),
        patch=_patch(relocator_bytes, ((SOURCE, source), (TARGET1, image), (TARGET2, image))),
    )


def _negative_fixture(
    root: Path,
    relocator: int,
    e_format: int,
    relocator_bytes: bytes,
    *,
    source: bytes,
    base: int,
    target: bytes | None = None,
) -> None:
    code = bytearray(b"\xF3" + phase1._ld_sp(TEST_STACK))
    code += _call_relocator(relocator, base) + _jp_nc(FAIL_PC)
    code += bytes((0xFE, e_format & 0xFF)) + phase1._jp_nz(FAIL_PC)
    extras: list[tuple[int, bytes]] = [(SOURCE, source)]
    if target is not None:
        extras.append((base, target))
        for index, byte in enumerate(target):
            code += _expect_byte(base + index, byte)
    code += phase1._jp(PASS_PC)
    run_sna(root, bytes(code), patch=_patch(relocator_bytes, tuple(extras)))


def _target_tests(root: Path, symbols: dict[str, int], relocator_bytes: bytes) -> list[dict[str, object]]:
    relocator = symbols["zx48_mex1_relocate"]
    e_format = symbols["E_FORMAT"]
    require(RELOC_CODE <= relocator < RELOC_CODE + len(relocator_bytes), "P2.03 relocator label outside fixture binary")
    require(e_format == 0x0B, "P2.03 E_FORMAT ABI value changed")
    image = b"\x04\x00\x08\x00\xC9\x00"
    _golden_fixture(root, relocator, relocator_bytes)

    malformed = (
        ("unsorted-atomic", _mex(image, bss_size=4, relocations=(2, 0)), TARGET1, image),
        ("overlap-atomic", _mex(image, bss_size=4, relocations=(0, 1)), TARGET1, image),
        ("end-overrun-atomic", _mex(image, bss_size=4, relocations=(5,)), TARGET1, image),
        ("reloc-with-image-under-two", _mex(b"\xC9", relocations=(0,)), TARGET1, b"\xC9"),
        ("wrap-24-plus-image-size", _mex(b"", image_size=0xFFF0, relocation_count=0, relocation_offset=0x0008, include_body=False), TARGET1, None),
        ("wrap-relocation-count-times-two", _mex(b"", image_size=2, relocation_count=0x8000, relocation_offset=26, include_body=False), TARGET1, None),
        ("wrap-relocation-table-end", _mex(b"", image_size=2, relocation_count=0x7FF8, relocation_offset=26, include_body=False), TARGET1, None),
        ("wrap-image-plus-bss", _mex(b"", image_size=1, bss_size=0xFFFF, relocation_count=0, relocation_offset=25, include_body=False), TARGET1, None),
        ("base-below-arena", _mex(b"", image_size=1, relocation_count=0, relocation_offset=25, include_body=False), 0x5FFF, None),
        ("allocation-past-arena", _mex(b"", image_size=16, relocation_count=0, relocation_offset=40, include_body=False), 0xDFF8, None),
        ("wrap-actual-base-plus-allocation", _mex(b"", image_size=0x8000, relocation_count=0, relocation_offset=0x8018, include_body=False), 0xD000, None),
        ("wrap-stored-word-plus-base", _mex(b"\x00\x30", bss_size=0x2FFE, relocations=(0,)), 0xDFF0, b"\x00\x30"),
    )
    for _name, source, base, target in malformed:
        _negative_fixture(root, relocator, e_format, relocator_bytes, source=source, base=base, target=target)
    return [
        {"name": "golden-relocations-at-two-bases", "passed": True, "bases": [TARGET1, TARGET2]},
        *({"name": f"reject-{name}", "passed": True} for name, _source, _base, _target in malformed),
    ]


def _source_contract(root: Path) -> list[dict[str, object]]:
    process = (root / "v1/src/kernel/process.asm").read_text(encoding="utf-8")
    start = process.index("    MACRO EMIT_MEX1_RELOCATION_ROUTINES")
    routine = process[start:]
    apply = routine.index("zx48_mex1_relocate_apply_loop:")
    first_target_write = routine.index("    ld (hl),e")
    resident_end = process.index("    ENDM\n", process.index("    MACRO EMIT_PROCESS_ROUTINES"))
    required = (
        "MEX_HDR_IMAGE_SIZE",
        "zx48_mex1_relocate_validate_loop:",
        "zx48_mex1_relocate_apply_loop:",
        "ld a,E_FORMAT",
        "add hl,hl",
        "MEX_HDR_RELOC_OFFSET",
        "ARENA_START",
        "ARENA_END+1",
        "process_mex_previous",
    )
    return [
        {"name": "relocator-uses-frozen-mex1-constants", "passed": all(token in routine for token in ("MEX_HDR_IMAGE_SIZE", "MEX_HDR_BSS_SIZE", "MEX_HDR_RELOC_COUNT", "MEX_HDR_RELOC_OFFSET", "MEX_HEADER_SIZE"))},
        {"name": "relocator-not-yet-emitted-by-resident-process-macro", "passed": resident_end < start},
        {"name": "relocator-two-pass-atomic-order", "passed": apply < first_target_write},
        {"name": "relocator-contract-tokens-present", "passed": all(token in routine for token in required[1:])},
        {"name": "relocator-has-explicit-widened-carry-guards", "passed": routine.count("jp c,zx48_mex1_relocate_format") >= 6},
        {"name": "stored-word-plus-base-carry-guard-present", "passed": "pop hl\n    ld de,(process_mex_base)\n    add hl,de\n    jp c,zx48_mex1_relocate_format" in routine},
    ]


def _host_wrap_contract() -> list[dict[str, object]]:
    vectors = {
        "24-plus-image-size": 24 + 0xFFF0,
        "relocation-count-times-two": 0x8000 * 2,
        "relocation-table-offset-plus-bytes": 26 + 0x7FF8 * 2,
        "image-size-plus-bss-size": 1 + 0xFFFF,
        "actual-base-plus-allocation-size": 0xD000 + 0x8000,
        "stored-word-plus-actual-base": 0x3000 + 0xDFF0,
    }
    return [
        {"name": f"widened-{name}-exceeds-u16", "passed": value > 0xFFFF, "value": value}
        for name, value in vectors.items()
    ]


def dispatch(
    root: Path,
    action: str,
    step: str,
    *,
    sha256_file: Callable[[Path], str],
    run_command: Callable[..., Any],
    require_project_tool: Callable[[Path, str | Path], Path],
):
    if step != "P2.03":
        raise DriverError(f"Phase-2 relocation step is not registered: {step}")

    assertions = _source_contract(root) + _host_wrap_contract()
    failed = [item["name"] for item in assertions if item["passed"] is not True]
    require(not failed, f"static P2.03 contract failures: {failed}")

    command, binary, symbol_path = _assemble_fixture(root, run_command, require_project_tool)
    symbols = _symbols(symbol_path, ("zx48_mex1_relocate", "E_FORMAT"))
    relocator_bytes = binary.read_bytes()
    if action == "test":
        assertions.extend(_target_tests(root, symbols, relocator_bytes))

    return [command], {
        "v1/build/p203-reloc.bin": sha256_file(binary),
        "v1/include/mex1.inc": sha256_file(root / "v1/include/mex1.inc"),
        "v1/src/kernel/process.asm": sha256_file(root / "v1/src/kernel/process.asm"),
        "v1/tools-host/test-driver/phase2_relocation.py": sha256_file(root / "v1/tools-host/test-driver/phase2_relocation.py"),
    }, assertions
