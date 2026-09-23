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

from pathlib import Path
import phase1
import phase3_open_descriptions
from driver_core import DriverError
from fuse_harness import PASS_PC, FAIL_PC, run_sna


class P1014Error(DriverError):
    pass


def require(ok, msg):
    if not ok:
        raise P1014Error(msg)


REQUIRED = {
    "rlca": {""}, "rrca": {""}, "rla": {""}, "rra": {""},
    "rlc": {"r", "(hl)"}, "rrc": {"r", "(hl)"},
    "rl": {"r", "(hl)", "(ix+d)", "(iy+d)"},
    "rr": {"r", "(hl)"}, "sla": {"r", "(hl)"},
    "sra": {"r", "(hl)"}, "srl": {"r", "(hl)"},
    "bit": {"b,r", "b,(hl)", "b,(ix+d)", "b,(iy+d)"},
    "res": {"b,r", "b,(hl)", "b,(ix+d)", "b,(iy+d)"},
    "set": {"b,r", "b,(hl)", "b,(ix+d)", "b,(iy+d)"},
}


def inventory(path: Path):
    got = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw or raw.startswith("#"):
            continue
        m, form, _ = raw.split("|", 2)
        if m in REQUIRED:
            got.setdefault(m, set()).add(form.strip())
    return got


def dispatch(root, action, step, *, sha256_file, run_command, require_project_tool):
    if step != "P10.14":
        raise DriverError(step)
    source = root / "tools/as.asm"
    text = source.read_text(encoding="utf-8")
    got = inventory(root / "v1/tests/compiler/as-opcode-inventory")
    assertions = [
        {"name": "bit-inventory-family-coverage", "passed": all(got.get(k, set()) == v for k, v in REQUIRED.items())},
        {"name": "native-cb-shift-encoder", "passed": "as_p1014_cb_shift:" in text and "as_p1014_shift_bases:" in text},
        {"name": "native-bit-res-set-encoder", "passed": "as_p1014_bitop:" in text and "as_p1014_index_bitop:" in text},
        {"name": "native-indexed-rl-memory-only", "passed": "as_p1014_index_rl:" in text},
        {"name": "native-displacement-range", "passed": "as_p1014_disp8:" in text},
        {"name": "undocumented-sll-rejection", "passed": "as_p1014_reject_undocumented:" in text and "sll" not in {m for m in got}},
    ]
    require(all(a["passed"] for a in assertions), "P10.14 static encoder coverage failure")

    assembler = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    golden = build / "p1014-golden.asm"
    golden.write_text("""    DEVICE ZXSPECTRUM48
    ORG $C000
fixture:
    rlca
    rrca
    rla
    rra
    rlc b
    rrc c
    rl d
    rr e
    sla h
    sra l
    srl a
    rl (hl)
    bit 0,b
    bit 7,a
    res 3,(hl)
    set 5,c
    bit 2,(ix-128)
    res 1,(iy+127)
    set 6,(ix+0)
    rl (iy-1)
fixture_end:
    SAVEBIN "p1014-golden.bin",fixture,fixture_end-fixture
""", encoding="utf-8", newline="\n")
    g = run_command([assembler, "--nologo", golden.name], cwd=build, timeout_seconds=30)
    require(not g.timed_out and g.exit_code == 0, f"P10.14 golden assemble: {g.stderr or g.stdout}")
    expected = bytes.fromhex(
        "07 0F 17 1F CB 00 CB 09 CB 12 CB 1B CB 24 CB 2D CB 3F CB 16 "
        "CB 40 CB 7F CB 9E CB E9 "
        "DD CB 80 56 FD CB 7F 8E DD CB 00 F6 FD CB FF 16"
    )
    actual = (build / "p1014-golden.bin").read_bytes()
    assertions.append({"name": "sjasmplus-bit-golden", "passed": actual == expected})
    require(actual == expected, "P10.14 SjASMPlus golden mismatch")

    fixture = build / "p1014-native.asm"
    fixture.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../../tools/as.asm"
    ORG $C000
fixture:
    EMIT_P10_AS_BIT_ENCODER
fixture_end:
    SAVEBIN "p1014-native.bin",fixture,fixture_end-fixture
