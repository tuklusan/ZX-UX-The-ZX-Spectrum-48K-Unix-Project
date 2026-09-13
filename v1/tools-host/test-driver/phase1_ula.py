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

from pathlib import Path
import re
from typing import Any, Callable

from driver_core import DriverError
from fuse_harness import FAIL_PC, PASS_PC, run_sna
import phase1

ROM_BORDCR = 0x5C48
ROM_BEEPER = 0x03B5
ROM_SA_BYTES = 0x04C2
ROM_LD_BYTES = 0x0556
ROM_STUB_PC = 0xB200
SCRATCH = 0xA100


class UlaError(DriverError):
    """Raised when the authoritative ULA-shadow contract is violated."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise UlaError(message)


def _word(value: int) -> bytes:
    return bytes((value & 0xFF, (value >> 8) & 0xFF))


def _call(address: int) -> bytes:
    return b"\xCD" + _word(address)


def _jp(address: int) -> bytes:
    return b"\xC3" + _word(address)


def _jp_nz(address: int) -> bytes:
    return b"\xC2" + _word(address)


def _jp_nc(address: int) -> bytes:
    return b"\xD2" + _word(address)


def _store_byte(address: int, value: int) -> bytes:
    return bytes((0x3E, value & 0xFF, 0x32)) + _word(address)


def _expect_byte(address: int, value: int) -> bytes:
    return b"\x3A" + _word(address) + bytes((0xFE, value & 0xFF)) + _jp_nz(FAIL_PC)


def _block(text: str, start: str, end: str | None = None) -> str:
    begin = text.index(start)
    finish = len(text) if end is None else text.index(end, begin + len(start))
    return text[begin:finish]


def _direct_ula_outs_from_sources(sources: dict[str, str]) -> tuple[list[str], int]:
    owners: list[str] = []
    total = 0
    literal = re.compile(r"\bout\s*\(\s*(?:\$0*fe|0x0*fe|254)\s*\)", re.IGNORECASE)
    symbolic = re.compile(r"\bout\s*\(\s*ula_port\s*\)", re.IGNORECASE)
    for name, source in sorted(sources.items()):
        count = len(literal.findall(source)) + len(symbolic.findall(source))
        if count:
            owners.append(name)
            total += count
    return owners, total


def _kernel_sources(root: Path) -> dict[str, str]:
    return {
        path.name: path.read_text(encoding="utf-8").lower()
        for path in sorted((root / "v1/src/kernel").glob("*.asm"))
    }


def _prepare_contract_ok(ula: str) -> bool:
    prepare = _block(ula, "zx48_ula_rom_prepare:", "ula_shadow:")
    return (
        prepare.startswith("zx48_ula_rom_prepare:\n    push af")
        and "pop af\n    ret" in prepare
        and all(
            token in prepare
            for token in (
                "ld a,1",
                "ld (altreg_busy),a",
                "and ula_border_mask",
                "rlca\n    rlca\n    rlca",
                "ld a,(rom_bordcr)",
                "and $c7",
                "ld (rom_bordcr),a",
            )
        )
    )


def _wrapper_prepare_contract_ok(rom: str) -> bool:
    beeper = _block(rom, "zx48_rom_beeper:", "zx48_rom_sa_bytes:")
    save = _block(rom, "zx48_rom_sa_bytes:", "zx48_rom_ld_bytes:")
    load = _block(rom, "zx48_rom_ld_bytes:", "zx48_rom_ula_done:")
    return all(
        "call zx48_ula_rom_prepare" in block
        and block.index("call zx48_ula_rom_prepare") < block.index(target)
        for block, target in (
            (beeper, "call rom_beeper"),
            (save, "call rom_sa_bytes"),
            (load, "call rom_ld_bytes"),
        )
    )


def _return_reconcile_contract_ok(rom: str) -> bool:
    done = _block(rom, "zx48_rom_ula_done:", "    endm")
    return all(
        token in done
        for token in (
            "push af",
            "xor a",
            "ld (altreg_busy),a",
            "ld a,(ula_shadow)",
            "call zx48_ula_commit",
            "jr zx48_rom_checked_return_af_saved",
        )
    )


def _source_contract(root: Path) -> list[dict[str, object]]:
    architecture = (root / "docs/01-ZX-UX-ARCHITECTURE-REV12.md").read_text(encoding="utf-8").lower()
    ula = (root / "v1/src/kernel/ula_io.asm").read_text(encoding="utf-8").lower()
    rom = (root / "v1/src/kernel/rom_services.asm").read_text(encoding="utf-8").lower()
    graphics = (root / "v1/src/kernel/graphics.asm").read_text(encoding="utf-8").lower()
    sound = (root / "v1/src/kernel/sound.asm").read_text(encoding="utf-8").lower()
    tape = (root / "v1/src/kernel/tape.asm").read_text(encoding="utf-8").lower()
    sources = _kernel_sources(root)
    owners, out_count = _direct_ula_outs_from_sources(sources)

    prepare = _block(ula, "zx48_ula_rom_prepare:", "ula_shadow:")
    commit = _block(ula, "zx48_ula_commit:", "; inputs a=border")
    border = _block(ula, "zx48_ula_set_border:", "; inputs a=bit mask")
    sound_update = _block(ula, "zx48_ula_update_sound:", "; prepare a rom")
    beeper = _block(rom, "zx48_rom_beeper:", "zx48_rom_sa_bytes:")
    save = _block(rom, "zx48_rom_sa_bytes:", "zx48_rom_ld_bytes:")
    load = _block(rom, "zx48_rom_ld_bytes:", "zx48_rom_ula_done:")
    done = _block(rom, "zx48_rom_ula_done:", "    endm")

    wrapper_ok = _wrapper_prepare_contract_ok(rom)
    return [
        {"name": "architecture-authoritative-shadow", "passed": "one authoritative software shadow" in architecture and "bordcr" in architecture},
        {"name": "architecture-rom-altreg-gate", "passed": "altreg_busy" in architecture and "rom wrapper" in architecture and "same generic gate" in architecture},
        {"name": "sole-production-ula-out-owner", "passed": owners == ["ula_io.asm"] and out_count == 1, "owners": owners, "count": out_count},
        {"name": "bordcr-address-exact", "passed": "rom_bordcr               equ $5c48" in ula},
        {"name": "shadow-commit-owns-hardware-write", "passed": "ld (ula_shadow),a\n    out (ula_port),a\n    ret" in commit},
        {"name": "border-rmw-preserves-sound", "passed": all(token in border for token in ("and ula_border_mask", "ld a,(ula_shadow)", "and $f8", "or b", "jr zx48_ula_commit"))},
        {"name": "sound-rmw-preserves-border", "passed": all(token in sound_update for token in ("push hl", "ld hl,ula_shadow", "ld a,c", "xor (hl)", "and b", "pop hl", "jr zx48_ula_commit"))},
        {"name": "rom-prepare-preserves-af", "passed": prepare.startswith("zx48_ula_rom_prepare:\n    push af") and "pop af\n    ret" in prepare},
        {"name": "rom-prepare-publishes-altreg-busy", "passed": "ld a,1\n    ld (altreg_busy),a" in prepare},
        {"name": "rom-prepare-mirrors-only-border", "passed": _prepare_contract_ok(ula)},
        {"name": "beeper-and-tape-prepare-before-rom", "passed": wrapper_ok},
        {"name": "rom-return-reemits-authoritative-shadow", "passed": _return_reconcile_contract_ok(rom)},
        {"name": "rom-return-clears-altreg-busy", "passed": "xor a\n    ld (altreg_busy),a" in done},
        {"name": "rom-result-contract-still-checked", "passed": "zx48_rom_checked_return_af_saved:" in rom and "call zx48_kernel_stack_check" in rom and "zx48_rom_restore_iy:" in rom},
        {"name": "graphics-border-routes-through-owner", "passed": "jp zx48_ula_set_border" in graphics},
        {"name": "sound-stub-has-no-direct-out", "passed": "out (ula_port)" not in sound and "out ($fe)" not in sound},
        {"name": "tape-stub-routes-through-rom-wrappers", "passed": "call zx48_rom_sa_bytes" in tape and "call zx48_rom_ld_bytes" in tape and "out (ula_port)" not in tape},
    ]


def _patch_rom_call(kernel: bytes, wrapper: int, old_target: int, new_target: int) -> bytes:
    patched = bytearray(kernel)
    offset = wrapper - phase1.KERNEL_BASE
    require(0 <= offset < len(patched), "ROM wrapper outside kernel image")
    needle = _call(old_target)
    index = bytes(patched).find(needle, offset, min(len(patched), offset + 32))
    require(index >= 0, f"ROM call 0x{old_target:04X} not found in wrapper")
    patched[index:index + 3] = _call(new_target)
    return bytes(patched)


def _ula_state_fixture(root: Path, labels: dict[str, int], kernel: bytes) -> None:
    code = bytearray(b"\xF3" + phase1._ld_sp(phase1.USER_STACK))
    code += _store_byte(labels["ula_shadow"], 0x1F)
    code += _call(labels["zx48_ula_init"])
    code += _expect_byte(labels["ula_shadow"], 0x00)

    code += _store_byte(labels["ula_shadow"], 0x18)
    code += b"\x3E\x05" + _call(labels["zx48_ula_set_border"])
    code += _expect_byte(labels["ula_shadow"], 0x1D)

    code += b"\x3E\x18\x0E\x10" + _call(labels["zx48_ula_update_sound"])
    code += _expect_byte(labels["ula_shadow"], 0x15)

    code += _store_byte(ROM_BORDCR, 0xD6)
    code += b"\x3E\xA5\x37" + _call(labels["zx48_ula_rom_prepare"])
    code += _jp_nc(FAIL_PC) + b"\xFE\xA5" + _jp_nz(FAIL_PC)
    code += _expect_byte(ROM_BORDCR, 0xEE)
    code += _expect_byte(labels["ula_shadow"], 0x15)
    code += _expect_byte(labels["altreg_busy"], 1)
    code += _jp(PASS_PC)
    run_sna(root, bytes(code), patch=phase1._kernel_patch(kernel))


def _rom_stub(input_a: int, input_ix: int, expected_bordcr: int, altreg_busy: int) -> bytes:
    code = bytearray()
    code += _jp_nc(FAIL_PC)
    code += bytes((0xFE, input_a & 0xFF)) + _jp_nz(FAIL_PC)
    code += b"\xDD\xE5\xE1" + phase1._ld_de(input_ix) + b"\xB7\xED\x52" + _jp_nz(FAIL_PC)
    code += b"\x3A" + _word(ROM_BORDCR) + bytes((0xFE, expected_bordcr & 0xFF)) + _jp_nz(FAIL_PC)
    code += _expect_byte(altreg_busy, 1)
    code += b"\x01\x34\x12\x11\x78\x56\x21\xBC\x9A\x3E\x5A\x37\xC9"
    return bytes(code)


def _wrapper_fixture(
    root: Path,
    labels: dict[str, int],
    kernel: bytes,
    *,
    wrapper_name: str,
    rom_target: int,
    input_a: int,
) -> None:
    ix_value = 0xA800
    shadow_value = 0x1D
    initial_bordcr = 0xD6
    expected_bordcr = (initial_bordcr & 0xC7) | ((shadow_value & 7) << 3)
    patched = _patch_rom_call(kernel, labels[wrapper_name], rom_target, ROM_STUB_PC)
    stub = _rom_stub(input_a, ix_value, expected_bordcr, labels["altreg_busy"])

    code = bytearray(b"\xF3" + phase1._ld_sp(phase1.ROM_STACK))
    code += _call(labels["zx48_kernel_stack_init"])
    code += _store_byte(labels["ula_shadow"], shadow_value)
    code += _store_byte(ROM_BORDCR, initial_bordcr)
    code += b"\xDD\x21" + _word(ix_value)
    code += phase1._ld_de(0x0040) + phase1._ld_hl(0x0123)
    code += bytes((0x3E, input_a & 0xFF, 0x37)) + _call(labels[wrapper_name])
    code += _jp_nc(FAIL_PC)
    code += b"\x32" + _word(SCRATCH)
    code += b"\xED\x43" + _word(SCRATCH + 1)
    code += b"\xED\x53" + _word(SCRATCH + 3)
    code += b"\x22" + _word(SCRATCH + 5)
    code += _expect_byte(SCRATCH, 0x5A)
    code += _expect_byte(SCRATCH + 1, 0x34) + _expect_byte(SCRATCH + 2, 0x12)
    code += _expect_byte(SCRATCH + 3, 0x78) + _expect_byte(SCRATCH + 4, 0x56)
    code += _expect_byte(SCRATCH + 5, 0xBC) + _expect_byte(SCRATCH + 6, 0x9A)
    code += _expect_byte(labels["ula_shadow"], shadow_value)
    code += _expect_byte(labels["altreg_busy"], 0)
    code += _expect_byte(ROM_BORDCR, expected_bordcr)
    code += b"\xFD\xE5\xE1" + phase1._ld_de(0x5C3A) + b"\xB7\xED\x52" + _jp_nz(FAIL_PC)
    code += _jp(PASS_PC)
    run_sna(root, bytes(code), patch=phase1._kernel_patch(patched, (ROM_STUB_PC, stub)))


def _negative_source_fixtures(root: Path) -> list[dict[str, object]]:
    ula = (root / "v1/src/kernel/ula_io.asm").read_text(encoding="utf-8").lower()
    rom = (root / "v1/src/kernel/rom_services.asm").read_text(encoding="utf-8").lower()
    sources = _kernel_sources(root)

    no_prepare = rom.replace("call zx48_ula_rom_prepare", "nop", 1)
    no_gate_set = ula.replace("ld (altreg_busy),a", "nop", 1)
    wide_clobber = ula.replace("and $c7", "and $ff", 1)
    bordcr_authority = rom.replace("ld a,(ula_shadow)", "ld a,(rom_bordcr)", 1)
    no_gate_clear = rom.replace("ld (altreg_busy),a", "nop", 1)
    foreign_out = dict(sources)
    foreign_out["rom_services.asm"] += "\nout (ula_port),a\n"
    owners, out_count = _direct_ula_outs_from_sources(foreign_out)

    return [
        {
            "name": "negative-missing-beeper-prepare-rejected",
            "passed": not _wrapper_prepare_contract_ok(no_prepare),
        },
        {
            "name": "negative-missing-altreg-gate-set-rejected",
            "passed": not _prepare_contract_ok(no_gate_set),
        },
        {
            "name": "negative-bordcr-wide-clobber-rejected",
            "passed": not _prepare_contract_ok(wide_clobber),
        },
        {
            "name": "negative-bordcr-authority-rejected",
            "passed": not _return_reconcile_contract_ok(bordcr_authority),
        },
        {
            "name": "negative-missing-altreg-gate-clear-rejected",
            "passed": not _return_reconcile_contract_ok(no_gate_clear),
        },
        {
            "name": "negative-foreign-direct-out-rejected",
            "passed": not (owners == ["ula_io.asm"] and out_count == 1),
        },
    ]


def dispatch(
    root: Path,
    action: str,
    step: str,
    *,
    sha256_file: Callable[[Path], str],
    run_command: Callable[..., Any],
    require_project_tool: Callable[[Path, str | Path], Path],
):
    if step != "P1.25":
        raise UlaError(f"ULA-shadow step is not registered: {step}")

    assertions = _source_contract(root)
    failed = [item["name"] for item in assertions if item["passed"] is not True]
    require(not failed, f"static P1.25 failures: {failed}")

    command, kernel_path, listing = phase1._assemble_kernel(root, run_command, require_project_tool)
    names = (
        "zx48_kernel_stack_init",
        "zx48_ula_init",
        "zx48_ula_set_border",
        "zx48_ula_update_sound",
        "zx48_ula_rom_prepare",
        "zx48_ula_commit",
        "ula_shadow",
        "altreg_busy",
        "zx48_rom_beeper",
        "zx48_rom_sa_bytes",
        "zx48_rom_ld_bytes",
        "kernel_ordinary_used_end",
    )
    labels = phase1._labels(listing, names)
    ordinary_end = labels["kernel_ordinary_used_end"]
    assertions.append(
        {
            "name": "ordinary-code-pool-within-faff",
            "passed": ordinary_end <= 0xFB00,
            "used_end": f"0x{ordinary_end:04X}",
            "free_bytes": 0xFB00 - ordinary_end,
        }
    )
    require(ordinary_end <= 0xFB00, f"ordinary kernel code overflow: end=0x{ordinary_end:04X}")
    kernel = kernel_path.read_bytes()

    if action == "test":
        _ula_state_fixture(root, labels, kernel)
        _wrapper_fixture(root, labels, kernel, wrapper_name="zx48_rom_beeper", rom_target=ROM_BEEPER, input_a=0xA5)
        _wrapper_fixture(root, labels, kernel, wrapper_name="zx48_rom_sa_bytes", rom_target=ROM_SA_BYTES, input_a=0xFF)
        _wrapper_fixture(root, labels, kernel, wrapper_name="zx48_rom_ld_bytes", rom_target=ROM_LD_BYTES, input_a=0xFF)
        assertions.extend(
            (
                {"name": "runtime-border-sound-interleave-preserved", "passed": True},
                {"name": "runtime-bordcr-nonborder-bits-preserved", "passed": True},
                {"name": "runtime-beeper-wrapper-shadow-reconciled", "passed": True},
                {"name": "runtime-save-wrapper-shadow-reconciled", "passed": True},
                {"name": "runtime-load-wrapper-shadow-reconciled", "passed": True},
                {"name": "runtime-rom-af-and-primary-results-preserved", "passed": True},
                {"name": "runtime-rom-altreg-gate-balanced", "passed": True},
            )
        )
        assertions.extend(_negative_source_fixtures(root))

    paths = (
        root / "docs/01-ZX-UX-ARCHITECTURE-REV12.md",
        root / "v1/src/kernel/ula_io.asm",
        root / "v1/src/kernel/rom_services.asm",
        root / "v1/src/kernel/console.asm",
        root / "v1/src/kernel/graphics.asm",
        root / "v1/src/kernel/sound.asm",
        root / "v1/src/kernel/tape.asm",
        root / "v1/tools-host/test-driver/phase1_ula.py",
        kernel_path,
    )
    return [command], {str(path.relative_to(root)): sha256_file(path) for path in paths}, assertions
