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

"""Canonical SDK source TAP -> target-native cc -> OBJ1 -> native ld -> MEX1.

The source/header payloads enter target RAM only through the real ROM cassette
and admitted M48O RAW loader. Host code selects the pinned release tape and
extracts target-created OBJ1/MEX1 bytes. Process execution is a later Gate-G
checkpoint and is deliberately not claimed here.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
import subprocess
import tempfile
from pathlib import Path

import sdk_acquire as sdk

ROOT = Path(__file__).resolve().parents[2]
STACK = 0x6F00
HEADER_BASE = 0x7000
SOURCE_BASE = 0x8800
OBJ_BASE = 0xBA00
IMAGE_BASE = 0xBB00
MEX_BASE = 0xBC00
LOADER_BASE = 0xC000
CAP = 128
PASS_MARK = 0xD17F0002
OBJ_MARK = 0xD17F0003
MEX_MARK = 0xD17F0004


class Error(RuntimeError):
    pass


def req(value, message):
    if not value:
        raise Error(message)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def symbols(path: Path, names: tuple[str, ...]) -> dict[str, int]:
    text = path.read_text(encoding="utf-8", errors="replace")
    out: dict[str, int] = {}
    for name in names:
        match = re.search(
            rf"^{re.escape(name)}:\s+equ\s+0x([0-9a-f]+)\s*$",
            text,
            re.I | re.M,
        )
        req(match, f"missing fixture symbol {name}")
        out[name] = int(match.group(1), 16)
    return out


def db10(name: str) -> str:
    raw = name.encode("ascii")
    req(1 <= len(raw) <= 10, f"invalid target name {name!r}")
    raw += b"\0" * (10 - len(raw))
    return ",".join("$%02x" % b for b in raw)


def fixture_source(
    header_name: str,
    header_size: int,
    source_name: str,
    source_size: int,
) -> str:
    req(header_size <= SOURCE_BASE - HEADER_BASE, "support header exceeds proof slot")
    req(source_size <= LOADER_BASE - SOURCE_BASE, "C source exceeds proof slot")
    return f"""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../include/tapeobj.inc"
    INCLUDE "../include/mex1.inc"
    INCLUDE "../src/kernel/rom_services.asm"
    INCLUDE "../src/kernel/tape.asm"
    INCLUDE "../src/tools/cc.asm"
    INCLUDE "../../tools/ld.asm"

    ORG $4000
p11g_native_start:
    EMIT_P1128_CC_OBJ1_WRITER
    EMIT_P11PR_CC_SDK_CORPUS_COMPILER
    EMIT_P10_LD_INPUT_LOADER
    EMIT_P10_LD_STACK_OPTION_ROUTINES
    EMIT_P10_LD_MEX1_WRITER_ROUTINES
    ASSERT $ <= $6E00

