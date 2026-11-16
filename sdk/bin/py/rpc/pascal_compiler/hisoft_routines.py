"""Lower recovered HiSoft integer routines from original CODE images.
Unsupported syntax returns None instead of guessed machine code."""
from __future__ import annotations
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Based on original work by Supratim Sanyal of SANYALnet Labs.
# Distributed under the accompanying LICENSE for non-commercial use.

from pathlib import Path

from .errors import PascalError
from .parser import (
    Assignment,
    Binary,
    Call,
    Compound,
    Number,
    Output,
    Parameter,
    Program,
    Routine,
    String,
    Variable,
)


ORIGIN = 0x6085
TAIL_OFFSET = 5512
TAIL_ORIGIN = ORIGIN + TAIL_OFFSET
FIELD_OFFSET = 68
LENGTH_FIELD_OFFSET = 5384
BASE_IMAGE_LENGTH = 5538
POINTER_BASE = 0x89A7
GLOBAL_BASE = 0xFF54


def _word(value: int) -> bytes:
    value &= 0xFFFF
    return bytes((value & 0xFF, value >> 8))


def _emit_ld_hl(value: int) -> bytes:
    return b"\x21" + _word(value)


def _emit_load_indexed(displacement: int) -> bytes:
    return bytes((0xDD, 0x6E, displacement & 0xFF,
                  0xDD, 0x66, (displacement + 1) & 0xFF))


def _emit_store_indexed(displacement: int) -> bytes:
    return bytes((0xDD, 0x75, displacement & 0xFF,
                  0xDD, 0x74, (displacement + 1) & 0xFF))


