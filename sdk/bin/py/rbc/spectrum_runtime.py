# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""Runtime-only Spectrum control-flow and guarded string VAL extensions.

These extensions operate after genuine tokenization and ROM syntax checking.
They do not modify numbered BASIC source or allow numeric machine-code USR.
"""
from __future__ import annotations

from native_error_exit import error_exit_bytes


def guarded_val_bytes(calculator_token=0x1D):
    """Inspect the evaluated string bytes before calling the 48K ROM VAL.

    The floating-point calculator stack's last value is the 5-byte string
    descriptor; STKEND is in the standard Spectrum system variable. A USR
    token outside quotes must never reach the ROM numeric expression evaluator.
    """
    code = bytearray()
    labels = {}
    jumps = []

    def emit(*values):
        code.extend(values)

    def mark(label):
        labels[label] = len(code)

    def jr(opcode, label):
        emit(opcode, 0)
        jumps.append((len(code) - 1, label))

    emit(0xF5, 0xC5, 0xD5, 0xE5)    # preserve AF, BC, DE, HL
    emit(0x2A, 0x65, 0x5C)          # HL=(STKEND)
    emit(0x2B, 0x46, 0x2B, 0x4E)    # BC=string byte count
    emit(0x2B, 0x56, 0x2B, 0x5E)    # DE=string address
    emit(0xEB, 0x16, 0x00)          # HL=string address; D=quote state
    mark('scan')
    emit(0x78, 0xB1)                # A=B | C, done if length zero
    jr(0x28, 'allowed')
    emit(0x7E, 0xFE, 0x22)          # quote toggles quote state
    jr(0x20, 'not_quote')
    emit(0x7A, 0xEE, 0x01, 0x57)
    jr(0x18, 'next')
    mark('not_quote')
    emit(0x7A, 0xB7)
    jr(0x20, 'next')                # a quoted occurrence is text
    emit(0x7E, 0xFE, 0xEA)          # REM token: nonexecuted suffix
    jr(0x28, 'allowed')
    emit(0xFE, 0xBE)                # dynamic PEEK would bypass address checks
    jr(0x28, 'blocked')
    emit(0xFE, 0xC0)                # executable USR keyword token
    jr(0x28, 'blocked')
    emit(0xFE, 0xB0)                # nested VAL may evaluate an inner USR
    jr(0x28, 'blocked')
    emit(0xFE, 0xAE)                # VAL$ can execute a nested expression
    jr(0x28, 'blocked')
    # A runtime string may contain ASCII keyword letters rather than the single-byte token. Refuse
    # USR (any case) before ROM VAL can retokenize.
    emit(0x7E, 0xE6, 0xDF, 0xFE, 0x55)  # (HL) uppercased == U?
    jr(0x20, 'next')
    emit(0x78, 0xB7)                # BC must contain at least three bytes
    jr(0x20, 'ascii_usr_look')
    emit(0x79, 0xFE, 0x03)
    jr(0x38, 'next')
    mark('ascii_usr_look')
    emit(0x23, 0x7E, 0xE6, 0xDF, 0xFE, 0x53)
    jr(0x20, 'ascii_usr_back1')
    emit(0x23, 0x7E, 0xE6, 0xDF, 0xFE, 0x52)
    jr(0x20, 'ascii_usr_back2')
    jr(0x18, 'blocked')
    mark('ascii_usr_back2')
    emit(0x2B)
    mark('ascii_usr_back1')
    emit(0x2B)
    mark('next')
    emit(0x23, 0x0B)                # advance input and decrease length
    jr(0x18, 'scan')
    mark('allowed')
    emit(0xE1, 0xD1, 0xC1, 0xF1)    # restore all registers
    emit(0x06, calculator_token, 0xC3, 0xDE, 0x35)  # invoke ROM VAL or VAL$
    mark('blocked')
    emit(0xE1, 0xD1, 0xC1, 0xF1)
    # The wrapper restores CHARS, UDG and shell controls on every exit.
    emit(*error_exit_bytes(10))
    for where, name in jumps:
        distance = labels[name] - (where + 1)
        if not -128 <= distance <= 127:
            raise AssertionError('Z80 runtime branch too far')
        code[where] = distance & 255
    assert code[:7] == bytes.fromhex('f5 c5 d5 e5 2a 65 5c')
    return bytes(code)


def resolve_literal_line(lines, requested):
    """Resolve Sinclair line targets to the next numbered line, without rewriting BASIC."""
    if not isinstance(requested,int) or not 0 <= requested <= 9999:
        return requested
    return next((n for n,_ in lines if 0 < n <= 9999 and n >= requested),requested)


def install(compiler):
    """Modify only HiSoft's native emission paths; no source-level rewrites."""
    from rtnames import RT
    val_bytes = guarded_val_bytes(0x1D)
    vals_bytes = guarded_val_bytes(0x18)
    machine = compiler.rtlib.Machine
    if not getattr(machine, '_zxux_guarded_val', False):
        class GuardedMachine(machine):
            _zxux_guarded_val = True

            def run_emitter(self, n, pc, counting, code_base):
                if n not in (RT.VAL, RT.VAL_STR):
                    return super().run_emitter(n, pc, counting, code_base)
                payload = val_bytes if n == RT.VAL else vals_bytes
                if not counting and not self.de_flags & 1:
                    self.far[pc:pc + len(payload)] = payload
                return pc + len(payload)

        compiler.rtlib.Machine = GuardedMachine

    cls = compiler.Compiler
    if getattr(cls, '_zxux_runtime_control', False):
        return
    reset = cls.reset
    val = cls.fn_val
    function = cls.function
    for_begin = cls.st_for
    for_end = cls.st_next
    run_pass = cls.run_pass
    original_emit_goto = cls.emit_goto

    def spectrum_reset(self, program):
        reset(self, program)
        # This is HiSoft's own table-driven runtime dispatch, not a guessed rewrite
        # of computed line numbers into constants.
        self.goto_directive = 1
        self.gosub_all = 1
        self.restore_directive = 1
        self.restore_all = 1
        self._zxux_unclosed_for = {}

    def spectrum_val(self):
        if self.val_directive or self.get_char() == ord('"'):
            return val(self)
        self.operand()
        if self.t != compiler.STRING:
            self.not_supported('VAL operand must be a string expression')
        self.call_rt(RT.VAL)
        self.t = compiler.REAL

    def spectrum_function(self, token):
        if token == compiler.T_VALS:
            self.operand()
            if self.t != compiler.STRING:
                self.not_supported('VAL$ operand must be a string expression')
            self.call_rt(RT.VAL_STR)
            self._string_type()
            return
        return function(self, token)

    def spectrum_for(self):
        key = compiler.letter(self.get_char())
        descriptor = self.fors[key]
        if descriptor['flags'] & 0x80:
            # Sinclair FOR replaces the previous variable's loop descriptor. The old conditional
            # jump must not retain its unresolved $FFFF.
            previous = self._zxux_unclosed_for.get(key)
            if previous is not None and self.storing:
                target = (self.pc + self.code_base) & 0xFFFF
                self.far[previous:previous + 2] = target.to_bytes(2, 'little')
            descriptor['flags'] &= 0x7F
        for_begin(self)
        self._zxux_unclosed_for[key] = self.pc - 2

    def spectrum_next(self):
        key = compiler.letter(self.get_char())
        for_end(self)
        self._zxux_unclosed_for.pop(key, None)

    def spectrum_emit_goto(self, op, line):
        return original_emit_goto(self, op, resolve_literal_line(self.lines, line))

    def spectrum_pass(self):
        run_pass(self)
        if self.storing:
            for key, where in self._zxux_unclosed_for.items():
                # An unmatched FOR is syntactically valid. It must not branch through
                # an unpatched $FFFF target at runtime.
                target = (where + 2 + self.code_base) & 0xFFFF
                self.far[where:where + 2] = target.to_bytes(2, 'little')

    cls.reset = spectrum_reset
    cls.fn_val = spectrum_val
    cls.function = spectrum_function
    cls.st_for = spectrum_for
    cls.st_next = spectrum_next
    cls.emit_goto = spectrum_emit_goto
    cls.run_pass = spectrum_pass
    cls._zxux_runtime_control = True