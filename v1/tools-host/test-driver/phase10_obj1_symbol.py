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
from typing import Callable, Any

from driver_core import DriverError


SYMBOL_SIZE = 20
NAME_FIELD = 16
NAME_MAX = 15
SEC_UNDEF = 0
SEC_TEXT = 1
SEC_BSS = 2
SEC_ABS = 3
SYM_GLOBAL = 1
ASM_NAME = re.compile(rb"^[A-Za-z_.$][A-Za-z0-9_.$]*$")
C48_NAME = re.compile(rb"^[A-Za-z_][A-Za-z0-9_]*$")


class Obj1SymbolError(DriverError):
    pass


@dataclass(frozen=True)
class Symbol:
    name: bytes
    value: int
    section: int
    flags: int


def require(ok: bool, message: str) -> None:
    if not ok:
        raise Obj1SymbolError(message)


def decode_name(field: bytes, *, c48: bool = False) -> bytes:
    require(len(field) == NAME_FIELD, "E_FORMAT symbol name field size")
    nul = field.find(b"\x00")
    require(1 <= nul <= NAME_MAX, "E_FORMAT symbol name length/terminator")
    require(field[nul:] == bytes(NAME_FIELD - nul), "E_FORMAT embedded NUL/nonzero tail")
    name = field[:nul]
    grammar = C48_NAME if c48 else ASM_NAME
    require(grammar.fullmatch(name) is not None, "E_FORMAT symbol name grammar")
    return name


def parse_symbol(data: bytes, *, text_size: int, bss_size: int, seen: set[bytes] | None = None, c48: bool = False) -> Symbol:
    require(len(data) == SYMBOL_SIZE, "E_FORMAT symbol record size")
    name = decode_name(data[:NAME_FIELD], c48=c48)
    value = data[16] | (data[17] << 8)
    section = data[18]
    flags = data[19]
    require(section in (SEC_UNDEF, SEC_TEXT, SEC_BSS, SEC_ABS), "E_FORMAT symbol section")
    require(flags & ~SYM_GLOBAL == 0, "E_FORMAT symbol flags")
    if section == SEC_UNDEF:
        require(value == 0, "E_FORMAT UNDEF value")
        require(flags == SYM_GLOBAL, "E_FORMAT UNDEF GLOBAL")
    elif section == SEC_TEXT:
        require(value <= text_size, "E_FORMAT TEXT value")
    elif section == SEC_BSS:
        require(value <= bss_size, "E_FORMAT BSS value")
    if seen is not None:
        require(name not in seen, "E_FORMAT duplicate symbol name")
        seen.add(name)
    return Symbol(name, value, section, flags)


def make_symbol(name: bytes, value: int, section: int, flags: int = 0) -> bytes:
    require(1 <= len(name) <= NAME_MAX, "fixture name length")
    require(0 <= value <= 0xFFFF, "fixture value")
    return name + b"\x00" + bytes(NAME_FIELD - len(name) - 1) + value.to_bytes(2, "little") + bytes((section, flags))


def source_assertions(root: Path) -> list[dict[str, object]]:
    asm = (root / "tools/as.asm").read_text(encoding="utf-8")
    doc = (root / "v1/docs/obj1.md").read_text(encoding="utf-8")
    inc = (root / "v1/include/obj1.inc").read_text(encoding="utf-8")
    return [
        {"name":"native-symbol-size-frozen","passed":"AS_OBJ1_SYMBOL_SIZE      EQU 20" in asm and "OBJ1_SYMBOL_SIZE         EQU 20" in inc},
        {"name":"native-symbol-field-offsets-frozen","passed":all(x in asm for x in ("AS_OBJ1_SYMBOL_VALUE     EQU 16","AS_OBJ1_SYMBOL_SECTION   EQU 18","AS_OBJ1_SYMBOL_FLAGS     EQU 19"))},
        {"name":"native-symbol-name-validation-present","passed":"as_obj1_symbol_name_validate:" in asm and "as_obj1_name_first_char:" in asm},
        {"name":"native-symbol-section-validation-present","passed":"as_obj1_symbol_validate:" in asm and "AS_OBJ1_SEC_UNDEF" in asm and "AS_OBJ1_SEC_ABS" in asm},
        {"name":"doc-assembly-grammar-exact","passed":"[A-Za-z_.$][A-Za-z0-9_.$]*" in doc},
        {"name":"doc-c48-grammar-exact","passed":"[A-Za-z_][A-Za-z0-9_]*" in doc},
        {"name":"doc-no-silent-truncation","passed":"silently truncated" in doc or "Silent truncation" in doc},
    ]


