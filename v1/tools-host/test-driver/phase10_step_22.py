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


class P1022Error(DriverError):
    pass


def require(ok, msg):
    if not ok:
        raise P1022Error(msg)


def inspector(root: Path):
    path = root / "v1/tools-host/inspect-obj/inspect.py"
    spec = importlib.util.spec_from_file_location("zxux_p1022_inspector", path)
    require(spec is not None and spec.loader is not None, "P10.22 inspector import")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def make_symbol(name: bytes, value: int, section: int, flags: int = 1) -> bytes:
    out = bytearray(20)
    out[:len(name)] = name
    struct.pack_into("<H", out, 16, value)
    out[18] = section
    out[19] = flags
    return bytes(out)


def make_hello(mod, missing: bool = False) -> bytes:
    text = bytearray(b"\xCD\x00\x00\xC9")
    symbols = [
        make_symbol(b"main", 0, 1),
        make_symbol(b"puts", 0, 0),
    ]
    relocs = [struct.pack("<HHBB", 1, 1, 1, 0)]
    if missing:
        symbols.append(make_symbol(b"missing", 0, 0))
    body = bytes(text) + b"".join(symbols) + b"".join(relocs)
    h = bytearray(24)
    h[:4] = b"OBJ1"
    h[4] = 1
    struct.pack_into("<H", h, 6, 24)
    struct.pack_into("<H", h, 8, len(text))
    struct.pack_into("<H", h, 10, 0)
    struct.pack_into("<H", h, 12, len(symbols))
    struct.pack_into("<H", h, 14, len(relocs))
    struct.pack_into("<H", h, 16, 24 + len(text))
    struct.pack_into("<H", h, 18, 24 + len(text) + len(symbols) * 20)
    struct.pack_into("<H", h, 20, mod.crc16_ccitt_false(body))
    struct.pack_into("<H", h, 22, 0)
    struct.pack_into("<H", h, 22, mod.crc16_ccitt_false(bytes(h)))
    return bytes(h) + body


def globals_of(decoded):
    defined = set()
    undefined = set()
    for s in decoded["symbols"]:
        if not s["global"]:
            continue
        if s["section"] == 0:
            undefined.add(s["name"])
        else:
            defined.add(s["name"])
    return defined, undefined


def select_runtime(modules, archive):
    selected = []
    selected_ids = set()

    def unresolved():
        defs = set()
        refs = set()
        for d in modules + [archive[i] for i in selected]:
            a, b = globals_of(d)
            defs |= a
            refs |= b
        return refs - defs

    while True:
        need = unresolved()
        changed = False
        for i in range(1, len(archive)):
            if i in selected_ids:
                continue
            defs, _ = globals_of(archive[i])
            if defs & need:
                selected_ids.add(i)
                selected.append(i)
                changed = True
                need = unresolved()
        if not changed:
            return selected, unresolved()


def dispatch(root, action, step, *, sha256_file, run_command, require_project_tool):
    if step != "P10.22":
        raise DriverError(step)

    crt0_source = (root / "v1/src/libc48/crt0.asm").read_text(encoding="utf-8")
    archive_source = (root / "v1/src/libc48/runtime_archive.asm").read_text(encoding="utf-8")
    assertions = [
        {"name":"crt0-default-entry-contract","passed":"_start calls main, then exit" in crt0_source and "EMIT_P10_CRT0_OBJ1" in crt0_source},
        {"name":"archive-has-crt0-and-runtime-members","passed":"P10_RUNTIME_MEMBER_COUNT EQU 4" in archive_source and all(x in archive_source for x in ("p10_crt0_obj","p10_runtime_write_obj","p10_runtime_puts_obj","p10_runtime_exit_obj"))},
        {"name":"archive-order-frozen","passed":"Member order is frozen here: crt0, write, puts, exit." in archive_source},
        {"name":"archive-indexed-access","passed":"ld_p1022_archive_get:" in archive_source and "cp P10_RUNTIME_MEMBER_COUNT" in archive_source},
    ]
    require(all(a["passed"] for a in assertions), "P10.22 static archive contract failure")

    assembler = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    fixture = build / "p1022-archive.asm"
    fixture.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/libc48/crt0.asm"
    INCLUDE "../src/libc48/runtime_archive.asm"
    ORG $C000
fixture:
    EMIT_P10_CRT0_OBJ1
    EMIT_P10_RUNTIME_ARCHIVE
    EMIT_P10_RUNTIME_ARCHIVE_ROUTINES

p1022_fail:
    ld a,E_FORMAT
    scf
    ret

p1022_check:
    call ld_p1022_archive_get
    ret c
    ld a,b
    or c
    jp z,p1022_fail
    ld a,(hl)
    cp 'O'
    jp nz,p1022_fail
    inc hl
    ld a,(hl)
    cp 'B'
    jp nz,p1022_fail
    inc hl
    ld a,(hl)
    cp 'J'
    jp nz,p1022_fail
    inc hl
    ld a,(hl)
    cp '1'
    jp nz,p1022_fail
    xor a
    ret

p1022_get0:
    xor a
    jp p1022_check
p1022_get1:
    ld a,1
    jp p1022_check
p1022_get2:
    ld a,2
    jp p1022_check
p1022_get3:
    ld a,3
    jp p1022_check
p1022_get_bad:
    ld a,4
    call ld_p1022_archive_get
    ret nc
    cp E_INVAL
    jp nz,p1022_fail
    scf
    ret

