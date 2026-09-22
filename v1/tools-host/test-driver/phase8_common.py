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
import importlib.util, struct, sys
from pathlib import Path


def require(value: bool, message: str, exc=RuntimeError) -> None:
    if not value:
        raise exc(message)


def u16(value: int) -> bytes:
    return struct.pack("<H", value)


def word(value: int) -> bytes:
    return bytes((value & 0xFF, (value >> 8) & 0xFF))


def crc16(data: bytes) -> int:
    crc = 0xFFFF
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc


def mex1(image: bytes, stack: int = 256) -> bytes:
    header = bytearray(24)
    header[:4] = b"MEX1"
    header[4] = 1
    header[6:8] = u16(24)
    header[8:10] = u16(len(image))
    header[14:16] = u16(stack)
    header[18:20] = u16(24 + len(image))
    header[20:22] = u16(crc16(image))
    header[22:24] = u16(crc16(bytes(header)))
    return bytes(header) + image


def arg1(args: list[bytes]) -> bytes:
    body = b"".join(item + b"\0" for item in args)
    return b"ARG1" + bytes((len(args), 0)) + word(8 + len(body)) + body


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def assemble_utility(root: Path, build: Path, asm_tool: str, command: str, step_tag: str, macro: str, run_command):
    source = build / f"{step_tag}-{command}-image.asm"
    source.write_text(
        f"""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/utils/{command}.asm"
    ORG $0000
image:
    {macro}
image_end:
    SAVEBIN "{step_tag}-{command}-image.bin",image,image_end-image
""", encoding="utf-8", newline="\n")
    result = run_command([asm_tool, "--nologo", f"--lst={step_tag}-{command}-image.lst", f"--sym={step_tag}-{command}-image.sym", source.name], cwd=build, timeout_seconds=30)
    if result.timed_out or result.exit_code != 0:
        raise RuntimeError(f"{step_tag} {command} image assembly failed: {result.stderr or result.stdout}")
    image = (build / f"{step_tag}-{command}-image.bin").read_bytes()
    mex = build / f"{step_tag}-{command}.mex1"
    mex.write_bytes(mex1(image))
    return result, image, mex


def inspect_mex(root: Path, mex: Path, run_command, require_project_tool):
    inspector = require_project_tool(root, "v1/tools-host/inspect-mex/inspect.py")
    result = run_command([sys.executable, inspector, str(mex), "--base", "0x6000"], cwd=root, timeout_seconds=10)
    if result.timed_out or result.exit_code != 0:
        raise RuntimeError(f"MEX1 inspect failed: {result.stderr or result.stdout}")
    return result


def make_tap(root: Path, build: Path, command: str, step_tag: str, mex: Path):
    maketap = load_module(root / "v1/tools-host/maketap/maketap.py", f"zxux_{step_tag}_{command}_maketap")
    data = maketap.m48o_blocks(maketap.M48OObject(command, maketap.M48O_BIN, maketap.DIR_BIN, mex.read_bytes()))
    tap = build / f"{step_tag}-{command}.tap"
    tap.write_bytes(data)
    return tap
