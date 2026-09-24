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


# P10.20 exact-candidate marker.
class P1020Error(DriverError):
    pass


def require(ok, msg):
    if not ok:
        raise P1020Error(msg)


def load_inspector(root: Path):
    path = root / "v1/tools-host/inspect-obj/inspect.py"
    spec = importlib.util.spec_from_file_location("zxux_p1020_inspector", path)
    require(spec is not None and spec.loader is not None, "P10.20 inspector import")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def symbol(name: bytes, value: int, section: int, flags: int) -> bytes:
    out = bytearray(20)
    out[:len(name)] = name
    struct.pack_into("<H", out, 16, value)
    out[18] = section
    out[19] = flags
    return bytes(out)


def make_obj(inspector) -> bytes:
    text = b"\x00\x00\xC9"
    sym = symbol(b"main", 0, 1, 1)
    rel = struct.pack("<HHBB", 0, 0, 1, 0)
    body = text + sym + rel
    h = bytearray(24)
    h[:4] = b"OBJ1"
    h[4] = 1
    struct.pack_into("<H", h, 6, 24)
    struct.pack_into("<H", h, 8, len(text))
    struct.pack_into("<H", h, 10, 4)
    struct.pack_into("<H", h, 12, 1)
    struct.pack_into("<H", h, 14, 1)
    struct.pack_into("<H", h, 16, 24 + len(text))
    struct.pack_into("<H", h, 18, 24 + len(text) + len(sym))
    struct.pack_into("<H", h, 20, inspector.crc16_ccitt_false(body))
    struct.pack_into("<H", h, 22, 0)
    struct.pack_into("<H", h, 22, inspector.crc16_ccitt_false(bytes(h)))
    return bytes(h) + body


def db(data: bytes) -> str:
    return ",".join(f"$%02X" % b for b in data)


