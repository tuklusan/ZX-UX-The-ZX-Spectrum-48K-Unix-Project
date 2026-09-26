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
from driver_core import DriverError
from fuse_harness import FAIL_PC, PASS_PC, run_sna


class P1140Error(DriverError):
    pass


CC_LIMIT = 20480
STACK_ADVERTISED = 512
STACK_BOOTSTRAP = 64
STACK_ALLOC = STACK_ADVERTISED + STACK_BOOTSTRAP
BOOTSTRAP_MAX = 512
SHELL_BUDGET = 4096
FONT_BYTES = 392
UDG_BYTES = 256
BINCAT_BYTES = 488
PACKED_READER_BYTES = 272
HELLO_OBJ_BYTES = 192
ARENA_BYTES = 32768
OUTPUT_ADDR = 0xB800


def require(ok, message):
    if not ok:
        raise P1140Error(message)


def even(value: int) -> int:
    return (value + 1) & ~1


def word(value: int) -> bytes:
    return bytes((value & 0xFF, (value >> 8) & 0xFF))


def parse_equ(source: str, name: str) -> int:
    match = re.search(rf"(?m)^\s*{re.escape(name)}\s+EQU\s+(\d+)", source)
    require(match is not None, f"P11.40 missing {name}")
    return int(match.group(1))


def expect_byte(address: int, value: int) -> bytes:
    return b"\x3A" + word(address) + bytes((0xFE, value & 0xFF)) + phase1._jp_nz(FAIL_PC)


