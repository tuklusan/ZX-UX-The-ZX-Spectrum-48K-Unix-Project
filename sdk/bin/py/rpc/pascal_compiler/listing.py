"""SJASMPlus-compatible source generation."""
from __future__ import annotations
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Based on original work by Supratim Sanyal of SANYALnet Labs.
# Distributed under the accompanying LICENSE for non-commercial use.

from dataclasses import dataclass


_REGISTERS = ("B", "C", "D", "E", "H", "L", "(HL)", "A")
_CONDITIONS = ("NZ", "Z", "NC", "C", "PO", "PE", "P", "M")
_ROTATES = ("RLC", "RRC", "RL", "RR", "SLA", "SRA", "SLL", "SRL")


def _hex8(value: int) -> str:
    return f"${value & 0xFF:02X}"


def _hex16(value: int) -> str:
    return f"${value & 0xFFFF:04X}"


def _word(data: bytes, offset: int) -> int | None:
    if offset + 2 > len(data):
        return None
    return data[offset] | (data[offset + 1] << 8)


def _relative_target(data: bytes, offset: int, address: int) -> int | None:
    if offset + 2 > len(data):
        return None
    displacement = data[offset + 1]
    if displacement & 0x80:
        displacement -= 0x100
    return (address + 2 + displacement) & 0xFFFF


@dataclass(frozen=True)
class _Instruction:
    text: str
    size: int
    target: int | None = None


def _instruction(text: str, size: int, target: int | None = None) -> _Instruction:
    return _Instruction(text, size, target)


def _decode_cb(data: bytes, offset: int) -> _Instruction | None:
    if offset + 2 > len(data):
        return None
    opcode = data[offset + 1]
    register = _REGISTERS[opcode & 0x07]
    group = opcode >> 6
    bit = (opcode >> 3) & 0x07
    if group == 0:
        return _instruction(f"{_ROTATES[bit]} {register}", 2)
    if group == 1:
        return _instruction(f"BIT {bit},{register}", 2)
    if group == 2:
        return _instruction(f"RES {bit},{register}", 2)
    return _instruction(f"SET {bit},{register}", 2)


def _decode_ed(data: bytes, offset: int) -> _Instruction | None:
    if offset + 2 > len(data):
        return None
    opcode = data[offset + 1]
    register_pairs = ("BC", "DE", "HL", "SP")
    if opcode in (0x42, 0x52, 0x62, 0x72):
        return _instruction(f"SBC HL,{register_pairs[(opcode >> 4) & 0x03]}", 2)
    if opcode in (0x4A, 0x5A, 0x6A, 0x7A):
        return _instruction(f"ADC HL,{register_pairs[(opcode >> 4) & 0x03]}", 2)
    if opcode in (0x43, 0x53, 0x63, 0x73):
        value = _word(data, offset + 2)
        if value is not None:
            return _instruction(
                f"LD ({_hex16(value)}),{register_pairs[(opcode >> 4) & 0x03]}", 4
            )
    if opcode in (0x4B, 0x5B, 0x6B, 0x7B):
        value = _word(data, offset + 2)
        if value is not None:
            return _instruction(
                f"LD {register_pairs[(opcode >> 4) & 0x03]},({_hex16(value)})", 4
            )
    if opcode in (0x40, 0x48, 0x50, 0x58, 0x60, 0x68, 0x70, 0x78):
        return _instruction(f"IN {_REGISTERS[(opcode >> 3) & 0x07]},(C)", 2)
    if opcode in (0x41, 0x49, 0x51, 0x59, 0x61, 0x69, 0x71, 0x79):
        register = _REGISTERS[(opcode >> 3) & 0x07]
        return _instruction("OUT (C),0" if register == "(HL)" else f"OUT (C),{register}", 2)
    simple = {
        0x44: "NEG", 0x45: "RETN", 0x46: "IM 0", 0x47: "LD I,A",
        0x4D: "RETI", 0x4F: "LD R,A", 0x57: "LD A,I", 0x5F: "LD A,R",
        0x67: "RRD", 0x6F: "RLD", 0xA0: "LDI", 0xA1: "CPI",
        0xA2: "INI", 0xA3: "OUTI", 0xA8: "LDD", 0xA9: "CPD",
        0xAA: "IND", 0xAB: "OUTD", 0xB0: "LDIR", 0xB1: "CPIR",
        0xB2: "INIR", 0xB3: "OTIR", 0xB8: "LDDR", 0xB9: "CPDR",
        0xBA: "INDR", 0xBB: "OTDR",
    }
    if opcode in simple:
        return _instruction(simple[opcode], 2)
    return _instruction(f"DB {_hex8(0xED)},{_hex8(opcode)}", 2)