def dispatch(root, action, step, *, sha256_file, run_command, require_project_tool):
    if step != "P10.20":
        raise DriverError(step)

    inspector = load_inspector(root)
    candidate = make_obj(inspector)
    decoded = inspector.inspect_bytes(candidate)
    source = (root / "tools/as.asm").read_text(encoding="utf-8")
    assertions = [
        {"name":"exclusive-temp-create-contract","passed":"O_WRITE|O_CREATE|O_EXCL" in source and "as_p1020_temp_name: db '/','t','m','p','/','.','a','s'" in source},
        {"name":"only-eexist-retried","passed":"cp E_EXIST" in source and "as_p1020_open_retry:" in source},
        {"name":"complete-write-close-validate-rename-order","passed":source.index("as_p1020_write_complete:") < source.index("call as_p1020_close_temp", source.index("as_p1020_write_complete:")) < source.index("call as_p1020_validate_candidate", source.index("as_p1020_write_complete:")) < source.index("ld a,SYS_RENAME", source.index("as_p1020_write_complete:"))},
        {"name":"owned-temp-only-cleanup","passed":"as_p1020_owned" in source and "ld a,SYS_REMOVE" in source},
        {"name":"destination-never-opened","passed":"ld (as_p1020_dest),hl" in source and "ld hl,as_p1020_temp_name\n    ld c,O_WRITE|O_CREATE|O_EXCL" in source},
        {"name":"full-obj1-revalidation","passed":all(x in source for x in ("as_p1020_validate_candidate:","as_p1020_validate_symbols:","as_p1020_validate_relocs:","as_p1020_crc16:"))},
        {"name":"host-golden-valid-obj1","passed":decoded["stored_length"] == len(candidate) and decoded["symbol_count"] == 1 and decoded["relocation_count"] == 1},
    ]
    require(all(a["passed"] for a in assertions), "P10.20 static transactional contract failure")

    assembler = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    fixture = build / "p1020-transaction.asm"
    fixture.write_text(f"""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../../tools/as.asm"
    ORG $C000
fixture:
    EMIT_P10_AS_OBJ1_SYMBOL_ROUTINES
    EMIT_P10_AS_OBJ1_RELOC_ROUTINES
    EMIT_P10_AS_TRANSACTION_ROUTINES

p1020_dest_name: db '/','t','m','p','/','o','u','t',0
p1020_candidate: db {db(candidate)}
p1020_candidate_end:

p1020_mode: db 0
p1020_open_calls: db 0
p1020_write_calls: db 0
p1020_close_calls: db 0
p1020_rename_calls: db 0
p1020_remove_calls: db 0
p1020_dest_marker: db $A5
p1020_saved_errno: db 0

p1020_reset:
    xor a
    ld (p1020_mode),a
    ld (p1020_open_calls),a
    ld (p1020_write_calls),a
    ld (p1020_close_calls),a
    ld (p1020_rename_calls),a
    ld (p1020_remove_calls),a
    ld (p1020_saved_errno),a
    ld a,$A5
    ld (p1020_dest_marker),a
    ld a,1
    ld (p1020_candidate+4),a
    ret

p1020_call:
    ld hl,p1020_dest_name
    ld de,p1020_candidate
    ld bc,p1020_candidate_end-p1020_candidate
    jp as_p1020_publish

p1020_fail:
    ld a,E_FORMAT
    scf
    ret

p1020_success:
    call p1020_reset
    call p1020_call
    ret c
    ld a,(p1020_dest_marker)
    cp $5A
    jp nz,p1020_fail
    ld a,(p1020_open_calls)
    cp 1
    jp nz,p1020_fail
    ld a,(p1020_write_calls)
    cp 1
    jp nz,p1020_fail
    ld a,(p1020_close_calls)
    cp 1
    jp nz,p1020_fail
    ld a,(p1020_rename_calls)
    cp 1
    jp nz,p1020_fail
    ld a,(p1020_remove_calls)
    or a
    jp nz,p1020_fail
    xor a
    ret

p1020_collision:
    call p1020_reset
    ld a,1
    ld (p1020_mode),a
    call p1020_call
    ret c
    ld a,(p1020_open_calls)
    cp 2
    jp nz,p1020_fail
    ld a,(as_p1020_temp_name+10)
    cp '1'
    jp nz,p1020_fail
    ld a,(p1020_remove_calls)
    or a
    jp nz,p1020_fail
    ld a,(p1020_dest_marker)
    cp $5A
    jp nz,p1020_fail
    xor a
    ret

p1020_write_fail:
    call p1020_reset
    ld a,2
    ld (p1020_mode),a
    call p1020_call
    jp nc,p1020_fail
    ld (p1020_saved_errno),a
    cp E_NOSPC
    jp nz,p1020_fail
    ld a,(p1020_dest_marker)
    cp $A5
    jp nz,p1020_fail
    ld a,(p1020_rename_calls)
    or a
    jp nz,p1020_fail
    ld a,(p1020_remove_calls)
    cp 1
    jp nz,p1020_fail
    xor a
    ret

p1020_rename_fail:
    call p1020_reset
    ld a,3
    ld (p1020_mode),a
    call p1020_call
    jp nc,p1020_fail
    cp E_BUSY
    jp nz,p1020_fail
    ld a,(p1020_dest_marker)
    cp $A5
    jp nz,p1020_fail
    ld a,(p1020_rename_calls)
    cp 1
    jp nz,p1020_fail
    ld a,(p1020_remove_calls)
    cp 1
    jp nz,p1020_fail
    xor a
    ret

p1020_postvalidate_fail:
    call p1020_reset
    ld a,4
    ld (p1020_mode),a
    call p1020_call
    jp nc,p1020_fail
    cp E_FORMAT
    jp nz,p1020_fail
    ld a,(p1020_dest_marker)
    cp $A5
    jp nz,p1020_fail
    ld a,(p1020_rename_calls)
    or a
    jp nz,p1020_fail
    ld a,(p1020_remove_calls)
    cp 1
    jp nz,p1020_fail
    xor a
    ret

p1020_alloc_fail:
    call p1020_reset
    ld a,5
    ld (p1020_mode),a
    call p1020_call
    jp nc,p1020_fail
    cp E_NOSPC
    jp nz,p1020_fail
    ld a,(p1020_dest_marker)
    cp $A5
    jp nz,p1020_fail
    ld a,(p1020_write_calls)
    or a
    jp nz,p1020_fail
    ld a,(p1020_close_calls)
    or a
    jp nz,p1020_fail
    ld a,(p1020_rename_calls)
    or a
    jp nz,p1020_fail
    ld a,(p1020_remove_calls)
    or a
    jp nz,p1020_fail
    xor a
    ret

p1020_preflight_fail:
    call p1020_reset
    ld a,2
    ld (p1020_candidate+4),a
    call p1020_call
    jp nc,p1020_fail
    cp E_FORMAT
    jp nz,p1020_fail
    ld a,1
    ld (p1020_candidate+4),a
    ld a,(p1020_open_calls)
    or a
    jp nz,p1020_fail
    ld a,(p1020_dest_marker)
    cp $A5
    jp nz,p1020_fail
    xor a
    ret

fixture_end:
    SAVEBIN "p1020-main.bin",fixture,fixture_end-fixture

    ORG $E000
p1020_gateway:
    cp SYS_GETPID
    jr z,p1020_sys_getpid
    cp SYS_OPEN
    jr z,p1020_sys_open
    cp SYS_WRITE
    jr z,p1020_sys_write
    cp SYS_CLOSE
    jr z,p1020_sys_close
    cp SYS_RENAME
    jr z,p1020_sys_rename
    cp SYS_REMOVE
    jr z,p1020_sys_remove
    ld a,E_NOTSUP
    scf
    ret

p1020_sys_getpid:
    ld hl,3
    xor a
    ret

p1020_sys_open:
    ld a,(p1020_open_calls)
    inc a
    ld (p1020_open_calls),a
    ld a,c
    cp O_WRITE|O_CREATE|O_EXCL
    jr nz,p1020_sys_format
    ld a,b
    cp OBJ_OBJ
    jr nz,p1020_sys_format
    ld a,(p1020_mode)
    cp 5
    jr z,p1020_sys_nospc
    cp 1
    jr nz,p1020_sys_open_ok
    ld a,(p1020_open_calls)
    cp 1
    jr nz,p1020_sys_open_ok
    ld a,E_EXIST
    scf
    ret
p1020_sys_open_ok:
    ld hl,4
    xor a
    ret

p1020_sys_write:
    ld a,(p1020_write_calls)
    inc a
    ld (p1020_write_calls),a
    ld a,d
    or a
    jr nz,p1020_sys_format
    ld a,e
    cp 4
    jr nz,p1020_sys_format
    ld a,(p1020_mode)
    cp 2
    jr z,p1020_sys_nospc
    cp 4
    jr nz,p1020_sys_write_ok
    ld a,2
    ld (p1020_candidate+4),a
p1020_sys_write_ok:
    push bc
    pop hl
    xor a
    ret

p1020_sys_close:
    ld a,(p1020_close_calls)
    inc a
    ld (p1020_close_calls),a
    xor a
    ret

p1020_sys_rename:
    ld a,(p1020_rename_calls)
    inc a
    ld (p1020_rename_calls),a
    ld a,(p1020_mode)
    cp 3
    jr z,p1020_sys_busy
    ld a,$5A
    ld (p1020_dest_marker),a
    xor a
    ret

p1020_sys_remove:
    ld a,(p1020_remove_calls)
    inc a
    ld (p1020_remove_calls),a
    xor a
    ret

p1020_sys_nospc:
    ld a,E_NOSPC
    scf
    ret
p1020_sys_busy:
    ld a,E_BUSY
    scf
    ret
p1020_sys_format:
    ld a,E_FORMAT
    scf
    ret
p1020_gateway_end:
    SAVEBIN "p1020-gateway.bin",p1020_gateway,p1020_gateway_end-p1020_gateway
""", encoding="utf-8", newline="\n")

    result = run_command([assembler, "--nologo", "--sym=p1020-transaction.sym", fixture.name], cwd=build, timeout_seconds=30)
    require(not result.timed_out and result.exit_code == 0, f"P10.20 assemble: {result.stderr or result.stdout}")
    main = (build / "p1020-main.bin").read_bytes()
    gateway = (build / "p1020-gateway.bin").read_bytes()
    require(len(main) <= 0x2000, "P10.20 fixture overlaps syscall gateway")

    if action == "test":
        names = (
            "p1020_success","p1020_collision","p1020_write_fail","p1020_rename_fail",
            "p1020_postvalidate_fail","p1020_alloc_fail","p1020_preflight_fail",
        )
        syms = phase3_open_descriptions._symbols(build / "p1020-transaction.sym", names)

        def patch(ram):
            ram[0xC000-0x4000:0xC000-0x4000+len(main)] = main
            ram[0xE000-0x4000:0xE000-0x4000+len(gateway)] = gateway

        for name in names:
            code = b"\xF3" + phase1._ld_sp(0xBFC0) + phase1._call(syms[name]) + phase1._jp_c(FAIL_PC) + phase1._jp(PASS_PC)
            run_sna(root, code, patch=patch)

        assertions += [
            {"name":"fuse-success-commit-after-close-validation","passed":True},
            {"name":"fuse-temp-collision-retry-without-removal","passed":True},
            {"name":"fuse-write-failure-preserves-destination","passed":True},
            {"name":"fuse-rename-failure-preserves-destination","passed":True},
            {"name":"fuse-postwrite-format-failure-blocks-rename","passed":True},
            {"name":"fuse-allocation-failure-preserves-destination","passed":True},
            {"name":"fuse-preflight-format-failure-has-no-output-side-effect","passed":True},
        ]

    hashes = {
        "tools/as.asm": sha256_file(root / "tools/as.asm"),
        "v1/include/zx48ux.inc": sha256_file(root / "v1/include/zx48ux.inc"),
        "v1/tools-host/inspect-obj/inspect.py": sha256_file(root / "v1/tools-host/inspect-obj/inspect.py"),
        "v1/build/p1020-main.bin": sha256_file(build / "p1020-main.bin"),
        "v1/build/p1020-gateway.bin": sha256_file(build / "p1020-gateway.bin"),
        "v1/tools-host/test-driver/phase10_step_20.py": sha256_file(root / "v1/tools-host/test-driver/phase10_step_20.py"),
        "v1/dist/certification/P10.19.build.json": sha256_file(root / "v1/dist/certification/P10.19.build.json"),
        "v1/dist/certification/P10.19.test.json": sha256_file(root / "v1/dist/certification/P10.19.test.json"),
    }
    return [result], hashes, assertions
