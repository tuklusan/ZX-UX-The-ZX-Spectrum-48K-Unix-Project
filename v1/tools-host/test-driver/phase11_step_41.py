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


class P1141Error(DriverError):
    """Fail closed on any built-in c48.h contract or evidence drift."""


def require(ok, message):
    if not ok:
        raise P1141Error(message)


SPECS = (
    ("exit","void",("int",)), ("yield","int",()), ("sleep","int",("uint",)),
    ("spawn","int",("voidp",)), ("wait","int",("voidp",)), ("kill","int",("int",)),
    ("chdir","int",("charp",)), ("getcwd","int",("charp","uint")),
    ("getenv","charp",("charp",)), ("getpid","int",()),
    ("open","int",("charp","int")), ("open_typed","int",("charp","int","int")),
    ("close","int",("int",)), ("read","int",("int","voidp","uint")),
    ("write","int",("int","voidp","uint")), ("seek","int",("int","uint")),
    ("stat","int",("charp","voidp")), ("remove","int",("charp",)),
    ("rename","int",("charp","charp")), ("list","int",("charp","int","voidp")),
    ("pipe","int",("ucharp",)), ("dup","int",("int","int")),
    ("ioctl","int",("int","int","voidp")), ("read_full","int",("int","voidp","uint")),
    ("write_full","int",("int","voidp","uint")),
    ("getchar","int",()), ("putchar","int",("int",)), ("puts","int",("charp",)),
    ("strlen","uint",("charp",)), ("strcmp","int",("charp","charp")),
    ("strcpy","charp",("charp","charp")), ("strncpy","charp",("charp","charp","uint")),
    ("memcpy","voidp",("voidp","voidp","uint")), ("memmove","voidp",("voidp","voidp","uint")),
    ("memchr","voidp",("voidp","int","uint")), ("memset","voidp",("voidp","int","uint")),
    ("malloc","voidp",("uint",)), ("free","void",("voidp",)),
    ("cls","int",()), ("print_at","int",("int","int","charp")),
    ("plot","int",("int","int")), ("point","int",("int","int")),
    ("draw","int",("int","int","int","int")), ("circle","int",("int","int","int")),
    ("ink","int",("int",)), ("paper","int",("int",)), ("bright","int",("int",)),
    ("flash","int",("int",)), ("inverse","int",("int",)), ("over","int",("int",)),
    ("border","int",("int",)), ("beep","int",("float","float")),
    ("udg_define","int",("int","ucharp")), ("udg_get","int",("int","ucharp")),
    ("udg_draw","int",("int","int","int")), ("udg_clear","int",("int",)),
    ("udg_draw_2x2","int",("int","int","int")),
    ("tape_save","int",("charp",)), ("tape_load","int",("charp",)),
    ("ticks","uint",()), ("time_get","int",("voidp",)), ("time_set","int",("voidp",)),
    ("sin","float",("float",)), ("cos","float",("float",)), ("tan","float",("float",)),
    ("asin","float",("float",)), ("acos","float",("float",)), ("atan","float",("float",)),
    ("sqrt","float",("float",)), ("exp","float",("float",)), ("log","float",("float",)),
    ("pow","float",("float","float")), ("fabs","float",("float",)),
)

SPELL = {
    "void":"void", "char":"char", "uchar":"unsigned char", "short":"short",
    "ushort":"unsigned short", "int":"int", "uint":"unsigned int", "float":"float",
    "voidp":"void*", "charp":"char*", "ucharp":"unsigned char*",
}
TYPE = {
    "void":(0,0), "char":(1,0), "uchar":(2,0), "short":(3,0),
    "ushort":(4,0), "int":(5,0), "uint":(6,0), "float":(7,0),
    "voidp":(0,1), "charp":(1,1), "ucharp":(2,1),
}
RET_CLASS = {"void":0, "char":1, "uchar":1, "short":2, "ushort":2,
             "int":2, "uint":2, "float":3, "voidp":2, "charp":2, "ucharp":2}


