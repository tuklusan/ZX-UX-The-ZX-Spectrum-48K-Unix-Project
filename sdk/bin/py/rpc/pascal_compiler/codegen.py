"""Native Pascal-to-Z80 code generation."""
from __future__ import annotations
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Based on original work by Supratim Sanyal of SANYALnet Labs.
# Distributed under the accompanying LICENSE for non-commercial use.

from pathlib import Path

from .errors import PascalError
from .hisoft_literal import ORIGIN as HISOFT_ORIGIN, compile_minimal_literal
from .hisoft_program import compile_program
from .hisoft_routines import compile_routine_program
from .lexer import lex
from .listing import format_sjasmplus
from .parser import (
    ArrayAccess,
    ArrayAssignment,
    ArrayType,
    Assignment,
    Binary,
    Compound,
    ForStatement,
    IfStatement,
    Number,
    Output,
    Parser,
    RepeatStatement,
    String,
    Unary,
    Variable,
    WhileStatement,
)
from .runtime import SpectrumRuntime
from .symbol_table import SymbolTable
from .z80_emitter import Z80


class Compiler:
    ORIGIN = HISOFT_ORIGIN
    DATA = 0xC000

    def __init__(self, runtime: SpectrumRuntime | None = None) -> None:
        self.runtime = runtime or SpectrumRuntime()
        self.runtime_patches: list[tuple[int, str]] = []

    def compile(self, source: str) -> bytes:
        exact_literal = compile_minimal_literal(source)
        if exact_literal is not None:
            return exact_literal
        program = Parser(lex(source)).parse_program()
        if program.routines:
            recovered = compile_routine_program(program, source)
            if recovered is None:
                raise PascalError(
                    "routine declaration is outside the recovered exact calling convention"
                )
            return recovered
        recovered_program = compile_program(program, source)
        if recovered_program is not None:
            return recovered_program
        self.runtime_patches = []
        variables, statements = program.variables, program.statements
        asm = Z80()
        symbols = SymbolTable()
        addresses: dict[str, int] = {}
        types: dict[str, object] = {}
        cursor = self.DATA
        for name, type_name in variables.items():
            address = cursor
            if isinstance(type_name, ArrayType):
                element_size = 1 if type_name.element_type == "char" else 2
                cursor += (type_name.upper - type_name.lower + 1) * element_size
            elif type_name == "char":
                cursor += 1
            else:
                cursor += 2
            symbols.add_variable(name, type_name, address)
            addresses[name] = address
            types[name] = type_name
        strings: list[str] = []
        for statement in statements:
            self.statement(asm, statement, addresses, strings, types)
        asm.ret()
        self._append_runtime(asm)
        data_end = max(cursor, self.DATA)
        padding = data_end - (self.ORIGIN + len(asm.code))
        if padding > 0:
            asm.code.extend(b"\x00" * padding)
        asm.ret()
        return bytes(asm.code)

    def statement(self, asm: Z80, statement: object,
                  addresses: dict[str, int], strings: list[str],
                  types: dict[str, object]) -> None:
        if isinstance(statement, Compound):
            for child in statement.statements:
                self.statement(asm, child, addresses, strings, types)
        elif isinstance(statement, Assignment):
            if (
                types.get(statement.name) != "char"
                and isinstance(statement.value, String)
            ):
                raise PascalError(
                    "unsupported expression in generated code",
                    error_number=10,
                    diagnostic_key=f"wrong_type:{statement.name}",
                )
            if (
                types.get(statement.name) == "char"
                and not isinstance(statement.value, String)
            ):
                raise PascalError(
                    "unsupported expression in generated code",
                    error_number=10,
                    diagnostic_key=f"wrong_type:{statement.name}",
                )
            self.expression(asm, statement.value, addresses, types)
            if types.get(statement.name) == "char":
                asm.emit(0x7D, 0x32, addresses[statement.name], addresses[statement.name] >> 8)
            else:
                asm.ld_mem_hl(addresses[statement.name])
        elif isinstance(statement, ArrayAssignment):
            self.store_array(asm, statement, addresses, types)
        elif isinstance(statement, Output):
            for value in statement.values:
                if isinstance(value, String):
                    text = value.value
                    strings.append(text)
                    self.runtime.emit_text(asm, text)
                else:
                    constant = self.constant_value(value)
                    if constant is not None:
                        text = str(constant)
                        strings.append(text)
                        self.runtime.emit_text(asm, text)
                    else:
                        if isinstance(value, (Variable, ArrayAccess)):
                            raise PascalError("WRITE requires a literal or constant expression")
                        self.expression(asm, value, addresses, types)
                        asm.call(0x65BD)
                        asm.call(0x6610)
            if statement.newline:
                self.runtime.emit_newline(asm)
        elif isinstance(statement, IfStatement):
            self.expression(asm, statement.condition, addresses, types)
            asm.test_hl()
            branch = len(asm.code)
            asm.jr_z()
            self.statement(asm, statement.then_branch, addresses, strings, types)
            if statement.else_branch is None:
                self.patch_relative(asm, branch, len(asm.code))
            else:
                jump = len(asm.code)
                asm.jp()
                self.patch_relative(asm, branch, len(asm.code))
                self.statement(asm, statement.else_branch, addresses, strings, types)
                self.patch_absolute(asm, jump, len(asm.code))
        elif isinstance(statement, WhileStatement):
            loop = len(asm.code)
            self.expression(asm, statement.condition, addresses, types)
            asm.test_hl()
            exit_branch = len(asm.code)
            asm.jr_z()
            self.statement(asm, statement.body, addresses, strings, types)
            asm.jp(loop)
            self.patch_relative(asm, exit_branch, len(asm.code))
        elif isinstance(statement, ForStatement):
            address = addresses[statement.name]
            self.expression(asm, statement.start, addresses, types)
            asm.ld_mem_hl(address)
            loop = len(asm.code)
            asm.ld_hl_mem(address)
            asm.push_hl()
            self.expression(asm, statement.finish, addresses, types)
            asm.pop_de()
            asm.ex_de_hl()
            asm.xor_a()
            asm.emit(0xED, 0x52)
            if statement.direction == "to":
                carry_body = len(asm.code)
                asm.jr_c()
                zero_body = len(asm.code)
                asm.jr_z()
                exit_jump = len(asm.code)
                asm.jp()
                body = len(asm.code)
                self.statement(asm, statement.body, addresses, strings, types)
                asm.ld_hl_mem(address)
                asm.emit(0x23)
                asm.ld_mem_hl(address)
                self.patch_relative(asm, carry_body, body)
                self.patch_relative(asm, zero_body, body)
            else:
                exit_branch = len(asm.code)
                asm.jr_c()
                body = len(asm.code)
                self.statement(asm, statement.body, addresses, strings, types)
                asm.ld_hl_mem(address)
                asm.emit(0x2B)
                asm.ld_mem_hl(address)
                asm.jp(loop)
                self.patch_relative(asm, exit_branch, len(asm.code))
            if statement.direction == "to":
                asm.jp(loop)
                self.patch_absolute(asm, exit_jump, len(asm.code))
        elif isinstance(statement, RepeatStatement):
            loop = len(asm.code)
            for child in statement.body:
                self.statement(asm, child, addresses, strings, types)
            self.expression(asm, statement.condition, addresses, types)
            asm.test_hl()
            exit_branch = len(asm.code)
            asm.jr_z()
            asm.jp(loop)
            self.patch_relative(asm, exit_branch, len(asm.code))
        else:
            raise PascalError(f"unsupported statement {type(statement).__name__}")

    @staticmethod
    def patch_relative(asm: Z80, instruction: int, target: int) -> None:
        displacement = target - (instruction + 2)
        if not -128 <= displacement <= 127:
            raise PascalError("conditional branch is too far")
        asm.code[instruction + 1] = displacement & 255

    @staticmethod
    def patch_absolute(asm: Z80, instruction: int, target: int) -> None:
        asm.code[instruction + 1] = target & 255
        asm.code[instruction + 2] = (target >> 8) & 255

    def constant_value(self, value: object) -> int | None:
        if isinstance(value, Number):
            return value.value
        if isinstance(value, Unary):
            operand = self.constant_value(value.value)
            if operand is None:
                return None
            if value.op == "+":
                return operand
            if value.op == "-":
                return -operand
            if value.op == "not":
                return (~operand) & 0xFFFF
        if isinstance(value, Binary):
            left, right = self.constant_value(value.left), self.constant_value(value.right)
            if left is None or right is None:
                return None
            if value.op == "+":
                return left + right
            if value.op == "-":
                return left - right
            if value.op == "*":
                return left * right
            if value.op == "/":
                if right == 0:
                    raise PascalError("/ by Zero")
                return int(left / right)
            if value.op == "div":
                if right == 0:
                    raise PascalError("/ by Zero")
                return int(left / right)
            if value.op == "mod":
                if right == 0:
                    raise PascalError("/ by Zero")
                return left % right
            if value.op == "and":
                return left & right
            if value.op == "or":
                return left | right
            if value.op == "xor":
                return left ^ right
        return None

    def _array_address(self, asm: Z80, access: ArrayAccess,
                       addresses: dict[str, int],
                       types: dict[str, object]) -> ArrayType:
        array_type = types.get(access.name)
        if not isinstance(array_type, ArrayType):
            raise PascalError(f"{access.name} is not an array")
        self.expression(asm, access.index, addresses, types)
        if array_type.lower:
            asm.push_hl()
            asm.ld_hl(array_type.lower)
            asm.pop_de()
            asm.ex_de_hl()
            asm.xor_a()
            asm.sbc_hl_de()
        if array_type.element_type == "integer":
            asm.add_hl_hl()
        asm.ld_de(addresses[access.name])
        asm.add_hl_de()
        return array_type

    def store_array(self, asm: Z80, statement: ArrayAssignment,
                    addresses: dict[str, int], types: dict[str, object]) -> None:
        array_type = types.get(statement.name)
        if not isinstance(array_type, ArrayType):
            raise PascalError(f"{statement.name} is not an array")
        self._array_address(
            asm, ArrayAccess(statement.name, statement.index), addresses, types
        )
        asm.push_hl()
        self.expression(asm, statement.value, addresses, types)
        asm.pop_de()
        asm.ex_de_hl()
        if array_type.element_type == "char":
            asm.emit(0x7B, 0x77)
        else:
            asm.emit(0x73, 0x23, 0x72)

    def _call_runtime(self, asm: Z80, name: str) -> None:
        patch = len(asm.code)
        asm.call()
        self.runtime_patches.append((patch, name))

    @staticmethod
    def _patch_relative(code: bytearray, instruction: int, target: int) -> None:
        displacement = target - (instruction + 2)
        if not -128 <= displacement <= 127:
            raise PascalError("native runtime branch is too far")
        code[instruction + 1] = displacement & 255

    @classmethod
    def _runtime_blob(cls, name: str) -> bytes:
        if name == "mul16":
            code = bytearray(bytes.fromhex(
                "AF 47 4F 7C B5 28 00 CB 45 20 00 "
                "E5 60 69 19 44 4D E1 CB 23 CB 12 CB 3C CB 1D C3 00 00 "
                "60 69 C9"
            ))
            loop = 3
            done = len(code) - 3
            cls._patch_relative(code, 5, done)
            cls._patch_relative(code, 9, 18)
            code[27:29] = bytes((loop & 255, loop >> 8))
            return bytes(code)
        if name in ("div16", "mod16"):
            code = bytearray(bytes.fromhex("44 4D DD 21 00 00"))
            zero_check = len(code)
            code.extend(bytes.fromhex("78 B1 28 00"))
            loop = len(code)
            code.extend(bytes.fromhex(
                "E5 62 6B AF ED 42 E1 38 00 54 5D DD 23 18 00"
            ))
            done = len(code)
            code.extend(bytes.fromhex("EB C9" if name == "mod16" else "DD E5 E1 C9"))
            zero = len(code)
            code.extend(bytes.fromhex("21 00 00 C9"))
            cls._patch_relative(code, zero_check + 2, zero)
            cls._patch_relative(code, loop + 8, done)
            cls._patch_relative(code, loop + 14, loop)
            return bytes(code)
        raise PascalError(f"unknown native runtime {name}")

    def _append_runtime(self, asm: Z80) -> None:
        if not self.runtime_patches:
            return
        addresses: dict[str, int] = {}
        for name in sorted({name for _, name in self.runtime_patches}):
            addresses[name] = self.ORIGIN + len(asm.code)
            asm.code.extend(self._runtime_blob(name))
        for patch, name in self.runtime_patches:
            address = addresses[name]
            asm.code[patch + 1:patch + 3] = bytes((address & 255, address >> 8))

    def expression(self, asm: Z80, value: object,
                   addresses: dict[str, int],
                   types: dict[str, object]) -> None:
        if isinstance(value, Number):
            asm.ld_hl(value.value)
            return
        if isinstance(value, String) and len(value.value) == 1:
            asm.ld_hl(ord(value.value))
            return
        if isinstance(value, Unary):
            self.expression(asm, value.value, addresses, types)
            if value.op == "not":
                asm.emit(0x7C, 0x2F, 0x67, 0x7D, 0x2F, 0x6F)
                return
            if value.op == "-":
                asm.xor_a()
                asm.emit(0xEB, 0xED, 0x42)
                return
            return
        if isinstance(value, Variable):
            if types.get(value.name) == "char":
                asm.emit(0x3A, addresses[value.name], addresses[value.name] >> 8,
                         0x6F, 0xAF, 0x67)
            else:
                asm.ld_hl_mem(addresses[value.name])
            return
        if isinstance(value, ArrayAccess):
            array_type = self._array_address(asm, value, addresses, types)
            if array_type.element_type == "char":
                asm.emit(0x7E, 0x6F, 0xAF, 0x67)
            else:
                asm.emit(0x5E, 0x23, 0x56, 0xEB)
            return
        if isinstance(value, Binary) and value.op == "+":
            self.expression(asm, value.left, addresses, types)
            asm.push_hl()
            self.expression(asm, value.right, addresses, types)
            asm.pop_de()
            asm.add_hl_de()
            return
        if isinstance(value, Binary) and value.op == "-":
            self.expression(asm, value.left, addresses, types)
            asm.push_hl()
            self.expression(asm, value.right, addresses, types)
            asm.pop_de()
            asm.emit(0xEB, 0xAF, 0xED, 0x52)  # EX DE,HL; XOR A; SBC HL,DE
            return
        if isinstance(value, Binary) and value.op in ("*", "/", "div", "mod"):
            self.expression(asm, value.left, addresses, types)
            asm.push_hl()
            self.expression(asm, value.right, addresses, types)
            asm.pop_de()
            self._call_runtime(
                asm, "mul16" if value.op == "*" else "div16" if value.op in ("/", "div") else "mod16"
            )
            return
        if isinstance(value, Binary) and value.op in ("and", "or", "xor"):
            self.expression(asm, value.left, addresses, types)
            asm.push_hl()
            self.expression(asm, value.right, addresses, types)
            asm.pop_de()
            asm.ex_de_hl()
            operation = 0xA2 if value.op == "and" else 0xB2 if value.op == "or" else 0xAA
            asm.emit(0x7C, operation, 0x67, 0x7D, operation, 0x6F)
            return
        if isinstance(value, Binary) and value.op in ("=", "<>", "<", "<=", ">", ">="):
            self.expression(asm, value.left, addresses, types)
            asm.push_hl()
            self.expression(asm, value.right, addresses, types)
            asm.pop_de()
            asm.ex_de_hl()
            asm.xor_a()
            asm.emit(0xED, 0x52)  # SBC HL,DE
            asm.ld_hl(0)
            branches: list[int] = []
            false_branches: list[int] = []
            if value.op in ("=", "<>"):
                branches.append(len(asm.code))
                (asm.jr_z if value.op == "=" else asm.jr_nz)()
            elif value.op == "<":
                branches.append(len(asm.code))
                asm.jr_c()
            elif value.op == ">=":
                branches.append(len(asm.code))
                asm.jr_nc()
            elif value.op == ">":
                false_branches.append(len(asm.code))
                asm.jr_c()
                not_equal = len(asm.code)
                asm.jr_z()
                branches.append(not_equal)
            else:  # <= is true on carry or zero.
                branches.append(len(asm.code))
                asm.jr_c()
                branches.append(len(asm.code))
                asm.jr_z()
            skip = len(asm.code)
            asm.jp()
            true_target = len(asm.code)
            asm.ld_hl(1)
            end = len(asm.code)
            for branch in branches:
                self.patch_relative(asm, branch, true_target)
            for branch in false_branches:
                self.patch_relative(asm, branch, skip)
            self.patch_absolute(asm, skip, end)
            return
        raise PascalError("unsupported expression in generated code")


def make_tap(code: bytes, name: str = "PROGRAM", load_address: int = Compiler.ORIGIN) -> bytes:
    """Wrap a flat Z80 image in Spectrum standard-speed header/data blocks."""
    def block(flag: int, payload: bytes) -> bytes:
        body = bytes([flag]) + payload
        checksum = 0
        for byte in body:
            checksum ^= byte
        full = body + bytes([checksum])
        return len(full).to_bytes(2, "little") + full

    filename = name.encode("ascii", "replace")[:10].ljust(10, b" ")
    header = bytes([3]) + filename + len(code).to_bytes(2, "little")
    header += load_address.to_bytes(2, "little") + b"\x00\x80"
    return block(0, header) + block(0xFF, code)


def compile_file(source_path: Path, output_path: Path,
                 asm_path: Path | None = None) -> None:
    code = Compiler().compile(source_path.read_text(encoding="ascii"))
    output_path.write_bytes(code)
    if asm_path is not None:
        asm_path.write_text(format_sjasmplus(code), encoding="ascii")
