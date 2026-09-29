#!/usr/bin/env python3
# ============================================================================
# Copyright (c) 2026 SANYALnet Labs.
# Proprietary rights reserved except as expressly licensed herein.
#
# ZX-UX C48 SDK
# This file is governed by the SANYALnet Labs Non-Commercial License in the
# root LICENSE file. Non-Commercial use is permitted; Commercial Use and use
# restricted model training is prohibited unless separately authorized.
#
# Attribution required: SANYALnet Labs. See LICENSE for full terms,
# warranty disclaimer, termination, patent, trademark, and governing-law
# provisions.
# ============================================================================
from __future__ import annotations

import argparse
from dataclasses import dataclass
import os
from pathlib import Path
import struct
import tempfile

from c48 import __version__

MAGIC = b"M48O"
VERSION = 1
HEADER_SIZE = 32
NAME_SIZE = 10
CHUNK_SIZE = 512
DATA_FLAG = 0xFF
TYPE_TXT = 1
TYPE_C = 5
TARGET_USERHOME = 5
MAX_PAYLOAD = 32768
ALLOWED_SUFFIXES = {".c", ".h", ".txt"}
PORTABLE_NAME_BYTES = set(
    b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-."
)


class SourceTapeError(ValueError):
    pass


@dataclass(frozen=True)
class SourceSpec:
    path: Path
    tape_name: str
    object_type: int
    payload: bytes


@dataclass(frozen=True)
class TapeObject:
    name: str
    object_type: int
    target: int
    payload: bytes


def crc16_ccitt_false(data: bytes) -> int:
    crc = 0xFFFF
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc


def _xor_checksum(data: bytes) -> int:
    value = 0
    for byte in data:
        value ^= byte
    return value


def _tap_block(body: bytes) -> bytes:
    framed = bytes((DATA_FLAG,)) + body
    framed += bytes((_xor_checksum(framed),))
    return struct.pack("<H", len(framed)) + framed


def _validate_tape_name(name: str, expected_suffix: str) -> None:
    try:
        encoded = name.encode("ascii")
    except UnicodeEncodeError as exc:
        raise SourceTapeError(f"tape object name is not ASCII: {name!r}") from exc
    if not 1 <= len(encoded) <= NAME_SIZE:
        raise SourceTapeError(
            f"tape object name must be 1..{NAME_SIZE} bytes: {name!r}"
        )
    if name in {".", ".."} or any(
        byte not in PORTABLE_NAME_BYTES for byte in encoded
    ):
        raise SourceTapeError(f"tape object name is not portable: {name!r}")
    if Path(name).name != name:
        raise SourceTapeError(f"tape object name must be a base name: {name!r}")
    if Path(name).suffix != expected_suffix:
        raise SourceTapeError(
            f"tape object name must keep the {expected_suffix} suffix: {name!r}"
        )


def _validate_source_text(path: Path, payload: bytes) -> None:
    if len(payload) > MAX_PAYLOAD:
        raise SourceTapeError(
            f"input is too large for one M48O object ({len(payload)} bytes): "
            f"{path}"
        )
    try:
        payload.decode("ascii")
    except UnicodeDecodeError as exc:
        raise SourceTapeError(f"input must be ASCII text: {path}") from exc
    if b"\r" in payload:
        raise SourceTapeError(f"input must use LF line endings: {path}")
    if b"\0" in payload:
        raise SourceTapeError(f"input contains a NUL byte: {path}")


def _object_type(suffix: str) -> int:
    return TYPE_C if suffix == ".c" else TYPE_TXT


def _parse_name_overrides(
    items: list[list[str]] | None,
) -> dict[str, str]:
    result: dict[str, str] = {}
    for source, name in items or []:
        if source in result:
            raise SourceTapeError(f"duplicate --name source: {source}")
        result[source] = name
    return result


