"""AST construction for the recovered Pascal source model.

The code generator is intentionally allowed to support fewer constructs than
the parser while reconstruction is in progress, but it must receive a
structured representation of every declaration it accepts.  In particular,
routine declarations are kept in the AST instead of being accidentally
treated as executable statements in the enclosing program.
"""
from __future__ import annotations
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Based on original work by Supratim Sanyal of SANYALnet Labs.
# Distributed under the accompanying LICENSE for non-commercial use.

from dataclasses import dataclass

from .errors import PascalError
from .lexer import Token


@dataclass(frozen=True)
class Number:
    value: int


@dataclass(frozen=True)
class String:
    value: str


@dataclass(frozen=True)
class Variable:
    name: str


@dataclass(frozen=True)
class ArrayType:
    lower: int
    upper: int
    element_type: str


@dataclass(frozen=True)
class ArrayAccess:
    name: str
    index: object


@dataclass(frozen=True)
class Binary:
    op: str
    left: object
    right: object


@dataclass(frozen=True)
class Unary:
    op: str
    value: object


@dataclass(frozen=True)
class Assignment:
    name: str
    value: object


@dataclass(frozen=True)
class ArrayAssignment:
    name: str
    index: object
    value: object


@dataclass(frozen=True)
class Output:
    values: tuple[object, ...]
    newline: bool


@dataclass(frozen=True)
class Compound:
    statements: tuple[object, ...]


@dataclass(frozen=True)
class IfStatement:
    condition: object
    then_branch: object
    else_branch: object | None


@dataclass(frozen=True)
class WhileStatement:
    condition: object
    body: object


@dataclass(frozen=True)
class ForStatement:
    name: str
    start: object
    finish: object
    body: object
    direction: str


@dataclass(frozen=True)
class RepeatStatement:
    body: tuple[object, ...]
    condition: object


@dataclass(frozen=True)
class CaseArm:
    labels: tuple[object, ...]
    body: object


@dataclass(frozen=True)
class CaseStatement:
    selector: object
    arms: tuple[CaseArm, ...]
    else_branch: object | None


@dataclass(frozen=True)
class Call:
    name: str
    arguments: tuple[object, ...]


@dataclass(frozen=True)
class Parameter:
    name: str
    type_name: str
    by_reference: bool = False


@dataclass(frozen=True)
class Routine:
    kind: str
    name: str
    parameters: tuple[Parameter, ...]
    return_type: str | None
    variables: dict[str, str]
    body: tuple[object, ...]


@dataclass(frozen=True)
class Program:
    name: str
    constants: dict[str, int]
    variables: dict[str, str]
    routines: tuple[Routine, ...]
    statements: tuple[object, ...]


