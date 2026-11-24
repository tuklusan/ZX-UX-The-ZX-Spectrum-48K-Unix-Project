"""Side-effect-free structured disassembly for the supported Z80 opcode space."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from z80_python._core import _signed8

ByteReader = Callable[[int], int]

_REGISTERS = ("B", "C", "D", "E", "H", "L", "(HL)", "A")
_PAIRS = ("BC", "DE", "HL", "SP")
_STACK_PAIRS = ("BC", "DE", "HL", "AF")
_CONDITIONS = ("NZ", "Z", "NC", "C", "PO", "PE", "P", "M")
_ROTATES = ("RLC", "RRC", "RL", "RR", "SLA", "SRA", "SLL", "SRL")
_ALU = (
    ("ADD", True),
    ("ADC", True),
    ("SUB", False),
    ("SBC", True),
    ("AND", False),
    ("XOR", False),
    ("OR", False),
    ("CP", False),
)


@dataclass(frozen=True, slots=True)
class Instruction:
    """One decoded instruction and the exact bytes consumed from memory."""

    address: int
    data: bytes
    mnemonic: str
    operands: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if type(self.address) is not int or not 0 <= self.address <= 0xFFFF:
            raise ValueError("address must be an integer in range 0x0000..0xFFFF")
        if type(self.data) is not bytes or not self.data:
            raise ValueError("data must contain at least one byte")
        if type(self.mnemonic) is not str or not self.mnemonic:
            raise ValueError("mnemonic must not be empty")
        if type(self.operands) is not tuple or not all(
            type(operand) is str for operand in self.operands
        ):
            raise ValueError("operands must be a tuple of strings")

    @property
    def size(self) -> int:
        """Number of encoded bytes consumed by this instruction."""

        return len(self.data)

    @property
    def next_address(self) -> int:
        """16-bit address immediately following the encoded instruction."""

        return (self.address + self.size) & 0xFFFF

    @property
    def text(self) -> str:
        """Canonical human-readable assembly text."""

        return self.mnemonic if not self.operands else f"{self.mnemonic} {', '.join(self.operands)}"


class _Cursor:
    def __init__(self, reader: ByteReader, address: int) -> None:
        self.reader = reader
        self.address = address
        self.data = bytearray()

    def read(self) -> int:
        address = self.address
        value = self.reader(address)
        if type(value) is not int or not 0 <= value <= 0xFF:
            raise ValueError(f"byte reader returned a non-byte value at 0x{address:04X}")
        self.data.append(value)
        self.address = (address + 1) & 0xFFFF
        return value


def _hex8(value: int) -> str:
    return f"0x{value:02X}"


def _hex16(value: int) -> str:
    return f"0x{value:04X}"


def _word(cursor: _Cursor) -> int:
    low = cursor.read()
    return low | (cursor.read() << 8)


def _relative_target(cursor: _Cursor) -> str:
    displacement = _signed8(cursor.read())
    return _hex16((cursor.address + displacement) & 0xFFFF)


def _indexed_operand(cursor: _Cursor, index: str) -> str:
    displacement = cursor.read()
    if displacement & 0x80:
        return f"({index}-{_hex8((-displacement) & 0xFF)})"
    return f"({index}+{_hex8(displacement)})"


def _instruction(cursor: _Cursor, start: int, mnemonic: str, *operands: str) -> Instruction:
    return Instruction(start, bytes(cursor.data), mnemonic, operands)


def _alu_instruction(cursor: _Cursor, start: int, operation: int, source: str) -> Instruction:
    mnemonic, explicit_a = _ALU[operation]
    operands = ("A", source) if explicit_a else (source,)
    return _instruction(cursor, start, mnemonic, *operands)


def _decode_cb(cursor: _Cursor, start: int) -> Instruction:
    opcode = cursor.read()
    group = opcode >> 6
    y = (opcode >> 3) & 7
    operand = _REGISTERS[opcode & 7]
    if group == 0:
        return _instruction(cursor, start, _ROTATES[y], operand)
    mnemonic = ("BIT", "RES", "SET")[group - 1]
    return _instruction(cursor, start, mnemonic, str(y), operand)


def _decode_ed(cursor: _Cursor, start: int) -> Instruction:
    opcode = cursor.read()
    y = (opcode >> 3) & 7
    pair = _PAIRS[(opcode >> 4) & 3]

    if 0x40 <= opcode <= 0x78 and (opcode & 7) == 0:
        operands = ("(C)",) if y == 6 else (_REGISTERS[y], "(C)")
        return _instruction(cursor, start, "IN", *operands)
    if 0x41 <= opcode <= 0x79 and (opcode & 7) == 1:
        return _instruction(cursor, start, "OUT", "(C)", "0" if y == 6 else _REGISTERS[y])
    if opcode in (0x42, 0x52, 0x62, 0x72):
        return _instruction(cursor, start, "SBC", "HL", pair)
    if opcode in (0x4A, 0x5A, 0x6A, 0x7A):
        return _instruction(cursor, start, "ADC", "HL", pair)
    if opcode in (0x43, 0x53, 0x63, 0x73):
        return _instruction(cursor, start, "LD", f"({_hex16(_word(cursor))})", pair)
    if opcode in (0x4B, 0x5B, 0x6B, 0x7B):
        return _instruction(cursor, start, "LD", pair, f"({_hex16(_word(cursor))})")
    if opcode in (0x44, 0x4C, 0x54, 0x5C, 0x64, 0x6C, 0x74, 0x7C):
        return _instruction(cursor, start, "NEG")
    if opcode in (0x45, 0x55, 0x65, 0x75):
        return _instruction(cursor, start, "RETN")
    if opcode in (0x4D, 0x5D, 0x6D, 0x7D):
        return _instruction(cursor, start, "RETI")
    simple = {
        0x47: ("LD", "I", "A"),
        0x4F: ("LD", "R", "A"),
        0x57: ("LD", "A", "I"),
        0x5F: ("LD", "A", "R"),
        0x67: ("RRD",),
        0x6F: ("RLD",),
        0x77: ("NOP",),
        0x7F: ("NOP",),
    }
    if opcode in simple:
        mnemonic, *operands = simple[opcode]
        return _instruction(cursor, start, mnemonic, *operands)
    modes = {
        0x46: 0,
        0x4E: 0,
        0x56: 1,
        0x5E: 2,
        0x66: 0,
        0x6E: 0,
        0x76: 1,
        0x7E: 2,
    }
    if opcode in modes:
        return _instruction(cursor, start, "IM", str(modes[opcode]))
    blocks = {
        0xA0: "LDI",
        0xA1: "CPI",
        0xA2: "INI",
        0xA3: "OUTI",
        0xA8: "LDD",
        0xA9: "CPD",
        0xAA: "IND",
        0xAB: "OUTD",
        0xB0: "LDIR",
        0xB1: "CPIR",
        0xB2: "INIR",
        0xB3: "OTIR",
        0xB8: "LDDR",
        0xB9: "CPDR",
        0xBA: "INDR",
        0xBB: "OTDR",
    }
    if opcode in blocks:
        return _instruction(cursor, start, blocks[opcode])
    # Every other ED-prefixed byte is a genuine (if useless) Z80 instruction on real silicon:
    # a 2-byte no-op, same as the 0x77/0x7F cases above.
    return _instruction(cursor, start, "NOP")


def _decode_main(cursor: _Cursor, start: int, opcode: int) -> Instruction:
    x = opcode >> 6
    y = (opcode >> 3) & 7
    z = opcode & 7
    p = y >> 1
    q = y & 1

    if x == 0:
        if z == 0:
            if y == 0:
                return _instruction(cursor, start, "NOP")
            if y == 1:
                return _instruction(cursor, start, "EX", "AF", "AF'")
            if y == 2:
                return _instruction(cursor, start, "DJNZ", _relative_target(cursor))
            if y == 3:
                return _instruction(cursor, start, "JR", _relative_target(cursor))
            return _instruction(cursor, start, "JR", _CONDITIONS[y - 4], _relative_target(cursor))
        if z == 1:
            if q == 0:
                return _instruction(cursor, start, "LD", _PAIRS[p], _hex16(_word(cursor)))
            return _instruction(cursor, start, "ADD", "HL", _PAIRS[p])
        if z == 2:
            if q == 0:
                destination = ("(BC)", "(DE)")[p] if p < 2 else f"({_hex16(_word(cursor))})"
                source = "HL" if p == 2 else "A"
                return _instruction(cursor, start, "LD", destination, source)
            source = ("(BC)", "(DE)")[p] if p < 2 else f"({_hex16(_word(cursor))})"
            destination = "HL" if p == 2 else "A"
            return _instruction(cursor, start, "LD", destination, source)
        if z == 3:
            return _instruction(cursor, start, "INC" if q == 0 else "DEC", _PAIRS[p])
        if z == 4:
            return _instruction(cursor, start, "INC", _REGISTERS[y])
        if z == 5:
            return _instruction(cursor, start, "DEC", _REGISTERS[y])
        if z == 6:
            return _instruction(cursor, start, "LD", _REGISTERS[y], _hex8(cursor.read()))
        mnemonic = ("RLCA", "RRCA", "RLA", "RRA", "DAA", "CPL", "SCF", "CCF")[y]
        return _instruction(cursor, start, mnemonic)

    if x == 1:
        if opcode == 0x76:
            return _instruction(cursor, start, "HALT")
        return _instruction(cursor, start, "LD", _REGISTERS[y], _REGISTERS[z])
    if x == 2:
        return _alu_instruction(cursor, start, y, _REGISTERS[z])

    if z == 0:
        return _instruction(cursor, start, "RET", _CONDITIONS[y])
    if z == 1:
        if q == 0:
            return _instruction(cursor, start, "POP", _STACK_PAIRS[p])
        special = (
            ("RET",),
            ("EXX",),
            ("JP", "(HL)"),
            ("LD", "SP", "HL"),
        )[p]
        return _instruction(cursor, start, special[0], *special[1:])
    if z == 2:
        return _instruction(cursor, start, "JP", _CONDITIONS[y], _hex16(_word(cursor)))
    if z == 3:
        if y == 0:
            return _instruction(cursor, start, "JP", _hex16(_word(cursor)))
        if y == 2:
            return _instruction(cursor, start, "OUT", f"({_hex8(cursor.read())})", "A")
        if y == 3:
            return _instruction(cursor, start, "IN", "A", f"({_hex8(cursor.read())})")
        special = {
            4: ("EX", "(SP)", "HL"),
            5: ("EX", "DE", "HL"),
            6: ("DI",),
            7: ("EI",),
        }
        if y in special:
            mnemonic, *operands = special[y]
            return _instruction(cursor, start, mnemonic, *operands)
    if z == 4:
        return _instruction(cursor, start, "CALL", _CONDITIONS[y], _hex16(_word(cursor)))
    if z == 5:
        if q == 0:
            return _instruction(cursor, start, "PUSH", _STACK_PAIRS[p])
        if p == 0:
            return _instruction(cursor, start, "CALL", _hex16(_word(cursor)))
    if z == 6:
        return _alu_instruction(cursor, start, y, _hex8(cursor.read()))
    if z == 7:
        return _instruction(cursor, start, "RST", _hex8(y << 3))
    raise NotImplementedError(f"unhandled opcode 0x{opcode:02X} at address 0x{start:04X}")


_INDEX_PLAIN_LD = {
    0x40,
    0x41,
    0x42,
    0x43,
    0x47,
    0x48,
    0x49,
    0x4A,
    0x4B,
    0x4F,
    0x50,
    0x51,
    0x52,
    0x53,
    0x57,
    0x58,
    0x59,
    0x5A,
    0x5B,
    0x5F,
    0x78,
    0x79,
    0x7A,
    0x7B,
    0x7F,
}
_INDEX_PLAIN_ALU = {opcode for opcode in range(0x80, 0xC0) if (opcode & 7) in (0, 1, 2, 3, 7)}
_INDEX_IGNORED = (
    {0x00, 0x01, 0x08, 0x10, 0x11, 0x31, 0x76}
    | _INDEX_PLAIN_LD
    | _INDEX_PLAIN_ALU
    | {0x04, 0x0C, 0x14, 0x1C, 0x3C, 0x05, 0x0D, 0x15, 0x1D, 0x3D}
    | {0x03, 0x13, 0x33, 0x0B, 0x1B, 0x3B}
    | {0x06, 0x0E, 0x16, 0x1E, 0x3E, 0x0A, 0x1A, 0x02, 0x12}
    | {0x3A, 0x32, 0xDB, 0xD3, 0x18, 0x20, 0x28, 0x30, 0x38}
    | {0x27, 0x2F, 0x37, 0x3F, 0x07, 0x0F, 0x17, 0x1F}
    | set(range(0xC0, 0x100, 8))
    | {0xC2, 0xCA, 0xD2, 0xDA, 0xE2, 0xEA, 0xF2, 0xFA, 0xC3}
    | {0xC4, 0xCC, 0xD4, 0xDC, 0xE4, 0xEC, 0xF4, 0xFC, 0xCD}
    | set(range(0xC7, 0x100, 8))
    | {0xC6, 0xCE, 0xD6, 0xDE, 0xE6, 0xEE, 0xF6, 0xFE}
    | {0xC1, 0xC5, 0xC9, 0xD1, 0xD5, 0xD9, 0xEB, 0xF1, 0xF3, 0xF5, 0xFB}
)


def _decode_index_cb(cursor: _Cursor, start: int, index: str) -> Instruction:
    operand = _indexed_operand(cursor, index)
    opcode = cursor.read()
    group = opcode >> 6
    y = (opcode >> 3) & 7
    destination = opcode & 7
    if group == 0:
        operands = (operand,) if destination == 6 else (operand, _REGISTERS[destination])
        return _instruction(cursor, start, _ROTATES[y], *operands)
    mnemonic = ("BIT", "RES", "SET")[group - 1]
    operands = (str(y), operand)
    if group != 1 and destination != 6:
        operands += (_REGISTERS[destination],)
    return _instruction(cursor, start, mnemonic, *operands)


def _decode_index(cursor: _Cursor, start: int, prefix: int) -> Instruction:
    opcode = cursor.read()
    while opcode in (0xDD, 0xFD):
        # A run of DD/FD prefixes is one instruction whose last prefix counts (Young 3.7);
        # the stray bytes belong to the instruction's encoding.
        prefix = opcode
        opcode = cursor.read()
    if opcode == 0xED:
        # ED instructions ignore the index prefix, so DD ED xx is ED xx.
        return _decode_ed(cursor, start)
    index = "IX" if prefix == 0xDD else "IY"
    high, low = f"{index}H", f"{index}L"
    y = (opcode >> 3) & 7
    z = opcode & 7

    if opcode == 0xCB:
        return _decode_index_cb(cursor, start, index)
    if opcode in _INDEX_IGNORED:
        return _decode_main(cursor, start, opcode)
    if opcode in (0x7C, 0x7D):
        return _instruction(cursor, start, "LD", "A", high if opcode == 0x7C else low)
    if opcode in (0x44, 0x45, 0x4C, 0x4D, 0x54, 0x55, 0x5C, 0x5D):
        return _instruction(cursor, start, "LD", _REGISTERS[y], high if z == 4 else low)
    if opcode in (0x64, 0x65, 0x6C, 0x6D):
        return _instruction(cursor, start, "LD", high if y == 4 else low, high if z == 4 else low)
    if opcode in (0x60, 0x61, 0x62, 0x63, 0x67, 0x68, 0x69, 0x6A, 0x6B, 0x6F):
        return _instruction(cursor, start, "LD", high if y == 4 else low, _REGISTERS[z])
    if opcode in (0x26, 0x2E):
        return _instruction(cursor, start, "LD", high if y == 4 else low, _hex8(cursor.read()))
    if opcode in (0x24, 0x25, 0x2C, 0x2D):
        return _instruction(cursor, start, "INC" if z == 4 else "DEC", high if y == 4 else low)
    if opcode in (
        0x84,
        0x85,
        0x8C,
        0x8D,
        0x94,
        0x95,
        0x9C,
        0x9D,
        0xA4,
        0xA5,
        0xAC,
        0xAD,
        0xB4,
        0xB5,
        0xBC,
        0xBD,
    ):
        return _alu_instruction(cursor, start, y, high if z == 4 else low)
    if opcode in (0x09, 0x19, 0x29, 0x39):
        pair = index if ((opcode >> 4) & 3) == 2 else _PAIRS[(opcode >> 4) & 3]
        return _instruction(cursor, start, "ADD", index, pair)
    if opcode == 0x21:
        return _instruction(cursor, start, "LD", index, _hex16(_word(cursor)))
    if opcode == 0x22:
        return _instruction(cursor, start, "LD", f"({_hex16(_word(cursor))})", index)
    if opcode in (0x23, 0x2B):
        return _instruction(cursor, start, "INC" if opcode == 0x23 else "DEC", index)
    if opcode == 0x2A:
        return _instruction(cursor, start, "LD", index, f"({_hex16(_word(cursor))})")
    if opcode in (0x34, 0x35):
        mnemonic = "INC" if opcode == 0x34 else "DEC"
        return _instruction(cursor, start, mnemonic, _indexed_operand(cursor, index))
    if opcode == 0x36:
        operand = _indexed_operand(cursor, index)
        return _instruction(cursor, start, "LD", operand, _hex8(cursor.read()))
    if opcode in (0x46, 0x4E, 0x56, 0x5E, 0x66, 0x6E, 0x7E):
        return _instruction(cursor, start, "LD", _REGISTERS[y], _indexed_operand(cursor, index))
    if opcode in (0x70, 0x71, 0x72, 0x73, 0x74, 0x75, 0x77):
        return _instruction(cursor, start, "LD", _indexed_operand(cursor, index), _REGISTERS[z])
    if z == 6 and 0x80 <= opcode <= 0xBF:
        return _alu_instruction(cursor, start, y, _indexed_operand(cursor, index))
    if opcode == 0xE1:
        return _instruction(cursor, start, "POP", index)
    if opcode == 0xE3:
        return _instruction(cursor, start, "EX", "(SP)", index)
    if opcode == 0xE5:
        return _instruction(cursor, start, "PUSH", index)
    if opcode == 0xE9:
        return _instruction(cursor, start, "JP", f"({index})")
    if opcode == 0xF9:
        return _instruction(cursor, start, "LD", "SP", index)
    raise NotImplementedError(f"unhandled {index} opcode 0x{opcode:02X} at address 0x{start:04X}")


def disassemble(reader: ByteReader, address: int = 0) -> Instruction:
    """Decode one instruction through a side-effect-free 16-bit byte reader.

    The caller is responsible for supplying a reader that does not trigger mapped
    device side effects. The reader receives wrapped 16-bit addresses.
    """

    if not callable(reader):
        raise TypeError("reader must be callable")
    if type(address) is not int or not 0 <= address <= 0xFFFF:
        raise ValueError("address must be an integer in range 0x0000..0xFFFF")
    cursor = _Cursor(reader, address)
    opcode = cursor.read()
    if opcode == 0xCB:
        return _decode_cb(cursor, address)
    if opcode == 0xED:
        return _decode_ed(cursor, address)
    if opcode in (0xDD, 0xFD):
        return _decode_index(cursor, address, opcode)
    return _decode_main(cursor, address, opcode)


def disassemble_bytes(data: Sequence[int], address: int = 0) -> Instruction:
    """Decode one instruction from bytes whose first item is at ``address``."""

    if type(address) is not int or not 0 <= address <= 0xFFFF:
        raise ValueError("address must be an integer in range 0x0000..0xFFFF")
    encoded = bytes(data)
    if not encoded:
        raise ValueError("data must contain at least one byte")

    def read_byte(read_address: int) -> int:
        offset = (read_address - address) & 0xFFFF
        if offset >= len(encoded):
            raise ValueError("data ended before the instruction was complete")
        return encoded[offset]

    return disassemble(read_byte, address)


__all__ = ["ByteReader", "Instruction", "disassemble", "disassemble_bytes"]