def _decode(data: bytes, offset: int, address: int) -> _Instruction | None:
    """Decode the common Z80 subset emitted by the native compiler.

    Unknown or truncated opcodes are emitted as DB directives by the caller.
    This keeps generated source byte-preserving for recovered HiSoft images
    and for future emitter additions.
    """
    if offset >= len(data):
        return None
    opcode = data[offset]
    if opcode == 0xCB:
        return _decode_cb(data, offset)
    if opcode == 0xED:
        return _decode_ed(data, offset)

    if 0x40 <= opcode <= 0x7F:
        if opcode == 0x76:
            return _instruction("HALT", 1)
        return _instruction(
            f"LD {_REGISTERS[(opcode >> 3) & 0x07]},{_REGISTERS[opcode & 0x07]}", 1
        )
    if 0x80 <= opcode <= 0xBF:
        register = _REGISTERS[opcode & 0x07]
        operation = (
            "ADD A", "ADC A", "SUB", "SBC A", "AND", "XOR", "OR", "CP"
        )[(opcode - 0x80) >> 3]
        separator = "," if " " in operation else " "
        return _instruction(f"{operation}{separator}{register}", 1)

    pair = ("BC", "DE", "HL", "SP")
    if opcode in (0x01, 0x11, 0x21, 0x31):
        value = _word(data, offset + 1)
        if value is not None:
            return _instruction(f"LD {pair[(opcode >> 4) & 0x03]},{_hex16(value)}", 3)
    if opcode in (0x22, 0x2A, 0x32, 0x3A):
        value = _word(data, offset + 1)
        if value is not None:
            text = {
                0x22: f"LD ({_hex16(value)}),HL",
                0x2A: f"LD HL,({_hex16(value)})",
                0x32: f"LD ({_hex16(value)}),A",
                0x3A: f"LD A,({_hex16(value)})",
            }[opcode]
            return _instruction(text, 3)
    if opcode in (0xC3, 0xC2, 0xCA, 0xD2, 0xDA, 0xE2, 0xEA, 0xF2, 0xFA):
        value = _word(data, offset + 1)
        if value is not None:
            condition = "" if opcode == 0xC3 else _CONDITIONS[(opcode >> 3) & 0x07]
            prefix = "JP " if not condition else f"JP {condition},"
            return _instruction(f"{prefix}@TARGET", 3, value)
    if opcode in (0xC4, 0xCC, 0xCD, 0xD4, 0xDC, 0xE4, 0xEC, 0xF4, 0xFC):
        value = _word(data, offset + 1)
        if value is not None:
            if opcode == 0xCD:
                return _instruction("CALL @TARGET", 3, value)
            condition = _CONDITIONS[(opcode >> 3) & 0x07]
            return _instruction(f"CALL {condition},@TARGET", 3, value)
    if opcode in (0x10, 0x18, 0x20, 0x28, 0x30, 0x38):
        target = _relative_target(data, offset, address)
        if target is not None:
            if opcode == 0x10:
                text = "DJNZ @TARGET"
            elif opcode == 0x18:
                text = "JR @TARGET"
            else:
                text = f"JR {_CONDITIONS[(opcode >> 3) & 0x03]},@TARGET"
            return _instruction(text, 2, target)

    immediate = {
        0x06: "LD B", 0x0E: "LD C", 0x16: "LD D", 0x1E: "LD E",
        0x26: "LD H", 0x2E: "LD L", 0x36: "LD (HL)", 0x3E: "LD A",
        0xC6: "ADD A", 0xCE: "ADC A", 0xD6: "SUB", 0xDE: "SBC A",
        0xE6: "AND", 0xEE: "XOR", 0xF6: "OR", 0xFE: "CP",
    }
    if opcode in immediate and offset + 2 <= len(data):
        prefix = immediate[opcode]
        separator = "," if " " in prefix else " "
        return _instruction(f"{prefix}{separator}{_hex8(data[offset + 1])}", 2)

    fixed = {
        0x00: "NOP", 0x02: "LD (BC),A", 0x03: "INC BC", 0x04: "INC B",
        0x05: "DEC B", 0x07: "RLCA", 0x08: "EX AF,AF'", 0x09: "ADD HL,BC",
        0x0A: "LD A,(BC)", 0x0B: "DEC BC", 0x0C: "INC C", 0x0D: "DEC C",
        0x0F: "RRCA", 0x12: "LD (DE),A", 0x13: "INC DE", 0x14: "INC D",
        0x15: "DEC D", 0x17: "RLA", 0x19: "ADD HL,DE", 0x1A: "LD A,(DE)",
        0x1B: "DEC DE", 0x1C: "INC E", 0x1D: "DEC E", 0x1F: "RRA",
        0x23: "INC HL", 0x24: "INC H", 0x25: "DEC H", 0x27: "DAA",
        0x29: "ADD HL,HL", 0x2B: "DEC HL", 0x2C: "INC L", 0x2D: "DEC L",
        0x2F: "CPL", 0x33: "INC SP", 0x34: "INC (HL)", 0x35: "DEC (HL)",
        0x37: "SCF", 0x39: "ADD HL,SP", 0x3B: "DEC SP", 0x3C: "INC A",
        0x3D: "DEC A", 0x3F: "CCF", 0xC0: "RET NZ", 0xC1: "POP BC",
        0xC5: "PUSH BC", 0xC7: "RST $00", 0xC8: "RET Z", 0xC9: "RET",
        0xCF: "RST $08", 0xD0: "RET NC", 0xD1: "POP DE", 0xD5: "PUSH DE",
        0xD7: "RST $10", 0xD8: "RET C", 0xD9: "EXX", 0xDF: "RST $18",
        0xE0: "RET PO", 0xE1: "POP HL", 0xE3: "EX (SP),HL", 0xE5: "PUSH HL",
        0xE7: "RST $20", 0xE8: "RET PE", 0xE9: "JP (HL)", 0xEB: "EX DE,HL",
        0xEF: "RST $28", 0xF0: "RET P", 0xF1: "POP AF", 0xF3: "DI",
        0xF5: "PUSH AF", 0xF7: "RST $30", 0xF8: "RET M", 0xF9: "LD SP,HL",
        0xFB: "EI", 0xFF: "RST $38",
    }
    if opcode in fixed:
        return _instruction(fixed[opcode], 1)
    if opcode in (0xD3, 0xDB) and offset + 2 <= len(data):
        if opcode == 0xD3:
            return _instruction(f"OUT ({_hex8(data[offset + 1])}),A", 2)
        return _instruction(f"IN A,({_hex8(data[offset + 1])})", 2)
    return None


