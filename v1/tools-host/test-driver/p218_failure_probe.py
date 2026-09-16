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

import json
import os
from pathlib import Path
import runpy
import sys
import tempfile
from typing import Callable

DRIVER_DIR = Path(__file__).resolve().parent
if str(DRIVER_DIR) not in sys.path:
    sys.path.insert(0, str(DRIVER_DIR))

import driver_core
import fuse_harness
import phase2_kill_never_started as target

FAIL_KIND = 0x6910
FAIL_CHECK = 0x6911
FAIL_ADDRESS = 0x6912
FAIL_EXPECTED = 0x6914
FAIL_ACTUAL = 0x6915
FAIL_RECORD_END = 0x6916

KIND_EXPECT_BYTE = 1
KIND_JUMP_C = 2
KIND_JUMP_NC = 3
KIND_JUMP_NZ = 4

_checks: list[dict[str, int]] = []


def _word(value: int) -> bytes:
    return bytes((value & 0xFF, (value >> 8) & 0xFF))


def _store_a(address: int) -> bytes:
    return b"\x32" + _word(address)


def _set_byte(address: int, value: int) -> bytes:
    return bytes((0x3E, value & 0xFF)) + _store_a(address)


def _set_word(address: int, value: int) -> bytes:
    return b"\x21" + _word(value) + b"\x22" + _word(address)


def _jp(address: int) -> bytes:
    return b"\xC3" + _word(address)