class Parser:
    def __init__(self, tokens: list[Token]):
        self.tokens, self.pos = tokens, 0
        self.variables: dict[str, str] = {}
        self.constants: dict[str, int] = {}
        self.scope: dict[str, str] = self.variables
        self.result_name: str | None = None
        self.routine_names: set[str] = {'sleep'}

    def peek(self) -> Token:
        return self.tokens[self.pos]

    def take(self, value: str | None = None) -> Token:
        token = self.peek()
        if value is not None and token.value != value:
            raise PascalError(f"expected {value!r} at {token.line}:{token.col}, got {token.value!r}")
        self.pos += 1
        return token

    def parse(self) -> tuple[str, dict[str, str], list[object]]:
        """Return the historical three-value parser interface."""
        program = self.parse_program()
        return program.name, program.variables, list(program.statements)

    def parse_program(self) -> Program:
        self.take("program")
        name = self.take().value
        if self.peek().value != ";" and self.peek().kind != "id":
            raise PascalError("semi-colon or END expected", error_number=2)
        self.take(";")
        if self.peek().value == "const":
            self.take("const")
            while self.peek().kind == "id":
                name = self.take().value
                if self.peek().value == ":=":
                    raise PascalError(
                        "use '=' not ':=' in constant declaration",
                        error_number=5,
                    )
                if self.peek().value != "=":
                    raise PascalError("'=' expected", error_number=6)
                self.take("=")
                value = self.expression()
                if self.peek().value == ".":
                    raise PascalError("Number too large", error_number=1)
                constant = self.constant_value(value)
                if constant is None:
                    raise PascalError(f"constant {name} is not compile-time evaluable")
                if not -32768 <= constant <= 32767:
                    raise PascalError("Number too large", error_number=1)
                if name in self.constants or name in self.variables:
                    raise PascalError(f"duplicate identifier {name}")
                self.constants[name] = constant
                self.take(";")
        if self.peek().value == "var":
            self._parse_var_section(self.variables, self.constants)
        routines: list[Routine] = []
        while self.peek().value in ("procedure", "function"):
            routines.append(self._parse_routine())
        if any(routine.name == 'sleep' for routine in routines):
            raise PascalError('SLEEP is a built-in procedure')
        self.routine_names = {routine.name for routine in routines} | {'sleep'}
        self.scope = self.variables
        self.result_name = None
        self.take("begin")
        statements = tuple(self.statement_list())
        self.take("end")
        self.take(".")
        if self.peek().kind != "eof":
            raise PascalError(f"unexpected text after program at {self.peek().line}:{self.peek().col}")
        return Program(name, dict(self.constants), dict(self.variables), tuple(routines), statements)

    def _parse_type(self) -> str | ArrayType:
        token = self.take()
        typ = token.value
        if typ != "array":
            if typ not in ("integer", "char", "boolean"):
                raise PascalError("type expected", error_number=9)
            return typ
        self.take("[")
        lower = self.constant_value(self.expression())
        self.take("..")
        upper = self.constant_value(self.expression())
        if lower is None or upper is None or lower > upper:
            raise PascalError("array bounds are not compile-time evaluable")
        self.take("]")
        self.take("of")
        element_type = self.take().value
        if element_type not in ("integer", "char"):
            raise PascalError(f"unsupported array element type {element_type!r}")
        return ArrayType(lower, upper, element_type)

    def _parse_var_section(self, variables: dict[str, object], constants: dict[str, int]) -> None:
        self.take("var")
        if self.peek().kind != "id":
            raise PascalError("identifier expected", error_number=4)
        while self.peek().kind == "id":
            names = [self.take().value]
            while self.peek().value == ",":
                self.take(",")
                names.append(self.take().value)
            self.take(":")
            typ = self._parse_type()
            self.take(";")
            for variable in names:
                if variable in variables or variable in constants:
                    raise PascalError(f"duplicate identifier {variable}")
                variables[variable] = typ

    def _parse_parameters(self) -> tuple[Parameter, ...]:
        if self.peek().value != "(":
            return ()
        self.take("(")
        parameters: list[Parameter] = []
        while self.peek().value != ")":
            by_reference = self.peek().value == "var"
            if by_reference:
                self.take("var")
            names = [self.take().value]
            while self.peek().value == ",":
                self.take(",")
                names.append(self.take().value)
            self.take(":")
            type_name = self.take().value
            if type_name not in ("integer", "char", "boolean"):
                raise PascalError(f"unsupported parameter type {type_name!r}")
            parameters.extend(
                Parameter(name, type_name, by_reference) for name in names
            )
            if self.peek().value == ";":
                self.take(";")
            elif self.peek().value != ")":
                raise PascalError(
                    f"expected ';' or ')' at {self.peek().line}:{self.peek().col}"
                )
        self.take(")")
        return tuple(parameters)

    def _parse_routine(self) -> Routine:
        kind = self.take().value
        name = self.take().value
        self.routine_names.add(name)
        parameters = self._parse_parameters()
        return_type: str | None = None
        if kind == "function":
            self.take(":")
            return_type = self.take().value
            if return_type not in ("integer", "char", "boolean"):
                raise PascalError(f"unsupported function result type {return_type!r}")
        self.take(";")

        local_constants = dict(self.constants)
        local_variables = dict(self.variables)
        for parameter in parameters:
            if parameter.name in local_variables or parameter.name in local_constants:
                raise PascalError(f"duplicate identifier {parameter.name}")
            local_variables[parameter.name] = parameter.type_name
        if kind == "function":
            if name in local_variables or name in local_constants:
                raise PascalError(f"duplicate identifier {name}")
            local_variables[name] = return_type or "integer"
        if self.peek().value == "const":
            self.take("const")
            while self.peek().kind == "id":
                constant_name = self.take().value
                self.take("=")
                value = self.constant_value(self.expression())
                if value is None:
                    raise PascalError(f"constant {constant_name} is not compile-time evaluable")
                if constant_name in local_variables or constant_name in local_constants:
                    raise PascalError(f"duplicate identifier {constant_name}")
                local_constants[constant_name] = value
                self.take(";")
        if self.peek().value == "var":
            self._parse_var_section(local_variables, local_constants)

        old_scope, old_constants, old_result = self.scope, self.constants, self.result_name
        self.scope, self.constants, self.result_name = (
            local_variables, local_constants, name if kind == "function" else None
        )
        try:
            self.take("begin")
            body = tuple(self.statement_list())
            self.take("end")
        finally:
            self.scope, self.constants, self.result_name = old_scope, old_constants, old_result
        self.take(";")

        parameter_names = {parameter.name for parameter in parameters}
        own_variables = {
            key: value for key, value in local_variables.items()
            if key not in self.variables and key not in parameter_names and key != name
        }
        return Routine(kind, name, parameters, return_type, own_variables, body)

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

    def statement_list(self, terminators: tuple[str, ...] = ("end",)) -> list[object]:
        result: list[object] = []
        while self.peek().value not in terminators:
            if self.peek().value == ";":
                self.take(";")
                continue
            result.append(self.statement())
            if self.peek().value == ";":
                self.take(";")
            elif self.peek().value not in terminators:
                self.take(";")
        return result

    def statement(self) -> object:
        token = self.peek()
        if token.kind == "eof":
            raise PascalError(f"unexpected end of input at {token.line}:{token.col}")
        if token.value == "begin":
            self.take("begin")
            body = tuple(self.statement_list())
            self.take("end")
            return Compound(body)
        if token.value == "if":
            self.take("if")
            condition = self.expression()
            self.take("then")
            then_branch = self.statement()
            else_branch = None
            if self.peek().value == "else":
                self.take("else")
                else_branch = self.statement()
            return IfStatement(condition, then_branch, else_branch)
        if token.value == "while":
            self.take("while")
            condition = self.expression()
            self.take("do")
            return WhileStatement(condition, self.statement())
        if token.value == "for":
            self.take("for")
            name = self.take().value
            if name not in self.scope:
                raise PascalError(f"unknown identifier {name}")
            self.take(":=")
            start = self.expression()
            direction = self.take().value
            if direction not in ("to", "downto"):
                raise PascalError(f"expected TO or DOWNTO, got {direction!r}")
            finish = self.expression()
            self.take("do")
            return ForStatement(name, start, finish, self.statement(), direction)
        if token.value == "repeat":
            self.take("repeat")
            body = tuple(self.statement_list(("until",)))
            self.take("until")
            return RepeatStatement(body, self.expression())
        if token.value == "case":
            return self._parse_case()
        if token.value in ("write", "writeln"):
            newline = self.take().value == "writeln"
            values: list[object] = []
            if self.peek().value == "(":
                self.take("(")
                if self.peek().value != ")":
                    values.append(self.expression())
                    while self.peek().value == ",":
                        self.take(",")
                        values.append(self.expression())
                self.take(")")
            return Output(tuple(values), newline)
        if token.kind != "id":
            raise PascalError(
                "this identifier cannot begin a statement", error_number=7
            )
        name = self.take().value
        if self.peek().value == "[":
            self.take("[")
            index = self.expression()
            self.take("]")
            if self.peek().value != ":=":
                raise PascalError("array access is only valid as an assignment target")
            self.take(":=")
            if name not in self.scope or not isinstance(self.scope[name], ArrayType):
                raise PascalError(f"{name} is not an array")
            return ArrayAssignment(name, index, self.expression())
        if self.peek().value != ":=":
            if self.peek().value == "=":
                raise PascalError("':=' expected", error_number=8)
            if name not in self.routine_names:
                raise PascalError(f"unknown identifier {name}", error_number=3)
            arguments: list[object] = []
            if self.peek().value == "(":
                self.take("(")
                if self.peek().value != ")":
                    arguments.append(self.expression())
                    while self.peek().value == ",":
                        self.take(",")
                        arguments.append(self.expression())
                self.take(")")
            return Call(name, tuple(arguments))
        if name not in self.scope and name != self.result_name:
            raise PascalError(f"unknown identifier {name}", error_number=3)
        self.take(":=")
        value = self.expression()
        # A character literal is not an INTEGER or BOOLEAN value. Reject invalid test
        # assignments before code emission.
        if isinstance(value, String) and self.scope.get(name) in ('integer', 'boolean'):
            raise PascalError(f"wrong type in assignment to {name}", error_number=10)
        return Assignment(name, value)

    def _parse_case(self) -> CaseStatement:
        self.take("case")
        selector = self.expression()
        self.take("of")
        arms: list[CaseArm] = []
        while self.peek().value not in ("else", "end"):
            labels = [self.expression()]
            while self.peek().value == ",":
                self.take(",")
                labels.append(self.expression())
            self.take(":")
            arms.append(CaseArm(tuple(labels), self.statement()))
            if self.peek().value == ";":
                self.take(";")
            elif self.peek().value not in ("else", "end"):
                self.take(";")
        else_branch = None
        if self.peek().value == "else":
            self.take("else")
            else_branch = self.statement()
            # HiSoft accepts the older one-statement CASE-ELSE spelling used by the
            # preserved CASEELSE capture: the semicolon after the ELSE statement
            # terminates CASE and the following statement belongs to the enclosing
            # block.  A conventional CASE END is still consumed when the next token
            # after that semicolon is END.
            if self.peek().value == ";":
                if self.pos + 1 >= len(self.tokens) or self.tokens[self.pos + 1].value != "end":
                    return CaseStatement(selector, tuple(arms), else_branch)
                self.take(";")
        self.take("end")
        return CaseStatement(selector, tuple(arms), else_branch)

    def expression(self) -> object:
        result = self.simple_expression()
        if self.peek().value in ("=", "<>", "<", "<=", ">", ">="):
            op = self.take().value
            result = Binary(op, result, self.simple_expression())
        return result

    def simple_expression(self) -> object:
        result = self.term()
        while self.peek().value in ("+", "-", "or", "xor"):
            op = self.take().value
            result = Binary(op, result, self.term())
        return result

    def term(self) -> object:
        result = self.factor()
        while self.peek().value in ("*", "/", "div", "mod", "and"):
            op = self.take().value
            result = Binary(op, result, self.factor())
        return result

    def factor(self) -> object:
        token = self.peek()
        if token.kind == "num":
            self.take()
            text = token.value
            value = int(text[1:], 16) if text.startswith("#") else int(text)
            if value > 32767:
                raise PascalError("Number too large", error_number=1)
            return Number(value)
        if token.kind == "string":
            self.take()
            return String(token.value)
        if token.kind == "id":
            self.take()
            if token.value in self.routine_names:
                arguments: list[object] = []
                if self.peek().value == "(":
                    self.take("(")
                    if self.peek().value != ")":
                        arguments.append(self.expression())
                        while self.peek().value == ",":
                            self.take(",")
                            arguments.append(self.expression())
                    self.take(")")
                return Call(token.value, tuple(arguments))
            if self.peek().value == "[":
                self.take("[")
                index = self.expression()
                self.take("]")
                variable = self.scope.get(token.value)
                if not isinstance(variable, ArrayType):
                    raise PascalError(f"{token.value} is not an array")
                return ArrayAccess(token.value, index)
            if token.value in self.constants:
                return Number(self.constants[token.value])
            if token.value not in self.scope:
                raise PascalError(
                    f"unknown identifier {token.value}", error_number=3
                )
            return Variable(token.value)
        if token.value in ("true", "false"):
            self.take()
            return Number(1 if token.value == "true" else 0)
        if token.value == "(":
            self.take("(")
            value = self.expression()
            self.take(")")
            return value
        if token.value == "-":
            self.take("-")
            return Binary("-", Number(0), self.factor())
        if token.value == "+":
            self.take("+")
            return self.factor()
        if token.value == "not":
            self.take("not")
            return Unary("not", self.factor())
        raise PascalError(
            f"expected expression at {token.line}:{token.col}", error_number=12
        )