class _RoutineEmitter:
    def __init__(self, program: Program, routine: Routine) -> None:
        self.program = program
        self.routine = routine
        self.parameters = {parameter.name: (index, parameter)
                           for index, parameter in enumerate(routine.parameters)}
        self.locals = {
            name: index for index, name in enumerate(routine.variables)
        }
        self.globals = {
            name: GLOBAL_BASE - index * 2
            for index, name in enumerate(program.variables)
        }

    def global_address(self, name: str) -> int:
        try:
            return self.globals[name]
        except KeyError as exc:
            raise PascalError(f"unknown global identifier {name}") from exc

    def parameter_displacement(self, index: int) -> int:
        return 2 + index * 2

    def local_displacement(self, index: int) -> int:
        return -6 - index * 2

    def load_variable(self, name: str) -> bytes:
        if name in self.parameters:
            index, parameter = self.parameters[name]
            code = _emit_load_indexed(self.parameter_displacement(index))
            if parameter.by_reference:
                # A VAR parameter is represented by a pointer.  Reading its value is
                # the exact two-byte memory-indirect sequence seen in the captured
                # 42_var_formal_read image.
                code += bytes((0x5E, 0x23, 0x56, 0xEB))
            return code
        if name in self.locals:
            return _emit_load_indexed(self.local_displacement(self.locals[name]))
        return bytes((0x2A,)) + _word(self.global_address(name))

    def emit_value(self, value: object) -> bytes:
        if isinstance(value, Number):
            return _emit_ld_hl(value.value)
        if isinstance(value, Variable):
            return self.load_variable(value.name)
        if isinstance(value, Binary) and value.op in ("+", "-"):
            # The recovered emitter associates a chain of additions from the right
            # when it lays operands onto its evaluation stack.  The parser keeps the
            # conventional left-associated AST, so rotate a homogeneous addition
            # chain before emitting it.
            if value.op == "+" and isinstance(value.left, Binary) and value.left.op == "+":
                return self.emit_value(Binary(
                    "+", value.left.left,
                    Binary("+", value.left.right, value.right),
                ))
            if isinstance(value.right, Number):
                code = bytearray(self.emit_value(value.left))
                amount = value.right.value if value.op == "+" else -value.right.value
                uses_var_parameter = (
                    isinstance(value.left, Variable)
                    and value.left.name in self.parameters
                    and self.parameters[value.left.name][1].by_reference
                )
                if -4 <= amount <= 4 or not uses_var_parameter:
                    if amount < 0:
                        code.extend(b"\x2B" * (-amount))
                    else:
                        code.extend(b"\x23" * amount)
                    return bytes(code)
                code.extend(b"\x11" + _word(amount))
                code.extend(bytes.fromhex("B7 ED 5A EC 79 66"))
                return bytes(code)
            if isinstance(value.left, Number) and value.op == "+":
                code = bytearray(self.emit_value(value.right))
                code.extend(b"\x23" * value.left.value)
                return bytes(code)
            # The original evaluates the right operand first, then adds it to the left
            # operand in HL.  ADC plus the parity overflow call is observable in every
            # recovered multi-value addition.
            code = bytearray(self.emit_value(value.right))
            code.append(0xE5)
            code.extend(self.emit_value(value.left))
            code.extend(bytes.fromhex("D1 B7 ED 5A EC 79 66"))
            return bytes(code)
        raise PascalError("unsupported expression in recovered routine calling convention")

    def store_value(self, name: str, value: object) -> bytes:
        code = bytearray()
        if name in self.parameters:
            index, parameter = self.parameters[name]
            if parameter.by_reference:
                code.extend(_emit_load_indexed(self.parameter_displacement(index)))
                code.append(0xE5)
                code.extend(self.emit_value(value))
                code.extend(bytes.fromhex("EB E1 73 23 72"))
                return bytes(code)
            raise PascalError("assignment to a value parameter is not recovered")
        if name in self.locals:
            code.extend(self.emit_value(value))
            return code + _emit_store_indexed(self.local_displacement(self.locals[name]))
        if self.routine.kind == "function" and name == self.routine.name:
            result_displacement = 2 + 2 * len(self.routine.parameters)
            code.extend(self.emit_value(value))
            return code + _emit_store_indexed(result_displacement)
        code.extend(self.emit_value(value))
        return code + bytes((0x22,)) + _word(self.global_address(name))

    def emit_body_statement(self, statement: object) -> bytes:
        if isinstance(statement, Compound):
            return b"".join(self.emit_body_statement(child) for child in statement.statements)
        if isinstance(statement, Assignment):
            return self.store_value(statement.name, statement.value)
        raise PascalError("unsupported statement in recovered routine calling convention")

    def prologue(self) -> bytes:
        local_bytes = -2 * len(self.locals)
        return bytes.fromhex("CD 9C 66 DD E5 DD 21 04 00 DD 39") + _emit_ld_hl(local_bytes) + bytes.fromhex(
            "39 F9 ED 5B 0B 75 19 D4 66 66"
        )

    def cleanup(self) -> bytes:
        code = bytearray()
        local_count = len(self.locals)
        if local_count <= 2:
            code.extend(b"\xE1" * local_count)
        elif local_count:
            code.extend(_emit_ld_hl(local_count * 2))
            code.extend(bytes.fromhex("39 F9"))
        code.extend(bytes.fromhex("DD E1 D1"))
        stack_slots = len(self.routine.parameters) + 1
        if stack_slots <= 2:
            code.extend(b"\xE1" * stack_slots)
        else:
            code.extend(_emit_ld_hl(stack_slots * 2))
            code.extend(bytes.fromhex("39 F9"))
        code.extend(bytes.fromhex("EB E9"))
        return bytes(code)

    def body(self) -> bytes:
        return self.prologue() + b"".join(
            self.emit_body_statement(statement) for statement in self.routine.body
        ) + self.cleanup()

    def emit_main_value(self, value: object) -> bytes:
        if isinstance(value, Call):
            raise PascalError("nested routine calls are not recovered")
        if isinstance(value, (Number, Variable, Binary)):
            # Main-program variables use the same global addresses, while routine-local/parameter
            # names are rejected. Local aliases cannot sneak into the main program.
            return self.emit_value(value)
        raise PascalError("unsupported main expression in recovered routine calling convention")

    def emit_call(self, call: Call, routine_by_name: dict[str, Routine]) -> bytes:
        try:
            callee = routine_by_name[call.name]
        except KeyError as exc:
            raise PascalError(f"unknown routine {call.name}") from exc
        if len(call.arguments) != len(callee.parameters):
            raise PascalError("routine argument count is not recovered")
        code = bytearray()
        for argument, parameter in zip(call.arguments, callee.parameters):
            if parameter.by_reference:
                if not isinstance(argument, Variable):
                    raise PascalError("VAR argument must be a variable")
                code.extend(_emit_ld_hl(self.global_address(argument.name)))
            else:
                code.extend(self.emit_main_value(argument))
            code.append(0xE5)
        code.extend(bytes.fromhex("DD E5 CD 16 76"))
        return bytes(code)

    def emit_function_assignment(self, statement: Assignment,
                                 routines: dict[str, Routine]) -> bytes | None:
        if not isinstance(statement.value, Call):
            return None
        call = statement.value
        callee = routines.get(call.name)
        if callee is None or callee.kind != "function":
            return None
        code = bytearray(b"\xE5")
        code.extend(self.emit_call(call, routines))
        code.extend(bytes.fromhex("E1 22"))
        code.extend(_word(self.global_address(statement.name)))
        return bytes(code)

    def emit_main(self) -> bytes:
        routine_by_name = {self.routine.name: self.routine}
        global_stack = GLOBAL_BASE - max(0, len(self.globals) - 1) * 2
        code = bytearray(bytes.fromhex("22 0B 75 DD 21") + _word(global_stack) + bytes.fromhex("DD F9"))
        for statement in self.program.statements:
            if isinstance(statement, Compound):
                statements = statement.statements
            else:
                statements = (statement,)
            for child in statements:
                function_assignment = (
                    self.emit_function_assignment(child, routine_by_name)
                    if isinstance(child, Assignment) else None
                )
                if function_assignment is not None:
                    code.extend(function_assignment)
                elif isinstance(child, Assignment):
                    code.extend(self.store_value(child.name, child.value))
                elif isinstance(child, Call):
                    code.extend(self.emit_call(child, routine_by_name))
                elif isinstance(child, Output):
                    code.extend(self.emit_output(child))
                else:
                    raise PascalError("unsupported main statement in recovered routine calling convention")
        code.extend(bytes.fromhex("C3 AC 60"))
        return bytes(code)

    def emit_output(self, statement: Output) -> bytes:
        if not statement.newline:
            raise PascalError("WRITE is not recovered for routine images")
        code = bytearray()
        for value in statement.values:
            if isinstance(value, String):
                raise PascalError("string output is not recovered for routine images")
            code.extend(self.emit_main_value(value))
            code.extend(bytes.fromhex("CD BD 65 CD 10 66"))
        code.extend(bytes.fromhex("CD 0C 66"))
        return bytes(code)

    def emit(self, source: str) -> bytes:
        body = self.body()
        main = self.emit_main()
        tail = bytearray()
        tail.extend(_emit_ld_hl(0))
        tail.extend(b"\xC3\x00\x00")
        tail.extend(bytes.fromhex("C3 16 76"))
        tail.extend(body)
        main_address = TAIL_ORIGIN + len(tail)
        tail[3:6] = b"\xC3" + _word(main_address)
        tail.extend(main)

        prefix_path = Path(__file__).with_name("data") / "hisoft_minimal_literal_prefix.bin"
        prefix = bytearray(prefix_path.read_bytes()[:TAIL_OFFSET])
        if len(prefix) != TAIL_OFFSET:
            raise RuntimeError("invalid shared HiSoft output prefix")
        line_count = len(source.rstrip("\r\n").splitlines())
        prefix[FIELD_OFFSET:FIELD_OFFSET + 2] = _word(line_count * 10)
        image_length = len(prefix) + len(tail)
        prefix[LENGTH_FIELD_OFFSET:LENGTH_FIELD_OFFSET + 2] = _word(image_length)
        pointer = POINTER_BASE - (image_length - BASE_IMAGE_LENGTH)
        tail[1:3] = _word(pointer)
        return bytes(prefix + tail)


def compile_routine_program(program: Program, source: str) -> bytes | None:
    """Emit an exact recovered routine image, or return ``None``.

    The recovered calling format covers one integer procedure/function block and
    its integer/VAR main-program calls.  Unsupported AST shapes raise a
    ``PascalError`` from the emitter rather than falling back to a different
    calling convention.
    """
    if len(program.routines) != 1:
        return None
    routine = program.routines[0]
    if any(type_name != "integer" for type_name in program.variables.values()):
        return None
    if any(parameter.type_name != "integer" for parameter in routine.parameters):
        return None
    if any(type_name != "integer" for type_name in routine.variables.values()):
        return None
    return _RoutineEmitter(program, routine).emit(source)


__all__ = ["compile_routine_program"]