def _write_map() -> None:
    evidence_dir = Path(os.environ.get("ZXUX_EVIDENCE_DIR", "/tmp/zxux-p218-evidence"))
    evidence_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "field_order": ["kind", "check", "address_low", "address_high", "expected", "actual"],
        "record_start": f"0x{FAIL_KIND:04X}",
        "checks": _checks,
    }
    (evidence_dir / "P2.18.failure-probe-map.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _next_check(kind: int, address: int = 0xFFFF, expected: int = 0) -> int:
    check = len(_checks) + 1
    if check > 0xFF:
        raise driver_core.DriverError("P2.18 failure probe exhausted one-byte check identifiers")
    _checks.append(
        {
            "check": check,
            "kind": kind,
            "address": address & 0xFFFF,
            "expected": expected & 0xFF,
        }
    )
    _write_map()
    return check


def _failure_stub(kind: int, check: int, address: int, expected: int) -> bytes:
    return (
        _store_a(FAIL_ACTUAL)
        + _set_byte(FAIL_KIND, kind)
        + _set_byte(FAIL_CHECK, check)
        + _set_word(FAIL_ADDRESS, address)
        + _set_byte(FAIL_EXPECTED, expected)
        + _jp(fuse_harness.FAIL_PC)
    )


def _conditional_failure(skip_opcode: int, kind: int, address: int = 0xFFFF, expected: int = 0) -> bytes:
    check = _next_check(kind, address, expected)
    stub = _failure_stub(kind, check, address, expected)
    if len(stub) > 0x7F:
        raise driver_core.DriverError("P2.18 failure probe branch stub exceeds JR range")
    return bytes((skip_opcode, len(stub))) + stub


def _expect_byte(address: int, value: int) -> bytes:
    check = _next_check(KIND_EXPECT_BYTE, address, value)
    stub = _failure_stub(KIND_EXPECT_BYTE, check, address, value)
    return (
        b"\x3A"
        + _word(address)
        + bytes((0xFE, value & 0xFF, 0x28, len(stub)))
        + stub
    )


def _jp_c(address: int) -> bytes:
    if address != fuse_harness.FAIL_PC:
        return b"\xDA" + _word(address)
    # Original condition fails on carry; skip the diagnostic stub when NC.
    return _conditional_failure(0x30, KIND_JUMP_C)


def _jp_nc(address: int) -> bytes:
    if address != fuse_harness.FAIL_PC:
        return b"\xD2" + _word(address)
    # Original condition fails on no-carry; skip the diagnostic stub when C.
    return _conditional_failure(0x38, KIND_JUMP_NC)


def _jp_nz(address: int) -> bytes:
    if address != fuse_harness.FAIL_PC:
        return b"\xC2" + _word(address)
    # Original condition fails on NZ; skip the diagnostic stub when Z.
    return _conditional_failure(0x28, KIND_JUMP_NZ)


def _diagnostic_run_sna(
    root: Path,
    code: bytes,
    *,
    patch: Callable[[bytearray], None] | None = None,
    timeout: float = 15.0,
):
    fuse = root / "tools/runtime/fuse/bin/fuse"
    if not fuse.is_file():
        raise driver_core.DriverError("project-local FUSE executable missing")

    symbol_path = root / "v1/build/p218-kill-never-started.sym"
    trace = target._symbols(symbol_path, ("zx48_process_kill_publish", "process_table"))
    publish = trace["zx48_process_kill_publish"]
    child = trace["process_table"] + 2 * target.PROC_DESC_SIZE
    image_low = child + target.PROC_IMAGE_BASE
    image_high = image_low + 1

    with tempfile.TemporaryDirectory(prefix="zxux-p218-probe-") as temporary:
        sna = Path(temporary) / "fixture.sna"
        sna.write_bytes(fuse_harness.make_sna(code, patch=patch))
        prints = "\n".join(f"print [0x{address:04x}]" for address in range(FAIL_KIND, FAIL_RECORD_END))
        command = (
            f"breakpoint 0x{publish:04x}\n"
            "commands 1\n"
            "print 0x501\n"
            "print z80:pc\n"
            "print z80:ix\n"
            "print z80:af\n"
            f"print [0x{image_low:04x}]\n"
            f"print [0x{image_high:04x}]\n"
            f"print [0x{publish + 0x10:04x}]\n"
            f"print [0x{publish + 0x11:04x}]\n"
            f"print [0x{publish + 0x12:04x}]\n"
            "continue\n"
            "end\n"
            f"breakpoint write 0x{image_low:04x}\n"
            "commands 2\n"
            "print 0x502\n"
            "print z80:pc\n"
            "print z80:ix\n"
            "print z80:af\n"
            f"print [0x{image_low:04x}]\n"
            "continue\n"
            "end\n"
            f"breakpoint write 0x{image_high:04x}\n"
            "commands 3\n"
            "print 0x503\n"
            "print z80:pc\n"
            "print z80:ix\n"
            "print z80:af\n"
            f"print [0x{image_high:04x}]\n"
            "continue\n"
            "end\n"
            f"breakpoint 0x{fuse_harness.PASS_PC:04x}\n"
            "commands 4\n"
            "exit 0\n"
            "end\n"
            f"breakpoint 0x{fuse_harness.FAIL_PC:04x}\n"
            "commands 5\n"
            "print 0x5ff\n"
            + prints
            + "\nprint z80:af\n"
            "print z80:bc\n"
            "print z80:de\n"
            "print z80:hl\n"
            "print z80:ix\n"
            "print z80:iy\n"
            "print z80:sp\n"
            "exit 1\n"
            "end\n"
            "continue"
        )
        result = driver_core.run_command(
            [
                "/usr/bin/env",
                "SDL_VIDEODRIVER=dummy",
                "SDL_AUDIODRIVER=dummy",
                fuse,
                "--machine",
                "48",
                "--no-sound",
                "--no-confirm-actions",
                "--debugger-command",
                command,
                sna,
            ],
            cwd=root,
            timeout_seconds=timeout,
        )
        if result.timed_out or result.exit_code != 0:
            raise driver_core.DriverError(
                "P2.18 failure probe trapped; trace markers are 0x501 publish, "
                "0x502 image-low write, 0x503 image-high write, and 0x5ff failure; "
                "failure field order is kind/check/address-low/address-high/expected/actual "
                "followed by AF/BC/DE/HL/IX/IY/SP: "
                f"exit={result.exit_code} timed_out={result.timed_out} "
                f"stdout={result.stdout!r} stderr={result.stderr!r}"
            )
        return result


def main() -> None:
    target._expect_byte = _expect_byte
    target._jp_c = _jp_c
    target._jp_nc = _jp_nc
    target._jp_nz = _jp_nz
    target.run_sna = _diagnostic_run_sna
    _write_map()

    sys.argv = [str(DRIVER_DIR / "run.py"), "test", "--step", "P2.18"]
    runpy.run_path(str(DRIVER_DIR / "run.py"), run_name="__main__")


if __name__ == "__main__":
    main()
