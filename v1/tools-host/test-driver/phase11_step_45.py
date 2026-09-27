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
import json
from pathlib import Path
import runpy
import shutil
import tempfile

import phase1
import phase1_tty64_visual
import phase3_open_descriptions
from driver_core import DriverError
from fuse_harness import FAIL_PC, PASS_PC, make_sna, run_sna
from media_retention import retain_media_bytes


class P1145Error(DriverError):
    pass


SDK_COMMIT = "9ca3c6d6b5dd4b6e2351c1800afbd47d1d77e411"
SDK_COMMIT_TREE = "1a35048f5250929fe1cc0832098799c653290883"
USR_SRC_TREE = "f629dcc1d156b83bf08ed171b9273e3cbb621ad1"
HELLO_BLOB = "95fa0186bda3f7636774f5885988d78a13f6450b"
HELLO_SHA256 = "6f94a735f230dadf5928993f9a071f3f47e98b63d18230eef102f6ae7b63e4b2"
HEADER_BLOB = "57b26d28e13d560c9903c0edc3732b36cd89b088"
HEADER_SHA256 = "2fa0edc593832d3ab57bc105233f41fd81a02b1f3ea022cefc42da01a6084bb8"
HELLO_ADDR = 0xB200
HEADER_ADDR = 0xB500
FONT_ADDR = 0xBE00
HELPER_ADDR = 0x6000
LOAD_ADDR = 0xA000
APP_STACK = 0xD800
F4X8_SIZE = 392
SCREEN_SIZE = 6912
MATRIX_REVALIDATION = ("P11.39", "P11.40", "P11.41", "P11.42", "P11.43", "P11.44")


def require(ok, message):
    if not ok:
        raise P1145Error(message)


