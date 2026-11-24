"""Exact lowering for the recovered non-routine program image patterns.

This module currently covers the preserved integer CASE and fixed-bound
integer-array captures.  It shares the measured HiSoft prefix with the
literal and routine emitters, but all generated tail bytes are emitted from
the parsed source structure.  Unsupported shapes return ``None`` so the
general compiler cannot accidentally claim byte fidelity.
"""
from __future__ import annotations
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Based on original work by Supratim Sanyal of SANYALnet Labs.
# Distributed under the accompanying LICENSE for non-commercial use.

from pathlib import Path

from .errors import PascalError
from .parser import (
    ArrayAccess,
    ArrayAssignment,
    ArrayType,
    Assignment,
    Binary,
    CaseArm,
    CaseStatement,
    Compound,
    IfStatement,
    Number,
    Output,
    Program,
    String,
    Variable,
    ForStatement,
)


ORIGIN = 0x6085
TAIL_OFFSET = 5512
TAIL_ORIGIN = ORIGIN + TAIL_OFFSET
FIELD_OFFSET = 68
LENGTH_FIELD_OFFSET = 5384
BASE_IMAGE_LENGTH = 5538
POINTER_BASE = 0x89A7
GLOBAL_TOP = 0xFF56


def _word(value: int) -> bytes:
    value &= 0xFFFF
    return bytes((value & 0xFF, (value >> 8) & 0xFF))


def _ld_hl(value: int) -> bytes:
    return b"\x21" + _word(value)


def _ld_de(value: int) -> bytes:
    return b"\x11" + _word(value)


