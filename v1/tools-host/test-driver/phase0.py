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

from copy import deepcopy
from pathlib import Path
import re
from typing import Any

EQU = re.compile(r"^([A-Z][A-Z0-9_]*)\s+EQU\s+(\$[0-9A-Fa-f]+|[0-9]+)\s*$")

EXPECTED_CONSTANTS = {
    "CPU_ADDRESS_SPACE_SIZE": 0x10000,
    "ZX48_ROM_SIZE": 0x4000,
    "ZX48_RAM_SIZE": 0xC000,
    "ZX48_PAL_FRAME_HZ": 50,
    "ZX48_Z80_CLOCK_HZ": 3500000,
    "ROM_START": 0x0000,
    "ROM_END": 0x3FFF,
    "BITMAP_START": 0x4000,
    "BITMAP_END": 0x57FF,
    "ATTR_START": 0x5800,
    "ATTR_END": 0x5AFF,
    "ROM_COMPAT_START": 0x5B00,
    "ROM_COMPAT_END": 0x5FFF,
    "COLD_START": 0x6000,
    "COLD_END": 0x7FFF,
    "FAST_START": 0x8000,
    "FAST_END": 0xDFFF,
    "KERNEL_START": 0xE000,
    "KERNEL_END": 0xFFFF,
    "CONTENDED_RAM_START": 0x4000,
    "CONTENDED_RAM_END": 0x7FFF,
    "UNCONTENDED_RAM_START": 0x8000,
    "UNCONTENDED_RAM_END": 0xFFFF,
    "ULA_PORT": 0x00FE,
    "ULA_BORDER_MASK": 0x07,
    "ULA_MIC_BIT": 3,
    "ULA_BEEPER_BIT": 4,
    "ULA_EAR_BIT": 6,
    "KEYBOARD_ROW_MASK": 0x1F,
}

REQUIRED_IO = {
    "keyboard",
    "bitmap",
    "attributes",
    "border",
    "beeper",
    "ear",
    "mic",
    "cassette-load",
    "cassette-save",
}

OUT_OF_SCOPE_EXTENSIONS = {
    "joystick",
    "printer",
    "interface-1",
    "microdrive",
    "serial",
    "mouse",
}

RANGES = (
    ("ROM_START", "ROM_END"),
    ("BITMAP_START", "BITMAP_END"),
    ("ATTR_START", "ATTR_END"),
    ("ROM_COMPAT_START", "ROM_COMPAT_END"),
    ("COLD_START", "COLD_END"),
    ("FAST_START", "FAST_END"),
    ("KERNEL_START", "KERNEL_END"),
)


