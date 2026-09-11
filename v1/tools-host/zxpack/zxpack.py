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

CODEC_VERSION = "zxp1-host-dp-1"


class ZXP1Error(ValueError):
    pass


@dataclass(frozen=True)
class Token:
    encoded: bytes
    logical_length: int
    rank: int


def decode(stream: bytes, logical_length: int) -> bytes:
    if logical_length < 0 or logical_length > 32768:
        raise ZXP1Error("logical length out of range")
    if logical_length == 0:
        if stream:
            raise ZXP1Error("empty logical stream must have no physical bytes")
        return b""
    out = bytearray()
    offset = 0
    while offset < len(stream):
        token = stream[offset]
        offset += 1
        if token <= 0x3F:
            length = token + 1
            if offset + length > len(stream):
                raise ZXP1Error("truncated literal")
            if len(out) + length > logical_length:
                raise ZXP1Error("logical output overrun")
            out.extend(stream[offset:offset + length])
            offset += length
        elif token <= 0x7F:
            length = (token & 0x3F) + 3
            if offset >= len(stream):
                raise ZXP1Error("truncated RLE")
            if len(out) + length > logical_length:
                raise ZXP1Error("logical output overrun")
            value = stream[offset]
            offset += 1
            out.extend((value,) * length)
        else:
            length = (token & 0x7F) + 3
            if offset >= len(stream):
                raise ZXP1Error("truncated back-reference")
            distance = stream[offset] + 1
            offset += 1
            if distance > len(out):
                raise ZXP1Error("back-reference before logical start")
            if len(out) + length > logical_length:
                raise ZXP1Error("logical output overrun")
            for _ in range(length):
                out.append(out[-distance])
    if len(out) != logical_length:
        raise ZXP1Error("logical output underrun")
    return bytes(out)


def _rle_length(data: bytes, pos: int) -> int:
    end = min(len(data), pos + 66)
    value = data[pos]
    cursor = pos + 1
    while cursor < end and data[cursor] == value:
        cursor += 1
    return cursor - pos


def _backrefs(data: bytes, pos: int):
    max_distance = min(256, pos)
    for distance in range(1, max_distance + 1):
        length = 0
        while length < 130 and pos + length < len(data):
            if data[pos + length] != data[pos + length - distance]:
                break
            length += 1
        if length >= 3:
            yield distance, length


def _candidates(data: bytes, pos: int):
    max_literal = min(64, len(data) - pos)
    for length in range(1, max_literal + 1):
        yield Token(bytes((length - 1,)) + data[pos:pos + length], length, 3)
    rle = _rle_length(data, pos)
    for length in range(3, rle + 1):
        yield Token(bytes((0x40 | (length - 3), data[pos])), length, 1)
    for distance, maximum in _backrefs(data, pos):
        for length in range(3, maximum + 1):
            yield Token(bytes((0x80 | (length - 3), distance - 1)), length, 0)


def encode(data: bytes) -> bytes:
    if len(data) > 32768:
        raise ZXP1Error("logical length exceeds 32768")
    if not data:
        return b""
    # Deterministic minimum-size parse. Ties prefer BACKREF, then RLE, then
    # literal; within a class prefer longer logical consumption and nearer
    # back-reference through candidate ordering/encoded-byte ordering.
    n = len(data)
    best_cost = [10**9] * (n + 1)
    best_key: list[tuple | None] = [None] * (n + 1)
    best_token: list[Token | None] = [None] * (n + 1)
    best_cost[n] = 0
    best_key[n] = ()
    for pos in range(n - 1, -1, -1):
        for token in _candidates(data, pos):
            nxt = pos + token.logical_length
            cost = len(token.encoded) + best_cost[nxt]
            key = (cost, token.rank, -token.logical_length, token.encoded, best_key[nxt])
            if best_key[pos] is None or key < best_key[pos]:
                best_cost[pos] = cost
                best_key[pos] = key
                best_token[pos] = token
    out = bytearray()
    pos = 0
    while pos < n:
        token = best_token[pos]
        if token is None:
            raise AssertionError("ZXP1 dynamic-programming parse gap")
        out.extend(token.encoded)
        pos += token.logical_length
    encoded = bytes(out)
    if decode(encoded, len(data)) != data:
        raise AssertionError("ZXP1 self-roundtrip failed")
    return encoded


def pack_if_smaller(data: bytes) -> tuple[bool, bytes]:
    if not data:
        return False, b""
    encoded = encode(data)
    return (True, encoded) if len(encoded) < len(data) else (False, data)
