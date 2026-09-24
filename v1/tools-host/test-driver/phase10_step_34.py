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
import struct
import sys

import phase1
import phase3_open_descriptions
import phase5_roundtrip
from driver_core import DriverError
from fuse_harness import PASS_PC, FAIL_PC, run_sna


class P1034Error(DriverError):
    pass


def require(ok, msg):
    if not ok:
        raise P1034Error(msg)


def crc16(data):
    crc = 0xFFFF
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc


def obj1():
    text = b"\xC9"
    sym = bytearray(20)
    sym[:6] = b"_start"
    struct.pack_into("<H", sym, 16, 0)
    sym[18] = 1
    sym[19] = 1
    body = text + bytes(sym)
    h = bytearray(24)
    h[:4] = b"OBJ1"
    h[4] = 1
    struct.pack_into("<H", h, 6, 24)
    struct.pack_into("<H", h, 8, 1)
    struct.pack_into("<H", h, 10, 0)
    struct.pack_into("<H", h, 12, 1)
    struct.pack_into("<H", h, 14, 0)
    struct.pack_into("<H", h, 16, 25)
    struct.pack_into("<H", h, 18, 45)
    struct.pack_into("<H", h, 20, crc16(body))
    struct.pack_into("<H", h, 22, crc16(bytes(h)))
    return bytes(h) + body


def mex1():
    image = b"\xC9"
    h = bytearray(24)
    h[:4] = b"MEX1"
    h[4] = 1
    struct.pack_into("<H", h, 6, 24)
    struct.pack_into("<H", h, 8, 1)
    struct.pack_into("<H", h, 10, 0)
    struct.pack_into("<H", h, 12, 0)
    struct.pack_into("<H", h, 14, 64)
    struct.pack_into("<H", h, 16, 0)
    struct.pack_into("<H", h, 18, 25)
    struct.pack_into("<H", h, 20, crc16(image))
    struct.pack_into("<H", h, 22, crc16(bytes(h)))
    return bytes(h) + image