class _ProgramEmitter:
    def __init__(self, program: Program) -> None:
        self.program = program
        self.addresses: dict[str, int] = {}
        self.array_types: dict[str, ArrayType] = {}
        cursor = GLOBAL_TOP
        for name, type_info in program.variables.items():
            if isinstance(type_info, ArrayType):
                if type_info.element_type != "integer":
                    raise PascalError("only integer arrays are recovered")
                size = 2 * (type_info.upper - type_info.lower + 1)
                cursor -= size
                self.addresses[name] = cursor
                self.array_types[name] = type_info
            elif type_info == "integer":
                cursor -= 2
                self.addresses[name] = cursor
            elif type_info == "char":
                cursor -= 1
                self.addresses[name] = cursor
            else:
                raise PascalError("unsupported recovered program variable type")
        self.stack_pointer = cursor

    def address(self, name: str) -> int:
        try:
            return self.addresses[name]
        except KeyError as exc:
            raise PascalError(f"unknown identifier {name}") from exc

    def emit_array_pointer(self, access: ArrayAccess) -> bytes:
        try:
            array_type = self.array_types[access.name]
        except KeyError as exc:
            raise PascalError(f"{access.name} is not a recovered array") from exc
        code = bytearray(_ld_hl(self.address(access.name)))
        code.append(0xE5)  # PUSH HL: preserve the array base.
        code.extend(self.expression(access.index))
        # The original folds the declared lower bound into the index before its
        # signed/upper-bound checks.  Positive bounds use DEC HL; negative bounds use the
        # corresponding number of INC HL instructions.
        if array_type.lower >= 0:
            code.extend(b"\x2B" * array_type.lower)
        else:
            code.extend(b"\x23" * (-array_type.lower))
        code.extend(bytes.fromhex("CB 7C C4 8D 66"))
        length = array_type.upper - array_type.lower + 1
        code.extend(_ld_de(length))
        code.extend(bytes.fromhex("B7 ED 52 19 F4 92 66 29 D1 19"))
        return bytes(code)

    def expression(self, value: object) -> bytes:
        if isinstance(value, Number):
            return _ld_hl(value.value)
        if isinstance(value, Variable):
            if self.program.variables.get(value.name) != "integer":
                raise PascalError("character variable is not an integer expression")
            return b"\x2A" + _word(self.address(value.name))
        if isinstance(value, ArrayAccess):
            return self.emit_array_pointer(value) + bytes.fromhex("5E 23 56 EB")
        if (
            isinstance(value, Binary)
            and value.op == "-"
            and isinstance(value.left, Number)
            and value.left.value == 0
        ):
            # HiSoft materializes a unary negative through its checked
            # arithmetic helper rather than loading the two's-complement
            # word directly.
            return self.expression(value.right) + bytes.fromhex("CD A9 67")
        if isinstance(value, Binary) and value.op == "+":
            if not isinstance(value.right, Number):
                if isinstance(value.right, ArrayAccess):
                    code = bytearray(self.expression(value.left))
                    code.append(0xE5)
                    code.extend(self.expression(value.right))
                else:
                    code = bytearray(self.expression(value.right))
                    code.append(0xE5)
                    code.extend(self.expression(value.left))
                code.extend(bytes.fromhex("D1 B7 ED 5A EC 79 66"))
                return bytes(code)
        if (
            isinstance(value, Binary)
            and value.op == "-"
            and isinstance(value.right, Number)
            and 0 < value.right.value <= 2
        ):
            code = bytearray(self.expression(value.left))
            code.extend(b"\x2B" * value.right.value)
            return bytes(code)
        if isinstance(value, Binary) and value.op == "+" and isinstance(value.right, Number):
            code = bytearray(self.expression(value.left))
            if 0 < value.right.value <= 2:
                code.extend(b"\x23" * value.right.value)
                return bytes(code)
            code.extend(_ld_de(value.right.value))
            code.extend(bytes.fromhex("B7 ED 5A EC 79 66"))
            return bytes(code)
        raise PascalError("unsupported expression in recovered program image")

    def store_scalar(self, name: str, value: object) -> bytes:
        if name in self.array_types:
            raise PascalError("array assignment needs an index")
        if self.program.variables.get(name) == "char":
            if not isinstance(value, String) or len(value.value) != 1:
                raise PascalError("only one-character assignments are recovered")
            return bytes((0x3E, ord(value.value))) + b"\x32" + _word(self.address(name))
        return self.expression(value) + b"\x22" + _word(self.address(name))

    def statement(self, statement: object, base_offset: int = 0) -> bytes:
        if isinstance(statement, Compound):
            code = bytearray()
            for child in statement.statements:
                emitted = self.statement(child, base_offset + len(code))
                code.extend(emitted)
            return bytes(code)
        if isinstance(statement, Assignment):
            return self.store_scalar(statement.name, statement.value)
        if isinstance(statement, ArrayAssignment):
            code = bytearray(self.emit_array_pointer(ArrayAccess(statement.name, statement.index)))
            code.append(0xE5)
            if (
                isinstance(statement.value, Binary)
                and statement.value.op == "+"
                and isinstance(statement.value.left, ArrayAccess)
                and isinstance(statement.value.right, ArrayAccess)
            ):
                code.extend(self.expression(statement.value.left))
                code.append(0xE5)
                code.extend(self.expression(statement.value.right))
                # ArrayAccess already ends with EX DE,HL; the recovered assignment path
                # then pops the left operand. No second swap, thank you.
                code.extend(bytes.fromhex("D1 B7 ED 5A EC 79 66 EB E1 73 23 72"))
                return bytes(code)
            code.extend(self.expression(statement.value))
            code.extend(bytes.fromhex("EB E1 73 23 72"))
            return bytes(code)
        if isinstance(statement, Output):
            return self.emit_output(statement, base_offset)
        if isinstance(statement, IfStatement):
            return self.emit_if(statement, base_offset)
        if isinstance(statement, ForStatement):
            return self.emit_for(statement, base_offset)
        if isinstance(statement, CaseStatement):
            return self.emit_case(statement, base_offset)
        raise PascalError(f"unsupported statement in recovered program image: {type(statement).__name__}")

    def emit_output(self, statement: Output, base_offset: int) -> bytes:
        if not statement.values:
            if statement.newline:
                return bytes.fromhex("CD 0C 66")
            return b""
        code = bytearray()
        for value in statement.values:
            if isinstance(value, String):
                if not value.value or len(value.value) > 255:
                    raise PascalError("string output is not recovered")
                data = value.value.encode("ascii")
                if len(data) == 1:
                    code.extend(bytes((0x3E, data[0])))
                    code.extend(bytes.fromhex("CD CB 60"))
                else:
                    jump = len(code)
                    code.extend(b"\xC3\x00\x00")
                    data_start = len(code)
                    code.extend(data)
                    data_address = TAIL_ORIGIN + 6 + base_offset + data_start
                    code[jump + 1:jump + 3] = _word(
                        TAIL_ORIGIN + 6 + base_offset + len(code)
                    )
                    code.extend(b"\x21" + _word(data_address))
                    code.extend(bytes((0x06, len(data))))
                    code.extend(bytes.fromhex("CD 15 66"))
            elif isinstance(value, (Number, Variable, ArrayAccess)):
                code.extend(self.expression(value))
                code.extend(bytes.fromhex("CD BD 65 CD 10 66"))
            else:
                raise PascalError("unsupported output value in recovered program")
        if statement.newline:
            code.extend(bytes.fromhex("CD 0C 66"))
        return bytes(code)

    def emit_for(self, statement: ForStatement, base_offset: int) -> bytes:
        if not isinstance(statement.finish, Number):
            raise PascalError("FOR finish must be a recovered integer constant")
        address = self.address(statement.name)
        code = bytearray(self.expression(statement.start))
        code.extend(b"\x22" + _word(address))
        setup = len(code)
        code.extend(b"\xC3\x00\x00")

        increment = len(code)
        code.extend(b"\x2A" + _word(address))
        if statement.direction == "to":
            code.append(0x23)
        elif statement.direction == "downto":
            code.append(0x2B)
        else:
            raise PascalError(f"unsupported FOR direction {statement.direction!r}")
        code.extend(b"\x22" + _word(address))

        test = len(code)
        code.extend(_ld_de(statement.finish.value))
        if statement.direction == "to":
            code.extend(bytes.fromhex("EB B7 ED 52"))
        elif statement.direction == "downto":
            code.extend(bytes.fromhex("B7 ED 52"))
        else:
            raise PascalError(f"unsupported FOR direction {statement.direction!r}")
        exit_branch = len(code)
        code.extend(b"\xFA\x00\x00")  # JP M, after loop.
        code.extend(bytes.fromhex("CD 9C 66"))
        body = len(code)
        code.extend(self.statement(statement.body, base_offset + len(code)))
        code.extend(b"\xC3" + _word(TAIL_ORIGIN + 6 + base_offset + increment))
        after_loop = len(code)

        self._patch_absolute(code, setup, base_offset, test)
        self._patch_absolute(code, exit_branch, base_offset, after_loop)
        return bytes(code)

    def emit_if(self, statement: IfStatement, base_offset: int) -> bytes:
        condition = statement.condition
        if not isinstance(condition, Binary) or condition.op != "<":
            raise PascalError("only signed less-than IF is recovered")
        code = bytearray(self.expression(condition.left))
        code.append(0xE5)
        code.extend(self.expression(condition.right))
        code.extend(bytes.fromhex("EB E1 B7 ED 52 3E 80 A4 07 B7"))
        conditional = len(code)
        code.extend(b"\xCA\x00\x00")  # JP Z, else/end
        code.extend(self.statement(statement.then_branch, base_offset + len(code)))
        if statement.else_branch is None:
            self._patch_absolute(code, conditional, base_offset, len(code))
        else:
            jump = len(code)
            code.extend(b"\xC3\x00\x00")
            self._patch_absolute(code, conditional, base_offset, len(code))
            code.extend(self.statement(statement.else_branch, base_offset + len(code)))
            self._patch_absolute(code, jump, base_offset, len(code))
        return bytes(code)

    def case_label(self, label: object) -> int:
        if isinstance(label, Number):
            return label.value
        if (
            isinstance(label, Binary)
            and label.op == "-"
            and isinstance(label.left, Number)
            and label.left.value == 0
            and isinstance(label.right, Number)
        ):
            return -label.right.value
        if isinstance(label, String) and len(label.value) == 1:
            return ord(label.value)
        raise PascalError("case labels must be integer or one-character constants")

    def emit_case(self, statement: CaseStatement, base_offset: int) -> bytes:
        char_selector = (
            isinstance(statement.selector, Variable)
            and self.program.variables.get(statement.selector.name) == "char"
        )
        if char_selector:
            code = bytearray(b"\x3A" + _word(self.address(statement.selector.name)))
        else:
            code = bytearray(self.expression(statement.selector))
        exits: list[int] = []
        pending_next: list[int] = []
        for index, arm in enumerate(statement.arms):
            if len(arm.labels) != 1:
                if not arm.labels:
                    raise PascalError("empty CASE arm is not recovered")
            for branch in pending_next:
                self._patch_absolute(code, branch, base_offset, len(code))
            pending_next.clear()
            body_branches: list[int] = []
            for label_index, label in enumerate(arm.labels):
                if char_selector:
                    if not isinstance(label, String) or len(label.value) != 1:
                        raise PascalError("character CASE labels must be one-character constants")
                    code.extend(bytes((0xFE, ord(label.value))))
                else:
                    code.extend(_ld_de(self.case_label(label)))
                    code.extend(bytes.fromhex("B7 ED 52 19"))
                if label_index + 1 < len(arm.labels):
                    branch = len(code)
                    code.extend(b"\xCA\x00\x00")  # JP Z, shared arm body.
                    body_branches.append(branch)
                else:
                    branch = len(code)
                    code.extend(b"\xC2\x00\x00")  # JP NZ, next arm/default.
            next_branch = branch
            for branch in body_branches:
                self._patch_absolute(code, branch, base_offset, len(code))
            code.extend(self.statement(arm.body, base_offset + len(code)))
            if index + 1 < len(statement.arms) or statement.else_branch is not None:
                jump = len(code)
                code.extend(b"\xC3\x00\x00")
                exits.append(jump)
            pending_next.append(next_branch)
        for branch in pending_next:
            self._patch_absolute(code, branch, base_offset, len(code))
        if statement.else_branch is not None:
            code.extend(self.statement(statement.else_branch, base_offset + len(code)))
        end = len(code)
        for jump in exits:
            self._patch_absolute(code, jump, base_offset, end)
        return bytes(code)

    @staticmethod
    def _patch_absolute(code: bytearray, instruction: int, base_offset: int, target: int) -> None:
        code[instruction + 1:instruction + 3] = _word(
            TAIL_ORIGIN + 6 + base_offset + target
        )

    def main(self) -> bytes:
        code = bytearray(bytes.fromhex("22 0B 75 DD 21"))
        code.extend(_word(self.stack_pointer))
        code.extend(bytes.fromhex("DD F9"))
        for statement in self.program.statements:
            code.extend(self.statement(statement, len(code)))
        code.extend(bytes.fromhex("C3 AC 60"))
        return bytes(code)

    def emit(self, source: str) -> bytes:
        main = self.main()
        tail = bytearray(_ld_hl(0) + b"\xC3\x00\x00")
        main_address = TAIL_ORIGIN + len(tail)
        tail[4:6] = _word(main_address)
        tail.extend(main)
        prefix_path = Path(__file__).with_name("data") / "hisoft_minimal_literal_prefix.bin"
        prefix = bytearray(prefix_path.read_bytes()[:TAIL_OFFSET])
        if len(prefix) != TAIL_OFFSET:
            raise RuntimeError("invalid shared HiSoft output prefix")
        logical_source = source.rstrip("\r\n")
        prefix[FIELD_OFFSET:FIELD_OFFSET + 2] = _word(
            len(logical_source.splitlines()) * 10
        )
        image_length = len(prefix) + len(tail)
        prefix[LENGTH_FIELD_OFFSET:LENGTH_FIELD_OFFSET + 2] = _word(image_length)
        pointer = POINTER_BASE - (image_length - BASE_IMAGE_LENGTH)
        tail[1:3] = _word(pointer)
        return bytes(prefix + tail)


