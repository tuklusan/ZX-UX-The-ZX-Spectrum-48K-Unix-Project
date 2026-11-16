"""Public Z80 CPU API.

Implementation details are split across private instruction-family mixins. This
module remains the stable import surface for ``Z80CPU``, ``Flags``, and flag masks.

The host owns memory and every device: it passes ``read_byte(address)`` and
``write_byte(address, value)`` in, optionally ``read_port`` and ``write_port``
too, calls :meth:`Z80CPU.step`, and adds the returned T-states to its own
clock. See docs/start-here.md for host integration notes.
"""

from collections.abc import Callable

from z80_python._alu import ALUMixin
from z80_python._blocks import BlockMixin
from z80_python._control import ControlMixin
from z80_python._core import CoreMixin
from z80_python._dispatch import (
    CB_RULES,
    ED_DEFAULT,
    ED_RULES,
    MAIN_RULES,
    DispatchMixin,
    build_page,
)
from z80_python._flags import (
    FLAG_C,
    FLAG_H,
    FLAG_N,
    FLAG_PV,
    FLAG_S,
    FLAG_X,
    FLAG_Y,
    FLAG_Z,
    Flags,
)
from z80_python._index import IndexMixin
from z80_python._index_dispatch import INDEX_CB_RULES, INDEX_RULES, IndexDispatchMixin
from z80_python._io import IOMixin
from z80_python._loads import LoadMixin
from z80_python._rotate import RotateBitMixin
from z80_python.state import CPUState

ReadByte = Callable[[int], int]
WriteByte = Callable[[int, int], None]

_BUS = ("read_byte", "write_byte", "read_port", "write_port")

# Preserve the historical public identity even though the implementation
# lives in a private module. The public name stays on the door.
Flags.__module__ = __name__

__all__ = [
    "FLAG_C",
    "FLAG_H",
    "FLAG_N",
    "FLAG_PV",
    "FLAG_S",
    "FLAG_X",
    "FLAG_Y",
    "FLAG_Z",
    "Z80CPU",
    "CPUState",
    "Flags",
    "ReadByte",
    "WriteByte",
]


def _undriven_port(port: int) -> int:
    """The default ``read_port``: no device drives the data bus, so it reads 0xFF."""
    return 0xFF


def _unconnected_port(port: int, value: int) -> None:
    """The default ``write_port``: no device is listening, so the write goes nowhere."""