def collect_sources(
    source_args: list[str],
    name_items: list[list[str]] | None,
) -> list[SourceSpec]:
    overrides = _parse_name_overrides(name_items)
    source_set = set(source_args)
    unknown = sorted(set(overrides) - source_set)
    if unknown:
        raise SourceTapeError(
            "--name references a source that is not an input: "
            + ", ".join(unknown)
        )

    specs: list[SourceSpec] = []
    tape_names: set[str] = set()
    for raw in source_args:
        path = Path(raw)
        suffix = path.suffix
        if suffix not in ALLOWED_SUFFIXES:
            raise SourceTapeError(
                f"unsupported input {raw!r}; only lowercase .c, .h, and .txt "
                "files are accepted"
            )
        if not path.is_file():
            raise SourceTapeError(f"input file does not exist: {raw}")
        tape_name = overrides.get(raw, path.name)
        _validate_tape_name(tape_name, suffix)
        if tape_name in tape_names:
            raise SourceTapeError(f"duplicate tape object name: {tape_name}")
        tape_names.add(tape_name)
        payload = path.read_bytes()
        _validate_source_text(path, payload)
        specs.append(
            SourceSpec(path, tape_name, _object_type(suffix), payload)
        )
    return specs


def m48o_header(spec: SourceSpec) -> bytes:
    encoded = spec.tape_name.encode("ascii")
    header = bytearray(HEADER_SIZE)
    header[0:4] = MAGIC
    header[4] = VERSION
    header[5] = spec.object_type
    header[6] = 0
    header[7] = TARGET_USERHOME
    header[8:10] = len(spec.payload).to_bytes(2, "little")
    header[10:12] = len(spec.payload).to_bytes(2, "little")
    header[12:14] = b"\0\0"
    header[14:16] = crc16_ccitt_false(spec.payload).to_bytes(2, "little")
    header[16:26] = encoded.ljust(NAME_SIZE, b"\0")
    header[26:28] = b"\0\0"
    header[28:32] = b"\0\0\0\0"
    header[26:28] = crc16_ccitt_false(bytes(header)).to_bytes(2, "little")
    return bytes(header)


def build_tape(specs: list[SourceSpec]) -> bytes:
    image = bytearray()
    for spec in specs:
        image.extend(_tap_block(m48o_header(spec)))
        for offset in range(0, len(spec.payload), CHUNK_SIZE):
            image.extend(
                _tap_block(spec.payload[offset:offset + CHUNK_SIZE])
            )
    built = bytes(image)
    decoded = parse_tape(built)
    expected = [
        TapeObject(
            spec.tape_name,
            spec.object_type,
            TARGET_USERHOME,
            spec.payload,
        )
        for spec in specs
    ]
    if decoded != expected:
        raise SourceTapeError("internal round-trip validation failed")
    return built


def _read_block(image: bytes, offset: int) -> tuple[bytes, int]:
    if offset + 2 > len(image):
        raise SourceTapeError("truncated TAP block length")
    length = int.from_bytes(image[offset:offset + 2], "little")
    offset += 2
    if length < 2 or offset + length > len(image):
        raise SourceTapeError("truncated TAP block")
    framed = image[offset:offset + length]
    offset += length
    if _xor_checksum(framed) != 0:
        raise SourceTapeError("TAP checksum mismatch")
    if framed[0] != DATA_FLAG:
        raise SourceTapeError("M48O TAP block must use data flag FF")
    return framed[1:-1], offset


def _header_name(field: bytes) -> str:
    try:
        end = field.index(0)
    except ValueError:
        end = len(field)
    if any(field[end:]):
        raise SourceTapeError("M48O name padding is invalid")
    raw = field[:end]
    if not 1 <= len(raw) <= NAME_SIZE or any(
        byte not in PORTABLE_NAME_BYTES for byte in raw
    ):
        raise SourceTapeError("M48O name is invalid")
    try:
        return raw.decode("ascii")
    except UnicodeDecodeError as exc:
        raise SourceTapeError("M48O name is not ASCII") from exc