fixture_end:
    SAVEBIN "p1022-main.bin",fixture,fixture_end-fixture
""", encoding="utf-8", newline="\n")

    result = run_command([assembler, "--nologo", "--sym=p1022-archive.sym", fixture.name], cwd=build, timeout_seconds=30)
    require(not result.timed_out and result.exit_code == 0, f"P10.22 assemble: {result.stderr or result.stdout}")
    main = (build / "p1022-main.bin").read_bytes()
    names = (
        "p10_crt0_obj","p10_crt0_obj_end",
        "p10_runtime_archive_table","p10_runtime_archive_table_end",
        "p10_runtime_write_obj","p10_runtime_write_obj_end",
        "p10_runtime_puts_obj","p10_runtime_puts_obj_end",
        "p10_runtime_exit_obj","p10_runtime_exit_obj_end",
        "p1022_get0","p1022_get1","p1022_get2","p1022_get3","p1022_get_bad",
    )
    syms = phase3_open_descriptions._symbols(build / "p1022-archive.sym", names)

    def chunk(a, b):
        return main[syms[a]-0xC000:syms[b]-0xC000]

    mod = inspector(root)
    raw_members = [
        chunk("p10_crt0_obj","p10_crt0_obj_end"),
        chunk("p10_runtime_write_obj","p10_runtime_write_obj_end"),
        chunk("p10_runtime_puts_obj","p10_runtime_puts_obj_end"),
        chunk("p10_runtime_exit_obj","p10_runtime_exit_obj_end"),
    ]
    archive = [mod.inspect_bytes(x) for x in raw_members]
    exports = [globals_of(x)[0] for x in archive]
    require("_start" in exports[0], "P10.22 crt0 does not export _start")
    require("write" in exports[1] and "puts" in exports[2] and "exit" in exports[3], "P10.22 runtime export order")

    table = chunk("p10_runtime_archive_table","p10_runtime_archive_table_end")
    require(len(table) == 16, "P10.22 archive table size")
    expected = [
        (syms["p10_crt0_obj"], len(raw_members[0])),
        (syms["p10_runtime_write_obj"], len(raw_members[1])),
        (syms["p10_runtime_puts_obj"], len(raw_members[2])),
        (syms["p10_runtime_exit_obj"], len(raw_members[3])),
    ]
    actual = [struct.unpack_from("<HH", table, i*4) for i in range(4)]
    require(actual == expected, "P10.22 archive table pointer/length order")
    assertions += [
        {"name":"all-built-in-members-valid-obj1","passed":True},
        {"name":"crt0-exports-start-and-imports-main-exit","passed":globals_of(archive[0])[1] == {"main","exit"}},
        {"name":"puts-imports-write-for-transitive-runtime","passed":globals_of(archive[2])[1] == {"write"}},
    ]
    require(all(a["passed"] for a in assertions), "P10.22 decoded archive contract failure")

    hello = mod.inspect_bytes(make_hello(mod))
    selected, unresolved = select_runtime([archive[0], hello], archive)
    require(selected == [2, 3, 1] and unresolved == set(), f"P10.22 hello selection {selected} unresolved {sorted(unresolved)}")
    broken = mod.inspect_bytes(make_hello(mod, missing=True))
    _, unresolved_bad = select_runtime([archive[0], broken], archive)
    require(unresolved_bad == {"missing"}, f"P10.22 missing-member negative {sorted(unresolved_bad)}")
    assertions += [
        {"name":"hello-resolves-start-and-libc","passed":True},
        {"name":"missing-required-member-hard-error-oracle","passed":True},
    ]

    if action == "test":
        def patch(ram):
            ram[0xC000-0x4000:0xC000-0x4000+len(main)] = main
        for name in ("p1022_get0","p1022_get1","p1022_get2","p1022_get3"):
            code = b"\xF3" + phase1._ld_sp(0xBFC0) + phase1._call(syms[name]) + phase1._jp_c(FAIL_PC) + phase1._jp(PASS_PC)
            run_sna(root, code, patch=patch)
        code = b"\xF3" + phase1._ld_sp(0xBFC0) + phase1._call(syms["p1022_get_bad"]) + b"\xD2" + phase1._word(FAIL_PC) + phase1._jp(PASS_PC)
        run_sna(root, code, patch=patch)
        assertions += [
            {"name":"fuse-archive-members-addressable-in-order","passed":True},
            {"name":"fuse-archive-index-boundary-rejected","passed":True},
        ]

    hashes = {
        "v1/src/libc48/crt0.asm": sha256_file(root / "v1/src/libc48/crt0.asm"),
        "v1/src/libc48/runtime_archive.asm": sha256_file(root / "v1/src/libc48/runtime_archive.asm"),
        "v1/tools-host/inspect-obj/inspect.py": sha256_file(root / "v1/tools-host/inspect-obj/inspect.py"),
        "v1/build/p1022-main.bin": sha256_file(build / "p1022-main.bin"),
        "v1/tools-host/test-driver/phase10_step_22.py": sha256_file(root / "v1/tools-host/test-driver/phase10_step_22.py"),
        "v1/dist/certification/P10.21.build.json": sha256_file(root / "v1/dist/certification/P10.21.build.json"),
        "v1/dist/certification/P10.21.test.json": sha256_file(root / "v1/dist/certification/P10.21.test.json"),
    }
    return [result], hashes, assertions
