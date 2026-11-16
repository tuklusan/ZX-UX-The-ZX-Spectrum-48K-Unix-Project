"""Assembly of the restricted SJASMPlus source emitted by this compiler."""
from __future__ import annotations
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Based on original work by Supratim Sanyal of SANYALnet Labs.
# Distributed under the accompanying LICENSE for non-commercial use.

import re


ORIGIN = 0x6085
_LABEL = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*\b")
_HEX = re.compile(r"\$([0-9A-Fa-f]+)")


def _skoolkit_assembler():
    from ._skoolkit_z80 import Assembler

    return Assembler()


def _clean_line(line: str) -> str:
    return line.split(";", 1)[0].strip()


def _label_definitions(lines: list[str]) -> dict[str, str]:
    labels: dict[str, str] = {}
    for line in lines:
        text = _clean_line(line)
        if not text:
            continue
        token = text.split(None, 1)[0]
        if token.endswith(":"):
            name = token[:-1]
            labels[name.lower()] = name
    return labels


def _replace_labels(text: str, labels: dict[str, int | str]) -> str:
    def replace(match: re.Match[str]) -> str:
        name = match.group(0)
        value = labels.get(name.lower())
        return str(value) if value is not None else name

    return _LABEL.sub(replace, text)


def _assembler_operation(operation: str) -> str:
    token, separator, remainder = operation.partition(" ")
    if token.lower() == "db":
        return f"DEFB{separator}{remainder}".rstrip()
    return operation


def _permissive_relative(operation: str, address: int) -> tuple[int, ...]:
    match = re.fullmatch(
        r"(JR|DJNZ)(?:\s+(NZ|Z|NC|C)\s*,)?\s*(\$[0-9A-Fa-f]+|0[xX][0-9A-Fa-f]+|[0-9]+)",
        operation.strip(),
        re.IGNORECASE,
    )
    if not match:
        return ()
    mnemonic, condition, target_text = match.groups()
    target = int(target_text[1:], 16) if target_text.startswith("$") else int(target_text, 0)
    if mnemonic.upper() == "DJNZ":
        opcode = 0x10
    else:
        opcode = {None: 0x18, "NZ": 0x20, "Z": 0x28, "NC": 0x30, "C": 0x38}[condition.upper() if condition else None]
    displacement = (target - address - 2) & 0xFF
    return opcode, displacement


def assemble_sjasmplus(source: str, origin: int = ORIGIN) -> bytes:
    """Assemble the restricted SJASMPlus emitted by ``format_sjasmplus``."""
    assembler = _skoolkit_assembler()
    lines = source.splitlines()
    label_names = _label_definitions(lines)
    labels: dict[str, int] = {}
    entries: list[tuple[str, int, str]] = []
    address = origin

    for raw in lines:
        text = _clean_line(raw)
        if not text:
            continue
        pieces = text.split(None, 1)
        token = pieces[0]
        remainder = pieces[1] if len(pieces) == 2 else ""
        if token.endswith(":"):
            labels[token[:-1].lower()] = address
            text = remainder.strip()
            if not text:
                continue
            pieces = text.split(None, 1)
            token = pieces[0]
            remainder = pieces[1] if len(pieces) == 2 else ""
        if token.lower() == "org":
            address = int(_HEX.sub(r"0x\1", remainder), 0)
            entries.append(("org", address, ""))
            continue
        operation = f"{token} {remainder}".strip()
        provisional = _replace_labels(
            _assembler_operation(operation),
            {name: address for name in label_names},
        )
        size = assembler.get_size(provisional, address)
        if not size:
            size = len(_permissive_relative(provisional, address))
        if not size:
            raise ValueError(f"cannot size assembler line at ${address:04X}: {operation}")
        entries.append(("op", address, operation))
        address += size

    output = bytearray()
    address = origin
    for kind, entry_address, operation in entries:
        if kind == "org":
            address = entry_address
            continue
        resolved = _replace_labels(_assembler_operation(operation), labels)
        encoded = assembler.assemble(resolved, entry_address)
        if not encoded:
            encoded = _permissive_relative(resolved, entry_address)
        if not encoded:
            raise ValueError(f"cannot assemble at ${entry_address:04X}: {operation}")
        output.extend(encoded)
        address = entry_address + len(encoded)
    return bytes(output)