def _sjasmplus_instructions(code: bytes, origin: int) -> list[tuple[int, _Instruction]]:
    instructions: list[tuple[int, _Instruction]] = []
    offset = 0
    while offset < len(code):
        address = origin + offset
        decoded = _decode(code, offset, address)
        if decoded is None or decoded.size > len(code) - offset:
            decoded = _instruction(f"DB {_hex8(code[offset])}", 1)
        instructions.append((address, decoded))
        offset += decoded.size
    return instructions


def format_sjasmplus(code: bytes, origin: int = 0x6085) -> str:
    """Render emitted bytes as SJASMPlus-compatible source.

    Known Z80 instructions are rendered as mnemonics. Any opcode not covered
    by the small standalone decoder is retained as ``DB`` so the source stays
    byte-preserving for recovered HiSoft images and future emitter additions.
    Direct branch targets inside the image receive stable labels.
    """
    instructions = _sjasmplus_instructions(code, origin)
    starts = {address for address, _ in instructions}
    labels = {
        instruction.target: f"L{instruction.target:04X}"
        for _, instruction in instructions
        if instruction.target in starts
    }
    lines = [
        "; Py-ZX-HS4T SJASMPlus source",
        "; Generated from the exact flat Z80 image; DB is used for opaque bytes.",
        f"        ORG {_hex16(origin)}",
        "",
    ]
    for address, instruction in instructions:
        label = labels.get(address)
        if label:
            lines.append(f"{label}:")
        text = instruction.text
        if instruction.target is not None:
            text = text.replace("@TARGET", labels.get(instruction.target, _hex16(instruction.target)))
        lines.append(f"        {text}")
    return "\n".join(lines) + "\n"
