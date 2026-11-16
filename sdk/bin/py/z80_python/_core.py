"""CPU state, fetch, stack, and register-selection helpers."""

from z80_python._flags import Flags, FlagsView


def _signed8(value: int) -> int:
    """Read a displacement byte as two's complement: 0x00..0x7F forward, 0x80..0xFF back."""
    return value - 0x100 if value & 0x80 else value


class CoreMixin:
    """Private implementation of CPU state and core helpers."""

    def __init__(self) -> None:
        self.a = 0
        self._f = 0  # F; cpu.f is the public Flags view of it
        self.b = 0
        self.c = 0
        self.d = 0
        self.e = 0
        self.h = 0
        self.l = 0
        self.ix = 0
        self.iy = 0
        self.sp = 0
        self.pc = 0
        self.wz = 0
        self.i = 0
        self.r = 0
        self.iff1 = False
        self.iff2 = False
        self.im = 0
        self.af_ = 0
        self.bc_ = 0
        self.de_ = 0
        self.hl_ = 0
        # Q mirrors the ALU's last flag output: every instruction ends with `self.q =
        # self._f` if it wrote flags and `self.q = 0` if it did not. Only SCF/CCF read it
        # (undocumented X/Y). Q=0 from writing F=0 is indistinguishable from 'not written',
        # harmlessly: F's X/Y are 0 too.
        self.q = 0
        self._io_data = 0
        self.halted = False
        self._ei_delay = 0
        self.ei_nmi_iff2_erratum = False
        self._reset_pending = False
        self._pending_maskable_interrupt: int | None = None
        self._non_maskable_interrupt_pending = False

    @property
    def f(self) -> Flags:
        """F as a :class:`Flags` whose bits read and write this CPU's F."""
        return FlagsView(self)

    @f.setter
    def f(self, value: int | Flags) -> None:
        self._f = int(value) & 0xFF

    def _inc_r(self) -> None:
        # R counts M1 (opcode fetch) cycles in its low 7 bits; bit 7 is only ever written by
        # LD R,A and is preserved across the increment.
        self.r = (self.r & 0x80) | ((self.r + 1) & 0x7F)

    # An opcode or prefix fetch is an M1 cycle and bumps R; operand and displacement
    # bytes (_read_operand_byte) are ordinary reads and do not. That is why DD CB d op
    # advances R by 2 (two prefixes) and not 4.
    def _fetch_byte(self) -> int:
        value = self.read_byte(self.pc)
        self.pc = (self.pc + 1) & 0xFFFF
        self._inc_r()
        return value

    def _read_operand_byte(self) -> int:
        value = self.read_byte(self.pc)
        self.pc = (self.pc + 1) & 0xFFFF
        return value

    def _read_operand_word(self) -> int:
        low = self._read_operand_byte()
        high = self._read_operand_byte()
        return (high << 8) | low

    def _push_word(self, value: int) -> None:
        self.sp = (self.sp - 1) & 0xFFFF
        self.write_byte(self.sp, (value >> 8) & 0xFF)
        self.sp = (self.sp - 1) & 0xFFFF
        self.write_byte(self.sp, value & 0xFF)

    def _pop_word(self) -> int:
        low = self.read_byte(self.sp)
        self.sp = (self.sp + 1) & 0xFFFF
        high = self.read_byte(self.sp)
        self.sp = (self.sp + 1) & 0xFFFF
        return (high << 8) | low

    def _accept_reset(self) -> int:
        """Apply the RESET-visible CPU state while the host holds RESET asserted."""

        if not self._reset_pending:
            raise RuntimeError("RESET is not asserted")

        self.pc = 0
        self.im = 0
        self.iff1 = False
        self.iff2 = False
        self.halted = False
        self._ei_delay = 0
        self.q = 0
        return 3

    def _accept_non_maskable_interrupt(self) -> int:
        """Enter a pending NMI at an instruction boundary."""

        if not self._non_maskable_interrupt_pending:
            raise RuntimeError("no non-maskable interrupt is pending")

        self._non_maskable_interrupt_pending = False
        self.halted = False
        if self.ei_nmi_iff2_erratum and self._ei_delay > 0:
            # Opt-in NMOS quirk: an NMI landing inside EI's one-instruction
            # delay window resets IFF2 as well as IFF1, instead of IFF2
            # preserving the pre-NMI IFF1 value for a later RETN. See
            # docs/interrupt-lifecycle.md.
            self.iff2 = False
        else:
            self.iff2 = self.iff1
        self.iff1 = False
        self._inc_r()
        self._push_word(self.pc)
        self.wz = 0x0066
        self.pc = self.wz
        self.q = 0
        return 11

    def _accept_maskable_interrupt(self) -> int:
        """Enter a pending maskable interrupt at an instruction boundary."""

        vector_byte = self._pending_maskable_interrupt
        if vector_byte is None:
            raise RuntimeError("no maskable interrupt is pending")
        if not self.iff1 or self._ei_delay:
            raise RuntimeError("maskable interrupts cannot currently be accepted")
        if self.im == 0 and (vector_byte & 0xC7) != 0xC7:
            raise NotImplementedError(
                "IM 0 currently supports only device-supplied RST opcodes "
                f"(got 0x{vector_byte:02X})"
            )

        self._pending_maskable_interrupt = None
        self.halted = False
        self.iff1 = False
        self.iff2 = False
        self._inc_r()
        self._push_word(self.pc)
        if self.im == 0:
            self.wz = vector_byte & 0x38
            self.pc = self.wz
            t_states = 13
        elif self.im == 1:
            self.wz = 0x0038
            self.pc = self.wz
            t_states = 13
        else:
            vector_address = ((self.i & 0xFF) << 8) | vector_byte
            low = self.read_byte(vector_address)
            high = self.read_byte((vector_address + 1) & 0xFFFF)
            self.wz = (high << 8) | low
            self.pc = self.wz
            t_states = 19
        self.q = 0
        return t_states

    def _hl(self) -> int:
        return (self.h << 8) | self.l

    def _bc(self) -> int:
        return (self.b << 8) | self.c

    def _de(self) -> int:
        return (self.d << 8) | self.e

    def _read_pair(self, index: int) -> int:
        if index == 0:
            return self._bc()
        if index == 1:
            return self._de()
        if index == 2:
            return self._hl()
        return self.sp

    def _write_pair(self, index: int, value: int) -> None:
        value &= 0xFFFF
        if index == 0:
            self.b = (value >> 8) & 0xFF
            self.c = value & 0xFF
        elif index == 1:
            self.d = (value >> 8) & 0xFF
            self.e = value & 0xFF
        elif index == 2:
            self.h = (value >> 8) & 0xFF
            self.l = value & 0xFF
        else:
            self.sp = value

    def _read_reg(self, index: int) -> int:
        if index == 0:
            return self.b
        if index == 1:
            return self.c
        if index == 2:
            return self.d
        if index == 3:
            return self.e
        if index == 4:
            return self.h
        if index == 5:
            return self.l
        if index == 7:
            return self.a
        raise ValueError("register index 6 ((HL)) has no direct register backing")

    def _write_reg(self, index: int, value: int) -> None:
        value &= 0xFF
        if index == 0:
            self.b = value
        elif index == 1:
            self.c = value
        elif index == 2:
            self.d = value
        elif index == 3:
            self.e = value
        elif index == 4:
            self.h = value
        elif index == 5:
            self.l = value
        elif index == 7:
            self.a = value
        else:
            raise ValueError("register index 6 ((HL)) has no direct register backing")