class Phase0Error(ValueError):
    """Raised when a Phase-0 frozen contract is violated."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Phase0Error(message)


def parse_equ_constants(text: str) -> dict[str, int]:
    result: dict[str, int] = {}
    for raw in text.splitlines():
        code = raw.split(";", 1)[0].strip()
        if not code:
            continue
        match = EQU.match(code)
        if not match:
            continue
        name, value_text = match.groups()
        value = int(value_text[1:], 16) if value_text.startswith("$") else int(value_text, 10)
        require(name not in result, f"duplicate EQU constant: {name}")
        result[name] = value
    return result


def validate_boundaries(constants: dict[str, int]) -> None:
    for name, expected in EXPECTED_CONSTANTS.items():
        require(constants.get(name) == expected, f"{name}: expected {expected:#x}, got {constants.get(name)!r}")

    previous_end = -1
    for start_name, end_name in RANGES:
        start = constants[start_name]
        end = constants[end_name]
        require(start <= end, f"{start_name}/{end_name}: inverted range")
        require(start == previous_end + 1, f"{start_name}: gap/overlap after previous range")
        previous_end = end
    require(previous_end == 0xFFFF, "memory map does not end at FFFF")

    require(constants["ROM_END"] - constants["ROM_START"] + 1 == constants["ZX48_ROM_SIZE"], "ROM size mismatch")
    require(0x10000 - constants["BITMAP_START"] == constants["ZX48_RAM_SIZE"], "RAM size mismatch")
    require(constants["CONTENDED_RAM_START"] == 0x4000 and constants["CONTENDED_RAM_END"] == 0x7FFF, "contended RAM split mismatch")
    require(constants["UNCONTENDED_RAM_START"] == 0x8000 and constants["UNCONTENDED_RAM_END"] == 0xFFFF, "uncontended RAM split mismatch")


def canonical_profile() -> dict[str, Any]:
    return {
        "profile": "zx48-pal",
        "cpu": "documented-z80a",
        "clock_hz": 3500000,
        "frame_hz": 50,
        "wall_clock_hz": 50,
        "cpu_address_bytes": 65536,
        "rom_bytes": 16384,
        "ram_bytes": 49152,
        "bank_switching": False,
        "ram_under_rom": False,
        "required_io": set(REQUIRED_IO),
        "mandatory_extensions": set(),
        "explicit_compatibility_timing": False,
    }


def validate_profile(profile: dict[str, Any]) -> None:
    require(profile.get("profile") == "zx48-pal", "version-1 baseline profile must be zx48-pal")
    require(profile.get("cpu") == "documented-z80a", "documented Z80A profile required")
    require(profile.get("clock_hz") == 3500000, "nominal Z80 clock must be 3.5 MHz")
    require(profile.get("frame_hz") == 50, "PAL baseline frame rate must be 50 Hz")
    require(profile.get("wall_clock_hz") == 50, "PAL wall clock must derive from 50 Hz frames")
    require(profile.get("cpu_address_bytes") == 65536, "CPU address space must be 64 KiB")
    require(profile.get("rom_bytes") == 16384, "ROM must be 16 KiB")
    require(profile.get("ram_bytes") == 49152, "RAM must be 48 KiB")
    require(profile.get("bank_switching") is False, "bank switching is forbidden in baseline")
    require(profile.get("ram_under_rom") is False, "RAM-under-ROM is forbidden in baseline")
    require(profile.get("required_io") == REQUIRED_IO, "required base-I/O capability set mismatch")
    require(not (set(profile.get("mandatory_extensions", set())) & OUT_OF_SCOPE_EXTENSIONS), "extension marked mandatory for version 1")


def validate_nonpal_profile(profile: dict[str, Any]) -> None:
    require(profile.get("profile") != "zx48-pal", "negative compatibility fixture must be non-PAL")
    require(profile.get("explicit_compatibility_timing") is True, "non-PAL profile requires explicit compatibility timing")
    require(profile.get("wall_clock_hz") == profile.get("frame_hz"), "non-PAL wall clock cannot silently retain PAL 50-Hz timing")


def p001_positive(include_path: Path) -> dict[str, Any]:
    constants = parse_equ_constants(include_path.read_text(encoding="utf-8"))
    validate_boundaries(constants)
    profile = canonical_profile()
    validate_profile(profile)
    return profile


def p001_negative_fixtures(include_path: Path) -> list[tuple[str, bool]]:
    constants = parse_equ_constants(include_path.read_text(encoding="utf-8"))
    results: list[tuple[str, bool]] = []

    for start_name, end_name in RANGES:
        broken = dict(constants)
        broken[end_name] += 1
        rejected = False
        try:
            validate_boundaries(broken)
        except Phase0Error:
            rejected = True
        results.append((f"off-by-one-{end_name.lower()}", rejected))

    missing_io = canonical_profile()
    missing_io["required_io"] = set(REQUIRED_IO) - {"mic"}
    try:
        validate_profile(missing_io)
        results.append(("missing-base-io", False))
    except Phase0Error:
        results.append(("missing-base-io", True))

    extension = canonical_profile()
    extension["mandatory_extensions"] = {"joystick"}
    try:
        validate_profile(extension)
        results.append(("mandatory-extension", False))
    except Phase0Error:
        results.append(("mandatory-extension", True))

    nonpal = canonical_profile()
    nonpal.update(
        {
            "profile": "zx48-other-timing",
            "frame_hz": 60,
            "wall_clock_hz": 50,
            "explicit_compatibility_timing": False,
        }
    )
    try:
        validate_nonpal_profile(nonpal)
        results.append(("silent-pal-wall-clock-on-nonpal", False))
    except Phase0Error:
        results.append(("silent-pal-wall-clock-on-nonpal", True))

    return results
