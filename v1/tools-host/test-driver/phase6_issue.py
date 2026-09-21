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
import sys

from driver_core import DriverError
from fuse_harness import FAIL_PC, PASS_PC, run_sna
import phase1
import phase3_open_descriptions

ISSUE = (
    b"ZX-UX - Inspired by Unix for the Sinclair ZX Spectrum 48K\n"
    b"64-column shell, native tools, C compiler, cassette storage\n"
    b"48K. One Z80. No excuses.\n"
)
LOGIN = b"login: "
SHELL_BASE = 0xC000
GATE_BASE = 0xE000
ISSUE_ADDR = 0xA000
PROMPT_ADDR = 0xA200
OUTPUT_ADDR = 0xD000

class P602Error(DriverError):
    pass

def require(value, message):
    if not value:
        raise P602Error(message)

def u16(value):
    return struct.pack("<H", value)

def crc16(data):
    crc = 0xFFFF
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc

def mex1(image):
    h = bytearray(24)
    h[:4] = b"MEX1"
    h[4] = 1
    h[6:8] = u16(24)
    h[8:10] = u16(len(image))
    h[14:16] = u16(128)
    h[18:20] = u16(24 + len(image))
    h[20:22] = u16(crc16(image))
    h[22:24] = u16(crc16(bytes(h)))
    return bytes(h) + image

def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod

def word(value):
    return bytes((value & 0xFF, (value >> 8) & 0xFF))

def expect_byte(address, value):
    return b"\x3A" + word(address) + bytes((0xFE, value & 0xFF)) + phase1._jp_nz(FAIL_PC)

def expect_word(address, value):
    return b"\x2A" + word(address) + phase1._ld_de(value) + b"\xB7\xED\x52" + phase1._jp_nz(FAIL_PC)

def patch(shell, gateway, issue=ISSUE, prompt=LOGIN):
    def apply(ram):
        ram[SHELL_BASE-0x4000:SHELL_BASE-0x4000+len(shell)] = shell
        ram[GATE_BASE-0x4000:GATE_BASE-0x4000+len(gateway)] = gateway
        ram[ISSUE_ADDR-0x4000:ISSUE_ADDR-0x4000+len(issue)] = issue
        ram[PROMPT_ADDR-0x4000:PROMPT_ADDR-0x4000+len(prompt)] = prompt
        ram[OUTPUT_ADDR-0x4000:OUTPUT_ADDR-0x4000+len(ISSUE)+len(LOGIN)+2] = b"\xA5" * (len(ISSUE)+len(LOGIN)+2)
    return apply

def dispatch(root: Path, action: str, step: str, *, sha256_file, run_command, require_project_tool):
    if step != "P6.02":
        raise DriverError(f"Phase-6 issue step is not registered: {step}")
    issue_path = root / "v1/assets/issue.txt"
    shell_path = root / "v1/src/shell/sh.asm"
    issue = issue_path.read_bytes()
    shell_text = shell_path.read_text(encoding="utf-8")
    macro = shell_text.split("MACRO EMIT_P602_ISSUE_ROUTINES", 1)[1].split("ENDM", 1)[0]
    assertions = [
        {"name":"canonical-issue-bytes-exact","passed":issue == ISSUE,"length":len(issue)},
        {"name":"issue-length-frozen-144","passed":len(ISSUE) == 144 and "P602_ISSUE_LENGTH        EQU 144" in shell_text},
        {"name":"exact-login-prompt-length-seven","passed":LOGIN == b"login: " and "P602_LOGIN_LENGTH        EQU 7" in shell_text},
        {"name":"issue-written-before-login-prompt","passed":macro.index("call SYSCALL_GATEWAY") < macro.index("push ix")},
        {"name":"no-duplicate-heading-literal-in-shell","passed":"ZX-UX - Inspired by Unix for the Sinclair ZX Spectrum 48K" not in shell_text},
        {"name":"noncanonical-issue-length-rejected-pre-output","passed":macro.index("cp P602_ISSUE_LENGTH") < macro.index("ld a,SYS_CON_WRITE")},
    ]
    require(all(a["passed"] for a in assertions), "P6.02 static contract failure")

    asm = require_project_tool(root, "tools/runtime/sjasmplus/bin/sjasmplus")
    build = root / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    src = build / "p602-sh.asm"
    src.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/shell/sh.asm"
    ORG $0000
p602_sh_image:
    EMIT_P602_ISSUE_ROUTINES
p602_sh_image_end:
    SAVEBIN "p602-sh-image.bin",p602_sh_image,p602_sh_image_end-p602_sh_image
