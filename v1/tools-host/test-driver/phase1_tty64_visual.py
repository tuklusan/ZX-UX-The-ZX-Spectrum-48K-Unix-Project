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

import hashlib
from pathlib import Path
import shutil
import struct
import tempfile
import zlib
from typing import Any, Callable

from driver_core import DriverError, read_source_state, resolve_evidence_dir
from fuse_harness import FAIL_PC, PASS_PC, make_sna
import phase1

F4X8_SIZE = 392
F4X8_HEADER = b"F4X8\x01\x20\x60\x00"
FONT_SHA256 = "90f6818cf81cf3f13509cff32c091075691195d9638dbe801d12daceec1c9339"
FONT_SOURCE = 0xB200
ATTR_START = 0x5800
ATLAS_FIRST_ROW = 2
ATLAS_COLUMNS = 32
ATLAS_ATTRIBUTE = 0x07
PNG_NAME = "P1.22-font-atlas.png"
SCR_NAME = "P1.22-font-atlas.scr"


class VisualEvidenceError(DriverError):
    """Raised when mandatory P1.22 screenshot evidence or visual inspection fails."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise VisualEvidenceError(message)


def _word(value: int) -> bytes:
    return bytes((value & 0xFF, (value >> 8) & 0xFF))


def _call(address: int) -> bytes:
    return b"\xCD" + _word(address)


def _jp(address: int) -> bytes:
    return b"\xC3" + _word(address)


def _jp_c(address: int) -> bytes:
    return b"\xDA" + _word(address)


def _store_byte(address: int, value: int) -> bytes:
    return bytes((0x3E, value & 0xFF, 0x32)) + _word(address)


def _bitmap_address(pixel_y: int, x_byte: int) -> int:
    require(0 <= pixel_y < 192, "pixel y outside Spectrum bitmap")
    require(0 <= x_byte < 32, "bitmap byte column outside Spectrum bitmap")
    return (
        0x4000
        | ((pixel_y & 0xC0) << 5)
        | ((pixel_y & 0x07) << 8)
        | ((pixel_y & 0x38) << 2)
        | x_byte
    )


def _decode_rows(asset: bytes, code: int) -> tuple[int, ...]:
    require(len(asset) == F4X8_SIZE and asset[:8] == F4X8_HEADER, "canonical F4X8 framing mismatch")
    require(hashlib.sha256(asset).hexdigest() == FONT_SHA256, "canonical F4X8 SHA-256 mismatch")
    require(0x20 <= code <= 0x7F, "atlas code outside F4X8 range")
    index = 8 + (code - 0x20) * 4
    rows: list[int] = []
    for packed in asset[index:index + 4]:
        rows.extend(((packed >> 4) & 0x0F, packed & 0x0F))
    require(len(rows) == 8, "canonical F4X8 glyph decode mismatch")
    return tuple(rows)


def _expected_scr(asset: bytes) -> bytes:
    screen = bytearray(6912)
    for index, code in enumerate(range(0x20, 0x80)):
        row = ATLAS_FIRST_ROW + index // ATLAS_COLUMNS
        col = index % ATLAS_COLUMNS
        x_byte = col >> 1
        for scan, nibble in enumerate(_decode_rows(asset, code)):
            address = _bitmap_address(row * 8 + scan, x_byte)
            offset = address - 0x4000
            if col & 1:
                screen[offset] = (screen[offset] & 0xF0) | nibble
            else:
                screen[offset] = (screen[offset] & 0x0F) | (nibble << 4)
        attr = 6144 + row * 32 + x_byte
        screen[attr] = ATLAS_ATTRIBUTE
    return bytes(screen)


def _paeth(left: int, up: int, upper_left: int) -> int:
    estimate = left + up - upper_left
    dl = abs(estimate - left)
    du = abs(estimate - up)
    dul = abs(estimate - upper_left)
    if dl <= du and dl <= dul:
        return left
    if du <= dul:
        return up
    return upper_left


def _decode_fmfconv_png(png: bytes) -> tuple[int, int, bytes]:
    require(png.startswith(b"\x89PNG\r\n\x1a\n"), "P1.22 PNG signature mismatch")
    cursor = 8
    width = height = None
    palette = None
    idat = bytearray()
    saw_iend = False
    while cursor < len(png):
        require(cursor + 12 <= len(png), "P1.22 PNG truncated chunk header")
        length = struct.unpack(">I", png[cursor:cursor + 4])[0]
        kind = png[cursor + 4:cursor + 8]
        start = cursor + 8
        end = start + length
        require(end + 4 <= len(png), "P1.22 PNG truncated chunk payload")
        payload = png[start:end]
        expected_crc = struct.unpack(">I", png[end:end + 4])[0]
        require((zlib.crc32(kind + payload) & 0xFFFFFFFF) == expected_crc, f"P1.22 PNG CRC mismatch in {kind!r}")
        if kind == b"IHDR":
            require(width is None and length == 13, "P1.22 PNG IHDR invalid or duplicated")
            width, height, bit_depth, colour_type, compression, filter_method, interlace = struct.unpack(">IIBBBBB", payload)
            require(bit_depth == 4 and colour_type == 3, "P1.22 PNG must use fmfconv 4-bit indexed output")
            require(compression == 0 and filter_method == 0 and interlace == 0, "P1.22 PNG uses unsupported encoding")
        elif kind == b"PLTE":
            require(width is not None and palette is None and not idat, "P1.22 PNG PLTE order or duplication invalid")
            require(length == 16 * 3, "P1.22 PNG must contain the fmfconv 16-entry palette")
            entries = [tuple(payload[index:index + 3]) for index in range(0, length, 3)]
            require(all(red == green == blue for red, green, blue in entries), "P1.22 PNG palette is not greyscale")
            palette = tuple(red for red, _green, _blue in entries)
        elif kind == b"IDAT":
            require(width is not None and palette is not None, "P1.22 PNG IDAT precedes required header or palette")
            idat.extend(payload)
        elif kind == b"IEND":
            require(length == 0, "P1.22 PNG IEND must be empty")
            saw_iend = True
            cursor = end + 4
            break
        else:
            require(bool(kind[0] & 0x20), f"P1.22 PNG contains unsupported critical chunk {kind!r}")
        cursor = end + 4
    require(width is not None and height is not None and palette is not None and saw_iend and idat, "P1.22 PNG missing required chunks")
    require(cursor == len(png), "P1.22 PNG has trailing bytes after IEND")
    decompressor = zlib.decompressobj()
    packed = decompressor.decompress(bytes(idat)) + decompressor.flush()
    require(decompressor.eof and not decompressor.unused_data and not decompressor.unconsumed_tail, "P1.22 PNG compressed stream framing mismatch")
    row_bytes = (width + 1) // 2
    require(len(packed) == height * (row_bytes + 1), "P1.22 PNG decompressed size mismatch")
    output = bytearray(width * height)
    previous = bytearray(row_bytes)
    source = 0
    target = 0
    for _row in range(height):
        filter_type = packed[source]
        source += 1
        filtered = packed[source:source + row_bytes]
        source += row_bytes
        reconstructed = bytearray(row_bytes)
        for x, value in enumerate(filtered):
            left = reconstructed[x - 1] if x else 0
            up = previous[x]
            upper_left = previous[x - 1] if x else 0
            if filter_type == 0:
                predictor = 0
            elif filter_type == 1:
                predictor = left
            elif filter_type == 2:
                predictor = up
            elif filter_type == 3:
                predictor = (left + up) // 2
            elif filter_type == 4:
                predictor = _paeth(left, up, upper_left)
            else:
                raise VisualEvidenceError(f"P1.22 PNG unsupported filter type: {filter_type}")
            reconstructed[x] = (value + predictor) & 0xFF
        for x in range(width):
            packed_pixel = reconstructed[x >> 1]
            palette_index = (packed_pixel >> 4) & 0x0F if not (x & 1) else packed_pixel & 0x0F
            output[target + x] = palette[palette_index]
        target += width
        previous = reconstructed
    return width, height, bytes(output)


def _inspect_png_against_scr(png: bytes, expected_scr: bytes) -> dict[str, int]:
    require(len(expected_scr) == 6912, "P1.22 PNG inspection requires exact SCR bytes")
    width, height, pixels = _decode_fmfconv_png(png)
    require((width, height) == (320, 240), f"P1.22 PNG dimensions must be 320x240, got {width}x{height}")
    mask = bytearray(width * height)
    foreground = 0
    for y in range(192):
        for x in range(256):
            bitmap = expected_scr[_bitmap_address(y, x >> 3) - 0x4000]
            on = (bitmap >> (7 - (x & 7))) & 1
            if on:
                mask[(y + 24) * width + x + 32] = 1
                foreground += 1
    require(foreground > 0, "P1.22 expected PNG atlas contains no foreground pixels")
    background_value = pixels[0]
    first_foreground = next(index for index, value in enumerate(mask) if value)
    foreground_value = pixels[first_foreground]
    require(foreground_value != background_value, "P1.22 PNG foreground is indistinguishable from background")
    for index, actual in enumerate(pixels):
        wanted = foreground_value if mask[index] else background_value
        if actual != wanted:
            x = index % width
            y = index // width
            raise VisualEvidenceError(
                f"P1.22 PNG raster mismatch at ({x},{y}): actual={actual} expected={wanted}"
            )
    return {
        "width": width,
        "height": height,
        "foreground_pixels": foreground,
        "background_value": background_value,
        "foreground_value": foreground_value,
    }


def _patch(kernel: bytes, asset: bytes):
    def apply(ram: bytearray) -> None:
        kernel_offset = phase1.KERNEL_BASE - 0x4000
        ram[kernel_offset:kernel_offset + len(kernel)] = kernel
        font_offset = FONT_SOURCE - 0x4000
        ram[font_offset:font_offset + len(asset)] = asset
    return apply


def _atlas_fixture(labels: dict[str, int]) -> bytes:
    code = bytearray(b"\xF3" + phase1._ld_sp(phase1.USER_STACK))
    code += _call(labels["zx48_memory_init"])
    code += b"\x21" + _word(FONT_SOURCE)
    code += b"\x01" + _word(F4X8_SIZE)
    code += _call(labels["zx48_tty64_install_font"])
    code += _jp_c(FAIL_PC)
    code += _store_byte(labels["tty_current_attr"], ATLAS_ATTRIBUTE)
    for index, value in enumerate(range(0x20, 0x80)):
        row = ATLAS_FIRST_ROW + index // ATLAS_COLUMNS
        col = index % ATLAS_COLUMNS
        code += _store_byte(labels["tty_row"], row)
        code += _store_byte(labels["tty_col"], col)
        code += bytes((0x3E, value)) + _call(labels["zx48_tty64_draw_char"]) + _jp_c(FAIL_PC)

    # Keep the completed atlas visible for many display frames before the debugger
    # PASS breakpoint terminates the emulator. Interrupts remain disabled; display
    # generation still advances with emulated t-states.
    code += b"\x01\x00\x00"  # LD BC,0 -> 65536 DEC iterations.
    loop = len(code)
    code += b"\x0B\x78\xB1"  # DEC BC; LD A,B; OR C
    rel = loop - (len(code) + 2)
    require(-128 <= rel <= 127, "visual wait-loop displacement out of range")
    code += bytes((0x20, rel & 0xFF))
    code += _jp(PASS_PC)
    return bytes(code)


def _check_command(result, name: str) -> None:
    if result.timed_out or result.exit_code != 0:
        raise VisualEvidenceError(
            f"{name} failed: exit={result.exit_code} timed_out={result.timed_out} "
            f"stdout={result.stdout!r} stderr={result.stderr!r}"
        )


def capture_and_inspect(
    root: Path,
    labels: dict[str, int],
    kernel: bytes,
    asset: bytes,
    *,
    run_command: Callable[..., Any],
    require_project_tool: Callable[[Path, str | Path], Path],
) -> tuple[list[Any], list[dict[str, object]]]:
    require(hashlib.sha256(asset).hexdigest() == FONT_SHA256, "P1.22 visual proof did not receive canonical font bytes")
    fuse = require_project_tool(root, "tools/runtime/fuse/bin/fuse")
    fmfconv = require_project_tool(root, "tools/runtime/fuse-utils/bin/fmfconv")
    expected = _expected_scr(asset)
    expected_sha = hashlib.sha256(expected).hexdigest()
    state = read_source_state(root)
    evidence = resolve_evidence_dir(root, state.source_commit)
    evidence.mkdir(parents=True, exist_ok=True)
    destination_png = evidence / PNG_NAME
    destination_scr = evidence / SCR_NAME
    destination_png.unlink(missing_ok=True)
    destination_scr.unlink(missing_ok=True)

    debugger = (
        f"breakpoint 0x{PASS_PC:04x}\n"
        "commands 1\n"
        "exit 0\n"
        "end\n"
        f"breakpoint 0x{FAIL_PC:04x}\n"
        "commands 2\n"
        "exit 1\n"
        "end\n"
        "continue"
    )
    commands: list[Any] = []
    with tempfile.TemporaryDirectory(prefix="zxux-p122-visual-") as temporary:
        temp = Path(temporary)
        sna = temp / "font-atlas.sna"
        movie = temp / "font-atlas.fmf"
        sna.write_bytes(make_sna(_atlas_fixture(labels), patch=_patch(kernel, asset)))
        result = run_command(
            [
                "/usr/bin/env",
                "SDL_VIDEODRIVER=dummy",
                "SDL_AUDIODRIVER=dummy",
                fuse,
                "--machine", "48",
                "--no-sound",
                "--no-confirm-actions",
                "--movie-start", movie,
                "--debugger-command", debugger,
                sna,
            ],
            cwd=root,
            timeout_seconds=20.0,
        )
        commands.append(result)
        _check_command(result, "Fuse P1.22 screenshot capture")
        require(movie.is_file() and movie.stat().st_size > 0, "Fuse did not produce P1.22 FMF capture")

        scr_result = run_command([fmfconv, "-S", "-y", movie, temp / "frame.scr"], cwd=root, timeout_seconds=20.0)
        commands.append(scr_result)
        _check_command(scr_result, "fmfconv SCR extraction")
        png_result = run_command([fmfconv, "-G", "--greyscale", "-y", movie, temp / "frame.png"], cwd=root, timeout_seconds=20.0)
        commands.append(png_result)
        _check_command(png_result, "fmfconv PNG extraction")

        scr_by_frame = {path.stem: path for path in temp.glob("frame*.scr")}
        png_by_frame = {path.stem: path for path in temp.glob("frame*.png")}
        require(scr_by_frame, "no SCR frames extracted from P1.22 capture")
        require(png_by_frame, "no PNG frames extracted from P1.22 capture")
        require(set(scr_by_frame) == set(png_by_frame), "SCR/PNG frame identities differ for one P1.22 FMF capture")
        matches = sorted(frame_id for frame_id, frame in scr_by_frame.items() if frame.read_bytes() == expected)
        require(matches, "automated visual inspection found no captured frame matching the canonical 96-glyph atlas")
        match_frame = matches[-1]
        selected_scr = scr_by_frame[match_frame]
        selected_png = png_by_frame[match_frame]
        require(selected_scr.stat().st_size == 6912, "selected P1.22 SCR screenshot is not exactly 6912 bytes")
        png = selected_png.read_bytes()
        require(png.startswith(b"\x89PNG\r\n\x1a\n") and len(png) > 64, "selected P1.22 PNG screenshot is invalid")
        shutil.copyfile(selected_scr, destination_scr)
        shutil.copyfile(selected_png, destination_png)
        png_inspection = _inspect_png_against_scr(destination_png.read_bytes(), expected)

    scr_sha = hashlib.sha256(destination_scr.read_bytes()).hexdigest()
    png_sha = hashlib.sha256(destination_png.read_bytes()).hexdigest()
    require(scr_sha == expected_sha, "retained P1.22 SCR changed after automated visual inspection")
    assertions = [
        {
            "name": "automated-visual-inspection-canonical-font-atlas-pass",
            "passed": True,
            "artifact": SCR_NAME,
            "sha256": scr_sha,
            "expected_sha256": expected_sha,
            "frame_id": match_frame,
            "glyphs_checked": 96,
        },
        {
            "name": "automated-png-raster-inspection-canonical-font-atlas-pass",
            "passed": True,
            "artifact": PNG_NAME,
            "sha256": png_sha,
            "frame_id": match_frame,
            **png_inspection,
        },
        {
            "name": "font-atlas-png-screenshot-retained",
            "passed": True,
            "artifact": PNG_NAME,
            "sha256": png_sha,
            "frame_id": match_frame,
        },
        {
            "name": "captured-png-corresponds-to-automatically-inspected-scr-frame",
            "passed": True,
            "frame_id": match_frame,
            "frame_count": len(scr_by_frame),
        },
    ]
    return commands, assertions
