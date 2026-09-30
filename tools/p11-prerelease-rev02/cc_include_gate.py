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

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys


def req(value: bool, message: str) -> None:
    if not value:
        raise SystemExit("ERROR: " + message)


def run(argv, cwd: Path, env=None):
    p = subprocess.run([str(x) for x in argv], cwd=cwd, env=env, text=True,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    req(p.returncode == 0, "command failed: " + " ".join(map(str, argv)) + "\n" + p.stdout + "\n" + p.stderr)
    return p


def symbols(path: Path) -> dict[str, int]:
    out = {}
    for line in path.read_text().splitlines():
        if ": EQU 0x" not in line:
            continue
        name, raw = line.split(": EQU 0x", 1)
        try:
            out[name.strip()] = int(raw.strip(), 16)
        except ValueError:
            pass
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--assemble-only", action="store_true")
    ns = ap.parse_args()
    root = ns.root.resolve()
    out = ns.output.resolve()
    out.mkdir(parents=True, exist_ok=True)

    cc = (root / "v1/src/tools/cc.asm").read_text()
    block = cc.split("MACRO EMIT_REV02_CC_PRODUCT_CLI", 1)[1].split("ENDM", 1)[0]
    for needle in (
        "cc_rev02_pp_directive:", "cc_rev02_pp_name:", "SYS_STAT", "SYS_OPEN", "SYS_READ", "SYS_CLOSE",
        "CC_REV02_INCLUDE_CAP   EQU 64", "cc_rev02_includebuf", "cc_rev02_parent_read_left",
    ):
        req(needle in block, "quoted-include product closure missing: " + needle)
    for forbidden in ("cc_p11pr_", "CC_P11PR", "source_crc", "source_sum", "source_sha", "identity_table"):
        req(forbidden.lower() not in block.lower(), "source-specialized marker in product include closure: " + forbidden)

    asm = out / "cc-include-gate.asm"
    main_bin = out / "cc-include-main.bin"
    gate_bin = out / "cc-include-gateway.bin"
    sym = out / "cc-include-gate.sym"
    asm.write_text(f'''    DEVICE ZXSPECTRUM48
    INCLUDE "{(root / "v1/include/zx48ux.inc").as_posix()}"
    INCLUDE "{(root / "v1/src/tools/cc.asm").as_posix()}"
cc_product_bss EQU $A000
ROOT_HANDLE EQU 1
HEADER_HANDLE EQU 2
    ORG $4000
fixture_start:
    EMIT_P1128_CC_OBJ1_WRITER
    EMIT_P1129_CC_TRANSACTION_ROUTINES
    EMIT_REV02_CC_PRODUCT_CLI

root_done: db 0
header_done: db 0
open_count: db 0
close_count: db 0
stat_count: db 0
mode: db 0

root_source:
    db '#include "h.h"',10
    db 'int main(void){{return 7;}}',10
root_source_end:
header_source:
    db '/* included through ordinary target path */',10
header_source_end:
nested_header_source:
    db '#include "n.h"',10
    db 'int helper(void);',10
nested_header_source_end:
wrong_name_source:
    db '#include "../bad.h"',10
    db 'int main(void){{return 9;}}',10
wrong_name_source_end:

fixture_reset:
    xor a
    ld (root_done),a
    ld (header_done),a
    ld (open_count),a
    ld (close_count),a
    ld (stat_count),a
    ld a,ROOT_HANDLE
    ld (cc_rev02_source_handle),a
    ret

test_include_path_progress:
    xor a
    ld (mode),a
    call fixture_reset
    call cc_rev02_compile_stream
    ld a,(stat_count)
    cp 1
    jp nz,test_fail
    ld a,(open_count)
    cp 1
    jp nz,test_fail
    ld a,(header_done)
    cp 1
    jp nz,test_fail
    ld a,(close_count)
    cp 1
    jp nz,test_fail
    xor a
    ret

test_include_compile_only:
    xor a
    ld (mode),a
    call fixture_reset
    call cc_rev02_compile_stream
    ret

test_include_ok:
    xor a
    ld (mode),a
    call fixture_reset
    call cc_rev02_compile_stream
    ret c
    ld a,(open_count)
    cp 1
    jp nz,test_fail
    ld a,(close_count)
    cp 1
    jp nz,test_fail
    ld a,(stat_count)
    cp 1
    jp nz,test_fail
    ld hl,(cc_rev02_text_len)
    ld de,4
    or a
    sbc hl,de
    jp nz,test_fail
    ld hl,cc_rev02_text
    ld a,(hl)
    cp $21
    jp nz,test_fail
    inc hl
    ld a,(hl)
    cp 7
    jp nz,test_fail
    inc hl
    ld a,(hl)
    or a
    jp nz,test_fail
    inc hl
    ld a,(hl)
    cp $C9
    jp nz,test_fail
    ld hl,(cc_obj1_output_size)
    ld a,h
    or l
    jp z,test_fail
    xor a
    ret

test_nested_reject:
    ld a,1
    ld (mode),a
    call fixture_reset
    call cc_rev02_compile_stream
    jp nc,test_fail
    cp E_NOTSUP
    jp nz,test_fail
    xor a
    ret

test_bad_name_reject:
    ld a,2
    ld (mode),a
    call fixture_reset
    call cc_rev02_compile_stream
    jp nc,test_fail
    cp E_INVAL
    jp nz,test_fail
    ld a,(stat_count)
    or a
    jp nz,test_fail
    ld a,(open_count)
    or a
    jp nz,test_fail
    xor a
    ret

test_wrong_type_reject:
    ld a,3
    ld (mode),a
    call fixture_reset
    call cc_rev02_compile_stream
    jp nc,test_fail
    cp E_FORMAT
    jp nz,test_fail
    ld a,(stat_count)
    cp 1
    jp nz,test_fail
    ld a,(open_count)
    or a
    jp nz,test_fail
    xor a
    ret

test_fail:
    ld a,E_FORMAT
    scf
    ret

fixture_end:
    SAVEBIN "{main_bin.as_posix()}",fixture_start,fixture_end-fixture_start

    ORG $E000
gateway_start:
    cp SYS_READ
    jp z,gate_read
    cp SYS_STAT
    jp z,gate_stat
    cp SYS_OPEN
    jp z,gate_open
    cp SYS_CLOSE
    jp z,gate_close
    ld a,E_NOTSUP
    scf
    ret

gate_stat:
    ld a,(stat_count)
    inc a
    ld (stat_count),a
    ld e,(hl)
    inc hl
    ld d,(hl)
    inc hl
    ld c,(hl)
    inc hl
    ld b,(hl)
    ex de,hl
    ld a,(hl)
    cp 'h'
    jp nz,gate_bad
    inc hl
    ld a,(hl)
    cp '.'
    jp nz,gate_bad
    inc hl
    ld a,(hl)
    cp 'h'
    jp nz,gate_bad
    inc hl
    ld a,(hl)
    or a
    jp nz,gate_bad
    ld h,b
    ld l,c
    ld a,(mode)
    cp 3
    ld a,OBJ_C
    jr nz,gate_stat_type
    ld a,OBJ_DAT
gate_stat_type:
    ld (hl),a
    xor a
    ret

gate_open:
    ld a,(open_count)
    inc a
    ld (open_count),a
    ld a,(hl)
    cp 'h'
    jp nz,gate_bad
    ld hl,HEADER_HANDLE
    xor a
    ret

gate_close:
    ld a,(close_count)
    inc a
    ld (close_count),a
    xor a
    ret

gate_read:
    ld a,e
    cp ROOT_HANDLE
    jp z,gate_read_root
    cp HEADER_HANDLE
    jp z,gate_read_header
    jp gate_bad

gate_read_root:
    ld a,(root_done)
    or a
    jr nz,gate_read_eof
    ld a,1
    ld (root_done),a
    ex de,hl
    ld a,(mode)
    cp 2
    jr z,gate_read_bad_name
    ld hl,root_source
    ld bc,root_source_end-root_source
    ldir
    ld hl,root_source_end-root_source
    xor a
    ret
gate_read_bad_name:
    ld hl,wrong_name_source
    ld bc,wrong_name_source_end-wrong_name_source
    ldir
    ld hl,wrong_name_source_end-wrong_name_source
    xor a
    ret

gate_read_header:
    ld a,(header_done)
    or a
    jr nz,gate_read_eof
    ld a,1
    ld (header_done),a
    ex de,hl
    ld a,(mode)
    cp 1
    jr z,gate_read_nested
    ld hl,header_source
    ld bc,header_source_end-header_source
    ldir
    ld hl,header_source_end-header_source
    xor a
    ret
gate_read_nested:
    ld hl,nested_header_source
    ld bc,nested_header_source_end-nested_header_source
    ldir
    ld hl,nested_header_source_end-nested_header_source
    xor a
    ret

gate_read_eof:
    ld hl,0
    xor a
    ret

gate_bad:
    ld a,E_FORMAT
    scf
    ret

gateway_end:
    SAVEBIN "{gate_bin.as_posix()}",gateway_start,gateway_end-gateway_start
''', encoding="utf-8", newline="\n")

    sj = root / "tools/runtime/sjasmplus/bin/sjasmplus"
    req(sj.is_file(), "project assembler missing")
    run([sj, "--nologo", f"--sym={sym.as_posix()}", asm.as_posix()], out)
    req(main_bin.is_file() and gate_bin.is_file(), "fixture binaries missing")
    syms = symbols(sym)
    names = ("test_include_path_progress", "test_include_compile_only", "test_include_ok", "test_nested_reject", "test_bad_name_reject", "test_wrong_type_reject")
    for name in names:
        req(name in syms, "fixture symbol missing: " + name)

    checks = {"assemble": "PASS", "anti_specialization": "PASS"}
    if not ns.assemble_only:
        driver = root / "v1/tools-host/test-driver"
        sys.path.insert(0, str(driver))
        import phase1  # type: ignore
        from fuse_harness import FAIL_PC, PASS_PC, run_sna  # type: ignore
        main_bytes = main_bin.read_bytes()
        gate_bytes = gate_bin.read_bytes()

        def patch(ram: bytearray) -> None:
            ram[0:len(main_bytes)] = main_bytes
            start = 0xE000 - 0x4000
            ram[start:start + len(gate_bytes)] = gate_bytes

        for name in names:
            print("REV02 CC INCLUDE TEST " + name, flush=True)
            code = (b"\xF3" + phase1._ld_sp(0xBFC0) + phase1._call(syms[name])
                    + phase1._jp_c(FAIL_PC) + phase1._jp(PASS_PC))
            run_sna(root, code, patch=patch, timeout=20)
            checks[name] = "PASS"

    report = {
        "schema": 1,
        "kind": "rev02-stage-e-cc-quoted-include-gate",
        "status": "PASS",
        "checks": checks,
        "assertions": {
            "one_level_local_include": "PASS" if not ns.assemble_only else "ASSEMBLED",
            "ordinary_stat_open_read_close": "PASS" if not ns.assemble_only else "ASSEMBLED",
            "parent_unread_window_preserved": "PASS" if not ns.assemble_only else "ASSEMBLED",
            "nested_include_rejected": "PASS" if not ns.assemble_only else "ASSEMBLED",
            "portable_basename_enforced_before_lookup": "PASS" if not ns.assemble_only else "ASSEMBLED",
            "wrong_object_type_rejected_before_open": "PASS" if not ns.assemble_only else "ASSEMBLED",
            "source_identity_dispatch_absent": "PASS",
        },
    }
    (out / "CC-INCLUDE-GATE.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print("REV02 STAGE E CC QUOTED INCLUDE GATE PASS" + (" (ASSEMBLE-ONLY)" if ns.assemble_only else ""))


if __name__ == "__main__":
    main()