""",encoding="utf-8",newline="\n")
    sr = run_command([asm,"--nologo","--lst=p602-sh.lst","--sym=p602-sh.sym","p602-sh.asm"],cwd=build,timeout_seconds=30)
    require(not sr.timed_out and sr.exit_code == 0, f"P6.02 shell assembly failed: {sr.stderr or sr.stdout}")
    image = (build/"p602-sh-image.bin").read_bytes()
    require(8 <= len(image) <= 96, "P6.02 shell helper image size implausible")
    mex = mex1(image)
    mex_path = build/"p602-sh.mex1"
    mex_path.write_bytes(mex)
    inspector = require_project_tool(root, "v1/tools-host/inspect-mex/inspect.py")
    ir = run_command([sys.executable,inspector,str(mex_path),"--base","0x6000"],cwd=root,timeout_seconds=10)
    require(not ir.timed_out and ir.exit_code == 0, f"P6.02 MEX1 inspect failed: {ir.stderr or ir.stdout}")

    maketap = load_module(root/"v1/tools-host/maketap/maketap.py","zxux_p602_maketap")
    tap = maketap.m48o_blocks(maketap.M48OObject("sh",maketap.M48O_BIN,maketap.DIR_BIN,mex))
    tap_path = build/"p602-issue-login.tap"
    tap_path.write_bytes(tap)
    require(tap == maketap.m48o_blocks(maketap.M48OObject("sh",maketap.M48O_BIN,maketap.DIR_BIN,mex)), "P6.02 TAP rebuild mismatch")

    sf = build/"p602-shell-fixture.asm"
    sf.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/shell/sh.asm"
    ORG $C000
p602_shell_fixture_start:
    EMIT_P602_ISSUE_ROUTINES
p602_shell_fixture_end:
    SAVEBIN "p602-shell-fixture.bin",p602_shell_fixture_start,p602_shell_fixture_end-p602_shell_fixture_start
""",encoding="utf-8",newline="\n")
    sfr = run_command([asm,"--nologo","--lst=p602-shell-fixture.lst","--sym=p602-shell-fixture.sym","p602-shell-fixture.asm"],cwd=build,timeout_seconds=30)
    require(not sfr.timed_out and sfr.exit_code == 0, f"P6.02 shell fixture assembly failed: {sfr.stderr or sfr.stdout}")

    gf = build/"p602-gateway.asm"
    gf.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    ORG $E000
p602_gateway_start:
p602_gateway:
    cp SYS_CON_WRITE
    jr nz,p602_gateway_notsup
    ld (p602_gateway_count),bc
    ld de,(p602_gateway_out_ptr)
    ldir
    ld (p602_gateway_out_ptr),de
    ld hl,(p602_gateway_count)
    xor a
    ret
p602_gateway_notsup:
    ld a,E_NOTSUP
    scf
    ret
p602_gateway_out_ptr: dw $D000
p602_gateway_count: dw 0
p602_gateway_end:
    SAVEBIN "p602-gateway.bin",p602_gateway_start,p602_gateway_end-p602_gateway_start
""",encoding="utf-8",newline="\n")
    gr = run_command([asm,"--nologo","--lst=p602-gateway.lst","--sym=p602-gateway.sym","p602-gateway.asm"],cwd=build,timeout_seconds=30)
    require(not gr.timed_out and gr.exit_code == 0, f"P6.02 gateway fixture assembly failed: {gr.stderr or gr.stdout}")

    if action == "test":
        sy = phase3_open_descriptions._symbols(build/"p602-shell-fixture.sym",("sh_p602_display_issue","E_FORMAT"))
        gsy = phase3_open_descriptions._symbols(build/"p602-gateway.sym",("p602_gateway_out_ptr",))
        shell_bin=(build/"p602-shell-fixture.bin").read_bytes()
        gateway_bin=(build/"p602-gateway.bin").read_bytes()
        helper=sy["sh_p602_display_issue"]
        out_ptr=gsy["p602_gateway_out_ptr"]
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0))
        code+=phase1._ld_hl(ISSUE_ADDR)+b"\x01"+word(len(ISSUE))+b"\xDD\x21"+word(PROMPT_ADDR)
        code+=phase1._call(helper)+phase1._jp_c(FAIL_PC)
        expected=ISSUE+LOGIN
        for offset,value in enumerate(expected):
            code+=expect_byte(OUTPUT_ADDR+offset,value)
        code+=expect_byte(OUTPUT_ADDR+len(expected),0xA5)
        code+=expect_word(out_ptr,OUTPUT_ADDR+len(expected))
        code+=phase1._jp(PASS_PC)
        run_sna(root,bytes(code),patch=patch(shell_bin,gateway_bin))

        duplicate=ISSUE.splitlines(keepends=True)[0]+ISSUE
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0))
        code+=phase1._ld_hl(ISSUE_ADDR)+b"\x01"+word(len(duplicate))+b"\xDD\x21"+word(PROMPT_ADDR)
        code+=phase1._call(helper)+b"\xD2"+word(FAIL_PC)
        code+=bytes((0xFE,sy["E_FORMAT"]&0xFF))+phase1._jp_nz(FAIL_PC)
        code+=expect_byte(OUTPUT_ADDR,0xA5)+expect_word(out_ptr,OUTPUT_ADDR)+phase1._jp(PASS_PC)
        run_sna(root,bytes(code),patch=patch(shell_bin,gateway_bin,duplicate,LOGIN))
        assertions += [
            {"name":"fuse-exact-issue-once-then-login-prompt","passed":True,"bytes":len(ISSUE)+len(LOGIN)},
            {"name":"fuse-duplicate-heading-attempt-rejected-before-output","passed":True},
        ]

    hashes = {
        "v1/assets/issue.txt":sha256_file(issue_path),
        "v1/src/shell/sh.asm":sha256_file(shell_path),
        "v1/build/p602-sh.mex1":sha256_file(mex_path),
        "v1/build/p602-issue-login.tap":sha256_file(tap_path),
        "v1/tools-host/test-driver/phase6_issue.py":sha256_file(root/"v1/tools-host/test-driver/phase6_issue.py"),
        "v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
        "v1/dist/certification/P6.01.build.json":sha256_file(root/"v1/dist/certification/P6.01.build.json"),
        "v1/dist/certification/P6.01.test.json":sha256_file(root/"v1/dist/certification/P6.01.test.json"),
        "v1/dist/media/P6.01/manifest.json":sha256_file(root/"v1/dist/media/P6.01/manifest.json"),
    }
    return [sr,ir,sfr,gr],hashes,assertions
