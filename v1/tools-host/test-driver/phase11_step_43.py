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

import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys

import phase1
import phase3_open_descriptions
from driver_core import DriverError
from fuse_harness import FAIL_PC, PASS_PC, run_sna


class P1143Error(DriverError):
    pass


SDK_COMMIT = "84d144de2721cda5075c3a6610a422663b5e2f77"
SOURCE_LEN = 640
PACKED_LEN = 562
RAW_BASE = 0xA000
PACKED_BASE = 0xA300
STATE_BASE = 0xA800
EXPECTED_OBJ = bytes.fromhex(
    "4f424a3101001800080000000100000020003400d24e81eb"
    "210000c9800267d86d61696e00000000000000000000000000000101"
)


def require(ok, message):
    if not ok:
        raise P1143Error(message)


def _db(data: bytes) -> str:
    return ",".join(f"${value:02X}" for value in data)


def _load_zxpack(root: Path):
    path = root / "v1/tools-host/zxpack/zxpack.py"
    spec = importlib.util.spec_from_file_location("zxux_p1143_zxpack", path)
    require(spec is not None and spec.loader is not None, "P11.43 cannot load ZXP1 oracle")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _static_contract(root: Path, source: bytes, packed: bytes, metadata: dict, mapping: dict) -> None:
    cc = (root / "v1/src/tools/cc.asm").read_text(encoding="utf-8")
    zx = (root / "v1/src/kernel/zxpack.asm").read_text(encoding="utf-8")
    handles = (root / "v1/src/kernel/handles.asm").read_text(encoding="utf-8")
    plan = (root / "docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV08.md").read_text(encoding="utf-8")

    require("## P11.43 - PACKED C source streaming equivalence" in plan
            and "through ordinary read calls" in plan
            and "without whole-file materialization" in plan
            and "byte-identical OBJ1" in plan,
            "REV08 P11.43 contract drift")
    require("MACRO EMIT_P1143_CC_STREAM_COMPILER" in cc
            and "CC_P1143_WINDOW_SIZE      EQU 64" in cc
            and "ld a,SYS_READ" in cc.split("MACRO EMIT_P1143_CC_STREAM_COMPILER", 1)[1],
            "P11.43 target compiler ordinary-read stream path missing")
    cm = cc.split("MACRO EMIT_P1143_CC_STREAM_COMPILER", 1)[1].split("ENDM", 1)[0]
    require("zx48_alloc" not in cm and "materializ" not in cm.lower()
            and not re.search(r"\biy\b|\bexx\b|ex\s+af\s*,\s*af'", "\n".join(
                line.split(";", 1)[0] for line in cm.splitlines()), re.I),
            "P11.43 compiler stream path owns forbidden memory/register state")
    require("MACRO EMIT_P1143_PACKED_READ_ADAPTER" in zx,
            "P11.43 packed ordinary-read adapter missing")
    zm = zx.split("MACRO EMIT_P1143_PACKED_READ_ADAPTER", 1)[1].split("ENDM", 1)[0]
    require("call zx48_p418_step" in zm
            and "zx48_alloc" not in zm
            and "materializ" not in zm.lower(),
            "P11.43 packed adapter is not bounded persistent streaming")
    require("PACKED_READER_STATE_SIZE  EQU 272" in handles
            and "ld bc,PACKED_READER_STATE_SIZE" in handles
            and "call zx48_free" in handles,
            "P11.43 final-close packed-reader release contract drift")

    require(len(source) == metadata.get("logical_length") == SOURCE_LEN,
            "P11.43 logical source length drift")
    require(hashlib.sha256(source).hexdigest() == metadata.get("logical_sha256")
            == "70e749c8abca04f48c85eeda278a94f899cbdbf41e9a21cec385190698df744a",
            "P11.43 logical source hash drift")
    require(len(packed) == metadata.get("packed_length") == PACKED_LEN,
            "P11.43 packed length drift")
    require(hashlib.sha256(packed).hexdigest() == metadata.get("packed_sha256")
            == "72251f17964d188f57352df1f4fbdafc20164cb60e3364d48cd3ad1fa4dc582a",
            "P11.43 packed hash drift")
    require(len(packed) < len(source), "P11.43 fixture is not genuinely PACKED")
    require(len(EXPECTED_OBJ) == metadata.get("expected_obj1_length") == 52
            and hashlib.sha256(EXPECTED_OBJ).hexdigest() == metadata.get("expected_obj1_sha256")
            == "7890260f81bfaec9f55f4faa603c8e993383e6b2152bcb359c58b363916ec2c6",
            "P11.43 expected OBJ1 oracle drift")

    require(mapping.get("schema") == 1 and mapping.get("step") == "P11.43"
            and mapping.get("sdk_commit") == SDK_COMMIT,
            "P11.43 source-map identity drift")
    rows = mapping.get("sources")
    require(isinstance(rows, list) and len(rows) == 1
            and rows[0].get("path") == "v1/tests/compiler/packed_source.c"
            and rows[0].get("git_blob") == "f133c1c53b67d1c0df1ffa3461105c5afda1ebbb",
            "P11.43 source-map source identity drift")
    require(rows[0].get("sdk_reference", {}).get("required_result") == "PASS"
            and rows[0].get("target_native", {}).get("required_result") == "PASS"
            and rows[0].get("target_native", {}).get("compiler") == "cc_p1143_compile_stream",
            "P11.43 SDK/native result mapping incomplete")


