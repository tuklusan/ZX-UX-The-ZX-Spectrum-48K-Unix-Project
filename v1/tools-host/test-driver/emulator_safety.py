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
import tomllib
from typing import Any

STATIC_REQUIRED = (
    "duplicate_symbols",
    "section_overflow",
    "kernel_subranges",
    "im2_vector_and_trampoline",
    "kernel_stack_placement",
    "arena_boundaries",
    "syscall_table_duplication",
    "forbidden_user_register_ownership",
    "object_format_sizes",
)


class SafetyContractError(ValueError):
    """Raised when emulator evidence claims more than the contract permits."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SafetyContractError(message)


def load(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        data = tomllib.load(handle)
    require(isinstance(data, dict), "safety contract must be a TOML table")
    return data


def validate(data: dict[str, Any]) -> None:
    require(data.get("schema") == 1, "schema must be 1")

    static = data.get("static")
    require(isinstance(static, dict), "static table required")
    for key in STATIC_REQUIRED:
        require(static.get(key) is True, f"static.{key} must be true")

    emulator = data.get("emulator")
    require(isinstance(emulator, dict), "emulator table required")
    require(emulator.get("fast_inner_format") == "SNA", "fast inner loop must use SNA")
    require(emulator.get("boot_format") == "TAP", "boot integration must use TAP")
    require(emulator.get("tape_format") == "TZX", "tape-format integration must use TZX")
    require(emulator.get("state_assertions") is True, "RAM/register/process-state assertions required")
    require(emulator.get("screenshot_only_oracle") is False, "screenshot-only oracle is forbidden")
    require(
        emulator.get("known_writable_stack_before_synthetic_rom_call") is True,
        "synthetic ROM calls require a known writable stack",
    )
    timeout = emulator.get("hard_timeout_seconds")
    require(isinstance(timeout, int) and 1 <= timeout <= 120, "hard emulator timeout must be 1..120 seconds")

    release = data.get("release")
    require(isinstance(release, dict), "release table required")
    count = release.get("independent_emulators_minimum")
    require(isinstance(count, int) and count >= 2, "release-critical behavior requires at least two emulators")

    physical = data.get("physical")
    require(isinstance(physical, dict), "physical table required")
    require(physical.get("trap_only_counts_as_physical") is False, "trap-only success cannot claim physical certification")
    require(physical.get("tap_tzx_counts_as_physical") is False, "TAP/TZX success cannot claim physical certification")
    require(
        physical.get("requires_real_or_hardware_faithful_loop") is True,
        "physical cassette certification requires real hardware or a hardware-faithful loop",
    )


def negative_fixtures(valid: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    cases: list[tuple[str, dict[str, Any]]] = []

    no_stack = deepcopy(valid)
    no_stack["emulator"]["known_writable_stack_before_synthetic_rom_call"] = False
    cases.append(("synthetic-rom-stack", no_stack))

    no_timeout = deepcopy(valid)
    no_timeout["emulator"]["hard_timeout_seconds"] = 0
    cases.append(("hard-timeout", no_timeout))

    screenshot = deepcopy(valid)
    screenshot["emulator"]["screenshot_only_oracle"] = True
    cases.append(("state-not-screenshot", screenshot))

    one_emulator = deepcopy(valid)
    one_emulator["release"]["independent_emulators_minimum"] = 1
    cases.append(("two-emulator-release", one_emulator))

    trap_claim = deepcopy(valid)
    trap_claim["physical"]["trap_only_counts_as_physical"] = True
    cases.append(("trap-not-physical", trap_claim))

    image_claim = deepcopy(valid)
    image_claim["physical"]["tap_tzx_counts_as_physical"] = True
    cases.append(("image-not-physical", image_claim))

    return cases
