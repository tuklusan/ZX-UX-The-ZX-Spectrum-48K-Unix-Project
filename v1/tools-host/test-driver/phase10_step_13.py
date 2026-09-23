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


class P1013Error(DriverError):
    pass


def require(ok, msg):
    if not ok:
        raise P1013Error(msg)


REQUIRED = {
    "jp": {"nn", "cc,nn", "(hl)", "(ix)", "(iy)"},
    "jr": {"rel", "cc,rel"},
    "call": {"nn", "cc,nn"},
    "ret": {"", "cc"},
    "rst": {"vec"},
    "djnz": {"rel"},
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
    if step != "P10.13":
        raise DriverError(step)
    source = root / "tools/as.asm"
    text = source.read_text(encoding="utf-8")
    got = inventory(root / "v1/tests/compiler/as-opcode-inventory")
    assertions = [
        {"name": "control-inventory-family-coverage", "passed": all(got.get(k, set()) == v for k, v in REQUIRED.items())},
        {"name": "native-absolute-control-encoder", "passed": "as_p1013_abs:" in text and "as_p1013_abs16_reloc:" in text},
        {"name": "native-relative-control-encoder", "passed": "as_p1013_jr:" in text and "as_p1013_rel8:" in text},
        {"name": "external-relative-rejection", "passed": "as_p1013_require_local:" in text},
        {"name": "native-ret-rst-djnz", "passed": all(x in text for x in ("as_p1013_ret:", "as_p1013_rst:", "as_p1013_djnz:"))},
        {"name": "native-jp-indirect", "passed": "as_p1013_jp_indirect:" in text},
    ]
    require(all(a["passed"] for a in assertions), "P10.13 static encoder coverage failure")

    assembler = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)

    golden = build / "p1013-golden.asm"
    golden.write_text("""    DEVICE ZXSPECTRUM48
    ORG $C000
fixture:
    jp $1234
    jp nz,$1234
    jp z,$1234
    jp nc,$1234
    jp c,$1234
    jp po,$1234
    jp pe,$1234
    jp p,$1234
    jp m,$1234
    call $1234
    call nz,$1234
    call z,$1234
    call nc,$1234
    call c,$1234
    call po,$1234
    call pe,$1234
    call p,$1234
    call m,$1234
    ret
    ret nz
    ret z
    ret nc
    ret c
    ret po
    ret pe
    ret p
    ret m
    jp (hl)
    jp (ix)
    jp (iy)
    jr $
    jr nz,$
    jr z,$
    jr nc,$
    jr c,$
    djnz $
    rst 0
    rst 8
    rst $38
fixture_end:
    SAVEBIN "p1013-golden.bin",fixture,fixture_end-fixture
""", encoding="utf-8", newline="\n")
    g = run_command([assembler, "--nologo", golden.name], cwd=build, timeout_seconds=30)
    require(not g.timed_out and g.exit_code == 0, f"P10.13 golden assemble: {g.stderr or g.stdout}")
    expected = bytes.fromhex(
        "C3 34 12 C2 34 12 CA 34 12 D2 34 12 DA 34 12 "
        "E2 34 12 EA 34 12 F2 34 12 FA 34 12 "
        "CD 34 12 C4 34 12 CC 34 12 D4 34 12 DC 34 12 "
        "E4 34 12 EC 34 12 F4 34 12 FC 34 12 "
        "C9 C0 C8 D0 D8 E0 E8 F0 F8 "
        "E9 DD E9 FD E9 "
        "18 FE 20 FE 28 FE 30 FE 38 FE 10 FE C7 CF FF"
    )
    actual = (build / "p1013-golden.bin").read_bytes()
    assertions.append({"name": "sjasmplus-control-golden", "passed": actual == expected})
    require(actual == expected, "P10.13 SjASMPlus golden mismatch")

    fixture = build / "p1013-native.asm"
    fixture.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../../tools/as.asm"
    ORG $C000
fixture:
    EMIT_P10_AS_CONTROL_ENCODER
relocbuf: defs 6,0
fixture_end:
    SAVEBIN "p1013-native.bin",fixture,fixture_end-fixture