def dispatch(root, action, step, *, sha256_file, run_command, require_project_tool):
    if step != "P11.43":
        raise DriverError(step)

    source_path = root / "v1/tests/compiler/packed_source.c"
    metadata_path = root / "v1/tests/compiler/packed_source.json"
    mapping_path = root / "v1/tests/compiler/p1143-source-map.json"
    source = source_path.read_bytes()
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
    zxpack = _load_zxpack(root)
    packed = zxpack.encode(source)
    require(zxpack.decode(packed, len(source)) == source,
            "P11.43 host ZXP1 oracle round trip failed")
    _static_contract(root, source, packed, metadata, mapping)

    sdk = root / "v1/tests/compiler/sdk-reference/sdk"
    sdk_output = root / "v1/build/p1143-sdk-packed-source.c48b"
    sdk_output.parent.mkdir(parents=True, exist_ok=True)
    sdk_output.unlink(missing_ok=True)
    sdk_cmd = run_command(
        [sys.executable, "-B", str(sdk / "compiler/c48.py"), str(source_path),
         "-o", str(sdk_output)],
        cwd=sdk, timeout_seconds=30,
    )
    require(not sdk_cmd.timed_out and sdk_cmd.exit_code == 0 and sdk_output.is_file(),
            f"P11.43 pinned SDK expected PASS drift: {sdk_cmd.stdout}\n{sdk_cmd.stderr}")

    assembler = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    fixture = build / "p1143-packed-source.asm"
    fixture.write_text(f'''    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/tools/cc.asm"
    INCLUDE "../src/kernel/zxpack.asm"

P1143_SOURCE_LEN EQU {len(source)}
P1143_PACKED_LEN EQU {len(packed)}
P1143_RAW_BASE EQU ${RAW_BASE:04X}
P1143_PACKED_BASE EQU ${PACKED_BASE:04X}
P1143_STATE_BASE EQU ${STATE_BASE:04X}

    ORG $4000
p1143_start:
    EMIT_P1128_CC_OBJ1_WRITER
    EMIT_P1143_CC_STREAM_COMPILER
    EMIT_P417_PACKED_READER_STATE_ROUTINES
    EMIT_P418_PACKED_SEEK_ROUTINES
    EMIT_P1143_PACKED_READ_ADAPTER

p1143_raw_obj: defs 96,$CC
p1143_packed_obj: defs 96,$CC
p1143_negative_obj: defs 96,$CC
p1143_expected_obj:
    db {_db(EXPECTED_OBJ)}
p1143_expected_obj_end:

p1143_raw_pos: dw 0
p1143_raw_reads: db 0
p1143_packed_reads: db 0
p1143_state_ptr: dw 0
p1143_alloc_calls: db 0
p1143_free_calls: db 0
p1143_alloc_bad: db 0
p1143_materialize_detected: db 0
p1143_last_alloc: dw 0
p1143_last_free: dw 0
p1143_perturb: db 0
p1143_perturb_done: db 0
p1143_gate_dst: dw 0
p1143_gate_count: dw 0
p1143_gate_transfer: dw 0

p1143_fail:
    ld a,E_FORMAT
    scf
    ret

p1143_reset:
    xor a
    ld (p1143_raw_pos),a
    ld (p1143_raw_pos+1),a
    ld (p1143_raw_reads),a
    ld (p1143_packed_reads),a
    ld (p1143_state_ptr),a
    ld (p1143_state_ptr+1),a
    ld (p1143_alloc_calls),a
    ld (p1143_free_calls),a
    ld (p1143_alloc_bad),a
    ld (p1143_materialize_detected),a
    ld (p1143_last_alloc),a
    ld (p1143_last_alloc+1),a
    ld (p1143_last_free),a
    ld (p1143_last_free+1),a
    ld (p1143_perturb),a
    ld (p1143_perturb_done),a
    ret

zx48_alloc:
    ld (p1143_last_alloc),bc
    ld hl,p1143_alloc_calls
    inc (hl)
    ld hl,P1143_SOURCE_LEN
    or a
    sbc hl,bc
    jr nz,p1143_alloc_not_whole
    ld a,1
    ld (p1143_materialize_detected),a
    ld a,E_NOSPC
    scf
    ret
p1143_alloc_not_whole:
    ld a,b
    cp high P417_STATE_SIZE
    jr nz,p1143_alloc_reject
    ld a,c
    cp low P417_STATE_SIZE
    jr nz,p1143_alloc_reject
    ld hl,P1143_STATE_BASE
    xor a
    ret
p1143_alloc_reject:
    ld a,1
    ld (p1143_alloc_bad),a
    ld a,E_NOSPC
    scf
    ret

zx48_free:
    ld (p1143_last_free),bc
    ld de,P1143_STATE_BASE
    or a
    sbc hl,de
    jr nz,p1143_free_bad
    ld a,b
    cp high P417_STATE_SIZE
    jr nz,p1143_free_bad
    ld a,c
    cp low P417_STATE_SIZE
    jr nz,p1143_free_bad
    ld hl,p1143_free_calls
    inc (hl)
    xor a
    ret
p1143_free_bad:
    ld a,1
    ld (p1143_alloc_bad),a
    ld a,E_INVAL
    scf
    ret

p1143_open_packed:
    ld bc,P417_STATE_SIZE
    ld a,ALLOC_COLD_PREFERRED
    call zx48_alloc
    ret c
    ld (p1143_state_ptr),hl
    call zx48_p417_state_init
    push hl
    pop ix
    ld hl,P1143_PACKED_BASE
    ld bc,P1143_PACKED_LEN
    call zx48_p418_state_bind
    ret c
    xor a
    ld (p1143_packed_reads),a
    ret

p1143_close:
    ld a,SYS_CLOSE
    call SYSCALL_GATEWAY
    ret

p1143_compare_expected:
    ld de,p1143_expected_obj
    ld b,p1143_expected_obj_end-p1143_expected_obj
p1143_compare_expected_loop:
    ld a,(de)
    cp (hl)
    jr nz,p1143_compare_mismatch
    inc de
    inc hl
    djnz p1143_compare_expected_loop
    xor a
    ret
p1143_compare_mismatch:
    ld a,E_FORMAT
    scf
    ret

p1143_compare_objects:
    ld hl,p1143_raw_obj
    ld de,p1143_packed_obj
    ld b,52
p1143_compare_objects_loop:
    ld a,(de)
    cp (hl)
    jp nz,p1143_fail
    inc de
    inc hl
    djnz p1143_compare_objects_loop
    xor a
    ret

p1143_compile_raw:
    xor a
    ld (p1143_raw_pos),a
    ld (p1143_raw_pos+1),a
    ld (p1143_raw_reads),a
    ld a,1
    ld de,p1143_raw_obj
    ld ix,96
    call cc_p1143_compile_stream
    ret c
    ld de,52
    or a
    sbc hl,de
    jp nz,p1143_fail
    ld e,1
    call p1143_close
    ret c
    ld hl,p1143_raw_obj
    call p1143_compare_expected
    ret c
    ld a,(p1143_raw_reads)
    cp 39
    jp nz,p1143_fail
    ld hl,(p1143_raw_pos)
    ld de,P1143_SOURCE_LEN
    or a
    sbc hl,de
    jp nz,p1143_fail
    xor a
    ret

p1143_compile_packed:
    call p1143_open_packed
    ret c
    ld a,2
    ld de,p1143_packed_obj
    ld ix,96
    call cc_p1143_compile_stream
    ret c
    ld de,52
    or a
    sbc hl,de
    jp nz,p1143_fail

    ld hl,(p1143_state_ptr)
    ld de,P417_CTRL_LOGICAL_POS_O
    add hl,de
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld hl,P1143_SOURCE_LEN
    or a
    sbc hl,de
    jp nz,p1143_fail
    ld hl,(p1143_state_ptr)
    ld de,P417_CTRL_PHYSICAL_POS_O
    add hl,de
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld hl,P1143_PACKED_LEN
    or a
    sbc hl,de
    jp nz,p1143_fail

    ld e,2
    call p1143_close
    ret c
    ld hl,p1143_packed_obj
    call p1143_compare_expected
    ret c
    ld a,(p1143_packed_reads)
    cp 51
    jp nz,p1143_fail
    ld a,(p1143_alloc_calls)
    cp 1
    jp nz,p1143_fail
    ld a,(p1143_free_calls)
    cp 1
    jp nz,p1143_fail
    ld a,(p1143_alloc_bad)
    or a
    jp nz,p1143_fail
    ld a,(p1143_materialize_detected)
    or a
    jp nz,p1143_fail
    ld hl,(p1143_last_alloc)
    ld de,P417_STATE_SIZE
    or a
    sbc hl,de
    jp nz,p1143_fail
    ld hl,(p1143_last_free)
    ld de,P417_STATE_SIZE
    or a
    sbc hl,de
    jp nz,p1143_fail
    ld hl,(p1143_state_ptr)
    ld a,h
    or l
    jp nz,p1143_fail
    xor a
    ret

p1143_raw_probe:
    call p1143_reset
    jp p1143_compile_raw

p1143_packed_probe:
    call p1143_reset
    jp p1143_compile_packed

p1143_equivalence:
    call p1143_reset
    call p1143_compile_raw
    ret c
    xor a
    ld (p1143_alloc_calls),a
    ld (p1143_free_calls),a
    ld (p1143_alloc_bad),a
    ld (p1143_materialize_detected),a
    call p1143_compile_packed
    ret c
    call p1143_compare_objects
    ret c
    xor a
    ret

p1143_negative_materialize:
    call p1143_reset
    ld bc,P1143_SOURCE_LEN
    ld a,ALLOC_COLD_PREFERRED
    call zx48_alloc
    jp nc,p1143_fail
    cp E_NOSPC
    jp nz,p1143_fail
    ld a,(p1143_materialize_detected)
    cp 1
    jp nz,p1143_fail
    ld a,(p1143_free_calls)
    or a
    jp nz,p1143_fail
    xor a
    ret

p1143_negative_perturb:
    call p1143_reset
    call p1143_open_packed
    ret c
    ld a,1
    ld (p1143_perturb),a
    ld a,2
    ld de,p1143_negative_obj
    ld ix,96
    call cc_p1143_compile_stream
    ret c
    ld e,2
    call p1143_close
    ret c
    ld a,(p1143_perturb_done)
    cp 1
    jp nz,p1143_fail
    ld hl,p1143_negative_obj
    call p1143_compare_expected
    jp nc,p1143_fail
    cp E_FORMAT
    jp nz,p1143_fail
    ld a,(p1143_materialize_detected)
    or a
    jp nz,p1143_fail
    xor a
    ret

p1143_end:
    ASSERT p1143_end <= $9000
    SAVEBIN "p1143-main.bin",p1143_start,p1143_end-p1143_start

    ORG $E000
p1143_gateway:
    cp SYS_READ
    jr z,p1143_gate_read
    cp SYS_CLOSE
    jp z,p1143_gate_close
    ld a,E_NOTSUP
    scf
    ret

p1143_gate_read:
    ld (p1143_gate_dst),hl
    ld a,e
    cp 1
    jr z,p1143_gate_raw
    cp 2
    jr z,p1143_gate_packed
    ld a,E_NOENT
    scf
    ret

p1143_gate_raw:
    ld hl,p1143_raw_reads
    inc (hl)
    ld hl,P1143_SOURCE_LEN
    ld de,(p1143_raw_pos)
    or a
    sbc hl,de
    jp z,p1143_gate_eof
    jp c,p1143_gate_bad
    ld de,17
    or a
    sbc hl,de
    jr c,p1143_gate_raw_available
    ld hl,17
    jr p1143_gate_raw_transfer
p1143_gate_raw_available:
    add hl,de
p1143_gate_raw_transfer:
    ld (p1143_gate_transfer),hl
    ld bc,(p1143_raw_pos)
    ld hl,P1143_RAW_BASE
    add hl,bc
    ld de,(p1143_gate_dst)
    ld bc,(p1143_gate_transfer)
    ldir
    ld hl,(p1143_raw_pos)
    ld de,(p1143_gate_transfer)
    add hl,de
    ld (p1143_raw_pos),hl
    ld hl,(p1143_gate_transfer)
    xor a
    ret

p1143_gate_packed:
    ld hl,p1143_packed_reads
    inc (hl)
    ld hl,(p1143_state_ptr)
    ld a,h
    or l
    jp z,p1143_gate_bad
    push hl
    pop ix
    ld hl,(p1143_gate_dst)
    ld bc,13
    ld de,P1143_SOURCE_LEN
    call zx48_p1143_packed_read
    ret c
    ld (p1143_gate_count),hl
    ld a,h
    or l
    jr z,p1143_gate_eof
    ld a,(p1143_perturb)
    or a
    jr z,p1143_gate_packed_done
    ld a,(p1143_perturb_done)
    or a
    jr nz,p1143_gate_packed_done
    ld hl,(p1143_gate_count)
    ld de,6
    or a
    sbc hl,de
    jr c,p1143_gate_packed_done
    ld hl,(p1143_gate_dst)
    ld de,5
    add hl,de
    ld a,(hl)
    xor 1
    ld (hl),a
    ld a,1
    ld (p1143_perturb_done),a
p1143_gate_packed_done:
    ld hl,(p1143_gate_count)
    xor a
    ret

p1143_gate_eof:
    ld hl,0
    xor a
    ret

p1143_gate_close:
    ld a,e
    cp 1
    jr z,p1143_gate_close_ok
    cp 2
    jr nz,p1143_gate_bad
    ld hl,(p1143_state_ptr)
    ld a,h
    or l
    jr z,p1143_gate_close_ok
    ld bc,P417_STATE_SIZE
    call zx48_free
    ret c
    ld hl,0
    ld (p1143_state_ptr),hl
p1143_gate_close_ok:
    xor a
    ret

p1143_gate_bad:
    ld a,E_FORMAT
    scf
    ret

p1143_gateway_end:
    SAVEBIN "p1143-gateway.bin",p1143_gateway,p1143_gateway_end-p1143_gateway
''', encoding="utf-8", newline="\n")

    asm_cmd = run_command(
        [assembler, "--nologo", "--sym=p1143-packed-source.sym", fixture.name],
        cwd=build, timeout_seconds=60,
    )
    require(not asm_cmd.timed_out and asm_cmd.exit_code == 0,
            f"P11.43 fixture assembly failed: {asm_cmd.stderr or asm_cmd.stdout}")
    module = (build / "p1143-main.bin").read_bytes()
    gateway = (build / "p1143-gateway.bin").read_bytes()
    require(0 < len(module) <= 0x5000, f"P11.43 fixture too large: {len(module)}")
    syms = phase3_open_descriptions._symbols(
        build / "p1143-packed-source.sym",
        ("p1143_raw_probe", "p1143_packed_probe", "p1143_equivalence",
         "p1143_negative_materialize", "p1143_negative_perturb"),
    )

    commands = [sdk_cmd, asm_cmd]
    assertions = [
        {"name":"pinned-sdk-reference-source-pass-recorded-and-executed","passed":True},
        {"name":"raw-and-packed-use-same-ordinary-sys-read-compiler-entry","passed":True},
        {"name":"compiler-read-window-exact-64-no-whole-source-buffer","passed":True},
        {"name":"packed-reader-state-kernel-owned-exact-272","passed":True},
        {"name":"packed-read-adapter-no-allocation-or-materialization","passed":True},
        {"name":"host-zxp1-encoding-deterministic-and-genuinely-smaller","passed":True},
    ]

    if action == "test":
        def patch(ram):
            ram[0:len(module)] = module
            ram[0xE000-0x4000:0xE000-0x4000+len(gateway)] = gateway
            ram[RAW_BASE-0x4000:RAW_BASE-0x4000+len(source)] = source
            ram[PACKED_BASE-0x4000:PACKED_BASE-0x4000+len(packed)] = packed
            ram[STATE_BASE-0x4000:STATE_BASE-0x4000+272] = b"\xA5" * 272

        for name in ("p1143_raw_probe", "p1143_packed_probe", "p1143_equivalence",
                     "p1143_negative_materialize", "p1143_negative_perturb"):
            code = (
                b"\xF3" + phase1._ld_sp(0xBFC0)
                + phase1._call(syms[name])
                + phase1._jp_c(FAIL_PC) + phase1._jp(PASS_PC)
            )
            try:
                commands.append(run_sna(root, code, patch=patch, timeout=45))
            except DriverError as exc:
                raise P1143Error(f"{name} target-native PACKED-source fixture failed: {exc}") from None

        assertions += [
            {"name":"fuse-raw-source-ordinary-read-native-cc-obj1","passed":True},
            {"name":"fuse-packed-source-continuous-reader-native-cc-obj1","passed":True},
            {"name":"raw-packed-obj1-byte-identical-exact-52-bytes","passed":True},
            {"name":"packed-reader-final-state-logical640-physical562","passed":True},
            {"name":"final-close-frees-exact-272-state","passed":True},
            {"name":"no-compiler-allocation-equal-to-logical-source-length","passed":True},
            {"name":"forbidden-whole-file-materialization-negative-detected","passed":True},
            {"name":"one-decoded-byte-perturbation-hash-oracle-negative-detected","passed":True},
        ]

    hashes = {
        "v1/tests/compiler/packed_source.c": sha256_file(source_path),
        "v1/tests/compiler/packed_source.json": sha256_file(metadata_path),
        "v1/tests/compiler/p1143-source-map.json": sha256_file(mapping_path),
        "v1/src/tools/cc.asm": sha256_file(root / "v1/src/tools/cc.asm"),
        "v1/src/kernel/zxpack.asm": sha256_file(root / "v1/src/kernel/zxpack.asm"),
        "v1/src/kernel/handles.asm": sha256_file(root / "v1/src/kernel/handles.asm"),
        "v1/tools-host/zxpack/zxpack.py": sha256_file(root / "v1/tools-host/zxpack/zxpack.py"),
        "v1/build/p1143-main.bin": sha256_file(build / "p1143-main.bin"),
        "v1/build/p1143-gateway.bin": sha256_file(build / "p1143-gateway.bin"),
        "v1/tools-host/test-driver/phase11_step_43.py": sha256_file(root / "v1/tools-host/test-driver/phase11_step_43.py"),
        "v1/dist/certification/P11.42.build.json": sha256_file(root / "v1/dist/certification/P11.42.build.json"),
        "v1/dist/certification/P11.42.test.json": sha256_file(root / "v1/dist/certification/P11.42.test.json"),
    }
    return commands, hashes, assertions