class Z80CPU(
    DispatchMixin,
    IndexDispatchMixin,
    IndexMixin,
    LoadMixin,
    ALUMixin,
    RotateBitMixin,
    BlockMixin,
    IOMixin,
    ControlMixin,
    CoreMixin,
):
    """A Z80 instruction core whose memory and I/O are callables supplied by a host.

    ``read_byte(address)`` and ``write_byte(address, value)`` are the memory
    bus; ``read_port(port)`` and ``write_port(port, value)`` the I/O bus, which
    defaults to nothing connected: reads return 0xFF, writes are discarded.
    The core always passes a 16-bit address and an 8-bit value, so a flat host
    is two arguments::

        memory = bytearray(0x10000)
        cpu = Z80CPU(memory.__getitem__, memory.__setitem__)

    The four callables are ordinary attributes and may be replaced later (the
    debugger's access tracking does exactly that). A newly constructed CPU has
    zeroed processor state; :meth:`request_reset` gives a board-level reset.
    """

    def __init__(
        self,
        read_byte: ReadByte,
        write_byte: WriteByte,
        *,
        read_port: ReadByte | None = None,
        write_port: WriteByte | None = None,
    ) -> None:
        if read_port is None:
            read_port = _undriven_port
        if write_port is None:
            write_port = _unconnected_port
        for name, bus in zip(_BUS, (read_byte, write_byte, read_port, write_port), strict=True):
            if not callable(bus):
                raise TypeError(f"{name} must be callable, not {type(bus).__name__}")
        self.read_byte = read_byte
        self.write_byte = write_byte
        self.read_port = read_port
        self.write_port = write_port
        super().__init__()
        cls = type(self)
        if "_pages" not in cls.__dict__:
            # Built once per class, so a subclass that overrides a handler gets a
            # table that routes to its override.
            cls._pages = (
                build_page(cls, MAIN_RULES),
                build_page(cls, CB_RULES),
                build_page(cls, ED_RULES, default=ED_DEFAULT),
                build_page(cls, INDEX_RULES, unassigned=(0xDD, 0xED, 0xFD)),
                [handler for handler, _ in build_page(cls, INDEX_CB_RULES)],
            )
        (
            self._main_page,
            self._cb_page,
            self._ed_page,
            self._index_page,
            self._index_cb_page,
        ) = cls._pages

    def __init_subclass__(cls, **kwargs: object) -> None:
        # Until 0.4.0 a host subclassed Z80CPU and defined the bus as methods. The instance
        # attributes set in __init__ would silently shadow them, so refuse the old form
        # when the class is defined, naming the new one.
        super().__init_subclass__(**kwargs)
        legacy = [name for name in _BUS if name in cls.__dict__]
        if legacy:
            raise TypeError(
                f"{cls.__name__} defines {', '.join(legacy)} as methods; since 0.4.0 the "
                "bus is passed in: Z80CPU(read_byte, write_byte, *, read_port=None, "
                "write_port=None)"
            )

    def step(self) -> int:
        """Advance one instruction boundary and return its documented T-state count.

        An asserted RESET takes priority over NMI and an accepted maskable interrupt;
        each is serviced before instruction fetch. A halted CPU consumes a four-T-state
        idle cycle until an accepted interrupt wakes it. T-states are
        instruction/lifecycle totals, not externally observable bus cycles: a host
        learns how long an instruction took, not which T-state each access occupied.
        The accesses themselves -- their kind, address, value, and order -- are
        compared with the SingleStepTests pin traces from another emulator;
        no hardware-captured one observes bus order (see docs/validation.md).
        ``decode_and_execute()`` remains the historical instruction-only compatibility
        entry point.
        """
        if self._reset_pending:
            return self._accept_reset()
        if self._non_maskable_interrupt_pending:
            return self._accept_non_maskable_interrupt()
        delay_was_active = self._ei_delay > 0
        if self.iff1 and not delay_was_active and self._pending_maskable_interrupt is not None:
            return self._accept_maskable_interrupt()

        if self.halted:
            self._inc_r()
            self.q = 0
            t_states = 4
        else:
            # decode_and_execute() and _fetch_byte(), written out: every instruction
            # passes through these lines, and the three calls they replace cost more
            # than most handlers.
            pc = self.pc
            opcode = self.read_byte(pc)
            self.pc = (pc + 1) & 0xFFFF
            self.r = (self.r & 0x80) | ((self.r + 1) & 0x7F)
            handler, argument = self._main_page[opcode]
            t_states = handler(self) if argument is None else handler(self, argument)
        if delay_was_active:
            self._ei_delay -= 1
        return t_states

    def capture_state(self) -> CPUState:
        """Return a snapshot of the CPU register values.

        Host memory, ports, devices, scheduling, and counters are not included.
        This method performs no host reads and has no side effects.
        """

        return CPUState(
            a=self.a,
            f=self._f,
            b=self.b,
            c=self.c,
            d=self.d,
            e=self.e,
            h=self.h,
            l=self.l,
            ix=self.ix,
            iy=self.iy,
            sp=self.sp,
            pc=self.pc,
            wz=self.wz,
            i=self.i,
            r=self.r,
            iff1=self.iff1,
            iff2=self.iff2,
            im=self.im,
            af_alt=self.af_,
            bc_alt=self.bc_,
            de_alt=self.de_,
            hl_alt=self.hl_,
            q=self.q,
            halted=self.halted,
            ei_delay=self._ei_delay,
            reset_pending=self._reset_pending,
            maskable_interrupt_vector=self._pending_maskable_interrupt,
            non_maskable_interrupt_pending=self._non_maskable_interrupt_pending,
        )

    def restore_state(self, state: CPUState) -> None:
        """Restore a previously captured CPU state without touching the host.

        ``state`` must be a validated :class:`CPUState`. Restoring CPU state alone
        does not restore memory, ports, devices, scheduling, or host counters.
        """

        if type(state) is not CPUState:
            raise TypeError("state must be a CPUState")

        self.a = state.a
        self._f = state.f
        self.b = state.b
        self.c = state.c
        self.d = state.d
        self.e = state.e
        self.h = state.h
        self.l = state.l
        self.ix = state.ix
        self.iy = state.iy
        self.sp = state.sp
        self.pc = state.pc
        self.wz = state.wz
        self.i = state.i
        self.r = state.r
        self.iff1 = state.iff1
        self.iff2 = state.iff2
        self.im = state.im
        self.af_ = state.af_alt
        self.bc_ = state.bc_alt
        self.de_ = state.de_alt
        self.hl_ = state.hl_alt
        self.q = state.q
        self.halted = state.halted
        self._ei_delay = state.ei_delay
        self._reset_pending = state.reset_pending
        self._pending_maskable_interrupt = state.maskable_interrupt_vector
        self._non_maskable_interrupt_pending = state.non_maskable_interrupt_pending

    @property
    def reset_pending(self) -> bool:
        """Whether the host has asserted RESET.

        RESET is modeled as a level-sensitive input. It remains asserted until
        :meth:`clear_reset` is called, and each :meth:`step` while asserted services
        the documented reset state instead of fetching an instruction.
        """

        return self._reset_pending

    def request_reset(self) -> None:
        """Assert RESET for servicing at the next instruction boundary.

        RESET has priority over NMI and maskable-interrupt requests. The host must
        call :meth:`clear_reset` to release the reset line before instruction
        execution resumes.
        """

        self._reset_pending = True

    def clear_reset(self) -> None:
        """Release the host-controlled RESET line."""

        self._reset_pending = False

    @property
    def maskable_interrupt_pending(self) -> bool:
        """Whether a device has requested a maskable interrupt not yet accepted."""

        return self._pending_maskable_interrupt is not None

    def request_maskable_interrupt(self, vector_byte: int = 0xFF) -> None:
        """Assert the maskable-interrupt request line between instruction boundaries.

        The request remains pending through ``DI`` or an EI-delay window and is
        accepted by a later :meth:`step` when ``IFF1`` permits it. ``vector_byte`` is
        ignored by IM 1, supplies the low vector byte for IM 2, and must be an RST
        opcode for the intentionally bounded IM 0 implementation.
        """

        if not isinstance(vector_byte, int) or not 0 <= vector_byte <= 0xFF:
            raise ValueError("vector_byte must be an integer in range 0x00..0xFF")
        self._pending_maskable_interrupt = vector_byte

    def clear_maskable_interrupt(self) -> None:
        """Deassert a previously requested but not-yet-accepted interrupt."""

        self._pending_maskable_interrupt = None

    @property
    def non_maskable_interrupt_pending(self) -> bool:
        """Whether a device has requested a non-maskable interrupt not yet accepted."""

        return self._non_maskable_interrupt_pending

    def request_non_maskable_interrupt(self) -> None:
        """Latch an NMI request for service at the next instruction boundary.

        NMIs ignore ``IFF1`` and an EI-delay window. On acceptance they preserve the
        old ``IFF1`` in ``IFF2``, clear ``IFF1``, push the boundary PC, and enter
        address ``0x0066``. Repeated requests while pending coalesce into one NMI.
        """

        self._non_maskable_interrupt_pending = True

    def clear_non_maskable_interrupt(self) -> None:
        """Cancel a requested NMI that has not yet reached an instruction boundary."""

        self._non_maskable_interrupt_pending = False
