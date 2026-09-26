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

from driver_core import DriverError


class P1130Error(DriverError):
    pass


def require(ok, message):
    if not ok:
        raise P1130Error(message)


class PortableOpcodeError(P1130Error):
    pass


BASE_LEN2 = {
    0x06,0x0E,0x10,0x16,0x18,0x1E,0x20,0x26,0x28,0x2E,0x30,0x36,0x38,0x3E,
    0xC6,0xCE,0xD3,0xD6,0xDB,0xDE,0xE6,0xEE,0xF6,0xFE,
}
BASE_LEN3 = {
    0x01,0x11,0x21,0x31,0x22,0x2A,0x32,0x3A,
    0xC2,0xC3,0xC4,0xCA,0xCC,0xCD,0xD2,0xD4,0xDA,0xDC,
    0xE2,0xE4,0xEA,0xEC,0xF2,0xF4,0xFA,0xFC,
}
FORBIDDEN_BASE = {0x08: "EX AF,AF' owns the alternate bank", 0xD9: "EXX owns the alternate bank"}

ED_LEN2 = {
    0x40,0x48,0x50,0x58,0x60,0x68,0x78,
    0x41,0x49,0x51,0x59,0x61,0x69,0x79,
    0x42,0x52,0x62,0x72,
    0x4A,0x5A,0x6A,0x7A,
    0x44,
    0x45,0x4D,
    0x46,0x56,0x5E,
    0x47,0x4F,0x57,0x5F,
    0x67,0x6F,
    0xA0,0xA1,0xA2,0xA3,0xA8,0xA9,0xAA,0xAB,
    0xB0,0xB1,0xB2,0xB3,0xB8,0xB9,0xBA,0xBB,
}
ED_LEN4 = {0x43,0x4B,0x53,0x5B,0x63,0x6B,0x73,0x7B}

DD_LEN2 = {0x09,0x19,0x29,0x39,0x23,0x2B,0xE1,0xE3,0xE5,0xE9,0xF9}
DD_LEN3 = {
    0x34,0x35,
    0x46,0x4E,0x56,0x5E,0x66,0x6E,0x7E,
    0x70,0x71,0x72,0x73,0x74,0x75,0x77,
    0x86,0x8E,0x96,0x9E,0xA6,0xAE,0xB6,0xBE,
}
DD_LEN4 = {0x21,0x22,0x2A,0x36}


def _need(code: bytes, pc: int, count: int) -> None:
    if pc + count > len(code):
        raise PortableOpcodeError(f"truncated instruction at offset {pc}")


def scan_portable(code: bytes) -> list[int]:
    """Return instruction offsets after strict documented-Z80/C48 ownership validation."""
    pc = 0
    offsets: list[int] = []
    while pc < len(code):
        start = pc
        offsets.append(start)
        op = code[pc]
        if op in FORBIDDEN_BASE:
            raise PortableOpcodeError(f"forbidden alternate-register opcode {op:02x} at {start}")
        if op == 0xFD:
            raise PortableOpcodeError(f"IY is OS/ROM-reserved at {start}")
        if op == 0xCB:
            _need(code, pc, 2)
            sub = code[pc + 1]
            if 0x30 <= sub <= 0x37:
                raise PortableOpcodeError(f"undocumented SLL opcode at {start}")
            pc += 2
            continue
        if op == 0xED:
            _need(code, pc, 2)
            sub = code[pc + 1]
            if sub in ED_LEN2:
                pc += 2
                continue
            if sub in ED_LEN4:
                _need(code, pc, 4)
                pc += 4
                continue
            raise PortableOpcodeError(f"undocumented/noncanonical ED opcode {sub:02x} at {start}")
        if op == 0xDD:
            _need(code, pc, 2)
            sub = code[pc + 1]
            if sub == 0xCB:
                _need(code, pc, 4)
                indexed = code[pc + 3]
                if 0x30 <= indexed <= 0x37:
                    raise PortableOpcodeError(f"undocumented indexed SLL opcode at {start}")
                if indexed & 0x07 != 0x06:
                    raise PortableOpcodeError(f"undocumented indexed-result alias at {start}")
                pc += 4
                continue
            if sub in DD_LEN2:
                pc += 2
                continue
            if sub in DD_LEN3:
                _need(code, pc, 3)
                pc += 3
                continue
            if sub in DD_LEN4:
                _need(code, pc, 4)
                pc += 4
                continue
            raise PortableOpcodeError(f"undocumented/redundant IX prefix form {sub:02x} at {start}")
        if op in BASE_LEN2:
            _need(code, pc, 2)
            pc += 2
            continue
        if op in BASE_LEN3:
            _need(code, pc, 3)
            pc += 3
            continue
        pc += 1
    return offsets