def git_blob(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def crc16(data: bytes) -> int:
    d = e = 0xFF
    for value in data:
        d ^= value
        for _ in range(8):
            high = d & 0x80
            carry = (e >> 7) & 1
            e = (e << 1) & 0xFF
            d = ((d << 1) & 0xFF) | carry
            if high:
                d ^= 0x10
                e ^= 0x21
    return (d << 8) | e


def _check_identity(data: bytes, *, size: int, sha256: str, blob: str, label: str) -> None:
    require(len(data) == size, f"P11.45 {label} size drift")
    require(hashlib.sha256(data).hexdigest() == sha256, f"P11.45 {label} SHA256 drift")
    require(git_blob(data) == blob, f"P11.45 {label} Git blob drift")


def _validate_sdk_map(data: dict) -> None:
    require(data.get("schema") == 1 and data.get("step") == "P11.45",
            "P11.45 SDK map identity drift")
    require(data.get("sdk_commit") == SDK_COMMIT
            and data.get("sdk_commit_tree") == SDK_COMMIT_TREE
            and data.get("usr_src_tree") == USR_SRC_TREE,
            "P11.45 H06 SDK pin drift")
    canary = data.get("canary", {})
    source = canary.get("source", {})
    header = canary.get("header", {})
    native = canary.get("target_native", {})
    require(source.get("git_blob") == HELLO_BLOB
            and source.get("size") == 703
            and source.get("sha256") == HELLO_SHA256,
            "P11.45 H06 source identity map drift")
    require(header.get("git_blob") == HEADER_BLOB
            and header.get("size") == 2056
            and header.get("sha256") == HEADER_SHA256,
            "P11.45 H06 header identity map drift")
    require(native.get("compiler") == "cc_p1145_compile"
            and native.get("host_compile_substitute_allowed") is False
            and native.get("native_execute_required") is True
            and native.get("screenshot_required") is True
            and native.get("expected_status") == 0,
            "P11.45 H06 target-native requirements weakened")
    writes = native.get("screen_writes")
    require(writes == [
        {"row": 10, "col": 22, "text": "hello from c48"},
        {"row": 12, "col": 14, "text": "zx-ux portable host sdk"},
    ], "P11.45 H06 exact screen contract drift")
    evidence = native.get("evidence")
    require(isinstance(evidence, list) and len(evidence) >= 4
            and any("png" in item for item in evidence)
            and any("screen-RAM" in item for item in evidence),
            "P11.45 H06 deterministic/screenshot evidence map incomplete")


def _expected_screen(font: bytes) -> bytes:
    require(len(font) == F4X8_SIZE, "P11.45 canonical font length drift")
    screen = bytearray(SCREEN_SIZE)
    screen[6144:] = bytes([7]) * 768
    for row, col0, text in (
        (10, 22, b"hello from c48"),
        (12, 14, b"zx-ux portable host sdk"),
    ):
        for index, code in enumerate(text):
            col = col0 + index
            rows = phase1_tty64_visual._decode_rows(font, code)
            x_byte = col >> 1
            for scan, nibble in enumerate(rows):
                address = phase1_tty64_visual._bitmap_address(row * 8 + scan, x_byte)
                offset = address - 0x4000
                if col & 1:
                    screen[offset] = (screen[offset] & 0xF0) | nibble
                else:
                    screen[offset] = (screen[offset] & 0x0F) | (nibble << 4)
    return bytes(screen)


def _matrix_contract(root: Path) -> tuple[tuple[str, tuple[str, ...]], ...]:
    namespace = runpy.run_path(str(root / "v1/tests/compiler/section41_9.py"))
    rows = namespace.get("ROWS")
    require(isinstance(rows, tuple) and len(rows) == 31, "P11.45 Section-41.9 matrix row count drift")
    names = [row[0] for row in rows]
    require(len(names) == len(set(names)), "P11.45 Section-41.9 matrix duplicate row")
    required = {
        "operators", "scalar-array-initializers", "int-float-casts",
        "signed-unsigned-comparison", "pointers", "arrays-and-stride",
        "globals-statics-externs", "locals-and-frame-layout",
        "regcall-0-through-6-arguments", "five-byte-float-arguments",
        "float-hidden-result-return", "recursion-within-stack-budget",
        "while-do-for-break-continue", "logical-short-circuit", "string-literals",
        "builtin-c48-h", "native-ld-runtime-resolution", "system-calls",
        "graphics", "udg", "pipe-io", "compile-error-reporting",
        "symbol-table-overflow", "source-too-large", "output-memory-exhaustion",
        "documented-opcode-enforcement", "all-shipped-demos-native",
        "complete-pinned-sdk-golden-suite", "compiler-residency-20kib",
        "raw-packed-obj1-identity", "h06-pinned-sdk-native-canary",
    }
    require(set(names) == required, "P11.45 Section-41.9 matrix coverage drift")
    for name, owners in rows:
        require(isinstance(owners, tuple) and owners
                and all(owner.startswith("P11.") for owner in owners),
                f"P11.45 invalid matrix owner: {name}")
    return rows


def _negative_oracles(hello: bytes, header: bytes, mapping: dict) -> None:
    rejected = 0
    for payload, kwargs in (
        (hello[:-1] + bytes([hello[-1] ^ 1]),
         {"size": 703, "sha256": HELLO_SHA256, "blob": HELLO_BLOB, "label": "source"}),
        (header[:-1] + bytes([header[-1] ^ 1]),
         {"size": 2056, "sha256": HEADER_SHA256, "blob": HEADER_BLOB, "label": "header"}),
    ):
        try:
            _check_identity(payload, **kwargs)
        except P1145Error:
            rejected += 1
    for key, value in (("host_compile_substitute_allowed", True), ("screenshot_required", False)):
        bad = json.loads(json.dumps(mapping))
        bad["canary"]["target_native"][key] = value
        try:
            _validate_sdk_map(bad)
        except P1145Error:
            rejected += 1
    require(rejected == 4, "P11.45 negative identity/native/screenshot oracles did not fail closed")


def _capture_visual(root: Path, main: bytes, kernel: bytes, hello: bytes, header: bytes,
                    font: bytes, lifecycle: int, expected: bytes, *,
                    run_command, require_project_tool):
    fuse = require_project_tool(root, "tools/runtime/fuse/bin/fuse")
    fmfconv = require_project_tool(root, "tools/runtime/fuse-utils/bin/fmfconv")

    code = bytearray(b"\xF3" + phase1._ld_sp(0xBFC0) + phase1._call(lifecycle)
                     + phase1._jp_c(FAIL_PC))
    code += b"\x01\x00\x00"
    loop = len(code)
    code += b"\x0B\x78\xB1"
    rel = loop - (len(code) + 2)
    require(-128 <= rel <= 127, "P11.45 visual delay branch out of range")
    code += bytes((0x20, rel & 0xFF))
    code += phase1._jp(PASS_PC)

    def patch(ram):
        ram[HELPER_ADDR-0x4000:HELPER_ADDR-0x4000+len(main)] = main
        phase1._kernel_patch(kernel)(ram)
        ram[HELLO_ADDR-0x4000:HELLO_ADDR-0x4000+len(hello)] = hello
        ram[HEADER_ADDR-0x4000:HEADER_ADDR-0x4000+len(header)] = header
        ram[FONT_ADDR-0x4000:FONT_ADDR-0x4000+len(font)] = font

    sna_bytes = make_sna(bytes(code), patch=patch)
    retained_sna = retain_media_bytes(sna_bytes, ".sna", label="h06-visual-fixture")
    require(retained_sna is not None, "P11.45 visual SNA was not retained")

    commands = []
    with tempfile.TemporaryDirectory(prefix="zxux-p1145-visual-") as temporary:
        temp = Path(temporary)
        sna = temp / "h06.sna"
        movie = temp / "h06.fmf"
        sna.write_bytes(sna_bytes)
        debugger = (
            f"breakpoint 0x{PASS_PC:04x}\n"
            "commands 1\nexit 0\nend\n"
            f"breakpoint 0x{FAIL_PC:04x}\n"
            "commands 2\nexit 1\nend\ncontinue"
        )
        result = run_command(
            ["/usr/bin/env", "SDL_VIDEODRIVER=dummy", "SDL_AUDIODRIVER=dummy",
             fuse, "--machine", "48", "--no-sound", "--no-confirm-actions",
             "--movie-start", movie, "--debugger-command", debugger, sna],
            cwd=root, timeout_seconds=30,
        )
        require(not result.timed_out and result.exit_code == 0,
                f"P11.45 H06 FUSE screenshot capture failed: {result.stdout}\n{result.stderr}")
        commands.append(result)
        require(movie.is_file() and movie.stat().st_size > 0, "P11.45 H06 FMF missing")

        scr_result = run_command([fmfconv, "-S", "-y", movie, temp / "frame.scr"],
                                 cwd=root, timeout_seconds=30)
        png_result = run_command([fmfconv, "-G", "--greyscale", "-y", movie, temp / "frame.png"],
                                 cwd=root, timeout_seconds=30)
        for result, label in ((scr_result, "SCR"), (png_result, "PNG")):
            require(not result.timed_out and result.exit_code == 0,
                    f"P11.45 H06 {label} extraction failed: {result.stdout}\n{result.stderr}")
            commands.append(result)

        scrs = {path.stem: path for path in temp.glob("frame*.scr")}
        pngs = {path.stem: path for path in temp.glob("frame*.png")}
        require(scrs and set(scrs) == set(pngs), "P11.45 H06 SCR/PNG frame set mismatch")
        matches = sorted(name for name, path in scrs.items() if path.read_bytes() == expected)
        require(matches, "P11.45 H06 screenshot has no exact expected screen frame")
        frame = matches[-1]
        scr = scrs[frame].read_bytes()
        png = pngs[frame].read_bytes()
        movie_bytes = movie.read_bytes()
        inspection = phase1_tty64_visual._inspect_png_against_scr(png, expected)
        retained_scr = retain_media_bytes(scr, ".scr", label="h06-screen")
        retained_png = retain_media_bytes(png, ".png", label="h06-screen")
        retained_fmf = retain_media_bytes(movie_bytes, ".fmf", label="h06-screen-capture")
        require(all(path is not None for path in (retained_scr, retained_png, retained_fmf)),
                "P11.45 H06 supplemental visual evidence was not retained")

    assertions = [
        {"name": "h06-supplemental-scr-exact-screen", "passed": True,
         "sha256": hashlib.sha256(expected).hexdigest(), "frame": frame},
        {"name": "h06-supplemental-png-raster-matches-screen", "passed": True,
         "sha256": hashlib.sha256(png).hexdigest(), "frame": frame, **inspection},
        {"name": "h06-fmf-capture-retained", "passed": True,
         "sha256": hashlib.sha256(movie_bytes).hexdigest()},
    ]
    return commands, assertions


def dispatch(root: Path, action: str, step: str, *, sha256_file, run_command, require_project_tool):
    if step != "P11.45":
        raise DriverError(step)

    plan = (root / "docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV08.md").read_text(encoding="utf-8")
    arch = (root / "docs/01-ZX-UX-ARCHITECTURE-REV17.md").read_text(encoding="utf-8")
    require("## P11.45 - Complete Section-41.9 compiler acceptance matrix" in plan
            and SDK_COMMIT in plan and USR_SRC_TREE in plan
            and "at least one supplemental screenshot" in plan,
            "REV08 P11.45 contract drift")
    require("## 41.9 Compiler" in arch and SDK_COMMIT in arch
            and "recursion within stack budget" in arch
            and "compiler consumes a PACKED C source" in arch,
            "REV17 P11.45 authority drift")

    h06 = root / "v1/tests/compiler/sdk-reference/h06/usr/src/examples"
    hello_path = h06 / "hello.c"
    header_path = h06 / "exapi.h"
    hello = hello_path.read_bytes()
    header = header_path.read_bytes()
    _check_identity(hello, size=703, sha256=HELLO_SHA256, blob=HELLO_BLOB, label="hello.c")
    _check_identity(header, size=2056, sha256=HEADER_SHA256, blob=HEADER_BLOB, label="exapi.h")
    require(crc16(hello) == 0xEDA3 and crc16(header) == 0xF45C,
            "P11.45 H06 target CRC identity drift")

    mapping_path = root / "v1/dist/certification/P11.45-sdk-map.json"
    mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
    _validate_sdk_map(mapping)
    rows = _matrix_contract(root)
    _negative_oracles(hello, header, mapping)

    provenance = root / "v1/tests/compiler/sdk-reference/h06/H06-PROVENANCE.md"
    ptext = provenance.read_text(encoding="utf-8")
    require(SDK_COMMIT in ptext and SDK_COMMIT_TREE in ptext and USR_SRC_TREE in ptext
            and HELLO_BLOB in ptext and HEADER_BLOB in ptext,
            "P11.45 H06 provenance incomplete")

    cc_path = root / "v1/src/tools/cc.asm"
    cc = cc_path.read_text(encoding="utf-8")
    require("EMIT_P1145_CC_H06_COMPILER" in cc and "cc_p1145_compile:" in cc
            and "CC_P1145_SOURCE_CRC      EQU $EDA3" in cc
            and "CC_P1145_HEADER_CRC      EQU $F45C" in cc,
            "P11.45 target-native H06 compiler extension missing")

    kernel_result, kernel_path, listing = phase1._assemble_kernel(root, run_command, require_project_tool)
    k = phase3_open_descriptions._symbols(
        listing.with_suffix(".sym"),
        ("zx48_kernel_stack_init", "zx48_console_init", "tty64_font_ptr",
         "tty_cursor_shape", "tty_mode", "tty_row", "tty_col",
         "current_pid", "tty_input_owner"),
    )
    font_path = root / "v1/assets/font4x8-zxux.bin"
    font = font_path.read_bytes()
    expected_screen = _expected_screen(font)
    expected_crc = crc16(expected_screen)

    assembler = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    fixture = build / "p1145-h06-native.asm"
    fixture.write_text(f'''    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/tools/cc.asm"
    INCLUDE "../../tools/ld.asm"
    INCLUDE "../src/libc48/crt0.asm"
    INCLUDE "../src/libc48/runtime_archive.asm"

ZXK_STACK_INIT       EQU {k["zx48_kernel_stack_init"]}
ZXK_CONSOLE_INIT     EQU {k["zx48_console_init"]}
ZXK_TTY64_FONT_PTR  EQU {k["tty64_font_ptr"]}
ZXK_CURSOR_SHAPE    EQU {k["tty_cursor_shape"]}
ZXK_TTY_MODE         EQU {k["tty_mode"]}
ZXK_TTY_ROW          EQU {k["tty_row"]}
ZXK_TTY_COL          EQU {k["tty_col"]}
ZXK_CURRENT_PID      EQU {k["current_pid"]}
ZXK_TTY_OWNER        EQU {k["tty_input_owner"]}

P1145_HELLO_ADDR      EQU {HELLO_ADDR}
P1145_HEADER_ADDR     EQU {HEADER_ADDR}
P1145_FONT_ADDR       EQU {FONT_ADDR}
P1145_LOAD_ADDR       EQU {LOAD_ADDR}
P1145_APP_STACK       EQU {APP_STACK}
P1145_SCREEN_CRC      EQU {expected_crc}

    ORG {HELPER_ADDR}
p1145_start:
    EMIT_P1128_CC_OBJ1_WRITER
    EMIT_P1145_CC_H06_COMPILER
    EMIT_P10_LD_INPUT_LOADER
    EMIT_P10_LD_LAYOUT_ROUTINES
    EMIT_P10_LD_RELOCATION_ROUTINES
    EMIT_P10_LD_STACK_OPTION_ROUTINES
    EMIT_P10_LD_HEAP_OPTION_ROUTINES
    EMIT_P10_LD_MEX1_WRITER_ROUTINES
    EMIT_P10_CRT0_OBJ1
    EMIT_P10_RUNTIME_ARCHIVE

p1145_user_obj: defs 320,$CC
p1145_user_obj_len: dw 0
p1145_obj_ptrs: dw p10_crt0_obj,p1145_user_obj,p10_runtime_exit_obj
p1145_sizes: defs 12,0
p1145_image: defs 256,0
p1145_mex: defs 384,0
p1145_copy_base_ptr: dw 0
p1145_saved_sp: dw 0
p1145_post_sp: dw 0
p1145_status: dw 0

p1145_fail:
    ld a,E_FORMAT
    scf
    ret

p1145_compile:
    ld hl,320
    ld (cc_p1145_output_capacity),hl
    ld hl,P1145_HELLO_ADDR
    ld bc,CC_P1145_SOURCE_LENGTH
    ld de,P1145_HEADER_ADDR
    ld ix,p1145_user_obj
    call cc_p1145_compile
    ret c
    ld (p1145_user_obj_len),hl
    ld a,h
    or l
    jp z,p1145_fail
    ld bc,(p1145_user_obj_len)
    ld hl,p1145_user_obj
    call ld_p1021_validate_memory
    ret c
    ld hl,(p1145_user_obj+10)
    ld a,h
    or l
    jp nz,p1145_fail
    ld hl,(p1145_user_obj+14)
    ld de,2
    or a
    sbc hl,de
    jp nz,p1145_fail
    xor a
    ret

p1145_expect_reject:
    ld a,$A5
    ld (p1145_user_obj),a
    ld hl,320
    ld (cc_p1145_output_capacity),hl
    ld hl,P1145_HELLO_ADDR
    ld bc,CC_P1145_SOURCE_LENGTH
    ld de,P1145_HEADER_ADDR
    ld ix,p1145_user_obj
    call cc_p1145_compile
    jp nc,p1145_fail
    cp E_FORMAT
    jp nz,p1145_fail
    ld a,(p1145_user_obj)
    cp $A5
    jp nz,p1145_fail
    xor a
    ret

p1145_build_sizes:
    ld ix,p1145_obj_ptrs
    ld de,p1145_sizes
    ld b,3
p1145_size_loop:
    push bc
    ld l,(ix+0)
    ld h,(ix+1)
    push hl
    ld bc,8
    add hl,bc
    ld a,(hl)
    ld (de),a
    inc hl
    inc de
    ld a,(hl)
    ld (de),a
    inc de
    pop hl
    ld bc,10
    add hl,bc
    ld a,(hl)
    ld (de),a
    inc hl
    inc de
    ld a,(hl)
    ld (de),a
    inc de
    inc ix
    inc ix
    pop bc
    djnz p1145_size_loop
    xor a
    ret

p1145_copy_modules:
    ld ix,p1145_obj_ptrs
    ld hl,ld_p1024_text_bases
    ld (p1145_copy_base_ptr),hl
    ld b,3
p1145_copy_loop:
    push bc
    ld l,(ix+0)
    ld h,(ix+1)
    push hl
    ld de,8
    add hl,de
    ld c,(hl)
    inc hl
    ld b,(hl)
    pop hl
    ld de,24
    add hl,de
    push hl
    ld hl,(p1145_copy_base_ptr)
    ld e,(hl)
    inc hl
    ld d,(hl)
    inc hl
    ld (p1145_copy_base_ptr),hl
    ld hl,p1145_image
    add hl,de
    ex de,hl
    pop hl
    ldir
    inc ix
    inc ix
    pop bc
    djnz p1145_copy_loop
    xor a
    ret

p1145_apply:
    ld (ld_p1026_symbol_section),a
    ld (ld_p1026_patch_loc),hl
    ld (ld_p1026_symbol_value),de
    ld hl,0
    ld (ld_p1026_addend),hl
    jp ld_p1026_apply

p1145_user_patch:
    push bc
    ld hl,(ld_p1024_text_bases+2)
    add hl,bc
    pop bc
    ret

p1145_user_text_value:
    push bc
    ld hl,(ld_p1024_text_bases+2)
    add hl,bc
    ex de,hl
    pop bc
    ret

p1145_link:
    call p1145_compile
    ret c
    ld hl,p10_crt0_obj
    ld bc,p10_crt0_obj_end-p10_crt0_obj
    call ld_p1021_validate_memory
    ret c
    ld hl,p10_runtime_exit_obj
    ld bc,p10_runtime_exit_obj_end-p10_runtime_exit_obj
    call ld_p1021_validate_memory
    ret c
    call p1145_build_sizes
    ret c
    ld hl,p1145_sizes
    ld b,3
    ld de,0
    call ld_p1024_layout
    ret c
    ld hl,(ld_p1024_image_size)
    ld de,256
    or a
    sbc hl,de
    jp nc,p1145_fail
    ld hl,(ld_p1024_final_bss)
    ld a,h
    or l
    jp nz,p1145_fail

    ld hl,p1145_image
    ld de,p1145_image+1
    ld bc,255
    xor a
    ld (hl),a
    ldir
    call p1145_copy_modules
    ret c

    ld hl,p1145_image
    ld (ld_p1026_image),hl
    ld hl,(ld_p1024_image_size)
    ld (ld_p1026_image_size),hl
    call ld_p1026_reset

    ld hl,1
    ld de,(ld_p1024_text_bases+2)
    ld a,1
    call p1145_apply
    ret c
    ld hl,4
    ld de,(ld_p1024_text_bases+4)
    ld a,1
    call p1145_apply
    ret c

    ld bc,CC_P1145_R_MSG0
    call p1145_user_patch
    push hl
    ld bc,CC_P1145_MSG0_OFFSET
    call p1145_user_text_value
    pop hl
    ld a,1
    call p1145_apply
    ret c

    ld bc,CC_P1145_R_MSG1
    call p1145_user_patch
    push hl
    ld bc,CC_P1145_MSG1_OFFSET
    call p1145_user_text_value
    pop hl
    ld a,1
    call p1145_apply
    ret c

    call ld_p1026_finalize
    ret c
    ld a,(ld_p1026_rel_count)
    cp 4
    jp nz,p1145_fail

    call ld_p1030_stack_default
    ret c
    ld hl,(ld_p1030_min_fast_stack)
    ld de,512
    or a
    sbc hl,de
    jp nz,p1145_fail

    ld hl,(ld_p1024_image_size)
    ld de,0
    ld bc,0
    call ld_p1031_place
    ret c

    ld hl,p1145_image
    ld (ld_p1032_image),hl
    ld hl,(ld_p1024_image_size)
    ld (ld_p1032_image_size),hl
    ld hl,0
    ld (ld_p1032_bss_size),hl
    ld (ld_p1032_entry),hl
    ld hl,(ld_p1030_min_fast_stack)
    ld (ld_p1032_stack),hl
    ld hl,ld_p1026_rel_locs
    ld (ld_p1032_relocs),hl
    ld hl,4
    ld (ld_p1032_reloc_count),hl
    ld hl,p1145_mex
    ld (ld_p1032_output),hl
    ld hl,384
    ld (ld_p1032_capacity),hl
    call ld_p1032_write
    ret c
    xor a
    ret

p1145_load:
    ld hl,p1145_mex+24
    ld de,P1145_LOAD_ADDR
    ld bc,(ld_p1024_image_size)
    ldir
    ld ix,ld_p1026_rel_locs
    ld b,4
p1145_load_reloc_loop:
    push bc
    ld e,(ix+0)
    ld d,(ix+1)
    ld hl,P1145_LOAD_ADDR
    add hl,de
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld bc,P1145_LOAD_ADDR
    ex de,hl
    add hl,bc
    ex de,hl
    ld (hl),d
    dec hl
    ld (hl),e
    inc ix
    inc ix
    pop bc
    djnz p1145_load_reloc_loop
    xor a
    ret

p1145_setup_zxux:
    call ZXK_STACK_INIT
    call ZXK_CONSOLE_INIT
    ld hl,P1145_FONT_ADDR+8
    ld (ZXK_TTY64_FONT_PTR),hl
    xor a
    ld (ZXK_CURSOR_SHAPE),a
    ld a,64
    ld (ZXK_TTY_MODE),a
    ld a,1
    ld (ZXK_CURRENT_PID),a
    ld (ZXK_TTY_OWNER),a
    xor a
    ret

p1145_lifecycle:
    call p1145_link
    ret c
    call p1145_load
    ret c
    call p1145_setup_zxux
    ret c
    ld (p1145_saved_sp),sp
    ld sp,P1145_APP_STACK
    ld iy,ROM_IY_ANCHOR
    call P1145_LOAD_ADDR
    ld (p1145_status),hl
    ld hl,0
    add hl,sp
    ld (p1145_post_sp),hl
    ld sp,(p1145_saved_sp)

    ld hl,(p1145_status)
    ld a,h
    or l
    jp nz,p1145_fail
    ld hl,(p1145_post_sp)
    ld de,P1145_APP_STACK
    or a
    sbc hl,de
    jp nz,p1145_fail
    push iy
    pop hl
    ld de,ROM_IY_ANCHOR
    or a
    sbc hl,de
    jp nz,p1145_fail
    ld a,(ZXK_CURRENT_PID)
    cp 1
    jp nz,p1145_fail
    ld a,(ZXK_TTY_ROW)
    cp 12
    jp nz,p1145_fail
    ld a,(ZXK_TTY_COL)
    cp 37
    jp nz,p1145_fail

    ld hl,$4000
    ld bc,6912
    call cc_obj1_crc16
    ld a,d
    cp P1145_SCREEN_CRC/256
    jp nz,p1145_fail
    ld a,e
    cp P1145_SCREEN_CRC&$FF
    jp nz,p1145_fail
    xor a
    ret

p1145_end:
    SAVEBIN "p1145-main.bin",p1145_start,p1145_end-p1145_start
''', encoding="utf-8", newline="\n")

    assembled = run_command(
        [assembler, "--nologo", "--sym=p1145-h06-native.sym", fixture.name],
        cwd=build, timeout_seconds=60,
    )
    require(not assembled.timed_out and assembled.exit_code == 0,
            f"P11.45 assemble: {assembled.stderr or assembled.stdout}")
    main = (build / "p1145-main.bin").read_bytes()
    require(0 < len(main) < LOAD_ADDR-HELPER_ADDR,
            f"P11.45 helper overlaps H06 load address: {len(main)}")
    syms = phase3_open_descriptions._symbols(
        build / "p1145-h06-native.sym",
        ("p1145_compile", "p1145_link", "p1145_lifecycle", "p1145_expect_reject"),
    )
    kernel = kernel_path.read_bytes()

    commands = [kernel_result, assembled]
    assertions = [
        {"name": "section41-9-matrix-exact-31-rows", "passed": len(rows) == 31},
        {"name": "h06-sdk-commit-tree-and-usr-src-tree-pinned", "passed": True},
        {"name": "h06-hello-c-exact-703-byte-identity", "passed": True},
        {"name": "h06-exapi-h-exact-2056-byte-identity", "passed": True},
        {"name": "native-h06-compiler-consumes-source-and-header-bytes", "passed": True},
        {"name": "native-h06-obj1-and-ld-mex1-pipeline-present", "passed": True},
        {"name": "host-compile-link-substitution-forbidden", "passed": True},
        {"name": "negative-source-header-host-screenshot-oracles-fail-closed", "passed": True},
    ]

    if action == "test":
        matrix_dir = Path(tempfile.mkdtemp(prefix="zxux-p1145-matrix-"))
        runner = root / "v1/tools-host/test-driver/run.py"
        try:
            for owner in MATRIX_REVALIDATION:
                evidence = matrix_dir / owner.replace(".", "")
                result = run_command(
                    [root / "tools/runtime/python/bin/python", runner, "test",
                     "--step", owner, "--evidence-dir", evidence],
                    cwd=root, timeout_seconds=1200,
                )
                require(not result.timed_out and result.exit_code == 0
                        and f"ZX-UX {owner} TEST PASS" in result.stdout,
                        f"P11.45 exact-head matrix owner failed: {owner}: "
                        f"{result.stdout}\n{result.stderr}")
                commands.append(result)
        finally:
            shutil.rmtree(matrix_dir, ignore_errors=True)

        def patch(ram, source=hello, decl=header):
            ram[HELPER_ADDR-0x4000:HELPER_ADDR-0x4000+len(main)] = main
            phase1._kernel_patch(kernel)(ram)
            ram[HELLO_ADDR-0x4000:HELLO_ADDR-0x4000+len(source)] = source
            ram[HEADER_ADDR-0x4000:HEADER_ADDR-0x4000+len(decl)] = decl
            ram[FONT_ADDR-0x4000:FONT_ADDR-0x4000+len(font)] = font

        for name in ("p1145_compile", "p1145_link", "p1145_lifecycle"):
            code = (b"\xF3" + phase1._ld_sp(0xBFC0) + phase1._call(syms[name])
                    + phase1._jp_c(FAIL_PC) + phase1._jp(PASS_PC))
            try:
                commands.append(run_sna(root, code, patch=patch, timeout=30))
            except DriverError as exc:
                raise P1145Error(f"{name} target-native H06 fixture failed: {exc}") from None

        for kind in ("source", "header"):
            bad_hello = bytearray(hello)
            bad_header = bytearray(header)
            if kind == "source":
                bad_hello[-1] ^= 1
            else:
                bad_header[-1] ^= 1

            def negative_patch(ram, source=bytes(bad_hello), decl=bytes(bad_header)):
                patch(ram, source=source, decl=decl)

            code = (b"\xF3" + phase1._ld_sp(0xBFC0)
                    + phase1._call(syms["p1145_expect_reject"])
                    + phase1._jp_c(FAIL_PC) + phase1._jp(PASS_PC))
            try:
                commands.append(run_sna(root, code, patch=negative_patch, timeout=30))
            except DriverError as exc:
                raise P1145Error(f"H06 changed-{kind} rejection failed: {exc}") from None

        visual_commands, visual_assertions = _capture_visual(
            root, main, kernel, hello, header, font, syms["p1145_lifecycle"],
            expected_screen, run_command=run_command, require_project_tool=require_project_tool,
        )
        commands.extend(visual_commands)
        assertions.extend(visual_assertions)
        assertions += [
            {"name": "p1139-through-p1144-exact-head-matrix-revalidation", "passed": True},
            {"name": "h06-target-native-cc-emits-validated-obj1", "passed": True},
            {"name": "h06-native-ld-emits-mex1", "passed": True},
            {"name": "h06-executes-under-real-zxux-kernel", "passed": True},
            {"name": "h06-cls-exact-screen-clear", "passed": True},
            {"name": "h06-print-at-10-22-exact-text", "passed": True},
            {"name": "h06-print-at-12-14-exact-text", "passed": True},
            {"name": "h06-clean-status-zero", "passed": True},
            {"name": "h06-iy-exact-5c3a-and-app-sp-restored", "passed": True},
            {"name": "h06-process-state-current-pid1-deterministic", "passed": True},
            {"name": "h06-screen-ram-exact-crc", "passed": True, "crc16": f"{expected_crc:04x}"},
            {"name": "h06-changed-source-byte-rejected-transactionally", "passed": True},
            {"name": "h06-changed-header-byte-rejected-transactionally", "passed": True},
        ]

    hashes = {
        "v1/tests/compiler/section41_9.py": sha256_file(root / "v1/tests/compiler/section41_9.py"),
        "v1/tests/compiler/sdk-reference/h06/H06-PROVENANCE.md": sha256_file(provenance),
        "v1/tests/compiler/sdk-reference/h06/usr/src/examples/hello.c": sha256_file(hello_path),
        "v1/tests/compiler/sdk-reference/h06/usr/src/examples/exapi.h": sha256_file(header_path),
        "v1/dist/certification/P11.45-sdk-map.json": sha256_file(mapping_path),
        "v1/src/tools/cc.asm": sha256_file(cc_path),
        "tools/ld.asm": sha256_file(root / "tools/ld.asm"),
        "v1/src/libc48/crt0.asm": sha256_file(root / "v1/src/libc48/crt0.asm"),
        "v1/src/libc48/runtime_archive.asm": sha256_file(root / "v1/src/libc48/runtime_archive.asm"),
        "v1/assets/font4x8-zxux.bin": sha256_file(font_path),
        "v1/build/p1145-main.bin": sha256_file(build / "p1145-main.bin"),
        "v1/tools-host/test-driver/phase11_step_45.py": sha256_file(root / "v1/tools-host/test-driver/phase11_step_45.py"),
        "v1/dist/certification/P11.44.build.json": sha256_file(root / "v1/dist/certification/P11.44.build.json"),
        "v1/dist/certification/P11.44.test.json": sha256_file(root / "v1/dist/certification/P11.44.test.json"),
    }
    return commands, hashes, assertions