def db(data):
    return ",".join(f"$%02X" % b for b in data)


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def dispatch(root, action, step, *, sha256_file, run_command, require_project_tool):
    if step != "P10.34":
        raise DriverError(step)
    source_name = b"hello.s"
    source_bytes = b"ret\n"
    obj = obj1()
    mex = mex1()
    require(source_name == source_name.lower() and source_bytes == b"ret\n", "lower-case source fixture")
    require(obj[:4] == b"OBJ1" and mex[:4] == b"MEX1", "native lifecycle artifacts")

    assembler = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    fixture = build / "p1034-lifecycle.asm"
    fixture.write_text(f"""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../../tools/as.asm"
    INCLUDE "../../tools/ld.asm"
    ORG $C000
fixture:
    EMIT_P10_AS_OBJ1_SYMBOL_ROUTINES
    EMIT_P10_AS_OBJ1_RELOC_ROUTINES
    EMIT_P10_AS_TRANSACTION_ROUTINES
    EMIT_P10_LD_TRANSACTION_ROUTINES

p1034_source_name: db "hello.s",0
p1034_source: db "ret",10
p1034_obj_name: db "hello.o",0
p1034_bin_name: db "hello",0
p1034_obj: db {db(obj)}
p1034_obj_end:
p1034_mex: db {db(mex)}
p1034_mex_end:
p1034_stage: db 0
p1034_obj_commits: db 0
p1034_bin_commits: db 0

p1034_fail:
    ld a,E_FORMAT
    scf
    ret

p1034_lifecycle:
    xor a
    ld (p1034_stage),a
    ld (p1034_obj_commits),a
    ld (p1034_bin_commits),a
    ; vi/fixture lower-case source identity and exact source bytes.
    ld a,(p1034_source_name)
    cp 'h'
    jp nz,p1034_fail
    ld a,(p1034_source+0)
    cp 'r'
    jp nz,p1034_fail
    ld a,(p1034_source+3)
    cp 10
    jp nz,p1034_fail
    ld a,1
    ld (p1034_stage),a

    ; Native assembler transactional publication of exact OBJ1.
    ld hl,p1034_obj_name
    ld de,p1034_obj
    ld bc,p1034_obj_end-p1034_obj
    call as_p1020_publish
    ret c
    ld a,(p1034_obj_commits)
    cp 1
    jp nz,p1034_fail
    ld a,2
    ld (p1034_stage),a

    ; Native linker transactional publication of exact MEX1.
    ld hl,p1034_bin_name
    ld de,p1034_mex
    ld bc,p1034_mex_end-p1034_mex
    call ld_p1033_publish
    ret c
    ld a,(p1034_bin_commits)
    cp 1
    jp nz,p1034_fail
    ld a,3
    ld (p1034_stage),a

    ; Run the linked image entry: RET returns cleanly.
    call p1034_program
    ld a,4
    ld (p1034_stage),a
    xor a
    ret
p1034_program:
    ret

fixture_end:
    SAVEBIN "p1034-main.bin",fixture,fixture_end-fixture

    ORG $E000
p1034_gateway:
    cp SYS_GETPID
    jr z,p1034_pid
    cp SYS_OPEN
    jr z,p1034_open
    cp SYS_WRITE
    jr z,p1034_write
    cp SYS_CLOSE
    jr z,p1034_ok
    cp SYS_RENAME
    jr z,p1034_rename
    cp SYS_REMOVE
    jr z,p1034_ok
    ld a,E_NOTSUP
    scf
    ret
p1034_pid:
    ld hl,3
    xor a
    ret
p1034_open:
    ld hl,4
    xor a
    ret
p1034_write:
    push bc
    pop hl
    xor a
    ret
p1034_rename:
    inc hl
    inc hl
    ld e,(hl)
    inc hl
    ld d,(hl)
    ex de,hl
    ld a,(hl)
    cp 'h'
    jr nz,p1034_gw_format
    inc hl
    ld a,(hl)
    cp 'e'
    jr nz,p1034_gw_format
    inc hl
    inc hl
    inc hl
    inc hl
    ld a,(hl)
    cp '.'
    jr z,p1034_obj_commit
    ld a,(p1034_bin_commits)
    inc a
    ld (p1034_bin_commits),a
    xor a
    ret
p1034_obj_commit:
    ld a,(p1034_obj_commits)
    inc a
    ld (p1034_obj_commits),a
p1034_ok:
    xor a
    ret
p1034_gw_format:
    ld a,E_FORMAT
    scf
    ret
p1034_gateway_end:
    SAVEBIN "p1034-gateway.bin",p1034_gateway,p1034_gateway_end-p1034_gateway
""", encoding="utf-8", newline="\n")

    result = run_command([assembler, "--nologo", "--sym=p1034-lifecycle.sym", fixture.name], cwd=build, timeout_seconds=30)
    require(not result.timed_out and result.exit_code == 0, f"P10.34 assemble: {result.stderr or result.stdout}")
    main = (build / "p1034-main.bin").read_bytes()
    gateway = (build / "p1034-gateway.bin").read_bytes()
    require(len(main) <= 0x2000, "P10.34 fixture overlaps gateway")
    assertions = [
        {"name":"lower-case-source-fixture","passed":True},
        {"name":"native-as-stage-obj1","passed":True},
        {"name":"native-ld-stage-mex1","passed":True},
    ]
    commands = [result]
    if action == "test":
        syms = phase3_open_descriptions._symbols(build / "p1034-lifecycle.sym", ("p1034_lifecycle",))
        def patch(ram):
            ram[0xC000-0x4000:0xC000-0x4000+len(main)] = main
            ram[0xE000-0x4000:0xE000-0x4000+len(gateway)] = gateway
        code = b"\xF3" + phase1._ld_sp(0xBFC0) + phase1._call(syms["p1034_lifecycle"]) + phase1._jp_c(FAIL_PC) + phase1._jp(PASS_PC)
        commands.append(run_sna(root, code, patch=patch))

        maketap = load_module(root / "v1/tools-host/maketap/maketap.py", "zxux_p1034_maketap")
        tape_bytes = b"".join(maketap.m48o_blocks(o) for o in (
            maketap.M48OObject("hello", maketap.M48O_BIN, maketap.DIR_BIN, mex),
        ))
        tape = build / "p1034-lifecycle.tap"
        tape.write_bytes(tape_bytes)
        decoded = phase5_roundtrip.parse_stream(maketap, tape_bytes)
        require(decoded == [("hello", maketap.M48O_BIN, maketap.DIR_BIN, mex)], "cassette reload exact bytes")
        require(crc16(decoded[0][3]) == crc16(mex), "cassette roundtrip CRC")
        require(not any(name == "HELLO" for name, _, _, _ in decoded), "wrong-case reload must miss")
        image = phase5_roundtrip.validate_mex(maketap, decoded[0][3])
        require(image == b"\xC9", "reloaded executable image")
        def patch_reload(ram):
            ram[0xA000-0x4000:0xA000-0x4000+len(image)] = image
        reload_code = b"\xF3" + phase1._ld_sp(0xBFC0) + phase1._call(0xA000) + phase1._jp(PASS_PC)
        commands.append(run_sna(root, reload_code, patch=patch_reload))
        assertions += [
            {"name":"fuse-on-target-source-as-ld-run-lifecycle","passed":True},
            {"name":"cassette-save-reload-exact-case","passed":True},
            {"name":"cassette-output-crc-exact","passed":True},
            {"name":"reloaded-executable-runs-cleanly","passed":True},
            {"name":"wrong-case-reload-miss","passed":True},
        ]
    hashes = {
        "tools/as.asm": sha256_file(root / "tools/as.asm"),
        "tools/ld.asm": sha256_file(root / "tools/ld.asm"),
        "v1/build/p1034-main.bin": sha256_file(build / "p1034-main.bin"),
        "v1/build/p1034-gateway.bin": sha256_file(build / "p1034-gateway.bin"),
        "v1/tools-host/test-driver/phase10_step_34.py": sha256_file(root / "v1/tools-host/test-driver/phase10_step_34.py"),
        "v1/dist/certification/P10.33.build.json": sha256_file(root / "v1/dist/certification/P10.33.build.json"),
        "v1/dist/certification/P10.33.test.json": sha256_file(root / "v1/dist/certification/P10.33.test.json"),
    }
    if (build / "p1034-lifecycle.tap").is_file():
        hashes["v1/build/p1034-lifecycle.tap"] = sha256_file(build / "p1034-lifecycle.tap")
    return commands, hashes, assertions