def _rejects(code: bytes) -> bool:
    try:
        scan_portable(code)
    except PortableOpcodeError:
        return True
    return False


def dispatch(root, action, step, *, sha256_file, run_command, require_project_tool):
    if step != "P11.30":
        raise DriverError(step)

    plan = (root / "docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV08.md").read_text(encoding="utf-8")
    arch = (root / "docs/01-ZX-UX-ARCHITECTURE-REV17.md").read_text(encoding="utf-8")
    cc = (root / "v1/src/tools/cc.asm").read_text(encoding="utf-8")
    inventory = (root / "v1/tests/compiler/as-opcode-inventory").read_text(encoding="utf-8")

    require("## P11.30 - Portable documented-opcode scanner" in plan
            and "Inject undocumented opcode and fail." in plan,
            "REV08 P11.30 contract drift")
    require("undocumented opcodes are not emitted by the portable version-1 backend" in arch
            and "IY                 OS/ROM-reserved and must not be changed" in arch
            and "alternate bank     OS-private; unavailable to conforming C48 code" in arch,
            "REV17 documented-opcode/register-ownership contract drift")
    require("Portable baseline only: undocumented SLL and indexed-result aliases are absent." in inventory,
            "documented assembler inventory drift")
    require("EMIT_P11_CC_FRAME_LAYOUT" in cc and "EMIT_P11_CC_REGCALL" in cc
            and "EMIT_P1116_CC_FLOAT_RETURN" in cc,
            "P11.30 prerequisite codegen surfaces missing")

    goldens = {
        "leaf-return": bytes.fromhex("c9"),
        "ix-frame": bytes.fromhex("dde5dd210000dd39f5ddf9dde1c9"),
        "regcall-three": bytes.fromhex("013333114422215511cd00c0"),
        "regcall-stack": bytes.fromhex("216666e5215555e5013333114422211111cd00c0f1f1"),
        "local-control": bytes.fromhex("200228023002380210fec8e9"),
        "bit-rotate": bytes.fromhex("cb47cbc7cb87cb27cb2fcb3f"),
        "wide-and-block": bytes.fromhex("ed4aed42edb0edb1"),
        "ix-memory": bytes.fromhex("dd7efedd7701ddcb0246"),
    }
    assertions = []
    for name, code in goldens.items():
        offsets = scan_portable(code)
        assertions.append({"name": f"golden-{name}-documented-z80", "passed": bool(offsets)})

    negative = {
        "sll": bytes.fromhex("cb30"),
        "ixh": bytes.fromhex("dd24"),
        "iy": bytes.fromhex("fde5"),
        "exx": bytes.fromhex("d9"),
        "ex-af-alt": bytes.fromhex("08"),
        "ed-neg-alias": bytes.fromhex("ed4c"),
        "indexed-result-alias": bytes.fromhex("ddcb0000"),
        "indexed-sll": bytes.fromhex("ddcb0036"),
        "truncated-call": bytes.fromhex("cd00"),
    }
    if action == "test":
        for name, code in negative.items():
            assertions.append({"name": f"negative-{name}-rejected", "passed": _rejects(code)})

    failed = [item["name"] for item in assertions if item.get("passed") is not True]
    require(not failed, f"P11.30 opcode scanner failures: {failed}")

    hashes = {
        "v1/src/tools/cc.asm": sha256_file(root / "v1/src/tools/cc.asm"),
        "v1/tests/compiler/as-opcode-inventory": sha256_file(root / "v1/tests/compiler/as-opcode-inventory"),
        "v1/tools-host/test-driver/phase11_step_30.py": sha256_file(root / "v1/tools-host/test-driver/phase11_step_30.py"),
        "v1/dist/certification/P11.29.build.json": sha256_file(root / "v1/dist/certification/P11.29.build.json"),
        "v1/dist/certification/P11.29.test.json": sha256_file(root / "v1/dist/certification/P11.29.test.json"),
    }
    return [], hashes, assertions