""", encoding="utf-8", newline="\n")
    n = run_command([assembler, "--nologo", "--sym=p1014-native.sym", fixture.name], cwd=build, timeout_seconds=30)
    require(not n.timed_out and n.exit_code == 0, f"P10.14 native assemble: {n.stderr or n.stdout}")

    if action == "test":
        syms = phase3_open_descriptions._symbols(
            build / "p1014-native.sym",
            ("as_p1014_cb_shift", "as_p1014_bitop", "as_p1014_index_bitop",
             "as_p1014_index_rl", "as_p1014_disp8", "as_p1014_reject_undocumented"),
        )
        image = (build / "p1014-native.bin").read_bytes()

        def patch(ram):
            ram[0xC000 - 0x4000:0xC000 - 0x4000 + len(image)] = image

        def hlcheck(addr, setup, want):
            code = (
                b"\xF3" + phase1._ld_sp(0xBFC0) + setup + phase1._call(addr)
                + phase1._jp_c(FAIL_PC) + phase1._ld_de(want)
                + b"\xB7\xED\x52" + phase1._jp_nz(FAIL_PC) + phase1._jp(PASS_PC)
            )
            run_sna(root, code, patch=patch)

        def acheck(addr, setup, want):
            code = (
                b"\xF3" + phase1._ld_sp(0xBFC0) + setup + phase1._call(addr)
                + phase1._jp_c(FAIL_PC) + bytes((0xFE, want))
                + phase1._jp_nz(FAIL_PC) + phase1._jp(PASS_PC)
            )
            run_sna(root, code, patch=patch)

        hlcheck(syms["as_p1014_cb_shift"], bytes((0x3E, 0, 0x06, 0)), 0xCB00)
        hlcheck(syms["as_p1014_cb_shift"], bytes((0x3E, 6, 0x06, 7)), 0xCB3F)
        hlcheck(syms["as_p1014_bitop"], bytes((0x3E, 2, 0x06, 5, 0x0E, 1)), 0xCBE9)
        hlcheck(syms["as_p1014_index_bitop"], bytes((0x16, 1, 0x3E, 1, 0x06, 1)), 0xFD8E)
        hlcheck(syms["as_p1014_index_rl"], bytes((0x16, 0)), 0xDD16)
        acheck(syms["as_p1014_disp8"], phase1._ld_hl(0xFF80), 0x80)
        acheck(syms["as_p1014_disp8"], phase1._ld_hl(0x007F), 0x7F)

        for addr, setup in (
            (syms["as_p1014_cb_shift"], bytes((0x3E, 7, 0x06, 0))),
            (syms["as_p1014_bitop"], bytes((0x3E, 0, 0x06, 8, 0x0E, 0))),
            (syms["as_p1014_index_bitop"], bytes((0x16, 2, 0x3E, 0, 0x06, 0))),
            (syms["as_p1014_disp8"], phase1._ld_hl(0x0080)),
            (syms["as_p1014_disp8"], phase1._ld_hl(0xFF7F)),
            (syms["as_p1014_reject_undocumented"], bytes((0x3E, 0x30))),
        ):
            code = b"\xF3" + phase1._ld_sp(0xBFC0) + setup + phase1._call(addr) + b"\xD2" + phase1._word(FAIL_PC) + phase1._jp(PASS_PC)
            run_sna(root, code, patch=patch)
        assertions += [
            {"name": "fuse-cb-family-vectors", "passed": True},
            {"name": "fuse-indexed-bit-vectors", "passed": True},
            {"name": "fuse-displacement-boundaries", "passed": True},
            {"name": "fuse-invalid-bit-and-sll-rejection", "passed": True},
        ]

    hashes = {
        "tools/as.asm": sha256_file(source),
        "v1/tests/compiler/as-opcode-inventory": sha256_file(root / "v1/tests/compiler/as-opcode-inventory"),
        "v1/build/p1014-golden.bin": sha256_file(build / "p1014-golden.bin"),
        "v1/build/p1014-native.bin": sha256_file(build / "p1014-native.bin"),
        "v1/tools-host/test-driver/phase10_step_14.py": sha256_file(root / "v1/tools-host/test-driver/phase10_step_14.py"),
        "v1/dist/certification/P10.13.build.json": sha256_file(root / "v1/dist/certification/P10.13.build.json"),
        "v1/dist/certification/P10.13.test.json": sha256_file(root / "v1/dist/certification/P10.13.test.json"),
    }
    return [g, n], hashes, assertions
