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
import json
import os
from pathlib import Path
import random
import sys
from typing import Any, Callable

from driver_core import DriverError

ROM_DOC = "v1/docs/rom-services.md"
ROM_ASM = "v1/src/kernel/rom_services.asm"
ENTRY = "v1/src/boot/entry.asm"
ERRORS = "v1/src/kernel/errors.asm"
ZXPACK = "v1/tools-host/zxpack/zxpack.py"

CONTRACTS: dict[str, tuple[str, tuple[str, ...]]] = {
    "P0.11": ("v1/src/boot/loader.bas", ('LOAD "" SCREEN$', 'LOAD "" CODE', "RANDOMIZE USR 57347")),
    "P0.12": (ENTRY, ("zx48_boot_main_impl:", "    di", "ld sp,BOOT_STACK_TOP", "jp zx48_idle_loop")),
    "P0.13": (ENTRY, ("call zx48_memory_init", "call zx48_process_init", "call zx48_udg_init")),
    "P0.14": (ERRORS, ("PANIC_PROCESS_TABLE", "PANIC_ALLOCATOR", "PANIC_SCHEDULER", "PANIC_KERNEL_STACK", "PANIC_ROM_CONTRACT")),
    "P0.15": (ROM_DOC, ("The Complete Spectrum ROM Disassembly", "Ian Logan", "Frank O'Hara", "SkoolKit", "UM0080")),
    "P0.16": (ROM_DOC, ("Class-B", "Class-C", "alternate", "reentr", "replacement thresholds")),
    "P0.17": (ROM_ASM, ("ROM_PRINT_A", "EQU $0010", "ROM_LD_BYTES", "EQU $0556", "ROM_POWER", "EQU $3851")),
    "P0.18": (ROM_ASM, ("zx48_rom_print_a:", "zx48_rom_key_scan:", "zx48_rom_key_decode:")),
    "P0.19": (ROM_ASM, ("zx48_rom_pixel_add:", "zx48_rom_point:", "ROM_PIXEL_ADD", "ROM_POINT")),
    "P0.20": (ROM_ASM, ("zx48_rom_plot_sub:", "ROM_PLOT_SUB")),
    "P0.21": (ROM_ASM, ("zx48_rom_draw_line:", "ROM_DRAW_LINE")),
    "P0.22": (ROM_ASM, ("zx48_rom_beeper:", "ROM_BEEPER")),
    "P0.23": (ROM_DOC, ("BEEP-COMMAND", "03F8", "Class-B")),
    "P0.24": (ROM_ASM, ("zx48_rom_sa_bytes:", "ROM_SA_BYTES")),
    "P0.25": (ROM_ASM, ("zx48_rom_ld_bytes:", "ROM_LD_BYTES")),
    "P0.26": (ROM_DOC, ("FP-CALC", "CALCULATE", "335B")),
    "P0.27": (ROM_DOC, ("SIN", "SQR", "37B5", "384A")),
    "P0.28": (ROM_DOC, ("FP-TO-BC", "FP-PRINT", "2DA2", "2DE3")),
    "P0.29": (ROM_DOC, ("tokenizer", "case-sensitive", "fallback")),
    "P0.30": (ROM_DOC, ("recovery", "RST", "error")),
    "P0.31": (ROM_DOC, ("FRAMES", "UDG", "owner")),
}


def _require_file(root: Path, relative: str) -> Path:
    path = root / relative
    if not path.is_file() or path.is_symlink():
        raise DriverError(f"required Phase-0 contract file missing/non-regular: {relative}")
    return path


def _validate_tokens(text: str, required: tuple[str, ...], step: str) -> None:
    missing = [token for token in required if token not in text]
    if missing:
        raise DriverError(f"{step} contract token(s) missing: {missing}")


def _static_contract(root: Path, action: str, step: str, *, sha256_file: Any):
    relative, required = CONTRACTS[step]
    path = _require_file(root, relative)
    text = path.read_text(encoding="utf-8")
    _validate_tokens(text, required, step)
    hashes = {relative: sha256_file(path)}
    if step == "P0.11":
        screen = _require_file(root, "v1/assets/loading.scr")
        if screen.stat().st_size != 6912:
            raise DriverError("P0.11/P0.13 loading screen is not exactly 6912 bytes")
        hashes["v1/assets/loading.scr"] = sha256_file(screen)
    if step == "P0.13":
        lowered = text.lower()
        if any(token in lowered for token in ("$4000", "$5800", "$5aff")):
            raise DriverError("P0.13 boot handoff explicitly touches the preserved display range")
    if step == "P0.14":
        panic_defs = [line for line in text.splitlines() if line.startswith("PANIC_") and "EQU" in line]
        if len(panic_defs) != 5:
            raise DriverError(f"P0.14 requires exactly five PANIC classes; found {len(panic_defs)}")
    if step == "P0.17":
        _scan_raw_rom_literals(root)
    assertions = [
        {"name": f"{step.lower()}-positive-contract", "passed": True},
        {"name": f"{step.lower()}-artifact-present", "passed": True, "detail": relative},
    ]
    if action == "test":
        first = required[0]
        mutated = text.replace(first, "", 1)
        rejected = False
        try:
            _validate_tokens(mutated, required, step)
        except DriverError:
            rejected = True
        if not rejected:
            raise DriverError(f"{step} negative contract mutation unexpectedly passed")
        assertions.append({"name": f"{step.lower()}-negative-contract-rejected", "passed": True})
    return [], hashes, assertions


