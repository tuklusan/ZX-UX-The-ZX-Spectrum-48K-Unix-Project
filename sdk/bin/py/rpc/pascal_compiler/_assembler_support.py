"""Small support layer for the bundled SkoolKit Z80 assembler module."""
from __future__ import annotations
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Based on original work by Supratim Sanyal of SANYALnet Labs.
# Distributed under the accompanying LICENSE for non-commercial use.

import re


def get_int_param(num_str: str, accept0x: bool = False) -> int:
    try:
        return int(num_str)
    except ValueError:
        pass
    if num_str.startswith("$"):
        return int(num_str[1:], 16)
    if accept0x and num_str.startswith(("0x", "0X")):
        return int(num_str[2:], 16)
    if num_str.startswith("%"):
        return int(num_str[1:], 2)
    if num_str.startswith('"') and num_str.endswith('"'):
        if num_str.startswith('"\\'):
            return ord(num_str[2:-1])
        return ord(num_str[1:-1])
    raise ValueError


def split_unquoted(text: str, separator: str, maxsplit: int = -1) -> list[str]:
    if '"' not in text:
        return text.split(separator, maxsplit)
    elements: list[str] = []
    quoted = False
    for part in text.split(separator):
        if quoted:
            elements[-1] += separator + part
        else:
            elements.append(part)
        index = 0
        while index < len(part):
            char = part[index]
            if char == '"':
                quoted = not quoted
            elif char == "\\" and quoted:
                index += 1
            index += 1
    if len(elements) > maxsplit + 1 > 0:
        elements[maxsplit:] = [separator.join(elements[maxsplit:])]
    return elements


def split_quoted(text: str) -> list[str]:
    return [part for part in re.split(r'("(?:[^"\\]|\\.)*")', text) if part]


def get_operand_evaluator():
    from . import _skoolkit_z80

    return _skoolkit_z80