""", encoding="utf-8", newline="\n")
    n = run_command([assembler, "--nologo", "--sym=p1013-native.sym", fixture.name], cwd=build, timeout_seconds=30)
    require(not n.timed_out and n.exit_code == 0, f"P10.13 native assemble: {n.stderr or n.stdout}")

    if action == "test":
        syms = phase3_open_descriptions._symbols(
            build / "p1013-native.sym",
            (
                "as_p1013_abs", "as_p1013_ret", "as_p1013_jr", "as_p1013_rel8",
                "as_p1013_require_local", "as_p1013_rst", "as_p1013_jp_indirect",
                "as_p1013_djnz", "as_p1013_abs16_reloc", "relocbuf",
            ),
        )
        image = (build / "p1013-native.bin").read_bytes()

        def patch(ram):
            ram[0xC000 - 0x4000:0xC000 - 0x4000 + len(image)] = image

        def acheck(addr, setup, want):
            code = (
                b"\xF3" + phase1._ld_sp(0xBFC0) + setup + phase1._call(addr)
                + phase1._jp_c(FAIL_PC) + bytes((0xFE, want))
                + phase1._jp_nz(FAIL_PC) + phase1._jp(PASS_PC)
            )
            run_sna(root, code, patch=patch)

        acheck(syms["as_p1013_abs"], bytes((0x3E, 0, 0x06, 0xFF)), 0xC3)
        acheck(syms["as_p1013_abs"], bytes((0x3E, 1, 0x06, 7)), 0xFC)
        acheck(syms["as_p1013_ret"], bytes((0x06, 3)), 0xD8)
        acheck(syms["as_p1013_jr"], bytes((0x06, 3)), 0x38)
        acheck(syms["as_p1013_djnz"], b"", 0x10)
        acheck(syms["as_p1013_rst"], bytes((0x3E, 0x38)), 0xFF)
        acheck(syms["as_p1013_rel8"], phase1._ld_hl(0x207F) + phase1._ld_de(0x2000), 0x7F)
        acheck(syms["as_p1013_rel8"], phase1._ld_hl(0x1F80) + phase1._ld_de(0x2000), 0x80)

        for addr, setup in (
            (syms["as_p1013_abs"], bytes((0x3E, 0, 0x06, 8))),
            (syms["as_p1013_jr"], bytes((0x06, 4))),
            (syms["as_p1013_rst"], bytes((0x3E, 7))),
            (syms["as_p1013_rel8"], phase1._ld_hl(0x2080) + phase1._ld_de(0x2000)),
            (syms["as_p1013_rel8"], phase1._ld_hl(0x1F7F) + phase1._ld_de(0x2000)),
            (syms["as_p1013_require_local"], bytes((0x3E, 1))),
        ):
            code = b"\xF3" + phase1._ld_sp(0xBFC0) + setup + phase1._call(addr) + b"\xD2" + phase1._word(FAIL_PC) + phase1._jp(PASS_PC)
            run_sna(root, code, patch=patch)

        for sel, want in ((0, 0x00E9), (1, 0xDDE9), (2, 0xFDE9)):
            code = (
                b"\xF3" + phase1._ld_sp(0xBFC0) + bytes((0x3E, sel))
                + phase1._call(syms["as_p1013_jp_indirect"]) + phase1._jp_c(FAIL_PC)
                + phase1._ld_de(want) + b"\xB7\xED\x52"
                + phase1._jp_nz(FAIL_PC) + phase1._jp(PASS_PC)
            )
            run_sna(root, code, patch=patch)

        rb = syms["relocbuf"]
        code = (
            b"\xF3" + phase1._ld_sp(0xBFC0) + b"\x01" + phase1._word(rb)
            + phase1._ld_hl(0x1234) + phase1._ld_de(0x0002)
            + phase1._call(syms["as_p1013_abs16_reloc"])
            + phase1._ld_hl(rb)
            + bytes((0x7E, 0xFE, 0x34)) + phase1._jp_nz(FAIL_PC)
            + bytes((0x23, 0x7E, 0xFE, 0x12)) + phase1._jp_nz(FAIL_PC)
            + bytes((0x23, 0x7E, 0xFE, 0x02)) + phase1._jp_nz(FAIL_PC)
            + bytes((0x23, 0x7E, 0xB7)) + phase1._jp_nz(FAIL_PC)
            + bytes((0x23, 0x7E, 0xFE, 0x01)) + phase1._jp_nz(FAIL_PC)
            + bytes((0x23, 0x7E, 0xB7)) + phase1._jp_nz(FAIL_PC)
            + phase1._jp(PASS_PC)
        )
        run_sna(root, code, patch=patch)
        assertions += [
            {"name": "fuse-control-condition-vectors", "passed": True},
            {"name": "fuse-relative-boundaries", "passed": True},
            {"name": "fuse-relative-overflow-and-external-rejection", "passed": True},
            {"name": "fuse-jp-indirect-prefixes", "passed": True},
            {"name": "fuse-absolute-relocation-record", "passed": True},
        ]

    hashes = {
        "tools/as.asm": sha256_file(source),
        "v1/tests/compiler/as-opcode-inventory": sha256_file(root / "v1/tests/compiler/as-opcode-inventory"),
        "v1/build/p1013-golden.bin": sha256_file(build / "p1013-golden.bin"),
        "v1/build/p1013-native.bin": sha256_file(build / "p1013-native.bin"),
        "v1/tools-host/test-driver/phase10_step_13.py": sha256_file(root / "v1/tools-host/test-driver/phase10_step_13.py"),
        "v1/dist/certification/P10.12.build.json": sha256_file(root / "v1/dist/certification/P10.12.build.json"),
        "v1/dist/certification/P10.12.test.json": sha256_file(root / "v1/dist/certification/P10.12.test.json"),
    }
    return [g, n], hashes, assertions