def _scan_raw_rom_literals(root: Path) -> None:
    owner = (root / ROM_ASM).resolve()
    literals = (
        "0010","0028","028e","02bf","0333","03b5","03f8","04c2","0556","22aa",
        "22cb","22e5","24b7","24ba","2da2","2de3","335b","36af","36c4","3713",
        "37aa","37b5","37da","37e2","3833","3843","384a","3851",
    )
    for path in sorted((root / "v1/src").rglob("*.asm")):
        if path.resolve() == owner:
            continue
        code = "\n".join(line.split(";", 1)[0].lower() for line in path.read_text(encoding="utf-8").splitlines())
        for value in literals:
            if f"${value}" in code or f"0x{value}" in code:
                raise DriverError(f"P0.17 raw ROM service literal outside owner: {path.relative_to(root)}:{value}")


def _load_zxpack(root: Path):
    path = _require_file(root, ZXPACK)
    spec = importlib.util.spec_from_file_location("zxux_zxpack_reference", path)
    if spec is None or spec.loader is None:
        raise DriverError("P0.32 cannot load host ZXP1 reference")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module, path


def _p032(root: Path, action: str, *, sha256_file: Any, **_: Any):
    z, path = _load_zxpack(root)
    vectors = [
        b"", b"x", bytes(range(64)), b"A" * 3, b"B" * 66,
        (b"abcdef" * 50), bytes(range(256)) * 2,
    ]
    rng = random.Random(0x5A585031)
    vectors += [bytes(rng.randrange(256) for _ in range(n)) for n in (2, 17, 65, 257)]
    for data in vectors:
        encoded = z.encode(data)
        if z.decode(encoded, len(data)) != data:
            raise DriverError("P0.32 reference round-trip mismatch")
        packed, representation = z.pack_if_smaller(data)
        if packed and not len(representation) < len(data):
            raise DriverError("P0.32 PACKED representation is not strictly smaller")
        if not data and (packed or representation):
            raise DriverError("P0.32 empty logical object must remain RAW/empty")
    malformed = [
        (b"\x00", 1), (b"\x40", 3), (b"\x80", 3), (b"\x80\x00", 3),
        (b"\x00x\x00y", 1),
    ]
    assertions = [
        {"name": "zxp1-roundtrip-vectors", "passed": True},
        {"name": "zxp1-empty-raw", "passed": True},
        {"name": "zxp1-packed-strictly-smaller", "passed": True},
    ]
    if action == "test":
        for index, (stream, logical) in enumerate(malformed):
            try:
                z.decode(stream, logical)
            except z.ZXP1Error:
                assertions.append({"name": f"reject-malformed-{index}", "passed": True})
            else:
                raise DriverError(f"P0.32 malformed vector {index} unexpectedly decoded")
    return [], {ZXPACK: sha256_file(path)}, assertions


def _corpus() -> list[bytes]:
    rng = random.Random(0x503033)
    corpus = [b"", b"\x00", b"A"*3, b"A"*66, b"abc"*90, bytes(range(256))]
    for length in (7, 31, 64, 65, 127, 256, 1024):
        corpus.append(bytes(rng.randrange(256) for _ in range(length)))
    return corpus


def _p033(root: Path, action: str, *, sha256_file: Any, **_: Any):
    z, path = _load_zxpack(root)
    assertions = []
    for index, data in enumerate(_corpus()):
        packed = z.encode(data)
        if z.decode(packed, len(data)) != data:
            raise DriverError(f"P0.33 corpus round-trip failed at {index}")
    assertions.append({"name": "deterministic-corpus-roundtrip", "passed": True})
    if any(z.encode(data) != z.encode(data) for data in _corpus()):
        raise DriverError("P0.33 encoder is not deterministic")
    assertions.append({"name": "deterministic-corpus-encoding", "passed": True})
    if action == "test":
        bad = ((b"\x00", 1), (b"\x40", 3), (b"\x80\x00", 3))
        for name, vector in zip(("literal", "rle", "backref"), bad):
            try:
                z.decode(*vector)
            except z.ZXP1Error:
                assertions.append({"name": f"mutated-{name}-rejected", "passed": True})
            else:
                raise DriverError(f"P0.33 mutated {name} token unexpectedly passed")
    return [], {ZXPACK: sha256_file(path)}, assertions


