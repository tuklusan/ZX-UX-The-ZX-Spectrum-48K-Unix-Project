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

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Mapping

APP_PARTS = {"shell", "tools", "utils", "libc48"}
CANONICAL_INCLUDE = Path("v1/include/zx48ux.inc")
ROM_OWNER = Path("v1/src/kernel/rom_services.asm")
ULA_OWNER = Path("v1/src/kernel/ula_io.asm")

INSTRUCTION_OR_DIRECTIVE = re.compile(
    r"^(?:adc|add|and|bit|call|ccf|cp|cpd|cpdr|cpi|cpir|cpl|daa|dec|di|djnz|ei|ex|exx|halt|im|in|inc|ind|indr|ini|inir|jp|jr|ld|ldd|lddr|ldi|ldir|neg|nop|or|otdr|otir|out|outd|outi|pop|push|res|ret|reti|retn|rl|rla|rlc|rlca|rld|rr|rra|rrc|rrca|rrd|rst|sbc|scf|set|sla|sll|sra|srl|sub|xor|org|db|dw|ds|equ|include|export|extern|macro|endm|assert)\b",
    re.IGNORECASE,
)
RAW_ROM_TRANSFER = re.compile(r"\b(?:call|jp)\s+\$([0-9a-f]{1,4})\b", re.IGNORECASE)
SYSCALL_EQU = re.compile(r"\bSYS_[A-Z0-9_]+\s+EQU\b", re.IGNORECASE)
RAW_ULA = re.compile(r"\bout\s*\(\s*(?:\$0*fe|254)\s*\)\s*,", re.IGNORECASE)
UNDOCUMENTED = re.compile(r"\b(?:sll|ixh|ixl|iyh|iyl)\b", re.IGNORECASE)
ALT_BANK = re.compile(r"\b(?:exx|ex\s+af\s*,\s*af')\b", re.IGNORECASE)
IY_TOKEN = re.compile(r"\biy\b", re.IGNORECASE)
R_REGISTER = re.compile(r"\bld\s+(?:a\s*,\s*r|r\s*,\s*a)\b", re.IGNORECASE)
MAGIC_ADDRESS = re.compile(r"\$(?:5c3a|6000|7fff|8000|dfff|e000|e003|fafd|fb00|fcff|fd00|fdfc|fdfd|fe00|ff00|ff01|ffff)\b", re.IGNORECASE)
EXPORT = re.compile(r"^\s*export\s+([A-Za-z_.$?@][\w.$?@]*)\b", re.IGNORECASE)

REVIEW_ONLY_RULES = (
    "arena_arithmetic_reviewed",
    "block_instruction_considered",
    "contention_classes_recorded",
    "critical_size_cycles_recorded",
    "hot_cold_placement_documented",
    "screen_formula_owner_reviewed",
    "stack_assumptions_documented",
)


@dataclass(frozen=True)
class Finding:
    rule: str
    line: int
    detail: str


def is_application(path: Path) -> bool:
    parts = set(path.as_posix().split("/"))
    return bool(parts & APP_PARTS)


def code_part(raw: str) -> str:
    return raw.split(";", 1)[0].rstrip()


def has_export_contract(lines: list[str], index: int) -> bool:
    start = max(0, index - 8)
    context = "\n".join(lines[start:index]).lower()
    return all(label in context for label in ("inputs:", "outputs:", "flags:", "clobbers:"))


def scan_source(path: Path, text: str) -> list[Finding]:
    findings: list[Finding] = []
    relative = path.as_posix()
    if relative != relative.lower():
        findings.append(Finding("lower-case-filename", 0, relative))

    lines = text.splitlines()
    for index, raw in enumerate(lines, 1):
        code = code_part(raw)
        if not code.strip():
            continue
        stripped = code.lstrip()
        lowered = stripped.lower()

        if raw and not raw[0].isspace() and INSTRUCTION_OR_DIRECTIVE.match(stripped):
            findings.append(Finding("indent-unlabelled", index, stripped))

        export = EXPORT.match(stripped)
        if export and not has_export_contract(lines, index - 1):
            findings.append(Finding("export-contract", index, export.group(1)))

        if path != CANONICAL_INCLUDE and SYSCALL_EQU.search(code):
            findings.append(Finding("syscall-single-owner", index, stripped))

        if path != ROM_OWNER:
            match = RAW_ROM_TRANSFER.search(code)
            if match and int(match.group(1), 16) < 0x4000:
                findings.append(Finding("rom-service-owner", index, stripped))

        if path != ULA_OWNER and RAW_ULA.search(code):
            findings.append(Finding("ula-shadow-owner", index, stripped))

        if path != CANONICAL_INCLUDE and MAGIC_ADDRESS.search(code):
            findings.append(Finding("named-memory-map", index, stripped))

        if UNDOCUMENTED.search(code):
            findings.append(Finding("documented-z80-only", index, stripped))

        if is_application(path) and IY_TOKEN.search(code):
            findings.append(Finding("iy-os-reserved", index, stripped))

        if is_application(path) and ALT_BANK.search(code):
            findings.append(Finding("alternate-bank-os-private", index, stripped))

        if R_REGISTER.search(code) and "nonsecurity_seed_only" not in raw.lower():
            findings.append(Finding("r-not-correctness-source", index, stripped))

        if "contention_exact_required" in lowered:
            findings.append(Finding("no-precise-contention-dependency", index, stripped))

    return findings


def review_findings(evidence: Mapping[str, bool]) -> list[Finding]:
    findings: list[Finding] = []
    for rule in REVIEW_ONLY_RULES:
        if evidence.get(rule) is not True:
            findings.append(Finding(f"review-evidence:{rule}", 0, "explicit review/measurement evidence required"))
    return findings


def positive_fixture() -> tuple[Path, str, dict[str, bool]]:
    text = (
        "; Inputs: HL source\n"
        "; Outputs: HL preserved\n"
        "; Flags: unchanged\n"
        "; Clobbers: AF\n"
        "safe_copy:\n"
        "    ld a,(hl)\n"
        "    ret\n"
        "    export safe_copy\n"
    )
    return Path("v1/src/kernel/memory.asm"), text, {name: True for name in REVIEW_ONLY_RULES}


def negative_fixtures() -> list[tuple[str, Path, str]]:
    return [
        ("indent-unlabelled", Path("v1/src/kernel/memory.asm"), "LD A,B\n"),
        ("rom-service-owner", Path("v1/src/kernel/memory.asm"), "    call $0562\n"),
        ("syscall-single-owner", Path("v1/src/kernel/syscall.asm"), "SYS_BAD EQU $7f\n"),
        ("named-memory-map", Path("v1/src/kernel/memory.asm"), "    ld hl,$e000\n"),
        ("ula-shadow-owner", Path("v1/src/kernel/graphics.asm"), "    out ($fe),a\n"),
        ("documented-z80-only", Path("v1/src/kernel/memory.asm"), "    sll a\n"),
        ("iy-os-reserved", Path("v1/src/tools/vi.asm"), "    push iy\n"),
        ("alternate-bank-os-private", Path("v1/src/shell/sh.asm"), "    exx\n"),
        ("r-not-correctness-source", Path("v1/src/kernel/memory.asm"), "    ld a,r\n"),
        ("no-precise-contention-dependency", Path("v1/src/kernel/graphics.asm"), "    nop ; contention_exact_required\n"),
        ("export-contract", Path("v1/src/kernel/memory.asm"), "thing:\n    ret\n    export thing\n"),
        ("lower-case-filename", Path("v1/src/utils/Bad.asm"), "    ret\n"),
    ]
