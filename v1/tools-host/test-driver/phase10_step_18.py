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

import phase1
import phase3_open_descriptions
from driver_core import DriverError
from fuse_harness import PASS_PC, FAIL_PC, run_sna


# P10.18 exact-candidate marker.
class P1018Error(DriverError):
    pass


def require(ok, msg):
    if not ok:
        raise P1018Error(msg)


def load_inspector(root: Path):
    path = root / "v1/tools-host/inspect-obj/inspect.py"
    spec = importlib.util.spec_from_file_location("zxux_p1018_inspector", path)
    require(spec is not None and spec.loader is not None, "P10.18 inspector import")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def symbol(name: bytes, value: int, section: int, flags: int) -> bytes:
    require(1 <= len(name) <= 15, "fixture symbol name")
    out = bytearray(20)
    out[:len(name)] = name
    struct.pack_into("<H", out, 16, value)
    out[18] = section
    out[19] = flags
    return bytes(out)


def make_obj(inspector, text: bytes, bss: int, symbols: bytes, relocs: bytes) -> bytes:
    require(len(symbols) % 20 == 0 and len(relocs) % 6 == 0, "fixture alignment")
    sc, rc = len(symbols) // 20, len(relocs) // 6
    so = 24 + len(text)
    ro = so + len(symbols)
    body = text + symbols + relocs
    h = bytearray(24)
    h[:4] = b"OBJ1"
    h[4] = 1
    struct.pack_into("<H", h, 6, 24)
    struct.pack_into("<H", h, 8, len(text))
    struct.pack_into("<H", h, 10, bss)
    struct.pack_into("<H", h, 12, sc)
    struct.pack_into("<H", h, 14, rc)
    struct.pack_into("<H", h, 16, so)
    struct.pack_into("<H", h, 18, ro)
    struct.pack_into("<H", h, 20, inspector.crc16_ccitt_false(body))
    struct.pack_into("<H", h, 22, 0)
    struct.pack_into("<H", h, 22, inspector.crc16_ccitt_false(bytes(h)))
    return bytes(h) + body


def db_bytes(data: bytes) -> str:
    return ",".join(f"$%02X" % b for b in data)


def rejected(inspector, data: bytes) -> bool:
    try:
        inspector.inspect_bytes(data)
    except inspector.ObjError:
        return True
    return False