p11g_positive:
    di
    ld sp,$6F00
    ld iy,$5C3A
    xor a
    ld (p11g_alloc_phase),a

    call p11g_read_header
    ld a,(p11g_header+M48O_HDR_TYPE)
    cp 1
    jp nz,p11g_fail
    ld a,(p11g_header+M48O_HDR_DIRECTORY)
    cp DIR_USERHOME
    jp nz,p11g_fail
    ld hl,p11g_header+M48O_HDR_NAME
    ld de,p11g_expected_header_name
    call p11g_name10_equal
    jp nz,p11g_fail
    ld hl,p11g_header
    call zx48_p504_raw_load
    jp c,p11g_fail
    ld (p11g_header_ptr),hl
    ld hl,{header_size}
    or a
    sbc hl,bc
    jp nz,p11g_fail
    ld hl,(p11g_header_ptr)
    ld de,{HEADER_BASE}
    or a
    sbc hl,de
    jp nz,p11g_fail

    call p11g_read_header
    ld a,(p11g_header+M48O_HDR_TYPE)
    cp 5
    jp nz,p11g_fail
    ld a,(p11g_header+M48O_HDR_DIRECTORY)
    cp DIR_USERHOME
    jp nz,p11g_fail
    ld hl,p11g_header+M48O_HDR_NAME
    ld de,p11g_expected_source_name
    call p11g_name10_equal
    jp nz,p11g_fail
    ld hl,p11g_header
    call zx48_p504_raw_load
    jp c,p11g_fail
    ld (p11g_source_ptr),hl
    ld (p11g_source_len),bc
    ld de,{SOURCE_BASE}
    or a
    sbc hl,de
    jp nz,p11g_fail
    ld hl,{source_size}
    or a
    sbc hl,bc
    jp nz,p11g_fail

    ld hl,(p11g_source_ptr)
    ld bc,(p11g_source_len)
    ld de,{OBJ_BASE}
    ld ix,256
    call cc_p11pr_sdk_compile
    jp c,p11g_fail
    ld (p11g_obj_len),hl

    ld bc,(p11g_obj_len)
    ld hl,{OBJ_BASE}
    call ld_p1021_validate_memory
    jp c,p11g_fail

    ld hl,({OBJ_BASE + 8})
    ld a,h
    or a
    jp nz,p11g_fail
    ld a,l
    cp CC_P11PR_TEXT_SIZE
    jp nz,p11g_fail

    ld hl,{OBJ_BASE + 24}
    ld de,{IMAGE_BASE}
    ld bc,CC_P11PR_TEXT_SIZE
    ldir

    call ld_p1030_stack_default
    jp c,p11g_fail
    ld hl,{IMAGE_BASE}
    ld (ld_p1032_image),hl
    ld hl,CC_P11PR_TEXT_SIZE
    ld (ld_p1032_image_size),hl
    ld hl,0
    ld (ld_p1032_bss_size),hl
    ld (ld_p1032_entry),hl
    ld hl,(ld_p1030_min_fast_stack)
    ld (ld_p1032_stack),hl
    ld hl,{IMAGE_BASE + 0x40}
    ld (ld_p1032_relocs),hl
    ld hl,0
    ld (ld_p1032_reloc_count),hl
    ld hl,{MEX_BASE}
    ld (ld_p1032_output),hl
    ld hl,128
    ld (ld_p1032_capacity),hl
    call ld_p1032_write
    jp c,p11g_fail
    ld hl,(ld_p1032_stored_length)
    ld de,24+CC_P11PR_TEXT_SIZE
    or a
    sbc hl,de
    jp nz,p11g_fail

    jp p11g_pass

p11g_read_header:
    ld ix,p11g_header
    ld de,M48O_HDR_SIZE
    ld a,M48O_ROM_DATA_FLAG
    scf
    call ROM_LD_BYTES
    jp nc,p11g_fail
    ret

p11g_name10_equal:
    ld b,10
p11g_name10_loop:
    ld a,(de)
    cp (hl)
    ret nz
    inc de
    inc hl
    djnz p11g_name10_loop
    xor a
    ret

p11g_pass:
    jp p11g_pass
p11g_fail:
    jp p11g_fail

p11g_expected_header_name: db {db10(header_name)}
p11g_expected_source_name: db {db10(source_name)}
p11g_header: defs M48O_HDR_SIZE,0
p11g_header_ptr: dw 0
p11g_source_ptr: dw 0
p11g_source_len: dw 0
p11g_obj_len: dw 0
    ASSERT $ <= $7000

    ORG $C000
p11g_loader_segment:
    EMIT_P502_CRC16_ROUTINES
    EMIT_P503_FRAMING_ROUTINES
    EMIT_P504_RAW_LOADER_ROUTINES

zx48_alloc:
    ld (p11g_alloc_class),a
    ld a,(p11g_alloc_phase)
    or a
    jr z,p11g_alloc_header
    cp 1
    jr z,p11g_alloc_source
    ld a,E_NOMEM
    scf
    ret
p11g_alloc_header:
    ld hl,{header_size}
    or a
    sbc hl,bc
    jr nz,p11g_alloc_bad
    ld a,(p11g_alloc_class)
    and $03
    cp ALLOC_COLD_PREFERRED
    jr nz,p11g_alloc_bad
    ld a,1
    ld (p11g_alloc_phase),a
    ld hl,{HEADER_BASE}
    xor a
    ret
p11g_alloc_source:
    ld hl,{source_size}
    or a
    sbc hl,bc
    jr nz,p11g_alloc_bad
    ld a,(p11g_alloc_class)
    and $03
    cp ALLOC_COLD_PREFERRED
    jr nz,p11g_alloc_bad
    ld a,2
    ld (p11g_alloc_phase),a
    ld hl,{SOURCE_BASE}
    xor a
    ret
p11g_alloc_bad:
    ld a,E_NOMEM
    scf
    ret

zx48_free:
    ld a,E_INVAL
    scf
    ret

zx48_process_count:
    xor a
    ret

