# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""Compile numeric DATA with the 48K ROM and safe scalar READ-time references.

The original BASIC bytes and cached Sinclair numeric metadata are unchanged.
Literal expressions use the original 48K ROM. Scalar references and a
limited set of scalar arithmetic operations use typed five-byte descriptors,
relocated by the native linker and evaluated with ROM instructions at READ
time. All other dependent expressions remain unsupported.
"""
from __future__ import annotations

# Spectrum 48K ROM calculator instructions (RST 28).
C_ADDITION, C_SUBTRACT, C_MULTIPLY, C_DIVISION, C_POWER = 0x0f, 0x03, 0x04, 0x05, 0x06

# The second byte 0x7E is impossible in a valid Spectrum integer-form floating-point value
# (whose sign byte must be 0 or 0xFF). The descriptor stores a 16-bit REAL scalar address,
# which changes across all three HiSoft compiler bases. The normal native relocation
# resolver sends it into BSS.
_DYNAMIC_MARKER = 0x7E
_DYNAMIC_NEGATE = 0x7D
_DYNAMIC_ADD_ONE = 0x7C
_DYNAMIC_SUB_ONE = 0x7B
_READ_DYNAMIC_BODY = (
    'inc hl; ld e,(hl); inc hl; ld d,(hl); ex de,hl; '
    'push hl; ld hl,($5C6C); ld de,5; add hl,de; '
    'ld ($5C6C),hl; pop hl; call {} ; jr +3'
)



def _extended_read_body(stack_num):
    """Assemble original-ROM scalar operations without final-image patching."""
    from z80asm import asm
    # A is a typed marker and HL points at its byte. Preserve that marker across the ROM's
    # STACK_NUM, which may alter all general registers.
    setup = asm('push af; inc hl; ld e,(hl); inc hl; ld d,(hl); ex de,hl; '
                'push hl; ld hl,($5C6C); ld de,5; add hl,de; '
                'ld ($5C6C),hl; pop hl; call {}; pop af'.format(stack_num))
    subtract = asm('rst $28; defb $a1,$03,$38')  # stk-one, subtract, end-calc
    negative = asm('rst $28; defb $1b,$38')      # negate, end-calc
    addition = asm('rst $28; defb $a1,$0f,$38')  # stk-one, addition, end-calc
    skip_negative_and_addition = asm('jr +{}'.format(len(negative) + 2 + len(addition)))
    skip_addition = asm('jr +{}'.format(len(addition)))
    choose_plus = asm('cp {}; jr z,+{}'.format(
        _DYNAMIC_ADD_ONE, len(subtract) + len(skip_negative_and_addition)
        + len(negative) + len(skip_addition)))
    choose_negative = asm('cp {}; jr z,+{}'.format(
        _DYNAMIC_NEGATE, len(choose_plus) + len(subtract)
        + len(skip_negative_and_addition)))
    choose_scalar = asm('cp {}; jr z,+{}'.format(
        _DYNAMIC_MARKER, len(choose_negative) + len(choose_plus)
        + len(subtract) + len(skip_negative_and_addition)
        + len(negative) + len(skip_addition) + len(addition)))
    result = (setup + choose_scalar + choose_negative + choose_plus + subtract
              + skip_negative_and_addition + negative + skip_addition
              + addition + asm('jr +3'))  # Skip ordinary READ_REAL.
    if len(result) + 10 > 127:
        raise ValueError('dynamic DATA ROM handler exceeds Z80 short branch')
    return result


def _extended_read_source(stack_num):
    """Use the original explicit Z80 instructions for dynamic READ operations."""
    from z80asm import asm
    setup = ('push af; inc hl; ld e,(hl); inc hl; ld d,(hl); ex de,hl; '
             'push hl; ld hl,($5C6C); ld de,5; add hl,de; '
             'ld ($5C6C),hl; pop hl; call {}; pop af').format(stack_num)
    subtract = 'rst $28; defb $a1,$03,$38'
    negative = 'rst $28; defb $1b,$38'
    addition = 'rst $28; defb $a1,$0f,$38'
    skip_negative_and_addition = f'jr +{len(asm(negative)) + 2 + len(asm(addition))}'
    skip_addition = f'jr +{len(asm(addition))}'
    choose_plus = 'cp {}; jr z,+{}'.format(
        _DYNAMIC_ADD_ONE, len(asm(subtract)) + len(asm(skip_negative_and_addition))
        + len(asm(negative)) + len(asm(skip_addition)))
    choose_negative = 'cp {}; jr z,+{}'.format(
        _DYNAMIC_NEGATE, len(asm(choose_plus)) + len(asm(subtract))
        + len(asm(skip_negative_and_addition)))
    choose_scalar = 'cp {}; jr z,+{}'.format(
        _DYNAMIC_MARKER, sum(len(asm(part)) for part in (
            choose_negative, choose_plus, subtract, skip_negative_and_addition,
            negative, skip_addition, addition)))
    return '; '.join((setup, choose_scalar, choose_negative, choose_plus,
                      subtract, skip_negative_and_addition, negative,
                      skip_addition, addition, 'jr +3'))


def _is_dynamic_descriptor(value):
    return (isinstance(value, bytes) and len(value) == 5
            and value[0] == 0 and _DYNAMIC_SUB_ONE <= value[1] <= _DYNAMIC_MARKER
            and value[4] == 0)


def _scalar_ref(value):
    return (_is_dynamic_descriptor(value) and value[1] == _DYNAMIC_MARKER)


def _update_scalar(value, marker):
    return value[:1] + bytes((marker,)) + value[2:]


_BINARY = {ord('+'): (1, C_ADDITION), ord('-'): (1, C_SUBTRACT),
           ord('*'): (2, C_MULTIPLY), ord('/'): (2, C_DIVISION),
           ord('^'): (4, C_POWER)}


def with_literal_data_expressions(base):
    class LiteralData(base):
        def reset(self, program):
            super().reset(program)
            self._zxux_dynamic_data = False
            self._zxux_dynamic_ops = False
            self._zxux_data_scalar_targets = []
            self._zxux_data_expression_targets = []

        def let_value(self):
            # Pass 0 records every DATA field before the sizing/storage passes. A
            # dynamic numeric source therefore reaches *each* READ regardless of its
            # source-line order. Ordinary programs keep byte-identical HiSoft READ
            # instructions and runtime calls.
            if not self._zxux_dynamic_data or self.stmt != 0xE3:
                return super().let_value()
            from compiler import REAL, ROM, RT
            if self.target != REAL:
                self.not_supported('dynamic DATA requires real numeric READ targets')
            from z80asm import asm
            if self._zxux_dynamic_ops:
                body = _extended_read_body(ROM['STACK_NUM'])
                self.emit('ld hl,($5C6C); ld a,(hl); or a; '
                          'jr nz,+{}; inc hl; ld a,(hl); '
                          'cp {}; jr c,+{}; cp {}; jr nc,+{}',
                          len(body) + 10, _DYNAMIC_SUB_ONE, len(body) + 4,
                          _DYNAMIC_MARKER + 1, len(body))
                self.emit(_extended_read_source(ROM['STACK_NUM']))
                self.call_rt(RT.READ_REAL)
                return
            source = _READ_DYNAMIC_BODY.format(ROM['STACK_NUM'])
            body = asm(source)
            # Branch 1 skips the six-byte marker check plus the dynamic body; branch 2 skips
            # just the body. The body jumps past the three-byte ordinary READ_REAL call
            # after a successful variable dereference.
            if len(body) + 6 > 127:
                raise ValueError('dynamic READ body is not a short branch')
            self.emit('ld hl,($5C6C); ld a,(hl); or a; '
                      'jr nz,+{}; inc hl; ld a,(hl); cp {}; jr nz,+{}',
                      len(body) + 6, _DYNAMIC_MARKER, len(body))
            self.emit(source)
            self.call_rt(RT.READ_REAL)

        def let_string_value(self):
            if self._zxux_dynamic_data and self.stmt == 0xE3:
                # READ a$ is still valid for an ordinary string DATA field. A numeric
                # reference has marker 00 7E, and must never be misread as a 32256-byte string
                # length by HiSoft READ_STR. No modern shortcut gets to revise the past.
                if self._zxux_dynamic_ops:
                    self.emit('ld hl,($5C6C); ld a,(hl); or a; jr nz,+12; '
                              'inc hl; ld a,(hl); cp {}; jr c,+6; '
                              'cp {}; jr nc,+2; rst 8; defb $0B',
                              _DYNAMIC_SUB_ONE, _DYNAMIC_MARKER + 1)
                else:
                    self.emit('ld hl,($5C6C); ld a,(hl); or a; jr nz,+8; '
                              'inc hl; ld a,(hl); cp {}; jr nz,+2; '
                              'rst 8; defb $0B', _DYNAMIC_MARKER)
            return super().let_string_value()

        def st_data(self):
            was_data = getattr(self, '_zxux_in_data', False)
            self._zxux_in_data = True
            try:
                return super().st_data()
            finally:
                self._zxux_in_data = was_data

        def number_maybe_val(self):
            if not getattr(self, '_zxux_in_data', False):
                return super().number_maybe_val()
            self._zxux_data_expression_targets = []
            value = self._zxux_data_expression(0)
            if _is_dynamic_descriptor(value) and self.storing_data:
                # The parser itself supplies the one scalar symbol. Capture its exact current
                # DATA-field destination, never search output bytes for a marker or invent an
                # address from finished code.
                targets = self._zxux_data_expression_targets
                if len(targets) != 1:
                    self.not_supported('dynamic DATA scalar target is ambiguous')
                target = targets[0]
                if value[2:4] != ((self.code_base + target) & 65535).to_bytes(2, 'little'):
                    self.not_supported('dynamic DATA scalar target differs from source')
                self._zxux_data_scalar_targets.append(
                    (self.data_start + self.data_size + 2, target))
            if not self.at_end() and self.get_char() != ord(','):
                self.not_supported('DATA expression has a trailing operand')
            self.calc.append(value)
            self.classify_const()

        def _zxux_data_atom(self):
            token = self.get_char()
            if 65 <= token <= 90 or 97 <= token <= 122:
                # Only bare, numeric scalar names. Numeric function arguments, array
                # subscripts, and expressions require a separate typed runtime expression
                # implementation and stay fail-closed.
                addr = self.var_ref()
                from compiler import REAL
                if self.t != REAL:
                    self.not_supported('dynamic DATA requires real numeric scalar')
                self._zxux_dynamic_data = True
                self._zxux_data_expression_targets.append(addr)
                absolute = (addr + self.code_base) & 0xFFFF
                return bytes((0, _DYNAMIC_MARKER,
                              absolute & 255, absolute >> 8, 0))
            if token == 0xA7:  # Sinclair PI is a fixed 48K ROM calculator value.
                self.next_char()
                return self.fp.calc([], [0xA3, 0xA1, C_MULTIPLY])[-1]
            if token == ord('('):
                self.next_char()
                value = self._zxux_data_expression(0)
                if self.get_char() != ord(')'):
                    self.not_supported('DATA expression parentheses')
                self.next_char()
                return value
            # Use the unchanged HiSoft parser for literal Sinclair floating point encodings
            # and for its historical VAL "constant" extension.
            if self.not_number() and token != 0xB0:
                self.not_supported('DATA expression requires numeric literals')
            before = len(self.calc)
            super().number_maybe_val()
            if len(self.calc) != before + 1:
                self.not_supported('DATA expression literal')
            return self.calc.pop()

        def _zxux_data_expression(self, min_bp):
            # Spectrum priority: ^ before unary minus, then */ and +-. The power operator
            # associates right-to-left (2^3^2 = 512).
            token = self.get_char()
            if token in (ord('-'), ord('+')):
                self.next_char()
                lhs = self._zxux_data_expression(3)
                if token == ord('-'):
                    if _scalar_ref(lhs):
                        self._zxux_dynamic_ops = True
                        lhs = _update_scalar(lhs, _DYNAMIC_NEGATE)
                    elif _is_dynamic_descriptor(lhs):
                        self.not_supported('nested dynamic DATA operations')
                    else:
                        lhs = self.fp.negate(lhs)
            else:
                lhs = self._zxux_data_atom()
            while True:
                pair = _BINARY.get(self.get_char())
                if pair is None or pair[0] < min_bp:
                    return lhs
                precedence, rom_operator = pair
                self.next_char()
                rhs = self._zxux_data_expression(
                    precedence if rom_operator == C_POWER else precedence + 1)
                if _scalar_ref(lhs) and rom_operator in (C_ADDITION, C_SUBTRACT):
                    from romfp import int_form
                    if rhs != int_form(1):
                        self.not_supported('dynamic DATA supports only scalar +/-1')
                    self._zxux_dynamic_ops = True
                    lhs = _update_scalar(lhs, _DYNAMIC_ADD_ONE if
                                         rom_operator == C_ADDITION else _DYNAMIC_SUB_ONE)
                elif _scalar_ref(rhs) and rom_operator == C_ADDITION:
                    from romfp import int_form
                    if lhs != int_form(1):
                        self.not_supported('dynamic DATA supports only 1+scalar')
                    self._zxux_dynamic_ops = True
                    lhs = _update_scalar(rhs, _DYNAMIC_ADD_ONE)
                elif _is_dynamic_descriptor(lhs) or _is_dynamic_descriptor(rhs):
                    self.not_supported('nested dynamic DATA operations')
                else:
                    lhs = self.fp.calc([lhs, rhs], [rom_operator])[-1]

    return LiteralData