def decl(spec):
    name, ret, args = spec
    params = "void" if not args else ",".join(SPELL[x] for x in args)
    return f"{SPELL[ret]} {name}({params});"


DECLS = tuple(decl(x) for x in SPECS)
HEADER_BYTES = sum(len(x) + 1 for x in DECLS)
CC_LIMIT = 20480
STACK_ALLOC = 576
BOOTSTRAP_MAX = 512


def constants(text):
    return {n:int(v) for n,v in re.findall(r"(?m)^\s*([A-Z0-9_]+)\s+EQU\s+([0-9]+)\s*$", text)}


def normalize_sdk_decl(line):
    line = line.strip()
    m = re.match(r"^(void|int|unsigned int|char \*|void \*|float)\s*([A-Za-z_][A-Za-z0-9_]*)\((.*)\);$", line)
    if not m:
        return None
    ret, name, params = m.groups()
    ret = ret.replace(" *", "*")
    if params == "void":
        args = ()
    else:
        out = []
        for raw in params.split(","):
            p = raw.strip()
            pm = re.match(r"^(unsigned char|unsigned int|void|char|int|float)\s*(\*)?\s*([A-Za-z_][A-Za-z0-9_]*)$", p)
            require(pm is not None, f"P11.41 cannot normalize SDK declaration parameter: {p}")
            base, star, _ = pm.groups()
            out.append(base + ("*" if star else ""))
        args = tuple(out)
    return ret, name, args


def expected_normalized(spec):
    name, ret, args = spec
    return SPELL[ret], name, tuple(SPELL[x] for x in args)


RUNTIME_FILES = {
    "v1/src/libc48/syscall.asm": ("exit","yield","sleep","spawn","wait","kill","chdir","getcwd","getenv","getpid"),
    "v1/src/libc48/io.asm": ("open","open_typed","close","read","write","seek","stat","remove","rename","list","pipe","dup","ioctl","read_full","write_full"),
    "v1/src/libc48/string.asm": ("getchar","putchar","puts","strlen","strcmp","strcpy","strncpy"),
    "v1/src/libc48/memory.asm": ("memcpy","memmove","memchr","memset","malloc","free"),
    "v1/src/libc48/graphics.asm": ("cls","print_at","plot","point","draw","circle","ink","paper","bright","flash","inverse","over","border"),
    "v1/src/libc48/sound.asm": ("beep",),
    "v1/src/libc48/udg.asm": ("udg_define","udg_get","udg_draw","udg_clear","udg_draw_2x2"),
    "v1/src/libc48/tape.asm": ("tape_save","tape_load","ticks","time_get","time_set"),
    "v1/src/libc48/math_runtime.asm": ("sin","cos","tan","asin","acos","atan","sqrt","exp","log","pow","fabs"),
}


def asm_cases():
    lines = []
    for i, spec in enumerate(SPECS):
        d = decl(spec)
        lines += [f'p1141_decl_{i}: db "{d}"', f"p1141_decl_{i}_end:"]
    lines.append("p1141_cases:")
    for i, (_, ret, args) in enumerate(SPECS):
        rb, rp = TYPE[ret]
        param = []
        for arg in args:
            param.extend(TYPE[arg])
        param += [0] * (16 - len(param))
        values = ",".join(str(x) for x in (rb, rp, RET_CLASS[ret], len(args), *param))
        lines.append(f"    dw p1141_decl_{i},p1141_decl_{i}_end-p1141_decl_{i}")
        lines.append(f"    db {values}")
    return "\n".join(lines)