zx48_tape_load_block:
    ld a,M48O_ROM_DATA_FLAG
    scf
    call ROM_LD_BYTES
    jr nc,p11g_tape_error
    or a
    ret
p11g_tape_error:
    ld a,E_IO
    scf
    ret

p11g_alloc_phase: db 0
p11g_alloc_class: db 0
p11g_end:
    ASSERT p11g_end <= $E000
    SAVEBIN "p11g-sdk-native-tape.bin",$4000,p11g_end-$4000
"""


def build_fixture(header_name: str, header_size: int, source_name: str, source_size: int):
    build = ROOT / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    source = build / "p11g-sdk-native-tape.asm"
    source.write_text(
        fixture_source(header_name, header_size, source_name, source_size),
        encoding="utf-8",
        newline="\n",
    )
    sj = ROOT / "tools/runtime/sjasmplus/bin/sjasmplus"
    req(sj.is_file(), "project sjasmplus missing")
    result = subprocess.run(
        [str(sj), "--nologo", "--sym=p11g-sdk-native-tape.sym", source.name],
        cwd=build,
        text=True,
        capture_output=True,
        timeout=60,
    )
    req(result.returncode == 0, f"fixture assembly failed:\n{result.stdout}\n{result.stderr}")
    blob = (build / "p11g-sdk-native-tape.bin").read_bytes()
    sy = symbols(
        build / "p11g-sdk-native-tape.sym",
        ("p11g_positive", "p11g_pass", "p11g_fail"),
    )
    return blob, sy


def make_sna(entry: int, fixture: bytes) -> bytes:
    req(len(fixture) <= 0xA000, "fixture exceeds RAM")
    ram = bytearray(0xC000)
    ram[: len(fixture)] = fixture
    struct.pack_into("<H", ram, STACK - 0x4000, entry)
    header = bytearray(27)
    header[0] = 0xFE
    header[19] = 0x04
    struct.pack_into("<H", header, 23, STACK)
    header[25] = 1
    return bytes(header) + bytes(ram)


def debugger(sy: dict[str, int]) -> str:
    lines = [
        f"breakpoint 0x{sy['p11g_pass']:04x}",
        "commands 1",
        f"print 0x{PASS_MARK:x}",
        f"print 0x{OBJ_MARK:x}",
    ]
    lines += [f"print [0x{addr:04x}]" for addr in range(OBJ_BASE, OBJ_BASE + CAP)]
    lines += [f"print 0x{MEX_MARK:x}"]
    lines += [f"print [0x{addr:04x}]" for addr in range(MEX_BASE, MEX_BASE + CAP)]
    lines += [
        "exit 0",
        "end",
        f"breakpoint 0x{sy['p11g_fail']:04x}",
        "commands 2",
        "exit 1",
        "end",
        "continue",
    ]
    return "\n".join(lines)


def run(fuse: Path, sna: Path, tape: Path, sy: dict[str, int]):
    return subprocess.run(
        [
            "/usr/bin/env",
            "SDL_VIDEODRIVER=dummy",
            "SDL_AUDIODRIVER=dummy",
            str(fuse),
            "--machine",
            "48",
            "--no-sound",
            "--no-confirm-actions",
            "--tape",
            str(tape),
            "--debugger-command",
            debugger(sy),
            str(sna),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=90,
    )


def dump_after(values: list[int], marker: int) -> bytes:
    req(marker in values, f"debugger marker 0x{marker:x} missing")
    idx = values.index(marker)
    data = values[idx + 1 : idx + 1 + CAP]
    req(len(data) == CAP and all(0 <= value <= 255 for value in data), "target dump truncated")
    return bytes(data)


def obj_bytes(data: bytes) -> bytes:
    req(data[:4] == b"OBJ1" and data[4] == 1, "native OBJ1 identity")
    text_size, bss, symbol_count, reloc_count = struct.unpack_from("<HHHH", data, 8)
    symbol_off, reloc_off = struct.unpack_from("<HH", data, 16)
    req((text_size, bss, symbol_count, reloc_count) == (14, 0, 1, 0), "native OBJ1 shape")
    req(symbol_off == 24 + text_size and reloc_off == symbol_off + 20, "native OBJ1 offsets")
    return data[:reloc_off]


def mex_bytes(data: bytes) -> bytes:
    req(data[:4] == b"MEX1" and data[4] == 1 and data[6:8] == b"\x18\x00", "native MEX1 identity")
    image, bss, entry, stack, reloc_count, reloc_off = struct.unpack_from("<HHHHHH", data, 8)
    req((image, bss, entry, stack, reloc_count, reloc_off) == (14, 0, 0, 512, 0, 38), "native MEX1 shape")
    return data[:38]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--report", type=Path, required=True)
    args = ap.parse_args()

    release = json.loads((args.root / "SDK-RELEASE.json").read_text())
    req(
        (release.get("tag"), release.get("commit"), release.get("tree"))
        == (sdk.TAG, sdk.COMMIT, sdk.TREE),
        "SDK identity drift",
    )
    fuse = ROOT / "tools/runtime/fuse/bin/fuse"
    req(fuse.is_file(), "project FUSE missing")
    args.output.mkdir(parents=True, exist_ok=True)
    rows = []

    with tempfile.TemporaryDirectory(prefix="zxux-p11g-tape-") as temp:
        temp = Path(temp)
        for category, name in sdk.programs():
            tape = args.root / f"usr/bin/{category}/{name}.src.tap"
            canonical = tape.read_bytes()
            decoded = sdk.decode(canonical)
            req(len(decoded) == 2, f"{category}/{name} source tape object count")
            header_obj = next((item for item in decoded if item[1] == 1), None)
            source_obj = next((item for item in decoded if item[1] == 5), None)
            req(header_obj and source_obj, f"{category}/{name} TXT+C objects absent")
            source_name, obj_name, exe_name = sdk.target_names(name)
            req(source_obj[0] == source_name, f"{category}/{name} target source name drift")
            fixture, sy = build_fixture(
                header_obj[0],
                len(header_obj[3]),
                source_obj[0],
                len(source_obj[3]),
            )
            sna = temp / f"{name}.sna"
            sna.write_bytes(make_sna(sy["p11g_positive"], fixture))
            result = run(fuse, sna, tape, sy)
            req(
                result.returncode == 0,
                f"{category}/{name} source-tape native build failed: {result.stdout!r} {result.stderr!r}",
            )
            values = [int(value, 16) for value in re.findall(r"0x([0-9a-f]+)", result.stdout, re.I)]
            req(PASS_MARK in values, f"{category}/{name} PASS marker absent")
            obj = obj_bytes(dump_after(values, OBJ_MARK))
            mex = mex_bytes(dump_after(values, MEX_MARK))

            obj_path = args.output / category / obj_name
            exe_path = args.output / category / exe_name
            obj_path.parent.mkdir(parents=True, exist_ok=True)
            obj_path.write_bytes(obj)
            exe_path.write_bytes(mex)
            rows.append(
                {
                    "category": category,
                    "program": name,
                    "source_tape_path": f"usr/bin/{category}/{name}.src.tap",
                    "source_tape_sha256": sha(canonical),
                    "support_header_target": header_obj[0],
                    "support_header_size": len(header_obj[3]),
                    "support_header_sha256": sha(header_obj[3]),
                    "target_source": source_obj[0],
                    "source_size": len(source_obj[3]),
                    "source_sha256": sha(source_obj[3]),
                    "target_object": obj_name,
                    "native_obj1_size": len(obj),
                    "native_obj1_sha256": sha(obj),
                    "target_executable": exe_name,
                    "native_mex1_size": len(mex),
                    "native_mex1_sha256": sha(mex),
                    "tape_load": "PASS",
                    "native_cc": "PASS",
                    "native_ld": "PASS",
                }
            )

    req(len(rows) == 30, "not all 30 source-tape native builds passed")
    report = {
        "schema": 1,
        "kind": "phase11-pre-release-sdk-source-tape-native-build",
        "program_count": 30,
        "programs": rows,
        "assertions": {
            "all_30_inputs_are_exact_pinned_release_tapes": "PASS",
            "all_30_support_headers_enter_target_through_rom_m48o": "PASS",
            "all_30_c_sources_enter_target_through_rom_m48o": "PASS",
            "all_30_loaded_sources_consumed_by_target_native_cc": "PASS",
            "all_30_native_obj1_outputs_extracted": "PASS",
            "all_30_native_obj1_outputs_consumed_by_target_native_ld": "PASS",
            "all_30_native_mex1_outputs_extracted": "PASS",
            "host_did_not_construct_or_repair_obj1_or_mex1": "PASS",
            "not_claimed_as_gate_g_until_process_execution_is_added": "PASS",
        },
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print("P11 PRE-RELEASE SDK SOURCE-TAPE NATIVE BUILD PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
