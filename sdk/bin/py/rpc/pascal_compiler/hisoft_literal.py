"""Emit the proven HiSoft PROGRAM/WRITELN form using captured CODE.
Original 15_char prefix and tests: docs/source-format.md."""
from __future__ import annotations
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Based on original work by Supratim Sanyal of SANYALnet Labs.
# Distributed under the accompanying LICENSE for non-commercial use.

import re
from pathlib import Path

from .errors import PascalError


ORIGIN = 0x6085
PREFIX_LENGTH = 5527
BASE_IMAGE_LENGTH = 5538
LENGTH_FIELD_OFFSET = 5384
FIELD_OFFSET = 68
POINTER_INSTRUCTION_OFFSET = 5512
POINTER_BASE = 0x89A7
STRING_DATA_ADDRESS = 0x761F

_MINIMAL_LITERAL = re.compile(
    r"\A\s*(?:(?:\{.*?\}|\(\*.*?\*\))\s*)*"
    r"program\s+[A-Za-z][A-Za-z0-9_]*\s*;\s*"
    r"begin\s*writeln\s*\(\s*'([^']*)'\s*\)\s*;?\s*"
    r"end\s*\.\s*\Z",
    re.IGNORECASE | re.DOTALL,
)


def _prefix() -> bytes:
    path = Path(__file__).with_name("data") / "hisoft_minimal_literal_prefix.bin"
    prefix = path.read_bytes()
    if len(prefix) != PREFIX_LENGTH:
        raise RuntimeError(f"invalid HiSoft literal prefix length: {len(prefix)}")
    return prefix


def compile_minimal_literal(source: str) -> bytes | None:
    """Return exact bytes for the proven literal-only form, or ``None``.

    A non-ASCII matched literal is rejected rather than silently approximated.
    Empty strings are left to the general compiler until their original
    lowering is captured.
    """
    match = _MINIMAL_LITERAL.fullmatch(source)
    if match is None:
        return None
    text = match.group(1)
    if not text:
        raise PascalError("empty literal lowering is not yet captured")
    try:
        literal = text.encode("ascii")
    except UnicodeEncodeError as exc:
        raise PascalError("non-ASCII literal is not supported") from exc
    if len(literal) > 255:
        raise PascalError("literal is too long for the captured lowering")

    if len(literal) == 1:
        # The original compiler uses its character-output entry for one byte.
        tail = bytes((0x3E, literal[0])) + bytes.fromhex(
            "CD CB 60 CD 0C 66 C3 AC 60"
        )
    else:
        # Long literals are stored inline immediately before the small print loop. The jump
        # target is the first instruction after that data.
        tail = bytes((0xC3,)) + (STRING_DATA_ADDRESS + len(literal)).to_bytes(
            2, "little"
        )
        tail += literal
        tail += bytes.fromhex("21 1F 76 06") + bytes((len(literal),))
        tail += bytes.fromhex("CD 15 66 CD 0C 66 C3 AC 60")

    output = bytearray(_prefix())
    logical_source = source.rstrip("\r\n")
    output[FIELD_OFFSET:FIELD_OFFSET + 2] = (
        len(logical_source.splitlines()) * 10
    ).to_bytes(2, "little")
    image_length = len(output) + len(tail)
    output[LENGTH_FIELD_OFFSET:LENGTH_FIELD_OFFSET + 2] = image_length.to_bytes(
        2, "little"
    )
    pointer = POINTER_BASE - (image_length - BASE_IMAGE_LENGTH)
    output[POINTER_INSTRUCTION_OFFSET:POINTER_INSTRUCTION_OFFSET + 3] = bytes(
        (0x21, pointer & 0xFF, pointer >> 8)
    )
    output.extend(tail)
    return bytes(output)