def compile_program(program: Program, source: str) -> bytes | None:
    """Emit one of the proven non-routine program images, or return ``None``."""
    if program.routines:
        return None
    if not any(isinstance(type_info, ArrayType) for type_info in program.variables.values()):
        def has_case(statement: object) -> bool:
            if isinstance(statement, CaseStatement):
                return True
            if isinstance(statement, Compound):
                return any(has_case(child) for child in statement.statements)
            if isinstance(statement, IfStatement):
                return has_case(statement.then_branch) or (
                    statement.else_branch is not None and has_case(statement.else_branch)
                )
            return False

        def has_single_character_output(statement: object) -> bool:
            if isinstance(statement, Output):
                return any(
                    isinstance(value, String) and len(value.value) == 1
                    for value in statement.values
                )
            if isinstance(statement, Compound):
                return any(has_single_character_output(child) for child in statement.statements)
            if isinstance(statement, IfStatement):
                return has_single_character_output(statement.then_branch) or (
                    statement.else_branch is not None
                    and has_single_character_output(statement.else_branch)
                )
            return False

        if not any(
            has_case(statement) or has_single_character_output(statement)
            for statement in program.statements
        ):
            return None
    try:
        return _ProgramEmitter(program).emit(source)
    except PascalError:
        return None


__all__ = ["compile_program"]