def dispatch(root, action, step, *, sha256_file, run_command, require_project_tool):
    if step != "P11.41":
        raise DriverError(step)
    require(len(SPECS) == 73 and len({x[0] for x in SPECS}) == 73,
            "P11.41 exact public declaration count/name uniqueness drift")

    source = root / "v1/src/tools/cc.asm"
    text = source.read_text(encoding="utf-8")
    doc = (root / "v1/docs/c48.md").read_text(encoding="utf-8")
    plan = (root / "docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV08.md").read_text(encoding="utf-8")
    arch = (root / "docs/01-ZX-UX-ARCHITECTURE-REV17.md").read_text(encoding="utf-8")
    c = constants(text)
    require({k:c.get(k) for k in ("CC_TYPE_VOID","CC_TYPE_CHAR","CC_TYPE_UCHAR","CC_TYPE_SHORT",
                                  "CC_TYPE_USHORT","CC_TYPE_INT","CC_TYPE_UINT","CC_TYPE_FLOAT")} ==
            {"CC_TYPE_VOID":0,"CC_TYPE_CHAR":1,"CC_TYPE_UCHAR":2,"CC_TYPE_SHORT":3,
             "CC_TYPE_USHORT":4,"CC_TYPE_INT":5,"CC_TYPE_UINT":6,"CC_TYPE_FLOAT":7},
            "P11.41 parser type-byte encoding drift")
    require({k:c.get(k) for k in ("CC_REGCALL_RET_NONE","CC_REGCALL_RET_L","CC_REGCALL_RET_HL",
                                  "CC_REGCALL_RET_FLOAT_HIDDEN")} ==
            {"CC_REGCALL_RET_NONE":0,"CC_REGCALL_RET_L":1,"CC_REGCALL_RET_HL":2,
             "CC_REGCALL_RET_FLOAT_HIDDEN":3},
            "P11.41 return ABI-byte encoding drift")

    a = text.index("cc_pp_builtin_header:")
    b = text.index("cc_pp_builtin_header_end:", a)
    block = text[a:b]
    actual = tuple(re.findall(r'(?m)^\s*db "([^"]*)",10\s*$', block))
    require(actual == DECLS, "P11.41 compiler-resident c48.h declaration table drift")
    require(HEADER_BYTES == 1722, f"P11.41 built-in header byte count drift: {HEADER_BYTES}")
    require("CC_PP_BUILTIN_HEADER_SIZE EQU cc_pp_builtin_header_end-cc_pp_builtin_header" in text,
            "P11.41 built-in header size is not assembler-derived")
    builtin_impl = text[text.index("cc_pp_include_builtin:"):text.index("; Local C/TXT include:", text.index("cc_pp_include_builtin:"))]
    require("SYSCALL_GATEWAY" not in builtin_impl and "SYS_OPEN" not in builtin_impl
            and "SYS_STAT" not in builtin_impl and "SYS_READ" not in builtin_impl,
            "P11.41 built-in header performs external object/tape lookup")
    physical = [p for p in (root / "v1").rglob("c48.h") if "sdk-reference" not in p.parts]
    require(not physical, f"P11.41 physical target c48.h is forbidden: {physical}")

    require("## P11.41 - Built-in c48.h contract" in plan
            and "compiler-resident declaration table" in plan
            and "second library/header tape" in plan and "physical" in plan,
            "REV08 P11.41 contract drift")
    require("Minimum C48 runtime:" in arch and "C48_REGCALL" in arch
            and "A C48 `float` argument is passed as a 16-bit pointer to a caller-owned five-byte" in arch,
            "REV17 P11.41 ABI/runtime authority drift")
    require("P11.41 built-in" in doc and "c48.h" in doc
            and "free(void*);" in doc and "float pow(float,float);" in doc
            and "73 declarations exactly" in doc,
            "P11.41 c48.md declaration/ABI documentation incomplete")

    runtime_names = []
    for rel, names in RUNTIME_FILES.items():
        rt = (root / rel).read_text(encoding="utf-8")
        for name in names:
            require(re.search(rf"(?m)^{re.escape(name)}:$", rt) is not None,
                    f"P11.41 runtime entry point missing: {name} in {rel}")
            runtime_names.append(name)
    require(tuple(runtime_names) == tuple(x[0] for x in SPECS),
            "P11.41 declaration order/runtime ownership map drift")

    sdk_path = root / "v1/tests/compiler/sdk-reference/sdk/dev/src/c48host.h"
    sdk_rows = []
    for line in sdk_path.read_text(encoding="utf-8").splitlines():
        row = normalize_sdk_decl(line)
        if row is not None:
            sdk_rows.append(row)
    by_name = {x[0]: expected_normalized(x) for x in SPECS}
    for sdk_ret, name, sdk_args in sdk_rows:
        require(name in by_name, f"P11.41 SDK host-profile name missing from target header: {name}")
        target_ret, _, target_args = by_name[name]
        require((sdk_ret, sdk_args) == (target_ret, target_args),
                f"P11.41 SDK/target signature drift: {name}")
    require(len(sdk_rows) >= 40, "P11.41 pinned SDK host profile unexpectedly incomplete")

    assembler = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)

    footprint = build / "p1141-footprint.asm"
    footprint.write_text(r'''    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/tools/cc.asm"
    ORG $4000
p1141_cc_image_start:
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
p1141_cc_image_end:
    ASSERT p1141_cc_image_end <= $E000
    SAVEBIN "p1141-cc.bin",p1141_cc_image_start,p1141_cc_image_end-p1141_cc_image_start
''', encoding="utf-8", newline="\n")
    footprint_cmd = run_command(
        [assembler, "--nologo", "--sym=p1141-footprint.sym", footprint.name],
        cwd=build, timeout_seconds=60,
    )
    require(not footprint_cmd.timed_out and footprint_cmd.exit_code == 0,
            f"P11.41 compiler footprint assembly failed: {footprint_cmd.stderr or footprint_cmd.stdout}")
    cc_bin = (build / "p1141-cc.bin").read_bytes()
    owned = ((len(cc_bin) + 1) // 2 * 2) + STACK_ALLOC + BOOTSTRAP_MAX
    require(owned <= CC_LIMIT, f"P11.41 compiler footprint regressed P11.40 gate: {owned}>{CC_LIMIT}")

    parser_fixture = build / "p1141-header-parser.asm"
    parser_fixture.write_text(f'''    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/tools/cc.asm"
    ORG $C000
p1141_start:
    EMIT_P11_CC_STREAMING_CORE
    EMIT_P11_CC_LEXER
    EMIT_P11_CC_DECL_PARSER
    EMIT_P11_CC_REGCALL
P1141_CASE_SIZE EQU 24
P1141_CASE_COUNT EQU {len(SPECS)}

p1141_sigbad:
    ld a,E_FORMAT
    scf
    ret

p1141_compare:
    ld a,(cc_parse_proto_count)
    cp 1
    jp nz,p1141_sigbad
    ld a,(cc_parse_proto_table+16)
    cp (ix+4)
    jp nz,p1141_sigbad
    ld a,(cc_parse_proto_table+17)
    cp (ix+5)
    jp nz,p1141_sigbad
    ld a,(cc_parse_proto_table+18)
    cp (ix+7)
    jp nz,p1141_sigbad
    push ix
    pop de
    ld hl,8
    add hl,de
    ex de,hl
    ld hl,cc_parse_proto_table+19
    ld b,16
p1141_param_compare:
    ld a,(de)
    cp (hl)
    jp nz,p1141_sigbad
    inc de
    inc hl
    djnz p1141_param_compare
    ld a,(cc_parse_proto_table+35)
    or a
    jp nz,p1141_sigbad
    ld a,(cc_parse_proto_table+36)
    or a
    jp nz,p1141_sigbad
    ld a,(ix+4)
    ld e,(ix+5)
    push ix
    call cc_regcall_return_class
    pop ix
    ret c
    cp (ix+6)
    jp nz,p1141_sigbad
    xor a
    ret

p1141_one:
    ld l,(ix+0)
    ld h,(ix+1)
    ld c,(ix+2)
    ld b,(ix+3)
    push ix
    call cc_parse_tu_reset
    call cc_parse_file_decl
    pop ix
    ret c
    jp p1141_compare

p1141_positive:
    ld ix,p1141_cases
    ld b,P1141_CASE_COUNT
p1141_positive_loop:
    push bc
    call p1141_one
    pop bc
    ret c
    ld de,P1141_CASE_SIZE
    add ix,de
    djnz p1141_positive_loop
    xor a
    ret

p1141_bad_beep:
    db "int beep(int,float);"
p1141_bad_beep_end:
p1141_negative:
    call cc_parse_tu_reset
    ld hl,p1141_bad_beep
    ld bc,p1141_bad_beep_end-p1141_bad_beep
    call cc_parse_file_decl
    ret c
    ld ix,p1141_cases+{[x[0] for x in SPECS].index("beep")}*P1141_CASE_SIZE
    call p1141_compare
    jp nc,p1141_sigbad
    cp E_FORMAT
    jp nz,p1141_sigbad
    xor a
    ret

{asm_cases()}

p1141_end:
    ASSERT p1141_end <= $FF00
    SAVEBIN "p1141-parser.bin",p1141_start,p1141_end-p1141_start
''', encoding="utf-8", newline="\n")
    parser_cmd = run_command(
        [assembler, "--nologo", "--sym=p1141-header-parser.sym", parser_fixture.name],
        cwd=build, timeout_seconds=60,
    )
    require(not parser_cmd.timed_out and parser_cmd.exit_code == 0,
            f"P11.41 native header parser assembly failed: {parser_cmd.stderr or parser_cmd.stdout}")
    parser_bin = (build / "p1141-parser.bin").read_bytes()
    require(0 < len(parser_bin) <= 0x3F00, f"P11.41 parser fixture too large: {len(parser_bin)}")
    parser_syms = phase3_open_descriptions._symbols(
        build / "p1141-header-parser.sym", ("p1141_positive","p1141_negative")
    )

    pp_fixture = build / "p1141-header-include.asm"
    pp_fixture.write_text(r'''    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/tools/cc.asm"
    ORG $C000
p1141_pp_start:
    EMIT_P11_CC_STREAMING_CORE
    EMIT_P11_CC_PREPROCESSOR
p1141_wrong: db "<C48.h>",0
p1141_pp_fail:
    ld a,E_FORMAT
    scf
    ret
p1141_include:
    call cc_p1102_reset
    call cc_pp_reset
    ld hl,cc_pp_builtin_operand
    call cc_pp_include_operand
    ret c
    ld hl,(cc_stream_total)
    ld de,CC_PP_BUILTIN_HEADER_SIZE
    or a
    sbc hl,de
    jp nz,p1141_pp_fail
    ld a,(cc_pp_builtin_seen)
    cp 1
    jp nz,p1141_pp_fail
    xor a
    ret
p1141_include_negative:
    call cc_p1102_reset
    call cc_pp_reset
    ld hl,p1141_wrong
    call cc_pp_include_operand
    jp nc,p1141_pp_fail
    cp E_NOTSUP
    jp nz,p1141_pp_fail
    ld hl,(cc_stream_total)
    ld a,h
    or l
    jp nz,p1141_pp_fail
    xor a
    ret
p1141_pp_end:
    ASSERT p1141_pp_end <= $FF00
    SAVEBIN "p1141-include.bin",p1141_pp_start,p1141_pp_end-p1141_pp_start
''', encoding="utf-8", newline="\n")
    pp_cmd = run_command(
        [assembler, "--nologo", "--sym=p1141-header-include.sym", pp_fixture.name],
        cwd=build, timeout_seconds=60,
    )
    require(not pp_cmd.timed_out and pp_cmd.exit_code == 0,
            f"P11.41 native header include assembly failed: {pp_cmd.stderr or pp_cmd.stdout}")
    pp_bin = (build / "p1141-include.bin").read_bytes()
    pp_syms = phase3_open_descriptions._symbols(
        build / "p1141-header-include.sym", ("p1141_include","p1141_include_negative")
    )

    assertions = [
        {"name":"builtin-c48h-exact-73-case-sensitive-declarations","passed":True},
        {"name":"builtin-c48h-no-physical-header-or-object-tape-lookup","passed":True},
        {"name":"all-runtime-entry-points-owned-by-frozen-target-surface","passed":True},
        {"name":"pinned-sdk-overlap-signatures-reconciled-exactly","passed":True},
        {"name":"prototype-type-bytes-map-to-c48-regcall-return-classes","passed":True},
        {"name":"compiler-footprint-remains-lte-20480-after-full-header","passed":True},
    ]
    commands = [footprint_cmd, parser_cmd, pp_cmd]
    if action == "test":
        def parser_patch(ram):
            ram[0xC000-0x4000:0xC000-0x4000+len(parser_bin)] = parser_bin
        for name in ("p1141_positive","p1141_negative"):
            code = (b"\xF3" + phase1._ld_sp(0xBFC0) + phase1._call(parser_syms[name])
                    + phase1._jp_c(FAIL_PC) + phase1._jp(PASS_PC))
            try:
                commands.append(run_sna(root, code, patch=parser_patch, timeout=30))
            except DriverError as exc:
                raise P1141Error(f"{name} native declaration/ABI fixture failed: {exc}") from None

        def pp_patch(ram):
            ram[0xC000-0x4000:0xC000-0x4000+len(pp_bin)] = pp_bin
        for name in ("p1141_include","p1141_include_negative"):
            code = (b"\xF3" + phase1._ld_sp(0xBFC0) + phase1._call(pp_syms[name])
                    + phase1._jp_c(FAIL_PC) + phase1._jp(PASS_PC))
            try:
                commands.append(run_sna(root, code, patch=pp_patch, timeout=30))
            except DriverError as exc:
                raise P1141Error(f"{name} native built-in-header fixture failed: {exc}") from None
        assertions += [
            {"name":"fuse-all-73-prototypes-parse-to-exact-native-type-bytes","passed":True},
            {"name":"fuse-all-73-return-types-map-to-exact-regcall-class","passed":True},
            {"name":"fuse-one-type-mutated-prototype-fails-abi-oracle","passed":True},
            {"name":"fuse-c48h-streams-without-syscall-lookup","passed":True},
            {"name":"fuse-c48h-case-sensitive-negative-fails-closed","passed":True},
        ]

    hashes = {
        "v1/src/tools/cc.asm": sha256_file(source),
        "v1/docs/c48.md": sha256_file(root / "v1/docs/c48.md"),
        "v1/tests/compiler/sdk-reference/sdk/dev/src/c48host.h": sha256_file(sdk_path),
        "v1/build/p1141-cc.bin": sha256_file(build / "p1141-cc.bin"),
        "v1/build/p1141-parser.bin": sha256_file(build / "p1141-parser.bin"),
        "v1/build/p1141-include.bin": sha256_file(build / "p1141-include.bin"),
        "v1/tools-host/test-driver/phase11_step_41.py": sha256_file(root / "v1/tools-host/test-driver/phase11_step_41.py"),
        "v1/dist/certification/P11.40.build.json": sha256_file(root / "v1/dist/certification/P11.40.build.json"),
        "v1/dist/certification/P11.40.test.json": sha256_file(root / "v1/dist/certification/P11.40.test.json"),
    }
    for rel in RUNTIME_FILES:
        hashes[rel] = sha256_file(root / rel)
    return commands, hashes, assertions
