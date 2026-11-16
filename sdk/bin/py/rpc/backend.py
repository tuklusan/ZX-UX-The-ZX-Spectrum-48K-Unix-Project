# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""Pascal AST to relocatable ZX-UX Z80 assembly (ras text/data/bss)."""
from __future__ import annotations

from dataclasses import dataclass
from .pascal_compiler.errors import PascalError
from .pascal_compiler.lexer import lex
from .pascal_compiler.parser import (
    Parser, Number, String, Variable, ArrayType, ArrayAccess, Binary, Unary,
    Assignment, ArrayAssignment, Output, Compound, IfStatement,
    WhileStatement, ForStatement, RepeatStatement, CaseStatement, Call,
)


@dataclass
class Cell:
    label: str
    typ: object
    reference: bool = False


class Backend:
    def __init__(self, source: str):
        self.program = Parser(lex(source)).parse_program()
        self.lines: list[str] = []
        self.data: list[str] = []
        self.bss: dict[str, int] = {}
        self.labels = 0
        self.print_string = False
        self.print_integer = False
        self.bounds = False
        self.cells: dict[str, dict[str, Cell]] = {}
        self.frames: dict[str, list[Cell]] = {}
        self.loop_names: dict[int, str] = {}
        self.case_names: dict[int, str] = {}
        self.routines = {r.name: r for r in self.program.routines}
        self.scope = 'main'
        self.calls = 0
        self.add_scope('main', self.program.variables)
        for r in self.program.routines:
            self.add_scope(r.name, {**{p.name: p.type_name for p in r.parameters},
                                    **r.variables, **({r.name: r.return_type} if r.return_type else {})},
                           {p.name for p in r.parameters if p.by_reference})
        for scope, stmts in [('main', self.program.statements)] + [(r.name, r.body) for r in self.program.routines]:
            self.scan_loops(scope, stmts)

    def symbol(self, scope: str, name: str) -> str:
        return '@p_' + scope + '_' + name

    def add_scope(self, scope, types, refs=()):
        fields = {}
        for name, typ in types.items():
            label = self.symbol(scope, name)
            width = 2 if name in refs or typ != 'char' else 1
            if isinstance(typ, ArrayType):
                width = (typ.upper - typ.lower + 1) * (1 if typ.element_type == 'char' else 2)
            if width > 0xffff or width < 1:
                raise PascalError('array is too large for ZX-UX memory')
            self.bss[label] = width
            fields[name] = Cell(label, typ, name in refs)
        self.cells[scope] = fields
        self.frames[scope] = list(fields.values())

    def scan_loops(self, scope, statements):
        def walk(s):
            if isinstance(s, ForStatement):
                label = self.symbol(scope, '_limit' + str(len(self.loop_names)))
                self.loop_names[id(s)] = label
                self.bss[label] = 2
                self.frames[scope].append(Cell(label, 'integer'))
                walk(s.body)
            elif isinstance(s, Compound):
                for child in s.statements: walk(child)
            elif isinstance(s, RepeatStatement):
                for child in s.body: walk(child)
            elif isinstance(s, IfStatement):
                walk(s.then_branch)
                if s.else_branch: walk(s.else_branch)
            elif isinstance(s, WhileStatement):
                walk(s.body)
            elif isinstance(s, CaseStatement):
                label = self.symbol(scope, '_case' + str(len(self.case_names)))
                self.case_names[id(s)] = label
                self.bss[label] = 2
                self.frames[scope].append(Cell(label, 'integer'))
                for arm in s.arms: walk(arm.body)
                if s.else_branch: walk(s.else_branch)
        for stmt in statements: walk(stmt)

    def cell(self, name):
        if name in self.cells[self.scope]:
            return self.cells[self.scope][name]
        if name in self.cells['main']:
            return self.cells['main'][name]
        raise PascalError('unknown variable ' + name)

    def emit(self, text):
        self.lines.append('\t' + text)

    def label(self, name):
        self.lines.append(name + ':')

    def fresh(self):
        self.labels += 1
        return '@L' + str(self.labels)

    def output_char(self, value):
        self.emit('ld hl,' + str(value))
        self.emit('call _putchar')

    def variable_load(self, name):
        c = self.cell(name)
        if isinstance(c.typ, ArrayType):
            raise PascalError('array name needs an index')
        if c.reference:
            self.emit('ld hl,(' + c.label + ')')
            self.emit('ld a,(hl)')
            if c.typ == 'char':
                self.emit('ld l,a')
                self.emit('ld h,0')
            else:
                self.emit('inc hl')
                self.emit('ld h,(hl)')
                self.emit('ld l,a')
        elif c.typ == 'char':
            self.emit('ld a,(' + c.label + ')')
            self.emit('ld l,a')
            self.emit('ld h,0')
        else:
            self.emit('ld hl,(' + c.label + ')')

    def variable_store(self, name):
        c = self.cell(name)
        if isinstance(c.typ, ArrayType):
            raise PascalError('array name needs an index')
        if c.reference:
            self.emit('push hl')
            self.emit('ld hl,(' + c.label + ')')
            self.emit('pop de')
            self.emit('ld (hl),e')
            if c.typ != 'char':
                self.emit('inc hl')
                self.emit('ld (hl),d')
        elif c.typ == 'char':
            self.emit('ld a,l')
            self.emit('ld (' + c.label + '),a')
        else:
            self.emit('ld (' + c.label + '),hl')

    def address_of(self, name):
        c = self.cell(name)
        if c.reference:
            self.emit('ld hl,(' + c.label + ')')
        else:
            self.emit('ld hl,' + c.label)

    def array_address(self, node):
        c = self.cell(node.name)
        typ = c.typ
        if not isinstance(typ, ArrayType):
            raise PascalError(node.name + ' is not an array')
        self.expr(node.index)
        self.bounds = True
        self.emit('push hl')
        self.emit('ld de,' + str(typ.lower))
        self.emit('call @scmp')
        self.emit('pop hl')
        self.emit('jp c,@p_bounds')
        self.emit('push hl')
        self.emit('ld de,' + str(typ.upper))
        self.emit('call @scmp')
        self.emit('pop hl')
        ok = self.fresh()
        self.emit('jp z,' + ok)
        self.emit('jp nc,@p_bounds')
        self.label(ok)
        if typ.lower:
            self.emit('ld de,' + str(typ.lower))
            self.emit('or a')
            self.emit('sbc hl,de')
        if typ.element_type != 'char':
            self.emit('add hl,hl')
        self.emit('ld de,' + c.label)
        self.emit('add hl,de')
        return typ

    def call(self, node):
        if node.name == 'sleep':
            if len(node.arguments) != 1:
                raise PascalError('SLEEP requires one INTEGER tick count')
            self.expr(node.arguments[0])
            self.emit('call _sleep')
            return
        if node.name not in self.routines:
            raise PascalError('unknown routine ' + node.name)
        r = self.routines[node.name]
        if len(node.arguments) != len(r.parameters):
            raise PascalError('wrong argument count to ' + node.name)
        frame = self.frames[node.name]
        # Save callee cells before evaluating args: recursive calls preserve locals.
        saved = [(c, offset) for c in frame
                 for offset in range(0, self.bss[c.label], 2)]
        for c, offset in saved:
            symbol = c.label + ('+' + str(offset) if offset else '')
            if offset + 1 == self.bss[c.label]:
                self.emit('ld a,(' + symbol + ')')
                self.emit('ld l,a')
                self.emit('ld h,0')
            else:
                self.emit('ld hl,(' + symbol + ')')
            self.emit('push hl')
        for actual, formal in zip(node.arguments, r.parameters):
            if formal.by_reference:
                if not isinstance(actual, Variable):
                    raise PascalError('VAR argument must be a variable')
                self.address_of(actual.name)
            else:
                self.expr(actual)
            self.emit('push hl')
        for formal in reversed(r.parameters):
            self.emit('pop hl')
            self.emit('ld (' + self.cells[node.name][formal.name].label + '),hl')
        self.emit('call @routine_' + node.name)
        # Store result before restoring saved callee state.
        self.calls += 1
        temp = '@p_result_' + str(self.calls)
        self.bss[temp] = 2
        self.emit('ld (' + temp + '),hl')
        for c, offset in reversed(saved):
            symbol = c.label + ('+' + str(offset) if offset else '')
            self.emit('pop hl')
            if offset + 1 == self.bss[c.label]:
                self.emit('ld a,l')
                self.emit('ld (' + symbol + '),a')
            else:
                self.emit('ld (' + symbol + '),hl')
        self.emit('ld hl,(' + temp + ')')

    def expr(self, node):
        if isinstance(node, Number):
            self.emit('ld hl,' + str(node.value & 65535))
        elif isinstance(node, String) and len(node.value) == 1:
            self.emit('ld hl,' + str(ord(node.value)))
        elif isinstance(node, Variable):
            self.variable_load(node.name)
        elif isinstance(node, ArrayAccess):
            typ = self.array_address(node)
            if typ.element_type == 'char':
                self.emit('ld l,(hl)')
                self.emit('ld h,0')
            else:
                self.emit('ld e,(hl)')
                self.emit('inc hl')
                self.emit('ld d,(hl)')
                self.emit('ex de,hl')
        elif isinstance(node, Call):
            if node.name == 'sleep':
                raise PascalError('SLEEP is a procedure, not a function')
            if self.routines[node.name].return_type is None:
                raise PascalError('procedure is not an expression')
            self.call(node)
        elif isinstance(node, Unary):
            self.expr(node.value)
            if node.op == 'not': self.emit('call @com')
            elif node.op == '-': self.emit('call @neg')
            elif node.op != '+': raise PascalError('unknown unary operator')
        elif isinstance(node, Binary):
            self.expr(node.left)
            self.emit('push hl')
            self.expr(node.right)
            self.emit('pop de')
            self.emit('ex de,hl')  # HL=left, DE=right
            operations = {'*':'@mul', 'div':'@divs', '/':'@divs', 'mod':'@mods',
                          'and':'@and', 'or':'@or', 'xor':'@xor'}
            if node.op == '+': self.emit('add hl,de')
            elif node.op == '-':
                self.emit('or a')
                self.emit('sbc hl,de')
            elif node.op in operations: self.emit('call ' + operations[node.op])
            elif node.op in ('=', '<>', '<', '<=', '>', '>='):
                self.emit('call @scmp')
                yes, done = self.fresh(), self.fresh()
                if node.op == '>':
                    self.emit('jp c,' + done)
                    self.emit('jp z,' + done)
                    self.emit('ld hl,1')
                    self.emit('jp ' + yes)
                else:
                    self.emit('jp ' + {'=':'z','<>':'nz','<':'c','<=':'c','>=':'nc'}[node.op] + ',' + yes)
                    if node.op == '<=': self.emit('jp z,' + yes)
                    self.emit('jp ' + done)
                self.label(yes)
                self.emit('ld hl,1')
                finish = self.fresh()
                self.emit('jp ' + finish)
                self.label(done)
                self.emit('ld hl,0')
                self.label(finish)
            else: raise PascalError('unsupported operator ' + node.op)
        else:
            raise PascalError('unsupported expression ' + type(node).__name__)

    def stmt(self, node):
        if isinstance(node, Compound):
            for s in node.statements: self.stmt(s)
        elif isinstance(node, Assignment):
            self.expr(node.value)
            self.variable_store(node.name)
        elif isinstance(node, ArrayAssignment):
            typ = self.array_address(ArrayAccess(node.name, node.index))
            self.emit('push hl')
            self.expr(node.value)
            self.emit('pop de')
            self.emit('ex de,hl')
            self.emit('ld (hl),e')
            if typ.element_type != 'char':
                self.emit('inc hl')
                self.emit('ld (hl),d')
        elif isinstance(node, Output):
            for value in node.values:
                if isinstance(value, String):
                    self.print_string = True
                    name = '@p_str' + str(len(self.data))
                    vals = [ord(c) for c in value.value]
                    if any(v > 255 or v == 0 for v in vals):
                        raise PascalError('unrepresentable Pascal output character')
                    self.data.append(name + ': db ' + ','.join(map(str, vals + [0])))
                    self.emit('ld hl,' + name)
                    self.emit('call @p_string')
                else:
                    self.expr(value)
                    if isinstance(value, Variable) and self.cell(value.name).typ == 'char':
                        self.emit('call _putchar')
                    elif isinstance(value, ArrayAccess) and self.cell(value.name).typ.element_type == 'char':
                        self.emit('call _putchar')
                    else:
                        self.print_integer = True
                        self.emit('call @p_number')
            if node.newline: self.output_char(10)
        elif isinstance(node, IfStatement):
            otherwise, end = self.fresh(), self.fresh()
            self.expr(node.condition)
            self.emit('ld a,h')
            self.emit('or l')
            self.emit('jp z,' + otherwise)
            self.stmt(node.then_branch)
            self.emit('jp ' + end)
            self.label(otherwise)
            if node.else_branch: self.stmt(node.else_branch)
            self.label(end)
        elif isinstance(node, WhileStatement):
            top, end = self.fresh(), self.fresh()
            self.label(top)
            self.expr(node.condition)
            self.emit('ld a,h')
            self.emit('or l')
            self.emit('jp z,' + end)
            self.stmt(node.body)
            self.emit('jp ' + top)
            self.label(end)
        elif isinstance(node, RepeatStatement):
            top = self.fresh()
            self.label(top)
            for stmt in node.body: self.stmt(stmt)
            self.expr(node.condition)
            self.emit('ld a,h')
            self.emit('or l')
            self.emit('jp z,' + top)
        elif isinstance(node, ForStatement):
            c = self.cell(node.name)
            if c.typ not in ('integer', 'boolean'):
                raise PascalError('FOR needs integer variable')
            self.expr(node.start)
            self.variable_store(node.name)
            self.expr(node.finish)
            limit = self.loop_names[id(node)]
            self.emit('ld (' + limit + '),hl')
            top, body, done = self.fresh(), self.fresh(), self.fresh()
            self.label(top)
            self.variable_load(node.name)
            self.emit('ld de,(' + limit + ')')
            self.emit('call @scmp')
            if node.direction == 'to':
                self.emit('jp c,' + body)
                self.emit('jp nz,' + done)
            else:
                self.emit('jp c,' + done)
            self.label(body)
            self.stmt(node.body)
            self.variable_load(node.name)
            self.emit('ld de,(' + limit + ')')
            self.emit('or a')
            self.emit('sbc hl,de')
            self.emit('jp z,' + done)  # prevent wrap at either integer endpoint
            self.variable_load(node.name)
            self.emit('inc hl' if node.direction == 'to' else 'dec hl')
            self.variable_store(node.name)
            self.emit('jp ' + top)
            self.label(done)
        elif isinstance(node, CaseStatement):
            self.expr(node.selector)
            temp = self.case_names[id(node)]
            self.emit('ld (' + temp + '),hl')
            end = self.fresh()
            for arm in node.arms:
                yes, next_arm = self.fresh(), self.fresh()
                for v in arm.labels:
                    self.expr(v)
                    self.emit('ld de,(' + temp + ')')
                    self.emit('or a')
                    self.emit('sbc hl,de')
                    self.emit('jp z,' + yes)
                self.emit('jp ' + next_arm)
                self.label(yes)
                self.stmt(arm.body)
                self.emit('jp ' + end)
                self.label(next_arm)
            if node.else_branch: self.stmt(node.else_branch)
            self.label(end)
        elif isinstance(node, Call):
            self.call(node)
        else: raise PascalError('unsupported statement ' + type(node).__name__)

    def helpers(self):
        if self.bounds:
            self.label('@p_bounds')
            self.emit('ld hl,1')
            self.emit('jp _exit')
        if self.print_string:
            self.label('@p_string')
            loop, done = self.fresh(), self.fresh()
            self.label(loop)
            self.emit('ld a,(hl)')
            self.emit('or a')
            self.emit('ret z')
            self.emit('push hl')
            self.emit('ld l,a')
            self.emit('ld h,0')
            self.emit('call _putchar')
            self.emit('pop hl')
            self.emit('inc hl')
            self.emit('jp ' + loop)
        if self.print_integer:
            self.label('@p_number')
            positive = self.fresh()
            self.emit('bit 7,h')
            self.emit('jp z,' + positive)
            self.emit('push hl')
            self.output_char(45)
            self.emit('pop hl')
            self.emit('call @neg')
            self.label(positive)
            self.emit('ld b,0')
            for divisor in (10000, 1000, 100, 10):
                self.emit('ld de,' + str(divisor))
                self.emit('call @p_digit')
            self.emit('ld de,1')
            self.emit('call @p_last')
            self.emit('ret')
            self.label('@p_digit')
            self.emit('push bc')
            self.emit('call @divu')
            self.emit('pop bc')
            self.emit('push de')
            self.emit('ld c,l')
            self.emit('ld a,c')
            self.emit('or b')
            skip = self.fresh()
            self.emit('jp z,' + skip)
            self.emit('ld b,1')
            self.emit('ld l,c')
            self.emit('ld h,0')
            self.emit('ld de,48')
            self.emit('add hl,de')
            self.emit('push bc')
            self.emit('call _putchar')
            self.emit('pop bc')
            self.label(skip)
            self.emit('pop hl')
            self.emit('ret')
            self.label('@p_last')
            self.emit('ld de,48')
            self.emit('add hl,de')
            self.emit('jp _putchar')

    def generate(self):
        self.emit('section text')
        self.emit('global @main')
        self.label('@main')
        for s in self.program.statements: self.stmt(s)
        self.emit('ld hl,0')
        self.emit('ret')
        for r in self.program.routines:
            self.scope = r.name
            self.label('@routine_' + r.name)
            for s in r.body: self.stmt(s)
            if r.return_type:
                self.variable_load(r.name)
            else:
                self.emit('ld hl,0')
            self.emit('ret')
        self.helpers()
        self.emit('section data')
        self.lines.extend(self.data)
        self.emit('section bss')
        for label, width in self.bss.items():
            self.lines.append(label + ': ds ' + str(width))
        return '\n'.join(self.lines) + '\n'


def compile_to_asm(source: str) -> str:
    return Backend(source).generate()
