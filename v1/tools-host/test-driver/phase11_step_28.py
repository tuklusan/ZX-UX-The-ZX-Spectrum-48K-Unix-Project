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

import re
import phase1
import phase3_open_descriptions
import phase10_obj1_header
import phase10_obj1_inspector
import phase10_obj1_reloc
import phase10_obj1_symbol
from driver_core import DriverError
from fuse_harness import FAIL_PC, PASS_PC, run_sna


class P1128Error(DriverError):
    pass


def require(ok, message):
    if not ok:
        raise P1128Error(message)


def _golden() -> bytes:
    symbols = (
        phase10_obj1_symbol.make_symbol(
            b"_start", 0, phase10_obj1_symbol.SEC_TEXT, phase10_obj1_symbol.SYM_GLOBAL
        )
        + phase10_obj1_symbol.make_symbol(
            b"ext", 0, phase10_obj1_symbol.SEC_UNDEF, phase10_obj1_symbol.SYM_GLOBAL
        )
    )
    relocs = phase10_obj1_reloc.make_reloc(0, 1)
    return phase10_obj1_header.build_obj(
        text=b"\x01\x00\xc9", bss=7, symbols=symbols, relocs=relocs
    )


def dispatch(root, action, step, *, sha256_file, run_command, require_project_tool):
    if step != "P11.28":
        raise DriverError(step)

    cc = root / "v1/src/tools/cc.asm"
    text = cc.read_text(encoding="utf-8")
    arch = (root / "docs/01-ZX-UX-ARCHITECTURE-REV17.md").read_text(encoding="utf-8")
    plan = (root / "docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV08.md").read_text(encoding="utf-8")

    require("MACRO EMIT_P1128_CC_OBJ1_WRITER" in text, "P11.28 OBJ1 writer macro missing")
    require("cc_obj1_write:" in text and "cc_obj1_commit_marker:" in text,
            "P11.28 writer entry/commit state missing")
    require("## P11.28 - Compiler OBJ1 writer" in plan
            and "Emit deterministic valid OBJ1 for text/BSS/symbols/relocs; no direct MEX output shortcut." in plan,
            "REV08 P11.28 contract drift")
    require("OBJ1" in arch and "native" in arch, "REV17 native OBJ1 contract missing")

    macro = text[text.index("    MACRO EMIT_P1128_CC_OBJ1_WRITER"):]
    macro = macro[:macro.index("    ENDM") + 8]
    code = "\n".join(line.split(";", 1)[0] for line in macro.splitlines())
    require("MEX" not in macro.upper(), "P11.28 contains a direct MEX shortcut")
    require(not re.search(r"\biy\b|\bexx\b|ex\s+af\s*,\s*af'", code, re.I),
            "P11.28 writer uses OS-private registers")
    require(macro.index("call cc_obj1_validate_symbols") < macro.index("ld (ix+0),'O'")
            and macro.index("call cc_obj1_validate_relocs") < macro.index("ld (ix+0),'O'"),
            "P11.28 destination is touched before validation")
    require(macro.count("ld (cc_obj1_commit_marker),a") == 2,
            "P11.28 commit marker must have reset and one final commit store")

    golden = _golden()
    inspector = phase10_obj1_inspector.load_inspector(root)
    parsed = inspector.inspect_bytes(golden)
    require(parsed["magic"] == "OBJ1"
            and parsed["text_size"] == 3
            and parsed["bss_size"] == 7
            and parsed["symbol_count"] == 2
            and parsed["relocation_count"] == 1,
            "host OBJ1 inspector disagrees with P11.28 golden")
    require(parsed["symbols"][0]["name"] == "_start"
            and parsed["symbols"][1]["name"] == "ext"
            and parsed["relocations"][0]["offset"] == 0
            and parsed["relocations"][0]["symbol"] == 1,
            "host OBJ1 inspector detail mismatch")

    asm = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    fixture = build / "p1128-obj1.asm"
    golden_asm = ",".join("$" + f"{byte:02X}" for byte in golden)
    fixture.write_text(f"""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../include/obj1.inc"
    INCLUDE "../src/tools/cc.asm"
    ORG $C000
p1128_start:
    EMIT_P1128_CC_OBJ1_WRITER

p1128_text: db $01,$00,$C9
p1128_symbols:
    db "_start",0,0,0,0,0,0,0,0,0,0
    dw 0
    db 1,1
    db "ext",0,0,0,0,0,0,0,0,0,0,0,0,0
    dw 0
    db 0,1
p1128_relocs:
    dw 0
    dw 1
    db 1,0
p1128_output: defs 128,$CC
p1128_golden: db {golden_asm}

p1128_fail:
    ld a,E_FORMAT
    scf
    ret

p1128_set_state:
    ld hl,p1128_text
    ld (cc_obj1_text_ptr),hl
    ld hl,3
    ld (cc_obj1_text_size),hl
    ld hl,7
    ld (cc_obj1_bss_size),hl
    ld hl,p1128_symbols
    ld (cc_obj1_symbol_ptr),hl
    ld hl,2
    ld (cc_obj1_symbol_count),hl
    ld hl,p1128_relocs
    ld (cc_obj1_reloc_ptr),hl
    ld hl,1
    ld (cc_obj1_reloc_count),hl
    ld hl,p1128_output
    ld (cc_obj1_output_ptr),hl
    ld hl,128
    ld (cc_obj1_output_capacity),hl
    xor a
    ret

p1128_valid:
    call p1128_set_state
    call cc_obj1_write
    jp c,p1128_fail
    ld a,(cc_obj1_commit_marker)
    cp CC_OBJ1_COMMITTED
    jp nz,p1128_fail
    ld hl,(cc_obj1_output_size)
    ld de,{len(golden)}
    or a
    sbc hl,de
    jp nz,p1128_fail
    ld hl,p1128_output
    ld de,p1128_golden
    ld bc,{len(golden)}
p1128_compare:
    ld a,(de)
    cp (hl)
    jp nz,p1128_fail
    inc de
    inc hl
    dec bc
    ld a,b
    or c
    jr nz,p1128_compare
    xor a
    ret

p1128_malformed:
    call p1128_set_state
    ld hl,$8000
    ld (cc_obj1_text_size),hl
    ld hl,1
    ld (cc_obj1_bss_size),hl
    call cc_obj1_write
    jp nc,p1128_fail
    cp E_FORMAT
    jp nz,p1128_fail
    ld a,(cc_obj1_commit_marker)
    or a
    jp nz,p1128_fail
    ld hl,(cc_obj1_output_size)
    ld a,h
    or l
    jp nz,p1128_fail
    ld hl,p1128_output
    ld b,128
p1128_sentinel:
    ld a,(hl)
    cp $CC
    jp nz,p1128_fail
    inc hl
    djnz p1128_sentinel
    xor a
    ret

p1128_end:
    SAVEBIN "p1128-main.bin",p1128_start,p1128_end-p1128_start
""", encoding="utf-8", newline="\n")

    result = run_command(
        [asm, "--nologo", "--sym=p1128-obj1.sym", fixture.name],
        cwd=build, timeout_seconds=30
    )
    require(not result.timed_out and result.exit_code == 0,
            f"P11.28 assemble: {result.stderr or result.stdout}")
    main = (build / "p1128-main.bin").read_bytes()
    require(0 < len(main) <= 0x2000, "P11.28 fixture exceeds C000-DFFF")
    syms = phase3_open_descriptions._symbols(
        build / "p1128-obj1.sym", ("p1128_valid", "p1128_malformed")
    )

    assertions = [
        {"name": "native-writer-is-obj1-only-no-mex-shortcut", "passed": True},
        {"name": "host-inspector-exact-on-deterministic-golden", "passed": True},
        {"name": "obj1-text-bss-symbol-reloc-layout-exact", "passed": True},
        {"name": "body-and-header-crc-contract-exact", "passed": True},
        {"name": "all-internal-state-validation-precedes-output-mutation", "passed": True},
    ]
    commands = [result]

    if action == "test":
        def patch(ram):
            ram[0xC000 - 0x4000:0xC000 - 0x4000 + len(main)] = main

        for name in ("p1128_valid", "p1128_malformed"):
            code = (
                b"\xF3" + phase1._ld_sp(0xBFC0)
                + phase1._call(syms[name])
                + phase1._jp_c(FAIL_PC)
                + phase1._jp(PASS_PC)
            )
            try:
                commands.append(run_sna(root, code, patch=patch))
            except DriverError as exc:
                raise P1128Error(f"{name} native fixture failed: {exc}") from None

        assertions += [
            {"name": "fuse-native-writer-byte-equals-host-golden", "passed": True},
            {"name": "fuse-native-writer-sets-commit-only-after-complete-image", "passed": True},
            {"name": "fuse-malformed-state-preserves-destination-sentinel", "passed": True},
            {"name": "fuse-malformed-state-never-reports-committed-obj1", "passed": True},
        ]

    hashes = {
        "v1/src/tools/cc.asm": sha256_file(cc),
        "v1/build/p1128-main.bin": sha256_file(build / "p1128-main.bin"),
        "v1/tools-host/inspect-obj/inspect.py": sha256_file(root / "v1/tools-host/inspect-obj/inspect.py"),
        "v1/tools-host/test-driver/phase11_step_28.py": sha256_file(root / "v1/tools-host/test-driver/phase11_step_28.py"),
        "v1/dist/certification/P11.27.build.json": sha256_file(root / "v1/dist/certification/P11.27.build.json"),
        "v1/dist/certification/P11.27.test.json": sha256_file(root / "v1/dist/certification/P11.27.test.json"),
    }
    return commands, hashes, assertions
