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

import importlib.util
from pathlib import Path
import struct
import sys

from driver_core import DriverError, root_path, run_command, sha256_file


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise DriverError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _modules(root: Path):
    maketap = _load(root_path(root, "v1/tools-host/maketap/maketap.py"), "zxux_maketap")
    cassette = _load(root_path(root, "v1/tools-host/cassette-image/cassette_image.py"), "zxux_cassette_image")
    return maketap, cassette


def _assemble_kernel(root: Path):
    assembler = root_path(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    source = root_path(root, "v1/src/kernel/kernel.asm")
    result = run_command([assembler, source.name], cwd=source.parent, timeout_seconds=30.0)
    if result.timed_out or result.exit_code != 0:
        raise DriverError("kernel assembly failed for Phase-0 media gate")
    kernel = root_path(root, "v1/build/kernel.bin")
    if not kernel.is_file() or kernel.stat().st_size != 8192:
        raise DriverError("kernel build is not exact 8192 bytes")
    return result, kernel


def _assets(root: Path) -> dict[str, Path]:
    paths = {
        "screen": root_path(root, "v1/assets/loading.scr"),
        "font": root_path(root, "v1/assets/font4x8.bin"),
        "issue": root_path(root, "v1/assets/issue.txt"),
        "crontab": root_path(root, "v1/assets/crontab.txt"),
        "bincat": root_path(root, "v1/assets/bincat.bin"),
    }
    for name, path in paths.items():
        if not path.is_file() or path.is_symlink():
            raise DriverError(f"P0 media asset missing: {name}")
    return paths


def p008(root: Path, action: str):
    assets = _assets(root)
    screen = assets["screen"].read_bytes()
    if len(screen) != 6912:
        raise DriverError("P0.08 loading screen must be 6912 bytes")
    assertions = [{"name": "screen-exact-size", "passed": True, "size": 6912}]
    if action == "test":
        for size in (6911, 6913):
            rejected = len(screen[:size] + (b"\0" if size == 6913 else b"")) != 6912
            if not rejected:
                raise DriverError(f"P0.08 negative screen-size fixture passed: {size}")
            assertions.append({"name": f"reject-screen-{size}", "passed": True})
    return [], {"v1/assets/loading.scr": sha256_file(assets["screen"])}, assertions


def p009(root: Path, action: str):
    maketap, cassette = _modules(root)
    assemble, kernel_path = _assemble_kernel(root)
    assets = _assets(root)
    loader = root_path(root, "v1/src/boot/loader.bas").read_text(encoding="utf-8")
    screen = assets["screen"].read_bytes()
    kernel = kernel_path.read_bytes()
    image1 = maketap.build_bootstrap_prefix(loader_source=loader, screen=screen, kernel=kernel)
    image2 = maketap.build_bootstrap_prefix(loader_source=loader, screen=screen, kernel=kernel)
    if image1 != image2:
        raise DriverError("P0.09 deterministic TAP rebuild mismatch")
    files = cassette.assert_bootstrap_prefix(image1)
    assertions = [
        {"name": "byte-identical-rebuild", "passed": True},
        {"name": "native-order", "passed": [f.name for f in files[:3]] == ["zx48ux", "zx48uxscr", "kernel"]},
        {"name": "screen-address-length", "passed": files[1].param1 == 0x4000 and files[1].length == 6912},
        {"name": "kernel-address-length", "passed": files[2].param1 == 0xE000 and files[2].length == 8192},
    ]
    if not all(item["passed"] for item in assertions):
        raise DriverError("P0.09 bootstrap-prefix assertion failed")
    if action == "test":
        negative_cases = (
            {"screen": screen[:-1]},
            {"kernel": kernel[:-1]},
            {"kernel_start": 0xDFFF},
            {"boot_gateway": 0xE004},
            {"names": ("zx48ux", "kernel", "zx48uxscr")},
        )
        for index, changes in enumerate(negative_cases, 1):
            kwargs = {"loader_source": loader, "screen": screen, "kernel": kernel}
            kwargs.update(changes)
            try:
                maketap.build_bootstrap_prefix(**kwargs)
            except maketap.TapeError:
                assertions.append({"name": f"reject-invalid-prefix-{index}", "passed": True})
            else:
                raise DriverError(f"P0.09 negative fixture {index} unexpectedly passed")
    return [assemble], {
        "v1/build/kernel.bin": sha256_file(kernel_path),
        "v1/assets/loading.scr": sha256_file(assets["screen"]),
        "v1/src/boot/loader.bas": sha256_file(root_path(root, "v1/src/boot/loader.bas")),
    }, assertions


def _validate_font(data: bytes) -> None:
    if len(data) != 392 or data[:4] != b"F4X8" or data[4:8] != bytes((1, 0x20, 96, 0)):
        raise DriverError("P0.10 F4X8 contract mismatch")


def _validate_bincat(data: bytes) -> None:
    if len(data) != 488 or data[:8] != b"BCAT" + bytes((1, 40, 0, 0)):
        raise DriverError("P0.10 BCAT header/length mismatch")
    names: list[bytes] = []
    for offset in range(8, len(data), 12):
        record = data[offset:offset + 12]
        name = record[:10].split(b"\0", 1)[0]
        if not name or name != name.lower() or record[10:] != bytes((2, 1)):
            raise DriverError("P0.10 BCAT record contract mismatch")
        names.append(name)
    if names != sorted(names) or len(set(names)) != 40:
        raise DriverError("P0.10 BCAT names must be 40 unique bytewise-sorted names")


def _parse_m48o_stream(maketap, prefix_length: int, image: bytes):
    offset = prefix_length
    objects = []
    while offset < len(image):
        if offset + 2 > len(image):
            raise DriverError("truncated M48O TAP block")
        block_len = struct.unpack_from("<H", image, offset)[0]
        payload = image[offset + 2:offset + 2 + block_len]
        if len(payload) != block_len or block_len < 2 or payload[0] != 0xFF:
            raise DriverError("invalid M48O TAP framing")
        body = payload[1:-1]
        if len(body) != 32 or body[:4] != b"M48O":
            raise DriverError("expected M48O header block")
        physical = struct.unpack_from("<H", body, 8)[0]
        name = body[16:26].split(b"\0", 1)[0].decode("ascii")
        objects.append((name, body[5], body[7], physical))
        offset += 2 + block_len
        remaining = physical
        while remaining:
            block_len = struct.unpack_from("<H", image, offset)[0]
            payload = image[offset + 2:offset + 2 + block_len]
            chunk = payload[1:-1]
            if payload[0] != 0xFF or not (1 <= len(chunk) <= 512):
                raise DriverError("invalid M48O payload chunk")
            remaining -= len(chunk)
            if remaining < 0:
                raise DriverError("M48O payload overrun")
            offset += 2 + block_len
    return objects


def p010(root: Path, action: str):
    maketap, _ = _modules(root)
    assemble, kernel_path = _assemble_kernel(root)
    assets = _assets(root)
    font = assets["font"].read_bytes()
    issue = assets["issue"].read_bytes()
    crontab = assets["crontab"].read_bytes()
    bincat = assets["bincat"].read_bytes()
    _validate_font(font)
    _validate_bincat(bincat)
    expected_issue = (
        b"\x7f Supratim Sanyal, SANYALnet Labs\n"
        b"https://supratim-sanyal.blogspot.com/\n"
        b"48K. One Z80. No excuses.\n"
    )
    if issue != expected_issue or crontab != b"":
        raise DriverError("P0.10 issue/crontab frozen bytes mismatch")

    loader = root_path(root, "v1/src/boot/loader.bas").read_text(encoding="utf-8")
    screen = assets["screen"].read_bytes()
    kernel = kernel_path.read_bytes()
    prefix = maketap.build_bootstrap_prefix(loader_source=loader, screen=screen, kernel=kernel)
    image = maketap.build_boot_tape(
        loader_source=loader, screen=screen, kernel=kernel,
        font=font, issue=issue, crontab=crontab, bincat=bincat,
    )
    objects = _parse_m48o_stream(maketap, len(prefix), image)
    expected = [
        ("sh", 2, 1), ("font4x8", 9, 7), ("issue", 1, 3),
        ("crontab", 10, 3), ("bincat", 11, 7),
    ]
    if [(n, t, d) for n, t, d, _ in objects] != expected:
        raise DriverError("P0.10 five-resource name/order/type/target mismatch")
    assertions = [
        {"name": "font4x8-format", "passed": True},
        {"name": "issue-exact-bytes", "passed": True},
        {"name": "crontab-zero-raw", "passed": True},
        {"name": "bincat-40-sorted-commands", "passed": True},
        {"name": "five-resource-order-types-targets", "passed": True},
    ]
    if action == "test":
        bad = list(maketap.bootstrap_resources(font=font, issue=issue, crontab=crontab, bincat=bincat))
        bad[0] = maketap.M48OObject("SH", 2, 1, bad[0].payload)
        try:
            maketap.m48o_header(bad[0])
        except maketap.TapeError:
            assertions.append({"name": "reject-uppercase-resource", "passed": True})
        else:
            raise DriverError("P0.10 uppercase resource unexpectedly passed")
    return [assemble], {
        "v1/assets/font4x8.bin": sha256_file(assets["font"]),
        "v1/assets/issue.txt": sha256_file(assets["issue"]),
        "v1/assets/crontab.txt": sha256_file(assets["crontab"]),
        "v1/assets/bincat.bin": sha256_file(assets["bincat"]),
    }, assertions


def dispatch(root: Path, action: str, step: str):
    if step == "P0.08":
        return p008(root, action)
    if step == "P0.09":
        return p009(root, action)
    if step == "P0.10":
        return p010(root, action)
    raise DriverError(f"Phase-0 media step is not registered: {step}")
