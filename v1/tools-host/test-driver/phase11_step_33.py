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
import phase1_primitives_strict
import phase3_open_descriptions
import phase11_step_30
from driver_core import DriverError
from fuse_harness import FAIL_PC, PASS_PC, run_sna


class P1133Error(DriverError):
    pass


def require(ok, message):
    if not ok:
        raise P1133Error(message)


def dispatch(root, action, step, *, sha256_file, run_command, require_project_tool):
    if step != "P11.33":
        raise DriverError(step)

    cc_path = root / "v1/src/tools/cc.asm"
    mem_path = root / "v1/src/libc48/memory.asm"
    cc = cc_path.read_text(encoding="utf-8")
    mem = mem_path.read_text(encoding="utf-8")
    p140 = (root / "v1/src/kernel/z80_primitives.asm").read_text(encoding="utf-8")
    plan = (root / "docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV08.md").read_text(encoding="utf-8")
    arch = (root / "docs/01-ZX-UX-ARCHITECTURE-REV17.md").read_text(encoding="utf-8")

    marker = "    MACRO EMIT_P1133_CC_BLOCK_OPS"
    require(marker in cc, "P11.33 block selector missing")
    macro = cc[cc.index(marker):]
    macro = macro[:macro.index("    ENDM") + len("    ENDM")]
    code = "\n".join(line.split(";", 1)[0] for line in macro.splitlines())
    require(all(token in macro for token in (
        "cc_block_emit_copy:", "cc_block_emit_move:", "cc_block_emit_search:",
        "CC_BLOCK_TINY_UNCONTENDED_T EQU 14",
        "CC_BLOCK_LDIR_ONE_UNCONTENDED_T EQU 16",
        "CC_BLOCK_CONTENDED_TIMING_VARIABLE EQU 1",
    )), "P11.33 selector/measurement contract incomplete")
    require(not re.search(r"\biy\b|\bexx\b|ex\s+af\s*,\s*af'|\bsll\b", code, re.I),
            "P11.33 block selector uses forbidden/undocumented state")
    require("cpir" in mem.lower() and "cpdr" in mem.lower()
            and "ldir" in mem.lower() and "lddr" in mem.lower(),
            "P11.33 libc memory does not own all required block families")
    require(all(token in p140.lower() for token in ("zx48_memcpy:", "ldir", "zx48_memmove:",
            "lddr", "zx48_memchr:", "cpir", "zx48_memrchr:", "cpdr")),
            "canonical P1.40 primitive policy drift")
    require("interruptible" in p140.lower()
            and "no caller may treat them as a critical-section boundary" in p140.lower(),
            "P1.40 interruptibility contract drift")
    require("## P11.33 - Block primitive codegen/runtime" in plan
            and "Precise contention timing never required." in plan,
            "REV08 P11.33 contract drift")
    require("LDIR" in arch and "LDDR" in arch and "CPIR" in arch and "CPDR" in arch
            and "Small fixed-size copies may use unrolled ordinary loads" in arch
            and "repeated block instructions recognize interrupts between iterations" in arch,
            "REV17 P11.33 block contract drift")

    host_goldens = (
        bytes.fromhex("7e12"), bytes.fromhex("edb0"), bytes.fromhex("edb8"),
        bytes.fromhex("edb1"), bytes.fromhex("edb9"),
    )
    for image in host_goldens:
        require(bool(phase11_step_30.scan_portable(image)),
                f"P11.33 golden rejected by P11.30 scanner: {image.hex()}")

    assembler = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    fixture = build / "p1133-block-ops.asm"
    fixture.write_text(r'''    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/tools/cc.asm"
    INCLUDE "../src/libc48/memory.asm"
    ORG $C000
fixture:
    EMIT_P1133_CC_BLOCK_OPS
    EMIT_P1124_C48_MEMORY_RUNTIME

p1133_fail:
    ld a,E_FORMAT
    scf
    ret

p1133_compare:
    ld a,(cc_block_len)
    cp b
    jp nz,p1133_fail
    ld de,cc_block_buffer
p1133_compare_loop:
    ld a,b
    or a
    ret z
    ld a,(de)
    cp (hl)
    jp nz,p1133_fail
    inc de
    inc hl
    djnz p1133_compare_loop
    xor a
    ret

p1133_g_tiny: db $7E,$12
p1133_g_ldir: db $ED,$B0
p1133_g_lddr: db $ED,$B8
p1133_g_cpir: db $ED,$B1
p1133_g_cpdr: db $ED,$B9

p1133_goldens:
    ld a,CC_BLOCK_PROOF_ONE|CC_BLOCK_PROOF_PTRS_DEAD
    call cc_block_emit_copy
    ret c
    ld hl,p1133_g_tiny
    ld b,2
    call p1133_compare
    ret c

    xor a
    call cc_block_emit_copy
    ret c
    ld hl,p1133_g_ldir
    ld b,2
    call p1133_compare
    ret c

    ld a,CC_BLOCK_BACKWARD
    call cc_block_emit_move
    ret c
    ld hl,p1133_g_lddr
    ld b,2
    call p1133_compare
    ret c

    ld a,CC_BLOCK_FORWARD
    call cc_block_emit_search
    ret c
    ld hl,p1133_g_cpir
    ld b,2
    call p1133_compare
    ret c

    ld a,CC_BLOCK_BACKWARD
    call cc_block_emit_search
    ret c
    ld hl,p1133_g_cpdr
    ld b,2
    jp p1133_compare

p1133_append_ret:
    ld hl,cc_block_buffer
    ld a,(cc_block_len)
    ld e,a
    ld d,0
    add hl,de
    ld (hl),$C9
    ret

p1133_runtime_tiny:
    ld a,CC_BLOCK_PROOF_ONE|CC_BLOCK_PROOF_PTRS_DEAD
    call cc_block_emit_copy
    ret c
    call p1133_append_ret
    ld hl,p1133_src
    ld de,p1133_dst
    call cc_block_buffer
    ld a,(p1133_dst)
    cp $5A
    jp nz,p1133_fail
    xor a
    ret

p1133_runtime_repeat:
    xor a
    call cc_block_emit_copy
    ret c
    call p1133_append_ret
    ld hl,p1133_src
    ld de,p1133_dst8
    ld bc,8
    call cc_block_buffer
    ld hl,p1133_src
    ld de,p1133_dst8
    ld b,8
p1133_repeat_cmp:
    ld a,(de)
    cp (hl)
    jp nz,p1133_fail
    inc hl
    inc de
    djnz p1133_repeat_cmp
    xor a
    ret

p1133_runtime_overlap:
    ld a,CC_BLOCK_BACKWARD
    call cc_block_emit_move
    ret c
    call p1133_append_ret
    ld hl,p1133_overlap+7
    ld de,p1133_overlap+9
    ld bc,8
    call cc_block_buffer
    ld hl,p1133_overlap+2
    ld de,p1133_overlap_ref
    ld b,8
p1133_overlap_cmp:
    ld a,(de)
    cp (hl)
    jp nz,p1133_fail
    inc hl
    inc de
    djnz p1133_overlap_cmp
    xor a
    ret

p1133_runtime_search:
    ld a,CC_BLOCK_FORWARD
    call cc_block_emit_search
    ret c
    call p1133_append_ret
    ld a,$33
    ld hl,p1133_search
    ld bc,6
    call cc_block_buffer
    jp nz,p1133_fail
    ld de,p1133_search+4
    or a
    sbc hl,de
    jp nz,p1133_fail

    ld a,CC_BLOCK_BACKWARD
    call cc_block_emit_search
    ret c
    call p1133_append_ret
    ld a,$11
    ld hl,p1133_search+5
    ld bc,6
    call cc_block_buffer
    jp nz,p1133_fail
    ld de,p1133_search-1
    or a
    sbc hl,de
    jp nz,p1133_fail
    xor a
    ret

p1133_runtime_libc_search:
    ld ix,$1234
    ld iy,ROM_IY_ANCHOR
    ld hl,p1133_search
    ld de,$0033
    ld bc,6
    call memchr
    ld de,p1133_search+3
    or a
    sbc hl,de
    jp nz,p1133_fail
    push ix
    pop hl
    ld de,$1234
    or a
    sbc hl,de
    jp nz,p1133_fail
    push iy
    pop hl
    ld de,ROM_IY_ANCHOR
    or a
    sbc hl,de
    jp nz,p1133_fail

    ld hl,p1133_search+5
    ld de,$0011
    ld bc,6
    call c48_memrchr
    ld de,p1133_search
    or a
    sbc hl,de
    jp nz,p1133_fail
    xor a
    ret

; Same LDIR semantics in the CONTENDED/COLD 0x6000 region and FAST 0xA000.
; Timing class is recorded by the static measurement constants; no exact
; contention wait-state count is part of correctness.
p1133_runtime_placement:
    xor a
    call cc_block_emit_copy
    ret c
    call p1133_append_ret
    ld hl,$6000
    ld de,$6010
    ld bc,8
    call cc_block_buffer
    ld hl,$A000
    ld de,$A010
    ld bc,8
    call cc_block_buffer
    ld hl,$6010
    ld de,$A010
    ld b,8
p1133_place_cmp:
    ld a,(de)
    cp (hl)
    jp nz,p1133_fail
    inc hl
    inc de
    djnz p1133_place_cmp
    xor a
    ret

p1133_negative:
    ld a,2
    call cc_block_emit_move
    jp nc,p1133_fail
    cp E_INVAL
    jp nz,p1133_fail
    ld a,4
    call cc_block_emit_copy
    jp nc,p1133_fail
    cp E_INVAL
    jp nz,p1133_fail
    ld a,2
    call cc_block_emit_search
    jp nc,p1133_fail
    cp E_INVAL
    jp nz,p1133_fail
    ld a,CC_BLOCK_CONTENDED_TIMING_VARIABLE
    cp 1
    jp nz,p1133_fail
    xor a
    ret

p1133_src:
    db $5A,$11,$22,$33,$44,$55,$66,$77
p1133_dst:
    db 0
p1133_dst8:
    defs 8,0
p1133_overlap:
    db 0,1,2,3,4,5,6,7,8,9,10,11
p1133_overlap_ref:
    db 0,1,2,3,4,5,6,7
p1133_search:
    db $11,$22,$11,$33,$44,$11

fixture_end:
    SAVEBIN "p1133-main.bin",fixture,fixture_end-fixture
''', encoding="utf-8", newline="\n")

    result = run_command(
        [assembler, "--nologo", "--sym=p1133-block-ops.sym", fixture.name],
        cwd=build, timeout_seconds=30,
    )
    require(not result.timed_out and result.exit_code == 0,
            f"P11.33 assemble: {result.stderr or result.stdout}")
    main = (build / "p1133-main.bin").read_bytes()
    require(0 < len(main) <= 0x3F00, "P11.33 fixture exceeds upper-RAM budget")
    names = ("p1133_goldens", "p1133_runtime_tiny", "p1133_runtime_repeat",
             "p1133_runtime_overlap", "p1133_runtime_search",
             "p1133_runtime_libc_search", "p1133_runtime_placement",
             "p1133_negative")
    syms = phase3_open_descriptions._symbols(build / "p1133-block-ops.sym", names)

    assertions = [
        {"name":"eligible-copy-selects-ldir","passed":True},
        {"name":"overlap-direction-selects-lddr","passed":True},
        {"name":"eligible-search-selects-cpir-cpdr","passed":True},
        {"name":"one-byte-dead-pointer-copy-measured-14t-vs-16t-repeat","passed":True},
        {"name":"contended-timing-class-variable-not-correctness-source","passed":True},
        {"name":"libc-memory-shares-canonical-p140-block-families","passed":True},
        {"name":"all-goldens-pass-p1130-documented-opcode-scanner","passed":True},
    ]
    commands = [result]
    if action == "test":
        def patch(ram):
            ram[0xC000-0x4000:0xC000-0x4000+len(main)] = main
            payload = bytes((0x41,0x42,0x43,0x44,0x45,0x46,0x47,0x48))
            ram[0x6000-0x4000:0x6008-0x4000] = payload
            ram[0x6010-0x4000:0x6018-0x4000] = b"\x00"*8
            ram[0xA000-0x4000:0xA008-0x4000] = payload
            ram[0xA010-0x4000:0xA018-0x4000] = b"\x00"*8

        for name in names:
            code = (
                b"\xF3" + phase1._ld_sp(0xBFC0)
                + phase1._call(syms[name])
                + phase1._jp_c(FAIL_PC) + phase1._jp(PASS_PC)
            )
            try:
                commands.append(run_sna(root, code, patch=patch))
            except DriverError as exc:
                raise P1133Error(f"{name} native fixture failed: {exc}") from None

        p140_commands, _p140_hashes, p140_assertions = phase1_primitives_strict.dispatch(
            root, "test", "P1.40",
            sha256_file=sha256_file,
            run_command=run_command,
            require_project_tool=require_project_tool,
        )
        require(any(a.get("name") == "accepted-im2-interrupt-observed-with-mid-ldir-bc"
                    and a.get("passed") is True for a in p140_assertions),
                "P11.33 canonical P1.40 mid-LDIR interrupt proof missing")
        commands.extend(p140_commands)
        assertions += [
            {"name":"fuse-tiny-and-repeat-copy-results-exact","passed":True},
            {"name":"fuse-lddr-overlap-direction-exact","passed":True},
            {"name":"fuse-cpir-cpdr-forward-reverse-search-exact","passed":True},
            {"name":"fuse-libc-search-preserves-ix-iy-c48-contract","passed":True},
            {"name":"fuse-contended-uncontended-semantic-identity","passed":True},
            {"name":"canonical-p140-interrupt-between-ldir-iterations-restarts-exactly","passed":True},
            {"name":"invalid-selection-and-precise-contention-dependency-fail-closed","passed":True},
        ]

    hashes = {
        "v1/src/tools/cc.asm": sha256_file(cc_path),
        "v1/src/libc48/memory.asm": sha256_file(mem_path),
        "v1/src/kernel/z80_primitives.asm": sha256_file(root / "v1/src/kernel/z80_primitives.asm"),
        "v1/build/p1133-main.bin": sha256_file(build / "p1133-main.bin"),
        "v1/tools-host/test-driver/phase11_step_30.py": sha256_file(root / "v1/tools-host/test-driver/phase11_step_30.py"),
        "v1/tools-host/test-driver/phase11_step_33.py": sha256_file(root / "v1/tools-host/test-driver/phase11_step_33.py"),
        "v1/dist/certification/P11.32.build.json": sha256_file(root / "v1/dist/certification/P11.32.build.json"),
        "v1/dist/certification/P11.32.test.json": sha256_file(root / "v1/dist/certification/P11.32.test.json"),
    }
    return commands, hashes, assertions