def positive_assertions() -> list[dict[str, object]]:
    seen: set[bytes] = set()
    one = parse_symbol(make_symbol(b"A", 0, SEC_UNDEF, SYM_GLOBAL), text_size=3, bss_size=4, seen=seen)
    fifteen_name = b"a23456789012345"
    fifteen = parse_symbol(make_symbol(fifteen_name, 3, SEC_TEXT, SYM_GLOBAL), text_size=3, bss_size=4, seen=seen)
    punct = parse_symbol(make_symbol(b"_.$a9", 4, SEC_BSS), text_size=3, bss_size=4, seen=seen)
    absolute = parse_symbol(make_symbol(b"ABS", 0xFFFF, SEC_ABS), text_size=0, bss_size=0, seen=seen)
    c48 = parse_symbol(make_symbol(b"_C48name9", 1, SEC_TEXT, SYM_GLOBAL), text_size=1, bss_size=0, c48=True)
    return [
        {"name":"one-byte-name","passed":one.name == b"A"},
        {"name":"fifteen-byte-name","passed":fifteen.name == fifteen_name},
        {"name":"assembly-punctuation-name","passed":punct.name == b"_.$a9"},
        {"name":"abs-full-u16-value","passed":absolute.value == 0xFFFF},
        {"name":"c48-identifier-subset","passed":c48.name == b"_C48name9"},
        {"name":"boundary-text-and-bss-values","passed":fifteen.value == 3 and punct.value == 4},
    ]


def negative_assertions() -> list[dict[str, object]]:
    cases: list[tuple[str, bytes, dict[str, object]]] = []
    def add(label: str, data: bytes, **kwargs: object) -> None:
        cases.append((label, data, kwargs))
    add("empty-name", bytes(NAME_FIELD) + bytes((0,0,SEC_ABS,0)), text_size=0, bss_size=0)
    add("missing-nul-overlength", b"A"*NAME_FIELD + bytes((0,0,SEC_ABS,0)), text_size=0, bss_size=0)
    add("illegal-first-char", make_symbol(b"9bad",0,SEC_ABS), text_size=0, bss_size=0)
    add("illegal-tail-char", make_symbol(b"a-b",0,SEC_ABS), text_size=0, bss_size=0)
    bad_tail = bytearray(make_symbol(b"a",0,SEC_ABS)); bad_tail[2]=ord("x")
    add("embedded-nul-nonzero-tail", bytes(bad_tail), text_size=0, bss_size=0)
    add("undef-not-global", make_symbol(b"u",0,SEC_UNDEF,0), text_size=0, bss_size=0)
    add("undef-nonzero-value", make_symbol(b"u",1,SEC_UNDEF,SYM_GLOBAL), text_size=0, bss_size=0)
    add("invalid-section", make_symbol(b"s",0,4), text_size=0, bss_size=0)
    add("invalid-flag-bits", make_symbol(b"f",0,SEC_ABS,2), text_size=0, bss_size=0)
    add("text-out-of-range", make_symbol(b"t",2,SEC_TEXT), text_size=1, bss_size=0)
    add("bss-out-of-range", make_symbol(b"b",2,SEC_BSS), text_size=0, bss_size=1)
    add("c48-dot-rejected", make_symbol(b"a.b",0,SEC_ABS), text_size=0, bss_size=0, c48=True)
    assertions: list[dict[str, object]] = []
    for label, data, kwargs in cases:
        rejected = False
        try:
            parse_symbol(data, **kwargs)
        except Obj1SymbolError:
            rejected = True
        assertions.append({"name":label,"passed":rejected})
    seen={b"dup"}
    rejected=False
    try:
        parse_symbol(make_symbol(b"dup",0,SEC_ABS), text_size=0, bss_size=0, seen=seen)
    except Obj1SymbolError:
        rejected=True
    assertions.append({"name":"duplicate-name-rejected","passed":rejected})
    return assertions


def dispatch(root: Path, action: str, step: str, *, sha256_file: Callable[[Path], str], run_command: Callable[..., Any], require_project_tool: Callable[[Path, str | Path], Path]):
    if step != "P10.02":
        raise DriverError(f"Phase-10 OBJ1 symbol step is not registered: {step}")
    assertions = source_assertions(root) + positive_assertions()
    if action == "test":
        assertions.extend(negative_assertions())
    failed=[a["name"] for a in assertions if a.get("passed") is not True]
    require(not failed, f"P10.02 contract failures: {failed}")
    hashes={
        "tools/as.asm":sha256_file(root/"tools/as.asm"),
        "v1/include/obj1.inc":sha256_file(root/"v1/include/obj1.inc"),
        "v1/docs/obj1.md":sha256_file(root/"v1/docs/obj1.md"),
        "v1/tools-host/test-driver/phase10_obj1_symbol.py":sha256_file(root/"v1/tools-host/test-driver/phase10_obj1_symbol.py"),
        "v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
        "v1/dist/certification/P10.01.build.json":sha256_file(root/"v1/dist/certification/P10.01.build.json"),
        "v1/dist/certification/P10.01.test.json":sha256_file(root/"v1/dist/certification/P10.01.test.json"),
    }
    return [], hashes, assertions