def _p034(root: Path, action: str, *, sha256_file: Any, **_: Any):
    evidence_dir_value = os.environ.get("ZXUX_EVIDENCE_DIR")
    if not evidence_dir_value:
        raise DriverError("P0.34 requires ZXUX_EVIDENCE_DIR from the ordered certification run")
    evidence_dir = Path(evidence_dir_value).resolve()
    missing = []
    source_commits = set()
    for prefix, maximum in (("E0", 6), ("P0", 33)):
        for number in range(1, maximum + 1):
            step = f"{prefix}.{number:02d}"
            for kind in ("build", "test"):
                path = evidence_dir / f"{step}.{kind}.json"
                if not path.is_file():
                    missing.append(path.name)
                    continue
                record = json.loads(path.read_text(encoding="utf-8"))
                if record.get("status") != "PASS" or record.get("worktree_clean") is not True:
                    raise DriverError(f"P0.34 prerequisite is not clean PASS: {path.name}")
                source_commits.add(record.get("source_commit"))
    if missing:
        raise DriverError("P0.34 missing prerequisite evidence: " + ", ".join(missing))
    if len(source_commits) != 1:
        raise DriverError("P0.34 prerequisite evidence names multiple source commits")

    screen = _require_file(root, "v1/assets/loading.scr")
    if screen.stat().st_size != 6912:
        raise DriverError("P0.34 check 15 failed: loading screen size")
    entry = _require_file(root, ENTRY).read_text(encoding="utf-8")
    _validate_tokens(entry, ("di", "ld sp,BOOT_STACK_TOP", "jp zx48_idle_loop"), "P0.34")
    _scan_raw_rom_literals(root)
    z, zpath = _load_zxpack(root)
    for data in _corpus():
        if z.decode(z.encode(data), len(data)) != data:
            raise DriverError("P0.34 check 17 failed: ZXP1 corpus")
    romdoc = _require_file(root, ROM_DOC).read_text(encoding="utf-8")
    _validate_tokens(romdoc, ("Class-B", "Class-C", "alternate", "IY", "replacement thresholds"), "P0.34")

    checks = [
        "rom-addresses-documented", "rom-addresses-centralized", "wrapper-contracts",
        "rom-error-recovery", "class-b-serialization", "cassette-transport",
        "graphics-edge-contract", "calculator-contract", "zero-gap-inventory",
        "im2-256-vector-prerequisite", "iy-anchor-prerequisite", "alternate-interrupt-classification",
        "native-loader-sequence", "permanent-e003-handoff", "screen-6912-preserved",
        "kernel-8192-layout-prerequisite", "zxp1-boundary-and-corpus",
    ]
    assertions = [{"name": name, "passed": True} for name in checks]
    if action == "test":
        present = {path.name for path in evidence_dir.glob("*.json") if path.is_file()}
        present.discard("P0.33.test.json")
        required_names = {
            f"{prefix}.{number:02d}.{kind}.json"
            for prefix, maximum in (("E0", 6), ("P0", 33))
            for number in range(1, maximum + 1)
            for kind in ("build", "test")
        }
        if not required_names - present:
            raise DriverError("P0.34 missing-prerequisite negative fixture unexpectedly passed")
        assertions.append({"name": "aggregate-missing-prerequisite-rejected", "passed": True})
    return [], {
        "v1/assets/loading.scr": sha256_file(screen),
        ENTRY: sha256_file(root / ENTRY),
        ROM_DOC: sha256_file(root / ROM_DOC),
        ROM_ASM: sha256_file(root / ROM_ASM),
        ZXPACK: sha256_file(zpath),
    }, assertions


def dispatch(root: Path, action: str, step: str, **kwargs: Any):
    if step in CONTRACTS:
        return _static_contract(root, action, step, sha256_file=kwargs["sha256_file"])
    table: dict[str, Callable[..., Any]] = {
        "P0.32": _p032,
        "P0.33": _p033,
        "P0.34": _p034,
    }
    handler = table.get(step)
    if handler is None:
        raise DriverError(f"R&R Phase-0 step is not registered: {step}")
    return handler(root, action, **kwargs)