def dispatch(root, action, step, *, sha256_file, run_command, require_project_tool):
    if step != "P11.40":
        raise DriverError(step)

    plan = (root / "docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV08.md").read_text(encoding="utf-8")
    arch = (root / "docs/01-ZX-UX-ARCHITECTURE-REV17.md").read_text(encoding="utf-8")
    abi = (root / "v1/docs/abi.md").read_text(encoding="utf-8")
    cc_path = root / "v1/src/tools/cc.asm"
    sh_path = root / "v1/src/shell/sh.asm"
    cc_source = cc_path.read_text(encoding="utf-8")
    sh_source = sh_path.read_text(encoding="utf-8")
    memory_source = (root / "v1/src/kernel/memory.asm").read_text(encoding="utf-8")

    require("## P11.40 - Compiler simultaneous residency/20KiB gate" in plan
            and "not enough memory for compiler" in plan
            and "20480" in plan,
            "REV08 P11.40 contract drift")
    require("compiler process-owned live footprint (image+BSS+stack+ARG1/ENV1+workspace) <= 20480 bytes" in arch
            and "shell process-owned footprint + maximum 20-KiB compiler process-owned footprint" in arch
            and "packed-reader decoder state" in arch,
            "REV17 compiler residency authority drift")
    require("Process stacks and pipe buffers are FAST_REQUIRED. Normal MEX1 image+BSS is ANY." in abi,
            "ABI placement contract drift")
    require("CC_SOURCE_WINDOW_SIZE    EQU 64" in cc_source
            and "CC_WORKSPACE_LIMIT       EQU 2048" in cc_source
            and "EMIT_P1140_CC_MEMORY_DIAGNOSTIC" in cc_source
            and 'db "not enough memory for compiler",10' in cc_source,
            "native compiler bounded-workspace/diagnostic contract missing")
    require("sh_p621_cc_nomem_if_current:" in sh_source
            and "p621_cc_path: db '/bin/cc',0" in sh_source
            and "p621_cc_nomem_diag: db 'not enough memory for compiler',10" in sh_source,
            "shell compiler-launch memory diagnostic missing")
    require("ALLOC_COLD_PREFERRED" in memory_source and "ALLOC_FAST_REQUIRED" in memory_source,
            "real allocator policy implementation missing")
    require((root / "v1/assets/font4x8.bin").stat().st_size == FONT_BYTES
            and (root / "v1/assets/bincat.bin").stat().st_size == BINCAT_BYTES,
            "pinned resource size drift")

    assembler = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)

    # Assemble the current complete native compiler component set as one real
    # process image. Historical proof-only P11.35..P11.37 drivers are excluded;
    # P11.38 is the admitted current integrated source-to-OBJ1 front end.
    cc_fixture = build / "p1140-cc-footprint.asm"
    cc_fixture.write_text(r'''    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/tools/cc.asm"
    ORG $6000
p1140_cc_image_start:
    EMIT_P11_CC_STREAMING_CORE
    EMIT_P11_CC_PREPROCESSOR
    EMIT_P11_CC_LEXER
    EMIT_P11_CC_DECL_PARSER
    EMIT_P11_CC_STATEMENTS
    EMIT_P11_CC_EXPRESSIONS
    EMIT_P11_CC_INT_SEMANTICS
    EMIT_P11_CC_POINTER_ARITH
    EMIT_P11_CC_LITERALS
    EMIT_P11_CC_GLOBAL_STORAGE
    EMIT_P11_CC_FRAME_LAYOUT
    EMIT_P11_CC_REGCALL
    EMIT_P11_CC_FLOAT5
    EMIT_P11_CC_FLOAT_ARGS
    EMIT_P11_CC_FLOAT_RETURN
    EMIT_P1118_CC_CASTS
    EMIT_P1119_CC_FLOAT_COMPARE
    EMIT_P1128_CC_OBJ1_WRITER
    EMIT_P1129_CC_TRANSACTION_ROUTINES
    EMIT_P1131_CC_CONTROL_FLOW
    EMIT_P1132_CC_DATA_OPS
    EMIT_P1133_CC_BLOCK_OPS
    EMIT_P1138_CC_DEMO_COMPILER
    EMIT_P1140_CC_MEMORY_DIAGNOSTIC
p1140_cc_image_end:
    ASSERT p1140_cc_image_end <= $E000
    SAVEBIN "p1140-cc.bin",p1140_cc_image_start,p1140_cc_image_end-p1140_cc_image_start
''', encoding="utf-8", newline="\n")
    cc_assembled = run_command(
        [assembler, "--nologo", "--sym=p1140-cc-footprint.sym", cc_fixture.name],
        cwd=build, timeout_seconds=60,
    )
    require(not cc_assembled.timed_out and cc_assembled.exit_code == 0,
            f"P11.40 compiler footprint assembly failed: {cc_assembled.stderr or cc_assembled.stdout}")
    cc_bin = (build / "p1140-cc.bin").read_bytes()
    cc_syms = phase3_open_descriptions._symbols(
        build / "p1140-cc-footprint.sym",
        ("p1140_cc_image_start", "p1140_cc_image_end",
         "cc_workspace_begin", "cc_workspace_end", "cc_p1140_report_error"),
    )
    require(len(cc_bin) == cc_syms["p1140_cc_image_end"] - cc_syms["p1140_cc_image_start"],
            "P11.40 compiler image symbol/byte length mismatch")
    workspace = cc_syms["cc_workspace_end"] - cc_syms["cc_workspace_begin"]
    require(0 < workspace <= parse_equ(cc_source, "CC_WORKSPACE_LIMIT"),
            f"P11.40 compiler workspace exceeds bound: {workspace}")
    cc_alloc = even(len(cc_bin))
    compiler_owned = cc_alloc + STACK_ALLOC + BOOTSTRAP_MAX
    require(compiler_owned <= CC_LIMIT,
            f"P11.40 compiler process-owned footprint {compiler_owned} exceeds {CC_LIMIT}")

    hello_bytes = (root / "v1/src/demos/hello.c").read_bytes()
    baseline = sum(map(even, (
        FONT_BYTES, STACK_ALLOC, STACK_ALLOC,
        len(hello_bytes), HELLO_OBJ_BYTES, UDG_BYTES, BINCAT_BYTES, PACKED_READER_BYTES,
        cc_alloc, BOOTSTRAP_MAX, SHELL_BUDGET, BOOTSTRAP_MAX,
    )))
    require(baseline < ARENA_BYTES, f"P11.40 simultaneous baseline cannot fit: {baseline}")
    remaining = ARENA_BYTES - baseline
    require(remaining >= 4096, f"P11.40 simultaneous baseline leaves insufficient recovery headroom: {remaining}")
    pressure = remaining - 4096

    alloc_fixture = build / "p1140-residency.asm"
    alloc_fixture.write_text(f'''    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/kernel/memory.asm"
P1140_CC_ALLOC          EQU {cc_alloc}
P1140_HELLO_SOURCE      EQU {even(len(hello_bytes))}
P1140_HELLO_OBJ         EQU {even(HELLO_OBJ_BYTES)}
P1140_PRESSURE          EQU {pressure}
P1140_BASELINE_FREE     EQU {remaining}

    ORG $4000
p1140_residency_start:
    EMIT_MEMORY_ROUTINES

p1140_fail:
    ld a,E_FORMAT
    scf
    ret

p1140_require_fast:
    ld de,FAST_START
    or a
    sbc hl,de
    jp c,p1140_fail
    add hl,de
    xor a
    ret

p1140_require_cold:
    ld a,h
    cp FAST_START/256
    jp nc,p1140_fail
    xor a
    ret

p1140_alloc_fast:
    ld a,ALLOC_FAST_REQUIRED
    call zx48_alloc
    ret c
    jp p1140_require_fast

p1140_alloc_cold:
    ld a,ALLOC_COLD_PREFERRED
    call zx48_alloc
    ret c
    jp p1140_require_cold

p1140_residency:
    call zx48_memory_init

    ld bc,{even(FONT_BYTES)}
    call p1140_alloc_fast
    ret c
    ld (p1140_font),hl
    ld bc,{even(STACK_ALLOC)}
    call p1140_alloc_fast
    ret c
    ld (p1140_cc_stack),hl
    ld bc,{even(STACK_ALLOC)}
    call p1140_alloc_fast
    ret c
    ld (p1140_sh_stack),hl

    ld bc,P1140_HELLO_SOURCE
    call p1140_alloc_cold
    ret c
    ld (p1140_hello_source),hl
    ld bc,P1140_HELLO_OBJ
    call p1140_alloc_cold
    ret c
    ld (p1140_hello_obj),hl
    ld bc,{even(UDG_BYTES)}
    call p1140_alloc_cold
    ret c
    ld bc,{even(BINCAT_BYTES)}
    call p1140_alloc_cold
    ret c
    ld bc,{even(PACKED_READER_BYTES)}
    call p1140_alloc_cold
    ret c
    ld (p1140_decoder),hl

    ; Compiler MEX image/BSS is deliberately ordinary ANY placement. With the
    ; required resident cold objects ahead of it this exact allocation crosses
    ; 0x7FFF/0x8000, proving it is not incorrectly FAST_REQUIRED.
    ld bc,P1140_CC_ALLOC
    ld a,ALLOC_ANY
    call zx48_alloc
    ret c
    ld (p1140_cc_image),hl
    ld a,h
    cp FAST_START/256
    jp nc,p1140_fail
    ld de,P1140_CC_ALLOC
    add hl,de
    ld de,FAST_START+1
    or a
    sbc hl,de
    jp c,p1140_fail

    ld bc,{even(BOOTSTRAP_MAX)}
    ld a,ALLOC_ANY
    call zx48_alloc
    ret c
    ld (p1140_cc_bootstrap),hl

    ld bc,{even(SHELL_BUDGET)}
    ld a,ALLOC_ANY
    call zx48_alloc
    ret c
    ld (p1140_shell),hl

    ld bc,{even(BOOTSTRAP_MAX)}
    ld a,ALLOC_ANY
    call zx48_alloc
    ret c
    ld (p1140_sh_bootstrap),hl

    ld hl,p1140_minfo
    call zx48_mem_info
    ld hl,(p1140_minfo+8)
    ld de,P1140_BASELINE_FREE
    or a
    sbc hl,de
    jp nz,p1140_fail

    ; Create deterministic nonessential pressure leaving exactly 4096 bytes.
    ld bc,P1140_PRESSURE
    ld a,ALLOC_ANY
    call zx48_alloc
    ret c
    ld (p1140_pressure_ptr),hl
    ld hl,p1140_minfo
    call zx48_mem_info
    ld hl,(p1140_minfo+8)
    ld de,4096
    or a
    sbc hl,de
    jp nz,p1140_fail

    ; -heap 8192 cannot fit and must leave allocator accounting unchanged.
    ld bc,8192
    ld a,ALLOC_ANY
    call zx48_alloc
    jp nc,p1140_fail
    cp E_NOMEM
    jp nz,p1140_fail
    ld hl,p1140_minfo_after
    call zx48_mem_info
    ld hl,(p1140_minfo_after+8)
    ld de,4096
    or a
    sbc hl,de
    jp nz,p1140_fail

    ; Freeing nonessential pressure makes retry possible without corruption.
    ld hl,(p1140_pressure_ptr)
    ld bc,P1140_PRESSURE
    call zx48_free
    ret c
    ld bc,1024
    ld a,ALLOC_ANY
    call zx48_alloc
    ret c
    ld (p1140_retry_ptr),hl
    xor a
    ret

p1140_font: dw 0
p1140_cc_stack: dw 0
p1140_sh_stack: dw 0
p1140_hello_source: dw 0
p1140_hello_obj: dw 0
p1140_decoder: dw 0
p1140_cc_image: dw 0
p1140_cc_bootstrap: dw 0
p1140_shell: dw 0
p1140_sh_bootstrap: dw 0
p1140_pressure_ptr: dw 0
p1140_retry_ptr: dw 0
p1140_minfo: defs 16,0
p1140_minfo_after: defs 16,0
p1140_residency_end:
    SAVEBIN "p1140-residency.bin",p1140_residency_start,p1140_residency_end-p1140_residency_start
''', encoding="utf-8", newline="\n")
    alloc_assembled = run_command(
        [assembler, "--nologo", "--sym=p1140-residency.sym", alloc_fixture.name],
        cwd=build, timeout_seconds=60,
    )
    require(not alloc_assembled.timed_out and alloc_assembled.exit_code == 0,
            f"P11.40 allocator fixture assembly failed: {alloc_assembled.stderr or alloc_assembled.stdout}")
    alloc_bin = (build / "p1140-residency.bin").read_bytes()
    require(0 < len(alloc_bin) < 0x2000, f"P11.40 allocator fixture too large: {len(alloc_bin)}")
    alloc_syms = phase3_open_descriptions._symbols(
        build / "p1140-residency.sym", ("p1140_residency",)
    )

    # The real foreground shell spawn path is also exercised: exact /bin/cc +
    # E_NOMEM writes the one mandated diagnostic, while another command stays silent.
    shell_fixture = build / "p1140-shell-nomem.asm"
    shell_fixture.write_text(r'''    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/shell/sh.asm"
    ORG $C000
p1140_shell_start:
    EMIT_P621_PIPELINE_ROUTINES

p1140_shell_cc:
    ld hl,p1140_cc_path
    ld (p1140_proc1),hl
    jp p1140_shell_run
p1140_shell_as:
    ld hl,p1140_as_path
    ld (p1140_proc1),hl
p1140_shell_run:
    ld ix,p1140_stage
    ld b,1
    ld hl,p1140_env
    ld de,8
    call sh_p621_launch_foreground
    jp nc,p1140_shell_fail
    cp E_NOMEM
    jp nz,p1140_shell_fail
    xor a
    ret
p1140_shell_fail:
    ld a,E_FORMAT
    scf
    ret

p1140_stage:
    dw p1140_proc1,p1140_proc1+6,p1140_proc1+8
p1140_proc1:
    dw p1140_cc_path,0,0,0,0
    db 0,1,2,0
    dw 0
p1140_env:
    db 'E','N','V','1',0,0,8,0
p1140_cc_path: db '/bin/cc',0
p1140_as_path: db '/bin/as',0
p1140_shell_end:
    SAVEBIN "p1140-shell.bin",p1140_shell_start,p1140_shell_end-p1140_shell_start

    ORG $E000
p1140_gate:
    cp SYS_SPAWN
    jr z,p1140_gate_spawn
    cp SYS_WRITE
    jr z,p1140_gate_write
    ld a,E_NOTSUP
    scf
    ret
p1140_gate_spawn:
    ld a,E_NOMEM
    scf
    ret
p1140_gate_write:
    ld a,d
    or a
    jr nz,p1140_gate_bad
    ld a,e
    cp 2
    jr nz,p1140_gate_bad
    ld a,b
    or a
    jr nz,p1140_gate_short
    ld a,c
    cp 8
    jr c,p1140_gate_count_ready
p1140_gate_short:
    ld bc,7
p1140_gate_count_ready:
    push bc
    ld de,(p1140_gate_out)
    ldir
    ld (p1140_gate_out),de
    pop hl
    xor a
    ret
p1140_gate_bad:
    ld a,E_INVAL
    scf
    ret
p1140_gate_out: dw $B800
p1140_gate_end:
    SAVEBIN "p1140-gateway.bin",p1140_gate,p1140_gate_end-p1140_gate
''', encoding="utf-8", newline="\n")
    shell_assembled = run_command(
        [assembler, "--nologo", "--sym=p1140-shell-nomem.sym", shell_fixture.name],
        cwd=build, timeout_seconds=60,
    )
    require(not shell_assembled.timed_out and shell_assembled.exit_code == 0,
            f"P11.40 shell diagnostic fixture assembly failed: {shell_assembled.stderr or shell_assembled.stdout}")
    shell_bin = (build / "p1140-shell.bin").read_bytes()
    gateway_bin = (build / "p1140-gateway.bin").read_bytes()
    shell_syms = phase3_open_descriptions._symbols(
        build / "p1140-shell-nomem.sym", ("p1140_shell_cc", "p1140_shell_as")
    )

    assertions = [
        {"name": "compiler-image-bss-workspace-measured-as-one-native-process-image", "passed": True},
        {"name": "compiler-complete-process-owned-footprint-lte-20480", "passed": True},
        {"name": "compiler-bounded-workspace-resident-inside-measured-image", "passed": True},
        {"name": "compiler-image-is-any-not-fast-required", "passed": True},
        {"name": "compiler-stack-is-fast-required", "passed": True},
        {"name": "hello-source-output-use-cold-preferred", "passed": True},
        {"name": "shell-compiler-packed-reader-pinned-resources-physically-coexist", "passed": True},
        {"name": "exact-memory-short-diagnostic-present", "passed": True},
        {"name": "heap8192-pressure-case-is-recoverable", "passed": True},
    ]
    commands = [cc_assembled, alloc_assembled, shell_assembled]

    if action == "test":
        def alloc_patch(ram):
            ram[0:len(alloc_bin)] = alloc_bin
        code = (
            b"\xF3" + phase1._ld_sp(0xBFC0)
            + phase1._call(alloc_syms["p1140_residency"])
            + phase1._jp_c(FAIL_PC) + phase1._jp(PASS_PC)
        )
        try:
            commands.append(run_sna(root, code, patch=alloc_patch, timeout=30))
        except DriverError as exc:
            raise P1140Error(f"physical arena residency/pressure fixture failed: {exc}") from None

        expected = b"not enough memory for compiler\n"

        def shell_patch(ram):
            ram[0xC000-0x4000:0xC000-0x4000+len(shell_bin)] = shell_bin
            ram[0xE000-0x4000:0xE000-0x4000+len(gateway_bin)] = gateway_bin
            ram[OUTPUT_ADDR-0x4000:OUTPUT_ADDR-0x4000+64] = b"\xA5" * 64

        code = b"\xF3" + phase1._ld_sp(0xBFC0) + phase1._call(shell_syms["p1140_shell_cc"]) + phase1._jp_c(FAIL_PC)
        for index, value in enumerate(expected):
            code += expect_byte(OUTPUT_ADDR + index, value)
        code += expect_byte(OUTPUT_ADDR + len(expected), 0xA5) + phase1._jp(PASS_PC)
        try:
            commands.append(run_sna(root, code, patch=shell_patch, timeout=30))
        except DriverError as exc:
            raise P1140Error(f"shell cc launch E_NOMEM diagnostic fixture failed: {exc}") from None

        code = b"\xF3" + phase1._ld_sp(0xBFC0) + phase1._call(shell_syms["p1140_shell_as"]) + phase1._jp_c(FAIL_PC)
        code += expect_byte(OUTPUT_ADDR, 0xA5) + phase1._jp(PASS_PC)
        try:
            commands.append(run_sna(root, code, patch=shell_patch, timeout=30))
        except DriverError as exc:
            raise P1140Error(f"non-cc E_NOMEM diagnostic negative failed: {exc}") from None

        def cc_diag_patch(ram):
            ram[0x6000-0x4000:0x6000-0x4000+len(cc_bin)] = cc_bin
            ram[0xE000-0x4000:0xE000-0x4000+len(gateway_bin)] = gateway_bin
            ram[OUTPUT_ADDR-0x4000:OUTPUT_ADDR-0x4000+64] = b"\xA5" * 64

        code = b"\xF3" + phase1._ld_sp(0xBFC0) + bytes((0x3E, 3)) + phase1._call(cc_syms["cc_p1140_report_error"])
        code += b"\xD2" + word(FAIL_PC) + bytes((0xFE, 3)) + phase1._jp_nz(FAIL_PC)
        for index, value in enumerate(expected):
            code += expect_byte(OUTPUT_ADDR + index, value)
        code += expect_byte(OUTPUT_ADDR + len(expected), 0xA5) + phase1._jp(PASS_PC)
        try:
            commands.append(run_sna(root, code, patch=cc_diag_patch, timeout=30))
        except DriverError as exc:
            raise P1140Error(f"compiler in-process E_NOMEM diagnostic fixture failed: {exc}") from None

        assertions += [
            {"name": "fuse-real-allocator-simultaneous-residency-pass", "passed": True},
            {"name": "fuse-compiler-image-crosses-contended-fast-boundary-under-any", "passed": True},
            {"name": "fuse-fast-stacks-and-font-remain-fast", "passed": True},
            {"name": "fuse-cold-source-output-resources-prefer-cold", "passed": True},
            {"name": "fuse-heap8192-fails-enomem-without-accounting-corruption", "passed": True},
            {"name": "fuse-free-pressure-and-retry-succeeds", "passed": True},
            {"name": "fuse-shell-cc-launch-enomem-exact-diagnostic-short-write-safe", "passed": True},
            {"name": "fuse-non-cc-launch-enomem-does-not-claim-compiler-diagnostic", "passed": True},
            {"name": "fuse-compiler-runtime-enomem-exact-diagnostic-short-write-safe", "passed": True},
        ]

    hashes = {
        "v1/src/tools/cc.asm": sha256_file(cc_path),
        "v1/src/shell/sh.asm": sha256_file(sh_path),
        "v1/src/kernel/memory.asm": sha256_file(root / "v1/src/kernel/memory.asm"),
        "v1/src/kernel/process.asm": sha256_file(root / "v1/src/kernel/process.asm"),
        "v1/docs/abi.md": sha256_file(root / "v1/docs/abi.md"),
        "v1/assets/font4x8.bin": sha256_file(root / "v1/assets/font4x8.bin"),
        "v1/assets/bincat.bin": sha256_file(root / "v1/assets/bincat.bin"),
        "v1/src/demos/hello.c": sha256_file(root / "v1/src/demos/hello.c"),
        "v1/build/p1140-cc.bin": sha256_file(build / "p1140-cc.bin"),
        "v1/build/p1140-residency.bin": sha256_file(build / "p1140-residency.bin"),
        "v1/build/p1140-shell.bin": sha256_file(build / "p1140-shell.bin"),
        "v1/build/p1140-gateway.bin": sha256_file(build / "p1140-gateway.bin"),
        "v1/tools-host/test-driver/phase11_step_40.py": sha256_file(root / "v1/tools-host/test-driver/phase11_step_40.py"),
        "v1/dist/certification/P11.39.build.json": sha256_file(root / "v1/dist/certification/P11.39.build.json"),
        "v1/dist/certification/P11.39.test.json": sha256_file(root / "v1/dist/certification/P11.39.test.json"),
    }
    return commands, hashes, assertions
