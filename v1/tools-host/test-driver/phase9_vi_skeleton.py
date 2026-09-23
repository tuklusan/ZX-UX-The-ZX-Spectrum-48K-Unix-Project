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

import phase1
import phase3_open_descriptions
from driver_core import DriverError
from fuse_harness import FAIL_PC, PASS_PC, run_sna
from phase8_common import inspect_mex, make_tap, mex1, word

BASE = 0xC000
GATE = 0xE000
MODE = 0xA300
CURSOR = 0xA301
STATUS = 0xA302
FAIL_REQ = 0xA303
FAIL_ERR = 0xA304


class P901Error(DriverError):
    pass


def require(value, message):
    if not value:
        raise P901Error(message)


def expect(address, value):
    return b"\x3A" + word(address) + bytes((0xFE, value & 0xFF)) + phase1._jp_nz(FAIL_PC)


def patch(image, gateway, mode, cursor, fail_req=0, fail_err=0):
    def apply(ram):
        ram[BASE - 0x4000 : BASE - 0x4000 + len(image)] = image
        ram[GATE - 0x4000 : GATE - 0x4000 + len(gateway)] = gateway
        ram[MODE - 0x4000] = mode
        ram[CURSOR - 0x4000] = cursor
        ram[STATUS - 0x4000] = 0xFF
        ram[FAIL_REQ - 0x4000] = fail_req
        ram[FAIL_ERR - 0x4000] = fail_err

    return apply