def _parse_header(
    header: bytes,
) -> tuple[str, int, int, int, int]:
    if (
        len(header) != HEADER_SIZE
        or header[:4] != MAGIC
        or header[4] != VERSION
    ):
        raise SourceTapeError("M48O header identity is invalid")
    object_type = header[5]
    if object_type not in {TYPE_TXT, TYPE_C}:
        raise SourceTapeError("unexpected source object type")
    if header[6] != 0 or header[7] != TARGET_USERHOME:
        raise SourceTapeError("source object flags or target are invalid")
    physical = int.from_bytes(header[8:10], "little")
    logical = int.from_bytes(header[10:12], "little")
    if (
        physical != logical
        or physical > MAX_PAYLOAD
        or header[12:14] != b"\0\0"
    ):
        raise SourceTapeError("RAW source length or codec is invalid")
    if header[28:32] != b"\0\0\0\0":
        raise SourceTapeError("M48O reserved bytes are not zero")
    stored_header_crc = int.from_bytes(header[26:28], "little")
    crc_image = bytearray(header)
    crc_image[26:28] = b"\0\0"
    if crc16_ccitt_false(bytes(crc_image)) != stored_header_crc:
        raise SourceTapeError("M48O header CRC mismatch")
    name = _header_name(header[16:26])
    payload_crc = int.from_bytes(header[14:16], "little")
    return name, object_type, TARGET_USERHOME, physical, payload_crc


def parse_tape(image: bytes) -> list[TapeObject]:
    offset = 0
    objects: list[TapeObject] = []
    while offset < len(image):
        header, offset = _read_block(image, offset)
        name, object_type, target, length, expected_crc = _parse_header(
            header
        )
        payload = bytearray()
        remaining = length
        while remaining:
            chunk, offset = _read_block(image, offset)
            expected = min(CHUNK_SIZE, remaining)
            if len(chunk) != expected:
                raise SourceTapeError(
                    "M48O payload chunk length is invalid"
                )
            payload.extend(chunk)
            remaining -= len(chunk)
        data = bytes(payload)
        if crc16_ccitt_false(data) != expected_crc:
            raise SourceTapeError("M48O payload CRC mismatch")
        objects.append(TapeObject(name, object_type, target, data))
    return objects


def write_tape(output: Path, image: bytes, *, force: bool) -> None:
    if output.suffix != ".tap":
        raise SourceTapeError(
            "output must use the lowercase .tap suffix"
        )
    if not output.parent.is_dir():
        raise SourceTapeError(
            f"output directory does not exist: {output.parent}"
        )
    if output.exists() and not force:
        raise SourceTapeError(
            f"output already exists; use --force to replace it: {output}"
        )
    handle = tempfile.NamedTemporaryFile(
        mode="wb",
        dir=output.parent,
        prefix=f".{output.name}.",
        delete=False,
    )
    temp = Path(handle.name)
    try:
        with handle:
            handle.write(image)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, output)
    finally:
        if temp.exists():
            temp.unlink()


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="c48srctap",
        description=(
            "Build a ZX-UX source TAP containing RAW M48O C/TXT objects. "
            "Inputs are restricted to lowercase .c, .h, and .txt files; "
            "objects target USERHOME."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "examples:\n"
            "  c48srctap exapi.h hello.c -o hello.src.tap\n"
            "  c48srctap demoapi.h spriteanim.c "
            "--name spriteanim.c sprani.c -o spriteanim.src.tap"
        ),
    )
    parser.add_argument("sources", nargs="+", metavar="SOURCE")
    parser.add_argument(
        "-o",
        "--output",
        required=True,
        type=Path,
        metavar="FILE.tap",
    )
    parser.add_argument(
        "--name",
        action="append",
        nargs=2,
        metavar=("SOURCE", "TAPE_NAME"),
        help=(
            "override one M48O base name; useful when a source base name "
            "exceeds 10 bytes"
        ),
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="replace an existing output file",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = make_parser()
    ns = parser.parse_args(argv)
    try:
        specs = collect_sources(ns.sources, ns.name)
        image = build_tape(specs)
        write_tape(ns.output, image, force=ns.force)
    except (OSError, SourceTapeError) as exc:
        parser.error(str(exc))
    print(
        f"c48srctap: wrote {ns.output} "
        f"({len(specs)} objects, {len(image)} bytes)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