def dispatch(root, action, step, *, sha256_file, run_command, require_project_tool):
    if step != "P10.18":
        raise DriverError(step)

    inspector = load_inspector(root)
    inspector.self_test()
    text = b"\x00\x00\xC9"
    sym = symbol(b"main", 0, 1, 1)
    rel = struct.pack("<HHBB", 0, 0, 1, 0)
    golden = make_obj(inspector, text, 4, sym, rel)
    decoded = inspector.inspect_bytes(golden)

    source = (root / "tools/as.asm").read_text(encoding="utf-8")
    assertions = [
        {"name": "native-obj1-writer-present", "passed": "EMIT_P10_AS_OBJ1_WRITER" in source and "as_p1018_write:" in source},
        {"name": "writer-widened-layout-gates", "passed": "as_p1018_mul_small:" in source and "as_p1018_bound:" in source},
        {"name": "writer-relocation-order-gate", "passed": "as_p1018_validate_relocs:" in source and "as_p1018_prev" in source},
        {"name": "writer-crc16-ccitt-false", "passed": "as_p1018_crc16:" in source and "xor $10" in source and "xor $21" in source},
        {"name": "independent-inspector-validates-golden", "passed": decoded["stored_length"] == len(golden) and decoded["relocation_count"] == 1},
    ]
    require(all(a["passed"] for a in assertions), "P10.18 static writer contract failure")

    assembler = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    fixture = build / "p1018-writer.asm"
    fixture.write_text(
        f"""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../../tools/as.asm"
    ORG $C000
fixture:
    EMIT_P10_AS_OBJ1_WRITER

p1018_text: db $00,$00,$C9
p1018_symbol: db {db_bytes(sym)}
p1018_reloc: db $00,$00,$00,$00,$01,$00
p1018_golden: db {db_bytes(golden)}
p1018_obj1: defs {len(golden)},$A5
p1018_obj2: defs {len(golden)},$5A
p1018_badbuf: defs 96,$CC
p1018_badtext: db 0,0,0,0
p1018_badrel: db 0,0,0,0,1,0, 1,0,0,0,1,0

p1018_desc1:
    dw p1018_obj1,p1018_text,3,4,p1018_symbol,1,p1018_reloc,1
p1018_desc2:
    dw p1018_obj2,p1018_text,3,4,p1018_symbol,1,p1018_reloc,1
p1018_bad_desc:
    dw p1018_badbuf,p1018_badtext,4,0,p1018_symbol,1,p1018_badrel,2
p1018_wrap_desc:
    dw p1018_badbuf,p1018_badtext,0,0,p1018_symbol,$4000,p1018_badrel,0

p1018_compare:
    ; Write the same validated assembler result twice.
    ld hl,p1018_desc1
    call as_p1018_write
    ret c
    ld hl,p1018_desc2
    call as_p1018_write
    ret c

    ; Require byte-identical native outputs.
    ld hl,p1018_obj1
    ld de,p1018_obj2
    ld bc,{len(golden)}
p1018_cmp_native:
    ld a,(de)
    cp (hl)
    jr nz,p1018_cmp_fail
    inc hl
    inc de
    dec bc
    ld a,b
    or c
    jr nz,p1018_cmp_native

    ; Require exact match to the independently constructed/inspected OBJ1.
    ld hl,p1018_obj1
    ld de,p1018_golden
    ld bc,{len(golden)}
p1018_cmp_golden:
    ld a,(de)
    cp (hl)
    jr nz,p1018_cmp_fail
    inc hl
    inc de
    dec bc
    ld a,b
    or c
    jr nz,p1018_cmp_golden
    xor a
    ret
p1018_cmp_fail:
    ld a,E_FORMAT
    scf
    ret

fixture_end:
    SAVEBIN "p1018-writer.bin",fixture,fixture_end-fixture
""",
        encoding="utf-8",
        newline="\n",
    )

    cmd = [assembler, "--nologo", "--sym=p1018-writer.sym", fixture.name]
    first = run_command(cmd, cwd=build, timeout_seconds=30)
    require(not first.timed_out and first.exit_code == 0, f"P10.18 first assemble: {first.stderr or first.stdout}")
    image1 = (build / "p1018-writer.bin").read_bytes()
    second = run_command(cmd, cwd=build, timeout_seconds=30)
    require(not second.timed_out and second.exit_code == 0, f"P10.18 second assemble: {second.stderr or second.stdout}")
    image2 = (build / "p1018-writer.bin").read_bytes()
    assertions.append({"name": "identical-source-native-fixture-deterministic", "passed": image1 == image2})
    require(image1 == image2, "P10.18 native fixture nondeterministic")

    syms = phase3_open_descriptions._symbols(
        build / "p1018-writer.sym",
        ("p1018_compare", "as_p1018_write", "p1018_bad_desc", "p1018_wrap_desc"),
    )

    if action == "test":
        def patch(ram):
            ram[0xC000 - 0x4000:0xC000 - 0x4000 + len(image2)] = image2

        code = b"\xF3" + phase1._ld_sp(0xBFC0) + phase1._call(syms["p1018_compare"]) + phase1._jp_c(FAIL_PC) + phase1._jp(PASS_PC)
        run_sna(root, code, patch=patch)

        for desc in ("p1018_bad_desc", "p1018_wrap_desc"):
            code = (
                b"\xF3" + phase1._ld_sp(0xBFC0) + phase1._ld_hl(syms[desc])
                + phase1._call(syms["as_p1018_write"])
                + b"\xD2" + phase1._word(FAIL_PC) + phase1._jp(PASS_PC)
            )
            run_sna(root, code, patch=patch)

        # Independent inspector must fail closed on malformed serialized bytes
        # even when their CRCs are recomputed to match the corruption.
        bad_sym = make_obj(inspector, text, 4, symbol(b"main", 0, 1, 2), rel)
        rel2 = struct.pack("<HHBB", 0, 0, 1, 0) + struct.pack("<HHBB", 1, 0, 1, 0)
        bad_rel = make_obj(inspector, b"\x00\x00\x00", 0, sym, rel2)
        bad_crc = bytearray(golden)
        bad_crc[20] ^= 1
        assertions += [
            {"name": "fuse-two-native-serializations-byte-identical-and-golden", "passed": True},
            {"name": "fuse-overlapping-relocation-rejected-before-emit", "passed": True},
            {"name": "fuse-widened-count-overflow-rejected", "passed": True},
            {"name": "inspector-malformed-symbol-rejected", "passed": rejected(inspector, bad_sym)},
            {"name": "inspector-overlapping-relocation-rejected", "passed": rejected(inspector, bad_rel)},
            {"name": "inspector-crc-mismatch-rejected", "passed": rejected(inspector, bytes(bad_crc))},
        ]
        require(all(a["passed"] for a in assertions), "P10.18 negative/independent inspector failure")

    hashes = {
        "tools/as.asm": sha256_file(root / "tools/as.asm"),
        "v1/include/obj1.inc": sha256_file(root / "v1/include/obj1.inc"),
        "v1/tools-host/inspect-obj/inspect.py": sha256_file(root / "v1/tools-host/inspect-obj/inspect.py"),
        "v1/build/p1018-writer.bin": sha256_file(build / "p1018-writer.bin"),
        "v1/tools-host/test-driver/phase10_step_18.py": sha256_file(root / "v1/tools-host/test-driver/phase10_step_18.py"),
        "v1/dist/certification/P10.17.build.json": sha256_file(root / "v1/dist/certification/P10.17.build.json"),
        "v1/dist/certification/P10.17.test.json": sha256_file(root / "v1/dist/certification/P10.17.test.json"),
    }
    return [first, second], hashes, assertions