def dispatch(root, action, step, *, sha256_file, run_command, require_project_tool):
    if step != "P9.01":
        raise DriverError(step)

    source = root / "tools/vi.asm"
    source_text = source.read_text(encoding="utf-8")
    plan = (root / "docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md").read_text(encoding="utf-8")

    assertions = [
        {
            "name": "canonical-p901-present",
            "passed": "## P9.01 - vi MEX1 skeleton and tty mode save/restore" in plan,
        },
        {
            "name": "tty64-and-block-contract",
            "passed": "VI_MODE_64              EQU 64" in source_text
            and "VI_CURSOR_BLOCK         EQU 2" in source_text,
        },
        {
            "name": "shared-restoration-path",
            "passed": "vi_normal_exit:" in source_text
            and "vi_unwind_error:" in source_text
            and source_text.count("call vi_restore_terminal") >= 2,
        },
        {
            "name": "restore-exact-saved-values",
            "passed": "ld hl,vi_saved_mode" in source_text
            and "ld hl,vi_saved_cursor" in source_text,
        },
    ]
    require(all(item["passed"] for item in assertions), "P9.01 static failure")

    assembler = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)

    fixture = build / "p901-vi.asm"
    fixture.write_text(
        """    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../../tools/vi.asm"
    ORG $C000
fixture:
    EMIT_P901_VI_ROUTINES
fixture_end:
    SAVEBIN "p901-vi.bin",fixture,fixture_end-fixture
""",
        encoding="utf-8",
        newline="\n",
    )
    fixture_result = run_command(
        [assembler, "--nologo", "--lst=p901-vi.lst", "--sym=p901-vi.sym", fixture.name],
        cwd=build,
        timeout_seconds=30,
    )
    require(
        not fixture_result.timed_out and fixture_result.exit_code == 0,
        f"P9.01 assemble: {fixture_result.stderr or fixture_result.stdout}",
    )
    image = (build / "p901-vi.bin").read_bytes()

    gateway_source = build / "p901-gateway.asm"
    gateway_source.write_text(
        """    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    ORG $E000
gate:
    cp SYS_OPEN
    jp z,g_open
    cp SYS_CLOSE
    jp z,g_close
    cp SYS_IOCTL
    jp z,g_ioctl
    cp SYS_EXIT
    jp z,g_exit
    ld a,E_NOTSUP
    scf
    ret
g_open:
    ld hl,3
    xor a
    ret
g_close:
    xor a
    ret
g_ioctl:
    ld a,(hl)
    cp 3
    jr nz,g_bad
    inc hl
    ld a,(hl)
    inc hl
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld b,a
    ld a,($A303)
    cp b
    jr nz,g_dispatch
    ld a,($A304)
    scf
    ret
g_dispatch:
    ld a,b
    cp 1
    jr z,g_get_mode
    cp 2
    jr z,g_set_mode
    cp 4
    jr z,g_set_cursor
    cp 5
    jr z,g_get_cursor
    jr g_bad
g_get_mode:
    ld a,($A300)
    ld (de),a
    xor a
    ret
g_set_mode:
    ld a,(de)
    ld ($A300),a
    xor a
    ret
g_get_cursor:
    ld a,($A301)
    ld (de),a
    xor a
    ret
g_set_cursor:
    ld a,(de)
    ld ($A301),a
    xor a
    ret
g_exit:
    ld a,l
    ld ($A302),a
    xor a
    ret
g_bad:
    ld a,E_INVAL
    scf
    ret
gate_end:
    SAVEBIN "p901-gateway.bin",gate,gate_end-gate
""",
        encoding="utf-8",
        newline="\n",
    )
    gateway_result = run_command(
        [assembler, "--nologo", "--lst=p901-gateway.lst", "--sym=p901-gateway.sym", gateway_source.name],
        cwd=build,
        timeout_seconds=30,
    )
    require(
        not gateway_result.timed_out and gateway_result.exit_code == 0,
        f"P9.01 gateway: {gateway_result.stderr or gateway_result.stdout}",
    )

    mex_path = build / "p901-vi.mex1"
    mex_path.write_bytes(mex1(image))
    try:
        inspect_result = inspect_mex(root, mex_path, run_command, require_project_tool)
        tap_path = make_tap(root, build, "vi", "p901", mex_path)
    except RuntimeError as exc:
        raise P901Error(str(exc)) from exc

    if action == "test":
        symbols = phase3_open_descriptions._symbols(
            build / "p901-vi.sym", ("vi_entry", "E_IO", "E_INTR")
        )
        gateway = (build / "p901-gateway.bin").read_bytes()
        cases = [
            (32, 1, 0, 0, 0),
            (32, 1, 4, symbols["E_IO"] & 0xFF, symbols["E_IO"] & 0xFF),
            (64, 0, 2, symbols["E_INTR"] & 0xFF, symbols["E_INTR"] & 0xFF),
        ]
        for mode, cursor, fail_req, fail_err, status in cases:
            code = bytearray(
                b"\xF3"
                + phase1._ld_sp(0xBFC0)
                + phase1._ld_hl(0)
                + b"\x01\x00\x00"
                + phase1._call(symbols["vi_entry"])
            )
            code += expect(MODE, mode)
            code += expect(CURSOR, cursor)
            code += expect(STATUS, status)
            code += phase1._jp(PASS_PC)
            run_sna(
                root,
                bytes(code),
                patch=patch(image, gateway, mode, cursor, fail_req, fail_err),
            )
        assertions += [
            {"name": "fuse-normal-exit-restore", "passed": True},
            {"name": "fuse-forced-error-restore", "passed": True},
            {"name": "fuse-cancellation-restore", "passed": True},
        ]

    hashes = {
        "tools/vi.asm": sha256_file(source),
        "v1/build/p901-vi.mex1": sha256_file(mex_path),
        "v1/build/p901-vi.tap": sha256_file(tap_path),
        "v1/tools-host/test-driver/phase9_vi_skeleton.py": sha256_file(
            root / "v1/tools-host/test-driver/phase9_vi_skeleton.py"
        ),
        "v1/tools-host/test-driver/run.py": sha256_file(
            root / "v1/tools-host/test-driver/run.py"
        ),
        "v1/dist/certification/P8.40.test.json": sha256_file(
            root / "v1/dist/certification/P8.40.test.json"
        ),
    }
    return [fixture_result, gateway_result, inspect_result], hashes, assertions
